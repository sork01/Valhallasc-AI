# Bifrost Reach enemy artwork release

Released as **Beta 1.39.8** on 2026-11-03 after the owner requested
"deploy and finish skill". Source **5f6e9d4** from `feat/bifrost-slime-art`,
prepared in `/media/raid/valhallasc-data/bifrost-slime-work`, is merged into
main and live. All four BIFROST-SLIME deliverables are complete.

All **eight public release hashes** and both health endpoints pass; **35 public
artwork hashes** from other zones are preserved. Server PID and executable
stayed unchanged, with no test flags, new journal errors or public test guests.
No build, restart or database action. Receipt:
`test-results/bifrost-release-20261103T192930Z.json`.

Five original editable PixelFlow sprites use Greenmeadow's glossy shading,
large white eyes with highlights, blush and chunky shapes. Bodies retain
their dimensions; limbs, fins, armour and feathers move independently.

| Kind | Motion and fitting death | New PixelFlow ID | Previous ID |
| --- | --- | --- | --- |
| Galehound | Four jointed legs with distinct near/far feet, bent hind joints and diagonal walking pairs; legs fold, solid body/head fall and lightning expires. | eb5eadd388c59b4b | 6d5cf7b281374693 |
| Prism Golem | Jointed faceted crystal components; fractures spread, shards drop and the separated pieces slump. | 49c6de45376a59e7 | f14c439c4371063e |
| Skyray | Smooth triangular manta fins and a tapered whipping tail; body descends, fins curl inward and the tail settles. | bc4e43f2eeae58ed | a06176aa5f7453a3 |
| Hollow Einherjar | Rigid horned helmet, plate, shield and rotating sword; spectral wisps rise and vanish while empty armour falls and the sword settles flat. | b264885a2869eeb3 | 76225da74618c01c |
| Thunderroc | Blue hinged wing feathers, white head, brown breast and golden beak/claws; wings fold, claws curl, feathers fall and lightning expires. | e55dd3cfa101cf61 | 55be297c758f1e60 |

All 170 frames, five production portraits and five private gameplay screenshots
were visually inspected. All eight death poses per kind differ; final death
silhouettes differ across all five kinds. No generic squash or puddle death.
The original eight-frame death duration is preserved.

## Pipeline

```sh
python3 scripts/make_sky_sprites.py preview
python3 scripts/make_sky_sprites.py build
python3 scripts/make_sky_sprites.py export
python3 scripts/make_sky_sprites.py verify
```

The existing CLI delegates to `bifrost_slime_redraw.py`. Both build entry points
refuse destructive `--replace`; registered sources are preserved. Export reads
saved editor frames instead of rerendering them. Verify directly compares all
170 saved editor frames with installed atlas pixels. Registry:
`scripts/bifrost_slime_sources.txt`; arrays:
`scripts/bifrost_slime_<kind>_raw.npz`; new source prefix:
`valhallasc_bifrost_slime_style_`. Drawing uses the established Wyrdwood Painter
and base palette, extended with storm blue and warm eagle brown.
Historical art code, arrays and source IDs remain available.

Same 96×96 frame, anchor (48,90), 768×480 atlas and five-clip contract:
6 idle at 6fps, 8 walk at 10fps, 8 attack at 12fps, 4 hurt at 10fps,
8 die at 8fps. Export derives health tops **68/89/71/86/83**, consumed by the
existing production loader. The five existing `sky_<kind>.png` paths and
`sky.txt` replace the old art in the release; no duplicate old atlases
are left under assets.

No map, stats, combat timings, rewards, zone IDs, renderer, server, database or
music changes. No rebuild, restart, migration, grinding or encounter sweeps.
Version label, release notes and Swedish keep list carry the release version;
Swedish data is regenerated and byte-identical. Future releases must read the live label before choosing their version.

## Rollback

External `/media/raid/valhallasc-data/bifrost-slime-original-20261103` contains
all five original PNGs and `sky.txt`. `manifest.txt` records six SHA256 hashes,
previous PixelFlow IDs and base revision. It is outside live and candidate trees.

```sh
python3 /media/raid/valhallasc-data/bifrost-slime-work/scripts/rollback_bifrost_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for a dry run. The command preflights the exact file set, every
source hash and target path, replaces each file atomically and verifies restored
hashes. Actual restoration on disposable candidate copies passed; a corrupt
backup was refused before any target changed. Version/notes rollback is separate.

## Focused verification

**75 bounded real-art browser checks pass** with the current production binary
and a private server/database: all 170 nonempty frames clear of borders,
original counts/rates, animated clips, readable eyes, five new source IDs,
production portraits, derived/consumed health tops, eight distinct death poses
per kind, retained solid anatomy, lowered final poses, four separate Galehound
lower legs in every idle pose, distinct final silhouettes, authoritative zone 7
presence and no browser errors. Artifacts: `test-results/driver-9wqZvo`.

A deliberate frozen Galehound death atlas is rejected by the browser check's
`die preserves timing and animates distinctly` assertion. Mutation is served
only through a private Playwright route; neither live nor candidate art was
changed. Evidence: `test-results/bifrost-slime/mutation-proof.json` and
`mutation.log`. No full suites or fight tests run.

All **170 saved-editor/export frames match exactly**, using the established
maker CLI. `test-results/bifrost-slime/editor-export-proof.json` records frame
and atlas hashes; `validation.json` records frame count, rollback, corrupt-backup
refusal, destructive-build refusal, unchanged live art, browser run, mutation
and verified FileDrop count. Python/JavaScript syntax, Swedish consistency,
release-note guard and diff checks pass.

```sh
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server bash scripts/test-touch-bounded.sh tests/bifrost-slime-art.cjs
python3 scripts/bifrost_slime_review.py review
python3 scripts/bifrost_slime_review.py verify
python3 scripts/bifrost_slime_review.py upload
```

Review `verify` expects original live files; after deployment use maker `verify`
for editor equality. Upload is a separate operation. Preview preparation caught
crystal-body/wing edge collisions and an oversized helmet plume; owning geometry
was corrected before source export. A repeated early fracture pose was corrected
in the newly created native source to retain eight distinct death poses.

## FileDrop review

All **18 PNG/GIF previews** are uploaded and SHA256, size, dimensions, original
filename and MIME metadata verified. Receipt:
`test-results/bifrost-slime/filedrop-receipt.json`.

- [Before/after comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-before-after.png)
- [Before](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-before.png)
- [After](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-after.png)
- [Galehound death comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-galehound-death-before-after.gif)
- [Prism Golem death comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-prismgolem-death-before-after.gif)
- [Skyray death comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-skyray-death-before-after.gif)
- [Hollow Einherjar death comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-einherjar-death-before-after.gif)
- [Thunderroc death comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-thunderroc-death-before-after.gif)

Each kind also has `valhallasc-bifrost-<kind>-frames.png` (all 34 poses) and
`valhallasc-bifrost-<kind>-animations.gif` (all five clips at original rates).
Next unfinished zone: **Rán's Deep**. Greenmeadow remains a separate private
candidate. The owner approved Bifrost's pictures and deployment; public release
verification is recorded above.

## Redo v2 release (2026-11-04, **Beta 1.39.17**, `feat/bifrost-slime-redo`)

Prepared in `/media/raid/valhallasc-data/bifrost-slime-redo-work` for the four
reopened `BIFROST-SLIME-*` tasks and deployed as **Beta 1.39.17** after the
owner approved the flying Skyray with its aerial whip tail and requested
"deploy and /finish".

Every Bifrost Reach kind now uses its own measured `kindFrames` entry in
`client/assets/sky.txt` (via `kindframe.set_kind_frame`), has eight distinct
attack frames (wind-up, strike with weapon/arc/bolt reach, and recovery to the
idle silhouette), and satisfies `QUADRUPED-GROUNDING` (all four grounded kinds
rest their lowest pixel on `kay` in every living and death frame; the flying
Skyray hovers well above `kay` with its tapered whip tail in mid-air and falls
onto `kay` on death):

| Kind | Frame & anchor (`w×h`, `ax,ay`) | Top | New v2 PixelFlow ID | Preserved v1 ID |
| --- | --- | --- | --- | --- |
| Galehound | `124×76`, `(54,70)` | 60 | `7450f8bb136a9936` | `eb5eadd388c59b4b` |
| Prism Golem | `120×102`, `(52,96)` | 85 | `f352194463eb9ae2` | `49c6de45376a59e7` |
| Skyray | `120×74`, `(52,68)` | 49 | `2837ad79482c989d` | `bc4e43f2eeae58ed` |
| Hollow Einherjar | `120×102`, `(46,96)` | 81 | `a78dbd54dc6acfa6` | `b264885a2869eeb3` |
| Thunderroc | `130×82`, `(47,76)` | 66 | `0689197b87d81900` | `e55dd3cfa101cf61` |

- **Two-level rollback:** `scripts/rollback_bifrost_art.py` defaults to
  `/media/raid/valhallasc-data/bifrost-slime-v1-20261104` (live Beta 1.39.8 v1
  art); `/media/raid/valhallasc-data/bifrost-slime-original-20261103` retains
  the pre-slime originals. Both rollbacks and corrupt-backup refusal are verified
  on disposable copies by `python3 scripts/bifrost_slime_review.py verify`. The
  v1 drawer, registry and `.npz` arrays are preserved in
  `scripts/bifrost_slime_v1_*`.
- **116 bounded real-art browser checks pass** (`tests/bifrost-slime-art.cjs`),
  covering `Field.frameOf` per-kind frame sizes, 170 nonempty/unclipped frames,
  8 distinct attack frames with wind-up/strike/recovery thresholds, 8 distinct
  death frames, exact `r.low === kay` grounding for all 170 frames, 4 Galehound
  idle ground runs and 4 lower-leg tracks (`>= 2` in walk), 2 idle ground runs
  for Prism Golem, Hollow Einherjar and Thunderroc, `#fffbea` eye whites,
  portraits, derived health-bar tops, and Zone 7 presence. Both floating-frame
  and fake-attack mutation controls (`MUTATE_KIND` + `MUTATE_PNG`) fail at their
  targeted assertions.
- **23 `valhallasc-bifrost-redo-*` FileDrop PNG/GIFs** are uploaded and verified
  (`test-results/bifrost-slime/filedrop-receipt-redo.json`):
  - [Before/after comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-redo-before-after.png)
  - [After (v2)](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-redo-after.png)
  - [Attack frames 1–8 before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-bifrost-redo-attacks-before-after.png)
  - Per-kind `valhallasc-bifrost-redo-<kind>-{frames.png,animations.gif,attack-before-after.gif,die-before-after.gif}`
