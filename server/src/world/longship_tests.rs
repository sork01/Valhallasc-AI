//! Only the level-35 Longship addition: collision, travel, private copies, real kills and quest loot.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const LONGSHIP: usize = 43;
const DEEP: usize = 8;

fn enter(w: &mut World, session: u64) {
    place(w, session, DEEP, at(54., 146.));
    w.time += 2.;
    w.use_portal(session);
}

#[test]
fn longship_data_and_actual_collision_are_reachable() {
    let w = world();
    let m = &w.maps[LONGSHIP];
    assert_eq!(
        (m.name.as_str(), m.min_level, m.players, m.copies),
        ("The Drowned Longship", 35, 5, 4)
    );
    assert!(!m.sealed_template && m.interior);
    assert_eq!(w.maps[40].name, "The Arena", "older public IDs stay fixed");
    assert_eq!(
        w.instances
            .iter()
            .filter(|i| i.template == LONGSHIP)
            .count(),
        4
    );
    assert!(pursuit::grid_matches_collision(m, PLAYER_RADIUS));
    let seen = flood(m, &blocked(m, &[]), m.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == LONGSHIP) {
        assert!(reached(m, &seen, s.point()), "{} is reachable", s.kind);
        assert_eq!(s.level, 35);
        assert!(s.point().distance(m.spawn) > 8.);
        assert!(item(material(&s.kind)).is_some());
    }
    for p in &m.portals {
        assert!(reached(m, &seen, at(p.x, p.y)));
        let target = &w.maps[p.to];
        let mut arrival = at(p.tx, p.ty);
        target.collide(&mut arrival, PLAYER_RADIUS);
        assert!(arrival.distance(at(p.tx, p.ty)) < 1e-6);
        assert!(
            target
                .slimes
                .iter()
                .all(|s| at(s.x, s.y).distance(arrival) > 8.)
        );
    }
    assert_eq!(m.slimes.len(), 15);
    assert_eq!(
        crate::cathedral::ENEMIES
            .iter()
            .filter(|e| e.kind.starts_with("keel_"))
            .count(),
        6
    );
    assert_eq!(
        ITEMS
            .iter()
            .filter(|i| i.source.as_deref() == Some("longship"))
            .count(),
        29
    );
    let quests: Vec<_> = w.maps[DEEP]
        .quests
        .iter()
        .filter(|q| q.id.starts_with("keel_"))
        .collect();
    assert_eq!(quests.len(), 3);
    assert_eq!(quests.iter().filter(|q| q.group).count(), 2);
    assert!(
        quests
            .iter()
            .all(|q| q.objectives.iter().all(|o| o.target != "keel_captain"))
    );
    for q in quests {
        if let Some(id) = &q.reward_item {
            assert_eq!(item(id).unwrap().required_level, 35);
        }
    }
    assert!(w.signs.contains_key("keel_captain"));
}

#[test]
fn longship_entry_gate_and_party_isolation_and_return() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=3).map(|id| join(&mut w, id, Class::Warrior)).collect();
    let ally = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(ally),
            name: None,
        },
    );
    w.social(
        2,
        SocialCommand::PartyAccept {
            id: w.players[&1].character.id.clone(),
        },
    );
    for id in 1..=3 {
        w.players.get_mut(&id).unwrap().character.level = 35;
    }
    w.players.get_mut(&1).unwrap().character.level = 34;
    enter(&mut w, 1);
    assert_eq!(w.players[&1].character.zone, DEEP);
    w.players.get_mut(&1).unwrap().character.level = 35;
    for id in 1..=3 {
        enter(&mut w, id);
    }
    let a = w.players[&1].character.zone;
    let b = w.players[&3].character.zone;
    assert_eq!(a, w.players[&2].character.zone);
    assert_ne!(a, b);
    assert_eq!(w.public_zone(a), LONGSHIP);
    assert_eq!(w.public_zone(b), LONGSHIP);
    place(&mut w, 1, a, at(56., 110.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, DEEP);
    assert_eq!(w.players[&2].character.zone, a);
}

#[test]
fn longship_bosses_drop_exclusive_gear_and_only_clear_their_copy() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
    for id in 1..=2 {
        w.players.get_mut(&id).unwrap().character.level = 35;
        enter(&mut w, id);
    }
    let zone = w.players[&1].character.zone;
    let other = w.players[&2].character.zone;
    for q in ["keel_cargo", "keel_rigging"] {
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .push(QuestProgress {
                id: q.into(),
                counts: vec![0],
                claimed: false,
                completions: 0,
            });
    }
    // Kill the final first: the clear portal must still wait for BOTH earlier guardians.
    for (n, kind) in ["keel_captain", "keel_cargomaw", "keel_bosun"]
        .iter()
        .enumerate()
    {
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == zone && s.kind == *kind)
            .unwrap();
        let point = w.slimes[id].point();
        place(&mut w, 1, zone, point);
        w.hit_slime(id, 1, 1e9, false);
        assert_eq!(w.instance_cleared(zone), n == 2);
        assert!(!w.instance_cleared(other));
        let pieces: Vec<_> = w
            .drops
            .iter()
            .filter(|d| d.zone == zone && d.point().distance(point) < 1.)
            .filter_map(|d| d.item.as_deref().and_then(item))
            .filter(|i| i.source.as_deref() == Some("longship"))
            .collect();
        assert_eq!(pieces.len(), boss_slots(kind).len());
        assert!(
            pieces
                .iter()
                .all(|i| i.rarity == "rare" && i.required_level == 35)
        );
        assert!(
            w.drops
                .iter()
                .any(|d| d.zone == zone && d.item.as_deref() == Some(material(kind)))
        );
    }
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .all(|q| q.counts == vec![1])
    );
    let living_other = w
        .slimes
        .iter()
        .filter(|s| s.zone == other && !s.dead)
        .count();
    assert_eq!(living_other, 15);
    place(&mut w, 1, zone, at(64., 13.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, DEEP);
}

#[test]
fn longship_keelbound_set_heals_only_its_wearer_and_has_a_timer() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 35;
    let mut slots = BTreeMap::new();
    for kind in [
        "armor",
        "headgear",
        "shoulders",
        "gloves",
        "weapon",
        "pants",
        "necklace",
        "cloak",
        "accessory",
    ] {
        let piece = ITEMS
            .iter()
            .find(|i| {
                i.source.as_deref() == Some("longship")
                    && i.kind == kind
                    && i.class.is_none_or(|v| v == Class::Warrior)
            })
            .unwrap();
        c.add_item(&piece.id, 1);
        let slot = match kind {
            "armor" => "chest",
            "weapon" => "hands",
            "accessory" => "accessory1",
            other => other,
        };
        slots.insert(slot.into(), piece.id.clone());
    }
    c.equip_slots(&slots).unwrap();
    assert_eq!(c.set_counts()["longship"], 8);
    c.hp = c.max_hp() * 0.5;
    c.resource = Some(0.);
    let resource_expected = c.max_resource() * 0.03;
    let hp = c.hp;
    let expected = c.max_hp() * 0.03;
    let other = w.players[&2].character.hp;
    let at = w.players[&1].character.point();
    assert_eq!(
        w.apply_set_signature(1, "battlecry", at, Point { x: 1., y: 0. }, None, &[])
            .as_deref(),
        Some("longship")
    );
    assert!((w.players[&1].character.hp - hp - expected).abs() < 1e-8);
    assert_eq!(w.players[&2].character.hp, other);
    assert!((w.players[&1].character.resource() - resource_expected).abs() < 1e-8);
    assert!(
        w.apply_set_signature(1, "battlecry", at, Point { x: 1., y: 0. }, None, &[])
            .is_none()
    );
}

#[test]
fn longship_hull_hatches_and_bulkheads_are_physical() {
    let w = world();
    let m = &w.maps[LONGSHIP];
    for (x, y) in [(55., 69.), (70., 69.), (53., 89.), (76., 47.), (30., 12.)] {
        let origin = at(x, y);
        let mut actual = origin;
        m.collide(&mut actual, PLAYER_RADIUS);
        assert!(
            actual.distance(origin) > 0.01,
            "water or hull must block {x},{y}"
        );
    }
    for (x, y) in [(64., 69.), (64., 89.), (64., 47.), (64., 110.)] {
        let origin = at(x, y);
        let mut actual = origin;
        m.collide(&mut actual, PLAYER_RADIUS);
        assert!(
            actual.distance(origin) < 1e-6,
            "gangway must stay clear {x},{y}"
        );
    }
}

#[test]
fn longship_anchorfall_warns_and_spares_players_who_step_aside() {
    for low_health in [false, true] {
        let mut w = world();
        let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
        for s in &mut w.slimes {
            s.dead = true;
            s.respawn = 1e9;
        }
        let boss = w
            .slimes
            .iter()
            .position(|s| s.zone == LONGSHIP && s.kind == "keel_captain")
            .unwrap();
        w.slimes[boss].dead = false;
        w.slimes[boss].state = "chase".into();
        w.slimes[boss].target = Some(1);
        if low_health {
            w.slimes[boss].hp *= 0.3;
        }
        w.enter_instance(LONGSHIP);
        place(&mut w, 1, LONGSHIP, at(64., 30.));
        place(&mut w, 2, LONGSHIP, at(64., 32.));
        let mut lane = None;
        for _ in 0..(30. / TICK) as usize {
            w.time += TICK;
            w.tick += 1;
            w.update_boss_mechanics();
            for view in w.boss_mech_view(LONGSHIP) {
                if view["cast"]["name"] != "Anchorfall" {
                    continue;
                }
                let shape = &view["tele"][0]["shapes"][0];
                let ax = shape["x1"].as_f64().unwrap();
                let ay = shape["y1"].as_f64().unwrap();
                let bx = shape["x2"].as_f64().unwrap();
                let by = shape["y2"].as_f64().unwrap();
                let len = (bx - ax).hypot(by - ay);
                let mid = at((ax + bx) * 0.5, (ay + by) * 0.5);
                let offset = shape["half"].as_f64().unwrap() + 1.5;
                let safe = at(
                    mid.x - (by - ay) / len * offset,
                    mid.y + (bx - ax) / len * offset,
                );
                let mut resolved = safe;
                w.maps[LONGSHIP].collide(&mut resolved, PLAYER_RADIUS);
                assert!(
                    resolved.distance(safe) < 1e-6,
                    "safe ground fits inside the real hull"
                );
                lane = Some((mid, safe));
                break;
            }
            if lane.is_some() {
                break;
            }
        }
        let (danger, safe) = lane.expect("visible Anchorfall warning");
        place(&mut w, 1, LONGSHIP, safe);
        place(&mut w, 2, LONGSHIP, danger);
        for _ in 0..(4.8 / TICK) as usize {
            w.time += TICK;
            w.tick += 1;
            w.update_boss_mechanics();
            assert!(
                w.players[&2].character.hp > 0.,
                "warning must precede lethal impact"
            );
        }
        for _ in 0..(0.5 / TICK) as usize {
            w.time += TICK;
            w.tick += 1;
            w.update_boss_mechanics();
        }
        assert!(
            w.players[&1].character.hp > 0.,
            "stepping sideways avoids the anchor"
        );
        assert!(w.players[&2].fallen && w.players[&2].character.hp <= 0.);
        if low_health {
            place(&mut w, 1, LONGSHIP, danger);
            for _ in 0..(3.2 / TICK) as usize {
                w.time += TICK;
                w.tick += 1;
                w.update_boss_mechanics();
            }
            assert!(
                w.players[&1].fallen,
                "the wider final phase pulls the same strip again"
            );
        }
    }
}

#[test]
#[ignore = "focused combat calibration: hired five against the new packs and side guardians"]
fn longship_hired_five_can_clear_the_packs_and_guardians() {
    use super::ttk::{Case, run_hired_party_pack_once};
    let w = world();
    let mercs = [Class::Priest, Class::Mage, Class::Hunter, Class::Assassin];
    let mut fights: Vec<(String, Vec<usize>)> = Vec::new();
    for (x, y) in [(64., 98.), (48., 77.), (81., 61.), (64., 43.)] {
        fights.push((
            format!("pack {x},{y}"),
            w.spawns
                .iter()
                .enumerate()
                .filter(|(_, s)| {
                    s.zone == LONGSHIP && !is_boss(&s.kind) && at(s.x, s.y).distance(at(x, y)) < 6.
                })
                .map(|(id, _)| id)
                .collect(),
        ));
    }
    for kind in ["keel_cargomaw", "keel_bosun"] {
        fights.push((
            kind.into(),
            vec![
                w.spawns
                    .iter()
                    .position(|s| s.zone == LONGSHIP && s.kind == kind)
                    .unwrap(),
            ],
        ));
    }
    for (name, ids) in fights {
        assert!(!ids.is_empty());
        let case = Case {
            consumables: true,
            rarity: "uncommon",
            enemy_level: Some(35),
            cap: Some(180.),
            ..Case::new(Class::Warrior, 35)
        };
        let out = run_hired_party_pack_once(&case, Class::Warrior, &mercs, &ids, 1);
        eprintln!(
            "[longship hired5] {name}: won {}, {:.1}s, {} fell, enemy {:.1}% DPS {:?}",
            out.killed,
            out.seconds,
            out.deaths,
            out.enemy_left * 100.,
            out.dps
        );
        assert!(out.killed, "hired five must beat {name}");
    }
}
