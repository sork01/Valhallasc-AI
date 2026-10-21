# The Black Hour Foundry — level 99

Implementation: `I99F-*`. Public template 44, parent Yearwheel 28, four
private party copies. The source entrance is open after balance and protocol
validation. Public activation and saved-character migration are separate work.

The Yearwheel has a missing hour: beneath its Equinox axle a midnight factory
has been swallowing the time between seasons. Players descend onto a broken
clock's outer rim, cross two enormous forging wheels, then enter the suspended
midnight engine. The map's circular rims, missing teeth and furnace channels
are physical collision, rather than rectangular rooms painted as machinery.
Black iron, violet fire, white-hot cyan coils and four tarnished seasonal seals
connect the foundry to Yearwheel. Keep damage warnings distinct from scenery.

Three large ordinary kinds: Kilnback Hauler (walking furnace quadruped),
Pendulum Breaker (counterweight giant) and Coil Cathedral (levitating industrial
organ). Four three-enemy packs. Bosses: Vark, the Twelve-Ton Bell; Iona,
Mistress of the Dead Current; and The Thirteenth Hour, a colossal hollow clock
engine. Vark and Iona have separate party quest givers; the final boss has none.
All six have original editable PixelFlow atlases and enlarged client scale.
Ordinary visual scale is 1.9 and boss scale 2.6 (on the renderer's 2.1 pixel
base), deliberately large but bounded after real-client inspection. The first
4.2 boss multiplier hid too much floor and was rejected; collision/stats and
the measured fight times are independent of this presentation correction.

Balance acceptance uses level-99 five-person parties (one of each class), the
actual hired-fighter brain, allocated normal attributes, no rebirth/refinement
or orange equipment, and complete ordinary level-95 blue sets (the highest
ordinary blue tier available at level 99). Repeat with complete green sets.
Blue must clear every pack in >=120 seconds, each side boss in >=180 seconds,
and the final in >=300 seconds, without an artificial invulnerability timer.
Green must fail the complete dungeon; tune actual encounter pressure/enrage,
not a rarity access lock. Report each seed, falls and class DPS. Set enrage
from measured raw blue and green outcomes, never an assumed global value.
Purple progression may shorten later farming runs; the minimum times apply
to the specified blue baseline, not every possible player build.

Nullforged: 28 exclusive, level-99 epic catalog pieces, two useful attributes,
the existing purple rarity budget plus the established dungeon bonus. Gear
uses new shapes rather than tinted starter geometry: offset turbine pauldrons,
open clock crowns, hanging heat fins, segmented furnace greaves, a split-tooth
greatblade and counterweight shield, open coil staff, twin ratchet sickles,
industrial censer hammer and forked induction bow. Black/violet metal with
cyan-hot gaps and restrained acid-yellow warning marks. Every equipment drop
from the foundry's ordinary enemies and bosses must be purple Nullforged;
materials, gold and consumables are not equipment. Preserve the global orange
per-kill roll outside the foundry. Quest gear also uses the exclusive epic set.

Music: original dark industrial techno, 4/4 at 132 BPM, D minor, 64 bars.
Distorted kick pulse, metallic percussion, tightly locked bass, Sork-60 synth
motif and pads; Chillhop hats only. Four 16-bar sections develop the same
machine signal, with a natural-ending full render and a seamless game loop.
No FileDrop upload unless requested. Report listening limitations honestly.

Deployment is separate. Appending file zone 44 shifts every old extra dungeon
copy by one; derive the old/new template mapping before migrating a stopped DB.
Never load a saved old copy index as the new template. No production DB edits
or public restart are part of this task.

With the current 45 file zones, the existing extra dungeon copies 44–100 move
to 45–101. The Foundry's extra copies are 102–104, and Arena copies 105–112.
Recheck against the actual running release before any saved-character migration.

## Entry quest: Four Hours Returned (2026-10-21)

The Yearwheel door (`year_blackhour`, `needs_quest: null_keys`) stays shut until the
character has completed **Four Hours Returned** (`null_keys`). Server-side, in
`use_portal`, for every hero separately (a party mate with the quest does not carry
one without it). The quest is given by Sigrun Ashminute (`null_guide`) and can only
be accepted at level 99 (`Quest.min_level`, `minLevel` in map.txt; accepted check in
`quest_action_with_choice`, locked card in `client/quests.js`). Four `bring`
objectives, one shard each; the quest pays 30,000 gold and level-99 XP. `null_entry`
(The Missing Minute) now `requires` it.

Shards are quest items (`kind: material`, `sell: 0`, `items::is_quest_item`: not sold
to a merchant, not traded). Each final boss lets its shard fall, 100%, as a private
ground drop (`world/hour_shards.rs`) for every real hero of the fight who holds the
quest unclaimed and has no such shard in the bag or on the ground:

| Dungeon | Final boss | Shard |
| --- | --- | --- |
| The Blooming Labyrinth | `bloom_heart` | Shard of the Bloomed Hour |
| The Solar Crucible | `solar_heart` | Shard of the Solar Hour |
| The Amber Archive | `amber_memory` | Shard of the Amber Hour |
| The Silent Solstice | `solstice_heart` | Shard of the Silent Hour |

A hero who sells nothing but loses a shard (drops it, banks it) simply earns it again
from the next kill. Generator: `scripts/generate_blackhour.py --open` (items, quest,
door). Tests: `blackhour_door_opens_only_after_the_four_hour_shards_are_handed_in`,
`hour_shards_cannot_be_sold_or_traded`; the older gate test grants the finished
quest first. The map hash below predates this quest.

## Rebuild and focused validation

```sh
python3 scripts/generate_blackhour.py --open   # omit --open to seal a development copy
python3 scripts/gear_levels.py --blackhour-only
python3 scripts/make_blackhour_sprites.py preview
python3 scripts/make_blackhour_sprites.py build # refuses existing sprites
python3 scripts/make_blackhour_sprites.py export
python3 scripts/make_blackhour_sprites.py verify
python3 scripts/instance_gear_jobs.py sync
python3 scripts/build_blackhour_gear.py --preview
python3 scripts/build_blackhour_gear.py         # resumes saved PixelFlow records
node scripts/sync-world.cjs
python3 scripts/build_swedish.py
bash scripts/cargo.sh test blackhour -- --nocapture
BLACKHOUR_SEEDS=4 bash scripts/cargo.sh test blackhour_blue_and_green_encounter_bands -- --ignored --nocapture
bash scripts/cargo.sh build
VALHALLA_BINARY=target/debug/valhalla-server node scripts/test-via-mcp.cjs run blackhour
PLAYWRIGHT_BROWSERS_PATH=/tmp/valhallasc-playwright node tests/blackhour-gear-art.cjs
PLAYWRIGHT_BROWSERS_PATH=/tmp/valhallasc-playwright node tests/blackhour-ui.cjs
REAL_SPRITES=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/valhallasc-playwright node tests/blackhour-ui.cjs
```

Use the documented absolute Node binary and NODE_PATH on this host.
`--mutation-original` on the gear test must reject unchanged starter silhouettes.
`BLACKHOUR_FIGHTS=pack1,null_hour`, `BLACKHOUR_SEEDS`, and `BLACKHOUR_MEASURE=1`
scope calibration without changing production data. `ELITE_POWER_FILE` and
`ENRAGE_FILE` select scratch multiplier tables without rebuilding a test binary.
Keep only one scratch test binary. `generate_blackhour.py --open` is the final
content opening step, followed by sync-world and rebuild; it does not restart
the public service.

`BLACKHOUR_RARITIES=rare|uncommon` selects the blue/green fixture. By default
that fixture retains the real map, attacks, mechanics, loot and hired AI but
simulates only the selected encounter. `BLACKHOUR_FULL_WORLD=1` retains all
world actors as an independent control; existing dungeon harnesses are unchanged.
The test does not substitute god mode, a damage dummy or an invulnerability timer.

Raw blue boss measurements (four compact seeds plus two full-world controls):
Vark 204.0–208.7 s, Iona 228.1–231.3 s, Thirteenth Hour 386.4–571.2 s.
Accepted enrage starts are respectively 224, 248 and 608 seconds, calculated
as `ceil(1.06 * slowest raw blue win) + 2`. The final's mechanics make its
spread wider than the side bosses'. With those starts active, all 14 blue
encounters pass (two seeds for each pack/boss), and all four green final-boss
parties wipe, not merely time out, at 617.2–627.1 s with 22.8–24.6% boss health.

| Blue encounter | Measured clear seconds, enrage active |
| --- | ---: |
| Southwest pack | 124.7–133.7 |
| West flywheel pack | 141.8–144.0 |
| East flywheel pack | 146.0–147.5 |
| Southeast pack | 132.1–155.6 |
| Vark | 204.0–204.7 |
| Iona | 228.1–230.3 |
| Thirteenth Hour | 395.9–555.3 |

Evidence: `test-results/blackhour-blue-raw-compact.log`,
`blackhour-balance-candidate.log` (full-world control),
`blackhour-blue-enrage.log`, and `blackhour-green-enrage.log`. Each row logs
class DPS and falls; victory is the actual kill, never a fall-count heuristic.

Music project: `2802cf4aaf18d145`, *The Shift That Never Ends*. Reopen/render
with `sh scripts/create_blackhour_song.sh --render`; `--mix` reapplies the
measured mix correction. `finish_blackhour_music.py` folds the tail, removes
DC and creates the game loop and natural-ending files. The final decoded loop
is 116.363646 seconds, mono RMS -24.00 dB, peak -6.78 dBFS, zero PCM seam delta.
The score's rendered tracks are non-silent and unclipped. A complete listening
review and the audible loop seam remain unverified.

## Verification

- Two open generator reruns have identical map SHA-256
  `ced9830648b86e2ed99ec4829e2ed9b0ed3f42217db8db0bb427b09885869c2d`.
- Five focused Rust checks pass: physical reachability and stable templates;
  level gate, copy isolation, boss loot, quests and both exits; exclusive epic
  chest equipment plus Cold restart; five-second press warning and its echo;
  all three ordinary kinds' material and exclusive purple equipment through
  the real kill path (one seeded kill each, no farming loop).
- Six 34-frame enemy atlases pass bounds and exact PixelFlow/source round trips.
- 28 Nullforged pieces have 438 editable PixelFlow records, 80 fitted layers and
  21,760 worn frames. All ten hero rigs pass real Chromium composition, shape
  and palette checks; minimum changed outline 35 pixels, minimum two new colors.
  Earlier icon cells/pixels are unchanged (2,051 entries).
  The mutation check rejects reused starter silhouettes with delta zero.
- Chromium gear evidence: `test-results/blackhour-redesign/gear-browser.json`
  and the five `blackhour-<class>-equipped.png` sheets. All six enemy contact
  sheets are in `test-results/eye-below-preview/null_*.png`.
- Private MCP `blackhour` passes, including level rejection, actual gate entry
  and both returns, party-copy isolation, materials and epic boss pools, all
  three quest claims, saved rewards after restart and enemy spacing.
  Report: `test-results/driver-VI55kr/report.json`.
- Stub and real Chromium `blackhour-ui.cjs` pass with actual portal movement,
  fitted Nullforged equipment, all six enemy atlases, bounded giant scale,
  dedicated scenery, exact floor map, readable sign, decoded score, volume,
  mute and Yearwheel score on return. Final screenshot directories:
  `test-results/driver-AJKQc6` (stub), `test-results/driver-96L3ok` (real).
  The earlier stale-client-map and invalid floor-color defects were corrected;
  the test now asserts an open client map and valid independent canvas colors.
- Clippy `--all-targets -- -D warnings`, Python syntax, client JavaScript syntax,
  Swedish translation check and `git diff --check` pass. Tests cover only the
  new content and directly coupled catalog/parent assertions, not full suites.
- Finish checks use a separate index/scratch checkout that excludes concurrent
  orange-gear changes: ten focused Rust checks pass, including the level-99
  capstone/attribute catalog guards; combat calibration is intentionally ignored
  in that quick pass and was measured separately above. Evidence is in
  `test-results/blackhour-finish-index-{rust,clippy,static}.log`.
- Implementation validation preceded the separately requested finish/commit.
  No public server restart, production database change or FileDrop upload was
  performed. Debug builds/private test servers are not a release.
