//! Only the level-25 Nornroot addition: collision, travel, private copies, real kills and quest loot.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const BARROW: usize = 41;
const WYRD: usize = 6;

fn enter(w: &mut World, session: u64) {
    // These original checks exercise level limits, copies and loot after admission.
    let c = &mut w.players.get_mut(&session).unwrap().character;
    if !c.quests.iter().any(|q| q.id == "entry_norn") {
        c.quests.push(QuestProgress {
            id: "entry_norn".into(),
            counts: vec![1; 4],
            claimed: true,
            completions: 1,
        });
    }
    place(w, session, WYRD, at(84., 66.));
    w.time += 2.;
    w.use_portal(session);
}

#[test]
fn nornroot_data_and_actual_collision_are_reachable() {
    let w = world();
    let m = &w.maps[BARROW];
    assert_eq!(
        (m.name.as_str(), m.min_level, m.players, m.copies),
        ("Nornroot Barrow", 25, 5, 4)
    );
    assert!(!m.sealed_template && m.interior);
    assert_eq!(w.maps[40].name, "The Arena", "older public IDs stay fixed");
    assert_eq!(
        w.instances.iter().filter(|i| i.template == BARROW).count(),
        4
    );
    assert!(pursuit::grid_matches_collision(m, PLAYER_RADIUS));
    let seen = flood(m, &blocked(m, &[]), m.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == BARROW) {
        assert!(reached(m, &seen, s.point()), "{} is reachable", s.kind);
        assert_eq!(s.level, 25);
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
            .filter(|e| e.kind.starts_with("barrow_"))
            .count(),
        6
    );
    assert_eq!(
        ITEMS
            .iter()
            .filter(|i| i.source.as_deref() == Some("nornroot"))
            .count(),
        29
    );
    let quests: Vec<_> = w.maps[WYRD]
        .quests
        .iter()
        .filter(|q| q.id.starts_with("barrow_"))
        .collect();
    assert_eq!(quests.len(), 3);
    assert_eq!(quests.iter().filter(|q| q.group).count(), 2);
    assert!(
        quests
            .iter()
            .all(|q| q.objectives.iter().all(|o| o.target != "barrow_fatebound"))
    );
    for q in quests {
        if let Some(id) = &q.reward_item {
            assert_eq!(item(id).unwrap().required_level, 25);
        }
    }
    assert!(w.signs.contains_key("barrow_fatebound"));
}

#[test]
fn nornroot_entry_gate_and_party_isolation_and_return() {
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
        w.players.get_mut(&id).unwrap().character.level = 25;
    }
    w.players.get_mut(&1).unwrap().character.level = 24;
    enter(&mut w, 1);
    assert_eq!(w.players[&1].character.zone, WYRD);
    w.players.get_mut(&1).unwrap().character.level = 25;
    for id in 1..=3 {
        enter(&mut w, id);
    }
    let a = w.players[&1].character.zone;
    let b = w.players[&3].character.zone;
    assert_eq!(a, w.players[&2].character.zone);
    assert_ne!(a, b);
    assert_eq!(w.public_zone(a), BARROW);
    assert_eq!(w.public_zone(b), BARROW);
    place(&mut w, 1, a, at(49., 99.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, WYRD);
    assert_eq!(w.players[&2].character.zone, a);
}

#[test]
fn nornroot_bosses_drop_exclusive_gear_and_only_clear_their_copy() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
    for id in 1..=2 {
        w.players.get_mut(&id).unwrap().character.level = 25;
        enter(&mut w, id);
    }
    let zone = w.players[&1].character.zone;
    let other = w.players[&2].character.zone;
    for q in ["barrow_amber", "barrow_threads"] {
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
    for (n, kind) in ["barrow_fatebound", "barrow_doorward", "barrow_threadkeeper"]
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
            .filter(|i| i.source.as_deref() == Some("nornroot"))
            .collect();
        assert_eq!(pieces.len(), boss_slots(kind).len());
        assert!(
            pieces
                .iter()
                .all(|i| i.rarity == "rare" && i.required_level == 25)
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
            .filter(|q| q.id != "entry_norn")
            .all(|q| q.counts == vec![1])
    );
    let living_other = w
        .slimes
        .iter()
        .filter(|s| s.zone == other && !s.dead)
        .count();
    assert_eq!(living_other, 15);
    place(&mut w, 1, zone, at(56., 10.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, WYRD);
}

#[test]
fn nornroot_fatewoven_set_heals_only_its_wearer_and_has_a_timer() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 25;
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
                i.source.as_deref() == Some("nornroot")
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
    assert_eq!(c.set_counts()["nornroot"], 8);
    c.hp = c.max_hp() * 0.5;
    let hp = c.hp;
    let expected = c.max_hp() * 0.04;
    let other = w.players[&2].character.hp;
    let at = w.players[&1].character.point();
    assert_eq!(
        w.apply_set_signature(1, "battlecry", at, Point { x: 1., y: 0. }, None, &[])
            .as_deref(),
        Some("nornroot")
    );
    assert!((w.players[&1].character.hp - hp - expected).abs() < 1e-8);
    assert_eq!(w.players[&2].character.hp, other);
    assert!(
        w.apply_set_signature(1, "battlecry", at, Point { x: 1., y: 0. }, None, &[])
            .is_none()
    );
}

#[test]
fn nornroot_spindle_snare_warns_then_spares_the_clear_middle() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
    for s in &mut w.slimes {
        s.dead = true;
        s.respawn = 1e9;
    }
    let boss = w
        .slimes
        .iter()
        .position(|s| s.zone == BARROW && s.kind == "barrow_fatebound")
        .unwrap();
    w.slimes[boss].dead = false;
    w.slimes[boss].state = "chase".into();
    w.slimes[boss].target = Some(1);
    w.enter_instance(BARROW);
    place(&mut w, 1, BARROW, at(57., 18.)); // Inside the clear middle.
    place(&mut w, 2, BARROW, at(62., 18.)); // Inside the lethal ring.
    let mut warned = false;
    for _ in 0..(30. / TICK) as usize {
        w.time += TICK;
        w.tick += 1;
        w.update_boss_mechanics();
        if w.boss_mech_view(BARROW)
            .iter()
            .any(|v| v["cast"]["name"] == "Spindle Snare")
        {
            warned = true;
            assert!(
                w.players[&2].character.hp > 0.,
                "the warning precedes damage"
            );
        }
        if w.players[&2].character.hp <= 0. {
            break;
        }
    }
    assert!(warned, "the cast is visible for the five-second warning");
    assert!(w.players[&1].character.hp > 0.);
    assert!(w.players[&2].character.hp <= 0.);
    assert!(w.players[&2].fallen);
}
