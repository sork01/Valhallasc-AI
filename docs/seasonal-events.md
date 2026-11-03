# Seasonal city events

Beta 1.34.0 dresses only Alderhaven, Skaldholm, Nacrehold and Asterion,
inside their city bounds. Smaller camps have no seasonal dressing. Pumpkins,
lanterns, bunting, candles, scarecrows, doorway wreaths and elevated cobwebs
are distributed through the four cities. Bat bow ties and the four hosts’
witch hats layer onto existing NPC artwork. These cosmetic objects have no collision.
They are placed away from people, obstacles and gates; walking routes and
service/quest names remain visible. Native Canvas artwork uses the existing
City cache and depth list; NPCs retain their original sprite atlases.

The authoritative real-world calendar is **Europe/Stockholm**. Halloween
starts at local midnight October 26 and ends at local midnight November 10,
so November 9 is included. This calendar is independent of game day/night,
client clocks and browser timezone. The standard-library calendar implements
Stockholm’s CET/CEST offsets and the last-Sunday EU daylight-saving rule.
A reusable registry in `world/seasons.txt` defines event IDs, month/day
boundaries (including intervals spanning New Year) and quest IDs.

Every character may complete each of the four city errands **once each calendar year**.
The four quests use existing talk/visit objectives and normal level, distance,
progress, XP and gold validation:

| City | Quest | Giver | Level | Gold |
| --- | --- | --- | --- | --- |
| Alderhaven | A Light for Every Door | Pip | 1 | 75 |
| Skaldholm | The Kindly Ghost Parade | Eira | 20 | 450 |
| Nacrehold | Lanterns for the Lost | Pelar | 40 | 1,400 |
| Asterion | The Midnight Masquerade | Vela | 60 | 2,600 |

XP follows `levels[level-1] / 10`. These four errands add no quest items or combat grinds.
Two defaulted save maps, `seasonalClaims` and `seasonalStarted`, record the
claim/accept period (year for the errands, YYYYMMDD for the daily hunt). Completed rewards and completion history are retained.
At event end, unfinished quests retire automatically with a system notice;
a previous completed run stays in history. No pending objectives carry into
the next year. Abandoning and retaking during the same event is allowed until
that year’s reward has been claimed. Reloading an expired saved quest applies
the same retirement before entry.

The world checks expiry every second, even while menus are open. Every
accept/claim separately rechecks the actual calendar, so a stale button cannot
claim an expired reward. Snapshot `seasons` and the owning player’s
`seasonalClaims` control client dressing, offers and guidance. The open NPC
conversation refreshes at a boundary. A private-only `season_time` debug
command enables date tests; production GMs cannot override this calendar.

Run `node scripts/sync-world.cjs` (using the local Node path where necessary)
to apply `scripts/seasonal_cities.py` after the final geography overlay and
regenerate client data, then rebuild Rust. Both overlays are idempotent.
There are no new zones or shifted private-copy IDs. Existing character saves
load with empty annual maps; no database backfill is required.

Focused validation: Rust `seasonal` and `compact_atlas` filters;
`tests/cities-seasonal-ui.cjs` under `scripts/test-touch-bounded.sh`, using an
explicit private binary. The latter exercises actual talk/visit progress,
claim duplication, annual reset, expiry/reconnect, rendered cities/NPCs,
Undervault clipping/entry/return, Bifrost bypass/travel and day/night exit
signage at desktop and phone sizes. `MUTATE=clip` must fail the aperture check.

Visibility regressions must be checked against final canvas pixels: Nacrehold’s
water tint originally ran after the new signs and reduced their contrast.
Destination plaques now draw after all terrain/weather filters, before travel
messages and guidance. The browser check measures actual bright glyph pixels
and physical font size in both viewport sizes, rather than merely observing a
`fillText` call. The native stone arch needs a real rise above the projected
wall slope: a shallow screen-space curve reads like a plank in this camera.

## Shared daily hunt (Beta 1.34.0)

The four hosts also offer `halloween_hunt`, one shared daily five-fighter
summon in Gloamfen. Daily eligibility uses the same authoritative Stockholm
calendar; claim and personal mount-roll ledgers are independent and persistent.
The Hollow Rider, ritual lantern, hires and unfinished quest retire at event
end; owned mounts remain. See [halloween-hunt.md](halloween-hunt.md) for the
1% personal reward rule, party scaling and focused validation. No file zones
or private-copy IDs change.

## Christmas and permanent seasonal titles (Beta 1.35.0)

Christmas uses the same registry and Stockholm calendar: December 15–28,
ending December 29 midnight. The four cities receive Christmas trees, lights,
wreaths, garlands, gifts, snowmen and NPC hats/scarves instead of Halloween
art. All seasonal NPCs/offers are filtered by their own event ID; Christmas
must never expose the haunted lantern merely because another event is active.

Four annual city errands plus the shared daily Grinch hunt award the Merry
quest-set achievement/title; Halloween’s five distinct claimed quests award
the Hallowed. Permanent claimed evidence counts across years and reconciles
old seasonal claim ledgers on login. Titles never alter saved character names.
The shared encounter engine preserves Halloween’s average-level/1% rules while
Christmas uses highest-level/5% rules. Full rules, generator and cleanup:
[christmas-event.md](christmas-event.md).

## Computed Easter candidate

Registry `calendar: gregorianEaster` uses Meeus/Jones/Butcher each year, then
`startOffset: -2` and `endOffsetExclusive: 9`. Local calendar dates are shifted
before CET/CEST midnight conversion: E−2 through E+8 inclusive. Existing fixed
and cross-year windows keep their semantics. The four cities receive native
painted eggs, baskets, spring flowers, ribbons and socket-fitted NPC accessories.
Four annual errands and the shared daily Bloomwarden quest use the same saved
claims/attempt/expiry engine. Details: easter-event.md.

## Summer Solstice (private Beta 1.37.0)

`calendar: juneSolstice` computes the June-solstice instant using Meeus and
NASA delta-T, then derives its Stockholm date before local offsets −4/+5
exclusive. Supported years are 2000–2099. Five authored quests and the shared
five-fighter hunt use the existing annual/daily save maps; only four cities
receive Midsummer poles, birch, wildflowers and blue/yellow dressing.
See [summer-solstice-event.md](summer-solstice-event.md) for the exact 5%
Sunwoven Stag rules, independent astronomical references and candidate
integration decision. Other candidate seasons remain separate.
## New Year (Beta 1.36.0)

December 29–January 2 uses the existing cross-year calendar registry. One
shared daily five-fighter Starfire Rocketeer quest, no city errands, a personal
5% Starflight Rocket roll/day, and Ring in the New Year (25 points) on claim.
Worldwide fireworks are dense inside the four actual city bounds and sparse
everywhere else, including instances, with a still reduced-motion display.
See [new-year-event.md](new-year-event.md) and [new-year-validation.md](new-year-validation.md).

## Festival Spirit and guided dances (private Beta 1.38.0)

Owner requirements: flowers in Summer Solstice NPC hair, hearts for Valentine,
decorated eggs for Easter; every season offers two hours of +10% attack and
+50% experience, earned by pressing its centerpiece and dancing two full laps.

Recorded implementation defaults: automatic guided counterclockwise dance,
radius1.8 tiles, ten seconds per lap, plus a short normal-speed approach to
the nearest point of the ring. Each of the four cities has a reachable clear
centerpiece: pole/tree/heart/egg/pumpkin/rocket for Solstice/Christmas/Valentine/
Easter/Halloween/New Year. Every registered future season gets the same flow
with a flower centerpiece unless its generator assigns a specific theme. The
elite-summon landmarks and actions remain distinct. No quest or group required.

The server owns route movement, accumulated angle and completion; no client
coordinates, timer or completed-lap claim is accepted. Manual movement, combat
actions, damage/death, control-impairing status, mounting, travel, zone change,
disconnect or event expiry cancel unfinished dances with no partial credit.
Idle input/Stop preserve the dance. Hires/ambient fighters cannot earn it.
The visible existing body-specific dance choreography follows the guided route.
The path is checked for collision and tiny legal per-tick steps; outside actors
do not block players. Two laps are 4π accumulated angle, not stationary spins,
back-and-forth motion or a timer standing still.

Completion grants one non-stacking Festival Spirit. The saved authoritative
Unix expiry is now+7200 seconds; another completed dance refreshes it to now+7200,
never adds durations or bonuses. No cooldown. Timer runs offline; death,
rebirth and season end retain the earned buff until that expiry. Unfinished
dance progress is transient and never resumes after disconnect. Old saves
default to no buff; no DB migration or backfill.

Attack is the normal calculated attack stat multiplied by1.10 after gear/set
bonuses, used by the existing combat/skill paths; defense and PvP tuning constants
are unchanged. XP adds50% of the base reward alongside rebirth/Hierloom and
Rested bonuses, for monster/party/quest rewards through the existing common XP
path. It does not multiply other XP bonuses or spend the Rested reserve.
UI uses authoritative seconds remaining, a tap/keyboard tooltip, progress and
cancellation notices, with hand-written Swedish and desktop/phone controls.

Integration: this private checkout contains all six seasonal registries,
generator/render/hunt/mount hooks and achievement/title catalogs. Valentine's
guaranteed mount ON CLAIM remains distinct from rare kill rolls. Mailboxes is
not a dependency. No publication, production DB/client/server change, new zones,
copy-ID migration, grinding or timing/balance sweep is part of this task.
