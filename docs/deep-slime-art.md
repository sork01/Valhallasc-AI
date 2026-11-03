# Rán's Deep enemy artwork (private candidate)

**Candidate Beta 1.39.9**, 2026-11-03, built in `/media/raid/valhallasc-data/deep-slime-work` on `feat/deep-slime-art` (base `d8cde11`).
Not deployed: the owner must see the FileDrop pictures and approve first. All four DEEP-SLIME deliverables are complete.

Eight original editable PixelFlow sprites use Greenmeadow's glossy shading, large eyes with highlights and blush. Each has material-appropriate
motion and its own death clip (no generic squash). Only this zone uses these atlases (`Field.deepSprites`); nothing is borrowed.

| Kind | Motion and fitting death | New PixelFlow ID | Previous ID |
| --- | --- | --- | --- |
| Drowned Draugr | Rotten-rag tunic, barnacles, weed hair and a rusted axe; the dead fall apart: head rolls off, barnacles and ribs scatter, axe drops flat. | 178ced3fea57e381 | dcb96423502b2fdb |
| Lantern Angler | Swims on the spot; the lure flares before the bead is spat; the lure goes dark, it rolls belly-up, sinks and bubbles rise. | 0d3232de9bd69eba | 4b232709b55021ab |
| Gnashing Moray | Rippling eel along the sea floor; strikes with a rearing lunge; a last convulsion, then it goes limp, the coil settles and the tongue lolls. | 4c9139ad14331b6b | 4d4baf4ecd280218 |
| Siren | Hovering singer; arms flung wide and notes on attack; dissolves in a dither into foam and bubbles, leaving the pearl. | 4f81dc6d7b02754c | 883c943f806553c2 |
| Shellback | Rigid shell on four stout planted legs; rears and slams; head and legs draw in, shell settles then tips onto its side showing the plastron, the plank falls flat. | 99412db02a27b9f1 | 69b4c8ea8a971fb8 |
| The Kraken | Violet mantle on six stepping tentacles; two slam in the attack; the mantle deflates and the tentacles go slack and splay. | 375e2e2f8ffb2414 | 1c2ba4fe984d117e |
| Hvitserk | Navy coat, gold epaulettes, white beard, tricorn and cutlass; coat collapses, hat tumbles off and the cape pools. | 7a7ce19f2c2df638 | 2f1a0a41ed5b1e9c |
| Ghostmaw | Pale, crystal-spined moray; flesh dissolves to a skeleton and rising wisps (the boss version of the moray's death). | 1fc321846ddef17d | 167b214f07044242 |

**Grounding rule (owner report `QUADRUPED-GROUNDING`, 2026-11-03):** every foot or belly that rests on the floor sits exactly on the anchor row 90
(Painter `y = ry`, integer radius), so nothing floats. Shellback's near and far feet, the draugr/Hvitserk boots and the eel bellies touch row 90 in every
living frame; hovering kinds (angler, siren) keep their old float height; the Kraken's tentacle tips rest on rows 88-89. The earlier remade zones were
**not** re-grounded here.

## Pipeline

```sh
python3 scripts/make_deep_sprites.py preview|build|export|verify
```
The established CLI delegates to `deep_slime_redraw.py`; both refuse destructive `--replace`. Registry `scripts/deep_slime_sources.txt`, arrays
`scripts/deep_slime_<kind>_raw.npz`, prefix `valhallasc_deep_slime_style_b_`. A first-pass set (prefix `..._style_`, IDs in `deep_slime_draft_sources.txt`)
was superseded after resizing the Kraken, Shellback and eels; it stays in PixelFlow, unused. Export reads saved editor frames and derives health tops
{"draugr": 70, "angler": 72, "moray": 36, "siren": 82, "shellback": 61, "kraken": 68, "hvitserk": 69, "ghostmaw": 42} (previously 80/70/45/81/50/64/80/45). Same 96x96 frame, anchor (48,90), five-clip 34-frame contract; atlases `deep_<kind>.png` and
`deep.txt` replace the old art. No server, map, stats, timings, rewards, zone, DB or music change; no rebuild or restart.

## Rollback

`/media/raid/valhallasc-data/deep-slime-original-20261103` holds the nine original files (`deep.txt` + eight PNGs), `manifest.txt` with SHA256 and old IDs.
```sh
python3 /media/raid/valhallasc-data/deep-slime-work/scripts/rollback_deep_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```
Dry run without `--apply`; preflights every hash and path. Restoration on disposable copies and corrupt-backup refusal pass. Version/notes rollback is separate.

## Verification

* **125 bounded real-art browser checks pass** (`test-results/driver-ReGEDB`, `bash scripts/test-touch-bounded.sh tests/deep-slime-art.cjs`, env as in `docs/bifrost-slime-art.md`; `DEEP_ART_KINDS=a,b` selects kinds): 272 nonempty border-clear frames, timings, eyes, derived tops, **grounding floors for every living frame**, eight distinct deaths per kind, dissolve vs solid death, distinct final silhouettes, portraits, authoritative zone 8 presence, no errors.
* **Mutation:** a shellback atlas with its lowest rows removed is rejected by the grounding assertion (`DEEP_MUTATED_ATLAS`, `test-results/deep-slime/mutation.log`). A whole-atlas shift is caught earlier by the health-top check.
* 272 saved-editor/export frames match exactly (`editor-export-proof.json`); `validation.json` covers rollback, corrupt-backup refusal, `--replace` refusal and unchanged live art.
* Review `python3 scripts/deep_slime_review.py review|verify|upload`: `verify` expects the ORIGINAL live files (pre-deployment); afterwards use `make_deep_sprites.py verify`.

## FileDrop (27 files, hash/size/MIME verified, receipt `test-results/deep-slime/filedrop-receipt.json`)

[Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-deep-before-after.png), `-before.png`, `-after.png`, and per kind
`valhallasc-deep-<kind>-frames.png`, `-animations.gif`, `-death-before-after.gif`.
