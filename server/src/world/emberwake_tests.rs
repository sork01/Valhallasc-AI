//! Emberwake Caldera (zone 45, levels 95-99) as an authored map on the shapes pilot: its data, the two rim gates (the Obsidian Orrery, the Ribbonwild), the two seams (the
//! Stormglass Flats on the north, the Moonspore Canopy on the west), Chainrest and four more hubs, the molten river and its causeway, the Nine-Chain Door and its two ways
//! out, the quests (holds, visits, brings, kills, the two elite quests) and the three elites.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;
const ZONE: usize = 45;
const ELITES: [(&str, u32); 3] = [("ew_chainmaw", 97), ("ew_bellows", 99), ("ew_crown", 99)];
/// (gate, the zone it leads to, the far gate that leads back); the borders to the Flats and the Canopy are seams
const GATES: [(&str, usize, &str); 2] = [
    ("atlas_45_15", 15, "atlas_15_45"),
    ("path_45_21", 21, "path_21_45"),
];
const HAMLETS: [(&str, &str); 3] = [
    ("craterwatch", "ew_cw_"),
    ("cinderquay", "ew_cq_"),
    ("glasshold", "ew_gh_"),
];

fn run(w: &mut World, rx: &mut mpsc::Receiver<Value>, ticks: usize) -> Vec<String> {
    let mut told = vec![];
    for _ in 0..ticks {
        w.step();
        told.extend(lines(rx));
    }
    told
}

/// Distance from a point to a polyline.
fn to_line(p: Point, line: &[Point]) -> f64 {
    line.windows(2)
        .map(|s| {
            let (dx, dy) = (s[1].x - s[0].x, s[1].y - s[0].y);
            let t = (((p.x - s[0].x) * dx + (p.y - s[0].y) * dy) / (dx * dx + dy * dy).max(1e-9))
                .clamp(0., 1.);
            p.distance(at(s[0].x + t * dx, s[0].y + t * dy))
        })
        .fold(f64::MAX, f64::min)
}

#[test]
fn the_caldera_is_a_big_outdoor_map_with_four_kinds_by_distance_three_elites_five_hubs_two_gates_the_raid_door_and_two_seams()
 {
    let w = world();
    let map = &w.maps[ZONE];
    assert_eq!(map.name, "Emberwake Caldera");
    assert_eq!((map.size, map.levels), (400, Some([95, 99])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(!map.interior && map.players == 0 && map.copies == 0);
    let mut live = std::collections::BTreeMap::<&str, Vec<f64>>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == ZONE) {
        if spawn.ambush.is_some() {
            assert!(
                w.slimes[id].dead && w.slimes[id].state == "waiting" && w.slimes[id].respawn >= 1e8,
                "an ambusher sleeps"
            );
            continue;
        }
        live.entry(spawn.kind.as_str())
            .or_default()
            .push(at(spawn.x, spawn.y).distance(map.spawn));
        assert!(!map.in_city(at(spawn.x, spawn.y)));
        assert!((95..=99).contains(&Slime::default_level(&spawn.kind)));
        assert!(!is_boss(&spawn.kind));
    }
    for (kind, floor) in [
        ("ew_ashback", 30),
        ("ew_glasswing", 30),
        ("ew_slagjaw", 40),
        ("ew_cinderhorn", 30),
    ] {
        assert!(live[kind].len() >= floor, "{kind}: {}", live[kind].len());
    }
    for (kind, level) in ELITES {
        assert_eq!(live[kind].len(), 1, "{kind}");
        assert_eq!(Slime::default_level(kind), level, "{kind}");
        assert!(is_elite(kind));
    }
    // the hardest kind lives deep: beside the Flats seam the ashbacks are the commonest kind, beside the Canopy seam the rams are all but absent
    let seam_of = |to: usize| -> Vec<Point> {
        map.portals
            .iter()
            .find(|p| p.to == to && p.seam.is_some())
            .unwrap()
            .seam
            .as_ref()
            .unwrap()
            .points
            .iter()
            .map(|q| at(q[0], q[1]))
            .collect()
    };
    let (flats, canopy) = (seam_of(19), seam_of(16));
    let count_near = |kind: &str, line: &[Point]| {
        w.spawns
            .iter()
            .filter(|s| {
                s.zone == ZONE
                    && s.kind == kind
                    && s.ambush.is_none()
                    && to_line(at(s.x, s.y), line) < 70.
            })
            .count()
    };
    for kind in ["ew_glasswing", "ew_slagjaw", "ew_cinderhorn"] {
        assert!(
            count_near("ew_ashback", &flats) > count_near(kind, &flats),
            "the ashbacks are the commonest kind beside the Flats seam ({kind})"
        );
    }
    assert!(
        count_near("ew_cinderhorn", &canopy) <= 3,
        "the rams stay away from the Canopy seam"
    );
    assert_eq!(map.quests.iter().filter(|q| q.group).count(), 2);
    assert!(
        !map.quests
            .iter()
            .any(|q| q.objectives.iter().any(|o| o.target == "ew_crown")),
        "the Uncrowned Ember has no quest"
    );
    // Chainrest is the zone's `city`, the Nine-Chain Hold and the three outposts are camps; every hub is safe ground with a travel master and a mailbox
    let c = map.city.as_ref().unwrap();
    assert_eq!(
        ((c.x0 + c.x1) / 2., (c.y0 + c.y1) / 2.),
        (228., 84.),
        "Chainrest"
    );
    assert_eq!(map.camps.len(), 4);
    for camp in &map.camps {
        assert!(map.in_city(at((camp.x0 + camp.x1) / 2., (camp.y0 + camp.y1) / 2.)));
    }
    for key in [
        "chainrest",
        "door",
        "craterwatch",
        "cinderquay",
        "glasshold",
    ] {
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(master.travel_stop.is_some());
        assert!(
            master
                .travel_links
                .iter()
                .filter(|l| l.starts_with("travel_"))
                .count()
                >= 4,
            "{key} links to the other hubs"
        );
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_45_{key}")),
            "a mailbox at {key}"
        );
    }
    assert!(map.in_city(map.spawn), "a saved hero is moved to Chainrest");
    let mut free = map.spawn;
    map.collide(&mut free, PLAYER_RADIUS);
    assert!(free.distance(map.spawn) < 1e-6, "the spawn is free ground");
    // places: six to visit, four hold circles
    assert_eq!(
        map.places
            .iter()
            .filter(|p| matches!(
                p.id.as_str(),
                "ew_slopes" | "ew_links" | "ew_shore" | "ew_quench" | "ew_fold" | "ew_crater"
            ))
            .count(),
        6
    );
    assert_eq!(map.places.iter().filter(|p| p.waves.len() == 2).count(), 4);
    // the raid door, the two rim gates and two seams (the Flats, the Canopy)
    assert_eq!(map.portals.len(), 5);
    let mut seams: Vec<usize> = map
        .portals
        .iter()
        .filter(|p| p.seam.is_some())
        .map(|p| p.to)
        .collect();
    seams.sort_unstable();
    assert_eq!(
        seams,
        vec![16, 19],
        "only the Canopy and the Flats are seams"
    );
    for (id, to, _) in GATES {
        let g = map.portals.iter().find(|p| p.id == id).expect(id);
        assert!(g.seam.is_none() && g.walk.is_some() && g.to == to, "{id}");
    }
    let raid = map.portals.iter().find(|p| p.id == "ew_raid").unwrap();
    assert_eq!(
        (raid.to, raid.needs_quest.as_deref()),
        (46, Some("raid_key"))
    );
    assert!(
        at(raid.x, raid.y).distance(at(322., 80.)) < 0.01,
        "the raid door stands under the Nine-Chain Door"
    );
}

#[test]
fn everything_is_reachable_from_the_spawn_the_river_blocks_and_its_causeway_is_floor_and_the_door_is_sealed()
 {
    let w = world();
    let map = &w.maps[ZONE];
    let grid = blocked(map, &[]);
    let open = flood(map, &grid, map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == ZONE) {
        assert!(
            reached(map, &open, at(spawn.x, spawn.y)),
            "{} at {},{} is cut off ({id})",
            spawn.kind,
            spawn.x,
            spawn.y
        );
    }
    for p in &map.places {
        let r = p.r + 1.;
        assert!(
            [(0., 0.), (r, 0.), (-r, 0.), (0., r), (0., -r)]
                .iter()
                .any(|(dx, dy)| reached(map, &open, at(p.x + dx, p.y + dy))),
            "{} is cut off",
            p.id
        );
    }
    for (gate_id, _, _) in GATES {
        let g = map.portals.iter().find(|p| p.id == gate_id).unwrap();
        let side = g.walk.unwrap();
        let inside = at(g.x - f64::from(side[0]) * 6., g.y - f64::from(side[1]) * 6.);
        assert!(reached(map, &open, inside), "{gate_id} is cut off");
    }
    // both banks of the river: Glasshold, Cinderquay and the Ember Crater lie south of it, reached over the causeway or round its west end
    for (name, x, y) in [
        ("Glasshold", 292., 234.),
        ("Cinderquay", 186., 312.),
        ("the Ember Crater", 253., 248.),
        ("Chainmaw", 136., 200.),
    ] {
        assert!(reached(map, &open, at(x, y)), "{name} is cut off");
    }
    // the river is lava: its middle blocks
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let lava: Vec<(f64, f64)> = raw["zones"][ZONE - 1]["objects"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["kind"] == "ew_lava")
        .map(|o| (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap()))
        .collect();
    assert!(lava.len() > 200, "{} lava circles", lava.len());
    for (x, y) in lava.iter().step_by(17) {
        let mut p = at(*x, *y);
        map.collide(&mut p, PLAYER_RADIUS);
        assert!(p.distance(at(*x, *y)) > 0.1, "lava at {x},{y} is floor");
    }
    // the causeway: floor where the Chain Road crosses
    let mut crossing = at(190., 226.5);
    map.collide(&mut crossing, PLAYER_RADIUS);
    assert!(
        crossing.distance(at(190., 226.5)) < 0.01,
        "the causeway is floor"
    );
    // and the river is a wall elsewhere: a straight walk across it far from the causeway stops
    let mut p = at(153., 214.);
    let before = p;
    map.walk(&mut p, before.direction(at(153., 246.)), 32., PLAYER_RADIUS);
    assert!(
        p.distance(at(153., 246.)) > 5.,
        "the river stops a straight walk at x 153"
    );
    // the Nine-Chain Door is sealed scenery
    let mut door = at(322., 76.);
    map.collide(&mut door, PLAYER_RADIUS);
    assert!(
        door.distance(at(322., 76.)) > 0.1,
        "the sealed door has collision"
    );
}

#[test]
fn no_enemy_or_lava_stands_near_a_seam_and_the_elites_keep_clear_of_everything_a_hero_walks_to() {
    let w = world();
    let map = &w.maps[ZONE];
    let seams: Vec<Vec<Point>> = map
        .portals
        .iter()
        .filter_map(|p| p.seam.as_ref())
        .map(|s| s.points.iter().map(|q| at(q[0], q[1])).collect())
        .collect();
    assert_eq!(seams.len(), 2);
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == ZONE) {
        for l in &seams {
            assert!(
                to_line(at(spawn.x, spawn.y), l) > 20.,
                "{} ({id}) stands within 20 tiles of a seam",
                spawn.kind
            );
        }
    }
    // a seam neighbour draws no lava: every circle stands 17 tiles clear
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    for o in raw["zones"][ZONE - 1]["objects"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["kind"] == "ew_lava")
    {
        let (x, y, r) = (
            o["x"].as_f64().unwrap(),
            o["y"].as_f64().unwrap(),
            o["r"].as_f64().unwrap(),
        );
        for l in &seams {
            assert!(to_line(at(x, y), l) - r >= 17., "lava at {x},{y}");
        }
    }
    let walked: Vec<Point> = map
        .npcs
        .iter()
        .map(|n| at(n.x, n.y))
        .chain(
            map.portals
                .iter()
                .filter(|p| p.seam.is_none())
                .map(|p| at(p.x, p.y)),
        )
        .chain(map.places.iter().map(|p| at(p.x, p.y)))
        .collect();
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == ZONE && s.kind == kind)
            .unwrap();
        let near = walked
            .iter()
            .map(|p| p.distance(at(e.x, e.y)))
            .fold(f64::MAX, f64::min);
        assert!(
            near > 15.,
            "{kind} stands {near:.1} tiles from something a hero walks to"
        );
        for c in std::iter::once(map.city.as_ref().unwrap()).chain(&map.camps) {
            let gap = (c.x0 - e.x)
                .max(0.)
                .max(e.x - c.x1)
                .hypot((c.y0 - e.y).max(0.).max(e.y - c.y1));
            assert!(gap > 15., "{kind} stands {gap:.1} tiles from a hub");
        }
    }
}

#[test]
fn the_two_rim_gates_are_walked_through_both_ways_and_every_arrival_is_clear_ground() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in GATES {
        let gate = w.maps[ZONE]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, ZONE, at(gate.x, gate.y));
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
        assert_eq!(back.to, ZONE, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        assert!(
            arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
                && arrival.distance(at(gate.x, gate.y)) < 12.,
            "{back_id} arrives beside {gate_id}, clear of its disc"
        );
        let mut a = arrival;
        w.maps[ZONE].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == ZONE)
                .all(|s| at(s.x, s.y).distance(arrival) > 8.),
            "an enemy stands near the arrival of {back_id}"
        );
        // and back
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
        assert_eq!(w.players[&1].character.zone, ZONE, "{back_id} returns");
        let c = &w.players[&1].character;
        assert!(
            at(c.x, c.y).distance(at(gate.x, gate.y)) < 12.,
            "{back_id} puts the hero near {gate_id}"
        );
    }
}

#[test]
fn the_raid_door_moved_whole_and_both_ways_out_of_the_forge_arrive_in_front_of_it() {
    let w = world();
    let map = &w.maps[ZONE];
    let door = at(316., 81.);
    for id in ["cf_return", "cf_clear"] {
        let p = w.maps[46].portals.iter().find(|p| p.id == id).unwrap();
        assert_eq!(p.to, ZONE, "{id}");
        assert!(
            at(p.tx, p.ty).distance(door) < 0.01,
            "{id} arrives in front of the Door"
        );
    }
    let mut a = door;
    map.collide(&mut a, PLAYER_RADIUS);
    assert!(
        a.distance(door) < 1e-6,
        "the way out of the Forge lands on free ground"
    );
    assert!(
        map.in_city(door),
        "the arrival is inside the Nine-Chain Hold"
    );
    for id in ["ew_smith", "ew_stone", "ew_seal", "ew_echo"] {
        let n = map.npcs.iter().find(|n| n.id == id).unwrap();
        assert!(map.in_city(at(n.x, n.y)), "{id} stands in the Hold");
        assert!(
            at(n.x, n.y).distance(at(322., 76.)) < 25.,
            "{id} stands by the Door"
        );
    }
    // the Empty Seat's two places keep their ids: the guest at the last door stands outside the sanctuary, the answer is given at the Door
    let es25 = map.places.iter().find(|p| p.id == "es_25_m").unwrap();
    assert!(
        !map.in_city(at(es25.x, es25.y)),
        "the shade's circle is outside the sanctuary"
    );
    let es26 = map.places.iter().find(|p| p.id == "es_26_m").unwrap();
    assert!(at(es26.x, es26.y).distance(at(322., 76.)) < 25.);
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (key, prefix) in HAMLETS {
        let map = &w.maps[ZONE];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_45_{key}")),
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
        place(&mut w, 1, ZONE, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
}

#[test]
fn the_caldera_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let map = &w.maps[ZONE];
    let new = [
        "ew_h_hold",
        "ew_h_rounds",
        "ew_cw_walk",
        "ew_cw_scales",
        "ew_cw_hold",
        "ew_cw_links",
        "ew_cq_walk",
        "ew_cq_wings",
        "ew_cq_hold",
        "ew_cq_quench",
        "ew_gh_walk",
        "ew_gh_horns",
        "ew_gh_hold",
        "ew_gh_crater",
    ];
    for id in new {
        let q = map
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap_or_else(|| panic!("no quest {id}"));
        assert!((95..=99).contains(&q.level), "{id} level {}", q.level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{id}");
        assert!(q.reward_gold >= 20000, "{id}");
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
                "kill" => assert!(
                    w.spawns
                        .iter()
                        .any(|s| s.zone == ZONE && s.kind == o.target && s.ambush.is_none()),
                    "{id} hunts {}",
                    o.target
                ),
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
    // the old chain keeps its ids and the elites' quests stay groups
    for (id, kind, players) in [
        ("ew_link", "ew_chainmaw", 3),
        ("ew_breath", "ew_bellows", 5),
    ] {
        let q = map.quests.iter().find(|q| q.id == id).unwrap();
        assert!(q.group);
        assert_eq!(q.recommended_players, players, "{id}");
        assert!(q.objectives.len() == 1 && q.objectives[0].target == kind);
    }
    for id in [
        "ew_warm", "ew_road", "ew_voice", "raid_key", "es_25", "es_26", "es_27",
    ] {
        assert!(map.quests.iter().any(|q| q.id == id), "{id} keeps its id");
    }
    // the hold circles have four sleepers each, in two waves
    for hold in ["ew_warm_m", "ew_rim_m", "ew_quay_m", "ew_glass_m"] {
        let sleepers = w
            .spawns
            .iter()
            .filter(|s| {
                s.zone == ZONE
                    && s.ambush
                        .as_deref()
                        .is_some_and(|t| t.starts_with(&format!("{hold}#")))
            })
            .count();
        assert_eq!(sleepers, 4, "{hold}");
    }
}

#[test]
fn emberwake_kills_pay_materials_and_keep_elite_rules() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    for kind in [
        "ew_ashback",
        "ew_glasswing",
        "ew_slagjaw",
        "ew_cinderhorn",
        "ew_chainmaw",
        "ew_bellows",
        "ew_crown",
    ] {
        let i = (0..w.slimes.len())
            .find(|&i| {
                w.slimes[i].zone == ZONE && w.slimes[i].kind == kind && w.spawns[i].ambush.is_none()
            })
            .unwrap();
        let point = w.slimes[i].point();
        place(&mut w, 1, ZONE, point);
        w.hit_slime(i, 1, 1e15, false);
        assert!(w.slimes[i].dead);
        assert_eq!(w.slimes[i].respawn, if is_elite(kind) { 600. } else { 22. });
        assert!(
            w.drops
                .iter()
                .any(|d| d.item.as_deref() == Some(format!("{kind}_relic").as_str())),
            "{kind}"
        );
    }
}
