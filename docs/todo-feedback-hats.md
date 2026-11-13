# Quest chime, bag refusals, dungeon loot mail and headgear (Beta 1.47.2)

Implemented from the four owner requests of 2026-11-12 and **deployed 2026-11-12 18:07 CET**
as **Beta 1.47.2**, source `d8e03c21`. The owner explicitly
invoked finish and deploy. Client and server fixes are live; all four TODOs are
complete. The candidate was tested in
`/media/raid/valhallasc-data/todo-feedback-work`, with its own RAID target.

- Restarted with nobody online: PID `183593` → `339798`.
- All **38 character states / 24 guest records** are unchanged; no migration.
- All **18 public client hashes**, the installed/running executable, public and
  bridge health, advancing simulation, SQLite `quick_check`, production
  environment and restart journal checks pass.
- The exact production binary passed a private release probe: refused reward
  says `Insufficient bag space`, no partial rewards, successful claim after
  freeing space, **31 snapshots / 2997 ms**, tick gaps exactly two.
- Backup: `deploy/backups/todo-feedback-release-20261112T170607Z`. Includes previous/new executable, online and stopped
  SQLite backups, all 18 original client files, metadata, private probe,
  restart journal and rollback instructions.
- Running binary SHA-256: `f458c3f10239c89caa689c2ab65e83a46b234f0860ca5b6ccd2b94552271c6cc`.

Binary rollback: stop the service, restore `valhalla-server.prev` to
`target/release/valhalla-server`, start and verify health. Ordinary binary
rollback can retain current saves; restore `stopped/valhalla.sqlite` only when
a complete state rollback is intended. The existing mail table is reused.

## Completion chime

`QuestAudio.play` uses two short sine tones through the existing effects bus,
including its sound switch and effects volume. `Quests.update` calls it beside
the named completion banner, under the existing authoritative transition guard.
Initial progress, identical snapshots and ordinary quest acceptance stay silent.
No song, recorded audio, or new bitmap artwork is created.

## Bag-space refusals

Ground-pickup preflight retains its five-second throttle, fixed pile coordinates
and party eligibility. Its refusal is now an `ok: false` notice, so the existing
red error stack receives it as well as the chat log.

NPC dialogue, shop, bank, trade and mail replies now route bag-space refusals to
the same stack. Dialogue has no general refusal flag, so that path matches only
bag-space refusal text. Nonfatal ordinary errors and refused notices already
use the stack. Existing in-window explanations remain available.

A quest item reward that cannot fit says exactly `Insufficient bag space`.
The existing cloned-character transaction first removes eligible hand-in items,
then checks **all** fixed and chosen item rewards, and commits only if all fit.
Refusal keeps hand-in items, gold, XP, reward items and claimed state intact.
A hand-in that actually frees enough space is still allowed.

## Dungeon roll awards

A human winner with insufficient space in an instance receives the resolved
award in persistent mail escrow instead of as a ground pile. Open-world rolls
and existing mercenary rules retain their existing delivery rules. A recipient
with room still receives the ordinary ground award.

- Each roll has a UUID receipt. System mail uses reserved sender
  `@dungeon-loot` and the mail table's permanent unique sender/receipt pair.
  Collection and deletion do not discard that receipt.
- A failed mail save retains the chosen winner, result text, exact copy and
  hand-off deadline, and retries after five seconds. Disconnecting after a
  failed save does not reroll or discard that award. Rolls awaiting delivery
  remain in memory, as ordinary open rolls do; they are not a persistent queue
  across a process crash before escrow commits.
- System delivery bypasses player-mail eligibility, rate and inbox limits.
  Thus bound class gear and a full inbox cannot forfeit a roll win. Players
  still cannot mail bound gear themselves.
- Rolls, rank, rarity, attributes, wear and the existing party hand-off window
  are kept. Collection assigns the normal fresh owner-local copy ID; ordinary
  player mail still clears hand-off windows.
- System letters cannot be returned. `systemAward` identifies them in the
  inbox, including after collection, so they are translated in Swedish and
  never labelled as returned player letters. Player-written mail stays literal.
- The winner receives the usual unread badge and a delivery explanation. No
  ground copy is created after escrow succeeds. Mail collection remains atomic
  and harmless to repeat.

The existing mail table is reused; there is no database schema migration.

## Headgear directions, corrected (Beta 1.48.1, `HELM-DIRECTIONS-PROPER`)

The 1.47.2 approach below only narrowed and sheared the stored drawing, and the
owner rejected the result ("good south and north, the rest look like shit").
Cause: every head layer has two drawings per pose, a front (stored for S) and a
back (stored for N); the side rows repeat one of them. `turnHead` in
`client/magesprite.js` now rebuilds every turned pose from that pose's own S and
N frames, using the same `headFrames` records (`[x, y, right-axis x, right-axis
y, front, side]`); no sprite, bounds or manifest file changed.

- **Shell:** each row of the hat has a radius about the head axis. The screen
  shows the half-turn facing the camera: the front drawing covers a quarter turn
  either side of the face, the back drawing the rest, shifted by the yaw. Each
  drawing is sampled one pixel short of its side outline, so no outline lands
  where they meet; the new side edges get the drawing's darkest colour.
- **Far side:** where the near shell is open, the far shell shows, 40 px behind
  in depth, so the head covers it.
- **Standing parts** (ears, feathers, horns, plumes): whatever rises above the
  running minimum of the outline from the head axis outwards. Drawn once, from
  the front drawing for front-facing yaws and the back one otherwise, at
  `h * cos(yaw)` (never under half), the far one behind.
- **Depth:** the back drawing's half sits 8 px towards the camera so a turned
  hood covers the hair behind the face; the front drawing's half keeps its own
  depth so face and fringe show as they do from the front.
- S and N (within 0.2 of a quarter turn) are returned untouched.

Known limits: a deep hood hides most of the face in profile; winged helms splay
both wings in profile; a crown's points bunch towards the middle. True side
drawings per piece would be the only cure.

Checks: `tests/headgear-directions.cjs` passes for all five classes and both
bodies (382 layers, 51,952 poses, minimum 83 changed pixels). Contact sheets
through the real compositor with `tests/gear-sheet.cjs` were reviewed for
hunter, mage, warrior and assassin (idle) and a hunter hurt pose.

## Headgear directions (1.47.2, superseded)

The saved hat frames used a camera-facing head plane. `MageSprite` now attaches
that plane to the rig's real head origin and axes when decoding head layers.
Side views narrow, pitch in opposite directions, and receive a matching depth
gradient. Tall hurt/death poses limit the pitch to keep their artwork inside
the atlas. The shared compositor applies this to classes, both bodies, lazy
head layers and their catalog recolours.

`scripts/headgear_poses.py` exports 2,720 attachment records into the ten class
manifests. It requires `VALHALLA_TOOLS` pointing to the archived rig tools; the
validation used `/media/raid/valhallasc-data/npc-named-work/rig-tools`.
`cel_common.Sheet.export` preserves these records. Rerun the pose exporter after
changing rig poses. All original manifest data, saved editor IDs, PNGs, depth
PNGs, native bounds, bodies and other equipment layers are preserved.

## Focused validation

- `tests/headgear-directions.cjs`, one bounded class run at a time: **382 native
  headgear layers, 51,952 poses**, across all five classes and both bodies.
  Every southeast, southwest, west and east idle/walk/attack/hurt/death frame
  retains visible headgear and stays clear of atlas borders. **1,528** idle
  comparisons reject unchanged camera-facing frames. The test uses actual
  saved art and the real compositor, including lazy loading and tinting.
  Before/after contact sheets were visually reviewed. Removing the pose data
  (`MUTATE=head`) fails at the first stationary hat.
- The ten class manifests, with `headFrames` removed, compare exactly with
  their previous JSON data. No sprite PNG or bounds file changed.
- `tests/todo-bags-chime-ui.cjs`: private browser checks for completion timing,
  first-load silence, snapshot deduplication, real WebAudio oscillator output,
  muting, a full bag, the actual NPC turn-in refusal and retained quest state.
  Nine completion/NPC assertions passed in `driver-QeYdXZ`. After correcting
  the ground-pile fixture, `PART=pickup` passed four independent assertions in
  `driver-UI15sQ`. The debug
  `drop_item` operation creates a pile; it does not remove a carried item.
- Rust checks cover multi-reward/hand-in atomicity, preserved roll properties,
  mail save failure and offline retry, database reopen, full-bag mail refusal,
  repeated collection and receipts surviving deletion. Relevant existing roll,
  class binding and ordinary mail-copy checks also pass: eight focused Rust
  tests in total. The test-profile server build succeeds.
- Changed JS/Python syntax, Swedish assembly/freshness, release-note guard and
  whitespace checks are used. No general suite or encounter/balance grind.

Receipts and screenshots: candidate `test-results/headgear-directions/` and
`test-results/driver-*`; build/check logs are
`/media/raid/valhallasc-data/todo-feedback-*.log`.
