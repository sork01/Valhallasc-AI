# Gloamfen: slime-style artwork candidate

The owner approved deployment and the finish skill on 2026-11-03 after reviewing
the corrected tails. The tested **Beta 1.39.4** release is prepared in
`/media/raid/valhallasc-data/fen-slime-work`, branch `feat/fen-slime-art`, based on
main `3c9394e`. Publication and public hash verification are the next steps.

Five new native PixelFlow sprites share Greenmeadow's glossy shading, large
white eyes, highlights, blush and chunky proportions. Fen colours and creature
identities remain readable. Kind IDs, production names, paths, frame size,
anchors and animation rates are unchanged.

- **Fen Toad:** folded hind legs, propping forefeet, hopping movement, warts,
  pale belly and tongue strike. Death tucks the legs and tips the intact animal
  backwards onto its back; it does not melt into a puddle.
- **Mire Crocodile:** articulated four-legged stride, tapered tail, back spikes,
  long toothed snout and jaw snap. Death folds the legs and rolls the scaled
  body onto its flank, preserving its body and snout dimensions.
- **Drowned Knight:** fixed-size plate pieces, jointed steps, shield and sword,
  kelp crest and sea-green magic. Death buckles the legs, separates the rigid
  armour pieces, drops the helmet and sword, and fades the motes.
- **Mire Hydra:** three swaying necks, central lunging bite, four legs, teal body
  and purple frills. Death drops the left, right and central necks at different
  times, leaving the three heads lying across the intact body.
- **Gloomroot Colossus:** rigid bark, root feet, heavy branch arms, moss,
  mushrooms and a glowing heart. Death splits the trunk, drops branch pieces,
  extinguishes the heart and wilts the moss/leaves. No squash of the wood.

All eight death poses per kind differ, with five distinct final corpse
silhouettes. Full sheets were visually reviewed before creating saved sources.
The private gameplay and portrait screenshots were also inspected.

## Editable sources and pipeline

| Kind | New PixelFlow ID | Preserved previous ID |
| --- | --- | --- |
| toad | c6ce973be726b47d | 62301637ad14d062 |
| croc | 1fc8953f0a948cc9 | 63dafae785d1794c |
| knight | 68753169f383d6ad | 8536840e86dd5186 |
| hydra | db998fee96b02ee8 | a34152941af03712 |
| gloomroot | 93928dcaecfa02a4 | daea7c6103b488fb |

New prefix `valhallasc_fen_slime_style_`, registry
`scripts/fen_slime_sources.txt`, indexed arrays
`scripts/fen_slime_<kind>_raw.npz`. Previous PixelFlow sources and historical
raw arrays remain intact. No previous source was modified or deleted.

```sh
python3 scripts/fen_slime_redraw.py preview
python3 scripts/fen_slime_redraw.py build
python3 scripts/fen_slime_redraw.py export
python3 scripts/fen_slime_redraw.py verify
```

The established `make_fen_sprites.py` CLI delegates to this pipeline. Both
entry points refuse destructive `build --replace`. Build retains registered
sources. Export reads the saved editor frames, preserving edits; verify compares
saved frames directly to exported atlases. Export derives health-bar tops:
toad 48, croc 42, knight 85, hydra 87, Gloomroot 83. The existing production
loader consumes those values without renderer changes.

Same 96×96 frame, anchor (48,90), 768×480 atlas, 34 frames per kind:
6 idle at 6fps, 8 walk at 10fps, 8 attack at 12fps, 4 hurt at 10fps,
8 die at 8fps. Candidate replaces only five PNGs and `fen.txt` at the existing
art paths; no duplicate old atlas remains under assets. No map, stats, rewards,
zone IDs, server or database changes; no rebuild, restart or migration.
No music change, grinding or encounter/balance/timing testing.

## Rollback

External backup `/media/raid/valhallasc-data/fen-slime-original-20261103`
contains all five previous PNGs and `fen.txt`, plus hashes and previous
PixelFlow IDs in `manifest.txt`. It is outside both live and candidate trees.

```sh
python3 /media/raid/valhallasc-data/fen-slime-work/scripts/rollback_fen_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for dry run. All six source hashes and target paths are checked
before writing. Files are replaced atomically and verified after restoration.
Version labels/notes are separate from art rollback. Actual restore on disposable
candidate copies passed; a corrupt backup was refused without changing targets.
All six live art files still match original backup hashes.

## Focused verification

**69 bounded real-art browser checks pass**, in a private server using an
isolated database and the existing production binary:
contract, kind/source IDs, all 170 nonempty/unclipped frames, five animating
clips at original timing, readable eye whites/gloss, production portraits,
derived/consumed health-bar tops, eight distinct death poses per kind,
retained solid anatomy/material, five distinct corpse silhouettes,
authoritative Gloamfen presence and no browser errors.

Browser artifacts: `test-results/driver-jZmeNG` (portraits, five desktop gameplay
views, landscape-phone view and numerical report).

All **170 saved-editor/export frames match exactly**, verified through the
established CLI. Proof: `test-results/fen-slime/editor-export-proof.json`
(frame and atlas hashes). `validation.json` records rollback, corrupt-backup
refusal, unchanged live art and destructive-build refusal. Python/JavaScript
syntax, Swedish generation/check, release-note guard and diff checks pass.
No full test suites or Rust checks were needed for this art-only change.

```sh
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server bash scripts/test-touch-bounded.sh tests/fen-slime-art.cjs
python3 scripts/fen_slime_review.py review
python3 scripts/fen_slime_review.py verify
```

Review `verify` is a pre-deployment check that expects original live art.
After deployment use `python3 scripts/make_fen_sprites.py verify` instead.

## Owner pictures

All **19** FileDrop destinations are SHA256/size/dimensions/original-name/MIME
verified. Receipt: `test-results/fen-slime/filedrop-receipt.json`.

- `valhallasc-fen-before.png`, `-after.png`, `-before-after.png`
- `valhallasc-fen-{toad,croc,knight,hydra,gloomroot}-frames.png`
- `valhallasc-fen-{toad,croc,knight,hydra,gloomroot}-animations.gif`
- `valhallasc-fen-{toad,croc,knight,hydra,gloomroot}-death-before-after.gif`

Equal-scale comparisons show both idle and final death poses. Sheets show every
frame; GIFs run the original clip rates and hold the final death pose briefly.
`fen_slime_review.py upload` is a separate explicit action.

[Before/after comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-fen-before-after.png).
Next unfinished zone: **The Undervault**. Live remains Beta 1.39.2; reconcile
candidate numbering against the live label when deployment is approved.

## Tail correction after owner review

The owner meant the crocodile and three-headed **hydra**, not Rimeveil's wyrm.
Both tail drawings ended in broad, constant-width stroke caps. They were inside
the canvas, so the old no-border-clipping assertions did not catch the missing
taper. Both now use continuous curved silhouettes narrowing to pointed tips.
All 68 affected frames were visually reviewed and remain inside their frames.

New corrected PixelFlow sources: croc `1fc8953f0a948cc9`, hydra
`db998fee96b02ee8`. Earlier candidate sources `2aff30697015da30` and
`2567adb11318d3b6` remain intact; history is
`scripts/fen_slime_tail_sources.txt`. `python3 scripts/fen_slime_redraw.py tails`
creates only these two corrected sources and preserves them on subsequent calls.
The prior candidate PNGs, raw arrays, source registry and drawer are archived at
`/media/raid/valhallasc-data/fen-slime-before-tail-fix-20261103`.

**32 focused browser checks pass** for only croc/hydra, including the new
pointed-tail check across all 52 live poses, all 68 frames clear of borders,
unchanged clips, distinct death poses, portraits and consumed health-bar tops.
Artifacts: `test-results/driver-fQ5oV1`. Scope with `FEN_ART_KINDS=croc,hydra`.
The new profile check rejects all 26 old live poses of **each** creature.
All 170 current saved-editor/export frames still match; rollback/corrupt-backup
refusal and syntax/Swedish/release-note/diff gates pass. No Rimeveil changes.

The original 18 FileDrop reviews have been refreshed. A 19th close-up compares
the previous blunt tails directly to their corrections:
[Corrected tails](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-fen-tails-corrected.png).
Current private label **Beta 1.39.4** supersedes the initial 1.39.3 candidate.
Public art remains unchanged pending owner approval.
