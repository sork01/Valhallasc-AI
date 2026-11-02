# Seasonal city events

Beta 1.33.0 introduces Halloween in Alderhaven, Skaldholm, Nacrehold and
Asterion, with dressing in the other town camps too. Pumpkins, warm lanterns,
orange/purple bunting, bat bow ties and the four hosts’ witch hats layer onto
existing scenery and NPC artwork. These cosmetic objects have no collision.
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

Every character may complete each festival quest **once each calendar year**.
The four quests use existing talk/visit objectives and normal level, distance,
progress, XP and gold validation:

| City | Quest | Giver | Level | Gold |
| --- | --- | --- | --- | --- |
| Alderhaven | A Light for Every Door | Pip | 1 | 75 |
| Skaldholm | The Kindly Ghost Parade | Eira | 20 | 450 |
| Nacrehold | Lanterns for the Lost | Pelar | 40 | 1,400 |
| Asterion | The Midnight Masquerade | Vela | 60 | 2,600 |

XP follows `levels[level-1] / 10`. No quest items or combat grinds are added.
Two defaulted save maps, `seasonalClaims` and `seasonalStarted`, record the
claim/accept year. Completed rewards and completion history are retained.
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
