# Christmas — Beta 1.35.0

Christmas is active every year from **December 15 through December 28** on the
server's Europe/Stockholm calendar. It begins at December 15 midnight and ends
at December 29 midnight. Game time, browser timezone and client clocks cannot
change eligibility. Only Alderhaven, Skaldholm, Nacrehold and Asterion receive
city scenery/NPC costumes, inside their city bounds. Rimeveil's great Christmas
tree is the specifically authored encounter landmark outside that scope.

Implementation defaults were stated to the owner while optional clarification
was requested: four city errands total, one per city, annual; independent daily
personal mount rolls; seasonal achievements accept claimed quests across years.
These follow the existing Halloween conventions, not an additional owner reply.
The Grinch's highest-level scaling and 5% chance are explicit owner requirements.

| City | Quest | Giver | Level | Gold |
| --- | --- | --- | --- | --- |
| Alderhaven | A Gift for Every Hearth | Pip | 1 | 100 |
| Skaldholm | The Winter Bell Choir | Eira | 20 | 500 |
| Nacrehold | Pearls on the Christmas Tree | Pelar | 40 | 1,500 |
| Asterion | The Star Above Every Door | Vela | 60 | 2,800 |

Each errand pays XP from `levels[level-1]/10`, once per character/year. The same
four hosts offer/receive `christmas_hunt`, a single shared daily quest, worth
300 gold and level-one quest XP. The quest must be claimed before Stockholm
midnight; unfinished previous-day progress retires when the day changes.

The Grinch is summoned by pressing the great Christmas tree at **(112,100)**
in **Rimeveil Glacier, zone 2**, beside the clear circle centred **(103,100)**.
Any party member with the accepted current-day quest may summon. Exactly five
living fighters, including hires, must gather nearby, dismounted and out of
combat. The summoner interacts within 2.8 units; all five gather within 12 units
of the centre. The level is the **highest level of the five fighters**, frozen
with participant IDs at summon. Late joiners cannot damage or receive credit;
the Grinch targets/damages only those participants. Existing Halloween continues
to use its rounded-up average and leader-only lantern interaction.

Each living real participant with the accepted daily quest within 18 units of
the clearing earns kill credit and **one independent 5% Red-nosed Reindeer roll
per Stockholm day**. Hires do not roll. The daily roll ledger and city claim
ledger are separate; switching hosts, repeating kills, abandoning or reconnecting
cannot restore an attempt. Ownership is granted directly, so full bags cannot
lose the reward. Already owned mounts do not duplicate or replace the selected
mount. All mounts travel at **160% of normal walking speed**.

A wipe or empty clearing resets after eight seconds; pulling the elite beyond
13 units or reaching the 15-minute encounter limit also retires it. December 29
removes the Grinch, tree, city dressing/costumes and unfinished quests, while
permanent mounts, achievements, claimed history and titles remain. The event
returns automatically next December. No new zones/private-copy IDs are inserted.

Claiming all five distinct Christmas quests awards **Merry in Every City**,
25 achievement points and **`<Name> the Merry`**. One claimed daily hunt is enough
for that quest's place in the set. Halloween's equivalent grants **the Hallowed**.
Both reuse permanent quest evidence and suffix rendering; saved names and unique
name reservations stay unchanged. Existing seasonal claims reconcile on login.

`christmas_cities.py` extends the final seasonal generator; sync-world remains
idempotent. Shared authoritative encounters live in `world/seasonal_hunt.rs`.
The original Grinch and reindeer use saved PixelFlow sources and the existing
cel/depth pipeline. City scenery is native cached Canvas artwork; no collision
props are added to streets. Larger trees fade when they cover a fighter.
Encounter health/enrage remain provisional for owner-run timing/win-rate review;
focused tests use direct fixtures and controlled RNG, with no grinding or sweeps.

Focused checks, sprite source IDs, requested pictures and deployment evidence:
[christmas-validation.md](christmas-validation.md).
