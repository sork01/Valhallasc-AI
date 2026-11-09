//! The Yearwheel (zone 28, levels 95-99) as an authored map on the shapes pilot, at its own scale (k = 2.8, grid 888): four season towns round the Equinox Crossing, three outposts, thirteen elites,
//! the four sealed doors and the Black Hour Foundry's, a wall on the Lapis and Frostwake sides, and ONE crossing to Sunward Vale: a seamless vault.
use super::wyrd_tests::{at, blocked, flood, join, lines, place, reached, world};
use super::*;

const YEAR: usize = 28;
const VALE: usize = 20;
const KINDS: [(&str, u32, &str); 17] = [
    ("brooknewt", 95, "newt_ribbon"),
    ("sundarter", 96, "sundarter_scale"),
    ("acornmimic", 97, "amber_acorn"),
    ("snowstoat", 98, "stoat_silverfur"),
    ("bloomtortoise", 95, "bloom_shell"),
    ("petalchimera", 96, "chimera_petal"),
    ("rainseraph", 97, "seraph_rainfeather"),
    ("glasslion", 96, "glasslion_mane"),
    ("sunwheel", 97, "sunwheel_cog"),
    ("firephoenix", 98, "phoenix_ember"),
    ("lanternowl", 97, "lanternowl_eye"),
    ("harvestreaper", 98, "reaper_scythe_shard"),
    ("ambermantis", 99, "amber_mantis_claw"),
    ("rimesaber", 97, "rimesaber_fang"),
    ("snowgiant", 98, "snowgiant_heart"),
    ("longnightwyrm", 99, "longnight_scale"),
    ("equinoxstag", 98, "equinox_antler"),
];
/// (outpost, the prefix of its new people)
const OUTPOSTS: [(&str, &str); 3] = [
    ("wheelmark", "yo_wm_"),
    ("tidehollow", "yo_th_"),
    ("lowfall", "yo_lf_"),
];

fn run(w: &mut World, rx: &mut mpsc::Receiver<Value>, ticks: usize) -> Vec<String> {
    let mut told = vec![];
    for _ in 0..ticks {
        w.step();
        told.extend(lines(rx));
    }
    told
}

fn raw() -> Value {
    serde_json::from_str(include_str!("../../../world/map.txt")).unwrap()
}

fn border_pts(zone: &Value, other: usize) -> Vec<(f64, f64)> {
    zone["shape"]["edges"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["kind"] == "shared" && e["other"] == other)
        .unwrap_or_else(|| panic!("no border with {other}"))["points"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (p[0].as_f64().unwrap(), p[1].as_f64().unwrap()))
        .collect()
}

fn border_dist(pts: &[(f64, f64)], x: f64, y: f64) -> f64 {
    pts.windows(2)
        .map(|s| {
            let (a, b) = (s[0], s[1]);
            let (dx, dy) = (b.0 - a.0, b.1 - a.1);
            let t = (((x - a.0) * dx + (y - a.1) * dy) / (dx * dx + dy * dy)).clamp(0., 1.);
            ((x - a.0 - t * dx).powi(2) + (y - a.1 - t * dy).powi(2)).sqrt()
        })
        .fold(f64::MAX, f64::min)
}

/// the distance along the polyline to the point nearest (x, y)
fn along(pts: &[(f64, f64)], x: f64, y: f64) -> f64 {
    let (mut best, mut at_s, mut s) = (f64::MAX, 0., 0.);
    for seg in pts.windows(2) {
        let (a, b) = (seg[0], seg[1]);
        let (dx, dy) = (b.0 - a.0, b.1 - a.1);
        let len = (dx * dx + dy * dy).sqrt();
        let t = (((x - a.0) * dx + (y - a.1) * dy) / (dx * dx + dy * dy)).clamp(0., 1.);
        let d = ((x - a.0 - t * dx).powi(2) + (y - a.1 - t * dy).powi(2)).sqrt();
        if d < best {
            best = d;
            at_s = s + t * len;
        }
        s += len;
    }
    at_s
}

fn first_land(rows: &[&str], x: usize) -> Option<usize> {
    rows.iter().position(|r| r.as_bytes().get(x) == Some(&b'#'))
}

fn last_land(rows: &[&str], x: usize) -> Option<usize> {
    rows.iter()
        .rposition(|r| r.as_bytes().get(x) == Some(&b'#'))
}

fn floor_rows(zone: &Value) -> Vec<&str> {
    zone["shapeFloor"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r.as_str().unwrap())
        .collect()
}

#[test]
fn the_wheel_is_a_big_shaped_zone_with_four_towns_three_outposts_thirteen_elites_and_the_doors() {
    let w = world();
    let m = &w.maps[YEAR];
    assert_eq!(
        (m.name.as_str(), m.size, m.levels),
        ("The Yearwheel", 888, Some([95, 99]))
    );
    let data = raw();
    let z = &data["zones"][YEAR - 1];
    assert_eq!(z["shape"]["k"], 2.8, "the Yearwheel keeps its own scale");
    assert_eq!(z["yearCentre"], serde_json::json!([440, 480]));
    assert_eq!(
        z["camps"].as_array().unwrap().len(),
        6,
        "three old camps and three outposts"
    );
    assert_eq!(z["city"]["name"], "Springmere");
    let future = z["futureInstances"].as_array().unwrap();
    assert_eq!(future.len(), 4);
    assert!(future.iter().all(|door| door["status"] == "open"));
    // 40 old quests keep their ids, 15 are new
    assert_eq!(m.quests.len(), 55);
    for old in [
        "yr_sp_intro",
        "yr_su_solar_final",
        "yr_au_amber_trials",
        "yr_wi_sols_final",
        "yr_onward",
        "null_keys",
        "entry_solstice",
        "es_24",
        "es_go_24",
    ] {
        assert!(
            m.quests.iter().any(|q| q.id == old),
            "old quest {old} is gone"
        );
    }
    assert_eq!(
        m.quests.iter().filter(|q| q.id.starts_with("yrs_")).count(),
        15
    );
    for q in &m.quests {
        // (the Empty Seat's rewardless hand-offs pay nothing)
        if !q.id.starts_with("es_go_") {
            assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
        }
        assert!(format!("quest:accept:{}", q.id).len() <= 32, "{}", q.id);
    }
    assert!(m.slimes.len() > 400, "{} spawns", m.slimes.len());
    // the portals: four sealed doors, the Foundry's, and the vault: nothing else
    assert_eq!(m.portals.len(), 6);
    for (id, to) in [
        ("year_bloom_descent", 36),
        ("year_solar_descent", 37),
        ("year_amber_descent", 38),
        ("year_solstice_descent", 39),
        ("year_blackhour", 44),
        ("path_28_20", VALE),
    ] {
        assert!(m.portals.iter().any(|p| p.id == id && p.to == to), "{id}");
    }
    // the Spark network: the four towns and the three outposts, every link both ways
    let mut masters: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for map in &w.maps {
        for n in map.npcs.iter().filter(|n| n.travel_stop.is_some()) {
            masters.insert(n.id.clone(), n.travel_links.clone());
        }
    }
    for stop in [
        "springmere",
        "solhaven",
        "harvestwatch",
        "rimehold",
        "wheelmark",
        "tidehollow",
        "lowfall",
    ] {
        let id = format!("travel_{stop}");
        let links = masters.get(&id).unwrap_or_else(|| panic!("no {id}"));
        assert!(links.len() >= 2, "{id}");
        for other in links {
            assert!(
                masters.get(other).is_some_and(|l| l.contains(&id)),
                "{id} -> {other} is not reciprocal"
            );
        }
    }
    let springmere = &masters["travel_springmere"];
    assert!(
        springmere.contains(&"travel_millbridge".to_string())
            && springmere.contains(&"travel_wickerfield".to_string()),
        "Sunward's masters link to Springmere"
    );
    // Lapis and Frostwake have no portal to the wheel any more
    for map in [&w.maps[25], &w.maps[26]] {
        assert!(
            !map.portals.iter().any(|p| p.to == YEAR),
            "{} has a portal to the Yearwheel",
            map.name
        );
    }
}

#[test]
fn each_outpost_is_a_sanctuary_with_two_givers_a_trader_a_travel_master_and_a_mailbox() {
    let w = world();
    let m = &w.maps[YEAR];
    let data = raw();
    let z = &data["zones"][YEAR - 1];
    for (key, prefix) in OUTPOSTS {
        let people: Vec<_> = m.npcs.iter().filter(|n| n.id.starts_with(prefix)).collect();
        assert_eq!(people.len(), 3, "{key}: two givers and a trader");
        assert!(people.iter().any(|n| n.buys), "{key}: a trader");
        assert!(
            m.npcs.iter().any(|n| n.id == format!("travel_{key}")),
            "{key}: a Spark master"
        );
        assert!(
            m.npcs.iter().any(|n| n.id == format!("mailbox_28_{key}")),
            "{key}: a mailbox"
        );
        let camp = z["camps"]
            .as_array()
            .unwrap()
            .iter()
            .find(|c| c["name"].as_str().unwrap().to_lowercase().starts_with(key))
            .unwrap_or_else(|| panic!("no camp {key}"));
        let f = |k: &str| camp[k].as_f64().unwrap();
        for n in people {
            assert!(
                n.x > f("x0") && n.x < f("x1") && n.y > f("y0") && n.y < f("y1"),
                "{} stands outside its camp",
                n.id
            );
        }
    }
    let directory: Value =
        serde_json::from_str(include_str!("../../../world/mailboxes.txt")).unwrap();
    assert_eq!(
        directory
            .as_array()
            .unwrap()
            .iter()
            .filter(|d| d["zone"] == 28)
            .count(),
        7,
        "one mailbox per hub"
    );
}

#[test]
fn seasonal_enemies_loot_and_elite_courts() {
    let w = world();
    let m = &w.maps[YEAR];
    for (kind, level, drop) in KINDS {
        assert!(
            m.slimes.iter().any(|s| s.kind == kind),
            "{kind} has no spawn"
        );
        assert_eq!(Slime::default_level(kind), level);
        assert_eq!(material(kind), drop);
        assert!(item(drop).is_some(), "{drop}");
    }
    assert_eq!(m.slimes.iter().filter(|s| is_elite(&s.kind)).count(), 13);
    // the new elite has no quest
    let quests = m
        .quests
        .iter()
        .flat_map(|q| q.objectives.iter())
        .filter(|o| o.target == "equinoxstag")
        .count();
    assert_eq!(quests, 0, "the Equinox Stag has no quest");
    // every elite stands clear of every road, hub, gate, place and person: awareness + 3
    let data = raw();
    let z = &data["zones"][YEAR - 1];
    let mut walked: Vec<(f64, f64)> = vec![];
    for road in z["paths"].as_array().unwrap() {
        let pts: Vec<(f64, f64)> = road
            .as_array()
            .unwrap()
            .iter()
            .map(|p| (p[0].as_f64().unwrap(), p[1].as_f64().unwrap()))
            .collect();
        for s in pts.windows(2) {
            let n = (((s[1].0 - s[0].0).powi(2) + (s[1].1 - s[0].1).powi(2)).sqrt() / 3.)
                .ceil()
                .max(1.) as usize;
            walked.extend((0..=n).map(|i| {
                (
                    s[0].0 + (s[1].0 - s[0].0) * i as f64 / n as f64,
                    s[0].1 + (s[1].1 - s[0].1) * i as f64 / n as f64,
                )
            }));
        }
    }
    walked.extend(m.places.iter().map(|p| (p.x, p.y)));
    walked.extend(m.npcs.iter().map(|n| (n.x, n.y)));
    walked.extend(m.portals.iter().map(|p| (p.x, p.y)));
    for s in m.slimes.iter().filter(|s| is_elite(&s.kind)) {
        let awareness = Slime::attack_profile(&s.kind).3;
        let near = walked
            .iter()
            .map(|q| ((q.0 - s.x).powi(2) + (q.1 - s.y).powi(2)).sqrt())
            .fold(f64::MAX, f64::min);
        assert!(
            near >= awareness + 3. - 0.5,
            "{} stands {near:.1} tiles from something walked to (awareness {awareness})",
            s.kind
        );
    }
}

#[test]
fn the_lapis_and_frostwake_borders_are_walled_with_no_way_through_and_the_sunward_border_with_one_gap()
 {
    let data = raw();
    let zone = &data["zones"][YEAR - 1];
    let objects = zone["objects"].as_array().unwrap();
    let pieces: Vec<(f64, f64)> = objects
        .iter()
        .filter(|o| o["kind"] == "rampart" || o["kind"] == "tower")
        .map(|o| (o["x"].as_f64().unwrap(), o["y"].as_f64().unwrap()))
        .collect();
    assert!(objects.iter().filter(|o| o["kind"] == "tower").count() >= 40);
    assert!(pieces.len() >= 600, "{} wall pieces", pieces.len());
    let runs: Vec<(usize, Vec<(f64, f64)>)> = [25, 26, 20]
        .iter()
        .map(|&o| (o, border_pts(zone, o)))
        .collect();
    // every piece stands about 1.7 tiles inside one of the three borders
    for &(x, y) in &pieces {
        let d = runs
            .iter()
            .map(|(_, p)| border_dist(p, x, y))
            .fold(f64::MAX, f64::min);
        // (a tower at an acute corner, where two borders meet, may stand a little nearer one of them)
        assert!(
            (0.2..=2.6).contains(&d),
            "a wall piece {d:.2} tiles from the border at {x:.0},{y:.0}"
        );
    }
    // along each closed border the pieces are never more than 3.4 tiles apart; along the Sunward border there is ONE gap, the vault's
    for (other, pts) in &runs {
        let total: f64 = pts
            .windows(2)
            .map(|s| ((s[1].0 - s[0].0).powi(2) + (s[1].1 - s[0].1).powi(2)).sqrt())
            .sum();
        let mut s: Vec<f64> = pieces
            .iter()
            .filter(|&&(x, y)| border_dist(pts, x, y) < 3.0)
            .map(|&(x, y)| along(pts, x, y))
            .collect();
        s.sort_by(f64::total_cmp);
        let mut gaps = vec![];
        for pair in s.windows(2) {
            if pair[1] - pair[0] > 3.4 {
                gaps.push((pair[0], pair[1]));
            }
        }
        if *other == 20 {
            assert_eq!(gaps.len(), 1, "one opening on the Sunward border: {gaps:?}");
            let (a, b) = gaps[0];
            assert!(
                (80. ..=110.).contains(&(b - a)),
                "the opening is the vault's span ({:.0} wide)",
                b - a
            );
        } else {
            assert!(
                gaps.is_empty(),
                "the border with zone {other} has gaps {gaps:?}"
            );
            assert!(
                s.first().unwrap() < &4. && s.last().unwrap() > &(total - 4.),
                "the wall covers the whole border with zone {other}"
            );
        }
    }
    // a walker pushed toward the Lapis and Frostwake borders from 8 tiles inland, at a dozen places, never gets within a body of it
    let w = world();
    let map = &w.maps[YEAR];
    let mut tried = 0;
    for (other, pts) in runs.iter().filter(|(o, _)| *o != 20) {
        for i in 1..13 {
            let k = ((pts.len() - 1) as f64 * i as f64 / 13.) as usize;
            let (a, b) = (pts[k], pts[(k + 1).min(pts.len() - 1)]);
            let (mx, my) = (a.0 + (b.0 - a.0) * 0.5, a.1 + (b.1 - a.1) * 0.5);
            let ln = ((b.0 - a.0).powi(2) + (b.1 - a.1).powi(2)).sqrt().max(1e-9);
            let (mut nx, mut ny) = (-(b.1 - a.1) / ln, (b.0 - a.0) / ln);
            let far = |s: f64| (mx + nx * s - 440.).powi(2) + (my + ny * s - 480.).powi(2);
            if far(5.) > far(-5.) {
                nx = -nx;
                ny = -ny;
            }
            let mut foot = at(mx + nx * 8., my + ny * 8.);
            let mut c = foot;
            map.collide(&mut c, PLAYER_RADIUS);
            if c.distance(foot) > 1e-6 {
                continue;
            }
            tried += 1;
            for _ in 0..90 {
                map.walk(&mut foot, at(-nx, -ny), 0.5, PLAYER_RADIUS);
            }
            assert!(
                border_dist(pts, foot.x, foot.y) > 1.2,
                "a walker got to {:.2} tiles from the border with zone {other} at {mx:.0},{my:.0}",
                border_dist(pts, foot.x, foot.y)
            );
        }
    }
    assert!(tried >= 12, "only {tried} places could be tried");
}

#[test]
fn the_vault_is_one_doorway_in_two_frames_the_shifts_cancel_and_the_borders_meet_cell_for_cell() {
    let data = raw();
    let (vale, year) = (&data["zones"][VALE - 1], &data["zones"][YEAR - 1]);
    let up = vale["portals"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == "path_20_28")
        .unwrap();
    let down = year["portals"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == "path_28_20")
        .unwrap();
    let (va, vb) = (
        up["vault"].as_array().unwrap(),
        down["vault"].as_array().unwrap(),
    );
    let (sx, sy) = (va[0].as_f64().unwrap(), va[1].as_f64().unwrap());
    assert!(
        (sx + vb[0].as_f64().unwrap()).abs() < 1e-9 && (sy + vb[1].as_f64().unwrap()).abs() < 1e-9,
        "the shifts are exact negatives"
    );
    assert!(
        sx.fract() == 0. && sy.fract() == 0.,
        "a whole-tile shift: the two cell grids coincide"
    );
    assert_eq!(up["vault_half"], down["vault_half"]);
    assert_eq!(up["walk"], serde_json::json!([0, -1]));
    assert_eq!(down["walk"], serde_json::json!([0, 1]));
    // the arches stand at the same place in the two frames, and each gate stands 3 tiles past its arch
    let arch = |z: &Value, id: &str| -> Value {
        z["exitArches"]
            .as_array()
            .unwrap()
            .iter()
            .find(|a| a["portal"] == id)
            .unwrap_or_else(|| panic!("no arch for {id}"))
            .clone()
    };
    let (aa, ab) = (arch(vale, "path_20_28"), arch(year, "path_28_20"));
    assert!(
        (aa["x"].as_f64().unwrap() + sx - ab["x"].as_f64().unwrap()).abs() < 0.02
            && (aa["y"].as_f64().unwrap() + sy - ab["y"].as_f64().unwrap()).abs() < 0.02
    );
    assert!((up["y"].as_f64().unwrap() - (aa["y"].as_f64().unwrap() - 3.)).abs() < 0.02);
    assert!((down["y"].as_f64().unwrap() - (ab["y"].as_f64().unwrap() + 3.)).abs() < 0.02);
    // the region polygons: each frame names what the OTHER zone owns beyond the line
    for (z, id, to) in [(vale, "path_20_28", YEAR), (year, "path_28_20", VALE)] {
        let r = z["shape"]["vaultRegions"].as_array().unwrap();
        assert_eq!(r.len(), 1);
        assert_eq!(
            (
                r[0]["portal"].as_str().unwrap(),
                r[0]["to"].as_u64().unwrap() as usize
            ),
            (id, to)
        );
        assert!(r[0]["city"].as_array().unwrap().len() >= 16);
    }
    // the border meets cell for cell: our last land row in a column is the row above Sunward's first, across the whole exact stretch (46 tiles each side)
    let (fv, fy) = (floor_rows(vale), floor_rows(year));
    let ax = aa["x"].as_f64().unwrap() as i64;
    for x in (ax - 46)..=(ax + 46) {
        let top = first_land(&fv, x as usize).expect("Sunward land") as i64 + sy as i64;
        let bottom = last_land(&fy, (x + sx as i64) as usize).expect("Yearwheel land") as i64;
        assert_eq!(
            bottom + 1,
            top,
            "column {x}: the Yearwheel's land ends at {bottom}, Sunward's begins at {top}"
        );
    }
}

#[test]
fn a_hero_walks_through_the_vault_to_the_wheel_and_back_without_a_hop() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let up = w.maps[VALE]
        .portals
        .iter()
        .find(|p| p.id == "path_20_28")
        .unwrap()
        .clone();
    let down = w.maps[YEAR]
        .portals
        .iter()
        .find(|p| p.id == "path_28_20")
        .unwrap()
        .clone();
    let [sx, sy] = up.vault.expect("a vault");
    // the arch is 3 tiles inside the gate (the gate's walk is north)
    let arch = (up.x, up.y + 3.);
    place(&mut w, 1, VALE, at(arch.0, arch.1 + 4.));
    w.message(
        1,
        ClientMessage::Move {
            x: arch.0,
            y: arch.1 - 1.,
        },
    );
    run(&mut w, &mut rx, 80);
    let p = w.players[&1].character.point();
    assert_eq!(
        w.players[&1].character.zone, YEAR,
        "the vault leads to the Yearwheel"
    );
    // no hop: in Sunward's frame the hero is where the walk took it (within a body of the arch line)
    let (hx, hy) = (p.x - sx, p.y - sy);
    assert!(
        (hx - arch.0).abs() < 1.5 && (hy - (arch.1 - 1.)).abs() < 1.5,
        "the hero stands at {hx:.1},{hy:.1} in Sunward's frame, the walk's goal was {:.1},{:.1}",
        arch.0,
        arch.1 - 1.
    );
    let mut foot = p;
    w.maps[YEAR].collide(&mut foot, PLAYER_RADIUS);
    assert!(
        foot.distance(p) < 1e-6,
        "the arrival is free ground in the Yearwheel"
    );
    // and back: from 4 tiles north of the Yearwheel's arch, walking south
    let arch_y = (down.x, down.y - 3.);
    place(&mut w, 1, YEAR, at(arch_y.0, arch_y.1 - 4.));
    w.message(
        1,
        ClientMessage::Move {
            x: arch_y.0,
            y: arch_y.1 + 1.,
        },
    );
    run(&mut w, &mut rx, 80);
    assert_eq!(
        w.players[&1].character.zone, VALE,
        "and back through the vault"
    );
    let q = w.players[&1].character.point();
    let mut foot = q;
    w.maps[VALE].collide(&mut foot, PLAYER_RADIUS);
    assert!(
        foot.distance(q) < 1e-6,
        "the arrival is free ground in Sunward Vale"
    );
    assert!(
        (q.x - (arch_y.0 - sx)).abs() < 1.5 && (q.y - (arch_y.1 + 1. - sy)).abs() < 1.5,
        "the hero comes out where the walk was going ({:.1},{:.1})",
        q.x,
        q.y
    );
}

#[test]
fn everyone_and_everything_on_the_wheel_can_be_walked_to_from_the_vault() {
    let w = world();
    let map = &w.maps[YEAR];
    let open = flood(map, &blocked(map, &[]), map.spawn);
    for n in &map.npcs {
        assert!(reached(map, &open, at(n.x, n.y)), "{} is cut off", n.id);
    }
    for p in &map.places {
        let r = p.r + 1.;
        assert!(
            [(0., 0.), (r, 0.), (-r, 0.), (0., r), (0., -r)]
                .iter()
                .any(|(dx, dy)| reached(map, &open, at(p.x + dx, p.y + dy))),
            "{} is cut off",
            p.id
        );
    }
    for (id, s) in w.spawns.iter().enumerate().filter(|(_, s)| s.zone == YEAR) {
        assert!(
            reached(map, &open, at(s.x, s.y)),
            "{} #{id} is cut off",
            s.kind
        );
    }
    for p in map.portals.iter().filter(|p| p.vault.is_none()) {
        assert!(reached(map, &open, at(p.x, p.y)), "{} is cut off", p.id);
    }
    // the vault itself: the arch is reached on foot (it stands in the pocket past our own border line)
    let down = map.portals.iter().find(|p| p.id == "path_28_20").unwrap();
    assert!(
        reached(map, &open, at(down.x, down.y - 3.)),
        "the vault's arch is cut off"
    );
    // every dungeon door's way home arrives on free ground and no enemy within 8 tiles of the arrival
    for z in w.maps.iter() {
        for p in z
            .portals
            .iter()
            .filter(|p| p.to == YEAR && p.vault.is_none())
        {
            let arrival = at(p.tx, p.ty);
            let mut clear = arrival;
            map.collide(&mut clear, PLAYER_RADIUS);
            assert!(
                clear.distance(arrival) < 1e-6,
                "{}'s arrival is blocked",
                p.id
            );
            assert!(
                w.slimes
                    .iter()
                    .filter(|s| s.zone == YEAR)
                    .all(|s| s.point().distance(arrival) >= 8.),
                "an enemy stands near {}'s arrival",
                p.id
            );
            assert!(
                reached(map, &open, arrival),
                "{}'s arrival is cut off",
                p.id
            );
        }
    }
}
