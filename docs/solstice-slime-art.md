# Silent Solstice enemy artwork candidate

Prepared 2026-11-11 in `/media/raid/valhallasc-data/silent-solstice-slime-work`, branch `feat/silent-solstice-slime-art`. Private candidate awaiting picture approval under the enemy remake rules in `TODO.md`. Candidate Beta 1.43.1; reconcile the current version and shared Cathedral manifest slices before deployment.

Six native editable PixelFlow sources, 204 frames. Each uses a 176×172 frame and anchor (88,164), eight distinct wind-up/strike/recovery poses and eight distinct material-fitting death poses. The original clip counts and rates remain: idle 6 at 6 fps, walk 8 at 10 fps, attack 8 at 12 fps, hurt 4 at 10 fps, death 8 at 8 fps. The shared Cathedral manifest retains its 96×96 fallback, (48,90) anchor and all 140 unrelated kinds. All 129 unrelated native atlases remain byte-identical. Artwork only; no server, map, combat or reward changes.

| Kind | New source | Previous source | Identity, attack and death |
| --- | --- | --- | --- |
| `solstice_flurry` (Whispering Flurry) | `b1bc37890e38c354` | `8f12653cc1520d6a` | Attached snow-whip winds back and lashes forward. Snow vortex disperses into a low settled drift; its face vanishes. |
| `solstice_owl` (Night Owl) | `8b3db14761a3a178` | `88895b5cdc0e5043` | Feather wings flare and beat into a talon strike. Intact feathered body topples onto its side; golden eyes close. |
| `solstice_guard` (Rime Guard) | `cb8d575f9bdfdc70` | `b5f85657b11da09e` | Braces behind an ice shield and thrusts its spear from raised preparation. Visor darkens and rigid armour, shield and spear topple together. |
| `solstice_watcher` (The Frost Watcher) | `6b9197351ae2e2a7` | `a8a85641f159d912` | Single crowned eye glares as an ice fist rises and punches. Eye extinguishes and hard ice halves separate into low faceted fragments. |
| `solstice_harbinger` (Harbinger of Night) | `68c1c0853685b94c` | `92d77572e732046a` | Winged spectral figure raises and sweeps a crescent staff. Body and feather wings dissipate upward; only its fallen crescent relic remains. |
| `solstice_heart` (Heart of the Longest Night) | `ad4688477cdf218e` | `2036902ed7471f75` | Six rigid crystal petals spread around a widening star aperture. Core light extinguishes; six separate petals break outward and settle. |

The flurry, harbinger and heart hover at least 12 source pixels above the anchor while alive, then settle monotonically through death. The owl, guard and watcher stay grounded. Art scale is independent of frame padding, chosen against the original art and private in-game captures. Distinct faces follow the later enemy-art direction: no generic shared round-eye and blush overlay.

## Pipeline

```sh
python3 scripts/solstice_slime_redraw.py preview
python3 scripts/solstice_slime_redraw.py build
python3 scripts/solstice_slime_redraw.py export
python3 scripts/make_yearwheel_dungeon_sprites.py verify solstice_flurry solstice_owl solstice_guard solstice_watcher solstice_harbinger solstice_heart
python3 tests/solstice-materials.py
python3 scripts/solstice_slime_review.py review
```

Models: `solstice_slime_models.py`; source registry: `solstice_slime_sources.txt`. `build` preserves registered sources; `refresh KIND...` updates only named editor frames. `export` reads saved PixelFlow frames, preserving manual edits, derives health-bar tops, and changes only these six manifest entries. Both maker CLI and module functions delegate these kinds. Amber dispatch is retained when its independent native module is available; otherwise Amber keeps its existing maker. `dungeon_cel.py solstice` delegates before the old deletion path. Both entry points refuse destructive `--replace`. Preserve all other candidates' dispatches when combining branches.

## Rollback

Seven original files, old PixelFlow IDs, byte counts, dimensions, SHA-256 hashes and 129 unrelated atlas hashes are saved at `/media/raid/valhallasc-data/solstice-slime-original-20261111`.

```sh
python3 scripts/rollback_solstice_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run by default. Disposable-copy verification: dry run writes nothing; application restores all seven originals exactly; corrupt backups and unrelated Cathedral manifest changes are refused before writes. Receipt: `test-results/solstice-slime/rollback-proof.json`. Both old and new PixelFlow sources remain saved.

## Validation

- All 204 saved editor frames equal their exported atlas cells.
- Bounded real-art browser batches pass 62 + 62 assertions (`driver-33EBAc`, `driver-GiCumd`): real production loader, source IDs, frame lookup, all animation rates, nonempty unclipped frames, eight substantial attacks with wind-up/strike/recovery, grounding or hover, death landing, health tops, portraits and no page errors.
- 36 exported-art material checks pass; all six corpse-as-idle semantic mutations fail the matching material assertions. Receipts: `materials.log`, `material-mutations.json`.
- Original flurry atlas routed through the production loader is rejected by the browser atlas contract. Receipt: `browser-old-mutation.log`.
- Swedish build and release-note guard pass for candidate Beta 1.43.1. No broad suites, server build/restart or fight testing.

## Review pictures

29 PNG/GIF files, 3,392,179 bytes, uploaded and verified against SHA-256, FileDrop MIME/metadata, byte counts, dimensions and animation frame counts. Receipt: `test-results/solstice-slime/filedrop-receipt.json`.

- [Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-solstice-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-solstice-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-solstice-deaths-before-after.gif)

Each kind also has a full 34-frame sheet, combined animation GIF, attack comparison and death comparison under `valhallasc-solstice-<kind>-*`.

Next enemy group: Nornroot Barrow (`NORNROOT-SLIME-ART`).
