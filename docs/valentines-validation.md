# Valentine's candidate validation — 2026-11-03

Private candidate **Beta 1.36.0**, branch `feat/valentines`, based on `a5af4c4`
(main at implementation start). Main's separately requested mailbox backlog
`0635d11` is preserved in this candidate's TODO. This feature is **not deployed**.
No production binary/database/client files have been changed. No new zones,
private-copy ID shift, schema migration, public guest or encounter balance sweep.

Rules are in [valentines-event.md](valentines-event.md). All five VALENTINE TODO
IDs are implemented. Easter and mailbox tasks remain open. New Year remains a
separate candidate: it also uses Beta 1.36.0. Reconcile the release version/notes
and shared seasonal integration if combining those branches for publication.

## Focused server and protocol checks

Eight distinct `world::valentines_tests` checks pass:

- February 9/10 and February 18/19 Stockholm boundaries; exact four-city scope,
  four annual errands, single dormant elite and clear/reachable shrine.
- Frozen highest level and participant IDs; outsider damage refusal.
- Exactly five living, online, nearby, dismounted, calm fighters at admission.
- Guaranteed unicorn **on quest claim**, full-bag safety, hires excluded, existing
  selected horse preserved, duplicate claim/ownership safety and serialized save.
- Shared city daily allowance, next-day acceptance and repeated mount ownership.
- Dead, distant, disconnected and unaccepted participants excluded from kill credit.
- Wipe, full disconnect, leash, timeout and season expiry retire without rewards;
  unfinished quests removed, permanent mount retained and off-season summon refused.
- Accepted/ready and four-claimed sets fail; five claimed across years grant exactly
  one 25-point Lovefool; selection/points survive real rebirth and JSON reload.
  Saved Sork name is unchanged; prefix metadata and legacy Merry suffix coexist.

The catalog's focused positive-points/atlas/reward check also passes: **105
achievements, 2,275 maximum points, nine titles**. One initial fixture expected
only 25 total new points; it was corrected because the fifth quest simultaneously
earns the existing 5-point quest milestone. Only that corrected check was rerun.
No balance/timing controls, grinding or unrelated Rust suite was run.

Private MCP `valentines`: **10 checks pass**, including real hired-fighter gather
and summon, kill-to-ready, guaranteed mount on cross-city claim, daily refusal,
server restart, expiry and enemy spacing. Evidence:
`test-results/driver-EDN3DN/report.json`.

## Bounded browser checks

`tests/valentines-ui.cjs`: **34 checks pass**, real sprites, 1440×960 and 844×390,
reduced motion. All four errands use their actual talk/visit paths; their annual
rewards and repeat refusal pass. Actual shrine button/hired crew/highest scaling,
quest marker, claim reward/unicorn, normal achievement toast, exact `Lovefool Sork`
HUD, phone title selector, next-day reset, expiry/reconnect permanence, existing
suffix compatibility, a second real browser's remote nameplate and Swedish pass.
No browser errors. Evidence and screenshots:
`test-results/driver-jr36Kg/summary.json` and sibling PNGs.

`tests/valentines-art-ui.cjs`: **65 checks pass**, real PixelFlow exports under the
1536 MiB / 100% CPU bounded harness. All ten class/body rigs, eight distinct
facings and both gaits show the unicorn and preserve every protected rider head
pixel through production depth composition. All 16 saved source IDs are present.
Four real city NPC accessory views, full night/daylight/reduced-motion views,
no dressing/costume on the smaller Rimeveil refuge, five elite clips and no frame
edge clipping pass. No browser errors. Evidence/contact sheets/native canvas
city captures: `test-results/driver-rsLsyp/`.

## Artwork and generation

Original rose-armoured thorn guardian **Briarheart**, PixelFlow source
`72a1b9c1d1a73a37`, 34 frames, five clips, 96×96, anchor (48,90).
Original **Roseheart Unicorn** uses 16 saved PixelFlow sprites: eight directions,
4 idle + 8 forward-run frames per direction (96 frames total), 160×160 colour and
depth atlases. Pearl-pink coat, rose-red mane/tail, golden horn/hooves and sculpted
heart breastplate; existing saddle/depth rig. All previous mount source IDs and
metadata are unchanged. Its manifest has raise 25/cut 34 and existing 160% speed.
No FileDrop upload was requested or performed.

City dressing counts: Alderhaven 23, Skaldholm 544, Nacrehold 795, Asterion 749.
Heart/rose/ribbon/light props reuse safe four-city placement and native cached
Canvas renderers. NPC rose accessories follow actual animated head/collar sockets.
The parsed map differs only in festival quests/offers/decor and the Rimeveil
shrine/dormant spawn/ritual metadata. Existing collision, routes, portals, ordinary
spawns, city geometry and zone IDs are identical. Histogram diff is additions only.

After initial ordering convergence, consecutive full sync-world outputs are
byte-stable (the stored comparison includes all generated outputs):

- `world/map.txt`: `24ad319f6c9dee1dab582862396826e9c4fd394161d5a1b045eb5625c49031ba`
- `world/seasons.txt`: `fbd875592affd1dc93d80b661cdcd6b81f5455ea8ed51218b1907bf57f67df79`
- `client/world.js`: `3b59dbdad2e780c5fc75b912feded33d34db119605912df9fe0eb1764b17ba22`
- `client/items.js`: `f6f3fc6f44690d1879945ffa5655434f25dc04d0aad7b593c17ea05c098e4947`
- `client/cathedral.js`: `ce61cf5d09db4033d5a4e9fd13280e863a2c1dfb07e740b207e55b740689c68b`

## Other gates and reproduction

All-target Clippy with warnings denied, cargo formatting, changed-JavaScript
syntax, Python syntax, hand-written Swedish generation, 23 Locale.translate checks
and release-note guard pass. The historical house-sign removal note's reason was
changed from “to keep” to “so” to satisfy the existing removal-reason guard.
No broader Swedish/browser/full Rust suites were run.

The private optimized binary is built with:
`CARGO_TARGET_DIR=/media/raid/valhallasc-data/todo-fixes-target bash scripts/cargo.sh build --profile test`.
This is a shared scratch target; rebuild it from the intended branch before reuse.
Use its absolute `debug/valhalla-server` path in `VALHALLA_BINARY`. Protocol check:
`node scripts/test-via-mcp.cjs run valentines`. UI/art checks use respectively
`bash scripts/test-touch-bounded.sh tests/valentines-ui.cjs` and
`bash scripts/test-touch-bounded.sh tests/valentines-art-ui.cjs`, with the normal
project Node/NODE_PATH setup. Preserve the memory/CPU limits.

The final binary is rebuilt against the converged map before committing. Public
installation/release verification is outside this private candidate; retain the
normal zero-human backup/build/install/health/hash/SQLite checks when publishing.
Owner retains encounter timing and win-rate evaluation.

Final private optimized binary SHA-256: `9b8dc5ce2cd2178699e374023a642a0b7bad1bef7c0d2982f4a8c5baa202b313`.
