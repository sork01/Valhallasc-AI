# New Year

New Year runs every year from **December 29 through January 2 inclusive**,
on the authoritative **Europe/Stockholm** calendar. It starts at December 29
midnight and expires at January 3 midnight. The season year is the December
start year; the daily allowance uses the actual local YYYYMMDD on both sides
of January 1. Browser clocks and game day/night never change eligibility.

The owner requested worldwide fireworks, abundant in Alderhaven, Skaldholm,
Nacrehold and Asterion and sparse elsewhere, exactly one five-player elite
quest, a 5% rocket mount chance, and a New Year achievement.

Implementation defaults reuse Christmas: one shared daily quest offered and
claimable at Pip, Eira, Pelar and Vela; one independent personal 5% mount roll
per Stockholm day; highest-of-five level frozen at summon, including hires.
These are implementation decisions, not additional owner answers. The mount
is **Starflight Rocket**, the elite **The Starfire Rocketeer**, and the
achievement **Ring in the New Year**, worth **25 points**, without a title.
No city errands or additional New Year quests are added.

## Single daily hunt

`newyear_hunt` is available from all four festival hosts at level 1. It pays
300 gold and levels[0]/10 XP on claim. City switching, abandoning, repeat kills
and reconnecting cannot bypass either the daily claim or separate roll ledger.
Unclaimed previous-day progress retires at Stockholm midnight. Completed
history remains permanent across years.

The **Festival Launchpad** at **(112,100), Rimeveil Glacier (zone 2)** replaces
the retired Christmas tree during New Year. It uses the existing reachable
clearing centred **(103,100)**; no normal monsters, routes, city services or
portals move, no new zones/copy IDs are added. Any real party member holding
the current daily quest may interact within 2.8 units. Exactly five living,
dismounted, out-of-combat fighters must gather within 12 units of the centre.
Hires count; ambient adventurers and gauntlet actors do not. Membership and
the highest of all five levels freeze at summon. Outsiders cannot damage the
elite or receive credit, and the elite can target/damage only participants.
The shared seasonal encounter slot prevents duplicate summons.

Living real participants within 18 units of the centre, with the accepted
current-day quest, receive credit and one independent **5%** roll: uniform
server random value in [0, 0.05) wins; 0.05 and above lose. Hires never roll.
The server grants mount ownership directly, even with full bags. Duplicates
never add another mount or change the current selection. Every mount travels
at **160% of walking speed**. The rocket hovers visually; it follows ordinary
server movement/collision and cannot fly over obstacles.

An empty/wiped/disconnected clearing resets after eight seconds without any
living participant nearby. Pulling beyond 13 units or reaching 15 minutes
also retires the elite; a reset without a kill spends no roll. January 3
retires summons, elite, fireworks and unfinished quests, keeping earned mounts,
achievement points and claimed history. Rejoining/restarting restores ledgers.
Encounter timing and win rates remain for the owner; no balance sweeps.

## Achievement

Claiming the single hunt once awards **Ring in the New Year (25 points)**,
independently of the rocket result. Accepted or ready objectives do not count.
Use the existing permanent claimed quest evidence and positive seasonal claim
ledger reconciliation on login, so prior-year claims qualify and repeats
never give more points. Existing achievement listing, celebration and English/
Swedish presentation apply. Rewards survive expiry, reconnect and rebirth.

## Fireworks and artwork

Fireworks run throughout every zone, including dungeons/private copies. The
actual four city bounds determine dense displays; outside those bounds the
same zone uses sparse displays. Bursts stay in the upper viewport, behind
combat labels and HUD, without sounds, full-screen flashes or camera shake.
The renderer has a fixed burst/ray budget, no accumulating particles, and
reduced-motion shows a still, subdued star display. Low graphics reduces rays
and trails. Event availability always comes from the server snapshot.

Original Rocketeer five-clip and eight-direction rocket idle/run sprites are
saved and exported through PixelFlow; IDs remain in assets/newyear.txt and
assets/mounts_sprites.txt. The mount uses the existing depth compositor for all
ten class/body rigs. City architecture and service/quest markers stay intact.

See seasonal-events.md, christmas-event.md, halloween-hunt.md and achievements.md
for shared infrastructure. Focused evidence: new-year-validation.md.
