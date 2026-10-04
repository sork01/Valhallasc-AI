//! Escort quests. A stranded person (an NPC with an `escort` definition) joins whoever speaks to them while that
//! person's escort quest is taken and its escort objective is still open. The escort is an ordinary `Player`
//! (so enemies fight it, a priest could heal it and every client draws it) that is never saved, never joins a
//! party and whose input is decided here: it walks the route in the NPC's definition at its own pace, waits when
//! its owner falls behind, stands still while an enemy is fighting it, and wakes the ambushers the route passes.
//! Reaching the last waypoint completes the objective. If the escort or its owner dies, the owner leaves the zone
//! for good, or the owner is left far behind, the journey fails: the escort is gone, the objective stays open and
//! speaking to the stranded person again starts it over.
use super::*;

/// The escort waits for its owner when they are farther away than this.
const WAIT_DISTANCE: f64 = 12.;
/// An owner this far from the escort (or in another zone) for `LOST_SECONDS` is deemed to have abandoned it.
const LOST_DISTANCE: f64 = 40.;
const LOST_SECONDS: f64 = 20.;
/// An enemy this close that has picked the escort as its target stops the walk.
const ENGAGED: f64 = 3.5;
/// A waypoint is reached inside this distance.
const ARRIVE: f64 = 0.8;
/// How long the escort stays after safety before it walks off.
const FAREWELL: f64 = 3.;
/// A walker that has not moved for this long while free to go is put on its next waypoint (waypoints are clear ground).
const STUCK_SECONDS: f64 = 4.;
/// Seconds between two "I am waiting for you" reminders.
const REMIND_EVERY: f64 = 20.;

#[derive(Clone)]
pub struct Escort {
    pub npc: String,
    pub quest: String,
    /// The character id of the hero being escorted for.
    pub owner: String,
    route: Vec<Point>,
    ambush: Vec<AmbushDef>,
    next: usize,
    speed: f64,
    fired: Vec<String>,
    lost: f64,
    stuck: f64,
    reminded: f64,
    arrived: Option<f64>,
}
impl Escort {
    /// Walking speed in tiles per second.
    pub fn speed(&self) -> f64 {
        self.speed
    }
    /// Whether the journey has ended in safety (the escort lingers a moment before it walks off).
    #[cfg(test)]
    pub fn arrived(&self) -> bool {
        self.arrived.is_some()
    }
}

impl World {
    /// The session of the escort that walks with this character, if any.
    pub(super) fn escort_of(&self, owner: &str) -> Option<u64> {
        self.players
            .iter()
            .find(|(_, p)| p.escort.as_ref().is_some_and(|e| e.owner == owner))
            .map(|(session, _)| *session)
    }

    /// Called whenever `session` speaks to `npc_id`: starts that person's escort when the quest is taken and the
    /// objective open. Returns the sentence the conversation should show (None when nothing happened).
    pub(super) fn try_start_escort(&mut self, session: u64, npc_id: &str) -> Option<String> {
        let c = &self.players.get(&session)?.character;
        let zone = c.zone;
        let npc = self.maps[zone].npcs.iter().find(|n| n.id == npc_id)?;
        let def = npc.escort.as_ref()?;
        if c.hp <= 0. || c.point().distance(npc.position_at(self.time)) > 2.8 {
            return None;
        }
        let quest = self.maps[zone].quests.iter().find(|q| q.id == def.quest)?;
        let objective = quest
            .objectives
            .iter()
            .position(|o| o.kind == "escort" && o.target == npc_id)?;
        let progress = c.quests.iter().find(|g| g.id == quest.id && !g.claimed)?;
        if progress.counts.get(objective).copied().unwrap_or(0) >= quest.objectives[objective].count
        {
            return Some(format!("{} is already safe.", npc.name));
        }
        if let Some(other) = self.escort_of(&c.id) {
            let name = &self.players[&other].character.look.name;
            return Some(if name == &npc.name {
                format!("{name} is already walking with you.")
            } else {
                format!("You are already escorting {name}.")
            });
        }
        let class = mercs::class_named(&def.class)?;
        let owner = c.id.clone();
        let mut character = Character::mercenary(class, def.level, &npc.name);
        character.look.gender = if def.female {
            Gender::Female
        } else {
            Gender::Male
        };
        character.look.hair_color = def.hair_color;
        character.look.skin = def.skin;
        character.zone = zone;
        let at = npc.position_at(self.time);
        let mut start = Point {
            x: at.x + 1.,
            y: at.y + 1.,
        };
        self.maps[zone].collide(&mut start, PLAYER_RADIUS);
        character.x = start.x;
        character.y = start.y;
        character.hp = character.max_hp();
        let name = npc.name.clone();
        let title = quest.title.clone();
        let escort = Escort {
            npc: npc_id.to_owned(),
            quest: quest.id.clone(),
            owner: owner.clone(),
            route: def
                .route
                .iter()
                .map(|p| Point { x: p[0], y: p[1] })
                .collect(),
            ambush: def.ambush.clone(),
            next: 0,
            speed: def.speed,
            fired: vec![],
            lost: 0.,
            stuck: 0.,
            reminded: self.time,
            arrived: None,
        };
        let session_id = mercs::MERC_BASE + self.merc_seq;
        self.merc_seq += 1;
        // Nobody reads an escort's socket either: a closed channel makes every send a harmless no-op.
        let (tx, _rx) = mpsc::channel(1);
        let mut player = Player::new(character, tx);
        player.merc = Some(owner);
        player.escort = Some(escort);
        self.players.insert(session_id, player);
        Some(format!(
            "{name} joins you for \"{title}\". Keep {name} alive and bring them to safety: if either of you falls, the quest fails."
        ))
    }

    /// Once per tick, before the players move: decide what every escort does.
    pub(super) fn update_escorts(&mut self) {
        let sessions: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.escort.is_some())
            .map(|(session, _)| *session)
            .collect();
        for session in sessions {
            self.escort_think(session);
        }
    }

    fn escort_think(&mut self, session: u64) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let Some(e) = p.escort.clone() else {
            return;
        };
        let name = p.character.look.name.clone();
        let Some(owner) = self.session_of(&e.owner) else {
            // The owner logged out or was removed: nobody is left to be failed.
            self.remove_escort(session);
            return;
        };
        if let Some(arrived) = e.arrived {
            if self.time - arrived >= FAREWELL {
                let _ = self.players[&owner].peer.try_send(json!({"type":"system","text":format!("{name} thanks you and hurries off to safety.")}));
                self.remove_escort(session);
            }
            return;
        }
        let me = p.character.point();
        let zone = p.character.zone;
        let owner_p = &self.players[&owner];
        if p.character.hp <= 0. {
            return self.fail_escort(session, &format!("{name} has fallen."));
        }
        if owner_p.character.hp <= 0. {
            return self.fail_escort(
                session,
                &format!("You have fallen, and {name} cannot go on alone."),
            );
        }
        let there = owner_p.character.point();
        let together = owner_p.character.zone == zone;
        let gap = if together {
            me.distance(there)
        } else {
            f64::MAX
        };
        if gap > LOST_DISTANCE {
            let lost = e.lost + TICK;
            if lost >= LOST_SECONDS {
                return self.fail_escort(session, &format!("You left {name} behind."));
            }
            self.players
                .get_mut(&session)
                .unwrap()
                .escort
                .as_mut()
                .unwrap()
                .lost = lost;
        } else if e.lost > 0. {
            self.players
                .get_mut(&session)
                .unwrap()
                .escort
                .as_mut()
                .unwrap()
                .lost = 0.;
        }
        // Ambushers wake when the walk passes their trigger.
        let waking: Vec<String> = e
            .ambush
            .iter()
            .filter(|a| {
                !e.fired.contains(&a.tag)
                    && me.distance(Point {
                        x: a.at[0],
                        y: a.at[1],
                    }) < a.r
            })
            .map(|a| a.tag.clone())
            .collect();
        for tag in waking {
            self.release_ambush(&tag, session);
            self.players
                .get_mut(&session)
                .unwrap()
                .escort
                .as_mut()
                .unwrap()
                .fired
                .push(tag);
        }
        let engaged = self.slimes.iter().any(|s| {
            !s.dead
                && s.zone == zone
                && s.target == Some(session)
                && s.point().distance(me) < ENGAGED + s.r
        });
        let waiting = gap > WAIT_DISTANCE;
        let time = self.time;
        let p = self.players.get_mut(&session).unwrap();
        let escort = p.escort.as_mut().unwrap();
        if engaged || waiting {
            p.goal = None;
            p.input = Point::default();
            escort.stuck = 0.;
            if waiting && time - escort.reminded >= REMIND_EVERY {
                escort.reminded = time;
                let _ = self.players[&owner].peer.try_send(
                    json!({"type":"system","text":format!("{name} is waiting for you to catch up.")}),
                );
            }
            return;
        }
        while escort.next < escort.route.len() && me.distance(escort.route[escort.next]) < ARRIVE {
            escort.next += 1;
        }
        let Some(&goal) = escort.route.get(escort.next) else {
            p.goal = None;
            escort.arrived = Some(time);
            let npc = escort.npc.clone();
            let quest = escort.quest.clone();
            let owner_p = self.players.get_mut(&owner).unwrap();
            quest_progress(
                &mut owner_p.character,
                &self.maps[zone].quests,
                "escort",
                &npc,
            );
            let title = self.maps[zone]
                .quests
                .iter()
                .find(|q| q.id == quest)
                .map_or(String::new(), |q| q.title.clone());
            let owner_p = &self.players[&owner];
            let _ = owner_p.peer.try_send(json!({"type":"notice","ok":true,"text":format!("{name} is safe! Return to the quest giver for \"{title}\".")}));
            self.save();
            return;
        };
        // A walker that makes no progress is lifted onto its next waypoint, which the generator keeps clear.
        if !p.moving && p.goal.is_some() {
            escort.stuck += TICK;
            if escort.stuck >= STUCK_SECONDS {
                escort.stuck = 0.;
                p.character.x = goal.x;
                p.character.y = goal.y;
            }
        } else {
            escort.stuck = 0.;
        }
        p.goal = Some(goal);
        p.input = Point::default();
    }

    /// The escort ends in failure: it is gone, its ambushers go back to sleep, and the owner is told why.
    fn fail_escort(&mut self, session: u64, why: &str) {
        let Some(e) = self.players.get(&session).and_then(|p| p.escort.clone()) else {
            return;
        };
        self.remove_escort(session);
        if let Some(owner) = self.session_of(&e.owner) {
            let title = self
                .maps
                .iter()
                .flat_map(|m| &m.quests)
                .find(|q| q.id == e.quest)
                .map_or(String::new(), |q| q.title.clone());
            let p = &self.players[&owner];
            let _ = p.peer.try_send(json!({"type":"notice","ok":false,"text":format!("Quest failed: {title}. {why} Speak to them again to start over.")}));
            let _ = p
                .peer
                .try_send(json!({"type":"system","text":format!("Quest failed: {title}. {why}")}));
        }
    }

    /// Removes an escort without a word (it arrived, its owner left, or the world is being reset).
    pub(super) fn remove_escort(&mut self, session: u64) {
        let Some(p) = self.players.remove(&session) else {
            return;
        };
        if let Some(e) = p.escort {
            for a in &e.ambush {
                self.sleep_ambush(&a.tag);
            }
        }
    }

    /// Every sleeping enemy tagged `tag` attacks the escort (and whoever is with it) at once.
    pub(super) fn release_ambush(&mut self, tag: &str, target: u64) {
        let ids: Vec<usize> = (0..self.spawns.len())
            .filter(|i| self.spawns[*i].ambush.as_deref() == Some(tag) && self.slimes[*i].dead)
            .collect();
        for id in ids {
            let spawn = self.spawns[id].clone();
            let level = self.roll_level(&spawn.kind);
            let mut enemy = Slime::with_level(id, &spawn, level);
            let bodies = self.actor_bodies(spawn.zone, None, Some(id));
            if let Some(point) = free_actor_position(
                &self.maps[spawn.zone],
                enemy.point(),
                enemy.r,
                &bodies,
                true,
            ) {
                enemy.x = point.x;
                enemy.y = point.y;
            }
            enemy.target = Some(target);
            enemy.hunt = true;
            enemy.state = "chase".into();
            self.slimes[id] = enemy;
            self.event(
                "ambush",
                "",
                Point {
                    x: spawn.x,
                    y: spawn.y,
                },
                0.,
                false,
            );
        }
    }

    /// Sleeping ambushers are dead, hidden and never respawn; a living one is put back to sleep.
    pub(super) fn sleep_ambush(&mut self, tag: &str) {
        for id in 0..self.spawns.len() {
            if self.spawns[id].ambush.as_deref() == Some(tag) {
                self.slimes[id] = self.dormant_enemy(id);
            }
        }
    }

    /// A slot that exists but is not on the field: stable id, dead, waiting, no respawn timer.
    pub(super) fn dormant_enemy(&mut self, id: usize) -> Slime {
        let spawn = self.spawns[id].clone();
        let mut enemy = Slime::with_level(id, &spawn, Slime::default_level(&spawn.kind));
        enemy.dead = true;
        enemy.hp = 0.;
        enemy.state = "waiting".into();
        enemy.die_t = 2.;
        enemy.respawn = 1e9;
        enemy
    }
}
