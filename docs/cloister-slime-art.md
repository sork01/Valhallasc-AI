# Flooded Cloister enemy artwork (candidate)

**Candidate Beta 1.39.10, not deployed.** Built in `/media/raid/valhallasc-data/cloister-slime-work` on `feat/cloister-slime-art` (base `5a80d2d`); the owner approves the pictures before anything is merged. Client-only: no server, map, stats, timings, rewards, zone, DB or music change; no rebuild or restart.

Eight new editable PixelFlow sprites use Greenmeadow's glossy shading, large eyes with highlights and blush. Each has material-appropriate motion and its own death clip (no universal squash).

| Kind | Motion and fitting death | New PixelFlow ID | Previous ID |
| --- | --- | --- | --- |
| Tide Templar | Rigid teal armour on jointed legs, horned helm and fin crest; thrusts a trident. Knees buckle, the suit slumps into a heap and the trident clatters flat. | cd7ff4924a779cb8 | ccd51d6b9acfaba4 |
| Tide Cantor | Hooded robe with swinging bead chains; the chains whip on attack. The robe crumples empty onto the floor, the hood sinks in and the beads scatter. | fde8ff9cf98da578 | f82bcee8d420301a |
| Tide Leech | Segmented crawler inching in a wave (one segment always flat on the floor); rears and bites. Goes limp and flat. | 356b42219ae7365c | 4beb47d44bd7bacd |
| Bellkeeper | Rigid bell on gold feet that sways as it walks; overhead hammer swing with ring lines. Cracks run through the bell, chips fly off, the hammer drops and the bell telescopes into a dented heap with the face plate sunk in. | 0f27f6d32c7515a4 | f535a897b5968901 |
| Mourning Sister | Veiled ghost with a lantern; the hem tatters all reach the floor. The lantern drops and goes dark while she dissolves in a dither, top down. | 725ae0933228f6eb | 71c20782dc2889de |
| Root Abbot | Wooden monk with a leaf hood and tentacle beard; arms slam roots up from the floor. The trunk cracks and splits lengthwise into two logs that fall outward, the hood drops on top and every leaf wilts. | 0f7f02bac6eebc84 | 24c89f1ba16a09cb |
| Choirmother | Robed matriarch with rose hair, crown, pearl hem and four singing ghosts. The singers pop one by one as she swoons and the robe pools. | c82b6ea277a531f7 | deae9d7a051c773a |
| Bound Singer | Small ghost dragging a chain and iron ball; sings notes. Drifts apart from the top down into rising motes; only the iron ball stays. | 1180a4e2e4c0584c | c84037fa098e7762 |

Health-bar `tops` (derived from the tallest idle pose, new/old): 64/84, 59/81, 29/43, 51/68, 61/82, 65/82, 70/82, 42/47.

## Shared data (read before touching it)

* `client/assets/cathedral.txt` is shared by 146 kinds. `cloister_slime_redraw.py export` replaces **only** these eight `sprites`/`tops` entries and asserts that the rest of the manifest (including key order) is unchanged; `boss_add_art_aliases.py` leaves it byte-identical afterwards.
* **The Coral Reliquary (zone 11) and Grand Nave also spawn `tidetemplar` and `tidecantor`**, so they inherit the new art; the Reliquary task only has to redraw its other six kinds (`reliccrab`, `pearlwidow`, `glasscantor`, `relicwarden`, `coralregent`, `reliquarypearl`). `choirsinger` is a boss-helper add (asleep in zone 10, atlas loaded on demand); `boss_helper_art.py all` now skips building/exporting it and its verify delegates to the new pipeline.
* `make_cathedral_sprites.py` still serves every other kind unchanged; for these eight kinds `build`/`--replace`/`export` are refused/skipped and `verify` delegates to `cloister_slime_redraw.py verify`.

## Pipeline

```sh
python3 scripts/cloister_slime_redraw.py preview|build|export|verify
```
Registry `scripts/cloister_slime_sources.txt`, arrays `scripts/cloister_slime_<kind>_raw.npz` (the old `cathedral_<kind>_raw.npz` stay), prefix `valhallasc_cloister_slime_style_`. Build refuses `--replace`; export reads the saved editor frames, so editor edits survive. Same 96x96 frame, anchor (48,90) and five-clip 34-frame contract.

**Grounding (`QUADRUPED-GROUNDING` rule, owner 2026-11-03):** every foot, hem, base or belly rests exactly on row 90 in every living frame (integer radius with centre y = radius; the leech's flat segment is forced by subtracting the wave minimum). No exemptions are needed here: ghosts keep their hem tatters and chain ball on the floor.

## Rollback

`/media/raid/valhallasc-data/cloister-slime-original-20261103` holds the eight original PNGs, `manifest.txt` (SHA256, old IDs, old tops) and a full reference copy of the manifest.
```sh
python3 scripts/rollback_cloister_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```
Dry run without `--apply`; preflights every hash and path. It restores the eight PNGs and **merges only the eight `sprites`/`tops` entries** back into the live `cathedral.txt` (never the whole file, because the Reliquary work edits it too). Tested on a scratch copy whose manifest carries an unrelated Reliquary edit (it survives) and with a corrupt backup (refused, nothing changed). Version/notes rollback is separate.

## Verification

* Bounded real-art browser test: `bash scripts/test-touch-bounded.sh tests/cloister-slime-art.cjs` (env as in `docs/bifrost-slime-art.md`; `CLOISTER_ART_KINDS=a,b` selects kinds; `CLOISTER_MUTATED_ATLAS=<png>` serves a templar atlas for the mutation control). Checks frame/anchor, shared manifest size, new sources, nonempty border-clear frames, timings, eyes, derived tops, **exact ground row in every living frame**, eight distinct deaths, dissolve vs solid vs lowered death, final silhouettes, portraits, authoritative zone 10 presence with production tops, and the same atlas in the Reliquary.
* `python3 scripts/cloister_slime_redraw.py verify` compares the installed atlases to the saved editor frames (272). `python3 scripts/cloister_slime_review.py review|verify|upload`: `verify` expects the ORIGINAL live files (pre-deployment check); afterwards use `cloister_slime_redraw.py verify`. Upload is a separate explicit action.
