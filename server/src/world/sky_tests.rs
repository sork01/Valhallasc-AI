//! Bifrost Reach (zone 7, levels 30-35): its floating islands and the void between them, the five monster kinds, the hub, the
//! Stormrift gate pair, the Spark flight and the new `hold` quest objective ("hold the ward").
use super::wyrd_tests::{at, blocked, calm, drain, flood, join, lines, place, reached, world};
use super::*;

const SKALD: usize = 4;
const WYRD: usize = 6;
const SKY: usize = 7;
const STEP: f64 = 1.;

/// The zone's floor as the client draws it: 160 strings, ' ' void, '#' island, '=' bridge.
fn rows() -> Vec<Vec<char>> {
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    raw["zones"][SKY - 1]["sky"]
        .as_array()
        .expect("the zone lists its floor")
        .iter()
        .map(|r| r.as_str().unwrap().chars().collect())
        .collect()
}
fn on_floor(rows: &[Vec<char>], x: f64, y: f64) -> bool {
    rows.get(y as usize)
        .and_then(|r| r.get(x as usize))
        .is_some_and(|c| *c != ' ')
}
fn npc(w: &World, id: &str) -> Npc {
    w.maps[SKY]
        .npcs
        .iter()
        .find(|n| n.id == id)
        .unwrap_or_else(|| panic!("no NPC {id}"))
        .clone()
}
fn quest(w: &World, id: &str) -> Quest {
    w.maps[SKY]
        .quests
        .iter()
        .find(|q| q.id == id)
        .unwrap_or_else(|| panic!("no quest {id}"))
        .clone()
}
fn place_of(w: &World, id: &str) -> Place {
    w.maps[SKY]
        .places
        .iter()
        .find(|p| p.id == id)
        .unwrap_or_else(|| panic!("no place {id}"))
        .clone()
}
/// The cell beside a spot counts too: people and enemies stand close to walls and the grid is one tile.
fn near(map: &Map, seen: &[bool], p: Point) -> bool {
    [(0., 0.), (1., 0.), (-1., 0.), (0., 1.), (0., -1.)]
        .iter()
        .any(|(dx, dy)| reached(map, seen, at(p.x + dx, p.y + dy)))
}

// ---- data ----------------------------------------------------------------------------------------------------------------------
#[test]
fn bifrost_reach_is_a_sky_zone_with_five_kinds_one_hub_three_wards_and_a_gate_pair() {
    let w = world();
    let map = &w.maps[SKY];
    assert_eq!(map.name, "Bifrost Reach");
    assert_eq!((map.size, map.levels), (160, Some([30, 35])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert_eq!(map.copies, 0);
    // enemies: every kind at its default level, in the counts the design lists (sleeping ward waves apart)
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    let mut asleep = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == SKY) {
        if let Some(tag) = &spawn.ambush {
            *asleep.entry(spawn.kind.as_str()).or_default() += 1;
            let s = &w.slimes[id];
            assert!(
                s.dead && s.state == "waiting" && s.respawn >= 1e8,
                "{tag} sleeps"
            );
            assert!(
                map.places
                    .iter()
                    .any(|p| p.waves.iter().any(|wave| &wave.tag == tag)),
                "{tag} belongs to a ward"
            );
        } else {
            *live.entry(spawn.kind.as_str()).or_default() += 1;
            assert!(!w.slimes[id].dead, "{} is on the field", spawn.kind);
        }
        assert!(!map.in_city(at(spawn.x, spawn.y)));
    }
    assert_eq!(
        live.into_iter().collect::<Vec<_>>(),
        [
            ("einherjar", 10),
            ("galehound", 8),
            ("prismgolem", 8),
            ("skyray", 10),
            ("thunderroc", 9)
        ]
    );
    // the waves: two galehounds, two einherjar and a skyray, then two thunderrocs, two prism golems and two thunderrocs
    assert_eq!(
        asleep.into_iter().collect::<Vec<_>>(),
        [
            ("einherjar", 2),
            ("galehound", 2),
            ("prismgolem", 2),
            ("skyray", 1),
            ("thunderroc", 4)
        ]
    );
    for (kind, level) in [
        ("galehound", 30),
        ("prismgolem", 31),
        ("skyray", 32),
        ("einherjar", 33),
        ("thunderroc", 35),
    ] {
        assert_eq!(Slime::default_level(kind), level, "{kind}");
        assert!(!is_elite(kind), "{kind} is an ordinary kind");
    }
    // the new zone comes last of the file's zones, so every older enemy id stays
    assert_eq!(
        w.spawns.iter().position(|s| s.zone == SKY),
        Some(w.spawns.iter().filter(|s| s.zone < SKY).count())
    );
    // one hub on the arrival island, safe ground, with a travel master
    assert!(map.camps.is_empty());
    assert_eq!(
        map.city.as_ref().map(|c| (c.x0, c.x1, c.y0, c.y1)),
        Some((62., 98., 124., 153.))
    );
    assert!(map.in_city(at(80., 136.)) && !map.in_city(at(30., 106.)));
    let master = map
        .npcs
        .iter()
        .find(|n| n.travel_stop.is_some())
        .expect("a travel master");
    assert_eq!(master.id, "travel_perch");
    assert_eq!(map.npcs.len(), 8, "seven people and the travel master");
    // the gate pair: the Wyrdwood's Stormrift up, and the Perch's down, each arrival clear of every gate and of enemies
    let up = w.maps[WYRD]
        .portals
        .iter()
        .find(|p| p.id == "sky_gate")
        .unwrap();
    let down = map
        .portals
        .iter()
        .find(|p| p.id == "stormrift_down")
        .unwrap();
    assert_eq!((up.to, down.to), (SKY, WYRD));
    assert_eq!((up.tx, up.ty), (map.spawn.x, map.spawn.y));
    assert_eq!((down.tx, down.ty), (24., 14.));
    for (arrival, gates) in [
        (at(up.tx, up.ty), &map.portals),
        (at(down.tx, down.ty), &w.maps[WYRD].portals),
    ] {
        for gate in gates {
            assert!(
                arrival.distance(at(gate.x, gate.y)) > gate.r + 0.5,
                "{} is clear of {}",
                arrival.x,
                gate.id
            );
        }
    }
    for m in [map.spawn, at(down.tx, down.ty)] {
        let zone = if m.x == map.spawn.x { SKY } else { WYRD };
        let mut clear = m;
        w.maps[zone].collide(&mut clear, PLAYER_RADIUS);
        assert!(clear.distance(m) < 1e-6, "{m:?} is free ground");
        for s in w.slimes.iter().filter(|s| s.zone == zone) {
            assert!(
                s.point().distance(m) > 8.,
                "{} is clear of the arrival",
                s.kind
            );
        }
    }
    assert!(
        w.maps[WYRD].portals.len() == 2 && w.maps[WYRD].portals[0].id == "skaldholm_gate",
        "the Wyrdwood's old gate keeps index 0"
    );
    // places: the ward circles carry waves, the rest are plain visit spots; a map without `waves` still loads
    assert_eq!(map.places.len(), 7);
    assert_eq!(map.places.iter().filter(|p| !p.waves.is_empty()).count(), 3);
    let old: Place = serde_json::from_str(r#"{"id":"a","name":"A","x":1,"y":2,"r":3}"#).unwrap();
    assert!(old.waves.is_empty());
}

#[test]
fn the_void_is_sealed_nobody_can_walk_off_an_island_or_a_bridge() {
    let w = world();
    let map = &w.maps[SKY];
    let floor = rows();
    assert_eq!(floor.len(), 160);
    assert!(floor.iter().all(|r| r.len() == 160));
    // a ring of void rectangles round every island and bridge
    let rects = map
        .objects
        .iter()
        .filter(|o| o.width > 0. && o.depth > 0.)
        .count();
    assert!(rects > 300, "a ring of void round every island: {rects}");
    // every cell a hero can reach from the arrival lies on the floor
    let grid = blocked(map, &[]);
    let open = flood(map, &grid, map.spawn);
    let n = (map.size as f64 / STEP) as usize;
    let mut reachable = 0;
    for j in 0..n {
        for i in 0..n {
            if open[j * n + i] {
                reachable += 1;
                let (x, y) = ((i as f64 + 0.5) * STEP, (j as f64 + 0.5) * STEP);
                assert!(
                    on_floor(&floor, x, y),
                    "({x}, {y}) is reachable over the void"
                );
            }
        }
    }
    assert!(
        reachable > 5000,
        "{reachable} walkable cells: the whole archipelago"
    );
    // every person, every live enemy, every place, both gates and every ward ambusher can be walked to
    for npc in &map.npcs {
        assert!(
            near(map, &open, at(npc.x, npc.y)),
            "{} is unreachable",
            npc.id
        );
    }
    for s in w.slimes.iter().filter(|s| s.zone == SKY) {
        assert!(near(map, &open, s.point()), "{} at {:?}", s.kind, s.point());
        assert!(on_floor(&floor, s.x, s.y), "{} stands on the floor", s.kind);
    }
    for p in &map.places {
        // a landmark stands in the middle of its place
        assert!(near(map, &open, at(p.x, p.y + 2.4)), "{}", p.id);
    }
    for g in &map.portals {
        assert!(near(map, &open, at(g.x, g.y - 2.)), "{}", g.id);
    }
    // a real walk with the real collision: out through a bridge's end into the void stops at the edge
    let mut p = at(30., 130.);
    for _ in 0..40 {
        map.walk(&mut p, at(0., 1.), 1., PLAYER_RADIUS);
    }
    assert!(on_floor(&floor, p.x, p.y), "stopped at {p:?}");
    let mut dash = at(80., 150.);
    map.walk(&mut dash, at(0., 1.), 12., PLAYER_RADIUS);
    assert!(
        on_floor(&floor, dash.x, dash.y),
        "a dash cannot tunnel through the void: {dash:?}"
    );
}

#[test]
fn each_bridge_closes_exactly_the_islands_beyond_it_so_the_bands_come_in_order() {
    let w = world();
    let map = &w.maps[SKY];
    // the middle of a bridge's long leg; closing it is a disc 3.4 wide
    let seal = |points: &[(f64, f64)]| -> Vec<(f64, f64, f64)> {
        points.iter().map(|&(x, y)| (x, y, 3.4)).collect()
    };
    let b_west = (43.5, 134.5);
    let b_east = (117.5, 134.5);
    let b_wcrown = (56.5, 106.5);
    let b_scrown = (104.5, 106.5);
    let b_hall = (49.5, 76.5);
    let b_eyrie = (85.5, 40.5);
    // which kinds still have a reachable representative with these bridges closed
    let cut = |closed: &[(f64, f64)]| -> Vec<&'static str> {
        let open = flood(map, &blocked(map, &seal(closed)), map.spawn);
        let mut gone = vec![];
        for kind in [
            "galehound",
            "prismgolem",
            "skyray",
            "einherjar",
            "thunderroc",
        ] {
            let mut live = w
                .slimes
                .iter()
                .filter(|s| s.zone == SKY && s.kind == kind && !s.dead);
            if !live.any(|s| near(map, &open, s.point())) {
                gone.push(kind);
            }
        }
        gone
    };
    assert!(cut(&[]).is_empty());
    assert_eq!(
        cut(&[b_west, b_east]),
        [
            "galehound",
            "prismgolem",
            "skyray",
            "einherjar",
            "thunderroc"
        ],
        "the Perch has two exits"
    );
    assert_eq!(
        cut(&[b_west]),
        Vec::<&str>::new(),
        "the ring: the east way still reaches everything"
    );
    assert_eq!(cut(&[b_west, b_wcrown]), ["galehound"]);
    assert_eq!(cut(&[b_east, b_scrown]), ["prismgolem"]);
    assert_eq!(
        cut(&[b_wcrown, b_scrown]),
        ["skyray", "einherjar", "thunderroc"],
        "the Stormcrown needs one of its two bridges"
    );
    assert_eq!(cut(&[b_hall]), ["einherjar", "thunderroc"]);
    assert_eq!(cut(&[b_eyrie]), ["thunderroc"]);
    // the wards: the first lies on its own islet, the vigil in the hall, the last in the Eyrie
    let open = |closed: &[(f64, f64)]| flood(map, &blocked(map, &seal(closed)), map.spawn);
    let ward_wind = place_of(&w, "sky_ward_wind");
    let ward_vigil = place_of(&w, "sky_ward_vigil");
    let ward_last = place_of(&w, "sky_ward_last");
    let reach = |seen: &[bool], p: &Place| near(map, seen, at(p.x, p.y + 2.4));
    assert!(reach(&open(&[]), &ward_wind));
    assert!(
        !reach(&open(&[(12.5, 87.5)]), &ward_wind),
        "the islet hangs off one short bridge"
    );
    assert!(!reach(&open(&[b_hall]), &ward_vigil));
    assert!(reach(&open(&[b_eyrie]), &ward_vigil));
    assert!(!reach(&open(&[b_eyrie]), &ward_last));
}

#[test]
fn every_bifrost_monster_has_its_own_stats_attacks_materials_and_rewards() {
    for (kind, hp, damage, gold, material_id) in [
        ("galehound", 12500., 275., 430, "gale_fang"),
        ("prismgolem", 17500., 330., 460, "prism_shard"),
        ("skyray", 13500., 300., 490, "stormray_wing"),
        ("einherjar", 18500., 370., 520, "rune_token"),
        ("thunderroc", 22000., 440., 600, "thunderroc_quill"),
    ] {
        let spawn = SlimeSpawn {
            ambush: None,
            x: 5.,
            y: 5.,
            kind: kind.into(),
            zone: SKY,
        };
        let level = Slime::default_level(kind);
        let base = Slime::with_level(0, &spawn, level);
        assert_eq!(
            (base.max_hp, base.damage, base.gold),
            (hp, damage, gold),
            "{kind}"
        );
        assert_eq!(base.xp, enemy_xp(level));
        let up = Slime::with_level(0, &spawn, level + 2);
        assert_eq!(up.max_hp, (hp * 1.24_f64).round());
        assert_eq!(up.xp, enemy_xp(level + 2));
        assert_eq!(material(kind), material_id);
        let i = item(material_id).expect("the material is in the catalog");
        assert_eq!((i.kind.as_str(), i.rarity.as_str()), ("material", "common"));
        // a real kill pays that level's XP and gold, and drops the material, all in Bifrost Reach
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.players.get_mut(&1).unwrap().character.zone = SKY;
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == SKY && s.kind == kind && !s.dead)
            .unwrap();
        w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), level + 1);
        let (xp, gold) = (w.slimes[id].xp, w.slimes[id].gold);
        w.hit_slime(id, 1, 1e9, false);
        let c = &w.players[&1].character;
        let paid: u32 = (1..c.level).map(xp_to_level).sum::<u32>() + c.xp;
        assert_eq!(paid, xp, "{kind} xp");
        assert_eq!(
            w.drops.iter().find(|d| d.item.is_none()).unwrap().value,
            gold
        );
        assert!(
            w.drops
                .iter()
                .any(|d| d.item.as_deref() == Some(material_id)),
            "{kind} material"
        );
        assert!(w.drops.iter().all(|d| d.zone == SKY));
    }
    // how each one fights: only the skyray shoots, only the golem pounds the ground, the roc charges fastest
    let ray = Slime::ranged("skyray").unwrap();
    assert_eq!((ray.shots, ray.range), (2, 12.));
    for kind in ["galehound", "prismgolem", "einherjar", "thunderroc"] {
        assert!(Slime::ranged(kind).is_none(), "{kind}");
    }
    assert_eq!(Slime::slam_radius("prismgolem"), 3.);
    for kind in ["galehound", "skyray", "einherjar", "thunderroc"] {
        assert_eq!(Slime::slam_radius(kind), 0., "{kind}");
    }
    let charge = |k: &str| Slime::attack_profile(k).2;
    assert!(
        charge("thunderroc") > charge("galehound") && charge("galehound") > charge("einherjar")
    );
    assert_eq!(charge("skyray"), 0., "a ray never charges");
    for kind in [
        "galehound",
        "prismgolem",
        "skyray",
        "einherjar",
        "thunderroc",
    ] {
        assert!(
            !Slime::fixed_level(kind),
            "{kind} rolls its level like any open-world kind"
        );
    }
}

// ---- the questline -----------------------------------------------------------------------------------------------------------------
#[test]
fn the_questline_has_twenty_two_quests_with_three_wards_and_the_old_objective_kinds() {
    let w = world();
    let map = &w.maps[SKY];
    assert_eq!(map.quests.len(), 22);
    let mut kinds = std::collections::BTreeSet::new();
    let mut holds = vec![];
    for q in &map.quests {
        assert!(npc_exists(map, &q.npc), "{} giver {}", q.id, q.npc);
        assert_eq!(
            q.reward_xp,
            xp_to_level(q.level) / 10,
            "{} pays a tenth of its level",
            q.id
        );
        assert!(
            (30..=35).contains(&q.level),
            "{} is a level 30-35 quest",
            q.id
        );
        for o in &q.objectives {
            kinds.insert(o.kind.clone());
            match o.kind.as_str() {
                "kill" => assert!(
                    o.target == "any" || map.slimes.iter().any(|s| s.kind == o.target),
                    "{}",
                    q.id
                ),
                "bring" => assert!(item(&o.target).is_some_and(|i| i.kind == "material")),
                "talk" => assert!(npc_exists(map, &o.target), "{}", q.id),
                "visit" => assert!(map.places.iter().any(|p| p.id == o.target)),
                "reach" => assert_eq!(o.target, "Bifrost Reach"),
                "hold" => {
                    let place = map
                        .places
                        .iter()
                        .find(|p| p.id == o.target)
                        .expect("a ward");
                    assert!(!place.waves.is_empty(), "{} is a ward with waves", place.id);
                    // the last wave comes before the ward is held
                    assert!(place.waves.iter().all(|wave| wave.at < o.count));
                    holds.push((q.id.clone(), o.target.clone(), o.count));
                }
                other => panic!("unsupported objective {other}"),
            }
        }
        if let Some(requires) = &q.requires {
            assert!(
                map.quests.iter().any(|r| &r.id == requires),
                "{} requires {requires}",
                q.id
            );
        }
    }
    assert_eq!(
        kinds.into_iter().collect::<Vec<_>>(),
        ["bring", "hold", "kill", "reach", "talk", "visit"]
    );
    assert_eq!(
        holds,
        [
            ("sky_ward_wind".to_string(), "sky_ward_wind".to_string(), 60),
            (
                "sky_ward_vigil".to_string(),
                "sky_ward_vigil".to_string(),
                75
            ),
            (
                "sky_ward_last".to_string(),
                "sky_ward_last".to_string(),
                120
            ),
        ]
    );
    // the last ward is the group quest: three heroes, hired at its giver, and an epic reward
    let last = quest(&w, "sky_ward_last");
    assert!(last.group && last.recommended_players == 3);
    assert_eq!(
        last.reward_item.as_deref(),
        Some("pants_wayfarer_l20_purple")
    );
    assert!(item("pants_wayfarer_l20_purple").is_some());
    assert!(
        npc(&w, "sky_warden")
            .offers
            .iter()
            .any(|o| o.merc.is_some())
    );
    // the progression quest finds you at level 30 and is handed in at the Perch's warden
    let onward = quest(&w, "sky_onward");
    assert_eq!(
        (onward.auto_level, onward.npc.as_str()),
        (Some(30), "sky_warden")
    );
    // a hold objective is never repeatable: no repeatable quest uses one
    assert!(
        map.quests
            .iter()
            .filter(|q| q.repeatable)
            .all(|q| q.objectives.iter().all(|o| o.kind != "hold"))
    );
}
fn npc_exists(map: &Map, id: &str) -> bool {
    map.npcs.iter().any(|n| n.id == id)
}

// ---- hold the ward -----------------------------------------------------------------------------------------------------------------
/// A world with every enemy asleep, and a level-40 hero in god mode who has taken the quest and stands at (x, y) of the zone.
fn holder(quest_id: &str, zone: usize, at_: Point) -> (World, mpsc::Receiver<Value>) {
    let mut w = world();
    calm(&mut w);
    w.god_mode = true;
    let rx = join(&mut w, 1, Class::Warrior);
    let objectives = quest(&w, quest_id).objectives.len();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 40;
    c.quests.push(QuestProgress {
        id: quest_id.into(),
        counts: vec![0; objectives],
        claimed: false,
        completions: 0,
    });
    place(&mut w, 1, zone, at_);
    (w, rx)
}
fn held(w: &World) -> u32 {
    w.players[&1].character.quests[0].counts[0]
}
/// Steps the world and returns every notice and system line the hero was sent meanwhile.
fn run(w: &mut World, rx: &mut mpsc::Receiver<Value>, ticks: usize) -> Vec<String> {
    let mut told = vec![];
    for _ in 0..ticks {
        w.step();
        told.extend(lines(rx));
    }
    told
}
fn set_held(w: &mut World, value: u32) {
    w.players.get_mut(&1).unwrap().character.quests[0].counts[0] = value;
}
/// The enemies of one ward wave that are on the field.
fn awake(w: &World, tag: &str) -> Vec<usize> {
    (0..w.spawns.len())
        .filter(|&i| w.spawns[i].ambush.as_deref() == Some(tag) && !w.slimes[i].dead)
        .collect()
}
fn asleep_all(w: &World, place: &Place) -> bool {
    place.waves.iter().all(|wave| {
        (0..w.spawns.len())
            .filter(|&i| w.spawns[i].ambush.as_deref() == Some(wave.tag.as_str()))
            .all(|i| {
                w.slimes[i].dead && w.slimes[i].state == "waiting" && w.slimes[i].respawn >= 1e8
            })
    })
}

#[test]
fn a_ward_counts_one_second_per_second_inside_the_circle_and_pauses_outside() {
    let ward = place_of(&world(), "sky_ward_wind");
    let (mut w, mut rx) = holder("sky_ward_wind", SKY, at(ward.x, ward.y + 2.));
    let told = run(&mut w, &mut rx, 19);
    assert_eq!(held(&w), 0, "not yet a second");
    assert!(
        !told.iter().any(|t| t.contains("begin to hold")),
        "{told:?}"
    );
    let told = run(&mut w, &mut rx, 1);
    assert_eq!(held(&w), 1);
    assert!(told.iter().any(|t| t.contains("begin to hold")), "{told:?}");
    run(&mut w, &mut rx, 40);
    assert_eq!(held(&w), 3);
    // the edge of the circle counts, a step past it does not
    place(&mut w, 1, SKY, at(ward.x + ward.r - 0.3, ward.y));
    run(&mut w, &mut rx, 20);
    assert_eq!(held(&w), 4, "inside by a hair");
    place(&mut w, 1, SKY, at(ward.x + ward.r + 0.4, ward.y));
    run(&mut w, &mut rx, 200);
    assert_eq!(held(&w), 4, "outside only pauses the count");
    place(&mut w, 1, SKY, at(ward.x, ward.y + 1.));
    run(&mut w, &mut rx, 20);
    assert_eq!(held(&w), 5, "and it picks up where it stopped");
}

#[test]
fn a_ward_only_counts_for_a_hero_who_took_the_quest_in_the_zone_that_has_it() {
    let ward = place_of(&world(), "sky_ward_wind");
    // not accepted: nothing counts and nothing wakes
    let mut w = world();
    calm(&mut w);
    w.god_mode = true;
    let mut rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, SKY, at(ward.x, ward.y + 2.));
    run(&mut w, &mut rx, 400);
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .all(|q| q.id != "sky_ward_wind")
    );
    assert!(w.hold.fired.is_empty() && awake(&w, "sky_ward_wind#a").is_empty());
    // already claimed: no more counting
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.quests.push(QuestProgress {
            id: "sky_ward_wind".into(),
            counts: vec![60],
            claimed: true,
            completions: 1,
        });
    }
    run(&mut w, &mut rx, 100);
    assert_eq!(w.players[&1].character.quests[0].counts[0], 60);
    assert!(w.hold.fired.is_empty());
    // the same coordinates in another zone are not a ward: only the zone's own places count
    let (mut w, mut rx) = holder("sky_ward_wind", 1, at(ward.x, ward.y));
    run(&mut w, &mut rx, 100);
    assert_eq!(held(&w), 0);
    // a hero without the quest next to one who holds it does not count, and the holder still does
    let (mut w, mut rx) = holder("sky_ward_wind", SKY, at(ward.x, ward.y + 1.));
    let mut rx2 = join(&mut w, 2, Class::Mage);
    place(&mut w, 2, SKY, at(ward.x + 1., ward.y));
    run(&mut w, &mut rx, 60);
    drain(&mut rx2);
    assert_eq!(held(&w), 3);
    assert!(w.players[&2].character.quests.is_empty());
}

#[test]
fn waves_wake_at_their_marks_hunt_the_holder_and_each_wave_comes_once() {
    let ward = place_of(&world(), "sky_ward_wind");
    let (mut w, mut rx) = holder("sky_ward_wind", SKY, at(ward.x, ward.y + 1.));
    set_held(&mut w, 13);
    run(&mut w, &mut rx, 20);
    assert_eq!(held(&w), 14);
    assert!(
        awake(&w, "sky_ward_wind#a").is_empty(),
        "the first wave comes at 15 s"
    );
    run(&mut w, &mut rx, 20);
    assert_eq!(held(&w), 15);
    let first = awake(&w, "sky_ward_wind#a");
    assert_eq!(first.len(), 1, "one galehound");
    for &id in &first {
        let s = &w.slimes[id];
        assert_eq!(
            (s.kind.as_str(), s.zone, s.target, s.hunt),
            ("galehound", SKY, Some(1), true)
        );
        assert_eq!(s.level, 30);
    }
    assert!(awake(&w, "sky_ward_wind#b").is_empty());
    // kill the first wave: it does not come back at the next second, nor when the count passes the mark again
    for &id in &first {
        w.hit_slime(id, 1, 1e9, false);
    }
    run(&mut w, &mut rx, 80);
    assert!(awake(&w, "sky_ward_wind#a").is_empty(), "a wave comes once");
    set_held(&mut w, 39);
    run(&mut w, &mut rx, 20);
    let second = awake(&w, "sky_ward_wind#b");
    assert_eq!(held(&w), 40);
    assert_eq!(second.len(), 1, "the second galehound at 40 s");
    // the enemies of the ward are shared slots: a wave that is awake is not woken a second time
    run(&mut w, &mut rx, 40);
    assert_eq!(awake(&w, "sky_ward_wind#b"), second);
    // the vigil sends three waves and the last ward two kinds of heavy hitter
    let waves = |id: &str| {
        place_of(&w, id)
            .waves
            .iter()
            .map(|x| (x.at, x.tag.clone()))
            .collect::<Vec<_>>()
    };
    assert_eq!(
        waves("sky_ward_vigil"),
        [
            (10, "sky_ward_vigil#a".to_string()),
            (40, "sky_ward_vigil#b".to_string()),
            (65, "sky_ward_vigil#c".to_string())
        ]
    );
    assert_eq!(waves("sky_ward_last").len(), 3);
}

#[test]
fn holding_the_ward_for_its_full_time_completes_the_objective_and_the_storm_spawn_dissolve() {
    let ward = place_of(&world(), "sky_ward_wind");
    let (mut w, mut rx) = holder("sky_ward_wind", SKY, at(ward.x, ward.y + 1.));
    set_held(&mut w, 34);
    run(&mut w, &mut rx, 20);
    assert!(!awake(&w, "sky_ward_wind#a").is_empty() || !awake(&w, "sky_ward_wind#b").is_empty());
    set_held(&mut w, 58);
    run(&mut w, &mut rx, 20);
    assert_eq!(held(&w), 59);
    assert!(
        !quest(&w, "sky_ward_wind").ready(&w.players[&1].character.quests[0]),
        "59 of 60 is not enough"
    );
    drain(&mut rx);
    run(&mut w, &mut rx, 19);
    let told = run(&mut w, &mut rx, 1);
    assert_eq!(held(&w), 60);
    assert!(quest(&w, "sky_ward_wind").ready(&w.players[&1].character.quests[0]));
    assert!(
        asleep_all(&w, &ward),
        "every wave dissolves when the ward holds"
    );
    assert!(w.hold.fired.is_empty());
    assert!(told.iter().any(|t| t.contains("holds")), "{told:?}");
    // and it stays at 60: standing on in the circle changes nothing and wakes nothing
    run(&mut w, &mut rx, 200);
    assert_eq!(held(&w), 60);
    assert!(asleep_all(&w, &ward));
}

#[test]
fn falling_at_the_ward_loses_the_count_and_puts_the_waves_back_to_sleep() {
    let ward = place_of(&world(), "sky_ward_wind");
    let (mut w, mut rx) = holder("sky_ward_wind", SKY, at(ward.x, ward.y + 1.));
    w.god_mode = false;
    set_held(&mut w, 29);
    run(&mut w, &mut rx, 20);
    assert_eq!(held(&w), 30);
    w.release_ambush("sky_ward_wind#a", 1);
    assert!(!awake(&w, "sky_ward_wind#a").is_empty());
    drain(&mut rx);
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    let told = run(&mut w, &mut rx, 1);
    assert_eq!(held(&w), 0, "the whole count is lost");
    assert!(asleep_all(&w, &ward));
    assert!(told.iter().any(|t| t.contains("collapses")), "{told:?}");
    // a hero who died far from the ward keeps what they had
    let (mut w, mut rx) = holder("sky_ward_wind", SKY, at(80., 140.));
    w.god_mode = false;
    set_held(&mut w, 30);
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    run(&mut w, &mut rx, 2);
    assert_eq!(held(&w), 30);
}

#[test]
fn enemies_left_awake_by_a_hero_who_walked_away_go_back_to_sleep_after_twelve_seconds() {
    let ward = place_of(&world(), "sky_ward_wind");
    let (mut w, mut rx) = holder("sky_ward_wind", SKY, at(ward.x, ward.y + 1.));
    set_held(&mut w, 14);
    run(&mut w, &mut rx, 20);
    assert!(!awake(&w, "sky_ward_wind#a").is_empty());
    // the hero leaves for the Perch, far from the ward: nobody is near it any more
    place(&mut w, 1, SKY, at(80., 140.));
    run(&mut w, &mut rx, 200);
    assert!(
        !awake(&w, "sky_ward_wind#a").is_empty(),
        "ten seconds is not enough"
    );
    run(&mut w, &mut rx, 60);
    assert!(asleep_all(&w, &ward), "twelve seconds with nobody near");
    assert!(w.hold.fired.is_empty());
    assert_eq!(held(&w), 15, "the count is kept");
    // coming back wakes the first wave again, since it has not been beaten
    place(&mut w, 1, SKY, at(ward.x, ward.y + 1.));
    run(&mut w, &mut rx, 20);
    assert_eq!(held(&w), 16);
    assert!(!awake(&w, "sky_ward_wind#a").is_empty());
}

#[test]
fn a_held_ward_pays_its_reward_through_the_giver_and_a_hero_cannot_claim_it_early() {
    let w0 = world();
    let q = quest(&w0, "sky_ward_wind");
    let giver = npc(&w0, &q.npc);
    let (mut w, mut rx) = holder("sky_ward_wind", SKY, at(giver.x, giver.y + 1.5));
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.quests.push(QuestProgress {
            id: "sky_cairn".into(),
            claimed: true,
            completions: 1,
            counts: vec![1, 3],
        });
        c.level = 31;
    }
    w.time += 0.6;
    w.interact(1, &q.npc, Some("quest:claim:sky_ward_wind"));
    assert!(
        !w.players[&1].character.quests[0].claimed,
        "an unfinished ward cannot be claimed"
    );
    set_held(&mut w, 60);
    let gold = w.players[&1].character.gold;
    let (level, xp) = (w.players[&1].character.level, w.players[&1].character.xp);
    w.time += 0.6;
    w.interact(1, &q.npc, Some("quest:claim:sky_ward_wind"));
    run(&mut w, &mut rx, 1);
    let c = &w.players[&1].character;
    assert!(c.quests[0].claimed && c.quests[0].completions == 1);
    assert_eq!(c.gold, gold + q.reward_gold);
    let paid: u32 = (level..c.level).map(xp_to_level).sum::<u32>() + c.xp - xp;
    assert_eq!(paid, q.reward_xp);
}

// ---- the gates and the flight ----------------------------------------------------------------------------------------------------------
#[test]
fn the_stormrift_carries_a_hero_up_and_the_perch_gate_carries_them_down_without_bouncing() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    let up = w.maps[WYRD]
        .portals
        .iter()
        .find(|p| p.id == "sky_gate")
        .unwrap()
        .clone();
    place(&mut w, 1, WYRD, at(up.x, up.y + 4.));
    w.message(
        1,
        ClientMessage::Move {
            x: up.x,
            y: up.y - 1.,
        },
    );
    for _ in 0..200 {
        w.time += TICK;
        w.update_player(1);
        if w.players[&1].character.zone == SKY {
            break;
        }
    }
    let c = &w.players[&1].character;
    assert_eq!(c.zone, SKY);
    assert!(c.point().distance(at(up.tx, up.ty)) < 1e-6);
    assert!(w.maps[SKY].in_city(c.point()), "you land in the hub");
    assert_eq!(w.snapshot_for(SKY)["players"].as_array().unwrap().len(), 1);
    assert!(
        w.snapshot_for(WYRD)["players"]
            .as_array()
            .unwrap()
            .is_empty()
    );
    // standing in the way back too soon does nothing; a moment later it carries you down to the summit court
    let down = w.maps[SKY].portals[0].clone();
    place(&mut w, 1, SKY, at(down.x, down.y));
    w.update_player(1);
    assert_eq!(w.players[&1].character.zone, SKY, "no instant bounce");
    w.time += PORTAL_DELAY + 0.1;
    w.update_player(1);
    let c = &w.players[&1].character;
    assert_eq!(c.zone, WYRD);
    assert!(c.point().distance(at(down.tx, down.ty)) < 1e-6);
    assert!(c.point().distance(at(up.x, up.y)) > up.r + 0.5);
}

#[test]
fn the_perch_has_its_own_spark_travel_master_linked_to_skuldwatch() {
    let w = world();
    assert_eq!(npc(&w, "travel_perch").travel_links, ["travel_skuldwatch"]);
    assert!(
        w.maps[WYRD]
            .npcs
            .iter()
            .find(|n| n.id == "travel_skuldwatch")
            .unwrap()
            .travel_links
            .iter()
            .any(|l| l == "travel_perch")
    );
    let master = npc(&w, "travel_perch");
    let mut at_ = at(master.x, master.y);
    w.maps[SKY].collide(&mut at_, PLAYER_RADIUS);
    assert!(
        at_.distance(at(master.x, master.y)) < 1e-6,
        "the master stands on free ground"
    );
    assert!(w.maps[SKY].in_city(at(master.x, master.y)));
    assert_eq!(
        w.maps[SKALD].portals.len(),
        3,
        "Skaldholm's gates are untouched"
    );
}

// ---- balance: a hero (and hired fighters) holding each ward against its waves --------------------------------------------------------
struct WardFight {
    held: bool,
    seconds: f64,
    deaths: u32,
    count: u32,
}
/// A trained hero of `level` takes `quest_id` from its giver, hires `classes` (when the quest allows it) and holds the ward with the
/// real skills, potions and AI mercenaries. Heroes do not path-find in tests, so everyone is staged at the ward and a fallen hero
/// is put back in the circle (which has lost its count, as in play).
fn ward_fight(quest_id: &str, pre: &[&str], level: u32, classes: &[&str], limit: f64) -> WardFight {
    let mut w = world();
    w.rng = 7;
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    let q = quest(&w, quest_id);
    let ward = place_of(&w, &q.objectives[0].target);
    let giver = npc(&w, &q.npc);
    {
        let points = (level - 1) * 3;
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = level;
        c.gold = 9000;
        c.attributes.stamina = points / 5;
        c.attributes.accuracy = 7;
        c.attributes.strength = points - points / 5 - 7;
        c.add_item("health_potion", 3);
        for p in pre {
            c.quests.push(QuestProgress {
                id: (*p).into(),
                claimed: true,
                completions: 1,
                ..Default::default()
            });
        }
    }
    place(&mut w, 1, SKY, at(giver.x, giver.y + 1.));
    w.time += 0.6;
    w.interact(1, &q.npc, Some(&format!("quest:accept:{quest_id}")));
    for class in classes {
        w.time += 0.6;
        w.interact(1, &q.npc, Some(&format!("merc_{class}")));
    }
    drain(&mut rx);
    assert_eq!(
        w.players.values().filter(|p| p.merc.is_some()).count(),
        classes.len()
    );
    let home = at(ward.x, ward.y + 1.5);
    place(&mut w, 1, SKY, home);
    for (i, p) in w
        .players
        .values_mut()
        .filter(|p| p.merc.is_some())
        .enumerate()
    {
        p.character.zone = SKY;
        p.character.x = ward.x + 1.5 + i as f64;
        p.character.y = ward.y - 1.5;
    }
    let (mut deaths, mut elapsed) = (0, 0.);
    let index = w.players[&1]
        .character
        .quests
        .iter()
        .position(|p| p.id == quest_id)
        .unwrap();
    for _ in 0..(limit / TICK) as usize {
        let fallen = w.players[&1].character.hp <= 0.;
        if !fallen {
            // the nearest enemy that is awake, if any
            let me = w.players[&1].character.point();
            let foe = (0..w.slimes.len())
                .filter(|&i| w.slimes[i].zone == SKY && !w.slimes[i].dead)
                .min_by(|&a, &b| {
                    w.slimes[a]
                        .point()
                        .distance(me)
                        .total_cmp(&w.slimes[b].point().distance(me))
                });
            if let Some(id) = foe {
                w.message(1, ClientMessage::Target { id });
                let aim = me.direction(w.slimes[id].point());
                for skill in [
                    "battlecry",
                    "shieldwall",
                    "cleave",
                    "whirlwind",
                    "charge",
                    "groundslam",
                ] {
                    w.use_skill(1, skill, aim);
                }
            }
            let c = &w.players[&1].character;
            if c.hp <= c.max_hp() - 150. {
                w.use_item(1, "health_potion");
            }
        }
        // a fallen hero stays down for this tick, so the ward sees the fall (and loses its count), then is put back in the circle
        w.step();
        elapsed += TICK;
        drain(&mut rx);
        if fallen {
            deaths += 1;
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.hp = c.max_hp();
            c.x = home.x;
            c.y = home.y;
            w.players.get_mut(&1).unwrap().dead_time = 0.;
        }
        for (_, p) in w.players.iter_mut().filter(|(_, p)| p.merc.is_some()) {
            if p.character.hp <= 0. {
                deaths += 1;
                p.character.hp = p.character.max_hp();
                p.character.x = ward.x + 2.;
                p.character.y = ward.y - 2.;
            }
        }
        // a hero pulled out of the circle by the chase is put back (a player would step back in)
        let c = &mut w.players.get_mut(&1).unwrap().character;
        if c.point().distance(at(ward.x, ward.y)) > ward.r - 0.5 && c.hp > 0. {
            c.x = home.x;
            c.y = home.y;
        }
        if q.ready(&w.players[&1].character.quests[index]) {
            break;
        }
    }
    let count = w.players[&1].character.quests[index].counts[0];
    WardFight {
        held: q.ready(&w.players[&1].character.quests[index]),
        seconds: elapsed,
        deaths,
        count,
    }
}

#[test]
#[ignore = "balance probe: prints how parties fare at the three wards (cargo test --release ward_balance_probe -- --ignored --nocapture)"]
fn ward_balance_probe() {
    let report = |label: &str, f: WardFight| {
        eprintln!(
            "{label}: held {} ({} s counted) in {:.0} s, deaths {}",
            f.held, f.count, f.seconds, f.deaths
        )
    };
    // only the group quest lets its giver hire fighters: the first two wards are a hero alone, at three levels
    for level in [30, 31, 32] {
        report(
            &format!("first ward, lone hero of level {level}"),
            ward_fight("sky_ward_wind", &["sky_cairn"], level, &[], 400.),
        );
    }
    for level in [33, 34, 35] {
        report(
            &format!("vigil, lone hero of level {level}"),
            ward_fight("sky_ward_vigil", &["sky_hallgate"], level, &[], 500.),
        );
    }
    for classes in [vec![], vec!["priest"], vec!["warrior", "priest"]] {
        report(
            &format!("last ward (lvl 35), hirer + {classes:?}"),
            ward_fight("sky_ward_last", &["sky_quills"], 35, &classes, 700.),
        );
    }
}

// ---- balance: one trained hero against one ordinary monster -----------------------------------------------------------------------
/// A hero of `level` (stats trained the way the elite probes do, no gear, three potions) fights one default-level monster of `kind`
/// until it falls or the hero does. Returns (won, seconds, health left of the hero as a fraction).
fn duel(kind: &str, level: u32) -> (bool, f64, f64) {
    let mut w = world();
    w.rng = 7;
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    let id = w
        .slimes
        .iter()
        .position(|s| s.kind == kind && w.spawns[s.id].ambush.is_none())
        .unwrap();
    let zone = w.slimes[id].zone;
    let spawn = w.spawns[id].clone();
    w.slimes[id] = Slime::with_level(id, &spawn, Slime::default_level(kind));
    let point = w.slimes[id].point();
    {
        let points = (level - 1) * 3;
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = level;
        c.attributes.stamina = points / 5;
        c.attributes.accuracy = 7;
        c.attributes.strength = points - points / 5 - 7;
        c.add_item("health_potion", 3);
    }
    place(&mut w, 1, zone, at(point.x - 3., point.y));
    w.message(1, ClientMessage::Target { id });
    let mut elapsed = 0.;
    for _ in 0..(900. / TICK) as usize {
        let me = w.players[&1].character.point();
        if w.players[&1].character.hp <= 0. {
            return (false, elapsed, 0.);
        }
        if w.slimes[id].dead {
            let c = &w.players[&1].character;
            return (true, elapsed, c.hp / c.max_hp());
        }
        let aim = me.direction(w.slimes[id].point());
        for skill in [
            "battlecry",
            "shieldwall",
            "cleave",
            "whirlwind",
            "charge",
            "groundslam",
        ] {
            w.use_skill(1, skill, aim);
        }
        let c = &w.players[&1].character;
        if c.hp <= c.max_hp() - 150. {
            w.use_item(1, "health_potion");
        }
        w.step();
        elapsed += TICK;
        drain(&mut rx);
    }
    (
        false,
        elapsed,
        w.players[&1].character.hp / w.players[&1].character.max_hp(),
    )
}

#[test]
#[ignore = "balance probe: one level-matched hero against one monster of each older and newer kind (cargo test --release duel_probe -- --ignored --nocapture)"]
fn duel_probe() {
    for (kind, level) in [
        ("boar", 21),
        ("troll", 25),
        ("crow", 23),
        ("weaver", 27),
        ("ram", 29),
        ("galehound", 30),
        ("prismgolem", 31),
        ("skyray", 32),
        ("einherjar", 33),
        ("thunderroc", 35),
    ] {
        let (won, seconds, left) = duel(kind, level);
        eprintln!(
            "{kind} (lvl {level}) vs a hero of the same level: won {won} in {seconds:.0} s, hero health left {:.0}%",
            left * 100.
        );
    }
}

#[test]
fn the_last_ward_is_a_group_job_a_lone_hero_falls_again_and_again_and_a_hired_priest_carries_it() {
    let alone = ward_fight("sky_ward_last", &["sky_quills"], 35, &[], 200.);
    assert!(
        !alone.held && alone.deaths >= 3,
        "alone: {} s counted, {} deaths",
        alone.count,
        alone.deaths
    );
    let pair = ward_fight("sky_ward_last", &["sky_quills"], 35, &["priest"], 140.);
    assert!(
        pair.held,
        "hirer and priest: {} s counted, {} deaths",
        pair.count, pair.deaths
    );
    assert!(
        pair.seconds >= 119.,
        "a real wait, not a pull: {} s",
        pair.seconds
    );
    assert!(pair.deaths <= 2, "{} deaths", pair.deaths);
}
