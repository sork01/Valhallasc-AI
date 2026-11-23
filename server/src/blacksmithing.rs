//! Saved profession state and the shared client/server recipe catalog.
use crate::items::{is_boss, is_elite};
use crate::model::{Map, Point};
use crate::profession::{SKILL_BAND, Skill};
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::sync::LazyLock;

pub const MAX_SKILL: u16 = 300;
pub const WORKSHOP: &str = "blacksmithing_workshop";
pub const TRAINER: &str = "smith";
pub const STARTER_PICK: &str = "smith_pick_1";

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub struct Progress {
    pub proficiency: Skill,
    pub recipes: BTreeSet<String>,
}

impl Progress {
    pub fn is_untrained(&self) -> bool {
        self.proficiency.skill == 0
    }
}

#[derive(Debug, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Command {
    Train { npc: String },
    Learn { npc: String, recipe: String },
    Craft {
        npc: String,
        recipe: String,
        #[serde(default)]
        all: bool,
    },
    Study { plan: String },
}

#[derive(Clone, Copy, Debug, PartialEq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Method {
    Smelt,
    Upgrade,
    Staple,
    Rare,
    Epic,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Recipe {
    pub item: String,
    pub method: Method,
    pub skill: u16,
    pub tier: usize,
    pub cost: u32,
    pub ingredients: Vec<(String, u32)>,
    pub plan: Option<String>,
}

pub fn training_cap(tier: usize) -> u16 {
    (tier as u16 + 1) * SKILL_BAND
}

#[derive(Deserialize)]
pub struct Tier {
    pub ore: String,
    pub zones: Vec<usize>,
}

#[derive(Deserialize)]
pub struct Pick {
    pub item: String,
    pub reaches: usize,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Catalog {
    pub tiers: Vec<Tier>,
    pub picks: Vec<Pick>,
    pub recipes: Vec<Recipe>,
    epic_bosses: Vec<String>,
}

impl Catalog {
    pub fn tier(&self, zone: usize) -> Option<usize> {
        self.tiers
            .iter()
            .position(|tier| tier.zones.contains(&zone))
    }

    pub fn recipe(&self, id: &str) -> Option<&Recipe> {
        self.recipes.iter().find(|recipe| recipe.item == id)
    }

    pub fn plan(&self, id: &str) -> Option<&Recipe> {
        self.recipes
            .iter()
            .find(|recipe| recipe.plan.as_deref() == Some(id))
    }

    /// Rare plans use the outdoor region's ore tier and its normal level range.
    /// Epic plans share one pool on the selected level-99 final bosses.
    pub fn drop_plan(
        &self,
        zone: usize,
        map: &Map,
        kind: &str,
        level: u32,
        rolls: (f64, f64),
    ) -> Option<&str> {
        let (chance, choice) = rolls;
        if map.final_boss == kind && level == 99 && self.epic_bosses.iter().any(|boss| boss == kind)
        {
            if chance >= 0.20 {
                return None;
            }
            let pool: Vec<_> = self
                .recipes
                .iter()
                .filter(|r| r.method == Method::Epic)
                .collect();
            return pool
                .get((choice * pool.len() as f64) as usize)?
                .plan
                .as_deref();
        }
        let tier = self.tier(zone)?;
        let [min, max] = map.levels.unwrap_or([1, 5]);
        if level < min.saturating_sub(2)
            || level > max + 2
            || chance
                >= if is_elite(kind) || is_boss(kind) {
                    0.045
                } else {
                    0.015
                }
        {
            return None;
        }
        self.recipes
            .iter()
            .find(|r| r.method == Method::Rare && r.tier == tier)?
            .plan
            .as_deref()
    }
}

pub static CATALOG: LazyLock<Catalog> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/blacksmithing.txt"))
        .expect("Blacksmithing catalog")
});

pub static CANDIDATES: LazyLock<std::collections::BTreeMap<usize, Vec<Point>>> =
    LazyLock::new(|| {
        serde_json::from_str(include_str!("../../world/mining-veins.txt"))
            .expect("Mining vein positions")
    });
