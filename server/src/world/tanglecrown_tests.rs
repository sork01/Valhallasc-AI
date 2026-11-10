//! The Tanglecrown (zone 22, levels 75-80) as an authored rain jungle on the shapes pilot: its data, the two rim gates, the temple door and the Ribbonwild seam, Banyan Landing,
//! the Rainstep Camp and three outposts, the quests (holds, visits, brings, kills, the two elite quests) and the new elite with no quest.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const JUNGLE: usize = 22;
const ELITES: [(&str, u32); 3] = [
    ("jadeanaconda", 79),
    ("crownjaguar", 80),
    ("rootcentipede", 77),
];
/// (gate, the zone it leads to, the far gate that leads back); the border to the Ribbonwild is a seam, the temple is a door
const GATES: [(&str, usize, &str); 0] = []; // the Veyrroot and Sunward borders are seams since 2026-11-09
const HAMLETS: [(&str, &str); 3] = [
    ("rootgate", "tg_rg_"),
    ("drumroot", "tg_dr_"),
    ("stilt", "tg_sp_"),
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
fn the_tanglecrown_is_a_jungle_triangle_with_four_families_three_elites_five_hubs_and_the_temple_door()
 {
    let w = world();
    let map = &w.maps[JUNGLE];
    assert_eq!(map.name, "The Tanglecrown");
    assert_eq!((map.size, map.levels), (304, Some([75, 80])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert!(map.in_city(map.spawn), "the spawn is Banyan Landing");
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w
        .spawns
        .iter()
        .enumerate()
        .filter(|(_, s)| s.zone == JUNGLE)
    {
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
        ("orchidmantis", 20),
        ("canopyglider", 20),
        ("poolcaiman", 20),
        ("drumgorilla", 15),
    ] {
        assert!(live[kind] >= floor, "{kind}: {}", live[kind]);
    }
    for (kind, _) in ELITES {
        assert_eq!(live[kind], 1, "{kind}");
    }
    for (kind, level, drop) in [
        ("orchidmantis", 75, "mantis_petals"),
        ("canopyglider", 76, "glider_membrane"),
        ("poolcaiman", 77, "caiman_scale"),
        ("drumgorilla", 78, "gorilla_drumskin"),
    ] {
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
    }
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zone = &raw["zones"][JUNGLE - 1];
    assert_eq!(zone["city"]["name"], "Banyan Landing");
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
            "Drumroot Post",
            "Rainstep Camp",
            "Rootgate Post",
            "Stilt Post"
        ]
    );
    let masters = map.npcs.iter().filter(|n| n.travel_stop.is_some()).count();
    assert_eq!(
        masters, 5,
        "the Landing and four camps each have a Spark master"
    );
    assert_eq!(zone["futureInstance"]["status"], "open");
    assert_eq!(zone["futureInstance"]["name"], "Temple of the Rain Crown");
    let objects = zone["objects"].as_array().unwrap();
    for (kind, floor) in [
        ("kapok_tree", 60),
        ("strangler_fig", 80),
        ("banana_palm", 60),
        ("hanging_vines", 60),
        ("jungle_water", 30),
    ] {
        assert!(
            objects.iter().filter(|o| o["kind"] == kind).count() >= floor,
            "{kind}"
        );
    }
    // the Spark network is not an island: the Landing links the camps, Sunward's master, the Veyrroot Canopy's and the Ribbonwild's
    let master = map.npcs.iter().find(|n| n.id == "travel_banyan").unwrap();
    for id in [
        "travel_millbridge",
        "travel_garland",
        "travel_veyrroot",
        "travel_rootgate",
        "travel_drumroot",
        "travel_stilt",
        "travel_rainstep",
    ] {
        assert!(master.travel_links.iter().any(|l| l == id), "{id}");
    }
    assert!(
        w.maps[21]
            .npcs
            .iter()
            .find(|n| n.id == "travel_garland")
            .unwrap()
            .travel_links
            .contains(&"travel_banyan".to_string()),
        "the Ribbonwild's master links back"
    );
}

#[test]
fn both_rim_gates_are_walked_through_both_ways_the_temple_door_leads_in_and_the_arrivals_are_clear()
{
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in GATES {
        let gate = w.maps[JUNGLE]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        assert_eq!(gate.to, zone, "{gate_id}");
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, JUNGLE, at(gate.x, gate.y));
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
        assert_eq!(back.to, JUNGLE, "{back_id} leads here");
        let arrival = at(back.tx, back.ty);
        assert!(
            arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5
                && arrival.distance(at(gate.x, gate.y)) < 8.,
            "{back_id} arrives beside {gate_id}, clear of its disc"
        );
        let mut a = arrival;
        w.maps[JUNGLE].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
        assert!(
            w.spawns
                .iter()
                .filter(|s| s.zone == JUNGLE)
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
        assert_eq!(w.players[&1].character.zone, JUNGLE, "{back_id} returns");
    }
    // the temple's door stands in the Rainstep Camp, and both its ways out arrive in front of it on free ground
    let door = w.maps[JUNGLE]
        .portals
        .iter()
        .find(|p| p.id == "tangle_rain_gate")
        .unwrap()
        .clone();
    assert_eq!(door.to, 32);
    for back_id in ["rain_crown_return", "rain_crown_exit"] {
        let back = w.maps[32].portals.iter().find(|p| p.id == back_id).unwrap();
        assert_eq!(back.to, JUNGLE);
        let arrival = at(back.tx, back.ty);
        assert!(arrival.distance(at(door.x, door.y)) < 14., "{back_id}");
        let mut a = arrival;
        w.maps[JUNGLE].collide(&mut a, PLAYER_RADIUS);
        assert!(a.distance(arrival) < 1e-6, "{back_id} lands on free ground");
    }
}

#[test]
fn the_tanglecrown_border_to_the_ribbonwild_is_a_seam_with_a_road_across_and_the_other_borders_are_gates()
 {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in data["zones"][zi - 1]["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == JUNGLE || to == JUNGLE) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> =
        [(21, 22), (22, 21), (22, 23), (23, 22), (20, 22), (22, 20)].into();
    assert_eq!(
        pairs, want,
        "one seam each to the Ribbonwild, the Veyrroot and Sunward Vale, seen from both sides"
    );
    // both seam portals stand where the road crosses (the old gate's place, in the south-west), not on the middle of the border
    let w = world();
    let mine = w.maps[JUNGLE]
        .portals
        .iter()
        .find(|p| p.to == 21)
        .expect("the seam portal");
    // the Veyrroot seam (2026-11-09) stands where the old rim gate stood, on the north-east border
    let veyrroot = w.maps[JUNGLE]
        .portals
        .iter()
        .find(|p| p.to == 23)
        .expect("the Veyrroot seam portal");
    assert!(
        (veyrroot.x - 184.5).abs() < 1.5 && veyrroot.y > 90. && veyrroot.y < 105.,
        "{} {}",
        veyrroot.x,
        veyrroot.y
    );
    assert!(
        (mine.x - 94.).abs() < 2. && (mine.y - 253.3).abs() < 2.,
        "{} {}",
        mine.x,
        mine.y
    );
    // a road runs to the border on this side: some road polyline ends within a tile of the portal
    let zone = &data["zones"][JUNGLE - 1];
    let near = zone["paths"].as_array().unwrap().iter().any(|road| {
        road.as_array().unwrap().iter().any(|q| {
            let (x, y) = (q[0].as_f64().unwrap(), q[1].as_f64().unwrap());
            ((x - mine.x).powi(2) + (y - mine.y).powi(2)).sqrt() < 1.5
        })
    });
    assert!(near, "a road meets the seam at the crossing");
}

#[test]
fn everyone_and_everything_in_the_tanglecrown_can_be_walked_to_from_the_landing() {
    let w = world();
    let map = &w.maps[JUNGLE];
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
        .filter(|(_, s)| s.zone == JUNGLE)
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
    let door = map
        .portals
        .iter()
        .find(|p| p.id == "tangle_rain_gate")
        .unwrap();
    assert!(
        reached(map, &open, at(door.x, door.y + 2.)),
        "the temple door is cut off"
    );
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox_and_the_temple_has_a_camp()
 {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (key, prefix) in HAMLETS {
        let map = &w.maps[JUNGLE];
        let master = map
            .npcs
            .iter()
            .find(|n| n.id == format!("travel_{key}"))
            .unwrap_or_else(|| panic!("no travel master at {key}"));
        assert!(master.travel_links.iter().any(|l| l == "travel_banyan"));
        assert!(
            map.npcs.iter().any(|n| n.id == format!("mailbox_22_{key}")),
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
        place(&mut w, 1, JUNGLE, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(w.players[&1].character.hp, before, "no damage inside {key}");
    }
    // the Rainstep Camp at the temple door: the scholar and the Meeting Stone moved into it, with its own master and mailbox
    let map = &w.maps[JUNGLE];
    let rain_master = map.npcs.iter().find(|n| n.id == "travel_rainstep").unwrap();
    let camp = map
        .camps
        .iter()
        .find(|k| {
            at(rain_master.x, rain_master.y).distance(at((k.x0 + k.x1) / 2., (k.y0 + k.y1) / 2.))
                < 12.
        })
        .expect("the Rainstep Camp");
    for id in [
        "tangle_scholar",
        "tangle_stone",
        "travel_rainstep",
        "mailbox_22_rainstep",
    ] {
        let n = map.npcs.iter().find(|n| n.id == id).expect(id);
        assert!(
            n.x >= camp.x0 && n.x <= camp.x1 && n.y >= camp.y0 && n.y <= camp.y1,
            "{id} stands in the Rainstep Camp"
        );
    }
    let door = map
        .portals
        .iter()
        .find(|p| p.id == "tangle_rain_gate")
        .unwrap();
    assert!(
        door.x >= camp.x0 - 2.
            && door.x <= camp.x1 + 2.
            && door.y >= camp.y0 - 4.
            && door.y <= camp.y1,
        "the temple door stands at the camp"
    );
}

#[test]
fn the_tanglecrown_quests_are_connected_and_every_objective_names_something_that_exists() {
    let w = world();
    let map = &w.maps[JUNGLE];
    let new = [
        "tangle_lh_hold",
        "tangle_rounds",
        "tangle_rg_walk",
        "tangle_rg_petals",
        "tangle_rg_hold",
        "tangle_rg_glide",
        "tangle_sp_walk",
        "tangle_sp_scales",
        "tangle_sp_hold",
        "tangle_sp_water",
        "tangle_dr_walk",
        "tangle_dr_skins",
        "tangle_dr_hold",
        "tangle_dr_stair",
    ];
    for id in new {
        let q = map
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap_or_else(|| panic!("no quest {id}"));
        assert!((75..=80).contains(&q.level), "{id} level {}", q.level);
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
                        .any(|s| s.zone == JUNGLE && s.kind == o.target && s.ambush.is_none()),
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
        ("tangle_anaconda", "jadeanaconda"),
        ("tangle_jaguar", "crownjaguar"),
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
            .any(|q| q.objectives.iter().any(|o| o.target == "rootcentipede")),
        "the Hollowroot Centipede has no quest"
    );
    for hold in ["tg_lh_m", "tg_rg_m", "tg_dr_m", "tg_sp_m"] {
        let p = map.places.iter().find(|p| p.id == hold).unwrap();
        for wave in ['a', 'b'] {
            let tag = format!("{hold}#{wave}");
            let sleepers: Vec<_> = w
                .spawns
                .iter()
                .filter(|s| s.zone == JUNGLE && s.ambush.as_deref() == Some(tag.as_str()))
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
        "tangle_welcome",
        "tangle_mantises",
        "tangle_gliders",
        "tangle_caimans",
        "tangle_drums",
        "tangle_anaconda",
        "tangle_jaguar",
        "tangle_temple",
        "tangle_crown_trials",
        "tangle_crown_final",
        "tangle_patrol",
        "tangle_onward",
        "tangle_banyan_1",
        "tangle_banyan_2",
        "tangle_banyan_3",
        "tangle_banyan_4",
        "es_18",
        "es_go_18",
    ] {
        assert!(map.quests.iter().any(|q| q.id == id), "{id}");
    }
    assert_eq!(map.quests.len(), 32, "18 old quests and 14 new ones");
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
                zone: JUNGLE,
            },
            level,
        );
        assert!(s.elite && s.max_hp > 1_000_000., "{kind} {}", s.max_hp);
    }
    assert_eq!(material("rootcentipede"), "hollow_chitin");
    let w = world();
    let map = &w.maps[JUNGLE];
    let bearer = map
        .npcs
        .iter()
        .find(|n| n.id == "tangle_hatchling")
        .unwrap();
    for (kind, _) in ELITES {
        let e = w
            .spawns
            .iter()
            .find(|s| s.zone == JUNGLE && s.kind == kind)
            .unwrap();
        let awareness = Slime::attack_profile(kind).3 + 3.;
        for n in &map.npcs {
            if n.id == "tangle_hatchling" {
                continue;
            }
            assert!(
                at(n.x, n.y).distance(at(e.x, e.y)) > awareness,
                "{kind} near {}",
                n.id
            );
        }
        for p in &map.places {
            if matches!(
                p.id.as_str(),
                "tangle_anaconda_pool" | "tangle_jaguar_terrace"
            ) {
                continue;
            }
            assert!(
                at(p.x, p.y).distance(at(e.x, e.y)) > awareness,
                "{kind} near {}",
                p.id
            );
        }
        // nothing the hatchling's escort walks passes within the elite's reach
        for p in &bearer.escort.as_ref().unwrap().route {
            assert!(
                at(p[0], p[1]).distance(at(e.x, e.y)) > awareness,
                "{kind} near the escort route"
            );
        }
    }
    let find = |k: &str| {
        w.spawns
            .iter()
            .find(|s| s.zone == JUNGLE && s.kind == k)
            .unwrap()
    };
    assert!(
        find("jadeanaconda").y < 130.,
        "the anaconda keeps the Jade Basin in the north"
    );
    assert!(
        find("crownjaguar").x > 170. && find("crownjaguar").y > 140.,
        "the jaguar holds the terrace east of the trunk road"
    );
    assert!(
        find("rootcentipede").x > 180. && find("rootcentipede").y > 170.,
        "the centipede sits in the Strangler Maze in the south-east"
    );
}

#[test]
fn the_empty_seat_moves_with_its_sleeper_the_mailboxes_stand_on_free_ground_and_the_hatchling_walks_to_mara()
 {
    let w = world();
    let map = &w.maps[JUNGLE];
    let seat = map.places.iter().find(|p| p.id == "es_18_m").unwrap();
    let foe = w
        .spawns
        .iter()
        .find(|s| s.zone == JUNGLE && s.ambush.as_deref() == Some("empty-seat:es_18_m"))
        .expect("the sleeper waits at the Empty Seat's place");
    assert!(at(foe.x, foe.y).distance(at(seat.x, seat.y)) < 6.);
    for (box_id, master_id) in [
        ("mailbox_22_banyan_landing", "travel_banyan"),
        ("mailbox_22_rootgate", "travel_rootgate"),
        ("mailbox_22_drumroot", "travel_drumroot"),
        ("mailbox_22_stilt", "travel_stilt"),
        ("mailbox_22_rainstep", "travel_rainstep"),
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
        .filter(|d| d["zone"] == JUNGLE)
        .count();
    assert_eq!(
        mine, 5,
        "the directory lists the Landing, the Rainstep Camp and three outposts"
    );
    // the escort ends beside Mara Vines
    let bearer = map
        .npcs
        .iter()
        .find(|n| n.id == "tangle_hatchling")
        .unwrap();
    let route = &bearer.escort.as_ref().unwrap().route;
    let mara = map.npcs.iter().find(|n| n.id == "tangle_tracker").unwrap();
    let last = route.last().unwrap();
    assert!(
        at(last[0], last[1]).distance(at(mara.x, mara.y)) < 6.,
        "the route ends beside Mara"
    );
}

#[test]
fn tanglecrown_enemies_materials_and_quest_rewards_are_registered() {
    let w = world();
    let m = &w.maps[JUNGLE];
    for (kind, level, drop) in [
        ("orchidmantis", 75, "mantis_petals"),
        ("canopyglider", 76, "glider_membrane"),
        ("poolcaiman", 77, "caiman_scale"),
        ("drumgorilla", 78, "gorilla_drumskin"),
        ("rootcentipede", 77, "hollow_chitin"),
        ("jadeanaconda", 79, "anaconda_jade"),
        ("crownjaguar", 80, "jaguar_crown"),
    ] {
        assert!(w.spawns.iter().any(|s| s.zone == JUNGLE && s.kind == kind));
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some());
        let (hp, damage, _, _) = Slime::stats(kind);
        assert!(hp > 300000. && damage > 5000.);
    }
    assert!(is_elite("jadeanaconda") && is_elite("crownjaguar") && is_elite("rootcentipede"));
    assert!(!is_elite("poolcaiman"));
    for q in &m.quests {
        if q.id.starts_with("es_go_") {
            continue; // a hand-off pays nothing
        }
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
    for id in [
        "tangle_mantises",
        "tangle_gliders",
        "tangle_anaconda",
        "tangle_jaguar",
        "tangle_lh_hold",
        "tangle_rounds",
        "tangle_rg_hold",
        "tangle_rg_glide",
        "tangle_sp_hold",
        "tangle_sp_water",
        "tangle_dr_hold",
        "tangle_dr_stair",
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
    for id in ["tangle_anaconda", "tangle_jaguar"] {
        assert!(m.quests.iter().find(|q| q.id == id).unwrap().group);
    }
}
