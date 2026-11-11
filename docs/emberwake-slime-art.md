# Emberwake Caldera enemy artwork (private candidate)

Seven enemies are redrawn on `feat/emberwake-slime-art` in
`/media/raid/valhallasc-data/emberwake-slime-work`. Live artwork stays unchanged.
The enemy-art backlog requires picture approval before deployment. Candidate
Beta 1.43.1 needs version reconciliation at integration.

Seven native PixelFlow sources contain 238 editable frames. Every kind has
its own fierce face, eight distinct attack poses and eight fitting death poses.
Original idle/walk/attack/hurt/die rates of 6/10/12/10/8 fps and counts of
6/8/8/4/8 remain intact. Every kind uses 176×172 at anchor (88,164); shared
Cathedral fallback remains 96×96 at (48,90). No server, map, balance or encounter
changes. No server build or restart.

| Kind | Saved source | Anatomy, attack and death |
| --- | --- | --- |
| `ew_ashback` | `2bbd1d60a27e12d7` | Long molten salamander, tapered tail, rock back plates and a narrow lizard socket. Coils back then lunges with its muzzle; four legs fold, torso settles and molten skin cools to stone. |
| `ew_glasswing` | `122a4fe7c7d09fd0` | Six-legged glass moth, faceted compound eyes, antennae and rigid veined wing panels. Wings draw back then cast cinder shards; panels rotate at their roots, crack, fold and land from hover. |
| `ew_slagjaw` | `cb0e594ac0aea3e2` | Squat plated burrower, interlocking dorsal blades, wedge snout and recessed reptilian eye. Lower jaw opens on its visible rear hinge then bites; legs tuck beneath the plated torso, jaw closes and fissures darken. |
| `ew_cinderhorn` | `c16125cb432f4de7` | Tall-shouldered stone ram with spiral iron horns, rectangular pupil and beard. Raises its head then drives its horns down and forward; legs fold, belly settles and exposed fire cools. |
| `ew_chainmaw` | `79c86c8e75383576` | Broad shackled beast with square muzzle, one scarred eye and attached jaw bridle. Opens and raises its jaws then slams; legs fold, molten seams cool and the linked bridle follows the jaw into the corpse. |
| `ew_bellows` | `7c912134420335fa` | Yrsa has a severe human scowl, iron crown, burgundy coat and accordion forearms. Bellows expand on wind-up, compress into a two-nozzle flame cast, then recover; knees buckle, arms fold and flames extinguish. |
| `ew_crown` | `f2c84ae0421f03c4` | Charcoal humanoid with asymmetric fissure eyes, furnace mouth, huge fists and a separate broken crown. Fists rise and hammer down; stone limbs buckle, the core cools and the crown drops to the ground beside the torso. |

Original/new idle opaque dimensions: Ashback 72×48 / 72×49, Glasswing 73×55 /
75×55, Slagjaw 70×47 / 69×48, Cinderhorn 72×59 / 72×61, Chainmaw 69×51 /
70×51, Yrsa 74×75 / 73×75, Ember 76×79 / 77×79. Scale was chosen after original
in-game captures and before creating sources; existing elite scaling stays intact.
Grounded frames rest on the anchor; Glasswing hovers at least 12 pixels and
lands monotonically on death. Raw canvas clipping is checked before grounding.

## Pipeline

```sh
python3 scripts/emberwake_slime_redraw.py preview
python3 scripts/emberwake_slime_redraw.py build
python3 scripts/emberwake_slime_redraw.py export
python3 scripts/make_emberwake_sprites.py verify
python3 tests/emberwake-materials.py
python3 scripts/emberwake_slime_review.py review
```

Models: `scripts/emberwake_slime_models.py`. IDs: `emberwake_slime_sources.txt`.
Build preserves registered sources; `refresh KIND...` overwrites only named
candidate editor frames. Export reads saved editor frames and derives health-bar
tops, preserving manual edits. `make_emberwake_sprites.py` delegates module/CLI
operations and refuses `--replace`. The old `emberwake_sheets.py` keeps its sheet
and cast filenames but now reads declared per-kind frames.

Export merges only these seven Cathedral kinds. All other 139 kind records,
shared clip metadata and 128 unrelated native PNG hashes are preserved.
Integrate only this manifest slice alongside other candidates, and reconcile
version/notes before release.

## Rollback

Eight originals, hashes, byte lengths, dimensions and old PixelFlow IDs are at
`/media/raid/valhallasc-data/emberwake-slime-original-20261111`.

```sh
python3 scripts/rollback_emberwake_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for a no-write dry run. All backup and unrelated-manifest guards
run before writes. Disposable-copy checks prove exact restoration of all eight
files, dry-run immutability, corrupt-backup refusal and unrelated-manifest refusal
without writes. Receipt: `test-results/emberwake-slime/rollback-proof.json`.
Both generations of saved editor sources remain available. Version/release notes
are separate from artwork rollback.

## Focused verification and review

All 238 saved editor frames match the exported atlases. Bounded real-client
batches pass 81 checks for the four ordinary kinds (`driver-mktvYV`) and 62
for the elites (`driver-YvNtAv`); Ember's final crown-grounding correction passes
24 more (`driver-85tTMM`). Checks cover actual source/frame lookup, portraits,
clip rates, substantive wind-up/strike/recovery, all eight attack/death poses,
borders, ground/hover and health-bar tops. An original Ashback atlas is rejected
at the production per-kind frame contract. Select kinds with `EMBERWAKE_ART_KINDS`.

40 material/preservation assertions pass. All seven idle-as-corpse controls are
rejected at fire shutdown. Material checks also require solid retained glass,
stone and iron, folded supporting torsos, a sideways fallen Yrsa and a landed
broken crown. Rollback guards, destructive-rebuild refusal, Python/JS syntax,
Swedish generation/check and release-note validation pass. Existing
`emberwake-ui.cjs` atlas assertions now use `Field.frameOf`; its older encounter,
travel, map and music checks were outside this artwork task.

All 34-frame sheets and real-client captures were inspected. Advisor review
prompted six moth legs, clearer glass fractures, torso-supported quadruped corpses
and folded accordion arms. A material check caught Ember's crown above the ground;
it now settles beside the body. Review pictures use anchored old/new cells at
the same scale.

33 review PNG/GIFs include rosters, before/after attacks and deaths, and each
kind's complete sheet and animations. `emberwake_slime_review.py upload` checks
SHA-256, byte lengths, MIME metadata, dimensions and animation counts.
All 33 files / 4,592,622 bytes are uploaded and verified. Receipt:
`test-results/emberwake-slime/filedrop-receipt.json`.

- [Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-emberwake-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-emberwake-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-emberwake-deaths-before-after.gif)

Awaiting picture approval. Next enemy-art group: The Chained Forge
(`FORGE-SLIME-ART`).
