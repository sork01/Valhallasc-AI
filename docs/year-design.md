# The Yearwheel as a shaped, authored zone with a seamless vault to Sunward Vale (zone shapes pilot, 2026-11-09)

Owner request: "for pilot. reshape yearwheel. and remake the zone and quests to fit the new shape. no fillers. Seamless through the vault to sunward vale. This one could keep the 2.8 tiles per pixel. Just have the vault towards sunvale be seamless". Owner answers (AskUserQuestion): **keep the four season towns and add three outposts**, **keep the 12 seasonal elites and add one with no quest**, **the same isometric wall on the Yearwheel side of the Lapis and Frostwake borders** (they already have it on theirs, no gates). Pilot only (branch `feat/zone-shapes-year`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-year-work`, cargo target `zone-year-target`, wrapper `zone-year-cargo.sh`). The twenty-second pilot zone.

## The shape and its own scale

The Yearwheel is the only zone NOT at k = 1.0: `world/zone-shapes.txt` has `zoneScale {28: 2.8}` (`zone_shapes.zone_scale`). The old 400 square fits from k = 2.3; at 2.8 the outline is **grid 888 with 385,949 land tiles** (the old square held 160,000), 614 x 882 tiles: a tall wheel with the sea along the north and the east, Frostwake on the west (857 tiles of border), the Lapis Erg on the south-east (366) and Sunward Vale on the south-west (285). It is `designOnly` (the old layout is moved as a block, not rebuilt: Emberwake's design still reads the old healer) and `seamWith {28: []}`: no seam with anyone. A seam needs equal scales, a vault does not (it is one doorway: a whole-tile translation).

World map and fog already follow `shape.k` / zone size; the minimap, the weather, the city floor and the sky read the new `zdef.yearCentre` ([440, 480]) instead of the old hard-coded 200.

## The vault to Sunward Vale (the only crossing)

Sunward's approved design is untouched except `path_20_28` (now a `Portal.vault`) and `shape.vaultRegions` (`year_design.late_vault`): its objects, spawns and roads are byte-identical (cross-zone map diff).

- **One frame, one whole-tile shift** (`vault_frame`): Sunward's arch (262.12, 16.65) sits 1.7 tiles inside its border; the same atlas point in the Yearwheel frame is shifted by the integer vector (21, 862), chosen to minimise the perpendicular error. `path_20_28.vault = [21, 862]`, `path_28_20.vault = [-21, -862]` (exact negatives), `vault_half` 5.2, the gate 3 tiles past each arch (Skaldholm's convention), `walk` north / south.
- **The border lines agree only near the doorway.** Same atlas line at two scales: the curvature differs by 2.8, so the lines drift 3 tiles apart 40 tiles from the vault. `match_border` therefore makes the Yearwheel's floor end **exactly** where Sunward's begins for 46 tiles each side (column by column, `tests`: our last land row + 1 = Sunward's first), then eases back to the atlas line over 44 tiles (largest edit 5 tiles); `shape.edges`, `shapeFloor`, `shapeEdge` and the walls follow.
- **Pocket:** walkable ground across the arch past our own line (`repocket`: the void pieces are cut again), so a walker can step up to the arch and be carried over.
- **Regions** (`regions_for`): each frame has one `shape.vaultRegions` entry whose `city` polygon is what the OTHER zone owns beyond the line (90 tiles deep, +-40 tiles along it, starting 0.5 tile inside our own land so no sliver can show). Both zones take the existing shaped-zone branch of `Field.vaultRegions()`; nothing city-specific (`hide`, `inSquare`) is used. Each zone draws the other's ground, scenery and Sunward's wall through the opening; each has an `exitArches` record for the same arch.
- **Spark links:** Millbridge and the Wickerfield Post link to Springmere, exactly as before; the outposts and towns link among themselves, every link both ways.

## The wall

The wheel's own isometric `rampart` (645) and `tower` (59) along the whole Lapis and Frostwake borders and along the Sunward border outside the vault's span (inside it Sunward's own wall stands on the line), 1.7 tiles inside the border, pieces 2 tiles apart. No gate. There is a 3.4-tile jog where our wall meets Sunward's ghost wall (40 + 8 tiles from the vault); it is off screen from the doorway.

## The design (`scripts/year_design.py`, `year_content.py`)

- **Four towns** keep their people, quests, doors and Spark masters (their offsets from their plazas): Springmere (300, 770, the city, near the vault), Solhaven (620, 660), Harvestwatch (620, 300), Rimehold (320, 300), round the **Equinox Crossing** (440, 480) with the Black Hour Foundry's door and Sigrun/Torv beside the axle. **Three outposts** (two givers, a trader, a Spark master, a mailbox, two lodges each): Wheelmark Post (336, 128, winter), Tidehollow Camp (690, 470, autumn coast), Lowfall Rest (480, 650, summer plain).
- **Four sealed doors** keep their ids and offsets: the Blooming Labyrinth (232, 598), the Solar Crucible (702, 592), the Amber Archive (702, 402), the Silent Solstice (262, 384, with the Dawn Vigil). Every dungeon's way home arrives beside its door.
- **Roads:** every road enters a town along one of three clear rays (west, east, north-east of the plaza: the old people stand on the others); the vault road runs north to Springmere; a spoke from each town to the Crossing; a rim round the four towns; the outposts by a hook round their south side into the east corridor.
- **Thirteen elites** (awareness + 3 tiles clear of everything walked to, auto-snapped): the old 12 with their quests (three a season) and the **Equinox Stag** (level 98, no quest, first-guess stats `(7.4 M hp, 46,000 attack)`, material `equinox_antler`, enrage `[180, 0.2, 3.0]`, native PixelFlow art `scripts/year_elite_redraw.py`: a tawny stag whose antlers carry the four seasons in turn, eight distinct attack and death frames).
- **Eighteen regions** (the four quarters have three to five each), the four seasonal grounds (`yearSeason` quadrants round `yearCentre`), 3,385 objects of the old season families (`v` follows the palette), **450 ordinary spawns** (1.1 per 1,000 tiles, one family per season) and 16 sleepers at four hold circles.

## Quests (55; the old 40 keep their ids, 15 are new)

New ids start `yrs_` (at most 19 characters), people `yo_`: a hold at Springmere (`yrs_sp_hold`), the three outposts' chains (walk with kills, a bring, a hold circle, a final walk: `yrs_wm_*`, `yrs_th_*`, `yrs_lf_*`), `yrs_rounds` (the three outposts) and `yrs_crossing`. All Swedish written by hand (91 texts); place names stay English.

## Checks

`cargo test yearwheel_tests` (7: data, outposts, enemies and the 13 elites, the walls, the vault's frames and the cell-for-cell border, a walk through the vault both ways, everything reachable from the vault), `sunward_tests` (the vault walk moved here), `zone_shape_tests`, `lapis_tests`, `frostwake_tests`, `cairn_tests`; `python3 scripts/year_design.py plan OUT.png` (`YEAR_WORLD=<cached shaped world>`, `YEAR_LAX=1` lists problems); bounded UI `tests/year-vault-ui.cjs` **in parts** (the pilot client is near the 1.5 GiB cap): `PART=pair SS=0.6:0`, `PART=pair SS=1.2:3`, `PART=scene`, `PART=walk DIR=1`, `PART=walk DIR=-1` (`VW=960 VH=600`; `MUTATE=1 PART=pair` serves a `field.js` without the vault drawing and fails: 44 vs 9.6 mean diff). Same point from both frames: diff 7.8 vs noise 7.1 (0.2% of pixels off); 43 / 43 scenery objects identical around the arch; the crossing step 7.1 against ordinary 6.1.

## Not done / open

- Spawn density, walking times between the hubs and the elite pockets were not judged in play. The Equinox Stag's stats are a first guess and its art a first pass.
- Music and weather at the crossing are not handled (as at every vault). The Yearwheel's own chunk cache is large (888 grid): the client holds 20 MB of `world.js` now.
- `blackhour_data_and_actual_collision` and `blackhour_door_opens_only_after_the_four_hour_shards_are_handed_in` fail identically on the previous pilot binary (enrage 760 vs 608; the Solstice door's quest), not touched.
- Older suites that teleport into the old Yearwheel coordinates (MCP `yearwheel`, `tests/yearwheel-*`) are stale.
- Sunward's Hollow door scenery is still the old flat elevation (owner rule: gates are isometric).
