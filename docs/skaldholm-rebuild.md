# Skaldholm rebuild (zone shapes pilot, branch `feat/skaldholm-rebuild`, off `feat/zone-shapes` bd9fec8)

Owner, 2026-11-06: the four neighbours' walls (Greenmeadow, Crags, Gloamfen, Rimeveil) stay exactly as built; the city is made in the middle of them ("i just want to keep the walls ... and make the city in the middle"). Pilot only. TODO `SKALDHOLM-REBUILD`, wiki `10_projects:valhallasc_skaldholm_rebuild_20261106`.

## Measured

The ground the four shaped neighbours do not own is an **L of 14,486 tiles** (91% of the old 126 x 126 = 15,876), atlas frame = tile + `shape.T`: a north part x 370-454 (85 wide), y 600-728, and a south band x 370-502, y 728-755. The doors are fixed by the neighbours: N (411,601), E (452,663), W (371,703), S (438,755). The atlas decagon (15,800) is NOT what the walls enclose. `zone_scale` as coded would give Skaldholm k = 1.32: it must be forced to 1.0. `python3 scripts/skaldholm_rebuild_plan.py OUT.png` reproduces the numbers and draws the plan (read-only).

## Layout (stage 1, a plan, nothing written to the map yet)

* **Rigid middle strip.** Old x 38.5-123.5 (85 wide), old y 13-139 translate by (331.5, 587): the Grand Avenue (old x 80) lands on x 411.5, the Trade Road (old y 76) on y 663 = the Crags door, the N end on the Rimeveil door. That keeps the plaza and fountain, Cathedral, Steward's court, Archive, Guild court, Gilded Lute yard, Meeting Stone court, the Undervault stairs (old 104.4,122) and 82 of the 108 houses exactly as they are, with no scaling. NPC routes inside the strip need no change.
* **South band** (133 x 27, about 3,500 tiles) takes what lay outside the strip: 26 houses, smithy yard, stable yard, the NW garden with its fountain, 8 NPCs (smith, apprentice, painter, weaver, stable master, three watchmen), plus a street along it (new Southgate Street) and the road up from the S door (438,755). Free room is left over: the only place for a new district.
* Old walls, towers, the Great Gate approach, the Glacier gate arch at x 48 and the outer trees go.

## Open points found while planning

* The **Steward's Hall** (old 80,19) stands in the avenue where the Rimeveil door now lands: move the hall off the avenue (not yet done) and keep its NPC and `es_05_m` (80,28) coherent.
* The **W door** (371,703) lands beside old houses at the west edge (old x 39-46, y 110-125): they move to the band and a West Street runs from the door to Lark Lane.
* The **Crags/Greenmeadow notch**: the L's top edge x 456-502 at y 727 has no wall piece, it is only void collision. The city needs a wall there (a Crags-side segment, a small addition to the four walls).
* The vault machinery (`build_walls` in `zone_shapes.py`) copies the city's OWN wall pieces into each neighbour's frame and derives the vault shift from the arch positions, so the plan keeps it: stage 2 makes the city a shaped zone in ONE frame (T = [357,599], grid 168), puts its arches exactly in the doorways so each vault shift equals `T_neighbour - T_city`, and makes the city's wall pieces coincide with the neighbours' pieces. Then there is one wall, seen from both sides.
* Everything keyed to city coordinates moves with the rigid strip (`exitArches`, `cityEntrances`, `atlasPaths`, `exitRoutes`, `paths`, the season decor arrays, `places`, `spawn`, NPC routes, quest targets, the Undervault stairs portal); the band content needs the same.

## Stages

1. Plan (this commit).
2. `zone_shapes.py`: Skaldholm joins `zones`, sidecar/unshape, force k = 1.0, one frame; a `skaldholm_design.py` applies the cut-and-translate and fills the band; walls and vaults re-derived; `align_corner_wall` and `trim_corner_seam` re-checked.
3. Checks: `tests/vault-seamless-ui.cjs` (bounded), Rust city tests, two `sync-world` runs byte-identical, pilot swap per the pilot deploy order.
