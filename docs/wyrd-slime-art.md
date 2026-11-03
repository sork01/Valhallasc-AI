# Wyrdwood slime-style artwork release

Released as **Beta 1.39.7** on 2026-11-03 after the owner approved the corrected
boar, ram and Oakhorn legs and requested "deploy and finish skill". Source
**d99b36e** from `feat/wyrd-slime-art`, prepared in
`/media/raid/valhallasc-data/wyrd-slime-work`, is merged into main and live.
All **10 public release hashes** and both health endpoints pass; **27 public
art hashes** from Crags, Rimeveil, Gloamfen, Undervault and Greenmeadow are
preserved. Server PID and executable stayed unchanged; no build, restart or
database action. No test flags, new journal errors or public test guest.
Receipt: `test-results/wyrd-release-20261103T190716Z.json`.

Seven new native PixelFlow sources use Greenmeadow's glossy shading, large
white eyes with highlights, blush and chunky proportions. Each retains its
identity and anatomy. Body components keep their dimensions while limbs fold,
cloth drapes or stone components separate; no generic squash/puddle death.

- **Rotfang Boar:** brown bristles, green blight patches and ivory tusks;
  jointed walking and a forward attack. Death folds the legs and drops the
  intact body and head onto the ground.
- **Gallowcrow:** dark blue feathers, golden beak/claws and a bone charm;
  hinged wing flaps and a pecking attack. Death lowers the bird, folds its
  wings, curls its claws and drops loose feathers.
- **Mosshide Troll:** moss-green skin, sprout/mushroom and rigid wooden club;
  heavy jointed steps and a lifted strike. Death buckles the knees, drops the
  club, lowers the torso/head and wilts the small stems.
- **Wyrdweaver:** violet hood/robe, golden threads and a drop spindle;
  swaying cloth and casting hands. Death relaxes the arms, unravels and drops
  the threads, tips the spindle and settles the hood into the draped robe.
- **Stormram:** pale blue fleece, curled gold horns and storm sparks;
  jointed hooves and a forward strike. Death folds the legs, rests the body
  and horns on the ground and extinguishes its sparks.
- **Oakhorn:** moss-backed stag with branching oak antlers, autumn leaves and
  golden markings. Death folds the longer legs and neck, lowers the intact
  body/antlers and sheds falling leaves in a staged elite fall.
- **Hrungnir:** blue-grey granite giant, crystal crown/shoulders, rune and
  lightning beard. Death grows fractures, drops stone fragments, separates
  and slumps the solid components, then extinguishes rune and lightning.

All eight death poses per kind differ; final silhouettes differ across the
seven kinds. All 238 frames, portraits and private gameplay screenshots were
visually inspected. The eight-frame death timing stays unchanged.

## Editable sources

| Kind | New PixelFlow ID | Preserved previous ID |
| --- | --- | --- |
| boar | 7ef72fb866da5857 | ea4b8b54549af551 |
| crow | 6c08b122e9081a38 | be9b4f3aeae92b67 |
| troll | 8235202bf15c25f8 | 0c06e3a6c26a6b0a |
| weaver | f572033866c9eaa8 | 48f4308891f285da |
| ram | 62bd6cef83ff8251 | f90f6997816a8ef7 |
| oakhorn | 1e9c8a7dff65fc61 | b1150a62ee7151d0 |
| hrungnir | a2f64de2fa2f750d | b52981453374ab5f |

Registry `scripts/wyrd_slime_sources.txt`, indexed arrays
`scripts/wyrd_slime_<kind>_raw.npz`, prefix `valhallasc_wyrd_slime_style_`.
Historical source IDs, arrays and rig helpers remain available.

```sh
python3 scripts/make_wyrd_sprites.py preview
python3 scripts/make_wyrd_sprites.py build
python3 scripts/make_wyrd_sprites.py legs  # preserve/reuse corrected leg sources
python3 scripts/make_wyrd_sprites.py export
python3 scripts/make_wyrd_sprites.py verify
```

The CLI delegates to `wyrd_slime_redraw.py`; both entry points refuse
`--replace`. Build preserves registered sources; export reads saved editor
frames rather than rerendering them. Verify compares the saved editor pixels
directly against atlas pixels. Health tops are derived from those exports:
57/71/86/86/58/86/87 in kind order; the existing loader consumes them.

Same 96×96 frame, anchor (48,90), 768×480 atlas and 34 frames per kind:
6 idle at 6fps, 8 walk at 10fps, 8 attack at 12fps, 4 hurt at 10fps,
8 die at 8fps. Seven existing PNG paths plus `wyrd.txt` replace the old art
in the release; no duplicate old atlases remain under assets.
No map, stats, combat timings, rewards, zone IDs, renderer, server, database or
music changes. No build, restart, migration, grinding or fight/balance sweeps.

## Rollback

External `/media/raid/valhallasc-data/wyrd-slime-original-20261103` contains the
seven previous PNGs and `wyrd.txt`, with all eight SHA256 hashes and previous
PixelFlow IDs in `manifest.txt`. It is outside live and candidate trees.

```sh
python3 /media/raid/valhallasc-data/wyrd-slime-work/scripts/rollback_wyrd_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run without `--apply`. The command preflights the exact file set, all source
hashes and target paths before writes, replaces each file atomically and
verifies restored hashes. Actual restoration on disposable candidate copies
passes; a corrupt backup is refused without changes. Version labels and notes
are separate from artwork rollback.

## Focused verification and pictures

**102 initial bounded real-art browser checks passed**, using the existing production
binary with a private server/database. Coverage: all 238 nonempty/unclipped
frames, original counts/rates, distinct motion in all five clips, readable
eyes, source IDs, target portraits, derived and consumed health tops, eight
unique death poses per kind, retained solid anatomy/cloth, fallen poses below
living poses, distinct final silhouettes, authoritative zone 6 presence and
no browser errors. Artifacts: `test-results/driver-ejKYh8`.

All **238 saved-editor/export frames match exactly** through the established
CLI. `test-results/wyrd-slime/editor-export-proof.json` records frame and atlas
hashes; `validation.json` records rollback, corrupt-backup refusal, destructive
build refusal and unchanged live art. Python/JavaScript syntax, Swedish check,
release-note guard and diff checks pass. No full suites run.

```sh
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server bash scripts/test-touch-bounded.sh tests/wyrd-slime-art.cjs
python3 scripts/wyrd_slime_review.py review
python3 scripts/wyrd_slime_review.py verify
python3 scripts/wyrd_slime_review.py upload
```

All **26 FileDrop PNG/GIF previews** have destination SHA256, size, dimensions,
original filename and MIME metadata verified. Receipt:
`test-results/wyrd-slime/filedrop-receipt.json`. Upload is a separate operation.
Review `verify` expects original live files; after approved deployment use the
maker CLI's `verify` for saved-editor equality.

- `valhallasc-wyrd-before.png`, `-after.png`, `-before-after.png`
- `valhallasc-wyrd-{kind}-frames.png` (all 34 frames)
- `valhallasc-wyrd-{kind}-animations.gif` (all five clips at original rates)
- `valhallasc-wyrd-{kind}-death-before-after.gif` (equal-scale deaths)

[Before/after comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-wyrd-before-after.png).
Next unfinished zone: **Bifrost Reach**. Owner approval and public release
verification are recorded above.

## Owner leg-placement correction (private Beta 1.39.7)

The owner flagged the boar, ram and Oakhorn legs. Their near/far limbs overlapped
and long exposed leg roots started high on the flanks, reading as two poles.
The correction hides upper roots beneath the barrel, places them at the shoulder
and haunch, bends rear stifles/hocks, tapers the shins and staggers four hooves
across the perspective plane. Darker, narrower far legs land higher than near
legs; diagonal pairs alternate during walking. Each animal retains its fitting
folding-leg death and solid body size. All other enemy atlas bytes are unchanged.

New native PixelFlow sources: boar `7ef72fb866da5857`, ram `62bd6cef83ff8251`,
Oakhorn `1e9c8a7dff65fc61`. Earlier candidate sources remain in
`scripts/wyrd_slime_leg_sources.txt`; prior candidate art/arrays/registry/script
and hashes are archived at
`/media/raid/valhallasc-data/wyrd-slime-before-leg-fix-20261103`.
The original live-art rollback backup remains intact. Both CLIs expose `legs`
to preserve/reuse the corrected sources; no destructive source replacement.

**49 focused browser checks pass** on only these three creatures:
`test-results/driver-O1jU8L`. The new lower-leg separation assertion reads four
separate tracks in all six idle poses for each animal. All 18 earlier candidate
poses read only two tracks and fail that condition; proof:
`test-results/wyrd-slime/leg-placement-proof.json`. All 238 saved-editor/export
frames still match and rollback/corrupt-backup checks pass. Before deployment,
all eight live art hashes were confirmed unchanged. The first correction browser attempt was blocked before
art assertions by the release-notes popup; the fixture now seeds its current
version in `valhallasc.whats-new.v1`. No application flow change was needed.
The 102 initial checks remain historical evidence for the other four creatures.

All 24 original review files are refreshed and two correction files added;
all **26** destinations have verified hashes and metadata. Updated receipt is
`test-results/wyrd-slime/filedrop-receipt.json`.

- [Previous candidate versus corrected legs](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-wyrd-legs-corrected.png)
- [Walking comparison at the original rate](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-wyrd-legs-walk-before-after.gif)

Owner approved these corrected legs and deployment. The tested source and
public release verification are recorded above.
