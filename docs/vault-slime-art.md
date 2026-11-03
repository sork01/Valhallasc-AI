# Undervault slime-style artwork release

Released as **Beta 1.39.5** on 2026-11-03 after the owner approved the
pictures and requested deployment and the finish skill. Source **95ab27d**
from `feat/vault-slime-art`, prepared in
`/media/raid/valhallasc-data/vault-slime-work`, is merged into main and live.
All 10 public release hashes and both health endpoints pass; 19 existing
Crags/Rimeveil/Gloamfen/Greenmeadow art hashes are preserved. Server PID and
executable stayed unchanged: no build, restart or database action.
Receipt: `test-results/vault-release-20261103T184312Z.json`.

Seven new native PixelFlow sources use Greenmeadow's glossy shading, large
white eyes, highlights, blush and chunky proportions. Skeletons keep bone
anatomy; armour and stone stay rigid. Kind IDs, names, art paths, frame sizes,
anchors and animation rates are unchanged.

- **Vault Thrall:** jointed bony steps, cracked shield and rusty sword. Death
  loosens and separates the ribs, drops the shield/sword and rolls the skull
  sideways into a scattered bone heap.
- **Bone Archer:** brown hood, quiver, recurve bow and drawn-string release.
  Death folds the knees, drops and rotates the rigid bow, scatters arrows and
  leaves the hooded skull on the other side of the bone pile.
- **Hollow Acolyte:** violet hood/robe and a glowing staff. Cloth sways during
  walking; death drops the skull into the settling robe, tips the staff flat
  and extinguishes the orb while the final magic motes rise away.
- **Hrolf Bonegate:** horned helm, heavy plate, red shield and axe. Death buckles
  the legs, separates/cracks rigid armour, drops the axe and tips the helmet
  and skull across the fallen breastplate.
- **Valka, the Hollow Choir:** veiled floating lich, teal gown, silver diadem
  and singing notes. Death dissolves the rising face/veil into separated
  spectral ribbons; the cloth and sleeves settle below it. The final pose
  retains cloth, without a solid skull or a squashed spirit body.
- **Ironwake:** solid blue-grey construct components, oversized fists and a
  bright rune core. Death grows fractures, drops fragments, slumps separated
  components into a stone heap and extinguishes the core.
- **Haldor, the Hollow King:** green armour, purple cape, greatsword and golden
  crown. The crown tumbles first; delayed ribs and limbs fall apart, the sword
  drops, the cape drapes and the green magic expires.

Every death has eight different poses and a distinct final silhouette. All
238 frames and the production portrait/gameplay screenshots were inspected.
The existing eight-frame death timing remains intact; bosses use staged
failures and extra falling parts within that timing.

## Editable sources

| Kind | New PixelFlow ID | Preserved previous ID |
| --- | --- | --- |
| thrall | 7dee3916397e745c | e635e2c7bae16ec1 |
| archer | 9303b719d8401202 | 39c33957abc7b8a7 |
| acolyte | 7a9851aa0becadae | a6c0354646530d2c |
| gatewarden | fc18588356e1c7e3 | 78ed7f80073fb351 |
| choir | 6d002bf680604a12 | 71caf73e7d1b1b51 |
| colossus | 787787128faf3195 | 105f0d600bec805b |
| hollowking | b582240b1e315395 | 2811c940c413fed9 |

Registry `scripts/vault_slime_sources.txt`; indexed source arrays
`scripts/vault_slime_<kind>_raw.npz`; prefix `valhallasc_vault_slime_style_`.
Previous PixelFlow sources and historical raw arrays remain intact.

```sh
python3 scripts/make_vault_sprites.py preview
python3 scripts/make_vault_sprites.py build
python3 scripts/make_vault_sprites.py export
python3 scripts/make_vault_sprites.py verify
```

The established CLI delegates to `vault_slime_redraw.py`. Both CLIs refuse
`--replace`; build preserves registered sources. Export reads saved editor
frames, preserving edits, and derives health-bar tops (73/79/80/86/87/86/84 in
kind order). Verify compares saved editor pixels directly with atlas pixels.
The existing production loader consumes those tops without renderer changes.

Same 96×96 frame, anchor (48,90), 768×480 atlas and 34 frames per kind:
6 idle at 6fps, 8 walk at 10fps, 8 attack at 12fps, 4 hurt at 10fps,
8 die at 8fps. Seven existing PNG paths plus `vault.txt` replace the old live art;
no duplicate old atlases remain under assets.
No map, stats, combat timings, rewards, zone IDs, server, database or music changes;
no build, restart, migration, grinding or fight/balance/timing sweeps.

## Rollback

External backup `/media/raid/valhallasc-data/vault-slime-original-20261103`
contains the seven previous PNGs and `vault.txt`, with all eight hashes and
previous PixelFlow IDs in `manifest.txt`. It is outside live and candidate trees.

```sh
python3 /media/raid/valhallasc-data/vault-slime-work/scripts/rollback_vault_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run without `--apply`. It preflights the exact file set, every source hash
and target path before writes, then replaces files atomically and verifies
restored hashes. Actual restoration on disposable candidate copies passes;
a corrupt backup is refused without target changes. Version labels and notes
are separate from artwork rollback.

## Verification and owner pictures

**95 bounded real-art browser checks pass**, using the existing production
binary with a private server/database: all 238 frames nonempty/unclipped,
original counts/rates, distinct motion in all five clips, large readable eyes,
source IDs, target portraits, derived and consumed health-bar tops, eight
unique death poses per kind, retained solid material, Valka's spirit dispersal,
seven distinct final silhouettes, authoritative Undervault presence and no
browser errors. Artifact directory: `test-results/driver-jEp74W`.

All **238 saved-editor/export frames match exactly** through the established
CLI. `test-results/vault-slime/editor-export-proof.json` records frame/atlas
hashes; `validation.json` records rollback, corrupt-backup refusal, destructive
build refusal and unchanged live art. Python/JavaScript syntax, Swedish
check, release-note guard and diff checks pass. No full suites run.

```sh
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server bash scripts/test-touch-bounded.sh tests/vault-slime-art.cjs
python3 scripts/vault_slime_review.py review
python3 scripts/vault_slime_review.py verify
python3 scripts/vault_slime_review.py upload
```

All **24 FileDrop PNG/GIF previews** have destination SHA256, size, dimensions,
original filename and MIME metadata verified. Receipt:
`test-results/vault-slime/filedrop-receipt.json`. Upload is a separate operation.
Review `verify` expects original live art; after approved release use the maker
CLI's `verify` for saved-editor equality.

- `valhallasc-vault-before.png`, `-after.png`, `-before-after.png`
- `valhallasc-vault-{kind}-frames.png` (all 34 frames)
- `valhallasc-vault-{kind}-animations.gif` (all five clips at original rates)
- `valhallasc-vault-{kind}-death-before-after.gif` (equal-scale death comparisons)

[Before/after comparison](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-vault-before-after.png).
Next unfinished zone: **Wyrdwood**. Owner picture approval and release verification are recorded above.
