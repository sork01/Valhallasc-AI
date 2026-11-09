# The Veyrroot Canopy as a shaped, authored WILD zone (zone shapes pilot, 2026-11-09)

Owner request: "for pilot. reshape veyroot. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against **the Tanglecrown and the Lapis Erg** (Sunward Vale stays a gate), **"veyroot should be wild with enemies. heartwood should be a peaceful city"**, and for Heartwood **"remake and reshape heartwood. it should be the main city in the big tree. like a main city like skaldholm. people live in there."**, three outposts and the old quests kept. Then: "go ahead, veyrroot first". Pilot only (branch `feat/zone-shapes-veyrroot`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-veyrroot-work`, cargo target `zone-veyrroot-target`, wrapper `zone-veyrroot-cargo.sh`). The eighteenth pilot zone: 0, 1, 2, 3, 6, 7, 8, 9, 13, 14, 15, 16, 19, 21, 22, 23, 25, 45. **This document covers step one, the Veyrroot; Heartwood (zone 24) is step two** and still the old 96 square.

## The shape

At k = 1.0 the atlas outline is grid 352 with 64,756 land tiles (the old square was 128, 16,384): a wide wedge, the largest zone after the Wyrdwood. Borders: **the Lapis Erg along the whole north side (280 tiles, a seam)**, **the Tanglecrown along the south-west (245 tiles, a seam)**, Sunward Vale in the west (12 + 71 tiles, the gate) and a coast on the east. The painting shows teal canopy masses cut by pale trails, a big sandy glade in the west and the Great Tree on a round green clearing in the middle-south (atlas marker (210, 211)).

`world/zone-shapes.txt`: `designOnly` + **`rebuild`** (the old 128 square is not moved: `veyrroot_design.restore_and_shift` brings the old people, places and quests back from `preshape-23.txt`), `seamWith {22: [21, 23], 23: [22, 25], 25: [23]}`. `seam_roads.ROAD_ZONES` + 23 and 25. Order in `zone_shapes.apply`: after the Lapis Erg's design.

## The Tanglecrown and the Lapis Erg ran unchanged (late seams)

Their `tangle_worldheart_gate` and `lapis_canopy_gate` became the seams. `LATE_SEAMS = {23}` in both designs keeps the masks (the gates keep their discs and their roads, so the seeded scatter is identical). Cross-zone map diff against the pilot's previous tip (`git show HEAD:world/map.txt`), zone by zone:

- **Tanglecrown:** 12 spawns within 7 tiles of the border went (`drop_near_seam`); three **art-less objects** stepped back (`greenmeadow_design.step_back_artless`: Rootgate Post's notice board, Drumroot Post's notice board and bench, because a plain seam draws neighbour scenery with `City.art` but no art-less objects, and none may stand within 20 tiles of the seam); `exitRoutes` lost the seamed gate; two Spark masters gained a link. Nothing else differs apart from the void pieces re-cut for the seam margin.
- **Lapis Erg:** 11 spawns went; no object moved (the nearest person is 23.6 tiles from the border); one Spark master gained a link.
- **Sunward Vale and Heartwood:** one arrival coordinate each (Sunward's way into the Veyrroot, Heartwood's way back to the arch). Every other zone is identical.

`step_back_artless` runs after `content.install` (so it sees the people's final places) and keeps a spot 2.4 tiles from every person and `r + 2` from every place; inside the camp rectangle first, then up to six tiles beyond it.

**The crossings are at the old gates' places.** `veyrroot_design.aim_seams` puts both seam portals on the border at the column where the neighbour's road ends (Veyrroot x 118.5 against the Tanglecrown, x 191.5 against the Lapis Erg; Tanglecrown gate x 184.5, Lapis gate x 135.5), as `tangle_design.aim_seam` did for the Ribbonwild. The Veyrroot's roads end on the border there.

## The design (`scripts/veyrroot_design.py`, `veyrroot_content.py`)

- **Rootfoot** (the city, a 44 x 40 sanctuary) at (210, 241) at the foot of the Great Tree (a solid trunk, r 9, at (210, 207)). The Hollow Arch to Heartwood stands at (210, 222) with its scenery behind it (an r 0 object still pushes a walker out of a point: the way in and out runs south of it). The old Canopy people stay (ids are saved progress): the matriarch, ranger, healer, trader, the Meeting Stone, the Spark master and the mailbox.
- **Outposts** (each: two givers, a trader, a Spark master, a mailbox): **Gladewatch Post** (100, 192) in the Sunlit Glade, **Rootstair Post** (206, 98) below the Twin Roots (its second giver is the old nectar keeper Miri Nectar), **Eastbark Post** (296, 198) on the eastern coast. **Sunleaf Lookout** (252, 146) is built round the Sunleaf Observatory: the lookout Sela, a master and a mailbox. Five Spark masters, linked to each other and across the seams and the Sunward gate (`veyrroot_design.link_travel`, targeted: a global sync rewrites every pilot zone).
- **Roads:** the Sunward road from the west gate (47, 130) through Gladewatch to Rootfoot; the Tanglecrown road from the seam (118.5, 279) up to meet it; the north road from Rootfoot past the Lookout and Rootstair Post to the Lapis seam (191.5, 53); the east road to Eastbark Post; a link from the Lookout; branches to the Hanging Gardens, the Hive Crown, the Sap Flats, the Eastern Roots and the Twin Roots.
- **Elites** stand in pockets 19+ tiles clear of every road, hub, place, person and gate: the **Lantern Queen** (82, quest, flies) at (132, 104) in the north-western canopy ringed by buttress roots, the **Heartbark Colossus** (84, quest) at (312, 118) in the Eastern Roots, the **Amber Sap Golem** (83, no quest) at (262, 266) on the southern sap flats.
- **Fourteen regions** (nearest seed, warped): The Moss Stair, The Sunlit Glade, The Hanging Gardens, The Hive Canopy, The Twin Roots, The Rootstair Reach, The Sunleaf Rise, The Eastern Roots, The Bark Coast, The Heart Clearing, The Amber Sap Flats, The Fernbreak, The Tangle Verge, The Lapis Verge. Nine ground classes (`veyrClassGround`, `VEYR_MINI` in `field.js`): canopy moss, loam, leaf litter, pale pollen glade, amber sap, root bark, bright fern, deep shade, teal moss.
- **Scenery:** the existing worldtree kinds (buttress root, hanging pod, lantern vine, epiphyte garden, canopy market, suspended garden, Hollow Arch, observatory, Great Tree) plus four wild kinds in `client/veyrrootart.js` (`vr_canopy_tree`, `vr_fernbank`, `vr_amber_bloom`, `vr_moss_stone`). Every kind draws through `City.art`, so every one ghosts across the seams.
- **Spawns:** 199 in all (the four existing level-80 families, unused until now: moss lemurs in the west and the gardens, sap beetles in the glade and on the sap flats, lantern hornets in the north and the hive canopy, bark mimics in the east and round the tree), the three elites, 16 sleepers at the four hold circles; none within 10 tiles of a seam. The four families carry the stats they always had (no `elite-power` entries, no multiplier): first guesses for the owner to judge.

## Quests (25; the old 9 keep their ids, 16 are new)

- **Old, kept:** `heart_welcome`, `_walkways`, `_lanterns`, `_gardens`, `_market`, `_circuits`, `_patrol` (retitled and reworded where the geography changed: the Canopy was a city of ring decks), `es_19` and `es_go_19` (the Empty Seat's memory now stands at the foot of the Great Tree).
- **New:** `veyr_rf_hold` and `veyr_rounds` (Rootfoot); per outpost four: a walk with kills, a bring, a hold circle, a final walk (`veyr_gw_*`, `veyr_rs_*`, `veyr_eb_*`); the two elite quests `veyr_queen` (3 players) and `veyr_colossus` (5 players), with class choices and a blue reward. Rewards in `quest_gear_rewards.py` (a green at the end of each chain). All Swedish written by hand (97 texts, 15 kept names).

## New elites (`scripts/veyr_elite_redraw.py`, manifest `client/assets/veyrelites.txt`)

Three native PixelFlow sources, each with its own frame and eight distinct attack and eight distinct death frames (owner rule: unique and mean):

- **Lantern Queen** (`lanternqueen`, level 82, quest, flies; frame 160 x 144): a wasp queen the size of a wagon, a dark chitin thorax striped with amber, four glass wings, a head with two big slanted red compound eyes under a scowling ridge and serrated mandibles, a fat abdomen that burns like a lantern with a hooked black stinger. 3,000,000 HP, 23,500 damage, speed 3.0.
- **Heartbark Colossus** (`barkcolossus`, 84, quest; 130 x 144): a walking grove, a hunched trunk of split bark with a crown of moss and fungus, two root-arms with knotted knuckles, a head sunk between the shoulders with a jagged brow, glowing green eyes and a gaping splinter mouth. 4,100,000 HP, 29,500 damage, speed 1.9.
- **Amber Sap Golem** (`ambergolem`, 83, no quest; 122 x 140): a faceted hulk of hardened sap with whole insects trapped dark inside, a molten core in its chest, amber spikes on its shoulders, a wedge skull with two hollow slits. It breaks into chunks when it dies. 3,700,000 HP, 27,000 damage, speed 1.7.

All stats and the art are first passes. Materials `queen_amber`, `heartbark_slab`, `golem_amber`; enrage `[180, 0.2, 3.0]` each (`world/enrage.txt`).

## Checks

`cargo test veyrroot_tests` (11: layout and families, the two seams and their roads, the Sunward gate and the arch, a hero walking over both seams and back, reachability, the three outposts, the quests, the elites, the Empty Seat and mailboxes, registration, exit routes) + `zone_shape` + `lapis_tests` + `tanglecrown_tests`; `python3 scripts/veyrroot_design.py plan OUT.png` (needs `VEYR_WORLD=<cached shaped world>`); bounded `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/veyrroot-design-ui.cjs` (`MUTATE=1` serves the pilot's previous `field.js`: the ground-class check must fail). Two `sync-world` runs byte-identical.

## Not done / open

- **Heartwood (zone 24) is still the old 96-square peaceful interior** (step two: the main city, owner request above). Its old tests (`worldheart_tests`) now describe the Veyrroot as wild.
- The three elites' stats and look are first passes (judge on in-game screenshots); their size in play was not judged. Walking time between hubs, spawn density and the Hive Canopy / Eastern Roots pockets were not judged in play.
- Older suites that teleport into the old Canopy coordinates (`tests/worldheart-ui.cjs`, MCP `worldheart`) are stale.
- Failures that are not this work (identical names on the previous pilot binary): four to six `compact_atlas` tests, two `sunward_tests`, `yearwheel_tests::four_seasons_*`, `empty_seat` / mercenary-price tests, `mount_speed`, several `world::tests::*` travel-link tests.
