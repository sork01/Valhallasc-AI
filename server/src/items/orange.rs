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
}
#[derive(Deserialize)]
struct Piece {
    id: String,
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

/// Run once after every credited mob death. Each successful copy gets five independent rolls;
/// the returned values travel with the drop through party voting and are never rolled at pickup.
pub fn roll_orange(mut random: impl FnMut() -> f64) -> Option<GearInstance> {
    if random() >= RULES.drop.chance_per_kill {
        return None;
    }
    let at = (random().clamp(0., 1. - f64::EPSILON) * RULES.pieces.len() as f64) as usize;
    let piece = &RULES.pieces[at];
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

    #[test]
    fn independent_probability_uniform_piece_and_inclusive_stats() {
        assert!(roll_orange(|| 0.001).is_none());
        for n in 0..50 {
            let mut values = [0., (n as f64 + 0.5) / 50., 0., 0., 0., 0., 0.].into_iter();
            let copy = roll_orange(|| values.next().unwrap()).unwrap();
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
        let high = roll_orange(|| values.next().unwrap()).unwrap();
        assert_eq!(
            (
                high.attack,
                high.defense,
                high.bonus_stats.stamina,
                high.bonus_stats.accuracy,
                high.bonus_stats.dexterity
            ),
            (55., 145., 140, 20, 35)
        );
    }

    #[test]
    fn first_two_orange_pieces_equip_on_every_class() {
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let mut c = Character::mercenary(class, 1, "Orange Test");
            c.add_item("orange_01", 1);
            c.add_item("orange_02", 1);
            c.equip_slots(&BTreeMap::from([
                ("chest".into(), "orange_01".into()),
                ("hands".into(), "orange_02".into()),
            ]))
            .unwrap();
            assert_eq!(c.gear().0, "orange_01");
            assert_eq!(c.gear().1, "orange_02");
            assert_eq!(
                c.equipped_count(super::super::item("orange_01").unwrap()),
                1
            );
        }
    }
}
