# Skill ranks and milestones through level 99

Each class keeps its ten existing active abilities, now learned at levels
4, 8, 12, …, 40. The names, IDs, icons and resource costs stay stable. Each
ability gains rank 2 two levels after it is learned, at levels 6, 10, …, 42.
Level 2 grants no active skill. Ranks are derived from the saved level, so
existing characters receive their earned skills and ranks on their next
session without a save migration. Saved skillbar assignments to skills that
are temporarily locked remain in place and become usable at their new level.

| Class | 4 | 8 | 12 | 16 | 20 | 24 | 28 | 32 | 36 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Warrior | Cleave | Battle Cry | Shield Wall | Whirlwind | Charge | Ground Slam | Second Wind | Berserk | Earthshatter | Titan's Wrath |
| Mage | Twin Bolt | Arcane Ward | Fireball | Arcane Barrage | Blink | Chain Lightning | Meteor | Life Drain | Arcane Storm | Starfall |
| Assassin | Throwing Knives | Evasion | Lunge | Flurry | Shadow Veil | Cyclone Blades | Assassinate | Deadly Focus | Knife Ring | Thousand Cuts |
| Priest | Mend | Smite | Ward of Light | Prayer of Healing | Holy Nova | Blessing of Might | Guardian Light | Searing Light | Divine Hymn | Heaven's Wrath |
| Hunter | Power Shot | Multi-Shot | Roll Away | Piercing Arrow | Hunter's Mark | Explosive Arrow | Rapid Fire | Rain of Arrows | Eagle Sight | Arrow Storm |

Rank 2 increases damage, healing or buff strength by 20%. Blink and Roll
Away have no damaging effect, so their rank reduces their cooldown by 15%.
The 42–60 rotation follows the same columns in the table: Twin Bolt and Cleave
receive rank 3 at 42, and Starfall and Titan's Wrath at 60. Level 42 also grants
rank 2 of the level-40 skill. Rank 3 is 40% stronger
than the base damage, healing or buff effect; Blink and Roll Away gain a 30%
shorter cooldown than their base cooldown.
All five classes receive rank 4 at levels 62–80 in the same order,
in catalog order. Rank 4 is 60% stronger than
the base damage, healing or buff effect. Blink and Roll Away have a 45% shorter base cooldown.
All five classes receive rank 5 at levels 82–98 for their first nine abilities.
It is 80% stronger than the base effect; Blink and Roll Away have a 60% shorter
cooldown. Each class's level-40 skill receives its final rank at level 99 as a
capstone, doubling its base damage and showing a distinct cast flourish.
Server combat uses the highest earned rank. The skill library shows its current
rank and next unlock; the level-up banner announces a rank instead of a new
skill. Each rank's multipliers are relative to the base skill, not compounded
with earlier ranks. `scripts/extend_skill_ranks.py` regenerates these rows
idempotently in `world/skills.txt`.

Every class also earns a separate automatic passive at levels 10, 20, …, 90.
The 45 distinct names and stat grants are in `scripts/generate_passives.py`,
which writes `world/passives.txt`; `scripts/sync-world.cjs` writes the client
catalog. The server adds earned bonuses to effective attributes, alongside
trained and worn stats. They cost no trained points, need no skillbar slot, and
are derived from saved class and level on login. The skill library shows earned
and future passives, and level-up events name newly earned passives.

The high-level skill identity pass changes five existing IDs without touching
saved bar assignments: Earthshatter is a directional fissure, Starfall lands in
a distant area, Thousand Cuts sweeps a broad blade fan, Guardian Light is an
emergency self heal, and Arrow Storm strikes all enemies around the hunter.
Their cooldowns, descriptions and cast effects follow these new roles.
