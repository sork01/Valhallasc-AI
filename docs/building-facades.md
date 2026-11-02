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
