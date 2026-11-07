# Roads across the seams (zone shapes pilot)

Owner, 2026-11-07: "all the zones should have roads from to other zones. like now I see no road from meadow to gloamfen".

## What was wrong
A seam is the shared border of two shaped zones, crossed on foot anywhere along it. Each zone's design (or, for the Moonspore Canopy, the plain
shaping) drew its own trails and nobody asked where the two networks meet. Measured on the pilot map before this pass, the nearest road to a border:

| pair | side A | side B |
|---|---|---|
| Greenmeadow - Crags | 17 tiles | 17 |
| Greenmeadow - Gloamfen | 29 | 14 |
| Greenmeadow - Moonspore | 16 | 110 |
| Crags - Rimeveil | 23 | 12 |
| Crags - Moonspore | 38 | 38 |
| Rimeveil - Gloamfen | 18 | 18 |

(Best point of each border, the worse side counted. Crags - Wyrdwood and Rimeveil - Wyrdwood were 2-5 tiles off on both sides, close but not touching.) Gloamfen's road even ran *along* the border a few tiles
inside it, so the picture looked connected from one side only.

## The pass (`scripts/seam_roads.py`)
Runs **last** in `zone_shapes.py apply` (after the designs, the Skaldholm rebuild and the dock). It is deliberately not part of any design's `ROADS`: a
new road vertex changes `Designer.road`, which gates the seeded scatter and spawn picks, so every approved zone would reshuffle.

For each seam pair among the zones that draw trails (`ROAD_ZONES` = 0, 1, 2, 3, 6, 16):

1. Dijkstra from every road cell over the walkable land of each side (what no void piece covers, 0.7 tiles in from a void edge, minus water/lava/ice,
   buildings, walls, towers, peaks; loose scenery, people and spawns only cost a little).
2. The crossing is the border point, at least 14 tiles from either end (ends are corners, coasts, Skaldholm's wall), with the smallest total cost of the
   two sides.
3. One polyline per side: nearest existing road, then line of sight where the land allows, to the crossing, then on past it into the neighbour's land (up to 2.2 tiles,
   as far as open land goes: the land margin is the part of the grid no `void` piece covers, and a road keeps 0.7 tiles from a void edge). The neighbour draws its ground across the seam from its own `paths` (`groundSample`), so both polylines overlap on the line and the dirt is one road.
4. Only what stands on it goes: loose scenery within 2.6 tiles, spawns within 3.6 (elites within 17 where their zone kept that rule). Everything else of an
   approved design is untouched; a seam that already has a road on both sides at the same point is left alone.

Result on the pilot map: 8 pairs, 16 roads laid (Greenmeadow-Gloamfen: 36 tiles from the shore path to the border, 4 from Gloamfen's road), 83 loose
objects removed, 7 spawns nudged. Wyrdwood lost nothing.

## Not covered
- Skaldholm, Bifrost (updrafts only), Rán's Deep and Nacrehold: no dirt trails (the Deep has no road style, Nacrehold draws `roads`, its only seam is
  the Deep's). Their gates are not seams.
- Every non-seam gate of the trail zones (vaults, updrafts, the Orrery and Nornroot doors) already has a road within 4 tiles.
- A crossing's road is straight where the land allows; the designers' own roads are traced, these are not. Re-trace one in `ROADS` later if it should bend.

## Checks
- `python3 tests/seam-roads.py`: pure data. For every pair both sides' roads touch the border at one point; no building, wall, water or other obstacle
  under the roads that reach a border; no loose scenery within 2.5 tiles of them, no spawn within 3.4. `MAP=<old map.txt>` must fail (8 of 8 pairs do).
- `PAIR=0-3 bash scripts/test-touch-bounded.sh tests/seam-roads-ui.cjs` (`PLAYWRIGHT_BROWSERS_PATH`, `NODE_PATH`, `VALHALLA_BINARY`): a hero on each side of
  every crossing, pictures in `test-results/seam-roads/`. Look at them: the dirt is judged by eye.
