# Cairnspine as a shaped, authored zone (zone shapes pilot, 2026-11-09)

Owner request: "for pilot. reshape cairnspine. and remake the zone and quests to fit the new shape. no fillers." Owner answers (AskUserQuestion): seamless against **the Prismwaste only** (the Frostwake Shelf crossing stays a gate), **keep all three elites and add a fourth with no quest**, **keep the Thunderheart Gate door and rebuild the hub**, three outposts. Pilot only (branch `feat/zone-shapes-cairn`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-cairn-work`, cargo target `zone-cairn-target`, wrapper `zone-cairn-cargo.sh`). The nineteenth pilot zone.

## The shape

At k = 1.0 the atlas outline is grid 272 with 32,469 land tiles (the old square was 168): a mountain shield. The Prismwaste lies along the whole south-west diagonal (247 tiles, the seam), the Frostwake Shelf along the east (283 tiles, a gate), a coast in the north (211 tiles). The painting shows a snow-capped massif in the north (the Thunderheart), switchback terraces in the middle and a tapering toe in the south.

`world/zone-shapes.txt`: `designOnly` + `rebuild` (the old 168 square cannot sit inside the outline, so `cairn_design.restore_and_shift` brings the old people, places and quests back from `preshape-27.txt`), `seamWith {27: [14], 14: [13, 15, 19, 27]}`. `seam_roads.ROAD_ZONES` + 27. Order in `zone_shapes.apply`: after the Heartwood block.

## The Prismwaste ran unchanged

`prism_design.LATE_SEAMS = {19, 27}`: the masks are unchanged (the gate keeps its disc and its road), only the 12 spawns within 7 tiles of the new seam go and the void pieces along the border are re-cut for the seam margin. No people, art-less object or place stands within 22 tiles of the seam on the Prismwaste side (checked). Both seam portals stand where the Prismwaste's road already ended (its old gate at (225.88, 150.0), Cairnspine (97.88, 178.0)); the seam road pass laid its crossing there (cost 4.4).

## The design (`scripts/cairn_design.py`, `cairn_content.py`)

- **Boulderwatch** (the city, 42 x 36) at (156, 170) in the middle of the pass: the old warden, healer, surveyor, trader, peak scout, Spark master and mailbox keep their ids. Three isometric watchhalls, a signal beacon, a notice board, a fire.
- **Outposts** (built of the same isometric watchhalls; each: two givers, a trader, a Spark master, a mailbox): **Singing Cairn Post** (96, 92) on the western height (the stone singer Edda moved in), **Whitebark Post** (140, 112) in the middle heights (the grove keeper Tala), **Stormgate Camp** (176, 58) on the northern ridge (the windseer Oren and the Meeting Stone).
- **The Thunderheart Gate** keeps its id, its dungeon (zone 35) and both ways home (re-aimed); the door stands at (160, 30.5) at the head of the northern ridge, 28 tiles from the camp.
- **Roads:** the Prismwaste road from the seam to Boulderwatch; the Four Turns (switchbacks north to the Whitebark Post); west to the Singing Cairn Post and its cairn; north-east to the Stormgate Camp and on to the gate and the Condor Spires; east to the Frostwake rim gate; a toe trail south; a trail east to the Adder Stones; a grove trail.
- **Elites** stand in pockets awareness + 3 tiles clear of every road, hub, place, person and gate: the **Cairn Behemoth** (93, quest) in the southern toe (160, 244), the **Whitebark Titan** (94, quest) in the Whitebark Wood (130, 48), the **Storm Condor** (95, quest) on the north-eastern spires (212, 30), the **Avalanche Bear** (92, NO quest) in the north-western Hollow Peaks (62, 52).
- **Fourteen regions** (nearest seed, warped): The Boulderwatch Terraces, The Prism Verge, The Four Turns, The Walking Toe, The Adder Stones, The Scree Run, The Frostwake Rim, The Whitebark Slopes, The Whitebark Wood, The Singing Heights, The Hollow Peaks, The Stormgate Ridge, The Condor Spires, The Cold Coast. Nine ground classes (`cairnClassGround`, `CAIRN_MINI` in `field.js`): blue slate, ochre terrace dust, grey scree, snow, pale ash floor, dark shale, lichen slate, pale stone, black basalt.
- **Scenery:** the existing Cairnspine kinds (boulder, pebble, dead tree, slate spire, windbanner, watchhall, signal, stone circle, white grove, eyrie, boulder altar) plus two new (`cairn_stack`, `cairn_lichen_rock`) in `client/cairnart.js`. Every kind draws through `City.art`, so every one ghosts across the seam. **The Thunderheart Gate scenery is redrawn isometric** (owner rule: gates are never a flat front elevation): a plinth, two slate pillars with bronze bands, a lintel and the stormlight ring in the wall plane.
- **Spawns:** ~110 of the four existing families (scree ferrets on the low scree, ibex on the slopes, ravens on the heights and the coast, adders on the warm stones), the four elites and 16 sleepers at the four hold circles; none within 10 tiles of the seam.

## Quests (29; the old 15 keep their ids, 14 are new)

- **Old, kept:** the whole chain (`cairn_welcome` ... `cairn_thunder_final`, `cairn_patrol`, `cairn_onward`, `es_23`, `es_go_23`); descriptions reworded where the geography changed (the elite quests now say where each lives). The Empty Seat's three oath bells moved rigidly with the Singing Cairn.
- **New** (`crn_` ids, people `cn_`): `crn_bw_hold` and `crn_rounds` (Boulderwatch); per outpost four: a walk with kills, a bring, a hold circle, a final walk (`crn_sc_*`, `crn_wb_*`, `crn_sg_*`). Rewards in `quest_gear_rewards.py` (a green at the end of each chain). All Swedish written by hand.

## The new elite (`scripts/cairn_elite_redraw.py`, manifest `client/assets/cairnelites.txt`)

A native PixelFlow source with its own frame (156 x 120, anchor (60, 112), art scale .82), eight distinct attack and eight distinct death frames (owner rule: unique and mean). **Avalanche Bear** (`avalanchebear`, level 92, no quest): a mountain-sized bear with slate-grey fur gone white on the belly and legs, a ridge of jagged blue-white ice spines down its back, small ice-blue eyes under a scowling brow, torn round ears and bone fangs. It rears onto its hind legs with the spines flared on the wind-up, drops its whole front half on the strike, and dies by sinking onto the snow while the spines shatter shorter and the colour drains to grey from the rump forward. 4,100,000 HP, 28,500 damage, speed 2.6; material `avalanche_claw`; enrage `[180, 0.2, 3.0]`. Stats and art are first passes.

## Checks

`cargo test cairn_tests` (11) + `zone_shape` + `prism_tests`; `python3 scripts/cairn_design.py plan OUT.png` (`CAIRN_WORLD=<cached shaped world>`); bounded `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/cairn-design-ui.cjs` (`MUTATE=1` serves the pilot's previous `field.js`: the ground-class check must fail; `MUTATE=seam` the one from before the seam-blend fix: the same-point check must fail).

## Not done / open

- The bear's stats and look are first passes (judge on an in-game screenshot); walking time between hubs, spawn density and the toe / Hollow Peaks pockets were not judged in play.
- The Frostwake Shelf was shaped later the same day (2026-11-09): its design lists 27 in `seamWith` and the rim gate became the second seam (`cairn_design.aim_frostwake_seam`, `LATE_SEAMS = {26}`).
- Older suites that teleport into the old Cairnspine coordinates (`tests/cairn-ui.cjs`, MCP `cairn`) are stale.
