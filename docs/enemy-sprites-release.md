# Accepted enemy sprite release — Beta 1.44.0

The owner approved **all enemy sprites** on 2026-11-12. This supersedes the
approval-pending wording in the original private-candidate notes. Earlier enemy
batches were already deployed; this integrates the remaining 21 batches, with
153 native PixelFlow atlases (5,202 editable frames) and ten Empty Seat borrowers.
The existing Greenmeadow slimes remain the style reference. Separately authored
zone elites and all NPC entries remain intact.

## Integration

Prepared on `release/enemy-sprites-20261112` from main `c1300c67`, outside the live
checkout. Source files and accepted PNGs are consolidated from the exact refs
below; stale candidate version numbers and backlog snapshots are excluded.
Shared manifests apply only changed records, preserving other batches and NPCs.
Forge aliases are applied before Shared's independent Firelord source, top, frame
and atlas override. Forge's exporter now skips aliases with independent atlases.
Both shared dungeon makers dispatch both native casts; `dungeon_cel.py` delegates
the remade dungeons before its legacy deletion path.

This is a client-only feature release. The map, server executable, character data,
encounter rules, loot, music and timings do not change. Displayed version,
English release notes, Swedish version keep-list and generated Swedish catalog
are updated together. The original candidate docs retain their review history.

| Batch | Source branch | Accepted source head |
| --- | --- | --- |
| frostwake | `feat/frostwake-slime-art` | `079ca5f1a4a5` |
| cairn | `feat/cairn-slime-art` | `0112c9f9b300` |
| yearwheel | `feat/yearwheel-slime-art` | `bcf3f084a1b1` |
| eye | `feat/eye-slime-art` | `69d6760cba7d` |
| elder | `feat/elder-slime-art` | `c8a7009c21ac` |
| pavilion | `feat/pavilion-slime-art` | `d8a21eb20cf9` |
| raincrown | `feat/raincrown-slime-art` | `871d7914ad64` |
| seedvault | `feat/seedvault-slime-art` | `23de73330a8a` |
| astrolabe | `feat/astrolabe-slime-art` | `01a21dce698b` |
| thunderheart | `feat/thunderheart-slime-art` | `d1e484813df2` |
| blooming | `feat/blooming-slime-art` | `dc381f12d618` |
| crucible | `feat/crucible-slime-art` | `1ba09965a3e7` |
| amber | `feat/amber-slime-art` | `7e98f75a8900` |
| silent-solstice | `feat/silent-solstice-slime-art` | `f84b4f91c8c6` |
| nornroot | `feat/nornroot-slime-art` | `e79579d3acaa` |
| span | `feat/span-slime-art` | `079bd31043d7` |
| longship | `feat/longship-slime-art` | `a79f9e49fb9e` |
| foundry | `feat/foundry-slime-art` | `1399945429ec` |
| emberwake | `feat/emberwake-slime-art` | `78c1d0c609f2` |
| forge | `feat/forge-slime-art` | `1c2901b87465` |
| shared | `feat/shared-slime-art` | `d9c0b4b30f8e` |

## Verification

- All 153 accepted PNG byte hashes and 447 changed manifest values match their
  source candidates; all other manifest values and client assets are preserved.
- `tests/enemy-sprites-integration.cjs` exercises the existing production loader,
  frame lookup, portrait and compositor with real assets in bounded Chromium.
  It exposes the private loader only in the test response, without changing its
  body, and closes each page after twelve kinds to bound decoded-image memory.
  All 153 kinds pass source, actual fetched PNG hash, frame/anchor, health-bar
  top, portrait and every attack/death cell checks (2,448 compositor renders).
  The initial run passed 144 kinds before a reference-tint mismatch at Firelord;
  the test now uses the real Greenmeadow cross tint and focused remaining-kind
  checks pass. It does not run encounters.
- Mocked native pipeline checks cover 16 dungeon routes, destructive-replacement
  refusals and both casts in both shared makers. No editor mutation is performed.
- Changed Python/JavaScript syntax, release-note guard and Swedish build pass.
  `tests/swedish-catalog.py` has the same four proper-name failures on unchanged
  main and this release; that pre-existing result is recorded separately.
- Full client rollback passes dry run, exact restoration, corrupt-backup refusal
  and refusal of later client edits on disposable RAID copies.

Receipts: `test-results/enemy-sprites/` in the release checkout. Original material,
mutation and saved-editor proofs remain in each source worktree; the accepted
PNGs are copied byte-for-byte, so those artwork checks are not repeated.

## Rollback

Immutable pre-release files and hashes are in
`/media/raid/valhallasc-data/enemy-sprites-release-original-20261112`.

```sh
python3 scripts/rollback_enemy_sprites_release.py --apply
```

Omit `--apply` for a no-write dry run. All changed client files, including the
version and Swedish catalog, are checked before any writes. Originals are restored
and newly introduced PNGs are removed. Later client changes and corrupted backup
files are refused. The existing per-batch backups and old PixelFlow IDs remain.
After a rollback, reconcile the tracked client changes with git before releasing
further work.

## Deployment

Deployed 2026-11-12 by fast-forwarding source `9b6c48e9` into the live main
checkout. All 167 changed client files and 76 preserved asset checks match their
public SHA-256 hashes. Public and bridge health report OK. Server PID 3337765 and
the executable hash are unchanged; no service restart or public test characters.
The public page displays Beta 1.44.0. Receipt:
`test-results/enemy-sprites/public-release.json` in the release worktree.

The planned enemy-sprite remake queue is now complete and released. The owner
has accepted all artwork; historical candidate notes do not require new approval.
