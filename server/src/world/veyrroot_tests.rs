//! The Veyrroot Canopy (zone 23, levels 80-84) as an authored WILD jungle on the shapes pilot: its data, the Sunward Vale gate, the Hollow Arch to Heartwood, the two seams (the Tanglecrown
//! and the Lapis Erg) with their roads, Rootfoot, the Sunleaf Lookout and three outposts, the quests (holds, visits, brings, kills, the two elite quests) and the three new elites.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const WOOD: usize = 23;
const TANGLE: usize = 22;
const ERG: usize = 25;
const ELITES: [(&str, u32); 3] = [
    ("lanternqueen", 82),
    ("barkcolossus", 84),
    ("ambergolem", 83),
];
const HAMLETS: [(&str, &str); 3] = [
    ("gladewatch", "ve_gw_"),
    ("rootstair", "ve_rs_"),
    ("eastbark", "ve_eb_"),
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
fn the_veyrroot_is_a_wild_wedge_with_four_families_three_elites_five_hubs_and_the_arch() {
    let w = world();
    let map = &w.maps[WOOD];
    assert_eq!(map.name, "Veyrroot Canopy");
    assert_eq!((map.size, map.levels), (352, Some([80, 84])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(map.in_city(map.spawn), "the spawn is Rootfoot");
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == WOOD) {
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
        ("sapbeetle", 25),
        ("lanternhornet", 30),
        ("mosslemur", 25),
        ("barkmimic", 25),
    ] {
        assert!(live[kind] >= floor, "{kind}: {}", live[kind]);
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind], 1, "{kind}");
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][WOOD - 1];
    assert_eq!(zone["city"]["name"], "Rootfoot");
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
            "Eastbark Post",
            "Gladewatch Post",
            "Rootstair Post",
            "Sunleaf Lookout"
        ]
    );
    let masters = map.npcs.iter().filter(|n| n.travel_stop.is_some()).count();
    assert_eq!(
        masters, 5,
        "Rootfoot and four camps each have a Spark master"
    );
    let objects = zone["objects"].as_array().unwrap();
    for (kind, floor) in [
        ("vr_canopy_tree", 150),
        ("vr_fernbank", 150),
        ("buttress_root", 40),
        ("hanging_pod", 30),
        ("epiphyte_garden", 50),
    ] {
        assert!(
            objects.iter().filter(|o| o["kind"] == kind).count() >= floor,
            "{kind}"
        );
    }
    assert_eq!(
        objects
            .iter()
            .filter(|o| o["kind"] == "worldheart_trunk")
            .count(),
        1,
        "one Great Tree"
    );
    // the Spark network is not an island: Rootfoot links the camps, Banyan Landing's master and Azure Wells'
    let master = map.npcs.iter().find(|n| n.id == "travel_veyrroot").unwrap();
    for id in [
        "travel_banyan",
        "travel_azure_wells",
        "travel_gladewatch",
        "travel_rootstair",
        "travel_eastbark",
        "travel_lookout",
    ] {
        assert!(master.travel_links.iter().any(|l| l == id), "{id}");
    }
}

#[test]
fn the_borders_to_the_tanglecrown_and_the_lapis_erg_are_seams_with_roads_across_and_sunward_is_a_seam_too()
 {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in data["zones"][zi - 1]["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == WOOD || to == WOOD) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> =
        [(22, 23), (23, 22), (23, 25), (25, 23), (20, 23), (23, 20)].into();
    assert_eq!(pairs, want, "three seams, seen from both sides");
    let w = world();
    let zone = &data["zones"][WOOD - 1];
    // both seam portals stand where the approved neighbours' roads end, and a road of this zone meets each
    for (other, x) in [(TANGLE, 118.5), (ERG, 191.5)] {
        let mine = w.maps[WOOD]
            .portals
            .iter()
            .find(|p| p.to == other)
            .expect("the seam portal");
        assert!((mine.x - x).abs() < 1., "{other}: {} {}", mine.x, mine.y);
        let theirs = w.maps[other]
            .portals
            .iter()
            .find(|p| p.to == WOOD)
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
        assert!(near, "a road meets the seam to {other}");
    }
    let sunward = w.maps[WOOD]
        .portals
        .iter()
        .find(|p| p.id == "path_23_20")
        .unwrap();
    assert!(
        sunward.walk.is_none() && sunward.seam.is_some() && sunward.to == 20,
        "the Sunward border is a seam since 2026-11-09"
    );
    assert!(
        w.maps[WOOD]
            .portals
            .iter()
            .all(|p| p.to != HEARTWOOD || p.id == "canopy_hollow_gate")
    );
}

const HEARTWOOD: usize = 24;

#[test]
fn the_hollow_arch_works_and_the_arrival_is_clear() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    // the Hollow Arch and Heartwood's way back
    let arch = w.maps[WOOD]
        .portals
        .iter()
        .find(|p| p.id == "canopy_hollow_gate")
        .unwrap()
        .clone();
    assert_eq!(arch.to, HEARTWOOD);
    let mut foot = at(arch.x, arch.y);
    w.maps[WOOD].collide(&mut foot, PLAYER_RADIUS);
    assert!(
        foot.distance(at(arch.x, arch.y)) < 1e-6,
        "the arch is not blocked"
    );
    let way_back = w.maps[HEARTWOOD]
        .portals
        .iter()
        .find(|p| p.id == "hollow_canopy_gate")
        .unwrap();
    assert_eq!(way_back.to, WOOD);
    let arrival = at(way_back.tx, way_back.ty);
    assert!(
        arrival.distance(at(arch.x, arch.y)) < 12.,
        "Heartwood returns beside the arch"
    );
    let mut a = arrival;
    w.maps[WOOD].collide(&mut a, PLAYER_RADIUS);
    assert!(
        a.distance(arrival) < 1e-6,
        "the arch arrival is on free ground"
    );
    assert!(
        w.spawns
            .iter()
            .filter(|s| s.zone == WOOD)
            .all(|s| at(s.x, s.y).distance(arrival) > 8.)
    );
}

#[test]
fn a_hero_crosses_both_seams_and_comes_back() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (other, dy) in [(TANGLE, 1.), (ERG, -1.)] {
        let p = w.maps[WOOD]
            .portals
            .iter()
            .find(|p| p.to == other)
            .unwrap()
            .clone();
        place(&mut w, 1, WOOD, at(p.x, p.y - dy * 3.));
        w.message(
            1,
            ClientMessage::Move {
                x: p.x,
                y: p.y + dy * 4.,
            },
        );
        run(&mut w, &mut rx, 80);
        assert_eq!(
            w.players[&1].character.zone, other,
            "walking over the seam to {other}"
        );
        let q = w.maps[other]
            .portals
            .iter()
            .find(|q| q.to == WOOD)
            .unwrap()
            .clone();
        place(&mut w, 1, other, at(q.x, q.y + dy * 3.));
        w.message(
            1,
            ClientMessage::Move {
                x: q.x,
                y: q.y - dy * 4.,
            },
        );
        run(&mut w, &mut rx, 80);
        assert_eq!(
            w.players[&1].character.zone, WOOD,
            "walking back over the seam from {other}"
        );
    }
}

#[test]
fn everyone_and_everything_in_the_veyrroot_can_be_walked_to_from_rootfoot() {
    let w = world();
    let map = &w.maps[WOOD];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == WOOD) {
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
        let map = &w.maps[WOOD];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(master.travel_links.iter().any(|l| l == "travel_veyrroot"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_23_{key}")),
            "a mailbox at {key}"
        );
        let mut people: Vec<_> = map
            .npcs
            .iter()
            .filter(|n| n.id.starts_with(prefix))
            .collect();
        if key == "rootstair" {
            // Miri Nectar, the old nectar keeper, is this post's second giver
            people.extend(map.npcs.iter().filter(|n| n.id == "heart_apiarist"));
        }
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
        place(&mut w, 1, WOOD, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
    // Rootfoot keeps the old Canopy people (their ids are saved progress) and the Meeting Stone; the lookout stands at the observatory
    let map = &w.maps[WOOD];
    for id in [
        "heart_matriarch",
        "heart_ranger",
        "heart_healer",
        "heart_trader",
        "heart_stone",
        "travel_veyrroot",
        "mailbox_23_veyrroot_canopy",
    ] {
        let n = map.npcs.iter().find(|n| n.id == id).expect(id);
        assert!(map.in_city(at(n.x, n.y)), "{id} stands in Rootfoot");
    }
    let lookout = map.npcs.iter().find(|n| n.id == "heart_lookout").unwrap();
    let obs = map
        .places
        .iter()
        .find(|p| p.id == "heart_observatory")
        .unwrap();
    assert!(at(lookout.x, lookout.y).distance(at(obs.x, obs.y)) < 8.);
}

#[test]
fn the_veyrroot_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let m = &w.maps[WOOD];
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
                    w.spawns
                        .iter()
                        .any(|s| s.zone == WOOD && s.kind == o.target),
                    "{}: nothing to kill: {}",
                    q.id,
                    o.target
                ),
                "bring" => assert!(item(&o.target).is_some(), "{}: no item {}", q.id, o.target),
                _ => {}
            }
        }
    }
    assert!(m.quests.len() >= 25, "{} quests", m.quests.len());
    for id in [
        "heart_welcome",
        "heart_walkways",
        "heart_lanterns",
        "heart_gardens",
        "heart_market",
        "heart_circuits",
        "heart_patrol",
        "es_19",
        "es_go_19",
    ] {
        assert!(ids.contains(&id), "the old {id} keeps its id");
    }
    let new = ids.iter().filter(|i| i.starts_with("veyr_")).count();
    assert_eq!(new, 16, "sixteen new quests");
    for q in &m.quests {
        assert!(format!("quest:accept:{}", q.id).len() <= 32, "{}", q.id);
    }
    for id in ["veyr_queen", "veyr_colossus"] {
        let q = m.quests.iter().find(|q| q.id == id).unwrap();
        assert!(q.group && q.reward_item.is_some(), "{id}");
        assert!(!q.reward_choices.is_empty(), "{id} offers class choices");
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
                zone: WOOD,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 1_000_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("lanternqueen"), "queen_amber");
    assert_eq!(material("barkcolossus"), "heartbark_slab");
    assert_eq!(material("ambergolem"), "golem_amber");
    let w = world();
    let map = &w.maps[WOOD];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == WOOD && s.kind == kind)
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
            .find(|s| s.zone == WOOD && s.kind == k)
            .unwrap()
    };
    assert!(
        find("lanternqueen").x < 180. && find("lanternqueen").y < 140.,
        "the queen keeps her hive in the north-western canopy"
    );
    assert!(
        find("barkcolossus").x > 260. && find("barkcolossus").y < 160.,
        "the colossus walks the Eastern Roots"
    );
    assert!(
        find("ambergolem").y > 230.,
        "the golem stands on the southern sap flats"
    );
}

#[test]
fn the_empty_seat_stays_at_the_great_tree_and_the_mailboxes_stand_on_free_ground() {
    let w = world();
    let m = &w.maps[WOOD];
    let memory = m.places.iter().find(|p| p.id == "es_19_m").unwrap();
    let rootfoot = at(210., 241.);
    assert!(
        at(memory.x, memory.y).distance(rootfoot) < 25.,
        "the memory is at the foot of the Great Tree"
    );
    let open = flood(m, &blocked(m, &[]), m.spawn);
    assert!(reached(m, &open, at(memory.x, memory.y)));
    for n in m.npcs.iter().filter(|n| n.id.starts_with("mailbox_23_")) {
        let mut foot = at(n.x, n.y);
        m.collide(&mut foot, PLAYER_RADIUS);
        assert!(foot.distance(at(n.x, n.y)) < 1e-6, "{} is blocked", n.id);
        assert!(reached(m, &open, at(n.x, n.y)));
    }
}

#[test]
fn veyrroot_enemies_materials_elites_and_quest_rewards_are_registered() {
    let w = world();
    let m = &w.maps[WOOD];
    for (kind, level, drop) in [
        ("sapbeetle", 80, "sapbeetle_resin"),
        ("lanternhornet", 80, "hornet_amber"),
        ("mosslemur", 80, "mosslemur_fur"),
        ("barkmimic", 80, "barkmimic_chip"),
        ("lanternqueen", 82, "queen_amber"),
        ("ambergolem", 83, "golem_amber"),
        ("barkcolossus", 84, "heartbark_slab"),
    ] {
        assert!(w.spawns.iter().any(|s| s.zone == WOOD && s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 300000. && damage > 5000.);
    }
    assert!(is_elite("lanternqueen") && is_elite("barkcolossus") && is_elite("ambergolem"));
    assert!(!is_elite("barkmimic"));
    for q in &m.quests {
        if q.id.starts_with("es_go_") {
            continue; // a hand-off pays nothing
        }
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "veyr_rf_hold",
        "veyr_rounds",
        "veyr_gw_hold",
        "veyr_gw_flats",
        "veyr_rs_hold",
        "veyr_rs_hive",
        "veyr_eb_hold",
        "veyr_eb_grove",
        "veyr_queen",
        "veyr_colossus",
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
    for route in data["zones"][WOOD - 1]["exitRoutes"].as_array().unwrap() {
        let points = route["points"].as_array().unwrap();
        for pair in points.windows(2) {
            let p = |v: &Value| at(v[0].as_f64().unwrap(), v[1].as_f64().unwrap());
            assert!(
                w.maps[WOOD].line_clear(p(&pair[0]), p(&pair[1]), PLAYER_RADIUS),
                "the exit route of {} is blocked: {:?} -> {:?}",
                route["portal"],
                pair[0],
                pair[1]
            );
        }
    }
}
