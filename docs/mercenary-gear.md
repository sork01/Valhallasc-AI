# Mercenary gear (MERC-MIRROR-GEAR, 2026-11-14)

A hired fighter (`World::place_mercenary`, so Meeting Stone, quest contracts, dungeons, the raid quartermaster and GM free hires) wears what its hirer wears, in its own class. Level was already the hirer's; the price is unchanged (`merc_price`).

- `Character::mirror_gear_of(&hirer)` (`server/src/items.rs`): for every worn, non-starter, unbroken piece of the hirer, pick from the ordinary ladder (no `source`, rarity common..epic, no starter) a piece of the same kind, the merc's class (or class-neutral for pants, necklace, rings, cloak), at the hirer piece's level and rarity. The rarity is that of the worn gear copy, so a merged copy counts as its new tier. Exact level/tier missing (epic only every tenth level): the best piece at or below both. Set, orange, Hierloom and GM pieces map to the ordinary piece of that level, capped at epic; set bonuses are never mirrored.
- A slot the hirer leaves empty or fills with a starter keeps the hire's own starter chest/weapon and green cloak (so an ungeared hirer changes nothing).
- Snapshot at hire time (contracts end with the objective or instance clear); not refreshed when the hirer re-equips. Nothing is saved, wear stays zero, hires still forfeit loot.
- Stat points are re-spent after the gear is on (`allocate_recommended` reads the effective attributes), then hp and resource are refilled.
- `World::merc_mirror_gear` is off in unit-test worlds (`!cfg!(test)`), so the dungeon/boss/elite calibration tests keep green-geared hires. No recalibration was done on purpose: a well-geared hero finds hires stronger and dungeons easier.
- Tests: `cargo test mirror_tests` (4). Mutation: an early return in `mirror_gear_of` fails all four.
