# Consumable balance rules

These rules follow the post kill-time calibration audit in [consumable-audit.md](consumable-audit.md). The catalog supplies a **flat minimum**. A health potion restores `max(item.heal, round(0.40 × character.max_hp))` immediately, capped at full health. A meal restores the same total evenly over eight seconds. This makes a saved low-tier stack useful after leveling without changing its ID. The level-one flat heal is 60 instead of 100; the remaining existing flat values and item IDs stay in place.

One food effect may run at a time, and every meal tier shares one **30-second** cooldown (`cooldown` in the catalog, counted from the start of the meal, so 22 seconds remain after the 8-second meal ends). Switching to another tier or family of food cannot start a second meal early. The cooldown is server-owned, saved as a wall-clock second (`Character.meal_ready`) so logging out or a restart cannot skip it, and sent to the client as `mealCd`; bags and the quick slot show the remaining seconds. A refused meal is not consumed. The meal itself is not saved, so a relog mid-meal loses the rest of the healing but not the wait. A potion may be drunk during a meal or its cooldown, so their health and resource restoration add, subject to the normal maximums. Health and resource potions continue to share one persistent **60-second** cooldown. The cooldown starts when a potion is used, survives logout and restart, and applies in world PvP, duels and arenas exactly as in PvE. Meals have the same one-at-a-time rule in those modes; no mode bypasses the server's life, level, ownership, fullness or cooldown checks. Resource amounts follow the existing rule: mana uses the catalog flat amount; rage and energy use its tier-scaled share of the 100-point cap.

All merchants with a `tiered` family offer automatically sell the highest tier the buyer's level permits, at that item's price. Existing stacks, quick-slot family selection and item IDs remain valid. The new 95 and 99 tiers add a final choice near the level cap. No intermediate health tier is needed: the 40% floor prevents the decade sag shown in the original audit; mana remains 48–73% of the pool for mana classes at levels 10–99. Inventory icons retain the family glyph and colour, with a rarity ring and a level number on the two final tiers.

| Required level | Health flat floor | Mana/resource catalog | Potion gold | Meal gold | Potion and meal rarity |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 60 | 100 | 5 | 3 | common |
| 10 | 210 | 170 | 60 | 25 | uncommon |
| 20 | 350 | 300 | 110 | 45 | rare |
| 30 | 490 | 430 | 180 | 75 | epic |
| 40 | 630 | 550 | 270 | 115 | legendary |
| 50 | 770 | 680 | 380 | 165 | legendary |
| 60 | 910 | 810 | 520 | 225 | legendary |
| 70 | 1050 | 930 | 700 | 300 | legendary |
| 80 | 1190 | 1060 | 900 | 390 | legendary |
| 90 | 1330 | 1190 | 1150 | 500 | legendary |
| 95 | 1400 | 1260 | 1275 | 550 | legendary |
| 99 | 1460 | 1320 | 1400 | 600 | legendary |

At any level from 1 through 99, use the row with the greatest required level no higher than the character's level. Health restoration is then the larger of that row's floor and 40% of the character's current maximum health. This is the full curve, including levels between rows. Prices preserve existing tiers and rise moderately at 95 and 99. The post-balance audit finds the cost of drinking one potion every minute at 45% of level-one ordinary kill gold income, 34% at level 10 and at most 28% from level 20 onward; actual need is lower in ordinary fights because the kill-time grid completes those fights without a potion.
