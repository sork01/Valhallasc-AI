use crate::model::{Attributes, Class};
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;

#[derive(Clone, Copy, Debug, PartialEq, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum BuffKind {
    Damage,
    Shield,
    Haste,
    Dodge,
    Crit,
    /// Food: `amount` hit points per second while it lasts.
    Regen,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(tag = "effect", rename_all = "snake_case")]
pub enum Effect {
    /// Everything within reach in front of you (`dot` is the cosine of the widest angle).
    Cone {
        reach: f64,
        dot: f64,
        mult: f64,
    },
    /// Everything around you.
    Nova {
        radius: f64,
        mult: f64,
    },
    /// `count` projectiles; a spread of a full circle fires them in every direction.
    Volley {
        count: u32,
        spread: f64,
        mult: f64,
        pierce: bool,
        blast: f64,
        color: String,
        size: f64,
    },
    /// A fast move, dealing `mult` damage to what it passes through (none when zero).
    Dash {
        speed: f64,
        time: f64,
        mult: f64,
    },
    /// `hits` separate blows on the nearest enemy.
    Strike {
        hits: u32,
        mult: f64,
        range: f64,
    },
    /// Jumps between up to `targets` enemies.
    Chain {
        targets: u32,
        mult: f64,
        range: f64,
    },
    /// Lands on the target (or the ground ahead) after a short fall.
    Meteor {
        range: f64,
        radius: f64,
        mult: f64,
    },
    /// With a `range`, party members that close get the buff too.
    Buff {
        kind: BuffKind,
        amount: f64,
        time: f64,
        #[serde(default)]
        range: f64,
    },
    Heal {
        fraction: f64,
    },
    /// Heals up to `targets` wounded party members (you included) within `range`, the most hurt first,
    /// for `mult` times your attack power.
    Mend {
        mult: f64,
        range: f64,
        targets: u32,
    },
}

/// After any effect: every living party member (you included) within `range` is healed for `mult` times
/// your attack power.
#[derive(Clone, Debug, Deserialize)]
pub struct Pulse {
    pub mult: f64,
    pub range: f64,
}

#[derive(Clone, Debug, Deserialize)]
pub struct Skill {
    pub id: String,
    pub name: String,
    pub class: Class,
    pub level: u32,
    pub cooldown: f64,
    pub cost: f64,
    #[serde(default)]
    pub lifesteal: f64,
    #[serde(default)]
    pub pulse: Option<Pulse>,
    pub effect: Effect,
    #[serde(default)]
    pub ranks: Vec<Rank>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct Rank {
    pub level: u32,
    /// Multiplies the base damage, healing or buff strength. The highest earned
    /// rank wins; rank multipliers do not compound. Movement-only skills use 1.
    pub power: f64,
    /// Multiplies the base cooldown; ranks never change an ability's ID.
    pub cooldown: f64,
    #[serde(default)]
    pub capstone: bool,
}

impl Skill {
    pub fn rank_at(&self, level: u32) -> usize {
        1 + self.ranks.iter().take_while(|r| r.level <= level).count()
    }

    pub fn at_level(&self, level: u32) -> Self {
        let mut skill = self.clone();
        let rank_number = self.rank_at(level);
        if rank_number == 1 {
            return skill;
        }
        let rank = &self.ranks[rank_number - 2];
        skill.cooldown *= rank.cooldown;
        match &mut skill.effect {
            Effect::Cone { mult, .. }
            | Effect::Nova { mult, .. }
            | Effect::Volley { mult, .. }
            | Effect::Dash { mult, .. }
            | Effect::Strike { mult, .. }
            | Effect::Chain { mult, .. }
            | Effect::Meteor { mult, .. }
            | Effect::Mend { mult, .. } => *mult *= rank.power,
            Effect::Buff { amount, .. } => *amount = (*amount * rank.power).min(0.8),
            Effect::Heal { fraction } => *fraction = (*fraction * rank.power).min(1.),
        }
        if let Some(pulse) = &mut skill.pulse {
            pulse.mult *= rank.power;
        }
        skill
    }
}

pub static SKILLS: LazyLock<Vec<Skill>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/skills.txt")).expect("valid skill catalog")
});

#[derive(Clone, Debug, Deserialize)]
pub struct Passive {
    pub id: String,
    pub class: Class,
    pub level: u32,
    pub bonus: Attributes,
}

pub static PASSIVES: LazyLock<Vec<Passive>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/passives.txt")).expect("valid passive catalog")
});

/// Milestone effects are derived from class and saved level, so old characters
/// receive them on login without a character migration or client action.
pub fn passive_bonus(class: Class, level: u32) -> Attributes {
    let mut total = Attributes::default();
    for passive in PASSIVES
        .iter()
        .filter(|p| p.class == class && p.level <= level)
    {
        total.strength = total.strength.saturating_add(passive.bonus.strength);
        total.agility = total.agility.saturating_add(passive.bonus.agility);
        total.intellect = total.intellect.saturating_add(passive.bonus.intellect);
        total.stamina = total.stamina.saturating_add(passive.bonus.stamina);
        total.dexterity = total.dexterity.saturating_add(passive.bonus.dexterity);
        total.accuracy = total.accuracy.saturating_add(passive.bonus.accuracy);
    }
    total
}

pub fn find(class: Class, id: &str) -> Option<&'static Skill> {
    SKILLS.iter().find(|s| s.class == class && s.id == id)
}

/// Ids of the skills a class learns when its level rises from `from` to `to`.
pub fn unlocked(class: Class, from: u32, to: u32) -> Vec<&'static str> {
    let mut learned: Vec<_> = SKILLS
        .iter()
        .filter(|s| s.class == class)
        .flat_map(|s| {
            std::iter::once(s.level)
                .chain(s.ranks.iter().map(|r| r.level))
                .filter(move |level| *level > from && *level <= to)
                .map(|level| (level, s.id.as_str()))
        })
        .collect();
    learned.extend(
        PASSIVES
            .iter()
            .filter(|p| p.class == class && p.level > from && p.level <= to)
            .map(|p| (p.level, p.id.as_str())),
    );
    learned.sort_by_key(|(level, _)| *level);
    learned.into_iter().map(|(_, id)| id).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    const LAST_SKILL_LEVEL: u32 = 40;

    #[test]
    fn every_class_learns_a_new_skill_every_four_levels_through_forty() {
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let mut levels: Vec<_> = SKILLS
                .iter()
                .filter(|s| s.class == class)
                .map(|s| s.level)
                .collect();
            levels.sort_unstable();
            assert_eq!(
                levels,
                (1..=LAST_SKILL_LEVEL / 4)
                    .map(|n| n * 4)
                    .collect::<Vec<_>>()
            );
            assert!(unlocked(class, 1, 2).is_empty());
            assert!(unlocked(class, 2, 3).is_empty());
            assert_eq!(unlocked(class, 3, 4).len(), 1);
            assert_eq!(unlocked(class, 0, 99).len(), 59);
            for level in (4..=80).step_by(2) {
                let active: Vec<_> = unlocked(class, level - 1, level)
                    .into_iter()
                    .filter(|id| find(class, id).is_some())
                    .collect();
                assert_eq!(
                    active.len(),
                    if level == 42 { 2 } else { 1 },
                    "{class:?} level {level}"
                );
            }
            for level in (82..=98).step_by(2) {
                let active: Vec<_> = unlocked(class, level - 1, level)
                    .into_iter()
                    .filter(|id| find(class, id).is_some())
                    .collect();
                assert_eq!(active.len(), 1, "{class:?} level {level}");
            }
            assert_eq!(unlocked(class, 98, 99).len(), 1);
        }
    }

    #[test]
    fn skill_ids_are_unique_and_values_are_sane() {
        let mut ids: Vec<_> = SKILLS.iter().map(|s| s.id.as_str()).collect();
        ids.sort_unstable();
        ids.dedup();
        assert_eq!(ids.len(), SKILLS.len());
        for s in SKILLS.iter() {
            assert_eq!(s.ranks.len(), 4, "{}", s.id);
            let index = s.level / 4 - 1;
            assert_eq!(s.ranks[0].level, s.level + 2, "{}", s.id);
            assert_eq!(s.ranks[1].level, 42 + index * 2, "{}", s.id);
            assert_eq!(s.ranks[2].level, 62 + index * 2, "{}", s.id);
            assert_eq!(s.rank_at(s.ranks[2].level), 4, "{}", s.id);
            assert_eq!(
                s.ranks[3].level,
                if s.level == 40 { 99 } else { 82 + index * 2 },
                "{}",
                s.id
            );
            assert_eq!(s.ranks[3].capstone, s.level == 40, "{}", s.id);
            for rank in &s.ranks {
                assert!(rank.power >= 1. && rank.power <= 2., "{}", s.id);
                assert!(rank.cooldown > 0. && rank.cooldown <= 1., "{}", s.id);
            }
            assert_eq!(s.rank_at(s.level), 1, "{}", s.id);
            assert_eq!(s.rank_at(s.ranks[0].level), 2, "{}", s.id);
            assert_eq!(s.rank_at(s.ranks[1].level), 3, "{}", s.id);
            assert!(
                s.cost > 0. && s.cost.is_finite() && s.cost <= 100.,
                "{}",
                s.id
            );
            assert!(s.cooldown > 0. && s.cooldown.is_finite(), "{}", s.id);
            assert!((0. ..=1.).contains(&s.lifesteal), "{}", s.id);
            match &s.effect {
                Effect::Volley { count, .. } => assert!((1..=16).contains(count), "{}", s.id),
                Effect::Strike { hits, .. } => assert!((1..=12).contains(hits), "{}", s.id),
                Effect::Chain { targets, .. } => assert!((1..=8).contains(targets), "{}", s.id),
                Effect::Dash { speed, time, .. } => assert!(speed * time <= 8., "{}", s.id),
                Effect::Buff { amount, time, .. } => {
                    assert!(*amount > 0. && *amount <= 0.8 && *time > 0., "{}", s.id)
                }
                Effect::Heal { fraction } => assert!((0. ..=1.).contains(fraction), "{}", s.id),
                Effect::Mend {
                    mult,
                    range,
                    targets,
                } => assert!(
                    *mult > 0. && *range > 0. && (1..=5).contains(targets),
                    "{}",
                    s.id
                ),
                _ => {}
            }
        }
    }

    #[test]
    fn every_class_has_nine_distinct_authoritative_milestone_passives() {
        let mut ids = std::collections::HashSet::new();
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let class_passives: Vec<_> = PASSIVES.iter().filter(|p| p.class == class).collect();
            assert_eq!(class_passives.len(), 9);
            for (index, p) in class_passives.iter().enumerate() {
                assert_eq!(p.level, (index as u32 + 1) * 10);
                assert!(ids.insert(p.id.as_str()));
                let before = passive_bonus(class, p.level - 1);
                let after = passive_bonus(class, p.level);
                assert_ne!(before, after, "{} has no server effect", p.id);
                assert!(unlocked(class, p.level - 1, p.level).contains(&p.id.as_str()));
            }
        }
    }

    #[test]
    fn saved_level_earns_passive_stats_without_spending_trained_points() {
        let mut mage = crate::model::Character::mercenary(Class::Mage, 9, "Legacy Mage");
        let points = mage.stat_points();
        let before = mage.effective_attributes();
        mage.level = 10;
        assert_eq!(mage.effective_attributes().intellect, before.intellect + 4);
        assert_eq!(mage.stat_points(), points + 3);
        let serialized = serde_json::to_string(&mage).unwrap();
        let restored: crate::model::Character = serde_json::from_str(&serialized).unwrap();
        assert_eq!(restored.effective_attributes(), mage.effective_attributes());
    }

    #[test]
    fn final_even_level_rotation_scales_each_class_from_its_base_effect() {
        for (class, id) in [
            (Class::Warrior, "cleave"),
            (Class::Mage, "twinbolt"),
            (Class::Assassin, "throwingknives"),
            (Class::Priest, "mend"),
        ] {
            let skill = find(class, id).unwrap();
            let power = |level| match skill.at_level(level).effect {
                Effect::Cone { mult, .. }
                | Effect::Volley { mult, .. }
                | Effect::Mend { mult, .. } => mult,
                _ => panic!("unexpected effect for {id}"),
            };
            assert!((power(82) / power(4) - 1.8).abs() < 1e-9, "{id}");
            assert!((power(81) / power(4) - 1.6).abs() < 1e-9, "{id}");
        }
        let hunter = find(Class::Hunter, "powershot").unwrap();
        assert_eq!(hunter.rank_at(61), 3);
        assert_eq!(hunter.rank_at(62), 4);
        assert_eq!(hunter.rank_at(82), 5);
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let skill = SKILLS
                .iter()
                .find(|s| s.class == class && s.level == 40)
                .unwrap();
            assert_eq!(skill.rank_at(98), 4);
            assert_eq!(skill.rank_at(99), 5);
            assert!(skill.ranks[3].capstone);
        }
    }

    #[test]
    fn ranks_change_authoritative_effects_without_changing_skill_ids() {
        let bolt = find(Class::Mage, "twinbolt").unwrap();
        let before = bolt.at_level(5);
        let after = bolt.at_level(6);
        assert_eq!(after.id, before.id);
        assert_eq!(before.cooldown, after.cooldown);
        match (before.effect, after.effect) {
            (Effect::Volley { mult: a, .. }, Effect::Volley { mult: b, .. }) => {
                assert!((b - a * 1.2).abs() < 0.0001);
            }
            _ => panic!("Twin Bolt must stay a volley"),
        }
        let blink = find(Class::Mage, "blink").unwrap();
        assert_eq!(blink.at_level(21).cooldown, blink.cooldown);
        assert!((blink.at_level(22).cooldown - blink.cooldown * 0.85).abs() < 0.0001);
        assert_eq!(blink.at_level(49).cooldown, blink.cooldown * 0.85);
        assert!((blink.at_level(50).cooldown - blink.cooldown * 0.7).abs() < 0.0001);
        assert_eq!(blink.at_level(69).cooldown, blink.cooldown * 0.7);
        assert!((blink.at_level(70).cooldown - blink.cooldown * 0.55).abs() < 0.0001);
        let ward = find(Class::Mage, "arcaneward").unwrap();
        match ward.at_level(10).effect {
            Effect::Buff { amount, .. } => assert!((amount - 0.48).abs() < 0.0001),
            _ => panic!("Arcane Ward must stay a buff"),
        }
        match ward.at_level(44).effect {
            Effect::Buff { amount, .. } => assert!((amount - 0.56).abs() < 0.0001),
            _ => panic!("Arcane Ward must stay a buff"),
        }
        match ward.at_level(64).effect {
            Effect::Buff { amount, .. } => assert!((amount - 0.64).abs() < 0.0001),
            _ => panic!("Arcane Ward must stay a buff"),
        }
        let mend = find(Class::Priest, "mend").unwrap();
        match (mend.at_level(61).effect, mend.at_level(62).effect) {
            (Effect::Mend { mult: before, .. }, Effect::Mend { mult: after, .. }) => {
                assert!((after - before * (1.6 / 1.4)).abs() < 0.0001);
            }
            _ => panic!("Mend must stay a party heal"),
        }
    }
}
