//! Astralhollow (zone 13, levels 40-45) as an authored basin on the shapes pilot: its data, the four crossings (all gates), the court and
//! three outposts, the quests (holds, visits, brings, kills, the two elite quests) and the three new elites.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const ASTRAL: usize = 13;
const KINDS: [&str; 5] = [
    "voidmoth",
    "crystalwyrm",
    "orbitbeetle",
    "eclipsedryad",
    "meteorgolem",
];
const ELITES: [(&str, u32); 3] = [("cometmaw", 42), ("eclipsequeen", 44), ("orbitwarden", 45)];
/// (gate, the zone it leads to, the far gate that leads back); the border to the Orrery became a seam on 2026-11-08
const GATES: [(&str, usize, &str); 3] = [
    ("astral_nacre_gate", 9, "nacre_astral_gate"),
    ("path_13_8", 8, "path_8_13"),
    ("astral_prism_gate", 14, "prism_astral_gate"),
];
const HAMLETS: [(&str, &str); 3] = [
    ("choirrest", "astral_cr_"),
    ("cometwatch", "astral_cw_"),
    ("fallstone", "astral_fh_"),
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
fn astralhollow_is_a_big_basin_with_five_kinds_by_distance_three_elites_four_hubs_three_gates_and_a_seam() {
    let w = world();
    let map = &w.maps[ASTRAL];
    assert_eq!(map.name, "Astralhollow");
    assert_eq!((map.size, map.levels), (336, Some([40, 45])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    // the five families, banded from the court in the south to the Fallstone Fields in the north
    let mut live = std::collections::BTreeMap::<&str, Vec<f64>>::new();
    for (id, spawn) in w
        .spawns
        .iter()
        .enumerate()
        .filter(|(_, s)| s.zone == ASTRAL)
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
            "{} is clear of the court",
            spawn.kind
        );
    }
    for (kind, floor) in [
        ("voidmoth", 50),
        ("crystalwyrm", 55),
        ("orbitbeetle", 55),
        ("eclipsedryad", 50),
        ("meteorgolem", 50),
    ] {
        assert!(live[kind].len() >= floor, "{kind}: {}", live[kind].len());
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind].len(), 1, "{kind}");
    }
    assert_eq!(live.len(), 8, "{:?}", live.keys());
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
        ("voidmoth", 40),
        ("crystalwyrm", 41),
        ("orbitbeetle", 42),
        ("eclipsedryad", 43),
        ("meteorgolem", 45),
        ("cometmaw", 42),
        ("eclipsequeen", 44),
        ("orbitwarden", 45),
    ] {
        assert_eq!(Slime::default_level(kind), level, "{kind}");
    }
    // the court is the zone's `city`, the three outposts are camps; every hub is safe ground with a travel master
    let c = map.city.as_ref().unwrap();
    assert_eq!((c.x1 - c.x0, c.y1 - c.y0), (38., 18.));
    assert_eq!(map.camps.len(), 3);
    for camp in &map.camps {
        assert!(map.in_city(at((camp.x0 + camp.x1) / 2., (camp.y0 + camp.y1) / 2.)));
    }
    for id in [
        "travel_astralhollow",
        "travel_choirrest",
        "travel_cometwatch",
        "travel_fallstone",
    ] {
        assert!(
            map.npcs
                .iter()
                .any(|n| n.id == id && n.travel_stop.is_some()),
            "{id}"
        );
    }
    assert!(map.in_city(map.spawn), "a new hero starts in the court");
    let mut free = map.spawn;
    map.collide(&mut free, PLAYER_RADIUS);
    assert!(free.distance(map.spawn) < 1e-6, "the spawn is free ground");
    // nine places: five to visit, four hold circles
    assert_eq!(
        map.places
            .iter()
            .filter(|p| p.id.starts_with("astral_"))
            .count(),
        9
    );
    // three walk-in gates and one seam (to the Orrery)
    assert_eq!(map.portals.len(), 4);
    let seams: Vec<usize> = map
        .portals
        .iter()
        .filter(|p| p.seam.is_some())
        .map(|p| p.to)
        .collect();
    assert_eq!(seams, vec![15], "only the Orrery border is a seam");
}

#[test]
fn all_three_gates_are_walked_through_both_ways_and_every_arrival_is_clear_ground() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in GATES {
        let gate = w.maps[ASTRAL]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        assert_eq!(gate.to, zone, "{gate_id}");
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, ASTRAL, at(gate.x, gate.y));
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
        assert_eq!(back.to, ASTRAL, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        assert!(
            arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
                && arrival.distance(at(gate.x, gate.y)) < 8.,
            "{back_id} arrives beside {gate_id}, clear of its disc"
        );
        let mut a = arrival;
        w.maps[ASTRAL].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        // no enemy within eight tiles of an arrival
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == ASTRAL)
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
        assert_eq!(w.players[&1].character.zone, ASTRAL, "{back_id} returns");
        let c = &w.players[&1].character;
        assert!(
            at(c.x, c.y).distance(at(gate.x, gate.y)) < 12.,
            "{back_id} puts the hero near {gate_id}"
        );
    }
}

#[test]
fn everyone_and_everything_in_astralhollow_can_be_walked_to_from_the_court() {
    let w = world();
    let map = &w.maps[ASTRAL];
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
        .filter(|(_, s)| s.zone == ASTRAL)
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
    let hub = w.maps[ASTRAL]
        .npcs
        .iter()
        .find(|n| n.id == "travel_astralhollow")
        .unwrap()
        .clone();
    for (key, prefix) in HAMLETS {
        let map = &w.maps[ASTRAL];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(
            hub.travel_links.iter().any(|l| l == &master.id),
            "the court links to {key}"
        );
        assert!(
            master
                .travel_links
                .iter()
                .any(|l| l == "travel_astralhollow")
        );
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_13_{key}")),
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
        place(&mut w, 1, ASTRAL, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
}

#[test]
fn the_astralhollow_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let map = &w.maps[ASTRAL];
    let new = [
        "astral_h_lamps",
        "astral_h_rounds",
        "astral_cr_hollows",
        "astral_cr_lanterns",
        "astral_cr_chord",
        "astral_cr_ring",
        "astral_cw_scout",
        "astral_cw_shells",
        "astral_cw_fire",
        "astral_cometmaw",
        "astral_fh_walk",
        "astral_fh_cores",
        "astral_fh_line",
        "astral_eclipsequeen",
    ];
    for id in new {
        let q = map
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap_or_else(|| panic!("no quest {id}"));
        assert!((40..=45).contains(&q.level), "{id} level {}", q.level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{id}");
        assert!(q.reward_gold >= 500, "{id}");
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
                        .any(|s| s.zone == ASTRAL && s.kind == o.target && s.ambush.is_none()),
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
    // the two elite quests: one kill, three players recommended, a blue reward
    for (id, kind) in [
        ("astral_cometmaw", "cometmaw"),
        ("astral_eclipsequeen", "eclipsequeen"),
    ] {
        let q = map.quests.iter().find(|q| q.id == id).unwrap();
        assert_eq!(q.recommended_players, 3, "{id}");
        assert!(q.objectives.len() == 1 && q.objectives[0].target == kind);
        let reward = item(q.reward_item.as_deref().unwrap()).unwrap();
        assert_eq!(reward.rarity, "rare", "{id}");
    }
    assert!(
        !map.quests
            .iter()
            .any(|q| q.objectives.iter().any(|o| o.target == "orbitwarden")),
        "the Orbit Warden has no quest"
    );
    // every hold circle has both of its waves asleep beside it
    for hold in [
        "astral_lamps_m",
        "astral_chord_m",
        "astral_fire_m",
        "astral_line_m",
    ] {
        let p = map.places.iter().find(|p| p.id == hold).unwrap();
        for wave in ['a', 'b'] {
            let tag = format!("{hold}#{wave}");
            let sleepers: Vec<_> = w
                .spawns
                .iter()
                .filter(|s| s.zone == ASTRAL && s.ambush.as_deref() == Some(tag.as_str()))
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
        "astral_welcome",
        "astral_moths",
        "astral_wyrms",
        "astral_beetles",
        "astral_dryads",
        "astral_golems",
        "astral_survey",
        "astral_onward",
        "es_10",
        "es_go_10",
    ] {
        assert!(map.quests.iter().any(|q| q.id == id), "{id}");
    }
}

#[test]
fn the_three_elites_have_stats_materials_art_names_and_stand_clear_of_everything_walked_to() {
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
                zone: ASTRAL,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 100_000., "{kind} {}", s.max_hp);
    }
    // the Cometmaw is a rush, the Eclipse Queen a sweep, the Orbit Warden a slam: three different wind-ups
    let wind = |k: &str| Slime::attack_profile(k).0;
    assert!(wind("cometmaw") < wind("eclipsequeen") && wind("eclipsequeen") < wind("orbitwarden"));
    let w = world();
    let map = &w.maps[ASTRAL];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == ASTRAL && s.kind == kind)
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
    // each stands in its own part of the basin
    let find = |k: &str| {
        w.spawns
            .iter()
            .find(|s| s.zone == ASTRAL && s.kind == k)
            .unwrap()
    };
    assert!(
        find("cometmaw").x > 232.,
        "the Cometmaw runs the east field"
    );
    assert!(find("eclipsequeen").x < 130. && find("eclipsequeen").y < 100.);
    assert!(at(find("orbitwarden").x, find("orbitwarden").y).distance(at(172., 152.)) < 25.);
}
