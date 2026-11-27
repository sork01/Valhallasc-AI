# GM Island

Private festival island and combat laboratory, authored at file zone 47. Its 68,509
land tiles are within 1% of Greenmeadow's 68,006. Christmas (Hollyhaven), New Year
(Midnight Quay), Halloween (Pumpkin Hollow), Midsummer (Sunribbon), Easter
(Blossombell) and Valentine (Roseheart) villages remain decorated all year. Each
has four cottages, a host and a Spark Travel master. Island Spark routes connect
only to island villages, are free, and are discovered on entry. Public routes never acquire these stops.
The island uses clear outdoor weather and never rolls random treasure chests.

Enter with the GM Test menu's **Visit GM Island** button, `/island`, `/tp island`,
or the GM gate at Greenmeadow (276, 226). The gate is hidden from ordinary clients.
Admission uses `Character.gm` and `Map.gm_only` on the server, including direct
teleports, Meeting Stone acceptance and saved logins. Test shortcuts never bypass
this rule. Ordinary saves found on the island return to Greenmeadow.

## Island services

* Torvald the Quartermaster and Saga the Class Mentor: choose level 1–99, any of
  the five classes and common/green/blue/purple/orange gear. Each slot receives
  the highest available piece of the requested rarity at or below the level.
  A rarity with no available pieces is refused. Two rings receive separate
  instances. A new test character uses recommended attributes, retains the GM's
  race/gender and has no rebirth, alchemy or seasonal damage bonuses. GM golden
  equipment and its lethal-strike override are absent from test loadouts.
* Edda the Summoner: searchable monster/boss catalogue, level and count. Up to 24
  opponents occupy new, reusable island slots, without moving the world's real
  enemies. Normal AI, attacks and boss mechanics run at their island spawn.
  The arena's open interior is 56 × 50 tiles; enemies that leave its bounds return
  to their spawn. Deaths award no XP, gold, loot or quest credit and never respawn.
  Clear arena also ends boss mechanics and clears projectiles and the meter.
* Runa the Recruiter: up to four free companions, selectable class/level, through
  the normal mercenary implementation. Apply the loadout first; changing it
  dismisses companions. Leaving removes island companions.
* Bjorn the Trainer: reset DPS; heal/refill and clear cooldowns. Six level
  1/20/40/60/80/99 dummies stand twelve tiles apart. They never move, attack or die;
  the hit path records actual attack damage, including skills and enchantments.
  Their level affects hit chances normally. The standard DPS meter freezes five
  seconds after the last hit. Reset stops attacks and clears in-flight player bolts.
* Isle Warden: leave and restore the original character. The return portal to
  Greenmeadow also restores it. Arena defeats revive the GM at the island arrival.

The first entry checkpoints the complete original `Character` in the optional,
server-written `gm_island_backup`. It persists through disconnects/restarts.
Loadout changes replace only the test character and retain that checkpoint.
Leaving through the Warden, return gate, `/tp`, or `/goto` restores the original
character; ordinary travel then uses its selected destination. Dungeon/gauntlet
menu entry is refused until the GM leaves the island. Companions, projectiles,
enemy slots and meter totals stay transient. Ambient adventurers and guards do
not populate the island. Existing ordinary characters acquire no saved field.

## Generation and validation

`python3 scripts/generate_gm_island.py` is seeded and byte-stable, preserves all
existing zones and installs the reciprocal gate. World sync detaches the island
before public overlays, runs the generator after public Spark routes, and refreshes
the weather/chest tables. When running the generator alone, also run
`python3 scripts/weather_zones.py --write` and
`python3 scripts/chest_zones.py --write`. Rebuild Rust after changing world data. Its flood check covers every service, town and dummy;
the native test also flood-fills actual Rust collision.

Source: `server/src/world/gm_island.rs`, `client/gm-island.js`,
`scripts/generate_gm_island.py`. Isometric rails, pillars and wooden dummies use
the existing canvas art system; villages reuse existing cottages and holiday art.

Focused checks:

```
python3 tests/gm-island-map.py
cargo test gm_island -- --test-threads=1
VALHALLA_BINARY=<private-optimized-binary> node tests/gm-island-probe.cjs
VALHALLA_BINARY=<private-optimized-binary> node scripts/test-via-mcp.cjs run gm_island
VALHALLA_BINARY=<private-optimized-binary> bash scripts/test-touch-bounded.sh tests/gm-island-ui.cjs
VALHALLA_BINARY=<private-optimized-binary> GMI_PHONE=1 bash scripts/test-touch-bounded.sh tests/gm-island-ui.cjs
VALHALLA_BINARY=<private-optimized-binary> GMI_ART_ONLY=1 REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/gm-island-ui.cjs
```

The protocol probe uses a disposable database and a local fake SSO endpoint,
authenticates a real GM and ordinary guest, and disables test commands. It covers
all classes, summon limits/cleanup, actual dummy attacks and meter reset,
reconnect/restore and the 30-snapshots/3-seconds tick budget. The MCP scenario proves
private test commands also cannot admit an ordinary character. Browser checks
exercise NPC controls on desktop and a 740 × 360 touch viewport. The separate real-art
pass waits for the GM and all NPC atlases, then saves all six villages, arena,
dummies and the map. Keep class-changing controls separate from the real-art pass:
the combined Warrior/Mage/Priest sprite banks exceeded the 1.5 GiB test cap.
The split runs retain the same memory and CPU limits.

## Local validation, 2026-11-27

All implementation checks passed on `feat/gm-island` before release preparation.

* 30 native checks: 12 island checks, eight existing GM-menu checks, three DPS-meter
  checks, three weather checks, chest eligibility, Undervault copy geometry and
  two Forge copy/cleanup checks.
* 28 real private-protocol checks without test flags, including all five loadouts,
  actual boss combat/mechanics, seasonal bosses, four hires, immortal dummy hits,
  DPS reset, reconnect and original-character restoration. NPC cooldown waits use
  simulation ticks, not wall time; the fifth-hire refusal checks the actual limit.
* Six private MCP scenario checks and four driver/SDK lifecycle checks. The SDK
  shortcut test now forwards an explicitly selected `VALHALLA_BINARY`.
* Nine desktop and nine 740 × 360 touch control checks; 13 separate real-art checks.
  All use the unchanged 1.5 GiB, one-CPU, no-swap browser runner. An initial combined
  real-art class-switch run hit that memory cap; splitting controls and art resolved it.
* Public-map preservation, arrival clearance, NPC art assignments, isolated Spark
  links, two byte-identical generations and future-zone detach/install checks pass.
  Removing GM admission or moving arrival into the exit gate fails the independent
  mutation checks. Weather/chest derivations, Swedish, JavaScript syntax, new Rust
  file formatting and whitespace checks pass.

The final probe records 30 steady snapshots in **2,925 ms**, with every tick gap
exactly two. Its separate unaligned window took **3,026 ms**; earlier unaligned
windows took 3,075–3,146 ms. The steady window begins just after the existing
100-tick periodic save and ends before the next one. This is a steady-state budget,
not a worst-case latency guarantee. Timing artifacts retain individual timestamps
and tick numbers; the cause of isolated longer gaps was not established.

Local evidence (ignored test artifacts):

* `test-results/gm-island-validation.json`: binary/data hashes and final results.
* `test-results/gm-island-probe-VEUoWx/receipt.txt` and `snapshot-timing.txt`.
* `test-results/driver-J6bmFj/report.json`: final MCP scenario.
* `test-results/gm-island-ui-VY0Pzx/`: desktop controls.
* `test-results/gm-island-ui-HHOSud/`: touch controls.
* `test-results/gm-island-ui-xFLJVu/`: real-art villages, arena, training yard and map.

At implementation sign-off, public service PID remained **1572995**. No live
database writes, release, restart, commit or push had been performed. The private optimized build has only the existing
unused `mail_unread` warning.

## Deployment and saved-zone migration

This change requires a coordinated server/client release. It is not a client-only
update. The owner subsequently authorized deployment as a **silent update**:
retain the 1.15.14 label and existing release notes, with a new commit-suffixed
client snapshot and the matching server executable.

Appending one file zone moves every appended dungeon/raid/Arena copy ID up one:
previous file zones are 0–46, new file zones 0–47, first appended copy 47 → 48,
total runtime maps 117 → 118. Before release, take the required database/executable
backups and inspect **all saved characters**, corpses, and saved flight points.
Translate old appended-copy references by +1 exactly once in the stopped database
(or move those characters to a known public entrance). Never reinterpret an old
copy-47 GM save as an island save. Rollback must reverse this reference migration
or restore the matching database. Existing public file-zone IDs do not change.
Update `vault_tests.rs::COPY`, the Forge copy list (46/108/109) and total-map
assertion alongside insertion. The GM-menu normal-dungeon hire assertion now
expects the existing `Some(copy)` contract instead of its obsolete `None`; no
mercenary contract implementation changed for that assertion.
