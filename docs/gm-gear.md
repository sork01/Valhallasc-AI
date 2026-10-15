# Game master gear rules

These settle `GM-GEAR-RULES` in [TODO.md](../TODO.md). `GM-GEAR-DATA` raises the pieces, `GM-GEAR-SERVER` adds the combat rule and `GM-GEAR-CHECK` verifies it.

## Why gear stats alone cannot do it

The GM (always the male Warrior created by `Character::become_gm`) wears the Golden Robe (defense 12), the Golden Top Hat (defense 4) and the Golden Sword & Shield (attack 10,020, defense 10,004). A player hit is `attack × DAMAGE_DEALT_SCALE (0.25) × (0.8–1.2)`, so the sword deals about 2,500 per hit. The strongest monster in the data, the Longnight Wyrm, has 8,100,000 HP at its default level (the next are the Amber Mantis at 7,600,000 and the Fire Phoenix at 7,100,000), and monsters gain 12% HP per level above their default. One hit would need an attack stat near 100 million, which is a display number nobody can read and an overflow risk when it multiplies against stats and crits. So the one-hit kill is a **combat rule**, and the gear is raised only for defense.

## Rule: the GM strike

- **Where:** `World::hit_slime`, the single entry point for every player-to-enemy hit (basic attacks, bolts, area skills, damage over time and cast effects all use it). The rule is applied at the top, before the miss check.
- **Who:** only when the attacker's own character has `gm == true` **and** wears the `gm`-rarity weapon (`warrior_weapon_gm`). The test is read from server state, never from a client message. A mercenary the GM hires is a different session with its own character, so it gets nothing; its kills still credit its hirer as today.
- **What:** the damage becomes `max(rolled damage, the target's current HP)` and the hit never misses and never dodges. The target dies from exactly its own HP, so there is no overkill number to overflow. Because it uses the target's current HP, a boss with the most HP still dies in one hit, and so would a future boss with more.
- **Every damaging skill** one-shots, not only the basic attack: an area skill kills every enemy it hits, one floor per target.
- **Credit is unchanged:** XP (including the boss multiplier), gold, drops, quest progress, party sharing and contributor lists all run through the normal kill path.
- **Margin the test must show:** at the highest-HP spawn at its top rolled level (derived from the data, not hard-coded), the GM's damage is at least that monster's `max_hp`.

## Exceptions (written down, tested)

| Target | GM strike? | Reason |
| --- | --- | --- |
| Other players, duels, opt-in PvP and arena matches | No | Normal formula only. The GM does not one-shot players; there is no opt-in switch. |
| Mercenaries and NPCs | No | They are not enemies. |
| Any enemy marked invulnerable, scripted shield or immune phase | No, the hit does the normal damage | The data currently has no such enemy and no training dummy; if one is added it must set the flag the GM strike checks. |
| Dead targets, targets in another zone | No | `hit_slime` already refuses them. |

## Rest of the kit

- **Movement speed, attack speed, mana and rage:** unchanged. The GM is not special-cased beyond the strike and defense; no skill becomes free.
- **Cooldowns:** unchanged. The one-hit rule removes the need.
- **Damage taken:** raised through gear (below), with the existing `(damage − defense) × DAMAGE_TAKEN_SCALE` formula. Total defense must beat the highest monster damage stat (49,000 at default level, more after the 12% per level scaling) by at least 3 times so every hit floors at the 1-damage minimum: **target total defense 150,000**.
- Debug god mode (`set_god_mode`) stays an unrelated tool.

## Gear data (`GM-GEAR-DATA`)

Keep the item IDs, the `gm` rarity (never rolled, never sold or dropped, cannot be sent to or received by another player) and the saves. The target defense per piece, summing to 150,004 with the existing weapon:

| Slot | Item | Defense |
| --- | --- | ---: |
| Armor | Golden Robe of the Game Master (existing id `warrior_armor_gm`) | 40,000 |
| Headgear | Golden Top Hat (existing) | 25,000 |
| Shoulders | new `warrior_shoulders_gm` | 15,000 |
| Gloves | new `warrior_gloves_gm` | 15,000 |
| Pants | new `gm_pants` (class-independent) | 25,000 |
| Necklace | new `gm_necklace` | 10,000 |
| Accessory | new `gm_accessory` | 10,000 |
| Weapon | Golden Sword & Shield (existing) | 10,004 (attack stays 10,020) |

New pieces carry `gm` rarity, `requiredLevel` 1 and `sell` 0, golden art and 48×48 icons made through PixelFlow in the same family as the existing three. Attack stays on the weapon only, since the strike makes extra attack pointless. `GM_GEAR` in `server/src/items.rs` lists every new id so `become_gm` grants them and the existing GM save receives them on load.

## Checks (`GM-GEAR-CHECK`)

- A private world with a GM account and a normal account: the GM kills the highest-HP monster of every zone and dungeon in one hit; the normal character's damage and misses are unchanged.
- A normal character holding a copy of a GM piece is refused (`GM_GEAR` equip is GM-only) and cannot receive it by trade.
- The GM hits another player with normal damage in a duel, opt-in PvP and an arena match.
- The GM's total defense meets the target, the highest-damage monster hit floors at 1, and the largest HP and attack values do not overflow, wrap or produce NaN.
- A mercenary hired by the GM does not one-shot.
