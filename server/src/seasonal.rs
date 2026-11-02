//! Real-world, server-owned seasonal calendar. Stockholm time, independent of game day/night.
use crate::model::Character;
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Event {
    id: String,
    start: [u32; 2],
    end_exclusive: [u32; 2],
    quests: Vec<String>,
    #[serde(default)]
    daily_quests: Vec<String>,
    #[serde(default)]
    givers: std::collections::BTreeMap<String, Vec<String>>,
}
static EVENTS: LazyLock<Vec<Event>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/seasons.txt")).expect("valid seasonal calendar")
});
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Active {
    pub id: String,
    pub year: u32,
    pub day: u32,
    pub until: u64,
}

fn leap(year: u32) -> bool {
    year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400))
}
fn months(year: u32) -> [u32; 12] {
    [
        31,
        if leap(year) { 29 } else { 28 },
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]
}
fn day_number(year: u32, month: u32, day: u32) -> u64 {
    (1970..year)
        .map(|y| if leap(y) { 366_u64 } else { 365 })
        .sum::<u64>()
        + months(year)[..month as usize - 1]
            .iter()
            .map(|d| u64::from(*d))
            .sum::<u64>()
        + u64::from(day - 1)
}
fn date(unix: u64) -> (u32, u32, u32) {
    let mut days = unix.min(253_402_214_399) / 86400;
    let mut year = 1970;
    loop {
        let n = if leap(year) { 366 } else { 365 };
        if days < n {
            break;
        }
        days -= n;
        year += 1;
    }
    let mut month = 1;
    for n in months(year) {
        if days < u64::from(n) {
            break;
        }
        days -= u64::from(n);
        month += 1;
    }
    (year, month, days as u32 + 1)
}
fn last_sunday(year: u32, month: u32) -> u32 {
    let last = months(year)[month as usize - 1];
    last - ((day_number(year, month, last) + 4) % 7) as u32
}
fn summer(unix: u64, year: u32) -> bool {
    unix >= day_number(year, 3, last_sunday(year, 3)) * 86400 + 3600
        && unix < day_number(year, 10, last_sunday(year, 10)) * 86400 + 3600
}
fn midnight(year: u32, month: u32, day: u32) -> u64 {
    let utc = day_number(year, month, day) * 86400;
    // Both candidate offsets are unambiguous at midnight on event boundaries.
    utc - if summer(utc - 7200, year) { 7200 } else { 3600 }
}
pub fn active_at(unix: u64) -> Vec<Active> {
    let (year, month, day) = date(
        unix + if summer(unix, date(unix).0) {
            7200
        } else {
            3600
        },
    );
    let calendar_day = year * 10000 + month * 100 + day;
    EVENTS
        .iter()
        .filter_map(|e| {
            [year.saturating_sub(1).max(1970), year]
                .into_iter()
                .find_map(|year| {
                    let start = midnight(year, e.start[0], e.start[1]);
                    let end_year = year + u32::from(e.end_exclusive <= e.start);
                    let end = midnight(end_year, e.end_exclusive[0], e.end_exclusive[1]);
                    (unix >= start && unix < end).then(|| Active {
                        id: e.id.clone(),
                        year,
                        day: calendar_day,
                        until: end,
                    })
                })
        })
        .collect()
}
pub fn quest_event(id: &str) -> Option<&'static str> {
    EVENTS
        .iter()
        .find(|e| e.quests.iter().any(|q| q == id))
        .map(|e| e.id.as_str())
}
pub fn daily(id: &str) -> bool {
    EVENTS
        .iter()
        .any(|e| e.daily_quests.iter().any(|q| q == id))
}
pub fn period(id: &str, active: &[Active]) -> Option<u32> {
    let event = quest_event(id)?;
    active
        .iter()
        .find(|a| a.id == event)
        .map(|a| if daily(id) { a.day } else { a.year })
}
pub fn giver(id: &str, npc: &str) -> bool {
    EVENTS
        .iter()
        .any(|e| e.givers.get(id).is_some_and(|v| v.iter().any(|n| n == npc)))
}
pub fn sync_character(c: &mut Character, active: &[Active]) -> bool {
    let mut changed = false;
    c.quests.retain_mut(|q| {
        let Some(event) = quest_event(&q.id) else {
            return true;
        };
        if q.claimed {
            return true;
        }
        let _ = event;
        let current = period(&q.id, active);
        if current.is_some() && current == c.seasonal_started.get(&q.id).copied() {
            return true;
        }
        changed = true;
        c.seasonal_started.remove(&q.id);
        if q.completions > 0 {
            q.claimed = true;
            q.counts.clear();
            true
        } else {
            false
        }
    });
    changed
}
#[derive(Default)]
pub struct Calendar {
    pub override_unix: Option<u64>,
    pub cached: Vec<Active>,
    pub next_check: f64,
}
impl Calendar {
    pub fn now(&self) -> u64 {
        self.override_unix
            .unwrap_or_else(|| crate::store::unix_now().max(0) as u64)
    }
    pub fn active(&self) -> Vec<Active> {
        active_at(self.now())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn seasonal_stockholm_boundaries_and_dst_are_inclusive() {
        for year in [2025, 2026, 2027, 2028, 2030] {
            let start = midnight(year, 10, 26);
            let end = midnight(year, 11, 10);
            assert!(active_at(start - 1).is_empty());
            assert_eq!(active_at(start)[0].year, year);
            assert!(!active_at(midnight(year, 11, 9) + 86399).is_empty());
            assert!(!active_at(end - 1).is_empty());
            assert!(active_at(end).is_empty());
        }
        assert_eq!(midnight(2026, 10, 26), 1792969200);
        assert_eq!(midnight(2025, 10, 26), 1761429600);
    }
}
