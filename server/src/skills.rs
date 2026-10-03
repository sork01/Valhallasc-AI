use crate::model::Class;
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
}

pub static SKILLS: LazyLock<Vec<Skill>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/skills.txt")).expect("valid skill catalog")
});

pub fn find(class: Class, id: &str) -> Option<&'static Skill> {
    SKILLS.iter().find(|s| s.class == class && s.id == id)
}

/// Ids of the skills a class learns when its level rises from `from` to `to`.
pub fn unlocked(class: Class, from: u32, to: u32) -> Vec<&'static str> {
    SKILLS
        .iter()
        .filter(|s| s.class == class && s.level > from && s.level <= to)
        .map(|s| s.id.as_str())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A class learns one skill per even level up to this level.
    const LAST_SKILL_LEVEL: u32 = 20;

    #[test]
    fn every_class_learns_one_skill_at_each_even_level_up_to_twenty() {
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
                (1..=LAST_SKILL_LEVEL / 2)
                    .map(|n| n * 2)
                    .collect::<Vec<_>>()
            );
            assert_eq!(unlocked(class, 1, 2).len(), 1);
            assert!(unlocked(class, 2, 3).is_empty());
            assert_eq!(unlocked(class, 0, 99).len(), 10);
        }
    }

    #[test]
    fn skill_ids_are_unique_and_values_are_sane() {
        let mut ids: Vec<_> = SKILLS.iter().map(|s| s.id.as_str()).collect();
        ids.sort_unstable();
        ids.dedup();
        assert_eq!(ids.len(), SKILLS.len());
        for s in SKILLS.iter() {
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
}
