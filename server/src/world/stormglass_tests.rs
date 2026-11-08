//! The Stormglass Flats (zone 19, levels 60-65; formerly "The Stormglass Shore") as an authored night plain on the shapes pilot: its data, the three rim gates, the
//! Asterion gate on the compass rose, the two seams (the Prismwaste on the north, the Obsidian Orrery on the west), Breakwater Camp and three outposts, the
//! quests (holds, visits, brings, kills, the two elite quests) and the two new elites.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const FLATS: usize = 19;
const ELITES: [(&str, u32); 3] = [
    ("maelstromheart", 65),
    ("lamphermit", 63),
    ("stormtusk", 62),
];
/// (gate, the zone it leads to, the far gate that leads back); the borders to the Prismwaste and the Orrery are seams
const GATES: [(&str, usize, &str); 2] = [
    ("stormglass_sun_gate", 20, "sun_stormglass_gate"),
    ("path_19_26", 26, "path_26_19"),
];
const HAMLETS: [(&str, &str); 3] = [
    ("rodstead", "storm_rs_"),
    ("fulgur", "storm_fp_"),
    ("bankhold", "storm_bh_"),
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
fn the_flats_are_a_big_night_plain_with_four_families_by_distance_three_elites_four_hubs_three_gates_the_compass_gate_and_two_seams()
 {
    let w = world();
    let map = &w.maps[FLATS];
    assert_eq!(map.name, "The Stormglass Flats");
    assert_eq!((map.size, map.levels), (328, Some([60, 65])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    // the four families, banded by distance from the camp in the south-west: claws by it, then rays, and the sentinels farthest
    let mut live = std::collections::BTreeMap::<&str, Vec<f64>>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == FLATS) {
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
        assert!(
            at(spawn.x, spawn.y).distance(map.spawn) > 8.,
            "{} is clear of the camp",
            spawn.kind
        );
    }
    for (kind, floor) in [
        ("saltclaw", 50),
        ("stormgull", 45),
        ("glassray", 50),
        ("breakersentinel", 40),
    ] {
        assert!(live[kind].len() >= floor, "{kind}: {}", live[kind].len());
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind].len(), 1, "{kind}");
    }
    assert_eq!(live.len(), 7, "{:?}", live.keys());
    let mean = |k: &str| live[k].iter().sum::<f64>() / live[k].len() as f64;
    assert!(
        mean("saltclaw") < mean("glassray") && mean("glassray") < mean("breakersentinel"),
        "claws, then rays, then sentinels, by distance from the camp"
    );
    assert!(
        mean("saltclaw") + 25. < mean("breakersentinel"),
        "the sentinels live well beyond the claws"
    );
    for (kind, level) in [
        ("saltclaw", 60),
        ("stormgull", 61),
        ("glassray", 62),
        ("breakersentinel", 64),
        ("maelstromheart", 65),
        ("lamphermit", 63),
        ("stormtusk", 62),
    ] {
        assert_eq!(Slime::default_level(kind), level, "{kind}");
    }
    // the camp is the zone's `city`, the three outposts are camps; every hub is safe ground with a travel master
    let c = map.city.as_ref().unwrap();
    assert_eq!((c.x1 - c.x0, c.y1 - c.y0), (39., 28.));
    assert_eq!(map.camps.len(), 3);
    for camp in &map.camps {
        assert!(map.in_city(at((camp.x0 + camp.x1) / 2., (camp.y0 + camp.y1) / 2.)));
    }
    for id in [
        "travel_breakwater",
        "travel_rodstead",
        "travel_fulgur",
        "travel_bankhold",
    ] {
        assert!(
            map.npcs
                .iter()
                .any(|n| n.id == id && n.travel_stop.is_some()),
            "{id}"
        );
    }
    assert!(map.in_city(map.spawn), "a new hero starts in the camp");
    let mut free = map.spawn;
    map.collide(&mut free, PLAYER_RADIUS);
    assert!(free.distance(map.spawn) < 1e-6, "the spawn is free ground");
    // ten places: six to visit, four hold circles (the Eye's two and the Empty Seat's are not counted)
    assert_eq!(
        map.places
            .iter()
            .filter(|p| p.id.starts_with("storm_"))
            .count(),
        10
    );
    // the two rim gates, Asterion's gate, the Eye's descent and three seams (the Prismwaste, the Orrery, Emberwake)
    assert_eq!(map.portals.len(), 7);
    let mut seams: Vec<usize> = map
        .portals
        .iter()
        .filter(|p| p.seam.is_some())
        .map(|p| p.to)
        .collect();
    seams.sort_unstable();
    assert_eq!(
        seams,
        vec![14, 15, 45],
        "only the Prismwaste, the Orrery and Emberwake are seams"
    );
    for (id, to, _) in GATES {
        let g = map.portals.iter().find(|p| p.id == id).expect(id);
        assert!(g.seam.is_none() && g.walk.is_some() && g.to == to, "{id}");
    }
    // Asterion's gate stands in the open on the compass rose: no side to walk out of
    let ast = map
        .portals
        .iter()
        .find(|p| p.id == "stormglass_asterion_gate")
        .unwrap();
    assert!(ast.walk.is_none() && ast.to == 17);
    assert!(
        at(ast.x, ast.y).distance(at(177., 277.)) < 10.,
        "the gate stands on the compass rose"
    );
}

#[test]
fn the_three_rim_gates_are_walked_through_both_ways_and_every_arrival_is_clear_ground() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in GATES {
        let gate = w.maps[FLATS]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        assert_eq!(gate.to, zone, "{gate_id}");
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, FLATS, at(gate.x, gate.y));
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
        assert_eq!(back.to, FLATS, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        assert!(
            arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
                && arrival.distance(at(gate.x, gate.y)) < 12.,
            "{back_id} arrives beside {gate_id}, clear of its disc"
        );
        let mut a = arrival;
        w.maps[FLATS].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        // no enemy within eight tiles of an arrival
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == FLATS)
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
        assert_eq!(w.players[&1].character.zone, FLATS, "{back_id} returns");
        let c = &w.players[&1].character;
        assert!(
            at(c.x, c.y).distance(at(gate.x, gate.y)) < 12.,
            "{back_id} puts the hero near {gate_id}"
        );
    }
}

#[test]
fn the_compass_gate_and_the_eye_lead_both_ways_and_land_on_clear_ground() {
    let w = world();
    let m = &w.maps[FLATS];
    let out = m
        .portals
        .iter()
        .find(|p| p.id == "stormglass_asterion_gate")
        .unwrap();
    let back = w.maps[17]
        .portals
        .iter()
        .find(|p| p.id == "asterion_stormglass_gate")
        .unwrap();
    assert_eq!((out.to, back.to), (17, FLATS));
    for (source, portal) in [(m, out), (&w.maps[17], back)] {
        let mut p = at(portal.x, portal.y);
        source.collide(&mut p, PLAYER_RADIUS);
        assert!(
            p.distance(at(portal.x, portal.y)) < 1e-6,
            "{} is blocked",
            portal.id
        );
        let mut arrival = at(portal.tx, portal.ty);
        w.maps[portal.to].collide(&mut arrival, PLAYER_RADIUS);
        assert!(
            arrival.distance(at(portal.tx, portal.ty)) < 1e-6,
            "{} arrival blocked",
            portal.id
        );
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == portal.to && s.ambush.is_none())
                .all(|s| at(s.x, s.y).distance(arrival) >= 8.),
            "an enemy stands near the arrival of {}",
            portal.id
        );
    }
    // the arrival from Asterion is clear of the gate's own disc
    assert!(at(back.tx, back.ty).distance(at(out.x, out.y)) > out.r + 1.);
    // the Eye Below keeps its descent and both of its ways back arrive in front of it
    let eye = m
        .portals
        .iter()
        .find(|p| p.id == "stormglass_eye_descent")
        .unwrap();
    assert_eq!(eye.to, 29);
    for id in ["eye_below_return", "eye_below_exit"] {
        let r = w.maps[29].portals.iter().find(|p| p.id == id).unwrap();
        assert_eq!(r.to, FLATS, "{id}");
        assert!(
            at(r.tx, r.ty).distance(at(eye.x, eye.y)) > eye.r + 1.
                && at(r.tx, r.ty).distance(at(eye.x, eye.y)) < 8.,
            "{id} arrives in front of the descent"
        );
        let mut a = at(r.tx, r.ty);
        m.collide(&mut a, PLAYER_RADIUS);
        assert!(
            a.distance(at(r.tx, r.ty)) < 1e-6,
            "{id} lands on free ground"
        );
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let z = &raw["zones"][FLATS - 1];
    assert_eq!(z["futureInstance"]["status"], "open");
    assert_eq!(z["futureInstance"]["name"], "The Eye Below");
    assert!(
        (z["futureInstance"]["x"].as_f64().unwrap() - eye.x).abs() < 1.
            && (z["futureInstance"]["y"].as_f64().unwrap() - eye.y).abs() < 6.,
        "the instance marker follows the Eye"
    );
    assert!(m.npcs.iter().any(|n| n.id == "stormglass_stone"));
    assert!(
        w.maps[17]
            .npcs
            .iter()
            .find(|n| n.id == "travel_asterion")
            .unwrap()
            .travel_links
            .contains(&"travel_breakwater".to_string())
    );
}

#[test]
fn everyone_and_everything_in_the_flats_can_be_walked_to_from_the_camp() {
    let w = world();
    let map = &w.maps[FLATS];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in map
        .places
        .iter()
        .filter(|p| p.id != "stormglass_eye" && p.id != "stormglass_bell")
    {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == FLATS) {
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
    // Asterion's gate is approached from the road in the north; the Eye's descent from the south, where its way back arrives (the arch stands on it)
    for (id, dy) in [
        ("stormglass_asterion_gate", -3.),
        ("stormglass_eye_descent", 3.),
    ] {
        let g = map.portals.iter().find(|p| p.id == id).unwrap();
        assert!(reached(map, &open, at(g.x, g.y + dy)), "{id} is cut off");
    }
    // the Eye's arch and bell stand on their own places: those are reached from beside them
    for id in ["stormglass_eye", "stormglass_bell"] {
        let p = map.places.iter().find(|p| p.id == id).unwrap();
        assert!(
            reached(map, &open, at(p.x, p.y + p.r + 1.)),
            "{id} is cut off"
        );
    }
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let hub = w.maps[FLATS]
        .npcs
        .iter()
        .find(|n| n.id == "travel_breakwater")
        .unwrap()
        .clone();
    for (key, prefix) in HAMLETS {
        let map = &w.maps[FLATS];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(
            hub.travel_links.iter().any(|l| l == &master.id),
            "the camp links to {key}"
        );
        assert!(master.travel_links.iter().any(|l| l == "travel_breakwater"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_19_{key}")),
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
        // the two who are not the trader give quests
        for n in people.iter().filter(|n| !n.buys) {
            assert!(
                map.quests.iter().any(|q| q.npc == n.id),
                "{} gives a quest",
                n.id
            );
        }
        let (x, y) = ((camp.x0 + camp.x1) / 2., (camp.y0 + camp.y1) / 2.);
        place(&mut w, 1, FLATS, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
}

#[test]
fn the_flats_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let map = &w.maps[FLATS];
    let new = [
        "storm_h_hold",
        "storm_h_rounds",
        "stormglass_hermit",
        "storm_rs_walk",
        "storm_rs_reeds",
        "storm_rs_hold",
        "storm_rs_pans",
        "storm_fp_walk",
        "storm_fp_feathers",
        "storm_fp_hold",
        "storm_fp_drift",
        "storm_bh_walk",
        "storm_bh_cores",
        "storm_bh_hold",
        "storm_bh_shards",
    ];
    for id in new {
        let q = map
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap_or_else(|| panic!("no quest {id}"));
        assert!((60..=65).contains(&q.level), "{id} level {}", q.level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{id}");
        assert!(q.reward_gold >= 3000, "{id}");
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
                        .any(|s| s.zone == FLATS && s.kind == o.target && s.ambush.is_none()),
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
    // the two elite quests: one kill, a group, a blue reward
    for (id, kind, players) in [
        ("stormglass_hermit", "lamphermit", 3),
        ("stormglass_heart", "maelstromheart", 5),
    ] {
        let q = map.quests.iter().find(|q| q.id == id).unwrap();
        assert!(q.group);
        assert_eq!(q.recommended_players, players, "{id}");
        assert!(q.objectives.len() == 1 && q.objectives[0].target == kind);
        let reward = item(q.reward_item.as_deref().unwrap()).unwrap();
        assert_eq!(reward.rarity, "rare", "{id}");
    }
    assert!(
        !map.quests
            .iter()
            .any(|q| q.objectives.iter().any(|o| o.target == "stormtusk")),
        "the Stormtusk has no quest"
    );
    // the sea is gone: no quest text sends anyone to a shore, a strand or the surf (read from the data: the server keeps no descriptions)
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    for q in raw["zones"][FLATS - 1]["quests"].as_array().unwrap() {
        let id = q["id"].as_str().unwrap();
        if id.starts_with("es_") {
            continue; // The Empty Seat's texts belong to scripts/empty_seat.py
        }
        for key in ["title", "description"] {
            let text = q[key].as_str().unwrap();
            let t = text.to_lowercase();
            for word in ["shore", "strand", "surf", "coast", "beach", "cliff"] {
                assert!(!t.contains(word), "{id} says {word}: {text}");
            }
        }
    }
    // the travel quest's objective names the renamed zone
    let onward = map
        .quests
        .iter()
        .find(|q| q.id == "stormglass_onward")
        .unwrap();
    assert_eq!(onward.objectives[0].target, "The Stormglass Flats");
    assert!(w.maps.iter().any(|m| m.name == onward.objectives[0].target));
    // every hold circle has both of its waves asleep beside it
    for hold in [
        "storm_lamp_m",
        "storm_rod_m",
        "storm_beacon_m",
        "storm_wall_m",
    ] {
        let p = map.places.iter().find(|p| p.id == hold).unwrap();
        for wave in ['a', 'b'] {
            let tag = format!("{hold}#{wave}");
            let sleepers: Vec<_> = w
                .spawns
                .iter()
                .filter(|s| s.zone == FLATS && s.ambush.as_deref() == Some(tag.as_str()))
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
    // the chain stays whole: the old quests are all still here
    for id in [
        "stormglass_welcome",
        "stormglass_crabs",
        "stormglass_gulls",
        "stormglass_rays",
        "stormglass_guards",
        "stormglass_eye",
        "stormglass_depth",
        "stormglass_ward",
        "stormglass_heart",
        "stormglass_patrol",
        "stormglass_onward",
        "es_15",
        "es_go_15",
    ] {
        assert!(map.quests.iter().any(|q| q.id == id), "{id}");
    }
}

#[test]
fn the_three_elites_have_stats_materials_names_and_stand_clear_of_everything_walked_to() {
    for (kind, level) in ELITES {
        assert!(is_elite(kind), "{kind}");
        assert_eq!(Slime::default_level(kind), level, "{kind}");
        let m = material(kind);
        let i = item(m).expect("the material is in the catalog");
        assert_eq!((i.kind.as_str(), i.rarity.as_str()), ("material", "common"));
        let s = Slime::with_level(
            0,
            &SlimeSpawn {
                ambush: None,
                x: 5.,
                y: 5.,
                kind: kind.into(),
                zone: FLATS,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 100_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("lamphermit"), "hermit_lens");
    assert_eq!(material("stormtusk"), "tusk_storm");
    let w = world();
    let map = &w.maps[FLATS];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == FLATS && s.kind == kind)
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
        for p in map.portals.iter().filter(|p| p.seam.is_none()) {
            assert!(
                at(p.x, p.y).distance(at(e.x, e.y)) > awareness,
                "{kind} near {}",
                p.id
            );
        }
    }
    // each stands in its own part of the flats
    let find = |k: &str| {
        w.spawns
            .iter()
            .find(|s| s.zone == FLATS && s.kind == k)
            .unwrap()
    };
    assert!(
        find("maelstromheart").y < 80. && find("maelstromheart").x > 150.,
        "the Heart stands at the foot of the Stormspire in the north"
    );
    assert!(
        find("lamphermit").x < 100. && find("lamphermit").y > 200.,
        "the Hermit drags its lamphouse across the Salt Pans in the south-west"
    );
    assert!(
        find("stormtusk").x > 220. && find("stormtusk").y > 250.,
        "the Stormtusk roams the Low Shards in the south-east"
    );
}

#[test]
fn the_eye_below_and_its_meeting_stone_moved_together() {
    let w = world();
    let map = &w.maps[FLATS];
    let eye = map
        .portals
        .iter()
        .find(|p| p.id == "stormglass_eye_descent")
        .unwrap();
    for id in ["stormglass_watcher", "stormglass_stone"] {
        let n = map.npcs.iter().find(|n| n.id == id).unwrap();
        assert!(
            at(n.x, n.y).distance(at(eye.x, eye.y)) < 22.,
            "{id} stands at the Eye"
        );
    }
    let place = map
        .places
        .iter()
        .find(|p| p.id == "stormglass_eye")
        .unwrap();
    assert!(at(place.x, place.y).distance(at(eye.x, eye.y)) < 8.);
    let seat = map.places.iter().find(|p| p.id == "es_15_m").unwrap();
    let foe = w
        .spawns
        .iter()
        .find(|s| s.zone == FLATS && s.ambush.as_deref() == Some("empty-seat:es_15_m"))
        .expect("the Empty Seat's foe sleeps at its place");
    assert!(at(foe.x, foe.y).distance(at(seat.x, seat.y)) < 6.);
}

#[test]
fn the_four_flats_mailboxes_stand_on_free_ground_with_a_clear_line_to_their_travel_master() {
    let w = world();
    let map = &w.maps[FLATS];
    for (box_id, master_id) in [
        ("mailbox_19_breakwater_camp", "travel_breakwater"),
        ("mailbox_19_rodstead", "travel_rodstead"),
        ("mailbox_19_fulgur", "travel_fulgur"),
        ("mailbox_19_bankhold", "travel_bankhold"),
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
        assert!(
            map.portals
                .iter()
                .filter(|p| p.seam.is_none())
                .all(|p| point.distance(at(p.x, p.y)) > p.r + 1.5),
            "{box_id} stands on a portal"
        );
    }
    let directory: Value =
        serde_json::from_str(include_str!("../../../world/mailboxes.txt")).unwrap();
    let mine = directory
        .as_array()
        .unwrap()
        .iter()
        .filter(|d| d["zone"] == FLATS)
        .count();
    assert_eq!(mine, 4, "the directory lists the camp and three outposts");
}
