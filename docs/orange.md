# Orange (legendary) pieces and the level gate

Source of truth: `world/orange_rules.txt`, written by `python3 scripts/orange_rules.py`; `python3 scripts/orange_items.py`
copies the catalog entries into `world/items.txt`; then `node scripts/sync-world.cjs` and a Rust rebuild.

## Ladder
Ten families of five slots (armor, weapon, headgear, shoulders, gloves), one level per family:

| Family | Level | Pieces |
|---|---|---|
| Ember Sovereign | 10 | orange_01..05 |
| Verdant Crown | 20 | 06..10 |
| Storm Oracle | 30 | 11..15 |
| Abyss Singer | 40 | 16..20 |
| Starforged | 50 | 21..25 |
| Solar Regent | 60 | 26..30 |
| Ash Phoenix | 70 | 31..35 |
| Moonlit Sentinel | 80 | 36..40 |
| Chronometer | 90 | 41..45 |
| Worldheart | 99 | 46..50 |

## Rules
- `requiredLevel` is the family level and is enforced on equip like any other gear.
- A hero is only offered pieces with `requiredLevel <= hero level + 5` (`drop.levelWindow`). Nothing drops below
  level 5. The pick is uniform over the eligible pool. The rebirth boost (`roll_orange_boosted`, `copies()`) and the chest
  opener use the same filter, with the credited hero's / opener's level. The random draws are the same at every level.
- Stats: nominal = purple budget of that slot and level (`gear_levels.budget`) x 1.175 (orange is 17.5% over purple),
  every roll spans +-4% of it, in whole numbers. Armor uses the 3.0 chest base, weapons attack 4.0, the rest defense 1.0.
  Stamina follows `ATTRIBUTE_BONUS` (extended to 114 at 99) x 1.175; accuracy and dexterity follow it but stop at
  20 and 70 (the hit and dodge caps).
- `orange_rules.py` asserts that each piece's lowest roll beats the purple of its level and that no roll reaches the
  next family's nominal value for the same slot. The Rust tests (`items/orange.rs`) assert the same from the shipped file,
  plus the drop window and equip-at-level on all five classes.
- Catalog `attack`/`defense`/`bonusStats` are the lowest rolls (only used by `give_item` and old saves);
  `sell` is 500 x level factor.

## Saved copies
`python3 scripts/backfill_orange_levels.py --db data/valhalla.sqlite --apply --backup <path>` (service stopped) re-rolls
every saved orange copy inside the new ranges (seeded by character and copy id, recorded in `orange_migrations`, so a
rerun does nothing) and returns worn pieces above the character's level to the bag.
