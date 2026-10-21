# Greenmeadow night: The Meadow After Sundown

**Historical 90 BPM / 6/8 version.** The owner subsequently approved a different
instrument lineup and a swung 1990s hip-hop rework. The same active project now
holds **Greenmeadow After Hours**; current composition and delivery are documented
in [greenmeadow-hiphop.md](greenmeadow-hiphop.md). The older create script is an
archive and rejects the renamed active project.

Owner brief (2026-10-21): “the Greenmeadow theme, slower, chillhop no lead.”
Follow `docs/musical-style.md` and the local createsong recipe. The editable
daytime source is `e2041a0c18b333d3`, **Greenmeadow Wander**, inspected through
dybase2 MCP: 132 quarter-note BPM, 6/8, G major, 32 bars. Its opening is
G–B–D–B, followed by D–C–B–A. The previous night project
`6c52c389c99ed898` remains an archive, not this replacement's editable source.

## Arrangement brief

90 quarter-note BPM (60 dotted-quarter pulses/minute), 6/8, G major with
an E-minor middle. 32 bars, exactly 64 seconds before the natural ending.
There is no dedicated lead or flute. Quiet Dexed MARIMBA accompaniment
retains the G–B–D–B shape in a lower register with rests and new phrasing.
Its descending answer uses each bar's chord tones. Sork-60 Hiphop Chorus Keys
and a quiet Mellow Pad supply harmony; Sork Bass II Fingered supplies bass.
The drum kit, including every hat, is Axiom-8 Chillhop. No echo or noise layer.

| Bars | Section | Chord in each bar |
| --- | --- | --- |
| 1–8 | Familiar path | Gmaj7, D7/F#, Em7, Cmaj7, Gmaj7, D6, Cmaj7, D7 |
| 9–16 | Lantern windows | Em7, Bm7, Cmaj7, Gmaj7, Am7, D7, Gmaj7, D7 |
| 17–24 | Grass under moonlight | Cmaj7, Gmaj7, Em7, D6, Am7, Em7, Cmaj7, D7 |
| 25–32 | Home beneath the stars | Gmaj7, D6, Em7, Cmaj7, Am7, D7, Gmaj7, G6 |

Beat positions below are quarter notes from each bar's start. Kick and bass
anchor beat 0 in every bar. Alternating bars add a bass fifth and a matching
kick at 2.5. Snare marks the second compound pulse, beat 1.5, throughout.
Quiet hats use deliberate eighths, varied by section. Chords attack at 0
and answer at 1.5. The pad releases before the next chord; its envelope and
send are tightened rather than allowing an old chord to blur the next bass.
The marimba motif and new falling answer alternate instead of running a
continuous foreground melody. The last section thins to a G6 resolution;
the loop returns naturally to Gmaj7.

## Delivery and review

`scripts/create_meadow_night_theme.sh` writes the separate editable dybase2
project through MCP and records its full note grid and render report under
`test-results/meadow-night-new/`. Every pitched note is checked against its
actual bar chord, with recurring bass/kick and snare checks on the read-back
grid. Rendering uses the actual DAW instruments, including per-track checks.
The export folds the effect tail into the game loop, high-passes at 25 Hz,
and measures the decoded 128 kbps MP3 against -24 dB mono RMS. A separate
192 kbps MP3 retains the natural ending. FileDrop upload is offered only.

Full-song listening against a pulse and an audible loop-seam review still
require human ears; numeric checks cannot supply that sign-off. Keep
`TIME-NIGHT-Z0-NEW` open until that review is confirmed.

## Editable replacement and measured export

New project: [`0d47202bc633294a`](https://gunning.se/dybase2/?project=0d47202bc633294a),
**Valhalla Greenmeadow Night — The Meadow After Sundown**, owner `codex`.
The old daytime and night projects were not edited. Rebuild this replacement
with `sh scripts/create_meadow_night_theme.sh 0d47202bc633294a`; without an ID,
the script creates a separate new project. The active project's complete
32-bar grid was read back through MCP. It has 252 chord notes, 69 quiet motif
notes, 96 pad notes, 47 bass notes and 235 drum hits. The rests in the motif
track are intentional. There are no song-analysis problems or warnings.

The stock keys release was shortened as well as the pad release, preventing
old chords from carrying into the next bar. Short solo renders measured
attacks within 14 ms of their intended start for every part; keys and pad
tails just before the next bar were respectively 43 and 36 dB below the next
attack. These are waveform measurements, not an auditory review.

The complete render uses the actual DAW exporter, with no clipping or failed
instruments. Its warning about the quiet unmastered mix is handled by export
gain. The informational SorkVerb offline-compatibility message is an unchecked
capability probe, not a failed load. Export uses the established Meadow smooth
peak curve on just 0.00114% of samples, without hard clamping. The encoded game
loop is 64.000 s at 128 kbps, -24.000 dB mono RMS, -22.4 LUFS integrated and
-1.7 dBTP. Decoded DC is about 0.00001 per channel. The WAV endpoints match;
the decoded MP3 boundary step is 0.0041 versus a 0.0730 maximum internal step.
These seam measurements do not establish that the seam sounds seamless.

`python3 scripts/finish_meadow_night_theme.py` stages these files under
`test-results/meadow-night-new/`:

- `music_meadow_night.mp3`: the game loop.
- `The_Meadow_After_Sundown.mp3`: 67 s, 192 kbps, natural ending.
- `metronome.mp3`: full song with both compound pulses for listening review.
- `loop-seam.mp3`: four seconds either side of the encoded loop boundary.
- `score.json`, `render.json`, `export.json`, `attacks.json` and
  `attack-analysis.json`: full grid and measurement records.

The owner subsequently requested the MP3 upload. The 67-second natural-ending
192 kbps copy was uploaded to Sork’s FileDrop as **The Meadow After Sundown.mp3**
(`The_Meadow_After_Sundown.mp3`), with an audio/mpeg metadata sidecar. The copied
file’s SHA-256 matched the source (`59298459ce7fd3d2` prefix).

The game asset `client/assets/music_meadow_night.mp3` was replaced after the
focused private Chromium check passed. Existing `nightScores` routing already
selects it for zone 0. The check decoded the staged MP3 in Chromium and verified
the 64-second duration, -24 dB mono RMS, unclipped peak, dusk and dawn crossfades,
saved 80% music volume, mute/unmute, leaving and returning to Greenmeadow, and
the shared fallback remaining silent in the indoor Deep. The older fallback
probe used Wyrdwood, which now has its own night song; it was corrected to Deep.
No Rust build or service restart was needed. The task stays open only for
full-song and loop-seam listening review.

The public asset was downloaded and its SHA-256 matched the staged and installed
loop: `76bdb70badeb978d0ff852024f79f0684feb1ce4e660a3950e8c29b347973b43`.
