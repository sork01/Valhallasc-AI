use super::GearInstance;
use crate::model::Attributes;
use serde::Deserialize;
use std::sync::LazyLock;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Rules {
    drop: DropRule,
    pieces: Vec<Piece>,
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct DropRule {
    chance_per_kill: f64,
    level_window: u32,
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Piece {
    id: String,
    required_level: u32,
    rolls: Ranges,
}
#[derive(Deserialize)]
struct Ranges {
    attack: [u32; 2],
    defense: [u32; 2],
    stamina: [u32; 2],
    accuracy: [u32; 2],
    dexterity: [u32; 2],
}
static RULES: LazyLock<Rules> = LazyLock::new(|| {
    let rules: Rules = serde_json::from_str(include_str!("../../../world/orange_rules.txt"))
        .expect("valid orange rules");
    assert_eq!(rules.pieces.len(), 50);
    rules
});

fn uniform(range: [u32; 2], random: f64) -> u32 {
    assert!(range[0] <= range[1]);
    range[0] + ((random.clamp(0., 1. - f64::EPSILON) * f64::from(range[1] - range[0] + 1)) as u32)
}

/// Run once after every credited mob death, for the hero at `level`. Each successful copy gets five independent
/// rolls; the returned values travel with the drop through party voting and are never rolled at pickup.
#[cfg(test)]
pub fn roll_orange(level: u32, random: impl FnMut() -> f64) -> Option<GearInstance> {
    roll_orange_boosted(1, level, random)
}

/// The pieces a hero at `level` can find: none is more than `level_window` levels above them.
fn pool(level: u32) -> impl Iterator<Item = &'static Piece> {
    let reach = level.saturating_add(RULES.drop.level_window);
    RULES
        .pieces
        .iter()
        .filter(move |piece| piece.required_level <= reach)
}

/// `roll_orange` at a drop multiplier (docs/rebirth.md): the first draw, the one that decides whether anything drops,
/// is compared with `multiplier` times the chance. At 1 it is the plain roll.
pub fn roll_orange_boosted(
    multiplier: u32,
    level: u32,
    mut random: impl FnMut() -> f64,
) -> Option<GearInstance> {
    let mut first = true;
    let mut random = move || {
        let value = random();
        if std::mem::take(&mut first) {
            value / f64::from(multiplier.max(1))
        } else {
            value
        }
    };
    if random() >= RULES.drop.chance_per_kill {
        return None;
    }
    let eligible = pool(level).count();
    // The pick is drawn even when nothing qualifies, so the random sequence does not depend on the level.
    let pick = random().clamp(0., 1. - f64::EPSILON);
    let piece = pool(level).nth((pick * eligible as f64) as usize)?;
    Some(GearInstance {
        id: 0,
        item: piece.id.clone(),
        rarity: "legendary".into(),
        attack: f64::from(uniform(piece.rolls.attack, random())),
        defense: f64::from(uniform(piece.rolls.defense, random())),
        bonus_stats: Attributes {
            stamina: uniform(piece.rolls.stamina, random()),
            accuracy: uniform(piece.rolls.accuracy, random()),
            dexterity: uniform(piece.rolls.dexterity, random()),
            ..Attributes::default()
        },
        rolled_stats: Attributes::default(),
        rank: 0,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Character, Class};
    use std::collections::BTreeMap;

    const TOP: u32 = 99;

    /// The ladder: ten families of five slots, one level per family.
    const FAMILY_LEVELS: [u32; 10] = [10, 20, 30, 40, 50, 60, 70, 80, 90, 99];

    #[test]
    fn independent_probability_uniform_piece_and_inclusive_stats() {
        assert!(roll_orange(TOP, || 0.001).is_none());
        for n in 0..50 {
            let mut values = [0., (n as f64 + 0.5) / 50., 0., 0., 0., 0., 0.].into_iter();
            let copy = roll_orange(TOP, || values.next().unwrap()).unwrap();
            assert_eq!(copy.item, format!("orange_{:02}", n + 1));
            assert_eq!(copy.rarity, "legendary");
            assert!(copy.attack > 0. && copy.defense > 0.);
        }
        let mut values = [
            0.,
            0.,
            1. - f64::EPSILON,
            1. - f64::EPSILON,
            1. - f64::EPSILON,
            1. - f64::EPSILON,
            1. - f64::EPSILON,
        ]
        .into_iter();
        let piece = &RULES.pieces[0];
        let high = roll_orange(TOP, || values.next().unwrap()).unwrap();
        assert_eq!(
            (
                high.attack,
                high.defense,
                high.bonus_stats.stamina,
                high.bonus_stats.accuracy,
                high.bonus_stats.dexterity
            ),
            (
                f64::from(piece.rolls.attack[1]),
                f64::from(piece.rolls.defense[1]),
                piece.rolls.stamina[1],
                piece.rolls.accuracy[1],
                piece.rolls.dexterity[1]
            )
        );
    }

    #[test]
    fn a_piece_is_found_only_by_a_hero_within_five_levels_of_it() {
        // Nobody below level 5 finds anything: the lowest piece is level 10.
        for level in 1..5 {
            assert!(roll_orange(level, || 0.0).is_none(), "level {level}");
        }
        // Sweep the pick across the eligible pool, so every eligible piece comes out exactly once.
        let found = |level: u32| -> Vec<String> {
            let size = pool(level).count();
            (0..size)
                .map(|n| {
                    let mut values = [0., (n as f64 + 0.5) / size as f64].into_iter();
                    roll_orange(level, || values.next().unwrap_or(0.))
                        .unwrap()
                        .item
                })
                .collect()
        };
        for level in [5, 6, 14, 15, 19, 24, 50, 60, 94, 98, 99, 120] {
            let items = found(level);
            let reach = level + 5;
            let expected = RULES
                .pieces
                .iter()
                .filter(|p| p.required_level <= reach)
                .count();
            assert_eq!(items.len(), expected, "level {level}");
            for id in &items {
                let piece = RULES.pieces.iter().find(|p| &p.id == id).unwrap();
                assert!(piece.required_level <= level + 5, "{id} at {level}");
            }
        }
        // Boundaries: level 5 reaches the level 10 family, level 15 the level 20 family, level 94 the top one.
        assert_eq!(pool(5).count(), 5);
        assert_eq!(pool(14).count(), 5);
        assert_eq!(pool(15).count(), 10);
        assert_eq!(pool(93).count(), 45);
        assert_eq!(pool(94).count(), 50);
        // The random sequence is the same at every level (a pick is drawn even with nothing to pick).
        let mut draws = 0;
        assert!(
            roll_orange(1, || {
                draws += 1;
                0.0
            })
            .is_none()
        );
        assert_eq!(draws, 2);
    }

    #[test]
    fn the_boost_filters_by_level_in_the_same_way() {
        // At x5 the chance is five times as large, but a level 1 hero still finds nothing.
        assert!(roll_orange_boosted(5, 1, || 0.004).is_none());
        assert!(roll_orange_boosted(5, 5, || 0.004).is_some());
    }

    #[test]
    fn every_piece_has_a_level_and_stats_between_purple_and_the_next_family() {
        let levels: Vec<u32> = RULES.pieces.iter().map(|p| p.required_level).collect();
        for (n, piece) in RULES.pieces.iter().enumerate() {
            assert_eq!(piece.required_level, FAMILY_LEVELS[n / 5], "{}", piece.id);
            let item = super::super::item(&piece.id).unwrap();
            assert_eq!(item.required_level, piece.required_level, "{}", piece.id);
            let (stat, base) = match item.kind.as_str() {
                "weapon" => ("attack", 4.0),
                "armor" => ("defense", 3.0),
                _ => ("defense", 1.0),
            };
            // The purple piece of this level: green budget 1.25, two tiers of 17.5%.
            let total =
                base * (0.16 * f64::from(piece.required_level) + 0.8) * 1.25 * 1.175 * 1.175;
            let (attack, defense) = if stat == "attack" {
                (total * 0.8, total * 0.2)
            } else {
                (total * 0.2, total * 0.8)
            };
            assert!(
                f64::from(piece.rolls.attack[0]) >= attack.floor()
                    && f64::from(piece.rolls.defense[0]) >= defense.floor(),
                "{} does not beat the purple of its level",
                piece.id
            );
            // The caps of hit and dodge.
            assert!(
                piece.rolls.accuracy[1] <= 20 && piece.rolls.dexterity[1] <= 70,
                "{}",
                piece.id
            );
            for r in [
                piece.rolls.attack,
                piece.rolls.defense,
                piece.rolls.stamina,
                piece.rolls.accuracy,
                piece.rolls.dexterity,
            ] {
                assert!(r[0] < r[1], "{} has an empty roll range", piece.id);
            }
        }
        assert!(levels.windows(2).all(|w| w[0] <= w[1]));
        // The same slot grows with the level: the best roll of one family is under the next family's best.
        for slot in 0..5 {
            let run: Vec<&Piece> = RULES.pieces.iter().skip(slot).step_by(5).collect();
            for pair in run.windows(2) {
                let (low, high) = (&pair[0].rolls, &pair[1].rolls);
                assert!(low.attack[1] <= high.attack[1] && low.defense[1] <= high.defense[1]);
                assert!(low.stamina[1] < high.stamina[1], "{}", pair[0].id);
            }
        }
    }

    #[test]
    fn a_piece_equips_on_every_class_from_its_own_level_only() {
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            for piece in &RULES.pieces {
                let item = super::super::item(&piece.id).unwrap();
                assert_eq!(item.required_level, piece.required_level);
                assert!(item.class.is_none());
                let slot = match item.kind.as_str() {
                    "armor" => "chest",
                    "weapon" => "hands",
                    "headgear" => "headgear",
                    "shoulders" => "shoulders",
                    "gloves" => "gloves",
                    kind => panic!("unexpected orange kind: {kind}"),
                };
                let wear = BTreeMap::from([(slot.into(), piece.id.clone())]);
                let mut c = Character::mercenary(class, piece.required_level - 1, "Orange Test");
                c.add_item(&piece.id, 1);
                assert!(
                    c.equip_slots(&wear).is_err(),
                    "{} {class:?} one level short",
                    piece.id
                );
                let mut c = Character::mercenary(class, piece.required_level, "Orange Test");
                c.add_item(&piece.id, 1);
                c.equip_slots(&wear).unwrap();
                assert_eq!(c.equipped_count(item), 1, "{} {class:?}", piece.id);
            }
        }
    }
}
