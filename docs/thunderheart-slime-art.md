# Zone 35 — The Thunderheart Gate Enemy Sprite Remake

## Overview
- **Branch / Worktree:** `feat/thunderheart-slime-art` (`/media/raid/valhallasc-data/thunderheart-slime-work`)
- **Candidate Version:** `Beta 1.43.1` (held on candidate branch until owner picture approval)
- **Shared Manifest:** `client/assets/cathedral.txt` (`146` total kinds; `6` Thunderheart Gate kinds updated in-place under `sprites`, `tops`, and `kindFrames`; `140` unrelated Cathedral kinds untouched; fallback `96×96` frame and `(48, 90)` anchor preserved)
- **Per-Kind Frame Geometry:** `176×172` with anchor `(88, 164)` across `34` frames (`idle` 6 @ 6 fps, `walk` 8 @ 10 fps, `attack` 8 @ 12 fps, `hurt` 4 @ 10 fps, `die` 8 @ 8 fps)

## Backup & Guarded Rollback
- **External Backup:** `/media/raid/valhallasc-data/thunderheart-slime-original-20261111` (`7` files + `manifest.txt` with SHA-256 digests and `oldSprites`)
- **Rollback Script:** `scripts/rollback_thunderheart_art.py`
  - Dry-run: `python3 scripts/rollback_thunderheart_art.py`
  - Restore: `python3 scripts/rollback_thunderheart_art.py --apply`
  - Refuses to overwrite if any backup SHA-256 fails or if any of the `140` unrelated Cathedral kinds in `client/assets/cathedral.txt` changed since the backup.

## PixelFlow Sources & Silhouettes (`scripts/thunderheart_slime_sources.txt`)

| Kind | Name | Old Sprite ID | New Sprite ID | Grounding | Silhouette, Attack & Material Death |
|---|---|---|---|---|---|
| `thunder_spark` | Forked Spark | `3d07a6b680376603` | `8ad51bbeda9d8429` | Flyer (`idle low=141`, descends onto `164`) | Hovering bronze-and-slate storm-capacitor sphere with twin forked golden lightning horns, jagged lower prongs, a turquoise plasma core, and a fierce frowning visor. Draws back to overcharge its prongs (`f0–f2`), lunges forward discharging a forked lightning bolt (`f3–f5`), and recovers (`f6–f7`). On death, the golden lightning prongs and teal plasma arcs discharge completely while the bronze-and-slate capacitor shell descends monotonically onto row `164`. |
| `thunder_ray` | Stormglass Ray | `ab22374a25fd6af2` | `853b78ef204b839c` | Flyer (`idle low=140`, descends onto `164`) | Gliding cobalt-and-violet stormglass manta ray with broad swept pectoral wings veined with golden lightning ribs, pearl belly plates, and a whip-like barbed lightning tail. Banks its wings back (`f0–f2`), whips its tail forward to lash a storm-arc (`f3–f5`), and levels out (`f6–f7`). On death, the golden lightning tail-barb and wing-vein charge extinguish while the cobalt manta body settles monotonically onto row `164`. |
| `thunder_guard` | Slatebound Guard | `ec80ec788e2871c4` | `4c1fa519a8e66044` | Grounded (`ay=164`) | Heavy slate-armoured storm sentinel with a lightning-plumed crest helm, bronze-trimmed tower shield blazoned with a golden bolt, and a turquoise-cored flanged storm mace. Braces behind his tower shield (`f0–f2`), swings the storm mace in a heavy arc (`f3–f5`), and resets (`f6–f7`). On death, his knees buckle and the slate armour and shield collapse lower onto the ground while the storm-mace core and visor glow shut off. |
| `thunder_conductor` | Storm Conductor | `5634d3d12ef9345b` | `5f56daa3d062c33a` | Grounded (`ay=164`) | Tall storm-priest in a gold-trimmed violet conductor greatcoat with dual shoulder-mounted copper Tesla coils, a brass crown circlet, and a twin-forked tuning-fork lightning staff. Raises his tuning-fork staff (`f0–f2`), thrusts it forward to channel a forked storm arc from his coils (`f3–f5`), and recovers (`f6–f7`). On death, he slumps lower into his coat and the Tesla coil arcs, eye glare, and staff discharge extinguish. |
| `thunder_bastion` | The Thunder Bastion | `806929d046a5274c` | `664577d6948ea045` | Grounded (`ay=164`) | Massive basalt-slate fortress colossus with crenellated battlement shoulders, bronze lightning-rod spires, a turquoise storm-furnace chest grate, and a two-handed pylon hammer. Hefts its pylon hammer overhead (`f0–f2`), slams it down in a ground-shock strike (`f3–f5`), and braces (`f6–f7`). On death, its stone pillar legs buckle and the fortress torso slumps lower while the turquoise storm-furnace core and furnace-slit eyes go dark. |
| `thunder_heart` | Heart of the Stormgate | `1c70caa2e42135f0` | `d741bd17311337b8` | Flyer (`idle low=140`, descends onto `164`) | Boss stormgate dynamo of intersecting steel and bronze containment rings enclosing a violet-and-teal tempest heart orbited by four golden lightning pylons. Spins its containment rings (`f0–f2`), unleashes a concentrated stormgate lance (`f3–f5`), and re-stabilises (`f6–f7`). On death, the orbiting golden lightning pylons and stormgate arcs extinguish while the heavy steel and bronze rings decouple and settle monotonically into a collapsed heap on row `164`. |

## Verification Commands
```bash
python3 scripts/thunderheart_slime_redraw.py verify
python3 tests/thunderheart-materials.py
! MUTATE_KIND=thunder_spark python3 tests/thunderheart-materials.py
python3 scripts/rollback_thunderheart_art.py
THUNDERHEART_ART_KINDS=thunder_spark,thunder_ray,thunder_guard bash scripts/test-touch-bounded.sh tests/thunderheart-slime-art.cjs
THUNDERHEART_ART_KINDS=thunder_conductor,thunder_bastion,thunder_heart bash scripts/test-touch-bounded.sh tests/thunderheart-slime-art.cjs
```
