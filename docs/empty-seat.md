# The Empty Seat

A 28-chapter, one-time story campaign from level 2 to 99. It follows the approved
Eldmarr history in `molten-raid.md`: the first forge kept the roots alive, the gods
promised its keeper a seat, and nine of his own captains chained him in exchange
for places in their hall. The campaign gradually reveals that history, then
shows why his plan to melt the roots must be stopped despite the betrayal.

Begin with **Bram Emberforge in Alderhaven**, level 2, **Ash in the Bread**. Each
chapter names the next giver, region and minimum level in its journal entry.
Existing characters may start at the beginning. Prerequisites are claims, so
existing raid clears do not silently complete the story. Normal progression,
Ember Key requirements and the raid's ten-fighter rules remain in force.

| Chapter | Level | Region | Quest | Play |
|---|---:|---|---|---|
| 1 | 2 | Greenmeadow | Ash in the Bread | Listen to the ash |
| 2 | 7 | Emberfall Crags | The Cinder That Followed You | Summon a homeless cinder |
| 3 | 12 | Rimeveil | A Warmth Older Than Spring | Recover a missing verse |
| 4 | 17 | Gloamfen | The Name in the Drowned Ledger | Defeat the Oath-Eater |
| 5 | 20 | Skaldholm | The Tenth Place Setting | Hear a suppressed toast |
| 6 | 25 | Wyrdwood | Keep One Root Alive | Defend a root against sootlings |
| 7 | 32 | Bifrost Reach | An Invitation With No Door | Ring three oath bells together |
| 8 | 37 | Rán's Deep | The First Shadow | Fight the Shade of Eldmarr |
| 9 | 40 | Nacrehold | What the Archive Was Paid to Forget | Restore an erased inscription |
| 10 | 43 | Astralhollow | A Constellation With One Star Missing | See the captains become Wardens |
| 11 | 48 | Prismwaste | Break the Beautiful Lie | Fight the Gilded Witness |
| 12 | 53 | Orrery | The Clock That Counts Downward | Discover the failing chains |
| 13 | 58 | Moonspore | Borrow a Dream That Is Not Yours | Prepare to enter the lost night |
| 14 | 60 | Asterion | Before the Nine Chains | Three ordered, playable memories |
| 15 | 63 | Stormglass | The Sea Cannot Swallow This Fire | Hold a cooling circle |
| 16 | 68 | Sunward | The Harvest of Tomorrow | Receive Eldmarr's offer |
| 17 | 73 | Ribbonwild | A Mask for the Man He Was | Fight the Uninvited Guest |
| 18 | 78 | Tanglecrown | The Root That Refused the Order | Defend a disobedient root |
| 19 | 80 | Veyrroot Canopy | Count the Windows, Not the Thrones | Hear the homes that will fall |
| 20 | 80 | Veyrroot Heartwood | A Third Answer | Find a way beyond imprisonment or revenge |
| 21 | 83 | Lapis Erg | The Route Beneath Every Map | Tune three survey bells |
| 22 | 88 | Frostwake | An Apology Made of Ice | Break the Penitent Chain |
| 23 | 93 | Cairnspine | Teach the Mountain His Name | Ring the true name into the stone |
| 24 | 97 | Yearwheel | One Year the Fire Cannot Have | Gather four seasonal promises |
| 25 | 99 | Emberwake | The Guest at the Last Door | Fight the Shade of the Unbound King |
| 26 | 99 | Emberwake | A Place for the Living | Refuse Eldmarr's bargain |
| 27 | 99 | Chained Forge / Emberwake giver | The Table He Was Promised | Defeat the actual Eldmarr |
| 28 | 99 | Greenmeadow | Leave One Chair Empty | Speak to Bram; witness the memorial |

## Rewards

Owner instruction: green gear for campaign quests, blue every fifth quest,
purple on the last quest before the raid. Chapters **5, 10, 15, 20, 25** offer
blue; chapter **26** offers purple; the others offer green. Every chapter offers
two existing pieces for each of the five classes, rotating slots. The selected
tier is the highest catalog tier the chapter's level can use. The ordinary
class-choice claim path rejects other classes, full bags and duplicate claims.
XP follows the existing level-table tenth; gold is 12 times the chapter level.
There are no new stat tables or drop rates.

## Mechanics and persistence

- `scripts/empty_seat.py` is the additive/idempotent map, scene, enemy, reward and
  Swedish text overlay, reapplied last by `scripts/sync-world.cjs`. Rebuild the
  server after syncing. No zones are inserted and no saved zone IDs migrate.
- **Memory** objectives require 14 uninterrupted seconds in a marked circle;
  the three Asterion flashback scenes require 18 seconds each. Movement, damage,
  combat, stun, death, mounting, travel or departure interrupts attention.
  Only the first unfinished objective can advance. Completed memories persist
  in the existing quest ledger; partial listening is transient. Asterion shows
  the First Hearth, Promised Table and Closing Chain in that order, with
  spectral Eldmarr, roots, ten cups/an empty chair and nine chains.
- **Echo** objectives wake dedicated sleeping enemy slots when an eligible
  living hero enters their circle. One shared enemy per site; no duplicate
  spawns per player. Positive contributors (including damage credited through
  their hires) with the accepted current objective, alive in the same zone
  within 60 units of the death, get personal credit. Observers, dead heroes
  and unrelated quests do not. Abandoned echoes sleep after 12 seconds without
  a nearby eligible hero and can be called again. A restart also rearms them.
- **Hold** objectives use the existing twenty-second ward rules and two
  sleeping attackers. Leaving pauses the hold; falling resets it. **Chime**
  puzzles use three personal bells, each sounding for thirty seconds.
- All ten summoned enemy kinds borrow editable Forge art through `artFrom`.
  Combat sprites are smaller, translucent and cool-tinted; the two Eldmarr
  shades use his atlas. They grant no XP, gold, gear, materials or ordinary
  kill credit. Their quest turn-ins supply rewards. Health/damage are authored
  initial solo settings, not measured encounter-balance results.
- Chapter 27 uses the existing authoritative `cf_eldmarr` kill-credit path,
  including all three private raid copies, ordinary eligibility and the
  existing raid rewards. A shade cannot satisfy it. The campaign adds no raid
  admission requirement. The player still needs the Ember Key.
- `client/emptyseat.js` draws quest rings and readable captions without taking
  input or pausing play. The map and journal resolve the two new objective
  types to real places. Active and completed story entries expand to show the recovered
  text; each chapter also names the next giver. All new narrative/UI text has authored Swedish;
  release notes remain English-only.

## Focused validation

`python3 scripts/empty_seat.py --check`, `cargo test empty_seat_`, the bounded `tests/empty-seat-ui.cjs`, the release-note
check, generator byte stability, Swedish catalog check, Clippy, formatting and
changed-source syntax. No encounter-timing sweep or unrelated full suite.

Nine focused server checks pass, including live kill credit in all three raid
copies, ordered/interrupted memories, ward waves, bell completion, retry cleanup
and class/full-bag/duplicate reward refusal. The bounded staged-client browser
pass has 17 checks with real sprites; it also checks caption alignment, a
15-pixel minimum reading size, the suppressed arrival banner and both reward
choices. Reviewed screenshots: private run `driver-rMPaBo`. Clippy with warnings
denied, formatting, source syntax, Swedish text coverage, release notes, art
aliases, all 38 reachable sites and generator byte stability pass. Bell routes
take at most six seconds at walking speed, within their thirty-second timer.

The encounter strengths are initial authored values for owner evaluation. No
raid balance, existing encounter tuning or PvP numbers were changed.
