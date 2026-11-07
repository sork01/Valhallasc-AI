# Astralhollow as a shaped, authored zone (zone shapes pilot, 2026-11-07)

Owner request: "for pilot. reshape astralhollow. and remake the zone and quests to fit the new shape. no fillers." Owner answers: three new elites (the zone had none; two with a quest, one without), three new outposts. Pilot only (branch `feat/zone-shapes-astral`, off `feat/zone-shapes`, worktree `/media/raid/valhallasc-data/zone-astral-work`, cargo target `zone-astral-target`, wrapper `zone-astral-cargo.sh`). The tenth pilot zone: 0, 1, 2, 3, 6, 7, 8, 9, 13, 16.

## The shape

At k = 1.0 the atlas outline is a tall rounded shield: grid 336, bbox 254 x 335, 60,525 land tiles against the old 128 square's 16,000. The Deep lies along the whole west side, Nacrehold at the short south-west corner, the Orrery along the south, the Prismwaste down the east, the world's coast to the north. The painting shows a dark teal land with a pale court at the south end, one golden trunk road straight up the middle, an oval ring road round a crater, and big cyan crystals along the ring: the design follows it.

## Crossings: all four stay gates

`world/zone-shapes.txt`: zone 13 in `zones`, `designOnly: [13]` (outline floor, no filler, the design places its own gates) and `seamWith {13: []}`. No seam is possible today (the Deep and Nacrehold exclude it, the Prismwaste and the Orrery are not in the pilot), so the Nacrehold Starway (south-west), the Deep stair (west), the Prismwaste road (east) and the Orrery way (south) are walk-in portals on the rim, arrival six tiles in (`astral_nacre_gate`, `path_13_8`, `astral_prism_gate`, `path_13_15`). The incoming arrivals are rewritten (the Deep `path_8_13`, Nacrehold `nacre_astral_gate`, the Prismwaste `prism_astral_gate`, the Orrery `path_15_13`); every other zone is byte-identical.

**The Orrery is the next pilot candidate, so its border and the Prismwaste's are reserved now**, computed from `shape.edges` runs (not seam portals, so a later seam changes neither the masks nor the RNG order): no art-less object or person within 20 tiles, no spawn within 7, no loose scenery within 2.5. The court stands 30 tiles off the Orrery run.

## What "keep Astralhollow's style" means here

The impact basin, living starglass groves, crystal spires, the observatory court with its starwell and lamps, the five families banded by distance from the court (void moths at the court, then crystalwyrms, orbit beetles, eclipse dryads, meteor golems at the far north), the observatory style of buildings. Only the geometry follows the outline.

## The design (`scripts/astral_design.py`, `astral_content.py`)

- **Fixed, moved as a rigid block** from `world/zone-shapes/preshape-13.txt` by (108, 178): the Observatory Court (observatory, starwell, two houses, six lamps), all nine people, the Empty Seat place. The Ember Grave Cross and its sleeper move to a ring of stones in a quiet hollow (196, 128).
- **Roads** follow the painting: the Starway (trunk) from the court north round the observatory to the Hearth Crossing and on through the Heart of the Fall to the Fallstone Hold; the Impact Ring road round the crater; spurs to the north-west crown and the north-east spurs; two loops through the south; the four gate roads.
- **Landmarks:** two broken rings of crystal round the crater (open at every road), the Heart of the Fall (a ring of fallen stone and a ring of obelisks), the Choir Stones (nine obelisks), four waystones at the Hearth Crossing, the Falling Line (five craters of starstone running north-east), the Pyre Hollow round the Cross, a low ring of starstone round each elite, trees in rows in the Moth Orchard, 37 lamps along the long roads.
- **Thirteen regions** (nearest seed, warped): the Observatory Court, the Lantern Meadows, the Moth Orchard, the Singing Glass, the Choir Hollows, the Hearth Crossing, the Heart of the Fall, the Cometfield, the Broken Ring, the Eclipse Wood, the Dusk Spurs, the Fallstone Fields, the Comet's Crown. Nine ground classes (`astralClassGround` in `field.js`): lantern meadow, orchard loam, glass grit, hollow moss, the scorched crater floor, comet frost, dusk heath, eclipse shade, fallstone scree. 340 spawns (was 49), about 1,670 objects.
- **Proofs in `design()`:** everything reachable from the spawn; roads clear; the reserved bands honoured; each elite stands awareness + 3 tiles from every road, place, person and hub and 20 from every gate, in its own region.

## Outposts, quests, elites

- **Choir Rest** (west side of the ring), **Cometwatch** (east side), **Fallstone Hold** (north end): three people each (two givers, a trader), a Travel Master linked to the court and each other, a mailbox. `world/mailboxes.txt` is rewritten for all four Astralhollow hubs.
- **38 quests:** the old 24 (ids kept) and **14 new**: `astral_h_lamps`, `astral_h_rounds`, `astral_cr_{hollows,lanterns,chord,ring}`, `astral_cw_{scout,shells,fire}`, `astral_cometmaw`, `astral_fh_{walk,cores,line}`, `astral_eclipsequeen`. Four hold circles (Hearth Lamps, Choir Chord, Watchfire, Mended Line) each wake two waves of sleepers. Rewards in `quest_gear_rewards.py`. Swedish written by hand.
- **Elites** (hard-coded in `world.rs`/`items.rs` like the other pilot elites, first-guess stats the owner tests): the **Cometmaw** (level 42, quest, east field: a low hunched hound of ice with a comet-tail of fire and a huge maw), the **Eclipse Queen** (44, quest, north-west wood: a rooted bark dryad with a black sun behind her head), the **Orbit Warden** (45, no quest, the Heart: a star-metal sentinel with a lantern heart and three bronze orbiting rings). 150k/190k/260k HP, materials `cometmaw_tail`, `eclipsequeen_crown`, `orbitwarden_ring`, respawn 180 s, enrage `[180, 0.2, 3.0]`. Art `scripts/astral_elite_redraw.py` (preview, montage, extents, build, refresh, export, verify), manifest `client/assets/astralelites.txt`, PixelFlow sources in `scripts/astral_elite_sources.txt`. Three body plans and three deaths: the hound's fire goes out and it slumps, the queen withers, the warden kneels and its rings roll off.
- Saved characters in zone 13 are moved to the spawn (`shape.placeAtSpawn`).

## Checks

`cargo test astral_` (6), `zone_shape`; `python3 scripts/astral_design.py plan OUT.png`; `REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/astral-design-ui.cjs` (`MUTATE=1` serves the previous `field.js`: the ground-class checks must fail).

## Not done / open

- Elite stats and the fights are first guesses; the art is a first pass judged on contact sheets and one in-game screenshot each.
- Older suites that teleport into Astralhollow at the old coordinates (`tests/astral-ui.cjs`, MCP `astral`) are stale like the other pilot zones'.
- The minimap and the world map show the plain pilot background.
