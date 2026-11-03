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
No FileDrop upload was requested during initial implementation. The owner subsequently requested uploads; see the receipt below.

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

## Requested FileDrop screenshots — 2026-11-03

The owner requested these uploads after implementation. All 23 PNGs are in
[Sork’s FileDrop](https://gunning.se/filedrop/), with source/destination SHA-256
and metadata/size matches. Four cities each have daylight, night and phone views;
the set also includes the summoned Briarheart and ten class/body unicorn rider
contact sheets. Full local receipt: `test-results/valentines-filedrop.json`.

| File | SHA-256 |
| --- | --- |
| `valhallasc-valentine-alderhaven-day.png` | `ca34e027d06066f914976a9f8cf1b82be99be8a25d606d048db5751cfda3dae2` |
| `valhallasc-valentine-alderhaven-night.png` | `17970bf27fd8ca3f6eda2fb44bc12243d0223f1efc20d614acaa7543030c9d5a` |
| `valhallasc-valentine-alderhaven-phone.png` | `9d4e9473ebb5203efe7840b98d326cf4ef5453f6aa0d875b6078d05cd28fa6e4` |
| `valhallasc-valentine-skaldholm-day.png` | `8cc2662eb3826668afb33aa100b4450a3855715dd62e9cb616a754e7d83eac06` |
| `valhallasc-valentine-skaldholm-night.png` | `04e52ab07f8da53c2faf7f6272947ee43620ff1bd65b45c02bc9a10b2c8f7cec` |
| `valhallasc-valentine-skaldholm-phone.png` | `ad71f7e0671774ab5fa70fc3b60528d468ee128fd66af924884b148008619eb6` |
| `valhallasc-valentine-nacrehold-day.png` | `bccbc1eea86dacd464e9e20fad7ce99b460ad087d0fd5b505541dfef5b7f2b6f` |
| `valhallasc-valentine-nacrehold-night.png` | `ce7e5df169e9294d1e5d23e6e292bfa591882404589bf87298b839546d7eda4c` |
| `valhallasc-valentine-nacrehold-phone.png` | `c78b5376027e7bba980467ba639437a13121bc31afbba7a227953011a450d0ad` |
| `valhallasc-valentine-asterion-day.png` | `2ea6e57577567322e7513519a9667389f91aa1f505e569cdcf72e6972503384a` |
| `valhallasc-valentine-asterion-night.png` | `0fdb520fd734bc53649d48e88af7ffd40d09a3f6fedde34181c85e49ec1250a9` |
| `valhallasc-valentine-asterion-phone.png` | `6b6f466bb6967d4299fc30f6aaec777153dc0e4ffeb556126ab278f52ccba504` |
| `valhallasc-valentine-briarheart.png` | `3fb6c3237deb6eb5d5910f7ca14a5c6ef4912072aa1e79e19ad3949e52303d85` |
| `valhallasc-valentine-unicorn-warrior-male.png` | `4983c3cc92e6c72e6909bb5653ace455b8aeb0d58267c4325068334d7be7ea5a` |
| `valhallasc-valentine-unicorn-warrior-female.png` | `c8540aa7bbe0a43cfa1a92df5571ff31261659a8a28b88cbf873046a591d3193` |
| `valhallasc-valentine-unicorn-mage-male.png` | `c80f95ddfceb709e646c1cafd8405d6ae2daa6e4ebb17c7d4abd5b38673091d9` |
| `valhallasc-valentine-unicorn-mage-female.png` | `62ebc65a771ed031aa9510410bc03d62a12f81855156e8a66c17c8453cf27729` |
| `valhallasc-valentine-unicorn-assassin-male.png` | `e64592d9cc6103f5782c5ce6cddbd3e4beb4bc15d067f490aaddf4fdbfd29fba` |
| `valhallasc-valentine-unicorn-assassin-female.png` | `f87577969aaeedda3bb0d81542da549ce8ac88e343781458724687ed4c0addbe` |
| `valhallasc-valentine-unicorn-priest-male.png` | `3919ac8ba453ebd189b5fff05a8d74dfcf375634a9bfef19d48b9016c0ef4eca` |
| `valhallasc-valentine-unicorn-priest-female.png` | `77574cfe4ff79a707aba15d5c985065e9727ba1a8ef8b86b1198d321c431ce8d` |
| `valhallasc-valentine-unicorn-hunter-male.png` | `ce946b821395acd1f94037339b9ad2af5740032fdc6f704d0017de3dd72d767a` |
| `valhallasc-valentine-unicorn-hunter-female.png` | `d98c4314d11178d7fb7cb3aaf54a132957e26057fa4f1508a5abdcc200502453` |
