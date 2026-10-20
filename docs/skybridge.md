# The Shattered Span — level 30

The second of the three requested progression dungeons. Its entrance is in
**Bifrost Reach (zone 7), at (58, 128)**, on the western floating platform below
Heimdall's Perch. The return arrival is (58, 133), outside the entrance disc.
Sigrid the Gatewarden and Hakon the Chronicler stand beside the approach; Sigrid
offers the existing five-class mercenary service. Public zone **42** is appended
after Nornroot Barrow (41).

The 112 × 112 private interior has four party copies, a level-30 access gate
and a recommended party size of five. A western toll-gate gallery and an eastern
crystal-weaving gallery flank the central rainbow arches. The northern terrace
holds the Keystone Arch and Vaelor the Bifrost Archon. Torvald, the Last Watcher,
waits beside the safe arrival (56, 99) for the entry quest. An entrance exit
always works; the northern arch exit opens after all three guardians fall, even
if they are killed out of order.

## Encounters and rewards

Four packs each contain a Glassfang Lynx, Bifrost Sentinel and ranged Prismatic
Caster. Torstein, Keeper of the Toll, guards the west gallery; Sunniva, the
Spectrum Weaver, holds the east gallery; Vaelor, the Bifrost Archon, waits at
the northern keystone arch. Torstein and Sunniva each have a party quest at a
separate giver. The Archon has no quest and awards the final two guaranteed blue
pieces. Each ordinary kind and guardian also has its own material (`span_*_relic`).
Combat, kill credit and rewards use the existing authoritative dungeon systems.

The Archon's **Sundering Arc** shows a frontal cone warning for 3.5 seconds. The
area behind and outside the 90° arc is safe. Below 40% health the arc expands
and fires quicker. The sign at (56, 26) explains the safe positioning behind the
boss. Fallen fighters stay down through the fight.

The 28 exclusive **Bridgeward** blue pieces require level 30 and have 15% more
base attack/defense than that level's ordinary blue set. The first two bosses
cover all seven non-chest categories; the Archon drops one chest and one piece
from the other categories. Two boss quests award class-neutral pants (`pants_wayfarer_l30_span`)
and an amber ring (`accessory_amber_l30_span`). `scripts/gear_levels.py` generates
the pieces; `scripts/quest_gear_rewards.py` preserves the fixed rewards. Class set
bonuses live in `docs/set-bonuses.md`; the eight-piece **Prism arc** strikes the
nearest enemy within four tiles for 16% basic-hit damage, with the existing
20-second signature timer.

## Assets and music

`client/skybridgeart.js` draws lapis stone tiles, prismatic glass shards, cyan
braziers with dynamic light pools, floating obelisks and the northern Keystone
Arch. The original six cel enemies have 96 × 96 frames, anchor (48, 90) and 34
editable PixelFlow frames each. Their IDs and atlas metadata are merged into
`client/assets/cathedral.txt`; existing dungeon sprites are retained. Source art
is in `scripts/make_skybridge_sprites.py` and `scripts/eye_below_span_*_raw.npz`
(the latter prefix comes from the shared exporter).

**Seven Broken Arches** is an original 24-bar 3/4 chamber score at 96 BPM in
E minor. Dexed Harpsichord ostinato, Dexed Wood Bass, Dexed Glass Vibes, Sork-60
Pad and Axiom-8 Chillhop percussion weave a somber, luminous atmosphere without
harsh leads or busy hi-hats.
Editable dybase2 project: `5d59c0df33cd65c9` (owner `codex`),
[open score](https://gunning.se/dybase2/?project=5d59c0df33cd65c9).

The 128 kbps game loop is 45.000 seconds, with its tail folded back, 25 Hz
high-pass, decoded mono RMS −24.00 dB and peak −4.20 dBFS. The natural-ending
MP3 stays in `test-results/skybridge/Seven Broken Arches.mp3`; no FileDrop
upload was requested.

## Rebuild and focused checks

```sh
python3 scripts/generate_skybridge.py
python3 scripts/gear_levels.py
node scripts/sync-world.cjs
python3 scripts/build_swedish.py
bash scripts/cargo.sh build

python3 scripts/make_skybridge_sprites.py preview
python3 scripts/make_skybridge_sprites.py build
python3 scripts/make_skybridge_sprites.py export
python3 scripts/make_skybridge_sprites.py verify

bash scripts/render_skybridge_song.sh
python3 scripts/finish_skybridge_music.py

bash scripts/cargo.sh test skybridge_tests -- --nocapture
NODE_PATH=/home/serveperry/webserver/www/dybase2/node_modules /home/serveperry/.nvm/versions/node/v20.20.2/bin/node scripts/test-via-mcp.cjs run skybridge
```

## Deployment and saved private zones

Implementation and private validation do not restart the public service.
Client files in this checkout are served from disk immediately. A separate
server release is required to make the authoritative entrance playable.

Existing public IDs 0–41 stay fixed. The Shattered Span occupies runtime slot 42.
The Arena's public map occupies slot 40, Nornroot Barrow occupies slot 41.
Dungeon copies follow all 43 static maps (`COPY = 43`).
