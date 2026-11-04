# The Stormglass Shore enemy artwork (candidate, owner approval pending)

**Status:** private candidate on `feat/stormglass-slime-art` in `/media/raid/valhallasc-data/stormglass-slime-work`. Not deployed, no version bump until the owner has seen the FileDrop pictures and approved. Client-only. The Shore is zone 19 in the docs and index 18 in `world/map.txt`; look it up by name in tests. The zone also spawns `es_foe_15` (Empty Seat), which is not part of this art.

**Owner direction (2026-11-04):** every enemy unique and mean, no shared round-eye-plus-blush face. Each kind has its own face routine: stalked pale bulbs with a red bar pupil over side-opening serrated mandibles (saltclaw), a jagged lightning-bolt eye cut into a dark mask over a hooked horn beak (stormgull), two angular glowing slits under brow shards over a toothed glass maw (glassray), one horizontal lantern slit under slanted stone brows (breakersentinel), and one huge veined eye stitched shut across the lids, the zone's "sealed eye beneath the sea" (maelstromheart). No blush anywhere. Storm effects (arcs) are attached to feathers and rings, never loose glyphs. Defaults chosen without asking (veto welcome): stormgull, glassray and maelstromheart hover, saltclaw and breakersentinel stand on the ground; the Maelstromheart is the boss, the Breakersentinel the big elite.

| kind | look | attack | death |
|---|---|---|---|
| saltclaw | brine-teal crab: dome carapace crusted with salt crystals, a huge crimson crusher and a small cutter, stalked pale eyes, serrated mandibles | rears the crusher up, lunges and slams it down in a salt spray | carapace cracks and splits in two, legs fold, claws drop, salt crumbles into a pile |
| stormgull (hovers) | storm-dark gull, big ragged wings with lightning arcing along the feathers, hooked horn beak, bolt eye | draws back, then dives talons-first with the beak wide | arcs die out, tumbles nose-down and lands on its back, wings drooping |
| glassray (hovers) | manta of storm-glass: faceted pane wings, horned wedge head, angular slit eyes, toothed maw, barbed glass tail | tail whips overhead and stings forward, wings sweep wide | cracks run across the head, the wing panes fall away and the head splits into a heap of shards |
| breakersentinel (elite) | barnacled sea-stone guardian with kelp bands, rusted ship's anchor held like a halberd, lantern slit under a crown of barnacle spikes | hauls the anchor overhead and slams it down in front, crouching | head cracks, legs buckle, body collapses into a barnacle rubble heap, anchor falls across it |
| maelstromheart (boss, hovers) | a drowned heart wound in two thorned water rings with torn vessels and a stitched-shut eye | rings contract, the stitches snap, the eye glares open and the rings burst outward crackling | the eye closes for good, the heart darkens and stops, the rings unwind into a ripple on the ground |

## Files and frames
One manifest as before: `client/assets/stormglass.txt` with `stormglass_<kind>.png`. Per-kind frames (`KIND_FRAMES`, art scale in `SCALE`, tuned with `extents` and an in-game screenshot; a size change needs a NEW PixelFlow source: remove the kind from `scripts/stormglass_slime_sources.txt`, `SOURCE_SUFFIX=_x ... build`). Superseded sources are in `scripts/stormglass_slime_sources_superseded.txt`. Flyers need their lowest pixel at least 12 px above the anchor row in every living frame, so raise the hover height rather than the frame when `preview` complains.

| kind | frame | anchor | PixelFlow source |
|---|---|---|---|
| saltclaw | 100x62 | (46,56) | `556f7e4e2e5afd7e` |
| stormgull | 85x80 | (42,74) | `793128c99438e6e2` |
| glassray | 113x77 | (56,71) | `fb4494d6d181b64d` |
| breakersentinel | 120x93 | (41,87) | `22e635b74ca3ec6a` |
| maelstromheart | 102x70 | (51,64) | `a7a1dc3ea471a80b` |

```sh
python3 scripts/stormglass_slime_redraw.py preview|montage [kinds]   # contact sheets
python3 scripts/stormglass_slime_redraw.py extents [kinds]           # measure on a scratch canvas
python3 scripts/stormglass_slime_redraw.py build                     # create missing sources
python3 scripts/stormglass_slime_redraw.py refresh <kinds>           # rewrite same-size sources
python3 scripts/stormglass_slime_redraw.py export                    # editor frames -> atlas, manifest, tops
python3 scripts/stormglass_slime_redraw.py verify
```
`make_stormglass_sprites.py` keeps its helpers but its CLI delegates here and refuses `--replace`. `stormglass_cel_redraw.py` is untouched (the old art, imported by the old maker).

## Rollback
```sh
python3 scripts/rollback_stormglass_art.py --target /path/to/checkout            # dry run
python3 scripts/rollback_stormglass_art.py --target /path/to/checkout --apply
```
Backup `/media/raid/valhallasc-data/stormglass-slime-original-20261104` (six files, hashes, old PixelFlow ids in `manifest.txt`); every hash is checked before any write and a corrupt backup is refused.

## Checks
`tests/stormglass-slime-art.cjs` (104 checks, `scripts/test-touch-bounded.sh`, `REAL_SPRITES=1`, `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright`, `VALHALLA_BINARY` = main release binary, `NODE_PATH` from main): production loading, portraits, timings, borders, eight distinct attacks and deaths with a reaching strike, grounding (flyers hover and settle), health-bar tops. `SOFT_CHECKS=1` lists every failure instead of stopping at the first. Mutation: `STORMGLASS_ART_KINDS=saltclaw MUTATE_KIND=saltclaw MUTATE_PNG=<backup>/client/assets/stormglass_saltclaw.png` fails as required. `scripts/stormglass_slime_review.py review|verify|upload` builds the 25 FileDrop pictures, checks 170 editor/export frames and rollback incl. the corrupt-backup refusal. No encounter or balance testing was run.
