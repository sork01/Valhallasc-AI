# Building door/window projection — Beta 1.35.2

Asterion and Astralhollow windows were flat screen rectangles placed at an
isometric anchor. Nacrehold windows/doors used the same approach with circles
and ovals. Their anchors belonged to the wall, but their frames, panes and
crossbars faced the camera. The Cathedral's animated ring had the same issue.

`City.kit.wallPlane(g,x,y,side)` maps local horizontal pixels onto a vertical
wall while preserving upright verticals. Call it inside save/restore, after
projecting the wall anchor with `iso`. The +Y/front wall has screen slope
**+0.5**; the +X/right wall has slope **−0.5**. Moving the anchor alone does not
project the opening. Frames, panes, bars, knobs and effects share that plane.

Affected native cached art: Asterion homes; Nacrehold homes, inn, palace,
archive and Cathedral entrance; Astralhollow homes and observatory. Archive
upper windows now use actual right-wall anchors. The lower central Asterion
window is omitted because the doorway occupies that space. The Cathedral's
ring uses the same origin/plane as its seal. Curved shell decorations retain
their authored surface. Common timber houses, chapels and tower slits already
use isometric polygons and remain unchanged.

Focused bounded `tests/building-openings-ui.cjs`: **12 checks / 551 painted
openings / 116 distinct variants / 413 placed buildings**, both wall directions,
static and animated openings, frames/panes and unchanged common architecture.
Actual fill/stroke path masks must have the expected pixel covariance slope;
a flat screen shape yields zero and fails. No browser errors. Inspected native
contact sheet: `test-results/driver-f9T55I/building-openings-contact.png`.
The first test fixture allocated a full canvas for every opening; it was replaced
with one reused canvas cropped to each path's bounds, keeping the 1536 MiB cap.

This is a client-only native artwork correction. No map, collision, gate,
interaction, save, PixelFlow sprite or server changes are required. JavaScript
syntax, Swedish freshness and release-note checks accompany publication.


Deployed client **Beta 1.35.2**, main source `0a627d5` (private `433b861`).
All six public client hashes and public/bridge health pass; the existing server
remains Beta 1.35.0/PID 1089769, with no restart or database writes. Receipt:
`test-results/building-openings-release-20261102T191209Z.json`.

The four existing city pictures and the wall-detail picture in FileDrop were
refreshed, and `valhallasc-building-openings-fixed.png` shows the corrected
building styles. All six uploads have matching SHA-256. Native captures:
`test-results/driver-B1OIB3`; building gallery: `test-results/driver-f9T55I`.

Beta 1.35.3 also replaces the detached/front-facing Nacrehold shell roofs and
pillars with projected geometry, and places the common-house doorstep at its
door instead of on the wall: [nacre-roof-geometry.md](nacre-roof-geometry.md).


## House sign clutter — Beta 1.35.4

Residential street-and-number labels are catalog metadata and no longer draw
plaques on the houses. All 344 address texts and backing boards are suppressed.
The 43 named shop/service signs remain, floating above roof, chimney and chapel
tower bounds with a gap. Field culling accounts for that height. Shop signs
are drawn outside the shared building cache, so names cannot bake into another
house’s sprite. Named stalls already place their names above their awnings.

A focused private render inspection confirms zero residential address text or
boards and all 43 named signs/boards retained. Native city views were inspected;
no full suite or new permanent test was needed for this presentation change.
