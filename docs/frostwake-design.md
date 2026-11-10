# The Frostwake Shelf as a shaped, authored zone (zone shapes pilot, 2026-11-09)

Owner request: "for pilot. reshape frostwake shelf. and remake the zone and quests to fit the new shape. no fillers. a wall towards yearwheel". Owner answers (AskUserQuestion): seamless against **Cairnspine only** (the Stormglass Flats and Sunward Vale stay rim gates), a **solid wall and no portal** towards the Yearwheel (as on the Lapis Erg), **keep the three elites and add none**, rebuild the hub and add **three outposts**. Pilot only (branch `feat/zone-shapes-frost`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-frost-work`, cargo target `zone-frost-target`, wrapper `zone-frost-cargo.sh`). The twentieth pilot zone.

## The shape

At k = 1.0 the atlas outline is grid 312 with 51,614 land tiles (the old square was 160, 25,600 tiles): a tall shelf. Cairnspine lies along the whole west side (283 tiles, the seam), the Yearwheel along the east (305 tiles, the wall), Sunward Vale along the south (175 tiles, a gate), the Stormglass Flats on the south-west corner (50 tiles, a gate), a short corner touches the Prismwaste and a frozen coast runs along the north. The painting shows pale snow with about a dozen small snowy peaks, a net of blue trails and a paler blue glacier in the south-west.

`world/zone-shapes.txt`: `designOnly` + `rebuild` (the old 160 square cannot sit inside the outline: `frostwake_design.restore_and_shift` brings the old people, places and quests back from `preshape-26.txt`), `seamWith {26: [27], 27: [14, 26]}`. `seam_roads.ROAD_ZONES` + 26. Order in `zone_shapes.apply`: right after Cairnspine's design.

## Cairnspine ran unchanged

`cairn_design.Cairn.LATE_SEAMS = {26}`: the masks are unchanged (its east rim gate keeps its discs and its road), only the five spawns within 7 tiles of the new seam go, the void pieces along the border are re-cut and the portal `cairn_frostwake_gate` becomes the seam (same id, no `walk`). `cairn_design.aim_frostwake_seam` stands both seam portals where Cairnspine's east road already ends (row 118.5); the Frostwake road meets the crossing at (116.7, 115.5) in this frame. Cross-zone map diff against the committed pilot map: only Frostwake, Cairnspine's seam change (portal, exit route, five spawns, voids, one road), the two re-aimed arrivals (Stormglass, Sunward), the Yearwheel closure and the atlas link.

## The wall towards the Yearwheel

A solid wall of the game's own isometric `rampart` (140) and `tower` (12) objects along the whole Yearwheel border, 1.7 tiles inside it, pieces 2 tiles apart so nothing slips between them, a tower at both ends and about every 28 tiles (frosted stone, glacier-blue roofs). **No gate, no arch, no portal**: `close_yearwheel` deletes the `path_26_28` / `path_28_26` portal pair, the Yearwheel's exit route and trail, the atlas link and the Spark links between the two zones (idempotent, and it runs after `compact_atlas` made them). The Yearwheel stays reachable through Sunward Vale (`path_20_28`). `check()` asserts that no cell between the wall and the border is reachable; `cargo test frostwake_tests` pushes a walker at the wall at eleven places.

## The design (`scripts/frostwake_design.py`, `frostwake_content.py`)

- **Frostwake Station** (the city, 44 x 34) at (124, 268) in the south, near both gates: the old captain, healer, surveyor, trader and snow scout, the Spark master and the mailbox keep their ids. Three isometric lodges (new `frostwake_lodge`), a signal, a hearth, a notice board.
- **Outposts** (each: two givers, a trader, a Spark master, a mailbox, two lodges): **Bellward Post** (168, 186) on the western slopes (the bellkeeper Ylva moved in), **Aurora Post** (226, 62) in the north-east (the aurora watcher Vessa) and **Ribwatch Camp** (168, 40) on the northern rim (the leviathan watcher Irik and the Meeting Stone).
- **Gates:** Sunward Vale (`path_26_20`) on the south rim at (170, 303), Stormglass (`path_26_19`) on the south-west rim; both arrivals in the new frame (`path_20_26`, `path_19_26` re-aimed).
- **Roads:** the Cairnspine pass from the seam to the Central Crossing, the Lantern Road north from the Station through the Bellward Post to the crossing and on to the Ribwatch Camp, the east road to the Aurora Post, a link along the north, short spurs to the Mammoth Bells, the Blue Fissures, the Eastern Cliff, the frozen pool, the Deep Ice Rib, the Northern Crack and the obelisk. Every hub is entered through a free corridor (the lodges stand north and west of an outpost plaza).
- **Elites** stand in pockets awareness + 3 tiles clear of every road, hub, place, person and gate (`check()`): the **Bell Mammoth** (88, quest) on the western shelf (112, 206), the **Aurora Manta** (89, quest) under the Eastern Cliff (252, 108), the **Crevasse Leviathan** (90, quest, five players) in the far north-east (240, 20).
- **Fifteen regions** (nearest seed, warped; the wall strip and the coast are overridden): The Station Flats, The Blue Glacier, The Sunward Drift, The Bell Barrens, The Bellward Slopes, The Blue Fissures, The Cairn Rim, The Central Crossing, The Eastern Cliff, The Wheel Wall Verge, The Aurora Reach, The Rib Fields, The Northern Peaks, The Pool Fields, The Frozen Coast. Nine ground classes (`frostwakeClassGround`, `FROSTWAKE_MINI` in `field.js`): powder snow, blue ice, wind-packed crust, deep glacier ice, moraine, aurora-tinted frost, dark slate, the pale blue glacier, shore ice.
- **Scenery:** the existing Frostwake kinds (snowdrift, ice spire, snow pine, ice flower, lantern, crevasse, frozen pool, signal, hearth, obelisk, fossil, mammoth bells, leviathan rib) plus two new in `client/frostwakeart.js`: `frostwake_lodge` (isometric: snow-packed step, dark left wall with a lit window, lighter right wall with the door, snow roof) and `frostwake_peak` (a small snowy peak, 22 of them, 16 placed from the painting). Every kind draws through `City.art`, so each ghosts across the seam; the walkable ground decals (crevasses, frozen pools) stay 17+ tiles off the seam because the neighbour draws no such ground.
- **Spawns:** 159 of the four existing families (hares on the powder, otters at the pools, herons at the crossings and the cliff, crabs in the fissures), the three elites and 16 sleepers at the four hold circles; none within 10 tiles of the seam or the wall.

## Quests (27; the old 13 keep their ids, 14 are new)

- **Old, kept:** `frostwake_welcome` ... `frostwake_onward`, `es_22`, `es_go_22`; descriptions reworded where the geography changed (the elite quests say where each lives; `frostwake_onward` no longer sends anyone across the Erg). The Empty Seat's echo circle `es_22_m` stands east of the Bellward Post with its sleeping foe (the overlay re-places it from the old layout on every sync-world, so the design puts it back).
- **New** (`fws_` ids, people `fw_`): `fws_st_hold` and `fws_rounds` at the Station, and four chains of four at the Bellward Post (`fws_bw_*`), the Aurora Post (`fws_au_*`) and the Ribwatch Camp (`fws_rw_*`): a walk with kills, a bring, a hold circle, a final walk. A green reward at the end of each chain (`quest_gear_rewards.py`). All Swedish written by hand.

## Checks

`cargo test frostwake_tests` (13) + `cairn_tests` + `zone_shape`; `python3 scripts/frostwake_design.py plan OUT.png` (`FROST_WORLD=<cached shaped world>`, 3 s); bounded `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/frostwake-design-ui.cjs` (`MUTATE=1` serves the pilot's previous `field.js`: the ground-class check must fail; `MUTATE=seam` the one from before the seam-blend fix: the same-point check must fail; `SEAM_ONLY=1`).

## Not done / open

- Spawn density, walking times between hubs and the elite pockets were not judged in play. The elites keep their old stats and art.
- Cairnspine's approved elites were placed before this seam existed: the Cairn Behemoth (160, 244) stands 12.6 tiles from the Frostwake border (awareness 17, so a hero who walks across the south-western stretch of the seam steps inside its aggro range) and the Storm Condor (212, 30) 20.1 tiles (awareness 19); the four ambush sleepers and every person are 28+ tiles away. Cairnspine was left unchanged on purpose (an approved zone must not reshuffle); moving the Behemoth's pocket is the owner's call.
- The day the Sunward Vale (20) or the Stormglass Flats (19) crossing becomes a seam, the matching `seamWith` rule must list 26 and `frostwake_design` aim that crossing.
- Older suites that teleport into the old Frostwake coordinates (MCP `frostwake`, `tests/frostwake-*`) are stale.
