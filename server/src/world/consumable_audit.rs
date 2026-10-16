//! `CONS-AUDIT`: how the potions and food compare with real characters (`docs/consumable-audit.md`).
//!
//! Characters are built exactly like the kill-time harness builds them (normal gear for the level, `ttk::build_character`),
//! so health, mana, defense and dodge come from the real formulas. Monster damage uses the damage rule of
//! `hurt_player_by`: `max(damage - defense, 1) * DAMAGE_TAKEN_SCALE`, one hit per windup plus cooldown. Run with
//! `bash scripts/cargo.sh test --offline consumable_audit -- --ignored --nocapture` and `CONS_OUT=path.json`.
use super::ttk::{CLASSES, Case, Foe, Spread, build_character, pick_enemy};
use super::wyrd_tests::world;
use super::*;

/// The levels of the audit: 1, then every ten levels, and the two new final tiers.
pub fn audit_levels() -> Vec<u32> {
    [1].into_iter()
        .chain((1..=9).map(|n| n * 10))
        .chain([95, 99])
        .collect()
}
/// Midpoint of the authoritative target band, plus 10 s to find the next monster.
/// Level 1 is outside the kill-time grid and retains the original 22.5 s estimate.
pub fn seconds_per_kill(level: u32) -> f64 {
    if level < 5 {
        return 32.5;
    }
    let bands: Vec<Value> =
        serde_json::from_str(include_str!("../../../world/ttk-targets.txt")).unwrap();
    let band = bands
        .iter()
        .find(|b| {
            level >= b["minLevel"].as_u64().unwrap() as u32
                && level <= b["maxLevel"].as_u64().unwrap() as u32
        })
        .unwrap_or_else(|| panic!("no kill-time target for level {level}"));
    (band["minSeconds"].as_f64().unwrap() + band["maxSeconds"].as_f64().unwrap()) / 2. + 10.
}
/// One enemy: damage taken per second by `defense`, and the damage of one hit.
fn enemy_row(w: &World, id: usize, defense: f64, dodge: f64) -> Value {
    let s = &w.slimes[id];
    let (windup, cooldown, ..) = Slime::attack_profile(&s.kind);
    let hit = ((s.damage - defense).max(1.) * DAMAGE_TAKEN_SCALE)
        .round()
        .max(1.);
    json!({"kind": s.kind, "level": s.level, "hp": s.max_hp, "hit": hit,
           "perSecond": hit * (1. - dodge) / (windup + cooldown), "gold": s.gold})
}
/// The closest boss or elite of the data to `level` (any zone), with its level pinned to the character's.
fn pinned(w: &mut World, level: u32, boss: bool) -> Option<usize> {
    let mut best: Option<(u32, usize)> = None;
    for s in &w.slimes {
        if s.kind == "big" || is_boss(&s.kind) != boss || (!boss && !is_elite(&s.kind)) {
            continue;
        }
        let gap = Slime::default_level(&s.kind).abs_diff(level);
        if best.is_none_or(|b| (gap, s.id) < b) {
            best = Some((gap, s.id));
        }
    }
    let id = best?.1;
    let spawn = w.spawns[id].clone();
    w.slimes[id] = Slime::with_level(id, &spawn, level);
    Some(id)
}

#[test]
#[ignore = "audit table; see the module comment"]
fn consumable_audit() {
    let mut w = world();
    let mut rows = vec![];
    for level in audit_levels() {
        let ordinary = pick_enemy(&w, level.max(5), Foe::Ordinary).unwrap();
        let spawn = w.spawns[ordinary].clone();
        w.slimes[ordinary] = Slime::with_level(ordinary, &spawn, level);
        let elite = pinned(&mut w, level, false).unwrap();
        let boss = pinned(&mut w, level, true).unwrap();
        let health = crate::items::best_tier("health_potion", level).unwrap();
        let mana = crate::items::best_tier("mana_potion", level).unwrap();
        let food = crate::items::best_tier("traveler_stew", level).unwrap();
        for class in CLASSES {
            for (name, spread) in [
                ("even", Spread::Even),
                ("stamina", Spread::Stamina),
                ("main", Spread::Damage),
            ] {
                let mut c = Character::mercenary(class, level, "Audit");
                // Level 1 has no normal set and no points to spend, so it keeps the starter character as it is.
                if level >= 5 {
                    build_character(
                        &mut c,
                        &Case {
                            spread,
                            ..Case::new(class, level)
                        },
                    );
                }
                let (max_hp, defense) = (c.max_hp(), c.stats().1);
                let dodge = c.dodge_chance();
                let mana_user = class.resource_type() == "mana";
                let max_resource = c.max_resource();
                let health_heal = super::consumables::health_amount(health, &c);
                let food_heal = super::consumables::health_amount(food, &c);
                let enemies: Vec<Value> = [ordinary, elite, boss]
                    .iter()
                    .map(|&id| enemy_row(&w, id, defense, dodge))
                    .collect();
                let per_kill = seconds_per_kill(level);
                let ordinary_dps = enemies[0]["perSecond"].as_f64().unwrap();
                // Damage absorbed per hour while fighting about half of every kill cycle, in potions.
                let fighting = per_kill - 10.;
                let hurt_per_hour = ordinary_dps * fighting * 3600. / per_kill;
                let kills_per_hour = 3600. / per_kill;
                rows.push(json!({
                    "level": level, "class": format!("{class:?}").to_lowercase(), "spread": name,
                    "maxHp": max_hp, "maxMana": if mana_user { max_resource } else { 0. }, "defense": defense, "dodge": dodge,
                    "potion": {"id": health.id, "heal": health_heal, "flat": health.heal,
                               "pctMaxHp": health_heal / max_hp * 100.,
                               "price": health.price, "perSecond": health_heal / health.cooldown},
                    "manaPotion": {"id": mana.id, "mana": mana.mana, "pctMaxMana": if mana_user { mana.mana / max_resource * 100. } else { 0. },
                                   "price": mana.price},
                    "food": {"id": food.id, "heal": food_heal, "flat": food.heal, "mana": food.mana,
                             "pctMaxHp": food_heal / max_hp * 100.,
                             "perSecond": food_heal / food.duration, "price": food.price},
                    "enemies": enemies,
                    "killsPerHour": kills_per_hour,
                    "goldPerHour": enemies[0]["gold"].as_f64().unwrap() * kills_per_hour,
                    "damagePerHour": hurt_per_hour,
                    "potionsPerHour": hurt_per_hour / health_heal,
                    "potionGoldPerHour": hurt_per_hour / health_heal * health.price as f64,
                    "continuousPotionGoldPerHour": 60. * health.price as f64,
                }));
            }
        }
    }
    let text = serde_json::to_string_pretty(&rows).unwrap();
    if let Ok(path) = std::env::var("CONS_OUT") {
        std::fs::write(path, &text).unwrap();
    }
    println!("{} rows", rows.len());
}

#[test]
fn the_audit_rows_use_the_documented_levels_and_positive_numbers() {
    assert_eq!(audit_levels().len(), 12);
    assert_eq!(audit_levels()[..3], [1, 10, 20]);
    assert_eq!(audit_levels()[10..], [95, 99]);
    assert!(seconds_per_kill(5) < seconds_per_kill(99));
}
