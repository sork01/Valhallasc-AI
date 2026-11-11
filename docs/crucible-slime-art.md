# The Solar Crucible enemy art candidate

Prepared 2026-11-11 in `/media/raid/valhallasc-data/crucible-slime-work`, branch `feat/crucible-slime-art`. Private, awaiting picture approval under the enemy remake rules in `TODO.md`. Proposed Beta 1.43.1; reconcile the live version before eventual deployment.

Seven native, editable PixelFlow sources (six dungeon encounters plus the Cinder of the Crucible boss-mechanic helper), 238 frames total. Each has a 176×172 frame with anchor `(88, 164)`, eight distinct wind-up/strike/recovery frames and eight distinct death frames. Original timing is preserved: `idle` 6, `walk` 10, `attack` 12, `hurt` 10 and `die` 8 fps. The shared Cathedral manifest keeps its 96×96 fallback, `(48, 90)` anchor and all other 139 kinds (`146 - 7 = 139`). Art only; encounters, stats, maps and server code are unchanged.

| Kind | PixelFlow source | Identity and attack | Death |
| --- | --- | --- | --- |
| `solar_emberling` | `e7594982ee3d3da6` | Squat basalt-and-charcoal furnace imp on two stumpy iron-shod legs, glowing grate belly, slanted ember slit eyes, fanged coal jaw, five-tongued solar flame crown and ember-tongs; winds up and thrusts tongs forward | Flame crown gutters out completely while the cracked coal shell splits into two tilted halves on the ground |
| `solar_sunmoth` | `18849de5452c5ee9` | Four-winged solar moth with bronze-chitin thorax, segmented abdomen, serrated antennae, compound eyes, eclipse-spot forewings and blazing solar proboscis; folds back and dives | Descends to the ground, folds sunburst wings inward, curls six chitin legs under its thorax and extinguishes its eclipse-eye glints and proboscis |
| `solar_crucible_guard` | `f8ae545abb94816e` | Heavy dark-iron forge sentinel on two planted greaves, grated furnace breastplate, cauldron-rimmed helm with bubbling molten gold, riveted cauldron shield and forge hammer; braces shield and swings hammer | Molten helm, furnace ribs and hammer core cool and go dark while rigid dark-iron armour, shield and hammer slump forward onto the ground |
| `solar_ashwarden` | `23d4d0c9a8a7c6ce` | Tall soot-and-obsidian warden in ash-mantle plates, horned furnace-stack helm with triple visor slits, shoulder ember-braziers, ash-urn buckler and ash-forged greatblade; draws blade high and cleaves | Shoulder ember-braziers, visor slits and greatblade magma edge extinguish while obsidian helm, mantle and greatblade slump onto the ground |
| `solar_heliomancer` | `0a25bf053743460c` | High solar prelate in layered gold-and-crimson vestments, sun-miter helm, eight-rayed floating sun-disc halo, solar astrolabe buckler and Twin-Sun Scepter; raises scepter and thrusts a solar lance forward | Radiant sun-disc halo and scepter solar core extinguish while vestments, miter and scepter collapse into a low heap on the ground |
| `solar_heart` | `0e592ddf1d957a6b` | Hovering dark-iron crucible-sphere suspended above the floor by eight magnetic containment fins and twin riveted iron bands, with blazing three-slit solar aperture, furnace grate teeth and roaring corona; flares and thrusts a concentrated solar beam | Roaring solar corona and blazing core extinguish as the heavy dark-iron crucible bowl and containment fins crash onto the ground |
| `solar_cinder` | `152360ad1558a592` | Boss-mechanic helper (`Twin Suns` split): jagged basalt-slag cinder construct on two stocky iron legs with internal magma fissures, three-horned slag crest, asymmetric lava-hollow eyes, fanged grate maw and molten slag-fist; winds up and slams | Internal magma fissures and lava-hollow eyes gutter out as the basalt-slag carapace splits wider and lower across the ground |

`solar_sunmoth` and `solar_heart` hover well above the anchor row (`164`) during all living clips and descend monotonically onto `164` on death. The other five stay grounded on row `164` across all 34 frames. Shapes use clean shaded bands without checkerboard dither; faces are distinct creature and helm designs without shared round-eye or blush overlays.

## Pipeline

```sh
python3 scripts/crucible_slime_redraw.py preview
python3 scripts/crucible_slime_redraw.py extents
python3 scripts/crucible_slime_redraw.py build
python3 scripts/crucible_slime_redraw.py export
python3 scripts/make_solar_sprites.py verify
python3 scripts/crucible_slime_review.py review
python3 scripts/crucible_slime_review.py verify
python3 tests/crucible-materials.py
```

`crucible_slime_models.py` contains the seven articulated models. Registry: `scripts/crucible_slime_sources.txt`. `build` preserves saved sources and refuses `--replace`; `refresh KIND...` overwrites only the named editor frames. `export` reads the saved editor, preserves hand edits and derives health-bar tops from idle bounds. `make_solar_sprites.py` retains its imported helpers (used by `boss_helper_art.py`) and delegates `preview`, `extents`, `build`, `refresh`, `export` and `verify` to `crucible_slime_redraw`. `dungeon_cel.py solar_crucible build|preview` delegates before the legacy deletion path.

## Backup and rollback

Eight originals (`client/assets/cathedral.txt` and the seven `client/assets/cathedral_<kind>.png` atlases), SHA-256 hashes, byte sizes, dimensions and old PixelFlow IDs are saved outside the served tree at `/media/raid/valhallasc-data/crucible-slime-original-20261111`.

```sh
python3 scripts/rollback_crucible_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run by default. All backup sources and destinations are validated before writes. Restoring on a disposable copy, refusing a corrupt backup and refusing an unrelated Cathedral-manifest edit all pass. Rollback never deletes old or new PixelFlow sources.

## Focused checks

Bounded real-client batches (`tests/crucible-slime-art.cjs` via `scripts/test-touch-bounded.sh`) verify all seven kinds in two batches (the six awake dungeon encounters by teleporting to their Zone 37 spawns, plus the sleeping ambush helper `solar_cinder` loaded into `Field.cathedralSprites.img` and rendered in-world), checking 176×172 per-kind frames, `(88, 164)` anchors, 1408×860 atlases, 146 total Cathedral kinds, clip frame rates, 34 non-empty non-clipped cells, 8 distinct attack and death frames, forward strike reach, grounding/hovering, monotonic flying descent, health-bar tops and zero page errors. Routing the original `cathedral_solar_emberling.png` into the production loader fails the frame-contract check as expected.

Exported-art material assertions (`tests/crucible-materials.py`) verify extinguished flames/coronae and split coal/slag shells (`solar_emberling`, `solar_cinder`), folded chitin wings (`solar_sunmoth`), cooled molten iron and slumped armour (`solar_crucible_guard`, `solar_ashwarden`), collapsed solar vestments (`solar_heliomancer`) and extinguished crucible core (`solar_heart`), and fail under `MUTATE_KIND=solar_emberling` and `MUTATE_KIND=solar_crucible_guard`.

## Review pictures

All 33 PNG/GIF review files (`5 + 7 * 4`) uploaded to FileDrop and verified against local SHA-256, metadata, MIME, byte counts and dimensions (`test-results/crucible-slime/filedrop-receipt.json`):

- [Before/after](https://gunning.se/filedrop/?download=valhallasc-crucible-before-after.png)
- [Attacks](https://gunning.se/filedrop/?download=valhallasc-crucible-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/?download=valhallasc-crucible-deaths-before-after.gif)

Next enemy group: The Sunken Astrolabe (`ASTROLABE-SLIME-ART`).
