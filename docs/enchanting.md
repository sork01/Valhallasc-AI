# Enchanting

Every character can learn Enchanting for free by speaking with an Enchanting Master. After training, use the Enchanting panel in your bags. Study a recipe scroll once to learn its recipe permanently. To recover materials, choose Disenchant, select the exact unequipped copy in your bags, then review and confirm the yield. Crafting produces a tradeable, single-use scroll. Any character can apply one to a compatible gear copy from their bags or equipped slots. The Apply panel lists eligible gear, the effect, cooldown, cost and any enchantment it will replace.

Recipes come from eligible monster loot and from the Enchanting Masters listed below. A recipe scroll teaches the recipe and a crafted scroll applies the effect. Monsters below level 10 and repeated mechanic summons cannot supply recipes. Trades involving enchanted gear show which copy is offered and which enchantment it carries.

| Town | Where to find the Enchanting Master |
| --- | --- |
| Alderhaven | Near Mira Moonleaf, the apothecary |
| Skaldholm | Near Master Smith Brunhild |
| Nacrehold | Near Thalos Reefhammer |
| Asterion | Near Bramble Gilt |
| Veyrroot Heartwood | Near Master Smith Torvald Pithfire |

## Initial progression

| Tier | Required skill | Cost in dust, essence, shards, cores | Minimum enemy level | Monster drop chance | Vendor price |
| --- | ---: | --- | ---: | ---: | ---: |
| Rare (blue) | 1 | 4, 2, 0, 0 | 10 | 1.25% | 25 gold |
| Epic (purple) | 75 | 6, 4, 2, 0 | 35 | 0.6% | 100 gold |
| Legendary (orange) | 180 | 10, 8, 6, 1 | 65 | 0.25% | 400 gold |

One recipe can drop per eligible kill. The roll reserves the legendary band first, followed by epic and rare, with uniform selection among the recipes in the tier. Elites and bosses triple the chances. Normal kill credit assigns the drop.

Green yields two dust, blue yields two essence, purple yields two shards, and orange yields one core. Orange gear is the sole source of cores. Gray, starter, Hierloom and GM gear are excluded from disenchanting. An enchanter can study recipes before reaching their crafting tier.

Enchanting starts at skill 1 and caps at 300. Applying or disenchanting level 1–5 gear can raise skill through 30. Every five item levels add another 30 points to the cap. That puts level 6–10 gear at 60, level 11–15 at 90, and level 46–50 or higher at 300. Gear above the current minimum can still grant a point. Lower-level gear still yields its materials or takes its enchant.

Crafting can train through the first band in which each tier unlocks. The crafting caps are 30 for rare, 90 for epic and 210 for legendary. Applying and disenchanting higher-level gear cover the remaining bands. Each eligible action can award one point. Higher rarities improve the odds, and two eligible attempts without a point guarantee the next eligible one. Untrained characters can still apply crafted scrolls.


## Equipment and combat

The owner has one profession skill and a set of known recipes in the character save. The enchant ID lives on a physical gear copy. Refining, repairing, equipping, unequipping, banking, mail, trading and buyback carry that field as part of the same gear record. Merging consumes the source copies and makes a new piece. Older characters start with no profession and no enchanted copies. Inspect shows the enchant on the actual worn item. It exposes no profession progress or recipes.

A broken piece gives no enchant effect. Cooldowns belong to the character and effect identifier, so identical rings share a timer and changes of equipment, relogs and restarts preserve the remaining wait. Enchantments are for PvE and inactive in duels, matches, the gauntlet and while flagged for world PvP. Direct enchant damage follows monster defenses and kill credit. It cannot feed equipment signature procs, skill lifesteal or another enchant. Passing Spark can continue its own chain through monsters it defeats. Lightning Rod and Passing Spark use a fixed noncritical basic-hit reference. Double Tap and Shieldbreaker use the hit that triggered them.

Shake It Off responds to the movement slow from enemy rear-hit daze. Moonstep draws ordinary monsters within five tiles. Lightning Rod uses a four-tile radius around the planted rod. Heartwood Grove covers four tiles and heals the wearer and eligible party members for six one-second pulses. Rise from Ash follows the actual attacker for line of sight. Scripted boss mechanics that force an immediate death still do so. Second Wind triggers on XP-bearing enemies at the level cap as well.

## Data and protocol

The source for tiers, costs, drops, materials, display descriptions and cooldowns is `world/enchanting.txt`. `scripts/enchanting_catalog.py` generates the purchasable items, vendor stock and client display data as part of `scripts/sync-world.cjs`. The controller accepts the `enchanting` request with an `open`, `study`, `disenchant`, `craft` or `apply` operation. Training uses the Enchanting Master’s normal NPC interaction and checks the offer and distance. Copy operations carry a copy ID and the expected current enchant. The controller validates and saves a staged character before publishing a change. Combat timers are saved with character progression and temporary combat state stays in the current session.

The trade controller accepts exact copy IDs, validates the selected copies again at confirmation and keeps the existing binding rules. The bank and mail controllers use the existing gear-copy serialization.

## Focused checks

- `cargo test enchanting` covers profession progression, saved recipes, all 16 combat effects, ineligible input, replacement and storage.
- `node tests/enchanting.cjs --mutations` runs production controls and tooltip fault checks. `python3 tests/enchanting-data.py` checks the generated data and vendor stock.
- `node tests/enchanting-protocol.cjs` uses a disposable private game to exercise vendor purchase, crafting, exact-copy trade, inspection and restart persistence.
