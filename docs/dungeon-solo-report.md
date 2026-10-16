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

## Bosses: not reachable with multipliers

Measured with the same tools:

- Undervault bosses (80k to 130k health, a party of five needs 76 to 120 s at x1): damage x2.5 already leaves the party at 1 of 2 on the Colossus and Hollowking while 75 of 120 lone fights survive; x4 loses the party on Gatewarden (180 s, nobody died, the time runs out because the party spends it healing); x6 kills all five. Party time grows with damage even with no death. The lone Priest survives up to x5 and still clears Gatewarden at 0.7 health x12.
- Flooded Cloister bosses: x4 changes nothing (94 of 120 survive); x10 leaves 51 of 120 alive (only purple, +5 levels, almost all classes) and loses the party on Choirmother. A lone character in purple gear is about as strong as five in green, so any damage that kills the purple character also breaks the green party.
- Priests out-heal every boss in the sim (hero health 2.0k to 9.9k, boss hits of 6k to 8k nominal).

So **no health/damage pair makes a boss kill a lone purple+5 player while a green party of five still wins**. A mechanic is needed (for example a soft enrage: after N seconds the boss's damage ramps, which a party's burn-down beats and a lone fighter cannot), or the rule has to say "a lone player cannot kill it within 180 s" instead of "the boss kills a lone player". Boss and mob power for bosses is unchanged.
