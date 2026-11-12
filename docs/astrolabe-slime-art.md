# Zone 34 — The Sunken Astrolabe Enemy Sprite Remake

Owner accepted all enemy sprites on 2026-11-12. Integrated for Beta 1.44.0; see
[the combined release](enemy-sprites-release.md). The private-candidate status
below records the original review stage and is superseded by that approval.

## Overview
- **Branch / Worktree:** `feat/astrolabe-slime-art` (`/media/raid/valhallasc-data/astrolabe-slime-work`)
- **Candidate Version:** `Beta 1.43.1` (held on candidate branch until owner picture approval)
- **Shared Manifest:** `client/assets/cathedral.txt` (`146` total kinds; `6` Sunken Astrolabe kinds updated in-place under `sprites`, `tops`, and `kindFrames`; `140` unrelated Cathedral kinds untouched; fallback `96×96` frame and `(48, 90)` anchor preserved)
- **Per-Kind Frame Geometry:** `176×172` with anchor `(88, 164)` across `34` frames (`idle` 6 @ 6 fps, `walk` 8 @ 10 fps, `attack` 8 @ 12 fps, `hurt` 4 @ 10 fps, `die` 8 @ 8 fps)

## Backup & Guarded Rollback
- **External Backup:** `/media/raid/valhallasc-data/astrolabe-slime-original-20261111` (`7` files + `manifest.txt` with SHA-256 digests and `oldSprites`)
- **Rollback Script:** `scripts/rollback_astrolabe_art.py`
  - Dry-run: `python3 scripts/rollback_astrolabe_art.py`
  - Restore: `python3 scripts/rollback_astrolabe_art.py --apply`
  - Refuses to overwrite if any backup SHA-256 fails or if any of the `140` unrelated Cathedral kinds in `client/assets/cathedral.txt` changed since the backup.

## PixelFlow Sources & silhouettes (`scripts/astrolabe_slime_sources.txt`)

| Kind | Name | Old Sprite ID | New Sprite ID | Grounding | Silhouette, Attack & Material Death |
|---|---|---|---|---|---|
| `astro_gearling` | Brass Gearling | `6bc064ce1fc65aa0` | `fedc88bf48d85116` | Grounded (`ay=164`) | Compact brass cog-wheel automaton with eight outer teeth, rear counter-gear, turquoise aether-core, and angry brass visor. Winds its crank arm back (`f0–f2`), punches its glowing piston rod forward (`f3–f5`), and retracts (`f6–f7`). On death, piston legs buckle, the turquoise core extinguishes to dark slate, and a loose cog rolls beside the hull. |
| `astro_starling` | Fallen Starling | `730e24b4b06b8f28` | `b205896238d7dab4` | Flyer (`idle low=139`, descends onto `164`) | Hovering five-pointed golden star construct with a crimson brow shard, snarling fangs, and trailing cobalt-and-teal comet plume. Draws back into a tight flare (`f0–f2`), lances a starlight spike forward (`f3–f5`), and recovers (`f6–f7`). On death, the comet trail dissipates completely while the rigid golden star hull descends monotonically onto row `164`. |
| `astro_sentinel` | Orrery Sentinel | `3bf5edda588d7c51` | `09e9dbd031298814` | Grounded (`ay=164`) | Domed brass-and-steel clockwork guardian with an orbiting turquoise bead, slate-and-gold buckler, and astrolabe staff. Raises its staff high (`f0–f2`), sweeps it down to project an aetherial arc (`f3–f5`), and returns to guard (`f6–f7`). On death, brass knees buckle, the torso topples forward onto its staff, and the chest core, visor, and orbiting bead shut off. |
| `astro_warden` | Meridian Warden | `f6838d1fc3140dc1` | `69c4be21bec843b9` | Grounded (`ay=164`) | Cobalt-and-gold meridian knight with a spire helm, gold-crossed Meridian Shield, and violet celestial blade. Braces behind its shield (`f0–f2`), cleaves forward in a broad arc (`f3–f5`), and resets (`f6–f7`). On death, the knight's knees give way and the cobalt plate armour and shield collapse lower onto the ground while retaining their solid mass. |
| `astro_navigator` | The Lost Navigator | `ac433307c64d3632` | `f95bd925aad9ed50` | Grounded (`ay=164`) | Ancient chart-keeper in a navy greatcoat and tricorn hat with a braided pearl beard, cyan monocle, brass sextant, and star-tipped spyglass staff. Sight-locks through his sextant (`f0–f2`), thrusts the spyglass staff to fire a starlight bolt (`f3–f5`), and recovers (`f6–f7`). On death, he slumps into his greatcoat, his tricorn tips forward, and his monocle and spyglass glints go dark. |
| `astro_axis` | Axis of the Buried Sky | `1d8c61c63038ec66` | `26468296452d64a5` | Flyer (`idle low=141`, descends onto `164`) | Boss armillary construct of intersecting brass and steel rings enclosing a violet-and-azure celestial core with orbiting star nodes. Spins its outer rings (`f0–f2`), projects a golden meridian lance (`f3–f5`), and re-aligns (`f6–f7`). On death, the celestial core and star nodes extinguish while the heavy brass and steel rings decouple and settle monotonically into a collapsed heap on row `164`. |

## Verification Commands
```bash
python3 scripts/astrolabe_slime_redraw.py verify
python3 tests/astrolabe-materials.py
! MUTATE_KIND=astro_gearling python3 tests/astrolabe-materials.py
python3 scripts/rollback_astrolabe_art.py
ASTROLABE_ART_KINDS=astro_gearling,astro_starling,astro_sentinel bash scripts/test-touch-bounded.sh tests/astrolabe-slime-art.cjs
ASTROLABE_ART_KINDS=astro_warden,astro_navigator,astro_axis bash scripts/test-touch-bounded.sh tests/astrolabe-slime-art.cjs
```
