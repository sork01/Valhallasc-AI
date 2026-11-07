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
    assert_eq!((m.name.as_str(), m.size), ("Nacrehold", 248));
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
    assert_eq!(m.npcs.len(), 40);
    assert_eq!(m.quests.len(), 32);
    // Every dungeon added since keeps its copies after the file zones, so the count only grows.
    assert!(w.maps.len() >= 49, "{} maps", w.maps.len());
    assert_eq!(w.maps.iter().find_map(|m| m.template), Some(5));
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
    for n in people.iter().filter(|n| n["art"] != "stone" && n.get("look").is_some()) {
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
        8,
        "the Deep seam, three Cathedral entrances and the four gates (Astralhollow, the Orrery, the Crags, Bifrost)"
    );
    let stone = z["objects"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["kind"] == "meetingstone")
        .unwrap();
    let dist = (stone["x"].as_f64().unwrap() - 128.).hypot(stone["y"].as_f64().unwrap() - 50.);
    assert!(dist < 25., "stone is beside the entrance");
}

#[test]
fn nacre_deep_border_is_a_seam_and_every_other_crossing_is_a_walk_in_gate() {
    let w = world();
    let m = &w.maps[NACRE];
    let seams: Vec<_> = m.portals.iter().filter(|p| p.seam.is_some()).collect();
    assert_eq!(seams.len(), 1, "one seam");
    assert_eq!(seams[0].to, DEEP);
    for to in [1, 7, 13, 15] {
        let p = m.portals.iter().find(|p| p.to == to).unwrap();
        assert!(p.seam.is_none() && p.walk.is_some(), "the way to {to} is a gate");
        // the arrival six tiles inside the neighbour's gate stands on free ground and clear of every gate disc
        let n = &w.maps[to];
        let arrival = at(p.tx, p.ty);
        let mut c = arrival;
        n.collide(&mut c, PLAYER_RADIUS);
        assert!(c.distance(arrival) < 1e-6, "arrival from Nacrehold in zone {to}");
    }
    // the Deep keeps no gate to Nacrehold: its border is the seam
    assert!(w.maps[DEEP].portals.iter().all(|p| p.to != NACRE || p.seam.is_some()));
    // every crossing that arrives here lands on free ground inside the sanctuary
    for (zi, n) in w.maps.iter().enumerate() {
        for p in n.portals.iter().filter(|p| p.to == NACRE && p.seam.is_none()) {
            let arrival = at(p.tx, p.ty);
            let mut c = arrival;
            m.collide(&mut c, PLAYER_RADIUS);
            assert!(c.distance(arrival) < 1e-6, "{} (zone {zi}) arrives in an obstacle", p.id);
            assert!(m.in_city(arrival), "{} arrives outside the sanctuary", p.id);
        }
    }
}

#[test]
fn nacre_new_places_and_quests_walk_the_new_shape() {
    let w = world();
    let m = &w.maps[NACRE];
    for id in ["nacre_tideway", "nacre_plaza", "nacre_way_crags", "nacre_way_orrery", "nacre_way_astral", "nacre_way_bifrost", "nacre_reef_west", "nacre_reef_south", "nacre_reef_east"] {
        assert!(m.places.iter().any(|p| p.id == id), "{id}");
    }
    let five = m.quests.iter().find(|q| q.id == "nacre_five_ways").unwrap();
    assert_eq!(five.objectives.len(), 5);
    // the Tideway pad lies on the open promenade, between the city and the Deep
    let pad = m.places.iter().find(|p| p.id == "nacre_tideway").unwrap();
    assert!(pad.y < 44.);
    // no person stands within 22 tiles of the Deep border: a seam draws ground, scenery and enemies of the other side, not people
    let seam = m.portals.iter().find(|p| p.seam.is_some()).unwrap().seam.as_ref().unwrap();
    for n in m.npcs.iter().filter(|n| !n.id.starts_with("festival_dance_")) {
        let d = seam.distance(at(n.x, n.y));
        assert!(d >= 22., "{} stands {d:.1} from the Deep border", n.id);
    }
}

#[test]
fn nacre_quests_have_valid_targets_prerequisites_and_level_table_rewards() {
    let w = world();
    let m = &w.maps[NACRE];
    assert_eq!(
        m.quests.iter().filter(|q| q.repeatable && !q.id.contains("halloween") && !q.id.contains("christmas") && !q.id.contains("easter") && !q.id.contains("solstice") && !q.id.contains("valentine") && !q.id.starts_with("arena_") && !q.id.starts_with("es_")).count(),
        1
    );
    for q in &m.quests {
        assert!(m.npcs.iter().any(|n| n.id == q.npc));
        if q.reward_xp != 0 || !q.id.starts_with("es_go_") {
            // (the Empty Seat's rewardless hand-offs pay nothing)
            assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
        }
        if let Some(id) = &q.requires {
            // the Empty Seat chapter chain continues from the previous zone's chapter
            assert!(q.id.starts_with("es_") || m.quests.iter().any(|p| p.id == *id), "{}", q.id);
        }
        for o in &q.objectives {
            assert!(
                match o.kind.as_str() {
                    "talk" => m.npcs.iter().any(|n| n.id == o.target),
                    "visit" | "memory" => m.places.iter().any(|p| p.id == o.target),
                    "bring" => crate::items::item(&o.target).is_some(),
                    "kill" => m
                        .portals
                        .iter()
                        .any(|p| w.maps[p.to].slimes.iter().any(|s| s.kind == o.target)),
                    "reach" => w.maps.iter().any(|area| area.name == o.target),
                    "gauntlet" => q.gauntlet_level().is_some(),
                    _ => q.id.starts_with("es_"), // the Empty Seat has its own objective kinds (tested in empty_seat)
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
    // the Deep (Keelhaven) and Astralhollow stay linked; the shapes pilot added the Crags, Bifrost and the Orrery (every neighbour with a master)
    for id in ["travel_keelhaven", "travel_astralhollow"] {
        assert!(master.travel_links.iter().any(|l| l == id), "{id}");
    }
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
