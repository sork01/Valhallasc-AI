# Fishing rules and implementation plan

Owner request (2026-11-18): fishing with craftable rods, a bobber in the water you press for when a fish bites, animations, fish icons, rare drops, places to fish, and a special rod for lava. Backlog chain: `FISH-*` in `TODO.md`.

## Grill answers (2026-11-18)
- **Bite:** pure timing, one press. Every fish has the same window. Rarity comes from the tables, rod and spot, never from a harder press.
- **Where:** any shore next to water (or lava with the lava rod), plus marked rich ripple spots.
- **Rods:** tiers, crafted at a Fisher NPC from the previous rod plus fish, a zone material and gold (a one-screen workshop, not a general crafting system).
- **Fish are for:** selling, food (eat raw, cook at the Fisher), Fisher quests, and a collection log with achievements.
- Fishing is a separate side activity. The 28 `es_` chapters stay untouched; Fisher quests are ordinary zone side quests. Ask again before touching `es_`.

## Server core decisions

The action is `fish`. A rod occupies a bag cell and the highest usable tier for the habitat wins. Fish use the stackable item kind `fish`. Fisher bring quests will consume the ordinary bag stack. The species roster and weight ranges are in `world/fish.txt`, with 57 species across eight habitats. Rods and fish have ordinary inventory definitions so private characters can exercise the complete loop before the Fisher vendors arrive.

Each cast needs a fresh press. Missing or interrupting a cast clears the current catch streak. Five timing misses display the doze-off message and reset the miss counter. A successful fish catch counts once for the collection and awards the rebirth-adjusted stack. Only the owner receives the Unix-seconds bite deadline. The public player snapshot supplies bobber position and phase. Rich spots have a three-tile radius. `fishingSpots` in map data is a validated candidate pool; only the randomly active points from the zone snapshot are rich. The data overlay, junk/treasure catalogue and raw fish meals are implemented by FISH-DATA. Fisher workshops, cooking and quests are implemented by FISH-RODS below; player controls belong to a later task.

## Core loop (server authoritative)
1. **Cast.** Action `fish` (one key, a touch button): the hero must be within 4 tiles of a water or lava edge, facing it, not in combat, not airborne, not in an instance or underwater zone (`UNDERWATER_THEMES`), with a rod in the bags and a free bag cell. A mount is dismounted (as for skills). Sanctuaries allow it (the pier is a sanctuary). The server picks the landing point: the nearest edge point toward the facing, 3 to 6 tiles out, and checks it lies in water/lava of a fishing habitat.
2. **Wait.** Server draws 3 to 12 s, scaled by rod tier and spot richness (`x0.75` on a rich spot), rain `x0.85`, dawn and dusk `x0.9`. Moving more than 0.6 tiles, taking damage, combat, opening a shop or a trade, or pressing the key again cancels the line. A press during the wait = "Too early", line pulled in, 1 s cooldown.
3. **Bite.** The server sends one `fish_bite` event with the server-clock deadline. The window is **1.2 s**, same for every fish, plus 0.25 s grace for latency (judged on the server clock, never on a client timestamp).
4. **Press.** Inside the window the catch is rolled: bag full or no loot = nothing is rolled. Outside = "It got away" and the line is gone. Five misses in a row end the session with "You doze off. Cast again to keep fishing" (stops idle macros).
5. **Catch.** The server picks the result, weight and rarity and puts it in the bags (`award_roll_item` style; every roll goes through `copies()`/`loot_stack`/`pile_for` so the rebirth multiplier applies, and `perks_tests` scans for it). The client never sends or decides what was caught.

Anti-exploit: one line at a time per hero, 1 s between casts, mercenaries and ambient adventurers never fish, no fishing during a duel or arena match, the key is ignored while a cutscene plays.

## Habitats and where to fish
Map objects kinds that are fishable water: `water` (1,733 circles: zones 2, 3, 6, 20, 25), `seafoam` (19), `jungle_water` (22), `year_spring_pool` (28), `frostwake_frozen_pool` (26), `jade_pool` (22), `lapis_oasis` (25), and **lava**: `lava` (zone 1, 543) and `ew_lava` (zone 45, 247). Greenmeadow (0) has inland water objects. At Saltby, the sea beside the pier is represented by void rectangles. A hero on the dock can cast across an exposed plank edge into that sea. The ship footprint is excluded. Ran's Deep and the Cathedral are underwater and excluded; `cf_lavafall` and the Foundry are instances and excluded.

| Habitat | Zones | Notes |
| --- | --- | --- |
| Shore (sea) | 0 pier, 19 Stormglass | 0 is the tutorial spot, 19 the salt fish |
| Cold water | 2 Rimeveil, 26 Frostwake | icy fish, 26 ice pools |
| Swamp | 3 Gloamfen | eels, bog fish |
| Forest river | 6 Wyrdwood, 20 Sunward | river fish |
| Jungle | 22 Tanglecrown | jade pool, bright fish |
| Oasis | 25 Lapis Erg | desert fish |
| Spring | 28 Yearwheel | seasonal-flavoured, high level |
| Lava | 1 Emberfall Crags, 45 Emberwake | needs a lava rod |

- **Any shore** works, with the zone's ordinary table.
- **Rich spots** ("ripples"): 4 to 8 active per fishing zone when separate waters fit, drawn as a ring of ripples, found by `scripts/fishing_spots.py --write` as an overlay (`world/fishing-spots.txt`, shipped by sync-world, run **after** `zone_shapes.py apply`, flood-checked to be reachable on foot, 18+ tiles off seams, 10+ tiles from hubs). A rich spot has `x3` rare weight, `x0.75` wait and its own spot fish.
- **Owner decision (2026-11-18): rich spots spawn randomly in the waters.** Each zone requests 4–8 active spots, with fewer where the valid waters cannot fit separate three-tile ripple areas (Lapis and Frostwake). Each yields 5–10 successful fish shared by all anglers, then disappears and is replaced at another valid water location. Junk and treasure do not spend a fish. Candidate waters remain byte-stable map data; active spots and their remaining catches are connection-independent world state, published in zone snapshots. No timer relocation.

## Rods
Item kind `rod` (not a worn slot: the best rod in the bags is used; a tenth-slot-style change like cloaks is not worth it). Data `world/rods.txt`, items by `scripts/fish_catalog.py` (idempotent overlay run by sync-world after `gear_levels.py`, like `cloak_catalog.py`).

| Tier | Rod | Level | Source | Reaches |
| --- | --- | --- | --- | --- |
| 1 | Twig Rod | 1 | vendor in Alderhaven, 50 copper | sea shore, Gloamfen, Rimeveil commons |
| 2 | Willow Rod | 10 | Fisher craft | zones 2-3 rich, 6 |
| 3 | Reedglass Rod | 25 | Fisher craft | zones 6, 20, 22 |
| 4 | Silverline Rod | 40 | Fisher craft | zones 19, 22, 25 |
| 5 | Starcatch Rod | 60 | Fisher craft | 26, 25 rares |
| 6 | Worldwire Rod | 80 | Fisher craft | 28 and every legendary |
| L1 | Emberline Rod | 5 | Fisher craft in Crags | lava, zone 1 |
| L2 | Magma Reel | 45 | Fisher craft in Emberwake | lava, zone 45, all lava legendaries |

Tier sets bite speed (-6% per tier on the wait) and the **rare weight** (+10% per tier), and gates which fish of a zone you can land (a fish has a `min_tier`). The craft is the previous rod + gold + 5 common fish of the band + one zone material (an elite or ordinary drop, `items::is_elite`), taken by the Fisher in one window (`rod:<tier>` offers like `repair:<copy>`; validate before taking, one transaction). A rod does not wear. A lava rod does not work on water and the reverse, so a hero carries both.

## Fish, junk and rare drops
About 60 species, ~7 per habitat: 3 common, 2 uncommon, 1 rare, 1 legendary ("trophy") per habitat, plus 4 shared. Each has: id, name, rarity, sell price, `min_tier`, weight range (kg, whole numbers for UI), `food` (raw heal) and a `dish` (cooked). Weights are rolled by the server and shown as `ca` rounded values (metric only). Draw weights: common 70%, uncommon 22%, rare 6%, legendary 0.5% (x3 on a rich spot, x rod tier bonus, a rain/dusk bonus), junk 8% on top.

- **Junk (sell 1-3 gold):** driftwood, a boot, tangled line, a cracked shell. Lava junk: cooled slag, charred branch.
- **Treasure:** Sunken Coffer (opens like a chest, uses `chests.rs` tiers; never orange), Message in a Bottle (small gold + a hint line about a spot), Lost Purse (gold), Rod Charm (a rare crafting extra: -1 required fish for the next craft).
- **Legendary fish** are announced to the zone (`announce` kind `treasure`, one packet) and shown with a glow. Examples: Moonscale Carp, Glass Eel, Jade Dragonfish, Frostwake Pike, **Phoenix Koi** (Crags lava), **Sunfire Ray** (Emberwake lava).
- Orange gear is never a fishing drop (`orange_rules`).
- Quest fish (`qi_`-style) are not needed: Fisher quests use the ordinary fish through `bring_have`.

## Using fish
- **Sell:** every fish and junk has `sell`. "Sell all junk" handles junk; fish are not junk (a confirm for rare and legendary).
- **Eat raw:** small heal, uses the 30 s meal timer (`consumables.rs`).
- **Cook:** the Fisher cooks fish into a dish (food kind, `family` ids, tiers like `traveler_stew`, `consumable_tiers.py`): better heal/mana, same 30 s timer, cost in gold. Raw never beats the vendor meal of its tier.
- **Collection log:** `Character.fishing` (`#[serde(default)]`): totals, per species count and best weight, longest streak, legendary count. A window lists every species with a silhouette until caught, plus records.
- **Achievements (FISH-META):** 13 achievements / 230 points: 1, 100 and 1000 successful catches; all eight habitat collections; first legendary; a 20 kg catch. Titles: "the Angler" at 1000 catches and "Lavacaster" for all eight lava species, including both zone-exclusive legendaries. Current feature catalog: 120 achievements / 2555 points / 12 titles / 11 mounts. See `docs/achievements.md`.
- **Quests:** a Fisher in each hub near water gives 3 bring quests (common, uncommon, rare fish of the band) and one daily-style repeatable. Ordinary side quests, with `level` and `rewardXp` = levels.txt[level-1]/10.

## Client: what it shows
No new class art. Like the lead shoes, fishing is a **derived overlay** (`drawFishing` in `field.js`), so no per-class sprites change:
- **Cast:** the hero turns to the water and plays the existing attack swing (the whip frame as the throw), a rod overlay (a curved line from the hand) and a line arcing out with a small ease, 0.5 s; plop and ring ripples where the bobber lands.
- **Wait:** the bobber (red and white float, lava: a glowing obsidian float with a flame tip) bobs 1 px up and down, the line sags, slow ripple rings every 1.4 s, a faint lava glow and ember sparks in lava. Other players see your bobber and line (`fishing: {x, y, state}` in the player view, no deadline).
- **Bite:** the bobber plunges, a splash and droplets, a gold exclamation mark above it, a ring that drains over the window, a bite sound, and the key hint `Keys.label('fish')` pulses under the hero. On touch the Cast button becomes a big **Hook!** button.
- **Hook and reel:** the rod flexes, the line goes taut, the fish arcs out of the water toward the hero, 0.6 s; lava fish leave a short fire trail.
- **Result:** a catch card (icon, name, `ca` weight, rarity colour) above the hero for 3 s and one system line. Legendary: screen-edge glow, fanfare, `announce`. Miss: the bobber sinks and "It got away." in the error stack, with a small splash.
- Honours reduced motion (the tests run with it): fewer ripples, no screen glow.
- **Key map:** new action `fish` in `client/keymap.js` (check `Keys.holders` for a free default code before choosing; two keys per action). Text names it as `‹fish›`, never a letter.
- **Touch:** a contextual button next to the skills when facing a shore with a rod (hidden otherwise), not an always-on slot.
- **Sound:** cast whoosh, plop, bite splash, reel click, catch jingle, legendary fanfare, lava bubble. Through `sfxOut(c)`; pick the generator from the existing `sfx_*.mp3` pipeline.
- **Music:** none.

## Art to make
- **Icons (48x48):** about 60 fish, 8 junk/treasure, 8 rods, 16 dishes, rod charm, coffer, bottle = ~95. PixelFlow procedural, one art style and a contact sheet to judge before wiring (judge on the in-game screenshot, not the sheet). Rarity gets the usual colour border, not different art.
- **Fisher NPC:** one new player-style design in `scripts/npcp_general.py` (`npcp_fisher`, PixelFlow prefix `valhallasc_npcp_`) with hat, vest and rod; assignment via `assign_all_npc_art.py`.
- **Overlay art:** procedural canvas (rod, line, bobber, ripples, splash, catch card). No PixelFlow.
- A tiny bobber skin set as an achievement reward is a stretch goal, saved as a Prefs-free `Character.cosmetics` string (not in the first build).

## Server and data layout
- `server/src/world/fishing.rs` (+ `fishing_tests.rs`): state machine `Idle -> Cast -> Waiting -> Bite -> Done`, `Player.fishing`, one `fish` client op, events `fish_cast`, `fish_bite`, `fish_catch`, `fish_miss`. A new key in the big snapshot `json!` breaks `cargo test` (recursion limit): add `view["fishing"]` after it, and strip the deadline for others in `filter_view` (`OWN_ONLY`).
- `world/fish.txt` (species, habitats), `world/rods.txt`, `world/fishing-spots.txt`: JSON in `.txt` (Apache blocks `.json`), embedded in the binary like the others, so a world-data change needs a server release.
- Items through `scripts/fish_catalog.py`; fish items are `kind: "fish"` (new kind: `items::is_*` helpers, the shop, "sell junk", trade, bank, mail, `bring_have` and tooltips must learn it). Counts in catalogue tests are derived, never literal.
- Save: `Character.fishing` only, `#[serde(default)]`. No rod or spot state is saved. Saves are one-way migrations: nothing here changes an old character.
- Swedish by hand (`docs/swedish-glossary.md`): every UI line, fish names, rods, Fisher dialogue. A Rust `format!` is harvested: keep generated phrases static.
- Version: a bigger feature, so the middle number: label `1.1.0` plus a release note (New/Changed, plain English, no words "server" or "rust").

## Rollout
1. **Vertical slice: Greenmeadow pier + Crags lava** (one water, one lava, Twig and Emberline rods, 10 fish, the full press loop). Proves the loop, the overlay, both habitats and the lava rules.
2. Rods, cooking and the Fisher NPCs for all hubs, then all habitats and fish.
3. Log window, achievements, quests, announcements.
4. Art polish and sound pass, Swedish, release.

## Traps to remember
- Never fish into a hostile aggro bubble: damage cancels the line; fishing never counts as safe (no sanctuary side effects).
- Lava must be reachable only as a **shore** (the existing collision keeps heroes out), and lava damage rules in Crags/Emberwake stay as they are. A lava catch never moves the hero.
- A shaped zone regenerates: spots are an overlay run after `zone_shapes.py apply`, and a zone redesign must re-run it (add it to the sync-world chain and a test that fails when a spot is not on foot-reachable shore).
- Bring/quest paths: `Quest::sync_bring` and `take_bring` must see `kind: "fish"` as material.
- The best-rod pick must prefer a matching habitat (lava vs water), not just the highest tier.
- Each bite is one server clock deadline: assert it with a frozen clock, never a sleep; the browser test drives `window.pako`-free packets like the other suites.

## FISH-DATA implementation (2026-11-19)

- Existing IDs are retained: 57 species, six water rods and two lava rods. Species now own their name, rarity, sale price, minimum tier, weight range, raw heal, level and future cooked-dish ID in `world/fish.txt`; rods own their catalogue details in `world/rods.txt`.
- `scripts/fish_catalog.py` regenerates their inventory definitions and ten shared junk/treasure entries from `world/fishing-loot.txt`. It preserves every unrelated item and its order. Sixteen dish IDs are reserved here; dishes and Fisher cooking offers are built by FISH-RODS. Coffer/bottle/purse use actions and the charm crafting discount still need their later service implementation; they are collectible/tradeable loot in this data slice.
- `scripts/fishing_spots.py --write` runs after the finished shapes and generates candidate waters with a reachable shore/facing witness. The half-tile flood uses expanded real obstacle footprints, including point obstacles, and checks the spawn-connected component. Both bobber and shore stay 18+ tiles from full seam borders and 10+ from hub rectangles. It does not add, move or remove scenery, NPCs, quests or monsters.
- The live game picks random active locations from that candidate pool. Only `snapshot.fishingSpots` contains active rich spots; renderers must never draw the whole candidate pool from `WORLD_MAP.fishingSpots`. A spot yields 5–10 fish across all players, then relocates; junk/treasure and rebirth extra copies never spend additional fish. A line whose spot was depleted by another angler loses the rich rarity bonus. Each spot reserves an alternate location clear of the other spots so sparse waters can always replace a depleted spot. Candidates are not replenished by reconnects.
- Fish and rods remain stackable bag items, never equipment. Raw fish share the 30-second meal timer with food, and their small catalogue heal does not receive the ordinary meal's 40%-max-HP floor. Fish can be sold, banked, mailed, traded and handed in through ordinary bring quests. Sell all junk preserves fish; selling rare or legendary fish requests confirmation.
- The public fishing controls, ripple rendering, icons, cooking NPCs and achievements remain separate tasks. No release or version bump is part of this data slice.

### FISH-DATA verification (2026-11-19)

- `cargo test fishing_ -- --test-threads=1`: all 13 focused tests passed. These cover actual collision/casts at every candidate, all-zone spot replacement, 5–10-fish depletion, rebirth copies, lava junk, treasure, raw fish meals, bring quests, bank, mail, trade and the existing server core.
- `python3 tests/fishing-spots.py`: three checks passed, including two byte-identical generations, catalogue preservation and the flood/seam/hub checks. There are 644 candidate waters across twelve zones; active locations are selected randomly at runtime. Removing catalogue classification or clearance failed its mutation check.
- `node tests/fishing-data-client.cjs` passed. The pre-change inventory, fish-as-junk and missing rare-sale-confirmation mutations each failed. `node tests/swedish-locale.cjs` passed 23 checks; Swedish freshness and changed JavaScript syntax checks passed.
- The full world sync completed. Its known unrelated cathedral and mailbox output was restored. An audit against the branch baseline found no map changes outside `fishingSpots` and no changed unrelated item definitions; original catalogue order is retained.
- The private `--profile test` executable passed `tests/fishing-core.cjs`: 30 snapshots in 2.896 seconds, tick gaps of two, Copper Mackerel caught and stored, inventory preserved after reconnect. No production database was used.
- Strict Clippy reports two existing baseline issues: unused `Store::mail_unread` and `clippy::doc_lazy_continuation` in `world/quest_drops.rs`. The executable check passed with only those categories excluded (`-D warnings -A dead_code -A clippy::doc_lazy_continuation`).
- The designated cloud box timed out over SSH, so browser validation there remains unavailable. The existing cleanup wiki confirms it was removed on 2026-11-18; its runner instructions are obsolete. This is feature-branch work in `/media/raid/valhallasc-data/fishing-core` on `feat/fishing-core`, not a public release. Next task: FISH-RODS.


## FISH-RODS implementation (2026-11-19)

The owner confirmed one waterside Fisher per fishing zone, plus Alderhaven and Saltby (2026-11-19). The feature branch now has 13 Fisher service NPCs: one near a reachable water/lava shore in each fishing zone, plus the Alderhaven seller (Saltby is Greenmeadow's waterside Fisher). A hub without nearby water is served by the Fisher at the nearest safe shore; the overlay does not create water or move any existing content. `scripts/fisher_npcs.py` runs after shapes and fishing spots, assigns the existing player-style `fisher` atlas, and adds three chained bring quests plus one freely repeatable creel quest per Fisher (52 quests). The creel is not limited by the calendar. Every quest uses ordinary fish stacks, with XP from its recommended level in `levels.txt`.

`world/fishing-workshop.txt` owns seven upgrade recipes and cooking for all 57 species. Recipe IDs are `rod:2` through `rod:6`, `rod:emberline`, `rod:magma`, and `cook:<fish item>`. Upgrade costs are one previous rod, five accessible common fish, one ordinary local material and copper. Emberline consumes a Twig Rod and shore fish, so it can be made before the first lava cast; buy another Twig Rod if you also want to keep fishing in water. A carried Rod Charm automatically replaces one of the five fish and is consumed only by a successful craft. Twig Rod costs **50 copper** (`cost: 50`, the existing numeric design price; all stored `gold` amounts are copper, see `docs/money.md`). Recipe costs, ingredients and the charm are displayed before purchase.

The workshop validates the actual NPC offer, zone, level, gold, ingredients, bag capacity after consuming ingredients, and that the hero is alive, unmounted, out of combat/trade/PvP/cutscenes and free to act. It applies the transaction to a clone and commits once. Repeated or forged requests cannot obtain a recipe without its costs. The dialogue returns current recipe quotes alongside the ordinary inventory and purse; the server owns every price. Opening the workshop sets shop presence so fishing is blocked while it is open, and closing/back clears it. A completed service cancels any active line. Rod selection already prefers the highest usable rod of the matching habitat; a focused regression covers mixed water/lava bags and required levels.

`consumable_tiers.fishing_dishes` generates the 16 reserved dish IDs via the fishing catalogue. Each is ordinary food, restores health/resource, improves on every raw fish used by its recipe and uses the shared 30-second meal timer. No new equipment slot or save field is needed. Existing fish/rod IDs and the 57-species roster are unchanged. The workshop and all new names, dialogue, quests and errors have hand-written Swedish.

This is FISH-RODS only. Casting controls, fishing animation/log UI, new icons/sounds, achievements, treasure use actions and public release remain later tasks. There is no version bump or deployment in this slice.


### FISH-RODS verification (2026-11-19)

- `cargo test fishing_ -- --test-threads=1`: 20 passed. Seven new workshop/rod tests cover all upgrade recipes, exact payment, failed operations, full bags that do/do not free ingredient cells, the charm, cooking's shared timer, every real Fisher quest hand-in/repeat and best matching usable rods. The three adjusted Lapis/Tanglecrown/Yearwheel content fixtures also pass.
- The deliberate missing-transaction and wrong-habitat mutations fail the intended tests (five failures, two passes); the original source was restored and all 20 fishing tests passed again.
- `tests/fishing-workshop.py` (two) and `tests/fishing-spots.py` (three) pass. Suppressing the Fisher overlay and serving the pre-dish catalogue both fail their new assertions. Full sync-world completed; its known cathedral manifest/mailbox output and unrelated item reordering were restored. Cross-zone comparison proves existing map content, item values and catalogue order are unchanged; only Fishers/quests and 16 dishes are added.
- `tests/npc-assignment.cjs` covers all 601 people, including 13 Fishers, with original identities preserved. The quote-rendering and existing fishing-data client checks pass. Swedish freshness and all 23 locale checks pass; changed JavaScript/Python syntax and scoped Rust formatting are checked.
- `tests/fishing-workshop.cjs` passes against a private optimized executable and disposable database: Twig purchase, forged recipe at the smith rejected with costs intact, crafting/cooking and full inventory/purse persistence after reconnect. The private probe received 30 snapshots in **2.896 seconds**, tick gaps of two.
- Bounded `tests/fishing-workshop-ui.cjs` passes buying the Twig Rod, missing-input controls, crafting, cooking, updated costs, retained workshop/back/close, and landscape phone layouts at 844×390 and 600×390. The corrected check requires visible, uncovered recipe buttons; portrait correctly shows the existing rotation cover. Its pre-workshop `city.js` mutation fails. Desktop/phone/NPC screenshots were inspected.
- Strict all-target Clippy reports existing dead-code helpers/`Store::mail_unread`, `quest_drops.rs` doc continuation and the single-element loop in `quest_journal_tests.rs`; those files/diagnostics predate this task. All-target Clippy passes with only `dead_code`, `clippy::doc_lazy_continuation` and `clippy::single_element_loop` excluded. No source lint suppressions were added.

Browser/protocol checks in this worktree use `NODE_PATH=/media/raid/valhallasc-data/valhalla-dev/node_modules:/home/serveperry/webserver/www/dybase2/node_modules`, the existing Playwright cache, and an absolute `VALHALLA_BINARY` for the feature worktree's `target/debug/valhalla-server` built with `--profile test`. The cloud box is retired. Implementation is on `feat/fishing-core`; no public release, version bump, service restart or production database change. Next task: **FISH-LAVA**.


## FISH-LAVA implementation (2026-11-19)

Lava fishing is complete on `feat/fishing-core`, without a public release. The previous core/data/rod slices already supplied both lava surfaces, matching rods, eight lava species and the lava junk table. This slice closes the shore-validation gap and verifies that content through actual casts and catches. There are still 57 species and eight rod IDs; no map, catalogue, recipe, scenery, monster, movement, damage or rendering data changed.

`landing` now tests the hero's full collision footprint on a copy of their position. A centre outside the lava is insufficient when the hero's feet overlap it; a blocked shore is also refused. Validation never pushes or teleports the hero. This shore requirement also applies to ordinary water. The existing error text and Swedish remain valid.

- Emberline (level 5, lava tier 1) fishes the Crags; Magma Reel (level 45, lava tier 2) fishes both lava zones and is required in Emberwake. The best matching usable rod wins, even with a higher-tier water rod in the bags. Lava rods do not fish water, and water rods do not fish lava.
- Phoenix Koi stays exclusive to the Crags, Sunfire Ray to Emberwake. Species minimum tiers, weight bounds, rarity, collection records and rebirth copies use the existing catch path. Cooled Slag and Charred Branch are lava junk; water junk cannot leak into lava catches.
- All 128 authored lava shore witnesses (64 per zone) work through `fish_press`, without moving or hurting the angler. Existing collision still blocks a walk into the pool. Overlapping circles use an iterative solver: the movement assertion allows 0.001 tile of numerical overlap in the expanded collision radius (the existing worst witness, `fish_45_56`, differs by about 0.00011 tile). It still excludes entry into the liquid itself. The old `(18,303)` example predates the shaped map; tests derive shores and facing from current candidate data instead.
- Active lava rich spots spend one fish per successful hook regardless of rebirth copies; junk spends none. Taking damage cancels the line without a catch or spot depletion. Existing five-to-ten-fish depletion and relocation checks remain in the focused fishing suite.

### FISH-LAVA verification

- `cargo test fishing_ -- --test-threads=1`: **25 passed**, including five new lava tests in `server/src/world/fishing_lava_tests.rs`.
- `python3 tests/fishing-lava-mutations.py`: **eight independent mutations caught** (shore footprint, matching rods, liquid surfaces, species zone/tier filters, lava junk, public lava flag, rich-spot spending and damage cancellation). The runner requires exclusive worktree access, builds one temporary instrumented test executable, checks an unmutated control and restores the source in `finally`. Rebuild clean binaries afterward.
- `python3 tests/fishing-spots.py`: all three checks pass, including spawn-connected shore reachability and two identical candidate generations. Map, fish, rods, spot data and the lava rendering files are byte-identical to the pre-task commit.
- `tests/fishing-lava.cjs` against a clean private optimized executable and disposable database: real casts and catches in both zones; high-tier water rod rejected in lava, Emberline rejected in Emberwake, lava-only bags rejected in water; inventory and collection log survive reconnect. The probe received 30 snapshots in **2.966 seconds**, with tick gaps of two, while a lava line was active.
- Swedish freshness, changed-file syntax and scoped formatting checks pass. Strict Clippy retains the documented baseline dead-code, quest-drop documentation and single-element-loop diagnostics. All-target Clippy passes with only `dead_code`, `clippy::doc_lazy_continuation` and `clippy::single_element_loop` excluded; no lint suppressions were added to source.

`tests/lava-motion-ui.cjs` was not run: the designated browser host was retired and the owner bars browser suites on the production host. The lava renderer and that suite are unchanged. Browser regression validation remains pending for an approved test host under FISH-CHECK. No version bump, release notes, service restart or production database change. Finish record: wiki `10_projects:valhallasc_fishing_lava_20261119`. Next task: **FISH-CLIENT**.

## FISH-META implementation (2026-11-19, feature branch only)

Fishing achievements reconcile from the existing saved fishing log. Per-hook totals
exclude rebirth copies, junk and treasure; collections require distinct caught
species, and the weight goal uses the best recorded weight of a real caught species.
Inventory ownership alone awards nothing. Old saves default to an empty log; prior
fishing catches reconcile once. Existing achievement events, title selection,
snapshots and persistence carry the new rewards without new protocol or save fields.
Hand-written Swedish covers every catalog string and the new Fishing category.
No version bump or deployment: FISH-CLIENT, FISH-ART, FISH-CHECK and FISH-RELEASE
remain separate tasks.


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

## FISH-ART implementation (2026-11-19)

The feature branch now has **91 distinct 48×48 icons**: all 57 species, eight rods,
ten junk/treasure items (including the charm, coffer and bottle), and 16 cooked
dishes. Counts follow the real catalogue rather than the earlier approximate
95-icon brief. Existing species and rod IDs are preserved.

`client/assets/fishing-icons.png` is a separate 13×7 atlas. Its native PixelFlow
sources, frame order, cell lookup and retained first-candidate source IDs live in
`client/assets/fishing-icons.txt`; `client/fishingicons.js` exposes the same lookup.
`Inventory.icon` selects this atlas for fishing items, retaining the existing bag
rarity borders. Equipment's original atlas and other icons are unchanged. Fish
have cel shading, dark outlines, habitat colours and authored body/fin/pattern
choices; eels, rays, catfish, gar, crownfin, dragonfish and sturgeon have distinct
features. Rods include line, float and reel; dishes have habitat garnish.

The new `fisher_rod` player-style design has a straw hat, leather vest, pockets,
rod, reel and hanging float. It is additive: the older fish-carrying `fisher`
source and all 318 earlier looks remain unchanged. `fisher_npcs.assign_art`, also
called by `assign_all_npc_art.py`, assigns the new look to all 13 fishing NPCs,
keeping their individual colours, identities and gameplay. The library now has
319 looks. Its PixelFlow source is `031e3fed395b7b5b`, with six idle, eight walk
and six talk frames; the export is `client/assets/npcp_fisher_rod.png`.

The seven effects are `assets/sfx_fish_{cast,plop,bite,reel,catch,legendary,lava}.mp3`.
They use the established boss-cue dybase2/export recipe: mono 44.1 kHz MP3 at
96 kbps, 25 Hz high-pass, independent peak normalization and short edge fades.
All cues were authored in the new editable dybase2 project
[`2e46dfdfb98c6923`](https://gunning.se/dybase2/?project=2e46dfdfb98c6923).
Sork-60 supplies noise/water, resonant bubbles and the two short catch stingers;
Dexed MARIMBA supplies the reel clicks. No existing score/project was edited.
`fishing-sounds.txt` records each cue's source bar, duration and final checksum.
Decoded duration, levels and clipping were checked; direct listening was not
available, so these checks do not claim an auditory sign-off.

### Reproduce or preserve editor changes

```sh
python3 scripts/make_fishing_art.py preview
python3 scripts/make_fishing_art.py build
python3 scripts/make_fishing_art.py export
python3 scripts/make_fishing_art.py verify
python3 scripts/make_npcp_sprites.py verify fisher_rod
sh scripts/create_fishing_sounds.sh --render
python3 scripts/export_fishing_sounds.py
```

`build` preserves registered PixelFlow work. `export` reads the actual saved
frames, including later editor changes; no local-render bypass is provided.
PixelFlow permits at most 64 frames per source, so fish and tackle use separate
saves. The first candidate is retained in `sourceHistory`; the final source IDs
are `65ccf93e7d5b859c` (fish) and `79022f15d7d351fb` (tackle).
The sound script reopens its saved project and renders it without rewriting its
notes or presets. The exporter splits its two-bar-spaced cue markers at 120 BPM.

### Focused verification

- `python3 tests/fishing-art.py`: all 91 unique cells and transparent margins,
  unchanged earlier NPC metadata, stable assignments, all 20 new poses,
  grounded feet, and seven finite, audible, unclipped mono MP3 decodes pass.
- `make_fishing_art.py verify` and `make_npcp_sprites.py verify fisher_rod`:
  all 91 icon frames and all 20 NPC frames match their saved editor pixels.
- `tests/npc-assignment.cjs`: 601/601 actual people are assigned; original
  identities are preserved. Its look count rises from 318 to 319 because the
  rod-carrying Fisher is an additional saved design.
- Bounded `tests/fishing-art-ui.cjs`: 91 icons use the production inventory
  renderer, 13 Fishers × 20 poses use the new player-style bank with head sockets,
  all seven MP3s decode in Chromium, and the actual bags/workshop/scene pass.
  Screenshots in `test-results/driver-lQND3l/` were visually inspected.
- `MUTATE=icons|npc|sound` fails separately in both the asset and browser tests.
  Browser mutations serve the pre-art inventory from `a1764688`, remove the new
  Fisher from the served manifest, or serve a corrupt plop file. None edits the
  worktree or the production game. The missing-style assertion runs before image
  readiness so a missing new source fails directly rather than timing out.
- Swedish freshness, changed Python/JavaScript/shell syntax and `git diff --check`
  pass. Only these affected checks ran, on the local bounded private runner;
  the retired cloud host was not used. No combat or balance suites ran.
- **Host-policy correction recorded at finish:** these browser runs happened on
  the shared host despite the canonical restriction against browser suites here.
  The assistant missed that rule and disclosed the mistake. Caps did not grant
  an exception. The results above describe the runs that occurred; further
  browser validation requires an approved replacement host. Existing pending
  lava-motion and achievement browser checks remain pending.

### Handoff to FISH-CLIENT

The bag/workshop item-icon helper and Fisher assignments are already connected.
The seven sound assets are ready; their playback and event timing belong to
FISH-CLIENT. Route sources through `sfxOut(c)`, honour Sound/SFX preferences,
play plop when the cast lands, bite on `fish_bite`, reel during the hook, and the
catch/legendary cue when the catch card appears (avoid double celebration cues).
The client catch card and collection log can use `Inventory.icon(item)` to share
the same art. The bobber, line, cast arc and splash remain procedural overlays.

This work is private and has no version bump or release note; those belong to
FISH-RELEASE. No world data, saved characters, production DB, running binary or
live release link changed. Nothing was uploaded to FileDrop.

## FISH-CLIENT implementation (2026-11-19, feature branch only)

The fishing client is implemented in `client/fishing.js`, with Field hooks in the
ground and foreground passes. It draws cast arcs, rods/lines, water and ember
bobbers, wait ripples, bite splashes and a draining server-clock ring, reel/fish
arcs, miss ripples and three-second catch cards. Other players' public lines are
drawn from their snapshots. Rich ripples use **only active `snapshot.fishingSpots`**;
the map's candidate pool is never drawn. Low graphics and reduced motion simplify
the effects and suppress the legendary edge glow.

The new `fish` action defaults to **R**, verified free with `Keys.holders`, and is
rebindable in Keyboard settings. Held-key repeat and text entry cannot cast.
Every fresh press sends only `{type:"fish"}`; the world owns eligibility, timing,
loot and records. Touch uses one contextual Cast/Hook button beside the skills,
with pointerdown activation and synthetic-click suppression. Shore visibility
checks matching usable rods and the facing ray against pools or Saltby's dock
sea mask; it is a cached UI hint, with authoritative validation unchanged.

**World Menu → Fishing log** opens the resizable collection window. It lists all
57 species with silhouettes until caught, filters by habitat, and shows saved
catch totals, legendary catches, longest streaks and per-species counts/best
weights. Habitat option values remain English IDs when their labels translate.
Catch cards and the log reuse `Inventory.icon`. All new UI text is hand-written
in Swedish. Catch events add one rarity-marked System line; misses use the red
error stack. Reconnect/character changes clear private UI and pending effects.

All seven existing recorded cues play through `sfxOut(c)` and honour Sound/SFX
preferences. Plop plays at landing, bite on the event, reel before the card, then
one ordinary catch **or** legendary celebration. Decoded audio is cached; muted,
late and out-of-game requests do not play obsolete cues.

Two small presentation protocol additions complete the UI: `snapshot.fishingTime`
shares the Unix clock used by private bite deadlines, and a legendary hook emits
one `announce`/`treasure` packet to its zone. The announcement carries its actor
so existing hidden-GM filtering applies. Ordinary catches, junk, treasure and
rebirth extra copies do not create additional legendary announcements.

### FISH-CLIENT verification

- `node tests/fishing-client.cjs`: **717 behavioural checks**, including all 644
  authored shore witnesses, the real Field key/action routing and touch handlers,
  key rebinding/repeat/typing guards, active-point rendering/depletion, other
  players' bobbers, server-clock countdown, reel/card timing, record filters,
  silhouettes, cleanup, reduced motion, System lines, real Swedish translation
  and recorded-audio bus/mute/cache/latency handling. Catch cards stay inside
  phone screen edges after converting between scene and CSS pixels.
- Its nine in-memory `MUTATE=input|spots|records|deadline|privacy|cleanup|sound|cardX|cardY`
  controls fail their intended behavioural assertions; they remain effective
  after committing because they mutate the current implementation directly.
- Three focused Rust checks pass for the Unix clock, one legendary announcement
  (ordinary/junk catches excluded, rebirth copies counted once), zone delivery,
  hidden actors and private catch events. `tests/fishing-client-mutations.py`
  catches four independent protocol mutations (clock, missing announcement,
  ordinary announcement and wrong zone). Source is restored in `finally`;
  clean focused tests and a private executable rebuild pass afterwards. The
  runner requires exclusive worktree access.
- `tests/fishing-client-probe.cjs` drives the actual client controller with real
  WebSocket packets from a disposable private server/DB: cast, public bobber,
  private deadline/result, hook, reel/card/sound order, bag award and reconnect
  persistence pass. **30 snapshots in 2.915 seconds**, tick gaps of two. No loot
  grinding or encounter/balance testing.
- Swedish freshness, the catalogue gate and 23 existing locale checks pass.
  Changed JS/Python syntax and diff whitespace pass. Strict all-target Clippy
  reports only the documented baseline: `mail_unread`, hosted-count helpers,
  quest-drop documentation indentation and the quest-journal single-element
  loop. No source lint suppressions were added.
- Browser coverage is prepared in `tests/fishing-ui.cjs` for actual keyboard and
  touch casting, catch cards, early misses, collection/filter UI and landscape
  phone layout. **It has not run:** the approved cloud host was retired and the
  owner bars browser suites on this production host. Its disabled-feature
  `MUTATE=1` control and visual review remain for an approved replacement host
  under **FISH-CHECK**, alongside the existing lava-motion/achievement checks.

This slice does not change the 57 species, eight rods, art assets, world data or
achievement catalogue. It has no version bump, release note, public deployment,
service restart or production database change. **FISH-CHECK and FISH-RELEASE remain
open.** Release/version work belongs to FISH-RELEASE.


## FISH-CHECK verification (2026-11-19)

The owner explicitly approved bounded browser checks on this host for FISH-CHECK.
Every browser suite ran sequentially with the existing 1.5 GiB memory limit,
no swap, one CPU and ten-minute timeout. This is a task-specific exception to
the default host policy, not permission for later browser work.

- All **34** `cargo test fishing_ -- --test-threads=1` checks pass. No world
  generators or combat/balance suites ran; the 57 species and eight rods remain.
- All three `tests/fishing-spots.py` checks pass, including 644 reachable shore
  witnesses and byte-identical candidate generation. `tests/fishing-client.cjs`
  passes **719** checks; its new `MUTATE=hint` fails the intended key-hint assertion.
- New MCP scenario **fishing** is last in the scenario catalogue. The actual
  MCP SDK handshake runs **17 assertions** covering early miss, pier hook,
  Unix clock, active rich points, public bobber/private deadline and result,
  bag award, record evidence, dry-shore health/position, water/lava rod isolation,
  and inventory/log persistence across a SQLite-backed executable restart.
  `tests/fishing-check-mutations.cjs` catches missing fishing inputs, a zero
  clock, serving the candidate pool, a leaked private deadline and lost inventory
  after restart. Mutations alter test-process transport data in memory only.
  The affected MCP lifecycle/catalogue test passes with its ordered list updated.
- Bounded `tests/fishing-ui.cjs` passes real keyboard cast/hook, touch cast/early
  miss, catch card, records/filter, initial and rebound key hints, reduced-motion
  glow suppression and 844x390 layout. Screenshots were inspected.
  `MUTATE=1` disables the actual fishing module and fails its direct assertion.
- Bounded `tests/lava-motion-ui.cjs` passes **18** assertions, including visible
  and changing lava, zero reduced-motion deltas, footprint containment, camera
  anchoring and sparse bubbles in Emberwake and the Chained Forge. The disabled
  motion mutation fails the actual-field pixel assertion. The presentation clock
  is frozen within each pair: new rich-spot ripples otherwise move between the
  off/on frames and contaminate the comparison. Thresholds are unchanged; clean
  full-frame maximum deltas are 25 (Emberwake) and 21 (Forge), below the same 100.
- All **136** achievement/category/title browser checks and their category mutation pass.
  These UI checks use the existing placeholder-sprite mode; a full-art run hit
  the 1536 MiB cap while opening its second character page. No cap was raised.
  The fishing UI and lava scene checks above use real sprites.
- The complete **`npm run test:swedish`** passed before the rich-spot follow-up inside the same bounded scope,
  including freshness, catalogue, locale, language switching and window layout.
- Strict all-target Clippy reports only the documented existing `dead_code`
  helpers/`mail_unread`, `doc_lazy_continuation` and `single_element_loop` issues.
  All-target Clippy passes with only those three categories excluded. No source
  lint suppressions or unrelated Rust fixes were added. Changed JavaScript syntax
  and `git diff --check` pass.

The real UI exposed an unresolved initial `‹fish›` token in the collection log.
`fishing.js` now resolves the bound key when the module loads and after rebinding;
unit/browser checks verify R initially and V after a real keymap rebind. Facing
setup in the browser fixture resets to the pier after its directional input:
real-art frame stalls under the cap must not extend that setup into a long walk.
Affected MCP/Swedish launchers preserve the shared worktree's environment.
The token replacement uses a regular expression: a standalone quoted key token
is otherwise harvested as untranslated player text by the Swedish build.

### Rich-spot feedback found during manual testing

The owner could see ordinary pond ripples, but could not identify rich points or
observe depletion. A short observation of the separate manual server found their
bobber **12.54 tiles** from the nearest active point, outside the authoritative
three-tile bonus radius. Those were ordinary-water catches. There was also a real
rendering defect: the rich ground pass ran before `drawWater`, so Greenmeadow's
ponds painted over its markers. The ground pass now follows painted water and
flat liquid objects, while staying below people.

Active snapshot points now have a gold fish silhouette and **Rich fishing spot**
label, plus a viewport-clamped hover tooltip explaining rarity chances and
5–10-fish depletion. The angler's line says **Rich fishing spot** or **Ordinary
fishing water**. Rich status remembers the point at cast time and loses its bonus
indicator when that point disappears; a later spawn cannot upgrade an ordinary
line. These are presentation changes using existing authoritative snapshots;
the fishing rules, depletion count and rarity tables are unchanged. Swedish is
hand-written. No test-server restart was needed; reload the test page.

`tests/fishing-rich-client.cjs` passes 15 behaviour assertions and five mutations
(hit area, marker, current-line status, stale/depleted status, tooltip). The new
bounded real-art `tests/fishing-rich-ui.cjs` verifies actual marker pixels above
painted pond water, mouse hover and an actual rich cast. Restoring the old layer
order fails the centre-marker pixel assertion; disabling hover fails its tooltip
assertion. Before/after screenshots were inspected. No catches were ground for
this regression; existing focused Rust depletion checks cover the shared budget.

### Manual fishing server

**https://gunning.se/ValhallaFishing/** is left running as the separate transient
user service `valhalla-fishing-test.service` on `172.18.0.1:8082`. It serves this
feature branch's client and a separate copy of its clean optimized test binary.
Its private database is
`/home/serveperry/webserver/www/Valhalla/fishing-test/valhalla.sqlite`: a consistent
read-only backup of the public database. The two copied characters retain their
levels/progression, start at the Saltby pier, and have all eight rods, four large
bags and at least 1,000,000 copper. God mode/test commands are enabled; new
characters start at 99. Log in with the usual account. Rods stay in bags; face
water, press R, wait for Hook!, press R again. Touch uses Cast/Hook!

The test server passes HTTPS health, exact client-byte comparison, WebSocket
upgrade, executable comparison and SQLite `quick_check`. The public service's
PID remains 1849; its database/client release/binary were not changed or
restarted. Apache was validated and gracefully reloaded for the separate route.
The local `fishing-test/README.md`, `start.py` and `receipt.json` retain the paths,
recreation and stop commands. The transient service lasts until stopped/rebooted;
the starter preserves its existing database. A normal later client release
replaces the Apache include, so retain/remove the test route deliberately then.

FISH-CHECK is complete. After the owner resumed work, the final post-rich-fix lava and full Swedish browser reruns passed. Lava uses `VW=960 VH=600` and the cached headless shell to reduce its rendering footprint; the 1.5 GiB/no-swap/one-CPU limits and all 18 assertions/thresholds remain unchanged. `tests/lava-motion-ui.cjs` retains its normal viewport by default and now accepts the explicit override. Rich-spot mutation checks use placeholder character sprites while preserving the actual painted pond; the normal rich-spot scene/hover/cast run used real character art. FISH-RELEASE remains pending.

No version bump, release notes, live release link
swap, production game restart, world sync or FileDrop upload belongs to this check.
