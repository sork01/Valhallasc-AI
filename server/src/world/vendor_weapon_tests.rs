//! Decade green vendor weapons: stock, level/class boundaries, real purchases and refusals.
use super::wyrd_tests::world;
use super::*;
const CLASSES: [Class; 5] = [
    Class::Warrior,
    Class::Mage,
    Class::Assassin,
    Class::Priest,
    Class::Hunter,
];

fn family(class: Class) -> String {
    format!("vendor_weapon_{}", mercs::class_title(class).to_lowercase())
}
fn offer(class: Class) -> String {
    format!(
        "buy_green_weapon_{}",
        mercs::class_title(class).to_lowercase()
    )
}
fn fixture(class: Class) -> (World, mpsc::Receiver<Value>, String) {
    let mut w = world();
    let (tx, rx) = mpsc::channel(4096);
    let welcome = w
        .join(
            1,
            None,
            Some(Look {
                class,
                ..Look::default()
            }),
            tx,
        )
        .unwrap();
    let token = welcome["token"].as_str().unwrap().to_owned();
    let smith = &w.maps[0].npcs.iter().find(|n| n.id == "smith").unwrap();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.x = smith.x;
    c.y = smith.y;
    c.gold = 1_000_000;
    (w, rx, token)
}
fn buy(w: &mut World, rx: &mut mpsc::Receiver<Value>, class: Class) -> String {
    while rx.try_recv().is_ok() {}
    w.time += 1.;
    w.interact(1, "smith", Some(&offer(class)));
    std::iter::from_fn(|| rx.try_recv().ok())
        .filter(|v| v["type"] == "dialogue")
        .last()
        .unwrap()["notice"]
        .as_str()
        .unwrap()
        .to_owned()
}

#[test]
fn vendor_weapon_catalog_has_all_five_classes_at_each_decade_and_scaled_prices() {
    for class in CLASSES {
        let f = family(class);
        assert!(best_tier(&f, 9).is_none());
        for level in 10..=99 {
            let item = best_tier(&f, level).unwrap();
            let step = (level / 10 * 10).min(90);
            assert_eq!(item.required_level, step);
            assert_eq!(item.price, 10 * step * step);
            assert!(item.price > item.sell);
            assert_eq!(item.class, Some(class));
            assert_eq!(
                (item.kind.as_str(), item.rarity.as_str()),
                ("weapon", "uncommon")
            );
            assert!(item.source.is_none());
        }
    }
}

#[test]
fn vendor_weapon_stock_is_available_at_merchants_and_armorers_only() {
    let w = world();
    let mut vendors = 0;
    for npc in w.maps.iter().flat_map(|m| &m.npcs) {
        let eligible = npc.buys || npc.role == "Armorer";
        let stock: Vec<_> = npc
            .offers
            .iter()
            .filter(|o| o.id.starts_with("buy_green_weapon_"))
            .collect();
        assert_eq!(stock.len(), if eligible { 5 } else { 0 }, "{}", npc.id);
        if !eligible {
            continue;
        }
        vendors += 1;
        for class in CLASSES {
            let o = stock.iter().find(|o| o.id == offer(class)).unwrap();
            assert!(o.tiered);
            assert_eq!(
                o.item.as_deref(),
                Some(best_tier(&family(class), 10).unwrap().id.as_str())
            );
            assert_eq!(o.cost, 1000);
        }
    }
    assert!(vendors >= 28);
}

#[test]
fn vendor_weapon_real_purchases_charge_each_tier_and_save_the_exact_piece() {
    for class in CLASSES {
        let (mut w, mut rx, token) = fixture(class);
        for level in (10..=90).step_by(10) {
            w.players.get_mut(&1).unwrap().character.level = level;
            let stock = best_tier(&family(class), level).unwrap();
            let gold = w.players[&1].character.gold;
            let text = buy(&mut w, &mut rx, class);
            assert_eq!(text, format!("Bought {}.", stock.name));
            let c = &w.players[&1].character;
            assert_eq!(c.gold, gold - stock.price);
            assert_eq!(c.quantity(&stock.id), 1);
            let saved = w.store.load(&token).unwrap().unwrap();
            assert_eq!(saved.gold, c.gold);
            assert_eq!(saved.quantity(&stock.id), 1);
        }
    }
}

#[test]
fn vendor_weapon_refuses_wrong_class_low_level_funds_remote_and_full_bag_without_charge() {
    let (mut w, mut rx, _) = fixture(Class::Warrior);
    let id = best_tier(&family(Class::Warrior), 10).unwrap().id.clone();
    w.players.get_mut(&1).unwrap().character.level = 9;
    assert_eq!(buy(&mut w, &mut rx, Class::Warrior), "Requires level 10.");
    assert_eq!(w.players[&1].character.gold, 1_000_000);
    w.players.get_mut(&1).unwrap().character.level = 10;
    assert_eq!(
        buy(&mut w, &mut rx, Class::Hunter),
        "This weapon is for another class."
    );
    assert_eq!(w.players[&1].character.gold, 1_000_000);
    w.players.get_mut(&1).unwrap().character.gold = 999;
    assert!(buy(&mut w, &mut rx, Class::Warrior).contains("1000 gold"));
    assert_eq!(w.players[&1].character.gold, 999);
    assert_eq!(w.players[&1].character.quantity(&id), 0);
    let p = &mut w.players.get_mut(&1).unwrap().character;
    p.gold = 1_000_000;
    for material in ITEMS.iter().filter(|i| i.kind == "material") {
        if p.bag_used() == p.bag_capacity() {
            break;
        }
        p.add_item(&material.id, 1);
    }
    assert_eq!(p.bag_used(), p.bag_capacity());
    assert!(!p.can_collect(&id));
    let quantity = p.quantity(&id);
    assert!(buy(&mut w, &mut rx, Class::Warrior).contains("bags are full"));
    assert_eq!(w.players[&1].character.gold, 1_000_000);
    assert_eq!(w.players[&1].character.quantity(&id), quantity);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.inventory.pop();
    assert!(
        c.can_collect(&id),
        "remote refusal must not be masked by a full bag"
    );
    c.x += 50.;
    w.time += 1.;
    w.interact(1, "smith", Some(&offer(Class::Warrior)));
    assert_eq!(w.players[&1].character.gold, 1_000_000);
    assert_eq!(w.players[&1].character.quantity(&id), quantity);
}
