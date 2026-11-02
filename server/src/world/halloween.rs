//! One seasonal summon, frozen party scaling and independent daily personal mount rolls.
use super::*;
pub(super) const KIND: &str = "hollow_rider";
pub(super) const QUEST: &str = "halloween_hunt";
pub(super) const RITUAL: &str = "halloween_lantern";
const ZONE: usize = 3;
const CENTRE: Point = Point { x: 105., y: 23. };
const LANTERN: Point = Point { x: 105., y: 32. };
const TAG: &str = "halloween:hollow-rider";
pub(super) struct Run {
    pub members: Vec<String>,
    pub enemy: usize,
    pub started: f64,
    pub away: f64,
}
pub(super) fn wins_mount(roll: f64) -> bool {
    (0. ..0.01).contains(&roll)
}
impl World {
    pub(super) fn halloween_member(&self, session: u64) -> bool {
        self.halloween.as_ref().is_some_and(|r| {
            self.players
                .get(&session)
                .is_some_and(|p| r.members.contains(&p.character.id))
        })
    }
    pub(super) fn halloween_view(&self) -> Value {
        let active = self.seasonal.cached.iter().any(|e| e.id == "halloween");
        if !active {
            return Value::Null;
        }
        json!({"zone":ZONE,"x":CENTRE.x,"y":CENTRE.y,"radius":9.,"quest":QUEST,"active":self.halloween.is_some(),"level":self.halloween.as_ref().map(|r|self.slimes[r.enemy].level)})
    }
    pub(super) fn summon_halloween(&mut self, session: u64) -> Result<(), String> {
        let seasons = self.seasonal.active();
        let period = crate::seasonal::period(QUEST, &seasons)
            .ok_or("The haunted lantern only answers during Halloween.")?;
        if self.halloween.is_some() {
            return Err(
                "The Hollow Rider is already summoned. Wait for that encounter to finish.".into(),
            );
        }
        let p = self.players.get(&session).ok_or("Unknown fighter.")?;
        if p.character.zone != ZONE
            || p.character.point().distance(LANTERN) > 2.8
            || p.character.hp <= 0.
        {
            return Err("Walk closer to the haunted lantern.".into());
        }
        if !p
            .character
            .quests
            .iter()
            .any(|q| q.id == QUEST && !q.claimed)
            || p.character.seasonal_started.get(QUEST) != Some(&period)
        {
            return Err("Accept The Hollow Rider daily quest in a city first.".into());
        }
        let owner = p.character.id.clone();
        if self.party_leader(&owner).is_some_and(|id| id != owner) {
            return Err("The party leader must light the haunted lantern.".into());
        }
        let members = self.party_mates(&owner);
        if members.len() != 5 {
            return Err("Gather exactly five living fighters, including hired fighters, at the ritual clearing.".into());
        }
        let mut levels = 0_u64;
        for member in &members {
            let p = self
                .online(member)
                .ok_or("All five fighters must be online at the ritual clearing.")?;
            if p.ambient.is_some()
                || p.gauntlet
                || p.character.hp <= 0.
                || p.character.zone != ZONE
                || p.character.point().distance(CENTRE) > 12.
                || p.character.mounted
                || p.character.spark_travel.is_some()
                || p.combat_left > 0.
            {
                return Err("All five fighters must gather alive, dismounted and out of combat at the ritual clearing.".into());
            }
            levels += u64::from(p.character.level);
        }
        let level = levels.div_ceil(5) as u32;
        let enemy = self
            .spawns
            .iter()
            .position(|s| s.zone == ZONE && s.ambush.as_deref() == Some(TAG))
            .ok_or("The ritual clearing is unavailable.")?;
        let mut s = Slime::with_level(enemy, &self.spawns[enemy], level);
        // Scale health with the reference attack curve and damage with player health.
        // This keeps the event a five-fighter encounter throughout the existing level curve.
        let reference = Character::mercenary(Class::Warrior, level.min(99), "Rider scale");
        let base = Character::mercenary(Class::Warrior, 1, "Rider base");
        let (health, damage, _, _) = Slime::stats(KIND);
        s.max_hp = (health * reference.stats().0 / base.stats().0).round();
        s.hp = s.max_hp;
        s.damage = damage * reference.max_hp() / base.max_hp();
        s.xp = 0;
        s.gold = 0;
        s.target = Some(session);
        s.state = "chase".into();
        s.atk_cd = 2.;
        let bodies = self.actor_bodies(ZONE, None, Some(enemy));
        let at = free_actor_position(&self.maps[ZONE], CENTRE, s.r, &bodies, true)
            .ok_or("Clear the middle of the ritual circle before summoning.")?;
        s.x = at.x;
        s.y = at.y;
        s.hx = CENTRE.x;
        s.hy = CENTRE.y;
        self.slimes[enemy] = s;
        self.halloween = Some(Run {
            members,
            enemy,
            started: self.time,
            away: 0.,
        });
        self.emit_zone(ZONE,json!({"type":"system","text":format!("The Hollow Rider rises at level {level}: the average of five fighters, rounded up.")}));
        Ok(())
    }
    pub(super) fn update_halloween(&mut self) {
        let active = self.seasonal.cached.iter().any(|e| e.id == "halloween");
        let Some(run) = self.halloween.as_mut() else {
            return;
        };
        let living = run.members.iter().any(|id| {
            self.players.values().any(|p| {
                p.character.id == *id
                    && p.character.hp > 0.
                    && p.character.zone == ZONE
                    && p.character.point().distance(CENTRE) < 25.
            })
        });
        if living {
            run.away = 0.;
        } else {
            run.away += TICK;
        }
        let reset = !active
            || run.away >= 8.
            || self.time - run.started > 900.
            || self.slimes[run.enemy].point().distance(CENTRE) > 13.;
        if reset {
            self.sleep_ambush(TAG);
            self.halloween = None;
            self.emit_zone(ZONE,json!({"type":"system","text":"The Hollow Rider fades. The haunted lantern falls silent."}));
        }
    }
    pub(super) fn halloween_killed(&mut self, enemy: usize) {
        let Some(run) = self.halloween.take() else {
            return;
        };
        if run.enemy != enemy {
            self.halloween = Some(run);
            return;
        }
        let seasons = self.seasonal.active();
        let Some(day) = crate::seasonal::period(QUEST, &seasons) else {
            return;
        };
        let quest = self
            .maps
            .iter()
            .flat_map(|m| &m.quests)
            .find(|q| q.id == QUEST)
            .cloned()
            .expect("Halloween daily quest");
        let sessions: Vec<_> = self
            .players
            .iter()
            .filter(|(_, p)| {
                run.members.contains(&p.character.id)
                    && p.merc.is_none()
                    && p.ambient.is_none()
                    && p.character.hp > 0.
                    && p.character.zone == ZONE
                    && p.character.point().distance(CENTRE) <= 18.
                    && p.character.seasonal_started.get(QUEST) == Some(&day)
                    && p.character
                        .quests
                        .iter()
                        .any(|q| q.id == QUEST && !q.claimed)
            })
            .map(|(id, _)| *id)
            .collect();
        for session in sessions {
            let roll = self.random();
            let p = self.players.get_mut(&session).unwrap();
            quest_progress(&mut p.character, std::slice::from_ref(&quest), "kill", KIND);
            if p.character.seasonal_rolls.get(QUEST) != Some(&day) {
                p.character.seasonal_rolls.insert(QUEST.into(), day);
                if wins_mount(roll) && p.character.grant_mount("nightmare") {
                    let _=p.peer.try_send(json!({"type":"notice","ok":true,"text":"The Hollow Rider dropped a Nightmare Steed! It is permanently added to your mounts."}));
                } else {
                    let _=p.peer.try_send(json!({"type":"notice","ok":true,"text":"Your daily 1% Nightmare Steed roll is complete. Return to any city festival host."}));
                }
            }
        }
        self.save();
    }
}
