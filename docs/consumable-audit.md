# Consumable audit (CONS-AUDIT)

How the potions and food compare with real characters. Measured on 2026-10-15 with the server's own formulas, nothing estimated by hand:

- **Potion and food numbers** come from the real item catalog (`scripts/consumable_tiers.py`) against characters built by the kill-time harness (normal gear for the level, points spent as in [ttk-rules.md](ttk-rules.md)). `bash scripts/cargo.sh test --offline consumable_audit -- --ignored` writes the rows (`CONS_OUT=path.json`; code in `server/src/world/consumable_audit.rs`): 165 rows for levels 1, 10, 20 ... 90 and 99, five classes, and the even, stamina-heavy and main-stat-heavy spreads.
- **Damage taken** comes from the kill-time harness (`bash scripts/ttk.sh` with `TTK_LEVELS=10,20,30,40,50,60,70,80,90,99 TTK_SPREADS=even,stamina TTK_RUNS=3`): 300 fights against the closest same-level ordinary monster, no consumables. The figure is damage taken per second of the fight, up to the kill or the death. Three seeds per case rather than nine, so read the numbers as magnitudes.
- **Hit sizes** apply the game's rule `max(damage - defense, 1) * 0.25` with the character's real defense. The elite and boss figures use the closest elite or boss of the data, pinned to the level.
- **Gold per hour** assumes one kill every target time (the middle of the [ttk-rules.md](ttk-rules.md) band) plus 10 s of walking. Redo it after `TTK-TUNE` changes the fights.

## Potions and food against max health and mana

The tier is the best one the level allows (`best_tier`). A new tier arrives every ten levels, so the percentages are the **best case** of each decade and sag toward the next tier.

| Level | Health potion heal | Price | % of max HP, even spread (five classes) | % of max HP, stamina-heavy | Mana potion, % of max mana (mage / priest, even; mage, main-stat) | Meal HP per second (8 s) |
| ---: | ---: | ---: | --- | --- | --- | ---: |
| 1 | 100 | 30 | 83–125% | 83–125% | 100% / 100% / 100% | 12 |
| 10 | 210 | 60 | 56–66% | 46–54% | 65% / 65% / 53% | 26 |
| 20 | 350 | 110 | 53–61% | 44–47% | 67% / 67% / 53% | 44 |
| 30 | 490 | 180 | 52–58% | 42–45% | 69% / 68% / 52% | 61 |
| 40 | 630 | 270 | 51–57% | 40–43% | 67% / 67% / 52% | 79 |
| 50 | 770 | 380 | 50–56% | 40–43% | 67% / 66% / 51% | 96 |
| 60 | 910 | 520 | 49–55% | 40–42% | 66% / 66% / 51% | 114 |
| 70 | 1050 | 700 | 48–54% | 38–41% | 65% / 64% / 49% | 131 |
| 80 | 1190 | 900 | 47–53% | 39–41% | 64% / 64% / 49% | 149 |
| 90 | 1330 | 1150 | 46–52% | 38–41% | 63% / 62% / 48% | 166 |
| 99 | 1330 | 1150 | 42–48% | 35–38% | 58% / 58% / 44% | 166 |

- **Too strong:** only level 1. The 100-point potion is 125% of a mage's 80 HP, 111% for an assassin and 105% for a hunter: a full heal with the surplus wasted, for 30 gold.
- **Mana for three classes:** warriors (rage), assassins and hunters (energy) get **nothing** from a mana potion or from the mana part of a meal, and `use_item` refuses the potion ("You cannot restore any mana with this item."). Mana potions are dead stock for three of the five classes, yet every trader lists them.
- **Sag inside a decade:** the heal list was set for about 70% of a warrior's health at the tier's own level. At level 99 the level-90 tier gives 42–48%, and a stamina-heavy character gets 35–38%.
- **Cooldown:** a potion is one use every 60 s (about 13 HP/s at level 50 and 22 HP/s at level 90). A meal heals the same total over 8 s, so it is the only item that heals at a pace near monster damage, and it cannot be eaten again while it runs.

## Healing against the damage of the same level

Warrior, even spread, ordinary monster. "Potion buys" is how many seconds of the measured damage rate one potion (or one meal) covers. "Hits to die" is max HP divided by one landed hit.

| Level | Ordinary monster | Fight | Damage per second taken | Potion buys | Ordinary hit of max HP | Hits to die: ordinary / elite / boss | Kill gold per hour | Potion gold per hour (every 60 s) | Share of income |
| ---: | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 10 | crab | 13 s, 3 of 3 killed | 5 | 40.4 s | 10 of 372 | 37.2 / 9.3 / 8.3 | 6,646 | 3,600 | 54% |
| 20 | hydra | 76 s, 2 of 3 killed | 8 | 41.7 s | 29 of 660 | 22.8 / 1.8 / 2.7 | 39,877 | 6,600 | 17% |
| 30 | galehound | 120 s, 0 of 3 killed | 27 | 18.3 s | 57 of 948 | 16.6 / 1.5 / 1.4 | 38,700 | 10,800 | 28% |
| 40 | voidmoth | 120 s, 0 of 3 killed | 55 | 11.5 s | 125 of 1236 | 9.9 / 1.1 / 2.6 | 81,000 | 16,200 | 20% |
| 50 | bronzemantis | 120 s, 0 of 3 killed | 101 | 7.7 s | 356 of 1540 | 4.3 / 5.3 / 2.4 | 159,158 | 22,800 | 14% |
| 60 | saltclaw | 120 s, 0 of 3 killed | 171 | 5.3 s | 652 of 1860 | 2.9 / 0.5 / 0.7 | 295,579 | 31,200 | 11% |
| 70 | ribbongecko | 120 s, 0 of 3 killed | 241 | 4.4 s | 948 of 2180 | 2.3 / 0.4 / 0.7 | 553,263 | 42,000 | 8% |
| 80 | sandhopper | 120 s, 0 of 3 killed | 245 | 4.9 s | 1595 of 2500 | 1.6 / 0.4 / 0.6 | 949,091 | 54,000 | 6% |
| 90 | screeferret | 120 s, 0 of 3 killed | 282 | 4.7 s | 1991 of 2860 | 1.4 / 0.3 / 0.4 | 1,374,545 | 69,000 | 5% |
| 99 | snowstoat | 120 s, 0 of 3 killed | 750 | 1.8 s | 3492 of 3112 | 0.9 / 0.3 / 0.4 | 2,160,000 | 69,000 | 3% |

## Findings

1. **Levels 5–20 are fine.** A potion is 53–66% of health and covers about 40 s of the damage taken. Using one every 60 s costs 54% of income at level 10 and 17% at level 20. The one weak spot is level 1: continuous use (1,800 gold per hour) costs 2.7 times what a level-1 character earns (665).
2. **A potion is useless in a fight from level 60.** It buys 5.3 s of damage at level 60, 4.4 s at 70 and 1.8 s at 99, against a 60 s cooldown. From level 40 it covers under 12 s.
3. **The fights are the problem, not the potions.** In normal gear no class kills its same-level ordinary monster from level 30 up within 120 s (at level 20 the warrior needs 76 s and one seed in three fails). At level 99 one ordinary hit does 3,492 damage to a 3,112-HP warrior, so one hit kills. At level 90 it takes 1.4 hits and at level 70 2.3. Elites and bosses of the same level kill in 0.3–5 hits from level 20 up. No potion size fixes that, so `CONS-RULES` should wait for `TTK-TUNE`, and the audit should then be repeated.
4. **Potion prices are small against income.** Using a potion every 60 s costs 14% of kill gold at level 50 and 3% at level 99. Price is not the limiter above level 20; the 60 s cooldown and the bag are.
5. **Meals** heal 12 HP/s at level 1 and 166 HP/s at level 90. They are the right size for the first 40 levels and below the damage rate from level 50 (about 100 HP/s) up.
6. **Stamina-heavy characters** have 1.2–1.3 times the health but the same potion, so its percentage falls by about 10 points. They take the same damage per hit, so they gain survival time, not potion value.

## Problems to fix when `CONS-RULES` runs

| Problem | Levels | Observation |
| --- | --- | --- |
| Potion too strong | 1 | 105–125% of health for mage, assassin and hunter |
| Potion useless | 60–99 | Buys 1.8–5.3 s of damage; 60 s cooldown |
| Meal outpaced | 50–99 | 96–166 HP/s against 100–750 HP/s of damage |
| Mana potion dead stock | all | No effect for warrior, assassin, hunter |
| Gold | 1 | Continuous use costs 2.7 times the income |
| Same-level fights unwinnable | 30–99 | See `TTK-RUN` and `TTK-TUNE` |
