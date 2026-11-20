use super::*;
use crate::items::{ITEMS, ItemStack};

fn hero() -> Character {
    let mut c = Character::mercenary(Class::Warrior, 30, "Wardrobe");
    c.gold = 1_000_000;
    c.bags = vec!["traveler_pack".into(); 4];
    c
}
fn piece(class: Class, slot: &str, level: u32) -> &'static Item {
    ITEMS
        .iter()
        .find(|i| {
            i.kind == kind(slot)
                && i.class.is_none_or(|k| k == class)
                && i.required_level >= level
                && i.rarity == "uncommon"
                && i.variant.is_some()
        })
        .unwrap()
}
fn selection(slot: &str, id: &str) -> BTreeMap<String, String> {
    BTreeMap::from([(slot.into(), id.into())])
}

#[test]
fn transmog_class_neutral_weapon_is_usable_without_level_or_ownership_after_unlock() {
    let mut c = hero();
    c.level = 1;
    let neutral = ITEMS
        .iter()
        .find(|i| i.class.is_none() && i.kind == "weapon" && i.variant.is_some())
        .unwrap();
    c.add_item(&neutral.id, 1);
    c.consume_item(&neutral.id, 1);
    let stats = c.stats();
    let actual = c.look.warrior_weapon.clone();
    c.apply_transmogs(&selection("hands", &neutral.id)).unwrap();
    assert_eq!(
        c.appearance_look().warrior_weapon,
        neutral.variant.as_deref().unwrap()
    );
    assert_eq!(c.look.warrior_weapon, actual);
    assert_eq!(c.stats(), stats);
    assert_eq!(c.quantity(&neutral.id), 0);
}

#[test]
fn transmog_unlock_is_permanent_unique_equipment_only_and_ignores_zero_grants() {
    let mut c = hero();
    c.wardrobe.unlocked.clear();
    let i = piece(Class::Warrior, "headgear", 50);
    c.add_item(&i.id, 0);
    assert!(!c.wardrobe.unlocked.contains(&i.id));
    c.add_item(&i.id, 1);
    c.add_item(&i.id, 1);
    assert_eq!(c.wardrobe.unlocked.len(), 1);
    c.consume_item(&i.id, 2);
    assert!(c.wardrobe.unlocked.contains(&i.id));
    for kind in ["material", "potion", "bag", "fish", "rod"] {
        let i = ITEMS.iter().find(|i| i.kind == kind).unwrap();
        c.add_item(&i.id, 1);
        assert!(!c.wardrobe.unlocked.contains(&i.id), "{kind}");
    }
    let other = hero();
    assert!(!other.wardrobe.unlocked.contains(&i.id));
}

#[test]
fn transmog_backfills_worn_bags_and_bank_once_and_survives_serialization() {
    let mut c = hero();
    let bag = piece(Class::Warrior, "headgear", 40);
    let bank = piece(Class::Warrior, "cloak", 50);
    c.inventory.push(ItemStack {
        item: bag.id.clone(),
        quantity: 1,
    });
    c.bank.items.push(ItemStack {
        item: bank.id.clone(),
        quantity: 1,
    });
    c.wardrobe = Wardrobe::default();
    let worn: Vec<_> = c.worn_slots().iter().map(|(_, i)| i.id.clone()).collect();
    let mut old = serde_json::to_value(&c).unwrap();
    old.as_object_mut().unwrap().remove("wardrobe");
    c = serde_json::from_value(old).unwrap();
    c.migrate_wardrobe();
    assert!(c.wardrobe.migrated);
    for id in worn.iter().chain([&bag.id, &bank.id]) {
        assert!(c.wardrobe.unlocked.contains(id), "{id}");
    }
    let chest_id = worn
        .iter()
        .find(|id| item(id).unwrap().kind == "armor")
        .unwrap();
    c.apply_transmogs(&selection("chest", chest_id)).unwrap();
    c.inventory.clear();
    c.bank.items.clear();
    let saved = serde_json::to_string(&c).unwrap();
    let mut loaded: Character = serde_json::from_str(&saved).unwrap();
    loaded.migrate_wardrobe();
    assert_eq!(loaded.wardrobe.unlocked, c.wardrobe.unlocked);
    assert_eq!(loaded.wardrobe.slots, c.wardrobe.slots);
    loaded.wardrobe.unlocked.remove(&bank.id);
    loaded.bank.items.push(ItemStack {
        item: bank.id.clone(),
        quantity: 1,
    });
    loaded.migrate_wardrobe();
    assert!(
        !loaded.wardrobe.unlocked.contains(&bank.id),
        "one-way migration does not run twice"
    );
}

#[test]
fn transmog_all_seven_slots_all_classes_preserve_actual_gear_stats_and_vitals() {
    for class in [
        Class::Warrior,
        Class::Mage,
        Class::Assassin,
        Class::Priest,
        Class::Hunter,
    ] {
        let mut c = Character::mercenary(class, 99, "Wardrobe");
        c.gold = 1_000_000;
        c.bags = vec!["traveler_pack".into(); 4];
        let mut choices = BTreeMap::new();
        for slot in SLOTS {
            let worn = piece(class, slot, 20);
            let appearance = piece(class, slot, 60);
            c.add_item(&worn.id, 1);
            c.add_item(&appearance.id, 1);
            c.equip_slots(&selection(slot, &worn.id)).unwrap();
            choices.insert(slot.into(), appearance.id.clone());
        }
        let before = serde_json::to_value(&c).unwrap();
        let (stats, attributes, hp, resource) =
            (c.stats(), c.gear_attributes(), c.hp, c.resource());
        assert_eq!(c.apply_transmogs(&choices), Ok(140_000));
        assert_eq!(c.active_transmogs().len(), 7);
        let look = serde_json::to_value(c.appearance_look()).unwrap();
        let class_name = serde_json::to_value(class)
            .unwrap()
            .as_str()
            .unwrap()
            .to_owned();
        for (slot, id) in choices {
            let field = match slot.as_str() {
                "chest" => format!("{class_name}Armor"),
                "hands" => format!("{class_name}Weapon"),
                "headgear" => "head".into(),
                _ => slot.clone(),
            };
            assert_eq!(
                look[field],
                item(&id).unwrap().variant.as_deref().unwrap(),
                "{class:?} {slot}"
            );
        }
        assert_eq!(serde_json::to_value(&c.look).unwrap(), before["look"]);
        assert_eq!(
            serde_json::to_value(&c.inventory).unwrap(),
            before["inventory"]
        );
        assert_eq!(
            serde_json::to_value(&c.equipment).unwrap(),
            before["equipment"]
        );
        assert_eq!(
            serde_json::to_value(c.gear_attributes()).unwrap(),
            serde_json::to_value(attributes).unwrap()
        );
        assert_eq!((c.stats(), c.hp, c.resource()), (stats, hp, resource));
    }
}

#[test]
fn transmog_persists_across_upgrade_unequip_and_low_level_rebirth() {
    let mut c = hero();
    let old = piece(Class::Warrior, "chest", 20);
    let upgrade = piece(Class::Warrior, "chest", 25);
    let cosmetic = piece(Class::Warrior, "chest", 95);
    for i in [old, upgrade, cosmetic] {
        c.add_item(&i.id, 1);
    }
    c.equip_slots(&selection("chest", &old.id)).unwrap();
    c.apply_transmogs(&selection("chest", &cosmetic.id))
        .unwrap();
    c.equip_slots(&selection("chest", &upgrade.id)).unwrap();
    assert_eq!(
        c.appearance_look().warrior_armor,
        cosmetic.variant.as_deref().unwrap()
    );
    c.equip_slots(&selection("chest", "none")).unwrap();
    assert_eq!(c.appearance_look().warrior_armor, "none");
    assert_eq!(c.wardrobe.slots["chest"], cosmetic.id);
    c.equip_slots(&selection("chest", &old.id)).unwrap();
    c.level = 50;
    let unlocked = c.wardrobe.unlocked.clone();
    c.rebirth(crate::model::Point { x: 10., y: 10. }).unwrap();
    assert_eq!(c.level, 1);
    assert_eq!(c.wardrobe.unlocked, unlocked);
    assert_eq!(c.wardrobe.slots["chest"], cosmetic.id);
    assert_eq!(
        c.appearance_look().warrior_armor,
        cosmetic.variant.as_deref().unwrap()
    );
}

#[test]
fn transmog_hide_and_empty_slots_and_free_revert() {
    let mut c = hero();
    for slot in HIDE_SLOTS {
        let i = piece(Class::Warrior, slot, 1);
        c.add_item(&i.id, 1);
        c.equip_slots(&selection(slot, &i.id)).unwrap();
        assert!(c.apply_transmogs(&selection(slot, "hide")).unwrap() > 0);
    }
    let look = c.appearance_look();
    assert_eq!(
        (&*look.head, &*look.shoulders, &*look.cloak),
        ("none", "none", "none")
    );
    c.gold = 0;
    let revert = HIDE_SLOTS
        .iter()
        .map(|s| (s.to_string(), "real".into()))
        .collect();
    assert_eq!(c.apply_transmogs(&revert), Ok(0));
    assert!(c.wardrobe.slots.is_empty());
    assert_ne!(c.appearance_look().head, "none");
    c.equip_slots(&selection("headgear", "none")).unwrap();
    c.gold = 10_000;
    c.apply_transmogs(&selection("headgear", "hide")).unwrap();
    assert!(!c.active_transmogs().contains_key("headgear"));
    assert_eq!(c.appearance_look().head, "none");
}

#[test]
fn transmog_guards_batch_atomically_and_scales_fees_with_free_noops() {
    let mut c = hero();
    let i = piece(Class::Warrior, "chest", 95);
    c.add_item(&i.id, 1);
    c.level = 1;
    assert_eq!(c.transmog_price(), 500);
    c.level = 99;
    assert_eq!(c.transmog_price(), 20_000);
    c.level = 50;
    assert_eq!(c.transmog_price(), 10_250);
    let before = serde_json::to_value(&c).unwrap();
    let foreign = piece(Class::Mage, "chest", 50);
    c.unlock_appearance(&foreign.id);
    let gm = ITEMS
        .iter()
        .find(|i| i.rarity == "gm" && i.kind == "armor")
        .unwrap();
    c.unlock_appearance(&gm.id);
    let locked = piece(Class::Warrior, "hands", 95);
    for (s, id) in [
        ("chest", foreign.id.as_str()),
        ("chest", gm.id.as_str()),
        ("hands", locked.id.as_str()),
        ("necklace", i.id.as_str()),
        ("chest", "hide"),
        ("gloves", "hide"),
        ("chest", "unknown"),
        ("hands", i.id.as_str()),
    ] {
        let mut batch = selection("headgear", "hide");
        batch.insert(s.into(), id.into());
        assert!(c.apply_transmogs(&batch).is_err(), "{s} {id}");
        assert_eq!(c.gold, before["gold"].as_u64().unwrap() as u32);
        assert!(c.wardrobe.slots.is_empty());
    }
    c.gold = c.transmog_price() - 1;
    assert!(c.apply_transmogs(&selection("chest", &i.id)).is_err());
    assert!(c.wardrobe.slots.is_empty());
    c.gold += 1;
    assert_eq!(
        c.apply_transmogs(&selection("chest", &i.id)),
        Ok(c.transmog_price())
    );
    assert_eq!(c.gold, 0);
    assert_eq!(c.apply_transmogs(&selection("chest", &i.id)), Ok(0));
    c.wardrobe.slots.insert("chest".into(), gm.id.clone());
    assert!(
        !c.active_transmogs().contains_key("chest"),
        "invalid saved GM override never renders"
    );
    assert_eq!(c.apply_transmogs(&selection("chest", "real")), Ok(0));
    c.gm = true;
    c.gold = 100_000;
    assert!(c.apply_transmogs(&selection("chest", &gm.id)).is_ok());
}
