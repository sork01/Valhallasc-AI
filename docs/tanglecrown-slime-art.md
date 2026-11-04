# The Tanglecrown enemy artwork (candidate, not deployed)

**Status:** candidate built 2026-11-04 on `feat/tanglecrown-slime-art` in `/media/raid/valhallasc-data/tanglecrown-slime-work`, client-only, **not merged**: deployment waits for the owner. The Tanglecrown is zone 22 in the docs and index 21 in `world/map.txt`; look it up by name in tests.

**Owner direction (2026-11-04):** every enemy unique and mean, no shared round-eye-plus-blush face. This overrides the older "big eyes with highlight, blush" wording in the TODO tasks. The old Tanglecrown art gave every kind googly round eyes. Each kind has its own face routine: a dark brow scale over a small glaring slit eye above a row of heat pits and a hinged fanged gape with a forked tongue (jadeanaconda); a flat snarling muzzle with a mint almond eye in a dark mask, black tear mark, bared canines and a crown of jade thorns (crownjaguar); a wide triangular head with long slanted glossy bulb eyes, one dark pseudopupil each, under angry ridges over crossed mandibles (orchidmantis); a black mask band with narrowed gold glaring eyes, tall ears and needle teeth (canopyglider); a small ember glint on a raised turret under an armoured brow ridge, with upper and lower teeth showing even when the jaw is shut (poolcaiman); and deep-set red glints in shadow under a brow shelf over a jutting jaw with two upturned tusks (drumgorilla). No blush anywhere. Effects are attached to the body, never loose glyphs.

| kind | look | attack | death |
|---|---|---|---|
| jadeanaconda (elite) | three heaped jade coils with black saddles and gold dots, a raised S-curved neck, a wedge head with gold crown spines | the head pulls back in a tight S, then darts forward and down with the jaws wide, fangs out and the tongue lashing | the head drops, the coils unwind and it lies out flat along the ground with the tongue lolling (soft body, so it may flatten) |
| crownjaguar (elite) | heavy gold black-rosetted cat, thorn crown of jade, bared canines | crouches low, then pounces with the forepaws reaching and the claws out and the jaws open | collapses onto its belly, legs splayed, head down, tail limp |
| orchidmantis | upright lime chitin body, pink and gold orchid-petal wings and knee lobes, spined raptorial forelegs | the forelegs cock up behind the head, then snap down and forward | the chitin buckles, it tips over backwards with legs curling in, petals splayed (rigid: no squash) |
| canopyglider (hovers) | teal fur, tan membranes between wrist and ankle, ringed brush tail | climbs and tucks, then dives claws first with the wing reaching forward | the membranes crumple, it tumbles and lands in a heap on the ground row |
| poolcaiman | low armoured bog-green croc, keeled scutes and tail, moss tufts | the head rears back with the jaws agape, then snaps forward | rolls belly-up with the legs kicking in the air and the jaws slack (armoured: no squash) |
| drumgorilla | charcoal silverback, silver saddle, war drum on a strap, bone drumsticks | both sticks hauled overhead, then slammed down on the drum | topples over backwards, the drum rolling off ahead of it |

## Files and frames
The six enemies share `client/assets/tanglecrown.txt` with three **NPCs** (`tangle_warden`, `tangle_scholar`, `tangle_travel`, 96x96, tops 82/83/81). `export` merges only the six enemy entries and asserts the NPCs' sprite ids and tops are unchanged and that they have no `kindFrames` entry; the manifest keeps its nine-kind `kinds` order and the zone-wide `frame [96,96]`/`anchor [48,90]` the NPCs use. Per-kind frames (`KIND_FRAMES`, art scale in `SCALE`, tuned with `extents`); a size change needs a NEW PixelFlow source: remove the kind from `scripts/tanglecrown_slime_sources.txt` and run `SOURCE_SUFFIX=_x python3 scripts/tanglecrown_slime_redraw.py build`.

| kind | frame | anchor | PixelFlow source | idle size (old) |
|---|---|---|---|---|
| jadeanaconda | 143x79 | (47,73) | `6c0f21091489e300` | 90x64 (72x65) |
| crownjaguar | 131x62 | (55,56) | `e4055986ab09dadd` | 95x54 (65x69) |
| orchidmantis | 136x98 | (93,92) | `b752928703c276aa` | 52x86 (58x82) |
| canopyglider | 94x98 | (46,92) | `5f9c32b1eba65894` | 77x61 (77x53) |
| poolcaiman | 130x38 | (57,32) | `a2fd6b4d3f18e568` | 96x25 (84x41) |
| drumgorilla | 143x114 | (90,108) | `d51226f63f5d397d` | 59x72 (70x66) |

```sh
python3 scripts/tanglecrown_slime_redraw.py preview|montage [kinds]   # contact sheets
python3 scripts/tanglecrown_slime_redraw.py extents [kinds]           # measure on a scratch canvas
python3 scripts/tanglecrown_slime_redraw.py build                     # create missing sources
python3 scripts/tanglecrown_slime_redraw.py refresh <kinds>           # rewrite same-size sources
python3 scripts/tanglecrown_slime_redraw.py export                    # editor frames -> atlas, manifest, tops (merges)
python3 scripts/tanglecrown_slime_redraw.py verify
```
`make_tanglecrown_sprites.py` keeps its helpers but its CLI delegates here and refuses `--replace`. `tanglecrown_cel_redraw.py` is untouched (the old art). The three NPCs keep their old sources.

**Hover:** only the Canopy Glider hovers. Every living frame keeps its lowest pixel at least 12 px above the anchor row; its death falls to the ground row. `frame()` asserts both. **Roll and tumble helpers:** `FlipRig` rolls the caiman over its long axis (y scaled by cos), `Rig` tips the mantis and gorilla over, `HeadRig` enlarges a head about its own centre so small bodies carry menacing faces. Hardly any code is shared with the Ribbonwild redo and no face routine is shared with any zone.
**Walk frames:** the shared `curves()` is wrapped to offset the walk phase by 0.45 rad, so no two of the eight walk frames mirror each other.
**Borrowed art:** none. The `es_foe_18` shades in this zone use their own data.

## Rollback
```sh
python3 scripts/rollback_tanglecrown_art.py --target /path/to/checkout            # dry run
python3 scripts/rollback_tanglecrown_art.py --target /path/to/checkout --apply
```
Backup `/media/raid/valhallasc-data/tanglecrown-slime-original-20261104` (seven files: the manifest and six atlases, hashes, old PixelFlow ids in `manifest.txt`); every hash is checked before any write, a corrupt backup is refused, and the restore stops if an NPC entry in the live manifest differs from the backup's.

## Checks
`tests/tanglecrown-slime-art.cjs` (`scripts/test-touch-bounded.sh`, `REAL_SPRITES=1`, `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`, `VALHALLA_BINARY` = main release binary, `NODE_PATH` from main): production loading, the three untouched NPCs (ids, tops, 96x96, 768x480), portraits, timings, borders, eight distinct attacks and deaths with a reaching strike, anchor-row grounding (the glider: hover above the row, settle on death), planted feet for the jaguar, caiman and gorilla, health-bar tops, no browser errors. `SOFT_CHECKS=1` lists every failure instead of stopping at the first. Mutation: `MUTATE_KIND=<kind> MUTATE_PNG=<original atlas>` must fail. `tests/tanglecrown-ui.cjs` and `tests/zones22-39-sprites-ui.cjs` read each kind's atlas size from `Field.frameOf`.
Review pictures: `python3 scripts/tanglecrown_slime_review.py review|verify|upload` (upload is a separate, explicit step; pictures are named `valhallasc-tanglecrown-*`).
