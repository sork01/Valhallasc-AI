# Coral Reliquary enemy artwork (Beta 1.39.18)

**Deployed 2026-11-04 as Beta 1.39.18** (owner approved FileDrop pictures: "deploy and /finish"; source `2a782fd` from `/media/raid/valhallasc-data/reliquary-slime-work` on `feat/reliquary-slime-art`, base `2c8f7fc`). Client-only: no server, map, stats, timings, rewards, zone, DB or music change; no rebuild or restart.

Six new editable PixelFlow sprites for Zone 11 (The Drowned Cathedral — Coral Reliquary) use the shared slime style: glossy multi-stop shading, large eyes with `#fffbea` eye whites and highlights, warm blush and chunky readable silhouettes. Each kind has its own wider/taller frame in `client/assets/cathedral.txt` (`kindFrames`) so raised claws, scepters, hammer-claws, tidal waves and pearl beams never clip, plus 8 distinct attack frames (wind-up, strike, recovery) and 8 distinct material-appropriate death frames.

| Kind | Frame (`w×h`, anchor) | Motion, attack and fitting death | New PixelFlow ID | Previous ID | Top (new / old) |
| --- | --- | --- | --- | --- | --- |
| Relic Crab (`reliccrab`) | `128×96` `(54, 90)` | Turquoise crab carrying a miniature gold-and-coral cathedral shrine on its shell. Raises both claws and its roof cross (`rises=17`), then lunges (`reach=29`) with a wide claw snap and golden relic arc. On death, its legs splay flat on row 90 and the heavy shrine tips off onto the floor while the cross rolls clear. | `db58a0a5484721e6` | `eeeb1e106f92880e` | `68 / 56` |
| Pearl Widow (`pearlwidow`) | `136×100` `(58, 94)` | Violet-and-pearl spider with a glowing nacre abdomen, pearl tiara and fangs hanging from the corners of its mouth. Rears its abdomen and forelegs high (`rises=10`) and lunges (`reach=25`) with a venomous silk-and-pearl lash. On death, all eight legs curl inward and the pearl sac settles low on row 94. | `63b072c8369ef6f5` | `3152300002a5d9ec` | `67 / 52` |
| Glass Cantor (`glasscantor`) | `124×108` `(52, 102)` | Translucent cyan stained-glass cantor in a rose-window mitre with orbiting glass shards and a chime rod. Raises the chime rod and halo (`rises=10`), then sweeps it forward (`reach=33`) to launch a resonating glass prism beam. On death, cracks spread across the body and it shatters into glowing stained-glass shards on row 102. | `c11accd2c6e89fea` | `c8be0e992c3ee0ef` | `87 / 84` |
| Relic Warden (`relicwarden`) | `136×112` `(56, 106)` | Heavy coral-and-gold crustacean guardian carrying a vaulted reliquary arch on its carapace and a massive crusher hammer-claw. Hoists the crusher claw high overhead (`rises=20`) and slams it down (`reach=27`) with a golden shockwave. On death, the carapace splits open, the legs fold flat on row 106 and the reliquary arch topples sideways. | `73a994d9b3f767d4` | `f3a58210139b7518` | `86 / 84` |
| Coral Regent (`coralregent`) | `136×114` `(54, 108)` | Boss monarch in a sweeping crimson-and-violet mantle with a branching coral crown and pearl-orb scepter. Rears up with crown glowing (`rises=12`) and sweeps the scepter (`reach=45`) to unleash a surging coral-and-pearl tidal wave. On death, the scepter and crown tumble to the floor as the royal mantle pools low on row 108. | `0a8dc9a954c22fe9` | `f7913eb200e2952c` | `86 / 85` |
| Reliquary Pearl (`reliquarypearl`) | `116×96` `(50, 90)` | Boss-mechanic helper: a radiant nacre pearl creature seated in a scalloped gold-rimmed clam reliquary on a coral pedestal. Hinges its top shell wide open (`rises=15`) and fires a concentrated pearl beam (`reach=26`). On death, the top shell cracks and slides off while the pearl dims on its pedestal on row 90. | `4680314b634eddd9` | `4568b6329ef8c316` | `69 / 69` |

## Shared data & inherited kinds

* `client/assets/cathedral.txt` is shared across 146 kinds. `reliquary_slime_redraw.py export` uses `kindframe.merge_kind_entries` to update **only** these six `sprites`, `tops` and `kindFrames` entries while preserving key order and all other 140 kinds.
* Zone 11 (Coral Reliquary) also spawns `tidetemplar` and `tidecantor`, which already use the Flooded Cloister slime art (`scripts/cloister_slime_redraw.py`) and remain untouched.
* `reliquarypearl` is a boss-mechanic helper add (`add: true`) that sleeps until the Coral Regent fight wakes it; `scripts/boss_helper_art.py` delegates its verification to `make_cathedral_sprites.py` -> `reliquary_slime_redraw.verify`.

## Pipeline

```sh
python3 scripts/reliquary_slime_redraw.py preview|extents|build|export|verify
```
Registry `scripts/reliquary_slime_sources.txt`, raw arrays `scripts/reliquary_slime_<kind>_raw.npz`, PixelFlow name prefix `valhallasc_reliquary_slime_style_`. `build` refuses `--replace` and never deletes old sprites; `export` reads the saved editor frames back from PixelFlow and writes `test-results/reliquary-slime/editor-export-proof.json`.

**Grounding (`QUADRUPED-GROUNDING`):** every living and death frame of all six kinds rests its lowest pixel exactly on `kay` (`r.low === kay`). The three multi-legged kinds (`reliccrab`, `pearlwidow`, `relicwarden`) keep `>= 4` distinct ground contact runs and `>= 4` lower leg tracks in all 6 idle frames, and `>= 2` ground runs at every walk step.

## Rollback

`/media/raid/valhallasc-data/reliquary-slime-original-20261104` holds the six pre-change PNGs, `manifest.txt` (SHA256 hashes, old PixelFlow IDs, old `tops`, `oldFrames: {}`) and a full reference copy of `cathedral.txt`.
```sh
python3 scripts/rollback_reliquary_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```
Dry run without `--apply`; preflights every backup file hash before writing and uses `kindframe.restore_kind_entries` so only the six Coral Reliquary entries in `cathedral.txt` are restored (preserving Flooded Cloister and all other kinds).

## Verification

* `python3 scripts/reliquary_slime_review.py review|verify|upload`: builds the 28 FileDrop comparison sheets, per-kind 34-frame sheets and original-rate GIFs, verifies all 204 saved editor frames match the exported atlases, tests the rollback script (including preserving an unrelated manifest edit and rejecting a corrupt backup), confirms live `/home/serveperry/webserver/www/Valhallasc` files are untouched, and uploads the 28 files to FileDrop.
* Bounded real-art browser test:
  ```sh
  PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright \
  NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules \
  VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server \
  bash scripts/test-touch-bounded.sh tests/reliquary-slime-art.cjs
  ```
  Runs 147 checks across all six Reliquary kinds and inherited `tidetemplar`/`tidecantor` in Zone 11, with mutation controls (`MUTATE_KIND` + `MUTATE_PNG`) for floating feet and still-attack frames.
