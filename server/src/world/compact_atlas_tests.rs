//! Organic reference geography and authoritative walking crossings; no encounter simulation.
use super::wyrd_tests::{at, calm, join, place, world};
use super::*;

fn bundled() -> Value {
    serde_json::from_str(include_str!("../../../world/map.txt")).unwrap()
}
fn routes(data: &Value) -> Vec<(usize, usize)> {
    let mut pairs: Vec<_> = data["atlas"]["links"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| {
            (
                p["a"].as_u64().unwrap() as usize,
                p["b"].as_u64().unwrap() as usize,
            )
        })
        .collect();
    pairs.push((17, 19));
    pairs
}

#[test]
fn compact_atlas_bifrost_arrivals_and_approaches_stay_on_visible_floor() {
    let data = bundled();
    let sky = &data["zones"][6];
    let floor = |p: Point| {
        for (dx, dy) in [(0., 0.), (0.38, 0.), (-0.38, 0.), (0., 0.38), (0., -0.38)] {
            let x = (p.x + dx).floor() as usize;
            let y = (p.y + dy).floor() as usize;
            assert_ne!(
                sky["sky"][y].as_str().unwrap().as_bytes()[x],
                b' ',
                "Bifrost route has no visible floor at {p:?}"
            );
        }
    };
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    for from in [1, 6, 8, 9] {
        let gate = w.maps[from]
            .portals
            .iter()
            .find(|p| p.to == 7)
            .unwrap()
            .clone();
        floor(at(gate.tx, gate.ty));
        let side = gate.walk.unwrap();
        let dir = at(f64::from(side[0]), f64::from(side[1]));
        w.players.get_mut(&1).unwrap().stop();
        place(
            &mut w,
            1,
            from,
            at(gate.x - dir.x * 4., gate.y - dir.y * 4.),
        );
        w.time += PORTAL_DELAY + 1.;
        for _ in 0..40 {
            w.time += TICK;
            let hero = w.players.get_mut(&1).unwrap();
            hero.input = dir;
            hero.input_at = w.time;
            w.update_player(1);
            if w.players[&1].character.zone == 7 {
                break;
            }
        }
        assert_eq!(w.players[&1].character.zone, 7, "crossing from {from}");
        for _ in 0..20 {
            floor(w.players[&1].character.point());
            w.time += TICK;
            w.update_player(1);
        }
    }
    for path in sky["atlasPaths"].as_array().unwrap() {
        for segment in path.as_array().unwrap().windows(2) {
            let point = |v: &Value| at(v[0].as_f64().unwrap(), v[1].as_f64().unwrap());
            let a = point(&segment[0]);
            let b = point(&segment[1]);
            let steps = (a.distance(b) * 4.).ceil().max(1.) as usize;
            for i in 0..=steps {
                let f = i as f64 / steps as f64;
                floor(at(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f));
            }
        }
    }
}

#[test]
fn compact_atlas_organic_provinces_and_every_walking_approach_are_safe() {
    let w = world();
    let data = bundled();
    let atlas = &data["atlas"];
    assert_eq!(atlas["regions"].as_array().unwrap().len(), 23);
    assert_eq!(atlas["width"], 2048);
    assert_eq!(atlas["height"], 1041);
    assert!(
        atlas["regions"]
            .as_array()
            .unwrap()
            .iter()
            .all(|r| r["polygon"].as_array().unwrap().len() > 8)
    );
    assert!(
        atlas["cities"]
            .as_array()
            .unwrap()
            .iter()
            .any(|c| c["zone"] == 17 && c["parent"] == 19)
    );
    assert!(
        atlas["cities"]
            .as_array()
            .unwrap()
            .iter()
            .any(|c| c["zone"] == 23 && c["parent"] == 23)
    );
    assert!(
        !atlas["regions"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r["zone"] == 17)
    );
    let pairs = routes(&data);
    assert_eq!(pairs.len(), 48);
    let mut count = 0;
    for (i, j) in pairs.iter().flat_map(|&(i, j)| [(i, j), (j, i)]) {
        let m = &w.maps[i];
        let p = m.portals.iter().find(|p| p.to == j).unwrap();
        let side = p
            .walk
            .expect("outdoor route must be an ordinary walking path");
        let back = w.maps[j].portals.iter().find(|p| p.to == i).unwrap();
        assert_eq!(back.walk, Some([-side[0], -side[1]]));
        assert!((p.tx - (back.x + f64::from(side[0]) * 6.)).abs() < 1e-8);
        assert!((p.ty - (back.y + f64::from(side[1]) * 6.)).abs() < 1e-8);
        for (map, point) in [(m, at(p.x, p.y)), (&w.maps[j], at(p.tx, p.ty))] {
            let mut actual = point;
            map.collide(&mut actual, PLAYER_RADIUS);
            assert!(actual.distance(point) < 1e-8, "collision {i}->{j}");
            assert!(
                map.slimes
                    .iter()
                    .all(|s| point.distance(at(s.x, s.y)) >= 8.),
                "spawn {i}->{j}"
            );
        }
        assert!(
            w.maps[j]
                .portals
                .iter()
                .all(|q| at(p.tx, p.ty).distance(at(q.x, q.y)) > q.r + PLAYER_RADIUS),
            "bounce {i}->{j}"
        );
        assert!(w.maps[j].line_clear(at(p.tx, p.ty), at(back.x, back.y), PLAYER_RADIUS));
        count += 1;
    }
    assert_eq!(count, 96);
    for (i, m) in w.maps.iter().enumerate().take(47) {
        let z = if i == 0 { &data } else { &data["zones"][i - 1] };
        let Some(paths) = z["atlasPaths"].as_array() else {
            continue;
        };
        for path in paths {
            let points: Vec<_> = path
                .as_array()
                .unwrap()
                .iter()
                .map(|p| at(p[0].as_f64().unwrap(), p[1].as_f64().unwrap()))
                .collect();
            let mut actual = points[0];
            for &next in points.iter().skip(1) {
                let distance = actual.distance(next);
                let direction = actual.direction(next);
                for portal in &m.portals {
                    let gate = at(portal.x, portal.y);
                    if points[0].distance(gate) < 0.01 {
                        continue;
                    }
                    let along = ((gate.x - actual.x) * direction.x
                        + (gate.y - actual.y) * direction.y)
                        .clamp(0., distance);
                    let closest = at(
                        actual.x + direction.x * along,
                        actual.y + direction.y * along,
                    );
                    assert!(
                        closest.distance(gate) >= portal.r + PLAYER_RADIUS,
                        "approach {i} crosses {}",
                        portal.id
                    );
                }
                m.walk(&mut actual, direction, distance, PLAYER_RADIUS);
                assert!(actual.distance(next) < 0.01, "walking approach {i}");
            }
            assert!(actual.distance(m.spawn) < 1.5);
        }
    }
}

#[test]
fn compact_atlas_all_96_paths_really_cross_and_keep_held_movement() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    for (i, j) in routes(&bundled())
        .iter()
        .flat_map(|&(i, j)| [(i, j), (j, i)])
    {
        let p = w.maps[i]
            .portals
            .iter()
            .find(|p| p.to == j)
            .unwrap()
            .clone();
        let side = p.walk.unwrap();
        let dir = at(f64::from(side[0]), f64::from(side[1]));
        w.players.get_mut(&1).unwrap().stop();
        place(&mut w, 1, i, at(p.x - dir.x * 4., p.y - dir.y * 4.));
        w.time += PORTAL_DELAY + 1.;
        for _ in 0..40 {
            w.time += TICK;
            let hero = w.players.get_mut(&1).unwrap();
            hero.input = dir;
            hero.input_at = w.time;
            w.update_player(1);
            if w.players[&1].character.zone == j {
                break;
            }
        }
        assert_eq!(w.players[&1].character.zone, j, "path {}", p.id);
        assert!(
            w.players[&1].character.point().distance(at(p.tx, p.ty)) < 1e-8,
            "arrival {}",
            p.id
        );
        assert_eq!(w.players[&1].input, dir, "held input continues {}", p.id);
        let before = w.players[&1].character.point();
        w.time += TICK;
        w.update_player(1);
        let after = w.players[&1].character.point();
        assert!(
            (after.x - before.x) * dir.x + (after.y - before.y) * dir.y > 0.,
            "keeps walking {}",
            p.id
        );
    }
}

#[test]
fn compact_atlas_paths_do_not_take_idle_or_inward_fighters_and_click_goals_continue() {
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    let p = w.maps[0]
        .portals
        .iter()
        .find(|p| p.walk.is_some())
        .unwrap()
        .clone();
    let side = p.walk.unwrap();
    let dir = at(f64::from(side[0]), f64::from(side[1]));
    place(&mut w, 1, 0, at(p.x, p.y));
    w.time += PORTAL_DELAY + 1.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 0);
    {
        let hero = w.players.get_mut(&1).unwrap();
        hero.input = at(-dir.x, -dir.y);
        hero.moving = true;
    }
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 0);
    w.players.get_mut(&1).unwrap().stop();
    place(&mut w, 1, 0, at(p.x - dir.x * 4., p.y - dir.y * 4.));
    w.message(
        1,
        ClientMessage::Move {
            x: p.x + dir.x * 3.,
            y: p.y + dir.y * 3.,
        },
    );
    while rx.try_recv().is_ok() {}
    for _ in 0..40 {
        w.time += TICK;
        w.update_player(1);
        if w.players[&1].character.zone == p.to {
            break;
        }
    }
    assert_eq!(w.players[&1].character.zone, p.to);
    assert!(w.players[&1].goal.is_some());
    let before = w.players[&1].character.point();
    w.time += TICK;
    w.update_player(1);
    assert!(w.players[&1].character.point().distance(before) > 0.);
    let events: Vec<_> = std::iter::from_fn(|| rx.try_recv().ok()).collect();
    assert!(
        events.iter().all(|v| v["kind"] != "portal"),
        "ordinary paths have no teleport flare"
    );
    assert!(events.iter().any(|v| {
        v["text"]
            .as_str()
            .is_some_and(|s| s.starts_with("You enter "))
    }));
}

#[test]
fn compact_atlas_keeps_all_keys_private_doors_and_spark_links_match_crossings() {
    let w = world();
    for (zone, id, key) in [
        (6, "wyrd_nornroot", "entry_norn"),
        (17, "asterion_moonwell_stairs", "entry_moon"),
        (25, "lapis_astrolabe_gate", "entry_astro"),
        (28, "year_solstice_descent", "entry_solstice"),
        (28, "year_blackhour", "null_keys"),
        (45, "ew_raid", "raid_key"),
    ] {
        let p = w.maps[zone].portals.iter().find(|p| p.id == id).unwrap();
        assert_eq!(p.needs_quest.as_deref(), Some(key));
        assert!(p.walk.is_none());
        assert!(w.maps[p.to].copies > 0 && w.maps[p.to].min_level > 0);
    }
    let masters: std::collections::HashMap<_, _> = w
        .maps
        .iter()
        .enumerate()
        .take(47)
        .flat_map(|(i, m)| {
            m.npcs
                .iter()
                .filter(|n| n.travel_stop.is_some())
                .map(move |n| (n.id.clone(), (i, n)))
        })
        .collect();
    for (id, (zone, n)) in &masters {
        for other in &n.travel_links {
            let (to, b) = masters.get(other).unwrap();
            assert!(b.travel_links.contains(id));
            assert!(
                zone == to || w.maps[*zone].portals.iter().any(|p| p.to == *to),
                "flight {id}->{other} needs a real crossing"
            );
        }
    }
}
