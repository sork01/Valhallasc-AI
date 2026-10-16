# Player-side kill-time balance

Decision on 2026-10-15: increase player attack and health instead of reducing monsters. Every monster's health, damage, attack pattern, XP and gold stay unchanged. The baseline remains a green progression set with even recommended attributes, no consumables and the normal skill rotation. The private harness in `server/src/world/ttk.rs` is the source of measurements.

## Targets

`world/ttk-targets.txt` is the shared source for the test and this table. Levels 5–10 retain their faster pace because the owner chose to keep monster stats unchanged and player damage cannot be lowered to fit the former 15–30 s band.

| Levels | Median kill time |
| --- | --- |
| 5–10 | 6–15 s |
| 15–20 | 15–30 s |
| 25–45 | 20–40 s |
| 50–75 | 25–50 s |
| 80–99 | 30–60 s |

Every tested class must kill, finish above 20% HP, and stay within 1.3 times the fastest class at that level.

## Implementation

- `Character::stats` multiplies final attack by a class-and-level calibration and a common level curve in `server/src/items.rs`. Both basic attacks and skills use that authoritative stat. The common attack factor grows from 1 at level 15 to 1.48 at 20, 5.26 at 50 and 16.56 at 99. The class curve is measured separately at every fifth level and interpolated between them.
- `Character::max_hp` multiplies the old class/level/stamina formula by `PLAYER_HEALTH_CURVE` in `server/src/model.rs`: 1 at level 10, 3 at 20, 8 at 50, 20 at 90 and 36 at 99. A one-time store migration preserves each saved character's current HP percentage and leaves defeated characters defeated. It records `health_curve_version` so reconnecting cannot repeat the conversion.
- The first player-side grid (one seed per case, 100 cases) killed every target, versus 76 failures in the old nine-seed report. A second one-seed grid exposed small class outliers; the final class adjustments were checked with nine seeds. The final report in `docs/ttk-report.md` covers **100 cases and 900 fights**: zero failed seeds, every median inside its level band, maximum class kill-time spread **1.291×**, and lowest median remaining HP **37%**. The level-5 assassin was rerun for nine seeds after a final point adjustment and its row replaced in the raw class report before merging.

## Checks and limits

Run `TTK_RUNS=9 bash scripts/ttk-parallel.sh` for all 100 cases, then pass the five JSON files from that run directory to `python3 scripts/check_ttk.py` to check its raw results. `sampled_kill_times_stay_in_band_across_classes_and_progression` runs in the normal Rust test suite; `full_kill_time_balance_gate` applies the shared target data to the complete nine-seed grid when explicitly requested. The report includes damage per hit and HP left so a time-only pass cannot hide an unsurvivable fight.

The stronger players make group content easier with monster stats fixed. In deterministic private probes, a level-20 solo warrior now clears the Undervault barracks and ossuary packs in 33 and 69 seconds, while a full party clears them in 16 and 19 seconds with much more HP left. The four Undervault bosses fall to a full party in 57–90 seconds; a three-person party beats the Hollow King in 125 seconds against the full party's 90. A solo level-35 warrior can hold the last sky ward for its full 120 seconds. Oakhorn falls to a solo warrior after 245 seconds and nine deaths, while a three-person party wins in 65 seconds without a death. Hrungnir survives a solo warrior's 300-second attempt, but a three-person party wins in 97 seconds and a full party in 55. The group tests now check these party advantages instead of enforcing old group-only gates.

PvP and healing as a fraction of max HP also change with the larger player stats; the kill-time grid does not measure those modes. XP and gold paid per kill are unchanged, but higher kill rates increase both per hour. The follow-up audit and new consumable curve are in [consumable-audit.md](consumable-audit.md) and [consumables.md](consumables.md).
