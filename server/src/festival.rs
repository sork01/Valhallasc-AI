//! Permanent expiry timestamp for the shared, non-stacking seasonal buff.
use crate::model::Character;
use serde::{Deserialize, Serialize};
pub const DURATION: u64 = 7200;
#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Spirit {
    #[serde(default)]
    pub until: u64,
    #[serde(default)]
    pub season: String,
}
impl Spirit {
    pub fn left(&self, now: u64) -> u64 {
        self.until.saturating_sub(now).min(DURATION)
    }
    pub fn grant(&mut self, now: u64, season: &str) {
        self.until = now.saturating_add(DURATION);
        self.season = season.into();
    }
}
pub fn now() -> u64 {
    crate::store::unix_now().max(0) as u64
}
impl Character {
    pub fn festival_attack_at(&self, now: u64) -> f64 {
        if self.festival_spirit.left(now) > 0 {
            1.1
        } else {
            1.
        }
    }
    pub fn festival_xp_at(&self, now: u64) -> u32 {
        if self.festival_spirit.left(now) > 0 {
            50
        } else {
            0
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Class;

    #[test]
    fn festival_spirit_exact_expiry_refresh_and_offline_save_compatibility() {
        let mut c = Character::mercenary(Class::Warrior, 1, "Spirit");
        let old = serde_json::to_value(&c).unwrap();
        c.festival_spirit.grant(1000, "solstice");
        assert_eq!(c.festival_spirit.left(1000), 7200);
        assert_eq!(c.festival_spirit.left(8199), 1);
        assert_eq!(c.festival_spirit.left(8200), 0);
        c.festival_spirit.grant(2000, "christmas");
        assert_eq!(c.festival_spirit.until, 9200);
        assert_eq!(c.festival_spirit.left(2000), 7200);
        let loaded: Character = serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
        assert_eq!(loaded.festival_spirit.left(9100), 100);
        let mut legacy = old;
        legacy.as_object_mut().unwrap().remove("festivalSpirit");
        let legacy: Character = serde_json::from_value(legacy).unwrap();
        assert_eq!(legacy.festival_spirit.until, 0);
        assert_eq!(c.festival_attack_at(9199), 1.1);
        assert_eq!(c.festival_attack_at(9200), 1.);
        assert_eq!(c.festival_xp_at(9200), 0);
    }
    #[test]
    fn festival_spirit_exact_attack_and_additive_xp_for_all_classes() {
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let mut c = Character::mercenary(class, 20, "Stats");
            let before = c.stats();
            let normal = c.boosted_xp(100);
            c.festival_spirit.grant(now(), "easter");
            assert!((c.stats().0 - before.0 * 1.1).abs() < 1e-7);
            assert_eq!(c.stats().1, before.1);
            assert_eq!(c.boosted_xp(100), normal + 50);
            assert_eq!(c.boosted_xp(0), 0);
            assert_eq!(c.boosted_xp(u32::MAX), u32::MAX);
            c.rested.join(1000);
            c.rested.join(1000 + 40 * 3600);
            assert_eq!(c.reward_xp(100).0, normal + 250);
        }
    }
    #[test]
    fn festival_spirit_survives_death_rebirth_and_season_expiry_without_stacking() {
        let mut c = Character::mercenary(Class::Warrior, 50, "Keep");
        c.festival_spirit.grant(now(), "valentine");
        let expiry = c.festival_spirit.until;
        c.hp = 0.;
        assert!(c.festival_spirit.left(now()) > 0);
        c.hp = c.max_hp();
        c.rebirth(crate::model::Point { x: 36., y: 83. }).unwrap();
        crate::seasonal::sync_character(&mut c, &[]);
        assert_eq!(c.festival_spirit.until, expiry);
        assert!(c.festival_spirit.left(now()) > 0);
    }
}
