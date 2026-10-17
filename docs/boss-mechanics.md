# Final boss mechanics

Design for the `BOSSMECH-*` tasks in [TODO.md](../TODO.md). Owner's request (2026-10-17): every final boss gets a gimmick, for example a big area attack with a five-second cast that kills anyone still in it, or a boss that turns invulnerable and spawns adds that must die to end it. The engine is built (see below); the sixteen mechanics are not. Every number is a starting value to tune with the dungeon harness (`BOSSMECH-CHECK`).

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

Each boss lists `mechanics`; each has a `name` (the cast bar and "Killed by <name>"), an optional health window (`hp_max`, default 1, and `hp_min`, default 0: an escalation is a second entry with a lower `hp_max`), and a `block`:

| Block | Fields | Notes |
| --- | --- | --- |
| `zone` | `shape`, `effect` (`kill`, `heavy`, `kill_outside`), `heavy`, `cast`, `every`, `first`, `repeat`, `repeat_gap`, `echo`, `linger` | Shapes: `circle` (with `inner` for a ring, `at` boss, target or random), `cone`, `lane`, `half`, `arena`, `islands`, `lit`. `echo` lands the same shape again after each delay and leaves a pale copy. `kill_outside` goes with `islands` and `lit` only. |
| `shield` | `steps` (`hp`, `tag`, `count`, `still`), `heal_per_s` | Wakes sleeping monsters of `tag`; no damage reaches the boss until they are all dead. With nothing to wake there is no shield. |
| `adds` | `tag`, `count`, `every`, `first`, `scatter`, `still`, `bloom` (`after`, `heal`, `then`) | A bloom removes the add, heals the boss and wakes one `then` add where it stood. |
| `mark` | `count`, `every`, `first`, `cast`, `effect` (`burst` or `beam`), `waves`, `wave_gap` | At most 3, never everyone, at least one; the ring or beam follows the bearer; the bearer is never hurt by their own mark. |
| `sweep` | `kind` `walls` (`warn`, `speed`, `thickness`, `gap`, `walls` with `from` and `gap` low, high, middle or random) or `spokes` (`count`, `width`, `deg_per_s`, `reverse_every`, `reverse_warn`, `length`) | Walls are dashed for `warn`, then red; the green gap is safe. Spokes turn about the arena's centre and are lethal to touch. |
| `break` | `cast`, `every`, `first`, `bar`, `stun`, `vulnerable` | The boss is held still; damage from anyone fills the bar (a share of its maximum health); broken: stunned and `vulnerable` extra damage; unbroken: everyone in the fight dies. |
| `stasis` | `every`, `first`, `orbs`, `speed`, `life`, `tag`, `hold` | Orbs seek players; a touched player is frozen (no input, no damage) in a cocoon (a sleeping monster of `tag`); kill the cocoon to free them, or they are lost after `hold`. |
| `split` | `hp`, `tag`, `revive_after`, `survivor_bonus`, `bridge` | The boss and its partner keep half the remaining health each. A body that would fall while the other lives is left on 1 health and downed; the other falling in time finishes both, otherwise it rises with half its health and the survivor hits harder. |
| `hold` | `points`, `r`, `hold_for`, `lit_for`, `snuff_every` | A place is lit by standing in it; lit places are the safe discs of a `lit` zone. |
| `gaze` | `cast`, `every`, `first`, `cover`, `regrow`, `sweep`, `beam` | Everyone with a clear line (`Map::line_clear` and standing cover) is struck at the end of the cast; with `sweep` a beam turns once round the room instead. Cover cracks after one gaze that it shielded someone from, breaks after two, regrows after `regrow`. |

Things worth knowing:
  * `every` runs from one start to the next, and `validate` insists it is longer than the whole sequence (casts, repeat gaps, echoes).
  * Adds are the sleeping monsters the map already holds (spawns with `ambush: <tag>`, state `waiting`); the dungeon's data places them, the mechanic only names the tag. A fight puts every one it woke back to sleep when it ends.
  * A fight starts when the boss is awake and fighting and ends when it dies, walks home or its copy is reset. It belongs to one boss slot, so dungeon copies never share state.
  * The snapshot carries `bossMech` (one entry per running fight: `cast`, `break`, `tele` with colour and shapes, `marked`, `frozen`, `shield`, `stunned`, `partner`, `banner`). Events: `bossmech` with a `phase` (`cast`, `land`, `add`, `shield`, `broken`, `bloom`, `frozen`, `split`, `down`, `rise`, `reverse`) and `immune` for a blow the shield swallowed. A death event carries `cause`.
  * `cargo test boss_mechanics` and `cargo test bossmech` run the engine's tests; `every_shipped_boss_is_fair_and_its_tags_exist_in_the_map` reads whatever the sixteen tasks add and fails on a point with no way out in time or a tag with no sleeping monster behind it.
  * Found while building it: the design's *Moon Lance* has a 3 s cast and kills, which is under the 5 s floor of rule 2; `BOSSMECH-MOONWELL-ECHO` has to lengthen it to 5 s or make it a heavy hit. The Flooded Cloister's boss room is 8 by 8 tiles and *Toll of the Deep* is a ring of radius 8, which fills the room: the fairness walk lets players run out of the door, but the room (or the ring) may need to change in `BOSSMECH-CHOIRMOTHER`.

## The sixteen mechanics

### 1. Haldor, the Hollow King — The Undervault (level 20): *Dirge of the Hollow*

The first dungeon is the gentlest: one mechanic, no kill-on-sight ring, no shield, and a generous margin.

- Every 30 s Haldor raises his crown and **channels for 8 s** while a blue break bar sits over his head. If the party deals damage to him equal to the bar before it ends, the dirge breaks: he is stunned 6 s and takes +30% damage. If not, the dirge ends in the **Hollow Wail**, which kills everyone.
- Tuning rule: the bar is set so a green party of five breaks it with **about 5 s to spare** (an early party is still learning), and a lone player never can. The damage counts from everyone, so no class is needed. The harness measures the number (roughly 5% of his health to start).
- No escalation: the same dirge for the whole fight, only a little more often (every 25 s) below 30%.

### 2. Elyss, Mother of the Bound Choir — Flooded Cloister (level 40): *Toll of the Deep* and *the Bound Chorus*

Both of the owner's examples, at the first dungeon where a party has had practice.

- **Toll of the Deep.** Every 25 s Elyss rings a drowned bell. A red ring (radius 8 round her) fills over a **5 s cast**; anyone inside when it lands dies. Melee has to step out and back in. The bar reads "Toll of the Deep".
- **The Bound Chorus.** At 66% and 33% health Elyss is **invulnerable** behind a pale shield of song and four Bound Singers (the Cloister's Bound Cantor model, weak) rise. The shield falls when all four are dead; killing them takes about 15 s for a green party. The toll keeps coming during the chorus.
- Escalation: at 33% the chorus is six singers and the toll comes every 18 s.

### 3. Queen Avariel, the Coral Regent — Coral Reliquary (level 45): *Pearl Shell*

- At 75%, 50% and 25% Avariel closes into a **pearl shell**: invulnerable, and she **heals 2% of her health per second** while it stands. Three Reliquary Pearls grow at marked spots round the room (stationary monsters, about 4% of her health each, each with a small pulse of damage to anyone adjacent). The shell opens when all three are broken.
- Escalation: at 25% there are four pearls and two Reliquary Crabs.

### 4. High Hierophant Vael, Heart of the Tide — Grand Nave (level 50): *Rising Tide*

The reverse of the king's ring: here you **must stand inside** the circle.

- Every 35 s the nave begins to flood. A **5 s warning** lights three dry **islands** (blue circles, radius 2.5); when the flood lands, anyone standing in the water dies, and the water drains again after 4 s.
- Islands are spread so that none is more than 60% of the cast away from any point; they appear in new places each time.
- Escalation: at 30% there are two islands and the flood comes twice in a row, with the islands moving between the floods.

### 5. The Moonwell Echo — The Moonwell (level 60): *Echo*

- Every 15 s she casts a **Moon Lance**: a red lane across the room, **3 s** to land, lethal. A pale copy of the lane stays on the floor, and **3 s after the first one lands the same lane lands again.** Her slam ring does the same: it lands round her, then again round the same spot after she has moved.
- The lesson is not to step back into where it just was. Escalation: at 40% the echo comes after 2 s and the echo itself echoes once more.

### 6. The Unblinking Eye — The Eye Below (level 65): *Unblinking Gaze*

- The lid opens; after a **5 s warning** the Eye sees everything: **anyone in its line of sight dies**. Only cover helps. Six lens pillars stand in the room; a pillar shields everyone behind it, **cracks after one gaze and breaks after two**, and regrows after 45 s, so the party rotates cover while fighting.
- Needs `eye_pillar` obstacles added to the boss room (the room has none today). Line of sight uses `Map::line_clear`.
- Escalation: at 30% the gaze comes every 15 s and **sweeps** across the room as a rotating beam: hide, then move round the pillar.

### 7. Heart of the Elder — The Elder Hollow (level 70): *Bramble Sweep*

- Every 20 s two **walls of thorns** (3 tiles thick) rise at opposite edges, shown as dashed lines for **4 s**, then sweep across at 4 tiles/s. Each wall has one **gap** (4 tiles wide) marked in green; the second wall's gap is on the opposite side, so the party has to cross the room between the walls. A wall kills anything it touches.
- Escalation: at 40% the walls come from both axes at once, with the gaps lined up on one cell of a grid.

### 8. Sovereign of the Last Fold — Thousandfold Pavilion (level 75): *Fold*

- A **crease line** appears through the arena at a random angle; one half is shaded red. After a **5 s warning** that half **folds flat**: anyone on it dies. It unfolds after 3 s. The safe half is never smaller than 40% of the room. Every 22 s.
- Escalation: at 33% a second fold follows the first (a quarter of the room, then the opposite half), and the crease can pass through the boss.

### 9. The Rain Crown — Temple of the Rain Crown (level 80): *Downpour*

- Every 25 s a **storm cloud** marks up to three players (never everyone) with a ring (radius 4) that follows them for **5 s** and then bursts as **lethal rain**. Marked players must **spread out and away** from everyone else; unmarked players must stay out of every ring. Rain puddles linger 8 s.
- Escalation: at 40% the marks come in two waves, the second 3 s after the first lands.

### 10. Heart of the Worldseed — The Seed Vault (level 80): *Germination*

- Every 30 s three **seeds** are planted at random spots and grow for **12 s**, shown as a bar over each. A seed that blooms becomes a **Bloom Treant** (strong, 3% of the boss's health) and **heals the Worldseed 4%**. Each seed has about 1.5% of the boss's health, so the party has to split to burst them before they bloom.
- Escalation: at 35% five seeds at once.

### 11. Axis of the Buried Sky — Sunken Astrolabe (level 85): *Orrery Spokes*

- Three **brass spokes** (lanes 1.6 wide, from the Axis to the wall) rotate round it at 20°/s, each 120° from the next. A spoke is lethal to touch. Players run with the rotation, or stand in the gap, which moves at under 3 tiles/s at 8 tiles out.
- The spokes **reverse** every 12 s after a **2 s** warning (a gear symbol and a sound).
- Escalation: at 30% there are four spokes at 28°/s.

### 12. Heart of the Stormgate — The Thunderheart Gate (level 95): *Static*

- Every damaging **skill or hit you land adds one Static charge**. At 12 charges you detonate: a lethal burst (radius 5) at your feet. A **Grounding Rod** (four, in the corners) clears all your charge and gives 8 s of immunity to Static; after use a rod is dark for 12 s. So the party has to leave the boss every ~10 s to ground, and cannot all use one rod.
- A banner at 8 charges and a crackle on the hero warn. Escalation: at 30% charge comes in twos and the rods go dark 20 s.

### 13. Heart of the Labyrinth — The Blooming Labyrinth (level 97): *Prism Bounce*

- Every 18 s the Heart **marks a player** with a gem. After **4 s** it fires a lethal beam at where the player stands, and the beam **bounces off the arena walls twice**: all three segments are drawn as dashed lines for the whole countdown. The marked player has to line the bounces up so they miss the others.
- Escalation: at 30% two marks and three bounces.
- Note: this Heart already beats five players in green gear (`DUNGEON-PARTY-CHECK`); ease its health before the mechanic goes in.

### 14. Heart of the Crucible — The Solar Crucible (level 98): *Twin Suns*

- At 60% the Heart **splits** into Sol (fire: cone bursts) and Cinder (ash: ring bursts), on opposite sides, each with half the remaining health. While both live, a **lethal bridge of sunlight** joins them along the line between the bodies and moves when they do.
- If one dies and the other lives for **more than 10 s**, the dead one rises again with half its health and the survivor gains +50% damage. The party must burst both within 10 s of each other.

### 15. The Last Memory — The Amber Archive (level 99): *Amber Stasis*

- Every 25 s two **amber orbs** seek random players. A player they hit is **frozen in amber**: no movement, no skills, no damage taken. The cocoon is an object with about 2% of the boss's health: allies must **break it within 10 s**, or the amber closes and the player is lost. While frozen the player is a target that cannot dodge, so the next attack decides it.
- Escalation: at 30% three orbs, and the cocoon holds for 8 s.

### 16. Heart of the Longest Night — The Silent Solstice (level 99): *The Longest Night*

- Every 45 s **Night falls**: after a **5 s warning** the arena goes dark and the cold kills anyone caught outside a **lit brazier's circle** within 6 s. Four braziers stand round the room; one is lit by a player **holding it for 3 s** (the `hold` block), and stays lit 30 s. The Heart sends flurries to snuff one every 12 s. So the party has to keep at least two braziers lit while it fights.
- Escalation: at 30% Night falls every 30 s and the braziers burn 20 s.

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
