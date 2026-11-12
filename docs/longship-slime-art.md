# Drowned Longship enemy artwork (private candidate)

Owner accepted all enemy sprites on 2026-11-12. Integrated for Beta 1.44.0; see
[the combined release](enemy-sprites-release.md). The private-candidate status
below records the original review stage and is superseded by that approval.

Built 2026-11-11 on `feat/longship-slime-art`, worktree
`/media/raid/valhallasc-data/longship-slime-work`. The live client stays unchanged.
Candidate label Beta 1.43.1; reconcile against the current live label when approved.
Deployment requires the owner's picture approval, per the enemy-art backlog.

Six native PixelFlow sources contain 204 editable frames. Every kind has its own
mean face and eight distinct attack/death poses. Each source is 176×172, anchor
(88,164); each atlas is 1408×860. Shared fallback stays 96×96 at (48,90).
Original clip rates remain idle 6, walk 10, attack 12, hurt 10, die 8 fps, with
6/8/8/4/8 frames. No encounter, quest, balance, map or server changes.

| Kind | Native source | Identity and motion |
| --- | --- | --- |
| `keel_crab` | `0d388beb96b65af8` | Verdigris legs, ridged copper shell, angry stalk eyes and jointed pincers. Raises claws then snaps forwards; folds stalks, legs and pincers beside the rolled intact shell. |
| `keel_deckhand` | `e679482c03191623` | Hollow drowned eyes, exposed cheekbones and teeth, navy sailor cap and fitted coat, copper cleaver. Connected wrist drives the cleaver swing; body, cap and weapon fall sideways together. |
| `keel_lantern` | `5d9c94921707e831` | Narrow corroded cage, handle, angular holes in a teal flame. Hovers at least 12 pixels above ground and thrusts a connected tongue of flame; light extinguishes monotonically as the rigid cage lands sideways. |
| `keel_cargomaw` | `c05448b9243d4434` | Salt-dark wooden chest, copper straps and articulated lid hinges, asymmetric keyhole eyes and interlocking teeth. Hinged bite and forward lunge; legs buckle inward, eyes darken, lid shuts onto the tipped solid chest. |
| `keel_bosun` | `d5a9cd7f76fd59ac` | Broad sailor, coral bandanna, eyepatch, squint, rope coil and copper hook. Casts outward with a rope attached to the exact rotating hook eye; crew, rope and hook settle together. |
| `keel_captain` | `e0fbac39f1a9e736` | Svala's stern angular face, ivory braids, bicorne, shoulder copper and split navy coat. Two hands follow the rotating anchor shaft through Anchorfall's wind-up and strike. Anchor has a ring, stock and curved twin flukes; captain and gear fall sideways. |

Original and replacement idle opaque sizes, chosen after inspecting all six old
in-game screenshots and before creating sources: crab 64×46 / 64×45; deckhand
51×52 / 49×52; lantern 36×63 / 35×61; Cargo Maw 76×63 / 75×61; bosun 62×54 /
60×54; captain 60×53 / 58×53. Engine elite scaling stays unchanged. Grounded
frames rest on the anchor; the Lantern settles onto it through death. Raw-canvas
bounds are checked before the grounding roll can hide clipping.

## Pipeline

```sh
python3 scripts/longship_slime_redraw.py preview
python3 scripts/longship_slime_redraw.py build
python3 scripts/longship_slime_redraw.py export
python3 scripts/make_longship_sprites.py verify
python3 tests/longship-materials.py
python3 scripts/longship_slime_review.py review
```

Models live in `longship_slime_models.py`; saved IDs in
`longship_slime_sources.txt`. Build keeps registered sources; `refresh KIND...`
overwrites only named editor sources. Export reads saved editor frames so manual
edits survive, derives health-bar tops, and changes only these six entries in the
shared Cathedral manifest. All other 140 kinds, clip metadata and 129 unrelated
native PNG hashes are preserved. `make_longship_sprites.py` delegates its module
and CLI operations; `dungeon_cel.py longship` delegates before the legacy deletion
path. `--replace` is refused. Preserve every other candidate's dungeon dispatch
and merge only this six-kind manifest slice on integration.

## Rollback

Seven originals, SHA-256, sizes, dimensions, old editor IDs and unrelated atlas
hashes are saved outside the live tree at
`/media/raid/valhallasc-data/longship-slime-original-20261111`.

```sh
python3 scripts/rollback_longship_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for dry run. All checks precede writes. Disposable-copy proof
covers no-write dry run, restoring every original, corrupt backup refusal and
unrelated shared-manifest change refusal. Receipt:
`test-results/longship-slime/rollback-proof.json`. Both generations of PixelFlow
sources remain saved. Version/release notes are separate from art rollback.

## Focused validation and review

All 204 editor/export frames match. Bounded real-art browser batches pass 62 + 62
assertions; the final corrected crab passes another 24. These cover production
frame/source loading, timings, substantial wind-up/strike/recovery, all distinct
attack/death frames, borders, grounding/hover, health bars and target portraits.
Run three kinds at a time with `LONGSHIP_ART_KINDS`. Original crab atlas mutation
(`MUTATE_KIND=keel_crab`, `MUTATE_PNG=<backup>/client/assets/cathedral_keel_crab.png`)
fails the production frame contract as intended. Evidence runs: `driver-G6eBhU`,
`driver-PriQfd`, `driver-rBbSFr`.

38 material/preservation assertions pass. Every kind's idle-as-corpse mutation is
rejected by its material assertion (`MUTATE_MATERIAL=kind`,
`LONGSHIP_MATERIAL_KINDS=kind`). Swedish build/check, release-note guard and
Python/JavaScript syntax pass. The existing `longship-ui.cjs` atlas check now uses
`Field.frameOf`; its unrelated music/travel checks were not rerun.

The art advisor reviewed the approach and all full sheets; corrections connected
the Bosun's rope to its rotated hook eye, added visible Cargo Maw lid hinges, and
folded the crab's raised claws/stalks into a clear death pose. All six final full
frame sheets and in-game captures were inspected.

29 before/after review PNG/GIFs are uploaded to FileDrop: 3,707,300 bytes,
SHA-256, byte lengths, MIME/metadata, dimensions and animation counts verified in
`test-results/longship-slime/filedrop-receipt.json`.

- [Before and after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-longship-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-longship-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-longship-deaths-before-after.gif)

Awaiting picture approval. Next enemy-art group: Black Hour Foundry
(`FOUNDRY-SLIME-ART`).
