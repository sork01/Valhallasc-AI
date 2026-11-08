//! Zones with the outline of their province on the atlas (docs/zone-shapes.md): the walkable land is the outline.
use super::wyrd_tests::{at, join, place, world};
use super::*;

const SHAPED: [usize; 6] = [0, 1, 2, 3, 6, 16];

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
                    // a walker can only start where he can stand (the Wyrdwood's river runs right out to the edge: its water is solid there)
                    let mut free = p;
                    w.maps[zone].collide(&mut free, 0.4);
                    if free.distance(p) > 0.01 {
                        continue;
                    }
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
        // (Gloamfen has seams on two sides and a wall on a third, the glacier seams on three: little plain edge is left)
        let floor = if zone == 2 { 10 } else { 20 };
        assert!(tested > floor, "zone {zone}: only {tested} edge walks");
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
        // (the glacier's Wyrdwood border and the Wyrdwood's glacier and Crags borders are seams too: each keeps one gate; the Canopy keeps only Emberwake's since the Orrery border became a seam)
        // (the Canopy keeps no gate at all: its Orrery and Emberwake borders are seams)
        let wanted = match zone {
            16 => 0,
            0 | 2 | 3 | 6 => 1,
            _ => 2,
        };
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
fn the_deep_and_nacrehold_share_a_seam() {
    seam_walks(8, 9);
}

#[test]
fn nacrehold_keeps_its_gates_to_the_crags_bifrost_astralhollow_and_the_orrery() {
    gates_stand_on_free_land(9, &[1, 7, 13, 15]);
}

#[test]
fn nacrehold_is_seamless_against_the_deep_only() {
    let data = bundled();
    let mut seams = 0;
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in zone_of(&data, zi)["portals"].as_array().unwrap() {
            if p.get("seam").is_some() && (zi == 9 || p["to"] == 9) {
                seams += 1;
                assert!(
                    (zi == 8 && p["to"] == 9) || (zi == 9 && p["to"] == 8),
                    "zone {zi} has a seam to {}",
                    p["to"]
                );
            }
        }
    }
    assert_eq!(seams, 2, "one seam, seen from both sides");
}

#[test]
fn the_crags_and_the_moonspore_canopy_share_a_seam() {
    seam_walks(1, 16);
}

#[test]
fn the_moonspore_canopy_and_emberwake_share_a_seam() {
    seam_walks(16, 45);
}

#[test]
fn gloamfen_keeps_its_gate_to_skaldholm() {
    gates_stand_on_free_land(3, &[4]);
}

#[test]
fn the_glacier_keeps_its_gate_to_skaldholm() {
    gates_stand_on_free_land(2, &[4]);
}

#[test]
fn the_wyrdwood_keeps_its_gate_to_bifrost() {
    gates_stand_on_free_land(6, &[7]);
}

#[test]
fn the_wyrdwood_and_the_glacier_share_a_seam() {
    seam_walks(6, 2);
}

#[test]
fn the_wyrdwood_and_the_crags_share_a_seam() {
    seam_walks(6, 1);
}

#[test]
fn the_wyrdwood_seams_meet_the_crags_and_glacier_seam_at_a_corner_nobody_stands_on_two_crossings_at()
 {
    let data = bundled();
    let z = zone_of(&data, 6);
    let seams: Vec<&Value> = z["portals"]
        .as_array()
        .unwrap()
        .iter()
        .filter_map(|p| p.get("seam"))
        .collect();
    assert_eq!(
        seams.len(),
        2,
        "the Wyrdwood has a seam to the Crags and one to the glacier"
    );
    // the junction: the end point the two seams share
    let ends: Vec<Vec<(f64, f64)>> = seams
        .iter()
        .map(|s| {
            let p = s["points"].as_array().unwrap();
            [&p[0], &p[p.len() - 1]]
                .iter()
                .map(|q| (q[0].as_f64().unwrap(), q[1].as_f64().unwrap()))
                .collect()
        })
        .collect();
    let junction = ends[0]
        .iter()
        .flat_map(|a| ends[1].iter().map(move |b| (*a, *b)))
        .min_by(|x, y| {
            ((x.0.0 - x.1.0).hypot(x.0.1 - x.1.1))
                .partial_cmp(&((y.0.0 - y.1.0).hypot(y.0.1 - y.1.1)))
                .unwrap()
        })
        .unwrap();
    assert!(
        (junction.0.0 - junction.1.0).hypot(junction.0.1 - junction.1.1) < 0.5,
        "the two seams meet at one corner"
    );
    // a hero walking toward the corner from inside the Wyrdwood is never on land of one zone while a neighbour's seam also claims him:
    // stand on the Wyrdwood's land 3, 6 and 12 tiles from the corner along the bisector and check every crossing claims at most one seam
    let on_land = land(z);
    let (cx, cy) = junction.0;
    let mut checked = 0;
    for dist in [3., 6., 12.] {
        for k in 0..16 {
            let a = k as f64 / 16. * std::f64::consts::TAU;
            let (x, y) = (cx + a.cos() * dist, cy + a.sin() * dist);
            if !on_land(x, y) {
                continue;
            }
            checked += 1;
            let claims = seams
                .iter()
                .filter(|s| {
                    s["points"].as_array().unwrap().windows(2).any(|w| {
                        let (ax, ay) = (w[0][0].as_f64().unwrap(), w[0][1].as_f64().unwrap());
                        let (bx, by) = (w[1][0].as_f64().unwrap(), w[1][1].as_f64().unwrap());
                        let (dx, dy) = (bx - ax, by - ay);
                        let t =
                            (((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)).clamp(0., 1.);
                        (x - ax - t * dx).hypot(y - ay - t * dy) < 0.5
                    })
                })
                .count();
            assert!(
                claims <= 1,
                "a point on the land at ({x:.1}, {y:.1}) lies on both seams"
            );
        }
    }
    assert!(checked > 0, "no land samples near the corner");
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
        assert!(length >= 70., "zone {zone}: only {length:.0} tiles of wall"); // (Greenmeadow's wall stops at the city's east wall since the rebuild)
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
    seam_walks_with(from_zone, to_zone, 6., 8);
}

/// `min_len`: segments shorter than this are skipped; `min_crossed`: how many samples must cross (the Prismwaste-Orrery seam is only 37 tiles long)
fn seam_walks_with(from_zone: usize, to_zone: usize, min_len: f64, min_crossed: usize) {
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
            if len < min_len {
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
    assert!(
        crossed >= min_crossed,
        "only {crossed} border samples crossed"
    );
    assert!(
        at_wall <= 6,
        "{at_wall} border samples stand at a wall: the wall runs along the seam"
    );
}

#[test]
fn astralhollow_and_the_orrery_share_a_seam() {
    seam_walks(13, 15);
}

#[test]
fn the_orrery_and_the_moonspore_canopy_share_a_seam() {
    seam_walks(15, 16);
}

#[test]
fn the_orrery_keeps_its_gates_to_the_crags_nacrehold_and_emberwake() {
    gates_stand_on_free_land(15, &[1, 9, 45]);
}

#[test]
fn the_orrery_is_seamless_against_astralhollow_the_prismwaste_stormglass_and_the_moonspore_canopy_only()
 {
    let data = bundled();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in zone_of(&data, zi)["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == 15 || to == 15) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> = [
        (13, 15),
        (15, 13),
        (14, 15),
        (15, 14),
        (15, 16),
        (16, 15),
        (15, 19),
        (19, 15),
    ]
    .into();
    assert_eq!(
        pairs, want,
        "one seam each to Astralhollow, the Prismwaste, Stormglass and the Canopy, seen from both sides"
    );
}

#[test]
fn astralhollow_and_the_prismwaste_share_a_seam() {
    seam_walks(13, 14);
}

#[test]
fn the_prismwaste_and_the_orrery_share_a_seam() {
    seam_walks_with(14, 15, 3., 6);
}

#[test]
fn the_prismwaste_keeps_its_gate_to_cairnspine() {
    gates_stand_on_free_land(14, &[27]);
}

#[test]
fn the_prismwaste_is_seamless_against_astralhollow_the_orrery_and_stormglass_only() {
    let data = bundled();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in zone_of(&data, zi)["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == 14 || to == 14) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> =
        [(13, 14), (14, 13), (14, 15), (15, 14), (14, 19), (19, 14)].into();
    assert_eq!(
        pairs, want,
        "one seam each to Astralhollow, the Orrery and Stormglass, seen from both sides"
    );
}

#[test]
fn the_prismwaste_and_the_stormglass_flats_share_a_seam() {
    seam_walks(14, 19);
}

#[test]
fn the_orrery_and_the_stormglass_flats_share_a_seam() {
    seam_walks(15, 19);
}

#[test]
fn the_stormglass_flats_keep_their_gates_to_sunward_and_frostwake() {
    gates_stand_on_free_land(19, &[20, 26]);
}

#[test]
fn the_stormglass_flats_and_emberwake_share_a_seam() {
    seam_walks(19, 45);
}

#[test]
fn emberwake_keeps_its_gate_to_the_orrery() {
    gates_stand_on_free_land(45, &[15]);
}

#[test]
fn emberwake_and_the_ribbonwild_share_a_seam() {
    seam_walks(21, 45);
}

#[test]
fn emberwake_is_seamless_against_the_stormglass_flats_the_moonspore_canopy_and_the_ribbonwild_only()
{
    let data = bundled();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in zone_of(&data, zi)["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == 45 || to == 45) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> =
        [(19, 45), (45, 19), (16, 45), (45, 16), (21, 45), (45, 21)].into();
    assert_eq!(
        pairs, want,
        "one seam to the Flats and one to the Canopy, seen from both sides"
    );
}

#[test]
fn the_stormglass_flats_are_seamless_against_the_prismwaste_the_orrery_and_emberwake_only() {
    let data = bundled();
    let mut pairs = std::collections::BTreeSet::new();
    for zi in 1..=data["zones"].as_array().unwrap().len() {
        for p in zone_of(&data, zi)["portals"].as_array().unwrap() {
            let to = p["to"].as_u64().unwrap() as usize;
            if p.get("seam").is_some() && (zi == 19 || to == 19) {
                pairs.insert((zi, to));
            }
        }
    }
    let want: std::collections::BTreeSet<_> =
        [(14, 19), (19, 14), (15, 19), (19, 15), (19, 45), (45, 19)].into();
    assert_eq!(
        pairs, want,
        "one seam each to the Prismwaste, the Orrery and Emberwake, seen from both sides"
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

// ---- Rimeveil Glacier, authored (scripts/rimeveil_design.py) ----------------------------------------------------------

#[test]
fn the_glacier_outposts_are_sanctuaries_with_their_people() {
    let w = world();
    let map = &w.maps[2];
    assert_eq!(
        map.camps.len(),
        3,
        "Driftwatch, Shearwind Post and Peakrest"
    );
    for id in [
        "rime_dw_hild",
        "rime_dw_nils",
        "rime_dw_trader",
        "travel_driftwatch",
        "rime_sw_runa",
        "rime_sw_arne",
        "rime_sw_trader",
        "travel_shearwind",
        "rime_pk_gunnar",
        "rime_pk_sif",
        "rime_pk_trader",
        "travel_peakrest",
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
                .filter(|s| s.zone == 2 && s.state != "waiting")
                .all(|s| s.point().distance(spot) > 8.),
            "no enemy within eight units of {id}"
        );
    }
    // mail_all stops at the camp's old entry, so the outposts' mailboxes are checked here
    for hub in ["driftwatch", "shearwind", "peakrest"] {
        let find = |id: String| map.npcs.iter().find(|n| n.id == id).unwrap();
        let (b, m) = (
            find(format!("mailbox_2_{hub}")),
            find(format!("travel_{hub}")),
        );
        let (spot, anchor) = (at(b.x, b.y), at(m.x, m.y));
        let mut q = spot;
        map.collide(&mut q, 0.6);
        assert!(q.distance(spot) < 0.01, "{hub}: mailbox blocked");
        assert!(map.line_clear(anchor, spot, 0.4), "{hub}: mailbox approach");
    }
    let master = map.npcs.iter().find(|n| n.id == "travel_rimeward").unwrap();
    for hub in ["driftwatch", "shearwind", "peakrest"] {
        assert!(
            master
                .travel_links
                .iter()
                .any(|l| l == &format!("travel_{hub}")),
            "Rimeward's Travel Master links to {hub}"
        );
    }
}

#[test]
fn every_glacier_quest_can_be_done_on_the_map() {
    let w = world();
    let map = &w.maps[2];
    let mut played = 0;
    for q in map.quests.iter().filter(|q| !q.id.starts_with("es_")) {
        assert!((10..=15).contains(&q.level), "{}: level {}", q.id, q.level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
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
                    w.slimes.iter().any(|s| s.zone == 2 && s.kind == o.target),
                    "{}: enemy {}",
                    q.id,
                    o.target
                ),
                "bring" => assert!(
                    w.slimes
                        .iter()
                        .any(|s| s.zone == 2 && crate::items::material(&s.kind) == o.target),
                    "{}: some enemy of the glacier drops {}",
                    q.id,
                    o.target
                ),
                _ => {}
            }
            played += 1;
        }
        assert!(
            map.npcs.iter().any(|n| n.id == q.npc),
            "{}: giver {} is on the glacier",
            q.id,
            q.npc
        );
        if let Some(id) = &q.requires {
            let pre = map.quests.iter().find(|p| &p.id == id).unwrap();
            assert!(pre.level <= q.level, "{} unlocks upward", q.id);
        }
    }
    assert!(played > 35, "the walk covers the whole chain: {played}");
}

#[test]
fn the_glacier_has_three_elites_two_with_a_quest() {
    let w = world();
    let quests = &w.maps[2].quests;
    for (kind, quest) in [
        ("hoarhorn", true),
        ("whitewail", true),
        ("shardback", false),
    ] {
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 2 && s.kind == kind)
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
fn a_glacier_road_reaches_every_gate_and_the_ice_rings_are_solid() {
    let w = world();
    let map = &w.maps[2];
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let paths = data["zones"][1]["paths"].as_array().unwrap();
    for p in map.portals.iter().filter(|p| p.seam.is_none()) {
        let near = paths.iter().flat_map(|r| r.as_array().unwrap()).any(|q| {
            at(q[0].as_f64().unwrap(), q[1].as_f64().unwrap()).distance(at(p.x, p.y)) < 2.
        });
        assert!(near, "a road reaches {}", p.id);
    }
    // a ring of ice is terrain: nobody walks through its middle, and every road still gets across at a ford
    let rings: Vec<&Value> = data["zones"][1]["objects"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["kind"] == "water")
        .collect();
    assert!(rings.len() > 500, "{} water circles", rings.len());
    let o = rings[rings.len() / 2];
    let spot = at(o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
    let mut q = spot;
    map.collide(&mut q, PLAYER_RADIUS);
    assert!(q.distance(spot) > 0.1, "the ice is solid");
    for road in paths {
        let pts = road.as_array().unwrap();
        for leg in pts.windows(2) {
            let (a, b) = (
                at(leg[0][0].as_f64().unwrap(), leg[0][1].as_f64().unwrap()),
                at(leg[1][0].as_f64().unwrap(), leg[1][1].as_f64().unwrap()),
            );
            for k in 0..=24 {
                let t = k as f64 / 24.;
                let spot = at(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t);
                if map.in_city(spot) {
                    continue;
                }
                let mut q = spot;
                map.collide(&mut q, PLAYER_RADIUS);
                assert!(q.distance(spot) < 1e-6, "the road is clear at {spot:?}");
            }
        }
    }
}

fn glacier_hero(w: &mut World, x: f64, y: f64, level: u32, quest: &str) -> mpsc::Receiver<Value> {
    let rx = meadow_hero(w, x, y, level, quest);
    w.players.get_mut(&1).unwrap().character.zone = 2;
    rx
}

fn hold_wakes_its_waves_and_counts_twenty_seconds(
    spot: (f64, f64),
    level: u32,
    quest: &str,
    prefix: &str,
) {
    let mut w = world();
    let _rx = glacier_hero(&mut w, spot.0, spot.1, level, quest);
    let sleepers = |w: &World| {
        w.spawns
            .iter()
            .enumerate()
            .filter(|(_, s)| s.ambush.as_deref().is_some_and(|t| t.starts_with(prefix)))
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
        c.quests.iter().find(|q| q.id == quest).unwrap().counts[0] >= 20,
        "the hold is complete"
    );
}

#[test]
fn the_signal_fire_wakes_the_fells_and_counts_twenty_seconds() {
    hold_wakes_its_waves_and_counts_twenty_seconds(
        (30., 128.),
        14,
        "rime_sw_signal",
        "rime_signal_m",
    );
}

#[test]
fn the_stranded_sledge_wakes_the_drifts_and_counts_twenty_seconds() {
    hold_wakes_its_waves_and_counts_twenty_seconds(
        (96., 259.),
        12,
        "rime_dw_sledge",
        "rime_sledge_m",
    );
}

#[test]
fn sif_walks_the_charts_from_peakrest_down_through_the_rings_to_the_heart() {
    let mut w = world();
    let sif = w.maps[2]
        .npcs
        .iter()
        .find(|n| n.id == "rime_pk_sif")
        .unwrap()
        .clone();
    let route = &sif.escort.as_ref().unwrap().route;
    for leg in route.windows(2) {
        let (from, to) = (at(leg[0][0], leg[0][1]), at(leg[1][0], leg[1][1]));
        for k in 0..=20 {
            let t = k as f64 / 20.;
            let spot = at(from.x + (to.x - from.x) * t, from.y + (to.y - from.y) * t);
            let mut q = spot;
            w.maps[2].collide(&mut q, PLAYER_RADIUS);
            assert!(q.distance(spot) < 1e-6, "the road is clear at {spot:?}");
        }
    }
    let _rx = glacier_hero(&mut w, sif.x, sif.y + 1., 14, "rime_pk_chart");
    w.time += 1.;
    w.interact(1, "rime_pk_sif", None);
    let owner = w.players[&1].character.id.clone();
    let escort = w.escort_of(&owner).expect("Sif joins");
    for _ in 0..(150. / TICK) as usize {
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
        for s in w.slimes.iter_mut().filter(|s| s.zone == 2 && !s.dead) {
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
            .find(|q| q.id == "rime_pk_chart")
            .unwrap()
            .counts[0],
        1,
        "Sif reached the Heart"
    );
}

// ---- Gloamfen, authored (scripts/gloamfen_design.py) ------------------------------------------------------------------

#[test]
fn the_fen_outposts_are_sanctuaries_with_their_people() {
    let w = world();
    let map = &w.maps[3];
    assert_eq!(
        map.camps.len(),
        3,
        "Reedhallow, Dikewatch and Garrison's Rest"
    );
    for id in [
        "fen_rh_brid",
        "fen_rh_sten",
        "fen_rh_trader",
        "travel_reedhallow",
        "fen_dk_magnus",
        "fen_dk_linnea",
        "fen_dk_trader",
        "travel_dikewatch",
        "fen_gr_ysolde",
        "fen_gr_per",
        "fen_gr_trader",
        "travel_lastlight",
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
                .filter(|s| s.zone == 3 && s.state != "waiting")
                .all(|s| s.point().distance(spot) > 8.),
            "no enemy within eight units of {id}"
        );
    }
    for hub in ["reedhallow", "dikewatch", "lastlight"] {
        let find = |id: String| map.npcs.iter().find(|n| n.id == id).unwrap();
        let (b, m) = (
            find(format!("mailbox_3_{hub}")),
            find(format!("travel_{hub}")),
        );
        let (spot, anchor) = (at(b.x, b.y), at(m.x, m.y));
        let mut q = spot;
        map.collide(&mut q, 0.6);
        assert!(q.distance(spot) < 0.01, "{hub}: mailbox blocked");
        assert!(map.line_clear(anchor, spot, 0.4), "{hub}: mailbox approach");
    }
    let master = map
        .npcs
        .iter()
        .find(|n| n.id == "travel_lanternmere")
        .unwrap();
    for hub in ["reedhallow", "dikewatch", "lastlight"] {
        assert!(
            master
                .travel_links
                .iter()
                .any(|l| l == &format!("travel_{hub}")),
            "Lanternmere's Travel Master links to {hub}"
        );
    }
}

#[test]
fn every_fen_quest_can_be_done_on_the_map() {
    let w = world();
    let map = &w.maps[3];
    let mut played = 0;
    for q in map.quests.iter().filter(|q| !q.id.starts_with("es_")) {
        assert!((15..=20).contains(&q.level), "{}: level {}", q.id, q.level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
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
                    w.slimes.iter().any(|s| s.zone == 3 && s.kind == o.target),
                    "{}: enemy {}",
                    q.id,
                    o.target
                ),
                "bring" => assert!(
                    w.slimes
                        .iter()
                        .any(|s| s.zone == 3 && crate::items::material(&s.kind) == o.target),
                    "{}: some enemy of the fen drops {}",
                    q.id,
                    o.target
                ),
                _ => {}
            }
            played += 1;
        }
        assert!(
            map.npcs.iter().any(|n| n.id == q.npc),
            "{}: giver {} is in the fen",
            q.id,
            q.npc
        );
        if let Some(id) = &q.requires {
            let pre = map.quests.iter().find(|p| &p.id == id).unwrap();
            assert!(pre.level <= q.level, "{} unlocks upward", q.id);
        }
    }
    assert!(played > 40, "the walk covers the whole chain: {played}");
    // every new quest and person is a `fen_` id
    for q in map.quests.iter().filter(|q| q.id.starts_with("fen_")) {
        assert!(q.id.len() <= 19, "{}: the accept string must fit", q.id);
    }
}

#[test]
fn the_fen_has_three_elites_two_with_a_quest() {
    let w = world();
    let quests = &w.maps[3].quests;
    for (kind, quest) in [
        ("gloomroot", true),
        ("bellowmaw", true),
        ("rustmarshal", false),
    ] {
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 3 && s.kind == kind)
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
fn a_fen_road_reaches_every_gate_and_the_water_is_solid_with_fords() {
    let w = world();
    let map = &w.maps[3];
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let paths = data["zones"][2]["paths"].as_array().unwrap();
    for p in map.portals.iter().filter(|p| p.seam.is_none()) {
        let near = paths.iter().flat_map(|r| r.as_array().unwrap()).any(|q| {
            at(q[0].as_f64().unwrap(), q[1].as_f64().unwrap()).distance(at(p.x, p.y)) < 2.
        });
        assert!(near, "a road reaches {}", p.id);
    }
    let water: Vec<&Value> = data["zones"][2]["objects"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["kind"] == "water")
        .collect();
    assert!(water.len() > 400, "{} water circles", water.len());
    let o = water[water.len() / 2];
    let spot = at(o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
    let mut q = spot;
    map.collide(&mut q, PLAYER_RADIUS);
    assert!(q.distance(spot) > 0.1, "the water is solid");
    // the water the camera can see from inside Skaldholm is never drawn from there: none stands east of x = 222
    for o in &water {
        assert!(
            o["x"].as_f64().unwrap() + o["r"].as_f64().unwrap() < 222.,
            "water inside the vault view"
        );
    }
    for road in paths {
        let pts = road.as_array().unwrap();
        for leg in pts.windows(2) {
            let (a, b) = (
                at(leg[0][0].as_f64().unwrap(), leg[0][1].as_f64().unwrap()),
                at(leg[1][0].as_f64().unwrap(), leg[1][1].as_f64().unwrap()),
            );
            for k in 0..=24 {
                let t = k as f64 / 24.;
                let spot = at(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t);
                if map.in_city(spot) {
                    continue;
                }
                let mut q = spot;
                map.collide(&mut q, PLAYER_RADIUS);
                assert!(q.distance(spot) < 1e-6, "the road is clear at {spot:?}");
            }
        }
    }
}

fn fen_hero(w: &mut World, x: f64, y: f64, level: u32, quest: &str) -> mpsc::Receiver<Value> {
    let rx = meadow_hero(w, x, y, level, quest);
    w.players.get_mut(&1).unwrap().character.zone = 3;
    rx
}

fn fen_hold(spot: (f64, f64), level: u32, quest: &str, prefix: &str) {
    let mut w = world();
    let _rx = fen_hero(&mut w, spot.0, spot.1, level, quest);
    let sleepers = |w: &World| {
        w.spawns
            .iter()
            .enumerate()
            .filter(|(_, s)| s.ambush.as_deref().is_some_and(|t| t.starts_with(prefix)))
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
        c.quests.iter().find(|q| q.id == quest).unwrap().counts[0] >= 20,
        "the hold is complete"
    );
}

#[test]
fn the_failing_wicks_wake_the_bank_and_count_twenty_seconds() {
    fen_hold((86., 128.), 16, "fen_rh_wicks", "fen_wick_m");
}

#[test]
fn the_dike_breach_wakes_the_shore_and_counts_twenty_seconds() {
    fen_hold((176., 240.), 18, "fen_dk_breach", "fen_breach_m");
}

#[test]
fn per_walks_the_survey_from_the_rest_over_the_causeway_to_hydra_isle() {
    let mut w = world();
    let per = w.maps[3]
        .npcs
        .iter()
        .find(|n| n.id == "fen_gr_per")
        .unwrap()
        .clone();
    let route = &per.escort.as_ref().unwrap().route;
    for leg in route.windows(2) {
        let (from, to) = (at(leg[0][0], leg[0][1]), at(leg[1][0], leg[1][1]));
        for k in 0..=20 {
            let t = k as f64 / 20.;
            let spot = at(from.x + (to.x - from.x) * t, from.y + (to.y - from.y) * t);
            let mut q = spot;
            w.maps[3].collide(&mut q, PLAYER_RADIUS);
            assert!(q.distance(spot) < 1e-6, "the way is clear at {spot:?}");
        }
    }
    let _rx = fen_hero(&mut w, per.x, per.y + 1., 19, "fen_gr_chart");
    w.time += 1.;
    w.interact(1, "fen_gr_per", None);
    let owner = w.players[&1].character.id.clone();
    let escort = w.escort_of(&owner).expect("Per joins");
    for _ in 0..(170. / TICK) as usize {
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
        for s in w.slimes.iter_mut().filter(|s| s.zone == 3 && !s.dead) {
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
            .find(|q| q.id == "fen_gr_chart")
            .unwrap()
            .counts[0],
        1,
        "Per reached Hydra Isle"
    );
}

#[test]
fn walking_down_rimeveils_wall_into_the_last_wedge_never_shuts_a_hero_in() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (sx, sy, dx, dy) in [
        (224.5, 270., 0., 1.),
        (224.5, 270., -0.3, 1.),
        (216., 285., 0.7, 0.7),
        (224.5, 286., 0., 1.),
        (224.5, 286., 1., 1.),
    ] {
        place(&mut w, 1, 2, at(sx, sy));
        for _ in 0..600 {
            w.time += TICK;
            let hero = w.players.get_mut(&1).unwrap();
            hero.input = at(dx, dy);
            hero.input_at = w.time;
            w.update_player(1);
        }
        let c = w.players[&1].character.clone();
        let spot = at(c.x, c.y);
        // wherever the hero ends, in the wedge or across the border, it can walk away again
        let zone = c.zone;
        let mut moved = 0.;
        for k in 0..8 {
            let a = k as f64 * std::f64::consts::FRAC_PI_4;
            let mut p = spot;
            w.maps[zone].walk(&mut p, at(a.cos(), a.sin()), 6., PLAYER_RADIUS);
            moved += p.distance(spot);
        }
        assert!(
            moved > 20.,
            "shut in at zone {zone} ({:.1},{:.1}) after walking from ({sx},{sy}): {moved}",
            c.x,
            c.y
        );
        if zone == 3 {
            assert!(
                c.x < 246.5,
                "arrived inside Skaldholm's wall at ({:.1},{:.1})",
                c.x,
                c.y
            );
        }
    }
}

// ---- the Wyrdwood as an authored map (scripts/wyrdwood_design.py) ---------------------------------------------------------
const WYRD_HUBS: [&str; 3] = ["gallowsfoot", "ridgewatch", "highmoor"];

#[test]
fn the_wyrdwood_outposts_are_sanctuaries_with_their_people() {
    let w = world();
    let map = &w.maps[6];
    assert_eq!(
        map.camps.len(),
        4,
        "Skuldwatch, Gallowsfoot, Ridgewatch and Highmoor Hold"
    );
    for id in [
        "wyrd_gf_hild",
        "wyrd_gf_orm",
        "wyrd_gf_trader",
        "travel_gallowsfoot",
        "wyrd_rw_dagny",
        "wyrd_rw_fenn",
        "wyrd_rw_trader",
        "travel_ridgewatch",
        "wyrd_hm_sunniva",
        "wyrd_hm_loom",
        "wyrd_hm_trader",
        "travel_highmoor",
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
                .filter(|s| s.zone == 6 && s.state != "waiting")
                .all(|s| s.point().distance(spot) > 8.),
            "no enemy within eight units of {id}"
        );
    }
    for hub in [
        "hollowmoot",
        "skuldwatch",
        "gallowsfoot",
        "ridgewatch",
        "highmoor",
    ] {
        let find = |id: String| map.npcs.iter().find(|n| n.id == id).unwrap();
        let (b, m) = (
            find(format!("mailbox_6_{hub}")),
            find(format!("travel_{hub}")),
        );
        let (spot, anchor) = (at(b.x, b.y), at(m.x, m.y));
        let mut q = spot;
        map.collide(&mut q, 0.6);
        assert!(q.distance(spot) < 0.01, "{hub}: mailbox blocked");
        assert!(map.line_clear(anchor, spot, 0.4), "{hub}: mailbox approach");
    }
    // the mail directory is in the shaped frame too
    let dir: Vec<Value> =
        serde_json::from_str(include_str!("../../../world/mailboxes.txt")).unwrap();
    for hub in [
        "hollowmoot",
        "skuldwatch",
        "gallowsfoot",
        "ridgewatch",
        "highmoor",
    ] {
        let entry = dir
            .iter()
            .find(|d| d["id"] == format!("mailbox_6_{hub}"))
            .unwrap_or_else(|| panic!("{hub} is in the mail directory"));
        let b = map
            .npcs
            .iter()
            .find(|n| n.id == format!("mailbox_6_{hub}"))
            .unwrap();
        assert!(
            (entry["x"].as_f64().unwrap() - b.x).abs() < 0.01
                && (entry["y"].as_f64().unwrap() - b.y).abs() < 0.01,
            "{hub}: the directory holds the mailbox where it stands"
        );
    }
    let skuld = map
        .npcs
        .iter()
        .find(|n| n.id == "travel_skuldwatch")
        .unwrap();
    for hub in WYRD_HUBS {
        assert!(
            skuld
                .travel_links
                .iter()
                .any(|l| l == &format!("travel_{hub}")),
            "Skuldwatch's Travel Master links to {hub}"
        );
    }
}

#[test]
fn every_wyrdwood_quest_can_be_done_on_the_map() {
    let w = world();
    let map = &w.maps[6];
    let mut played = 0;
    for q in map.quests.iter().filter(|q| q.id.starts_with("wyrd_")) {
        assert!((20..=30).contains(&q.level), "{}: level {}", q.id, q.level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
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
                    w.slimes.iter().any(|s| s.zone == 6 && s.kind == o.target),
                    "{}: enemy {}",
                    q.id,
                    o.target
                ),
                "bring" => assert!(
                    w.slimes
                        .iter()
                        .any(|s| s.zone == 6 && crate::items::material(&s.kind) == o.target),
                    "{}: some enemy of the Wyrdwood drops {}",
                    q.id,
                    o.target
                ),
                _ => {}
            }
            played += 1;
        }
        assert!(
            map.npcs.iter().any(|n| n.id == q.npc),
            "{}: giver {} is in the Wyrdwood",
            q.id,
            q.npc
        );
        if let Some(id) = &q.requires {
            let pre = map.quests.iter().find(|p| &p.id == id).unwrap();
            assert!(pre.level <= q.level, "{} unlocks upward", q.id);
        }
        assert!(q.id.len() <= 19, "{}: the accept string must fit", q.id);
    }
    assert!(played > 55, "the walk covers the whole chain: {played}");
    // the fourteen new quests
    for id in [
        "wyrd_h_wood",
        "wyrd_s_bridge",
        "wyrd_gf_quills",
        "wyrd_gf_hush",
        "wyrd_gf_vigil",
        "wyrd_gf_mill",
        "wyrd_rw_orders",
        "wyrd_rw_horns",
        "wyrd_rw_gap",
        "wyrd_rw_fire",
        "wyrd_hm_rams",
        "wyrd_hm_threads",
        "wyrd_hm_ring",
        "wyrd_hm_gale",
    ] {
        assert!(map.quests.iter().any(|q| q.id == id), "{id}");
    }
}

#[test]
fn the_wyrdwood_has_three_elites_two_with_a_quest() {
    let w = world();
    let quests = &w.maps[6].quests;
    for (kind, quest) in [("oakhorn", true), ("hrungnir", true), ("hangedking", false)] {
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 6 && s.kind == kind)
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
fn a_wyrdwood_road_reaches_every_gate_and_the_river_is_solid() {
    let w = world();
    let map = &w.maps[6];
    let data = bundled();
    let z = zone_of(&data, 6);
    let paths = z["paths"].as_array().unwrap();
    for p in map.portals.iter().filter(|p| p.seam.is_none()) {
        let near = paths.iter().flat_map(|r| r.as_array().unwrap()).any(|q| {
            at(q[0].as_f64().unwrap(), q[1].as_f64().unwrap()).distance(at(p.x, p.y)) < 2.
        });
        assert!(near, "a road reaches {}", p.id);
    }
    let water: Vec<&Value> = z["objects"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["kind"] == "water")
        .collect();
    assert!(water.len() > 300, "{} water circles", water.len());
    let o = water[water.len() / 2];
    let spot = at(o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
    let mut q = spot;
    map.collide(&mut q, PLAYER_RADIUS);
    assert!(q.distance(spot) > 0.1, "the water is solid");
    // neither neighbour with a seam draws water: none stands within 16 tiles of one
    let seams: Vec<(f64, f64)> = z["portals"]
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
    for o in &water {
        let (x, y) = (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
        assert!(
            seams.iter().all(|q| (q.0 - x).hypot(q.1 - y) > 16.),
            "water at ({x},{y}) is near a seam"
        );
    }
    for road in paths {
        let pts = road.as_array().unwrap();
        for leg in pts.windows(2) {
            let (a, b) = (
                at(leg[0][0].as_f64().unwrap(), leg[0][1].as_f64().unwrap()),
                at(leg[1][0].as_f64().unwrap(), leg[1][1].as_f64().unwrap()),
            );
            for k in 0..=24 {
                let t = k as f64 / 24.;
                let spot = at(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t);
                if map.in_city(spot) {
                    continue;
                }
                let mut q = spot;
                map.collide(&mut q, PLAYER_RADIUS);
                assert!(q.distance(spot) < 1e-6, "the road is clear at {spot:?}");
            }
        }
    }
    // no art-less building stands within the camera's reach of a seam: the other side draws none of them
    for o in z["objects"].as_array().unwrap() {
        let kind = o["kind"].as_str().unwrap();
        if [
            "house",
            "tent",
            "stall",
            "noticeboard",
            "campfire",
            "brazier",
            "bench",
            "lamp",
            "chapel",
            "post",
        ]
        .contains(&kind)
        {
            let (x, y) = (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap());
            for pair in z["portals"]
                .as_array()
                .unwrap()
                .iter()
                .filter_map(|p| p.get("seam"))
                .flat_map(|s| {
                    let pts = s["points"].as_array().unwrap();
                    (0..pts.len() - 1)
                        .map(|i| (pts[i].clone(), pts[i + 1].clone()))
                        .collect::<Vec<_>>()
                })
            {
                let (ax, ay, bx, by) = (
                    pair.0[0].as_f64().unwrap(),
                    pair.0[1].as_f64().unwrap(),
                    pair.1[0].as_f64().unwrap(),
                    pair.1[1].as_f64().unwrap(),
                );
                let (dx, dy) = (bx - ax, by - ay);
                let t = (((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)).clamp(0., 1.);
                assert!(
                    (x - ax - t * dx).hypot(y - ay - t * dy) >= 20.,
                    "{kind} at ({x},{y}) is within 20 tiles of a seam"
                );
            }
        }
    }
}

fn wyrd_hero(w: &mut World, x: f64, y: f64, level: u32, quest: &str) -> mpsc::Receiver<Value> {
    let rx = meadow_hero(w, x, y, level, quest);
    w.players.get_mut(&1).unwrap().character.zone = 6;
    rx
}

fn wyrd_hold(place: &str, level: u32, quest: &str, prefix: &str) {
    let mut w = world();
    let spot = {
        let p = w.maps[6].places.iter().find(|p| p.id == place).unwrap();
        (p.x, p.y)
    };
    let _rx = wyrd_hero(&mut w, spot.0, spot.1, level, quest);
    let sleepers = |w: &World| {
        w.spawns
            .iter()
            .enumerate()
            .filter(|(_, s)| s.ambush.as_deref().is_some_and(|t| t.starts_with(prefix)))
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
        c.quests.iter().find(|q| q.id == quest).unwrap().counts[0] >= 20,
        "the hold is complete"
    );
}

#[test]
fn the_hanged_vigil_wakes_the_hill_and_counts_twenty_seconds() {
    wyrd_hold("wyrd_vigil_m", 25, "wyrd_gf_vigil", "wyrd_vigil_m");
}

#[test]
fn the_ridge_fire_wakes_the_terrace_and_counts_twenty_seconds() {
    wyrd_hold("wyrd_fire_m", 29, "wyrd_rw_fire", "wyrd_fire_m");
}

#[test]
fn the_gale_stones_wake_the_highmoor_and_count_twenty_seconds() {
    wyrd_hold("wyrd_gale_m", 30, "wyrd_hm_gale", "wyrd_gale_m");
}

#[test]
fn the_bridgehead_wakes_the_bank_and_counts_twenty_seconds() {
    wyrd_hold("wyrd_bridge_m", 26, "wyrd_s_bridge", "wyrd_bridge_m");
}
