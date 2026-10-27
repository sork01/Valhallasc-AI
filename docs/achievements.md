# Achievements

Beta 1.30.0 adds character-specific achievements. Each awards positive achievement
points once; some also award a title or mount. World Menu → Achievements and the
Character window open the panel. It shows earned points / maximum points, each
requirement, progress, completion state, points and rewards, with all/completed/in
progress filters. The title selector offers earned titles and No title.

The server owns completion and unlocks. Points are the sum of completed catalog
entries, and the maximum is the sum of all catalog points, including completed
ones. Points are a score, not currency. The panel requests the catalog on opening
and refreshes every 1.5 seconds while open; snapshots carry only the chosen title
and earned points. Ordinary progression is reconciled once a second and awards a
notice. Closing a window never pauses the world.

## Evidence, saves and rebirth

The `#[serde(default)]` achievement ledger belongs to the character, including
for guests. Old saves start with an empty ledger, then reconcile saved level,
kill count, completed quests, explored masks, rebirths and mounts at login.
Unknown past boss kills are not invented: boss achievements track kills from this
release onward. Already-earned mounts remain owned; the Forge reward adds an
alternative route to the same Gryphon, never a duplicate or a replacement for an
existing selected mount. The egg/hatching route remains available.

The ledger preserves highest level, different completed quest IDs, the union of
explored cells and different defeated boss kinds. Repeated quest completions count
once; rewardless `es_go_*` directions do not count. The final story chapter is
`es_28`. Saved kill and rebirth counters are already permanent. The ledger and
selected title survive rebirth; evidence is reconciled before quests, level and
fog reset. Exploration achievement progress spans lifetimes; the map still shows
the current lifetime's fog. Achievements remain complete when more content arrives.
The catalog defines the current maximum, so adding achievements increases it.

## Exploration and combat credit

The Explorer means the whole outdoor atlas: the nine authoritative 3×3 fog cells
in each of the 23 provinces in `world/atlas-geography.txt` (207 cells). Every region
also has a 10-point achievement for its nine cells. Interior cities, dungeon
copies, match-only arenas, offshore decorative clouds and sealed templates add no
requirements. Atlas regions are read from the existing geography, never guessed
from clone IDs. Only server movement uncovers cells. Fake client masks cannot
change achievement evidence. The selected title renders as `<Name> The Explorer`;
Swedish clients translate the title while preserving the name.

Boss credit follows the existing kill-credit group: the living killer (or hirer
of the hired killer) and living party members in the same dungeon copy. Dead
players, strangers, players in another copy, hires and ambient adventurers receive
no ledger credit. Repeated boss kills count once. Boss mechanic helpers do not
count. Forge completion needs all ten named bosses; merely entering or completing
The Ember Key is insufficient. Its reward is The Chainbreaker and the existing
Gryphon mount, with the normal 2× speed, riding, selection and collision rules.
Titles are cosmetic suffixes shown in the HUD and remote world nameplates (and
player target badge); they coexist with the separate rebirth tier badge/aura.
Unknown or unearned title selections are refused without changing the selection.

## Catalog

`world/achievements.txt` is the source for IDs, positive points, thresholds, titles
and mount rewards. The server embeds it; no world/map generation is needed. New
catalog text needs hand-written Swedish. No gameplay stats or encounter balance
change. When expanding the atlas, add the new region achievement and update the
Explorer threshold, translations, documented maximum and focused catalog checks
together. See the table below for the current catalog.

102 achievements; maximum **2,200 points** (Beta 1.30.1).

| Achievement | Requirement | Points | Extra reward |
| --- | --- | ---: | --- |
| Finding Your Feet | Reach level 10. | 10 |  |
| Seasoned Adventurer | Reach level 50. | 20 |  |
| At the Summit | Reach level 99. | 30 |  |
| First Victory | Defeat 1 monster. | 5 |  |
| Monster Hunter | Defeat 100 monsters. | 10 |  |
| Veteran Hunter | Defeat 1000 monsters. | 20 |  |
| Helping Hand | Complete 1 quest. | 5 |  |
| Trusted Friend | Complete 25 different quests. | 15 |  |
| Questkeeper | Complete 100 different quests. | 30 | The Questkeeper |
| Beyond the Horizon | Visit 5 atlas regions. | 10 |  |
| World Traveller | Visit 23 atlas regions. | 25 |  |
| Explore Greenmeadow | Uncover all 9 map cells in Greenmeadow. | 10 |  |
| Explore Emberfall Crags | Uncover all 9 map cells in Emberfall Crags. | 10 |  |
| Explore Rimeveil Glacier | Uncover all 9 map cells in Rimeveil Glacier. | 10 |  |
| Explore Gloamfen | Uncover all 9 map cells in Gloamfen. | 10 |  |
| Explore Skaldholm | Uncover all 9 map cells in Skaldholm. | 10 |  |
| Explore Wyrdwood | Uncover all 9 map cells in Wyrdwood. | 10 |  |
| Explore Bifrost Reach | Uncover all 9 map cells in Bifrost Reach. | 10 |  |
| Explore Rán's Deep | Uncover all 9 map cells in Rán's Deep. | 10 |  |
| Explore Nacrehold | Uncover all 9 map cells in Nacrehold. | 10 |  |
| Explore Astralhollow | Uncover all 9 map cells in Astralhollow. | 10 |  |
| Explore The Prismwaste | Uncover all 9 map cells in The Prismwaste. | 10 |  |
| Explore The Obsidian Orrery | Uncover all 9 map cells in The Obsidian Orrery. | 10 |  |
| Explore The Moonspore Canopy | Uncover all 9 map cells in The Moonspore Canopy. | 10 |  |
| Explore The Stormglass Shore | Uncover all 9 map cells in The Stormglass Shore. | 10 |  |
| Explore Sunward Vale | Uncover all 9 map cells in Sunward Vale. | 10 |  |
| Explore The Ribbonwild | Uncover all 9 map cells in The Ribbonwild. | 10 |  |
| Explore The Tanglecrown | Uncover all 9 map cells in The Tanglecrown. | 10 |  |
| Explore Veyrroot | Uncover all 9 map cells in Veyrroot. | 10 |  |
| Explore The Lapis Erg | Uncover all 9 map cells in The Lapis Erg. | 10 |  |
| Explore Frostwake Shelf | Uncover all 9 map cells in Frostwake Shelf. | 10 |  |
| Explore The Cairnspine | Uncover all 9 map cells in The Cairnspine. | 10 |  |
| Explore The Yearwheel | Uncover all 9 map cells in The Yearwheel. | 10 |  |
| Explore Emberwake Caldera | Uncover all 9 map cells in Emberwake Caldera. | 10 |  |
| The Explorer | Uncover all 207 map cells across the 23 atlas regions. | 50 | The Explorer |
| A New Beginning | Be reborn once. | 20 |  |
| Five Lives | Be reborn 5 times. | 40 |  |
| A Seat at the Table | Complete the final chapter of The Empty Seat. | 30 |  |
| Dungeon Victor | Defeat a dungeon or raid boss. | 15 |  |
| Breaker of the Ten Chains | Defeat all ten different Chained Forge bosses. | 100 | The Chainbreaker, Gryphon mount |
| Stable Friends | Own 3 different mounts. | 20 |  |
| A Small Adventure | Reach level 5. | 5 |  |
| Ready for the Depths | Reach level 20. | 10 |  |
| Under a Wider Sky | Reach level 30. | 10 |  |
| Through Storm and Shadow | Reach level 40. | 15 |  |
| Among the Stars | Reach level 60. | 20 |  |
| Sunlit Veteran | Reach level 70. | 20 |  |
| Roots of Greatness | Reach level 80. | 25 |  |
| Winter Cannot Stop Me | Reach level 90. | 25 |  |
| Ten Victories | Defeat 10 monsters. | 5 |  |
| Making the Roads Safer | Defeat 25 monsters. | 5 |  |
| A Formidable Foe | Defeat 250 monsters. | 15 |  |
| Protector of the Roads | Defeat 500 monsters. | 15 |  |
| A Familiar Face | Complete 5 different quests. | 5 |  |
| Always Happy to Help | Complete 10 different quests. | 10 |  |
| A Friend in Every Town | Complete 50 different quests. | 20 |  |
| No Plea Unanswered | Complete 150 different quests. | 40 |  |
| Far from Home | Visit 10 atlas regions. | 15 |  |
| Many Roads Travelled | Visit 15 atlas regions. | 20 |  |
| Nearly Everywhere | Visit 20 atlas regions. | 20 |  |
| Twice Renewed | Be reborn 2 times. | 25 |  |
| Another Dawn | Be reborn 3 times. | 30 |  |
| Filling the Blank Spaces | Uncover 52 of the 207 atlas map cells. | 10 |  |
| Half a World of Memories | Uncover 104 of the 207 atlas map cells. | 20 |  |
| The Last Few Blank Spaces | Uncover 156 of the 207 atlas map cells. | 30 |  |
| Master of the Stables | Own all 5 different mounts. | 50 | The Stablemaster |
| The Story Takes Root | Complete chapter 5 of The Empty Seat. | 10 |  |
| Following the Empty Chair | Complete chapter 10 of The Empty Seat. | 15 |  |
| Remembering the Forgotten | Complete chapter 15 of The Empty Seat. | 20 |  |
| Witness to the Truth | Complete chapter 20 of The Empty Seat. | 25 | The Witness |
| Before the Last Door | Complete chapter 25 of The Empty Seat. | 30 |  |
| Break the Chain: Kettil Linkbearer | Defeat Kettil Linkbearer in The Chained Forge. | 25 |  |
| Break the Chain: Ysolt Bellowsmaid | Defeat Ysolt Bellowsmaid in The Chained Forge. | 25 |  |
| Break the Chain: Hallgrim Anvilhand | Defeat Hallgrim Anvilhand in The Chained Forge. | 25 |  |
| Break the Chain: Sigrun Slagmother | Defeat Sigrun Slagmother in The Chained Forge. | 25 |  |
| Break the Chain: Dagfinn Tongsbearer | Defeat Dagfinn Tongsbearer in The Chained Forge. | 25 |  |
| Break the Chain: Thorbjörg Quenchwife | Defeat Thorbjörg Quenchwife in The Chained Forge. | 25 |  |
| Break the Chain: Ragnhild Cinderfoot | Defeat Ragnhild Cinderfoot in The Chained Forge. | 25 |  |
| Break the Chain: Orm Ashwalker | Defeat Orm Ashwalker in The Chained Forge. | 25 |  |
| Break the Chain: Hildr Lastlink | Defeat Hildr Lastlink in The Chained Forge. | 25 |  |
| Break the Chain: Eldmarr, the Ember-Lord | Defeat Eldmarr, the Ember-Lord in The Chained Forge. | 25 |  |
| Conquer The Undervault | Defeat every boss in The Undervault. | 30 |  |
| Conquer The Drowned Cathedral — Flooded Cloister | Defeat every boss in The Drowned Cathedral — Flooded Cloister. | 30 |  |
| Conquer The Drowned Cathedral — Coral Reliquary | Defeat every boss in The Drowned Cathedral — Coral Reliquary. | 30 |  |
| Conquer The Drowned Cathedral — Grand Nave | Defeat every boss in The Drowned Cathedral — Grand Nave. | 30 |  |
| Conquer The Moonwell | Defeat every boss in The Moonwell. | 30 |  |
| Conquer The Eye Below | Defeat every boss in The Eye Below. | 30 |  |
| Conquer The Elder Hollow | Defeat every boss in The Elder Hollow. | 30 |  |
| Conquer The Thousandfold Pavilion | Defeat every boss in The Thousandfold Pavilion. | 30 |  |
| Conquer Temple of the Rain Crown | Defeat every boss in Temple of the Rain Crown. | 30 |  |
| Conquer The Seed Vault | Defeat every boss in The Seed Vault. | 30 |  |
| Conquer The Sunken Astrolabe | Defeat every boss in The Sunken Astrolabe. | 30 |  |
| Conquer The Thunderheart Gate | Defeat every boss in The Thunderheart Gate. | 30 |  |
| Conquer The Blooming Labyrinth | Defeat every boss in The Blooming Labyrinth. | 30 |  |
| Conquer The Solar Crucible | Defeat every boss in The Solar Crucible. | 30 |  |
| Conquer The Amber Archive | Defeat every boss in The Amber Archive. | 30 |  |
| Conquer The Silent Solstice | Defeat every boss in The Silent Solstice. | 30 |  |
| Conquer Nornroot Barrow | Defeat every boss in Nornroot Barrow. | 30 |  |
| Conquer The Shattered Span | Defeat every boss in The Shattered Span. | 30 |  |
| Conquer The Drowned Longship | Defeat every boss in The Drowned Longship. | 30 |  |
| Conquer The Black Hour Foundry | Defeat every boss in The Black Hour Foundry. | 30 |  |
| Master of the Depths | Defeat every boss across all 20 non-raid dungeons. | 100 | The Delver |

## Focused verification

`cargo test achievements -- --nocapture` covers catalog/atlas totals, old saves,
existing progress, duplicate events, title validation, all-cell exploration,
rebirth persistence, actual combat credit, party/copy/death exclusions, and mount
ownership/selection. `tests/achievements-ui.cjs` uses the bounded touch harness at
844×390 and 1024×768 for the real panel, totals, authoritative exploration,
filters, title selection/refusal, reconnect persistence, another browser's
nameplate, touch targets and Swedish. Its mutation replaces the maximum with the
earned total and must fail. These checks use seeded progress, never grinding.

Validation: eight focused Rust tests and all 58 bounded phone/tablet browser
assertions pass on the release binary. Browser peak was 923 MiB under the
1536 MiB cap. Clippy with warnings denied, formatting, JavaScript/Python syntax,
Swedish coverage and release-note validation pass. Screenshots are in the private
worktree under `test-results/touch/achievements-{844x390,1024x768}.png`.
The incorrect-maximum browser mutation fails at the intended total-points
assertion (562 MiB peak). No encounter timing or balance suites were run.

## Initial deployment (Beta 1.30.0)

Beta 1.30.0 was deployed from source `0e5083b` (2026-10-27). The release was built
in the isolated RAID checkout, privately checked and installed with nobody online.
Both bridge/public health, all nine changed public client hashes, the exact
running binary, SQLite `quick_check`, unchanged 31 characters / 18 existing guests,
absence of test flags and a clean warning/error journal were verified. No zone
IDs changed or character backfill was needed; no public test guests were created.

Rollback and proof: `deploy/backups/achievements-1.30.0-20261027T173235Z/`, including the previous
running binary, consistent live/stopped database snapshots, `verified.txt`,
focused check logs and phone/tablet screenshots under `verification/`.

## Catalog expansion (Beta 1.30.1)

61 additional achievements use existing permanent evidence, with no new counters
or migration. Named boss sets require every distinct listed boss, and story
milestones require the exact completed chapter. Repeating one boss never
substitutes for another. Dungeon goals cover all 20 currently open non-raid
templates; the dungeon master needs all 65 different bosses across them.
Existing boss credit, saved exploration, highest level, quest IDs, kills,
rebirths and mount ownership credit the new goals on reconciliation. Historical
boss kills missing from the saved ledger remain unverifiable.

Expansion validation: 11 focused Rust tests and 68 bounded phone/tablet
assertions pass on the exact release binary (967 MiB peak under the 1536 MiB
cap). Tests cover preservation of the original 685 earned points and rewards,
distinct named boss sets, exact story chapters, the new title unlocks, current
maximum and Swedish rewards. Clippy, formatting, syntax, Swedish generation
and release-note checks pass.
The incorrect-maximum mutation fails at the intended 2,200-point total assertion
(553 MiB peak).

Beta 1.30.1 is deployed from source `7d1bb73`. Public/bridge health, the exact
running release binary, all three changed public client files, SQLite
`quick_check`, unchanged 31 characters / 18 existing guests, absence of test
flags and a clean warning/error journal were verified. Nobody was online during
installation; no zone migration, character backfill or public test guest.
Rollback and verification artifacts: `deploy/backups/achievement-expansion-1.30.1-20261027T175310Z/`.
