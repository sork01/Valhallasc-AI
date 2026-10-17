# Rebirth

These settle `REBIRTH-RULES` in [TODO.md](../TODO.md). `REBIRTH-SERVER` stores the state and the `rebirth` message, `REBIRTH-PERKS` implements each perk, `REBIRTH-UI` adds the panel, `REBIRTH-ART` the looks and `REBIRTH-CHECK` verifies the loop. Nothing here is code yet; every constant below is meant to live once, in `world/rebirth.txt` (a JSON table like `world/levels.txt`) and one Rust module, and no test may repeat the numbers.

Owner's decisions (2026-10-17): perks **stack** across rebirths; the **double drop rate covers everything**; quest rewards can be **earned again**. The rest was settled on 2026-10-17 from the code as it stands.

## The ladder

A character may rebirth at **level 50 or more**. The tier is set by the level at that moment:

`tier = (level - 40) / 10`, integer division, for level 50 and up. The level cap is 99.

| Level | 50–59 | 60–69 | 70–79 | 80–89 | 90–99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tier | 1 | 2 | 3 | 4 | 5 |

Levels 91–99 give **nothing more than 90**, so the UI says "90 is the best rebirth" from level 90 on and does not push the player past it. A rebirth at tier T grants **every perk unlocked at tier T or lower, once each** (a tier includes the lower tiers' perks). Later therefore pays more, because it adds kinds of perk, not just size.

## The perk table

Every perk has a **step** added by each rebirth that reaches its unlock tier, and a **cap**. None changes attack, defense, health, damage taken, skill power or skill unlocks.

| Perk | Unlocks at | Each rebirth adds | Cap | What it touches |
| --- | :---: | --- | --- | --- |
| XP bonus | tier 1 (50) | +10% | +50% | All XP the character gains: kills, shared party XP, quest rewards. Not the XP lost on death. |
| Gold bonus | tier 2 (60) | +10% | +50% | Gold piles from kills, quest gold and the price a shop pays for sales. Not player-to-player trades and not the stat-reset price. |
| Extra bag cells | tier 3 (70) | +2 cells | +10 cells | Added to `bag_capacity()` on top of the 16 backpack cells and the four fitted bags (112 at most today, 122 at most reborn). |
| Cheaper Spark Travel | tier 4 (80) | −10% | −50% | Each leg's fare: `LEG_COST` 20 becomes 10 at the cap. |
| Cheaper stat reset | tier 4 (80) | −10% | −50% | The price of `stat_reset_price()`, including its prior-reset multiplier. |
| Double drop rate | tier 5 (90) | ×2, **once** | ×2 | See below. The second and later tier-5 rebirths do not raise it. |
| Reborn mark | tier 1 | — | — | Title, name colour and aura (below). |
| Mount coat tint | tiers 2–5 | one tint per tier reached | — | Cosmetic only, chosen in the Rebirth panel; a mount shows the tint on its coat. |

What was left out of the candidate list, and why:

- **Extra stat points per level.** Attributes feed attack, defense and health, so this is combat power. The elite, dungeon and kill-time tuning (`world/elite-power.txt`, `world/enrage.txt`, `docs/ttk-rules.md`) assumes level-appropriate stats.
- **Higher skill-rank cap.** Ranks are derived from the saved level (`docs/skill-ranks.md`) and are combat power too.
- **Extra skillbar slot.** The bar has 12 slots and a class has ten active skills, so a thirteenth slot would do nothing.

### How perks stack, and why it cannot run away

The character stores only the **count of rebirths per tier** (`rebirth_tiers: [u32; 5]`, `#[serde(default)]`; count `i` is the rebirths done at tier `i + 1`). Every perk is **derived** from it:

`value = min(cap, step × (number of rebirths whose tier is at least the perk's unlock tier))`

Deriving instead of storing totals means a rebalance of `world/rebirth.txt` needs no save migration, and a save cannot hold a total above the cap. The drop perk is `rebirth_tiers[4] > 0`.

The quickest route is repeating the rebirth at 50. It gives only the XP bonus, and that stops at +50% after five rebirths; every other perk needs a rebirth at 60, 70, 80 or 90. Each rebirth needs the first 49 levels again (580,100 XP at base rates, from `world/levels.txt`), so the cap is paid for in play time, not in clicks. Once every perk is capped, a further rebirth only changes the count shown; the preview says "adds nothing new" and the confirmation asks the player to be sure.

Totals at the cap: +50% XP, +50% gold, +10 bag cells, −50% fares, −50% stat-reset price, double drops. Gold with the drop perk can reach about three times (two piles, each +50%); that is accepted and noted for `REBIRTH-CHECK`.

## What resets, what stays

**Reset** (in one atomic save, as `reset_trained_stats` does for stat points):

- Level to 1, XP to 0, HP and resource full.
- Trained attributes to the default (all points back to unspent, which are none at level 1 because points come from the level), `stat_budget_floor` to 0, and `stat_resets` to 0 so the reset price starts again at the first.
- Quest progress: the whole `quests` list is cleared, claimed flags and `completions` included. Quests that find the player by themselves (`auto_level`) are given again by the normal sync.
- The fog of war (`explored`).
- Position: the character moves to the starting city, because a level-1 hero must not be left in a level-90 zone. Mounted state is cleared (rebirth is refused while mounted anyway).
- Gear that needs a higher level than 1 is **taken off into the bags**, the way any gear is, because the level requirement gates wearing. If the bags cannot hold it, the rebirth is refused and the confirmation names how many cells to free.

**Kept:** the account, character id, name and look; friends; fellowship points (`party_points`); gold; inventory, bags, fitted bag expansions and gear copies with their rarity and rank; mounts and the selected mount; discovered Spark Travel masters; kills; game master status; potion and meal cooldowns; every perk and the rebirth counts.

## Where it is offered, and when it is refused

- **Where:** a **Rebirth** panel in the Character window (visible to everyone, disabled with the reason under level 50); a hint on the level-50 level-up banner; and on levels 60, 70, 80 and 90 a one-line notice that a better rebirth is now available. There is no NPC.
- **Confirmation:** a dialog lists what resets and what stays and the exact perks it adds, and asks the player to type **REBIRTH**. The server first answers a `rebirth_preview` with the tier, the perk changes, the cells to free and a **nonce** tied to the character's level and rebirth count and valid for 60 seconds; `rebirth` must carry that nonce, so a stale or scripted client cannot trigger it and a replay fails once the level has dropped to 1.
- **Refused** (the same wording style as the stat reset): level below 50; defeated; in combat (the rule that blocks mounting); mounted; escorting; inside a private dungeon or any party dungeon copy; in an arena or a duel; in the middle of a trade; during Spark Travel; with the bags unable to take the removed gear.

## Double drop rate

Applies to the kill's **credited hero** (the existing `credit_id`; for a mercenary kill that is the hirer), and for a chest to the **opener**. A party's loot is shared by the existing Need/Greed and round-robin rules after the roll, so nothing about sharing changes. A party member who is not credited does not add or remove the doubling; this is accepted so that a seeded kill has one multiplier.

**The rule: the expected number of drops doubles, the quality of a drop does not.** Let `p` be a roll's chance:

- If `2p` is at most 1, the same random draw is compared with `2p`. **No extra draw is made**, so seeded sequences and the existing tests are unchanged.
- If `p` is more than a half (a guaranteed drop is `p = 1`), the roll gives `floor(2p)` whole drops and one more roll for the fraction: a guaranteed drop gives two independent copies, a 33% roll gives 66% (the second copy of a 100% roll draws its own `choice`).
- One helper `doubled(p, multiplier) -> (whole, fraction)` carries this, and every site below calls it; a new drop site that forgets it fails the audit test listed under *Verification*.

| Roll | Today | Doubled |
| --- | --- | --- |
| Gold pile | one per kill | two piles (each with the gold bonus) |
| Material | one per kill | two |
| Bag (`BAG_DROP_CHANCE`) | 2% | 4% |
| Ordinary gear, per rarity (`base_drop_chance`, in `roll_rarity`) | gray 2%, green 1.5%, blue 0.03%, purple 0.01% (and 0.01% orange for elites, each ×5 for elites) | every edge doubled; the sum stays far below 1 |
| Orange (`roll_orange`, `chance_per_kill`) | the rules file's per-kill chance | twice that, by passing the scaled chance to the first draw |
| Outdoor elite tiers (`outdoor_elite_drop_chance`) | green 100%, blue 33%, purple 5% | green 2 copies, blue 66%, purple 10% (gray and orange doubled) |
| Boss and final-boss set pools (`boss_loot`) | each pool rolled once, guaranteed | each pool rolled twice |
| Purple copy of a set piece (`EPIC_SET_DROP_CHANCE`) | 5% per dropped piece | **5% per piece, unchanged**: it is quality, and twice the pieces already gives twice the purple |
| Mount licences | Whistle 4%, Egg 3% | **8% and 6%** |
| Chest | gold ×1, material ×1, 2 equipment rolls, 0.1% orange, 6% dungeon set piece | gold ×2, material ×2, 4 equipment rolls, 0.2%, 12%; the rarity ladder inside an equipment roll (62/30/7.5/0.5) is quality and stays |

Not drops, so not doubled: quest rewards, shop stock, the Gryphon hatching, merge and refinement results, and the stat roll of an orange piece.

How it combines with the existing rules: [epic-set-drops.md](epic-set-drops.md) keeps its 5% and its "cannot merge further" rules; [chests.md](chests.md) keeps its timer, lifetime and placement (the chest's contents are rolled at opening with the opener's multiplier); [mounts.md](mounts.md) keeps its licences bound and Need-only-for-non-owners, only the chance changes. Hired fighters and the Need/Greed pile are untouched.

## Quest rewards are earned again

After the reset every quest can be accepted and claimed again with its XP, gold, gear and class-choice rewards, because the whole `quests` list is gone. A mount reward that is already owned only repeats XP and gold: `grant_mount` already returns false for an owned mount, so the Raptor chain can be done again for its XP and gold alone. Repeatable bounties start at zero completions.

Checks, with the numbers from the code:

- **Low quests stay worth doing.** A quest pays a tenth of the XP its recommended level needs (`levels.txt`: 100 XP to leave level 1, 32,000 at level 49), and the XP bonus applies to it; gold is raised by the gold bonus. The reward for a given quest is exactly what it was on the first run, never less.
- **Gear cannot be farmed faster than the quests allow.** Each quest pays once per rebirth, and a rebirth needs level 50 again, at least 580,100 XP of play at base rates (about 386,700 with the full +50% bonus). Quest gear is therefore bounded by the time of a full climb, no faster than the first time and slower than farming kills.
- **Double drop does not touch quests** (above), and the bag-space check in the claim path still refuses a reward the bags cannot hold.

## How a reborn character is shown

The snapshot carries `reborn: {count, tier}` (the number of rebirths and the **highest tier reached**) for every player, so other players see it:

- **Title:** "Reborn" plus the highest tier as a numeral, "Reborn V", under the name; Swedish "Omfödd V".
- **Name colour** by highest tier: bronze, silver, gold, cyan, rose-white (exact values chosen in `REBIRTH-ART`).
- **Aura or mark** under the feet, five looks by highest tier, cheap enough for the render-cost rules (no `backdrop-filter`, no constantly animated `filter`, one cached sprite per tier).
- The nameplate, the party frame and the friend list show the title; the Character window shows the count, every perk and its progress to the cap.
- One short celebration effect at the rebirth, sent as a single event.

## Verification hooks (for `REBIRTH-PERKS` and `REBIRTH-CHECK`)

- A pure test of the ladder: 49 is refused, 50, 60, 70, 80 and 90 give tiers 1 to 5, 99 gives tier 5.
- A pure test of `doubled`: 0.04 gives 0.08, 0.5 gives 1.0, 1.0 gives two copies, 0.33 gives 0.66, and a multiplier of 1 leaves everything and the random sequence untouched.
- Rate tests over several hundred seeded kills compare a tier-5 character with an unreborn control at the same seed for gold, materials, bags, gear, orange, set pieces, the chest and both licences. The existing gear-drop and set-piece tests keep their unreborn expectations; each gets a doubled twin with a stated tolerance.
- An **audit test** walks the kill-reward code and the chest opener and fails when a drop roll does not go through `doubled`.
- A test that no perk changes attack, defense, health or damage taken, and one that no perk changes skill power; then `scripts/elite-solo-parallel.sh` and `scripts/dungeon-solo-parallel.sh` for one elite and one dungeon, unchanged.
- Stacking: five tier-1 rebirths stop at +50% XP and give no gold, bags or fares; one tier-5 rebirth gives all of them once; a second tier-5 rebirth does not raise the drop multiplier; a legacy save with no `rebirth_tiers` loads as never reborn.
