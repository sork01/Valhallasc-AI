# Bifrost Reach as a shaped, authored zone (zone shapes pilot, 2026-11-07)

Owner request: "for pilot. reshape bifrost. and remake the zone and quests to fit the new shape. no fillers. keep the portals/updrafts since this place should be inaccessible without them". Pilot only (branch `feat/zone-shapes-bifrost`, off `feat/zone-shapes`). The seventh pilot zone: 0, 1, 2, 3, 6, 7, 16.

## The shape

At k = 1.0 the atlas outline of Bifrost Reach is a rounded wedge (bbox 339 x 371, grid 376, 80,826 tiles inside the outline against the old 25,600) with the Wyrdwood along its long south-west side, the Crags at its short south end, Nacrehold on the south-east and Rán's Deep on the east. The painting shows a ring of cloud round purple sky, **six green islands** joined by **pink rainbow ribbons** and **four pink landing pads**. That is the floor: `scripts/bifrost_geometry.py` reads the islands out of the painted atlas (colour classes, closing and opening, a gaussian smooth) and authors the bridges and pads over the same picture. Walkable ground is 30,921 tiles (4,550 of them bridge and pad), the rest of the outline is open sky.

| island | painted | now |
|---|---|---|
| `nw` Windward Meadow | top left, 6,326 tiles | galehounds (30), Windward Roost, the Windcairn, the first ward, the Western Beacon, **Sköll** |
| `hub` Heimdall's Perch | centre, 6,176 | the old Perch moved whole, the Span door, the Empty Seat circle; a few galehounds and prism golems round it |
| `north` Hall of the Fallen | small, 1,019 | the Hall Gate, the Silent Bell, the Fallen's Vigil ward |
| `ne` the Roc's Eyrie | top right, 5,392 | thunderrocs (35) and einherjar, Eyrie Landing, the Last Ward, the Nest Rod, **Heimdall's Shade** |
| `se` the Stormcrown | bottom right, 5,263 | skyrays (32-33), Stormcrown Station, the Tally Stones, the Station Rod, the Ember Grave Cross |
| `south` the Shardfields | bottom, 2,195 | prism golems (31), the Lightning Spire, the Shardfield, the Cragsfall updraft, the **Shard-King** |

## Gate only: no seams, every crossing an updraft

`world/zone-shapes.txt` has `"gateOnly": [7]`. `zone_shapes.py` honours it in four places: `make_seams` (no seam between a gate-only zone and any neighbour), the seam-margin loop in `apply` (no 2.4 tiles of land past the border, so the Crags' and Wyrdwood's land is byte-identical), `place_portals` (Bifrost's own gates are never sent to `chain_endpoint`), and the back-fill of `tx/ty` (the neighbours' arrival is still written into Bifrost's portal). `apply` moves the old layout into the new frame as a block, regrids the `sky` rows to 376 and **omits `shapeFloor`/`shapeEdge`**: Bifrost is drawn from its `sky` rows as before, the outline only frames the world map and minimap (`shape.T`, `shape.k`). `shape.placeAtSpawn` tells `zone_shapes_migrate.py` to put saved characters at the new spawn.

Non-regression: after the change `map.txt` differs from the baseline only in Bifrost and in six arrival coordinates (`path_1_7`, `sky_gate`, `maelstrom_up`, `path_9_7`, `span_return`, `span_clear`); every other zone is byte-identical.

The four updrafts each stand on their painted pad, gate near the rim facing the neighbour, arrival six tiles in: **Stormrift** (pad south-west, to the Wyrdwood), **Maelstrom** (the orb in the east, Rán's Deep), **Nacrehold** (south-east pad), **Cragsfall** (the Shardfields' southern tip, the Crags). The Span's door keeps its place on the Perch. `ZoneJourney` already draws the wind passage for any crossing into or out of a sky theme, so nothing changed there.

## The design (`scripts/bifrost_design.py`, `bifrost_content.py`)

- **Rigid blocks** from `world/zone-shapes/preshape-07.txt`: the Perch with its eleven people, buildings, lamps, benches, the Span road and door, the Empty Seat circle. The block moves by one offset (107, 58) so it stands on the central island with four tiles to spare. The grave cross and its sleeper move to the Stormcrown. Every id is kept.
- **Bridges** (13) are authored polylines with diagonals; `masks()` asserts every bridge joins two pieces of land. The graph has cycles (the Perch, the Stormrift pad, Windward Meadow and the pylon form a ring; so do the Perch, the Shardfields and the Stormcrown); `design()` proves the cuts that must hold (the Nacrehold pad hangs off one bridge, Windward Meadow, the Hall and the Shardfields each off two).
- **Roads** are A* routes on the floor around the buildings; no scenery within 2.6 tiles.
- **Void** is rebuilt last from the final walkable mask with integer rectangles (the 1.32.7 platform-escape lesson) and checked to cover exactly the empty sky.
- **Spawns** 151 (was 57) by island and band, away from places, camps and gates; **six hold circles** (the three old wards plus the Western Beacon, the Station Rod and the Nest Rod), each waking two or three waves of sleepers.
- **Outposts** (3, each a 28 x 22 sanctuary with two givers, a trader, a Travel Master and a mailbox): **Windward Roost**, **Stormcrown Station**, **Eyrie Landing**. Spark Travel links stay inside Bifrost. `world/mailboxes.txt` is rewritten for all four hubs.
- **Quests:** the old ids all stay (texts rewritten only where the geography changed: the meadow, the Shardfields, the Stormcrown, the pylon, the Hall gate, the Eyrie, the wards) and **14 are new** (`sky_h_*` at the Perch, `sky_wr_*`, `sky_ss_*`, `sky_hl_bell`, `sky_el_*`). Three more `hold` objectives. The old objective kinds are untouched, so saved progress keeps working.
- **Elites** (owner rule: three, two with a quest, one without): **Sköll, the Gale-Alpha** (`skoll`, level 31, quest `sky_wr_alpha`), **the Shard-King** (`shardking`, 33, quest `sky_h_shardking`), **Heimdall's Shade** (`heimdallr`, 35, no quest). Quests are plain with `recommendedPlayers` 3, like the other pilot elites' (no group, no hired fighters). Hard-coded in `world.rs`/`items.rs` like the other pilot elites (60,000 / 110,000 / 140,000 HP, 1,100 / 1,800 / 2,300 damage: **first guesses, the owner tests fights**), respawn 180 s, enrage `[180, 0.2, 3.0]`, materials `skoll_fang`, `shardking_crown`, `heimdallr_horn`. Each stands awareness + 3 tiles from every road, place, person and camp (asserted in the design and in Rust). Art `scripts/bifrost_elite_redraw.py` (montage, preview, build, export, verify), manifest `client/assets/bifrostelites.txt`, PixelFlow sources in `scripts/bifrost_elite_sources.txt` (frames capped at 30,840 pixels by PixelFlow: Sköll 192 x 124, the others 160 x 192): a storm-black wolf with a swept silver ruff and one white-hot eye, a violet-and-cyan crystal golem with a crown of rainbow shards, a ghost in pale plate with a winged helm, a spear and the broken Gjallarhorn. Eight distinct attack and death frames each. **First-pass art: judge it in the game.**
- **Swedish** written by hand for every new text (102 entries).

## Checks

`cargo test sky_tests` (19: the old tests rewritten for the new map plus `bifrosts_three_elites_...`, `the_three_outposts_...`, `every_updraft_lands_on_walkable_floor_...`, `bifrost_is_gate_only_...`), the atlas tests that name Bifrost (`compact_atlas_bifrost_*`, `compact_atlas_city_archways_...`) and the three `skybridge_*` tests that enter and leave through the Span door. `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/bifrost-design-ui.cjs` (hub and outposts name themselves, every pad, every elite draws; pictures in `test-results/bifrost-design/`).

Stale before this change and fixed on the way: the gold assertion in `every_bifrost_monster_...` ignored `MOB_GOLD_SCALE`; the Skaldholm gate count in the Perch test.

## Not done / open

- The elites' stats are first guesses and no fight test covers them; the art is a first pass.
- Not judged in play: the walking time between islands (the longest ribbon is 90 tiles), the spawn mix, the look of the painted outline on the world map.
- `compact_atlas_all_96_paths...`, `..._organic_provinces...` and `..._paths_do_not_take...` already failed on the pilot branch (seams have no `walk`); the Deep tests (`ember_firelord` counted as live, a Spark link to Astralhollow, 25 quests against 30, gold halving) were stale as well (`the_maelstrom_stands_on_the_eyrie_and_both_gates_work` touches Bifrost's gate and now walks the gate's way, so it passes); `tests/quest-rewards.py` fails for the Nornroot, Keelhaven and Null quests only, none of the new `sky_*` rewards. The Wyrdwood's arrival from the Stormrift has a ram 7.5 tiles away (the old rule is 8): the new updraft test allows 7 on that side only.
- Older suites that teleport into Bifrost at the old coordinates (`bifrost-wind-ui.cjs`, `sky-ui`, music and seasonal suites, MCP `sky`/`ironhide` scenarios) are stale like the other pilot zones'; update before any merge.
