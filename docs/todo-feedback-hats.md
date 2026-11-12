# Quest chime, bag refusals, dungeon loot mail and headgear (Beta 1.47.2)

Implemented from the four open owner requests of 2026-11-12. The candidate was
built and checked in `/media/raid/valhallasc-data/todo-feedback-work`, branch
`fix/todo-feedback-hats`. All 34 changed project files were applied to the main
working tree after verification. The client is live as **Beta 1.47.2**: all 18
changed public client files hash-match. The running server is still PID
`183593`; its changes are built and tested but **deployment is pending**. No
server restart or production database change was made. The owner has now explicitly invoked finish and deployment; the release
build and backup are being prepared. Public hash receipt:
`test-results/todo-feedback-public.json` in the candidate checkout.

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

## Headgear directions

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
