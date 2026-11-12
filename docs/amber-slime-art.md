# The Amber Archive enemy art candidate

Owner accepted all enemy sprites on 2026-11-12. Integrated for Beta 1.44.0; see
[the combined release](enemy-sprites-release.md). The private-candidate status
below records the original review stage and is superseded by that approval.

Prepared 2026-11-11 in `/media/raid/valhallasc-data/amber-slime-work`, branch `feat/amber-slime-art`. Private, awaiting picture approval under the enemy remake rules in `TODO.md`. Candidate Beta 1.43.1; reconcile the live version before deployment.

Seven native editable PixelFlow sources, 238 frames total. Each uses a 176×172 frame with anchor `(88,164)`, eight distinct wind-up/strike/recovery frames and eight distinct death frames. Original timing stays `idle` 6, `walk` 10, `attack` 12, `hurt` 10 and `die` 8 fps. The shared Cathedral manifest retains its 96×96 fallback, `(48,90)` anchor and all 139 other kinds. All 128 unrelated native atlases remain unchanged; the other 11 kinds retain their borrowed source IDs. Art only: encounter data, stats, routes and server code are unchanged.

| Kind | PixelFlow source | Identity and attack | Death |
| --- | --- | --- | --- |
| `amber_page` | `72829a6edfe8151f` | Living Page: curled parchment, angular ink eyes, wax seal; corner uncoils into a paper-edge slash | Ink face disappears as parchment folds and tears into a low sheet; wax seal stays attached |
| `amber_moth` | `e6680702d6dbbdfd` | Script Moth: four veined amber wings, segmented abdomen, serrated antennae, six attached legs, compound eyes; banks and thrusts proboscis | Wings fold at their hinges, legs curl, eye glints darken, body lands |
| `amber_sentinel` | `f8fb0bd8e0cb3af9` | Archive Sentinel: amber armour, narrow continuous visor, leather tome shield and key-spear; braces and thrusts | Visor darkens, greaves buckle and rigid armour, shield and spear topple sideways |
| `amber_curator` | `b55a6c9239a54146` | The Curator: swept white hair, hooked nose, half-moon glasses, robes, keys and quill; winds up and casts ink | Knees buckle and body falls sideways with head, robes, keys and quill retained |
| `amber_chronicle` | `edeb25b4f2637140` | The Living Chronicle: red leather grimoire, seal cyclops, paper-tooth maw; covers and pages fan open | Binding breaks, face goes dark, rigid covers rotate sideways and loose leaves settle |
| `amber_memory` | `1dedbe85d6adf7ff` | The Last Memory: hollow-eyed spirit inside a faceted amber reliquary; spectral hand reaches forward | Spirit dissipates upward, amber halves rotate outward into grounded fragments |
| `amber_cocoon` | `556c4cbc0e04ffe1` | Amber Cocoon: curled humanoid trapped in resin; restrained defensive resin pulse | Rigid shell splits outward and trapped figure disappears, suggesting release |

The Page, Moth, Chronicle and Memory hover at least 12 source pixels above the anchor in every living frame and settle monotonically onto row 164 during death. Sentinel, Curator and Cocoon remain grounded in every frame. Per-kind art scales were chosen against the original idle bounds and private in-game captures, rather than enlarging art to fill the new canvases. Faces and silhouettes differ between kinds; no shared blush/round-eye overlay.

The cocoon represents the Last Memory's **Amber Stasis**, which traps a player; it is not an insect chrysalis. Its existing zero-damage behavior is unchanged. The required attack animation is a defensive resin pulse.

## Pipeline

```sh
python3 scripts/amber_slime_redraw.py preview
python3 scripts/amber_slime_redraw.py extents
python3 scripts/amber_slime_redraw.py build
python3 scripts/amber_slime_redraw.py export
python3 scripts/make_yearwheel_dungeon_sprites.py verify amber_page amber_moth amber_sentinel amber_curator amber_chronicle amber_memory amber_cocoon
python3 scripts/amber_slime_review.py review
python3 tests/amber-materials.py
```

Models live in `amber_slime_models.py`; source IDs in `amber_slime_sources.txt`. `build` preserves existing native sources and refuses `--replace`; `refresh KIND...` overwrites only named editor frames. `export` reads saved editor frames, preserves hand edits and derives health-bar tops from all idle frames. `make_yearwheel_dungeon_sprites.py` delegates Amber calls at both CLI and module level (including `boss_helper_art.py`), preserving Silent Solstice's maker functions. `dungeon_cel.py amber build|preview` delegates before its legacy destructive build path. Other candidate branches also edit `dungeon_cel.py`; preserve their dispatches when integrating.

## Backup and rollback

Eight original files, their SHA-256 hashes, dimensions, byte sizes and old PixelFlow IDs are saved at `/media/raid/valhallasc-data/amber-slime-original-20261111`. `manifest.txt` also records hashes of the 128 unrelated native Cathedral atlases.

```sh
python3 scripts/rollback_amber_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Dry run by default. Tested on a disposable copy: dry run writes nothing, `--apply` restores all eight files byte-for-byte, corrupt backups are refused before writes, and unrelated Cathedral manifest changes are refused before writes. Old and new PixelFlow sources are retained. Receipt: `test-results/amber-slime/rollback-proof.json`.

## Focused validation

- 238 saved editor frames equal their exported atlas cells, including the Last Memory's corrected amber facets.
- Bounded real-art browser batches pass 81 + 62 assertions (`driver-XvZseD`, `driver-1AjcXw`): frame/anchor contracts, timing, nonempty unclipped cells, distinct clips, eight substantial attack poses with recovery, grounding/hovering, death landing, health tops, source IDs, production portraits and no page errors.
- Sleeping `amber_cocoon` art is explicitly loaded and rendered as a private preview actor; its production source and portrait are checked without playing the boss encounter. A further 24-check helper run (`driver-i7oFYW`) verifies a substantial production world-sprite draw and captures it synchronously. Preview actors need finite `seed`, hop and clip timers; missing `seed` makes the idle frame index NaN and silently draws no sprite. A later live snapshot removes the preview, so its canvas capture stays in the same browser evaluation as the draw.
- Routing the original Living Page atlas through the production loader fails the frame contract as required.
- 39 exported-art material checks pass. All seven `MUTATE_MATERIAL=<kind>` controls replace the corpse with idle **after** animation-contract checks, and fail the corresponding material assertions. Receipts: `materials.log`, `material-mutations.json`.
- `tests/whats-new-notes.cjs` and the Swedish build pass for candidate Beta 1.43.1. No broad game suites or combat balance runs.

The browser capture loop waits for authoritative hero arrival, because preloaded art alone does not prove the camera has reached a later room. Review sheets allocate full frame-sized cells and assert image bounds, so wide book covers and amber fragments remain visible.

## Review pictures

33 PNG/GIF files, 3,660,779 bytes, uploaded and verified against local SHA-256, FileDrop metadata, MIME, byte counts and dimensions. Receipt: `test-results/amber-slime/filedrop-receipt.json`.

- [Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-amber-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-amber-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-amber-deaths-before-after.gif)

Each kind also has a full 34-frame sheet, combined animation GIF, attack comparison and death comparison under `valhallasc-amber-<kind>-*`.

Next enemy group: The Silent Solstice (`SOLSTICE-DUNGEON-SLIME-ART`).
