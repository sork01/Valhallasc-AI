# Plan to fix the kill times

Measured on 2026-10-15 with the kill-time harness ([ttk-rules.md](ttk-rules.md), [ttk-report.md](ttk-report.md)). The class kill speed comes from fights where the monster deals no damage (`TTK_HARMLESS=1 bash scripts/ttk.sh`, three seeds, even spread, the **green** baseline gear); the damage numbers come from the normal fights. Targets are the middle of each band of `ttk-rules.md`: 22.5 s up to level 20, 30 s for 25 to 45, 37.5 s for 50 to 75, 45 s for 80 to 99, and a character that never drops under 60% of its health on the way (40% of max HP is the damage budget).

Baseline gear: **green**, decided 2026-10-15 (`BASELINE_RARITY` in `server/src/world/ttk.rs`). The earlier gray measurements differ by only a few percent.

## Decision: bring the monsters down and level out the classes; do not raise the players

From level 10 to level 99 the players grow slowly and the monsters grow explosively:

| Level 10 to 99 | Grows by |
| --- | --- |
| Warrior damage per second | about 12 times (82 to 980) |
| Warrior max health | about 8 times (372 to 3,112) |
| Monster health (ordinary, same level) | about 1,270 times (900 to 1,142,400) |
| Monster hit on the warrior | about 390 times (9 to 3,484) |

Raising the players enough to meet that is a hundredfold change, and it would also move PvP, gear and refinement values, orange and set pieces, potion sizes and every saved character. The monsters are data: `Slime::stats` and the zone files. Changing them touches no item ID, no save and no PvP rule. So the fix is on the monster side, plus one player-side change: the classes are far apart, and that must be levelled first because "the" kill time means nothing while a warrior needs 3 to 5 times as long as a mage.

## What the numbers say

Damage dealt per second by each class against a harmless same-level monster, and what the monster would have to be for the middle class to hit the target:

| Level | Warrior | Mage | Assassin | Priest | Hunter | Spread | Median | Monster HP now | Target HP | Change |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 82 | 63 | 80 | 75 | 86 | 1.4x | 80 | 900 | 1,800 | 2.0x up |
| 20 | 69 | 164 | 62 | 157 | 160 | 2.6x | 157 | 5,200 | 3,532 | 0.68x |
| 30 | 122 | 257 | 94 | 303 | 303 | 3.2x | 257 | 12,500 | 7,710 | 0.62x |
| 40 | 206 | 353 | 137 | 424 | 454 | 3.3x | 353 | 30,000 | 10,590 | 0.35x |
| 50 | 307 | 456 | 222 | 565 | 593 | 2.7x | 456 | 90,000 | 17,100 | 0.19x |
| 60 | 404 | 658 | 252 | 815 | 767 | 3.2x | 658 | 185,000 | 24,675 | 0.13x |
| 70 | 527 | 988 | 336 | 1,156 | 944 | 3.4x | 944 | 290,000 | 35,400 | 0.12x |
| 80 | 620 | 1,319 | 413 | 1,470 | 1,204 | 3.6x | 1,204 | 475,000 | 54,180 | 0.11x |
| 90 | 864 | 1,805 | 529 | 1,805 | 1,465 | 3.4x | 1,465 | 650,000 | 65,925 | 0.10x |
| 99 | 980 | 2,582 | 544 | 2,323 | 1,533 | 4.7x | 1,533 | 1,142,400 | 68,985 | 0.06x |

Monster damage, for the warrior in normal gear (the same cut keeps the other classes inside budget, since they have a similar health pool):

| Level | Raw damage now | Damage per hit now | Measured damage per second | Raw damage target | Change |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 60 | 9 | 5 | 60 | none |
| 20 | 150 | 27 | 8 | 150 | none |
| 30 | 275 | 54 | 25 | 169 | 0.61x |
| 40 | 560 | 121 | 55 | 221 | 0.39x |
| 50 | 1,500 | 352 | 101 | 322 | 0.21x |
| 60 | 2,700 | 647 | 171 | 412 | 0.15x |
| 70 | 3,900 | 943 | 241 | 493 | 0.13x |
| 80 | 6,500 | 1,588 | 245 | 724 | 0.11x |
| 90 | 8,100 | 1,983 | 282 | 882 | 0.11x |
| 99 | 14,112 | 3,484 | 750 | 690 | 0.05x |

(The hit is `(raw - defense) * 0.25` and defense is only 24 to 176 across these levels, so raw damage and the hit scale almost together.)

## Steps, in order

1. **Level out the classes (`TTK-FIX-CLASSES`).** Bring each class's damage per second at each level to the five-class median above. It is the warrior and the assassin that lag (by 2.3 and 2.5 times at level 20, 1.6 and 2.8 times at 99); the mage and priest are above the median from the 70s and need a small cut. The levers are the skill `mult` numbers and class base attack (`world/skills.txt`, `scripts/extend_skill_ranks.py`, `Look::stats`), never item IDs. Re-measure with `TTK_HARMLESS=1` until the spread is under 1.3 times at every level.
2. **Fit the monsters to one curve (`TTK-FIX-DAMAGE`, `TTK-FIX-SPEED`).** Do not edit hundreds of kinds. Add one table, keyed by default level, with a health multiplier and a damage multiplier, applied where a monster's stats are built (`Slime::stats`/`with_level`). Fill it from the target columns above (interpolate between the measured levels). Elites and bosses keep their ratio to the ordinary monster of their level, so a boss stays a group fight. A ratio test then guards the table: for example, no same-level boss kills a full-health character in fewer than 4 hits.
3. **Re-run the grid** (`TTK_RUNS=9 bash scripts/ttk-parallel.sh`, 41 minutes) and adjust the table. Done when no case from level 25 up fails, the medians are inside their bands, and no character finishes under 20% health.
4. **Make the report a test (`TTK-CHECK`)** with the bands as assertions.
5. **Then size the consumables (`CONS-RULES` and the `CONS-FIX-*` tasks).** Potions are meaningless while a hit can take 100% of the health; once the damage is on target, a percentage-based heal can be judged.

## Risks to check on the way

- **Experience and gold per hour.** Kills pay `45 + 5 * level` XP and a per-kind gold amount, independent of health. If a level-50 monster dies in 37 seconds instead of never, kills become the main way to level and to earn. Re-derive XP per hour and gold per hour from the new kill times before releasing, and rescale the per-kill rewards if the economy runs fast.
- **Dungeons, elites and bosses** were authored against the old curve (the Hollow King has 130,000 health at level 20, 25 times a same-level monster). The multiplier table moves them with their level, so each dungeon's balance tests (`vault_tests`, `cathedral_tests`, the later instance suites) must be re-run and retuned.
- **Level 10 and below are slightly too fast** (6 to 15 s against 15 to 30 s): the table raises monster health there instead of lowering it.
- **Gear matters in play.** The baseline is green (decided 2026-10-15; gray is the floor below it). Blue, purple, orange and set pieces add 17.5% per tier plus bonuses, so a better-geared character kills faster than the table. Green barely moves the numbers against gray (a few percent of damage, about 15% more defense) because attributes, not gear, carry most of a character's damage.

## Questions for the owner

- Are the bands of `ttk-rules.md` still right, in particular 30 s for levels 25 to 45 and 37.5 s for 50 to 75?
- Should the classes be levelled to the median (raising the warrior and assassin, trimming mage and priest slightly) or all raised to the strongest?
