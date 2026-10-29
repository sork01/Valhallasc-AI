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

The same-day follow-up doubles the current forward chest profile: the chest
and under-chest depth factors change from 1.85/1.55 to 3.70/3.10. Width, height,
waist, back depth and attachment positions stay fixed. This is a doubling of
forward projection, rather than a uniform enlargement of the torso. The owner
again requested a silent release in the same version. Keep its before/candidate
assets and validation receipts separate in `test-results/female-torso-double`;
run the focused browser check with `TORSO_ART_DIR` pointing to that directory.
The fuller female surface is drawn as height bands with interpolated depth
and one silhouette outline. A single average-depth front/side polygon creates
crossing seams at this scale. The Priest delegates its female torso to this
shared surface renderer while retaining its original male drawing path.

Follow-up verification: 4,352 body/outfit frames remain nonempty and unclipped;
58 real-compositor checks pass. Twenty-four isolated female torso surfaces have
no interior outline crossings, while the former flat-polygon control fails in
all eight facings. Twenty-four male index/depth render pairs remain identical.
All 37 public art hashes match the checked candidates; public health is OK.
The updated FileDrop comparison is
`female-characters-double-before-after-20261029.png`. Version and release notes
remain unchanged.

The final same-day size adjustment reduces the doubled chest/under-chest
projection by 30%, from 3.70/3.10 to 2.59/2.17 (70% of that version). It retains
the corrected band/depth rendering. Candidates, before images and verification
receipts live separately in `test-results/female-torso-smaller`. This remains a
silent Beta 1.32.2 artwork update.

The 30% reduction passes all 58 focused compositor checks; all 4,352 generated
body/outfit frames are nonempty and unclipped. Geometry checks confirm 70% of
the previous forward projection across three torso fits. All 37 public asset
hashes match the checked candidates, health is OK, and the version/release
notes are unchanged. FileDrop comparison:
`female-characters-30pct-smaller-before-after-20261029.png`.
