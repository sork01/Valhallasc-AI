# Rimeveil Glacier: slime-style artwork, second pass (v2, Beta 1.39.13 candidate)

**Status (2026-11-04): candidate, not deployed.** The four RIME-SLIME tasks were redone under the 2026-11-04 rules
(distinct attacks, free frame size, feet exactly on the ground row). Branch `feat/rime-slime-redo`, private worktree
`/media/raid/valhallasc-data/rime-slime-redo-work`, based on main `faac43c`. Live art is still the v1 art below until the
owner approves.

## What changed from v1

| Kind | Frame (anchor) | Attack (8 distinct frames) | Death (8 distinct frames) |
| --- | --- | --- | --- |
| Rime Crab | 112x96 (52,90) | Both claws rear up open, then slam down and pinch shut; frost bursts on impact | Legs curl in, the rigid shell rolls over backwards onto its back, claws go slack, crystals chip off |
| Frostfang Wolf | 112x96 (52,90) | Crouch with the head back, pounce forward with open jaws and fangs, recover | Legs fold, the body sinks and ends on its side with stiff legs |
| Glacier Yeti | 112x112 (56,106) | Leans back and throws both fists overhead, then pounds the ice (ice erupts either side) | Knees buckle, the body tips over sideways like a felled tree, head lolls, arms go slack |
| Rime Wyrm | 144x96 (56,90) | Draws back, lunges forward and down with open jaws and a frost-breath cone | The three coils slide apart across the ice, the head drops beside them |

- **Grounding (`QUADRUPED-GROUNDING`):** every living frame's lowest pixel is exactly the anchor row; every death frame
  is snapped to the ground (never sunk, never floating). v1 had crab feet around row 87 and wolf paws near 88.
- **Frame sizes (`docs/kind-frames.md`):** the zone-wide manifest frame stays 96x96 (48,90) as the fallback; the four
  kinds each carry a `kindFrames` entry (the first zone to use it). A larger frame makes the click hitbox larger (it is
  frame-sized): the wyrm's is 144x96 against 96x96 before. The creatures keep the same art pixel scale; the extra room is
  for raised fists, a pounce and the lunge. Server collision, aggro and ranges are untouched.
- **Fixes carried over from owner corrections elsewhere:** the wolf has four separate legs with roots hidden under the
  barrel, a bent hind hock and a diagonal gait (Wyrdwood lesson); the wolf and wyrm tails taper to points, not blunt caps
  (Gloamfen lesson); the wyrm's neck is a chain of shaded balls (a round tube), not a flat ribbon.
- **No whole-image rotation:** v1 rotated whole frames with nearest-neighbour; v2 draws every part from points, and the
  crab shell is a rotated shaded ellipse (`Painter.ball(..., ang=)`), so edges stay clean.

## Pipeline

```sh
python3 scripts/rime_slime_redraw.py preview [kind...]   # sheets in test-results/rime-slime, lists border overruns
python3 scripts/rime_slime_redraw.py build               # NEW PixelFlow sources (prefix valhallasc_rime_slime_style_b_); skips registered kinds
python3 scripts/rime_slime_redraw.py refresh <kinds>     # rewrite a kind's EXISTING source from the drawer (same size only; overwrites editor edits)
python3 scripts/rime_slime_redraw.py export              # reads the SAVED editor frames, writes atlases + rime.txt (tops, kindFrames)
python3 scripts/rime_slime_redraw.py verify              # installed atlases == saved editor frames
```

`make_rime_sprites.py` delegates to it; `--replace` is refused. A frame-size change needs a new source (build skips
registered kinds), so keep the frame table `KIND_FRAMES` stable once built. Sources (registry
`scripts/rime_slime_sources.txt`): crab `02bc13f91cc5aa2a`, wolf `9d1075e53372ade6`, yeti `b8f3b5f515ed7d1a`,
wyrm `04ce35e47b927205`. The v1 sources and raw arrays are kept as `rime_slime_v1_*`; the pre-slime IDs are in the
backup manifests. Health-bar `tops` are derived from the tallest idle pose of each kind's own frame.

## Rollback (two levels)

```sh
# to the live v1 slime art (Beta 1.39.1)
python3 scripts/rollback_rime_art.py --target <checkout> --backup /media/raid/valhallasc-data/rime-slime-v1-20261104 --apply
# to the pre-slime originals
python3 scripts/rollback_rime_art.py --target <checkout> --apply
```

Dry run without `--apply`; both verify every backup hash first. `rime_slime_review.py verify` exercises both on a disposable
copy, plus the corrupt-backup refusal. It is a PRE-deployment check (it asserts the live files are still v1); after a
release use `make_rime_sprites.py verify`.

## Checks

`tests/rime-slime-art.cjs` (89 checks, bounded: `bash scripts/test-touch-bounded.sh tests/rime-slime-art.cjs`, with
`VALHALLA_BINARY` = main's release binary and `NODE_PATH` including main's `node_modules`, run from the worktree):
declared frame via the production `Field.frameOf`, 34 frames clear of every border at each kind's own size, eight distinct
attack and death frames, wind-up / strike / recovery measured against the idle silhouette, grounding on the anchor row for
every living and death frame, colour-exact eye whites (`#edf6f7`; the frost ramps are also near-white, so an RGB>220 test
would pass vacuously), shell and coil material checks, portraits, health-bar tops. Mutations: `MUTATE_KIND=wolf
MUTATE_PNG=<atlas shifted up one row>` fails grounding; a wolf attack row replaced by idle plus one unique pixel per
frame keeps the hashes distinct but fails the wind-up measure.

Pictures: `rime_slime_review.py review | upload` write and upload 19 `valhallasc-rime-redo-*` PNG/GIFs (before = live v1);
the 15 v1 uploads and their receipt are untouched.

---

# v1 (Beta 1.39.1, currently live)

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

The main TODO queue records the release; next zone is Gloamfen. Crags was
subsequently approved and deployed as Beta 1.39.2 (source `bae6ec2`), with all
five public Rimeveil art hashes preserved. Greenmeadow remains a separate
private candidate, preserved as `5d4a3ee` on `feat/meadow-slime-art`; it needs a
fresh release label/notes/Swedish keep entry if later approved for deployment.
