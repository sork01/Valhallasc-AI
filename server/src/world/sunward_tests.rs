//! Sunward Vale: two bridge routes, six distinct enemies and a sealed root stair.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

const VALE: usize = 20;

#[test]
fn vale_gates_bridges_hub_and_all_encounters_are_reachable() {
    let w = world();
    let m = &w.maps[VALE];
    assert_eq!(
        (m.name.as_str(), m.levels, m.size),
        ("Sunward Vale", Some([65, 70]), 128)
    );
    assert_eq!((m.slimes.len(), m.quests.len()), (42, 9));
    assert!(m.in_city(m.spawn));
    let out = m
        .portals
        .iter()
        .find(|p| p.id == "sun_stormglass_gate")
        .unwrap();
    let back = w.maps[19]
        .portals
        .iter()
        .find(|p| p.id == "stormglass_sun_gate")
        .unwrap();
    assert_eq!((out.to, back.to), (19, VALE));
    for (source, portal) in [(m, out), (&w.maps[19], back)] {
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
    for s in w.slimes.iter().filter(|s| s.zone == VALE) {
        assert!(reached(m, &seen, s.point()), "{}", s.kind);
    }
    for p in [at(out.x, out.y), at(106., 25.), at(48., 72.), at(96., 62.)] {
        assert!(reached(m, &seen, p));
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][VALE - 1];
    assert_eq!(zone["futureInstance"]["status"], "sealed");
    assert_eq!(zone["futureInstance"]["name"], "The Elder Hollow");
    assert_eq!(zone["portals"].as_array().unwrap().len(), 1);
    let objects = zone["objects"].as_array().unwrap();
    let trees = objects
        .iter()
        .filter(|o| {
            matches!(
                o["kind"].as_str(),
                Some("oak_tree" | "birch_tree" | "apple_tree" | "willow_tree")
            )
        })
        .count();
    assert!(trees >= 170, "the vale stays a landscape of real trees");
    assert!(objects.iter().filter(|o| o["kind"] == "water").count() >= 40);
    assert!(m.npcs.iter().any(|n| n.id == "sun_stone"));
    assert_eq!(
        m.npcs
            .iter()
            .find(|n| n.id == "travel_millbridge")
            .unwrap()
            .travel_links,
        ["travel_breakwater"]
    );
    assert!(
        w.maps[19]
            .npcs
            .iter()
            .find(|n| n.id == "travel_breakwater")
            .unwrap()
            .travel_links
            .contains(&"travel_millbridge".to_string())
    );
}

#[test]
fn vale_kinds_have_distinct_rewards_and_elite_quests() {
    let w = world();
    let m = &w.maps[VALE];
    for (kind, level, drop) in [
        ("meadowhare", 65, "hare_whisker"),
        ("sunbacksnail", 66, "sunback_shell"),
        ("brushfox", 67, "fox_tail_tuft"),
        ("spadebadger", 68, "badger_claw"),
        ("honeyjaw", 69, "honeyjaw_comb"),
        ("wickerwarden", 70, "wicker_heart"),
    ] {
        assert!(m.slimes.iter().any(|s| s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 200000. && damage > 3000.);
    }
    assert!(is_elite("honeyjaw") && is_elite("wickerwarden"));
    assert!(!is_elite("spadebadger"));
    for q in &m.quests {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in ["sun_hares", "sun_snails", "sun_honeyjaw", "sun_warden"] {
        assert!(
            m.quests
                .iter()
                .find(|q| q.id == id)
                .unwrap()
                .reward_item
                .is_some()
        );
    }
    for id in ["sun_honeyjaw", "sun_warden"] {
        assert!(m.quests.iter().find(|q| q.id == id).unwrap().group);
    }
}
