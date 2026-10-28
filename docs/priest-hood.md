# Priest hair and starter hood

Fixed in the existing Beta 1.31.1 release, 2026-10-28.

Pilgrim's Hood used a screen-facing opening for every forward/side facing.
The body and face turned, but the opening, gold trim and cords did not.
`pilgrim_hood` in `scripts/make_priest_sprites.py` now moves and narrows the
opening with the same facing/twist values as the eyes. The crown follows the
head axis, the far cord disappears in profile, and rear views stay closed.
Both male and female assets use this geometry.

`scripts/export_priest_part.py` exports only the selected colour and depth
atlases and refreshes only that part's bounds entry. It leaves other equipment,
metadata and saved editor IDs intact. First run without `--write` to inspect
candidate PNGs in `test-results/priest-hood/`. Install/update under the shared
host's CPU/memory limits:

```sh
python3 scripts/export_priest_part.py --editor --write
python3 scripts/export_priest_part.py --female --write
python3 scripts/export_priest_part.py --female --part body --out test-results/priest-hair --write
```

The male rig has 40 saved Pilgrim editor sprites. `--editor` archives their
previous state in `test-results/priest-hood/editor-before/`, changes only the
hood layer, and verifies that all other layers and palettes stay identical.
The legacy female base metadata has no saved editor IDs, so it uses generated
art; `--editor` refuses that rig before modifying anything. Do not run a full
male local export, which would discard its editor IDs.

Focused hood validation: `bash scripts/test-touch-bounded.sh tests/priest-art.cjs`
passes all 544 actual client composite frames across both bodies, all clips and
eight facings. Direction checks distinguish left/right trim from the original
centered trim and verify closed rear views. Screenshot reviewed:
`test-results/priest-hood/client-facings.png`. Both hood bounds match every frame;
all other bounds are preserved. Python/JS syntax, release notes and diff checks
pass. Public hashes match the four changed PNGs, two bounds sidecars and release
notes. This is client-only and needs no server restart.

The owner clarified that the female hair also looked wrong while turning.
The fringe's outer crown now stays rounded over the skull while its inner
hairline and cheek locks follow the face's facing/twist. Long hair uses curved
back and side surfaces, with depth along each surface, rather than one flat
sheet. This preserves volume in profile and keeps the hair connected above the
collar. The female body no longer inherits the man's goatee. These changes are
limited to the female body colour/depth atlases and its bounds entry; male
source samples remain identical across five clips and front/side/rear views.

Use `tests/priest-art.cjs --hair` for female poses with and without a hood,
profile-volume and walk-motion checks. A candidate can be checked before
installation with `PRIEST_HAIR_PREVIEW=1`; the exporter saves candidate bounds
alongside the PNGs so old bounds cannot crop the new hair during preview.
All 272 female poses pass with and without the hood. Both profile views retain
7–9 hair pixels at the sampled lower lengths (previously 1–2), and the eight-frame
walk has five distinct hair positions, matching its symmetric sine cycle.
The actual client screenshot is `test-results/priest-hair/client-facings.png`.
Only the female body PNGs and its body bounds entry changed in this follow-up;
all other part bounds are preserved. The installed files match the checked
candidates and public copies. Beta 1.31.1 remains the release version.

The subsequent shared crown correction covers every class and both bodies,
including the Priest scalp. Current source, export and all-rig validation are
in `docs/character-hair.md`; the male-preservation statements above describe
the earlier female long-hair follow-up.
