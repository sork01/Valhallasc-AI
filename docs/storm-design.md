# The Stormglass Flats as a shaped, authored zone (zone shapes pilot, 2026-11-08)

Owner request: "for pilot. reshape stormglass shore. probably rename it since its no shore. and remake the zone and quests to fit the new shape. no fillers." Owner answers: the name is **The Stormglass Flats**, seamless against **the Prismwaste (north) and the Obsidian Orrery (west)**, keep the Maelstrom Heart and add **two new elites** (one with a quest, one without), **three new outposts**. Pilot only (branch `feat/zone-shapes-storm`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-storm-work`, cargo target `zone-storm-target`, wrapper `zone-storm-cargo.sh`). The thirteenth pilot zone: 0, 1, 2, 3, 6, 7, 8, 9, 13, 14, 15, 16, 19.

## The shape and the name

At k = 1.0 the atlas outline is **landlocked**: grid 328, 72,140 land tiles against the old 128 square's 16,384, and every border is a neighbour (the Prismwaste on the north, 193 tiles; the Orrery on the west, 250; Sunward Vale on the east, 288; Emberwake on the south, 269; Frostwake only the 50-tile north-east corner). There is no coast, so the Shore became the Flats: the sea has gone and left its floor. The painting shows a dark night plain under huge blue storm-glass crystals, a pale flat in the south-west, a straight trunk road down the middle, a hexagon of roads round two crystals in the west, a diagonal web of roads in the east and a compass rose in the south. Asterion is a landmark point inside this province (atlas `cities`): its gate stands on the painted compass rose and the city stays as it is.

The rename is data and display only: ids, the `stormglass` theme and the `stormglass_*` prefixes stay. `storm_design.rename` rewrites the name in every string of the world dict at the very end of `apply` (the zone name is also the `reach` target of `stormglass_onward`, the portal names in other zones, the achievement text in the quests of other zones); the hand-edited files follow: `world/achievements.txt` explore_19, `world/atlas-geography.txt`, `client/worldmap.js` NAMES, `scripts/sv-keep.txt` and the `sv-translations.txt` keys.

## Crossings: two seams, three rim gates, the compass gate, the Eye

`world/zone-shapes.txt`: zone 19 in `zones`, `designOnly: [19]`, `seamWith {19: [14, 15], 14: [13, 15, 19], 15: [13, 16, 14, 19]}`.

- **The Prismwaste (north) and the Orrery (west) are seams.** Both neighbours' approved designs ran **unchanged**: a scan showed their Stormglass borders were nearly clean (no art-less object or person within 20 tiles, no loose scenery within 2.5; only 10 and 5 spawns within 7 tiles). Their `LATE_SEAMS = {19}` keeps the masks as they were; `greenmeadow_design.drop_near_seam` drops only those 15 spawns afterwards (Prismwaste 234 to 224, Orrery 358 to 353); the Prismwaste's design now also skips seam portals in its exit routes and inbound rewrite (the Orrery's already did). A cross-zone map diff against `HEAD` (zone by zone, voids excluded) shows zones 14 and 15 differ only in the portal, one exit route, the spawns and one seam road; zones 17, 20, 26, 29 and 45 only in an arrival coordinate. `seam_roads.ROAD_ZONES` includes 19.
- **Three rim gates**: Sunward Vale (east, row 203), Frostwake (north-east corner, column 262), Emberwake (south, column 137), 2.5 tiles in from the last land cell, arrival six tiles inside. Their far gates' arrivals are rewritten.
- **Asterion's gate** (`stormglass_asterion_gate`) stands in the open at (177.5, 271) on the compass rose: no `walk`, the classic two-post gate, arrival on the road side (177.5, 264).
- **The Eye Below** keeps its descent (`stormglass_eye_descent`, now (238, 108)) and both ways back from the dungeon template (`eye_below_return`, `eye_below_exit`) arrive in front of it.

## The design (`scripts/storm_design.py`, `storm_content.py`)

- **Fixed, moved as rigid blocks** from `world/zone-shapes/preshape-19.txt` (the old layout): Breakwater Camp (huts, lamps, bell, its six people, the Spark Travel master, the mailbox) by (58, 154) onto the pale flat of the painting, plaza (88, 262), and the Eye (arch, descent, bell, the Meeting Stone, Mara of the Last Light) by (133, 81) into the Eye Basin. Every person, place, portal and quest keeps its id.
- **Roads** follow the painting: the trunk, the hexagon, the east web, the thin lightning road, spurs to every outpost and hold circle, the gate roads.
- **Landmarks:** thirteen stands of storm-glass spires where the painting shows its crystals (the biggest, the Stormspire, in the north), three broken rings of salt pillars round the Eye Basin (the sea's old whirlpool), eight tide bells at the points of the compass rose, two tide bells at each junction, a low ring of black pebbles round each hold circle and elite.
- **Twelve regions** (nearest seed, warped): Breakwater Pan, The Black Dunes, The Reed Seeps, The Salt Pans, The Northern Drift, The Stormspire, The Rodfields, The Eye Basin, The Sunward Bank, The Compass Floor, The Low Shards, The Cold Rim. Ten ground classes (`stormClassGround` in `field.js`, `STORM_MINI`). 343 spawns (was 43), about 1,460 objects. Four families banded by distance from the camp: saltclaws, stormgulls, glass rays and breaker sentinels.
- **Proofs in `design()`:** everything reachable from the spawn; roads clear; the reserved seam bands honoured; each elite stands awareness + 3 tiles from every road, place, person, gate and hub and 20 from every gate, in its own region.

## Outposts, quests, elites

- **Rodstead** (west, the Reed Seeps), **Fulgur Post** (north-west), **Bankhold** (east, on the old sea wall): three people each (two givers and a trader), a Travel Master linked to Breakwater Camp and each other, a mailbox. `world/mailboxes.txt` is rewritten for all four hubs.
- **28 quests:** the old 13 (ids kept; five descriptions and one title rewritten, the camp's people say a dry sea bed now) and **15 new**: `storm_h_hold`, `storm_h_rounds`, `stormglass_hermit` (the elite's), and four per outpost `storm_{rs,fp,bh}_*` (a walk, a bring, a hold circle, a final walk). Four hold circles each wake two waves of sleepers. Rewards in `quest_gear_rewards.py`. Swedish written by hand.
- **Elites:** the **Maelstrom Heart** (65, quest, kept, at the foot of the Stormspire), the new **Lamphouse Hermit** (63, quest `stormglass_hermit`, 3 players, the Salt Pans) and the new **Stormtusk** (62, no quest, the Low Shards). Wired into `world.rs`/`items.rs` like the other pilot elites: stats 1.15 M HP / 11,800 and 0.98 M HP / 10,600 (**first guesses**), materials `hermit_lens` and `tusk_storm`, respawn 180 s, enrage `[180, 0.2, 3.0]`.
- **Art** `scripts/storm_elite_redraw.py` (preview, montage, extents, build, refresh, export, verify), manifest `client/assets/stormelites.txt`: a hermit crab as big as a barn wearing a wrecked lighthouse lamphouse (leaning stone drum, iron gallery, a lantern room with one smashed pane, copper-green roof and rod; slit-pupilled eyes on armoured stalks under spiked brows; a toothed crusher; the rod discharges into the claw on the slam; the tower tips back and the lamp gutters out when it dies) and a stranded narwhal of black glass (scarred pale belly, glowing cracks that go dark one by one, a white slit of an eye, needle teeth, a spiral tusk that crackles and snaps off when it dies). First pass, judged on a contact sheet.
- Saved characters in zone 19 are moved to the spawn (`shape.placeAtSpawn`).

## Checks

`cargo test stormglass_` (9), `prism_`, `orrery_`, `zone_shape` (the seam sets, 14-19 and 15-19 walks, the Flats' three gates), `eye_below_`; `python3 scripts/storm_design.py plan OUT.png`; `python3 tests/seam-roads.py`; `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/storm-design-ui.cjs` (`SEAM_ONLY=1 KS='[7]'` for the seams alone; `MUTATE=1` serves the previous `field.js`: the ground-class check must fail).

## Not done / open

- The elites' stats and fights are first guesses; the art is a first pass.
- The Empty Seat's `es_15` text was reworded (owner, 2026-11-08): salt boils on the dry sea bed, in `scripts/empty_seat.py` and its Swedish.
- Older suites that teleport into the Shore at the old coordinates (`tests/stormglass-ui.cjs`, MCP `stormglass`) are stale like the other pilot zones'.
- Sunward Vale, Frostwake and Emberwake are not shaped yet; when they are, their borders with the Flats need the same reservation scan (art-less 20, spawns 7, loose scenery 2.5 along `shape.edges`; the Flats' east side is not reserved).
- The minimap and the world map show the plain pilot background.
