# Group elites against a lone player (ELITE-SOLO-TEST)

Run on 2026-10-16: 113 elites and bosses taken from the group quests in `world/map.txt` (`group` and `recommendedPlayers` of 2 or more), each fought by a lone character of every class, 2 seeds, at the quest's level. The rotation is the kill-time rotation with every potion and meal, and the enemy is levelled to the character. Run it again with `ELITE_SOLO_SEEDS=2 bash scripts/elite-solo-parallel.sh` (about 25 minutes on 4 cores) and the control with `bash scripts/elite-party-parallel.sh` (about 4 minutes). The lone-player tests are `#[ignore]`d in the normal suite because they fail until `ELITE-SOLO-FIX` is done.

## Lone player in green (the baseline gear) gear

1130 fights, 142 lone kills. **19 of 113 elites can be killed by at least one class.** Wins are out of 10 fights (5 classes, 2 seeds).

| Elite | Level | Recommended players | Wins | Winning classes |
|---|--:|--:|--:|---|
| cinderlord | 10 | 2 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| eye_adept | 65 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| eye_drifter | 65 | 5 | 8/10 | Assassin 2, Mage 2, Priest 2, Warrior 2 |
| eye_lurker | 65 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| elder_barkguard | 70 | 5 | 6/10 | Assassin 2, Hunter 2, Priest 2 |
| elder_moth | 70 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| elder_thornling | 70 | 5 | 6/10 | Assassin 2, Mage 2, Priest 2 |
| pavilion_foldling | 75 | 5 | 6/10 | Assassin 2, Mage 2, Priest 2 |
| pavilion_inkmoth | 75 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| pavilion_silkguard | 75 | 5 | 7/10 | Assassin 2, Hunter 2, Mage 1, Priest 2 |
| rain_crown_droplet | 80 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| rain_crown_guard | 80 | 5 | 4/10 | Assassin 2, Priest 2 |
| rain_crown_oracle | 80 | 5 | 8/10 | Assassin 2, Mage 2, Priest 2, Warrior 2 |
| seed_mote | 80 | 5 | 6/10 | Assassin 2, Mage 2, Priest 2 |
| astro_gearling | 85 | 5 | 7/10 | Assassin 2, Mage 1, Priest 2, Warrior 2 |
| bloom_spore | 97 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| solar_emberling | 98 | 5 | 6/10 | Assassin 2, Mage 2, Priest 2 |
| amber_page | 99 | 5 | 6/10 | Assassin 2, Mage 2, Priest 2 |
| solstice_flurry | 99 | 5 | 8/10 | Assassin 2, Mage 2, Priest 2, Warrior 2 |

## Lone player in purple (the best ordinary set; orange, refined and set-bonus gear are not covered) gear

1130 fights, 572 lone kills. **91 of 113 elites can be killed by at least one class.** Wins are out of 10 fights (5 classes, 2 seeds).

| Elite | Level | Recommended players | Wins | Winning classes |
|---|--:|--:|--:|---|
| cinderlord | 10 | 2 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| hvitserk | 37 | 3 | 8/10 | Assassin 2, Hunter 2, Mage 2, Warrior 2 |
| bellkeeper | 40 | 5 | 3/10 | Assassin 1, Hunter 2 |
| ghostmaw | 40 | 3 | 8/10 | Assassin 2, Hunter 2, Mage 2, Warrior 2 |
| mournsister | 40 | 5 | 2/10 | Warrior 2 |
| glasscantor | 45 | 5 | 4/10 | Assassin 2, Hunter 2 |
| pearlwidow | 45 | 5 | 4/10 | Assassin 2, Hunter 2 |
| relicwarden | 45 | 5 | 6/10 | Assassin 2, Hunter 2, Warrior 2 |
| mirrorqueen | 49 | 3 | 6/10 | Assassin 2, Mage 2, Warrior 2 |
| chainmarshal | 50 | 5 | 4/10 | Assassin 2, Warrior 2 |
| hierophant | 50 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| starseraph | 50 | 5 | 6/10 | Assassin 2, Hunter 2, Priest 2 |
| tidejudicator | 50 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| pendulummatron | 54 | 3 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| epochengine | 55 | 5 | 2/10 | Mage 2 |
| mireheart | 58 | 3 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| silverwidow | 59 | 3 | 7/10 | Assassin 2, Mage 2, Priest 1, Warrior 2 |
| hourpetal_stag | 60 | 5 | 2/10 | Priest 2 |
| nightbloom | 60 | 5 | 2/10 | Mage 2 |
| tideglass_heron | 60 | 5 | 6/10 | Hunter 2, Mage 2, Warrior 2 |
| eye_adept | 65 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| eye_drifter | 65 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| eye_lenswarden | 65 | 5 | 4/10 | Hunter 2, Mage 2 |
| eye_lurker | 65 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| maelstromheart | 65 | 5 | 2/10 | Mage 2 |
| honeyjaw | 69 | 3 | 6/10 | Mage 2, Priest 2, Warrior 2 |
| elder_barkguard | 70 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| elder_gatekeeper | 70 | 5 | 3/10 | Assassin 2, Priest 1 |
| elder_matron | 70 | 5 | 4/10 | Assassin 2, Priest 2 |
| elder_moth | 70 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| elder_thornling | 70 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| wickerwarden | 70 | 5 | 1/10 | Priest 1 |
| paradegryphon | 74 | 3 | 8/10 | Assassin 2, Mage 2, Priest 2, Warrior 2 |
| pavilion_foldling | 75 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| pavilion_inkmoth | 75 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| pavilion_mirror | 75 | 5 | 4/10 | Assassin 2, Priest 2 |
| pavilion_silkguard | 75 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| pavilion_weaver | 75 | 5 | 4/10 | Assassin 2, Priest 2 |
| jadeanaconda | 79 | 3 | 8/10 | Assassin 2, Mage 2, Priest 2, Warrior 2 |
| crownjaguar | 80 | 5 | 4/10 | Mage 2, Warrior 2 |
| rain_crown_droplet | 80 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| rain_crown_gatekeeper | 80 | 5 | 4/10 | Assassin 2, Warrior 2 |
| rain_crown_guard | 80 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| rain_crown_oracle | 80 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| rain_crown_sibyl | 80 | 5 | 8/10 | Assassin 2, Hunter 2, Priest 2, Warrior 2 |
| seed_germinator | 80 | 5 | 2/10 | Assassin 2 |
| seed_mote | 80 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| seed_warden | 80 | 5 | 4/10 | Assassin 2, Priest 2 |
| dunecolossus | 84 | 3 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| astro_gearling | 85 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| astro_navigator | 85 | 5 | 4/10 | Assassin 2, Warrior 2 |
| astro_warden | 85 | 5 | 4/10 | Assassin 2, Hunter 2 |
| mirageroc | 85 | 5 | 4/10 | Mage 2, Warrior 2 |
| bellmammoth | 88 | 3 | 8/10 | Hunter 2, Mage 2, Priest 2, Warrior 2 |
| auroramanta | 89 | 4 | 4/10 | Mage 2, Warrior 2 |
| crevasseleviathan | 90 | 5 | 4/10 | Mage 2, Priest 2 |
| cairnbehemoth | 93 | 3 | 8/10 | Hunter 2, Mage 2, Priest 2, Warrior 2 |
| whitebarktitan | 94 | 4 | 8/10 | Hunter 2, Mage 2, Priest 2, Warrior 2 |
| bloomtortoise | 95 | 3 | 8/10 | Hunter 2, Mage 2, Priest 2, Warrior 2 |
| stormcondor | 95 | 5 | 6/10 | Hunter 2, Mage 2, Priest 2 |
| thunder_bastion | 95 | 5 | 6/10 | Assassin 2, Priest 2, Warrior 2 |
| thunder_conductor | 95 | 5 | 8/10 | Assassin 2, Mage 2, Priest 2, Warrior 2 |
| thunder_heart | 95 | 5 | 2/10 | Assassin 2 |
| thunder_spark | 95 | 5 | 2/10 | Hunter 2 |
| glasslion | 96 | 3 | 6/10 | Hunter 2, Mage 2, Priest 2 |
| petalchimera | 96 | 4 | 6/10 | Hunter 2, Mage 2, Priest 2 |
| bloom_heart | 97 | 5 | 4/10 | Assassin 2, Priest 2 |
| bloom_mirror | 97 | 5 | 8/10 | Assassin 2, Mage 2, Priest 2, Warrior 2 |
| bloom_spore | 97 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| bloom_thornkeeper | 97 | 5 | 7/10 | Assassin 2, Hunter 2, Mage 1, Priest 2 |
| lanternowl | 97 | 3 | 6/10 | Hunter 2, Mage 2, Priest 2 |
| rainseraph | 97 | 5 | 6/10 | Hunter 2, Mage 2, Priest 2 |
| rimesaber | 97 | 3 | 8/10 | Hunter 2, Mage 2, Priest 2, Warrior 2 |
| sunwheel | 97 | 4 | 6/10 | Hunter 2, Mage 2, Priest 2 |
| firephoenix | 98 | 5 | 8/10 | Hunter 2, Mage 2, Priest 2, Warrior 2 |
| harvestreaper | 98 | 4 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| snowgiant | 98 | 4 | 6/10 | Hunter 2, Mage 2, Priest 2 |
| solar_ashwarden | 98 | 5 | 8/10 | Assassin 2, Hunter 2, Priest 2, Warrior 2 |
| solar_emberling | 98 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| solar_heart | 98 | 5 | 4/10 | Assassin 2, Priest 2 |
| solar_heliomancer | 98 | 5 | 7/10 | Assassin 2, Mage 1, Priest 2, Warrior 2 |
| amber_chronicle | 99 | 5 | 8/10 | Assassin 2, Hunter 2, Priest 2, Warrior 2 |
| amber_curator | 99 | 5 | 6/10 | Assassin 2, Hunter 2, Priest 2 |
| amber_memory | 99 | 5 | 4/10 | Assassin 2, Priest 2 |
| amber_page | 99 | 5 | 8/10 | Assassin 2, Hunter 2, Mage 2, Priest 2 |
| ambermantis | 99 | 5 | 6/10 | Assassin 2, Mage 2, Priest 2 |
| longnightwyrm | 99 | 5 | 4/10 | Mage 2, Priest 2 |
| solstice_flurry | 99 | 5 | 10/10 | Assassin 2, Hunter 2, Mage 2, Priest 2, Warrior 2 |
| solstice_harbinger | 99 | 5 | 6/10 | Assassin 2, Priest 2, Warrior 2 |
| solstice_heart | 99 | 5 | 4/10 | Assassin 2, Priest 2 |
| solstice_watcher | 99 | 5 | 6/10 | Assassin 2, Hunter 2, Priest 2 |

## Not killed by any lone class, even in purple gear (22)

choir (L20, 5p), colossus (L20, 5p), gatewarden (L20, 5p), gloomroot (L20, 5p), hollowking (L20, 5p), oakhorn (L25, 3p), hrungnir (L30, 5p), choirmother (L40, 5p), kraken (L40, 5p), rootabbot (L40, 5p), coralregent (L45, 5p), sunshard (L50, 5p), moonskein_weaver (L60, 5p), moonwell_echo (L60, 5p), eye_unblinking (L65, 5p), eye_undertide (L65, 5p), elder_heart (L70, 5p), maskcolossus (L75, 5p), pavilion_sovereign (L75, 5p), rain_crown_sovereign (L80, 5p), seed_worldseed (L80, 5p), astro_axis (L85, 5p)

## Control: a party of the recommended size, purple gear, 2 seeds

112 of 113 elites die to a party of the recommended size in at least one of two runs. Cannot win: hollowking (L20, 5 players). Hollowking is the Undervault's final boss; check whether a scripted phase or adds stop the harness before calling it too hard.


## Update 2026-10-16 (evening): the owner's rule and the fix

The first report above measured the original stats and a different rule ("nobody can solo a group elite"). The owner then settled the rule: a lone player at the elite's level in ordinary green gear cannot kill a group elite, but it is soloable with good gear (purple) or about five levels above it, and a party of the recommended size can beat it. Only open-world elites follow this rule (41 of them); a dungeon's mobs and bosses follow the dungeon rules in `TODO.md`. The fight limit is 180 s for lone players and parties alike.

Result with the original stats (180 s limit): only the Cinderlord and, by 2 s, Hvitserk were soloable in green gear; Gloomroot and Hrungnir could not be soloed even in purple. The fix is `world/elite-power.txt`: Cinderlord x8 health and x1.1 damage, Hvitserk x1.25 health, Gloomroot x0.8 health and x0.6 damage, Hrungnir x0.8 health. All 41 elites now satisfy both lone rules, and the party control passes (a party of the recommended size beat all of them in the final checks, including two players in green gear against the Cinderlord).
