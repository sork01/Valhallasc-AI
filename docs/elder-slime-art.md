# The Elder Hollow enemy art candidate

Private candidate prepared 2026-11-11 in `/media/raid/valhallasc-data/elder-slime-work`, branch `feat/elder-slime-art`. Picture approval is required before deployment under the enemy remake rules in `TODO.md`. Proposed label: Beta 1.43.1; reconcile with the live label again before release.

Six native, editable PixelFlow sources replace the original Elder Hollow artwork. All have 34 frames in 176×172 cells, anchored at (88,164). Original clip rates stay idle 6, walk 10, attack 12, hurt 10 and death 8 fps. Each creature has eight distinct wind-up/strike/recovery frames and eight distinct death frames. Shared `cathedral.txt` retains its 96×96 fallback, (48,90) anchor and the other 140 kinds' entries and atlases. Art only; encounter data and combat timing stay unchanged.

| Kind | Source | Face and attack | Death |
| --- | --- | --- | --- |
| elder_thornling | e0108ef21fc96fdf | Asymmetric acorn socket, hooked brow, hinged bite | Legs buckle; beast falls onto its muzzle, thorns snap |
| elder_moth | 2ef4d15a290513e2 | Black compound eyes, wing fan and feeding-tube thrust | Folds its wings, curls its legs and lands on its side |
| elder_barkguard | 3ca0909651b129ee | Unequal hollow knots, shield brace and club strike | Bark cracks, plates split and stump slumps beside shield |
| elder_gatekeeper | c30845bf264e862c | Single vertical slit, branch antlers, gate-slab ram | Roots buckle, branches snap and rigid gate tips down |
| elder_matron | 8b5f365a2bc7e82d | Seed-shaped sockets, toothed flower mask, pod cast | Collar petals droop; robe, stalk and pod wither |
| elder_heart | 7eff5c6170c86474 | Ribbed furnace knot, roots gather then lash forward | Root buttresses buckle, trunk splits and sap core darkens |

The moth hovers in all living clips and reaches the ground on its final death frame. Every other kind stands on the anchor row in every living/death frame. Thornling has four separate planted paws; both guards have two planted feet. Each face differs, with no shared cartoon-eye/blush overlay. Scale follows the original idle footprints, with room for limbs and props in the larger transparent cells.

## Workflow

```sh
python3 scripts/elder_slime_redraw.py preview
python3 scripts/elder_slime_redraw.py extents
python3 scripts/elder_slime_redraw.py build
python3 scripts/elder_slime_redraw.py export
python3 scripts/make_elder_hollow_sprites.py verify
python3 scripts/elder_slime_review.py review
python3 scripts/elder_slime_review.py verify
```

`elder_slime_models.py` holds the six jointed models; `elder_slime_redraw.py` supplies the palette, frame checks, registry and exporter. `build` preserves existing registered sources and refuses `--replace`. `refresh KIND...` intentionally overwrites only the named source frames. `export` reads saved editor art, preserving hand edits, and derives health-bar tops. A frame-size change requires a new source name via `SOURCE_SUFFIX` and a new registry entry.

The legacy maker retains helper functions imported by other dungeon makers; its CLI delegates to this workflow. `dungeon_cel.py elder_hollow build|preview` also delegates before the old source-deletion path, so that older command cannot destroy this candidate's sources.

## Rollback

Seven originals, their SHA-256 hashes and old PixelFlow IDs are backed up outside the served tree at `/media/raid/valhallasc-data/elder-slime-original-20261111`.

```sh
python3 scripts/rollback_elder_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for a dry run. All sources/destinations and unrelated shared-manifest entries are checked before any write. A real restore on a disposable copy passed; corrupt backups and unrelated-kind changes were both refused without destination writes. After another Cathedral group is deployed, reconcile the shared manifest rather than bypassing that refusal.

## Focused checks

Two bounded real-art browser runs passed 66 + 64 = 130 assertions: all frames nonempty and clear of borders; five clips animate at original rates; eight attacks and deaths per kind; substantial wind-up/strike and recovery; hover, landing, grounding and planted feet; new source IDs; authoritative enemy presence; derived health-bar tops and production portraits. Artifacts: `test-results/driver-PerHb7` and `test-results/driver-Boz33N`.

All 204 saved editor frames equal their exported cells. Original art in the served checkout and all other Cathedral entries/atlases are unchanged. All six full frame sheets and game captures were visually inspected. Baseline captures: `test-results/driver-n4ZvfD`. Swedish build, release-notes guard and Python syntax checks pass. No combat grinding, balance sweeps or full suites.

```sh
ELDER_ART_KINDS=elder_thornling,elder_moth,elder_barkguard \
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright \
NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules \
VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/debug/valhalla-server \
bash scripts/test-touch-bounded.sh tests/elder-slime-art.cjs
```

Use the other three kinds for the second batch. `BASELINE=1` captures original art before export; `SCREENSHOTS=1` captures without assertions and hides transient banners. The old-Thornling-atlas mutation failed at the production frame-contract assertion as required (`test-results/driver-dx4N7p`). The mutation uses `ELDER_ART_KINDS=elder_thornling MUTATE_KIND=elder_thornling MUTATE_PNG=/media/raid/valhallasc-data/elder-slime-original-20261111/client/assets/cathedral_elder_thornling.png`; it must fail. The route glob includes the loader's query string.

## Review pictures

All 29 PNG/GIF files were uploaded to FileDrop and verified against local hashes, original-name metadata, MIME types, byte counts and image dimensions (3,211,835 bytes). Receipt: `test-results/elder-slime/filedrop-receipt.json`. GIFs use a shared palette and each manifest's original frame rates.

[Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-elder-before-after.png) · [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-elder-attacks-before-after.png) · [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-elder-deaths-before-after.gif)

Next group: The Thousandfold Pavilion (`PAVILION-SLIME-ART`).
