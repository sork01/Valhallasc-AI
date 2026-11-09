//! The Frostwake Shelf (zone 26, levels 85-90) as an authored glacier shelf on the shapes pilot: its data, the seam to Cairnspine with a road across, the Sunward Vale and Stormglass
//! gates, the wall that covers the Yearwheel (no crossing from either side), Frostwake Station and three outposts, the quests (holds, visits, brings, kills, the three elite quests)
//! and the three elites.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const SHELF: usize = 26;
const CAIRN: usize = 27;
const YEARWHEEL: usize = 28;
const ELITES: [(&str, u32); 3] = [
    ("bellmammoth", 88),
    ("auroramanta", 89),
    ("crevasseleviathan", 90),
];
/// (gate, the zone it leads to, the far gate that leads back); Cairnspine is a seam and the Yearwheel has no crossing
const GATES: [(&str, usize, &str); 1] = [("path_26_19", 19, "path_19_26")]; // the Sunward border is a seam since 2026-11-09
const HAMLETS: [(&str, &str, &str); 3] = [
    ("bellward", "fw_bw_", "frostwake_bellkeeper"),
    ("aurora", "fw_au_", "frostwake_skywatcher"),
    ("ribwatch", "fw_rw_", "frostwake_ribkeeper"),
];

fn run(w: &mut World, rx: &mut mpsc::Receiver<Value>, ticks: usize) -> Vec<String> {
    let mut told = vec![];
    for _ in 0..ticks {
        w.step();
        told.extend(lines(rx));
    }
    told
}

fn spot(w: &World, id: &str) -> (f64, f64) {
    let p = w.maps[SHELF]
        .places
        .iter()
        .find(|p| p.id == id)
        .unwrap_or_else(|| panic!("no place {id}"));
    (p.x, p.y)
}

fn camp_centre(_w: &World, name: &str) -> (f64, f64) {
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let c = raw["zones"][SHELF - 1]["camps"]
        .as_array()
        .unwrap()
        .iter()
        .find(|c| c["name"] == name)
        .unwrap_or_else(|| panic!("no camp {name}"));
    let f = |k: &str| c[k].as_f64().unwrap();
    ((f("x0") + f("x1")) / 2., (f("y0") + f("y1")) / 2.)
}

#[test]
fn the_shelf_is_a_tall_glacier_with_four_families_three_elites_four_hubs_and_no_dungeon() {
    let w = world();
    let map = &w.maps[SHELF];
    assert_eq!(map.name, "Frostwake Shelf");
    assert_eq!((map.size, map.levels), (312, Some([85, 90])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(map.in_city(map.spawn), "the spawn is Frostwake Station");
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == SHELF) {
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
        ("snowhare", 30),
        ("iceotter", 18),
        ("frostheron", 25),
        ("glaciercrab", 20),
    ] {
        assert!(live[kind] >= floor, "{kind}: {}", live[kind]);
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind], 1, "{kind}");
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][SHELF - 1];
    assert_eq!(zone["city"]["name"], "Frostwake Station");
    let mut names: Vec<_> = zone["camps"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["name"].as_str().unwrap())
        .collect();
    names.sort();
    assert_eq!(names, ["Aurora Post", "Bellward Post", "Ribwatch Camp"]);
    let masters = map.npcs.iter().filter(|n| n.travel_stop.is_some()).count();
    assert_eq!(
        masters, 4,
        "the Station and three camps each have a Spark master"
    );
    assert!(
        zone.get("futureInstance").is_none(),
        "the shelf has no dungeon door"
    );
    let objects = zone["objects"].as_array().unwrap();
    for (kind, floor) in [
        ("frostwake_snowdrift", 150),
        ("frostwake_ice_spire", 100),
        ("frostwake_snow_pine", 60),
        ("frostwake_iceflower", 40),
        ("frostwake_peak", 12),
        ("frostwake_crevasse", 12),
        ("frostwake_lodge", 9),
    ] {
        assert!(
            objects.iter().filter(|o| o["kind"] == kind).count() >= floor,
            "{kind}"
        );
    }
    // the Spark network is not an island: the Station links the camps and Cairnspine's masters, and no longer the Yearwheel's
    let master = map
        .npcs
        .iter()
        .find(|n| n.id == "travel_frostwake")
        .unwrap();
    for id in [
        "travel_bellward",
        "travel_aurora",
        "travel_ribwatch",
        "travel_stormgate",
    ] {
        assert!(master.travel_links.iter().any(|l| l == id), "{id}");
    }
    for id in ["travel_rimehold", "travel_springmere", "travel_solhaven"] {
        assert!(
            !master.travel_links.iter().any(|l| l == id),
            "{id}: the Yearwheel is walled off"
        );
    }
    // every Spark link of this zone's masters is answered from the other side (both halves of the seam)
    for zone_id in [SHELF, CAIRN] {
        for n in w.maps[zone_id]
            .npcs
            .iter()
            .filter(|n| n.travel_stop.is_some())
        {
            for l in &n.travel_links {
                let other = w
                    .maps
                    .iter()
                    .flat_map(|z| z.npcs.iter())
                    .find(|m| &m.id == l)
                    .unwrap_or_else(|| panic!("{} links to {l}, which does not exist", n.id));
                assert!(
                    other.travel_links.contains(&n.id),
                    "{} <-> {l} is not reciprocal",
                    n.id
                );
            }
        }
    }
    assert!(
        w.maps[CAIRN].npcs.iter().any(|n| n
            .travel_links
            .iter()
            .any(|l| map.npcs.iter().any(|m| &m.id == l))),
        "a Cairnspine master links across the seam"
    );
}

#[test]
fn the_borders_to_cairnspine_and_sunward_are_seams_with_a_road_across_and_stormglass_stays_a_gate()
{
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in data["zones"][zi - 1]["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == SHELF || to == SHELF) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> = [(26, 27), (27, 26), (20, 26), (26, 20)].into();
    assert_eq!(
        pairs, want,
        "one seam each to Cairnspine and Sunward Vale, seen from both sides"
    );
    let w = world();
    let zone = &data["zones"][SHELF - 1];
    let mine = w.maps[SHELF]
        .portals
        .iter()
        .find(|p| p.to == CAIRN)
        .expect("the seam portal");
    let theirs = w.maps[CAIRN]
        .portals
        .iter()
        .find(|p| p.to == SHELF)
        .expect("the far seam portal");
    assert!(
        (theirs.x - mine.tx).abs() < 1e-6 && (theirs.y - mine.ty).abs() < 1e-6,
        "the two portals face each other"
    );
    assert!(
        (mine.y - 115.5).abs() < 1.5 && (theirs.y - 118.5).abs() < 1.5,
        "the seam crosses at the row where Cairnspine's east road ends: {} {}",
        mine.y,
        theirs.y
    );
    let near = zone["paths"].as_array().unwrap().iter().any(|road| {
        road.as_array().unwrap().iter().any(|q| {
            let (qx, qy) = (q[0].as_f64().unwrap(), q[1].as_f64().unwrap());
            ((qx - mine.x).powi(2) + (qy - mine.y).powi(2)).sqrt() < 2.
        })
    });
    assert!(near, "a road of this zone meets the seam");
    assert!(
        w.maps[SHELF]
            .portals
            .iter()
            .all(|p| p.to == CAIRN || p.to == 19 || p.to == 20),
        "the Cairnspine seam and the Stormglass and Sunward gates are the only crossings"
    );
    for (gate, to, _) in GATES {
        let g = w.maps[SHELF].portals.iter().find(|p| p.id == gate).unwrap();
        assert!(g.walk.is_some() && g.to == to, "{gate} is a rim gate");
    }
}

#[test]
fn a_hero_crosses_the_seam_to_cairnspine_and_comes_back() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let p = w.maps[SHELF]
        .portals
        .iter()
        .find(|p| p.to == CAIRN)
        .unwrap()
        .clone();
    // the seam runs north-south here: Cairnspine lies to the west
    place(&mut w, 1, SHELF, at(p.x + 3., p.y));
    w.message(
        1,
        ClientMessage::Move {
            x: p.x - 4.,
            y: p.y,
        },
    );
    run(&mut w, &mut rx, 80);
    assert_eq!(
        w.players[&1].character.zone, CAIRN,
        "walking over the seam to Cairnspine"
    );
    let q = w.maps[CAIRN]
        .portals
        .iter()
        .find(|q| q.to == SHELF)
        .unwrap()
        .clone();
    place(&mut w, 1, CAIRN, at(q.x - 3., q.y));
    w.message(
        1,
        ClientMessage::Move {
            x: q.x + 4.,
            y: q.y,
        },
    );
    run(&mut w, &mut rx, 80);
    assert_eq!(
        w.players[&1].character.zone, SHELF,
        "walking back over the seam"
    );
}

#[test]
fn both_rim_gates_are_walked_through_both_ways_and_the_arrivals_are_clear() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in GATES {
        let gate = w.maps[SHELF]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        assert_eq!(gate.to, zone, "{gate_id}");
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, SHELF, at(gate.x, gate.y));
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
        assert_eq!(back.to, SHELF, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        assert!(
            arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
                && arrival.distance(at(gate.x, gate.y)) < 8.,
            "{back_id} arrives beside {gate_id}, clear of its disc"
        );
        let mut a = arrival;
        w.maps[SHELF].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == SHELF)
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
        assert_eq!(w.players[&1].character.zone, SHELF, "{back_id} returns");
    }
}

#[test]
fn the_yearwheel_has_no_crossing_from_either_side_only_a_solid_wall_along_its_whole_border() {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    // no portal, no atlas link, no exit route in either direction
    for p in data["zones"][SHELF - 1]["portals"].as_array().unwrap() {
        assert_ne!(
            p["to"], YEARWHEEL,
            "the shelf has a portal to the Yearwheel"
        );
    }
    for p in data["zones"][YEARWHEEL - 1]["portals"].as_array().unwrap() {
        assert_ne!(p["to"], SHELF, "the Yearwheel has a portal to the shelf");
    }
    for r in data["zones"][YEARWHEEL - 1]["exitRoutes"]
        .as_array()
        .unwrap()
    {
        assert_ne!(r["portal"], "path_28_26", "no exit route to the shelf");
    }
    for l in data["atlas"]["links"].as_array().unwrap() {
        let pair = (l["a"].as_u64().unwrap(), l["b"].as_u64().unwrap());
        assert!(pair != (26, 28) && pair != (28, 26), "no atlas link");
    }
    // the Yearwheel stays reachable some other way (Sunward Vale)
    assert!(
        data["zones"][YEARWHEEL - 1]["portals"]
            .as_array()
            .unwrap()
            .iter()
            .any(|p| p["to"] == 20),
        "the Yearwheel still opens on Sunward Vale"
    );
    let zone = &data["zones"][SHELF - 1];
    assert!(
        zone["exitRoutes"]
            .as_array()
            .unwrap()
            .iter()
            .all(|r| r["portal"] != "path_26_28")
    );
    // the wall is isometric city art with real collision: ramparts and towers
    let objects = zone["objects"].as_array().unwrap();
    let ramparts: Vec<_> = objects.iter().filter(|o| o["kind"] == "rampart").collect();
    let towers: Vec<_> = objects.iter().filter(|o| o["kind"] == "tower").collect();
    assert!(ramparts.len() >= 100, "{} ramparts", ramparts.len());
    assert!(towers.len() >= 8, "{} towers", towers.len());
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
    pieces.sort_by(|a, b| a.1.total_cmp(&b.1));
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
    let map = &w.maps[SHELF];
    let mut tried = 0;
    for i in 1..12 {
        let k = ((pts.len() - 1) as f64 * i as f64 / 12.) as usize;
        let (a, b) = (pts[k], pts[(k + 1).min(pts.len() - 1)]);
        let (mx, my) = (a.0 + (b.0 - a.0) * 0.5, a.1 + (b.1 - a.1) * 0.5);
        let ln = ((b.0 - a.0).powi(2) + (b.1 - a.1).powi(2)).sqrt();
        let (mut nx, mut ny) = (-(b.1 - a.1) / ln, (b.0 - a.0) / ln);
        // the land side is the one nearer the zone's middle
        let far = |s: f64| (mx + nx * s - 156.).powi(2) + (my + ny * s - 156.).powi(2);
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
fn everyone_and_everything_on_the_shelf_can_be_walked_to_from_the_station() {
    let w = world();
    let map = &w.maps[SHELF];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == SHELF) {
        assert!(
            reached(map, &open, at(s.x, s.y)),
            "{} #{id} is cut off",
            s.kind
        );
    }
    for p in &map.portals {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (gate_id, _, _) in GATES {
        let g = map.portals.iter().find(|p| p.id == gate_id).unwrap();
        let side = g.walk.unwrap();
        let inside = at(g.x - f64::from(side[0]) * 6., g.y - f64::from(side[1]) * 6.);
        assert!(reached(map, &open, inside), "{gate_id} is cut off");
    }
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (key, prefix, old) in HAMLETS {
        let map = &w.maps[SHELF];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(master.travel_links.iter().any(|l| l == "travel_frostwake"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_26_{key}")),
            "a mailbox at {key}"
        );
        let mut people: Vec<_> = map
            .npcs
            .iter()
            .filter(|n| n.id.starts_with(prefix))
            .collect();
        people.extend(map.npcs.iter().filter(|n| n.id == old));
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
        place(&mut w, 1, SHELF, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
    // the Station keeps the old shelf people (their ids are saved progress); the Meeting Stone stands at the Ribwatch Camp
    let map = &w.maps[SHELF];
    for id in [
        "frostwake_captain",
        "frostwake_healer",
        "frostwake_surveyor",
        "frostwake_trader",
        "frostwake_scout",
        "travel_frostwake",
        "mailbox_26_frostwake_station",
    ] {
        let n = map.npcs.iter().find(|n| n.id == id).expect(id);
        assert!(map.in_city(at(n.x, n.y)), "{id} stands in the Station");
    }
    let stone = map.npcs.iter().find(|n| n.id == "frostwake_stone").unwrap();
    let (cx, cy) = camp_centre(&w, "Ribwatch Camp");
    assert!(
        (stone.x - cx).abs() <= 12. && (stone.y - cy).abs() <= 11.,
        "the Meeting Stone stands in the Ribwatch Camp"
    );
}

#[test]
fn the_shelf_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let m = &w.maps[SHELF];
    let ids: Vec<&str> = m.quests.iter().map(|q| q.id.as_str()).collect();
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
        for o in &q.objectives {
            match o.kind.as_str() {
                "visit" => assert!(
                    m.places.iter().any(|p| p.id == o.target),
                    "{}: no place {}",
                    q.id,
                    o.target
                ),
                "hold" => assert!(
                    m.places
                        .iter()
                        .any(|p| p.id == o.target && !p.waves.is_empty()),
                    "{}: no hold circle {}",
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
                "kill" => assert!(
                    w.spawns.iter().any(|s| s.kind == o.target),
                    "{}: nothing to kill: {}",
                    q.id,
                    o.target
                ),
                "bring" => assert!(item(&o.target).is_some(), "{}: no item {}", q.id, o.target),
                _ => {}
            }
        }
    }
    assert!(m.quests.len() >= 27, "{} quests", m.quests.len());
    for id in [
        "frostwake_welcome",
        "frostwake_hares",
        "frostwake_otters",
        "frostwake_herons",
        "frostwake_crabs",
        "frostwake_mammoth",
        "frostwake_manta",
        "frostwake_leviathan",
        "frostwake_aurora",
        "frostwake_patrol",
        "frostwake_onward",
        "es_22",
        "es_go_22",
    ] {
        assert!(ids.contains(&id), "the old {id} keeps its id");
    }
    let new = ids.iter().filter(|i| i.starts_with("fws_")).count();
    assert_eq!(new, 14, "fourteen new quests");
    for q in &m.quests {
        assert!(format!("quest:accept:{}", q.id).len() <= 32, "{}", q.id);
    }
    for id in [
        "frostwake_mammoth",
        "frostwake_manta",
        "frostwake_leviathan",
    ] {
        let q = m.quests.iter().find(|q| q.id == id).unwrap();
        assert!(q.group && q.reward_item.is_some(), "{id}");
        assert!(!q.reward_choices.is_empty(), "{id} offers class choices");
    }
    // the old text that sent players across the Erg is gone
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    for q in raw["zones"][SHELF - 1]["quests"].as_array().unwrap() {
        assert!(
            !q["description"].as_str().unwrap().contains("Erg"),
            "{} still names the Erg",
            q["id"]
        );
    }
}

/// every compass word in a quest or person text is checked against the coordinates (a word that lies is a bug)
#[test]
fn the_compass_words_in_the_texts_match_where_things_stand() {
    let w = world();
    let m = &w.maps[SHELF];
    let (bx, by) = camp_centre(&w, "Bellward Post");
    let (ax, ay) = camp_centre(&w, "Aurora Post");
    let (rx, ry) = camp_centre(&w, "Ribwatch Camp");
    let city = m.city.as_ref().unwrap();
    let st = ((city.x0 + city.x1) / 2., (city.y0 + city.y1) / 2.);
    let (x, y) = spot(&w, "fw_bells");
    assert!(
        x < bx && y > by,
        "the Mammoth Bells are south-west of the Bellward Post"
    );
    let (x, y) = spot(&w, "fw_fissures");
    assert!(
        x > bx && y > by,
        "the Blue Fissures are south-east of the Bellward Post"
    );
    let (x, y) = spot(&w, "fw_cliff");
    assert!(
        y > ay && (x - ax).abs() < (y - ay),
        "the Eastern Cliff is south of the Aurora Post"
    );
    let (x, y) = spot(&w, "frostwake_pool");
    assert!(
        x < ax && y > ay,
        "the pool is south-west of the Aurora Post"
    );
    let (x, y) = spot(&w, "frostwake_obelisk");
    assert!(
        x > ax && y < ay,
        "the obelisk is north-east of the Aurora Post"
    );
    let (x, y) = spot(&w, "frostwake_rib");
    assert!(
        x > rx && (y - ry).abs() < (x - rx),
        "the Deep Ice Rib is east of the Ribwatch Camp"
    );
    let (_, y) = spot(&w, "fw_crack");
    assert!(y < ry, "the Northern Crack is north of the Ribwatch Camp");
    let (x, _) = spot(&w, "fws_st_m");
    assert!(x < st.0, "the Station Lantern is west of the Station");
    let (x, _) = spot(&w, "fws_bw_m");
    assert!(x < bx, "the Bellward Circle is west of the Bellward Post");
    let (x, y) = spot(&w, "fws_au_m");
    assert!(
        x < ax && (y - ay).abs() < (ax - x),
        "the Aurora Circle is west of the Aurora Post"
    );
    let (x, y) = spot(&w, "fws_rw_m");
    assert!(
        x < rx && y > ry,
        "the Ribwatch Circle is south-west of the Ribwatch Camp"
    );
    // the elites
    let find = |k: &str| {
        w.spawns
            .iter()
            .find(|s| s.zone == SHELF && s.kind == k)
            .unwrap()
    };
    let bells = spot(&w, "fw_bells");
    assert!(
        find("bellmammoth").x < bells.0,
        "the Mammoth stands west of the Mammoth Bells"
    );
    assert!(
        find("auroramanta").x > ax && find("auroramanta").y > ay,
        "the Manta is south-east of the Aurora Post"
    );
    assert!(
        find("crevasseleviathan").x > spot(&w, "frostwake_rib").0,
        "the Leviathan lies beyond the rib"
    );
    // the three outposts lie north of the Station: the Bellward Post nearest, the Aurora Post and the Ribwatch Camp beyond
    assert!(bx > st.0 && by < st.1 && ay < by && ry < by);
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
                zone: SHELF,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 1_000_000., "{kind} {}", s.max_hp);
    }
    let w = world();
    let map = &w.maps[SHELF];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == SHELF && s.kind == kind)
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
    assert_eq!(
        map.slimes
            .iter()
            .filter(|s| is_elite(&s.kind) && !s.kind.starts_with("es_foe_"))
            .count(),
        3,
        "three elites, all three with a quest (the Empty Seat's echo foe is a story encounter, not an elite of the shelf)"
    );
}

#[test]
fn the_empty_seats_echo_stands_east_of_the_bellward_post_with_its_foe_asleep() {
    let w = world();
    let m = &w.maps[SHELF];
    let (bx, by) = camp_centre(&w, "Bellward Post");
    let p = m.places.iter().find(|p| p.id == "es_22_m").unwrap();
    assert!(
        p.x > bx && (p.y - by).abs() < p.x - bx,
        "the echo circle is east of the Bellward Post"
    );
    let open = flood(m, &blocked(m, &[]), m.spawn);
    assert!(reached(m, &open, at(p.x, p.y)));
    let foes: Vec<_> = w
        .spawns
        .iter()
        .enumerate()
        .filter(|(_, s)| s.zone == SHELF && s.kind == "es_foe_22")
        .collect();
    assert_eq!(foes.len(), 1, "one echo foe");
    let (id, foe) = foes[0];
    assert!(at(foe.x, foe.y).distance(at(p.x, p.y)) < 4.);
    assert!(
        w.slimes[id].dead && w.slimes[id].respawn >= 1e8,
        "it sleeps until the echo is called"
    );
    for n in m.npcs.iter().filter(|n| n.id.starts_with("mailbox_26_")) {
        let mut foot = at(n.x, n.y);
        m.collide(&mut foot, PLAYER_RADIUS);
        assert!(foot.distance(at(n.x, n.y)) < 1e-6, "{} is blocked", n.id);
        assert!(reached(m, &open, at(n.x, n.y)));
    }
}

#[test]
fn the_shelf_enemies_materials_elites_and_quest_rewards_are_registered() {
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
        assert!(w.spawns.iter().any(|s| s.zone == SHELF && s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 500000. && damage > 7000.);
    }
    assert!(!is_elite("snowhare"));
    for q in &m.quests {
        if q.id.starts_with("es_go_") {
            continue; // a hand-off pays nothing
        }
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "frostwake_hares",
        "frostwake_otters",
        "frostwake_mammoth",
        "frostwake_manta",
        "frostwake_leviathan",
        "fws_st_hold",
        "fws_rounds",
        "fws_bw_hold",
        "fws_bw_fissures",
        "fws_au_hold",
        "fws_au_pools",
        "fws_rw_hold",
        "fws_rw_crabs",
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
}

#[test]
fn every_exit_route_follows_clear_floor() {
    let w = world();
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    for route in data["zones"][SHELF - 1]["exitRoutes"].as_array().unwrap() {
        let points = route["points"].as_array().unwrap();
        for pair in points.windows(2) {
            let p = |v: &Value| at(v[0].as_f64().unwrap(), v[1].as_f64().unwrap());
            assert!(
                w.maps[SHELF].line_clear(p(&pair[0]), p(&pair[1]), PLAYER_RADIUS),
                "the exit route of {} is blocked: {:?} -> {:?}",
                route["portal"],
                pair[0],
                pair[1]
            );
        }
    }
}
