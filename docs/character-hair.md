# Directional character hair

Beta 1.31.1, 2026-10-28. The owner requested keeping the same version.

All five classes previously painted their crown/fringe on the camera-facing
head axis. Bodies and eyes changed facing, but the top hair kept the same
silhouette and highlights. Earlier Priest fixes handled the hood and long hair;
they did not fix this shared scalp issue.

`scripts/turning_hair.py` supplies head-local curved scalp surfaces, parting,
fringe and tufts. Facing and pose twist project these surfaces into each frame.
Strands belong to the head; lighting remains in world space. Separate scalp
rendering preserves the actual silhouette and adds a thin outline. Depth stays
within the existing hat-over-hair contract. Only scalp polygons are replaced;
the class face, hair colour ramps, long hair, beards and worn items remain their
own artwork. Both bodies of Warrior, Mage, Assassin, Priest and Hunter use it.

The five local sprite makers include the shared hair source in their cache
revision. Male Assassin's body is legacy art: the local `render_body_frame`
adapter wraps the read-only original renderer for that frame, then restores it.
No file in the original Valhalla project is changed. Run exporters serially.

`scripts/export_character_body.py CLASS [--female]` prepares only the body colour
and depth PNGs and a matching bounds sidecar in
`test-results/turning-hair/assets/`. It preserves all equipment images, metadata
and editor IDs. Prior files are archived in `test-results/turning-hair/before/`.
`--editor` changes only the existing body layer in saved male editor sprites,
archives their state, and verifies other layers/palettes stayed identical.
Female and legacy Assassin bodies have no saved body editor layer. `--write`
installs the candidate body and its single bounds entry. Keep all other part
bounds unchanged. Use CPU/memory limits on this shared host.

Focused verification before installation:

```sh
HAIR_CANDIDATES=1 bash scripts/test-touch-bounded.sh tests/character-hair-art.cjs
```

It compares canonical crown
silhouettes across facings against the prior PNGs, then uses the actual browser
compositor across every pose, direction and body, bare and with starter headgear.
Snapshots and a verification report live in `test-results/turning-hair/`.
These checks target the hair itself: a whole-character hash or a hood-only
rotation check cannot catch a stationary crown on a turning body.

All **5,440 real composite frames pass** across ten rigs: 272 poses each, with
and without starter headgear. The new crowns have 64–128 distinct sampled depth
levels per facing, compared with 2–4 in the old flat scalp paintings. Canonical
crown masks change with facing independently of body movement. No frame clips
and starter headgear remains visible in every pose. All ten comparison sheets
were visually reviewed in `all-crowns-reviewed.png`. `checked-hashes.txt` records
the exact 30 candidate PNG/bounds files that passed.

Some male editor sprites predate the GM palette additions. Remap only colours
used in the body; absent colours used solely by unrelated gear do not require
changing the saved editor palette. Every used body colour must already exist.

Installed the exact 30 checked files. All public body PNGs, depth PNGs and bounds
match `checked-hashes.txt`; release notes and the unchanged Beta 1.31.1 page also
match local hashes (`public-verification.txt`). All other part bounds are
unchanged. The 160 existing male body editor sprites were updated with their
other layers, palettes and IDs preserved. Female and legacy Assassin bodies
remain generated assets. Python syntax, browser-test syntax, release notes and
diff checks pass. No Rust, world data or service restart was involved. Reload
the game to replace sprite sources already cached in the running page.
