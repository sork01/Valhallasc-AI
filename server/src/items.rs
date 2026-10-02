use crate::model::{Character, Class};
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;

pub const EXTRA_SLOTS: [&str; 7] = [
    "headgear",
    "shoulders",
    "pants",
    "gloves",
    "necklace",
    "accessory1",
    "accessory2",
];

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Item {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub rarity: String,
    pub sell: u32,
    #[serde(default)]
    pub attack: f64,
    #[serde(default)]
    pub defense: f64,
    pub class: Option<Class>,
    pub variant: Option<String>,
    #[serde(default)]
    pub starter: bool,
    #[serde(default, rename = "bagSlots")]
    pub bag_slots: usize,
    /// Food and potions: hit points restored in total.
    #[serde(default)]
    pub heal: f64,
    /// Food: seconds over which `heal` arrives. Potions heal at once.
    #[serde(default)]
    pub duration: f64,
    /// Potions: seconds before any potion can be drunk again.
    #[serde(default)]
    pub cooldown: f64,
}
#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
pub struct ItemStack {
    pub item: String,
    pub quantity: u32,
}
pub static ITEMS: LazyLock<Vec<Item>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/items.txt")).expect("valid item catalog")
});
pub fn unix_now() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_secs())
}
pub fn item(id: &str) -> Option<&'static Item> {
    ITEMS.iter().find(|i| i.id == id)
}
pub fn equipment(class: Class, kind: &str, variant: &str) -> Option<&'static Item> {
    ITEMS
        .iter()
        .find(|i| i.class == Some(class) && i.kind == kind && i.variant.as_deref() == Some(variant))
}
pub fn material(kind: &str) -> &'static str {
    match kind {
        "blue" => "blue_gel",
        "pink" => "pink_gel",
        "yellow" => "golden_gel",
        "beetle" => "ironhide_shell",
        "big" => "royal_jelly",
        "wisp" => "ember_core",
        "spider" => "magma_fang",
        "wraith" => "ash_veil",
        "golem" => "basalt_heart",
        _ => "slime_gel",
    }
}
pub fn equipment_chance(kind: &str) -> f64 {
    match kind {
        "big" => 0.35,
        "golem" => 0.20,
        "wraith" => 0.14,
        "beetle" => 0.12,
        "spider" => 0.10,
        "wisp" => 0.08,
        "blue" | "pink" | "yellow" => 0.05,
        _ => 0.02,
    }
}
pub fn roll_equipment(kind: &str, chance: f64, choice: f64) -> Option<&'static Item> {
    if chance >= equipment_chance(kind) {
        return None;
    }
    let pool: Vec<_> = ITEMS
        .iter()
        .filter(|i| i.rarity == "rare" && i.kind != "material")
        .collect();
    pool.get((choice * pool.len() as f64) as usize).copied()
}
impl Character {
    pub fn bag_capacity(&self) -> usize {
        16 + self
            .bags
            .iter()
            .filter_map(|id| item(id))
            .map(|i| i.bag_slots)
            .sum::<usize>()
    }
    pub fn bag_used(&self) -> usize {
        self.inventory
            .iter()
            .filter(|s| item(&s.item).is_some_and(|i| s.quantity > self.equipped_count(i)))
            .count()
    }
    pub fn can_collect(&self, id: &str) -> bool {
        item(id).is_some_and(|i| {
            i.kind != "bag"
                && (self.quantity(id) > self.equipped_count(i)
                    || self.bag_used() < self.bag_capacity())
        })
    }
    pub fn purchase_bag(&mut self, id: &str, cost: u32) -> Result<usize, &'static str> {
        if self.hp <= 0. {
            return Err("You cannot buy bags while defeated.");
        }
        let bag = item(id)
            .filter(|i| i.kind == "bag" && i.bag_slots > 0)
            .ok_or("Unknown bag.")?;
        if self.gold < cost {
            return Err("You need more gold for this bag.");
        }
        if self.bags.len() < 4 {
            self.bags.push(id.into());
        } else {
            let index = self
                .bags
                .iter()
                .enumerate()
                .filter_map(|(n, id)| {
                    item(id)
                        .filter(|i| i.bag_slots < bag.bag_slots)
                        .map(|i| (n, i.bag_slots))
                })
                .min_by_key(|(_, size)| *size)
                .map(|(n, _)| n)
                .ok_or("All four expansion bag slots are filled.")?;
            self.bags[index] = id.into();
        }
        self.gold -= cost;
        Ok(self.bag_capacity())
    }
    /// Seconds left of the potion cooldown, from the saved wall-clock end (never more than an hour).
    pub fn potion_cooldown_left(&self) -> f64 {
        self.potion_ready.saturating_sub(unix_now()).min(3600) as f64
    }
    pub fn quantity(&self, id: &str) -> u32 {
        self.inventory
            .iter()
            .find(|s| s.item == id)
            .map_or(0, |s| s.quantity)
    }
    pub fn add_item(&mut self, id: &str, quantity: u32) {
        if item(id).is_none() || quantity == 0 {
            return;
        }
        if let Some(stack) = self.inventory.iter_mut().find(|s| s.item == id) {
            stack.quantity = stack.quantity.saturating_add(quantity);
        } else {
            self.inventory.push(ItemStack {
                item: id.into(),
                quantity,
            });
        }
    }
    pub fn equipped_count(&self, i: &Item) -> u32 {
        let extras = self.equipment.values().filter(|id| *id == &i.id).count() as u32;
        if i.class != Some(self.look.class) {
            return extras;
        }
        let (armor, weapon) = self.gear();
        extras
            + u32::from(
                i.variant.as_deref() == Some(if i.kind == "armor" { armor } else { weapon }),
            )
    }
    pub fn gear(&self) -> (&str, &str) {
        match self.look.class {
            Class::Warrior => (&self.look.warrior_armor, &self.look.warrior_weapon),
            Class::Mage => (&self.look.mage_armor, &self.look.mage_weapon),
            Class::Assassin => (&self.look.assassin_armor, &self.look.assassin_weapon),
            Class::Priest => (&self.look.priest_armor, &self.look.priest_weapon),
        }
    }
    pub fn seed_inventory(&mut self) {
        let class = self.look.class;
        let (armor, weapon) = self.gear();
        let ids: Vec<_> = ITEMS
            .iter()
            .filter(|i| {
                i.class == Some(class)
                    && (i.starter
                        || i.variant.as_deref()
                            == Some(if i.kind == "armor" { armor } else { weapon }))
            })
            .map(|i| i.id.clone())
            .collect();
        for id in ids {
            if self.quantity(&id) == 0 {
                self.add_item(&id, 1);
            }
        }
    }
    pub fn equip_owned(&mut self, armor: &str, weapon: &str) -> Result<(), &'static str> {
        if self.hp <= 0. {
            return Err("You cannot change equipment while defeated.");
        }
        for (kind, variant) in [("armor", armor), ("weapon", weapon)] {
            if variant != "none"
                && !equipment(self.look.class, kind, variant)
                    .is_some_and(|i| self.quantity(&i.id) > 0)
            {
                return Err("You must own equipment for your class before equipping it.");
            }
        }
        let mut next = self.clone();
        next.look.equip(armor, weapon)?;
        if next.bag_used() > next.bag_capacity() {
            return Err("Your bags are full. Make room before unequipping gear.");
        }
        *self = next;
        Ok(())
    }
    pub fn equip_slots(
        &mut self,
        slots: &std::collections::BTreeMap<String, String>,
    ) -> Result<(), &'static str> {
        if self.hp <= 0. {
            return Err("You cannot change equipment while defeated.");
        }
        let mut next = self.clone();
        for (slot, id) in slots {
            if !EXTRA_SLOTS.contains(&slot.as_str()) && slot != "chest" && slot != "hands" {
                return Err("Unknown equipment slot.");
            }
            let kind = match slot.as_str() {
                "chest" => "armor",
                "hands" => "weapon",
                "accessory1" | "accessory2" => "accessory",
                _ => slot.as_str(),
            };
            let gear = if id == "none" {
                None
            } else {
                Some(
                    item(id)
                        .filter(|i| {
                            i.kind == kind
                                && i.class.is_none_or(|class| class == self.look.class)
                                && self.quantity(id) > 0
                        })
                        .ok_or("You must own compatible gear for this slot.")?,
                )
            };
            if slot == "chest" || slot == "hands" {
                let variant = gear.and_then(|i| i.variant.as_deref()).unwrap_or("none");
                let (armor, weapon) = next.gear();
                let armor = if slot == "chest" { variant } else { armor }.to_owned();
                let weapon = if slot == "hands" { variant } else { weapon }.to_owned();
                next.look.equip(&armor, &weapon)?;
            } else if gear.is_some() {
                next.equipment.insert(slot.clone(), id.clone());
            } else {
                next.equipment.remove(slot);
            }
        }
        for i in ITEMS.iter() {
            if next.equipped_count(i) > next.quantity(&i.id) {
                if i.kind == "armor" || i.kind == "weapon" {
                    return Err("You must own equipment for your class before equipping it.");
                }
                return Err("Each equipped slot needs its own copy of the item.");
            }
        }
        if next.bag_used() > next.bag_capacity() {
            return Err("Your bags are full. Make room before unequipping gear.");
        }
        *self = next;
        Ok(())
    }
    pub fn stats(&self) -> (f64, f64) {
        let (mut attack, mut defense) = self.look.stats(self.level);
        let a = &self.attributes;
        attack += a.strength as f64
            * if self.look.class == Class::Warrior {
                2.
            } else {
                0.5
            }
            + a.agility as f64
                * if self.look.class == Class::Assassin {
                    2.
                } else {
                    0.5
                }
            + a.intellect as f64
                * if matches!(self.look.class, Class::Mage | Class::Priest) {
                    2.
                } else {
                    0.5
                };
        defense += a.strength as f64 * 0.2;
        for id in self.equipment.values() {
            if let Some(i) = item(id) {
                attack += i.attack;
                defense += i.defense;
            }
        }
        (attack, defense)
    }
    pub fn sell_item(&mut self, id: &str, quantity: u32) -> Result<u32, &'static str> {
        let i = item(id).ok_or("Unknown item.")?;
        if i.starter {
            return Err("Starter gear cannot be sold.");
        }
        let available = self.quantity(id).saturating_sub(self.equipped_count(i));
        if quantity == 0 || quantity > available {
            return Err("You can only sell items you own. Equipped items must be kept.");
        }
        let value = i
            .sell
            .checked_mul(quantity)
            .filter(|value| self.gold.checked_add(*value).is_some())
            .ok_or("That sale is too large.")?;
        let stack = self.inventory.iter_mut().find(|s| s.item == id).unwrap();
        stack.quantity -= quantity;
        self.inventory.retain(|s| s.quantity > 0);
        self.gold += value;
        Ok(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        model::{Look, Point},
        store::Store,
    };
    fn character() -> Character {
        Store::open(std::path::Path::new(":memory:"))
            .unwrap()
            .create(Look::default(), Point::default())
            .unwrap()
            .0
    }
    #[test]
    fn every_attribute_has_a_combat_effect_and_classes_have_specialties() {
        for class in [Class::Warrior, Class::Mage, Class::Assassin, Class::Priest] {
            let mut c = character();
            c.look.class = class;
            c.grant_xp(300);
            let attack = c.stats().0;
            let defense = c.stats().1;
            let hp = c.max_hp();
            for stat in [
                "strength",
                "agility",
                "intellect",
                "stamina",
                "dexterity",
                "accuracy",
            ] {
                c.allocate_stat(stat).unwrap();
            }
            assert_eq!(c.stat_points(), 0);
            assert_eq!(c.stats().0, attack + 3.);
            assert_eq!(c.stats().1, defense + 0.2);
            assert_eq!(c.max_hp(), hp + 8.);
            assert_eq!(c.hp, c.max_hp());
            assert!(c.dodge_chance() > 0. && c.hit_chance() > 0.90);
            assert!(c.attack_cooldown() < class.cooldown());
            assert!(c.crit_chance() > if class == Class::Assassin { 0.28 } else { 0.14 });
            assert!(c.allocate_stat("stamina").is_err());
        }
    }
    #[test]
    fn trained_chances_are_capped_and_dead_players_cannot_train() {
        let mut c = character();
        c.grant_xp(100);
        c.hp = 0.;
        assert!(c.allocate_stat("stamina").is_err());
        assert_eq!(c.attributes.stamina, 0);
        c.attributes.accuracy = 200;
        c.attributes.dexterity = 200;
        c.attributes.agility = 200;
        c.attributes.intellect = 200;
        assert_eq!(c.hit_chance(), 1.);
        assert_eq!(c.dodge_chance(), 0.35);
        assert_eq!(c.crit_chance(), 0.60);
        assert_eq!(c.cooldown_multiplier(), 0.70);
        assert!(c.attack_cooldown() >= c.look.class.duration());
    }
    #[test]
    fn capped_attributes_cannot_consume_more_points() {
        let mut c = character();
        c.level = 100;
        c.attributes.accuracy = 20;
        c.attributes.dexterity = 70;
        let before = c.stat_points();
        assert!(c.allocate_stat("accuracy").is_err());
        assert!(c.allocate_stat("dexterity").is_err());
        assert_eq!(c.stat_points(), before);
        c.allocate_stat("intellect").unwrap();
        assert_eq!(c.stat_points(), before - 1);
    }
    #[test]
    fn deeper_enemies_drop_gear_more_often_and_each_kind_has_its_own_material() {
        let chances: Vec<_> = ["green", "beetle", "wisp", "spider", "wraith", "golem"]
            .iter()
            .map(|k| equipment_chance(k))
            .collect();
        assert!(
            chances[0] < chances[1]
                && chances[2] < chances[3]
                && chances[3] < chances[4]
                && chances[4] < chances[5]
        );
        for (kind, id, sell) in [
            ("wisp", "ember_core", 28),
            ("spider", "magma_fang", 36),
            ("wraith", "ash_veil", 48),
            ("golem", "basalt_heart", 70),
        ] {
            assert_eq!(material(kind), id);
            let i = item(id).expect("the material exists in the catalog");
            assert_eq!((i.kind.as_str(), i.sell), ("material", sell));
        }
    }
    #[test]
    fn loot_rates_and_pool_cover_every_class_and_slot() {
        for kind in ["green", "blue", "pink", "yellow", "beetle", "big"] {
            assert!(roll_equipment(kind, equipment_chance(kind), 0.).is_none());
            for class in [Class::Warrior, Class::Mage, Class::Assassin, Class::Priest] {
                for slot in ["armor", "weapon"] {
                    let pool_size = ITEMS.iter().filter(|i| i.rarity == "rare").count();
                    assert!((0..pool_size).any(|n| {
                        roll_equipment(kind, 0., (n as f64 + 0.5) / pool_size as f64)
                            .is_some_and(|i| i.class == Some(class) && i.kind == slot)
                    }));
                }
            }
        }
        assert!(equipment_chance("big") > equipment_chance("beetle"));
        assert!(equipment_chance("beetle") > equipment_chance("blue"));
        assert!(equipment_chance("blue") > equipment_chance("green"));
    }
    #[test]
    fn ownership_class_and_equipped_copy_are_enforced() {
        let mut c = character();
        assert!(c.equip_owned("azure", "royal").is_err());
        c.add_item("mage_weapon_crystal", 1);
        assert!(c.equip_owned("crimson", "crystal").is_err());
        c.add_item("warrior_weapon_royal", 2);
        c.equip_owned("crimson", "royal").unwrap();
        assert!(c.sell_item("warrior_weapon_royal", 2).is_err());
        assert_eq!(c.sell_item("warrior_weapon_royal", 1).unwrap(), 30);
        assert_eq!(c.quantity("warrior_weapon_royal"), 1);
        assert!(c.sell_item("warrior_weapon_royal", 1).is_err());
        assert_eq!(c.sell_item("mage_weapon_crystal", 1).unwrap(), 30);
        assert_eq!(c.gold, 60);
        c.add_item("slime_gel", 3);
        assert!(c.sell_item("slime_gel", 0).is_err());
        assert!(c.sell_item("slime_gel", 4).is_err());
        assert_eq!(c.sell_item("slime_gel", 3).unwrap(), 9);
        assert!(c.sell_item("slime_gel", 1).is_err());
        c.equip_owned("none", "none").unwrap();
        assert!(c.sell_item("warrior_weapon_sword", 1).is_err());
        c.hp = 0.;
        assert!(c.equip_owned("crimson", "royal").is_err());
    }
    #[test]
    fn oversized_sales_leave_inventory_and_gold_unchanged() {
        let mut c = character();
        c.gold = u32::MAX;
        c.add_item("slime_gel", 1);
        assert!(c.sell_item("slime_gel", 1).is_err());
        assert_eq!(c.quantity("slime_gel"), 1);
        assert_eq!(c.gold, u32::MAX);
    }
    #[test]
    fn finite_bags_allow_stacking_and_gear_swaps_but_refuse_overflow() {
        let mut c = character();
        for i in ITEMS
            .iter()
            .filter(|i| i.kind != "bag" && !(i.class == Some(Class::Warrior) && i.starter))
            .take(16)
        {
            c.add_item(&i.id, 1);
        }
        assert_eq!(c.bag_used(), 16);
        assert_eq!(c.bag_capacity(), 16);
        assert!(c.can_collect("slime_gel"));
        assert!(!c.can_collect("headgear_upgrade"));
        assert!(c.equip_owned("none", "none").is_err());
        assert_eq!(c.gear(), ("crimson", "sword"));
        c.equip_slots(&[("hands".into(), "warrior_weapon_royal".into())].into())
            .unwrap();
        assert_eq!(c.bag_used(), 16);
        assert!(
            c.equip_slots(&[("hands".into(), "none".into())].into())
                .is_err()
        );
        c.gold = 24;
        c.purchase_bag("adventurer_satchel", 24).unwrap();
        assert_eq!(c.bag_capacity(), 24);
        assert_eq!(c.gold, 0);
        assert!(c.can_collect("headgear_upgrade"));
        c.equip_slots(&[("hands".into(), "none".into())].into())
            .unwrap();
        assert_eq!(c.bag_used(), 17);
    }
    #[test]
    fn purchases_validate_funds_life_and_four_bags_and_upgrade_the_smallest() {
        let mut c = character();
        assert!(c.purchase_bag("traveler_pack", 60).is_err());
        c.gold = 500;
        assert!(c.purchase_bag("slime_gel", 1).is_err());
        for _ in 0..4 {
            c.purchase_bag("adventurer_satchel", 24).unwrap();
        }
        assert_eq!(c.bag_capacity(), 48);
        let gold = c.gold;
        assert!(c.purchase_bag("adventurer_satchel", 24).is_err());
        assert_eq!(c.gold, gold);
        c.purchase_bag("traveler_pack", 60).unwrap();
        assert_eq!(c.bag_capacity(), 56);
        assert_eq!(c.bags.len(), 4);
        c.hp = 0.;
        assert!(c.purchase_bag("traveler_pack", 60).is_err());
        assert_eq!(c.bag_capacity(), 56);
    }
    #[test]
    fn nine_slots_validate_ownership_kind_class_and_accessory_copies_atomically() {
        let mut c = character();
        let request = |pairs: &[(&str, &str)]| {
            pairs
                .iter()
                .map(|(slot, id)| (slot.to_string(), id.to_string()))
                .collect()
        };
        assert!(
            c.equip_slots(&request(&[("headgear", "headgear_upgrade")]))
                .is_err()
        );
        c.add_item("headgear_upgrade", 1);
        assert!(
            c.equip_slots(&request(&[("pants", "headgear_upgrade")]))
                .is_err()
        );
        assert!(c.equip_slots(&request(&[("gold", "none")])).is_err());
        c.add_item("mage_weapon_crystal", 1);
        assert!(
            c.equip_slots(&request(&[("hands", "mage_weapon_crystal")]))
                .is_err()
        );
        c.add_item("accessory_upgrade", 1);
        assert!(
            c.equip_slots(&request(&[
                ("headgear", "headgear_upgrade"),
                ("accessory1", "accessory_upgrade"),
                ("accessory2", "accessory_upgrade")
            ]))
            .is_err()
        );
        assert!(c.equipment.is_empty());
        c.add_item("accessory_upgrade", 2);
        c.equip_slots(&request(&[
            ("headgear", "headgear_upgrade"),
            ("accessory1", "accessory_upgrade"),
            ("accessory2", "accessory_upgrade"),
        ]))
        .unwrap();
        assert_eq!(c.stats(), (32., 7.));
        assert!(c.sell_item("accessory_upgrade", 2).is_err());
        assert_eq!(c.sell_item("accessory_upgrade", 1).unwrap(), 25);
        assert!(c.sell_item("accessory_upgrade", 1).is_err());
        c.equip_slots(&request(&[("accessory1", "none")])).unwrap();
        c.sell_item("accessory_upgrade", 1).unwrap();
        assert_eq!(c.stats(), (31., 6.));
        c.equip_slots(&request(&[("chest", "none"), ("hands", "none")]))
            .unwrap();
        assert_eq!(c.stats(), (27., 3.));
        c.hp = 0.;
        assert!(c.equip_slots(&request(&[("headgear", "none")])).is_err());
    }
}
