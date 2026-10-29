# Startup loading

Beta 1.32.2 reduces work during the first seconds of play. Monster artwork loads
from the current zone's snapshots instead of starting every monster bank at
login. Ordinary Rimeveil requests four monster atlases and Gloamfen five, rather
than requesting the whole world's 300-plus images. Loaded art is reused when
returning to a zone.

`client/field.js` shares one kind-to-bank map between loading and rendering.
Preserve its first-match precedence for catalog enemies that borrow artwork.
Actors with `state == "waiting"` are dormant and need no art until activated;
other deaths are not used to identify sleepers. The shared Cathedral bank also
contains late dungeon monsters, story foes and raid helpers, so it loads images
individually. A partial bank returns no source for a missing image, preserving
the procedural fallback. Concurrent snapshots share pending requests; failed
banks retry after five seconds. The existing NPC artwork fallbacks remain.

`client/combat-audio.js` primes recordings one at a time, yielding through
`requestIdleCallback` (16 ms timer fallback) before each load and using low fetch
priority. An unavailable recording continues to use synthesis immediately.
Sound choices, recordings and variation are unchanged.

Focused validation: `tests/startup-loading-ui.cjs` through
`bash scripts/test-touch-bounded.sh`, plus `tests/recorded-audio.cjs`. The browser
check uses a private server and database, resumes a character saved in Rimeveil,
checks deferred real monster artwork, Gloamfen travel and portraits, shared-bank
incremental loading, art reuse, and all 68 recorded sound decodes. It keeps stub
player sprites so the test measures the changed monster/audio loading paths.

All 13 focused browser checks pass, including four initial Rimeveil monster
atlases, five on entering Gloamfen, two separately introduced shared-bank images,
68 idle yields and 68 sound decodes with at most one decode in flight. The
`MUTATE=art` check restores eager Gloamfen loading and fails the deferred-art
assertion. The recorded-audio unit checks and release-note gate pass.
