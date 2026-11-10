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
  from the south-west along the pier (`shipAt`) and the camera follows `SHOTS` (zoom .42 to 1.6, pans along the hull, a push in to the skipper, a close-up
  of the summoning); from 53 s it settles on the pier at zoom 1 and the projection is nudged so the pier start lands on the hero's real screen position,
  so the 2.2 s fade into the world has no jump. The hero (real look and class) is hidden until the summoning (48.7 s), stands on the deck, then walks the
  plank to the pier start (`pose.walk`).
- **The story in the sky** (screen-space overlays, `sky()`): ember glow on the edges, a far mountain with a ring of fire (the first forge), a gold light
  with an empty seat (the gods' hall), nine chains that appear one by one and fail one by one, burning roots, sparks; the sea warms from blue to red
  and back (`WARM`); the summoning is a ring of light with runes and a light column on the deck (`summon()`).
- **Narrator**: seven lines in `LINES` (about 140 words, epic and solemn) shown as subtitles and read by `speechSynthesis` (`speak()` in `cutscene.js`:
  English `en-GB` or Swedish `sv-SE` by the language setting, a male-sounding voice if one exists, pitch .78, rate fitted to the slot, silent when the
  sound setting is off or no voice exists). Swedish text is written by hand in `scripts/sv-translations.txt`.
- **Audio**: synthesised in `game.js` (`CutsceneAudio`): `sea_bed` (62 s of swell and a thin wind), `creak`, `ember` (a rumble under the history),
  `chord` (the summoning), `thud`.
- **Checks**: `cargo test cutscene` (12), `tests/intro-ui.cjs` (19 checks: lock, narration order and language, subtitles, the sea on the canvas, no skip for a
  first character, a held key skips a replay and silences the narrator, the full minute and control back; `MUTATE=lock|skip|narrate` fail it).
