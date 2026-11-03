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
