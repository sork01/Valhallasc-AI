//! Cosmetic wardrobe. `Character::look` remains the real equipment, including chest/weapon stats.
use crate::{
    items::{Item, item},
    model::{Character, Class, Look},
};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub const SLOTS: [&str; 7] = [
    "chest",
    "hands",
    "headgear",
    "shoulders",
    "gloves",
    "pants",
    "cloak",
];
pub const HIDE_SLOTS: [&str; 3] = ["headgear", "shoulders", "cloak"];

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Wardrobe {
    pub migrated: bool,
    pub unlocked: BTreeSet<String>,
    pub slots: BTreeMap<String, String>,
}
pub fn kind(slot: &str) -> &str {
    match slot {
        "chest" => "armor",
        "hands" => "weapon",
        _ => slot,
    }
}
fn visible(i: &Item) -> bool {
    SLOTS.iter().any(|s| kind(s) == i.kind) && i.variant.is_some()
}
/// The same mapping is used by the client preview. No change to the saved equipment look.
fn set_piece(look: &mut Look, slot: &str, variant: &str) {
    let field = match slot {
        "headgear" => &mut look.head,
        "shoulders" => &mut look.shoulders,
        "gloves" => &mut look.gloves,
        "pants" => &mut look.pants,
        "cloak" => &mut look.cloak,
        "chest" => match look.class {
            Class::Warrior => &mut look.warrior_armor,
            Class::Mage => &mut look.mage_armor,
            Class::Assassin => &mut look.assassin_armor,
            Class::Priest => &mut look.priest_armor,
            Class::Hunter => &mut look.hunter_armor,
        },
        "hands" => match look.class {
            Class::Warrior => &mut look.warrior_weapon,
            Class::Mage => &mut look.mage_weapon,
            Class::Assassin => &mut look.assassin_weapon,
            Class::Priest => &mut look.priest_weapon,
            Class::Hunter => &mut look.hunter_weapon,
        },
        _ => return,
    };
    *field = variant.into();
}
impl Character {
    pub fn unlock_appearance(&mut self, id: &str) {
        if item(id).is_some_and(crate::items::is_gear) {
            self.wardrobe.unlocked.insert(id.into());
        }
    }
    pub fn collect_owned_appearances(&mut self) {
        let ids: Vec<String> = self
            .inventory
            .iter()
            .filter(|s| s.quantity > 0)
            .map(|s| s.item.clone())
            .chain(self.worn_slots().into_iter().map(|(_, i)| i.id.clone()))
            .collect();
        for id in ids {
            self.unlock_appearance(&id);
        }
    }
    pub fn migrate_wardrobe(&mut self) {
        if self.wardrobe.migrated {
            return;
        }
        self.collect_owned_appearances();
        let ids: Vec<_> = self
            .bank
            .items
            .iter()
            .filter(|s| s.quantity > 0)
            .map(|s| s.item.clone())
            .collect();
        for id in ids {
            self.unlock_appearance(&id);
        }
        self.wardrobe.migrated = true;
    }
    pub fn transmog_price(&self) -> u32 {
        500 + (self.level.clamp(1, 99) - 1) * 19_500 / 98
    }
    fn appearance_allowed(&self, slot: &str, id: &str) -> bool {
        if !SLOTS.contains(&slot) {
            return false;
        }
        if id == "hide" {
            return HIDE_SLOTS.contains(&slot);
        }
        self.wardrobe.unlocked.contains(id)
            && item(id).is_some_and(|i| {
                visible(i)
                    && i.kind == kind(slot)
                    && i.class.is_none_or(|c| c == self.look.class)
                    && (i.rarity != crate::items::GM_RARITY || self.gm)
            })
    }
    pub fn active_transmogs(&self) -> BTreeMap<String, String> {
        if self.wardrobe.slots.is_empty() {
            return BTreeMap::new();
        }
        let worn = self.worn_slots();
        self.wardrobe
            .slots
            .iter()
            .filter(|(s, id)| {
                worn.iter().any(|(slot, _)| slot == s) && self.appearance_allowed(s, id)
            })
            .map(|(s, id)| (s.clone(), id.clone()))
            .collect()
    }
    pub fn appearance_look(&self) -> Look {
        let mut look = self.look.clone();
        for (slot, id) in self.active_transmogs() {
            let variant = if id == "hide" {
                "none"
            } else {
                item(&id)
                    .and_then(|i| i.variant.as_deref())
                    .unwrap_or("none")
            };
            set_piece(&mut look, &slot, variant);
        }
        look
    }
    /// Validate the whole batch before charging. Reverting ("real") is always free, even on empty slots.
    pub fn apply_transmogs(
        &mut self,
        changes: &BTreeMap<String, String>,
    ) -> Result<u32, &'static str> {
        if changes.len() > SLOTS.len() {
            return Err("Invalid appearance selection.");
        }
        let mut fee = 0u32;
        for (slot, id) in changes {
            if !SLOTS.contains(&slot.as_str())
                || (id != "real" && !self.appearance_allowed(slot, id))
            {
                return Err("That appearance is not unlocked or compatible with this slot.");
            }
            if id != "real" && self.wardrobe.slots.get(slot) != Some(id) {
                fee += self.transmog_price();
            }
        }
        if self.gold < fee {
            return Err("You do not have enough money for these appearances.");
        }
        self.gold -= fee;
        for (slot, id) in changes {
            if id == "real" {
                self.wardrobe.slots.remove(slot);
            } else {
                self.wardrobe.slots.insert(slot.clone(), id.clone());
            }
        }
        Ok(fee)
    }
}

#[cfg(test)]
#[path = "transmog_tests.rs"]
mod tests;
