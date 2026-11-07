# Rán's Deep as a shaped, authored zone (zone shapes pilot, 2026-11-07)

Owner request: "for pilot. reshape rans deep. and remake the zone and quests to fit the new shape. no fillers. keep the portals/updrafts since this place should be inaccessible without them. the only place it should have a seamless against is nacrehold. but thatll come after nacrehold reshape", then "it should keep rans deep style". Pilot only (branch `feat/zone-shapes-deep`, off `feat/zone-shapes`). The eighth pilot zone: 0, 1, 2, 3, 6, 7, 8, 16. Owner answers: keep the three elites (Hvitserk, the Ghostmaw, the Kraken), three new outposts.

## The shape

At k = 1.0 the atlas outline of Rán's Deep is a rounded quadrilateral (bbox 253 x 235, grid 256, 49,715 tiles inside the outline against the old 176-square maze's 26,560 walkable ones). Bifrost Reach lies along its west side, Astralhollow east, Nacrehold south, and the north edge is the world's coast. The painting shows dark water with a faint labyrinth in the north and west and open water in the south: that is the zone's character, and it is kept.

## What "keep the Deep's style" means here

The Net (the coral labyrinth, 16-tile cells, walls 3 thick, corridors 13 wide), the open Shallows, Keelhaven (moved whole), the tidebell chains, the Kraken's Court with exactly two doors, the five monster kinds by maze depth, the underwater client theme and black water beyond the outer reef are all unchanged in kind. Only the geometry follows the outline.

## The design (`scripts/deep_design.py`, `deep_pilot_content.py`)

- **Lattice:** 15 x 10 cells of 16 tiles laid over the outline (origin 8,14); a cell exists when at least half of its floor box is walkable ground inside the outline (135 of 150; the 15 that do not are slivers on the west edge and the north-east corner). Dropped cells and the 3-tile rim are solid reef (`reefwall` boxes tagged `rim`, void collision underneath).
- **The maze** is the old depth-first labyrinth with 55% of dead ends braided, over the kept cells, with three rooms as single nodes: Rán's Court (2 x 2, the Kraken, exactly two doors), and two camps (Lanternrest, Gatewatch). `MAZE_SEED = 536` came from `search_seed()`: the Court lies at the 80th percentile of depth, Gatewatch at the 77th, Lanternrest at the 47th. One door in the Net's south wall, the Pearl Gate.
- **The Shallows** (y 174-243) hold Keelhaven (south-west, under the Pearl Gate), the Wreck of Naglfar and Hvitserk in the middle, Drownwatch and the Drowned Chapel in the east, the Empty Seat circle and the Ember Grave Cross. 26 draugr.
- **Net bands:** angler, moray, siren, shellback by quartile of maze depth (16 / 16 / 16 / 14), as before.
- **Chimes:** three chains, 3 / 4 / 5 bells, 35 / 45 / 50 s. The harbour bells stand in the Shallows; the Net's and Rán's bells are chosen from hop-count tours of 52-68 % / 55-70 % of what the slowest class walks while the first bell rings, widest spread first, and the design then re-proves the REAL walk on the 0.5 grid (Dijkstra, best order): harbour 58 %, Net 57 %, Rán 44 % (want 40-78 %).
- **Proofs in `check()`:** everything reachable from the spawn; closing the Pearl Gate cuts off the whole Net and nothing in the Shallows; closing both Court doors cuts off only the Kraken, one alone nothing; each kind stands in its depth quartile; no two bells within 12 tiles; elites keep awareness + 3 tiles from everything walked and 12 from every place; void covers exactly the cells that are not floor.

## Crossings: every one stays a portal

`zone-shapes.txt`: `"designOnly": [8]` (outline floor, no filler, `place_portals` skips the zone and the design places its own gates) and `"seamWith": {"8": [9]}` (the Deep may only ever seam with Nacrehold; `make_seams` and the margin loop honour it, so shaping Astralhollow later will not seam it).

| gate | where | goes to |
|---|---|---|
| `maelstrom_up` (look: maelstrom) | west rim of the Shallows, arrival six tiles in | Bifrost's Maelstrom (arrival unchanged) |
| `nacre_gate` | south rim under Keelhaven | Nacrehold (arrival unchanged) |
| `path_8_13` | east rim, inside Gatewatch | Astralhollow (arrival unchanged) |
| `deep_longship` (look: longship) | beside Keelhaven, west of the plaza | The Drowned Longship |

Arrivals elsewhere that point here are rewritten: Bifrost `maelstrom_down`, Nacrehold `nacre_deep_gate`, Astralhollow `path_13_8`, the Longship's `keel_return` and `keel_clear`. Every other zone is byte-identical.

**For the Nacrehold seam later:** the south border band is already free: no scenery within 2.5 tiles, no spawn within 7 (12 in practice), no building within 20, Keelhaven stands 21 tiles off. Rim reef pieces carry `rim: 1` so the seam can remove the ones along that run, and the Tideway portal `nacre_gate` becomes the seam.

## People and quests

Keelhaven is the old block moved by (+16, +47) with its people, houses, lamps, the Longship door and its two people. Three outposts, each a sanctuary with two givers, a trader, a Spark Travel master and a mailbox: **Lanternrest** (a room of the Net, west), **Gatewatch** (a room on the east rim, beside the way up to Astralhollow), **Drownwatch** (open Shallows, east). **14 new quests**, all old ids kept (texts rewritten where the geography changed): `deep_kh_ledger` (stand at all four crossings), `deep_lr_*` (4), `deep_gw_*` (4), `deep_dw_*` (4). Levels 35-40; rewards in `quest_gear_rewards.py`. Swedish written by hand.

## Client

The Deep draws as a shaped zone: tiles outside the outline are black water (`beyondDeepWall` reads `shapeFloor`), no coast foam or border blend, a dark sea beyond the grid, a plain deep-blue minimap with no shallows. All scoped to the `deep` theme; Nacrehold (`nacre`) and every land zone are unchanged.

## Checks

`REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/deep-design-ui.cjs` (`MUTATE=1` serves the committed `field.js`: the black-water check must fail), `cargo test deep_tests` (rewritten for the new map), `python3 scripts/deep_design.py plan OUT.png`.

## Not done / open

- Balance of the new bands and the walking time through a 135-cell Net are not judged in play (the longest way from the Pearl Gate is 37 cells; Spark Travel masters at the camps shorten the return).
- Older suites that teleport into the Deep at the old coordinates (`tests/deep-ui.cjs`, MCP `deep`, `deep_quests`) are stale like the other pilot zones'; update before any merge.
- The minimap and the world map show the plain pilot background.
