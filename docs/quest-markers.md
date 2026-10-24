# Quest map markers (UI-QUEST-MARKERS)

Beta 1.16.0 adds quest guidance to the minimap and the detailed zone view of the world map. Client only; no server restart, world generation or save changes.

Every NPC whose gossip offers an available quest gets a gold `!`. A ready quest gets a blue `?`, taking priority when that giver also offers another quest. Repeatable quests use the same colors. Active, completed, locked and upcoming quests do not produce giver markers. This uses the existing journal `status()` rules, including prerequisites and minimum level.

Choose **Track quest** in the journal, or click a quest title in the tracker, to add green outline diamonds at its unfinished destinations. Talk and escort objectives use NPC positions; visit and hold objectives use their places; chime objectives mark their bells. A hunt marks an actual matching spawn near the center of that enemy's authored area, including ordinary-slime aliases. A hub quest naming enemies in an adjacent dungeon marks those enemies inside that dungeon. Reach objectives mark the relevant gate and destination spawn. Bring and Arena quests point to their giver. Finishing all objectives replaces the tracked destinations with the hand-in NPC; claiming the reward removes them. Completed individual objectives disappear as progress arrives. Material quests do not expose hidden Firelord crosses.

Markers remain visible through unexplored cells; ground fog, enemy visibility and discovery rules remain unchanged. Only NPCs and objectives belonging to the displayed zone appear. The world sheet still opens only visited zones, and the detailed view can show a different zone from the hero's location.

`Quests.mapMarkers(zone)` is the shared presentation source. It derives NPC coordinates from the same `WORLD_MAP` NPC lists used by `City.npcs` and `Field.visitNpc`. Arrays are cached per zone and invalidated on quest-state changes, level changes, tracking changes and reset. The minimap draws the overlay each frame after fog and actors, outside its ground cache. The world map checks the cached array every 250 ms while open and rebuilds only its quest marker layer when needed. It keeps the existing gate, party, hero and Travel Master layers. Zone markers have tooltips and accessible labels, and the sidebar explains the three symbols. New labels and templates have hand-written Swedish.

## Focused verification

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
