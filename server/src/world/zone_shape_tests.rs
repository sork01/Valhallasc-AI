//! Zones with the outline of their province on the atlas (docs/zone-shapes.md): the walkable land is the outline.
use super::wyrd_tests::{at, join, place, world};
use super::*;

const SHAPED: [usize; 5] = [0, 1, 2, 3, 16];

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
        rows.get(y.floor().max(0.) as usize).and_then(|r| {
            r.as_str()
                .unwrap()
                .as_bytes()
                .get(x.floor().max(0.) as usize)
        }) == Some(&b'#')
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
        assert!(on_land(
            z["spawn"]["x"].as_f64().unwrap(),
            z["spawn"]["y"].as_f64().unwrap()
        ));
        for key in ["slimes", "npcs", "places", "crosses", "portals"] {
            for o in z[key].as_array().into_iter().flatten() {
                if o.get("seam").is_some() {
                    continue; // a border line, not a place on the land
                }
                let (x, y) = (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
                assert!(
                    on_land(x, y),
                    "zone {zone} {key} {} at ({x},{y}) is off the land",
                    o["id"]
                );
            }
        }
        // Walk outward from every few land cells that touch the edge: the walker must stay on land.
        let rows: Vec<&[u8]> = z["shapeFloor"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r.as_str().unwrap().as_bytes())
            .collect();
        let mut tested = 0;
        // Along a seam the land runs a margin past the line on purpose (the server moves a walker who steps over it).
        let seam: Vec<(f64, f64)> = z["portals"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|p| p.get("seam"))
            .flat_map(|s| {
                s["points"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|q| (q[0].as_f64().unwrap(), q[1].as_f64().unwrap()))
            })
            .collect();
        // Skaldholm's wall stands 1.6 tiles inside its borders: the strip behind it is not a place to walk from.
        let wall: Vec<(f64, f64)> = z["objects"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|o| o["kind"] == "rampart" || o["kind"] == "tower")
            .map(|o| (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap()))
            .collect();
        for y in 1..n - 1 {
            for x in 1..n - 1 {
                if rows[y][x] != b'#' {
                    continue;
                }
                if wall
                    .iter()
                    .any(|q| (q.0 - x as f64).hypot(q.1 - y as f64) < 4.)
                {
                    continue;
                }
                for (dx, dy) in [(1i32, 0i32), (-1, 0), (0, 1), (0, -1)] {
                    let (nx, ny) = ((x as i32 + dx) as usize, (y as i32 + dy) as usize);
                    if rows[ny][nx] == b'#' || (x * 7 + y * 13) % 11 != 0 {
                        continue;
                    }
                    if seam
                        .iter()
                        .any(|q| (q.0 - x as f64).hypot(q.1 - y as f64) < 30.)
                    {
                        continue; // near a seam border (the line's vertices are up to ~30 tiles apart)
                    }
                    let mut p = at(x as f64 + 0.5, y as f64 + 0.5);
                    w.maps[zone].walk(&mut p, at(dx as f64, dy as f64), 4.0, 0.4);
                    assert!(
                        on_land(p.x, p.y),
                        "zone {zone}: walked off the land from ({x},{y}) toward ({dx},{dy}) to ({:.1},{:.1})",
                        p.x,
                        p.y
                    );
                    tested += 1;
                }
            }
        }
        // (Gloamfen has seams on two sides and a wall on a third: little plain edge is left)
        assert!(tested > 20, "zone {zone}: only {tested} edge walks");
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
            let chain: Vec<&Value> = edges
                .iter()
                .filter(|e| e["kind"] == "shared" && e["other"] == to)
                .collect();
            if chain.is_empty() {
                continue;
            }
            border += 1;
            if p.get("vault").is_some() {
                continue; // stands on the straight wall line, not the leaning border: the vault tests cover it
            }
            let (x, y) = (p["x"].as_f64().unwrap(), p["y"].as_f64().unwrap());
            let d = chain
                .iter()
                .flat_map(|e| e["points"].as_array().unwrap().iter())
                .map(|q| {
                    ((q[0].as_f64().unwrap() - x).powi(2) + (q[1].as_f64().unwrap() - y).powi(2))
                        .sqrt()
                })
                .fold(f64::MAX, f64::min);
            assert!(
                d < 16.,
                "zone {zone} portal {} is {d:.1} tiles from its shared border",
                p["id"]
            );
            // the arrival in the neighbour is free ground there
            let (tx, ty) = (p["tx"].as_f64().unwrap(), p["ty"].as_f64().unwrap());
            let mut a = at(tx, ty);
            w.maps[to].collide(&mut a, 0.4);
            assert!(
                (a.x - tx).hypot(a.y - ty) < 0.01,
                "arrival ({tx:.1},{ty:.1}) in zone {to} is inside an obstacle"
            );
        }
        // the meadow's and Gloamfen's other borders are seams now: only Skaldholm is a gate
        let wanted = if zone == 0 || zone == 3 { 1 } else { 2 };
        assert!(
            border >= wanted,
            "zone {zone}: only {border} gate crossings"
        );
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
    assert_eq!(
        p.zone, to,
        "walking at the border from {start:?} did not cross into zone {to}"
    );
    // The arrival is just inside the border line, which can fall in a margin cell (the raster is whole cells): within a tile of land.
    let on_land = land(zone_of(data, to));
    assert!(
        [
            (0., 0.),
            (1., 0.),
            (-1., 0.),
            (0., 1.),
            (0., -1.),
            (1., 1.),
            (-1., -1.),
            (1., -1.),
            (-1., 1.)
        ]
        .iter()
        .any(|(dx, dy)| on_land(p.x + dx, p.y + dy)),
        "arrived far off the land in zone {to} at ({:.1},{:.1})",
        p.x,
        p.y
    );
    at(p.x, p.y)
}

#[test]
fn a_shared_border_is_crossed_anywhere_along_it_in_both_directions() {
    seam_walks(0, 1);
}

#[test]
fn the_meadow_and_the_moonspore_canopy_share_a_seam() {
    seam_walks(0, 16);
}

#[test]
fn the_meadow_and_gloamfen_share_a_seam() {
    seam_walks(0, 3);
}

#[test]
fn the_crags_and_the_moonspore_canopy_share_a_seam() {
    seam_walks(1, 16);
}

#[test]
fn the_moonspore_canopy_keeps_its_gates_to_the_orrery_and_emberwake() {
    gates_stand_on_free_land(16, &[15, 45]);
}

#[test]
fn gloamfen_keeps_its_gate_to_skaldholm() {
    gates_stand_on_free_land(3, &[4]);
}

#[test]
fn the_glacier_keeps_gates_to_wyrdwood_and_skaldholm() {
    gates_stand_on_free_land(2, &[4, 6]);
}

#[test]
fn the_crags_and_the_glacier_share_a_seam() {
    seam_walks(1, 2);
}

#[test]
fn the_glacier_and_gloamfen_share_a_seam() {
    seam_walks(2, 3);
}

// Skaldholm has shaped zones on every side, so a wall's ends meet those zones' seams: a vault must stand clear of them, or a walker at the
// opening is on two crossings at once (the Crags' arch once stood on the end of its run, right where the glacier's seam now ends).
#[test]
fn no_vault_stands_on_a_seam() {
    let data = bundled();
    for zone in [0usize, 1, 2, 3] {
        let z = zone_of(&data, zone);
        let portals = z["portals"].as_array().unwrap();
        let arch = z["exitArches"]
            .as_array()
            .and_then(|a| a.iter().find(|e| e["name"] == "Skaldholm"))
            .unwrap();
        let (ax, ay) = (arch["x"].as_f64().unwrap(), arch["y"].as_f64().unwrap());
        for seam in portals.iter().filter_map(|p| p.get("seam")) {
            for q in seam["points"].as_array().unwrap() {
                let d = (q[0].as_f64().unwrap() - ax).hypot(q[1].as_f64().unwrap() - ay);
                assert!(
                    d > 25.,
                    "zone {zone}: the vault stands {d:.1} tiles from a seam"
                );
            }
        }
    }
}

#[test]
fn skaldholms_wall_runs_along_its_borders_and_the_vault_is_open() {
    let w = world();
    let data = bundled();
    for zone in [0usize, 1, 2, 3] {
        let z = zone_of(&data, zone);
        let objects = z["objects"].as_array().unwrap();
        let pieces: Vec<&Value> = objects
            .iter()
            .filter(|o| o["kind"] == "rampart" || o["kind"] == "tower")
            .collect();
        // (measured in tiles: the wall is Skaldholm's own long pieces, copied, so a piece count says little)
        let length: f64 = pieces
            .iter()
            .map(|o| {
                o["width"]
                    .as_f64()
                    .unwrap()
                    .max(o["depth"].as_f64().unwrap())
            })
            .sum();
        assert!(length >= 80., "zone {zone}: only {length:.0} tiles of wall");
        let arch = z["exitArches"]
            .as_array()
            .and_then(|a| a.iter().find(|e| e["name"] == "Skaldholm"))
            .unwrap_or_else(|| panic!("zone {zone} has no vault"));
        let gate = z["portals"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["id"] == arch["portal"])
            .unwrap();
        let (gx, gy) = (gate["x"].as_f64().unwrap(), gate["y"].as_f64().unwrap());
        let walk = gate["walk"].as_array().unwrap();
        let (wx, wy) = (walk[0].as_f64().unwrap(), walk[1].as_f64().unwrap());
        assert!(gate["to"] == 4, "the vault leads into Skaldholm");
        // the way in is open: from 5 tiles inland straight at the gate nothing blocks a walker (further out is ordinary scenery)
        for i in 0..=8 {
            let t = 5. - i as f64 * 0.5;
            let (x, y) = (gx - wx * t, gy - wy * t);
            let mut a = at(x, y);
            w.maps[zone].collide(&mut a, 0.4);
            assert!(
                (a.x - x).hypot(a.y - y) < 0.01,
                "zone {zone}: the vault approach is blocked at ({x:.1},{y:.1})"
            );
        }
        // and the wall is solid on both sides of the opening, within 25 tiles along it
        let half = arch["halfWidth"].as_f64().unwrap();
        let near = pieces
            .iter()
            .filter(|o| {
                let d = (o["x"].as_f64().unwrap() - arch["x"].as_f64().unwrap())
                    .hypot(o["y"].as_f64().unwrap() - arch["y"].as_f64().unwrap());
                d > half && d < half + 25.
            })
            .count();
        assert!(
            near >= 6,
            "zone {zone}: the wall beside the vault is missing ({near} pieces)"
        );
    }
}

#[test]
fn walking_into_the_vault_enters_skaldholm() {
    let mut w = world();
    let data = bundled();
    let _rx = join(&mut w, 1, Class::Warrior);
    for zone in [0usize, 1, 2, 3] {
        let z = zone_of(&data, zone);
        let gate = z["portals"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["to"] == 4)
            .unwrap();
        let (gx, gy) = (gate["x"].as_f64().unwrap(), gate["y"].as_f64().unwrap());
        let walk = gate["walk"].as_array().unwrap();
        let (wx, wy) = (walk[0].as_f64().unwrap(), walk[1].as_f64().unwrap());
        place(&mut w, 1, zone, at(gx - wx * 5., gy - wy * 5.));
        let dir = at(wx, wy);
        for _ in 0..160 {
            w.time += TICK;
            let hero = w.players.get_mut(&1).unwrap();
            hero.input = dir;
            hero.input_at = w.time;
            w.update_player(1);
            if w.players[&1].character.zone == 4 {
                break;
            }
        }
        let c = &w.players[&1].character;
        assert_eq!(
            c.zone, 4,
            "walking through the vault of zone {zone} from 5 tiles did not enter Skaldholm (ended at {:.1},{:.1})",
            c.x, c.y
        );
        // the city's own arch is the other half of the vault: you land just inside it, on free ground, not in a margin outside the wall
        let city = zone_of(&data, 4);
        let back = city["portals"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["to"] == zone as u64)
            .unwrap();
        let arch = city["exitArches"]
            .as_array()
            .unwrap()
            .iter()
            .find(|a| a["portal"] == back["id"])
            .unwrap();
        let (ax, ay) = (arch["x"].as_f64().unwrap(), arch["y"].as_f64().unwrap());
        assert!(
            (c.x - ax).hypot(c.y - ay) < 5.,
            "zone {zone}: you land {:.1} tiles from the city's arch",
            (c.x - ax).hypot(c.y - ay)
        );
        // one doorway seen from two zones: the two offsets cancel, and the arch of this zone maps onto the city's own
        for k in 0..2 {
            assert!(
                (gate["vault"][k].as_f64().unwrap() + back["vault"][k].as_f64().unwrap()).abs()
                    < 0.011,
                "zone {zone}: the vault offsets do not cancel"
            );
        }
        let zarch = zone_of(&data, zone)["exitArches"]
            .as_array()
            .unwrap()
            .iter()
            .find(|a| a["name"] == "Skaldholm")
            .unwrap();
        assert!(
            (zarch["x"].as_f64().unwrap() + gate["vault"][0].as_f64().unwrap() - ax).abs() < 0.011
                && (zarch["y"].as_f64().unwrap() + gate["vault"][1].as_f64().unwrap() - ay).abs()
                    < 0.011,
            "zone {zone}: the vault does not line up with the city's arch"
        );
        // and back out through the arch: held movement carries on, you stand in front of the vault again
        let out = back["walk"].as_array().unwrap();
        let odir = at(out[0].as_f64().unwrap(), out[1].as_f64().unwrap());
        for _ in 0..160 {
            w.time += TICK;
            let hero = w.players.get_mut(&1).unwrap();
            hero.input = odir;
            hero.input_at = w.time;
            w.update_player(1);
            if w.players[&1].character.zone == zone {
                break;
            }
        }
        let c = &w.players[&1].character;
        assert_eq!(
            c.zone, zone,
            "walking out of Skaldholm's arch did not return to zone {zone} (ended at {:.1},{:.1})",
            c.x, c.y
        );
        assert!(
            (c.x - gx).hypot(c.y - gy) < 6.,
            "zone {zone}: you come out {:.1} tiles from the vault",
            (c.x - gx).hypot(c.y - gy)
        );
    }
}

fn gates_stand_on_free_land(zone: usize, targets: &[u64]) {
    let w = world();
    let data = bundled();
    let z = zone_of(&data, zone);
    for &to in targets {
        let p = z["portals"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["to"] == to && p.get("seam").is_none())
            .unwrap_or_else(|| panic!("no gate from zone {zone} to zone {to}"));
        let (x, y) = (p["x"].as_f64().unwrap(), p["y"].as_f64().unwrap());
        assert!(land(z)(x, y), "gate to {to} is off the land");
        let mut a = at(x, y);
        w.maps[zone].collide(&mut a, 0.4);
        assert!(
            (a.x - x).hypot(a.y - y) < 0.01,
            "gate to {to} is inside an obstacle"
        );
        // and the way back lands on free Canopy ground
        let back = zone_of(&data, to as usize)["portals"]
            .as_array()
            .unwrap()
            .iter()
            .find(|q| q["to"] == zone as u64)
            .unwrap();
        let (tx, ty) = (back["tx"].as_f64().unwrap(), back["ty"].as_f64().unwrap());
        assert!(land(z)(tx, ty), "arrival from {to} is off the land");
        let mut b = at(tx, ty);
        w.maps[zone].collide(&mut b, 0.4);
        assert!(
            (b.x - tx).hypot(b.y - ty) < 0.01,
            "arrival from {to} is inside an obstacle"
        );
    }
}

fn seam_walks(from_zone: usize, to_zone: usize) {
    let mut w = world();
    let data = bundled();
    let _rx = join(&mut w, 1, Class::Warrior);
    let (a, b) = (zone_of(&data, from_zone), zone_of(&data, to_zone));
    let seam = a["portals"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["to"] == to_zone && p.get("seam").is_some())
        .map(|p| &p["seam"])
        .expect("a seam between the two zones");
    let points: Vec<Point> = seam["points"]
        .as_array()
        .unwrap()
        .iter()
        .map(|q| at(q[0].as_f64().unwrap(), q[1].as_f64().unwrap()))
        .collect();
    let on_a = land(a);
    let mut crossed = 0;
    // Skaldholm's wall meets a seam at its end: the last tiles of such a seam are the wall, on either side of the line.
    let (sx, sy) = (
        seam["shift"][0].as_f64().unwrap(),
        seam["shift"][1].as_f64().unwrap(),
    );
    let walled = |z: &Value, x: f64, y: f64| {
        z["objects"].as_array().unwrap().iter().any(|o| {
            (o["kind"] == "rampart" || o["kind"] == "tower")
                && (o["x"].as_f64().unwrap() - x).hypot(o["y"].as_f64().unwrap() - y) < 8.
        })
    };
    let mut at_wall = 0;
    // Samples along every border segment: the point 4 tiles inside the meadow, found from the side that is land.
    for pair in points.windows(2) {
        for t in [0.25, 0.5, 0.75] {
            let q = at(
                pair[0].x + (pair[1].x - pair[0].x) * t,
                pair[0].y + (pair[1].y - pair[0].y) * t,
            );
            let (dx, dy) = (pair[1].x - pair[0].x, pair[1].y - pair[0].y);
            let len = dx.hypot(dy);
            if len < 6. {
                continue;
            }
            let normal = at(-dy / len, dx / len);
            let inward = if on_a(q.x + normal.x * 4., q.y + normal.y * 4.) {
                normal
            } else {
                at(-normal.x, -normal.y)
            };
            if !on_a(q.x + inward.x * 4., q.y + inward.y * 4.) {
                continue;
            }
            if walled(a, q.x, q.y) || walled(b, q.x + sx, q.y + sy) {
                at_wall += 1;
                continue;
            }
            let landed = cross(&mut w, &data, from_zone, to_zone, q, inward);
            crossed += 1;
            // and back from where we arrived: straight at the same border again
            let shift = (
                seam["shift"][0].as_f64().unwrap(),
                seam["shift"][1].as_f64().unwrap(),
            );
            let q_in_b = at(q.x + shift.0, q.y + shift.1);
            let _back = cross(
                &mut w,
                &data,
                to_zone,
                from_zone,
                q_in_b,
                at(-inward.x, -inward.y),
            );
            assert!(
                landed.distance(q_in_b) < 4.,
                "the crossing is continuous: arrived {:.1} tiles from the mirrored spot",
                landed.distance(q_in_b)
            );
            let _ = b;
        }
    }
    assert!(crossed >= 8, "only {crossed} border samples crossed");
    assert!(
        at_wall <= 6,
        "{at_wall} border samples stand at a wall: the wall runs along the seam"
    );
}

#[test]
fn the_other_side_of_a_seam_is_listed_for_the_view_but_only_near_the_line() {
    let mut w = world();
    let data = bundled();
    let _a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Mage);
    let seam = zone_of(&data, 0)["portals"]
        .as_array()
        .unwrap()
        .iter()
        .find_map(|p| p.get("seam"))
        .unwrap();
    let pts = seam["points"].as_array().unwrap();
    let (shx, shy) = (
        seam["shift"][0].as_f64().unwrap(),
        seam["shift"][1].as_f64().unwrap(),
    );
    let mid = &pts[pts.len() / 2];
    // hero 2 stands in the Crags at the mirrored border point (inside the Crags land), hero 1 in the meadow
    let q = at(
        mid[0].as_f64().unwrap() + shx,
        mid[1].as_f64().unwrap() + shy,
    );
    let inside = (0..200)
        .map(|i| at(q.x + (i % 20) as f64 - 10., q.y + (i / 20) as f64 - 5.))
        .find(|p| land(zone_of(&data, 1))(p.x, p.y))
        .unwrap();
    place(&mut w, 2, 1, inside);
    let s0 = w.maps[0].spawn;
    place(&mut w, 1, 0, at(s0.x, s0.y));
    let view = w.snapshot_for(0);
    let across = view["across"]
        .as_array()
        .expect("the meadow lists what lies across its seam");
    assert_eq!(across[0]["to"], 1);
    assert_eq!(
        across[0]["players"].as_array().unwrap().len(),
        1,
        "the Crags hero near the border is listed"
    );
    // moved far from the border (beyond the view range), hero 2 is no longer listed
    let seam_line: Seam = serde_json::from_value(seam.clone()).unwrap();
    let on_b = land(zone_of(&data, 1));
    let far = (0..w.maps[1].size)
        .step_by(4)
        .flat_map(|y| {
            (0..w.maps[1].size)
                .step_by(4)
                .map(move |x| at(x as f64 + 0.5, y as f64 + 0.5))
        })
        .find(|p| on_b(p.x, p.y) && seam_line.distance(at(p.x - shx, p.y - shy)) > 80.)
        .expect("a Crags spot far from the border");
    place(&mut w, 2, 1, far);
    let view = w.snapshot_for(0);
    assert!(
        view["across"][0]["players"].as_array().unwrap().is_empty(),
        "a hero far from the border is not"
    );
    assert!(
        view["players"]
            .as_array()
            .unwrap()
            .iter()
            .all(|p| p["zone"] == 0),
        "own-zone players are unchanged"
    );
}

#[test]
fn what_lies_across_a_seam_is_slim_and_never_a_hidden_gm() {
    let mut w = world();
    let data = bundled();
    let _a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Mage);
    let seam = zone_of(&data, 0)["portals"]
        .as_array()
        .unwrap()
        .iter()
        .find_map(|p| p.get("seam"))
        .unwrap();
    let pts = seam["points"].as_array().unwrap();
    let (shx, shy) = (
        seam["shift"][0].as_f64().unwrap(),
        seam["shift"][1].as_f64().unwrap(),
    );
    let mid = &pts[pts.len() / 2];
    let q = at(
        mid[0].as_f64().unwrap() + shx,
        mid[1].as_f64().unwrap() + shy,
    );
    let inside = (0..200)
        .map(|i| at(q.x + (i % 20) as f64 - 10., q.y + (i / 20) as f64 - 5.))
        .find(|p| land(zone_of(&data, 1))(p.x, p.y))
        .unwrap();
    place(&mut w, 2, 1, inside);
    let s0 = w.maps[0].spawn;
    place(&mut w, 1, 0, at(s0.x, s0.y));
    let across = w.snapshot_for(0)["across"][0].clone();
    let player = &across["players"][0];
    assert_eq!(player["id"], w.players[&2].character.id);
    for field in [
        "x", "y", "look", "hp", "maxHp", "fx", "fy", "moving", "walk", "atkT", "dead", "buffs",
        "mounted",
    ] {
        assert!(player.get(field).is_some(), "ghost player lacks {field}");
    }
    for leak in [
        "inventory",
        "quests",
        "equipment",
        "gold",
        "gearInstances",
        "bags",
        "attributes",
        "mailUnread",
        "session",
        "explored",
        "storyMemory",
    ] {
        assert!(player.get(leak).is_none(), "ghost player leaks {leak}");
    }
    // A hidden GM in the neighbour zone is not listed at all.
    w.players.get_mut(&2).unwrap().character.gm = true;
    w.players.get_mut(&2).unwrap().hidden = true;
    assert!(
        w.snapshot_for(0)["across"][0]["players"]
            .as_array()
            .unwrap()
            .is_empty(),
        "a hidden GM is visible across the seam"
    );
    // Enemies: the fields a client draws, none of the server's bookkeeping.
    let enemy = w
        .slimes
        .iter()
        .find(|s| s.zone == 1)
        .expect("a Crags enemy")
        .across_view();
    for field in [
        "id",
        "kind",
        "x",
        "y",
        "state",
        "dir",
        "hop",
        "dead",
        "dieT",
        "windupTime",
        "maxHp",
        "seed",
    ] {
        assert!(enemy.get(field).is_some(), "ghost enemy lacks {field}");
    }
    for bookkeeping in ["hx", "hy", "respawn", "atkCd"] {
        assert!(
            enemy.get(bookkeeping).is_none(),
            "ghost enemy sends {bookkeeping}"
        );
    }
}

#[test]
fn a_hero_beside_a_vault_is_listed_across_it_from_both_sides() {
    let mut w = world();
    let data = bundled();
    let _a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Mage);
    for zone in [0usize, 1, 2, 3] {
        let gate = zone_of(&data, zone)["portals"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["to"] == 4)
            .unwrap();
        let (gx, gy) = (gate["x"].as_f64().unwrap(), gate["y"].as_f64().unwrap());
        let (vx, vy) = (
            gate["vault"][0].as_f64().unwrap(),
            gate["vault"][1].as_f64().unwrap(),
        );
        // hero 1 stands at the zone's gate, hero 2 in Skaldholm at the same world point (the vault offset)
        place(&mut w, 1, zone, at(gx - 4., gy));
        place(&mut w, 2, 4, at(gx - 4. + vx, gy + vy));
        let list = |view: &Value, to: usize| {
            view["across"]
                .as_array()
                .and_then(|a| a.iter().find(|e| e["to"] == to))
                .map(|e| (e["players"].as_array().unwrap().len(), e["shift"].clone()))
        };
        let (n, shift) = list(&w.snapshot_for(zone), 4)
            .unwrap_or_else(|| panic!("zone {zone} lists nothing across its vault"));
        assert_eq!(
            n, 1,
            "zone {zone}: the hero in Skaldholm is listed beside the vault"
        );
        assert_eq!(shift[0].as_f64().unwrap(), vx);
        let (n, shift) = list(&w.snapshot_for(4), zone)
            .unwrap_or_else(|| panic!("Skaldholm lists nothing across its vault to zone {zone}"));
        assert_eq!(n, 1, "Skaldholm lists the hero standing in zone {zone}");
        assert_eq!(shift[0].as_f64().unwrap(), -vx);
        // far from the gate (the zone's spawn), nobody is listed
        // (Rimeward Camp stands right behind its vault: the far end of the zone is the Wyrdwood gate)
        let s0 = if zone == 2 {
            at(167.5, 67.5)
        } else {
            w.maps[zone].spawn
        };
        place(&mut w, 1, zone, at(s0.x, s0.y));
        let (n, _) = list(&w.snapshot_for(4), zone).unwrap();
        assert_eq!(n, 0, "zone {zone}: a hero far from the vault is not listed");
    }
}

#[test]
fn the_whole_opening_of_a_vault_crosses_not_only_its_middle() {
    let mut w = world();
    let data = bundled();
    let _rx = join(&mut w, 1, Class::Warrior);
    for zone in [0usize, 1, 2, 3] {
        let gate = zone_of(&data, zone)["portals"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["to"] == 4)
            .unwrap();
        let (gx, gy) = (gate["x"].as_f64().unwrap(), gate["y"].as_f64().unwrap());
        let walk = gate["walk"].as_array().unwrap();
        let (wx, wy) = (walk[0].as_f64().unwrap(), walk[1].as_f64().unwrap());
        let half = gate["vault_half"]
            .as_f64()
            .expect("a vault knows its opening");
        for across in [-(half - 0.6), -half / 2., half / 2., half - 0.6] {
            // start 6 tiles before the gate, off to the side of the opening, and walk straight through
            place(
                &mut w,
                1,
                zone,
                at(gx - wx * 6. + -wy * across, gy - wy * 6. + wx * across),
            );
            let dir = at(wx, wy);
            for _ in 0..200 {
                w.time += TICK;
                let hero = w.players.get_mut(&1).unwrap();
                hero.input = dir;
                hero.input_at = w.time;
                w.update_player(1);
                if w.players[&1].character.zone == 4 {
                    break;
                }
            }
            let c = &w.players[&1].character;
            assert_eq!(
                c.zone, 4,
                "zone {zone}: walking through the opening {across:+.1} tiles off its middle did not enter Skaldholm (at {:.1},{:.1})",
                c.x, c.y
            );
        }
    }
}

// Greenmeadow is an authored map (scripts/greenmeadow_design.py): hamlets, elites and quests on real ground.
#[test]
fn greenmeadows_hamlets_are_sanctuaries_with_their_people() {
    let w = world();
    let map = &w.maps[0];
    assert_eq!(map.camps.len(), 3, "Stonefold, Saltby and Applewick");
    for id in [
        "fold_hild",
        "fold_torvald",
        "fold_trader",
        "travel_stonefold",
        "salt_ragna",
        "salt_odd",
        "salt_trader",
        "travel_saltby",
        "apple_maren",
        "apple_sten",
        "apple_trader",
        "travel_applewick",
        "apple_lotta",
    ] {
        let npc = map.npcs.iter().find(|n| n.id == id).unwrap();
        let spot = Point { x: npc.x, y: npc.y };
        assert!(map.in_city(spot), "{id} stands in a sanctuary");
        let mut q = spot;
        map.collide(&mut q, PLAYER_RADIUS);
        assert!(q.distance(spot) < 1e-6, "{id} stands on free ground");
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 0 && s.state != "waiting")
                .all(|s| s.point().distance(spot) > 8.),
            "no enemy within eight units of {id}"
        );
    }
}

#[test]
fn every_greenmeadow_quest_can_be_done_on_the_map() {
    let w = world();
    let map = &w.maps[0];
    for q in map.quests.iter().filter(|q| q.level <= 5) {
        let seasonal = [
            "halloween",
            "christmas",
            "easter",
            "solstice",
            "valentine",
            "newyear",
        ];
        if q.id.starts_with("es_") || seasonal.iter().any(|s| q.id.starts_with(s)) {
            continue;
        }
        for o in &q.objectives {
            match o.kind.as_str() {
                "visit" | "hold" => assert!(
                    map.places.iter().any(|p| p.id == o.target),
                    "{}: place {}",
                    q.id,
                    o.target
                ),
                "talk" | "escort" => assert!(
                    map.npcs.iter().any(|n| n.id == o.target),
                    "{}: npc {}",
                    q.id,
                    o.target
                ),
                "kill" if o.target != "any" && o.target != "slime" => assert!(
                    w.slimes.iter().any(|s| s.zone == 0 && s.kind == o.target),
                    "{}: enemy {}",
                    q.id,
                    o.target
                ),
                _ => {}
            }
        }
    }
}

#[test]
fn greenmeadow_has_three_elites_two_with_a_quest() {
    let w = world();
    let quests = &w.maps[0].quests;
    for (kind, quest) in [
        ("oldtusker", true),
        ("tidecrusher", true),
        ("orchardqueen", false),
    ] {
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 0 && s.kind == kind)
                .count(),
            1,
            "one {kind}"
        );
        assert!(crate::items::is_elite(kind), "{kind} is an elite");
        assert_eq!(
            quests
                .iter()
                .any(|q| q.objectives.iter().any(|o| o.target == kind)),
            quest,
            "{kind} quest"
        );
    }
}

fn meadow_hero(w: &mut World, x: f64, y: f64, level: u32, quest: &str) -> mpsc::Receiver<Value> {
    let rx = join(w, 1, Class::Warrior);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = level;
    c.zone = 0;
    c.x = x;
    c.y = y;
    c.hp = c.max_hp();
    c.quests.push(QuestProgress {
        id: quest.into(),
        counts: vec![0],
        ..Default::default()
    });
    rx
}

#[test]
fn the_ring_at_dusk_wakes_its_slimes_and_counts_twenty_seconds() {
    let mut w = world();
    let _rx = meadow_hero(&mut w, 58., 222., 4, "fold_watch");
    let sleepers = |w: &World| {
        w.spawns
            .iter()
            .enumerate()
            .filter(|(_, s)| {
                s.ambush
                    .as_deref()
                    .is_some_and(|t| t.starts_with("fold_watch_m"))
            })
            .filter(|(id, _)| w.slimes[*id].dead)
            .count()
    };
    assert_eq!(
        sleepers(&w),
        4,
        "four slimes sleep until the waves call them"
    );
    for tick in 0..(24. / TICK) as usize {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.hp = c.max_hp();
        w.step();
        if tick == (5. / TICK) as usize {
            assert_eq!(sleepers(&w), 2, "the first wave came");
        }
        if tick == (15. / TICK) as usize {
            assert_eq!(sleepers(&w), 0, "the second wave came");
        }
    }
    let c = &w.players[&1].character;
    assert!(
        c.quests
            .iter()
            .find(|q| q.id == "fold_watch")
            .unwrap()
            .counts[0]
            >= 20,
        "the hold is complete"
    );
}

#[test]
fn lotta_walks_the_lane_from_applewick_to_the_watermill() {
    let mut w = world();
    let lotta = w.maps[0]
        .npcs
        .iter()
        .find(|n| n.id == "apple_lotta")
        .unwrap()
        .clone();
    let route = &lotta.escort.as_ref().unwrap().route;
    for leg in route.windows(2) {
        let (from, to) = (at(leg[0][0], leg[0][1]), at(leg[1][0], leg[1][1]));
        for k in 0..=20 {
            let t = k as f64 / 20.;
            let spot = at(from.x + (to.x - from.x) * t, from.y + (to.y - from.y) * t);
            let mut q = spot;
            w.maps[0].collide(&mut q, PLAYER_RADIUS);
            assert!(q.distance(spot) < 1e-6, "the lane is clear at {spot:?}");
        }
    }
    let _rx = meadow_hero(&mut w, lotta.x, lotta.y + 1., 4, "apple_mill");
    w.time += 1.;
    w.interact(1, "apple_lotta", None);
    let owner = w.players[&1].character.id.clone();
    let escort = w.escort_of(&owner).expect("Lotta joins");
    for _ in 0..(90. / TICK) as usize {
        let Some(e) = w.players.get(&escort) else {
            break;
        };
        let there = e.character.point();
        let e = &mut w.players.get_mut(&escort).unwrap().character;
        e.hp = e.max_hp();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = there.x + 1.;
        c.y = there.y + 1.;
        c.hp = c.max_hp();
        // The hero fights what comes: an escort stands still while an enemy is on it.
        for s in w.slimes.iter_mut().filter(|s| s.zone == 0 && !s.dead) {
            if s.point().distance(there) < 12. {
                s.dead = true;
                s.respawn = 1e9;
            }
        }
        w.step();
    }
    let c = &w.players[&1].character;
    assert_eq!(
        c.quests
            .iter()
            .find(|q| q.id == "apple_mill")
            .unwrap()
            .counts[0],
        1,
        "Lotta reached the watermill"
    );
}

// The Emberfall Crags are an authored map (scripts/crags_design.py): outposts, elites and quests on real ground.
#[test]
fn the_crags_outposts_are_sanctuaries_with_their_people() {
    let w = world();
    let map = &w.maps[1];
    assert_eq!(map.camps.len(), 3, "Anvilrest, Ashford and Lasthearth");
    for id in [
        "anvil_ingrid",
        "anvil_bror",
        "anvil_trader",
        "travel_anvilrest",
        "ford_tora",
        "ford_olaf",
        "ford_ulf",
        "ford_trader",
        "travel_ashford",
        "hearth_sigrid",
        "hearth_elof",
        "hearth_trader",
        "travel_lasthearth",
    ] {
        let npc = map.npcs.iter().find(|n| n.id == id).unwrap();
        let spot = Point { x: npc.x, y: npc.y };
        assert!(map.in_city(spot), "{id} stands in a sanctuary");
        let mut q = spot;
        map.collide(&mut q, PLAYER_RADIUS);
        assert!(q.distance(spot) < 1e-6, "{id} stands on free ground");
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 1 && s.state != "waiting")
                .all(|s| s.point().distance(spot) > 8.),
            "no enemy within eight units of {id}"
        );
    }
    // mail_all stops at Alderhaven's old entry, so the outposts' mailboxes are checked here
    for hub in ["anvilrest", "ashford", "lasthearth"] {
        let find = |id: String| map.npcs.iter().find(|n| n.id == id).unwrap();
        let (b, m) = (
            find(format!("mailbox_1_{hub}")),
            find(format!("travel_{hub}")),
        );
        let (spot, anchor) = (at(b.x, b.y), at(m.x, m.y));
        let mut q = spot;
        map.collide(&mut q, 0.6);
        assert!(q.distance(spot) < 0.01, "{hub}: mailbox blocked");
        assert!(map.line_clear(anchor, spot, 0.4), "{hub}: mailbox approach");
    }
}

#[test]
fn every_crags_quest_can_be_done_on_the_map() {
    let w = world();
    let map = &w.maps[1];
    let mut played = 0;
    for q in map.quests.iter().filter(|q| !q.id.starts_with("es_")) {
        assert!((5..=10).contains(&q.level), "{}: level {}", q.id, q.level);
        for o in &q.objectives {
            match o.kind.as_str() {
                "visit" | "hold" => assert!(
                    map.places.iter().any(|p| p.id == o.target),
                    "{}: place {}",
                    q.id,
                    o.target
                ),
                "talk" | "escort" => assert!(
                    map.npcs.iter().any(|n| n.id == o.target),
                    "{}: npc {}",
                    q.id,
                    o.target
                ),
                "kill" if o.target != "any" => assert!(
                    w.slimes.iter().any(|s| s.zone == 1 && s.kind == o.target),
                    "{}: enemy {}",
                    q.id,
                    o.target
                ),
                _ => {}
            }
            played += 1;
        }
        assert!(
            map.npcs.iter().any(|n| n.id == q.npc),
            "{}: giver {} is in the Crags",
            q.id,
            q.npc
        );
    }
    assert!(played > 30, "the walk covers the whole chain: {played}");
}

#[test]
fn the_crags_have_three_elites_two_with_a_quest() {
    let w = world();
    let quests = &w.maps[1].quests;
    for (kind, quest) in [("cinderlord", true), ("slagmaw", true), ("ashwing", false)] {
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 1 && s.kind == kind)
                .count(),
            1,
            "one {kind}"
        );
        assert!(crate::items::is_elite(kind), "{kind} is an elite");
        assert_eq!(
            quests
                .iter()
                .any(|q| q.objectives.iter().any(|o| o.target == kind)),
            quest,
            "{kind} quest"
        );
    }
}

#[test]
fn a_crags_road_reaches_every_gate() {
    let w = world();
    let map = &w.maps[1];
    // the road network reaches every crossing: each gate has a road end within a step of it
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let paths = data["zones"][0]["paths"].as_array().unwrap();
    for p in map.portals.iter().filter(|p| p.seam.is_none()) {
        let near = paths.iter().flat_map(|r| r.as_array().unwrap()).any(|q| {
            at(q[0].as_f64().unwrap(), q[1].as_f64().unwrap()).distance(at(p.x, p.y)) < 2.
        });
        assert!(near, "a road reaches {}", p.id);
    }
}

fn crags_hero(w: &mut World, x: f64, y: f64, level: u32, quest: &str) -> mpsc::Receiver<Value> {
    let rx = meadow_hero(w, x, y, level, quest);
    w.players.get_mut(&1).unwrap().character.zone = 1;
    rx
}

#[test]
fn the_beacon_wakes_the_ridge_and_counts_twenty_seconds() {
    let mut w = world();
    let _rx = crags_hero(&mut w, 122., 92., 9, "ford_lit");
    let sleepers = |w: &World| {
        w.spawns
            .iter()
            .enumerate()
            .filter(|(_, s)| {
                s.ambush
                    .as_deref()
                    .is_some_and(|t| t.starts_with("ford_lit_m"))
            })
            .filter(|(id, _)| w.slimes[*id].dead)
            .count()
    };
    assert_eq!(
        sleepers(&w),
        4,
        "four enemies sleep until the waves call them"
    );
    for tick in 0..(24. / TICK) as usize {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.hp = c.max_hp();
        w.step();
        if tick == (5. / TICK) as usize {
            assert_eq!(sleepers(&w), 2, "the first wave came");
        }
        if tick == (15. / TICK) as usize {
            assert_eq!(sleepers(&w), 0, "the second wave came");
        }
    }
    let c = &w.players[&1].character;
    assert!(
        c.quests.iter().find(|q| q.id == "ford_lit").unwrap().counts[0] >= 20,
        "the hold is complete"
    );
}

#[test]
fn ulf_walks_the_cart_over_the_ford_and_up_the_highfire_road() {
    let mut w = world();
    let ulf = w.maps[1]
        .npcs
        .iter()
        .find(|n| n.id == "ford_ulf")
        .unwrap()
        .clone();
    let route = &ulf.escort.as_ref().unwrap().route;
    for leg in route.windows(2) {
        let (from, to) = (at(leg[0][0], leg[0][1]), at(leg[1][0], leg[1][1]));
        for k in 0..=20 {
            let t = k as f64 / 20.;
            let spot = at(from.x + (to.x - from.x) * t, from.y + (to.y - from.y) * t);
            let mut q = spot;
            w.maps[1].collide(&mut q, PLAYER_RADIUS);
            assert!(q.distance(spot) < 1e-6, "the road is clear at {spot:?}");
        }
    }
    let _rx = crags_hero(&mut w, ulf.x, ulf.y + 1., 8, "ford_cart");
    w.time += 1.;
    w.interact(1, "ford_ulf", None);
    let owner = w.players[&1].character.id.clone();
    let escort = w.escort_of(&owner).expect("Ulf joins");
    for _ in 0..(120. / TICK) as usize {
        let Some(e) = w.players.get(&escort) else {
            break;
        };
        let there = e.character.point();
        let e = &mut w.players.get_mut(&escort).unwrap().character;
        e.hp = e.max_hp();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = there.x + 1.;
        c.y = there.y + 1.;
        c.hp = c.max_hp();
        for s in w.slimes.iter_mut().filter(|s| s.zone == 1 && !s.dead) {
            if s.point().distance(there) < 12. {
                s.dead = true;
                s.respawn = 1e9;
            }
        }
        w.step();
    }
    let c = &w.players[&1].character;
    assert_eq!(
        c.quests
            .iter()
            .find(|q| q.id == "ford_cart")
            .unwrap()
            .counts[0],
        1,
        "Ulf reached the end of the road"
    );
}
