# Chainforged raid rewards

Implemented in the isolated `feat/raid-rewards` checkout. The raid stays sealed;
this change does not add encounters or release the entrance.

The Chained Forge rewards level-99 legendary equipment. There are **29 item
types**: five class pieces per class (armor, headgear, shoulders, gloves, weapon),
plus neutral pants, necklace, accessory and cloak. A complete outfit has **ten
copies**, including two accessories. The cloak does not count toward set bonuses,
following the existing cloak rule. Each class can fill every slot.

## Guaranteed tables

Each Warden chooses two **different** kinds from its row, without replacement.
Each class-specific piece then picks one of the five classes uniformly, regardless
of who is present. Shared kinds are equally likely to be chosen as class kinds.
Eldmarr also makes two independent weapon selections, so a clear yields **22
orange copies** at the base rebirth multiplier. Rebirth repeats the complete table
per multiplier step. Each copy rolls its five attributes independently and keeps
those rolls through drops, Need/Greed/Pass, trade, bank, saving and reloading.
Only humans participate in raid rolls; mercenaries cannot take these drops.

| Boss | Two different non-weapon kinds | Extra weapons |
| --- | --- | --- |
| `cf_kettil` | armor, headgear, cloak | 0 |
| `cf_ysolt` | shoulders, gloves, pants | 0 |
| `cf_hallgrim` | necklace, accessory, armor | 0 |
| `cf_sigrun` | headgear, cloak, shoulders | 0 |
| `cf_dagfinn` | gloves, pants, necklace | 0 |
| `cf_thorbjorg` | accessory, armor, headgear | 0 |
| `cf_ragnhild` | cloak, shoulders, gloves | 0 |
| `cf_orm` | pants, necklace, accessory | 0 |
| `cf_hildr` | armor, headgear, shoulders | 0 |
| `cf_eldmarr` | gloves, pants, cloak | 2 |

The 60-item world-drop orange pool is unchanged. Chainforged is excluded from
ordinary gear and orange rolls, packs, chests and other bosses. Future encounter
catalog entries use these stable `cf_*` kinds; the tables are already wired into
`World::boss_loot` and `boss_piece_for`.

## Stats and sets

Ranges follow the level-99 purple budget, orange's 1.175 factor, a further 1.10,
and a +/-4% inclusive integer range. Rounding is adjusted so every lowest uncapped
roll exceeds Worldheart's best corresponding slot. Necklace and accessory use
their offensive budgets (base 2 and 1.5), rather than the old five-slot orange
helper's fallback defense budget. Cloaks add attributes without attack or defense.
Accuracy and dexterity keep the existing 20/70 per-copy caps. Raw item sums below
include both rings; character attack scaling, attribute caps and set bonuses apply
later and are not included in these figures.

| Class | Attack | Defense | Stamina | Accuracy | Dexterity |
| --- | --- | --- | --- | --- | --- |
| warrior | 310–336 | 267–286 | 1420–1530 | 190–200 | 670–700 |
| mage | 310–336 | 267–286 | 1420–1530 | 190–200 | 670–700 |
| assassin | 310–336 | 267–286 | 1420–1530 | 190–200 | 670–700 |
| priest | 310–336 | 267–286 | 1420–1530 | 190–200 | 670–700 |
| hunter | 310–336 | 267–286 | 1420–1530 | 190–200 | 670–700 |

Set tiers use eight distinct non-cloak kinds; a second ring is not a ninth kind.
Two pieces grant the class row's 5% stat bonus, four reduce the named skill's
cooldown by 15%, six double the named skill's output, and eight grant **Unbroken
resolve**: a four-second shield for 4% of maximum health and 3% resource recovery,
with the existing 20-second set trigger cooldown. Class rows are authored in
`docs/set-bonuses.md` and generated through `scripts/set_bonuses.py`.

## Signature weapons

Only Eldmarr drops these five weapons. The server determines the equipped weapon,
rolls the proc and computes every effect. A weapon replaces the display name and
adds to the original skill in its existing bar slot; its id, unlock level, cost,
cooldown, learned ranks and saved assignments stay intact. Unequipping returns the
original name and cancels pending damage and Warmth; an ember ward already granted
lasts for its remaining four-second duration. The additions below that deal
damage target monsters; Warmth's extra healing applies outside PvP fights.

| Class / weapon | Proc | Replacement in the original slot |
| --- | --- | --- |
| Warrior / Chainsplitter | 8% on hit: 12-tile forward slag wave; total <=60% of one basic blow, split over at most three foes | Earthshatter -> Slagshatter: four-second burning ground |
| Mage / Cinderwake Staff | 10% on spell hit: six-second orb, four strikes 1.5 seconds apart, each 12% of a basic blow | Arcane Ward -> Cinder Ward: 20% basic-blow pulse at expiry |
| Assassin / Twin Embertongs | Hit builds a four-second burn, up to five stacks; 1% basic-blow damage per stack per second | Knife Ring -> Ember Ring: four-second burning trail behind the caster |
| Priest / Bellows Censer | 8% on effective heal: four-second ember ward for 3% of target maximum health | Mend -> Bellows Mend: next effective heal within 15 seconds gains 10% |
| Hunter / Chainbow | 10% on hit: chain to two other foes at half the hit, <=30% basic blow per target | Arrow Storm -> Chain Storm: one bounce at 20% of a basic blow |

**Later owner decision, 2026-10-22:** procs also affect players. All proc damage
passes `pvp_hit`, its consent and sanctuary checks, defense, dodge, PvP scale,
shield/ward rules and defeat handling. A proc's pre-reduction player budget is at
most 3% of target maximum health (split across delayed ticks); each hero has one
proc per three seconds. A proc/set effect cannot proc another proc. Healing wards
use the existing caster-aware PvP heal factor. Procs never add lifesteal. The full
PvP matrix was not run because tuning is closed and the owner requested focused
checks only.

The caps give single-target expected proc additions below 8% of basic damage:
Warrior <=4.8%, Mage <=4.8% per spell hit, Hunter <=6%; Assassin's capped five-stack
burn is 5% of a basic blow per second with a three-second application cooldown.
These are cap/probability calculations, not new encounter or kill-time calibration.
The proc share of complete future raid fights remains part of RAID-CHECK.

Molten strips in each weapon's fitted animation have a cached mask for a subtle
150 BPM glow. Reduced motion holds it still. A class-specific short impact sound
uses the existing SFX bus/mute/volume controls. Mage orbs, burning patches/trails
and proc flares use the field's existing effect lifecycle.

## Clears to a complete outfit

`scripts/raid_reward_model.py` runs 1,500 seeded pure table simulations per group.
The set includes the cloak and **two rings**. Humans Need a missing usable slot;
Need winners are uniform among eligible humans. Duplicate stat upgrades are not
modeled. There is no demand-aware selection or bad-luck protection.

| Humans (remaining seats hired) | First complete, median clears | Everyone complete, median | Everyone complete, 95th percentile | Worst of 1,500 |
| --- | --- | --- | --- | --- |
| 1 | 4 | 4 | 9 | 18 |
| 5 | 3 | 7 | 12 | 22 |
| 10 | 5 | 12 | 17 | 26 |

## Rebuild and saved characters

Run `python3 scripts/raid_rewards.py`, `python3 scripts/gear_art_catalog.py`,
`python3 scripts/set_bonuses.py`, `node scripts/sync-world.cjs`, then build the
private server. Gear/cloak generators preserve these boss-only catalog entries.
New stats are rolled in the saved-copy ledger; no old item id, stat range or save
schema changed, so **no live-database backfill is needed**.

Artwork: `scripts/chainforged_shapes.py`, `chainforged_assassin_shapes.py` and
`chainforged_hunter_shapes.py`, `chainforged_mage_shapes.py` and
`chainforged_priest_shapes.py` draw original joint-fitted equipment.
`docs/raid-reward-gear-state.txt` lists the 29 jobs. Use
`make_progression_gear.py preview|build|export JOB`, with `VALHALLA_TOOLS` pointing
to the existing Valhalla tool directory in an isolated checkout. Preview before
building. Build creates editable PixelFlow sprites; export reads them back and
preserves edits. Explicit redesigns archive old editor records in `history`;
preserve unchanged class fittings. Avoid the legacy `gear_art_status.py` path,
which would recreate the retired gear backlog. Completed jobs refuse a rebuild without an explicit redesign.
PixelFlow ids and offsets are preserved in `world/gear-art.txt`, for both bodies
and all five clips/eight facings; each piece has a 48x48 icon. Metadata and sprite
bounds include the fitted layers. PixelFlow editor: `/pixelflow/?sprite=<id>`.

## Focused validation

- Rust filter `raid_rewards`, plus the drop-multiplier and set-matrix checks.
- `tests/raid-reward-gear-art.cjs`: all 29 pieces on ten rigs, all 24,480 poses,
  paired equipped/empty pixels, original-silhouette mutation, weapon pulse and
  reduced motion.
- `tests/raid-rewards-ui.cjs`: private server, equipment/tooltip, skill replacement,
  twelve-slot preservation, unequip, reload and Swedish.
- Formatting, Clippy, JavaScript/Python syntax, Swedish catalog and stable generation.

The 12 focused Rust checks passed, including actual rebirth multipliers, original
skill costs/cooldowns, proc consent/caps and the ember ward absorbing both monster
and player hits. Clippy and formatting passed. The complete original art check
passed for all 90 fitted layers and 24,480 poses; focused reruns cover subsequent
owner-requested redesigns. The private equipment UI passed 14 checks, including
paired canvas pixels proving that the Character preview redraws after lazy gear
loads, saved equipment/reload and Swedish replacement names. The set header uses
the display name Chainforged.

Owner art direction (2026-10-22): the Assassin hood follows the pointed wine-red
cowl reference, with a dark lower-face mask. The Warrior set follows the supplied
Battlegear of Might reference: large spiked pauldrons, green plates, gold edges,
teal breast panels and matching fitted gauntlets/greaves. The Assassin outfit
follows the supplied Bloodfang reference: black fitted leather, crimson chevrons,
swept red shoulder blades and broad red cuffs/knee guards. Both references are
interpreted as original joint-fitted cel shapes. The Hunter follows the supplied
Beaststalker reference: beast-head cap, curved ivory shoulder horns, gold-edged
brown leather, pale fur bands and green accents. Warrior/Hunter weapons retain
their molten pulse while their metalwork matches their new outfits. Cloaks have
class-fitted colors for all five classes. The Mage follows the supplied violet-and-gold
reference with a jeweled hood, shoulder globes and a long paneled robe. The Priest
uses the corrected blue-and-ivory reference, with cyan shoulder stones, a floating
halo and gold-edged azure vestments; the mistakenly supplied Mage link was withdrawn. Replaced editor sources remain
in each job's manifest history; builds must preserve those records.

Full equipped male/female hero contact sheets for all five classes are in Sork's
FileDrop, named `Chainforged <Class> - Full Raid Gear.png`. All five latest reference-directed sheets supersede the initial versions.
The raid entrance remains governed by RAID-OPEN; no release is performed here.

Final reference exports passed for **90 current fitted layers / 24,480 poses** across
all five classes and both bodies. Current bounds match the PNGs and all 29 icons
are distinct. There are 487 active editable PixelFlow sprites and 870 unique
saved sprites including superseded history. Five final FileDrop copies were
verified byte-for-byte; receipts are in `test-results/raid-rewards/filedrop-receipts.txt`.
