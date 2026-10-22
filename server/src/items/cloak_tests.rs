use super::*;
use crate::model::{Gender, Look, Point};
use crate::store::Store;
use std::collections::BTreeMap;

const CLASSES: [Class; 5] = [
    Class::Warrior,
    Class::Mage,
    Class::Assassin,
    Class::Priest,
    Class::Hunter,
];
fn hero(class: Class, gender: Gender, level: u32) -> Character {
    let mut c = Store::open(std::path::Path::new(":memory:"))
        .unwrap()
        .create(
            Look {
                class,
                gender,
                ..Look::default()
            },
            Point::default(),
        )
        .unwrap()
        .0;
    c.level = level;
    c.hp = c.max_hp();
    c
}
fn slot(id: &str) -> BTreeMap<String, String> {
    BTreeMap::from([("cloak".into(), id.into())])
}

#[test]
fn cloak_catalog_ladder_and_all_ten_bodies_equip_only_the_cloak_slot() {
    let cloaks: Vec<_> = ITEMS.iter().filter(|i| i.kind == "cloak").collect();
    assert_eq!(cloaks.len(), 100);
    assert!(EXTRA_SLOTS.contains(&"cloak"));
    assert!(
        cloaks
            .iter()
            .all(|i| i.class.is_none() && !i.starter && i.attack == 0. && i.defense == 0.)
    );
    for level in (5..=95).step_by(5).chain([99]) {
        for rarity in ["common", "uncommon", "rare", "epic", "legendary"] {
            let expected = match rarity {
                "epic" | "legendary" => level % 10 == 0 || level == 99,
                _ => true,
            };
            assert_eq!(
                cloaks.iter().any(|i| i.required_level == level
                    && i.rarity == rarity
                    && (i.source.is_none() || i.source.as_deref() == Some("orange_pool"))),
                expected,
                "{level}/{rarity}"
            );
        }
    }
    for class in CLASSES {
        for gender in [Gender::Male, Gender::Female] {
            for piece in &cloaks {
                let mut c = hero(class, gender, piece.required_level);
                c.add_item(&piece.id, 1);
                c.equip_slots(&slot(&piece.id)).unwrap();
                assert_eq!(c.look.cloak, *piece.variant.as_ref().unwrap());
                assert_eq!(c.equipped_count(piece), 1);
                assert_eq!(c.gear_attributes(), piece.bonus_stats);
                assert!(c.set_counts().is_empty(), "cloaks never count toward sets");
                assert!(c.look.validate().is_ok());
                assert!(
                    c.equip_slots(&BTreeMap::from([("necklace".into(), piece.id.clone())]))
                        .is_err()
                );
                c.equip_slots(&slot("none")).unwrap();
                assert_eq!(c.look.cloak, "none");
                assert_eq!(c.gear_attributes(), Default::default());
            }
            let mut c = hero(class, gender, 4);
            c.add_item("cloak_l5_common", 1);
            assert!(c.equip_slots(&slot("cloak_l5_common")).is_err());
            c.add_item("necklace_upgrade", 1);
            assert!(c.equip_slots(&slot("necklace_upgrade")).is_err());
        }
    }
}

#[test]
fn cloak_stats_count_once_save_roundtrips_and_old_saves_default_to_none() {
    let mut c = hero(Class::Mage, Gender::Female, 50);
    let mut old = serde_json::to_value(&c).unwrap();
    old["look"].as_object_mut().unwrap().remove("cloak");
    old.as_object_mut().unwrap().remove("equipment");
    let mut loaded: Character = serde_json::from_value(old).unwrap();
    loaded.sync_look();
    assert_eq!(loaded.look.cloak, "none");
    assert!(loaded.equipment.is_empty());
    c.add_item("cloak_l50_uncommon", 2);
    let base = c.max_hp();
    assert!(c.is_upgrade(item("cloak_l50_uncommon").unwrap()));
    c.equip_slots(&slot("cloak_l50_uncommon")).unwrap();
    assert!(c.max_hp() > base);
    let worn = c.max_hp();
    c.sync_look();
    assert_eq!(c.max_hp(), worn);
    let mut saved: Character = serde_json::from_slice(&serde_json::to_vec(&c).unwrap()).unwrap();
    saved.sync_look();
    assert_eq!(saved.look.cloak, c.look.cloak);
    assert_eq!(saved.max_hp(), worn);
    assert!(!saved.is_upgrade(item("cloak_l5_uncommon").unwrap()));
    saved.equip_slots(&slot("none")).unwrap();
    assert_eq!(saved.max_hp(), base);
    let fresh = hero(Class::Warrior, Gender::Male, 1);
    assert_eq!(fresh.look.cloak, "none");
    assert!(
        fresh
            .inventory
            .iter()
            .all(|s| item(&s.item).unwrap().kind != "cloak")
    );
}

#[test]
fn cloak_mercenaries_and_sources_use_the_tenth_slot() {
    for class in CLASSES {
        for level in [1, 4, 5, 10, 55, 95, 99] {
            let c = Character::mercenary(class, level, "Cloak hire");
            assert_eq!(c.equipment.contains_key("cloak"), level >= 5);
            if level >= 5 {
                let i = item(&c.equipment["cloak"]).unwrap();
                assert_eq!(i.required_level, if level == 99 { 99 } else { level });
            }
        }
    }
    for piece in ITEMS
        .iter()
        .filter(|i| i.kind == "cloak" && i.source.as_deref().is_some_and(|s| s != "orange_pool"))
    {
        let source = piece.source.as_deref().unwrap();
        let mut found = false;
        // Every catalogue boss that owns this source can select its cloak from an authored pool.
        for e in crate::cathedral::ENEMIES
            .iter()
            .filter(|e| e.boss && e.loot_source.as_deref() == Some(source))
        {
            for pool in boss_slots(&e.kind) {
                if !pool.contains(&"cloak") {
                    continue;
                }
                found |= boss_piece_for(&e.kind, pool, 1. - f64::EPSILON)
                    .is_some_and(|i| i.id == piece.id);
            }
        }
        if source == "undervault" {
            found = boss_piece(&["cloak"], 0.).is_some_and(|i| i.id == piece.id);
        }
        if source == "moonwell" {
            found =
                boss_piece_for("moonwell_echo", &["cloak"], 0.).is_some_and(|i| i.id == piece.id);
        }
        assert!(found, "{source}: missing boss cloak");
    }
}

#[test]
fn cloak_instances_merge_refine_and_bank_without_losing_their_stats() {
    let mut c = hero(Class::Priest, Gender::Female, 99);
    c.add_item("cloak_l50_rare", 2);
    c.materialize_gear_instances();
    let copies: Vec<_> = c
        .gear_instances
        .iter()
        .filter(|g| g.item == "cloak_l50_rare")
        .map(|g| g.id)
        .collect();
    assert_eq!(copies.len(), 2);
    let merged = c.merge_gear(copies[0], copies[1]).unwrap();
    assert_eq!(merged.rarity, "epic");
    assert_eq!(merged.attack, 0.);
    assert_eq!(merged.defense, 0.);
    c.gold = 1_000_000;
    c.add_item("refinement_crystal_epic", 5);
    let (refined, _, _) = c.refine_gear(merged.id).unwrap();
    assert_eq!(refined.rank, 1);
    c.equip_slots(&slot("cloak_l50_rare")).unwrap();
    assert_eq!(c.gear_attributes(), refined.effective_bonus_stats());
    c.equip_slots(&slot("none")).unwrap();
    c.bank_deposit("cloak_l50_rare", 1, Some(refined.id))
        .unwrap();
    assert_eq!(
        c.bank.gear[0].effective_bonus_stats(),
        refined.effective_bonus_stats()
    );
    c.bank_withdraw("cloak_l50_rare", 1, Some(refined.id))
        .unwrap();
    let withdrawn = c
        .gear_instances
        .iter()
        .find(|g| g.item == "cloak_l50_rare")
        .unwrap();
    let withdrawn_id = withdrawn.id;
    assert_eq!(
        withdrawn.effective_bonus_stats(),
        refined.effective_bonus_stats()
    );
    let saved: Character = serde_json::from_slice(&serde_json::to_vec(&c).unwrap()).unwrap();
    assert_eq!(
        saved
            .gear_instances
            .iter()
            .find(|g| g.id == withdrawn_id)
            .unwrap()
            .effective_bonus_stats(),
        refined.effective_bonus_stats()
    );
}
