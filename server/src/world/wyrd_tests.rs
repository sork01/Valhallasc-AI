//! The Wyrdwood (zone 6, levels 20-30): its data, geography, monsters, two hubs, visit objectives, the escort quest
//! and the two elites.
use super::*;

const SKALD: usize = 4;
const WYRD: usize = 6;
const STEP: f64 = 1.;

fn world() -> World {
    World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
}
fn join(w: &mut World, id: u64, class: Class) -> mpsc::Receiver<Value> {
    let (tx, rx) = mpsc::channel(4096);
    let look = Look {
        class,
        ..Look::default()
    };
    w.join(id, None, Some(look), tx).unwrap();
    rx
}
fn drain(rx: &mut mpsc::Receiver<Value>) -> Vec<Value> {
    std::iter::from_fn(|| rx.try_recv().ok()).collect()
}
/// Every notice and system line the player was sent, as text.
fn lines(rx: &mut mpsc::Receiver<Value>) -> Vec<String> {
    drain(rx)
        .into_iter()
        .filter(|v| matches!(v["type"].as_str(), Some("notice" | "system" | "dialogue")))
        .filter_map(|v| {
            v["text"]
                .as_str()
                .or(v["notice"].as_str())
                .map(str::to_owned)
        })
        .collect()
}
fn place(w: &mut World, session: u64, zone: usize, at: Point) {
    let c = &mut w.players.get_mut(&session).unwrap().character;
    c.zone = zone;
    c.x = at.x;
    c.y = at.y;
    c.hp = c.max_hp();
}
fn at(x: f64, y: f64) -> Point {
    Point { x, y }
}
fn npc(w: &World, id: &str) -> Npc {
    w.maps[WYRD]
        .npcs
        .iter()
        .find(|n| n.id == id)
        .unwrap_or_else(|| panic!("no NPC {id}"))
        .clone()
}
fn quest(w: &World, id: &str) -> Quest {
    w.maps[WYRD]
        .quests
        .iter()
        .find(|q| q.id == id)
        .unwrap_or_else(|| panic!("no quest {id}"))
        .clone()
}
/// Everything that moves in the Wyrdwood is put to sleep except what a test wants.
fn calm(w: &mut World) {
    for s in w.slimes.iter_mut() {
        s.dead = true;
        s.respawn = 1e9;
    }
}

// ---- a coarse walking grid: the same obstacles as Map::collide, rasterised --------------------------------------------------
fn grid_size(map: &Map) -> usize {
    (map.size as f64 / STEP) as usize
}
fn blocked(map: &Map, extra: &[(f64, f64, f64)]) -> Vec<bool> {
    let n = grid_size(map);
    let mut grid = vec![false; n * n];
    let r = PLAYER_RADIUS;
    for j in 0..n {
        for i in 0..n {
            let (x, y) = ((i as f64 + 0.5) * STEP, (j as f64 + 0.5) * STEP);
            if x < 0.7 + 0.5
                || y < 0.7 + 0.5
                || x > map.size as f64 - 1.2
                || y > map.size as f64 - 1.2
            {
                grid[j * n + i] = true;
            }
        }
    }
    let mut mark = |x0: f64, y0: f64, x1: f64, y1: f64, hit: &dyn Fn(f64, f64) -> bool| {
        for j in ((y0 / STEP).floor().max(0.) as usize)..=((y1 / STEP).ceil() as usize).min(n - 1) {
            for i in
                ((x0 / STEP).floor().max(0.) as usize)..=((x1 / STEP).ceil() as usize).min(n - 1)
            {
                let (x, y) = ((i as f64 + 0.5) * STEP, (j as f64 + 0.5) * STEP);
                if hit(x, y) {
                    grid[j * n + i] = true;
                }
            }
        }
    };
    for o in &map.objects {
        if o.width > 0. && o.depth > 0. {
            let (hx, hy) = (o.width / 2. + r, o.depth / 2. + r);
            mark(o.x - hx, o.y - hy, o.x + hx, o.y + hy, &|x, y| {
                (x - o.x).abs() < hx && (y - o.y).abs() < hy
            });
        } else {
            let reach = o.r + r;
            mark(
                o.x - reach,
                o.y - reach,
                o.x + reach,
                o.y + reach,
                &|x, y| (x - o.x).hypot(y - o.y) < reach,
            );
        }
    }
    for &(cx, cy, cr) in extra {
        mark(cx - cr, cy - cr, cx + cr, cy + cr, &|x, y| {
            (x - cx).hypot(y - cy) < cr
        });
    }
    grid
}
fn flood(map: &Map, grid: &[bool], from: Point) -> Vec<bool> {
    let n = grid_size(map);
    let start = ((from.y / STEP) as usize) * n + (from.x / STEP) as usize;
    let mut seen = vec![false; n * n];
    assert!(!grid[start], "start {from:?} is blocked");
    seen[start] = true;
    let mut queue = std::collections::VecDeque::from([start]);
    while let Some(c) = queue.pop_front() {
        let (i, j) = (c % n, c / n);
        for (di, dj) in [(1i64, 0i64), (-1, 0), (0, 1), (0, -1)] {
            let (a, b) = (i as i64 + di, j as i64 + dj);
            if a < 0 || b < 0 || a >= n as i64 || b >= n as i64 {
                continue;
            }
            let k = b as usize * n + a as usize;
            if !seen[k] && !grid[k] {
                seen[k] = true;
                queue.push_back(k);
            }
        }
    }
    seen
}
fn reached(map: &Map, seen: &[bool], p: Point) -> bool {
    seen[((p.y / STEP) as usize) * grid_size(map) + (p.x / STEP) as usize]
}
/// A straight walk from a to b with the real collision: true when nothing stops it.
fn walkable(map: &Map, a: Point, b: Point) -> bool {
    let mut p = a;
    let d = a.distance(b);
    map.walk(&mut p, a.direction(b), d, PLAYER_RADIUS);
    p.distance(b) < 0.05
}

// ---- data -------------------------------------------------------------------------------------------------------------------
#[test]
fn the_wyrdwood_is_a_big_forest_zone_with_five_kinds_two_elites_two_hubs_and_a_gate_pair() {
    let w = world();
    let map = &w.maps[WYRD];
    assert_eq!(map.name, "Wyrdwood");
    assert_eq!((map.size, map.levels), (192, Some([20, 30])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert_eq!(map.copies, 0);
    // enemies: every kind at its default level, in the bands the design lists (sleeping ambushers apart)
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    let mut asleep = std::collections::BTreeMap::<&str, usize>::new();
    for (id, spawn) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == WYRD) {
        if spawn.ambush.is_some() {
            *asleep.entry(spawn.kind.as_str()).or_default() += 1;
            let s = &w.slimes[id];
            assert!(
                s.dead && s.state == "waiting" && s.respawn >= 1e8,
                "an ambusher sleeps"
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
            ("boar", 14),
            ("crow", 12),
            ("hrungnir", 1),
            ("oakhorn", 1),
            ("ram", 10),
            ("troll", 12),
            ("weaver", 12)
        ]
    );
    assert_eq!(
        asleep.into_iter().collect::<Vec<_>>(),
        [("crow", 3), ("troll", 2)]
    );
    for (kind, level) in [
        ("boar", 21),
        ("crow", 23),
        ("troll", 25),
        ("weaver", 27),
        ("ram", 29),
        ("oakhorn", 25),
        ("hrungnir", 30),
    ] {
        assert_eq!(Slime::default_level(kind), level, "{kind}");
    }
    assert!(is_elite("oakhorn") && is_elite("hrungnir") && !is_elite("boar"));
    // the first spawns of the old zones keep their ids: the new zone comes last of the file's zones
    assert!(w.spawns.iter().take_while(|s| s.zone < WYRD).count() > 0);
    assert_eq!(
        w.spawns.iter().position(|s| s.zone == WYRD),
        Some(w.spawns.iter().filter(|s| s.zone < WYRD).count())
    );
    // two hubs, both safe ground, each with a travel master; the first is the zone's `city`, the other a camp
    assert_eq!(
        map.city.as_ref().map(|c| (c.x0, c.x1, c.y0, c.y1)),
        Some((9., 57., 131., 172.))
    );
    assert_eq!(map.camps.len(), 1);
    assert!(
        map.in_city(at(33., 150.)) && map.in_city(at(96., 86.)),
        "both plazas are sanctuary"
    );
    assert!(!map.in_city(at(96., 120.)) && !map.in_city(at(60., 150.)));
    for id in ["travel_hollowmoot", "travel_skuldwatch"] {
        assert!(
            map.npcs
                .iter()
                .any(|n| n.id == id && n.travel_stop.is_some()),
            "{id}"
        );
    }
    // the gate pair: Skaldholm's East Gate and the Wyrdwood's way back, each arrival clear of both gates and of enemies
    let east = w.maps[SKALD]
        .portals
        .iter()
        .find(|p| p.id == "wyrd_gate")
        .unwrap();
    let back = map
        .portals
        .iter()
        .find(|p| p.id == "skaldholm_gate")
        .unwrap();
    assert_eq!((east.to, back.to), (WYRD, SKALD));
    assert_eq!((east.tx, east.ty), (map.spawn.x, map.spawn.y));
    assert_eq!((back.tx, back.ty), (147.6, 76.));
    for (arrival, gates) in [
        (at(east.tx, east.ty), &map.portals),
        (at(back.tx, back.ty), &w.maps[SKALD].portals),
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
    let mut spawn_clear = map.spawn;
    map.collide(&mut spawn_clear, PLAYER_RADIUS);
    assert!(
        spawn_clear.distance(map.spawn) < 1e-6,
        "the arrival is free ground"
    );
    for s in w.slimes.iter().filter(|s| s.zone == WYRD) {
        assert!(
            s.point().distance(map.spawn) > 8.,
            "{} is clear of the arrival",
            s.kind
        );
    }
    // a map that is saved with `places`, `bridges` and `camps` stays loadable: the places are what visit objectives name
    assert_eq!(map.places.len(), 6);
    assert!(map.places.iter().all(|p| p.r > 0. && p.x > 0. && p.y > 0.));
}

#[test]
fn the_river_has_one_bridge_and_each_ridge_one_gap_so_the_bands_come_in_order() {
    let w = world();
    let map = &w.maps[WYRD];
    let arrival = map.spawn;
    let bridge_y = 108. + 2.6 * (96f64 / 19.).sin() + 1.6 * (96f64 / 7.3 + 1.).sin();
    let seal = |extra: &[(f64, f64, f64)]| flood(map, &blocked(map, extra), arrival);
    let open = seal(&[]);
    // every person, every live enemy, every place and both gates can be walked to
    // (a cell beside the spot counts: people stand close to walls, and the grid is coarse)
    let near = |seen: &[bool], p: Point| {
        [(0., 0.), (1., 0.), (-1., 0.), (0., 1.), (0., -1.)]
            .iter()
            .any(|(dx, dy)| reached(map, seen, at(p.x + dx, p.y + dy)))
    };
    for n in &map.npcs {
        assert!(near(&open, at(n.x, n.y)), "{}", n.id);
    }
    for s in w.slimes.iter().filter(|s| s.zone == WYRD && !s.dead) {
        assert!(
            reached(map, &open, s.point()),
            "{} at {:?} is unreachable",
            s.kind,
            s.point().x
        );
    }
    for p in &map.places {
        let below = if p.id.contains("beacon") { 2.4 } else { 0. };
        assert!(reached(map, &open, at(p.x, p.y + below)), "{}", p.id);
    }
    // closing the bridge cuts the map in two: Skuldwatch, the heights and every north-bank enemy are cut off
    let no_bridge = seal(&[(96., bridge_y, 3.6)]);
    assert!(
        !reached(map, &no_bridge, at(96., 86.)),
        "Skuldwatch lies beyond the bridge"
    );
    assert!(!reached(map, &no_bridge, at(96., 30.)));
    for s in w.slimes.iter().filter(|s| s.zone == WYRD && !s.dead) {
        assert_eq!(
            reached(map, &no_bridge, s.point()),
            s.y > bridge_y,
            "{} at y {}",
            s.kind,
            s.y
        );
    }
    assert!(
        near(&no_bridge, at(58., 150.)) && near(&no_bridge, at(140., 170.)),
        "the whole south is still open"
    );
    // the first ridge (y 44) has its gap in the east: rams only above it, weavers only below
    let no_gap_a = seal(&[(150., 44., 5.4)]);
    for s in w.slimes.iter().filter(|s| s.zone == WYRD && !s.dead) {
        match s.kind.as_str() {
            "ram" => assert!(
                !reached(map, &no_gap_a, s.point()),
                "ram at {:?}",
                s.point().x
            ),
            "weaver" => assert!(reached(map, &no_gap_a, s.point())),
            _ => {}
        }
    }
    // the second ridge (y 22) has its gap in the west: Hrungnir's court only above it
    let no_gap_b = seal(&[(42., 22., 5.4)]);
    let king = w.slimes.iter().find(|s| s.kind == "hrungnir").unwrap();
    assert!(!reached(map, &no_gap_b, king.point()) && reached(map, &open, king.point()));
    assert!(
        reached(map, &no_gap_b, at(46., 33.4)),
        "the Storm Beacon is on the rams' terrace"
    );
    assert!(
        !reached(map, &no_gap_a, at(46., 33.4)),
        "and the terrace needs the first gap"
    );
}

#[test]
fn every_wyrdwood_monster_has_its_own_stats_attacks_materials_and_rewards() {
    // (kind, hp, damage, gold) at the default level
    for (kind, hp, damage, gold, material_id) in [
        ("boar", 5600., 165., 270, "rotfang_tusk"),
        ("crow", 4300., 150., 290, "gallows_feather"),
        ("troll", 9500., 210., 330, "mosshide_scrap"),
        ("weaver", 7600., 190., 360, "fate_thread"),
        ("ram", 11500., 255., 400, "stormram_horn"),
    ] {
        let spawn = SlimeSpawn {
            ambush: None,
            x: 5.,
            y: 5.,
            kind: kind.into(),
            zone: WYRD,
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
        // a real kill pays that level's XP and gold, and drops the material, all in the Wyrdwood
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.players.get_mut(&1).unwrap().character.zone = WYRD;
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == WYRD && s.kind == kind && !s.dead)
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
        assert!(w.drops.iter().all(|d| d.zone == WYRD));
    }
    // how each one fights: the crow shoots two feathers and backs away, the weaver three thread bolts, the troll pounds the ground
    let crow = Slime::ranged("crow").unwrap();
    assert_eq!((crow.shots, crow.range), (2, 11.));
    let weaver = Slime::ranged("weaver").unwrap();
    assert_eq!((weaver.shots, weaver.range), (3, 11.));
    assert!(
        Slime::ranged("boar").is_none()
            && Slime::ranged("ram").is_none()
            && Slime::ranged("troll").is_none()
    );
    assert_eq!(Slime::slam_radius("troll"), 2.6);
    assert!(Slime::slam_radius("boar") == 0. && Slime::slam_radius("ram") == 0.);
    // the boar and the ram charge faster than anything else of the zone
    let charge = |k: &str| Slime::attack_profile(k).2;
    assert!(charge("ram") > charge("boar") && charge("boar") > charge("troll"));
    // Oakhorn charges after a full second of warning; Hrungnir shoots three bolts from afar and pounds up close
    assert_eq!(Slime::attack_profile("oakhorn").0, 1.);
    assert_eq!(Slime::ranged("hrungnir").map(|r| r.shots), Some(3));
    assert_eq!(
        (
            Slime::slam_radius("hrungnir"),
            Slime::melee_inside("hrungnir")
        ),
        (3.6, 4.5)
    );
    assert_eq!(material("oakhorn"), "oakhorn_crown");
    assert_eq!(material("hrungnir"), "stormheart_shard");
}

// ---- the two hubs and their quests ------------------------------------------------------------------------------------------
#[test]
fn both_hubs_have_valid_connected_quests_with_every_kind_of_objective_across_levels_twenty_to_thirty()
 {
    let w = world();
    let map = &w.maps[WYRD];
    assert_eq!(
        map.npcs.len(),
        17,
        "7 + 7 people, the stranded Eydis and two travel masters"
    );
    assert!(map.quests.len() >= 24, "{} quests", map.quests.len());
    let mut kinds = std::collections::BTreeSet::new();
    let mut levels = std::collections::BTreeSet::new();
    let mut roots = vec![];
    for q in &map.quests {
        assert!(
            q.id.starts_with("wyrd_") && q.npc.starts_with("wyrd_"),
            "{}",
            q.id
        );
        assert!((20..=30).contains(&q.level), "{} level {}", q.id, q.level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
        assert!(q.reward_gold >= 400, "{}", q.id);
        levels.insert(q.level);
        assert!(
            map.npcs.iter().any(|n| n.id == q.npc),
            "{} has a giver",
            q.id
        );
        if q.requires.is_none() && q.auto_level.is_none() {
            roots.push(q.id.clone());
        }
        if let Some(id) = &q.requires {
            assert!(
                map.quests.iter().any(|p| &p.id == id),
                "{} needs {id}",
                q.id
            );
        }
        for o in &q.objectives {
            kinds.insert(o.kind.clone());
            match o.kind.as_str() {
                "kill" => assert!(
                    o.target == "any"
                        || w.spawns
                            .iter()
                            .any(|s| s.zone == WYRD && s.kind == o.target),
                    "{} hunts {}",
                    q.id,
                    o.target
                ),
                "talk" => assert!(
                    map.npcs.iter().any(|n| n.id == o.target),
                    "{} talks to {}",
                    q.id,
                    o.target
                ),
                "bring" => assert_eq!(
                    item(&o.target).map(|i| i.kind.as_str()),
                    Some("material"),
                    "{}",
                    q.id
                ),
                "visit" => assert!(
                    map.places.iter().any(|p| p.id == o.target),
                    "{} visits {}",
                    q.id,
                    o.target
                ),
                "escort" => assert!(npc(&w, &o.target).escort.is_some(), "{}", q.id),
                "reach" => assert_eq!(o.target, "Wyrdwood"),
                other => panic!("{} has an unknown objective {other}", q.id),
            }
        }
    }
    assert_eq!(
        roots,
        ["wyrd_welcome"],
        "one root: Skuldwatch's chain starts after the seal is carried"
    );
    assert_eq!(
        kinds.into_iter().collect::<Vec<_>>(),
        ["bring", "escort", "kill", "reach", "talk", "visit"]
    );
    assert_eq!((levels.first(), levels.last()), (Some(&20), Some(&30)));
    assert!(
        levels.len() >= 9,
        "every level from 20 to 30 has work: {levels:?}"
    );
    assert_eq!(map.quests.iter().filter(|q| q.repeatable).count(), 4);
    // the two elite quests: group-credited, a guaranteed gear reward that is not in the ordinary drop pool of new items
    let oak = quest(&w, "wyrd_oakhorn");
    let storm = quest(&w, "wyrd_hrungnir");
    assert!(oak.group && storm.group);
    assert_eq!((oak.recommended_players, storm.recommended_players), (3, 5));
    assert_eq!(
        item(oak.reward_item.as_deref().unwrap()).unwrap().rarity,
        "rare"
    );
    assert_eq!(
        item(storm.reward_item.as_deref().unwrap()).unwrap().rarity,
        "epic"
    );
    for q in [&oak, &storm] {
        let reward = item(q.reward_item.as_deref().unwrap()).unwrap();
        assert!(
            reward.class.is_none() && reward.required_level == 20,
            "usable by every class"
        );
        assert!(q.objectives.len() == 1 && q.objectives[0].kind == "kill");
    }
    assert_eq!(
        (oak.npc.as_str(), storm.npc.as_str()),
        ("wyrd_warden", "wyrd_captain")
    );
    // the second hub's chain starts after the message from the first
    assert_eq!(
        quest(&w, "wyrd_watch_welcome").requires.as_deref(),
        Some("wyrd_seal")
    );
    assert_eq!(quest(&w, "wyrd_seal").objectives[0].target, "wyrd_captain");
}

#[test]
fn the_wyrdwood_progression_quest_comes_at_level_twenty_two_and_completes_on_arrival() {
    let w = world();
    let q = quest(&w, "wyrd_onward");
    assert_eq!((q.auto_level, q.level), (Some(22), 22));
    assert_eq!(q.npc, "wyrd_warden");
    let mut c = Character::mercenary(Class::Warrior, 21, "Walker");
    assert!(
        sync_progression(&mut c, &w.maps).is_empty()
            || !c.quests.iter().any(|p| p.id == "wyrd_onward")
    );
    c.level = 22;
    let arrived = sync_progression(&mut c, &w.maps);
    assert!(arrived.iter().any(|t| t == "The Road East"), "{arrived:?}");
    assert_eq!(
        c.quests
            .iter()
            .find(|p| p.id == "wyrd_onward")
            .unwrap()
            .counts,
        vec![0]
    );
    c.zone = WYRD;
    sync_progression(&mut c, &w.maps);
    assert_eq!(
        c.quests
            .iter()
            .find(|p| p.id == "wyrd_onward")
            .unwrap()
            .counts,
        vec![1]
    );
}

#[test]
fn visit_objectives_complete_only_inside_the_named_place_for_an_accepted_quest() {
    let w = world();
    let q = quest(&w, "wyrd_moonpetal");
    let glade = w.maps[WYRD]
        .places
        .iter()
        .find(|p| p.id == "wyrd_glade")
        .unwrap()
        .clone();
    let mut c = Character::mercenary(Class::Warrior, 24, "Herbalist");
    c.zone = WYRD;
    // not accepted: standing there does nothing
    (c.x, c.y) = (glade.x, glade.y);
    assert!(sync_visits(&mut c, &w.maps).is_empty());
    c.quests.push(QuestProgress {
        id: q.id.clone(),
        counts: vec![0, 0],
        ..Default::default()
    });
    // accepted, but a few steps outside the radius
    (c.x, c.y) = (glade.x + glade.r + 0.5, glade.y);
    assert!(sync_visits(&mut c, &w.maps).is_empty());
    assert_eq!(c.quests[0].counts, vec![0, 0]);
    // inside the radius: the first objective is done once, the kill objective is untouched
    (c.x, c.y) = (glade.x + glade.r - 0.5, glade.y);
    assert_eq!(
        sync_visits(&mut c, &w.maps),
        vec!["Moonpetal Glade".to_owned()]
    );
    assert_eq!(c.quests[0].counts, vec![1, 0]);
    assert!(sync_visits(&mut c, &w.maps).is_empty(), "reported once");
    // the same place in another zone is a different place
    let mut d = Character::mercenary(Class::Warrior, 24, "Elsewhere");
    d.zone = 1;
    (d.x, d.y) = (glade.x, glade.y);
    d.quests.push(QuestProgress {
        id: q.id,
        counts: vec![0, 0],
        ..Default::default()
    });
    assert!(sync_visits(&mut d, &w.maps).is_empty());
}

#[test]
fn skaldholm_flies_to_both_wyrdwood_hubs_through_the_east_gate_for_twenty_gold_a_leg() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let skald = w.maps[SKALD]
        .npcs
        .iter()
        .find(|n| n.id == "travel_skaldholm")
        .unwrap()
        .clone();
    assert!(skald.travel_links.iter().any(|l| l == "travel_hollowmoot"));
    assert_eq!(
        npc(&w, "travel_hollowmoot").travel_links,
        ["travel_skaldholm", "travel_skuldwatch"]
    );
    assert_eq!(
        npc(&w, "travel_skuldwatch").travel_links,
        ["travel_hollowmoot"]
    );
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = SKALD;
        c.x = skald.x;
        c.y = skald.y + 1.;
        c.gold = 100;
        c.travel_stops = vec!["travel_skaldholm".into(), "travel_hollowmoot".into()];
    }
    // the second stop is not discovered: the whole trip is refused and costs nothing
    w.time += 1.;
    w.interact(1, "travel_skaldholm", Some("spark:travel_skuldwatch"));
    assert_eq!(w.players[&1].character.gold, 100);
    assert!(w.players[&1].character.spark_travel.is_none());
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .travel_stops
        .push("travel_skuldwatch".into());
    w.time += 1.;
    drain(&mut rx);
    w.interact(1, "travel_skaldholm", Some("spark:travel_skuldwatch"));
    let flight = w.players[&1]
        .character
        .spark_travel
        .clone()
        .expect("the flight starts");
    assert_eq!(
        w.players[&1].character.gold, 60,
        "two legs: Skaldholm - Hollowmoot - Skuldwatch"
    );
    assert_eq!(
        flight.stops,
        ["travel_skaldholm", "travel_hollowmoot", "travel_skuldwatch"]
    );
    let east = w.maps[SKALD]
        .portals
        .iter()
        .find(|p| p.id == "wyrd_gate")
        .unwrap()
        .clone();
    assert!(
        flight
            .points
            .iter()
            .any(|p| p.zone == SKALD && (p.x, p.y) == (east.x, east.y)),
        "it leaves through the East Gate"
    );
    assert!(
        flight
            .points
            .iter()
            .any(|p| p.zone == WYRD && (p.x, p.y) == (east.tx, east.ty)),
        "and lands at the Wyrdwood arrival"
    );
    for _ in 0..(400. / TICK) as usize {
        w.step();
        if w.players[&1].character.spark_travel.is_none() {
            break;
        }
    }
    let c = &w.players[&1].character;
    assert!(c.spark_travel.is_none());
    let stop = npc(&w, "travel_skuldwatch");
    assert_eq!(c.zone, WYRD);
    assert!(
        c.point().distance(at(stop.x, stop.y)) < 0.5,
        "landed at Skuldwatch's master"
    );
}

#[test]
fn skuldwatch_is_a_sanctuary_like_hollowmoot() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (x, y) in [(96., 86.), (33., 150.)] {
        place(&mut w, 1, WYRD, at(x, y));
        w.time += 10.;
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 5000., at(x, y));
        assert_eq!(
            w.players[&1].character.hp, before,
            "no damage inside the hub at {x}"
        );
    }
    place(&mut w, 1, WYRD, at(96., 130.));
    w.time += 10.;
    let before = w.players[&1].character.hp;
    w.hurt_player(1, 5000., at(96., 130.));
    assert!(w.players[&1].character.hp < before);
}

#[test]
fn a_hirer_rents_two_fighters_for_the_oakhorn_and_four_for_hrungnir() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    calm(&mut w);
    let mercs = |w: &World| w.players.values().filter(|p| p.merc.is_some()).count();
    // the Oakhorn's giver is the Moot-Warden; she wants a party of three
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 25;
        c.gold = 2000;
        for id in ["wyrd_crows", "wyrd_boars"] {
            c.quests.push(QuestProgress {
                id: id.into(),
                claimed: true,
                completions: 1,
                ..Default::default()
            });
        }
    }
    place(&mut w, 1, WYRD, at(33., 141.5));
    w.time += 1.;
    w.interact(1, "wyrd_warden", Some("merc_warrior"));
    assert_eq!(mercs(&w), 0, "the quest must be taken first");
    w.time += 1.;
    w.interact(1, "wyrd_warden", Some("quest:accept:wyrd_oakhorn"));
    for class in ["warrior", "priest", "mage"] {
        w.time += 1.;
        w.interact(1, "wyrd_warden", Some(&format!("merc_{class}")));
    }
    assert_eq!(mercs(&w), 2, "a party of three: the hero and two fighters");
    assert_eq!(w.players[&1].character.gold, 2000 - 2 * 250);
}

#[test]
fn oakhorn_credits_three_nearby_contributors_pays_a_blue_item_and_resets_whole() {
    let mut w = world();
    let id = w.slimes.iter().position(|s| s.kind == "oakhorn").unwrap();
    let point = w.slimes[id].point();
    let q = quest(&w, "wyrd_oakhorn");
    let reward = q.reward_item.clone().unwrap();
    // sessions 1-3 fight and stand close; 4 fights from far away; 5 never hits
    let _rx: Vec<_> = (1..=5).map(|s| join(&mut w, s, Class::Warrior)).collect();
    for session in 1..=5 {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.zone = WYRD;
        c.x = point.x + 2.;
        c.y = point.y;
        for pre in ["wyrd_crows", "wyrd_boars"] {
            c.quests.push(QuestProgress {
                id: pre.into(),
                claimed: true,
                completions: 1,
                ..Default::default()
            });
        }
        assert!(quest_action(c, &q, "accept").2);
        if session != 5 {
            w.hit_slime(id, session, 1., false);
        }
    }
    w.players.get_mut(&4).unwrap().character.x = point.x - 20.;
    w.hit_slime(id, 1, 1e9, false);
    for session in 1..=5 {
        let c = &w.players[&session].character;
        let counts = &c
            .quests
            .iter()
            .find(|p| p.id == "wyrd_oakhorn")
            .unwrap()
            .counts;
        assert_eq!(counts, &vec![u32::from(session <= 3)], "session {session}");
    }
    assert_eq!(w.slimes[id].respawn, 180.);
    assert!(w.slimes[id].elite);
    for session in 1..=3 {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        let (text, _, changed) = quest_action(c, &q, "claim");
        assert!(changed, "{text}");
        assert_eq!(c.quantity(&reward), 1);
    }
    // evading restores every point of health and forgets who helped
    w.slimes[id].respawn = TICK;
    w.update_slime(id);
    w.hit_slime(id, 1, 5000., false);
    assert_eq!(w.slimes[id].contributors.len(), 1);
    w.slimes[id].state = "return".into();
    w.update_slime(id);
    assert!(w.slimes[id].contributors.is_empty());
    assert_eq!(w.slimes[id].hp, w.slimes[id].max_hp);
}

#[test]
fn hrungnir_credits_five_pays_an_epic_necklace_and_returns_in_five_minutes() {
    let mut w = world();
    let id = w.slimes.iter().position(|s| s.kind == "hrungnir").unwrap();
    let point = w.slimes[id].point();
    let q = quest(&w, "wyrd_hrungnir");
    let reward = q.reward_item.clone().unwrap();
    let _rx: Vec<_> = (1..=6).map(|s| join(&mut w, s, Class::Warrior)).collect();
    for session in 1..=6 {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.zone = WYRD;
        c.x = point.x + 2.;
        c.y = point.y + 3.;
        c.quests.push(QuestProgress {
            id: "wyrd_stones".into(),
            claimed: true,
            completions: 1,
            ..Default::default()
        });
        assert!(quest_action(c, &q, "accept").2);
        w.hit_slime(id, session, 1., false);
    }
    w.players.get_mut(&6).unwrap().character.x = point.x - 20.;
    w.hit_slime(id, 1, 1e9, false);
    let credited: Vec<u32> = (1..=6)
        .map(|s| {
            w.players[&s]
                .character
                .quests
                .iter()
                .find(|p| p.id == "wyrd_hrungnir")
                .unwrap()
                .counts[0]
        })
        .collect();
    assert_eq!(credited, [1, 1, 1, 1, 1, 0]);
    assert_eq!(w.slimes[id].respawn, 300.);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let (text, _, changed) = quest_action(c, &q, "claim");
    assert!(changed, "{text}");
    assert_eq!(c.quantity(&reward), 1);
    assert_eq!(c.gold, 3000);
}

// ---- the escort ---------------------------------------------------------------------------------------------------------------
fn escort_world() -> (World, mpsc::Receiver<Value>) {
    let mut w = world();
    let rx = join(&mut w, 1, Class::Warrior);
    calm(&mut w);
    let eydis = npc(&w, "wyrd_eydis");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 26;
    c.zone = WYRD;
    c.x = eydis.x;
    c.y = eydis.y + 1.;
    c.hp = c.max_hp();
    c.quests.push(QuestProgress {
        id: "wyrd_watch_welcome".into(),
        claimed: true,
        completions: 1,
        ..Default::default()
    });
    (w, rx)
}
fn take_escort_quest(w: &mut World) {
    let q = quest(w, "wyrd_escort");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    assert!(quest_action(c, &q, "accept").2);
}
fn start_escort(w: &mut World) -> u64 {
    w.time += 1.;
    w.interact(1, "wyrd_eydis", None);
    let owner = w.players[&1].character.id.clone();
    w.escort_of(&owner).expect("Eydis joins")
}
fn route_of(w: &World) -> Vec<Point> {
    npc(w, "wyrd_eydis")
        .escort
        .unwrap()
        .route
        .iter()
        .map(|p| at(p[0], p[1]))
        .collect()
}
/// The hero keeps pace with the escort (as a real player would) and the world runs for `seconds`.
fn walk_together(w: &mut World, escort: u64, seconds: f64) {
    for _ in 0..(seconds / TICK) as usize {
        if let Some(e) = w.players.get(&escort) {
            let there = e.character.point();
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = there.x + 1.;
            c.y = there.y + 1.;
        }
        w.step();
        w.players.get_mut(&1).unwrap().last_hurt = w.time;
    }
}

#[test]
fn the_escort_route_is_clear_ground_from_the_mill_to_skuldwatch_and_the_ambushers_sleep_beside_it()
{
    let w = world();
    let eydis = npc(&w, "wyrd_eydis");
    let def = eydis.escort.clone().unwrap();
    let map = &w.maps[WYRD];
    assert_eq!(
        (def.quest.as_str(), def.class.as_str(), def.level),
        ("wyrd_escort", "mage", 26)
    );
    assert!(def.speed > 2. && def.speed < 4., "about half a hero's pace");
    let route: Vec<Point> = std::iter::once(at(eydis.x, eydis.y))
        .chain(def.route.iter().map(|p| at(p[0], p[1])))
        .collect();
    for pair in route.windows(2) {
        assert!(
            walkable(map, pair[0], pair[1]),
            "blocked between {:?} and {:?}",
            (pair[0].x, pair[0].y),
            (pair[1].x, pair[1].y)
        );
        assert!(
            pair[0].distance(pair[1]) <= 40.,
            "waypoints are never far apart"
        );
    }
    let end = route.last().unwrap();
    assert!(
        end.x > 67. && end.x < 125. && end.y > 75. && end.y < 97.,
        "the walk ends inside Skuldwatch"
    );
    // two ambushes: crows near the foot of the gallows hill, trolls at the bridge
    assert_eq!(
        def.ambush
            .iter()
            .map(|a| a.tag.as_str())
            .collect::<Vec<_>>(),
        ["wyrd_eydis#crow", "wyrd_eydis#troll"]
    );
    for a in &def.ambush {
        let slots: Vec<_> = w
            .spawns
            .iter()
            .enumerate()
            .filter(|(_, s)| s.ambush.as_deref() == Some(a.tag.as_str()))
            .collect();
        assert!(slots.len() >= 2);
        for (id, s) in slots {
            assert!(w.slimes[id].dead, "asleep");
            assert!(
                at(s.x, s.y).distance(at(a.at[0], a.at[1])) < a.r + 6.,
                "{} slot is near its trigger",
                a.tag
            );
        }
    }
}

#[test]
fn speaking_to_eydis_starts_the_escort_only_for_a_hero_who_took_the_quest() {
    let (mut w, mut rx) = escort_world();
    let owner = w.players[&1].character.id.clone();
    w.time += 1.;
    w.interact(1, "wyrd_eydis", None);
    assert!(w.escort_of(&owner).is_none(), "no quest, no escort");
    take_escort_quest(&mut w);
    // too far away to be heard
    place(&mut w, 1, WYRD, at(100., 100.));
    w.time += 1.;
    w.interact(1, "wyrd_eydis", None);
    assert!(w.escort_of(&owner).is_none());
    let eydis = npc(&w, "wyrd_eydis");
    place(&mut w, 1, WYRD, at(eydis.x, eydis.y + 1.));
    drain(&mut rx);
    let session = start_escort(&mut w);
    assert!(
        session >= mercs::MERC_BASE,
        "it lives among the mercenary sessions"
    );
    let e = &w.players[&session];
    assert_eq!(e.character.look.name, "Eydis Mapwright");
    assert_eq!(e.character.look.class, Class::Mage);
    assert_eq!(e.character.look.gender, Gender::Female);
    assert_eq!(e.merc.as_deref(), Some(owner.as_str()));
    assert!(e.character.hp > 400., "a tough walker: {}", e.character.hp);
    assert_eq!(e.character.zone, WYRD);
    let told = lines(&mut rx);
    assert!(
        told.iter().any(|t| t.contains("Eydis Mapwright joins you")),
        "{told:?}"
    );
    // she is no human online, no party member, never saved, and clients are told what she is
    assert_eq!(w.humans_online(), 1);
    assert_eq!(w.party_mates(&owner).len(), 1);
    assert_eq!(
        w.players
            .values()
            .filter(|p| p.merc.is_some() && p.escort.is_none())
            .count(),
        0,
        "she is not a hired fighter"
    );
    let snap = w.snapshot_for(WYRD);
    let seen = snap["players"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["escort"].is_object())
        .expect("in the snapshot");
    assert_eq!(seen["escort"]["npc"], "wyrd_eydis");
    assert_eq!(seen["escort"]["owner"], owner.as_str());
    w.save();
    assert!(
        w.pending_saves.is_empty(),
        "saving works and never includes her"
    );
    // dismissing hired fighters never sends her away
    assert!(w.dismiss_mercenaries(1).is_err(), "she is not a mercenary");
    assert_eq!(w.players.values().filter(|p| p.escort.is_some()).count(), 1);
    // asking again changes nothing
    w.time += 1.;
    w.interact(1, "wyrd_eydis", None);
    assert_eq!(w.players.values().filter(|p| p.escort.is_some()).count(), 1);
    assert!(
        lines(&mut rx)
            .iter()
            .any(|t| t.contains("already walking with you"))
    );
}

#[test]
fn eydis_walks_the_route_waits_for_her_hero_and_stops_when_an_enemy_fights_her() {
    let (mut w, _rx) = escort_world();
    take_escort_quest(&mut w);
    let session = start_escort(&mut w);
    let start = w.players[&session].character.point();
    // far ahead of her hero she waits
    place(&mut w, 1, WYRD, at(start.x - 30., start.y));
    for _ in 0..40 {
        w.step();
    }
    assert!(
        w.players[&session].character.point().distance(start) < 0.5,
        "she waits for her hero"
    );
    // beside her she walks, at about her own pace
    place(&mut w, 1, WYRD, at(start.x + 1., start.y));
    walk_together(&mut w, session, 10.);
    let moved = w.players[&session].character.point().distance(start);
    assert!(
        moved > 15. && moved < 30.,
        "10 s of walking at 2.5 per second: {moved}"
    );
    // an enemy who has taken her as its target stops her where she stands
    let id = w
        .slimes
        .iter()
        .position(|s| s.zone == WYRD && s.kind == "boar")
        .unwrap();
    let here = w.players[&session].character.point();
    w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), 21);
    w.slimes[id].x = here.x + 1.5;
    w.slimes[id].y = here.y;
    w.slimes[id].target = Some(session);
    w.slimes[id].state = "chase".into();
    let frozen = w.players[&session].character.point();
    for _ in 0..30 {
        let there = w.players[&session].character.point();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = there.x - 1.;
        c.y = there.y;
        w.slimes[id].atk_cd = 99.;
        w.slimes[id].target = Some(session);
        w.step();
        w.slimes[id].state = "chase".into();
    }
    assert!(
        w.players[&session].character.point().distance(frozen) < 0.8,
        "she holds still while she is fought"
    );
    w.slimes[id].dead = true;
    walk_together(&mut w, session, 3.);
    assert!(
        w.players[&session].character.point().distance(frozen) > 3.,
        "and walks on once it is gone"
    );
}

#[test]
fn enemies_pick_the_escort_as_a_target_and_hurt_her() {
    let (mut w, _rx) = escort_world();
    take_escort_quest(&mut w);
    let session = start_escort(&mut w);
    let here = w.players[&session].character.point();
    place(&mut w, 1, WYRD, at(here.x - 40., here.y));
    let id = w
        .slimes
        .iter()
        .position(|s| s.zone == WYRD && s.kind == "boar")
        .unwrap();
    w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), 21);
    w.slimes[id].x = here.x + 4.;
    w.slimes[id].y = here.y;
    (w.slimes[id].hx, w.slimes[id].hy) = (w.slimes[id].x, w.slimes[id].y);
    w.update_slime(id);
    assert_eq!(
        w.slimes[id].target,
        Some(session),
        "the nearest hero in sight is Eydis"
    );
    let hp = w.players[&session].character.hp;
    w.time += 5.;
    w.hurt_player_by(session, 400., here, "boar", 21);
    assert!(w.players[&session].character.hp < hp);
}

#[test]
fn reaching_skuldwatch_completes_the_objective_wakes_the_ambushes_on_the_way_and_pays_at_the_loremaster()
 {
    let (mut w, mut rx) = escort_world();
    take_escort_quest(&mut w);
    let session = start_escort(&mut w);
    let route = route_of(&w);
    let total: f64 = route.windows(2).map(|p| p[0].distance(p[1])).sum();
    let mut woke = std::collections::BTreeSet::new();
    let mut ticks = 0;
    while w
        .players
        .get(&session)
        .is_some_and(|e| !e.escort.as_ref().unwrap().arrived())
        && ticks < 4000
    {
        walk_together(&mut w, session, TICK);
        ticks += 1;
        for (id, s) in w.spawns.iter().enumerate() {
            if let Some(tag) = &s.ambush
                && !w.slimes[id].dead
            {
                woke.insert(tag.clone());
                // an ambusher is sent at the escort; keep the test about the walk by dropping it at once
                assert_eq!(w.slimes[id].target, Some(session), "{tag} goes for Eydis");
                w.slimes[id].dead = true;
                w.slimes[id].respawn = 1e9;
            }
        }
    }
    assert!(
        ticks as f64 * TICK > total / 3.2 && ticks < 4000,
        "the walk took {} s for {total:.0} tiles",
        ticks as f64 * TICK
    );
    assert_eq!(
        woke.into_iter().collect::<Vec<_>>(),
        ["wyrd_eydis#crow", "wyrd_eydis#troll"],
        "both ambushes woke on the way"
    );
    let c = &w.players[&1].character;
    assert_eq!(
        c.quests
            .iter()
            .find(|p| p.id == "wyrd_escort")
            .unwrap()
            .counts,
        vec![1]
    );
    assert!(
        lines(&mut rx)
            .iter()
            .any(|t| t.contains("Eydis Mapwright is safe"))
    );
    // she stays three seconds, then is gone, and every sleeper is asleep again
    walk_together(&mut w, session, 4.);
    assert!(!w.players.contains_key(&session));
    assert!(
        w.spawns
            .iter()
            .enumerate()
            .all(|(i, s)| s.ambush.is_none() || w.slimes[i].dead)
    );
    // the quest is ready: only Vigdis pays, once
    let q = quest(&w, "wyrd_escort");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let before = (c.gold, c.level, c.xp);
    let (text, _, changed) = quest_action(c, &q, "claim");
    assert!(changed, "{text}");
    assert_eq!(c.gold, before.0 + q.reward_gold);
    assert!(!quest_action(c, &q, "claim").2);
    assert_eq!(q.npc, "wyrd_loremaster");
}

#[test]
fn the_escort_quest_fails_when_eydis_or_her_hero_falls_or_is_left_behind_and_can_be_started_again()
{
    for how in ["eydis", "hero", "left behind", "logout"] {
        let (mut w, mut rx) = escort_world();
        take_escort_quest(&mut w);
        let session = start_escort(&mut w);
        walk_together(&mut w, session, 4.);
        drain(&mut rx);
        match how {
            "eydis" => w.players.get_mut(&session).unwrap().character.hp = 0.,
            "hero" => w.players.get_mut(&1).unwrap().character.hp = 0.,
            "left behind" => {
                let there = w.players[&session].character.point();
                place(&mut w, 1, WYRD, at(there.x, there.y - 55.));
            }
            _ => {}
        }
        if how == "logout" {
            w.leave(1);
        }
        // a fall ends the journey at once; being left behind takes twenty seconds
        let patience = if matches!(how, "eydis" | "hero") {
            1.
        } else {
            25.
        };
        for _ in 0..(patience / TICK) as usize {
            let now = w.time;
            if let Some(p) = w.players.get_mut(&1) {
                p.last_hurt = now;
            }
            w.step();
            if !w.players.contains_key(&session) {
                break;
            }
        }
        assert!(!w.players.contains_key(&session), "{how}: she is gone");
        assert!(
            w.spawns
                .iter()
                .enumerate()
                .all(|(i, s)| s.ambush.is_none() || w.slimes[i].dead),
            "{how}: the ambushers sleep"
        );
        if how == "logout" {
            continue;
        }
        let told = lines(&mut rx);
        assert!(
            told.iter()
                .any(|t| t.starts_with("Quest failed: Safe Passage")),
            "{how}: {told:?}"
        );
        let c = &w.players[&1].character;
        let progress = c.quests.iter().find(|p| p.id == "wyrd_escort").unwrap();
        assert_eq!(
            (progress.counts.clone(), progress.claimed),
            (vec![0], false),
            "{how}: the objective is open again"
        );
        // she is still at the mill for another try
        let eydis = npc(&w, "wyrd_eydis");
        place(&mut w, 1, WYRD, at(eydis.x, eydis.y + 1.));
        w.time += 1.;
        w.interact(1, "wyrd_eydis", None);
        let owner = w.players[&1].character.id.clone();
        assert!(w.escort_of(&owner).is_some(), "{how}: a second try");
    }
}

#[test]
fn a_finished_escort_cannot_be_started_again_and_two_heroes_each_get_their_own() {
    let (mut w, _rx) = escort_world();
    let _rx2 = join(&mut w, 2, Class::Mage);
    let eydis = npc(&w, "wyrd_eydis");
    {
        let c = &mut w.players.get_mut(&2).unwrap().character;
        c.level = 26;
        c.zone = WYRD;
        c.x = eydis.x;
        c.y = eydis.y + 1.;
        c.quests.push(QuestProgress {
            id: "wyrd_watch_welcome".into(),
            claimed: true,
            completions: 1,
            ..Default::default()
        });
    }
    take_escort_quest(&mut w);
    let q = quest(&w, "wyrd_escort");
    assert!(quest_action(&mut w.players.get_mut(&2).unwrap().character, &q, "accept").2);
    let first = start_escort(&mut w);
    w.time += 1.;
    w.interact(2, "wyrd_eydis", None);
    let second_owner = w.players[&2].character.id.clone();
    let second = w
        .escort_of(&second_owner)
        .expect("the second hero has their own Eydis");
    assert_ne!(first, second);
    assert_eq!(w.players.values().filter(|p| p.escort.is_some()).count(), 2);
    // the first hero finishes (debug-complete the objective), then speaking again says she is safe
    quest_progress(
        &mut w.players.get_mut(&1).unwrap().character,
        &w.maps[WYRD].quests,
        "escort",
        "wyrd_eydis",
    );
    w.remove_escort(first);
    w.time += 1.;
    w.interact(1, "wyrd_eydis", None);
    let owner = w.players[&1].character.id.clone();
    assert!(
        w.escort_of(&owner).is_none(),
        "an escort that is done is not repeated"
    );
}

#[test]
fn an_escort_never_takes_a_portal_even_when_walked_onto_one() {
    let (mut w, _rx) = escort_world();
    take_escort_quest(&mut w);
    let session = start_escort(&mut w);
    let gate = w.maps[WYRD].portals[0].clone();
    {
        let e = &mut w.players.get_mut(&session).unwrap();
        e.character.x = gate.x + 0.2;
        e.character.y = gate.y;
    }
    w.players.get_mut(&session).unwrap().portal_at = -99.;
    w.use_portal(session);
    assert_eq!(w.players[&session].character.zone, WYRD);
}

// ---- balance: a hirer plus hired fighters against each elite ------------------------------------------------------------------
struct Fight {
    won: bool,
    seconds: f64,
    deaths: u32,
    boss_left: f64,
}
/// A trained hero of `level` hires `classes` at `giver` for `quest_id` and fights `kind` with the real skills, potions and AI
/// mercenaries. Returns how it went. (Heroes do not path-find in tests, so everyone is staged at the boss.)
fn fight(
    kind: &str,
    quest_id: &str,
    giver: &str,
    pre: &str,
    level: u32,
    classes: &[&str],
    limit: f64,
) -> Fight {
    let mut w = world();
    w.rng = 7;
    let mut rx = join(&mut w, 1, Class::Warrior);
    let id = w.slimes.iter().position(|s| s.kind == kind).unwrap();
    let point = w.slimes[id].point();
    for s in w.slimes.iter_mut().filter(|s| s.id != id) {
        s.dead = true;
        s.respawn = 1e9;
    }
    {
        let points = (level - 1) * 3;
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = level;
        c.gold = 9000;
        c.attributes.stamina = points / 5;
        c.attributes.accuracy = 7;
        c.attributes.strength = points - points / 5 - 7;
        c.add_item("health_potion", 1);
        for p in pre.split(',') {
            c.quests.push(QuestProgress {
                id: p.into(),
                claimed: true,
                completions: 1,
                ..Default::default()
            });
        }
    }
    let giver_at = npc(&w, giver);
    place(&mut w, 1, WYRD, at(giver_at.x, giver_at.y + 1.));
    w.time += 0.6;
    w.interact(1, giver, Some(&format!("quest:accept:{quest_id}")));
    for class in classes {
        w.time += 0.6;
        w.interact(1, giver, Some(&format!("merc_{class}")));
    }
    drain(&mut rx);
    assert_eq!(
        w.players.values().filter(|p| p.merc.is_some()).count(),
        classes.len()
    );
    place(&mut w, 1, WYRD, at(point.x - 3., point.y));
    for (i, p) in w
        .players
        .values_mut()
        .filter(|p| p.merc.is_some())
        .enumerate()
    {
        p.character.zone = WYRD;
        p.character.x = point.x + 2. + i as f64;
        p.character.y = point.y + 2.;
    }
    w.message(1, ClientMessage::Target { id });
    let mut deaths = 0;
    let mut elapsed = 0.;
    for _ in 0..(limit / TICK) as usize {
        if w.players[&1].character.hp > 0. {
            let aim = w.players[&1]
                .character
                .point()
                .direction(w.slimes[id].point());
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
        } else {
            // a fallen hero is put back at the fight (test heroes do not path-find)
            deaths += 1;
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.hp = c.max_hp();
            c.x = point.x - 3.;
            c.y = point.y;
            w.players.get_mut(&1).unwrap().dead_time = 0.;
        }
        w.step();
        elapsed += TICK;
        drain(&mut rx);
        for (_, p) in w.players.iter_mut().filter(|(_, p)| p.merc.is_some()) {
            if p.character.hp <= 0. {
                deaths += 1;
                p.character.hp = p.character.max_hp();
                p.character.x = point.x + 3.;
                p.character.y = point.y + 3.;
                p.dead_time = 0.;
            }
        }
        if w.slimes[id].dead {
            break;
        }
    }
    Fight {
        won: w.slimes[id].dead,
        seconds: elapsed,
        deaths,
        boss_left: w.slimes[id].hp / w.slimes[id].max_hp,
    }
}

#[test]
#[ignore = "balance probe: prints how parties fare against the two elites (cargo test --release wyrd_balance_probe -- --ignored --nocapture)"]
fn wyrd_balance_probe() {
    let report = |label: &str, f: Fight| {
        eprintln!(
            "{label}: won {} in {:.0} s, deaths {}, boss left {:.0}%",
            f.won,
            f.seconds,
            f.deaths,
            f.boss_left * 100.
        )
    };
    for classes in [
        vec![],
        vec!["warrior"],
        vec!["warrior", "priest"],
        vec!["priest", "mage"],
    ] {
        report(
            &format!("Oakhorn, hirer + {classes:?}"),
            fight(
                "oakhorn",
                "wyrd_oakhorn",
                "wyrd_warden",
                "wyrd_crows,wyrd_boars",
                25,
                &classes,
                400.,
            ),
        );
    }
    for classes in [
        vec![],
        vec!["warrior", "priest"],
        vec!["warrior", "priest", "mage"],
        vec!["warrior", "priest", "mage", "hunter"],
    ] {
        report(
            &format!("Hrungnir, hirer + {classes:?}"),
            fight(
                "hrungnir",
                "wyrd_hrungnir",
                "wyrd_captain",
                "wyrd_stones",
                30,
                &classes,
                600.,
            ),
        );
    }
}

#[test]
fn a_lone_hero_cannot_beat_the_oakhorn_but_a_hired_trio_with_a_healer_can() {
    let alone = fight(
        "oakhorn",
        "wyrd_oakhorn",
        "wyrd_warden",
        "wyrd_crows,wyrd_boars",
        25,
        &[],
        300.,
    );
    assert!(
        !alone.won && alone.boss_left > 0.5,
        "one hero: {} left",
        alone.boss_left
    );
    let three = fight(
        "oakhorn",
        "wyrd_oakhorn",
        "wyrd_warden",
        "wyrd_crows,wyrd_boars",
        25,
        &["warrior", "priest"],
        300.,
    );
    assert!(three.won, "three with a healer: {} left", three.boss_left);
    assert!(
        three.seconds > 100.,
        "a real fight, not a pull: {} s",
        three.seconds
    );
}

#[test]
fn hrungnir_is_a_five_hero_fight_that_one_hero_cannot_touch() {
    let alone = fight(
        "hrungnir",
        "wyrd_hrungnir",
        "wyrd_captain",
        "wyrd_stones",
        30,
        &[],
        300.,
    );
    assert!(
        !alone.won && alone.boss_left > 0.7,
        "one hero: {} left",
        alone.boss_left
    );
    let five = fight(
        "hrungnir",
        "wyrd_hrungnir",
        "wyrd_captain",
        "wyrd_stones",
        30,
        &["warrior", "priest", "mage", "hunter"],
        400.,
    );
    assert!(five.won, "five heroes: {} left", five.boss_left);
    assert!(
        five.seconds > 120.,
        "a fight of minutes: {} s",
        five.seconds
    );
}

#[test]
fn a_woken_ambusher_that_dies_never_respawns_and_one_that_is_still_alive_goes_back_to_sleep() {
    let (mut w, _rx) = escort_world();
    take_escort_quest(&mut w);
    let session = start_escort(&mut w);
    let slots: Vec<usize> = (0..w.spawns.len())
        .filter(|i| w.spawns[*i].ambush.as_deref() == Some("wyrd_eydis#troll"))
        .collect();
    assert_eq!(slots.len(), 2);
    w.release_ambush("wyrd_eydis#troll", session);
    assert!(
        slots.iter().all(|i| !w.slimes[*i].dead
            && w.slimes[*i].hunt
            && w.slimes[*i].target == Some(session))
    );
    // a kill pays like any kill, but the slot does not come back
    w.hit_slime(slots[0], 1, 1e12, false);
    assert!(
        w.slimes[slots[0]].dead && w.slimes[slots[0]].respawn >= 1e8,
        "a dead ambusher stays dead"
    );
    for _ in 0..(40. / TICK) as usize {
        w.step();
    }
    assert!(
        w.slimes[slots[0]].dead,
        "even after the ordinary respawn time"
    );
    // the other is still fighting; when the journey ends it is put back to sleep without a reward
    assert!(!w.slimes[slots[1]].dead);
    w.remove_escort(session);
    assert!(w.slimes[slots[1]].dead && w.slimes[slots[1]].state == "waiting");
}
