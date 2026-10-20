use crate::model::{Attributes, Character, Class, GM_NAME};
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;

mod gear_services;
pub use gear_services::GearInstance;
mod orange;
#[cfg(test)]
pub use orange::roll_orange;
pub use orange::roll_orange_boosted;

pub const EXTRA_SLOTS: [&str; 7] = [
    "headgear",
    "shoulders",
    "pants",
    "gloves",
    "necklace",
    "accessory1",
    "accessory2",
];

// Green-gear, even-stat damage calibration from the private kill-time harness. Entries are
// warrior, mage, assassin, priest, hunter. Interpolation avoids a jump when a character levels.
// This is part of authoritative attack power, so skills, basic attacks and the displayed stat
// all use the same value.
const CLASS_ATTACK_CURVE: &[(u32, [f64; 5])] = &[
    (5, [0.98, 1.09, 0.69, 1.41, 0.95]),
    (10, [1.15, 1.15, 0.85, 1.26, 0.93]),
    (15, [1.13, 0.80, 1.90, 1.00, 0.94]),
    (20, [2.27, 0.85, 2.52, 1.04, 1.04]),
    (25, [2.19, 0.98, 2.13, 0.72, 0.92]),
    (30, [2.31, 0.83, 2.41, 0.85, 0.89]),
    (35, [2.22, 1.00, 2.52, 0.69, 0.83]),
    (40, [1.484, 1.620, 1.259, 1.374, 1.299]),
    (45, [1.348, 1.502, 1.193, 1.182, 1.191]),
    (50, [1.368, 1.421, 1.202, 1.160, 1.202]),
    (55, [1.536, 1.507, 1.312, 1.184, 1.334]),
    (60, [1.682, 1.516, 1.446, 1.219, 1.436]),
    (65, [1.534, 1.356, 1.395, 1.140, 1.353]),
    (70, [1.625, 1.244, 1.526, 1.231, 1.421]),
    (75, [1.690, 1.252, 1.576, 1.215, 1.484]),
    (80, [1.597, 1.181, 1.577, 1.197, 1.542]),
    (85, [1.537, 1.088, 1.592, 1.141, 1.483]),
    (90, [1.462, 0.985, 1.573, 1.117, 1.433]),
    (95, [1.480, 0.940, 1.551, 1.068, 1.386]),
    (99, [1.416, 0.859, 1.449, 1.031, 1.360]),
];

fn class_attack_scale(class: Class, level: u32) -> f64 {
    let index = match class {
        Class::Warrior => 0,
        Class::Mage => 1,
        Class::Assassin => 2,
        Class::Priest => 3,
        Class::Hunter => 4,
    };
    let upper = CLASS_ATTACK_CURVE
        .partition_point(|(at, _)| *at < level)
        .min(CLASS_ATTACK_CURVE.len() - 1);
    if upper == 0 {
        return 1. + (CLASS_ATTACK_CURVE[0].1[index] - 1.) * (level.saturating_sub(1) as f64 / 4.);
    }
    let (lo_level, lo) = CLASS_ATTACK_CURVE[upper - 1];
    let (hi_level, hi) = CLASS_ATTACK_CURVE[upper];
    let fraction = (level.saturating_sub(lo_level) as f64 / (hi_level - lo_level) as f64).min(1.);
    lo[index] + (hi[index] - lo[index]) * fraction
}

// Raise the five-class median against existing monster health to the target time bands.
const PLAYER_ATTACK_CURVE: &[(u32, f64)] = &[
    (1, 1.0),
    (15, 1.0),
    (20, 1.48),
    (30, 1.62),
    (40, 2.83),
    (50, 5.26),
    (60, 7.50),
    (70, 8.19),
    (80, 8.77),
    (90, 9.86),
    (99, 16.56),
];

pub(crate) fn player_attack_scale(class: Class, level: u32) -> f64 {
    class_attack_scale(class, level)
        * crate::model::interpolate_level_scale(PLAYER_ATTACK_CURVE, level)
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Item {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub rarity: String,
    /// Character level needed to wear gear or buy/fit a bag. A level loss does not remove a fitted bag.
    #[serde(default = "first_level", rename = "requiredLevel")]
    pub required_level: u32,
    pub sell: u32,
    #[serde(default)]
    pub attack: f64,
    #[serde(default)]
    pub defense: f64,
    /// Fixed per item type: one level-scaled useful attribute on blue gear, two on purple.
    #[serde(default, rename = "bonusStats")]
    pub bonus_stats: Attributes,
    pub class: Option<Class>,
    pub variant: Option<String>,
    /// The equipment atlas key. Catalog variants can share a fitted drawing;
    /// the client recolours it only when the catalog also supplies a tint.
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
    /// `mount_licence` items: the mount that using the item grants.
    #[serde(default)]
    pub mount: Option<String>,
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
/// Mount licences drop from one kill each, on a roll of their own that is independent of gold, materials, bags and
/// every gear pool, with no bad-luck protection (docs/mounts.md): the Whistle from the Rimesaber, the Egg from the
/// final boss of the Thunderheart Gate.
pub const SABERTOOTH_WHISTLE_CHANCE: f64 = 0.04;
pub const GRYPHON_EGG_CHANCE: f64 = 0.03;
/// The licence a kill of `kind` can drop and its chance. `final_boss` says the kill ended its dungeon.
pub fn mount_licence_drop(kind: &str, final_boss: bool) -> Option<(&'static str, f64)> {
    match kind {
        "rimesaber" => Some(("sabertooth_whistle", SABERTOOTH_WHISTLE_CHANCE)),
        "thunder_heart" if final_boss => Some(("gryphon_egg", GRYPHON_EGG_CHANCE)),
        _ => None,
    }
}
/// Each selected dungeon set piece gets its own rarity roll.
pub const EPIC_SET_DROP_CHANCE: f64 = 0.05;
pub fn set_piece_copy(piece: &Item, roll: f64) -> Option<GearInstance> {
    if roll >= EPIC_SET_DROP_CHANCE || piece.rarity != "rare" || piece.source.is_none() {
        return None;
    }
    let useful: &[&str] = match piece.class {
        Some(Class::Warrior) => &["strength", "stamina", "agility", "accuracy", "dexterity"],
        Some(Class::Mage | Class::Priest) => {
            &["intellect", "stamina", "agility", "accuracy", "dexterity"]
        }
        Some(Class::Assassin | Class::Hunter) => {
            &["agility", "stamina", "strength", "accuracy", "dexterity"]
        }
        None if piece.required_level >= 75 => &["stamina", "strength", "agility"],
        None => &["stamina", "accuracy", "dexterity"],
    };
    let value = [
        piece.bonus_stats.strength,
        piece.bonus_stats.agility,
        piece.bonus_stats.intellect,
        piece.bonus_stats.stamina,
        piece.bonus_stats.dexterity,
        piece.bonus_stats.accuracy,
    ]
    .into_iter()
    .max()
    .unwrap_or(0);
    let mut rolled = Attributes::default();
    for stat in useful {
        let (current, target, cap) = match *stat {
            "strength" => (piece.bonus_stats.strength, &mut rolled.strength, u32::MAX),
            "stamina" => (piece.bonus_stats.stamina, &mut rolled.stamina, u32::MAX),
            "agility" => (piece.bonus_stats.agility, &mut rolled.agility, u32::MAX),
            "intellect" => (piece.bonus_stats.intellect, &mut rolled.intellect, u32::MAX),
            "accuracy" => (piece.bonus_stats.accuracy, &mut rolled.accuracy, 20),
            "dexterity" => (piece.bonus_stats.dexterity, &mut rolled.dexterity, 70),
            _ => unreachable!(),
        };
        if current == 0 && value <= cap {
            *target = value;
            break;
        }
    }
    Some(GearInstance {
        id: 0,
        item: piece.id.clone(),
        rarity: "epic".into(),
        attack: (piece.attack * 1.175 * 10.).round() / 10.,
        defense: (piece.defense * 1.175 * 10.).round() / 10.,
        bonus_stats: piece.bonus_stats.clone(),
        rolled_stats: rolled,
        rank: 0,
    })
}
/// One independent bag roll per enemy defeat, including elites and dungeon bosses.
pub const BAG_DROP_CHANCE: f64 = 0.02;
pub fn roll_bag(enemy_level: u32, chance: f64) -> Option<&'static Item> {
    (chance < BAG_DROP_CHANCE).then(|| {
        ITEMS
            .iter()
            .filter(|i| i.kind == "bag" && i.required_level <= enemy_level)
            .max_by_key(|i| i.required_level)
    })?
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
        .or_else(|| {
            ITEMS.iter().find(|i| {
                i.class.is_none()
                    && i.source.as_deref() == Some("orange_pool")
                    && i.kind == kind
                    && i.variant.as_deref() == Some(variant)
            })
        })
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
        "voidmoth" => "voidwing",
        "crystalwyrm" => "astral_scale",
        "orbitbeetle" => "orbit_shell",
        "eclipsedryad" => "eclipse_bark",
        "meteorgolem" => "meteor_core",
        "miragejackal" => "mirage_fang",
        "shardscarab" => "shard_carapace",
        "glassharrier" => "harrier_pinions",
        "prismsentinel" => "prism_heart",
        "mirrorqueen" => "queens_mirror",
        "sunshard" => "sunshard_core",
        "bronzemantis" => "mantis_blade",
        "gearling" => "gearling_tooth",
        "orbitseer" => "seer_lens",
        "chronoguard" => "chronoguard_plate",
        "pendulummatron" => "matron_pendulum",
        "epochengine" => "epoch_core",
        "glowcapgrazer" => "glowcap",
        "silkwing" => "moon_silk",
        "rootlurker" => "root_heart",
        "lanternwraith" => "wraith_lantern",
        "mireheart" => "mireheart_seed",
        "silverwidow" => "widow_silk",
        "nightbloom" => "nightbloom_petal",
        "dew_moth" => "moon_dew",
        "lumen_eel" => "lumen_scale",
        "rootbell" => "rootbell_seed",
        "tideglass_heron" => "tideglass_plume",
        "hourpetal_stag" => "hourpetal_antler",
        "moonskein_weaver" => "moonskein_thread",
        "moonwell_echo" => "moonwell_shard",
        "saltclaw" => "saltclaw_shell",
        "stormgull" => "stormgull_feather",
        "glassray" => "glassfin",
        "breakersentinel" => "breaker_core",
        "maelstromheart" => "stormheart",
        "meadowhare" => "hare_whisker",
        "sunbacksnail" => "sunback_shell",
        "brushfox" => "fox_tail_tuft",
        "spadebadger" => "badger_claw",
        "honeyjaw" => "honeyjaw_comb",
        "wickerwarden" => "wicker_heart",
        "ribbongecko" => "ribbon_tail",
        "balloonbeetle" => "balloon_silk",
        "paintedmacaw" => "macaw_plume",
        "jesterling" => "jester_bell",
        "paradegryphon" => "gryphon_feather",
        "maskcolossus" => "masquerade_mask",
        "orchidmantis" => "mantis_petals",
        "canopyglider" => "glider_membrane",
        "poolcaiman" => "caiman_scale",
        "drumgorilla" => "gorilla_drumskin",
        "jadeanaconda" => "anaconda_jade",
        "crownjaguar" => "jaguar_crown",
        "sapbeetle" => "sapbeetle_resin",
        "lanternhornet" => "hornet_amber",
        "mosslemur" => "mosslemur_fur",
        "barkmimic" => "barkmimic_chip",
        "sandhopper" => "sandhopper_chitin",
        "dunefennec" => "fennec_fur",
        "glassscorpion" => "scorpion_glass",
        "sunvulture" => "vulture_quill",
        "dunecolossus" => "colossus_core",
        "mirageroc" => "roc_plume",
        "snowhare" => "snowhare_fur",
        "iceotter" => "iceotter_pelt",
        "frostheron" => "heron_feather",
        "glaciercrab" => "glaciercrab_shell",
        "bellmammoth" => "mammoth_bell",
        "auroramanta" => "manta_aurora",
        "crevasseleviathan" => "leviathan_fang",
        "screeferret" => "screeferret_pelt",
        "stoneibex" => "ibex_horn",
        "slateraven" => "slate_raven_feather",
        "ridgeadder" => "ridgeadder_scale",
        "cairnbehemoth" => "behemoth_heartstone",
        "whitebarktitan" => "whitebark_core",
        "stormcondor" => "stormcondor_plume",
        "brooknewt" => "newt_ribbon",
        "sundarter" => "sundarter_scale",
        "acornmimic" => "amber_acorn",
        "snowstoat" => "stoat_silverfur",
        "bloomtortoise" => "bloom_shell",
        "petalchimera" => "chimera_petal",
        "rainseraph" => "seraph_rainfeather",
        "glasslion" => "glasslion_mane",
        "sunwheel" => "sunwheel_cog",
        "firephoenix" => "phoenix_ember",
        "lanternowl" => "lanternowl_eye",
        "harvestreaper" => "reaper_scythe_shard",
        "ambermantis" => "amber_mantis_claw",
        "rimesaber" => "rimesaber_fang",
        "snowgiant" => "snowgiant_heart",
        "longnightwyrm" => "longnight_scale",
        _ => "slime_gel",
    }
}
/// The golden gear of the administrator character. Its rarity "gm" is not in `RARITIES`, so no enemy ever rolls it.
pub const GM_RARITY: &str = "gm";
pub const GM_GEAR: [&str; 8] = [
    "warrior_armor_gm",
    "warrior_headgear_gm",
    "warrior_weapon_gm",
    "warrior_shoulders_gm",
    "warrior_gloves_gm",
    "gm_pants",
    "gm_necklace",
    "gm_accessory",
];
/// The equipment slot of each GM piece that is not part of the look's armor and weapon (see `docs/gm-gear.md`).
const GM_SLOTS: [(&str, &str); 6] = [
    ("headgear", "warrior_headgear_gm"),
    ("shoulders", "warrior_shoulders_gm"),
    ("gloves", "warrior_gloves_gm"),
    ("pants", "gm_pants"),
    ("necklace", "gm_necklace"),
    ("accessory1", "gm_accessory"),
];
/// Rarity tiers, lowest first. The catalog colours them gray, green, blue, purple and orange.
pub const RARITIES: [&str; 5] = ["common", "uncommon", "rare", "epic", "legendary"];
/// Instance elites still use the original single-roll table; outdoor elites have independent tier rolls below.
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
            | "mirrorqueen"
            | "sunshard"
            | "pendulummatron"
            | "epochengine"
            | "mireheart"
            | "silverwidow"
            | "nightbloom"
            | "tideglass_heron"
            | "hourpetal_stag"
            | "moonskein_weaver"
            | "moonwell_echo"
            | "maelstromheart"
            | "honeyjaw"
            | "wickerwarden"
            | "paradegryphon"
            | "maskcolossus"
            | "jadeanaconda"
            | "crownjaguar"
            | "dunecolossus"
            | "mirageroc"
            | "bellmammoth"
            | "auroramanta"
            | "crevasseleviathan"
            | "cairnbehemoth"
            | "whitebarktitan"
            | "stormcondor"
            | "bloomtortoise"
            | "petalchimera"
            | "rainseraph"
            | "glasslion"
            | "sunwheel"
            | "firephoenix"
            | "lanternowl"
            | "harvestreaper"
            | "ambermantis"
            | "rimesaber"
            | "snowgiant"
            | "longnightwyrm"
    ) || is_vault_enemy(kind)
}
/// Everything that lives in the Undervault: the trash packs and the four bosses are all elites.
pub fn is_vault_enemy(kind: &str) -> bool {
    if crate::cathedral::enemy(kind).is_some() {
        return false;
    }
    matches!(
        kind,
        "thrall" | "archer" | "acolyte" | "gatewarden" | "choir" | "colossus" | "hollowking"
    )
}
/// The four bosses of the Undervault (the dungeon under Skaldholm). Each drops guaranteed blue gear.
pub fn is_boss(kind: &str) -> bool {
    if let Some(e) = crate::cathedral::enemy(kind) {
        return e.boss;
    }
    matches!(
        kind,
        "gatewarden"
            | "choir"
            | "colossus"
            | "hollowking"
            | "tideglass_heron"
            | "hourpetal_stag"
            | "moonskein_weaver"
            | "moonwell_echo"
    )
}
/// The slot pools a boss drops from: one shared wing-level blue piece per pool, chosen across all classes.
pub fn boss_slots(kind: &str) -> &'static [&'static [&'static str]] {
    if let Some(e) = crate::cathedral::enemy(kind) {
        if !e.boss {
            return &[];
        }
        if kind == "null_bell"
            || kind == "keel_cargomaw"
            || kind == "barrow_doorward"
            || kind == "span_warden"
        {
            return &[&["headgear", "shoulders", "gloves"]];
        }
        if kind == "null_conductor"
            || kind == "keel_bosun"
            || kind == "barrow_threadkeeper"
            || kind == "span_weaver"
        {
            return &[&["weapon", "pants", "necklace", "accessory"]];
        }
        if kind == "null_hour"
            || kind == "keel_captain"
            || kind == "barrow_fatebound"
            || kind == "span_archon"
        {
            return &[
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
            ];
        }
        if kind == "eye_lenswarden" {
            return &[&["headgear", "shoulders", "gloves"]];
        }
        if kind == "elder_gatekeeper" {
            return &[&["headgear", "shoulders", "gloves"]];
        }
        if kind == "elder_matron" {
            return &[&["weapon", "pants", "necklace"]];
        }
        if kind == "elder_heart" {
            return &[
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
            ];
        }
        if kind == "pavilion_mirror" {
            return &[&["headgear", "shoulders", "gloves"]];
        }
        if kind == "pavilion_weaver" {
            return &[&["weapon", "pants", "necklace"]];
        }
        if kind == "pavilion_sovereign" {
            return &[&["armor", "accessory"]];
        }
        if kind == "rain_crown_gatekeeper" {
            return &[&["headgear", "shoulders", "gloves"]];
        }
        if kind == "rain_crown_sibyl" {
            return &[&["weapon", "pants", "necklace"]];
        }
        if kind == "rain_crown_sovereign" {
            return &[&["armor", "accessory"]];
        }
        if kind == "seed_warden" {
            return &[&["headgear", "shoulders", "gloves"]];
        }
        if kind == "seed_germinator" {
            return &[&["weapon", "pants", "necklace"]];
        }
        if kind == "seed_worldseed" {
            return &[&["armor", "accessory"]];
        }
        if kind == "astro_warden" {
            return &[&["headgear", "shoulders", "gloves"]];
        }
        if kind == "astro_navigator" {
            return &[&["weapon", "pants", "necklace"]];
        }
        if kind == "astro_axis" {
            return &[&["armor", "accessory"]];
        }
        if kind == "thunder_conductor"
            || kind == "bloom_thornkeeper"
            || kind == "solar_ashwarden"
            || kind == "amber_curator"
            || kind == "solstice_watcher"
        {
            return &[&["headgear", "shoulders", "gloves"]];
        }
        if kind == "thunder_bastion"
            || kind == "bloom_mirror"
            || kind == "solar_heliomancer"
            || kind == "amber_chronicle"
            || kind == "solstice_harbinger"
        {
            return &[&["weapon", "pants", "necklace"]];
        }
        if kind == "thunder_heart"
            || kind == "bloom_heart"
            || kind == "solar_heart"
            || kind == "amber_memory"
            || kind == "solstice_heart"
        {
            return &[&["armor", "accessory"]];
        }
        if kind == "eye_undertide" {
            return &[&["weapon", "pants", "necklace"]];
        }
        if kind == "eye_unblinking" {
            return &[
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
            ];
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
                "necklace",
                "accessory",
            ],
        ],
        "tideglass_heron" => &[&["headgear", "shoulders"]],
        "hourpetal_stag" => &[&["weapon", "pants"]],
        "moonskein_weaver" => &[&["gloves", "necklace", "accessory"]],
        "moonwell_echo" => &[
            &["armor", "weapon", "headgear"],
            &["gloves", "pants", "necklace", "accessory"],
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
    if matches!(
        kind,
        "tideglass_heron" | "hourpetal_stag" | "moonskein_weaver" | "moonwell_echo"
    ) {
        let pool: Vec<_> = ITEMS
            .iter()
            .filter(|i| {
                i.rarity == "rare"
                    && i.required_level == 60
                    && i.source.as_deref() == Some("moonwell")
                    && slots.contains(&i.kind.as_str())
            })
            .collect();
        return pool.get((choice * pool.len() as f64) as usize).copied();
    }
    let Some(e) = crate::cathedral::enemy(kind) else {
        return boss_piece(slots, choice);
    };
    let source = e.loot_source.as_deref()?;
    let (rarity, level) = if source == "blackhour" {
        ("epic", 99)
    } else {
        ("rare", e.level.min(95))
    };
    let pool: Vec<_> = ITEMS
        .iter()
        .filter(|i| {
            i.rarity == rarity
                && i.required_level == level
                && i.source.as_deref() == Some(source)
                && slots.contains(&i.kind.as_str())
        })
        .collect();
    pool.get((choice * pool.len() as f64) as usize).copied()
}
/// The original single-roll table for ordinary enemies and instance elites. Outdoor elites use
/// independent rolls instead. `roll` is uniform in [0, 1); legendary exists only for elites.
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
/// Independent equipment rolls for an elite killed outside an instance. Green is guaranteed;
/// blue and purple can both drop on the same kill. Preserve the old gray and orange odds.
pub fn outdoor_elite_drop_chance(rarity: &str) -> f64 {
    match rarity {
        "uncommon" => 1.,
        "rare" => 0.33,
        "epic" => 0.05,
        "common" | "legendary" => base_drop_chance(rarity) * ELITE_DROP_MULTIPLIER,
        _ => 0.,
    }
}
/// A random piece of gear of the rolled tier that an enemy of this level can drop (see `max_drop_level`); starter
/// pieces never drop, and an empty tier drops nothing.
pub fn roll_equipment(kind: &str, level: u32, chance: f64, choice: f64) -> Option<&'static Item> {
    let rarity = roll_rarity(kind, chance)?;
    equipment_of_rarity(rarity, level, choice)
}
pub fn equipment_of_rarity(rarity: &str, level: u32, choice: f64) -> Option<&'static Item> {
    let limit = max_drop_level(level);
    let pool: Vec<_> = ITEMS
        .iter()
        .filter(|i| {
            i.rarity == rarity
                && is_gear(i)
                && !i.starter
                && i.source.is_none()
                && i.required_level <= limit
                && (level < 50
                    || i.required_level
                        >= (if level >= 75 {
                            75
                        } else if level >= 70 {
                            70
                        } else if level >= 65 {
                            65
                        } else if level >= 55 {
                            55
                        } else {
                            50
                        }))
        })
        .collect();
    pool.get((choice * pool.len() as f64) as usize).copied()
}
impl Character {
    pub fn bag_capacity(&self) -> usize {
        16 + self.rebirth_bag_cells()
            + self
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
            if i.kind == "bag" {
                self.can_fit_bag(id).is_ok()
            } else {
                self.quantity(id) > self.equipped_count(i) || self.bag_used() < self.bag_capacity()
            }
        })
    }
    /// None means an empty expansion slot; Some(index) replaces the smallest smaller bag.
    fn bag_slot(&self, id: &str) -> Result<Option<usize>, &'static str> {
        let bag = item(id)
            .filter(|i| i.kind == "bag" && i.bag_slots > 0)
            .ok_or("Unknown bag.")?;
        if self.hp <= 0. {
            return Err("You cannot fit bags while defeated.");
        }
        if self.level < bag.required_level {
            return Err("Your level is too low for this bag.");
        }
        if self.bags.len() < 4 {
            return Ok(None);
        }
        self.bags
            .iter()
            .enumerate()
            .filter_map(|(n, id)| {
                item(id)
                    .filter(|i| i.bag_slots < bag.bag_slots)
                    .map(|i| (n, i.bag_slots))
            })
            .min_by_key(|(_, size)| *size)
            .map(|(n, _)| Some(n))
            .ok_or("All four expansion bag slots are filled.")
    }
    pub fn can_fit_bag(&self, id: &str) -> Result<(), &'static str> {
        self.bag_slot(id).map(|_| ())
    }
    pub fn fit_bag(&mut self, id: &str) -> Result<usize, &'static str> {
        match self.bag_slot(id)? {
            Some(index) => self.bags[index] = id.into(),
            None => self.bags.push(id.into()),
        }
        Ok(self.bag_capacity())
    }
    pub fn purchase_bag(&mut self, id: &str) -> Result<usize, &'static str> {
        let price = item(id)
            .filter(|i| i.kind == "bag" && i.bag_slots > 0)
            .ok_or("Unknown bag.")?
            .price;
        self.bag_slot(id)?;
        if self.gold < price {
            return Err("You need more gold for this bag.");
        }
        let capacity = self.fit_bag(id)?;
        self.gold -= price;
        Ok(capacity)
    }
    /// Seconds left of the potion cooldown, from the saved wall-clock end (never more than an hour).
    pub fn potion_cooldown_left(&self) -> f64 {
        self.potion_ready.saturating_sub(unix_now()).min(3600) as f64
    }
    /// Seconds left of the shared meal cooldown, from the saved wall-clock end (never more than an hour).
    pub fn meal_cooldown_left(&self) -> f64 {
        self.meal_ready.saturating_sub(unix_now()).min(3600) as f64
    }
    pub fn quantity(&self, id: &str) -> u32 {
        self.inventory
            .iter()
            .find(|s| s.item == id)
            .map_or(0, |s| s.quantity)
    }
    /// Uses up `quantity` of a loose item. False, and nothing changes, when there are fewer in the bags.
    pub fn consume_item(&mut self, id: &str, quantity: u32) -> bool {
        let Some(stack) = self
            .inventory
            .iter_mut()
            .find(|s| s.item == id && s.quantity >= quantity)
        else {
            return false;
        };
        stack.quantity -= quantity;
        self.inventory.retain(|s| s.quantity > 0);
        true
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
        if i.class != Some(self.look.class) && i.source.as_deref() != Some("orange_pool") {
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
    pub(crate) fn worn_items(&self) -> Vec<&'static Item> {
        let (armor, weapon) = self.gear();
        let class = self.look.class;
        self.equipment
            .values()
            .filter_map(|id| item(id))
            .chain(equipment(class, "armor", armor))
            .chain(equipment(class, "weapon", weapon))
            .collect()
    }
    /// Count distinct equipment kinds, so wearing two accessories never substitutes for a missing set slot.
    /// Catalog source identifies the set even when a copy has been merged to epic or refined.
    pub fn set_counts(&self) -> std::collections::BTreeMap<String, usize> {
        let mut kinds =
            std::collections::BTreeMap::<String, std::collections::BTreeSet<String>>::new();
        for piece in self.worn_items() {
            let Some(source) = piece.source.as_deref() else {
                continue;
            };
            if !crate::sets::is_set(source)
                || piece.required_level > self.level
                || piece.class.is_some_and(|class| class != self.look.class)
            {
                continue;
            }
            kinds
                .entry(source.into())
                .or_default()
                .insert(piece.kind.clone());
        }
        kinds
            .into_iter()
            .map(|(source, slots)| (source, slots.len()))
            .collect()
    }

    /// Additive percentage bonuses from active two-piece tiers; every other tier is resolved in combat.
    pub fn set_stat_bonus(&self, stat: &str) -> f64 {
        let counts = self.set_counts();
        crate::sets::rows(self.look.class)
            .filter(|row| row.stat == stat && counts.get(&row.source).is_some_and(|n| *n >= 2))
            .count() as f64
            * 0.05
    }
    /// Attribute points supplied by usable worn gear. These never spend or refund trained points.
    pub fn gear_attributes(&self) -> Attributes {
        let mut bonus = Attributes::default();
        let mut occurrences = std::collections::BTreeMap::<&str, usize>::new();
        for i in self.worn_items().into_iter().filter(|i| {
            i.required_level <= self.level && i.class.is_none_or(|class| class == self.look.class)
        }) {
            let occurrence = occurrences.entry(&i.id).or_default();
            let stats = self.worn_gear_instance(&i.id, *occurrence).map_or_else(
                || i.bonus_stats.clone(),
                GearInstance::effective_bonus_stats,
            );
            *occurrence += 1;
            bonus.strength = bonus.strength.saturating_add(stats.strength);
            bonus.agility = bonus.agility.saturating_add(stats.agility);
            bonus.intellect = bonus.intellect.saturating_add(stats.intellect);
            bonus.stamina = bonus.stamina.saturating_add(stats.stamina);
            bonus.dexterity = bonus.dexterity.saturating_add(stats.dexterity);
            bonus.accuracy = bonus.accuracy.saturating_add(stats.accuracy);
        }
        bonus
    }
    pub fn effective_attributes(&self) -> Attributes {
        let bonus = self.gear_attributes();
        let passive = crate::skills::passive_bonus(self.look.class, self.level);
        Attributes {
            strength: self
                .attributes
                .strength
                .saturating_add(bonus.strength)
                .saturating_add(passive.strength),
            agility: self
                .attributes
                .agility
                .saturating_add(bonus.agility)
                .saturating_add(passive.agility),
            intellect: self
                .attributes
                .intellect
                .saturating_add(bonus.intellect)
                .saturating_add(passive.intellect),
            stamina: self
                .attributes
                .stamina
                .saturating_add(bonus.stamina)
                .saturating_add(passive.stamina),
            dexterity: self
                .attributes
                .dexterity
                .saturating_add(bonus.dexterity)
                .saturating_add(passive.dexterity),
            accuracy: self
                .attributes
                .accuracy
                .saturating_add(bonus.accuracy)
                .saturating_add(passive.accuracy),
        }
    }
    /// Keep missing HP/mana stable when an item's Stamina or Intellect changes the maxima.
    fn preserve_vitals_after_equipping(&mut self, before: &Character) {
        let health_change = self.max_hp() - before.max_hp();
        self.hp = (before.hp + health_change).clamp(1., self.max_hp());
        if self.look.class.resource_type() == "mana" {
            let mana_change = self.max_resource() - before.max_resource();
            self.resource = Some((before.resource() + mana_change).clamp(0., self.max_resource()));
        }
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
        self.mark_starters_granted();
    }
    /// Records every starter piece of this class that the character owns as given, so selling it is final.
    fn mark_starters_granted(&mut self) {
        let class = self.look.class;
        let owned: Vec<_> = ITEMS
            .iter()
            .filter(|i| i.starter && i.class == Some(class) && self.quantity(&i.id) > 0)
            .map(|i| i.id.clone())
            .collect();
        for id in owned {
            if !self.starters_granted.contains(&id) {
                self.starters_granted.push(id);
            }
        }
    }
    /// Turns a new character into the administrator character: a male Warrior named [GM]Sork wearing the whole golden
    /// set. Called by the store while the character is created, never for a loaded save.
    pub fn become_gm(&mut self) {
        self.gm = true;
        self.look.name = GM_NAME.into();
        self.look.class = Class::Warrior;
        self.look.gender = crate::model::Gender::Male;
        self.hp = self.max_hp();
        let _ = self.look.equip("gm", "gm");
        self.grant_missing_gm_gear();
    }
    /// Gives the administrator character every golden piece it does not own yet and wears each new piece whose slot is
    /// empty (the set grew after the first GM was created). A piece the GM took off on purpose stays off, because it
    /// is still owned.
    pub fn grant_missing_gm_gear(&mut self) {
        if !self.gm {
            return;
        }
        for id in GM_GEAR {
            if self.quantity(id) > 0 {
                continue;
            }
            self.add_item(id, 1);
            if let Some((slot, _)) = GM_SLOTS.iter().find(|(_, piece)| *piece == id) {
                self.equipment
                    .entry((*slot).into())
                    .or_insert_with(|| id.into());
            }
        }
        self.sync_look();
    }
    /// Gives a character the starter pieces of their class that they have never been given (new catalog entries reach
    /// existing saves this way). A piece that was given and later sold or banked is listed in `starters_granted` and
    /// never comes back. Pieces that would overfill the bags wait for the next load.
    pub fn grant_missing_starters(&mut self) {
        self.mark_starters_granted();
        let class = self.look.class;
        let ids: Vec<_> = ITEMS
            .iter()
            .filter(|i| {
                i.starter && i.class == Some(class) && !self.starters_granted.contains(&i.id)
            })
            .map(|i| i.id.clone())
            .collect();
        for id in ids {
            if self.bag_used() < self.bag_capacity() {
                self.add_item(&id, 1);
                self.starters_granted.push(id);
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
                    .is_some_and(|i| self.quantity(&i.id) > 0 && (self.gm || i.rarity != GM_RARITY))
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
        next.preserve_vitals_after_equipping(self);
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
                                && (self.gm || i.rarity != GM_RARITY)
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
        next.preserve_vitals_after_equipping(self);
        *self = next;
        Ok(())
    }
    pub fn stats(&self) -> (f64, f64) {
        let (mut attack, mut defense) = self.look.stats(self.level);
        let effective = self.effective_attributes();
        let a = &effective;
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
        let mut occurrences = std::collections::BTreeMap::<&str, usize>::new();
        for i in self
            .worn_items()
            .into_iter()
            .filter(|i| i.required_level <= self.level)
        {
            let occurrence = occurrences.entry(&i.id).or_default();
            if let Some(copy) = self.worn_gear_instance(&i.id, *occurrence) {
                attack += copy.effective_attack() - i.attack;
                defense += copy.effective_defense() - i.defense;
            }
            *occurrence += 1;
        }
        (
            attack
                * player_attack_scale(self.look.class, self.level)
                * (1. + self.set_stat_bonus("attack")),
            defense * (1. + self.set_stat_bonus("defense")),
        )
    }
    pub fn sell_item(&mut self, id: &str, quantity: u32) -> Result<u32, &'static str> {
        let i = item(id).ok_or("Unknown item.")?;
        if i.rarity == GM_RARITY {
            return Err("Game master gear cannot be sold.");
        }
        if i.kind == "mount_licence" {
            return Err("A mount licence is bound to you and cannot be sold.");
        }
        let available = self.quantity(id).saturating_sub(self.equipped_count(i));
        if quantity == 0 || quantity > available {
            return Err("You can only sell items you own. Equipped items must be kept.");
        }
        if is_gear(i) {
            self.materialize_gear_instances();
        }
        let epic_copies = self
            .gear_instances
            .iter()
            .filter(|g| g.item == id)
            .skip(self.equipped_count(i) as usize)
            .take(quantity as usize)
            .filter(|g| i.rarity == "rare" && g.rarity == "epic")
            .count() as u32;
        let value = quantity
            .checked_add(epic_copies)
            .and_then(|count| i.sell.checked_mul(count))
            .map(|value| self.boosted_gold(value))
            .filter(|value| self.gold.checked_add(*value).is_some())
            .ok_or("That sale is too large.")?;
        if is_gear(i) {
            self.remove_loose_gear_instances(i, quantity);
        }
        let stack = self.inventory.iter_mut().find(|s| s.item == id).unwrap();
        stack.quantity -= quantity;
        self.inventory.retain(|s| s.quantity > 0);
        self.gold += value;
        Ok(value)
    }
}

/// Extra (health, damage) multipliers per monster kind from `world/elite-power.txt`, `(1, 1)` for every kind not listed.
/// They tune how hard a kind is without touching its base table: the group elites that a lone player in ordinary gear
/// must not be able to kill (`ELITE-SOLO-TEST`, `docs/elite-solo-report.md`).
pub fn elite_power(kind: &str) -> (f64, f64) {
    use std::collections::BTreeMap;
    use std::sync::OnceLock;
    static POWER: OnceLock<BTreeMap<String, [f64; 2]>> = OnceLock::new();
    POWER
        .get_or_init(|| {
            // Test builds may read another table (`ELITE_POWER_FILE=path`), so calibrating a multiplier needs no rebuild.
            #[cfg(test)]
            if let Ok(path) = std::env::var("ELITE_POWER_FILE") {
                let text = std::fs::read_to_string(&path).expect("readable ELITE_POWER_FILE");
                return serde_json::from_str(&text).expect("valid ELITE_POWER_FILE table");
            }
            serde_json::from_str(include_str!("../../world/elite-power.txt"))
                .expect("valid elite power table")
        })
        .get(kind)
        .map_or((1., 1.), |p| (p[0], p[1]))
}

/// Soft enrage of a boss from `world/enrage.txt`: `kind -> [start, ramp]` (or `[start, ramp, cap]`), in seconds. After
/// `start` seconds of fighting, the boss's damage grows by 100% every `ramp` seconds (`1 + (fight - start) / ramp`),
/// which a party that burns the boss down never sees and a lone player who needs minutes cannot outlast
/// (`DUNGEON-BOSS-LETHAL`). The optional `cap` is the most the factor can reach: the open-world elites use `3.0`, so
/// their damage triples once the enrage begins and stays there.
fn enrage_entry(kind: &str) -> Option<&'static Vec<f64>> {
    use std::collections::BTreeMap;
    use std::sync::OnceLock;
    static TABLE: OnceLock<BTreeMap<String, Vec<f64>>> = OnceLock::new();
    TABLE
        .get_or_init(|| {
            // Test builds may read another table (`ENRAGE_FILE=path`), so calibrating needs no rebuild.
            #[cfg(test)]
            if let Ok(path) = std::env::var("ENRAGE_FILE") {
                let text = std::fs::read_to_string(&path).expect("readable ENRAGE_FILE");
                return serde_json::from_str(&text).expect("valid ENRAGE_FILE table");
            }
            serde_json::from_str(include_str!("../../world/enrage.txt"))
                .expect("valid enrage table")
        })
        .get(kind)
}
pub fn enrage(kind: &str) -> Option<(f64, f64)> {
    enrage_entry(kind).map(|p| (p[0], p[1].max(0.1)))
}
/// The damage multiplier of `kind` after `fight` seconds of combat: 1 until its enrage starts.
pub fn enrage_factor(kind: &str, fight: f64) -> f64 {
    enrage_entry(kind).map_or(1., |p| {
        let factor = 1. + ((fight - p[0]) / p[1].max(0.1)).max(0.);
        p.get(2).map_or(factor, |cap| factor.min(*cap))
    })
}

/// Range, speed, colour, size, fan count, spread and melee reach of a boss projectile.
pub type BossRangedProfile = (f64, f64, String, f64, u32, f64, f64);

/// A boss's ranged attack from `world/boss-ranged.txt`: `kind -> [range, speed, colour, size, shots, spread, melee]`
/// (the fields of `Slime::ranged` and `Slime::melee_inside`). It takes precedence over the encounter catalog, so a boss
/// that a ranged hero could kite outside its reach shoots, and the fan always has an odd number of shots: with an even
/// number none flies straight and a hero standing still in the gap is never hit.
pub fn boss_ranged(kind: &str) -> Option<&'static BossRangedProfile> {
    use std::collections::BTreeMap;
    use std::sync::OnceLock;
    static TABLE: OnceLock<BTreeMap<String, BossRangedProfile>> = OnceLock::new();
    TABLE
        .get_or_init(|| {
            // Test builds may read another table (`BOSS_RANGED_FILE=path`), so calibrating needs no rebuild.
            #[cfg(test)]
            if let Ok(path) = std::env::var("BOSS_RANGED_FILE") {
                let text = std::fs::read_to_string(&path).expect("readable BOSS_RANGED_FILE");
                return serde_json::from_str(&text).expect("valid BOSS_RANGED_FILE table");
            }
            serde_json::from_str(include_str!("../../world/boss-ranged.txt"))
                .expect("valid boss ranged table")
        })
        .get(kind)
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
    fn a_boss_enrages_only_after_its_start_and_then_ramps_linearly() {
        assert_eq!(enrage_factor("no_such_boss", 500.), 1.);
        let (start, ramp) = enrage("bellkeeper").expect("bellkeeper has an enrage");
        assert!(start > 30. && start < 180. && ramp > 0.);
        assert_eq!(enrage_factor("bellkeeper", 0.), 1.);
        assert_eq!(enrage_factor("bellkeeper", start), 1.);
        assert!((enrage_factor("bellkeeper", start + ramp * 3.) - 4.).abs() < 1e-9);
    }
    #[test]
    fn every_boss_ranged_attack_is_a_boss_with_an_odd_fan() {
        let table: std::collections::BTreeMap<String, BossRangedProfile> =
            serde_json::from_str(include_str!("../../world/boss-ranged.txt")).unwrap();
        assert!(table.len() >= 20, "{} bosses", table.len());
        for (kind, (range, speed, _, size, shots, spread, melee)) in table {
            assert!(is_boss(&kind), "{kind} is not a boss");
            assert!(
                shots % 2 == 1,
                "{kind}: an even fan leaves a gap at the target"
            );
            assert!(
                range > melee && speed > 0. && size > 0. && spread > 0.,
                "{kind}"
            );
        }
    }
    #[test]
    fn an_elite_enrage_triples_its_damage_at_180_s_and_stops_there() {
        assert_eq!(enrage_factor("kraken", 179.), 1.);
        assert_eq!(enrage_factor("kraken", 180.), 1.);
        assert!(enrage_factor("kraken", 180.1) > 1. && enrage_factor("kraken", 180.1) < 3.);
        assert_eq!(enrage_factor("kraken", 181.), 3.);
        assert_eq!(enrage_factor("kraken", 900.), 3.);
        // A boss has no cap: its damage keeps growing.
        assert!(enrage_factor("bellkeeper", 500.) > 3.);
    }
    #[test]
    fn every_open_world_elite_enrages_at_180_s_and_the_instance_bosses_keep_their_own() {
        for kind in ["big", "cinderlord", "gloomroot", "kraken", "longnightwyrm"] {
            assert_eq!(enrage(kind), Some((180., 0.2)), "{kind}");
        }
        assert_ne!(enrage("moonwell_echo").map(|e| e.0), Some(180.));
    }
    #[test]
    fn every_enrage_start_is_after_a_plausible_party_kill_and_before_the_fight_limit() {
        let table: std::collections::BTreeMap<String, Vec<f64>> =
            serde_json::from_str(include_str!("../../world/enrage.txt")).unwrap();
        assert!(table.len() >= 40, "{} bosses", table.len());
        for (kind, entry) in table {
            let (start, ramp) = (entry[0], entry[1]);
            // Bosses, plus the open-world elites (180 s, `world/enrage.txt`).
            assert!(
                is_boss(&kind) || is_elite(&kind),
                "{kind} is not a boss or an elite"
            );
            assert!(
                (30. ..=if kind.starts_with("null_") {
                    720.
                } else {
                    180.
                })
                    .contains(&start)
                    && (0.1..=10.).contains(&ramp),
                "{kind}"
            );
        }
    }
    #[test]
    fn dungeon_set_epic_copy_has_independent_threshold_and_sale_value() {
        for piece in ITEMS.iter().filter(|i| {
            i.rarity == "rare" && i.source.as_deref().is_some_and(|s| s != "orange_pool")
        }) {
            let epic = set_piece_copy(piece, 0.0499).unwrap();
            assert!(set_piece_copy(piece, 0.05).is_none(), "{}", piece.id);
            assert_eq!(epic.item, piece.id);
            assert_eq!(epic.rarity, "epic");
            assert_eq!(epic.attack, (piece.attack * 11.75).round() / 10.);
            assert_eq!(epic.defense, (piece.defense * 11.75).round() / 10.);
            assert_eq!(epic.bonus_stats, piece.bonus_stats);
            let combined = epic.effective_bonus_stats();
            let present = [
                combined.strength,
                combined.agility,
                combined.intellect,
                combined.stamina,
                combined.dexterity,
                combined.accuracy,
            ];
            assert_eq!(
                present.into_iter().filter(|n| *n > 0).count(),
                2,
                "{}",
                piece.id
            );
            assert!(
                combined.accuracy <= 20 && combined.dexterity <= 70,
                "{}",
                piece.id
            );
            assert_eq!(epic.rank, 0);
            assert_eq!(epic.crystal(), "refinement_crystal_epic");
        }
        let piece = ITEMS
            .iter()
            .find(|i| i.source.as_deref() == Some("undervault") && i.kind == "necklace")
            .or_else(|| {
                ITEMS
                    .iter()
                    .find(|i| i.source.as_deref() == Some("undervault"))
            })
            .unwrap();
        let mut c = character();
        c.add_item(&piece.id, 1);
        c.materialize_gear_instances();
        c.gear_instances
            .iter_mut()
            .find(|g| g.item == piece.id)
            .unwrap()
            .rarity = "epic".into();
        let saved = serde_json::to_string(&c).unwrap();
        let mut loaded: Character = serde_json::from_str(&saved).unwrap();
        assert_eq!(
            loaded
                .gear_instances
                .iter()
                .find(|g| g.item == piece.id)
                .unwrap()
                .rarity,
            "epic"
        );
        assert_eq!(loaded.sell_item(&piece.id, 1).unwrap(), piece.sell * 2);
        let mut refining = character();
        refining.add_item(&piece.id, 2);
        refining.materialize_gear_instances();
        for copy in refining
            .gear_instances
            .iter_mut()
            .filter(|g| g.item == piece.id)
        {
            copy.rarity = "epic".into();
        }
        let ids: Vec<_> = refining
            .gear_instances
            .iter()
            .filter(|g| g.item == piece.id)
            .map(|g| g.id)
            .collect();
        assert!(refining.preview_merge(ids[0], ids[1]).is_err());
        refining.gold = 1_000;
        refining.add_item("refinement_crystal_epic", 1);
        let (ranked, paid, used) = refining.refine_gear(ids[0]).unwrap();
        assert_eq!(
            (ranked.rarity.as_str(), ranked.rank, paid, used),
            ("epic", 1, 800, 1)
        );
    }
    fn attribute_attack(a: &Attributes, class: Class) -> f64 {
        a.strength as f64 * if class == Class::Warrior { 2. } else { 0.5 }
            + a.agility as f64
                * if matches!(class, Class::Assassin | Class::Hunter) {
                    2.
                } else {
                    0.5
                }
            + a.intellect as f64
                * if matches!(class, Class::Mage | Class::Priest) {
                    2.
                } else {
                    0.5
                }
    }
    #[test]
    fn blue_and_purple_attribute_bonuses_are_fixed_useful_and_save_with_gear() {
        for i in ITEMS.iter().filter(|i| {
            is_gear(i) && i.rarity != GM_RARITY && i.source.as_deref() != Some("orange_pool")
        }) {
            let a = &i.bonus_stats;
            let values = [
                ("strength", a.strength),
                ("agility", a.agility),
                ("intellect", a.intellect),
                ("stamina", a.stamina),
                ("dexterity", a.dexterity),
                ("accuracy", a.accuracy),
            ];
            let expected = match i.rarity.as_str() {
                "rare" => 1,
                "epic" => 2,
                _ => 0,
            };
            assert_eq!(
                values.iter().filter(|(_, value)| *value > 0).count(),
                expected,
                "{}",
                i.id
            );
            let useful: &[&str] = match i.class {
                Some(Class::Warrior) => {
                    &["strength", "stamina", "agility", "accuracy", "dexterity"]
                }
                Some(Class::Mage | Class::Priest) => {
                    &["intellect", "stamina", "agility", "accuracy", "dexterity"]
                }
                Some(Class::Assassin | Class::Hunter) => {
                    &["agility", "stamina", "strength", "accuracy", "dexterity"]
                }
                None if i.required_level >= 75 => &["stamina", "strength", "agility"],
                None => &["stamina", "accuracy", "dexterity"],
            };
            for (name, value) in values {
                if value > 0 {
                    let expected = match i.required_level {
                        1 | 5 => 1,
                        10 => 3,
                        15 => 5,
                        20 => 7,
                        25 => 10,
                        30 => 15,
                        35 => 20,
                        40 => 30,
                        45 => 35,
                        50 => 40,
                        55 => 48,
                        60 => 55,
                        65 => 63,
                        70 => 70,
                        75 => 78,
                        80 => 85,
                        85 => 93,
                        90 => 100,
                        95 | 99 => 108,
                        level => panic!("unexpected gear level {level}"),
                    };
                    assert_eq!(value, expected, "{}", i.id);
                    assert!(useful.contains(&name), "{} has irrelevant {name}", i.id);
                    assert!(name != "accuracy" || value <= 20, "{} overcaps hit", i.id);
                    assert!(
                        name != "dexterity" || value <= 70,
                        "{} overcaps dodge",
                        i.id
                    );
                }
            }
        }
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            for rarity in ["rare", "epic"] {
                let i = ITEMS
                    .iter()
                    .find(|i| {
                        i.class == Some(class)
                            && i.kind == "weapon"
                            && i.required_level == 40
                            && i.rarity == rarity
                            && i.source.is_none()
                    })
                    .unwrap();
                let mut c = character();
                c.look.class = class;
                c.inventory.clear();
                c.seed_inventory();
                c.level = 40;
                c.add_item(&i.id, 1);
                c.equip_slots(&slots(&[("hands", "none")])).unwrap();
                let points = c.stat_points();
                let before = c.stats();
                let hp = c.max_hp();
                let health_scale = hp / c.legacy_max_hp();
                let mana = c.max_resource();
                c.equip_slots(&slots(&[("hands", &i.id)])).unwrap();
                assert_eq!(c.gear_attributes(), i.bonus_stats, "{} fixed bonus", i.id);
                assert_eq!(
                    c.stat_points(),
                    points,
                    "gear does not spend trained points"
                );
                assert!(
                    (c.stats().0
                        - before.0
                        - (i.attack + attribute_attack(&i.bonus_stats, class))
                            * player_attack_scale(class, c.level))
                    .abs()
                        < 1e-8,
                    "{} attack",
                    i.id
                );
                assert!(
                    (c.stats().1 - before.1 - i.defense - i.bonus_stats.strength as f64 * 0.2)
                        .abs()
                        < 1e-8,
                    "{} defense",
                    i.id
                );
                assert_eq!(
                    c.max_hp() - hp,
                    i.bonus_stats.stamina as f64 * 8. * health_scale,
                    "{} health",
                    i.id
                );
                assert_eq!(
                    c.max_resource() - mana,
                    if class.resource_type() == "mana" {
                        i.bonus_stats.intellect as f64 * 5.
                    } else {
                        0.
                    },
                    "{} resource",
                    i.id
                );
                let saved: Character =
                    serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
                assert_eq!(
                    saved.gear_attributes(),
                    i.bonus_stats,
                    "{} survives save",
                    i.id
                );
            }
        }
    }
    #[test]
    fn equipping_stamina_and_intellect_preserves_missing_health_and_mana() {
        let id = "mage_gloves_runic_l20_purple";
        let i = item(id).unwrap();
        assert_eq!(i.bonus_stats.stamina, 7);
        assert_eq!(i.bonus_stats.intellect, 7);
        let mut c = character();
        c.look.class = Class::Mage;
        c.inventory.clear();
        c.seed_inventory();
        c.level = 20;
        c.add_item(id, 1);
        let hp = c.max_hp();
        let health_gain = 56. * hp / c.legacy_max_hp();
        let mana = c.max_resource();
        c.hp = hp - 25.;
        c.resource = Some(mana - 15.);
        let points = c.stat_points();
        c.equip_slots(&slots(&[("gloves", id)])).unwrap();
        assert_eq!(c.max_hp(), hp + health_gain);
        assert_eq!(c.hp, hp - 25. + health_gain);
        assert_eq!(c.max_resource(), mana + 35.);
        assert_eq!(c.resource(), mana - 15. + 35.);
        assert_eq!(c.stat_points(), points);
        c.equip_slots(&slots(&[("gloves", "none")])).unwrap();
        assert_eq!(c.hp, hp - 25.);
        assert_eq!(c.resource(), mana - 15.);
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
            let attack_gain = 3. * player_attack_scale(class, c.level);
            let health_gain = 8. * hp / c.legacy_max_hp();
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
            assert!((c.stats().0 - attack - attack_gain).abs() < 1e-9);
            assert_eq!(c.stats().1, defense + 0.2);
            assert_eq!(c.max_hp(), hp + health_gain);
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
    fn recommended_stats_spend_only_unspent_points_and_respect_effective_caps() {
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let mut c = character();
            c.look.class = class;
            c.level = 50;
            c.attributes.accuracy = 20;
            c.attributes.dexterity = 70;
            c.attributes.stamina = 5;
            let before = c.attributes.clone();
            let hp = c.hp;
            let points = c.stat_points();
            let spent = c.allocate_recommended().unwrap();
            assert_eq!(c.stat_points(), 0, "{class:?}");
            assert_eq!(
                spent.strength
                    + spent.agility
                    + spent.intellect
                    + spent.stamina
                    + spent.dexterity
                    + spent.accuracy,
                points
            );
            assert_eq!(c.attributes.accuracy, 20);
            assert_eq!(c.attributes.dexterity, 70);
            assert!(c.attributes.stamina >= before.stamina);
            assert!(c.hp >= hp);
            assert_eq!(
                c.allocate_recommended(),
                Err("You have no stat points to spend.")
            );
            let saved: Character =
                serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
            assert_eq!(saved.attributes, c.attributes);
        }
        let mut mage = character();
        mage.look.class = Class::Mage;
        mage.level = 10;
        mage.attributes.intellect = 12;
        let old = mage.attributes.clone();
        mage.allocate_recommended().unwrap();
        assert!(
            mage.attributes.intellect >= old.intellect,
            "manual training is preserved"
        );
        assert!(
            mage.attributes.stamina > 0,
            "an intellect-heavy mage gets survival points"
        );
        mage.hp = 0.;
        let saved = mage.attributes.clone();
        assert_eq!(
            mage.allocate_recommended(),
            Err("You cannot train stats while defeated.")
        );
        assert_eq!(mage.attributes, saved);
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
    fn spare_starter_pieces_can_be_sold_and_never_come_back() {
        let mut c = character();
        let spare: Vec<_> = ITEMS
            .iter()
            .filter(|i| i.starter && i.class == Some(c.look.class))
            .filter(|i| c.quantity(&i.id) > c.equipped_count(i))
            .map(|i| i.id.clone())
            .collect();
        assert!(spare.len() >= 3, "a new hero carries spare starter pieces");
        let used = c.bag_used();
        for id in &spare {
            assert_eq!(c.sell_item(id, 1), Ok(0), "{id}");
        }
        assert_eq!(c.bag_used(), used - spare.len());
        // Worn pieces are still kept.
        let worn = ITEMS
            .iter()
            .find(|i| i.starter && i.class == Some(c.look.class) && c.equipped_count(i) > 0)
            .expect("a worn starter piece");
        assert!(c.sell_item(&worn.id, 1).is_err());
        // A save, a reload and the grant that runs on every load bring nothing back.
        let mut again: Character =
            serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
        again.grant_missing_starters();
        for id in &spare {
            assert_eq!(again.quantity(id), 0, "{id} stays sold");
        }
        assert_eq!(again.bag_used(), c.bag_used());
    }

    #[test]
    fn a_save_from_before_the_list_gets_a_missing_starter_piece_once() {
        let mut c = character();
        let id = ITEMS
            .iter()
            .find(|i| {
                i.starter
                    && i.class == Some(c.look.class)
                    && c.quantity(&i.id) > c.equipped_count(i)
            })
            .map(|i| i.id.clone())
            .expect("a spare starter piece");
        c.sell_item(&id, 1).unwrap();
        c.starters_granted.clear();
        c.grant_missing_starters();
        assert_eq!(c.quantity(&id), 1, "an old save is given what it lacks");
        assert!(c.starters_granted.contains(&id));
        c.sell_item(&id, 1).unwrap();
        c.grant_missing_starters();
        assert_eq!(c.quantity(&id), 0, "and only that once");
    }

    #[test]
    fn game_master_gear_never_drops_and_the_gm_rarity_cannot_be_rolled() {
        assert_eq!(GM_GEAR.len(), 8);
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
        let mut ordinary = character();
        ordinary.add_item("warrior_weapon_gm", 1);
        let armor = ordinary.look.warrior_armor.clone();
        assert!(ordinary.equip_owned(&armor, "gm").is_err());
        assert!(
            ordinary
                .equip_slots(&[("hands".into(), "warrior_weapon_gm".into())].into())
                .is_err()
        );
    }
    #[test]
    fn no_ordinary_character_can_equip_any_golden_piece() {
        for id in GM_GEAR {
            let mut ordinary = character();
            ordinary.add_item(id, 1);
            let slot = GM_SLOTS.iter().find(|(_, piece)| *piece == id).map_or_else(
                || {
                    if id.contains("armor") {
                        "chest"
                    } else {
                        "hands"
                    }
                },
                |(slot, _)| slot,
            );
            let before = ordinary.equipment.clone();
            assert!(
                ordinary
                    .equip_slots(&[(slot.into(), id.into())].into())
                    .is_err(),
                "{id} in {slot}"
            );
            assert_eq!(ordinary.equipment, before, "{id} changed the loadout");
        }
    }
    #[test]
    fn game_master_set_fills_every_slot_and_meets_the_defense_target() {
        let mut gm = character();
        gm.become_gm();
        for (slot, id) in GM_SLOTS {
            assert_eq!(
                gm.equipment.get(slot).map(String::as_str),
                Some(id),
                "{slot}"
            );
        }
        assert_eq!(gm.look.pants, "gm");
        assert_eq!(gm.look.necklace, "gm");
        assert_eq!(gm.look.accessory, "gm");
        assert_eq!(
            (gm.look.shoulders.as_str(), gm.look.gloves.as_str()),
            ("gm", "gm")
        );
        let piece_defense: f64 = GM_GEAR.iter().map(|id| item(id).unwrap().defense).sum();
        assert_eq!(piece_defense, 570_004.);
        assert!(gm.stats().1 >= 560_000., "{}", gm.stats().1);
        assert!(gm.look.validate().is_ok());
    }
    #[test]
    fn an_older_game_master_save_receives_the_new_golden_pieces_once() {
        let mut gm = character();
        gm.gm = true;
        for id in &GM_GEAR[..3] {
            gm.add_item(id, 1);
        }
        let _ = gm.look.equip("gm", "gm");
        gm.equipment
            .insert("headgear".into(), "warrior_headgear_gm".into());
        gm.grant_missing_gm_gear();
        for id in GM_GEAR {
            assert_eq!(gm.quantity(id), 1, "{id}");
        }
        assert_eq!(gm.equipment.len(), 6);
        // A piece taken off on purpose is not worn again on the next load.
        gm.equipment.remove("gloves");
        gm.grant_missing_gm_gear();
        assert!(!gm.equipment.contains_key("gloves"));
        assert_eq!(gm.quantity("warrior_gloves_gm"), 1);
        // An ordinary character is never granted the set.
        let mut other = character();
        other.grant_missing_gm_gear();
        assert!(GM_GEAR.iter().all(|id| other.quantity(id) == 0));
        // Another player can neither wear the new pieces nor show their art.
        other.add_item("gm_pants", 1);
        assert!(
            other
                .equip_slots(&[("pants".into(), "gm_pants".into())].into())
                .is_err()
        );
    }
    #[test]
    fn potions_and_food_have_a_stronger_tier_every_ten_levels() {
        for family in ["health_potion", "mana_potion", "traveler_stew"] {
            let tiers: Vec<_> = ITEMS
                .iter()
                .filter(|i| i.family.as_deref() == Some(family))
                .collect();
            assert_eq!(tiers.len(), 12, "{family}");
            let levels: Vec<u32> = tiers.iter().map(|i| i.required_level).collect();
            assert_eq!(
                levels,
                [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99],
                "{family}"
            );
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
            "traveler_stew_l99"
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
    fn outdoor_elites_roll_green_blue_and_purple_independently() {
        assert_eq!(outdoor_elite_drop_chance("uncommon"), 1.);
        assert_eq!(outdoor_elite_drop_chance("rare"), 0.33);
        assert_eq!(outdoor_elite_drop_chance("epic"), 0.05);
        assert_eq!(outdoor_elite_drop_chance("common"), 0.10);
        assert_eq!(outdoor_elite_drop_chance("legendary"), 0.0005);
        for rarity in ["uncommon", "rare", "epic"] {
            for level in [5, 10, 20, 30, 40, 45] {
                let gear = equipment_of_rarity(rarity, level, 0.5).unwrap();
                assert_eq!(gear.rarity, rarity);
                assert!(gear.required_level <= max_drop_level(level));
                assert!(gear.source.is_none());
            }
        }
    }
    #[test]
    fn level_twenty_to_forty_five_enemies_can_roll_the_next_gear_step_through_fifty() {
        for (enemy_level, top) in [(20, 25), (25, 30), (30, 35), (35, 40), (40, 45), (45, 50)] {
            assert_eq!(max_drop_level(enemy_level), top);
            for rarity in ["uncommon", "rare", "epic"] {
                let pool: Vec<_> = ITEMS
                    .iter()
                    .filter(|i| {
                        i.rarity == rarity
                            && is_gear(i)
                            && !i.starter
                            && i.source.is_none()
                            && i.required_level <= top
                    })
                    .collect();
                assert!(!pool.is_empty());
                let highest = (0..pool.len())
                    .filter_map(|n| {
                        equipment_of_rarity(
                            rarity,
                            enemy_level,
                            (n as f64 + 0.5) / pool.len() as f64,
                        )
                    })
                    .map(|i| i.required_level)
                    .max()
                    .unwrap();
                let expected = if rarity == "epic" { top / 10 * 10 } else { top };
                assert_eq!(
                    highest, expected,
                    "level {enemy_level} {rarity} drops level {expected} gear"
                );
            }
        }
    }
    #[test]
    fn every_instance_finale_has_two_guaranteed_blue_pools() {
        for kind in ["hollowking", "choirmother", "coralregent", "hierophant"] {
            let slots = boss_slots(kind);
            assert!(slots.len() >= 2, "{kind} needs two guaranteed gear rolls");
            for pool in slots {
                for choice in [0., 0.5, 0.999] {
                    let gear = boss_piece_for(kind, pool, choice).unwrap();
                    assert_eq!(gear.rarity, "rare", "{kind}: blue gear");
                    assert!(is_gear(gear));
                }
            }
        }
    }
    #[test]
    fn instance_elites_keep_the_original_five_times_single_roll_table() {
        // The width of a tier's band is its chance. The instance-elite table is 5x the ordinary width.
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
        // Orange gear has its own independent roll, never the ordinary level-capped pool.
        let roll = roll_for("big", "legendary");
        assert!(roll_equipment("big", 6, roll, 0.).is_none());
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
        for level in std::iter::once(1).chain((5..=60).step_by(5)) {
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
                // Original fitted sets name dedicated atlases rather than an item variant.
                if art.starts_with("regear") || art == "fatewoven" {
                    let slot = if i.kind == "headgear" {
                        "head"
                    } else {
                        &i.kind
                    };
                    let key = format!("\"{slot}_{art}\"");
                    assert!(
                        include_str!("../../client/assets/mage_f_sprites.txt").contains(&key),
                        "{} names a missing progression atlas {key}",
                        i.id
                    );
                    continue;
                }
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
        // Walk every level-50+ ordinary drop-pool cell. Source and obsolete gear must never leak in.
        for rarity in ["common", "uncommon", "rare", "epic"] {
            let eligible: std::collections::BTreeSet<_> = ITEMS
                .iter()
                .filter(|i| {
                    is_gear(i)
                        && i.rarity == rarity
                        && !i.starter
                        && i.source.is_none()
                        && (50..=55).contains(&i.required_level)
                })
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
    fn late_zone_drop_pools_reach_level_seventy_five_gear() {
        for rarity in ["common", "uncommon", "rare", "epic"] {
            let pool: Vec<_> = ITEMS
                .iter()
                .filter(|i| {
                    is_gear(i)
                        && i.rarity == rarity
                        && !i.starter
                        && i.source.is_none()
                        && (55..=95).contains(&i.required_level)
                })
                .collect();
            assert!(!pool.is_empty(), "{rarity} has level 55–95 gear");
            for enemy_level in [55, 58, 60, 62, 65, 67, 70] {
                let drops: std::collections::BTreeSet<_> = (0..pool.len())
                    .map(|n| {
                        equipment_of_rarity(
                            rarity,
                            enemy_level,
                            (n as f64 + 0.5) / pool.len() as f64,
                        )
                        .unwrap()
                        .id
                        .as_str()
                    })
                    .collect();
                let expected: std::collections::BTreeSet<_> = pool
                    .iter()
                    .filter(|i| {
                        i.required_level <= max_drop_level(enemy_level)
                            && i.required_level
                                >= if enemy_level >= 70 {
                                    70
                                } else if enemy_level >= 65 {
                                    65
                                } else {
                                    55
                                }
                    })
                    .map(|i| i.id.as_str())
                    .collect();
                assert_eq!(drops, expected, "{rarity} at enemy level {enemy_level}");
            }
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
                (equipped.0
                    - naked.0
                    - (i.attack + attribute_attack(&i.bonus_stats, c.look.class))
                        * player_attack_scale(c.look.class, c.level))
                .abs()
                    < 1e-8,
                "{} attack",
                i.id
            );
            assert!(
                (equipped.1 - naked.1 - i.defense - i.bonus_stats.strength as f64 * 0.2).abs()
                    < 1e-8,
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
            // The exclusive Foundry set is an intentional level-99 capstone, not ordinary ladder gear.
            if i.source.as_deref() == Some("blackhour") {
                assert_eq!(i.required_level, 99);
                assert_eq!(i.rarity, "epic");
                continue;
            }
            if matches!(i.kind.as_str(), "material" | "bag" | "food" | "potion") {
                // Bags and consumables come in ten-level tiers (plus the 95 and 99 consumable tiers); materials have no level.
                let tier = (i.kind == "bag" || i.family.is_some())
                    && (i.required_level == 1
                        || i.required_level % 10 == 0
                        || matches!(i.required_level, 95 | 99));
                assert!(tier || i.required_level == 1, "{} is not gear", i.id);
                continue;
            }
            assert!(
                i.required_level == 1 || (i.required_level <= 95 && i.required_level % 5 == 0),
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
                .chain((5..=95).step_by(5))
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
        assert!(
            (c.stats().0
                - base15.0
                - (-4. + royal.attack + attribute_attack(&royal.bonus_stats, c.look.class))
                    * player_attack_scale(c.look.class, c.level))
            .abs()
                < 1e-9,
            "sword out, royal in"
        );
        assert_eq!(
            c.stats().1,
            base15.1 + royal.defense + royal.bonus_stats.strength as f64 * 0.2,
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
            (
                base.0 - 4. * player_attack_scale(c.look.class, c.level),
                base.1,
            ),
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
            28,
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
        for i in ITEMS.iter().filter(|i| {
            (i.attack > 0. || i.defense > 0.)
                && i.rarity != GM_RARITY
                && i.source.as_deref() != Some("orange_pool")
        }) {
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
        c.level = item("warrior_weapon_royal").unwrap().required_level.max(10);
        c.equip_slots(&[("hands".into(), "warrior_weapon_royal".into())].into())
            .unwrap();
        assert_eq!(c.bag_used(), 16);
        assert!(
            c.equip_slots(&[("hands".into(), "none".into())].into())
                .is_err()
        );
        c.gold = 1500;
        c.purchase_bag("adventurer_satchel").unwrap();
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
        c.gold = 100_000;
        assert_eq!(
            c.purchase_bag("adventurer_satchel"),
            Err("Your level is too low for this bag.")
        );
        assert_eq!(c.gold, 100_000);
        c.level = 50;
        assert!(c.purchase_bag("slime_gel").is_err());
        for _ in 0..4 {
            c.purchase_bag("adventurer_satchel").unwrap();
        }
        assert_eq!(c.bag_capacity(), 48);
        let gold = c.gold;
        assert!(c.purchase_bag("adventurer_satchel").is_err());
        assert_eq!(c.gold, gold);
        c.purchase_bag("traveler_pack").unwrap();
        assert_eq!(c.bag_capacity(), 56);
        assert_eq!(c.bags.len(), 4);
        c.hp = 0.;
        assert!(c.purchase_bag("traveler_pack").is_err());
        assert_eq!(c.bag_capacity(), 56);
    }
    #[test]
    fn bag_tiers_and_drop_bands_match_catalog_prices() {
        let tiers = [
            (1, "linen_satchel", 6, 500),
            (10, "adventurer_satchel", 8, 1_500),
            (20, "trail_pack_l20", 10, 4_000),
            (30, "ranger_pack_l30", 12, 9_000),
            (40, "expedition_pack_l40", 14, 18_000),
            (50, "traveler_pack", 16, 35_000),
            (60, "pathfinder_pack_l60", 18, 60_000),
            (70, "warden_pack_l70", 20, 100_000),
            (80, "hero_pack_l80", 22, 160_000),
            (90, "sovereign_pack_l90", 24, 240_000),
        ];
        assert_eq!(
            ITEMS.iter().filter(|i| i.kind == "bag").count(),
            tiers.len()
        );
        for (level, id, slots, price) in tiers {
            let bag = item(id).unwrap();
            assert_eq!(
                (bag.required_level, bag.bag_slots, bag.price, bag.sell),
                (level, slots, price, price)
            );
            assert_eq!(roll_bag(level, 0.).unwrap().id, id);
            assert_eq!(
                roll_bag(if level == 1 { 9 } else { level + 9 }, 0.)
                    .unwrap()
                    .id,
                id
            );
        }
        assert!(roll_bag(34, BAG_DROP_CHANCE).is_none());
        assert!(roll_bag(34, BAG_DROP_CHANCE - f64::EPSILON).is_some());
        assert_eq!(roll_bag(34, 0.).unwrap().id, "ranger_pack_l30");
        assert!(roll_bag(0, 0.).is_none());
    }
    #[test]
    fn bag_purchase_checks_level_gold_and_existing_fitted_capacity() {
        let mut c = character();
        c.gold = 1_499;
        c.level = 10;
        assert_eq!(
            c.purchase_bag("adventurer_satchel"),
            Err("You need more gold for this bag.")
        );
        assert_eq!((c.gold, c.bag_capacity()), (1_499, 16));
        c.gold = 1_500;
        assert_eq!(c.purchase_bag("adventurer_satchel"), Ok(24));
        assert_eq!(c.gold, 0);
        c.level = 1; // A level loss does not take away a fitted legacy or earned bag.
        assert_eq!(c.bag_capacity(), 24);
        assert_eq!(
            c.can_fit_bag("adventurer_satchel"),
            Err("Your level is too low for this bag.")
        );
        assert!(c.can_collect("linen_satchel"));
        assert!(!c.can_collect("adventurer_satchel"));
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
        let passive = crate::skills::passive_bonus(c.look.class, c.level);
        let passive_attack =
            passive.strength as f64 * 2. + (passive.agility + passive.intellect) as f64 * 0.5;
        let passive_defense = passive.strength as f64 * 0.2;
        let (attack, defense) = c.stats();
        assert!(
            (attack
                - (22. + 80. + 4. + passive_attack + head.attack + 2. * ring.attack)
                    * player_attack_scale(c.look.class, c.level))
            .abs()
                < 1e-9
        );
        assert!((defense - (3. + passive_defense + head.defense + 2. * ring.defense)).abs() < 1e-9);
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
                (106. + passive_attack + head.attack + ring.attack)
                    * player_attack_scale(c.look.class, c.level),
                3. + passive_defense + head.defense + ring.defense,
            ),
        );
        c.equip_slots(&request(&[("chest", "none"), ("hands", "none")]))
            .unwrap();
        close(
            c.stats(),
            (
                (102. + passive_attack + head.attack + ring.attack)
                    * player_attack_scale(c.look.class, c.level),
                passive_defense + head.defense + ring.defense,
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
        // An older save (no list of given pieces) without the new pieces gets them on load, one each.
        h.starters_granted.clear();
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
