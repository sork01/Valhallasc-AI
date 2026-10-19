//! Best-rotation search (`DPS-ROTATION`). For a class and level it looks for the priority list (`dps_tests::Rotation`)
//! that deals the most damage to the training dummy in a minute, by hill climbing over the order of the skills and
//! whether each one is off, cast when affordable, or held for. The search runs on a few seeds; the finalists and the
//! mercenaries' own rotation are then measured again on nine other seeds, and the best of those is reported, so a lucky
//! roll in the search is not mistaken for a better rotation. `best_<class>` (ignored) writes the data for
//! `scripts/merge_rotations.py`.
use super::dps_tests::{
    DpsRun, MEASURE_SECONDS, Rotation, Slot, levels, row, run_once, run_with, usable_skills,
};
use super::*;
use crate::skills::SKILLS;
use serde_json::{Value, json};
use std::collections::HashMap;

/// Seeds of the search and of the validation; disjoint on purpose.
const SEARCH_SEEDS: [u64; 2] = [1, 2];
/// The search plays shorter runs than the validation (`DPS_SEARCH_SECONDS`), to climb faster; the finalists are judged on full minutes.
const SEARCH_SECONDS: f64 = 40.;
const VALIDATE_SEEDS: [u64; 9] = [101, 102, 103, 104, 105, 106, 107, 108, 109];
/// A neighbour must beat the current rotation by this much to be taken (the rolls are noisy).
const MIN_GAIN: f64 = 0.003;

struct Search {
    class: Class,
    level: u32,
    seconds: f64,
    cache: HashMap<Rotation, f64>,
    evals: usize,
}
impl Search {
    fn fitness(&mut self, rotation: &Rotation) -> f64 {
        let key = rotation.canonical();
        if let Some(v) = self.cache.get(&key) {
            return *v;
        }
        self.evals += 1;
        let total: f64 = SEARCH_SEEDS
            .iter()
            .map(|&seed| run_with(self.class, self.level, seed, self.seconds, Some(&key)).dps())
            .sum();
        let value = total / SEARCH_SEEDS.len() as f64;
        self.cache.insert(key, value);
        value
    }

    fn neighbours(rotation: &Rotation) -> Vec<Rotation> {
        let rotation = rotation.canonical();
        let n = rotation.order.len();
        let mut out = vec![];
        for i in 0..n {
            for slot in [Slot::Off, Slot::Cast, Slot::Hold] {
                if rotation.order[i].1 != slot {
                    let mut r = rotation.clone();
                    r.order[i].1 = slot;
                    out.push(r);
                }
            }
            // Moving a skill one place earlier covers every reordering over several steps.
            if i > 0 && rotation.order[i].1 != Slot::Off {
                let mut r = rotation.clone();
                r.order.swap(i - 1, i);
                out.push(r);
            }
        }
        out
    }

    /// Steepest ascent from `start`.
    fn climb(&mut self, start: Rotation) -> (Rotation, f64) {
        let mut best = start.canonical();
        let mut best_value = self.fitness(&best);
        loop {
            let mut next: Option<(Rotation, f64)> = None;
            for candidate in Self::neighbours(&best) {
                let v = self.fitness(&candidate);
                if v > best_value * (1. + MIN_GAIN) && next.as_ref().is_none_or(|(_, b)| v > *b) {
                    next = Some((candidate, v));
                }
            }
            match next {
                Some((r, v)) => {
                    best = r;
                    best_value = v;
                }
                None => return (best, best_value),
            }
        }
    }
}

fn rotation_of(ids: &[String], slot: Slot) -> Rotation {
    Rotation {
        order: ids.iter().map(|id| (id.clone(), slot)).collect(),
    }
}

fn median(values: &mut [f64]) -> f64 {
    values.sort_by(|a, b| a.total_cmp(b));
    super::ttk::median(values)
}
fn validate(class: Class, level: u32, seconds: f64, rotation: Option<&Rotation>) -> Vec<DpsRun> {
    VALIDATE_SEEDS
        .iter()
        .map(|&seed| run_with(class, level, seed, seconds, rotation))
        .collect()
}
fn median_dps(runs: &[DpsRun]) -> f64 {
    median(&mut runs.iter().map(DpsRun::dps).collect::<Vec<_>>())
}

fn name_of(id: &str) -> String {
    SKILLS
        .iter()
        .find(|s| s.id == id)
        .map_or(id.to_string(), |s| s.name.clone())
}

/// The best rotation found for one class and level, as a JSON row.
fn best_row(class: Class, level: u32, seconds: f64) -> Value {
    let ids = usable_skills(class, level);
    let reverse: Vec<String> = ids.iter().rev().cloned().collect();
    let mut search = Search {
        class,
        level,
        seconds: std::env::var("DPS_SEARCH_SECONDS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(SEARCH_SECONDS.min(seconds)),
        cache: HashMap::new(),
        evals: 0,
    };
    // Three starts: the mercenaries' order, the same with every skill held for, and the latest (strongest) skill first.
    let starts = [
        (
            "class order, cast when affordable",
            rotation_of(&ids, Slot::Cast),
        ),
        ("class order, all held", rotation_of(&ids, Slot::Hold)),
        (
            "latest skill first, all held",
            rotation_of(&reverse, Slot::Hold),
        ),
    ];
    let mut finalists: Vec<(String, Rotation)> = vec![];
    for (label, start) in starts {
        let (found, _) = search.climb(start);
        if !finalists.iter().any(|(_, r)| *r == found) {
            finalists.push((label.to_string(), found));
        }
    }
    // The finalists, and the mercenaries' own rotation, on seeds the search never saw.
    let brain = validate(class, level, seconds, None);
    let brain_dps = median_dps(&brain);
    let mut best: Option<(String, Rotation, Vec<DpsRun>, f64)> = None;
    let mut tried = vec![];
    for (label, rotation) in finalists {
        let runs = validate(class, level, seconds, Some(&rotation));
        let dps = median_dps(&runs);
        tried.push(json!({"start": label, "dps": (dps * 10.).round() / 10.}));
        if best.as_ref().is_none_or(|b| dps > b.3) {
            best = Some((label, rotation, runs, dps));
        }
    }
    let (label, rotation, runs, dps) = best.unwrap();
    let mut row = row(class, level, &runs);
    let order: Vec<Value> = rotation
        .order
        .iter()
        .map(|(id, slot)| {
            json!({
                "id": id,
                "name": name_of(id),
                "slot": format!("{slot:?}").to_lowercase(),
                "unlock": SKILLS.iter().find(|s| &s.id == id).map_or(0, |s| s.level),
            })
        })
        .collect();
    let object = row.as_object_mut().unwrap();
    object.insert("rotation".into(), Value::Array(order));
    object.insert("startedFrom".into(), json!(label));
    object.insert("brainDps".into(), json!((brain_dps * 10.).round() / 10.));
    object.insert("bestDps".into(), json!((dps * 10.).round() / 10.));
    object.insert(
        "uplift".into(),
        json!(((dps / brain_dps - 1.) * 1000.).round() / 10.),
    );
    object.insert("finalists".into(), Value::Array(tried));
    object.insert("evals".into(), json!(search.evals));
    row
}

/// Every level for one class, the work of one process: `DPS_LEVELS`, `DPS_SECONDS` (default 60) and `DPS_OUT`.
fn report(class: Class) {
    let levels: Vec<u32> = std::env::var("DPS_LEVELS")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .map(|v| v.split(',').map(|s| s.trim().parse().unwrap()).collect())
        .unwrap_or_else(levels);
    let seconds: f64 = std::env::var("DPS_SECONDS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(MEASURE_SECONDS);
    let mut rows = vec![];
    for level in levels {
        let started = std::time::Instant::now();
        let r = best_row(class, level, seconds);
        eprintln!(
            "{class:?} {level}: {} dps against {} for the mercenaries ({}%), {} evals, {:.0} s",
            r["bestDps"],
            r["brainDps"],
            r["uplift"],
            r["evals"],
            started.elapsed().as_secs_f64()
        );
        rows.push(r);
        if let Ok(path) = std::env::var("DPS_OUT") {
            std::fs::write(path, serde_json::to_string_pretty(&rows).unwrap()).unwrap();
        }
    }
    println!("{}", serde_json::to_string_pretty(&rows).unwrap());
}

#[test]
#[ignore = "search; run with scripts/best-rotation-parallel.sh"]
fn best_warrior() {
    report(Class::Warrior);
}
#[test]
#[ignore = "search; run with scripts/best-rotation-parallel.sh"]
fn best_mage() {
    report(Class::Mage);
}
#[test]
#[ignore = "search; run with scripts/best-rotation-parallel.sh"]
fn best_assassin() {
    report(Class::Assassin);
}
#[test]
#[ignore = "search; run with scripts/best-rotation-parallel.sh"]
fn best_priest() {
    report(Class::Priest);
}
#[test]
#[ignore = "search; run with scripts/best-rotation-parallel.sh"]
fn best_hunter() {
    report(Class::Hunter);
}

/// Plays the saved best rotations again and prints each class's median DPS on the validation seeds, so a change to the
/// class attack curve can be measured without searching again. `DPS_ROTATIONS_DIR` holds the `<class>.json` files of a
/// search, `DPS_ROTATION_LEVEL` is the level whose rotation is played (default 99), `DPS_LEVELS` the levels it is played
/// at (default 99; a rotation found at 99 is a good, not a proven best, rotation at the levels below) and `DPS_CLASSES`
/// limits the classes. Lines look like `REPLAY 40 warrior 9876`.
#[test]
#[ignore = "replay; DPS_ROTATIONS_DIR=test-results/best-rotation-XXXX"]
fn replay_best_rotations() {
    let dir = std::env::var("DPS_ROTATIONS_DIR").expect("DPS_ROTATIONS_DIR");
    let list = |var: &str, default: &str| -> Vec<String> {
        std::env::var(var)
            .ok()
            .filter(|v| !v.trim().is_empty())
            .unwrap_or_else(|| default.to_string())
            .split(',')
            .map(|s| s.trim().to_string())
            .collect()
    };
    let rotation_level: u64 = std::env::var("DPS_ROTATION_LEVEL")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(99);
    let measured: Vec<u32> = list("DPS_LEVELS", "99")
        .iter()
        .map(|v| v.parse().unwrap())
        .collect();
    for name in list("DPS_CLASSES", "warrior,mage,assassin,priest,hunter") {
        let class = match name.as_str() {
            "warrior" => Class::Warrior,
            "mage" => Class::Mage,
            "assassin" => Class::Assassin,
            "priest" => Class::Priest,
            "hunter" => Class::Hunter,
            other => panic!("unknown class {other}"),
        };
        let rows: Vec<Value> =
            serde_json::from_str(&std::fs::read_to_string(format!("{dir}/{name}.json")).unwrap())
                .unwrap();
        let found = rows
            .iter()
            .find(|r| r["level"] == rotation_level)
            .unwrap_or_else(|| panic!("no level {rotation_level} for {name}"));
        let rotation = Rotation {
            order: found["rotation"]
                .as_array()
                .unwrap()
                .iter()
                .map(|s| {
                    let slot = match s["slot"].as_str().unwrap() {
                        "off" => Slot::Off,
                        "hold" => Slot::Hold,
                        _ => Slot::Cast,
                    };
                    (s["id"].as_str().unwrap().to_string(), slot)
                })
                .collect(),
        };
        for &level in &measured {
            let runs = validate(class, level, MEASURE_SECONDS, Some(&rotation));
            eprintln!("REPLAY {level} {name} {:.0}", median_dps(&runs));
        }
    }
}

#[test]
fn a_held_skill_is_cast_where_the_mercenary_rotation_starves_it() {
    // At level 40 the assassin's cheap skills eat all its energy and Thousand Cuts (50) is never cast.
    let brain = run_once(Class::Assassin, 40, 1, 40.);
    assert_eq!(brain.sources["thousandcuts"].casts, 0);
    let mut order: Vec<(String, Slot)> = usable_skills(Class::Assassin, 40)
        .into_iter()
        .map(|id| (id, Slot::Cast))
        .collect();
    for (id, slot) in &mut order {
        if id == "thousandcuts" {
            *slot = Slot::Hold;
        }
    }
    order.sort_by_key(|(_, slot)| *slot != Slot::Hold);
    let held = run_with(Class::Assassin, 40, 1, 40., Some(&Rotation { order }));
    assert!(held.sources["thousandcuts"].casts > 0, "{:?}", held.sources);
    assert!(held.sources["thousandcuts"].damage > 0.);
}

#[test]
fn neighbours_reach_every_slot_and_swap_and_equal_rotations_share_a_key() {
    let ids = vec!["a".to_string(), "b".to_string(), "c".to_string()];
    let r = rotation_of(&ids, Slot::Cast);
    // 3 skills x 2 other slots + 2 swaps.
    assert_eq!(Search::neighbours(&r).len(), 8);
    let off_ab = Rotation {
        order: vec![
            ("c".into(), Slot::Cast),
            ("a".into(), Slot::Off),
            ("b".into(), Slot::Off),
        ],
    };
    let off_ba = Rotation {
        order: vec![
            ("c".into(), Slot::Cast),
            ("b".into(), Slot::Off),
            ("a".into(), Slot::Off),
        ],
    };
    assert_eq!(off_ab.canonical(), off_ba.canonical());
}
