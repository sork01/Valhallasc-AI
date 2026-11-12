# Quest guidance and world feedback (Beta 1.46.0)

**Beta 1.46.2 corrections (owner, 2026-11-12):** errors use a separate stack
at five percent of the game height, with smaller text, so chest/quest banners
cannot push them over the character. Blocked autoattacks show
`Out of line of sight.` through this stack, including the touch Auto button.

**Beta 1.46.1 corrections (owner, 2026-11-12):** errors share the fixed screen
announcement stack as plain red text, with no border/background, up to five
simultaneous lines, newest at the bottom, fading over two seconds. The left
tracker now puts ready quests below unfinished ones even when tracked. Normal
question marks are yellow; repeatable question marks are blue. Gold tooltips
use a viewport overlay outside the transformed game stage.

Owner requests, 2026-11-12: put finished quests last, name completed quests in a
toast, identify ground loot on hover, correct all quest tracking, show brief
errors above the hero, make repeatable minimap quests blue, fade the missing
Greenmeadow trees, and discover travel stops on reaching their hub.

**Beta 1.47.2:** completion banners now have a sound-setting-aware chime; bag-space refusals, including NPC quest rewards and refused ground pickups, use the top error stack. Details: [todo-feedback-hats.md](todo-feedback-hats.md).

## Journal and completion

The journal lists unfinished objectives first, then quests ready to turn in,
then the folded completed history. Tracking a ready quest does not move it above
unfinished quests. The same ordering now applies to the left-side tracker.
Claimed repeatable quests also appear in completed history,
while remaining available at their giver. History cards are read-only.

An authoritative progress transition to all objectives complete shows
`Quest completed: <title>` through the existing announcement stack. First-load
snapshots do not announce old progress, and later identical snapshots do not
repeat it. A new run of a repeatable quest can announce completion again.

## Guidance

`client/quest-guidance.js` indexes current map NPCs, enemy spawns and places.
`scripts/quest_sources.py` exports every public material-source spawn rather
than a single central representative. The journal, minimap, world map and Arrow
share these targets through `Quests.mapMarkers` and `Quests.navigationTarget`.

- Hunt and gather guidance selects nearby real candidates as the hero moves.
  General hunts stay in their province. Named enemies in other zones remain
  reachable through the existing portal graph, including dungeon templates.
- NPC targets follow the current walking NPC positions. An escort initially
  points to the stranded person; after it starts, guidance points to the route's
  safe endpoint.
- Memory and echo objectives follow the story's enforced order. Reach targets
  use untranslated world names, so Swedish does not change their identity.
- Completed objectives disappear, and ready quests guide back to their hand-in
  NPCs. Secret Ember/Hour materials retain giver hints without revealing hidden
  crosses. Arena guidance continues to support every arena giver.
- Route searches are cached; nearest destination selection uses the current
  position rather than retaining a destination chosen before the hero moved.
- Repeatable quests use blue exclamation/question marks. Non-repeatable quests
  use yellow exclamation/question marks on NPCs and both maps. A non-repeatable
  available quest at the same giver keeps priority over an available repeatable
  quest.

## Ground loot and action errors

`client/worldfeedback.js` identifies the visible pile under the cursor and uses
the inventory tooltip with that pile's quantity and actual gear copy. Gold has a
small quantity tooltip. Pointer exit, pickup, pausing and field reset clear the
hover tooltip; a stationary cursor is checked against the current camera. Gold
tooltips are appended to `document.body`, like inventory tooltips: the game
stage has a CSS transform, which would otherwise offset fixed coordinates
relative to the stage instead of the viewport on letterboxed screens.

Nonfatal error packets and refused notices use a fixed stack near the top of
the game and remain in the existing chat log. Each error is
plain red text with no background, border or shadow, and fades from full opacity
to invisible over exactly two seconds. Up to five errors stack in arrival order,
newest at the bottom; a sixth removes the oldest error. Repeated identical
errors keep separate lines. Other announcements keep their own three-message
limit and usual lifetime. Error text remains translated, ignores input, and
keeps its opacity fade with reduced motion enabled.

Autoattack feedback uses the selected target, authoritative movement/attack
state, and existing obstacle geometry. After 350 ms stationary without an
attack or cooldown, an obstructed line produces `Out of line of sight.` at
most once every two seconds. Moving, attacking, clearing input, death, pausing
and cutscenes suppress the hint. A player's projectile hitting an obstacle
also produces the warning from the existing `shotBlocked` event. Combat and
server collision rules are unchanged.

Greenmeadow's oak, birch, apple and willow art now declares canopy occlusion.
The existing sprite trees use their actual frame bounds for the same test.

## Travel discovery

`World::update_spark_discovery`, after player movement, unlocks masters in the
city/camp rectangle the hero has entered. It also accepts ordinary proximity to
a master. Each discovery is saved and announced once, without opening a
conversation, charging gold, or granting talk-quest credit. Dead heroes,
mercenaries, ambient adventurers and heroes flying through on Spark Travel do
not discover stops. Existing characters discover their current hub on the next
tick; no save migration is needed.

## Focused checks

- `node tests/quest-guidance.cjs`: all 1,298 authored objectives resolve against
  26,070 real candidates; checks live walkers, nearest targets, story order and
  escort endpoints. Every objective also has a usable zone route from its quest
  province; all 810 quests have valid giver/hand-in NPCs.
- `cargo test world::travel::spark_tests::spark_hub_entry`: entry discovery,
  one-time notification, persistence and life/flight/hub restrictions.
- `VALHALLA_BINARY=<test-profile binary> bash scripts/test-touch-bounded.sh
  tests/todo-feedback-ui.cjs`: bounded private real-client checks, including
  paired minimap/tree pixels, authoritative quest transitions, real dropped
  loot, errors, and Swedish guidance. No encounter grinding or balance sweeps.

Initial Beta 1.46.0 verification: 21 browser checks passed in `test-results/driver-VGh0HP`, including
paired images for each of the four tree kinds. Screenshot review found that
announcement banners could cover the error box; action errors now draw above
them, checked separately with `PART=errors` (four banner/edge checks in
`test-results/driver-zx41OL`). The twelve changed public client files match the
checkout by SHA-256.

## Beta 1.46.1 correction checks

`PART=corrections VALHALLA_BINARY=<test-profile binary> bash
scripts/test-touch-bounded.sh tests/todo-feedback-ui.cjs` passes all 15 checks
in `test-results/driver-61QW4o`. It covers the actual tracker completion
transition, yellow normal/blue repeatable question marks on NPCs and maps,
five plain red errors in arrival order, fixed announcement placement, a
half-opacity sample at one second, two-second expiry, normal chest notices
remaining intact, duplicate errors, reset, and a real gold drop on a wide
letterboxed viewport. Screenshots of the five-line stack and the corrected
gold tooltip were reviewed. Test gold is created by one private shortcut kill;
the owner retreats beyond the three-tile loot magnet before measuring it.

All eight changed public client hashes match the checkout. JavaScript syntax,
release notes, Swedish freshness and whitespace checks pass. This follow-up is
client only; production PID 183593 and the running server remain unchanged.

## Beta 1.46.2 correction checks

`PART=attack-errors` passes nine focused checks in `test-results/driver-RY5s1D`:
five simultaneous errors stay above the character independently of ordinary
banners, text is smaller, real blocked mage/warrior autoattacks produce
throttled warnings, and attacks resume without warnings after clearing the
obstacle. The screenshot was reviewed. A focused touch Auto run
(`ATTACK_CLASS=warrior`) passes seven checks in `test-results/driver-iuzhmO`,
including the nearest-enemy targeting path. Nine changed public client hashes
match, both health endpoints are healthy, and PID 183593 remains unchanged.
Swedish freshness, release notes, syntax and whitespace checks pass.

## Production release

Released **2026-11-12 12:42 CET as Beta 1.46.0**, source `203d2ed7`,
with the owner's explicit "finish skill and deploy" instruction. The service
restarted with nobody online. Automatic travel discovery and the two-player
Old Tusker adjustment are now live, alongside the client changes.

Backup: `deploy/backups/quest-feedback-release-20261112T113457Z`. The prior executable is `valhalla-server.prev`;
`stopped/valhalla.sqlite` is the consistent database at shutdown. No migration or
manual database change was required. All 38 character states and the 24 guest
records are unchanged. Running PID `183593` matches the saved release
binary; public/bridge health, SQLite `quick_check`, absence of test flags and
the restart journal pass. All twelve changed public client hashes match.

The release executable also passed a private probe with ambient adventurers:
31 snapshots in 3,007 ms, every tick gap exactly two, automatic hub discovery
announced once, and Old Tusker's base health 1,000. No public test character was
created. Rollback steps and verification receipts are stored with the backup.
