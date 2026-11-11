# Black Hour Foundry enemy artwork (private candidate)

Built 2026-11-11 on `feat/foundry-slime-art`, worktree
`/media/raid/valhallasc-data/foundry-slime-work`. Live art is unchanged.
Candidate Beta 1.43.1 needs reconciliation at integration. The enemy-art backlog
requires the owner's picture approval before deployment.

Six native PixelFlow sources contain 204 editable frames. Every kind has eight
distinct attack and death frames, a separate mean face and articulated metal
parts. Idle/walk/attack/hurt/die retain 6/10/12/10/8 fps and 6/8/8/4/8 frames.
The shared Cathedral fallback remains 96×96 at (48,90). Five kinds use 176×172
at (88,164); Breaker uses 192×160 at (76,152) so its axe sweep fits. Every source
stays within the 1,048,576-cell limit. No server, map, encounter or balance changes.

| Kind | Native source | Anatomy, attack and death |
| --- | --- | --- |
| `null_hauler` | `4fe1c5e26eb58f13` | Ribbed amethyst kiln, three exhaust stacks, four piston legs and a projecting grille jaw. Neck pulls back then crushes forward; legs buckle and the intact kiln tips onto its front, with furnace and jaw current shut off. |
| `null_breaker` | `061f884379fa4fd7` | Broad armoured knight, angular visor, shoulder cogs and suspended chest pendulum. Wrist drives a large pendulum axe from raised wind-up through a sweeping strike; body, axe and counterweight fall sideways. |
| `null_coil` | `86e4febf8ac3bafe` | Six ribbed organ-pipe solenoids attached to an amethyst gear lens with a narrow vertical aperture. Draws back then throws connected current from three terminals; pipes and gear rotate intact, current extinguishes and the hovering array lands. |
| `null_bell` | `1a0c2717bc6fc677` | Cast bell skirt, crown yoke, glaring angled apertures, physical clapper and huge jointed gauntlets. Fists rise and hammer down; legs fold, the bell rolls sideways and the clapper darkens. |
| `null_conductor` | `145fefb59b0e4ffc` | Iona's severe iron mask, gear halo, split rigid skirt and six hinged current arms. Winds up and casts through connected terminals; current shuts off and the entire mechanism settles sideways from its hover. |
| `null_hour` | `42f2c63de6f74f4f` | Toothed clock case, twelve brass hour marks, physical hands, fanged grille, shaded crown and two clock-hand blades. Arms lift and sweep wide, then recover; the case rolls, blades fold inward and the clock stops with its metal intact. |

Original/replacement idle opaque sizes: Hauler 65×71 / 66×70; Breaker 72×61 /
71×60; Coil 60×57 / 59×57; Bell 75×75 / 75×74; Iona 76×61 / 75×61; Hour
80×72 / 79×71. These were chosen after original in-game captures and before
creating the saved sources. Client elite scaling is unchanged. Grounded frames
rest exactly on their anchors; Coil and Iona hover at least 12 pixels and land
monotonically through death. Raw clipping is checked before grounding can hide it.

## Pipeline

```sh
python3 scripts/foundry_slime_redraw.py preview
python3 scripts/foundry_slime_redraw.py build
python3 scripts/foundry_slime_redraw.py export
python3 scripts/make_blackhour_sprites.py verify
python3 tests/foundry-materials.py
python3 scripts/foundry_slime_review.py review
```

Models live in `foundry_slime_models.py`, IDs in `foundry_slime_sources.txt`.
Build preserves registered sources. `refresh KIND...` overwrites only named
candidate editor sources. Export reads saved editor frames so manual edits
survive, then derives health-bar tops. All 140 other Cathedral kind records,
shared clip metadata and 129 unrelated native PNG hashes are preserved.
`make_blackhour_sprites.py` delegates module and CLI operations;
`dungeon_cel.py blackhour` delegates before the legacy deletion path. Both refuse
`--replace`. On integration, merge this six-kind manifest slice and combine all
other candidate dungeon dispatches.

## Rollback

Seven originals, hashes, sizes, dimensions and old PixelFlow IDs are outside the
live tree at `/media/raid/valhallasc-data/foundry-slime-original-20261111`.

```sh
python3 scripts/rollback_foundry_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for a dry run. All guards precede writes. Disposable-copy proof
confirms a dry run writes nothing, apply restores all seven originals, and
corrupt backups and unrelated shared-manifest changes are refused without writes.
Receipt: `test-results/foundry-slime/rollback-and-mutation-proof.json`.
Both generations of saved editor sources remain available. Version/release notes
are separate from the art rollback.

## Focused verification and review

204 saved editor/export frames match. Initial bounded real-client batches pass
62 + 62 assertions. The final Vark/Iona scowl and Hour crown correction passes another 62 checks
(`driver-qpzXYp`); first batch `driver-y8iRpp`, initial bosses `driver-2vTtnS`. Tests cover actual source/frame lookup, substantial attack wind-up,
strike and recovery, clip timings, eight distinct attack/death frames, borders,
grounding/hover, production health-bar tops and target portraits. Select three
kinds with `FOUNDRY_ART_KINDS`. An original Hauler atlas fails the production
frame contract as intended.

44 material/preservation assertions pass. All six idle-as-corpse controls fail
at their required current shutdown check (`MUTATE_MATERIAL=kind`,
`FOUNDRY_MATERIAL_KINDS=kind`). Swedish build/check, release-note guard and Python
and JavaScript syntax checks pass. `blackhour-ui.cjs` now checks per-kind atlas
geometry; its unrelated encounter, equipment, travel and music tests were not run.

All six complete frame sheets and real game captures were inspected. The final
face pass slopes Vark and Iona's brows downward towards the nose to read as
scowls. Hour's crown has separate lit and shaded planes. Review cells allow
the Breaker's full axe reach and preserve every kind's anchor.

29 review PNG/GIFs include old/new rosters, attacks and deaths, plus each kind's
complete frame sheet and animations. FileDrop hashes, byte lengths, MIME metadata,
dimensions and animation frame counts are checked by `foundry_slime_review.py`.
Total: 4,398,975 bytes, all uploaded and verified after the final face pass.
Receipt: `test-results/foundry-slime/filedrop-receipt.json`.

- [Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-foundry-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-foundry-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-foundry-deaths-before-after.gif)

Awaiting picture approval. Next enemy-art group: Emberwake Caldera
(`EMBERWAKE-SLIME-ART`).
