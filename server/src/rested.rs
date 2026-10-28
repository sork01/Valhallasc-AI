//! Offline-earned bonus XP. The reserve is a fraction of a level, independent of XP gear.
use crate::model::Character;
use serde::{Deserialize, Serialize};

// One offline second earns 1,000 units: 3,600 seconds = 5% of a level.
const LEVEL: u64 = 72_000_000;
const CAP: u64 = 2 * LEVEL;

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Rested {
    pub reserve: u64,
    pub last_seen: u64,
}

impl Rested {
    /// Called only when joining, after rejecting an already-online character.
    pub fn join(&mut self, now: u64) {
        let elapsed = if self.last_seen == 0 {
            0 // Old saves have no trustworthy offline timestamp.
        } else {
            now.saturating_sub(self.last_seen)
        };
        self.reserve = self
            .reserve
            .saturating_add(elapsed.saturating_mul(1_000))
            .min(CAP);
        self.last_seen = now;
    }

    pub fn percent(&self) -> f64 {
        self.reserve.min(CAP) as f64 * 100. / LEVEL as f64
    }

    /// Spend only bonus XP actually awarded, using the level before this reward.
    fn bonus(&mut self, base: u32, normal: u32, need: u32) -> u32 {
        self.reserve = self.reserve.min(CAP);
        let available = self.reserve * u64::from(need) / LEVEL;
        let bonus = (u64::from(base) * 2)
            .min(available)
            .min(u64::from(u32::MAX - normal)) as u32;
        let spent = (u64::from(bonus) * LEVEL).div_ceil(u64::from(need));
        self.reserve = self.reserve.saturating_sub(spent);
        bonus
    }
}

impl Character {
    /// All real XP payouts share this path. Rested adds 200% of base XP alongside
    /// the existing additive rebirth/Hierloom bonuses; it never multiplies those.
    pub fn reward_xp(&mut self, base: u32) -> (u32, u32) {
        let normal = self.boosted_xp(base);
        let need = self.xp_need();
        let got = normal + self.rested.bonus(base, normal, need);
        (got, self.grant_xp(got))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{model::Look, store::Store};

    fn hero() -> Character {
        Store::open(std::path::Path::new(":memory:"))
            .unwrap()
            .create(Look::default(), Default::default())
            .unwrap()
            .0
    }

    #[test]
    fn rested_hourly_partial_hours_cap_and_clock_rollback() {
        let mut r = Rested::default();
        r.join(1_000_000);
        assert_eq!(r.reserve, 0);
        r.join(1_001_800);
        assert_eq!(r.percent(), 2.5);
        r.join(1_003_600);
        assert_eq!(r.percent(), 5.);
        r.join(1_144_000);
        assert_eq!(r.percent(), 200.);
        r.join(u64::MAX);
        assert_eq!(r.percent(), 200.);
        r.reserve = 0;
        r.join(1);
        assert_eq!(r.reserve, 0);
    }

    #[test]
    fn rested_triples_base_xp_spends_only_bonus_and_exhausts_partway() {
        let mut c = hero();
        c.rested.reserve = CAP;
        let need = c.xp_need();
        assert_eq!(c.reward_xp(10).0, 30);
        assert_eq!(c.xp, 30);
        assert_eq!(
            c.rested.reserve,
            CAP - (20 * LEVEL).div_ceil(u64::from(need))
        );
        // Exactly 5 bonus XP remain: this payout is only partially rested.
        c.rested.reserve = (5 * LEVEL).div_ceil(u64::from(need));
        assert_eq!(c.reward_xp(10).0, 15);
        assert_eq!(c.rested.reserve, 0);
        assert_eq!(c.reward_xp(10).0, 10);
    }

    #[test]
    fn rested_stacks_additively_and_does_not_spend_on_zero_or_overflow() {
        let mut c = hero();
        c.level = 50;
        c.rebirth_tiers = [5, 0, 0, 0, 0];
        c.add_item("hierloom_necklace", 1);
        c.equip_slots(&std::collections::BTreeMap::from([(
            "necklace".into(),
            "hierloom_necklace".into(),
        )]))
        .unwrap();
        c.rested.reserve = CAP;
        assert_eq!(c.reward_xp(100).0, 450);
        let reserve = c.rested.reserve;
        assert_eq!(c.reward_xp(0).0, 0);
        assert_eq!(c.rested.reserve, reserve);
        assert_eq!(c.reward_xp(u32::MAX).0, u32::MAX);
        assert_eq!(c.rested.reserve, reserve);
    }

    #[test]
    fn rested_level_up_and_rebirth_keep_the_remaining_percentage() {
        let mut c = hero();
        c.rested.reserve = CAP;
        c.xp = c.xp_need() - 1;
        let need = c.xp_need();
        assert_eq!(c.reward_xp(1), (3, 1));
        let reserve = CAP - (2 * LEVEL).div_ceil(u64::from(need));
        assert_eq!(c.rested.reserve, reserve);
        c.level = 50;
        c.hp = c.max_hp();
        // The real character reset preserves the reserve, like other permanent perks.
        c.rebirth(Default::default()).unwrap();
        assert_eq!(c.level, 1);
        assert_eq!(c.rested.reserve, reserve);
    }

    #[test]
    fn rested_old_saves_start_empty_and_new_fields_round_trip() {
        let mut c = hero();
        let mut saved = serde_json::to_value(&c).unwrap();
        saved.as_object_mut().unwrap().remove("rested");
        let old: Character = serde_json::from_value(saved).unwrap();
        assert_eq!(old.rested.reserve, 0);
        assert_eq!(old.rested.last_seen, 0);
        c.rested.join(1_000_000);
        c.rested.join(1_003_600);
        let saved: Character = serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
        assert_eq!(saved.rested.percent(), 5.);
        assert_eq!(saved.rested.last_seen, 1_003_600);
    }
}
