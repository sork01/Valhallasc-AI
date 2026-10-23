# The Chained Forge (Molten raid) — design record for `RAID-RULES`

Status 2026-10-21: **the owner answered the four open questions (section 12) and
`RAID-RULES` is complete.** Everything marked "decided" comes from the owner's five
rounds in `TODO.md` plus the sixth round in section 12; what is still marked
"proposed" is detail for the task that builds it. Numbers marked "model" or
"estimate" are not server measurements; section 11 lists what must be measured and
with which fixture.

Working names (proposed): the raid is **The Chained Forge**, its 28-piece orange
family is **Chainforged**. Both are one-line changes.

## 1. Where it stands in the world (decided, from the approach work)

The raid door stands beyond Emberwake Caldera, a public level 95–99 volcanic zone
connected to Asterion (17). Emberwake is file zone 45 and is described in
[emberwake.md](emberwake.md). The raid takes the next free file zone at
implementation time: with Emberwake present, that is **46**. The Nine-Chain Door
has no portal until `RAID-MAP` installs the real one; `RAID-OPEN` opens it.

The raid requires exactly ten level-99 fighters, any mix of humans and hired
mercenaries, fixed health, three private copies, no loot lockout. Nine hired
fighters are allowed inside the raid only; the outdoor approach keeps the cap of
four. Asterion's warm flagstones, cracked well and Runa Coalhand foreshadow the
forge, and Emberwake's last quest lets the player hear Eldmarr's threat through
the sealed door.

**Eldmarr's story (decided, round 5).** Eldmarr, the Ember-Lord of the fire
giants, kept the first forge beneath the world. Its heat kept the roots of the
world tree alive through the long winter, and the gods raised their hall on his
fire. They promised him a seat at the table and never gave it. When he came up to
claim it they bound him in the stone under Asterion's mountain with nine chains,
each held by a Warden (once his own smiths and captains, set to guard him for a
place in the hall), and told the world the forge had gone out. It had not: the
chains hold the fire in, and the fire has been rising for a hundred years. The
Wardens have gone slag-mad from the heat, one by one the chains fail, and the
ground around Asterion is warm in the evenings. Eldmarr does not want to burn the
world for its own sake; he wants the table he was promised, and he will take the
hall by melting the roots that hold it.

## 2. The owner's decisions in one table

| # | Decision | Consequence for the build |
| --- | --- | --- |
| 1 | Main antagonist is a Surtr-style fire giant, **Eldmarr** | final boss `eldmarr`, section 8 |
| 2 | Level 99 only, **exactly ten** fighters | portal gate `players: 10` counts humans and mercenaries |
| 3 | Need/Greed/Pass among the **humans only**; mercenaries never roll; a lone human is awarded the drop at once | `rolls.rs` extended to ten rollers; section 9 |
| 4 | Final-boss weapons carry a proc, a skill change and a visual/sound identity | section 10 |
| 5, 12 | Door in a new volcanic zone off **Asterion** | Emberwake (zone 45), done |
| 6 | No lockout; every kill drops | no weekly state |
| 7, 9, 11 | Any mix of humans and mercenaries, ten in total; up to nine hires, **raid only** | section 6 |
| 8 | Three private copies | section 7 |
| 13 | Health fixed for ten fighters, no scaling by makeup | one health table |
| 14 | Kill times measured with the hirer plus nine mercenaries (real `auto_play` brain, full orange); record median and fastest of at least 16 seeds | section 5 |
| 15 | A wipe resets only the current boss; killed bosses stay dead; the fallen stay down while the fight runs; everyone wakes at the door of that boss's hall | section 6 |
| 16 | Packs are hard but partly skippable; the path to each boss is mandatory | section 4 |
| 17 | Backstory above | signs, quests, lines in hand-written Swedish |
| 18 | Ordinary raid enemies drop **purple at 3%** per kill | section 9 |
| 19 | Zone music is dub-techno about 110 BPM; the raid is industrial techno | section 13 |

Round 2's "the instance resets on a wipe" is superseded by round 4 (decision 15):
only the boss in progress resets.

## 3. Baselines, measured 2026-10-21 from `world/map.txt`

Method: the server's own collision (`blocked_grid` in `world/chests.rs`: map border
margin 1.2, every object as a rectangle or circle grown by `PLAYER_RADIUS` 0.3),
then a flood fill from the arrival point. "Reachable floor" is walkable one-tile
cells. (The `blackhourFloor` and `longshipFloor` art masks give the same 8,024 and
5,060.) Ordinary = the repeated kinds that are not sleepers; a pack = a cluster of
ordinary spawns within 12 tiles; bosses = kinds that occur once and are awake.

| Dungeon | Map | Reachable floor | Ordinary | Packs | Bosses |
| --- | --- | ---: | ---: | ---: | ---: |
| Grand Nave (Cathedral) | 192 | **11,484** | 16 | 4 | 4 |
| Black Hour Foundry (L99) | 160 | **8,024** | 12 | 4 | 3 |
| Flooded Cloister / Coral Reliquary | 160 | 7,480 / 7,176 | 16 | 4 | 4 |
| Undervault (L20) | 128 | 7,799 | 46 | 10 | 4 |
| Drowned Longship | 128 | 5,060 | 12 | 4 | 3 |
| Nornroot / Shattered Span | 112 | 4,326 | 12 | 4 | 3 |
| Yearwheel dungeons (29–39) | 96 | 2,037–3,497 | 9 | (scattered, not clustered) | 3 |

The biggest single dungeon by floor is the Grand Nave; by ordinary enemies it is
the Undervault; the biggest **level 99** one, and the closest sibling, is the
Foundry. The Foundry's four packs have three enemies each.

Kill-time baselines already measured (hired five, no orange):

| Fight | Baseline |
| --- | --- |
| Non-final dungeon boss, project standard (`elite-power.txt` tuning) | about 70 s |
| Foundry packs, complete level-95 blue sets | 124.7–155.6 s (middle about 140 s) |
| Foundry side bosses, blue | 204.0–231.3 s |
| Foundry final, blue | 386.4–571.2 s |
| Final bosses with a mechanic | enrage start per boss, `world/enrage.txt` |

## 4. Size and packs (decided 2026-10-21, sixth round)

"4 times the size of a regular dungeon" was read as four times the floor of the
sibling dungeon. Options the owner saw for the floor:

| Option | Reachable floor | Map at the Foundry's 31% fill |
| --- | ---: | --- |
| A. 4 × Grand Nave | about 45,900 | about 385 × 385 (Yearwheel is 400) |
| **B. 4 × Black Hour Foundry (chosen)** | **about 32,100** | **320 × 320** |
| C. 4 × a typical Yearwheel dungeon | about 12,000 | 200 × 200 |

**Chosen: B, with 10 packs.** B keeps the Foundry's construction (collision from
objects, a floor mask for the art) and doubles its linear size. The owner chose ten
packs rather than sixteen: the floor is four times the Foundry's, but the pack
*count* is 2.5 times, and every pack still takes four times as long.

Layout: **ten encounter halls** in one descent, joined by ten legs. **Ten packs of
four enemies** (the Foundry has three; one more so ten fighters have targets):
**six mandatory**, standing in the path on the six longest legs, and **four
optional**, in alcoves, on bridges and in side forges. Optional packs are never
behind a lock that needs the whole pack dead (decision 16); a pack that is sneaked
past or pulled one at a time still gives the same kill time per pack. All ten carry
the purple chance. **Owner correction (2026-10-22): every pack enemy is a
dungeon elite; there are no separate special elites or elite quests.** Music
remains RAID-MUSIC.

### Full-run length (estimate, fighting time only)

Targets per section 5: pack 564 s (4 × 141), Warden 280 s (4 × 70), final median 1,080 s.

| Part | Count | Each | Total |
| --- | ---: | ---: | ---: |
| Packs, all | 10 | 9.4 min | 94 min |
| Packs, mandatory only | 6 | 9.4 min | 56 min |
| Wardens | 9 | 4.7 min | 42 min |
| Eldmarr | 1 | 18 min | 18 min |
| Walking, regrouping, loot rolls | 10 legs | — | about 10 min |

Plus about 20% for recoveries and a wipe or two:

| Plan | Fighting | With 20% |
| --- | ---: | ---: |
| **Chosen: 10 packs, everything cleared** | 164 min | **about 3.3 h** |
| Chosen: 10 packs, mandatory only | 126 min | about 2.5 h |
| (Not chosen) 16 packs, everything cleared | 220 min | about 4.4 h |
| (Not chosen) 16 packs, mandatory only | 164 min | about 3.3 h |

That is a long raid; it is what "4 times as long" gives. These are estimates; the
real figure comes from `RAID-CHECK`.

## 5. Kill-time targets and measurement

**Owner update, 2026-10-22: pack clear-time calibration is deferred. Leave the
packs overpowered; the owner has a fix in mind for later.** The earlier pack
numbers below are planning targets, not acceptance gates for RAID-PACKS.
Boss timings remain later tasks.

All times are for **the hirer plus nine mercenaries**, the real `auto_play` brain,
in full orange gear (decision 14); skilled humans may be faster and that is
accepted. Ten fighters deal about twice the damage of five, so four times the time
needs **about eight times the health** of the five-fighter baseline: an estimate,
because mana and energy run out in a long fight and time grows faster than health.
The health tables are set by measurement through `elite-power.txt` scratch copies
(`ELITE_POWER_FILE`, no rebuild), never by this ratio.

| Fight | Baseline | Target (ten fighters, orange) | Basis |
| --- | ---: | ---: | --- |
| Ordinary pack | about 141 s | **500–620 s** (middle 564 s) | 4 × the Foundry's blue packs |
| Warden | about 70 s | **about 280 s** (240–320 s) | 4 × the project's 70 s standard for non-final bosses |
| Eldmarr | 386–571 s | **at least 900 s**, middle about 1,080 s; the fastest seed must still be 900 s or more | the owner's floor; 4 × the Foundry final would be about 30 min and is not required |

Why 70 s for the Wardens and not the Foundry's 204–231 s: 70 s is the rule for all
35 non-final bosses, and four times the Foundry's side bosses would be 14–15 minutes
each, which is Eldmarr's floor. The Foundry's longer times came from a blue-gear
fixture with its own mechanics, not from a tuning target.

Records per future boss fight, from at least 16 seeds: median, fastest, slowest,
falls, DPS per class. A win is the actual kill. Controls with the same fixture: ten minus two
fighters must lose or take at least 1.25 times the median; a lone player at level 99
must die to every pack and every Warden (`a_dungeon_pack_kills_a_lone_player` and
the boss equivalent); the old rule that four mercenaries alone must lose was removed by the owner on
2026-10-23 (`merc_alone_party_times_report` only prints times). Enrage per
boss: `ceil(1.06 × slowest ten-fighter win) + 2`, judged from raw times with the
enrage off (`ENRAGE_FILE=<{}>`), as in the other dungeons.

**Interim fixture.** "Full orange" does not exist yet: Worldheart (family 99) has five
slots (armor, weapon, headgear, shoulders, gloves) and no pants, necklace or
accessories, and every Worldheart piece is class-neutral. Until `RAID-ORANGE` ships
Chainforged, measure with Worldheart's five pieces plus the Nullforged purple pants,
necklace and two accessories, and write the fixture next to each number. Every number
is re-measured once Chainforged exists; the final is re-measured with the signature
weapons equipped.

**The fallen.** Final bosses keep the fallen down while the fight runs
(`BossMech::fight_in`); `FALLEN_HOLD_MAX` is 600 s, shorter than Eldmarr's 900 s
floor, so a fallen hero would wake mid-fight. Proposed: a raid-zone value of **2,400 s**
(1.5 times the slowest expected win, rounded up), the other dungeons unchanged;
recompute it from the slowest measured Eldmarr win (`ceil(1.5 × slowest / 60) × 60`).

## 6. Group rules (mostly decided, details proposed)

* **Group.** A party flagged **raid** holds up to ten members, humans and
  mercenaries together; the leader converts, and converting back needs five or fewer.
  The five-player party and its constants stay as they are (proposed in preference to
  a separate raid type, because invites, kick, grace and XP all live in `social.rs`).
* **Entry.** The portal needs exactly ten (`players: 10`, `min_level: 99`); fewer or
  more is refused with a count in the message. Instances prefer a raid mate's copy.
* **Hiring.** The current Meeting Stone hire is capped at `social::PARTY_MAX` (5)
  (`world/mercs.rs`). The raid needs a **quartermaster at the Nine-Chain Door** whose
  offer is a "raid contract": it hires up to the free slots (ten minus the group),
  prices each at `merc_price(level)` like any hire, and the contract fighters follow
  only through the raid portal. Everywhere else the cap stays four (decision 11).
  Mercenaries are the hirer's level, forfeit loot, are excluded from human counts,
  saves, `who` and invites, and are dismissed when the instance is cleared.
* **XP.** Mercenaries take none and are not members (`partyxp.rs`); a hirer with nine
  mercenaries keeps the whole XP. Ten humans use the party level already earned;
  `PARTY_XP_PERCENT` has no entries for 6–10 members and does not need them (the
  percentage depends on the party level 1–5, not on the size). A boss is worth 15
  fellowship points, as today.
* **Gold.** A party splits kill gold evenly and a mercenary's share is destroyed, so a
  hirer with nine mercenaries keeps a tenth. `MOB_GOLD_SCALE` 0.5 still applies.
* **Loot.** Need/Greed/Pass among the humans only (30 s). One human: awarded at once.
  A mercenary's share goes into the humans' rolls. Section 9.
* **Wipe (decision 15, details proposed).** When the whole group has fallen, everyone
  wakes at the door of that boss's hall; the boss resets to full health and its
  sleeping helpers (`place_boss_adds.py`) go back to sleep; killed bosses and killed
  packs stay dead; 60 s of grace to return. An empty copy resets after 20 minutes
  (proposed, so a disconnect does not lose the night).
* **Death.** The fallen stay down while a boss fight runs (section 5).

### 6.1 What `RAID-PARTY` built (2026-10-21)

* `Party.raid` and `social::RAID_MAX` (10); `party_raid` (leader only). Turning it off needs five or fewer members and
  nobody inside a raid zone. Pending invites count against the party's own cap.
* `Map.raid` marks the raid zone and its copies. `use_portal` refuses a group that is not exactly ten (mercenaries
  counted) with the count in the message; a lone hero with no party is simply a group of one, so it is refused too.
* A five-player dungeon's door (any zone with copies that is not a raid) refuses a group of more than five, with the
  count in the message, so a raid cannot walk into a dungeon balanced for five. Copies inherit `Map.raid` because
  `make_instances` clones the whole map (a test pins it).
* Raid contract: an NPC offer with `raid: true` and a class (`merc_warrior`, ...) hires one fighter per click up to ten
  minus the group, at `merc_price`, with no quest. The leader (or a lone hirer) signs and the group becomes a raid; a
  member signs only for a group that already is one. Its fighters carry `Player.merc_raid` = the door's zone and are
  let go once the hirer is neither in that zone nor in a raid zone. The NPC and the portal come with `RAID-MAP`.
* Loot in a raid zone: items (rolls, the gray round robin) are for humans only; one human gets the piece at once; a
  mercenary's kill belongs to its hirer; gold still splits among everyone and a mercenary's share is destroyed.
* XP: unchanged. The owner pointed out that level 99 is the highest level, so XP is moot in the raid.
* Decided by the owner (2026-10-21): on a wipe the contract fighters wake with the group and stay; a solo hirer with nine
  hires is a fully supported route, with no cap on its drops.
* Decided by the owner (2026-10-21): raid-zone `FALLEN_HOLD_MAX` is 2,400 s (recompute from the slowest measured Eldmarr
  win if that changes); the contract charges the normal `merc_price(level)` per fighter, so nine cost about 1,035,000
  gold at level 99 (a deliberate gold sink).
* Open for `RAID-MAP`: the quartermaster and door in `map.txt`.

## 7. The zone and the copy ids (derived, recheck at release)

Public zone 46, a sealed template with **three** copies: the template is copy 0 and
`make_instances` appends two clones. Dungeon clones are appended after all file
zones in template order, and the Arena's eight copies come last. With 46 file zones
(0–45, Emberwake the last) there are 60 extras from the existing 20 templates
(Undervault, three Cathedral wings, Moonwell, Yearwheel dungeons 29–39,
Nornroot, Span, Longship, Foundry): ids 46–105, the Arena 106–113. Adding file
zone 46:

| Entity | Id before the raid (Emberwake only) | Id with the raid |
| --- | --- | --- |
| Existing 60 dungeon extras | 46–105 | **47–106** (+1) |
| The raid's two extras | — | **107–108** |
| Arena copies | 106–113 | **109–116** |

Relative to the main checkout without Emberwake (extras 45–104, Arena 105–112) the old
extras move by +2 and the Arena by +4. A saved character inside a private copy stores
that index: before a release inspect `select state from characters` in the stopped
DB, move anyone in an old copy to a safe hub (Skaldholm zone 4, x104.2 y125.4), and
update `COPY` in `vault_tests.rs`. Always derive the mapping from the actual old and
new world files and the running binary; this table is arithmetic, not a record of
the live server.

## 8. Wardens and Eldmarr (approved by the owner, 2026-10-21)

Each boss task re-checks its mechanic against `docs/boss-mechanics.md` before it
builds. Rules for every one: telegraph the whole cast; an instant kill is cast for at
least 5 s; safety is reachable within 60% of the cast at 5.2 tiles/s; no class is
required (a role is "whoever stands there", "whoever carries it", never "the tank");
nothing is solved by five players standing still while five idle; a sign before the
door, ability names, banners and hand-written Swedish; a `world/boss-mechanics.txt`
entry; an enrage entry; and a brain rule in `boss_play.rs`, because the ten-fighter
measurement is run by the mercenary brain and a mechanic the brain cannot answer
cannot be certified.

Existing blocks: `zone`, `shield`, `adds`, `mark`, `sweep`, `break`, `stasis`, `split`,
`hold`, `static`, `gaze`, with `echo`/`linger`/`alternate` as zone options. The sixteen
finals use them as: Hollowking `break`; Choirmother ring + `shield`; Coral Regent
`shield` + heal; Hierophant `islands`; Moonwell Echo `echo`; Eye `gaze`; Elder
`walls`; Pavilion `half`; Rain Crown `mark` burst; Worldseed `adds` bloom; Axis
`spokes`; Thunder `static` + overload `break`; Bloom Heart `mark` beam; Solar Heart
`split`/merge + bridge; Amber `stasis`; Solstice `hold` + `lit`.

| # | Warden (once Eldmarr's…) | Mechanic | The rule, with ten fighters | Block | Not like |
| --- | --- | --- | --- | --- | --- |
| 1 | Kettil Linkbearer (first link) | **Taut Chain** | Every 30 s heroes are chained in pairs. At the *Heave* (5 s dashed cord) a pair must stand within 6 tiles of each other or both take a heavy hit. Your partner is whoever the chain says. | `tether` (new) | Rain Crown spreads marks; this binds two together |
| 2 | Ysolt Bellowsmaid (bellows) | **Gale of the Bellows** | A 5 s dashed arrow, then a wind shoves everyone 10 tiles toward the lava rim; the rim kills. Four iron posts hold three heroes each within 1.5 tiles; the rest are shoved. Posts stand far enough apart for melee and ranged alike. | `gust` (new) | no final has a knockback |
| 3 | Hallgrim Anvilhand (anvil) | **Hammerfall** | Three anvil circles are marked; at the landing each needs **three or more** heroes inside, or its blast kills those inside and hits the raid heavily. Ten fighters make three groups of three and a spare. | `soak` (new) | Hierophant islands need no count; Rain Crown wants spacing |
| 4 | Sigrun Slagmother (slag) | **Ingot Order** | The Warden is untouchable while six numbered ingots stand round the hall; only the lowest number can be hurt. An ingot left standing 25 s explodes on the raid (heavy). | `shield` + `ordered` (extension) | Choirmother and Coral Regent open on any order, no clock per piece |
| 5 | Dagfinn Tongsbearer (tongs; **halfway**) | **Two Valves** | At 70% and 40% the hall splits into two basalt islands. Each island's valve needs **three** heroes holding it for 20 s or lava rises on that island. Ten fighters split five and five. His death opens a shortcut and lowers the lava in the remaining halls. | `hold` + `need`, `half` floor (extension) | Solstice braziers need one hero and no split |
| 6 | Thorbjörg Quenchwife (quench) | **Brand Relay** | Three heroes carry a Brand with an 8 s fuse. Touching another hero passes it on and gives the giver 6 s immunity; a brand that burns out detonates (kill within 5 tiles). Whoever carries the brand passes it. | `relay` (new) | marks follow one hero; here the burden moves |
| 7 | Ragnhild Cinderfoot (the dance floor) | **Four on the Floor** | The floor is a 6 × 6 grid of tiles that light in a four-beat pattern at 150 BPM after a 5 s cue showing the numbers. Anyone on a tile at its beat takes a heavy hit. The brain reuses the walls' search through space and time. | `grid` (new) | Elder walls and Pavilion fold are single shapes |
| 8 | Orm Ashwalker (ash and water) | **Water Carriers** | Ten flasks sit in wells round the hall. The Warden is "Molten" (takes half damage, hits hard). Six flasks thrown at his feet within 5 s start 15 s of "Quenched" (takes double). A carrier moves at 60% speed. | `carry` (new) | no final has a carried object |
| 9 | Hildr Lastlink (the last chain) | **Mirror Plate** | For 8 s every 40 s she glows white and whatever hits her hits back (heavy). The group stops attacking for the glow; "hold fire" is the brain's existing flag. It also lengthens the fight by the windows. | `reflect` (new) | Thunder's static is the player's own charge; this is a shared pause |

**Eldmarr, the Ember-Lord** — three base mechanics in sequence, a throne hall that
changes at each, and nine chains that break in threes (banner and sound at 66%, 33% and
8%):

| Phase | Health | Mechanic | The rule | Block |
| --- | --- | --- | --- | --- |
| 1 | 100–66% | **The Forge Floor** | A cell stood on for 3 s cracks and becomes lava 8 s later, until it cools after 40 s. The group must keep moving and use the whole hall; a camper is the only loser. | `crack` (new) |
| 2 | 66–33% | **Rising Heat** | Every hero's Heat meter rises over time (not from hits); four Cold Wells each cool three heroes at a time and move every 30 s. At full, the hero detonates (kill within 5 tiles). | `heat` (new) |
| 3 | 33–0% | **A Seat for Everyone** | Every 40 s, after a 5 s warning, only the ten seat plates (radius 1.2, one hero each) are safe; the rest of the hall kills. With a hero down there is a spare seat. | `seats` (`kill_outside` with a per-plate capacity, new) |
| Enrage | below 8% | all three at 1.25 times the tempo (a later phase may combine earlier ones) | |

Breathing: two safe windows between phases, no cast longer than the telegraph rule
allows, tempo varied so 15 minutes stays readable. Eldmarr drops the signature
weapons (section 10); after the kill the instance clears (`after_clear`), an
`announce` packet (kind `boss`) fires for the first kill, and a reward room opens.

**Engine cost.** Twelve new or extended blocks (`tether`, `gust`, `soak`, an ordered
`shield`, a counted `hold`, `relay`, `grid`, `carry`, `reflect`, `crack`, `heat`,
`seats`), each with a `Rig` test, a brain rule and a sign. They are built one at a
time by the boss tasks; none is needed before `RAID-MAP`.

## 9. Orange loot (implemented reward tables, 2026-10-22)

**Slots.** After the cloak change a character wears ten pieces: armor, weapon, headgear,
shoulders, gloves, pants, necklace, cloak and two accessories. Set bonuses count
eight non-cloak categories (the two accessories are one). Existing orange (Worldheart) covers five slots and is
class-neutral (`class: null`, weapon included); only Nullforged purple is per class.

**Chainforged: 29 pieces, level 99, including the new neutral cloak.** Per class armor, headgear, shoulders,
gloves and weapon (25), plus class-neutral pants, necklace, accessory and cloak (4), like
Nullforged. Stats: the purple budget of the slot times 1.175 (orange) times **1.10**
over Worldheart, every roll ±4%; `orange_rules.py` asserts that the lowest roll beats
Worldheart's highest (1.2925 × 0.96 = 1.241 against 1.175 × 1.04 = 1.222). New shapes,
never a tinted copy (`createarmors`); the 2/4/6/8 set bonus in `set_bonuses.py`.
The raid does not use the 0.1% orange roll anywhere else.

**Drops.** Each Warden lists three slots and drops **two** of them at random; Eldmarr
drops **two signature weapons** (their classes follow the class rule below) plus two
of three listed slots: **22 pieces per clear**. Lists rotate through the eight
non-weapon slot types, so each of them drops about 2.5 times per clear and the
weapon twice.

**Which class a piece is for — decided: A, a uniform pick over all five classes**
(what `boss_piece_for` does today for dungeon bosses; the owner chose it over the
two options below). Chainforged is therefore 28 per-class pieces as above. The
consequence, model output (1,500 simulated runs, a hero needing all nine worn slots,
medians in clears, first hero / all heroes), is that a set takes real repeat clears:

| Group | **A. Uniform over classes (chosen)** | B. Class of a human present | C. Demand-aware |
| --- | --- | --- | --- |
| One human + nine mercenaries | **4** | 1 | 1 |
| Five humans, one per class | **4 / 7** | 4 / 7 | 3 / 3 |
| Ten humans, two per class | **6 / 11** | 6 / 11 | 5 / 6 |

The worst single run of the 1,500 for a solo hirer was 19 clears. Because a solo
hirer sees many pieces of other classes, those pieces go to Greed or are sold
(about 8,300 gold each, section below). B and C stay documented in case the owner
reopens this after `RAID-CHECK`; C would need "already has it" defined as the
character holding a Chainforged piece of that slot equipped, in the bags or in the
bank (by item id) and reads three inventories per drop.

**Purple at 3%.** An independent roll per pack enemy killed. **Owner correction
(2026-10-22): unique original, class-neutral level-99 pieces** from the Cinderwork
pool in section 16. The existing `copies()` and raid loot path preserve rebirth
and human-only Need/Greed/Pass. Expected purple per clear: 10 packs × 4 = 40
enemies → about **1.2**; the six mandatory packs only → about 0.7 (counted per enemy).

**Economy.** A level-99 hire costs `merc_price(99)` = 115,000 gold, so nine
mercenaries cost **1,035,000 gold** per attempt (`world/mercs.rs`). An orange piece
sells for about 8,300 (`orange_47`), so 22 pieces are worth about 180,000 if every one
were sold; a hirer keeps a tenth of kill gold. The raid is therefore a gold sink: its
reward is the gear. Lever if the owner wants it: a raid-contract price factor (for
example 0.25) in the quartermaster's offer.

## 10. Signature weapons (approved by the owner, 2026-10-21)

Five weapons, one per class, dropped only by Eldmarr. Each has a **proc**, a **skill
change while equipped** and a **look and sound**. Rules: server-computed; at most one
proc per hero per 3 s. **Superseded by the owner's 2026-10-22 decision:** procs also
reach players through `pvp_hit`, with a 3% maximum-health pre-reduction budget and
normal PvP/heal rules. The added skill damage remains monster-only and Warmth's
extra healing applies outside PvP fights. The replacement keeps the old skill id,
bar slot, cost, cooldown and PvP damage numbers. See `docs/raid-rewards.md` for the
implemented caps, tables, ten-slot model and original PixelFlow artwork.

| Class | Weapon (working) | Proc | Skill change |
| --- | --- | --- | --- |
| Warrior | Chainsplitter | 8% on hit: a 12-tile slag wave in front, 60% of the blow | Earthshatter also leaves burning ground for 4 s |
| Mage | Cinderwake Staff | 10% on a spell: an ember orb orbits 6 s and strikes the nearest enemy every 1.5 s | Arcane Ward also flares a short pulse when it expires |
| Assassin | Twin Embertongs | stacking burn, five stacks | Knife Ring leaves a burning trail |
| Priest | Bellows Censer | 8% of heals leave an ember ward worth 3% of maximum health | Mend also warms the next heal by 10% |
| Hunter | Chainbow | 10% of shots chain to two more enemies at half damage | Arrow Storm bounces once |

Look: molten glow along the weapon in every animation, pulsing at the raid's tempo,
a distinct impact flare and sound (`createweapons`). Tooltip in plain words, Swedish
by hand.

## 11. What each task must measure, and with what

`RAID-MAP`: reachable-floor count by the section 3 method, plus walk times between
halls. `RAID-PACKS`: elite, collision, loot and rendering checks; deliberately
overpowered per the owner's 2026-10-22 instruction, with clear-time calibration
deferred. A lone player must die. Each boss task: its own ten-fighter times (median, fastest, slowest), the ten
minus two control, the lone-player rule, the mechanic's fairness test, the enrage
start. `RAID-ORANGE`: the orange sums per class and slot, the clears-to-set model
re-run on the real tables. `RAID-CHECK`: the final at 900 s or more with the
signature weapons. Never the other nine bosses, never a whole suite, one scratch
binary.

## 12. The owner's answers (sixth round, 2026-10-21)

1. **Size and length — decided.** About 32,100 reachable cells (4 × the Foundry,
   320 × 320), **10 packs** (6 mandatory), a full clear of about 3.3 h and about 2.5 h
   with the mandatory packs only (estimates).
2. **Loot class model — decided.** A, a uniform pick over all five classes, with
   Chainforged as 28 per-class pieces. A solo hirer needs about 4 clears for a full
   set; ten humans need about 6 for the first and 11 for all (model output).
3. **The Wardens and Eldmarr — approved as written** (section 8), including the
   dozen new engine blocks, built one boss at a time.
4. **The weapons — approved as written** (section 10), procs and changed skills off
   in PvP.

Not asked, so they stand as proposed unless the owner objects: hire price unscaled
(1,035,000 gold for nine at level 99), raid `FALLEN_HOLD_MAX` 2,400 s, a 20-minute
empty-copy reset, the quartermaster at the door, the raid-flagged party, the family
name Chainforged and the raid name The Chained Forge.

## 13. Music (decided style, proposed numbers)

Approach: 110 BPM dub-techno / half-time (day) and 96 BPM (night), done in
Emberwake. Raid: **industrial techno**, 150 BPM or more, a key other than D minor
(Foundry) and F minor (Emberwake), a final-boss variant at 160 BPM; minimal drone/ratchet
motif, no foreground lead, the weight in the distorted kick, clanging percussion and
noise hits; warehouse reverb; Sork-60 pads only, Chillhop hats only, SorkCrush for
distortion. State the instruments to the owner before writing, loop-fold, -24 dB mono
RMS, 128 kbps; offer the MP3 for FileDrop, do not upload unasked.

**RAID-MUSIC implemented 2026-10-23 (client only):** *Nine Chains Below*, 152 BPM,
and Eldmarr's *The Table He Was Promised*, 160 BPM, both F-sharp minor, 4/4,
64 bars. Corrected mixes are saved as dybase2 projects `001bb0c3080f4534` and
`cbee414e186d8bf9`; game loops decode at -23.99/-23.98 dB mono RMS, with no
clipping. The existing server `bossMech` state selects the final variant only
while the living `cf_eldmarr` is fighting. Twenty private browser checks pass,
and disabling that switch in the private response fails the expected assertion.
The final encounter is still a later task, so its packets are replayed for this
music check. The raid stays sealed; no server restart is needed. Full score,
export recipe, measurements and listening limitation: [raid-music.md](raid-music.md).

## 14. Reading list used

`docs/blackhour.md`, `docs/boss-mechanics.md`, `docs/orange.md`, `docs/ttk-plan.md`,
`docs/nornroot.md`, `docs/set-bonuses.md`, `docs/emberwake.md`; code: `world/mercs.rs`
(hire, price), `world/partyxp.rs`, `world/social.rs` (`PARTY_MAX`), `world/rolls.rs`,
`world/instances.rs` (`make_instances`), `world.rs` (instance order, `FALLEN_HOLD_MAX`),
`items.rs` (`boss_slots`, `boss_piece_for`, `EXTRA_SLOTS`), `world/chests.rs`
(`blocked_grid`).

## 15. RAID-MAP implementation (2026-10-22)

Source is in `.tools/emberwake-worktree`, branch `feat/raid-approach`. The entrance
remains sealed. No production files or database have been changed by this task.

`python3 scripts/generate_chained_forge.py` appends file zone **46**, a 320 × 320
indoor raid with three copies, level 99 and ten fighters. The byte-stable generator
writes an exact collision complement and the matching `forgeFloor` art mask.
It preserves later zones, existing encounters/quests and an already-open entrance;
`--open` is reserved for RAID-OPEN. `generate_emberwake.py` reapplies the raid door
and quartermaster directions after rebuilding the approach. Pipeline tail:
`generate_blackhour.py` → `generate_emberwake.py` → `generate_chained_forge.py` →
`place_boss_adds.py` / `place_boss_signs.py` when encounters exist → `sync-world.cjs`
→ rebuild Rust.

The plan has **32,102 floor cells**, including the isolated 575-cell muster chamber;
31,527 belong to the connected main descent. There are ten distinct courts joined
by basalt galleries and narrow iron bridges over the molten forge. Workshop landmarks, chain pylons, lights, molten falls, vents and numbered rally
marks give the courts their identities. Static lava lies below the floor and is impassable; there
are no invisible damage volumes. Moving hazards and their warnings belong to the
individual boss tasks. The floor reserves ten four-enemy pack sites (six mandatory,
four in side forges); actual enemies, elites, quests, enemy-name entries and their
art belong to RAID-PACKS and RAID-BOSS, so this task adds no placeholder monsters.

| Hall | Centre | Approach length / 5.2 tiles per second |
| --- | --- | --- |
| The First Link | 84, 272 | 5.57 s |
| The Iron Lung | 209, 272 | 24.12 s |
| The Three Anvils | 270, 204 | 22.57 s |
| The Numbered Forge | 164, 201 | 20.66 s |
| The Divided Crucible | 55, 201 | 21.13 s |
| The Brand Gallery | 52, 117 | 16.77 s |
| The Cinder Floor | 156, 121 | 20.38 s |
| The Quenching Wells | 268, 122 | 21.91 s |
| The Last Chain | 266, 43 | 15.88 s |
| The Promised Table | 111, 43 | 30.24 s |

These are geometric estimates along the authored routes, totalling 199.23 s,
excluding fights, looting and regrouping. The private MCP walkthrough records
actual wall-clock walking times for every leg.

**Inside-only hiring.** The external Nine-Chain Door leads to a physically separate
muster chamber; the level-99 restriction and seal apply there too. Entering that
chamber does not require a complete group. Quartermaster Halla signs raid contracts
inside it at the normal price (nine cost 1,035,000 gold). The inner gate requires
exactly ten living level-99 group members gathered within 20 tiles and transfers
all ten together. Its solid surroundings prevent walking around it. This preserves
the outdoor cap of four hires. Contract fighters are dismissed when their owner
returns outdoors. Interior debug validation can exercise this gate while the
external entrance remains sealed; no public debug flags are enabled.

**Recovery.** A raid fighter stays fallen for at most 2,400 seconds during an active
boss fight; ordinary dungeons keep 600 seconds. On a complete wipe, only the active
boss is restored to full health and its mechanics engine returns awakened helpers
to sleep. Killed bosses and packs stay dead. Everyone, including contract fighters,
wakes at that hall's rally mark, contracts retained, with 60 seconds free of
automatic enemy aggression; attacking ends that grace early. Empty raid copies
reserve progress for 20 minutes and can be reclaimed by their previous group;
other dungeons retain their immediate empty reset. Raid chest placement starts its
reachability search on the descent, so the separate muster does not hide the
entire dungeon from the chest system.

**Client.** `client/chainedforgeart.js` registers original code-native scenery with
`City.art`, floor shading, iron seams, lava-bank edges, background, portals and
hall landmarks. `field.js` uses the authoritative floor mask for the ground and
minimap; the world atlas has a tile and floor renderer, hidden while sealed.
The raid is enclosed (`DayNight.nightMix === 0`). Music is silent until RAID-MUSIC
adds the industrial techno scores; the approach retains its own music.
Hand-written Swedish covers the hall names, quartermaster, directions and recovery.

**Migration before release.** There are now 47 file zones. Existing dungeon extras
are 47–106, raid extras 107–108, Arena copies 109–116; total runtime maps 117.
`vault_tests.rs::COPY` is 47. Relative to the deployed world without Emberwake,
old extra ids shift by +2 and Arena copies by +4. Derive the final mapping from
the running binary and saved character zones before RAID-OPEN. No live DB has
been inspected or migrated here.


RAID-MAP validation completed 2026-10-22: six focused Rust checks and five related
Emberwake/raid contract/portal checks pass. Clippy (`--all-targets --profile test --
-D warnings`), fmt, changed JavaScript/Python syntax, the Swedish build check and
generator stability/preservation checks pass. The real-sprite Chromium check passes
32 assertions with no page errors or missing raid assets, including both screen
sizes for every hall and a paired comparison of the actual field render with its
scenery removed. Screenshots: `test-results/driver-7ZhAat`.
The private MCP scenario passes 22 checks: the external seal,
inside-only contracts and their price, copy isolation, the ten-fighter gate, walking
every hall, and safe return/dismissal. Measured walking totals **215.50 s**
(3.59 min); per-leg times are in
`test-results/chained-forge-map/walk-times.txt`, and its raw world report is
`test-results/driver-JJC71D/report.json`. This is a floor-plan check;
RAID-PACKS, the ten boss tasks, loot, weapons and music remain separate tasks.
No full suite, live migration or deployment was performed.

At the owner's request, all twenty hall screenshots (desktop and mobile), the
muster chamber and the zone overview were uploaded to Sork's FileDrop: **22 PNGs**,
9,113,088 bytes. Every uploaded file and metadata sidecar was checked; the SHA-256
receipts are in `test-results/chained-forge-map/filedrop-upload.json`.


### Molten exterior follow-up (owner, 2026-10-22)

Animated lava follow-up (2026-10-22): Emberwake and the Chained Forge now share
`EmberwakeArt.moltenMotion`, drawn above the cached terrain and below actors and
combat telegraphs. Sparse warm glints drift slowly across hot fissures; small
bubbles swell, rise slightly, then flatten and fade as they pop. There are no
sparks or flashes. Positions and phases are derived from world coordinates and
the existing frame clock, so moving the camera does not move the effect relative
to the lava. Anchors exclude the river banks and the raid's authoritative floor
mask, including bridges. The minimap and world map retain their static terrain.

Four-tile anchor chunks are generated on demand with a bounded 192-entry cache
per zone. The existing texture caches are unchanged; there is no new animation
loop or per-frame texture generation. No visible anchors means no canvas calls;
reduced motion returns immediately with no overlay. Client files are served from
disk, so this change needs no server build or restart.

Focused real-sprite validation: `tests/lava-motion-ui.cjs` passes 18 assertions
against a private server. Paired actual field frames change 911–963 pixels in
the sampled views, with a maximum channel change of 26/255; reduced-motion
frames have zero overlay changes. Sixty sampled overlay frames per zone show
no pixels on walkable ground or outside the river, at most three simultaneous
bubbles, and exact matching pixels after a camera shift. The sampled cached
overlay cost is approximately 0.02–0.05 ms/frame in headless Chromium (800×500).
`MUTATE=1` disables the overlay in the test browser and fails at the first
actual-field pixel assertion (zero changed pixels). JavaScript syntax and diff
whitespace checks pass. Report and screenshots: `test-results/driver-YGaP7o/`.

The owner requested that all unwalkable space look like Emberwake's molten river.
`ChainedForgeArt.background` now paints a continuous isometric molten surface in
world coordinates, using the same `EmberwakeArt.moltenColor` sampler as the river:
glowing orange/yellow fissures, irregular dark crust plates and cooled shores
beside the authoritative floor mask. It replaces the earlier striped background.
Eight-tile texture chunks have sampling gutters and a 96-entry cache, so the large
raid does not allocate one full-map lava image. The texture stays attached to the
world through movement and zoom, including outside the map boundary.

`tests/chained-forge-lava-ui.cjs` passes six focused real-client assertions. The
actual outside surface contains both bright fissures and dark crust, all 5,162
camera-shift samples match, and the refactored Emberwake river differs from the
previous renderer by zero channels across 63,198 painted pixels. Replacing the
new renderer with a flat backdrop makes the test fail (no bright fissures).
Desktop and mobile screenshots cover the muster chamber, bridge, throne and outer
edge. Reports: `test-results/chained-forge-map/molten-render-result.txt` and
`molten-render-mutation.log`; screenshots: `test-results/driver-L1DzQS/`.
At the owner's standing screenshot request, eight updated PNG previews were added
to Sork's FileDrop and verified by SHA-256 and metadata; receipt:
`test-results/chained-forge-map/molten-filedrop-upload.json`.
This follow-up changes client rendering only; source is retained on
`feat/raid-approach` in the raid worktree, with no deployment.

Session wrap-up: the owner invoked the `finish` skill to commit and push the
prepared source on `feat/raid-approach` and the main TODO pointer. The source stays
isolated from the served checkout. Wiki: `10_projects:valhallasc_chained_forge_map_20261022`.


## 16. RAID-PACKS — implementation and owner corrections (2026-10-22)

The owner's corrections in this task supersede section 4's outdoor-style elite
rule: **this is a dungeon. All 40 enemies in its ten four-enemy packs are elites;
there are no three special elites or elite side quests.** The ten bosses are
separate tasks. All packs remain level 99, six mandatory and four optional.

Four original kinds: Slaghammer Brute (hammer slam), Ventspitter Crawler
(three-shot fan), Crucible Channeler (five-shot magma fan), Obsidian Bulwark
(melee). Their catalog is `world/chained_forge.txt`, generated from
`scripts/chained_forge_content.py`; `raidPack: true` identifies the dedicated
purple-roll path independently of the elite flag. Tuning remains exclusively in
`world/elite-power.txt`. Every kind fully heals after an evade and has no respawn
inside the active instance, as other dungeon packs do.

**Owner correction: purple mob drops must be unique and class-neutral.** The
ordinary progression and Nullforged pools are not the mob's purple rewards.
Cinderwork Kiln Gaiters, Cinderwork Crucible Pendant and Cinderwork Clamp Ring
are three original level-99 purple pieces, wearable by all five classes. They use
the existing level-99 purple stat budget with original louvred gaiters, open
crucible pendant and square clamp-ring geometry fitted to all ten body rigs.
They have no set bonus and never join the ordinary equipment pool. The 3% roll
is independent of materials and normal gray/green/blue equipment, multiplied by
rebirth through `copies`, and uses the existing humans-only raid loot path. The
ordinary purple and orange rolls are suppressed in this raid. At the base rate,
40 kills yield **1.2 purple pieces per full pack clear on average**, 0.72 for six
mandatory packs; this is per enemy, not per pack. Boss orange tables remain for
RAID-ORANGE.

Measurement fixture: the real quartermaster hires nine contract fighters, giving
two of every class including the Warrior hirer. All use the existing `auto_play`
brain, points and consumables. The approved interim equipment is Worldheart's
five orange slots plus Nullforged purple pants, necklace and two rings: **nine
worn pieces, no cloak** (the separate cloak branch is not merged here). These are
fixture items, not the new mob drop pool. Repeat measurements after Chainforged
and the cloak work are integrated.


### Owner update: deliberately overpowered

After the diagnostic fights, the owner said: **"don't worry so much about the
time to clear a pack. just make the packs overpowered. i have a fix in mind for
later"** (2026-10-22). Clear-time calibration stopped at that instruction. The
500–620-second target and a guaranteed win for the hired ten are deferred; no
later fix has been guessed or implemented here.

All four kinds use **`[140, 90]` health/damage multipliers** in
`world/elite-power.txt`. These deliberately strong settings can overwhelm the
geared hired ten. Earlier tuning logs are experiments, not accepted clear-time
promises. Rebalance only when implementing the owner's later fix.

| Kind | Behavior | Level-99 health after tuning | Authored damage × multiplier |
| --- | --- | ---: | ---: |
| Slaghammer Brute | melee-range hammer slam | 179,200,000 | 16,300 × 90 |
| Ventspitter Crawler | three-shot ranged fan | 134,400,000 | 13,500 × 90 |
| Crucible Channeler | five-shot ranged fan | 155,400,000 | 13,900 × 90 |
| Obsidian Bulwark | melee pressure | 179,200,000 | 16,300 × 90 |

Damage values precede the engine's global damage scale, armor and wards. Each
pack contains one of each kind. Bridge sites 2, 5 and 6 use lines along their
walkable floor; other sites use a three-tile square. They use normal dungeon AI,
without boss scripts.

The optional ignored diagnostic `raid_pack_measure_encounters` defaults to one
seed, reports raw kills/falls/DPS/time, and imposes no pack time band or ten-player
win gate. `RAID_PACK_FIGHTS=pack1,pack2`, `RAID_PACK_SEEDS`,
`RAID_PACK_COUNT=1|8|10` and `RAID_PACK_CLASS` select a fixture. The lone-player
control must still die. `raid_pack_careless_ten_without_defense_or_healing_lose`
checks a group using basic attacks without defensive skills or consumables.
Use the RAID build cache and one scratch test executable; never replace it
while a diagnostic is active. No further timing runs are needed for this task.

Encounter compaction preserves local authored collision, with a full-map
control available via `RAID_PACK_FULL_MAP=1`. Full terrain is restored before a
fallen fighter can wake outside the retained area. The equipment index preserves
original first-match catalog selection, checked across every class/kind/variant.


### Final verification

Only the new content was tested; no full suite, release or public restart.
Seven focused `raid_pack` tests, six `chained_forge` tests, gear-level and set
catalog checks pass. Brief fixed-fixture controls kill a lone fighter in all
five classes; the Priest is also checked at both bridge sites, and all ten
basic-only fighters fall in the careless control. No further clear-time sweep.
Clippy with warnings denied, fmt, changed JS/Python syntax, Swedish and two
byte-stable generator rebuilds pass.

The final optimized private server passes MCP `raid_packs` (copy isolation,
actual material kills, unique loot fixtures and persistence; report
`test-results/driver-QoJ0vb/report.json`) and **17 real-client checks** at desktop
and mobile sizes (`test-results/driver-9AAGHn/raid-pack-desktop.png` and
`raid-pack-mobile.png`). All **8,160 gear poses** pass across ten body rigs;
substituting the old gear art fails the silhouette guard. Consolidated evidence:
`test-results/raid-packs/verification.json`. Generator commands and source remain
in the isolated raid worktree on `feat/raid-approach`; nothing is deployed.


## 17. Raid strength (owner request, 2026-10-22)

The owner requested **+1% damage-taken reduction and +50% extra attack for each
other fighter in the instance**, and explicitly confirmed that **mercenaries
count too**. This is implemented for the raid template and each private raid
copy. Each human and hired fighter receives the bonus individually:

| Fighters present | Other fighters | Extra attack | Total attack | Incoming damage multiplier |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | 0% | 1× | 1.00× |
| 2 | 1 | +50% | 1.5× | 0.99× |
| 5 | 4 | +200% | 3× | 0.96× |
| 10 | 9 | **+450%** | **5.5×** | **0.91×** |

Presence is determined by the authoritative runtime zone id, before copy ids are
mapped back to the public template in snapshots. Other copies, outdoor zones,
ordinary dungeons, ambient actors, escorts, gauntlet actors and hidden GMs do not
contribute. A fighter counts themselves zero times. The bonus is capped at nine
others, has no distance restriction, and counts fallen fighters who remain
inside. Entering, exiting, disconnecting or dismissing hired fighters changes
it automatically; party members outside the copy contribute nothing.

`server/src/world/raid.rs` computes this from current actors. The bonus never
modifies saved gear, attributes or the character's base stats. Basic attacks,
damaging skills and attack-based set effects use the boosted attack power.
Attack-based healing uses that same power; fixed percentage-of-health heals do
not change. The incoming multiplier combines with armor, shields and other
normal reductions before absorption. Boss heavy hits also receive the reduction;
explicit instant-kill mechanics still kill.

Snapshots expose the effective attack and a `raidSupport` breakdown. The
character panel displays the other-fighter count and both bonuses, including
Swedish. The client explicitly clears `hero.raidSupport` when leaving: its
normal actor merge keeps old optional fields unless they are cleared.

Validation: six focused `raid_support` Rust tests cover real quartermaster
contracts, same-copy presence, fallen members, removal, non-raid exclusion,
caps, seeded attack rolls, actual incoming hits, shields, attack-based healing,
snapshots and boss heavy/instant-kill paths. `tests/raid-support-ui.cjs` passes
**20 private browser checks**: nine real hires and their live percentages,
mercenaries receiving the same bonus, another copy staying solo, desktop/mobile
character panel, dismissal, exit, and Swedish. Evidence:
`test-results/driver-OVjunQ/raid-support-ui.json` and the desktop/mobile PNGs.
Clippy with warnings denied, fmt, JS syntax and Swedish checks pass. Clear-time
calibration remains deferred. Source is in the isolated raid worktree, not
committed or deployed in this follow-up.

## Combined release integration (2026-10-22)

The cloak branch adds the tenth worn slot to every full-gear fixture. The
interim raid fixture now wears six Worldheart pieces (the original five plus
the class-neutral cloak), Nullforged pants and necklace, and two rings: ten
pieces total, with each ring slot listed once. Actual hired fighters receive
their ordinary level-appropriate green cloak unless a full-gear measurement
explicitly replaces it. Pack multipliers remain `[140, 90]`; the owner deferred
pack timing calibration. Inspect now displays the same effective raid attack
as Character. The unfinished raid entrance remains sealed.

## 19. Raid rewards implementation (2026-10-22)

`docs/raid-rewards.md` records the actual 29-piece tables, 22 guaranteed drops,
ten-slot outfit including the cloak/two rings, original all-pose PixelFlow art,
2/4/6/8 set bonuses and five signature weapons. The later owner PvP decision
supersedes section 12 answer 4. The actual table model is 4 clears median for a
solo hirer, 3/7 for five humans, 5/12 for ten humans (first/all complete),
including the cloak. No encounter tuning, boss mechanics or entrance release
is included in this slice.

## 18. First three Wardens (2026-10-23)

Kettil, Ysolt and Hallgrim are built in the isolated `feat/raid-bosses-1-3`
checkout. Exact mechanics, fairness adjustments, original PixelFlow sources,
Chainforged reward integration, focused checks and measured boss times are
recorded in [raid-bosses.md](raid-bosses.md). The entrance remains sealed.
The owner-approved raid reduction is now 5% per other fighter, capped at 45%;
this supersedes section 17's original 1%/9% numbers. Pack-time tuning stays deferred.

## 19. Fourth Warden: Sigrun Slagmother

Sigrun and her six numbered ingots are built in isolated `feat/raid-boss-4`. The 25-second ordered shield and its 40% reforge, original PixelFlow art, signs, hired targeting and focused validation are described in [raid-boss-4.md](raid-boss-4.md). The entrance remains sealed.
