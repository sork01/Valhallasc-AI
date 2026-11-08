# The Tanglecrown as a shaped, authored zone (zone shapes pilot, 2026-11-08)

Owner request: "for pilot. reshape tanglecrown. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the **Ribbonwild only** (Sunward Vale, the Veyrroot Canopy and the Temple of the Rain Crown stay gates), **keep all portals**, **keep both elites and add one with no quest**, **three outposts**. Pilot only (branch `feat/zone-shapes-tangle`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-tangle-work`, cargo target `zone-tangle-target`, wrapper `zone-tangle-cargo.sh`). The sixteenth pilot zone: 0, 1, 2, 3, 6, 7, 8, 9, 13, 14, 15, 16, 19, 21, 22, 45.

## The shape

At k = 1.0 the atlas outline is grid 304 with 32,708 land tiles (the old square was 144, 20,736 tiles): a wide triangle. Borders: the Ribbonwild on the west (295 tiles, **the seam**), Sunward Vale in the north-west corner (77), the Veyrroot Canopy along the north-east side (246), a 60-tile land edge in the east and a 201-tile coast in the south-east. The painting is a jungle cut by a net of pale trails: a trunk road with a junction, a western branch, an eastern fork.

`world/zone-shapes.txt`: `designOnly` + **`rebuild`** (the old 144 square does not fit inside the outline, so nothing is moved: `tangle_design.restore_and_shift` brings the old people, places, escort and sleepers back from `preshape-22.txt`), `seamWith {22: [21], 21: [45, 22]}`. `seam_roads.ROAD_ZONES` + 22.

## The Ribbonwild ran unchanged (a late seam)

Its `ribbon_tangle_gate` became the seam. `ribbon_design.LATE_SEAMS = {22}` keeps the masks (the phantom gate keeps its discs and its road, so the seeded scatter is identical); `drop_near_seam` removes the 4 spawns within 7 tiles of the border and the loose scenery within 2.5; its exit routes skip the seamed portal. **A plain seam draws neighbour scenery with art but no people**, so the Pavilion's Spark master and mailbox stepped back within the camp (offsets `(6, 9)` -> `(-3, 9)`, `(4, -9)` -> `(-6, -9)`: 27 and 25 tiles from the border; the keeper stands 21). `ribbon_design.check` now fails on any person or art-less object within 20 tiles of the new seam. Cross-zone map diff against `HEAD`: see the wiki page.

**The crossing is at the old gate's place.** `seam_roads` weighs both seam portals' points, which `make_seams` puts in the middle of the border (next to the Pavilion, 130 tiles from where the roads end). `tangle_design.aim_seam` moves both seam portals to the border row y = 253.3 where the Ribbonwild's south-east road ends (Ruben Marigold says the Tanglecrown road comes in south-east of Garland Rest). The Tanglecrown's road R_S ends on the border; the pass then lays only the 3-point Ribbonwild stub (crossing cost 3.2).

## The design (`scripts/tangle_design.py`, `tangle_content.py`)

- **Banyan Landing** (the city, the old 40 x 40 rectangle) stands at (122, 190) in the west-centre, 52 tiles from the seam. Roads: the trunk road from the Veyrroot gate (184, 89) down through Rootgate Post to Stilt Post; the north-west road from the Sunward gate (58, 50) past the Hanging Gardens to the Landing's north side; the east fork from the trunk junction through Drumroot Post to the temple camp; a south road from the Landing to the Ribbonwild seam, with a link to Stilt Post.
- **Outposts** (each: two givers, a trader, a Spark master, a mailbox): **Rootgate Post** (170, 120), **Drumroot Post** (214, 128), **Stilt Post** (160, 218). **Rainstep Camp** (254, 146) is built round the temple door moved whole (`DOOR`, 254, 134): the scholar, the Meeting Stone, a master and a mailbox. Five Spark masters, linked to each other and across the three gates and the seam (`tangle_design.link_travel`, targeted: a global sync rewrites every pilot zone).
- **Elites** stand in pockets 20+ tiles clear of every road, hub, place, person and gate: the **Jade Anaconda** (79, quest) in the Jade Basin at (128, 104), the **Crown Jaguar** (80, quest) on the High Jaguar Terrace at (190, 162) ringed by seven jaguar totems, and the new **Hollowroot Centipede** (77, no quest) in the Strangler Maze at (205, 192): three rings of strangler figs with gaps on opposite sides (r 15, 21, 27).
- **Fourteen regions** (nearest seed, warped): The Sunward Stair, The Hanging Gardens, The Jade Basin, The Orchid Rise, The Kapok Gate, The Landing Glades, The Gliders' Reach, The High Jaguar Terrace, The Drum Terraces, The Rain Crown Steps, The Strangler Maze, The Blackwater Edge, The Mangrove Stair, The Seam Verge. Nine ground classes (`tangleClassGround`, `TANGLE_MINI` in `field.js`): canopy, loam, moss, blackwater mud, jade stone, orchid bloom, leaf litter, coast clay, fern floor. Nine pools of blackwater (`jungle_water` discs), the Jade Basin's pool, two root bridges.
- **Scenery:** the existing kapok, strangler fig, banana palm, hanging vines, fern, orchid, glow mushroom, jungle water, jade pool, root bridge, jaguar totem, banyan lodge and boardwalk stall. Every kind draws through `City.art` (checked), so every one ghosts across the seam.
- **Spawns:** about 110 live + sleepers: mantises in the north and west, gliders over the middle, caimans in the blackwater, gorillas on the eastern terraces; none within 22 tiles of the seam.

## Quests (32; the old 18 keep their ids, 14 are new)

- **Old, kept:** `tangle_welcome`, `_mantises`, `_gliders`, `_caimans`, `_drums`, `_anaconda`, `_jaguar`, `_temple`, `_crown_trials`, `_crown_final`, `_patrol`, `_onward`, `_banyan_1`-`_banyan_4` (the hatchling escort: Tamsin now waits on the west road at (110, 144) and walks three waypoints to Mara Vines at the Landing), `es_18` (its place and sleeper moved to (90, 176)), `es_go_18`. Four descriptions were reworded where the geography changed.
- **New:** `tangle_lh_hold` and `tangle_rounds` (the Landing); per outpost four: a walk with kills, a bring, a hold circle, a final walk (`tangle_rg_*`, `tangle_sp_*`, `tangle_dr_*`). Four hold circles wake two waves of two sleepers each. Rewards in `quest_gear_rewards.py` (a green at the end of each chain). All Swedish written by hand.

## New elite: the Hollowroot Centipede (`rootcentipede`)

Level 77, no quest, material `hollow_chitin`. A giant jungle centipede: thirteen banded plates (olive and rust, pale belly), a rust head under an olive hood with three glowing eyes, long antennae and two venom-tipped sickle fangs. `scripts/tangle_elite_redraw.py` (a native PixelFlow source, frame 190 x 119, eight distinct attack and eight distinct death frames), manifest `client/assets/tangleelites.txt`. Stats are a first guess: 2,350,000 HP, 19,000 damage, speed 2.5, enrage `[180, 0.2, 3.0]`.

## Checks

`cargo test tanglecrown_tests` + `ribbonwild_tests` + `zone_shape` + `emberwake_tests`; `python3 tests/seam-roads.py`; `python3 scripts/tangle_design.py plan OUT.png`; `SEAMLESS_SOFT=1 REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/tangle-design-ui.cjs` (`MUTATE=1` serves the pilot's previous `field.js`: the ground-class check must fail).

## Not done / open

- The centipede's stats and look are first passes (judge on an in-game screenshot).
- Older Tanglecrown suites (MCP `tanglecrown`, `tests/tanglecrown-ui.cjs` if present) use the old coordinates.
- Not judged in play: walking time between hubs, spawn density, the Strangler Maze's rings.
