# Prismwaste enemy artwork (Beta 1.39.21)

Owner approved the corrected artwork on 2026-11-04 with “ok deploy and finish skill”. Prepared from `/media/raid/valhallasc-data/prism-slime-work`, branch `feat/prism-slime-art`, base `a0bf0d7`, as Beta 1.39.21. Client-only release; the original art is retained in the external rollback backup. Public verification and deployment details are recorded below after release.

Six new editable native PixelFlow sources use Greenmeadow's glossy shading, large highlighted eyes (`#fffbea`), blush and chunky details. Each kind gets its own frame and anchor in `client/assets/prism.txt`; the 96×96, (48,90) fallback, 34-frame/five-clip layout, original 10 fps timing, kind IDs and game draw scales are preserved. The idle opaque pixels determine click bounds; planted feet, health-bar tops, shadows and portraits use the existing per-kind client path.

| Kind | Frame and anchor | New PixelFlow ID | Previous ID | Top |
| --- | --- | --- | --- | --- |
| `miragejackal` | 152×104, (60, 98) | `a7a7d194727e8f71` | `ab495b6f6c94cfd8` | 69 |
| `shardscarab` | 148×108, (62, 102) | `a320707216edfeb6` | `c05b3daeb5b65907` | 58 |
| `glassharrier` | 160×124, (66, 118) | `96ca59774a9b433c` | `c2ebb6c77c341029` | 99 |
| `prismsentinel` | 168×136, (62, 130) | `9d2105e426ee6c70` | `5bbb3705addd934f` | 92 |
| `mirrorqueen` | 164×140, (62, 134) | `ccac96cfa50e7469` | `69aa988de5edb6ea` | 94 |
| `sunshard` | 160×140, (64, 134) | `fc641927dad58174` | `ccd6ace7e306eda5` | 93 |

**miragejackal:** Sand-and-cream jackal with rainbow flank stripes, tall ears, four separate planted paws and a tapered prism-tipped tail. Pulls its connected neck/head high, then lunges forward with hinged snapping jaws. Knees buckle and its body settles onto its side; ears fold and the tail settles flat with its crystal intact.

**shardscarab:** Teal glass carapace, violet jointed legs and attached amethyst dorsal fan. Rears its rigid shell and spreads its fan, then slams forward with mandibles and flying shards. Legs curl, shell tips and cracks, dorsal shards settle.

**glassharrier:** Lavender hawk with connected icy-glass wing feathers, hooked gold beak and talons. Hovers, banks high, then dives forward with its neck following the head and talons reaching ahead. Falls onto the ground, folding its wings and shedding glass fragments.

**prismsentinel:** Silver armour with cyan crystal crest, kite shield and a gold-shafted crystal spear. Draws its spear back/up, then thrusts far forward before returning to guard. Knees buckle, armour slumps, shield tips and spear lies beside it.

**mirrorqueen:** Violet gown, indigo hair, mirror crown, hand mirror and orbiting glass fragments. Raises the mirror overhead and swings it forward to cast a reflected beam. Sinks into a pooled gown while the crown falls beside her and the cracked mirror rotates down.

**sunshard:** Floating amber solar crystal, pointed corona and two detached crystal fists. Raises its fists and flares its rays, then punches forward and downward. Core cracks and dims, rays extinguish, and fists and core break into grounded fragments.

## Pipeline

```sh
python3 scripts/make_prism_sprites.py preview|extents|build|refresh|export|verify
# Or the same commands through scripts/prism_slime_redraw.py.
# Refresh only explicitly named candidate sources:
python3 scripts/prism_slime_redraw.py refresh miragejackal
```

Source registry: `scripts/prism_slime_sources.txt`; names `valhallasc_prism_slime_style_<kind>_all`; raw indexed frames `scripts/prism_slime_<kind>_raw.npz`. `build` preserves registered sources and refuses `--replace`. `export` reads saved editor frames and writes `test-results/prism-slime/editor-export-proof.json`, preserving later editor edits. Common shading/helpers are imported from `astral_slime_redraw.py`; the old `prism_redraw.py` remains historical source only.

Every attack has eight unique poses: ready, anticipation, maximum wind-up, release, impact, follow-through, recoil, recovery. Frame 7 returns to the initial silhouette, including the queen's orbiting glass and Sunshard's rays. Every death also has eight distinct poses. All grounded kinds rest exactly on their anchor row in every living/death frame. The jackal has four distinct idle ground contacts and lower leg tracks (at least two contacts while walking), the scarab has six idle contacts (at least three while walking), and the sentinel has two (at least one while walking). The harrier and Sunshard hover at least 12 px above their anchor and settle onto it on death.

## Rollback

`/media/raid/valhallasc-data/prism-slime-original-20261104` holds all six previous atlases, `client/assets/prism.txt`, SHA256 hashes, old PixelFlow IDs, tops and frame overrides (`oldFrames: {}`).

```sh
python3 scripts/rollback_prism_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for a dry run. All seven source hashes and target paths are checked before the first write. Both actual restoration and corrupt-backup refusal were checked in a scratch directory. The previous PixelFlow sprites remain intact.

## Checks and review

```sh
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright \
NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules \
VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server \
bash scripts/test-touch-bounded.sh tests/prism-slime-art.cjs
```

145 unique focused real-art browser assertions passed across the four unchanged kinds and the corrected queen/Sunshard follow-up (49 assertions), including measured wind-up height, forward strike reach, recovery, grounding, distinct attack/death frames, source IDs, declared sizes, health-bar tops and production portraits. Evidence: `test-results/prism-slime/browser-check.log` (first four kinds complete through check 99), `browser-queen-sun-check.log` and `test-results/driver-zUppkK/`. The earlier scarab death-height and queen recovery failures were corrected before the passing checks. No broad suites, fight timing or balance sweeps were run.

Both controls fail at their intended assertions: a jackal atlas moved up one pixel fails ground contact; replacing attack poses with idle plus one recoloured opaque pixel per frame (eight different hashes) fails wind-up motion. Receipts: `test-results/prism-slime/mutation-proof.json` and `mutation-*.log`. Test knobs: `PRISM_ART_KINDS`, `MUTATE_KIND`, `MUTATE_PNG`.

204 editor/export frames match. Rollback, corrupt-backup refusal, destructive-build refusal, release-note checks, Swedish generation, Python/JavaScript syntax and diff checks pass. The older `tests/prism-ui.cjs` atlas expectation now uses `Field.frameOf` rather than 768×480; its unrelated historical zone-count assertions are untouched.

```sh
python3 scripts/prism_slime_review.py review
python3 scripts/prism_slime_review.py verify   # PRE-deployment: live art must still match the backup
python3 scripts/prism_slime_review.py upload
```

29 FileDrop PNG/GIF reviews: before, after, combined comparisons, eight attack frames before/after, all 34 frames per kind, per-kind animation/attack/death GIFs, and a combined six-kind death comparison. GIFs use the preserved clip timing. Upload verifies SHA256, MIME, dimensions, size and original-name metadata; receipt `test-results/prism-slime/filedrop-receipt.json`.

- [Before / after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-prism-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-prism-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-prism-deaths-before-after.gif)

Live version was checked as Beta 1.39.20 before preparing Beta 1.39.21. This client-only release needs no server build/restart or DB action. Next unfinished zone: The Obsidian Orrery (Zone 15).

## Owner review: tail crystal correction

The owner reported that the Mirage Jackal’s tail crystal looked weird and floppy. The tail now sweeps backward into a solid, faceted prism along its axis; the earlier hooked end and vertical hanging diamond are removed. The crystal keeps a fixed orientation in living clips and rotates as one rigid shape while the tail settles during death. Saved source ID, frame, anchor and tops are unchanged.

30 focused jackal browser checks pass (`test-results/driver-YrtmTN`, `test-results/prism-slime/browser-tail-fix.log`); 204 editor/export frame hashes and rollback still verify. The five other kinds’ full frame sheets are hash-identical. The preceding candidate art, script, raw grid and PixelFlow source packet are saved in `/media/raid/valhallasc-data/prism-slime-before-tail-fix-20261104`. All existing review pictures were refreshed; the two tail comparisons below bring the verified total to 31 files (`filedrop-tail-receipt.json`, `tail-fix-receipt.json`).

- [Tail before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-miragejackal-tail-before-after.png)
- [Tail animation before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-miragejackal-tail-before-after.gif)
