//! The Obsidian Orrery (zone 15, levels 50-55) as an authored plain on the shapes pilot: its data, the five gates and two seams, the refuge and
//! three outposts, the quests (holds, visits, brings, kills, the two elite quests) and the new elite with no quest.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const ORRERY: usize = 15;
const KINDS: [&str; 4] = ["bronzemantis", "gearling", "orbitseer", "chronoguard"];
const ELITES: [(&str, u32); 3] = [
    ("pendulummatron", 54),
    ("epochengine", 55),
    ("mainspringwyrm", 53),
];
/// (gate, the zone it leads to, the far gate that leads back)
const GATES: [(&str, usize, &str); 5] = [
    ("path_15_9", 9, "path_9_15"),
    ("path_15_1", 1, "path_1_15"),
    ("orrery_prism_gate", 14, "prism_orrery_gate"),
    ("path_15_19", 19, "path_19_15"),
    ("atlas_15_45", 45, "atlas_45_15"),
];
const HAMLETS: [(&str, &str); 3] = [
    ("bellcourt", "orrery_bc_"),
    ("crownwatch", "orrery_cn_"),
    ("shardwatch", "orrery_sw_"),
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
fn the_orrery_is_a_big_plain_with_four_families_by_distance_three_elites_four_hubs_five_gates_and_two_seams()
 {
    let w = world();
    let map = &w.maps[ORRERY];
    assert_eq!(map.name, "The Obsidian Orrery");
    assert_eq!((map.size, map.levels), (344, Some([50, 55])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    // the four families, banded from the refuge in the south-west to the Crown Valley in the north
    let mut live = std::collections::BTreeMap::<&str, Vec<f64>>::new();
    for (id, spawn) in w
        .spawns
        .iter()
        .enumerate()
        .filter(|(_, s)| s.zone == ORRERY)
    {
        if spawn.ambush.is_some() {
            assert!(
                w.slimes[id].dead && w.slimes[id].state == "waiting" && w.slimes[id].respawn >= 1e8,
                "an ambusher sleeps"
            );
            continue;
        }
        live.entry(spawn.kind.as_str()).or_default().push(spawn.y);
        assert!(!map.in_city(at(spawn.x, spawn.y)));
        assert!(
            at(spawn.x, spawn.y).distance(map.spawn) > 8.,
            "{} is clear of the refuge",
            spawn.kind
        );
    }
    for (kind, floor) in [
        ("bronzemantis", 60),
        ("gearling", 60),
        ("orbitseer", 60),
        ("chronoguard", 50),
    ] {
        assert!(live[kind].len() >= floor, "{kind}: {}", live[kind].len());
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind].len(), 1, "{kind}");
    }
    assert_eq!(live.len(), 7, "{:?}", live.keys());
    let mean = |k: &str| live[k].iter().sum::<f64>() / live[k].len() as f64;
    for pair in KINDS.windows(2) {
        assert!(
            mean(pair[0]) > mean(pair[1]) + 20.,
            "{} lives south of {}",
            pair[0],
            pair[1]
        );
    }
    for (kind, level) in [
        ("bronzemantis", 50),
        ("gearling", 51),
        ("orbitseer", 52),
        ("chronoguard", 53),
        ("pendulummatron", 54),
        ("epochengine", 55),
        ("mainspringwyrm", 53),
    ] {
        assert_eq!(Slime::default_level(kind), level, "{kind}");
    }
    // the refuge is the zone's `city`, the three outposts are camps; every hub is safe ground with a travel master
    let c = map.city.as_ref().unwrap();
    assert_eq!((c.x1 - c.x0, c.y1 - c.y0), (37., 22.));
    assert_eq!(map.camps.len(), 3);
    for camp in &map.camps {
        assert!(map.in_city(at((camp.x0 + camp.x1) / 2., (camp.y0 + camp.y1) / 2.)));
    }
    for id in [
        "travel_stillpoint",
        "travel_bellcourt",
        "travel_crownwatch",
        "travel_shardwatch",
    ] {
        assert!(
            map.npcs
                .iter()
                .any(|n| n.id == id && n.travel_stop.is_some()),
            "{id}"
        );
    }
    assert!(map.in_city(map.spawn), "a new hero starts in the refuge");
    let mut free = map.spawn;
    map.collide(&mut free, PLAYER_RADIUS);
    assert!(free.distance(map.spawn) < 1e-6, "the spawn is free ground");
    // nine places: five to visit, four hold circles (the Empty Seat's own place is not counted)
    assert_eq!(
        map.places
            .iter()
            .filter(|p| p.id.starts_with("orrery_"))
            .count(),
        9
    );
    // five gates (the Crags, Nacrehold, the Prismwaste, Stormglass, Emberwake) and two seams (Astralhollow, the Canopy)
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
        vec![13, 16],
        "only Astralhollow and the Canopy are seams"
    );
    for (id, to, _) in GATES {
        let g = map.portals.iter().find(|p| p.id == id).expect(id);
        assert!(g.seam.is_none() && g.walk.is_some() && g.to == to, "{id}");
    }
}

#[test]
fn all_five_gates_are_walked_through_both_ways_and_every_arrival_is_clear_ground() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in GATES {
        let gate = w.maps[ORRERY]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        assert_eq!(gate.to, zone, "{gate_id}");
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, ORRERY, at(gate.x, gate.y));
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
        assert_eq!(back.to, ORRERY, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        assert!(
            arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
                && arrival.distance(at(gate.x, gate.y)) < 8.,
            "{back_id} arrives beside {gate_id}, clear of its disc"
        );
        let mut a = arrival;
        w.maps[ORRERY].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        // no enemy within eight tiles of an arrival
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == ORRERY)
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
        assert_eq!(w.players[&1].character.zone, ORRERY, "{back_id} returns");
        let c = &w.players[&1].character;
        assert!(
            at(c.x, c.y).distance(at(gate.x, gate.y)) < 12.,
            "{back_id} puts the hero near {gate_id}"
        );
    }
}

#[test]
fn everyone_and_everything_in_the_orrery_can_be_walked_to_from_the_refuge() {
    let w = world();
    let map = &w.maps[ORRERY];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (id, s) in w
        .spawns
        .iter()
        .enumerate()
        .filter(|(_, s)| s.zone == ORRERY)
    {
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
    let hub = w.maps[ORRERY]
        .npcs
        .iter()
        .find(|n| n.id == "travel_stillpoint")
        .unwrap()
        .clone();
    for (key, prefix) in HAMLETS {
        let map = &w.maps[ORRERY];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(
            hub.travel_links.iter().any(|l| l == &master.id),
            "the refuge links to {key}"
        );
        assert!(master.travel_links.iter().any(|l| l == "travel_stillpoint"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_15_{key}")),
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
        place(&mut w, 1, ORRERY, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
}

#[test]
fn the_orrery_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let map = &w.maps[ORRERY];
    let new = [
        "orrery_h_hold",
        "orrery_h_rounds",
        "orrery_bc_walk",
        "orrery_bc_blades",
        "orrery_bc_hold",
        "orrery_bc_axis",
        "orrery_cn_valley",
        "orrery_cn_plates",
        "orrery_cn_hold",
        "orrery_cn_lens",
        "orrery_sw_reaches",
        "orrery_sw_glass",
        "orrery_sw_hold",
        "orrery_sw_south",
    ];
    for id in new {
        let q = map
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap_or_else(|| panic!("no quest {id}"));
        assert!((50..=55).contains(&q.level), "{id} level {}", q.level);
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
                        .any(|s| s.zone == ORRERY && s.kind == o.target && s.ambush.is_none()),
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
    // the two elite quests keep their ids: one kill, a group, a blue reward
    for (id, kind, players) in [
        ("orrery_matron", "pendulummatron", 3),
        ("orrery_engine", "epochengine", 5),
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
            .any(|q| q.objectives.iter().any(|o| o.target == "mainspringwyrm")),
        "the Mainspring Wyrm has no quest"
    );
    // every hold circle has both of its waves asleep beside it
    for hold in [
        "orrery_still_m",
        "orrery_bell_m",
        "orrery_gate_m",
        "orrery_shard_m",
    ] {
        let p = map.places.iter().find(|p| p.id == hold).unwrap();
        for wave in ['a', 'b'] {
            let tag = format!("{hold}#{wave}");
            let sleepers: Vec<_> = w
                .spawns
                .iter()
                .filter(|s| s.zone == ORRERY && s.ambush.as_deref() == Some(tag.as_str()))
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
        "orrery_welcome",
        "orrery_mantises",
        "orrery_gearlings",
        "orrery_teeth",
        "orrery_seers",
        "orrery_guards",
        "orrery_survey",
        "orrery_patrol",
        "orrery_onward",
        "es_12",
        "es_go_12",
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
                zone: ORRERY,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 100_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("mainspringwyrm"), "mainspring_coil");
    let w = world();
    let map = &w.maps[ORRERY];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == ORRERY && s.kind == kind)
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
    // each stands in its own part of the plain
    let find = |k: &str| {
        w.spawns
            .iter()
            .find(|s| s.zone == ORRERY && s.kind == k)
            .unwrap()
    };
    assert!(
        find("pendulummatron").x < 150. && find("pendulummatron").y < 140.,
        "the Matron keeps the Winding Court in the west"
    );
    assert!(
        find("epochengine").y < 60.,
        "the Engine stands under the crown"
    );
    assert!(
        find("mainspringwyrm").x > 230.,
        "the Wyrm coils through the Reaches in the east"
    );
}
