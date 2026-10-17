//! The bank (docs/bank.md): a character's own store, the same in the five big cities. Every number lives here once.
//! The rules are `Character` methods that work on a copy the world assigns whole, so a refused request changes
//! nothing; the range, life and combat checks and the single save are in `world/bank.rs`.
use crate::items::{GM_RARITY, GearInstance, ItemStack, is_gear, item};
use crate::model::Character;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

/// Cells of a new bank, and what each paid expansion adds.
pub const BASE_CELLS: usize = 48;
pub const EXPANSION_CELLS: usize = 12;
/// Gold for each expansion, in the order they are bought; the length is the number of expansions.
pub const EXPANSION_PRICES: [u32; 4] = [10_000, 40_000, 120_000, 300_000];
/// How near the banker the character must stand (the same range as every townsperson).
pub const BANK_RANGE: f64 = 2.8;

#[derive(Clone, Debug, Default, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Bank {
    /// Stacks by catalog ID, like the bags' `inventory`.
    #[serde(default)]
    pub items: Vec<ItemStack>,
    /// The per-copy data of the gear in `items`: one entry for every unit of a gear stack.
    #[serde(default)]
    pub gear: Vec<GearInstance>,
    #[serde(default)]
    pub gold: u32,
    #[serde(default)]
    pub expansions: u8,
}

impl Bank {
    pub fn quantity(&self, id: &str) -> u32 {
        self.items
            .iter()
            .find(|s| s.item == id)
            .map_or(0, |s| s.quantity)
    }
    /// One cell per distinct catalog ID. An ID that has left the catalog is kept but neither counted nor shown.
    pub fn used(&self) -> usize {
        self.items
            .iter()
            .filter(|s| s.quantity > 0 && item(&s.item).is_some())
            .count()
    }
    pub fn capacity(&self) -> usize {
        BASE_CELLS + EXPANSION_CELLS * (self.expansions as usize).min(EXPANSION_PRICES.len())
    }
    /// The gold the next expansion costs; None once all are bought.
    pub fn next_price(&self) -> Option<u32> {
        EXPANSION_PRICES.get(self.expansions as usize).copied()
    }
    /// What the window and the character delete confirmation show: catalog items only.
    pub fn view(&self) -> Value {
        let items: Vec<_> = self
            .items
            .iter()
            .filter(|s| s.quantity > 0 && item(&s.item).is_some())
            .collect();
        let gear: Vec<_> = self
            .gear
            .iter()
            .filter(|g| item(&g.item).is_some())
            .collect();
        json!({"items":items,"gear":gear,"gold":self.gold,"expansions":self.expansions,
            "used":self.used(),"capacity":self.capacity(),"nextPrice":self.next_price()})
    }
    fn add(&mut self, id: &str, quantity: u32) -> Result<(), &'static str> {
        if let Some(stack) = self.items.iter_mut().find(|s| s.item == id) {
            stack.quantity = stack
                .quantity
                .checked_add(quantity)
                .ok_or("That stack is too large for the bank.")?;
        } else {
            self.items.push(ItemStack {
                item: id.into(),
                quantity,
            });
        }
        Ok(())
    }
}

impl Character {
    /// Whether `quantity` more of `id` fit the bags: a stack already counted, or a free cell.
    fn bags_have_room_for(&self, id: &str) -> bool {
        item(id).is_some_and(|i| {
            self.quantity(id) > self.equipped_count(i) || self.bag_used() < self.bag_capacity()
        })
    }
    /// Moves `quantity` loose units of `id` from the bags into the bank. A gear copy keeps all of its data; `copy`
    /// names one loose copy (and then `quantity` must be 1), otherwise the first loose copies go.
    pub fn bank_deposit(
        &mut self,
        id: &str,
        quantity: u32,
        copy: Option<u64>,
    ) -> Result<(), &'static str> {
        let i = item(id).ok_or("Unknown item.")?;
        if i.rarity == GM_RARITY {
            return Err("Game master gear cannot be banked.");
        }
        if quantity == 0 || (copy.is_some() && quantity != 1) {
            return Err("Choose a quantity to store.");
        }
        if quantity > self.quantity(id).saturating_sub(self.equipped_count(i)) {
            return Err("You can only store items you own. Worn pieces must stay on you.");
        }
        if self.bank.quantity(id) == 0 && self.bank.used() >= self.bank.capacity() {
            return Err("The bank is full.");
        }
        let mut next_bank = self.bank.clone();
        next_bank.add(id, quantity)?;
        let mut moved = vec![];
        if is_gear(i) {
            self.materialize_gear_instances();
            let worn = self.equipped_count(i) as usize;
            let loose = self
                .gear_instances
                .iter()
                .filter(|g| g.item == id)
                .skip(worn);
            moved = match copy {
                Some(copy) => loose.filter(|g| g.id == copy).cloned().collect(),
                None => loose.take(quantity as usize).cloned().collect(),
            };
            if moved.len() != quantity as usize {
                return Err("That gear copy is not available to store.");
            }
        } else if copy.is_some() {
            return Err("Only gear comes in separate copies.");
        }
        let ids: Vec<u64> = moved.iter().map(|g| g.id).collect();
        self.gear_instances.retain(|g| !ids.contains(&g.id));
        next_bank.gear.extend(moved);
        self.consume_item(id, quantity);
        // A starter piece that goes into the bank is not handed out again on the next login.
        if i.starter && !self.starters_granted.iter().any(|s| s == id) {
            self.starters_granted.push(id.into());
        }
        self.bank = next_bank;
        Ok(())
    }
    /// Moves `quantity` units of `id` from the bank into the bags. A gear copy gets a new id here, which is appended
    /// after the ones already held, so the worn copies (the first of an ID) never change.
    pub fn bank_withdraw(
        &mut self,
        id: &str,
        quantity: u32,
        copy: Option<u64>,
    ) -> Result<(), &'static str> {
        let i = item(id).ok_or("Unknown item.")?;
        if quantity == 0 || (copy.is_some() && quantity != 1) {
            return Err("Choose a quantity to take.");
        }
        if quantity > self.bank.quantity(id) {
            return Err("The bank does not hold that many.");
        }
        if !self.bags_have_room_for(id) {
            return Err("Your bags are full. Make room first.");
        }
        if self.quantity(id).checked_add(quantity).is_none() {
            return Err("That stack is too large for your bags.");
        }
        let mut moved = vec![];
        if is_gear(i) {
            let copies = self.bank.gear.iter().filter(|g| g.item == id);
            moved = match copy {
                Some(copy) => copies.filter(|g| g.id == copy).cloned().collect(),
                None => copies.take(quantity as usize).cloned().collect(),
            };
            if moved.len() != quantity as usize {
                return Err("Those gear copies are not in the bank.");
            }
        } else if copy.is_some() {
            return Err("Only gear comes in separate copies.");
        }
        // Existing copies first, so the arriving ones are not mistaken for a missing legacy record.
        self.materialize_gear_instances();
        let ids: Vec<u64> = moved.iter().map(|g| g.id).collect();
        self.bank.gear.retain(|g| !ids.contains(&g.id));
        for stack in self.bank.items.iter_mut().filter(|s| s.item == id) {
            stack.quantity -= quantity;
        }
        self.bank.items.retain(|s| s.quantity > 0);
        self.add_item(id, quantity);
        for mut gear in moved {
            gear.id = self.next_gear_id;
            self.next_gear_id += 1;
            self.gear_instances.push(gear);
        }
        Ok(())
    }
    /// Gold between the purse and the bank's separate balance. Nothing else ever reads the bank's gold.
    pub fn bank_gold(&mut self, deposit: bool, amount: u32) -> Result<(), &'static str> {
        if amount == 0 {
            return Err("Choose an amount of gold.");
        }
        if deposit {
            if amount > self.gold {
                return Err("You do not carry that much gold.");
            }
            let banked = self
                .bank
                .gold
                .checked_add(amount)
                .ok_or("The bank cannot hold that much gold.")?;
            self.gold -= amount;
            self.bank.gold = banked;
        } else {
            if amount > self.bank.gold {
                return Err("The bank does not hold that much gold.");
            }
            let carried = self
                .gold
                .checked_add(amount)
                .ok_or("You cannot carry that much gold.")?;
            self.bank.gold -= amount;
            self.gold = carried;
        }
        Ok(())
    }
    /// Buys the next expansion with carried gold. Never refunded.
    pub fn bank_expand(&mut self) -> Result<usize, &'static str> {
        let price = self
            .bank
            .next_price()
            .ok_or("The bank is already at its largest.")?;
        if self.gold < price {
            return Err("You need more gold for this expansion.");
        }
        self.gold -= price;
        self.bank.expansions += 1;
        Ok(self.bank.capacity())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Class;

    const PIECE: &str = "warrior_weapon_sword_l5_gray";
    fn hero() -> Character {
        let mut c = Character::mercenary(Class::Warrior, 20, "Banker Test");
        c.gold = 1_000;
        c
    }
    /// The weapon the hero wears (their starter piece), a gear item with one worn copy.
    fn worn_weapon(c: &Character) -> String {
        let (_, weapon) = c.gear();
        let id = crate::items::equipment(c.look.class, "weapon", weapon)
            .expect("a worn weapon")
            .id
            .clone();
        assert!(c.equipped_count(item(&id).unwrap()) > 0);
        id
    }
    /// Every unit of every item, in the bags, the bank and worn, and the gold of both: what no request may change.
    fn totals(c: &Character) -> (std::collections::BTreeMap<String, u32>, u64) {
        let mut sum = std::collections::BTreeMap::new();
        for s in c.inventory.iter().chain(&c.bank.items) {
            *sum.entry(s.item.clone()).or_insert(0) += s.quantity;
        }
        (sum, c.gold as u64 + c.bank.gold as u64)
    }
    #[test]
    fn a_stack_goes_in_whole_or_in_part_and_comes_back() {
        let mut c = hero();
        c.add_item("slime_gel", 10);
        let before = totals(&c);
        c.bank_deposit("slime_gel", 4, None).unwrap();
        assert_eq!(
            (c.quantity("slime_gel"), c.bank.quantity("slime_gel")),
            (6, 4)
        );
        c.bank_deposit("slime_gel", 6, None).unwrap();
        assert_eq!(c.quantity("slime_gel"), 0);
        assert!(c.inventory.iter().all(|s| s.item != "slime_gel"));
        assert_eq!(c.bank.used(), 1);
        c.bank_withdraw("slime_gel", 3, None).unwrap();
        c.bank_withdraw("slime_gel", 7, None).unwrap();
        assert!(c.bank.items.is_empty());
        assert_eq!(c.quantity("slime_gel"), 10);
        assert_eq!(totals(&c), before);
    }
    #[test]
    fn bad_quantities_and_unknown_items_change_nothing() {
        let mut c = hero();
        c.add_item("slime_gel", 2);
        let before = c.clone();
        for (id, n) in [("slime_gel", 0), ("slime_gel", 3), ("no_such_item", 1)] {
            assert!(c.bank_deposit(id, n, None).is_err(), "{id} {n}");
        }
        assert!(c.bank_deposit("slime_gel", 1, Some(1)).is_err());
        assert!(c.bank_withdraw("slime_gel", 1, None).is_err());
        assert_eq!(c.inventory, before.inventory);
        assert_eq!(c.bank, before.bank);
    }
    #[test]
    fn a_gear_copy_keeps_every_field_through_a_round_trip_and_the_worn_one_stays_worn() {
        let mut c = hero();
        let id = worn_weapon(&c);
        c.add_item(&id, 2);
        c.materialize_gear_instances();
        let copies = |c: &Character| -> Vec<GearInstance> {
            c.gear_instances
                .iter()
                .filter(|g| g.item == id)
                .cloned()
                .collect()
        };
        assert_eq!(copies(&c).len(), 3);
        // The last copy is a refined purple one.
        let mut fancy = copies(&c).pop().unwrap();
        fancy.rarity = "epic".into();
        fancy.rank = 3;
        fancy.attack += 7.;
        fancy.rolled_stats.strength = 5;
        let at = c
            .gear_instances
            .iter()
            .position(|g| g.id == fancy.id)
            .unwrap();
        c.gear_instances[at] = fancy.clone();
        let worn_id = copies(&c)[0].id;
        c.bank_deposit(&id, 1, Some(fancy.id)).unwrap();
        assert_eq!(c.bank.gear, vec![fancy.clone()]);
        assert_eq!(c.quantity(&id), 2);
        assert!(c.gear_instances.iter().all(|g| g.id != fancy.id));
        assert_eq!(copies(&c)[0].id, worn_id);
        c.bank_withdraw(&id, 1, Some(fancy.id)).unwrap();
        let back = c.gear_instances.last().unwrap().clone();
        assert_ne!(back.id, fancy.id, "a withdrawn copy has a new id");
        assert_eq!(
            GearInstance {
                id: fancy.id,
                ..back
            },
            fancy
        );
        assert_eq!(copies(&c)[0].id, worn_id);
        assert!(c.bank.items.is_empty() && c.bank.gear.is_empty());
        // The worn copy itself cannot go, whichever way it is named.
        assert!(c.bank_deposit(&id, 1, Some(worn_id)).is_err());
        assert!(c.bank_deposit(&id, 3, None).is_err());
        assert!(c.bank.gear.is_empty());
    }
    #[test]
    fn a_worn_piece_game_master_gear_and_an_unowned_copy_cannot_be_banked() {
        let mut c = hero();
        let worn = worn_weapon(&c);
        assert_eq!(c.quantity(&worn), 1);
        assert!(c.bank_deposit(&worn, 1, None).is_err());
        let gm = crate::items::GM_GEAR[0];
        c.add_item(gm, 1);
        assert!(c.bank_deposit(gm, 1, None).is_err());
        c.add_item(PIECE, 1);
        c.materialize_gear_instances();
        assert!(c.bank_deposit(PIECE, 1, Some(u64::MAX)).is_err());
        assert!(c.bank.items.is_empty() && c.bank.gear.is_empty());
    }
    #[test]
    fn starter_gear_and_a_licence_can_be_stored_and_a_starter_is_not_granted_again() {
        let mut c = hero();
        let starter = crate::items::ITEMS
            .iter()
            .find(|i| i.starter && i.class == Some(c.look.class) && c.equipped_count(i) == 0)
            .expect("an unworn starter piece")
            .id
            .clone();
        // A save from before the list was kept.
        c.starters_granted.clear();
        let owned = c.quantity(&starter);
        assert!(owned > 0);
        c.bank_deposit(&starter, owned, None).unwrap();
        c.grant_missing_starters();
        assert_eq!(c.quantity(&starter), 0);
        assert!(c.starters_granted.contains(&starter));
        let licence = crate::items::ITEMS
            .iter()
            .find(|i| i.kind == "mount_licence")
            .unwrap()
            .id
            .clone();
        c.add_item(&licence, 1);
        c.bank_deposit(&licence, 1, None).unwrap();
        c.bank_withdraw(&licence, 1, None).unwrap();
        assert_eq!(c.quantity(&licence), 1);
    }
    #[test]
    fn a_full_bank_refuses_a_new_id_but_still_merges_into_a_stack() {
        let mut c = hero();
        let ids: Vec<_> = crate::items::ITEMS
            .iter()
            .filter(|i| i.kind == "material")
            .take(BASE_CELLS + 1)
            .map(|i| i.id.clone())
            .collect();
        assert!(ids.len() > BASE_CELLS);
        for id in &ids {
            c.add_item(id, 2);
        }
        for id in &ids[..BASE_CELLS] {
            c.bank_deposit(id, 1, None).unwrap();
        }
        assert_eq!(c.bank.used(), BASE_CELLS);
        let before = c.clone();
        assert_eq!(
            c.bank_deposit(&ids[BASE_CELLS], 1, None),
            Err("The bank is full.")
        );
        assert_eq!(c.bank, before.bank);
        c.bank_deposit(&ids[0], 1, None).unwrap();
        assert_eq!(c.bank.quantity(&ids[0]), 2);
        // An expansion opens more cells.
        c.gold = EXPANSION_PRICES[0];
        assert_eq!(c.bank_expand(), Ok(BASE_CELLS + EXPANSION_CELLS));
        c.bank_deposit(&ids[BASE_CELLS], 1, None).unwrap();
    }
    #[test]
    fn a_full_bag_refuses_a_withdrawal_that_needs_a_new_cell() {
        let mut c = hero();
        c.add_item("slime_gel", 5);
        c.bank_deposit("slime_gel", 5, None).unwrap();
        let fillers: Vec<_> = crate::items::ITEMS
            .iter()
            .filter(|i| i.kind == "material" && i.id != "slime_gel")
            .map(|i| i.id.clone())
            .collect();
        for id in fillers {
            if c.bag_used() >= c.bag_capacity() {
                break;
            }
            c.add_item(&id, 1);
        }
        assert_eq!(c.bag_used(), c.bag_capacity());
        let before = c.clone();
        assert_eq!(
            c.bank_withdraw("slime_gel", 1, None),
            Err("Your bags are full. Make room first.")
        );
        assert_eq!((&c.inventory, &c.bank), (&before.inventory, &before.bank));
    }
    #[test]
    fn gold_moves_between_the_purse_and_its_own_balance() {
        let mut c = hero();
        c.bank_gold(true, 400).unwrap();
        assert_eq!((c.gold, c.bank.gold), (600, 400));
        assert!(c.bank_gold(true, 601).is_err());
        assert!(c.bank_gold(false, 401).is_err());
        assert!(c.bank_gold(true, 0).is_err());
        c.bank_gold(false, 150).unwrap();
        assert_eq!((c.gold, c.bank.gold), (750, 250));
        c.bank.gold = u32::MAX - 10;
        assert!(c.bank_gold(true, 11).is_err());
        assert_eq!((c.gold, c.bank.gold), (750, u32::MAX - 10));
        c.gold = u32::MAX - 5;
        assert!(c.bank_gold(false, 6).is_err());
    }
    #[test]
    fn expansions_are_bought_in_order_with_carried_gold_only() {
        let mut c = hero();
        c.bank.gold = 10_000_000;
        assert!(c.bank_expand().is_err(), "the bank's gold pays nothing");
        let mut capacity = BASE_CELLS;
        for price in EXPANSION_PRICES {
            c.gold = price - 1;
            assert!(c.bank_expand().is_err());
            c.gold = price;
            capacity += EXPANSION_CELLS;
            assert_eq!(c.bank_expand(), Ok(capacity));
            assert_eq!(c.gold, 0);
        }
        c.gold = u32::MAX;
        assert_eq!(c.bank_expand(), Err("The bank is already at its largest."));
        assert_eq!(c.bank.capacity(), 96);
        assert_eq!(c.bank.next_price(), None);
    }
    #[test]
    fn a_legacy_save_has_an_empty_bank_and_a_new_one_survives_a_reload() {
        let c = hero();
        let mut value = serde_json::to_value(&c).unwrap();
        value.as_object_mut().unwrap().remove("bank");
        let legacy: Character = serde_json::from_value(value).unwrap();
        assert_eq!(legacy.bank, Bank::default());
        assert_eq!(legacy.bank.capacity(), BASE_CELLS);
        let mut c = c;
        c.add_item(PIECE, 2);
        c.bank_deposit(PIECE, 1, None).unwrap();
        c.bank_gold(true, 100).unwrap();
        c.bank.items.push(ItemStack {
            item: "left_the_catalog".into(),
            quantity: 3,
        });
        let again: Character = serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
        assert_eq!(again.bank, c.bank);
        // An ID the catalog no longer has is kept, but neither counted nor shown.
        assert_eq!(again.bank.used(), 1);
        assert_eq!(again.bank.view()["items"].as_array().unwrap().len(), 1);
        assert_eq!(again.bank.quantity("left_the_catalog"), 3);
    }
    #[test]
    fn no_sequence_of_requests_loses_or_copies_an_item_or_gold() {
        let mut c = hero();
        c.gold = 50_000;
        let pool: Vec<String> = ["slime_gel", PIECE]
            .iter()
            .map(|s| s.to_string())
            .chain(
                crate::items::ITEMS
                    .iter()
                    .filter(|i| matches!(i.kind.as_str(), "material" | "potion" | "food"))
                    .take(70)
                    .map(|i| i.id.clone()),
            )
            .collect();
        for id in &pool {
            c.add_item(id, 5);
        }
        let before = totals(&c);
        let start_used = c.bag_used();
        let mut seed = 0x9e3779b97f4a7c15_u64;
        let mut next = move || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            seed
        };
        let (mut ok, mut refused) = (0, 0);
        for _ in 0..6_000 {
            let id = &pool[(next() % pool.len() as u64) as usize];
            let n = (next() % 7) as u32;
            let mut attempt = c.clone();
            let result = match next() % 6 {
                0 | 1 => attempt.bank_deposit(id, n, None),
                2 | 3 => attempt.bank_withdraw(id, n, None),
                4 => attempt.bank_gold(next() % 2 == 0, (next() % 9_000) as u32),
                _ => attempt.bank_expand().map(|_| ()),
            };
            match result {
                Ok(()) => {
                    ok += 1;
                    c = attempt;
                }
                Err(_) => refused += 1,
            }
            let mut after = totals(&c);
            // Expansions spend gold: add back what they cost.
            after.1 += EXPANSION_PRICES[..c.bank.expansions as usize]
                .iter()
                .map(|p| *p as u64)
                .sum::<u64>();
            assert_eq!(after, before);
            // Gear copies and gear stacks agree, in the bags and in the bank.
            let held = c.gear_instances.iter().filter(|g| g.item == PIECE).count() as u32;
            assert!(held <= c.quantity(PIECE));
            let banked = c.bank.gear.iter().filter(|g| g.item == PIECE).count() as u32;
            assert_eq!(banked, c.bank.quantity(PIECE));
            assert!(c.bank.used() <= c.bank.capacity());
            // The bags start over full here; a withdrawal must never make that worse.
            assert!(c.bag_used() <= start_used.max(c.bag_capacity()));
        }
        assert!(ok > 500 && refused > 500, "{ok} ok, {refused} refused");
    }
    #[test]
    fn gear_copy_ids_stay_unique_across_the_bags_and_the_bank() {
        let mut c = hero();
        c.add_item(PIECE, 4);
        c.materialize_gear_instances();
        c.bank_deposit(PIECE, 3, None).unwrap();
        for _ in 0..3 {
            c.bank_withdraw(PIECE, 2, None).ok();
            c.bank_deposit(PIECE, 2, None).ok();
        }
        let mut ids: Vec<_> = c
            .gear_instances
            .iter()
            .chain(&c.bank.gear)
            .map(|g| g.id)
            .collect();
        let all = ids.len();
        ids.sort();
        ids.dedup();
        assert_eq!(ids.len(), all);
        // A counter that fell behind (it is saved, but nothing else keeps it ahead of the bank) catches up.
        c.next_gear_id = 1;
        c.materialize_gear_instances();
        assert!(c.next_gear_id > c.bank.gear.iter().map(|g| g.id).max().unwrap());
    }
}
