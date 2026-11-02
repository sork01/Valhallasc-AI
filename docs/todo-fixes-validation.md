# Seven owner reports — Beta 1.32.8

Implemented from the seven open owner reports of 2026-11-01. The owner's
2026-11-02 decisions are recorded in TODO.md: any arena giver can enter/reward a
trial; quest cleanup discards only completed/abandoned leftovers, without gold.

## Publication state

**Deployed and verified 2026-11-02**, with zero humans online. Public client is
Beta 1.32.8 and the running executable matches the reviewed release binary.
The complete reviewed source export is at
`/media/raid/valhallasc-data/todo-fixes-1.32.8-source/`.

The earlier Bifrost/wind changes form the validation baseline and are preserved.
The backed-up executable matches the previous Beta 1.32.7 wind-release hash;
that geometry was already live. Those earlier source changes are included in
the finish commit, alongside this seven-fix release. The seven-fix review patch
separates the new work from that baseline. No public guest or character migration
was needed.

## Changes

- Direction/depth-sorted local and remote melee streaks and persistent buff shells.
- Wider authoritative gate approaches, larger shared mouse/touch selection and routed crossings.
- Arena entry and reward claims at any of the five givers; duplicate levels hidden.
- Public material-source markers for unfinished bring objectives, switching to hand-in destinations.
- Explicit ready state in tracker/folded journal, cross-zone hand-in guidance and a touch-sized destination control.
- Confirmed merchant discard of eligible leftover materials; active quest materials and keys protected.
- Pickup eligibility checked before the loot magnet moves a refused pile.

## Focused proof

- Rust `owner_fixes`: **4 passed**, covering solo/party/full-bag refusal and recovery, wider gates/access/bounce, cross-giver arena return/reward/duplicate prevention, discard persistence/no-gold/keys/active sale refusal.
- Rust `compact_atlas`: **6 passed**, including all 96 walking crossings, directional entry, safe approaches and Bifrost visible-floor arrivals/edges.
- Bounded `tests/owner-fixes-ui.cjs`: **25 passed**, English desktop and Swedish short-screen touch, no browser errors. Artifact: `test-results/driver-Lt3R45/`.
- Bounded real-sprite `tests/melee-depth-ui.cjs`: **49 passed**, five melee families in both directions on local/remote fighters. Artifact: `test-results/driver-mgps99/`. The upward local Swing would cross 395 opaque body pixels; repaired rendering changes zero protected pixels. Cleave would cross 1,417; repaired rendering changes zero.
- Melee mutation restores a single foreground pass and fails the upward body-pixel assertion (397 protected pixels covered).
- Ready-guidance mutation removes hand-in destinations and fails the final-objective remote hand-in assertion.
- All-target Clippy with warnings denied, Rust formatting, changed JavaScript/Python syntax, Swedish generation freshness, **23 locale checks**, release-notes guard and whitespace pass.
- Source export is byte-stable across two material-source generations: 63 bring materials audited, 49 with public sources and 14 intentional secret/gate fallbacks.

Only the reported systems were exercised. No encounter timing, win-rate sweep,
full test suite or gameplay grind was run. The optional DPS panel was closed for
the phone gate fixture so it did not cover the tap point.

## Reproduce

Use `CARGO_TARGET_DIR=/media/raid/valhallasc-data/todo-fixes-target` with
`bash scripts/cargo.sh test owner_fixes -- --nocapture` and
`bash scripts/cargo.sh test compact_atlas -- --nocapture`.

For bounded browser checks set `OWNER_FIXES_CLIENT` to the exported `client/`
and `VALHALLA_BINARY` to the private optimized test binary, then run the named
file through `bash scripts/test-touch-bounded.sh`. `MUTATE=1` selects the melee
mutation; `MUTATE=ready` selects the guidance mutation. Both must fail at the
reported assertion. `OWNER_FIXES_ONLY=touch`/`locale` allow just the short-screen
cases while diagnosing those fixtures.

Release preparation/backup receipt: `test-results/todo-fixes-release.json`.

The isolated release build completed successfully. Its release binary also
passed a private startup, cross-giver arena entry/return and authoritative
no-gold discard probe (`test-results/driver-88KObS/`). The previous live executable
and a consistent SQLite backup are preserved at the path in the release receipt;
backup quick_check is OK, with 35 saved characters and 22 guests. The 47 file zones
are unchanged in count and saved characters are in zones 0–7, so no copy-ID
migration is needed. The service was restarted after the owner explicitly requested deployment.

Reviewable seven-fix diff: `test-results/todo-fixes-1.32.8.patch`; file hashes:
`test-results/todo-fixes-files.json`. This diff excludes the earlier Bifrost work.


## Public verification

All 11 checked public file hashes match local files (the nine changed client
files, plus world.js and zonejourney.js). Public/bridge health are OK; SQLite
quick_check is OK; saved counts remain 35 characters / 22 guests. The new service
has no test flags and no warning/error journal entries after restart. The live,
installed and reviewed binary SHA-256 is
`fbd9558c89ecbe58d7aa3899f29bfd430601386d733964ebe5177866a51c68f5`.
Backup: `deploy/backups/todo-fixes-1.32.8-20261102T075751Z/`, including the previous
executable/client and consistent before/stopped SQLite copies. Detailed receipt:
`test-results/todo-fixes-release.json`.

The staged export matches the validated server/world/client payload. A full
indexed `sync-world.cjs` run, including the new material-source generator, is
byte-stable; indexed Swedish and release-note guards also pass.
