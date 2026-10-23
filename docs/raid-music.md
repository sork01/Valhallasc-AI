# Chained Forge music

RAID-MUSIC, 2026-10-23. Two original industrial techno scores, both in F-sharp
minor, 4/4, 64 bars. The instruments were inspected through the dybase2 MCP and
stated to the owner before composition.

| Score | Editable dybase2 project | Tempo | Game loop |
| --- | --- | --- | --- |
| Nine Chains Below | [001bb0c3080f4534](https://gunning.se/dybase2/?project=001bb0c3080f4534) | 152 BPM | 101.0526 s |
| The Table He Was Promised | [cbee414e186d8bf9](https://gunning.se/dybase2/?project=cbee414e186d8bf9) | 160 BPM | 96 s |

## Arrangement

The rhythm carries the score: Axiom-8 Hardstyle kick through SorkCrush,
Axiom-8 Techno snare/clap/toms/cymbal punctuations, and separate Axiom-8 Chillhop
hats. Dexed TUB BELLS makes the chain clangs, with restrained crushing and a
shared SorkVerb warehouse return. Sork-303 Deep Rubber plays bass at the kick
anchors. A quiet Sork-60 Mellow Pad and a short Sork-60 Hardstyle Stab-derived
machine call/answer sit inside the accompaniment; there is no foreground lead.
The motif has a normal filter envelope, shortened amplitude envelope and no
pitch LFO. There is no tape echo, OB-Xd or Hip-hop hat.

The eight-bar harmonic cycle is F#m, F#m, D, D, E, E, F#m, F#m. Every tonal note
belongs to its actual bar's chord. The final bar resolves to F#m. The recurring
machine call plays root/root/fifth/third, and the next bar answers fifth/third/root.
The code's zero-based beat offsets are 0, .75, 1.5, 2.5 and .5, 2, 3.25.
All notes have explicit starts and lengths.

| Bars | Section |
| --- | --- |
| 1–8 | Ignition: kick, bass, pad, short signal and sparse chain clangs; hats enter in bar 5 |
| 9–24 | Nine chains: backbeat and full offbeat hat groove |
| 25–32 | Pressure: continuing groove, a brighter machine signal and fills |
| 33–40 | Release valve: kick and bass thin to beats one/three in bars 33–36 (33–34 for Eldmarr), then rebuild |
| 41–56 | Full forge: extra sixteenth hats, clap accents and brightest signal |
| 57–64 | Return to the furnace; the final bar resolves, drops the running drums and lets the metal ring |

Eldmarr keeps the motif and harmony but runs at 160 BPM, with more chain strikes,
Dexed LOG DRUM responses, a Techno ride pattern, stronger kick drive, more claps
and a shorter breakdown. Both songs have a separate natural-ending export.

## Routing

`music_raid.js` uses the shared `createLoopMusic` player. Zone 46 selects the
Forge loop. A server `bossMech` fight whose boss is the living monster matching
the raid map's `final_boss` (`cf_eldmarr`) selects Eldmarr's variant. Merely
seeing the boss, targeting it, fighting a pack or fighting a Warden does not.
The variant stays while the fight runs, including when the hero is fallen;
death, wipe or evade returns to the Forge loop. Leaving the raid stops both.
The server normalizes private-copy zone IDs to template 46 in snapshots, so all
three copies use the same routing. Existing fades, volume, mute and fanfare
ducking apply to both players. The raid remains sealed.

The final boss is not built yet (RAID-BOSS-FINAL). The focused browser test
replays future `cf_eldmarr` snapshot data at the WebSocket boundary in a private
world; this validates the music wiring, not the future boss encounter. It uses
real server travel and actual browser audio decoding/output for both loops.

## Export and verification

The editable source of truth is the two dybase2 projects. Scripts create and
edit them exclusively through the dybase2 MCP:

```sh
sh scripts/create_raid_songs.sh --inspect
sh scripts/create_raid_songs.sh --compose --mix --probe --render
python3 scripts/check_raid_music.py
python3 scripts/finish_raid_music.py --install
```

Project receipts/checkpoints, complete read-back note grids, chord audit,
per-track render measurements, isolated rendered attacks, source WAVs, export
reports and natural-ending MP3s are under `test-results/raid-music/`. Keep these
checkpoints to resume the existing projects; do not accidentally create new
projects when repairing these scores. `RAID_SONG=forge` or `eldmarr` limits a run.
`--mix --render` repairs the mix without rewriting notes; `--probe` renders the
five rhythmic/pad parts independently over bar 9 and restores their solo state.

The export folds four seconds of tail over the exact loop, high-passes at 25 Hz
with cyclic history, joins the PCM endpoints over 3 ms, and encodes at 128 kbps.
It measures the decoded mono RMS and corrects gain to -24 dB, verifies duration,
DC, seam jump, peaks and clipping, and retains the natural-ending 192 kbps MP3s
locally. FileDrop is only on the owner's request.

| Decoded game MP3 | Mono RMS | Peak | Duration | Clipped samples |
| --- | --- | --- | --- | --- |
| Nine Chains Below | -23.99 dB | -5.83 dBFS | 101.052625 s | 0 |
| The Table He Was Promised | -23.98 dB | -7.37 dBFS | 96 s | 0 |

PCM endpoints match exactly; decoded MP3 endpoint jumps are .00312 and .00331
full scale. DC is below .00001. All parts are non-silent, neither final full
render has a mix-balance finding, and there are no unsupported drum pitches or
harmony warnings. Earlier mixes buried the hats, snare and motif; the retained
projects contain the corrected faders and motif filter envelope.
Decoded integrated loudness is -22.9/-22.5 LUFS and true peak -5.8/-7.2 dBFS.

The complete 3,312-note MCP read-back matches the intended grids. The chord and
kick/bass-anchor audits pass. Isolated drum attacks land within 1 ms of their
grid, the motif within 1.4 ms, and the soft pad reaches the measured threshold
within 56 ms. These measurements do not establish an auditory sign-off:
**direct listening was unavailable; the full arrangement and audible loop seam
still need an ear review.**

Focused browser check (use the optimized existing private-server binary):

```sh
VALHALLA_BINARY=target/release/valhalla-server \
NODE_PATH=/home/serveperry/webserver/www/dybase2/node_modules \
/home/serveperry/.nvm/versions/node/v20.20.2/bin/node tests/raid-music-ui.cjs
```

`MUTATE=1` disables the final-boss selection in the served `game.js` response;
the boss-switch assertion must fail. No public guest, server restart, encounter
calibration or broader suite is required for this client-only task.

The normal run passes **20 checks**, report
`test-results/driver-k15PUM/raid-music-result.json`: actual audio output and
duration, dormant boss/Warden exclusion, engaged/fallen/wipe/death transitions,
volume and mute across switches, outdoor-night return, saved-volume reload,
sealed entrance and browser/asset errors. Private test sprites are stubbed;
this task changes no art. The initial test spawn at (22,303) was on the exit
portal; the corrected safe muster position is (35,303).
The mutation run in `test-results/driver-9jOhEE` fails exactly when the engaged
final boss should select its score: the Forge score keeps running and the boss
player stays stopped. No production source is mutated. Summary:
`test-results/raid-music/mutation-check.json`. JS/Python syntax and diff whitespace
checks pass. No Rust or world data was changed for RAID-MUSIC.

Both natural-ending MP3s were uploaded to Sork’s FileDrop at the owner’s request
on 2026-10-23. SHA-256 and audio metadata verified; receipts are in
`test-results/raid-music/filedrop-receipts.json`. Listening review remains pending.

Finish validation also passed against an exported Git index on the RAID: the
Swedish gate, JS/Python syntax and all 20 private browser checks. Evidence:
`test-results/raid-music/finish-index-browser.json` and `finish-index-check.log`.
The export has no local node_modules, so its browser run prepends the original
project node_modules to NODE_PATH before dybase2’s dependencies.
