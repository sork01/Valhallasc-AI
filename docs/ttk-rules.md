# Kill-time test rules

These settle `TTK-RULES` in [TODO.md](../TODO.md). `TTK-HARNESS` builds the test, `TTK-RUN` produces the table, `TTK-TUNE` fixes outliers and `TTK-CHECK` keeps the bands as assertions. The same numbers feed `CONS-AUDIT`.

## Cases

- **Levels:** 5, 10, 15 … 95 and 99, which is 20 levels. **Classes:** warrior, mage, assassin, priest, hunter. That is 100 cases per variant.
- **Normal gear** is the level's ordinary progression set at **green (uncommon)** rarity in all eight slots (decided 2026-10-15: green is the baseline a character is expected to wear; gray is the floor below it and blue and better add on top) (armor, headgear, shoulders, gloves, weapon, pants, necklace, accessory): the set whose `requiredLevel` is the character's level rounded down to a multiple of 5 (99 uses the level-95 set). It is worn with **no refinement, no merge, no set bonus, no orange or dungeon piece**. The harness takes pieces from `world/items.txt` by `requiredLevel` and `rarity`, so a catalog change moves the test with it.
- **Skills:** the skills and ranks the class has at that level (`docs/skill-ranks.md`), on the skillbar in unlock order, with passives from `skills::passive_bonus`.
- **Attributes:** `3 × (level − 1)` points spent three ways:
  - `even`: the Recommended spread from [recommended-stats.md](recommended-stats.md).
  - `stamina`: 60% stamina, the rest by the Recommended spread.
  - `damage`: 80% the class's main stat (strength, agility or intellect), the rest stamina.
  Accuracy 20 and dexterity 70 caps apply to all three.
- **Target:** an ordinary (non-elite) monster of the same level. The harness picks the enemy kind whose default level is closest to the character level (rolled level pinned to the character's level), and the choice is derived from the data, not listed by hand. Elites are measured too when one exists within two levels, but they are group fights: their time is **reported, not asserted**, and solo deaths against them are not failures.
- **Consumables:** none in the main run. A second run per case allows the best potion and food tier for the level to measure how much consumables change the result (`CONS-AUDIT`).
- **Rotation:** use every damaging skill whenever it is off cooldown and affordable, ordered by highest unlock level first, and a basic attack otherwise. A second run uses basic attack only. Healing, buff and utility skills are used only when they raise damage or are needed to survive (priest heals below 50% HP).
- **What counts as a kill:** the clock runs from the character's first command (including walking in from 8 tiles away and every cooldown wait) to the target's death. Nobody else helps. If the character dies first, the case is a **failure**, recorded with the damage dealt so far, and counts as "too slow".
- **Repetitions:** 9 seeded repetitions per case (seeds 1–9), reported as median with minimum and maximum. All assertions use the median.
- **Isolation:** a private world with the test commands enabled; never the live world or saves.

## Target kill times (median, ordinary same-level monster, main rotation)

| Level band | Target | Too fast | Too slow |
| --- | --- | --- | --- |
| 5–10 | 6–15 s | under 5 s | over 20 s |
| 15–20 | 15–30 s | under 10 s | over 45 s |
| 25–45 | 20–40 s | under 12 s | over 60 s |
| 50–75 | 25–50 s | under 15 s | over 75 s |
| 80–99 | 30–60 s | under 18 s | over 90 s |

The level 5–10 band preserves the early fights after the owner's 2026-10-15 decision to keep every monster stat unchanged and raise player damage and health for later progression. Level 15–20 retains the confirmed 15–30 s pace. Later bands allow longer fights as rotations grow.

Further rules:

- The `damage` and `stamina` variants must stay within 0.6–1.6 times the `even` median (no variant breaks the band by itself).
- The basic-attack-only run must kill within 2.5 times the target ceiling; a class that cannot kill without its skills is flagged.
- At each level the slowest class median must be no more than 1.3 times the fastest class median.
- Damage taken is recorded with every case. A case where the character finishes under 20% HP is flagged even if it is inside the band.

## Report

`TTK-RUN` writes `docs/ttk-report.md`: a table of median seconds by class and level for each variant, the same-level monster's damage per hit against the character, and a flag column. `TTK-CHECK` loads the target bands from one JSON data file shared by the harness and the assertions, so these tables and the test cannot drift.
