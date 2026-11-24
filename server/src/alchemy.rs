//! Shared Alchemy catalog and saved character state.
use crate::model::Point;
use crate::profession::{SKILL_BAND, Skill, gathering_requirement};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::sync::LazyLock;

pub const MAX_SKILL: u16 = 600;
pub const WORKSHOP: &str = "alchemy_workshop";
pub const TRAINER: &str = "alchemy_alderhaven";
pub const POTION_COOLDOWN: u64 = 60;

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Progress {
    #[serde(default)]
    pub proficiency: Skill,
    #[serde(default, skip_serializing_if = "BTreeSet::is_empty")]
    pub recipes: BTreeSet<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub flask: Option<ActiveBrew>,
}

impl Progress {
    pub fn is_untrained(&self) -> bool {
        self.proficiency.skill == 0 && self.flask.is_none() && self.recipes.is_empty()
    }

    pub fn train_gathering(&mut self, band: u16, roll: f64) {
        if self.proficiency.skill >= gathering_requirement(band) {
            self.proficiency
                .try_gain_to(0, (band + 1) * SKILL_BAND, MAX_SKILL, roll);
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Stat {
    Damage,
    Ward,
    Healing,
    Speed,
    Health,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct ActiveBrew {
    pub item: String,
    pub until: u64,
}

impl ActiveBrew {
    pub fn active(&self, now: u64) -> Option<(&'static Recipe, u64)> {
        let left = self.until.saturating_sub(now);
        if left == 0 {
            return None;
        }
        Some((CATALOG.recipe(&self.item)?, left))
    }
}

#[derive(Deserialize)]
pub struct Flower {
    pub item: String,
    pub band: u16,
}

#[derive(Deserialize)]
pub struct Recipe {
    pub item: String,
    pub skill: u16,
    pub level: u32,
    pub flask: bool,
    pub stat: Stat,
    pub amount: u32,
    pub ingredients: Vec<(Vec<String>, u32)>,
    pub formula: Option<String>,
    pub boss: Option<String>,
}

impl Recipe {
    pub fn duration(&self) -> u64 {
        if self.flask { 45 * 60 } else { 15 }
    }

    pub fn modifier(&self, stat: Stat) -> f64 {
        if self.stat == stat {
            f64::from(self.amount) / 100.
        } else {
            0.
        }
    }
}

#[derive(Deserialize)]
pub struct Catalog {
    pub flowers: Vec<Flower>,
    pub recipes: Vec<Recipe>,
}

impl Catalog {
    pub fn recipe(&self, item: &str) -> Option<&Recipe> {
        self.recipes.iter().find(|recipe| recipe.item == item)
    }

    pub fn formula(&self, item: &str) -> Option<&Recipe> {
        self.recipes
            .iter()
            .find(|recipe| recipe.formula.as_deref() == Some(item))
    }
}

#[derive(Deserialize)]
pub struct PatchPool {
    pub flower: usize,
    pub active: usize,
    pub points: Vec<Point>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case")]
pub enum Command {
    Train { npc: String },
    Learn { npc: String, recipe: String },
    Study { formula: String },
    Brew {
        npc: String,
        recipe: String,
        #[serde(default)]
        all: bool,
    },
}

pub static CATALOG: LazyLock<Catalog> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/alchemy.txt")).expect("Alchemy catalog")
});
pub static PATCHES: LazyLock<BTreeMap<usize, Vec<PatchPool>>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/flower-patches.txt")).expect("Alchemy patches")
});
