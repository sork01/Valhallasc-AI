# Character body art

The five female rigs use the shared `cel_common.torso_panels` profile, including
the Priest's independent renderer. The 2026-10-29 adjustment widens the chest
and increases its forward depth, with a separate under-chest taper. Neck,
shoulder and hip attachments stay fixed. The male branch is unchanged.

The body undershirts and original armor/robe sets follow this profile. Export
only those generated female layers with:

```
python3 scripts/export_character_torso.py warrior --out test-results/female-torso/assets
```

Repeat for `mage`, `assassin`, `priest`, and `hunter`. This prepares candidates
without saving live files. It preserves the existing metadata and rebuilds
only the exported parts' bounds. Other gear, bespoke progression/raid artwork,
and editor IDs remain intact. Do not use a broad progression gear rebuild or
overwrite its saved editor sprites for a body adjustment.

Run `bash scripts/test-touch-bounded.sh tests/female-torso-art.cjs` after all
five candidates exist. The private HTTP fixture loads the real compositor,
before/candidate bodies and original outfits. Matching poses, colors, scale,
and clothing produce comparison rows in `test-results/female-torso`.

2026-10-29 verification: 4,352 exported body/outfit frames are nonempty and
unclipped; 58 browser assertions pass across all five classes, animations,
outfits and front/side views. Occluded chest changes need not alter every
composite pixel. Twenty-four male torso index/depth render pairs match the
previous renderer exactly. Metadata and unrelated part bounds are unchanged.
The exact 37 checked PNG/depth/bounds files are listed in `checked-hashes.txt`.

The owner requested a quiet update: Beta 1.32.2 and release notes stay as they
were. This is client artwork only; no service restart or database changes.
Reload to replace sprite sources already cached in a running page.

All 37 installed public art files match the checked SHA-256 values. Public
health is OK. The reviewed side-by-side sheet was copied to the owner's
FileDrop as `female-characters-before-after-20261029.png`, with its SHA-256
verified after upload.
