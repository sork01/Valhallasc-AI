# Test tools

Measuring tools, balance checks and the database rehearsal live in the Rust crate beside the code they measure, behind the
`tools` build switch. A plain `cargo test` does not build or list them. They are also marked `#[ignore]`, so building with
the switch still runs none of them unless asked.

```
bash scripts/cargo.sh test --features valhalla-server/tools <name> -- --ignored --nocapture
bash scripts/cargo.sh test --features valhalla-server/tools -- --ignored --list      # all of them
```

| Tool | Command |
|---|---|
| Kill-time report | `bash scripts/ttk.sh`, `bash scripts/ttk-parallel.sh` |
| Damage per class | `bash scripts/dps-parallel.sh` |
| Best skill order | `bash scripts/best-rotation-parallel.sh`; replay: `replay_best_rotations` |
| Duel matrix | `bash scripts/duel-parallel.sh` |
| Lone player and parties in dungeons | `bash scripts/dungeon-solo-parallel.sh`, `bash scripts/dungeon-party-parallel.sh`, `scripts/dungeon-calibrate.py` |
| Group elites | `bash scripts/elite-solo-parallel.sh`, `bash scripts/elite-party-parallel.sh` |
| Arena win rates | `rates_<level>` |
| Probes and measurements | `vault_balance_probe`, `ward_balance_probe`, `duel_probe`, `wyrd_balance_probe`, `cathedral_balance_probe`, `dungeon_probe`, `dungeon_inventory`, `consumable_audit`, `blackhour_blue_and_green_encounter_bands`, `raid_boss_measure_first_three`, `raid_pack_measure_encounters` |
| Database rehearsal | `REHEARSE_DB=<copy of the live database>` with `rehearse_migration` |

The balance rules were retired by the owner on 2026-11-14, so a failing balance check is not a defect.

A new measuring tool or slow check gets `#[cfg(feature = "tools")]`, `#[test]` and `#[ignore = "why"]`.

## Browser and Node scripts

Scripts that need extra input, and the public smoke check, are in `tests/tools/`; the suite runners only take `tests/*.cjs`.

| Script | Needs |
|---|---|
| `character-hair-art.cjs`, `female-torso-art.cjs` | git-ignored art inputs (`scripts/make_test_art_inputs.sh`) |
| `gear-piece-art.cjs` | a checklist job id |
| `gear-sheet.cjs` | `OUT` and `LOOKS` |
| `shared-slime-art.cjs` | the shared art candidate, real artwork and the bounded runner |
| `dungeon-boss-health-probe.cjs`, `dungeon-difficulty-probe.cjs` | an old and a new server executable to compare |
| `public-smoke.cjs` | nothing, but it creates guest characters on the live game: run it only on purpose |
