//! Frostwake Shelf: reachable snow roads, three elite territories, rewards and reciprocal gate.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

const SHELF: usize = 26;

#[test]
fn frostwake_routes_gates_and_hub_are_reachable() {
    let w = world();
    let m = &w.maps[SHELF];
    assert_eq!(
        (m.name.as_str(), m.levels, m.size),
        ("Frostwake Shelf", Some([85, 90]), 160)
    );
    assert_eq!((m.slimes.len(), m.quests.len()), (43, 11));
    assert!(m.in_city(m.spawn));
    let back = m
        .portals
        .iter()
        .find(|p| p.id == "frostwake_lapis_gate")
        .unwrap();
    let gate = w.maps[25]
        .portals
        .iter()
        .find(|p| p.id == "lapis_frostwake_gate")
        .unwrap();
    assert_eq!((back.to, gate.to), (25, SHELF));
    for (source, portal) in [(m, back), (&w.maps[25], gate)] {
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
    for s in w.slimes.iter().filter(|s| s.zone == SHELF) {
        assert!(reached(m, &seen, s.point()), "{}", s.kind);
    }
    for p in [at(79., 74.), at(119., 25.), at(96., 37.)] {
        assert!(reached(m, &seen, p));
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][SHELF - 1];
    assert!(
        zone["objects"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|o| o["kind"] == "frostwake_crevasse")
            .count()
            >= 20
    );
    assert!(
        m.npcs
            .iter()
            .find(|n| n.id == "travel_frostwake")
            .unwrap()
            .travel_links
            .contains(&"travel_azure_wells".to_string())
    );
    assert!(
        w.maps[25]
            .npcs
            .iter()
            .find(|n| n.id == "travel_azure_wells")
            .unwrap()
            .travel_links
            .contains(&"travel_frostwake".to_string())
    );
}

#[test]
fn frostwake_kinds_elites_materials_and_gear_rewards_are_registered() {
    let w = world();
    let m = &w.maps[SHELF];
    for (kind, level, drop) in [
        ("snowhare", 85, "snowhare_fur"),
        ("iceotter", 86, "iceotter_pelt"),
        ("frostheron", 87, "heron_feather"),
        ("glaciercrab", 88, "glaciercrab_shell"),
        ("bellmammoth", 88, "mammoth_bell"),
        ("auroramanta", 89, "manta_aurora"),
        ("crevasseleviathan", 90, "leviathan_fang"),
    ] {
        assert!(m.slimes.iter().any(|s| s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 500000. && damage > 7000.);
    }
    assert_eq!(m.slimes.iter().filter(|s| is_elite(&s.kind)).count(), 3);
    for q in &m.quests {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "frostwake_hares",
        "frostwake_otters",
        "frostwake_mammoth",
        "frostwake_manta",
        "frostwake_leviathan",
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
    for id in [
        "frostwake_mammoth",
        "frostwake_manta",
        "frostwake_leviathan",
    ] {
        assert!(m.quests.iter().find(|q| q.id == id).unwrap().group);
    }
}
