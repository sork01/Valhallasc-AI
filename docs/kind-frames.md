# Per-kind enemy frame sizes (client, exporter, check)

Status: implemented 2026-11-04 (client `frameOf`, `scripts/kindframe.py`, checks), staged and **not committed**: the owner has not yet approved. `client/field.js` and `client/emptyseat.js` are served from disk, so the (behaviour-neutral) client change is already live; no version bump or release note has been made. Live art is unchanged: no manifest or atlas carries a per-kind frame yet; the six reopened remakes are the first users.

## Contract

An enemy manifest (`client/assets/<zone>.txt`) keeps its zone-wide `frame: [w, h]` and `anchor: [x, y]`. It may add an optional map:

```json
"kindFrames": { "golem": { "frame": [192, 192], "anchor": [96, 186] } }
```

- **Fallback:** a kind with no entry uses the zone-wide `frame`/`anchor`. A manifest without `kindFrames` behaves exactly as before (every live manifest, 32 files / 336 kinds, is asserted so).
- **Atlas layout:** `assets/<zone>_<kind>.png` is always 8 columns by 5 rows of that kind's own cell size (`8w x 5h`), 34 frames, the same five clips and row order (idle 6, walk 8, attack 8, hurt 4, die 8). Clip timing is zone-wide (`clips` is not per kind).
- **Limits:** each side 32..192 px (192 x 192 is a 1536 x 960 atlas, about 6 MB of texture), integers only, anchor inside the frame. The client ignores an entry outside these limits or whose atlas is not exactly `8w x 5h`, logs `kindFrames rejected <kind> ...` once, and draws the zone-wide frame. The exporter refuses them outright (`scripts/kindframe.py`, `check_frame`).
- **Scale (owner, 2026-11-04):** one art pixel is always the same size on screen (`SLIME_K` x the kind's `scale`), so a bigger frame is a bigger creature. There is no per-kind draw scale.
- **Collision (owner):** art and click hitbox only. Server collision, aggro, ranges, pathing and balance do not change; nothing in Rust knows about frames.
- **Feet:** the anchor is the planted foot row. Keep every living frame's lowest pixel on `anchor y` (the Crags/`QUADRUPED-GROUNDING` rule), and keep a transparent border (`kindframe.check_bounds`).
- **`tops`:** the health-bar height is `anchor y - highest idle pixel` in the kind's own cell, so it uses the kind's own anchor (`kindframe.top_of`). The client already reads `tops` per kind into `SLIME[kind].top`.

## Who reads what (client)

`frameOf(src, kind)` in `field.js` (exposed as `Field.frameOf`) is the single lookup: `{w, h, ax, ay, own, shadow}`, cached per manifest and kind, never allocated per frame. Enemy-art readers that use it:

| Reader | Uses |
| --- | --- |
| `drawSlimeSprite` | cell size and anchor for the `drawImage` source and destination |
| `enemyHitbox` | cell size and anchor for the opaque bounds (click/target box), cached per image |
| `drawTargetPortrait` | cell size and anchor to crop the hitbox out of the idle row |
| draw loop cull margin (`enemyCullMargin`) | a kind with its own frame is culled at `max(100, frame h x SLIME_K x scale)`; others keep 100 |
| ground shadow (`enemyShadowK`) | a kind with its own frame draws its shadow `own width / zone width` times wider; others keep 1 |
| `emptyseat.js` (Eldmarr memory actor) | borrows `cf_eldmarr` through `Field.frameOf` |
| borrowed art (`artFrom`, e.g. the Empty Seat `es_foe_*` and the boss helpers) | `frameOf` falls back to the borrowed kind's `kindFrames` entry, because the actor draws the borrowed atlas; `scripts/boss_add_art_aliases.py` also copies the entry into the alias kind's own manifest slot |

**Rule for NPC art:** a few enemy-atlas kinds double as NPC art in `city.js` (`sun_`, `ribbon_`, `tangle_`, `heart_`, `year_`, `cairn_`, `frostwake_`, `lapis_`, `bank_`; it reads the zone-wide `meta.frame`). Such a kind must stay on the zone-wide frame: never give it a `kindFrames` entry.

Not touched (different art families): NPC (`npc-art.js`), mounts, class sprites (`magesprite.js`), chests, hero/warrior atlases, `drawSlime` procedural fallbacks. Health-bar `barY`, the target-menu anchor (`best.d.top`) and the click box already derive from `tops`/`enemyHitbox`, so they follow the kind's frame without further code. The stub-sprite test mode has no `kindFrames`, so it is unaffected.

## Exporters and rollback

`scripts/kindframe.py` holds the rules (`check_frame`, `frame_of`, `set_kind_frame`, `atlas_size`, `check_bounds`, `top_of`, `merge_kind_entries`, `restore_kind_entries`).

- A zone exporter declares `KIND_FRAMES = {kind: (w, h, ax, ay)}` (empty by default) and `kind_frame(kind)`; PixelFlow `create` width/height, the editor-frame assertion, atlas size, border check, `tops` and the verify crop all use the kind's own size. `set_kind_frame` writes a `kindFrames` entry only for a kind that differs from the zone-wide frame (a kind equal to it removes any entry, and an empty map is dropped), so an unchanged zone exports byte-identically. Wired in `crags_slime_redraw.py` and `cloister_slime_redraw.py`; copy the pattern into the other `*_slime_redraw.py` when a zone is redone. The drawing code of a zone still has to paint its own cell size (the Painter grid), which is remake-time work.
- **Shared Cathedral manifest:** `merge_kind_entries` replaces only the named kinds' `sprites`, `tops` and `kindFrames` entries and keeps every other kind and key order; `rollback_cloister_art.py` uses `restore_kind_entries` (a backup made before this existed has no `oldFrames`, so its kinds return to the zone-wide frame; a new backup should store `oldFrames` for kinds that had one).
- Back up atlases and manifest before changing any frame size, and ship a rollback script as for any remake. A backup `manifest.txt` records `oldFrames` (`{kind: {frame, anchor}}`, the manifest shape) for every restored kind that had its own frame; `kindframe.frames_from_manifest` converts it. Other tools that read frames: `zone_tops.py` and `render_enemy_sheet.py` now use `kindframe.frame_of` per kind (the sheet output for 96 px zones is unchanged).

## Checks

- `python3 -I tests/kindframe.py`: limits (193 px and sub-32 refused), atlas size, no-op round trips for Crags and the shared Cathedral manifest, `tops`, border rule (16 checks, no server).
- `bash scripts/test-touch-bounded.sh tests/kindframe-ui.cjs` (needs `PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright`): scratch Crags manifest with 64x64, 96x96, 128x112, 192x192 and a refused 193 px entry through the production loader. Per kind: `frameOf`, atlas 8x5, 34 non-empty frames, hitbox, drawn bounds and feet on the ground point, `tops`, shadow, cull margin, whole centred portrait. Back-compat: no live manifest carries `kindFrames`, `client/assets` equals HEAD, `frameOf` equals the zone-wide frame for all 336 live kinds, and the real Greenmeadow, Beetle and Crags art renders pixel-identically to the old formula (a reimplementation written in the test, not HEAD's `field.js` served to a second page: the exhaustive `frameOf` equality is what carries the all-zones claim, and the TODO's "one kind per live zone" was met for three zones). A borrowed-art kind takes its source's frame. 57 checks.
- Mutation controls: `MUTATE=hitbox|draw|portrait|shadow` serves `field.js` with one reader reverted to the zone-wide frame; each fails (the cull-margin reader has no mutation control).
- A kind with a frame under 96 px is possible but its click box and portrait follow its art, not the frame.
