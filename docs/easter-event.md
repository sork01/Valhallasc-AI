# Easter season

Owner requirements: compute Gregorian Easter Sunday with Meeus/Jones/Butcher;
start two days earlier, end ten days after the start. Dress Alderhaven,
Skaldholm, Nacrehold and Asterion, add seasonal city errands and one five-player
elite hunt with an exact 5% Easter bunny mount reward. Claiming every distinct
quest awards an achievement and Easter title.

The recorded date interpretation is **E−2 through E+8 inclusive**, expiring at
Stockholm midnight E+9. Add calendar dates before converting each boundary to
UTC, so March/April rollover and Stockholm DST never shorten a festival date.
The reusable registry declares `calendar: gregorianEaster`, `startOffset: -2`,
`endOffsetExclusive: 9`; the server calculates each year. Existing fixed-date
and cross-year seasons retain their rules. Availability comes from snapshots;
the browser clock cannot extend quests, summons or decorations.

Recorded implementation defaults: four annual errands total, one per city;
one shared daily hunt; highest fighter level frozen at summon; independent
personal daily 5% rolls, separate from claims; permanent claimed evidence across
years. These are TODO choices, not new owner answers.

| City | Quest ID | Name | Host | Level | Gold |
| --- | --- | --- | --- | --- | --- |
| Alderhaven | easter_alder | An Egg for Every Hearth | Pip | 1 | 100 |
| Skaldholm | easter_skald | The Spring Bell Parade | Eira | 20 | 500 |
| Nacrehold | easter_nacre | Pearls of a New Spring | Pelar | 40 | 1500 |
| Asterion | easter_aster | A Basket of Starlight | Vela | 60 | 2800 |

Each errand pays levels[level−1]/10 XP once per character/year. All four hosts
offer and receive `easter_hunt`, **The Bloomwarden**, once per Stockholm day,
level 1, 300 gold and level-one quest XP. Hires use the existing price formula.
No collecting grind or additional quest item is introduced.

The Bloomwarden is an original moss-and-blossom guardian with decorated egg
armour, summoned at the **Springtide Egg Basket**, Rimeveil zone 2 (112,100),
beside the existing clearing (103,100). Its dates do not overlap Christmas.
Any current-day accepted quest participant may summon within 2.8 units of the
basket. Exactly five living, online, dismounted, calm party fighters must gather
within 12 units of the centre. Hires count; ambient/gauntlet actors do not.
Freeze participant character IDs and highest fighter level. Outsiders/late
joiners cannot damage, become targets or earn credit.

Living real frozen participants with today's accepted hunt, in the same zone
within 18 units of the centre, receive credit and one independent exact 5% roll
(`0 ≤ roll < 0.05`) per Stockholm day. Dead, distant, disconnected, unaccepted
and hired fighters never roll. The persisted `seasonalRolls[easter_hunt]` ledger
is separate from claims. Abandoning, repeating kills, changing hosts or
reconnecting cannot restore an attempt. A successful roll grants **Springtide
Bunny** directly outside inventory, safe with full bags. Existing ownership
never duplicates or replaces the selected mount. It is a large white rabbit
with pastel-pink ears, a floral saddle and decorated egg basket, travelling at
the existing 160% walking speed.

Wipe/empty clearing resets after eight seconds; a 13-unit leash or 15-minute
encounter limit also retires it without credit. Rejoining the same character
may resume a still-active run. Unclaimed daily progress expires at the next
Stockholm midnight. Festival expiry removes unfinished quests, summon, elite,
city dressing and costumes, including while menus are open. Earned rewards and
claimed history remain through save, reconnect and rebirth.

Claiming all five distinct Easter quests awards **Eggstraordinary Easter**,
**25 points**, unlocking selectable permanent suffix **`<name> the Springbringer`**.
One claimed hunt fills its place in the set; accepted/ready quests never count.
Use existing achievement reconciliation, toast, selection and suffix renderer;
preserve saved names and reservations. All rewards are idempotent.

Owning generator: `scripts/easter_event.py`, after Christmas through
seasonal_cities/sync-world. Native cached canvas eggs, baskets, spring flowers
and pastel ribbons preserve city identity and existing routes/entrances/services.
NPC accessories follow animated head/collar sockets. Original elite and bunny
art are saved through PixelFlow; mount exports include colour/depth, eight
facings, idle/run and all ten class/body rider rigs. Support day/night, reduced
motion, phone controls and English/hand-written Swedish. No new zones, schema
or private-copy ID shift. Owner retains encounter timing and win-rate evaluation.

Calendar reference: [US Naval Observatory observance service](https://aa.usno.navy.mil/data/christian_observances).
Focused checks and requested pictures are recorded in easter-validation.md.
