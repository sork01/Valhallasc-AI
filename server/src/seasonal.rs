//! Real-world, server-owned seasonal calendar. Stockholm time, independent of game day/night.
use crate::model::Character;
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Event {
    id: String,
    start: Option<[u32; 2]>,
    end_exclusive: Option<[u32; 2]>,
    #[serde(default)]
    calendar: Option<String>,
    #[serde(default)]
    start_offset: i32,
    #[serde(default)]
    end_offset_exclusive: i32,
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
/// Gregorian Meeus/Jones/Butcher computus, including its century corrections.
fn easter_sunday(year: u32) -> (u32, u32) {
    let a = year % 19;
    let b = year / 100;
    let c = year % 100;
    let d = b / 4;
    let e = b % 4;
    let f = (b + 8) / 25;
    let g = (b - f + 1) / 3;
    let h = (19 * a + b - d - g + 15) % 30;
    let i = c / 4;
    let k = c % 4;
    let l = (32 + 2 * e + 2 * i - h - k) % 7;
    let m = (a + 11 * h + 22 * l) / 451;
    let n = h + l - 7 * m + 114;
    (n / 31, n % 31 + 1)
}
/// Meeus (2nd ed.), ch. 27, June solstice with all Table 27.C periodic terms.
/// TT -> UT: Espenak/Meeus delta-T polynomials (NASA). See independent fixtures.
/// Deliberately bounded to 2000..=2099; fail closed outside the validated range.
fn june_solstice(year: u32) -> Option<u64> {
    if !(2000..=2099).contains(&year) {
        return None;
    }
    let y = (f64::from(year) - 2000.) / 1000.;
    let jde0 = 2451716.56767 + 365241.62603 * y + 0.00325 * y * y + 0.00888 * y.powi(3)
        - 0.00030 * y.powi(4);
    let t = (jde0 - 2451545.) / 36525.;
    let w = (35999.373 * t - 2.47).to_radians();
    let dl = 1. + 0.0334 * w.cos() + 0.0007 * (2. * w).cos();
    let terms: [(f64, f64, f64); 24] = [
        (485., 324.96, 1934.136),
        (203., 337.23, 32964.467),
        (199., 342.08, 20.186),
        (182., 27.85, 445267.112),
        (156., 73.14, 45036.886),
        (136., 171.52, 22518.443),
        (77., 222.54, 65928.934),
        (74., 296.72, 3034.906),
        (70., 243.58, 9037.513),
        (58., 119.81, 33718.147),
        (52., 297.17, 150.678),
        (50., 21.02, 2281.226),
        (45., 247.54, 29929.562),
        (44., 325.15, 31555.956),
        (29., 60.93, 4443.417),
        (18., 155.12, 67555.328),
        (17., 288.79, 4562.452),
        (16., 198.04, 62894.029),
        (14., 199.76, 31436.921),
        (12., 95.39, 14577.848),
        (12., 287.11, 31931.756),
        (12., 320.81, 34777.259),
        (9., 227.73, 1222.114),
        (8., 15.45, 16859.074),
    ];
    let correction = terms
        .iter()
        .map(|(a, b, c)| a * (b + c * t).to_radians().cos())
        .sum::<f64>();
    let decimal_year = f64::from(year) + 5.5 / 12.;
    let delta_t = if decimal_year < 2005. {
        let u = decimal_year - 2000.;
        63.86 + 0.3345 * u - 0.060374 * u.powi(2)
            + 0.0017275 * u.powi(3)
            + 0.000651814 * u.powi(4)
            + 0.00002373599 * u.powi(5)
    } else if decimal_year < 2050. {
        let u = decimal_year - 2000.;
        62.92 + 0.32217 * u + 0.005589 * u * u
    } else {
        -20. + 32. * ((decimal_year - 1820.) / 100.).powi(2) - 0.5628 * (2150. - decimal_year)
    };
    Some(((jde0 + 0.00001 * correction / dl - 2440587.5) * 86400. - delta_t).round() as u64)
}
fn stockholm_date(unix: u64) -> (u32, u32, u32) {
    date(
        unix + if summer(unix, date(unix).0) {
            7200
        } else {
            3600
        },
    )
}
fn interval(event: &Event, year: u32) -> (u64, u64) {
    if matches!(
        event.calendar.as_deref(),
        Some("gregorianEaster" | "juneSolstice")
    ) {
        let (month, day) = if event.calendar.as_deref() == Some("juneSolstice") {
            let Some(unix) = june_solstice(year) else {
                return (0, 0);
            };
            let (_, month, day) = stockholm_date(unix);
            (month, day)
        } else {
            easter_sunday(year)
        };
        let ordinal = day_number(year, month, day) as i64;
        // Shift LOCAL calendar dates first. Each midnight has its own CET/CEST offset.
        let boundary = |offset: i32| {
            let (y, m, d) = date(((ordinal + i64::from(offset)) * 86400) as u64);
            midnight(y, m, d)
        };
        (
            boundary(event.start_offset),
            boundary(event.end_offset_exclusive),
        )
    } else {
        let start = event.start.expect("fixed season start");
        let end = event.end_exclusive.expect("fixed season end");
        (
            midnight(year, start[0], start[1]),
            midnight(year + u32::from(end <= start), end[0], end[1]),
        )
    }
}
pub fn active_at(unix: u64) -> Vec<Active> {
    let (year, month, day) = stockholm_date(unix);
    let calendar_day = year * 10000 + month * 100 + day;
    EVENTS
        .iter()
        .filter_map(|e| {
            [year.saturating_sub(1).max(1970), year]
                .into_iter()
                .find_map(|year| {
                    let (start, end) = interval(e, year);
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
    fn solstice_matches_independent_usno_instants_and_stockholm_dates() {
        let data: serde_json::Value =
            serde_json::from_str(include_str!("../../docs/solstice-calendar-reference.txt"))
                .unwrap();
        for row in data["samples"].as_array().unwrap() {
            let year = row["year"].as_u64().unwrap() as u32;
            let unix = june_solstice(year).unwrap();
            let reference = row["unix"].as_u64().unwrap();
            assert!(
                unix.abs_diff(reference) <= 180,
                "{year}: {} seconds",
                unix.abs_diff(reference)
            );
            let (y, m, d) = stockholm_date(unix);
            assert_eq!(
                format!("{y:04}-{m:02}-{d:02}"),
                row["stockholmDate"].as_str().unwrap()
            );
        }
        assert!(june_solstice(1999).is_none());
        assert!(june_solstice(2100).is_none());
    }
    #[test]
    fn solstice_nine_local_dates_start_last_day_expiry_and_leap_years() {
        let event = EVENTS.iter().find(|e| e.id == "solstice").unwrap();
        for year in [
            2000, 2008, 2012, 2016, 2024, 2026, 2027, 2048, 2050, 2096, 2099,
        ] {
            let (_, m, d) = stockholm_date(june_solstice(year).unwrap());
            let (start, end) = interval(event, year);
            assert_eq!(start, midnight(year, m, d - 4));
            assert_eq!(end, midnight(year, m, d + 5));
            assert_eq!(end - start, 9 * 86400);
            for (at, expected) in [
                (start - 1, false),
                (start, true),
                (midnight(year, m, d + 4), true),
                (end - 1, true),
                (end, false),
            ] {
                assert_eq!(
                    active_at(at).iter().any(|e| e.id == "solstice"),
                    expected,
                    "{year}, {at}"
                );
            }
        }
        assert_eq!(interval(event, 2100), (0, 0));
    }
    #[test]
    fn easter_computus_matches_independent_usno_dates() {
        // USNO /calculated/observances/christian?year=YEAR, fetched 2026-11-03.
        // Includes earliest/latest dates and the 1954/1981/2049/2076 corrections.
        for (year, month, day) in [
            (1818, 3, 22),
            (1943, 4, 25),
            (1954, 4, 18),
            (1981, 4, 19),
            (2000, 4, 23),
            (2024, 3, 31),
            (2026, 4, 5),
            (2027, 3, 28),
            (2038, 4, 25),
            (2049, 4, 18),
            (2076, 4, 19),
            (2100, 3, 28),
        ] {
            assert_eq!(easter_sunday(year), (month, day), "year {year}");
        }
    }
    #[test]
    fn easter_local_dates_boundaries_rollover_and_dst() {
        let event = EVENTS.iter().find(|e| e.id == "easter").unwrap();
        for (year, start_date, end_date, start_unix, end_unix) in [
            (2024, [3, 29], [4, 9], 1711666800, 1712613600),
            (2027, [3, 26], [4, 6], 1806015600, 1806962400),
            (2038, [4, 23], [5, 4], 2155586400, 2156536800),
        ] {
            let (start, end) = interval(event, year);
            assert_eq!(start, midnight(year, start_date[0], start_date[1]));
            assert_eq!(end, midnight(year, end_date[0], end_date[1]));
            assert_eq!((start, end), (start_unix, end_unix));
            let active = |unix| active_at(unix).into_iter().find(|e| e.id == "easter");
            assert!(active(start - 1).is_none());
            assert_eq!(active(start).unwrap().year, year);
            assert!(active(end - 1).is_some());
            assert!(active(end).is_none());
            assert_eq!((end - start) / 3600, if year == 2038 { 264 } else { 263 });
        }
        // The March DST transition advances the daily key by a local date, not 24h.
        let before = midnight(2027, 3, 28);
        let after = midnight(2027, 3, 29);
        assert_eq!(after - before, 23 * 3600);
        assert_eq!(period("easter_hunt", &active_at(after - 1)), Some(20270328));
        assert_eq!(period("easter_hunt", &active_at(after)), Some(20270329));
    }
    #[test]
    fn easter_registry_preserves_fixed_and_cross_year_windows() {
        let e: Event = serde_json::from_value(serde_json::json!({
            "id":"cross","start":[12,29],"endExclusive":[1,3],"quests":[]
        }))
        .unwrap();
        assert_eq!(
            interval(&e, 2026),
            (midnight(2026, 12, 29), midnight(2027, 1, 3))
        );
        let christmas = EVENTS.iter().find(|e| e.id == "christmas").unwrap();
        assert_eq!(
            interval(christmas, 2026),
            (midnight(2026, 12, 15), midnight(2026, 12, 29))
        );
        assert_eq!(date(midnight(2000, 3, 1) + 3600), (2000, 3, 1));
        assert!(!leap(2100));
    }
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
