# Dungeon difficulty report (2026-10-16)

Owner's rules: a **pack** (3 or more mobs chained within 10 tiles) must kill a lone player; a **boss** must kill a lone player; a **party of five** in green gear must beat every pack and boss. Single mobs are only reported.

## Tooling

- `ELITE_POWER_FILE=<path>` (test builds only, read by `items::elite_power`) replaces `world/elite-power.txt`, so a multiplier trial needs no rebuild.
- `DUNGEON_SOLO_DUNGEONS=undervault,cloister` (name words) and `DUNGEON_SOLO_KINDS=thrall,hollowking` (kinds; packs are kept when they hold one) limit a run. `DUNGEON_SOLO_CLASS` takes a comma list.
- `python3 scripts/dungeon-calibrate.py <dungeons> --kind thrall=3 --kind hollowking=2,4 [--tests pack,boss,party] [--seeds 2] [--kinds ...] [--classes ...] [--verbose] [--write]` merges the multipliers (`kind=damage` or `kind=hp,damage`) over the table, runs the lone and party checks on all cores and prints survivors per dungeon and boss. A two-dungeon trial takes 2 to 5 minutes.
- Report-only tests: `dungeon_inventory` (what each dungeon holds) and `dungeon_probe` (damage taken per boss and class).

## Packs: done

Damage multipliers (health 1) in `world/elite-power.txt`:

| Dungeons | Kinds | Damage |
| --- | --- | --- |
| Undervault | thrall, archer, acolyte | x7 |
| Drowned Cathedral (three wings) | tidetemplar, tidecantor, tideleech, reliccrab, abysszealot | x16 |
| Moonwell, Rain Crown, Seed Vault, Thunderheart Gate, Solar Crucible, Amber Archive | all their mob kinds | x24 |

Final run, 4 seeds, 10 dungeons, 32 packs: **a lone player survived 0 of 640 fights** (five classes, green gear), and **five players in green gear won every pack in 4 of 4 runs**. Headroom is small in the Undervault (x8 already makes the pack of eight slow: 105 s with deaths; x12 loses it) and in the Cathedral (x30 loses the party); the later dungeons tolerate x30 only marginally. The lone Priest is the last class to die: below these values it out-heals and wins, at the lowest health of 0 to 25 percent.

Six dungeons have **no pack of three or more** (Eye Below, Elder Hollow, Thousandfold Pavilion, Sunken Astrolabe, Blooming Labyrinth, Silent Solstice): only lone mobs, pairs and triples spaced more than 10 tiles apart. They were left alone. Either add real packs in `world/*.txt` or make the pairs lethal by power; the owner has to choose.

## Bosses: soft enrage (2026-10-16, second pass)

Health/damage multipliers cannot do it (see the last section). A **soft enrage** can: `world/enrage.txt` maps a boss kind to `[start, ramp]` in seconds; after `start` seconds of fighting, the boss's damage is multiplied by `1 + (fight - start) / ramp` (a ramp of 0.2 is +100% per 0.2 s, so a few hits after the start end any hero). The clock (`Slime.fight`) runs while the boss has a target within 14 tiles, drains when nobody is that close and restarts when the boss returns home (`items::enrage_factor`, applied to melee, slam and ranged bolts).

How the table was made: baseline of all 53 bosses (5 classes x green, purple, purple+5 x 2 seeds = 1,590 lone fights); every boss except the Undervault's Choir, Colossus and Hollowking was cleared by someone. For each of the 47 bosses with a party time, `start = ceil(1.06 x slowest party-of-five kill in 4 seeds) + 2`, `ramp = 0.2`. A slow ramp (+100% per 3 or 10 s) hardly changed anything: a lone purple hero absorbs the first enraged hits and finishes.

Result on the 47 bosses (2 seeds, 1,410 lone fights): lone clears fell from 820 to 303. Green gear: 36 clears before, **0 after**. Purple at the dungeon's level: 383 before, **42 after**. Purple +5 levels: 401 before, 155 after (accepted by the owner: a hero five levels up may clear a boss; the lone-boss test now only checks green and purple at the dungeon's level). The 42 same-level purple clears are fights that end before or just after the start. The party of five in green gear wins every one of the 47 in 4 of 4 runs (final run with the real file), as it did without the enrage: it never reaches the start.

Not covered, and why:

- **Choir, Colossus, Hollowking** (Undervault; Hollowking now has the Dirge of the Hollow, see `docs/boss-mechanics.md`: a lone hero dies at the first song or the next, 0 of 144 lived): no lone player can kill them and they stay as they were (the lone Priest survives); a party needs 90 to 180 s, so no safe start exists.
- **Bloom Heart and Solstice Heart**: a party of five in green gear cannot beat them in 180 s today (72 percent health left, nobody dies). Easing by health is a cliff, not a slope: x0.31 still fails, x0.27 wins in about 18 s, x0.2 in 11 s. Their stats equal Amber Archive's Amber Memory, which the party beats in 77 to 84 s, so the cause is something else (not found). They have no enrage until that is fixed.
- **Thunder Heart** had a bimodal party time (74 to 77 s, or 172 to 180 s with nobody dead, even with the enrage running), so its start (93 s) is based on the fast mode; the slow runs look like a boss that stops engaging.
- (Since 2026-10-18 a boss with a `world/boss-mechanics.txt` entry is exempt, because its wail can end the fight at any moment.) The harness stops a fight as hopeless after 30 s when the lone hero's pace projects past three times the limit and counts it as "survived"; such fights (about 100 of 1,410) never reach the enrage, but the hero cannot win them either.

Tools: `ENRAGE_FILE=<path>` (test builds) and `scripts/dungeon-calibrate.py --enrage-file <path>`. The party check now runs one process per core.

## Hired party of five against the sixteen final bosses (2026-10-19, `BOSSMECH-MERC` / `BOSSMECH-CHECK`)

`cargo test a_hired_party -- --ignored --nocapture` (`DUNGEON_SOLO_SEEDS=4`, about 11 minutes): the hirer is a warrior in green gear at the dungeon's level; at Skaldholm's Meeting Stone, through the real offers (250 gold each), they hire a priest, a mage, a hunter and an assassin. The hired fighters have no gear (level attributes and starting potions) and play themselves (`merc_think`, `boss_play`). The same seeds are fought by the bot party of five (the control above). A boss counts as won only if it dies within 180 s; falls do not matter. The rule: the hired party wins at least half the seeds and never fewer than the bot party minus one.

| Boss | Hired | Bots | Boss | Hired | Bots |
| --- | --- | --- | --- | --- | --- |
| Hollowking | 4/4 | 4/4 | Seed Vault Worldseed | 4/4 | 4/4 |
| Choirmother | 4/4 | 4/4 | Sunken Astrolabe Axis | 3/4 | 4/4 |
| Coral Regent | 4/4 | 4/4 | Thunder Heart | 4/4 | 4/4 |
| Hierophant | 4/4 | 4/4 | Bloom Heart | 4/4 | 4/4 |
| Moonwell Echo | 4/4 | 4/4 | **Solar Heart** | **1/4** | 4/4 |
| Eye Below | 3/4 | 4/4 | Amber Memory | 4/4 | 4/4 |
| Elder Heart | 4/4 | 4/4 | Solstice Heart | 4/4 | 4/4 |
| Pavilion Sovereign | 4/4 | 4/4 | Rain Crown | 4/4 | 4/4 |

Fifteen of sixteen meet the rule. **Solar Heart** does not (1 of 4; 2 of 8 in a longer run) and is listed in `KNOWN_SHORT` in the test. Cause, from the fight trace: a hired fighter who falls wakes at the door, runs 40 to 60 tiles back alone and arrives into bodies that have moved; Twin Suns' bridge of light (lethal within 1.1 of the line between the bodies, which chase) kills the whole party again and again, and a wiped party ends the run (36 to 49 s, boss at 1 to 14 percent). `BOSSMECH-DEATH` (the dead stay down until the fight ends) removed the run-in loop; the re-run is in the last section (Solar Heart 3 of 4).

What the check changed:

- **The harness** (`ttk.rs`, `run_hired_party_pack_once`): only the hirer is driven; the party is not beaten while a hired fighter lives (the first version stopped as soon as the hirer fell). A hirer who has been idle 10 s with no line of sight to the boss is set down in sight of it with the hired fighters beside them ("stepped round a wall" in the output): bodies and bots walk in straight lines and a wall between them was a stalemate no human would keep.
- **The brain** (`boss_play.rs`): against a divided boss each fighter kept re-choosing the half with more health after every blow, so the whole party changed sides of the bridge every second or two (trace: target 1197, 1198, 1197...). A fighter now stays on the half they chose until the other has a fifth more health (`BossMech.halves`). The bot party on Solar Heart: 8 of 8 before and after (62 to 88 s); a side-of-body station instead of the far side was tried and made the bots worse (5 of 8), so it was dropped.
- Eye Below and the Astrolabe each lose one seed to the hired party (3 of 4): the hired fighters fall more (10 falls in the worst run) but still kill the boss three times in four.

### Why multipliers alone failed (first pass)

Measured with the same tools:

- Undervault bosses (80k to 130k health, a party of five needs 76 to 120 s at x1): damage x2.5 already leaves the party at 1 of 2 on the Colossus and Hollowking while 75 of 120 lone fights survive; x4 loses the party on Gatewarden (180 s, nobody died, the time runs out because the party spends it healing); x6 kills all five. Party time grows with damage even with no death. The lone Priest survives up to x5 and still clears Gatewarden at 0.7 health x12.
- Flooded Cloister bosses: x4 changes nothing (94 of 120 survive); x10 leaves 51 of 120 alive (only purple, +5 levels, almost all classes) and loses the party on Choirmother. A lone character in purple gear is about as strong as five in green, so any damage that kills the purple character also breaks the green party.
- Priests out-heal every boss in the sim (hero health 2.0k to 9.9k, boss hits of 6k to 8k nominal).

So **no health/damage pair makes a boss kill a lone purple+5 player while a green party of five still wins**. A mechanic is needed (for example a soft enrage: after N seconds the boss's damage ramps, which a party's burn-down beats and a lone fighter cannot), or the rule has to say "a lone player cannot kill it within 180 s" instead of "the boss kills a lone player". Boss and mob power for bosses is unchanged.

## The fallen stay down (2026-10-19, `BOSSMECH-DEATH`)

A hero or hired fighter who dies while a final boss fight runs stays down until it ends (boss dead, or nobody left and the boss walks home), then wakes at the door 3.2 s later, together with everyone else who is down. The harness no longer puts a fallen bot back after 20 s, and `KNOWN_SHORT` is gone from the hired-party test. Rule 10 of `docs/boss-mechanics.md`.

Same seeds, four each, the shipped table:

- **Bot party of five, all sixteen: 4 of 4** (falls only on Solar Heart 1-2, Eye Below 1-2, Bloom Heart 0-2). Times unchanged from the party table in the sections above.
- **Hired party, all sixteen: meets the rule** (wins at least half and not fewer than the bot party minus one): 14 bosses 4 of 4, Thunder Heart 3 of 4, Solar Heart 3 of 4 (it was 1 of 4 with the run-back).
- **A lone player still dies** to every boss (`a_dungeon_boss_kills_a_lone_player`, two seeds, green and purple): ok. A death now ends a lone fight at once, so the enrage starts were left as they are (a re-derivation would only tighten them; the party wins still sit inside `1.06 x slowest win + 2`).

What the permanent death exposed (neither was visible while the fallen came back):

| Boss | Before the fix | Cause | Fix |
| --- | --- | --- | --- |
| Solstice Heart | 0 of 4, all five fell at the first Night | a fighter pressed against a wall passed no full-width line test, so the flee search found nothing; a brazier 15 tiles off was missed by a ring of 24 angles; fighters on safe ground walked off to light another brazier while the dark was up | the nearest burning brazier is the goal, thin line test, no walking off while a kill zone is up: 4 of 4, 0 falls |
| Axis | hired 2 of 4, four dead in the first tick | new spokes begin at a random angle and were lethal at once | new spokes are dashed and harmless for 3 s (`SPOKES_ARM`): hired 4 of 4 |

Fall counts of the hired party, per boss (four seeds): Hollowking 0, Choirmother 0-3, Coral Regent 0, Hierophant 0-3, Moonwell Echo 0, Eye Below 0-4, Elder Heart 0-4, Pavilion 0-4, Rain Crown 0, Worldseed 0-4, Axis 0-3, Thunder Heart 0-9, Bloom Heart 0-3, Solar Heart 1-9, Amber Memory 0, Solstice Heart 0-4.

## Recalibration after the class balance (2026-10-20)

The class balance (`DPS-BALANCE-99`, `DPS-BALANCE-40-95`) raised mage, priest and hunter damage about 50% from level 40, so about 30 non-final bosses fell to a lone character in purple gear. Fix, in order:

- **Health** (`world/elite-power.txt`, x1.33 to x3.86) brings each non-final boss to 69-75 s for the hired five (`BOSS-LENGTH-MID`). Time rises faster than health (`chainmarshal` x4.83 gave 14 s to 92 s), so it took two passes with factor x (70 / measured)^(1/1.2). `choir` and `colossus` are not scaled (documented exceptions); `gatewarden` is scaled (x1.39) but gets no ranged attack.
- **Enrage starts** (`world/enrage.txt`): `ceil(1.06 x slowest hired win) + 2`, 76-80 s; `pavilion_weaver` is 62 s, because a lone purple priest kills it in 75 s like the hired five (starts of 64 s or more let her live).
- **Ranged attacks** (`world/boss-ranged.txt`): a ranged hero used to stay outside the enrage range (14 tiles) and never be reached. Every non-final boss now shoots from range; fans have an odd number of shots, because with an even number none flies straight and a hero standing still was never hit (the hunter took 0 damage in 180 s from the four-shot bosses).
- **Harness**: `Case.run_to_end` stops the "hopeless" early exit in `a_dungeon_boss_kills_a_lone_player`; it used to report a player as alive whom the enrage would have killed a little later.
- **Packs**: priest cleared the Coral Reliquary pack (tidetemplar, tidecantor, reliccrab, now damage x20) and the Rain Crown pack (droplet, guard, oracle, now x30); the party of five still wins them.
- Result: 700 lone boss fights (35 bosses x 5 classes x green/purple x 2 seeds), 0 survivors; the hired five win 4 of 4 on all 37 non-final bosses; the old dungeons' packs all kill the lone player. Open: the new Nornroot Barrow and Shattered Span packs.
