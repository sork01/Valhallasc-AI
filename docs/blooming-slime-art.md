# Zone 36 — The Blooming Labyrinth Enemy Sprite Remake

## Overview
- **Branch / Worktree:** `feat/blooming-slime-art` (`/media/raid/valhallasc-data/blooming-slime-work`)
- **Candidate Version:** `Beta 1.43.1` (held on candidate branch until owner picture approval)
- **Shared Manifest:** `client/assets/cathedral.txt` (`146` total kinds; `6` Blooming Labyrinth kinds updated in-place under `sprites`, `tops`, and `kindFrames`; `140` unrelated Cathedral kinds untouched; fallback `96×96` frame and `(48, 90)` anchor preserved)
- **Per-Kind Frame Geometry:** `176×172` with anchor `(88, 164)` across `34` frames (`idle` 6 @ 6 fps, `walk` 8 @ 10 fps, `attack` 8 @ 12 fps, `hurt` 4 @ 10 fps, `die` 8 @ 8 fps)

## Backup & Guarded Rollback
- **External Backup:** `/media/raid/valhallasc-data/blooming-slime-original-20261111` (`7` files + `manifest.txt` with SHA-256 digests and `oldSprites`)
- **Rollback Script:** `scripts/rollback_blooming_art.py`
  - Dry-run: `python3 scripts/rollback_blooming_art.py`
  - Restore: `python3 scripts/rollback_blooming_art.py --apply`
  - Refuses to overwrite if any backup SHA-256 fails or if any of the `140` unrelated Cathedral kinds in `client/assets/cathedral.txt` changed since the backup.

## PixelFlow Sources & Silhouettes (`scripts/blooming_slime_sources.txt`)

| Kind | Name | Old Sprite ID | New Sprite ID | Grounding | Silhouette, Attack & Material Death |
|---|---|---|---|---|---|
| `bloom_spore` | Bloom Spore | `0858c35929a3f9c9` | `f8251911148efb06` | Flyer (`idle low=143`, descends onto `164`) | Hovering violet fungal spore-pod with an unfurling rose-magenta lotus petal crown, dangling jade root-tendrils, a golden stamen-crown, and a scowling bio-luminescent visor. Compresses its petals (`f0–f2`), bursts forward to eject a golden-and-magenta pollen cloud (`f3–f5`), and settles (`f6–f7`). On death, the golden pollen and stamen glow disperse while the split violet bulb and wilted petals descend monotonically onto row `164`. |
| `bloom_moth` | Glasspetal Moth | `1405e8be310d895b` | `dd9a6428b08a2e30` | Flyer (`idle low=139`, descends onto `164`) | Gliding stained-glass floral moth with four faceted rose-magenta and teal prism wings framed in dark violet lead-lines, feathered golden antennae, asegmented violet thorax/abdomen, and a fierce compound-eye glare. Sweeps its glass wings high (`f0–f2`), banks forward to project a prismatic glasspetal beam (`f3–f5`), and levels out (`f6–f7`). On death, the teal prism refraction and golden antennae glow fade while the moth folds its stained-glass wings inward and settles monotonically onto row `164`. |
| `bloom_guard` | Hedge Warden | `b6ae1174c904cda7` | `43223246fcae8dce` | Grounded (`ay=164`) | Heavy briar-wood and jade-leaf topiary knight with a rose-crested bark helm, a thorny hedge tower shield blazoned with a golden bloom emblem, and a rose-tipped briar halberd. Braces behind his hedge shield (`f0–f2`), thrusts and sweeps the briar halberd forward (`f3–f5`), and resets (`f6–f7`). On death, his timber knees buckle and the bark armour and hedge shield collapse lower onto row `164` while the golden bloom emblem and eye glow go dark. |
| `bloom_thornkeeper` | The Thornkeeper | `8b23a6b3b459e1f0` | `560aed46e1fae71c` | Grounded (`ay=164`) | Tall briar-druid sovereign in a sweeping cloak of woven jade vines and violet-black thorns, crowned with a stag-like ironwood antler-wreath of blooming roses and wielding a coiled briar-lash staff. Coils his briar-lash staff back (`f0–f2`), whips a barbed rose-vine lash forward (`f3–f5`), and recoils (`f6–f7`). On death, his root-legs buckle and the thorn-cloak slumps lower onto row `164` while the golden lantern-bud and eye glare extinguish. |
| `bloom_mirror` | Mirror-Petalled | `9d1bf0a5e271d56a` | `33c196f7d4d11909` | Flyer (`idle low=146`, descends onto `164`) | Hovering kaleidoscope sentinel of six silvered teal-glass mirror petals orbiting a faceted rose-crystal prism mask and violet chalice-core. Spins and aligns its mirror petals (`f0–f2`), focuses a blinding prismatic mirror-ray forward (`f3–f5`), and re-spaces its ring (`f6–f7`). On death, the golden prism spark extinguishes while the six mirror petals decouple and settle monotonically with the violet core into a low ring on row `164`. |
| `bloom_heart` | Heart of the Labyrinth | `8cfa0101b1668b1b` | `829b727ce0ad7cf6` | Flyer (`idle low=145`, descends onto `164`) | Boss world-flower sanctuary core: a massive floating rose-and-violet crystal lotus heart cradled in an ancient ironwood root-throne, orbited by four stained-glass prism-petals (`Prism Bounce` reflectors) and a golden solar corona. Opens its lotus jaws (`f0–f2`), unleashes a concentrated prismatic labyrinth beam (`f3–f5`), and closes back (`f6–f7`). On death, the golden corona extinguishes while the ironwood root-throne, lotus heart, and four prism-petals collapse monotonically into a dormant mound on row `164`. |

## Verification Commands
```bash
python3 scripts/blooming_slime_redraw.py verify
python3 tests/blooming-materials.py
! MUTATE_KIND=bloom_spore python3 tests/blooming-materials.py
python3 scripts/rollback_blooming_art.py
BLOOMING_ART_KINDS=bloom_spore,bloom_moth,bloom_guard bash scripts/test-touch-bounded.sh tests/blooming-slime-art.cjs
BLOOMING_ART_KINDS=bloom_thornkeeper,bloom_mirror,bloom_heart bash scripts/test-touch-bounded.sh tests/blooming-slime-art.cjs
```
