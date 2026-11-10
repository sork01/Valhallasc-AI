//! Heartwood (zone 24) as the main city inside the world-tree on the shapes pilot: its round floor, the services of a main city, the Hollow Arch and the Seed Vault's door, the people who
//! live there, the quests, and the owner's rule that every building is something that could be found inside a big tree (grown or carved wood).
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const HEART: usize = 24;
const WOOD: usize = 23;
const VAULT: usize = 33;
/// every kind of object that may stand in Heartwood: wood, sap-light, living plants and the Meeting Stone: no masonry
const WOODEN: [&str; 17] = [
    "heartwood_core",
    "heart_lamp",
    "root_bench",
    "heart_burl",
    "heart_burl_tall",
    "heart_stall",
    "seed_chapel",
    "amber_library",
    "pith_forge",
    "root_loom",
    "heartwood_vault",
    "hollow_arch",
    "heartwood_column",
    "epiphyte_garden",
    "leaf_lantern",
    "hanging_pod",
    "meetingstone",
];

#[test]
fn heartwood_is_a_round_peaceful_city_with_homes_districts_and_a_living_pith() {
    let w = world();
    let map = &w.maps[HEART];
    assert_eq!(map.name, "Veyrroot Heartwood");
    assert_eq!((map.size, map.levels), (208, Some([80, 80])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(map.in_city(map.spawn) && map.in_city(at(104., 104.)));
    assert_eq!(
        w.slimes.iter().filter(|s| s.zone == HEART).count(),
        0,
        "a city has no enemies"
    );
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][HEART - 1];
    assert_eq!(zone["city"]["name"], "Veyrroot Heartwood");
    assert_eq!(
        zone["regions"]["names"].as_array().unwrap().len(),
        7,
        "the Pith and six districts"
    );
    assert_eq!(zone["futureInstance"]["name"], "The Seed Vault");
    let objects = zone["objects"].as_array().unwrap();
    let homes = objects
        .iter()
        .filter(|o| {
            (o["kind"] == "heart_burl" || o["kind"] == "heart_burl_tall")
                && o.get("label").is_none()
        })
        .count();
    assert!(homes >= 100, "{homes} homes: people live in there");
    // the floor is a disc: the centre is land, the corners are void
    let rows = zone["shapeFloor"].as_array().unwrap();
    let land = |x: usize, y: usize| rows[y].as_str().unwrap().as_bytes()[x] == b'#';
    assert!(land(104, 104) && land(104, 20) && land(104, 190));
    assert!(!land(4, 4) && !land(204, 204) && !land(4, 204) && !land(204, 4));
    // a place to live for each name: at least thirty people
    assert!(map.npcs.len() >= 30, "{} people", map.npcs.len());
}

#[test]
fn every_building_is_grown_or_carved_wood_and_stands_on_the_floor() {
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][HEART - 1];
    for o in zone["objects"].as_array().unwrap() {
        let kind = o["kind"].as_str().unwrap();
        if kind == "void" {
            continue;
        }
        assert!(
            WOODEN.contains(&kind),
            "{kind} is not something found inside a big tree"
        );
        let (x, y) = (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
        assert!(
            ((x - 104.).powi(2) + (y - 104.).powi(2)).sqrt() < 98.,
            "{kind} at {x},{y} is off the floor"
        );
    }
}

#[test]
fn heartwood_has_the_services_of_a_main_city() {
    let w = world();
    let map = &w.maps[HEART];
    let has = |npc: &str, offer: &str| {
        map.npcs
            .iter()
            .find(|n| n.id == npc)
            .unwrap_or_else(|| panic!("no {npc}"))
            .offers
            .iter()
            .any(|o| o.id == offer)
    };
    assert!(has("banker_heartwood", "bank"));
    assert!(has("hw_steward", "stat_reset") && has("hw_steward", "gauntlet"));
    assert!(has("hw_smith", "repair") && has("hw_smith", "fitting"));
    assert!(has("hw_healer", "blessing"));
    assert!(has("hw_trader", "satchel") && has("hw_trader", "buy_cloak_rare"));
    assert!(has("hw_innkeeper", "rest"));
    let stone = map.npcs.iter().find(|n| n.id == "hw_stone").unwrap();
    assert_eq!(
        stone
            .offers
            .iter()
            .filter(|o| o.open && o.merc.is_some())
            .count(),
        5
    );
    assert!(map.npcs.iter().find(|n| n.id == "hw_trader").unwrap().buys);
    let master = map
        .npcs
        .iter()
        .find(|n| n.id == "travel_heartwood")
        .unwrap();
    assert!(master.travel_links.iter().any(|l| l == "travel_veyrroot"));
    assert!(
        w.maps[WOOD]
            .npcs
            .iter()
            .find(|n| n.id == "travel_veyrroot")
            .unwrap()
            .travel_links
            .iter()
            .any(|l| l == "travel_heartwood"),
        "the Rootfoot master links back"
    );
    assert!(
        map.npcs
            .iter()
            .any(|n| n.id == "mailbox_24_veyrroot_heartwood")
    );
    // the old people keep their ids
    for id in [
        "heart_archivist",
        "heart_carver",
        "heart_oracle",
        "heart_custodian",
    ] {
        assert!(map.npcs.iter().any(|n| n.id == id), "{id}");
    }
    // arena trials: nine levels from the steward
    assert_eq!(
        map.quests
            .iter()
            .filter(|q| q.id.starts_with("arena_heart_"))
            .count(),
        9
    );
}

#[test]
fn the_hollow_arch_and_the_seed_vault_door_work_both_ways_and_the_arrivals_are_clear() {
    let w = world();
    for (zone, id, to, back_zone, back_id) in [
        (
            HEART,
            "hollow_canopy_gate",
            WOOD,
            WOOD,
            "canopy_hollow_gate",
        ),
        (HEART, "heart_seed_gate", VAULT, VAULT, "seed_vault_return"),
    ] {
        let p = w.maps[zone]
            .portals
            .iter()
            .find(|p| p.id == id)
            .unwrap()
            .clone();
        assert_eq!(p.to, to, "{id}");
        let mut foot = at(p.x, p.y);
        w.maps[zone].collide(&mut foot, PLAYER_RADIUS);
        assert!(foot.distance(at(p.x, p.y)) < 1e-6, "{id} is blocked");
        let back = w.maps[back_zone]
            .portals
            .iter()
            .find(|q| q.id == back_id)
            .unwrap()
            .clone();
        assert_eq!(back.to, zone, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        let mut a = arrival;
        w.maps[zone].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        assert!(
            arrival.distance(at(p.x, p.y)) < 12.,
            "{back_id} arrives beside {id}"
        );
    }
}

#[test]
fn everyone_and_everything_in_heartwood_can_be_walked_to_from_the_hollow_arch() {
    let w = world();
    let map = &w.maps[HEART];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for p in &map.portals {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    let sane = |x: f64, y: f64| ((x - 104.).powi(2) + (y - 104.).powi(2)).sqrt() < 98.;
    assert!(map.npcs.iter().all(|n| sane(n.x, n.y)));
}

#[test]
fn the_heartwood_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let m = &w.maps[HEART];
    let everywhere: Vec<&str> = w
        .maps
        .iter()
        .flat_map(|z| z.quests.iter().map(|q| q.id.as_str()))
        .collect();
    for q in &m.quests {
        assert!(
            q.requires
                .as_deref()
                .is_none_or(|r| everywhere.contains(&r)),
            "{} requires a quest that exists",
            q.id
        );
        assert!(
            m.npcs.iter().any(|n| n.id == q.npc),
            "{} is given by {}",
            q.id,
            q.npc
        );
        assert!(format!("quest:accept:{}", q.id).len() <= 32, "{}", q.id);
        for o in &q.objectives {
            match o.kind.as_str() {
                "visit" => assert!(
                    m.places.iter().any(|p| p.id == o.target),
                    "{}: no place {}",
                    q.id,
                    o.target
                ),
                "talk" => assert!(
                    w.maps
                        .iter()
                        .any(|z| z.npcs.iter().any(|n| n.id == o.target)),
                    "{}: no person {}",
                    q.id,
                    o.target
                ),
                "bring" => assert!(item(&o.target).is_some(), "{}: no item {}", q.id, o.target),
                _ => {}
            }
        }
    }
    for id in [
        "heart_rings",
        "heart_seed_vault",
        "heart_seed_trials",
        "heart_seed_final",
        "es_20",
        "es_go_20",
    ] {
        assert!(
            m.quests.iter().any(|q| q.id == id),
            "the old {id} keeps its id"
        );
    }
    let new = m.quests.iter().filter(|q| q.id.starts_with("hw_")).count();
    assert!(new >= 14, "{new} new city quests");
    for id in [
        "hw_hollows",
        "hw_resin",
        "hw_panes",
        "hw_blankets",
        "hw_stools",
        "hw_watch",
    ] {
        assert!(
            m.quests
                .iter()
                .find(|q| q.id == id)
                .unwrap()
                .reward_item
                .is_some(),
            "{id}"
        );
    }
    // the city's own errands are peaceful: only talk, visit and bring
    for q in m.quests.iter().filter(|q| q.id.starts_with("hw_")) {
        assert!(
            q.objectives
                .iter()
                .all(|o| matches!(o.kind.as_str(), "talk" | "visit" | "bring")),
            "{}",
            q.id
        );
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
}

#[test]
fn heartwood_is_a_sanctuary() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, HEART, at(104., 104.));
    w.time += 10.;
    let before = w.players[&1].character.hp;
    w.hurt_player(1, 5000., at(104., 104.));
    assert_eq!(w.players[&1].character.hp, before, "no damage in Heartwood");
}

#[test]
fn heartwood_hosts_all_five_festivals_and_the_six_dances_and_dresses_for_each_season() {
    let w = world();
    let map = &w.maps[HEART];
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][HEART - 1];
    // the host: Baker Olle hires fighters for every festival and gives the annual errand
    let host = map
        .npcs
        .iter()
        .find(|n| n.id == "hw_baker")
        .expect("the festival host");
    for season in ["halloween", "christmas", "easter", "solstice", "valentine"] {
        for class in ["warrior", "mage", "assassin", "priest", "hunter"] {
            let id = format!("{season}:hire:{class}");
            assert!(host.offers.iter().any(|o| o.id == id), "{id}");
        }
        let quest = map
            .quests
            .iter()
            .find(|q| q.id == format!("{season}_heart"))
            .unwrap_or_else(|| panic!("{season}_heart"));
        assert_eq!(quest.npc, "hw_baker");
        assert!(quest.objectives.len() >= 3);
        for o in &quest.objectives {
            match o.kind.as_str() {
                "talk" => assert!(
                    map.npcs.iter().any(|n| n.id == o.target),
                    "{}: {}",
                    quest.id,
                    o.target
                ),
                "visit" => assert!(
                    map.places.iter().any(|p| p.id == o.target),
                    "{}: {}",
                    quest.id,
                    o.target
                ),
                _ => {}
            }
        }
    }
    // the dance: one centrepiece per season on clear ground, two laps of radius 1.8 walkable
    let c = at(120., 124.5);
    for season in [
        "halloween",
        "christmas",
        "newyear",
        "valentine",
        "easter",
        "solstice",
    ] {
        let n = map
            .npcs
            .iter()
            .find(|n| n.id == format!("festival_dance_{season}_24"))
            .unwrap_or_else(|| panic!("{season} dance"));
        assert!(at(n.x, n.y).distance(c) < 1e-6);
        for i in 0..64 {
            let a = |k: f64| {
                at(
                    c.x + 1.8 * (k * std::f64::consts::TAU / 64.).cos(),
                    c.y + 1.8 * (k * std::f64::consts::TAU / 64.).sin(),
                )
            };
            assert!(
                map.line_clear(a(i as f64), a(i as f64 + 1.), PLAYER_RADIUS),
                "{season} orbit step {i}"
            );
        }
    }
    // the dressing: dense for every season, nothing on the ground near the dance, nothing on a road
    for key in [
        "seasonDecor",
        "christmasDecor",
        "easterDecor",
        "solsticeDecor",
        "valentineDecor",
    ] {
        let decor = zone[key].as_array().unwrap_or_else(|| panic!("{key}"));
        assert!(decor.len() >= 200, "{key}: {}", decor.len());
        for o in decor {
            let (x, y) = (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
            assert!(
                ((x - 104.).powi(2) + (y - 104.).powi(2)).sqrt() < 98.,
                "{key} decor off the floor"
            );
            if o.get("z").and_then(|z| z.as_f64()).unwrap_or(0.) == 0. {
                assert!(
                    ((x - 120.).powi(2) + (y - 124.5).powi(2)).sqrt() > 3.2,
                    "{key}: ground decor on the dance circle"
                );
            }
        }
    }
    assert!(
        zone["christmasDecor"]
            .as_array()
            .unwrap()
            .iter()
            .any(|o| o["kind"] == "christmasGrandTree")
    );
    assert!(
        zone["solsticeDecor"]
            .as_array()
            .unwrap()
            .iter()
            .any(|o| o["kind"] == "solsticeTable")
    );
}
