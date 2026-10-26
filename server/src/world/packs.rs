//! A pack pull outlives its hirer's respawn, but ends when its fighters win or all fall.
use super::*;
use std::collections::BTreeSet;

#[derive(Default)]
pub(super) struct Fight {
    pub enemies: BTreeSet<usize>,
    pub members: BTreeSet<u64>,
    pub downed: BTreeSet<u64>,
}

impl World {
    pub(super) fn holding_pack(&self, session: u64) -> bool {
        self.players.get(&session).is_some_and(|p| {
            self.pack_fights
                .get(&p.character.zone)
                .is_some_and(|f| f.members.contains(&session) && !f.downed.contains(&session))
        })
    }

    pub(super) fn update_pack_fights(&mut self) {
        let zones: BTreeSet<_> = self
            .players
            .values()
            .filter(|p| {
                p.ambient.is_none()
                    && self.is_instance(p.character.zone)
                    && !self.is_arena_zone(p.character.zone)
            })
            .map(|p| p.character.zone)
            .chain(self.pack_fights.keys().copied())
            .collect();
        let mut engaged_by_zone: BTreeMap<usize, BTreeSet<usize>> = BTreeMap::new();
        if !zones.is_empty() {
            for s in &self.slimes {
                if zones.contains(&s.zone)
                    && !s.dead
                    && !is_boss(&s.kind)
                    && self.spawns[s.id].ambush.is_none()
                    && s.target.is_some()
                    && matches!(s.state.as_str(), "chase" | "windup" | "lunge")
                {
                    engaged_by_zone.entry(s.zone).or_default().insert(s.id);
                }
            }
        }
        for zone in zones {
            // Boss deaths retain their existing fallen/rally rules.
            if self.boss.fight_in(zone) || !self.is_instance(zone) {
                if let Some(fight) = self.pack_fights.remove(&zone) {
                    for session in fight.members {
                        if let Some(p) = self.players.get_mut(&session)
                            && p.character.zone == zone
                            && p.character.hp <= 0.
                        {
                            p.pack_death = false;
                        }
                    }
                }
                continue;
            }
            let engaged = engaged_by_zone.remove(&zone).unwrap_or_default();
            let Some(mut fight) = self
                .pack_fights
                .remove(&zone)
                .or_else(|| (!engaged.is_empty()).then(Fight::default))
            else {
                continue;
            };
            fight.enemies.extend(engaged);
            for (&session, p) in &self.players {
                if p.character.zone == zone
                    && p.ambient.is_none()
                    && p.escort.is_none()
                    && !p.gauntlet
                    && !p.is_hidden()
                {
                    fight.members.insert(session);
                }
            }
            for &session in &fight.members {
                let Some(p) = self.players.get_mut(&session) else {
                    continue;
                };
                if p.character.zone != zone {
                    continue;
                }
                if p.character.hp <= 0. {
                    fight.downed.insert(session);
                    p.pack_death = true;
                    if p.merc.is_some() {
                        p.fallen = true;
                    }
                } else if fight.downed.contains(&session)
                    && (p.target.is_some_and(|id| fight.enemies.contains(&id))
                        || (p.moving && p.character.point().distance(self.maps[zone].spawn) > 8.))
                    && fight.enemies.iter().any(|&id| {
                        let s = &self.slimes[id];
                        !s.dead
                            && s.point().distance(p.character.point())
                                < Slime::attack_profile(&s.kind).3
                    })
                {
                    // A returned player can deliberately rejoin the pull.
                    fight.downed.remove(&session);
                }
            }
            let fighting = fight.enemies.iter().any(|&id| {
                let s = &self.slimes[id];
                !s.dead && !matches!(s.state.as_str(), "idle" | "wander" | "return" | "waiting")
            });
            let survivors = fight.members.iter().any(|session| {
                !fight.downed.contains(session)
                    && self.players.get(session).is_some_and(|p| {
                        p.character.zone == zone && p.character.hp > 0. && !p.is_hidden()
                    })
            });
            if fighting && survivors {
                self.pack_fights.insert(zone, fight);
                continue;
            }
            if fighting && !survivors {
                // Only this pull resets; already killed enemies and other copies stay untouched.
                // Restore living enemies directly to their authored homes, without kill rewards
                // or a new level roll, so a wall cannot strand an evading pack.
                for id in fight.enemies {
                    if !self.slimes[id].dead {
                        self.slimes[id] =
                            Slime::with_level(id, &self.spawns[id], self.slimes[id].level);
                        self.place_enemy(id);
                    }
                }
                self.enemy_bolts.retain(|b| b.zone != zone);
                self.bolts.retain(|b| b.zone != zone);
            }
            // Dead hired fighters wait for the pull to end, then regroup normally.
            for session in fight.members {
                if let Some(p) = self.players.get_mut(&session)
                    && p.character.zone == zone
                    && p.pack_death
                    && p.character.hp <= 0.
                {
                    p.fallen = false;
                    p.dead_time = 0.;
                }
            }
        }
    }
}
