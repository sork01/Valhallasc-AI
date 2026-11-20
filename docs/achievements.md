# Achievements

Beta 1.30.0 adds character-specific achievements. Each awards positive achievement
points once; some also award a title or mount. World Menu → Achievements and the
Character window open the panel. It shows earned points / maximum points, each
requirement, progress, completion state, points and rewards, with all/completed/in
progress filters. The title selector offers earned titles and No title.

Beta 1.30.2 exposes the catalog's Adventure (17), Combat (40), Quests (13) and
Exploration (32) categories as filter buttons with completed / total counts.
All achievements groups cards under category headings. Category selection combines
with the completion filter; counts always describe the whole category. Refreshes
preserve the selected category, focused button and scroll position. Switching a
filter starts at the top. Category labels and headings support Swedish.
Cards have layered gold borders, four decorative SVG corner flourishes, point
medallions and a brighter completed finish. This is a client-only release.
The category buttons share one row, with counts beneath their labels.
Validation: 120 bounded browser checks pass at 844×390 and 1024×768 (923 MiB
peak). Disabling the category predicate with `MUTATE=category` fails at the
Adventure-only assertion as intended. JavaScript syntax, Swedish generation,
release-note checks and all six changed public client file hashes pass.

Beta 1.30.3 adds a 4.8-second emerald trophy ribbon with a stamping gold seal,
one gleam and six drifting diamond motes. Its short struck-bell cadence uses the
shared effects bus, Sound toggle and squared volume taper. Reduced motion shows
a still ribbon. The overlay captures no input and does not pause play.
The client consumes the original successful `Achievement earned: NAME (+N points).`
notice from `world/achievements.rs`, before localization; ordinary chat cannot
trigger it. A 200 ms collection window batches simultaneous awards, shows the
first two names and remaining count, and sums their points. Awards wait for an
active level-up banner or hidden document before showing. Names are deduplicated
within the connection; disconnect/character reset clears the timers, queue and
visible ribbon. Opening the panel and login reconciliation do not replay awards.
This presentation needs no server rebuild. If the server notice format changes,
update the parser and its focused integration check together.
`tests/achievement-effects-ui.cjs` passes 48 bounded phone/tablet checks (617 MiB
peak), including real server awards, level-up sequencing, batching, duplicate and
reset handling, Swedish text and native offline rendering of the production bell
and effects-bus functions for audible level, no clipping, volume taper and mute.
Removing notice dispatch with `MUTATE=1` fails waiting for the ribbon, as intended.
Syntax, Swedish generation, release notes and seven public client hashes pass.

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
Gryphon mount, with the normal 1.6× speed, riding, selection and collision rules.
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

Prepared catalog: **154 achievements / 4,090 points / 20 titles / 12 available mounts**.
The live catalog remains **120 achievements / 2,555 points / 12 titles**. Fishing
and the seahorse quest are live; the November 20 expansion remains staged at the
owner's explicit request.
The older seasonal candidate totals below describe their historical releases.

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

## Seasonal quest sets (Beta 1.35.0)

Hallowed Hearts and Merry in Every City each award 25 points and the suffix
titles `the Hallowed` and `the Merry`. Each requires the four distinct annual
city errands plus one claimed daily hunt for its festival. Completions across
years count, following the permanent achievement evidence model. Claimed
seasonal ledgers reconcile old completions even after a pending quest has
replaced an earlier run. Accepted or ready-but-unclaimed quests do not count.
Earned titles survive expiry, reconnect and rebirth; names and name reservation
keys are untouched. The catalog now has 104 achievements / 2,250 points and
eight title rewards. Existing suffix rendering and selection/celebration are
reused.

## Easter candidate

Eggstraordinary Easter awards 25 points and selectable suffix `the Springbringer`
for all five distinct claimed Easter quests. Permanent claimed history across
years counts; accepted/ready quests never do. One daily hunt claim counts once.
The existing celebration, name display and selector are reused, with no saved
name/reservation changes. Reconnect, expiry and rebirth retain rewards. This
independent candidate has 105 achievements / 2,275 maximum points / nine titles;
New Year and Valentine remain separate branches. See easter-event.md.
## Valentine's prefix title (candidate Beta 1.36.0)

Lovefool awards 25 points for claiming all five distinct Valentine quests (the four
annual city errands plus one daily hunt). Permanent claim history across years
counts; accepted/ready quests do not. The catalog now has 105 achievements, 2,275
points and nine titles. The catalog's default-false `title_prefix` marks this title
as a prefix; snapshots and achievement replies expose its placement explicitly.
The shared name formatter paints `Lovefool Sork` in HUD, remote nameplates and
player targets, with one separating space. Existing titles remain suffixes. Saved
names and reservations never change. Expiry, reconnect and actual rebirth preserve
evidence, points, eligibility and selection. Rewards use the usual award notice,
celebration and selector, with English/Swedish presentation. This feature is a
private candidate; see valentines-event.md and valentines-validation.md.
## New Year (Beta 1.36.0)

Ring in the New Year requires one claimed `newyear_hunt`, grants 25 points
and no title. It uses permanent quest/seasonal claim reconciliation across
years, independently of the rare mount roll. Accepted/ready quests do not
count; repeats never add points. Catalog: 105 achievements / 2,275 points,
with the existing eight titles and mount rewards preserved.

## Fishing achievements (FISH-META, 2026-11-19)

Thirteen achievements add 230 points and two suffix titles in the Fishing category.
They read the saved `Character.fishing` log, so existing fishing history reconciles
on the next achievement update without inventing catches from inventory. Buying,
trading, receiving or cooking fish never grants catch credit. One successful hook
counts once even with rebirth copies; junk, treasure and misses do not count.

| Achievement | Requirement | Points | Extra reward |
| --- | --- | ---: | --- |
| First Catch | Catch 1 fish. | 5 |  |
| A Hundred Hooks | Catch 100 fish. | 10 |  |
| A Thousand Catches | Catch 1000 fish. | 20 | the Angler |
| Shore Collection | Catch every species in the Shore habitat. | 20 |  |
| Coldwater Collection | Catch every species in the Cold habitat. | 20 |  |
| Swamp Collection | Catch every species in the Swamp habitat. | 20 |  |
| Forest Collection | Catch every species in the Forest habitat. | 20 |  |
| Jungle Collection | Catch every species in the Jungle habitat. | 20 |  |
| Oasis Collection | Catch every species in the Oasis habitat. | 20 |  |
| Spring Collection | Catch every species in the Spring habitat. | 20 |  |
| Lava Collection | Catch every lava species, including Phoenix Koi and Sunfire Ray. | 20 | Lavacaster |
| A Legendary Catch | Catch 1 legendary fish. | 25 |  |
| Heavy Haul | Catch a fish weighing at least 20 kg. | 10 |  |

Habitat collections require each distinct species with a positive catch count.
The eight member lists match `world/fish.txt` (57 species total); Lava includes both
zone-exclusive legendaries. A weight record requires a positive catch count for a
catalog species; unknown and zero-count records cannot qualify. Progress is capped
at its target. The legendary and total counters are clamped before u64-to-u32
conversion. No new persisted fields or migrations are needed. Logs, awards, points
and title selections survive save/reconnect and rebirth, using the existing ledger.
Existing suffix rendering, celebration and category navigation handle the additions.
All new names, descriptions, the category and both titles have hand-written Swedish.

No new mount or cosmetic rewards, version bump or release are part of this slice.
Focused Rust coverage is in `server/src/fishing_achievement_tests.rs` and the real
catch test in `server/src/world/fishing_tests.rs`. Catalog-dependent browser fixtures
are updated; browser execution awaits an approved replacement host under FISH-CHECK.


Validation for this slice: **44 distinct focused Rust tests pass** (32 `fishing_`
checks and 12 existing achievement checks, with no duplicate test runs in the clean
build). These include real hooks, both title snapshots, SQLite reconnect, duplicate
award prevention, saved prior history and rebirth. **Eight independent mutations**
are caught by `python3 tests/fishing-meta-mutations.py`: disabled progress, counter
wrap, duplicate species, zero-count species, foreign species, legendary credit,
weight evidence and rebirth-copy inflation. The runner restores the real source;
all final checks used the clean build. Hand-written Swedish freshness/catalog and
23 locale checks, changed JavaScript/Python syntax, scoped rustfmt and diff whitespace
pass. All 107 earlier achievement catalog entries are byte-equivalent as JSON values.

Strict all-target Clippy reports only the documented baseline: unused `mail_unread`
and hosted-count helpers, quest-drop doc indentation and the quest-journal
single-element loop. No new lint diagnostics. Browser suites are not run on this
production host; updated catalog/category/title browser assertions await an approved
replacement host under FISH-CHECK. No world sync, version bump, release or restart.

## Silent expansion (2026-11-20)

34 new achievements add 1,535 points and eight suffix titles. All 120 existing
entries and their rewards remain unchanged. No new save fields, gameplay stats,
world generation, version label or release-note changes. Existing saved evidence
reconciles at login and the ordinary achievement update; unverifiable history
is never invented. Fisher circuits require a claimed quest at every distinct
Fisher, across any days or lifetimes; repeats at one Fisher cannot replace another.
The seahorse achievement requires the claimed quest, not mount inventory.
The complete fish collection needs a positive catch record for all 57 species.

| Achievement | Requirement | Points | Extra reward |
| --- | --- | ---: | --- |
| An Unbroken Watch | Defeat 2500 monsters. | 25 |  |
| A Thousand Roads Made Safe | Defeat 5000 monsters. | 30 |  |
| The Relentless Hunt | Defeat 10000 monsters. | 40 | The Relentless |
| A Legend in Every Camp | Defeat 25000 monsters. | 50 |  |
| Defender of the Realm | Defeat 50000 monsters. | 75 |  |
| A Taste for Danger | Defeat 5 different dungeon or raid bosses. | 20 |  |
| Ten Different Terrors | Defeat 10 different dungeon or raid bosses. | 25 |  |
| No Stranger to the Depths | Defeat 25 different dungeon or raid bosses. | 35 |  |
| Vanquisher of Legends | Defeat 50 different dungeon or raid bosses. | 50 | The Vanquisher |
| Every Terror Remembered | Defeat 75 different dungeon or raid bosses. | 75 |  |
| The Work Goes On | Complete 200 different quests. | 45 |  |
| Tales from Every Road | Complete 300 different quests. | 50 |  |
| Keeper of Five Hundred Stories | Complete 500 different quests. | 75 | The Storykeeper |
| A World of Deeds | Complete 750 different quests. | 100 |  |
| Ten Dawns Later | Be reborn 10 times. | 50 | The Everlasting |
| Life Finds a Way | Be reborn 20 times. | 75 |  |
| A Soul Without End | Be reborn 30 times. | 100 |  |
| Room for One More | Own 8 different mounts. | 30 |  |
| A Remarkable Menagerie | Own 10 different mounts. | 50 | The Collector |
| A Dozen Companions | Own 12 different mounts. | 75 |  |
| Learning the Waters | Catch 10 fish. | 5 |  |
| A Well-Worn Hook | Catch 25 fish. | 5 |  |
| Patience Pays | Catch 250 fish. | 15 |  |
| A Full Season of Fishing | Catch 500 fish. | 20 |  |
| The Long Cast | Catch 2500 fish. | 30 |  |
| Master of the Tides | Catch 5000 fish. | 50 | The Tidemaster |
| Legends on the Line | Catch 10 legendary fish. | 30 |  |
| More Than a Fish Tale | Catch 50 legendary fish. | 50 |  |
| Every Fish Has a Story | Catch all 57 different fish species. | 100 | The Complete Angler |
| Fresh Fish Everywhere | Claim the Fresh Fish quest at each of the 13 Fishers. | 25 |  |
| Finer Fish Everywhere | Claim the Finer Catch quest at each of the 13 Fishers. | 30 |  |
| Friend of the Fishers | Claim the Trophy quest at each of the 13 Fishers. | 50 | Friend of the Fishers |
| The Daily Round | Claim the Daily Creel quest at each of the 13 Fishers at least once. | 30 |  |
| A Bond Beneath the Waves | Complete A Friend Beneath the Tide in Rán's Deep. | 20 |  |

Validation: all 25 focused `achievements` Rust checks pass, including the six new
post-launch tests. Six independent catalog faults are caught by
`python3 tests/achievement-refresh-mutations.py`; its temporary instrumentation is
removed before the clean release build. The original catalog fingerprint, exact
threshold boundaries, all 57 possible missing species, every missing Fisher,
claimed-versus-pending quests, new title validation and save/rebirth persistence
are covered without grinding. The existing fishing fixtures now exclude species
shared with the new complete collection, and their overflow scenario explicitly
expects the new 10/50-legendary rewards; their former expectations were obsolete.
All catalog maxima and category counts in affected Rust/seasonal/browser fixtures
are updated together. Swedish coverage/freshness, 23 locale checks, scoped Rust
formatting, JavaScript/Python syntax and the unchanged-version release gate pass.
Browser suites are not run under the production-host restriction.
Strict Clippy remains blocked only by documented baseline diagnostics: unused
`mail_unread` and hosted-count helpers, quest-drop doc indentation and the
quest-journal single-element loop. No diagnostic points to the new tests or data.
The clean production release binary also passes 121 private WebSocket/catalog/
Swedish checks in `tests/achievement-refresh-probe.cjs`: authoritative totals and
categories, initially locked goals, a real new award notice, unearned-title
refusal, the new title in a second player's snapshot, the claimed seahorse quest,
and points/title persistence through reconnect and a full SQLite process restart.
Every new name, description and title is checked through production `Locale.translate`.
The release executable is 56,242,576 bytes and contains no mutation instrumentation.


### Staged deployment handoff (owner decision, 2026-11-20)

Owner explicitly chose **Keep staged** after validation; do not infer permission
for a later public restart. Implementation `cc1c12fa` is pushed to main. The initial client
translation release `1.2.0-cc1c12fa` was verified; the later guest/performance
client `1.2.0-f8031984` includes those translations without activating the
achievements. The running
public executable is still the previous release (PID 1250668 at verification).
The new achievements become available only after an explicitly approved restart.
Version remains 1.2.0 and release notes are unchanged.

Clean implementation checkout: `/media/raid/valhallasc-data/achievement-refresh`.
Executable and running-DB backup, candidate, verification logs and deployment state:
`deploy/backups/achievement-refresh-20261120T063606Z/`. Its
`valhalla-server.candidate` is 56,242,576 bytes, SHA-256
`5f93ba8337d98c920334aadb6e0e3497f57a0c0e786a18e077c8a23f3e27f66b`.
`candidate.json` records the source commit, public client hash and staging decision;
`valhalla-server.prev` and `running.sqlite` preserve the previous executable and
consistent live database. On a future approved install, take a fresh backup,
stop, preserve the stopped database, install the exact verified candidate, start,
and verify the running hash, public/bridge health, SQLite quick_check and journal.
No migration is required. Keep the independent fishing test service inactive.
The shared main checkout's pending female character art was excluded and preserved.
