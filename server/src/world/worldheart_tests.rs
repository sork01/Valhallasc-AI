//! Veyrroot's open canopy and inhabitable hollow are reachable public maps.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

#[test]
fn canopy_meeting_stone_has_visible_scenery_and_a_clear_hiring_spot() {
    let w = world();
    let map = &w.maps[23];
    let stone = map.npcs.iter().find(|n| n.id == "heart_stone").unwrap();
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let objects = raw["zones"][22]["objects"].as_array().unwrap();
    let object = objects
        .iter()
        .find(|o| o["kind"] == "meetingstone")
        .unwrap();
    let base = at(object["x"].as_f64().unwrap(), object["y"].as_f64().unwrap());
    assert!(base.distance(stone.position_at(0.)) < 2.8);
    let mut foot = stone.position_at(0.);
    map.collide(&mut foot, PLAYER_RADIUS);
    assert!(foot.distance(stone.position_at(0.)) < 1e-6);
    assert_eq!(
        stone
            .offers
            .iter()
            .filter(|o| o.open && o.merc.is_some())
            .count(),
        5
    );
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    assert!(reached(map, &seen, foot));
}

#[test]
fn worldheart_gates_and_both_city_floors_are_reachable() {
    let w = world();
    let jungle = &w.maps[22];
    let outer = &w.maps[23];
    let inner = &w.maps[24];
    assert_eq!(
        (outer.name.as_str(), outer.levels, outer.size),
        ("Veyrroot Canopy", Some([80, 80]), 128)
    );
    assert_eq!(
        (inner.name.as_str(), inner.levels, inner.size),
        ("Veyrroot Heartwood", Some([80, 80]), 96)
    );
    assert_eq!(
        (
            outer.slimes.len(),
            outer.quests.len(),
            inner.slimes.len(),
            inner.quests.len()
        ),
        (0, 7, 0, 4)
    );
    assert!(outer.in_city(at(56., 88.)) && inner.in_city(inner.spawn));
    for (map, id, to) in [
        (jungle, "tangle_worldheart_gate", 23),
        (outer, "canopy_jungle_gate", 22),
        (outer, "canopy_hollow_gate", 24),
        (inner, "hollow_canopy_gate", 23),
        (inner, "heart_seed_gate", 33),
    ] {
        let p = map.portals.iter().find(|p| p.id == id).unwrap();
        assert_eq!(p.to, to);
        let mut foot = at(p.x, p.y);
        map.collide(&mut foot, PLAYER_RADIUS);
        assert!(foot.distance(at(p.x, p.y)) < 1e-6, "{id} blocked");
        let mut arrival = at(p.tx, p.ty);
        w.maps[p.to].collide(&mut arrival, PLAYER_RADIUS);
        assert!(
            arrival.distance(at(p.tx, p.ty)) < 1e-6,
            "{id} arrival blocked"
        );
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == p.to)
                .all(|s| s.point().distance(arrival) >= 8.)
        );
    }
    for (id, map) in [(23, outer), (24, inner)] {
        let seen = flood(map, &blocked(map, &[]), map.spawn);
        for n in &map.npcs {
            assert!(reached(map, &seen, n.position_at(0.)), "{}", n.id);
        }
        for p in &map.portals {
            assert!(reached(map, &seen, at(p.x, p.y)), "{}", p.id);
        }
        for s in w.slimes.iter().filter(|s| s.zone == id) {
            assert!(reached(map, &seen, s.point()), "{}", s.kind);
        }
    }
    let master = outer
        .npcs
        .iter()
        .find(|n| n.id == "travel_veyrroot")
        .unwrap();
    assert!(master.travel_links.contains(&"travel_banyan".to_string()));
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    assert_eq!(raw["zones"][23]["futureInstance"]["name"], "The Seed Vault");
    assert_eq!(raw["zones"][23]["futureInstance"]["status"], "open");
    assert_eq!(inner.portals.len(), 2);
}

#[test]
fn worldheart_creatures_are_reserved_for_instance_and_city_quests_are_peaceful() {
    let w = world();
    for (kind, drop) in [
        ("sapbeetle", "sapbeetle_resin"),
        ("lanternhornet", "hornet_amber"),
        ("mosslemur", "mosslemur_fur"),
        ("barkmimic", "barkmimic_chip"),
    ] {
        assert_eq!(Slime::default_level(kind), 80);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 300000. && damage > 5000.);
    }
    for (map, peaceful) in [(&w.maps[23], true), (&w.maps[24], false)] {
        for q in &map.quests {
            assert_eq!(q.reward_xp, xp_to_level(80) / 10, "{}", q.id);
            if peaceful || matches!(q.id.as_str(), "heart_rings" | "heart_seed_vault") {
                assert!(
                    q.objectives
                        .iter()
                        .all(|o| matches!(o.kind.as_str(), "talk" | "visit")),
                    "{}",
                    q.id
                );
            }
        }
    }
    for id in ["heart_walkways", "heart_lanterns", "heart_market"] {
        assert!(
            w.maps[23]
                .quests
                .iter()
                .find(|q| q.id == id)
                .unwrap()
                .reward_item
                .is_some()
        );
    }
}
