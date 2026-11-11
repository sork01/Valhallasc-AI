# The Seed Vault enemy art candidate

Prepared 2026-11-11 in `/media/raid/valhallasc-data/seedvault-slime-work`, branch `feat/seedvault-slime-art`. Private, awaiting picture approval under the enemy remake rules in `TODO.md`. Proposed Beta 1.43.1; reconcile the live version before eventual deployment.

Eight native, editable PixelFlow sources (six dungeon encounters plus two Worldseed boss-mechanic helpers), 272 frames total. Each has a 176×172 frame with anchor `(88, 164)`, eight distinct wind-up/strike/recovery frames and eight distinct death frames. Original timing is preserved: `idle` 6, `walk` 10, `attack` 12, `hurt` 10 and `die` 8 fps. The shared Cathedral manifest keeps its 96×96 fallback, `(48, 90)` anchor and all other 138 kinds (`146 - 8 = 138`). Art only; encounters, stats, maps and server code are unchanged.

| Kind | PixelFlow source | Identity and attack | Death |
| --- | --- | --- | --- |
| `seed_mote` | `359353a06a459b31` | Floating golden-brown seed husk with twin sprout leaves, slanted slit eyes and fanged split mouth; rears back and lunges leaves-first | Descends onto the ground and splits along its seam into two cracked husk halves with wilted leaves |
| `seed_amberwing` | `019c2b1d1989fdac` | Four-winged amber and honey moth with dark crimson-centered ocelli, faceted compound eyes, mandibles and proboscis; folds back and dives | Descends to the ground, folds wings inward, curls all six legs under its thorax and droops antennae |
| `seed_rootguard` | `87dbe7bb469121c9` | Bark-armoured sentinel on two planted root-feet, three-leaf war-helm, vertical slit eyes, wooden tusks, ribbed buckler and sap-amber root club; braces shield and swings club | Knees buckle and torso topples forward onto the ground while rigid bark shield and club retain their mass |
| `seed_warden` | `adc206a4a5734702` | Golden-bark robed keeper with concentric tree-ring halo, three emerald ring-eyes, ring buckler and Ring Staff; draws staff high and thrusts forward | Collapses into its robe heap while rigid concentric gold rings and staff head stay intact |
| `seed_germinator` | `9407aa92547dcaae` | Quadruped carnivorous pod on four vine-stalk legs with seven magenta petals, four hunter eyes, thorn maw and two barbed whip-vines; coils vines and lashes forward | Vine legs splay outward, petals droop and the pod settles low onto the ground |
| `seed_worldseed` | `1f0805a5731e983c` | Ancient golden-brown Worldseed shell on four root pillars with blazing fissure eye, side slit eyes, sweeping root tendrils and triple canopy crown; rears up and slams forward | Root pillars splay, shell splits into two tilted halves on the ground and the inner fissure gutters out |
| `seed_sprout` | `eb156dd6173dfd20` | Boss-mechanic helper: squat horned acorn-cap pod on two stubby root-feet with golden brow-gem, glowering eyes, fanged grin and leaf-dagger; winds up and stabs | Topples onto its side with solid acorn cap and seed hull intact |
| `seed_treant` | `2fde0d88c7ed35cc` | Boss-mechanic helper: knotted bark treant on two root-legs with pink blossom crown, glowing sap-core, emerald-slit hollows, root buckler and blossom-tipped bough; swings bough | Buckles downward onto the ground with solid bark trunk and blossom crown preserved |

`seed_mote` and `seed_amberwing` hover at least 12 pixels above the anchor row (`164`) during all living clips and descend monotonically onto `164` on death. The other six stay grounded on row `164` across all 34 frames. Shapes use clean shaded bands without checkerboard dither; faces are distinct creature designs without shared round-eye or blush overlays.

## Pipeline

```sh
python3 scripts/seedvault_slime_redraw.py preview
python3 scripts/seedvault_slime_redraw.py extents
python3 scripts/seedvault_slime_redraw.py build
python3 scripts/seedvault_slime_redraw.py export
python3 scripts/make_seed_vault_sprites.py verify
python3 scripts/seedvault_slime_review.py review
python3 scripts/seedvault_slime_review.py verify
python3 tests/seedvault-materials.py
```

`seedvault_slime_models.py` contains the eight articulated models. Registry: `scripts/seedvault_slime_sources.txt`. `build` preserves saved sources and refuses `--replace`; `refresh KIND...` overwrites only the named editor frames. `export` reads the saved editor, preserves hand edits and derives health-bar tops from idle bounds. `make_seed_vault_sprites.py` retains its imported helpers (used by `boss_helper_art.py`) and delegates `preview`, `extents`, `build`, `refresh`, `export` and `verify` to `seedvault_slime_redraw`. `dungeon_cel.py seed_vault build|preview` delegates before the legacy deletion path.

## Backup and rollback

Nine originals (`client/assets/cathedral.txt` and the eight `client/assets/cathedral_<kind>.png` atlases), SHA-256 hashes, byte sizes, dimensions and old PixelFlow IDs are saved outside the served tree at `/media/raid/valhallasc-data/seedvault-slime-original-20261111`.

```sh
python3 scripts/rollback_seedvault_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run by default. All backup sources and destinations are validated before writes. Restoring on a disposable copy, refusing a corrupt backup and refusing an unrelated Cathedral-manifest edit all pass. Rollback never deletes old or new PixelFlow sources.

## Focused checks

Bounded real-client batches (`tests/seedvault-slime-art.cjs` via `scripts/test-touch-bounded.sh`) verify all eight kinds in two 4-kind batches (the six awake dungeon encounters by teleporting to their Zone 33 spawns, plus the two sleeping ambush helpers `seed_sprout` and `seed_treant` loaded into `Field.cathedralSprites.img` and rendered in-world), checking 176×172 per-kind frames, `(88, 164)` anchors, 1408×860 atlases, 146 total Cathedral kinds, clip frame rates, 34 non-empty non-clipped cells, 8 distinct attack and death frames, forward strike reach, grounding/hovering, monotonic flying descent, health-bar tops and zero page errors. Routing the original `cathedral_seed_mote.png` into the production loader fails the frame-contract check as expected.

Exported-art material assertions (`tests/seedvault-materials.py`) verify split seed shells (`seed_mote`, `seed_worldseed`), folded chitin wings (`seed_amberwing`), solid toppled bark/rings (`seed_rootguard`, `seed_warden`, `seed_sprout`, `seed_treant`) and wilted petals/pod (`seed_germinator`), and fail under `MUTATE_KIND=seed_mote`.

## Review pictures

All 37 PNG/GIF review files (`5 + 8 * 4`) uploaded to FileDrop and verified against local SHA-256, metadata, MIME, byte counts and dimensions (`test-results/seedvault-slime/filedrop-receipt.json`):

- [Before/after](https://gunning.se/filedrop/?download=valhallasc-seedvault-before-after.png)
- [Attacks](https://gunning.se/filedrop/?download=valhallasc-seedvault-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/?download=valhallasc-seedvault-deaths-before-after.gif)

Next enemy group: The Sunken Astrolabe (`ASTROLABE-SLIME-ART`).
