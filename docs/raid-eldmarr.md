# Eldmarr, the Ember-Lord

Release update 2026-10-23: merged into main and deployed in `c4d5e9e`; the raid entrance is open. The implementation notes below describe the original isolated build. Timing and win-rate evaluation remain with the owner; see `molten-raid.md` for release checks and current handoff.

`RAID-BOSS-FINAL` is implemented on `feat/raid-eldmarr`, based on the completed Wardens 5–9 branch plus main. The source checkout is `/media/raid/valhallasc-data/raid-eldmarr-work`. No new file zone, copy ID shift, public client publication, database change or restart is involved. The external entrance remains sealed.

Eldmarr is the original fire giant from the approved story: the first forge keeper, denied his promised place in Valhalla and bound beneath Asterion by nine Wardens. His existing Asterion/Emberwake foreshadowing is preserved. His final hall now contains the actual catalog boss, a readable approach sign and original editable PixelFlow art. The 96 × 96 sprite has 34 frames across idle, walk, attack, hurt and death, rendered at scale 3.2. Its basalt mantle, nine-link crown, flame beard, furnace ribs and great cleaver differ from the Wardens.

| Health | Mechanic | Server rule and player response |
| --- | --- | --- |
| 100–66% | The Forge Floor | Staying in one 2 × 2 floor cell for three seconds cracks it. An eight-second red warning precedes lethal lava; the cell cools forty seconds after becoming lava. Move into another cell. |
| 66–33% | Rising Heat | Heat rises from time, without receiving damage. Four blue Cold Wells each cool at most three living fighters. The wells rotate every thirty seconds, with their next positions shown five seconds beforehand. A full meter starts a separate five-second lethal blast fuse, radius five. Cooling below 90% cancels that fuse. |
| 33–8% | A Seat for Everyone | Every forty seconds, ten numbered plates appear for a nine-second warning. Each plate shelters exactly one living actor. Use the assigned number; a fallen fighter's seat is spare. The server counts actual occupants, so two bodies cannot share a plate. |
| Below 8% | Eldmarr Unbound | The nine chains are broken. All three systems run together; floor dwell, well relocation, heat gain and seat intervals are 1.25 times faster. Lethal warning lengths stay eight, five and nine seconds. |

Three chains break at each threshold, with a banner and sound. The floor tint, chain stumps, wells and seat furniture change with the phase. At 66% and 33%, a ten-second breathing window suspends both mechanics and boss attacks. He cannot take damage during these windows. Incoming hits stop at the next phase boundary, including an opening hit before the first mechanics tick, so burst, damage over time and signature weapons cannot skip a phase.

The approved draft's five-second seat warning was lengthened to nine seconds to satisfy the shared reachability rule **with ten separately assigned plates**. All authored court cells can reach every plate within `5.2 × 0.6 × 9` tiles along a clear route, including a crew starting stacked at one corner. Plate centres form a non-overlapping ring, radius five, each safe circle radius 1.2. No class or dash is required.

In the combined phase, the Cold Wells and current seat circles cannot contain lava. Heat and its pending fuses pause during a seat warning; a successful seat clears both when it lands. This prevents a simultaneous demand to hold a plate and visit a well, or a short fuse resuming before cooling is reachable. Eldmarr stays on the nearest unoccupied ground to his authored throne position. Actor spacing still applies, while melee separation and knockbacks cannot drag him and the crew across the hall into old lava. Persistent lava is included in the danger query and in a small court route search for hired fighters; ordinary stone pathfinding alone would send them straight through a live floor cell.

A fighter joins by actually entering the hall or contributing to Eldmarr. Leaving does not discard heat, escape a pending seat or cancel participation: an eight-second return warning covers leaving the court. Dead and departed actors are excluded from counts. Live state belongs to one boss in one runtime copy and is discarded on evade, wipe, death and reset. Temporary effects never change saved stats or gear. The existing 2,400-second raid fallen hold covers this encounter; ordinary dungeons retain 600 seconds.

The hired brain retains its floor escape goal until it has crossed clear; continually choosing the nearest point to the boss can oscillate at a cell boundary. It uses the same engine state: move before dwell completes, split among cooling wells with capacity matching, and take distinct numbered seats. The ordinary `merc_think` and the harness's `auto_play` share these answers. The hirer and nine actual quartermaster hires are covered by a short movement/roles integration check; no encounter completion time is used as a test assertion.

On death, the existing guaranteed raid reward table awards two orange armour selections and two signature weapons, preserving rebirth and the humans-only roll path. The raid clears when its actual final boss dies. A single boss announcement is emitted per cleared copy, the `after_clear` exit opens, and a thirty-minute reward chest appears near the released exit (111, 29). Repeat clear calls do not duplicate the announcement or chest. Other copies stay closed. The shipped dungeon/final-boss music switch now receives the actual Eldmarr fight and death snapshots.

Cracked and lava cells also have a foreground outline above actors and darkness, so Eldmarr cannot hide their footprint. Each cracked cell shows seconds until lava; live lava shows an exclamation mark. These cues remain visible with reduced motion and Low graphics.

All instructions, names, meters, banners and the announcement have hand-written Swedish. Numbered roles and heat percentages supplement colour, and the full warnings remain visible with reduced motion.

## Balance is left to the owner

The owner's latest instruction (2026-10-23) is that he will do timing and win-rate testing himself. No repeated timing, win-rate, sixteen-seed or balance-control sweeps were run for this task. The design target remains at least 900 simulated seconds for the hirer plus nine mercenaries in full Chainforged gear. **It has not been measured or certified here.**

Initial tuning: base health 1,000,000 × 4,500 = 4.5 billion; damage ×6; soft enrage starts at 1,320 seconds with a thirty-second ramp. These are provisional encounter settings, not measured evidence that ten fighters win or eight lose. The owner can select `RAID_BOSSES=cf_eldmarr` in the existing ignored `raid_boss_measure_first_three` harness; its Eldmarr cap is now 2,400 seconds. Recalculate the enrage from the owner's accepted results before opening the raid.

## Focused verification

Use the RAID build cache and the private database supplied by the test driver:

```bash
CARGO_TARGET_DIR=/media/raid/valhallasc-data/raid-bosses-5-9-target bash scripts/cargo.sh test eldmarr_ -- --nocapture
CARGO_TARGET_DIR=/media/raid/valhallasc-data/raid-bosses-5-9-target bash scripts/cargo.sh build --profile test
REAL_SPRITES=1 VALHALLA_BINARY=/media/raid/valhallasc-data/raid-bosses-5-9-target/debug/valhalla-server NODE_PATH=/home/serveperry/webserver/www/Valhallasc/node_modules /home/serveperry/.nvm/versions/node/v20.20.2/bin/node tests/eldmarr-ui.cjs
```

The worktree has no `.tools/cargo` installation. In that checkout also export `CARGO_HOME`, `RUSTUP_HOME` and `PATH` pointing to the primary checkout's `.tools/cargo` and `.tools/rustup`.

Mechanic tests cover each base mechanic, actual death and spared bystanders, dwell reset/cooling, real well capacity, cancelable fuses, relocation, distinct seat roles, spare seats, exits, phase gates, safe breathing, final overlaps, hazard routing, copy cleanup, the long fallen hold, actual orange/signature drops and idempotent clear rewards. A focused hired-movement check exercises the real AI cadence rather than teleporting the crew through casts. The browser checks actual server snapshots, desktop/phone casts and signs, original sprites, Swedish, ten actual plate occupants, the reward chest and live music switching. `MUTATE_FLOOR=1` removes floor rendering and must fail its scene-pixel check with the HUD suppressed.

Rebuild source data with `python3 scripts/generate_chained_forge.py`, then `node scripts/sync-world.cjs`, `python3 scripts/build_swedish.py` and Rust. Art commands accept `cf_eldmarr` so they preserve every Warden's editable sprite: `make_chained_forge_boss_sprites.py preview|build|export|verify cf_eldmarr`.

## Accepted results

- **20 focused Rust checks pass**, including all three base mechanics, the combined finale and the real hired-ten movement sequence. This is a mechanics fixture with no normal attack pressure and an effectively unkillable target; it is not a timing or win-rate measurement.
- **31 private real-sprite browser checks pass**, using the actual shipped server table, ten connected fighters, all four phases, the two breathing windows, actual plate counts, orange/signature rolls, clear/chest and the existing final-music switch. Artifacts: `test-results/driver-qJFuD7`; machine-readable evidence: `eldmarr-ui.json` there.
- Removing floor rendering with `MUTATE_FLOOR=1` is rejected at **zero changed floor pixels**. The HUD is excluded from the comparison.
- Desktop and phone landscape captures show the actual casts. Portrait captures show the existing rotate-device guard; they are not evidence of portrait playability. The sign was checked and captured on desktop.
- All 34 original sprite frames match their indexed source and fit the atlas. The manifest preserves every older sprite.
- The final eight generated map/catalog/sign/client sources remain byte-identical after another generator/sync pass.
- Clippy over all targets with warnings denied, formatting, changed JS/Python syntax and Swedish validation pass.

Consolidated evidence and logs: `test-results/eldmarr-proof/`. No broad test suite, balance sweep, public guest, production restart or database change was performed.
