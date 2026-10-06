use crate::model::{Character, Class, GM_NAME};
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
    /// Character level needed to wear the piece (1 or a five-level step through 50). Wearing it earlier is refused, and
    /// a piece worn above the character's level (a level lost to a death) adds nothing until the level is back.
    #[serde(default = "first_level", rename = "requiredLevel")]
    pub required_level: u32,
    pub sell: u32,
    #[serde(default)]
    pub attack: f64,
    #[serde(default)]
    pub defense: f64,
    pub class: Option<Class>,
    pub variant: Option<String>,
    /// The drawn piece this one is a recolouring of (its `variant` names the recolouring itself). Unset for the
    /// original pieces. The client paints the base art with the `tint` the catalog carries.
    pub art: Option<String>,
    #[serde(default)]
    pub starter: bool,
    #[serde(default, rename = "bagSlots")]
    pub bag_slots: usize,
    /// Food and potions: hit points restored in total.
    #[serde(default)]
    pub heal: f64,
    /// Mana restored, alongside optional health recovery.
    #[serde(default)]
    pub mana: f64,
    /// Food: seconds over which `heal` arrives. Potions heal at once.
    #[serde(default)]
    pub duration: f64,
    /// Potions: seconds before any potion can be drunk again.
    #[serde(default)]
    pub cooldown: f64,
    /// Potions and food come in tiers, one every ten levels (scripts/consumable_tiers.py); this names the line they
    /// belong to (`health_potion`, `mana_potion`, `traveler_stew`). A tiered vendor offer sells the best tier the buyer's
    /// level allows, at its `price`.
    #[serde(default)]
    pub family: Option<String>,
    /// Gear that only one dungeon's bosses hand out. It is never part of the ordinary drop pool.
    #[serde(default)]
    pub source: Option<String>,
    #[serde(default)]
    pub price: u32,
}
fn first_level() -> u32 {
    1
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
static INDEX: LazyLock<std::collections::HashMap<&'static str, &'static Item>> =
    LazyLock::new(|| ITEMS.iter().map(|i| (i.id.as_str(), i)).collect());
pub fn item(id: &str) -> Option<&'static Item> {
    INDEX.get(id).copied()
}
/// Kinds that are worn (everything in the catalog that is not a material, bag, food or potion).
pub const GEAR_KINDS: [&str; 8] = [
    "armor",
    "weapon",
    "headgear",
    "shoulders",
    "gloves",
    "pants",
    "necklace",
    "accessory",
];
pub fn is_gear(i: &Item) -> bool {
    GEAR_KINDS.contains(&i.kind.as_str())
}
/// The highest required level an enemy of this level can drop: its own level rounded up to the next gear step, plus
/// one more step, so an early enemy can reward gear for the next zone.
pub fn max_drop_level(enemy_level: u32) -> u32 {
    enemy_level.div_ceil(5) * 5 + 5
}
/// The best tier of a potion or food line that a character of `level` may use.
pub fn best_tier(family: &str, level: u32) -> Option<&'static Item> {
    ITEMS
        .iter()
        .filter(|i| i.family.as_deref() == Some(family) && i.required_level <= level)
        .max_by_key(|i| i.required_level)
}
pub fn equipment(class: Class, kind: &str, variant: &str) -> Option<&'static Item> {
    ITEMS
        .iter()
        .find(|i| i.class == Some(class) && i.kind == kind && i.variant.as_deref() == Some(variant))
}
pub fn material(kind: &str) -> &'static str {
    if let Some(e) = crate::cathedral::enemy(kind) {
        return &e.material;
    }
    match kind {
        "blue" => "blue_gel",
        "pink" => "pink_gel",
        "yellow" => "golden_gel",
        "beetle" => "ironhide_shell",
        "big" => "royal_jelly",
        "wisp" => "ember_core",
        "spider" => "magma_fang",
        "wraith" => "ash_veil",
        "golem" | "cinderlord" => "basalt_heart",
        "crab" => "rime_shell",
        "wolf" => "frost_pelt",
        "yeti" => "yeti_horn",
        "wyrm" => "wyrm_scale",
        "toad" => "toad_gland",
        "croc" => "croc_hide",
        "knight" => "drowned_gauntlet",
        "hydra" => "hydra_fang",
        "gloomroot" => "gloomroot_heartwood",
        "thrall" => "crypt_bone",
        "archer" => "bone_fletching",
        "acolyte" => "hollow_ash",
        "gatewarden" => "wardens_signet",
        "choir" => "hollow_chime",
        "colossus" => "runed_keystone",
        "hollowking" => "crown_shard",
        "boar" => "rotfang_tusk",
        "crow" => "gallows_feather",
        "troll" => "mosshide_scrap",
        "weaver" => "fate_thread",
        "ram" => "stormram_horn",
        "oakhorn" => "oakhorn_crown",
        "hrungnir" => "stormheart_shard",
        "galehound" => "gale_fang",
        "prismgolem" => "prism_shard",
        "skyray" => "stormray_wing",
        "einherjar" => "rune_token",
        "thunderroc" => "thunderroc_quill",
        "draugr" => "drowned_coin",
        "angler" => "angler_lure",
        "moray" => "moray_tooth",
        "siren" => "siren_pearl",
        "shellback" => "shellback_plate",
        "kraken" => "kraken_beak",
        "hvitserk" => "captains_signet",
        "ghostmaw" => "ghostmaw_tooth",
        _ => "slime_gel",
    }
}
/// The golden gear of the administrator character. Its rarity "gm" is not in `RARITIES`, so no enemy ever rolls it.
pub const GM_RARITY: &str = "gm";
pub const GM_GEAR: [&str; 3] = [
    "warrior_armor_gm",
    "warrior_headgear_gm",
    "warrior_weapon_gm",
];
/// Rarity tiers, lowest first. The catalog colours them gray, green, blue, purple and orange.
pub const RARITIES: [&str; 5] = ["common", "uncommon", "rare", "epic", "legendary"];
/// Elites (special enemies) roll every tier this many times as often, and are the only source of legendary gear.
pub const ELITE_DROP_MULTIPLIER: f64 = 5.;
/// Chance per ordinary kill that one piece of this tier drops. Gray gear drops too (it is mostly for selling);
/// the starter pieces never do.
pub fn base_drop_chance(rarity: &str) -> f64 {
    match rarity {
        "common" => 0.02,
        "uncommon" => 0.015,
        "rare" => 0.0003,
        "epic" => 0.0001,
        "legendary" => 0.0001,
        _ => 0.,
    }
}
/// Colour of the drop marker on the ground; the client CSS uses the same five.
pub fn rarity_color(rarity: &str) -> &'static str {
    match rarity {
        "uncommon" => "#4ad66d",
        "rare" => "#4aa3ff",
        "epic" => "#b45cff",
        "legendary" => "#ff9a2e",
        "gm" => "#ffd24a",
        _ => "#c4c4c4",
    }
}
pub fn is_elite(kind: &str) -> bool {
    if crate::cathedral::enemy(kind).is_some() {
        return true;
    }
    matches!(
        kind,
        "big"
            | "cinderlord"
            | "gloomroot"
            | "oakhorn"
            | "hrungnir"
            | "kraken"
            | "hvitserk"
            | "ghostmaw"
    ) || is_vault_enemy(kind)
}
/// Everything that lives in the Undervault: the trash packs and the four bosses are all elites.
pub fn is_vault_enemy(kind: &str) -> bool {
    if crate::cathedral::enemy(kind).is_some() {
        return false;
    }
    matches!(kind, "thrall" | "archer" | "acolyte") || is_boss(kind)
}
/// The four bosses of the Undervault (the dungeon under Skaldholm). Each drops guaranteed blue gear.
pub fn is_boss(kind: &str) -> bool {
    if let Some(e) = crate::cathedral::enemy(kind) {
        return e.boss;
    }
    matches!(kind, "gatewarden" | "choir" | "colossus" | "hollowking")
}
/// The slot pools a boss drops from: one shared wing-level blue piece per pool, chosen across all classes.
pub fn boss_slots(kind: &str) -> &'static [&'static [&'static str]] {
    if let Some(e) = crate::cathedral::enemy(kind) {
        if !e.boss {
            return &[];
        }
        return if matches!(kind, "choirmother" | "coralregent" | "hierophant") {
            &[
                &["armor"],
                &[
                    "weapon",
                    "headgear",
                    "shoulders",
                    "gloves",
                    "pants",
                    "necklace",
                    "accessory",
                ],
            ]
        } else {
            match kind {
                "bellkeeper" | "pearlwidow" | "chainmarshal" => &[&["headgear", "shoulders"]],
                "mournsister" | "glasscantor" | "starseraph" => &[&["gloves", "pants", "necklace"]],
                "rootabbot" | "relicwarden" | "tidejudicator" => &[&["weapon", "accessory"]],
                _ => &[],
            }
        };
    }
    match kind {
        "gatewarden" => &[&["headgear", "shoulders"]],
        "choir" => &[&["gloves", "pants"]],
        "colossus" => &[&["weapon", "accessory"]],
        "hollowking" => &[
            &["armor"],
            &[
                "weapon",
                "headgear",
                "shoulders",
                "gloves",
                "pants",
                "accessory",
            ],
        ],
        _ => &[],
    }
}
/// A piece of Undervault gear (a 15% stronger recolour of the level-20 blue set) of one of `slots`, across all classes.
/// `choice` is uniform in [0, 1).
pub fn boss_piece(slots: &[&str], choice: f64) -> Option<&'static Item> {
    let pool: Vec<_> = ITEMS
        .iter()
        .filter(|i| {
            i.rarity == "rare"
                && i.required_level == 20
                && i.source.as_deref() == Some("undervault")
                && slots.contains(&i.kind.as_str())
        })
        .collect();
    pool.get((choice * pool.len() as f64) as usize).copied()
}
/// Cathedral bosses guarantee their own wing's exclusive blue set at its exact required level.
pub fn boss_piece_for(kind: &str, slots: &[&str], choice: f64) -> Option<&'static Item> {
    let Some(e) = crate::cathedral::enemy(kind) else {
        return boss_piece(slots, choice);
    };
    let source = e.loot_source.as_deref()?;
    let pool: Vec<_> = ITEMS
        .iter()
        .filter(|i| {
            i.rarity == "rare"
                && i.required_level == e.level
                && i.source.as_deref() == Some(source)
                && slots.contains(&i.kind.as_str())
        })
        .collect();
    pool.get((choice * pool.len() as f64) as usize).copied()
}
/// Which tier, if any, a kill drops. `roll` is uniform in [0, 1): the bands start with the rarest tier, so one roll
/// gives at most one piece. Legendary exists only for elites.
pub fn roll_rarity(kind: &str, roll: f64) -> Option<&'static str> {
    let elite = is_elite(kind);
    let multiplier = if elite { ELITE_DROP_MULTIPLIER } else { 1. };
    let mut edge = 0.;
    for rarity in RARITIES.iter().rev() {
        if *rarity == "legendary" && !elite {
            continue;
        }
        edge += base_drop_chance(rarity) * multiplier;
        if roll < edge {
            return Some(rarity);
        }
    }
    None
}
/// A random piece of gear of the rolled tier that an enemy of this level can drop (see `max_drop_level`); starter
/// pieces never drop, and an empty tier drops nothing.
pub fn roll_equipment(kind: &str, level: u32, chance: f64, choice: f64) -> Option<&'static Item> {
    let rarity = roll_rarity(kind, chance)?;
    let limit = max_drop_level(level);
    let pool: Vec<_> = ITEMS
        .iter()
        .filter(|i| {
            i.rarity == rarity
                && is_gear(i)
                && !i.starter
                && i.source.is_none()
                && i.required_level <= limit
        })
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
                matches!(i.kind.as_str(), "armor" | "weapon")
                    && i.variant.as_deref() == Some(if i.kind == "armor" { armor } else { weapon }),
            )
    }
    /// Whether `i` beats what this character wears in its slot (attack plus defense; an empty slot loses to any
    /// stat, and for rings the weaker of the two counts). Mercenaries use it to decide whether to need a piece.
    pub fn is_upgrade(&self, i: &Item) -> bool {
        let score = |x: &Item| x.attack + x.defense;
        let worn = |slot: &str| {
            self.equipment
                .get(slot)
                .and_then(|id| item(id))
                .map_or(0., score)
        };
        let current = match i.kind.as_str() {
            "armor" | "weapon" => {
                let (armor, weapon) = self.gear();
                let variant = if i.kind == "armor" { armor } else { weapon };
                equipment(self.look.class, &i.kind, variant).map_or(0., score)
            }
            "accessory" => worn("accessory1").min(worn("accessory2")),
            slot => worn(slot),
        };
        score(i) > current
    }
    /// Every worn piece: the extra slots plus the class armor and weapon.
    fn worn_items(&self) -> Vec<&'static Item> {
        let (armor, weapon) = self.gear();
        let class = self.look.class;
        self.equipment
            .values()
            .filter_map(|id| item(id))
            .chain(equipment(class, "armor", armor))
            .chain(equipment(class, "weapon", weapon))
            .collect()
    }
    /// Refuses a change that puts on a piece above this character's level. Pieces already worn in `before` are not
    /// asked again, so an old save keeps what it wore and an unrelated swap is never blocked by it.
    pub fn check_required_levels(&self, before: &Character) -> Result<(), &'static str> {
        let already: Vec<_> = before.worn_items().iter().map(|i| i.id.as_str()).collect();
        if self
            .worn_items()
            .iter()
            .any(|i| i.required_level > self.level && !already.contains(&i.id.as_str()))
        {
            return Err("You are not a high enough level to wear that.");
        }
        Ok(())
    }
    pub fn gear(&self) -> (&str, &str) {
        match self.look.class {
            Class::Warrior => (&self.look.warrior_armor, &self.look.warrior_weapon),
            Class::Mage => (&self.look.mage_armor, &self.look.mage_weapon),
            Class::Assassin => (&self.look.assassin_armor, &self.look.assassin_weapon),
            Class::Priest => (&self.look.priest_armor, &self.look.priest_weapon),
            Class::Hunter => (&self.look.hunter_armor, &self.look.hunter_weapon),
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
                        || (matches!(i.kind.as_str(), "armor" | "weapon")
                            && i.variant.as_deref()
                                == Some(if i.kind == "armor" { armor } else { weapon })))
            })
            .map(|i| i.id.clone())
            .collect();
        for id in ids {
            if self.quantity(&id) == 0 {
                self.add_item(&id, 1);
            }
        }
    }
    /// Turns a new character into the administrator character: a male Warrior named [GM]Sork wearing the golden robe,
    /// top hat, sword and shield. Called by the store while the character is created, never for a loaded save.
    pub fn become_gm(&mut self) {
        self.gm = true;
        self.look.name = GM_NAME.into();
        self.look.class = Class::Warrior;
        self.look.gender = crate::model::Gender::Male;
        self.hp = self.max_hp();
        for id in GM_GEAR {
            if self.quantity(id) == 0 {
                self.add_item(id, 1);
            }
        }
        let _ = self.look.equip("gm", "gm");
        self.equipment
            .insert("headgear".into(), "warrior_headgear_gm".into());
        self.sync_look();
    }
    /// Gives a character the starter pieces of their class that they do not own yet (new catalog entries reach
    /// existing saves this way). Starter gear cannot be sold, so a missing one was never granted. Pieces that would
    /// overfill the bags wait for the next load.
    pub fn grant_missing_starters(&mut self) {
        let class = self.look.class;
        let ids: Vec<_> = ITEMS
            .iter()
            .filter(|i| i.starter && i.class == Some(class))
            .map(|i| i.id.clone())
            .collect();
        for id in ids {
            if self.quantity(&id) == 0 && self.bag_used() < self.bag_capacity() {
                self.add_item(&id, 1);
            }
        }
    }
    /// Makes the look's worn-piece layers match the headgear, shoulders, gloves, pants, necklace and accessory slots. A
    /// piece of the character's own class shows its class art; a class-independent piece (class null in items.txt) shows
    /// the shared art named by its variant. Anything else worn there only adds stats.
    pub fn sync_look(&mut self) {
        let worn = |slot: &str| {
            self.equipment
                .get(slot)
                .and_then(|id| item(id))
                .filter(|i| i.class.is_none_or(|class| class == self.look.class))
                .and_then(|i| i.variant.clone())
                .unwrap_or_else(|| "none".into())
        };
        let accessory = ["accessory1", "accessory2"]
            .iter()
            .map(|slot| worn(slot))
            .find(|variant| variant != "none")
            .unwrap_or_else(|| "none".into());
        let (head, shoulders, gloves) = (worn("headgear"), worn("shoulders"), worn("gloves"));
        let (pants, necklace) = (worn("pants"), worn("necklace"));
        self.look.head = head;
        self.look.shoulders = shoulders;
        self.look.gloves = gloves;
        self.look.pants = pants;
        self.look.necklace = necklace;
        self.look.accessory = accessory;
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
        next.check_required_levels(self)?;
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
        next.sync_look();
        next.check_required_levels(self)?;
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
                * if matches!(self.look.class, Class::Assassin | Class::Hunter) {
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
            if let Some(i) = item(id).filter(|i| i.required_level <= self.level) {
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
        if i.rarity == GM_RARITY {
            return Err("Game master gear cannot be sold.");
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
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
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
    // One roll value that lands inside a tier's band, found by walking the same bands roll_rarity uses.
    fn roll_for(kind: &str, rarity: &str) -> f64 {
        let mut x = 0.;
        while x < 1. {
            if roll_rarity(kind, x) == Some(rarity) {
                return x;
            }
            x += 0.000001;
        }
        panic!("{kind} never rolls {rarity}");
    }
    #[test]
    fn each_kind_has_its_own_material() {
        for (kind, id, sell) in [
            ("wisp", "ember_core", 28),
            ("spider", "magma_fang", 36),
            ("wraith", "ash_veil", 48),
            ("golem", "basalt_heart", 70),
            ("crab", "rime_shell", 80),
            ("wolf", "frost_pelt", 95),
            ("yeti", "yeti_horn", 115),
            ("wyrm", "wyrm_scale", 140),
            ("toad", "toad_gland", 150),
            ("croc", "croc_hide", 170),
            ("knight", "drowned_gauntlet", 195),
            ("hydra", "hydra_fang", 230),
            ("gloomroot", "gloomroot_heartwood", 420),
            ("thrall", "crypt_bone", 90),
            ("archer", "bone_fletching", 95),
            ("acolyte", "hollow_ash", 105),
            ("gatewarden", "wardens_signet", 600),
            ("choir", "hollow_chime", 700),
            ("colossus", "runed_keystone", 800),
            ("hollowking", "crown_shard", 1200),
        ] {
            assert_eq!(material(kind), id);
            let i = item(id).expect("the material exists in the catalog");
            assert_eq!((i.kind.as_str(), i.sell), ("material", sell));
        }
    }
    #[test]
    fn game_master_gear_never_drops_and_the_gm_rarity_cannot_be_rolled() {
        assert_eq!(GM_GEAR.len(), 3);
        for id in GM_GEAR {
            let i = item(id).expect("in the catalog");
            assert_eq!(
                (i.rarity.as_str(), i.sell, i.starter),
                (GM_RARITY, 0, false),
                "{id}"
            );
        }
        assert_eq!(base_drop_chance(GM_RARITY), 0.);
        for kind in ["green", "big", "cinderlord", "gloomroot", "hydra"] {
            for n in 0..2000 {
                assert_ne!(roll_rarity(kind, n as f64 / 2000.), Some(GM_RARITY));
            }
        }
    }
    #[test]
    fn potions_and_food_have_a_stronger_tier_every_ten_levels() {
        for family in ["health_potion", "mana_potion", "traveler_stew"] {
            let tiers: Vec<_> = ITEMS
                .iter()
                .filter(|i| i.family.as_deref() == Some(family))
                .collect();
            assert_eq!(tiers.len(), 10, "{family}");
            let levels: Vec<u32> = tiers.iter().map(|i| i.required_level).collect();
            assert_eq!(levels, [1, 10, 20, 30, 40, 50, 60, 70, 80, 90], "{family}");
            for pair in tiers.windows(2) {
                let (a, b) = (pair[0], pair[1]);
                assert!(
                    b.heal >= a.heal && b.mana >= a.mana,
                    "{} is no weaker",
                    b.id
                );
                assert!(b.heal + b.mana > a.heal + a.mana, "{} is stronger", b.id);
                assert!(b.price > a.price && b.sell > a.sell, "{} costs more", b.id);
                assert_eq!((a.kind.as_str(), a.cooldown), (b.kind.as_str(), b.cooldown));
            }
            assert_eq!(tiers[0].id, family, "the first tier keeps its old id");
            assert_eq!(tiers[2].rarity, "rare", "{family}: level 20 is a blue tier");
            for i in &tiers {
                assert!(i.price > 0 && (i.heal > 0. || i.mana > 0.), "{}", i.id);
                assert_eq!(i.required_level == 1, i.id == family);
            }
        }
        assert_eq!(best_tier("health_potion", 1).unwrap().id, "health_potion");
        assert_eq!(best_tier("health_potion", 9).unwrap().id, "health_potion");
        assert_eq!(
            best_tier("health_potion", 10).unwrap().id,
            "health_potion_l10"
        );
        assert_eq!(best_tier("mana_potion", 25).unwrap().id, "mana_potion_l20");
        assert_eq!(
            best_tier("traveler_stew", 100).unwrap().id,
            "traveler_stew_l90"
        );
        assert!(best_tier("not_a_family", 20).is_none());
        // A mana-using mercenary of level 20 carries the level-20 potions of both lines.
        let merc = Character::mercenary(Class::Priest, 20, "Merc Priest");
        assert_eq!(merc.quantity("health_potion_l20"), 3);
        assert_eq!(merc.quantity("mana_potion_l20"), 3);
        let warrior = Character::mercenary(Class::Warrior, 20, "Merc Warrior");
        assert_eq!(
            (
                warrior.quantity("health_potion_l20"),
                warrior.quantity("mana_potion_l20")
            ),
            (3, 0)
        );
    }
    #[test]
    fn every_item_has_a_known_rarity_and_starters_are_common() {
        for i in ITEMS.iter() {
            assert!(
                RARITIES.contains(&i.rarity.as_str()) || i.rarity == GM_RARITY,
                "{} has rarity {}",
                i.id,
                i.rarity
            );
            if i.starter || i.kind == "material" {
                assert_eq!(i.rarity, "common", "{}", i.id);
            }
        }
    }
    #[test]
    fn rarer_tiers_drop_less_often_and_only_elites_drop_legendary() {
        let rates: Vec<_> = ["uncommon", "rare", "epic"]
            .iter()
            .map(|r| base_drop_chance(r))
            .collect();
        assert!(rates[0] >= 0.01 && rates[0] <= 0.02, "green is 1-2%");
        assert!(rates[0] > rates[1] && rates[1] > rates[2]);
        assert!(
            base_drop_chance("common") > rates[0],
            "gray drops most often, and is mostly for selling"
        );
        // The user's WoW-style ranges for ordinary mobs.
        assert!((0.0001..=0.0005).contains(&rates[1]), "blue is 0.01-0.05%");
        assert!(
            (0.00001..=0.0002).contains(&rates[2]),
            "purple is 0.001-0.02%"
        );
        for kind in ["green", "blue", "beetle", "wisp", "golem"] {
            assert!(!is_elite(kind));
            assert_ne!(roll_rarity(kind, 0.), Some("legendary"));
            // Sweep the whole range: an ordinary mob never produces orange.
            for n in 0..2000 {
                assert_ne!(
                    roll_rarity(kind, n as f64 / 2000. * 0.05),
                    Some("legendary")
                );
            }
        }
        assert!(is_elite("big"));
        assert_eq!(roll_rarity("big", 0.), Some("legendary"));
        assert_eq!(roll_rarity("green", 0.9), None);
        assert_eq!(roll_rarity("big", 0.9), None);
    }
    #[test]
    fn elites_roll_every_tier_five_times_as_often() {
        // The width of a tier's band is its chance. Elites: band = 5x the ordinary width.
        let width = |kind: &str, rarity: &str| {
            let step = 0.000001;
            (0..100_000)
                .filter(|n| roll_rarity(kind, *n as f64 * step) == Some(rarity))
                .count() as f64
                * step
        };
        for rarity in ["uncommon", "rare", "epic"] {
            let ordinary = width("green", rarity);
            let elite = width("big", rarity);
            assert!(
                (elite / ordinary - ELITE_DROP_MULTIPLIER).abs() < 0.05,
                "{rarity}: ordinary {ordinary}, elite {elite}"
            );
        }
        assert_eq!(ELITE_DROP_MULTIPLIER, 5.);
    }
    #[test]
    fn a_rolled_tier_drops_gear_of_exactly_that_tier() {
        for (kind, rarity) in [
            ("green", "common"),
            ("green", "uncommon"),
            ("green", "rare"),
            ("green", "epic"),
            ("big", "uncommon"),
            ("big", "rare"),
            ("big", "epic"),
        ] {
            let roll = roll_for(kind, rarity);
            let pool = ITEMS
                .iter()
                .filter(|i| i.rarity == rarity && is_gear(i) && !i.starter)
                .count();
            assert!(pool > 0, "{rarity} has gear");
            // Level 12 enemies can drop every required level (the limit is 20).
            for n in 0..pool {
                let i = roll_equipment(kind, 12, roll, (n as f64 + 0.5) / pool as f64).unwrap();
                assert_eq!(i.rarity, rarity);
                assert!(!i.starter);
            }
        }
        // An empty tier drops nothing (no legendary gear exists yet, or the roll would panic on an empty pool).
        let roll = roll_for("big", "legendary");
        let pool = ITEMS
            .iter()
            .filter(|i| i.rarity == "legendary" && is_gear(i))
            .count();
        assert_eq!(roll_equipment("big", 6, roll, 0.).is_some(), pool > 0);
    }
    #[test]
    fn enemies_drop_gear_up_to_one_step_above_their_zone() {
        assert_eq!(
            [1, 5, 6, 10, 11, 12].map(max_drop_level),
            [10, 10, 15, 15, 20, 20]
        );
        for (level, limit) in [(2, 10), (6, 15), (12, 20)] {
            let roll = roll_for("green", "uncommon");
            let pool = ITEMS
                .iter()
                .filter(|i| {
                    i.rarity == "uncommon" && is_gear(i) && !i.starter && i.required_level <= limit
                })
                .count();
            let mut top = 0;
            for n in 0..pool {
                let i =
                    roll_equipment("green", level, roll, (n as f64 + 0.5) / pool as f64).unwrap();
                assert!(
                    i.required_level <= limit,
                    "{} for a level {level} enemy",
                    i.id
                );
                top = top.max(i.required_level);
            }
            assert_eq!(top, limit, "the top step is reachable");
        }
    }
    #[test]
    fn every_level_has_gray_green_blue_and_purple_every_other_step() {
        let has = |class: Option<Class>, kind: &str, level: u32, rarity: &str| {
            ITEMS.iter().any(|i| {
                i.class == class
                    && i.kind == kind
                    && i.required_level == level
                    && i.rarity == rarity
                    && i.source.is_none()
            })
        };
        let classes = [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ];
        for level in std::iter::once(1).chain((5..=50).step_by(5)) {
            for rarity in ["common", "uncommon", "rare", "epic"] {
                let purple_level = level % 10 == 0;
                for class in classes {
                    for kind in ["armor", "headgear", "shoulders", "gloves", "weapon"] {
                        assert_eq!(
                            has(Some(class), kind, level, rarity),
                            rarity != "epic" || purple_level,
                            "{class:?} {kind} level {level} {rarity}"
                        );
                    }
                }
                for kind in ["pants", "necklace", "accessory"] {
                    assert_eq!(
                        has(None, kind, level, rarity),
                        rarity != "epic" || purple_level,
                        "shared {kind} level {level} {rarity}"
                    );
                }
            }
        }
    }
    #[test]
    fn recoloured_pieces_name_a_real_base_piece_and_every_variant_is_unique() {
        let mut seen = std::collections::BTreeSet::new();
        for i in ITEMS.iter().filter(|i| is_gear(i)) {
            let variant = i.variant.as_deref().unwrap();
            assert!(
                seen.insert((i.kind.clone(), variant)),
                "{} repeats a variant",
                i.id
            );
            if let Some(art) = &i.art {
                let base = ITEMS
                    .iter()
                    .find(|b| {
                        b.kind == i.kind && b.class == i.class && b.variant.as_deref() == Some(art)
                    })
                    .unwrap_or_else(|| panic!("{} recolours {art}, which does not exist", i.id));
                assert!(base.art.is_none(), "{} recolours a recolouring", i.id);
            }
        }
    }
    #[test]
    fn cathedral_sets_cover_every_slot_and_only_their_own_bosses_can_award_them() {
        for (source, level) in [
            ("cathedral_cloister", 40),
            ("cathedral_reliquary", 45),
            ("cathedral_nave", 50),
        ] {
            let pieces: std::collections::BTreeSet<_> = ITEMS
                .iter()
                .filter(|i| i.source.as_deref() == Some(source))
                .map(|i| i.id.as_str())
                .collect();
            assert_eq!(
                pieces.len(),
                28,
                "{source}: five class slots and three shared slots"
            );
            let mut reachable = std::collections::BTreeSet::new();
            for e in crate::cathedral::ENEMIES
                .iter()
                .filter(|e| e.loot_source.as_deref() == Some(source))
            {
                assert!(e.boss);
                assert_eq!(e.level, level);
                for slots in boss_slots(&e.kind) {
                    for n in 0..100 {
                        let i = boss_piece_for(&e.kind, slots, n as f64 / 100.).unwrap();
                        assert_eq!(i.required_level, level);
                        assert_eq!(i.source.as_deref(), Some(source));
                        assert_eq!(i.rarity, "rare");
                        reachable.insert(i.id.as_str());
                        let base_id = i.id.replace(
                            &format!("_l{level}_{}", &source[10..]),
                            &format!("_l{level}_blue"),
                        );
                        let base = item(&base_id).unwrap();
                        assert!(
                            (i.attack - base.attack * 1.15).abs() <= 0.051,
                            "{} attack",
                            i.id
                        );
                        assert!(
                            (i.defense - base.defense * 1.15).abs() <= 0.051,
                            "{} defense",
                            i.id
                        );
                    }
                }
            }
            assert_eq!(reachable, pieces, "{source}: no reward is unreachable");
        }
        for e in crate::cathedral::ENEMIES.iter().filter(|e| !e.boss) {
            assert!(e.loot_source.is_none());
            assert!(boss_piece_for(&e.kind, &["weapon"], 0.).is_none());
        }
        // Walk every ordinary drop-pool cell, including all high-level pieces. Source gear must never leak in.
        for rarity in ["common", "uncommon", "rare", "epic"] {
            let eligible: std::collections::BTreeSet<_> = ITEMS
                .iter()
                .filter(|i| is_gear(i) && i.rarity == rarity && !i.starter && i.source.is_none())
                .map(|i| i.id.as_str())
                .collect();
            let drops: std::collections::BTreeSet<_> = (0..eligible.len())
                .map(|n| {
                    roll_equipment(
                        "hierophant",
                        50,
                        roll_for("hierophant", rarity),
                        (n as f64 + 0.5) / eligible.len() as f64,
                    )
                    .unwrap()
                    .id
                    .as_str()
                })
                .collect();
            assert_eq!(
                drops, eligible,
                "{rarity}: only world gear in ordinary rolls"
            );
            assert!(
                drops
                    .iter()
                    .any(|id| item(id).unwrap().required_level == 50)
            );
        }
    }
    #[test]
    fn level_25_through_50_gear_enforces_requirements_updates_look_stats_and_survives_saves() {
        for i in ITEMS.iter().filter(|i| is_gear(i) && i.required_level > 20) {
            let slot = match i.kind.as_str() {
                "armor" => "chest",
                "weapon" => "hands",
                "accessory" => "accessory1",
                kind => kind,
            };
            let mut c = character();
            c.look.class = i.class.unwrap_or(Class::Warrior);
            c.inventory.clear();
            c.seed_inventory();
            c.add_item(&i.id, 1);
            c.level = i.required_level - 1;
            let before = c.clone();
            assert!(
                c.equip_slots(&slots(&[(slot, &i.id)])).is_err(),
                "{} below level",
                i.id
            );
            assert_eq!(c.stats(), before.stats());
            assert_eq!(c.quantity(&i.id), 1);
            c.level = i.required_level;
            c.equip_slots(&slots(&[(slot, "none")])).unwrap();
            let naked = c.stats();
            c.equip_slots(&slots(&[(slot, &i.id)])).unwrap();
            let equipped = c.stats();
            assert!(
                (equipped.0 - naked.0 - i.attack).abs() < 1e-8,
                "{} attack",
                i.id
            );
            assert!(
                (equipped.1 - naked.1 - i.defense).abs() < 1e-8,
                "{} defense",
                i.id
            );
            assert!(c.look.validate().is_ok(), "{} worn look", i.id);
            let saved: Character =
                serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
            assert_eq!(saved.stats(), equipped);
            assert_eq!(
                serde_json::to_value(&saved.look).unwrap(),
                serde_json::to_value(&c.look).unwrap()
            );
            c.level -= 1;
            let worn = c.clone();
            c.equip_slots(&slots(&[(slot, "none")])).unwrap();
            assert_eq!(
                worn.stats(),
                c.stats(),
                "{} dormant after a level loss",
                i.id
            );
            if let Some(class) = i.class {
                c = character();
                c.level = i.required_level;
                c.look.class = if class == Class::Mage {
                    Class::Warrior
                } else {
                    Class::Mage
                };
                c.inventory.clear();
                c.seed_inventory();
                c.add_item(&i.id, 1);
                assert!(
                    c.equip_slots(&slots(&[(slot, &i.id)])).is_err(),
                    "{} wrong class",
                    i.id
                );
            }
        }
    }
    #[test]
    fn a_recoloured_piece_is_worn_and_shown_but_only_by_its_own_class() {
        let mut c = character();
        c.level = 20;
        c.add_item("warrior_armor_azure_l5_green", 1);
        c.add_item("mage_armor_runic_l5_green", 1);
        c.equip_slots(&slots(&[("chest", "warrior_armor_azure_l5_green")]))
            .unwrap();
        assert_eq!(c.look.warrior_armor, "azure_l5_green");
        assert!(c.look.validate().is_ok());
        assert!(
            c.equip_slots(&slots(&[("chest", "mage_armor_runic_l5_green")]))
                .is_err()
        );
        c.look.mage_armor = "azure_l5_green".into();
        assert!(
            c.look.validate().is_err(),
            "another class's field only takes that class's pieces"
        );
        c.look.mage_armor = "apprentice".into();
        c.look.pants = "wayfarer_l10_blue".into();
        assert!(c.look.validate().is_ok(), "shared pants fit every class");
        c.look.head = "not_a_piece".into();
        assert!(c.look.validate().is_err());
    }
    #[test]
    fn the_gear_pools_cover_every_class_and_slot_between_them() {
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            for kind in ["armor", "weapon", "headgear", "shoulders", "gloves"] {
                assert!(
                    ITEMS
                        .iter()
                        .any(|i| i.rarity != "common" && i.class == Some(class) && i.kind == kind),
                    "{class:?} {kind} has a dropping piece"
                );
            }
        }
    }
    #[test]
    fn ownership_class_and_equipped_copy_are_enforced() {
        let mut c = character();
        c.level = 20;
        assert!(c.equip_owned("azure", "royal").is_err());
        c.add_item("mage_weapon_crystal", 1);
        assert!(c.equip_owned("crimson", "crystal").is_err());
        c.add_item("warrior_weapon_royal", 2);
        c.equip_owned("crimson", "royal").unwrap();
        assert!(c.sell_item("warrior_weapon_royal", 2).is_err());
        assert_eq!(c.sell_item("warrior_weapon_royal", 1).unwrap(), 25);
        assert_eq!(c.quantity("warrior_weapon_royal"), 1);
        assert!(c.sell_item("warrior_weapon_royal", 1).is_err());
        assert_eq!(c.sell_item("mage_weapon_crystal", 1).unwrap(), 25);
        assert_eq!(c.gold, 50);
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
    fn gear_levels_come_in_steps_of_five_and_use_every_step() {
        let mut used = std::collections::BTreeSet::new();
        for i in ITEMS.iter() {
            if matches!(i.kind.as_str(), "material" | "bag" | "food" | "potion") {
                // Potions and food come in a tier every ten levels; everything else non-gear needs none.
                let tier =
                    i.family.is_some() && (i.required_level == 1 || i.required_level % 10 == 0);
                assert!(tier || i.required_level == 1, "{} is not gear", i.id);
                continue;
            }
            assert!(
                i.required_level == 1 || (i.required_level <= 50 && i.required_level % 5 == 0),
                "{} needs level {}",
                i.id,
                i.required_level
            );
            if i.starter {
                assert_eq!(i.required_level, 1, "starter gear is wearable at once");
            }
            used.insert(i.required_level);
        }
        assert_eq!(
            used.into_iter().collect::<Vec<_>>(),
            std::iter::once(1)
                .chain((5..=50).step_by(5))
                .collect::<Vec<_>>()
        );
    }
    #[test]
    fn gear_above_your_level_cannot_be_put_on_and_adds_nothing() {
        let mut c = character();
        c.add_item("warrior_weapon_sword_l15_blue", 1);
        c.add_item("necklace_upgrade", 1);
        let royal = item("warrior_weapon_sword_l15_blue").unwrap();
        assert_eq!((royal.required_level, c.level), (15, 1));
        assert!(c.equip_owned("crimson", "sword_l15_blue").is_err());
        assert!(
            c.equip_slots(&slots(&[("hands", "warrior_weapon_sword_l15_blue")]))
                .is_err()
        );
        assert!(
            c.equip_slots(&slots(&[("necklace", "necklace_upgrade")]))
                .is_err()
        );
        assert_eq!(c.gear().1, "sword", "a refused change wears nothing");
        let base = c.stats();
        c.level = 15;
        let base15 = c.stats();
        c.equip_slots(&slots(&[("hands", "warrior_weapon_sword_l15_blue")]))
            .unwrap();
        assert_eq!(
            c.stats().0,
            base15.0 - 4. + royal.attack,
            "sword out, royal in"
        );
        assert_eq!(
            c.stats().1,
            base15.1 + royal.defense,
            "the secondary stat counts"
        );
        assert!(
            c.equip_slots(&slots(&[("necklace", "necklace_upgrade")]))
                .is_err(),
            "level 20"
        );
        // A level lost to a death switches the piece off without taking it away.
        c.level = 1;
        assert_eq!(c.gear().1, "sword_l15_blue");
        assert_eq!(
            c.stats(),
            (base.0 - 4., base.1),
            "the sword is off and the Royal Sword is dormant"
        );
        // ... and what is already worn never blocks an unrelated change.
        c.add_item("warrior_headgear_crimson", 1);
        c.equip_slots(&slots(&[("headgear", "warrior_headgear_crimson")]))
            .unwrap();
        c.level = 5;
        c.add_item("warrior_headgear_azure", 1);
        c.equip_slots(&slots(&[("headgear", "warrior_headgear_azure")]))
            .unwrap();
        assert_eq!(c.gear().1, "sword_l15_blue");
    }
    // The catalog's budget, as the stat ladder states it: base x level factor x tier. White carries one stat; green
    // adds the other on top of an unchanged base; blue is 17.5% over green, purple 17.5% over blue.
    #[test]
    fn undervault_gear_comes_only_from_the_bosses_never_from_the_ordinary_drop_roll() {
        let vault: Vec<_> = ITEMS
            .iter()
            .filter(|i| i.source.as_deref() == Some("undervault"))
            .collect();
        assert_eq!(
            vault.len(),
            27,
            "every level-20 blue piece the bosses can drop"
        );
        for kind in ["green", "big", "hydra", "gloomroot", "hollowking", "thrall"] {
            for n in 0..4000 {
                let choice = n as f64 / 4000.;
                for tier in [0.00005, 0.0001, 0.0004, 0.002] {
                    if let Some(i) = roll_equipment(kind, 20, tier, choice) {
                        assert!(i.source.is_none(), "{kind} dropped {}", i.id);
                    }
                }
            }
        }
        let mut possible = std::collections::BTreeSet::new();
        for kind in ["gatewarden", "choir", "colossus", "hollowking"] {
            for slots in boss_slots(kind) {
                for n in 0..1000 {
                    let piece = boss_piece(slots, n as f64 / 1000.).expect("a boss piece");
                    assert!(slots.contains(&piece.kind.as_str()));
                    possible.insert(piece.id.as_str());
                }
            }
        }
        assert_eq!(
            possible,
            vault.iter().map(|i| i.id.as_str()).collect(),
            "every class's boss gear can drop"
        );
    }
    #[test]
    fn stats_follow_the_level_and_rarity_ladder() {
        let factor = |level: u32| -> f64 {
            match level {
                1 => 1.,
                5 => 1.6,
                10 => 2.4,
                15 => 3.2,
                level => 0.16 * level as f64 + 0.8,
            }
        };
        let tier = |rarity: &str| -> f64 {
            match rarity {
                "common" => 1.,
                "uncommon" => 1.25,
                "rare" => 1.25 * 1.175,
                "epic" => 1.25 * 1.175 * 1.175,
                _ => 1.25 * 1.175 * 1.175 * 1.175,
            }
        };
        assert!((tier("rare") / tier("uncommon") - 1.175).abs() < 1e-9);
        assert!((tier("epic") / tier("rare") - 1.175).abs() < 1e-9);
        assert!((1.15..=1.2).contains(&(tier("rare") / tier("uncommon"))));
        assert!(
            (1.30..=1.40).contains(&(tier("epic") / tier("uncommon"))),
            "purple vs green"
        );
        // The game master's gear is outside the ladder: it never drops and is not for sale.
        for i in ITEMS
            .iter()
            .filter(|i| (i.attack > 0. || i.defense > 0.) && i.rarity != GM_RARITY)
        {
            let base = match i.kind.as_str() {
                "weapon" => 4.,
                "armor" if matches!(i.class, Some(Class::Mage | Class::Assassin)) => 2.,
                "armor" => 3.,
                "necklace" => 2.,
                "accessory" => 1.5,
                _ => 1.,
            };
            let total = i.attack + i.defense;
            // Instance gear is its wing's blue set recoloured and made 15% stronger.
            let bonus = if i.source.is_some() { 1.15 } else { 1. };
            let expected = base * factor(i.required_level) * tier(&i.rarity) * bonus;
            assert!(
                (total - expected).abs() <= if bonus > 1. { 0.2 } else { 0.1 } + 1e-9,
                "{}: {total} against {expected}",
                i.id
            );
            let (primary, secondary) =
                if matches!(i.kind.as_str(), "weapon" | "necklace" | "accessory") {
                    (i.attack, i.defense)
                } else {
                    (i.defense, i.attack)
                };
            if i.rarity == "common" {
                assert_eq!(
                    secondary, 0.,
                    "{} is white: base armor or damage only",
                    i.id
                );
            } else {
                assert!(
                    secondary > 0.,
                    "{} is green or better: it carries a secondary stat",
                    i.id
                );
                // Green keeps exactly the white base of its level; each tier above scales both stats.
                assert!(
                    (primary
                        - base * factor(i.required_level) * tier(&i.rarity) / tier("uncommon")
                            * bonus)
                        .abs()
                        <= 0.2 + 1e-9,
                    "{} keeps the base of white gear of its level, scaled by its tier",
                    i.id
                );
            }
        }
        // Preserve the original low-level curve; later levels continue that same linear growth.
        assert!(factor(5) / factor(1) > 1.175 && factor(20) / factor(15) > 1.175);
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
        // The character already carries its unworn starter pieces; fill what is left of the 16 cells.
        let room = 16 - c.bag_used();
        // Reserve the gear used below: the catalog's ordering grows when new classes are added.
        c.add_item("warrior_weapon_royal", 1);
        for i in ITEMS
            .iter()
            .filter(|i| {
                i.kind != "bag"
                    && i.id != "warrior_weapon_royal"
                    && !(i.class == Some(Class::Warrior) && i.starter)
            })
            .take(room - 1)
        {
            c.add_item(&i.id, 1);
        }
        assert_eq!(c.bag_used(), 16);
        assert_eq!(c.bag_capacity(), 16);
        assert!(c.can_collect("slime_gel"));
        assert!(!c.can_collect("headgear_upgrade"));
        assert!(c.equip_owned("none", "none").is_err());
        assert_eq!(c.gear(), ("crimson", "sword"));
        c.level = item("warrior_weapon_royal").unwrap().required_level;
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
        c.level = 20;
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
        let (head, ring) = (
            item("headgear_upgrade").unwrap(),
            item("accessory_upgrade").unwrap(),
        );
        let (attack, defense) = c.stats();
        assert!((attack - (22. + 80. + 4. + head.attack + 2. * ring.attack)).abs() < 1e-9);
        assert!((defense - (3. + head.defense + 2. * ring.defense)).abs() < 1e-9);
        assert!(c.sell_item("accessory_upgrade", 2).is_err());
        assert_eq!(c.sell_item("accessory_upgrade", 1).unwrap(), ring.sell);
        assert!(c.sell_item("accessory_upgrade", 1).is_err());
        c.equip_slots(&request(&[("accessory1", "none")])).unwrap();
        c.sell_item("accessory_upgrade", 1).unwrap();
        let close = |got: (f64, f64), want: (f64, f64)| {
            assert!(
                (got.0 - want.0).abs() < 1e-9 && (got.1 - want.1).abs() < 1e-9,
                "{got:?} vs {want:?}"
            );
        };
        close(
            c.stats(),
            (
                106. + head.attack + ring.attack,
                3. + head.defense + ring.defense,
            ),
        );
        c.equip_slots(&request(&[("chest", "none"), ("hands", "none")]))
            .unwrap();
        close(
            c.stats(),
            (
                102. + head.attack + ring.attack,
                head.defense + ring.defense,
            ),
        );
        c.hp = 0.;
        assert!(c.equip_slots(&request(&[("headgear", "none")])).is_err());
    }
    fn slots(pairs: &[(&str, &str)]) -> std::collections::BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect()
    }
    #[test]
    fn class_pieces_in_the_extra_slots_change_the_look_and_other_classes_pieces_are_refused() {
        let mut c = character();
        let worn = |c: &Character| {
            (
                c.look.head.clone(),
                c.look.shoulders.clone(),
                c.look.gloves.clone(),
            )
        };
        assert_eq!(worn(&c), ("none".into(), "none".into(), "none".into()));
        // Starter pieces are issued unworn, so the layers start off.
        for id in [
            "warrior_headgear_crimson",
            "warrior_shoulders_crimson",
            "warrior_gloves_crimson",
        ] {
            assert_eq!(c.quantity(id), 1, "{id}");
        }
        let defense = c.stats().1;
        c.equip_slots(&slots(&[
            ("headgear", "warrior_headgear_crimson"),
            ("shoulders", "warrior_shoulders_crimson"),
            ("gloves", "warrior_gloves_crimson"),
        ]))
        .unwrap();
        assert_eq!(
            worn(&c),
            ("crimson".into(), "crimson".into(), "crimson".into())
        );
        assert!(c.look.validate().is_ok());
        assert!(c.stats().1 > defense, "the pieces add their defense");
        // A class-independent piece shows the shared art named by its variant, whatever the class.
        c.level = 15;
        c.add_item("headgear_upgrade", 1);
        c.equip_slots(&slots(&[("headgear", "headgear_upgrade")]))
            .unwrap();
        assert_eq!(c.look.head, "ironhide");
        assert!(c.look.validate().is_ok());
        c.equip_slots(&slots(&[("headgear", "warrior_headgear_crimson")]))
            .unwrap();
        assert_eq!(c.look.head, "crimson");
        c.equip_slots(&slots(&[("headgear", "none")])).unwrap();
        assert_eq!(c.look.head, "none");
        // Another class's piece cannot be worn, even when owned.
        c.add_item("mage_headgear_runic", 1);
        assert!(
            c.equip_slots(&slots(&[("headgear", "mage_headgear_runic")]))
                .is_err()
        );
        assert_eq!(c.look.head, "none");
        // The look itself only takes the class's own tier names.
        let mut look = c.look.clone();
        look.head = "runic".into();
        assert!(look.validate().is_err());
        look.head = "azure".into();
        assert!(look.validate().is_ok());
        look.class = Class::Priest;
        assert!(
            look.validate().is_err(),
            "the Priest wears pilgrim and dawn pieces, not a Warrior's azure helm"
        );
        look.head = "dawn".into();
        look.shoulders = "none".into();
        look.gloves = "none".into();
        assert!(look.validate().is_ok());
    }
    #[test]
    fn class_independent_pieces_show_on_every_class_and_have_their_own_layers() {
        let mut c = character();
        c.level = 20;
        for id in [
            "headgear_upgrade",
            "shoulders_upgrade",
            "gloves_upgrade",
            "pants_upgrade",
            "necklace_upgrade",
            "accessory_upgrade",
        ] {
            c.add_item(id, 1);
        }
        c.equip_slots(&slots(&[
            ("headgear", "headgear_upgrade"),
            ("shoulders", "shoulders_upgrade"),
            ("gloves", "gloves_upgrade"),
            ("pants", "pants_upgrade"),
            ("necklace", "necklace_upgrade"),
            ("accessory2", "accessory_upgrade"),
        ]))
        .unwrap();
        let worn = |c: &Character| {
            [
                c.look.head.as_str(),
                c.look.shoulders.as_str(),
                c.look.gloves.as_str(),
                c.look.pants.as_str(),
                c.look.necklace.as_str(),
                c.look.accessory.as_str(),
            ]
            .join(" ")
        };
        assert_eq!(
            worn(&c),
            "ironhide ironhide duelist wayfarer moonstone amber"
        );
        assert!(c.look.validate().is_ok());
        // The ring shows from either accessory slot, and unequipping clears each layer.
        c.equip_slots(&slots(&[
            ("accessory2", "none"),
            ("accessory1", "accessory_upgrade"),
        ]))
        .unwrap();
        assert_eq!(c.look.accessory, "amber");
        c.equip_slots(&slots(&[
            ("accessory1", "none"),
            ("pants", "none"),
            ("necklace", "none"),
        ]))
        .unwrap();
        assert_eq!(worn(&c), "ironhide ironhide duelist none none none");
        // The same pieces validate on every class; unknown names do not.
        for class in [Class::Mage, Class::Assassin, Class::Priest, Class::Hunter] {
            let mut look = c.look.clone();
            look.class = class;
            assert!(look.validate().is_ok(), "{class:?}");
        }
        let mut look = c.look.clone();
        look.pants = "ironhide".into();
        assert!(look.validate().is_err());
        look.pants = "none".into();
        look.necklace = "amber".into();
        assert!(look.validate().is_err());
    }
    #[test]
    fn a_new_characters_draft_look_carries_nothing_worn() {
        // The creation form reuses the previous character's look, so a Hunter's scout hood would otherwise get a new
        // Mage refused with "Invalid equipment".
        let mut look = character().look;
        look.class = Class::Mage;
        look.head = "scout".into();
        look.pants = "wayfarer".into();
        assert!(look.validate().is_err());
        look.clear_worn();
        assert!(look.validate().is_ok());
        assert_eq!((look.head.as_str(), look.pants.as_str()), ("none", "none"));
    }
    #[test]
    fn priest_starts_with_pilgrim_pieces_and_wears_them() {
        let mut p = character();
        p.look.class = Class::Priest;
        p.inventory.clear();
        p.seed_inventory();
        for id in [
            "priest_armor_pilgrim",
            "priest_weapon_mace",
            "priest_headgear_pilgrim",
            "priest_shoulders_pilgrim",
            "priest_gloves_pilgrim",
        ] {
            assert_eq!(p.quantity(id), 1, "{id}");
        }
        assert_eq!(p.bag_used(), 3);
        p.equip_slots(&slots(&[
            ("headgear", "priest_headgear_pilgrim"),
            ("shoulders", "priest_shoulders_pilgrim"),
            ("gloves", "priest_gloves_pilgrim"),
        ]))
        .unwrap();
        assert_eq!(
            (
                p.look.head.as_str(),
                p.look.shoulders.as_str(),
                p.look.gloves.as_str()
            ),
            ("pilgrim", "pilgrim", "pilgrim")
        );
        assert!(p.look.validate().is_ok());
    }
    #[test]
    fn hunter_starts_in_scout_gear_and_existing_saves_receive_new_starter_pieces() {
        let mut h = character();
        h.look.class = Class::Hunter;
        h.inventory.clear();
        h.seed_inventory();
        assert_eq!(h.gear(), ("scout", "shortbow"));
        for id in [
            "hunter_armor_scout",
            "hunter_weapon_shortbow",
            "hunter_headgear_scout",
            "hunter_shoulders_scout",
            "hunter_gloves_scout",
        ] {
            assert_eq!(h.quantity(id), 1, "{id}");
        }
        // Worn armor and weapon are not bag cells; the three pieces are.
        assert_eq!(h.bag_used(), 3);
        assert!(h.look.class.ranged());
        // An older save without the new pieces gets them on load, one each.
        h.inventory
            .retain(|s| !s.item.contains("hunter_headgear") && !s.item.contains("hunter_gloves"));
        h.grant_missing_starters();
        h.grant_missing_starters();
        assert_eq!(h.quantity("hunter_headgear_scout"), 1);
        assert_eq!(h.quantity("hunter_gloves_scout"), 1);
        h.equip_slots(&slots(&[
            ("headgear", "hunter_headgear_scout"),
            ("gloves", "hunter_gloves_scout"),
        ]))
        .unwrap();
        assert_eq!(
            (h.look.head.as_str(), h.look.gloves.as_str()),
            ("scout", "scout")
        );
    }
}
