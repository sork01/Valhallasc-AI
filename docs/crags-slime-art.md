# Emberfall Crags: slime-style artwork candidate

Released as **Beta 1.39.2** on 2026-11-03 after the owner's explicit "deploy crags"
approval. Source **bae6ec2**, assembled on top of Rimeveil/main `5c18db3` in
`/media/raid/valhallasc-data/crags-slime-release-20261103` on
`release/crags-slime-20261103`, is merged into main and live. Eight public release
hashes and both health endpoints pass; five public Rimeveil art hashes are
unchanged. Server PID/executable unchanged, with no restart, build or DB work.
Receipt: `test-results/crags-release-20261103T173612Z.json`.
The original candidate remains archived in
`/media/raid/valhallasc-data/crags-slime-work`, based on `9dea2cc`; its stale
TODO/version must not overwrite current main.

The five existing Crags kinds now share Greenmeadow's glossy pixel shading,
large white eyes, highlights, blush and chunky proportions. Existing kind IDs,
colours, weapons and material identities remain. The owner clarified during
implementation: **do not use squash and collapse where they do not make sense**.
That supersedes the initial universal squash/stretch/death wording in TODO.md.

Movement follows the material:

- Fire Wisp: flickering deformable fire; extinguishes to a small ember and ash.
- Lava Spider: rigid shell, eight jointed legs; legs buckle underneath on death.
- Ash Wraith: drifting hood and swinging scythe; dissolves upward into ash.
- Cinder Golem: fixed-size stone components, stepping feet and raised fist;
  stone components slump and separate on death.
- Cinderlord: rigid armour and hammer, moving limbs, horns and molten core;
  armour slumps with scattered stones on death.

The spider, golem and Cinderlord have no whole-body squash/stretch, flattened
puddle death or elastic resizing. Names here follow the owner's request;
production display names remain Cinder Wisp, Magma Spider, Ash Wraith,
Basalt Golem and Cinderlord.

## Editable sources and export

| Kind | New PixelFlow ID | Preserved previous ID |
| --- | --- | --- |
| wisp | c62b50368813e7d4 | fd0afdfe7b3ee253 |
| spider | 10a626fa62ff0e11 | 9819492cb5c33f19 |
| wraith | f46a745bc9b8ee57 | 9a502a20b669e176 |
| golem | 39ba48e3c3cf86d1 | f4e022ffcfb5b24f |
| cinderlord | dc4053a775a9b79a | 58433dbc7f28eee8 |

New prefix: `valhallasc_crags_slime_style_`. Saved IDs live in
`scripts/crags_slime_sources.txt` and the candidate's `client/assets/crags.txt`.
Indexed source arrays: `scripts/crags_slime_<kind>_raw.npz`. New sprites were
created and drawn through PixelFlow, then read back from their saved editor
frames for export. No previous PixelFlow source was replaced or deleted.

`python3 scripts/crags_slime_redraw.py preview | build | export` is the new
workflow; the established `make_crag_sprites.py` command delegates to it.
Build preserves registered sources and refuses duplicate unregistered names;
edit saved sources in PixelFlow, then export to retain editor changes.
Destructive `--replace` is refused. Export derives health-bar `tops` itself.

Same 96×96 frame, anchor (48,90), 768×480 atlas, 34 frames: idle 6 at 6fps,
walk 8 at 10fps, attack 8 at 12fps, hurt 4 at 10fps, die 8 at 8fps. The candidate
replaces the five old PNGs at their existing asset paths; no old PNG duplicate
is installed under `client/assets`. No renderer, map, stats, combat timing,
reward, zone, server or database changes. No server build or restart needed.

## Rollback

Original files and their SHA256 hashes, plus the previous PixelFlow IDs, are
kept **outside the live tree and candidate worktree**:
`/media/raid/valhallasc-data/crags-slime-original-20261103/manifest.txt`.
This directory contains the exact previous `crags.txt` and five PNGs.

One-command rollback of a deployed version (only run when rollback is wanted):

```sh
python3 /media/raid/valhallasc-data/crags-slime-work/scripts/rollback_crags_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for a dry run. Use `--target` for an alternate checkout and
`--backup` for an alternate backup directory. The script validates the complete
file set and all source hashes before changing anything, atomically replaces
each of the six files, and verifies the restored hashes. It touches no release
labels, scripts, other art, server or database. Release notes/version changes
after a production rollback must describe the restored appearance.

The actual rollback command was tested against a disposable candidate copy:
all six original hashes restored. A corrupted backup is refused before any
target file changes. Proof: `test-results/crags-slime/validation.json`.

## Focused verification

- All **170** saved-editor frames match exported atlas pixels exactly.
- **58** bounded real-art browser checks pass: source IDs, dimensions, anchors,
  34 nonempty frames per kind, clear borders, all five distinct clips at original
  fps/counts, eye whites/highlights, health-bar tops, production portraits,
  authoritative Crags presence and no browser errors.
- Desktop gameplay for every kind, landscape phone gameplay and production
  portrait montage: `test-results/driver-BdMD8a`.
- Editor hashes/bounds: `test-results/crags-slime/editor-export-proof.json`.
- Release-note guard, Swedish generation/check, Python/JavaScript syntax and
  diff whitespace pass. No Rust changes, full suites, grinding or balance runs.

The first browser launch used an absent RAID browser cache; the installed
Chromium at `/home/serveperry/.cache/ms-playwright` was used successfully.
Run the focused check from the candidate with:

```sh
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server bash scripts/test-touch-bounded.sh tests/crags-slime-art.cjs
```

Release integration on the current Rimeveil stack also passes all **58** focused
browser checks. Artifacts: `test-results/driver-bh9J5B` in the isolated release
checkout. All 170 copied frames still match saved-editor proof; the five death
clips contain 8/7/8/7/7 distinct frames, respectively. No artwork regeneration
was performed for deployment.

## Owner review pictures

All **13** requested/related files are uploaded to Sork's FileDrop. Destination
SHA256, size, dimensions, original filename and MIME metadata were verified.
Receipt: `test-results/crags-slime/filedrop-receipt.json`.

- `valhallasc-crags-before.png`
- `valhallasc-crags-after.png`
- `valhallasc-crags-before-after.png`
- `valhallasc-crags-{wisp,spider,wraith,golem,cinderlord}-frames.png`
- `valhallasc-crags-{wisp,spider,wraith,golem,cinderlord}-animations.gif`

The comparison uses the exact old/new idle frames at the same 2× nearest-neighbor
scale. Animation previews run all five clips simultaneously at original fps;
death holds its final frame briefly before replaying. Frame sheets show all
34 frames. Use the receipt as the authoritative full-hash record.

The owner approved Crags deployment after Rimeveil. The private 1.39.1 label
is reconciled to 1.39.2 in this release. No release restart or migration is
required. Greenmeadow remains a separate feature candidate; Gloamfen is next.

## v2 redo (Beta 1.39.11, 2026-11-04, candidate, not live)

The owner reopened the Crags remake and asked for it redone from scratch in the
same direction. `scripts/crags_slime_redraw.py` was rewritten with the lessons of
the later zones; the v1 sources and raw arrays are kept as
`scripts/crags_slime_v1_*` (v1 PixelFlow IDs in `crags_slime_v1_sources.txt`).

- Five new native PixelFlow sources (prefix `valhallasc_crags_slime_style_b_`, IDs
  in `crags_slime_sources.txt`); `build` refuses `--replace` and registered kinds,
  `export` preserves saved editor frames and derives the health-bar tops
  (81/43/68/71/85).
- **Grounding rule (`QUADRUPED-GROUNDING`):** every living frame of the spider,
  golem and Cinderlord has its lowest pixel exactly on row 90 (planted feet are
  `Painter` balls with integer radius and centre y = radius). Death frames of the
  rigid kinds are clamped so they never sink below row 90. The wisp and wraith
  hover by nature.
- Deaths (eight distinct frames each, all checked): wisp gutters and falls as an
  ember with drifting smoke; spider folds its legs and its shell drops and cracks;
  wraith dissolves from the hood down (`erase_rising`) into settling ash; golem
  kneels, head rolls off, core goes dark; Cinderlord buckles and topples on a
  `Rig` with the hammer lying on the floor.
- Walk cycles of the golem and Cinderlord swing the fists opposite each other
  (`cos` phase) so no two walk frames are identical.

### Checks

`tests/crags-slime-art.cjs` (71 bounded real-art checks) now also asserts eight
distinct death frames per kind and the row-90 grounding of the three rigid kinds.
Mutation control: `MUTATE_SPIDER_PNG=<png>` serves a spider atlas with the idle
frame moved up 1 px and the grounding check fails (`lowest rows 89,90`). 170
saved-editor/export frames match (`crags_slime_redraw.py verify`).

### Rollback (two levels)

- To v1 (live art since Beta 1.39.2): `python3 scripts/rollback_crags_art.py
  --target <checkout> --backup /media/raid/valhallasc-data/crags-slime-v1-20261104 --apply`
  (dry run without `--apply`).
- To the pre-slime originals: the same command with the default backup
  (`crags-slime-original-20261103`).

Not deployed: wait for the owner to approve the pictures. Release recipe: commit
all but `TODO.md` in this worktree, merge `--ff-only` into main, verify the
public hashes of the six art files and `index.html`.
