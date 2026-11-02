# Sky and ocean crossings

Beta 1.32.4 makes Bifrost Reach's height and the ocean-floor setting of
Rán's Deep and Nacrehold explicit. This is a presentation change; the existing
authoritative walking crossings, collision, input and arrival positions remain
the source of travel state. No world regeneration or server restart is needed.

`client/zonejourney.js` chooses the direction from the source and destination
themes. Entering `sky` climbs above the clouds. Entering `deep` or `nacre`
from outside those themes descends to the ocean floor. Travel between the two
underwater themes continues along the seabed, without replaying a dive.
Returning to land describes the corresponding descent or ascent.

`field.js` draws pale climbing steps or blue descending steps at walking
approaches, with a direction arrow and destination name. On an authoritative
zone change, cloud banks pass downward for a climb; bubbles and surface rings
pass upward during a dive. Effects occupy the edges and a faint wash, leaving
the character and combat visible. Cloud banks behind Bifrost's islands give
the void a visible lower cloud layer throughout the visit.

An accessible, translated arrival message lasts 4.6 seconds. The sky/seabed
label beside the minimap remains until the player leaves that environment.
Reduced motion retains the steps, messages and location label while suppressing
the animated travel overlay and freezing approach bubbles/lower cloud drift.
Joining or reconnecting updates the location label without replaying a journey.
Each subsequent crossing replaces the previous effect; Field start/stop clears it.
No additional images, audio, camera shake, input locks or network messages are used.

Focused validation:

```
bash scripts/test-touch-bounded.sh tests/zone-journey-ui.cjs
MUTATE=1 bash scripts/test-touch-bounded.sh tests/zone-journey-ui.cjs
```

The normal check crosses the real routes 6→7, 7→8, 7→9, 13→8, 13→9 and
8→9. English desktop and Swedish landscape touch checks cover canvas approach
labels, arrival text and viewport fit, persistent location labels, directional
particle motion, reduced motion, effect expiry and reconnect suppression.
Paired game-canvas pixels verify that the render actually paints the effect.
The mutation disables travel drawing and must fail the visible-atmosphere check.
`JOURNEY_CANDIDATE` privately routes the four changed presentation files from
a candidate directory. `JOURNEY_FINAL=1` limits a follow-up to the Swedish touch
viewport when checking final installation and layout changes.

Validation on 2026-10-29: the initial private desktop/Swedish-touch pass completed
47 checks. The final installed Swedish-touch pass completed 19 checks, including
the added game-canvas pixel comparison and persistent-label bounds check.
Disabling travel drawing failed the visible-atmosphere assertion as intended.
Release-note, JavaScript syntax, Swedish catalog and diff checks passed. Public
SHA-256 content matches were verified for index.html, field.js, online.css,
zonejourney.js, sv-data.js and release-notes.txt. Screenshots are in
`test-results/driver-rNKGMa/` and `test-results/driver-Iqv72I/`.

## Bifrost arrival correction (Beta 1.32.5)

The original atlas generator checked collision objects but did not require a
visible sky-floor tile. Bifrost's void rectangles guard island edges rather than
every distant empty-sky cell. Consequently, flood search could route outside the
islands: Wyrdwood arrived at (11.5, 59.5), and Nacrehold at (148.5, 61.5), both
empty sky. The earlier presentation check verified the zone change and effect,
but did not assert visible floor underneath the character.

`scripts/compact_atlas.py` now masks empty sky out of route searches, checks the
floor along endpoint segments including the player's footprint, and requires a
seven-tile lateral passing area beside sky exits. Existing island/bridge layout,
collision geometry, zone IDs and content remain unchanged. Regenerated approaches
stay on floor; the corrected arrivals are (37.5, 78.5) from Wyrdwood and
(107.5, 106.5) from Nacrehold. The same floor checks apply to the other Bifrost
walking routes. `sync-world.cjs` owns the generated map and client output.

Focused Rust regression:
`compact_atlas_bifrost_arrivals_and_approaches_stay_on_visible_floor` checks four
real incoming crossings, continued movement, and samples the complete authored
approaches and player footprint against the sky floor. It passed, and two world
syncs produced byte-identical map/client data. The old two arrivals fail the
same floor condition. Browser check: `tests/bifrost-arrival-ui.cjs`, under the
normal bounded helper, verifies actual Wyrdwood/Nacrehold arrivals, both rendered
and authoritative coordinates, and continued walking on visible floor.

Unlike the presentation-only release, this correction changes embedded map
data and requires a matching server release. Before restarting, back up the
running executable and SQLite, and move any saved Bifrost character on an empty
sky tile to the corrected Wyrdwood landing. No zone/copy IDs shift.

Released on 2026-10-29 with zero humans online. The focused Rust regression,
Clippy with warnings denied, formatting, locale/release guards and nine bounded
browser assertions passed. Running the browser regression against the previous
binary failed at the corrected-arrival assertion as expected. Screenshots:
`test-results/driver-ecMjtY/bifrost-arrival-from-{6,9}.png`.

Backup: `deploy/backups/bifrost-arrival-1.32.5-20261029T185928Z/`, including the
previous executable, online/stopped SQLite copies, previous four client files,
rescued-character receipt and `verification.json`. The one stranded saved
character, `[GM]Sork`, moved from (4.7, 113.8462) to (37.5, 78.5); all other
character state remains intact. Counts stayed at 31 characters / 18 guests.
Public and bridge health, SQLite quick_check, public file hashes, no test flags
and warning journal checks passed. Running/installed/candidate binary SHA-256:
`0684b3b496c0bcdb2d442d6f34cb7daa07e1280ef9eb497ca6eeafa2d454bbcd`.

## Solid staircase artwork (Beta 1.32.6)

The owner found the original seven short strokes looked like loose planks.
`ZoneJourney.approach` now draws eight isometric stone treads with full vertical
risers, filled stepped side walls, masonry joints, a foot landing, highlight
edges and continuous handrails with connected posts. Each rise is 26 virtual
pixels (208 total), replacing the old 50-pixel flight. The flight turns at its
landing where needed to keep its risers facing the fixed camera. Sky stairs use
pale marble and gold rails; ocean stairs use turquoise stone and light rails.
Labels sit above the raised flight, and clouds stay at the upper landing.

This is an artwork change only; the corrected crossing coordinates, visible
floor, collision and authoritative movement remain unchanged. No restart or
world regeneration. Three private in-game previews (Wyrdwood→Bifrost,
Bifrost→Deep and Astralhollow→Nacrehold) rendered without browser errors, and
the before/after contact sheet was inspected after the rail connection fix.
Artifacts and verified public hashes: `test-results/solid-stairs-20261029/`.
Changed JavaScript syntax, Swedish generation, release-note and diff checks pass.

## Wind passages and complete sky collision (Beta 1.32.7)

The owner preferred an updraft or teleport after finding the stair model still
looked like an ascent on the Bifrost side. Both ends of that decorative model
were above local ground, even when its label described descent. Travel now uses
wind: a tall rising column on the lower side and a low, inward-swirling cloud
opening with downward chevrons on Bifrost. Ocean routes use swirling water and
rising currents. The existing authoritative crossings and arrival atmosphere
remain; the decorative raised stair geometry is removed. New passage labels
are translated into Swedish, and reduced motion freezes the swirl animation.

The reported platform escape was a separate collision defect. The atlas
landing overlay removed pieces of the old void rim when it extended the bridge,
but did not rebuild barriers along the new platform edges. Fixing valid arrival
positions alone did not close those exits. `generate_bifrost.void_pieces` now
covers all empty-sky cells, and `compact_atlas.sky_landing` regenerates that
collision from the final sky rows after extending the platform. The floor plan,
portals and safe arrival coordinates stay unchanged.

Collision pieces split at exact tile boundaries. Dividing long runs into equal
fractions and rounding their widths/centres introduced tiny seams; an exhaustive
empty-sky check caught one at (146.5, 14.5). Integer splits remove those gaps.
The focused `compact_atlas_bifrost_platform_edges_and_void_are_solid` regression
checks empty-sky coverage, walking and dashing toward exposed floor edges, and
real held movement at all four sides of the added platform. Existing incoming
crossings remain covered by the earlier focused regression.

`tests/bifrost-wind-ui.cjs` exercises held movement at the four platform edges,
updraft versus downward-opening artwork, reduced motion and the actual crossing
in both directions. It uses `BIFROST_CANDIDATE` for private map/art/HTML routes and
an explicit `VALHALLA_BINARY` for the matching embedded map. The normal bounded
browser helper remains required. Deploy the regenerated world and client with
the matching rebuilt server; inspect saved Bifrost positions before restart.

Released 2026-10-29 with zero humans online. Both focused Bifrost Rust tests,
Clippy all-targets with warnings denied, formatting, Python/JavaScript syntax,
Swedish/release guards and 17 bounded browser assertions pass. The previous
binary fails the browser edge check: eastward movement reaches blank sky at
x=49.02 and beyond; the corrected server stops at x=48.7 for a 0.3-radius player.
Normal screenshots (both directions) are in `test-results/driver-16Erbz/` and
were visually inspected. Final map/client generation is byte-stable.

Backup and release receipts:
`deploy/backups/bifrost-wind-1.32.7-20261029T201834Z/`. Previous executable,
consistent online/stopped SQLite, previous five client files, next executable
and `verification.json` are retained. No saved Bifrost characters needed rescue;
31 characters / 18 guests remained unchanged. Public/bridge health, SQLite
quick_check, no test flags, warning journal and all five public file hashes pass.
Running/installed/candidate binary SHA-256:
`bd2ce8194e6e7a00f361ad5d690d2bc78fa3fbbd395c0078d1b6f82f9e07579c`.

## Forgiving gate approaches (Beta 1.32.8)

The authored portal discs and arrival coordinates remain the source of passive
entry and safe arrival checks. An additional approach within at least 2.8 tiles
can cross when the hero is moving toward the centre and the authoritative
collision map has a clear body-width line to the opening. Walking exits still
require outward movement. The existing cooldown, instance, quest, boss, level,
sealed-template and party admission checks run after this reach check.

Mouse and touch use the same larger projected opening hit area. Selecting it
routes to a clear approach, then through the opening in its outward direction;
this sends ordinary movement actions, with the server choosing the crossing.
Hover shows a pointer cursor, and a steady/pulsing floor outline identifies the
opening. Arrival movement faces away from the return opening, avoiding passive
bounce after the cooldown without enlarging authored arrival discs.

Focused checks: `owner_fixes_wider_gate_approach_keeps_arrivals_and_access_rules`,
the existing compact-atlas arrival/crossing checks, and bounded mouse/short-screen
touch crossings in `tests/owner-fixes-ui.cjs`.
