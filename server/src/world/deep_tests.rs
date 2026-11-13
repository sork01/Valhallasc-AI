//! Ran's Deep (zone 8, levels 35-40): the sea-floor zone with Keelhaven, the Shallows and the Net (a labyrinth with a two-door
//! chamber), its six monster kinds, the Maelstrom gate pair, the Spark flight and the new `chime` quest objective ("ring the
//! tidebells").
use super::wyrd_tests::{
    at, blocked, calm, drain, flood, grid_size, join, lines, place, reached, world,
};
use super::*;
use std::cmp::Reverse;
use std::collections::BinaryHeap;

const SKALD: usize = 4;
const SKY: usize = 7;
const DEEP: usize = 8;
const KINDS: [&str; 5] = ["draugr", "angler", "moray", "siren", "shellback"];
/// The Net's door in the maze's south wall (the Pearl Gate), and the two doors of Ran's Court (the middles of the wall gaps): the pilot map.
const NET_DOOR: (f64, f64) = (96., 174.);
const COURT_DOORS: [(f64, f64); 2] = [(120., 54.), (144., 46.)];
/// The three camps and what lives in them.
const CAMPS: [(&str, &str); 3] = [
    ("lanternrest", "deep_lr_"),
    ("gatewatch", "deep_gw_"),
    ("drownwatch", "deep_dw_"),
];

fn npc(w: &World, id: &str) -> Npc {
    w.maps[DEEP]
        .npcs
        .iter()
        .find(|n| n.id == id)
        .unwrap_or_else(|| panic!("no NPC {id}"))
        .clone()
}
fn quest(w: &World, id: &str) -> Quest {
    w.maps[DEEP]
        .quests
        .iter()
        .find(|q| q.id == id)
        .unwrap_or_else(|| panic!("no quest {id}"))
        .clone()
}
fn place_of(w: &World, id: &str) -> Place {
    w.maps[DEEP]
        .places
        .iter()
        .find(|p| p.id == id)
        .unwrap_or_else(|| panic!("no place {id}"))
        .clone()
}
fn bells(w: &World, chain: &str) -> Vec<Place> {
    w.maps[DEEP]
        .places
        .iter()
        .filter(|p| p.chain == chain)
        .cloned()
        .collect()
}
fn npc_exists(map: &Map, id: &str) -> bool {
    map.npcs.iter().any(|n| n.id == id)
}
/// The cell beside a spot counts too: people and enemies stand close to walls and the grid is one tile.
fn near(map: &Map, seen: &[bool], p: Point) -> bool {
    [(0., 0.), (1., 0.), (-1., 0.), (0., 1.), (0., -1.)]
        .iter()
        .any(|(dx, dy)| reached(map, seen, at(p.x + dx, p.y + dy)))
}
/// Walking distance (8 neighbours, no corner cutting) from `from` to every cell of the one-tile grid, in tiles.
fn walk_distance(map: &Map, grid: &[bool], from: Point) -> Vec<f64> {
    let n = grid_size(map);
    let mut dist = vec![f64::INFINITY; n * n];
    let start = (from.y as usize) * n + from.x as usize;
    dist[start] = 0.;
    let mut heap = BinaryHeap::new();
    heap.push(Reverse((0u64, start)));
    while let Some(Reverse((d, i))) = heap.pop() {
        if d as f64 / 1000. > dist[i] + 1e-9 {
            continue;
        }
        let (x, y) = ((i % n) as i32, (i / n) as i32);
        for (dx, dy) in [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
        ] {
            let (a, b) = (x + dx, y + dy);
            if a < 0 || b < 0 || a >= n as i32 || b >= n as i32 {
                continue;
            }
            let j = (b as usize) * n + a as usize;
            if grid[j] {
                continue;
            }
            if dx != 0
                && dy != 0
                && (grid[(y as usize) * n + a as usize] || grid[(b as usize) * n + x as usize])
            {
                continue;
            }
            let step = if dx != 0 && dy != 0 {
                std::f64::consts::SQRT_2
            } else {
                1.
            };
            let nd = dist[i] + step;
            if nd < dist[j] {
                dist[j] = nd;
                heap.push(Reverse(((nd * 1000.) as u64, j)));
            }
        }
    }
    dist
}
fn permutations(n: usize) -> Vec<Vec<usize>> {
    fn go(rest: &mut Vec<usize>, now: &mut Vec<usize>, out: &mut Vec<Vec<usize>>) {
        if rest.is_empty() {
            out.push(now.clone());
            return;
        }
        for k in 0..rest.len() {
            let v = rest.remove(k);
            now.push(v);
            go(rest, now, out);
            now.pop();
            rest.insert(k, v);
        }
    }
    let mut out = vec![];
    go(&mut (0..n).collect(), &mut vec![], &mut out);
    out
}
/// Where a hero stands to be inside a bell's circle: beside the bell itself, on ground the grid can reach.
fn spot(map: &Map, seen: &[bool], p: &Place) -> Point {
    for (dx, dy) in [
        (0., 0.),
        (0., 2.),
        (2., 0.),
        (0., -2.),
        (-2., 0.),
        (1.5, 1.5),
        (-1.5, 1.5),
        (1.5, -1.5),
        (-1.5, -1.5),
    ] {
        let c = at(p.x + dx, p.y + dy);
        if reached(map, seen, c) {
            return c;
        }
    }
    panic!("{} cannot be stood in", p.id)
}
fn cell_at(map: &Map, p: Point) -> usize {
    (p.y as usize) * grid_size(map) + p.x as usize
}

// ---- data ----------------------------------------------------------------------------------------------------------------------
#[test]
fn rans_deep_is_a_sea_floor_zone_with_six_kinds_one_hub_and_a_maelstrom_gate_pair() {
    let w = world();
    let map = &w.maps[DEEP];
    assert_eq!(map.name, "R\u{e1}n's Deep");
    assert_eq!((map.size, map.levels), (256, Some([35, 40])));
    assert_eq!(map.size % 8, 0, "the ground is cut in chunks of eight");
    assert_eq!(map.copies, 0);
    // enemies: every kind at its default level, in the counts the design lists; the two sleepers (the Ember Key's guardian and the Empty Seat's
    // shadow) wake only for their own events
    let mut live = std::collections::BTreeMap::<&str, usize>::new();
    let mut sleepers: Vec<&str> = w
        .spawns
        .iter()
        .filter(|s| s.zone == DEEP && s.ambush.is_some())
        .map(|s| s.kind.as_str())
        .collect();
    sleepers.sort_unstable();
    assert_eq!(sleepers, ["ember_firelord", "es_foe_08"]);
    for (id, spawn) in w
        .spawns
        .iter()
        .enumerate()
        .filter(|(_, s)| s.zone == DEEP && s.ambush.is_none())
    {
        *live.entry(spawn.kind.as_str()).or_default() += 1;
        assert!(!w.slimes[id].dead);
        assert!(!map.in_city(at(spawn.x, spawn.y)));
    }
    assert_eq!(
        live.into_iter().collect::<Vec<_>>(),
        [
            ("angler", 16),
            ("draugr", 26),
            ("ghostmaw", 1),
            ("hvitserk", 1),
            ("kraken", 1),
            ("moray", 16),
            ("shellback", 14),
            ("siren", 16)
        ]
    );
    for (kind, level) in [
        ("draugr", 35),
        ("angler", 36),
        ("moray", 37),
        ("siren", 38),
        ("shellback", 39),
        ("kraken", 40),
        ("hvitserk", 37),
        ("ghostmaw", 39),
    ] {
        assert_eq!(Slime::default_level(kind), level, "{kind}");
        assert_eq!(
            is_elite(kind),
            matches!(kind, "kraken" | "hvitserk" | "ghostmaw"),
            "{kind}"
        );
    }
    // exactly three elites live here: the Kraken (five heroes), Hvitserk and the Ghostmaw (three each)
    let elites: Vec<&str> = w
        .slimes
        .iter()
        .filter(|s| {
            s.zone == DEEP && s.elite && !matches!(s.kind.as_str(), "ember_firelord" | "es_foe_08")
        })
        .map(|s| s.kind.as_str())
        .collect();
    assert_eq!(elites.len(), 3);
    for kind in ["kraken", "hvitserk", "ghostmaw"] {
        assert!(elites.contains(&kind), "{kind}");
    }
    // the new zone comes last of the file's zones, so every older enemy id stays
    assert_eq!(
        w.spawns.iter().position(|s| s.zone == DEEP),
        Some(w.spawns.iter().filter(|s| s.zone < DEEP).count())
    );
    // one hub on the sea floor in the south-west, safe ground, with a travel master, and three camps
    assert_eq!(map.camps.len(), 3);
    assert_eq!(
        map.city.as_ref().map(|c| (c.x0, c.x1, c.y0, c.y1)),
        Some((78., 114., 190., 219.))
    );
    assert!(
        map.in_city(at(96., 202.)) && !map.in_city(at(40., 150.)) && !map.in_city(at(96., 100.))
    );
    let master = map
        .npcs
        .iter()
        .find(|n| n.travel_stop.is_some())
        .expect("a travel master");
    assert_eq!(master.id, "travel_keelhaven");
    assert_eq!(
        map.npcs.len(),
        26,
        "Keelhaven's eleven and the three camps' fifteen"
    );
    // the gate pair: Bifrost's Maelstrom down, Keelhaven's up; each arrival clear of every gate and of enemies
    let down = w.maps[SKY]
        .portals
        .iter()
        .find(|p| p.id == "maelstrom_down")
        .unwrap();
    let up = map.portals.iter().find(|p| p.id == "maelstrom_up").unwrap();
    assert_eq!((down.to, up.to), (DEEP, SKY));
    // each arrival is six tiles inside its gate, on the way the gate faces away from
    let (dw, uw) = (down.walk.unwrap(), up.walk.unwrap());
    assert_eq!(
        (down.tx, down.ty),
        (up.x - f64::from(uw[0]) * 6., up.y - f64::from(uw[1]) * 6.)
    );
    assert_eq!(
        (up.tx, up.ty),
        (
            down.x - f64::from(dw[0]) * 6.,
            down.y - f64::from(dw[1]) * 6.
        )
    );
    for (arrival, gates) in [
        (at(down.tx, down.ty), &map.portals),
        (at(up.tx, up.ty), &w.maps[SKY].portals),
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
    for (zone, m) in [
        (DEEP, map.spawn),
        (DEEP, at(down.tx, down.ty)),
        (SKY, at(up.tx, up.ty)),
    ] {
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
        w.maps[SKY].portals.len() >= 2 && w.maps[SKY].portals[0].id == "stormrift_down",
        "Bifrost Reach's old gate keeps index 0"
    );
    // places: 5 landmarks, 7 for the new quests, the Empty Seat circle and 12 bells in three chains; a map without `chain` and `burn` still loads
    assert_eq!(map.places.len(), 25);
    assert_eq!(
        map.places.iter().filter(|p| !p.chain.is_empty()).count(),
        12
    );
    let old: Place = serde_json::from_str(r#"{"id":"a","name":"A","x":1,"y":2,"r":3}"#).unwrap();
    assert!(old.chain.is_empty() && old.burn == 0. && old.waves.is_empty());
    // everybody stands on free ground inside the hub or a camp
    let city = map.city.as_ref().unwrap();
    for n in &map.npcs {
        assert!(
            n.id.starts_with("keel_") // (the Longship door's two people stand beside the door, just west of the plaza)
                || city.contains(at(n.x, n.y))
                || map.camps.iter().any(|c| c.contains(at(n.x, n.y))),
            "{} is in Keelhaven or a camp",
            n.id
        );
        let mut clear = at(n.x, n.y);
        map.collide(&mut clear, PLAYER_RADIUS);
        assert!(
            clear.distance(at(n.x, n.y)) < 1e-6,
            "{} stands in scenery",
            n.id
        );
    }
    // the dungeon copies come after every file zone
    // Every dungeon added since keeps its copies after the file zones, so the count only grows.
    assert!(w.maps.len() >= 49, "{} maps", w.maps.len());
    let first_copy = w.maps.iter().position(|m| m.template.is_some()).unwrap();
    assert!(
        first_copy > 26 && w.maps[first_copy..].iter().all(|m| m.template.is_some()),
        "every copy follows the last file zone"
    );
}

// ---- the Net ------------------------------------------------------------------------------------------------------------------
#[test]
fn the_net_has_one_door_and_a_court_with_two_so_the_kinds_come_in_depth_order() {
    let w = world();
    let map = &w.maps[DEEP];
    let open = |closed: &[(f64, f64, f64)]| flood(map, &blocked(map, closed), map.spawn);
    let kinds_cut = |seen: &[bool]| -> Vec<&'static str> {
        let mut gone = vec![];
        for kind in KINDS.iter().chain(&["kraken", "ghostmaw"]) {
            let mut live = w
                .slimes
                .iter()
                .filter(|s| s.zone == DEEP && s.kind == *kind && !s.dead);
            if !live.any(|s| near(map, seen, s.point())) {
                gone.push(*kind);
            }
        }
        gone
    };
    assert!(kinds_cut(&open(&[])).is_empty(), "everything is reachable");
    // closing the Net's one door cuts off everything in the maze, and nothing in the Shallows
    let sealed = open(&[(NET_DOOR.0, NET_DOOR.1, 8.)]);
    assert_eq!(
        kinds_cut(&sealed),
        [
            "angler",
            "moray",
            "siren",
            "shellback",
            "kraken",
            "ghostmaw"
        ]
    );
    for p in map.places.iter().filter(|p| p.y < 168. || p.y > 186.) {
        let inside = p.y < 168.;
        assert_eq!(
            near(map, &sealed, at(p.x, p.y + 2.)) || near(map, &sealed, at(p.x, p.y)),
            !inside,
            "{} is {} the Net",
            p.id,
            if inside { "inside" } else { "outside" }
        );
    }
    // the chamber has two doors: closing both cuts off only the Kraken, closing one cuts off nothing
    let doors: Vec<(f64, f64, f64)> = COURT_DOORS.iter().map(|&(x, y)| (x, y, 8.)).collect();
    assert_eq!(kinds_cut(&open(&doors)), ["kraken"]);
    for d in &doors {
        assert!(
            kinds_cut(&open(&[*d])).is_empty(),
            "{d:?} alone does not seal the Court"
        );
    }
    // a wall with no door cannot be crossed: the chamber's own walls stand where the doors are not
    let wall = (120., 70., 8.);
    assert!(
        kinds_cut(&open(&[wall])).is_empty(),
        "a disc on the plain wall changes nothing"
    );
    // depth: the further a kind lives from the arrival (by walking), the stronger it is
    let grid = blocked(map, &[]);
    let dist = walk_distance(map, &grid, map.spawn);
    let mean = |kind: &str| {
        let d: Vec<f64> = w
            .slimes
            .iter()
            .filter(|s| s.zone == DEEP && s.kind == kind)
            .map(|s| {
                let c = s.point();
                [(0., 0.), (1., 0.), (-1., 0.), (0., 1.), (0., -1.)]
                    .iter()
                    .map(|(dx, dy)| dist[cell_at(map, at(c.x + dx, c.y + dy))])
                    .fold(f64::INFINITY, f64::min)
            })
            .collect();
        assert!(d.iter().all(|v| v.is_finite()), "{kind} is reachable");
        d.iter().sum::<f64>() / d.len() as f64
    };
    // (the draugr roam the whole width of the Shallows, so they are left out: the Net's kinds come in depth order)
    let order = ["angler", "moray", "siren", "shellback", "kraken"];
    for pair in order.windows(2) {
        assert!(
            mean(pair[0]) < mean(pair[1]),
            "{} lives nearer than {}: {:.0} vs {:.0}",
            pair[0],
            pair[1],
            mean(pair[0]),
            mean(pair[1])
        );
    }
    // the maze is a real labyrinth: the walk to the Kraken is far longer than the straight line
    let boss = w
        .slimes
        .iter()
        .find(|s| s.kind == "kraken")
        .unwrap()
        .point();
    // (measured from the Pearl Gate: the way from Keelhaven to the gate is open water)
    let gate = at(NET_DOOR.0, NET_DOOR.1 + 2.);
    let from_gate = walk_distance(map, &grid, gate);
    let straight = gate.distance(boss);
    let walk = [(0., 0.), (3., 0.), (-3., 0.), (0., 3.), (0., -3.)]
        .iter()
        .map(|(dx, dy)| from_gate[cell_at(map, at(boss.x + dx, boss.y + dy))])
        .fold(f64::INFINITY, f64::min);
    assert!(
        walk > 3. * straight,
        "the way in is {walk:.0}, the line {straight:.0}"
    );
    // enemies keep clear of the bells' circles
    for s in w
        .slimes
        .iter()
        .filter(|s| s.zone == DEEP && !overlay_enemy(&s.kind))
    {
        for b in map.places.iter().filter(|p| !p.chain.is_empty()) {
            assert!(
                s.point().distance(at(b.x, b.y)) > b.r + 3.,
                "{} is clear of {}",
                s.kind,
                b.id
            );
        }
    }
}

// ---- monsters ------------------------------------------------------------------------------------------------------------------
#[test]
fn every_deep_monster_has_its_own_stats_attacks_materials_and_rewards() {
    for (kind, hp, damage, gold, material_id) in [
        ("draugr", 24000., 470., 640, "drowned_coin"),
        ("angler", 20500., 440., 680, "angler_lure"),
        ("moray", 27000., 540., 720, "moray_tooth"),
        ("siren", 23500., 520., 770, "siren_pearl"),
        ("shellback", 40000., 700., 830, "shellback_plate"),
        // Kraken, Hvitserk and Ghostmaw carry their health multiplier from `world/elite-power.txt`.
        ("kraken", 386400., 4400., 4500, "kraken_beak"),
        ("hvitserk", 231000., 2600., 2500, "captains_signet"),
        ("ghostmaw", 383800., 3000., 3200, "ghostmaw_tooth"),
    ] {
        let spawn = SlimeSpawn {
            ambush: None,
            x: 5.,
            y: 5.,
            kind: kind.into(),
            zone: DEEP,
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
        // a real kill pays that level's XP and gold, and drops the material, all in Ran's Deep
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.players.get_mut(&1).unwrap().character.zone = DEEP;
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == DEEP && s.kind == kind && !s.dead)
            .unwrap();
        w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), level + 1);
        let (xp, gold) = (w.slimes[id].xp, w.slimes[id].gold);
        w.hit_slime(id, 1, 1e9, false);
        let c = &w.players[&1].character;
        let paid: u32 = (1..c.level).map(xp_to_level).sum::<u32>() + c.xp;
        assert_eq!(paid, xp, "{kind} xp");
        // enemy gold drops are halved at the kill (MOB_GOLD_SCALE)
        assert_eq!(
            w.drops.iter().find(|d| d.item.is_none()).unwrap().value,
            ((f64::from(gold) * 0.5).round() as u32).max(1)
        );
        assert!(
            w.drops
                .iter()
                .any(|d| d.item.as_deref() == Some(material_id)),
            "{kind} material"
        );
        assert!(w.drops.iter().all(|d| d.zone == DEEP));
    }
    // how each one fights: the angler shoots one slow bead, the siren three bolts, the shellback pounds the ground, the moray charges fastest
    let angler = Slime::ranged("angler").unwrap();
    assert_eq!((angler.shots, angler.range), (1, 12.));
    let siren = Slime::ranged("siren").unwrap();
    assert_eq!((siren.shots, siren.range), (3, 12.5));
    assert!(angler.speed < siren.speed, "the bead is the slow one");
    for kind in ["draugr", "moray", "shellback", "hvitserk", "ghostmaw"] {
        assert!(Slime::ranged(kind).is_none(), "{kind}");
    }
    assert_eq!(Slime::slam_radius("hvitserk"), 3.);
    assert_eq!(Slime::slam_radius("ghostmaw"), 0.);

    assert_eq!(Slime::slam_radius("shellback"), 3.2);
    for kind in ["draugr", "angler", "moray", "siren"] {
        assert_eq!(Slime::slam_radius(kind), 0., "{kind}");
    }
    let charge = |k: &str| Slime::attack_profile(k).2;
    assert!(charge("ghostmaw") >= 12. && charge("hvitserk") < charge("draugr") + 1.);
    assert!(charge("moray") > charge("draugr") && charge("draugr") > charge("shellback"));
    assert_eq!(charge("angler"), 0., "an angler never charges");
    assert_eq!(charge("siren"), 0., "a siren never charges");
    // the Kraken coils for a full second, throws three bolts of ink from afar and pounds the ground up close
    assert_eq!(Slime::attack_profile("kraken").0, 1.);
    assert_eq!(Slime::ranged("kraken").map(|r| r.shots), Some(3));
    assert_eq!(
        (Slime::slam_radius("kraken"), Slime::melee_inside("kraken")),
        (4., 4.5)
    );
    for kind in ["draugr", "angler", "moray", "siren", "shellback", "kraken"] {
        assert!(
            !Slime::fixed_level(kind),
            "{kind} rolls its level like any open-world kind"
        );
    }
}

#[test]
fn the_kraken_credits_five_pays_an_epic_necklace_and_returns_in_five_minutes() {
    let mut w = world();
    let id = w.slimes.iter().position(|s| s.kind == "kraken").unwrap();
    let point = w.slimes[id].point();
    assert_eq!(w.slimes[id].level, 40);
    assert!(w.slimes[id].elite, "the Kraken is an elite");
    let q = quest(&w, "deep_kraken");
    let reward = q.reward_item.clone().unwrap();
    let _rx: Vec<_> = (1..=6).map(|s| join(&mut w, s, Class::Warrior)).collect();
    for session in 1..=6 {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.zone = DEEP;
        c.x = point.x + 2.;
        c.y = point.y + 3.;
        c.quests.push(QuestProgress {
            id: "deep_rans".into(),
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
                .find(|p| p.id == "deep_kraken")
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
    assert_eq!(c.gold, 5000);
}

#[test]
fn both_three_player_elites_credit_nearby_heroes_and_pay_gear() {
    let mut w = world();
    let id = w.slimes.iter().position(|s| s.kind == "hvitserk").unwrap();
    let point = w.slimes[id].point();
    let q = quest(&w, "deep_captain");
    let reward = q.reward_item.clone().unwrap();
    let _rx: Vec<_> = (1..=4).map(|s| join(&mut w, s, Class::Warrior)).collect();
    for session in 1..=4 {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.zone = DEEP;
        c.x = point.x + 2.;
        c.y = point.y + 3.;
        c.quests.push(QuestProgress {
            id: "deep_longship".into(),
            claimed: true,
            completions: 1,
            ..Default::default()
        });
        assert!(quest_action(c, &q, "accept").2);
        w.hit_slime(id, session, 1., false);
    }
    w.players.get_mut(&4).unwrap().character.x = point.x - 20.;
    w.hit_slime(id, 1, 1e9, false);
    let credited: Vec<u32> = (1..=4)
        .map(|s| {
            w.players[&s]
                .character
                .quests
                .iter()
                .find(|p| p.id == "deep_captain")
                .unwrap()
                .counts[0]
        })
        .collect();
    assert_eq!(credited, [1, 1, 1, 0]);
    assert_eq!(w.slimes[id].respawn, 300.);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let (text, _, changed) = quest_action(c, &q, "claim");
    assert!(changed, "{text}");
    assert_eq!(c.quantity(&reward), 1);
    assert_eq!(c.gold, 3000);
    // Thora's quest credits the same three nearby contributors; the Ghostmaw
    // drops its tooth and comes back after ten minutes.
    let g = w.slimes.iter().position(|s| s.kind == "ghostmaw").unwrap();
    let ghost_point = w.slimes[g].point();
    let ghost_quest = quest(&w, "deep_ghostmaw");
    for session in 1..=4 {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.x = ghost_point.x + 2.;
        c.y = ghost_point.y + 3.;
        c.quests.push(QuestProgress {
            id: "deep_garden".into(),
            claimed: true,
            completions: 1,
            ..Default::default()
        });
        assert!(quest_action(c, &ghost_quest, "accept").2);
        w.hit_slime(g, session, 1., false);
    }
    w.players.get_mut(&4).unwrap().character.x = ghost_point.x - 20.;
    w.hit_slime(g, 1, 1e9, false);
    let credited: Vec<u32> = (1..=4)
        .map(|s| {
            w.players[&s]
                .character
                .quests
                .iter()
                .find(|p| p.id == "deep_ghostmaw")
                .unwrap()
                .counts[0]
        })
        .collect();
    assert_eq!(credited, [1, 1, 1, 0]);
    assert_eq!(w.slimes[g].respawn, 600.);
    assert!(
        w.drops
            .iter()
            .any(|d| d.item.as_deref() == Some("ghostmaw_tooth"))
    );
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let (text, _, changed) = quest_action(c, &ghost_quest, "claim");
    assert!(changed, "{text}");
    assert_eq!(c.quantity("necklace_moonstone_l40_blue"), 1);
    assert_eq!(c.gold, 6800);
}

// ---- the questline -----------------------------------------------------------------------------------------------------------------
#[test]
fn the_questline_has_thirty_eight_deep_quests_with_three_chime_chains_and_the_old_objective_kinds()
{
    let w = world();
    let map = &w.maps[DEEP];
    // 38 of the zone's own, the Longship's three (`keel_*`, their people stand in the dungeon) and the Empty Seat's two
    assert_eq!(map.quests.len(), 43);
    assert_eq!(
        map.quests
            .iter()
            .filter(|q| q.id.starts_with("deep_"))
            .count(),
        38
    );
    let mut kinds = std::collections::BTreeSet::new();
    let mut chimes = vec![];
    for q in map.quests.iter().filter(|q| q.id.starts_with("deep_")) {
        assert!(npc_exists(map, &q.npc), "{} giver {}", q.id, q.npc);
        assert_eq!(
            q.reward_xp,
            xp_to_level(q.level) / 10,
            "{} pays a tenth of its level",
            q.id
        );
        assert!(
            (35..=40).contains(&q.level),
            "{} is a level 35-40 quest",
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
                "reach" => assert_eq!(o.target, "R\u{e1}n's Deep"),
                "chime" => {
                    let chain = bells(&w, &o.target);
                    assert_eq!(
                        chain.len() as u32,
                        o.count,
                        "{} wants every bell of its chain",
                        q.id
                    );
                    assert!(chain.iter().all(|b| b.burn > 0. && b.burn == chain[0].burn));
                    chimes.push((q.id.clone(), o.target.clone(), o.count, chain[0].burn));
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
        ["bring", "chime", "kill", "reach", "talk", "visit"]
    );
    assert_eq!(
        chimes,
        [
            (
                "deep_harbour".to_string(),
                "deep_harbour".to_string(),
                3,
                35.
            ),
            ("deep_net".to_string(), "deep_net".to_string(), 4, 45.),
            ("deep_rans".to_string(), "deep_rans".to_string(), 5, 50.),
        ]
    );
    // the chimes do not repeat, and no chain is shared between quests
    assert!(
        map.quests
            .iter()
            .filter(|q| q.repeatable)
            .all(|q| q.objectives.iter().all(|o| o.kind != "chime"))
    );
    // The Kraken needs five heroes, hired at its giver, and an epic reward; the bells open the way to it.
    let kraken = quest(&w, "deep_kraken");
    assert!(kraken.group && kraken.recommended_players == 5);
    assert_eq!(
        kraken.reward_item.as_deref(),
        Some("necklace_moonstone_l40_purple")
    );
    assert_eq!(kraken.requires.as_deref(), Some("deep_rans"));
    // Each group quest has its own giver with rental offers.
    assert!(
        npc(&w, "deep_warden")
            .offers
            .iter()
            .any(|o| o.merc.is_some())
    );
    assert!(
        npc(&w, "deep_halla")
            .offers
            .iter()
            .any(|o| o.merc.is_some())
    );
    assert!(
        npc(&w, "deep_thora")
            .offers
            .iter()
            .any(|o| o.merc.is_some())
    );
    assert_eq!(
        (quest(&w, "deep_captain").npc.as_str(), kraken.npc.as_str()),
        ("deep_halla", "deep_warden")
    );
    for (id, reward) in [
        ("deep_net", "pants_wayfarer_l35_blue"),
        ("deep_rans", "pants_wayfarer_l40_blue"),
    ] {
        assert_eq!(quest(&w, id).reward_item.as_deref(), Some(reward));
        assert!(item(reward).is_some(), "{reward}");
    }
    // Each elite has a separate group quest, including Thora's Ghostmaw hunt.
    let captain = quest(&w, "deep_captain");
    assert!(captain.group && captain.recommended_players == 3);
    assert_eq!(captain.objectives[0].target, "hvitserk");
    assert_eq!(
        captain.reward_item.as_deref(),
        Some("accessory_amber_l35_blue")
    );
    assert!(item("accessory_amber_l35_blue").is_some());
    let ghostmaw = quest(&w, "deep_ghostmaw");
    assert!(ghostmaw.group && ghostmaw.recommended_players == 3);
    assert_eq!(ghostmaw.npc, "deep_thora");
    assert_eq!(ghostmaw.requires.as_deref(), Some("deep_garden"));
    assert_eq!(
        ghostmaw.reward_item.as_deref(),
        Some("necklace_moonstone_l40_blue")
    );
    for (kind, quests) in [("hvitserk", 1), ("kraken", 1), ("ghostmaw", 1)] {
        let n = map
            .quests
            .iter()
            .filter(|q| {
                q.objectives
                    .iter()
                    .any(|o| o.kind == "kill" && o.target == kind)
            })
            .count();
        assert_eq!(n, quests, "{kind} quests");
    }
    // the progression quest finds you at level 35 and is handed in at Keelhaven's warden
    let onward = quest(&w, "deep_onward");
    assert_eq!(
        (onward.auto_level, onward.npc.as_str()),
        (Some(35), "deep_warden")
    );
    // the bells come in the order of the story: harbour, net, then Ran's
    let at_of = |id: &str| map.quests.iter().position(|q| q.id == id).unwrap();
    assert!(at_of("deep_harbour") < at_of("deep_net") && at_of("deep_net") < at_of("deep_rans"));
    // every monster of the zone has a hunt and a hand-in
    for kind in KINDS {
        assert!(
            map.quests.iter().any(|q| q
                .objectives
                .iter()
                .any(|o| o.kind == "kill" && o.target == kind)),
            "{kind} is hunted"
        );
    }
}

#[test]
fn the_deep_progression_quest_comes_at_level_thirty_five_and_completes_on_arrival() {
    let w = world();
    let q = quest(&w, "deep_onward");
    assert_eq!((q.auto_level, q.level), (Some(35), 35));
    assert_eq!(q.npc, "deep_warden");
    let mut c = Character::mercenary(Class::Warrior, 34, "Diver");
    sync_progression(&mut c, &w.maps);
    assert!(!c.quests.iter().any(|p| p.id == "deep_onward"));
    c.level = 35;
    let arrived = sync_progression(&mut c, &w.maps);
    assert!(
        arrived.iter().any(|t| t == "Down the Maelstrom"),
        "{arrived:?}"
    );
    let counts = |c: &Character| {
        c.quests
            .iter()
            .find(|p| p.id == "deep_onward")
            .unwrap()
            .counts
            .clone()
    };
    assert_eq!(counts(&c), vec![0]);
    c.zone = DEEP;
    sync_progression(&mut c, &w.maps);
    assert_eq!(counts(&c), vec![1]);
}

#[test]
fn the_deep_spark_master_links_keelhaven_to_the_perch() {
    let w = world();
    let links = npc(&w, "travel_keelhaven").travel_links;
    for stop in [
        "travel_perch",
        "travel_nacrehold",
        "travel_astralhollow",
        "travel_lanternrest",
        "travel_gatewatch",
        "travel_drownwatch",
    ] {
        assert!(links.iter().any(|l| l == stop), "Keelhaven links to {stop}");
    }
    // (Bifrost's Perch also links the Cinderwatch camp and its own outposts now)
    let perch = w.maps[SKY]
        .npcs
        .iter()
        .find(|n| n.id == "travel_perch")
        .unwrap()
        .travel_links
        .clone();
    assert!(
        // towards the Wyrdwood the Perch flies to Ridgewatch, the station nearest the Stormrift
        perch.iter().any(|l| l == "travel_ridgewatch")
            && perch.iter().any(|l| l == "travel_keelhaven")
    );
    assert!(w.maps[DEEP].in_city(at(
        npc(&w, "travel_keelhaven").x,
        npc(&w, "travel_keelhaven").y
    )));
}

// ---- ring the tidebells ----------------------------------------------------------------------------------------------------------
/// A world with every enemy asleep, and a level-40 hero in god mode who has taken the quest and stands at `at_` in zone `zone`.
fn ringer(quest_id: &str, zone: usize, at_: Point) -> (World, mpsc::Receiver<Value>) {
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
fn rung(w: &World) -> u32 {
    w.players[&1].character.quests[0].counts[0]
}
fn run(w: &mut World, rx: &mut mpsc::Receiver<Value>, ticks: usize) -> Vec<String> {
    let mut told = vec![];
    for _ in 0..ticks {
        w.step();
        told.extend(lines(rx));
    }
    told
}
fn seconds(s: f64) -> usize {
    (s / TICK).round() as usize
}
/// Somewhere in the zone that is inside no bell's circle and no hub.
const PARKED: (f64, f64) = (80., 165.);

#[test]
fn a_bell_rings_the_moment_a_hero_walks_into_its_circle_and_goes_silent_after_its_burn_time() {
    let bell = place_of(&world(), "deep_harbour_a1");
    assert_eq!((bell.chain.as_str(), bell.burn), ("deep_harbour", 35.));
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(PARKED.0, PARKED.1));
    let told = run(&mut w, &mut rx, 40);
    assert_eq!(rung(&w), 0, "nothing rings while the hero is elsewhere");
    assert!(told.iter().all(|t| !t.contains("bell")), "{told:?}");
    // the first tick inside the circle counts at once (no second of waiting)
    place(&mut w, 1, DEEP, at(bell.x + 1., bell.y));
    let told = run(&mut w, &mut rx, 1);
    assert_eq!(rung(&w), 1);
    assert!(
        told.iter()
            .any(|t| t.contains(&bell.name) && t.contains("35 s")),
        "{told:?}"
    );
    // it keeps ringing after the hero leaves, for exactly its burn time
    place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1));
    run(&mut w, &mut rx, seconds(34.));
    assert_eq!(rung(&w), 1, "still ringing after 34 s");
    let told = run(&mut w, &mut rx, seconds(1.5));
    assert_eq!(rung(&w), 0, "silent after 35 s");
    assert!(
        told.iter().any(|t| t.contains("last bell falls silent")),
        "{told:?}"
    );
    // the edge of the circle counts, a step past it does not
    place(&mut w, 1, DEEP, at(bell.x + bell.r + 0.4, bell.y));
    run(&mut w, &mut rx, 5);
    assert_eq!(rung(&w), 0);
    place(&mut w, 1, DEEP, at(bell.x + bell.r - 0.3, bell.y));
    run(&mut w, &mut rx, 1);
    assert_eq!(rung(&w), 1);
}

#[test]
fn ringing_a_bell_again_restarts_its_time_and_standing_in_it_keeps_it_lit() {
    let bell = place_of(&world(), "deep_harbour_a1");
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(bell.x, bell.y + 1.));
    run(&mut w, &mut rx, seconds(60.));
    assert_eq!(
        rung(&w),
        1,
        "a hero who stays inside keeps the bell ringing for ever"
    );
    place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1));
    run(&mut w, &mut rx, seconds(30.));
    assert_eq!(rung(&w), 1);
    // walk back in at 30 s of 35: the time starts over
    place(&mut w, 1, DEEP, at(bell.x, bell.y + 1.));
    run(&mut w, &mut rx, 1);
    place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1));
    run(&mut w, &mut rx, seconds(34.));
    assert_eq!(rung(&w), 1, "34 s after the second ring");
    run(&mut w, &mut rx, seconds(2.));
    assert_eq!(rung(&w), 0);
}

#[test]
fn the_objective_completes_when_every_bell_rings_at_once_and_stays_done() {
    let chain = bells(&world(), "deep_harbour");
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(PARKED.0, PARKED.1));
    let mut told = vec![];
    for (k, bell) in chain.iter().enumerate() {
        place(&mut w, 1, DEEP, at(bell.x + 1., bell.y));
        told.extend(run(&mut w, &mut rx, 1));
        assert_eq!(rung(&w), if k + 1 < chain.len() { k as u32 + 1 } else { 3 });
        place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1));
        told.extend(run(&mut w, &mut rx, seconds(5.)));
    }
    assert_eq!(rung(&w), 3);
    assert!(
        told.iter().any(|t| t.contains("All 3 bells ring as one")),
        "{told:?}"
    );
    assert!(w.chime.lit.is_empty(), "the finished chain stops ringing");
    // done for good: the count does not fall when the time would have run out, and the quest is ready to hand in
    run(&mut w, &mut rx, seconds(80.));
    assert_eq!(rung(&w), 3);
    let q = quest(&w, "deep_harbour");
    assert!(q.ready(&w.players[&1].character.quests[0]));
}

#[test]
fn a_hero_who_is_too_slow_never_completes_the_chain() {
    let chain = bells(&world(), "deep_harbour");
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(PARKED.0, PARKED.1));
    for bell in &chain {
        place(&mut w, 1, DEEP, at(bell.x + 1., bell.y));
        run(&mut w, &mut rx, 1);
        place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1));
        run(&mut w, &mut rx, seconds(20.));
    }
    assert!(
        rung(&w) < 3,
        "20 s between bells is too slow for 35 s bells"
    );
    assert!(!quest(&w, "deep_harbour").ready(&w.players[&1].character.quests[0]));
    // two bells together are not enough either
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(PARKED.0, PARKED.1));
    for bell in chain.iter().take(2) {
        place(&mut w, 1, DEEP, at(bell.x + 1., bell.y));
        run(&mut w, &mut rx, 1);
        place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1));
        run(&mut w, &mut rx, seconds(2.));
    }
    assert_eq!(rung(&w), 2);
    run(&mut w, &mut rx, seconds(40.));
    assert_eq!(rung(&w), 0);
}

#[test]
fn a_fall_silences_every_bell_and_resets_the_count() {
    let chain = bells(&world(), "deep_harbour");
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(chain[0].x, chain[0].y + 1.));
    run(&mut w, &mut rx, 2);
    place(&mut w, 1, DEEP, at(chain[1].x, chain[1].y + 1.));
    run(&mut w, &mut rx, 2);
    assert_eq!(rung(&w), 2);
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    let told = run(&mut w, &mut rx, 2);
    assert_eq!(rung(&w), 0);
    assert!(w.chime.lit.is_empty());
    assert!(told.iter().any(|t| t.contains("chime breaks")), "{told:?}");
    // a hero who stays down does not ring anything even when lying inside a circle
    run(&mut w, &mut rx, 20);
    assert_eq!(rung(&w), 0);
}

#[test]
fn bells_ring_only_for_the_chain_of_an_accepted_unfinished_quest_and_per_hero() {
    let a1 = place_of(&world(), "deep_harbour_a1");
    // not accepted: nothing rings
    let mut w = world();
    calm(&mut w);
    w.god_mode = true;
    let mut rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, DEEP, at(a1.x, a1.y + 1.));
    run(&mut w, &mut rx, 40);
    assert!(w.chime.lit.is_empty());
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .all(|q| q.id != "deep_harbour")
    );
    // already claimed: nothing rings
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .quests
        .push(QuestProgress {
            id: "deep_harbour".into(),
            counts: vec![3],
            claimed: true,
            completions: 1,
        });
    run(&mut w, &mut rx, 40);
    assert!(w.chime.lit.is_empty());
    assert_eq!(w.players[&1].character.quests[0].counts[0], 3);
    // another chain's quest ignores these bells
    let (mut w, mut rx) = ringer("deep_net", DEEP, at(a1.x, a1.y + 1.));
    run(&mut w, &mut rx, 40);
    assert_eq!(rung(&w), 0);
    assert!(w.chime.lit.is_empty());
    // the same coordinates in another zone are not a bell: only the zone's own places count
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(a1.x, a1.y));
    place(&mut w, 1, 1, at(a1.x, a1.y));
    run(&mut w, &mut rx, 40);
    assert_eq!(rung(&w), 0);
    assert!(w.chime.lit.is_empty());
    // two heroes: each has their own bells; one who does not hold the quest rings nothing
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(a1.x, a1.y + 1.));
    let mut rx2 = join(&mut w, 2, Class::Mage);
    place(&mut w, 2, DEEP, at(a1.x + 1., a1.y));
    run(&mut w, &mut rx, 10);
    drain(&mut rx2);
    assert_eq!(rung(&w), 1);
    assert!(w.players[&2].character.quests.is_empty());
    assert_eq!(w.chime.view(1).len(), 1);
    assert!(w.chime.view(2).is_empty());
    // a second hero with the quest rings a bell of their own, and the first one's count does not move
    let objectives = quest(&w, "deep_harbour").objectives.len();
    w.players
        .get_mut(&2)
        .unwrap()
        .character
        .quests
        .push(QuestProgress {
            id: "deep_harbour".into(),
            counts: vec![0; objectives],
            claimed: false,
            completions: 0,
        });
    let a2 = place_of(&w, "deep_harbour_a2");
    place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1));
    place(&mut w, 2, DEEP, at(a2.x, a2.y + 1.));
    run(&mut w, &mut rx, 5);
    assert_eq!(w.players[&2].character.quests[0].counts[0], 1);
    assert_eq!(rung(&w), 1, "hero 1 still has only the first bell");
    assert_eq!(w.chime.view(1)[0].0, "deep_harbour_a1");
    assert_eq!(w.chime.view(2)[0].0, "deep_harbour_a2");
}

#[test]
fn the_snapshot_lists_a_heros_bells_with_the_time_left() {
    let a1 = place_of(&world(), "deep_harbour_a1");
    let (mut w, mut rx) = ringer("deep_harbour", DEEP, at(a1.x, a1.y + 1.));
    let mut rx2 = join(&mut w, 2, Class::Mage);
    place(&mut w, 2, DEEP, at(PARKED.0, PARKED.1));
    run(&mut w, &mut rx, 2);
    place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1 - 3.));
    run(&mut w, &mut rx, seconds(10.));
    drain(&mut rx2);
    let view = w.snapshot_for(DEEP);
    let id = w.players[&1].character.id.clone();
    let mine = view["players"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == id)
        .unwrap();
    let list = mine["bells"].as_array().expect("bells are listed");
    assert_eq!(list.len(), 1);
    assert_eq!(list[0]["place"], "deep_harbour_a1");
    let left = list[0]["left"].as_f64().unwrap();
    assert!((left - 24.9).abs() < 0.3, "left {left}");
    // a hero with no bells has no such key; another zone's view has none either
    let other = view["players"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] != id)
        .unwrap();
    assert!(other.get("bells").is_none());
    assert!(w.snapshot_for(1)["players"].as_array().unwrap().is_empty());
    // the time falls every tick
    run(&mut w, &mut rx, seconds(5.));
    let view = w.snapshot_for(DEEP);
    let mine = view["players"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == id)
        .unwrap();
    assert!(mine["bells"][0]["left"].as_f64().unwrap() < left - 4.5);
}

#[test]
fn a_saved_count_with_no_bells_resets_quietly_and_leaving_clears_the_bells() {
    let chain = bells(&world(), "deep_net");
    let (mut w, mut rx) = ringer("deep_net", DEEP, at(PARKED.0, PARKED.1));
    // a hero who logged out with two bells counted comes back to a count of 0, without a "falls silent" line
    w.players.get_mut(&1).unwrap().character.quests[0].counts[0] = 2;
    let told = run(&mut w, &mut rx, 3);
    assert_eq!(rung(&w), 0);
    assert!(told.iter().all(|t| !t.contains("falls silent")), "{told:?}");
    // a bell rung and then the hero leaves the world: nothing is left behind
    place(&mut w, 1, DEEP, at(chain[0].x, chain[0].y + 1.));
    run(&mut w, &mut rx, 2);
    assert_eq!(w.chime.lit.len(), 1);
    w.players.remove(&1);
    w.step();
    assert!(w.chime.lit.is_empty());
}

// ---- can the bells be rung in time? ---------------------------------------------------------------------------------------------
/// For every chain: the shortest walk that visits all its bells, on the real collision grid, is a fraction of the distance the
/// slowest class covers while the first bell still rings. Returns (best order of bell indices, distance between each pair).
fn plan(w: &World, chain: &str) -> (Vec<Place>, Vec<Point>, Vec<usize>, Vec<f64>) {
    let map = &w.maps[DEEP];
    let grid = blocked(map, &[]);
    let seen = flood(map, &grid, map.spawn);
    let list = bells(w, chain);
    let spots: Vec<Point> = list.iter().map(|b| spot(map, &seen, b)).collect();
    let fields: Vec<Vec<f64>> = spots
        .iter()
        .map(|&s| walk_distance(map, &grid, s))
        .collect();
    let mut best: Option<(f64, Vec<usize>)> = None;
    for order in permutations(list.len()) {
        let total: f64 = order
            .windows(2)
            .map(|p| fields[p[0]][cell_at(map, spots[p[1]])])
            .sum();
        if best.as_ref().is_none_or(|(b, _)| total < *b) {
            best = Some((total, order));
        }
    }
    let (_, order) = best.unwrap();
    let legs: Vec<f64> = order
        .windows(2)
        .map(|p| fields[p[0]][cell_at(map, spots[p[1]])])
        .collect();
    (list, spots, order, legs)
}

#[test]
fn every_chain_can_be_rung_by_the_slowest_class_but_not_by_a_much_slower_hero() {
    let speed = Class::Warrior.speed();
    for (chain, bells_n, burn) in [
        ("deep_harbour", 3, 35.),
        ("deep_net", 4, 45.),
        ("deep_rans", 5, 50.),
    ] {
        let w = world();
        let (list, spots, order, legs) = plan(&w, chain);
        assert_eq!(list.len(), bells_n);
        let total: f64 = legs.iter().sum();
        let window = speed * burn;
        assert!(
            total > 0.45 * window && total < 0.8 * window,
            "{chain}: the best tour is {total:.0} tiles against a window of {window:.0}"
        );
        // simulate it: the warrior walks the best order at full speed (parked outside every circle while walking)
        let run_chain = |factor: f64| -> u32 {
            let (mut w, mut rx) = ringer(chain, DEEP, at(PARKED.0, PARKED.1));
            for (k, &i) in order.iter().enumerate() {
                if k > 0 {
                    let ticks = (legs[k - 1] / (speed * factor * TICK)).ceil() as usize;
                    run(&mut w, &mut rx, ticks);
                }
                place(&mut w, 1, DEEP, spots[i]);
                run(&mut w, &mut rx, 1);
                place(&mut w, 1, DEEP, at(PARKED.0, PARKED.1));
            }
            rung(&w)
        };
        assert_eq!(
            run_chain(1.),
            bells_n as u32,
            "{chain}: a warrior at full speed rings every bell"
        );
        assert!(
            run_chain(0.45) < bells_n as u32,
            "{chain}: a hero at 45 % speed fails"
        );
    }
}

// ---- the Maelstrom ----------------------------------------------------------------------------------------------------------------
#[test]
fn the_maelstrom_stands_on_the_eyrie_and_both_gates_work() {
    let mut w = world();
    let down = w.maps[SKY]
        .portals
        .iter()
        .find(|p| p.id == "maelstrom_down")
        .unwrap()
        .clone();
    // it is on floor, clear of scenery, and the old return gate of Bifrost Reach is untouched
    let rows: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let floor = rows["zones"][SKY - 1]["sky"].as_array().unwrap();
    let arrival = w.maps[DEEP].portals[0].clone();
    for (x, y) in [(down.x, down.y), (arrival.tx, arrival.ty)] {
        let row = floor[y as usize].as_str().unwrap().as_bytes();
        assert_ne!(row[x as usize], b' ', "({x}, {y}) is over the void");
    }
    // walking into it carries the hero down to Keelhaven, and back up (the updrafts are walk-in gates: the hero walks the way they face)
    let mut rx = join(&mut w, 1, Class::Warrior);
    let side = down.walk.expect("a walk-in gate");
    place(&mut w, 1, SKY, at(down.x, down.y));
    w.message(
        1,
        ClientMessage::Move {
            x: down.x + f64::from(side[0]) * 3.,
            y: down.y + f64::from(side[1]) * 3.,
        },
    );
    run(&mut w, &mut rx, 40);
    assert_eq!(w.players[&1].character.zone, DEEP);
    let up = w.maps[DEEP].portals[0].clone();
    let side = up.walk.expect("a walk-in gate");
    place(&mut w, 1, DEEP, at(up.x, up.y));
    w.message(
        1,
        ClientMessage::Move {
            x: up.x + f64::from(side[0]) * 3.,
            y: up.y + f64::from(side[1]) * 3.,
        },
    );
    run(&mut w, &mut rx, 40);
    assert_eq!(w.players[&1].character.zone, SKY);
    assert!(w.maps[SKALD].portals.len() >= 2);
}

// ---- the pilot map: gates on the rim, outposts, the Nacrehold band ------------------------------------------------------------------
fn raw_deep() -> Value {
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    raw["zones"][DEEP - 1].clone()
}
fn on_outline(raw: &Value, x: f64, y: f64) -> bool {
    raw["shapeFloor"][y as usize]
        .as_str()
        .and_then(|r| r.as_bytes().get(x as usize).copied())
        == Some(b'#')
}
fn segment_distance(p: (f64, f64), a: (f64, f64), b: (f64, f64)) -> f64 {
    let (dx, dy) = (b.0 - a.0, b.1 - a.1);
    let t = (((p.0 - a.0) * dx + (p.1 - a.1) * dy) / (dx * dx + dy * dy).max(1e-9)).clamp(0., 1.);
    (p.0 - a.0 - t * dx).hypot(p.1 - a.1 - t * dy)
}

#[test]
fn every_crossing_of_the_deep_stays_a_portal_on_the_rim_and_keeps_its_far_end() {
    let w = world();
    let raw = raw_deep();
    let map = &w.maps[DEEP];
    // the only seam in or out is the one to Nacrehold (owner, 2026-11-07); every other crossing of the Deep stays a portal
    for (zone, m) in w.maps.iter().enumerate() {
        for p in m.portals.iter().filter(|p| p.to == DEEP || zone == DEEP) {
            assert!(
                p.seam.is_none() || (zone == 9 && p.to == DEEP) || (zone == DEEP && p.to == 9),
                "zone {zone}: {} is a seam",
                p.id
            );
        }
    }
    let ids: Vec<&str> = map.portals.iter().map(|p| p.id.as_str()).collect();
    assert_eq!(
        ids,
        ["maelstrom_up", "nacre_gate", "deep_longship", "path_8_13"]
    );
    // each stands on the outline floor, a gate on the rim faces outwards and its arrival lies inside
    for p in map.portals.iter().filter(|p| p.seam.is_none()) {
        assert!(on_outline(&raw, p.x, p.y), "{} is on the floor", p.id);
        if let Some(side) = p.walk {
            let beyond = (p.x + f64::from(side[0]) * 6., p.y + f64::from(side[1]) * 6.);
            assert!(
                !on_outline(&raw, beyond.0, beyond.1),
                "{} faces the rim: six tiles on is open sea",
                p.id
            );
        }
    }
    // the far ends point back at the arrival six tiles inside each gate, or below the Longship's door
    let arrival = |id: &str| {
        let p = map.portals.iter().find(|p| p.id == id).unwrap();
        let s = p.walk.unwrap();
        (p.x - f64::from(s[0]) * 6., p.y - f64::from(s[1]) * 6.)
    };
    for (zone, id, gate) in [
        (SKY, "maelstrom_down", "maelstrom_up"),
        (13, "path_13_8", "path_8_13"),
    ] {
        let p = w.maps[zone].portals.iter().find(|p| p.id == id).unwrap();
        let (x, y) = arrival(gate);
        assert!(
            (p.tx - x).abs() < 1e-6 && (p.ty - y).abs() < 1e-6,
            "{id} arrives at the Deep's {gate}"
        );
        assert!(
            on_outline(&raw, p.tx, p.ty),
            "{id}: the arrival is on the floor"
        );
    }
    let door = map
        .portals
        .iter()
        .find(|p| p.id == "deep_longship")
        .unwrap();
    for id in ["keel_return", "keel_clear"] {
        let p = w
            .maps
            .iter()
            .flat_map(|m| &m.portals)
            .find(|p| p.id == id)
            .unwrap();
        assert_eq!((p.tx, p.ty), (door.x, door.y + 5.), "{id}");
    }
    // and every one of them can be walked to from the spawn
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for p in map.portals.iter().filter(|p| p.seam.is_none()) {
        let s = p.walk.unwrap_or([0, 0]);
        assert!(
            near(
                map,
                &seen,
                at(
                    p.x - f64::from(s[0]) * 2.,
                    p.y - f64::from(s[1]) * 2. + if p.walk.is_none() { 3. } else { 0. }
                )
            ),
            "{} can be reached on foot",
            p.id
        );
    }
}

#[test]
fn the_three_outposts_are_sanctuaries_with_their_people_a_master_a_mailbox_and_the_new_quests() {
    let w = world();
    let map = &w.maps[DEEP];
    for (key, prefix) in CAMPS {
        let master = npc(&w, &format!("travel_{key}"));
        let camp = map
            .camps
            .iter()
            .find(|c| c.contains(at(master.x, master.y)))
            .unwrap_or_else(|| panic!("{key} has a camp"));
        let people: Vec<&Npc> = map
            .npcs
            .iter()
            .filter(|n| n.id.starts_with(prefix))
            .collect();
        assert_eq!(people.len(), 3, "{key}: two givers and a trader");
        assert_eq!(
            people.iter().filter(|n| n.buys).count(),
            1,
            "{key}: one trader"
        );
        for n in people {
            assert!(camp.contains(at(n.x, n.y)), "{} stands in {key}", n.id);
        }
        let box_ = npc(&w, &format!("mailbox_8_{key}"));
        assert!(camp.contains(at(box_.x, box_.y)), "{key} has its mailbox");
        // every camp is linked with Keelhaven and with the other camps
        assert!(
            master
                .travel_links
                .contains(&"travel_keelhaven".to_string())
        );
        for other in ["lanternrest", "gatewatch", "drownwatch"] {
            assert!(
                other == key || master.travel_links.contains(&format!("travel_{other}")),
                "{key}: the two other camps"
            );
        }
        assert!(
            npc(&w, "travel_keelhaven")
                .travel_links
                .contains(&format!("travel_{key}")),
            "Keelhaven links back to {key}"
        );
        // the camp's own quests: four each, every giver one of its people (the ledger is Keelhaven's)
        let quests: Vec<&Quest> = map
            .quests
            .iter()
            .filter(|q| q.id.starts_with(prefix))
            .collect();
        assert_eq!(quests.len(), 4, "{key}");
        for q in quests {
            assert!(q.npc.starts_with(prefix), "{} is given in {key}", q.id);
        }
    }
    assert!(
        map.quests
            .iter()
            .any(|q| q.id == "deep_kh_ledger" && q.npc == "deep_warden")
    );
    // every old quest id is still here
    for id in [
        "deep_welcome",
        "deep_draugr",
        "deep_coins",
        "deep_longship",
        "deep_harbour",
        "deep_anglers",
        "deep_lures",
        "deep_morays",
        "deep_teeth",
        "deep_chapel",
        "deep_captain",
        "deep_net",
        "deep_sirens",
        "deep_pearls",
        "deep_door",
        "deep_shellbacks",
        "deep_plates",
        "deep_garden",
        "deep_ghostmaw",
        "deep_rans",
        "deep_kraken",
        "deep_patrol",
        "deep_bounty",
        "deep_vanguard",
        "deep_onward",
        "keel_entry",
        "keel_cargo",
        "keel_rigging",
        "es_08",
        "es_go_08",
    ] {
        quest(&w, id);
    }
    // the elites keep their quests and nobody new joined them
    for (id, kind) in [
        ("deep_captain", "hvitserk"),
        ("deep_ghostmaw", "ghostmaw"),
        ("deep_kraken", "kraken"),
    ] {
        assert!(
            quest(&w, id).objectives.iter().any(|o| o.target == kind),
            "{id}"
        );
    }
}

#[test]
fn the_nacrehold_border_band_is_kept_free_for_the_seam() {
    let w = world();
    let raw = raw_deep();
    let runs: Vec<Vec<(f64, f64)>> = raw["shape"]["edges"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|e| e["kind"] == "shared" && e["other"] == 9)
        .map(|e| {
            e["points"]
                .as_array()
                .unwrap()
                .iter()
                .map(|p| (p[0].as_f64().unwrap(), p[1].as_f64().unwrap()))
                .collect()
        })
        .collect();
    assert!(!runs.is_empty(), "the Deep shares a border with Nacrehold");
    let band = |x: f64, y: f64| {
        runs.iter()
            .flat_map(|run| run.windows(2).map(|s| segment_distance((x, y), s[0], s[1])))
            .fold(f64::INFINITY, f64::min)
    };
    for s in w.slimes.iter().filter(|s| s.zone == DEEP) {
        assert!(
            band(s.x, s.y) >= 7.,
            "{} stands {:.1} from the Nacrehold border",
            s.kind,
            band(s.x, s.y)
        );
    }
    for o in raw["objects"].as_array().unwrap() {
        let (kind, x, y) = (
            o["kind"].as_str().unwrap(),
            o["x"].as_f64().unwrap(),
            o["y"].as_f64().unwrap(),
        );
        if [
            "house",
            "chapel",
            "stall",
            "fountain",
            "lamp",
            "bench",
            "noticeboard",
            "tent",
        ]
        .contains(&kind)
        {
            assert!(
                band(x, y) >= 20.,
                "{kind} stands {:.1} from the border",
                band(x, y)
            );
        } else if kind != "void" && kind != "reefwall" {
            assert!(
                band(x, y) >= 2.5,
                "{kind} stands {:.1} from the border",
                band(x, y)
            );
        }
    }
    // the rim reef that will open when the seam comes is tagged, so it can be found
    let rim = raw["objects"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["rim"] == 1)
        .count();
    assert!(rim > 200, "{rim} rim pieces");
}

#[test]
fn the_tideway_and_the_way_to_astralhollow_are_walked_through_both_ways() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (gate_id, zone, back_id) in [
        ("path_8_13", 13, "path_13_8"),
        ("maelstrom_up", SKY, "maelstrom_down"),
    ] {
        let gate = w.maps[DEEP]
            .portals
            .iter()
            .find(|p| p.id == gate_id)
            .unwrap()
            .clone();
        let side = gate.walk.expect("a walk-in gate");
        place(&mut w, 1, DEEP, at(gate.x, gate.y));
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
        // and back: the far side's gate carries the hero to the arrival six tiles inside this gate
        let back = w.maps[zone]
            .portals
            .iter()
            .find(|p| p.id == back_id)
            .unwrap()
            .clone();
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
        assert_eq!(
            w.players[&1].character.zone, DEEP,
            "{back_id} returns to the Deep"
        );
        let c = &w.players[&1].character;
        assert!(
            at(c.x, c.y).distance(at(gate.x, gate.y)) < 12.,
            "{back_id} puts the hero near {gate_id}"
        );
    }
}
