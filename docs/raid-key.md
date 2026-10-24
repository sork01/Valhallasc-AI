# The Ember Key

Every hero must claim `raid_key` before entering the Chained Forge outer door,
including heroes who entered or cleared the raid before this update. Hired
fighters follow their hirer without an individual key. Saved raid occupants
already return to the outside entrance through the existing instance recovery.
No zone indices change and no saved-character backfill is needed.

Iarn Emberkeeper (`raid_key_keeper`) at Emberwake's arrival camp (23,131) offers
**The Ember Key**, level/minimum level 99. Ten bring objectives list only the zone
names. No map/minimap markers, route buttons, tracker direction or coordinates
are shown to players. The tracker shows `Pieces: n/10`. Claiming the quest grants
`ember_key` and permanently unlocks the door through `needs_quest: raid_key`.
Shards stay in the bag after claiming, as requested. The normal level-99 quest XP
rule applies to turn-in; Firelords themselves give no XP, gold, gear or materials
besides the private shard. Shards and key are unsellable/untradeable materials.

| Zone | Cross | Item | Herald |
|---|---|---|---|
| 0 Greenmeadow | 38,47 | ember_shard_0 | Ashwarden of Greenmeadow |
| 1 Emberfall Crags | 24,73 | ember_shard_1 | Cinderthane of Emberfall |
| 2 Rimeveil Glacier | 64,96 | ember_shard_2 | Frostflame of Rimeveil |
| 3 Gloamfen | 19,37 | ember_shard_3 | Bogflame of Gloamfen |
| 6 Wyrdwood | 69,158 | ember_shard_6 | Rootpyre of Wyrdwood |
| 7 Bifrost Reach | 66,106 | ember_shard_7 | Skybrand of Bifrost |
| 8 Rán's Deep | 80,131 | ember_shard_8 | Tidepyre of Rán's Deep |
| 13 Astralhollow | 87,87 | ember_shard_13 | Starpyre of Astralhollow |
| 14 The Prismwaste | 32,75 | ember_shard_14 | Glassflame of the Prismwaste |
| 15 The Obsidian Orrery | 59,90 | ember_shard_15 | Clockpyre of the Orrery |

These coordinates were selected and flood-checked against the existing map.
The herald starts 2.5 tiles west of the cross, on reachable ground. Rán's Deep
uses an existing seabed ledge; Bifrost uses an existing island. Greenmeadow's
cross is near the main road north of the starting area. There is no fog-only
access requirement. Generator checks enforce distance from ordinary spawns,
hubs, every gate disc and inbound portal arrivals.

A cross is visually present but inert without the active quest, after collecting
its shard, or while the hero has a pending private shard drop. Near an eligible
cross the prompt is **Commune with the cross · [interact binding]**. The new
`interact` key action defaults to G, leaving the existing talk interaction key unchanged;
it respects the key map and typing rules. Clicking the cross also interacts.

Communing costs nothing and channels for three server seconds. Movement,
damage, death, stun or leaving the zone interrupts it. The cross glows during
channeling, including for observers. Only one channel or living herald may own
a cross at once. An interruption immediately re-arms it. On completion a level-99
`ember_firelord` wakes from that cross's dedicated dormant slot. It uses Eldmarr's
existing editable sprite, smaller and tinted for the zone, and ordinary elite AI
with no new mechanics. Reuse existing boss audio; no new song.

Provisional stats: 60,000 health, 650 authored damage (normal combat scales
apply), movement speed 3.2, radius .63; `elite-power` factor [1,1], soft enrage
starts at 240 seconds with a 120-second ramp. These are authored starting values
for the owner's evaluation, not a measured balance claim. No balance sweeps.

The herald hunts without a home leash, never crosses portals or enters a hub,
and fully heals if it evades. It despawns only when no real hero remains in the
zone (mercenaries/ambient adventurers cannot keep it alive). Death or despawn
immediately frees the cross. Helpers may fight, but they never qualify for shards.

At death, each living real hero who contributed positive damage personally or
through their hired mercenary, is in the same zone within SHARE_RANGE (60), has
the active quest and lacks this shard (including pending drops), receives one
private drop. Other heroes, helpers and distant contributors receive nothing.
The special kill path bypasses all ordinary XP/gold/loot/rebirth rolls.

Swedish: The Ember Key = Glödnyckeln; Ember Shard = Glödskärva; Ember Grave Cross =
Glödgravskors; Firelord = Eldherre; Pieces = Delar; Commune with the cross =
Åkalla vid korset. Zone names follow the existing Swedish glossary/catalog.

Source: `scripts/raid_key.py` owns crosses, dedicated sleeping spawns, quest,
NPC, items, enemy catalog and door gate. Zone generators reapply its map changes;
`sync-world.cjs` reapplies it before exporting. Cross art is authored through
PixelFlow. No new enemy sprite set is created.

## Validation and release

Eight focused Rust checks pass: data/collision, inert guards, timing/interruption/
exclusivity, contributor eligibility/private-only rewards, empty-zone despawn,
evade/sanctuary, nine/ten-shard claim/entry and saved unkeyed raid-occupant recovery.
`MUTATE_RAID_KEY_GATE=1` on the test binary removes the map gate and correctly
fails the nine-shard entry assertion. It is test code only.

The real MCP `raid_key` scenario passes 11 checks. `tests/raid-key-ui.cjs` passes
17 checks with real sprites, including pixel evidence, remapped interaction,
channel cancellation, the herald's smaller atlas/name, shard collection and
tracker progress. `MUTATE=1` disables cross drawing and correctly fails the pixel
check. Screenshots are in private run `test-results/driver-1nkbvE`.

Clippy (`--all-targets -- -D warnings`), formatting, changed JS/Python syntax,
generator byte stability and the full Swedish gate pass (catalog, 21 locale,
15 language UI and 36 layout checks). No balance sweeps were run.

A level-99 login notice warns that every hero needs this key, including past
raiders. Client/server deployment is performed together with nobody online;
backup and public verification details will be recorded here after release.
