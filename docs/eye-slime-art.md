# The Eye Below enemy art candidate

Private candidate for six enemies at zone 29, prepared 2026-11-11 in `/media/raid/valhallasc-data/eye-slime-work`, branch `feat/eye-slime-art`. Awaiting picture approval before deployment. The proposed version is Beta 1.43.1; reconcile it with the live label before release.

The six kinds have separate faces and silhouettes, with no blush: the Silt Drifter's crescent glare and hooked feeding mouth; the Glassjaw Lurker's unequal stalked eyes and hinged crystal jaw; the Veil Adept's black hood and offset pinprick lights; the Lenswarden's square aperture behind a broad mechanical visor; the Undertide Sibyl's three diagonal diamond pupils and frown; the Unblinking Eye's radial iris and star pupil. An advisor reviewed the approach before drawing.

Each is an editable native PixelFlow source with 34 frames, exported into `cathedral_<kind>.png`. Cells are 176×172, anchored at (88,164); art scale follows the original opaque idle footprints rather than filling the larger cells. The shared `cathedral.txt` retains its 96×96 fallback, (48,90) anchor, all 146 kinds, original clip rates (idle 6, walk 10, attack 12, hurt 10, death 8 fps), and the other 140 kinds' IDs, tops, frames and atlases. No renderer change is needed.

| Kind | PixelFlow source | Idle opaque size | Attack | Death |
| --- | --- | --- | --- | --- |
| eye_drifter | a44e790d87d43cdc | 40×50 | Mantle retracts, tentacles thrust | Loses buoyancy and folds onto its tentacles |
| eye_adept | 65fa46bfb8b94457 | 40×57 | Draws held lens inward, casts forward | Hood and robe slump around the dim cracked lens |
| eye_lurker | 71b4258c6a3d9546 | 72×34 | Crouches, opens connected jaw, lunges | Legs buckle, glass jaw cracks and rests open |
| eye_lenswarden | bceb4c1da3564610 | 74×55 | Braces shield, raises and strikes with staff | Kneels and slumps; shield tips towards the floor |
| eye_undertide | c74c9d21b40eefbb | 47×57 | Arms gather, attached wave crest casts forward | Tide-hair sinks and robe spreads into a pool |
| eye_unblinking | 5fe7fd198e15004f | 66×69 | Ring draws back, dilated iris thrusts forward | Iris clouds, roots buckle and blade ring settles |

The Drifter and Unblinking Eye hover at least 12 pixels above the anchor in living clips and land on it at the end of death. All other kinds remain grounded in every frame. Eight attack poses and eight death poses are distinct for every kind. No creature rotates through the floor. Rigid shield flattening depicts tipping its face towards the floor.

## Commands

Run inside the candidate worktree:

```sh
python3 scripts/eye_slime_redraw.py preview
python3 scripts/eye_slime_redraw.py extents
python3 scripts/eye_slime_redraw.py build
python3 scripts/eye_slime_redraw.py export
python3 scripts/make_eye_below_sprites.py verify
python3 scripts/eye_slime_review.py review
python3 scripts/eye_slime_review.py verify
```

`build` preserves existing registered sources and refuses `--replace`; `refresh KIND...` intentionally replaces those named editor frames. `export` reads the saved editor frames, keeps hand edits, calculates health-bar tops and merges only the six kinds' manifest entries. A frame-size change requires a new source (`SOURCE_SUFFIX`, remove its registry entry first). The legacy maker retains helpers imported by later dungeon makers, while its CLI delegates to this workflow.

## Backup and rollback

Seven original files, SHA-256 digests and old PixelFlow IDs are preserved outside the served tree in `/media/raid/valhallasc-data/eye-slime-original-20261111`.

```sh
python3 scripts/rollback_eye_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for a dry run. The script validates every backup before writing and refuses if any unrelated shared-manifest entry changed. The review verifier exercised a real seven-file rollback on a disposable copy, corrupt-backup refusal with no destination writes, and unrelated-kind tampering refusal with no writes. It also checks destructive build refusal and that live art remains unchanged.

## Focused validation

- 204 saved editor frames exactly equal their exported atlas cells; raw-canvas extents have no clipping.
- Two bounded real-art browser runs, three kinds each: 64 + 64 = 128 passing assertions. Check frame lookup, all 34 cells, timing, attack wind-up/strike/recovery, eight distinct attacks and deaths, grounding/hover/landing, shaded silhouettes, real server presence, health-bar tops and production target portraits. Artifacts: `test-results/driver-113J2L`, `test-results/driver-9hGwOH`.
- Old-Drifter-atlas mutation fails the production frame contract. The route includes a trailing `*` for the loader's query string.
- All six complete frame sheets and in-game screenshots visually inspected. Review capture (`test-results/driver-HO24AH`, copies in `test-results/eye-slime`) additionally hides transient toast/level-up/achievement overlays for readable pictures; it does not change production code.
- Shared manifest's other 140 kinds and their PNGs preserved; live files equal the original backup.
- No combat grinding, encounter calibration or full suites. No server build, restart, production database edit or deployment.

Run browser checks in batches under the standard 1.5 GiB cap:

```sh
EYE_ART_KINDS=eye_drifter,eye_adept,eye_lurker \
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright \
NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules \
VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/debug/valhalla-server \
bash scripts/test-touch-bounded.sh tests/eye-slime-art.cjs
```

Use the remaining three kinds for the second batch. `SCREENSHOTS=1` captures all six without rerunning assertions; `BASELINE=1` captures the original art before building. `MUTATE_KIND=eye_drifter MUTATE_PNG=/media/raid/valhallasc-data/eye-slime-original-20261111/client/assets/cathedral_eye_drifter.png` must fail.

## Review deliverables

29 PNG/GIF files in `test-results/eye-slime`: before, after, comparison, complete attack comparison sheet, combined death comparison, and four per-kind files (full 34-frame sheet, all-clips animation, attack comparison and death comparison). GIFs share one palette across their frames and follow each manifest's original clip rates.

The owner requested FileDrop upload on 2026-11-11. `python3 scripts/eye_slime_review.py upload` uploaded all 29 files (3,044,528 bytes) and verified SHA-256 hashes, MIME types, original-name metadata, lengths and dimensions. Receipt: `test-results/eye-slime/filedrop-receipt.json`. `EYE-SLIME-FILEDROP` is complete. [Before/after review](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-eye-before-after.png) · [Death comparisons](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-eye-deaths-before-after.gif). Picture approval is still required before merging the candidate into the served main checkout. No server restart is required for this art change.
