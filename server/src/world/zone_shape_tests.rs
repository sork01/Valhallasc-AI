//! Zones with the outline of their province on the atlas (docs/zone-shapes.md): the walkable land is the outline.
use super::wyrd_tests::{at, join, place, world};
use super::*;

const SHAPED: [usize; 2] = [0, 1];

fn bundled() -> Value {
    serde_json::from_str(include_str!("../../../world/map.txt")).unwrap()
}

fn zone_of(data: &Value, zone: usize) -> &Value {
    if zone == 0 {
        data
    } else {
        &data["zones"][zone - 1]
    }
}

fn land(z: &Value) -> impl Fn(f64, f64) -> bool + '_ {
    let rows = z["shapeFloor"].as_array().unwrap();
    move |x, y| {
        rows.get(y.floor().max(0.) as usize)
            .and_then(|r| r.as_str().unwrap().as_bytes().get(x.floor().max(0.) as usize))
            == Some(&b'#')
    }
}

#[test]
fn shaped_zones_keep_all_content_on_land_and_the_edge_stops_walkers() {
    let w = world();
    let data = bundled();
    for zone in SHAPED {
        let z = zone_of(&data, zone);
        let n = z["size"].as_u64().unwrap() as usize;
        assert_eq!(n % 8, 0, "whole ground chunks");
        assert_eq!(z["shapeFloor"].as_array().unwrap().len(), n);
        assert_eq!(w.maps[zone].size as usize, n);
        let on_land = land(z);
        assert!(on_land(z["spawn"]["x"].as_f64().unwrap(), z["spawn"]["y"].as_f64().unwrap()));
        for key in ["slimes", "npcs", "places", "crosses", "portals"] {
            for o in z[key].as_array().unwrap() {
                if o.get("seam").is_some() {
                    continue; // a border line, not a place on the land
                }
                let (x, y) = (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
                assert!(on_land(x, y), "zone {zone} {key} {} at ({x},{y}) is off the land", o["id"]);
            }
        }
        // Walk outward from every few land cells that touch the edge: the walker must stay on land.
        let rows: Vec<&[u8]> = z["shapeFloor"].as_array().unwrap().iter().map(|r| r.as_str().unwrap().as_bytes()).collect();
        let mut tested = 0;
        // Along a seam the land runs a margin past the line on purpose (the server moves a walker who steps over it).
        let seam: Vec<(f64, f64)> = z["portals"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|p| p.get("seam"))
            .flat_map(|s| s["points"].as_array().unwrap().iter().map(|q| (q[0].as_f64().unwrap(), q[1].as_f64().unwrap())))
            .collect();
        for y in 1..n - 1 {
            for x in 1..n - 1 {
                if rows[y][x] != b'#' {
                    continue;
                }
                for (dx, dy) in [(1i32, 0i32), (-1, 0), (0, 1), (0, -1)] {
                    let (nx, ny) = ((x as i32 + dx) as usize, (y as i32 + dy) as usize);
                    if rows[ny][nx] == b'#' || (x * 7 + y * 13) % 11 != 0 {
                        continue;
                    }
                    if seam.iter().any(|q| (q.0 - x as f64).hypot(q.1 - y as f64) < 30.) {
                        continue; // near a seam border (the line's vertices are up to ~30 tiles apart)
                    }
                    let mut p = at(x as f64 + 0.5, y as f64 + 0.5);
                    w.maps[zone].walk(&mut p, at(dx as f64, dy as f64), 4.0, 0.4);
                    assert!(on_land(p.x, p.y), "zone {zone}: walked off the land from ({x},{y}) toward ({dx},{dy}) to ({:.1},{:.1})", p.x, p.y);
                    tested += 1;
                }
            }
        }
        assert!(tested > 40, "zone {zone}: only {tested} edge walks");
    }
}

#[test]
fn shaped_zones_cross_into_each_other_on_their_shared_border() {
    let w = world();
    let data = bundled();
    for zone in SHAPED {
        let z = zone_of(&data, zone);
        let edges = z["shape"]["edges"].as_array().unwrap();
        let mut border = 0;
        for p in z["portals"].as_array().unwrap() {
            if p.get("seam").is_some() {
                continue; // a border you cross anywhere: see the next test
            }
            let to = p["to"].as_u64().unwrap() as usize;
            let chain: Vec<&Value> = edges.iter().filter(|e| e["kind"] == "shared" && e["other"] == to).collect();
            if chain.is_empty() {
                continue;
            }
            border += 1;
            let (x, y) = (p["x"].as_f64().unwrap(), p["y"].as_f64().unwrap());
            let d = chain
                .iter()
                .flat_map(|e| e["points"].as_array().unwrap().iter())
                .map(|q| ((q[0].as_f64().unwrap() - x).powi(2) + (q[1].as_f64().unwrap() - y).powi(2)).sqrt())
                .fold(f64::MAX, f64::min);
            assert!(d < 16., "zone {zone} portal {} is {d:.1} tiles from its shared border", p["id"]);
            // the arrival in the neighbour is free ground there
            let (tx, ty) = (p["tx"].as_f64().unwrap(), p["ty"].as_f64().unwrap());
            let mut a = at(tx, ty);
            w.maps[to].collide(&mut a, 0.4);
            assert!((a.x - tx).hypot(a.y - ty) < 0.01, "arrival ({tx:.1},{ty:.1}) in zone {to} is inside an obstacle");
        }
        assert!(border >= 2, "zone {zone}: only {border} gate crossings");
    }
}

/// Walk from 3 tiles inside zone `from` straight at its shared border: the hero must end up on land in `to`.
fn cross(w: &mut World, data: &Value, from: usize, to: usize, q: Point, inward: Point) -> Point {
    let start = at(q.x + inward.x * 3., q.y + inward.y * 3.);
    place(w, 1, from, start);
    let dir = at(-inward.x, -inward.y);
    for _ in 0..80 {
        w.time += TICK;
        let hero = w.players.get_mut(&1).unwrap();
        hero.input = dir;
        hero.input_at = w.time;
        w.update_player(1);
        if w.players[&1].character.zone == to {
            break;
        }
    }
    let p = w.players[&1].character.clone();
    assert_eq!(p.zone, to, "walking at the border from {start:?} did not cross into zone {to}");
    // The arrival is just inside the border line, which can fall in a margin cell (the raster is whole cells): within a tile of land.
    let on_land = land(zone_of(data, to));
    assert!(
        [(0., 0.), (1., 0.), (-1., 0.), (0., 1.), (0., -1.), (1., 1.), (-1., -1.), (1., -1.), (-1., 1.)].iter().any(|(dx, dy)| on_land(p.x + dx, p.y + dy)),
        "arrived far off the land in zone {to} at ({:.1},{:.1})",
        p.x,
        p.y
    );
    at(p.x, p.y)
}

#[test]
fn a_shared_border_is_crossed_anywhere_along_it_in_both_directions() {
    let mut w = world();
    let data = bundled();
    let _rx = join(&mut w, 1, Class::Warrior);
    let (a, b) = (zone_of(&data, 0), zone_of(&data, 1));
    let seam = a["portals"].as_array().unwrap().iter().find_map(|p| p.get("seam")).expect("the meadow has a seam to the Crags");
    let points: Vec<Point> = seam["points"].as_array().unwrap().iter().map(|q| at(q[0].as_f64().unwrap(), q[1].as_f64().unwrap())).collect();
    let on_a = land(a);
    let mut crossed = 0;
    // Samples along every border segment: the point 4 tiles inside the meadow, found from the side that is land.
    for pair in points.windows(2) {
        for t in [0.25, 0.5, 0.75] {
            let q = at(pair[0].x + (pair[1].x - pair[0].x) * t, pair[0].y + (pair[1].y - pair[0].y) * t);
            let (dx, dy) = (pair[1].x - pair[0].x, pair[1].y - pair[0].y);
            let len = dx.hypot(dy);
            if len < 6. {
                continue;
            }
            let normal = at(-dy / len, dx / len);
            let inward = if on_a(q.x + normal.x * 4., q.y + normal.y * 4.) { normal } else { at(-normal.x, -normal.y) };
            if !on_a(q.x + inward.x * 4., q.y + inward.y * 4.) {
                continue;
            }
            let landed = cross(&mut w, &data, 0, 1, q, inward);
            crossed += 1;
            // and back from where we arrived: straight at the same border again
            let shift = (seam["shift"][0].as_f64().unwrap(), seam["shift"][1].as_f64().unwrap());
            let q_in_b = at(q.x + shift.0, q.y + shift.1);
            let _back = cross(&mut w, &data, 1, 0, q_in_b, at(-inward.x, -inward.y));
            assert!(landed.distance(q_in_b) < 4., "the crossing is continuous: arrived {:.1} tiles from the mirrored spot", landed.distance(q_in_b));
            let _ = b;
        }
    }
    assert!(crossed >= 8, "only {crossed} border samples crossed");
}
