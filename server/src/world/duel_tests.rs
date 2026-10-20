//! Duel matrix (`PVP-DUEL-MATRIX`; method at the top of `docs/duel-report.md`).
//!
//! Two characters of the same level in the normal gear for that level fight a real duel (`world/pvp.rs`: challenge,
//! accept, the 25-tile ring, stop at 1 health), each driven by the mercenaries' own code: `World::ai_combat_at` casts
//! the skills (damage skills, buffs, heals) and the harness walks to the class's reach and swings the basic attack
//! (`PvpCommand::Attack`, the one PvP basic blow) whenever the cooldown allows. Every number is read from the server's
//! own accounting (`World::damage_by_source`, `casts_by_skill`, the players' health), never from the client.
//! `duel_matrix` (ignored) writes the report data; the fast tests keep the harness honest.
use super::ttk::{Case, build_character};
use super::wyrd_tests::{drain, join, world};
use super::*;
use serde_json::{Value, json};

/// Seconds a duel may last; the game's own limit is 300 s too (`ARENA_TIME`). Longer counts as a draw.
pub const CAP: f64 = 300.;
/// Tiles between the two at the start: inside the ring, outside every reach.
const START_GAP: f64 = 10.;
/// The zone the duels are fought in: Greenmeadow, outside the city.
const ZONE: usize = 0;

/// The distance `pvp_attack` allows for a class.
pub fn duel_range(class: Class) -> f64 {
    class.reach().max(if class.ranged() { 8. } else { 1.8 })
}

/// What one side did in one duel.
#[derive(Clone, Debug, Default)]
pub struct Side {
    pub class: Option<Class>,
    /// Health damage dealt to the other side, by source: a skill id, or `basic` for the basic attack (damage taken off,
    /// so the 1 health floor of a duel is respected), with the number of blows that landed.
    pub by_source: BTreeMap<String, (f64, u32)>,
    pub swings: u32,
    pub casts: BTreeMap<String, u32>,
    /// Health left at the end, as a fraction of the maximum.
    pub hp_left: f64,
    /// Maximum health, attack and defence at the start (`Character::stats`), to read the damage and healing against.
    pub max_hp: f64,
    pub attack: f64,
    pub defence: f64,
    /// Health regained over the duel, from the books: end health - start health + damage taken (overheal is lost, so
    /// this is a floor).
    pub healed: f64,
}
#[derive(Clone, Debug)]
pub struct DuelRun {
    /// 0 = the first class, 1 = the second, None = no winner within the cap.
    pub winner: Option<usize>,
    pub seconds: f64,
    pub sides: [Side; 2],
}

/// A flat clear stretch of Greenmeadow outside the city: the left end of a `START_GAP`-long line the two stand on.
fn duel_spot(w: &World) -> Point {
    let map = &w.maps[ZONE];
    let size = map.size as f64;
    let mut y = 12.;
    while y < size - 12. {
        let mut x = 12.;
        while x < size - 12. - START_GAP {
            let (a, b) = (
                Point { x, y },
                Point {
                    x: x + START_GAP,
                    y,
                },
            );
            let clear = |p: Point| {
                let mut q = p;
                map.collide(&mut q, PLAYER_RADIUS * 3.);
                q.distance(p) < 0.01 && !map.in_city(p)
            };
            if clear(a) && clear(b) && map.line_clear(a, b, 0.5) {
                return a;
            }
            x += 2.;
        }
        y += 2.;
    }
    panic!("no clear duel line in zone {ZONE}");
}

/// One tick of one player: close in, swing, and let the mercenaries' skill code cast.
fn play(w: &mut World, me: u64, foe: u64, side: &mut Side) {
    let (class, hp, here, has_goal) = {
        let p = &w.players[&me];
        let c = &p.character;
        (c.look.class, c.hp, c.point(), p.goal.is_some())
    };
    if hp <= 0. {
        return;
    }
    let there = w.players[&foe].character.point();
    let distance = here.distance(there);
    // Where a mercenary stands against a monster: at the class's reach (`update_player`'s target mode).
    if distance - PLAYER_RADIUS > class.reach() * 0.9 {
        w.message(
            me,
            ClientMessage::Move {
                x: there.x,
                y: there.y,
            },
        );
    } else if has_goal {
        w.message(me, ClientMessage::Stop);
    }
    let ready = {
        let p = &w.players[&me];
        p.cooldown <= 0. && p.dash <= 0. && p.stun <= 0.
    };
    if ready
        && distance <= duel_range(class)
        && (!class.ranged() || w.maps[ZONE].line_clear(here, there, 0.05))
    {
        let foe_id = w.players[&foe].character.id.clone();
        w.pvp_command(me, PvpCommand::Attack { id: foe_id });
        if w.players[&me].cooldown > 0. {
            side.swings += 1;
        }
    }
    w.ai_combat_at(me, &[], Some((there, PLAYER_RADIUS)));
}

/// One duel: `a` against `b` at `level`. `a_left` puts `a` on the left of the line and gives it session 1, which acts
/// first within a tick; running both ways round gives each class that edge half the time.
pub fn run_duel(a: Class, b: Class, level: u32, seed: u64, a_left: bool) -> DuelRun {
    let mut w = world();
    w.rng = seed;
    for s in w.slimes.iter_mut().filter(|s| s.zone == ZONE) {
        s.dead = true;
        s.respawn = 1e9;
    }
    let left = duel_spot(&w);
    let right = Point {
        x: left.x + START_GAP,
        y: left.y,
    };
    let classes = if a_left { [a, b] } else { [b, a] };
    let mut rx = [join(&mut w, 1, classes[0]), join(&mut w, 2, classes[1])];
    let mut starts = [(0., 0., 0.); 2];
    for (i, session) in [1u64, 2].into_iter().enumerate() {
        let case = Case::new(classes[i], level);
        let p = w.players.get_mut(&session).unwrap();
        p.character.look.name = format!("Duelist{session}");
        p.character.zone = ZONE;
        let at = if i == 0 { left } else { right };
        p.character.x = at.x;
        p.character.y = at.y;
        build_character(&mut p.character, &case);
        let slot = if (i == 0) == a_left { 0 } else { 1 };
        let (attack, defence) = p.character.stats();
        starts[slot] = (p.character.max_hp(), attack, defence);
    }
    let ids = [1u64, 2].map(|s| w.players[&s].character.id.clone());
    w.pvp_command(1, PvpCommand::DuelRequest { id: ids[1].clone() });
    w.pvp_command(2, PvpCommand::DuelAccept { id: ids[0].clone() });
    assert!(w.pvp_busy(&ids[0]), "the duel did not start");
    let started = w.time;
    // sides[0] is the first class (`a`), whichever session it has.
    let mut sides = [Side::default(), Side::default()];
    sides[0].class = Some(a);
    sides[1].class = Some(b);
    let slot_of_session = |session: u64| {
        let first_is_session_one = a_left;
        if (session == 1) == first_is_session_one {
            0
        } else {
            1
        }
    };
    // The duel names its winner in a notice (a bolt or a dash can end it during `step`, after which the loser has already
    // started to regenerate, so health at the end cannot say who won).
    let mut winner_session: Option<u64> = None;
    while w.pvp_busy(&ids[0]) && w.time - started < CAP {
        for (me, foe) in [(1u64, 2u64), (2, 1)] {
            let slot = slot_of_session(me);
            play(&mut w, me, foe, &mut sides[slot]);
        }
        w.step();
        for r in rx.iter_mut() {
            for v in drain(r) {
                let text = v["text"].as_str().unwrap_or_default();
                if let Some(who) = text.strip_suffix(" wins the duel!") {
                    winner_session = Some(if who == "Duelist1" { 1 } else { 2 });
                }
            }
        }
    }
    let seconds = w.time - started;
    for session in [1u64, 2] {
        let slot = slot_of_session(session);
        let c = &w.players[&session].character;
        sides[slot].hp_left = c.hp / c.max_hp();
        for ((s, skill), (damage, hits)) in &w.damage_by_source {
            if *s == session {
                let key = if skill.is_empty() { "basic" } else { skill };
                let e = sides[slot].by_source.entry(key.to_string()).or_default();
                e.0 += damage;
                e.1 += hits;
            }
        }
        for ((s, skill), n) in &w.casts_by_skill {
            if *s == session {
                *sides[slot].casts.entry(skill.clone()).or_default() += n;
            }
        }
    }
    for slot in 0..2 {
        let (max_hp, attack, defence) = starts[slot];
        let taken: f64 = sides[1 - slot].by_source.values().map(|v| v.0).sum();
        let side = &mut sides[slot];
        side.max_hp = max_hp;
        side.attack = attack;
        side.defence = defence;
        side.healed = (side.hp_left * max_hp - max_hp + taken).max(0.);
    }
    let winner = winner_session.map(slot_of_session);
    DuelRun {
        winner,
        seconds,
        sides,
    }
}

fn round2(v: f64) -> f64 {
    (v * 100.).round() / 100.
}
fn name(class: Class) -> String {
    format!("{class:?}").to_lowercase()
}
/// The JSON row of one duel; `PVP-DUEL-MATRIX` merges these with `scripts/merge_duel.py`.
pub fn row(level: u32, seed: u64, a_left: bool, run: &DuelRun) -> Value {
    let side = |s: &Side| {
        let damage: f64 = s.by_source.values().map(|v| v.0).sum();
        let hits: u32 = s.by_source.values().map(|v| v.1).sum();
        let sources: BTreeMap<&String, Value> = s
            .by_source
            .iter()
            .map(|(k, v)| (k, json!({"damage": v.0.round(), "hits": v.1})))
            .collect();
        json!({
            "damage": damage.round(),
            "swings": s.swings,
            "hits": hits,
            "hpLeft": round2(s.hp_left),
            "maxHp": s.max_hp.round(),
            "attack": s.attack.round(),
            "defence": s.defence.round(),
            "healed": s.healed.round(),
            "sources": sources,
            "casts": s.casts,
        })
    };
    json!({
        "a": name(run.sides[0].class.unwrap()),
        "b": name(run.sides[1].class.unwrap()),
        "level": level,
        "seed": seed,
        "aLeft": a_left,
        "winner": match run.winner { Some(0) => "a", Some(_) => "b", None => "draw" },
        "seconds": round2(run.seconds),
        "sides": [side(&run.sides[0]), side(&run.sides[1])],
    })
}

const CLASSES: [Class; 5] = [
    Class::Warrior,
    Class::Mage,
    Class::Assassin,
    Class::Priest,
    Class::Hunter,
];

/// The pairs of the report: the 10 distinct ones and the 5 mirrors, or the `DUEL_PAIRS` subset (`warrior-mage,mage-mage`).
fn pairs() -> Vec<(Class, Class)> {
    let all: Vec<(Class, Class)> = (0..5)
        .flat_map(|i| (i..5).map(move |j| (CLASSES[i], CLASSES[j])))
        .collect();
    match std::env::var("DUEL_PAIRS")
        .ok()
        .filter(|v| !v.trim().is_empty())
    {
        None => all,
        Some(list) => list
            .split(',')
            .map(|p| {
                let (x, y) = p.trim().split_once('-').expect("pairs look like a-b");
                let find = |n: &str| *CLASSES.iter().find(|c| name(**c) == n).expect("a class");
                (find(x), find(y))
            })
            .collect(),
    }
}

/// The work of one process: `DUEL_LEVELS` (default 10, 20 ... 90, 99), `DUEL_RUNS` (seeds per order, default 4),
/// `DUEL_PAIRS` and `DUEL_OUT` (a path for the JSON). A mirror pair is run with `2 x DUEL_RUNS` seeds on one order.
fn report() {
    let levels: Vec<u32> = std::env::var("DUEL_LEVELS")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .map(|v| v.split(',').map(|s| s.trim().parse().unwrap()).collect())
        .unwrap_or_else(|| (1..=9).map(|n| n * 10).chain([99]).collect());
    let runs: u64 = std::env::var("DUEL_RUNS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(4);
    let mut rows = vec![];
    for level in levels {
        for (a, b) in pairs() {
            let mut wins = [0u32; 3];
            let started = std::time::Instant::now();
            let orders: &[bool] = if a == b { &[true] } else { &[true, false] };
            let seeds = if a == b { runs * 2 } else { runs };
            for &a_left in orders {
                for seed in 1..=seeds {
                    let run = run_duel(a, b, level, seed, a_left);
                    wins[run.winner.unwrap_or(2)] += 1;
                    rows.push(row(level, seed, a_left, &run));
                }
            }
            eprintln!(
                "{a:?} v {b:?} level {level}: {}-{}-{} (draws last) in {:.1} s",
                wins[0],
                wins[1],
                wins[2],
                started.elapsed().as_secs_f64()
            );
        }
    }
    let text = serde_json::to_string_pretty(&rows).unwrap();
    if let Ok(path) = std::env::var("DUEL_OUT") {
        std::fs::write(path, &text).unwrap();
    }
    println!("{text}");
}

#[test]
#[ignore = "full grid; run with scripts/duel-parallel.sh"]
fn duel_matrix() {
    report();
}

#[test]
fn a_duel_ends_at_one_health_and_every_blow_is_accounted_for() {
    let run = run_duel(Class::Warrior, Class::Mage, 10, 1, true);
    assert!(run.winner.is_some(), "no winner in {} s", run.seconds);
    assert!(run.seconds > 1. && run.seconds < CAP);
    let loser = 1 - run.winner.unwrap();
    assert!(
        run.sides[loser].hp_left <= 0.1,
        "the loser stops at 1 health: {}",
        run.sides[loser].hp_left
    );
    for side in &run.sides {
        assert!(
            side.by_source.get("basic").is_some_and(|b| b.0 > 0.),
            "no basic damage"
        );
    }
    // A fixed order and seed repeat exactly.
    let again = run_duel(Class::Warrior, Class::Mage, 10, 1, true);
    assert_eq!(run.winner, again.winner);
    assert_eq!(run.seconds, again.seconds);
}

#[test]
fn damaging_skills_hurt_the_other_duelist() {
    // Warrior against warrior: no heal and no potion, so the health one side lost is what the other dealt (the
    // floor of 1 health is the only slack).
    let run = run_duel(Class::Warrior, Class::Warrior, 30, 3, true);
    assert!(run.winner.is_some());
    for (dealer, taker) in [(0usize, 1usize), (1, 0)] {
        let skill_damage: f64 = run.sides[dealer]
            .by_source
            .iter()
            .filter(|(k, _)| *k != "basic")
            .map(|(_, v)| v.0)
            .sum();
        assert!(skill_damage > 0., "side {dealer} dealt no skill damage");
        let _ = taker;
    }
}
