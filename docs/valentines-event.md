# Valentine's season

Owner requirements: February 10–18 inclusive, Europe/Stockholm; dress Alderhaven,
Skaldholm, Nacrehold and Asterion; seasonal city errands and one five-player elite
quest with a guaranteed Valentine's mount. Claiming all distinct quests grants an
achievement and permanent selectable prefix `Lovefool <name>` (one space), without
changing the saved name or its reservation.

Implementation defaults: Roseheart Unicorn (pearl-pink coat, rose-red mane/tail,
golden horn, heart tack); Lovefool achievement, 25 points. Four annual city errands
and one shared daily hunt follow Christmas. Permanent claimed evidence across
years counts; one claimed hunt satisfies its place in the set. These are recorded
TODO defaults, not additional owner answers.

| City | Quest ID | Name | Host | Level | Gold |
| --- | --- | --- | --- | --- | --- |
| Alderhaven | valentine_alder | A Heart at Every Hearth | Pip | 1 | 100 |
| Skaldholm | valentine_skald | A Ballad for Brave Hearts | Eira | 20 | 500 |
| Nacrehold | valentine_nacre | Roses for the Remembered | Pelar | 40 | 1500 |
| Asterion | valentine_aster | Written in the Stars | Vela | 60 | 2800 |

Each errand pays levels[level-1]/10 XP, once per character/year. All four hosts
accept/claim `valentine_hunt` (The Briarheart), level 1, 300 gold and level-one XP,
once per Stockholm day. Hires are offered at those hosts under existing prices.
The annual errands plus this claimed daily are the exact five achievement members.
Accepted and ready quests do not count. Awards/points/selection are idempotent.

The Briarheart is an original rose-armoured thorn guardian summoned at the
Roseheart Shrine, Rimeveil zone 2 (112,100), beside the existing seasonal clearing
(103,100). Its calendar does not overlap Christmas. Any accepted-current-day quest
party member may summon within 2.8 units of the shrine. Exactly five living,
online, dismounted, out-of-combat party fighters must gather within 12 units of
the centre; hires count, ambient actors and gauntlet opponents do not. Freeze
participant character IDs and the highest fighter level on summon. Outsiders and
late party members cannot damage, become targets or receive credit.

A living real frozen participant with today's accepted hunt in the same zone and
within 18 units of the centre earns kill credit. Dead, distant, disconnected,
hired and ambient fighters receive no reward. Rejoining the same character can
resume participation while the run remains active. No random mount roll is made:
claiming the credited quest at any city host grants Roseheart Unicorn directly,
outside inventory. Full bags are safe, ownership never duplicates and the current
selected mount is preserved. Abandoning/repeating kills/changing hosts/reconnecting
cannot bypass the persisted daily claim ledger. An unclaimed hunt expires at the
next Stockholm midnight and may be accepted again for that new day.

Wipe/empty clearing resets after eight seconds, pulling beyond 13 units or the
15-minute encounter cap also retires the elite. A reset grants no quest credit.
February 19 midnight retires decorations, NPC costumes, shrine, elite and all
unfinished seasonal quests. Recheck against the server clock, including open menus.
Earned mounts, quest evidence, achievement points and selected titles survive
expiry, save/reconnect and rebirth. Mount speed is the existing 160% of walking.
No zone IDs or schema migration; no original-project changes.

Generator: scripts/valentines_event.py, after Christmas via seasonal_cities.py /
sync-world. City props stay within existing bounds, reuse safe facade/perimeter
placements, leave entrances/routes/services intact, and use native cached canvas
hearts/roses/ribbons/pink lights. NPC accessories use actual animated head/collar
sockets. Elite and eight-direction idle/run unicorn use saved PixelFlow sources
and depth exports for all ten rider rigs. Static artwork supports reduced motion.
English/hand-written Swedish presentation uses authoritative availability.
Focused validation is recorded in valentines-validation.md. Encounter timing and
win rates remain for the owner; no grinding, full suites or balance sweeps.
