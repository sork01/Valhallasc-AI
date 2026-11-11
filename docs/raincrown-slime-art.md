# Temple of the Rain Crown enemy art candidate

Prepared 2026-11-11 in `/media/raid/valhallasc-data/raincrown-slime-work`, branch `feat/raincrown-slime-art`. Private, awaiting picture approval under the enemy remake rules in `TODO.md`. Proposed Beta 1.43.1; reconcile the live version before eventual deployment.

Six native, editable PixelFlow sources, 204 frames total. Each has a 176×172 frame with anchor (88,164), eight distinct wind-up/strike/recovery frames and eight distinct death frames. Original timing is preserved: idle 6, walk 10, attack 12, hurt 10 and death 8 fps. The shared Cathedral manifest keeps its 96×96 fallback, (48,90) anchor and all other 140 kinds. Art only; encounters, stats, maps and server code are unchanged.

| Kind | PixelFlow source | Identity and attack | Death |
| --- | --- | --- | --- |
| rain_crown_droplet | 71a3b14a49f3c83a | Pointed blue water spirit, small gold crown, sharp eyes and fanged grin; draws back and splashes forward | Water spreads into a shallow splash, rigid crown lands against the water |
| rain_crown_oracle | 4d2820ab57795dd3 | Jade skin and robes, teal cowl, gold third-eye circlet; raises and extends a hand-held casting orb | Knees and robe buckle into a cloth heap |
| rain_crown_guard | 6bdb872224b5bda4 | Blue armour, red visor, turquoise umbrella shield and spear; braces, draws back and thrusts | Joints buckle and armour tips, shield and spearhead retain their shape |
| rain_crown_gatekeeper | 43bbd58541a82100 | Angular stone face, moss, iron wheel and sluice shield; raises the shield and slams forward | Stone cracks, knees buckle, wheel stops and water jets shut off |
| rain_crown_sibyl | 69122624349fb35e | Purple hair and robe, tear mask, pale cloud and yellow lightning; raises hand and casts forward | Cloud disperses, rain stops, body falls and cloth settles |
| rain_crown_sovereign | dfc75558c8a13f18 | Blue water body, three unequal eyes, fangs, five streams and tall gold crown; rises and lunges | Streams and body drain into a broad pool, intact crown tips against it |

Droplet, Sibyl and Sovereign hover at least 12 pixels above the anchor during all living clips and descend smoothly to the ground on death. The other three stay grounded. Guard and Gatekeeper have two separate planted feet. Art scale was selected against original idle bounds and a private real-client capture, rather than enlarged with the new frame. Shapes use clean shaded bands without dither; faces are separate designs without shared blush overlays.

## Pipeline

```sh
python3 scripts/raincrown_slime_redraw.py preview
python3 scripts/raincrown_slime_redraw.py extents
python3 scripts/raincrown_slime_redraw.py build
python3 scripts/raincrown_slime_redraw.py export
python3 scripts/make_rain_crown_sprites.py verify
python3 scripts/raincrown_slime_review.py review
python3 scripts/raincrown_slime_review.py verify
python3 tests/raincrown-materials.py
```

`raincrown_slime_models.py` contains the articulated models. Registry: `scripts/raincrown_slime_sources.txt`. `build` preserves saved sources and refuses `--replace`; `refresh KIND...` deliberately overwrites only the named editor frames. `export` reads the saved editor, preserves hand edits and derives health-bar tops from idle bounds. New frame dimensions require a new source. The legacy maker retains its imported helpers and delegates its CLI to this pipeline. `dungeon_cel.py rain_crown build|preview` delegates before the legacy deletion path.

## Backup and rollback

Seven originals, SHA-256 hashes, old PixelFlow IDs and any old per-kind dimensions are saved outside the served tree at `/media/raid/valhallasc-data/raincrown-slime-original-20261111`.

```sh
python3 scripts/rollback_raincrown_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run by default. All backup sources and destinations are validated before writes. Restoring seven files on a disposable target passed; a corrupt backup and an unrelated Cathedral-manifest edit were both refused before any writes. The rollback never deletes either old or new PixelFlow sources.

At integration, merge only these six entries into `cathedral.txt`; Eye, Elder and Pavilion candidates also edit the shared manifest. Combine the safe `dungeon_cel.py` dispatch cases rather than replacing that file with a stale copy. Reconcile versions and release notes. Rollback deliberately refuses unrelated manifest changes, which must be reconciled rather than bypassed.

## Focused checks

Bounded real-client batches pass 64 and 83 assertions: `test-results/driver-qH2mTr` and `driver-4XIiln`. The second batch checks the four changed creatures after refining their landing motion and Gatekeeper death; unchanged Oracle and Guard keep their first-batch evidence. Checks cover 34 frames, clip rates, distinct attacks/deaths, substantial wind-up/strike silhouettes, recovery, grounding, hover/landing, source IDs, authoritative presence, health-bar tops and production portraits. Every model also uses animation phase in its walking clip.

18 exported-art material assertions pass (`tests/raincrown-materials.py`): spreading/draining water, retained rigid crowns and props, connected crown support, smooth descent, retained stone and cloth, the stone corpse itself touching the anchor, and disappearing rain/cloud. An in-memory idle-as-death mutation fails at the water assertion. Routing the original Droplet atlas into the production loader fails the frame-contract assertion as intended.

All 204 saved editor frames match their exported cells. All six full frame sheets and in-game captures were inspected. Original captures: `test-results/driver-Jij4sE`; final captures with transient banners hidden: `test-results/driver-VEOujE`. Swedish generation, release notes and syntax checks pass. Other 140 Cathedral kinds and the original live assets remain unchanged. No full suites, combat grinding, balance sweeps, server rebuild or restart.

```sh
RAINCROWN_ART_KINDS=rain_crown_droplet,rain_crown_oracle,rain_crown_guard \
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright \
NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules \
VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/debug/valhalla-server \
bash scripts/test-touch-bounded.sh tests/raincrown-slime-art.cjs
```

Select the other three for another batch. `BASELINE=1` or `SCREENSHOTS=1` captures without art assertions. Old-art mutation: select only `rain_crown_droplet` and set `MUTATE_KIND=rain_crown_droplet MUTATE_PNG=/media/raid/valhallasc-data/raincrown-slime-original-20261111/client/assets/cathedral_rain_crown_droplet.png`; it must fail. Mutation routes include the loader query string.

## Review pictures

All 29 PNG/GIF reviews uploaded to FileDrop and verified against local SHA-256, original-name metadata, MIME, byte counts and dimensions: 2,632,990 bytes. Receipt: `test-results/raincrown-slime/filedrop-receipt.json`. GIFs use one shared palette and each version's real clip rate. Complete frame sheets, all clips, attacks and before/after deaths are included.

[Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-raincrown-before-after.png) · [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-raincrown-attacks-before-after.png) · [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-raincrown-deaths-before-after.gif)

Next enemy group: The Seed Vault (`SEEDVAULT-SLIME-ART`).
