# Ironhide Beetle: rigid-shell redo (candidate Beta 1.39.12, 2026-11-04)

Reopened by the owner (new rules: distinct attacks, free frame size, grounded feet). The squash-and-stretch
slime-style Ironhide (Beta 1.38.1, still live until approval) is replaced by a rigid steel beetle in the
Greenmeadow slime style: shell, head and horn only translate and tilt as solid parts on six jointed legs.

- **Pipeline:** `scripts/meadow_slime_redraw.py preview | build | refresh | export | verify` (the
  `make_ironhide_sprites.py` CLI delegates; `--replace` is refused). One native PixelFlow source,
  `valhallasc_meadow_ironhide_redo_all` = **d80cccfe6dfc9e32** (`scripts/meadow_slime_sources.txt`). The earlier
  rigid candidate (`d1ab641330d34105`, never live) is kept in `meadow_slime_v1_sources.txt` / `meadow_slime_v1_raw.npz`;
  the live slime-style source `399849edffa3ab6f` and the original `a3f8837048d1098c` stay in PixelFlow.
  `refresh` rewrites the saved source from the drawer (overwrites editor edits); `export` keeps editor edits.
- **Frame:** 96x70, anchor (40,64), atlas 768x350 (frame size is free per zone; the old frame was 72x64). The
  Painter draws on 96x96 and each frame is cropped. Same art pixel scale as before, so the beetle keeps its size.
  `client/field.js` now applies `meta.tops.beetle` to `SLIME.beetle.top` (the old manifest had no `tops`).
- **Grounding:** every living frame's lowest pixel is exactly the anchor row (feet are Painter balls with integer
  radius, centre y = radius + lift); death frames never sink below it.
- **Attack (eight distinct frames):** rear up on the hind legs (1-3, pitch up to 20 degrees, front feet lifted),
  slam the horn forward and down (4-6, sparks and dust), recover (7-8).
- **Death:** shell fractures, legs buckle, then the beetle rolls onto its back with its legs in the air, the head
  beside the shell and the legs going limp; shell chips fall around it. No scaling or puddle.
- **Check:** `bash scripts/test-touch-bounded.sh tests/ironhide-slime-art.cjs` (needs `NODE_PATH` with the main
  `node_modules` and `VALHALLA_BINARY` = the main `target/release/valhalla-server` when run from a worktree): 22
  checks incl. 8 distinct attack and death frames, wind-up/strike/recovery extents, constant steel area (rigid),
  grounding on row 64, health-bar top and portrait. `MUTATE_PNG=<atlas shifted one row up>` must fail the grounding check.
- **Rollback:** `python3 scripts/rollback_meadow_art.py --target <checkout> --apply` restores the live slime-style
  `ironhide.png`/`ironhide.txt` from `/media/raid/valhallasc-data/meadow-slime-original-20261103` (hash-verified,
  dry run by default, corrupt-backup refusal tested). The change is client-only: no server rebuild or restart.
- **Review pictures:** `scripts/meadow_slime_review.py review | verify | upload` (nine `valhallasc-meadow-redo-*`
  FileDrop files incl. attack and death before/after GIFs). `verify` is a pre-deployment check (it expects the
  original live files); after release use `make_ironhide_sprites.py verify`.
- Not deployed: owner approval pending.

---

# Ironhide Beetle — slime-style redraw, private Beta 1.38.1

Owner request: redo the Ironhide Beetle in the style of the slime. The editable
PixelFlow redraw keeps its steel-blue carapace, bronze horn and six legs, with
the slimes' round glossy pixel shading, large white eyes, blink, chunky feet,
squash/stretch hop, charge anticipation/lunge and collapsing death frames.
No enemy statistics, combat timings, map data, rewards or other sprites changed.

Generator: `scripts/make_ironhide_sprites.py preview | build | export`.
New saved PixelFlow source: **399849edffa3ab6f**,
`valhallasc_ironhide_slime_style_all`. Original **a3f8837048d1098c** remains
in PixelFlow; the new prefix avoids destroying its editable frames.
`build --replace` affects the new variant only and discards its editor changes;
use export to retain them. Indexed source: `scripts/ironhide_raw.npz`.

The renderer contract is unchanged:72×64, foot anchor(36,60),576×320atlas,
34frames:6idle/8walk/8attack/4hurt/8die at6/10/12/10/8fps. Every exported frame
is pixel-for-pixel identical to the saved editor source, nonempty and has clear
outer edges. Proof: `test-results/ironhide-slime-proof.json`.
New PNG SHA256: `a91ecac9df2dbc96700f9ae2c95ec90b2248a6bbebbebdc5b22039bbb7921d8f`.
Previous PNG SHA256: `0dfe5aaa5a08370d935f6706dc1150f82ad6668fbdd297d2dd65d5e0590e0cb1`.

`tests/ironhide-slime-art.cjs`:11 focused real-browser checks pass: frame/anchor/
atlas contract, all34frames, saved sourceID, five clips animate distinctly,
readable whites/gloss, production target portrait and no browser errors.
Desktop and phone gameplay, clip gallery, portrait and slime/reference comparison:
`test-results/driver-T4GLas`. The first fixture attempted an unexposed slimeSrc
getter; corrected to load the actual reference PNG, then the focused test passed.
No full suite, gameplay grinding or combat balance/timing tests.

Python/JS syntax, Swedish generation, release-note guard and diff checks pass.
Boss-add art aliases were reapplied and the unrelated cathedral atlas is
byte-identical. Display/notes/Swedish keep label all use Beta1.38.1.

Implemented in the existing private `/media/raid/valhallasc-data/solstice-work`,
branch `feat/summer-solstice`, after the combined seasonal candidate. Local and
uncommitted, not deployed; no public assets or production database changes.
No server rebuild is required for this client artwork. The previous optimized
private server is reused only for the bounded browser check.

Owner-requested FileDrop follow-up: uploaded `valhallasc-ironhide-before.png`,
`valhallasc-ironhide-after.png` and `valhallasc-ironhide-before-after.png` to Sork's
FileDrop. The comparison uses the exact old and new idle atlas frames at equal
nearest-neighbor scale. All three destination hashes, PNG dimensions and metadata
were verified; receipt: `test-results/ironhide-filedrop.json`.
