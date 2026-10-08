//! Nacrehold: the safe merfolk city, its real offers/visits, tideway and future instance landmark.
use super::wyrd_tests::{at, blocked, calm, drain, flood, join, place, reached, world};
use super::*;

const NACRE: usize = 9;
const DEEP: usize = 8;

fn stand(w: &mut World, id: &str) {
    let n = w.maps[NACRE].npcs.iter().find(|n| n.id == id).unwrap();
    place(w, 1, NACRE, n.position_at(w.time));
    w.time += 0.6;
}

#[test]
fn nacre_city_is_large_safe_and_has_120_distinct_addressed_homes() {
    let w = world();
    let m = &w.maps[NACRE];
    assert_eq!((m.name.as_str(), m.size), ("Nacrehold", 192));
    assert!(m.levels.is_none() && m.copies == 0 && m.template.is_none());
    assert!(m.slimes.is_empty() && !w.slimes.iter().any(|s| s.zone == NACRE));
    assert!(m.in_city(m.spawn));
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let z = &raw["zones"][NACRE - 1];
    let houses: Vec<_> = z["objects"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["kind"] == "nacrehouse")
        .collect();
    assert_eq!(houses.len(), 120);
    let names: std::collections::BTreeSet<_> = houses
        .iter()
        .map(|o| o["label"].as_str().unwrap())
        .collect();
    assert_eq!(names.len(), 120);
    assert_eq!(m.npcs.len(), 30);
    assert_eq!(m.quests.len(), 9);
    assert_eq!(w.maps.len(), 29);
    assert_eq!(w.maps[17].template, Some(5));
}

#[test]
fn nacre_every_house_door_person_place_and_swim_route_is_reachable() {
    let w = world();
    let m = &w.maps[NACRE];
    let seen = flood(m, &blocked(m, &[]), m.spawn);
    for n in &m.npcs {
        assert!(reached(m, &seen, n.position_at(0.)), "{}", n.id);
        for t in 0..600 {
            let p = n.position_at(t as f64 * 0.5);
            let mut c = p;
            m.collide(&mut c, PLAYER_RADIUS);
            assert!(c.distance(p) < 1e-6, "{} swimmer at {t}", n.id);
        }
    }
    for p in &m.places {
        assert!(reached(m, &seen, at(p.x, p.y)), "{}", p.id);
    }
    for o in m
        .objects
        .iter()
        .filter(|o| o.width == 3.4 && o.depth == 2.6)
    {
        let depth = o.depth;
        assert!(
            reached(m, &seen, at(o.x, o.y + depth / 2. + 1.)),
            "door {},{}",
            o.x,
            o.y
        );
        let mut p = at(o.x, o.y);
        m.collide(&mut p, PLAYER_RADIUS);
        assert!(p.distance(at(o.x, o.y)) > 1., "house must block movement");
    }
}

#[test]
fn nacre_all_people_are_merfolk_except_the_stone_and_the_cathedral_has_three_open_wings() {
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let z = &raw["zones"][NACRE - 1];
    let people = z["npcs"].as_array().unwrap();
    for n in people.iter().filter(|n| n["art"] != "stone") {
        assert_eq!(n["look"]["species"], "merfolk");
        assert!(n["look"]["female"].is_boolean());
    }
    let plan = &z["futureInstance"];
    assert_eq!(plan["name"], "The Drowned Cathedral");
    assert_eq!(plan["status"], "open");
    let warden = z["npcs"]
        .as_array()
        .unwrap()
        .iter()
        .find(|n| n["id"] == "nacre_warden")
        .unwrap();
    let dialogue = warden["dialogue"].as_str().unwrap();
    assert!(
        dialogue.contains("level 40")
            && dialogue.contains("Coral Reliquary")
            && dialogue.contains("Grand Nave")
            && !dialogue.contains("sealed")
    );
    assert_eq!(
        (plan["level"].as_u64(), plan["players"].as_u64()),
        (None, Some(5))
    );
    assert_eq!(
        z["portals"].as_array().unwrap().len(),
        5,
        "Tideway, three Cathedral entrances and the Astralhollow Starway"
    );
    let stone = z["objects"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["kind"] == "meetingstone")
        .unwrap();
    let dist = (stone["x"].as_f64().unwrap() - 96.).hypot(stone["y"].as_f64().unwrap() - 24.);
    assert!(dist < 18., "stone is beside the entrance");
}

#[test]
fn nacre_tideway_is_clear_safe_paired_and_walked_in_both_directions_without_bounce() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    let down = w.maps[DEEP]
        .portals
        .iter()
        .find(|p| p.id == "nacre_gate")
        .unwrap()
        .clone();
    let up = w.maps[NACRE].portals[0].clone();
    assert_eq!((down.to, up.to), (NACRE, DEEP));
    for p in [&down, &up] {
        let m = &w.maps[p.to];
        let arrival = at(p.tx, p.ty);
        let mut c = arrival;
        m.collide(&mut c, PLAYER_RADIUS);
        assert!(c.distance(arrival) < 1e-6);
        assert!(
            m.portals
                .iter()
                .all(|g| arrival.distance(at(g.x, g.y)) > g.r + 0.5)
        );
        assert!(m.slimes.iter().all(|s| arrival.distance(at(s.x, s.y)) > 8.));
    }
    place(&mut w, 1, DEEP, at(down.x, down.y));
    w.step();
    assert_eq!(w.players[&1].character.zone, NACRE);
    for _ in 0..60 {
        w.step();
    }
    assert_eq!(w.players[&1].character.zone, NACRE);
    place(&mut w, 1, NACRE, at(up.x, up.y));
    w.step();
    assert_eq!(w.players[&1].character.zone, DEEP);
}

#[test]
fn nacre_quests_have_valid_targets_prerequisites_and_level_table_rewards() {
    let w = world();
    let m = &w.maps[NACRE];
    assert_eq!(m.quests.iter().filter(|q| q.repeatable).count(), 1);
    for q in &m.quests {
        assert!(m.npcs.iter().any(|n| n.id == q.npc));
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10);
        if let Some(id) = &q.requires {
            assert!(m.quests.iter().any(|p| p.id == *id));
        }
        for o in &q.objectives {
            assert!(
                match o.kind.as_str() {
                    "talk" => m.npcs.iter().any(|n| n.id == o.target),
                    "visit" => m.places.iter().any(|p| p.id == o.target),
                    "bring" => crate::items::item(&o.target).is_some(),
                    _ => false,
                },
                "{} {}",
                q.id,
                o.target
            );
        }
    }
}

#[test]
fn nacre_welcome_uses_real_talks_requires_acceptance_and_claims_once() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    stand(&mut w, "nacre_healer");
    w.interact(1, "nacre_healer", None);
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .all(|g| g.id != "nacre_welcome")
    );
    stand(&mut w, "nacre_envoy");
    w.interact(1, "nacre_envoy", Some("quest:accept:nacre_welcome"));
    for id in [
        "nacre_healer",
        "nacre_trader",
        "nacre_gardener",
        "nacre_warden",
    ] {
        stand(&mut w, id);
        w.interact(1, id, None);
    }
    let g = w.players[&1]
        .character
        .quests
        .iter()
        .find(|g| g.id == "nacre_welcome")
        .unwrap();
    assert_eq!(g.counts, [1, 1, 1, 1]);
    let def = w.maps[NACRE].quests[0].clone();
    let before = w.players[&1].character.gold;
    stand(&mut w, "nacre_envoy");
    w.interact(1, "nacre_envoy", Some("quest:claim:nacre_welcome"));
    assert_eq!(w.players[&1].character.gold, before + def.reward_gold);
    stand(&mut w, "nacre_envoy");
    w.interact(1, "nacre_envoy", Some("quest:claim:nacre_welcome"));
    assert_eq!(w.players[&1].character.gold, before + def.reward_gold);
    assert!(drain(&mut rx).iter().any(|v| v["type"] == "dialogue"));
}

#[test]
fn nacre_meetingstone_hires_for_gold_and_refuses_remote_requests() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.gold = 500;
    let spawn = w.maps[NACRE].spawn;
    place(&mut w, 1, NACRE, spawn);
    w.interact(1, "nacre_stone", Some("merc_priest"));
    assert!(!w.players.values().any(|p| p.merc.is_some()));
    assert_eq!(w.players[&1].character.gold, 500);
    stand(&mut w, "nacre_stone");
    w.interact(1, "nacre_stone", Some("merc_priest"));
    assert_eq!(w.players[&1].character.gold, 250);
    let m = w.players.values().find(|p| p.merc.is_some()).unwrap();
    assert_eq!(m.character.zone, NACRE);
    assert_eq!(m.character.look.class, Class::Priest);
    stand(&mut w, "nacre_stone");
    w.interact(1, "nacre_stone", Some("merc_dismiss"));
    assert!(!w.players.values().any(|p| p.merc.is_some()));
}

#[test]
fn nacre_travel_stop_has_a_reciprocal_link_and_discovery_is_authoritative() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let master = w.maps[NACRE]
        .npcs
        .iter()
        .find(|n| n.id == "travel_nacrehold")
        .unwrap();
    assert_eq!(
        master.travel_links,
        ["travel_keelhaven", "travel_astralhollow"]
    );
    assert!(
        w.maps[DEEP]
            .npcs
            .iter()
            .find(|n| n.id == "travel_keelhaven")
            .unwrap()
            .travel_links
            .contains(&master.id)
    );
    w.interact(1, "travel_nacrehold", None);
    assert!(
        !w.players[&1]
            .character
            .travel_stops
            .iter()
            .any(|id| id == "travel_nacrehold")
    );
    stand(&mut w, "travel_nacrehold");
    w.interact(1, "travel_nacrehold", None);
    assert!(
        w.players[&1]
            .character
            .travel_stops
            .iter()
            .any(|id| id == "travel_nacrehold")
    );
}
