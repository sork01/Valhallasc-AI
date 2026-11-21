//! Shared 1–300 progression for secondary professions.
use serde::{Deserialize, Serialize};

pub const MAX_SKILL: u16 = 300;

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

    /// Basic actions stay useful through 300. Better materials or fish improve the odds,
    /// and two eligible attempts without a point guarantee one on the next attempt.
    pub fn try_gain(&mut self, quality: u8, roll: f64) -> bool {
        if !(1..MAX_SKILL).contains(&self.skill) {
            return false;
        }
        let chance = 0.9 - 0.3 * f64::from(self.skill - 1) / f64::from(MAX_SKILL - 1)
            + 0.05 * f64::from(quality.min(3));
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
    fn profession_skill_basic_actions_reach_300_even_with_the_worst_rolls() {
        let mut skill = Skill::default();
        assert!(!skill.try_gain(3, 0.));
        skill.initialize(1);
        for level in 1..MAX_SKILL {
            assert_eq!(skill.skill, level);
            assert!(!skill.try_gain(0, 0.999));
            assert!(!skill.try_gain(0, 0.999));
            assert!(skill.try_gain(0, 0.999));
        }
        assert_eq!(skill.skill, MAX_SKILL);
        assert!(!skill.try_gain(3, 0.));
    }

    #[test]
    fn profession_skill_quality_improves_odds_and_misses_survive_reload() {
        let mut basic = Skill::default();
        basic.initialize(299);
        let mut better = basic.clone();
        assert!(!basic.try_gain(0, 0.7));
        assert!(better.try_gain(3, 0.7));
        assert!(!basic.try_gain(0, 0.999));
        let mut restored: Skill =
            serde_json::from_value(serde_json::to_value(basic).unwrap()).unwrap();
        assert!(restored.try_gain(0, 0.999));
        assert_eq!(restored.skill, 300);
    }
}
