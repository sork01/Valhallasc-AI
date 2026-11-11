# Nornroot Barrow enemy artwork candidate

Prepared 2026-11-11 on `feat/nornroot-slime-art`, private worktree `/media/raid/valhallasc-data/nornroot-slime-work`. Candidate Beta 1.43.1. Picture approval is required before deployment by the enemy remake rules in `TODO.md`. Reconcile the live version and other candidates' shared Cathedral manifest entries before integration.

Six editable native PixelFlow sources, 204 frames. Each uses a 176×172 frame and anchor (88,164), with eight distinct wind-up/strike/recovery poses and eight distinct material-fitting deaths. The original timing remains: idle 6 at 6 fps, walk 8 at 10 fps, attack 8 at 12 fps, hurt 4 at 10 fps, death 8 at 8 fps. The shared Cathedral manifest keeps its 96×96 fallback, (48,90) anchor, all 140 unrelated kinds and 129 unrelated native atlas hashes. Changes are artwork only.

| Kind | New native source | Identity, attack and death |
| --- | --- | --- |
| `barrow_hound` | `6137029beb8c9727` | Low violet quadruped with tall torn ears, a snarling long muzzle and gold thread bindings. Jaw retracts and bites; four legs fold beneath an intact side-fall corpse, and the eye closes. |
| `barrow_scarab` | `3a33b9a7d56b1d80` | Amber elytra, a dark shell seam, six jointed legs and hooked mandibles. Rears and snaps; rigid shell tips, legs curl, antennae relax and eyes close. |
| `barrow_spinner` | `1dd1b50eb3b8cf4f` | Spectral green face suspended between amber spindle flanges. Connected needle and thread lash forward. Spirit and face unravel; the solid spindle pieces fall and settle. |
| `barrow_doorward` | `0534d58de1950897` | Arn wears broad root/amber armour, an angular visor and an amber shield. Raises and swings a heavy spindle mace; visor extinguishes and rigid armour, shield and mace topple together. |
| `barrow_threadkeeper` | `bb7e69e9e70f9605` | Vessa has an exposed stern face, visible hands, a shaded ribcage/waist and overlapping robe folds. Articulated arm casts a shuttle with connected thread; cloth and spindle fall sideways. |
| `barrow_fatebound` | `35a90f4049a0d909` | The Unwritten King has asymmetric hollow eye sockets, a gaunt jaw and a broad root/gold crown. Both hands grip the shaft throughout its spindle strike; bones and plates fall and the crown separates. |

Spinner alone hovers at least 12 source pixels above the anchor; it settles monotonically during death. Other kinds stay grounded in every frame. Padding provides clearance rather than enlarging the visible creatures: old/new idle opaque bounds are hound 71×40 / 73×46, scarab 62×42 / 69×41, Spinner 60×48 / 51×46, Arn 58×57 / 58×58, Vessa 53×58 / 63×60, King 61×57 / 60×60. Scale was chosen against all six original in-game captures before creating sources. All final game views and whole frame sheets were reviewed.

The art advisor was consulted before implementation and after the first candidate. Final review corrected the King's lower hand to follow the rotated shaft, made his corpse fall farther onto its side, and relaxed the scarab antennae and jaws. Vessa keeps a readable face, separate fingers and shaded cloth volume from the start, following the previous Harbinger lessons.

## Pipeline

```sh
python3 scripts/nornroot_slime_redraw.py preview
python3 scripts/nornroot_slime_redraw.py build
python3 scripts/nornroot_slime_redraw.py export
python3 scripts/make_nornroot_sprites.py verify
python3 tests/nornroot-materials.py
python3 scripts/nornroot_slime_review.py review
```

Models: `nornroot_slime_models.py`; registry: `nornroot_slime_sources.txt`. `build` preserves registered native sources; `refresh KIND...` overwrites only named sources. `export` reads saved editor frames, preserves manual edits, derives health-bar tops and modifies only these six manifest entries. The maker's CLI/module entry points and `dungeon_cel.py nornroot` delegate before the old destructive path; both refuse `--replace`. Other candidate dungeon dispatches must be preserved on integration.

## Rollback

Seven originals, old editor IDs, byte counts, PNG dimensions, SHA-256 hashes and all unrelated native atlas hashes are saved outside the live tree at `/media/raid/valhallasc-data/nornroot-slime-original-20261111`.

```sh
python3 scripts/rollback_nornroot_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run by default. A disposable-copy check proved that dry run writes nothing, application restores all seven originals, and corrupt backups or unrelated manifest changes are refused before any write. Receipt: `test-results/nornroot-slime/rollback-proof.json`. Both original and new editor IDs remain saved.

## Validation and review

Validation receipts and 29 before/after PNG/GIFs live in `test-results/nornroot-slime/`. `tests/nornroot-slime-art.cjs` runs through the real production loader in the bounded browser runner; `NORNROOT_ART_KINDS` selects a small group. `MUTATE_KIND` plus `MUTATE_PNG` can substitute original art. `tests/nornroot-materials.py` checks actual exported death materials and accepts `MUTATE_MATERIAL=kind` for corpse-as-idle controls.

All 204 saved editor frames match their atlas cells. The bounded real-art browser passed 62 + 62 assertions across all six kinds; after the review corrections, the scarab/King batch passed 43 assertions (`driver-wkFXei`). Original-art mutation is rejected by the atlas contract. All 37 exported material/preservation checks pass, and each of the six corpse-as-idle controls is rejected by its material assertion. Both build entry points refuse --replace without changing source IDs or the manifest. Swedish build, release-note guard and Python/JavaScript syntax checks pass.

29 before/after PNG/GIFs uploaded and verified against SHA-256, MIME/metadata, byte lengths, dimensions and animation frame counts. Receipt: `test-results/nornroot-slime/filedrop-receipt.json`.

- [Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-nornroot-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-nornroot-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-nornroot-deaths-before-after.gif)

Each kind also has a full 34-frame sheet, combined animation GIF and attack/death comparison GIFs under `valhallasc-nornroot-<kind>-*`. No server build, restart, combat sweeps, map or database changes. Next art group: The Shattered Span (`SPAN-SLIME-ART`).
