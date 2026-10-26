//! Raid-only Hierloom gear: attributes follow the wearer, never the saved copy.
use super::{GearInstance, Item, item, raid_rewards};
use crate::model::{Attributes, Character};

pub const RARITY: &str = "hierloom";
pub const PIECES: [&str; 4] = [
    "hierloom_dawn_ring",
    "hierloom_ember_ring",
    "hierloom_necklace",
    "hierloom_cloak",
];
pub const DROP_CHANCE: f64 = 0.10;

pub fn is_hierloom(piece: &Item) -> bool {
    piece.rarity == RARITY
}

/// Catalog attributes are the per-level budget, shared by all five classes.
/// Only the wearer's level matters, including immediately after rebirth/trade.
pub fn attributes(piece: &Item, level: u32) -> Option<Attributes> {
    is_hierloom(piece).then(|| {
        let base = &piece.bonus_stats;
        let level = level.max(1);
        Attributes {
            strength: base.strength.saturating_mul(level),
            agility: base.agility.saturating_mul(level),
            intellect: base.intellect.saturating_mul(level),
            stamina: base.stamina.saturating_mul(level),
            dexterity: base.dexterity.saturating_mul(level),
            accuracy: base.accuracy.saturating_mul(level),
        }
    })
}

impl Character {
    /// Only usable, equipped pieces grant XP. Stored and banked pieces grant none.
    /// This stacks additively with rebirth XP, so four pieces add 400 percentage points.
    pub fn hierloom_xp_percent(&self) -> u32 {
        self.worn_items()
            .into_iter()
            .filter(|i| is_hierloom(i) && i.required_level <= self.level)
            .count() as u32
            * 100
    }
}

/// Extra roll alongside the existing orange rewards, using the ordinary rebirth
/// drop multiplier. Select each of the four items with equal probability.
pub fn drops(kind: &str, multiplier: u32, mut random: impl FnMut() -> f64) -> Vec<GearInstance> {
    if raid_rewards::boss(kind).is_none() {
        return vec![];
    }
    let count = crate::perks::copies(DROP_CHANCE, multiplier, &mut random);
    (0..count)
        .map(|_| {
            let at = (random().clamp(0., 1. - f64::EPSILON) * PIECES.len() as f64) as usize;
            GearInstance::new(0, item(PIECES[at]).expect("hierloom catalog piece"))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Class, Point};
    use std::collections::BTreeMap;

    fn equipped(level: u32) -> Character {
        let mut c = Character::mercenary(Class::Warrior, level, "Hierloom Test");
        for id in PIECES {
            c.add_item(id, 1);
        }
        c.equip_slots(&BTreeMap::from([
            ("accessory1".into(), PIECES[0].into()),
            ("accessory2".into(), PIECES[1].into()),
            ("necklace".into(), PIECES[2].into()),
            ("cloak".into(), PIECES[3].into()),
        ]))
        .unwrap();
        c
    }

    #[test]
    fn hierloom_catalog_is_usable_by_every_class_and_never_world_drops() {
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let mut c = equipped(1);
            c.look.class = class;
            c.sync_look();
            c.look.validate().unwrap();
            assert_eq!(c.hierloom_xp_percent(), 400);
            assert!(c.set_counts().is_empty());
        }
        for id in PIECES {
            let it = item(id).unwrap();
            assert_eq!(it.rarity, RARITY);
            assert_eq!(it.required_level, 1);
            assert_eq!(it.source.as_deref(), Some("raid_hierlooms"));
            assert!(it.class.is_none());
            assert!(super::super::equipment_of_rarity(RARITY, 99, 0.).is_none());
        }
    }

    #[test]
    fn hierloom_xp_counts_only_equipped_slots_and_stacks_with_rebirth() {
        let mut c = equipped(50);
        assert_eq!(c.boosted_xp(100), 500);
        assert_eq!(c.boosted_xp(0), 0);
        assert_eq!(c.boosted_xp(u32::MAX), u32::MAX);
        c.rebirth_tiers = [5, 0, 0, 0, 0];
        assert_eq!(c.boosted_xp(100), 550);
        c.add_item(PIECES[0], 10);
        assert_eq!(c.boosted_xp(100), 550, "spare copies grant no bonus");
        c.equipment.clear();
        assert_eq!(c.boosted_xp(100), 150);
        for (n, (slot, id)) in [
            ("accessory1", PIECES[0]),
            ("accessory2", PIECES[1]),
            ("necklace", PIECES[2]),
            ("cloak", PIECES[3]),
        ]
        .into_iter()
        .enumerate()
        {
            c.equip_slots(&BTreeMap::from([(slot.into(), id.into())]))
                .unwrap();
            assert_eq!(c.boosted_xp(100), 150 + 100 * (n as u32 + 1));
        }
    }

    #[test]
    fn hierloom_stats_follow_level_and_rebirth_without_rewriting_saved_copies() {
        let mut c = equipped(1);
        let copy = c.gear_instances.clone();
        let low = c.gear_attributes();
        assert_eq!(
            (low.strength, low.agility, low.intellect, low.stamina),
            (4, 4, 4, 8)
        );
        c.level = 99;
        let high = c.gear_attributes();
        assert_eq!((high.strength, high.stamina), (396, 792));
        assert_eq!(c.gear_instances, copy);
        c.rebirth(Point { x: 31., y: 88. }).unwrap();
        assert_eq!(c.level, 1);
        assert_eq!(c.equipment.len(), 4);
        assert_eq!(c.gear_attributes(), low);
        assert_eq!(c.boosted_xp(100), 510);
        let loaded: Character = serde_json::from_value(serde_json::to_value(c).unwrap()).unwrap();
        assert_eq!(loaded.gear_attributes(), low);
    }

    #[test]
    fn hierloom_deaths_never_wear_or_break_or_require_repairs() {
        let mut c = equipped(99);
        let before = c.gear_attributes();
        for _ in 0..12 {
            assert_eq!(c.wear_worn_gear(), super::super::DeathWear::default());
        }
        assert!(c.gear_instances.iter().all(|g| g.wear == 0));
        // Even a malformed historical copy cannot turn an indestructible piece off.
        let at = c
            .gear_instances
            .iter()
            .position(|g| g.item == PIECES[0])
            .unwrap();
        c.gear_instances[at].wear = 100;
        assert!(!c.gear_instances[at].broken());
        assert_eq!(c.repair_price(&c.gear_instances[at]), 0);
        assert!(c.repair_quote(4).is_empty());
        assert_eq!(c.gear_attributes(), before);
        assert_eq!(c.boosted_xp(100), 500);
    }

    #[test]
    fn hierloom_all_ten_bosses_have_exact_ten_percent_boundary_and_four_choices() {
        let rules: serde_json::Value =
            serde_json::from_str(include_str!("../../../world/raid-rewards.txt")).unwrap();
        assert_eq!(rules["bosses"].as_array().unwrap().len(), 10);
        for boss in rules["bosses"].as_array().unwrap() {
            let kind = boss["kind"].as_str().unwrap();
            assert!(drops(kind, 1, || 0.10).is_empty());
            assert!(drops(kind, 1, || 0.999).is_empty());
            for (at, id) in PIECES.iter().enumerate() {
                let mut values = [0.10 - f64::EPSILON, (at as f64 + 0.5) / 4.].into_iter();
                let result = drops(kind, 1, || values.next().unwrap());
                assert_eq!(result.len(), 1);
                assert_eq!(result[0].item, *id);
                assert_eq!(result[0].rarity, RARITY);
            }
            assert!(drops(kind, 5, || 0.50).is_empty());
            assert_eq!(drops(kind, 5, || 0.50 - f64::EPSILON).len(), 1);
        }
        for kind in ["slime", "king", "cf_chainbound", "cinderlord"] {
            assert!(drops(kind, 1, || panic!("non-raid boss must not roll")).is_empty());
        }
    }
}
