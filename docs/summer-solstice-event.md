# Summer Solstice

The annual **Summer Solstice** season celebrates Swedish Midsummer. Let S be the
Europe/Stockholm calendar date containing the astronomical northern June solstice.
The event starts at local midnight S−4 and includes S+4, expiring at S+5 midnight:
nine local calendar dates. This is the recorded TODO interpretation, independent
of the Friday/Saturday Swedish Midsummer holiday. Server snapshots own availability.

Calendar: Meeus, Astronomical Algorithms, second edition, chapter 27 (June
polynomial and all 24 periodic corrections), TT converted to UT with the
NASA/Espenak–Meeus delta-T polynomials. Supported years **2000–2099**; outside
that range this computed event is unavailable, without affecting other seasons.
Only the Stockholm date is used. Independent US Naval Observatory UTC samples,
including 2012 and 2016 when UTC/Stockholm dates differ, are saved in
`solstice-calendar-reference.txt`; tests require time agreement within three
minutes and exact Stockholm dates. Future delta-T and time-zone legislation
require maintenance before extending the range.

Sources: [USNO seasons](https://aa.usno.navy.mil/data/Earth_Seasons),
[NASA delta-T polynomials](https://eclipse.gsfc.nasa.gov/SEhelp/deltatpoly2004.html).

Recorded defaults follow the other seasons: four annual errands total, one per
city, one shared daily five-fighter hunt, highest fighter level frozen, one
independent personal 5% mount roll per Stockholm day. No new achievement/title
was requested or added. Quest IDs and hosts:

| City | Quest / ID | Host ID | Level | Gold |
| --- | --- | --- | --- | --- |
| Alderhaven | Flowers for Every Door / solstice_alder | baker (Pip) | 1 | 100 |
| Skaldholm | Raise the Midsummer Pole / solstice_skald | city_bard (Eira) | 20 | 500 |
| Nacrehold | Wreaths upon the Water / solstice_nacre | nacre_gardener (Pelar) | 40 | 1500 |
| Asterion | The Sunlit Garland / solstice_aster | asterion_singer (Vela) | 60 | 2800 |

All four hosts offer/claim **The Birchcrown Guardian**, `solstice_hunt`, daily,
level 1, 300 gold. Errands use ordinary talk/visit objectives; all XP equals
levels[level−1]/10. No collecting grind. Annual allowances are per character/year;
the shared daily allowance is per character/Stockholm date.

Summon at the **Sunwoven Midsummer Pole**, `solstice_pole`, Rimeveil zone 2,
(112,100), beside the existing clearing centre (103,100). Non-overlapping
seasons share that already-clear site, preserving all geography/ordinary spawns.
The original birch-bark guardian has leafy wreath shoulders, a sun crest and
a flower staff. Any party member with today's accepted quest may summon within
2.8 units. Exactly five living, online, dismounted, out-of-combat party fighters
within 12 units of centre are required. Hires count; ambient/gauntlet actors
do not. Highest fighter level and character IDs freeze at summon. Outsiders
cannot damage, become targets or earn credit.

Living, connected, real frozen participants with today's accepted quest in the
same zone within 18 units receive credit and an independent exact **5%** roll
(`0 <= roll < 0.05`). Hires never roll. `seasonalRolls[solstice_hunt]` persists
separately from claims; host switching, abandonment, reconnect and repeated
kills cannot restore an attempt. Success grants **Sunwoven Stag**, mount ID
`sunwoven`, directly as permanent ownership outside inventory, safe with full
bags. A golden-white stag wears wildflowers and blue/yellow tack. Duplicate
ownership never duplicates or changes the selected mount. Eight directions,
idle/run and depth composition fit all ten class/body rigs; speed remains 160%.

A wipe/empty clearing resets after eight seconds; a 13-unit leash or 15-minute
limit also retires the encounter without rewards. The same character may
reconnect to a still-active run. Daily midnight removes unfinished previous-day
progress. Event expiry removes unfinished quests, summons, encounters, city
dressing and costumes while keeping rewards, ledgers and claimed history
through save, reconnect and rebirth. Menus cannot delay expiry.

City dressing stays within Alderhaven/Skaldholm/Nacrehold/Asterion bounds.
Leafy poles have crossbars and two wreath rings, with clear dancing space;
birch branches, wildflowers, crowns, garlands, blue/yellow ribbons and summer
tables retain local architecture and readable routes/service names. Native
Canvas scenery has no collision; NPC flowers use animated head/collar sockets.
Original guardian/mount art is saved/exported through PixelFlow. English and
hand-written Swedish, day/night, reduced motion and phone are supported.

Integration decision: isolated `feat/summer-solstice` starts from the verified
Easter candidate 94a9fc6, whose computed-date calendar and shared hunt are the
required prerequisites. New Year e6a4635 and Valentine 948a155 are separate
candidates, not dependencies: do not merge or deploy them as part of this task.
Their fixed/cross-year rules remain supported by calendar tests. On combination,
union registry/hunt specs, snapshot/renderer hooks, mount registries and
seasonal generator calls; suppress ALL dormant shared-clearing kinds before
Christmas validates the clearing, then reapply each event. Keep Valentine's
guaranteed ON-CLAIM reward distinct from 5% personal kill rolls. Preserve all
achievement/title catalogs. Mailboxes b6f81e4 is unrelated and remains separate.
Summer Solstice uses **Beta 1.37.0** after the 1.36.0 Easter base; reconcile
versions on a future release combination. No new zones/schema/copy-ID migration,
no publication or live service changes. Owner retains timing/win-rate testing.
