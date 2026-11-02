# Nacrehold shell roofs, pillars and Alderhaven ledges — Beta 1.35.3

The old Nacrehold shell was a front-facing drawing lifted by a screen-space
height heuristic. It floated above the flat ceiling and ignored the building’s
world axes. Pillars were similar flat drawings at fixed screen coordinates.

`nacreart.js` now builds a ribbed barrel-shell roof from projected world-space
vertices. Its front fan follows +Y, its curved roof extends through the actual
depth, and its rim overlaps the wall top. Homes use height 100; grand homes 160;
the Cathedral 193; stall canopies 130. Small overhangs preserve clear streets.

Pillars have projected circular plinths/capitals and tapered shafts, with a
shared 2:1 ground projection and world-coordinate front-floor anchors. The same
primitives align the palace/Cathedral, market supports, garden and fountain.
Garden posts paint back-to-front. The Cathedral rose window belongs to the new
fan face; the palace pearl sits on the roof ridge. The memorial shell is
projected onto its upright world plane. Native cached boxes stay intact.

Alderhaven’s apparent window ledge was the common-house doorstep rendered at
world origin inside the building. It now touches the front door: centre at
`(0, depth/2 + .25)`, depth .5, rear edge at the wall. Existing correctly
projected window frames and shutters remain unchanged.

Focused bounded `tests/nacre-roof-geometry-ui.cjs`: **14 distinct checks** over
**33 variants / 129 Nacrehold objects**, all four Alderhaven buildings, actual
roof eave vertices at their wall-top heights, pillar floor anchors/capital
projection, no cached-box clipping, rose window/pearl attachment and browser
errors. Initial coverage: `test-results/driver-PolxAl`; final landmark refinements
only: `test-results/driver-bRkQIm`. Both native contact sheets inspected.

Client-only artwork/placement fix. No map, collisions, interactions, saved data,
server, new sprites or PixelFlow IDs change. JavaScript syntax, Swedish
freshness and the matching release-note guard accompany publication.


Deployed and verified client **Beta 1.35.3**, main source `e14fa6f` (private
`dc20136`). All four changed public client hashes and public/bridge health
pass; the server remains Beta 1.35.0/PID1089769, with no restart or database
writes. Receipt: `test-results/nacre-roofs-release-20261102T195237Z.json`.

City pictures and the wall-detail preview were refreshed in FileDrop, plus
`valhallasc-nacre-shells-pillars-fixed.png`; all six uploads SHA-256 verified.
Final city captures: `test-results/driver-T05nu3`; gallery: `driver-bRkQIm`.
