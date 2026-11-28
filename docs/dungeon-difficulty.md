# Dungeon enemy health and damage

## Boss-only follow-up, released 1.15.13: 50% more health

Owner request, 2026-11-27: dungeon bosses get 50% more HP. Applied to the current
values for the same 65 ordinary-dungeon boss kinds as 1.15.11 (150,000 becomes
225,000). Health only: damage, packs, helpers, raid and outdoor enemies are
unchanged. Boss health is now 1.6875 of the pre-1.15.5 baseline.

The pre-change table is pinned in
`tests/fixtures/dungeon-power-before-boss-hp-plus50.txt`. The spawn test rounds the
combined factor to the table's 10 decimals: Mournsister two levels down lands on
exactly 670,234.5, and multiplying the factors one at a time rounds it the other way.
`tests/tools/dungeon-boss-health-probe.cjs` defaults to this change (`BOSS_HP_FACTOR`,
`BOSS_HP_FIXTURE` override it; 0.75 with `dungeon-power-before-boss-hp.txt`
reproduces 1.15.11).

Verified: three `dungeon_difficulty_` checks pass and all three fail on the old
table through `ELITE_POWER_FILE`. The optimized candidate passes 65 private boss
comparisons with 34 pack/raid controls unchanged (Gatewarden 123,300 to 184,950);
using the old executable on both sides fails. Branch
`balance/dungeon-boss-health-plus50`.

Owner approved with "deploy it". Released as **1.15.13-c32ee8bc** and
fast-forwarded to main. The only non-test server or world file that differs from
1.15.12 is `world/elite-power.txt`. Verified PID `1543908`, exact candidate
executable, all ten character rows unchanged, SQLite, public/legacy/bridge health,
both changed public files, no test flags and a clean journal. Receipt
`www/Valhalla/boss-hp-plus50-release-receipt.json`; backups and frozen executables
`/media/raid/valhallasc-data/backups/valhalla-boss-hp-plus50-20261127-PxlUND/`. Client rollback is
`1.15.12-85b15f7e`; executable rollback is `previous-before-build` there and needs
fresh restart approval.

## Boss-only follow-up, released 1.15.11: another 25% less health

Owner clarification, 2026-11-27: **dungeon bosses only, not raids**. Multiply
current boss health by 0.75 (200,000 becomes 150,000), preserving damage.
The 65 boss kinds across all 20 ordinary dungeons and their 80 runtime copies
are selected through `items::is_boss` and the existing ordinary-dungeon scope.
Boss kinds do not overlap raid/outdoor kinds. Ordinary packs and sleeping
helpers retain their current health. All damage multipliers remain identical.

The pre-change table is pinned in
`tests/fixtures/dungeon-power-before-boss-hp.txt`. Only the first number of those
65 entries changes. Boss health becomes 1.125 of the pre-1.15.5 baseline;
ordinary enemy health and all ordinary-dungeon damage remain 1.5 of that baseline.
No world regeneration, mechanics changes or save migration.

The three focused `dungeon_difficulty_` checks cover every power value, unchanged
speed/scale and damage, default and ±2 spawn levels, all 65 bosses and every
private copy. `tests/tools/dungeon-boss-health-probe.cjs` compares the retained public
and candidate executables in private worlds: all 65 boss max-HP values become
75%, and representative dungeon packs and all raid enemy kinds retain exact HP.
No encounter grinding or win-rate sweep. This follow-up is included with the
1.15.11 party-resource update.

Verified: all three focused native checks pass. The exact optimized executable
passes 65 private boss comparisons, plus 20 ordinary pack and 14 raid enemy-kind
controls with unchanged HP. Gatewarden changes from 164,400 to 123,300 HP.
Using the unchanged executable for both sides fails that comparison as expected.
Swedish, release notes, all client JavaScript syntax and whitespace gates pass.

Implementation `1ebe3ade`, branch `balance/dungeon-boss-health-minus25` in
`/media/raid/valhallasc-data/firefox-scrolling`, includes the staged party bars.
Frozen candidate: 57,204,176 bytes, SHA-256
`12e11e1cfc1e694bc2d8ffcada5fb61c353e21303085a2779dc21789cc5b4fdc`.
Backups and staged receipt:
`/media/raid/valhallasc-data/backups/valhalla-dungeon-boss-hp-20261127-y50wu_mj/`;
public receipt `dungeon-boss-hp-release-receipt.json`.

Owner approved “merge whatever branch there is and deploy”. Merged to main as
`40429bbe`, released from `78b2254d` as **1.15.11-78b2254d**. The merge changes
only backlog documentation relative to the tested runtime. Verified PID
`1480788`, exact candidate executable, all ten character states unchanged,
SQLite, public/legacy/bridge health, five public files, no test flags and a clean
journal. The release helper verified the whole client copy byte-for-byte.
Rollback client: `1.15.10-a5e486f2`; executable: `previous-before-build` in the
backup directory (a rollback restart needs fresh approval).

Main is checked out in `/media/raid/valhallasc-data/firefox-scrolling`. The
original `/media/raid/valhallasc-data/valhalla-dev` checkout remains at its prior
commit on `preserve/main-local-art-20261127`, with all 33 local/untracked artwork
and note files preserved and hash-verified. Backups are under `main-local-work/`
in the release backup directory. Production executable installation remains at
that original checkout's `target/release/valhalla-server` path.


## Previous correction: 25% below the 1.15.5–1.15.8 values

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

`tests/tools/dungeon-difficulty-probe.cjs` compares the retained live and candidate
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
