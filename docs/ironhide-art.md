# Greenmeadow Ironhide: rigid-shell artwork candidate

All four MEADOW-SLIME TODO deliverables are privately complete as **Beta 1.39.1**
in `/media/raid/valhallasc-data/meadow-slime-work`, branch `feat/meadow-slime-art`,
based on main `9dea2cc`. Local/uncommitted; not pushed, merged or deployed.
TODO.md requires picture review and owner approval before public replacement.

Ironhide keeps the slimes' round glossy shading, large white eyes, highlights,
blush and chunky proportions, together with its steel-blue shell, bronze horn
and six legs. Shell movement uses translation and rigid rotation: idle weight
shifts, jointed walking, horn lunge and recoil. Death shows angular shell cracks,
buckling knees, crossed eyes, a forward tip and small metal chips. The shell
stays solid, with no squash/stretch or puddle death. Eight distinct death frames.
The five Greenmeadow slime kinds and other zones' art remain unchanged.

## Sources and contract

New native PixelFlow source **d1ab641330d34105**,
`valhallasc_meadow_ironhide_rigid_all`. Previous **399849edffa3ab6f** and earlier
original **a3f8837048d1098c** remain saved. IDs: `scripts/meadow_slime_sources.txt`.
New raw indexed frames: `scripts/meadow_slime_raw.npz`; historical
`scripts/ironhide_raw.npz` remains unchanged.

`python3 scripts/make_ironhide_sprites.py preview | build | export`.
Build uses a separate name prefix, retains existing sources and refuses
`--replace`. Export reads saved editor frames, preserving edits, and derives
health-bar `tops.beetle` (currently 36); the beetle loader now uses it.

Same kind ID/file paths,72×64 frame,anchor(36,60),576×320atlas,34frames:
6idle@6fps,8walk@10,8attack@12,4hurt@10,8die@8.
New atlas SHA256: `49c897b97ab646b3dc0a63de4cc156a12062715d942837395b36ba6c5cda881b`.
Old atlas replaced only in the candidate, without duplicate old live assets.
No stats/timings/maps/rewards/zone IDs/server/DB changes; no rebuild or restart.

## Rollback

External backup `/media/raid/valhallasc-data/meadow-slime-original-20261103`
contains exact previous `client/assets/ironhide.png` and `ironhide.txt`, plus
hashes and previous source IDs in `manifest.txt`. Old atlas SHA256:
`a91ecac9df2dbc96700f9ae2c95ec90b2248a6bbebbebdc5b22039bbb7921d8f`.

One command to restore old art when wanted:

```sh
python3 /media/raid/valhallasc-data/meadow-slime-work/scripts/rollback_meadow_art.py --target /home/serveperry/webserver/www/Valhallasc --apply
```

Omit `--apply` for dry run. Validates both backups before writing, atomically
replaces each art file and verifies both restored hashes. It leaves release
labels/notes alone; a production rollback needs matching notes and a new version.
Restoration on disposable copies and corrupt-backup refusal without changes pass.

## Focused verification

**16 distinct bounded real-art browser checks pass**: dimensions/anchor,
34 nonempty unclipped frames, saved source ID, five animating clips, eye whites/
gloss, production portrait, eight distinct death poses, retained body height/area
and steel-shell pixels during death, derived health top, authoritative Greenmeadow
beetle top and no browser errors. Final artifacts: `test-results/driver-OwqsCG`
(gallery, portrait, slime reference, desktop/landscape-phone gameplay and numerical
report). Test uses a tracked source registry, with no ignored-proof dependency.

All **34 saved-editor/export frames match**. Evidence:
`test-results/meadow-slime/editor-export-proof.json` and `validation.json`.
Python/JS syntax, Swedish generation/check, release-note guard and diff checks
pass. No full suites, combat grinding, fight tests or balance sweeps.

```sh
PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules:/home/serveperry/webserver/www/dybase2/node_modules VALHALLA_BINARY=/home/serveperry/webserver/www/Valhallasc/target/release/valhalla-server bash scripts/test-touch-bounded.sh tests/ironhide-slime-art.cjs
python3 scripts/meadow_slime_review.py review
python3 scripts/meadow_slime_review.py verify
```

## Owner review

Seven FileDrop outputs uploaded; destination SHA256,size,dimensions,original
filename and MIME metadata verified. Receipt:
`test-results/meadow-slime/filedrop-receipt.json`.

- `valhallasc-meadow-before.png`
- `valhallasc-meadow-after.png`
- `valhallasc-meadow-before-after.png`
- `valhallasc-meadow-frames.png`
- `valhallasc-meadow-death-frames.png`
- `valhallasc-meadow-animations.gif`
- `valhallasc-meadow-death-before-after.gif`

Before/after uses equal scales. Animations use original clip rates and hold the
final death pose briefly. `meadow_slime_review.py upload` is separate from
review/verify and uploads this set only when requested.

Live art hashes remain identical to the backup. Both this and the separate Crags
candidate label themselves1.39.1: reconcile current version/notes/Swedish keep label
when combining approved candidates. Main TODO is maintained in the shared checkout;
do not overwrite it with this worktree's older snapshot. Next zone is Rimeveil.
