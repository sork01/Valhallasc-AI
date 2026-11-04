# Grand Nave enemy artwork (Beta 1.39.19)

**Deployed 2026-11-04 as Beta 1.39.19** (owner approved FileDrop pictures: "deploy and /finish"; source `61864f5` from `/media/raid/valhallasc-data/nave-slime-work` on `feat/nave-slime-art`, base `e515f2f`). Client-only: no server, map, stats, timings, rewards, zone, DB or music change; no rebuild or restart.

Five new editable PixelFlow sprites for Zone 12 (The Drowned Cathedral — Grand Nave) use the shared slime style: glossy multi-stop shading, large eyes with `#fffbea` eye whites and highlights, warm blush and chunky readable silhouettes. Each kind has its own wider/taller frame in `client/assets/cathedral.txt` (`kindFrames`) so raised censers, ship anchors, seraph wings, judicial gavels and papal crosiers never clip, plus 8 distinct attack frames (wind-up, strike, recovery) and 8 distinct material-appropriate death frames.

| Kind | Frame (`w×h`, anchor) | Motion, attack and fitting death | New PixelFlow ID | Previous ID | Top (new / old) |
| --- | --- | --- | --- | --- | --- |
| Abyssal Zealot (`abysszealot`) | `128×104` `(52, 98)` | Hunched deep-indigo robed zealot in a tall pointed cowl swinging a golden chain censer burning with violet-and-teal abyssal flame. Hoists the censer high overhead (`rises=14`), then whips it far forward (`reach=42`) in a blazing arc of abyssal fire. On death, the censer clatters flat as its flame gutters out and the empty robe crumples on row 98 while violet motes rise. | `7fda970e0aa760ae` | `c2cab87fa5cc4344` | `76 / 84` |
| Chain Marshal (`chainmarshal`) | `136×112` `(54, 106)` | Heavy dark-steel and gold plated juggernaut bound in crossed chains with a chest padlock, spiked pauldrons, horned great-helm and a massive iron ship-anchor on a chain. Heaves the anchor high overhead (`rises=17`) and slams it far forward (`reach=36`) with shockwave sparks. On death, his armoured legs buckle, the anchor and chains crash flat, and the steel plate collapses on row 106. | `be78cd79be2e14fe` | `462e65b0ea4e3b1a` | `74 / 79` |
| Star Seraph (`starseraph`) | `136×114` `(56, 108)` | Fallen celestial seraph in a star-spangled lavender gown with four feathered wings, broken golden star-halo, crystal tear and radiant starlight orb. Spreads all four feathered wings high overhead (`rises=17`) and sweeps forward (`reach=34`) to loose a blazing shooting-star volley. On death, her broken halo shatters to the floor, her four wings fold and droop, and she sinks into a pool of starlit cloth on row 108. | `82a0f6b1f2b069b8` | `fefc71ed55fcb00a` | `76 / 85` |
| Tide Judicator (`tidejudicator`) | `136×112` `(56, 106)` | Monumental parchment-and-slate robed judge with a brow blindfold band, golden judicial crown, tilting Balance Scales of the Tide and a massive iron-and-gold gavel. Raises the gavel high overhead as the scales flare (`rises=13`), then brings it crashing down (`reach=38`) with a golden verdict shockwave. On death, the balance scales spill onto the floor, the gavel drops flat, the crown slips and the judicial robes collapse on row 106. | `bd9501ef46e5dd9d` | `4d95fb5d35541056` | `78 / 82` |
| Hierophant Vael (`hierophant`) | `136×116` `(54, 110)` | Final boss of the Drowned Cathedral in royal-violet and gold vestments with a glowing cyan Tide-Heart gem on his chest, flowing silver beard, tall papal mitre and golden Tide-Orb crosier. Hoists the crosier high above his mitre (`rises=13`) and sweeps it far forward (`reach=47`) unleashing a surging torrent of tide orbs. On death, the Tide-Heart cracks and dims, the crosier and mitre tumble to the floor, and his vestments crumple on row 110. | `5db94628883ff5dc` | `e84af5fba462af60` | `84 / 80` |

## Shared data & inherited kinds

* `client/assets/cathedral.txt` is shared across 146 kinds. `nave_slime_redraw.py export` uses `kindframe.merge_kind_entries` to update **only** these five `sprites`, `tops` and `kindFrames` entries while preserving key order and all other 141 kinds (including Flooded Cloister and Coral Reliquary).
* Zone 12 (Grand Nave) also spawns `tidetemplar` and `tidecantor`, which already use the Flooded Cloister slime art (`scripts/cloister_slime_redraw.py`) and remain untouched.

## Pipeline

```sh
python3 scripts/nave_slime_redraw.py preview|extents|build|refresh|export|verify
```
Registry `scripts/nave_slime_sources.txt`, raw arrays `scripts/nave_slime_<kind>_raw.npz`, PixelFlow name prefix `valhallasc_nave_slime_style_`. `build` refuses `--replace` and never deletes old sprites; `export` reads the saved editor frames back from PixelFlow and writes `test-results/nave-slime/editor-export-proof.json`.

**Grounding (`QUADRUPED-GROUNDING`):** every living and death frame of all five kinds rests its lowest pixel exactly on `kay` (`r.low === kay`). Both armoured boots of `chainmarshal` touch the ground row in all 6 idle frames (`groundRuns === 2`) and at least one planted boot touches in every walk step.

## Rollback

`/media/raid/valhallasc-data/nave-slime-original-20261104` holds the five pre-change PNGs, `manifest.txt` (SHA256 hashes, old PixelFlow IDs, old `tops`, `oldFrames: {}`) and a full reference copy of `cathedral.txt`.
```sh
python3 scripts/rollback_nave_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```
Dry run without `--apply`; preflights every backup file hash before writing and uses `kindframe.restore_kind_entries` so only the five Grand Nave entries in `cathedral.txt` are restored (preserving Flooded Cloister, Coral Reliquary and all other kinds).

## Verification

* `python3 scripts/nave_slime_review.py review|verify|upload`: builds the 24 FileDrop comparison sheets, per-kind 34-frame sheets and original-rate GIFs, verifies all 170 saved editor frames match the exported atlases, tests the rollback script (including preserving an unrelated manifest edit and rejecting a corrupt backup), confirms live `/home/serveperry/webserver/www/Valhallasc` files are untouched, and uploads the 24 files to FileDrop.
* Bounded real-art browser test:
  ```sh
  PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright \
  NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules \
  VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server \
  bash scripts/test-touch-bounded.sh tests/nave-slime-art.cjs
  ```
  Runs 118 checks across all five Grand Nave kinds and inherited `tidetemplar`/`tidecantor` in Zone 12, with mutation controls (`MUTATE_KIND` + `MUTATE_PNG`) for floating feet and still-attack frames.
