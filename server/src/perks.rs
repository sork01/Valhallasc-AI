//! Rebirth perks (docs/rebirth.md, REBIRTH-PERKS). Every perk is derived from `Character::rebirth_tiers` and the table in
//! `world/rebirth.txt`, so a rebalance needs no save migration and a save can never hold more than the cap. None of
//! them touches attack, defense, health, damage taken or skill power.
use crate::model::Character;
use serde::Deserialize;
use std::sync::LazyLock;

#[derive(Deserialize)]
struct Perk {
    /// The lowest rebirth tier that earns this perk.
    unlock: u32,
    step: u32,
    cap: u32,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Table {
    xp_percent: Perk,
    gold_percent: Perk,
    bag_cells: Perk,
    fare_percent: Perk,
    reset_price_percent: Perk,
    drop_multiplier: Perk,
}

static TABLE: LazyLock<Table> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/rebirth.txt")).expect("valid rebirth table")
});

/// Rebirths done at the perk's tier or higher.
fn count_from(c: &Character, perk: &Perk) -> u32 {
    let from = (perk.unlock as usize).saturating_sub(1).min(5);
    c.rebirth_tiers[from..]
        .iter()
        .fold(0u32, |sum, n| sum.saturating_add(*n))
}

/// `min(cap, step x rebirths at the perk's tier or higher)`.
fn earned(c: &Character, perk: &Perk) -> u32 {
    perk.step.saturating_mul(count_from(c, perk)).min(perk.cap)
}

/// `value` raised by `percent`, rounded to the nearest whole number.
fn plus_percent(value: u32, percent: u32) -> u32 {
    if percent == 0 {
        return value;
    }
    let raised = (u64::from(value) * u64::from(100 + percent) + 50) / 100;
    u32::try_from(raised).unwrap_or(u32::MAX)
}

/// `price` lowered by `percent`, rounded to the nearest whole number and never below 1 for a price above 0.
pub fn minus_percent(price: u32, percent: u32) -> u32 {
    if percent == 0 || price == 0 {
        return price;
    }
    let lowered = (u64::from(price) * u64::from(100 - percent.min(100)) + 50) / 100;
    (lowered as u32).max(1)
}

impl Character {
    /// Extra XP from every source that pays XP for play (kills, shared party XP, quests), in percent.
    pub fn rebirth_xp_percent(&self) -> u32 {
        earned(self, &TABLE.xp_percent)
    }
    /// Extra gold from kills, quests and sales, in percent.
    pub fn rebirth_gold_percent(&self) -> u32 {
        earned(self, &TABLE.gold_percent)
    }
    /// Extra bag cells on top of the backpack and the fitted bags.
    pub fn rebirth_bag_cells(&self) -> usize {
        earned(self, &TABLE.bag_cells) as usize
    }
    /// Discount on a Spark Travel fare, in percent.
    pub fn rebirth_fare_percent(&self) -> u32 {
        earned(self, &TABLE.fare_percent)
    }
    /// Discount on the stat-reset price, in percent.
    pub fn rebirth_reset_percent(&self) -> u32 {
        earned(self, &TABLE.reset_price_percent)
    }
    /// The drop rate multiplier, 1 for everyone who never rebirthed at the top tier, at most the table's cap.
    pub fn drop_multiplier(&self) -> u32 {
        let perk = &TABLE.drop_multiplier;
        1u32.saturating_add(perk.step.saturating_mul(count_from(self, perk)))
            .min(perk.cap.max(1))
    }
    pub fn boosted_xp(&self, xp: u32) -> u32 {
        plus_percent(xp, self.rebirth_xp_percent())
    }
    pub fn boosted_gold(&self, gold: u32) -> u32 {
        plus_percent(gold, self.rebirth_gold_percent())
    }
    pub fn spark_fare(&self, fare: u32) -> u32 {
        minus_percent(fare, self.rebirth_fare_percent())
    }
}

/// How a roll with chance `p` splits at drop multiplier `m`: whole drops and the chance of one more. A chance whose
/// product with `m` stays below 1 is one roll against that product; a larger one gives its whole part for sure.
pub fn scaled(p: f64, m: u32) -> (u32, f64) {
    let target = (p * f64::from(m.max(1))).max(0.);
    let whole = target.floor();
    if whole < 1. {
        (0, target)
    } else {
        (whole as u32, target - whole)
    }
}

/// The number of drops from a roll with chance `p` at multiplier `m`, using `draw` for the random numbers. At `m = 1`
/// this is exactly the old single draw compared with `p` (so seeded sequences do not change); above it, a guaranteed
/// part needs no draw.
pub fn copies(p: f64, m: u32, mut draw: impl FnMut() -> f64) -> u32 {
    if m <= 1 {
        return u32::from(draw() < p);
    }
    let (whole, fraction) = scaled(p, m);
    if whole == 0 {
        return u32::from(draw() < fraction);
    }
    whole + u32::from(fraction > 0. && draw() < fraction)
}

/// A chance that decides the quality of a drop that was already made (the purple copy of a set piece), multiplied and
/// capped at 100%.
pub fn boosted_chance(p: f64, m: u32) -> f64 {
    (p * f64::from(m.max(1))).min(1.)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Class;

    fn reborn(tiers: [u32; 5]) -> Character {
        let mut c = Character::mercenary(Class::Warrior, 1, "Reborn");
        c.rebirth_tiers = tiers;
        c
    }

    #[test]
    fn scaled_follows_the_documented_examples() {
        let near = |(whole, fraction): (u32, f64), want: (u32, f64)| {
            assert_eq!(whole, want.0);
            assert!((fraction - want.1).abs() < 1e-9, "{fraction} vs {}", want.1);
        };
        near(scaled(0.04, 2), (0, 0.08));
        near(scaled(0.5, 2), (1, 0.));
        near(scaled(1., 2), (2, 0.));
        near(scaled(0.02, 5), (0, 0.10));
        near(scaled(1., 5), (5, 0.));
        near(scaled(0.33, 5), (1, 0.65));
        near(scaled(0.05, 5), (0, 0.25));
        near(scaled(0.3, 1), (0, 0.3));
        assert_eq!(boosted_chance(0.04, 5), 0.2);
        assert!((boosted_chance(0.03, 5) - 0.15).abs() < 1e-12);
        assert_eq!(boosted_chance(0.5, 5), 1., "a chance never passes 100%");
    }

    #[test]
    fn a_multiplier_of_one_makes_the_old_single_draw_and_nothing_else() {
        for p in [0., 0.02, 0.5, 1.] {
            for draw in [0., 0.01, 0.3, 0.999] {
                let mut calls = 0;
                let n = copies(p, 1, || {
                    calls += 1;
                    draw
                });
                assert_eq!((n, calls), (u32::from(draw < p), 1), "p {p} draw {draw}");
            }
        }
    }

    #[test]
    fn copies_multiplies_the_expected_number_of_drops() {
        // A deterministic low-discrepancy sequence stands in for the random numbers.
        for (p, m) in [(0.02, 2), (0.02, 5), (0.33, 5), (1., 2), (1., 5), (0.15, 3)] {
            let mut x = 0.123;
            let mut total = 0u64;
            let runs = 20_000;
            for _ in 0..runs {
                total += u64::from(copies(p, m, || {
                    x = (x + 0.618_033_988_749_895) % 1.;
                    x
                }));
            }
            let want = p * f64::from(m);
            let got = total as f64 / f64::from(runs);
            assert!(
                (got - want).abs() < want * 0.05 + 0.01,
                "p {p} m {m}: {got} vs {want}"
            );
        }
    }

    #[test]
    fn perks_stack_to_their_caps_and_start_at_their_tiers() {
        let never = reborn([0; 5]);
        assert_eq!(
            (
                never.rebirth_xp_percent(),
                never.rebirth_gold_percent(),
                never.rebirth_bag_cells()
            ),
            (0, 0, 0)
        );
        assert_eq!(
            (never.rebirth_fare_percent(), never.rebirth_reset_percent()),
            (0, 0)
        );
        assert_eq!(never.drop_multiplier(), 1);
        // Five tier-1 rebirths stop at +50% XP and give nothing else.
        let five_first = reborn([5, 0, 0, 0, 0]);
        assert_eq!(five_first.rebirth_xp_percent(), 50);
        assert_eq!(reborn([9, 0, 0, 0, 0]).rebirth_xp_percent(), 50);
        assert_eq!(
            (
                five_first.rebirth_gold_percent(),
                five_first.rebirth_bag_cells(),
                five_first.rebirth_fare_percent(),
                five_first.rebirth_reset_percent(),
                five_first.drop_multiplier()
            ),
            (0, 0, 0, 0, 1)
        );
        // One top-tier rebirth gives every perk once and doubles the drops.
        let top = reborn([0, 0, 0, 0, 1]);
        assert_eq!(
            (
                top.rebirth_xp_percent(),
                top.rebirth_gold_percent(),
                top.rebirth_bag_cells(),
                top.rebirth_fare_percent(),
                top.rebirth_reset_percent(),
                top.drop_multiplier()
            ),
            (10, 10, 2, 10, 10, 2)
        );
        // The multiplier climbs by one per further top-tier rebirth and stops at 5; lower tiers never raise it.
        let climb: Vec<u32> = (0..=6)
            .map(|n| reborn([0, 0, 0, 0, n]).drop_multiplier())
            .collect();
        assert_eq!(climb, [1, 2, 3, 4, 5, 5, 5]);
        assert_eq!(reborn([9, 9, 9, 9, 0]).drop_multiplier(), 1);
        // Every perk is capped.
        let most = reborn([40, 40, 40, 40, 40]);
        assert_eq!(
            (
                most.rebirth_xp_percent(),
                most.rebirth_gold_percent(),
                most.rebirth_bag_cells(),
                most.rebirth_fare_percent(),
                most.rebirth_reset_percent(),
                most.drop_multiplier()
            ),
            (50, 50, 10, 50, 50, 5)
        );
    }

    #[test]
    fn percentages_round_to_the_nearest_whole_number() {
        let c = reborn([1, 0, 0, 0, 0]);
        assert_eq!(c.boosted_xp(0), 0);
        assert_eq!(c.boosted_xp(100), 110);
        assert_eq!(c.boosted_xp(15), 17, "16.5 rounds up");
        assert_eq!(c.boosted_xp(u32::MAX), u32::MAX);
        assert_eq!(reborn([0; 5]).boosted_gold(37), 37);
        assert_eq!(minus_percent(20, 10), 18);
        assert_eq!(minus_percent(20, 50), 10);
        assert_eq!(minus_percent(1, 50), 1, "a price never reaches 0");
        assert_eq!(minus_percent(0, 50), 0);
        assert_eq!(minus_percent(20, 0), 20);
    }
}
