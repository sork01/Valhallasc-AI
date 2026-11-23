//! Shared 1–600 progression for secondary professions.
use serde::{Deserialize, Serialize};

pub const MAX_SKILL: u16 = 600;
pub const SKILL_BAND: u16 = 30;
pub(crate) const EXPERT_ODDS_FLOOR_AT: u16 = 300;
const GEAR_LEVELS_PER_BAND: u16 = 5;

pub fn gear_skill_cap(level: u32) -> u16 {
    let band = level.max(1).div_ceil(u32::from(GEAR_LEVELS_PER_BAND));
    (band.min(u32::from(MAX_SKILL / SKILL_BAND)) as u16) * SKILL_BAND
}

pub fn training_gear_level(skill: u16) -> Option<u16> {
    (1..MAX_SKILL)
        .contains(&skill)
        .then(|| skill / SKILL_BAND * GEAR_LEVELS_PER_BAND + 1)
}

pub const fn band_cap(skill: u16) -> u16 {
    let cap = (skill / SKILL_BAND + 1) * SKILL_BAND;
    if cap > MAX_SKILL { MAX_SKILL } else { cap }
}

#[derive(Clone, Debug, Default, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Skill {
    #[serde(default)]
    pub skill: u16,
    #[serde(default, skip_serializing_if = "crate::profession::no_misses")]
    misses: u8,
}

fn no_misses(misses: &u8) -> bool {
    *misses == 0
}

impl Skill {
    /// Unlock at skill one, or give a one-time starting level to existing characters.
    pub fn initialize(&mut self, start: u16) {
        if self.skill == 0 {
            self.skill = start.clamp(1, MAX_SKILL);
        }
    }

    /// Only eligible actions affect the streak. Two eligible attempts without a point
    /// guarantee one on the next attempt, and better materials or fish improve the odds.
    pub fn try_gain(&mut self, quality: u8, cap: u16, roll: f64) -> bool {
        self.try_gain_with_floor(quality, cap, MAX_SKILL, EXPERT_ODDS_FLOOR_AT, roll)
    }

    pub(crate) fn train_batch(
        &mut self,
        attempts: u32,
        quality: u8,
        cap: u16,
        max_skill: u16,
        odds_floor_at: u16,
        mut roll: impl FnMut() -> f64,
    ) {
        for _ in 0..attempts {
            if self.skill == 0 || self.skill >= cap.min(max_skill) {
                break;
            }
            self.try_gain_with_floor(quality, cap, max_skill, odds_floor_at, roll());
        }
    }

    pub fn try_gain_to(&mut self, quality: u8, cap: u16, max_skill: u16, roll: f64) -> bool {
        self.try_gain_with_floor(quality, cap, max_skill, max_skill, roll)
    }

    fn try_gain_with_floor(
        &mut self,
        quality: u8,
        cap: u16,
        max_skill: u16,
        odds_floor_at: u16,
        roll: f64,
    ) -> bool {
        if !(1..cap.min(max_skill)).contains(&self.skill) {
            return false;
        }
        // Fishing and Enchanting reach the same base odds floor at 300 as before.
        let progress = f64::from(self.skill.min(odds_floor_at) - 1) / f64::from(odds_floor_at - 1);
        let chance = 0.9 - 0.3 * progress + 0.05 * f64::from(quality.min(3));
        if self.misses >= 2 || roll < chance.min(1.) {
            self.skill += 1;
            self.misses = 0;
            true
        } else {
            self.misses += 1;
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn profession_skill_eligible_actions_reach_600_even_with_the_worst_rolls() {
        let mut skill = Skill::default();
        assert!(!skill.try_gain(3, MAX_SKILL, 0.));
        skill.initialize(1);
        for level in 1..MAX_SKILL {
            assert_eq!(skill.skill, level);
            assert!(!skill.try_gain(0, band_cap(level), 0.999));
            assert!(!skill.try_gain(0, band_cap(level), 0.999));
            assert!(skill.try_gain(0, band_cap(level), 0.999));
        }
        assert_eq!(skill.skill, MAX_SKILL);
        assert!(!skill.try_gain(3, MAX_SKILL, 0.));
    }

    #[test]
    fn profession_skill_gear_caps_and_ineligible_actions_do_not_build_pity() {
        for (level, cap) in [
            (1, 30),
            (5, 30),
            (6, 60),
            (10, 60),
            (11, 90),
            (45, 270),
            (46, 300),
            (50, 300),
            (51, 330),
            (55, 330),
            (56, 360),
            (95, 570),
            (96, 600),
            (99, 600),
        ] {
            assert_eq!(gear_skill_cap(level), cap, "item level {level}");
        }
        assert_eq!(training_gear_level(30), Some(6));
        assert_eq!(training_gear_level(270), Some(46));
        assert_eq!(training_gear_level(300), Some(51));
        assert_eq!(training_gear_level(570), Some(96));
        assert_eq!(training_gear_level(600), None);
        let mut skill = Skill::default();
        skill.initialize(30);
        for _ in 0..3 {
            assert!(!skill.try_gain(0, 30, 0.999));
        }
        assert!(!skill.try_gain(0, 60, 0.999));
        assert!(!skill.try_gain(0, 60, 0.999));
        assert!(skill.try_gain(0, 60, 0.999));
    }

    #[test]
    fn profession_skill_expert_batches_keep_alchemy_and_smithing_odds() {
        let mut enchant = Skill::default();
        enchant.initialize(330);
        let mut alchemy = enchant.clone();
        enchant.train_batch(1, 0, 360, MAX_SKILL, EXPERT_ODDS_FLOOR_AT, || 0.7);
        alchemy.train_batch(1, 0, 360, MAX_SKILL, MAX_SKILL, || 0.7);
        assert_eq!(enchant.skill, 330);
        assert_eq!(alchemy.skill, 331);

        let mut smith = Skill::default();
        smith.initialize(crate::blacksmithing::MAX_SKILL);
        assert!(!smith.try_gain_to(0, 330, crate::blacksmithing::MAX_SKILL, 0.));
    }

    #[test]
    fn profession_skill_quality_improves_odds_and_misses_survive_reload() {
        let mut basic = Skill::default();
        basic.initialize(599);
        let mut better = basic.clone();
        assert!(!basic.try_gain(0, MAX_SKILL, 0.7));
        assert!(better.try_gain(3, MAX_SKILL, 0.7));
        assert!(!basic.try_gain(0, MAX_SKILL, 0.999));
        let mut restored: Skill =
            serde_json::from_value(serde_json::to_value(basic).unwrap()).unwrap();
        assert!(restored.try_gain(0, MAX_SKILL, 0.999));
        assert_eq!(restored.skill, 600);
    }
}
