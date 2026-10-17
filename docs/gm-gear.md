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
- **Damage taken:** raised through gear (below), with the existing `(damage − defense) × DAMAGE_TAKEN_SCALE` formula. Total defense must beat the highest monster damage stat (49,000 at default level, more after the 12% per level scaling) by at least 3 times so every hit floors at the 1-damage minimum: **target total defense 150,000**. *Superseded by `GM-GEAR-CHECK` (2026-10-17): monster damage grows faster than the 12% HP rule, and the data's hardest hit is 391,200 (Amber Sentinel, level 99), so the total is now 570,004; see "As checked".*
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

## As built (2026-10-17, `GM-GEAR-DATA`)

All eight pieces are in `world/items.txt` with the defense above (total 150,004). `GM_GEAR` has eight ids and `GM_SLOTS` maps the six non-look slots; `become_gm` wears everything, and `grant_missing_gm_gear` (run when a character is loaded) gives an older GM save the new pieces once and wears each one whose slot is empty, so a piece taken off on purpose stays off. Worn art exists only in the **Warrior** atlas (the administrator is always a male Warrior): `shoulders_gm`, `gloves_gm`, `pants_gm`, `necklace_gm`, `accessory_gm`, in PixelFlow groups `gm` (with the robe, hat, blade and pauldrons) and `gm2`, lazy-loaded. The client filter (`pieces()` in `magesprite.js`) accepts the variant of any `gm`-rarity item for its slot; on any other class the layer is simply absent. The greaves sit under the robe's skirt and show only at the boots and in the walk. Icons are in `scripts/make_item_sprites.py`.

## As checked (2026-10-17, `GM-GEAR-CHECK`)

The check found that 150,004 defense did **not** meet the rule: 144 of the 1,968 spawned enemies (the Amber Archive, Solar Crucible and other level 95+ zones) hit harder than that, up to 391,200. The golden pieces were raised in `world/items.txt` (robe 160,000, top hat 100,000, shoulders 60,000, gloves 60,000, pants 100,000, necklace 40,000, accessory 40,000, sword 10,004), a total of **570,004**, and `scripts/sync-world.cjs` regenerated `client/items.js`. The test derives the hardest hit from the spawned enemies, so a stronger monster fails it until the gear is raised again. Rust tests (all mutation-checked unless noted):

  * `the_game_master_takes_one_damage_from_the_hardest_hit_in_the_data`: total defense above the hardest enemy damage, and a real hit through `hurt_player_by` costs 1 HP; `f64::MAX` leaves finite health.
  * `gm_strike_reaches_the_toughest_living_enemy_in_every_populated_zone` and `gm_strike_uses_worn_weapon_and_normal_kill_path`: the one-hit kill and the normal reward path.
  * `only_the_game_masters_own_golden_weapon_strikes_so_mercenaries_and_players_hit_normally`: a non-GM wearing the sword hits for the rolled damage; hired fighters are built with `gm` off (mutation: dropping the flag from the strike condition fails it).
  * `the_game_master_gets_normal_damage_against_players_in_duels_and_world_pvp`: the target keeps almost all of 10^12 health in a flagged-PvP hit and in a duel hit. Arena matches use the same `pvp_attack` path (the 1-HP duel/arena floor is unchanged).
  * `no_ordinary_character_can_equip_any_golden_piece` (all eight pieces; mutation: removing the rarity gate fails it) and `no_golden_piece_can_be_offered_in_a_trade`.

Not run: a live private-world pass through the MCP scenarios, and a deploy. The server must be rebuilt and restarted, and the client files deployed together, for the new defense values to apply.
