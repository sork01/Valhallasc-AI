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

Each cast needs a fresh press. Missing or interrupting a cast clears the current catch streak. Five timing misses display the doze-off message and reset the miss counter. A successful hook counts once for the collection and awards the rebirth-adjusted stack. Only the owner receives the Unix-seconds bite deadline. The public player snapshot supplies bobber position and phase. Rich spots are map points in `fishingSpots` with a three-tile radius. The data overlay, junk and treasure, cooking, Fisher quests and player controls belong to later backlog tasks.

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
- **Rich spots** ("ripples"): 4 to 8 per fishing zone, drawn as a ring of ripples, found by `scripts/fishing_spots.py --write` as an overlay (`world/fishing-spots.txt`, shipped by sync-world, run **after** `zone_shapes.py apply`, flood-checked to be reachable on foot, 18+ tiles off seams, 10+ tiles from hubs). A rich spot has `x3` rare weight, `x0.75` wait and its own spot fish.
- The worldwide rule from the shaped-world work holds: nothing pops in on entering a zone, so spots are static map data, not random spawns.

## Rods
Item kind `rod` (not a worn slot: the best rod in the bags is used; a tenth-slot-style change like cloaks is not worth it). Data `world/rods.txt`, items by `scripts/fish_catalog.py` (idempotent overlay run by sync-world after `gear_levels.py`, like `cloak_catalog.py`).

| Tier | Rod | Level | Source | Reaches |
| --- | --- | --- | --- | --- |
| 1 | Twig Rod | 1 | vendor in Alderhaven, 50 gold | sea shore, Gloamfen, Rimeveil commons |
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
- **Achievements:** about 12 new (first catch, 100/1000 fish, each habitat log complete, first legendary, lava angler, record weights) and 2-3 titles ("the Angler", "Lavacaster"). `achievements.rs` is pinned at 107 / 2325 points / 10 titles / 11 mounts: update those expectations in the same commit.
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
