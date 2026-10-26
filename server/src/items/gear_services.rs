use super::{GM_RARITY, Item, is_gear, item};
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
    /// Wall-clock Unix seconds until which a rolled class piece may be handed to `trade_with`.
    /// Zero means the piece is bound like every other class piece.
    #[serde(default)]
    pub trade_until: u64,
    /// Character ids that took part in the roll that awarded this copy.
    #[serde(default)]
    pub trade_with: Vec<String>,
    /// Durability lost, 0 (new) to `WEAR_MAX` (broken). Stored as wear so that a copy saved before durability existed
    /// loads at full condition. Only a death wears gear; a smith repairs it (docs/durability.md).
    #[serde(default)]
    pub wear: u8,
}

/// What a death did to the worn gear: pieces that lost durability, and pieces that are broken afterwards.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct DeathWear {
    pub worn: u32,
    pub broken: u32,
}

/// Wear is a percentage of the piece's durability; a broken piece has all of it.
pub const WEAR_MAX: u8 = 100;
/// One death wears every worn piece by a tenth of its durability, whatever its level or rarity.
pub const WEAR_PER_DEATH: u8 = 10;
/// Repairing a piece from broken to new costs this share of its sale value.
pub const REPAIR_PRICE_SHARE: f64 = 0.25;

/// How long the winner of a Need/Greed/Pass roll may hand a class piece on to the other voters.
pub const ROLL_TRADE_WINDOW_SECS: u64 = 2 * 60 * 60;

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
    pub fn new(id: u64, catalog: &Item) -> Self {
        Self {
            id,
            item: catalog.id.clone(),
            rarity: catalog.rarity.clone(),
            attack: catalog.attack,
            defense: catalog.defense,
            bonus_stats: catalog.bonus_stats.clone(),
            rolled_stats: Attributes::default(),
            rank: 0,
            trade_until: 0,
            trade_with: vec![],
            wear: 0,
        }
    }
    /// Durability left, 100 for a new piece and 0 for a broken one.
    pub fn durability(&self) -> u8 {
        if item(&self.item).is_some_and(super::hierlooms::is_hierloom) {
            WEAR_MAX
        } else {
            WEAR_MAX.saturating_sub(self.wear)
        }
    }
    /// A broken piece stays worn but gives no attack, defense or attributes.
    pub fn broken(&self) -> bool {
        self.durability() == 0
    }
    /// Opens the two-hour hand-off window for the other voters of the roll that awarded this copy.
    pub fn open_trade_window(&mut self, voters: Vec<String>, now: u64) {
        self.trade_until = now + ROLL_TRADE_WINDOW_SECS;
        self.trade_with = voters;
    }
    pub fn clear_trade_window(&mut self) {
        self.trade_until = 0;
        self.trade_with.clear();
    }
    /// Whether the window is open for `receiver` at `now` (Unix seconds).
    pub fn tradeable_to(&self, receiver: &str, now: u64) -> bool {
        self.trade_until > now && self.trade_with.iter().any(|id| id == receiver)
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
            .max(
                self.gear_instances
                    .iter()
                    .chain(&self.bank.gear)
                    .map(|g| g.id)
                    .max()
                    .unwrap_or(0)
                    + 1,
            )
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
    /// Class pieces are bound to their owner. `item_id` is gear of a class; the copies returned are the
    /// loose ones whose roll window is open for `receiver`, in ledger order.
    pub fn tradeable_copies(&self, item_id: &str, receiver: &str, now: u64) -> Vec<&GearInstance> {
        let worn = item(item_id).map_or(0, |i| self.equipped_count(i)) as usize;
        self.gear_instances
            .iter()
            .filter(|g| g.item == item_id)
            .skip(worn)
            .filter(|g| g.tradeable_to(receiver, now))
            .collect()
    }
    pub fn worn_gear_instance(&self, item_id: &str, occurrence: usize) -> Option<&GearInstance> {
        self.gear_instances
            .iter()
            .filter(|copy| copy.item == item_id)
            .nth(occurrence)
    }
    /// Whether the worn copy that `gear_attributes` pairs with occurrence `occurrence` of `item_id` is broken.
    pub fn worn_broken(&self, item_id: &str, occurrence: usize) -> bool {
        self.worn_gear_instance(item_id, occurrence)
            .is_some_and(GearInstance::broken)
    }
    /// Ledger position of the copy each worn piece uses, in `worn_items` order: repeats of one item take successive
    /// copies, as in `gear_attributes`. A piece with no ledger copy yet has `None`.
    fn worn_copy_positions(&self) -> Vec<(&'static Item, Option<usize>)> {
        let mut seen = std::collections::BTreeMap::<&str, usize>::new();
        self.worn_items()
            .into_iter()
            .map(|piece| {
                let nth = seen.entry(&piece.id).or_default();
                let at = self
                    .gear_instances
                    .iter()
                    .enumerate()
                    .filter(|(_, g)| g.item == piece.id)
                    .nth(*nth)
                    .map(|(at, _)| at);
                *nth += 1;
                (piece, at)
            })
            .collect()
    }
    /// A death: every worn piece loses `WEAR_PER_DEATH` of its durability. Starter and game master gear never wears,
    /// and a piece that is already broken stays worn and broken.
    pub fn wear_worn_gear(&mut self) -> DeathWear {
        self.materialize_gear_instances();
        let mut out = DeathWear::default();
        for (piece, at) in self.worn_copy_positions() {
            if piece.starter || piece.rarity == GM_RARITY || super::hierlooms::is_hierloom(piece) {
                continue;
            }
            let Some(copy) = at.map(|at| &mut self.gear_instances[at]) else {
                continue;
            };
            if !copy.broken() {
                out.worn += 1;
            }
            copy.wear = copy.wear.saturating_add(WEAR_PER_DEATH).min(WEAR_MAX);
            out.broken += u32::from(copy.broken());
        }
        out
    }
    /// What a smith charges to bring this copy back to full durability: a share of its sale value (a rare piece merged to
    /// epic sells for twice), scaled by the wear, never less than one gold for a damaged copy.
    pub fn repair_price(&self, copy: &GearInstance) -> u32 {
        let Some(catalog) =
            item(&copy.item).filter(|i| copy.wear > 0 && !super::hierlooms::is_hierloom(i))
        else {
            return 0;
        };
        let merged = u64::from(catalog.rarity == "rare" && copy.rarity == "epic");
        let value = u64::from(catalog.sell) * (1 + merged);
        let price =
            (value as f64 * REPAIR_PRICE_SHARE * f64::from(copy.wear) / f64::from(WEAR_MAX)).ceil();
        (price as u64).clamp(1, u64::from(u32::MAX)) as u32
    }
    /// Every damaged copy with its repair price, for the smith's window.
    pub fn repair_quote(&self, multiplier: u32) -> Vec<(u64, u32)> {
        self.gear_instances
            .iter()
            .filter(|g| g.wear > 0 && g.durability() < WEAR_MAX)
            .map(|g| (g.id, self.repair_price(g).saturating_mul(multiplier)))
            .collect()
    }
    /// Repairs one copy (`only`) or every damaged copy, for gold. All or nothing, checked on a clone like the other
    /// gear services; the caller checks range and combat. Returns (copies repaired, gold paid).
    pub fn repair_gear(
        &mut self,
        only: Option<u64>,
        multiplier: u32,
    ) -> Result<(u32, u32), &'static str> {
        if self.hp <= 0. {
            return Err("You cannot repair gear while defeated.");
        }
        if self.mounted {
            return Err("Dismount before repairing gear.");
        }
        let mut next = self.clone();
        next.materialize_gear_instances();
        if only.is_some_and(|id| next.gear_instances.iter().all(|g| g.id != id)) {
            return Err("Unknown gear copy.");
        }
        let due: Vec<usize> = next
            .gear_instances
            .iter()
            .enumerate()
            .filter(|(_, g)| g.durability() < WEAR_MAX && only.is_none_or(|id| g.id == id))
            .map(|(at, _)| at)
            .collect();
        if due.is_empty() {
            return Err("Nothing needs repair.");
        }
        let total: u64 = due
            .iter()
            .map(|at| {
                u64::from(
                    next.repair_price(&next.gear_instances[*at])
                        .saturating_mul(multiplier),
                )
            })
            .sum();
        if u64::from(next.gold) < total {
            return Err("You cannot afford that repair.");
        }
        next.gold -= total as u32;
        for at in &due {
            next.gear_instances[*at].wear = 0;
        }
        next.preserve_vitals_after_equipping(self);
        *self = next;
        Ok((due.len() as u32, total as u32))
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
            trade_until: 0,
            trade_with: vec![],
            wear: 0,
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
        result.wear = 0;
        result.clear_trade_window();
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
    use crate::items::player_attack_scale;
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

    // ----- durability (docs/durability.md) -----
    // A rare necklace worth 240 gold with +7 dexterity, and a blue sword with 4.7 attack.
    const NECKLACE: &str = "necklace_upgrade";
    const BLUE_SWORD: &str = "warrior_weapon_sword_l1_blue";
    fn necklace_on() -> Character {
        let mut c = character();
        // A mercenary wears a cloak; start from a bare character.
        c.equipment.clear();
        c.add_item(NECKLACE, 1);
        c.equipment.insert("necklace".into(), NECKLACE.into());
        c.materialize_gear_instances();
        c
    }
    fn wear_of(c: &Character, id: &str) -> u8 {
        c.gear_instances.iter().find(|g| g.item == id).unwrap().wear
    }
    fn set_wear(c: &mut Character, id: &str, wear: u8) {
        c.gear_instances
            .iter_mut()
            .find(|g| g.item == id)
            .unwrap()
            .wear = wear;
    }
    #[test]
    fn a_copy_saved_before_durability_loads_new() {
        let mut saved = serde_json::to_value(GearInstance::new(7, item(PIECE).unwrap())).unwrap();
        saved.as_object_mut().unwrap().remove("wear");
        let copy: GearInstance = serde_json::from_value(saved).unwrap();
        assert_eq!(
            (copy.wear, copy.durability(), copy.broken()),
            (0, 100, false)
        );
    }
    #[test]
    fn a_death_takes_a_tenth_and_ten_deaths_break_a_piece_that_stays_worn() {
        let mut c = necklace_on();
        for death in 1..=9u8 {
            let wear = c.wear_worn_gear();
            assert_eq!(wear_of(&c, NECKLACE), death * 10);
            assert_eq!((wear.worn, wear.broken), (1, 0), "death {death}");
        }
        let wear = c.wear_worn_gear();
        assert_eq!((wear.worn, wear.broken), (1, 1));
        let copy = c
            .gear_instances
            .iter()
            .find(|g| g.item == NECKLACE)
            .unwrap();
        assert_eq!((copy.durability(), copy.broken()), (0, true));
        // Still worn, never lost, and further deaths take nothing more.
        assert_eq!(
            c.equipment.get("necklace").map(String::as_str),
            Some(NECKLACE)
        );
        let wear = c.wear_worn_gear();
        assert_eq!((wear.worn, wear.broken), (0, 1));
        assert_eq!(wear_of(&c, NECKLACE), WEAR_MAX);
    }
    #[test]
    fn starter_and_game_master_gear_never_wears() {
        let mut c = character();
        c.equipment.clear();
        let starter = crate::items::ITEMS
            .iter()
            .find(|i| i.starter && i.kind == "weapon" && i.class == Some(Class::Warrior))
            .unwrap();
        c.add_item(&starter.id, 1);
        c.look
            .equip(
                c.gear().0.to_string().as_str(),
                starter.variant.as_deref().unwrap(),
            )
            .unwrap();
        c.materialize_gear_instances();
        assert_eq!(c.wear_worn_gear(), DeathWear::default());
        assert!(c.gear_instances.iter().all(|g| g.wear == 0));
        let mut gm = character();
        gm.equipment.clear();
        gm.become_gm();
        gm.materialize_gear_instances();
        assert!(gm.worn_items().iter().any(|i| i.rarity == GM_RARITY));
        assert_eq!(gm.wear_worn_gear(), DeathWear::default());
        assert!(gm.gear_instances.iter().all(|g| g.wear == 0));
    }
    #[test]
    fn a_broken_piece_gives_no_attribute_attack_or_set_credit_but_a_worn_one_does() {
        let mut c = necklace_on();
        let dexterity = c.gear_attributes().dexterity;
        set_wear(&mut c, NECKLACE, 90);
        assert_eq!(
            c.gear_attributes().dexterity,
            dexterity,
            "full stats above 0 durability"
        );
        set_wear(&mut c, NECKLACE, WEAR_MAX);
        assert_eq!(
            c.gear_attributes().dexterity,
            dexterity - 7,
            "zero stats at 0"
        );

        let mut c = character();
        c.equipment.clear();
        c.add_item(BLUE_SWORD, 1);
        let armor = c.gear().0.to_string();
        c.look.equip(&armor, "sword_l1_blue").unwrap();
        c.materialize_gear_instances();
        let (attack, defense) = c.stats();
        set_wear(&mut c, BLUE_SWORD, 90);
        assert_eq!(c.stats(), (attack, defense));
        set_wear(&mut c, BLUE_SWORD, WEAR_MAX);
        let (broken_attack, broken_defense) = c.stats();
        let catalog = item(BLUE_SWORD).unwrap();
        // The attack total is scaled by the class curve; the defense total is not.
        let scale = player_attack_scale(c.look.class, c.level);
        // The sword's attribute bonus feeds attack too (a warrior: strength x2, agility and intellect x0.5).
        let bonus = &catalog.bonus_stats;
        let fed = f64::from(bonus.strength) * 2.
            + f64::from(bonus.agility) * 0.5
            + f64::from(bonus.intellect) * 0.5;
        assert!(
            (attack - broken_attack - (catalog.attack + fed) * scale).abs() < 1e-6,
            "{attack} {broken_attack} {scale}"
        );
        // Strength also gives 0.2 defense per point.
        assert!(
            (defense - broken_defense - catalog.defense - f64::from(bonus.strength) * 0.2).abs()
                < 1e-9
        );
    }
    #[test]
    fn a_smith_charges_a_quarter_of_the_sale_value_scaled_by_the_wear() {
        let mut c = necklace_on();
        set_wear(&mut c, NECKLACE, 40);
        let copy = c
            .gear_instances
            .iter()
            .find(|g| g.item == NECKLACE)
            .unwrap()
            .clone();
        assert_eq!(c.repair_price(&copy), 24, "240 x 25% x 40%");
        let mut epic = copy.clone();
        epic.rarity = "epic".into();
        epic.wear = WEAR_MAX;
        assert_eq!(
            c.repair_price(&epic),
            120,
            "a rare piece merged to epic sells for twice"
        );
        let mut tiny = copy;
        tiny.item = PIECE.into();
        tiny.wear = 1;
        assert_eq!(
            c.repair_price(&tiny),
            1,
            "a damaged copy costs at least one gold"
        );
        assert_eq!(
            c.repair_price(&GearInstance::new(1, item(PIECE).unwrap())),
            0
        );
        c.gold = 100;
        assert_eq!(c.repair_gear(None, 1), Ok((1, 24)));
        assert_eq!((c.gold, wear_of(&c, NECKLACE)), (76, 0));
    }
    #[test]
    fn a_repair_is_refused_without_gold_when_defeated_mounted_or_unneeded_and_changes_nothing() {
        let mut c = necklace_on();
        assert_eq!(c.repair_gear(None, 1), Err("Nothing needs repair."));
        set_wear(&mut c, NECKLACE, 40);
        c.gold = 23;
        let before = serde_json::to_string(&c).unwrap();
        assert_eq!(
            c.repair_gear(None, 1),
            Err("You cannot afford that repair.")
        );
        assert_eq!(c.repair_gear(Some(999_999), 1), Err("Unknown gear copy."));
        c.gold = 1_000;
        c.mounted = true;
        assert_eq!(
            c.repair_gear(None, 1),
            Err("Dismount before repairing gear.")
        );
        c.mounted = false;
        c.hp = 0.;
        assert_eq!(
            c.repair_gear(None, 1),
            Err("You cannot repair gear while defeated.")
        );
        c.hp = c.max_hp();
        c.gold = 23;
        assert_eq!(serde_json::to_string(&c).unwrap().len(), before.len());
        assert_eq!(wear_of(&c, NECKLACE), 40);
        c.gold = 1_000;
        let id = c
            .gear_instances
            .iter()
            .find(|g| g.item == NECKLACE)
            .unwrap()
            .id;
        assert_eq!(c.repair_gear(Some(id), 1), Ok((1, 24)));
        assert_eq!(c.repair_gear(Some(id), 1), Err("Nothing needs repair."));
    }
    #[test]
    fn merging_and_refining_restore_full_durability() {
        let mut c = character();
        c.add_item(PIECE, 2);
        c.materialize_gear_instances();
        for g in c.gear_instances.iter_mut().filter(|g| g.item == PIECE) {
            g.wear = 50;
        }
        let ids: Vec<_> = c
            .gear_instances
            .iter()
            .filter(|g| g.item == PIECE)
            .map(|g| g.id)
            .collect();
        let merged = c.merge_gear(ids[0], ids[1]).unwrap();
        assert_eq!(merged.wear, 0);
        c.add_item("refinement_crystal_common", 5);
        let mut c = character();
        c.add_item(PIECE, 1);
        c.add_item("refinement_crystal_common", 5);
        c.materialize_gear_instances();
        set_wear(&mut c, PIECE, 60);
        let id = c
            .gear_instances
            .iter()
            .find(|g| g.item == PIECE)
            .unwrap()
            .id;
        let (refined, _, _) = c.refine_gear(id).unwrap();
        assert_eq!((refined.rank, refined.wear), (1, 0));
        assert_eq!(wear_of(&c, PIECE), 0);
    }
}
