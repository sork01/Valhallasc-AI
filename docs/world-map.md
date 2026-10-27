# Organic world atlas and walking paths

The Beta 1.29.0 world atlas uses the owner's FileDrop
`newworldmap.png` as its painted overview. It supersedes the earlier sketch and
procedural terrain previews. The supplied artwork was cleaned of misspelled
baked labels with the built-in imagegen tool; geography and terrain are retained.
Correct game names and level ranges are accessible HTML overlays. The original
FileDrop upload is preserved. Asset provenance and the editing prompt are in
`docs/world-atlas-art.txt`.

The overview has 23 irregular regions. Asterion is a city landmark inside
Stormglass. Veyrroot is the regional name for zone 23, with its Canopy city
landmark inside it. Skaldholm and Nacrehold retain separate regions. The bay
contains Rán's Deep and Nacrehold, and Bifrost's floating islands sit above
Wyrdwood. The overview uses existing zone IDs and existing local maps; Asterion
keeps its detailed city map, and Veyrroot's region/city open the Canopy map.
Heartwood and the Seed Vault remain nested interior maps.

The background is `client/assets/world-atlas-painted.png`. Province hit areas
are traced along its painted borders in a 2048×1041 coordinate frame; they are
not generated Voronoi cells. Labels sit in their matching terrain. City buttons
outline the existing painted star city and giant tree rather than covering them
with thumbnails. Entrance buttons remain independently accessible. Exploration
fog is masked to the painted island shoreline, including land between provinces.
The ocean, compass and map grid stay visible. Unknown regions have no visible
labels; discovered regions show their names. Explored ground clears through the
province polygons with soft edges. Detailed zone maps still render the real
terrain, actors, quests, services and routes from `world/map.txt`.

The overview redraws only when the background loads or exploration changes. It
keeps the supplied landscape proportions and fits the entire atlas inside its
window each time it opens (Beta 1.29.1). Scrolling over the overview zooms around
the pointer, from the fitted view up to four times that size. The fitted view
adapts to window resizing; zoomed views can be panned with the scrollbars or
touch scrolling. Detail maps retain their normal scrolling.

## Sources and regeneration

* `world/atlas-geography.txt`: traced shared polygon chains, region names,
  label sites, nested city positions and background asset path.
* `scripts/atlas_geography.py`: deterministic bounds and shared-edge detection.
  Borders stay aligned to the art; corner contacts shorter than 24 atlas units
  do not create walking routes. NumPy/Pillow provide the ownership mask.
* `scripts/compact_atlas.py`: final authoritative route overlay. It runs after
  admission/story/repair overlays inside `scripts/sync-world.cjs`. It replaces
  obsolete outdoor links, places the new paths and exports the same atlas data
  for the client. Ordinary terrain and encounter content remain owned by their
  zone generators.

Run the owning content generator, then `node scripts/sync-world.cjs`, then
rebuild Rust. Never hand-edit generated `world/map.txt` or `client/world.js`.
Two complete sync runs produce identical world and client bytes. A small
Bifrost bridge landing keeps traffic from being forced through another exit;
its sky floor and void collision are updated together.

## Authoritative walking crossings

There are 47 shared-region walking connections and one street into Asterion:
48 two-way routes, or 96 directed crossings. Sunward and Emberwake touch only
at a corner in this artwork, so their former crossing is removed. Region neighbours receive paths
in both directions. Connections from obsolete atlas arrangements are removed
when the regions no longer touch. The travel-master network is rebuilt from
the real crossings, preserving same-zone links and reciprocal flights.

The shared route model retains the existing server-authoritative zone handling.
An optional `Portal.walk` outward direction identifies an ordinary walking path.
A crossing requires actual movement toward the neighbouring region; idle or
inward-facing fighters stay put. On crossing, the server preserves held input
and the remaining local offset of a click destination, clears obsolete targets,
and sends a normal arrival message. Outdoor crossings emit no teleport flare.
The client draws trails and low roadside waymarks instead of glowing gates,
removes their portal night lights, and uses path marks on the minimap/detail map.

Arrivals stand six tiles inward from the return crossing. Both ends are clear
of collision and at least eight tiles from monster spawns. Each generated
approach is actually walkable under Rust collision and avoids all other trigger
areas, including dungeon doors. Players, enemies and scenery retain their data;
the Bifrost landing changes only the local bridge floor and void rectangles.

## Cities, interiors and exploration

City buttons show Asterion inside Stormglass and the Canopy inside Veyrroot.
The current city and its parent region are highlighted together. A known city
can open its detail map before the first visit; its detailed map retains fog until explored.

The 21 dungeon/raid entrances and Heartwood remain purple map buttons in their
parent regions. Heartwood and its nested Seed Vault resolve outward to Veyrroot;
the Moonwell resolves outward through Asterion to Stormglass. Dungeon interiors
occupy no separate overview territory. A discovered entrance can preview an
unvisited map without revealing terrain, enemies or the unknown directory.
Names, routes and doors retain the existing exploration visibility rules.

Opening a map never travels or unlocks a door. The server still checks minimum
level, completed admission quests, party size, raid muster and private copies.
All six keyed entrances, dungeon entrance coordinates, returns and cleared
exits remain unchanged. Keyboard Enter activates city/entrance buttons; Escape
returns to the atlas and preserves its zoom and scroll position.

## Focused validation

* `bash scripts/cargo.sh test compact_atlas -- --nocapture`: organic province
  structure and city containment; safe crossings and collision along every
  approach; all 96 real walking transitions with continued held movement; idle
  and inward refusal, continued click movement, preserved keys and travel links.
* The four existing `dungeon_admission` tests verify the protected quest doors.
* `VALHALLA_BINARY=<candidate> bash scripts/test-touch-bounded.sh tests/organic-atlas-ui.cjs`:
  desktop, phone and tablet; province terrain/labels, city containment, all 22
  interior buttons, fog previews, 44-pixel touch controls, current-city highlight,
  keyboard navigation, detail paths and actual held movement through eight paths.
  `MUTATE=layout` and `MUTATE=entrance` must fail.
* `VALHALLA_BINARY=<candidate> bash scripts/test-touch-bounded.sh tests/organic-atlas-position-ui.cjs`: four actual edge-position markers remain inside their irregular provinces.
* `VALHALLA_BINARY=<candidate> node scripts/test-via-mcp.cjs run walkways`: actual
  MCP handshake, normal click movement both ways, no teleport effects, separate
  zone observations and destination persistence through a private server restart.
* `tests/compact-atlas-ui.cjs`, `tests/worldmap-atlas-ui.cjs` and
  `CHECK_ONLY=atlas tests/travel-fixes-ui.cjs` delegate to the organic atlas suite.
  Held mouse and horse gait checks remain separate in the travel-fixes suite.

No file zones or copy IDs are added or reordered, and saved positions remain
valid. The release was prepared on `feat/compact-worldmap` at
`/media/raid/valhallasc-data/compact-worldmap-review` and merged to main.
The owner authorized merge and deployment on 2026-10-27. Deploy future embedded
server and synchronized client changes together. Client files in the
main checkout are served immediately, so prepare and validate in isolation.


The painted revision passed four revised `compact_atlas` Rust checks and 116
bounded browser assertions at desktop, phone and tablet sizes. The browser audit
checks pixels against the supplied background as well as province names, city
containment, all 22 entrances, fog previews, touch spacing, keyboard access and
actual held-movement crossings. The first phone run exposed entrance/label
crowding; placement now uses rendered bounds after fonts load and a finer search,
including city captions. The final passing run is `test-results/driver-C6bYjN`.
Four actual edge-position marker checks also pass with the traced borders.
The complete sync is byte-stable. Changed JS/Python syntax, formatting, Swedish
coverage and release notes pass. All-target Clippy with warnings denied passes
under a one-CPU, 1.5-GiB scope (the first uncapped invocation was interrupted). Earlier admission/MCP and mutation results refer
to the preceding candidate; no combat or full-suite tests were repeated.

The full-map screenshot is uploaded to FileDrop as
`valhallasc-painted-worldmap.png` (SHA-256 `26efdc7d98ffb8b5891e2dfe08c1c5b00386dcc748ca92a6ec112dfb53214af7`). The original owner upload remains untouched.
The owner authorized merge and deployment on 2026-10-27. Release preparation
backs up the running binary, client files and a consistent SQLite copy. All 47
file-zone IDs are unchanged; saved characters need no migration. Public verification passed; the deployment receipt follows.


## Deployment receipt — 2026-10-27

Beta 1.29.0 is merged and live at https://gunning.se/Valhallasc/.
Runtime source: `04d47531f5e0fb1bdaa8e70dd0a506622d0ad049`. The optimized
release was built in the isolated RAID checkout with one CPU and a 3-GiB cap;
its private startup check passed before the public switch. No players were
online at shutdown. Client and server were installed together.

* Running executable matches both the installed and isolated build binaries:
  SHA-256 `5c90957619a5ec6d8ebe6384343c7f5dabde34e3a72dd5de6e11ad3a0e66d9fb`.
* Public and bridge health both returned `ok`.
* All nine changed public client files match the checkout byte for byte,
  including the new atlas PNG, world data, renderer, styles and version label.
* SQLite `quick_check` returned `ok`; all 31 saved characters remain. All 47 file
  zones retain their IDs, so no saved-zone migration was required.
* No test flags, journal errors or public test guests were introduced.
* Rollback backup: `deploy/backups/painted-atlas-1.29.0-20261027T142200Z/` — previous running
  executable, client ZIP, consistent pre-build database, stopped DB/WAL/shm
  copies where present, and complete before/after receipts with file hashes.

The source commit contains the implementation; the later documentation-only
receipt commit records the deployment without changing runtime assets.

Beta 1.29.2 replaces flat pale province fills with one continuous, cached
grey-blue cloud bank. Warped noise at several scales gives the clouds shaded
billows and wisps. The overview starts fully covered and subtracts only explored
terrain, using the existing per-zone exploration masks; the clearing combines a
soft outer edge with the original clear core. This closes gaps outside province
outlines without leaving fog over already explored ground. Once all overview
regions are fully charted, the original artwork is shown across the whole map.

Focused private browser validation checked 14,707 samples outside province
outlines with no uncovered gaps, shaded cloud variation, clear explored ground,
disabled unknown zones, desktop and landscape phone screenshots, full discovery
restoring the original artwork and absence of browser errors. Reproduction and
pre-change source are in `test-results/worldmap-fog-1.29.2/`. This is a client-only
change and needs no server restart.


Beta 1.29.3 narrows the continuous clouds to a separate island silhouette and
hides unknown region labels and subtitles. `islandMask` in `client/worldmap.js`
traces the actual shoreline in the artwork's 1758×895 frame, independently of
the inset gameplay provinces; the cloud texture receives it once using
`destination-in`. Province geometry alone left exposed strips of coastal land.
The opaque interior covers those strips and province gaps, while the exterior
retains the original ocean, compass and coordinate grid. Known names reappear
through the existing discovery refresh. This supersedes the full-artwork
coverage described for Beta 1.29.2 above.

The focused private check passed ocean/margin pixel equality, five coastal
probes beyond the province boundaries, all 22 unknown regions clouded, 43
province seams covered, no visible unknown labels, clear explored ground,
unknown-zone access restrictions, all 23 names reappearing after discovery,
full discovery restoring the original artwork, and no browser errors. Desktop
and landscape-phone previews and the reproduction script are preserved under
`test-results/worldmap-fog-1.29.3/`.


Beta 1.29.4 feathers the coastline mask with a 12-pixel blur at the cached
cloud texture's half-atlas resolution. Only the mask alpha is softened, so
cloud details stay sharp while the shoreline blends into the nearby ocean.
The private browser check confirmed a partially transparent coastal transition,
clear open ocean and compass pixels, and no browser errors. Desktop and
landscape-phone previews and reproduction are preserved in
`test-results/worldmap-fog-1.29.4/`.


Beta 1.29.5 expands the shoreline mask 72 artwork pixels into the water
(144-pixel round stroke) before the existing blur. A 48-texture-pixel padding
keeps the blur from exposing land where the island meets the image boundary.
The fade now lies offshore and unexplored coastal land remains opaque.
The focused private browser check compared eight coast/boundary probes with
the unmasked cloud texture: all matched exactly, showing no background land
leakage. Offshore fog, clear outer-ocean and compass pixels, desktop/landscape
phone previews and no browser errors were also verified. Reproduction and
previews: `test-results/worldmap-fog-1.29.5/`.


Beta 1.29.6 extends exploration clearing to the offshore cloud apron. A cached
half-atlas-resolution nearest-land lookup assigns pixels outside the province
polygons to an opaque interior source pixel. Multi-source flood fill builds
this lookup once; each discovery redraw copies the nearest source's explored
alpha into the offshore clearing mask. Province interiors remain independent,
so the change does not uncover neighbouring unexplored terrain. The resulting
clearing retains the existing soft edge. No exploration data or saves change.

The focused private browser check explored Veyrroot's eastern middle cell
through a normal private debug teleport. Three offshore probes and the coastal
probe changed from clouded to exact original-art pixels; a separate unknown
coast stayed covered. Desktop/landscape-phone previews and no browser errors
were checked. Reproduction: `test-results/worldmap-fog-1.29.6/`.
