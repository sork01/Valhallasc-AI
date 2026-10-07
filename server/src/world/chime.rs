//! Chime objectives: "ring the tidebells". A chain of bells (places with the same `chain` and a `burn` time) stands about a
//! zone. Walking into a bell's circle rings it for `burn` seconds, and walking in again while it still rings starts the time
//! over. The objective's count is how many bells of its chain ring *at this moment*, and it is done once all of them do, so the
//! bells have to be reached in one run, quicker than the first one goes silent. A hero's fall silences every bell they rang.
//! Nothing but the finished objective is permanent: the bells are held here, per hero, and are not saved (a hero who logs out
//! mid-run starts over, and the count in their save is rewritten from the live bells on the first tick).
use super::*;

#[derive(Default)]
pub struct Chimes {
    /// Seconds left on every bell a hero has rung, per (session, place id).
    pub(super) lit: BTreeMap<(u64, String), f64>,
    /// How many bells of a chain rang at the previous tick, per (session, chain): what a silenced bell is announced against.
    last: BTreeMap<(u64, String), u32>,
}

struct Job {
    index: usize,
    n: usize,
    chain: String,
    need: u32,
    have: u32,
    bells: Vec<Place>,
}

impl Chimes {
    /// The bells one hero has ringing, for their snapshot: (place id, seconds left), in place order.
    pub(super) fn view(&self, session: u64) -> Vec<(String, f64)> {
        self.lit
            .range((session, String::new())..)
            .take_while(|((s, _), _)| *s == session)
            .map(|((_, id), left)| (id.clone(), (left * 10.).round() / 10.))
            .collect()
    }
}

impl World {
    pub(super) fn update_chimes(&mut self) {
        for left in self.chime.lit.values_mut() {
            *left -= TICK;
        }
        self.chime.lit.retain(|_, left| *left > 0.);
        let sessions: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.merc.is_none() && p.ambient.is_none())
            .map(|(session, _)| *session)
            .collect();
        for session in sessions {
            let Some(p) = self.players.get(&session) else {
                continue;
            };
            let map = &self.maps[p.character.zone];
            let mut jobs = Vec::new();
            for (index, progress) in p.character.quests.iter().enumerate() {
                if progress.claimed {
                    continue;
                }
                let Some(quest) = map.quests.iter().find(|q| q.id == progress.id) else {
                    continue;
                };
                for (n, o) in quest.objectives.iter().enumerate() {
                    let have = progress.counts.get(n).copied().unwrap_or(0);
                    if o.kind == "chime" && have < o.count {
                        jobs.push(Job {
                            index,
                            n,
                            chain: o.target.clone(),
                            need: o.count,
                            have,
                            bells: map
                                .places
                                .iter()
                                .filter(|pl| pl.chain == o.target)
                                .cloned()
                                .collect(),
                        });
                    }
                }
            }
            let here = p.character.point();
            let alive = p.character.hp > 0.;
            if jobs.is_empty() {
                self.chime.lit.retain(|(s, _), _| *s != session);
                self.chime.last.retain(|(s, _), _| *s != session);
                continue;
            }
            for job in jobs {
                let bells = job.bells.clone();
                let chain_key = (session, job.chain.clone());
                if !alive {
                    for b in &bells {
                        self.chime.lit.remove(&(session, b.id.clone()));
                    }
                    self.chime.last.remove(&chain_key);
                    if job.have > 0 {
                        self.set_chime(session, &job, 0);
                        self.chime_notice(
                            session,
                            false,
                            "The chime breaks as you fall. Ring the bells again from the start."
                                .into(),
                        );
                    }
                    continue;
                }
                for b in &bells {
                    let d = here.distance(Point { x: b.x, y: b.y });
                    if d > b.r {
                        continue;
                    }
                    let key = (session, b.id.clone());
                    if !self.chime.lit.contains_key(&key) {
                        self.chime_notice(
                            session,
                            true,
                            format!("You ring {}. It sounds for {:.0} s.", b.name, b.burn),
                        );
                    }
                    self.chime.lit.insert(key, b.burn);
                }
                let lit = bells
                    .iter()
                    .filter(|b| self.chime.lit.contains_key(&(session, b.id.clone())))
                    .count() as u32;
                if lit >= job.need {
                    for b in &bells {
                        self.chime.lit.remove(&(session, b.id.clone()));
                    }
                    self.chime.last.remove(&chain_key);
                    self.set_chime(session, &job, job.need);
                    self.chime_notice(
                        session,
                        true,
                        format!(
                            "All {} bells ring as one! The sound carries across the deep. Return to the quest giver.",
                            job.need
                        ),
                    );
                    self.save();
                    continue;
                }
                if lit != job.have {
                    self.set_chime(session, &job, lit);
                }
                let prev = self.chime.last.get(&chain_key).copied().unwrap_or(0);
                if lit < prev {
                    let text = if lit == 0 {
                        "The last bell falls silent. Begin again.".to_string()
                    } else {
                        format!("A bell falls silent: {lit} of {} still ring.", job.need)
                    };
                    self.chime_notice(session, false, text);
                }
                self.chime.last.insert(chain_key, lit);
            }
        }
        let live: Vec<u64> = self.players.keys().copied().collect();
        self.chime.lit.retain(|(s, _), _| live.contains(s));
        self.chime.last.retain(|(s, _), _| live.contains(s));
    }

    fn set_chime(&mut self, session: u64, job: &Job, value: u32) {
        if let Some(p) = self.players.get_mut(&session) {
            let counts = &mut p.character.quests[job.index].counts;
            if counts.len() <= job.n {
                counts.resize(job.n + 1, 0);
            }
            counts[job.n] = value.min(job.need);
        }
    }

    fn chime_notice(&self, session: u64, ok: bool, text: String) {
        if let Some(p) = self.players.get(&session) {
            let _ = p
                .peer
                .try_send(json!({"type":"notice","ok":ok,"text":text}));
        }
    }
}
