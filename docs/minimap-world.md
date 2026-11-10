# World minimap (MINIMAP-WORLD, Beta 1.41.0)

Owner, 2026-11-06: "i want the minimap to be the whole world. like the zones are, and never change when crossing a border."

## What it does
- A **world zone** is a shaped zone with `shape.k == 1`, a `shape.T` and a rule other than `authored` (`worldZone()` in `client/field.js`): 22 zones including Skaldholm and Bifrost. Heartwood (no atlas place), the Yearwheel (2.8 tiles per atlas px) and every dungeon, instance, Arena, Asterion and Moonwell keep the old single-zone minimap.
- A zone's tile (x, y) lies at atlas (x, y) + `shape.T`. For 70 of the 72 seam and vault links the shift equals the `T` difference (checked 2026-11-10; the two exceptions are the Sunward-Yearwheel vault, whose scales differ), so the minimap places zone Z at `T[Z] - T[hero zone]` in the hero's frame and a crossing swaps nothing.
- `drawMini` draws every world zone whose grid box reaches the view: all shallows first, then land, each land layer with its own zone's fog. Gate-only borders (no seam) show the neighbour too. NPCs, Spark masters and `Quests.mapMarkers(z)` of every zone in view are drawn with no fade (other zones' quest marks only where in view; the hero's own pin to the edge). Enemy dots stay what the server sends (`farDots`, ghosts).
- One sea colour for the atlas frame (`#2b2421`; Rán's Deep and Nacrehold keep their deep-blue `#071018`). Bifrost's canvas is cut to its islands like an outlined zone.

## Memory and cost
- Per zone two canvases (land, shallows) at 2.4 px per tile, cached in `miniCache`: 8 soft cap, 14 hard, least recently used first, never the hero's zone, never a zone still in reach (view plus a 60% margin). Missing zones are queued nearest first and built one per 30 ms timer tick from a context kept out of `ctxs` (`miniCtx`), so they never count as seam neighbours for `staleChunk`/`nbFloor`. Leaving the atlas (a dungeon) frees them.
- Measured 2026-11-10: the renderer sits near 0.8-1.1 GB with or without it; the cache is not a visible share. A bounded run that visits five or six zones in one client dies with `oom-kill` with the OLD client too, and so did the touch section of `tests/minimap-ui.cjs` (two clients): the test now closes the desktop context first.

## Tests
`tests/minimap-ui.cjs` (bounded runner, `explore_all` first because a fresh guest has explored one meadow cell and the rest is mist): both sides of the Crags-meadow border agree on the ground (enemy and travel dots skipped), the Stormglass-Frostwake gate shows Frostwake, `Field.miniZones` lists the cache. `FIELD_JS=<file>` serves that file as `field.js`: the old version must fail on the gate pixel.

## Open
- Dungeons, raids, Arena, Asterion, Moonwell and Heartwood: the owner's 11-06 answer was a world view centred on the entrance with an "inside" marker; not built, to confirm.
- Sunward Vale-Yearwheel doorway still changes the minimap (different scale).
