//! Stormglass Shore: a reachable shared zone with a sealed future instance.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

const SHORE: usize = 19;

#[test]
fn shore_has_reciprocal_clear_gates_a_hub_and_a_sealed_eye() {
    let w = world();
    let m = &w.maps[SHORE];
    assert_eq!(
        (m.name.as_str(), m.levels, m.size),
        ("The Stormglass Shore", Some([60, 65]), 128)
    );
    assert_eq!((m.slimes.len(), m.quests.len()), (41, 8));
    assert!(m.in_city(m.spawn));
    let out = m
        .portals
        .iter()
        .find(|p| p.id == "stormglass_asterion_gate")
        .unwrap();
    let back = w.maps[17]
        .portals
        .iter()
        .find(|p| p.id == "asterion_stormglass_gate")
        .unwrap();
    assert_eq!((out.to, back.to), (17, SHORE));
    for (source, portal) in [(m, out), (&w.maps[17], back)] {
        let mut p = at(portal.x, portal.y);
        source.collide(&mut p, PLAYER_RADIUS);
        assert!(
            p.distance(at(portal.x, portal.y)) < 1e-6,
            "{} is blocked",
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
            arrival.distance(at(
                w.maps[portal.to].portals[0].x,
                w.maps[portal.to].portals[0].y
            )) > 1.2
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
    for s in w.slimes.iter().filter(|s| s.zone == SHORE) {
        assert!(reached(m, &seen, s.point()), "{}", s.kind);
    }
    assert!(reached(m, &seen, at(out.x, out.y)));
    assert!(reached(m, &seen, at(105., 27.)));
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let z = &raw["zones"][SHORE - 1];
    assert_eq!(z["futureInstance"]["status"], "sealed");
    assert_eq!(z["futureInstance"]["name"], "The Eye Below");
    assert_eq!(
        z["portals"].as_array().unwrap().len(),
        1,
        "the dungeon has no portal yet"
    );
    assert!(m.npcs.iter().any(|n| n.id == "stormglass_stone"));
    let travel = m.npcs.iter().find(|n| n.id == "travel_breakwater").unwrap();
    assert_eq!(travel.travel_links, ["travel_asterion"]);
    assert!(
        w.maps[17]
            .npcs
            .iter()
            .find(|n| n.id == "travel_asterion")
            .unwrap()
            .travel_links
            .contains(&"travel_breakwater".to_string())
    );
}

#[test]
fn shore_enemies_have_real_stats_materials_and_quest_rewards() {
    let w = world();
    let m = &w.maps[SHORE];
    for (kind, level, drop) in [
        ("saltclaw", 60, "saltclaw_shell"),
        ("stormgull", 61, "stormgull_feather"),
        ("glassray", 62, "glassfin"),
        ("breakersentinel", 64, "breaker_core"),
        ("maelstromheart", 65, "stormheart"),
    ] {
        assert!(m.slimes.iter().any(|s| s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 100000. && damage > 2000.);
    }
    assert!(is_elite("maelstromheart"));
    assert!(!is_elite("breakersentinel"));
    for q in &m.quests {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "stormglass_crabs",
        "stormglass_gulls",
        "stormglass_guards",
        "stormglass_heart",
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
}
