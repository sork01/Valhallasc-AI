# Greenmeadow After Hours

The owner replaced the earlier night brief on 2026-10-21: swung 1990s hip-hop
beats, lush jazz/soul/bossa harmony, 70–90 BPM, warm electric piano, acoustic-style
accompaniment and subtle background texture. They approved the exact instruments
before use: Dexed TINE PIANO, WOOD BASS and MARIMBA, Sork-60 Mellow Pad, Axiom-8
Hip-hop kick/snare, Axiom-8 Chillhop hats, and a little SorkCrush hiss. No lead or
flute. These are synthesized acoustic-style timbres, not recordings. Hiss is not
represented as a recording of vinyl crackle or a room.

The active dybase2 project is `0d47202bc633294a`. Before edits, MCP inspection
read its full 32-bar 90 BPM 6/8 score, instruments, notes and arrangement, saved
under `test-results/meadow-night-hiphop/inspection.json`. The source project JSON
is also archived there. The original daytime project `e2041a0c18b333d3` remains
unchanged. Its G–B–D–B motif stays in quiet marimba accompaniment; a new descending
answer follows each bar's actual chord.

## Composition brief written before the rework

82 BPM, 4/4, 32 bars, 93.658537 seconds plus natural ending. A shared 60:40 eighth
swing maps offbeats to 0.6 of each quarter-note beat. Drums, bass, electric-piano
comping and marimba use that same mapping, including deliberately subdivided
sixteenth pickups. The snare anchors beats 2 and 4 throughout (zero-based 1 and 3).
Every bass attack has a matching kick. The Hip-hop kit plays only kick and snare;
every closed/open hat comes from the separate Chillhop kit, as the music guide
requires. Hat timbre does not determine the new groove's style.

| Bars | Section | Actual chord in each bar |
| --- | --- | --- |
| 1–8 | Familiar streets | Gmaj9, Gmaj9, Am9, D13, Bm7, E7b9, Am9, D13 |
| 9–16 | Window light | G6/9, Bm7, Em9, A13, Am9, D13, Gmaj9, D13 |
| 17–24 | Bossa under the trees | Cmaj9, Cm6, Bm7, E7b9, Am9, D13, G6/9, D13 |
| 25–32 | Home on the last beat | Gmaj9, Bm7, Em9, A13, Am9, D13, G6/9, G6/9 |

The E7b9 secondary dominant, A13 and borrowed Cm6 are intentional colours; G-sharp,
F-natural, C-sharp and E-flat must be checked against these actual chords rather
than rejected from a global G-major scale. Rootless four-note electric-piano
voicings provide the extended harmony above a monophonic wood bass. A small
0–0.018 beat spread within each chord is deliberate finger timing. The third
section adds a bossa-style anticipation at beat 2.75 (mapped through the same
swing), while the snare remains fixed. The final section thins to G6/9, resolving
both the natural ending and the loop return to Gmaj9.

## Build and delivery

`sh scripts/rework_meadow_night_hiphop.sh` rebuilds this active project through
dybase2 MCP after inspecting it. `MODE=inspect` only reads it; `MODE=render` reads
the complete grid, checks it and rerenders without rewriting notes. Optional
`MEADOW_MIX` is a JSON object of track names to fader dB values for a render pass.
The script rejects any Hip-hop-kit pitch other than kick/snare, missing backbeats,
unanchored bass notes, chord clashes and notes crossing bar boundaries. Render
analysis includes every instrument separately.

The game export folds the effect tail, high-passes at 25 Hz, encodes at 128 kbps
and measures -24 dB mono RMS after decoding. A separate 192 kbps copy retains
the full ending. The owner's FileDrop upload request persists for this revision.
Only focused song checks are needed. Auditory review remains explicitly separate
from numeric checks; no full-song listening can be claimed by the agent.

## Render and export results

The complete 32-bar grid was read back through MCP: 376 piano notes, 78 bass notes,
65 marimba notes, 96 pad notes, 172 kick/snare hits and 256 hat hits. The falling
answers and secondary-dominant pitches match their actual bar chords. The Hip-hop
track contains only MIDI 36/38; the separate Chillhop track supplies every hat.
The full render has no clipping, song-analysis problems or render problems. The
MCP messages that SorkCrush/SorkVerb “could not be checked” refer to the offline
capability probe, not failed instrument loads. All tracks rendered audibly.

The first render exposed an inaudible hat stem and a marimba buried 26 dB below
the piano. The final faders and hat dynamics are saved in the editable project:
piano -16 dB, wood bass -11, marimba -8, pad -36, kick/snare -7, hats 0, with a
6 dB instrument hat trim. Their measured stem RMS levels are respectively -29.6,
-32.5, -34.9, -45.2, -35.6 and -45.3 dB. The marimba remains accompaniment below
the piano. The first swung hat follows the opening kick, giving it space.
SorkCrush keeps 24-bit/48 kHz processing with zero jitter, dither and drive; its
noise/mix controls add restrained hiss, fading away at the final bar boundary.

`python3 scripts/finish_meadow_night_theme.py` derives tempo, meter, length, title
and WAV path from the current MCP reports. It defaults to
`test-results/meadow-night-hiphop/`; passing the older report directory reexports
that archived arrangement. It folds the three-second tail into the exact loop,
filters at 25 Hz and applies a smooth peak curve to only 0.00075% of samples.
The decoded 128 kbps game MP3 is **93.658542 s, -23.998 dB mono RMS, -22.1 LUFS,
-1.8 dBTP**, with no clipping. The WAV endpoints match; the decoded MP3 boundary
step is 0.00430 versus a 0.18447 maximum internal step. Those measurements do not
establish an audible seamless loop.

The full 192 kbps MP3, **Greenmeadow_After_Hours.mp3**, is 96.658542 seconds with its
natural ending. Full-song metronome and loop-seam review copies, the complete
grid and all measurement reports are in the same ignored report directory.

The short solo exports measured every attack within 12 ms of its intended onset
(piano/bass/drums within 1 ms; pad 11.75 ms). Piano and pad tails immediately
before the next bar were 42.1 and 32.6 dB below the next attack. These are numeric
timing checks, not a listening sign-off.

The focused private Chromium test passed using the staged MP3: decoded duration,
-24 dB mono RMS, unclipped peak, dusk/dawn fades, saved 80% music volume,
mute/unmute, travel away and back, and shared indoor fallback. The tested file
then replaced `client/assets/music_meadow_night.mp3`; the existing zone-0 routing
needs no change or server restart. The full natural-ending MP3 was uploaded to
Sork’s FileDrop as **Greenmeadow After Hours.mp3**, with metadata and a matching
SHA-256 (`d6031d2a59bcf0c4` prefix). The prior FileDrop version is retained under
its older title. All source-grid, full-render, export and solo checks passed.
`TIME-NIGHT-Z0-NEW` stays unchecked solely for the required full-song and seam
listening review.
