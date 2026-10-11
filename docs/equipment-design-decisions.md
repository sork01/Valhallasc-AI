# Equipment decisions for the remaining gear work

These decisions settle `G-MERGE-RULES`, `G-REFINE-RULES`, `A55-DECIDE`, and `G-VAULT-ART` in [TODO.md](../TODO.md). The services and art exports are separate backlog tasks. The numbers below are the contract for their server implementation.

## Merging

- Two **unequipped copies of the same catalog item ID and current rarity** merge into one copy. The base item ID, required level, class restriction, slot and worn art stay the same. A merged copy gets the next rarity: common → uncommon → rare → epic. Epic is the cap. Orange items never merge.
- Rolled bonuses may differ between the two inputs. For each stat key, take the rounded arithmetic mean of their values, then apply the next rarity's fixed 17.5% tier multiplier to the entire piece. Missing keys count as zero. The output keeps the union of both sets of keys. This makes the result deterministic and prevents repeatedly merging a single exceptional roll from multiplying it unchecked.
- The output refinement rank is the **lower** input rank. Refinement paid into the higher rank is not refunded. The UI preview must show both input copies, the exact output stats and the rank that survives before confirmation.
- Equipped copies are ineligible. The server selects two explicit instance IDs, locks the character save, checks ownership, life and bag capacity for the resulting stack, then consumes and creates the result in one transaction. A failed request changes nothing.

## Refinement

- Ranks are 0–5. Each rank adds **4% of the piece's unrefined attack, defense and rolled attributes**; gains are calculated from rank 0 each time, so the total at rank 5 is 20%, with no compounding or rounding drift. Round attack/defense to one decimal and attribute points to the nearest integer.
- Rank `r` (1–5) costs `100 × r² × rarity factor` gold and `r` matching refinement crystals. Factors: common 1, uncommon 2, rare 4, epic 8, orange 12. The crystals are a future material catalog entry and are consumed in the same transaction as gold. A preview must show the exact cost and resulting stats.
- Refinement is permitted on equipped gear; the server updates that one owned instance and recomputes derived combat stats before broadcasting a snapshot. Dead characters cannot refine. Merging uses the lower input rank as stated above. Orange pieces can be refined but cannot merge.
- A legacy stack becomes individually addressable only when the player first uses a merge/refine action or receives a rolled item. Its old item ID, count and equipped allocation must survive that conversion exactly.

## Level 55 art

Level 55 intentionally reuses the level-50 silhouette with its own tint and stats. Moonspore quests lead into Asterion and Moonwell within five levels, so a separate 55 set would occupy a short stretch just before the level-60 visual reset. Its existing item IDs and appearance remain the contract. New level-60 art begins a distinct silhouette series.

## Undervault visual direction

The 27 exclusive level-20 pieces use a **bone, iron and cold teal** language: rib-shaped overlapping plates, chipped edges, inset runes and a narrow teal inner glow. They must be new source layers on both bodies for every pose, plus matching icons; a tint of starter gear does not fulfill `G-VAULT-EXPORT`.

| Pieces | Shape direction distinct from starter gear |
| --- | --- |
| Warrior chest, head, shoulders, hands, sword | Ribbed cuirass, broken crown helm, outward split pauldrons, plate claws and a broad nicked blade with a rune fuller. |
| Mage chest, head, shoulders, hands, staff | Long split funerary robe, tall lantern hood, floating shoulder bones, thin rune gloves and a forked bell staff. |
| Assassin chest, head, shoulders, hands, daggers | Short layered grave coat, half skull mask, asymmetric spine shoulder, hooked gauntlets and inward curved paired blades. |
| Priest chest, head, shoulders, hands, mace | Stole over a plated burial robe, candle crown, reliquary shoulder cases, bandaged hands and a cage headed mace. |
| Hunter chest, head, shoulders, hands, bow | Bone scale jerkin, antler visor, fur and rib mantle, claw bracers and a recurved bow with carved limb tips. |
| Shared pants and accessory | A visibly segmented grave greave and a teal rune ring; both work with every class silhouette. |

At full size the 27 shapes should read apart from level-20 ordinary blue gear, the five classes should still read apart from one another, and the icon silhouette should match the worn layer. Keep all IDs, stats and loot sources unchanged.
