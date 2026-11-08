# The Obsidian Orrery as a shaped, authored zone (zone shapes pilot, 2026-11-08)

Owner request: "for pilot. reshape orrey. and remake the zone and quests to fit the new shape. no fillers." Owner answers: keep the Pendulum Matron and the Epoch Engine and add one new elite with no quest, three new outposts, and the Orrery seamless against **Astralhollow and the Moonspore Canopy** (every other crossing stays a walk-in gate). Pilot only (branch `feat/zone-shapes-orrery`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-orrery-work`, cargo target `zone-orrery-target`, wrapper `zone-orrery-cargo.sh`). The eleventh pilot zone: 0, 1, 2, 3, 6, 7, 8, 9, 13, 15, 16.

## The shape

At k = 1.0 the atlas outline is a wide, tall wedge: grid 344, bbox 313 x 338, 78,983 land tiles against the old 128 square's 16,000. Astralhollow lies along the whole north border (an arc, 197 tiles), the Moonspore Canopy along the short south border at the bottom left, the Crags down the west side, Nacrehold at the north-west corner, the Prismwaste at the north-east corner, Stormglass down the east side and Emberwake on the south-east diagonal. The painting shows a dark starry plain, two trunk roads running down from the north, a diamond of roads in the west, an X where they cross in the middle, a pale plaza in the south-west corner (the Stillpoint) and big obsidian shards: the design follows it.

## Crossings: two seams, five gates

`world/zone-shapes.txt`: zone 15 in `zones`, `designOnly: [15]` and `seamWith {15: [13, 16], 13: [15]}` (Astralhollow's rule changes from `[]`; the Moonspore Canopy has no rule). Without the `15` entry the Crags would seam with the Orrery by default and reshuffle the approved Crags.

- **Astralhollow (north) and the Moonspore Canopy (south) are seams**: walk over the line anywhere. Astralhollow's approved design ran unchanged: it had reserved the Orrery border from `shape.edges` runs (no art-less object or person within 20 tiles, no spawn within 7, no loose scenery within 2.5), so only its `path_13_15` gate became the seam portal (`astral_design.shifted_state` skips a seam portal, `exitRoutes` and the inbound rewrite skip it). The Canopy is a filler zone: it only lost its gate (`moonspore_orrery_gate` is the seam portal now), five loose objects and one spawn moved with its seam road. Diff against the previous pilot map: Astralhollow differs only in the portal, one exit route, the void boxes and one new road; every other zone differs only in the arrival coordinates of its gate to the Orrery.
- **Five rim gates** stand six tiles in from the void edge, arrival six tiles beyond: `path_15_9` Nacrehold, `path_15_1` the Crags, `orrery_prism_gate` the Prismwaste (north-east corner), `path_15_19` Stormglass, `atlas_15_45` Emberwake. The incoming arrivals (`path_9_15`, `path_1_15`, `prism_orrery_gate`, `path_19_15`, `atlas_45_15`) are rewritten.
- `seam_roads.ROAD_ZONES` now includes 13 and 15: one road crosses each seam (13-15 at Astralhollow (172,332); 15-16 at the Orrery (83,340)).

## What "keep the Orrery's style" means here

The starry black plain, the three broken rings of clockwall (now round the Axis, the crossing in the middle, open at every road), obsidian spires (the painting's shards become stands of spires), cogstones, timegrass, hour pillars, the Stillpoint (the pavilion and its refuge moved whole), the Epoch Crown at the top of the northern valley, the four families banded by distance from the refuge (bronze mantises by the refuge, then gearlings, orbit seers, chronoguards to the north), the Ember Grave Cross.

## The design (`scripts/orrery_design.py`, `orrery_content.py`)

- **Fixed, moved as a rigid block** from `world/zone-shapes/preshape-15.txt` by (50, 189): the Stillpoint (the pavilion, two hour pillars, all five people, the Travel Master and the mailbox), plaza (79, 301). The Ember Grave Cross and its sleeper move to a quiet hollow (64, 230); the Empty Seat's place `es_12_m` to (98, 176).
- **Roads** follow the painting: two trunks from the north (x 163 and x 222-230), the western diamond, the X, the Axis, the lower triangle, the east-west plaza roads, the west road along the Crags; spurs to each outpost, the Crown, the hold circles and the five gates.
- **Twelve regions** (nearest seed, warped): the Stillpoint, the Brass Meadows, the Dust Verge, the Gearyards, the Lower Ring, the Axis, the Winding Court, the Seer Terraces, the Obsidian Reaches, the Crown Valley, the Hourglass Heath, the Escapement. Nine ground classes (`orreryClassGround` in `field.js`, `ORRERY_MINI`): brass meadow, dust, gearyard slate, ring floor, the Axis's brass floor, obsidian glass, valley slate, heath, the burnt hollow of the Cross. 358 spawns (was 49), about 1,800 objects.
- **Proofs in `design()`:** everything reachable from the spawn; roads clear; the reserved bands honoured (spawns, people, art-less objects, loose scenery); each elite stands awareness + 3 tiles from every road, place, person and hub, 20 from every gate, in its own region.

## Outposts, quests, elites

- **Bellcourt** (west, under the Winding Court), **Crownwatch** (north, in the valley below the Crown), **Shardwatch** (east): three people each (two givers and a trader), a Travel Master linked to the Stillpoint and each other, a mailbox. `world/mailboxes.txt` is rewritten for all four Orrery hubs.
- **27 quests:** the old 13 (ids kept; matron, engine and survey texts rewritten) and **14 new**: `orrery_h_{hold,rounds}`, `orrery_bc_{walk,blades,hold,axis}`, `orrery_cn_{valley,plates,hold,lens}`, `orrery_sw_{reaches,glass,hold,south}`. Four hold circles (the Stillpoint Dial, the Western Bell, the Crown Gate, the Shardfall Ridge) each wake two waves of sleepers. Rewards in `quest_gear_rewards.py`. Swedish written by hand.
- **Elites:** the **Pendulum Matron** (54, quest, the Winding Court) and the **Epoch Engine** (55, quest, under the Crown) keep their stats; the new **Mainspring Wyrm** (53, no quest, the Obsidian Reaches in the east) is wired into `world.rs`/`items.rs` like the other pilot elites: 600k HP, 6,400 damage, material `mainspring_coil`, respawn 300 s, enrage `[180, 0.2, 3.0]`. Stats are first guesses. Art `scripts/orrery_elite_redraw.py` (preview, montage, build, export, verify), manifest `client/assets/orreryelites.txt`: a serpent of brass cog-discs on a wound spring with an obsidian head, a jaw of cog teeth and one amber slit eye; it rears and lunges, and dies when the spring snaps (the discs roll apart, the head drops last).
- Saved characters in zone 15 are moved to the spawn (`shape.placeAtSpawn`).

## Checks

`cargo test orrery_` (6) and the seam/gate tests in `zone_shape_tests.rs`; `python3 scripts/orrery_design.py plan OUT.png`; `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/orrery-design-ui.cjs` (`SEAM_ONLY=1 KS='[7]'` for the seams alone; `MUTATE=1` serves the previous `field.js`: the ground-class check must fail).

## Not done / open

- The Mainspring Wyrm's stats and the fights are first guesses; the art is a first pass judged on a contact sheet and one in-game screenshot.
- Edge letters of other neighbours over a seam partner's floor (a drawing leak, like the other pilot corners): Nacrehold 7 cells over Astralhollow, the Prismwaste 52 cells over the Orrery's north-east corner, Emberwake 13 over the Canopy, the Crags 2 and Emberwake 31 over the Orrery from the Canopy's side.
- Older suites that teleport into the Orrery at the old coordinates (`tests/orrery-ui.cjs`, MCP `orrery`) are stale like the other pilot zones'.
- The minimap and the world map show the plain pilot background.

## Update 2026-11-08: the Prismwaste border is a seam too

`seamWith {15: [13, 16, 14]}`: `orrery_prism_gate` is now a seam portal at the north-east corner (37 tiles). Nothing of the Orrery stood near it, so the design ran unchanged; `design()` now skips a seam portal in its exit routes and inbound rewrite (the same filter Astralhollow has). The Orrery has four rim gates (the Crags, Nacrehold, Stormglass, Emberwake) and three seams (Astralhollow, the Prismwaste, the Canopy). See `docs/prism-design.md`.

## Update 2026-11-08: the Stormglass border is a seam too

`seamWith {15: [13, 16, 14, 19]}`: `path_15_19` is now a seam portal along the east side (250 tiles). The approved design ran unchanged (`LATE_SEAMS = {19}`); only the 5 spawns within 7 tiles of the seam were dropped. The Orrery keeps three rim gates (the Crags, Nacrehold, Emberwake) and has four seams (Astralhollow, the Prismwaste, the Canopy, Stormglass). See `docs/storm-design.md`.
