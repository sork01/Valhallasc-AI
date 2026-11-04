# Moonspore Canopy enemy artwork (candidate, owner approval pending)

**Status:** private candidate on `feat/moonspore-slime-art` in `/media/raid/valhallasc-data/moonspore-slime-work`. Not deployed, no version bump (main stays Beta 1.39.23) until the owner has seen the FileDrop pictures and approved.

**Owner direction (2026-11-04, asked before starting):** "i want them to look unique and mean. last few have all been the same. the circle as face etc." So the shared slime face (one big round glossy eye with a highlight, plus blush) is gone. Every kind has its own face and silhouette: slit and angular eyes under heavy brows, fangs, no blush. Shaded volume, props at least four pixels thick, no floating glyphs, eight distinct attack frames and eight distinct death frames per kind still apply. Lantern Wraith and Silkwing both hover (owner choice).

## The seven kinds
| kind | look | attack | death |
|---|---|---|---|
| glowcapgrazer | hunched mossy boar-beast, ridge of glowing toadstool caps and thorn spikes, bone brow, burning yellow slit eyes, two upturned tusks | rears its head back, then gores forward in a spore cloud | buckles, rolls over, caps wilt and shrivel |
| silkwing (hovers) | death's-head moth: tattered razor wings with glaring red slit false eyes, skull mark on the thorax, mandibles, feathered antennae | wings thrown up, then a slashing sweep shedding scales | wings fold, it spirals down and settles, wings crumpled |
| rootlurker | hunched bark root-thing, long clawed arms, antlers, knothole face with burning slit eyes and splinter teeth | rears up, rakes both claws down, bark spikes burst from the ground | splinters into logs and a heap of moss |
| lanternwraith (hovers) | hooded void-faced wraith, two narrow green slit eyes and a fanged grin, ragged cloak, skeletal hand with a hooked lantern | lifts the lantern and hurls a ghostfire orb | cloak unravels upward into wisps, lantern drops to the ground |
| mireheart (elite) | hulking bog-toad, heavy-lidded scowl, wide needle-tooth mouth, exposed pulsing heart in thorny rib roots | crouches and lashes a barbed tongue far out | heart goes dark, body deflates and slumps, tongue lolls |
| silverwidow (elite) | black-violet spider, silver crescent mark, six unequal burning eyes, venom fangs, eight thick jointed legs | rears on its hind legs, lunges a bite with a silk spray | legs curl in and it flips onto its back, belly up |
| nightbloom (elite) | carnivorous flower: plum maw lined with thorn teeth, two lime slit eyes, vine whips, root feet | arches back, snaps down, vines lash | wilts, the stem withers and bows, petals scatter |

## Frames
Per-kind frames (`KIND_FRAMES`, art scale in `SCALE`, both tuned with `extents`). The Mireheart tongue and Silver Widow legs are what fix the widths (max frame 192).

| kind | frame | anchor | PixelFlow source |
|---|---|---|---|
| glowcapgrazer | 154x75 | (52,69) | `15950f32d655bbdd` |
| silkwing | 117x114 | (52,108) | `ded9cc79f4bd454f` |
| rootlurker | 122x103 | (46,97) | `58847ba9630e32f8` |
| lanternwraith | 125x112 | (37,106) | `c4156f7d6c781e02` |
| mireheart | 185x82 | (49,76) | `0f44e83198435013` |
| silverwidow | 179x100 | (60,94) | `e6af029d8dccea81` |
| nightbloom | 98x105 | (36,99) | `c8bd1b84f8a1f941` |

(Frames may be re-tuned with `extents` after art edits; the manifest `kindFrames` is the truth.) Sources are in `scripts/moonspore_slime_sources.txt`; raw frames in `scripts/moonspore_slime_<kind>_raw.npz` (the older `moonspore_<kind>_raw.npz` are the original cel art, kept).

```sh
python3 scripts/moonspore_slime_redraw.py preview [kinds]   # contact sheets in test-results/moonspore-slime
python3 scripts/moonspore_slime_redraw.py extents           # measure each kind on a scratch canvas
python3 scripts/moonspore_slime_redraw.py build             # create missing sources (SOURCE_SUFFIX for a new size)
python3 scripts/moonspore_slime_redraw.py refresh <kinds>   # rewrite same-size sources, then export
python3 scripts/moonspore_slime_redraw.py export            # export saved editor frames and tops
python3 scripts/moonspore_slime_redraw.py verify            # compare editor and atlas
```
`scripts/make_moonspore_sprites.py` keeps its old helper functions (the sunward, ribbonwild, lapis, cairn, frostwake and stormglass makers import them) but its command line now delegates to the new pipeline and refuses `--replace`.

## Rollback
```sh
python3 scripts/rollback_moonspore_art.py --target /path/to/checkout            # dry run
python3 scripts/rollback_moonspore_art.py --target /path/to/checkout --apply
```
Backup `/media/raid/valhallasc-data/moonspore-slime-original-20261104` (eight files, hashes, old PixelFlow IDs and tops); every hash is checked before any write and a corrupt backup is refused.

## Checks
`tests/moonspore-slime-art.cjs` (145 checks, run with `scripts/test-touch-bounded.sh`, `REAL_SPRITES=1`, `VALHALLA_BINARY` = the main release binary): production loading, portraits, timings, borders, eight distinct attacks and deaths per kind, wind-up/strike motion, grounding (flyers hover and settle), feet on the ground, health-bar tops. `scripts/moonspore_slime_review.py review|verify|upload` builds the before/after pictures, checks 238 editor/export matches and rollback including the corrupt-backup refusal. No encounter or balance testing was run.
