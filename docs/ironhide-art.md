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
