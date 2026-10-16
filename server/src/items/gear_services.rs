use super::{Item, is_gear, item};
use crate::model::{Attributes, Character};
use serde::{Deserialize, Serialize};

/// One addressable copy of a catalog piece. `inventory` still holds its total count, so old
/// saves, bag layouts and trades keep their catalog IDs. Values here are rank-zero values.
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct GearInstance {
    pub id: u64,
    pub item: String,
    pub rarity: String,
    pub attack: f64,
    pub defense: f64,
    pub bonus_stats: Attributes,
    #[serde(default)]
    pub rolled_stats: Attributes,
    #[serde(default)]
    pub rank: u8,
}

fn round_one(value: f64) -> f64 {
    (value * 10.).round() / 10.
}
fn scale_stats(stats: &Attributes, factor: f64) -> Attributes {
    Attributes {
        strength: (stats.strength as f64 * factor).round() as u32,
        agility: (stats.agility as f64 * factor).round() as u32,
        intellect: (stats.intellect as f64 * factor).round() as u32,
        stamina: (stats.stamina as f64 * factor).round() as u32,
        dexterity: (stats.dexterity as f64 * factor).round() as u32,
        accuracy: (stats.accuracy as f64 * factor).round() as u32,
    }
}
fn merge_stats(a: &Attributes, b: &Attributes) -> Attributes {
    Attributes {
        strength: ((a.strength as f64 + b.strength as f64) * 0.5 * 1.175).round() as u32,
        agility: ((a.agility as f64 + b.agility as f64) * 0.5 * 1.175).round() as u32,
        intellect: ((a.intellect as f64 + b.intellect as f64) * 0.5 * 1.175).round() as u32,
        stamina: ((a.stamina as f64 + b.stamina as f64) * 0.5 * 1.175).round() as u32,
        dexterity: ((a.dexterity as f64 + b.dexterity as f64) * 0.5 * 1.175).round() as u32,
        accuracy: ((a.accuracy as f64 + b.accuracy as f64) * 0.5 * 1.175).round() as u32,
    }
}
fn next_rarity(rarity: &str) -> Option<&'static str> {
    match rarity {
        "common" => Some("uncommon"),
        "uncommon" => Some("rare"),
        "rare" => Some("epic"),
        _ => None,
    }
}
fn rarity_factor(rarity: &str) -> Option<u32> {
    match rarity {
        "common" => Some(1),
        "uncommon" => Some(2),
        "rare" => Some(4),
        "epic" => Some(8),
        "legendary" => Some(12),
        _ => None,
    }
}
impl GearInstance {
    fn new(id: u64, catalog: &Item) -> Self {
        Self {
            id,
            item: catalog.id.clone(),
            rarity: catalog.rarity.clone(),
            attack: catalog.attack,
            defense: catalog.defense,
            bonus_stats: catalog.bonus_stats.clone(),
            rolled_stats: Attributes::default(),
            rank: 0,
        }
    }
    pub fn effective_attack(&self) -> f64 {
        round_one(self.attack * (1. + self.rank as f64 * 0.04))
    }
    pub fn effective_defense(&self) -> f64 {
        round_one(self.defense * (1. + self.rank as f64 * 0.04))
    }
    pub fn effective_bonus_stats(&self) -> Attributes {
        let combined = Attributes {
            strength: self
                .bonus_stats
                .strength
                .saturating_add(self.rolled_stats.strength),
            agility: self
                .bonus_stats
                .agility
                .saturating_add(self.rolled_stats.agility),
            intellect: self
                .bonus_stats
                .intellect
                .saturating_add(self.rolled_stats.intellect),
            stamina: self
                .bonus_stats
                .stamina
                .saturating_add(self.rolled_stats.stamina),
            dexterity: self
                .bonus_stats
                .dexterity
                .saturating_add(self.rolled_stats.dexterity),
            accuracy: self
                .bonus_stats
                .accuracy
                .saturating_add(self.rolled_stats.accuracy),
        };
        scale_stats(&combined, 1. + self.rank as f64 * 0.04)
    }
    pub fn crystal(&self) -> String {
        format!("refinement_crystal_{}", self.rarity)
    }
    pub fn next_refine_cost(&self) -> Option<(u32, u32)> {
        let rank = u32::from(self.rank) + 1;
        let factor = rarity_factor(&self.rarity)?;
        (rank <= 5).then_some((100 * rank * rank * factor, rank))
    }
}

impl Character {
    /// Converts only missing copies. The existing inventory stacks and equipped catalog IDs stay
    /// unchanged, so legacy saves remain readable and local bag layouts retain their keys.
    pub fn materialize_gear_instances(&mut self) -> bool {
        let mut changed = false;
        self.next_gear_id = self
            .next_gear_id
            .max(self.gear_instances.iter().map(|g| g.id).max().unwrap_or(0) + 1)
            .max(1);
        for stack in &self.inventory {
            let Some(catalog) = item(&stack.item).filter(|i| is_gear(i)) else {
                continue;
            };
            let existing = self
                .gear_instances
                .iter()
                .filter(|g| g.item == stack.item)
                .count();
            for _ in existing..stack.quantity as usize {
                self.gear_instances
                    .push(GearInstance::new(self.next_gear_id, catalog));
                self.next_gear_id += 1;
                changed = true;
            }
        }
        changed
    }
    /// Legacy equipment references are catalog IDs. The first owned copies of each ID are its
    /// worn allocation; all later copies are loose and eligible for a merge or sale.
    pub fn gear_instance_equipped(&self, id: u64) -> bool {
        let Some(g) = self.gear_instances.iter().find(|g| g.id == id) else {
            return false;
        };
        let Some(catalog) = item(&g.item) else {
            return false;
        };
        let worn = self.equipped_count(catalog) as usize;
        self.gear_instances
            .iter()
            .filter(|copy| copy.item == g.item)
            .take(worn)
            .any(|copy| copy.id == id)
    }
    pub fn worn_gear_instance(&self, item_id: &str, occurrence: usize) -> Option<&GearInstance> {
        self.gear_instances
            .iter()
            .filter(|copy| copy.item == item_id)
            .nth(occurrence)
    }
    fn merge_output(&self, first: u64, second: u64) -> Result<GearInstance, &'static str> {
        if self.hp <= 0. {
            return Err("You cannot merge gear while defeated.");
        }
        if first == second {
            return Err("Choose two different copies.");
        }
        let a = self
            .gear_instances
            .iter()
            .find(|g| g.id == first)
            .ok_or("Unknown gear copy.")?;
        let b = self
            .gear_instances
            .iter()
            .find(|g| g.id == second)
            .ok_or("Unknown gear copy.")?;
        if a.item != b.item || a.rarity != b.rarity {
            return Err("Both copies must be the same item and rarity.");
        }
        if self.gear_instance_equipped(first) || self.gear_instance_equipped(second) {
            return Err("Unequip both copies before merging.");
        }
        let rarity = next_rarity(&a.rarity).ok_or("That rarity cannot be merged.")?;
        Ok(GearInstance {
            id: self.next_gear_id,
            item: a.item.clone(),
            rarity: rarity.into(),
            attack: round_one((a.attack + b.attack) * 0.5 * 1.175),
            defense: round_one((a.defense + b.defense) * 0.5 * 1.175),
            bonus_stats: merge_stats(&a.bonus_stats, &b.bonus_stats),
            rolled_stats: merge_stats(&a.rolled_stats, &b.rolled_stats),
            rank: a.rank.min(b.rank),
        })
    }
    pub fn preview_merge(&mut self, first: u64, second: u64) -> Result<GearInstance, &'static str> {
        self.materialize_gear_instances();
        self.merge_output(first, second)
    }
    pub fn merge_gear(&mut self, first: u64, second: u64) -> Result<GearInstance, &'static str> {
        let mut next = self.clone();
        next.materialize_gear_instances();
        let result = next.merge_output(first, second)?;
        let stack = next
            .inventory
            .iter_mut()
            .find(|s| s.item == result.item)
            .ok_or("Missing gear stack.")?;
        if stack.quantity < 2 {
            return Err("Two copies are required.");
        }
        stack.quantity -= 1;
        next.gear_instances
            .retain(|g| g.id != first && g.id != second);
        next.next_gear_id += 1;
        next.gear_instances.push(result.clone());
        if next.bag_used() > next.bag_capacity() {
            return Err("Your bags are full.");
        }
        *self = next;
        Ok(result)
    }
    pub fn preview_refine(&mut self, id: u64) -> Result<(GearInstance, u32, u32), &'static str> {
        self.materialize_gear_instances();
        if self.hp <= 0. {
            return Err("You cannot refine gear while defeated.");
        }
        let current = self
            .gear_instances
            .iter()
            .find(|g| g.id == id)
            .ok_or("Unknown gear copy.")?;
        let (gold, crystals) = current
            .next_refine_cost()
            .ok_or("This gear is already at rank 5.")?;
        let mut result = current.clone();
        result.rank += 1;
        Ok((result, gold, crystals))
    }
    pub fn refine_gear(&mut self, id: u64) -> Result<(GearInstance, u32, u32), &'static str> {
        let mut next = self.clone();
        let (result, gold, crystals) = next.preview_refine(id)?;
        if next.gold < gold {
            return Err("Not enough gold for refinement.");
        }
        let material = result.crystal();
        if next.quantity(&material) < crystals {
            return Err("Not enough matching refinement crystals.");
        }
        next.gold -= gold;
        let stack = next
            .inventory
            .iter_mut()
            .find(|s| s.item == material)
            .ok_or("Missing crystals.")?;
        stack.quantity -= crystals;
        next.inventory.retain(|s| s.quantity > 0);
        let at = next.gear_instances.iter().position(|g| g.id == id).unwrap();
        next.gear_instances[at] = result.clone();
        next.preserve_vitals_after_equipping(self);
        *self = next;
        Ok((result, gold, crystals))
    }
    /// Selects which copy an existing catalog-ID equipment slot uses, and which copy will be
    /// chosen the next time that catalog item is equipped. No ownership or stat comes from input.
    pub fn prefer_gear_instance(&mut self, id: u64) -> Result<(), &'static str> {
        if self.hp <= 0. {
            return Err("You cannot select gear while defeated.");
        }
        let mut next = self.clone();
        next.materialize_gear_instances();
        let at = next
            .gear_instances
            .iter()
            .position(|g| g.id == id)
            .ok_or("Unknown gear copy.")?;
        let copy = next.gear_instances.remove(at);
        let front = next
            .gear_instances
            .iter()
            .position(|g| g.item == copy.item)
            .unwrap_or(next.gear_instances.len());
        next.gear_instances.insert(front, copy);
        next.preserve_vitals_after_equipping(self);
        *self = next;
        Ok(())
    }
    pub fn remove_loose_gear_instances(&mut self, catalog: &Item, count: u32) {
        if self.gear_instances.is_empty() {
            return;
        }
        self.materialize_gear_instances();
        let worn = self.equipped_count(catalog) as usize;
        let ids: Vec<u64> = self
            .gear_instances
            .iter()
            .filter(|g| g.item == catalog.id)
            .skip(worn)
            .take(count as usize)
            .map(|g| g.id)
            .collect();
        self.gear_instances.retain(|g| !ids.contains(&g.id));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Class;

    const PIECE: &str = "warrior_weapon_sword_l5_gray";
    fn character() -> Character {
        let mut c = Character::mercenary(Class::Warrior, 20, "Gear Test");
        c.gold = 100_000;
        c
    }
    #[test]
    fn legacy_stacks_materialize_into_stable_copies_without_changing_equipment() {
        let mut c = character();
        c.add_item(PIECE, 2);
        let before = (
            c.inventory.clone(),
            c.equipment.clone(),
            c.look.clone(),
            c.bag_used(),
        );
        let saved = serde_json::to_value(&c).unwrap();
        let mut legacy = saved.as_object().unwrap().clone();
        legacy.remove("gear_instances");
        legacy.remove("next_gear_id");
        let mut loaded: Character =
            serde_json::from_value(serde_json::Value::Object(legacy)).unwrap();
        assert!(loaded.materialize_gear_instances());
        assert_eq!(
            (
                loaded.inventory.clone(),
                loaded.equipment.clone(),
                loaded.look.clone(),
                loaded.bag_used()
            ),
            before
        );
        let ids: Vec<_> = loaded
            .gear_instances
            .iter()
            .filter(|g| g.item == PIECE)
            .map(|g| g.id)
            .collect();
        assert_eq!(ids.len(), 2);
        assert!(!loaded.materialize_gear_instances());
        let roundtrip: Character =
            serde_json::from_str(&serde_json::to_string(&loaded).unwrap()).unwrap();
        assert_eq!(roundtrip.gear_instances, loaded.gear_instances);
    }
    #[test]
    fn merge_consumes_two_matching_loose_copies_and_persists_the_result() {
        let mut c = character();
        c.add_item(PIECE, 2);
        c.materialize_gear_instances();
        let ids: Vec<_> = c
            .gear_instances
            .iter()
            .filter(|g| g.item == PIECE)
            .map(|g| g.id)
            .collect();
        let base = item(PIECE).unwrap();
        let result = c.merge_gear(ids[0], ids[1]).unwrap();
        assert_eq!(c.quantity(PIECE), 1);
        assert_eq!(result.rarity, "uncommon");
        assert_eq!(result.rank, 0);
        assert_eq!(result.attack, round_one(base.attack * 1.175));
        assert!(
            c.gear_instances
                .iter()
                .all(|g| g.id != ids[0] && g.id != ids[1])
        );
        let loaded: Character = serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
        assert_eq!(
            loaded.gear_instances.iter().find(|g| g.id == result.id),
            Some(&result)
        );
    }
    #[test]
    fn merge_averages_different_rolls_and_keeps_the_lower_refinement_rank() {
        let mut c = character();
        c.add_item(PIECE, 2);
        c.materialize_gear_instances();
        let ids: Vec<_> = c
            .gear_instances
            .iter()
            .filter(|g| g.item == PIECE)
            .map(|g| g.id)
            .collect();
        let first = c
            .gear_instances
            .iter_mut()
            .find(|g| g.id == ids[0])
            .unwrap();
        first.rank = 3;
        first.rolled_stats.strength = 10;
        let second = c
            .gear_instances
            .iter_mut()
            .find(|g| g.id == ids[1])
            .unwrap();
        second.rank = 1;
        second.rolled_stats.agility = 6;
        let result = c.merge_gear(ids[0], ids[1]).unwrap();
        assert_eq!(result.rank, 1);
        assert_eq!(
            (result.rolled_stats.strength, result.rolled_stats.agility),
            (6, 4)
        );
        assert_eq!(
            c.gear_instances
                .iter()
                .find(|g| g.id == result.id)
                .unwrap()
                .effective_bonus_stats()
                .strength,
            ((result.bonus_stats.strength + result.rolled_stats.strength) as f64 * 1.04).round()
                as u32
        );
    }
    #[test]
    fn merge_rejects_invalid_pairs_equipped_copies_and_full_bags_atomically() {
        let mut c = character();
        c.add_item(PIECE, 2);
        c.materialize_gear_instances();
        let ids: Vec<_> = c
            .gear_instances
            .iter()
            .filter(|g| g.item == PIECE)
            .map(|g| g.id)
            .collect();
        let snapshot = serde_json::to_value(&c).unwrap();
        assert!(c.merge_gear(ids[0], ids[0]).is_err());
        assert!(c.merge_gear(ids[0], 999999).is_err());
        assert_eq!(serde_json::to_value(&c).unwrap(), snapshot);
        let worn = c
            .gear_instances
            .iter()
            .find(|g| c.gear_instance_equipped(g.id))
            .unwrap()
            .id;
        assert!(c.merge_gear(worn, ids[0]).is_err());
        assert_eq!(serde_json::to_value(&c).unwrap(), snapshot);
        c.gear_instances
            .iter_mut()
            .find(|g| g.id == ids[1])
            .unwrap()
            .rarity = "rare".into();
        assert!(c.merge_gear(ids[0], ids[1]).is_err());
        c.gear_instances
            .iter_mut()
            .find(|g| g.id == ids[1])
            .unwrap()
            .rarity = "common".into();
        for rarity in ["epic", "legendary"] {
            for id in &ids {
                c.gear_instances
                    .iter_mut()
                    .find(|g| g.id == *id)
                    .unwrap()
                    .rarity = rarity.into();
            }
            assert!(c.merge_gear(ids[0], ids[1]).is_err());
        }
        for id in &ids {
            c.gear_instances
                .iter_mut()
                .find(|g| g.id == *id)
                .unwrap()
                .rarity = "common".into();
        }
        for material in crate::items::ITEMS
            .iter()
            .filter(|i| i.kind == "material")
            .take(20)
        {
            c.add_item(&material.id, 1);
        }
        let full = serde_json::to_value(&c).unwrap();
        assert!(c.merge_gear(ids[0], ids[1]).is_err());
        assert_eq!(serde_json::to_value(&c).unwrap(), full);
    }
    #[test]
    fn refinement_charges_matching_crystals_and_updates_worn_stats_without_compounding() {
        let mut c = character();
        let worn = c.gear().1.to_string();
        let worn_id = crate::items::equipment(Class::Warrior, "weapon", &worn)
            .unwrap()
            .id
            .clone();
        c.materialize_gear_instances();
        let id = c
            .gear_instances
            .iter()
            .find(|g| g.item == worn_id)
            .unwrap()
            .id;
        c.add_item("refinement_crystal_common", 15);
        let before = c.stats();
        for rank in 1..=5 {
            let (preview, cost, crystals) = c.preview_refine(id).unwrap();
            assert_eq!(preview.rank, rank);
            assert_eq!(cost, 100 * u32::from(rank) * u32::from(rank));
            assert_eq!(crystals, u32::from(rank));
            c.refine_gear(id).unwrap();
        }
        assert_eq!(
            c.gear_instances.iter().find(|g| g.id == id).unwrap().rank,
            5
        );
        assert!(c.stats().0 >= before.0);
        assert!(c.refine_gear(id).is_err());
        assert_eq!(c.quantity("refinement_crystal_common"), 0);
        let loaded: Character = serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
        assert_eq!(loaded.stats(), c.stats());
    }
    #[test]
    fn refinement_rejects_missing_payment_and_death_without_changes() {
        let mut c = character();
        c.add_item(PIECE, 1);
        c.materialize_gear_instances();
        let id = c
            .gear_instances
            .iter()
            .find(|g| g.item == PIECE)
            .unwrap()
            .id;
        let before = serde_json::to_value(&c).unwrap();
        assert!(c.refine_gear(id).is_err());
        assert_eq!(serde_json::to_value(&c).unwrap(), before);
        c.add_item("refinement_crystal_common", 1);
        c.hp = 0.;
        let dead = serde_json::to_value(&c).unwrap();
        assert!(c.refine_gear(id).is_err());
        assert_eq!(serde_json::to_value(&c).unwrap(), dead);
    }
    #[test]
    fn selected_copy_changes_worn_stats_and_survives_reload() {
        let mut c = character();
        let variant = c.gear().1.to_string();
        let id = crate::items::equipment(Class::Warrior, "weapon", &variant)
            .unwrap()
            .id
            .clone();
        c.add_item(&id, 1);
        c.materialize_gear_instances();
        let copies: Vec<_> = c
            .gear_instances
            .iter()
            .filter(|g| g.item == id)
            .map(|g| g.id)
            .collect();
        assert_eq!(copies.len(), 2);
        assert!(c.gear_instance_equipped(copies[0]));
        c.gear_instances
            .iter_mut()
            .find(|g| g.id == copies[1])
            .unwrap()
            .attack += 10.;
        let before = c.stats().0;
        c.prefer_gear_instance(copies[1]).unwrap();
        assert!(!c.gear_instance_equipped(copies[0]));
        assert!(c.gear_instance_equipped(copies[1]));
        assert!(
            (c.stats().0 - before - 10. * crate::items::player_attack_scale(c.look.class, c.level))
                .abs()
                < 1e-9
        );
        let loaded: Character = serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
        assert!(loaded.gear_instance_equipped(copies[1]));
        assert_eq!(loaded.stats(), c.stats());
    }
}
