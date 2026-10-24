# Mercenary movement around walls

Hired fighters used the ordinary player's straight-line goal/target movement.
A nearby wall could therefore stop them forever: the old catch-up warp only
applied beyond 26 tiles and outside the hirer's combat. A ranged fighter could
also stand in attack range with no clear shot and never walk around the wall.

Hired fighters now follow collision-safe waypoints when their direct movement
is blocked, using the existing pursuit grid shared by map template and body
size. Routes check complete segments rather than sampled corner visibility; a tiny
numerical tolerance allows exact wall tangency consistently with movement.
Each fighter caches its route; moving destinations and failed routes
replan at most once a second. Attack targets stay selected while routing.
This applies to formation, enemy approach and the boss brain's movement goals.
Ordinary player movement, autonomous adventurers, escorts and arena opponents
keep their existing behavior.

Formation, hiring and catch-up positions must have a clear connection to the
hirer's floor position. If the normal offset hits or crosses an obstacle, the
hirer's own safe position is used instead. Players already pass through each
other, so standing together is permitted.

If a hired fighter tries to move without making progress for three seconds,
it can catch up beside its hirer once both are out of combat. This also handles
unreachable paths within the old leash. Death, stun, root, frozen status and
Spark Travel must not provide a catch-up shortcut. Existing zone following and
long-distance leash behavior remain; recovery does not resurrect anyone or
return a fallen fighter to an ongoing encounter.

Focused regression checks live in `world::mercs::follow_tests`. They exercise
the real mercenary decisions and authoritative player movement on controlled
wall geometry: all five classes following and approaching enemies, a close
formation slot through a thin wall, unreachable-path recovery, both combat
gates, death/immobilization and safe hiring/zone arrivals. The first two
regression cases fail on the original source.

`tests/merc-follow.cjs` hires a real four-fighter party through the Meeting
Stone offers, then follows snapshots around two existing Skaldholm buildings.
It checks each class takes the detour, nobody uses a recovery warp on a
reachable route, the price is correct and only the human is counted online.
Run with an explicit `VALHALLA_BINARY` and the main checkout's `node_modules`
on `NODE_PATH` from the isolated worktree. No encounter timing or win-rate
checks are involved.

Validation (2026-10-24): seven focused Rust tests and 15 private real-protocol
checks pass against the immutable release candidate, including actual hiring
and both building detours. Private artifact:
`.tools/merc-follow-worktree/test-results/driver-GkVcSK`. Clippy with warnings
denied, formatting, changed JavaScript syntax and diff whitespace checks pass.

Deployed 2026-10-24 with nobody online (source `e679177`). Rollback binary and
consistent pre-build/stopped database snapshots:
`deploy/backups/merc-follow-20261024T102629Z/`. No client/world changes or
zone/schema migration. Public and bridge health pass; running binary matches
the privately tested candidate; no test flags or warning/error journal entries.
SQLite `quick_check` passes, counts unchanged at 25 characters / 14 guests.
Release SHA-256:
`669d959add44fab536f15ac74bda17c39e0780d8ce4b327671bc053a7aadfcb1`.
