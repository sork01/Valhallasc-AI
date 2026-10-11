//! The Tanglecrown: reachable braided jungle, services and two outdoor elites.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

const JUNGLE: usize = 22;

#[test]
fn tanglecrown_gates_hub_loops_and_temple_are_reachable() {
    let w = world();
    let m = &w.maps[JUNGLE];
    assert_eq!(
        (m.name.as_str(), m.levels, m.size),
        ("The Tanglecrown", Some([75, 80]), 144)
    );
    assert_eq!((m.slimes.len(), m.quests.len()), (42, 9));
    assert!(m.in_city(m.spawn));
    let back = m
        .portals
        .iter()
        .find(|p| p.id == "tangle_ribbon_gate")
        .unwrap();
    let gate = w.maps[21]
        .portals
        .iter()
        .find(|p| p.id == "ribbon_tangle_gate")
        .unwrap();
    assert_eq!((back.to, gate.to), (21, JUNGLE));
    for (source, portal) in [(m, back), (&w.maps[21], gate)] {
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
    for s in w.slimes.iter().filter(|s| s.zone == JUNGLE) {
        assert!(reached(m, &seen, s.point()), "{}", s.kind);
    }
    for p in [at(112., 26.), at(72., 27.), at(87., 96.), at(57., 57.)] {
        assert!(reached(m, &seen, p));
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][JUNGLE - 1];
    assert_eq!(zone["futureInstance"]["status"], "sealed");
    assert_eq!(zone["futureInstance"]["name"], "Temple of the Rain Crown");
    let objects = zone["objects"].as_array().unwrap();
    assert!(objects.iter().filter(|o| o["kind"] == "kapok_tree").count() >= 80);
    assert!(
        objects
            .iter()
            .filter(|o| o["kind"] == "jungle_water")
            .count()
            >= 20
    );
    let travel = m.npcs.iter().find(|n| n.id == "travel_banyan").unwrap();
    assert_eq!(travel.travel_links, ["travel_jubilee"]);
    assert!(
        w.maps[21]
            .npcs
            .iter()
            .find(|n| n.id == "travel_jubilee")
            .unwrap()
            .travel_links
            .contains(&"travel_banyan".to_string())
    );
}

#[test]
fn tanglecrown_enemies_materials_and_quest_rewards_are_registered() {
    let w = world();
    let m = &w.maps[JUNGLE];
    for (kind, level, drop) in [
        ("orchidmantis", 75, "mantis_petals"),
        ("canopyglider", 76, "glider_membrane"),
        ("poolcaiman", 77, "caiman_scale"),
        ("drumgorilla", 78, "gorilla_drumskin"),
        ("jadeanaconda", 79, "anaconda_jade"),
        ("crownjaguar", 80, "jaguar_crown"),
    ] {
        assert!(m.slimes.iter().any(|s| s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 300000. && damage > 5000.);
    }
    assert!(is_elite("jadeanaconda") && is_elite("crownjaguar"));
    assert!(!is_elite("poolcaiman"));
    for q in &m.quests {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "tangle_mantises",
        "tangle_gliders",
        "tangle_anaconda",
        "tangle_jaguar",
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
    for id in ["tangle_anaconda", "tangle_jaguar"] {
        assert!(m.quests.iter().find(|q| q.id == id).unwrap().group);
    }
}
