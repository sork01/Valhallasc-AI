# The Prismwaste as a shaped, authored zone (zone shapes pilot, 2026-11-08)

Owner request: "for pilot. reshape prism waste and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against **Astralhollow and the Obsidian Orrery**, keep the Mirror Queen and the Sunshard and add one new elite with no quest, three new outposts. Pilot only (branch `feat/zone-shapes-prism`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-prism-work`, cargo target `zone-prism-target`, wrapper `zone-prism-cargo.sh`). The twelfth pilot zone: 0, 1, 2, 3, 6, 7, 8, 9, 13, 14, 15, 16.

## The shape

At k = 1.0 the atlas outline is a tall rose-coloured shield: grid 288, bbox 282 x 270, 49,206 land tiles against the old 128 square's 16,000. Astralhollow lies along the whole west side (273 tiles), the Orrery only touches the south-west tip (37 tiles), Stormglass runs along the south (193), the Cairnspine mountains down the east side (247) and the sea lies to the north. The painting shows a rose-salt desert, a diamond of golden roads in the middle, a trunk road up the west to a pair of huge crystals, a road north-east to the coast, a road along the south coast to the Orrery corner and big pink crystals about the land: the design follows it.

## Crossings: two seams, two gates

`world/zone-shapes.txt`: zone 14 in `zones`, `designOnly: [14]`, `seamWith {14: [13, 15], 13: [15, 14], 15: [13, 16, 14]}`.

- **Astralhollow (west) and the Orrery (south-west tip) are seams.** Both neighbours' approved designs ran **unchanged**: Astralhollow had reserved the Prismwaste border (`shape.edges` runs: no art-less object or person within 20 tiles, no spawn within 7, no loose scenery within 2.5), and a scan showed the Orrery has nothing near its north-east corner. Only the neighbours' Prismwaste gates became the seam portals. `orrery_design.design()` now skips a seam portal in its exit routes and its inbound rewrite, exactly as Astralhollow's already did. A cross-zone map diff (zone by zone, voids excluded) shows Astralhollow and the Orrery differ only in that portal, one exit route, the void boxes and one new seam road; Stormglass and the Cairnspine differ only in the arrival coordinates of their Prismwaste gate.
- **Two rim gates**: `path_14_19` Stormglass (south, column 150) and `path_14_27` the Cairnspine (east, row 150), 2.5 tiles in from the last land cell, arrival six tiles beyond. The incoming arrivals are rewritten.
- `seam_roads.ROAD_ZONES` includes 14: one road crosses each seam (13-14 at Prismwaste (7,141); 14-15 at (63,277)).

## What "keep the Prismwaste's style" means here

Standing mirrors, sunspires (the painting's huge crystals become stands of spires), glass stones, salt brush, lens pillars, the Last Shade's awning, the Broken Crown, four families banded by distance from the refuge (mirage jackals by it, then shard scarabs, glass harriers, and the prism sentinels farthest), the Ember Grave Cross.

## The design (`scripts/prism_design.py`, `prism_content.py`)

- **Fixed, moved as a rigid block** from `world/zone-shapes/preshape-14.txt` by (22, 58): the Last Shade (its tent, three lens pillars, all five people, the Travel Master and the mailbox), plaza (86, 172). The Ember Grave Cross and its sleeper move to a hollow in the Lens Fields (160, 172); the Empty Seat's place `es_11_m` and its sleeper to (128, 178).
- **Roads** follow the painting: the diamond (west vertex at the Last Shade), the west trunk up to the Mirror Court, the north-west road to the coast, the south coast roads, the way to each seam and gate, spurs to every outpost and hold circle.
- **Landmarks:** twelve stands of sunspires where the painting shows its crystals, four broken lines of standing mirrors (open at every road), the Great Lens (a broken ring of lens pillars round the heart of the waste), the Broken Crown with its ring, a ring of lens pillars where the Broken Watch stood, a low ring of glass stones round each hold circle, the Pyre Hollow and each elite.
- **Twelve regions** (nearest seed, warped): the Last Shade, the Salt Flats, the Western Verge, the First Ridge, the Lens Fields, the Mirror Court, the Broken Crown, the Beacon Rise, the Broken Watch, the Cairn Slopes, the Sunspire Reaches, the Brine Road. Ten ground classes (`prismClassGround` in `field.js`, `PRISM_MINI`). 234 spawns (was 44), about 1,150 objects.
- **Proofs in `design()`:** everything reachable from the spawn; roads clear; the reserved seam bands honoured; each elite stands awareness + 3 tiles from every road, place, person and hub, 20 from every gate, in its own region.

## Outposts, quests, elites

- **Mirrorfall** (north-west, east of the Mirror Court), **Whitesun Post** (north, below the Broken Crown), **Cairnfoot** (east, inside the diamond by the mountains): three people each (two givers and a trader), a Travel Master linked to the Last Shade and each other, a mailbox. `world/mailboxes.txt` is rewritten for all four Prismwaste hubs.
- **27 quests:** the old 13 (ids kept; six descriptions rewritten) and **14 new**: `prism_h_{hold,rounds}`, `prism_mf_{walk,lenses,hold,glass}`, `prism_ws_{walk,hearts,hold,watch}`, `prism_cf_{walk,fangs,hold,south}`. Four hold circles (the Awning, the Court Mirror, the Beacon, the Cairn Circle) each wake two waves of sleepers. Rewards in `quest_gear_rewards.py`. Swedish written by hand.
- **Elites:** the **Mirror Queen** (49, quest, the Mirror Court) and the **Sunshard** (50, quest, below the Broken Crown) keep their stats; the new **Shatterhorn** (48, no quest, the Sunspire Reaches) is wired into `world.rs`/`items.rs` like the other pilot elites: 480k HP, 5,200 damage, material `horn_prism`, respawn 180 s, enrage `[180, 0.2, 3.0]`. Stats are first guesses. A scorpion was dropped because the Lapis Erg already has a Glass Scorpion. Art `scripts/prism_elite_redraw.py` (preview, montage, extents, build, refresh, export, verify), manifest `client/assets/prismelites.txt`: a rhinoceros of dark rose glass with plates of grey-violet hide, a back of pale prisms and a great faceted prism for a horn; it paws the ground, then charges; it dies on its knees, the horn snaps off and the back crystals go dull one by one.
- Saved characters in zone 14 are moved to the spawn (`shape.placeAtSpawn`).

## Checks

`cargo test prism_` (8 of this zone's, plus the old boss-mechanics one) and the seam/gate tests in `zone_shape_tests.rs`; `python3 scripts/prism_design.py plan OUT.png`; `python3 tests/seam-roads.py`; `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/prism-design-ui.cjs` (`SEAM_ONLY=1 KS='[7]'` for the seams alone; `MUTATE=1` serves the previous `field.js`: the ground-class check must fail).

## Not done / open

- The Shatterhorn's stats and the fights are first guesses; the art is a first pass judged on a contact sheet and one in-game screenshot.
- Older suites that teleport into the Prismwaste at the old coordinates (`tests/prism*`, MCP `prism`) are stale like the other pilot zones'.
- Edge-letter leaks at the triple corner (drawing, a few cells, like the earlier pilot zones'): 40 cells with Astralhollow's coast letter and 47 with the Orrery's Astralhollow letter lie over the Prismwaste floor; at most 52 cells either way over each other seam partner. Not fixed.
- `mail_all_authored_hub_mailboxes_...` fails at the Alderhaven hub before it reaches the Prismwaste (same on the previous pilot commit); `the_four_prismwaste_mailboxes_stand_on_free_ground_...` checks the four Prismwaste mailboxes directly.
- Seam point 15/7 of the browser test was polluted by another player walking through the frame (32% noise); the check passes relative to the noise but proves little at that point (points 13/3, 13/7 and 15/3 are clean).
- The minimap and the world map show the plain pilot background.

## Update 2026-11-08: the Stormglass border is a seam too

`seamWith {14: [13, 15, 19]}`: `path_14_19` is now a seam portal along the south side. The approved design ran unchanged (`LATE_SEAMS = {19}`); only the 10 spawns within 7 tiles of the seam were dropped (`greenmeadow_design.drop_near_seam`), and `design()` now skips a seam portal in its exit routes and inbound rewrite. The Prismwaste keeps one rim gate (the Cairnspine) and has three seams (Astralhollow, the Orrery, Stormglass). See `docs/storm-design.md`.
