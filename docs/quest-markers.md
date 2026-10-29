# Quest map markers (UI-QUEST-MARKERS)

Beta 1.16.0 adds quest guidance to the minimap and the detailed zone view of the world map. Client only; no server restart, world generation or save changes.

Every NPC whose gossip offers an available quest gets a gold `!`. A ready quest gets a blue `?`, taking priority when that giver also offers another quest. Repeatable quests use the same colors. Active, completed, locked and upcoming quests do not produce giver markers. This uses the existing journal `status()` rules, including prerequisites and minimum level.

Choose **Track quest** in the journal or beside a quest in the tracker to add green outline diamonds at its unfinished destinations. The tracker button toggles tracking without opening the journal; its pressed state and a green border identify the selected quest. Clicking a tracker title still selects that quest and opens its journal entry. Talk and escort objectives use NPC positions; visit and hold objectives use their places; chime objectives mark their bells. A hunt marks an actual matching spawn near the center of that enemy's authored area, including ordinary-slime aliases. A hub quest naming enemies in an adjacent dungeon marks those enemies inside that dungeon. Reach objectives mark the relevant gate and destination spawn. Bring and Arena quests point to their giver. Finishing all objectives replaces the tracked destinations with the hand-in NPC; claiming the reward removes them. Completed individual objectives disappear as progress arrives. Material quests do not expose hidden Firelord crosses.

Beta 1.32.2 (same version at the owner's request) adds **Arrow** in Settings. It starts off and saves its choice in `Prefs.questArrow`. With a quest selected, a green pointer ahead of the character faces the nearest unfinished destination using the field's isometric projection. In another zone it points to the nearest exit among routes with the fewest zone crossings. Sealed templates and uncleared completion exits are excluded. At the destination, while dead or during Spark Travel, the pointer is hidden. It reuses quest-marker coordinates and does not move the character. `Quests.navigationTarget` caches route candidates until quest progress, level, tracking, zone or instance-clear state changes; each frame only selects the nearest cached candidate.

Markers remain visible through unexplored cells; ground fog, enemy visibility and discovery rules remain unchanged. Only NPCs and objectives belonging to the displayed zone appear. The world sheet still opens only visited zones, and the detailed view can show a different zone from the hero's location.

`Quests.mapMarkers(zone)` is the shared presentation source. It derives NPC coordinates from the same `WORLD_MAP` NPC lists used by `City.npcs` and `Field.visitNpc`. Arrays are cached per zone and invalidated on quest-state changes, level changes, tracking changes and reset. The minimap draws the overlay each frame after fog and actors, outside its ground cache. The world map checks the cached array every 250 ms while open and rebuilds only its quest marker layer when needed. It keeps the existing gate, party, hero and Travel Master layers. Zone markers have tooltips and accessible labels, and the sidebar explains the three symbols. New labels and templates have hand-written Swedish.

## Focused verification

Tracker buttons, Arrow preference persistence, actual canvas pixels/orientation, cross-zone exits and authoritative accept/complete/claim transitions: `bash scripts/test-touch-bounded.sh tests/quest-arrow-ui.cjs`. Set `QUEST_ARROW_CANDIDATE=/absolute/candidate-directory` to route candidate files privately before installing them; `MUTATE=1` disables arrow rendering and must fail the visible-arrow assertion.

Use the existing release binary in an isolated world, with real sprites:

```
REAL_SPRITES=1 VALHALLA_BINARY=/absolute/path/to/target/release/valhalla-server node tests/quest-markers-ui.cjs
MUTATE=1 VALHALLA_BINARY=/absolute/path/to/target/release/valhalla-server node tests/quest-markers-ui.cjs
node tests/whats-new-notes.cjs
python3 scripts/build_swedish.py --check
python3 tests/swedish-catalog.py
node tests/swedish-locale.cjs
```

The mutation disables `Quests.mapMarkers` through a private browser route and must fail. The browser check covers authoritative accept/complete/claim transitions, prerequisites, repeatable quests, level-only invalidation, priority at a shared giver, fog preservation, paired minimap pixels and colors, actual NPC/place/enemy positions, tracked talk/kill/visit/hand-in objectives, partial progress, remote zone viewing, cross-zone errands, dungeon targets, gossip parity across all zones, reset, short-screen rendering, and English/Swedish tooltips. Extended objective checks use presentation fixtures without grinding. Screenshots and a result file stay in the private driver's artifacts directory.

## Release verification (2026-10-24)

All 40 real-sprite browser checks pass in private world `driver-sxKZkn`; `MUTATE=1` fails when the map marker source is disabled. Changed JavaScript syntax, whitespace, the release-notes guard, the full Swedish catalog and all 21 Locale checks pass. The seven changed public client assets match local SHA-256 hashes, and public/bridge health report OK. Proof and inspected screenshots: `test-results/quest-markers-20261024/`. No server build, restart, public guest creation or database migration.

## Tracker / Arrow verification (2026-10-29)

Beta 1.32.2: 16 English desktop checks pass against privately routed candidates (`driver-xs97vp`), and 15 Swedish short-screen touch checks pass against the installed files (`driver-xRE0k3`). The latter verifies the translated control/help, physical 44 px tracking target, actual arrow pixels/orientation, saved choice and no browser errors. Remote routing and quest lifecycle transitions run on desktop. Disabling the arrow draw through a private route fails the visible-arrow assertion. Screenshots are in those private driver directories. Chrome requires a loopback-network permission for a fulfilled candidate HTML document; the candidate test grants it only to its private origin.

JavaScript syntax, whitespace, release notes, Swedish generation freshness and 23 Locale checks pass. The broader Swedish catalog guard still flags three existing NPC names containing English words; those exact entries also fail at HEAD and are unchanged by this work. All eight changed public client files match local SHA-256 hashes; public and bridge health report OK. Client-only installation, no restart or database change; version held at the owner's request.
