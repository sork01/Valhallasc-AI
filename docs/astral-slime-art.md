# Astralhollow enemy artwork (Beta 1.39.20 candidate)

**Candidate prepared 2026-11-04 as Beta 1.39.20** in `/media/raid/valhallasc-data/astral-slime-work` on `feat/astral-slime-art` (base `62d26dc`, awaiting owner review of FileDrop pictures). Client-only: no server, map, stats, timings, rewards, zone, DB or music change; no rebuild or restart.

Five new editable PixelFlow sprites for Zone 13 (Astralhollow) use the shared slime style: glossy multi-stop shading, large eyes with `#fffbea` eye whites and highlights, warm blush and chunky readable silhouettes. Each kind has its own wider/taller frame in `client/assets/astral.txt` (`kindFrames`) so raised nebula wings, crystal jaws,scarab horns, thorny vines and meteorite fists never clip, plus 8 distinct attack frames (wind-up, strike, recovery) and 8 distinct material-appropriate death frames.

| Kind | Frame (`w×h`, anchor) | Motion, attack and fitting death | New PixelFlow ID | Previous ID | Top (new / old) |
| --- | --- | --- | --- | --- | --- |
| Void Moth (`voidmoth`) | `132×98` `(54, 92)` |Plump lavender-and-indigo nocturnal moth hovering in mid-air (`lows=64..78 <= kay-14`) with four scalloped nebula wings bearing golden crescent-and-star eyespots, feathered antennae and a hanging starlight lantern. Banks back with all four wings swept high to charge a starlight orb (`rises=12`), then swoops forward (`reach=34`) firing a volley of starlight bolts. On death, it tumbles from mid-air and folds its wings flat on the ground row (`kay=92`) as its lantern dims. | `580586199f4e6879` | `16f1579889ca68a9` | `66 / 88` |
| Crystal Wyrm (`crystalwyrm`) | `148×100` `(60, 94)` | Low-slung azure-and-cyan crystalline drake grounded on four distinct clawed paws (`groundRuns=4`, `legTracks=4`) with faceted belly scales, magenta dorsal prism spines and horned crystal crest. Rears up as its dorsal prisms flare (`rises=14`) and lunges far forward (`reach=44`) snapping its jaws with a crystal frost-shard breath. On death, its legs splay out and it collapses flat onto its belly on row 94 as its dorsal prisms crack. | `af24bb7845f50e67` | `c4dbc00ed0a20cc4` | `68 / 60` |
| Orbit Beetle (`orbitbeetle`) | `140×100` `(54, 94)` | Round-shelled golden-amber astral scarab grounded on four distinct claw groups (`groundRuns=4`, `legTracks=5`) with constellation-engraved elytra, a tall forked rhinoceros horn and an orbiting golden moonlet above a violet underwing. Rears its carapace high (`rises=14`) and swings its forked horn in a wide uppercut (`reach=46`) while its moonlet streaks forward in a starry arc. On death, it flips onto its back on row 94 with its legs curled upward and the moonlet resting beside it. | `dcb7647f8ef1658c` | `c779c03de017e0e6` | `69 / 70` |
| Eclipse Dryad (`eclipsedryad`) | `132×114` `(52, 108)` | Leafy emerald-and-mossy sylvan spirit grounded on two wooden root-boots (`groundRuns=2`) in a layered leaf-petal skirt with a glowing pink blossom core, bark arms and a golden solar-eclipse halo crown. Lifts her eclipse halo high overhead (`rises=16`) and lashes a thorny vine whip far forward (`reach=43`) with bursting star-leaves. On death, her bark knees buckle, her eclipse crown dims, and she wilts into a mossy mound of leaves on row 108. | `f042853483dd824a` | `2d35cbaf0e90a3a6` | `78 / 89` |
| Meteor Golem (`meteorgolem`) | `136×112` `(56, 106)` | Chunky slate-violet meteorite construct grounded on two stone boots (`groundRuns=2`) with a glowing orange-and-violet core fissure, purple shoulder crystals, cratered stone fists and orbiting asteroid pebbles. Hoists both meteorite fists high overhead (`rises=19`) and slams them into the ground (`reach=33`) with an impact shockwave of flying shards. On death, its core goes dark and its meteorite boulders crack apart into a low rubble pile on row 106. | `20f02bb4828b9527` | `3b03b821e34145c5` | `74 / 79` |

## Pipeline

```sh
python3 scripts/astral_slime_redraw.py preview|extents|build|refresh|export|verify
```
Registry `scripts/astral_slime_sources.txt`, raw arrays `scripts/astral_slime_<kind>_raw.npz`, PixelFlow name prefix `valhallasc_astral_slime_style_`. `build` refuses `--replace` and never deletes old sprites; `export` reads the saved editor frames back from PixelFlow and writes `test-results/astral-slime/editor-export-proof.json`.

**Grounding (`QUADRUPED-GROUNDING`):** the four grounded kinds (`crystalwyrm`, `orbitbeetle`, `eclipsedryad`, `meteorgolem`) rest their lowest pixel on `kay` (`r.low === kay`) in every living and death frame, with 4 separate grounded leg groups (`groundRuns === 4`, `legTracks >= 4`) in all 6 idle frames and `>= 2` in every walk step for `crystalwyrm` and `orbitbeetle`, and 2 grounded feet (`groundRuns === 2`) in idle for `eclipsedryad` and `meteorgolem`. The flying `voidmoth` hovers in mid-air (`r.low <= kay - 12`) across all living clips and falls onto `kay` on death (`die.at(-1).low === kay`).

## Rollback

`/media/raid/valhallasc-data/astral-slime-original-20261104` holds the five pre-change PNGs, `client/assets/astral.txt`, and `manifest.txt` (SHA256 hashes, old PixelFlow IDs, old `tops`, `oldFrames: {}`).
```sh
python3 scripts/rollback_astral_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```
Dry run without `--apply`; preflights every backup file hash before writing and restores `client/assets/astral.txt` and all five `astral_<kind>.png` atlases in one command.

## Verification

* `python3 scripts/astral_slime_review.py review|verify|upload`: builds the 24 FileDrop comparison sheets, per-kind 34-frame sheets and original-rate GIFs, verifies all 170 saved editor frames match the exported atlases, tests the rollback script (including rejecting a corrupt backup), confirms live `/home/serveperry/webserver/www/Valhallasc` files are untouched, and uploads the 24 files to FileDrop.
* Bounded real-art browser test:
  ```sh
  PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright \
  NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules \
  VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server \
  bash scripts/test-touch-bounded.sh tests/astral-slime-art.cjs
  ```
  Runs 123 checks across all five Astralhollow kinds in Zone 13, with mutation controls (`MUTATE_KIND` + `MUTATE_PNG`) for floating feet and still-attack frames.
