//! Cairnspine (zone 27, levels 90-95) as an authored mountain pass on the shapes pilot: its data, the seam to the Prismwaste with a road across, the Frostwake rim gate and the
//! Thunderheart Gate door, Boulderwatch and three outposts, the quests (holds, visits, brings, kills, the three elite quests) and the four elites (one new, no quest).
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const CAIRN: usize = 27;
const PRISM: usize = 14;
const FROSTWAKE: usize = 26;
const THUNDER: usize = 35;
const ELITES: [(&str, u32); 4] = [
    ("cairnbehemoth", 93),
    ("whitebarktitan", 94),
    ("stormcondor", 95),
    ("avalanchebear", 92),
];
const HAMLETS: [(&str, &str); 3] = [
    ("singing", "cn_sc_"),
    ("whitebark", "cn_wb_"),
    ("stormgate", "cn_sg_"),
];
/// the inland normal of the seam (it runs south-west to north-east): from the Prismwaste into Cairnspine
const NORMAL: (f64, f64) = (214. / 246., -122. / 246.);

fn run(w: &mut World, rx: &mut mpsc::Receiver<Value>, ticks: usize) -> Vec<String> {
    let mut told = vec![];
    for _ in 0..ticks {
        w.step();
        told.extend(lines(rx));
    }
    told
}

#[test]
fn cairnspine_is_a_mountain_shield_with_four_families_four_elites_four_hubs_and_the_door() {
    let w = world();
    let map = &w.maps[CAIRN];
    assert_eq!(map.name, "The Cairnspine");
    assert_eq!((map.size, map.levels), (272, Some([90, 95])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(map.in_city(map.spawn), "the spawn is Boulderwatch");
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == CAIRN) {
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
        ("screeferret", 20),
        ("stoneibex", 15),
        ("slateraven", 20),
        ("ridgeadder", 10),
    ] {
        assert!(live[kind] >= floor, "{kind}: {}", live[kind]);
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind], 1, "{kind}");
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][CAIRN - 1];
    assert_eq!(zone["city"]["name"], "Boulderwatch");
    let mut names: Vec<_> = zone["camps"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["name"].as_str().unwrap())
        .collect();
    names.sort();
    assert_eq!(
        names,
        ["Singing Cairn Post", "Stormgate Camp", "Whitebark Post"]
    );
    let masters = map.npcs.iter().filter(|n| n.travel_stop.is_some()).count();
    assert_eq!(
        masters, 4,
        "Boulderwatch and three camps each have a Spark master"
    );
    let objects = zone["objects"].as_array().unwrap();
    for (kind, floor) in [
        ("cairn_boulder", 100),
        ("cairn_pebble", 150),
        ("cairn_dead_tree", 70),
        ("cairn_slate_spire", 70),
        ("cairn_stack", 30),
        ("cairn_lichen_rock", 30),
    ] {
        assert!(
            objects.iter().filter(|o| o["kind"] == kind).count() >= floor,
            "{kind}"
        );
    }
    assert_eq!(zone["futureInstance"]["status"], "open");
    // the Spark network is not an island: Boulderwatch links the camps, Frostwake Station and the Prismwaste's Cairnfoot
    let master = map
        .npcs
        .iter()
        .find(|n| n.id == "travel_boulderwatch")
        .unwrap();
    for id in [
        "travel_frostwake",
        "travel_cairnfoot",
        "travel_singing",
        "travel_whitebark",
        "travel_stormgate",
    ] {
        assert!(master.travel_links.iter().any(|l| l == id), "{id}");
    }
    assert!(
        w.maps[FROSTWAKE]
            .npcs
            .iter()
            .find(|n| n.id == "travel_frostwake")
            .unwrap()
            .travel_links
            .contains(&"travel_boulderwatch".to_string())
    );
}

#[test]
fn the_border_to_the_prismwaste_is_a_seam_with_a_road_across_and_frostwake_stays_a_gate() {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in data["zones"][zi - 1]["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == CAIRN || to == CAIRN) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> = [(14, 27), (27, 14)].into();
    assert_eq!(pairs, want, "one seam, seen from both sides");
    let w = world();
    let zone = &data["zones"][CAIRN - 1];
    let mine = w.maps[CAIRN]
        .portals
        .iter()
        .find(|p| p.to == PRISM)
        .expect("the seam portal");
    assert!(
        (mine.x - 97.88).abs() < 1. && (mine.y - 178.).abs() < 1.,
        "the seam crosses where the Prismwaste's road ends: {} {}",
        mine.x,
        mine.y
    );
    let theirs = w.maps[PRISM]
        .portals
        .iter()
        .find(|p| p.to == CAIRN)
        .expect("the far seam portal");
    assert!(
        (theirs.x - mine.tx).abs() < 1e-6 && (theirs.y - mine.ty).abs() < 1e-6,
        "the two portals face each other"
    );
    let near = zone["paths"].as_array().unwrap().iter().any(|road| {
        road.as_array().unwrap().iter().any(|q| {
            let (qx, qy) = (q[0].as_f64().unwrap(), q[1].as_f64().unwrap());
            ((qx - mine.x).powi(2) + (qy - mine.y).powi(2)).sqrt() < 2.
        })
    });
    assert!(near, "a road of this zone meets the seam");
    let gate = w.maps[CAIRN]
        .portals
        .iter()
        .find(|p| p.id == "cairn_frostwake_gate")
        .unwrap();
    assert!(gate.walk.is_some() && gate.to == FROSTWAKE);
    assert!(
        w.maps[CAIRN]
            .portals
            .iter()
            .all(|p| p.to == PRISM || p.to == FROSTWAKE || p.to == THUNDER),
        "the Prismwaste seam, the Frostwake gate and the Thunderheart door are the only crossings"
    );
}

#[test]
fn the_frostwake_gate_and_the_thunderheart_door_work_and_the_arrivals_are_clear() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let gate = w.maps[CAIRN]
        .portals
        .iter()
        .find(|p| p.id == "cairn_frostwake_gate")
        .unwrap()
        .clone();
    let side = gate.walk.expect("a walk-in gate");
    place(&mut w, 1, CAIRN, at(gate.x, gate.y));
    w.message(
        1,
        ClientMessage::Move {
            x: gate.x + f64::from(side[0]) * 3.,
            y: gate.y + f64::from(side[1]) * 3.,
        },
    );
    run(&mut w, &mut rx, 40);
    assert_eq!(
        w.players[&1].character.zone, FROSTWAKE,
        "Frostwake is reached"
    );
    let back = w.maps[FROSTWAKE]
        .portals
        .iter()
        .find(|p| p.id == "frostwake_cairn_gate")
        .unwrap()
        .clone();
    assert_eq!(back.to, CAIRN);
    let arrival = at(back.tx, back.ty);
    assert!(
        arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
            && arrival.distance(at(gate.x, gate.y)) < 8.
    );
    let mut a = arrival;
    w.maps[CAIRN].collide(&mut a, PLAYER_RADIUS);
    assert!(
        a.distance(arrival) < 1e-6,
        "the Frostwake arrival is on free ground"
    );
    assert!(
        w.spawns
            .iter()
            .filter(|s| s.zone == CAIRN)
            .all(|s| at(s.x, s.y).distance(arrival) > 8.),
        "an enemy stands near the Frostwake arrival"
    );
    // the Thunderheart Gate: the door stands on free ground and both of the dungeon's ways home arrive beside it
    let door = w.maps[CAIRN]
        .portals
        .iter()
        .find(|p| p.id == "cairn_thunderheart_gate")
        .unwrap()
        .clone();
    assert_eq!(door.to, THUNDER);
    let mut foot = at(door.x, door.y);
    w.maps[CAIRN].collide(&mut foot, PLAYER_RADIUS);
    assert!(
        foot.distance(at(door.x, door.y)) < 1e-6,
        "the door is not blocked"
    );
    for id in ["thunderheart_gate_return", "thunderheart_gate_exit"] {
        let home = w.maps[THUNDER].portals.iter().find(|p| p.id == id).unwrap();
        assert_eq!(home.to, CAIRN);
        let arrival = at(home.tx, home.ty);
        assert!(
            arrival.distance(at(door.x, door.y)) < 10.,
            "{id} returns beside the door"
        );
        let mut a = arrival;
        w.maps[CAIRN].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{id} arrives on free ground");
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == CAIRN)
                .all(|s| at(s.x, s.y).distance(arrival) > 8.),
            "{id}: an enemy stands at the arrival"
        );
    }
    let stand = w.maps[CAIRN]
        .places
        .iter()
        .find(|p| p.id == "cairn_thunder")
        .unwrap();
    assert!(at(stand.x, stand.y).distance(at(door.x, door.y)) < 10.);
}

#[test]
fn a_hero_crosses_the_seam_and_comes_back() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let p = w.maps[CAIRN]
        .portals
        .iter()
        .find(|p| p.to == PRISM)
        .unwrap()
        .clone();
    place(
        &mut w,
        1,
        CAIRN,
        at(p.x + NORMAL.0 * 3., p.y + NORMAL.1 * 3.),
    );
    w.message(
        1,
        ClientMessage::Move {
            x: p.x - NORMAL.0 * 4.,
            y: p.y - NORMAL.1 * 4.,
        },
    );
    run(&mut w, &mut rx, 80);
    assert_eq!(
        w.players[&1].character.zone, PRISM,
        "walking over the seam to the Prismwaste"
    );
    let q = w.maps[PRISM]
        .portals
        .iter()
        .find(|q| q.to == CAIRN)
        .unwrap()
        .clone();
    place(
        &mut w,
        1,
        PRISM,
        at(q.x - NORMAL.0 * 3., q.y - NORMAL.1 * 3.),
    );
    w.message(
        1,
        ClientMessage::Move {
            x: q.x + NORMAL.0 * 4.,
            y: q.y + NORMAL.1 * 4.,
        },
    );
    run(&mut w, &mut rx, 80);
    assert_eq!(
        w.players[&1].character.zone, CAIRN,
        "walking back over the seam"
    );
}

#[test]
fn everyone_and_everything_in_cairnspine_can_be_walked_to_from_boulderwatch() {
    let w = world();
    let map = &w.maps[CAIRN];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == CAIRN) {
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
    for (key, prefix) in HAMLETS {
        let map = &w.maps[CAIRN];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(
            master
                .travel_links
                .iter()
                .any(|l| l == "travel_boulderwatch")
        );
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_27_{key}")),
            "a mailbox at {key}"
        );
        let mut people: Vec<_> = map
            .npcs
            .iter()
            .filter(|n| n.id.starts_with(prefix))
            .collect();
        // the old Cairnspine givers moved into the camps: the stone singer, the grove keeper and the windseer
        let old = match key {
            "singing" => "cairn_stonesinger",
            "whitebark" => "cairn_grovekeeper",
            _ => "cairn_windseer",
        };
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
        place(&mut w, 1, CAIRN, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
    // Boulderwatch keeps the old Cairnspine people (their ids are saved progress); the Meeting Stone stands at the Stormgate Camp
    let map = &w.maps[CAIRN];
    for id in [
        "cairn_warden",
        "cairn_healer",
        "cairn_surveyor",
        "cairn_trader",
        "cairn_scout",
        "travel_boulderwatch",
        "mailbox_27_boulderwatch",
    ] {
        let n = map.npcs.iter().find(|n| n.id == id).expect(id);
        assert!(map.in_city(at(n.x, n.y)), "{id} stands in Boulderwatch");
    }
    let stone = map.npcs.iter().find(|n| n.id == "cairn_stone").unwrap();
    let master = map
        .npcs
        .iter()
        .find(|n| n.id == "travel_stormgate")
        .unwrap();
    let camp = map
        .camps
        .iter()
        .find(|k| at(master.x, master.y).distance(at((k.x0 + k.x1) / 2., (k.y0 + k.y1) / 2.)) < 12.)
        .unwrap();
    assert!(stone.x >= camp.x0 && stone.x <= camp.x1 && stone.y >= camp.y0 && stone.y <= camp.y1);
}

#[test]
fn the_cairnspine_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let m = &w.maps[CAIRN];
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
        "cairn_welcome",
        "cairn_ferrets",
        "cairn_ibex",
        "cairn_ravens",
        "cairn_adders",
        "cairn_behemoth",
        "cairn_titan",
        "cairn_condor",
        "cairn_gate",
        "cairn_storm_trials",
        "cairn_thunder_final",
        "cairn_patrol",
        "cairn_onward",
        "es_23",
        "es_go_23",
    ] {
        assert!(ids.contains(&id), "the old {id} keeps its id");
    }
    let new = ids.iter().filter(|i| i.starts_with("crn_")).count();
    assert_eq!(new, 14, "fourteen new quests");
    for q in &m.quests {
        assert!(format!("quest:accept:{}", q.id).len() <= 32, "{}", q.id);
    }
    for id in ["cairn_behemoth", "cairn_titan", "cairn_condor"] {
        let q = m.quests.iter().find(|q| q.id == id).unwrap();
        assert!(q.group && q.reward_item.is_some(), "{id}");
        assert!(!q.reward_choices.is_empty(), "{id} offers class choices");
    }
    assert!(
        m.quests
            .iter()
            .all(|q| !q.objectives.iter().any(|o| o.target == "avalanchebear")),
        "the Avalanche Bear has no quest"
    );
}

#[test]
fn the_four_elites_have_stats_materials_names_and_stand_clear_of_everything_walked_to() {
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
                zone: CAIRN,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 1_000_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("avalanchebear"), "avalanche_claw");
    let w = world();
    let map = &w.maps[CAIRN];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == CAIRN && s.kind == kind)
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
            .find(|s| s.zone == CAIRN && s.kind == k)
            .unwrap()
    };
    assert!(
        find("cairnbehemoth").y > 220.,
        "the behemoth walks the southern toe"
    );
    assert!(
        find("whitebarktitan").y < 80. && find("whitebarktitan").x > 100.,
        "the titan stands in the Whitebark Wood"
    );
    assert!(
        find("stormcondor").x > 180. && find("stormcondor").y < 60.,
        "the condor hunts the north-eastern spires"
    );
    assert!(
        find("avalanchebear").x < 90. && find("avalanchebear").y < 80.,
        "the bear sleeps in the Hollow Peaks"
    );
}

#[test]
fn the_empty_seats_bells_stand_at_the_singing_cairn_and_the_mailboxes_stand_on_free_ground() {
    let w = world();
    let m = &w.maps[CAIRN];
    let cairn = m.places.iter().find(|p| p.id == "cairn_stones").unwrap();
    let open = flood(m, &blocked(m, &[]), m.spawn);
    for i in 0..3 {
        let bell = m
            .places
            .iter()
            .find(|p| p.id == format!("es_23_{i}"))
            .unwrap();
        assert!(
            at(bell.x, bell.y).distance(at(cairn.x, cairn.y)) < 20.,
            "bell {i} stands at the Singing Cairn"
        );
        assert!(reached(m, &open, at(bell.x, bell.y)));
    }
    for n in m.npcs.iter().filter(|n| n.id.starts_with("mailbox_27_")) {
        let mut foot = at(n.x, n.y);
        m.collide(&mut foot, PLAYER_RADIUS);
        assert!(foot.distance(at(n.x, n.y)) < 1e-6, "{} is blocked", n.id);
        assert!(reached(m, &open, at(n.x, n.y)));
    }
}

#[test]
fn cairnspine_enemies_materials_elites_and_quest_rewards_are_registered() {
    let w = world();
    let m = &w.maps[CAIRN];
    for (kind, level, drop) in [
        ("screeferret", 90, "screeferret_pelt"),
        ("stoneibex", 91, "ibex_horn"),
        ("slateraven", 92, "slate_raven_feather"),
        ("ridgeadder", 93, "ridgeadder_scale"),
        ("avalanchebear", 92, "avalanche_claw"),
        ("cairnbehemoth", 93, "behemoth_heartstone"),
        ("whitebarktitan", 94, "whitebark_core"),
        ("stormcondor", 95, "stormcondor_plume"),
    ] {
        assert!(w.spawns.iter().any(|s| s.zone == CAIRN && s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 600000. && damage > 8000.);
    }
    assert!(!is_elite("screeferret"));
    assert_eq!(
        m.slimes.iter().filter(|s| is_elite(&s.kind)).count(),
        4,
        "four elites"
    );
    for q in &m.quests {
        if q.id.starts_with("es_go_") {
            continue; // a hand-off pays nothing
        }
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "cairn_ferrets",
        "cairn_ibex",
        "cairn_behemoth",
        "cairn_titan",
        "cairn_condor",
        "crn_bw_hold",
        "crn_rounds",
        "crn_sc_hold",
        "crn_sc_adders",
        "crn_wb_hold",
        "crn_wb_wood",
        "crn_sg_hold",
        "crn_sg_spires",
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
    for route in data["zones"][CAIRN - 1]["exitRoutes"].as_array().unwrap() {
        let points = route["points"].as_array().unwrap();
        for pair in points.windows(2) {
            let p = |v: &Value| at(v[0].as_f64().unwrap(), v[1].as_f64().unwrap());
            assert!(
                w.maps[CAIRN].line_clear(p(&pair[0]), p(&pair[1]), PLAYER_RADIUS),
                "the exit route of {} is blocked: {:?} -> {:?}",
                route["portal"],
                pair[0],
                pair[1]
            );
        }
    }
}
