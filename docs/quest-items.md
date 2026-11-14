# Quest-only items for `bring` quests (`QUEST-ITEM-DROPS`)

A `bring` quest that used to ask for an ordinary monster material (slime gel, ember cores ...) now asks for **its own quest item**.

- **Items:** `scripts/quest_items.py` (run last by `sync-world`, idempotent) gives every such objective an unsellable item `qi_<quest id>`
  (kind material, `sell` 0, `questMaterial` = the ordinary material it comes from), named "<Material> (<Quest title>)" with a hand-composed Swedish
  name, and rewrites the objective's `target` in `world/map.txt`. The 14 older quest items (hour shards, ember shards, keys) are untouched.
  Ordinary materials still drop and sell as before, so gold income is unchanged.
- **Drops** (`server/src/world/quest_drops.rs`): the monsters of the material also drop the quest item, but only for a hero who holds the quest
  (not claimed) and is still short of it (the bags and the drops already lying there for them count), never past the need, at the objective's own
  `dropChance` (0.30 to 0.80, seeded by the quest id, kept if already set, shown nowhere in the UI), through the rebirth multiplier (`copies`).
  One copy per kill goes, in turn, to the party members in range who still need it.
- **Hand-in:** the quest takes its count; whatever remains of a quest item that no other held quest asks for is discarded for no gold
  ("Discarded N × item").
- **Old saves** (`Character.quest_items_version` 0 -> 1, on login): for each held `bring` quest the old material the hero carries (up to the count) becomes the
  quest item, the ordinary rest stays sellable; quest items nobody needs are removed, and a banked quest item is dropped.
- Where to hunt: `scripts/quest_sources.py` resolves a quest item's monsters through its `questMaterial`, so the journal and map markers still point at them.
- Checks: `cargo test quest_drops`.
