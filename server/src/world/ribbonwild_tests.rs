//! The Ribbonwild: a reachable pinwheel circuit, vivid festival hub and six new enemies.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

const FAIR: usize = 21;

#[test]
fn ribbonwild_gates_hub_circuit_and_entrance_are_reachable() {
    let w = world();
    let m = &w.maps[FAIR];
    assert_eq!(
        (m.name.as_str(), m.levels, m.size),
        ("The Ribbonwild", Some([70, 75]), 136)
    );
    assert_eq!((m.slimes.len(), m.quests.len()), (42, 12));
    assert!(m.in_city(m.spawn));
    let out = m
        .portals
        .iter()
        .find(|p| p.id == "ribbon_sun_gate")
        .unwrap();
    let back = w.maps[20]
        .portals
        .iter()
        .find(|p| p.id == "sun_ribbon_gate")
        .unwrap();
    assert_eq!((out.to, back.to), (20, FAIR));
    for (source, portal) in [(m, out), (&w.maps[20], back)] {
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
    for s in w.slimes.iter().filter(|s| s.zone == FAIR) {
        assert!(reached(m, &seen, s.point()), "{}", s.kind);
    }
    for p in [at(72., 28.), at(72., 106.), at(108., 65.), at(113., 65.)] {
        assert!(reached(m, &seen, p));
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][FAIR - 1];
    assert_eq!(zone["futureInstance"]["status"], "open");
    assert_eq!(zone["futureInstance"]["name"], "The Thousandfold Pavilion");
    let objects = zone["objects"].as_array().unwrap();
    assert!(
        objects
            .iter()
            .filter(|o| o["kind"] == "festival_bloom")
            .count()
            >= 120
    );
    assert!(
        objects
            .iter()
            .filter(|o| o["kind"] == "fan_topiary")
            .count()
            >= 50
    );
    let master = m.npcs.iter().find(|n| n.id == "travel_jubilee").unwrap();
    assert_eq!(master.travel_links, ["travel_millbridge", "travel_banyan"]);
    assert!(
        w.maps[20]
            .npcs
            .iter()
            .find(|n| n.id == "travel_millbridge")
            .unwrap()
            .travel_links
            .contains(&"travel_jubilee".to_string())
    );
}

#[test]
fn ribbonwild_kinds_gear_and_elite_quests_are_registered() {
    let w = world();
    let m = &w.maps[FAIR];
    for (kind, level, drop) in [
        ("ribbongecko", 70, "ribbon_tail"),
        ("balloonbeetle", 71, "balloon_silk"),
        ("paintedmacaw", 72, "macaw_plume"),
        ("jesterling", 73, "jester_bell"),
        ("paradegryphon", 74, "gryphon_feather"),
        ("maskcolossus", 75, "masquerade_mask"),
    ] {
        assert!(m.slimes.iter().any(|s| s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 250000. && damage > 3500.);
    }
    assert!(is_elite("paradegryphon") && is_elite("maskcolossus"));
    assert!(!is_elite("jesterling"));
    for q in &m.quests {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "ribbon_geckos",
        "ribbon_beetles",
        "ribbon_gryphon",
        "ribbon_colossus",
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
    for id in ["ribbon_gryphon", "ribbon_colossus"] {
        assert!(m.quests.iter().find(|q| q.id == id).unwrap().group);
    }
}
