# Mounts

These settle `MOUNT-RULES` in [TODO.md](../TODO.md). `MOUNT-SERVER` stores the owned set, `MOUNT-SOURCES` adds the acquisitions below, `MOUNT-UI` adds the picker, `MOUNT-GRYPHON`/`LIZARD`/`RAPTOR`/`SABERTOOTH` draw the sprites and `MOUNT-CHECK` verifies it all. The horse keeps its price (50,000 gold), level (50), vendor (Stable-hand Greta, Skaldholm) and every rule in the README.

## One cosmetic choice at one speed

All five mounts are the **same ability with a different look**: 2× the class's walking speed in the open world, as today (`speed() * 2` in `world.rs`). No mount crosses water, void, cliffs or any collision, and none flies, jumps or changes combat. The gryphon is a ground-runner that spreads its wings in the animation; this avoids new collision, zone-edge and exploit rules (Bifrost Reach's void rings, sealed gates, instance walls) and keeps travel balance identical to the horse. A mount's rank is its price of effort, not its power.

## How each mount is obtained

Each uses a different route, and the later the mount the harder it is. A character's level gates **getting** the mount; once owned there is no riding level.

| Mount | Route | Level | Cost and effort |
| --- | --- | ---: | --- |
| Horse | Shop: Stable-hand Greta, Skaldholm (unchanged) | 50 | 500,000 gold |
| Raptor | Quest chain in the Tanglecrown: *The Banyan Run*, four steps given by Mara Vines (Canopy tracker) | 75 | No gold fee. Kill 25 canopy monsters, bring 10 of the zone's materials, win one elite fight and escort a hatchling back. One-time, class-neutral. |
| Lizard | Shop: a new Dune-wrangler NPC in the Lapis Erg hub (beside Basma Silk) | 80 | 160,000 gold (the price of a level-80 Hero Pack, the same wealth tier as the horse at its level) |
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

All mounts follow the existing rules exactly: mounting needs a living character, out of combat, not escorting, in the open world; attacking, casting, Shadowstep, dashing, taking aggro, Spark Travel, dying, entering a private dungeon, or an arena or duel dismount. A stat reset is refused while mounted ("Dismount before resetting stats."). Outdoor gates and cities keep the rider mounted. The selection survives all of them. There is no mount-specific exception.

## Tradability

Mounts are not items and cannot be traded, given or sold; ownership is a flag on the character. Only the Raptor quest, the Lizard purchase, the Whistle and the Egg grant a mount, and only the Whistle and Egg are items, both bound. This also closes any duplication route through `SOC-TRADE`.

## What the other tasks must do

- `MOUNT-SERVER`: add `mounts` and `mount`, keep `mount_owned` for the migration, make the speed multiplier a per-mount constant that is 2.0 for all five, send `mounts` and `mount` in the snapshot, refuse unknown IDs, and add the `mount_licence` use path.
- `MOUNT-SOURCES`: the Raptor quest, the Dune-wrangler shop offer (`mount` field now names the mount), the Windseer hatching offer, the two licence items and drop rolls.
- `MOUNT-CHECK`: purchase gates, bound licences, duplicate-use refusal, save/reload with a legacy horse save, per-mount sprites and one speed.

## Sprites (2026-10-18)

All five mounts share one pipeline, `scripts/make_mount_sprites.py` (`preview | sheet | build [--replace] | export [--local]`): the models in `scripts/mount_models.py` are drawn by the 3D toon renderer in `scripts/mount_toon.py` in the class sprites' camera and depth encoding, eight facings by two clips (`idle` 4 frames, `run` 8, which is the gait of a mounted traveller), 160x160 with anchor (80,119). PixelFlow holds one sprite per mount, clip and facing (`mount_<id>_<clip>_<facing>`, 16 per mount; `build --replace` discards editor edits, `export` keeps them); `client/assets/mount_<id>.png` + `_depth.png` and `mounts_sprites.txt` are the export.

- **One sheet for every class and both bodies.** `client/mountart.js` lays the rider's `idle` frame (class sprite, depth kept by `MageSprite.frame`) into the mount's frame pixel by pixel on depth. Each mount lists `raise` (world units the rider is lifted onto the saddle), `bob` per frame (the saddle's bounce), `cut` (the rider is hidden below that world height: the legs vanish into the barrel) and `shadow`. A pixel's world height is `cos30 * (AY - y) / PX - depth / 2`.
- **Size and seat per mount:** the models are drawn at the class's scale and multiplied (`scale`: horse 1.3, raptor 1.12, lizard 1.25, sabertooth 1.25, gryphon 1.25) so the rider fits. Gaits: quadrupeds trot on diagonal pairs, the raptor runs on two legs with its tail as a balance, the gryphon beats its wings.
- **Rebirth tints** recolour the coat ramp (`coat` in the atlas metadata) by tone. The canvas horse of `field.js` is only the fallback while the art loads and in stub-sprite test mode.
- **The horse was redesigned** with the others: a stout chestnut with a blaze, a thick mane and tail, a bridle and a gold-trimmed saddle on a red blanket.
- Checks: `node tests/mount-art-ui.cjs` (needs `REAL_SPRITES=1`), `node tests/mount-ui.cjs`, `cargo test mount`.
