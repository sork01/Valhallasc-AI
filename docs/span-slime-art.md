# The Shattered Span enemy artwork

Owner accepted all enemy sprites on 2026-11-12. Integrated for Beta 1.44.0; see
[the combined release](enemy-sprites-release.md). The private-candidate status
below records the original review stage and is superseded by that approval.

Private candidate, 2026-11-11, branch `feat/span-slime-art`, worktree `/media/raid/valhallasc-data/span-slime-work`. Candidate Beta 1.43.1; not deployed. The enemy-art queue requires picture approval before integration. Reconcile the live version and other pending candidates' Cathedral manifest slices before release.

Six new editable native PixelFlow sources, 204 frames. Five kinds use 176×172 cells at (88,164); Vaelor uses 192×160 at (88,152), providing room for his glaive sweep within PixelFlow's 1,048,576-cell source limit. Extra padding preserves the established visible size. The shared Cathedral fallback remains 96×96 at (48,90), with all 146 kinds, original 6/10/12/10/8 fps and idle/walk/attack/hurt/die counts 6/8/8/4/8. All 140 unrelated kind entries and 129 unrelated native PNG hashes remain unchanged. Server, mechanics, maps, stats and database are unchanged.

| Kind | Native source | Identity, attack and death |
| --- | --- | --- |
| `span_lynx` | `b117f296612f1f89` | Low cyan feline, tufted ears, short muzzle and glass fangs; amber predatory eye. Crouches, reaches with a forepaw and bites. Four jointed legs fold and the intact body falls onto its side; eye closes. |
| `span_sentinel` | `7a4c75d44af6a59d` | Gold segmented construct with one recessed cyan visor and crystal forearms. Raises both forearms, then hammers down. Visor goes dark, elbows fold inward and rigid plates fall fully onto their side. |
| `span_caster` | `44cbcf217c1a7f58` | Violet spectral refractor between solid gold prism rings, pointed face and magenta eyes. Rings counter-rotate as connected crystal hands draw back and thrust. Spirit and face unravel; tangible rings descend and settle. |
| `span_warden` | `38523b9a2dc0c337` | Torstein's winged helm, exposed stern face, gold plate, cyan kite shield and hooked toll polearm. Braces and swings the polearm about his gripping hand. Body, shield and weapon fall together. |
| `span_weaver` | `ac25a2ea1ae665ec` | Sunniva's framed face, silver hair, fitted violet ribcage and waist, overlapping shaded robe folds and separate fingers. Both hands spread connected coloured threads, then cast across the body. Robe falls sideways and hands relax; eyes close and magical threads fade. |
| `span_archon` | `9c9e7d705090cd96` | Vaelor's cyan plate, split winglike cape, three-point crown, masked jaw and crystal glaive. Two hands follow the rotating shaft through a broad Sundering Arc sweep. Body and armour topple, cape folds underneath, crown separates and grips relax. |

Caster alone hovers at least 12 source pixels above the anchor in all living clips, then settles monotonically through death. Every grounded kind rests on its anchor in every frame. Eight distinct attack poses show wind-up, strike and recovery; all eight death poses are distinct. Raw-canvas checks precede the grounding roll so clipped source art cannot pass by being moved afterwards.

Old/new idle opaque sizes, chosen against all six original game captures before source creation: Lynx 72×45 / 68×46; Sentinel 53×57 / 59×58; Caster 57×38 / 53×39; Torstein 62×57 / 62×54; Sunniva 52×59 / 51×56; Vaelor 65×58 / 61×58. The art advisor reviewed the approach and all full sheets. Review corrected the Sentinel's outstretched arms, which initially propped up its corpse. All final whole-frame sheets and six game views were inspected.

## Pipeline

```sh
python3 scripts/span_slime_redraw.py preview
python3 scripts/span_slime_redraw.py build
python3 scripts/span_slime_redraw.py export
python3 scripts/make_skybridge_sprites.py verify
python3 tests/span-materials.py
python3 scripts/span_slime_review.py review
```

`span_slime_models.py` contains the connected rigs and material poses; `span_slime_sources.txt` saves editor IDs. Build preserves registered sources; `refresh KIND...` overwrites only named sources. Export reads editor frames, preserving manual changes, derives health-bar tops and merges only the six owned Cathedral entries. `make_skybridge_sprites.py` delegates module and CLI entry points to the native pipeline; its old drawings are removed. `dungeon_cel.py skybridge` delegates before its legacy destructive path. Both native and maker builds refuse `--replace` without touching sources or the manifest. Preserve other candidates' dungeon dispatches on integration.

## Rollback

Seven original files, hashes, sizes, dimensions, editor IDs and unrelated native atlas hashes are saved at `/media/raid/valhallasc-data/span-slime-original-20261111`.

```sh
python3 scripts/rollback_span_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run is the default. Disposable-copy checks proved that dry run writes nothing and apply restores all seven originals; corrupt backups and unrelated shared-manifest changes are refused before writes. Receipt: `test-results/span-slime/rollback-proof.json`. Both original and new PixelFlow sources remain available.

## Validation and review

All 204 editor/export frames match. Bounded real-art browser checks pass in two three-kind batches (62 + 62 assertions); the corrected Lynx/Sentinel batch passes 43 assertions. The browser checks production frame lookup, sources, all clips, substantial wind-up/strike/recovery, grounding/hover, health-bar tops and portraits. `SPAN_ART_KINDS` selects a small batch. Original-atlas substitution via `MUTATE_KIND` and `MUTATE_PNG` must fail the frame contract. The existing Skybridge UI atlas assertion now uses `Field.frameOf` for per-kind dimensions; its unrelated travel/music checks were not rerun.

38 semantic material/preservation checks pass. Each of the six idle-as-corpse mutations is rejected by its material assertion (`MUTATE_MATERIAL=kind` and `SPAN_MATERIAL_KINDS=kind`). Swedish build/check, release-note guard and Python/JavaScript syntax checks pass. Receipts, full-frame sheets and game captures live in `test-results/span-slime/`.

29 before/after PNG/GIFs were uploaded to FileDrop and verified (3,726,679 bytes), including roster comparisons, all attack frames, animated death comparisons, and a full frame sheet plus three animations per kind. `test-results/span-slime/filedrop-receipt.json` verifies SHA-256, byte length, MIME/metadata, dimensions and animation frame counts.

- [Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-span-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-span-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-span-deaths-before-after.gif)

Artwork remains private pending picture approval. Next art group: The Drowned Longship (`LONGSHIP-SLIME-ART`).
