//! Hold objectives: "hold the ward". The hero stands inside a named place (a ward circle) and channels: every second
//! spent inside adds one to the objective, standing outside only pauses it. While they channel, waves of dormant
//! enemies tagged on the place (`Place::waves`) wake at set progress marks and hunt them, so the circle has to be held
//! against a crowd. Falling near the ward loses the progress; finishing it dissolves whatever is still awake. Enemies
//! left awake by a hero who walked away go back to sleep once nobody is near the ward for a while.
use super::*;
use std::collections::BTreeSet;

/// Seconds without any channeller near a ward before its woken enemies go back to sleep.
const AWAY_SECONDS: f64 = 12.;
/// How far from the ward's edge a hero still counts as being at it (for the death rule and the sleep timer).
const WATCH_RADIUS: f64 = 30.;

#[derive(Default)]
pub struct Holds {
    /// Ticks spent inside a ward since the last whole second, per session.
    pub(super) ticks: BTreeMap<u64, u32>,
    /// Waves already released at a ward (zone, place id).
    pub(super) fired: BTreeMap<(usize, String), Vec<String>>,
    /// Seconds since a ward with woken enemies last had a hero near it.
    pub(super) away: BTreeMap<(usize, String), f64>,
}

struct Job {
    index: usize,
    n: usize,
    place: Place,
    need: u32,
    have: u32,
}

impl World {
    pub(super) fn update_holds(&mut self) {
        let sessions: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.merc.is_none())
            .map(|(session, _)| *session)
            .collect();
        let per_second = (1. / TICK).round() as u32;
        let mut near: BTreeSet<(usize, String)> = BTreeSet::new();
        for session in sessions {
            let Some(p) = self.players.get(&session) else {
                continue;
            };
            let zone = p.character.zone;
            let map = &self.maps[zone];
            let mut jobs = Vec::new();
            for (index, progress) in p.character.quests.iter().enumerate() {
                if progress.claimed {
                    continue;
                }
                let Some(quest) = map.quests.iter().find(|q| q.id == progress.id) else {
                    continue;
                };
                for (n, o) in quest.objectives.iter().enumerate() {
                    if o.kind != "hold" {
                        continue;
                    }
                    let Some(place) = map.places.iter().find(|pl| pl.id == o.target) else {
                        continue;
                    };
                    let have = progress.counts.get(n).copied().unwrap_or(0);
                    if have < o.count {
                        jobs.push(Job {
                            index,
                            n,
                            place: place.clone(),
                            need: o.count,
                            have,
                        });
                    }
                }
            }
            if jobs.is_empty() {
                self.hold.ticks.remove(&session);
                continue;
            }
            let here = p.character.point();
            let alive = p.character.hp > 0.;
            for job in jobs {
                let key = (zone, job.place.id.clone());
                let d = here.distance(Point {
                    x: job.place.x,
                    y: job.place.y,
                });
                if !alive {
                    if job.have > 0 && d < job.place.r + WATCH_RADIUS {
                        self.set_hold(session, &job, 0);
                        self.stop_hold(&key);
                        self.hold_notice(
                            session,
                            false,
                            format!(
                                "The ward at {} collapses as you fall. Hold it again from the start.",
                                job.place.name
                            ),
                        );
                    }
                    continue;
                }
                if d >= job.place.r + WATCH_RADIUS {
                    continue;
                }
                near.insert(key.clone());
                if d > job.place.r {
                    continue;
                }
                let ticks = self.hold.ticks.entry(session).or_insert(0);
                *ticks += 1;
                let mut have = job.have;
                if *ticks >= per_second {
                    *ticks = 0;
                    have += 1;
                    self.set_hold(session, &job, have);
                    if have == 1 {
                        self.hold_notice(
                            session,
                            true,
                            format!(
                                "You begin to hold the ward at {}. Stay inside the circle.",
                                job.place.name
                            ),
                        );
                    }
                }
                let due: Vec<String> = job
                    .place
                    .waves
                    .iter()
                    .filter(|w| {
                        w.at <= have
                            && !self
                                .hold
                                .fired
                                .get(&key)
                                .is_some_and(|f| f.contains(&w.tag))
                    })
                    .map(|w| w.tag.clone())
                    .collect();
                for tag in due {
                    self.release_ambush(&tag, session);
                    self.hold.fired.entry(key.clone()).or_default().push(tag);
                    self.hold_notice(
                        session,
                        true,
                        "The storm answers: something is coming for the ward.".into(),
                    );
                }
                if have >= job.need {
                    self.stop_hold(&key);
                    self.hold_notice(
                        session,
                        true,
                        format!(
                            "The ward at {} holds! The storm-spawn dissolve. Return to the quest giver.",
                            job.place.name
                        ),
                    );
                    self.save();
                }
            }
        }
        let sites: Vec<(usize, String)> = self.hold.fired.keys().cloned().collect();
        for key in sites {
            if near.contains(&key) {
                self.hold.away.remove(&key);
                continue;
            }
            let away = self.hold.away.entry(key.clone()).or_insert(0.);
            *away += TICK;
            if *away >= AWAY_SECONDS {
                self.stop_hold(&key);
            }
        }
    }

    fn set_hold(&mut self, session: u64, job: &Job, value: u32) {
        if let Some(p) = self.players.get_mut(&session) {
            let counts = &mut p.character.quests[job.index].counts;
            if counts.len() <= job.n {
                counts.resize(job.n + 1, 0);
            }
            counts[job.n] = value.min(job.need);
        }
    }

    /// Every wave of a ward goes back to sleep and may be released again.
    fn stop_hold(&mut self, key: &(usize, String)) {
        self.hold.fired.remove(key);
        self.hold.away.remove(key);
        let tags: Vec<String> = self.maps[key.0]
            .places
            .iter()
            .find(|p| p.id == key.1)
            .map(|p| p.waves.iter().map(|w| w.tag.clone()).collect())
            .unwrap_or_default();
        for tag in tags {
            self.sleep_ambush(&tag);
        }
    }

    fn hold_notice(&self, session: u64, ok: bool, text: String) {
        if let Some(p) = self.players.get(&session) {
            let _ = p
                .peer
                .try_send(json!({"type":"notice","ok":ok,"text":text}));
        }
    }
}
