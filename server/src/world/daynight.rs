use serde_json::{Value, json};
use std::time::{SystemTime, UNIX_EPOCH};

/// The clock advances 24 game hours in 1,200 real seconds.
const CYCLE_MS: i64 = 1_200_000;
const MS_PER_GAME_HOUR: f64 = CYCLE_MS as f64 / 24.;

pub(super) fn unix_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
        .min(i64::MAX as u128) as i64
}

#[derive(Clone)]
pub(super) struct WorldClock {
    epoch_ms: i64,
    frozen_hour: Option<f64>,
}

impl WorldClock {
    pub(super) fn new(epoch_ms: i64) -> Self {
        Self {
            epoch_ms,
            frozen_hour: None,
        }
    }

    pub(super) fn hour_at(&self, now_ms: i64) -> f64 {
        self.frozen_hour.unwrap_or_else(|| {
            (now_ms.saturating_sub(self.epoch_ms) as f64 / MS_PER_GAME_HOUR).rem_euclid(24.)
        })
    }

    pub(super) fn snapshot(&self) -> Value {
        json!({"hour": self.hour_at(unix_ms()), "hoursPerSecond": if self.frozen_hour.is_some() { 0. } else { 0.02 }})
    }

    /// Returns the new persistent epoch when running; a frozen test clock is transient.
    pub(super) fn set(&mut self, hour: Option<f64>, freeze: bool) -> Result<Option<i64>, String> {
        let hour = hour.unwrap_or_else(|| self.hour_at(unix_ms()));
        if !hour.is_finite() || !(0. ..24.).contains(&hour) {
            return Err("World time must be from 0:00 through 23:59.".into());
        }
        if freeze {
            self.frozen_hour = Some(hour);
            Ok(None)
        } else {
            self.epoch_ms = unix_ms() - (hour * MS_PER_GAME_HOUR).round() as i64;
            self.frozen_hour = None;
            Ok(Some(self.epoch_ms))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{store::Store, world::World};

    #[test]
    fn twenty_real_minutes_make_one_day_and_freeze_does_not_advance() {
        let mut clock = WorldClock::new(10_000);
        assert_eq!(clock.hour_at(10_000), 0.);
        assert_eq!(clock.hour_at(60_000), 1.);
        assert_eq!(clock.hour_at(610_000), 12.);
        assert_eq!(clock.hour_at(1_210_000), 0.);
        clock.set(Some(18.5), true).unwrap();
        assert_eq!(clock.hour_at(9_999_999), 18.5);
        assert!(clock.set(Some(24.), false).is_err());
    }

    #[test]
    fn sqlite_epoch_survives_reopen_and_private_snapshot_can_freeze() {
        let path = std::env::temp_dir().join(format!(
            "valhallasc-daynight-{}.sqlite",
            uuid::Uuid::new_v4()
        ));
        {
            let store = Store::open(&path).unwrap();
            assert_eq!(store.world_clock_epoch_ms(123_456).unwrap(), 123_456);
            assert_eq!(store.world_clock_epoch_ms(987_654).unwrap(), 123_456);
            store.set_world_clock_epoch_ms(777_000).unwrap();
        }
        {
            let store = Store::open(&path).unwrap();
            assert_eq!(store.world_clock_epoch_ms(987_654).unwrap(), 777_000);
        }
        for suffix in ["", "-wal", "-shm"] {
            let _ = std::fs::remove_file(format!("{}{}", path.display(), suffix));
        }
        let store = Store::open(std::path::Path::new(":memory:")).unwrap();
        let mut world = World::with_level_spread(store, 0);
        world.world_clock.set(Some(21.5), true).unwrap();
        let view = world.snapshot_for(0);
        assert_eq!(view["worldTime"]["hour"], 21.5);
        assert_eq!(view["worldTime"]["hoursPerSecond"], 0.);
        assert_eq!(world.snapshot_for(1)["worldTime"], view["worldTime"]);
    }
}
