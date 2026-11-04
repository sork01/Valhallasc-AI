# The Ribbonwild enemy artwork (candidate, not deployed)

**Status:** candidate built 2026-11-04 on `feat/ribbonwild-slime-art` in `/media/raid/valhallasc-data/ribbonwild-slime-work`, client-only, **not merged**: deployment waits for the owner. The Ribbonwild is zone 21 in the docs and index 20 in `world/map.txt`; look it up by name in tests.

**Owner direction (2026-11-04):** every enemy unique and mean, no shared round-eye-plus-blush face. The old Ribbonwild art was the worst case (googly eyes on every kind, blush on the jesterling and the colossus). Each kind has its own face routine: bulging lidded eye with a vertical slit pupil over a toothed gape and a lashing tongue (gecko), faceted red compound eyes over hooked mandibles (beetle), a pinprick eye in a bare white face patch under a scarlet brow over a tall hooked beak (macaw), hollow dark sockets with red glints over a painted needle-tooth grin (jesterling), a hard yellow raptor glare under a heavy brow over a screaming hooked beak (gryphon), and a cracked porcelain mask with hollow sockets, ember pinpoints and a jagged black mouth (colossus). No blush anywhere. Ribbons, strings, bells and plumes are attached to the body, never loose glyphs. Defaults chosen without asking (veto welcome): only the Balloon Beetle hovers; Parade Gryphon and Mask Colossus are the two elites (as in `items::is_elite`) and the biggest; sizes follow the originals' footprint, judged on the before/after sheet and one in-game screenshot (the gecko is about hero-sized in length; the other five kinds were not inspected in-game).

| kind | look | attack | death |
|---|---|---|---|
| ribbongecko | low teal wall-gecko, pale belly, magenta back-frill, ribbon-bow tail tip, bulging amber slit-pupil eye under a heavy lid, toothed gape | crouches, then lunges with the jaw wide and the tongue lashing out, front claws forward | goes slack and flat, legs splayed, tongue lolling, eye crossed (soft body, so it may squash) |
| balloonbeetle | armoured violet beetle with a brass seam and studs, red compound eyes under a plated brow, hooked bone mandibles, a red and a blue balloon tied to the shell (hovers) | tilts back with the mandibles spread, then dives forward and snaps them shut | the balloons pop and hang as rags, it falls, the shell cracks and it lands on its back (rigid: no squash) |
| paintedmacaw | scarlet macaw on thin talons, white face patch, pinprick pale-gold eye, tall hooked dark beak, folded blue and gold wing, barred tail | head drawn back with the wings flared, then it strikes forward and down, beak wide | topples forward, wing and tail feathers splayed over the ground |
| jesterling | pale painted jester in a harlequin tunic, ruffled collar, three-bell cap, hollow sockets with red glints, needle-tooth grin, curved knife | knife cocked back behind the head, then a long forward slash | knees buckle and it folds into a heap of cloth, cap and bells |
| paradegryphon (elite) | lion body, violet eagle head with a hooked amber beak and a raptor glare, crest of red, gold, teal and pink plumes, banded wings with streamers | rears with the wings flared, then rakes both talons forward and drops the head | collapses onto its belly with the wings and plumes spread flat |
| maskcolossus (elite) | robed giant, gold sash, ruffled collar, white-gloved fists, crowned cracked porcelain mask with tall hollow sockets, ember pinpoints and a jagged black mouth | both fists raised overhead, then slammed forward | the mask splits in two, the crown rolls off and the body slumps into a heap (rigid: no squash) |

## Files and frames
The six enemies share `client/assets/ribbonwild.txt` with three **NPCs** (`ribbon_host`, `ribbon_keeper`, `ribbon_travel`, 96x96, tops 80/83/81). `export` merges only the six enemy entries and asserts the NPCs' sprite ids and tops are unchanged and that they have no `kindFrames` entry; the manifest keeps its nine-kind `kinds` order and the zone-wide `frame [96,96]`/`anchor [48,90]` the NPCs use. Per-kind frames (`KIND_FRAMES`, art scale in `SCALE`, tuned with `extents`); a size change needs a NEW PixelFlow source: remove the kind from `scripts/ribbonwild_slime_sources.txt` and run `SOURCE_SUFFIX=_x python3 scripts/ribbonwild_slime_redraw.py build`.

| kind | frame | anchor | PixelFlow source | idle size (old) |
|---|---|---|---|---|
| ribbongecko | 128x40 | (59,34) | `34dddc1baab0761b` | 93x32 (72x53) |
| balloonbeetle | 92x99 | (40,93) | `bdad37a853357e8d` | 57x72 (57x74) |
| paintedmacaw | 100x80 | (46,74) | `cce66e3246600b01` | 65x69 (54x79) |
| jesterling | 88x86 | (26,80) | `2fa9c4920f43be8e` | 39x77 (48x77) |
| paradegryphon | 129x88 | (63,82) | `b6039b7b2b193ac7` | 86x74 (74x71) |
| maskcolossus | 120x96 | (41,90) | `e5fb7e1d82a96e2d` | 66x89 (76x85) |

```sh
python3 scripts/ribbonwild_slime_redraw.py preview|montage [kinds]   # contact sheets
python3 scripts/ribbonwild_slime_redraw.py extents [kinds]           # measure on a scratch canvas
python3 scripts/ribbonwild_slime_redraw.py build                     # create missing sources
python3 scripts/ribbonwild_slime_redraw.py refresh <kinds>           # rewrite same-size sources
python3 scripts/ribbonwild_slime_redraw.py export                    # editor frames -> atlas, manifest, tops (merges)
python3 scripts/ribbonwild_slime_redraw.py verify
```
`make_ribbonwild_sprites.py` keeps its helpers but its CLI delegates here and refuses `--replace` (its old `build --replace` deleted whatever PixelFlow ids the manifest named and rewrote the manifest at 96x96). `ribbonwild_cel_redraw.py` is untouched (the old art). The three NPCs keep their old sources.

**Hover:** only the Balloon Beetle hovers. Every living frame keeps its lowest pixel at least 12 px above the anchor row; its death falls to the ground row and settles on its back. `frame()` asserts both. Wing and plume feathers use `feather_fan`; the beetle's balloons are `balloon()`.
**Walk frames:** the shared `curves()` is wrapped to offset the walk phase by 0.45 rad, so no two of the eight walk frames mirror each other.
**Borrowed art:** none. `es_foe_*` shades of this zone use their own data.

## Rollback
```sh
python3 scripts/rollback_ribbonwild_art.py --target /path/to/checkout            # dry run
python3 scripts/rollback_ribbonwild_art.py --target /path/to/checkout --apply
```
Backup `/media/raid/valhallasc-data/ribbonwild-slime-original-20261104` (seven files: the manifest and six atlases, hashes, old PixelFlow ids in `manifest.txt`); every hash is checked before any write, a corrupt backup is refused, and the restore stops if an NPC entry in the live manifest differs from the backup's.

## Checks
`tests/ribbonwild-slime-art.cjs` (124 checks, `scripts/test-touch-bounded.sh`, `REAL_SPRITES=1`, `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`, `VALHALLA_BINARY` = main release binary, `NODE_PATH` from main): production loading, the three untouched NPCs (ids, tops, 96x96, 768x480), portraits, timings, borders, eight distinct attacks and deaths with a reaching strike, anchor-row grounding (the beetle: hover above row, settle on death), planted feet for gryphon and colossus, health-bar tops, no browser errors. `SOFT_CHECKS=1` lists every failure instead of stopping at the first. Mutation: `RIBBONWILD_ART_KINDS=ribbongecko MUTATE_KIND=ribbongecko MUTATE_PNG=<backup>/client/assets/ribbonwild_ribbongecko.png` fails as required. `tests/ribbonwild-ui.cjs` now compares atlases to `Field.frameOf` (syntax checked only). `scripts/ribbonwild_slime_review.py review|verify|upload` builds the 29 FileDrop pictures, checks the 204 editor/export frames, rollback with its corrupt-backup and NPC-tamper refusals, that the destructive build is refused, and that the live art and NPCs are untouched. No encounter or balance testing was run.
