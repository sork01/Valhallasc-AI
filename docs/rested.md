# Rested

Owner request and decisions, 2026-10-28.

Each character earns **5% Rested per hour offline**, continuously including partial
hours, up to **200% after 40 hours**. Being idle, opening menus or putting the game
in the background while connected does not earn Rested. Unplayed characters accrue
independently, even when another character on the account is online.

While the reserve lasts, all earned XP (monster kills, each member's party share,
and quest turn-ins) receives **200% extra base XP**. A normal 100 XP reward pays
300 XP. Rebirth and Hierloom bonuses remain additive: +50% rebirth, four +100%
Hierlooms and Rested pay 750 XP from a base 100 XP. Rested does not multiply those
other bonuses, and other party members never spend your reserve.

The owner confirmed that **100% Rested stores bonus XP equal to one level's XP
requirement**, and **only the extra XP spends the reserve**. The level requirement
before each reward determines the cost. With 50 bonus XP left, a base 100 XP
reward pays 150 XP, empties the reserve, and later rewards return to normal.
Leveling and rebirth preserve the remaining percentage. No decay while online.
Zero rewards and refused/repeated quest claims spend nothing.

The purple readout below the XP bar shows the reserve out of 200%. Press it for
the rate, cap and bonus explanation; it supports touch, keyboard and Swedish.
The readout is part of the existing Character frame and follows its UI scaling.
It stays hidden when connected to an older server without Rested support.

`Character.rested` is server-owned saved state with serde defaults. The reserve
uses fixed-point level units (72,000,000 per level, 1,000 per offline second),
avoiding float drift across reconnects. Bonus XP rounds down to whole XP and its
reserve cost rounds up to avoid duplication. Less than one bonus XP can remain
until further offline accrual. Payouts saturate at the existing XP integer limit
and never spend reserve for bonus XP that cannot be awarded.

On join, after the already-online check and pending-save recovery, wall-clock
time since the last online checkpoint is credited exactly once. Normal online
saves, disconnect and graceful shutdown update that checkpoint without accruing.
A crash uses the last successful save, so at most the save interval can be
mistaken for offline time; all progression already shares that checkpoint.
Backwards clock jumps earn nothing, long absences clamp at the cap, and neither
clients nor test commands can submit a reserve or offline duration. A persistent
`world_meta.rested_epoch` records when Rested was first installed.
Existing saves without a timestamp accrue from that moment, including characters
that stay offline after release. New characters start empty at creation time.
Offline history before installation cannot be reconstructed reliably. The epoch
is installed idempotently at startup; no per-character database backfill is needed.

Implementation: `server/src/rested.rs`, join/save hooks in `world.rs`, and the
common monster/party and quest reward paths. `boosted_xp` remains the pure existing
rebirth/Hierloom calculation; `reward_xp` applies/spends Rested and grants the XP.
Direct `grant_xp` remains a raw fixture/debug helper, without spending Rested.

Validation: focused `cargo test rested`, a bounded private browser check in
`tests/rested-ui.cjs`, all-target clippy with warnings denied, fmt, changed JS
syntax, Swedish compilation/coverage and release-note validation. No balance
sweeps or broad game suites.

Released as **Beta 1.31.0**, 2026-10-28. All ten focused Rust checks pass,
including persisted installation-time accrual for an old account character.
All 28 bounded browser checks pass at 844 × 390 (English) and 1024 × 768
(Swedish), using the exact release binary; final peak memory was 742 MiB.
Screenshots are `test-results/touch/rested-844x390.png` and
`test-results/touch/rested-1024x768.png`. Visual review caught the quest tracker
painting above the explanation: raise the Character frame while the explanation
is open, because its UI scale creates a separate stacking context.
Clippy for all targets with warnings denied, fmt, changed JS/Python syntax,
Swedish coverage and release-note validation pass. No broad game suite or balance
sweep was run.

Backup: `deploy/backups/rested-1.31.0-20261028T063431Z/` contains the previous
running binary, consistent pre-build database, stopped database, tested next
binary, prior client files and `verification.json`. Deployed with zero humans
online. Public and bridge health, all seven changed public file hashes, the exact
running binary, SQLite quick_check, unchanged 30 characters and 18 guest characters,
absence of test flags and absence of journal warnings/errors are verified.
The feature installation epoch is 1793169798 (2026-10-28 06:43:18 UTC).
No public test character or per-character backfill was used. Rested begins
accruing for existing offline characters from that installation time.
