//! The Lapis Erg (zone 25, levels 80-85) as an authored desert on the shapes pilot: its data, the Sunward Vale and Veyrroot Canopy gates, the Sunken Astrolabe's door, the wall that
//! covers the Yearwheel (no crossing from either side), Azure Wells, the Astrolabe Rest and three outposts, the quests (holds, visits, brings, kills, the two elite quests) and the new
//! elite with no quest.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const ERG: usize = 25;
const YEARWHEEL: usize = 28;
const ELITES: [(&str, u32); 3] = [
    ("dunecolossus", 84),
    ("mirageroc", 85),
    ("cobaltbasilisk", 83),
];
/// (gate, the zone it leads to, the far gate that leads back); the Astrolabe is a door, the Yearwheel has none
const GATES: [(&str, usize, &str); 1] = [("path_25_20", 20, "path_20_25")];
const HAMLETS: [(&str, &str); 3] = [
    ("wallwatch", "lp_ww_"),
    ("saltpan", "lp_sp_"),
    ("eastwell", "lp_ew_"),
];

fn run(w: &mut World, rx: &mut mpsc::Receiver<Value>, ticks: usize) -> Vec<String> {
    let mut told = vec![];
    for _ in 0..ticks {
        w.step();
        told.extend(lines(rx));
    }
    told
}

#[test]
fn the_lapis_erg_is_a_desert_wedge_with_four_families_three_elites_five_hubs_and_the_astrolabe_door()
 {
    let w = world();
    let map = &w.maps[ERG];
    assert_eq!(map.name, "The Lapis Erg");
    assert_eq!((map.size, map.levels), (296, Some([80, 85])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(map.in_city(map.spawn), "the spawn is Azure Wells");
    assert!(
        !w.maps[23].slimes.is_empty(),
        "the Veyrroot is wild since 2026-11-09"
    );
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == ERG) {
        if spawn.ambush.is_some() {
            assert!(
                w.slimes[id].dead && w.slimes[id].state == "waiting" && w.slimes[id].respawn >= 1e8,
                "an ambusher sleeps"
            );
            continue;
        }
        *live.entry(spawn.kind.as_str()).or_default() += 1;
        assert!(!map.in_city(at(spawn.x, spawn.y)));
    }
    for (kind, floor) in [
        ("sandhopper", 20),
        ("dunefennec", 25),
        ("glassscorpion", 20),
        ("sunvulture", 20),
    ] {
        assert!(live[kind] >= floor, "{kind}: {}", live[kind]);
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind], 1, "{kind}");
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][ERG - 1];
    assert_eq!(zone["city"]["name"], "Azure Wells");
    let mut names: Vec<_> = zone["camps"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["name"].as_str().unwrap())
        .collect();
    names.sort();
    assert_eq!(
        names,
        [
            "Astrolabe Rest",
            "Eastwell Post",
            "Saltpan Post",
            "Wallwatch Post"
        ]
    );
    let masters = map.npcs.iter().filter(|n| n.travel_stop.is_some()).count();
    assert_eq!(
        masters, 5,
        "Azure Wells and four camps each have a Spark master"
    );
    assert_eq!(zone["futureInstance"]["status"], "open");
    assert_eq!(zone["futureInstance"]["name"], "The Sunken Astrolabe");
    let objects = zone["objects"].as_array().unwrap();
    assert_eq!(
        objects
            .iter()
            .filter(|o| o["kind"] == "lapis_oasis")
            .count(),
        3
    );
    assert_eq!(objects.iter().filter(|o| o["kind"] == "water").count(), 3);
    for (kind, floor) in [
        ("lapis_date_palm", 100),
        ("lapis_dunegrass", 150),
        ("lapis_sandstone", 100),
        ("lapis_salt_spire", 50),
    ] {
        assert!(
            objects.iter().filter(|o| o["kind"] == kind).count() >= floor,
            "{kind}"
        );
    }
    // the Spark network is not an island: Azure Wells links the camps, Sunward's master and the Veyrroot Canopy's, and no longer the Yearwheel's
    let master = map
        .npcs
        .iter()
        .find(|n| n.id == "travel_azure_wells")
        .unwrap();
    for id in [
        "travel_millbridge",
        "travel_veyrroot",
        "travel_wallwatch",
        "travel_eastwell",
        "travel_saltpan",
        "travel_astro",
    ] {
        assert!(master.travel_links.iter().any(|l| l == id), "{id}");
    }
    assert!(
        !master.travel_links.iter().any(|l| l == "travel_solhaven"),
        "the Yearwheel is walled off"
    );
    assert!(
        w.maps[23]
            .npcs
            .iter()
            .find(|n| n.id == "travel_veyrroot")
            .unwrap()
            .travel_links
            .iter()
            .any(|l| l == "travel_saltpan")
            || w.maps[23]
                .npcs
                .iter()
                .find(|n| n.id == "travel_rootstair")
                .unwrap()
                .travel_links
                .iter()
                .any(|l| l == "travel_saltpan"),
        "a Veyrroot master links to the nearest master here (across the seam)"
    );
}

#[test]
fn both_rim_gates_are_walked_through_both_ways_the_astrolabe_door_leads_in_and_the_arrivals_are_clear()
 {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in GATES {
        let gate = w.maps[ERG]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        assert_eq!(gate.to, zone, "{gate_id}");
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, ERG, at(gate.x, gate.y));
        w.message(
            1,
            ClientMessage::Move {
                x: gate.x + f64::from(side[0]) * 3.,
                y: gate.y + f64::from(side[1]) * 3.,
            },
        );
        run(&mut w, &mut rx, 40);
        assert_eq!(
            w.players[&1].character.zone, zone,
            "{gate_id} leads to {zone}"
        );
        let back = w.maps[zone]
            .portals
            .iter()
            .find(|p| p.id == back_id)
            .unwrap()
            .clone();
        assert_eq!(back.to, ERG, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        assert!(
            arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
                && arrival.distance(at(gate.x, gate.y)) < 8.,
            "{back_id} arrives beside {gate_id}, clear of its disc"
        );
        let mut a = arrival;
        w.maps[ERG].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == ERG)
                .all(|s| at(s.x, s.y).distance(arrival) > 8.),
            "an enemy stands near the arrival of {back_id}"
        );
        let side = back.walk.expect("a walk-in gate");
        place(&mut w, 1, zone, at(back.x, back.y));
        w.message(
            1,
            ClientMessage::Move {
                x: back.x + f64::from(side[0]) * 3.,
                y: back.y + f64::from(side[1]) * 3.,
            },
        );
        run(&mut w, &mut rx, 40);
        assert_eq!(w.players[&1].character.zone, ERG, "{back_id} returns");
    }
    // the astrolabe's door stands in the Astrolabe Rest, and both its ways out arrive in front of it on free ground
    let door = w.maps[ERG]
        .portals
        .iter()
        .find(|p| p.id == "lapis_astrolabe_gate")
        .unwrap()
        .clone();
    assert_eq!(door.to, 34);
    for back_id in ["sunken_astrolabe_return", "sunken_astrolabe_exit"] {
        let back = w.maps[34].portals.iter().find(|p| p.id == back_id).unwrap();
        assert_eq!(back.to, ERG);
        let arrival = at(back.tx, back.ty);
        assert!(arrival.distance(at(door.x, door.y)) < 14., "{back_id}");
        let mut a = arrival;
        w.maps[ERG].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
    }
}

#[test]
fn the_yearwheel_has_no_crossing_from_either_side_only_a_solid_wall_along_its_whole_border() {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    // no portal, no atlas link, no exit route in either direction
    for p in data["zones"][ERG - 1]["portals"].as_array().unwrap() {
        assert_ne!(
            p["to"], YEARWHEEL,
            "the Lapis Erg has a portal to the Yearwheel"
        );
        assert!(
            p.get("seam").is_none() || p["to"] == 23,
            "no seam but the Veyrroot's"
        );
    }
    for p in data["zones"][YEARWHEEL - 1]["portals"].as_array().unwrap() {
        assert_ne!(p["to"], ERG, "the Yearwheel has a portal to the Lapis Erg");
    }
    for l in data["atlas"]["links"].as_array().unwrap() {
        let pair = (l["a"].as_u64().unwrap(), l["b"].as_u64().unwrap());
        assert!(pair != (25, 28) && pair != (28, 25), "no atlas link");
    }
    let zone = &data["zones"][ERG - 1];
    assert!(
        zone["exitRoutes"]
            .as_array()
            .unwrap()
            .iter()
            .all(|r| r["portal"] != "atlas_25_28")
    );
    // the wall is isometric city art with real collision: ramparts and towers
    let objects = zone["objects"].as_array().unwrap();
    let ramparts: Vec<_> = objects.iter().filter(|o| o["kind"] == "rampart").collect();
    let towers: Vec<_> = objects.iter().filter(|o| o["kind"] == "tower").collect();
    assert!(ramparts.len() >= 50, "{} ramparts", ramparts.len());
    assert!(towers.len() >= 4, "{} towers", towers.len());
    let edge = zone["shape"]["edges"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["kind"] == "shared" && e["other"] == YEARWHEEL)
        .expect("the Yearwheel border");
    let pts: Vec<(f64, f64)> = edge["points"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (p[0].as_f64().unwrap(), p[1].as_f64().unwrap()))
        .collect();
    let dist = |x: f64, y: f64| {
        pts.windows(2)
            .map(|s| {
                let (a, b) = (s[0], s[1]);
                let (dx, dy) = (b.0 - a.0, b.1 - a.1);
                let t = (((x - a.0) * dx + (y - a.1) * dy) / (dx * dx + dy * dy)).clamp(0., 1.);
                ((x - a.0 - t * dx).powi(2) + (y - a.1 - t * dy).powi(2)).sqrt()
            })
            .fold(f64::MAX, f64::min)
    };
    // every wall piece stands about 1.7 tiles inside the border, and neighbouring pieces overlap so nothing slips between them
    let mut pieces: Vec<(f64, f64)> = ramparts
        .iter()
        .chain(towers.iter())
        .map(|o| (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap()))
        .collect();
    for &(x, y) in &pieces {
        let d = dist(x, y);
        assert!(
            (1.0..=2.6).contains(&d),
            "a wall piece {d:.2} tiles from the border"
        );
    }
    pieces.sort_by(|a, b| a.0.total_cmp(&b.0));
    for pair in pieces.windows(2) {
        let gap = ((pair[0].0 - pair[1].0).powi(2) + (pair[0].1 - pair[1].1).powi(2)).sqrt();
        assert!(
            gap <= 3.2,
            "a gap of {gap:.1} tiles in the wall at {:?}",
            pair[0]
        );
    }
    // a walker pushed toward the border from 6 tiles inland, at a dozen places along it, never gets within a body of it
    let w = world();
    let map = &w.maps[ERG];
    let mut tried = 0;
    for i in 1..12 {
        let k = ((pts.len() - 1) as f64 * i as f64 / 12.) as usize;
        let (a, b) = (pts[k], pts[(k + 1).min(pts.len() - 1)]);
        let (mx, my) = (a.0 + (b.0 - a.0) * 0.5, a.1 + (b.1 - a.1) * 0.5);
        let ln = ((b.0 - a.0).powi(2) + (b.1 - a.1).powi(2)).sqrt();
        let (mut nx, mut ny) = (-(b.1 - a.1) / ln, (b.0 - a.0) / ln);
        // the land side is the one nearer the zone's middle
        let far = |s: f64| (mx + nx * s - 150.).powi(2) + (my + ny * s - 150.).powi(2);
        if far(5.) > far(-5.) {
            nx = -nx;
            ny = -ny;
        }
        let mut foot = at(mx + nx * 6., my + ny * 6.);
        let mut c = foot;
        map.collide(&mut c, PLAYER_RADIUS);
        if c.distance(foot) > 1e-6 {
            continue; // a scenery object stands on this sample point
        }
        tried += 1;
        for _ in 0..80 {
            map.walk(&mut foot, at(-nx, -ny), 0.5, PLAYER_RADIUS);
        }
        assert!(
            dist(foot.x, foot.y) > 1.2,
            "a walker got to {:.2} tiles from the Yearwheel border at {mx:.0},{my:.0}",
            dist(foot.x, foot.y)
        );
    }
    assert!(tried >= 6, "only {tried} places could be tried");
}

#[test]
fn everyone_and_everything_in_the_lapis_erg_can_be_walked_to_from_azure_wells() {
    let w = world();
    let map = &w.maps[ERG];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == ERG) {
        assert!(
            reached(map, &open, at(s.x, s.y)),
            "{} #{id} is cut off",
            s.kind
        );
    }
    for (gate_id, _, _) in GATES {
        let g = map.portals.iter().find(|p| p.id == gate_id).unwrap();
        let side = g.walk.unwrap();
        let inside = at(g.x - f64::from(side[0]) * 6., g.y - f64::from(side[1]) * 6.);
        assert!(reached(map, &open, inside), "{gate_id} is cut off");
    }
    let door = map
        .portals
        .iter()
        .find(|p| p.id == "lapis_astrolabe_gate")
        .unwrap();
    assert!(
        reached(map, &open, at(door.x, door.y + 2.)),
        "the astrolabe door is cut off"
    );
}

#[test]
fn oasis_shores_block_walking_through_water_and_keep_routes_open() {
    let w = world();
    let map = &w.maps[ERG];
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let objects = raw["zones"][ERG - 1]["objects"].as_array().unwrap();
    for water in objects.iter().filter(|o| o["kind"] == "water") {
        let center = at(water["x"].as_f64().unwrap(), water["y"].as_f64().unwrap());
        let r = water["r"].as_f64().unwrap();
        let mut inside = center;
        map.collide(&mut inside, PLAYER_RADIUS);
        assert!(inside.distance(center) >= r + PLAYER_RADIUS - 1e-6);
        for side in [-1., 1.] {
            let mut foot = at(center.x + side * (r + PLAYER_RADIUS + 0.1), center.y);
            for _ in 0..60 {
                map.walk(&mut foot, at(-side, 0.), 0.1, PLAYER_RADIUS);
                assert!(foot.distance(center) >= r + PLAYER_RADIUS - 1e-6);
            }
        }
    }
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for portal in &map.portals {
        assert!(reached(map, &seen, at(portal.x, portal.y)), "{}", portal.id);
    }
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox_and_the_astrolabe_has_a_camp()
 {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (key, prefix) in HAMLETS {
        let map = &w.maps[ERG];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(
            master
                .travel_links
                .iter()
                .any(|l| l == "travel_azure_wells")
        );
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_25_{key}")),
            "a mailbox at {key}"
        );
        let people: Vec<_> = map
            .npcs
            .iter()
            .filter(|n| n.id.starts_with(prefix))
            .collect();
        assert_eq!(people.len(), 3, "{key}");
        assert_eq!(
            people.iter().filter(|n| n.buys).count(),
            1,
            "one trader at {key}"
        );
        let camp = map
            .camps
            .iter()
            .find(|k| {
                at(master.x, master.y).distance(at((k.x0 + k.x1) / 2., (k.y0 + k.y1) / 2.)) < 12.
            })
            .unwrap_or_else(|| panic!("{key} is a camp"));
        for n in &people {
            assert!(
                n.x >= camp.x0 && n.x <= camp.x1 && n.y >= camp.y0 && n.y <= camp.y1,
                "{} stands in the camp",
                n.id
            );
        }
        for n in people.iter().filter(|n| !n.buys) {
            assert!(
                map.quests.iter().any(|q| q.npc == n.id),
                "{} gives a quest",
                n.id
            );
        }
        let (x, y) = ((camp.x0 + camp.x1) / 2., (camp.y0 + camp.y1) / 2.);
        place(&mut w, 1, ERG, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
    // the Astrolabe Rest at the lens: the seer and the Meeting Stone moved into it, with its own master and mailbox
    let map = &w.maps[ERG];
    let rest_master = map.npcs.iter().find(|n| n.id == "travel_astro").unwrap();
    let camp = map
        .camps
        .iter()
        .find(|k| {
            at(rest_master.x, rest_master.y).distance(at((k.x0 + k.x1) / 2., (k.y0 + k.y1) / 2.))
                < 12.
        })
        .expect("the Astrolabe Rest");
    for id in [
        "lapis_seer",
        "lapis_stone",
        "travel_astro",
        "mailbox_25_astro",
    ] {
        let n = map.npcs.iter().find(|n| n.id == id).expect(id);
        assert!(
            n.x >= camp.x0 && n.x <= camp.x1 && n.y >= camp.y0 && n.y <= camp.y1,
            "{id} stands in the Astrolabe Rest"
        );
    }
    let door = map
        .portals
        .iter()
        .find(|p| p.id == "lapis_astrolabe_gate")
        .unwrap();
    assert!(
        door.x >= camp.x0 - 2.
            && door.x <= camp.x1 + 2.
            && door.y >= camp.y0 - 4.
            && door.y <= camp.y1,
        "the astrolabe door stands at the camp"
    );
}

#[test]
fn the_lapis_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let map = &w.maps[ERG];
    let new = [
        "lapis_wl_hold",
        "lapis_rounds",
        "lapis_ww_walk",
        "lapis_ww_fur",
        "lapis_ww_hold",
        "lapis_ww_dune",
        "lapis_sp_walk",
        "lapis_sp_glass",
        "lapis_sp_hold",
        "lapis_sp_glare",
        "lapis_ew_walk",
        "lapis_ew_quill",
        "lapis_ew_hold",
        "lapis_ew_crag",
    ];
    for id in new {
        let q = map
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap_or_else(|| panic!("no quest {id}"));
        assert!((80..=85).contains(&q.level), "{id} level {}", q.level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{id}");
        assert!(q.reward_gold >= 1000, "{id}");
        assert!(map.npcs.iter().any(|n| n.id == q.npc), "{id} has a giver");
        assert!(q.requires.is_some(), "{id} follows another quest");
        assert!(
            map.quests
                .iter()
                .any(|p| Some(&p.id) == q.requires.as_ref()),
            "{id} needs a quest that exists"
        );
        assert!(("quest:accept:".len() + id.len()) <= 32);
        for o in &q.objectives {
            match o.kind.as_str() {
                "kill" => {
                    let live = w
                        .spawns
                        .iter()
                        .filter(|s| s.zone == ERG && s.kind == o.target && s.ambush.is_none())
                        .count();
                    assert!(
                        live >= 2 * o.count as usize,
                        "{id} hunts {} ({live} live)",
                        o.target
                    );
                }
                "talk" => assert!(map.npcs.iter().any(|n| n.id == o.target), "{id}"),
                "bring" => assert_eq!(
                    item(&o.target).map(|i| i.kind.as_str()),
                    Some("material"),
                    "{id}"
                ),
                "visit" => assert!(map.places.iter().any(|p| p.id == o.target), "{id}"),
                "hold" => assert!(
                    map.places
                        .iter()
                        .any(|p| p.id == o.target && p.waves.len() == 2),
                    "{id} holds {}",
                    o.target
                ),
                other => panic!("{id} has an unknown objective {other}"),
            }
        }
    }
    for (id, kind) in [
        ("lapis_colossus", "dunecolossus"),
        ("lapis_roc", "mirageroc"),
    ] {
        let q = map.quests.iter().find(|q| q.id == id).unwrap();
        assert!(q.group);
        assert!(q.objectives.len() == 1 && q.objectives[0].target == kind);
        let reward = item(q.reward_item.as_deref().unwrap()).unwrap();
        assert_eq!(reward.rarity, "rare", "{id}");
    }
    assert!(
        !map.quests
            .iter()
            .any(|q| q.objectives.iter().any(|o| o.target == "cobaltbasilisk")),
        "the Cobalt Basilisk has no quest"
    );
    for hold in ["lp_wl_m", "lp_ww_m", "lp_sp_m", "lp_ew_m"] {
        let p = map.places.iter().find(|p| p.id == hold).unwrap();
        for wave in ['a', 'b'] {
            let tag = format!("{hold}#{wave}");
            let sleepers: Vec<_> = w
                .spawns
                .iter()
                .filter(|s| s.zone == ERG && s.ambush.as_deref() == Some(tag.as_str()))
                .collect();
            assert!(sleepers.len() >= 2, "{tag}");
            assert!(
                sleepers
                    .iter()
                    .all(|s| at(s.x, s.y).distance(at(p.x, p.y)) < 16.),
                "{tag} sleeps beside its circle"
            );
        }
    }
    for id in [
        "lapis_welcome",
        "lapis_hoppers",
        "lapis_fennecs",
        "lapis_scorpions",
        "lapis_vultures",
        "lapis_colossus",
        "lapis_roc",
        "lapis_astrolabe",
        "lapis_astro_trials",
        "lapis_astro_final",
        "lapis_patrol",
        "lapis_onward",
        "entry_astro",
        "es_21",
        "es_go_21",
    ] {
        assert!(map.quests.iter().any(|q| q.id == id), "{id}");
    }
    assert_eq!(map.quests.len(), 29, "15 old quests and 14 new ones");
}

#[test]
fn the_three_elites_have_stats_materials_names_and_stand_clear_of_everything_walked_to() {
    for (kind, level) in ELITES {
        assert!(is_elite(kind), "{kind}");
        assert_eq!(Slime::default_level(kind), level, "{kind}");
        let i = item(material(kind)).expect("the material is in the catalog");
        assert_eq!((i.kind.as_str(), i.rarity.as_str()), ("material", "common"));
        let s = Slime::with_level(
            0,
            &SlimeSpawn {
                ambush: None,
                x: 5.,
                y: 5.,
                kind: kind.into(),
                zone: ERG,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 1_000_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("cobaltbasilisk"), "basilisk_scale");
    let w = world();
    let map = &w.maps[ERG];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == ERG && s.kind == kind)
            .unwrap();
        let awareness = Slime::attack_profile(kind).3 + 3.;
        for n in &map.npcs {
            assert!(
                at(n.x, n.y).distance(at(e.x, e.y)) > awareness,
                "{kind} near {}",
                n.id
            );
        }
        for p in &map.places {
            assert!(
                at(p.x, p.y).distance(at(e.x, e.y)) > awareness,
                "{kind} near {}",
                p.id
            );
        }
    }
    let find = |k: &str| {
        w.spawns
            .iter()
            .find(|s| s.zone == ERG && s.kind == k)
            .unwrap()
    };
    assert!(
        find("dunecolossus").x < 100. && find("dunecolossus").y < 130.,
        "the colossus walks the dune in the north-west"
    );
    assert!(
        find("mirageroc").x > 180.,
        "the roc nests on the crag in the east"
    );
    assert!(
        find("cobaltbasilisk").x > 200. && find("cobaltbasilisk").y > 200.,
        "the basilisk lies in the Glass Dunes in the south-east"
    );
}

#[test]
fn the_empty_seat_moves_with_its_bells_and_the_mailboxes_stand_on_free_ground() {
    let w = world();
    let map = &w.maps[ERG];
    let bells: Vec<_> = (0..3)
        .map(|i| {
            map.places
                .iter()
                .find(|p| p.id == format!("es_21_{i}"))
                .unwrap_or_else(|| panic!("bell {i}"))
        })
        .collect();
    // the three bells keep their old triangle (they must all be rung within thirty seconds)
    let d01 = at(bells[0].x, bells[0].y).distance(at(bells[1].x, bells[1].y));
    let d12 = at(bells[1].x, bells[1].y).distance(at(bells[2].x, bells[2].y));
    assert!(
        (d01 - 10.).abs() < 1.5 && (d12 - 12.4).abs() < 1.5,
        "{d01} {d12}"
    );
    for (box_id, master_id) in [
        ("mailbox_25_azure_wells", "travel_azure_wells"),
        ("mailbox_25_wallwatch", "travel_wallwatch"),
        ("mailbox_25_eastwell", "travel_eastwell"),
        ("mailbox_25_saltpan", "travel_saltpan"),
        ("mailbox_25_astro", "travel_astro"),
    ] {
        let b = map.npcs.iter().find(|n| n.id == box_id).expect(box_id);
        let m = map
            .npcs
            .iter()
            .find(|n| n.id == master_id)
            .expect(master_id);
        let (point, anchor) = (at(b.x, b.y), at(m.x, m.y));
        let mut resolved = point;
        map.collide(&mut resolved, 0.6);
        assert!(point.distance(resolved) < 0.01, "{box_id} is blocked");
        assert!(
            map.line_clear(anchor, point, 0.4),
            "{box_id} has no clear approach from {master_id}"
        );
    }
    let directory: Value =
        serde_json::from_str(include_str!("../../../world/mailboxes.txt")).unwrap();
    let mine = directory
        .as_array()
        .unwrap()
        .iter()
        .filter(|d| d["zone"] == ERG)
        .count();
    assert_eq!(
        mine, 5,
        "the directory lists Azure Wells, the Astrolabe Rest and three outposts"
    );
}

#[test]
fn lapis_enemies_materials_elites_and_quest_rewards_are_registered() {
    let w = world();
    let m = &w.maps[ERG];
    for (kind, level, drop) in [
        ("sandhopper", 80, "sandhopper_chitin"),
        ("dunefennec", 81, "fennec_fur"),
        ("glassscorpion", 82, "scorpion_glass"),
        ("sunvulture", 83, "vulture_quill"),
        ("cobaltbasilisk", 83, "basilisk_scale"),
        ("dunecolossus", 84, "colossus_core"),
        ("mirageroc", 85, "roc_plume"),
    ] {
        assert!(w.spawns.iter().any(|s| s.zone == ERG && s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 400000. && damage > 6000.);
    }
    assert!(is_elite("dunecolossus") && is_elite("mirageroc") && is_elite("cobaltbasilisk"));
    assert!(!is_elite("glassscorpion"));
    for q in &m.quests {
        if q.id.starts_with("es_go_") || q.id == "entry_astro" {
            continue; // a hand-off pays nothing, and the door key pays only experience
        }
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "lapis_hoppers",
        "lapis_fennecs",
        "lapis_colossus",
        "lapis_roc",
        "lapis_wl_hold",
        "lapis_rounds",
        "lapis_ww_hold",
        "lapis_ww_dune",
        "lapis_sp_hold",
        "lapis_sp_glare",
        "lapis_ew_hold",
        "lapis_ew_crag",
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
    for id in ["lapis_colossus", "lapis_roc"] {
        assert!(m.quests.iter().find(|q| q.id == id).unwrap().group);
    }
}
