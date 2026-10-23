# Sigrun Slagmother: Ingot Order

`RAID-BOSS-4`, built in the isolated `feat/raid-boss-4` checkout at `/media/raid/valhallasc-data/raid-boss-4-work`. The public entrance remains sealed. This adds no file zones or private-copy ID changes.

Sigrun holds the fourth chain in The Numbered Forge, hall 4 of The Chained Forge. Six numbered ingots shield her at the start. Only the lowest surviving number accepts damage; all ten fighters focus that ingot, then the next. Each newly vulnerable number gets 25 seconds, including movement. An unfinished ingot bursts at the deadline, dealing 90% of maximum health before raid support reduction to living fighters in Sigrun's court. It then shatters without kill credit or loot. Other halls and private copies are unaffected.

Breaking all six removes the shield. At 40% health Sigrun reforges the six ingots once, at full health, as her escalation. The fight and enrage clocks continue through both shield phases. Evade, wipe and copy reset remove the shield and return every helper to sleep. A fresh pull starts again at number 1 with a full deadline. Numbering follows the authored spawn order, including when a mixture of killed and overheated ingots is reused.

This signature extends `shield` with an optional `ordered` block (`deadline`, `heavy`). Ordinary shields keep their existing damage and target rules. Boss damage and damage against later numbers are rejected in `boss_incoming`, so basic attacks, skills, damage over time and private debug kills obey the same order. The hired brain reads that same current target and directs every class to it. No class or special interaction is required. Compared with Choirmother/Coral Regent, any-order helper kills are insufficient and each number has its own clock. Kettil uses cooperative positional anvils; Sigrun uses damage against real numbered actors.

The client draws a named countdown, the shield counter, a red current ring and dashed waiting rings. Numbers and “Hit this one!” / “Wait for its number” are drawn above actors and do not depend on colour. The approach sign explains all six numbers, the 25-second deadline, raid-wide shock and 40% reforge in plain English with hand-written Swedish.

Sigrun and her ingots have original 96×96, 34-frame, five-clip PixelFlow atlases in `client/assets/cathedral.txt`. Sigrun wears a six-toothed mould crown and furnace apron and carries a pouring ladle; the ingots have their own trapezoidal mould silhouette. Boss scale is 2.6, ingot scale 1.25. Source: `scripts/make_chained_forge_boss_sprites.py`; preview, build, export and verify accept `cf_sigrun cf_ingot` to preserve every other Warden's art.

Source data lives in `scripts/chained_forge_bosses.py`, installed by `generate_chained_forge.py`, followed by `sync-world.cjs` and a Rust build. Health/damage multipliers live in `world/elite-power.txt`; enrage lives in `world/enrage.txt`. The generator owns the fourth boss, its six sleepers, sign, mechanic and catalog, and clears solid decorative props from her court. Two consecutive generations must match the map, catalog, signs, mechanics and items.

Rewards use the existing guaranteed raid table: two distinct selections from Chainforged headgear, cloak and shoulders, multiplied by rebirth, with human-only raid distribution. Helpers have no gold or loot. Sigrun drops no signature weapon and does not clear the raid.

## Focused validation

Rust filter `raid_boss_sigrun` checks damage order and immunity, all-ten hired target choices, per-number warnings, exact deadline behavior, god mode, other halls, original/reset copies, the 40% reforge, sign numbers, full-court reachability, schema rejection and actual orange/rebirth drops. `tests/raid-boss-4-ui.cjs` checks real packets, private kill-path immunity, rendered ground pixels, numbered actor labels, editable art, next-number countdown, readable signs and Swedish at desktop and phone sizes. `MUTATE_FLOOR=1` must fail the paired scene-pixel assertion.

Timing uses the existing boss-only harness with `RAID_BOSSES=cf_sigrun`: a level-99 hirer and nine actual quartermaster mercenaries wearing ten Chainforged pieces. Sixteen seeds, enrage off, then the enrage start is `ceil(1.06 × slowest kill) + 2`; controls use eight fighters and all five solo classes. `[ordered-ingot-expired]` in test output identifies a missed ingot deadline, so a timing win cannot silently stand in for answering the mechanic.

## Verified results

Sixteen of sixteen ten-fighter runs won, with zero falls, missed ingot deadlines or harness unsticking. Median **278.50 s**, fastest **269.70 s**, slowest **285.35 s**. Sigrun has 800 million health (multiplier 800), ingots 25 million each (multiplier 25); Sigrun damage multiplier 6. Enrage starts at **305 s**, with a 30-second ramp, derived from the slowest measured win.

With shipped enrage, eight fighters won in 485.40 and 486.75 seconds (1.74–1.75 times the full-group median), satisfying the approved slower-group control. Every solo class died: Warrior, Mage, Assassin, Priest and Hunter. Controls use actual hired fighters and the same ten-slot Chainforged fixture.

All four focused Sigrun Rust tests and four shared shield compatibility checks pass. A five-ingot data mutation fails the six-ingot assertion. Clippy with warnings denied, formatting, Swedish validation, JavaScript/Python syntax and original atlas verification pass. Two generator runs match all five generated source files.

The real-sprite browser test passed **18 checks**, including ten connected raid members, immunity through the server kill path, six numbered floor markers, actor labels, fresh next-number countdowns, original editable art, Swedish, sealed entrance and desktop/phone cast and sign screenshots. Artifacts: `test-results/driver-Td0onl/`. Disabling floor telegraphs is rejected by the paired scene-pixel assertion. Raw measurements, per-fighter DPS, all seven controls and gate logs are in `test-results/sigrun/`.

Reproduce the measurement with `RAID_BOSSES=cf_sigrun RAID_BOSS_SEEDS=16 ELITE_POWER_FILE=world/elite-power.txt ENRAGE_FILE=test-results/sigrun/enrage-off.txt /media/raid/valhallasc-data/raid-bosses-target/debug/deps/valhalla_server-fadf8f897c2036af --ignored --nocapture raid_boss_measure_first_three`. The optional harness name predates this fourth Warden; its selector now includes Sigrun. Private browser binary: `/media/raid/valhallasc-data/raid-bosses-target/debug/valhalla-server`, built from the final source with `--profile test`.

Source remains uncommitted in isolated `feat/raid-boss-4`. No merge, deployment, production DB change or service restart was performed.
