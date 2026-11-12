# Yearwheel enemy art candidate

Owner accepted all enemy sprites on 2026-11-12. Integrated for Beta 1.44.0; see
[the combined release](enemy-sprites-release.md). The private-candidate status
below records the original review stage and is superseded by that approval.

Private candidate on `feat/yearwheel-slime-art`, checkout `/media/raid/valhallasc-data/yearwheel-slime-work` (uncommitted, not deployed, no version bump). Sixteen new native, editable PixelFlow sources replace the sixteen cel-shaded enemies in `client/assets/yearwheel.txt`. The eight season NPCs (`year_*_keeper`, `year_*_travel`), the Equinox Stag (`yearwheelelites*`), world data and combat behaviour are untouched.

Each source has 34 frames (idle 6, walk 8, attack 8, hurt 4, die 8, 10 fps). Frames are 192x160 anchored (96,152) for the long kinds (brooknewt, bloomtortoise, petalchimera, sundarter, glasslion, snowstoat, rimesaber, ambermantis, longnightwyrm) and 176x172 anchored (88,164) for the rest; both are under PixelFlow's per-frame cap. Per-kind `SCALE` makes each idle match the old idle size. The shared fallback frame stays 96x96 at (48,90).

| Season | Kind | Attack | Death |
|---|---|---|---|
| Spring | Brook Newt | head draws back, then a long toothed lunge | legs splay, belly and tail settle, tongue out |
| | Bloom Tortoise | head pulls into the shell, then snaps out | rigid shell cracks, flowers wilt and drop |
| | Petal Chimera | crouch, pounce with jaw and claws, tail-snake strikes | knees fold, petals scatter, lies down |
| | Rain Seraph (flies) | wings back, water orb thrown as a spray of drops | dissolves in a dither and falls as rain into a puddle |
| Summer | Sun Dart | coils back, snaps forward | sail droops, body lowers |
| | Glass Lion | crouch, pounce and swipe | crystal mane shards break loose, lies down |
| | Sunwheel (flies) | spins up, rays lengthen, lunges | flames die: gold to ember to grey cinder, falls and rolls |
| | Fire Phoenix (flies) | wings sweep back, neck and flame breath forward | flames gutter to ash grey and it drops |
| Autumn | Acorn Mimic | cap hinges open on a toothed maw, then chomps | the shell splits into two halves |
| | Lantern Owl (flies) | wings back, swoops swinging the lantern | lantern goes dark, owl tumbles down |
| | Harvest Reaper | scythe raised behind, then a sweep down | robe collapses into a heap, hat and scythe drop |
| | Amber Mantis | claws cocked, then a long slash | legs buckle, body tips forward, claws drop |
| Winter | Snow Stoat | arched crouch and lunge | flops flat |
| | Rime Saber | pounce with great ice fangs | collapses forward |
| | Snow Giant | club overhead, then a slam | slumps to his knees into a snowdrift |
| | Longnight Wyrm | neck coils back, long bite | coils release along the floor, head lowers |

Flyers (rainseraph, sunwheel, firephoenix, lanternowl) hover at least 12 px above the anchor row in every living frame and settle on it at the end of death; grounded kinds rest exactly on the anchor row in every frame. Faces are per kind (slit eyes, fangs, scowls), no shared round-eye template and no blush on the aggressive kinds.

```sh
python3 scripts/yearwheel_slime_redraw.py preview [KIND...]   # YW_LAX=1 lists problems instead of stopping, YW_ZOOM, YW_COLS
python3 scripts/yearwheel_slime_redraw.py extents [KIND...]
python3 scripts/yearwheel_slime_redraw.py build               # creates unregistered sources only
python3 scripts/yearwheel_slime_redraw.py refresh KIND...     # re-draws a saved source, then export and verify
python3 scripts/yearwheel_slime_redraw.py export
python3 scripts/yearwheel_slime_redraw.py verify
python3 scripts/yearwheel_slime_review.py review | verify | upload
```

`make_yearwheel_sprites.py` keeps its helpers but its CLI delegates here; `build --replace` is refused.

**Face pass (2026-11-11):** each kind now has its own eye shape (`eye()` in `yearwheel_slime_redraw.py`: goat bar pupil on the Chimera, faceted crystal on the Glass Lion, hollow glow under a heavy brow on the Rime Saber, vertical-pupil bead, big round owl/bird eyes, jack-o'-lantern triangles, blank orbs on the Seraph, coal dots, star glints; slit eyes remain only on the Newt, Tortoise, Acorn, Sunwheel, Stoat), the three cats have different heads, the Rain Seraph has a swept-hair, two-eyed face, and Sunwheel (rays that point down are short) and Lantern Owl (shorter lantern cord) hover about 15 px lower. Re-checked: four bounded batches, 330 assertions, 0 failures.

Backup: `/media/raid/valhallasc-data/yearwheel-slime-original-20261111` (16 atlases, `yearwheel.txt`, old PixelFlow IDs and tops, hashes). `python3 scripts/rollback_yearwheel_art.py --target <checkout> [--apply]` restores the 17 files, refusing a corrupt backup or changed NPC/other manifest data.

Browser check: `tests/yearwheel-slime-art.cjs` through `scripts/test-touch-bounded.sh` (`REAL_SPRITES=1`, the main checkout's `target/debug` binary, `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`, main `node_modules` on `NODE_PATH`). Run four kinds at a time with `YEARWHEEL_ART_KINDS=a,b,c,d`. `MUTATE_KIND=brooknewt MUTATE_PNG=<backup>/client/assets/yearwheel_brooknewt.png YEARWHEEL_ART_KINDS=brooknewt` must fail. The client loads `yearwheel_<kind>.png?v=cel1`: the mutation route glob needs the trailing `*`.

## Verification (2026-11-11)

- All 544 saved editor cels equal the exported frames (`verify`); rollback to 17 files, corrupt-backup and NPC-tamper refusal pass (`review verify`, receipt `test-results/yearwheel-slime/validation.json`).
- Bounded browser check in four season batches: 83 + 83 + 81 + 83 passing assertions, no failures, no oom-kill. The first run flagged two real issues, fixed and re-exported: Brook Newt's wind-up silhouette was too small, Rain Seraph did not recover to its idle silhouette; the Harvest Reaper idle did not animate. Old-brooknewt-atlas mutation fails at the production frame lookup.
- 73 review pictures/animations generated in `test-results/yearwheel-slime/` (`valhallasc-yearwheel-*`). All 73 pictures/GIFs uploaded to FileDrop by the owner with matching hashes (the auto-mode classifier had denied the agent's own upload run).

Saved sources: brooknewt `fc067e2389b30046`, bloomtortoise `f756db696158ea35`, petalchimera `ac59c455f6ec0be7`, rainseraph `7be03a87ef9a5b21`, sundarter `1e28ca147e7c0181`, glasslion `a4868fb465fa0962`, sunwheel `e318b0f09fcb4ecd`, firephoenix `e9f3000419bcd003`, acornmimic `582bd5acc8f00a26`, lanternowl `c836a8c70ebf70ca`, harvestreaper `d803941942715dff`, ambermantis `fbdad2f694f01b05`, snowstoat `830603779d4c60ba`, rimesaber `82ef18e108129524`, snowgiant `e073a605224ef33a`, longnightwyrm `b26fbcb9e6647bea`.
