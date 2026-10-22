# Dungeon set bonus matrix

This is the live catalog for the five class set tasks. The set keys are the
`source` values on exclusive equipment in `world/items.txt`; skill IDs are
from `world/skills.txt`. `scripts/set_bonuses.py` validates this matrix and
generates the shared Rust/client catalog when `scripts/sync-world.cjs` runs.

The eight categories are armor, headgear, shoulders, gloves, weapon, pants,
necklace and accessory. The two physical accessory slots count as one
category. A piece belongs to its catalog source regardless of copy rarity,
roll or refinement; an orange piece has no dungeon source. Only usable gear
for the character's class and level counts. Tiers are cumulative and update
from worn gear on every snapshot and skill cast, including after login.
Undervault's Choirbone Pendant is the eighth kind and drops from the Hollow
King; it reuses Moonstone Necklace art and needs no new sprite.

Each row describes the cumulative 2, 4, 6 and 8-piece tiers. The 2-piece
column grants its listed percentage to the character's derived attribute;
attack and defense mean the final combat values, while health and resource
mean their maxima. The 4-piece column reduces the named skill's final
cooldown by 15%. The 6-piece column doubles the named skill's effective
damage or healing **after its earned rank**, without doubling its duration,
range, number of targets, resource cost, or any lifesteal fraction. For
multi-hit skills it doubles the damage of the whole cast, not each hit twice.
The 8-piece column names the skill that triggers the set's signature in the
first table. A signature triggers at most once per cast and has its own
20-second cooldown, starts after the triggering skill succeeds, and cannot
trigger other set signatures. Its damage uses the caster's ordinary basic-hit
damage before critical hits; its healing uses the recipient's maximum health.
The balance target is for an eight-piece set to outperform an equal-level,
equal-rarity 4+4 mix in the set's intended skill rotation, while the mix
remains useful when its cooldown and stat perks match a player's build.
Higher-rarity off-set gear can still win on raw stats. This avoids making a
full set mandatory for every encounter.

## Signature effects at eight pieces

| Set source | Dungeon | Signature, triggered by the class skill in the last column |
| --- | --- | --- |
| `chained_forge` | The Chained Forge | **Unbroken resolve:** the caster gains a 4-second shield absorbing 4% of maximum health and recovers 3% of maximum resource. |
| `blackhour` | The Black Hour Foundry | **Cold restart:** the caster gains a 4-second shield absorbing 5% of maximum health and recovers 2% of maximum resource. |
| `longship` | The Drowned Longship | **Bilge pump:** the caster recovers 3% of maximum health and 3% of maximum resource. |
| `nornroot` | Nornroot Barrow | **Second thread:** the caster recovers 4% of maximum health. |
| `skybridge` | The Shattered Span | **Prism arc:** the nearest enemy within four tiles takes 16% basic-hit damage. |
| `undervault` | Undervault | **Hollow guard:** the caster gains a 4-second shield absorbing 6% of maximum health. |
| `cathedral_cloister` | Flooded Cloister | **Undertow:** the nearest enemy within four tiles is pulled one tile toward the caster; bosses instead lose 20% movement speed for two seconds. |
| `cathedral_reliquary` | Coral Reliquary | **Coral bond:** the lowest-health nearby party member gains a 4-second shield absorbing 5% of their maximum health. |
| `cathedral_nave` | Grand Nave | **Choir pulse:** each party member within four tiles, including the caster, recovers 3% of their own maximum health. |
| `moonwell` | Moonwell | **Lunar draw:** restore 5% of the caster's maximum mana, rage or energy, capped at its ordinary maximum. |
| `eye_below` | The Eye Below | **Storm fork:** up to two other enemies within four tiles take 12% basic-hit damage each. |
| `elder_hollow` | The Elder Hollow | **Briar hold:** the nearest nonboss enemy within four tiles is rooted for 0.8 seconds; a boss is slowed by 15% for two seconds. |
| `thousandfold` | The Thousandfold Pavilion | **Mirror return:** after 0.6 seconds the triggering skill repeats 20% of its damage or healing on the same valid targets, with no extra resource cost or secondary effects. |
| `rain_crown` | Temple of the Rain Crown | **Rain veil:** the caster takes 12% less ranged damage for four seconds. |
| `seed_vault` | The Seed Vault | **Germination:** a seed at the skill's target point bursts after one second, dealing 15% basic-hit damage to enemies within two tiles. |
| `sunken_astrolabe` | The Sunken Astrolabe | **Orbiting star:** a star orbits the caster for three seconds, then hits the nearest enemy within five tiles for 18% basic-hit damage; it expires harmlessly if none is in range. |
| `thunderheart_gate` | The Thunderheart Gate | **Thunderbreak:** interrupt the nearest enemy windup within four tiles and delay its next attack by 0.5 seconds; bosses only suffer the delay. |
| `blooming_labyrinth` | The Blooming Labyrinth | **Spring pollen:** the lowest-health party member within five tiles recovers 4% of maximum health evenly over four seconds. |
| `solar_crucible` | The Solar Crucible | **Afterglow:** the nearest enemy within four tiles burns for 18% basic-hit damage over three seconds. |
| `amber_archive` | The Amber Archive | **Stored moment:** the caster's next different skill used within five seconds receives a 10% reduction to that cast's cooldown. |
| `silent_solstice` | The Silent Solstice | **Stillness:** the first incoming attack against the caster within two seconds deals 20% less damage; the effect then ends. |

If a signature requires a target and none is valid, it does nothing and does
not begin its 20-second timer. Damage, shields and healing obey their normal
caps and the normal party/zone visibility rules. Pull, root, slow and attack
delay never move a boss or a player. PvP uses the ordinary basic attack path,
which receives derived 2-piece stats but cannot trigger a skill signature.
Signature damage and control target enemies only.

## Warrior (`SET-WARRIOR`)

| Source | 2 pieces | 4-piece cooldown | 6-piece double | 8-piece trigger |
| --- | --- | --- | --- | --- |
| `chained_forge` | +5% attack | `battlecry` | `cleave` | `earthshatter` |
| `blackhour` | +5% attack | `titanswrath` | `earthshatter` | `whirlwind` |
| `longship` | +5% defense | `secondwind` | `whirlwind` | `battlecry` |
| `nornroot` | +5% health | `shieldwall` | `cleave` | `battlecry` |
| `skybridge` | +5% attack | `groundslam` | `whirlwind` | `charge` |
| `undervault` | +5% defense | `shieldwall` | `cleave` | `charge` |
| `cathedral_cloister` | +5% health | `charge` | `whirlwind` | `groundslam` |
| `cathedral_reliquary` | +5% defense | `secondwind` | `earthshatter` | `shieldwall` |
| `cathedral_nave` | +5% attack | `battlecry` | `titanswrath` | `secondwind` |
| `moonwell` | +5% resource | `berserk` | `groundslam` | `battlecry` |
| `eye_below` | +5% attack | `earthshatter` | `cleave` | `charge` |
| `elder_hollow` | +5% health | `shieldwall` | `whirlwind` | `earthshatter` |
| `thousandfold` | +5% attack | `whirlwind` | `titanswrath` | `cleave` |
| `rain_crown` | +5% defense | `shieldwall` | `groundslam` | `berserk` |
| `seed_vault` | +5% health | `secondwind` | `cleave` | `charge` |
| `sunken_astrolabe` | +5% attack | `earthshatter` | `whirlwind` | `titanswrath` |
| `thunderheart_gate` | +5% attack | `charge` | `earthshatter` | `groundslam` |
| `blooming_labyrinth` | +5% health | `secondwind` | `titanswrath` | `battlecry` |
| `solar_crucible` | +5% attack | `berserk` | `earthshatter` | `whirlwind` |
| `amber_archive` | +5% resource | `battlecry` | `groundslam` | `secondwind` |
| `silent_solstice` | +5% defense | `shieldwall` | `cleave` | `earthshatter` |

## Mage (`SET-MAGE`)

| Source | 2 pieces | 4-piece cooldown | 6-piece double | 8-piece trigger |
| --- | --- | --- | --- | --- |
| `chained_forge` | +5% attack | `arcaneward` | `fireball` | `arcanestorm` |
| `blackhour` | +5% attack | `meteor` | `barrage` | `starfall` |
| `longship` | +5% defense | `arcaneward` | `barrage` | `lifedrain` |
| `nornroot` | +5% health | `blink` | `twinbolt` | `fireball` |
| `skybridge` | +5% attack | `chainlightning` | `fireball` | `blink` |
| `undervault` | +5% defense | `arcaneward` | `twinbolt` | `blink` |
| `cathedral_cloister` | +5% health | `blink` | `barrage` | `arcanestorm` |
| `cathedral_reliquary` | +5% defense | `arcaneward` | `chainlightning` | `meteor` |
| `cathedral_nave` | +5% attack | `arcanestorm` | `starfall` | `twinbolt` |
| `moonwell` | +5% resource | `lifedrain` | `fireball` | `arcaneward` |
| `eye_below` | +5% attack | `chainlightning` | `meteor` | `barrage` |
| `elder_hollow` | +5% health | `blink` | `lifedrain` | `fireball` |
| `thousandfold` | +5% attack | `barrage` | `starfall` | `chainlightning` |
| `rain_crown` | +5% defense | `arcaneward` | `arcanestorm` | `blink` |
| `seed_vault` | +5% health | `meteor` | `twinbolt` | `fireball` |
| `sunken_astrolabe` | +5% attack | `starfall` | `chainlightning` | `meteor` |
| `thunderheart_gate` | +5% attack | `blink` | `arcanestorm` | `chainlightning` |
| `blooming_labyrinth` | +5% health | `lifedrain` | `meteor` | `arcaneward` |
| `solar_crucible` | +5% attack | `fireball` | `starfall` | `arcanestorm` |
| `amber_archive` | +5% resource | `arcaneward` | `lifedrain` | `starfall` |
| `silent_solstice` | +5% defense | `blink` | `twinbolt` | `arcaneward` |

## Assassin (`SET-ASSASSIN`)

| Source | 2 pieces | 4-piece cooldown | 6-piece double | 8-piece trigger |
| --- | --- | --- | --- | --- |
| `chained_forge` | +5% attack | `evasion` | `flurry` | `knifering` |
| `blackhour` | +5% attack | `thousandcuts` | `cycloneblades` | `assassinate` |
| `longship` | +5% defense | `shadowveil` | `throwingknives` | `deadlyfocus` |
| `nornroot` | +5% health | `evasion` | `flurry` | `lunge` |
| `skybridge` | +5% attack | `cycloneblades` | `flurry` | `evasion` |
| `undervault` | +5% defense | `evasion` | `flurry` | `shadowveil` |
| `cathedral_cloister` | +5% health | `lunge` | `cycloneblades` | `knifering` |
| `cathedral_reliquary` | +5% defense | `shadowveil` | `throwingknives` | `evasion` |
| `cathedral_nave` | +5% attack | `deadlyfocus` | `thousandcuts` | `flurry` |
| `moonwell` | +5% resource | `evasion` | `knifering` | `shadowveil` |
| `eye_below` | +5% attack | `throwingknives` | `assassinate` | `lunge` |
| `elder_hollow` | +5% health | `shadowveil` | `flurry` | `assassinate` |
| `thousandfold` | +5% attack | `flurry` | `thousandcuts` | `assassinate` |
| `rain_crown` | +5% defense | `evasion` | `cycloneblades` | `deadlyfocus` |
| `seed_vault` | +5% health | `knifering` | `throwingknives` | `lunge` |
| `sunken_astrolabe` | +5% attack | `thousandcuts` | `knifering` | `assassinate` |
| `thunderheart_gate` | +5% attack | `lunge` | `assassinate` | `cycloneblades` |
| `blooming_labyrinth` | +5% health | `evasion` | `assassinate` | `shadowveil` |
| `solar_crucible` | +5% attack | `deadlyfocus` | `thousandcuts` | `assassinate` |
| `amber_archive` | +5% resource | `shadowveil` | `cycloneblades` | `knifering` |
| `silent_solstice` | +5% defense | `evasion` | `throwingknives` | `shadowveil` |

## Priest (`SET-PRIEST`)

| Source | 2 pieces | 4-piece cooldown | 6-piece double | 8-piece trigger |
| --- | --- | --- | --- | --- |
| `chained_forge` | +5% health | `mend` | `smite` | `prayer` |
| `blackhour` | +5% health | `heavenswrath` | `searinglight` | `divinehymn` |
| `longship` | +5% defense | `guardianlight` | `searinglight` | `prayer` |
| `nornroot` | +5% health | `wardoflight` | `smite` | `prayer` |
| `skybridge` | +5% attack | `blessing` | `holynova` | `smite` |
| `undervault` | +5% defense | `wardoflight` | `smite` | `holynova` |
| `cathedral_cloister` | +5% health | `prayer` | `holynova` | `mend` |
| `cathedral_reliquary` | +5% defense | `wardoflight` | `mend` | `prayer` |
| `cathedral_nave` | +5% attack | `divinehymn` | `heavenswrath` | `holynova` |
| `moonwell` | +5% resource | `blessing` | `searinglight` | `divinehymn` |
| `eye_below` | +5% attack | `searinglight` | `heavenswrath` | `smite` |
| `elder_hollow` | +5% health | `guardianlight` | `prayer` | `wardoflight` |
| `thousandfold` | +5% attack | `holynova` | `smite` | `heavenswrath` |
| `rain_crown` | +5% defense | `wardoflight` | `divinehymn` | `guardianlight` |
| `seed_vault` | +5% health | `prayer` | `mend` | `searinglight` |
| `sunken_astrolabe` | +5% attack | `heavenswrath` | `searinglight` | `smite` |
| `thunderheart_gate` | +5% attack | `smite` | `holynova` | `heavenswrath` |
| `blooming_labyrinth` | +5% health | `guardianlight` | `divinehymn` | `prayer` |
| `solar_crucible` | +5% attack | `searinglight` | `heavenswrath` | `holynova` |
| `amber_archive` | +5% resource | `blessing` | `prayer` | `mend` |
| `silent_solstice` | +5% defense | `wardoflight` | `mend` | `guardianlight` |

## Hunter (`SET-HUNTER`)

| Source | 2 pieces | 4-piece cooldown | 6-piece double | 8-piece trigger |
| --- | --- | --- | --- | --- |
| `chained_forge` | +5% attack | `eaglesight` | `powershot` | `arrowstorm` |
| `blackhour` | +5% attack | `arrowstorm` | `multishot` | `piercingarrow` |
| `longship` | +5% defense | `rollaway` | `explosivearrow` | `huntersmark` |
| `nornroot` | +5% health | `rollaway` | `powershot` | `huntersmark` |
| `skybridge` | +5% attack | `rapidfire` | `piercingarrow` | `rollaway` |
| `undervault` | +5% defense | `huntersmark` | `powershot` | `multishot` |
| `cathedral_cloister` | +5% health | `rollaway` | `multishot` | `rainofarrows` |
| `cathedral_reliquary` | +5% defense | `huntersmark` | `piercingarrow` | `eaglesight` |
| `cathedral_nave` | +5% attack | `rapidfire` | `arrowstorm` | `powershot` |
| `moonwell` | +5% resource | `eaglesight` | `explosivearrow` | `rapidfire` |
| `eye_below` | +5% attack | `piercingarrow` | `powershot` | `multishot` |
| `elder_hollow` | +5% health | `rollaway` | `rainofarrows` | `huntersmark` |
| `thousandfold` | +5% attack | `multishot` | `arrowstorm` | `rainofarrows` |
| `rain_crown` | +5% defense | `eaglesight` | `rainofarrows` | `rollaway` |
| `seed_vault` | +5% health | `explosivearrow` | `multishot` | `piercingarrow` |
| `sunken_astrolabe` | +5% attack | `arrowstorm` | `powershot` | `eaglesight` |
| `thunderheart_gate` | +5% attack | `piercingarrow` | `explosivearrow` | `arrowstorm` |
| `blooming_labyrinth` | +5% health | `huntersmark` | `rainofarrows` | `rapidfire` |
| `solar_crucible` | +5% attack | `explosivearrow` | `arrowstorm` | `powershot` |
| `amber_archive` | +5% resource | `rapidfire` | `multishot` | `huntersmark` |
| `silent_solstice` | +5% defense | `rollaway` | `piercingarrow` | `eaglesight` |

There are 17 sources and ten skills per class. A literal rule forbidding a
skill from appearing at the same tier in any two sets is impossible for 17
sets. Uniqueness therefore means that each class has 17 distinct ordered
combinations of cooldown skill, doubled skill and trigger skill. Every
signature also has a different mechanic. The generator and Rust catalog test
assert these rules from the matrix.
