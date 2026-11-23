use super::*;
use crate::model::{Class, FishRecord, Point};

fn hero() -> Character {
    Character::mercenary(Class::Warrior, 1, "Fishing Achiever")
}

fn achievement(id: &str) -> &'static Achievement {
    catalog().iter().find(|a| a.id == id).unwrap()
}

fn caught(c: &mut Character, id: &str, count: u64, kg: u32) {
    c.fishing
        .species
        .insert(id.into(), FishRecord { count, best_kg: kg });
}

#[test]
fn fishing_achievements_catalog_preserves_original_waters_and_rewards() {
    let fish: Vec<Value> = serde_json::from_str(include_str!("../../world/fish.txt")).unwrap();
    let fishing: Vec<_> = catalog()
        .iter()
        .filter(|a| a.category == "Fishing")
        .collect();
    assert_eq!(fishing.len(), 26);
    assert_eq!(fishing.iter().map(|a| a.points).sum::<u32>(), 670);
    assert_eq!(fishing.iter().filter(|a| !a.title.is_empty()).count(), 5);
    assert!(
        fishing
            .iter()
            .all(|a| a.mount.is_empty() && !a.title_prefix)
    );
    let original_habitats = [
        "Shore", "Cold", "Swamp", "Forest", "Jungle", "Oasis", "Spring", "Lava",
    ];
    let fish: Vec<_> = fish
        .into_iter()
        .filter(|f| original_habitats.contains(&f["habitat"].as_str().unwrap()))
        .collect();
    let habitats: BTreeSet<_> = fish
        .iter()
        .map(|f| f["habitat"].as_str().unwrap())
        .collect();
    assert_eq!(habitats.len(), 8);
    let mut covered = BTreeSet::new();
    for habitat in habitats {
        let a = achievement(&format!("fish_log_{}", habitat.to_lowercase()));
        let expected: BTreeSet<_> = fish
            .iter()
            .filter(|f| f["habitat"] == habitat)
            .map(|f| f["item"].as_str().unwrap().to_owned())
            .collect();
        assert_eq!(a.metric, "fish_set");
        assert_eq!(a.members.iter().cloned().collect::<BTreeSet<_>>(), expected);
        assert_eq!(a.target as usize, expected.len());
        covered.extend(expected);
    }
    assert_eq!(covered.len(), fish.len());
    let weight = achievement("fish_weight_20");
    assert_eq!(
        weight.members.iter().cloned().collect::<BTreeSet<_>>(),
        covered
    );
    assert!(
        fish.iter()
            .any(|f| f["kg"][1].as_u64().unwrap() >= u64::from(weight.target))
    );
    assert_eq!(achievement("fish_1000").title, "the Angler");
    assert_eq!(achievement("fish_log_lava").title, "Lavacaster");
    assert_eq!(crate::model::MOUNTS.len(), 12); // Fishing quest adds the underwater seahorse.
}

#[test]
fn fishing_achievements_total_boundaries_clamp_and_award_once() {
    for (id, target) in [("fish_1", 1), ("fish_100", 100), ("fish_1000", 1000)] {
        let a = achievement(id);
        assert_eq!(a.target, target);
        let mut c = hero();
        c.fishing.total = u64::from(target - 1);
        c.sync_achievements();
        assert_eq!(c.achievement_progress(a), target - 1);
        assert!(!c.achievements.completed.contains(id));
        c.fishing.total += 1;
        assert!(c.sync_achievements().contains(&id.to_owned()));
        assert_eq!(c.achievement_progress(a), target);
        let points = c.achievement_points();
        assert!(c.sync_achievements().is_empty());
        assert_eq!(c.achievement_points(), points);
        // 2^32 would wrap to zero if converted before clamping.
        c.fishing.total = 1u64 << 32;
        assert_eq!(c.achievement_progress(a), target);
        c.fishing.total = u64::MAX;
        assert_eq!(c.achievement_progress(a), target);
    }
}

#[test]
fn fishing_achievements_collections_require_each_positive_species_record() {
    for a in catalog().iter().filter(|a| a.metric == "fish_set") {
        let mut c = hero();
        for id in &a.members[..a.members.len() - 1] {
            caught(&mut c, id, 1000, 20);
        }
        // Owning a fish, unknown records and records with no catch are not evidence.
        let last = a.members.last().unwrap();
        c.add_item(last, 1);
        caught(&mut c, last, 0, 20);
        caught(&mut c, "fish_unknown", 1000, 100);
        caught(&mut c, "fishing_cooled_slag", 1000, 100);
        for other in catalog()
            .iter()
            .filter(|other| other.metric == "fish_set" && other.id != a.id)
        {
            // Collections now overlap: the all-species goal includes every habitat.
            // Seed only foreign species so this fixture keeps its required species missing.
            for id in other.members.iter().filter(|id| !a.members.contains(id)) {
                caught(&mut c, id, 1, 1);
            }
        }
        c.sync_achievements();
        assert_eq!(c.achievement_progress(a), a.target - 1, "{}", a.id);
        assert!(!c.achievements.completed.contains(&a.id), "{}", a.id);
        caught(&mut c, last, 1, 1);
        assert!(c.sync_achievements().contains(&a.id));
        assert_eq!(c.achievement_progress(a), a.target);
        assert!(c.sync_achievements().is_empty());
    }
    let lava = achievement("fish_log_lava");
    for missing in ["fish_phoenix_koi", "fish_sunfire_ray"] {
        let mut c = hero();
        for id in lava.members.iter().filter(|id| id.as_str() != missing) {
            caught(&mut c, id, 1, 1);
        }
        c.sync_achievements();
        assert!(!c.achievements.completed.contains(&lava.id));
        assert!(c.select_achievement_title(&lava.id).is_err());
    }
}

#[test]
fn fishing_achievements_legendary_and_weight_require_catch_evidence() {
    let mut c = hero();
    let legendary = achievement("fish_legendary");
    let weight = achievement("fish_weight_20");
    c.add_item("fish_phoenix_koi", 1);
    caught(&mut c, "fish_unknown", 1, 100);
    caught(&mut c, "fishing_cooled_slag", 1, 100);
    caught(&mut c, "fish_sunfire_ray", 0, 23);
    c.sync_achievements();
    assert_eq!(c.achievement_progress(legendary), 0);
    assert_eq!(c.achievement_progress(weight), 0);
    c.fishing.legendary = 1;
    caught(&mut c, "fish_sunfire_ray", 1, 19);
    assert!(c.sync_achievements().contains(&legendary.id));
    assert!(!c.achievements.completed.contains(&weight.id));
    assert_eq!(c.achievement_progress(weight), 19);
    caught(&mut c, "fish_sunfire_ray", 2, 20);
    assert!(c.sync_achievements().contains(&weight.id));
    caught(&mut c, "fish_sunfire_ray", 3, 23);
    assert_eq!(c.achievement_progress(weight), 20);
    c.fishing.legendary = 1u64 << 32;
    assert_eq!(c.achievement_progress(legendary), 1);
    // A huge old log now legitimately earns the new 10/50-legendary milestones.
    assert_eq!(
        c.sync_achievements(),
        ["fish_legendary_10", "fish_legendary_50"]
    );
    assert!(c.sync_achievements().is_empty());
}

#[test]
fn fishing_achievements_old_logs_titles_save_and_rebirth_keep_progress() {
    let mut c = hero();
    assert!(c.select_achievement_title("fish_1000").is_err());
    c.fishing.total = 999;
    c.fishing.legendary = 1;
    for id in &achievement("fish_log_lava").members {
        caught(&mut c, id, 1, 20);
    }
    // Existing log reconciles from a save with no achievement ledger.
    let mut old = serde_json::to_value(&c).unwrap();
    old.as_object_mut().unwrap().remove("achievements");
    let mut c: Character = serde_json::from_value(old.clone()).unwrap();
    let newly = c.sync_achievements();
    assert!(newly.contains(&"fish_log_lava".to_owned()));
    assert!(!newly.contains(&"fish_1000".to_owned()));
    c.select_achievement_title("fish_log_lava").unwrap();
    assert_eq!(c.achievement_title(), "Lavacaster");
    assert_eq!(c.achievement_title_position(), "suffix");
    assert!(c.select_achievement_title("fish_1000").is_err());
    assert_eq!(c.achievement_title(), "Lavacaster");
    c.level = 99;
    c.rebirth(Point { x: 36., y: 60. }).unwrap();
    assert_eq!(c.fishing.total, 999);
    assert_eq!(
        c.fishing.species.len(),
        achievement("fish_log_lava").members.len()
    );
    assert_eq!(c.achievement_title(), "Lavacaster");
    c.fishing.total += 1;
    assert!(c.sync_achievements().contains(&"fish_1000".to_owned()));
    c.select_achievement_title("fish_1000").unwrap();
    assert_eq!(c.achievement_title(), "the Angler");
    let points = c.achievement_points();
    let mut saved: Character = serde_json::from_value(serde_json::to_value(&c).unwrap()).unwrap();
    assert!(saved.sync_achievements().is_empty());
    assert_eq!(saved.achievement_points(), points);
    assert_eq!(saved.achievement_view()["selected"], "fish_1000");
    assert_eq!(saved.achievement_title(), "the Angler");
    // A save predating fishing must not invent progress or rewards.
    old.as_object_mut().unwrap().remove("fishing");
    let mut old: Character = serde_json::from_value(old).unwrap();
    old.sync_achievements();
    assert!(
        old.achievements
            .completed
            .iter()
            .all(|id| !id.starts_with("fish_"))
    );
}
