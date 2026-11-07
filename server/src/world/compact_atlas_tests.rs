//! Organic reference geography and authoritative walking crossings; no encounter simulation.
use super::wyrd_tests::{at, calm, join, place, world};
use super::*;

fn bundled() -> Value {
    serde_json::from_str(include_str!("../../../world/map.txt")).unwrap()
}

#[test]
fn compact_atlas_city_walkways_align_with_streets_and_real_wall_openings() {
    let w = world();
    let data = bundled();
    let mut checked = 0;
    for zone in [0, 4, 9, 17] {
        let z = if zone == 0 {
            &data
        } else {
            &data["zones"][zone - 1]
        };
        let entrances = z["cityEntrances"].as_array().unwrap();
        assert_eq!(
            entrances.len(),
            match zone {
                0 => 2,
                4 => 4,
                9 => 5,
                _ => 1,
            }
        );
        for e in entrances {
            let points = e["points"].as_array().unwrap();
            let point = |p: &Value| at(p[0].as_f64().unwrap(), p[1].as_f64().unwrap());
            // (Skaldholm's portal stands just beyond the arch line, on the neighbour's side: its path starts on the ground.)
            for pair in points.windows(2).skip(usize::from(zone == 4)) {
                assert!(
                    w.maps[zone].line_clear(point(&pair[0]), point(&pair[1]), 1.2),
                    "blocked city entry {zone}:{}",
                    e["id"]
                );
            }
            let vertical = e["axis"] == "y";
            let street = e["street"].as_f64().unwrap();
            if zone == 0 {
                assert_eq!(street, z["city"]["plaza"]["x"].as_f64().unwrap());
            } else if zone != 4 {
                // Match original streets, excluding paving created by this overlay.
                assert!(
                    z["roads"].as_array().unwrap().iter().any(|r| {
                        if r.get("cityEntry").is_some() {
                            return false;
                        }
                        let Some(x0) = r["x0"].as_f64() else {
                            return false;
                        };
                        let (x1, y0, y1) = (
                            r["x1"].as_f64().unwrap(),
                            r["y0"].as_f64().unwrap(),
                            r["y1"].as_f64().unwrap(),
                        );
                        let (across, along, centre) = if vertical {
                            (x1 - x0, y1 - y0, (x0 + x1) / 2.)
                        } else {
                            (y1 - y0, x1 - x0, (y0 + y1) / 2.)
                        };
                        along > 30. && across >= 4. && (centre - street).abs() < 0.001
                    }),
                    "entry misses a real city street: {zone}:{}",
                    e["id"]
                );
            }
            if let Some(id) = e["portal"].as_str() {
                let portal = w.maps[zone].portals.iter().find(|p| p.id == id).unwrap();
                assert_eq!(point(&points[0]), at(portal.x, portal.y));
                if zone != 4 {
                    assert_eq!(if vertical { portal.x } else { portal.y }, street);
                }
                let back = w.maps[portal.to]
                    .portals
                    .iter()
                    .find(|p| p.to == zone)
                    .unwrap();
                assert!(zone == 4 || at(back.tx, back.ty).distance(at(portal.x, portal.y)) >= 5.9);
                assert!(w.maps[zone].line_clear(at(back.tx, back.ty), point(&points[1]), 1.2));
            }
            // Skaldholm (zone 4) has no wall of its own since the rebuild: its doors are the neighbours' vaults (zone_shape_tests).
            if let Some(opening) = e.get("opening").filter(|_| zone != 4) {
                let (x, y) = (
                    opening["x"].as_f64().unwrap(),
                    opening["y"].as_f64().unwrap(),
                );
                let side = opening["vertical"].as_bool().unwrap();
                let half = opening["halfWidth"].as_f64().unwrap();
                assert_eq!(if side { y } else { x }, street);
                let n = if side { at(1., 0.) } else { at(0., 1.) };
                let outer = if zone == 0 && y == 94. { 1. } else { 3. };
                assert!(w.maps[zone].line_clear(
                    at(x - n.x * 3., y - n.y * 3.),
                    at(x + n.x * outer, y + n.y * outer),
                    1.2
                ));
                let beside = at(x + n.y * (half + 1.), y + n.x * (half + 1.));
                assert!(!w.maps[zone].line_clear(
                    at(beside.x - n.x * 3., beside.y - n.y * 3.),
                    at(beside.x + n.x * 3., beside.y + n.y * 3.),
                    PLAYER_RADIUS
                ));
            }
            checked += 1;
        }
    }
    assert_eq!(checked, 12);
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
fn compact_atlas_bifrost_platform_edges_and_void_are_solid() {
    let data = bundled();
    let sky = &data["zones"][6];
    let rows: Vec<_> = sky["sky"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r.as_str().unwrap().as_bytes())
        .collect();
    let floor = |p: Point| {
        rows.get(p.y.floor() as usize)
            .and_then(|r| r.get(p.x.floor() as usize))
            .is_some_and(|c| *c != b' ')
    };
    let mut w = world();
    calm(&mut w);
    let map = &w.maps[7];
    let mut edges = 0;
    for y in 1..map.size as usize - 1 {
        for x in 1..map.size as usize - 1 {
            let start = at(x as f64 + 0.5, y as f64 + 0.5);
            if !floor(start) {
                assert!(
                    !map.line_clear(start, start, 0.),
                    "unblocked empty sky {start:?}"
                );
                continue;
            }
            let mut clear_start = start;
            map.collide(&mut clear_start, PLAYER_RADIUS);
            if clear_start.distance(start) > 1e-8 {
                continue;
            }
            for dir in [at(-1., 0.), at(1., 0.), at(0., -1.), at(0., 1.)] {
                if floor(at(start.x + dir.x, start.y + dir.y)) {
                    continue;
                }
                let mut foot = start;
                for _ in 0..10 {
                    map.walk(&mut foot, dir, 0.2, PLAYER_RADIUS);
                    assert!(
                        floor(foot),
                        "walk off island {start:?} toward {dir:?}: {foot:?}"
                    );
                }
                let mut dash = start;
                map.walk(&mut dash, dir, 12., PLAYER_RADIUS);
                assert!(
                    floor(dash),
                    "dash off island {start:?} toward {dir:?}: {dash:?}"
                );
                edges += 1;
            }
        }
    }
    assert!(
        edges > 400,
        "checked exposed island and bridge edges: {edges}"
    );
    let _rx = join(&mut w, 1, Class::Warrior);
    // Along the rim of every updraft pad (both ways at right angles to its gate), outside the gate's trigger.
    let mut sweeps = vec![];
    for g in sky["portals"].as_array().unwrap() {
        let Some(side) = g["walk"].as_array() else {
            continue;
        };
        let (wx, wy) = (side[0].as_f64().unwrap(), side[1].as_f64().unwrap());
        let (gx, gy) = (g["x"].as_f64().unwrap(), g["y"].as_f64().unwrap());
        for sign in [-1., 1.] {
            sweeps.push((at(gx - wx * 5., gy - wy * 5.), at(-wy * sign, wx * sign)));
        }
    }
    assert_eq!(sweeps.len(), 8);
    for (start, dir) in sweeps {
        place(&mut w, 1, 7, start);
        for _ in 0..40 {
            w.time += TICK;
            let hero = w.players.get_mut(&1).unwrap();
            hero.input = dir;
            hero.input_at = w.time;
            w.update_player(1);
            assert_eq!(w.players[&1].character.zone, 7);
            assert!(
                floor(w.players[&1].character.point()),
                "held movement leaves platform from {start:?}"
            );
        }
    }
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
            if z["cityEntrances"]
                .as_array()
                .is_some_and(|entries| entries.iter().any(|e| e["points"] == *path))
            {
                // City approaches join the existing street network rather than
                // following the perimeter back to the old default spawn.
                let city = &z["city"];
                assert!(
                    actual.x > city["x0"].as_f64().unwrap()
                        && actual.x < city["x1"].as_f64().unwrap()
                );
                assert!(
                    actual.y > city["y0"].as_f64().unwrap()
                        && actual.y < city["y1"].as_f64().unwrap()
                );
            } else {
                assert!(actual.distance(m.spawn) < 1.5);
            }
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

#[test]
fn compact_atlas_city_archways_and_nacre_alcove_are_walkable() {
    let data = bundled();
    let mut w = world();
    calm(&mut w);
    let city = &w.maps[4];
    let arches = data["zones"][3]["exitArches"].as_array().unwrap();
    assert_eq!(arches.len(), 4);
    for arch in arches {
        let x = arch["x"].as_f64().unwrap();
        let y = arch["y"].as_f64().unwrap();
        // The doorway is on the city's ground edge: the street runs in from it, solid void lies beyond (the neighbour's vault takes over).
        let id = arch["portal"].as_str().unwrap();
        let portal = city.portals.iter().find(|p| p.id == id).unwrap();
        let w_ = portal.walk.unwrap();
        let inward = at(-f64::from(w_[0]), -f64::from(w_[1]));
        assert!(city.line_clear(
            at(x + inward.x * 4., y + inward.y * 4.),
            at(x + inward.x * 1.5, y + inward.y * 1.5),
            PLAYER_RADIUS
        ));
        assert!(!city.line_clear(
            at(x + inward.x * 1.5, y + inward.y * 1.5),
            at(x - inward.x * 4., y - inward.y * 4.),
            PLAYER_RADIUS
        ));
    }
    let gate = w.maps[7]
        .portals
        .iter()
        .find(|p| p.to == 9)
        .unwrap()
        .clone();
    // the Nacrehold updraft stands on its own pad in the south-east (the shapes pilot), six tiles from where Nacrehold sends you
    assert_eq!((gate.x, gate.y), (330.8, 300.0));
    let back = w.maps[9].portals.iter().find(|p| p.to == 7).unwrap();
    assert_eq!((back.tx, back.ty), (gate.x - 6., gate.y));
    assert!(w.maps[7].line_clear(
        at(gate.x - 6., gate.y),
        at(gate.x - 1., gate.y),
        PLAYER_RADIUS
    ));
    let _rx = join(&mut w, 1, Class::Warrior);
    // passing along the pad, at right angles to the gate, must not travel
    place(&mut w, 1, 7, at(gate.x - 5., gate.y - 4.));
    for _ in 0..40 {
        w.time += TICK;
        let p = w.players.get_mut(&1).unwrap();
        p.input = at(0., 1.);
        p.input_at = w.time;
        w.update_player(1);
        assert_eq!(
            w.players[&1].character.zone, 7,
            "passing along the pad must not travel"
        );
    }
    assert!(w.players[&1].character.y > gate.y + 1.);
    for (zone, map) in std::iter::once(&data)
        .chain(data["zones"].as_array().unwrap())
        .enumerate()
    {
        for route in map["exitRoutes"].as_array().into_iter().flatten() {
            let points = route["points"].as_array().unwrap();
            assert!(points.len() >= 2);
            for pair in points.windows(2) {
                let p = |v: &Value| at(v[0].as_f64().unwrap(), v[1].as_f64().unwrap());
                assert!(
                    w.maps[zone].line_clear(p(&pair[0]), p(&pair[1]), PLAYER_RADIUS),
                    "exit paving must follow clear floor in zone {zone}"
                );
            }
        }
    }
}
