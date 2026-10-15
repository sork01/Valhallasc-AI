# Plan to fix the kill times

Measured on 2026-10-15 with the kill-time harness ([ttk-rules.md](ttk-rules.md), [ttk-report.md](ttk-report.md)). The class kill speed comes from fights where the monster deals no damage (`TTK_HARMLESS=1 bash scripts/ttk.sh`, three seeds, even spread, normal gray gear); the damage numbers come from the normal fights. Targets are the middle of each band of `ttk-rules.md`: 22.5 s up to level 20, 30 s for 25 to 45, 37.5 s for 50 to 75, 45 s for 80 to 99, and a character that never drops under 60% of its health on the way (40% of max HP is the damage budget).

## Decision: bring the monsters down and level out the classes; do not raise the players

From level 10 to level 99 the players grow slowly and the monsters grow explosively:

| Level 10 to 99 | Grows by |
| --- | --- |
| Warrior damage per second | about 11 times (87 to 950) |
| Warrior max health | about 8 times (372 to 3,112) |
| Monster health (ordinary, same level) | about 1,270 times (900 to 1,142,400) |
| Monster hit on the warrior | about 350 times (10 to 3,492) |

Raising the players enough to meet that is a hundredfold change, and it would also move PvP, gear and refinement values, orange and set pieces, potion sizes and every saved character. The monsters are data: `Slime::stats` and the zone files. Changing them touches no item ID, no save and no PvP rule. So the fix is on the monster side, plus one player-side change: the classes are far apart, and that must be levelled first because "the" kill time means nothing while a warrior needs 3 to 5 times as long as a mage.

## What the numbers say

Damage dealt per second by each class against a harmless same-level monster, and what the monster would have to be for the middle class to hit the target:

| Level | Warrior | Mage | Assassin | Priest | Hunter | Spread | Median | Monster HP now | Target HP | Change |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 87 | 63 | 76 | 72 | 81 | 1.4x | 76 | 900 | 1,710 | 1.9x up |
| 20 | 69 | 155 | 60 | 153 | 157 | 2.6x | 153 | 5,200 | 3,440 | 0.66x |
| 30 | 119 | 251 | 91 | 289 | 282 | 3.2x | 251 | 12,500 | 7,530 | 0.60x |
| 40 | 199 | 340 | 133 | 401 | 441 | 3.3x | 340 | 30,000 | 10,200 | 0.34x |
| 50 | 297 | 443 | 216 | 547 | 573 | 2.7x | 443 | 90,000 | 16,600 | 0.18x |
| 60 | 391 | 640 | 245 | 790 | 742 | 3.2x | 640 | 185,000 | 24,000 | 0.13x |
| 70 | 510 | 962 | 327 | 1,121 | 913 | 3.4x | 913 | 290,000 | 34,200 | 0.12x |
| 80 | 600 | 1,319 | 401 | 1,425 | 1,165 | 3.6x | 1,165 | 475,000 | 52,400 | 0.11x |
| 90 | 837 | 1,805 | 515 | 1,805 | 1,420 | 3.5x | 1,420 | 650,000 | 63,900 | 0.10x |
| 99 | 950 | 2,517 | 530 | 2,256 | 1,486 | 4.7x | 1,486 | 1,142,400 | 66,900 | 0.06x |

Monster damage, for the warrior in normal gear (the same cut keeps the other classes inside budget, since they have a similar health pool):

| Level | Raw damage now | Damage per hit now | Measured damage per second | Raw damage target | Change |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 60 | 10 | 5 | 60 | none |
| 20 | 150 | 29 | 8 | 150 | none |
| 30 | 275 | 57 | 27 | 155 | 0.56x |
| 40 | 560 | 125 | 55 | 211 | 0.38x |
| 50 | 1,500 | 356 | 101 | 309 | 0.21x |
| 60 | 2,700 | 652 | 171 | 394 | 0.15x |
| 70 | 3,900 | 948 | 241 | 472 | 0.12x |
| 80 | 6,500 | 1,595 | 245 | 699 | 0.11x |
| 90 | 8,100 | 1,991 | 282 | 856 | 0.11x |
| 99 | 14,112 | 3,492 | 750 | 661 | 0.05x |

(The hit is `(raw - defense) * 0.25` and defense is only 19 to 146 across these levels, so raw damage and the hit scale almost together.)

## Steps, in order

1. **Level out the classes (`TTK-FIX-CLASSES`).** Bring each class's damage per second at each level to the five-class median above. It is the warrior and the assassin that lag (by 2.2 and 2.5 times at level 20, 1.6 and 2.8 times at 99); the mage and priest are above the median from the 70s and need a small cut. The levers are the skill `mult` numbers and class base attack (`world/skills.txt`, `scripts/extend_skill_ranks.py`, `Look::stats`), never item IDs. Re-measure with `TTK_HARMLESS=1` until the spread is under 1.3 times at every level.
2. **Fit the monsters to one curve (`TTK-FIX-DAMAGE`, `TTK-FIX-SPEED`).** Do not edit hundreds of kinds. Add one table, keyed by default level, with a health multiplier and a damage multiplier, applied where a monster's stats are built (`Slime::stats`/`with_level`). Fill it from the target columns above (interpolate between the measured levels). Elites and bosses keep their ratio to the ordinary monster of their level, so a boss stays a group fight. A ratio test then guards the table: for example, no same-level boss kills a full-health character in fewer than 4 hits.
3. **Re-run the grid** (`TTK_RUNS=9 bash scripts/ttk-parallel.sh`, 41 minutes) and adjust the table. Done when no case from level 25 up fails, the medians are inside their bands, and no character finishes under 20% health.
4. **Make the report a test (`TTK-CHECK`)** with the bands as assertions.
5. **Then size the consumables (`CONS-RULES` and the `CONS-FIX-*` tasks).** Potions are meaningless while a hit can take 100% of the health; once the damage is on target, a percentage-based heal can be judged.

## Risks to check on the way

- **Experience and gold per hour.** Kills pay `45 + 5 * level` XP and a per-kind gold amount, independent of health. If a level-50 monster dies in 37 seconds instead of never, kills become the main way to level and to earn. Re-derive XP per hour and gold per hour from the new kill times before releasing, and rescale the per-kill rewards if the economy runs fast.
- **Dungeons, elites and bosses** were authored against the old curve (the Hollow King has 130,000 health at level 20, 25 times a same-level monster). The multiplier table moves them with their level, so each dungeon's balance tests (`vault_tests`, `cathedral_tests`, the later instance suites) must be re-run and retuned.
- **Level 10 and below are slightly too fast** (6 to 15 s against 15 to 30 s): the table raises monster health there instead of lowering it.
- **Gear matters in play.** The test is the floor (gray gear). Green, blue, purple, orange and set pieces add 17.5% per tier plus bonuses, so a real character kills faster than the table; if that proves too fast, set the monster targets for blue gear and keep gray as the lower bound.

## Questions for the owner

- Are the bands of `ttk-rules.md` still right, in particular 30 s for levels 25 to 45 and 37.5 s for 50 to 75?
- Should the classes be levelled to the median (raising the warrior and assassin, trimming mage and priest slightly) or all raised to the strongest?
- Is gray gear the baseline, as the test assumes, or blue?
