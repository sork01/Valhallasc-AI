# Sunward Vale as a shaped, authored river valley (zone shapes pilot, 2026-11-09)

Owner request: "for pilot. resape sunward vale. and remake the zone and quests to fit the new shape. no fillers. a wall with a vault opening towards yearwheel". Owner answers (AskUserQuestion, then in words): **every shaped neighbour is seamless** ("all should be seamless"), **keep Old Honeyjaw and the Wicker Warden and add one elite with no quest**, and (asked when the audit found Bankhold on the new seam) **move Bankhold inland**. Pilot only (branch `feat/zone-shapes-sunward`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-sunward-work`, cargo target `zone-sunward-target`, wrapper `zone-sunward-cargo.sh`). The twenty-first pilot zone.

## The shape

At k = 1.0 the outline is grid 352 with 87,097 land tiles (the old square was 128, 16,384 tiles): a broad green valley. Frostwake lies along the north-west (175 tiles), the Yearwheel along the north-east (102, the wall), the Lapis Erg east (177), the Veyrroot Canopy south-east (173), the Tanglecrown south (77), the Ribbonwild south-west (153) and the Stormglass Flats along the whole west side (288). The painting shows a net of tan trails (a trunk road down the middle), ten big oaks and a river across the middle.

`world/zone-shapes.txt`: `designOnly` + `rebuild`, `seamWith {20: [19, 21, 22, 23, 25, 26]}` and 20 in each of those six rules. `seam_roads.ROAD_ZONES` + 20. Runs in `zone_shapes.apply` after Frostwake's design.

## Six seams, and the neighbours ran unchanged

All six approved designs gained 20 in `LATE_SEAMS` (masks unchanged, the old gate keeps its discs and road), call `drop_near_seam` / `step_back_artless` for it (`greenmeadow_design.late_targets`, `is_seam_portal`) and no longer demand the Sunward gate as a rim gate. Sunward's design stands both portals of each seam where the neighbour's own road already ends (`PARTNER_ROAD_END`, `aim_seams`). Proof: a cross-zone map diff against the committed pilot map shows only the seam portal, its exit route, near-seam spawns, re-cut voids and Spark links in the six neighbours, plus the arrival re-aims of the Elder Hollow and the Yearwheel; `python3 tests/sunward-late-seams.py` audits every partner (no person or art-less object within 20 tiles of the Sunward seam, no loose scenery within 2.5, no spawn within 7): 0 hard problems.

**Bankhold moved** (Stormglass outpost, centre 272,150: 3 tiles from the seam, with three people): `storm_design.late_move_bankhold` translates it 56 tiles west beside the Eye Basin (216,150) and the Wall Circle with its four sleepers 12 tiles west, as a LATE edit of the finished design (the approved scatter is not redrawn; scenery and spawns that now stand inside the new hub went, the old stub road was replaced). Four quest texts and one dialogue were re-worded (`storm_content.py`), Swedish by hand. Reported, not moved: ambush sleepers of the Ribbonwild's Pavilion circle (7.9 and 8.7 tiles) and of Stormglass's Wall Circle (12.6 and 13.6 tiles) stand near the seam; they sleep until their hold wave.

Because a plain seam draws no people, art-less objects or water, everything in Sunward stands inland of all six borders: people and art-less objects 22+ tiles, hubs 32+, water 18+, spawns 10+. The working valley is a 250 x 255 core inside a calm strip of oaks, hedges and hares.

## The Yearwheel: a wall with a vault

A wall of the city's isometric `rampart` (39) and `tower` (5) along the whole Yearwheel border, 1.7 tiles inside it, with **one opening: the vault** at (262, 11) on the wall line: an `exitArches` arch (`ExitPaths.arch`, half width 5.2) between two towers, and the portal `path_20_28` (`walk` north) with its arrival seven tiles inside; the Yearwheel's `path_28_20` arrives there. `check()` asserts that no cell between the wall and the border is reachable away from the vault.

**Not seamless yet.** The vault is a walked-through portal, not a `Portal.vault` crossing: the Skaldholm machinery (`vaultRegions`, `paintVault`) draws the other zone's ground and scenery across the opening and needs that zone's own `shape.vaultRegions`; the Yearwheel is not shaped, so the view through the arch is the wall's far side only and the hero arrives at the Yearwheel's south gate. The day the Yearwheel is shaped its design can make this a real vault.

## The design (`scripts/sunward_design.py`, `sunward_content.py`)

- **Millbridge** (the town, 44 x 34) at (126, 201) south of the river at the trunk crossing: the old miller, herbalist, carpenter, guide, provisioner, Spark master and mailbox keep their ids; Greenmeadow's isometric `meadow_mill` and five `meadow_cottage` (thatch and stone), a notice board, benches, a market stall.
- **Outposts** (two givers, a trader, a Spark master, a mailbox, two cottages each): **Honeywood Steading** (92, 72) north-west, **Wickerfield Post** (236, 94) north-east, **Elderroot Camp** (176, 66) with the old keeper and the Meeting Stone, the Hollow door (`sun_elder_gate`, art `elder_hollow_gate`) 14 tiles north of it.
- **River:** solid water circles with a pond at each end, fords where a road crosses and two stone bridges (151, 175) and (236, 160); nothing within 18 tiles of a seam.
- **Roads:** a trunk road from the Frostwake crossing down to the Ribbonwild crossing, spurs to every hub and place, one lead to each seam crossing; every hub is entered along its east side.
- **Elites** (clear of everything by awareness + 3): Old Honeyjaw (62, 50) and the Wicker Warden (290, 78) with their quests, and the new **Harrow Ox** (208, 282, level 69, no quest): a plough-ox dragging its rusted iron harrow on a chain. First-guess stats `(2.1 M hp, 16,800 attack)`, material `harrow_horn`, enrage `[180, 0.2, 3.0]`; native PixelFlow art (`scripts/sunward_elite_redraw.py`, `client/assets/sunwardelites*`, eight distinct attack and death frames).
- **Fifteen regions** (nearest seed, warped; river and wall strips overridden) and nine ground classes (`sunwardClassGround`, `SUNWARD_MINI`): meadow, clover, golden leas, oak moss, orchard turf, river silt, heath, stubble, root loam.
- **Spawns:** 304 of the four existing families (hares on the meadows, snails in the orchards, foxes in the oakwoods, badgers by the water and on the heath) and 16 sleepers at the four hold circles.

## Quests (28; the old 14 keep their ids, 14 are new)

New ids start `svs_`, people `sv_`: `svs_mb_hold` and `svs_rounds` at Millbridge, and four chains of four at Honeywood, Wickerfield and Elderroot (a walk with kills, a bring, a hold circle, a final walk); a green reward at the end of the chains. Old texts reworded where the geography changed. All Swedish written by hand.

## Checks

`cargo test sunward_tests` (14), `zone_shape` (87, with six new seam walks), the six neighbours' suites, `python3 tests/sunward-late-seams.py`, bounded `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/sunward-design-ui.cjs` (run `PART=regions`, `PART=rest` and `SEAM_ONLY=1 PARTNERS=<z>` separately: the whole run exceeds the 1.5 GiB cap; `MUTATE=1` must fail the ground-class check).

## Not done / open

- The vault is not seamless (above). The Hollow door's scenery `elder_hollow_gate` is still the old flat front elevation (owner rule: gates are isometric).
- Spawn density, walking times between the hubs and the elite pockets were not judged in play. The Harrow Ox's stats are a first guess.
- `compact_atlas_tests` fail on the pilot already (seam pairs have no `walk`); not touched. Older suites that teleport into the old Sunward coordinates (MCP `sunward`, `tests/sunward-*`) are stale.
