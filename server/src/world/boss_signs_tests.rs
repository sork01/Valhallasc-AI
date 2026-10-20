//! The boss signs (`BOSSMECH-SIGN-ENGINE`): the data, where each sign stands, what the snapshot says about it, and
//! what reading it does.
use super::boss_mechanics::BossMech;
use super::chests::{blocked_grid, distance_field, in_room};
use super::*;
use crate::bossmech::BossDef;
use crate::bosssign::{self, SignDef};
use crate::model::Class;
use crate::world::wyrd_tests::{drain, join, world};

/// Every zone that is the template of a dungeon with a final boss: (zone index, boss kind).
fn dungeons(w: &World) -> Vec<(usize, String)> {
    (0..w.maps.len())
        .filter(|&z| w.maps[z].template.is_none() && !w.maps[z].final_boss.is_empty())
        .map(|z| (z, w.maps[z].final_boss.clone()))
        .collect()
}
/// A boss entry in the table, which is all a sign asks of a mechanic: that the boss has one.
fn mechanic() -> BossDef {
    serde_json::from_str(r#"{"mechanics":[]}"#).expect("a boss definition")
}

#[test]
fn there_is_a_sign_for_each_dungeon_and_nowhere_else() {
    let w = world();
    let found = dungeons(&w);
    assert_eq!(found.len(), 18, "{found:?}");
    let mut kinds: Vec<&str> = found.iter().map(|(_, k)| k.as_str()).collect();
    kinds.sort_unstable();
    let mut signs: Vec<&str> = w.signs.keys().map(String::as_str).collect();
    signs.sort_unstable();
    assert_eq!(signs, kinds);
    // Copies carry the template's boss kind, so they share its sign and need none of their own.
    for z in 0..w.maps.len() {
        if w.maps[z].template.is_some() && !w.maps[z].final_boss.is_empty() {
            assert!(w.signs.contains_key(&w.maps[z].final_boss), "zone {z}");
        }
    }
}

#[test]
fn every_sign_has_words_and_a_picture_and_a_missing_one_is_refused() {
    let w = world();
    for (kind, def) in &w.signs {
        bosssign::validate(kind, def).unwrap_or_else(|e| panic!("{e}"));
    }
    let good = w.signs["hollowking"].clone();
    let bad = |edit: &dyn Fn(&mut SignDef)| {
        let mut d = good.clone();
        edit(&mut d);
        bosssign::validate("hollowking", &d).is_err()
    };
    assert!(!bad(&|_| {}));
    assert!(bad(&|d| d.what = "  ".into()));
    assert!(bad(&|d| d.todo.clear()));
    assert!(bad(&|d| d.tip.clear()));
    assert!(bad(&|d| d.title.clear()));
    assert!(bad(&|d| d.tip = "x".repeat(bosssign::MAX_PART + 1)));
    assert!(bad(&|d| d.colors.clear()));
    assert!(bad(&|d| d.colors = vec!["purple".into()]));
    assert!(bad(&|d| d.colors = vec!["red".into(), "red".into()]));
    assert!(bad(&|d| d.x = f64::NAN));
}

#[test]
fn the_wording_is_the_same_kind_on_every_sign() {
    // Plain words: no jargon on a sign a child reads. The set grows as the signs are written (BOSSMECH-SIGNS).
    let w = world();
    for (kind, def) in &w.signs {
        let all = format!("{} {} {}", def.what, def.todo, def.tip).to_lowercase();
        for word in [
            "aoe", "burst", "dps", "nerf", "die", "kill", "dead", "death",
        ] {
            assert!(
                !all.split(|c: char| !c.is_alphabetic()).any(|t| t == word),
                "{kind} uses `{word}`"
            );
        }
    }
}

#[test]
fn signs_stand_where_the_rules_say() {
    let w = world();
    for (zone, kind) in dungeons(&w) {
        let map = &w.maps[zone];
        let def = &w.signs[&kind];
        let at = Point { x: def.x, y: def.y };
        let boss = w
            .spawns
            .iter()
            .find(|s| s.zone == zone && s.kind == kind)
            .unwrap_or_else(|| panic!("{kind} has no spawn"));
        let boss_at = Point {
            x: boss.x,
            y: boss.y,
        };
        let n = map.size as usize;
        let grid = blocked_grid(map);
        let field = distance_field(map, &grid, map.spawn);
        let (cx, cy) = (at.x as usize, at.y as usize);
        // Free, reachable ground with open ground all round it.
        assert!(!grid[cy * n + cx], "{kind}: the sign stands in a wall");
        let steps = field[cy * n + cx];
        assert_ne!(steps, u16::MAX, "{kind}: a hero cannot reach the sign");
        for (dx, dy) in [
            (-1_i32, -1_i32),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        ] {
            let (x, y) = ((cx as i32 + dx) as usize, (cy as i32 + dy) as usize);
            assert!(
                !grid[y * n + x],
                "{kind}: the sign is wedged against a wall"
            );
        }
        // Never in the boss's room, and nearer the arrival point than the boss is.
        assert!(
            !map.rooms
                .iter()
                .any(|r| in_room(r, boss_at) && in_room(r, at)),
            "{kind}: the sign is in the boss's room"
        );
        if !map.rooms.is_empty() {
            assert!(
                map.rooms.iter().any(|r| in_room(r, at)),
                "{kind}: the sign is in no room"
            );
        }
        let boss_steps = (0..n * n)
            .filter(|&i| field[i] != u16::MAX)
            .min_by(|&a, &b| {
                let d = |i: usize| {
                    Point {
                        x: (i % n) as f64 + 0.5,
                        y: (i / n) as f64 + 0.5,
                    }
                    .distance(boss_at)
                };
                d(a).total_cmp(&d(b))
            })
            .map(|i| field[i])
            .unwrap();
        assert!(steps < boss_steps, "{kind}: the sign is behind the boss");
        // Reading it never wakes the boss: outside its awareness, plus a margin.
        let awareness = Slime::attack_profile(&kind).3;
        assert!(
            at.distance(boss_at) >= awareness + 2.,
            "{kind}: {:.1} tiles from the boss, awareness {awareness}",
            at.distance(boss_at)
        );
        // Away from every monster home and portal, and off the shortest walk to the boss.
        for s in w.spawns.iter().filter(|s| s.zone == zone) {
            assert!(
                at.distance(Point { x: s.x, y: s.y }) >= 3.,
                "{kind}: a {} stands by the sign",
                s.kind
            );
        }
        for p in &map.portals {
            assert!(
                at.distance(Point { x: p.x, y: p.y }) >= 3.,
                "{kind}: the portal {} is by the sign",
                p.id
            );
        }
        for npc in &map.npcs {
            assert!(
                at.distance(npc.position_at(0.)) >= 3.,
                "{kind}: {} is by the sign",
                npc.id
            );
        }
        let mut cell = (0..n * n)
            .filter(|&i| field[i] != u16::MAX)
            .min_by(|&a, &b| {
                let d = |i: usize| {
                    Point {
                        x: (i % n) as f64 + 0.5,
                        y: (i / n) as f64 + 0.5,
                    }
                    .distance(boss_at)
                };
                d(a).total_cmp(&d(b))
            })
            .unwrap();
        let mut route = vec![cell];
        while field[cell] > 0 {
            let (x, y) = ((cell % n) as i32, (cell / n) as i32);
            cell = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                .iter()
                .map(|(dx, dy)| ((y + dy) as usize) * n + (x + dx) as usize)
                .find(|&c| field[c] != u16::MAX && field[c] + 1 == field[cell])
                .expect("the walk back has a step");
            route.push(cell);
        }
        let near = route
            .iter()
            .map(|&i| {
                Point {
                    x: (i % n) as f64 + 0.5,
                    y: (i / n) as f64 + 0.5,
                }
                .distance(at)
            })
            .fold(f64::MAX, f64::min);
        assert!(
            near >= 2.2,
            "{kind}: the sign is {near:.1} tiles from the walked route"
        );
    }
}

/// The Undervault with one hero standing `distance` tiles west of the sign, and the king's mechanic in the table
/// when `mechanic` is true.
fn rig(distance: f64, live: bool) -> (World, tokio::sync::mpsc::Receiver<Value>, usize) {
    let mut w = world();
    if live {
        w.boss = BossMech::with_table(BTreeMap::from([("hollowking".to_string(), mechanic())]));
    } else {
        w.boss = BossMech::with_table(BTreeMap::new());
    }
    let zone = w
        .maps
        .iter()
        .position(|m| m.final_boss == "hollowking")
        .unwrap();
    w.enter_instance(zone);
    let mut rx = join(&mut w, 1, Class::Warrior);
    let def = w.signs["hollowking"].clone();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    (c.zone, c.x, c.y) = (zone, def.x - distance, def.y);
    c.hp = c.max_hp();
    drain(&mut rx);
    (w, rx, zone)
}
fn read(w: &mut World, sign: &str) {
    w.message(1, ClientMessage::SignRead { sign: sign.into() });
}

#[test]
fn the_snapshot_lists_a_sign_only_where_the_boss_has_a_mechanic() {
    let (w, _rx, zone) = rig(1., true);
    let view = w.snapshot_for(zone);
    let signs = view["signs"].as_array().expect("a sign is listed");
    assert_eq!(signs.len(), 1);
    assert_eq!(signs[0]["id"], "hollowking");
    assert_eq!(signs[0]["x"], w.signs["hollowking"].x);
    // The words are not in the snapshot.
    let text = signs[0].to_string();
    assert!(!text.contains(&w.signs["hollowking"].what), "{text}");
    assert!(view["signs"][0].get("tip").is_none());
    // No mechanic, no sign. Another zone never lists one.
    let (w2, _rx2, zone2) = rig(1., false);
    assert!(w2.snapshot_for(zone2).get("signs").is_none());
    assert!(w.snapshot_for(0).get("signs").is_none());
}

#[test]
fn reading_a_sign_answers_with_its_words_and_stops_the_hero() {
    let (mut w, mut rx, _) = rig(1.5, true);
    w.players.get_mut(&1).unwrap().attack = 1.;
    read(&mut w, "hollowking");
    let got = drain(&mut rx);
    let answer = got
        .iter()
        .find(|v| v["type"] == "sign")
        .expect("the sign answers");
    let def = &w.signs["hollowking"];
    assert_eq!(answer["title"], def.title.as_str());
    assert_eq!(answer["what"], def.what.as_str());
    assert_eq!(answer["todo"], def.todo.as_str());
    assert_eq!(answer["tip"], def.tip.as_str());
    assert_eq!(answer["colors"], json!(def.colors));
    assert_eq!(w.players[&1].attack, 0.);
    // Reading it again, as after a reload, gives the same words.
    read(&mut w, "hollowking");
    assert_eq!(
        drain(&mut rx)
            .iter()
            .filter(|v| v["type"] == "sign")
            .count(),
        1
    );
}

#[test]
fn a_sign_cannot_be_read_from_afar_when_defeated_or_by_a_wrong_name() {
    let refused = |w: &mut World, rx: &mut tokio::sync::mpsc::Receiver<Value>, sign: &str| {
        read(w, sign);
        let got = drain(rx);
        assert!(got.iter().all(|v| v["type"] != "sign"), "{got:?}");
        got.iter().any(|v| v["type"] == "error")
    };
    let (mut w, mut rx, _) = rig(bosssign::READ_RANGE + 0.5, true);
    assert!(refused(&mut w, &mut rx, "hollowking"), "too far");
    let (mut w, mut rx, _) = rig(1., true);
    assert!(
        refused(&mut w, &mut rx, "choirmother"),
        "another dungeon's sign"
    );
    assert!(refused(&mut w, &mut rx, ""), "no name");
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    assert!(refused(&mut w, &mut rx, "hollowking"), "defeated");
    // Not in a dungeon at all, and a dungeon whose boss has no mechanic yet.
    let (mut w, mut rx, _) = rig(1., true);
    w.players.get_mut(&1).unwrap().character.zone = 0;
    assert!(refused(&mut w, &mut rx, "hollowking"), "outside");
    let (mut w, mut rx, _) = rig(1., false);
    assert!(refused(&mut w, &mut rx, "hollowking"), "no mechanic yet");
}

#[test]
fn chests_keep_clear_of_the_sign() {
    let (mut w, _rx, zone) = rig(1., true);
    // Put the sign where a chest would go, then ask for many chests: none may land within three tiles of it.
    let first = w.chest_spot(zone).expect("a chest spot in the Undervault");
    let sign = w.signs.get_mut("hollowking").unwrap();
    (sign.x, sign.y) = (first.x, first.y);
    let mut placed = 0;
    for _ in 0..4000 {
        if let Some(spot) = w.chest_spot(zone) {
            placed += 1;
            assert!(
                spot.distance(first) >= 3.,
                "a chest at {spot:?} is by the sign at {first:?}"
            );
        }
    }
    assert!(placed > 1000, "chests still get placed ({placed})");
}
