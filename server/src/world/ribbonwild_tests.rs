//! The Ribbonwild (zone 21, levels 70-75) as an authored wheel of colour courts on the shapes pilot: its data, the two gates and the Emberwake seam, Jubilee
//! Crossroads, the Pavilion camp and three outposts, the quests (holds, visits, brings, kills, the two elite quests) and the new elite with no quest.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const FAIR: usize = 21;
const ELITES: [(&str, u32); 3] = [
    ("paradegryphon", 74),
    ("maskcolossus", 75),
    ("whorlshell", 73),
];
/// (gate, the zone it leads to, the far gate that leads back); the border to Emberwake is a seam, the Pavilion is a door
const GATES: [(&str, usize, &str); 2] = [
    ("ribbon_sun_gate", 20, "sun_ribbon_gate"),
    ("ribbon_tangle_gate", 22, "tangle_ribbon_gate"),
];
const HAMLETS: [(&str, &str); 3] = [
    ("bunting", "rw_bp_"),
    ("tassel", "rw_tp_"),
    ("garland", "rw_gr_"),
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
fn the_ribbonwild_is_a_big_wheel_with_four_families_three_elites_five_hubs_and_the_pavilion_door() {
    let w = world();
    let map = &w.maps[FAIR];
    assert_eq!(map.name, "The Ribbonwild");
    assert_eq!((map.size, map.levels), (368, Some([70, 75])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(map.in_city(map.spawn), "the spawn is Jubilee Crossroads");
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == FAIR) {
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
        ("ribbongecko", 25),
        ("balloonbeetle", 20),
        ("paintedmacaw", 30),
        ("jesterling", 30),
    ] {
        assert!(live[kind] >= floor, "{kind}: {}", live[kind]);
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind], 1, "{kind}");
    }
    for (kind, level) in [
        ("ribbongecko", 70),
        ("balloonbeetle", 71),
        ("paintedmacaw", 72),
        ("jesterling", 73),
    ] {
        assert_eq!(Slime::default_level(kind), level);
        assert!(item(material(kind)).is_some());
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][FAIR - 1];
    assert_eq!(zone["city"]["name"], "Jubilee Crossroads");
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
            "Bunting Post",
            "Garland Rest",
            "Pavilion Steps",
            "Tassel Post"
        ]
    );
    let masters = map.npcs.iter().filter(|n| n.travel_stop.is_some()).count();
    assert_eq!(
        masters, 5,
        "the crossroads and four camps each have a Spark master"
    );
    assert_eq!(zone["futureInstance"]["status"], "open");
    assert_eq!(zone["futureInstance"]["name"], "The Thousandfold Pavilion");
    let objects = zone["objects"].as_array().unwrap();
    for (kind, floor) in [
        ("festival_bloom", 300),
        ("fan_topiary", 100),
        ("pinwheel", 80),
        ("ribbon_pole", 30),
        ("rw_blossom_tree", 20),
    ] {
        assert!(
            objects.iter().filter(|o| o["kind"] == kind).count() >= floor,
            "{kind}"
        );
    }
    // no oak, birch or apple: the meadow's trees have no art here to ghost across the seam
    assert!(!objects.iter().any(|o| matches!(
        o["kind"].as_str(),
        Some("oak_tree" | "birch_tree" | "apple_tree")
    )));
    // the Spark network is not an island: the crossroads links the camps, Sunward's master and the Tanglecrown's
    let master = map.npcs.iter().find(|n| n.id == "travel_jubilee").unwrap();
    for id in [
        "travel_millbridge",
        "travel_banyan",
        "travel_bunting",
        "travel_tassel",
        "travel_garland",
        "travel_pavilion",
    ] {
        assert!(master.travel_links.iter().any(|l| l == id), "{id}");
    }
}

#[test]
fn both_gates_are_walked_through_both_ways_the_door_leads_to_the_pavilion_and_the_arrivals_are_clear()
 {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in GATES {
        let gate = w.maps[FAIR]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        assert_eq!(gate.to, zone, "{gate_id}");
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, FAIR, at(gate.x, gate.y));
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
        assert_eq!(back.to, FAIR, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        assert!(
            arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
                && arrival.distance(at(gate.x, gate.y)) < 8.,
            "{back_id} arrives beside {gate_id}, clear of its disc"
        );
        let mut a = arrival;
        w.maps[FAIR].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == FAIR)
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
        assert_eq!(w.players[&1].character.zone, FAIR, "{back_id} returns");
    }
    // the Pavilion's door stands at the end of the east road, and both its ways out arrive in front of it on free ground
    let door = w.maps[FAIR]
        .portals
        .iter()
        .find(|p| p.id == "ribbon_pavilion_gate")
        .unwrap()
        .clone();
    assert_eq!(door.to, 31);
    for back_id in ["thousandfold_return", "thousandfold_exit"] {
        let back = w.maps[31].portals.iter().find(|p| p.id == back_id).unwrap();
        assert_eq!(back.to, FAIR);
        let arrival = at(back.tx, back.ty);
        assert!(arrival.distance(at(door.x, door.y)) < 14., "{back_id}");
        let mut a = arrival;
        w.maps[FAIR].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
    }
}

#[test]
fn the_ribbonwild_border_to_emberwake_is_a_seam_and_the_other_borders_are_gates() {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in data["zones"][zi - 1]["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == FAIR || to == FAIR) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> = [(21, 45), (45, 21)].into();
    assert_eq!(pairs, want, "one seam to Emberwake, seen from both sides");
}

#[test]
fn everyone_and_everything_in_the_ribbonwild_can_be_walked_to_from_the_crossroads() {
    let w = world();
    let map = &w.maps[FAIR];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == FAIR) {
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
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (key, prefix) in HAMLETS {
        let map = &w.maps[FAIR];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(master.travel_links.iter().any(|l| l == "travel_jubilee"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_21_{key}")),
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
        place(&mut w, 1, FAIR, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
}

#[test]
fn the_ribbonwild_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let map = &w.maps[FAIR];
    let new = [
        "ribbon_jc_hold",
        "ribbon_rounds",
        "ribbon_bp_walk",
        "ribbon_bp_tails",
        "ribbon_bp_hold",
        "ribbon_bp_dance",
        "ribbon_tp_walk",
        "ribbon_tp_plumes",
        "ribbon_tp_hold",
        "ribbon_tp_rosette",
        "ribbon_gr_walk",
        "ribbon_gr_bells",
        "ribbon_gr_hold",
        "ribbon_gr_stair",
    ];
    for id in new {
        let q = map
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap_or_else(|| panic!("no quest {id}"));
        assert!((70..=75).contains(&q.level), "{id} level {}", q.level);
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
                "kill" => assert!(
                    w.spawns
                        .iter()
                        .any(|s| s.zone == FAIR && s.kind == o.target && s.ambush.is_none()),
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
    for (id, kind) in [
        ("ribbon_gryphon", "paradegryphon"),
        ("ribbon_colossus", "maskcolossus"),
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
            .any(|q| q.objectives.iter().any(|o| o.target == "whorlshell")),
        "the Whorlshell has no quest"
    );
    for hold in ["rw_jc_m", "rw_bp_m", "rw_tp_m", "rw_gr_m"] {
        let p = map.places.iter().find(|p| p.id == hold).unwrap();
        for wave in ['a', 'b'] {
            let tag = format!("{hold}#{wave}");
            let sleepers: Vec<_> = w
                .spawns
                .iter()
                .filter(|s| s.zone == FAIR && s.ambush.as_deref() == Some(tag.as_str()))
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
        "ribbon_welcome",
        "ribbon_geckos",
        "ribbon_beetles",
        "ribbon_macaws",
        "ribbon_jesters",
        "ribbon_gryphon",
        "ribbon_colossus",
        "ribbon_curtain",
        "ribbon_folds",
        "ribbon_final",
        "ribbon_circuit",
        "ribbon_onward",
        "es_17",
        "es_go_17",
    ] {
        assert!(map.quests.iter().any(|q| q.id == id), "{id}");
    }
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
                zone: FAIR,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 1_000_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("whorlshell"), "whorl_shell");
    let w = world();
    let map = &w.maps[FAIR];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == FAIR && s.kind == kind)
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
            if matches!(p.id.as_str(), "ribbon_gryphon_court" | "ribbon_mask_court") {
                continue;
            }
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
            .find(|s| s.zone == FAIR && s.kind == k)
            .unwrap()
    };
    assert!(
        find("paradegryphon").y < 120.,
        "the gryphon keeps the Dance Floor in the north"
    );
    assert!(
        find("maskcolossus").x > 260.,
        "the colossus holds the Mask Court in the east"
    );
    assert!(
        find("whorlshell").x < 100.,
        "the Whorlshell sits in the Whorl in the west"
    );
}

#[test]
fn the_empty_seat_moves_with_its_sleeper_and_the_mailboxes_stand_on_free_ground() {
    let w = world();
    let map = &w.maps[FAIR];
    let seat = map.places.iter().find(|p| p.id == "es_17_m").unwrap();
    let foe = w
        .spawns
        .iter()
        .find(|s| s.zone == FAIR && s.ambush.as_deref() == Some("empty-seat:es_17_m"))
        .expect("the Uninvited Guest sleeps at the Empty Seat's place");
    assert!(at(foe.x, foe.y).distance(at(seat.x, seat.y)) < 6.);
    for (box_id, master_id) in [
        ("mailbox_21_jubilee_crossroads", "travel_jubilee"),
        ("mailbox_21_pavilion", "travel_pavilion"),
        ("mailbox_21_bunting", "travel_bunting"),
        ("mailbox_21_tassel", "travel_tassel"),
        ("mailbox_21_garland", "travel_garland"),
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
        .filter(|d| d["zone"] == FAIR)
        .count();
    assert_eq!(
        mine, 5,
        "the directory lists the crossroads, the Pavilion camp and three outposts"
    );
}
