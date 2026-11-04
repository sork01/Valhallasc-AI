# Gloamfen: slime-style artwork, second pass (v2, Beta 1.39.14 candidate)

**Status (2026-11-04): candidate, not deployed.** The four FEN-SLIME tasks were redone under the 2026-11-04 rules (distinct
attacks, free per-kind frame size, feet exactly on the ground row). Branch `feat/fen-slime-redo`, private worktree
`/media/raid/valhallasc-data/fen-slime-redo-work`, based on main `a6dd9bb`. Live art is still the v1 art (Beta 1.39.4, below)
until the owner approves.

| Kind | Frame (anchor) | Attack (8 distinct frames) | Death (8 distinct frames) |
| --- | --- | --- | --- |
| Fen Toad | 112x96 (44,90) | Crouches, throat sac puffs, long sticky tongue lashes out, snaps back | Legs go limp, tips over backwards onto its back |
| Mire Crocodile | 120x96 (56,90) | Rears back with jaws open wide, lunges, snaps shut (spray), tail whips the other way | Body sinks, legs splay flat, jaw drops slack, tail slumps |
| Drowned Knight | 120x108 (56,102) | Sword raised up and back (behind the head), cuts down in an arc with a light trail, recovers | Knees buckle, suit slumps forward, helmet rolls clear, sword and shield clatter down |
| Mire Hydra | 128x108 (50,102) | Side heads draw back, central head rears up then strikes forward/down with fangs, right head snaps a beat later | Three necks drop at different times, heads lie across the body |
| Gloomroot Colossus | 112x116 (52,110) | Both fists overhead, hammered into the ground (roots burst up), recover | Knees buckle, trunk splits and slumps, branches drop, heart goes out |

- **Grounding (`QUADRUPED-GROUNDING`):** every living frame's lowest pixel is the anchor row (feet use `foot()`: integer radius,
  centre y = radius); every death frame is snapped to the ground. The v1 feet sat on rows 87-89. The toad walk is a waddle (a
  forefoot and a hind foot always planted), no airborne hop.
- **Owner rules carried over:** crocodile and hydra tails taper to a point (`Painter.tail`; the tail-profile check is ported to
  the test); croc/hydra legs have roots under the barrel, a bent rear joint, planted feet and a diagonal gait; hydra necks are a
  chain of shaded balls (a round tube); fangs and teeth are drawn over the jaw with an outline; no whole-image rotation (the toad
  death turns every part from points).
- **Frame sizes:** the zone-wide manifest frame stays 96x96 (48,90) as fallback; each kind carries a `kindFrames` entry. The
  creatures keep the same art pixel scale; the click hitbox comes from the idle art, the shadow widens with frame width
  (toad 1.17x, croc/knight 1.25x, hydra 1.33x). Server collision is untouched.
- **Open for the owner's eye:** the toad death (belly-up, legs in the air) is the one pose that rotates; the knight's wind-up
  sword is drawn behind the head.

## Pipeline

```sh
python3 scripts/fen_slime_redraw.py preview [kind...]  # sheets in test-results/fen-slime; lists border/grounding problems
python3 scripts/fen_slime_redraw.py build              # NEW PixelFlow sources (prefix valhallasc_fen_slime_style_b_); skips registered kinds
python3 scripts/fen_slime_redraw.py refresh <kinds>    # rewrite a kind's EXISTING source from the drawer (same size only; overwrites editor edits)
python3 scripts/fen_slime_redraw.py export             # reads the SAVED editor frames, writes atlases + fen.txt (tops, kindFrames)
python3 scripts/fen_slime_redraw.py verify             # installed atlases == saved editor frames
```

`make_fen_sprites.py` delegates to it; `--replace` is refused. Sources (`scripts/fen_slime_sources.txt`): toad `c9f2500768e0086c`,
croc `b45c848cc65ed92d`, knight `9fe2f23b14e9b9dc`, hydra `74f7f2e45ef00f4f`, gloomroot `ed49cdd88e2c5ff2`. The v1 sources and
arrays are kept as `fen_slime_v1_*` (`fen_slime_tail_sources.txt` untouched); pre-slime IDs are in the backup manifests.

## Rollback (two levels)

```sh
# to the live v1 slime art (Beta 1.39.4)
python3 scripts/rollback_fen_art.py --target <checkout> --backup /media/raid/valhallasc-data/fen-slime-v1-20261104 --apply
# to the pre-slime originals
python3 scripts/rollback_fen_art.py --target <checkout> --apply
```

Dry run without `--apply`; every backup hash is verified first. `fen_slime_review.py verify` exercises both on a disposable copy
plus the corrupt-backup refusal; it is a PRE-deployment check (asserts the live files are still v1). After release use
`make_fen_sprites.py verify`.

## Checks

`tests/fen-slime-art.cjs` (110 checks, bounded: `bash scripts/test-touch-bounded.sh tests/fen-slime-art.cjs`, with
`PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright`, `VALHALLA_BINARY` = main's `target/release/valhalla-server` and
`NODE_PATH` including main's `node_modules` when run from a worktree): declared frames via `Field.frameOf`, eight distinct attack
frames with measured wind-up and strike (hydra: central head comes down), recovery returns to idle, eight distinct death frames,
every living and death frame on the anchor row, exact eye white `#f7fff0`, `tops`, portraits, tail-profile check, rigid mass
kept in death, production health-bar tops. Mutation controls (`MUTATE_KIND=croc MUTATE_PNG=<png> FEN_ART_KINDS=croc`): an atlas
shifted up one row fails grounding; an attack row replaced by shifted idle fails the wind-up measure.

`fen_slime_review.py review|verify|upload` makes the 23 `valhallasc-fen-redo-*` pictures (before = live v1) and uploads them
(separate explicit step).

---

# Gloamfen: slime-style artwork release (v1)

Released as **Beta 1.39.4** on 2026-11-03 after the owner approved the corrected
tails and requested deployment and the finish skill. Source **ceef9d2** from
`feat/fen-slime-art`, prepared in `/media/raid/valhallasc-data/fen-slime-work`,
is merged into main and live. Eight public release hashes and both health
endpoints pass; 13 existing Crags/Rimeveil/Greenmeadow art hashes are preserved.
Server PID/executable stayed unchanged: no restart, build or database work.
Receipt: `test-results/fen-release-20261103T182754Z.json`.

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
The six original live art files matched backup hashes before deployment;
public Gloamfen files now match the approved replacement sources.

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
Next unfinished zone: **The Undervault**. Live is **Beta 1.39.4**; the separate
Greenmeadow Ironhide candidate remains private and needs its own approval.

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
Released **Beta 1.39.4** supersedes the initial private 1.39.3 candidate.
The owner approved these corrections, and the public files are verified.
