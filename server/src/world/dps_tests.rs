//! Damage-per-second harness (`DPS-HARNESS`; the rules are in TODO.md and the method at the top of `docs/dps-report.md`).
//!
//! One run is a class at a level in the normal gear for that level, playing the mercenaries' rotation (`auto_play`)
//! against a training dummy for 60 seconds from its first hit. The dummy is an ordinary monster of the level made
//! harmless in the harness only: it has no damage, a health pool that cannot run out and no way to move. The game has no
//! enemy defence, resistance or evasion, so the dummy has none either. Every point of damage is read from the server's
//! own accounting (`World::damage_by_source`), never from the client. `dps_<class>` (ignored) writes the report data for
//! `DPS-RUN`; the fast test at the end keeps the harness honest.
use super::ttk::{Case, build_character, pick_enemy};
use super::wyrd_tests::{drain, join, world};
use super::*;
use crate::skills::SKILLS;
use serde_json::{Value, json};

/// Seconds measured, counted from the first point of damage.
pub const MEASURE_SECONDS: f64 = 60.;
/// 10, 20 ... 90 and 99.
pub fn levels() -> Vec<u32> {
    (1..=9).map(|n| n * 10).chain([99]).collect()
}
/// Where the character starts, in tiles from the dummy: well inside every reach, so the walk is not measured. Not at
/// the edge of a reach either: a character that walks in to exactly the reach of a monster that never moves stops
/// a rounding error short of it and never swings (a real monster closes the gap itself).
const START_DISTANCE: f64 = 1.;
/// A character that has not hurt the dummy after this long is a defect of the harness, not a result.
const FIRST_HIT_BY: f64 = 20.;
/// Health of the dummy; a minute of play at level 99 deals under 10^7.
const DUMMY_HP: f64 = 1e15;

/// What one skill (or the basic attack, or a set bonus) did in one run.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Source {
    pub damage: f64,
    pub hits: u32,
    pub casts: u32,
}
#[derive(Clone, Debug)]
pub struct DpsRun {
    /// Seconds from the first point of damage to the end of the run.
    pub seconds: f64,
    pub total: f64,
    /// By source id: a skill id, `basic` or `set_bonus`. Every skill the class has at the level is listed, even at 0.
    pub sources: BTreeMap<String, Source>,
}
impl DpsRun {
    pub fn dps(&self) -> f64 {
        self.total / self.seconds
    }
}

fn source_key(cur_skill: &str) -> String {
    if cur_skill.is_empty() {
        "basic".into()
    } else {
        cur_skill.to_string()
    }
}

/// How a skill takes part in a rotation.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Slot {
    /// Never cast.
    Off,
    /// Cast whenever it is ready, in reach and affordable; when it is ready but not affordable, the skills below it
    /// still get their turn.
    Cast,
    /// As `Cast`, but when it is ready and in reach yet not affordable nothing below it is cast, so the resource builds
    /// up for it.
    Hold,
}
/// A priority list: the first skill that can be cast is cast, every tick. The basic attack runs underneath on its own.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Rotation {
    pub order: Vec<(String, Slot)>,
}
impl Rotation {
    /// The same rotation with the skills that are off moved to the end in id order, so equal rotations compare equal.
    pub fn canonical(&self) -> Self {
        let mut live: Vec<_> = self
            .order
            .iter()
            .filter(|(_, slot)| *slot != Slot::Off)
            .cloned()
            .collect();
        let mut off: Vec<_> = self
            .order
            .iter()
            .filter(|(_, slot)| *slot == Slot::Off)
            .cloned()
            .collect();
        off.sort();
        live.extend(off);
        Self { order: live }
    }
}

/// The skills a rotation can use against a dummy: everything that deals damage or raises it. Heals, shields, dodge and
/// regeneration do nothing here, and a movement-only dash deals nothing.
pub fn usable_skills(class: Class, level: u32) -> Vec<String> {
    use crate::skills::{BuffKind, Effect};
    SKILLS
        .iter()
        .filter(|s| s.class == class && s.level <= level)
        .filter(|s| match &s.effect {
            Effect::Heal { .. } | Effect::Mend { .. } => false,
            Effect::Buff { kind, .. } => {
                matches!(kind, BuffKind::Damage | BuffKind::Haste | BuffKind::Crit)
            }
            Effect::Dash { mult, .. } => *mult > 0.,
            _ => true,
        })
        .map(|s| s.id.clone())
        .collect()
}

/// One tick of a rotation: walks the priority list and casts what the list allows.
fn play_rotation(w: &mut World, session: u64, id: usize, rotation: &Rotation) {
    use crate::skills::{BuffKind, Effect};
    let (me, level) = {
        let c = &w.players[&session].character;
        (c.point(), c.level)
    };
    let (target, radius) = (w.slimes[id].point(), w.slimes[id].r);
    let distance = me.distance(target);
    let aim = me.direction(target);
    for (skill_id, slot) in &rotation.order {
        if *slot == Slot::Off {
            continue;
        }
        let base = SKILLS.iter().find(|s| &s.id == skill_id).unwrap();
        let skill = base.at_level(level);
        let p = &w.players[&session];
        if p.dash > 0. {
            return;
        }
        if p.skill_cd.contains_key(&skill.id) {
            continue;
        }
        let in_reach = match &skill.effect {
            Effect::Cone { reach, .. } => distance - radius <= *reach,
            Effect::Nova { radius: r, .. } => distance - radius <= *r,
            Effect::Strike { range, .. } | Effect::Chain { range, .. } => {
                distance - radius <= *range
            }
            Effect::Meteor { range, .. } => distance <= *range,
            Effect::Volley { .. } => distance <= 9.,
            Effect::Dash { .. } => distance <= 6.,
            Effect::Buff { kind, .. } => {
                matches!(kind, BuffKind::Damage | BuffKind::Haste | BuffKind::Crit)
                    && distance < 10.
                    && !p.buffs.iter().any(|b| b.kind == *kind)
            }
            Effect::Heal { .. } | Effect::Mend { .. } => false,
        };
        if !in_reach {
            continue;
        }
        if p.character.resource() < skill.cost {
            if *slot == Slot::Hold {
                return;
            }
            continue;
        }
        w.use_skill(session, &skill.id, aim);
    }
}

/// One run with the mercenaries' rotation: `class` at `level` for `seconds` after its first hit on the dummy.
pub fn run_once(class: Class, level: u32, seed: u64, seconds: f64) -> DpsRun {
    run_with(class, level, seed, seconds, None)
}

/// One run; `rotation` None plays the mercenaries' code (`auto_play`).
pub fn run_with(
    class: Class,
    level: u32,
    seed: u64,
    seconds: f64,
    rotation: Option<&Rotation>,
) -> DpsRun {
    let mut w = world();
    w.rng = seed;
    let case = Case::new(class, level);
    let id = pick_enemy(&w, level, super::ttk::Foe::Ordinary)
        .unwrap_or_else(|| panic!("no ordinary monster for level {level}"));
    // Only the dummy's own zone is cleared; the rest stays dormant (see ttk.rs).
    let zone = w.slimes[id].zone;
    for s in w.slimes.iter_mut().filter(|s| s.id != id && s.zone == zone) {
        s.dead = true;
        s.respawn = 1e9;
    }
    let spawn = w.spawns[id].clone();
    w.slimes[id] = Slime::with_level(id, &spawn, level);
    {
        let dummy = &mut w.slimes[id];
        dummy.damage = 0.;
        dummy.hp = DUMMY_HP;
        dummy.max_hp = DUMMY_HP;
        // `set_root_left` counts down by a tick each step; this outlasts any run, so the dummy never moves.
        dummy.set_root_left = 1e12;
    }
    let home = w.slimes[id].point();
    let mut rx = join(&mut w, 1, class);
    let start = {
        let map = &w.maps[zone];
        let mut found = None;
        'search: for distance in [START_DISTANCE, 1.2, 1.4] {
            for k in 0..16 {
                let a = k as f64 / 16. * std::f64::consts::TAU;
                let mut p = Point {
                    x: home.x + a.cos() * distance,
                    y: home.y + a.sin() * distance,
                };
                let wanted = p;
                map.collide(&mut p, PLAYER_RADIUS);
                if p.distance(wanted) < 0.01 && map.line_clear(home, p, 0.3) {
                    found = Some(p);
                    break 'search;
                }
            }
        }
        found.unwrap_or_else(|| panic!("no clear start near {home:?} in zone {zone}"))
    };
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = zone;
        c.x = start.x;
        c.y = start.y;
        build_character(c, &case);
    }
    w.enter_instance(zone);
    w.message(1, ClientMessage::Target { id });
    let began = w.time;
    let mut first_hit: Option<f64> = None;
    loop {
        if let Some(t0) = first_hit {
            if w.time - t0 >= seconds {
                break;
            }
        } else if w.time - began > FIRST_HIT_BY {
            panic!("{class:?} level {level} never hurt the dummy in {FIRST_HIT_BY} s");
        }
        assert!(
            w.players[&1].character.hp > 0.,
            "{class:?} level {level} died against a harmless dummy"
        );
        match rotation {
            Some(r) => play_rotation(&mut w, 1, id, r),
            None => w.auto_play(1, &[], Some(id)),
        }
        let before = w.time;
        w.step();
        drain(&mut rx);
        if first_hit.is_none() && w.damage_log.get(&1).copied().unwrap_or(0.) > 0. {
            first_hit = Some(before);
        }
    }
    let elapsed = w.time - first_hit.unwrap();
    let mut sources: BTreeMap<String, Source> = SKILLS
        .iter()
        .filter(|s| s.class == class && s.level <= level)
        .map(|s| (s.id.clone(), Source::default()))
        .collect();
    sources.insert("basic".into(), Source::default());
    for ((session, skill), (damage, hits)) in &w.damage_by_source {
        if *session == 1 {
            let e = sources.entry(source_key(skill)).or_default();
            e.damage += damage;
            e.hits += hits;
        }
    }
    for ((session, skill), casts) in &w.casts_by_skill {
        if *session == 1 {
            sources.entry(skill.clone()).or_default().casts += casts;
        }
    }
    DpsRun {
        seconds: elapsed,
        total: w.damage_log.get(&1).copied().unwrap_or(0.),
        sources,
    }
}

fn median(values: &mut [f64]) -> f64 {
    values.sort_by(|a, b| a.total_cmp(b));
    super::ttk::median(values)
}
fn round1(v: f64) -> f64 {
    (v * 10.).round() / 10.
}
fn round2(v: f64) -> f64 {
    (v * 100.).round() / 100.
}

/// The JSON row for a class and level: the median DPS over the seeds, and each source's mean damage, hits and casts and
/// its share of the total damage in per cent. Shares come from the means, so they add up to 100.
pub fn row(class: Class, level: u32, runs: &[DpsRun]) -> Value {
    let n = runs.len() as f64;
    let mut dps: Vec<f64> = runs.iter().map(DpsRun::dps).collect();
    let (lo, hi) = (
        dps.iter().copied().fold(f64::MAX, f64::min),
        dps.iter().copied().fold(0., f64::max),
    );
    let med = median(&mut dps);
    let mean_total = runs.iter().map(|r| r.total).sum::<f64>() / n;
    let mean_seconds = runs.iter().map(|r| r.seconds).sum::<f64>() / n;
    let ids: Vec<&String> = runs[0].sources.keys().collect();
    let name_of = |id: &str| match id {
        "basic" => "Basic attack".to_string(),
        "set_bonus" => "Set bonus".to_string(),
        _ => SKILLS
            .iter()
            .find(|s| s.id == id)
            .map_or(id.to_string(), |s| s.name.clone()),
    };
    let unlock_of = |id: &str| SKILLS.iter().find(|s| s.id == id).map_or(0, |s| s.level);
    let mut sources: Vec<Value> = ids
        .iter()
        .map(|id| {
            let mean = |f: &dyn Fn(&Source) -> f64| {
                runs.iter().map(|r| f(&r.sources[*id])).sum::<f64>() / n
            };
            let damage = mean(&|s| s.damage);
            json!({
                "id": id,
                "name": name_of(id),
                "unlock": unlock_of(id),
                "damage": damage.round(),
                "share": if mean_total > 0. { round2(damage / mean_total * 100.) } else { 0. },
                "hits": round1(mean(&|s| s.hits as f64)),
                "casts": round1(mean(&|s| s.casts as f64)),
            })
        })
        .collect();
    sources.sort_by(|a, b| {
        b["damage"]
            .as_f64()
            .unwrap()
            .total_cmp(&a["damage"].as_f64().unwrap())
            .then_with(|| a["unlock"].as_u64().cmp(&b["unlock"].as_u64()))
    });
    let uncast: Vec<&str> = runs[0]
        .sources
        .keys()
        .filter(|id| *id != "basic" && *id != "set_bonus")
        .filter(|id| runs.iter().all(|r| r.sources[*id].casts == 0))
        .map(String::as_str)
        .collect();
    json!({
        "class": format!("{class:?}").to_lowercase(),
        "level": level,
        "runs": runs.len(),
        "seconds": round1(mean_seconds),
        "dpsMedian": round1(med),
        "dpsMin": round1(lo),
        "dpsMax": round1(hi),
        "totalMean": mean_total.round(),
        "sources": sources,
        "uncast": uncast,
    })
}

/// Every level of the report for one class, the work of one process: `DPS_LEVELS`, `DPS_RUNS` (default 5),
/// `DPS_SECONDS` (default 60) and `DPS_OUT` (a path for the JSON).
fn report(class: Class) {
    let levels: Vec<u32> = std::env::var("DPS_LEVELS")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .map(|v| v.split(',').map(|s| s.trim().parse().unwrap()).collect())
        .unwrap_or_else(levels);
    let runs: u64 = std::env::var("DPS_RUNS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(5);
    let seconds: f64 = std::env::var("DPS_SECONDS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(MEASURE_SECONDS);
    let mut rows = vec![];
    for level in levels {
        let results: Vec<DpsRun> = (1..=runs)
            .map(|seed| run_once(class, level, seed, seconds))
            .collect();
        let r = row(class, level, &results);
        eprintln!(
            "{class:?} {level}: {} dps, uncast {}",
            r["dpsMedian"], r["uncast"]
        );
        rows.push(r);
    }
    let text = serde_json::to_string_pretty(&rows).unwrap();
    if let Ok(path) = std::env::var("DPS_OUT") {
        std::fs::write(path, &text).unwrap();
    }
    println!("{text}");
}

#[test]
#[ignore = "full grid; run with scripts/dps-parallel.sh"]
fn dps_warrior() {
    report(Class::Warrior);
}
#[test]
#[ignore = "full grid; run with scripts/dps-parallel.sh"]
fn dps_mage() {
    report(Class::Mage);
}
#[test]
#[ignore = "full grid; run with scripts/dps-parallel.sh"]
fn dps_assassin() {
    report(Class::Assassin);
}
#[test]
#[ignore = "full grid; run with scripts/dps-parallel.sh"]
fn dps_priest() {
    report(Class::Priest);
}
#[test]
#[ignore = "full grid; run with scripts/dps-parallel.sh"]
fn dps_hunter() {
    report(Class::Hunter);
}

#[test]
fn dps_run_shares_add_up_and_the_dummy_stays_put() {
    let class = Class::Warrior;
    let run = run_once(class, 10, 1, 20.);
    assert!(run.total > 0., "the warrior hurt the dummy");
    assert!(
        (19.9..21.).contains(&run.seconds),
        "{} s measured",
        run.seconds
    );
    let by_source: f64 = run.sources.values().map(|s| s.damage).sum();
    assert!(
        (by_source - run.total).abs() < 1e-6,
        "sources {by_source} against total {}",
        run.total
    );
    let r = row(class, 10, &[run.clone(), run_once(class, 10, 2, 20.)]);
    let shares: f64 = r["sources"]
        .as_array()
        .unwrap()
        .iter()
        .map(|s| s["share"].as_f64().unwrap())
        .sum();
    assert!((shares - 100.).abs() < 0.5, "shares add up to {shares}");
    assert!(r["dpsMedian"].as_f64().unwrap() > 0.);
}
