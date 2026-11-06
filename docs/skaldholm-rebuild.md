# Skaldholm rebuild (zone shapes pilot, branch `feat/skaldholm-rebuild`, off `feat/zone-shapes` bd9fec8)

Owner, 2026-11-06: the four neighbours' walls (Greenmeadow, Crags, Gloamfen, Rimeveil) stay exactly as built; the city is made in the middle of them ("i just want to keep the walls ... and make the city in the middle"). Pilot only. TODO `SKALDHOLM-REBUILD`, wiki `10_projects:valhallasc_skaldholm_rebuild_20261106`.

## Measured

The ground the four shaped neighbours do not own is an **L of 14,486 tiles** (91% of the old 126 x 126 = 15,876), atlas frame = tile + `shape.T`: a north part x 370-454 (85 wide), y 600-728, and a south band x 370-502, y 728-755. The doors are fixed by the neighbours: N (411,601), E (452,663), W (371,703), S (438,755). The atlas decagon (15,800) is NOT what the walls enclose. `zone_scale` as coded would give Skaldholm k = 1.32: it must be forced to 1.0. `python3 scripts/skaldholm_rebuild_plan.py OUT.png` reproduces the numbers and draws the plan (read-only).

## Layout (stage 1, a plan, nothing written to the map yet)

* **Rigid middle strip.** Old x 38.5-123.5 (85 wide), old y 13-139 translate by (331.5, 587): the Grand Avenue (old x 80) lands on x 411.5, the Trade Road (old y 76) on y 663 = the Crags door, the N end on the Rimeveil door. That keeps the plaza and fountain, Cathedral, Steward's court, Archive, Guild court, Gilded Lute yard, Meeting Stone court, the Undervault stairs (old 104.4,122) and 82 of the 108 houses exactly as they are, with no scaling. NPC routes inside the strip need no change.
* **South band** (133 x 27, about 3,500 tiles) takes what lay outside the strip: 26 houses, smithy yard, stable yard, the NW garden with its fountain, 8 NPCs (smith, apprentice, painter, weaver, stable master, three watchmen), plus a street along it (new Southgate Street) and the road up from the S door (438,755). Free room is left over: the only place for a new district.
* Old walls, towers, the Great Gate approach, the Glacier gate arch at x 48 and the outer trees go.

## Open points found while planning

* The **Steward's Hall** (old 80,19) stands in the avenue where the Rimeveil door now lands: move the hall off the avenue (not yet done) and keep its NPC and `es_05_m` (80,28) coherent.
* The **W door** (371,703) lands beside old houses at the west edge (old x 39-46, y 110-125): they move to the band and a West Street runs from the door to Lark Lane.
* The **Crags/Greenmeadow notch**: the L's top edge x 456-502 at y 727 has no wall piece, it is only void collision. The city needs a wall there (a Crags-side segment, a small addition to the four walls).
* The vault machinery (`build_walls` in `zone_shapes.py`) copies the city's OWN wall pieces into each neighbour's frame and derives the vault shift from the arch positions, so the plan keeps it: stage 2 makes the city a shaped zone in ONE frame (T = [357,599], grid 168), puts its arches exactly in the doorways so each vault shift equals `T_neighbour - T_city`, and makes the city's wall pieces coincide with the neighbours' pieces. Then there is one wall, seen from both sides.
* Everything keyed to city coordinates moves with the rigid strip (`exitArches`, `cityEntrances`, `atlasPaths`, `exitRoutes`, `paths`, the season decor arrays, `places`, `spawn`, NPC routes, quest targets, the Undervault stairs portal); the band content needs the same.

## Stage 2 as built (scripts/skaldholm_rebuild.py, config key `cityRebuild` in world/zone-shapes.txt)

* **When:** the very last step of `zone_shapes.py apply`, after the four neighbours are shaped, walled and designed. The neighbours' ramparts, towers, floors and vault regions are fingerprinted before and after and must be identical (assert), so the walls stay exactly as built; only each gate's frame fields (`vault`, `tx`, `ty`) change. Verified: a diff of the whole map against the pilot map shows only `portals` in zones 0-3 and 5 and the whole of zone 4.
* **One frame:** city tile = atlas tile - TC (352, 590), grid 168; each vault's shift is `T_neighbour - TC`, the city's arches stand in the doorways (arch = neighbour arch + shift).
* **Ground:** the L the four neighbour floors leave (flood fill from the middle) plus the pocket in front of each door (14,779 tiles); `shapeFloor`, `shapeEdge` (a letter per neighbour), `void` collision beyond it; `shape.rule = 'rebuild'`. The city has NO wall of its own: no rampart or tower is left in zone 4 (the Hall's two flank towers go too, for the north door's lane).
* **Content:** the strip x 38.5-123.5 moves by (-20.5, -3.0). Outside it: 26 houses along Southgate Street (doors south) and its south side, the smithy yard (smith, apprentice, campfire), the stable yard (stables, stable-hand), the garden (fountain, benches, gardener, painter), the market stalls and the weaver, the two watchmen on new beats; the Steward's Hall stays and a lane runs behind it from the Rimeveil door and down its west side; West Street joins the Gloamfen door to Lark Lane; the avenue, Lark Lane and Raven Row run on to Southgate Street; a road runs up from the Greenmeadow door. Seasonal decor follows the piece it belonged to.
* **Checks inside the build:** every NPC, place, portal arrival and the spawn stands on ground; a flood fill over the collision from the spawn reaches the four doors, the Undervault stairs, every NPC and the Empty Seat place; every walker's route is on the ground and clear; NPCs inside a wall margin or a house step to the nearest reachable ground. Two `sync-world` runs are byte-identical.
* **Sidecar / unshape:** `world/zone-shapes/preshape-04.txt` holds the old city view and the Undervault's arrival points, saved at the start of `apply` (before the neighbours' `build_walls` edits the city's back portals) and restored by `unshape` AFTER the neighbours' `shift_incoming(-1)`.
* **Client** (`client/field.js`): `inSquare` is the floor mask when the city is shaped (a box test against an L hides the neighbours' land in the notch); beyond the L the sky is dark, not sea; the city's ground does not blend toward a neighbour's. The Crags/Greenmeadow notch (the L's top edge between them, x 104-158 at y 143 in the city frame) has a short run of 18 city ramparts (`layout: skaldholm_notch`), the only wall the city owns; the neighbours' walls are untouched. Each door has an alcove through its wall opening (3.5 tiles beyond the arch line, opening width minus 1) so you arrive on floor and can turn round; the city's back portal stands 1 tile beyond the arch line (a vault crosses from 3 tiles before its portal). Frame TC = (352, 584), grid 184 so every portal lies inside the grid.
* **Checks run (2026-11-06):** `tests/vault-seamless-ui.cjs` with `ZONES=0`, `1`, `2`, `3` (8-9 checks each, bounded, one door per run): same scenery around each arch from both sides, last row of land identical, no neighbour region hides anything on the city's own ground, real walks both ways with no crossing spike. Rust: the city tests adapted (`skaldholm_is_a_big...`, `skaldholm_people...`, `compact_atlas_city_*`) pass; the other failures (`skaldholm_has_eleven_valid_quests`, `the_skaldholm_gate_pair`, `skaldholm_flies_to_both_wyrdwood_hubs`, three `compact_atlas_*`, `shaped_zones_keep_all_content_on_land`, eleven `vault_tests`) fail identically on the pilot baseline `bd9fec8`.
* **Pilot database:** `scripts/skaldholm_positions.py --db FILE [--apply]` (strip positions move with the strip, the rest go to the spawn).
* `python3 scripts/skaldholm_rebuild.py plan OUT.png` draws the rebuilt city.

## Stages

1. Plan (this commit).
2. `zone_shapes.py`: Skaldholm joins `zones`, sidecar/unshape, force k = 1.0, one frame; a `skaldholm_design.py` applies the cut-and-translate and fills the band; walls and vaults re-derived; `align_corner_wall` and `trim_corner_seam` re-checked.
3. Checks: `tests/vault-seamless-ui.cjs` (bounded), Rust city tests, two `sync-world` runs byte-identical, pilot swap per the pilot deploy order.
