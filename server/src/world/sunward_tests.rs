//! Sunward Vale (zone 20, levels 65-70) as an authored river valley on the shapes pilot: its data, the six seams (the Stormglass Flats, the Ribbonwild, the Tanglecrown, the Veyrroot
//! Canopy, the Lapis Erg and the Frostwake Shelf) with a road across each, the wall along the Yearwheel border with its one vaulted opening, Millbridge and three outposts, the quests
//! (holds, visits, brings, kills, the two elite quests) and the three elites.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const VALE: usize = 20;
const YEARWHEEL: usize = 28;
/// the six shaped neighbours: every border to them is a seam
const PARTNERS: [usize; 6] = [19, 21, 22, 23, 25, 26];
const ELITES: [(&str, u32); 3] = [("honeyjaw", 69), ("wickerwarden", 70), ("harrowox", 69)];
/// (outpost, the prefix of its new people, its old person, if any)
const HAMLETS: [(&str, &str, &str); 3] = [
    ("honeywood", "sv_hw_", ""),
    ("wickerfield", "sv_wf_", ""),
    ("elderroot", "sv_er_", "sun_keeper"),
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
    let p = w.maps[VALE]
        .places
        .iter()
        .find(|p| p.id == id)
        .unwrap_or_else(|| panic!("no place {id}"));
    (p.x, p.y)
}

fn camp_centre(name: &str) -> (f64, f64) {
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let z = &raw["zones"][VALE - 1];
    let c = if z["city"]["name"] == name {
        &z["city"]
    } else {
        z["camps"]
            .as_array()
            .unwrap()
            .iter()
            .find(|c| c["name"] == name)
            .unwrap_or_else(|| panic!("no camp {name}"))
    };
    let f = |k: &str| c[k].as_f64().unwrap();
    ((f("x0") + f("x1")) / 2., (f("y0") + f("y1")) / 2.)
}

/// a place that stands on a building or a landmark (the Hollow gate, the hive, the wicker post) is reached from beside it
fn reached_near(map: &Map, open: &[bool], x: f64, y: f64, r: f64) -> bool {
    [(0., 0.), (r, 0.), (-r, 0.), (0., r), (0., -r)]
        .iter()
        .any(|(dx, dy)| reached(map, open, at(x + dx, y + dy)))
}

fn border_dist(pts: &[(f64, f64)], x: f64, y: f64) -> f64 {
    pts.windows(2)
        .map(|s| {
            let (a, b) = (s[0], s[1]);
            let (dx, dy) = (b.0 - a.0, b.1 - a.1);
            let t = (((x - a.0) * dx + (y - a.1) * dy) / (dx * dx + dy * dy)).clamp(0., 1.);
            ((x - a.0 - t * dx).powi(2) + (y - a.1 - t * dy).powi(2)).sqrt()
        })
        .fold(f64::MAX, f64::min)
}

#[test]
fn the_vale_is_a_broad_river_valley_with_four_families_three_elites_four_hubs_and_the_hollow_door()
{
    let w = world();
    let map = &w.maps[VALE];
    assert_eq!(map.name, "Sunward Vale");
    assert_eq!((map.size, map.levels), (352, Some([65, 70])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(map.in_city(map.spawn), "the spawn is Millbridge");
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == VALE) {
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
        ("meadowhare", 60),
        ("sunbacksnail", 50),
        ("brushfox", 40),
        ("spadebadger", 40),
    ] {
        assert!(live[kind] >= floor, "{kind}: {}", live[kind]);
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind], 1, "{kind}");
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][VALE - 1];
    assert_eq!(zone["city"]["name"], "Millbridge");
    let mut names: Vec<_> = zone["camps"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["name"].as_str().unwrap())
        .collect();
    names.sort();
    assert_eq!(
        names,
        ["Elderroot Camp", "Honeywood Steading", "Wickerfield Post"]
    );
    let masters = map.npcs.iter().filter(|n| n.travel_stop.is_some()).count();
    assert_eq!(
        masters, 4,
        "Millbridge and the three camps each have a Spark master"
    );
    // the Elder Hollow stays the dungeon door, north of Elderroot Camp
    assert_eq!(zone["futureInstance"]["status"], "open");
    assert_eq!(zone["futureInstance"]["name"], "The Elder Hollow");
    let door = map
        .portals
        .iter()
        .find(|p| p.id == "sun_elder_gate")
        .expect("the Hollow door");
    assert_eq!(door.to, 30);
    let (ex, ey) = camp_centre("Elderroot Camp");
    assert!(
        (door.x - ex).abs() < 3. && door.y < ey - 11.,
        "the door stands north of Elderroot Camp"
    );
    let objects = zone["objects"].as_array().unwrap();
    for (kind, floor) in [
        ("oak_tree", 120),
        ("birch_tree", 30),
        ("apple_tree", 40),
        ("willow_tree", 8),
        ("hawthorn_bush", 200),
        ("wildflowers", 300),
        ("haystack", 10),
        ("water", 60),
        ("meadow_cottage", 9),
        ("meadow_mill", 1),
        ("stone_bridge", 2),
        ("elder_hollow_gate", 1),
    ] {
        assert!(
            objects.iter().filter(|o| o["kind"] == kind).count() >= floor,
            "{kind}"
        );
    }
    // the Spark network is not an island: Millbridge links the camps, its neighbours' masters and the Yearwheel's
    let master = map
        .npcs
        .iter()
        .find(|n| n.id == "travel_millbridge")
        .unwrap();
    for id in [
        "travel_honeywood",
        "travel_wickerfield",
        "travel_elderroot",
        "travel_breakwater",
        "travel_springmere",
    ] {
        assert!(master.travel_links.iter().any(|l| l == id), "{id}");
    }
    // every Spark link of this zone's masters is answered from the other side (both halves of every seam)
    for zone_id in std::iter::once(VALE).chain(PARTNERS) {
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
}

#[test]
fn every_border_to_a_shaped_neighbour_is_a_seam_with_a_road_across_and_only_the_door_and_the_vault_are_portals()
 {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in data["zones"][zi - 1]["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == VALE || to == VALE) {
                pairs.insert((zi, to));
            }
        }
    }
    let mut want = std::collections::BTreeSet::new();
    for z in PARTNERS {
        want.insert((VALE, z));
        want.insert((z, VALE));
    }
    assert_eq!(pairs, want, "six seams, each seen from both sides");
    let w = world();
    let zone = &data["zones"][VALE - 1];
    for z in PARTNERS {
        let mine = w.maps[VALE]
            .portals
            .iter()
            .find(|p| p.to == z && p.seam.is_some())
            .unwrap_or_else(|| panic!("the seam portal to {z}"));
        let theirs = w.maps[z]
            .portals
            .iter()
            .find(|p| p.to == VALE && p.seam.is_some())
            .unwrap_or_else(|| panic!("the far seam portal of {z}"));
        assert!(
            (theirs.x - mine.tx).abs() < 1e-6 && (theirs.y - mine.ty).abs() < 1e-6,
            "the two portals of the seam to {z} face each other"
        );
        assert!(
            mine.walk.is_none() && theirs.walk.is_none(),
            "a seam is no gate"
        );
        let near = zone["paths"].as_array().unwrap().iter().any(|road| {
            road.as_array().unwrap().iter().any(|q| {
                let (qx, qy) = (q[0].as_f64().unwrap(), q[1].as_f64().unwrap());
                ((qx - mine.x).powi(2) + (qy - mine.y).powi(2)).sqrt() < 2.6
            })
        });
        assert!(near, "a road of this zone meets the seam to {z}");
        let theirs_near = data["zones"][z - 1]["paths"]
            .as_array()
            .unwrap()
            .iter()
            .any(|road| {
                road.as_array().unwrap().iter().any(|q| {
                    let (qx, qy) = (q[0].as_f64().unwrap(), q[1].as_f64().unwrap());
                    ((qx - theirs.x).powi(2) + (qy - theirs.y).powi(2)).sqrt() < 4.5
                })
            });
        assert!(theirs_near, "a road of zone {z} meets the same crossing");
    }
    let mut others: Vec<_> = w.maps[VALE]
        .portals
        .iter()
        .filter(|p| p.seam.is_none())
        .map(|p| (p.id.as_str(), p.to))
        .collect();
    others.sort();
    assert_eq!(
        others,
        [("path_20_28", YEARWHEEL), ("sun_elder_gate", 30)],
        "the Hollow door and the Yearwheel vault are the only portals"
    );
}

#[test]
fn the_yearwheel_is_walled_off_along_its_whole_border_but_for_one_vaulted_opening() {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &data["zones"][VALE - 1];
    // exactly one crossing to the Yearwheel, walked through, with an arch drawn for it
    let doors: Vec<_> = zone["portals"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|p| p["to"] == YEARWHEEL)
        .collect();
    assert_eq!(doors.len(), 1, "one vault");
    let vault = doors[0];
    assert_eq!(vault["id"], "path_20_28");
    assert_eq!(vault["walk"], serde_json::json!([0, -1]));
    let arch = zone["exitArches"]
        .as_array()
        .unwrap()
        .iter()
        .find(|a| a["portal"] == "path_20_28")
        .expect("the vault's arch");
    let (vx, vy) = (vault["x"].as_f64().unwrap(), vault["y"].as_f64().unwrap());
    assert!(
        (arch["x"].as_f64().unwrap() - vx).abs() < 1e-6
            && (arch["y"].as_f64().unwrap() - vy).abs() < 1e-6,
        "the arch stands at the vault"
    );
    assert_eq!(arch["vertical"], false);
    assert!(
        data["zones"][YEARWHEEL - 1]["portals"]
            .as_array()
            .unwrap()
            .iter()
            .any(|p| p["id"] == "path_28_20" && p["to"] == VALE),
        "the Yearwheel's way back"
    );
    // the wall is isometric city art with real collision: ramparts and towers
    let objects = zone["objects"].as_array().unwrap();
    let ramparts: Vec<_> = objects.iter().filter(|o| o["kind"] == "rampart").collect();
    let towers: Vec<_> = objects.iter().filter(|o| o["kind"] == "tower").collect();
    assert!(ramparts.len() >= 30, "{} ramparts", ramparts.len());
    assert!(towers.len() >= 5, "{} towers", towers.len());
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
    // every wall piece stands about 1.7 tiles inside the border, and neighbouring pieces overlap so nothing slips between them: the one gap is the vault's
    let mut pieces: Vec<(f64, f64)> = ramparts
        .iter()
        .chain(towers.iter())
        .map(|o| (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap()))
        .collect();
    for &(x, y) in &pieces {
        let d = border_dist(&pts, x, y);
        assert!(
            (1.0..=2.6).contains(&d),
            "a wall piece {d:.2} tiles from the border"
        );
    }
    pieces.sort_by(|a, b| a.0.total_cmp(&b.0));
    let mut gaps = vec![];
    for pair in pieces.windows(2) {
        let gap = ((pair[0].0 - pair[1].0).powi(2) + (pair[0].1 - pair[1].1).powi(2)).sqrt();
        if gap > 3.2 {
            gaps.push((pair[0], pair[1], gap));
        }
    }
    assert_eq!(gaps.len(), 1, "one opening in the wall: {gaps:?}");
    let (a, b, gap) = gaps[0];
    assert!(
        a.0 < vx && b.0 > vx && (10. ..=18.).contains(&gap),
        "the opening is the vault's ({gap:.1} wide, between {a:?} and {b:?})"
    );
    // a walker pushed toward the border from 6 tiles inland, at a dozen places along it (not at the vault), never gets within a body of it
    let w = world();
    let map = &w.maps[VALE];
    let mut tried = 0;
    for i in 1..12 {
        let k = ((pts.len() - 1) as f64 * i as f64 / 12.) as usize;
        let (a, b) = (pts[k], pts[(k + 1).min(pts.len() - 1)]);
        let (mx, my) = (a.0 + (b.0 - a.0) * 0.5, a.1 + (b.1 - a.1) * 0.5);
        if (mx - vx).abs() < 14. {
            continue;
        }
        let ln = ((b.0 - a.0).powi(2) + (b.1 - a.1).powi(2)).sqrt();
        let (mut nx, mut ny) = (-(b.1 - a.1) / ln, (b.0 - a.0) / ln);
        // the land side is the one nearer the zone's middle
        let far = |s: f64| (mx + nx * s - 176.).powi(2) + (my + ny * s - 176.).powi(2);
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
            border_dist(&pts, foot.x, foot.y) > 1.2,
            "a walker got to {:.2} tiles from the Yearwheel border at {mx:.0},{my:.0}",
            border_dist(&pts, foot.x, foot.y)
        );
    }
    assert!(tried >= 4, "only {tried} places could be tried");
}

#[test]
fn a_hero_walks_through_the_vault_to_the_yearwheel_and_back() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let vault = w.maps[VALE]
        .portals
        .iter()
        .find(|p| p.id == "path_20_28")
        .unwrap()
        .clone();
    place(&mut w, 1, VALE, at(vault.x, vault.y + 4.));
    w.message(
        1,
        ClientMessage::Move {
            x: vault.x,
            y: vault.y - 3.,
        },
    );
    run(&mut w, &mut rx, 60);
    assert_eq!(
        w.players[&1].character.zone, YEARWHEEL,
        "the vault leads to the Yearwheel"
    );
    let back = w.maps[YEARWHEEL]
        .portals
        .iter()
        .find(|p| p.id == "path_28_20")
        .unwrap()
        .clone();
    let (bx, by) = (back.tx, back.ty);
    assert!(
        (bx - vault.x).abs() < 1e-6 && (by - (vault.y + 7.)).abs() < 1e-6,
        "the Yearwheel's gate arrives seven tiles inside the vault, clear of it"
    );
    let mut arrival = at(bx, by);
    w.maps[VALE].collide(&mut arrival, PLAYER_RADIUS);
    assert!(
        arrival.distance(at(bx, by)) < 1e-6,
        "the arrival is free ground"
    );
    let side = back.walk.expect("a walk-in gate");
    place(&mut w, 1, YEARWHEEL, at(back.x, back.y));
    w.message(
        1,
        ClientMessage::Move {
            x: back.x + f64::from(side[0]) * 3.,
            y: back.y + f64::from(side[1]) * 3.,
        },
    );
    run(&mut w, &mut rx, 60);
    assert_eq!(
        w.players[&1].character.zone, VALE,
        "and back through the vault"
    );
}

#[test]
fn the_hollow_door_leads_down_and_both_ways_home_arrive_clear_beside_the_camp() {
    let w = world();
    let door = w.maps[VALE]
        .portals
        .iter()
        .find(|p| p.id == "sun_elder_gate")
        .unwrap();
    for id in ["elder_hollow_return", "elder_hollow_exit"] {
        let home = w.maps[30].portals.iter().find(|p| p.id == id).unwrap();
        assert_eq!(home.to, VALE, "{id}");
        assert!(
            at(home.tx, home.ty).distance(at(door.x, door.y)) > door.r + 0.5
                && at(home.tx, home.ty).distance(at(door.x, door.y)) < 10.,
            "{id} arrives beside the door, clear of its disc"
        );
        let mut a = at(home.tx, home.ty);
        w.maps[VALE].collide(&mut a, PLAYER_RADIUS);
        assert!(
            a.distance(at(home.tx, home.ty)) < 1e-6,
            "{id} lands on free ground"
        );
    }
    assert!(
        w.spawns
            .iter()
            .filter(|s| s.zone == VALE)
            .all(|s| at(s.x, s.y).distance(at(door.x, door.y)) > 8.),
        "nothing stands at the door"
    );
}

#[test]
fn everyone_and_everything_in_the_vale_can_be_walked_to_from_millbridge() {
    let w = world();
    let map = &w.maps[VALE];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(
            reached_near(map, &open, p.x, p.y, p.r + 1.),
            "{} is cut off",
            p.id
        );
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == VALE) {
        assert!(
            reached(map, &open, at(s.x, s.y)),
            "{} #{id} is cut off",
            s.kind
        );
    }
    for p in &map.portals {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (key, prefix, old) in HAMLETS {
        let map = &w.maps[VALE];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(master.travel_links.iter().any(|l| l == "travel_millbridge"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_20_{key}")),
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
        place(&mut w, 1, VALE, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
    // Millbridge keeps the old vale people (their ids are saved progress); the Meeting Stone stands at Elderroot Camp
    let map = &w.maps[VALE];
    for id in [
        "sun_miller",
        "sun_medic",
        "sun_carpenter",
        "sun_guide",
        "sun_trader",
        "travel_millbridge",
        "mailbox_20_millbridge",
    ] {
        let n = map.npcs.iter().find(|n| n.id == id).expect(id);
        assert!(map.in_city(at(n.x, n.y)), "{id} stands in Millbridge");
    }
    let stone = map.npcs.iter().find(|n| n.id == "sun_stone").unwrap();
    let (cx, cy) = camp_centre("Elderroot Camp");
    assert!(
        (stone.x - cx).abs() <= 12. && (stone.y - cy).abs() <= 11.,
        "the Meeting Stone stands in Elderroot Camp"
    );
}

#[test]
fn the_vale_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let m = &w.maps[VALE];
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
    assert!(m.quests.len() >= 28, "{} quests", m.quests.len());
    for id in [
        "sun_welcome",
        "sun_hares",
        "sun_snails",
        "sun_foxes",
        "sun_badgers",
        "sun_honeyjaw",
        "sun_warden",
        "sun_roots",
        "sun_hollow_trials",
        "sun_hollow_heart",
        "sun_patrol",
        "sun_onward",
        "es_16",
        "es_go_16",
    ] {
        assert!(ids.contains(&id), "the old {id} keeps its id");
    }
    let new = ids.iter().filter(|i| i.starts_with("svs_")).count();
    assert_eq!(new, 14, "fourteen new quests");
    for q in &m.quests {
        assert!(format!("quest:accept:{}", q.id).len() <= 32, "{}", q.id);
    }
    for id in ["sun_honeyjaw", "sun_warden"] {
        let q = m.quests.iter().find(|q| q.id == id).unwrap();
        assert!(q.group && q.reward_item.is_some(), "{id}");
        assert!(!q.reward_choices.is_empty(), "{id} offers class choices");
    }
    // the Harrow Ox has no quest: nothing asks for it
    assert!(
        m.quests
            .iter()
            .all(|q| q.objectives.iter().all(|o| o.target != "harrowox"))
    );
}

/// every compass word in a quest or person text is checked against the coordinates (a word that lies is a bug)
#[test]
fn the_compass_words_in_the_texts_match_where_things_stand() {
    let w = world();
    let (hx, hy) = camp_centre("Honeywood Steading");
    let (fx, fy) = camp_centre("Wickerfield Post");
    let (ex, ey) = camp_centre("Elderroot Camp");
    let (mx, _) = camp_centre("Millbridge");
    // Honeywood: the hives lie south-west, Thornback Ridge south-east, the circle north-east
    let (x, y) = spot(&w, "sv_hives");
    assert!(
        x < hx && y > hy,
        "the Hawthorn Hives are south-west of the Steading"
    );
    let (x, y) = spot(&w, "sv_ridge");
    assert!(
        x > hx && y > hy,
        "Thornback Ridge is south-east of the Steading"
    );
    let (x, y) = spot(&w, "svs_hw_m");
    assert!(
        x > hx && y < hy,
        "the Honeywood Circle is north-east of the Steading"
    );
    // Wickerfield: the rows south-west, the circle and the barrow south-east
    let (x, y) = spot(&w, "sv_rows");
    assert!(
        x < fx && y > fy,
        "the Scarecrow Rows are south-west of the post"
    );
    let (x, y) = spot(&w, "svs_wf_m");
    assert!(
        x > fx && y > fy,
        "the Wickerfield Circle is south-east of the post"
    );
    let (x, y) = spot(&w, "sv_barrow");
    assert!(
        x > fx && y > fy,
        "the Long Barrow is south-east of the post"
    );
    // Elderroot: the orchard south-west, the springs south-east, the circle north-east, the door north
    let (x, y) = spot(&w, "sv_orchard");
    assert!(
        x < ex && y > ey,
        "the Elder Orchard is south-west of the camp"
    );
    let (x, y) = spot(&w, "sv_springs");
    assert!(
        x > ex && y > ey,
        "the Root Springs are south-east of the camp"
    );
    let (x, y) = spot(&w, "svs_er_m");
    assert!(
        x > ex && y < ey,
        "the Elderroot Circle is north-east of the camp"
    );
    let (_, y) = spot(&w, "sun_elder_hollow");
    assert!(y < ey, "the Hollow door is north of the camp");
    // Millbridge: the Weir lies across the river, west of the mill
    let (x, _) = spot(&w, "svs_mb_m");
    assert!(x < mx, "the Millbridge Weir is west of Millbridge");
    // the three outposts: the Honeywood Steading in the north-west, the Wickerfield Post in the north-east, Elderroot Camp in the north
    assert!(hx < ex && ex < fx && hy < 120. && fy < 120. && ey < 120.);
    // the elites
    let find = |k: &str| {
        w.spawns
            .iter()
            .find(|s| s.zone == VALE && s.kind == k)
            .unwrap()
    };
    assert!(
        find("honeyjaw").x < hx && find("honeyjaw").y < hy,
        "Old Honeyjaw lies north-west of the Steading"
    );
    assert!(
        find("wickerwarden").x > fx && find("wickerwarden").y < fy,
        "the Wicker Warden stands north-east of the post"
    );
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
                zone: VALE,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 1_000_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("harrowox"), "harrow_horn");
    let w = world();
    let map = &w.maps[VALE];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == VALE && s.kind == kind)
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
        "three elites, two with a quest and the Harrow Ox without (the Empty Seat's echo foe is a story encounter, not an elite of the vale)"
    );
}

#[test]
fn the_empty_seats_echo_stands_east_of_millbridge() {
    let w = world();
    let m = &w.maps[VALE];
    let (mx, my) = camp_centre("Millbridge");
    let p = m.places.iter().find(|p| p.id == "es_16_m").unwrap();
    assert!(
        p.x > mx && (p.y - my).abs() < p.x - mx,
        "the echo circle is east of Millbridge"
    );
    let open = flood(m, &blocked(m, &[]), m.spawn);
    assert!(reached(m, &open, at(p.x, p.y)));
    // chapter 16 is a memory, not a fight: no echo foe stands there
    assert!(
        w.spawns
            .iter()
            .all(|s| !(s.zone == VALE && s.kind.starts_with("es_foe_"))),
        "chapter 16 has no foe"
    );
    for n in m.npcs.iter().filter(|n| n.id.starts_with("mailbox_20_")) {
        let mut foot = at(n.x, n.y);
        m.collide(&mut foot, PLAYER_RADIUS);
        assert!(foot.distance(at(n.x, n.y)) < 1e-6, "{} is blocked", n.id);
        assert!(reached(m, &open, at(n.x, n.y)));
    }
}

#[test]
fn the_vale_enemies_materials_elites_and_quest_rewards_are_registered() {
    let w = world();
    let m = &w.maps[VALE];
    for (kind, level, drop) in [
        ("meadowhare", 65, "hare_whisker"),
        ("sunbacksnail", 66, "sunback_shell"),
        ("brushfox", 67, "fox_tail_tuft"),
        ("spadebadger", 68, "badger_claw"),
        ("honeyjaw", 69, "honeyjaw_comb"),
        ("harrowox", 69, "harrow_horn"),
        ("wickerwarden", 70, "wicker_heart"),
    ] {
        assert!(w.spawns.iter().any(|s| s.zone == VALE && s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 200000. && damage > 3000.);
    }
    assert!(is_elite("honeyjaw") && is_elite("wickerwarden") && is_elite("harrowox"));
    assert!(!is_elite("spadebadger"));
    for q in &m.quests {
        if q.id.starts_with("es_go_") {
            continue; // a hand-off pays nothing
        }
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "sun_hares",
        "sun_snails",
        "sun_honeyjaw",
        "sun_warden",
        "svs_mb_hold",
        "svs_rounds",
        "svs_hw_hold",
        "svs_hw_ridge",
        "svs_wf_hold",
        "svs_wf_barrow",
        "svs_er_hold",
        "svs_er_springs",
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
    for route in data["zones"][VALE - 1]["exitRoutes"].as_array().unwrap() {
        let points = route["points"].as_array().unwrap();
        for pair in points.windows(2) {
            let p = |v: &Value| at(v[0].as_f64().unwrap(), v[1].as_f64().unwrap());
            assert!(
                w.maps[VALE].line_clear(p(&pair[0]), p(&pair[1]), PLAYER_RADIUS),
                "the exit route of {} is blocked: {:?} -> {:?}",
                route["portal"],
                pair[0],
                pair[1]
            );
        }
    }
}

#[test]
fn the_river_is_solid_water_with_fords_and_two_bridges_and_stays_clear_of_every_seam() {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &data["zones"][VALE - 1];
    let objects = zone["objects"].as_array().unwrap();
    let water: Vec<(f64, f64)> = objects
        .iter()
        .filter(|o| o["kind"] == "water")
        .map(|o| (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap()))
        .collect();
    assert!(water.len() >= 60, "{} water circles", water.len());
    // the neighbours draw no water: none within 17 tiles of any seam
    for p in zone["portals"].as_array().unwrap() {
        if p.get("seam").is_none() {
            continue;
        }
        let pts: Vec<(f64, f64)> = p["seam"]["points"]
            .as_array()
            .unwrap()
            .iter()
            .map(|q| (q[0].as_f64().unwrap(), q[1].as_f64().unwrap()))
            .collect();
        for &(x, y) in &water {
            assert!(
                border_dist(&pts, x, y) >= 17.,
                "water at {x:.0},{y:.0} stands {:.1} tiles from the seam to {}",
                border_dist(&pts, x, y),
                p["to"]
            );
        }
    }
    // the water is solid, and the two stone bridges and the fords let the roads across
    let w = world();
    let map = &w.maps[VALE];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    let centre = at(water[water.len() / 2].0, water[water.len() / 2].1);
    let mut foot = centre;
    map.collide(&mut foot, PLAYER_RADIUS);
    assert!(
        foot.distance(centre) > 0.3,
        "a walker cannot stand in the river"
    );
    let bridges: Vec<_> = objects
        .iter()
        .filter(|o| o["kind"] == "stone_bridge")
        .collect();
    assert_eq!(bridges.len(), 2, "two stone bridges");
    for b in bridges {
        // the bridge's own cell is marked by the flood grid: both its banks are what a walker reaches
        let (bx, by) = (b["x"].as_f64().unwrap(), b["y"].as_f64().unwrap());
        assert!(
            reached(map, &open, at(bx, by - 3.)) && reached(map, &open, at(bx, by + 3.)),
            "a bridge is walked to from both banks: {bx},{by}"
        );
    }
    // both banks are one world: the north outposts and the southern pastures are connected through the open floor
    for id in ["sv_hives", "sv_barrow", "sv_orchard", "svs_mb_m"] {
        let (x, y) = spot(&w, id);
        assert!(
            reached(map, &open, at(x, y)),
            "{id} is walked to from Millbridge"
        );
    }
}
