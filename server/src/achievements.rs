//! Character-owned achievements. Saved evidence survives rebirth; points always come from the catalog.
use crate::model::{Character, FOG_GRID};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{collections::BTreeSet, sync::OnceLock};

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct Progress {
    pub completed: BTreeSet<String>,
    pub title: String,
    pub highest_level: u32,
    pub quests: BTreeSet<String>,
    pub explored: Vec<u16>,
    pub bosses: BTreeSet<String>,
}
#[derive(Deserialize, Serialize)]
pub struct Achievement {
    pub id: String,
    pub name: String,
    pub description: String,
    pub category: String,
    pub metric: String,
    pub target: u32,
    pub points: u32,
    pub title: String,
    pub mount: String,
    pub zone: Option<usize>,
    /// Exact distinct boss or quest IDs required by a catalog set.
    #[serde(default)]
    pub members: Vec<String>,
}
pub const FORGE_BOSSES: [&str; 10] = [
    "cf_kettil",
    "cf_ysolt",
    "cf_hallgrim",
    "cf_sigrun",
    "cf_dagfinn",
    "cf_thorbjorg",
    "cf_ragnhild",
    "cf_orm",
    "cf_hildr",
    "cf_eldmarr",
];
pub fn catalog() -> &'static [Achievement] {
    static DATA: OnceLock<Vec<Achievement>> = OnceLock::new();
    DATA.get_or_init(|| {
        let rows: Vec<Achievement> =
            serde_json::from_str(include_str!("../../world/achievements.txt"))
                .expect("achievement catalog");
        let mut ids = BTreeSet::new();
        for a in &rows {
            assert!(ids.insert(&a.id) && a.points > 0 && a.target > 0);
            assert!(matches!(
                a.metric.as_str(),
                "level"
                    | "kills"
                    | "quests"
                    | "regions"
                    | "fog"
                    | "exploration"
                    | "rebirth"
                    | "story"
                    | "bosses"
                    | "forge"
                    | "mounts"
                    | "boss_set"
                    | "quest_set"
            ));
            if matches!(a.metric.as_str(), "boss_set" | "quest_set") {
                assert_eq!(a.target as usize, a.members.len());
                assert_eq!(
                    a.members.iter().collect::<BTreeSet<_>>().len(),
                    a.members.len()
                );
                if a.metric == "boss_set" {
                    assert!(a.members.iter().all(|kind| crate::items::is_boss(kind)));
                }
            }
            assert!(a.mount.is_empty() || crate::model::mount_speed(&a.mount).is_some());
        }
        rows
    })
}
pub fn regions() -> &'static [usize] {
    static DATA: OnceLock<Vec<usize>> = OnceLock::new();
    DATA.get_or_init(|| {
        let atlas: Value = serde_json::from_str(include_str!("../../world/atlas-geography.txt"))
            .expect("atlas geography");
        atlas["regions"]
            .as_array()
            .expect("atlas regions")
            .iter()
            .map(|r| r["zone"].as_u64().expect("atlas zone") as usize)
            .collect()
    })
}
const FOG_MASK: u16 = (1 << (FOG_GRID * FOG_GRID)) - 1;
impl Character {
    fn achievement_progress(&self, a: &Achievement) -> u32 {
        let p = &self.achievements;
        let cells =
            |zone: usize| (p.explored.get(zone).copied().unwrap_or(0) & FOG_MASK).count_ones();
        match a.metric.as_str() {
            "level" => p.highest_level,
            "kills" => self.kills,
            "mounts" => self.mounts.iter().collect::<BTreeSet<_>>().len() as u32,
            "quests" => p.quests.len() as u32,
            "regions" => regions().iter().filter(|&&z| cells(z) > 0).count() as u32,
            "fog" => a.zone.map_or(0, cells),
            "exploration" => regions().iter().map(|&z| cells(z)).sum(),
            "rebirth" => self.rebirth_count(),
            "story" => u32::from(p.quests.contains("es_28")),
            "bosses" => p.bosses.len() as u32,
            "boss_set" => a.members.iter().filter(|id| p.bosses.contains(*id)).count() as u32,
            "quest_set" => a.members.iter().filter(|id| p.quests.contains(*id)).count() as u32,
            "forge" => FORGE_BOSSES
                .iter()
                .filter(|&&id| p.bosses.contains(id))
                .count() as u32,
            _ => 0,
        }
        .min(a.target)
    }
    /// Reconcile saved facts and return newly earned achievements. No point balance can be spent or duplicated.
    pub fn sync_achievements(&mut self) -> Vec<String> {
        self.achievements.highest_level = self.achievements.highest_level.max(self.level);
        for q in &self.quests {
            if q.completions > 0 && !q.id.starts_with("es_go_") {
                self.achievements.quests.insert(q.id.clone());
            }
        }
        self.achievements
            .explored
            .resize(self.achievements.explored.len().max(self.explored.len()), 0);
        for (zone, &seen) in self.explored.iter().enumerate() {
            self.achievements.explored[zone] |= seen & FOG_MASK;
        }
        let mut earned = Vec::new();
        for a in catalog() {
            if self.achievement_progress(a) >= a.target
                && self.achievements.completed.insert(a.id.clone())
            {
                if !a.mount.is_empty() {
                    self.grant_mount(&a.mount);
                }
                earned.push(a.id.clone());
            }
        }
        if !self.achievements.title.is_empty() && self.achievement_title().is_empty() {
            self.achievements.title.clear();
        }
        earned
    }
    pub fn achievement_title(&self) -> &str {
        catalog()
            .iter()
            .find(|a| {
                a.id == self.achievements.title && self.achievements.completed.contains(&a.id)
            })
            .map_or("", |a| a.title.as_str())
    }
    pub fn select_achievement_title(&mut self, id: &str) -> Result<(), &'static str> {
        if !id.is_empty()
            && !catalog().iter().any(|a| {
                a.id == id && !a.title.is_empty() && self.achievements.completed.contains(id)
            })
        {
            return Err("You have not earned that title.");
        }
        self.achievements.title = id.to_owned();
        Ok(())
    }
    pub fn achievement_points(&self) -> u32 {
        catalog()
            .iter()
            .filter(|a| self.achievements.completed.contains(&a.id))
            .map(|a| a.points)
            .sum()
    }
    pub fn achievement_view(&self) -> Value {
        json!({"type":"achievements", "character":self.id, "points":self.achievement_points(),
            "maximum":catalog().iter().map(|a| a.points).sum::<u32>(), "selected":self.achievements.title,
            "entries":catalog().iter().map(|a| json!({"id":a.id,"name":a.name,"description":a.description,
                "category":a.category,"points":a.points,"target":a.target,"progress":self.achievement_progress(a),
                "complete":self.achievements.completed.contains(&a.id),"title":a.title,"mount":a.mount})).collect::<Vec<_>>()})
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Class, Point, QuestProgress};
    fn hero() -> Character {
        Character::mercenary(Class::Warrior, 1, "Achiever")
    }
    fn quest(id: &str) -> QuestProgress {
        QuestProgress {
            id: id.into(),
            counts: vec![],
            claimed: true,
            completions: 1,
        }
    }
    #[test]
    fn achievements_catalog_has_positive_points_and_correct_atlas_and_rewards() {
        assert_eq!(catalog().len(), 102);
        assert_eq!(regions().len(), 23);
        assert_eq!(regions().iter().collect::<BTreeSet<_>>().len(), 23);
        let c = hero();
        let view = c.achievement_view();
        assert_eq!(view["maximum"], 2200);
        for a in catalog() {
            if a.metric == "fog" {
                assert!(regions().contains(&a.zone.unwrap()));
            }
            if a.id == "explorer" {
                assert_eq!(a.target, (regions().len() * FOG_GRID * FOG_GRID) as u32);
            }
        }
        assert_eq!(catalog().iter().filter(|a| !a.title.is_empty()).count(), 6);
        assert_eq!(catalog().iter().filter(|a| !a.mount.is_empty()).count(), 1);
    }
    #[test]
    fn achievements_reconcile_existing_facts_award_once_and_ignore_unknown_ids() {
        let mut c = hero();
        c.level = 99;
        c.kills = 1000;
        c.quests = (0..100).map(|i| quest(&format!("quest_{i}"))).collect();
        c.quests.push(quest("es_go_01"));
        c.quests.push(quest("quest_0"));
        let earned = c.sync_achievements();
        assert!(earned.contains(&"quests_100".into()));
        assert_eq!(c.achievements.quests.len(), 100);
        let points = c.achievement_points();
        assert_eq!(points, 350);
        assert!(c.sync_achievements().is_empty());
        assert_eq!(c.achievement_points(), points);
        c.achievements.completed.insert("fake_achievement".into());
        assert_eq!(c.achievement_points(), points);
        assert!(c.select_achievement_title("forge").is_err());
        c.select_achievement_title("quests_100").unwrap();
        assert_eq!(c.achievement_title(), "The Questkeeper");
        assert!(c.select_achievement_title("level_99").is_err());
        assert_eq!(c.achievement_title(), "The Questkeeper");
        c.select_achievement_title("").unwrap();
        assert_eq!(c.achievement_title(), "");
    }
    #[test]
    fn achievements_explorer_needs_every_atlas_cell_and_no_interiors() {
        let mut c = hero();
        c.explored = vec![u16::MAX; 47];
        let last = *regions().last().unwrap();
        c.explored[last] &= !1;
        c.sync_achievements();
        assert!(!c.achievements.completed.contains("explorer"));
        assert_eq!(
            c.achievement_view()["entries"]
                .as_array()
                .unwrap()
                .iter()
                .find(|r| r["id"] == "explorer")
                .unwrap()["progress"],
            206
        );
        c.explored[last] |= 1;
        for zone in 0..47 {
            if !regions().contains(&zone) {
                c.explored[zone] = 0;
            }
        }
        c.sync_achievements();
        c.select_achievement_title("explorer").unwrap();
        assert_eq!(c.achievement_title(), "The Explorer");
        assert_eq!(
            c.achievements
                .completed
                .iter()
                .filter(|id| id.starts_with("explore_"))
                .count(),
            23
        );
    }
    #[test]
    fn achievements_forge_requires_ten_distinct_bosses_and_unlocks_mount_once() {
        let mut c = hero();
        c.grant_mount("horse");
        for kind in &FORGE_BOSSES[..9] {
            c.achievements.bosses.insert((*kind).into());
        }
        c.sync_achievements();
        assert!(!c.owns_mount("gryphon"));
        c.achievements.bosses.insert(FORGE_BOSSES[0].into());
        c.sync_achievements();
        assert!(!c.owns_mount("gryphon"));
        c.achievements.bosses.insert(FORGE_BOSSES[9].into());
        assert!(c.sync_achievements().contains(&"forge".into()));
        assert!(c.owns_mount("gryphon"));
        assert_eq!(c.mount, "horse");
        c.select_achievement_title("forge").unwrap();
        assert_eq!(c.achievement_title(), "The Chainbreaker");
        assert!(c.sync_achievements().is_empty());
        assert_eq!(c.mounts, ["horse", "gryphon"]);
        let mut first = hero();
        first.achievements.bosses = c.achievements.bosses.clone();
        first.sync_achievements();
        assert_eq!(first.mount, "gryphon");
        assert!(first.mount_owned);
        assert_eq!(crate::model::mount_speed("gryphon"), Some(2.));
    }
    #[test]
    fn achievements_survive_rebirth_with_progress_and_reconcile_before_reset() {
        let mut c = hero();
        c.level = 99;
        c.explored = vec![511];
        c.quests = vec![quest("es_28")];
        c.rebirth(Point { x: 36., y: 60. }).unwrap();
        assert_eq!(c.level, 1);
        assert!(c.explored.is_empty());
        assert!(c.quests.is_empty());
        assert!(c.achievements.completed.contains("level_99"));
        assert!(c.achievements.completed.contains("empty_seat"));
        assert!(c.achievements.completed.contains("rebirth_1"));
        assert_eq!(c.achievements.explored[0], 511);
        c.explored = vec![0, 511];
        c.sync_achievements();
        assert_eq!(&c.achievements.explored[..2], [511, 511]);
        let saved = serde_json::to_value(&c).unwrap();
        let mut restored: Character = serde_json::from_value(saved.clone()).unwrap();
        let points = c.achievement_points();
        assert!(restored.sync_achievements().is_empty());
        assert_eq!(restored.achievement_points(), points);
        let mut old = saved;
        old.as_object_mut().unwrap().remove("achievements");
        let mut old: Character = serde_json::from_value(old).unwrap();
        assert_eq!(old.achievement_points(), 0);
        old.sync_achievements();
        assert!(old.achievements.completed.contains("rebirth_1"));
        assert!(
            !old.achievements.completed.contains("level_99"),
            "no unverifiable history invented"
        );
    }
    #[test]
    fn achievements_completed_mount_reward_does_not_duplicate_existing_mount() {
        let mut c = hero();
        c.grant_mount("gryphon");
        c.achievements.bosses = FORGE_BOSSES.iter().map(|s| (*s).into()).collect();
        c.sync_achievements();
        assert_eq!(c.mounts, ["gryphon"]);
        c.achievements.title = "unknown".into();
        c.sync_achievements();
        assert!(c.achievements.title.is_empty());
    }
    #[test]
    fn achievements_expansion_preserves_all_original_points_and_selected_rewards() {
        let mut c = hero();
        let original = [
            "level_10",
            "level_50",
            "level_99",
            "kills_1",
            "kills_100",
            "kills_1000",
            "quests_1",
            "quests_25",
            "quests_100",
            "regions_5",
            "regions_23",
            "explorer",
            "rebirth_1",
            "rebirth_5",
            "empty_seat",
            "first_boss",
            "forge",
            "mounts_3",
        ];
        c.achievements
            .completed
            .extend(original.iter().map(|s| (*s).to_owned()));
        for zone in regions() {
            c.achievements.completed.insert(format!("explore_{zone}"));
        }
        assert_eq!(c.achievements.completed.len(), 41);
        c.grant_mount("gryphon");
        c.select_achievement_title("explorer").unwrap();
        assert_eq!(c.achievement_points(), 685);
        assert!(c.sync_achievements().is_empty());
        assert_eq!(c.achievement_points(), 685);
        assert_eq!(c.achievement_view()["maximum"], 2200);
        assert_eq!(c.achievement_title(), "The Explorer");
        assert_eq!(c.mounts, ["gryphon"]);
    }
    #[test]
    fn achievements_expansion_named_boss_sets_need_each_distinct_member() {
        let mut c = hero();
        c.achievements
            .bosses
            .extend(["gatewarden", "choir", "colossus", "cf_kettil"].map(str::to_owned));
        c.sync_achievements();
        assert!(c.achievements.completed.contains("boss_cf_kettil"));
        assert!(!c.achievements.completed.contains("dungeon_hollowking"));
        let before = c.achievement_points();
        c.achievements.bosses.insert("gatewarden".into());
        assert!(c.sync_achievements().is_empty());
        assert_eq!(c.achievement_points(), before);
        c.achievements.bosses.insert("hollowking".into());
        c.sync_achievements();
        assert!(c.achievements.completed.contains("dungeon_hollowking"));
        assert!(!c.achievements.completed.contains("dungeon_master"));
        let all = catalog().iter().find(|a| a.id == "dungeon_master").unwrap();
        assert_eq!(all.members.len(), 65);
        c.achievements.bosses.extend(all.members.iter().cloned());
        c.sync_achievements();
        c.select_achievement_title("dungeon_master").unwrap();
        assert_eq!(c.achievement_title(), "The Delver");
        assert_eq!(catalog().iter().filter(|a| a.id.starts_with("dungeon_") && c.achievements.completed.contains(&a.id)).count(),21);
        let restored: Character =
            serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
        assert_eq!(restored.achievement_title(), "The Delver");
        assert_eq!(restored.achievement_points(), c.achievement_points());
    }
    #[test]
    fn achievements_expansion_chapters_and_mount_collection_unlock_their_own_titles() {
        let mut c = hero();
        c.quests.push(quest("es_20"));
        c.sync_achievements();
        assert!(c.achievements.completed.contains("story_20"));
        assert!(!c.achievements.completed.contains("story_15"));
        assert!(!c.achievements.completed.contains("empty_seat"));
        c.select_achievement_title("story_20").unwrap();
        assert_eq!(c.achievement_title(), "The Witness");
        for mount in ["horse", "raptor", "lizard", "sabertooth"] {
            c.grant_mount(mount);
        }
        c.sync_achievements();
        assert!(!c.achievements.completed.contains("mounts_5"));
        c.grant_mount("gryphon");
        c.sync_achievements();
        c.select_achievement_title("mounts_5").unwrap();
        assert_eq!(c.achievement_title(), "The Stablemaster");
        assert_eq!(c.mount, "horse");
    }
}
