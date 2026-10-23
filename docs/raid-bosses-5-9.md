# Chained Forge Wardens 5–9

Source is isolated on `feat/raid-bosses-5-9` in `.tools/raid-bosses-5-9-worktree`. This slice adds Dagfinn, Thorbjörg, Ragnhild, Orm and Hildr to their existing halls. There are no new zones or changes to private-copy IDs. Eldmarr and opening the public entrance remain separate tasks.

| Warden | Mechanic | Answer |
| --- | --- | --- |
| Dagfinn Tongsbearer | Two Valves | At 70% and 40%, split across two islands. Each valve needs three living fighters holding together for 20 continuous seconds. |
| Thorbjörg Quenchwife | Brand Relay | Three brands have eight-second fuses. Carry one at least two tiles, then touch an eligible friend to pass it and renew the fuse. |
| Ragnhild Cinderfoot | Four on the Floor | Read a numbered 6 × 6 floor. Wait beside a 1/2 boundary, then cross onto the cleared 1 tile after the first beat. |
| Orm Ashwalker | Water Carriers | Collect flasks from ten wells and deliver six within five seconds. Quenching gives fifteen seconds of double damage. |
| Hildr Lastlink | Mirror Plate | Stop attacking during the five-second warning and eight-second white reflection window. |

Dagfinn gives ten seconds to choose an island before the central lava divide becomes lethal. He is invulnerable during the phase. Continuous holds begin after the warning; each side gets 25 seconds to complete its 20-second hold. Losing the three-person count resets that side's progress. Both valves must complete. If either is unfinished at the deadline, the participating crew falls; stacking the whole group on one island cannot skip the other valve. Leaving the court does not remove a fighter from their joined hold. Incoming damage stops at each threshold, so a large attack cannot skip either phase. The warning and all phases use the same fight and enrage clock.

Dagfinn's death unlocks two lift portals between the descent and his hall. The server checks the actual Dagfinn in the current runtime copy. Other copies stay locked; resetting the instance restores him and closes the lift. Recovering fighters can use the unlocked lift without assembling ten again. The existing muster and quartermaster recovery rules still apply. This follows the owner's later shortcut decision: no lasting lava-level change is made.

Thorbjörg warns for eight seconds before the fuses begin. Brands run for 32 seconds, with a new cast every 50 seconds. Passing requires actual server contact within 1.2 tiles, two tiles of travel since the last handoff, an eligible recipient without a brand, and no active giver immunity. A giver is immune for six seconds. A one-second minimum between passes prevents a single tick from consuming a chain of recipients. The travel requirement prevents a stationary stack from solving the relay automatically. A brand expiring strikes down everyone within five tiles. Leaving the court does not discard a carried brand. Lost bearers are removed rather than making an impossible assignment. The hired brain reserves distinct receivers, prioritizes the shortest fuse, and alternates handoff points; receivers rotate through the crew. One cast cannot starve a later brand merely by taking receivers first.

Ragnhild covers the arena with 36 numbered tiles. A five-second cue precedes four impacts, spaced 0.4 seconds apart (150 BPM). Each tile is hit only on its numbered beat for 90% maximum health before raid reduction. The layout changes every cast (18 seconds). The hired brain prepositions beside a 1/2 boundary and crosses by half a tile after beat 1, leaving time for the actual AI cadence. Numbers, cleared blue tiles, countdowns and beat events supplement colour. The warning remains visible with reduced motion. Once a fighter joins a cast, leaving the numbered court makes every beat hit them; running off the grid cannot cancel its danger.

Orm's flasks are picked up by proximity to a well and thrown by entering the ring within three tiles of his feet. The server assigns each flask once. Carriers move at 60% speed, including dashes. Molten armour takes half damage and doubles his ordinary attack damage. Six throws in a rolling five-second window quench him for fifteen seconds: he takes double damage and loses the molten attack bonus. Spent wells refill when he heats up. A failed window also refills once its throws expire; a fallen or departed carrier returns its flask. Orm stays rooted so the target does not move away while all ten carry. His three-shot ash fan reaches eighteen tiles, including the wells, and receives the same Molten attack multiplier. A melee-only prototype allowed solo fighters to kite between wells indefinitely; the ranged normal attack fixes that without changing health or damage multipliers. All movement and vulnerability modifiers disappear with the fight; saved gear and base stats are unchanged.

Hildr warns for five seconds, then reflects each damaging hit to its actual attacker as 90% maximum-health damage before raid reduction. Other players take no reflection from that hit. The mirror lasts eight seconds, every 40 seconds. The hired brain holds fire from the start of the warning, allowing already flying attacks to land. Human instructions explicitly include damage over time. The white ring and hold-fire label distinguish this from a damage zone; her silver mirror armour and broken-chain halo have original art.

The schema, per-fight engine state, snapshots, danger query and hired responses share `bossmech.rs`, `world/forge_wardens.rs` and `boss_play.rs`. Every outcome is authoritative. Live state belongs to one boss in one runtime copy and is discarded on evade, wipe and reset. No new client action can claim a pass, a flask, a valve count or a hit. Signs, labels, names, material relics and counters have hand-written Swedish.

All five have original 96 × 96, 34-frame, five-clip PixelFlow sprites. Sources are `scripts/make_chained_forge_boss_sprites.py`; editable IDs and exported atlases remain in `client/assets/cathedral.txt`. Boss scale is 2.6. Existing Wardens' sprites are preserved. The content generator owns the new catalog, spawns, courts, signs, mechanics and lift portals. Run `python3 scripts/generate_chained_forge.py`, then `node scripts/sync-world.cjs` and rebuild Rust. Repeated generation must preserve all five generated source hashes.

Each boss uses its existing raid reward table: two distinct Chainforged orange selections, with rebirth and human-only distribution. These Wardens never drop Eldmarr's signature weapons, clear the raid or open its external entrance.

## Reproduce focused validation

Use the RAID target directory, never a production binary or database:

```bash
CARGO_TARGET_DIR=/media/raid/valhallasc-data/raid-bosses-5-9-target bash scripts/cargo.sh test raid_warden -- --nocapture
CARGO_TARGET_DIR=/media/raid/valhallasc-data/raid-bosses-5-9-target bash scripts/cargo.sh build --profile test
REAL_SPRITES=1 VALHALLA_BINARY=/media/raid/valhallasc-data/raid-bosses-5-9-target/debug/valhalla-server NODE_PATH=/home/serveperry/webserver/www/dybase2/node_modules /home/serveperry/.nvm/versions/node/v20.20.2/bin/node tests/raid-bosses-5-9-ui.cjs
```

`MUTATE_FLOOR=1` removes floor rendering and must fail the paired scene-pixel assertion with the HUD suppressed. The browser uses ten real connections and records desktop, landscape and portrait cast screenshots and desktop/portrait signs. The Rust checks cover continuous holds, real transfers and immunity, warning deadlines, four impacts, actual movement slow, missed-window recovery, reflection, copy/reset isolation, lift gating and real orange rewards.

The existing boss-only hired-party report now selects all nine Wardens. Set `RAID_BOSSES` to one new kind at a time, `RAID_BOSS_SEEDS=16`, `ELITE_POWER_FILE` to the tuning table and `ENRAGE_FILE` to `{}` for measurement. Use one scratch executable. The fixture is a level-99 hirer plus nine real quartermaster mercenaries, two of every class, ten pieces of Chainforged gear including the cloak and both rings. Derive each enrage from `ceil(1.06 × slowest ten-fighter kill) + 2`; do not recalibrate packs or other bosses.

## Owner timing decision

The owner accepted the initial faster clear times on 2026-10-23: “that's fine”, “leave it like that”. All five retain their initial `[650, 6]` health/damage multipliers. The preliminary attempt to tune Dagfinn toward the old band (271–280 seconds at health ×950) was stopped and never applied to the source table. Further verification keeps health unchanged; the old 240–320-second band is superseded for these five.

## Measured hired-ten results

All **80/80** fights won, sixteen seeded fights per boss, with enrage disabled for measurement. Health remains 650 million and the damage multiplier remains six for each boss. No harness unsticking was used. Orm was remeasured after adding the ranged normal attack; the table uses that final version. The figures below are simulated fight seconds.

| Warden | Median | Fastest | Slowest | Enrage starts | Falls across 16 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dagfinn | 210.25 s | 201.60 s | 211.70 s | 227 s | 0 |
| Thorbjörg | 328.40 s | 309.30 s | 351.35 s | 375 s | 3 |
| Ragnhild | 188.68 s | 186.60 s | 196.20 s | 210 s | 0 |
| Orm | 88.45 s | 87.45 s | 89.95 s | 98 s | 0 |
| Hildr | 202.90 s | 193.25 s | 204.65 s | 219 s | 0 |

One Thorbjörg run (seed 11) missed one handoff and lost three fighters, then recovered and won in 351.35 seconds. The other 79 runs had no falls. That failure is retained in the raw report; these results do not promise flawless mercenaries. Enrage starts are `ceil(1.06 × slowest kill) + 2`, each with a 30-second ramp. This changes their timers without raising health.

Raw per-seed and per-fighter DPS logs: `test-results/wardens-5-9/full-*.log`, consolidated `full-party.json` and `summary.json`. Mutation reports are in `mutations.json`; each weakened mechanic is rejected by its focused test.

## Smaller-group and solo controls

All 35 controls pass with the final enrage table and identical Chainforged gear. Every solo class dies in every encounter (25/25); no timeout alive is counted as a death. Eight-fighter wins take longer than 1.25× the ten-fighter median. The eight-fighter relay groups lose.

| Warden | Eight fighters, two seeds | Five solo classes |
| --- | --- | --- |
| Dagfinn | 312.05 s, 307.70 s | all died |
| Thorbjörg | lost, lost | all died |
| Ragnhild | 327.45 s, 315.65 s | all died |
| Orm | 154.00 s, 153.75 s | all died |
| Hildr | 358.90 s, 332.05 s | all died |

Raw outcomes, falls, remaining boss health and DPS: `controls.json` and `control-*.log`. Orm’s earlier melee-only failed solo checks are retained under `pre-ranged-*` as diagnostics, excluded from the final results.

## Final verification

- 17 focused Rust checks pass, including real projectile pressure and the one-island valve bypass; four shared Sigrun shield checks pass.
- Five valid-data mutations are rejected (valve count, relay fuse, floor tempo, carrier speed and reflection damage).
- 49 full private browser checks pass with original sprites, ten real connections, both valve holds, the shortcut, all ten water pickups, six real deliveries, isolated per-boss floor pixels, names/counters, Swedish and desktop/phone screenshots. Artifacts: `test-results/driver-L1iQDD`.
- After tightening the valve failure rule, its 19 focused real-browser checks pass again with the final binary and sign: `test-results/driver-aAgsWE`. Successful holds and the measured timing path are unchanged. Use `RAID_UI_BOSSES=cf_dagfinn` to select this browser case.
- 36 checks pass in stub-sprite mode (`test-results/driver-3p57IF`). Removing floor rendering fails at zero changed pixels; the HUD and unrelated fights are excluded from the comparison.
- All 170 original sprite frames match their indexed source and fit the atlas bounds. Existing Warden art is preserved.
- Clippy with warnings denied, formatting, changed JS/Python syntax, Swedish validation and two byte-identical generator rebuilds pass.

Source and assets are maintained on the isolated `feat/raid-bosses-5-9` branch. The finish handoff commits and pushes that source and the main TODO pointers. Merging, public client publication and deployment remain separate; no production DB change or service restart was performed. The entrance remains sealed; Eldmarr, RAID-CHECK and RAID-OPEN remain separate work.

## Owner testing preference

After this implementation, the owner said there is no need for many timing and win-rate runs and that he will do those personally. Future agent validation should focus on mechanics and integration; no repeated timing, win-rate or multi-seed balance sweeps unless explicitly requested. The measurements above were already completed and remain historical evidence. This supersedes the earlier sixteen-seed instructions in this document.
