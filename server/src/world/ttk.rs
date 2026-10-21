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
    /// The monster's level when it differs from the character's (a player five levels above the elite).
    pub enemy_level: Option<u32>,
    /// Seconds the fight may last before it counts as not won (default: the rotation's cap).
    pub cap: Option<f64>,
    /// Fight to the cap or the character's death. Off, a fight whose progress projects past `HOPELESS_FACTOR` caps is
    /// stopped as soon as it is clear it cannot be won, which reports a lone player as alive who the boss's enrage
    /// would kill a little later (`dungeon_solo_tests`).
    pub run_to_end: bool,
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
            enemy_level: None,
            cap: None,
            run_to_end: false,
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
    /// Damage the character dealt (`damage / seconds` is its DPS).
    pub damage: f64,
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
fn cast_skills(w: &mut World, session: u64, id: usize, still: bool, outcome: &mut Outcome) {
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
            Effect::Dash { mult, .. } => !still && *mult > 0. && distance <= 6.,
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

/// A monster that holds still (a boss in its channel or its stun, a pearl, a seed, a cocoon) does not come to a party
/// that stands where the fight began, so the bots walk in as players would: to a melee reach of it, stopping where they
/// are if already close.
fn walk_up_to_a_held_boss(w: &mut World, session: u64, id: usize) {
    walk_up_to_held(w, session, id, false);
}

/// `anything`: also a helper of a mechanic (pearl, seed, cocoon), not only a boss with a table entry.
fn walk_up_to_held(w: &mut World, session: u64, id: usize, anything: bool) {
    const REACH: f64 = 2.5;
    let boss = &w.slimes[id];
    if (!anything && !w.boss.table.contains_key(&boss.kind)) || boss.set_root_left <= 0. {
        return;
    }
    let target = boss.point();
    let zone = boss.zone;
    let from = w.players[&session].character.point();
    let distance = from.distance(target);
    if distance > REACH {
        let step = from.direction(target);
        let walk = (distance - REACH).min(5.2 * TICK);
        bot_walk(w, session, zone, from, step, walk);
    }
}

/// One tick of walking at the slowest class's speed toward `goal`, stopped by walls like anyone's.
fn walk_to(w: &mut World, session: u64, goal: Point) {
    let c = &w.players[&session].character;
    let (zone, from) = (c.zone, c.point());
    let distance = from.distance(goal);
    if distance > 0.05 {
        let step = from.direction(goal);
        bot_walk(w, session, zone, from, step, distance.min(5.2 * TICK));
    }
}

fn bot_walk(w: &mut World, session: u64, zone: usize, from: Point, step: Point, walk: f64) {
    // Straight on, else sliding along the wall on one axis: a hero rounding a pillar does not stop dead at it.
    let moved = |dx: f64, dy: f64| {
        let mut to = Point {
            x: from.x + dx,
            y: from.y + dy,
        };
        w.maps[zone].collide(&mut to, PLAYER_RADIUS);
        to
    };
    let (dx, dy) = (step.x * walk, step.y * walk);
    let mut best = moved(dx, dy);
    for (ax, ay) in [(dx, 0.), (0., dy)] {
        let alt = moved(ax, ay);
        if alt.distance(from) > best.distance(from) {
            best = alt;
        }
    }
    let c = &mut w.players.get_mut(&session).unwrap().character;
    (c.x, c.y) = (best.x, best.y);
}

/// `DUNGEON_BOSS_BOTS=ignore` plays the party without the mechanics' answers (`boss_play.rs`), to measure that ignoring
/// them loses; the default plays them.
fn boss_bots_answer() -> bool {
    !std::env::var("DUNGEON_BOSS_BOTS").is_ok_and(|v| v == "ignore")
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

/// Keeps only the monsters of `zone` (ids renumbered, `spawns` in step) and returns the new id of each old one
/// (`usize::MAX` for a dropped one). A fight in one zone does not need the other ~1,900 monsters of the world, and
/// every step scans all of them several times; the map, the zone's monsters and their order stay the same. Seeded
/// outcomes differ from a full world's (sleeping monsters draw random numbers), so compare against runs made with
/// this trim, or set `TTK_FULL_WORLD=1` for the untrimmed world.
fn trim_to_zone(w: &mut World, zone: usize) -> Vec<usize> {
    let mut map = vec![usize::MAX; w.slimes.len()];
    if std::env::var("TTK_FULL_WORLD").is_ok() {
        return (0..w.slimes.len()).collect();
    }
    let (mut slimes, mut spawns) = (vec![], vec![]);
    for (old, s) in std::mem::take(&mut w.slimes).into_iter().enumerate() {
        if s.zone == zone {
            let mut s = s;
            map[old] = slimes.len();
            s.id = slimes.len();
            spawns.push(w.spawns[old].clone());
            slimes.push(s);
        }
    }
    w.slimes = slimes;
    w.spawns = spawns;
    map
}

/// One fight with one seed.
pub fn run_once(case: &Case, seed: u64) -> (Outcome, Summary) {
    let mut w = world();
    w.rng = seed;
    let id = case
        .target
        .or_else(|| pick_enemy(&w, case.level, case.foe))
        .unwrap_or_else(|| panic!("no {:?} foe for level {}", case.foe, case.level));
    let target_zone = w.slimes[id].zone;
    let id = trim_to_zone(&mut w, target_zone)[id];
    // Only the target's own zone is cleared. Monsters elsewhere stay alive and dormant, which `step` skips; dead ones
    // are updated every tick (about 6 ms per step across all zones, nearly all of a fight's cost).
    for s in w
        .slimes
        .iter_mut()
        .filter(|s| s.id != id && s.zone == target_zone)
    {
        s.dead = true;
        s.respawn = 1e9;
    }
    let spawn = w.spawns[id].clone();
    w.slimes[id] = Slime::with_level(id, &spawn, case.enemy_level.unwrap_or(case.level));
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
    // A dungeon copy nobody has entered is frozen: the monsters would never move or strike.
    w.enter_instance(zone);
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
        damage: 0.,
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
    let cap = case.cap.unwrap_or_else(|| cap_for(case.rotation));
    // `TTK_BRAIN=mercenary` plays the kill-time grid (an ordinary monster picked by level) with the mercenaries' own code,
    // like the party fights, instead of the harness rotation. Off by default: the bands were tuned with the harness
    // rotation, and the mercenary one is faster at some levels (warrior 20: 10.3 s against the 15 s minimum).
    let brain = case.target.is_none() && std::env::var("TTK_BRAIN").is_ok_and(|v| v == "mercenary");
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
            if brain {
                w.auto_play(1, &[], Some(id));
            } else {
                walk_up_to_a_held_boss(&mut w, 1, id);
                cast_skills(&mut w, 1, id, false, &mut out);
            }
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
        // A boss with a mechanic can end the fight at any moment (its wail), so the projection says nothing yet.
        if elapsed >= PROJECT_AFTER
            && !case.run_to_end
            && !w.boss.table.contains_key(&w.slimes[id].kind)
        {
            let done = 1. - w.slimes[id].hp / w.slimes[id].max_hp;
            if done <= 0. || elapsed / done > cap * HOPELESS_FACTOR {
                break;
            }
        }
    }
    out.seconds = w.time - start_time;
    out.damage = w.damage_log.get(&1).copied().unwrap_or(0.);
    if brain {
        // `auto_play` casts on its own, so the casts and the resource they cost are read from the server's tally.
        for ((session, skill), casts) in &w.casts_by_skill {
            if *session == 1 {
                out.casts += casts;
                out.resource_used += *casts as f64
                    * SKILLS
                        .iter()
                        .find(|s| &s.id == skill)
                        .map_or(0., |s| s.cost);
            }
        }
    }
    out.enemy_left = (w.slimes[id].hp / w.slimes[id].max_hp).clamp(0., 1.);
    if w.players[&1].character.hp <= 0. {
        out.died = true;
        out.lowest_hp_fraction = 0.;
    }
    (out, summary)
}

/// One lone character against several monsters at once (a dungeon pack). The pack is `killed` when every member is
/// dead; `enemy_left` is the share of the pack's total health still standing. The character always fights the nearest
/// living member and picks the next target as soon as one dies.
pub fn run_pack_once(case: &Case, ids: &[usize], seed: u64) -> Outcome {
    let mut w = world();
    w.rng = seed;
    let target_zone = w.slimes[ids[0]].zone;
    let trimmed = trim_to_zone(&mut w, target_zone);
    let ids = &ids.iter().map(|&id| trimmed[id]).collect::<Vec<_>>();
    for s in w
        .slimes
        .iter_mut()
        .filter(|s| s.zone == target_zone && !ids.contains(&s.id))
    {
        s.dead = true;
        s.respawn = 1e9;
    }
    for &id in ids {
        let spawn = w.spawns[id].clone();
        w.slimes[id] = Slime::with_level(id, &spawn, case.enemy_level.unwrap_or(case.level));
    }
    let centre = Point {
        x: ids.iter().map(|&i| w.slimes[i].x).sum::<f64>() / ids.len() as f64,
        y: ids.iter().map(|&i| w.slimes[i].y).sum::<f64>() / ids.len() as f64,
    };
    let home = ids
        .iter()
        .map(|&i| w.slimes[i].point())
        .min_by(|a, b| a.distance(centre).total_cmp(&b.distance(centre)))
        .unwrap();
    let total_hp: f64 = ids.iter().map(|&i| w.slimes[i].max_hp).sum();
    let mut rx = join(&mut w, 1, case.class);
    let start = start_point(&w, target_zone, home);
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = target_zone;
        c.x = start.x;
        c.y = start.y;
        build_character(c, case);
    }
    w.enter_instance(target_zone);
    let max_hp = w.players[&1].character.max_hp();
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
        damage: 0.,
    };
    let start_time = w.time;
    let cap = case.cap.unwrap_or_else(|| cap_for(case.rotation));
    let mut current = usize::MAX;
    let left = |w: &World| ids.iter().map(|&i| w.slimes[i].hp.max(0.)).sum::<f64>() / total_hp;
    while w.time - start_time < cap {
        if w.players[&1].character.hp <= 0. {
            out.died = true;
            break;
        }
        let me = w.players[&1].character.point();
        let Some(near) = ids
            .iter()
            .copied()
            .filter(|&i| !w.slimes[i].dead)
            .min_by(|&a, &b| {
                w.slimes[a]
                    .point()
                    .distance(me)
                    .total_cmp(&w.slimes[b].point().distance(me))
            })
        else {
            out.killed = true;
            break;
        };
        if near != current || w.slimes[current].dead {
            current = near;
            w.message(1, ClientMessage::Target { id: near });
        }
        if case.rotation == Rotation::Skills {
            walk_up_to_a_held_boss(&mut w, 1, near);
            cast_skills(&mut w, 1, near, false, &mut out);
        }
        if case.consumables {
            use_consumables(&mut w, 1, &mut out);
        }
        let before = w.players[&1].character.hp;
        w.step();
        drain(&mut rx);
        let after = w.players[&1].character.hp;
        if after < before {
            out.damage_taken += before - after;
            out.hits_taken += 1;
        }
        out.lowest_hp_fraction = out.lowest_hp_fraction.min((after / max_hp).max(0.));
        let elapsed = w.time - start_time;
        if elapsed >= PROJECT_AFTER
            && !ids
                .iter()
                .any(|&i| w.boss.table.contains_key(&w.slimes[i].kind))
        {
            let done = 1. - left(&w);
            if done <= 0. || elapsed / done > cap * HOPELESS_FACTOR {
                break;
            }
        }
    }
    out.seconds = w.time - start_time;
    out.damage = w.damage_log.get(&1).copied().unwrap_or(0.);
    out.enemy_left = left(&w).clamp(0., 1.);
    if w.players[&1].character.hp <= 0. {
        out.died = true;
        out.lowest_hp_fraction = 0.;
    }
    out
}

/// A party of `members` (one real character each, all in `case.rarity` gear at `case.level`) against the monster of
/// `case.target`: true if the monster dies within the rotation cap. The control for `ELITE-SOLO-TEST`.
pub fn run_party_once(case: &Case, members: &[Class], seed: u64) -> bool {
    let id = case.target.expect("a party fights a chosen monster");
    run_party_pack_once(case, members, &[id], seed).killed
}

/// What a party fight came to.
#[derive(Clone, Debug)]
pub struct PartyOutcome {
    /// Every monster of the group died.
    pub killed: bool,
    /// Members who died on the way.
    pub deaths: usize,
    pub seconds: f64,
    /// The group's health still standing, as a fraction of its total.
    pub enemy_left: f64,
    /// Seconds each broken channel had left (`BossMech::spare`).
    pub break_spare: Vec<f64>,
    /// Times the hired party was set down in sight of the boss after ten idle seconds behind a wall (a hirer who steps
    /// round the corner; the harness walks in straight lines).
    pub unstuck: u32,
    /// Damage per second each fighter dealt over the fight, by class (a party with two of a class lists both).
    pub dps: Vec<(Class, f64)>,
}

/// A party of `members` against several monsters at once (a dungeon pack or a boss). Every living member fights the
/// nearest living monster; the group is `killed` when every monster is dead before the cap.
pub fn run_party_pack_once(
    case: &Case,
    members: &[Class],
    ids: &[usize],
    seed: u64,
) -> PartyOutcome {
    party_pack_fight(case, members, &[], HirerRole::Fights, ids, seed, false)
}

/// The hirer (`hirer`, driven like any member) with `mercs` rented at Skaldholm's Meeting Stone through the real offers
/// (`merc_price` gold each, the hirer's level, no gear but the starting potions), against a dungeon boss or pack. The mercenaries
/// play themselves (`merc_think`, `boss_play`); `deaths` counts every fall, theirs too.
pub fn run_hired_party_pack_once(
    case: &Case,
    hirer: Class,
    mercs: &[Class],
    ids: &[usize],
    seed: u64,
) -> PartyOutcome {
    party_pack_fight(case, &[hirer], mercs, HirerRole::Fights, ids, seed, false)
}

/// A full equipment-tier party driven by the actual hired-fighter brain.
/// Only the test fixture changes gear; live mercenaries keep their ordinary equipment.
pub fn run_geared_hired_party(case: &Case, ids: &[usize], seed: u64) -> PartyOutcome {
    party_pack_fight(
        case,
        &[Class::Warrior],
        &[Class::Mage, Class::Assassin, Class::Priest, Class::Hunter],
        HirerRole::Fights,
        ids,
        seed,
        true,
    )
}

/// What the hirer does in a hired-party fight (`BOSSMECH-MERC-ALONE`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HirerRole {
    /// Fights like any member (the `BOSSMECH-MERC` check).
    Fights,
    /// Stands in the room within sight of the boss and does nothing: no target, no skill, no step, no potion.
    Idle,
    /// Is down for the whole fight (a hirer who fell, or a player who left the keyboard and was killed).
    Down,
}

/// The same fight as `run_hired_party_pack_once`, but the hirer plays `role`. The party starts five tiles from the
/// boss in the two roles that leave the hirer out, so the boss has someone to pick on and the mercenaries can answer.
pub fn run_hired_party_with_role(
    case: &Case,
    hirer: Class,
    role: HirerRole,
    mercs: &[Class],
    ids: &[usize],
    seed: u64,
) -> PartyOutcome {
    party_pack_fight(case, &[hirer], mercs, role, ids, seed, false)
}

/// A clear, walkable spot 4 to 7 tiles from `boss` that no telegraph covers, in `zone`.
fn seat_near_boss(w: &World, zone: usize, boss: Point) -> Option<Point> {
    for distance in [5., 6., 7., 4.] {
        for k in 0..16 {
            let a = k as f64 / 16. * std::f64::consts::TAU;
            let mut p = Point {
                x: boss.x + a.cos() * distance,
                y: boss.y + a.sin() * distance,
            };
            let wanted = p;
            w.maps[zone].collide(&mut p, PLAYER_RADIUS);
            if p.distance(wanted) < 0.01
                && w.maps[zone].line_clear(boss, p, 0.3)
                && w.bot_threat(zone, 1, p, 0.).is_none()
            {
                return Some(p);
            }
        }
    }
    None
}

/// Rents `mercs` for the hirer (session 1) at the Meeting Stone, then sets the hirer at `start` in `zone` with the hired
/// fighters on free ground beside them.
pub(super) fn hire_mercenaries(w: &mut World, mercs: &[Class], zone: usize, start: Point) {
    let stone_zone = w
        .maps
        .iter()
        .position(|m| m.npcs.iter().any(|n| n.id == "city_meetingstone"))
        .expect("a Meeting Stone");
    let stone = w.maps[stone_zone]
        .npcs
        .iter()
        .find(|n| n.id == "city_meetingstone")
        .unwrap()
        .clone();
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.gold = super::mercs::merc_price(c.level) * mercs.len() as u32 + 1000;
        c.zone = stone_zone;
        c.x = stone.x;
        c.y = stone.y + 1.;
    }
    for class in mercs {
        w.time += 0.6;
        let name = format!("{class:?}").to_lowercase();
        w.interact(1, "city_meetingstone", Some(&format!("merc_{name}")));
    }
    assert_eq!(
        w.players.values().filter(|p| p.merc.is_some()).count(),
        mercs.len(),
        "every mercenary was hired"
    );
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = zone;
        c.x = start.x;
        c.y = start.y;
    }
    seat_hired(w, zone, start);
}

/// Puts every hired fighter on free ground round `at`, in `zone`, at full health.
fn seat_hired(w: &mut World, zone: usize, at: Point) {
    let hired: Vec<u64> = w
        .players
        .iter()
        .filter(|(_, p)| p.merc.is_some())
        .map(|(s, _)| *s)
        .collect();
    let mut taken: Vec<Point> = vec![at];
    for session in hired {
        let spot = (0..200)
            .map(|k| {
                let a = k as f64 * 2.4;
                let r = 1.4 + k as f64 * 0.05;
                Point {
                    x: at.x + a.cos() * r,
                    y: at.y + a.sin() * r,
                }
            })
            .find(|&p| {
                let mut q = p;
                w.maps[zone].collide(&mut q, PLAYER_RADIUS);
                q.distance(p) < 0.01 && taken.iter().all(|t| t.distance(p) >= 0.9)
            })
            .expect("room beside the hirer for a mercenary");
        taken.push(spot);
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.zone = zone;
        c.x = spot.x;
        c.y = spot.y;
        c.hp = c.max_hp();
    }
}

fn party_pack_fight(
    case: &Case,
    members: &[Class],
    mercs: &[Class],
    role: HirerRole,
    ids: &[usize],
    seed: u64,
    equip_hired: bool,
) -> PartyOutcome {
    let mut w = world();
    w.rng = seed;
    let zone = w.slimes[ids[0]].zone;
    // The new equipment-tier fixture simulates only its selected encounter.
    // Preserve the real map, combat and hired AI, but avoid stepping thousands
    // of unrelated actors for these deliberately long fights. FULL_WORLD is
    // available for an independent control using the untrimmed world.
    let local_ids;
    let ids = if equip_hired && std::env::var("BLACKHOUR_FULL_WORLD").is_err() {
        let spawns: Vec<_> = ids.iter().map(|&id| w.spawns[id].clone()).collect();
        w.slimes = spawns
            .iter()
            .enumerate()
            .map(|(id, spawn)| Slime::with_level(id, spawn, case.enemy_level.unwrap_or(case.level)))
            .collect();
        w.spawns = spawns;
        w.next_king_spawn = f64::INFINITY;
        local_ids = (0..w.slimes.len()).collect::<Vec<_>>();
        local_ids.as_slice()
    } else {
        let trimmed = trim_to_zone(&mut w, zone);
        local_ids = ids.iter().map(|&id| trimmed[id]).collect::<Vec<_>>();
        local_ids.as_slice()
    };
    for s in w
        .slimes
        .iter_mut()
        .filter(|s| s.zone == zone && !ids.contains(&s.id))
    {
        s.dead = true;
        s.respawn = 1e9;
    }
    for &id in ids {
        let spawn = w.spawns[id].clone();
        w.slimes[id] = Slime::with_level(id, &spawn, case.enemy_level.unwrap_or(case.level));
    }
    let centre = Point {
        x: ids.iter().map(|&i| w.slimes[i].x).sum::<f64>() / ids.len() as f64,
        y: ids.iter().map(|&i| w.slimes[i].y).sum::<f64>() / ids.len() as f64,
    };
    let home = ids
        .iter()
        .map(|&i| w.slimes[i].point())
        .min_by(|a, b| a.distance(centre).total_cmp(&b.distance(centre)))
        .unwrap();
    let total_hp: f64 = ids.iter().map(|&i| w.slimes[i].max_hp).sum();
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
        if n == 0 && !mercs.is_empty() {
            hire_mercenaries(&mut w, mercs, zone, start);
            if equip_hired {
                for p in w.players.values_mut().filter(|p| p.merc.is_some()) {
                    let class = p.character.look.class;
                    build_character(&mut p.character, &Case { class, ..*case });
                }
            }
            if role != HirerRole::Fights
                && let Some(p) = seat_near_boss(&w, zone, home)
            {
                let c = &mut w.players.get_mut(&1).unwrap().character;
                (c.x, c.y) = (p.x, p.y);
                seat_hired(&mut w, zone, p);
            }
        }
    }
    w.enter_instance(zone);
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
        damage: 0.,
    };
    let classes: Vec<(u64, Class)> = w
        .players
        .iter()
        .map(|(s, p)| (*s, p.character.look.class))
        .collect();
    // Every fighter plays by the mercenaries' code (`auto_play`: the same skills, potions, telegraph steps and boss brain);
    // `DUNGEON_PARTY_BRAIN=harness` brings back the harness's own rotation for a comparison.
    let auto_brain = !std::env::var("DUNGEON_PARTY_BRAIN").is_ok_and(|v| v == "harness");
    let left = |w: &World| ids.iter().map(|&i| w.slimes[i].hp.max(0.)).sum::<f64>() / total_hp;
    let mut aimed = vec![usize::MAX; members.len()];
    let start_time = w.time;
    let cap = case.cap.unwrap_or_else(|| cap_for(case.rotation));
    let mut killed = false;
    let mut falls = 0;
    let mut unstuck = 0;
    let mut last_left = 1.;
    let mut idle_since = w.time;
    let mut merc_down: Vec<(u64, bool)> = w
        .players
        .iter()
        .filter(|(_, p)| p.merc.is_some())
        .map(|(s, _)| (*s, false))
        .collect();
    let answers = boss_bots_answer();
    let trace = std::env::var("DUNGEON_BOSS_TRACE").is_ok();
    while w.time - start_time < cap {
        if ids.iter().all(|&i| w.slimes[i].dead) {
            killed = true;
            break;
        }
        if !mercs.is_empty() {
            let now_left = left(&w);
            if (last_left - now_left).abs() > 0.0005 {
                last_left = now_left;
                idle_since = w.time;
            }
            let hirer = w.players[&1].character.point();
            let target = ids.iter().copied().find(|&i| !w.slimes[i].dead);
            if role == HirerRole::Fights
                && w.time - idle_since >= 10.
                && w.players[&1].character.hp > 0.
                && let Some(t) = target
                && !w.maps[zone].line_clear(hirer, w.slimes[t].point(), 0.3)
            {
                let boss = w.slimes[t].point();
                if let Some(p) = seat_near_boss(&w, zone, boss) {
                    let c = &mut w.players.get_mut(&1).unwrap().character;
                    (c.x, c.y) = (p.x, p.y);
                    seat_hired(&mut w, zone, p);
                    unstuck += 1;
                    idle_since = w.time;
                }
            }
        }
        let mut anyone_alive = false;
        for (n, aimed_at) in aimed.iter_mut().enumerate() {
            let session = n as u64 + 1;
            if role == HirerRole::Down && session == 1 {
                // Down for the whole fight: a wake-up at the door (before the fight holds the body) is undone.
                let p = w.players.get_mut(&1).unwrap();
                p.character.hp = 0.;
                p.dead_time = 0.;
                p.fallen = true;
            }
            if w.players[&session].character.hp <= 0. {
                continue;
            }
            anyone_alive = true;
            if role == HirerRole::Idle && session == 1 {
                continue;
            }
            let me = w.players[&session].character.point();
            let Some(mut near) =
                ids.iter()
                    .copied()
                    .filter(|&i| !w.slimes[i].dead)
                    .min_by(|&a, &b| {
                        w.slimes[a]
                            .point()
                            .distance(me)
                            .total_cmp(&w.slimes[b].point().distance(me))
                    })
            else {
                break;
            };
            if auto_brain {
                let mates: Vec<u64> = w.players.keys().copied().collect();
                w.auto_play(session, &mates, Some(near));
                continue;
            }
            // The mechanics' answers: where to stand, what to hit first, whether to hold fire.
            let play = if answers { w.boss_play(session) } else { None };
            if let Some(target) = play.as_ref().and_then(|b| b.target)
                && !w.slimes[target].dead
            {
                near = target;
            }
            let goal = play.as_ref().and_then(|b| b.goal);
            let stay = play.as_ref().is_some_and(|b| b.stay);
            if goal.is_some() || stay {
                // Running somewhere: a hero with a target walks toward it, so let go of it until they are there.
                let p = w.players.get_mut(&session).unwrap();
                p.target = None;
                p.goal = None;
                *aimed_at = usize::MAX;
            } else if *aimed_at != near || w.players[&session].target != Some(near) {
                // (the engine drops a target now and then: say it again whenever the fighter has lost it)
                *aimed_at = near;
                w.message(session, ClientMessage::Target { id: near });
            }
            if let Some(goal) = play.as_ref().and_then(|b| b.goal) {
                let before = w.players[&session].character.point();
                walk_to(&mut w, session, goal);
                if trace && n == 0 && (20.0..20.3).contains(&(w.time - start_time)) {
                    let after = w.players[&session].character.point();
                    let mut probe = Point {
                        x: before.x,
                        y: before.y - 0.26,
                    };
                    w.maps[w.players[&session].character.zone].collide(&mut probe, PLAYER_RADIUS);
                    eprintln!(
                        "  t=20 walk ({:.3},{:.3}) -> ({:.3},{:.3}) goal ({:.1},{:.1}) north-probe ({:.3},{:.3})",
                        before.x, before.y, after.x, after.y, goal.x, goal.y, probe.x, probe.y
                    );
                }
            } else if !stay {
                walk_up_to_held(&mut w, session, near, true);
            }
            if !play.as_ref().is_some_and(|b| b.hold_fire) {
                cast_skills(&mut w, session, near, stay, &mut out);
            }
            if case.consumables {
                use_consumables(&mut w, session, &mut out);
            }
        }
        // A hirer who fell stays down (like a bot that fell); the party is only beaten when the hired fighters are too.
        let hired_alive = w
            .players
            .values()
            .any(|p| p.merc.is_some() && p.character.hp > 0.);
        if !anyone_alive && !hired_alive {
            break;
        }
        w.step();
        if trace
            && std::env::var("DUNGEON_MERC_TRACE").is_ok()
            && w.boss.fights.contains_key(&ids[0])
        {
            let t = w.time - start_time;
            if (28. ..37.).contains(&t) && ((t * 20.).round() as u64).is_multiple_of(5) {
                let hired: Vec<u64> = w
                    .players
                    .iter()
                    .filter(|(_, p)| p.merc.is_some())
                    .map(|(s, _)| *s)
                    .collect();
                for session in hired {
                    let p = &w.players[&session];
                    let (at, goal, target) = (p.character.point(), p.goal, p.target);
                    let play = w.boss_play(session);
                    let bodies: Vec<(f64, f64)> = w
                        .slimes
                        .iter()
                        .filter(|s| {
                            s.zone == zone
                                && !s.dead
                                && (s.id == ids[0] || s.kind == "solar_cinder")
                        })
                        .map(|s| (s.x.round(), s.y.round()))
                        .collect();
                    let line = if bodies.len() == 2 {
                        Some(
                            (crate::bossmech::segment_distance(
                                at,
                                Point {
                                    x: bodies[0].0,
                                    y: bodies[0].1,
                                },
                                Point {
                                    x: bodies[1].0,
                                    y: bodies[1].1,
                                },
                            ) * 10.)
                                .round()
                                / 10.,
                        )
                    } else {
                        None
                    };
                    eprintln!(
                        "  t={t:.2} bodies {bodies:?} line-dist {line:?} merc {:?} at ({:.1},{:.1}) goal {:?} target {:?} play goal {:?} hold {} stay {} ptarget {:?}",
                        w.players[&session].character.look.class,
                        at.x,
                        at.y,
                        goal.map(|g| (g.x.round(), g.y.round())),
                        target,
                        play.as_ref()
                            .and_then(|b| b.goal)
                            .map(|g| (g.x.round(), g.y.round())),
                        play.as_ref().is_some_and(|b| b.hold_fire),
                        play.as_ref().is_some_and(|b| b.stay),
                        play.as_ref().and_then(|b| b.target),
                    );
                }
            }
        }
        for (session, was_down) in merc_down.iter_mut() {
            let down = w.players.get(session).is_none_or(|p| p.character.hp <= 0.);
            if down && !*was_down {
                falls += 1;
                if trace && let Some(p) = w.players.get(session) {
                    let boss = w.slimes[ids[0]].point();
                    let partner = w
                        .slimes
                        .iter()
                        .find(|s| s.kind == "solar_cinder" && s.zone == zone && !s.dead)
                        .map(|s| s.point());
                    eprintln!(
                        "  t={:.1} merc {:?} down at ({:.1},{:.1}); boss ({:.1},{:.1}) partner {:?} off the line {:?}",
                        w.time - start_time,
                        p.character.look.class,
                        p.character.x,
                        p.character.y,
                        boss.x,
                        boss.y,
                        partner.map(|q| (q.x.round(), q.y.round())),
                        partner.map(|q| (crate::bossmech::segment_distance(
                            p.character.point(),
                            boss,
                            q
                        ) * 10.)
                            .round()
                            / 10.)
                    );
                }
            }
            *was_down = down;
        }
        for (n, rx) in rxs.iter_mut().enumerate() {
            for v in drain(rx) {
                if n == 0 && v["kind"] == "death" {
                    falls += 1;
                }
                if trace && n == 0 && v["kind"] == "death" {
                    let who: Vec<String> = (0..members.len())
                        .map(|k| {
                            let c = &w.players[&(k as u64 + 1)].character;
                            format!("({:.2},{:.2})", c.x, c.y)
                        })
                        .collect();
                    let threats: Vec<String> = (0..members.len())
                        .map(|k| {
                            let c = &w.players[&(k as u64 + 1)].character;
                            format!(
                                "{:?}",
                                w.bot_threat(zone, k as u64 + 1, c.point(), 1.2)
                                    .map(|t| (t * 10.).round() / 10.)
                            )
                        })
                        .collect();
                    eprintln!(
                        "  t=D {} threat {} boss ({:.1},{:.1})",
                        who.join(" "),
                        threats.join(" "),
                        w.slimes[ids[0]].x,
                        w.slimes[ids[0]].y
                    );
                    eprintln!(
                        "  t={:.1} death of {} cause {}",
                        w.time - start_time,
                        v["actor"],
                        v["cause"]
                    );
                }
            }
        }
        // `DUNGEON_BOSS_TRACE=1` prints the fight every five seconds: the boss's health, its shield, each fighter.
        if trace && (((w.time - start_time) * 20.).round() as u64).is_multiple_of(100) {
            let boss = &w.slimes[ids[0]];
            let shield = w.boss.fights.get(&ids[0]).and_then(|f| f.shield_alive(&w));
            let frozen = w.boss.fights.get(&ids[0]).map_or(0, |f| f.frozen_count());
            let mut sessions: Vec<u64> = w.players.keys().copied().collect();
            sessions.sort_unstable();
            let who: Vec<String> = sessions
                .iter()
                .map(|s| {
                    let p = &w.players[s];
                    let c = &p.character;
                    format!(
                        "{}{:.0}%@({:.0},{:.0})",
                        if p.merc.is_some() { "m" } else { "" },
                        c.hp / c.max_hp() * 100.,
                        c.x,
                        c.y
                    )
                })
                .collect();
            eprintln!(
                "  t={:.0} boss {:.0}% at ({:.0},{:.0}) state {} shield {:?} frozen {} clear {} party {}",
                w.time - start_time,
                boss.hp / boss.max_hp * 100.,
                boss.x,
                boss.y,
                boss.state,
                shield,
                frozen,
                w.maps[zone].line_clear(w.players[&1].character.point(), boss.point(), 0.3),
                who.join(" ")
            );
        }
    }
    PartyOutcome {
        killed: killed || ids.iter().all(|&i| w.slimes[i].dead),
        // every time a member fell, not only the ones down at the end
        deaths: falls,
        seconds: w.time - start_time,
        enemy_left: left(&w).clamp(0., 1.),
        break_spare: w.boss.spare.clone(),
        unstuck,
        dps: classes
            .iter()
            .map(|(s, c)| {
                let damage = w.damage_log.get(s).copied().unwrap_or(0.);
                (*c, damage / (w.time - start_time).max(1.))
            })
            .collect(),
    }
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
        // Dungeon pack mobs are hardened on purpose (a pack must kill a lone player, `world/elite-power.txt`).
        if crate::items::elite_power(&spawn.kind).1 > 2. {
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
                                enemy_level: None,
                                cap: None,
                                run_to_end: false,
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
