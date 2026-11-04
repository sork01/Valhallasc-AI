# The Moonwell enemy artwork (candidate, owner approval pending)

**Status:** private candidate on `feat/moonwell-slime-art` in `/media/raid/valhallasc-data/moonwell-slime-work`. Not deployed, no version bump until the owner has seen the FileDrop pictures and approved. Client-only. The Moonwell is zone 18 in the docs and index 17 in `world/map.txt`; look it up by name in tests.

**Owner direction (2026-11-04):** every enemy unique and mean, no shared round-eye-plus-blush face. Each kind has its own eye routine: faceted compound eyes (dew_moth), blind milky eyes under a bone brow (lumen_eel), two pinpoint lights inside the dark of a bell (rootbell), a slit-pupil raptor eye (tideglass_heron), hollow skull sockets (hourpetal_stag), one vertical seam eye over a stitched mouth (moonskein_weaver), angular shard sockets over a glowing fissure (moonwell_echo). No `slit()` reuse and no blush. Defaults chosen without asking (veto welcome): dew_moth, lumen_eel and the Echo hover; the other four stand on the ground; heron, stag and weaver are the elites, the Echo is the final boss.

| kind | look | attack | death |
|---|---|---|---|
| dew_moth (hovers) | dew-drop mosquito-moth: glassy teardrop abdomen, four swept blade wings with dew beads, faceted eyes, needle proboscis | rears back, dives and stabs in a dew spray | abdomen bursts, wings fold, drops into a puddle |
| lumen_eel (hovers) | anglerfish-eel: hooked lure, blind eyes, needle-tooth jaw, glowing lateral lights | coils into an S, darts with jaw wide | lights go out, sinks limp, jaw open |
| rootbell | weathered bronze bell on gnarled roots, seedling crown, dark visor and toothed maw, clapper tongue | rears up, slams down in a clang ring | cracks run up the bell, it topples, seedling wilts |
| tideglass_heron (elite) | gaunt glass-feathered heron, stilt legs, dagger beak, shard crest | coils the neck, spears forward in a glass spray | shatters into a heap of shards |
| hourpetal_stag (elite) | violet stag with a skull face, bared fangs, scythe antlers with petal blooms, hourglass flank | lowers the antlers and gores | kneels, rolls over, sand runs out, petals fall |
| moonskein_weaver (elite) | tall stilt-legged puppeteer: thread-wound spindle, porcelain mask, four needle arms, orbiting beads | arms cross back, all four needles thrust | thread unravels into a heap, mask on top |
| moonwell_echo (boss, hovers) | cracked mirror wraith: shard mask, orbiting shards, hanging shard cloak | draws its shards in, hurls them | face splits, shards burst outward and fall into a heap |

## Files and frames
Two manifests are kept so `field.js` needs no change: `client/assets/moonwell.txt` (the Echo, atlas `moonwell_echo.png`) and `client/assets/moonwell_garden.txt` (six kinds, `moonwell_<kind>.png`). Per-kind frames (`KIND_FRAMES`, art scale in `SCALE`, tuned with `extents` and an in-game screenshot; a size change needs a NEW PixelFlow source: remove the kind from `scripts/moonwell_slime_sources.txt`, `SOURCE_SUFFIX=_x ... build`). Superseded sources are in `scripts/moonwell_slime_sources_superseded.txt`.

| kind | frame | anchor | PixelFlow source |
|---|---|---|---|
| dew_moth | 100x90 | (39,84) | `e7398d89791d45c1` |
| lumen_eel | 128x77 | (55,71) | `98476b90e0aa779a` |
| rootbell | 103x63 | (41,57) | `dfb31e19bf6b2c75` |
| tideglass_heron | 138x83 | (48,77) | `ec54d26e3542dbb8` |
| hourpetal_stag | 147x100 | (43,94) | `ca46ce18eb3e8c3b` |
| moonskein_weaver | 87x83 | (35,77) | `17c46d9a130f0958` |
| moonwell_echo | 168x115 | (74,109) | `f961f9c017e35657` |

```sh
python3 scripts/moonwell_slime_redraw.py preview|montage [kinds]   # contact sheets
python3 scripts/moonwell_slime_redraw.py extents [kinds]           # measure on a scratch canvas
python3 scripts/moonwell_slime_redraw.py build                     # create missing sources
python3 scripts/moonwell_slime_redraw.py refresh <kinds>           # rewrite same-size sources
python3 scripts/moonwell_slime_redraw.py export                    # editor frames -> atlases, manifests, tops
python3 scripts/moonwell_slime_redraw.py verify
```
`make_moonwell_sprites.py` and `make_moonwell_garden_sprites.py` keep their helpers but their CLIs delegate here and refuse `--replace`. Do not run two sessions' builds at once in this worktree (it happened once and duplicated PixelFlow sources).

## Rollback
```sh
python3 scripts/rollback_moonwell_art.py --target /path/to/checkout            # dry run
python3 scripts/rollback_moonwell_art.py --target /path/to/checkout --apply
```
Backup `/media/raid/valhallasc-data/moonwell-slime-original-20261104` (nine files, hashes, old Echo PixelFlow id `38fdfdff9a8a8bcc`); every hash is checked before any write and a corrupt backup is refused.

## Checks
`tests/moonwell-slime-art.cjs` (145 checks, `scripts/test-touch-bounded.sh`, `REAL_SPRITES=1`, `VALHALLA_BINARY` = main release binary, `NODE_PATH` from main): production loading of both sources, portraits, timings, borders, eight distinct attacks and deaths, grounding (flyers hover and settle), health-bar tops. Mutation: `MOONWELL_ART_KINDS=dew_moth MUTATE_KIND=dew_moth MUTATE_PNG=<backup>/client/assets/moonwell_dew_moth.png` fails as required. `scripts/moonwell_slime_review.py review|verify|upload` builds the 33 FileDrop pictures, checks 238 editor/export frames and rollback incl. the corrupt-backup refusal. No encounter or balance testing was run.
