//! The Yearwheel is a single 400-square outdoor map with four seasonal courts.
use super::wyrd_tests::{at, world};
use super::*;

const YEAR: usize = 28;
const KINDS: [(&str, u32, &str); 16] = [
    ("brooknewt", 95, "newt_ribbon"),
    ("sundarter", 96, "sundarter_scale"),
    ("acornmimic", 97, "amber_acorn"),
    ("snowstoat", 98, "stoat_silverfur"),
    ("bloomtortoise", 95, "bloom_shell"),
    ("petalchimera", 96, "chimera_petal"),
    ("rainseraph", 97, "seraph_rainfeather"),
    ("glasslion", 96, "glasslion_mane"),
    ("sunwheel", 97, "sunwheel_cog"),
    ("firephoenix", 98, "phoenix_ember"),
    ("lanternowl", 97, "lanternowl_eye"),
    ("harvestreaper", 98, "reaper_scythe_shard"),
    ("ambermantis", 99, "amber_mantis_claw"),
    ("rimesaber", 97, "rimesaber_fang"),
    ("snowgiant", 98, "snowgiant_heart"),
    ("longnightwyrm", 99, "longnight_scale"),
];

#[test]
fn four_seasons_hubs_travel_and_spring_dungeon() {
    let w = world();
    let m = &w.maps[YEAR];
    assert_eq!(
        (m.name.as_str(), m.size, m.levels),
        ("The Yearwheel", 400, Some([95, 99]))
    );
    assert!(m.size * m.size > 4 * 192 * 192);
    assert_eq!(
        (m.npcs.len(), m.quests.len(), m.slimes.len()),
        (30, 36, 156)
    );
    for q in &m.quests {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let z = &raw["zones"][YEAR - 1];
    assert_eq!(z["camps"].as_array().unwrap().len(), 3);
    let future = z["futureInstances"].as_array().unwrap();
    assert_eq!(future.len(), 4);
    assert_eq!(future[0]["status"], "open");
    assert!(future.iter().all(|door| door["status"] == "open"));
    assert_eq!(m.portals.len(), 6);
    assert!(
        m.portals
            .iter()
            .any(|p| p.id == "year_bloom_descent" && p.to == 36)
    );
    assert!(
        m.portals
            .iter()
            .any(|p| p.id == "year_solar_descent" && p.to == 37)
    );
    assert!(
        m.portals
            .iter()
            .any(|p| p.id == "year_amber_descent" && p.to == 38)
    );
    assert!(
        m.portals
            .iter()
            .any(|p| p.id == "year_solstice_descent" && p.to == 39)
    );
    let season_stops = [
        "travel_springmere",
        "travel_solhaven",
        "travel_harvestwatch",
        "travel_rimehold",
    ];
    for stop in season_stops {
        let n = m.npcs.iter().find(|n| n.id == stop).unwrap();
        assert!(n.travel_links.len() >= 2);
        assert!(
            n.travel_links
                .iter()
                .all(|link| link.starts_with("travel_"))
        );
    }
    assert!(
        m.npcs
            .iter()
            .find(|n| n.id == "travel_springmere")
            .unwrap()
            .travel_links
            .contains(&"travel_boulderwatch".to_string())
    );
    let out = m
        .portals
        .iter()
        .find(|p| p.id == "year_cairn_gate")
        .unwrap();
    let into = w.maps[27]
        .portals
        .iter()
        .find(|p| p.id == "cairn_year_gate")
        .unwrap();
    assert_eq!((out.to, into.to), (27, YEAR));
    for portal in [out, into] {
        let mut foot = at(portal.x, portal.y);
        w.maps[if portal.id == "year_cairn_gate" {
            YEAR
        } else {
            27
        }]
        .collide(&mut foot, PLAYER_RADIUS);
        assert!(foot.distance(at(portal.x, portal.y)) < 1e-6);
        let target = &w.maps[portal.to];
        let arrival = at(portal.tx, portal.ty);
        let mut clear = arrival;
        target.collide(&mut clear, PLAYER_RADIUS);
        assert!(clear.distance(arrival) < 1e-6);
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == portal.to)
                .all(|s| s.point().distance(arrival) >= 8.)
        );
    }
}

#[test]
fn seasonal_enemies_loot_and_elite_courts() {
    let w = world();
    let m = &w.maps[YEAR];
    for (kind, level, drop) in KINDS {
        assert!(m.slimes.iter().any(|s| s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
    }
    assert_eq!(m.slimes.iter().filter(|s| is_elite(&s.kind)).count(), 12);
}
