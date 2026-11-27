//! The owner's 1.15.9 correction: 25% below current dungeon health and damage,
//! leaving the earlier baseline's 50% increase, scoped to ordinary dungeons.
use super::wyrd_tests::world;
use super::*;
use std::collections::BTreeSet;

fn boss_hp_factor(kind: &str) -> f64 {
    if crate::items::is_boss(kind) {
        0.75
    } else {
        1.
    }
}

fn before() -> BTreeMap<String, [f64; 2]> {
    serde_json::from_str(include_str!(
        "../../../tests/fixtures/dungeon-power-before-1.15.9.txt"
    ))
    .unwrap()
}

fn is_dungeon(w: &World, zone: usize) -> bool {
    let map = &w.maps[w.maps[zone].template.unwrap_or(zone)];
    map.copies > 0 && !map.raid
}

fn close(actual: f64, expected: f64, kind: &str, stat: &str) {
    assert!(
        (actual - expected).abs() < expected.abs().max(1.) * 1e-10,
        "{kind} {stat}: expected {expected}, got {actual}"
    );
}

#[test]
fn dungeon_difficulty_reduces_current_pack_boss_and_helper_stats_by_25_percent_only() {
    let w = world();
    let old = before();
    let original: BTreeMap<String, [f64; 2]> = serde_json::from_str(include_str!(
        "../../../tests/fixtures/dungeon-power-before-1.15.5.txt"
    ))
    .unwrap();
    let dungeon_kinds: BTreeSet<_> = w
        .spawns
        .iter()
        .filter(|s| is_dungeon(&w, s.zone))
        .map(|s| s.kind.as_str())
        .collect();
    let outside_kinds: BTreeSet<_> = w
        .spawns
        .iter()
        .filter(|s| !is_dungeon(&w, s.zone))
        .map(|s| s.kind.as_str())
        .collect();
    assert!(dungeon_kinds.is_disjoint(&outside_kinds));
    assert_eq!(dungeon_kinds.len(), 127, "all authored dungeon enemy kinds");
    for kind in &dungeon_kinds {
        let prior = old.get(*kind).copied().unwrap_or([1., 1.]);
        let (base_hp, base_damage, speed, scale) = Slime::base_stats(kind);
        let actual = Slime::stats(kind);
        close(
            actual.0,
            base_hp * prior[0] * 0.75 * boss_hp_factor(kind),
            kind,
            "health",
        );
        close(actual.1, base_damage * prior[1] * 0.75, kind, "damage");
        let unboosted = original.get(*kind).copied().unwrap_or([1., 1.]);
        close(
            prior[0] * 0.75 * boss_hp_factor(kind),
            unboosted[0] * 1.5 * boss_hp_factor(kind),
            kind,
            "remaining health boost",
        );
        close(
            prior[1] * 0.75,
            unboosted[1] * 1.5,
            kind,
            "remaining damage boost",
        );
        assert_eq!((actual.2, actual.3), (speed, scale));
    }
    for kind in outside_kinds
        .iter()
        .copied()
        .chain(old.keys().map(String::as_str))
    {
        if dungeon_kinds.contains(kind) {
            continue;
        }
        let prior = old.get(kind).copied().unwrap_or([1., 1.]);
        assert_eq!(
            crate::items::elite_power(kind),
            (prior[0], prior[1]),
            "{kind} is outside the dungeon change"
        );
    }
}

#[test]
fn dungeon_difficulty_reaches_spawned_monsters_and_every_private_copy() {
    let w = world();
    let old = before();
    let mut templates = BTreeSet::new();
    let mut copies = BTreeSet::new();
    for spawn in &w.spawns {
        if !is_dungeon(&w, spawn.zone) {
            continue;
        }
        let template = w.maps[spawn.zone].template.unwrap_or(spawn.zone);
        templates.insert(template);
        copies.insert(spawn.zone);
        let prior = old.get(&spawn.kind).copied().unwrap_or([1., 1.]);
        let (base_hp, base_damage, _, _) = Slime::base_stats(&spawn.kind);
        // Check normal levels as well as the existing random level spread.
        for level in [
            Slime::default_level(&spawn.kind).saturating_sub(2).max(1),
            Slime::default_level(&spawn.kind),
            Slime::default_level(&spawn.kind) + 2,
        ] {
            let monster = Slime::with_level(0, spawn, level);
            let strength = Slime::level_scale(&spawn.kind, level, LEVEL_HP_DAMAGE);
            close(
                monster.max_hp,
                (base_hp * prior[0] * 0.75 * boss_hp_factor(&spawn.kind) * strength).round(),
                &spawn.kind,
                "spawn health",
            );
            close(
                monster.damage,
                (base_damage * prior[1] * 0.75 * strength).round(),
                &spawn.kind,
                "spawn damage",
            );
            assert_eq!(monster.hp, monster.max_hp);
        }
    }
    assert_eq!(templates.len(), 20);
    assert_eq!(copies.len(), 80, "four copies of each ordinary dungeon");
}

#[test]
fn dungeon_difficulty_boss_health_cut_preserves_every_other_power_value() {
    let w = world();
    let prior: BTreeMap<String, [f64; 2]> = serde_json::from_str(include_str!(
        "../../../tests/fixtures/dungeon-power-before-boss-hp.txt"
    ))
    .unwrap();
    let bosses: BTreeSet<_> = w
        .spawns
        .iter()
        .filter(|s| is_dungeon(&w, s.zone) && crate::items::is_boss(&s.kind))
        .map(|s| s.kind.as_str())
        .collect();
    assert_eq!(bosses.len(), 65);
    assert!(
        w.spawns
            .iter()
            .filter(|s| !is_dungeon(&w, s.zone))
            .all(|s| !bosses.contains(s.kind.as_str()))
    );
    for (kind, old) in &prior {
        let actual = crate::items::elite_power(kind);
        close(
            actual.0,
            old[0]
                * if bosses.contains(kind.as_str()) {
                    0.75
                } else {
                    1.
                },
            kind,
            "boss-only health",
        );
        close(actual.1, old[1], kind, "preserved damage");
    }
}
