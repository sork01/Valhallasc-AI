# The Wyrdwood as a shaped, authored zone (zone shapes pilot, 2026-11-07)

Owner request: "reshape wyrdwood and remake the zone and quests to fit the new shape. no fillers". Pilot only (branch `feat/zone-shapes-wyrd`, off `feat/zone-shapes`). The sixth pilot zone: 0, 1, 2, 3, 6, 16.

## The shape

At k = 1.0 the atlas outline is a fat triangle with its apex to the north (bbox 420 x 313, grid 424, 57,171 land tiles against the old 36,864): the West coast on the left, the cloud wall to Bifrost Reach on the right, Rimeveil and the Crags along the base. The old 192 square is a near miss (needs k 1.25), so it cannot be the core. `FILL[6]` has `warp=True` (the area-preserving row map from the Gloamfen pilot): it only exists to produce a valid shaped zone, then `wyrdwood_design.py` replaces everything.

Two new seams: **Wyrdwood-Rimeveil** (the long base) and **Wyrdwood-Crags** (the short east end). The Bifrost border stays one gate (`sky_gate`, now on the cloud wall at (221.5, 146.5) beside the Ridge Beacon; Bifrost's `stormrift_down` arrival and both Nornroot doors' return points are rewritten to match). Skaldholm is not a neighbour: `wyrd_onward` now sends you over the Crags or Rimeveil border.

## The design (`scripts/wyrdwood_design.py`, `wyrdwood_content.py`)

Tile = painted px * 2048/1758 - T, T = [168, 71]. The painting shows a brown massif with the River Skuld straight across its middle (y 226); the old topology stays: the town south of the river, one bridge, the fort at its north end, two ridges with one gap each stepping up to the storm giant on the summit.

- **Fixed, moved as rigid blocks** from `world/zone-shapes/preshape-06.txt` (the old, unwarped layout): Hollowmoot with the Elder Ash (shift 45, 127; rect 54..102 x 258..299), the Skuldwatch fort (shift 70, 117.5; camp 137..195 x 192.5..214.5), the Norn Stones with the Nornroot door and its three admission stones, the gallows and the mill (shift 142, 150), the Ember Grave Cross and its sleeper, the Empty Seat circle (at the glade), the rift stones. Every person, place, portal and quest keeps its id.
- **River Skuld:** 373 solid water circles from the sea to the cloud wall (it runs right out to the edge: edge walkers that start inside water are skipped by the Rust edge test), one dry corridor at the Troll Bridge (x 166). Ridge 1 (y 160, gap x 218.5-226.5 east) and ridge 2 (y 128, gap x 108.5-116.5 west) are crag walls from coast to cloud wall. `design()` proves the chokes: close the bridge and the whole north is cut off; close each gap and what lies beyond is cut off, in order.
- **Fifteen regions** (nearest seed, warped): the Moot Fields, the Rotfang Wood, the Moonpetal Glade, the Wyrdgate Rise, the Troll Banks (south bank only), the Oakhorn's Grove, Gallows Hill, the East Fells, the Ruined Mill, the Skuldwatch Yard (north bank only), the Norn Terrace, the West Cliffs, the Storm Terrace, the Highmoor, Hrungnir's Summit. Difficulty by position: boars 21 south-west, crows 23 south-centre and east, trolls 25 along the banks and fells, weavers 27 on the Norn Terrace, rams 29 on the terrace and the Highmoor; 319 spawns (was 70). Ground classes (`fenGround`'s sibling `wyrdClassGround`): leaf litter, moss, heath, scree, bank mud, golden bracken, burnt ground; none within 16-30 tiles of a seam.
- **Roads:** every gate and hub is joined; the north road passes one tile east of the admission stones and the fort's lamp (the old road did too).
- **Water and art-less objects near seams:** none within 16 tiles of a seam (the neighbour draws no water); no house, lamp, bench, stall or post within 20 tiles (no ghost art). Hollowmoot sits 23+ tiles from the Rimeveil seam for that reason.

## Outposts, quests, elites

- **Gallowsfoot** (255, 297, south-east), **Ridgewatch** (180, 143, between the ridges), **Highmoor Hold** (150, 112, on the Highmoor): three givers each (the third is the trader), a Travel Master linked to Hollowmoot and Skuldwatch, a mailbox. The mail directory (`world/mailboxes.txt`) is rewritten for all five Wyrdwood hubs in the shaped frame.
- **45 quests:** the old 31 (ids kept, texts rewritten only where the geography changed: the glade is now south-east, the road in, the beacons) and **14 new**: `wyrd_h_wood`, `wyrd_s_bridge` (hold the bridgehead), `wyrd_gf_quills/hush/vigil/mill`, `wyrd_rw_orders/horns/gap/fire`, `wyrd_hm_rams/threads/ring/gale`. Four new `hold` circles (Hanged Vigil, Ridge Fire, Gale Stones, Bridgehead) each wake two waves of four sleepers. Rewards in `quest_gear_rewards.py`.
- **Elites:** Oakhorn (quest `wyrd_oakhorn`) and Hrungnir (quest `wyrd_hrungnir`) with **the Hanged King** (`hangedking`, level 26, no quest) on Gallows Hill. Hard-coded in `world.rs`/`items.rs` like the other pilot elites (12,600 HP / 360, first guess: the owner tests fights), respawn 180 s, enrage `[180, 0.2, 3.0]`, material `hangedking_noose`. Art `scripts/wyrd_elite_redraw.py` (montage, preview, build, export, verify), manifest `client/assets/wyrdelites.txt`, PixelFlow source in `scripts/wyrd_elite_sources.txt`: a gaunt crowned corpse-king in a tattered crow-feather cloak, a rope wound round the ribs, a noose whose long end streams back, a beam of the gallows for a weapon. Eight distinct attack and death frames.
- Escort: Eydis walks from the Ruined Mill along the Gallows trunk to the Troll Bridge and into Skuldwatch (210 tiles, about 85 s at her pace); her two ambushes (crows by the hill, trolls by the bridge) sit beside the route.

## Neighbours changed (and how little)

Both designs ran with a gate toward the Wyrdwood and the seam replaces it. Adding a seam to a seeded scatter would shift every random draw and reshuffle the whole approved zone, so:

- `greenmeadow_design.Designer` leaves late seams (`LATE_SEAMS = {6}`) out of its masks, and `zone_shapes.phantom_gate` runs the Crags' and Rimeveil's designs with the old gate record (`world/zone-shapes/late-gates.txt`) so its blocked disc stays; then `late_trim` applies the seam's rules locally: loose scenery within 2.5 tiles, water and lava within 17, spawns within 7, ground classes within 16-30 tiles, art-less objects moved to 20.5+ tiles. Measured: Crags lose 19 lava circles and 2 spawns; Rimeveil loses 77 water circles (the ends of two ice-ring arcs next to the border), 7 spawns, and Peakrest's hall and noticeboard move a few tiles. Everything else is byte-identical (checked by diffing `map.txt` object sets).
- **Pilot DB:** `zone_shapes_migrate.py --db ... --zones 6` (a warped zone: characters go to the spawn), and re-run the Crags' and Rimeveil positions scripts: their seam-side objects changed.

## Checks

`cargo test wyrd_tests` (22) and `zone_shape_tests` (the new `the_wyrdwood_*`, `every_wyrdwood_quest...`, `a_wyrdwood_road...`, four hold tests, the seam walks 6-1 and 6-2, the junction test: the two Wyrdwood seams meet at one corner and no land point lies on both). `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/wyrdwood-design-ui.cjs` (regions, hubs, elites, river; pictures in `test-results/wyrdwood-design/`), `SEAMS=1` for the same point from both frames of each seam.

## Not done / open

- Older suites that teleport into the Wyrdwood at old coordinates (`tests/wyrdwood-ui.cjs`, MCP `wyrdwood` and `wyrd_quests`, music and seasonal suites, `nornroot-ui.cjs`) are stale like the other pilot zones'; update before any merge.
- No fight test for the Hanged King (HP and damage are first guesses); `wyrd_balance_probe` still covers only the two old elites.
- Not judged in play: walking time across the zone (the escort route from the mill is 210 tiles), the spawn mix, the storm climb (`stormLevel` runs from the river to the summit in the shaped zone), the look of the Rimeveil seam where the ice rings end early.
