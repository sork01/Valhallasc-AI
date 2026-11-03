# Easter candidate validation — 2026-11-03

Independent **Beta 1.36.0** candidate, branch `feat/easter`, based on main
`3072bb4`. Worktree `/media/raid/valhallasc-data/easter-work`. Not merged or
deployed. New Year and Valentine remain separate candidates also labelled
1.36.0; reconcile their seasonal arrays/hooks, shared clearing suppression,
catalog totals and release version/notes before combining for publication.

Rules: [easter-event.md](easter-event.md). No new zones/copy-ID shift, schema
migration, production client/binary/database changes, public guests, grinding,
full suites or encounter balance/timing sweeps. Owner retains timing/win rates.

## Server and protocol

13 focused Easter Rust checks pass, plus the focused achievement catalog check:

- Meeus/Jones/Butcher matches 12 independently fetched USNO dates, including
  earliest/latest bounds, correction years and leap centuries. Provenance and
  independent zoneinfo boundary fixtures: easter-calendar-reference.txt.
- Exact start/last active date/expiry, March–April–May rollover, a 23-hour
  Stockholm day, fixed seasons and synthetic cross-year registry behavior.
- Four-city bounds, four annual errands, one dormant elite, clear/reachable
  landmark; five living nearby online dismounted calm fighters including hires.
- Highest fighter level and participant IDs freeze; outsiders cannot damage.
- Independent deterministic 5% successes and failures, exact threshold, full
  bags, unchanged selected mount, repeat/abandon protection and serialized ledger.
- Hires never roll; dead/distant/disconnected/unaccepted participants lack credit.
- Shared host daily allowance/reset; wipe, disconnect, leash, timeout and expiry
  retire without reward; off-season summon refusal and permanent ownership.
- Accepted/ready and four-claimed sets fail; all five claimed across years award
  one 25-point Eggstraordinary Easter. Selection/rewards survive actual rebirth,
  serialization and expiry; saved Sork name and Merry suffix remain unchanged.

The catalog is 105 achievements / 2,275 maximum points / nine titles. The fifth
quest also earns the pre-existing five-quest 5-point milestone where applicable.

Private MCP `easter`: 10 checks pass through actual handshake, real hired-fighter
admission/summon, kill credit and attempt consumption, cross-city reward/daily
refusal, restart, expiry and spacing. Evidence: `test-results/driver-cQyx5J/report.json`.
The first attempt exposed the private driver's old mount enum; `springtide` was
added to both give/select schemas and the scenario passed. Mount ownership is
explicitly seeded only for protocol/UI persistence; Rust tests verify actual
random reward outcomes without grinding.

## Artwork and world generation

Original Bloomwarden: PixelFlow `a8caa30825f18752`, 34 frames, five clips,
96×96, anchor (48,90). Egg-armoured moss/blossom guardian with flower sceptre.
Springtide Bunny: 16 saved PixelFlow sources in mounts_sprites.txt, eight facings,
4 idle/8 hopping-run frames per direction, colour/depth 160×160 atlases; raise
25/cut34 and existing 160% walking speed. White rabbit, pastel-pink ears, floral
saddle, woven basket of decorated eggs. All seven existing mount entries and
source IDs remain byte-for-byte equivalent.

Native cached city eggs/baskets/flowers/pastel ribbons/light props: Alderhaven
23, Skaldholm 544, Nacrehold 795, Asterion 749. NPC rabbit-ear headbands and flower
ribbons use actual animated head/collar sockets. Elevated decorations use facade
projection. Existing routes/entrances/services, collision, geometry, ordinary
spawns and zones are unchanged: parsed world audit has zero non-Easter semantic
differences (`test-results/easter-world-audit.json`). No new quest items.

Owning generator easter_event.py follows Christmas in seasonal_cities/sync-world;
remove the dormant Bloomwarden before Christmas validates their non-overlapping
shared clearing. After initial ordering convergence, consecutive full sync outputs
are byte-stable (`test-results/easter-sync.json`). No generated file hand-edits.

Final private optimized binary SHA-256:
`4ab78d9b9826463aa145d0e6ac88a970c1f0074ec0adde087b0050ad89545e84`.
Build: `CARGO_TARGET_DIR=/media/raid/valhallasc-data/todo-fixes-target bash scripts/cargo.sh build --profile test`.
This target is shared scratch storage; rebuild the intended branch before reuse.

## Bounded browser checks

`tests/easter-ui.cjs`: **34 checks pass**, real sprites at 1440×960 and 844×390.
Actual talk/visit errands and annual refusal, shared daily offer/marker, real
hired-fighter summon button, attempt consumption and cross-city claim, normal
achievement toast, exact `Sork the Springbringer`, phone title selector, daily
reset, expiry/reconnect, second-browser remote nameplate and Swedish pass.
No browser errors. Evidence: `test-results/driver-EN4IFA/summary.json`.

`tests/easter-art-ui.cjs`: **65 checks pass**. All ten class/body rigs, eight
facings and idle/run show the bunny and preserve every protected rider head
pixel through production depth composition. All 16 source IDs, four real NPC
accessory views, daylight/night/reduced motion, no dressing in the small Rimeveil
refuge, all five elite clips and no clipped frame edges pass. No browser errors.
Evidence/contact sheets/native city canvases: `test-results/driver-b0KhaL/`.

Both suites ran sequentially under the 1536 MiB / 100% CPU / no-swap / ten-minute
harness. `MUTATE=decor` removes Easter scenery through a scoped browser route;
it fails the intended real-canvas draw assertion after the first errand. Shared
files and production assets are never swapped for mutation checks.

## Requested FileDrop pictures

All **24 PNGs** are in [Sork’s FileDrop](https://gunning.se/filedrop/). Four cities
have daylight, night and phone views (12); ten bunny class/body rider sheets,
a summoned encounter picture and a clear five-clip Bloomwarden gallery make up
the rest. Source/destination SHA-256, size, MIME and original-name metadata match.
The battle screenshot contains normal combat spell effects; the separate clip
gallery gives an unobstructed view of the guardian. Full local receipt:
`test-results/easter-filedrop.json`.


| File | SHA-256 |
| --- | --- |
| `valhallasc-easter-alderhaven-day.png` | `9c9498f471df2cbfc3d164ccb16730a8450bebb7480e833797498317c619af3b` |
| `valhallasc-easter-alderhaven-night.png` | `a810ba265b072fcb4eff0b73b8b62448fecc659989fac3d853b787ce99a381bb` |
| `valhallasc-easter-alderhaven-phone.png` | `24f0b4c5a3989c02dae7a8e5e878f361d7cee8fa223bc94e9ebbf824b66ee503` |
| `valhallasc-easter-skaldholm-day.png` | `8b5670b0d9d5a88065bcf9eb4fdd34409c6e7c7b1b40c0bbd8245e78ea9a8451` |
| `valhallasc-easter-skaldholm-night.png` | `4b0a80684c78847c6c04e514b728ee250492962a87ff012fc3003792875b7095` |
| `valhallasc-easter-skaldholm-phone.png` | `203ff6052716d4a7f690cc948523977e5467269e858123af608ad6b0835f375d` |
| `valhallasc-easter-nacrehold-day.png` | `4cf88f0c79ab719e037a553b43de58ab7698e98eecb3afc6d21e39c404e2f433` |
| `valhallasc-easter-nacrehold-night.png` | `bab2c68232d6fdd71f7e12d522064d76becd8676842832cd86cf72ccf8e61cef` |
| `valhallasc-easter-nacrehold-phone.png` | `a491863a4a95498f37d128aede0e6c277275569232110cc8788f3e8c719e1506` |
| `valhallasc-easter-asterion-day.png` | `c4da170f41eec9b9f893320396d87e5e0cd3f95514e98b61da8ad7d5f7eaf630` |
| `valhallasc-easter-asterion-night.png` | `addcb515f305b5de4755f6f236910c175f643d50d7a3d5b8aa02cabb324bfc97` |
| `valhallasc-easter-asterion-phone.png` | `dab299a17366711edf3995b11084fd69a67afe143bbc651808d6ea093c87d941` |
| `valhallasc-easter-bloomwarden.png` | `667a150844589acd0c93160ef9086811c5e84bd4f25c596e7eaf597d953c1aaf` |
| `valhallasc-easter-bunny-warrior-male.png` | `d72ce16850d03aa06d39f46d321c8b0d4a7373e4930f90eedab1a9ea5d6c126b` |
| `valhallasc-easter-bunny-warrior-female.png` | `86ba3dfe8bf5550e7987ea9d815218b43ae48d2a3cb1e0f7f75636c8b180099f` |
| `valhallasc-easter-bunny-mage-male.png` | `e1afdabab7bf907fb8b836d80e76af0d5c3945d777d4887e7de50d5c6e5eada7` |
| `valhallasc-easter-bunny-mage-female.png` | `dd95e082e5d8e6f24efd8f86b2a3ec6fbba7e9f2cdb2c81d19778b0abc2825df` |
| `valhallasc-easter-bunny-assassin-male.png` | `a425fc373b9f712d69f1766f4305b84b0ea9cadc965a7c164408d4b26d2a8e6d` |
| `valhallasc-easter-bunny-assassin-female.png` | `c4b0e4f3baadc507ece5901bb2017e9d0ea2b7af2f11db3eb13c6e187ced3d0a` |
| `valhallasc-easter-bunny-priest-male.png` | `2de3c6154b0d6f31404a4f67942c737a2689ce51909a797da87c729132d7c455` |
| `valhallasc-easter-bunny-priest-female.png` | `d71e12adfc9f2d73a26d2cce747c019bc375447f710820a4e7d4af08ae5e3a79` |
| `valhallasc-easter-bunny-hunter-male.png` | `564ba283210a9b6f25e06cf3d8fa7fafe0bff071aa768ce88c559b19d24b0f50` |
| `valhallasc-easter-bunny-hunter-female.png` | `7e605c50c25fdf247a9c37ceced78f7e4adc05a1b3bd00e442a51560a63c1ed6` |
| `valhallasc-easter-bloomwarden-clips.png` | `568ebc9a6cab09085e3a98934ff8262fa1cab2677effffa3e59441a51a1de6c3` |

## Other gates

JavaScript/Python syntax, cargo formatting, hand-written Swedish generation and
release-note validation pass. The existing Christmas UI fixture's catalog maximum
is updated to 2,275; that unrelated suite was not rerun. The historical residential
sign removal note uses “so” to satisfy the existing removal-reason guard. No full
Rust/browser suites or balance controls were run. All-target Clippy passes with
warnings denied under a one-CPU/no-swap scope.
