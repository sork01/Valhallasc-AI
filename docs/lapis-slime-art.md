# The Lapis Erg enemy artwork (candidate, not deployed)

**Status:** built 2026-11-04 as a client-only candidate on `feat/lapis-slime-art` in `/media/raid/valhallasc-data/lapis-slime-work`. Not merged, no version bump, nothing live. The Lapis Erg is zone 25 in the docs and index 24 in `world/map.txt`; look it up by name in tests.

**Owner direction (2026-11-04):** every enemy unique and mean, no shared round-eye-plus-blush face. This overrides the older "big eyes with highlight, blush" wording in `LAPIS-SLIME-ART`. Each kind has its own face routine: narrow glaring beads under a dark brow slab with two bared chisel incisors (sandhopper); ears laid back over amber slits in a dark mask, lip drawn up off long fangs (dunefennec); a ridge of six unequal amber eyes over hooked chelicerae (glassscorpion); a raw red slit eye under a hard brow ridge and a deep-hooked beak on a wrinkled bare head (sunvulture); a carved stone mask with two hollow cyan pits and a cracked mouth dragged down at both corners (dunecolossus); a hard magenta slit under a cruel brow ridge over a long hooked beak (mirageroc). No blush anywhere. No face routine is shared with another zone.

| kind | look | attack | death |
|---|---|---|---|
| sandhopper | hunched sand jerboa on huge hind legs, long tail with a dark tuft | coils low, then springs claws-first with the jaws open | thrown over backwards onto its back, hind legs kicking up |
| dunefennec | lean cream fox, enormous ears, brush tail | drops into a stalk with the ears laid flat, then lunges with the jaws wide | slumps forward onto its chest, then rolls onto its side, ears limp |
| glassscorpion | rigid blue glass shell, two claws, segmented tail with a glowing amber sting | tail cocks over the back, then stabs forward over the head, claws spread | the shell cracks, the tail drops, it tips over onto its back with the legs curling in (rigid: no squash) |
| sunvulture | hunched plum bird, bald pink head, white ruff, gold sun mark on the breast | wings half open, then thrown wide as the neck rips down | wings crumple out to the sides and it pitches forward onto its breast |
| dunecolossus (elite) | giant of sand-coloured stone blocks, lapis breastplate, gold stud | both fists overhead, then hammered down in front with sand thrown up | head drops first, arms break off, torso and legs slump into a heap of blocks (stone breaks, it does not collapse like a slime) |
| mirageroc (elite, hovers) | vast blue-feathered bird, gold breast, orange crest, magenta-shimmer wing fringes | wings beat up and back, then a dive with talons forward and the beak wide | a mirage does not fall like a bird: heat-haze bands slide sideways and an ordered dither eats the body as it sinks; a few feathers and gold sparks reach the ground |

## Files and frames
The six enemies share `client/assets/lapis.txt` with five **NPCs** (`lapis_keeper`, `lapis_cartographer`, `lapis_warden`, `lapis_seer`, `lapis_travel`, 96x96, tops 82/83/83/83/82). `export` merges only the six enemy entries and asserts the NPCs' sprite ids and tops are unchanged and that they have no `kindFrames` entry. The manifest keeps its eleven-kind order and the zone-wide `frame [96,96]`/`anchor [48,90]` the NPCs use. A size change needs a NEW PixelFlow source: remove the kind from `scripts/lapis_slime_sources.txt` and run `SOURCE_SUFFIX=_x python3 scripts/lapis_slime_redraw.py build`.

| kind | frame | anchor | PixelFlow source | top |
|---|---|---|---|---|
| sandhopper | 103x60 | (56,54) | `b3326dd314443057` | 49 |
| dunefennec | 95x64 | (48,58) | `f755ebd9c24b5859` | 56 |
| glassscorpion | 127x65 | (58,59) | `68df6d7bc7e92163` | 48 |
| sunvulture | 97x70 | (42,64) | `0addc31949bc9bc1` | 57 |
| dunecolossus | 137x120 | (59,114) | `7ec69756ab55998c` | 112 |
| mirageroc | 143x153 | (69,147) | `e886af6943869891` | 141 |

Art scale (`SCALE`) was set by comparing each kind's idle size with the old art's, not from an in-game screenshot: elites are deliberately the biggest (colossus 1.4x, roc 1.25x). Only the Mirage Roc hovers (lowest living pixel at least 12 px above the anchor row, settles on the ground row on death). The other five are grounded; `frame()` rests the lowest pixel on the anchor row.

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

## Checks
`tests/lapis-slime-art.cjs` (126 checks, passing): production loading, the five untouched NPCs, portraits, timings, borders, eight distinct attacks and deaths with a reaching strike, anchor-row grounding (the roc hovers, then settles), planted feet, health-bar tops, no browser errors. Run it with `scripts/test-touch-bounded.sh` and, in the SAME command, `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`, `NODE_PATH=<main>/node_modules:~/webserver/www/dybase2/node_modules`, `VALHALLA_BINARY=<main>/target/release/valhalla-server`; `SOFT_CHECKS=1` lists every failure. Mutation: `MUTATE_KIND=sunvulture MUTATE_PNG=<original atlas> LAPIS_ART_KINDS=sunvulture` fails as required. `tests/lapis-ui.cjs` now reads each kind's expected atlas size from `Field.frameOf` (it asserted 768x480 for all eleven); it has not been run. `python3 scripts/lapis_slime_review.py review|verify|upload` (pictures `valhallasc-lapis-*`; upload is a separate, explicit step and has NOT been done).

## Likely veto points
The roc's wings read like a fanned peacock tail; the sandhopper and vulture are smaller than the old art; the roc's last two death frames are nearly empty by design; the scorpion's claws are plain.
