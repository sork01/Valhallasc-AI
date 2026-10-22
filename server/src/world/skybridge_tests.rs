//! Only the level-30 Shattered Span addition: collision, travel, private copies, real kills and quest loot.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const SPAN: usize = 42;
const BIFROST: usize = 7;

fn enter(w: &mut World, session: u64) {
    place(w, session, BIFROST, at(58., 128.));
    w.time += 2.;
    w.use_portal(session);
}

#[test]
fn skybridge_data_and_actual_collision_are_reachable() {
    let w = world();
    let m = &w.maps[SPAN];
    assert_eq!(
        (m.name.as_str(), m.min_level, m.players, m.copies),
        ("The Shattered Span", 30, 5, 4)
    );
    assert!(!m.sealed_template && m.interior);
    assert_eq!(w.maps[40].name, "The Arena", "older public IDs stay fixed");
    assert_eq!(w.maps[41].name, "Nornroot Barrow", "Nornroot stays at 41");
    assert_eq!(w.instances.iter().filter(|i| i.template == SPAN).count(), 4);
    assert!(pursuit::grid_matches_collision(m, PLAYER_RADIUS));
    let seen = flood(m, &blocked(m, &[]), m.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == SPAN) {
        assert!(reached(m, &seen, s.point()), "{} is reachable", s.kind);
        assert_eq!(s.level, 30);
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
            .filter(|e| e.kind.starts_with("span_"))
            .count(),
        6
    );
    assert_eq!(
        ITEMS
            .iter()
            .filter(|i| i.source.as_deref() == Some("skybridge"))
            .count(),
        29
    );
    let quests: Vec<_> = w.maps[BIFROST]
        .quests
        .iter()
        .filter(|q| q.id.starts_with("span_"))
        .collect();
    assert_eq!(quests.len(), 3);
    assert_eq!(quests.iter().filter(|q| q.group).count(), 2);
    assert!(
        quests
            .iter()
            .all(|q| q.objectives.iter().all(|o| o.target != "span_archon"))
    );
    for q in quests {
        if let Some(id) = &q.reward_item {
            assert_eq!(item(id).unwrap().required_level, 30);
        }
    }
}

#[test]
fn skybridge_travel_enters_and_leaves_cleanly() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 30;
    enter(&mut w, 1);
    let p = &w.players[&1].character;
    assert_eq!(w.public_zone(p.zone), SPAN);
    assert_eq!(p.point(), w.maps[SPAN].spawn);
    let a = p.zone;
    place(&mut w, 1, a, at(49., 99.));
    w.time += 2.;
    w.use_portal(1);
    let p = &w.players[&1].character;
    assert_eq!(p.zone, BIFROST);
    assert_eq!(p.point(), at(58., 133.));
}

#[test]
fn skybridge_entry_gate_and_party_isolation_and_return() {
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
        w.players.get_mut(&id).unwrap().character.level = 30;
    }
    w.players.get_mut(&1).unwrap().character.level = 29;
    enter(&mut w, 1);
    assert_eq!(w.players[&1].character.zone, BIFROST);
    w.players.get_mut(&1).unwrap().character.level = 30;
    for id in 1..=3 {
        enter(&mut w, id);
    }
    let a = w.players[&1].character.zone;
    let b = w.players[&3].character.zone;
    assert_eq!(a, w.players[&2].character.zone);
    assert_ne!(a, b);
    assert_eq!(w.public_zone(a), SPAN);
    assert_eq!(w.public_zone(b), SPAN);
    place(&mut w, 1, a, at(49., 99.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, BIFROST);
    assert_eq!(w.players[&2].character.zone, a);
}

#[test]
fn skybridge_bosses_drop_exclusive_gear_and_only_clear_their_copy() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
    for id in 1..=2 {
        w.players.get_mut(&id).unwrap().character.level = 30;
        enter(&mut w, id);
    }
    let zone = w.players[&1].character.zone;
    let other = w.players[&2].character.zone;
    for q in ["span_toll", "span_spectrum"] {
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
    for (n, kind) in ["span_warden", "span_weaver", "span_archon"]
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
            .filter(|i| i.source.as_deref() == Some("skybridge"))
            .collect();
        assert_eq!(pieces.len(), boss_slots(kind).len());
        assert!(
            pieces
                .iter()
                .all(|i| i.rarity == "rare" && i.required_level == 30)
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
    place(&mut w, 1, zone, at(56., 10.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, BIFROST);
}

#[test]
fn skybridge_bridgeward_set_hits_nearest_enemy_and_has_a_timer() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 30;
    let mut slots = std::collections::BTreeMap::new();
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
                i.source.as_deref() == Some("skybridge")
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
    assert_eq!(c.set_counts()["skybridge"], 8);
    // Position an existing enemy nearby in the same zone so the prism arc finds a target
    let zone = w.players[&1].character.zone;
    let at = w.players[&1].character.point();
    let s_id = w.slimes.iter().position(|s| s.zone == zone).unwrap();
    w.slimes[s_id].dead = false;
    w.slimes[s_id].x = at.x + 1.;
    w.slimes[s_id].y = at.y;
    assert_eq!(
        w.apply_set_signature(1, "charge", at, Point { x: 1., y: 0. }, None, &[])
            .as_deref(),
        Some("skybridge")
    );
    assert!(
        w.apply_set_signature(1, "charge", at, Point { x: 1., y: 0. }, None, &[])
            .is_none()
    );
}
