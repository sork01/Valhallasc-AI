use super::*;

fn setup(class: Class) -> (World, mpsc::Receiver<Value>) {
    let mut w = World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
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
    (w, rx)
}
fn resource(w: &World) -> f64 {
    w.players[&1].character.resource()
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
        assert!((resource(&w) - 10.).abs() < 1e-8);
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
fn mana_waits_for_combat_to_end_including_enemy_aggro_without_damage() {
    let (mut w, _) = setup(Class::Mage);
    let p = w.players.get_mut(&1).unwrap();
    p.character.resource = Some(0.);
    p.combat_left = 5.;
    for _ in 0..99 {
        w.update_resource(1);
    }
    assert_eq!(resource(&w), 0.);
    let s = &mut w.slimes[0];
    s.dead = false;
    s.target = Some(1);
    s.state = "chase".into();
    for _ in 0..200 {
        w.update_resource(1);
    }
    assert_eq!(resource(&w), 0.);
    w.slimes[0].dead = true;
    for _ in 0..121 {
        w.update_resource(1);
    }
    assert!((resource(&w) - 5.5).abs() < 0.3);
}
#[test]
fn mana_grows_with_level_and_intellect_and_legacy_saves_start_full() {
    let (mut w, _) = setup(Class::Priest);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 10;
    c.attributes.intellect = 3;
    c.resource = None;
    assert_eq!(c.max_resource(), 205.);
    assert_eq!(c.resource(), 205.);
    let mut old = serde_json::to_value(&*c).unwrap();
    old.as_object_mut().unwrap().remove("resource");
    let legacy: Character = serde_json::from_value(old).unwrap();
    assert_eq!(legacy.resource(), 205.);
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
    assert_eq!(resource(&w), 10.);
    let point = w.players[&1].character.point();
    w.hurt_player(1, 43., point);
    assert_eq!(resource(&w), 20.);
    w.update_resource(1);
    assert_eq!(resource(&w), 20.);
    w.slimes[0].dead = true;
    w.players.get_mut(&1).unwrap().combat_left = 0.;
    for _ in 0..20 {
        w.update_resource(1);
    }
    assert!((resource(&w) - 15.).abs() < 1e-8);
    w.players.get_mut(&1).unwrap().character.resource = Some(0.);
    w.slimes[0].dead = false;
    w.slimes[0].hp = 2.;
    w.hit_slime(0, 1, 10000., false);
    assert_eq!(resource(&w), 1., "Overkill cannot grant extra rage");
    w.hit_slime(0, 1, 10000., false);
    assert_eq!(resource(&w), 1., "Dead enemies cannot grant rage");
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
    assert!((resource(&w) - 50.).abs() < 1e-8);
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
        w.use_item(1, "mana_potion");
        assert_eq!(w.players[&1].character.quantity("mana_potion"), 1);
        assert_eq!(w.players[&1].potion_cd, 0.);
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
        assert_eq!(
            w.players[&2].character.resource(),
            if class == Class::Warrior { 0. } else { 100. }
        );
    }
}
#[test]
fn healing_a_fighting_party_member_puts_the_priest_in_combat() {
    let (mut w, _) = setup(Class::Priest);
    let (tx, _rx) = mpsc::channel(256);
    w.join(2, None, Some(Look::default()), tx).unwrap();
    let p = w.players.get_mut(&2).unwrap();
    p.character.hp = 1.;
    p.combat_left = 5.;
    w.heal_players(1, &[2], 1.);
    assert_eq!(w.players[&1].combat_left, 5.);
    w.players.get_mut(&1).unwrap().character.resource = Some(0.);
    w.update_resource(1);
    assert_eq!(resource(&w), 0.);
}
