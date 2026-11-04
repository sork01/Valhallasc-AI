# The Sunward Vale enemy artwork (deployed, Beta 1.39.27)

**Status:** deployed 2026-11-04 as Beta 1.39.27 (merge `7a7ad39`, client-only, owner said "deploy"). Built on `feat/sunward-slime-art` in `/media/raid/valhallasc-data/sunward-slime-work`. Sunward Vale is zone 20 in the docs and index 19 in `world/map.txt`; look it up by name in tests.

**Owner direction (2026-11-04):** every enemy unique and mean, no shared round-eye-plus-blush face. Each kind has its own face routine: one bloodshot mad eye under a heavy brow over bared chisel teeth (meadowhare), two hooked-pupil eyestalks over a toothed rasp mouth (sunbacksnail), a narrow amber vertical slit under a dark brow over a bared muzzle (brushfox), a tiny hard eye under a white brow stripe in a black mask over a tusked snarl (spadebadger), a dark socket with one ember pinpoint under a scarred brow over a comb-toothed jaw trailing honey (honeyjaw), and two hollow angled ember slots plus a zigzag mouth slot in a woven face under a ragged hat (wickerwarden). No blush anywhere. Drips are strands attached to the jaw or claws, never loose glyphs. Defaults chosen without asking (veto welcome): all six stand on the ground, nothing hovers; Honeyjaw and Wicker Warden are the two elites (as in `items::is_elite`) and are clearly the biggest.

| kind | look | attack | death |
|---|---|---|---|
| meadowhare | grey-brown hunched hare: big haunch, long flat hind foot, torn ears, scar across the nose, bared chisel teeth | coils low with ears flat, then lunges, hind legs thrown back, front claws forward, jaws wide | flops onto its side, legs stiff and straight, ears droop, eye crossed |
| sunbacksnail | sun-gold spiral shell edged with thorns on sickly green flesh, hooked-pupil eyestalks, rasp mouth | rears its neck high, then drives the whole head forward with the rasp gaping | the soft body pulls into the shell, the rigid shell tips over and cracks, goo spreads (no squash) |
| brushfox | rust-orange stalker, black socks, white-tipped brush, narrow amber slit eye, bared fangs, black ears | crouches with ears flat, then pounces with front claws forward and jaws open | yelps and rolls onto its back, legs in the air, tongue out |
| spadebadger | low slate-grey digger, white-striped black mask, tusks, four huge spade claws per paw | rears both claws overhead, then rakes them down and forward in a spray of dirt | collapses forward, face and claws in the dirt, rump sinks |
| honeyjaw (elite) | hulking hive-bear: honeycomb hive grown over its back, sunken ember eye, scarred snout, hanging comb-toothed jaw with honey strands | rears up, arms overhead and jaw wide, then hammers both paws down so honey splashes along the ground | staggers back and falls over onto its back, the hive splits and honey spreads across the ground |
| wickerwarden (elite) | tall woven-cane giant: basket skull, ragged straw hat, hollow ember slots, zigzag mouth, straw-bound limbs, rusted scythe | scythe drawn back high behind it, then swung down in a long arc in front | the embers die, knees buckle and the body unravels into a heap of cane and straw under its hat, scythe fallen across it |

## Files and frames
The six enemies share `client/assets/sunward.txt` with three **villager NPCs** (`sun_miller`, `sun_keeper`, `sun_travel`, 96x96, tops 83). `export` merges only the six enemy entries and asserts the villagers' sprite ids, tops and frames are unchanged; the manifest keeps its nine-kind `kinds` order and the zone-wide `frame [96,96]`/`anchor [48,90]` the villagers use. Per-kind frames (`KIND_FRAMES`, art scale in `SCALE`, tuned with `extents`; a size change needs a NEW PixelFlow source: remove the kind from `scripts/sunward_slime_sources.txt`, `SOURCE_SUFFIX=_x ... build`). Idle sizes are close to the originals' (Honeyjaw 72x81 vs 72x81, Warden 86x91 vs 60x83 with the scythe, Hare 74x71 vs 61x79); judge them on an in-game screenshot and rescale before the sources are created, not after.

| kind | frame | anchor | PixelFlow source |
|---|---|---|---|
| meadowhare | 122x78 | (56,72) | `eef89dbdde8bfb60` |
| sunbacksnail | 112x65 | (39,59) | `cbf04647fe1bcdac` |
| brushfox | 124x92 | (56,86) | `a9f4e0b994c6a159` |
| spadebadger | 122x73 | (36,67) | `dab9c4728edb6924` |
| honeyjaw | 167x113 | (89,107) | `2715096a2bd9a48a` |
| wickerwarden | 130x135 | (41,129) | `5cc997243e029bb6` |

```sh
python3 scripts/sunward_slime_redraw.py preview|montage [kinds]   # contact sheets
python3 scripts/sunward_slime_redraw.py extents [kinds]           # measure on a scratch canvas
python3 scripts/sunward_slime_redraw.py build                     # create missing sources
python3 scripts/sunward_slime_redraw.py refresh <kinds>           # rewrite same-size sources
python3 scripts/sunward_slime_redraw.py export                    # editor frames -> atlas, manifest, tops (merges)
python3 scripts/sunward_slime_redraw.py verify
```
`make_sunward_sprites.py` keeps its helpers but its CLI delegates here and refuses `--replace` (its old `build --replace` deleted whatever PixelFlow ids the manifest named). `scripts/repair_spadeclaw_walk.py` (a one-off for the old art) now refuses to run. `sunward_cel_redraw.py` is untouched (the old art). `render_sunward_gallery.py` still crops 96x96 cells (an old promo picture); do not use it for the new atlases.

**Gait (SPADECLAW-WALK):** the Badger's front claws stride opposite the hind feet (diagonal gait). `spadebadger()` records each leg's ground x in `LEGS`; `sunward_slime_review.py verify` asserts all four legs move at least 6 px and each near/far diagonal pair is in opposite phase (correlation < -0.9). The browser check only asserts that front and hind both stride, because a pixel mean over a pair of legs in opposite phase cancels out.
**Walk frames:** the shared `curves()` is wrapped to offset the walk phase by 0.45 rad, so no two of the eight walk frames mirror each other.
**Borrowed art:** none. `es_foe_*` shades of this zone use their own data.

## Rollback
```sh
python3 scripts/rollback_sunward_art.py --target /path/to/checkout            # dry run
python3 scripts/rollback_sunward_art.py --target /path/to/checkout --apply
```
Backup `/media/raid/valhallasc-data/sunward-slime-original-20261104` (seven files: the manifest and six atlases, hashes, old PixelFlow ids in `manifest.txt`); every hash is checked before any write, a corrupt backup is refused, and the restore stops if a villager entry in the live manifest differs from the backup's.

## Checks
`tests/sunward-slime-art.cjs` (127 checks, `scripts/test-touch-bounded.sh`, `REAL_SPRITES=1`, `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`, `VALHALLA_BINARY` = main release binary, `NODE_PATH` from main): production loading, the three untouched villagers (ids, tops, 96x96, 768x480), portraits, timings, borders, eight distinct attacks and deaths with a reaching strike, every living and death frame exactly on the anchor row (no flyer here), planted feet for fox, bear and warden, Badger front and hind stride, health-bar tops, no browser errors. `SOFT_CHECKS=1` lists every failure instead of stopping at the first. Mutation: `SUNWARD_ART_KINDS=meadowhare MUTATE_KIND=meadowhare MUTATE_PNG=<backup>/client/assets/sunward_meadowhare.png` fails as required. `tests/sunward-ui.cjs` now compares atlases to `Field.frameOf` (syntax checked only). `scripts/sunward_slime_review.py review|verify|upload` builds the 29 FileDrop pictures, checks the 204 editor/export frames, rollback with its corrupt-backup and villager-tamper refusals, the Badger gait, and that the live art and villagers are untouched. No encounter or balance testing was run.
