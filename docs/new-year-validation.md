# New Year — Beta 1.36.0 validation

Implementation is in `/media/raid/valhallasc-data/newyear-work`, branch
`feat/new-year`, based on `de032ea`. It remains unmerged and undeployed.
The public site remains unchanged. Rules: [new-year-event.md](new-year-event.md).

## Scope and source provenance

Exactly one shared `newyear_hunt`, December 29–January 2 on the authoritative
Stockholm calendar. Five-fighter highest-level encounter, personal 5% rocket
roll/day and a 25-point claimed-quest achievement. No geography, existing
NPCs, ordinary spawns, old quests, zone indices or private-copy IDs change.
A structural comparison against the base map passes after stripping only
New Year additions. No schema migration or offline character backfill.

Original Starfire Rocketeer: PixelFlow **47efe29e4ebe94c0**, 34 frames/five clips.
Starflight Rocket: 16 saved PixelFlow sources covering eight directions and
idle/run, all IDs in `client/assets/mounts_sprites.txt`. Existing source IDs
are preserved; 96 color/depth frames have valid depth and clear borders.
Both saved exports were visually inspected. No new music was requested.

## Focused checks

- Data/art invariant check passes: one quest, XP/ID/giver rules, complete saved
  elite/mount frames, valid depth and no clipped sprite borders.
- A second full generator/sync pass is byte-identical for map, registry and
  client world. Hashes: `test-results/newyear-generator-stability.json`.
- Swedish generation/freshness passes. Release notes cover Beta 1.36.0.
  The existing 1.35.4 removal sentence was reworded with “so” to satisfy its
  existing explicit-reason guard; its meaning is unchanged.
- **10 focused Rust checks pass**: nine New Year tests and the achievement
  catalog count/rewards check. Eight New Year tests passed on the first run;
  only the remaining history test was rerun after accounting for the existing
  first-quest achievement, which also grants five points. New Year itself
  grants exactly 25; repeats, prior-year claims, abandonment and save history
  are covered. New Year rocket speed is 1.6 like every existing mount.
- **10 real MCP protocol checks pass**, including four hired fighters, shared
  cross-city daily reward, personal attempt, server restart and forged expired
  summon rejection: `test-results/driver-Gg4v3Q/report.json`.
- **20 distinct bounded real-client checks pass** across date boundaries,
  exactly one quest, actual four-city burst density/pixels/budget, static
  reduced motion, every world zone, quest marker, hired summon UI, ready versus
  claimed achievement, shared daily limits, year rollover, expiry, reconnect
  and Swedish. Evidence: `newyear-ui.log` (first three boundary checks),
  `newyear-ui-final.log` (eight visual/hunt checks), and
  `newyear-ui-rewards.log` (remaining nine). Fixture corrections allowed actual
  collision-safe plaza displacements and initialized the achievement reply
  slot before polling. Only unfinished portions resumed; gameplay was unchanged.
- **51 real-art checks pass** for all ten class/body rigs, eight facings and
  both gaits, distinct rendered mounts and protected rider head pixels after
  depth composition: `test-results/newyear-art-ui.log`, `driver-lLLEtW`.
  Native male Warrior/female Mage sheets and saved elite/rocket previews
  were visually inspected. Art/preview browser jobs ran sequentially under
  the repository's 1.5 GiB / one-core scope.
- `cargo clippy --all-targets --profile test -- -D warnings`, formatting,
  changed JavaScript/Python syntax, Swedish freshness and release-note guard
  pass. Private optimized binary built with `cargo build --profile test`;
  Cargo target `/media/raid/valhallasc-data/todo-fixes-target`.
- No full suites, grinding or encounter timing/win-rate sweeps.

## Requested FileDrop previews

All ten images were uploaded at the owner’s explicit request to Sork’s
[FileDrop](https://gunning.se/filedrop/), with source/destination SHA-256 matches.
Four-city/outdoor/phone images and achievement/mounted images are native
private-client captures; elite and eight-direction mount sheets use the
actual exported PixelFlow artwork.

| Image | SHA-256 |
| --- | --- |
| `valhallasc-newyear-alderhaven.png` | `1beb73935a0c3145902b1a95919a78ee9adff8dc3a00f4deffd075b6c737b185` |
| `valhallasc-newyear-skaldholm.png` | `ab7f0e96b816267aec16c3a73c0f1868ac719569b6c1543036dcef66a8bc5bae` |
| `valhallasc-newyear-nacrehold.png` | `555143a068fca8204b3428ca1d62f9ff9d4ea14c0d2cbd6312c42bda0829d0bb` |
| `valhallasc-newyear-asterion.png` | `137760e89424ecebd937c67dd7fedd97253fbbd3133392e181f263313d84272c` |
| `valhallasc-newyear-outdoors.png` | `b625153e3cab5dfaa4612a736255258025a945c5d0bc342a225c923961b9b044` |
| `valhallasc-newyear-phone.png` | `45026d2c799630702bb4376cc35f06714f79a47bd06c7ff19a5c0a78c1b66901` |
| `valhallasc-newyear-rocketeer.png` | `23583b1f70d09786335084baf5109e6386a487b7140772e3fe1e9f45c3d52d22` |
| `valhallasc-newyear-rocket-art.png` | `c8fe787b23e24d7c7931a64fc5b074bceba394966830c5f11a02b8d43c21b1e8` |
| `valhallasc-newyear-achievement.png` | `ec2c885e1e82b56c552d1113745e263f689b32fc9f28a94b6eb6ec28b6fd006c` |
| `valhallasc-newyear-rocket.png` | `7181f772dc5875b6fffb07b54a0f3da4ecb7900c458a381ba00795f8091508ab` |

Full local receipts: `test-results/newyear-filedrop.json`.

## Publication

Source is preserved on `feat/new-year`; the main backlog records its status.
Deployment awaits the owner’s request. Client files remain private so new quests/mounts
cannot be advertised by the public client before the matching server is installed.

Private optimized binary SHA-256: `2c906c5c5de990acde431517abc9044ddad682483e647bdc372b82b89c1cb529`.
