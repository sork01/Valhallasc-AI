//! Asterion and the Moonwell: geography, party instance, quest hub and final boss rewards.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const CITY: usize = 17;
const WELL: usize = 18;

#[test]
fn asterion_is_a_reachable_city_of_distinct_homes_people_and_services() {
    let w = world();
    let city = &w.maps[CITY];
    assert_eq!((city.name.as_str(), city.size), ("Asterion", 180));
    assert!(city.slimes.is_empty() && city.levels.is_none() && city.in_city(city.spawn));
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let houses: Vec<_> = raw["zones"][CITY - 1]["objects"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["kind"] == "aetherhouse")
        .collect();
    assert!(houses.len() >= 120);
    let labels: std::collections::BTreeSet<_> = houses
        .iter()
        .map(|o| o["label"].as_str().unwrap())
        .collect();
    assert_eq!(labels.len(), houses.len());
    assert_eq!(city.npcs.iter().filter(|n| n.route.len() > 1).count(), 10);
    assert_eq!(city.quests.len(), 6);
    let seen = flood(city, &blocked(city, &[]), city.spawn);
    for n in &city.npcs {
        for t in [0., 10., 60., 140.] {
            let p = n.position_at(t);
            assert!(reached(city, &seen, p), "{} at {t}", n.id);
            let mut q = p;
            city.collide(&mut q, PLAYER_RADIUS);
            assert!(q.distance(p) < 1e-6, "{} intersects scenery at {t}", n.id);
        }
    }
    for p in &city.portals {
        assert!(reached(city, &seen, at(p.x, p.y)), "{}", p.id);
    }
    let master = city
        .npcs
        .iter()
        .find(|n| n.id == "travel_asterion")
        .unwrap();
    assert_eq!(master.travel_links, ["travel_lamplight"]);
    assert!(
        w.maps[16].npcs.iter().any(|n| n.id == "travel_lamplight"
            && n.travel_links.contains(&"travel_asterion".to_string()))
    );
}

#[test]
fn moonwell_has_four_private_copies_safe_arrivals_and_a_unique_boss_drop() {
    let w = world();
    let well = &w.maps[WELL];
    assert_eq!(
        (
            well.name.as_str(),
            well.min_level,
            well.players,
            well.copies
        ),
        ("The Moonwell", 60, 5, 4)
    );
    assert_eq!(well.final_boss, "moonwell_echo");
    assert_eq!(w.instances.iter().filter(|i| i.template == WELL).count(), 4);
    assert_eq!(w.maps.len(), 34);
    let seen = flood(well, &blocked(well, &[]), well.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == WELL) {
        assert!(reached(well, &seen, s.point()), "{}", s.kind);
        assert!(s.point().distance(well.spawn) >= 8.);
    }
    for p in &well.portals {
        assert!(reached(well, &seen, at(p.x, p.y)), "{}", p.id);
        let mut a = at(p.tx, p.ty);
        w.maps[p.to].collide(&mut a, PLAYER_RADIUS);
        assert!(
            a.distance(at(p.tx, p.ty)) < 1e-6,
            "{} arrival blocked",
            p.id
        );
    }
    assert!(is_boss("moonwell_echo"));
    assert_eq!(material("moonwell_echo"), "moonwell_shard");
    for slots in boss_slots("moonwell_echo") {
        let piece = boss_piece_for("moonwell_echo", slots, 0.5).unwrap();
        assert_eq!((piece.required_level, piece.rarity.as_str()), (60, "rare"));
    }
}

#[test]
fn moonwell_stairs_enter_a_private_copy_and_return_to_asterion() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 60;
    place(&mut w, 1, CITY, at(125., 93.));
    w.time = 10.;
    w.use_portal(1);
    let copy = w.players[&1].character.zone;
    assert_eq!(w.instance_at(copy).unwrap().template, WELL);
    assert!(w.instance_at(copy).unwrap().active);
    place(&mut w, 1, copy, at(14., 64.));
    w.time += 4.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, CITY);
}
