# Chained Forge: first three Wardens

Work for `RAID-BOSS-1`, `RAID-BOSS-2` and `RAID-BOSS-3`, 2026-10-23. The public entrance remains sealed. Development is isolated in `.tools/raid-bosses-worktree`, branch `feat/raid-bosses-1-3`, with the existing `feat/raid-rewards` content integrated locally to use real Chainforged gear and guaranteed orange rewards. No public files, service or saved characters are changed.

The source of their positions is `scripts/chained_forge_bosses.py`, installed by `generate_chained_forge.py`. Rebuilding the raid preserves later encounters. Run the generator, `sync-world.cjs`, and build the server. The generator also maintains the catalog, signs and mechanics; balance stays in `elite-power.txt` and `enrage.txt`. All three Wardens are level 99 and use original 96×96, 34-frame, five-clip PixelFlow sprites at the raid's 2.6 scale. Editable IDs remain in `client/assets/cathedral.txt`.

| Warden | Signature | How to answer |
| --- | --- | --- |
| Kettil Linkbearer, The First Link | Taut Chain | Five numbered pairs, with one trio for an odd crew. Follow the dashed chain to identify your partner. Stand together at your numbered blue anvil; chains break in order, 1 through 5. |
| Ysolt Bellowsmaid, The Iron Lung | Gale of the Bellows | Four iron posts each shelter at most three fighters. Follow the gold arrow and spread between the blue posts before the wind pushes unprotected fighters ten tiles toward the red lava rim. |
| Hallgrim Anvilhand, The Three Anvils | Hammerfall | Three separate circles each need at least three living fighters at impact. Split 4/3/3, keeping a spare who can fill a gap. |

Kettil warns for nine seconds, then holds the standing leash for twelve seconds. Partners more than six tiles apart take 45% of maximum health per second before raid reduction. Each pair holds its anvil for 1.5 seconds, in order; the last pair has enough time after the first four. An unresolved chain hits its own pair for 90% at expiry. A fallen partner removes the impossible chain. This is a continuing distance constraint with cooperative release, distinct from the existing marks that resolve once into a tether. Every 30 seconds, new seeded partner groups are drawn; below 40% health this becomes every 24 seconds.

Ysolt warns for ten seconds every 30 seconds. Her four posts have a 1.5-tile radius and three-person capacity. The actual nearest three fighters at a post are sheltered; the client cannot claim protection. A swept, collision-checked push prevents movement through walls, and crossing the red 0.8-tile rim kills regardless of defenses. The wind zigzags toward one corner before reversing; a fixed four-way square would let an idle crew drift safely forever. Below 40% health the interval shortens to 24 seconds. GM/test god mode still blocks death. The warning extends the original five-second sketch because a full group starting at one corner needs to reach all four posts within the 60% movement allowance.

Hallgrim warns for eight seconds, every 28 seconds above 40% health and every 21 seconds below. Each radius-three circle needs three living, visible, unfrozen fighters. A deficient circle strikes down its occupants, then the failed hammer deals a 75% maximum-health shock to the crew, before raid reduction. The shock is applied once per cast so it remains a recoverable mistake for the other two groups. A current announced cast finishes before the low-health escalation starts. The warning grows from the original five-second sketch to meet the reach rule for every assigned anvil.

All three use server-owned timers and state per boss per private copy. Evade, wipe and reset discard their assignments, progress and warnings. New mechanics have a shared threat query and a `boss_play.rs` hook: a small capacity-constrained matching chooses stable group positions for hired fighters; it uses the same state that is sent to human clients. No player class is required. The raid signs are extended to allow several Wardens in one zone while ordinary dungeons keep their final-boss sign.

The previously approved `RAID-DAMAGE-REDUCTION` setting is applied here as a prerequisite to measuring these fights: 5% per other fighter, capped at 45%; the attack bonus stays +50% per other fighter. Pack timing remains deferred.

Rewards use the existing `RAID-ORANGE` tables: two distinct slot selections per Warden, multiplied by rebirth. Kettil: armor/headgear/cloak; Ysolt: shoulders/gloves/pants; Hallgrim: necklace/accessory/armor. These bosses never drop the signature weapons reserved for Eldmarr. Their death neither clears the raid nor opens its public entrance.

## Focused validation

Only these bosses, the changed raid support, and the sign functions they share are tested; no whole-suite or pack-time sweep. The private real-sprite Chromium run checks ten real clients, actual server packets, desktop and phone screenshots, signs and paired scene pixels. Station counts are drawn over actors so a large boss cannot hide them; an overfull post displays its actual occupancy.

The timing fixture is a level-99 Warrior hirer plus nine real quartermaster mercenaries, two of each class, in ten pieces of Chainforged gear including the cloak and two rings. The real hired brain handles each mechanic. Measurement uses scratch `ELITE_POWER_FILE` and `ENRAGE_FILE` files; enrage starts are `ceil(1.06 × slowest ten-fighter kill) + 2`. Each Warden targets a median 240–320 seconds, with sixteen seeds. The eight-fighter and lone controls use the same gear and mechanics.

## Measured ten-fighter times

All 48 runs won with zero falls and zero harness unsticking. The enrage was disabled for measurement, then set from the slowest actual kill. The band applies to the median; faster individual runs remain recorded.

| Warden | Health | Median | Fastest | Slowest | Enrage starts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kettil | 650 million | 290.38 s | 285.50 s | 294.60 s | 315 s |
| Ysolt | 800 million | 275.57 s | 187.30 s | 289.70 s | 310 s |
| Hallgrim | 720 million | 273.43 s | 217.25 s | 290.90 s | 311 s |

The health multipliers are 650/800/720 over the catalog's authored one-million base; damage is ×6. All live balancing goes through `elite-power.txt`. Enrage ramps over 30 seconds. Per-seed times, falls and each fighter's DPS are in `test-results/raid-boss-balance/kettil-16-seeds.log`, `ysolt-hallgrim-16-seeds.log`, `full-party.json` and `summary.json`. An independent trace of Ysolt's fast seed confirmed the crew continued to answer the posts; timing numbers above keep the original measured sample.

Reproduce one boss at a time with the test executable on the RAID:

```bash
CARGO_TARGET_DIR=/media/raid/valhallasc-data/raid-bosses-target bash scripts/cargo.sh test raid_boss --no-run
ELITE_POWER_FILE=test-results/raid-boss-balance/power-final.txt BOSSMECH_TABLE_FILE=world/boss-mechanics.txt ENRAGE_FILE=test-results/raid-boss-balance/enrage-off.txt RAID_BOSSES=cf_kettil RAID_BOSS_SEEDS=16 /media/raid/valhallasc-data/raid-bosses-target/debug/deps/valhalla_server-fadf8f897c2036af --ignored --nocapture raid_boss_measure_first_three
```

`RAID_BOSS_COUNT=8` measures the smaller crew; `RAID_BOSS_COUNT=1 RAID_BOSS_CLASS=warrior|mage|assassin|priest|hunter` selects a lone-class control. Use `ENRAGE_FILE=world/enrage.txt` for controls with the real enrage. `RAID_BOSS_FIRST_SEED=11 RAID_BOSS_SEEDS=1 DUNGEON_BOSS_TRACE=1` replays a single seed with positions. These are test-only options. No test flags are added to the public service.

## Smaller-group and solo controls

With the shipped enrage enabled, all six eight-fighter controls won later than 1.25× the ten-fighter median. They are permitted to win later under the approved rules; no claim is made that eight are locked out. Hallgrim caused four falls per run. Every lone class died in every selected encounter (15 controls, one seed per class per boss).

| Warden | Eight fighters, two runs | Time relative to ten-fighter median | Falls per run |
| --- | --- | ---: | ---: |
| Kettil | 431.00–439.35 s | 1.50× | 0 |
| Ysolt | 449.90–457.45 s | 1.65× | 0 |
| Hallgrim | 489.35–495.40 s | 1.80× | 4 |

Raw class-by-class solo times and outcomes are preserved in `test-results/raid-boss-balance/controls.json` and `control-*.log`. The slowest lone control was the Priest against Ysolt (1,038.3 s), still a death. There is no control that simply timed out alive. The eight-fighter group has one of each class plus another Warrior, Mage and Assassin, following the existing quartermaster fixture order.

Focused server validation: 23 passed, with only the optional timing report ignored. This includes the first three mechanic blocks, odd crews, live occupancy, sequential chain release, full warnings and low-health phase transitions, actual deaths, lava pushes, other-hall and copy isolation, fresh pulls, real orange/rebirth drops, fairness over the whole court, all seven changed raid-support checks, and ordinary sign access. Data mutations that weaken the leash, increase shelter capacity, or reduce the soak count each make their matching test fail. Clippy with warnings denied, formatting, Swedish catalog, Python and JavaScript syntax pass. Two consecutive generator runs match for the map, catalog, mechanic table and signs; unrelated compact boss-table entries retain their original formatting.

Final private browser verification: `tests/raid-bosses-ui.cjs` passed 32 checks with real sprites; artifacts `test-results/driver-31uhpx` include each cast and sign at desktop/phone size and Kettil's active Heave. `tests/raid-support-ui.cjs` passed 20 checks; artifacts `test-results/driver-tVx3vi` verify the 45% readout and live contract/copy changes. Disabling the floor telegraph renderer (`MUTATE_FLOOR=1`) is rejected by the paired floor-pixel assertion; the HUD is suppressed in both comparison frames, so a surviving cast bar cannot hide missing floor art.

The tested source and assets are maintained on isolated `feat/raid-bosses-1-3`, including the existing raid-rewards dependency. The finish handoff commits and pushes this feature branch and main TODO pointers. Merging to main and deployment remain separate: no public restart, database migration or client publication is part of this session. This slice adds no file zones and shifts no copy IDs.
