# Gear durability and repair

Owner, 2026-10-22: "remove exp penalty when dying. introduce gear durability and repair instead". A death used to take a third of the
current level's XP (`Character::lose_death_xp`, removed). It now wears the gear you wear, and a smith repairs it for gold.
Decisions were made in two rounds on 2026-10-22 (recorded in TODO.md under `DEATH-RULES`).

## Rules

- **Only dying wears gear.** Blows taken or dealt wear nothing. Duels and the Arena (and its gauntlet) cost nothing, as they
  cost no XP before: they never reach `Player::apply_death_penalty`, which has three callers (`hurt_player_by`, the boss
  mechanic kill and the debug `die`).
- **One death takes 10% of the maximum from every worn piece**, whatever its level or rarity (`WEAR_PER_DEATH`). Ten deaths
  in a row break a full set. A piece that is already broken stays broken and counts nothing more.
- **Full stats at any durability above 0, zero stats at 0.** A cliff, not a scale. A broken piece stays worn and is never lost,
  destroyed or unequippable. Broken means no attack, no defense, no attribute bonus and no credit towards a set bonus
  (`Character::stats`, `gear_attributes`, `set_counts`).
- **Every worn slot wears**: weapon, armor, headgear, shoulders, gloves, pants, necklace, both accessories and the cloak,
  every rarity including orange and class-neutral. **Starter and game master gear never wear** (`Item.starter`,
  rarity `gm`).
- **Mercenaries and ambient adventurers have no durability.** Only the hirer's own gear wears. The kill-time and boss harnesses
  build a fresh `World` per fight, so wear cannot carry from one fight to the next; no switch turns wear off, so a fixture that
  keeps its non-mercenary hirer through ten deaths inside one fight would see broken gear (not seen; the `HirerRole::Down`
  fixture sets hp directly and never reaches the death rule). Add an opt-out only if a measurement shows it.
- **Condition travels with the copy.** The bank and a trade keep the wear. **Merge and refine restore the result to full.**
- **Saved characters need no migration**: the field is `wear` (0 = new, 100 = broken, `#[serde(default)]`), so an old copy
  loads at full durability. The client shows durability as `100 - wear` and treats a missing field as full.

## Repair

- **Where**: the smith of each safe hub, offer `repair` (`scripts/add_repair_offers.py`, run after the zone generators and
  before `sync-world.cjs`): Alderhaven `smith` (Bram Emberforge), Skaldholm `city_smith`, Nacrehold `nacre_smith`, Asterion
  `asterion_smith`.
- **How**: the smith's window lists every damaged copy (worn or in the bags) with a Repair button and a Repair all button.
  Offer ids are `repair:<copy id>` and `repair_all`, handled in `World::interact` next to merge and refine; the 0.5 s service
  throttle does not apply. Gold only, not in combat (checked in the world handler, `combat_left`), not mounted, not defeated.
- **Price**: 25% of the piece's catalog sale value (`Item.sell`, a rare piece merged to epic counts twice, as when sold),
  scaled linearly by the missing durability, rounded up, at least 1 gold for a damaged copy
  (`Character::repair_price`). Rebirth gold boosts do not apply. The server quotes every damaged copy in the dialogue packet
  as `repairQuote: [[copy id, price], ...]`; an older server sends none and the client then hides the offer.
- `Character::repair_gear(only)` is one validated function on a cloned character, like merge and refine: all or nothing.

## Death notice

`You died.` (nothing worn lost durability), `Your gear lost durability. Repair it at a smith.` or
`Your gear lost durability. Broken pieces: {n}. Repair them at a smith.` Swedish by hand in `scripts/sv-*.txt`.

## Client

- Tooltip line `Durability N%` (amber, orange below 30%, red `Broken · no stats until repaired`), the copy lines of a gear
  tooltip, and a bar under each worn slot in the character window (`data-condition` on `.equipped-slot`).
- The smith's repair view is `GearServices.render('repair', ...)` in `client/gearservices.js`, opened from the gossip row
  (`client/city.js`).
- The bags button shows an `!` badge (`#inventory-open[data-gear]`, `low` below 30%, `broken` at 0) while any worn piece is
  low or broken: the low-durability hint, with no new HUD piece.
- The Inspect window is not changed (the whitelist packet carries no wear).
- The GM test menu hands out the gauntlet gear sets (`gear_set`: ordinary rarities, not rarity `gm`), so deaths during GM dungeon tests wear and can break that gear; repair it at a smith or hand the set out again.

## Checks

`cargo test` filters `gear_services::tests`, `dying_wears`, `tenth_death`, `mercenaries_and_adventurers`,
`hub_smith_repairs`, `every_hub_smith`; browser check `tests/durability-ui.cjs` (`MUTATE=1` must fail). Mutation: restoring the XP
loss or removing the broken-piece subtraction in `Character::stats` fails the tests.
