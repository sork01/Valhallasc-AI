# Rimeveil Glacier as an authored map (zone shapes pilot, 2026-11-06)

Owner request: "redesign rimeveil. keep shape and borders etc. but redesign the rest of the map and the quests. to not have any filler land and to use the entire map." Pilot only (`feat/zone-shapes`). Same request as Greenmeadow and the Crags. Owner choices: three new elites (two with a quest, one without), three outposts, every old `rime_*` quest id kept and rewritten, the painted ice rings become solid terrain with crossings.

## What stays

The outline, the seams to the Crags (east) and Gloamfen (south), Skaldholm's wall and vault, the Wyrdwood gate (north, `path_2_6`), Rimeward Camp and its five people, the spawn point, the Ember Grave Cross and its sleeper, the Empty Seat circle, the seasonal summoning pad at (293,225) with its five sleepers and four `*Ritual` records, and every quest id (14 `rime_*`, `es_03`, `es_go_03`).

## How it is built

- `scripts/rimeveil_design.py` runs in `zone_shapes.py apply` right after the Crags' design (`if 2 in cfg['zones']`), after `build_walls`, so nothing it does can move a border. `class Rimeveil(Designer)` reuses `greenmeadow_design.py`'s helpers; data in `scripts/rimeveil_content.py`. `python3 scripts/rimeveil_design.py plan OUT.png` draws it read-only. Rimeveil is `world['zones'][1]` (the file list starts at zone 1).
- The plan traces the painted atlas (`tile = painted px * 2048/1758 - shape.T`, T = [142,347]): four concentric blue ice rings round a Heart at (167,149), the grey spine road from the Wyrdwood gate straight down through every ring, the snow-capped peaks, the dark ice-holes scattered everywhere (thickest in the north-west).
- **Rings:** `RINGS` = (x radius, y radius, half width, gaps). Each is a line of overlapping `water` circles (collision) with a natural gap, a ford wherever a road crosses (97 fords) and tapering ends. Painted open towards the camp: the south-east of every ring is left out because of the vault (below).
- **Water is drawn from this zone's frame only.** The neighbours (the Crags and Gloamfen seams, Skaldholm's vault) draw no `water` scenery, so none stands within 17 tiles of a seam or inside the land region the vault shows (`shape.vaultRegions[0].land`, asserted: seam gap 17.2, vault gap 5.4). The same rule held for the Crags' lava.
- Eleven regions, every land cell in one: The Heart of the Glacier, The Inner Whorl, The Bluewater Walk, The Rimewalk (inside the outer ring, the lane out to the third ring), then The Bluewater Walk (inside the third), The Inner Whorl (inside the second) and The Heart (inside the first): each ring's own ellipse decides, because the rings are not scalings of one another, so a lane changes name exactly where a ring is crossed. Outside the outer ring by nearest seed: The Rimeward Shelf, The Southern Drifts, The Shearwind Strand, The Whalebone Fells, The Wyrdgate Reach, The Hornspire Ridge, The Whitefall.
- **Peaks:** `rime_peak` (`client/rimeveilart.js`, new file, script tag in `index.html`), three sizes by `v`, foot = collision circle, `occludes`. 28 of the painted peaks, nudged off roads and fixed spots (a peak with no room within 40 tiles is left out; none was).
- Self-checks in `design()`: spawns, new people, places and every gate reachable from the spawn on foot with ice solid, roads on land with nothing standing on them, Sif's escort route clear leg by leg, under 1% of open cells cut off, water clear of seams and the vault region. Two `sync-world` runs are byte-identical and no other zone changes.
- Difficulty comes only from where a kind stands: crabs (10) on the Shelf, Drifts and Strand; wolves (12) on the Rimewalk, Fells and Strand; yetis (13) on the Bluewater Walk, Whitefall, Hornspire and Fells; wyrms (15) in the Whorl, the Heart and the Hornspire. 303 spawns (was 109).

## New zone data and client

- `groundSpans` for zone 2: 1 packed snow, 2 blue ice, 3 hoar stone, 4 moraine, 5 powder, 6 wet bank beside the rings (`frostGround`, `FROST_MINI` in `field.js`). None within 16-30 tiles of a seam. Roads stay the plain frost road colour.
- `drawWater` has a frost look (pale snow lip, ice shelf, deep azure, drifting floes and hairline cracks instead of ripples and lily pads) and runs for the frost theme; minimap and world map colour `water` blue in the glacier.
- `regions`: reused from the Crags work; `camps`: Driftwatch (south-west, the fen border), Shearwind Post (west cliffs), Peakrest (north-east peaks), each with givers, a trader, a mailbox and a Travel Master linked to Rimeward Camp.
- Seam ghosts of a frost neighbour now include art-drawn scenery (`rime_peak`), as for the meadow and the Crags.
- Minimap: in the authored glacier scattered stones and trees (and ice blocks) are not dotted (`MINI_QUIET`).

## Quests

33 in the zone: 16 old ids (14 rime, 2 Empty Seat; 12 rewritten, some moved to outpost givers), 17 new. Level 10-15, `rewardXp = levels.txt[level-1] / 10`. Kinds: bring (frost pelts, rime shells, yeti horns, wyrm scales), kill, visit, talk, hold (The Stranded Sledge, The Shearwind Fire), escort (Sif Whitehand from Peakrest to the Heart), and a three-ford walk (`rime_spiral` (the four southern fords, one per ring)). New people and quest ids start `rime_` because a Rust test (`world.rs`, rimeveil quest catalogue) asks for it. Swedish by hand in `sv-translations.txt`, names and places in `sv-keep.txt`. Rewards in `quest_gear_rewards.py` (two greens per outpost, blue for the two group elites).

## Elites

`hoarhorn` (the Whalebone Fells, quest `rime_sw_hoarhorn`), `whitewail` (the Hornspire Ridge east of Peakrest, quest `rime_pk_whitewail`), `shardback` (the drifts beside the Fenward Gap, no quest). Level 15, hard-coded in `world.rs`/`items.rs` like the Crags' elites, respawn 180 s, enrage `[180, 0.2, 3.0]`, materials `hoarhorn_tusk`, `whitewail_shroud`, `shardback_carapace`. Art: `scripts/rime_elite_redraw.py` (montage, preview, extents, build, refresh, export, verify), sources `scripts/rime_elite_sources.txt`, manifest `client/assets/rimeelites.txt`. A mammoth with an ice-shard back and a tangle of icicle tusks, a screaming wraith in a torn shroud, a glacier crab with hooked pincers; eight distinct attack and death frames each. Stats are a first guess, not balanced: the owner tests fights.

## Checks

`REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/rimeveil-design-ui.cjs` (regions, outposts, elites, the four rings are water, pictures in `test-results/rimeveil-design/`); `SEAMS=1` compares the same world point from both frames of each seam against a camera-move control. Rust: `cargo test glacier` and `the_signal_fire`, `the_stranded_sledge`, `sif_walks` in `zone_shape_tests.rs` (outposts, every quest's targets, elites, roads and solid rings, both holds, the escort).

## Pilot database

`scripts/rimeveil_positions.py --db FILE [--apply]` moves characters who now stand inside scenery to the spawn (service stopped, backup first).

## Text and geography

Every compass word in the quest and dialogue text was checked against the giver's and target's coordinates (the Crags lie east of Rimeveil, so Rimeveil is a walk *west* of Cinderwatch; the camp's shelf lies north, east and west of it, Skaldholm's wall south). `rime_hornspire` is at (306,101), east of Peakrest, in the Hornspire region.
