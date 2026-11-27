use super::*;

fn setup(class: Class) -> (World, mpsc::Receiver<Value>) {
    let mut w = World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
    w.resource_rng = 1; // No mana return on the first cast unless a test explicitly forces it.
    let (tx, rx) = mpsc::channel(256);
    let welcome = w
        .join(
            1,
            None,
            Some(Look {
                class,
                ..Look::default()
            }),
            tx.clone(),
        )
        .unwrap();
    tx.try_send(welcome).unwrap();
    for s in &mut w.slimes {
        s.dead = true;
        s.respawn = 10000.;
    }
    // New heroes land on the pier, inside a sanctuary where nothing hurts them: stand on open ground.
    let c = &mut w.players.get_mut(&1).unwrap().character;
    (c.x, c.y) = (276., 226.);
    (w, rx)
}
fn resource(w: &World) -> f64 {
    w.players[&1].character.resource()
}

#[test]
fn mana_return_once_per_accepted_cast_for_both_casters() {
    for (class, id) in [(Class::Mage, "twinbolt"), (Class::Priest, "blessing")] {
        let (mut w, mut rx) = setup(class);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 40;
        let max = c.max_resource();
        c.resource = Some(max * 0.5);
        let before = c.resource();
        let cost = skills::find(class, id).unwrap().cost;
        w.resource_rng = 0; // First roll is below 10%.
        w.use_skill(1, id, Point { x: 1., y: 0. });
        assert!((resource(&w) - (before - cost + max * 0.2)).abs() < 1e-8);
        assert_eq!(w.resource_rng, 1, "one roll, including a multi-bolt spell");
        let event = std::iter::from_fn(|| rx.try_recv().ok())
            .find(|v| v["kind"] == "skill")
            .unwrap();
        assert_eq!(event["mana"], max * 0.2);
        assert!(w.players[&1].skill_cd.contains_key(id));
        if class == Class::Mage {
            assert_eq!(w.bolts.len(), 2);
        }
    }
}

#[test]
fn mana_return_rejected_casts_never_spend_mana_or_roll() {
    let (mut w, _rx) = setup(Class::Mage);
    for gate in [
        "locked",
        "poor",
        "stunned",
        "dead",
        "cooldown",
        "dashing",
        "no target",
        "wrong class",
    ] {
        let p = w.players.get_mut(&1).unwrap();
        p.character.level = if gate == "locked" { 1 } else { 40 };
        p.character.hp = if gate == "dead" {
            0.
        } else {
            p.character.max_hp()
        };
        p.character.resource = Some(if gate == "poor" { 1. } else { 100. });
        p.stun = if gate == "stunned" { 1. } else { 0. };
        p.dash = if gate == "dashing" { 1. } else { 0. };
        p.skill_cd.clear();
        if gate == "cooldown" {
            p.skill_cd.insert("twinbolt".into(), 2.);
        }
        let before = p.character.resource();
        w.resource_rng = 0;
        let skill = match gate {
            "no target" => "lifedrain",
            "wrong class" => "mend",
            _ => "twinbolt",
        };
        w.use_skill(1, skill, Point { x: 1., y: 0. });
        assert_eq!(resource(&w), before, "{gate}");
        assert_eq!(w.resource_rng, 0, "{gate} consumed a roll");
    }
}

#[test]
fn mana_return_counts_free_mend_and_caps_the_actual_event_amount() {
    let (mut w, mut rx) = setup(Class::Priest);
    let p = w.players.get_mut(&1).unwrap();
    p.character.level = 25;
    p.character.hp = p.character.max_hp() * 0.5;
    p.character.resource = Some(0.);
    p.mend_free_left = 4.;
    let max = p.character.max_resource();
    w.resource_rng = 0;
    w.use_skill(1, "mend", Point::default());
    assert_eq!(resource(&w), max * 0.2, "a valid free cast also rolls");
    let p = w.players.get_mut(&1).unwrap();
    p.character.hp = p.character.max_hp() * 0.5;
    p.character.resource = Some(max);
    p.skill_cd.clear();
    while rx.try_recv().is_ok() {}
    w.resource_rng = 0;
    w.use_skill(1, "mend", Point::default());
    assert_eq!(resource(&w), max);
    assert_eq!(w.resource_rng, 1);
    let event = std::iter::from_fn(|| rx.try_recv().ok())
        .find(|v| v["kind"] == "skill")
        .unwrap();
    assert_eq!(event["mana"], 0., "no false gain when already full");
    // A paid cast at full mana restores only the room left by its cost.
    let (mut w, _rx) = setup(Class::Mage);
    w.players.get_mut(&1).unwrap().character.level = 40;
    w.players.get_mut(&1).unwrap().character.reset_resource();
    w.resource_rng = 0;
    w.use_skill(1, "twinbolt", Point::default());
    assert_eq!(resource(&w), w.players[&1].character.max_resource());
}

#[test]
fn mana_return_chance_is_one_in_ten_and_other_resources_do_not_roll() {
    for class in [Class::Priest, Class::Mage] {
        let (mut w, _rx) = setup(class);
        w.players.get_mut(&1).unwrap().character.level = 40;
        let max = w.players[&1].character.max_resource();
        let mut count = 0;
        for _ in 0..6000 {
            w.players.get_mut(&1).unwrap().character.resource = Some(0.);
            let gained = w.roll_cast_mana(1);
            assert!(gained == 0. || (gained - max * 0.2).abs() < 1e-8);
            count += usize::from(gained > 0.);
        }
        assert!((510..=690).contains(&count), "{class:?}: {count}/6000");
    }
    for class in [Class::Warrior, Class::Hunter, Class::Assassin] {
        let (mut w, _rx) = setup(class);
        w.players.get_mut(&1).unwrap().character.resource = Some(0.);
        w.resource_rng = 0;
        assert_eq!(w.roll_cast_mana(1), 0.);
        assert_eq!(w.resource_rng, 0);
    }
}

#[test]
fn mana_return_also_applies_to_hired_casters_through_the_normal_ai_cast_path() {
    for class in [Class::Mage, Class::Priest] {
        let (mut w, mut rx) = setup(class);
        let p = w.players.get_mut(&1).unwrap();
        p.merc = Some("Owner".into());
        p.character.level = 4; // Exactly one available skill for each class.
        p.character.hp = p.character.max_hp() * 0.5;
        let max = p.character.max_resource();
        p.character.resource = Some(max * 0.5);
        w.resource_rng = 0;
        w.ai_combat_at(1, &[1], Some((Point { x: 279., y: 226. }, 0.5)));
        assert_eq!(w.resource_rng, 1, "{class:?}: AI made exactly one cast");
        let event = std::iter::from_fn(|| rx.try_recv().ok())
            .find(|v| v["kind"] == "skill")
            .unwrap();
        assert_eq!(event["mana"], max * 0.2);
    }
}

#[test]
fn warrior_half_rage_generation_also_applies_to_both_sides_of_pvp() {
    let (mut w, _rx) = setup(Class::Warrior);
    let _other_rx = super::wyrd_tests::join(&mut w, 2, Class::Warrior);
    super::wyrd_tests::place(&mut w, 2, 0, Point { x: 277., y: 226. });
    for p in w.players.values_mut() {
        p.pvp_flag = true;
    }
    let mut landed = 0;
    for _ in 0..30 {
        for p in w.players.values_mut() {
            p.character.hp = p.character.max_hp();
            p.character.resource = Some(0.);
        }
        let before = w.players[&2].character.hp;
        w.pvp_hit(1, 2, 20., false);
        let taken = before - w.players[&2].character.hp;
        if taken > 0. {
            landed += 1;
        }
        assert!((resource(&w) - taken * 0.25).abs() < 1e-8);
        assert!((w.players[&2].character.resource() - taken * 0.5).abs() < 1e-8);
    }
    assert!(landed > 0);
}

#[test]
fn class_basic_damage_multipliers_preserve_hit_crit_and_skill_rolls() {
    for class in [
        Class::Assassin,
        Class::Hunter,
        Class::Warrior,
        Class::Mage,
        Class::Priest,
    ] {
        let (mut w, _rx) = setup(class);
        w.players.get_mut(&1).unwrap().character.level = 60;
        let mut hits = 0;
        let mut misses = 0;
        let mut crits = 0;
        for seed in 0..100 {
            w.rng = seed;
            let normal = w.roll_damage(1, 1.);
            w.rng = seed;
            let basic = w.roll_basic_damage(1);
            assert_eq!(basic.1, normal.1, "{class:?}: critical chance");
            if normal.0 == 0. {
                assert_eq!(basic.0, 0., "miss stays a miss");
                misses += 1;
            } else {
                hits += 1;
                crits += usize::from(normal.1);
                let factor = match class {
                    Class::Assassin => 0.5,
                    Class::Hunter | Class::Priest => 1.5,
                    _ => 1.,
                };
                let expected = normal.0 * factor;
                assert!(
                    (basic.0 - expected).abs() <= 1.,
                    "{class:?}: {basic:?} / {normal:?}"
                );
            }
            // Skill rolls still apply their authored multiplier, without the basic-attack reduction.
            w.rng = seed;
            let skill = w.roll_damage(1, 2.);
            if normal.0 > 0. {
                assert!((skill.0 - normal.0 * 2.).abs() <= 1.);
            }
        }
        assert!(hits > 0 && misses > 0 && crits > 0, "{class:?}");
    }
}

#[test]
fn class_basic_strikes_use_their_multiplier_with_buffs_and_no_energy() {
    for (class, mult) in [
        (Class::Assassin, 0.5),
        (Class::Hunter, 1.5),
        (Class::Priest, 1.5),
    ] {
        let (mut w, _rx) = setup(class);
        let p = w.players.get_mut(&1).unwrap();
        p.character.level = 60;
        p.character.resource = Some(0.);
        p.face = Point { x: 1., y: 0. };
        p.apply_buff("test_damage", BuffKind::Damage, 0.3, 10.);
        let s = &mut w.slimes[0];
        s.dead = false;
        s.zone = 0;
        s.x = 277.;
        s.y = 226.;
        s.hp = 100000.;
        s.kind = "slime".into();
        for seed in 0..20 {
            w.rng = seed;
            let expected = w.roll_damage(1, mult);
            let before = w.slimes[0].hp;
            w.rng = seed;
            w.strike(1);
            if class.ranged() {
                let bolt = w.bolts.pop().unwrap();
                assert_eq!((bolt.damage, bolt.crit), expected, "{class:?}");
            } else {
                assert_eq!(before - w.slimes[0].hp, expected.0);
            }
            assert_eq!(resource(&w), 0.);
        }
    }
}

#[test]
fn each_class_starts_with_its_resource_and_authoritative_snapshot() {
    for (class, kind, amount) in [
        (Class::Warrior, "rage", 0.),
        (Class::Assassin, "energy", 100.),
        (Class::Hunter, "energy", 100.),
        (Class::Mage, "mana", 100.),
        (Class::Priest, "mana", 100.),
    ] {
        let (w, _) = setup(class);
        let p = w.players[&1].snapshot();
        assert_eq!(p["resourceType"], kind);
        assert_eq!(p["resource"], amount);
        assert_eq!(p["maxResource"], 100.);
    }
}
#[test]
fn energy_recovers_in_combat_caps_at_one_hundred_and_stops_when_dead() {
    for class in [Class::Assassin, Class::Hunter] {
        let (mut w, _) = setup(class);
        let p = w.players.get_mut(&1).unwrap();
        p.character.resource = Some(0.);
        p.combat_left = 5.;
        for _ in 0..20 {
            w.update_resource(1);
        }
        let expected = if class == Class::Hunter { 15. } else { 10. };
        assert!((resource(&w) - expected).abs() < 1e-8, "{class:?}");
        let p = w.players.get_mut(&1).unwrap();
        p.character.resource = Some(0.);
        p.combat_left = 0.;
        for _ in 0..20 {
            w.update_resource(1);
        }
        assert!(
            (resource(&w) - expected).abs() < 1e-8,
            "{class:?} out of combat"
        );
        for _ in 0..250 {
            w.update_resource(1);
        }
        assert_eq!(resource(&w), 100.);
        let p = w.players.get_mut(&1).unwrap();
        p.character.hp = 0.;
        p.character.resource = Some(0.);
        w.update_resource(1);
        assert_eq!(resource(&w), 0.);
    }
}
#[test]
fn mana_trickles_in_combat_including_enemy_aggro_without_damage_and_returns_quickly_after() {
    let (mut w, _) = setup(Class::Mage);
    let p = w.players.get_mut(&1).unwrap();
    p.character.resource = Some(0.);
    p.combat_left = 5.;
    // A mage has 100 mana at level 1: 1.5% a second in combat is 0.075 a tick.
    let gain = |w: &mut World| {
        let before = resource(w);
        w.update_resource(1);
        resource(w) - before
    };
    assert!((gain(&mut w) - 0.075).abs() < 1e-9);
    let s = &mut w.slimes[0];
    s.dead = false;
    s.target = Some(1);
    s.state = "chase".into();
    w.players.get_mut(&1).unwrap().combat_left = 0.;
    // A visible enemy chasing the mage is combat even with no damage dealt.
    // The old fixture left the enemy at its unrelated world spawn, possibly behind cover.
    w.maps[0].objects.clear();
    w.slimes[0].x = 277.;
    w.slimes[0].y = 226.;
    w.slimes[0].zone = 0;
    assert!((gain(&mut w) - 0.075).abs() < 1e-9);
    assert_eq!(w.players[&1].combat_left, 5.);
    w.slimes[0].dead = true;
    for _ in 0..102 {
        w.update_resource(1);
    }
    assert_eq!(w.players[&1].combat_left, 0.);
    // Out of combat it is 5% a second: 0.25 a tick.
    assert!((gain(&mut w) - 0.25).abs() < 1e-9);
}
#[test]
fn mana_grows_with_level_and_intellect_and_legacy_saves_start_full() {
    let (mut w, _) = setup(Class::Priest);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 10;
    c.attributes.intellect = 3;
    c.resource = None;
    // The level-10 priest milestone contributes Intellect alongside trained points.
    assert_eq!(c.max_resource(), 225.);
    assert_eq!(c.resource(), 225.);
    let mut old = serde_json::to_value(&*c).unwrap();
    old.as_object_mut().unwrap().remove("resource");
    let legacy: Character = serde_json::from_value(old).unwrap();
    assert_eq!(legacy.resource(), 225.);
    c.resource = Some(5.);
    c.grant_xp(c.xp_need());
    assert_eq!(c.resource(), c.max_resource());
}
#[test]
fn warrior_gains_rage_only_from_actual_damage_and_loses_it_outside_combat() {
    let (mut w, _) = setup(Class::Warrior);
    let s = &mut w.slimes[0];
    s.dead = false;
    s.hp = 100.;
    w.hit_slime(0, 1, 0., false);
    assert_eq!(resource(&w), 0.);
    w.hit_slime(0, 1, 20., false);
    assert_eq!(resource(&w), 5.);
    let point = w.players[&1].character.point();
    w.hurt_player(1, 43., point);
    assert_eq!(resource(&w), 10.);
    w.update_resource(1);
    assert_eq!(resource(&w), 10.);
    w.slimes[0].dead = true;
    w.players.get_mut(&1).unwrap().combat_left = 0.;
    for _ in 0..20 {
        w.update_resource(1);
    }
    assert!((resource(&w) - 5.).abs() < 1e-8);
    w.players.get_mut(&1).unwrap().character.resource = Some(0.);
    w.slimes[0].dead = false;
    w.slimes[0].hp = 2.;
    w.hit_slime(0, 1, 10000., false);
    assert_eq!(resource(&w), 0.5, "Overkill cannot grant extra rage");
    w.hit_slime(0, 1, 10000., false);
    assert_eq!(resource(&w), 0.5, "Dead enemies cannot grant rage");
}
#[test]
fn insufficient_resources_and_invalid_targets_spend_nothing_and_start_no_cooldown() {
    let (mut w, mut rx) = setup(Class::Mage);
    w.players.get_mut(&1).unwrap().character.level = 20;
    w.players.get_mut(&1).unwrap().character.resource = Some(1.);
    while rx.try_recv().is_ok() {}
    w.use_skill(1, "twinbolt", Point { x: 1., y: 0. });
    assert_eq!(resource(&w), 1.);
    assert!(w.players[&1].skill_cd.is_empty());
    assert!(w.bolts.is_empty());
    assert!(
        rx.try_recv().unwrap()["text"]
            .as_str()
            .unwrap()
            .contains("Not enough mana")
    );
    w.players.get_mut(&1).unwrap().character.resource = Some(100.);
    w.use_skill(1, "lifedrain", Point { x: 1., y: 0. });
    assert_eq!(resource(&w), 100.);
    assert!(w.players[&1].skill_cd.is_empty());
    w.use_skill(1, "twinbolt", Point { x: 1., y: 0. });
    assert_eq!(resource(&w), 76.);
    assert!(w.players[&1].skill_cd.contains_key("twinbolt"));
    w.use_skill(1, "twinbolt", Point { x: 1., y: 0. });
    assert_eq!(resource(&w), 76.);
}
#[test]
fn shadowstep_spends_energy_but_basic_attacks_work_with_no_resource() {
    let (mut w, _) = setup(Class::Assassin);
    w.players.get_mut(&1).unwrap().character.resource = Some(19.);
    w.message(1, ClientMessage::Dash { dx: 1., dy: 0. });
    assert_eq!(w.players[&1].dash, 0.);
    assert_eq!(resource(&w), 19.);
    w.players.get_mut(&1).unwrap().character.resource = Some(20.);
    w.message(1, ClientMessage::Dash { dx: 1., dy: 0. });
    assert!(w.players[&1].dash > 0.);
    assert_eq!(resource(&w), 0.);
    w.players.get_mut(&1).unwrap().dash = 0.;
    w.start_attack(1);
    assert!(w.players[&1].attack > 0.);
    assert_eq!(resource(&w), 0.);
    let (mut w, _) = setup(Class::Warrior);
    w.start_attack(1);
    assert!(w.players[&1].attack > 0.);
    assert_eq!(resource(&w), 0.);
}
#[test]
fn food_restores_mana_at_full_health_and_potions_share_cooldown_without_wasting_items() {
    let (mut w, _) = setup(Class::Mage);
    let p = w.players.get_mut(&1).unwrap();
    p.character.resource = Some(0.);
    p.combat_left = 100.;
    p.character.add_item("traveler_stew", 2);
    p.character.add_item("mana_potion", 2);
    p.character.add_item("health_potion", 1);
    w.use_item(1, "traveler_stew");
    assert_eq!(w.players[&1].character.quantity("traveler_stew"), 1);
    w.use_item(1, "traveler_stew");
    assert_eq!(w.players[&1].character.quantity("traveler_stew"), 1);
    for _ in 0..80 {
        w.update_food(1);
        w.update_player(1);
    }
    // The meal gives 50 mana over 4 s, plus the 1.5% a second trickle of a mage in combat.
    assert!((resource(&w) - 56.).abs() < 0.5, "{}", resource(&w));
    w.use_item(1, "mana_potion");
    assert_eq!(resource(&w), 100.);
    assert_eq!(w.players[&1].character.quantity("mana_potion"), 1);
    w.players.get_mut(&1).unwrap().character.hp = 1.;
    w.use_item(1, "health_potion");
    assert_eq!(w.players[&1].character.hp, 1.);
    assert_eq!(w.players[&1].character.quantity("health_potion"), 1);
    for class in [Class::Warrior, Class::Hunter, Class::Assassin] {
        let (mut w, _) = setup(class);
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item("mana_potion", 1);
        w.players.get_mut(&1).unwrap().character.resource = Some(100.);
        w.use_item(1, "mana_potion");
        assert_eq!(w.players[&1].character.quantity("mana_potion"), 1);
        assert_eq!(w.players[&1].potion_cd, 0.);
        w.players.get_mut(&1).unwrap().character.resource = Some(0.);
        w.use_item(1, "mana_potion");
        assert_eq!(w.players[&1].character.quantity("mana_potion"), 0);
        assert_eq!(resource(&w), 100.);
        assert!(w.players[&1].potion_cd > 0.);
    }
}

#[test]
fn old_health_stacks_scale_with_high_level_health_and_final_tiers_unlock_at_95_and_99() {
    let (mut w, _) = setup(Class::Warrior);
    assert_eq!(
        crate::items::best_tier("health_potion", 94)
            .unwrap()
            .required_level,
        90
    );
    assert_eq!(
        crate::items::best_tier("health_potion", 95)
            .unwrap()
            .required_level,
        95
    );
    assert_eq!(
        crate::items::best_tier("health_potion", 99)
            .unwrap()
            .required_level,
        99
    );
    let p = w.players.get_mut(&1).unwrap();
    p.character.level = 99;
    p.character.hp = 1.;
    p.character.add_item("health_potion", 1);
    p.character.add_item("traveler_stew", 1);
    let heal = (p.character.max_hp() * 0.4).round();
    w.use_item(1, "health_potion");
    assert_eq!(w.players[&1].character.hp, 1. + heal);
    assert_eq!(w.players[&1].character.quantity("health_potion"), 0);
    w.players.get_mut(&1).unwrap().character.hp = 1.;
    w.use_item(1, "traveler_stew");
    let meal = w.players[&1]
        .buffs
        .iter()
        .find(|b| b.kind == BuffKind::Regen)
        .unwrap();
    assert_eq!(meal.amount * meal.time, heal);
}

#[test]
fn every_consumable_tier_matches_its_price_healing_resource_and_food_rules_for_all_classes() {
    use crate::items::best_tier;
    let levels = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99];
    let potion_prices = [5, 60, 110, 180, 270, 380, 520, 700, 900, 1150, 1275, 1400];
    let meal_prices = [3, 25, 45, 75, 115, 165, 225, 300, 390, 500, 550, 600];
    for class in [
        Class::Warrior,
        Class::Mage,
        Class::Assassin,
        Class::Priest,
        Class::Hunter,
    ] {
        let (mut w, _) = setup(class);
        for (index, level) in levels.into_iter().enumerate() {
            let health = best_tier("health_potion", level).unwrap();
            let mana = best_tier("mana_potion", level).unwrap();
            let meal = best_tier("traveler_stew", level).unwrap();
            assert_eq!(
                (
                    health.required_level,
                    mana.required_level,
                    meal.required_level
                ),
                (level, level, level)
            );
            assert_eq!(
                (health.price, mana.price, meal.price),
                (
                    potion_prices[index],
                    potion_prices[index],
                    meal_prices[index]
                )
            );
            let p = w.players.get_mut(&1).unwrap();
            p.character.level = level;
            p.character.hp = 1.;
            p.character.resource = Some(0.);
            p.last_hurt = 1.0e9;
            p.potion_cd = 0.;
            p.character.potion_ready = 0;
            p.meal_cd = 0.;
            p.character.meal_ready = 0;
            p.buffs.clear();
            p.character.inventory.retain(|stack| {
                item(&stack.item).is_none_or(|i| !matches!(i.kind.as_str(), "food" | "potion"))
            });
            for item in [health, mana, meal] {
                p.character.add_item(&item.id, 2);
            }
            let max_hp = p.character.max_hp();
            let max_resource = p.character.max_resource();
            let heal = consumables::health_amount(health, &p.character);
            let restore = consumables::resource_amount(mana, &p.character).min(max_resource);
            let meal_resource = consumables::resource_amount(meal, &p.character).min(max_resource);
            assert!(heal >= (max_hp * 0.4).round(), "{class:?} level {level}");

            w.use_item(1, &health.id);
            assert_eq!(
                w.players[&1].character.hp,
                (1. + heal).min(max_hp),
                "health: {class:?} level {level}"
            );
            assert_eq!(w.players[&1].character.quantity(&health.id), 1);
            assert_eq!(w.players[&1].potion_cd, 60.);
            w.use_item(1, &mana.id);
            assert_eq!(
                w.players[&1].character.quantity(&mana.id),
                2,
                "the shared potion cooldown keeps the second family"
            );
            {
                let p = w.players.get_mut(&1).unwrap();
                p.potion_cd = 0.;
                p.character.potion_ready = 0;
            }
            w.use_item(1, &mana.id);
            assert!(
                (w.players[&1].character.resource() - restore).abs() < 1e-8,
                "resource: {class:?} level {level}"
            );
            assert_eq!(w.players[&1].character.quantity(&mana.id), 1);

            {
                let p = w.players.get_mut(&1).unwrap();
                p.character.hp = 1.;
                p.character.resource = Some(0.);
            }
            w.use_item(1, &meal.id);
            assert_eq!(w.players[&1].character.hp, 1., "food is gradual");
            assert_eq!(w.players[&1].character.quantity(&meal.id), 1);
            w.use_item(1, &meal.id);
            assert_eq!(
                w.players[&1].character.quantity(&meal.id),
                1,
                "one active meal"
            );
            for _ in 0..(8. / TICK) as usize {
                w.update_food(1);
                w.players.get_mut(&1).unwrap().buffs.retain_mut(|buff| {
                    buff.left -= TICK;
                    buff.left > 0.
                });
            }
            assert!(
                (w.players[&1].character.hp - (1. + heal).min(max_hp)).abs() < 1e-6,
                "meal health: {class:?} level {level}"
            );
            assert!(
                (w.players[&1].character.resource() - meal_resource).abs() < 1e-6,
                "meal resource: {class:?} level {level}: {} vs {meal_resource}",
                w.players[&1].character.resource()
            );
        }
    }
}
#[test]
fn mana_survives_resume_while_rage_and_energy_reset_and_death_respawns_correctly() {
    for class in [
        Class::Mage,
        Class::Priest,
        Class::Warrior,
        Class::Assassin,
        Class::Hunter,
    ] {
        let (mut w, mut rx) = setup(class);
        let welcome = std::iter::from_fn(|| rx.try_recv().ok())
            .find(|v| v["type"] == "welcome")
            .unwrap();
        let key = welcome["token"].as_str().unwrap().to_owned();
        w.players.get_mut(&1).unwrap().character.resource = Some(37.);
        w.leave(1);
        let (tx, _rx) = mpsc::channel(256);
        w.join(2, Some(key), None, tx).unwrap();
        let expected = match class.resource_type() {
            "mana" => 37.,
            "rage" => 0.,
            _ => 100.,
        };
        assert_eq!(w.players[&2].character.resource(), expected);
        let p = w.players.get_mut(&2).unwrap();
        p.character.hp = 0.;
        p.apply_death_penalty();
        assert_eq!(p.character.resource(), 0.);
        p.dead_time = 3.2;
        w.update_player(2);
        assert!(w.players[&2].character.ghost);
        assert_eq!(w.players[&2].character.resource(), 0.);
        let corpse = w.players[&2].character.corpse.clone().unwrap();
        let p = w.players.get_mut(&2).unwrap();
        p.character.zone = corpse.zone;
        p.character.x = corpse.x;
        p.character.y = corpse.y;
        w.update_player(2);
        assert!(w.players[&2].character.ghost);
        w.message(2, ClientMessage::Resurrect);
        let p = &w.players[&2];
        assert!(!p.character.ghost);
        assert_eq!(p.character.hp, (p.character.max_hp() * 0.5).round().max(1.));
        assert_eq!(
            p.character.resource(),
            if class == Class::Warrior { 0. } else { 100. }
        );
    }
}
#[test]
fn healing_a_fighting_party_member_puts_the_priest_in_combat() {
    let (mut w, _) = setup(Class::Priest);
    let (tx, _rx) = mpsc::channel(256);
    let look = Look {
        name: "Second".into(),
        ..Look::default()
    };
    w.join(2, None, Some(look), tx).unwrap();
    let p = w.players.get_mut(&2).unwrap();
    p.character.hp = 1.;
    p.combat_left = 5.;
    w.heal_players(1, &[2], 1.);
    assert_eq!(w.players[&1].combat_left, 5.);
    w.players.get_mut(&1).unwrap().character.resource = Some(0.);
    w.update_resource(1);
    // Still in combat: only the trickle, not the out-of-combat rate.
    assert!((resource(&w) - 0.075).abs() < 1e-9);
}
