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
  `allocate_recommended`, no potions, **with 70% of the health they would have** (owner, 2026-10-21: "30% easier"), named `Arena <Class>` ("Arena Warrior" and so on) and drawn with the ordinary class art.
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
- **Tuned once:** no win-rate target, but the owner asked for 30% easier after the first measurement (opponent health 70%).
  PvP balancing is closed (owner, 2026-10-20), so the knobs are the opponents' health, level and gear only. The measured win
  rates are in the next section.

## Measured win rates (scripted play, no target)

There is no win-rate target (owner, 2026-10-21): these are numbers for the owner to react to. They come from the gauntlet
itself, not from the duel matrix: `cargo test -- --ignored --nocapture rates_` (the `rates_<level>` tests in
`gauntlet_tests.rs`, `GAUNTLET_SEEDS` runs per class and level, default 6; `GAUNTLET_OPPONENT_HEALTH` sets the opponents'
health without a rebuild) plays whole runs through the real quest code with the hero driven by the mercenaries' brain
(`gauntlet_play`, the same driver as the opponents, no potions, no kiting). Each cell is "chance of winning all five fights /
chance of winning one fight", 6 runs per class and level (30 per level, 54 per class), so a level or class row is about +-9 points.

**First measurement (opponents at full health)**: a whole run was won 3% of the time (7 of 270 runs) and a single fight 47%.
Scripted play lost outright to at least one class at nearly every level. **The owner then asked for it to be 30% easier**
(2026-10-21), done as opponents with 30% less health (`OPPONENT_HEALTH` 0.7 in `gauntlet.rs`: every blow that lands on an
opponent counts for 1 / 0.7 as much; PvP formulas and the opponents' damage are untouched). Measured effect: a whole run
61% (165 of 270) and a single fight 90%. That is a bigger change in win rate than 30%, because a fight is decided by a damage
race. Intermediate values (0.85, 0.9) were not measured.

| | Health 100% (before) | Health 70% (now) |
| --- | ---: | ---: |
| **All 45 cells** | 3% / 47% | 61% / 90% |
| Level 20 | 7% / 50% | 27% / 70% |
| Level 30 | 0% / 36% | 40% / 78% |
| Level 40 | 0% / 44% | 77% / 95% |
| Level 50 | 7% / 58% | 77% / 95% |
| Level 60 | 3% / 44% | 57% / 89% |
| Level 70 | 0% / 46% | 53% / 89% |
| Level 80 | 3% / 50% | 67% / 92% |
| Level 90 | 0% / 43% | 77% / 95% |
| Level 99 | 3% / 46% | 77% / 95% |
| Warrior | 4% / 56% | 76% / 95% |
| Mage | 0% / 29% | 63% / 90% |
| Assassin | 4% / 46% | 43% / 85% |
| Priest | 2% / 44% | 56% / 88% |
| Hunter | 4% / 54% | 69% / 92% |

Scripted play is not a person: kiting, dashes, potions and picking skills by the situation make a real player better, so the
real pass rate is higher. The knobs, if the owner wants to move it again, are `OPPONENT_HEALTH` and the opponents' level and
gear (PvP balancing stays closed).

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
- MCP: `node scripts/test-via-mcp.cjs run gauntlet` (24 checks, ~35 s, mutation-checked). Two heroes, levels 20 and 99, in separate runs at once: accept at the Skaldholm steward, the same level refused from a second giver, the offer, the countdown, the opponent named and marked at the quest's level in a separate ring, a landed basic blow (the driver's new `pvp` action: `attack`, `arena_leave`, `refresh`), leaving (back at the giver, full health, 0 of 5), the weapon turn-in (level 99 pays the level-95 blue piece) and a restart. It does not win fights (starter-gear heroes lose at level 99, and grinding is not wanted): winning a whole run is covered by the Rust tests.
- Swedish: `python3 scripts/build_swedish.py --check`.
