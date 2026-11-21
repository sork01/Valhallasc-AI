use crate::items::{GearInstance, is_gear, is_quest_item, item};
use crate::model::Character;
use crate::profession::{band_cap, gear_skill_cap};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::sync::LazyLock;

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "snake_case")]
pub enum Enchant {
    DoubleTap,
    Quickhands,
    Brace,
    SecondWind,
    Slipstream,
    ArcaneBulwark,
    Spellweaver,
    Shieldbreaker,
    PassingSpark,
    GuardianThread,
    ShakeItOff,
    LightningRod,
    RiseFromAsh,
    BorrowedTime,
    Moonstep,
    HeartwoodGrove,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Tier {
    rarity: String,
    skill: u16,
    pub min_enemy_level: u32,
    pub drop_chance: f64,
}

impl Tier {
    pub fn skill_cap(&self) -> u16 {
        band_cap(self.skill)
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Material {
    id: String,
    rarity: String,
    #[serde(rename = "yield")]
    quantity: u32,
}

#[derive(Deserialize)]
pub struct Recipe {
    pub id: Enchant,
    kind: String,
    pub tier: usize,
    pub cooldown: f64,
    cost: [u32; 4],
}

#[derive(Deserialize)]
pub struct Catalog {
    pub tiers: [Tier; 3],
    materials: [Material; 4],
    pub enchants: Vec<Recipe>,
}

pub static CATALOG: LazyLock<Catalog> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/enchanting.txt"))
        .expect("valid enchanting catalog")
});

impl Enchant {
    pub fn recipe(self) -> &'static Recipe {
        CATALOG
            .enchants
            .iter()
            .find(|row| row.id == self)
            .expect("catalog entry for each enchant")
    }
    pub fn item(self, prefix: &str) -> String {
        let id = serde_json::to_value(self).expect("serializable enchant");
        ["enchant", prefix, id.as_str().expect("enchant identifier")].join("_")
    }
}

impl Recipe {
    pub fn fits(&self, gear: &GearInstance) -> bool {
        let Some(catalog) = item(&gear.item).filter(|i| !i.starter && is_gear(i)) else {
            return false;
        };
        let rarity = CATALOG
            .tiers
            .iter()
            .position(|tier| tier.rarity == gear.rarity);
        catalog.kind == self.kind && rarity.is_some_and(|rank| rank >= self.tier)
    }
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub struct Progress {
    #[serde(flatten)]
    pub proficiency: crate::profession::Skill,
    pub recipes: BTreeSet<Enchant>,
    /// Absolute seconds. Re-equipping, relogging and restarting do not reset a proc's cooldown.
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub ready: BTreeMap<Enchant, f64>,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Command {
    Open,
    Study {
        enchant: Enchant,
    },
    Disenchant {
        copy: u64,
        expected: Option<Enchant>,
    },
    Craft {
        enchant: Enchant,
    },
    Apply {
        enchant: Enchant,
        copy: u64,
        expected: Option<Enchant>,
    },
}

pub struct Training {
    pub quality: u8,
    pub cap: u16,
}

pub fn equipment_skill_cap(gear: &GearInstance) -> u16 {
    item(&gear.item).map_or(0, |piece| gear_skill_cap(piece.required_level))
}

impl Character {
    pub fn wears_enchant(&self, enchant: Enchant) -> bool {
        let recipe = enchant.recipe();
        self.worn_slots().into_iter().any(|(slot, piece)| {
            if piece.kind != recipe.kind || piece.required_level > self.level {
                return false;
            }
            let occurrence = usize::from(
                slot == "accessory2" && self.equipment.get("accessory1") == Some(&piece.id),
            );
            self.worn_gear_instance(&piece.id, occurrence)
                .is_some_and(|gear| gear.enchant == Some(enchant) && !gear.broken())
        })
    }

    pub fn learn_enchanting(&mut self) -> Result<(), &'static str> {
        if self.enchanting.proficiency.skill > 0 {
            return Err("You already know Enchanting.");
        }
        self.enchanting.proficiency.initialize(1);
        Ok(())
    }

    /// Operates on a staged character. The controller saves the completed change before publishing it.
    pub fn enchant_action(
        &mut self,
        command: Command,
    ) -> Result<(&'static str, Option<Training>), &'static str> {
        use Command::*;
        match command {
            Open => {
                self.materialize_gear_instances();
                Ok(("", None))
            }
            Study { enchant } => {
                self.require_enchanting()?;
                if self.enchanting.recipes.contains(&enchant) {
                    return Err("You already know this recipe.");
                }
                if !self.consume_item(&enchant.item("recipe"), 1) {
                    return Err("You need the recipe scroll in your bags.");
                }
                self.enchanting.recipes.insert(enchant);
                Ok(("You learned the recipe.", None))
            }
            Disenchant { copy, expected } => {
                self.require_enchanting()?;
                let (at, gear) = self.enchant_target(copy, expected)?;
                let (quality, material) = CATALOG
                    .materials
                    .iter()
                    .enumerate()
                    .find(|(_, m)| m.rarity == gear.rarity)
                    .ok_or("Disenchanting requires green, blue, purple or orange equipment.")?;
                if self.gear_instance_equipped(copy) {
                    return Err("Unequip that copy before disenchanting it.");
                }
                let id = gear.item.clone();
                let training = Training {
                    quality: quality as u8,
                    cap: equipment_skill_cap(gear),
                };
                if !self.consume_item(&id, 1) {
                    return Err("That gear copy is unavailable.");
                }
                self.gear_instances.remove(at);
                self.enchant_output(&material.id, material.quantity)?;
                Ok(("Equipment disenchanted.", Some(training)))
            }
            Craft { enchant } => {
                self.require_enchanting()?;
                let recipe = enchant.recipe();
                let tier = &CATALOG.tiers[recipe.tier];
                if !self.enchanting.recipes.contains(&enchant)
                    || self.enchanting.proficiency.skill < tier.skill
                {
                    return Err("This recipe requires training and more Enchanting skill.");
                }
                for (material, amount) in CATALOG.materials.iter().zip(recipe.cost) {
                    if amount > 0 && !self.consume_item(&material.id, amount) {
                        return Err("You need more enchanting materials.");
                    }
                }
                self.enchant_output(&enchant.item("scroll"), 1)?;
                Ok((
                    "Enchant scroll crafted.",
                    Some(Training {
                        quality: recipe.tier as u8 + 1,
                        cap: tier.skill_cap(),
                    }),
                ))
            }
            Apply {
                enchant,
                copy,
                expected,
            } => {
                let (at, gear) = self.enchant_target(copy, expected)?;
                if !enchant.recipe().fits(gear) {
                    return Err(
                        "This enchantment requires matching equipment of at least its rarity.",
                    );
                }
                if expected == Some(enchant) {
                    return Err("That copy already has this enchantment.");
                }
                let training = Training {
                    quality: enchant.recipe().tier as u8 + 1,
                    cap: equipment_skill_cap(gear),
                };
                if !self.consume_item(&enchant.item("scroll"), 1) {
                    return Err("You need the crafted scroll in your bags.");
                }
                self.gear_instances[at].enchant = Some(enchant);
                Ok(("Enchantment applied.", Some(training)))
            }
        }
    }

    fn enchant_target(
        &self,
        id: u64,
        expected: Option<Enchant>,
    ) -> Result<(usize, &GearInstance), &'static str> {
        let (at, gear) = self
            .gear_instances
            .iter()
            .enumerate()
            .find(|(_, g)| g.id == id)
            .ok_or("That gear copy is unavailable.")?;
        if gear.enchant != expected {
            return Err("That gear copy has changed. Choose it again.");
        }
        if !item(&gear.item).is_some_and(|i| is_gear(i) && !i.starter && !is_quest_item(i)) {
            return Err("That equipment cannot be enchanted or disenchanted.");
        }
        Ok((at, gear))
    }

    fn require_enchanting(&self) -> Result<(), &'static str> {
        (self.enchanting.proficiency.skill > 0)
            .then_some(())
            .ok_or("Learn Enchanting first.")
    }

    fn enchant_output(&mut self, id: &str, quantity: u32) -> Result<(), &'static str> {
        if !self.can_collect(id) || self.quantity(id).checked_add(quantity).is_none() {
            return Err("Your bags are full. Make room first.");
        }
        self.add_item(id, quantity);
        Ok(())
    }
}

pub fn drop_recipe(level: u32, elite: bool, chance: f64, choice: f64) -> Option<Enchant> {
    let bonus = if elite { 3. } else { 1. };
    let mut roll = chance;
    for (index, tier) in CATALOG.tiers.iter().enumerate().rev() {
        if level < tier.min_enemy_level {
            continue;
        }
        let odds = tier.drop_chance * bonus;
        if roll < odds {
            let mut options = CATALOG
                .enchants
                .iter()
                .filter(|recipe| recipe.tier == index);
            let count = options.clone().count();
            return options.nth((choice * count as f64) as usize).map(|r| r.id);
        }
        roll -= odds;
    }
    None
}
