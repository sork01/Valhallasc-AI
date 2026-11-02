# Halloween hunt and unique-name validation — Beta 1.34.0

Candidate: `feat/halloween-hunt`, private RAID checkout
`/media/raid/valhallasc-data/halloween-hunt-work`; no new file zones or shifted
private-copy IDs. Deployment is tracked below after public verification.

- Six focused Rust `halloween` tests: five-fighter admission, rounded-up mixed
  levels (5/10/15/20/26 -> 16), frozen membership, outsiders, hired fighters,
  wipe/reset, personal 1% threshold and both outcomes, duplicate mount/roll
  protection, persistence, shared city claims, midnight and November 10 expiry.
- Three Rust `unique_name` tests: accounts/guests/offline case collisions,
  concurrent requests with one winner, oldest duplicate migration and exact
  character-state preservation through refused/successful required rename.
- Six existing seasonal checks and seven compact-atlas checks pass, preserving
  the four annual errands, calendar edges and all 96 walking crossings.
- Private MCP `halloween_hunt`: ten checks, including real hiring/summon/kill,
  cross-city claim, restart persistence and forged off-season refusal.
  Artifact: `test-results/driver-NmQLAc/report.json`.
- Bounded `tests/halloween-hunt-ui.cjs`: 21 checks, four decorated cities at
  desktop and phone/night, no camp dressing, real level-99 hired summon,
  guidance, daily roll/claim/reset, event removal and required rename/reconnect.
  Artifact: `test-results/driver-zAJnE9`.
- Bounded `tests/nightmare-art-ui.cjs`: 52 real-art checks, saved PixelFlow
  sources, idle/run in eight directions for all five classes and both bodies,
  protected rider pixels, visible mount, elite clips and clear atlas edges.
  Artifact: `test-results/driver-GhxvGm`.
- All-target Clippy with warnings denied, formatting, changed JavaScript/Python
  syntax, release-note guard, Swedish generation freshness and 23 locale checks
  pass. The broader Swedish catalog retains three existing proper-name false
  positives (Laleh/Asha/Veya); no new translation gap was introduced.
- Two sync-world runs are byte-stable: map SHA-256
  `f5889d1de9ce91d4cd07164bffe49f7d28fdbbe55b7dbdc726496857eaab1729`;
  client world SHA-256
  `5222bc80450f6c3bbceffb58824bae58272b386e8917793e3087387a6c8bad09`.

Original sprite sources: sixteen Nightmare mount PixelFlow IDs in
`client/assets/mounts_sprites.txt`; Hollow Rider ID `97c4ae8579dd3197` in
`client/assets/halloween.txt`. Existing mount sources are preserved. The owner
requested a mount picture: `Nightmare Steed preview.png` was uploaded to
[FileDrop](https://gunning.se/filedrop/), stored as `mount_nightmare_run.png`,
with a matching SHA-256 (`13fe4ff2b14546d8` prefix).

No full suites, encounter grind or timing/win-rate sweeps were run. Encounter
health/enrage remain provisional for the owner's own play evaluation. The new
`HALLOWEEN-QUEST-ACHIEVEMENT` / “the Hallowed” suffix request is queued separately
and is not part of this release.

## Deployment

Pending optimized release build, zero-player restart, automatic name migration
and public verification. Live executable and consistent SQLite backup already
saved at `deploy/backups/halloween-hunt-1.34.0-20261102T134217Z`.
