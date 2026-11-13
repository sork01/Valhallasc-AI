# Crossing cutscenes (CUTSCENE-*)

The first time a hero climbs up to Bifrost Reach, comes down from it, dives into the sea or comes back up, a short locked cutscene plays.
Owner request 2026-11-10; answers of the grill are in `TODO.md` (`CUTSCENE-RULES`).

| Kind | When (first time only) | Scene (about 6 s) |
| --- | --- | --- |
| `sky_up` | a gate from land into a `sky`-theme zone (Bifrost) | an updraft catches the hero: leaf spiral, clouds and wind streaks rush past downward, flash, islands drift by |
| `sky_down` | a gate from Bifrost to land | the hero lets go: a flash, a fall through the clouds, the ground rushes up, dust ring, thud |
| `dive` | a gate from land into an underwater zone | on the pier the lead shoes go on (clank), the plank gives, splash, sinking through bubbles and light rays, seabed rises, thud |
| `surface` | a gate from an underwater zone to land | the shoes come off and lie on the sand, the hero floats up towards the light, breaks the surface in a splash |

Bifrost into the sea plays `sky_down` then `dive`; the sea into Bifrost plays `surface` then `sky_up`. Each part only if unseen. Underwater means
`Map::underwater()` (the lead-shoes list: `UNDERWATER_THEMES` in `server/src/model.rs`), sky means theme `sky` (zone 7).

## Server (`server/src/world/cutscene.rs`, extends `world/leadshoes.rs`)
- `Character.cutscenes` (`#[serde(default)]`, a list of the kinds seen) is saved; old saves load as "none seen".
- `update_lead_shoes` (every tick) tracks `Player.env` (Land, Sky, Sea). A change counts as a **crossing** only when the hero used a gate within
  0.3 s (`portal_at`): login, reconnect, Spark landings, respawns and debug teleports play nothing and set no flag. Mercenaries and ambient
  adventurers are skipped.
- One `{type:'cutscene', scenes:[...]}` packet carries the unseen scenes in order and they are marked seen on sending.
- The lead-shoes `announce` is left out when the scene carries the same words (captions say "Equipping/Removing lead shoes").
- `Player.cutscene_until` (6.5 s per scene + 1.5 s) keeps monsters off the hero (target scans and `hurt_player_by`), like Spark's airborne state.
  The server never ignores input, so bots and scenarios are not stalled.
- Test servers (`VALHALLA_TEST_COMMANDS=1`) play none until a test sends the `enable_cutscenes` debug op (`World::cutscene_opt_in`), so the
  older suites that walk the real routes are not locked in a scene.

## Client (`client/cutscene.js`)
- Inert until a `cutscene` packet arrives (`online.js`). `field.js` calls `Cutscene.draw` at the end of `draw(t)` and passes `paintHeroBody`,
  the world's own hero drawing, so the real class art is painted (lead shoes are decided by the scene: `drawLeadShoes` asks `Cutscene.shoes()`).
- The scene is painted on an offscreen layer (fades blend it with the world), the hero is zoomed 1.5x about the feet and settles to life size
  for the fade-out, and the finished frame is copied onto an opaque `<canvas class="cs-view">` inside `#cutscene`, so the DOM HUD is covered.
- Locked: key events are swallowed in the capture phase (browser shortcuts still work), the overlay takes every pointer event, `Field.cutsceneBegin()`
  releases held keys, routes and targets. Not skippable. `ZoneJourney.enter` stays quiet while a scene plays (`ZoneJourney.clear()` on start,
  because the zone-change snapshot arrives before the packet).
- Sounds: `window.CutsceneAudio.play(kind)` in `game.js`, synthesised on the effect bus (mute and volume apply). Captions: English in the
  scene tables, Swedish by hand in `scripts/sv-translations.txt`. Reduced motion drops only the camera shake and the flash.

## Checks
- `cargo test cutscene` (10): zone kinds, the six crossings, once only, chain, login and Spark landings, mercenaries, save and old saves, grace,
  test opt-in.
- `tests/cutscene-ui.cjs` (bounded runner, `VALHALLA_BINARY` a `--profile test` build): 23 checks over the four crossings; `MUTATE=lock` (keys not
  swallowed) and `MUTATE=draw` (scene not painted) each fail it.
- Pictures: trigger a scene client-side with `Cutscene.play(['dive'])` and screenshot while it runs.
- Known stale: `tests/zone-journey-ui.cjs` fails at its last route (8 -> 9 is a seam now, with no `walk` portal); not related.

# The opening cutscene (INTRO-*)

A brand-new character sees about a minute on the **Grey Gull**, the ship at Greenmeadow's pier, sailing to land on a moving camera while a narrator tells
why the hero was summoned (owner request 2026-11-10, grill answers in `TODO.md` `INTRO-RULES`).

- **Trigger (server, `world/cutscene.rs`)**: `join_as` queues `intro_pending[character id] = skippable` when a character is created (`skippable` = the account
  already has another character; a guest has none); on the character's first tick, if `Character.landing` is still set and `intro` is unseen, one
  `{type:'cutscene', scenes:['intro'], skippable}` packet is sent, `intro` is saved in `Character.cutscenes`, and the no-aggro grace covers the 62 s.
  A character that was not created in this process (an old one still on the pier, a relog) gets nothing. Test servers play it only for a session that
  sent `enable_cutscenes` (too late for the first tick, so the browser test starts it client-side).
- **Skipping**: only from the second character of an account; hold any key or a finger for a second (hint "Hold a key or your finger to skip" after 2.5 s).
  Replay from Settings > "Replay intro" is always skippable and client-side.
- **Scene (`client/intro.js`, registered with `Cutscene.register`)**: the ship, pier and mooring are `MeadowDock.ship/pier/moor` (exported from
  `meadowdock.js`) and the skipper is `City.drawNpc`, projected by a custom camera in the game's 2:1 projection (`TW 88, TH 44`). The ship sails in
  from the south-west along the pier (`shipAt`). **Camera (Beta 1.47.6, owner 2026-11-13):** one continuous move, a Hermite spline through `SHOTS`
  (tangents from the neighbouring keys, zoom in log space, .49 to 2.96) with a slow swell drift on top (off with reduced motion): it opens tight on
  the hero, cranes back to a high wide shot, glides down the hull to the skipper, lifts for the failing chains, sweeps round the bow and pushes in on
  the hero at "And it found you"; a vignette lifts as it settles. From 53 s it settles on the pier at zoom 1 and the projection is nudged so the pier
  start lands on the hero's real screen position, so the 2.2 s fade into the world has no jump. **The hero (real look and class) is aboard from the
  first frame** (`heroAt`): at the bow (`HERO_U` .12, forward of the sail's near end because the hero is painted over the scene and the sail cannot
  cover them) facing ahead (`pose.face`, new in `cutscene.js`), riding the hull's swell, lifted a little by the summoning light, then walking aft to
  the gangplank and down it to the pier start (`pose.walk`). `window.IntroScene` exposes `camera(t)`/`heroAt(t)`; check `tests/intro-camera-ui.cjs`
  (bounded runner, 8 checks, saves 14 frames in the run directory; `MUTATE=old` serves the previous `intro.js` and must fail).
- **The story in the sky** (screen-space overlays, `sky()`): ember glow on the edges, a far mountain with a ring of fire (the first forge), a gold light
  with an empty seat (the gods' hall), nine chains that appear one by one and fail one by one, burning roots, sparks; the sea warms from blue to red
  and back (`WARM`); the summoning is a ring of light with runes and a light column on the deck (`summon()`).
- **Narrator (Beta 1.47.4)**: the owner's seven ElevenLabs English recordings replace browser TTS entirely. The world is named **Veyrheim**;
  the last subtitle is “Welcome to Veyrheim, hero.” (`Välkommen till Veyrheim, hjälte.` in Swedish). Greenmeadow is the landing region.
  English/Swedish subtitles follow the language setting; both use the supplied English recordings. Original MP3 bytes are preserved in
  `client/assets/intro-narration-1.mp3` through `-7.mp3`; source names, SHA-256 hashes, durations and exact line mapping are in
  `docs/intro-narration-sources.txt`. Local PocketSphinx recognition confirmed passage order; original FileDrop files remain untouched.
- **Recorded voice lifecycle**: `CutsceneAudio.prepareNarration` fetches/decodes the clips once per page through the existing audio context.
  `narrate` plays a single voice on `sfxOut`; the sound switch and effects volume apply. Mute, skip, reset, disconnect, completion and a new scene
  stop active speech and invalidate pending playback. A 120 ms frame tolerance preserves normal line starts; slow decoding/network catches up
  to the current passage instead of queuing stale speech over later captions. A failed asset leaves subtitles; there is no TTS fallback.
- **Timing**: scene/server grace remains 62 seconds. Recording cues are 1.0, 12.5, 24, 34.5, 46.8, 51 and 58 seconds. The first cue starts half a
  second earlier and the final welcome half a second later so every recording fits at its original speed, without overlap or truncation.
- **Audio**: synthesised in `game.js` (`CutsceneAudio`): `sea_bed` (62 s of swell and a thin wind), `creak`, `ember` (a rumble under the history),
  `chord` (the summoning), `thud`.
- **Checks**: the existing twelve Rust cutscene checks cover server triggers/grace; no Rust changes are needed for this client release.
  `tests/intro-ui.cjs` now runs an actual recorded-audio playback on a private server under the unchanged bounded browser wrapper. It checks
  seven source hashes and cue boundaries, real MP3 decoding/WebAudio playback, first-character lock, all seven cues once/in order, the final
  Veyrheim caption, sound/effects volume, muting, delayed-load cancellation, replay/skip and reset cleanup. `MUTATE=narrate` removes the cue
  dispatch and fails at the first recorded-voice check. **20 focused checks pass**, including a full real-time playback; receipt and
  screenshot: candidate `test-results/driver-v55O6d/intro-recordings.json` and `intro-veyrheim-recorded.png`. Source/locale/syntax/
  whitespace checks pass. All **13 public client hashes** match, including seven `audio/mpeg` clips; public health passes and server
  PID `339798` is unchanged. Client **Beta 1.47.4** is live. Receipt: candidate `test-results/intro-recordings-release.json`.
  Prior client backup: `/media/raid/valhallasc-data/intro-recordings-original-20261112T194144Z`; metadata lists the seven newly added assets.
  Owner invoked finish and deploy. The combined Beta 1.47.4 client release verifies all **17** changed public files, both health
  endpoints, and an unchanged PID/executable. Finish receipt: candidate `test-results/mobile-intro-finish-release.json`;
  session record: wiki `10_projects:valhallasc_veyrheim_mobile_intro_20261112`. The server remains at the tested 1.47.2 release.

## Original intro score (Beta 1.47.5)

“Beyond the Nine Chains” is a finite 62-second dybase2 score, project
`2930e63d0705e3be`: 24 bars of 4/4 at 96 BPM in D minor, resolving to D major
for the welcome to Veyrheim. Five Sork-60 Juno Strings sections provide basses,
pulsing cellos, violas and two violin parts. The theme grows at 45 seconds;
the closing cadence starts at 57.5 seconds beneath the final welcome.

`create_intro_song.sh` creates the editable source through MCP. The five-synth
export crashed under the shared-host cap; `render_intro_song.sh` renders low/high
string groups in copies owned by codex, preserving the original five-track source.
Run it through the same 1536M/no-swap/one-CPU scope as browser tests. Then run
`python3 scripts/finish_intro_music.py`: sum the sample-aligned stems, high-pass
at 25 Hz, fade the natural ending and encode 128 kbps at -24 dB mono RMS.
The local 192 kbps preview stays in `test-results/intro-strings/`; no FileDrop upload.
Source IDs, export measurements and the asset hash are in `intro-score.json`.
Direct listening was unavailable; this is a technical delivery without auditory approval.

`music_intro.js` plays once against `Cutscene.state.el`, seeking after download
or AudioContext resume. `CutsceneAudio.setScore` suppresses title/field/day/night
music until completion, skip or reset. Music volume is independent of narration's
effects bus; the score has additional headroom beneath speech. Existing 62-second
server grace and all seven narration recordings are unchanged. Replay starts a
new run, and cancelled downloads cannot revive stopped playback.

Focused validation: `tests/intro-music-ui.cjs` through the bounded runner, covering
actual decoding/playback, narration overlap, sliders/mute, day/night suppression,
audio resume, restoration, replay, skip, delayed cancellation and a finite ending.
