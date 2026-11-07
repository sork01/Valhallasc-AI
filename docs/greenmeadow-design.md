# Greenmeadow as an authored map (zone shapes pilot, 2026-11-06)

Owner request: "redesign greenmeadow. keep shape and borders etc. but redesign the rest of the map and the quests. to not have any filler land and to use the entire map." Pilot only (`feat/zone-shapes`). Owner choices: existing enemy kinds plus three new elites; 2-3 hamlets with their own quest givers.

## What stays

The outline, seams, Skaldholm wall and vault, Alderhaven and its people, the spawn point, the Ember Grave Cross and its sleeper, the Empty Seat circles and the quest ids `welcome`, `slime_patrol`, `meadow_bounty`, `ironhide_hunt`, `king_challenge`.

## How it is built

- `scripts/greenmeadow_design.py` runs as the last step of `zone_shapes.py apply`, after `build_walls`, so nothing it does can move a border. `unshape` drops everything it added (camps, spans, new quests), so every overlay still sees the old square. Data: `scripts/greenmeadow_content.py` (hamlets, NPCs, places, quests).
- The plan traces the owner's painted atlas (`tile = atlas px - shape.T`): the road lattice, the north-east ponds, the western tree clumps, the south beach. `python3 scripts/greenmeadow_design.py plan OUT.png` draws it read-only.
- Every land cell belongs to the nearest noise-warped seed of nine regions, so no ground is left over: Alderhaven Fields, The Wallside Pasture, The Oldgrove, The Westerling Downs, The Saltgrass Strand, The Ironhide Scarp, The Three Meres, The Applewick Orchards, Hollowend.
- Self-checks in `design()`: spawns, new NPCs and places are reachable from the spawn on foot, roads stay on land, under 1% of open cells cut off. Two `sync-world` runs are byte-identical.
- Difficulty comes only from where a kind stands (a spawn has no level): green round the town, blue/pink further out, yellow, then beetles on the Scarp and in Hollowend. 278 spawns (was 222).

## New zone-0 data

- `groundSpans` `[y, x0, x1, kind]`: 1 sand, 2 tilled field, 3 downs, 4 forest floor, 5 clover, 6 scarp (`meadowGround`, `MEADOW_MINI` in `field.js`). None within 16-30 tiles of a seam: the other side blends toward plain meadow and knows nothing of these classes.
- `regions` `{names, spans}`: `Field.areaName` and the HUD banner name where you are.
- `camps`: Stonefold, Saltby, Applewick. Sanctuaries with givers, a trader, a mailbox and a Travel Master linked to Alderhaven. `ZONES[0]` in `field.js` copies a fixed key list, so `camps`, `places`, `groundSpans`, `regions` were added there. `stoneTile` leaves them on the region's own ground.
- Seam ghosts of a meadow neighbour now include art-drawn scenery (oaks, birches, hawthorn, wildflowers) and its ponds (`map.ghostWater`, `drawWater(g, t, true)`), or they would pop in. `sceneAround` skips water, so an object diff cannot see a missing pond: look at the pictures.
- Seamless check: `SEAMS=1 REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/greenmeadow-ui.cjs` compares three points on each meadow seam from both frames, object by object and on an 81-point pixel grid, against a control (the same points after a camera move inside the zone). `Field.screenOf` returns fractions of the canvas.

## Quests

16 new, level 1-5, `rewardXp = levels.txt[level-1] / 10`. Kinds used: bring, kill, visit, talk, hold (The Ring at Dusk, two waves), escort (Lotta to the watermill). Swedish by hand in `sv-translations.txt`; names and places in `sv-keep.txt`.

## Elites

`oldtusker` (the Oldgrove, quest), `tidecrusher` (the Strand, quest), `orchardqueen` (the wild hives, no quest). `tidecrusher` is not `saltclaw`: that id is a level-60 Stormglass enemy. Level 7, hard-coded in `world.rs`/`items.rs` like the Cinderlord, respawn 180 s, enrage `[180, 0.2, 3.0]`, materials `tusker_bristle`, `tidecrusher_shard`, `queen_stinger`. Art: `scripts/meadow_elite_redraw.py` (montage, preview, build, refresh, export, verify), sources `scripts/meadow_elite_sources.txt`, manifest `client/assets/greenmeadow.txt`. Stats are a first guess, not balanced: the owner tests fights.

## Pilot database

`scripts/greenmeadow_positions.py --db FILE [--apply]` moves characters who now stand inside scenery to the spawn (service stopped, backup first).

## Known

- Rust at this point: `zone_shape` 23 pass, `perks_tests` 16 pass. Still failing and not from this work: `compact_atlas` (3, listed in AGENTS.md), three Spark link-list tests on other hubs, `mail_all` (Alderhaven's directory entry keeps old-square coordinates, the same in HEAD), `king_spawn_announcement_stays_in_greenmeadow` (join refused: two default names; not compared against HEAD).
- `tests/quest-rewards.py` has six failures on older rewards (Nornroot, Longship, Black Hour); the Greenmeadow rewards all meet its rules.
- Not checked: the detailed world map pictures, the touch layout, fights against the elites.
- Pacing: a kill pays 50-70 XP, so level 5 needs about 24 kills; players outgrow a level 1-5 zone long before finishing this map. Left as it is pending an owner decision.
- `apple_tree` art: its fruit fell on a straight diagonal because x and y used the same linear seed (Sunward too); fixed in `sunwardart.js`.

## Collision grid (2026-11-06)

`server/src/object_grid.rs`: `Map::collide` and `Map::line_clear` scanned every obstacle of the zone. They now ask a 4-tile grid, built on first use per map (`GridSlot`, a clone starts empty). Results are exactly the scan's: file order is kept, and after a push the remaining obstacles are asked again near the new position. `grid_matches_the_full_scan` compares both on every zone (4,000 cases each; mutation-checked). A map whose object list was replaced falls back to the scan; an edit in place needs `map.grid = Default::default()` (only tests do this).

Measured, test profile, 20 heroes walking in Greenmeadow: 36.9 -> 13.5 ms per tick (budget 50 ms), 13.3 ms with no objects at all. `collide` in zone 0: 138 -> 0.29 us.

## Buildings (2026-11-07)

Owner: the hamlet houses "look terrible" / "like crap" (`STONEFOLD-HOUSES`, `APPLEWICK-HOUSES`, `GREENMEADOW-HOUSES`). The ten hamlet cottages and the mill were Sunward Vale's flat front-on pictures (`vale_cottage`, `watermill`), and Hollowend's "roofless chapel" drew as a whole timber house. Owner's choice: redo the cottages, the mill and the chapel; each hamlet builds its own way. Alderhaven, Fold Hall, the stalls and the Net Loft tent are unchanged.

- `client/meadowart.js` draws three isometric kinds whose walls stand on the collision footprint: `meadow_cottage` (`style` stone = Stonefold fieldstone and slate with window boxes and a woodpile; fisher = Saltby tarred/falu-red/blue planks, pantiles, white corner boards, net, oars, lobster pot; thatch = Applewick limewash, timbers, thatch with ridge roll, shutters, roses, apple crate), `meadow_mill` (stone ground floor, boarded loft, wheel and race on the east wall) and `chapel_ruin` (roofless; west gable standing with an empty window, low broken walls, ivy, rubble).
- `v` 0-3 is set per cottage in `DRESSING` (passing it keeps the rng order: the `pop` default is evaluated anyway). Odd `v` turns the ridge so the gable and door face the street; `v` also moves the door and picks roof, wall (Saltby) and door colours. The sprite cache key in `city.js` includes `style`.
- Sunward Vale keeps `vale_cottage` and `watermill`. Every building is 51+ tiles from a seam, so no ghost question. The new kinds glow in the night-light list in `field.js` (generic glow at the anchor, like `house`) and have `worldmap.js` colours; they are NOT in the occlusion cover list (that rule faded the Applewick cottage while the hero stood on the plaza). The ruin is solid (collision box), so its doorway is choked with fallen stone.
- Check: `bash scripts/test-touch-bounded.sh tests/meadow-houses-ui.cjs` (31 checks: isometric reach on the footprint, all ten cottages different, each hamlet's own colours, the field draws each through its new art); `MUTATE=1` (old flat art under the new kinds) must fail.
