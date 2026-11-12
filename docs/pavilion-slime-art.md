# Thousandfold Pavilion enemy art candidate

Owner accepted all enemy sprites on 2026-11-12. Integrated for Beta 1.44.0; see
[the combined release](enemy-sprites-release.md). The private-candidate status
below records the original review stage and is superseded by that approval.

Private candidate prepared 2026-11-11 in `/media/raid/valhallasc-data/pavilion-slime-work`, branch `feat/pavilion-slime-art`. Awaiting picture approval before deployment, as required by the enemy remake rules in `TODO.md`. Proposed Beta 1.43.1; reconcile against the live label again at release time.

Six native, editable PixelFlow sources replace only this dungeon's six enemies. All use 34 frames in 176×172 cells with anchor (88,164). Original rates are preserved: idle 6, walk 10, attack 12, hurt 10 and death 8 fps. Every kind has eight distinct wind-up/strike/recovery frames and eight distinct death frames. The shared Cathedral manifest retains its 96×96 fallback, (48,90) anchor and the other 140 kinds' entries and atlases. No encounter stats, timing, maps or server changes.

| Kind | Source | Identity and attack | Death |
| --- | --- | --- | --- |
| pavilion_foldling | 107b28b9962b908b | Faceted white paper crane, rose pleats, angular ink eye; neck draws back then beak snaps forward | Neck and wings concertina into a creased paper heap |
| pavilion_inkmoth | c37280112de1df35 | Ragged violet ink wings, narrow amber eye wedges; wings fan and feeding tube lashes | Wings and legs curl as ink spills into a flat pool beneath the body |
| pavilion_silkguard | 1db30dcf725667e9 | Red lacquer mask and silk coat, rigid conical hat; spear rises then thrusts | Knees buckle, silk crumples and the rigid spear tips with the hands |
| pavilion_mirror | 8867bd430ecd5f49 | Half-black porcelain face, one silver diamond eye, blue silk; twin mirrors cross then sweep out | Mirrors crack and tip while robe and ponytail slump |
| pavilion_weaver | 35bc5b0dd748cc15 | Eight jointed legs, six ruby pin-eyes, white silk loom; rears and strikes with attached fangs | Legs curl over the abdomen as the rigid body tips onto its side |
| pavilion_sovereign | 2bf7746f04ea01e8 | Long black stage mask, red pupil, white folded crown, red robe; war fan sweeps forward | Crown folds open, paper sleeves settle and silk robe slumps |

Inkwing alone hovers in all living clips and lands on the final death frame. All other kinds rest on their own anchor row throughout every living and death clip. The Foldling and Silkguard have separate planted feet; the Weaver has eight legs. Faces and silhouettes are separate designs without a shared round-eye/blush overlay.

## Commands

```sh
python3 scripts/pavilion_slime_redraw.py preview
python3 scripts/pavilion_slime_redraw.py extents
python3 scripts/pavilion_slime_redraw.py build
python3 scripts/pavilion_slime_redraw.py export
python3 scripts/make_thousandfold_sprites.py verify
python3 scripts/pavilion_slime_review.py review
python3 scripts/pavilion_slime_review.py verify
```

`pavilion_slime_models.py` holds the six articulated models. `pavilion_slime_redraw.py` handles frames, palette, registry and export. `build` preserves registered sources and refuses `--replace`. `refresh KIND...` intentionally overwrites only those editor frames. `export` reads saved art, preserving hand edits, and derives health-bar tops from idle bounds. A new frame size needs a new PixelFlow source (`SOURCE_SUFFIX` and registry entry).

The legacy maker retains helpers used by other dungeon makers; its CLI delegates to the new pipeline. `dungeon_cel.py thousandfold build|preview` also delegates before the old destructive source-deletion path.

## Rollback and eventual integration

Seven original files, their SHA-256 hashes and the old PixelFlow IDs are preserved outside the served tree at `/media/raid/valhallasc-data/pavilion-slime-original-20261111`.

```sh
python3 scripts/rollback_pavilion_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run by default. Every backup and destination, plus unrelated shared-manifest entries, is checked before writing. A real restore on a disposable copy passed; corrupt-backup and unrelated-kind tampering were both refused with no destination writes.

Other private candidates (Eye Below and Elder Hollow) edit the same Cathedral manifest. At integration, merge each group's own six entries and preserve the others; do not replace the complete manifest with a stale candidate's copy. Combine the safe `dungeon_cel.py` dispatch cases if merging multiple candidates. Reconcile candidate versions and release notes then. Rollback deliberately refuses if unrelated Cathedral entries changed since its backup; reconcile the manifest rather than bypassing that guard.

## Focused validation

Two completed bounded browser batches pass 66 + 64 = 130 assertions: frame contracts, nonempty/border bounds, original clip rates, unique attacks/deaths, readable wind-up/strike/recovery, hover/landing, grounding, planted feet, source IDs, authoritative enemy presence, health-bar tops and target portraits. Artifacts: `test-results/driver-uOLbDp` and `test-results/driver-JIQtsm`. The earlier second batch (`driver-xOIP94`) caught a static Sovereign walk; explicit phase-based robe pleats, sleeve sway and fan motion now produce eight distinct walking frames. Only the failed batch was rerun after correction.

All 204 saved editor frames equal the exported cells. Original served art and the other 140 Cathedral kinds are unchanged. Full frame sheets and in-game captures for all six kinds were visually inspected. Baseline game captures: `test-results/driver-TpOXLM`. Swedish build, release-notes guard, syntax and raw-canvas clipping checks pass. No full suites, combat grinding or balance sweeps.

```sh
PAVILION_ART_KINDS=pavilion_foldling,pavilion_inkmoth,pavilion_silkguard \
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright \
NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules \
VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/debug/valhalla-server \
bash scripts/test-touch-bounded.sh tests/pavilion-slime-art.cjs
```

Use the other three kinds for the second batch. `BASELINE=1` captures original art before export; `SCREENSHOTS=1` captures without assertions and hides transient banners. The old-Foldling-atlas mutation (`test-results/driver-LhUVEY`) fails the production frame-contract assertion as required. The old-art mutation uses `PAVILION_ART_KINDS=pavilion_foldling MUTATE_KIND=pavilion_foldling MUTATE_PNG=/media/raid/valhallasc-data/pavilion-slime-original-20261111/client/assets/cathedral_pavilion_foldling.png` and must fail. The route glob includes query strings added by the loader.

## Review

All 29 before/after PNG/GIF reviews are uploaded and verified against local SHA-256 hashes, original-name metadata, MIME types, byte counts and dimensions (2,858,708 bytes). They were refreshed after the Sovereign walking fix. They cover complete frame sheets, all clips, attack comparisons and death comparisons. GIFs use a shared palette and each version's actual clip rates. Local files and receipts: `test-results/pavilion-slime`.

[Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-pavilion-before-after.png) · [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-pavilion-attacks-before-after.png) · [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-pavilion-deaths-before-after.gif)

Next art group: Temple of the Rain Crown (`RAINCROWN-SLIME-ART`).
