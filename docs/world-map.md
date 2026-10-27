# World map geography

The atlas in `client/worldmap.js` is north-up, matching the coordinates in each
zone detail map. The former force layout kept connected regions near each
other but ignored the sides of their gates. Beta 1.28.0 replaces its positions
with a layout constrained by the authoritative portals in `world/map.txt`.

For ordinary connections, the destination lies on the source gate's dominant
side (nearest edge of the square zone). The source also lies on the reciprocal
entrance's side of the destination. An east exit therefore leads east, with
an entrance on the west; an east exit into a south entrance bends northeast.
Terrain tiles never overlap. Terrain sizes indicate regions, not travel scale.

Gold links are ordinary paths and join the land silhouette. Blue dashed links
are transport portals or entrances into an interior; purple dashed links lead
to private dungeons or the raid. The Stormrift, Maelstrom, Tideway and Starway
retain their transport meaning. The Summit/Gloamfen gates both face north,
and the Tideway gates both face south, so they cannot describe physical
adjacency: these are explicit portals. Veyrroot Heartwood is an interior.
No gameplay gates, coordinates, arrival positions, collision or access rules
are changed to draw the atlas.

Roads attach to their actual gate's side of each tile. A reciprocal portal is
chosen by proximity to the authoritative arrival (`tx`, `ty`), so a dungeon's
boss exit is not mistaken for its entrance. Each inter-zone pair appears once;
internal raid lifts and other same-zone portals are omitted. Routes and fog
still follow the real directed graph and discovered gates. The atlas scrolls
on mouse and touch devices, centers on the current region when opened, and
restores its scroll after returning from a zone detail.

When adding a zone, update `LAYOUT`, then check both gate sides and all nearby
regions. Do not generate a new unconstrained force layout. Special transport
IDs live in `TRANSPORT_GATES`; same-facing gate pairs and interior/dungeon
links are classified from their data. Artwork remains the existing renderer.
The filtered SVG is still baked once to canvas, never redrawn every frame.

Focused check: `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/travel-fixes-ui.cjs`.
It audits every atlas pair, direction, endpoint, overlap and reachability,
checks actual travel in both directions, held mouse movement on foot and
mounted, and all eight frames/facings of the corrected horse run. It also
checks the rider's saddle bob. `MUTATE=mouse|horse|atlas` must fail.
