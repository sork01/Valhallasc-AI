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
