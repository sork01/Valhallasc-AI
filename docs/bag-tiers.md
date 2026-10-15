# Expansion bag rules

This is the `BAG-RULES` decision for the bag catalog and vendor work. A character
has 16 backpack cells and four expansion bag slots. Bag capacity is the sum of
the fitted bags' `bagSlots` values plus 16; each loose item stack uses one cell.
The tier's level is the minimum level to **buy or fit** it, and the price is the
vendor price in gold. These values are fixed by tier, not scaled to the buyer.

| Minimum level | Item ID | Name | Extra cells | Price |
| ---: | --- | --- | ---: | ---: |
| 1 | `linen_satchel` | Linen Satchel | 6 | 500 |
| 10 | `adventurer_satchel` | Adventurer Satchel | 8 | 1,500 |
| 20 | `trail_pack_l20` | Trail Pack | 10 | 4,000 |
| 30 | `ranger_pack_l30` | Ranger Pack | 12 | 9,000 |
| 40 | `expedition_pack_l40` | Expedition Pack | 14 | 18,000 |
| 50 | `traveler_pack` | Traveler Pack | 16 | 35,000 |
| 60 | `pathfinder_pack_l60` | Pathfinder Pack | 18 | 60,000 |
| 70 | `warden_pack_l70` | Warden Pack | 20 | 100,000 |
| 80 | `hero_pack_l80` | Hero Pack | 22 | 160,000 |
| 90 | `sovereign_pack_l90` | Sovereign Pack | 24 | 240,000 |

Linen remains the entry bag at its existing 500-gold price. The existing
Adventurer Satchel and Traveler Pack IDs become the level-10 and level-50 tiers;
their slot counts stay 8 and 16. A character can own several copies of a tier.
There is no class restriction, and traders may show higher tiers as locked.

Buying a bag fits it immediately. With an empty expansion slot, it fills that
slot even if a larger bag is already fitted. With all four slots full, it must
be strictly larger than at least one fitted bag; it replaces the smallest one,
using the earliest slot to break a tie. The old bag is consumed, with no gold
credit. A same-size or smaller purchase with all four slots full is refused
before payment. Four level-90 bags provide the maximum of 112 cells in total.

A level loss never removes a fitted bag or its capacity. Existing saves keep
their exact `bags` IDs and slots, including Adventurer Satchels and Traveler
Packs fitted below their new purchase levels. The old pre-bag save migration
that grants Traveler Packs for overflow remains valid. Level gates apply when
buying or fitting a newly acquired bag; they do not retroactively invalidate
fitted legacy bags.

`scripts/bag_tiers.py` is the tier catalog and trader-offer source. Every zone
generator already requires `node scripts/sync-world.cjs` after generation; that
sync runs the idempotent bag pass before exporting `client/world.js` and
`client/items.js`, so regenerated trader offers keep all ten tiers.

## Enemy drops

Every defeated enemy, including elites, bosses and enemies inside party
instances, makes one independent 2% bag roll. The single named rate is
`BAG_DROP_CHANCE` in `server/src/items.rs`. Gold, material and equipment rolls
are unaffected. A successful roll selects the highest bag tier whose minimum
level does not exceed the enemy's rolled level: levels 1–9 drop Linen,
10–19 Adventurer, and so on through level 90 and above. Thus a level-34
enemy drops the level-30 Ranger Pack. The catalog's `sell` value equals that
tier's vendor price and never exceeds it.

The bag is a common shared ground drop. A party makes one roll for the kill,
then the existing round-robin pickup chooses the next member who can fit it.
Hired mercenaries keep their ordinary loot turn and forfeit a bag if selected.
The recipient fits the bag automatically on pickup; the same minimum level,
four-slot limit and smallest-smaller replacement rule apply. If nobody can fit
it, it stays on the ground until its normal expiry. Fitted bags are bound to
their recipient and cannot be traded or sold as loose items. This avoids a
separate bag-inventory state while preserving the existing save format.
