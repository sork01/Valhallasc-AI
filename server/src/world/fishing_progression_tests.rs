use super::*;

fn at_pool(w: &mut World, zone: usize, rod: &str) {
    let kind = if zone == 1 {
        "lava"
    } else if zone == 45 {
        "ew_lava"
    } else {
        "water"
    };
    w.maps[zone].objects =
        vec![serde_json::from_value(json!({"kind":kind,"x":53.,"y":50.,"r":2.})).unwrap()];
    w.maps[zone].grid = Default::default();
    w.rich_fishing.clear();
    let p = w.players.get_mut(&1).unwrap();
    p.character.zone = zone;
    p.character.x = 50.;
    p.character.y = 50.;
    p.character.level = 99;
    p.character.inventory.clear();
    p.character.add_item(rod, 1);
    p.face = Point { x: 1., y: 0. };
}

#[test]
fn fishing_progression_all_waters_name_the_required_rod_and_reject_its_predecessor() {
    let (mut w, _rx) = super::super::fishing_tests::angler();
    // Explicit gameplay contract, independent of the catalogue's unlock lists.
    for (zone, tier) in [
        (0, 1),
        (1, 2),
        (2, 1),
        (3, 1),
        (6, 2),
        (19, 5),
        (20, 4),
        (22, 4),
        (25, 5),
        (26, 7),
        (28, 8),
        (45, 6),
        (7, 6),
        (13, 6),
        (14, 6),
        (15, 6),
        (16, 7),
        (17, 7),
        (21, 8),
        (23, 9),
        (24, 9),
        (27, 10),
    ] {
        let rod = RODS.iter().find(|r| r.tier == tier).unwrap();
        at_pool(&mut w, zone, &rod.item);
        assert!(w.fishing_line(1, 20., false).is_ok(), "tier {tier} in zone {zone}");
        let p = w.players.get_mut(&1).unwrap();
        p.character.inventory.clear();
        if tier > 1 {
            p.character
                .add_item(&RODS.iter().find(|r| r.tier == tier - 1).unwrap().item, 1);
        }
        let message = w
            .fishing_line(1, 20., false)
            .err()
            .expect("weaker rod must be rejected");
        assert!(
            message.contains(&item(&rod.item).unwrap().name),
            "{message}"
        );
        assert!(
            message.contains(&format!(
                "level {}",
                item(&rod.item).unwrap().required_level
            )),
            "{message}"
        );
    }
    for zone in [2, 3] {
        at_pool(&mut w, zone, "rod_emberline_rod");
        let point = w.fishing_line(1, 20., false).unwrap().bobber;
        w.rich_fishing.insert(
            zone,
            vec![RichSpot {
                point,
                remaining: 7,
                reserve: None,
            }],
        );
        assert!(w.fishing_line(1, 20., false).err().unwrap().contains("Willow Rod"));
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item("rod_willow_rod", 1);
        assert!(w.fishing_line(1, 20., false).is_ok());
    }
}

#[test]
fn fishing_progression_every_upgrade_keeps_earlier_waters_and_replaces_one_rod() {
    let (mut w, _rx) = super::super::fishing_tests::angler();
    // All old save IDs still exist, and a single high rod handles water and both lava areas.
    for r in RODS.iter() {
        for zone in [0, 1, 6, 45] {
            at_pool(&mut w, zone, &r.item);
            assert_eq!(
                w.fishing_line(1, 20., false).is_ok(),
                r.tier
                    >= if zone == 45 {
                        6
                    } else if [1, 6].contains(&zone) {
                        2
                    } else {
                        1
                    },
                "{} in {zone}",
                r.item
            );
        }
    }
    let recipes: Value =
        serde_json::from_str(include_str!("../../../world/fishing-workshop.txt")).unwrap();
    let p = w.players.get_mut(&1).unwrap();
    p.character.inventory.clear();
    p.character.add_item("rod_twig_rod", 1);
    p.character.level = 99;
    p.character.gold = 1_000_000;
    for r in recipes
        .as_array()
        .unwrap()
        .iter()
        .filter(|r| r["id"].as_str().unwrap().starts_with("rod:"))
    {
        let zone = r["zones"][0].as_u64().unwrap() as usize;
        let npc = w.maps[zone]
            .npcs
            .iter()
            .find(|n| n.id.starts_with("fisher_"))
            .unwrap()
            .clone();
        let p = w.players.get_mut(&1).unwrap();
        p.character.zone = zone;
        for c in r["ingredients"].as_array().unwrap().iter().skip(1) {
            p.character
                .add_item(c[0].as_str().unwrap(), c[1].as_u64().unwrap() as u32);
        }
        (p.character, _) = super::super::fishing_workshop::purchase(
            p, &npc, r["id"].as_str().unwrap(), false,
        ).unwrap();
        assert_eq!(
            p.character.inventory.len(),
            1,
            "upgrade leaves only the upgraded rod"
        );
        assert_eq!(p.character.quantity(r["item"].as_str().unwrap()), 1);
    }
}

#[test]
fn fishing_progression_rods_and_food_change_wait_and_rare_weight() {
    let (mut w, _rx) = super::super::fishing_tests::angler();
    at_pool(&mut w, 0, "rod_twig_rod");
    w.world_clock.set(Some(12.), true).unwrap();
    w.weather
        .set(0, "clear", None, daynight::unix_ms())
        .unwrap();
    w.rng = 123;
    let first = w.fishing_line(1, 20., false).unwrap();
    at_pool(&mut w, 0, "rod_worldwire_rod");
    w.rng = 123;
    let last = w.fishing_line(1, 20., false).unwrap();
    assert!(
        ((last.bite_at - last.cast_end) / (first.bite_at - first.cast_end) - 0.58).abs() < 1e-8
    );
    assert!((last.bonus / first.bonus - 1.7).abs() < 1e-8);
    for (id, speed, luck) in [
        ("dish_oasis_feast", 0.8, 1.),
        ("dish_spring_feast", 1., 1.2),
    ] {
        let p = w.players.get_mut(&1).unwrap();
        p.buffs.clear();
        p.meal_cd = 0.;
        p.character.add_item(id, 1);
        w.use_item(1, id);
        w.rng = 123;
        let food = w.fishing_line(1, 20., false).unwrap();
        assert!(
            ((food.bite_at - food.cast_end) / (last.bite_at - last.cast_end) - speed).abs() < 1e-8,
            "{id}"
        );
        assert!((food.bonus / last.bonus - luck).abs() < 1e-8, "{id}");
    }
}

#[test]
fn fishing_progression_food_is_one_choice_at_full_health_with_stronger_feasts() {
    let (mut w, _rx) = super::super::fishing_tests::angler();
    for i in ITEMS.iter().filter(|i| i.id.starts_with("dish_")) {
        let p = w.players.get_mut(&1).unwrap();
        p.buffs.clear();
        p.meal_cd = 0.;
        p.character.level = 99;
        p.character.hp = p.character.max_hp();
        p.character.change_resource(p.character.max_resource());
        p.character.add_item(&i.id, 2);
        w.use_item(1, &i.id);
        let p = &w.players[&1];
        assert_eq!(
            p.character.quantity(&i.id),
            1,
            "eat at full health: {}",
            i.id
        );
        assert_eq!(p.meal_cd, 30.);
        let bonus = p.buffs.iter().find(|b| b.id.starts_with("meal:")).unwrap();
        assert_eq!(bonus.time, 600.);
        let spec = i.food_bonus.as_ref().unwrap();
        assert_eq!(bonus.kind, spec.kind);
        assert_eq!(bonus.amount, spec.amount);
        if i.id.ends_with("_feast") {
            let grill = item(&i.id.replace("_feast", "_grill")).unwrap();
            assert_eq!(spec.amount, grill.food_bonus.as_ref().unwrap().amount * 2.);
        }
        w.use_item(1, &i.id);
        assert_eq!(
            w.players[&1].character.quantity(&i.id),
            1,
            "shared timer rejects repeats"
        );
    }
    let p = w.players.get_mut(&1).unwrap();
    p.buffs.clear();
    p.meal_cd = 0.;
    p.character.add_item("dish_shore_grill", 1);
    p.character.add_item("dish_cold_feast", 1);
    w.use_item(1, "dish_shore_grill");
    let p = w.players.get_mut(&1).unwrap();
    p.apply_buff("test_haste", BuffKind::Haste, 0.1, 10.);
    assert!(
        (p.buff(BuffKind::Haste) - 0.12).abs() < 1e-8,
        "food coexists with skill buffs"
    );
    p.apply_buff("weaker_haste", BuffKind::Haste, 0.05, 10.);
    assert!((p.buff(BuffKind::Haste) - 0.12).abs() < 1e-8);
    p.buffs.retain(|b| b.kind != BuffKind::Regen);
    p.meal_cd = 0.;
    w.use_item(1, "dish_cold_feast");
    let p = &w.players[&1];
    assert_eq!(
        p.buffs.iter().filter(|b| b.id.starts_with("meal:")).count(),
        1
    );
    assert!((p.buff(BuffKind::Haste) - 0.1).abs() < 1e-8);
    assert!((p.buff(BuffKind::Shield) - 0.04).abs() < 1e-8);
    // One real world tick verifies expiry without waiting or grinding for ten minutes.
    for b in &mut w.players.get_mut(&1).unwrap().buffs {
        b.left = 0.01;
    }
    w.step();
    assert!(
        !w.players[&1]
            .buffs
            .iter()
            .any(|b| b.id.starts_with("meal:")),
        "food bonus expires"
    );
}
