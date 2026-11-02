# The Hollow Rider

Five living fighters summon the Halloween elite in a dedicated ritual clearing
in Gloamfen. Hirelings count; ambient adventurers do not. The summoner must lead
a party (or lead their hired group) and hold the shared city daily quest. All
five must be nearby, out of combat, unmounted, and able to participate. One
encounter occupies the clearing at a time. Level is ceil(sum(levels)/5), frozen
at summon along with participant IDs. A late join cannot damage or receive
credit from that encounter; the Rider targets and damages its participants.
The encounter retires after a full wipe, everyone leaving, or a fixed encounter
expiry. Re-summoning uses a fresh group and health pool. No ordinary enemy
respawns or loot pools are used for this event.

Owner decisions, 2026-11-02:

- Each eligible real player has an independent **1%** mount roll, once per
  Stockholm calendar day. The roll is consumed on that player's first credited
  Rider kill that day; repeating, relogging, abandoning, or changing city cannot
  restore it. Hirelings have no roll. Ownership is awarded directly so full
  bags cannot lose the rare mount. Already owned mounts are never duplicated.
- Scale to the average party level rounded up. All five participants, including
  hires, count in the average. Scaling stays fixed for that summon.
- Hires count toward the group, following the existing five-fighter model.

Alderhaven, Skaldholm, Nacrehold and Asterion offer the same quest ID,
`halloween_hunt`, through their existing festival hosts. Any of those four hosts
can accept or receive it. The quest requires one credited Rider kill; only a
living eligible participant in the clearing can receive credit and a mount
roll. Quest credit and the roll are persisted at the kill through the normal
character-save path. The quest can be claimed once per day for a small fixed reward;
its repeat/claim ledger is independent of the mount-roll ledger. A new local
calendar day retires pending previous-day progress and allows a new quest.
Existing annual city errands keep their annual cadence.

The event inherits the authoritative Europe/Stockholm October 26–November 9
inclusive schedule. At midnight November 10 the Rider despawns, summoning and
acceptance/claims stop, unfinished seasonal quests retire, and city props/NPC
costumes disappear in the next snapshot. Owned mounts and completion history
remain permanently. The next October 26 reopens the event automatically.

The Nightmare Steed uses the same 2× travel speed and dismount/collision rules
as existing mounts. Original dark horse geometry, burning mane/tail, glowing
hooves and gothic tack are saved through PixelFlow with depth atlases; the
headless revenant knight and jack-o'-lantern are a separate elite atlas.

No new file zone is inserted. The ritual is authored by the final seasonal
world overlay so ordinary generators and sync-world remain deterministic.
Encounter timing and win-rate acceptance remain with the owner; focused tests
use direct fixtures and controlled RNG, not grinding or balance sweeps.

Implementation bounds: the leader interacts within 2.8 units of the lantern;
all five fighters gather within 12 units of the circle centre. The frozen
participants receive kill credit only while living in Gloamfen within 18 units.
An empty/wiped clearing resets after eight seconds; the encounter also retires
after 15 minutes or if pulled more than 13 units from its centre. Ordinary
players outside the frozen group cannot hurt it, and it ignores them for both
targeting and its telegraphed ground-pound. The existing elite enrage policy is
used provisionally; timing remains owner-evaluated.

Health follows the attack ratio of a reference Warrior at the summoned level;
damage follows that reference's health ratio. Both start from the Rider's
`elite-power.txt`-controlled base, keeping level scaling aligned with the existing
player curves without changing player/PvP balance. The daily reward grants
mount ownership directly and keeps the existing selection if another mount was
already owned. No ordinary XP/material/gear loot is farmed from repeat summons.
