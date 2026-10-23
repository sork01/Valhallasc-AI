//! Boss-only Chainforged rolls. World-drop orange rules remain independent.
use super::*;
use serde::Deserialize;

pub const SOURCE: &str = "chained_forge";

#[derive(Deserialize)]
struct Rules {
    pieces: Vec<Piece>,
    bosses: Vec<Boss>,
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Piece {
    id: String,
    slot: String,
    class: Option<Class>,
    rolls: std::collections::BTreeMap<String, [u32; 2]>,
}
#[derive(Deserialize)]
pub struct Boss {
    pub kind: String,
    pub slots: Vec<String>,
    pub drops: usize,
    pub weapons: usize,
}
static RULES: LazyLock<Rules> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/raid-rewards.txt"))
        .expect("valid raid reward rules")
});

pub fn boss(kind: &str) -> Option<&'static Boss> {
    RULES.bosses.iter().find(|b| b.kind == kind)
}

fn pick(count: usize, value: f64) -> usize {
    (value.clamp(0., 1. - f64::EPSILON) * count as f64) as usize
}

/// Select slot first and class second, so a shared slot is not five times rarer.
pub fn piece_for(kind: &str, slots: &[&str], choice: f64) -> Option<&'static Item> {
    let rule = boss(kind)?;
    let allowed: Vec<_> = slots
        .iter()
        .copied()
        .filter(|s| (rule.weapons > 0 && *s == "weapon") || rule.slots.iter().any(|v| v == s))
        .collect();
    if allowed.is_empty() {
        return None;
    }
    let scaled = choice.clamp(0., 1. - f64::EPSILON) * allowed.len() as f64;
    let slot = allowed[scaled.floor() as usize];
    let class = [
        Class::Warrior,
        Class::Mage,
        Class::Assassin,
        Class::Priest,
        Class::Hunter,
    ][pick(5, scaled.fract())];
    let piece = RULES
        .pieces
        .iter()
        .find(|p| p.slot == slot && p.class.is_none_or(|c| c == class))?;
    item(&piece.id)
}

/// Inclusive, independent saved-copy rolls. No caller can invoke this for ordinary orange.
pub fn copy(piece: &Item, mut random: impl FnMut() -> f64) -> GearInstance {
    let rule = RULES
        .pieces
        .iter()
        .find(|p| p.id == piece.id)
        .expect("Chainforged piece");
    let mut roll = |stat: &str| {
        let [low, high] = rule.rolls[stat];
        low + pick((high - low + 1) as usize, random()) as u32
    };
    GearInstance {
        id: 0,
        item: piece.id.clone(),
        rarity: "legendary".into(),
        attack: f64::from(roll("attack")),
        defense: f64::from(roll("defense")),
        bonus_stats: Attributes {
            stamina: roll("stamina"),
            accuracy: roll("accuracy"),
            dexterity: roll("dexterity"),
            ..Attributes::default()
        },
        rolled_stats: Attributes::default(),
        rank: 0,
        trade_until: 0,
        trade_with: vec![],
        wear: 0,
    }
}

/// Two distinct non-weapon kinds per boss, and two weapon rolls on Eldmarr.
/// Repeat the whole guaranteed table at each rebirth step; ownership/voting are
/// handled by the existing raid loot path, which excludes hired fighters.
pub fn drops(kind: &str, multiplier: u32, mut random: impl FnMut() -> f64) -> Vec<GearInstance> {
    let Some(rule) = boss(kind) else {
        return vec![];
    };
    let mut result = vec![];
    for _ in 0..multiplier.max(1) {
        let mut slots = rule.slots.iter().map(String::as_str).collect::<Vec<_>>();
        for _ in 0..rule.drops {
            let slot = slots.remove(pick(slots.len(), random()));
            let piece = piece_for(kind, &[slot], random()).unwrap();
            result.push(copy(piece, &mut random));
        }
        for _ in 0..rule.weapons {
            let piece = piece_for(kind, &["weapon"], random()).unwrap();
            result.push(copy(piece, &mut random));
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::{BTreeMap, BTreeSet};

    #[test]
    fn raid_rewards_cover_all_classes_slots_and_roll_above_worldheart() {
        assert_eq!(RULES.pieces.len(), 29);
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let mut c = Character::mercenary(class, 99, "Reward Test");
            let mut wear = BTreeMap::new();
            for p in &RULES.pieces {
                if p.class.is_some_and(|v| v != class) {
                    continue;
                }
                let it = item(&p.id).unwrap();
                assert_eq!(
                    (it.source.as_deref(), it.rarity.as_str(), it.required_level),
                    (Some(SOURCE), "legendary", 99)
                );
                let low = copy(it, || 0.);
                let high = copy(it, || 1.);
                assert!(low.attack <= high.attack && low.defense <= high.defense);
                let previous: serde_json::Value =
                    serde_json::from_str(include_str!("../../../world/orange_rules.txt")).unwrap();
                if let Some(old) = previous["pieces"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .find(|i| i["requiredLevel"] == 99 && i["slot"] == p.slot)
                {
                    for stat in ["attack", "defense", "stamina"] {
                        let [lo, hi] = p.rolls[stat];
                        let best = old["rolls"][stat][1].as_u64().unwrap() as u32;
                        assert!(
                            hi == 0 || lo > best,
                            "{} {stat}: {lo} must beat {best}",
                            p.id
                        );
                    }
                }

                c.add_item(&p.id, 1);
                let slot = match p.slot.as_str() {
                    "armor" => "chest",
                    "weapon" => "hands",
                    "accessory" => "accessory1",
                    s => s,
                };
                wear.insert(slot.into(), p.id.clone());
                let mut under = Character::mercenary(class, 98, "Too Low");
                under.add_item(&p.id, 1);
                assert!(
                    under
                        .equip_slots(&BTreeMap::from([(slot.into(), p.id.clone())]))
                        .is_err()
                );
                if let Some(other) = p.class {
                    let wrong = if other == Class::Mage {
                        Class::Warrior
                    } else {
                        Class::Mage
                    };
                    let mut c = Character::mercenary(wrong, 99, "Wrong Class");
                    c.add_item(&p.id, 1);
                    assert!(
                        c.equip_slots(&BTreeMap::from([(slot.into(), p.id.clone())]))
                            .is_err()
                    );
                }
            }
            c.equip_slots(&wear).unwrap();
            assert_eq!(
                c.worn_items()
                    .iter()
                    .filter(|i| i.source.as_deref() == Some(SOURCE))
                    .count(),
                9
            );
            c.add_item("chainforged_accessory", 1);
            c.equip_slots(&BTreeMap::from([(
                "accessory2".into(),
                "chainforged_accessory".into(),
            )]))
            .unwrap();
            assert_eq!(
                c.worn_items()
                    .iter()
                    .filter(|i| i.source.as_deref() == Some(SOURCE))
                    .count(),
                10
            );
            assert_eq!(c.set_counts()[SOURCE], 8);
            c.look.validate().unwrap();
        }
    }

    #[test]
    fn raid_rewards_bosses_drop_distinct_slots_and_only_eldmarr_weapons() {
        let mut covered = BTreeSet::new();
        let mut total = 0;
        for b in &RULES.bosses {
            for choice in [0., 0.2, 0.4, 0.6, 0.8, 1. - f64::EPSILON] {
                let copies = drops(&b.kind, 1, || choice);
                assert_eq!(copies.len(), 2 + b.weapons);
                let kinds = copies
                    .iter()
                    .map(|p| item(&p.item).unwrap().kind.as_str())
                    .collect::<Vec<_>>();
                assert_ne!(kinds[0], kinds[1]);
                assert_eq!(kinds.iter().filter(|k| **k == "weapon").count(), b.weapons);
                covered.extend(kinds);
                assert_eq!(drops(&b.kind, 3, || choice).len(), copies.len() * 3);
            }
            total += drops(&b.kind, 1, || 0.).len();
            for slot in &b.slots {
                let pieces = (0..5)
                    .map(|n| piece_for(&b.kind, &[slot.as_str()], (n as f64 + 0.5) / 5.).unwrap())
                    .collect::<Vec<_>>();
                if pieces[0].class.is_some() {
                    assert_eq!(
                        pieces
                            .iter()
                            .map(|i| i.id.as_str())
                            .collect::<BTreeSet<_>>()
                            .len(),
                        5
                    );
                }
            }
        }
        assert_eq!(total, 22);
        assert_eq!(covered.len(), 9);
        assert!(piece_for("cf_kettil", &["weapon"], 0.).is_none());
        assert!(drops("slime", 1, || 0.).is_empty());
    }
}
