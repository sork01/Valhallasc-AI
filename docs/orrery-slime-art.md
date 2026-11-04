# Obsidian Orrery enemy artwork

**Redo v2 (private candidate, owner approval pending; live is still Beta 1.39.22 v1).** The owner was not happy with the v1 art. Review of the v1 sheets found: the Bronze Mantis read as a dog or deer on post legs with tiny hook scythes; large parts were flat unshaded fills (Chronoguard shield, Matron gown, Gearling and Epoch Engine rims); spears, pendulum arms and gear stems were two pixels thin; attack and death frames used floating `+` glyphs; and the creatures looked small and plain. Source branch `feat/orrery-slime-redo` in `/media/raid/valhallasc-data/orrery-slime-redo-work`.

## What changed
- Every body part is shaded volume: `plate` (rim, mid, lit panel, bright core), `gear` (toothed shaded cog with domed face and hub) and `ball`. No flat polygons remain; props are at least four pixels thick.
- Bronze Mantis: triangular head with big glossy eyes, long prothorax, folded raptorial forelegs with spined steel blades, four slanted jointed legs in a diagonal trot (two feet always planted), verdigris wing case. The blades rise overhead and cut forward and down with a gold slash trail; death folds the legs and drops the blades.
- Gearling: steel ball inside a big copper rim gear with a winding key; rears back, charges with spinning rim and dust, dies as the rim breaks away and rolls off flat.
- Orbit Seer: bigger eyeball in two gyroscope rings (front and back halves drawn around the eye) with orbiting moons; charges a glowing pupil then fires a layered beam; dies by falling with its rings settling flat around it.
- Chronoguard: gear-badge shield with brass rim, crested helm with a pale face window (the black visor is gone), thick spear drawn back and thrust; dies kneeling as spear and shield fall flat.
- Pendulum Matron: shaded pleated gown with rolled hem, hair clusters, chained brass pendulum swung overhead and slammed forward; dies as the gown settles into a heap.
- Epoch Engine: clock-faced dome in a big rim gear on piston legs with foot pads and gear fists; raises both fists overhead and slams them down with debris; dies as pistons buckle and the rim breaks apart.
- No `+` glyph, spark or hover marker is drawn anywhere. Each kind has eight distinct attack and death frames.

## Sizes and sources
Per-kind frames (art scale per kind in `SCALE`: mantis .78, gearling .88, seer .88, chronoguard .86, matron .9, engine .82). Measured on the before/after sheet: the Gearling, Matron and Chronoguard are about the same height as v1; the mantis, Orbit Seer and Epoch Engine are larger. `boss_add_art_aliases.py` was rerun and left the tree byte-identical (nothing borrows Orrery art). `orrery-ui.cjs` and `zones13-15-sprites-ui.cjs` derive sizes from `Field.frameOf`, so they need no change.

| kind | frame | anchor | PixelFlow source |
|---|---|---|---|
| bronzemantis | 140x118 | (72,112) | `d8deff7f20671018` |
| gearling | 146x88 | (63,82) | `f45a47573ca3f3c4` |
| orbitseer | 164x92 | (66,86) | `57eabc8f2048b018` |
| chronoguard | 158x118 | (50,112) | `8479fa9767684a4d` |
| pendulummatron | 145x141 | (71,135) | `e678e2477460fd3d` |
| epochengine | 149x130 | (69,124) | `ce87725153993436` |

Earlier PixelFlow sources stay saved: v1 in `scripts/orrery_slime_v1_sources.txt`, the draft passes in `scripts/orrery_slime_draft_sources.txt`. A frame-size change needs a NEW source: build with `SOURCE_SUFFIX=_x` after removing the kind from the registry (`refresh` only rewrites same-size sprites).

```sh
python3 scripts/orrery_slime_redraw.py preview [kinds]   # contact sheets in test-results/orrery-slime
python3 scripts/orrery_slime_redraw.py extents           # measure each kind on a scratch canvas
python3 scripts/orrery_slime_redraw.py build             # create missing sources (SOURCE_SUFFIX for a new size)
python3 scripts/orrery_slime_redraw.py refresh <kinds>   # rewrite same-size sources
python3 scripts/orrery_slime_redraw.py export            # export saved editor frames and tops
python3 scripts/orrery_slime_redraw.py verify            # compare editor and atlas
```

## Rollback
```sh
python3 scripts/rollback_orrery_art.py --target /path/to/checkout           # dry run, restores v1 (live 1.39.22)
python3 scripts/rollback_orrery_art.py --target /path/to/checkout --apply
python3 scripts/rollback_orrery_art.py --target ... --backup /media/raid/valhallasc-data/orrery-slime-original-20261104 --apply   # pre-slime originals
```
v1 backup: `/media/raid/valhallasc-data/orrery-slime-v1-20261104` (seven files, hashes, old IDs, old tops and kindFrames, v1 script). All hashes are checked before any write.

## Checks
`tests/orrery-slime-art.cjs` (124 checks, run with `scripts/test-touch-bounded.sh`, `REAL_SPRITES=1`, `VALHALLA_BINARY` = main release binary): production loading, portraits, timings, borders, eight distinct attacks and deaths, wind-up and strike motion, grounding (mantis four feet, walking keeps two planted; Orbit Seer hovers and settles), health-bar tops. `scripts/orrery_slime_review.py review|verify|upload` builds the before (live v1) / after pictures and checks 204 editor/export matches, rollback and corrupt-backup refusal. No encounter or balance testing was run.
