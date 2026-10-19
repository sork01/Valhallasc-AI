# Musical style and song checks

Read this before creating, remixing, repairing, or rendering any Valhallasc song. The editable dybase2 project is the musical source of truth. Work on the active project named in the task or wiki; check its actual tempo, meter, notes, instruments, and arrangement before editing. Do not substitute an older draft or treat a rendered MP3 as an editable source.

## Musical identity

- Give each new zone its own recognizable style. Build a clear motif, a complementary answer, section changes, and an ending that resolves naturally. Keep the game loop musically seamless.
- A night variation is a real remix of its daytime score: retain a recognizable motif, write new melodic phrasing, and change harmony, rhythm, or form. A slower tempo, quieter mix, or instrument swap alone is insufficient.
- The groove should support the zone and its meter. For the night rhythm tasks, each song needs its own Chillhop break, with recurring kick and snare anchors. Do not copy one break into every zone.

## Instruments and mix

- Use Sork-60 for pads and synth leads. Do not use OB-Xd or tape echo on leads.
- **Flute and whistle-flute parts use Dexed `WHISTLE FLUTE`. Never use the Sork-60 Whistle preset.** Preserve this choice when editing an existing part; a pitch or timing repair does not call for a replacement timbre.
- Keep the main melody audible and identifiable. Check every bright foreground track, including stabs, bells, arps, and answering phrases. A louder chord stab can make a single-note lead sound like two simultaneous lead notes. Balance their rendered levels and remove or revoice competing parts where needed.
- Check note release and effect tails as well as MIDI note starts and ends. Notes can sound together even when their grid events do not overlap.
- Check the rendered attack and decay of a pad against each chord change. A slow attack can make the chord arrive after the bass; a long release or strong reverb send can leave the old chord sounding under the next one. Tighten the envelope and send while retaining the chosen instrument.

## Rhythm and harmony

- Establish the project's actual BPM, time signature, bar length, and section starts before moving notes. Align drums, bass, chords, and melodic accents to that beat grid, allowing pickups, syncopation, or swing only when deliberate and consistent. Account for instrument attack latency by listening to the rendered result.
- Match recurring bass attacks with deliberate kick anchors. A bass hit on beat 3-and in every bar needs a kick there if the groove is meant to sound locked; an unrelated kick elsewhere can make a mathematically quantized track feel loose.
- Check every track after a rhythm edit, including parts you did not change. Moving one pluck pattern or rebuilding the drums can leave bass, lead, and pad attacks disagreeing with the new groove. Inspect recurring note positions in each bar and at every section change.
- Choose a clear subdivision for each phrase. In a straight eighth-note phrase, isolated sixteenth-note starts can sound late or early even though they are valid grid positions. Move accidental offsets to the intended eighth; keep a sixteenth pickup only when it is deliberately phrased and works against the drums.
- In 4/4, a half-time backbeat places the snare on beat 3 (zero-based beat 2). In 6/8, the second dotted-quarter pulse begins halfway through the bar. Use the song's chosen groove rather than applying either pattern by default.
- Write out the **actual chord in each bar** and check every lead pitch against it. A melody copied over a changed progression must be reharmonized or repitched. A global key or `analyse_song` warning is not enough to find clashes such as F over Em7, D-sharp over D7, or C over B7.
- For a single-note lead, verify that only one intended melodic pitch sounds at a time across *all* foreground tracks. Inspect note overlaps, overlapping release tails, and any dyads in accompaniment. If a harmony is intentional, arrange and mix it so the lead line remains clear.

## Review and delivery

1. Inspect the active dybase2 project and its complete note grid, including section boundaries. Check harmony bar by bar and the mix hierarchy track by track.
2. Render and listen through the entire arrangement against a metronome or steady pulse. Check the intro, transitions, ending, and loop seam. Numeric grid, codec, and level checks cannot establish that the song feels in time or in tune. If direct listening is unavailable, report that limit instead of claiming an auditory sign-off.
3. Use focused checks for this song: render tracks separately when timing or mix is unclear, compare the start of each rendered attack with its MIDI beat, inspect clipping and export problems, decode the game MP3, and check the in-game crossfade, volume, and mute behavior when routing changes. MIDI timing and rendered attack are separate checks; neither replaces listening.
4. Follow the established export recipe: fold the tail into the game loop, apply the 25 Hz high-pass needed for Sork-60 DC, and target about -24 dB mono RMS after MP3 decoding (about -23.55 dB in the source WAV at 128 kbps). Export the game loop at 128 kbps. Keep a full-length MP3 with its natural ending; upload it to Sork's FileDrop when the task requests it or the owner asks.

The Greenmeadow night repair established the Dexed flute choice. The Emberfall Crags repair showed why checking only MIDI overlap and the global key misses audible double notes and chord clashes: its loud two-note Stabs track competed with a quiet Lead, and the Lead phrase had been copied over different chords. Its next timing pass found that the bass hit beat 3-and in every bar while the kick often missed it, 25 lead notes wandered onto isolated sixteenth positions, and the pad's slow attack and long tail blurred chord changes. The repair added kick anchors, put the lead phrase on eighths, and tightened the same Sork-60 pad's envelope, note length, and reverb send. These are examples to diagnose against the actual song, not settings to copy into every score.
