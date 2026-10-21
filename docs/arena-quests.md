# Arena gauntlet quests

Owner's request, 2026-10-21. At level 20 and every ten levels after (20, 30, ... 90, and 99) a quest sends the hero into the
Arena (zone 40) to fight five opponents, one per class, one at a time. Winning all five makes the quest ready; handing it in
pays a blue weapon of the hero's class for that level, experience and gold.

## Rules (all decided by the owner on 2026-10-21)

- **Quests:** nine levels (20, 30, 40, 50, 60, 70, 80, 90, 99) at five givers, one in each major safe city: Alderhaven (`guide`),
  Skaldholm (`city_steward`), Nacrehold (`nacre_archivist`), Astralhollow (`astral_steward`), Asterion (`asterion_archon`).
  These are the stewards that already keep the stat reset. Ids are `arena_<alder|skald|nacre|astral|aster>_<level>`
  (`quest:accept:` + id stays within 32 characters). A quest is offered from its level upward (`minLevel`) and never expires.
- **Once per level per character**, whichever giver it came from: accepting another giver's quest of a level the hero already
  took is refused (`Quest::gauntlet_level`, checked in `interact`). The reward is a one-time reward and is handed in where the
  quest was taken.
- **Entering:** the quest's objective is `gauntlet` with the target `L<level>` and the count 5. The giver's `gauntlet` offer
  ("Enter the Arena") starts a run for the lowest accepted arena quest that is neither won nor handed in. The hero must stand at
  the giver, be alive, not hidden, not in a duel, queue or match, and not in another run. The hero is solo: nobody else can enter
  (the only way in is this offer).
- **The ring:** every run takes its own private Arena copy from the same pool as queued matches (`!Instance.active`); when none
  is free the giver says the Arena is full and nothing changes. The hero starts at (9, 16), opponents at (23, 16).
- **Fights:** a 10 s countdown before the first fight and between fights; one opponent at a time, one of each class in a random
  order each run. An opponent is that class at the quest's level (the level of the quest, not the hero's) in plain green
  progression gear (the set of the level rounded down to a multiple of 5; 99 uses the 95 set), attributes spent by
  `allocate_recommended`, no potions, named `Arena <Class>` ("Arena Warrior" and so on) and drawn with the ordinary class art.
- **PvP rules apply**: every blow goes through `pvp_hit` (`PVP_DAMAGE_SCALE` 0.5, the Hunter bonus, stun/root/wound, the Mage's
  ward, the priest's heal scale, the `pvp_fight` lifesteal block). Opponents are driven by the duel matrix's driver
  (`gauntlet_play`: close in, basic blow, `ai_combat_at`). Fights stop at one health like duels: nobody dies, no corpse run, no
  XP loss.
- **After a win** the hero gets full health and mana (stun, root, wound, ward and the basic cooldown cleared; skill cooldowns and
  the potion and meal timers are untouched) and the countdown starts. After the fifth win the hero is back at the giver and the
  quest is ready to hand in.
- **A loss** (the hero reaches one health), **a fight longer than 300 s** (the length of an arena match; the duel matrix's longest decided pair, Priest against Priest at level 30, takes 173 s), leaving (`arena_leave`, logging out) or being moved
  out of the Arena ends the whole run: the opponent is removed, the progress goes back to 0/5, the hero returns to the giver
  with full health and mana, and nothing is paid or lost. The hero retries by talking to a giver again. A run lives in memory
  only; a restart sends a saved hero in an Arena copy to the Greenmeadow spawn, as for matches.
- **Reward:** the blue ordinary weapon of the hero's class at the quest's level (`<class weapon>_l<N>_blue`; level 99 uses the
  level-95 piece), `rewardXp` = `levels.txt[level-1]/10`, and the gold of the hardest solo quest of that level
  (20: 1200, 30: 1200, 40: 2400, 50: 2500, 60: 5000, 70: 9000, 80: 15000, 90: 18000, 99: 30000; table in
  `scripts/arena_quests.py`). The opponents drop no loot, XP or gold.
- **Not tuned:** no win-rate target. PvP balancing is closed (owner, 2026-10-20), so the knobs are the opponents' level and gear
  only. The measured win rates are in the next section.

## Measured win rates (scripted play, no target)

There is no win-rate target (owner, 2026-10-21): this is what the existing duel matrix says, for the owner to react to. An
opponent is built exactly like a duelist of the matrix (the class at the quest's level in plain green progression gear,
`allocate_recommended`, no potions) and driven by the same code, so `docs/duel-report.md` is the measurement. Each cell is
"win rate over a fight against a random class / chance of winning all five fights in a row", for a hero played by the same
scripted brain (the mirror match counts as 50%). Eight duels per pair and level: each cell is about +-17 points.

| Level | Warrior | Mage | Assassin | Priest | Hunter |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 70% / 0% | 10% / 0% | 90% / 50% | 30% / 0% | 50% / 0% |
| 30 | 78% / 19% | 10% / 0% | 82% / 31% | 30% / 0% | 50% / 0% |
| 40 | 88% / 44% | 15% / 0% | 27% / 0% | 70% / 5% | 50% / 0% |
| 50 | 60% / 4% | 45% / 1% | 25% / 0% | 77% / 23% | 42% / 0% |
| 60 | 63% / 0% | 85% / 38% | 42% / 0% | 22% / 0% | 38% / 0% |
| 70 | 55% / 4% | 80% / 29% | 50% / 1% | 45% / 1% | 20% / 0% |
| 80 | 50% / 1% | 70% / 10% | 55% / 0% | 35% / 0% | 40% / 0% |
| 90 | 50% / 1% | 60% / 0% | 48% / 0% | 48% / 2% | 45% / 0% |
| 99 | 65% / 7% | 40% / 0% | 37% / 0% | 55% / 4% | 52% / 1% |

How to read it: scripted play loses outright to at least one class at nearly every level (a Mage or Hunter pass rate of 0% is
a 0% pair cell, not noise), so a run of five is rarely won by a script. A person plays better than the script (kiting, dashes,
potions, picking skills by the situation, the healing between fights is already counted) and the quests ask for exactly that,
but the numbers say the five-fight run is hard for every class. If the owner wants it easier, the knobs are the opponents'
level and gear only (PvP balancing stays closed): for example the previous green set (five levels lower, `green_gear` in
`gauntlet.rs`), or the opponent's level one step below the quest's. To measure a change, run `bash scripts/duel-parallel.sh` with the new opponent setup.

## How it works

- `server/src/world/gauntlet.rs`: `Run` (hero session, quest, level, Arena copy, return point, class order, wins, opponent,
  countdown or fight cap, `fallen`), `gauntlet_interact`/`gauntlet_start`, `update_gauntlets` (once per tick, after
  `update_mercenaries`), `gauntlet_view` (the `gauntlet` field of the `pvp` packet), `gauntlet_abort` (called from `leave` and
  `ArenaLeave`).
- An opponent is a real `Player` with `gauntlet: true` and `merc` set to the hero's character id, like an escort: it is never
  saved, never counted as online and never put in a party. `update_mercenaries` and `mercenaries_of` skip it.
- `pvp_legal` has one new case: the hero and that hero's own opponent in a live run, nobody else. `pvp_hit` floors health at 1
  for the pair and tells the run who fell (`gauntlet_fall`; the hero's fall beats a simultaneous one). `foes_near` no longer
  returns early while a run is live, and `pvp_busy` counts a hero in a run.
- Data: `scripts/arena_quests.py` (run by `sync-world.cjs`, idempotent and byte-stable) writes the quests and the offer into
  `world/map.txt`; never hand-edit them.
- Client: `client/pvp.js` shows the `#gauntlet-banner` (fight n of 5, the next class or the opponent, the countdown or the time
  left, "Leave the gauntlet"), targets the opponent when it appears and lets `canAttack` swing at it. The journal shows
  "Win five Arena fights: n/5".

## Checks

- Rust: `bash scripts/cargo.sh test gauntlet` (data of all 45 quests, a whole run with the reward, lost/timed-out/forfeited/
  logged-out runs, the pair-only legality, private rings, one trial per level, the opponent walking up and fighting, and a
  full green set for every class at all nine levels).
- Browser: `tests/gauntlet-ui.cjs` (refusal and accept at the giver, offer button, banner, countdown, the opponent marked in the
  snapshot, walking up and hitting it with the attack key, forfeit, the turn-in through the gossip window). Needs the
  worktree's `target/debug/valhalla-server` (the MCP launcher drops `VALHALLA_BINARY`), `NODE_PATH` with the dybase2 modules
  and `PLAYWRIGHT_BROWSERS_PATH` with chromium-headless-shell.
- Not done: an MCP scenario (`node scripts/test-via-mcp.cjs run gauntlet`) for levels 20 and 99.
- Swedish: `python3 scripts/build_swedish.py --check`.
