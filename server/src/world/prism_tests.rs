//! The Prismwaste (zone 14, levels 45-50) as an authored rose-salt desert on the shapes pilot: its data, the four seams (Astralhollow, the Orrery, Stormglass, Cairnspine), the refuge and
//! three outposts, the quests (holds, visits, brings, kills, the two elite quests) and the new elite with no quest.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const PRISM: usize = 14;
const KINDS: [&str; 4] = [
    "miragejackal",
    "shardscarab",
    "glassharrier",
    "prismsentinel",
];
const ELITES: [(&str, u32); 3] = [("mirrorqueen", 49), ("sunshard", 50), ("shatterhorn", 48)];
const HAMLETS: [(&str, &str); 3] = [
    ("mirrorfall", "prism_mf_"),
    ("whitesun", "prism_ws_"),
    ("cairnfoot", "prism_cf_"),
];

#[test]
fn the_prismwaste_is_a_big_waste_with_four_families_by_distance_three_elites_four_hubs_two_gates_and_two_seams()
 {
    let w = world();
    let map = &w.maps[PRISM];
    assert_eq!(map.name, "The Prismwaste");
    assert_eq!((map.size, map.levels), (288, Some([45, 50])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    // the four families, banded by distance from the refuge in the west: jackals by it, then scarabs, harriers, and the sentinels farthest
    let mut live = std::collections::BTreeMap::<&str, Vec<f64>>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == PRISM) {
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
            "{} is clear of the refuge",
            spawn.kind
        );
    }
    for (kind, floor) in [
        ("miragejackal", 40),
        ("shardscarab", 60),
        ("glassharrier", 35),
        ("prismsentinel", 25),
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
            mean(pair[1]) > mean(pair[0]) + 12.,
            "{} lives farther from the refuge than {}",
            pair[0],
            pair[1]
        );
    }
    for (kind, level) in [
        ("miragejackal", 45),
        ("shardscarab", 46),
        ("glassharrier", 47),
        ("prismsentinel", 48),
        ("mirrorqueen", 49),
        ("sunshard", 50),
        ("shatterhorn", 48),
    ] {
        assert_eq!(Slime::default_level(kind), level, "{kind}");
    }
    // the refuge is the zone's `city`, the three outposts are camps; every hub is safe ground with a travel master
    let c = map.city.as_ref().unwrap();
    assert_eq!((c.x1 - c.x0, c.y1 - c.y0), (34., 19.));
    assert_eq!(map.camps.len(), 3);
    for camp in &map.camps {
        assert!(map.in_city(at((camp.x0 + camp.x1) / 2., (camp.y0 + camp.y1) / 2.)));
    }
    for id in [
        "travel_last_shade",
        "travel_mirrorfall",
        "travel_whitesun",
        "travel_cairnfoot",
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
    // ten places: six to visit, four hold circles (the Empty Seat's own place is not counted)
    assert_eq!(
        map.places
            .iter()
            .filter(|p| p.id.starts_with("prism_"))
            .count(),
        10
    );
    // four seams (Astralhollow, the Orrery, Stormglass, Cairnspine) and no gate left
    assert_eq!(map.portals.len(), 4);
    let mut seams: Vec<usize> = map
        .portals
        .iter()
        .filter(|p| p.seam.is_some())
        .map(|p| p.to)
        .collect();
    seams.sort_unstable();
    assert_eq!(
        seams,
        vec![13, 15, 19, 27],
        "only Astralhollow, the Orrery, Stormglass and Cairnspine are seams"
    );
    assert!(
        map.portals
            .iter()
            .all(|p| p.seam.is_some() && p.walk.is_none()),
        "every crossing of the Prismwaste is a seam"
    );
}

#[test]
fn everyone_and_everything_in_the_prismwaste_can_be_walked_to_from_the_refuge() {
    let w = world();
    let map = &w.maps[PRISM];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == PRISM) {
        assert!(
            reached(map, &open, at(s.x, s.y)),
            "{} #{id} is cut off",
            s.kind
        );
    }
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let hub = w.maps[PRISM]
        .npcs
        .iter()
        .find(|n| n.id == "travel_last_shade")
        .unwrap()
        .clone();
    for (key, prefix) in HAMLETS {
        let map = &w.maps[PRISM];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(
            hub.travel_links.iter().any(|l| l == &master.id),
            "the refuge links to {key}"
        );
        assert!(master.travel_links.iter().any(|l| l == "travel_last_shade"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_14_{key}")),
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
        place(&mut w, 1, PRISM, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
}

#[test]
fn the_prismwaste_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let map = &w.maps[PRISM];
    let new = [
        "prism_h_hold",
        "prism_h_rounds",
        "prism_mf_walk",
        "prism_mf_lenses",
        "prism_mf_hold",
        "prism_mf_glass",
        "prism_ws_walk",
        "prism_ws_hearts",
        "prism_ws_hold",
        "prism_ws_watch",
        "prism_cf_walk",
        "prism_cf_fangs",
        "prism_cf_hold",
        "prism_cf_south",
    ];
    for id in new {
        let q = map
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap_or_else(|| panic!("no quest {id}"));
        assert!((45..=50).contains(&q.level), "{id} level {}", q.level);
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
                        .any(|s| s.zone == PRISM && s.kind == o.target && s.ambush.is_none()),
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
        ("prism_queen", "mirrorqueen", 3),
        ("prism_sunshard", "sunshard", 5),
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
            .any(|q| q.objectives.iter().any(|o| o.target == "shatterhorn")),
        "the Shatterhorn has no quest"
    );
    // every hold circle has both of its waves asleep beside it
    for hold in [
        "prism_awning_m",
        "prism_glass_m",
        "prism_beacon_m",
        "prism_cairn_m",
    ] {
        let p = map.places.iter().find(|p| p.id == hold).unwrap();
        for wave in ['a', 'b'] {
            let tag = format!("{hold}#{wave}");
            let sleepers: Vec<_> = w
                .spawns
                .iter()
                .filter(|s| s.zone == PRISM && s.ambush.as_deref() == Some(tag.as_str()))
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
        "prism_welcome",
        "prism_jackals",
        "prism_scarabs",
        "prism_wings",
        "prism_harriers",
        "prism_sentinels",
        "prism_queen",
        "prism_sunshard",
        "prism_survey",
        "prism_patrol",
        "prism_onward",
        "es_11",
        "es_go_11",
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
                zone: PRISM,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 100_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("shatterhorn"), "horn_prism");
    let w = world();
    let map = &w.maps[PRISM];
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == PRISM && s.kind == kind)
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
    // each stands in its own part of the waste
    let find = |k: &str| {
        w.spawns
            .iter()
            .find(|s| s.zone == PRISM && s.kind == k)
            .unwrap()
    };
    assert!(
        find("mirrorqueen").x < 80.,
        "the Queen keeps the Mirror Court in the north-west"
    );
    assert!(
        find("sunshard").y < 80.,
        "the Sunshard burns below the Broken Crown in the north"
    );
    assert!(
        find("shatterhorn").x > 220. && find("shatterhorn").y > 180.,
        "the Shatterhorn roams the Sunspire Reaches in the south-east"
    );
}

#[test]
fn the_cross_and_the_empty_seat_move_with_their_sleepers() {
    let w = world();
    let map = &w.maps[PRISM];
    let cross = map.crosses.first().expect("the Ember Grave Cross");
    let fire = w
        .spawns
        .iter()
        .find(|s| s.zone == PRISM && s.ambush.as_deref() == Some("raid_key:14"))
        .expect("the cross's sleeper");
    assert!(at(fire.x, fire.y).distance(at(cross.x, cross.y)) < 6.);
    let seat = map.places.iter().find(|p| p.id == "es_11_m").unwrap();
    let foe = w
        .spawns
        .iter()
        .find(|s| s.zone == PRISM && s.ambush.as_deref() == Some("empty-seat:es_11_m"))
        .expect("the Gilded Witness sleeps at the Empty Seat's place");
    assert!(at(foe.x, foe.y).distance(at(seat.x, seat.y)) < 6.);
}

#[test]
fn the_four_prismwaste_mailboxes_stand_on_free_ground_with_a_clear_line_to_their_travel_master() {
    let w = world();
    let map = &w.maps[PRISM];
    for (box_id, master_id) in [
        ("mailbox_14_the_last_shade", "travel_last_shade"),
        ("mailbox_14_mirrorfall", "travel_mirrorfall"),
        ("mailbox_14_whitesun", "travel_whitesun"),
        ("mailbox_14_cairnfoot", "travel_cairnfoot"),
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
        .filter(|d| d["zone"] == PRISM)
        .count();
    assert_eq!(mine, 4, "the directory lists the refuge and three outposts");
}
