# Cairnspine enemy art candidate

Private candidate on `feat/cairn-slime-art`, checkout `/media/raid/valhallasc-data/cairn-slime-work`. Seven new native, editable PixelFlow sources replace the seven older enemies in `client/assets/cairn.txt`. The six NPC entries and their atlases, the separately authored Avalanche Bear, world data and all combat behavior are preserved. This candidate awaits picture approval before deployment; it has no version bump or server release.

| Creature | Face and silhouette | Attack | Death |
|---|---|---|---|
| Scree Ferret | low russet mustelid, dark angular mask, amber bead eye, slate dorsal stones | crouches, then lunges with a connected toothed jaw | knees fold, belly and thin tail settle |
| Stone Ibex | beige coat, thick curved ridged horns, horizontal pupil, pointed beard | draws its neck back, then lowers its horns into a headbutt | knees buckle, head and rigid horns tip toward the ground |
| Slate Raven | compact slate-blue feather fan, narrow orange glare, pointed bill | wings draw back, neck extends into an asymmetric peck | wings fold and the bird tumbles from its hover |
| Ridge Adder | olive zigzag coils, vertical slit eye, hinged fang jaw | neck coils back, then extends into a long bite | coils release across the floor and the head lowers |
| Cairn Behemoth | squat slate boulders, recessed rectangular amber eyes, moss seams | heavy slab fists rise, then slam down and out | knees give way and rigid stone parts settle into rubble |
| Whitebark Titan | tall pale birch, dark grain, asymmetric branches, hollow knot eyes | branch arms draw up, then rake forward with splintered claws | root legs give way and the trunk tips onto its side |
| Storm Condor | broad storm-blue wings, bare crimson head, white ruff, hooked gold beak | wings rise, then sweep down with talons reaching | wings fold and the heavy bird crashes onto the ground |

Each source has 34 frames: idle 6, walk 8, attack 8, hurt 4, die 8; all 10 fps. Every attack and death frame is distinct. Frames are 176×172 with anchor (88,164), below PixelFlow's per-source pixel limit. Per-kind art scales keep idle dimensions close to the original art; the renderer already enlarges elites. Grounded creatures rest on the anchor row. Both birds hover at least 12 pixels above it in every living frame and settle onto it at the end of death. A lower raw drawing origin leaves room for tipped poses; raw borders are checked before the final grounding translation.

The exporter reads saved editor cels, preserves edits, writes per-kind frame metadata and derives health-bar tops from idle bounds. The shared NPC fallback remains 96×96 at (48,90). `make_cairn_sprites.py` retains its helper functions but its CLI delegates to the new pipeline; `build --replace` is refused.

```sh
python3 scripts/cairn_slime_redraw.py preview
python3 scripts/cairn_slime_redraw.py extents
python3 scripts/cairn_slime_redraw.py build
python3 scripts/cairn_slime_redraw.py refresh KIND
python3 scripts/cairn_slime_redraw.py export
python3 scripts/make_cairn_sprites.py verify
python3 scripts/cairn_slime_review.py review
python3 scripts/cairn_slime_review.py verify
python3 scripts/cairn_slime_review.py upload
```

Backup: `/media/raid/valhallasc-data/cairn-slime-original-20261111`. It contains seven original atlases, the shared manifest, original PixelFlow IDs and hashes. Rollback validates every backup and unrelated manifest entry before writing. Default is a dry run:

```sh
python3 scripts/rollback_cairn_art.py --target /path/to/checkout --apply
```

Focused browser check: `tests/cairn-slime-art.cjs` through `scripts/test-touch-bounded.sh`, with `REAL_SPRITES=1`, the main checkout's test-profile binary, browser cache and node modules. `CAIRN_ART_KINDS` limits checking to named kinds. `MUTATE_KIND=screeferret MUTATE_PNG=/media/raid/valhallasc-data/cairn-slime-original-20261111/client/assets/cairn_screeferret.png CAIRN_ART_KINDS=screeferret` substitutes old art and must fail. Evidence, before/after sheets, complete frame sheets and original-rate attack/death GIFs live under `test-results/cairn-slime/`.

## Verification (2026-11-11)

- All 238 saved editor cels match their exported frames; `make_cairn_sprites.py verify` passes. Raw bounds, eight distinct attack/death frames and material-specific motion were checked, and every full frame sheet and in-game creature screenshot was inspected.
- The first seven-kind bounded browser pass had 143 passing assertions and one failure: the raven had eleven opaque colors instead of twelve. Its feather highlights were improved; screenshot review also sharpened the titan's face and moved moss away from the behemoth's eye. The focused follow-up on those three changed creatures passes all 64 assertions with no browser errors. The other four atlas hashes are unchanged. Evidence: `test-results/driver-MJesKA` and `test-results/driver-QuWw44`.
- Substituting the original ferret atlas fails the production frame lookup assertion as required (`test-results/cairn-browser-mutation.log`). No broad test suites or balance runs were used.
- Hash-verified eight-file rollback passes, including refusal of a corrupt backup and changed unrelated NPC metadata before writing. All six shared NPC atlases and entries, the Avalanche Bear manifest/atlas, and live enemy assets remain unchanged. Receipt: `test-results/cairn-slime/validation.json`.
- 33 FileDrop PNG/GIF reviews have matching hashes, metadata, dimensions and sizes; receipt `test-results/cairn-slime/filedrop-receipt.json`. Main review files: `valhallasc-cairn-before-after.png`, `valhallasc-cairn-attacks-before-after.png`, `valhallasc-cairn-deaths-before-after.gif`. No live release or version bump.
- JavaScript syntax, Python compilation and whitespace checks pass. The candidate source and assets remain in the private worktree for review.

Saved sources:

- `screeferret`: `bdb4362fff88ce62`
- `stoneibex`: `8d86deca63130dc7`
- `slateraven`: `b5ee4823749d24b8`
- `ridgeadder`: `ee0aad6c47c28524`
- `cairnbehemoth`: `33cf43446bfaa37f`
- `whitebarktitan`: `1f72f0ab429a96ea`
- `stormcondor`: `d27f0e32a1630344`
