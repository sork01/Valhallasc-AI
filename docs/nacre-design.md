# Nacrehold as a shaped, authored city (zone shapes pilot, 2026-11-07)

Owner request: "for pilot. reshape nacrehold. and remake the zone and quests to fit the new shape. no fillers. keep the portals/updrafts since this place should be inaccessible without them. the only place it should have a seamless against is rans deep." Later: "bifrost should not have a seam". Answers: keep the 120 homes and six districts; the waterfront along the Deep is open the whole way; the four other gates stand on the rim facing their neighbour. Pilot only (branch `feat/zone-shapes-nacre`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-nacre-work`, cargo target `zone-nacre-target`, wrapper `zone-nacre-cargo.sh`). The ninth pilot zone: 0, 1, 2, 3, 6, 7, 8, 9, 16.

## The shape
At k = 1.0 the outline is a rounded shield: grid 248, bbox 244 x 214, 38,365 tiles (the old city: 31,000 walkable tiles in a 192 square). The Deep lies along the whole straight north edge (~197 tiles), Bifrost down the west side, Astralhollow at the short north-east corner, the Orrery down the long east diagonal, the Crags round the south tip. The old 176-tile square cannot sit inside it (the fit check said 1.35), so the city is rebuilt.

## Pipeline
`world/zone-shapes.txt`: zone 9 in `zones`, `designOnly: [8, 9]` (outline floor, no filler, the design places its own gates), `rebuild: [9]` (new: the old layout is NOT moved, the view is emptied and `nacre_design.py` rebuilds from `world/zone-shapes/preshape-09.txt`), `seamWith: {8: [9], 9: [8]}`. `zone_scale` returns k for design-only zones (the area floor and `city_fits` had bumped Nacrehold to 1.265, which silently prevents a seam). Bifrost stays `gateOnly`; the Crags, Astralhollow and the Orrery are kept off by `seamWith`. `apply` runs `deep_design.late_seam` after the Deep's design (the approved Deep is not reshuffled: it removes the rim reef within 7 tiles of the border run and the Tideway's gate posts and exit route, and rebuilds the void so the floor reaches the line and the margin past it), then `nacre_design.design`.

## The city (`scripts/nacre_design.py`, `python3 scripts/nacre_design.py plan OUT.png`)
- y 20-44 the **Tideway Promenade**: open reef garden and roads, nothing a seam cannot draw. Buildings, people and festival decor keep 22 tiles from the Deep border (a seam draws ground, scenery and enemies of the other side, not NPCs or decor); coral and kelp stay 14 off.
- y 46-86 the civic band: Lantern Gardens, the Memorial, the Drowned Cathedral with its court and the three wing doors, the Palace of the Gentle Tide, the Pearl Archive.
- The **Grand Axis** (x 128) runs from the cathedral through the fountain plaza (128, 108) to the Crags gate on the south tip; five avenues and seven streets on a 24-tile lattice; 120 homes on the lots nearest the plaza (labels `Rosecoral n` ... as before), six districts (two above the plaza, two beside, two below); three reef parks (West, South, Road Reef).
- Gates on the rim, arrival six tiles in: Astralhollow road (north-east), Orrery avenue (east), Crags gate (south), Bifrost stair (west). The Cathedral's three doors stand in the court. The Tideway is the seam.
- Sanctuary: `city` (the band with the plaza) plus 19 `camps`, 10-row bands of floor, all named Nacrehold (no `regions`, as before); covers over 93 % of the floor and everything a player stands on.
- People: every old id kept and moved; the 18 swimmers walk lattice blocks; **Harbour-Warden Selke Tideline** (promenade) and **Gatekeeper Orsa Stillfin** (gate square) are new. Mailbox and travel master at the Crags gate square. The Spark Travel links to the neighbours are re-synced (Nacrehold had no people while the zones were shaped).
- Quests: all 28 old ids kept; **4 new**: `nacre_tideway`, `nacre_five_ways`, `nacre_rim_gardens`, `nacre_grand_axis` (rewards in `quest_gear_rewards.py`). New places: `nacre_tideway`, `nacre_plaza`, four `nacre_way_*`, three `nacre_reef_*`. Swedish written by hand.
- Seasonal decor (five seasons) is regenerated for the new streets inside the decor rules of the old generators (they run on the square, before shaping).
- Every crossing that arrives here follows the new frame: Crags `path_1_9`, Bifrost `path_7_9`, Astralhollow, Orrery, the three wing returns and exits. `placeAtSpawn`: saved characters in zone 9 move to the spawn (128, 217).

## Client
Black water beyond the outline for the `nacre` theme (as the Deep), no border blend, deep-blue minimap, and `groundOf`/`deepLook` so the seam blend uses the real Deep and Nacrehold floor colours.

## Checks
- `python3 scripts/zone_shapes.py unshape && python3 scripts/zone_shapes.py apply`, or `node scripts/sync-world.cjs` twice (identical `map.txt`, `client/world.js`, `mailboxes.txt`).
- Non-regression diff against the previous map: only zones 1, 7 (arrival coordinates), 8 (seam side), 9, 10-12 and 13, 15 (arrivals) differ.
- Rust: `cargo test nacre_` (10), `deep_tests` (22), `zone_shape` (59, including `the_deep_and_nacrehold_share_a_seam`, `nacrehold_is_seamless_against_the_deep_only`).
- Browser: `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/nacre-design-ui.cjs` (`KS='[7]'` picks seam points; the whole run exceeds the 10 minute cap with all three; `MUTATE=1` must fail the black-water check, and does).

## Open
- **The same world point drawn from the two frames still differs** (mean ~30, 17-28 % of pixels; the test reports it, `STRICT=1` asserts it). Crossings themselves are seamless both ways, no banner, minimap scale kept, the other side's scenery is ghosted.
- Seam point 11 was not run in the last session; pilot deploy (backup, `zone_shapes_migrate.py --zones 9`, binary swap, restart) not done; wiki, TODO and the pilot doc's index line not updated; nothing committed.
- Older suites that teleport into Nacrehold at the old coordinates are stale (like the other pilot zones).
