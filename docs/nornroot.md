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
Threads, holds the east court; the Unwritten King waits at the loom. Arn and
Vessa each have a party quest at a separate giver. The king has no quest and
awards the final two guaranteed blue pieces. Each ordinary kind and guardian
also has its own material. Combat, kill credit and rewards use the existing
authoritative dungeon systems.

The king's **Spindle Snare** shows a red ring for five seconds. Its middle and
the ground beyond its outer edge are safe. Below 35% health the ring is wider
and repeats three seconds later. The sign at (56, 35) explains both safe routes
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

`client/nornrootart.js` draws violet burial slabs, amber wall bindings, woven
floor diagrams, sarcophagi and spindle lamps. The original six cel enemies
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
MP3 stays in `test-results/nornroot/Threads Without a King.mp3`; no FileDrop
upload was requested. Source/grid and codec checks passed; a full listening
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
Client files in this checkout are served from disk immediately. A separate
server release is required to make the authoritative entrance playable.

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
