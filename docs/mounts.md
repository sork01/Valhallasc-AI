# Mounts

> Money (2026-11): every amount below called "gold" is stored as copper and shown as gold, silver and copper (100 copper = 1 silver, 100 silver = 1 gold); see [money.md](money.md).

These settle `MOUNT-RULES` in [TODO.md](../TODO.md). `MOUNT-SERVER` stores the owned set, `MOUNT-SOURCES` adds the acquisitions below, `MOUNT-UI` adds the picker, `MOUNT-GRYPHON`/`LIZARD`/`RAPTOR`/`SABERTOOTH` draw the sprites and `MOUNT-CHECK` verifies it all. The horse keeps its price (500,000 gold), level (50), vendor (Stable-hand Greta, Skaldholm) and every rule in the README.

## One cosmetic choice at one speed

All mounts share the same travel speed: 1.6× the class's walking speed in the open world, as today (`speed() * 1.6` in `world.rs`). No mount bypasses void, cliffs or any collision, and none flies, jumps or changes combat. Ordinary mounts work only on land; the seahorse works only in underwater zones. The gryphon is a ground-runner that spreads its wings in the animation; this avoids new collision, zone-edge and exploit rules (Bifrost Reach's void rings, sealed gates, instance walls) and keeps travel balance identical to the horse. A mount's rank is its price of effort, not its power.

## How each mount is obtained

Each uses a different route, and the later the mount the harder it is. A character's level gates **getting** the mount; once owned there is no riding level.

| Mount | Route | Level | Cost and effort |
| --- | --- | ---: | --- |
| Roseheart Unicorn | Valentine Briarheart daily quest in Rimeveil Glacier | 1 | Guaranteed ownership on claim by each eligible real player; five fighters, highest party level. |
| Red-nosed Reindeer | Christmas Grinch daily hunt in Rimeveil Glacier | 1 | One independent 5% roll per eligible real player per Stockholm day; five fighters, highest party level. |
| Nightmare Steed | Halloween Hollow Rider daily hunt in Gloamfen | 1 | One independent 1% roll per eligible real player per Stockholm day; five fighters, average level rounded up. |
| Horse | Shop: Stable-hand Greta, Skaldholm (unchanged) | 50 | 500,000 copper (50 gold) |
| Raptor | Quest chain in the Tanglecrown: *The Banyan Run*, four steps given by Mara Vines (Canopy tracker) | 75 | No gold fee. Kill 25 canopy monsters, bring 10 of the zone's materials, win one elite fight and escort a hatchling back. One-time, class-neutral. |
| Lizard | Shop: a new Dune-wrangler NPC in the Lapis Erg hub (beside Basma Silk) | 80 | 160,000 copper (16 gold) (the price of a level-80 Hero Pack, the same wealth tier as the horse at its level) |
| Sabertooth | Rare drop: a **Sabertooth Whistle** from the Rimesaber, the level-97 elite of the Yearwheel's winter court | 95 | 4% per Rimesaber kill; a 5.5-million-HP elite, so it needs a group and a long fight |
| Gryphon | Dungeon reward, the hardest: a **Gryphon Egg** from the final boss of the Thunderheart Gate (level 95), hatched by Oren Highwind, Summit windseer, in the Cairnspine | 95 | 3% per final-boss kill, plus 250,000 gold to hatch. At 3% about 33 clears are expected. |

Rules for the items:

- The Whistle and the Egg are **licences**, a new item `kind: "mount_licence"` with a `mount` field naming the mount. Using one (or hatching, for the Egg) grants the mount and consumes the item. A character who already owns that mount keeps the item and is told so; a licence is never consumed uselessly.
- Licences are **bound**: they cannot be traded, sold to a shop or put in a trade offer (`trade.rs` already refuses starter and GM gear; the same check gains `mount_licence`). Rolling is Need/Greed: Need is allowed only for a character who does not own that mount, and a licence is never put in the round-robin pile.
- A licence uses its own drop roll, independent of gold, materials, bags and every gear pool, and the chance lives in one named constant per licence. No bad-luck protection is added; the Egg's gold fee is the sink.
- The Whistle and the Egg are used at the level shown. A lower-level character who somehow holds one is told the level; the item stays.

## Ownership and choosing one

- A character owns a **set** of mounts (`mounts`, an ordered list of IDs) and has one **selected** mount (`mount`). Existing saves migrate on load: `mount_owned == true` becomes `mounts = ["horse"]`, `mount = "horse"`. `mount_owned` stays readable in the snapshot as "owns at least one" for older clients.
- A newly acquired mount becomes the selected one only if it is the character's first.
- **H and the HUD button always summon the selected mount.** A new "Mounts" list in the character panel shows every mount with its name, route, level and price or drop rate, greyed with the unlock hint when not owned, and a Select button on the owned ones. Selecting never mounts or dismounts by itself; while mounted and out of combat it swaps the mount at once. Other players see the selected mount of the rider in snapshots.
- Choosing a mount the character does not own is refused with no change.

## Dismount rules

All mounts follow the existing rules exactly: mounting needs a living character, out of combat, not escorting, in the open world; attacking, casting, Shadowstep, dashing, taking aggro, Spark Travel, dying, entering a private dungeon, or an arena or duel dismount. A stat reset is refused while mounted ("Dismount before resetting stats."). Outdoor gates and cities keep the rider mounted when the destination allows that mount. The selection survives all of them. The seahorse is the sole underwater mount; crossing between land and underwater dismounts incompatible mounts while preserving selection and ownership. Private dungeons still disallow every mount.

## Tradability

Mounts are not items and cannot be traded, given or sold; ownership is a flag on the character. Only the Raptor quest, the Lizard purchase, the Whistle and the Egg grant a mount, and only the Whistle and Egg are items, both bound. This also closes any duplication route through `SOC-TRADE`.

## What the other tasks must do

- `MOUNT-SERVER`: add `mounts` and `mount`, keep `mount_owned` for the migration, make the speed multiplier a per-mount constant that is 1.6 for all seven, send `mounts` and `mount` in the snapshot, refuse unknown IDs, and add the `mount_licence` use path.
- `MOUNT-SOURCES`: the Raptor quest, the Dune-wrangler shop offer (`mount` field now names the mount), the Windseer hatching offer, the two licence items and drop rolls.
- `MOUNT-CHECK`: purchase gates, bound licences, duplicate-use refusal, save/reload with a legacy horse save, per-mount sprites and one speed.

## Sprites (2026-10-18)

All eight mounts share one pipeline, `scripts/make_mount_sprites.py` (`preview | sheet | build [--replace] | export [--local]`): the models in `scripts/mount_models.py` are drawn by the 3D toon renderer in `scripts/mount_toon.py` in the class sprites' camera and depth encoding, eight facings by two clips (`idle` 4 frames, `run` 8, which is the gait of a mounted traveller), 160x160 with anchor (80,119). PixelFlow holds one sprite per mount, clip and facing (`mount_<id>_<clip>_<facing>`, 16 per mount; `build --replace` discards editor edits, `export` keeps them); `client/assets/mount_<id>.png` + `_depth.png` and `mounts_sprites.txt` are the export.

- **One sheet for every class and both bodies.** `client/mountart.js` lays the rider's `idle` frame (class sprite, depth kept by `MageSprite.frame`) into the mount's frame pixel by pixel on depth. Each mount lists `raise` (world units the rider is lifted onto the saddle), `bob` per frame (the saddle's bounce), `cut` (the rider is hidden below that world height: the legs vanish into the barrel) and `shadow`. A pixel's world height is `cos30 * (AY - y) / PX - depth / 2`.
- **Size and seat per mount:** the models are drawn at the class's scale and multiplied (`scale`: horse 1.3, raptor 1.12, lizard 1.25, sabertooth 1.25, gryphon 1.25) so the rider fits. Gaits: quadrupeds trot on diagonal pairs, the raptor runs on two legs with its tail as a balance, the gryphon beats its wings.
- **Rebirth tints** recolour the coat ramp (`coat` in the atlas metadata) by tone. The canvas horse of `field.js` is only the fallback while the art loads and in stub-sprite test mode.
- **The horse was redesigned** with the others: a stout chestnut with a blaze, a thick mane and tail, a bridle and a gold-trimmed saddle on a red blanket.
- Checks: `node tests/mount-art-ui.cjs` (needs `REAL_SPRITES=1`), `node tests/mount-ui.cjs`, `cargo test mount`.

## Forward horse run playback (Beta 1.28.0)

The saved horse run frames lift each hoof while it travels backwards in model
space (+y is forward), then move it forwards while planted. `MountArt.compose`
plays only the horse's run in reverse source-frame order, `0,7,6,5,4,3,2,1`,
so planted feet push back and lifted feet recover forwards. The remapped index
selects color, depth and saddle bob together. Idle clips and other mounts keep
their existing playback. PixelFlow IDs, source artwork and atlas exports are
preserved; do not also reverse the authoring source without removing this
playback correction. `tests/travel-fixes-ui.cjs` checks every frame in all
eight facings against the actual atlas and verifies the rider's matching bob.

## Achievement route (Beta 1.30.0)

Defeating all ten different Chained Forge bosses also awards the Gryphon directly,
without an egg or hatching fee. This is the same mount and speed; the existing
egg/hatching route remains available. It never adds a duplicate or replaces an
existing mount selection. See [achievements.md](achievements.md).

## Nightmare Steed (Beta 1.34.0)

The seasonal mount grants ownership directly on the eligible kill; no bag
slot or licence is required. Ownership survives event end. It uses the same
riding rules and speed as the other mounts. Its original PixelFlow source
IDs and depth atlas are in `client/assets/mounts_sprites.txt`.
`make_mount_sprites.py build nightmare` and `export` use the existing pipeline;
its authored run gait already plays forwards (do not apply the horse-only
runtime reversal). The focused real-art check is `tests/nightmare-art-ui.cjs`.
See [halloween-hunt.md](halloween-hunt.md).

## Seasonal reindeer and speed (Beta 1.35.0)

All eight mounts use one authoritative 1.6× multiplier (160% of walking speed,
60% faster). Haste, class-relative speed, dismounts and collision retain their
existing order. The mounted gait cadence is 80% of the former 2× travel gait.
The Christmas reindeer grants permanent ownership directly, with no bag slot
and no duplicate or forced selection change. See [christmas-event.md](christmas-event.md).

## Easter candidate: Springtide Bunny

Large original white rabbit, pastel-pink ears, floral saddle and decorated egg
basket. One independent exact 5% roll per eligible real player per Stockholm day
on the summoned Bloomwarden kill. The persisted roll ledger is separate from
quest claims. Grant ownership directly outside inventory; no duplicate or selected
mount replacement. Same 160% walking speed. Sixteen saved PixelFlow sources cover
eight directions and idle/run; colour/depth exports serve all ten class/body rigs.
See easter-event.md and easter-validation.md.

## Sunwoven Stag (private Summer Solstice candidate)

Permanent `sunwoven` ownership is granted directly on a successful eligible
personal daily 5% Birchcrown Guardian kill roll. Inventory capacity does not
affect it. Existing selection, duplicate ownership guards, 160% movement and
all ten class/body depth rigs apply. Original PixelFlow colour/depth exports
have eight directions and idle/run clips; source IDs are in
`client/assets/mounts_sprites.txt`. See summer-solstice-event.md.
## Starflight Rocket (Beta 1.36.0)

`rocket` is a permanent New Year reward: one independent personal 5% chance
per eligible real participant per Stockholm day from the five-fighter
Starfire Rocketeer in Rimeveil. Hires do not roll. Full bags and duplicate
ownership are safe. It follows ordinary collision/movement at the same
160% walking speed as every mount; hovering is cosmetic. Original PixelFlow
idle/run sources cover eight directions and the shared ten-rig depth
compositor. Rules: [new-year-event.md](new-year-event.md).

## Fishing seahorse (1.2.0)

Brynja the Tidehealer in Keelhaven, Rán’s Deep, offers **A Friend Beneath the Tide**
after **Beneath the Maelstrom** at level 35. Bring 10 Pier Sprat and 5 Saltby
Herring from Saltby or any eligible sea coast. Both are common tier-one fish,
so a Twig Rod suffices. This is a one-time ordinary hand-in quest: fish are
consumed only on a valid claim, permanent `seahorse` ownership is granted
directly, and an existing mount selection stays selected. Fishing itself remains
unavailable underwater.

The seahorse travels at 160% of the class’s normal movement speed. It can be
ridden in Rán’s Deep and Nacrehold; underwater private dungeons retain the
no-riding rule. Every ordinary mount is refused underwater; a seahorse is
refused on land. The rules apply on mount input, selection, login, each movement
update and portal/seam arrival. The Deep–Nacrehold seam keeps a seahorse mounted.
Combat, death, Spark Travel, collision and all existing dismount rules remain.

`scripts/seahorse_quest.py` runs after the Fisher overlay in full world sync.
It appends only `deep_seahorse`, using the existing healer without changing
terrain, people or other quests. Original eight-facing idle/swim art is authored
in `mount_models.py`, saved as 16 PixelFlow sprites and exported through
`make_mount_sprites.py`; all ten class/body rigs use the shared depth compositor.

Focused checks: `cargo test underwater_mount`, `cargo test mounts_use_160`,
`python3 tests/seahorse-data.py`, `python3 tests/seahorse-art.py`,
`node tests/seahorse-client.cjs`, and `node tests/seahorse-probe.cjs`.
`tests/seahorse-ui.cjs` is the focused browser check; it needs an approved host
or explicit owner approval for the bounded local runner.

Validation: 13 focused Rust cases pass, including every real map/mount pairing,
real Maelstrom/Tideway crossings, the fish hand-in, duplicate claims and old
mounted saves. The private protocol probe completes the actual quest, verifies
a second player’s rider view, and retains the reward through reconnect and a
private process restart. The quest overlay is byte-stable and changes only that
quest; the existing Fisher preservation check passes. Art checks cover 96 frames,
16 saved PixelFlow sources and 960 real JavaScript depth composites across all
ten class/body rigs. Seven deliberate code/data/art/client faults are caught;
all seven restored underwater Rust cases pass again. Release notes, Swedish
freshness and the client release dry run pass. The browser suite remains pending
explicit permission under the production-host restriction.

Strict Clippy retains the existing unused-helper, `doc_lazy_continuation` and
`single_element_loop` baseline findings. All targets pass with only those three
known categories excluded on the command line; no source suppressions were added.
The Swedish catalogue and 23 locale checks also pass.

## Public release (2026-11-20)

Owner requested deployment of 1.2.0. Client `1.2.0-9ca2ef55` and the prepared
production executable from `9ca2ef55` are live. The approved stop/start took
1.125 seconds. All nine changed public files match the clean release checkout;
the running executable matches the pinned candidate. Public, legacy and bridge
health, production flags, SQLite `quick_check` and the service journal pass.
Fresh previous-executable, running-DB and stopped-DB backups plus the deployment
receipt are under `deploy/backups/seahorse-deploy-20261120T060608Z/`. The prior
client release is retained. The separate fishing test service remains stopped.
Browser suites were not run under the existing host restriction; the non-browser
and real private protocol/persistence checks remain the validation evidence.
