//! The Cairnspine: connected switchbacks, reciprocal pass, three outdoor elites and a sealed gate.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

const CAIRN: usize = 27;

#[test]
fn cairnspine_routes_hub_and_pass_are_reachable() {
    let w = world();
    let m = &w.maps[CAIRN];
    assert_eq!(
        (m.name.as_str(), m.levels, m.size),
        ("The Cairnspine", Some([90, 95]), 168)
    );
    assert_eq!((m.slimes.len(), m.quests.len()), (43, 11));
    assert!(m.in_city(m.spawn));
    let back = m
        .portals
        .iter()
        .find(|p| p.id == "cairn_frostwake_gate")
        .unwrap();
    let pass = w.maps[26]
        .portals
        .iter()
        .find(|p| p.id == "frostwake_cairn_gate")
        .unwrap();
    assert_eq!((back.to, pass.to), (26, CAIRN));
    for (source, portal) in [(m, back), (&w.maps[26], pass)] {
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
    for s in w.slimes.iter().filter(|s| s.zone == CAIRN) {
        assert!(reached(m, &seen, s.point()), "{}", s.kind);
    }
    for p in [at(55., 74.), at(106., 78.), at(134., 26.)] {
        assert!(reached(m, &seen, p));
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][CAIRN - 1];
    assert!(
        zone["objects"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|o| o["kind"] == "cairn_dead_tree")
            .count()
            >= 70
    );
    assert_eq!(zone["futureInstance"]["status"], "sealed");
    assert!(
        m.npcs
            .iter()
            .find(|n| n.id == "travel_boulderwatch")
            .unwrap()
            .travel_links
            .contains(&"travel_frostwake".to_string())
    );
    assert!(
        w.maps[26]
            .npcs
            .iter()
            .find(|n| n.id == "travel_frostwake")
            .unwrap()
            .travel_links
            .contains(&"travel_boulderwatch".to_string())
    );
}

#[test]
fn cairnspine_enemies_rewards_and_elites_are_registered() {
    let w = world();
    let m = &w.maps[CAIRN];
    for (kind, level, drop) in [
        ("screeferret", 90, "screeferret_pelt"),
        ("stoneibex", 91, "ibex_horn"),
        ("slateraven", 92, "slate_raven_feather"),
        ("ridgeadder", 93, "ridgeadder_scale"),
        ("cairnbehemoth", 93, "behemoth_heartstone"),
        ("whitebarktitan", 94, "whitebark_core"),
        ("stormcondor", 95, "stormcondor_plume"),
    ] {
        assert!(m.slimes.iter().any(|s| s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 600000. && damage > 8000.);
    }
    assert_eq!(m.slimes.iter().filter(|s| is_elite(&s.kind)).count(), 3);
    for q in &m.quests {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "cairn_ferrets",
        "cairn_ibex",
        "cairn_behemoth",
        "cairn_titan",
        "cairn_condor",
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
    for id in ["cairn_behemoth", "cairn_titan", "cairn_condor"] {
        assert!(m.quests.iter().find(|q| q.id == id).unwrap().group);
    }
}
