# Emberwake Caldera — RAID-APPROACH

Public outdoor zone 45, level recommendation 95–99, reached from Asterion's
north radial road. Existing public zone IDs remain unchanged. The caldera
crosses a physical molten channel on a broad basalt causeway, then climbs to
the Nine-Chain Door. The door stays sealed until RAID-MAP and RAID-OPEN.

The door currently has scenery and a readable seal, with no portal to an
unimplemented instance. Do not point it at a guessed future zone or an appended
private copy. RAID-MAP must install its real portal; RAID-OPEN opens that route.

| Connection | Gate | Destination arrival |
| --- | --- | --- |
| Asterion → Emberwake | zone 17, (90,18) | zone 45, (22,137) |
| Emberwake → Asterion | zone 45, (14,140) | zone 17, (90,25) |

Both arrivals lie outside gate discs, clear of monsters by more than eight
tiles. The level band is advice, with no access lock. This is an outdoor route,
with normal enemy level spread and outdoor loot; it is not a raid encounter.

Four ordinary kinds: Ashback Salamander (95), Obsidian Glasswing (96), Slagjaw
Burrower (97), Cinderhorn Ram (98). Three elites: Chainmaw, the First Shackle
(97, three-player quest), Yrsa, the Living Bellows (99, five-player quest), and
the Uncrowned Ember (99, no quest). Ordinary baseline stats and health
multipliers follow their Yearwheel peers; elite adjustments remain in
world/elite-power.txt. Their materials and gear use the normal kill path.
Weather follows the Crags: clear, fog and ash wind, with no rain or snow.
The new shared-catalog flags `elite` and `outdoor` default to the old dungeon
behavior, preserving existing catalogs. Outdoor elites heal on evade and
respawn after ten minutes; ordinary enemies respawn after 22 seconds.

Five one-time quests introduce the linkkeeper, clear the road, challenge two
elites, then carry Eldmarr's warning back to Svala. Quest XP is one tenth of
the authored level requirement, including the level-99 extrapolation. Setup
shortcuts avoid grinding during protocol checks. The Asterion smith, warm
flagstones and cracked well foreshadow the old forge. All player text has
hand-written Swedish in scripts/sv-translations.txt.

The Emberwake Meeting Stone is at (127,29). It offers the usual outdoor
mercenary company. **RAID-PARTY integration remains:** the owner's nine-hire
limit applies inside the raid only, while the volcanic zone retains the
current cap. Ten-player grouping, reservation/transfer at this stone and
the raid entrance's exact-ten gate must be connected together by RAID-PARTY
and RAID-MAP. This task does not silently raise the outdoor cap to nine.

## Source and commands

```
python3 scripts/generate_emberwake.py
python3 scripts/generate_emberwake.py --check
python3 scripts/make_emberwake_sprites.py preview
python3 scripts/make_emberwake_sprites.py build
python3 scripts/make_emberwake_sprites.py export
python3 scripts/make_emberwake_sprites.py verify
python3 scripts/emberwake_sheets.py
python3 scripts/weather_zones.py --write
python3 scripts/chest_zones.py --write
node scripts/sync-world.cjs
bash scripts/cargo.sh test emberwake -- --nocapture
bash scripts/cargo.sh build --profile test
node scripts/test-via-mcp.cjs run emberwake
REAL_SPRITES=1 node tests/emberwake-ui.cjs
```

Use the Node path and NODE_PATH from AGENTS.md. Build/export use the PixelFlow
API; `build --replace` discards only these seven sprites' editor changes.
All seven atlases use the existing 96×96, anchor (48,90), 34-frame contract
and are added to the shared cathedral manifest without overwriting old kinds.
Full contact sheets contain all frames, not just the first six of each clip.
Scenery lives in client/emberwakeart.js; there is no client build step.
The molten river is a single cached terrain texture sampled in world coordinates
and clipped to the authoritative channel. Uneven cooled banks, broken crust
plates and hot branching channels replace the rejected rectangular lava stamps.
The channel itself uses overlapping circular obstacles with winding banks,
variable width, narrow tips and coves; both maps and terrain sample that footprint.
Chunk overlap preserves the texture across ground-cache boundaries.

Run this generator after generate_blackhour.py and before sync-world.
generate_asterion.py and generate_blackhour.py preserve/reapply the approach.
The generator uses a fixed seed, checks all arrivals/NPCs/enemies with flood
fill, and must produce identical map bytes on successive runs. Rust checks
also use the actual server collision. The real-protocol scenario walks the
road, exercises both gates, quest claims, material drops and persistence.

## Music

Two editable dybase2 projects, 32 bars in 4/4 and F minor:

| Score | Project | Tempo | Loop |
| --- | --- | --- | --- |
| Heat Beneath the Stones | ffb8d401bfa26e43 | 110 BPM | 69.818 s |
| The Chains Dream | 5cbeb819c350d08f | 96 BPM | 80 s |

Dub-techno / half-time: Sork-60 Hiphop Chorus Keys, Sork-60 Mellow Pad,
Sork Bass II Sub Weight, Axiom-8 Techno kick/snare and separate Chillhop hats.
The three-link chord response has quantized diminishing repeats rather than
tape echo. The night arrangement changes chord order and bass/backbeat
placement; it carries the source response in accompaniment without a
foreground lead. The scores use a short reverb return with no noise preset.

Source: scripts/create_emberwake_song.sh (`MODE=inspect`, `MODE=mix`,
`MODE=render`); finishing: scripts/finish_emberwake_music.py. Game loops fold
the tail, remove DC at 25 Hz and target -24 dB decoded mono RMS at 128 kbps.
Natural-ending 192 kbps copies and render reports are kept in
test-results/emberwake. Numeric/source checks do not constitute listening;
these scores have not been auditioned by the agent.

## Deployment boundary

Source is preserved and pushed on `feat/raid-approach`; finish does not merge
this into the served main checkout. No production restart or save migration
is included. Appending
zone 45 shifts all existing appended copies by +1: old dungeon extras
45–104 become 46–105, and Arena copies 105–112 become 106–113. Recheck the
running binary and actual saved zones before a separate release. A saved
old private-copy ID must never load as the new public caldera. Client source
is served from disk; install client/world data together with the new server.

## Focused validation

Two Emberwake Rust tests pass: real reachability/collision, blocked molten
river and raid door, both portal transfers, outdoor weather, elite flags,
quest XP and actual material drops/respawn rules. The private MCP scenario
passes 12 checks, including the whole road walk, dialogue, claims, drops and
restart persistence. The Chromium test covers actual exported sprites, maps,
mobile landscape layout, both music buffers, dusk/dawn routing, volume, mute and return.
All 238 enemy frames round-trip to their source; fmt, Clippy and changed
JavaScript/Python checks pass. Weather/chest tables and Swedish are generated
and checked. No broad Rust or browser suite was run.

Final source map hash: 65d8cff7b643f6ee554b24ff47322e6692d56113823981757f4e28130fcb48ef.
Decoded game music mono RMS: day -23.97 dB, night -23.97 dB, both 128 kbps;
no clipped samples in either source render. Auditory review remains unverified.
The owner requested zone pictures, full enemy sheets and both music tracks
on FileDrop; upload receipts are in test-results/emberwake/filedrop-upload.json.
