# Bank

These settle `BANK-RULES` in [TODO.md](../TODO.md). `BANK-SERVER` stores the bank and the requests, `BANK-NPC` places the bankers, `BANK-UI` adds the window, `BANK-ART` the sprites and `BANK-CHECK` verifies it all. Every number below lives once, in a `bank` module of the server, and no test may repeat it.

Owner's decisions (2026-10-17): a bank and a banker in **the five big cities** (Alderhaven, Skaldholm, Nacrehold, Astralhollow, Asterion, the same five that offer the stat reset), and the bank belongs to **one character**. The rest was settled on 2026-10-17 from the code as it stands.

## What the bank is

A character's own store, kept in the character's saved state as `bank` (`#[serde(default)]`, so every old save has an empty bank). It is the same bank in all five cities, and nothing in it is shared with the account's other characters.

| Field | Meaning |
| --- | --- |
| `items` | Stacks by catalog ID with a quantity, exactly like the bags' `inventory`. |
| `gear` | The per-copy data (rarity, attack, defense, bonus and rolled stats, rank) of the gear copies that are in the bank, as `GearInstance`. |
| `gold` | A separate balance. |
| `expansions` | How many paid expansions are bought (0 to 4). |

## What can be stored

Anything that sits loose in the bags:

- **Materials, potions and food, loose bags** and every gear piece that is not worn. A gear copy keeps its rarity, rolled stats, rank and refinement, and is given a new id on the way out (as a trade does), so nothing is lost on a round trip.
- **The two mount licences** (`mount_licence`) can be stored. The bank is the character's own, so the licence never leaves them; it is still bound and cannot be traded or sold.

What cannot:

- **Worn pieces.** Only gear above the worn count (`equipped_count`) can go in. The worn allocation is the **first copies of an ID in `gear_instances`**, so a deposit takes copies after those and a withdrawal appends to the end; neither can shift which copy is worn.
- **Game master gear**, the same refusal as a trade. Starter gear can go in, because it can now be sold or banked for good: the character keeps a list of the starter pieces it has been given (`starters_granted`), and the catalog grant on login only hands out pieces that are not on it.
- **Fitted expansion bags** (they are in `bags`, not in the bags' items).
- **Gold above what the character carries,** and anything not in the catalog.

Items whose ID has left the catalog are never touched: the bank keeps them as they are and the window does not show them.

## Capacity

The bank counts cells the way the bags do: **one cell per distinct item ID**, whatever the quantity, and the copies of one gear ID share their cell. Stacks merge on deposit and on withdrawal.

| | Cells |
| ---: | ---: |
| Base | 48 |
| Each paid expansion | +12 |
| Maximum, after four | 96 |

Expansions are bought from the banker in order, with the carried gold, and are never refunded:

| Expansion | Price |
| ---: | ---: |
| 1 | 10,000 |
| 2 | 40,000 |
| 3 | 120,000 |
| 4 | 300,000 |

For scale: the bags go up to 112 cells, the top bag costs 240,000, and the first stat reset at level 50 costs 130,000. The bank is a second room, not a second bag, and the four steps are paid once.

## Fees

**None** for depositing or withdrawing, items or gold. The only gold sink is the expansions. There is no level requirement.

## Gold

A bank balance with `bank_gold` (deposit or withdraw an amount). It is limited only by the largest gold value the game stores (`u32::MAX`), and a request that would pass it is refused whole. **Services use the carried gold only**: the stat reset, bag purchases and Spark Travel never reach into the bank. Death costs XP and not gold, so the balance is only a place to keep it.

## Where and how

- **Where:** one banker in each of the five cities, beside the plaza near the existing service NPC and off every route. Opening the bank, and each deposit, withdrawal, gold move and expansion, needs the banker within **2.8 tiles** (the existing NPC range) in the character's zone. The client closes the window when the hero walks out of range, and the server re-checks on every request, so a stale window does nothing.
- **Refused** while defeated, in combat, or mounted ("Dismount first."), with the same wording style as the stat reset. There is no banker in a dungeon copy, so the range check already refuses it there.
- **The messages** are `bank_open`, `bank_deposit`, `bank_withdraw`, `bank_gold` and `bank_expand`, each naming the banker. The bank's contents travel only in the answer to `bank_open` and after a change, not in every snapshot.
- **Atomic:** every request is checked in full against a copy of the character and then assigned in one step, followed by one save, the way `reset_trained_stats` works. A refused request changes nothing, and because the world handles one message at a time two browsers cannot both withdraw the same item: the second finds it gone.
- **Full:** a deposit is refused when the item needs a new cell and the bank has none; a withdrawal is refused when the item needs a new bag cell and the bags have none (`can_collect`). Neither splits a request: all of it moves or none of it.

## The messages (`BANK-SERVER`)

All five name the banker the window was opened with (`npc`), and the server finds that NPC in the character's zone with a `bank` offer within `BANK_RANGE`. Rules and numbers are in `server/src/bank.rs`; the request handler is `server/src/world/bank.rs`.

| Message | Fields | Effect |
| --- | --- | --- |
| `bank_open` | `npc` | Answers with the bank; nothing changes. |
| `bank_deposit` | `npc`, `item`, `quantity`, optional `copy` | Bags to bank. `copy` names one loose gear copy (then `quantity` is 1); without it the first loose copies go. |
| `bank_withdraw` | `npc`, `item`, `quantity`, optional `copy` | Bank to bags, the same way. A gear copy gets a new id. |
| `bank_gold` | `npc`, `deposit`, `amount` | Gold between the purse and the bank's balance. |
| `bank_expand` | `npc` | Buys the next expansion with carried gold. |

Every answer is one `bank` packet: `ok`, `notice`, the bank (`items`, `gear`, `gold`, `expansions`, `used`, `capacity`, `nextPrice`) and the bag side (`gold`, `inventory`, `gearInstances`, `equipment`, `bags`, `bagCapacity`). A refused request still answers with the unchanged state, so a stale window repairs itself. A refusal before the bank is reached (defeated, in combat, mounted, travelling, out of range, the wrong NPC) is an `error` packet instead. The bank is in no snapshot and not in the `dialogue` packet.

A request is applied to a copy of the character, the copy is written with `Store::save_many` (as a trade does), and only then does it become the live character: if the write fails nothing has moved. The bank's gold and a copy's data are never read by any other system, and `materialize_gear_instances` keeps `next_gear_id` ahead of the banked copies' ids so an id is never given twice.

## How it meets the other systems

- **Rebirth keeps the bank**, gold and expansions included. `docs/rebirth.md` lists it among the things that stay.
- **Quests, merge, refine, sell and trade use the bags only.** A `bring` objective counts what is in the bags, so items in the bank do not count until they are taken out; the quest journal and the banker's dialogue both say so.
- **Bag capacity and the "bags full" messages ignore the bank.** Loot that does not fit still stays on the ground for 60 seconds.
- **Death** does not touch it. A game master character's bank works the same, minus the golden gear.
- **Deleting a character** deletes its bank with it, items and gold. The delete confirmation in the character list says how many items and how much gold the bank holds, so it is never a surprise.
- **Deposit order and display:** the bank keeps the order stacks were first deposited, as the bags do. The window can sort by kind, then level, then name; the server does not store a sort.

## The five bankers

Placed by an idempotent script that `scripts/sync-world.cjs` runs, as `scripts/stat_reset_npcs.py` does for the stewards. The offer is `bank`; the expansion is sold through it.

| City | Banker (id) | What they say |
| --- | --- | --- |
| Alderhaven | Brenna Coinwright (`banker_alderhaven`) | "Gold in your pocket is gold on the road. Leave what you cannot carry with me, and I will keep it as if it were my own." |
| Skaldholm | Hakon Vaultwarden (`banker_skaldholm`) | "The hall's strongroom has held a jarl's ransom. A few spare helms will not trouble it." |
| Nacrehold | Perla Tidekeeper (`banker_nacrehold`) | "Pearls and pennies, shells and swords. The sea keeps nothing but the bank does." |
| Astralhollow | Ilvane Stargaler (`banker_astralhollow`) | "Every deposit is entered in the sky ledger. The stars do not forget, and neither do I." |
| Asterion | Archon Veyl, Keeper of Weights (`banker_asterion`) | "Present what you would store. It will be weighed, named and returned to you unchanged." |

Placed (`scripts/bank_npcs.py`): Alderhaven (39, 82.5) by the fountain, Skaldholm (78, 65.5), Nacrehold (98.5, 93.5), Astralhollow (61, 116), Asterion (88, 92), each at least 2.6 tiles from every NPC, 4 from every portal and 2.5 from every walked route, on clear ground. Every line ends with the quest rule ("Mind that a quest counts only what you carry, not what is in the bank."). The role of Asterion's banker is "Keeper of Weights", with the name "Archon Veyl".

Each also answers when the bank is empty ("The strongroom is yours. Nothing is in it yet.") and when it is open to show the counts of cells used and free. The Swedish text for all of it is part of `BANK-NPC`.

## Verification hooks (for `BANK-SERVER` and `BANK-CHECK`)

- The total of every item ID and of gold, counting the bags, the bank and the worn gear, is the same after **any** sequence of requests (a long seeded random sequence, successful and refused, as an invariant test).
- A gear copy keeps every field through a deposit and withdrawal, and its worn neighbours stay worn.
- Game master gear, a worn piece, an unknown ID, a zero or oversized quantity, a full bank, a full bag, out of range, the wrong zone, defeated, in combat, mounted and a request that names a stack twice are all refused with nothing changed.
- A save, a reload and a legacy save with no `bank` field give the same bank (empty for the legacy one); a rebirth leaves it unchanged; deleting the character removes it.
- Exactly the five bankers exist, one per city, and no other city has one.
