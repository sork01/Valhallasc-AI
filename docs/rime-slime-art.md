# Rimeveil Glacier: slime-style artwork candidate

Released as **Beta 1.39.1** on 2026-11-03 after the owner requested deployment.
Source **2d1d2da**, initially prepared in
`/media/raid/valhallasc-data/rime-slime-work` on `feat/rime-slime-art`, based on
main `9dea2cc`, is merged into main. All seven public art/version/notes hashes
match the tested source; public and bridge health are healthy. The server PID
and executable hash stayed unchanged: this release required no restart or DB work.
Release receipt: `test-results/rime-release-20261103T173005Z.json`.

The four kinds now share Greenmeadow's glossy pixel shading, large white eyes,
highlights, blush and chunky proportions, retaining their frost colours and
anatomy. Kind IDs, production names, asset paths and combat timings are unchanged.

- **Rime Crab:** solid domed carapace, eight jointed legs, two snapping claws,
  eye stalks and frost crystals. Death curls the legs and tips the rigid shell
  onto its side, with a shell fracture. No shell squash or puddle death.
- **Frostfang Wolf:** four jointed legs, frost-tipped tail, ears, muzzle and icy
  spine. Death folds the legs and rolls the animal onto its side.
- **Glacier Yeti:** heavy stepping feet, long arms, blue face, tusks and ice horns.
  Death buckles the knees and topples the furred body; it does not disintegrate
  into stone fragments or flatten into a puddle.
- **Rime Wyrm:** three coils, curved neck, ice crest and biting/frost attack.
  Death spreads the coils and drops the head and neck across its body, with a
  few falling frost particles. Coil thickness remains intact.

Every death clip has eight different poses, and the four final silhouettes differ.
Preview poses were adjusted to keep the wolf/yeti falls inside the existing
frame and to give the wyrm a visibly moving slither. The finished sources were
saved only after the complete frame sheets were inspected.

## Editable sources and pipeline

| Kind | New PixelFlow ID | Preserved previous ID |
| --- | --- | --- |
| crab | 8193e3569a659d6e | ba38273ce296d517 |
| wolf | 55742e3f517a9bc8 | 5bad6f5a073b88f7 |
| yeti | c07c42df83c3f7ae | b813182e8e4bd2d2 |
| wyrm | 0282230513c5c7c0 | 6e6118b24d23d38e |

New prefix `valhallasc_rime_slime_style_`; registry
`scripts/rime_slime_sources.txt`. New indexed arrays:
`scripts/rime_slime_{crab,wolf,yeti,wyrm}_raw.npz`. Historical raw arrays remain.
No previous PixelFlow source was modified or deleted.

```sh
python3 scripts/rime_slime_redraw.py preview
python3 scripts/rime_slime_redraw.py build
python3 scripts/rime_slime_redraw.py export
python3 scripts/rime_slime_redraw.py verify
```

The established `make_rime_sprites.py` CLI delegates to this pipeline. Build
preserves registered sources; both entry points refuse destructive `--replace`.
Export reads the saved editor frames, preserving edits; verify compares those
saved frames directly to the exported atlases. Export derives health-bar tops:
crab 53, wolf 67, yeti 84, wyrm 87; the existing loader already consumes them.

Same 96×96 frame, anchor (48,90), 768×480 atlas, 34 frames per kind:
6 idle at 6fps, 8 walk at 10fps, 8 attack at 12fps, 4 hurt at 10fps,
8 die at 8fps. Only the candidate's four PNGs and `rime.txt` replace old art.
No duplicate old atlas is installed under assets. No renderer, map, stats,
rewards, zone IDs, server or database changes; no rebuild, restart or migration.

## Rollback

External backup `/media/raid/valhallasc-data/rime-slime-original-20261103`
contains the exact four previous PNGs and `rime.txt`, plus hashes and previous
PixelFlow IDs in `manifest.txt`. It is outside the live and candidate trees.

One-command restore when wanted:

```sh
python3 /media/raid/valhallasc-data/rime-slime-work/scripts/rollback_rime_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for dry run. It validates all five sources before writing,
atomically replaces each art file, then verifies the restored hashes. Version
labels and notes are separate from art rollback. Tested on disposable candidate
copies: all five hashes restored; a corrupt backup was refused without changes.
The backup retains the prior live art; the public assets now match the tested new source.

## Focused verification

**56 bounded real-art browser checks pass**: contract, kind/source IDs,
all 136 nonempty unclipped frames, five distinct clips per kind at original
rates/counts, eye whites/gloss, production portraits, derived and consumed tops,
all eight distinct death poses per kind, retained solid bodies, four distinct
final silhouettes, authoritative Rimeveil presence and no browser errors.
Artifacts: `test-results/driver-WTZH1E` (portraits, desktop gameplay per kind,
landscape-phone view, numerical browser report).

All **136 saved-editor/export frames match exactly**, including through the
established CLI's verify command. Proof and atlas hashes:
`test-results/rime-slime/editor-export-proof.json`. Rollback, unchanged live art
and destructive-replace refusal: `test-results/rime-slime/validation.json`.
Python/JavaScript syntax, Swedish generation/check, release-note guard and diff
checks pass. No full suites, grinding, encounter tests or balance/timing sweeps.

```sh
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server bash scripts/test-touch-bounded.sh tests/rime-slime-art.cjs
python3 scripts/rime_slime_review.py review
```

`rime_slime_review.py verify` records pre-deployment rollback/original-live-art
proof and expects the original public art. After release, use
`python3 scripts/make_rime_sprites.py verify` for editor/export equality instead.

## Owner pictures

All **15** files are uploaded to Sork's FileDrop and destination SHA256, size,
dimensions, original filename and MIME metadata verified. Receipt:
`test-results/rime-slime/filedrop-receipt.json`.

- `valhallasc-rime-before.png`, `-after.png`, `-before-after.png`
- `valhallasc-rime-{crab,wolf,yeti,wyrm}-frames.png`
- `valhallasc-rime-{crab,wolf,yeti,wyrm}-animations.gif`
- `valhallasc-rime-{crab,wolf,yeti,wyrm}-death-before-after.gif`

Pictures compare both idle and final death poses at equal 2× scale. Frame sheets
show every pose; GIFs show original animation rates and briefly hold the final
death pose. Upload is a separate explicit `rime_slime_review.py upload` action.

The main TODO queue records the release; next zone is Gloamfen. Greenmeadow and
Crags remain separate private candidates, still labelled 1.39.1. Rebase their
release labels/notes/Swedish keep entries against the current live version before
any later approved deployment. The Greenmeadow work is preserved separately as
`5d4a3ee` on `feat/meadow-slime-art`; it was not included in this release.
