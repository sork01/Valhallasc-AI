//! Rebirth, the character side (docs/rebirth.md, REBIRTH-SERVER): the tier ladder, the counts that every perk is derived
//! from, and the atomic reset. The refusals that need the world (combat, a dungeon copy, a duel, a trade, an escort)
//! live in `world/rebirth.rs`; the perks themselves arrive with REBIRTH-PERKS.
use crate::items::{equipment, item};
use crate::model::{Character, Class, Look, Point};

/// The lowest level that may rebirth.
pub const REBIRTH_MIN_LEVEL: u32 = 50;
/// Levels per tier: 50 is tier 1, 60 tier 2, and so on.
pub const REBIRTH_LEVEL_STEP: u32 = 10;
/// The highest tier. Levels 91 to 99 give nothing more than 90.
pub const REBIRTH_MAX_TIER: u32 = 5;

/// The tier a rebirth at `level` would have: `(level - 40) / 10`, none below 50, at most 5.
pub fn rebirth_tier(level: u32) -> Option<u32> {
    (level >= REBIRTH_MIN_LEVEL)
        .then(|| ((level - REBIRTH_MIN_LEVEL) / REBIRTH_LEVEL_STEP + 1).min(REBIRTH_MAX_TIER))
}

/// The armor and weapon variants a new character of this class starts in.
fn starter_variants(class: Class) -> (String, String) {
    let d = Look::default();
    match class {
        Class::Warrior => (d.warrior_armor, d.warrior_weapon),
        Class::Mage => (d.mage_armor, d.mage_weapon),
        Class::Assassin => (d.assassin_armor, d.assassin_weapon),
        Class::Priest => (d.priest_armor, d.priest_weapon),
        Class::Hunter => (d.hunter_armor, d.hunter_weapon),
    }
}

impl Character {
    /// Rebirths done so far, at any tier.
    pub fn rebirth_count(&self) -> u32 {
        self.rebirth_tiers
            .iter()
            .fold(0, |sum, n| sum.saturating_add(*n))
    }
    /// The highest tier ever reached, 0 for a character who never reborn.
    pub fn rebirth_highest_tier(&self) -> u32 {
        self.rebirth_tiers
            .iter()
            .rposition(|n| *n > 0)
            .map_or(0, |at| at as u32 + 1)
    }
    /// The tier a rebirth would have right now.
    pub fn rebirth_tier_now(&self) -> Option<u32> {
        rebirth_tier(self.level)
    }
    /// Why this character alone cannot rebirth now; the world adds the refusals that need other state.
    pub fn rebirth_blocker(&self) -> Option<String> {
        if self.rebirth_tier_now().is_none() {
            return Some(format!("You need level {REBIRTH_MIN_LEVEL} to be reborn."));
        }
        if self.hp <= 0. {
            return Some("You cannot be reborn while defeated.".into());
        }
        if self.mounted {
            return Some("Dismount before you are reborn.".into());
        }
        if self.spark_travel.is_some() {
            return Some("You cannot be reborn during Spark Travel.".into());
        }
        None
    }
    /// The next state with every piece that needs more than level 1 taken off (into the bags), or the number of bag
    /// cells that must be freed first.
    fn rebirth_unequipped(&self) -> Result<Character, usize> {
        let mut next = self.clone();
        let class = next.look.class;
        let too_high = |id: &str| item(id).is_some_and(|i| i.required_level > 1);
        next.equipment.retain(|_, id| !too_high(id));
        let (armor, weapon) = starter_variants(class);
        for (kind, worn, starter) in [
            ("armor", next.gear().0.to_owned(), armor),
            ("weapon", next.gear().1.to_owned(), weapon),
        ] {
            if !equipment(class, kind, &worn).is_some_and(|i| i.required_level > 1) {
                continue;
            }
            let owned = equipment(class, kind, &starter).is_some_and(|i| next.quantity(&i.id) > 0);
            let variant = if owned { starter } else { "none".into() };
            let (a, w) = next.gear();
            let (a, w) = if kind == "armor" {
                (variant, w.to_owned())
            } else {
                (a.to_owned(), variant)
            };
            // The variants come from the catalog or are "none", so validation cannot fail.
            let _ = next.look.equip(&a, &w);
        }
        next.sync_look();
        let over = next.bag_used().saturating_sub(next.bag_capacity());
        if over > 0 { Err(over) } else { Ok(next) }
    }
    /// How many worn pieces a rebirth takes off, and how many bag cells are missing for them (0 when it fits).
    pub fn rebirth_gear_cost(&self) -> (usize, usize) {
        let off = self
            .worn_items()
            .iter()
            .filter(|i| i.required_level > 1)
            .count();
        (off, self.rebirth_unequipped().err().unwrap_or(0))
    }
    /// Rebirth at the current level, all or nothing: the reset list of docs/rebirth.md, the count of the tier reached
    /// and a return to `spawn` in the starting zone. Returns the tier.
    pub fn rebirth(&mut self, spawn: Point) -> Result<u32, String> {
        if let Some(text) = self.rebirth_blocker() {
            return Err(text);
        }
        let tier = self.rebirth_tier_now().unwrap_or(1);
        let mut next = self.rebirth_unequipped().map_err(|cells| {
            format!("Free {cells} bag cells first: your high-level gear goes into the bags.")
        })?;
        next.rebirth_tiers[tier as usize - 1] =
            next.rebirth_tiers[tier as usize - 1].saturating_add(1);
        next.sync_achievements();
        next.level = 1;
        next.xp = 0;
        next.attributes = Default::default();
        next.stat_budget_floor = 0;
        next.stat_resets = 0;
        next.quests.clear();
        next.explored.clear();
        next.mounted = false;
        next.zone = 0;
        next.x = spawn.x;
        next.y = spawn.y;
        next.hp = next.max_hp();
        next.reset_resource();
        *self = next;
        Ok(tier)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn hero(level: u32) -> Character {
        let mut c = Character::mercenary(Class::Warrior, level, "Reborn");
        c.hp = c.max_hp();
        c
    }

    #[test]
    fn the_ladder_gives_tier_one_at_fifty_to_tier_five_at_ninety_and_stays_there() {
        assert_eq!(rebirth_tier(49), None);
        for (level, tier) in [
            (50, 1),
            (59, 1),
            (60, 2),
            (70, 3),
            (80, 4),
            (90, 5),
            (91, 5),
            (99, 5),
        ] {
            assert_eq!(rebirth_tier(level), Some(tier), "level {level}");
        }
    }

    #[test]
    fn a_rebirth_counts_its_tier_and_resets_what_the_rules_say() {
        let mut c = hero(70);
        c.xp = 500;
        c.attributes.strength = 30;
        c.stat_budget_floor = 90;
        c.stat_resets = 3;
        c.quests.push(crate::model::QuestProgress {
            id: "q".into(),
            counts: vec![1],
            claimed: true,
            completions: 2,
        });
        c.explored = vec![7, 9];
        c.zone = 5;
        c.gold = 1234;
        c.friends = vec!["friend".into()];
        c.party_points = 77;
        c.kills = 4000;
        c.grant_mount("horse");
        c.travel_stops = vec!["Skaldholm".into()];
        c.add_item("slime_gel", 4);
        c.bank_deposit("slime_gel", 3, None).unwrap();
        c.gold = 1434;
        c.bank_gold(true, 200).unwrap();
        c.bank.expansions = 2;
        let bank = c.bank.clone();
        let bags = c.bags.clone();
        let spawn = Point { x: 12., y: 13. };
        assert_eq!(c.rebirth(spawn).unwrap(), 3);
        assert_eq!(c.rebirth_tiers, [0, 0, 1, 0, 0]);
        assert_eq!((c.rebirth_count(), c.rebirth_highest_tier()), (1, 3));
        assert_eq!((c.level, c.xp), (1, 0));
        assert_eq!(c.trained_points(), 0);
        assert_eq!(
            (c.stat_budget_floor, c.stat_resets, c.stat_points()),
            (0, 0, 0)
        );
        assert!(c.quests.is_empty() && c.explored.is_empty());
        assert_eq!((c.zone, c.x, c.y), (0, 12., 13.));
        assert_eq!(c.hp, c.max_hp());
        // Kept.
        assert_eq!((c.gold, c.kills, c.party_points), (1234, 4000, 77));
        assert_eq!(c.friends, vec!["friend".to_string()]);
        assert_eq!(c.mounts, vec!["horse".to_string()]);
        assert_eq!(c.travel_stops, vec!["Skaldholm".to_string()]);
        assert_eq!(c.bags, bags);
        assert_eq!(c.bank, bank, "the bank is kept, gold and expansions too");
    }

    #[test]
    fn high_level_gear_comes_off_into_the_bags_and_a_full_bag_refuses() {
        let mut c = hero(60);
        let piece = crate::items::ITEMS
            .iter()
            .find(|i| {
                i.kind == "headgear"
                    && i.required_level >= 40
                    && i.class.is_none_or(|k| k == Class::Warrior)
            })
            .expect("a high headgear");
        c.add_item(&piece.id, 1);
        c.equipment.insert("headgear".into(), piece.id.clone());
        c.sync_look();
        let worn_high = c
            .worn_items()
            .iter()
            .filter(|i| i.required_level > 1)
            .count();
        assert!(worn_high >= 1);
        assert_eq!(c.rebirth_gear_cost(), (worn_high, 0));
        c.rebirth(Point::default()).unwrap();
        assert!(!c.equipment.contains_key("headgear"), "worn above level 1");
        assert_eq!(c.quantity(&piece.id), 1, "still owned");
        assert_eq!(c.look.head, "none");

        // No room: fill every bag cell with different materials first.
        let mut full = hero(60);
        full.equipment.insert("headgear".into(), piece.id.clone());
        full.add_item(&piece.id, 1);
        let fillers: Vec<_> = crate::items::ITEMS
            .iter()
            .filter(|i| i.kind == "material")
            .map(|i| i.id.clone())
            .collect();
        for id in fillers {
            if full.bag_used() >= full.bag_capacity() {
                break;
            }
            full.add_item(&id, 1);
        }
        assert!(full.bag_used() >= full.bag_capacity(), "the bag is full");
        let before = full.clone();
        let err = full.rebirth(Point::default()).unwrap_err();
        assert!(err.contains("bag cells"), "{err}");
        assert_eq!(full.level, before.level, "a refusal changes nothing");
        assert_eq!(full.rebirth_tiers, [0; 5]);
    }

    #[test]
    fn refusals_change_nothing() {
        for (setup, text) in [
            (0u8, "level 50"),
            (1, "defeated"),
            (2, "Dismount"),
            (3, "Spark Travel"),
        ] {
            let mut c = hero(if setup == 0 { 49 } else { 55 });
            match setup {
                1 => c.hp = 0.,
                2 => c.mounted = true,
                3 => {
                    c.spark_travel = Some(crate::model::SparkTravel {
                        destination: "x".into(),
                        stops: vec![],
                        points: vec![],
                        next: 0,
                    })
                }
                _ => {}
            }
            let before = (c.level, c.xp, c.rebirth_tiers);
            let err = c.rebirth(Point::default()).unwrap_err();
            assert!(err.contains(text), "{err}");
            assert_eq!((c.level, c.xp, c.rebirth_tiers), before);
        }
    }

    #[test]
    fn a_second_rebirth_needs_the_levels_again_and_stacks_the_counts() {
        let mut c = hero(90);
        assert_eq!(c.rebirth(Point::default()).unwrap(), 5);
        assert!(
            c.rebirth(Point::default()).is_err(),
            "level 1 cannot replay it"
        );
        assert_eq!(c.rebirth_tiers, [0, 0, 0, 0, 1]);
        c.level = 50;
        assert_eq!(c.rebirth(Point::default()).unwrap(), 1);
        assert_eq!(c.rebirth_tiers, [1, 0, 0, 0, 1]);
        assert_eq!((c.rebirth_count(), c.rebirth_highest_tier()), (2, 5));
    }

    #[test]
    fn a_legacy_save_loads_as_never_reborn_and_the_counts_survive_a_round_trip() {
        let c = hero(55);
        let mut v = serde_json::to_value(&c).unwrap();
        v.as_object_mut().unwrap().remove("rebirthTiers");
        let old: Character = serde_json::from_value(v).unwrap();
        assert_eq!(
            (
                old.rebirth_tiers,
                old.rebirth_count(),
                old.rebirth_highest_tier()
            ),
            ([0; 5], 0, 0)
        );
        let mut again = old;
        again.rebirth(Point::default()).unwrap();
        let saved: Character =
            serde_json::from_str(&serde_json::to_string(&again).unwrap()).unwrap();
        assert_eq!(saved.rebirth_tiers, [1, 0, 0, 0, 0]);
        assert_eq!(saved.level, 1);
    }
}
