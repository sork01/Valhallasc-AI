//! Cosmetic weather. Rules are generated from scripts/weather_zones.py; the schedule is a pure
//! function of the persisted world clock epoch, zone, and six-slot cycle.
use serde::Deserialize;
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::sync::OnceLock;

const SLOT_MS: i64 = 240_000;
const CYCLE_SLOTS: i64 = 6;

#[derive(Deserialize)]
struct Rule {
    zone: usize,
    theme: String,
    allowed: Vec<String>,
    variant: Option<String>,
    inside: bool,
}

fn rules() -> &'static [Rule] {
    static RULES: OnceLock<Vec<Rule>> = OnceLock::new();
    RULES.get_or_init(|| {
        serde_json::from_str(include_str!("../../../world/weather.txt"))
            .expect("generated weather rules")
    })
}

#[derive(Clone)]
struct Forced {
    kind: String,
    intensity: String,
    at_ms: i64,
}

pub(super) struct Weather {
    epoch_ms: i64,
    forced: BTreeMap<usize, Forced>,
}

fn mix(mut x: u64) -> u64 {
    x ^= x >> 30;
    x = x.wrapping_mul(0xbf58_476d_1ce4_e5b9);
    x ^= x >> 27;
    x = x.wrapping_mul(0x94d0_49bb_1331_11eb);
    x ^ (x >> 31)
}

// Integer halves represent the 1.5× desert bias without changing the allowed set.
fn hour_weight(kind: &str, hour: u32) -> usize {
    match (kind, hour) {
        ("fog", 5..=7) => 6,
        ("thunderstorm", 17..=21) => 4,
        ("sandstorm", 10..=15) => 3,
        _ => 2,
    }
}

impl Weather {
    pub(super) fn new(epoch_ms: i64) -> Self {
        Self {
            epoch_ms,
            forced: BTreeMap::new(),
        }
    }

    pub(super) fn set_epoch(&mut self, epoch_ms: i64) {
        self.epoch_ms = epoch_ms;
    }

    fn spell(&self, zone: usize, now_ms: i64, allowed: &[&str], variant: Option<&str>) -> Value {
        let elapsed = now_ms.saturating_sub(self.epoch_ms).max(0);
        let slot = elapsed / SLOT_MS;
        let cycle = slot / CYCLE_SLOTS;
        let within = slot % CYCLE_SLOTS;
        let seed = mix((self.epoch_ms as u64)
            ^ ((zone as u64).wrapping_mul(0x9e37_79b9_7f4a_7c15))
            ^ (cycle as u64));
        // 2–5 clear slots, then 4–1 weather slots. The weighted mean is 3.3/6 = 55% clear.
        let clear_slots = match seed % 20 {
            0..=4 => 2,
            5..=11 => 3,
            12..=16 => 4,
            _ => 5,
        };
        let clear_slots = if allowed.len() == 2 { 3 } else { clear_slots };
        let clear = within < clear_slots || allowed.len() == 1;
        let end_slot = cycle * CYCLE_SLOTS + if clear { clear_slots } else { CYCLE_SLOTS };
        let start_slot = cycle * CYCLE_SLOTS + if clear { 0 } else { clear_slots };
        let kind = if clear {
            "clear"
        } else {
            let hour = ((self
                .epoch_ms
                .saturating_add(start_slot.saturating_mul(SLOT_MS))
                .saturating_sub(self.epoch_ms) as f64
                / 50_000.)
                % 24.) as u32;
            let mut weighted = Vec::new();
            for kind in allowed.iter().skip(1) {
                let weight = hour_weight(kind, hour);
                for _ in 0..weight {
                    weighted.push(*kind);
                }
            }
            weighted[(mix(seed ^ 0xaad1_73b2_6c42_9d31) as usize) % weighted.len()]
        };
        let intensity = if clear {
            "none"
        } else {
            match mix(seed ^ 0x5c4e_842d_99be_0f37) % 20 {
                0..=9 => "light",
                10..=16 => "medium",
                _ => "heavy",
            }
        };
        let start_ms = self
            .epoch_ms
            .saturating_add(start_slot.saturating_mul(SLOT_MS));
        let end_ms = self
            .epoch_ms
            .saturating_add(end_slot.saturating_mul(SLOT_MS));
        json!({"type":kind,"intensity":intensity,"variant":if kind == "wind" { variant } else { None },
            "endsInSeconds":((end_ms-now_ms).max(0) as f64)/1000.,
            "ageSeconds":((now_ms-start_ms).max(0) as f64)/1000.})
    }

    pub(super) fn view(&self, zone: usize, template: Option<usize>, now_ms: i64) -> Value {
        let public = template.unwrap_or(zone);
        let Some(rule) = rules().get(public).filter(|r| r.zone == public) else {
            return json!({"type":"clear","intensity":"none","inside":true});
        };
        if rule.inside || template.is_some() {
            return json!({"type":"clear","intensity":"none","inside":true});
        }
        if let Some(forced) = self.forced.get(&public) {
            return json!({"type":forced.kind,"intensity":forced.intensity,"variant":rule.variant,
                "inside":false,"endsInSeconds":null,"ageSeconds":((now_ms-forced.at_ms).max(0) as f64)/1000.});
        }
        if rule.theme == "yearwheel" {
            let seasons = json!({
                "spring":self.spell(public * 4,now_ms,&["clear","rain","fog"],None),
                "summer":self.spell(public * 4 + 1,now_ms,&["clear","thunderstorm","fog"],None),
                "autumn":self.spell(public * 4 + 2,now_ms,&["clear","wind","fog"],Some("leaves")),
                "winter":self.spell(public * 4 + 3,now_ms,&["clear","snow","fog"],None),
            });
            return json!({"type":"clear","intensity":"none","inside":false,"seasons":seasons});
        }
        let allowed: Vec<&str> = rule.allowed.iter().map(String::as_str).collect();
        let mut value = self.spell(public, now_ms, &allowed, rule.variant.as_deref());
        value["inside"] = json!(false);
        value
    }

    pub(super) fn set(
        &mut self,
        zone: usize,
        kind: &str,
        intensity: Option<&str>,
        now_ms: i64,
    ) -> Result<Value, String> {
        let rule = rules()
            .get(zone)
            .filter(|r| r.zone == zone && !r.inside)
            .ok_or("Weather is unavailable indoors.")?;
        if kind == "resume" {
            self.forced.remove(&zone);
            return Ok(self.view(zone, None, now_ms));
        }
        if !rule.allowed.iter().any(|allowed| allowed == kind) {
            return Err(format!("{kind} is not allowed in this zone."));
        }
        let intensity = if kind == "clear" {
            "none"
        } else {
            intensity.unwrap_or("medium")
        };
        if kind != "clear" && !["light", "medium", "heavy"].contains(&intensity) {
            return Err("Use light, medium or heavy intensity.".into());
        }
        self.forced.insert(
            zone,
            Forced {
                kind: kind.into(),
                intensity: intensity.into(),
                at_ms: now_ms,
            },
        );
        Ok(self.view(zone, None, now_ms))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn hours_bias_only_the_intended_weather() {
        assert_eq!(hour_weight("fog", 6), 3 * hour_weight("rain", 6));
        assert_eq!(hour_weight("thunderstorm", 19), 2 * hour_weight("rain", 19));
        assert_eq!(
            hour_weight("sandstorm", 12) * 2,
            3 * hour_weight("rain", 12)
        );
        assert_eq!(hour_weight("fog", 12), hour_weight("rain", 12));
    }
    #[test]
    fn generated_rules_and_schedule_stay_valid() {
        let weather = Weather::new(1_000_000);
        assert!(rules().len() >= 40);
        for rule in rules() {
            for slot in 0..240 {
                let view = weather.view(rule.zone, None, 1_000_000 + slot * SLOT_MS);
                let kind = view["type"].as_str().unwrap();
                assert!(rule.allowed.iter().any(|allowed| allowed == kind));
                if rule.inside {
                    assert_eq!(kind, "clear");
                }
                assert_eq!(
                    view,
                    weather.view(rule.zone, None, 1_000_000 + slot * SLOT_MS)
                );
            }
        }
        assert_eq!(weather.view(0, Some(0), 1_000_000)["inside"], true);
        let clear = (0..6_000)
            .filter(|slot| weather.view(0, None, 1_000_000 + slot * SLOT_MS)["type"] == "clear")
            .count();
        assert!(
            (0.51..0.59).contains(&(clear as f64 / 6_000.)),
            "clear share: {clear}/6000"
        );
    }

    #[test]
    fn overrides_are_transient_and_allowed_types_follow_the_generated_map() {
        let epoch = 1_000_000;
        let mut weather = Weather::new(epoch);
        let original = weather.view(0, None, epoch + 20 * SLOT_MS);
        assert!(weather.set(0, "snow", Some("heavy"), epoch).is_err());
        assert!(weather.set(5, "rain", None, epoch).is_err());
        weather.set(0, "rain", Some("heavy"), epoch).unwrap();
        assert_eq!(weather.view(0, None, epoch)["type"], "rain");
        assert_eq!(weather.view(0, None, epoch)["intensity"], "heavy");
        assert_eq!(
            Weather::new(epoch).view(0, None, epoch + 20 * SLOT_MS),
            original,
            "a restart restores the seeded schedule"
        );
        weather.set(0, "resume", None, epoch).unwrap();
        assert_eq!(weather.view(0, None, epoch + 20 * SLOT_MS), original);
        weather.set_epoch(epoch + SLOT_MS);
        assert_eq!(
            weather.view(0, None, epoch + 20 * SLOT_MS),
            Weather::new(epoch + SLOT_MS).view(0, None, epoch + 20 * SLOT_MS)
        );
        let year = weather.view(28, None, epoch + 20 * SLOT_MS);
        assert!(
            year["seasons"]["spring"]["type"]
                .as_str()
                .is_some_and(|s| ["clear", "rain", "fog"].contains(&s))
        );
        assert!(
            year["seasons"]["winter"]["type"]
                .as_str()
                .is_some_and(|s| ["clear", "snow", "fog"].contains(&s))
        );
    }
}
