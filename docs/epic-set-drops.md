# Purple set-piece drops

These settle `DROP-EPIC-RULES` in [TODO.md](../TODO.md). `DROP-EPIC-SERVER` implements the roll, `DROP-EPIC-UI` shows it and `DROP-EPIC-CHECK` verifies it.

## The roll

- **5% per dropped set piece, not per kill.** After a boss slot pool or a chest set-piece roll has picked its blue catalog item, one more independent roll decides whether that copy is purple. A boss with two guaranteed blue pools makes two independent 5% rolls; a kill that drops no set piece rolls nothing. The expected rate is 0.1 purple pieces per boss kill.
- **One constant.** `EPIC_SET_DROP_CHANCE: f64 = 0.05` lives in `server/src/items.rs` next to `outdoor_elite_drop_chance`, and no other file repeats the number. The roll is made by one function, `set_piece_copy(piece, roll)`, which every set source calls, so a new source cannot forget it.
- **Where it applies:** every set piece that the server grants from `boss_piece_for` (all 15 dungeon sets, Undervault and Moonwell included, with their party and mercenary credit) and the 6% dungeon set-piece roll in treasure chests ([chests.md](chests.md)). Nothing else changes: outdoor drops, ordinary kills, outdoor elites (which already have their own 5% purple tier), quest rewards and shop stock keep today's tables.
- **Undervault and Moonwell are included.** They are the first two sets and the ones most players farm. Undervault has 27 pieces (no necklace) and the other sets 28; the roll is per piece, so that does not matter here.
- **Seeds.** The extra roll comes from `World::random()`, drawn only when a set piece was chosen, so seeded runs that never reach a set piece keep their sequence.

## A purple copy, not a new catalog entry

The dropped item is the **same catalog ID** as the blue piece, carried as a `GearInstance` with `rarity: "epic"` (the per-copy rarity from `G-INSTANCE-DATA`). No item is added to `world/items.txt`, so item IDs, loot pools, set membership and saves are unchanged, and an old save simply never contains such a copy. This is the same representation that merging produces, which keeps one code path for tooltips, refinement and trade.

Stat curve of the copy (the same ladder the catalog's own purple pieces use):

| Field | Value |
| --- | --- |
| `attack`, `defense` | blue values × 1.175 (the existing 17.5% rarity step, as `merge_output` applies), rounded to one decimal |
| `bonus_stats` | the blue piece's one fixed stat, unchanged |
| `rolled_stats` | the **second** fixed stat that `items.rs` expects of purple gear (`blue_and_purple_attribute_bonuses_are_fixed_useful_and_save_with_gear` wants exactly two) |
| `rank` | 0 |

The second stat is chosen without randomness, from the piece's own useful-stat list (the same lists the test uses): the first entry that the blue piece does not already have and that is not capped. Value is the piece's own ladder value (for example 30 at level 40). Caps hold: accuracy never exceeds 20 and dexterity never exceeds 70, so a capped entry is skipped to the next. The result is stored in `rolled_stats`, which `effective_bonus_stats` already adds to `bonus_stats`, so refinement and tooltips need no change.

Class lists, in order: warrior strength, stamina, agility, accuracy, dexterity; mage and priest intellect, stamina, agility, accuracy, dexterity; assassin and hunter agility, stamina, strength, accuracy, dexterity; class-independent pieces stamina, accuracy, dexterity (stamina, strength, agility from level 75).

## What a purple copy does

- **Counts as the piece for sets.** It is the same catalog item, so it counts once toward 2/4/6/8 exactly like the blue copy (`SET-RULES` counts distinct equipped slots).
- **Cannot merge further.** `next_rarity("epic")` is already `None`, so the merge dialogue refuses it with "That rarity cannot be merged." A purple copy can still be refined; it uses `refinement_crystal_epic`, which `GearInstance::crystal` already derives from the copy's rarity.
- **Shown purple everywhere.** Loot marker colour, the rarity word in tooltips and bag rows use the **copy's** rarity, not the catalog's. The drop pile carries the `GearInstance` (`Drop.gear`), as an orange drop does today, so a party's Need/Greed vote and the pickup message already name the right rarity.
- **Sale value** is the catalog's blue value × 2 (the same ratio as the catalog's blue and purple tiers at one level), so the piece is never worth less than the blue it could have been.

## Interactions

- Party loot: a purple set piece is rolled for like any purple drop (Need only for a class that can wear it, then Greed). The copy is created before the vote and travels with the pile.
- Full bags: the drop stays on the ground like any other (60-second lifetime), with its rarity.
- Trade: `trade.rs` already moves the offered gear copies (it re-ids them for the receiver), so the buyer receives the purple copy with its stats and rarity; `DROP-EPIC-CHECK` asserts it.
- Chests: the 6% set-piece roll picks the blue item, then `set_piece_copy` applies the same 5%.

## Verification hooks for `DROP-EPIC-CHECK`

- A pure test of `set_piece_copy` at roll 0.0, 0.0499 and 0.05: purple below the constant, blue at and above it, for every set piece and over every class list.
- Seeded boss kills (hundreds) average 5% purple per dropped set piece within a stated tolerance, and a kill without a set piece never rolls.
- A purple copy has exactly two bonus stats in total, attack and defense equal to 1.175 times the blue values, respects the accuracy and dexterity caps, survives save and reload, refuses to merge and refines with an epic crystal.
