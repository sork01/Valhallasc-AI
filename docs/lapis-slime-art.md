# The Lapis Erg enemy artwork (deployed as Beta 1.39.30)

**Status:** deployed 2026-11-04 as Beta 1.39.30 (fast-forward merge `d9f588e`, client-only, server PID 1654327 and binary unchanged; receipt `test-results/lapis-release-20261104.json`). Built on `feat/lapis-slime-art` in `/media/raid/valhallasc-data/lapis-slime-work`. The Lapis Erg is zone 25 in the docs and index 24 in `world/map.txt`; look it up by name in tests.

**Owner direction (2026-11-04):** every enemy unique and mean, no shared round-eye-plus-blush face. This overrides the older "big eyes with highlight, blush" wording in `LAPIS-SLIME-ART`. Each kind has its own face routine: narrow glaring beads under a dark brow slab with two bared chisel incisors (sandhopper); ears laid back over amber slits in a dark mask, lip drawn up off long fangs (dunefennec); a ridge of six unequal amber eyes over hooked chelicerae (glassscorpion); a raw red slit eye under a hard brow ridge and a deep-hooked beak on a wrinkled bare head (sunvulture); a carved stone mask with two hollow cyan pits and a cracked mouth dragged down at both corners (dunecolossus); a hard magenta slit under a cruel brow ridge over a long hooked beak (mirageroc). No blush anywhere. No face routine is shared with another zone.

| kind | look | attack | death |
|---|---|---|---|
| sandhopper | hunched sand jerboa on huge hind legs, long tail with a dark tuft | coils low, then springs claws-first with the jaws open | the hind legs give way and it stretches out flat, head down, ears back, tail limp |
| dunefennec | lean cream fox with a deep chest, tucked waist, jointed legs, pointed muzzle, enormous ears and a dark-tipped bush tail | sinks into a stalk with the ears laid flat, then lunges with the forepaws reaching and the jaws wide | the legs buckle, it sinks onto its belly and stretches out flat, head down, ears flopped |
| glassscorpion | rigid blue glass shell, two claws, segmented tail with a glowing amber sting | tail cocks over the back, then stabs forward over the head, claws spread | the shell cracks, the tail drops, it tips over onto its back with the legs curling in (rigid: no squash) |
| sunvulture | hunched plum bird, bald pink head, white ruff, gold sun mark on the breast | wings half open, then thrown wide as the neck rips down | the knees buckle, the breast drops, the neck flops forward along the ground and the wings slump back and down |
| dunecolossus (elite) | giant of sand-coloured stone blocks, lapis breastplate, gold stud | both fists overhead, then hammered down in front with sand thrown up | head drops first, arms break off, torso and legs slump into a heap of blocks (stone breaks, it does not collapse like a slime) |
| mirageroc (elite, hovers) | vast blue-feathered bird, gold breast, orange crest, magenta-shimmer wing fringes | wings beat up and back, then a dive with talons forward and the beak wide | a mirage does not fall like a bird: heat-haze bands slide sideways and an ordered dither eats the body as it sinks; a few feathers and gold sparks reach the ground |

## Files and frames
The six enemies share `client/assets/lapis.txt` with five **NPCs** (`lapis_keeper`, `lapis_cartographer`, `lapis_warden`, `lapis_seer`, `lapis_travel`, 96x96, tops 82/83/83/83/82). `export` merges only the six enemy entries and asserts the NPCs' sprite ids and tops are unchanged and that they have no `kindFrames` entry. The manifest keeps its eleven-kind order and the zone-wide `frame [96,96]`/`anchor [48,90]` the NPCs use. A size change needs a NEW PixelFlow source: remove the kind from `scripts/lapis_slime_sources.txt` and run `SOURCE_SUFFIX=_x python3 scripts/lapis_slime_redraw.py build`.

| kind | frame | anchor | PixelFlow source | top |
|---|---|---|---|---|
| sandhopper | 102x60 | (55,53) | `535fef92c3c75bf7` | 50 |
| dunefennec | 98x62 | (47,55) | `ddbbe969d30b6d27` | 51 |
| glassscorpion | 121x79 | (52,72) | `36760931f219d573` | 47 |
| sunvulture | 103x77 | (42,64) | `ebe3414bf120c529` | 57 |
| dunecolossus | 110x106 | (50,100) | `b952429dcb6f6070` | 80 |
| mirageroc | 116x124 | (56,118) | `3442d18f81495d7e` | 113 |

Art scale (`SCALE`) matches each kind's idle size to the old art's and was checked on in-game screenshots: the first pass drew the colossus at 1.4x and it towered over the hero, because the engine already draws elites larger, so the colossus is now 1.05x and the roc 1.0x. Only the Mirage Roc hovers (lowest living pixel at least 12 px above the anchor row, settles on the ground row on death). The other five are grounded; `frame()` rests the lowest pixel on the anchor row.

```sh
python3 scripts/lapis_slime_redraw.py preview|montage [kinds]   # contact sheets
python3 scripts/lapis_slime_redraw.py extents [kinds]           # measure on a scratch canvas
python3 scripts/lapis_slime_redraw.py build                     # create missing sources
python3 scripts/lapis_slime_redraw.py refresh <kinds>           # rewrite same-size sources
python3 scripts/lapis_slime_redraw.py export                    # editor frames -> atlas, manifest, tops (merges)
python3 scripts/lapis_slime_redraw.py verify
```
`make_lapis_sprites.py` keeps its helpers but its CLI delegates here and refuses `--replace`. `lapis_cel_redraw.py` is untouched (the old art; `frostwake_cel_redraw.py` imports it). The five NPCs keep their old sources.

## Rollback
```sh
python3 scripts/rollback_lapis_art.py --target /path/to/checkout            # dry run
python3 scripts/rollback_lapis_art.py --target /path/to/checkout --apply
```
Backup `/media/raid/valhallasc-data/lapis-slime-original-20261104` (seven files, hashes and the old PixelFlow ids in `manifest.txt`). Every hash is checked before any write, a corrupt backup is refused, and the restore stops if an NPC entry in the live manifest differs from the backup's.

## Clipping guard (added after the first review)
`frame()` rolls every grounded frame so its lowest pixel sits on the anchor row, and the border check ran AFTER that roll, so art drawn below the canvas was cut off silently and then looked fine to every check. `frame()` now tests the RAW Painter canvas for any non-empty edge row or column BEFORE the roll (`drawn past the canvas edge before the ground roll (clipped)`), and `build` (STRICT) refuses it; `preview` and `montage` list the offenders. `extents` measures the raw drawing on a scratch canvas with 150 rows of headroom and 42 below the ground, and reports how far the raw drawing goes below the anchor row. A 1-2 pixel sliver below the real feet is trimmed before grounding (it had lifted the fennec's paws one row off the ground). The first review also found a real bug: the colossus shoulders were placed with `tx and ty + 8`, which is 0 whenever `tx` is 0.0, so its shoulders sat on the ground and its fists hung at its feet. Rigid rotation of a whole creature through the ground was the cause of the clipped scorpion, sandhopper, fennec and vulture deaths: tails now use `settle()` (rigid with the body at the start, lying flat behind it at the end) and deaths buckle and lie down instead of tumbling.

## Checks
`tests/lapis-slime-art.cjs` (126 checks, passing; they did NOT catch the problems above, so judge the `-frames.png` sheets and the in-game screenshots it writes (`lapis-slime-<kind>-game.png` in `test-results/driver-*`), not the count): production loading, the five untouched NPCs, portraits, timings, borders, eight distinct attacks and deaths with a reaching strike, anchor-row grounding (the roc hovers, then settles), planted feet, health-bar tops, no browser errors. Run it with `scripts/test-touch-bounded.sh` and, in the SAME command, `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`, `NODE_PATH=<main>/node_modules:~/webserver/www/dybase2/node_modules`, `VALHALLA_BINARY=<main>/target/release/valhalla-server`; `SOFT_CHECKS=1` lists every failure. Mutation: `MUTATE_KIND=sunvulture MUTATE_PNG=<original atlas> LAPIS_ART_KINDS=sunvulture` fails as required. `tests/lapis-ui.cjs` now reads each kind's expected atlas size from `Field.frameOf` (it asserted 768x480 for all eleven); it has not been run. `python3 scripts/lapis_slime_review.py review|verify|upload` (pictures `valhallasc-lapis-*`; upload is a separate, explicit step and has NOT been done).

## Likely veto points
The roc's wings read like a fanned peacock tail; the roc's last two death frames are nearly empty by design; the scorpion's claws are plain; the colossus heap is a pile of blocks with the skull on top.
