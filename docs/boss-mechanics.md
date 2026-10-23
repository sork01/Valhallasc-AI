# Final boss mechanics

Design for the `BOSSMECH-*` tasks in [TODO.md](../TODO.md). Owner's request (2026-10-17): every final boss gets a gimmick, for example a big area attack with a five-second cast that kills anyone still in it, or a boss that turns invulnerable and spawns adds that must die to end it. The engine and all sixteen boss mechanics are built (see below). Every number is a starting value to tune with the dungeon harness (`BOSSMECH-CHECK`).

A **final boss** is the monster named in a dungeon's `final_boss`: sixteen of them. Open-world elites (Cinderlord, Gloomroot, the group elites) and the dungeons' middle bosses are not covered; say so if they should get the same treatment.

## Rules every mechanic follows

1. **Announced.** Every lethal or heavy effect shows a telegraph for its whole cast (red = hurts, blue = stand here, a dashed line = a path that is about to be used), the boss's cast bar with the ability name, a short banner line and a sound cue. A death says what killed the player ("Killed by Crown's Fall"), so a wipe teaches.
2. **Long enough.** An instant kill is cast for at least 5 s, a heavy hit at least 3 s. Players walk at 5.2 tiles/s, so a safe spot must be reachable from **anywhere in the arena in at most 60% of the cast time**. A unit test walks the arena grid for each mechanic and fails on any point that cannot get out.
3. **No class is required.** The answer is movement, damage or a kill order that every class has. A dash or a stun is a shortcut, never the only answer. (Breaking a channel is a damage threshold, not an interrupt.)
4. **Lone players still die, parties still win.** The dungeon rules of `docs/dungeon-solo-report.md` stand: the boss must kill a lone player and a party of five in green gear (hired mercenaries count as party) must beat it. A mechanic that only matters with several players (rescue, soak, split) is fine: alone it is just one more way to die.
5. **One signature per boss, plus one escalation** at low health, and no two bosses share a signature. The table below is the whole list.
6. **Fresh every pull.** State belongs to the dungeon copy and the fight; a wipe or an evade resets every timer, add, pearl and brazier.
7. **The fight clock keeps running.** The soft enrage (`world/enrage.txt`) counts through an invulnerable phase, so a mechanic cannot be used to stall. Each boss's enrage start is re-derived after its mechanic is in (the mechanic adds time).
8. **Rewards, XP and drops do not change.**
9. **A sign explains it before the door.** Every final boss has a sign in the last room (`BOSSMECH-SIGN-ENGINE`, `BOSSMECH-SIGNS`) that says what the boss does and what to do, in words a child of about eight can read, with a picture of the telegraph in the fight's own colours. The sign's numbers come from the same constants as the mechanic, so they cannot drift.
10. **The fallen stay down (`BOSSMECH-DEATH`, 2026-10-19).** A hero or hired fighter who dies while a final boss fight runs in their zone lies where they fell, the defeat screen says "You have fallen. Wait for the fight to end.", and they wake at the dungeon's door only after the fight is over: the boss dies, or nobody is left standing and the boss walks home (evade). The usual three seconds start when the fight ends, for everyone who is down at that moment together, so the first to wake cannot pull the boss back onto the rest. A death before the boss wakes is an ordinary death; a fight that lasts ten minutes (`FALLEN_HOLD_MAX`) lets the fallen go anyway. Because a death now costs the rest of the fight, a mechanic that kills must be one a careful player can answer every time.

## Settled numbers (`BOSSMECH-RULES`, 2026-10-17)

All of these live once in `server/src/bossmech.rs`; the engine, the client, the signs and the harness read them. They were settled as defaults while the owner was away, so each is one constant to flip.

| Question | Decision |
| --- | --- |
| Shortest cast | Instant kill and "kill outside" 5 s, heavy hit 3 s (`INSTANT_KILL_MIN_CAST`, `HEAVY_HIT_MIN_CAST`). |
| Reachability | Safe spot within 60% of the cast at 5.2 tiles/s, the Warrior's speed and the slowest class (a test keeps the constant equal to the slowest class). A 5 s cast allows 15.6 tiles, a 3 s cast 9.36. |
| Telegraph colours | Red `#e0453b` hurts, blue `#3f9bea` is safe, a dashed pale-gold `#f1e3b4` line is a path about to be used, green `#4fc26b` is the gap in a moving wall. The same four on every sign. |
| Defences against a kill | A kill ignores defence, dodge and dash invulnerability: where you stand at the end of the cast decides. A dash is still a way to cross a telegraph in time. |
| God mode | Test and GM god mode still block mechanics, so a manual test is not cut short. The cast and telegraph still run and the log says "Would have been killed by ...". Players in a city and hidden GMs are never targeted. |
| Death name | "Killed by <ability>" in the log and on the defeat screen; the ability name is the one on the boss's cast bar. |
| Enrage clock | Runs through an invulnerable phase (rule 7). |
| Marks | A marking mechanic marks at most 3 players and never everyone. |
| Elites and middle bosses | Not covered for now; revisit after `BOSSMECH-CHECK`. |

## Building blocks

`BOSSMECH-ENGINE` builds these once; the sixteen bosses only combine them.

| Block | What it does | Used by |
| --- | --- | --- |
| `zone` | A ground shape (circle, ring, cone, lane, half-arena) with a cast time and an effect: kill, heavy damage, or "kill unless you stand inside". | Choirmother, Hierophant, Echo, Sovereign |
| `shield` | The boss takes no damage until a condition holds: every add dead, every object broken. | Choirmother, Coral Regent |
| `adds` | Spawns monsters at set points, optionally with a deadline effect. | Choirmother, Worldseed |
| `mark` | A countdown debuff on chosen players that resolves at the end: a burst, a beam, a tether. | Rain Crown, Labyrinth |
| `sweep` | Something that moves across the arena on a schedule: a wall with gaps, a rotating beam, a bouncing line. | Elder, Axis, Labyrinth |
| `break` | A channel the party must cancel by dealing a damage threshold within a time. | Hollowking |
| `stasis` | A player is frozen until allies break the cocoon. | Last Memory |
| `split` | The boss divides, with a rule that links the halves. | Crucible |
| `hold` | Standing at a place for N seconds completes it (`world/hold.rs` already does this for wards). | Solstice |
| `echo` | Records a cast and plays it again later at the same place. | Moonwell Echo |
| `gaze` | A line-of-sight attack: only cover (an obstacle that blocks `Map::line_clear`) helps. | Unblinking Eye |

## The engine (`BOSSMECH-ENGINE`, built 2026-10-17)

The data is `world/boss-mechanics.txt`, a JSON object keyed by the final boss's monster kind; it ships as `{}` and the sixteen boss tasks fill it in. The schema, the shapes, the beam bounce and the fairness walk are pure code in `server/src/bossmech.rs`; the state machine that runs a fight is `server/src/world/boss_mechanics.rs`. The table is validated when the server starts (`bossmech::shipped()` panics on a bad entry), so a cast under its floor or a typo in a field name stops the server rather than shipping.

Each boss lists `mechanics`; each has a `name` (the cast bar and "Killed by <name>"), an optional health window (`hp_max`, default 1, and `hp_min`, default 0: an escalation is a second entry with a lower `hp_max`), and a `block`. A boss with `inner_arena: true` uses the smallest authored room containing it for floor shapes when rooms overlap; Vael's 12-by-12 chamber sits inside a much larger nave room, and the three 2.5-tile safe circles must cover that chamber within the five-second warning. A boss in a map with no rooms can specify `arena: [x0, y0, x1, y1]`; the Moonwell Echo's bounds cover its final platform instead of the whole 128-tile map.

| Block | Fields | Notes |
| --- | --- | --- |
| `zone` | `shape`, `effect` (`kill`, `heavy`, `kill_outside`), `heavy`, `cast`, `every`, `first`, `repeat`, `repeat_gap`, `alternate`, `echo`, `linger` | Shapes: `circle` (with `inner` for a ring, `at` boss, target or random), `cone`, `lane`, `half`, `arena`, `islands`, `lit`. `alternate` makes a repeated half-room cast strike the opposite side of its crease. `echo` lands the same shape again after each delay and leaves a pale copy. `linger` keeps the landed shape dangerous until it fades. `kill_outside` goes with `islands` and `lit` only. |
| `shield` | `steps` (`hp`, `tag`, `count`, `still`), `heal_per_s`, optional `ordered` (`deadline`, `heavy`) | Wakes sleeping monsters of `tag`; no damage reaches the boss until they are all dead. With nothing to wake there is no shield. Ordered shields allow only the lowest numbered living helper to take damage and give each number its own heavy-hit deadline; their first step may start at full health. Sigrun: [raid-boss-4.md](raid-boss-4.md). |
| `adds` | `tag`, `count`, `every`, `first`, `scatter`, `still`, `bloom` (`after`, `heal`, `then`) | A bloom removes the add, heals the boss and wakes one `then` add where it stood. |
| `mark` | `count`, `every`, `first`, `cast`, `effect` (`burst` or `beam`), `waves`, `wave_gap`, `linger` | At most 3, never everyone, at least one; the ring or beam follows the bearer; the bearer is never hurt by their own mark. A burst can leave a red puddle for `linger` seconds; the bearer is also safe from their own puddle. |
| `sweep` | `kind` `walls` (`warn`, `speed`, `thickness`, `gap`, `walls` with `from` and `gap` low, high, middle or random) or `spokes` (`count`, `width`, `deg_per_s`, `reverse_every`, `reverse_warn`, `length`) | Walls are dashed for `warn`, then red; the green gap is safe. Spokes turn about the arena's centre and are lethal to touch. |
| `break` | `cast`, `every`, `first`, `bar`, `stun`, `vulnerable` | The boss is held still; damage from anyone fills the bar (a share of its maximum health); broken: stunned and `vulnerable` extra damage; unbroken: everyone in the fight dies. |
| `stasis` | `every`, `first`, `orbs`, `speed`, `life`, `tag`, `hold` | Orbs seek players; a touched player is frozen (no input, no damage) in a cocoon (a sleeping monster of `tag`); kill the cocoon to free them, or they are lost after `hold`. |
| `split` | `hp`, `tag`, `revive_after`, `survivor_bonus`, `bridge` | The boss and its partner keep half the remaining health each. A body that would fall while the other lives is left on 1 health and downed; the other falling in time finishes both, otherwise it rises with half its health and the survivor hits harder. |
| `hold` | `points`, `r`, `hold_for`, `lit_for`, `snuff_every` | A place is lit by standing in it; lit places are the safe discs of a `lit` zone. |
| `static` | `limit`, `warn_at`, `per_hit`, `r`, `rods`, `rod_r`, `immune`, `dark` | Every blow a hero lands on the boss adds `per_hit` charges to that hero; at `limit` they detonate (kill within `r` of them, themselves included). Standing on a ready rod clears the charge, gives `immune` seconds in which none builds, and darkens the rod for `dark` seconds. A banner at `warn_at`. The charges, the rods and the detonation show in the snapshot (`static`, rod teles with `rod: true`). At least two rods. |
| `gaze` | `cast`, `every`, `first`, `cover`, `regrow`, `sweep`, `beam` | Everyone with a clear line (`Map::line_clear` and standing cover) is struck at the end of the cast; with `sweep` a beam turns once round the room instead. Cover cracks after one gaze that it shielded someone from, breaks after two, regrows after `regrow`. |

Things worth knowing:
  * `every` runs from one start to the next, and `validate` insists it is longer than the whole sequence (casts, repeat gaps, echoes).
  * Adds are the sleeping monsters the map already holds (spawns with `ambush: <tag>`, state `waiting`); the dungeon's data places them, the mechanic only names the tag. A fight puts every one it woke back to sleep when it ends.
  * A fight starts when the boss is awake and fighting and ends when it dies, walks home or its copy is reset. It belongs to one boss slot, so dungeon copies never share state.
  * The snapshot carries `bossMech` (one entry per running fight: `cast`, `break`, `tele` with colour and shapes, `marked`, `frozen`, `shield`, `stunned`, `partner`, `banner`). Events: `bossmech` with a `phase` (`cast`, `land`, `add`, `shield`, `broken`, `bloom`, `frozen`, `split`, `down`, `rise`, `reverse`) and `immune` for a blow the shield swallowed. A death event carries `cause`.
  * `cargo test boss_mechanics` and `cargo test bossmech` run the engine's tests; `every_shipped_boss_is_fair_and_its_tags_exist_in_the_map` reads whatever the sixteen tasks add and fails on a point with no way out in time or a tag with no sleeping monster behind it.
  * Found while building it: the design's *Moon Lance* has a 3 s cast and kills, which is under the 5 s floor of rule 2; `BOSSMECH-MOONWELL-ECHO` has to lengthen it to 5 s or make it a heavy hit. The Flooded Cloister's boss room is 8 by 8 tiles and *Toll of the Deep* is a ring of radius 8, which fills the room: the fairness walk lets players run out of the door, but the room (or the ring) may need to change in `BOSSMECH-CHOIRMOTHER`.

## The client (`BOSSMECH-CLIENT`, built 2026-10-18)

`client/bossmech.js` (`window.BossMech`) draws what the snapshot's `bossMech` says and nothing else; `field.js` feeds it (`update` in `applySnapshot`, `drawFloor` after the ground decals, `drawHud` before the minimap, `onEvent` for the death cause).

  * **Floor:** every shape is projected as a polygon (circle, ring with the even-odd rule, cone, lane, half-arena cut to the room that holds its point, room rectangle). Red hurts (it fills in as the cast runs, a circle grows from its centre, it flashes in the last second), blue is safe (a brazier being lit gets a bright arc), a dashed pale-gold outline is a path about to be used, green is a wall's gap, an echo is a pale dashed copy. Cover pillars, orbs, the gaze's source eye, and rings under marked (red) and frozen (amber) players.
  * **Screen:** the cast bar (ability name, red fill, countdown), the break bar ("Deal damage to stop it!"), the shield counter ("Invulnerable", the name, "n of m left") with a bubble round the boss, "Stunned" over the boss, "Marked!" and "Frozen!" over players, and the banner unless it only repeats the cast name. Drawing units match the field's 1600-wide canvas; the bar is `min(360, width - 40)` wide.
  * **Death:** "Killed by <ability>" under "Defeated!" (`#dead-cause`), "You were killed by <ability>." in the system tab, a heavy hit's `cause` replaces the monster name in the hit line.
  * **Sound:** four cues from the dybase2 project `c0e0eb6be0aa5149` ("Valhalla Boss Mechanic Cues"), `client/assets/sfx_boss_{warn,land,shield,broken}.mp3`, played by `bossMechSound` in `game.js` for the `bossmech` event phases (`cast` and `reverse` warn, `land` land, `shield` and `frozen` shield, `broken` and `rise` broken, `down` and `split` land). To change one, edit the project, render the bar (`render_audio` with `from_bar`/`bars`), and re-encode (96 kbps mono, high-pass 25 Hz, peak about -1 dB).
  * **Swedish** is written by hand (`sv-data.js` and the two caches under `scripts/`). Canvas text goes through `Locale.translate`; an ability's name, its banner and its Swedish come from the boss's own task.
  * **Render cost:** no filters, no blur, no per-frame allocation beyond a shape's points; reduced motion removes the pulse, the dash crawl and the flash.
  * **Test:** `npm run test:bossmech` (`tests/bossmech-ui.cjs`). The private server loads a test table through `VALHALLA_BOSSMECH_FILE` (only with `VALHALLA_TEST_COMMANDS=1`, `World::load_boss_table_file`, validated like the shipped one), so a browser can watch a real fight on a plain slime.

## The signs (`BOSSMECH-SIGN-ENGINE`, built 2026-10-18)

A sign stands before each of the sixteen final bosses. The engine is done; the real wording and the sign's place in each boss's done check belong to `BOSSMECH-SIGNS` and the sixteen boss tasks.

  * **Data:** `world/boss-signs.txt`, keyed by the final boss's kind (unique per dungeon, the same in every private copy): `x`, `y`, `title` (the boss's name), `what`, `todo`, `tip` (at most 150 characters each) and `colors` (one to four of `red`, `blue`, `path`, `green`, none twice). `server/src/bosssign.rs` loads and validates it at start-up. **The text of all sixteen is a shared placeholder** ("This boss has a special trick." ...) until `BOSSMECH-SIGNS` replaces it; it is never seen, because a sign is only listed for a dungeon whose boss has a mechanic in the live table (`boss.table`). So the first sign appeared with `BOSSMECH-HOLLOWKING` (2026-10-18), and a sign can never describe a fight that is not there.
  * **Where:** `scripts/place_boss_signs.py` (`--write` merges the spots into the data, keeping the words). The rules, which `signs_stand_where_the_rules_say` checks on the shipped data: free reachable ground with open ground round it; in a room that does not hold the boss; nearer the arrival point than the boss; at least the boss's awareness plus 2 tiles from its home (the script uses 18, above every awareness); at least 2.2 tiles from the shortest walk to the boss; at least 3 tiles from every monster home, portal and townsperson; beside the point where that walk first comes within 22 tiles of the boss. Chests keep 3 tiles from a sign (`chest_spot` treats it as a townsperson). Rerun the script after any change to a dungeon's map.
  * **Server:** `server/src/world/boss_signs.rs`. The snapshot lists `signs: [{id, x, y, title}]` for the zone (nothing it says). `sign_read {sign}` answers `{type:"sign", sign, title, what, todo, tip, colors}` within `READ_RANGE` (2.8 tiles, as for a townsperson) of a living hero, stops the hero, and otherwise answers an error ("Walk closer to read this sign." / "There is no sign to read here."). The words leave the server only here.
  * **Client:** `field.js` keeps `signs`, draws a wooden board on a post with a gold "!" that glints (canvas for now; the pixel art through PixelFlow in the dungeon's own style is still to do), and treats a sign like a townsperson: F within 2.8 tiles, or a click that walks up first (`talkTo` / `askNpc`). `client/bosssign.js` (`window.BossSign`) shows the window: title, a picture strip of the colours (taken from `BossMech.colors`, so a sign and the fight share the four colours), then **What it does**, **What to do**, **Good to know**, and Close. It does not pause the game. Esc, the cross, Close and walking away close it. It fits 844 x 390 (the Close button hides under 520 px height; the cross stays, 44 px on touch).
  * **Swedish** is by hand: `build_swedish.py` now harvests the keys `what`, `todo` and `tip` of the world files, so each line of a sign needs its Swedish when it is written.
  * **Tests:** Rust `server/src/world/boss_signs_tests.rs` (sixteen signs and nowhere else, validation with a mutation per field, no jargon words, placement rules, snapshot gating, reading, chests keep clear, mutation-checked by removing the chest clearance) and `npm run test:bosssign` (`tests/bosssign-ui.cjs`: drawn, F, click-and-walk, the four ways to close, reload, phone size, no sign elsewhere, Swedish).
  * **Numbers on a sign** are plain text; `the_sign_before_haldor_says_what_the_dirge_really_does` (boss mechanics tests) checks that "8 seconds" is the dirge's `cast`, so the words cannot drift from the table. Each boss task adds the same kind of check for the numbers its sign names.
  * **Not yet:** the sign art (all sixteen texts are written).

## Helpers of the mechanics: sleepers, art and loot (2026-10-18)

Six monsters exist only to serve a mechanic: the **Bound Singer** (`choirsinger`, Flooded Cloister), the **Reliquary Pearl** (`reliquarypearl`, Coral Reliquary), the **Worldseed Seed** (`seed_sprout`) and **Bloom Treant** (`seed_treant`), **Cinder of the Crucible** (`solar_cinder`) and the **Amber Cocoon** (`amber_cocoon`). They are catalog enemies marked `"add": true` with an `artFrom` kind, in the dungeons' content scripts (`cathedral_content.py`, `seed_vault_content.py`, `solar_crucible_content.py`, `yearwheel_dungeon_content.py`).

  * **Placed, asleep:** `scripts/place_boss_adds.py` adds the sleeping spawns (tag in `ambush`) round each boss and checks that every `hold` point and every `static` rod of the table stands on free, reachable ground in the boss's room. It is idempotent and runs after the dungeon generators (`generate_sealed_dungeon_maps.py` rebuilds zones 29 to 39 without them), then `node scripts/sync-world.cjs`. Counts: 10 singers (4 then 6), 10 pearls (3 + 3 + 4) and 2 Reliquary Crabs, 8 seeds and 10 treants, 1 Cinder, 6 cocoons.
  * **Used again:** a long fight can use up the sleepers (Germination plants every 30 s). `wake_adds` takes sleepers first, then a helper of the same fight that has since died; Amber Stasis does the same for cocoons. A helper that fell is listed once in `fight.woken` and is put back to sleep when the fight ends.
  * **Drop nothing:** a kill of an `add` gives experience and nothing else (no gold, material, bag, licence or gear roll), so a recycled seed cannot be farmed.
  * **Art:** each has its own cel-shaded PixelFlow art since 2026-10-18 (`scripts/boss_helper_cel_redraw.py`; `python3 scripts/boss_helper_art.py all` builds, exports and verifies; `sheet <dir>` writes FileDrop sheets). They no longer carry `artFrom`, so the client loads `cathedral_<kind>.png`; `scripts/boss_add_art_aliases.py` is now a no-op that stays for any future borrowed helper. The Bound Singer is a chained choirboy ghost with a shackle ball, the Reliquary Pearl a pearl in an open shell whose lid snaps shut on its slam, the Worldseed Seed a walking seed with a sprout and a glowing crack, the Bloom Treant a blossom-crowned wooden guard, the Cinder a cooling lump of coal with a flame tuft, and the Amber Cocoon a tall amber egg with the sleeper inside. Sleepers are not drawn, so check them awake or from the atlas.
  * **Tests that count a dungeon's monsters** skip the sleepers (`ambush` is set).

## The brain of a fighter who is not at a keyboard (`BOSSMECH-MERC`, `BOSSMECH-HARNESS`)

`server/src/world/boss_play.rs`, one brain for the hired mercenaries (`merc_think`) and the dungeon harness's bots (`ttk.rs`): `World::boss_play(session)` returns `BossPlay { goal, target, hold_fire, stay }` from the fight's own state, never touching the player. The harness answers it by walking and choosing a target; a mercenary by setting its goal and target. The rules, in order:

  1. **Telegraphs.** `bot_threat` is the soonest positional danger at a place (the danger query without a break bar's "deal damage", plus a seeking orb and the lethal bridge between a divided boss's bodies). A fighter on the edge of one (within half a tile) runs to the nearest safe place to the boss, with a margin, keeps that place until it is reached, and holds fire (a dash toward the boss would undo the step). While a telegraph is up and the fighter is outside it, it **stays out** until it has landed (walking back to the target put the party on the ring's edge at the landing).
     Added 2026-10-19 (`BOSSMECH-DEATH`, found because a fall now costs the rest of the fight): against the dark of the Longest Night the way out is the nearest **burning brazier** that is still lit when the dark falls and can be reached in time (a ring of samples missed a brazier 15 tiles off, and the "reachable" test used a full-width line that a fighter pressed against a wall fails in every direction); while a kill zone is up, a fighter on safe ground stays there instead of walking off to light another brazier. The party went from 0 of 4 to 4 of 4 on Solstice Heart with 0 falls.
  2. **Walls and spokes** are dodged by a search through space and time (half-tile cells, quarter-second steps, a step may not cut through a band, a 0.5 tile margin): `Ok(None)` means "stay here, this is safe".
  3. **A mark.** A bearer goes where the ring or the bouncing beam misses their friends; a friend beside a ring leaves it.
  4. **Static.** A hero with `warn_at` charges walks to the nearest ready rod and holds fire.
  5. **Braziers.** While fewer than three burn (or are being lit), the nearest free fighter takes the nearest dark one, keeps the claim until it burns, and holds fire.
  6. **Divided boss.** Hit the body with more health left, from its far side, away from the bridge.
  7. **Targets before the boss.** A friend's cocoon, a shield's helpers (spread over the party by rank), a seed, any helper of the fight within 7 tiles, then the boss.

Harness switches: `DUNGEON_BOSS_BOTS=ignore` plays the party without the brain (to measure that ignoring loses), `DUNGEON_BOSS_TRACE=1` prints the fight every 5 s and each fall with its cause. The party check now counts **falls** (every time a member went down), and a fighter who fell stays down until the fight is over (`BOSSMECH-DEATH`; the harness used to put a fallen bot back after 20 s, a run back that no longer exists). Found while building it: a bot whose target the engine had cleared stood still for the whole fight (the old Bloom Heart and Solstice Heart "cannot beat" notes were this), and the enemy-separation push could shove a boss through a one-tile dungeon wall (`separate_enemies` now refuses a move through a wall).

## The sixteen mechanics

### 1. Haldor, the Hollow King — The Undervault (level 20): *Dirge of the Hollow*

The first dungeon is the gentlest: one mechanic, no kill-on-sight ring, no shield, and a generous margin.

- Every 30 s Haldor raises his crown and **channels for 8 s** while a blue break bar sits over his head. If the party deals damage to him equal to the bar before it ends, the dirge breaks: he is stunned 6 s and takes +30% damage. If not, the dirge ends in the **Hollow Wail**, which kills everyone.
- Tuning rule: the bar is set so a green party of five breaks it with **about 5 s to spare** (an early party is still learning), and a lone player never can. The damage counts from everyone, so no class is needed. The harness measures the number (roughly 5% of his health to start).
- No escalation: the same dirge for the whole fight, only a little more often (every 25 s) below 30%.

**Built 2026-10-18 (`BOSSMECH-HOLLOWKING`).** `world/boss-mechanics.txt` holds two `break` entries named *Dirge of the Hollow* (the name on the cast bar and in "Killed by ..."): `hp_min` 0.3, `every` 30; and `hp_max` 0.3, `every` 25 (an interval counts only while its window is open, so the quicker song first comes 25 s after he drops to 30%). Both: `cast` 8, `bar` **0.035** of his maximum health (about 4,000 damage), `stun` 6, `vulnerable` 0.3. The first song starts 30 s into the fight. The bar was tuned with the harness (`DUNGEON_SOLO_DUNGEONS=undervault DUNGEON_SOLO_KINDS=hollowking`, the party check prints "breaks with a/b/c s to spare" per dirge):

| Bar | Green party of five (bots, 12 to 16 seeds) | Lone purple (24 seeds, Assassin, Priest, Warrior) |
| --- | --- | --- |
| 0.030 | breaks with 4 to 5 s to spare, won 10 of 12 | an Assassin lived 180 s in 1 of 4 early runs |
| 0.035 (shipped) | breaks with 3 to 5 s to spare (mean about 4), won 11 of 16 | **none lived** in 144 runs (died at 38 to 158 s) |
| 0.040 | 2 to 4 s to spare, won 10 of 16 | none lived (24 Assassin runs) |

The target of "5 s to spare and a lone player never can" cannot both hold with a pure damage threshold: a lone purple Assassin deals about 45% of what a green party of five does, so a bar the party clears with 5 s spare is cleared by that Assassin in about 7 s. The lone rule (rule 4) is the hard one, so the bar sits where no lone hero survived and the party still breaks with about 4 s to spare. The bots lose the party runs they do lose in a lull of skill cooldowns (the boss hp stops moving for 5 s), not at the bar: they have no basic attack of note and do not stagger bursts the way the sign tells players to. A real party that bursts on the cast has more room. Redo this in `BOSSMECH-HARNESS` with bots that save cooldowns for a channel.

The harness changes that came with it: a boss that has a mechanic is not cut off by the 30 s "hopeless" projection (its wail can end the fight any moment), the bots walk up to a boss that is held still (`walk_up_to_a_held_boss`: a channelling boss does not come to a party that stands where the fight began), and the party check prints each broken dirge's spare seconds (`BossMech::spare`, test builds only). `the_colossus_and_hollow_king_fall_faster_to_five_than_three` (vault tests) no longer requires a trio to win or to be hurt more: the dirge asks a real party's damage, so a trio may lose.

**Changed 2026-10-19 (`BOSSMECH-MERC-ALONE`).** Haldor's health went from 130,000 to 160,000 (a hired five now takes about 88 s, not 60 s), and the bar from 0.035 to **0.0285** of it so the damage the Dirge asks for in 8 s is the same 4,550 as before (the bar is a share of his health: 23% more health would have asked 23% more burst, which the hired party of the vault test could no longer give).

### 2. Elyss, Mother of the Bound Choir — Flooded Cloister (level 40): *Toll of the Deep* and *the Bound Chorus*

Both of the owner's examples, at the first dungeon where a party has had practice.

- **Toll of the Deep.** Every 25 s Elyss rings a drowned bell. A red ring (radius 8 round her) fills over a **5 s cast**; anyone inside when it lands dies. Melee has to step out and back in. The bar reads "Toll of the Deep".
- **The Bound Chorus.** At 66% and 33% health Elyss is **invulnerable** behind a pale shield of song and four Bound Singers (the Cloister's Bound Cantor model, weak) rise. The shield falls when all four are dead; killing them takes about 15 s for a green party. The toll keeps coming during the chorus.
- Escalation: at 33% the chorus is six singers and the toll comes every 18 s.

**Built 2026-10-18 (`BOSSMECH-CHOIRMOTHER`).** *Toll of the Deep* is a `zone` circle of radius 8 round Elyss, kill, 5 s cast, every 25 s (every 18 s below 33%). *The Bound Chorus* is a `shield` with two steps (66%: 4 singers, 33%: 6) over ten sleeping Bound Singers (`choirsinger`, 14,000 health each). The Cloister's boss room is 28 by 28, so the ring leaves room to run (the 8 by 8 corridor the engine notes mention is a path, not the arena). Elyss's health went from 330,000 to 250,000 with the mechanics in (a win takes about 70 to 80 s). Sign, hand-written Swedish and a diagram (the red ring with four singers waiting) are in; a test keeps the sign's "5 seconds" equal to the cast.

### 3. Queen Avariel, the Coral Regent — Coral Reliquary (level 45): *Pearl Shell*

- At 75%, 50% and 25% Avariel closes into a **pearl shell**: invulnerable, and she **heals 2% of her health per second** while it stands. Three Reliquary Pearls grow at marked spots round the room (stationary monsters, about 4% of her health each, each with a small pulse of damage to anyone adjacent). The shell opens when all three are broken.
- Escalation: at 25% there are four pearls and two Reliquary Crabs.

**Built 2026-10-18 (`BOSSMECH-CORALREGENT`).** *Pearl Shell* is a `shield` with three steps (75%, 50%, 25%: 3, 3 and 4 pearls, all held still) and `heal_per_s` 0.02, over ten sleeping Reliquary Pearls (`reliquarypearl`, 16,000 health, 4% of hers). *Reliquary Crabs* is an `adds` block that wakes the two sleeping Reliquary Crabs (`reliccrab`, tag `shellcrab`) when her health is at or below 25%. They are not part of the shield (the shell opens when the pearls are gone) and are free to move. The pearls' "small pulse" is not built: a held monster cannot strike.

### 4. High Hierophant Vael, Heart of the Tide — Grand Nave (level 50): *Rising Tide*

The reverse of the king's ring: here you **must stand inside** the circle.

- Every 35 s the nave begins to flood. A **5 s warning** lights three dry **islands** (blue circles, radius 2.5); when the flood lands, anyone standing in the water dies, and the water drains again after 4 s.
- Islands are spread so that none is more than 60% of the cast away from any point; they appear in new places each time.
- Escalation: at 30% there are two islands and the flood comes twice in a row, with the islands moving between the floods.

**Built 2026-10-18.** The 5-second, 2.5-tile island casts run in Vael's nested 12-by-12 chamber (`inner_arena`), so every walkable point reaches safety in time. The landed flood remains dangerous for its 4-second linger. The second cast uses two newly chosen islands. The sign has a three-island picture, matching numbers and hand-written Swedish.

### 5. The Moonwell Echo — The Moonwell (level 60): *Echo*

- Every 15 s she casts a **Moon Lance**: a red lane across the room, **3 s** to land, lethal. A pale copy of the lane stays on the floor, and **3 s after the first one lands the same lane lands again.** Her slam ring does the same: it lands round her, then again round the same spot after she has moved.
- The lesson is not to step back into where it just was. Escalation: at 40% the echo comes after 2 s and the echo itself echoes once more.

**Built 2026-10-18.** Moon Lance and the ring each record their landing shape, then strike the same place after 3 seconds, or twice at 2-second gaps below 40%. The lethal Moon Lance warns for **5 seconds**: its proposed 3 seconds conflicted with the shared instant-kill cast floor. The `arena` bounds cover the Moonwell's final platform instead of the full map, which has no authored rooms. The sign and its lane-and-ring picture explain the repeats in English and Swedish.

### 6. The Unblinking Eye — The Eye Below (level 65): *Unblinking Gaze*

- The lid opens; after a **5 s warning** the Eye sees everything: **anyone in its line of sight dies**. Only cover helps. Six lens pillars stand in the room; a pillar shields everyone behind it, **cracks after one gaze and breaks after two**, and regrows after 45 s, so the party rotates cover while fighting.
- Six lens bases are placed by the Eye Below generator in the boss room. The live cover circles sit on those exact centres; `Map::line_clear` still checks the stone walls, while the gaze checks the lenses separately so a broken lens stops shielding without blocking movement.
- Escalation: at 30% the gaze comes every 15 s and **sweeps** across the room as a rotating beam: hide, then move round the pillar.

**Built 2026-10-18.** The Eye warns for 5 seconds every 25 seconds. Each of the six lenses can shield players twice before breaking and regrows after 45 seconds. Below 30% it warns every 15 seconds and turns a beam through one full circle in 6 seconds. The generator, live cover view, sign picture and hand-written Swedish use the same six positions.

**Changed 2026-10-19 (`BOSSMECH-MERC-ALONE`).** *When the Eye enrages (`world/enrage.txt`, 130 s) every pillar breaks for good and never grows back* (`tick_cover`): from then on a gaze cannot be hidden from. Before, four mercenaries alone still won at 162 to 165 s: the boss is rooted and cannot attack for the whole cast (`hold_still` sets the attack cooldown), 5 s every 25 s and about 11 s of every 15 s below 30%, so the enrage, which only multiplies its attacks, had nothing to multiply. Health 2.2M to 4.2M (the hired five take about 114 s, the bot party about 120 s, four mercenaries alone about 160 s without the enrage and now none win). The party brain had three defects here, found with the harness: the danger query ignored the *turning* beam of the second phase (`danger_list` now notes when the beam reaches a spot, unless cover or the end of the turn is in the way), the flee search chose routes a thin line fits but a body does not (it snagged on a pillar's edge one step short of cover; `flee_spot` tries the body's width first), and a fighter in cover walked back out to the boss before the look landed (a gaze now counts as a telegraph for "stay out until it has landed").

### 7. Heart of the Elder — The Elder Hollow (level 70): *Bramble Sweep*

- Every 20 s two **walls of thorns** (3 tiles thick) rise at opposite edges, shown as dashed lines for **4 s**, then sweep across at 4 tiles/s. Each wall has one **gap** (4 tiles wide) marked in green; the second wall's gap is on the opposite side, so the party has to cross the room between the walls. A wall kills anything it touches.
- Escalation: at 40% the walls come from both axes at once, with the gaps lined up on one cell of a grid.

**Built 2026-10-18.** Two opposite 4-tile gaps cross the room after a 4-second dashed warning; below 40%, four walls approach from both axes with their gaps aligned at the centre. The sign pictures the walls and green gaps and has hand-written Swedish.

### 8. Sovereign of the Last Fold — Thousandfold Pavilion (level 75): *Fold*

- A **crease line** appears through the arena at a random angle; one half is shaded red. After a **5 s warning** that half **folds flat**: anyone on it dies. It unfolds after 3 s. The safe half is never smaller than 40% of the room. Every 22 s.
- Escalation: at 33% a second fold follows the first (a quarter of the room, then the opposite half), and the crease can pass through the boss.

**Built 2026-10-18.** The red half has a 5-second warning and stays dangerous for 3 seconds after landing. Below 33%, the next fold strikes the opposite side of the same crease; both sides leave at least 40% of the arena safe when struck. The sign shows its dashed crease and red half, in English and hand-written Swedish.

### 9. The Rain Crown — Temple of the Rain Crown (level 80): *Downpour*

- Every 25 s a **storm cloud** marks up to three players (never everyone) with a ring (radius 4) that follows them for **5 s** and then bursts as **lethal rain**. Marked players must **spread out and away** from everyone else; unmarked players must stay out of every ring. Rain puddles linger 8 s.
- Escalation: at 40% the marks come in two waves, the second 3 s after the first lands.

**Built 2026-10-18.** Up to three players carry a 4-tile red ring for 5 seconds; each burst leaves a visible, dangerous puddle for 8 seconds. A bearer is safe from their own burst and puddle. Below 40%, the second wave starts 3 seconds after the first lands. The sign shows the three marks, the puddle time and hand-written Swedish.

### 10. Heart of the Worldseed — The Seed Vault (level 80): *Germination*

- Every 30 s three **seeds** are planted at random spots and grow for **12 s**, shown as a bar over each. A seed that blooms becomes a **Bloom Treant** (strong, 3% of the boss's health) and **heals the Worldseed 4%**. Each seed has about 1.5% of the boss's health, so the party has to split to burst them before they bloom.
- Escalation: at 35% five seeds at once.

**Built 2026-10-18 (`BOSSMECH-WORLDSEED`).** *Germination* is an `adds` block: three seeds (five below 35%) every 30 s, scattered, held still, each blooming after 12 s into a Bloom Treant (`seed_treant`, 120,000 health = 3% of the Heart) and healing it 4%. A seed (`seed_sprout`, 60,000 = 1.5%) broken in time blooms into nothing. Eight sleeping seeds and ten treants stand in the boss room, and a seed or treant that fell is woken again, so every 30 s cycle finds its bodies.

### 11. Axis of the Buried Sky — Sunken Astrolabe (level 85): *Orrery Spokes*

- Three **brass spokes** (lanes 1.6 wide, from the Axis to the wall) rotate round it at 20°/s, each 120° from the next. A spoke is lethal to touch. Players run with the rotation, or stand in the gap, which moves at under 3 tiles/s at 8 tiles out.
- The spokes **reverse** every 12 s after a **2 s** warning (a gear symbol and a sound).
- Escalation: at 30% there are four spokes at 21°/s. The proposed 28°/s gives 3.91 tiles/s at 8 tiles, contradicting the under-3 limit above; 21°/s gives 2.93 tiles/s.

**Built 2026-10-18.** Three 1.6-tile spokes turn at 20°/s, then four at 21°/s below 30%. They reverse every 12 seconds. For the final 2 seconds a gear icon appears over the hub and a warning cue plays. The sign sketches the spokes and has hand-written Swedish. **Changed 2026-10-19 (`BOSSMECH-DEATH`):** new spokes (at the start of the fight and when the four replace the three) turn dashed and harmless for 3 s (`SPOKES_ARM`) before they hurt. They begin at a random angle, which could be right where the party stands, and a lethal thing must be announced (rule 1); it never mattered while the fallen came back, and once the dead stay down a party that spawns under a spoke would be lost before it fought.

### 12. Heart of the Stormgate — The Thunderheart Gate (level 95): *Static*

- Every damaging **skill or hit you land adds one Static charge**. At 12 charges you detonate: a lethal burst (radius 5) at your feet. A **Grounding Rod** (four, in the corners) clears all your charge and gives 8 s of immunity to Static; after use a rod is dark for 12 s. So the party has to leave the boss every ~10 s to ground, and cannot all use one rod.
- A banner at 8 charges and a crackle on the hero warn. Escalation: at 30% charge comes in twos and the rods go dark 20 s.

**Built 2026-10-18 (`BOSSMECH-THUNDER-HEART`), with the new `static` block.** *Static*: 12 charges detonate a hero (kill within 5 tiles), a banner and a red ring at 8, one charge per blow (two below 30%), four Grounding Rods in the corners (radius 1.8, 8 s immune, dark 12 s, 20 s below 30%). The rods are drawn as blue circles (grey while dark), the charges as "n of 12 sparks" over each hero. The detonation is the player's own doing and the charge count is the warning, so rule 2's cast floor does not apply to it; a hero who stops hitting is never in danger. `tests/bossmech-static-ui.cjs` watches it in a real browser.

### 13. Heart of the Labyrinth — The Blooming Labyrinth (level 97): *Prism Bounce*

- Every 18 s the Heart **marks a player** with a gem. After **4 s** it fires a lethal beam at where the player stands, and the beam **bounces off the arena walls twice**: all three segments are drawn as dashed lines for the whole countdown. The marked player has to line the bounces up so they miss the others.
- Escalation: at 30% two marks and three bounces.
- Note: this Heart already beats five players in green gear (`DUNGEON-PARTY-CHECK`); ease its health before the mechanic goes in.

**Built 2026-10-18 (`BOSSMECH-BLOOM-HEART`).** *Prism Bounce* is a `mark` with a beam: one friend, 5 s (the shared floor, not 4), two bounces, every 18 s; below 30% two friends and three bounces. The Heart's health went from 7.0M to 13.3M and an enrage start of 114 s was added: the harness bug that hid how easy it was is fixed, and at the old health a party won in 47 s, before the mechanic mattered.

### 14. Heart of the Crucible — The Solar Crucible (level 98): *Twin Suns*

- At 60% the Heart **splits** into Sol (fire: cone bursts) and Cinder (ash: ring bursts), on opposite sides, each with half the remaining health. While both live, a **lethal bridge of sunlight** joins them along the line between the bodies and moves when they do.
- If one dies and the other lives for **more than 10 s**, the dead one rises again with half its health and the survivor gains +50% damage. The party must burst both within 10 s of each other.

**Built 2026-10-18 (`BOSSMECH-SOLAR-HEART`).** *Twin Suns*: at 60% a sleeping Cinder (`solar_cinder`, the ash half, art borrowed from the Heart) wakes beside Sol, both with half the remaining health; revival after 10 s with +50% damage; the bridge of light is drawn as a dashed path for 3 s (`BRIDGE_WARNING`) and is lethal after that. Sol's *Sunburst* is a heavy cone (60% of a hero's health, 3 s cast, every 14 s); Cinder's rings are its own ground-pound. The Heart's health went from 7.6M to 6.0M (some wins took 162 s, near the cap).

**Changed 2026-10-19 (`BOSSMECH-MERC-ALONE`).** *The twins join again.* The split block takes `merge_hp` (0.25) and `merge_defense` (0.5): when a body would fall while the other lives, instead of lying down (10 s) and rising, the Cinder goes back to sleep and the Heart carries on alone **on 25% of its maximum health, taking half of every blow**; no bridge, no rising, no survivor bonus (those fields stay in the table for a boss that has no `merge_hp`; the old tests use them). Sign texts and their Swedish are rewritten. Two engine defects found on the way: a body that rose got its lethal bridge back with **no warning** (the 3 s dashed path is now shown again), and the party brain walked a fighter to the far side of a body in a straight line, **across the bridge** (it now goes round the corner of the corridor, `bridge_station`). The merge adds about 4.3M of effective health (a quarter of the bar at half damage), so the Heart's health went 6.0M to 8.1M to 9.4M to 8.6M while measuring, back to 6.0M, then **6.6M** (time is not linear in it: 6.0M gave about 69 s, 7.8M about 113 s). The brain also hit the body with more health, which sent the melee hirer back and forth across the arena between two bodies that both chase him, and he died to the bridge at about 20 s in every traced run, so the "hired five" fought as four; with merging twins there is no window to balance, so a fighter now hits the **nearer** body (`play_target`). Result (8 seeds, enrage off): hired five 7 of 8 at about 92 s, bot party 7 of 8 at about 117 s, four mercenaries with the hirer down 7 of 8 at about 122 s (91 to 178 s). **Open:** four mercenaries alone still win (hirer idle 3 to 4 of 8: an idle warrior in the room draws the boss and the mercenaries win as fast as the hired five; hirer down 7 of 8), and the spread of times (73 to 119 s hired, 91 to 178 s mercenaries alone) is wider than any enrage start can separate (129 s now). **Later the same day:** the party is driven by the mercenaries' own code (`World::auto_play`), so the hired five got faster (about 70 s at 6.6M); health is now **8.2M** and the enrage start **105 s** (owner). Enrage off, 8 seeds: hired five 6 of 8 at about 87 s; four mercenaries alone: hirer idle 8 of 8 at about 91 s (an idle warrior in the room draws the boss, so they win as fast as the hired five), hirer down 7 of 8 at about 112 s. DPS per class (hired five): assassin 32,700, warrior 25,300, mage 14,600, priest 12,800, hunter 11,500. **Final setup (owner, 2026-10-19):** the bridge no longer kills: `bridge_hit` 0.6 hits whoever stands on it for 60% of their health once a second (`BRIDGE_TICK`; one touch is survived, standing on it is not), which cut falls per fight from 2.8 to 1.4 so the fifth fighter counts; the joined Heart takes 35% of every blow (`merge_defense` 0.35) so the last phase decides whether all five survive; health 8.2M; enrage start **105 s** (not the standard 100: the hired five average about 102 s raw). Enrage on, 8 seeds: hired five 7 of 8, four mercenaries alone 2 to 3 of 8 (runs that end before about 105 s or a few seconds past it). Sign text ("burns hard anyone who stands on it") and its Swedish rewritten.

### 15. The Last Memory — The Amber Archive (level 99): *Amber Stasis*

- Every 25 s two **amber orbs** seek random players. A player they hit is **frozen in amber**: no movement, no skills, no damage taken. The cocoon is an object with about 2% of the boss's health: allies must **break it within 10 s**, or the amber closes and the player is lost. While frozen the player is a target that cannot dodge, so the next attack decides it.
- Escalation: at 30% three orbs, and the cocoon holds for 8 s.

**Built 2026-10-18 (`BOSSMECH-AMBER-MEMORY`).** *Amber Stasis*: two seeking orbs (speed 4.5, a hero can outrun them), 10 s to break the cocoon (`amber_cocoon`, 162,000 health = 2%), every 25 s; below 30%: three orbs and 8 s. Six sleeping cocoons, woken again when freed. The bots dodge orbs and, when a friend is frozen, hit the cocoon first.

### 16. Heart of the Longest Night — The Silent Solstice (level 99): *The Longest Night*

- Every 45 s **Night falls**: after a **5 s warning** the arena goes dark and the cold kills anyone caught outside a **lit brazier's circle** within 6 s. Four braziers stand round the room; one is lit by a player **holding it for 3 s** (the `hold` block), and stays lit 30 s. The Heart sends flurries to snuff one every 12 s. So the party has to keep at least two braziers lit while it fights.
- Escalation: at 30% Night falls every 30 s and the braziers burn 20 s.

**Built 2026-10-18 (`BOSSMECH-SOLSTICE-HEART`).** *The Longest Night*: a 5 s kill-outside warning every 45 s (30 s below 30%), four braziers at (42,14), (54,14), (42,21), (54,21), radius 2.5, held for 3 s, burning 30 s (20 s below 30%), one snuffed every 12 s. The Heart's health went from 8.1M to 11.2M with an enrage start of 113 s (the party now holds braziers instead of racing).

**Changed 2026-10-20 (`BOSSMECH-RECAL-99`, owner).** The soft enrage only multiplies a boss's own attacks, and its clock runs only while a target is within 14 tiles, so a fight paced by a mechanic ignores it. Three bosses got an enrage rule of their own:
- *Unblinking Eye*: at its enrage the gaze starts at once (`Fight.enraged`, `tick_cover`), on top of the cover that already crumbles for good; start 120 s.
- *Static* (Thunder Heart): the enrage loads every hero that is not grounded with 11 charges, capped one under the limit (`ENRAGE_STACKS`, once per fight), so the next blow on the boss detonates them unless a rod clears the charge; start 86 s (95 s changed nothing: the clock lags the displayed time).
- *Solar Surge* (Solar Heart): the `break` block takes `at` (a burst phase that begins once when the boss's health, with its partner's, falls to that share) and `enrage` (too slow starts the enrage and holds the boss's clock at its start, `Fight.enrage_floor`; no one is killed and the boss is not held still). Solar Heart: at 80% the party has 10 s to deal 20% of the maximum health, which ends exactly on the 60% split. Hired five 4 of 6, four mercenaries alone 0 of 12. The cone's damage is not scaled by the enrage (tried and removed).
- *Storm Surge* (Thunder Heart, 2026-10-21, `BOSSMECH-MERC-ALONE`): the `break` block also takes `overload` (a burst phase whose failure does not enrage or kill everyone: one random hero who is not grounded is loaded to the Static limit and detonates where they stand, killing whoever is within the burst radius; needs a `static` block, a window of at least the kill floor, and excludes `enrage`). Three bursts at 80%, 55% and 30% health: 8 s to deal 7% of the maximum health. Why: Thunder Heart is paced by its rod cycle (8 s immunity, 12 s dark), so a start for the enrage could not tell the hired five (about 92 s) from four mercenaries alone (about 105 s). A burst is a damage check, and each failure takes a hero out, which lowers the next burst's damage. 32 seeds, enrage start 86 s: hired five 25 of 32, mercenaries alone 0 of 32 with the hirer idle and 0 of 32 with the hirer down (bar 0.06 leaked two wins, 0.05 two of 16, 0.10 and over beat the hired five every time). Tune with a scratch table: `BOSSMECH_TABLE_FILE=<file>` (test builds only) and `four_mercenaries_alone_never_beat_a_final_boss`.
Wiki `10_projects:valhallasc_bossmech_recal_99_20261020`.

## Where the ideas come from

Searched 2026-10-17. Each is a well known fight whose mechanic was adapted, not copied; none of the numbers come from them.

- **Soak, spread, stack, towers, knockbacks, baits** (Final Fantasy XIV raids) — the vocabulary behind *Downpour*, *Static* and the "stand here" circles. [FFXIV tower and soak guide](https://boostroom.com/blog/common-wipes-explained-the-top-mistakes-players-make-in-ffxiv-raids), [Shiva (Unreal)](https://www.akhmorning.com/raids/shiva-unreal/), [Eden's Verse: Furor](https://ffxiv.consolegameswiki.com/wiki/Eden%27s_Verse:_Furor_(Savage)).
- **Invulnerable boss with adds** (Lady Deathwhisper's mana barrier, Ragnaros submerging into Sons of Flame) — *the Bound Chorus* and *Pearl Shell*. [Lady Deathwhisper](https://icy-veins.com/wotlk-classic/lady-deathwhisper-encounter-guide-strategy-abilities-loot), [Ragnaros tactics](https://warcraft.wiki.gg/wiki/Ragnaros_(tactics)).
- **Walls of lava with gaps** (Sartharion's Flame Tsunami) — *Bramble Sweep*. [Sartharion](https://icy-veins.com/wotlk-classic/sartharion-encounter-guide-strategy-abilities-loot).
- **A growing floor hazard and the choice to move** (the Lich King's Defile), **a safe place that shrinks** (Yogg-Saron's sanity wells) — behind *Rising Tide* and *The Longest Night*. [Yogg-Saron](https://icy-veins.com/wotlk-classic/yogg-saron-encounter-guide-strategy-abilities-loot), [Best Wrath raids](https://blizzardwatch.com/2022/05/03/best-wrath-lich-king-raids-dungeons/).
- **Run out of a fissure before it blasts** (Kel'Thuzad's Shadow Fissure) and **adds that join at a health mark** (Guardians of Icecrown) — the timing of *Toll of the Deep*. [Kel'Thuzad tactics](https://warcraft.wiki.gg/wiki/Kel%27Thuzad_(tactics)).
- **A break bar** (Guild Wars 2's defiance bar) — *Dirge of the Hollow*: damage, not a stun, fills it. [GW2 defiance break](https://wiki.guildwars2.com/wiki/Defiance_Break), [Snow Crows guide](https://snowcrows.com/guides/getting-started/defiance-and-cc-guide).
- **Two bodies that must die together** (Ornstein and Smough, Mimiron's final phase) — *Twin Suns*. [Ornstein and Smough](https://darksouls.wiki.fextralife.com/Ornstein).
- **A fight on two layers** (Halion's Twilight Realm) and **plates and adds that open the next step** (Spine of Deathwing) — considered; the layer swap was too heavy for the engine and the plates need a moving arena, so they were not used. [Halion](https://warcraft.wiki.gg/wiki/Halion), [Spine of Deathwing](https://www.icy-veins.com/wow/spine-of-deathwing-strategy-guide-normal-heroic).
- **Rotating beams and lines** (Halion's Twilight Cutter) — *Orrery Spokes*.
- **Phases a fight must not let you stall** (Heroic debuffs that wipe a raid unless handled) — rule 7.
