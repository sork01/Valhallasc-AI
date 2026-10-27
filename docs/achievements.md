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
together. See the table below for the launch catalog.

41 achievements; maximum **685 points**.

| Achievement | Requirement | Points | Extra reward |
| --- | --- | ---: | --- |
| Finding Your Feet | Reach level 10. | 10 |  |
| Seasoned Adventurer | Reach level 50. | 20 |  |
| At the Summit | Reach level 99. | 30 |  |
| First Victory | Defeat 1 monsters. | 5 |  |
| Monster Hunter | Defeat 100 monsters. | 10 |  |
| Veteran Hunter | Defeat 1000 monsters. | 20 |  |
| Helping Hand | Complete 1 different quests. | 5 |  |
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
| A New Beginning | Be reborn 1 times. | 20 |  |
| Five Lives | Be reborn 5 times. | 40 |  |
| A Seat at the Table | Complete the final chapter of The Empty Seat. | 30 |  |
| Dungeon Victor | Defeat a dungeon or raid boss. | 15 |  |
| Breaker of the Ten Chains | Defeat all ten different Chained Forge bosses. | 100 | The Chainbreaker, Gryphon mount |
| Stable Friends | Own 3 different mounts. | 20 |  |

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

## Deployment

Beta 1.30.0 is live from source `0e5083b` (2026-10-27). The release was built
in the isolated RAID checkout, privately checked and installed with nobody online.
Both bridge/public health, all nine changed public client hashes, the exact
running binary, SQLite `quick_check`, unchanged 31 characters / 18 existing guests,
absence of test flags and a clean warning/error journal were verified. No zone
IDs changed or character backfill was needed; no public test guests were created.

Rollback and proof: `deploy/backups/achievements-1.30.0-20261027T173235Z/`, including the previous
running binary, consistent live/stopped database snapshots, `verified.txt`,
focused check logs and phone/tablet screenshots under `verification/`.
