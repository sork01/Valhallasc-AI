//! The Lapis Erg: reachable oasis loops, caravan hub and two outdoor elites.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

const ERG: usize = 25;

#[test]
fn lapis_gates_oases_hub_and_astrolabe_are_reachable() {
    let w = world();
    let m = &w.maps[ERG];
    assert_eq!(
        (m.name.as_str(), m.levels, m.size),
        ("The Lapis Erg", Some([80, 85]), 160)
    );
    assert_eq!((m.slimes.len(), m.quests.len()), (42, 10));
    assert!(m.in_city(m.spawn));
    assert_eq!(
        w.maps[23].slimes.len(),
        0,
        "Veyrroot remains a peaceful city"
    );
    let back = m
        .portals
        .iter()
        .find(|p| p.id == "lapis_canopy_gate")
        .unwrap();
    let gate = w.maps[23]
        .portals
        .iter()
        .find(|p| p.id == "canopy_lapis_gate")
        .unwrap();
    assert_eq!((back.to, gate.to), (23, ERG));
    for (source, portal) in [(m, back), (&w.maps[23], gate)] {
        let mut foot = at(portal.x, portal.y);
        source.collide(&mut foot, PLAYER_RADIUS);
        assert!(
            foot.distance(at(portal.x, portal.y)) < 1e-6,
            "{} blocked",
            portal.id
        );
        let mut arrival = at(portal.tx, portal.ty);
        w.maps[portal.to].collide(&mut arrival, PLAYER_RADIUS);
        assert!(
            arrival.distance(at(portal.tx, portal.ty)) < 1e-6,
            "{} arrival blocked",
            portal.id
        );
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == portal.to)
                .all(|s| s.point().distance(arrival) >= 8.)
        );
    }
    let seen = flood(m, &blocked(m, &[]), m.spawn);
    for n in &m.npcs {
        assert!(reached(m, &seen, n.position_at(0.)), "{}", n.id);
    }
    for s in w.slimes.iter().filter(|s| s.zone == ERG) {
        assert!(reached(m, &seen, s.point()), "{}", s.kind);
    }
    for p in [at(132., 29.), at(67., 72.), at(112., 92.)] {
        assert!(reached(m, &seen, p));
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][ERG - 1];
    assert_eq!(zone["futureInstance"]["status"], "sealed");
    assert_eq!(zone["futureInstance"]["name"], "The Sunken Astrolabe");
    let objects = zone["objects"].as_array().unwrap();
    assert_eq!(
        objects
            .iter()
            .filter(|o| o["kind"] == "lapis_oasis")
            .count(),
        3
    );
    assert!(
        objects
            .iter()
            .filter(|o| o["kind"] == "lapis_date_palm")
            .count()
            >= 75
    );
    let travel = m
        .npcs
        .iter()
        .find(|n| n.id == "travel_azure_wells")
        .unwrap();
    assert!(travel.travel_links.contains(&"travel_veyrroot".to_string()));
    assert!(
        w.maps[23]
            .npcs
            .iter()
            .find(|n| n.id == "travel_veyrroot")
            .unwrap()
            .travel_links
            .contains(&"travel_azure_wells".to_string())
    );
}

#[test]
fn lapis_enemies_materials_elites_and_quest_rewards_are_registered() {
    let w = world();
    let m = &w.maps[ERG];
    for (kind, level, drop) in [
        ("sandhopper", 80, "sandhopper_chitin"),
        ("dunefennec", 81, "fennec_fur"),
        ("glassscorpion", 82, "scorpion_glass"),
        ("sunvulture", 83, "vulture_quill"),
        ("dunecolossus", 84, "colossus_core"),
        ("mirageroc", 85, "roc_plume"),
    ] {
        assert!(m.slimes.iter().any(|s| s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 400000. && damage > 6000.);
    }
    assert!(is_elite("dunecolossus") && is_elite("mirageroc"));
    assert!(!is_elite("glassscorpion"));
    for q in &m.quests {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "lapis_hoppers",
        "lapis_fennecs",
        "lapis_colossus",
        "lapis_roc",
    ] {
        assert!(
            m.quests
                .iter()
                .find(|q| q.id == id)
                .unwrap()
                .reward_item
                .is_some()
        );
    }
    for id in ["lapis_colossus", "lapis_roc"] {
        assert!(m.quests.iter().find(|q| q.id == id).unwrap().group);
    }
}
