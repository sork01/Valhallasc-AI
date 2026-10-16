//! Kill-time harness (`TTK-HARNESS`, rules in `docs/ttk-rules.md`).
//!
//! One case is a class at a level in the normal gear for that level, a stat spread and a rotation, fighting an
//! ordinary (or elite) monster of the same level in the real `World`, one `step()` at a time. Everything runs in memory:
//! `world()` opens `Store::open(":memory:")`, so no live world, no real save and no network is ever touched.
//! `run_case` repeats a case over seeds and reports the median and the spread. `ttk_report` (ignored by default) prints
//! the results for `TTK-RUN`; the fast tests below keep the harness itself honest.
use super::wyrd_tests::{drain, join, world};
use super::*;
use crate::skills::{BuffKind as Buff_, Effect, SKILLS};
use serde::Deserialize;

/// A fight that lasts longer than this is recorded as a failure ("too slow"). The skills run stops at 120 s, above the
/// highest "too slow" line of the rules (90 s), so the verdict is the same; the basic-attack-only run may take 2.5x the
/// ceiling (225 s), so it gets the longer cap.
pub const MAX_SECONDS: f64 = 240.;
pub const SKILLS_CAP_SECONDS: f64 = 120.;
/// A fight whose progress so far projects to more than this many caps is stopped early as a failure.
const HOPELESS_FACTOR: f64 = 3.;
/// The projection is only trusted after this long.
const PROJECT_AFTER: f64 = 30.;

fn cap_for(rotation: Rotation) -> f64 {
    match rotation {
        Rotation::Skills => SKILLS_CAP_SECONDS,
        Rotation::BasicOnly => MAX_SECONDS,
    }
}
/// How far from the monster the character starts, in tiles. Walking in is part of the clock.
const START_DISTANCE: f64 = 8.;
pub const CLASSES: [Class; 5] = [
    Class::Warrior,
    Class::Mage,
    Class::Assassin,
    Class::Priest,
    Class::Hunter,
];
/// 5, 10 ... 95 and 99.
pub fn levels() -> Vec<u32> {
    (1..=19).map(|n| n * 5).chain([99]).collect()
}
/// The eight worn slots of the rules: the equipment-slot name and the catalog kind that fills it.
const SLOTS: [(&str, &str); 8] = [
    ("chest", "armor"),
    ("headgear", "headgear"),
    ("shoulders", "shoulders"),
    ("gloves", "gloves"),
    ("hands", "weapon"),
    ("pants", "pants"),
    ("necklace", "necklace"),
    ("accessory1", "accessory"),
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Spread {
    Even,
    Stamina,
    Damage,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Rotation {
    Skills,
    BasicOnly,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Foe {
    Ordinary,
    Elite,
}
#[derive(Clone, Copy, Debug)]
pub struct Case {
    pub class: Class,
    pub level: u32,
    pub spread: Spread,
    pub rotation: Rotation,
    pub foe: Foe,
    /// The best potion and food tier for the level may be used (the second run of `CONS-AUDIT`).
    pub consumables: bool,
    /// The monster deals no damage, so the run measures the class's own kill speed (it cannot die before the cap).
    pub harmless: bool,
    /// Rarity of the gear worn; the baseline is green.
    pub rarity: &'static str,
    /// Spawn index of the monster to fight instead of the one `pick_enemy` chooses (the group elites of
    /// `ELITE-SOLO-TEST`). The monster is still levelled to `level`.
    pub target: Option<usize>,
}
impl Case {
    pub fn new(class: Class, level: u32) -> Self {
        Self {
            class,
            level,
            spread: Spread::Even,
            rotation: Rotation::Skills,
            foe: Foe::Ordinary,
            consumables: false,
            harmless: false,
            rarity: BASELINE_RARITY,
            target: None,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Outcome {
    pub seed: u64,
    /// Seconds from the first command to the monster's death; for a failure, how long the character lasted.
    pub seconds: f64,
    pub killed: bool,
    pub died: bool,
    pub damage_taken: f64,
    pub hits_taken: u32,
    pub lowest_hp_fraction: f64,
    /// Mana or rage spent on skills.
    pub resource_used: f64,
    pub casts: u32,
    pub potions_used: u32,
    pub food_used: u32,
    /// The monster's health left when the fight ended, as a fraction of its maximum.
    pub enemy_left: f64,
}

#[derive(Clone, Debug)]
pub struct Summary {
    pub case: Case,
    pub enemy: String,
    pub enemy_level: u32,
    pub enemy_hp: f64,
    pub enemy_damage: f64,
    pub character_hp: f64,
    pub runs: Vec<Outcome>,
}
impl Summary {
    fn spread_of(&self, f: impl Fn(&Outcome) -> f64) -> (f64, f64, f64) {
        let mut v: Vec<f64> = self.runs.iter().map(f).collect();
        v.sort_by(|a, b| a.total_cmp(b));
        (median(&v), v[0], v[v.len() - 1])
    }
    /// Median, minimum and maximum seconds. A failed run counts at its full length, which is what "too slow" means.
    pub fn seconds(&self) -> (f64, f64, f64) {
        let cap = cap_for(self.case.rotation);
        self.spread_of(|o| if o.killed { o.seconds } else { cap })
    }
    pub fn damage_taken(&self) -> (f64, f64, f64) {
        self.spread_of(|o| o.damage_taken)
    }
    pub fn failures(&self) -> usize {
        self.runs.iter().filter(|o| !o.killed).count()
    }
    /// Mean damage of one hit that landed on the character, over every run.
    pub fn damage_per_hit(&self) -> f64 {
        let hits: u32 = self.runs.iter().map(|o| o.hits_taken).sum();
        if hits == 0 {
            return 0.;
        }
        self.runs.iter().map(|o| o.damage_taken).sum::<f64>() / hits as f64
    }
    pub fn to_json(&self) -> Value {
        let (s, smin, smax) = self.seconds();
        let (d, dmin, dmax) = self.damage_taken();
        let (r, ..) = self.spread_of(|o| o.resource_used);
        let (low, ..) = self.spread_of(|o| o.lowest_hp_fraction);
        let (p, ..) = self.spread_of(|o| o.potions_used as f64);
        let (dps, ..) = self.spread_of(|o| o.damage_taken / o.seconds.max(1.));
        let hp = self.enemy_hp;
        let (dealt, ..) = self.spread_of(|o| hp * (1. - o.enemy_left) / o.seconds.max(1.));
        json!({
            "class": format!("{:?}", self.case.class).to_lowercase(),
            "level": self.case.level,
            "spread": format!("{:?}", self.case.spread).to_lowercase(),
            "rotation": format!("{:?}", self.case.rotation).to_lowercase(),
            "foe": format!("{:?}", self.case.foe).to_lowercase(),
            "consumables": self.case.consumables,
            "harmless": self.case.harmless,
            "enemy": self.enemy,
            "enemyLevel": self.enemy_level,
            "enemyHp": self.enemy_hp,
            "enemyDamage": self.enemy_damage,
            "characterHp": self.character_hp,
            "runs": self.runs.len(),
            "failures": self.failures(),
            "deaths": self.runs.iter().filter(|o| o.died).count(),
            "seconds": {"median": round1(s), "min": round1(smin), "max": round1(smax)},
            "damageTaken": {"median": d.round(), "min": dmin.round(), "max": dmax.round()},
            "damagePerHit": self.damage_per_hit().round(),
            "damagePerSecond": round1(dps),
            "damageDealtPerSecond": dealt.round(),
            "lowestHpFraction": (low * 100.).round() / 100.,
            "resourceUsed": r.round(),
            "potions": p,
        })
    }
}
fn round1(v: f64) -> f64 {
    (v * 10.).round() / 10.
}
pub fn median(sorted: &[f64]) -> f64 {
    let n = sorted.len();
    if n % 2 == 1 {
        sorted[n / 2]
    } else {
        (sorted[n / 2 - 1] + sorted[n / 2]) / 2.
    }
}

/// The rarity of the baseline gear: green (`uncommon`), as decided on 2026-10-15. Gray is the floor, green is what a
/// character is expected to wear, and blue and better add on top.
pub const BASELINE_RARITY: &str = "uncommon";

/// The normal gear for `level`: the green set whose required level is the level rounded down to a multiple
/// of 5, one piece per slot, with no source, no refinement and no orange or dungeon piece. 99 uses the 95 set.
pub fn gear_level(level: u32) -> u32 {
    (level / 5 * 5).clamp(5, 95)
}
pub fn normal_gear(class: Class, level: u32) -> Vec<(&'static str, String)> {
    normal_gear_of(class, level, BASELINE_RARITY)
}
/// The progression set of `rarity` (`common`, `uncommon`, `rare` or `epic`) for `level`, built like `normal_gear`.
pub fn normal_gear_of(class: Class, level: u32, rarity: &str) -> Vec<(&'static str, String)> {
    let colour = match rarity {
        "common" => "gray",
        "uncommon" => "green",
        "rare" => "blue",
        "epic" => "purple",
        other => panic!("no progression set of rarity {other}"),
    };
    // Gray, green and blue exist every 5 levels; purple comes in tens and stops at 90, so it uses the best set at or below.
    let want = if rarity == "epic" {
        (level / 10 * 10).clamp(10, 90)
    } else {
        gear_level(level)
    };
    SLOTS
        .iter()
        .map(|&(slot, kind)| {
            let green: Vec<&Item> = ITEMS
                .iter()
                .filter(|i| {
                    i.kind == kind
                        && i.rarity == rarity
                        && i.required_level == want
                        && i.source.is_none()
                        && !i.starter
                        && i.class.is_none_or(|c| c == class)
                })
                .collect();
            // The progression set is named `..._l<level>_green`. Older stray pieces of the same rarity (gloves_upgrade)
            // are not in it; where a slot has no progression piece (the level-5 pants) its single green piece is used.
            let named: Vec<&Item> = green
                .iter()
                .copied()
                .filter(|i| i.id.ends_with(&format!("_l{want}_{colour}")))
                .collect();
            let chosen = if named.is_empty() { &green } else { &named };
            assert!(
                chosen.len() == 1,
                "{} green {kind} for {class:?} at level {want}",
                chosen.len()
            );
            let piece = chosen[0];
            (slot, piece.id.clone())
        })
        .collect()
}

/// The kind of monster used at `level`: the non-elite, non-boss kind of an open outdoor zone whose default level is
/// closest (ties go to the lower level, then the name), or for `Foe::Elite` the closest elite within two levels.
pub fn pick_enemy(w: &World, level: u32, foe: Foe) -> Option<usize> {
    let mut best: Option<(u32, u32, &str, usize)> = None;
    for s in &w.slimes {
        let map = &w.maps[s.zone];
        if map.copies > 0 || map.template.is_some() || s.kind == "big" || is_boss(&s.kind) {
            continue;
        }
        if is_elite(&s.kind) != (foe == Foe::Elite) {
            continue;
        }
        let default = Slime::default_level(&s.kind);
        let gap = default.abs_diff(level);
        if foe == Foe::Elite && gap > 2 {
            continue;
        }
        let key = (gap, default, s.kind.as_str(), s.id);
        if best.is_none_or(|b| key < b) {
            best = Some(key);
        }
    }
    best.map(|b| b.3)
}

fn spend_points(c: &mut Character, spread: Spread) {
    let points = c.level.saturating_sub(1) * 3;
    let main = match c.look.class {
        Class::Warrior => 0,
        Class::Mage | Class::Priest => 2,
        Class::Assassin | Class::Hunter => 1,
    };
    match spread {
        Spread::Even => {}
        Spread::Stamina => c.attributes.stamina = (points as f64 * 0.6).round() as u32,
        Spread::Damage => {
            let big = (points as f64 * 0.8).round() as u32;
            match main {
                0 => c.attributes.strength = big,
                1 => c.attributes.agility = big,
                _ => c.attributes.intellect = big,
            }
            c.attributes.stamina = points - big;
        }
    }
    if c.stat_points() > 0 {
        c.allocate_recommended().expect("the remaining points fit");
    }
}

/// A level-`level` character of `class` in its normal gear with its points spent, at full health and resource.
pub fn build_character(c: &mut Character, case: &Case) {
    c.level = case.level;
    c.xp = 0;
    c.attributes = Attributes::default();
    let mut equip = BTreeMap::new();
    for (slot, id) in normal_gear_of(case.class, case.level, case.rarity) {
        c.add_item(&id, 1);
        equip.insert(slot.to_string(), id);
    }
    c.equip_slots(&equip).expect("normal gear equips");
    spend_points(c, case.spread);
    if case.consumables {
        for family in ["health_potion", "mana_potion", "traveler_stew"] {
            if let Some(i) = crate::items::best_tier(family, case.level) {
                c.add_item(&i.id, 30);
            }
        }
    }
    c.hp = c.max_hp();
    c.reset_resource();
}

/// Where the character starts: `START_DISTANCE` tiles from the monster along a clear, walkable line.
fn start_point(w: &World, zone: usize, from: Point) -> Point {
    let map = &w.maps[zone];
    for distance in [START_DISTANCE, 6., 4.] {
        for k in 0..16 {
            let a = k as f64 / 16. * std::f64::consts::TAU;
            let mut p = Point {
                x: from.x + a.cos() * distance,
                y: from.y + a.sin() * distance,
            };
            let wanted = p;
            map.collide(&mut p, PLAYER_RADIUS);
            if p.distance(wanted) < 0.01 && map.line_clear(from, p, 0.3) {
                return p;
            }
        }
    }
    panic!("no clear start near {from:?} in zone {zone}");
}

/// The rotation of the rules: every damaging skill whenever it is off cooldown, highest unlock level first. Buffs that
/// raise damage are used when ready, shields and dodge below 60% health, heals below 50%.
fn cast_skills(w: &mut World, session: u64, id: usize, outcome: &mut Outcome) {
    let (class, level, hp, max_hp, point) = {
        let c = &w.players[&session].character;
        (c.look.class, c.level, c.hp, c.max_hp(), c.point())
    };
    let target = w.slimes[id].point();
    let distance = point.distance(target);
    let aim = point.direction(target);
    let mut ready: Vec<&crate::skills::Skill> = SKILLS
        .iter()
        .filter(|s| s.class == class && s.level <= level)
        .collect();
    ready.sort_by_key(|s| std::cmp::Reverse(s.level));
    for s in ready {
        let in_reach = match &s.effect {
            Effect::Cone { reach, .. } => distance <= reach + 0.3,
            Effect::Nova { radius, .. } => distance <= *radius,
            Effect::Strike { range, .. } | Effect::Chain { range, .. } => distance <= *range,
            Effect::Meteor { range, .. } => distance <= *range,
            Effect::Volley { .. } => distance <= 14.,
            Effect::Dash { mult, .. } => *mult > 0. && distance <= 6.,
            Effect::Buff { kind, .. } => match kind {
                Buff_::Damage | Buff_::Haste | Buff_::Crit => distance <= 12.,
                Buff_::Shield | Buff_::Dodge => hp < max_hp * 0.6 && distance <= 12.,
                Buff_::Regen => false,
            },
            Effect::Heal { .. } | Effect::Mend { .. } => hp < max_hp * 0.5,
        };
        if !in_reach || w.players[&session].skill_cd.contains_key(&s.id) {
            continue;
        }
        w.use_skill(session, &s.id, aim);
        if w.players[&session].skill_cd.contains_key(&s.id) {
            outcome.casts += 1;
            outcome.resource_used += s.cost;
        }
    }
}

fn use_consumables(w: &mut World, session: u64, outcome: &mut Outcome) {
    let (class, level, hp, max_hp, resource, max_resource, ready, eating) = {
        let p = &w.players[&session];
        let c = &p.character;
        (
            c.look.class,
            c.level,
            c.hp,
            c.max_hp(),
            c.resource(),
            c.max_resource(),
            p.potion_cd <= 0.,
            p.buffs.iter().any(|b| b.kind == Buff_::Regen),
        )
    };
    let owned = |w: &World, family: &str| {
        crate::items::best_tier(family, level)
            .filter(|i| w.players[&session].character.quantity(&i.id) > 0)
            .map(|i| i.id.clone())
    };
    if ready
        && hp < max_hp * 0.5
        && let Some(id) = owned(w, "health_potion")
    {
        w.use_item(session, &id);
        outcome.potions_used += 1;
        return;
    }
    if ready
        && class.resource_type() == "mana"
        && resource < max_resource * 0.25
        && let Some(id) = owned(w, "mana_potion")
    {
        w.use_item(session, &id);
        outcome.potions_used += 1;
        return;
    }
    if !eating
        && hp < max_hp * 0.6
        && let Some(id) = owned(w, "traveler_stew")
    {
        w.use_item(session, &id);
        outcome.food_used += 1;
    }
}

thread_local! {
    /// Seconds spent in the rotation, in `World::step` and in draining messages, and the number of steps (a timing probe).
    pub static PHASES: std::cell::RefCell<[f64; 4]> = const { std::cell::RefCell::new([0.; 4]) };
}

/// One fight with one seed.
pub fn run_once(case: &Case, seed: u64) -> (Outcome, Summary) {
    let mut w = world();
    w.rng = seed;
    let id = case
        .target
        .or_else(|| pick_enemy(&w, case.level, case.foe))
        .unwrap_or_else(|| panic!("no {:?} foe for level {}", case.foe, case.level));
    // Only the target's own zone is cleared. Monsters elsewhere stay alive and dormant, which `step` skips; dead ones
    // are updated every tick (about 6 ms per step across all zones, nearly all of a fight's cost).
    let target_zone = w.slimes[id].zone;
    for s in w
        .slimes
        .iter_mut()
        .filter(|s| s.id != id && s.zone == target_zone)
    {
        s.dead = true;
        s.respawn = 1e9;
    }
    let spawn = w.spawns[id].clone();
    w.slimes[id] = Slime::with_level(id, &spawn, case.level);
    if case.harmless {
        w.slimes[id].damage = 0.;
    }
    let zone = w.slimes[id].zone;
    let home = w.slimes[id].point();
    let mut rx = join(&mut w, 1, case.class);
    let start = start_point(&w, zone, home);
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = zone;
        c.x = start.x;
        c.y = start.y;
        build_character(c, case);
    }
    let mut out = Outcome {
        seed,
        seconds: 0.,
        killed: false,
        died: false,
        damage_taken: 0.,
        hits_taken: 0,
        lowest_hp_fraction: 1.,
        resource_used: 0.,
        casts: 0,
        potions_used: 0,
        food_used: 0,
        enemy_left: 1.,
    };
    let summary = Summary {
        case: *case,
        enemy: w.slimes[id].kind.clone(),
        enemy_level: w.slimes[id].level,
        enemy_hp: w.slimes[id].max_hp,
        enemy_damage: w.slimes[id].damage,
        character_hp: w.players[&1].character.max_hp(),
        runs: vec![],
    };
    let max_hp = summary.character_hp;
    // The first command: attack the monster. The server walks the character in and swings on its own.
    w.message(1, ClientMessage::Target { id });
    let start_time = w.time;
    let cap = cap_for(case.rotation);
    while w.time - start_time < cap {
        if w.players[&1].character.hp <= 0. {
            out.died = true;
            break;
        }
        if w.slimes[id].dead {
            out.killed = true;
            break;
        }
        let phase = std::time::Instant::now();
        if case.rotation == Rotation::Skills {
            cast_skills(&mut w, 1, id, &mut out);
        }
        if case.consumables {
            use_consumables(&mut w, 1, &mut out);
        }
        let rotation_time = phase.elapsed();
        let before = w.players[&1].character.hp;
        let phase = std::time::Instant::now();
        w.step();
        let step_time = phase.elapsed();
        let phase = std::time::Instant::now();
        drain(&mut rx);
        PHASES.with(|p| {
            let mut p = p.borrow_mut();
            p[0] += rotation_time.as_secs_f64();
            p[1] += step_time.as_secs_f64();
            p[2] += phase.elapsed().as_secs_f64();
            p[3] += 1.;
        });
        let after = w.players[&1].character.hp;
        if after < before {
            out.damage_taken += before - after;
            out.hits_taken += 1;
        }
        out.lowest_hp_fraction = out.lowest_hp_fraction.min((after / max_hp).max(0.));
        let elapsed = w.time - start_time;
        if elapsed >= PROJECT_AFTER {
            let done = 1. - w.slimes[id].hp / w.slimes[id].max_hp;
            if done <= 0. || elapsed / done > cap * HOPELESS_FACTOR {
                break;
            }
        }
    }
    out.seconds = w.time - start_time;
    out.enemy_left = (w.slimes[id].hp / w.slimes[id].max_hp).clamp(0., 1.);
    if w.players[&1].character.hp <= 0. {
        out.died = true;
        out.lowest_hp_fraction = 0.;
    }
    (out, summary)
}

/// A party of `members` (one real character each, all in `case.rarity` gear at `case.level`) against the monster of
/// `case.target`: true if the monster dies within the rotation cap. The control for `ELITE-SOLO-TEST`.
pub fn run_party_once(case: &Case, members: &[Class], seed: u64) -> bool {
    let mut w = world();
    w.rng = seed;
    let id = case.target.expect("a party fights a chosen monster");
    // Only the target's own zone is cleared. Monsters elsewhere stay alive and dormant, which `step` skips; dead ones
    // are updated every tick (about 6 ms per step across all zones, nearly all of a fight's cost).
    let target_zone = w.slimes[id].zone;
    for s in w
        .slimes
        .iter_mut()
        .filter(|s| s.id != id && s.zone == target_zone)
    {
        s.dead = true;
        s.respawn = 1e9;
    }
    let spawn = w.spawns[id].clone();
    w.slimes[id] = Slime::with_level(id, &spawn, case.level);
    let zone = w.slimes[id].zone;
    let home = w.slimes[id].point();
    let mut rxs = vec![];
    for (n, &class) in members.iter().enumerate() {
        let session = n as u64 + 1;
        rxs.push(join(&mut w, session, class));
        let start = start_point(&w, zone, home);
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.zone = zone;
        c.x = start.x;
        c.y = start.y;
        build_character(c, &Case { class, ..*case });
    }
    let mut out = Outcome {
        seed,
        seconds: 0.,
        killed: false,
        died: false,
        damage_taken: 0.,
        hits_taken: 0,
        lowest_hp_fraction: 1.,
        resource_used: 0.,
        casts: 0,
        potions_used: 0,
        food_used: 0,
        enemy_left: 1.,
    };
    for n in 0..members.len() {
        w.message(n as u64 + 1, ClientMessage::Target { id });
    }
    let start_time = w.time;
    while w.time - start_time < cap_for(case.rotation) {
        if w.slimes[id].dead {
            return true;
        }
        for n in 0..members.len() {
            let session = n as u64 + 1;
            if w.players[&session].character.hp <= 0. {
                continue;
            }
            cast_skills(&mut w, session, id, &mut out);
            if case.consumables {
                use_consumables(&mut w, session, &mut out);
            }
        }
        w.step();
        for rx in rxs.iter_mut() {
            drain(rx);
        }
        if members
            .iter()
            .enumerate()
            .all(|(n, _)| w.players[&(n as u64 + 1)].character.hp <= 0.)
        {
            return false;
        }
    }
    w.slimes[id].dead
}

/// Seeds 1..=`runs` of one case, summarised.
pub fn run_case(case: &Case, runs: u64) -> Summary {
    let mut summary = None;
    let mut outcomes = vec![];
    for seed in 1..=runs {
        let (o, s) = run_once(case, seed);
        outcomes.push(o);
        summary.get_or_insert(s);
    }
    let mut summary = summary.expect("at least one run");
    summary.runs = outcomes;
    summary
}

// ---- tests ---------------------------------------------------------------------------------------------------------

fn parse_list(var: &str) -> Option<Vec<String>> {
    std::env::var(var)
        .ok()
        .filter(|v| !v.trim().is_empty())
        .map(|v| v.split(',').map(|s| s.trim().to_lowercase()).collect())
}
fn class_named(name: &str) -> Class {
    match name {
        "warrior" => Class::Warrior,
        "mage" => Class::Mage,
        "assassin" => Class::Assassin,
        "priest" => Class::Priest,
        "hunter" => Class::Hunter,
        other => panic!("unknown class {other}"),
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct TargetBand {
    min_level: u32,
    max_level: u32,
    min_seconds: f64,
    max_seconds: f64,
}

fn target_band(level: u32) -> TargetBand {
    serde_json::from_str::<Vec<TargetBand>>(include_str!("../../../world/ttk-targets.txt"))
        .expect("kill-time target data")
        .into_iter()
        .find(|band| band.min_level <= level && level <= band.max_level)
        .unwrap_or_else(|| panic!("no kill-time target for level {level}"))
}

fn assert_balanced_grid(levels: &[u32], runs: u64) {
    for &level in levels {
        let target = target_band(level);
        let mut times = vec![];
        for class in CLASSES {
            let result = run_case(&Case::new(class, level), runs);
            let seconds = result.seconds().0;
            assert_eq!(result.failures(), 0, "{class:?} {level} failed to kill");
            assert!(
                (target.min_seconds..=target.max_seconds).contains(&seconds),
                "{class:?} {level}: {seconds:.1}s outside {:.0}–{:.0}s",
                target.min_seconds,
                target.max_seconds
            );
            let lowest = result.spread_of(|o| o.lowest_hp_fraction).0;
            assert!(
                lowest >= 0.2,
                "{class:?} {level}: fell to {:.0}% HP",
                lowest * 100.
            );
            times.push(seconds);
        }
        times.sort_by(f64::total_cmp);
        assert!(
            times[4] / times[0] <= 1.3,
            "level {level}: class kill-time spread {:.2}x ({times:?})",
            times[4] / times[0]
        );
    }
}

#[test]
fn sampled_kill_times_stay_in_band_across_classes_and_progression() {
    assert_balanced_grid(&[5, 20, 50, 99], 1);
}

#[test]
#[ignore = "full 100-case, nine-seed balance gate; run after combat changes"]
fn full_kill_time_balance_gate() {
    assert_balanced_grid(&levels(), 9);
}

#[test]
fn green_gear_warrior_survives_four_plain_hits_from_same_level_elites() {
    let w = world();
    let mut seen = std::collections::BTreeSet::new();
    for spawn in &w.spawns {
        if !is_elite(&spawn.kind) || !seen.insert(spawn.kind.clone()) {
            continue;
        }
        let level = Slime::default_level(&spawn.kind);
        let enemy = Slime::with_level(0, spawn, level);
        let mut hero = Character::mercenary(Class::Warrior, level, "Guard");
        build_character(&mut hero, &Case::new(Class::Warrior, level));
        let hit = ((enemy.damage - hero.stats().1).max(1.) * DAMAGE_TAKEN_SCALE)
            .round()
            .max(1.);
        assert!(
            hero.max_hp() / hit >= 4.,
            "{} (level {level}): {:.0} HP, {:.0} per plain hit",
            spawn.kind,
            hero.max_hp(),
            hit
        );
    }
}

/// Prints the report for `TTK-RUN`; ignored in normal runs because the full grid takes a while.
///
/// `TTK_LEVELS=5,10 TTK_CLASSES=warrior,mage TTK_SPREADS=even,stamina,damage TTK_ROTATIONS=skills,basic TTK_FOES=ordinary,elite
/// TTK_CONSUMABLES=0,1 TTK_RUNS=9 TTK_OUT=path.json`; every variable is optional and defaults to the full grid of the rules.
#[test]
#[ignore = "full grid; run with scripts/ttk.sh"]
fn ttk_report() {
    let levels: Vec<u32> = parse_list("TTK_LEVELS")
        .map(|v| v.iter().map(|s| s.parse().unwrap()).collect())
        .unwrap_or_else(levels);
    let classes: Vec<Class> = parse_list("TTK_CLASSES")
        .map(|v| v.iter().map(|s| class_named(s)).collect())
        .unwrap_or_else(|| CLASSES.to_vec());
    let spreads = parse_list("TTK_SPREADS").unwrap_or_else(|| vec!["even".into()]);
    let rotations = parse_list("TTK_ROTATIONS").unwrap_or_else(|| vec!["skills".into()]);
    let foes = parse_list("TTK_FOES").unwrap_or_else(|| vec!["ordinary".into()]);
    let consumables = parse_list("TTK_CONSUMABLES").unwrap_or_else(|| vec!["0".into()]);
    let runs: u64 = std::env::var("TTK_RUNS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(9);
    let mut rows = vec![];
    for foe in &foes {
        for rotation in &rotations {
            for spread in &spreads {
                for use_consumables in &consumables {
                    for &level in &levels {
                        for &class in &classes {
                            let case = Case {
                                class,
                                level,
                                spread: match spread.as_str() {
                                    "even" => Spread::Even,
                                    "stamina" => Spread::Stamina,
                                    "damage" => Spread::Damage,
                                    other => panic!("unknown spread {other}"),
                                },
                                rotation: match rotation.as_str() {
                                    "skills" => Rotation::Skills,
                                    "basic" => Rotation::BasicOnly,
                                    other => panic!("unknown rotation {other}"),
                                },
                                foe: match foe.as_str() {
                                    "ordinary" => Foe::Ordinary,
                                    "elite" => Foe::Elite,
                                    other => panic!("unknown foe {other}"),
                                },
                                consumables: use_consumables == "1",
                                harmless: std::env::var("TTK_HARMLESS").is_ok_and(|v| v == "1"),
                                rarity: BASELINE_RARITY,
                                target: None,
                            };
                            if case.foe == Foe::Elite
                                && pick_enemy(&world(), level, Foe::Elite).is_none()
                            {
                                continue;
                            }
                            rows.push(run_case(&case, runs).to_json());
                        }
                    }
                }
            }
        }
    }
    let text = serde_json::to_string_pretty(&rows).unwrap();
    if let Ok(path) = std::env::var("TTK_OUT") {
        std::fs::write(path, &text).unwrap();
    }
    println!("{text}");
}

#[test]
fn normal_gear_is_eight_green_pieces_that_equip_for_every_class_and_level() {
    for class in CLASSES {
        for level in levels() {
            let gear = normal_gear(class, level);
            assert_eq!(gear.len(), 8, "{class:?} {level}");
            let mut c = Character::mercenary(class, level, "Gear");
            build_character(&mut c, &Case::new(class, level));
            for (_, id) in &gear {
                let i = item(id).unwrap();
                assert_eq!(i.rarity, BASELINE_RARITY, "{id}");
                assert_eq!(i.required_level, gear_level(level), "{id}");
                assert!(i.source.is_none() && !i.starter, "{id}");
                assert_eq!(c.equipped_count(i), 1, "{id} is worn at {level}");
            }
            assert!(
                c.gear_instances
                    .iter()
                    .all(|g| g.rank == 0 && g.rarity == BASELINE_RARITY)
            );
        }
    }
    assert_eq!(gear_level(99), 95);
    assert_eq!(gear_level(5), 5);
}

#[test]
fn the_three_spreads_spend_every_point_and_differ_as_the_rules_say() {
    for class in CLASSES {
        for level in levels() {
            let mut results = vec![];
            for spread in [Spread::Even, Spread::Stamina, Spread::Damage] {
                let mut c = Character::mercenary(class, level, "Spread");
                let case = Case {
                    spread,
                    ..Case::new(class, level)
                };
                build_character(&mut c, &case);
                let a = &c.attributes;
                let spent =
                    a.strength + a.agility + a.intellect + a.stamina + a.dexterity + a.accuracy;
                assert_eq!(
                    spent,
                    3 * (level - 1),
                    "{class:?} {level} {spread:?} spends every point"
                );
                assert!(
                    a.accuracy <= 20 && a.dexterity <= 70,
                    "{class:?} {level} {spread:?} caps"
                );
                results.push((a.stamina, a.strength.max(a.agility).max(a.intellect), spent));
            }
            let (even, stamina, damage) = (results[0], results[1], results[2]);
            assert!(
                stamina.0 > even.0,
                "{class:?} {level}: stamina variant has more stamina"
            );
            assert!(
                damage.1 > even.1,
                "{class:?} {level}: damage variant has more main stat"
            );
            assert_eq!(damage.1, (3. * (level - 1) as f64 * 0.8).round() as u32);
        }
    }
}

#[test]
fn every_level_has_an_ordinary_target_pinned_to_the_character_level() {
    let w = world();
    for level in levels() {
        let id = pick_enemy(&w, level, Foe::Ordinary).unwrap();
        let s = &w.slimes[id];
        assert!(!is_elite(&s.kind) && !is_boss(&s.kind) && s.kind != "big");
        let map = &w.maps[s.zone];
        assert!(
            map.copies == 0 && map.template.is_none(),
            "{} is outdoor",
            s.kind
        );
        let gap = Slime::default_level(&s.kind).abs_diff(level);
        assert!(gap <= 5, "level {level}: {} is {gap} levels away", s.kind);
        let spawn = w.spawns[id].clone();
        assert_eq!(Slime::with_level(id, &spawn, level).level, level);
    }
}

#[test]
fn a_run_is_repeatable_isolated_and_records_what_the_rules_name() {
    let case = Case::new(Class::Warrior, 5);
    let (a, summary) = run_once(&case, 3);
    let (b, _) = run_once(&case, 3);
    assert_eq!(a, b, "the same seed gives the same fight");
    assert!(a.killed && !a.died, "{a:?}");
    assert!(a.seconds > 1. && a.seconds < MAX_SECONDS, "{a:?}");
    assert!(a.damage_taken >= 0. && a.lowest_hp_fraction > 0. && a.lowest_hp_fraction <= 1.);
    assert!(
        a.casts > 0 && a.resource_used > 0.,
        "the rotation cast skills: {a:?}"
    );
    assert_eq!(summary.enemy_level, 5);
    let basic = run_once(
        &Case {
            rotation: Rotation::BasicOnly,
            ..case
        },
        3,
    )
    .0;
    assert_eq!(
        (basic.casts, basic.resource_used),
        (0, 0.),
        "basic-attack-only run casts nothing"
    );
    let fed = run_once(
        &Case {
            consumables: true,
            ..case
        },
        3,
    )
    .0;
    assert!(fed.potions_used + fed.food_used > 0 || fed.lowest_hp_fraction >= 0.5);
}

#[test]
fn a_summary_reports_median_and_spread_over_seeds() {
    let summary = run_case(&Case::new(Class::Mage, 5), 3);
    assert_eq!(summary.runs.len(), 3);
    let (median, min, max) = summary.seconds();
    assert!(min <= median && median <= max);
    let json = summary.to_json();
    assert_eq!(json["runs"], 3);
    assert!(json["deaths"].as_u64().unwrap() <= json["failures"].as_u64().unwrap());
    assert_eq!(json["class"], "mage");
    assert!(json["seconds"]["median"].as_f64().unwrap() > 0.);
}

#[test]
fn medians_of_even_and_odd_lists() {
    assert_eq!(median(&[1., 2., 9.]), 2.);
    assert_eq!(median(&[1., 2., 4., 9.]), 3.);
}
