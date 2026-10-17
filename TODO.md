# Valhalla game TODO

Pick any task by its **ID** (for example, `I65-MAP` or `A70-MAGE`). Each checkbox is one deliverable, and its ID stays stable if the list is reordered. Use focused private checks for the chosen change. An instance entrance stays sealed until its `OPEN` task is complete.

Rules for every TODO: use the `createmap` skill for all zone work; create all sprites through the PixelFlow API; create all music through the dybase2 MCP.

Audit basis: `world/map.txt`, `world/items.txt`, `world/skills.txt`, gear generators and server loot rules on 2026-10-11. Already playable: Undervault (20), Drowned Cathedral wings (40/45/50), Moonwell (60).

Core dependencies: each instance's `OPEN` task follows its four content tasks; randomized orange items and refinement use `G-INSTANCE-DATA`; orange pieces/drop rules use `O-RULES`; later skill ranks use `S-RANK-RULES`; world-map art/routes use `W-GRAPH`. Work on a selected task can start before a related feature is ready to release.

## Instances

Each instance has a separate map, encounter, quest/reward, presentation and opening task. The four Yearwheel doors are four different instances.

The former `I-VISUAL-IDENTITY` umbrella is split into one deliverable per private dungeon zone below. For each, give the interior distinctive floor and wall materials, room shapes, landmarks, props, palette and lighting. Keep paths, collision and combat effects readable, and compare its screenshot with the other dungeons in a private browser check. The Drowned Cathedral's three separately rendered wings have separate tasks.

- [x] `I-VISUAL-Z5` — Redesign The Undervault (zone 5) as a buried stronghold with its own vault masonry, chambers, machinery and lighting. Distinct chamber floors, boss dais rings, forge gearwork, brass-banded walls and brighter vault lighting; private screenshots checked against all other dungeons with `tests/undervault-visual-ui.cjs`.
- [x] `I-VISUAL-Z10` — Redesign the Drowned Cathedral's Flooded Cloister (zone 10) around submerged walkways, cloister arches and water-worn religious details. Raised stone routes and circular courts cross shallow teal water; pointed wall arcades, tide marks, worn chapel inlays and cooler lighting distinguish it from the other wings. Real-sprite private Cathedral browser screenshots and 168 checks passed.
- [x] `I-VISUAL-Z11` — Redesign the Drowned Cathedral's Coral Reliquary (zone 11) around coral-grown relic chambers, tidal pools and luminous marine details. Pearl-stone routes cross teal tidal pools; each boss court has a distinct inlaid color, coral relief and glowing relic cases. Real-sprite private Cathedral browser checks and room captures passed.
- [x] `I-VISUAL-Z12` — Redesign the Drowned Cathedral's Grand Nave (zone 12) as a monumental drowned sanctuary with a distinct central aisle, altar and stained-glass light. Dark marble side aisles, blue ceremonial paving, gold court borders, stained-glass windows and a violet altar; real-sprite private Cathedral browser checks and nave captures passed.
- [x] `I-VISUAL-Z18` — Redesign The Moonwell (zone 18) as an open-water garden of petal islands, glass causeways and moonlit reflections. Four colored petal courts, silver island floors, pale glass routes, shoreline ripples and sky reflections; real-sprite private Moonwell browser checks and island captures passed.
- [x] `I-VISUAL-Z29` — The Eye Below now has lens-shaped observation courts, deepglass inlays and illuminated wall apertures.
- [x] `I-VISUAL-Z30` — The Elder Hollow now has growth-ring courts, root-veined floors and living wall recesses.
- [x] `I-VISUAL-Z31` — The Thousandfold Pavilion now has folded-screen floor panels, fan inlays and silk gallery walls.
- [x] `I-VISUAL-Z32` — Temple of the Rain Crown now has stepped ritual courts, rain channels and wet jade walls.
- [x] `I-VISUAL-Z33` — The Seed Vault now has concentric seed courts, botanical floor marks and germination recesses.
- [x] `I-VISUAL-Z34` — The Sunken Astrolabe now has bronze orbital courts, star-chart tiles and instrument walls.
- [x] `I-VISUAL-Z35` — The Thunderheart Gate now has conductive floor circuits, pylon courts and charged wall channels.
- [x] `I-VISUAL-Z36` — The Blooming Labyrinth now has petal-shaped courts, flower mosaics and garden walls.
- [x] `I-VISUAL-Z37` — The Solar Crucible now has furnace-ring courts, gearwork floors and radiant forge walls.
- [x] `I-VISUAL-Z38` — The Amber Archive now has shelf-grid courts, memory marks and amber library walls.
- [x] `I-VISUAL-Z39` — The Silent Solstice now has icy star courts, frost cracks and aurora-lit frozen walls.

All eleven later interiors keep their existing collision rooms but now use different structural silhouettes: living bark and seed roots, painted folding screens, ritual water terraces, bronze observatory mechanisms, charged conduits, flower hedges, furnace walls, amber shelves and faceted ice. Their floor materials, inlays, indoor light and backdrops differ as well. `tests/later-dungeon-visual-ui.cjs` captures an entry, court and landmark in each private zone beside five earlier dungeons for comparison.

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

- [x] `SET-RULES` — Define what counts as a set (each dungeon's 28 exclusive items, plus Undervault and Moonwell), how pieces are counted (distinct equipped slots, refined copies, orange pieces). **Set membership depends on the piece, not its rarity**: a piece merged up to a higher rarity, or a copy with different rolled stats or refinement, still counts toward its set, so rarity never breaks or changes a set bonus (rarity may still affect the piece's own stats), the tier structure and the power budget so 8 pieces beat mixed gear without being mandatory. Each class has a unique ordered skill triplet for every set, and every 8-piece effect has a distinct mechanic. Record the full set-by-class matrix in a doc beside `docs/skill-ranks.md`.
- [x] `SET-SERVER` — Add authoritative set tracking: count equipped pieces per set, recompute on equip, unequip, merge, refine and login, and apply the stat, cooldown and skill-power effects in combat. Cooldown and power changes must stack correctly with skill ranks and passives.
- [x] `SET-UI` — Show set membership and the 2/4/6/8 tiers in item tooltips and the equipment panel: pieces worn out of the total, active tiers highlighted, inactive ones greyed with what they unlock. Add a short on-screen cue when a tier activates or drops.
- [x] `SET-WARRIOR` — Define the 2/4/6/8 bonuses for warriors in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon. Matrix: [docs/set-bonuses.md](docs/set-bonuses.md).
- [x] `SET-MAGE` — Define the 2/4/6/8 bonuses for mages in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon. Matrix: [docs/set-bonuses.md](docs/set-bonuses.md).
- [x] `SET-ASSASSIN` — Define the 2/4/6/8 bonuses for assassins in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon. Matrix: [docs/set-bonuses.md](docs/set-bonuses.md).
- [x] `SET-PRIEST` — Define the 2/4/6/8 bonuses for priests in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon. Matrix: [docs/set-bonuses.md](docs/set-bonuses.md).
- [x] `SET-HUNTER` — Define the 2/4/6/8 bonuses for hunters in every dungeon set, with **different perks per set** (different skills, effects and 8-piece mechanic for Undervault, Moonwell and each later dungeon), themed to that dungeon. Matrix: [docs/set-bonuses.md](docs/set-bonuses.md).
- [x] `SET-EFFECTS` — Give the 8-piece bonuses and doubled-skill (6-piece) bonuses distinct visual feedback on the skill, so players can see that a set effect is active.
- [x] `SET-CHECK` — Verify that no two sets give the same class identical perks (derive the matrix from the data and assert uniqueness), then check tier counting across mixed rarities (for example, 4 base pieces plus 4 merged pieces still make an 8-piece set), class gating, stacking with ranks and passives, unequip and swap behavior, save/reload, and PvP balance in focused private tests.

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

## Bank

Owner's request (2026-10-17): a **bank** and a **banker in each of the five big cities** (Alderhaven, Skaldholm, Nacrehold, Astralhollow and Asterion, the same five that offer the stat reset), so a player can store items and not carry everything around. The camps, refuges and stations get no banker. The bank is the same in all five. Work in this order: `BANK-RULES`, then `BANK-SERVER`, then the NPC, UI and art tasks, then `BANK-CHECK`.

- [x] `BANK-RULES` — Settled 2026-10-17 in [docs/bank.md](docs/bank.md). The bank is `Character.bank` (items, gear copies, gold, expansions), per character, the same in the five big cities. Stores any loose item and gear copy with its data (new id on withdrawal), the two licences included; not worn pieces, starter or GM gear, fitted bags. Capacity counts one cell per item ID like the bags: 48 cells, four paid expansions of +12 (10,000, 40,000, 120,000, 300,000 gold) up to 96. No fees, no level gate; a separate gold balance that services never touch. Needs the banker within 2.8 tiles; refused while defeated, in combat or mounted; every request atomic with one save. Quests, merge, refine, sell and trade use the bags only; rebirth keeps the bank; deleting a character deletes it. The five bankers and their lines are in the doc.
- [x] `BANK-SERVER` — Done 2026-10-17: `server/src/bank.rs` (rules, numbers, `Character.bank`) and `server/src/world/bank.rs` (the five `bank_*` messages, saved before assigned); wire format in [docs/bank.md](docs/bank.md). 18 Rust tests (a stack whole and in part, a gear copy by id with its refinement, gold, expansions, full bank, full bag, worn, game master gear, out of range, wrong NPC and zone, defeated, in combat, mounted, a double request, reload, legacy save, a seeded random run that loses and copies nothing) plus the rebirth test. Spec: Add the bank to the saved state (`#[serde(default)]`, so every old save has an empty bank) and authoritative `bank_deposit`, `bank_withdraw`, `bank_gold` and `bank_open` messages. Each checks life, the banker's range in the character's zone, the refusals from `BANK-RULES` and capacity on both sides, and applies in **one atomic step and one save**, as the stat reset does, so a crash or a double click can never lose or copy an item. Gear copies move with their data. Send the bank in the dialogue packet only while the window is open (not in every snapshot). Tests in Rust: deposit and withdraw of a stack, a partial stack, a gear copy with its refinement, gold, a full bank, a full bag, an item that is worn, a bound item, out of range, defeated, a double request, a save and reload, a legacy save, and that the total of every item and gold is unchanged by any sequence of requests.
- [x] `BANK-NPC` — Done 2026-10-17: `scripts/bank_npcs.py` (run by `sync-world.cjs`, idempotent, errors on a missing, doubled or stray banker) places the five; positions, looks and lines are in that script, the Swedish text is in `scripts/sv-translations.txt` and `client/sv-data.js`. Checks: the Rust test `exactly_five_bankers_stand_beside_their_plazas_clear_of_everything_and_nowhere_else` and `tests/bank-npcs.py`; all five answer `talk_to` on a live private server. The button still opens nothing until `BANK-UI`. Spec: A banker NPC with a `bank` offer in each of the five big cities, placed beside the plaza near the other service NPCs and not on a route. An idempotent script (as `scripts/stat_reset_npcs.py`, which already lists the five cities) adds one banker to each and is run by `scripts/sync-world.cjs`, and a check fails when one of the five has none or two, or any other city has one. Each banker has a name and a line of dialogue that fits their city, and the Swedish text exists for them. Keep the bankers out of the escort, ambush and chest placement rules (the chest tests keep NPCs 3 tiles away).
- [ ] `BANK-UI` — A bank window opened by talking to a banker: the bank grid beside the bag grid, click or drag to deposit and withdraw, shift-click for a whole stack and a quantity box for part of one, the same item tooltips and rarity colours as the bags, bank and bag capacity counters, a gold deposit and withdraw field, a clear message for every refusal, the expansion offer with its price, and keyboard use (Esc closes). The character delete confirmation shows how many items and how much gold the bank holds. Works on a phone-sized screen. Swedish text for every new string. Browser test as `tests/mount-ui.cjs` does: open, deposit, withdraw, a refused deposit, close, reload and see the same bank.
- [ ] `BANK-ART` — Through PixelFlow: a banker sprite (idle, and talking if the NPC set has it) that reads at game scale on every city's ground, with a palette variation per city so the five bankers do not look identical, and a bank counter or strongbox prop beside each one. The bank window gets an icon. Check by looking in a real browser.
- [ ] `BANK-CHECK` — Verify in a private world: a banker stands in each of the five big cities and nowhere else, an item and gold deposited in one city can be withdrawn in another, the bank survives logout, a server restart and a rebirth, a worn piece, a refined or purple copy and a bag keep their data through a deposit and withdrawal, a full bank or bag refuses cleanly, two browsers cannot both withdraw the same item, nothing is lost or copied in a long random sequence, and the Swedish text exists for every new string.

## Consumable balance

There are three families, generated by `scripts/consumable_tiers.py`: Traveler's Stew (health and resource over 8 seconds), Health Potions (health with a 60-second shared potion cooldown) and Mana Potions. Tiers run from level 1 through 99, with final steps at 95 and 99. Health restoration is the greater of the item's flat floor and 40% of the character's maximum HP. The curve, prices and PvP rule are in [docs/consumables.md](docs/consumables.md).

- [x] `CONS-AUDIT` — Measure how the potions and food compare with real characters at levels 1, 10, 20 ... 99 for every class, with and without heavy stamina or intellect: potion heal as a percentage of max HP, mana restored as a percentage of max mana (mages and priests use mana, warriors use rage, so check what mana does for each class), healing per second against the damage of that level's monsters, elites and bosses, and the cost in gold of keeping a character stocked per hour. Report the table in `docs/` and name the levels where a potion is useless or too strong. Reported in [docs/consumable-audit.md](docs/consumable-audit.md).
- [x] `CONS-RULES` — The complete level-1–99 curve and stacking, cooldown, price and PvP rules are recorded in [docs/consumables.md](docs/consumables.md). Health uses the larger of the flat floor and 40% of maximum HP; food takes eight seconds, and potions keep their persistent shared 60-second cooldown. No intermediate health tiers are needed because the percentage floor prevents a decade gap.
- [x] `CONS-DATA` — `scripts/consumable_tiers.py` now makes named level-95 and level-99 tiers with prices, rarity colours and marked family icons. Existing `tiered` NPC offers in each zone select the best allowed family tier, so the new items appear at the same traders. Existing IDs and stacks remain valid; the generator is byte-idempotent.
- [x] `CONS-SERVER` — Food and health potions use the authoritative 40% maximum-HP floor, including old stacks after leveling. Fullness, level, ownership and the saved 60-second shared cooldown continue to reject invalid uses in every mode, including PvP, duels and arenas. Focused Rust tests cover healing, stack preservation, tier gates and cooldown persistence.
- [x] `CONS-UI` — Bags, tooltips, trader offers, quick-slot titles and the active meal chip show the actual health and resource amounts for the current character, the maximum-health percentage and the existing shared potion cooldown. Level-95 and level-99 family icons show their tier numbers and a rarity ring.
- [x] `CONS-CHECK` — Verify in a private world at several levels and classes that each tier heals and restores what its tooltip says, cooldown and food rules hold, prices and shop lists are right, old saves and quick slots still work, and that the balance table from the audit passes. Done 2026-10-16 with existing and new suites: the 12 `resource_tests` (every tier x class: price, healing, resource, food rules), the audit rows, the 160 `world::tests`, and `tests/consumables-ui.cjs` (49 checks: shops, tiers at level 20/95/99, quick slots, bags, the meal wait, refusals).
- [x] `CONS-SHARED-COOLDOWNS` — Meals must not stack, and every meal tier must share one server-owned cooldown so switching foods cannot start another meal early. Keep one shared potion cooldown across **all** potion tiers and both health and mana potions; switching family or tier must never bypass it. Decide the meal cooldown length, persist both timers across logout and restart, show their remaining time in bags and quick slots, refuse use without consuming the item, and verify the cross-tier and cross-family cases in a private world. Done 2026-10-16: every meal tier shares one 30-second server-owned cooldown (`cooldown` on each food in the catalog, counted from the start of the meal; `Character.meal_ready` saved as a wall-clock second, `mealCd` in the snapshot). A refused meal is not consumed; potions keep their own shared 60 s timer and a potion works during the meal wait. Bags show the seconds on the stack, the quick slot counts them down, tooltips name the shared wait. `reset_cooldowns` clears both timers. Rust `every_meal_tier_shares_one_cooldown...` plus 49 browser checks.

## Kill-time testing

Measure how long it takes to kill a monster of the character's own level, every 5 levels (5, 10, 15 ... 95, plus 99), for every class, wearing the **normal gear for that level** (the ordinary progression set for that level, not dungeon, orange or refined gear). This shows where fights are too fast or too slow and feeds `CONS-AUDIT`.

- [x] `TTK-RULES` — Define the test: what "normal gear" is at each level (the level's ordinary piece in every slot, base rarity, no refinement, no set bonuses), the skillbar and rank each class has at that level, the attribute allocation (an even default plus a stamina-heavy and a damage-heavy variant), the target (an ordinary monster of the same level, and also an elite if one exists at that level), whether potions and food are used, and what counts as a kill (first hit to death, with travel and cooldown waits included). Set target kill times per level band and say what is too fast or too slow. Settled in [docs/ttk-rules.md](docs/ttk-rules.md).
- [x] `TTK-HARNESS` — Build a repeatable private-world test that creates a character of each class at the given level with that gear, spawns the monster, plays a fixed skill rotation (and a basic-attack-only run), and records time to kill, damage taken, mana or rage used, potions used and whether the character died. Run several seeded repetitions per case and report the median and spread. It must never touch the live world or real saves. Built as `server/src/world/ttk.rs` (in-memory `World`, 9 seeded repetitions, median and spread); run it with `bash scripts/ttk.sh` (variables listed in the script), and its fast tests run with `cargo test ttk`.
- [x] `TTK-RUN` — Run it for all 20 levels and five classes (100 cases per variant) and write the results as a table in `docs/`: kill time by class and level, plus the same-level monster's own damage against the character so the other side of the fight is visible. Done 2026-10-15 with nine seeds per case (`TTK_RUNS=9 bash scripts/ttk-parallel.sh`, 41 minutes on four cores): [docs/ttk-report.md](docs/ttk-report.md), median seconds and the monster's damage per landed hit for all 100 cases. Result: 76 of 100 cases never kill within the cap and only 4 land inside the target band; levels 5 to 10 are under the band (5 to 15 s against 15 to 30 s), level 15 is the one level that fits for most classes, the warrior and assassin fail from level 20, everyone but the priest from level 30, and everyone from level 45. This is the input for `TTK-FIX-DAMAGE` and `TTK-TUNE`. **Baseline changed 2026-10-15: green gear, not gray** (the user's decision; `BASELINE_RARITY` in `server/src/world/ttk.rs`, `docs/ttk-rules.md`). The table was regenerated on the green baseline; the gray run differed by only a few percent.
- [x] `TTK-TUNE` — Tuned the class and level outliers with monster stats and item IDs unchanged. The full nine-seed grid now has 900 successful fights, every median in band, at most 1.291× class spread and at least 37% median HP left. Group-encounter effects are recorded in docs/ttk-plan.md.
- [x] `TTK-CHECK` — Target bands live in world/ttk-targets.txt; the Rust harness asserts kills, time bands, class spread and survival. A sampled check runs in the normal suite, with the full nine-seed grid as an explicit slow gate. scripts/check_ttk.py validates the saved nine-seed reports.

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

- [x] `TTK-FIX-CLASSES` — Authoritative class-and-level calibration of final player attack now keeps the measured class kill-time spread at or below 1.291×; item IDs and ownership stay intact. Monster stats are unchanged.
- [x] `TTK-FIX-DAMAGE` — Player max health now grows with level; saved absolute HP migrates once by percentage and defeated characters remain defeated. Every measured fight ends above 37% median HP. Elite hit survival and group encounters have private Rust checks.
- [x] `TTK-FIX-SPEED` — Authoritative player attack growth brings every same-level ordinary kill median inside world/ttk-targets.txt, with all monster stats unchanged. The level 5–10 target band reflects the owner's decision to keep monsters fixed; before and after measurements are in docs/ttk-plan.md and docs/ttk-report.md.
- [x] `TTK-FIX-RUN` — Run one private harness process per class in parallel with `bash scripts/ttk-parallel.sh`, preserving the early stop and writing separate JSON/log files under `test-results/`; `scripts/merge_ttk.py` combines them into `docs/ttk-report.md`. The current ordinary-fight report covers nine seeds for all 20 levels and five classes.
- [x] `CONS-FIX-SCALE` — Repeated the 180-row real-formula audit after the kill-time health change ([docs/consumable-audit.md](docs/consumable-audit.md)). Set health potions and meals to the larger of the tier's flat heal and 40% of maximum HP; level-one healing is 60. The audit's level-99 warrior now receives 44,813 HP rather than the old 1,330 flat HP. The 60-second cooldown and existing prices remain; the new 95/99 tiers extend the catalog without changing old IDs.
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

### Skill effect clarity

Each item below covers one active skill in `world/skills.txt`. Give it a recognizable cast, travel and impact where applicable; show its actual range, affected area and purpose; align its icon and description with the result. Check it at game scale in a crowded fight and at higher ranks without hiding combat targets. Keep these as separate checkboxes so a finished skill can be checked off on its own.

#### Warrior

- [x] `S-FX-CLEAVE` — Cleave: the real server cast now draws its full forward cone as a subdued ground sector with a layered gold-and-steel blade sweep and moving tip flare. Real-sprite private browser capture verified the catalog's 1.9-unit reach and 3.54-radian cone; `tests/cleave-visual-ui.cjs` saved the frame, which was uploaded to Sork FileDrop as `Valhalla_Skill_Cleave_New_Effect.png`.
- [x] `S-FX-BATTLECRY` — Battle Cry now sends layered gold roar waves outward and keeps a gold damage-buff marker at the warrior's feet.
- [x] `S-FX-SHIELDWALL` — Shield Wall now raises a blue outlined shield around the warrior and keeps small shield markers while active.
- [x] `S-FX-WHIRLWIND` — Whirlwind now spins three steel arcs around the full authoritative 2.4-unit hit radius.
- [x] `S-FX-CHARGE` — Charge now draws a directional arrow and a trail to the actor's observed position, so the marked path shortens if movement is blocked.
- [x] `S-FX-GROUNDSLAM` — Ground Slam now fractures the ground, lifts stone shards and sends a shock ring to its 3.4-unit radius.
- [x] `S-FX-SECONDWIND` — Second Wind now raises green restorative ribbons and a self-heal cross without suggesting an attack area.
- [x] `S-FX-BERSERK` — Berserk now ignites red speed flames at cast and keeps a spinning red haste marker while active.
- [x] `S-FX-EARTHSHATTER` — Earthshatter now drives a branching fissure along its 4.8-unit forward lane with a subdued sector showing the full hit cone.
- [x] `S-FX-TITANSWRATH` — Titan's Wrath now sends a six-unit rune-ring shockwave, golden fractures and a central pillar; a green return ring appears when actual damage heals the warrior. All ten warrior effects were captured from real level-99 server casts in `tests/warrior-skill-effects-ui.cjs` with real sprites and uploaded to Sork FileDrop as `Valhalla_Warrior_Skill_<id>.png` (ten SHA-256-verified PNGs).

#### Mage

- [x] `S-FX-TWINBOLT` — Twin Bolt now fires two separate violet arcane bolts with individual server-confirmed impact flashes.
- [x] `S-FX-ARCANEWARD` — Arcane Ward raises a faceted blue shell on cast and keeps a restrained shell around the mage while the shield buff lasts.
- [x] `S-FX-FIREBALL` — Fireball has a bright traveling body and a separate two-unit fiery blast drawn only at its actual bolt hit.
- [x] `S-FX-BARRAGE` — Arcane Barrage shows five cyan bolts in the catalog's firing fan, each with its own impact flash.
- [x] `S-FX-BLINK` — Blink marks its departure and observed arrival with a short violet trace, without a damage ring.
- [x] `S-FX-CHAINLIGHTNING` — Chain Lightning draws staggered, branching jumps along the server's actual target sequence.
- [x] `S-FX-METEOR` — Meteor marks the chosen 2.6-unit landing area before its falling body and impact ring; its ground effect stays behind actors.
- [x] `S-FX-LIFEDRAIN` — Life Drain streams rose-colored energy from the struck enemy back to the caster and shows the real healing return.
- [x] `S-FX-ARCANESTORM` — Arcane Storm fills its five-unit area with a distinct rotating violet tempest beneath combatants.
- [x] `S-FX-STARFALL` — Starfall marks its 6.5-unit distant field with constellations and falling stars; impacts stay beneath actors. All ten Mage effects were captured from real level-99 server casts in `tests/mage-skill-effects-ui.cjs` with real sprites. Twelve SHA-256-verified captures, including Fireball travel and Meteor warning frames, are in Sork FileDrop as `Valhalla_Mage_Skill_<id>.png`.

#### Assassin

- [x] `S-FX-THROWINGKNIVES` — Throwing Knives launches three visible knives along the server's actual forward fan, with sharp impact flashes.
- [x] `S-FX-EVASION` — Evasion has a nimble side-step cast cue and restrained dodge chevrons throughout the buff.
- [x] `S-FX-LUNGE` — Lunge traces observed movement on the floor and cuts at the actual arrival point.
- [x] `S-FX-FLURRY` — Flurry paints each real target hit as a numbered, staggered cut; all four are visible when the target survives.
- [x] `S-FX-SHADOWVEIL` — Shadow Veil surges upward at cast and leaves a distinct trailing haste marker throughout the buff.
- [x] `S-FX-CYCLONEBLADES` — Cyclone Blades spins six steel daggers at its actual 2.6-unit hit radius beneath actors.
- [x] `S-FX-ASSASSINATE` — Assassinate focuses a reticle on the struck target before a decisive heavy cut.
- [x] `S-FX-DEADLYFOCUS` — Deadly Focus narrows a critical reticle at cast and keeps a small target mark while active.
- [x] `S-FX-KNIFERING` — Knife Ring sends twelve visible knives outward along twelve distinct server projectile paths.
- [x] `S-FX-THOUSANDCUTS` — Thousand Cuts fills its actual 3.7-unit forward cone with staggered shadow blades and a grounded sector. All ten Assassin effects were captured from real level-99 server casts in `tests/assassin-skill-effects-ui.cjs` with real sprites. Ten SHA-256-verified captures are in Sork FileDrop as `Valhalla_Assassin_Skill_<id>.png`.

#### Priest

- [x] `S-FX-MEND` — Mend connects the caster to its one actually wounded recipient with a distinct healing arc.
- [x] `S-FX-SMITE` — Smite drops a focused holy bolt onto the enemy actually struck.
- [x] `S-FX-WARDOFLIGHT` — Ward of Light shows its 8-unit protection circle and a persistent shield shell on the caster and recipients.
- [x] `S-FX-PRAYER` — Prayer of Healing sends separate links and light markers to each actually healed party member.
- [x] `S-FX-HOLYNOVA` — Holy Nova has separate gold damage and green healing waves at its real 3.4- and 6-unit radii.
- [x] `S-FX-BLESSING` — Blessing of Might spreads through its 9-unit circle and leaves a persistent gold damage-buff mark on recipients.
- [x] `S-FX-GUARDIANLIGHT` — Guardian Light centers a sanctuary beam and small floor seal on the caster's self-heal only.
- [x] `S-FX-SEARINGLIGHT` — Searing Light strikes the real enemy with hot light and returns healing energy to the caster when it heals.
- [x] `S-FX-DIVINEHYMN` — Divine Hymn sustains a 12-unit chorus ring and connects to each actually healed party member.
- [x] `S-FX-HEAVENSWRATH` — Heaven's Wrath adds a radiant crown to distinct 5-unit enemy damage and 8-unit party healing waves. All ten Priest effects were captured from real level-99 casts in a three-player private party with real sprites by `tests/priest-skill-effects-ui.cjs`. Ten SHA-256-verified captures are in Sork FileDrop as `Valhalla_Priest_Skill_<id>.png`.

#### Hunter

- [x] `S-FX-POWERSHOT` — Power Shot: forceful draw, single live arrow and confirmed first-target impact.
- [x] `S-FX-MULTISHOT` — Multi-Shot: three distinct server arrows spread through the actual fan.
- [x] `S-FX-ROLLAWAY` — Roll Away: ground trail tracks the real roll, with an airborne landing cue and no attack slash.
- [x] `S-FX-PIERCINGARROW` — Piercing Arrow: one live arrow continues through successive targets; two impacts from one bolt verified.
- [x] `S-FX-HUNTERSMARK` — Hunter's Mark: focused reticle cast and persistent damage-buff reticle on the hunter.
- [x] `S-FX-EXPLOSIVEARROW` — Explosive Arrow: live arrow flight, confirmed impact burst and true 2.2-unit floor radius.
- [x] `S-FX-RAPIDFIRE` — Rapid Fire: speed lines and persistent haste chevrons distinct from Mark.
- [x] `S-FX-RAINOFARROWS` — Rain of Arrows: actual target circle and staggered falling arrows across its 2.8-unit radius.
- [x] `S-FX-EAGLESIGHT` — Eagle Sight: eye-shaped cast and persistent sight cue on the hunter.
- [x] `S-FX-ARROWSTORM` — Arrow Storm: dense outward arrows across the true 4.2-unit hit area, including the capstone.

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
- [x] `GM-GEAR-DATA` — Raise the GM pieces to match the rules, with armor and headgear in the same league as the weapon today (the armor's 12 defense is tiny next to the sword's 10,004) and attribute bonuses if the stat formulas need them. Complete the set to every slot (shoulders, gloves, pants, necklace, accessories) if that is needed to reach the target, with golden art and icons made through PixelFlow. Keep the `gm` rarity (never rolled, never sold or dropped) and keep the item IDs and saves. Done 2026-10-17: the Golden Robe is 40,000 defense and the Top Hat 25,000; new `warrior_shoulders_gm` (15,000), `warrior_gloves_gm` (15,000), `gm_pants` (25,000), `gm_necklace` (10,000) and `gm_accessory` (10,000), all `gm` rarity, sell 0, level 1; total 150,004 with the sword. `GM_GEAR` lists all eight; `become_gm` wears them and `grant_missing_gm_gear` (called from `decode`) gives an older GM save the new pieces once and wears them in empty slots. Worn art is five new `*_gm` layers in the Warrior atlas only (PixelFlow groups `gm` and `gm2`, lazy-loaded; the pants sit under the robe's skirt), icons in `scripts/make_item_sprites.py`. Rust: `game_master_set_fills_every_slot_and_meets_the_defense_target`, `an_older_game_master_save_receives_the_new_golden_pieces_once`; browser: `tests/sprites-real.cjs warrior`, `tests/gm-ui.cjs`. Not deployed yet.
- [x] `GM-GEAR-SERVER` — Apply any special rule from `GM-GEAR-RULES` authoritatively in combat, only when the wearer is the GM character; a client or another player can never obtain it. Make sure it does not break the damage code for ordinary players (no overflow when a huge attack value multiplies against stats, no integer wrap and no NaN) and that kills still give normal credit, loot and quest progress.
- [x] `GM-GEAR-CHECK` — Verify in a private world that the GM kills the strongest monster of every zone and dungeon in one hit, that ordinary players and mobs behave exactly as before, that other players cannot equip or receive the GM pieces, that PvP follows the rules, and that large values do not overflow. Done 2026-10-17: the check found that 150,004 defense was too little (144 spawned enemies hit harder, up to 391,200), so the golden pieces now total 570,004 (see [docs/gm-gear.md](docs/gm-gear.md), "As checked"). Rust: `the_game_master_takes_one_damage_from_the_hardest_hit_in_the_data`, `the_game_master_gets_normal_damage_against_players_in_duels_and_world_pvp`, `only_the_game_masters_own_golden_weapon_strikes_so_mercenaries_and_players_hit_normally`, `no_ordinary_character_can_equip_any_golden_piece`, `no_golden_piece_can_be_offered_in_a_trade`, mutation-checked. Not deployed yet (rebuild, restart and client files together).

## Day and night

Add a day and night cycle to the world. **24 game hours pass in 20 real minutes**, so one game hour is 50 real seconds, noon comes every 20 minutes and the shortest night is only a few minutes long. Outdoor zones follow it; enclosed places (private dungeons, building interiors, caves) do not. `WEATHER-RULES` asks whether weather follows a world clock, so decide the clock here first.

- [x] `TIME-RULES` — Define the world clock: 1,200 real seconds per 24 game hours, the game time at server start (continuous across restarts from a stored epoch, never reset to dawn), the hour boundaries for dawn, day, dusk and night, and whether every zone shares one clock or some zones have a fixed time (an eternal dusk, a permanent aurora night in Frostwake, caves and dungeons with no cycle). Decide whether the time is shown to the player (a clock or sun/moon icon), whether any systems depend on it (monster spawns or stats, shop hours, quests, loot, regeneration, rest or the inn) and keep the first version cosmetic by default so combat and tests are unaffected. Derive which zones are indoors from the data.
- [x] `TIME-SERVER` — Make the server the one source of time: compute the game time from a stored epoch and the real clock, send the current time and its speed to each client on join and re-sync periodically so clients do not drift, and allow a private test world to set or freeze the time. The time never rolls back or restarts at a server restart.
- [x] `TIME-RENDER` — Tint the outdoor scene through the day: warm sunrise, bright noon, orange sunset, a blue-dark night with a gentle floor so the screen stays readable, smooth blending between phases, lit windows, lamps and campfires turning on at dusk, moon and stars at night, and a sun or moon position that fits the hour. It must never hide monsters, loot, players, skill telegraphs or text, and shadows should follow the sun if the art uses them. Keep the cost low: tint with one overlay or cached gradient rather than repainting layers, and respect reduced-motion.
- [x] `TIME-ZONES` — Give each zone's theme its own take on the cycle (the frost aurora at night, ember glow in the Crags, glowing flora in the fen and Veyrroot, a starry desert), while keeping the same readability floor, and make indoor zones and dungeons ignore the cycle. Make the transition when walking through a door smooth.
- [x] `TIME-UI` — Show the time of day in the HUD (a small sun/moon icon with the game hour, plus a tooltip), and add a setting to reduce or turn off the night darkening for players who find it hard to see. Add a debug command for the GM to set the time (see the game master tasks).
- [x] `TIME-MUSIC` — Add a night variation of the zone music (calmer or slower), made through the dybase2 tools, that fades in at dusk and back at dawn, if `TIME-RULES` wants it. **Done:** dybase2's 72 BPM *Lanterns After Sundown* is the shared outdoor nocturne; it crossfades with each zone score through dusk and dawn, while enclosed zones keep their own music. Private browser checks cover the clock phases, outdoor travel, enclosure, decoding and score volume.
- [x] `TIME-WEATHER` — Connect the cycle to weather: weather rules may depend on the hour (morning fog, evening storms), a rainy sky tints the day colour darker, and night rain/snow stays visible against the dark tint. Hour weights are checked in Rust; `client/weather.js` paints after the day/night tint, and the private browser test compares rain and snow against clear at midnight.
- [x] `TIME-CHECK` — Verify in a private world with the time forced: 24 game hours equal 20 real minutes within a small tolerance, every client shows the same hour, the time is continuous across a restart, outdoor zones follow the cycle and dungeons and interiors do not, nothing becomes unreadable at midnight in any zone (compare screenshots at several hours), and CPU with the cycle on and off stays within the render budget. Done 2026-10-16: `tests/daynight-check.cjs` (67 checks): two clients agree on the hour, the clock runs 0.02 game hours per real second (24 h = 1,200 s), every outdoor zone keeps a readable midnight (brightness 61-147 against 72-190 at noon) and every enclosed zone is unchanged, the tint costs no more than 1.35x the untinted main-thread time. The restart continuity half is the Rust test in `world/daynight.rs` (stored epoch survives a reopen).

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

- [ ] `W-WORLD-SHAPE` — Make the world map look like a believable world, not 50 intertwined worms. Redesign the overall geography into readable regions with convincing landforms, coastlines and terrain transitions; arrange zones and route lines so their relationships are clear at a glance. Preserve the authoritative portal graph, current-location marker, reachable routes and sealed entrances, then check the full map at game scale in a private browser.
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
- [x] `MOUNT-SERVER` — Replace the single owned-horse flag with a set of owned mounts plus a selected one, migrating existing saves so every horse owner keeps their horse. Keep travel speed, dismount rules and persistence authoritative, and send the selected mount in the player snapshot. Done 2026-10-17: `Character.mounts` (ordered set) and `mount` (selected) replace the flag as the truth; `mount_owned` stays as a derived "owns one" flag, and `normalize_mounts` migrates old saves on load and join (a horse owner gets `mounts=[horse]`, `mount=horse`; unknown or repeated IDs are dropped). `MOUNTS` in `model.rs` holds the five IDs with one speed each (2.0). New `select_mount` client message (refused with no change for an unowned mount, swaps at once while mounted); the snapshot carries `mounts` and `mount`; H summons the selected mount; Greta's sale goes through `grant_mount`. `mount_licence` items (`mount` field on the item) are consumed by `use_item` once the character does not own that mount, refused below the item's level and kept if already owned, and `trade.rs` refuses them. Tests: `cargo test riding_horse several_mounts a_legacy_horse` (the licence use path has no catalog item yet, so `MOUNT-SOURCES` must test it). Compiled in, not deployed; the client is unchanged until `MOUNT-UI`.
- [ ] `MOUNT-GRYPHON` — Create the gryphon mount sprites in every direction and gait for both bodies and all classes, with rider placement, through PixelFlow.
- [ ] `MOUNT-LIZARD` — Create the lizard mount sprites in every direction and gait for both bodies and all classes, with rider placement, through PixelFlow.
- [ ] `MOUNT-RAPTOR` — Create the raptor mount sprites in every direction and gait for both bodies and all classes, with rider placement, through PixelFlow.
- [ ] `MOUNT-SABERTOOTH` — Create the sabertooth mount sprites in every direction and gait for both bodies and all classes, with rider placement, through PixelFlow.
- [x] `MOUNT-SOURCES` — Add the acquisition for each new mount from `MOUNT-RULES`: stable or vendor NPCs with dialogue, quests, and drop sources with their rates. Done 2026-10-17, data in `scripts/mount_sources.py` (idempotent patcher; `progression_quests.keep_released_rewards_and_route_quest` calls it, so regenerated zones keep it; run `python3 scripts/mount_sources.py && node scripts/sync-world.cjs`, rebuild Rust). **Raptor:** four quests from Mara Vines, `tangle_banyan_1`..`4` (kill 25 canopy monsters; bring 10 materials; the group elite Jade Anaconda for 3 players; escort Tamsin Reedfoot, the hatchling's bearer, from (75, 68) down the canopy road to Mara), the last with `rewardMount: raptor`. **Lizard:** Zahir Dunereins, Dune-wrangler in the Lapis Erg hub (`buy_lizard`, level 80, 160,000 gold). **Gryphon:** Oren Highwind's `hatch_gryphon` offer (level 95, 250,000 gold, uses up the Gryphon Egg). **Sabertooth/Gryphon licences:** bound `mount_licence` items (`sabertooth_whistle` 4% from the Rimesaber, `gryphon_egg` 3% from the Thunderheart Gate's final boss, `mount_licence_drop` in `items.rs`, a roll of their own), never sold or traded, rolled for in a party with Need only for characters without the mount (hired fighters pass), used by double-click in the bags. Offers now carry `mount` (an id) and `needs`; Greta's offer is `mount: horse`. Tests: `cargo test mount_sources` (11) and `node tests/mount-ui.cjs` (adds the whistle). Open: the escorted NPC is a person (no hatchling art; `MOUNT-RAPTOR` can add it), licence icons are the generic glyph, no Swedish text yet (`build_swedish.py` needs the network), the Egg's drop has only a table test (a final-boss kill is not simulated), and the Thunderheart drop is compiled in, not deployed.
- [x] `MOUNT-UI` — Let the player see their owned mounts and choose which one the mount key and HUD button summon, with ownership, price and unlock hints for the ones not owned yet, and other players seeing the selected mount. Done 2026-10-17: `client/mounts.js` renders a Mounts list in the Character window (all five mounts: owned and selected state, a Select button on owned ones, greyed rows with level, route and price or drop rate for the rest) and sends `select_mount`; the HUD button names the selected mount; the snapshot's `mount` reaches other players, whose rider is drawn in the selected mount's coat colour (a placeholder on the horse body until the per-mount sprites exist). Also fixed a layout bug found on the way: the Character button covered the Mount button at every size (the weather line pushed the HUD down), so `tests/mount-ui.cjs` could not click it; the button now sits at 21cqw and the quest tracker at 24.4cqw. New debug op `give_mount` for private worlds. `node tests/mount-ui.cjs` passes (list, hints, selection, refusal, a second browser seeing the raptor, reload). Compiled and saved, not deployed.
- [ ] `MOUNT-CHECK` — Verify purchase gates, ownership and the selected mount across save/reload, that a horse owner keeps the horse, speed and dismount rules per mount, and the sprites at game scale in a real client in a private world.

## Rebirth

Owner's idea (2026-10-17): at level 50 a character may **rebirth**: start again from level 1 and keep extra perks. Every ten levels past 50 adds more perks, so you may rebirth at 50, 60, 70, 80 or 90 (the level cap is 99) and the later you go, the better the reward. Rebirth at 90 includes **double drop rate**, on everything. Working reading, to confirm in `REBIRTH-RULES`: a rebirth at level L has **tier (L - 40) / 10** (50 is tier 1, 90 is tier 5), and a tier's perks include every lower tier's. Confirmed in `REBIRTH-RULES`.

Owner's decisions (2026-10-17): **perks stack** across rebirths; **the drop rate boost covers everything** (every drop and roll, the purple chances, the mount licences and chests included; changed the same day from a one-off double to a stacking ×2 up to ×5); **quest rewards can be earned again** after the quest reset. Starting defaults for the rest (change them in `REBIRTH-RULES` if play says otherwise):

- **Later pays more, and it stacks:** the tier is set by the level you rebirth at, and each rebirth adds that tier's perks to what you already have. Because perks accumulate, rebirthing again and again at 50 would be the quickest way to stack, so every stacking perk needs a cap (and the drop perk a fixed rule: ×2 at the first tier-5 rebirth, +1 for each further one, capped at ×5).
- **Reset:** level, XP, trained stat points (and the stat-reset price), quest progress and the fog of war. **Kept:** the account, friends, mounts, bags and fitted bag expansions, gear and the inventory (level requirements already gate it), cosmetics, game master status and every perk.
- **Convenience over power:** perks speed up levelling and playing; none changes combat numbers (attack, defense, health, damage taken), because the elite, dungeon and kill-time tuning (`world/elite-power.txt`, `world/enrage.txt`, `docs/ttk-rules.md`) assumes level-appropriate stats and the rule that a lone player cannot beat group content.
- **Perks** (final table in [docs/rebirth.md](docs/rebirth.md), data in `world/rebirth.txt`): an XP bonus, a gold bonus, extra bag cells, cheaper Spark Travel, a cheaper stat reset, a "Reborn" title, name colour and aura that other players see, mount coat tints, and at tier 5 double drop rate. Extra stat points, skill-rank cap and skillbar slots were dropped: they change combat power.

- [x] `REBIRTH-RULES` — Settled 2026-10-17 in [docs/rebirth.md](docs/rebirth.md). Tier = (level - 40) / 10 (50 to 90 give 1 to 5; 91 to 99 add nothing over 90); a rebirth grants every perk unlocked at its tier or lower, once each. Perks (step, cap): XP +10% (+50%) from tier 1, gold +10% (+50%) from tier 2, bag cells +2 (+10) from tier 3, Spark fares −10% (−50%) and stat-reset price −10% (−50%) from tier 4, the drop rate multiplier from tier 5 (×2 after the first tier-5 rebirth, +1 per further one, cap ×5: a 2% roll becomes 10%). **Dropped from the candidates because they are combat power or useless:** extra stat points, a higher skill-rank cap, an extra skillbar slot. State is only `rebirth_tiers: [u32; 5]` and every perk is derived from it. The multiplier scales the expected number of drops **and the purple chances** (`scaled(p, m)`: same draw against m×p when that is at most 1, m copies of a guaranteed drop, no extra draw for an unreborn character; the 5% purple copy chance becomes 25% and the chest ladder's purple 0.5% becomes 2.5% at the cap; licences 20% and 15% at the cap; gold and materials are one pile or stack worth m times). Reset and keep lists, refusals, the preview nonce and the quest reset are in the doc.
- [x] `REBIRTH-SERVER` — Done 2026-10-17. `Character.rebirth_tiers: [u32; 5]` (`#[serde(default)]`; every perk will be derived from the counts, so a legacy save is never reborn), the ladder and the atomic reset in `server/src/rebirth.rs` (`rebirth_tier`, `Character::rebirth`), the world side in `server/src/world/rebirth.rs`. Protocol: `{"type":"rebirth_preview"}` answers `rebirthPreview` (`ok`, `reason`, `level`, `tier`, `count`, `tiers`, `gearOff`, `cellsNeeded`, `nonce`, `lifetime` 60 s); `{"type":"rebirth","nonce":...}` needs the live nonce of the last preview, tied to the level and rebirth count it was issued for and spent by any try. Refusals: level under 50, defeated, in combat, mounted, escorting, in a dungeon copy, arena, duel or trade, Spark Travel, and bags too full to take the high-level gear that comes off (the reason names the cells to free). Snapshot: `reborn {count, tier}` (highest tier) and `rebirthTiers`; one `rebirth` event (value = tier) at the start city plus a notice. Perks, the drop multiplier and `world/rebirth.txt` are `REBIRTH-PERKS`; the UI strings and Swedish text are `REBIRTH-UI`. Tests: `cargo test rebirth` (10: ladder 49/50 to 90/99, reset and keep lists, gear off and a full bag, every refusal, forged, replayed, expired and moved nonces, a second rebirth, a legacy save and a save round trip); clippy clean. Not tested: the duel and escort refusals directly (they use `pvp_busy` and `escort_of`).
- [ ] `REBIRTH-PERKS` — Implement each perk in the table as a small server hook (XP gain in `grant_xp`, bag capacity, gold drops, quest gold and sales, Spark Travel fares, the stat-reset price) and the tier 5 drop-rate multiplier in the kill-reward code beside `roll_bag`, `loot_drop`, `mount_licence_drop`, the orange and set-piece rolls and the chest rewards, so that one `scaled(p, multiplier)` helper reaches every roll (and nothing is doubled twice), plus an audit test that fails when a drop site skips it, plus the quest reset that lets every quest and its rewards be earned again. Each perk gets a unit test that measures the effect against an unreborn control at the same seed (for the drop perk at ×2 and ×5 over several hundred kills, as the Rimesaber test does, covering gold, materials, bags, gear, the purple copy chance, chests and both mount licences), and a test that **no perk changes attack, defense, health or damage taken**, so `scripts/elite-solo-parallel.sh` and `scripts/dungeon-solo-parallel.sh` need no re-calibration; re-run one elite and one dungeon check to prove it.
- [ ] `REBIRTH-UI` — A Rebirth panel in the Character window: the current tier, the perks owned, a preview of the tier you would get at your level and what it adds, the next ten-level step and its extra perks, and a **Rebirth** button that is disabled with the reason when refused. A confirmation dialog lists what resets and what stays and needs a typed or held confirmation. Show a Reborn title, name colour or aura on other players, the nameplate and the party frame, and a short celebration on rebirth. A hint on the level-50 level-up banner that rebirth is now possible. Browser test with a debug level-up: panel, preview, refusal in combat, the confirmation, the reset state in the snapshot and the visible title on a second browser, as `tests/mount-ui.cjs` does for mounts.
- [ ] `REBIRTH-ART` — The cosmetic side, through PixelFlow and the effects canvas: the Reborn aura or mark per tier (five looks, readable at game scale, cheap enough for the render-cost rules), the title text colours, and any mount coat colours the table grants. Check by looking in a real browser, not by file checks.
- [ ] `REBIRTH-CHECK` — Verify the whole loop in a private world: a level-50 character rebirths, replays the early zones with the perks, and rebirths again at 70 for tier 3; mounts, friends, party and gear survive; quests can be taken again; after the first level-90 rebirth drops are about twice as frequent over a large sample, the mount licences included (8% and 6%), and after four tier-5 rebirths about five times (20% and 15%, the purple copy chance 25%), and a repeated quest pays its rewards again; the combat harness results are unchanged; old saves load; and the Swedish text exists for every new string.

## Enemy sprites and animation, zones 10–39

Owner's verdict (2026-10-16): zones 1–8 have good monster sprites and animation; from zone 9 on the enemies are not up to par and need to be **redone**. Zone 9 (Nacrehold) is a city with no enemies, so the work starts at zone 10. One task per zone with enemies, covering every monster kind listed there, bosses included. Use the `makesprites` skill and PixelFlow for all art; the quality bar is zones 1–8 (read wiki `30_resources:valhallasc_rime_monster_sprite_lessons` and `30_resources:pixelflow_agent_sprite_cap` first). Redo the full set for each monster (idle, walk, attack, hurt, die) with a distinct silhouette and palette per kind, readable at game scale, and keep sizes, hitboxes and kind IDs unchanged. Check each result in a real browser by looking at it, not just by file checks.

- [ ] `ES-Z10` — Redo the monster sprites and animation for zone 10, Drowned Cathedral, Flooded Cloister: bellkeeper, choirmother, mournsister, rootabbot, tidecantor, tideleech, tidetemplar. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z11` — Redo the monster sprites and animation for zone 11, Drowned Cathedral, Coral Reliquary: coralregent, glasscantor, pearlwidow, reliccrab, relicwarden, tidecantor, tidetemplar. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z12` — Redo the monster sprites and animation for zone 12, Drowned Cathedral, Grand Nave: abysszealot, chainmarshal, hierophant, starseraph, tidecantor, tidejudicator, tidetemplar. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z13` — Redo the monster sprites and animation for zone 13, Astralhollow: crystalwyrm, eclipsedryad, meteorgolem, orbitbeetle, voidmoth. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z14` — Redo the monster sprites and animation for zone 14, The Prismwaste: glassharrier, miragejackal, mirrorqueen, prismsentinel, shardscarab, sunshard. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z15` — Redo the monster sprites and animation for zone 15, The Obsidian Orrery: bronzemantis, chronoguard, epochengine, gearling, orbitseer, pendulummatron. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z16` — Redo the monster sprites and animation for zone 16, The Moonspore Canopy: glowcapgrazer, lanternwraith, mireheart, nightbloom, rootlurker, silkwing, silverwidow. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z18` — Redo the monster sprites and animation for zone 18, The Moonwell: dew_moth, hourpetal_stag, lumen_eel, moonskein_weaver, moonwell_echo, rootbell, tideglass_heron. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z19` — Redo the monster sprites and animation for zone 19, The Stormglass Shore: breakersentinel, glassray, maelstromheart, saltclaw, stormgull. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z20` — Redo the monster sprites and animation for zone 20, Sunward Vale: brushfox, honeyjaw, meadowhare, spadebadger, sunbacksnail, wickerwarden. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z21` — Redo the monster sprites and animation for zone 21, The Ribbonwild: balloonbeetle, jesterling, maskcolossus, paintedmacaw, paradegryphon, ribbongecko. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z22` — Redo the monster sprites and animation for zone 22, The Tanglecrown: canopyglider, crownjaguar, drumgorilla, jadeanaconda, orchidmantis, poolcaiman. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z25` — Redo the monster sprites and animation for zone 25, The Lapis Erg: dunecolossus, dunefennec, glassscorpion, mirageroc, sandhopper, sunvulture. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z26` — Redo the monster sprites and animation for zone 26, Frostwake Shelf: auroramanta, bellmammoth, crevasseleviathan, frostheron, glaciercrab, iceotter, snowhare. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z27` — Redo the monster sprites and animation for zone 27, The Cairnspine: cairnbehemoth, ridgeadder, screeferret, slateraven, stoneibex, stormcondor, whitebarktitan. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z28` — Redo the monster sprites and animation for zone 28, The Yearwheel: acornmimic, ambermantis, bloomtortoise, brooknewt, firephoenix, glasslion, harvestreaper, lanternowl, longnightwyrm, petalchimera, rainseraph, rimesaber, snowgiant, snowstoat, sundarter, sunwheel. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z29` — Redo the monster sprites and animation for zone 29, The Eye Below: eye_adept, eye_drifter, eye_lenswarden, eye_lurker, eye_unblinking, eye_undertide. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z30` — Redo the monster sprites and animation for zone 30, The Elder Hollow: elder_barkguard, elder_gatekeeper, elder_heart, elder_matron, elder_moth, elder_thornling. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z31` — Redo the monster sprites and animation for zone 31, The Thousandfold Pavilion: pavilion_foldling, pavilion_inkmoth, pavilion_mirror, pavilion_silkguard, pavilion_sovereign, pavilion_weaver. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z32` — Redo the monster sprites and animation for zone 32, Temple of the Rain Crown: rain_crown_droplet, rain_crown_gatekeeper, rain_crown_guard, rain_crown_oracle, rain_crown_sibyl, rain_crown_sovereign. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z33` — Redo the monster sprites and animation for zone 33, The Seed Vault: seed_amberwing, seed_germinator, seed_mote, seed_rootguard, seed_warden, seed_worldseed. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z34` — Redo the monster sprites and animation for zone 34, The Sunken Astrolabe: astro_axis, astro_gearling, astro_navigator, astro_sentinel, astro_starling, astro_warden. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z35` — Redo the monster sprites and animation for zone 35, The Thunderheart Gate: thunder_bastion, thunder_conductor, thunder_guard, thunder_heart, thunder_ray, thunder_spark. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z36` — Redo the monster sprites and animation for zone 36, The Blooming Labyrinth: bloom_guard, bloom_heart, bloom_mirror, bloom_moth, bloom_spore, bloom_thornkeeper. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z37` — Redo the monster sprites and animation for zone 37, The Solar Crucible: solar_ashwarden, solar_crucible_guard, solar_emberling, solar_heart, solar_heliomancer, solar_sunmoth. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z38` — Redo the monster sprites and animation for zone 38, The Amber Archive: amber_chronicle, amber_curator, amber_memory, amber_moth, amber_page, amber_sentinel. Bring each up to the zone 1–8 standard (see the section intro).
- [ ] `ES-Z39` — Redo the monster sprites and animation for zone 39, The Silent Solstice: solstice_flurry, solstice_guard, solstice_harbinger, solstice_heart, solstice_owl, solstice_watcher. Bring each up to the zone 1–8 standard (see the section intro).

## Sound

- [x] `SFX-LEVELUP` — Add a proper level-up sound. Today `SFX.levelup` in `client/game.js` only plays a synthesized whoosh and chord on the `levelup` event (owner asked for a level-up sound on 2026-10-16, so judge whether it is missing in play or just too weak). Make it clearly audible and recognizable, short enough not to cover combat sounds, and obey the music/effects volume settings. Fire it once per level gained (a multi-level jump plays it once), including the grand level-up. Check in a real browser that it plays on the event and not on login or zone change. Done 2026-10-16: the synthesized fanfare already existed; it is now about 1.5x louder, ducks every running field score for 3.2 s, and `tests/levelup-sound.cjs` (9 checks, analyser on the speaker bus) proves one fanfare for your own level-up (31 voices, peak 0.24, no clipping), none for another player's, once for a multi-level jump, and silence afterwards. Not judged by ear: listen and say if it needs more.
- [x] `SFX-SWING` — Add swing sounds for every attack the player makes. Today `SFX.swing` in `client/game.js` is one short noise burst for everything, so give each weapon family its own swing (sword, mace, dagger, staff, bow draw and release, spell cast) that plays when the swing starts, not when it lands, with a miss sounding different from a hit. Only your own swings play at full volume; other players' swings are quieter and fade with distance. Obey the effects volume setting, and keep rapid attacks from stacking into a buzz. Done 2026-10-16: authoritative swing/cast events trigger distinct sword, mace, dagger, staff and bow sounds; the bow draws then releases and spell skills have their own cast. Misses differ from hits, remote players fade with distance, and rapid voices are capped.
- [x] `SFX-ENEMY-ATTACK` — Add attack sounds for enemies: a wind-up or strike sound for each monster kind's attack, so the player can hear a hit coming. Group by body type or family (beast, insect, undead, construct, plant, water, ranged, boss) rather than one sound per kind, give elites and bosses a heavier version, make the sound fade with distance, and make sure a crowd of monsters attacking at once does not stack into noise. Done 2026-10-16: a first windup snapshot triggers one family voice for a nearby enemy, with heavier elite/boss gain and a four-voice crowd cap.
- [x] `SFX-ENEMY-DEATH` — Add enemy dying sounds. Today `SFX.slimeDie` is the only death sound and plays for every kind, so give each family its own death (beast, insect, undead, construct, plant, water, boss), a longer and louder one for elites and bosses, and a distinct lower one for the final boss of a dungeon. Play it when the death animation starts, fade it with distance, and cap how many can sound at once. Done 2026-10-16: the first dead snapshot triggers the family death voice; elites/bosses last longer, final dungeon bosses have a lower, longer voice, and distance and the crowd cap apply.
- [x] `SFX-CHECK` — Verify the swing, enemy attack, enemy death and level-up sounds in a real browser. Count the voices and measure the peak with an analyser, as `tests/levelup-sound.cjs` does. Check that each family plays its own sound, that nothing clips, that distance and the effects volume setting apply, that many simultaneous sounds stay capped, and that no sound plays for events the player cannot see. Done 2026-10-16: `tests/levelup-sound.cjs` passed 9 browser checks and `tests/combat-sound.cjs` passed 25, measuring the effects bus, distinct family pitches, event path, distance, effects volume, peak and simultaneous voices. Run both with `npm run test:sound`.

## Group elites

Quests in `world/map.txt` carry `recommendedPlayers` (2 to 5) and `group: true` for the elites and bosses meant for a party: Cinderlord (2), then the three-, four- and five-player elites and dungeon bosses of every zone from Gloamfen on (69 such quests on 2026-10-16). Nothing enforces the number today; it is only a recommendation, so the fights must be hard enough by their stats alone.

- [x] `ELITE-SOLO-TEST` — Built and run on 2026-10-16 (report: [docs/elite-solo-report.md](docs/elite-solo-report.md)). `server/src/world/solo_elite_tests.rs` derives the 113 group elites and bosses from the quests (count floor 40), fights each with a lone character of every class, 2 seeds, with every potion and meal, in green and in purple gear, and runs a party of the recommended size as the control (purple gear). **The pass condition fails today: a lone player can kill 19 of 113 in green gear (for example Cinderlord, the Eye Below, Elder Moth, Astro Gearling, Bloom Spore, Amber Page) and 91 of 113 in purple gear; 22 are safe even in purple.** The party control kills 112 of 113 (only Hollowking, level 20, 5 players, fails; check for a scripted phase). Run with `bash scripts/elite-solo-parallel.sh` (about 25 minutes on 4 cores) and `bash scripts/elite-party-parallel.sh` (about 4 minutes); the lone-player and party tests are `#[ignore]`d in the normal suite because they are slow. Not covered: orange, refined and set-bonus gear, and the mercenary, kiting, gate and reconnect loopholes (a lone player with mercenaries is not simulated).
- [ ] `ELITE-SOLO-SPEED` — Partly done 2026-10-16: the harness cleared every monster in the world, and dead monsters are updated each tick, so a step cost 6.6 ms; it now clears only the target's zone (0.7 ms per step, 9x faster, identical results), the runs are sharded per class and per elite, and every fight prints a progress line. Still open: the step loops over all ~1,970 monsters even when they sleep (0.7 ms), so a world built from only the target's zone, or a tick-skipping loop, would be another ~5x; the coarse-tick idea is untouched. Original task: make the group-elite and kill-time harness runs much faster (owner asked on 2026-10-16 for roughly 10x; the first solo-elite run took over 30 minutes on 4 cores). The simulation already runs without waiting, so the cost is CPU per `World::step`, and `TICK` (0.05 s, `model.rs`) is a compile-time constant used by movement, cooldowns and attack windows, so a larger tick changes the results. Options, in order: profile one `run_once` and cut the per-step work that does not matter for a duel (ambient players, other zones, instances, weather, escorts, chests) and the world rebuild per case; run one process per class and no more processes than cores; stop a case early once it is decided (the lone player dies, or the elite is below a health line it cannot recover from). Only then try a coarser tick for the harness, and only after a same-seed comparison of a few dozen cases at the normal tick and the coarse tick shows the same kill/no-kill result and kill times within a few percent.
- [x] `ELITE-SOLO-FIX` — Done 2026-10-16 for the open-world group elites, under the owner's rule (a lone player at the elite's level in ordinary green gear cannot kill it; it is soloable with good gear (purple) or about five levels above; a party of the recommended size can beat it). `world/elite-power.txt` (applied in `Slime::stats` via `items::elite_power`) holds per-kind health and damage multipliers: Cinderlord x8 / x1.1 (lone green 0 of 20 wins, lone purple 1 of 17, green +5 levels 2 of 14, two players win 4 of 4 in green and purple), Hvitserk x1.25 health, Gloomroot x0.8 / x0.6 and Hrungnir x0.8 health (they were unsoloable even in purple). A fight limit of 180 s applies to both the lone and the party checks. The 18 other elites the first run flagged are dungeon mobs, which follow the dungeon rules below. A second direction was tried and dropped: scaling a short-handed party's damage by (fighters/needed)^2 (owner wanted gear and level to decide). Tests: `bash scripts/elite-solo-parallel.sh`, `bash scripts/elite-party-parallel.sh` (`ELITE_SOLO_KINDS`, `ELITE_SOLO_FAIL_FAST=0` for calibration; fail-fast is the default).

## Dungeon difficulty

Owner's rules (2026-10-16): in a dungeon a lone player may or may not beat a single mob (not a rule); a **pack** of mobs must kill a lone player; a **boss** must kill a lone player; and a **party of five** must be able to beat every pack and every boss. Tests: `server/src/world/dungeon_solo_tests.rs`, run with `bash scripts/dungeon-solo-parallel.sh` (lone players, about 50 minutes on 4 cores, `DUNGEON_SOLO_FAIL_FAST=0` collects every violation) and `bash scripts/dungeon-party-parallel.sh` (the party-of-five control, about 3 minutes). A pack is three or more mobs of a dungeon whose spawns chain within 10 tiles; a boss is any monster that appears once in its dungeon or is its final boss. The multipliers go in `world/elite-power.txt`.

- [x] `DUNGEON-TESTS` — Built 2026-10-16, with the harness fix that makes dungeon monsters act at all (the harness must call `enter_instance`; an unentered dungeon copy is frozen). Baseline on the unchanged dungeons: a lone green player died in only 16 of 320 pack fights (5%; the Cathedral packs were cleared 120 of 120) and in 14 of 1,590 boss fights (0.9%; lone players killed the boss in about 45% of fights); a lone player beat 474 of 480 single mobs. Five players in green gear beat 83 of the 85 packs and bosses (only the final bosses Bloom Heart and Solstice Heart held out).
- [x] `DUNGEON-PACK-LETHAL` — Done 2026-10-16 for the ten dungeons that have packs, with damage multipliers in `world/elite-power.txt` (Undervault x7, Drowned Cathedral x16, the six later dungeons with packs x24). 4 seeds, 32 packs: a lone player survived 0 of 640 fights and five players in green gear won 32 of 32 packs in 4 of 4 runs. Six dungeons (Eye Below, Elder Hollow, Thousandfold Pavilion, Sunken Astrolabe, Blooming Labyrinth, Silent Solstice) have no group of 3 or more mobs, so they are untouched: add real packs or make their pairs lethal (owner's choice). Details and the calibration tool (`scripts/dungeon-calibrate.py`, no rebuild per trial) are in [docs/dungeon-solo-report.md](docs/dungeon-solo-report.md). Not deployed yet (compiled in: rebuild and restart).
- [x] `DUNGEON-BOSS-LETHAL` — Done 2026-10-16 with a soft enrage instead of multipliers (`world/enrage.txt`, `items::enrage_factor`): 47 bosses, start about 6% past the slowest party kill, then +100% damage per 0.2 s. Green lone heroes cleared 36 of 470 fights before and 0 now; purple at the dungeon's level 383 before and 42 now; purple +5 may clear (owner agreed). The party of five wins all 47 in 4 of 4 runs. Left without an enrage: Choir, Colossus, Hollowking (no lone player kills them; party needs 90-180 s) and Bloom Heart / Solstice Heart (the green party cannot beat them in 180 s, cause unknown, see [docs/dungeon-solo-report.md](docs/dungeon-solo-report.md)). Compiled in, not deployed.
- [ ] `DUNGEON-PARTY-CHECK` — Packs (32 of 32) and the 47 enraged bosses are green in 4 of 4 runs; still open: the two final bosses Bloom Heart and Solstice Heart that the green party cannot beat in 180 s, and Thunder Heart's slow runs. After the two items above, run the party-of-five control until it is green for every pack and boss. Today the final bosses Bloom Heart (Blooming Labyrinth) and Solstice Heart (Silent Solstice) already beat five players in green gear, so they need easing, not hardening.

### Plan for hardening the dungeons (written 2026-10-16, not started)

Goal: for each of the 16 dungeons (Undervault, three Cathedral wings, Moonwell and the 11 later instances), a pack kills a lone player, a boss kills a lone player, and a party of five in green gear still beats every pack and boss. Single mobs stay as they are.

1. **Make calibration cheap first.** Today a multiplier change needs a rebuild (about 1.5 minutes) because `world/elite-power.txt` is compiled in. Add a test-only override (an `ELITE_POWER_FILE` environment variable read by `items::elite_power` under `cfg(test)`), a `DUNGEON_SOLO_DUNGEONS=<names>` filter in `dungeon_solo_tests.rs`, and a small driver script (`scripts/dungeon-calibrate.py`) that tries a multiplier, runs the lone and party checks for one dungeon, and prints the result. Then each trial is minutes, not an hour.
2. **Pick the knob per kind.** A pack kills a lone player through damage, not health, so raise **damage** on the mob kinds that appear in packs (the same kind also appears alone, which is fine: a single mob only has to be reported). A boss that only survives because it is slow (the Undervault bosses: the lone player lives but cannot finish them) needs **damage**; a boss that a lone player kills in 120 to 180 seconds needs **health and damage** together. Use the shared `world/elite-power.txt` table, one entry per kind, never the base stat tables.
3. **Order of work.** (a) The Undervault and the three Cathedral wings: they have real packs of 3 to 4 and the biggest gap (the Cathedral packs were cleared 120 of 120 times). (b) The Moonwell: three packs of 4 plus singles. (c) The 11 later dungeons: they have almost only lone mobs and a few pairs and triples, so first decide with the owner whether to add real packs (more spawns close together in `world/*.txt` or `generate_*.py`) or to make the existing pairs and triples lethal by power alone; the pack test only counts groups of 3 or more, so some dungeons have no pack to test today.
4. **Per dungeon, the loop.** Start from a damage multiplier of 1.5 on pack kinds and 2 on bosses; run the lone checks with `DUNGEON_SOLO_FAIL_FAST=0` and 2 seeds; raise by half steps until every lone fight ends in the player's death at green and purple gear at the dungeon's level and purple +5 for bosses; then run the party-of-five control in green gear; if the party loses a fight, lower the damage and raise health instead, or add the missing time (the fight limit is 180 s for both sides). Finish with 4 seeds on the final numbers.
5. **Final bosses that are already too hard.** Bloom Heart (Blooming Labyrinth) and Solstice Heart (Silent Solstice) beat five players in green gear today. Ease them first (multiplier under 1) before hardening their dungeons' other bosses.
6. **Regression after each batch.** The full Rust suite (`bash scripts/cargo.sh test`, about 6.5 minutes), the real-server scenario for that dungeon (`node scripts/test-via-mcp.cjs run <name>`; many hard-code monster health, for example `undervault`, `elder_hollow`, `thousandfold_foes`, `blooming_foes`, `solar_crucible`, `amber_archive`, `silent_solstice`), `cargo clippy --all-targets -- -D warnings`, and the dungeon Chromium tests that mention bosses. Update every test that hard-codes a changed number, and keep mechanics tests (credit, mercenaries, evade) on pinned stats as the Cinderlord tests are.
7. **Check the side effects.** Experience, gold and drops come from the level and kind, not from the multipliers, so rewards stay the same while the fights get longer and deadlier; check that the quest text and the group hints ("Group · 5 players") still match, that mercenary rental still fills a party (the hired fighters count as party members in the party control), and that nobody is stuck in a dungeon they cannot leave (the exit opens when the final boss falls).
8. **Deploy and watch.** One backup-and-restart deploy per batch of dungeons, with the new numbers in the change note, and a read of the Surv alarms and the journal afterwards. Record the final table and the party results in `docs/dungeon-solo-report.md` and the wiki.

## Previous gear redesign

All 252 level-25–50 and Cathedral base pieces are complete. Detailed piece history is in [GEAR_REDESIGN_TODO.md](GEAR_REDESIGN_TODO.md).

- [x] `R-CHECK` — Complete its final generator, Rust, MCP and browser/art integration checks, then close the detailed checklist.

## Completed in this batch (2026-10-12)

Closed 20 items: level-95 gear bonus; hunter ranks through 98; five level-99 capstones; five skill identity updates; high-level unlock and skillbar migration checks; world-map graph, routes and consistency; and mount price, speed, client controls and private-world checks. The mount costs 50,000 gold at level 50, persists across login, travels at twice normal speed, and dismounts for combat. Private mount and skill checks passed; the map data and client copy match across 29 connected zones with four distinct sealed doors and no tile overlaps. The full world-map browser suite and full Rust suite were not completed in this batch.
