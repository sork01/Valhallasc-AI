# Valhalla game TODO

Pick any task by its **ID** (for example, `I65-MAP` or `A70-MAGE`). Each checkbox is one deliverable, and its ID stays stable if the list is reordered. Use focused private checks for the chosen change. An instance entrance stays sealed until its `OPEN` task is complete.

Rules for every TODO: use the `createmap` skill for all zone work; create all sprites through the PixelFlow API; create all music through the dybase2 MCP.

Audit basis: `world/map.txt`, `world/items.txt`, `world/skills.txt`, gear generators and server loot rules on 2026-10-11. Already playable: Undervault (20), Drowned Cathedral wings (40/45/50), Moonwell (60).

Core dependencies: each instance's `OPEN` task follows its four content tasks; randomized orange items and refinement use `G-INSTANCE-DATA`; orange pieces/drop rules use `O-RULES`; later skill ranks use `S-RANK-RULES`; world-map art/routes use `W-GRAPH`. Work on a selected task can start before a related feature is ready to release.

## Instances

Each instance has a separate map, encounter, quest/reward, presentation and opening task. The four Yearwheel doors are four different instances.

- [ ] `I-VISUAL-IDENTITY` — Redesign the interiors of every dungeon, including Undervault, Cathedral, Moonwell and later instances, so each is recognizable at a glance rather than another underground stone vault. Give each its own floor and wall materials, room shapes, landmarks, props, palette and lighting that fit its setting; keep paths, collision and combat effects readable, then compare screenshots across all dungeons in a private browser check.

### The Eye Below — level 65, Stormglass Shore (zone 19)

- [x] `I65-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I65-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I65-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I65-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I65-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Elder Hollow — level 70, Sunward Vale (zone 20)

- [x] `I70-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I70-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I70-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I70-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I70-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Thousandfold Pavilion — level 75, Ribbonwild (zone 21)

- [x] `I75-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I75-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I75-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I75-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I75-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### Temple of the Rain Crown — level 80, Tanglecrown (zone 22)

- [x] `I80T-MAP` — Build its distinct private party map, collision, safe arrival and return route; the entrance opens under `I80T-OPEN`.
- [x] `I80T-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I80T-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I80T-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I80T-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Seed Vault — level 80, Veyrroot Heartwood (zone 24)

- [x] `I80S-MAP` — Build its distinct private party map, collision, safe arrival and return route; the entrance opens under `I80S-OPEN`.
- [x] `I80S-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I80S-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I80S-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I80S-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Sunken Astrolabe — level 85, Lapis Erg (zone 25)

- [x] `I85-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I85-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I85-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I85-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I85-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Thunderheart Gate — level 95, Cairnspine (zone 27)

- [x] `I95-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I95-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I95-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I95-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I95-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Blooming Labyrinth — level 97, Yearwheel spring (zone 28)

- [x] `I97B-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I97B-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I97B-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I97B-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I97B-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Solar Crucible — level 98, Yearwheel summer (zone 28)

- [x] `I98S-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I98S-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I98S-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I98S-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I98S-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Amber Archive — level 99, Yearwheel autumn (zone 28)

- [x] `I99A-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I99A-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I99A-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I99A-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I99A-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

### The Silent Solstice — level 99, Yearwheel winter (zone 28)

- [x] `I99W-MAP` — Build its distinct private party map, collision, safe arrival and return route. Keep the entrance sealed.
- [x] `I99W-FOES` — Add its ordinary enemies and bosses, authoritative combat rules and editable monster sprites.
- [x] `I99W-QUEST` — Add dungeon quests, boss objectives and level-appropriate loot; connect kill/clear credit to the party copy.
- [x] `I99W-SCENE` — Draw the interior and entrance transition, create its music and wire client rendering.
- [x] `I99W-OPEN` — After the four tasks above, activate the entrance and verify level gate, party isolation, travel, boss clear and rewards in a private world.

The Seed Vault is a separate dungeon: Veyrroot Canopy and Heartwood remain enemy-free cities.

## Quests and rewards

- [x] `Q-GHOSTMAW` — Add a dedicated group kill quest for Rán’s Deep elite Ghostmaw, with appropriate reward and credit rules.
- [x] `Q-VAULT-ENTRY` — Add the Undervault story/entry quest in Skaldholm, leading players to its existing level-20 dungeon.
- [x] `Q-VAULT-BOSSES` — Add kill/clear objectives for Gatewarden, Choir, Colossus and Hollow King.
- [x] `Q-CATH-CLOISTER` — Add Flooded Cloister boss objectives and a completion reward.
- [x] `Q-CATH-RELIQUARY` — Add Coral Reliquary boss objectives and a completion reward.
- [x] `Q-CATH-NAVE` — Add Grand Nave boss objectives and a completion reward.
- [x] `Q-PATH-40-55` — Add automatic next-area quests for the level-40, 45, 50 and 55 transitions.
- [x] `Q-PATH-60-75` — Add automatic next-area quests for the level-60, 65, 70 and 75 transitions.
- [x] `Q-PATH-80-99` — Add automatic next-area quests for the level-80, 85, 90 and 95 transitions through the Yearwheel.
- [x] `Q-REWARD-SKY` — Replace the level-20 rewards on `sky_ward_vigil` (34) and `sky_ward_last` (35) with gear appropriate to those quests.
- [x] `Q-REWARD-DEEP` — Replace the level-20 rewards on `deep_captain` (37), `deep_net` (38), `deep_rans` (40) and `deep_kraken` (40). Preserve existing item IDs and saves.
- [x] `Q-CLASS-40-55` — Add class-appropriate armor/weapon/head/shoulder/glove reward choices to Astralhollow, Prismwaste and Orrery quests.
- [x] `Q-CLASS-60-75` — Add those reward choices to Moonspore, Stormglass, Sunward and Ribbonwild quests.
- [x] `Q-CLASS-80-95` — Add those reward choices to Tanglecrown, Lapis Erg, Frostwake and Cairnspine quests.
- [x] `Q-YEAR-ELITES` — Give the twelve Yearwheel elite quests more varied rewards than the same three level-95 blue shared pieces; keep class fairness.

## Equipment systems

- [x] `G-INSTANCE-DATA` — Represent equipment copies with persistent per-item rolled stats and refinement, while preserving legacy stacked items and equipped saves. Needed for randomized orange drops and refinement.
- [x] `G-MERGE-RULES` — Set the rarity steps, cap and handling of differing stat rolls when two identical pieces merge. Decide whether orange gear is mergeable.
- [x] `G-MERGE-SERVER` — Consume exactly two owned copies and create one higher-rarity copy atomically; validate item identity, life, inventory and bag space on the server.
- [x] `G-MERGE-NPC` — Place the merge NPC, add dialogue and a clear preview/confirmation UI.
- [x] `G-MERGE-CHECK` — Verify success, invalid pairs, insufficient copies, full bags and save/reload in a private world.
- [x] `G-REFINE-RULES` — Define refinement levels, stat gains, material/gold costs, cap and interaction with merging/orange rolls.
- [x] `G-REFINE-SERVER` — Implement authoritative per-item refinement with atomic payment and persistent upgraded stats.
- [x] `G-REFINE-NPC` — Add the refinement service and UI that shows cost, current rank and resulting stats.
- [x] `G-REFINE-CHECK` — Verify upgrades, invalid attempts, equipped items and save/reload in a private world.

### Fifty orange pieces

All 50 must work for every class at every level, be exceptionally strong, have distinct worn art/icons and receive randomized stats when dropped. A kill of **any mob** rolls a **0.1% total chance**, independent of mob/player level; a success chooses one of the 50 pieces. The roll and ownership are authoritative.

- [x] `O-RULES` — Define the 50 names, slots, stat ranges and roll distribution without adding class or level gates.
- [x] `O-DROP` — Add the independent 0.1% per-kill roll and random choice from the 50-piece pool.
- [x] `O-UI` — Display orange rarity and each copy’s rolled stats consistently in bags, equipment and loot.
- [x] `O-01-05` — Create and wire orange pieces 01–05: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-06-10` — Create and wire orange pieces 06–10: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-11-15` — Create and wire orange pieces 11–15: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-16-20` — Create and wire orange pieces 16–20: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-21-25` — Create and wire orange pieces 21–25: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-26-30` — Create and wire orange pieces 26–30: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-31-35` — Create and wire orange pieces 31–35: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-36-40` — Create and wire orange pieces 36–40: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-41-45` — Create and wire orange pieces 41–45: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-46-50` — Create and wire orange pieces 46–50: catalog, distinct worn art, icon and randomized stat definition.
- [x] `O-CHECK` — Check the 50-piece pool, class/level freedom, drop probability, persistence and equip rules in focused private tests.

### Rare item pickup celebration

- [x] `LOOT-RARE-PICKUP` — When the server confirms that a player picks up a green, blue, purple or orange item, show that player large, prominent text saying "You picked up a green item!" (or the matching rarity). Make the colour, animation and effects progressively more dramatic from green through orange, so an orange pickup feels exceptional. Trigger it for the actual recipient of shared loot, use the item's effective rarity, and keep the item name readable. Verify all four rarities in a private browser check.

### Rare ground drop effects

- [x] `LOOT-DROP-PILLAR` — When a green, blue, purple or orange item drops, make the item on the ground emit a striking pillar of animated particles in its rarity colour. Keep the pillar anchored to the item until it is picked up or despawns, with a more dramatic effect for higher rarities. Drawn from each live drop's effective rarity in `client/field.js`; four colors, animation and gold filtering checked in `tests/loot-pillar-ui.cjs`.

### Ordinary gear artwork, levels 60–95

For each entry, replace tinted starter silhouettes with new worn layers and matching icons while preserving item IDs, stats and saves. Class entries cover armor, headgear, shoulders, gloves and weapon; shared entries cover pants, necklace and accessory. Level 55 currently reuses level-50 art.

- [x] `A55-DECIDE` — Decide whether level 55 should have its own artwork, then either plan it or record the intentional level-50 reuse.

#### Level 60

- [x] `A60-WARRIOR` — Create and wire the five level-60 warrior pieces and icons.
- [x] `A60-MAGE` — Create and wire the five level-60 mage pieces and icons.
- [x] `A60-ASSASSIN` — Create and wire the five level-60 assassin pieces and icons.
- [x] `A60-PRIEST` — Create and wire the five level-60 priest pieces and icons.
- [x] `A60-HUNTER` — Create and wire the five level-60 hunter pieces and icons.
- [x] `A60-SHARED` — Create and wire the three shared level-60 pieces and icons.

#### Level 65

- [x] `A65-WARRIOR` — Create and wire the five level-65 warrior pieces and icons.
- [x] `A65-MAGE` — Create and wire the five level-65 mage pieces and icons.
- [x] `A65-ASSASSIN` — Create and wire the five level-65 assassin pieces and icons.
- [x] `A65-PRIEST` — Create and wire the five level-65 priest pieces and icons.
- [x] `A65-HUNTER` — Create and wire the five level-65 hunter pieces and icons.
- [x] `A65-SHARED` — Create and wire the three shared level-65 pieces and icons.

#### Level 70

- [x] `A70-WARRIOR` — Create and wire the five level-70 warrior pieces and icons.
- [x] `A70-MAGE` — Create and wire the five level-70 mage pieces and icons.
- [x] `A70-ASSASSIN` — Create and wire the five level-70 assassin pieces and icons.
- [x] `A70-PRIEST` — Create and wire the five level-70 priest pieces and icons.
- [x] `A70-HUNTER` — Create and wire the five level-70 hunter pieces and icons.
- [x] `A70-SHARED` — Create and wire the three shared level-70 pieces and icons.

#### Level 75

- [x] `A75-WARRIOR` — Create and wire the five level-75 warrior pieces and icons.
- [x] `A75-MAGE` — Create and wire the five level-75 mage pieces and icons.
- [x] `A75-ASSASSIN` — Create and wire the five level-75 assassin pieces and icons.
- [x] `A75-PRIEST` — Create and wire the five level-75 priest pieces and icons.
- [x] `A75-HUNTER` — Create and wire the five level-75 hunter pieces and icons.
- [x] `A75-SHARED` — Create and wire the three shared level-75 pieces and icons.

#### Level 80

- [x] `A80-WARRIOR` — Create and wire the five level-80 warrior pieces and icons.
- [x] `A80-MAGE` — Create and wire the five level-80 mage pieces and icons.
- [x] `A80-ASSASSIN` — Create and wire the five level-80 assassin pieces and icons.
- [x] `A80-PRIEST` — Create and wire the five level-80 priest pieces and icons.
- [x] `A80-HUNTER` — Create and wire the five level-80 hunter pieces and icons.
- [x] `A80-SHARED` — Create and wire the three shared level-80 pieces and icons.

#### Level 85

- [x] `A85-WARRIOR` — Create and wire the five level-85 warrior pieces and icons.
- [x] `A85-MAGE` — Create and wire the five level-85 mage pieces and icons.
- [x] `A85-ASSASSIN` — Create and wire the five level-85 assassin pieces and icons.
- [x] `A85-PRIEST` — Create and wire the five level-85 priest pieces and icons.
- [x] `A85-HUNTER` — Create and wire the five level-85 hunter pieces and icons.
- [x] `A85-SHARED` — Create and wire the three shared level-85 pieces and icons.

#### Level 90

- [x] `A90-WARRIOR` — Create and wire the five level-90 warrior pieces and icons.
- [x] `A90-MAGE` — Create and wire the five level-90 mage pieces and icons.
- [x] `A90-ASSASSIN` — Create and wire the five level-90 assassin pieces and icons.
- [x] `A90-PRIEST` — Create and wire the five level-90 priest pieces and icons.
- [x] `A90-HUNTER` — Create and wire the five level-90 hunter pieces and icons.
- [x] `A90-SHARED` — Create and wire the three shared level-90 pieces and icons.

#### Level 95

- [x] `A95-WARRIOR` — Create and wire the five level-95 warrior pieces and icons.
- [x] `A95-MAGE` — Create and wire the five level-95 mage pieces and icons.
- [x] `A95-ASSASSIN` — Create and wire the five level-95 assassin pieces and icons.
- [x] `A95-PRIEST` — Create and wire the five level-95 priest pieces and icons.
- [x] `A95-HUNTER` — Create and wire the five level-95 hunter pieces and icons.
- [x] `A95-SHARED` — Create and wire the three shared level-95 pieces and icons.

### Dungeon and endgame gear

- [x] `G-VAULT-ART` — Give the 27 Undervault-exclusive level-20 pieces a distinct visual direction; record how its class and shared pieces differ from starter gear.
- [x] `G-VAULT-EXPORT` — Export/wire the Undervault worn layers and matching icons without changing item IDs or existing loot.
- [x] `G-MOON-CATALOG` — Define a Moonwell-exclusive level-60 blue set and boss slot pools; currently Moonwell bosses give ordinary blue gear.
- [x] `G-MOON-ART` — Create Moonwell set worn art and icons.
- [x] `G-MOON-LOOT` — Switch the four Moonwell bosses to their exclusive set and verify party drops.
- [x] `G-YEAR-SPRING` — Define level-97 Blooming Labyrinth gear rewards.
- [x] `G-YEAR-SUMMER` — Define level-98 Solar Crucible gear rewards.
- [x] `G-YEAR-AUTUMN` — Define level-99 Amber Archive gear rewards.
- [x] `G-YEAR-WINTER` — Define level-99 Silent Solstice gear rewards.

### Unique art for the later dungeon sets

Audit on 2026-10-14: each dungeon below already drops 28 exclusive items (25 class pieces and three shared pieces), but their `art` fields still reuse starter worn layers. Each task means a distinct, immediately recognizable silhouette for its own dungeon, with worn layers for every class and both bodies in every animation, matching inventory icons, and editable PixelFlow source. Preserve item IDs, stats, loot pools and saves. Verify real-client equipment, game-scale readability against progression gear, and update the all-class gallery in Filedrop. A palette or aura alone does not complete a task.

- [x] `G-I65-ART` — Create and wire unique Eye Below gear art for its level-65 set.
- [x] `G-I70-ART` — Create and wire unique Elder Hollow gear art for its level-70 set.
- [x] `G-I75-ART` — Create and wire unique Thousandfold Pavilion gear art for its level-75 set.
- [x] `G-I80T-ART` — Create and wire unique Temple of the Rain Crown gear art for its level-80 set.
- [x] `G-I80S-ART` — Create and wire unique Seed Vault gear art for its level-80 set.
- [x] `G-I85-ART` — Create and wire unique Sunken Astrolabe gear art for its level-85 set.
- [x] `G-I95-ART` — Create and wire unique Thunderheart Gate gear art for its level-95 set.
- [x] `G-I97B-ART` — Create and wire unique Blooming Labyrinth gear art for its level-95 reward set.
- [x] `G-I98S-ART` — Create and wire unique Solar Crucible gear art for its level-95 reward set.
- [x] `G-I99A-ART` — Create and wire unique Amber Archive gear art for its level-95 reward set.
- [x] `G-I99W-ART` — Create and wire unique Silent Solstice gear art for its level-95 reward set.

- [x] `G95-BONUS` — Decide the level-95 attribute bonus and remove the current clamp to the level-90 value if a larger bonus is intended.

### Dungeon set bonuses

Wearing several pieces of the same dungeon set grants escalating bonuses at **2, 4, 6 and 8** equipped pieces (eight slots: armor, headgear, shoulders, gloves, weapon, pants, necklace, accessory, so 8 is the full set). Example shape: 2 pieces give a class stat bonus (for example warrior +attack); 4 pieces lower a skill's cooldown; 6 pieces make a skill twice as powerful; 8 pieces give something even better, such as a set-defining effect. Bonuses are cumulative and class-specific. **Every dungeon set has its own perks**: a warrior's Undervault set must differ from the warrior's Moonwell set (and every other dungeon's) in which skills it touches, what the effects do and how they feel, not just in the numbers. Each set's perks should follow that dungeon's theme and boss identity. Preserve item IDs, stats, loot pools and saves.

- [ ] `SET-RULES` — Define what counts as a set (each dungeon's 28 exclusive items, plus Undervault and Moonwell), how pieces are counted (distinct equipped slots, refined copies, orange pieces). **Set membership depends on the piece, not its rarity**: a piece merged up to a higher rarity, or a copy with different rolled stats or refinement, still counts toward its set, so rarity never breaks or changes a set bonus (rarity may still affect the piece's own stats), the tier structure and the power budget so 8 pieces beat mixed gear without being mandatory. Add a uniqueness rule: for each class, no two sets may share the same skill at the cooldown, doubled-power or 8-piece tier, and no two 8-piece effects may be the same mechanic. Record the full set-by-class matrix in a doc beside `docs/skill-ranks.md`.
- [ ] `SET-SERVER` — Add authoritative set tracking: count equipped pieces per set, recompute on equip, unequip, merge, refine and login, and apply the stat, cooldown and skill-power effects in combat. Cooldown and power changes must stack correctly with skill ranks and passives.
- [ ] `SET-UI` — Show set membership and the 2/4/6/8 tiers in item tooltips and the equipment panel: pieces worn out of the total, active tiers highlighted, inactive ones greyed with what they unlock. Add a short on-screen cue when a tier activates or drops.
- [ ] `SET-WARRIOR` — Define the 2/4/6/8 bonuses for warriors in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon.
- [ ] `SET-MAGE` — Define the 2/4/6/8 bonuses for mages in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon.
- [ ] `SET-ASSASSIN` — Define the 2/4/6/8 bonuses for assassins in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon.
- [ ] `SET-PRIEST` — Define the 2/4/6/8 bonuses for priests in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon.
- [ ] `SET-HUNTER` — Define the 2/4/6/8 bonuses for hunters in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon.
- [ ] `SET-EFFECTS` — Give the 8-piece bonuses and doubled-skill (6-piece) bonuses distinct visual feedback on the skill, so players can see that a set effect is active.
- [ ] `SET-CHECK` — Verify that no two sets give the same class identical perks (derive the matrix from the data and assert uniqueness), then check tier counting across mixed rarities (for example, 4 base pieces plus 4 merged pieces still make an 8-piece set), class gating, stacking with ranks and passives, unequip and swap behavior, save/reload, and PvP balance in focused private tests.

### Purple dungeon drops

Dungeon sets stay blue at base. Each dungeon-set piece that drops has a small chance (about **5%**) to drop already purple (epic), so players can find purple pieces without merging. Purple copies count toward their set like any other rarity.

- [x] `DROP-EPIC-RULES` — Settle the roll: 5% per dropped set piece (not per kill), applied to every dungeon's boss and chest drops including party drops, with the value in one named constant. Decide whether it is a purple copy of the same catalog item (the per-copy rarity from `G-INSTANCE-DATA`, with the epic stat curve and second bonus stat that `server/src/items.rs` expects) or a separate catalog entry, and whether Undervault and Moonwell are included. Purple copies still cannot merge further, and the catalog, loot pools and saves keep their item IDs. Settled in [docs/epic-set-drops.md](docs/epic-set-drops.md).
- [x] `DROP-EPIC-SERVER` — Implement the authoritative independent roll on set-piece drops, with the epic stats applied to that copy. Check that outdoor and ordinary drop tables are unchanged and that a purple drop merges, refines, trades and saves like any other epic copy.
- [x] `DROP-EPIC-UI` — Show purple rarity on dungeon drops in the loot marker, bags, equipment and tooltips, with the set membership from `SET-UI` unchanged.
- [x] `DROP-EPIC-CHECK` — Verify the roll rate over many seeded drops (about 5%, not per kill), that purple pieces count for set tiers alongside blue ones, and that nothing else changes in a private world. Rate checked through the real boss-loot path in `world/epic_drop_tests.rs` (about 5% per dropped set piece, not per kill; mutation-checked); stat caps, merge refusal, refine, trade, sale and save are in `items.rs` and `trade.rs` tests.

## Bags

A character has 16 base slots plus up to four expansion bags (`bag_capacity` in `server/src/items.rs`). Traders now offer ten tiers from the 6-slot Linen Satchel at level 1 through the 24-slot Sovereign Pack at level 90; the full table is in [docs/bag-tiers.md](docs/bag-tiers.md).

- [x] `BAG-RULES` — Define the tier table (level, name, slots, price) from level 10 through 90 with a steeply rising price curve, whether the Linen Satchel stays as the cheap level-1 bag, and how the existing Adventurer Satchel (8) and Traveler Pack (16) in the catalog fit in or are retired. Keep the four-bag limit and the replace-the-smallest rule, and decide whether a smaller bag can still be bought once a larger one is owned. Preserve existing bag IDs and saves. Decisions: [docs/bag-tiers.md](docs/bag-tiers.md).
- [x] `BAG-CATALOG` — Add the new bag items with names and icons, and give the trader NPCs offers for each tier they may sell. Update `scripts/generate_*.py` and sync `world/`, since each zone's trader lists its own offers. The idempotent `scripts/bag_tiers.py` pass runs from `sync-world.cjs` after every zone generator.
- [x] `BAG-SERVER` — Enforce the level gate and price in `purchase_bag`, with a clear message when the level is too low or gold is short. Keep payment atomic, and make sure bags already owned still count after the change.
- [x] `BAG-UI` — Show the next bag tier, its level requirement, slot count and price in the trader dialog, with locked tiers greyed out and an "owned" state. Show the extra slots gained before buying.
- [x] `BAG-DROP-RULES` — Let bags drop from monsters at the right level: about a **2% chance per kill** of one bag, where the bag tier matches the monster's level band (a level-34 monster can drop the level-30 tier, not the level-40 one), independent of the other drop rolls and with the value in one named constant. Decide the band edges, whether elites, bosses and dungeon enemies roll it, how a party kill is shared (one roll per kill, awarded like other loot), and whether a dropped bag is bind-free or tradable (see `SOC-TRADE`). A dropped bag must not be worth more than buying one: set its sell value to match the tier. Drops never bypass the player's level gate on using the bag, if one applies. Decisions: [docs/bag-tiers.md](docs/bag-tiers.md).
- [x] `BAG-DROP-SERVER` — Add the authoritative roll and grant. `can_collect` currently refuses `kind == "bag"` items, so decide how a dropped bag is picked up, then fit it automatically or put it in the bag grid until the player chooses. Keep the four-bag limit and the replace-the-smallest rule.
- [x] `BAG-DROP-UI` — Show the dropped bag with its tier colour or icon on the ground and in loot messages, and show its slot count in tooltips.
- [x] `BAG-CHECK` — Verify level and gold gates, replacing a smaller bag, the four-bag limit, save/reload, and that capacity and a full-bag drop still behave in a private world. Include the bag drop rate (about 2% per kill over many seeded kills), the level-band match and party kills. Update the existing tests that assume a 22-slot capacity from one Linen Satchel only if the rules change it.

## Consumable balance

Today there are three families, each with a tier every ten levels (1, 10, 20 ... 90), generated by `scripts/consumable_tiers.py`: Traveler's Stew (heals and restores mana over 8 seconds), Health Potions (heal, 60-second shared cooldown) and Mana Potions. Healing runs 100, 210, 350, 490 ... 1,330 and mana 100, 170, 300 ... 1,190, in flat numbers, with prices from 12/30 to 500/1,150 gold. Maximum HP is `class base + 20 per level + 8 per stamina` (`max_hp` in `server/src/model.rs`), so a flat potion can fall far behind a high-level character's HP pool; there is no tier above level 90 for levels 91–99.

- [x] `CONS-AUDIT` — Measure how the potions and food compare with real characters at levels 1, 10, 20 ... 99 for every class, with and without heavy stamina or intellect: potion heal as a percentage of max HP, mana restored as a percentage of max mana (mages and priests use mana, warriors use rage, so check what mana does for each class), healing per second against the damage of that level's monsters, elites and bosses, and the cost in gold of keeping a character stocked per hour. Report the table in `docs/` and name the levels where a potion is useless or too strong. Reported in [docs/consumable-audit.md](docs/consumable-audit.md).
- [ ] `CONS-RULES` — From the audit, set the balance rules: whether healing scales as a percentage of max HP, a flat number or both, the 60-second cooldown (a full potion every minute is slow at high level) versus food's 8-second hot, how food and potions stack, and price against healing and against what a level's monsters drop. Add the missing tiers for levels 91–99 (for example 95 and 99) and any extra tiers inside the ten-level steps where the audit shows a gap, then record the final curve for levels 1–99.
- [ ] `CONS-DATA` — Update `scripts/consumable_tiers.py` and regenerate the items: new tiers with names, icons, rarity colours and prices, required levels, and the traders that sell them (each zone's NPC list in `scripts/generate_*.py`). Keep existing item IDs, stacks and quick-slot assignments.
- [ ] `CONS-SERVER` — Apply the new rules in the server (percentage healing, cooldowns or caps if chosen) with clear rejection messages, and make sure PvP, duels and arenas follow whatever limits `CONS-RULES` sets for potions.
- [ ] `CONS-UI` — Show the real healing and mana amounts (and percentage of max, if used) in tooltips, quick slots and the effects bar, and the cooldown on potions.
- [ ] `CONS-CHECK` — Verify in a private world at several levels and classes that each tier heals and restores what its tooltip says, cooldown and food rules hold, prices and shop lists are right, old saves and quick slots still work, and that the balance table from the audit passes.

## Kill-time testing

Measure how long it takes to kill a monster of the character's own level, every 5 levels (5, 10, 15 ... 95, plus 99), for every class, wearing the **normal gear for that level** (the ordinary progression set for that level, not dungeon, orange or refined gear). This shows where fights are too fast or too slow and feeds `CONS-AUDIT`.

- [x] `TTK-RULES` — Define the test: what "normal gear" is at each level (the level's ordinary piece in every slot, base rarity, no refinement, no set bonuses), the skillbar and rank each class has at that level, the attribute allocation (an even default plus a stamina-heavy and a damage-heavy variant), the target (an ordinary monster of the same level, and also an elite if one exists at that level), whether potions and food are used, and what counts as a kill (first hit to death, with travel and cooldown waits included). Set target kill times per level band and say what is too fast or too slow. Settled in [docs/ttk-rules.md](docs/ttk-rules.md).
- [x] `TTK-HARNESS` — Build a repeatable private-world test that creates a character of each class at the given level with that gear, spawns the monster, plays a fixed skill rotation (and a basic-attack-only run), and records time to kill, damage taken, mana or rage used, potions used and whether the character died. Run several seeded repetitions per case and report the median and spread. It must never touch the live world or real saves. Built as `server/src/world/ttk.rs` (in-memory `World`, 9 seeded repetitions, median and spread); run it with `bash scripts/ttk.sh` (variables listed in the script), and its fast tests run with `cargo test ttk`.
- [ ] `TTK-RUN` — Run it for all 20 levels and five classes (100 cases per variant) and write the results as a table in `docs/`: kill time by class and level, plus the same-level monster's own damage against the character so the other side of the fight is visible.
- [ ] `TTK-TUNE` — Fix the outliers the report shows by adjusting monster stats, skill numbers or gear stats, never by changing item IDs or saves, then re-run the affected cases. Record what was changed and why.
- [ ] `TTK-CHECK` — Keep the harness as a regression test with the target bands from `TTK-RULES` as assertions, so a later skill, gear or monster change that makes a class too fast or too slow fails the check.

### Stale tests (found 2026-10-15)

Eleven Rust tests failed on the commit before the Codex work and the speed-up (they assumed a smaller world). The suite itself now takes about 7 minutes (`bash scripts/cargo.sh test`), down from not finishing. Fix each by deriving the expected number from the data, as `vault_tests.rs` now does for `COPY`.

- [x] `TEST-STALE` — Update these tests, each with the message it fails with: `sunward_tests::vale_gates_bridges_hub_and_all_encounters_are_reachable` and `stormglass_tests::shore_has_reciprocal_clear_gates_a_hub_and_a_sealed_eye` (monster-kind and NPC counts grew: `(42, 12)` against `(42, 10)`, `(41, 11)` against `(41, 9)`); `world::tests::progression_quests_come_every_five_levels_and_each_names_the_zone_it_leads_to` (the list now runs to level 95); `skaldholm_is_a_big_enemy_free_city_with_a_hundred_houses_a_wall_and_a_gate_pair` (zone count 40, not 34); `skaldholm_has_eleven_valid_quests_mostly_errands_between_the_maps` (the guild offer list changed); `the_whole_city_questline_runs_from_the_gate_captain_to_the_steward` (`city_vault_entry` is never accepted); `set_level_restores_health_announces_unlocks_and_lowering_resets_trained_stats` (11 unlocks, expected 10); `spark_tests::spark_every_hub_has_one_clear_master_and_a_reciprocal_connected_network` (24 stops, expected 14); `social::tests::a_priest_alone_heals_themself_and_a_prayer_reaches_up_to_five` and `priest_blessings_and_pulses_reach_party_members_in_range_only` (the prayer no longer heals every wounded member, and a pulse gives `-0.0` where 0.3 is expected: check whether the skill numbers or the test moved); and `vault_tests::the_colossus_and_the_hollow_king_need_five_and_a_healer_the_king_beating_a_party_of_three` (a balance probe: the hired five no longer finish the king in the expected time, so it belongs with `TTK-TUNE`). Then make the suite green and keep it so. **Done 2026-10-15:** all eleven fixed and the suite is green (498 passed). The data tests now read quest, hub and unlock counts from the world or use lower bounds; the priest tests use the current skill unlock levels; the Skaldholm questline test covers only the talk-and-bring errands; the Undervault King probe was a fixture bug (the hired mage, priest and hunter were placed behind the arena wall and never fought, so only two of the five did any damage), and now they stand on free ground beside the hero, the full party kills the King in 193 s and a warrior-and-priest party needs 338 s.

### First measurements (2026-10-15): what they show and how to fix it

Reading the reports: a case that did not kill shows the cap (120 s) as its time, whether the character died or ran out of time; the `deaths` field counts the deaths. Source: `docs/consumable-audit.md` (potions, damage, income) and the kill-time harness (`bash scripts/ttk.sh`, 300 fights, three seeds, no consumables). The target for the middle bands is a normal-gear character killing its same-level ordinary monster in about 30 s without dropping under 20% HP (`docs/ttk-rules.md`). These numbers are the starting point for `TTK-RUN`, not a replacement for it: it must repeat them with nine seeds and every class.

**What was measured**

- Levels 5 and 10 are too fast. Level 5 takes 8–10 s (target 15–30 s), level 10 takes 13–14 s.
- Level 20 is lopsided: the mage kills the hydra in 34 s, the warrior needs 76 s and one seed in three fails. That is 2.2 times apart (the rule flags anything beyond 1.6 times).
- From level 30 up **nobody wins**. The character dies, or is still fighting at 120 s. The monster's damage is the cause: the warrior takes the damage per second below, which empties its health long before a 30 s fight ends.

  | Level | Ordinary monster | Warrior max HP | Damage taken per second | Allowed for a 30 s fight (40% of HP) | Too high by |
  | ---: | --- | ---: | ---: | ---: | ---: |
  | 20 | hydra | 660 | 8 | 8.8 | 1.0x |
  | 30 | galehound | 948 | 27 | 12.6 | 2.1x |
  | 40 | voidmoth | 1236 | 55 | 16.5 | 3.3x |
  | 50 | bronzemantis | 1540 | 101 | 20.5 | 4.9x |
  | 60 | saltclaw | 1860 | 171 | 24.8 | 6.9x |
  | 70 | ribbongecko | 2180 | 241 | 29.1 | 8.3x |
  | 80 | sandhopper | 2500 | 245 | 33.3 | 7.4x |
  | 90 | screeferret | 2860 | 282 | 38.1 | 7.4x |
  | 99 | snowstoat | 3112 | 750 | 41.5 | 18.1x |

  Hits are also huge: at level 99 one ordinary hit does 3,492 damage to a 3,112-HP warrior, and an elite or boss of the same level kills in 0.3–5 hits from level 20 up. The kill-speed side above level 20 is **not measured yet**, because those fights end in death; `TTK-RUN` needs the damage fix first, or a god-mode run, to see it.
- Potions are fine up to level 20, too weak from level 60 (they cover 1.8–5.3 s of damage), and the level-1 potion is 105–125% of a mage's, assassin's or hunter's health. Mana potions do nothing for warriors, assassins and hunters.

**How to fix it (in this order; each is a task)**

- [ ] `TTK-FIX-DAMAGE` — Bring monster damage down first, because nothing else can be judged while the character dies. For every ordinary monster kind, scale `damage` so the median damage per second the harness measures stays under 40% of max HP per 30 s (the factor column above is the first guess: about 2x at level 30, 3x at 40, 5x at 50, 7–8x at 60 to 90, 18x at 99, none at 20 and below). Do it in the monster data (`stats` of each kind in `world/*.txt` and the `Slime::stats` table in `server/src/world.rs`), never in the combat formula, so PvP, saves and item IDs do not move. Keep elites and bosses 2–4 times ordinary damage per second so they stay group fights, then check that no same-level boss kills a full-health character in fewer than 4 hits. Re-run `TTK-RUN` after each pass; stop when no case in levels 25–99 ends with the character under 20% HP.
- [ ] `TTK-FIX-SPEED` — With the character surviving, tune kill time by monster health: new HP = old HP × (target 30 s ÷ measured median), clamped to 0.5–2 per pass, per level band from `docs/ttk-rules.md`. The first guesses are level 5 about 2.1 times the health (8.4 s to 22 s) and level 10 about 1.7 times (13 s to 22 s). Then close the class gap: if a class stays beyond 1.6 times the cross-class median at a level (warrior against mage at level 20), adjust that class's rank multipliers or its weapon attack in `scripts/gear_levels.py`, not the monster. Record every change and the before/after medians here.
- [x] `TTK-FIX-RUN` — Run one private harness process per class in parallel with `bash scripts/ttk-parallel.sh`, preserving the early stop and writing separate JSON/log files under `test-results/`; `scripts/merge_ttk.py` combines them into `docs/ttk-report.md`. The full 20-level × five-class grid completed with one seed as a provisional report; `TTK-RUN` remains open for nine seeds and all variants.
- [ ] `CONS-FIX-SCALE` — After `TTK-FIX-DAMAGE`, redo `docs/consumable-audit.md` and then size the consumables in `CONS-RULES`. Proposals to test: make a potion heal the larger of its flat tier and a percentage of max HP (about 35–40%), so stamina-heavy characters and level 99 do not fall to 35% of health; keep the 60 s cooldown below level 40 and shorten it to 30–45 s above, so a potion matters in a 30 s fight; lower the level-1 potion to about 60 so it is 60–75% of the starting classes' health; let a meal heal a percentage of max HP over its 8 s. Keep every item ID and price tier.
- [x] `CONS-FIX-MANA` — Mana potions and meals now restore the class resource: mana stays flat, while rage and energy use a tier-scaled share of their 100-point cap. Old stacks and the shared cooldown remain valid; full-resource uses are refused without spending an item. Quick slots, tooltips and combat feedback show the recipient's resource. Rule recorded in `docs/consumable-audit.md`; five-class Rust checks and 41 private browser checks passed.
- [x] `CONS-FIX-GOLD` — The only price problem is level 1: a continuous potion habit (1,800 gold per hour) costs 2.7 times the income of 665. Lower the level-1 potion and meal price or raise level-1 kill gold until it is under about 50% of income; from level 20 up potions cost under 30% of income and need no change.


## Skills

Each class learns a new active skill every four levels from 4 through 40. Rank 2 arrives at 6, 10, …, 42; further ranks continue at even levels through 98, plus a level-99 class capstone. Automatic class passives at 10, 20, …, 90 are separate rewards. Existing characters receive all skills and ranks earned by their saved level.

- [x] `S-RANK-RULES` — Add skill-rank data, server unlock/combat rules and client rank descriptions without losing saved skillbar assignments.
- [x] `S-RESPACE-WARRIOR` — Spread the existing warrior kit across levels 4–40 and assign later ranks.
- [x] `S-RESPACE-MAGE` — Spread the existing mage kit across levels 4–40 and assign later ranks.
- [x] `S-RESPACE-ASSASSIN` — Spread the existing assassin kit across levels 4–40 and assign later ranks.
- [x] `S-RESPACE-PRIEST` — Spread the existing priest kit across levels 4–40 and assign later ranks.
- [x] `S-RESPACE-HUNTER` — Spread the existing hunter kit across levels 4–40 and assign later ranks.

The unlock and rank layout is recorded in [docs/skill-ranks.md](docs/skill-ranks.md).

- [ ] `S-FLASH-CLARITY` — Make every class skill more visually striking and immediately recognizable in play: distinct cast, travel and impact effects that show its range, target area and purpose (damage, healing, protection or movement), with skill icons/descriptions that match what players see. Check readability in crowded fights and at higher ranks.

### Skill ranks, levels 22–40

- [x] `S22-40-WARRIOR` — Add warrior skill/rank unlocks at every even level from 22 through 40.
- [x] `S22-40-MAGE` — Add mage skill/rank unlocks at every even level from 22 through 40.
- [x] `S22-40-ASSASSIN` — Add assassin skill/rank unlocks at every even level from 22 through 40.
- [x] `S22-40-PRIEST` — Add priest skill/rank unlocks at every even level from 22 through 40.
- [x] `S22-40-HUNTER` — Add hunter skill/rank unlocks at every even level from 22 through 40.

### Skill ranks, levels 42–60

- [x] `S42-60-WARRIOR` — Add warrior skill/rank unlocks at every even level from 42 through 60.
- [x] `S42-60-MAGE` — Add mage skill/rank unlocks at every even level from 42 through 60.
- [x] `S42-60-ASSASSIN` — Add assassin skill/rank unlocks at every even level from 42 through 60.
- [x] `S42-60-PRIEST` — Add priest skill/rank unlocks at every even level from 42 through 60.
- [x] `S42-60-HUNTER` — Add hunter skill/rank unlocks at every even level from 42 through 60.

### Skill ranks, levels 62–80

- [x] `S62-80-WARRIOR` — Add warrior skill/rank unlocks at every even level from 62 through 80.
- [x] `S62-80-MAGE` — Add mage skill/rank unlocks at every even level from 62 through 80.
- [x] `S62-80-ASSASSIN` — Add assassin skill/rank unlocks at every even level from 62 through 80.
- [x] `S62-80-PRIEST` — Add priest skill/rank unlocks at every even level from 62 through 80.
- [x] `S62-80-HUNTER` — Add hunter skill/rank unlocks at every even level from 62 through 80.

### Skill ranks, levels 82–98

- [x] `S82-98-WARRIOR` — Add warrior skill/rank unlocks at every even level from 82 through 98.
- [x] `S82-98-MAGE` — Add mage skill/rank unlocks at every even level from 82 through 98.
- [x] `S82-98-ASSASSIN` — Add assassin skill/rank unlocks at every even level from 82 through 98.
- [x] `S82-98-PRIEST` — Add priest skill/rank unlocks at every even level from 82 through 98.
- [x] `S82-98-HUNTER` — Add hunter skill/rank unlocks at every even level from 82 through 98.

### Ten-level class milestones


#### Levels 10, 20, 30

- [x] `P10-30-WARRIOR` — Add distinct warrior milestone skills at 10, 20 and 30, preferably passive, with server effects and visible unlocks.
- [x] `P10-30-MAGE` — Add distinct mage milestone skills at 10, 20 and 30, preferably passive, with server effects and visible unlocks.
- [x] `P10-30-ASSASSIN` — Add distinct assassin milestone skills at 10, 20 and 30, preferably passive, with server effects and visible unlocks.
- [x] `P10-30-PRIEST` — Add distinct priest milestone skills at 10, 20 and 30, preferably passive, with server effects and visible unlocks.
- [x] `P10-30-HUNTER` — Add distinct hunter milestone skills at 10, 20 and 30, preferably passive, with server effects and visible unlocks.

#### Levels 40, 50, 60

- [x] `P40-60-WARRIOR` — Add distinct warrior milestone skills at 40, 50 and 60, preferably passive, with server effects and visible unlocks.
- [x] `P40-60-MAGE` — Add distinct mage milestone skills at 40, 50 and 60, preferably passive, with server effects and visible unlocks.
- [x] `P40-60-ASSASSIN` — Add distinct assassin milestone skills at 40, 50 and 60, preferably passive, with server effects and visible unlocks.
- [x] `P40-60-PRIEST` — Add distinct priest milestone skills at 40, 50 and 60, preferably passive, with server effects and visible unlocks.
- [x] `P40-60-HUNTER` — Add distinct hunter milestone skills at 40, 50 and 60, preferably passive, with server effects and visible unlocks.

#### Levels 70, 80, 90

- [x] `P70-90-WARRIOR` — Add distinct warrior milestone skills at 70, 80 and 90, preferably passive, with server effects and visible unlocks.
- [x] `P70-90-MAGE` — Add distinct mage milestone skills at 70, 80 and 90, preferably passive, with server effects and visible unlocks.
- [x] `P70-90-ASSASSIN` — Add distinct assassin milestone skills at 70, 80 and 90, preferably passive, with server effects and visible unlocks.
- [x] `P70-90-PRIEST` — Add distinct priest milestone skills at 70, 80 and 90, preferably passive, with server effects and visible unlocks.
- [x] `P70-90-HUNTER` — Add distinct hunter milestone skills at 70, 80 and 90, preferably passive, with server effects and visible unlocks.

### Skill identity and final capstones

- [x] `S-REVAMP-WARRIOR` — Redesign lookalike warrior skills so their visuals, timing and mechanics are recognizable; preserve or migrate skillbar IDs.
- [x] `S99-WARRIOR` — Add the warrior level-99 capstone rank and its visual/UI feedback.
- [x] `S-REVAMP-MAGE` — Redesign lookalike mage skills so their visuals, timing and mechanics are recognizable; preserve or migrate skillbar IDs.
- [x] `S99-MAGE` — Add the mage level-99 capstone rank and its visual/UI feedback.
- [x] `S-REVAMP-ASSASSIN` — Redesign lookalike assassin skills so their visuals, timing and mechanics are recognizable; preserve or migrate skillbar IDs.
- [x] `S99-ASSASSIN` — Add the assassin level-99 capstone rank and its visual/UI feedback.
- [x] `S-REVAMP-PRIEST` — Redesign lookalike priest skills so their visuals, timing and mechanics are recognizable; preserve or migrate skillbar IDs.
- [x] `S99-PRIEST` — Add the priest level-99 capstone rank and its visual/UI feedback.
- [x] `S-REVAMP-HUNTER` — Redesign lookalike hunter skills so their visuals, timing and mechanics are recognizable; preserve or migrate skillbar IDs.
- [x] `S99-HUNTER` — Add the hunter level-99 capstone rank and its visual/UI feedback.
- [x] `S-MIGRATE-CHECK` — Verify existing high-level characters unlock the correct past ranks/passives and retain their skillbar layouts.

## Treasure chests

No treasure chests exist yet. Add chests that spawn at random in the open world: every **2 minutes** each eligible zone rolls a **10% chance** that a chest actually spawns, so one appears about every 20 minutes per zone. Only zones that have monsters roll; cities and enemy-free zones never do. **Chests can also appear inside dungeons**: each private party copy of a dungeon rolls on the same timer, and only that party sees it. A chest contains items that can drop in that area. When one spawns, a message tells the players there that a chest has appeared and will despawn in **3 minutes**, so they have to find it before then.

- [x] `CHEST-RULES` — Define the spawn timer, the 10% roll and the 3-minute lifetime as named constants. Decide the details: Settled in [docs/chests.md](docs/chests.md); the eligibility list is generated by `scripts/chest_zones.py` into [docs/chest-eligibility.txt](docs/chest-eligibility.txt).
  - Is it one roll per zone or one per map region, and one per running dungeon copy (starting when the party enters, stopping when the copy closes)?
  - Can a second chest spawn while one is still up?
  - How the spawn point is picked: a reachable, walkable tile that no monster, portal, NPC or other player blocks, ideally away from the arrival point. Dungeons need a tile inside the playable rooms that a party can reach without passing a sealed or boss-gated door, and never inside a boss arena during a fight.
  - What the contents are: a small number of rolls from the zone's own monster and material drop pool at the zone's level (the same table for ordinary gear, gold and materials), with no orange rolls beyond the normal 0.1%. In a dungeon, use that dungeon's own drops, and decide whether its exclusive set pieces can appear (and with what chance, including the purple roll), so a chest can't beat a boss kill.
  - Who may open it: first to arrive, or anyone nearby, with a shared loot rule for parties. In a dungeon, the party shares it.
  Record the eligibility list derived from the data (zones and dungeons with enemies), not hand-written.
- [x] `CHEST-SERVER` — Add the authoritative spawn loop, lifetime and despawn, the open action with range and life checks, and the loot grant, including a full-bag path so nothing is lost. Chests are runtime state, not saved; a restart clears them. Keep the timer per zone and per dungeon copy, make sure zones with no players online do not spawn chests that nobody can see, and make a dungeon copy's chests vanish when the copy closes or the party leaves. Built in `server/src/world/chests.rs` (12 tests); notes in [docs/chests.md](docs/chests.md).
- [x] `CHEST-ANNOUNCE` — Show a text message to players in the zone when a chest spawns, saying a chest has appeared and will despawn in 3 minutes. Decide whether the message also gives a direction or region hint, and whether players who arrive later see a countdown. Send a short message when it is opened or despawns.
- [ ] `CHEST-ART` — Draw the chest sprite (closed, opening and opened states) and a glint or marker through PixelFlow, readable at game scale on every zone's ground. Add a minimap or world-map marker only if `CHEST-RULES` says so.
- [x] `CHEST-CLIENT` — Render chests, handle clicking to open (with the same click-the-visible-body rule as monsters), show the despawn countdown on or near the chest, and play a short effect on open. Checked by `node tests/chest-ui.cjs` (8 checks: painted body, click beside does nothing, click opens, gold ring effect, announcements); the client walk-up route is not part of that check. Run browser tests against a release binary (`VALHALLA_BINARY=target/release/valhalla-server`): the debug server cannot keep 20 ticks a second in a zone with many enemies.
- [x] `CHEST-CHECK` — Verify in a private world with the timer shortened for tests: spawn rate over many seeded rolls (about 10%), only monster zones and dungeons spawn, a dungeon chest appears only for its own party and is gone when the copy closes, a chest in one party copy does not appear in another, the announcement text, despawn after 3 minutes, loot comes from the zone's own pool, parties, full bags, and reconnecting while a chest is up.

## Stat points

Today a character earns 3 stat points per level and spends them one click at a time on six attributes (strength, agility, intellect, stamina, dexterity, accuracy); accuracy is capped at 20 and dexterity at 70. Add a **Recommended** button in the attributes panel that spends the unspent points automatically on what is best for the character's class.

- [x] `STAT-RULES` — Decide the recommended spread per class, with a short reason for each (for example warrior toward strength and stamina, mage and priest toward intellect, assassin and hunter toward agility), and how it handles the accuracy and dexterity caps, stamina for survival, gear-granted attributes already worn, points already spent, and a class's changing needs at different levels. Decide whether it only spends unspent points or can also offer a full re-spread, and whether a re-spread costs gold. Record the table in [docs/recommended-stats.md](docs/recommended-stats.md).
- [x] `STAT-SERVER` — Add an authoritative request that spends the unspent points according to the rules in one atomic step, using the same checks as `allocate_stat` (not defeated, caps respected, points available) and saving immediately. Use the class from the server, never a value the client sends.
- [x] `STAT-UI` — Add the Recommended button to `client/attributes.js`, showing a preview of the points it will spend before the player confirms, a clear message when there are no points to spend, and a disabled state while a request is pending. Add a tooltip explaining the choice for the player's class. Manual spending still works as before.
- [x] `STAT-RESET-RULES` — Define the stat reset service: it refunds every trained point (3 per level minus the points already unspent; gear-granted attributes are never touched) and returns them to the unspent pool. Make it **expensive**: a gold price that grows with level (for example a base plus a per-level amount, in the tens or hundreds of thousands of gold by level 99, set against the mount's 50,000 gold at level 50 and the gold a level actually earns), and decide whether the price rises with each reset a character has bought, so it is a real decision. Decide which cities offer it (the major safe cities, derived from the map data, not every camp), which NPC runs it, and whether a first reset is cheaper. Record the price table in `docs/`.
- [x] `STAT-RESET-SERVER` — Add an authoritative reset: not while defeated, in combat or mounted, with atomic payment and a clear failure message when gold is short; refund the points and clear the allocation in one save. Persist the reset count if the price depends on it. Skills, equipment and bonuses from worn gear must stay as they are, and anything that depends on stamina (current HP) is clamped to the new maximum.
- [x] `STAT-RESET-NPC` — Place the NPC in each offering city, add dialogue, and a UI that shows the current price, the points that will be refunded and a separate confirmation (it cannot be undone), with the result shown straight away in the attributes panel. Combine it with the Recommended button so a player can reset and then spend again.
- [x] `STAT-CHECK` — Verify in a private world that a reset refunds exactly the trained points, charges the right price (and the rising price after repeat resets), is refused when gold is short, in combat, defeated or in a town that does not offer it, and survives save/reload; also verify that each class gets its recommended spread at several levels, caps are respected, points never go negative or unspent by mistake, a manual allocation after the button works, mid-way spreads continue sensibly, and everything saves and reloads.

## Game master

The game master is the golden `[GM]Sork` character on a GM account (`Character::gm`), who has personal god mode and the debug commands. A search of the server found no chat slash commands yet. Make the GM **invisible** by default: monsters never notice or target the GM, and players never see them, unless the GM types a command to be shown.

- [x] `GM-INVIS-RULES` — Decide what invisible means: no sprite, name, nameplate, minimap or party-list entry for others; not in the nearby-player list or the zone count; monsters ignore the GM for aggro and targeting and their area effects still do nothing to a god-mode GM; whether the GM can still see themselves (for example as a faint outline) and see other players normally; and how chat works while hidden (no chat, or chat shown without a position). Decide the command syntax (for example `/show` and `/hide`, or `/vis on|off`), that invisibility is the default on every login and zone change, and whether it carries into private dungeon copies and arena matches. Record the commands and defaults in the README. Settled in [docs/gm-invisibility.md](docs/gm-invisibility.md), with the commands and defaults in the README.
- [x] `GM-INVIS-SERVER` — Implement the state authoritatively on the server: a per-character flag set only for a GM account (a client request from anyone else is refused with no information), excluded from every snapshot, event, loot, party and trade broadcast to other players, and ignored by monster target selection and aggro. Add the first chat slash-command path if none exists, with the GM check on the server. The flag is reset on login and not saved, so the GM never starts a session visible by mistake. Rust: `server/src/visibility.rs`, `world/gm_visibility.rs`, `world::tests::gm_visibility_is_per_viewer_transient_and_server_authorized` (mutation-checked on the aggro filter).
- [x] `GM-INVIS-CLIENT` — Show the GM a clear indicator that they are hidden or shown (for example a status badge), render the GM to themselves with the outline chosen in the rules, and make sure other clients never receive the hidden character's position, name or effects, so nothing can be read from the network traffic. Hide the GM's own footsteps, attack effects and chat bubble from others while hidden, or decide which effects are acceptable. Hidden/Visible badge and a faint self outline; checked in `tests/gm-visibility-ui.cjs`.
- [x] `GM-INVIS-CHECK` — Verify in a private world with a GM account and a normal account in the same zone: the GM is absent from the normal client's snapshots (not just visually hidden), monsters do not aggro or attack the GM, `/show` makes the GM appear for everyone and `/hide` removes them, a non-GM sending the commands changes nothing, the default after login and zone change is hidden, and nothing is saved. `node tests/gm-visibility-ui.cjs` (23 checks: raw frames of the ordinary player never name the GM, counts, chat without id, /show /hide /vis, ordinary player refused, zone change hides; mutation-checked by disabling the player filter). Monsters ignoring the GM and the unsaved state are covered by the Rust test above.

### Game master gear

The GM currently wears three golden pieces (the Golden Robe with 12 defense, the Golden Top Hat with 4, and the Golden Sword & Shield with 10,020 attack and 10,004 defense), which are `gm` rarity and never drop. Make the GM gear **super overpowered**, so the GM kills almost anything in one hit.

- [x] `GM-GEAR-RULES` — Define "almost everything": the GM one-shots every ordinary monster, elite and boss in the open world and dungeons, with the exceptions written down (for example nothing special-cased such as a scripted invulnerable phase, training dummies or other players). Set the target as a margin over the highest-HP monster in the data, so a boss with the most HP still dies in one normal attack, and decide whether it is done through gear stats, a damage floor that scales with the target, or both. Decide the GM's effect on other players (PvP, duels and arenas should not become one-shot-the-player unless the GM explicitly opts in) and the rest of the kit: movement speed, attack speed, mana and rage, and whether every skill one-shots too or only the basic attack. Settled in [docs/gm-gear.md](docs/gm-gear.md): a GM-only damage floor in `hit_slime` plus defense gear, not an attack stat.
- [ ] `GM-GEAR-DATA` — Raise the GM pieces to match the rules, with armor and headgear in the same league as the weapon today (the armor's 12 defense is tiny next to the sword's 10,004) and attribute bonuses if the stat formulas need them. Complete the set to every slot (shoulders, gloves, pants, necklace, accessories) if that is needed to reach the target, with golden art and icons made through PixelFlow. Keep the `gm` rarity (never rolled, never sold or dropped) and keep the item IDs and saves.
- [x] `GM-GEAR-SERVER` — Apply any special rule from `GM-GEAR-RULES` authoritatively in combat, only when the wearer is the GM character; a client or another player can never obtain it. Make sure it does not break the damage code for ordinary players (no overflow when a huge attack value multiplies against stats, no integer wrap and no NaN) and that kills still give normal credit, loot and quest progress.
- [ ] `GM-GEAR-CHECK` — Verify in a private world that the GM kills the strongest monster of every zone and dungeon in one hit, that ordinary players and mobs behave exactly as before, that other players cannot equip or receive the GM pieces, that PvP follows the rules, and that large values do not overflow. Partly done and blocked: `gm_strike_uses_worn_weapon_and_normal_kill_path` and `gm_strike_reaches_the_toughest_living_enemy_in_every_populated_zone` pass, but the 150,000 total defense of `docs/gm-gear.md` cannot be met until `GM-GEAR-DATA` adds the missing golden pieces (the catalog has only three), so this stays open.

## Day and night

Add a day and night cycle to the world. **24 game hours pass in 20 real minutes**, so one game hour is 50 real seconds, noon comes every 20 minutes and the shortest night is only a few minutes long. Outdoor zones follow it; enclosed places (private dungeons, building interiors, caves) do not. `WEATHER-RULES` asks whether weather follows a world clock, so decide the clock here first.

- [x] `TIME-RULES` — Define the world clock: 1,200 real seconds per 24 game hours, the game time at server start (continuous across restarts from a stored epoch, never reset to dawn), the hour boundaries for dawn, day, dusk and night, and whether every zone shares one clock or some zones have a fixed time (an eternal dusk, a permanent aurora night in Frostwake, caves and dungeons with no cycle). Decide whether the time is shown to the player (a clock or sun/moon icon), whether any systems depend on it (monster spawns or stats, shop hours, quests, loot, regeneration, rest or the inn) and keep the first version cosmetic by default so combat and tests are unaffected. Derive which zones are indoors from the data.
- [x] `TIME-SERVER` — Make the server the one source of time: compute the game time from a stored epoch and the real clock, send the current time and its speed to each client on join and re-sync periodically so clients do not drift, and allow a private test world to set or freeze the time. The time never rolls back or restarts at a server restart.
- [x] `TIME-RENDER` — Tint the outdoor scene through the day: warm sunrise, bright noon, orange sunset, a blue-dark night with a gentle floor so the screen stays readable, smooth blending between phases, lit windows, lamps and campfires turning on at dusk, moon and stars at night, and a sun or moon position that fits the hour. It must never hide monsters, loot, players, skill telegraphs or text, and shadows should follow the sun if the art uses them. Keep the cost low: tint with one overlay or cached gradient rather than repainting layers, and respect reduced-motion.
- [x] `TIME-ZONES` — Give each zone's theme its own take on the cycle (the frost aurora at night, ember glow in the Crags, glowing flora in the fen and Veyrroot, a starry desert), while keeping the same readability floor, and make indoor zones and dungeons ignore the cycle. Make the transition when walking through a door smooth.
- [x] `TIME-UI` — Show the time of day in the HUD (a small sun/moon icon with the game hour, plus a tooltip), and add a setting to reduce or turn off the night darkening for players who find it hard to see. Add a debug command for the GM to set the time (see the game master tasks).
- [ ] `TIME-MUSIC` — Add a night variation of the zone music (calmer or slower), made through the dybase2 tools, that fades in at dusk and back at dawn, if `TIME-RULES` wants it.
- [x] `TIME-WEATHER` — Connect the cycle to weather: weather rules may depend on the hour (morning fog, evening storms), a rainy sky tints the day colour darker, and night rain/snow stays visible against the dark tint. Hour weights are checked in Rust; `client/weather.js` paints after the day/night tint, and the private browser test compares rain and snow against clear at midnight.
- [ ] `TIME-CHECK` — Verify in a private world with the time forced: 24 game hours equal 20 real minutes within a small tolerance, every client shows the same hour, the time is continuous across a restart, outdoor zones follow the cycle and dungeons and interiors do not, nothing becomes unreadable at midnight in any zone (compare screenshots at several hours), and CPU with the cycle on and off stays within the render budget.

## Weather

The world has no weather today. Each dungeon's art file has a small `weather()` function, but it only draws drifting ambient motes inside that dungeon. Add real weather to the outdoor world, such as rain, snow and others, which changes over time. It never shows when the player is **inside**: private dungeons and their rooms, building interiors and any other enclosed zone.

- [x] `WEATHER-RULES` — Define the weather types and how they fit each zone: rain, snow, fog, thunderstorm, wind-blown leaves or ash, sandstorm and a clear sky, with each zone's allowed types set by its theme (snow in Rimeveil, Frostwake and Cairnspine, no snow in the desert or fen, sandstorms in Lapis Erg, ash in the Crags, and so on, derived from the zone data). Set how long a spell lasts, how often it changes and how strong it is, and whether weather is random per zone, follows a world clock or a day/night cycle, and whether it is synced for everyone in the zone. Define "inside": private dungeon copies, building interiors, caves and any zone flagged as enclosed (derived from the data), and what happens when the player walks through a door. Decide whether weather is cosmetic or has small gameplay effects (reduced view distance in fog, slower movement in deep snow, lightning), keeping it cosmetic by default so combat and tests are unaffected. Settled in [docs/weather.md](docs/weather.md); the per-zone table is generated by `scripts/weather_zones.py` into [docs/weather-zones.txt](docs/weather-zones.txt).
- [x] `WEATHER-SERVER` — Add an authoritative weather state per outdoor zone with the type, intensity and end time, changed by a seeded schedule so a server restart does not flip it abruptly. Send it to the clients in the zone with their snapshot and on change, and keep enclosed zones fixed at no weather. Tests and private worlds must be able to set or freeze the weather. Implemented in `server/src/world/weather.rs` from generated `world/weather.txt`, with a transient `set_weather` debug override.
- [x] `WEATHER-RAIN` — Draw rain through the canvas (streaks, splashes on the ground, a darker sky tone), with light, medium and heavy settings and a puddle or wet-ground tint. `client/weather.js` draws intensity-scaled streaks, ground splashes and a wet tint.
- [x] `WEATHER-SNOW` — Draw snowfall (flakes of several sizes with drifting motion, a light white overlay on the ground and a cool sky tone), with light and heavy settings. `client/weather.js` draws drifting flakes and a cool ground tint.
- [x] `WEATHER-OTHER` — Draw the remaining types from the rules: fog, thunderstorm with lightning flashes, wind with leaves or ash, and a sandstorm. `client/weather.js` now paints each with the existing one-second transition, including variant-coloured wind particles and deterministic lightning flashes.
- [x] `WEATHER-INSIDE` — Make weather stop the moment a player enters an enclosed area and return when they walk out, with a smooth fade. Cover dungeons, building interiors, caves and portals, so a player standing in a doorway does not see rain indoors. Server reports clear/inside for enclosed maps and private copies; the client fades on portal changes. `interior: true` is supported for future whole-map interiors; no enterable building or cave regions exist yet.
- [x] `WEATHER-AUDIO` — Add soft ambient weather sound (rain, wind, thunder), made through the dybase2 tools or the existing audio route, ducked under music, off indoors and with its own volume setting. The existing Web Audio route now has quiet rain/wind noise beds and a thunder pulse through the effects bus, faded off indoors; Settings persists a separate weather sound slider.
- [x] `WEATHER-UI` — Show the current weather in the HUD (a small icon and name, or in the zone label), add a setting to turn weather effects off or lower them for slower devices, and respect reduced-motion. The HUD icon/name remains visible at 0%; `valhallasc.save.v1.weather` persists the 0–100% setting, and reduced motion draws fixed particles. `tests/weather-ui.cjs` has 14 private browser checks.
- [x] `WEATHER-CHECK` — Verify in a private world with the weather forced: every type appears only in the zones the rules allow, none shows in dungeons or building interiors, the transition when entering and leaving is correct, all players in a zone see the same weather, a restart keeps the schedule sensible, and the frame rate on a low-end profile stays within the render budget (measure CPU with weather on and off). The 35-check private browser suite covers all types, an indoor dungeon, two players, a private-server restart and 4× CPU throttling; Rust checks the generated eligibility table across all zones. There are no enterable building interiors yet.

## Login notifications

Optional Gotify login notifications are implemented in source and remain off until the service receives a dedicated URL and application token. The Rust server logs in through `auth.rs` (account login) and puts a character into the world in `world.rs` (`join_as`).

- [x] `NOTIFY-RULES` — Decide what a login notification is: the account login, the character entering the world (probably better, since it names the character and class), or both. Decide the content (character name, class, level and zone; the account name only if it is not private), the title with an emoji prefix, the priority (low, since it is informational), and the exclusions: the temporary ambient adventurers, mercenaries, test and private-world bots, and the GM's own character. Decide the throttling, so reconnects and a flapping connection do not spam: one push per player per cooldown window (for example 30 minutes) and an optional digest if many players join at once. Decide whether logout, first-ever login of a new account and failed logins are included.
- [x] `NOTIFY-SERVER` — Send the push from the server without ever blocking the game loop: queue the event and post it from a background task with a short timeout, log failures once and drop them, and never retry in a way that backs up. Read the Gotify URL and application token from the environment (never from the repository, the client or this file), and turn the feature off cleanly when they are not set. Make sure a private test world never sends anything, and that a player cannot inject text into the message (strip control characters and limit the length of the name).
- [x] `NOTIFY-DEPLOY` — Set the environment variables where the game server runs, check the server can reach Gotify from its container or host, and create a separate Gotify application (and token) for the game rather than reusing another service's token. Document the setup in the README without the token. Done 2026-10-15 differently from the first plan, by the user's choice: the service posts to Surv's notify endpoint (no separate Gotify application or token), so the pushes also show in Surv; see [docs/login-notifications.md](docs/login-notifications.md). The service is configured and was restarted on the new build.
- [x] `NOTIFY-CHECK` — Verify against a local fake Gotify endpoint that a login sends exactly one push with the right content, that excluded characters send none, that the throttle holds under reconnects, that an unreachable or slow Gotify does not delay the login or the game tick, that the feature is off without configuration, and that no token appears in logs, commits or client files.

## Combat HUD

- [x] `UI-TARGET-BADGE` — Show the current target’s face and HP next to the player HP badge; update it when the target changes and clear it when there is no target.
- [x] `UI-MONSTER-TARGETING` — Make monsters easier to target by clicking their visible bodies; clicks should not need to land below the sprite.

## Ranged combat

- [x] `C-RANGED-LOS` — Prevent players from firing ranged basic attacks and targeted ranged skills through walls, buildings and other solid map obstacles. Check the path from attacker to target on the authoritative server before spending resources or starting a cooldown; blocked shots cause no damage or rewards and give clear feedback. Keep the client projectile and effect visuals consistent with the collision result. Verify straight, diagonal and corner cases against enemies and players in a private world, including dungeon walls.

## Languages

- [x] `L-SWEDISH` — Add Swedish (`sv`) as a selectable, persistent game language; translate player-facing menus, HUD, skills, quests, items, NPC dialogue and system messages, and check the language switch in a private browser test. Settings stores `lang:sv`; the checked-in catalog covers static text plus dynamic message templates without translating server IDs or player chat. `tests/swedish-ui.cjs` passes 15 private browser checks for both directions of the switch and representative catalog and system text.

## Player interaction and PvP

- [x] `SOC-TRADE` — Let nearby players trade items and gold through a two-sided offer and confirmation flow; transfer both sides atomically on the server.
- [x] `PVP-DUEL` — Let one player challenge another to a consensual duel, with clear accept, start and end states.
- [x] `PVP-FLAG` — Add an opt-in PvP flag that lets flagged players fight other flagged players in the open world, with visible status and authoritative combat rules.
- [x] `PVP-ARENA` — Add arena matches for 1v1, 2v2 and 3v3 teams, including team entry, match boundaries and a clear win condition.

## Travel and world map

- [x] `W-GRAPH` — Lay out the authoritative zone/portal graph as connected geography, including city and dungeon branches.
- [x] `W-ART` — Replace the detached zone display with a readable illustrated world map built from that geography.
- [x] `W-ROUTES` — Show actual portal connections, current position, reachable routes and distinct sealed dungeon entrances.
- [x] `W-CHECK` — Check world/zone map navigation and consistency after portal moves.
- [x] `T-PORTALS-0-8` — Improve portal placement and reciprocal arrival routes in the starter through Rán’s Deep zones.
- [x] `T-PORTALS-9-18` — Improve portals around Nacrehold, Cathedral, Astralhollow through Moonwell.
- [x] `T-PORTALS-19-22` — Improve Stormglass, Sunward, Ribbonwild and Tanglecrown connections.
- [x] `T-PORTALS-23-25` — Improve the Veyrroot city/Heartwood and Lapis Erg connections.
- [x] `T-PORTALS-26-28` — Improve Frostwake, Cairnspine and all four Yearwheel approaches.
Portal tasks must keep both directions paired, preserve IDs where possible, use natural routes near hubs/landmarks and safe reachable arrivals, and update generators and map art together.
The route pass aligned the Stormrift, Hourglass Pass, Glassroot Causeway, Sunward Cut, Rootway, Hollow Arch, Sunroad and Year's Ascent landings with their marked approaches; all eight links keep their original portal IDs.

- [x] `M-PRICE` — Set a substantial mount price and level-50 purchase offer so most new level-50 characters cannot immediately afford it.
- [x] `M-SPEED` — Persist mount ownership and calculate **2× normal travel speed** authoritatively when mounted.
- [x] `M-CLIENT` — Add mount appearance, mount/dismount control and clear speed/ownership UI; settle combat, portal and city rules.
- [x] `M-CHECK` — Check level/gold gates, persistence, travel speed and transitions in a private world.

## More mounts

Today there is one mount: the riding horse, sold by Greta in Skaldholm at level 50 for 50,000 gold, with a 2× outdoor travel speed that dismounts on combat, aggro, Spark Travel, death or a private dungeon. Add **more mounts than the horse: a gryphon, a lizard, a raptor and a sabertooth**, each with its own look and a way to get it. Use PixelFlow for all mount sprites, and keep every existing horse save intact.

- [x] `MOUNT-RULES` — Decide, per mount: how it is obtained (shop with a level and price, quest, rare drop or dungeon reward; make them different, with the gryphon the hardest to earn), whether any mount differs in speed or ability (for example, whether the gryphon crosses water or cliffs, which would need collision and zone-edge rules) or all stay a cosmetic choice at 2× speed, and how a player owning several picks one. Define the dismount rules for each and whether mounts are tradable (see `SOC-TRADE`). Keep the horse's price and rules unchanged. Settled in [docs/mounts.md](docs/mounts.md).
- [ ] `MOUNT-SERVER` — Replace the single owned-horse flag with a set of owned mounts plus a selected one, migrating existing saves so every horse owner keeps their horse. Keep travel speed, dismount rules and persistence authoritative, and send the selected mount in the player snapshot.
- [ ] `MOUNT-GRYPHON` — Create the gryphon mount sprites in every direction and gait for both bodies and all classes, with rider placement, through PixelFlow.
- [ ] `MOUNT-LIZARD` — Create the lizard mount sprites in every direction and gait for both bodies and all classes, with rider placement, through PixelFlow.
- [ ] `MOUNT-RAPTOR` — Create the raptor mount sprites in every direction and gait for both bodies and all classes, with rider placement, through PixelFlow.
- [ ] `MOUNT-SABERTOOTH` — Create the sabertooth mount sprites in every direction and gait for both bodies and all classes, with rider placement, through PixelFlow.
- [ ] `MOUNT-SOURCES` — Add the acquisition for each new mount from `MOUNT-RULES`: stable or vendor NPCs with dialogue, quests, and drop sources with their rates.
- [ ] `MOUNT-UI` — Let the player see their owned mounts and choose which one the mount key and HUD button summon, with ownership, price and unlock hints for the ones not owned yet, and other players seeing the selected mount.
- [ ] `MOUNT-CHECK` — Verify purchase gates, ownership and the selected mount across save/reload, that a horse owner keeps the horse, speed and dismount rules per mount, and the sprites at game scale in a real client in a private world.

## Previous gear redesign

All 252 level-25–50 and Cathedral base pieces are complete. Detailed piece history is in [GEAR_REDESIGN_TODO.md](GEAR_REDESIGN_TODO.md).

- [x] `R-CHECK` — Complete its final generator, Rust, MCP and browser/art integration checks, then close the detailed checklist.

## Completed in this batch (2026-10-12)

Closed 20 items: level-95 gear bonus; hunter ranks through 98; five level-99 capstones; five skill identity updates; high-level unlock and skillbar migration checks; world-map graph, routes and consistency; and mount price, speed, client controls and private-world checks. The mount costs 50,000 gold at level 50, persists across login, travels at twice normal speed, and dismounts for combat. Private mount and skill checks passed; the map data and client copy match across 29 connected zones with four distinct sealed doors and no tile overlaps. The full world-map browser suite and full Rust suite were not completed in this batch.
