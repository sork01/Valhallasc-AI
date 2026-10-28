# Combat sounds and elite portraits

Beta 1.32.0, 2026-10-28. Client-only: the live server serves these files directly;
no Rust changes, world generation, database migration or service restart.

The selected enemy's portrait has a golden coiled dragon when its existing
`Field` catalog definition marks it as elite. This includes bosses and elite
dungeon packs. King Slime now has the client elite flag, matching the existing
server classification. Ordinary enemies and player portraits retain their
normal border. `hud-target-portrait` contains the canvas and decorative SVG;
the whole Character frame applies the UI scale once. The dragon does not receive
pointer events and leaves the name, level and HP outside its bounds.

Settings → Combat sounds offers **Recorded** and **Synthesized**. Recorded is the
default for new and old preferences; `valhallasc.save.v1.combatSounds` saves
the choice per browser/device. Invalid stored values return to Recorded.
The Swedish labels are Stridsljud, Inspelade and Syntetiska.
The Settings overlay uses a bounded grid track so the taller panel stays
centered within the stage at larger UI scales; touch controls retain their
physical 44 px minimum and scroll within the window.

Recorded mode replaces basic weapon attacks, hit/critical impacts, misses,
enemy attacks/hurt/death and player hurt/death with local recorded performances.
There are five weapon families and seven enemy families (beasts, insects,
undead, constructs, plants, water creatures and ranged creatures). Constructs
use wood/metal foley. Bosses have deeper, longer playback. Magic skill effects,
healing, music, mechanic warnings and interface sounds keep their authored
identities. Synthesized mode retains the original sound functions; the new
enemy-hurt cue also has a synthesized voice.

`combat-audio.js` decodes 29 short mono MP3s, 191,256 bytes altogether, with four
concurrent loads. The game primes them on entering play or enabling Recorded.
A missing/not-yet-decoded recording uses the original synth immediately; it
does not replay an old hit after a download finishes. Synthesized mode does not
request these files. Combat uses the existing hearing range and quieter remote
players, a shared maximum of four enemy voices and a twelve-recording total
ceiling. Every recording passes through `sfxOut` and its squared volume taper.
The Settings sound switch and sound key mute the bus immediately, including
effects already playing; switching modes stops active recordings.

Enemy hurt uses the existing authoritative `hit` event's enemy kind and position,
only for a visible, nonlethal hit. Enemy attack/death continue to use snapshot
transitions; player death continues to use the hero's death transition. No
client data alters combat or rewards.

The recordings are CC0-1.0, selected from:

| Creator | Pack and source | Material |
| --- | --- | --- |
| Kenney | [50 RPG sound effects](https://opengameart.org/content/50-rpg-sound-effects), also [RPG Audio](https://kenney.nl/assets/rpg-audio) | Weapon swishes, cloth, creaks, chop and metallic impacts |
| rubberduck | [80 CC0 creature SFX](https://opengameart.org/content/80-cc0-creature-sfx) | Mouth-performed creature voices with filters; the creator describes the recording method in the page comments |
| HaelDB | [Male Grunt/Yelling sounds](https://opengameart.org/content/male-gruntyelling-sounds) | Recorded human grunts/yells; the CC0 option is used |

Per-clip authors, original filenames, source/archive/output hashes and durations
are in `client/assets/combat/sources.txt`; notices are in the adjacent
`LICENSE.txt`. These are recorded performances/foley, not recordings of actual
fantasy creatures. The human voice is shared by character bodies, as was the
former synthesized hurt/death voice. No subjective listening acceptance is
claimed by the automated checks.

To reproduce the assets, download these archives to a scratch directory as
`rpg.zip`, `creature.zip`, `human.zip` respectively:

- https://opengameart.org/sites/default/files/RPGsounds_Kenney.zip
- https://opengameart.org/sites/default/files/80-CC0-creature-SFX_0.zip
- https://opengameart.org/sites/default/files/yelling%20sounds.zip

Run `python3 scripts/build_recorded_combat.py /path/to/cache` with ffmpeg
available. The script verifies the pinned archive checksums, trims silence,
limits each take to 1.4 seconds, applies short edge fades, peak-normalizes to
70%, and writes 44.1 kHz mono MP3 at 96 kbps. It uses no synthesis or music tools.
Only selected MP3s and the provenance notices ship to players.

Focused checks: `npm run test:combat-feedback` uses a private database/server
under the required 1.5 GiB memory/one-CPU cap. It checks desktop, phone and tablet
elite/ordinary/cleared selection, HUD scaling/readability, settings reachability
and Swedish, every recording's hash and decoding, audible signal/peak levels,
all weapon/enemy families, an actual server hit, distance/crowd ceilings,
volume taper, immediate mute, mode changes, both saved preferences and a failed
download fallback. `MUTATE=frame` and `MUTATE=audio` remove the relevant routing
and must fail. `tests/combat-sound.cjs` explicitly chooses Synthesized to keep
its original waveform assertions meaningful.

The staged export passes 146 checks at 1440×900 (desktop), 844×390 (phone), and
1024×768 (Swedish tablet), peaking at 1,148 MiB under the 1,536 MiB hard cap.
The original synthesized-sound check passes another 25 assertions from the
export. Both frame/audio mutations fail at their intended assertions; the
audio mutation skips the unrelated live-hit fixture to isolate sound routing.
All 29 audio files rebuild byte-for-byte. All 41 changed public client files
match their local SHA-256 hashes. Public and bridge health are both OK.
Captures, hashes and validation receipts are in `test-results/combat-feedback/`.

The Swedish builder and release-note check pass. The broader Swedish catalog
test currently rejects three unchanged proper-name translations containing
"of the" (Laleh, Asha and Veya); the same three entries occur at HEAD. New
labels are checked directly in the private Swedish browser.
