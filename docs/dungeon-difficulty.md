# Dungeon enemy health and damage

## Current correction: 25% below the 1.15.5–1.15.8 values

Owner clarification, 2026-11-27: reduce current dungeon enemies by **25%**.
The requested example is 200,000 health becoming 150,000. This lowers the earlier
+100% boost to +50% of the original baseline; it does not halve current stats.
Health and damage both use 0.75 of their current multipliers.

The change covers all 127 kinds in the 20 ordinary dungeons: packs, bosses and
sleeping helpers, across all 80 runtime copies. Scope remains maps with
`copies > 0` and `raid == false`, resolving private copies through their template.
Dungeon kinds do not overlap outdoor or raid kinds. All other entries in
`world/elite-power.txt` and their key ordering are preserved.

The exact previous table is pinned in
`tests/fixtures/dungeon-power-before-1.15.9.txt`. The older pre-increase table
remains in `tests/fixtures/dungeon-power-before-1.15.5.txt`. Both health and damage
are 0.75 of the former and 1.5 of the latter.

`Slime::stats` applies the existing power overlay before level scaling.
`Slime::with_level` applies level scaling and rounds spawned health/damage, so
snapshot comparisons allow one point for integer rounding. Speed, attack timing,
enrage timing, fixed/fractional/instant-kill boss mechanics, rewards, loot and
player stats keep their existing rules. The raid and outdoor enemies are outside
this change. Dungeon/raid mercenary contracts retain the 1.15.8 death/wipe fix.
No world generation or save migration is needed.

## Verification and activation

The two `dungeon_difficulty_` Rust regressions check every affected kind, all
preserved factors, default and ±2 spawn levels, full starting health, all 20
templates and their 80 copies. They also check that the resulting multipliers
are 1.5 of the original baseline. Through the existing test-only
`ELITE_POWER_FILE` override, both the previous doubled table and an incorrect
half-current table must fail the new expectations.

Both native checks pass. Both also fail with each incorrect table: retaining the
current doubled factors gives Abyss Zealot 94,000 HP instead of 70,500; halving
current factors gives 47,000 instead of 70,500. This checks the clarified 25%
reduction rather than either of the earlier interpretations.

`tests/dungeon-difficulty-probe.cjs` compares the retained live and candidate
executables in separate private worlds: authoritative health must be 75% of the
previous value in all 20 dungeons, with matching kinds and levels. The native
checks cover every kind and damage value. The candidate also checks 30 snapshots
arrive within 3000 ms, with tick gaps of two. No balance grind or multi-seed
win-rate sweep is required or performed.

Released after the owner's explicit “deploy” approval as **1.15.9-3493e600**,
source branch `balance/dungeon-difficulty-150-percent` in
`/media/raid/valhallasc-data/firefox-scrolling`. All 20 private executable
comparisons pass, and 30 snapshots arrive in 2956 ms with tick gaps two. Using the
unchanged executable as both sides fails the 75% health assertion as expected.
The running and installed executable match the frozen candidate, PID `1344169`,
SHA-256 `2c8dc909c7bbf3e26deeedd3449d2f36f9801ebace4929bb82c02778185054cf`.
All ten saved character states are unchanged. SQLite, public/legacy/bridge health,
the changed public files and clean journal pass; no test flags are present.

Receipt: `www/Valhalla/dungeon-minus25-release-receipt.json`. Backups and frozen
executables: `/media/raid/valhallasc-data/backups/valhalla-dungeon-minus25-20261127T082522Z-2pklrsno/`.
Client rollback is `1.15.8-c4059296`; executable rollback uses
`previous-before-build` there and requires fresh restart approval.

## Earlier increase: 1.15.5

On 2026-11-26, the owner requested dungeons become 100% harder. Release
`1.15.5-667091cb` doubled both health and damage for these same 127 kinds and
20 ordinary dungeons. Existing factors were multiplied by two; missing entries
used `[1, 1]`. Raid and outdoor factors were unchanged. The original two native
checks, previous-table mutation and all 20 private comparisons passed.

That release followed explicit “restart and deploy” approval. It verified PID
`908531`, all eight then-saved character states, SQLite, health and journal.
Historical receipt: `www/Valhalla/dungeon-difficulty-release-receipt.json`.
Backups: `/media/raid/valhallasc-data/backups/valhalla-dungeon-double-20261126T173855Z-ifp8b6p9/`.
The full history is in wiki
`10_projects:valhallasc_dungeon_difficulty_double_staged_20261126`.
