# Frostwake Shelf enemy art candidate

Built privately on `feat/frostwake-slime-art`, worktree `/media/raid/valhallasc-data/frostwake-slime-work`. This is a review candidate, not deployed. Seven new native editable PixelFlow sources preserve the existing enemy IDs, stats and animation timings. The six NPCs sharing `frostwake.txt` retain their entries and atlases.

| Creature | Attack | Death |
|---|---|---|
| Snow Hare | ears draw back, hind legs coil, teeth and forefeet reach forward | legs fold and the body drops onto its side, ears tilt down |
| Ice Otter | crouch and a long toothed lunge | legs fold under the belly; body and tail settle flat |
| Frost Heron | wings rise and neck retracts, then beak stabs down | stilt legs give way, wing and long neck fall sideways |
| Glacier Crab | ice claws cock high, then slam down | shell cracks, legs curl and the rigid shell rolls onto its back |
| Bell Mammoth | head and trunk draw back, then tusks thrust forward | pillar legs buckle, head and bell drop with the body |
| Aurora Manta | aurora wings rise and sweep down | fins fold and the body sinks to the ground |
| Crevasse Leviathan | coils back and opens its toothed jaw for a long bite | coiled body tips sideways and the head topples forward |

Each source has 34 frames: idle 6, walk 8, attack 8, hurt 4, die 8, all 10 fps. Frames are 168×180, anchor (84,170), within PixelFlow's 30,840 pixel limit. A separate drawing origin leaves space below the raw pose for rotation; raw edges are checked before the grounding translation. Every grounded frame rests on the anchor row; the manta hovers while alive and settles on it at the end of death. The exporter reads saved editor cels, writes `kindFrames` and derives health-bar tops from idle bounds. NPC fallback remains 96×96 at (48,90).

Commands:

```sh
python3 scripts/frostwake_slime_redraw.py preview
python3 scripts/frostwake_slime_redraw.py build
python3 scripts/frostwake_slime_redraw.py refresh KIND
python3 scripts/frostwake_slime_redraw.py export
python3 scripts/frostwake_slime_redraw.py verify
python3 scripts/frostwake_slime_review.py review
python3 scripts/frostwake_slime_review.py verify
python3 scripts/frostwake_slime_review.py upload
```

`build` preserves registered sources and refuses `--replace`. The original generator and original cel drawing code are retained; regeneration of the new art uses this new entry point.

Rollback keeps the previous seven atlases, shared manifest, original PixelFlow IDs and hashes at `/media/raid/valhallasc-data/frostwake-slime-original-20261111`. All backup hashes and unrelated manifest data are checked before any file is written:

```sh
python3 scripts/rollback_frostwake_art.py --target /path/to/checkout --apply
```

Validation receipts, previews and before/after animation GIFs live under `test-results/frostwake-slime`. The bounded browser check is `tests/frostwake-slime-art.cjs`; use the main checkout's test-profile binary and node modules. `MUTATE_KIND=snowhare MUTATE_PNG=/media/raid/valhallasc-data/frostwake-slime-original-20261111/client/assets/frostwake_snowhare.png FROSTWAKE_ART_KINDS=snowhare` serves old art and must fail.

Deployment requires the owner's picture approval, as specified in TODO.md. Reconcile the version against the current live label at release time; no candidate version bump or server build is needed.

## Verification (2026-11-11)

- 238 saved PixelFlow editor frames exported, with per-frame bounds and hashes in `editor-export-proof.json`.
- 140 bounded real-art browser checks pass: all seven sources loaded in their real zone; five clips animate; eight distinct attack and death frames each; substantial wind-up and strike silhouettes; recovery; grounding/hover; health-bar tops and production portraits. Browser evidence: `test-results/driver-ixp3Wp`.
- Serving the old Snow Hare atlas fails the declared production-frame assertion, as required.
- Eight-file rollback restores exact original hashes. Corrupt backup and changed NPC metadata are refused before any writes. All six NPC atlases and shared metadata remain unchanged; live assets match the original backup.
- 33 before/after PNG/GIF files uploaded to Sork's FileDrop. Hashes, metadata, dimensions and sizes verified; `test-results/frostwake-slime/filedrop-receipt.json`.
- The positive check used `SOFT_CHECKS=1` to collect any remaining failures in one run; it reported zero failures and exited successfully. No balance runs or broad test suites.

The seven sources are:

- `snowhare`: `c614901c29f613b5`
- `iceotter`: `3c56f1a0bd323154`
- `frostheron`: `aaddb10193b578cf`
- `glaciercrab`: `97c834163abc0cc1`
- `bellmammoth`: `25d9abfd2fb25faf`
- `auroramanta`: `a21fd2af6c9d492f`
- `crevasseleviathan`: `41b769adc2366b00`
