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
