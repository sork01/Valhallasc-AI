# Zone shapes pilot: Greenmeadow and the Emberfall Crags (branch `feat/zone-shapes`)

Status 2026-11-05: **candidate on a branch, not on main, live game untouched.** Owner decisions: `nofloor` scale rule, Asterion unchanged, everything on the atlas eventually (`docs/zone-shapes.md`). This pilot shapes zones 0 and 1 only.

## What changed for the player

| | before | now |
|---|---|---|
| Greenmeadow | 96x96 square | 240 grid, outline 236x135 tiles (2.28x area): Gloamfen to the west, Skaldholm north-west, Crags north-east, Moonspore east, coast in the south |
| Emberfall Crags | 96x96 square | 208 grid, outline 203x195 tiles (3.0x area): eight neighbours, the four lava rivers run on past the old edge |

* The **old square is kept as a core**, moved as one block (Greenmeadow by (116, 64), Crags by (43, 59)), so Alderhaven, Cinderwatch Camp, every NPC, quest, spawn and the lava fords are unchanged; new ground around it is filled with scenery, spawns and trail at the old densities (Greenmeadow +319 objects +37 spawns, Crags +463 objects +51 spawns; new spawn kinds follow the old progression: by distance from Alderhaven, by y for the Crags).
* **The Greenmeadow/Crags border is a seamless seam**: you walk over the line anywhere along its 87 tiles and the server moves you by the border's whole-tile shift to the very same spot of the other zone, with no hop, no banner and no chat line; held keys and the camera carry on. One `Portal` with a `seam` (polyline, shift, side) replaces the gate (`Seam::crossing` in `model.rs`, `use_portal` in `world.rs`); the land runs a 2.4 tile margin past the line so a walker can step over it. Both zones use one tile scale and **integer tile origins** (`shape.T`), so the shift is whole tiles and cells, noise and rasterised borders line up exactly. Borders with zones that are not shaped yet keep one gate each.
* **What you see across a seam:** the ground is the same mix of both floors from either side (weight .5 at the line, 0 at 14 tiles, each zone sampling the other's noise and trails at the mapped cell), and the neighbour's trees, bushes and rocks are drawn beyond the line (`map.ghosts`). Not shown across a seam yet: enemies, players, NPCs, lava and other themed scenery (that is step 2).
* **Ground transition:** near any border the ground blends into the neighbour's floor material over 14 tiles (meadow green to Crags ash, and back). Borders with only a gate get a low rim and the neighbour's flat ground outside.
* **Coast:** an outline edge is coast when open water lies within 60 atlas px outward (the pale beach strip no longer counts as land), so the whole south of Greenmeadow is shore.
* Outside the outline: coast is water, a border with another province is a dark wall, outer land a rocky rim; beyond that the backdrop is dark. The minimap and the detailed world map show only the land.

## How it is built

* `scripts/zone_shapes.py` (`unshape` / `apply`), config `world/zone-shapes.txt` (k = 0.56116 tiles per atlas px, zones `[0, 1]`).
* `sync-world` runs `unshape` first (every generator and overlay sees the **old square layout and old coordinates**, so `raid_key.py`, `empty_seat.py`, the seasonal overlays, `compact_atlas.py`, `mailboxes.py` need no change) and `apply` last. `apply` saves the old-layout zone to `world/zone-shapes/preshape-<zone>.txt`, then shapes it.
* **Never run a zone generator on a shaped zone**: run `python3 scripts/zone_shapes.py unshape` first (restores from the sidecar), run the generator, then `node scripts/sync-world.cjs`. Two consecutive `sync-world` runs give identical `map.txt` and `client/world.js`.
* Collision is the Bifrost mechanism (plus the seam portal in `model.rs`/`world.rs`): every non-land cell is covered by `void` rectangles (917 and 714 pieces, comparable to Bifrost's 1,022), so the server, pursuit, chest and route code needed no change. 
* New zone fields: `size` (multiple of 8), `shape` (rule, k, `offset` of the core, `frame`, `outline`, `edges` runs with kind/other zone), `shapeFloor` rows (`#` land), `shapeEdge` rows (what the outside cell next to the land is: b border, c coast, l land, g gap).
* Smoothing: each outline run between junctions gets two Chaikin passes, once per shared chain, so neighbours match.
* Portals: `place_portals` in `zone_shapes.py` reuses `compact_atlas`'s reachability and clearance tests and places each crossing 5-14 tiles inside its chain, with the arrival six tiles further in.
* Client: `field.js` (`paintShape`, `outsideTile`, backdrop, minimap, shifted meadow literals), `city.js` (Alderhaven road), `worldmap.js` (dot, outline overlay, atlas marker transform).
* Saved characters: `scripts/zone_shapes_migrate.py --db <file> [--apply]` adds the core offset to characters saved in shaped zones and resets those zones' fog.

## Test it (private copy next to the live game)

* Pilot server: port 8081 on the Docker bridge, own database **copy** (made with sqlite's backup API at 2026-11-05 02:10; the 30 characters in zones 0 and 1 were moved by the migration), no Surv notify variables. Beta progress does not carry back to the live game. Unit file `deploy/valhalla-shapes.service` (install by hand), served client = this branch's `client/` (live the moment a file is saved).
* Public path: `bash scripts/zone_shapes_beta.sh on|off|status` adds or removes a marked proxy block in the live checkout's `deploy/apache.conf` and reloads Apache gracefully after `configtest`; URL `https://gunning.se/Valhallasc-shapes/`. Log in again there (character storage is per endpoint); SSO and game accounts work.
* Checks run: Rust `zone_shape` (3 tests: land content, edge walkers, gate crossings, seam crossing at 24+ points both ways), `tests/zone-shape-ui.cjs` (bounded: edge walks, both gate crossings, hub placement, screenshots in `test-results/zone-shapes/`).

## Not done / open

* Not verified in a browser: detailed world map pictures and player markers (`atlasPosition` transform), Spark Travel pictures, the touch layout.
* The outside edge is a flat dark band (7 tiles), not final art; no cliff faces or shoreline foam.
* Existing Rust tests were not run beyond `zone_shape`; assertions on zone 0/1 sizes or old coordinates may need updating.
* Filler uses the old densities; kind mix and trail layout in the new ground have not been judged in play. The Crags rivers continue past the core with one extra ford about 52 tiles from each core edge.
* Rolling the pilot out for real needs `SHAPE-MIGRATE` (service stopped, backup, `zone_shapes_migrate.py --apply`) and a server restart.
