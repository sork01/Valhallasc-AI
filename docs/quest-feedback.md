# Quest guidance and world feedback (Beta 1.46.0)

Owner requests, 2026-11-12: put finished quests last, name completed quests in a
toast, identify ground loot on hover, correct all quest tracking, show brief
errors above the hero, make repeatable minimap quests blue, fade the missing
Greenmeadow trees, and discover travel stops on reaching their hub.

## Journal and completion

The journal lists unfinished objectives first, then quests ready to turn in,
then the folded completed history. Tracking a ready quest does not move it above
unfinished quests. Claimed repeatable quests also appear in completed history,
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
- Available repeatable quests use blue exclamation marks. Ready turn-ins use
  blue question marks. A non-repeatable available quest at the same giver keeps
  priority over an available repeatable quest.

## Ground loot and action errors

`client/worldfeedback.js` identifies the visible pile under the cursor and uses
the inventory tooltip with that pile's quantity and actual gear copy. Gold has a
small quantity tooltip. Pointer exit, pickup, pausing and field reset clear the
hover tooltip; a stationary cursor is checked against the current camera.

Nonfatal error packets and refused notices appear briefly above the local hero
and remain in the existing chat log. The box holds at most two messages;
repeated identical messages refresh their lifetime instead of stacking. It
follows the hero, translates the refusal, expires after 2.4 seconds, and never
captures input.

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

Verification: 21 browser checks passed in `test-results/driver-VGh0HP`, including
paired images for each of the four tree kinds. Screenshot review found that
announcement banners could cover the error box; action errors now draw above
them, checked separately with `PART=errors` (four banner/edge checks in
`test-results/driver-zx41OL`). The twelve changed public client files match the
checkout by SHA-256.

These changes are prepared in the checkout. The client is served directly from
disk; travel auto-discovery and the earlier Old Tusker adjustment require a
server release. No production restart or database edit is part of this work.
