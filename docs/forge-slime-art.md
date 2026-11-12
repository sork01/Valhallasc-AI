# The Chained Forge enemy artwork (private candidate)

Owner accepted all enemy sprites on 2026-11-12. Integrated for Beta 1.44.0; see
[the combined release](enemy-sprites-release.md). The private-candidate status
below records the original review stage and is superseded by that approval.

Fifteen raid kinds are remade in the Greenmeadow shading style on
`feat/forge-slime-art`, worktree `/media/raid/valhallasc-data/forge-slime-work`.
Candidate Beta 1.43.1 is private. The backlog requires picture approval before
deployment. Reconcile the version and shared manifest slices at integration.

Native editable PixelFlow sources contain 510 frames. Every kind uses 176×172
at anchor (72,164); the shared Cathedral fallback stays 96×96 at (48,90).
Original clip counts 6/8/8/4/8 and rates 6/10/12/10/8 fps are preserved.
Each attack has a wind-up, strike and recovery; each death has eight distinct
poses appropriate to its material. Rigid parts rotate at their joints without
squashing. The Channeler hovers and its crucible lands as its flame gutters out.
The numbered ingot's attack clip is a shield-warning pulse: its stationary,
zero-damage mechanics are unchanged. No server, map, balance or music changes.

| Kind | Identity, attack and death |
| --- | --- |
| `cf_brute` | Furnace-ribbed iron brute, chimney, narrow angry sockets and riveted hammer. Raises and slams hammer; joints buckle, furnace shuts down and rigid body tips over. |
| `cf_crawler` | Six-legged iron crawler with three vents, six furnace eyes and jointed mouthparts. Rears and spits from its vents; legs curl over a tipped carapace and vents extinguish. |
| `cf_caster` | Suspended crucible, articulated support arms and a severe flame face. Draws jets up then casts fire; flame gutters out and cracked empty crucible lands. |
| `cf_sentry` | Obsidian helmet, cyan visor and faceted shield. Raises and thrusts shield; knees buckle and the intact armour lands sideways. |
| `cf_kettil` | Crowned, scarred chain bearer with iron shoulder plates, shackles and dangling links. Draws a chain weight back and lashes it forward; armoured body falls and chain follows the hand. |
| `cf_ysolt` | Bellowsmaid with stern masked face, accordion bellows and cyan wand. Expands then compresses bellows and casts from attached nozzles; arms fold and bellows fall with her. |
| `cf_hallgrim` | Broad anvil shoulders, goggles, braided beard and heavy hammer. Raises and slams hammer in an arc; knees fold and smith falls sideways with the tool. |
| `cf_sigrun` | Mould crown, furnace apron, heavy scowl and pouring ladle. Raises and tips ladle; molten stream recovers into its bowl, then extinguishes as she falls. |
| `cf_dagfinn` | Two shoulder valve wheels, long beard and articulated tongs. Opens tongs on wind-up then clamps forward; body and tongs fall sideways, wheels stay rigid. |
| `cf_thorbjorg` | Dark hair, three burning brand cages and a hand-held brand. Raises then drives the brand forward; fire shuts down in the fallen cages. |
| `cf_ragnhild` | Asymmetric iron face mask, organ-pipe collar and sound hammer. Swings hammer to send a violet sound pulse; pipes fall with the body and shut down. |
| `cf_orm` | Round cooling tank, cyan sight glasses, respirator and water vessel. Raises then throws from vessel; jointed body falls, tank retains its volume and glass darkens. |
| `cf_hildr` | White-cyan mirror armour, severe slit face, seven mirror-halo facets and broken chains. Thrusts mirror plate; halo fractures into rigid fallen plates beside the body. |
| `cf_eldmarr` | Basalt giant, nine-link broken crown, furnace ribs, flame beard, chains and cleaver. Swings the cleaver in an arc; fire dies and heavy stone/iron joints slump sideways. |
| `cf_ingot` | Solid metal numbered target with vented fire panel. Harmless warning pulse; two rigid halves tip apart and cool, scattering small fragments. |

Idle opaque dimensions closely match the originals, within two source pixels
in each dimension. Existing raid pack/boss display scaling remains intact.
No common round-eye/blush face: each kind keeps its own eyes, mask, mouth,
headwear and distinctive attached equipment. Crown bands overlap the skull.

## Sources and pipeline

Models: `scripts/forge_slime_models.py`. Saved IDs:
`scripts/forge_slime_sources.txt`. Raw indexed frames:
`scripts/forge_slime_cf_*_raw.npz`.

```sh
python3 scripts/forge_slime_redraw.py preview
python3 scripts/forge_slime_redraw.py build
python3 scripts/forge_slime_redraw.py export
python3 scripts/forge_slime_redraw.py verify
python3 tests/forge-materials.py
python3 tests/forge-rollback.py
python3 scripts/forge_slime_review.py review
python3 scripts/forge_slime_review.py upload
```

Build preserves registered sources. `refresh KIND...` explicitly overwrites only
named candidate editor frames. Export reads saved editor frames and derives tops,
so manual editor changes survive. Both original Forge makers delegate module and
CLI operations; destructive `--replace` is refused. Older encounter UI atlas
checks use `Field.frameOf` for their own per-kind geometry.

Export merges these fifteen native kinds and the ten Empty Seat aliases borrowing
Kettil/Eldmarr. Their source IDs, tops and geometry follow the new sources. The existing shared
Firelord also borrows Eldmarr; its alias follows that source, preserving its tint
and mechanics. Its own independent remake remains the next shared/event task. The
existing Empty Seat memory actor already uses `Field.frameOf(cf_eldmarr)`.
All 120 unrelated Cathedral records, shared clip metadata and 120 unrelated
native PNG hashes are preserved. Merge only this owned manifest slice when
integrating alongside other pending candidates.

## Rollback

Sixteen originals, byte lengths, SHA-256 hashes, PNG dimensions and old editor
IDs are backed up outside the live checkout at
`/media/raid/valhallasc-data/forge-slime-original-20261111`.

```sh
python3 scripts/rollback_forge_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for a no-write dry run. All backup and unrelated-manifest guards
run before writes. Disposable-copy verification proves exact restoration of all
sixteen files, dry-run immutability, corrupt-backup refusal and unrelated-manifest
refusal without writes. Receipt: `test-results/forge-slime/rollback-proof.json`.
Both generations of editable sources remain available. Version/release notes are
separate from artwork rollback.

## Review delivery and verification

`tests/forge-slime-art.cjs` runs in bounded batches selected with
`FORGE_ART_KINDS`. It covers actual source lookup, per-kind geometry, 34 frames,
clip timing, eight attack/death poses, wind-up/strike/recovery, grounding/hover,
health-bar tops, full production portraits, real game screenshots, and Empty Seat
borrowed geometry/sources/portraits. It also compares the actual animation state
machine and production compositor pixels against every attack/death source cell.

All fifteen kinds have bounded real-client coverage. The four packs pass 81
checks and bosses five through eight pass 85, including exact compositor pixels.
The remaining bosses were checked together; after the ladle, mirror and armour
corrections their individual checks pass. The final ingot/Firelord correction
passes 47 checks (`driver-2oWWBd`). An original Brute atlas is rejected by the
production frame assertion. All fifteen idle-as-corpse controls are rejected;
both makers refuse destructive replacement. No full encounter suite was run.

85 material/preservation checks cover fire shutdown, retained iron and glass,
folded legs, fallen bodies, the landed crucible, fractured mirror halo and split
ingot. A rigid cooling tank stays bulky when fallen; tests preserve that volume.
Review corrections restore Kettil's iron armour, detach Hildr's mirror halo into
fallen plates, make the ingot's halves topple, and retract Sigrun's pouring stream
during recovery. No encounter timing, fight grinding or full suite runs.

65 review PNG/GIFs (10,230,948 bytes) are uploaded and verified. They include before/after rosters, attack and death comparisons,
and each kind's complete sheet and animations. Upload verifies SHA-256, byte
lengths, MIME metadata, dimensions and animation counts; receipt is
`test-results/forge-slime/filedrop-receipt.json`.

- [Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-forge-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-forge-attacks-before-after.png)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-forge-deaths-before-after.gif)

Await picture approval before deployment. Next enemy-art group: shared/event
kinds (`SHARED-SLIME-ART`).
