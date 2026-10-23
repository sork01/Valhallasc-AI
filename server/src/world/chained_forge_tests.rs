//! Chained Forge release: real collision, open muster, ten-fighter gate and copy recovery.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;
const ZONE: usize = 46;

fn open_for_test(w: &mut World) {
    for m in &mut w.maps {
        if m.raid {
            m.sealed_template = false;
        }
    }
}
fn hire_nine(w: &mut World) {
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    c.gold = 2_000_000;
    place(w, 1, ZONE, at(35., 303.));
    for class in [
        "warrior", "warrior", "mage", "mage", "assassin", "assassin", "priest", "priest", "hunter",
    ] {
        w.time += 1.;
        w.interact(1, "cf_quartermaster", Some(&format!("merc_{class}")));
    }
}
#[test]
fn chained_forge_floor_collision_halls_portals_and_three_copies() {
    let w = world();
    let m = &w.maps[ZONE];
    assert_eq!(
        (m.name.as_str(), m.size, m.min_level, m.players, m.copies),
        ("The Chained Forge", 320, 99, 10, 3)
    );
    assert!(m.raid && m.interior && !m.sealed_template);
    assert_eq!(w.weather.view(ZONE, None, 0)["inside"], true);
    assert!(
        m.slimes.iter().filter(|s| is_boss(&s.kind)).count() == 10,
        "all nine Wardens and Eldmarr ship together"
    );
    let grid = blocked(m, &[]);
    let descent = flood(m, &grid, at(62., 290.));
    let muster = flood(m, &grid, m.spawn);
    assert!(
        !reached(m, &muster, at(62., 290.)),
        "the muster cannot bypass its ten-fighter gate"
    );
    for p in &m.places {
        assert!(
            reached(
                m,
                if p.id == "cf_muster" {
                    &muster
                } else {
                    &descent
                },
                at(p.x, p.y)
            ),
            "{}",
            p.id
        );
        let original = at(p.x, p.y);
        let mut collided = original;
        m.collide(&mut collided, PLAYER_RADIUS);
        assert!(
            collided.distance(original) < 1e-6,
            "{} actual collision",
            p.id
        );
    }
    assert_eq!(
        m.places
            .iter()
            .filter(|p| p.id.starts_with("cf_hall_"))
            .count(),
        10
    );
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let z = &data["zones"][45];
    let cells = z["forgeFloor"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r.as_str().unwrap().bytes().filter(|c| *c == b'=').count())
        .sum::<usize>();
    assert!((31800..=32400).contains(&cells));
    assert_eq!(z["forgePacks"].as_array().unwrap().len(), 10);
    assert_eq!(
        z["forgePacks"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|p| p["mandatory"] == true)
            .count(),
        6
    );
    for h in z["forgeHalls"].as_array().unwrap() {
        let route = h["route"].as_array().unwrap();
        for pair in route.windows(2) {
            let a = at(pair[0][0].as_f64().unwrap(), pair[0][1].as_f64().unwrap());
            let b = at(pair[1][0].as_f64().unwrap(), pair[1][1].as_f64().unwrap());
            assert!(
                m.line_clear(a, b, PLAYER_RADIUS),
                "{} route blocked",
                h["id"]
            );
        }
    }
    for from in [ZONE, 45] {
        for p in &w.maps[from].portals {
            if p.to != ZONE && from != ZONE {
                continue;
            }
            let dst = &w.maps[p.to];
            let point = at(p.tx, p.ty);
            let mut collided = point;
            dst.collide(&mut collided, PLAYER_RADIUS);
            assert!(
                collided.distance(point) < 1e-6,
                "{} arrival collision",
                p.id
            );
            assert!(
                dst.portals
                    .iter()
                    .all(|q| point.distance(at(q.x, q.y)) > q.r + 1.),
                "{} bounce",
                p.id
            );
            assert!(
                dst.slimes
                    .iter()
                    .all(|s| point.distance(at(s.x, s.y)) >= 8.),
                "{} enemy clearance",
                p.id
            );
        }
    }
    let copies: Vec<_> = w
        .instances
        .iter()
        .filter(|i| i.template == ZONE)
        .map(|i| i.zone)
        .collect();
    assert_eq!(copies, vec![46, 107, 108]);
    assert!(copies.iter().all(|z| w.maps[*z].raid));
    assert_eq!(w.public_zone(107), ZONE);
    assert_eq!(w.maps.len(), 117);
}
#[test]
fn chained_forge_open_muster_preserves_seal_level_and_ten_fighter_gates() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    assert!(
        !w.maps[ZONE].sealed_template,
        "the released entrance is open"
    );
    for m in &mut w.maps {
        if m.raid {
            m.sealed_template = true;
        }
    }
    w.players.get_mut(&1).unwrap().character.level = 99;
    place(&mut w, 1, 45, at(133., 24.));
    w.time = 10.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 45, "sealed even for level 99");
    open_for_test(&mut w);
    w.players.get_mut(&1).unwrap().character.level = 98;
    w.time += PORTAL_DELAY;
    w.use_portal(1);
    assert_eq!(
        w.players[&1].character.zone, 45,
        "level gate applies to muster too"
    );
    w.players.get_mut(&1).unwrap().character.level = 99;
    w.time += PORTAL_DELAY;
    w.use_portal(1);
    assert_eq!(
        w.players[&1].character.zone, ZONE,
        "one human may enter only the separated muster"
    );
    place(&mut w, 1, ZONE, at(30., 296.));
    w.time += PORTAL_DELAY;
    w.use_portal(1);
    assert!(
        w.players[&1].character.point().distance(at(30., 296.)) < 0.01,
        "one cannot pass inner gate"
    );
    hire_nine(&mut w);
    assert_eq!(w.players.values().filter(|p| p.merc.is_some()).count(), 9);
    assert_eq!(w.players[&1].character.gold, 965000);
    for p in w.players.values_mut() {
        p.character.x = 32.;
        p.character.y = 302.;
    }
    let merc = *w.players.keys().find(|s| **s != 1).unwrap();
    w.players.get_mut(&merc).unwrap().character.hp = 0.;
    place(&mut w, 1, ZONE, at(30., 296.));
    w.time += PORTAL_DELAY;
    w.use_portal(1);
    assert!(
        w.players[&1].character.point().distance(at(30., 296.)) < 0.01,
        "a fallen fighter does not fill a seat"
    );
    w.players.get_mut(&merc).unwrap().character.hp = 1.;
    w.time += PORTAL_DELAY;
    w.use_portal(1);
    assert!(w.players[&1].character.point().distance(at(62., 290.)) < 0.01);
    w.update_mercenaries();
    assert!(w.players.values().all(|p| p.character.zone == ZONE));
    place(&mut w, 1, ZONE, at(22., 303.));
    w.time += PORTAL_DELAY;
    w.use_portal(1);
    w.update_mercenaries();
    assert_eq!(w.players[&1].character.zone, 45);
    assert_eq!(
        w.players.values().filter(|p| p.merc.is_some()).count(),
        0,
        "raid hires do not spill into the outdoor zone"
    );
}
#[test]
fn chained_forge_wipe_keeps_kills_contracts_and_recovers_at_current_hall() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    hire_nine(&mut w);
    w.enter_instance(ZONE);
    // Borrow two existing bosses and a helper to test recovery before raid bosses exist.
    let boss = w
        .slimes
        .iter()
        .position(|s| s.zone == 44 && s.kind == "null_hour")
        .unwrap();
    let killed = w
        .slimes
        .iter()
        .position(|s| s.zone == 44 && s.kind == "null_bell")
        .unwrap();
    let hall = at(164., 201.);
    w.spawns[boss].zone = ZONE;
    w.spawns[boss].x = hall.x;
    w.spawns[boss].y = hall.y;
    w.slimes[boss] = w.fresh_enemy(boss);
    w.slimes[boss].state = "chase".into();
    w.slimes[boss].target = Some(1);
    w.slimes[boss].hp = 1.;
    w.slimes[killed].zone = ZONE;
    w.slimes[killed].dead = true;
    for p in w.players.values_mut() {
        p.character.hp = 0.;
        p.fallen = true;
        p.dead_time = 400.;
    }
    w.players.get_mut(&1).unwrap().character.hp = 1.;
    w.update_raid_wipes();
    assert_eq!(w.slimes[boss].hp, 1., "a living fighter prevents a wipe");
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    w.update_raid_wipes();
    assert_eq!(w.slimes[boss].hp, w.slimes[boss].max_hp);
    assert!(w.slimes[killed].dead, "previous boss stays dead");
    assert!(w.players.values().all(|p| !p.fallen && p.dead_time == 0.));
    let rally = w.instance_at(ZONE).unwrap().rally.unwrap();
    let cp = w.maps[ZONE]
        .places
        .iter()
        .find(|p| p.id == "cf_checkpoint_4")
        .unwrap();
    assert!(rally.distance(at(cp.x, cp.y)) < 0.01);
    for p in w.players.values_mut() {
        p.dead_time = 3.2;
    }
    let sessions: Vec<_> = w.players.keys().copied().collect();
    for session in sessions {
        w.update_player(session);
    }
    assert!(
        w.players
            .values()
            .all(|p| p.character.hp > 0. && p.character.point().distance(rally) < 0.01)
    );
    w.update_mercenaries();
    assert_eq!(w.players.len(), 10, "contracts survive the wipe");
    assert!((w.instance_at(ZONE).unwrap().grace_until - w.time - 60.).abs() < 0.01);
    w.hit_slime(boss, 1, 1., false);
    assert_eq!(w.instance_at(ZONE).unwrap().grace_until, 0.);
    assert_eq!(RAID_FALLEN_HOLD_MAX, 2400.);
}
#[test]
fn chained_forge_empty_copy_reserves_twenty_minutes_and_resets_only_itself() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, ZONE, at(30., 303.));
    w.enter_instance(ZONE);
    w.update_instances();
    let second = 107;
    w.enter_instance(second);
    place(&mut w, 1, 45, at(127., 25.));
    w.update_instances();
    assert!(w.instance_at(ZONE).unwrap().active);
    assert_eq!(
        w.instance_for(1, ZONE).unwrap(),
        ZONE,
        "returner keeps progress"
    );
    w.time += 1199.;
    w.update_instances();
    assert!(w.instance_at(ZONE).unwrap().active);
    w.time += 2.;
    w.update_instances();
    assert!(!w.instance_at(ZONE).unwrap().active);
    assert!(w.instance_at(ZONE).unwrap().members.is_empty());
    // Other dungeons retain their immediate empty reset.
    w.enter_instance(5);
    w.update_instances();
    assert!(!w.instance_at(5).unwrap().active);
}

#[test]
fn chained_forge_fallen_stay_down_past_ten_minutes_while_the_raid_fight_runs() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, ZONE, at(164., 201.));
    w.enter_instance(ZONE);
    let boss = w
        .slimes
        .iter()
        .position(|s| s.zone == 44 && s.kind == "null_hour")
        .unwrap();
    w.spawns[boss].zone = ZONE;
    w.spawns[boss].x = 164.;
    w.spawns[boss].y = 201.;
    w.slimes[boss] = w.fresh_enemy(boss);
    w.slimes[boss].state = "chase".into();
    w.slimes[boss].target = Some(1);
    let def = std::sync::Arc::make_mut(w.boss.table.get_mut("null_hour").unwrap());
    def.mechanics.clear();
    def.arena = Some([145., 185., 183., 217.]);
    w.update_boss_mechanics();
    assert!(w.boss.fight_in(ZONE));
    let p = w.players.get_mut(&1).unwrap();
    p.character.hp = 0.;
    p.fallen = true;
    p.dead_time = 700.;
    w.update_player(1);
    assert!(
        w.players[&1].fallen,
        "raid fighter stays down past ordinary 600-second cap"
    );
    w.players.get_mut(&1).unwrap().dead_time = 2400.;
    w.update_player(1);
    assert!(
        !w.players[&1].fallen,
        "raid cap still provides an eventual escape"
    );
}

#[test]
fn chained_forge_inner_gate_moves_humans_and_mercenaries_together() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    hire_nine(&mut w);
    open_for_test(&mut w);
    // Turn one hired session into a second human without changing the real raid membership.
    let human = *w.players.keys().find(|s| **s != 1).unwrap();
    w.players.get_mut(&human).unwrap().merc = None;
    for p in w.players.values_mut() {
        p.character.x = 32.;
        p.character.y = 302.;
    }
    place(&mut w, 1, ZONE, at(30., 296.));
    w.time += PORTAL_DELAY;
    w.use_portal(1);
    assert!(
        w.players
            .values()
            .all(|p| p.character.point().distance(at(62., 290.)) < 0.01),
        "all ten cross atomically"
    );
}
