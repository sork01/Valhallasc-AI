# The Emberfall Crags as an authored map (zone shapes pilot, 2026-11-06)

Owner request: "for the pilot. redesign crags. keep shape and borders etc. but redesign the rest of the map and the quests. to not have any filler land and to use the entire map." Pilot only (`feat/zone-shapes`). Owner choices: the Cinderlord plus two new elites, three outposts, every old quest id kept and rewritten, the four lava rivers follow the painted atlas.

## What stays

The outline, seams, Skaldholm wall and vault, the four walk gates (Wyrdwood, Bifrost, Nacrehold, Orrery), Cinderwatch Camp and its people, the spawn point, the Ember Grave Cross and its sleeper, the Empty Seat circle, and every quest id. `crags_captain` keeps the mercenary offers.

## How it is built

- `scripts/crags_design.py` runs in `zone_shapes.py apply` right after Greenmeadow's design, after `build_walls`, so nothing it does can move a border. `class Crags(Designer)` reuses `greenmeadow_design.py`'s helpers; data in `scripts/crags_content.py`. `python3 scripts/crags_design.py plan OUT.png` draws it read-only.
- The plan traces the painted atlas (`tile = atlas px * 1758/2048 - shape.T` in painted pixels; the atlas frame is 2048 wide, the picture 1758): four rivers stepping the land into terraces, the snow-capped peaks, the pale ledge roads, the fire pit in the south, the cut quarry block in the south-west.
- Twelve regions, every land cell in one: The Cinderwatch Shelf, The Sunpit Flats, The Anvil Quarries, The Wallfoot, The Red Slopes, The Hearth Reach, The Horned Terrace, The Long Steps, Highfire Ridge, The Ashen Crown, The Steaming Spurs, The Glass Shore.
- **Rivers:** `lava` circles along a Catmull-Rom line, wider than the old ones; any road crossing makes a ford (10 fords). The Sunpit is a lake of the same circles. Lava stays more than 16 tiles from every seam (asserted, currently 22.5): the neighbour's ground does not draw it, so it would pop in.
- **Lava rendering:** `EmberwakeArt.molten` used one texture for the whole zone (`size*12` wide, 4320 x 2800 px with the rivers spread out). It now rasterises per ground chunk (`moltenPatch`), same sample grid, so the same pixels; nothing is retained.
- **Peaks:** `crag_peak` (`client/emberwakeart.js`), three sizes by `v`, foot = collision circle, `occludes` so a hero behind one shows through. Peaks nudge off roads and fixed spots.
- Self-checks in `design()`: spawns, new NPCs, places and every gate reachable from the spawn on foot with lava solid, roads on land with nothing standing on them, under 1% of open cells cut off, lava clear of seams. Two `sync-world` runs are byte-identical and no other zone changes.
- Difficulty comes only from where a kind stands: wisps (5) round the Flats, Shelf and Quarries; spiders (7) on the Slopes and Wallfoot; wraiths (8) on the Steps, Terrace and Reach; golems (10) on Highfire, the Crown and the Spurs. 363 spawns (was 252).

## New zone data and client

- `groundSpans` for zone 1: 1 ash, 2 scree, 3 terrace, 4 black sand, 5 quarry, 6 cooled crust beside lava, 7 steam rock (`emberGround`, `EMBER_MINI` in `field.js`). None within 16-30 tiles of a seam. Roads on classed ground are paler.
- `regions`: `regionAt` now reads the current zone; `areaName` uses hub, region, zone name for any zone with `regions`.
- `camps`: Anvilrest (quarry), Ashford (the second river's ford), Lasthearth (Orrery road). Each has givers, a trader, a mailbox and a Travel Master linked to Cinderwatch.
- Seam ghosts of an ember neighbour now include art-drawn scenery (`crag_peak`, `ew_basalt`, `ew_vent`, ...), as for the meadow.
- Minimap: in the authored Crags scattered stones and trees are not dotted (`MINI_QUIET`).

## Quests

33 in the zone: 16 old ids rewritten (some moved to outpost givers, `crags_supply_route` is now a three-outpost delivery), 17 new. Level 5-10, `rewardXp = levels.txt[level-1] / 10`. Kinds: bring, kill, visit, talk, hold (The Pit Props, The Beacon Lit), escort (Ulf up the Highfire road). Swedish by hand in `sv-translations.txt`, names and places in `sv-keep.txt`.

## Elites

`cinderlord` (Horned Terrace, quest), `slagmaw` (south shore of the Sunpit, quest `anvil_slagmaw`), `ashwing` (the Ashen Crown, no quest). Level 10, hard-coded in `world.rs`/`items.rs` like the Cinderlord, respawn 180 s, enrage `[180, 0.2, 3.0]`, materials `slagmaw_gullet`, `ashwing_plume`. Art: `scripts/crags_elite_redraw.py` (montage, preview, build, refresh, export, verify), sources `scripts/crags_elite_sources.txt`, manifest `client/assets/cragselites.txt`. PixelFlow caps a sprite at 1,048,576 cells: 34 frames allow about 175 x 175. Stats are a first guess, not balanced: the owner tests fights.

## Checks

`REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/crags-design-ui.cjs` (regions, outposts, elites, pictures in `test-results/crags-design/`); `SEAMS=1` compares the same world point from both frames of each Crags seam, object by object and on a pixel grid, against a camera-move control. `cargo test zone_shape` plays the beacon hold and Ulf's escort.

## Pilot database

`scripts/crags_positions.py --db FILE [--apply]` moves characters who now stand inside scenery to the spawn (service stopped, backup first).
