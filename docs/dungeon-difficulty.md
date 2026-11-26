# Dungeon difficulty increase (1.15.5)

The owner's request to make dungeons 100% harder is implemented as **100% more
monster health and 100% more monster damage** in all 20 ordinary dungeons.
It covers 127 kinds: packs, bosses and their sleeping helpers, across all four
private copies of each dungeon.

`world/elite-power.txt` is the existing authoritative health/damage overlay.
Each ordinary dungeon kind's two existing factors is multiplied by two. A kind
without an earlier entry used the default `[1, 1]`, so its new entry is `[2, 2]`.
The earlier table is pinned in
`tests/fixtures/dungeon-power-before-1.15.5.txt` for regression comparisons.
Dungeon kinds have no overlap with outdoor or raid kinds. Scope follows the
map's `copies > 0` and `raid == false`, including cloned private copies through
their template. Original table ordering and all other factors are retained.

`Slime::stats` applies the overlay before level scaling; `Slime::with_level`
applies the existing level scaling and rounding to spawned health and damage.
The existing melee, ranged and slam attacks use those scaled values. Boss
mechanics that explicitly kill or use fixed health fractions retain their
existing behavior, as do enrage timing, movement and attack speed. Raid, arena,
player and outdoor stats retain their previous values. Loot and quest rewards
retain their existing rules.

The two focused `dungeon_difficulty_` Rust regressions check every affected kind,
all preserved factors, normal and ±2 spawn levels, full starting health, all 20
templates and their 80 copies. Restoring the pre-change table through the
existing test-only `ELITE_POWER_FILE` override must fail these tests. The old
solo/party calibration and win-rate rules are retired; no encounter grinding or
multi-seed balance sweep is required or performed for this change.

The power table is embedded in the executable. Releasing the client alone does
not activate this change. Prepare an optimized executable and matching 1.15.5
client, verify them privately, then obtain fresh owner approval before stopping
and restarting the public game. Keep the previous executable and a consistent
SQLite backup before the build and refresh the backup immediately before an
approved restart. No world generation or save migration is needed.

Focused validation: both `dungeon_difficulty_` Rust regressions passed. Running
the same test executable with the pre-change power table failed both new tests,
confirming the assertions detect missing health/damage scaling. The optimized
release and private executable comparison are recorded in the staged deployment
receipt; the public game requires fresh restart approval before activation.
