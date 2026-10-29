# Combat sounds and elite portraits

Beta 1.32.1, updated 2026-10-29 (same version by owner request). Client-only: the live server serves these files directly;
no Rust changes, world generation, database migration or service restart.

The selected enemy's portrait has a golden coiled dragon when its existing
`Field` catalog definition marks it as elite. This includes bosses and elite
dungeon packs. King Slime now has the client elite flag, matching the existing
server classification. Ordinary enemies and player portraits retain their
normal border. `hud-target-portrait` contains the canvas and decorative SVG;
the whole Character frame applies the UI scale once. The dragon does not receive
pointer events and leaves the name, level and HP outside its bounds.

Settings → Combat sounds offers **Recorded** and **Synthesized**. Synthesized is the
default for new and old preferences without a saved choice (owner follow-up, 2026-10-29; no version bump); `valhallasc.save.v1.combatSounds` saves
the choice per browser/device. Invalid stored values return to Synthesized. Explicitly saved choices are preserved.
The Swedish labels are Stridsljud, Inspelade and Syntetiska.
The Settings overlay uses a bounded grid track so the taller panel stays
centered within the stage at larger UI scales; touch controls retain their
physical 44 px minimum and scroll within the window.

Recorded mode covers weapon attacks, hit/critical impacts, misses, enemy attacks/hurt/death, player hurt/death, all 50 learned skills, achievements and level-ups. Five weapon families and seven enemy families keep their identities. Constructs use wood/metal foley; bosses stay deeper and longer. Skills use explicit per-skill material/pitch profiles (blade, rush, earth, fire, arcane, shadow, ice/lightning, healing, holy, shield, focus and bow). Level-up and achievement cues use separate complete authored sound files. Music and boss-mechanic warnings retain their existing cues. Synthesized mode retains the original effects.

Female hurt and death each use three original AuraVoice performances, selected from the character's authoritative `Field.hero.look.gender` across all five classes. Male characters keep their male recordings, now with three takes per stage. Missing female recordings fall back to a higher-pitched synthesized voice, never a male recording. The synthesized female hurt/death pitch also follows the character body.

`combat-audio.js` decodes 68 short mono MP3s, 569,157 bytes altogether. Since
Beta 1.32.2, background priming loads one recording at a time, yields to browser
idle time before each load and uses low network priority. The game primes them
on entering play or enabling Recorded. See `docs/client-loading.md` for the
related zone-art startup fix and focused validation.
A missing/not-yet-decoded recording uses the original synth immediately; it
does not replay an old hit after a download finishes. Synthesized mode does not
request these files. Combat uses the existing hearing range and quieter remote
players, a shared maximum of four enemy voices and a twelve-recording total
ceiling (ten ordinary slots, two reserved for progression cues). A progression cue can replace an older ordinary voice at the ceiling. Every recording passes through `sfxOut` and its squared volume taper.
The Settings sound switch and sound key mute the bus immediately, including
effects already playing; switching modes stops active recordings.

Enemy hurt uses the existing authoritative `hit` event's enemy kind and position,
only for a visible, nonlethal hit. Enemy attack/death continue to use snapshot
transitions; player death continues to use the hero's death transition. No
client data alters combat or rewards.

The bundled performances and authored effects are CC0-1.0, selected from:

| Creator | Pack and source | Material |
| --- | --- | --- |
| Kenney | [50 RPG sound effects](https://opengameart.org/content/50-rpg-sound-effects), also [RPG Audio](https://kenney.nl/assets/rpg-audio) | Weapon swishes, cloth, creaks, chop and metallic impacts |
| rubberduck | [80 CC0 creature SFX](https://opengameart.org/content/80-cc0-creature-sfx) | Mouth-performed creature voices with filters; the creator describes the recording method in the page comments |
| HaelDB | [Male Grunt/Yelling sounds](https://opengameart.org/content/male-gruntyelling-sounds) | Recorded male grunts/yells; the CC0 option is used |
| AuraVoice / Nocturnal_Vanguard | [Female Hurt Grunts & Groans](https://opengameart.org/content/female-hurt-grunts-groans) | Original female voice performances |
| rubberduck | [80 CC0 RPG SFX](https://opengameart.org/content/80-cc0-rpg-sfx) | Alternate blades/impacts, spell and earth effects |
| JaggedStone | [Magic Spell SFX](https://opengameart.org/content/magic-spell-sfx) | Authored holy/healing/shield/focus spells, achievement and level-up cues |

Per-clip authors, original filenames, source/archive/output hashes and durations
are in `client/assets/combat/sources.txt`; notices are in the adjacent
`LICENSE.txt`. These are recorded performances/foley, not recordings of actual
fantasy creatures. Female characters use a female performer; male characters use male performances. Spell/celebration files are authored audio effects, rather than claimed acoustic recordings. No subjective listening acceptance is claimed by the automated checks.

The original delivery used these three archives in a scratch directory as
`rpg.zip`, `creature.zip`, `human.zip` respectively:

- https://opengameart.org/sites/default/files/RPGsounds_Kenney.zip
- https://opengameart.org/sites/default/files/80-CC0-creature-SFX_0.zip
- https://opengameart.org/sites/default/files/yelling%20sounds.zip

Run `python3 scripts/build_recorded_combat.py /path/to/cache` with ffmpeg
available. The script verifies the pinned archive checksums, trims silence,
limits ordinary clips to 1.4 seconds (complete authored cues up to 2.5 seconds), applies short edge fades, peak-normalizes to
70%, and writes 44.1 kHz mono MP3 at 96 kbps. It does not generate new speech, synthesis or music.
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

The original 29-file delivery passed 146 checks at 1440×900 (desktop), 844×390 (phone), and
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

Same-version owner follow-up (Beta 1.32.1, 2026-10-29): synthesized is the default when the stored mode is missing or invalid; either explicit mode remains saved. The recorded-audio suite now explicitly selects Recorded before waiting for its assets. The focused `daze-sound-defaults-ui.cjs` check passes 13 assertions, including new/legacy/invalid defaults, both saved modes across reload, and mounted daze behavior. Public hashes and health match in `test-results/daze-sound-defaults-public.json`.


## Varied sounds, female voices and progression (same-version follow-up)

Every play varies pitch (±8% for effects, ±3% for human voices, ±1% for progression), volume (±7%) and low-pass cutoff (7.5–11 kHz). Cue families with alternate takes never immediately repeat the same loaded take, even with a constant random value. Unavailable takes are skipped; if the whole family is unavailable, synthesis plays immediately. No delayed sound is replayed after loading. All 29 original MP3 hashes are unchanged; 39 files add alternate performances, female voices and authored skill/progression material. The new files add 377,901 bytes.

For reproduction, also download these pinned inputs beside the original three ZIPs:

| Cache filename | Download |
| --- | --- |
| `fantasy.zip` | https://opengameart.org/sites/default/files/80-CC0-RPG-SFX_0.zip |
| `female.ogg` | https://opengameart.org/sites/default/files/female_hurt_grunts_groans_1.ogg |
| `magic-1.ogg` | https://opengameart.org/sites/default/files/magical_1_0.ogg |
| `magic-2.ogg` | https://opengameart.org/sites/default/files/magical_2.ogg |
| `magic-3.ogg` | https://opengameart.org/sites/default/files/magical_3.ogg |
| `magic-4.ogg` | https://opengameart.org/sites/default/files/magical_4.ogg |
| `magic-5.ogg` | https://opengameart.org/sites/default/files/magical_5.ogg |
| `magic-6.ogg` | https://opengameart.org/sites/default/files/magical_6_0.ogg |
| `magic-7.ogg` | https://opengameart.org/sites/default/files/magical_7_0.ogg |

`python3 scripts/build_recorded_combat.py CACHE --output CANDIDATE/assets/combat` builds a review bank without changing served files. The builder pins every download, stores the six female take offsets/windows, and writes per-file metadata and attribution. It does not need the separately researched female scream pack; the selected hurt/death performances all come from AuraVoice.

Validation: `AUDIO_CANDIDATE=CANDIDATE node tests/recorded-audio.cjs` checks all cue names against the manifest, modulation limits, female routes, repeat prevention and voice ceilings; `MUTATE=repeat` must fail the repeat assertion. `AUDIO_CANDIDATE=CANDIDATE bash scripts/test-touch-bounded.sh tests/recorded-audio-variation-ui.cjs` checks a real female priest death, both voice bodies, all 50 skill routes, separate celebration audio, audible signal, volume/mute and Synthesized mode. The bounded browser passed 136 checks with candidate scripts/assets, artifact `test-results/driver-DGwu3a/recorded-audio-checks.json`. No Rust build, production test guest, balance sweep or restart is needed.

Same-version client release verified: all 76 public client/asset files match local SHA-256, public and bridge health are OK, and Beta 1.32.1 is unchanged. Receipt: `test-results/recorded-audio-1.32.1-public.json`. The generated Swedish catalog, release-note gate, changed JavaScript/Python syntax and whitespace checks pass. The existing audio suite now opts into Recorded explicitly, blocks the entire impact family for fallback checks, and measures the exact bus taper rather than comparing randomized take peaks.
