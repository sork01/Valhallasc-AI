use crate::items::{GearInstance, equipment, is_gear, is_quest_item, item};
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
    HorizonStep,
    PrismEcho,
    Siltweave,
    LanternKeeper,
    RibbonRush,
    Rootguard,
    Cairnstrike,
    EvergreenSigil,
}

#[derive(Clone, Copy, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "lowercase")]
enum Rarity {
    Rare,
    Epic,
    Legendary,
}

impl Rarity {
    fn gear(rarity: &str) -> Option<Self> {
        match rarity {
            "rare" => Some(Self::Rare),
            "epic" => Some(Self::Epic),
            "legendary" => Some(Self::Legendary),
            _ => None,
        }
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Tier {
    rarity: Rarity,
    skill: u16,
    #[serde(default)]
    min_gear_level: u32,
    pub min_enemy_level: u32,
    pub drop_chance: f64,
}

impl Tier {
    pub fn skill_cap(&self) -> u16 {
        band_cap(self.skill)
    }

    fn quality(&self) -> u8 {
        self.rarity as u8 + 1
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
    pub tiers: Vec<Tier>,
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
    pub fn min_gear_level(&self) -> u32 {
        CATALOG.tiers[self.tier].min_gear_level
    }

    pub fn fits(&self, gear: &GearInstance) -> bool {
        let Some(catalog) = item(&gear.item).filter(|i| !i.starter && is_gear(i)) else {
            return false;
        };
        let tier = &CATALOG.tiers[self.tier];
        catalog.kind == self.kind
            && catalog.required_level >= self.min_gear_level()
            && Rarity::gear(&gear.rarity).is_some_and(|rarity| rarity >= tier.rarity)
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
        #[serde(default)]
        all: bool,
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
    pub attempts: u32,
}

pub fn equipment_skill_cap(gear: &GearInstance) -> u16 {
    item(&gear.item).map_or(0, |piece| gear_skill_cap(piece.required_level))
}

impl Character {
    pub(crate) fn weapon_enchant(&self) -> Option<Enchant> {
        let weapon = equipment(self.look.class, "weapon", self.gear().1)?;
        let copy = self.worn_gear_instance(&weapon.id, 0)?;
        copy.enchant.filter(|enchant| {
            weapon.required_level <= self.level && !copy.broken() && enchant.recipe().kind == "weapon"
        })
    }

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
                    attempts: 1,
                };
                if !self.consume_item(&id, 1) {
                    return Err("That gear copy is unavailable.");
                }
                self.gear_instances.remove(at);
                self.enchant_output(&material.id, material.quantity)?;
                Ok(("Equipment disenchanted.", Some(training)))
            }
            Craft { enchant, all } => {
                self.require_enchanting()?;
                let recipe = enchant.recipe();
                let tier = &CATALOG.tiers[recipe.tier];
                if !self.enchanting.recipes.contains(&enchant)
                    || self.enchanting.proficiency.skill < tier.skill
                {
                    return Err("This recipe requires training and more Enchanting skill.");
                }
                let costs = CATALOG
                    .materials
                    .iter()
                    .zip(recipe.cost)
                    .filter(|(_, amount)| *amount > 0)
                    .map(|(material, amount)| (std::iter::once(material.id.as_str()), amount));
                let attempts = self.produce_recipe(
                    &enchant.item("scroll"),
                    0,
                    all,
                    costs,
                    "You need more enchanting materials.",
                )?;
                Ok((
                    "Enchant scroll crafted.",
                    Some(Training {
                        quality: tier.quality(),
                        cap: tier.skill_cap(),
                        attempts,
                    }),
                ))
            }
            Apply {
                enchant,
                copy,
                expected,
            } => {
                let (at, gear) = self.enchant_target(copy, expected)?;
                let recipe = enchant.recipe();
                if !recipe.fits(gear) {
                    return Err(
                        "This enchantment requires matching equipment of its level and rarity or higher.",
                    );
                }
                if expected == Some(enchant) {
                    return Err("That copy already has this enchantment.");
                }
                let training = Training {
                    quality: enchant.recipe().tier as u8 + 1,
                    cap: equipment_skill_cap(gear),
                    attempts: 1,
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

static DROP_TIERS: LazyLock<Vec<(usize, &'static Tier)>> = LazyLock::new(|| {
    let mut tiers: Vec<_> = CATALOG.tiers.iter().enumerate().collect();
    tiers.sort_by_key(|(index, tier)| std::cmp::Reverse((tier.rarity, *index)));
    tiers
});

pub fn drop_recipe(level: u32, elite: bool, chance: f64, choice: f64) -> Option<Enchant> {
    let bonus = if elite { 3. } else { 1. };
    let mut roll = chance;
    for &(index, tier) in DROP_TIERS.iter() {
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
