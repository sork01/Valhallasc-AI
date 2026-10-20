# Nornroot Barrow — level 25

The first of the three requested progression dungeons. Its entrance is in
**Wyrdwood (zone 6), at (84, 66)**, on the road below the Norn Stones. The return
arrival is (84, 71), outside the entrance disc. Runa Threadreader and Egil
Spindlekeeper stand beside the approach; Runa offers the existing five-class
mercenary service. Public zone **41** is appended after the Arena (40).

The 112 × 112 private interior has four party copies, a level-25 access gate
and a recommended party size of five. An amber burial court and a violet thread
court flank the central spindle gallery. The northern hall holds a stone loom
and the Unwritten King. Ida, the Last Witness, waits beside the safe arrival for the entry quest. An entrance exit always works; the northern exit opens
after all three guardians fall, even if they are killed out of order.

## Encounters and rewards

Four packs each contain a Graveamber Scarab, Threadbound Hound and ranged
Spindle Shade. Arn, the Amber Doorward, guards the west court; Vessa, Keeper of
Threads, is anchored to the spindle in the east court; the Unwritten King waits at the loom. Arn and
Vessa each have a party quest at a separate giver. The king has no quest and
awards the final two guaranteed blue pieces. Each ordinary kind and guardian
also has its own material. Combat, kill credit and rewards use the existing
authoritative dungeon systems.

The king's **Spindle Snare** shows a red ring for five seconds. Its middle and
the ground beyond its outer edge are safe. Below 35% health the ring is wider
and repeats three seconds later. The sign before the northern hall (currently at 47.5, 41.5) explains both safe routes
and shows an actual ring. Fallen fighters stay down through the fight.

The 28 exclusive **Fatewoven** blue pieces require level 25 and have 15% more
base attack/defense than that level's ordinary blue set. The first two bosses
cover all seven non-chest categories; the king drops one chest and one piece
from the other categories. Two boss quests award class-neutral pants and a ring.
`scripts/gear_levels.py` generates the pieces; `scripts/quest_gear_rewards.py`
preserves the fixed rewards. Class set bonuses live in `docs/set-bonuses.md`;
the eight-piece **Second thread** heals the wearer for 4% maximum health, with
the existing 20-second signature timer.

## Assets and music

`client/nornrootart.js` now draws a fossil-root burial loom: tangled root walls,
continuous end-grain rings, woven walkways, amber cocoon burials and a great
three-weight root loom. This replaces the first pass of purple stone slabs. The original six cel enemies
have 96 × 96 frames, anchor (48, 90) and 34 editable PixelFlow frames each.
Their IDs and atlas metadata are merged into `client/assets/cathedral.txt`;
existing dungeon sprites are retained. Source art is in
`scripts/make_nornroot_sprites.py` and `scripts/eye_below_barrow_*_raw.npz`
(the latter prefix comes from the shared exporter).

**Threads Without a King** is an original 24-bar 5/4 chamber procession at
88 BPM in D minor, with a 3+2 bass/drum pulse. A quiet harpsichord ostinato and
wooden percussion carry the motif, with Sork-60 Mellow Pad harmony, wood bass
and the Axiom-8 Chillhop kit. There is no foreground lead or hi-hat. Four
six-bar sections change the harmony and ostinato; A7's C-sharp is deliberate.
Editable dybase2 project: `3f288c16e36ca5c2` (owner `codex`),
[open score](https://gunning.se/dybase2/?project=3f288c16e36ca5c2).

The 128 kbps game loop is 81.818 seconds, with its tail folded back, 25 Hz
high-pass, decoded mono RMS −24.00 dB and peak −3.85 dBFS. The natural-ending
MP3 stays in `test-results/nornroot/Threads Without a King.mp3`; the owner
requested and received the music and artwork in FileDrop. Source/grid and codec checks passed; a full listening
review was unavailable, so the musical timing and audible seam are unverified.

## Rebuild and focused checks

```sh
python3 scripts/generate_nornroot.py
python3 scripts/gear_levels.py
node scripts/sync-world.cjs
python3 scripts/build_swedish.py
bash scripts/cargo.sh build

python3 scripts/make_nornroot_sprites.py preview
python3 scripts/make_nornroot_sprites.py build
python3 scripts/make_nornroot_sprites.py export
python3 scripts/make_nornroot_sprites.py verify
# Use export to preserve PixelFlow edits. --replace discards only these new sprites.

bash scripts/render_nornroot_song.sh
python3 scripts/finish_nornroot_music.py

bash scripts/cargo.sh test nornroot -- --nocapture
VALHALLA_BINARY=target/debug/valhalla-server node scripts/test-via-mcp.cjs run nornroot
PLAYWRIGHT_BROWSERS_PATH=/tmp/valhallasc-playwright node tests/nornroot-ui.cjs
REAL_SPRITES=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/valhallasc-playwright node tests/nornroot-ui.cjs
```

Node requires the project's documented Node binary and `NODE_PATH`. The
Wyrdwood generator reapplies the entrance after rebuilding the parent. Two
successive Nornroot generator runs must retain an identical map hash. Checks
and screenshots are recorded under `test-results/nornroot` and the private
test world's artifact folder.

## Deployment and saved private zones

Implementation and private validation do not restart the public service.
Client files in this checkout are served from disk immediately. Another session
committed the base Nornroot implementation in `b82a755` during this work. The
final pack damage and side-guardian enrage adjustments require a server release;
this task does not restart the public service.

Existing public IDs 0–40 stay fixed. The Arena's public map now occupies its
own inert runtime slot at 40 instead of temporarily borrowing the first
Undervault copy's index. The new dungeon is slot 41. Consequently old extra
dungeon copies **40–87 move to 42–89**; Nornroot's extra copies occupy 90–92;
the eight transient Arena copies move from 88–95 to 93–100. Arena matchmaking
continues to report public zone 40.

Before deployment, recheck saved character zones in a consistent stopped DB
copy. Move saved characters in old private copy IDs ≥40 to a safe public hub
(Skaldholm zone 4, x104.2 y125.4), or map old dungeon copy IDs by +2. Never let
an old copy index load as the new dungeon. A read-only check during development
found no saved characters in IDs ≥40; repeat at deployment because players
may have entered since. No live character database was modified.


## Current private-copy layout with Shattered Span

The other session also added Shattered Span as public zone 42. With both new
file zones present, the first extra dungeon copy is **43**. Old pre-Nornroot
extra dungeon copies 40–87 therefore map to 43–90 (+3); Nornroot's extra copies
are 91–93, Shattered Span's are 94–96, and Arena copies are 97–104. The +2
mapping above describes Nornroot on its own and must not be used for a release
that includes both dungeons. Always derive the mapping from the actual old and
new world files, and inspect the stopped DB before migration.


## Focused validation, 2026-10-20

- Five Nornroot Rust tests pass: actual collision/reachability, level gate and party copies, kill/loot/clear ordering, Fatewoven healing and its timer, and the ring warning/safe middle.
- Private MCP scenario `nornroot` passes 17 checks, including both exits, three quests, loot and a restart with saved rewards (`test-results/driver-jzMgmP/report.json`).
- All four packs kill each of the five lone classes: 20 fights, one seed. The hired five clear each pack in 13–15 seconds without deaths. Ordinary pack damage is multiplied by 5 in `world/elite-power.txt`.
- All three guardians kill each lone class in green and purple gear: 30 fights, one seed, through the actual fight ending. The test's old 30-second linear projection could stop before an enrage; boss checks now run to completion.
- Arn's hired-five win is 59 seconds; Vessa's is 82 seconds (one seed each). Their enrage starts are 80 and 90 seconds. Vessa is stationary at her spindle so the encounter stays inside its court.
- The Unwritten King: hired five win 4/4 in 86–89 seconds; four mercenaries lose 8/8 with the hirer idle or down. His enrage starts at 98 seconds, above the measured five-person wins and below the raw four-person wins (135–151 seconds).
- Private Chromium checks pass with stub sprites and real sprites: entry, four interior views, the actual sign/picture, decoded music duration, saved volume, mute and return music. Screenshots are in `test-results/driver-AqiPPZ` and the latest real-mode folder named in `test-results/nornroot/ui-real.log`.
- Formatting, Clippy, Swedish coverage, Python/JavaScript syntax and generator reachability checks pass. A shared ranged-boss tuple needed a type alias to satisfy Clippy; its behavior is unchanged.

One additional generic bot-party control lost 0/2 to the final enrage. The
owner's required hired-five check above passed 4/4; the fighter brain was not
changed. This report does not claim balance for every human rotation. Full-song
listening and the audible loop seam are unverified. The final balance edits
remain separate from the other session's base dungeon release.

## Visual correction: original scenery and Fatewoven shapes

The owner correctly identified the first Fatewoven pass as a recolour: it used
the starter gear layers with a hue filter. The first room art also retained the
generic rectangular stone wall and tiled-floor language. These claims of visual
distinctiveness were premature. The correction replaces both constructions.

- Scenery uses irregular root crusts, forked trunks, amber sap lanterns and
  wrapped burial cocoons. The west court is a giant tree cross-section; the east
  court carries warp threads. The final loom has three hanging amber weights.
  The root portal, interior lighting and minimap share its moss/wood/amber palette.
- All 28 Fatewoven items now use original `fatewoven` art without a tint filter.
  Root corslets, pegged shoulder frames, wound cuffs, split shin guards, three-bead
  rings and shuttle pendants are separate equipment layers. Class headgear and
  weapons have their own forms, including a loom crown/staff for the mage,
  needlecomb and twin shuttles for the assassin, and a double-limbed hunter bow.
- Existing item IDs, variants, names, stats and set bonuses remain stable. This
  is a visual correction, with no collision or encounter changes.
- `scripts/nornroot_gear_shapes.py` draws only new geometry on the existing hero
  skeletons. `scripts/make_nornroot_gear.py` exports ten rigs and all eight slots
  as PNG/depth atlases plus matching icons. Gear is source-drawn; no PixelFlow
  records are claimed for these new pieces. The six enemy PixelFlow records are
  unchanged. `world/gear-art.txt` and `docs/nornroot-gear-state.txt` preserve the
  gear source and file list.

Rebuild the gear with `python3 scripts/make_nornroot_gear.py`, then
`python3 scripts/gear_levels.py --nornroot-only`,
`python3 scripts/gear_art_catalog.py` and `node scripts/sync-world.cjs`.
The scoped catalogue command refreshes only Nornroot equipment.
Use `--preview` on the gear builder for the concept sheet.
The focused browser check is `tests/nornroot-gear-art.cjs`;
`tests/nornroot-ui.cjs` also equips a complete server-approved Fatewoven set
before taking the zone screenshots. Evidence is in
`test-results/nornroot-redesign/`.

The replacement gear exports 80 fitted layers / 21,760 frames without blank or
clipped frames. All 80 single-piece browser cases visibly equip and have a
changed alpha mask compared with the starter layer (minimum 38 changed pixels).
The full sets render all five clips in eight directions on all ten rigs. A
mutation that substitutes the starter equipment fails with the expected
"unchanged silhouette" error. The actual private game also confirms an 8/8
Fatewoven set and loads the new atlas layers before zone screenshots. Item
catalog comparison confirms only `art`/`tint` changed on the 28 Nornroot pieces.

Replacement real-game screenshots: `test-results/driver-akGZxQ`. On owner
request, the six zone pictures and complete hero gear sheet were replaced in
FileDrop and verified by SHA-256. Original enemy sheets and the music upload
remain available there.

Final checks: server debug build succeeds, the focused Rust catalogue test
passes (one test), formatting/syntax checks pass, and all seven replacement
FileDrop images match their source hashes. No public server restart was performed for this correction; the client artwork
is served from disk. The owner subsequently requested the finish skill to
preserve and push the completed work.
