//! Post-launch catalog goals exercise saved gameplay facts without grinding.
use super::*;
use crate::model::{Class, FishRecord, Point, QuestProgress};

fn hero() -> Character {
    Character::mercenary(Class::Warrior, 1, "New Achiever")
}
fn goal(id: &str) -> &'static Achievement {
    catalog().iter().find(|a| a.id == id).unwrap()
}
fn claimed(id: &str, completions: u32) -> QuestProgress {
    QuestProgress {
        id: id.into(),
        counts: vec![],
        claimed: completions > 0,
        completions,
    }
}
fn bosses() -> Vec<String> {
    goal("dungeon_master")
        .members
        .iter()
        .cloned()
        .chain(FORGE_BOSSES.iter().map(|s| (*s).into()))
        .collect()
}
fn seed(c: &mut Character, metric: &str, count: u32) {
    match metric {
        "kills" => c.kills = count,
        "quests" => {
            c.quests = (0..count)
                .map(|i| claimed(&format!("history_{i}"), 1))
                .collect()
        }
        "bosses" => c.achievements.bosses = bosses().into_iter().take(count as usize).collect(),
        "rebirth" => c.rebirth_tiers = [count, 0, 0, 0, 0],
        "mounts" => {
            c.mounts = crate::model::MOUNTS
                .iter()
                .take(count as usize)
                .map(|m| m.id.into())
                .collect()
        }
        "fish_catches" => c.fishing.total = u64::from(count),
        "fish_legendary" => c.fishing.legendary = u64::from(count),
        _ => panic!("unexpected metric {metric}"),
    }
}

#[test]
fn achievements_refresh_preserves_the_entire_old_catalog() {
    use sha2::{Digest, Sha256};
    let raw: Vec<Value> =
        serde_json::from_str(include_str!("../../world/achievements.txt")).unwrap();
    let digest = format!(
        "{:x}",
        Sha256::digest(serde_json::to_vec(&raw[..120]).unwrap())
    );
    assert_eq!(
        digest,
        "1810c83c4ac9b02244e60fd41d3d3f680f4893a715508dd4bc4ace1504a10620"
    );
    assert_eq!(raw.len(), 154);
    assert_eq!(catalog().iter().map(|a| a.points).sum::<u32>(), 4090);
    assert_eq!(
        catalog().iter().skip(120).map(|a| a.points).sum::<u32>(),
        1535
    );
    assert_eq!(
        catalog()
            .iter()
            .skip(120)
            .filter(|a| !a.title.is_empty())
            .count(),
        8
    );
    assert!(
        catalog()
            .iter()
            .skip(120)
            .all(|a| !a.title_prefix && a.mount.is_empty())
    );
}

#[test]
fn achievements_refresh_numeric_goals_award_at_the_exact_boundary_once() {
    for (metric, targets) in [
        ("kills", &[2500, 5000, 10000, 25000, 50000][..]),
        ("bosses", &[5, 10, 25, 50, 75][..]),
        ("quests", &[200, 300, 500, 750][..]),
        ("rebirth", &[10, 20, 30][..]),
        ("mounts", &[8, 10, 12][..]),
        ("fish_catches", &[10, 25, 250, 500, 2500, 5000][..]),
        ("fish_legendary", &[10, 50][..]),
    ] {
        for &target in targets {
            let prefix = match metric {
                "fish_catches" => "fish",
                "rebirth" => "rebirth",
                other => other,
            };
            let id = format!("{prefix}_{target}");
            let a = goal(&id);
            assert_eq!(a.target, target, "{id}");
            assert_eq!(a.metric, metric, "{id}");
            let mut c = hero();
            seed(&mut c, metric, target - 1);
            c.sync_achievements();
            assert_eq!(c.achievement_progress(a), target - 1, "{id}");
            assert!(!c.achievements.completed.contains(&id), "early award: {id}");
            seed(&mut c, metric, target);
            assert!(c.sync_achievements().contains(&id), "missing award: {id}");
            assert_eq!(c.achievement_progress(a), target, "{id}");
            let points = c.achievement_points();
            assert!(c.sync_achievements().is_empty(), "duplicate: {id}");
            assert_eq!(c.achievement_points(), points);
            let mut restored: Character =
                serde_json::from_value(serde_json::to_value(c).unwrap()).unwrap();
            assert!(restored.sync_achievements().is_empty());
            assert!(restored.achievements.completed.contains(&id));
        }
    }
}

#[test]
fn achievements_refresh_collections_match_real_fish_and_distinct_fisher_quests() {
    let fish: Vec<Value> = serde_json::from_str(include_str!("../../world/fish.txt")).unwrap();
    let a = goal("fish_log_all");
    let expected: BTreeSet<_> = fish
        .iter()
        .map(|f| f["item"].as_str().unwrap().to_owned())
        .collect();
    assert_eq!(a.members.iter().cloned().collect::<BTreeSet<_>>(), expected);
    assert_eq!(a.target, 57);
    let map: Value = serde_json::from_str(include_str!("../../world/map.txt")).unwrap();
    let quests: Vec<_> = std::iter::once(&map)
        .chain(map["zones"].as_array().unwrap())
        .flat_map(|z| z["quests"].as_array().unwrap())
        .collect();
    for tier in 1..=4 {
        let a = goal(&format!("fisher_circuit_{tier}"));
        let suffix = format!("_{tier}");
        let expected: BTreeSet<_> = quests
            .iter()
            .filter_map(|q| q["id"].as_str())
            .filter(|id| id.starts_with("fisher_") && id.ends_with(&suffix))
            .map(str::to_owned)
            .collect();
        assert_eq!(a.members.iter().cloned().collect::<BTreeSet<_>>(), expected);
        assert_eq!(a.target, 13);
        assert_eq!(a.members.len(), 13);
    }
    assert!(quests.iter().any(|q| q["id"] == "deep_seahorse"));
    assert_eq!(goal("seahorse_friend").members, ["deep_seahorse"]);
}

#[test]
fn achievements_refresh_missing_species_cannot_be_replaced_by_duplicates_or_inventory() {
    let a = goal("fish_log_all");
    for missing in &a.members {
        let mut c = hero();
        for id in &a.members {
            c.fishing.species.insert(
                id.clone(),
                FishRecord {
                    count: if id == missing { 0 } else { 100 },
                    best_kg: 100,
                },
            );
        }
        c.fishing.total = 5700;
        c.fishing.species.insert(
            "fish_invented".into(),
            FishRecord {
                count: 100,
                best_kg: 100,
            },
        );
        c.add_item(missing, 1);
        c.sync_achievements();
        assert_eq!(c.achievement_progress(a), 56, "{missing}");
        assert!(!c.achievements.completed.contains(&a.id));
        assert!(c.select_achievement_title(&a.id).is_err());
        c.fishing.species.get_mut(missing).unwrap().count = 1;
        assert!(c.sync_achievements().contains(&a.id));
        c.select_achievement_title(&a.id).unwrap();
        assert_eq!(c.achievement_title(), "The Complete Angler");
    }
}

#[test]
fn achievements_refresh_fisher_circuits_require_each_claim_across_lifetimes() {
    for tier in 1..=4 {
        let a = goal(&format!("fisher_circuit_{tier}"));
        for missing in &a.members {
            let mut c = hero();
            c.quests = a
                .members
                .iter()
                .filter(|id| *id != missing)
                .map(|id| claimed(id, 20))
                .collect();
            // An accepted or ready quest, and repeated claims elsewhere, cannot replace this Fisher.
            c.quests.push(claimed(missing, 0));
            c.sync_achievements();
            assert_eq!(c.achievement_progress(a), 12, "{missing}");
            assert!(!c.achievements.completed.contains(&a.id));
            c.level = 50;
            c.rebirth(Point { x: 36., y: 60. }).unwrap();
            assert!(c.quests.is_empty());
            c.quests.push(claimed(missing, 1));
            assert!(c.sync_achievements().contains(&a.id), "{missing}");
            assert!(c.sync_achievements().is_empty());
        }
    }
    let mut c = hero();
    c.grant_mount("seahorse");
    c.quests.push(claimed("deep_seahorse", 0));
    c.sync_achievements();
    assert!(!c.achievements.completed.contains("seahorse_friend"));
    c.quests = vec![claimed("deep_seahorse", 1)];
    assert!(c.sync_achievements().contains(&"seahorse_friend".into()));
    assert_eq!(c.mounts, ["seahorse"]);
}

#[test]
fn achievements_refresh_new_titles_unlock_and_survive_rebirth_and_legacy_saves() {
    for (id, title) in [
        ("kills_10000", "The Relentless"),
        ("bosses_50", "The Vanquisher"),
        ("quests_500", "The Storykeeper"),
        ("rebirth_10", "The Everlasting"),
        ("mounts_10", "The Collector"),
        ("fish_5000", "The Tidemaster"),
        ("fish_log_all", "The Complete Angler"),
        ("fisher_circuit_3", "Friend of the Fishers"),
    ] {
        let a = goal(id);
        assert_eq!(a.title, title);
        let mut c = hero();
        c.achievements.title = "".into();
        assert!(c.select_achievement_title(id).is_err());
        match a.metric.as_str() {
            "fish_set" => {
                for id in &a.members {
                    c.fishing.species.insert(
                        id.clone(),
                        FishRecord {
                            count: 1,
                            best_kg: 1,
                        },
                    );
                }
            }
            "quest_set" => c.quests = a.members.iter().map(|id| claimed(id, 1)).collect(),
            metric => seed(&mut c, metric, a.target),
        }
        // Old saves have no ledger: only verifiable facts may be reconstructed.
        if a.metric != "bosses" {
            let mut old = serde_json::to_value(&c).unwrap();
            old.as_object_mut().unwrap().remove("achievements");
            c = serde_json::from_value(old).unwrap();
        }
        assert!(c.sync_achievements().contains(&id.to_owned()));
        c.select_achievement_title(id).unwrap();
        c.level = 50;
        c.rebirth(Point { x: 36., y: 60. }).unwrap();
        let points = c.achievement_points();
        let mut restored: Character =
            serde_json::from_value(serde_json::to_value(c).unwrap()).unwrap();
        assert!(restored.sync_achievements().is_empty());
        assert_eq!(restored.achievement_title(), title);
        assert_eq!(restored.achievement_title_position(), "suffix");
        assert_eq!(restored.achievement_points(), points);
    }
}
