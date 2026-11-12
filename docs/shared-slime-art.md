# Shared and seasonal enemy art

Private candidate `feat/shared-slime-art`, worktree
`/media/raid/valhallasc-data/shared-slime-work`, based on main `c9f9df62`.
Candidate Beta 1.43.1 needs version reconciliation with other staged candidates
at integration. Live artwork is unchanged. The enemy-art backlog requires the
owner to see the pictures and approve deployment.

All six event guardians needed revision: their original death scripts compressed
rigid bodies vertically, their attacks were small arm movements, and Bloomwarden
and Birchcrown had nearly identical bodies and faces. Firelord previously borrowed
Eldmarr. The audit and art approach were reviewed by an advisor before building.

Seven independent native PixelFlow sources contain 238 editable frames. Each has
five clips, counts 6/8/8/4/8, original rates 6/10/12/10/8 fps, and a 176×172 frame
at anchor (64,164). The shared manifest fallback remains 96×96 at (48,90).
Idle dimensions stay within two pixels of the original art; the extra canvas
accommodates attacks and rigid falls. Grounded frames retain transparent borders.
All seven have different faces, silhouettes and attacks, without blush.

| Kind | Identity and attack | Death |
| --- | --- | --- |
| `ember_firelord` | Broad charcoal basalt giant, horned furnace skull and burning fissures; pulls back and hammers forward with a flaming fist | Knees buckle, stone torso slumps and heavy skull rolls aside; fire gutters out, cooled basalt remains |
| `hollow_rider` | Headless armoured rider on a charcoal nightmare, held pumpkin and crescent scythe; broad backswing and forward scythe sweep | Horse folds four jointed legs and lowers its neck; rider slumps, pumpkin lands and mane/tail fire fades |
| `grinch` | Green fur, long muzzle, sly angled eyes, red cap/coat and gathered cloth sack containing a ribboned parcel; swings sack in a wide arc | Knees fold and body falls sideways; hat and full-volume sack follow |
| `bloomwarden` | Moss body, decorated egg shoulder plates, petal crown and split seed eyes; raises flower staff and drives it forward | Branch legs buckle, egg plates crack and shed pieces, petals fall and staff topples |
| `birchcrown` | Tall warm ivory birch trunk, black scars, asymmetric knot eyes and leafy branch crown; sweeps a two-handed branch staff | Trunk fractures and tips with solid branch sections; leaves fall |
| `briarheart` | Asymmetric layered rose, thorn slits, hooked claws and a notched heart seed; draws thorn arms back then rakes forward | Wooden limbs topple, petals separate and heart darkens |
| `starrocketeer` | Brass goggles, curled pale moustache, pointed cap, twin red rockets and a star wand; aims back and thrusts with an attached flare | Knees buckle; intact body and rocket pack fall sideways and fuses extinguish |

Names, ten cross identities/tints, seasonal calendars, encounter rules, stats,
loot, map, server and music are unchanged. The first browser fixture used an old
keeper coordinate; it now reads the shaped world's actual NPC position.

## Pipeline and integration

`shared_slime_models.py` authors the connected anatomy and props. A socket
transform keeps each staff/scythe attached to its wrist through the swing.
Separate basalt, birch and sack ramps distinguish stone, bark and cloth.

```sh
python3 scripts/shared_slime_redraw.py preview
python3 scripts/shared_slime_redraw.py build
python3 scripts/shared_slime_redraw.py export
python3 scripts/shared_slime_redraw.py verify
python3 scripts/shared_slime_review.py
python3 tests/shared-materials.py
python3 tests/shared-rollback.py
python3 tests/shared-browser-coverage.py
```

Saved IDs: `scripts/shared_slime_sources.txt`; indexed source frames:
`scripts/shared_slime_*_raw.npz`. Build preserves registered editor sources.
`refresh KIND...` explicitly overwrites only named candidate frames; export reads
saved editor frames so manual edits survive. The six legacy event makers delegate
to this pipeline and refuse destructive `update` / `--replace` invocations.

Only the owned kind's `sprites`, `tops` and `kindFrames` entries change in each
manifest. Cathedral also has an `atlases.ember_firelord` filename override;
`field.js` respects it before the legacy `artFrom` borrower. The original
`cathedral_cf_eldmarr.png` and all other Cathedral kinds stay intact. Generic bank
loading now applies the manifest's health-bar tops to seasonal enemy definitions,
including a bank preloaded before the enemy enters the view.

**When combining with the pending Forge candidate, integrate Forge first and run
this candidate's export last.** Forge's current exporter still considers Firelord
an Eldmarr borrower and can overwrite its source/top/frame metadata. Future Forge
exports must skip that alias when `atlases.ember_firelord` exists, or rerun
`shared_slime_redraw.py export` afterwards. Do not take a whole stale Cathedral
manifest from either branch. Keep the independent Firelord slice and every other
candidate's owned records. Reconcile the candidate version and release notes.

## Review and verification

Local review artifacts are in `test-results/shared-slime/`:

- `shared-roster.png`: seven new idle designs.
- `shared-before-after.png`: originals beside idle, wind-up, strike, recovery and deaths.
- `shared-attack.gif`, `shared-die.gif`: animation previews.
- `shared-<kind>-frames.png`: every frame, checked visually for all seven kinds.
- `baseline-game.png`, `firelord-game.png`: original/candidate Firelord beside the real hero.
- `rendered-<kind>.png`: production compositor pose boards.

`tests/shared-slime-art.cjs` runs through the bounded browser wrapper with real
sprites, one 960×600 page and the existing main debug test binary. It summons the
real Firelord through the keeper quest and cross, then exercises the production
bank loaders, frame lookup, animation state machine, tint, compositor, click
bounds and portraits for each kind. It checks eight distinct attacks/deaths,
substantial attack reach, grounded frames and browser-decoded frame hashes against
verified editor export. Seasonal pose boards are renderer fixtures; event ritual
and combat timing tests are outside this artwork change.

The first browser pass caught weak Rider/Grinch reach; both swings were widened
without increasing idle size. Their feet stay grounded during attacks. The horse's
charcoal material separates it from the rider's purple armour. The final browser
coverage is reconciled with final atlas pixels, so later source refreshes cannot
silently invalidate an earlier result. No full suites or encounter grinding.

All seven kinds pass the focused browser assertions (12 per kind, plus shared
loader/identity/error checks), 76 material/preservation checks and seven guarded
rollback checks. All 238 editor/export frames agree. Swedish catalog validation,
release-notes validation and changed Python/JavaScript syntax checks pass.

The old Grinch atlas and an idle-as-death Rider atlas both fail the browser
checks as intended. Mutation pose boards use a separate prefix so they cannot
overwrite positive review captures.

Uploaded at the owner's request on 2026-11-12: **13 FileDrop PNG/GIF files,
2,311,559 bytes**, with SHA-256, byte length, MIME metadata, dimensions and
animation counts verified. The package contains the roster, before/after board,
attack/death GIFs, seven complete frame sheets and original/candidate Firelord
game screenshots. Receipt: `test-results/shared-slime/filedrop-receipt.json`.
`shared_slime_review.py upload` is an explicit upload command; the default
`review` command remains local. Deployment awaits picture approval.

- [Roster](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-shared-roster.png)
- [Before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-shared-before-after.png)
- [Attacks](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-shared-attacks.gif)
- [Deaths](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-shared-deaths.gif)

## Rollback

Fifteen original files, SHA-256 hashes, byte lengths and old PixelFlow IDs are kept
outside the live checkout in
`/media/raid/valhallasc-data/shared-slime-original-20261112`.

```sh
python3 scripts/rollback_shared_art.py --root /home/serveperry/webserver/www/Valhallasc --apply
```

Without `--apply`, all guards run and nothing is written. Rollback restores the
seven owned manifest slices, six event atlases and original renderer; it removes
the independent Firelord atlas, while preserving other Cathedral candidates.
All backup integrity and candidate checks finish before any writes. A later
unrelated `field.js` edit is refused and needs a manually integrated reverse
renderer patch. The original Eldmarr borrower is backed up but never modified.
Version/release notes and Swedish catalog rollback are separate from art rollback.
