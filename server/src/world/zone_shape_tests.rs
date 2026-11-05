//! Zones with the outline of their province on the atlas (docs/zone-shapes.md): the walkable land is the outline.
use super::wyrd_tests::{at, world};
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
                let (x, y) = (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
                assert!(on_land(x, y), "zone {zone} {key} {} at ({x},{y}) is off the land", o["id"]);
            }
        }
        // Walk outward from every few land cells that touch the edge: the walker must stay on land.
        let rows: Vec<&[u8]> = z["shapeFloor"].as_array().unwrap().iter().map(|r| r.as_str().unwrap().as_bytes()).collect();
        let mut tested = 0;
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
        assert!(border >= 4, "zone {zone}: only {border} border crossings");
    }
}
