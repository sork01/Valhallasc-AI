# GM test menu (2026-10-23)

For the game master character only (`[GM]Sork`, `Character.gm`). A window (button **Test** beside the visibility badge, or `/gmtest`) and console commands send `debug` ops; the server runs them only for the GM (or a private test world with `VALHALLA_TEST_COMMANDS=1`) and logs every one. Server: `server/src/world/gm_test.rs`; client: `client/gmtest.js`, `client/gm.js`. Checks: Rust `cargo test gm_test`, `tests/gmtest-ui.cjs`.

| Action | Window | Command | Op |
|---|---|---|---|
| list dungeons, gauntlet levels, multipliers | opens the window | `/gmtest` | `gm_test_info` |
| enter a dungeon copy at door / final boss / pack N, any gate | Dungeon: Enter | `/dungeon <zone> [door\|boss\|pack N] [level] [green\|blue\|purple] [mercs]` | `gm_dungeon_enter` |
| reset the copy (enemies back, everyone healed, GM kept in place) | Reset copy | `/dungeon reset` | `gm_dungeon_reset` |
| enrage clocks / skip to the enrage start | Enrage clock, Skip to enrage | `/dungeon enrage [skip]` | `gm_enrage` |
| arena gauntlet at a quest level and fight 1-5, no quest | Arena gauntlet: Start | `/gauntlet <level> [fight]` | `gm_gauntlet` |
| difficulty multipliers | sliders | `/tune <key> <x>`, `/tune reset` | `gm_tune` |

Rules worth knowing:

- **Enter** makes the GM visible (a hidden GM is ignored by monsters and cannot be in a party) and keeps `visible_zone` in step, picks a free copy through `instance_for` (a party mate's, else a free one), and stands the hero 6 tiles from the boss or pack on the door's side. The Chained Forge raid is offered alongside ordinary dungeons; GM entry bypasses its normal key and ten-fighter door checks. A pack is a cluster of pack-kind spawns (`elite-power.txt` damage factor above 2, linked within 10 tiles, at least 3), numbered in spawn order.
- **Level** sets the dungeon's level (`levels[0]`, else `min_level`). **Gear** equips a full set through `gauntlet::gear_set(class, level, rarity)` (blue = rare, purple = epic, which exists only at the tens 10..90); the old pieces stay in the bags. **Mercs** dismisses the old hired fighters and fills up to four seats for an ordinary dungeon or nine for the raid through `place_mercenary`, for free. The option shows the selected dungeon's hire count and keeps that selection after refreshing. A full raid has two of each class including the GM; raid hires use raid contracts and depart when the GM leaves the raid. Re-entering replaces hires instead of stacking them.
- **Multipliers are scoped.** `pack_damage`, `boss_health` and `enrage_start` live on the GM's dungeon copy (`Instance.tuning`), `opponent_health` and `opponent_damage` on the GM's gauntlet run (`Run.opponent_*`). They are in memory only, reset when the copy resets or the server restarts, and never touch `elite-power.txt`, `enrage.txt` or another player's copy. Pack damage applies to kinds with an `elite-power.txt` damage factor above 2 at the two damage sites (`update_slime`, `fire_enemy_bolts`); boss health rescales the living bosses of the copy (a reset re-applies it); the enrage start goes through `World::tuned`/`tuned_enrage_factor`, which the boss mechanics (Eye, Thunder Heart, Solar Heart) use too. Values must be 0.05 to 10.
- **Enrage clock** runs only while a boss fights someone within 14 tiles: skip moves bosses that are fighting; an idle boss resets to 0 on the next tick.
- **Gauntlet test runs** have an empty quest id, so no quest is read or written and nothing is claimed; the run starts at fight N with the fixed class order (Warrior, Mage, Assassin, Priest, Hunter), returns the GM to where they started, and is refused inside a dungeon, an arena, a duel or another run.
- An older server answers `unknown variant`; the window then says the server needs the new release.
