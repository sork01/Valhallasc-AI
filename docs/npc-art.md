# NPC artwork

## Complete NPC release — Beta 1.45.0

The owner authorized deployment with "finish skill and deploy" after reviewing the
robe correction. This supersedes the private/pending status in the history below.
All 588 actual people are assigned: the original 319 identities are preserved,
148 newly named people use their bespoke designs, and 121 generic roles reuse
coloured role artwork. Mailboxes, meeting stones and scenery remain excluded.

The library has 318 looks: the original 164, the 148 corrected named designs,
two corrected native role templates and four treefolk aliases of corrected named
sources. The latter reuse saved PixelFlow frames exactly, with their own material
remap tables. All twelve generic Veyrroot/Heartwood roles use bark and leaf colours.
No new winged cohort, people, dialogue, routes, quests or gameplay data is added.

`assign_all_npc_art.py` preserves original identities, installs all missing
assignments and validates exact coverage of actual people. The plan generator
uses the accepted 319-person baseline from git, so the approved plan remains
reproducible after all assignments are installed. `NpcArt` continues reading
assignments from `npc.txt` and frames from the matching player-style bank.

The two new role sources and all four aliases pass saved/editor export checks;
all six reuse looks pass focused atlas/grounding/head tests. The two human role
sources pass their new 40-pose garment-occlusion check. Existing named-art tests
and all 164 original atlas hashes remain valid and unchanged.
`tests/npc-assignment.cjs` asserts full coverage, source/species correctness and
original identity preservation. `tests/npc-all-scene.cjs` checks one real zone per
bounded process, including new people through `City.drawNpc` and personal colours.
All 269 new assignments pass in 22 bounded real-zone runs. Disabling the
player-style selection fails its check. Scene receipts are in
`test-results/npc-full-release/scenes/`.

This client-only release updates the displayed version, English release notes and
Swedish keep-list/catalog together. The map, server binary and saved data remain
unchanged; no restart or database backup is required. The release record and
public verification will be added after deployment.


## Missing named people — built 2026-11-12

### Robe/skirt correction after owner review (2026-11-12)

The owner found legs visible through skirts and robes, including standing poses.
The earlier contract/head-socket checks missed garment occlusion. The cause was
`Ink.plate` using one averaged depth for a tall panel while limbs carry interpolated
depth and a radius bias. Garments now use fitted depth planes. Closed skirts also
clip the separate leg/boot layer to their projected coverage, keeping hands and
props in front and visible legs below the hem. Treefolk root toes respect the
same cloth coverage.

All 148 named editor sources were corrected and re-exported; all 2,960 saved
frames match their PNGs. `tests/npc-skirt-occlusion.py` compares each exported
pose against the same pose with legs removed. Removing legs changes **zero**
pixels inside the eroded garment coverage in all 2,920 poses of the 146 designs
with legs; every design still has visible leg pixels outside the garment. The
old flat-depth/unclipped rendering fails all 20 Hild poses, including every idle
frame. The two mermaids have no legs. All 148 designs also pass the focused art
checks and all 2,960 production-browser poses again, with no browser errors.

Corrected standing and walking comparisons were visually inspected. All 24
previous review pictures were replaced in FileDrop and two comparisons added:
[Standing before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-npc-named-robe-fix-before-after.png),
[Walking before/after](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-npc-named-robe-fix-walk.gif).
The 26 files total 2,154,397 bytes; stored hashes, metadata, dimensions and frame
counts are verified. The pre-correction atlases, editor packets and pictures are
retained in `/media/raid/valhallasc-data/npc-named-robes-before-20261112`.
The original 164 designs and live assignments remain unchanged; this corrects
the private named-NPC candidate. It is not deployed.


148 new bespoke designs are complete on `feat/npc-named-designs`, in
`/media/raid/valhallasc-data/npc-named-work`. They cover 134 previously unassigned
quest givers and 14 individually characterised residents, including Halvard,
Lotta, Ulf and Heartwood residents/children. This is a private art candidate;
assignments and deployment remain the separate NPC-ALL tasks.

The corrected inventory is **269 missing people**, split into 148 bespoke designs
and 121 generic-role reuses. Another 145 unassigned entries are scenery, meeting
stones or mailboxes and are excluded. `docs/npc-named-plan.txt` records every
person, zone, reason, reuse choice and explicit design spec; it includes
Greenmeadow's top-level people and leaves the original plan/assignments intact.

Each new person has an authored player-rig archetype, occupational prop, headwear,
hair, garment cut and signature details. Added held props are a shepherd's crook,
apple basket, honey pot, flail and drum. Shapes distinguish people independently
of palette: the closest idle-alpha pair differs by 32 source pixels. All 26 new
Veyrroot/Heartwood designs are treefolk; both mermaids keep their tails. The
existing winged species cohort is unchanged.

There are 148 current native PixelFlow sources and 2,960 editable frames, with
the existing 96×96, (48,90), idle 6 / walk 8 / talk 6 contract. One pre-correction
candidate palette/source is retained in `npcp.txt` `sourceHistory`. All 164 prior
sources, material metadata, tops, bounds and PNG byte hashes are preserved.

`scripts/npc_named_plan.py` writes the explicit inventory;
`scripts/make_npcp_sprites.py build|export|verify named` produces the new group.
Build creates each source and all twenty frames atomically through PixelFlow,
merging only new metadata. Export reads saved editor frames and updates only
selected designs. `refresh` requires explicit `named_*` keys; a palette change
creates another source and retains the previous ID. The legacy catalog generator
must not be used to regenerate this batch: it includes mailboxes and reclassifies
unrelated people.

Checks passed: all saved/editor-export frames match; focused
`NPCP_ART_GROUP=named python3 tests/npcp-art.py` validates all new frames, heads,
animation, grounding and silhouette differences; bounded
`tests/npc-named-ui.cjs` draws all 2,960 production poses with finite head sockets,
nameplate heights and no clipping/browser errors. Removing the new player-style
entries fails its style assertion, as intended. Its assignments exist only in
the private page's memory, so `client/assets/npc.txt` remains byte-identical.
Swedish build validation and syntax checks pass. No encounter tests or grinding.

Local review: `scripts/npc_named_review.py` writes
`test-results/npc-named/roster.png`, 22 zone sheets (idle/walk/talk) and
`highlights.gif`, all from saved exports. The roster and the Heartwood motion
sheet have been visually inspected. The art advisor reviewed the initial
approach and prototypes; near-duplicate outlines and Kessa's drum were corrected
before final verification. Generic assignments, in-zone acceptance and release
remain separate tasks. The owner requested FileDrop delivery on 2026-11-12: the corrected 26 review files
(roster, highlight animation, 22 zone sheets and two robe-fix comparisons;
2,154,397 bytes) are uploaded,
with stored SHA-256, byte lengths, MIME metadata, dimensions and frame counts
verified. Receipt: `test-results/npc-named/filedrop-receipt.json`. Downloads use
the normal FileDrop login. Live artwork and assignments remain unchanged.

[Full roster](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-npc-named-roster.png) ·
[Animation preview](https://gunning.se/filedrop/api.php?action=download&file=valhallasc-npc-named-highlights.gif)

The production plan is `docs/npc-art-plan.txt`. It inventories every speaking person by stable id, name, occupation, zone, earlier artwork and new assignment. Names, routes, offers, dialogue, quest ids, interaction distances and saved data stay in the authoritative world catalog. Stones and speaking scenery keep their scenery artwork.

The 24 general designs are sentinel, physician, smith, baker, innkeeper, merchant, ranger, scholar, herald, gardener, fisher, weaver, courier, pilgrim, bard, child, elder, painter, carpenter, alchemist, steward, stablehand, lamplighter and banker. The plan specifies each silhouette, build, hairstyle, headwear and occupational prop. They vary from short wide smiths and round bakers to tall formal stewards, hunched elders, children, narrow rangers and full-skirted innkeepers. Tools are part of the silhouette, rather than a colour change on a shared body.

Special designs have their own saved sprite and spec per named person: existing bespoke characters, bankers, merfolk, astral/prism/clock/fungal inhabitants, Asterion's eccentric people, inner Heartwood inhabitants, dungeon witnesses and Emberwake/Forge characters. Match their region's materials: kelp/coral/fins, star embroidery, brass mechanisms, spore caps, floating rings, living branches, desert veils, glacier fur, slate, seasonal foliage, forge chains. Preserve named identities through the existing skin/hair palette, occupations and their individual prop and headwear. Merfolk keep tails.

Use hard cel bands, warm dark outlines, glossy anime eyes, big readable faces, complementary cloth/material ramps and upper-left highlights. No dithering. Frame 96×96, foot anchor (48,90), transparent margin on every side. Idle: six breathing/blinking frames; walk: eight frames with alternating feet, counter-swinging arms and moving loose clothing/props; talk: six frames with a raised gesture and mouth motion. Walking follows existing routes, with horizontal facing mirrored from direction. Ground contact stays fixed; head/nameplate bounds come from the exported frames. Portraits use the same frames and anchor.

All production sprites go through PixelFlow. `scripts/make_npc_sprites.py build` creates missing saves without replacing existing editor work; `export` reads the saved frames back, and `verify` compares every exported frame with its editor save. A manifest retains every saved id even when PixelFlow's list truncates to 100. General assignments preserve per-person skin, hair and clothing using palette material masks. A bounded cache holds recoloured atlases. The plan must be regenerated when NPCs are added, before producing any missing designs.

Focused checks cover the contact sheet of every design, transparent borders, clip variation, walk leg changes, saved/export agreement, renderer frames, named assignments, representative towns and special regions, portraits, and foot placement. Real-device acceptance stays in the separate touch TODOs.

Production and verification (2026-10-26, Beta 1.21.0): 164 saved designs (24 general, 140 special), 298 assigned people and 3280 frames. `python3 tests/npc-art.py` checks every exported frame and all 24 distinct general silhouettes; `make_npc_sprites.py verify` compares every frame against PixelFlow. The contact sheet is `test-results/npc-contact.png`. The real-art suite captured 14 towns/special zones, a merchant portrait and the moving Badger. The final private-index pass passed 34 browser checks at a 1338 MiB peak under the 1536 MiB cap. The NPC integration mutation fails when City stops using the new art.

Recolour canvases are released on zone changes; retention covers the town's NPC count, preventing repeated allocations when more than 24 people are visible. Foot/nameplate bounds are measured from the exported artwork. General identity colours come from the original NPC look data; fallback identities preserve the original Alderhaven faces.

Props use explicit grip points attached to the animated wrist. Draw fingers over
the handle after the prop, and use the second hand to support books, scrolls,
trays, chests, tablets and sacks. Satchels stay on their shoulder strap; walking
and conversation must keep the hand and prop together. Long poles keep their
lower end above the frame border. `python3 tests/npc-grips.py` checks visible
hands and handles in the shipped idle, walk and talk pixels.

The 21 entrance repair smiths reuse the general smith artwork, bringing the
identity inventory to 319 without adding saved designs. After adding identities,
run `npc_art_catalog.py`, then `make_npc_sprites.py assign` to refresh assignments
while preserving every saved frame, id and measured bound.

## Seasonal head attachments (Beta 1.35.1)

Nameplate bounds include occupational props and must never position a costume.
`NpcArt.head(n,t,talk)` reads the real exported frame, finds the principal skin
component near the head, then follows its connected central hair/headwear upward.
It returns the head centre, crown, width and collar, applying the actual sprite
scale, individual NPC scale and mirrored walking pose. Each design/clip/frame
is scanned once and cached; existing saved art and PixelFlow IDs stay untouched.
Christmas hats/scarves use these sockets, and names clear the resulting hat.
Idle, walk and talk must use the same pose on the body and its accessory.

Focused bounded check: `tests/christmas-attachments-ui.cjs`, real NPC exports,
103 NPCs / 2,884 poses, plus pixel contact checks and per-city contact sheets.
The former nameplate-based brim is detached in 108 sampled poses, so the check
exercises the reported failure rather than merely confirming accessory pixels.

## Player-style remake (NPC-PLAYER-STYLE, started 2026-11-10)

Owner decision (2026-11-03): every human NPC takes the **player's body and head ratio**; differences come only from clothing, hair, headwear, props, palette and posture. Non-humans keep their anatomy in the player's shading, eyes and animation feel. **Status: sample trio only, awaiting the owner's go/no-go.** Nothing is deployed, no PixelFlow sprite is built, no live file is touched.

### Method: draw with the players' own rig

`scripts/npcp_sample.py` imports `cel_common` read-only (skeleton, `torso`, `head_frame`, `face`, `Ink` cel renderer) and patches its frame constants at run time (`FW=FH=96`, anchor 48,89, `PX`), so the proportions, almond eyes, outline weight and 4-tone ramps are the players' by construction, with no hand-copied numbers. The rig module `make_warrior_sprites.py` was removed from `www/` with the old Valhalla; it is kept in `rig-tools/` (extracted from `/media/raid/valhallasc-data/old-valhalla-20261107.tar.gz`, set `VALHALLA_TOOLS` to move it). No class sprite is re-rendered and `cel_common.py` is untouched.

- **Scale:** players are 97 px tall in a 160 px cell (hair top to foot), drawn at 1.3 = 126 px on screen. NPC atlases draw at 1.4, so an adult at `PX` 0.81 (79 px with hair, about 110 px on screen, 0.88 of a player, the old sentinel was 75 px) fits the 96 frame with the foot at y 90 and room above for props. A child is rendered at 0.68 of that with a 1.28x head (64 px, 0.71 of a player). **True player height does not fit the 96 frame** (it would need 90 px of the 90 above the anchor), so NPCs are slightly shorter than players, as the old ones were. The frame stays 96x96, no `NpcArt`/`City` change.
- **Facing:** idle and talk face the camera (`S`), walk uses the three-quarter `SE` (the client mirrors it), as before.
- **Clips unchanged:** idle 6 (blink on frame 4), walk 8 (alternating feet, counter-swinging arms), talk 6 (raised hand, mouth opens on odd frames). Same `npc.txt` contract.
- **Palette:** per-design `skin`, `hair`, `coat` (cloth), `pants`, `trim`, `extra` ramps built from the NPC's own identity colours (`mats()`), so named people keep their colours.

### Traits that must survive (general designs, from `npc-art-plan.txt`)

| design | build | hair | headwear | prop | notes |
|---|---|---|---|---|---|
| sentinel | broad | crop | helm | spear | square shoulders, high greaves and long pennant spear |
| physician | tall | braid | veil | bottle | long split coat, narrow shoulders and high medicinal flask |
| smith | stocky | shaved | goggles | hammer | heavy apron, bare forearms and oversized smith hammer |
| baker | round | curls | toque | bread | round belly, towering soft chef hat and bread tray |
| innkeeper | curvy | bun | ribbon | mug | full skirt, puff sleeves, apron and welcoming tankard |
| merchant | round | beard | turban | scales | broad layered silk coat, wrapped hat and brass balance |
| ranger | lean | ponytail | feather | bow | long bow, fitted tunic and angled feather cap |
| scholar | stooped | long | cap | book | bent shoulders, long robe, spectacles and open folio |
| herald | tall | waves | beret | trumpet | angular tabard, jaunty beret and raised brass trumpet |
| gardener | short | pigtails | straw | flowers | wide straw hat, short overalls and overflowing flower basket |
| fisher | broad | beard | beanie | fish | oilskin cape, sea beard, creel and a silver fish |
| weaver | curvy | braid | ribbon | spool | asymmetric shawl, braids and spindle with threaded wool |
| courier | lean | crop | scarf | satchel | short jacket, long trailing scarf and packed messenger satchel |
| pilgrim | stooped | shaved | hood | staff | hunched cloak, high walking stick and tied bedroll |
| bard | lean | waves | feather | lyre | fitted vest, swept hair and large curved lyre |
| child | child | pigtails | ribbon | kite | small limbs, oversized round face and diamond kite |
| elder | stooped | beard | beanie | cane | low back, large beard, spectacles and crooked walking cane |
| painter | short | curls | beret | palette | painted smock, curled hair, broad palette and long brush |
| carpenter | broad | ponytail | band | saw | rolled sleeves, tool belt and long toothed hand saw |
| alchemist | short | spikes | goggles | alembic | short triangular coat, wild hair and glass distillation coil |
| steward | tall | long | circlet | scroll | straight formal mantle, thin crown and ribbon-bound scroll |
| stablehand | stocky | braid | cap | reins | leather chaps, strong boots, braided hair and looped reins |
| lamplighter | lean | crop | hood | lantern | long rain cape, pointed hood and hanging amber lantern |
| banker | round | bun | cap | chest | buttoned waistcoat, large coin chest and folded ledger |

Build words (stocky, round, stooped, child, ...) no longer change the body; they become clothing volume, posture and prop size.

### Special designs by group (count)

asterion 19, astral 6, banker 5, barrow 1, cairn 5, cf 1, ew 4, frostwake 5, heart 5, keel 1, lapis 4, moonspore 6, nacre 28, null 1, orrery 5, prism 5, raid 1, ribbon 2, sky 7, span 3, sun 2, tangle 2, travel 18, yr 4

Each keeps its region material (kelp/coral/fins, star embroidery, brass, spore caps, rings, living branches, veils, glacier fur, slate, forge chains) and its own headwear/prop; merfolk keep tails (see Captain Namar in the sample).

### Sample trio and open points

Smith (general, gripped prop), child (no player equivalent) and Captain Namar Deepwatch (non-human). Sheet: `test-results/npcp-sample/npcp-sample-sheet.png` (old | new idle, walk, talk | player at in-game scale), per-design clip strips beside it.
- **Not yet checked:** `NpcArt.head` socket detection on the new frames (the head is smaller and hair is drawn differently), hand-on-prop contact (`tests/npc-grips.py` expects the old wrist coordinates and `GRIPS`), `tests/npc-art.py`, portraits, nameplate bounds. All of it belongs to the full run, after the owner's go/no-go.
- **First-pass flaws to fix in the full run:** smith's hammer reads sideways (head too wide for the handle), the child's kite string is hidden behind the pigtail, scale texture on Namar's tail is flat, arms are thin in the idle pose.

### Batch 1: the 24 general designs (2026-11-10, staged, not deployed)

- Drawn by `scripts/npcp_general.py` (outfit spec + hair + hat + prop per design, on the players' rig), built and exported by `scripts/make_npcp_sprites.py` (`build | export | verify | sheet`). PixelFlow saves `valhallasc_npcp_<design>` (old `valhallasc_npc_*` ids untouched); atlases `client/assets/npcp_<design>.png` and manifest `client/assets/npcp.txt` sit **beside** the old art and nothing reads them yet.
- **Recolour contract:** per design the manifest carries the exact exported hex of `skin0-3`, `hair0-3`, `cloth0-3` plus `amounts` (the shade factors used to draw them: skin .62/.82/1/1.2, hair .5/.75/1/1.3, cloth .45/.7/1/1.45). The old client has fixed 3/3/4 factors, so wiring needs a small `npc-art.js` change: use `meta.designs[key].amounts` when present (default to the old lists). Person-by-person remap was verified in Python on five smiths, two innkeepers and five merchants (`test-results/npcp-general/recolour-people.png`).
- **Checks:** `python3 tests/npcp-art.py` (24 designs; contract, borders, feet, every clip animates, walk legs change, remap tones present, head socket by a port of `NpcArt.head` on all 480 frames, 24 distinct silhouettes, tops agree; `--mutate` must fail) passes. `make_npcp_sprites.py verify` agrees with PixelFlow.
- **Rollback:** `/media/raid/valhallasc-data/npc-style-original-20261110/` holds the old `npc.txt` (with every old PixelFlow id) and all 164 atlases; `python3 scripts/rollback_npc_art.py [--apply] [--drop-new]` restores them (dry run by default).
- **Deploy step (after the owner approves the pictures):** wire a design to its new atlas (read `npcp.txt`, per-design `amounts`), then run the in-browser checks (`christmas-attachments-ui.cjs` style sockets, portraits, foot and nameplate placement, representative towns) with the bounded runner. Not done yet.
- **Known compromises:** adults are drawn at 0.88 of player height, the child at 0.71 (see above); the head is the players' pixel size on a smaller body, as in the approved sample; 3/4 `SE` walk frames are mirrored by the client; props sit in the screen-right hand.

### Batch 2: the 140 special designs, treefolk and winged people (2026-11-10, staged, not deployed)

- Same renderer (`scripts/npcp_general.py`): every special is its general archetype (matched by the plan's `notes`) with its own colours, hair, hat, prop, a region **ornament** (wings, coral, stars, crystal, gears, mushroom, rings, wheat, ribbons, orchid, branches, leaf, veil, fur, slate, season, antler, rope, chains, braid) and, for merfolk, a tail with fin ears. Specials have fixed colours (`general: false`, no remap); their `materials` skin tones are in the manifest for the head sockets. `python3 scripts/make_npcp_sprites.py build|export|verify special` (or `all`).
- **Owner decisions (grill 2026-11-10):** treefolk are **humanoid with bark** (player body, bark skin, leaf hair, branch antlers, root toes), applied to the five `heart_*` people and the Veyrroot Spark master; **winged** people (the 7 Bifrost `sky_*`, `travel_perch`, the 3 Shattered Span people) get **feathered bird wings** (three tiers, spread on flap/talk) and **hover** a few pixels (body raised 3.4 units, shadow stays: `City.drawNpc` draws the ground shadow independently of the sprite). Manifest `designs[key].species` is `treefolk | winged | merfolk`. More winged zones: not decided.
- **Checks:** `tests/npcp-art.py` now covers all 164 designs (borders, feet, animation, walk legs, head sockets on 3,280 frames, species present, `--mutate` fails). `make_npcp_sprites.py verify all` agrees with PixelFlow for 164 saves. A merfolk tail flicks up to 7 px above the anchor on one walk frame (test slack 10).
- **Deployed 2026-11-11 (Beta 1.43.0):** `client/npc-art.js` draws every person from `npcp.txt` (the saved `npc.txt` stays as the per-person assignment and the fallback) and reads each design's own `amounts` for the recolour; `tests/npc-player-style-ui.cjs` (`ZONES=`, `MUTATE=style|amounts`) checks every person in a zone (player style, opaque, head socket, nameplate height, recolour ramp); merfolk swim geometry per style (`GEO`). Not looked at: seasonal hats on treefolk antlers, portraits of the hovering winged people in dialogue. Pictures: `test-results/npcp-special/` (`winged-motion.png`, `treefolk-motion.png`) and the before/after sheets from `make_npcp_sprites.py sheet <names>`.
