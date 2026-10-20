# The Drowned Longship — level 35

Implemented: I35-MAP/FOES/QUEST/SCENE/OPEN. Public zone 43, parent Rán’s Deep (8).
Private development worktree: `/media/raid/valhallasc-data/longship-development-20261020`
(base aecb80a), linked as main project `.tools/longship-work`. Developed and validated privately before integration. Preserve other sessions’ PvP/skills work.

## Identity

A pointed, curved wreck with actual hull collision, two bulkheads, split cargo
hatches and a gangplank. Stern → cargo maw → capstan/bosun → captain’s prow.
Teal sea, salt-dark planks, curved copper ribs, torn sails, porthole lamps,
ballast/cargo piles, a ship’s bell, a broken mast and a carved prow. No six-room
barrow template and no cathedral masonry.

Keelbound gear: original pose-fitted hull/anchor/sail geometry; verdigris copper,
navy sailcloth, ivory rope and coral accents. New class-specific heads and
weapons. All monsters AND gear must be saved/exported through PixelFlow, as
required by TODO rules; keep all poses/facings/both hero bodies and own icons.

Six foes (three ordinary, three guardians), entry talk quest and two distinct
guardian quests. Captain Svala Nineknots has no direct quest. Her Anchorfall
marks a lane for five seconds; stand to either side. Below 35%, wider lane
with a second pull after three seconds. Ability, sign, quests, gear and dialogue have hand-written Swedish.

New dybase2 MCP score: Below the Last Sail, a restrained 6/8 rowing
shanty in E dorian, 78 BPM, 32 bars, no foreground lead. Lock bass/kick at zero
and 1.5 quarter-beats; clear eight-bar harmony sections and natural ending.
Read docs/musical-style.md; no Hip-hop hats, no Sork-60 Whistle/noise drones.
Do not claim audition if unavailable; no unrequested FileDrop music upload.

## Pipeline / deployment

`generate_longship.py` creates the open template and safe entrance at (54,146),
return (54,151), west of Keelhaven; all spawns/NPCs/portals pass generator flood.
Use `--sealed` while changing unfinished content.

With new file zones 0–43, prior extra dungeon copies 43–96 shift to 44–97;
Longship extra copies 98–100; Arena copies 101–108. Never deploy without
inspecting stopped saved characters for old private-copy IDs. No DB changed.
No commit, push or server deployment requested in this turn.

Focused validation results follow. No public server deployment or DB migration has been performed.

## Completed source and art checks

Generator flood checks pass from the Bifrost arrival through the Keelhaven
approach, every dungeon spawn/NPC and both exits. Repeated `--open` generation
is byte-stable (repeat again after any layout changes). The exact `longshipFloor`
mask prevents the encounter-room rectangles from becoming a generic dungeon.
`generate_deep.py` reapplies the connecting gate after rebuilding the parent.

All six 96×96 enemy atlases have 34 editable PixelFlow frames, passed no-edge
bounds checks and exactly match their exported indexed source. The shared
cathedral manifest retains earlier monsters. New IDs:

| Kind | PixelFlow sprite |
| --- | --- |
| keel_crab | c56de92686212091 |
| keel_deckhand | eeb9cb4c79d8945f |
| keel_lantern | 1806195cd517b44e |
| keel_cargomaw | da01fea0e62149f9 |
| keel_bosun | 516da622c3f6559b |
| keel_captain | 78a307dae4671b58 |

Music project [Below the Last Sail](https://gunning.se/dybase2/?project=6acebdb1dd3ce640)
was created and rendered through the dybase2 MCP. Quiet Dexed marimba/wood bass,
Sork-60 Mellow Pad, sparse bells and oarlock drums; no hats or foreground lead.
32 bars in 6/8 at 78 BPM, E dorian; exact 73.846154-second loop. Decoded mono RMS
−23.995 dB, peak −2.264 dBFS, corrected PCM seam delta 0. Natural-ending MP3/WAV
and project/analysis/render metadata are in `test-results/longship/`.
The song has not been auditioned; no listening approval is claimed. The owner subsequently requested FileDrop delivery; see the delivery record below.

## Private browser and protocol evidence

- Six focused Rust integration tests pass: actual collision and reachable
  targets, entry level gate and party isolation, both return paths, all-boss
  clear/loot/quest credit, wearer-only timed health/resource recovery, and the
  full five-second Anchorfall warning plus low-health echo and fallen state.
- Private MCP `longship` passes 17 checks, including class-neutral quest rewards
  and restart persistence: `test-results/driver-y46y4C/report.json`.
- Stub UI: `test-results/driver-bNXlPx`; real UI: `test-results/driver-UFLn21`.
  Both pass travel, sign reading, independent indoor music selection, loop
  duration, saved volume, mute, return-to-Deep score and clean error checks.
  Six real enemy atlases decode. Screenshots cover stern, hatch, cargo, capstan,
  sail, captain and sign. The final scene check additionally covers the carved prow and the world map’s actual hull/hatch mask.
- `tests/longship-gear-art.cjs` passes all 28 items / 80 visible fitted layers /
  ten hero bodies, every clip and facing. Minimum changed outline: 51 pixels;
  each layer has at least three colours absent from its starter counterpart.
  The mutation that substitutes starter geometry fails at delta=0 as intended.
  `test-results/longship-redesign/` contains full equipped class sheets and data.
- All 21,760 source gear frames passed blank/clipping guards; 400 body-specific
  clip records remain editable in PixelFlow, with depth and matching icons.
  All 2,023 earlier icon entries retain their positions and exact pixels.
  Existing item records are unchanged; exactly 28 pieces and six materials added.

## Combat measurements

All measurements are limited to the new dungeon and use the hired fighters'
actual `auto_play`; each run prints class DPS. The no-enrage captain control
wins four of four with the hired five (51,57,51,51 seconds). With only four
mercenaries, the idle-hirer control wins in 82–88 seconds and the down-hirer
control in 84–91 seconds. The raw measurement intentionally fails the
mercenary-alone rule; it measures the available tuning interval.

A 64-second start (0.2 ramp) is later than every hired win and earlier than
any four-mercenary win. With this candidate the five win four of four, while
both idle/down controls win zero of four. This passing value is now in
`world/enrage.txt`; no public server has been restarted.
The four packs and two side guardians also fall to the hired five. Initial
side starts are 85/95 seconds. All 30 lone-boss cases (five classes, green and purple gear) lose. The initial pack multiplier 5 let a priest survive; candidate 8 passes all 20 lone-pack cases and all four hired-pack checks. Multiplier 8 is now in elite-power.txt. Both side guardians still fall to the hired party. Logs: solo.log (boss pass and original pack failure), packs-candidate.log (20 passes), hired-final.log (six wins).

## Final gates and delivery

Clippy passed with `--all-targets -- -D warnings`; Python/JavaScript syntax and
Rust formatting checks pass. The final private debug server build embeds the
64-second captain enrage and pack multiplier 8. All changed files were merged
into the main checkout using a three-way merge; other sessions’ PvP, skills,
mercenary, consumable and set changes were preserved. No git index edits,
commit, push, public restart or production DB migration was performed.

On owner request, the natural-ending MP3, all ten equipped hero bodies in one
Keelbound sheet, and real zone screenshots were uploaded to Sork’s FileDrop.
`scripts/filedrop_put.sh` verifies the delivered file SHA-256 against its source;
receipts are in `test-results/longship/filedrop.log`. Full-song listening remains
unverified even though export levels and in-game music routing/controls pass.

Final real-client recheck: `test-results/driver-D5lpFB` passes, including the
world-map hatch/gangplank pixel check and the carved dragon prow screenshot.
Six FileDrop deliveries have verified source/destination SHA-256 matches:
Split Hatch, Torn Sail, Carved Dragon Prow, Hull Map, the combined all-heroes
Keelbound sheet, and Below the Last Sail (natural-ending MP3).
