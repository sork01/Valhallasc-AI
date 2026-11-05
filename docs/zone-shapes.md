# Zone shapes follow the world-map provinces (SHAPE-RULES)

Status: **scale rule `nofloor` and "Asterion stays" approved by the owner (2026-11-05); the rest is still a proposal.** Nothing here is applied to `world/map.txt`. Numbers and pictures: `docs/zone-shapes-preview.md`, generator `scripts/zone_shapes_preview.py` (read-only).

Owner answers (2026-11-05): everything on the atlas; real relative scale; edges match the neighbour; preview first.

## Scope: what "everything on the atlas" is

The painted atlas (`world/atlas-geography.txt`) has **23 polygon regions**, not 29: zones 0-4, 6-9, 13-16, 19-23, 25-28 and **45 Emberwake**. The remaining atlas objects are not provinces:

| Zone | Atlas object | Proposal |
|---|---|---|
| 17 Asterion | a landmark point inside Stormglass (`cities`) | no outline of its own; **owner question** (keep its 180 grid, or fold it into Stormglass) |
| 24 Veyrroot Heartwood | nested interior of Veyrroot | no outline; keeps its layout |
| 5, 10-12, 18, 29-44, 46 | dungeons, instances, raid, arena | unchanged |

Zone IDs map to `world/map.txt` as: Greenmeadow is the top-level map, zone N is `zones[N-1]`.

## Scale rule (owner chose `nofloor`, 2026-11-05)

One factor `k` tiles per atlas pixel for every zone: tile area of a zone = polygon area x k^2. The atlas fits painted proportions, not game content, so strict proportion breaks things (numbers in the preview doc):

- Skaldholm's city is 126x126 tiles and Nacrehold's 176x176, but their atlas outlines are small (15.9k and 38.4k px^2). At any single `k` that makes the rest of the world reasonable they **cannot contain their own city** (Skaldholm needs k >= 1.33, Nacrehold k >= 1.23, against a median k of 0.561).
- The Yearwheel is 400x400 today (160k tiles; 8 portals, four season descents, the Black Hour door) but its outline is only 49k px^2: strict proportion makes it ~123x177, a tenth of today's area.
- Greenmeadow and Crags, the level 1-10 zones, grow to 2.3x and 3.0x area, so early walking distances grow ~1.5-1.7x.

Three rules are rendered; the preview states the cost of each:

1. **`median` (not chosen):** `k^2` = median of (old tile area / atlas area) = 0.315, k = 0.561. It minimises the median relative size change, so about half the zones grow and half shrink. Strict, no exceptions. The two cities do not fit and the Yearwheel collapses.
2. **`total`:** `k^2` = 0.452, k = 0.672, conserving total tile area. Every early zone and the Moonspore/Orrery/Sunward group grows 2-4x; cities still do not fit. Not recommended.
3. **`nofloor` (CHOSEN; a deviation from strict proportion that the owner accepted):** the median `k`, but no zone drops below its current area and a city footprint must fit inside the outline. Skaldholm and Nacrehold are drawn 2.4x and 2.2x bigger than their neighbours; the Yearwheel stays 1.0x (395x568 bbox). The owner accepted this on 2026-11-05.

The size of a zone is its outline's bounding box (`W x H`, rounded up). The engine map stays square (`size = max(W, H)`, rest outside the outline) unless the owner wants a non-square grid, which is a larger Rust and client change.

## How an outline becomes collision (proposal)

Today collision is a list of obstacles (rectangles with `width`/`depth`, circles with `r`) tested for every step; Bifrost's shape is 1,022 hand-placed `void` rectangles plus a `sky` mask, Rán's Deep uses a `bounds` rectangle. A polygon outline made of void rectangles would be thousands of obstacles per zone and slow `Map::collide`.

Proposal: a new zone field `outline` (the polygon in tile coordinates, plus the rasterised cell mask derived from it by the generator, one byte per cell). `Map::collide` and the pathing/sight code treat a cell outside the mask as solid, in O(1). The mask is generated data: never hand-edit it (same rule as the rest of `map.txt`). The client draws the themed edge outside the mask and the ground cache, minimap, world map and fog of war read the same mask. Old `bounds`/`sky`/`void` shapes for Deep and Bifrost are replaced by the outline (Bifrost's islands stay as interior obstacles).

## Shared borders and walking routes (edge = match the neighbour)

- Use `scripts/atlas_geography.py`'s shared chains and the 24-unit corner threshold, so the neighbour set equals the 47 live routes plus Asterion's street. Corner contacts shorter than 24 atlas px do not create routes.
- **A border is the walking route to the neighbour.** The portal sits on the shared chain (at the atlas link point or at the point nearest the old portal) and the exit route continues across. `Portal.walk` stays authoritative. Both sides of one border use the same chain, so the arrival of A is the departure of B.
- Long borders may carry more than one crossing; one route per neighbour is the rule until the owner asks for more.
- **Smoothing (if wanted):** the atlas outlines have 10-22 vertices, so straight edges are 30-50 tiles long at these sizes. Smooth **once per shared chain** (for example two Chaikin passes with the end points fixed) and give the result to both neighbours, so borders stay identical. Smoothing must never move a chain's end points or a portal.
- Unshared edges are classified by sampling the painted PNG 14 atlas px outside the edge midpoint: **coast** (water), **land** (outer land that is not another province) or **gap**. Coast gets sea or shore scenery, outer land a themed cliff/wall/fade (per zone theme), gaps are treated like land.

## Existing content that falls outside

The generators lay content out in the old square, so the preview maps old coordinates onto the new bounding box by stretch (an upper bound). Counts of what falls outside are in the preview doc. Rules for `SHAPE-DATA`:

- Spawns, camps, NPCs, places and crosses outside the outline move to the nearest valid cell, keeping spacing rules (enemy cells distinct, 8 units from portals).
- Fixed footprints (cities, camps, houses) keep their **true tile size** and are placed first; the outline rule decides whether they fit. They never scale.
- Portals to neighbours are re-placed on the shared chain. 12 of 94 border portals are more than 25 tiles from their chain under the stretch mapping (for example Wyrdwood's `sky_gate` to Bifrost, 95 tiles): those are real moves.
- Portals to non-provinces (dungeon doors, instances) are content: they must land inside the outline.

## Process and risks

- Sequence: `SHAPE-PREVIEW` (owner approves a rule and the open questions) -> `SHAPE-DATA` zone by zone, outdoor provinces first, cities after -> `SHAPE-CLIENT` -> `SHAPE-MIGRATE` -> `SHAPE-CHECK`.
- The map is embedded in the server: a rebuild and restart is needed (nobody online, backup first). Saved characters inside newly blocked cells must be moved, and dungeon private-copy IDs are unaffected because no zone is inserted (`COPY` in `vault_tests.rs` stays).
- Re-run the generator chain in the documented order; later generators preserve earlier zones. Decide per zone where the shaping step runs (it must run before `sync-world`'s final overlays).
- Balance: sizes change travel times and kill-time grids; recheck only the zones that grew or shrank (owner handles balance testing).
- Worktrees and cargo targets go under `/media/raid/valhallasc-data`, never `.tools/`.

## Owner decisions

1. Scale rule: **`nofloor`** (decided).
2. Asterion: **keeps its current layout** (decided); Heartwood keeps it too (default).

## Still open (proposed defaults apply)

3. Non-square zones: keep an engine-square grid with the outline masked (proposed) or add a rectangular grid?
4. Smooth the outlines (proposed, per shared chain) or keep the raw straight-edged polygons?
