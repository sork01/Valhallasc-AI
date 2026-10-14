# Valhalla game TODO

Pick any task by its **ID** (for example, `I65-MAP` or `A70-MAGE`). Each checkbox is one deliverable, and its ID stays stable if the list is reordered. Use focused private checks for the chosen change. An instance entrance stays sealed until its `OPEN` task is complete.

Rules for every TODO: use the `createmap` skill for all zone work; create all sprites through the PixelFlow API; create all music through the dybase2 MCP.

Audit basis: `world/map.txt`, `world/items.txt`, `world/skills.txt`, gear generators and server loot rules on 2026-10-11. Already playable: Undervault (20), Drowned Cathedral wings (40/45/50), Moonwell (60).

Core dependencies: each instance's `OPEN` task follows its four content tasks; randomized orange items and refinement use `G-INSTANCE-DATA`; orange pieces/drop rules use `O-RULES`; later skill ranks use `S-RANK-RULES`; world-map art/routes use `W-GRAPH`. Work on a selected task can start before a related feature is ready to release.

## Instances

Each instance has a separate map, encounter, quest/reward, presentation and opening task. The four Yearwheel doors are four different instances.

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
- [ ] `A75-ASSASSIN` — Create and wire the five level-75 assassin pieces and icons.
- [ ] `A75-PRIEST` — Create and wire the five level-75 priest pieces and icons.
- [ ] `A75-HUNTER` — Create and wire the five level-75 hunter pieces and icons.
- [ ] `A75-SHARED` — Create and wire the three shared level-75 pieces and icons.

#### Level 80

- [ ] `A80-WARRIOR` — Create and wire the five level-80 warrior pieces and icons.
- [ ] `A80-MAGE` — Create and wire the five level-80 mage pieces and icons.
- [ ] `A80-ASSASSIN` — Create and wire the five level-80 assassin pieces and icons.
- [ ] `A80-PRIEST` — Create and wire the five level-80 priest pieces and icons.
- [ ] `A80-HUNTER` — Create and wire the five level-80 hunter pieces and icons.
- [ ] `A80-SHARED` — Create and wire the three shared level-80 pieces and icons.

#### Level 85

- [ ] `A85-WARRIOR` — Create and wire the five level-85 warrior pieces and icons.
- [ ] `A85-MAGE` — Create and wire the five level-85 mage pieces and icons.
- [ ] `A85-ASSASSIN` — Create and wire the five level-85 assassin pieces and icons.
- [ ] `A85-PRIEST` — Create and wire the five level-85 priest pieces and icons.
- [ ] `A85-HUNTER` — Create and wire the five level-85 hunter pieces and icons.
- [ ] `A85-SHARED` — Create and wire the three shared level-85 pieces and icons.

#### Level 90

- [ ] `A90-WARRIOR` — Create and wire the five level-90 warrior pieces and icons.
- [ ] `A90-MAGE` — Create and wire the five level-90 mage pieces and icons.
- [ ] `A90-ASSASSIN` — Create and wire the five level-90 assassin pieces and icons.
- [ ] `A90-PRIEST` — Create and wire the five level-90 priest pieces and icons.
- [ ] `A90-HUNTER` — Create and wire the five level-90 hunter pieces and icons.
- [ ] `A90-SHARED` — Create and wire the three shared level-90 pieces and icons.

#### Level 95

- [ ] `A95-WARRIOR` — Create and wire the five level-95 warrior pieces and icons.
- [ ] `A95-MAGE` — Create and wire the five level-95 mage pieces and icons.
- [ ] `A95-ASSASSIN` — Create and wire the five level-95 assassin pieces and icons.
- [ ] `A95-PRIEST` — Create and wire the five level-95 priest pieces and icons.
- [ ] `A95-HUNTER` — Create and wire the five level-95 hunter pieces and icons.
- [ ] `A95-SHARED` — Create and wire the three shared level-95 pieces and icons.

### Dungeon and endgame gear

- [x] `G-VAULT-ART` — Give the 27 Undervault-exclusive level-20 pieces a distinct visual direction; record how its class and shared pieces differ from starter gear.
- [ ] `G-VAULT-EXPORT` — Export/wire the Undervault worn layers and matching icons without changing item IDs or existing loot.
- [x] `G-MOON-CATALOG` — Define a Moonwell-exclusive level-60 blue set and boss slot pools; currently Moonwell bosses give ordinary blue gear.
- [ ] `G-MOON-ART` — Create Moonwell set worn art and icons.
- [x] `G-MOON-LOOT` — Switch the four Moonwell bosses to their exclusive set and verify party drops.
- [x] `G-YEAR-SPRING` — Define level-97 Blooming Labyrinth gear rewards.
- [x] `G-YEAR-SUMMER` — Define level-98 Solar Crucible gear rewards.
- [x] `G-YEAR-AUTUMN` — Define level-99 Amber Archive gear rewards.
- [x] `G-YEAR-WINTER` — Define level-99 Silent Solstice gear rewards.

The four sealed dungeon reward sets reserve 44 item designs in [world/yearwheel_rewards.txt](world/yearwheel_rewards.txt); no sealed door or loot table is active yet.

- [x] `G95-BONUS` — Decide the level-95 attribute bonus and remove the current clamp to the level-90 value if a larger bonus is intended.

## Skills

Regular skills/ranks arrive every two levels from 2 through 98, plus a level-99 class capstone. The extra preferably passive class milestones at 10, 20, …, 90 are separate rewards. Existing characters receive all ranks earned by their saved level.

- [x] `S-RANK-RULES` — Add skill-rank data, server unlock/combat rules and client rank descriptions without losing saved skillbar assignments.
- [x] `S-RESPACE-WARRIOR` — Spread the existing warrior kit across levels 2–20 and design which abilities gain later ranks.
- [x] `S-RESPACE-MAGE` — Spread the existing mage kit across levels 2–20 and design which abilities gain later ranks.
- [x] `S-RESPACE-ASSASSIN` — Spread the existing assassin kit across levels 2–20 and design which abilities gain later ranks.
- [x] `S-RESPACE-PRIEST` — Spread the existing priest kit across levels 2–20 and design which abilities gain later ranks.
- [x] `S-RESPACE-HUNTER` — Spread the existing hunter kit across levels 2–20 and design which abilities gain later ranks.

The unlock and rank layout is recorded in [docs/skill-ranks.md](docs/skill-ranks.md).

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

## Combat HUD

- [x] `UI-TARGET-BADGE` — Show the current target’s face and HP next to the player HP badge; update it when the target changes and clear it when there is no target.
- [x] `UI-MONSTER-TARGETING` — Make monsters easier to target by clicking their visible bodies; clicks should not need to land below the sprite.

## Player interaction and PvP

- [x] `SOC-TRADE` — Let nearby players trade items and gold through a two-sided offer and confirmation flow; transfer both sides atomically on the server.
- [x] `PVP-DUEL` — Let one player challenge another to a consensual duel, with clear accept, start and end states.
- [x] `PVP-FLAG` — Add an opt-in PvP flag that lets flagged players fight other flagged players in the open world, with visible status and authoritative combat rules.
- [x] `PVP-ARENA` — Add arena matches for 1v1, 2v2 and 3v3 teams, including team entry, match boundaries and a clear win condition.

## Travel and world map

- [x] `W-GRAPH` — Lay out the authoritative zone/portal graph as connected geography, including city and dungeon branches.
- [ ] `W-ART` — Replace the detached zone display with a readable illustrated world map built from that geography.
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

## Previous gear redesign

All 252 level-25–50 and Cathedral base pieces are complete. Detailed piece history is in [GEAR_REDESIGN_TODO.md](GEAR_REDESIGN_TODO.md).

- [x] `R-CHECK` — Complete its final generator, Rust, MCP and browser/art integration checks, then close the detailed checklist.

## Completed in this batch (2026-10-12)

Closed 20 items: level-95 gear bonus; hunter ranks through 98; five level-99 capstones; five skill identity updates; high-level unlock and skillbar migration checks; world-map graph, routes and consistency; and mount price, speed, client controls and private-world checks. The mount costs 50,000 gold at level 50, persists across login, travels at twice normal speed, and dismounts for combat. Private mount and skill checks passed; the map data and client copy match across 29 connected zones with four distinct sealed doors and no tile overlaps. The full world-map browser suite and full Rust suite were not completed in this batch.
