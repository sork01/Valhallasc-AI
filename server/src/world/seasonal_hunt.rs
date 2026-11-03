//! Shared seasonal five-fighter hunts, frozen scaling and personal daily mount rolls.
use super::*;
#[derive(Clone, Copy)]
pub(super) struct Spec {
    pub season: &'static str,
    pub kind: &'static str,
    pub quest: &'static str,
    pub ritual: &'static str,
    pub summon: &'static str,
    pub mount: &'static str,
    pub name: &'static str,
    pub mount_name: &'static str,
    pub zone: usize,
    pub centre: Point,
    pub lantern: Point,
    pub tag: &'static str,
    pub average: bool,
    pub chance: f64,
}
pub(super) const HALLOWEEN: Spec = Spec {
    season: "halloween",
    kind: "hollow_rider",
    quest: "halloween_hunt",
    ritual: "halloween_lantern",
    summon: "halloween:summon",
    mount: "nightmare",
    name: "The Hollow Rider",
    mount_name: "Nightmare Steed",
    zone: 3,
    centre: Point { x: 105., y: 23. },
    lantern: Point { x: 105., y: 32. },
    tag: "halloween:hollow-rider",
    average: true,
    chance: 0.01,
};
pub(super) const CHRISTMAS: Spec = Spec {
    season: "christmas",
    kind: "grinch",
    quest: "christmas_hunt",
    ritual: "christmas_tree",
    summon: "christmas:summon",
    mount: "reindeer",
    name: "The Grinch",
    mount_name: "Red-nosed Reindeer",
    zone: 2,
    centre: Point { x: 103., y: 100. },
    lantern: Point { x: 112., y: 100. },
    tag: "christmas:grinch",
    average: false,
    chance: 0.05,
};
pub(super) const VALENTINE: Spec = Spec {
    season: "valentine",
    kind: "briarheart",
    quest: "valentine_hunt",
    ritual: "valentine_shrine",
    summon: "valentine:summon",
    mount: "roseheart",
    name: "The Briarheart",
    mount_name: "Roseheart Unicorn",
    zone: 2,
    centre: Point { x: 103., y: 100. },
    lantern: Point { x: 112., y: 100. },
    tag: "valentine:briarheart",
    average: false,
    chance: 0.,
};
pub(super) const EASTER: Spec = Spec {
    season: "easter",
    kind: "bloomwarden",
    quest: "easter_hunt",
    ritual: "easter_shrine",
    summon: "easter:summon",
    mount: "springtide",
    name: "The Bloomwarden",
    mount_name: "Springtide Bunny",
    zone: 2,
    centre: Point { x: 103., y: 100. },
    lantern: Point { x: 112., y: 100. },
    tag: "easter:bloomwarden",
    average: false,
    chance: 0.05,
};
pub(super) const SOLSTICE: Spec = Spec {
    season: "solstice",
    kind: "birchcrown",
    quest: "solstice_hunt",
    ritual: "solstice_pole",
    summon: "solstice:summon",
    mount: "sunwoven",
    name: "The Birchcrown Guardian",
    mount_name: "Sunwoven Stag",
    zone: 2,
    centre: Point { x: 103., y: 100. },
    lantern: Point { x: 112., y: 100. },
    tag: "solstice:birchcrown",
    average: false,
    chance: 0.05,
};
pub(super) const NEWYEAR: Spec = Spec {
    season: "newyear",
    kind: "starrocketeer",
    quest: "newyear_hunt",
    ritual: "newyear_launchpad",
    summon: "newyear:summon",
    mount: "rocket",
    name: "The Starfire Rocketeer",
    mount_name: "Starflight Rocket",
    zone: 2,
    centre: Point { x: 103., y: 100. },
    lantern: Point { x: 112., y: 100. },
    tag: "newyear:rocketeer",
    average: false,
    chance: 0.05,
};
pub(super) fn for_landmark(id: &str) -> Option<Spec> {
    [HALLOWEEN, CHRISTMAS, VALENTINE, EASTER, SOLSTICE, NEWYEAR]
        .into_iter()
        .find(|s| s.ritual == id)
}
pub(super) fn for_kind(kind: &str) -> Option<Spec> {
    [HALLOWEEN, CHRISTMAS, VALENTINE, EASTER, SOLSTICE, NEWYEAR]
        .into_iter()
        .find(|s| s.kind == kind)
}
pub(super) fn for_ritual(id: &str, offer: Option<&str>) -> Option<Spec> {
    [HALLOWEEN, CHRISTMAS, VALENTINE, EASTER, SOLSTICE, NEWYEAR]
        .into_iter()
        .find(|s| s.ritual == id && offer == Some(s.summon))
}
pub(super) struct Run {
    pub spec: Spec,
    pub members: Vec<String>,
    pub enemy: usize,
    pub started: f64,
    pub away: f64,
}
pub(super) fn wins_mount(roll: f64, chance: f64) -> bool {
    (0. ..chance).contains(&roll)
}
impl World {
    pub(super) fn festival_member(&self, kind: &str, session: u64) -> bool {
        self.seasonal_hunt.as_ref().is_some_and(|r| {
            r.spec.kind == kind
                && self
                    .players
                    .get(&session)
                    .is_some_and(|p| r.members.contains(&p.character.id))
        })
    }
    pub(super) fn festival_view(&self, spec: Spec) -> Value {
        let active = self.seasonal.cached.iter().any(|e| e.id == spec.season);
        if !active {
            return Value::Null;
        }
        let run = self
            .seasonal_hunt
            .as_ref()
            .filter(|r| r.spec.kind == spec.kind);
        json!({"summonX":spec.lantern.x,"summonY":spec.lantern.y,"zone":spec.zone,"x":spec.centre.x,"y":spec.centre.y,"radius":9.,"quest":spec.quest,"active":run.is_some(),"level":run.map(|r|self.slimes[r.enemy].level)})
    }
    pub(super) fn summon_festival(&mut self, session: u64, spec: Spec) -> Result<(), String> {
        let seasons = self.seasonal.active();
        let period = crate::seasonal::period(spec.quest, &seasons)
            .ok_or("This summon is only available during its festival.")?;
        if self.seasonal_hunt.is_some() {
            return Err(format!(
                "{} is already summoned. Wait for that encounter to finish.",
                spec.name
            ));
        }
        let p = self.players.get(&session).ok_or("Unknown fighter.")?;
        if p.character.zone != spec.zone
            || p.character.point().distance(spec.lantern) > 2.8
            || p.character.hp <= 0.
        {
            return Err(if spec.average {
                "Walk closer to the haunted lantern."
            } else {
                "Walk closer to the summoning landmark."
            }
            .into());
        }
        if !p
            .character
            .quests
            .iter()
            .any(|q| q.id == spec.quest && !q.claimed)
            || p.character.seasonal_started.get(spec.quest) != Some(&period)
        {
            return Err(format!("Accept {} daily quest in a city first.", spec.name));
        }
        let owner = p.character.id.clone();
        if spec.average && self.party_leader(&owner).is_some_and(|id| id != owner) {
            return Err("The party leader must light the haunted lantern.".into());
        }
        let members = self.party_mates(&owner);
        if members.len() != 5 {
            return Err("Gather exactly five living fighters, including hired fighters, at the ritual clearing.".into());
        }
        let mut levels = 0_u64;
        let mut highest = 0;
        for member in &members {
            let p = self
                .online(member)
                .ok_or("All five fighters must be online at the ritual clearing.")?;
            if p.ambient.is_some()
                || p.gauntlet
                || p.character.hp <= 0.
                || p.character.zone != spec.zone
                || p.character.point().distance(spec.centre) > 12.
                || p.character.mounted
                || p.character.spark_travel.is_some()
                || p.combat_left > 0.
            {
                return Err("All five fighters must gather alive, dismounted and out of combat at the ritual clearing.".into());
            }
            levels += u64::from(p.character.level);
            highest = highest.max(p.character.level);
        }
        let level = if spec.average {
            levels.div_ceil(5) as u32
        } else {
            highest
        };
        let enemy = self
            .spawns
            .iter()
            .position(|s| s.zone == spec.zone && s.ambush.as_deref() == Some(spec.tag))
            .ok_or("The ritual clearing is unavailable.")?;
        let mut s = Slime::with_level(enemy, &self.spawns[enemy], level);
        // Scale health with the reference attack curve and damage with player health.
        // This keeps the event a five-fighter encounter throughout the existing level curve.
        let reference = Character::mercenary(Class::Warrior, level.min(99), "Rider scale");
        let base = Character::mercenary(Class::Warrior, 1, "Rider base");
        let (health, damage, _, _) = Slime::stats(spec.kind);
        s.max_hp = (health * reference.stats().0 / base.stats().0).round();
        s.hp = s.max_hp;
        s.damage = damage * reference.max_hp() / base.max_hp();
        s.xp = 0;
        s.gold = 0;
        s.target = Some(session);
        s.state = "chase".into();
        s.atk_cd = 2.;
        let bodies = self.actor_bodies(spec.zone, None, Some(enemy));
        let at = free_actor_position(&self.maps[spec.zone], spec.centre, s.r, &bodies, true)
            .ok_or("Clear the middle of the ritual circle before summoning.")?;
        s.x = at.x;
        s.y = at.y;
        s.hx = spec.centre.x;
        s.hy = spec.centre.y;
        self.slimes[enemy] = s;
        self.seasonal_hunt = Some(Run {
            spec,
            members,
            enemy,
            started: self.time,
            away: 0.,
        });
        self.emit_zone(spec.zone,json!({"type":"system","text":if spec.average {format!("The Hollow Rider rises at level {level}: the average of five fighters, rounded up.")}else{format!("{} rises at level {level}: the highest level among the five fighters.",spec.name)}}));
        Ok(())
    }
    pub(super) fn update_festival_hunt(&mut self) {
        let Some(spec) = self.seasonal_hunt.as_ref().map(|r| r.spec) else {
            return;
        };
        let active = self.seasonal.cached.iter().any(|e| e.id == spec.season);
        let Some(run) = self.seasonal_hunt.as_mut() else {
            return;
        };
        let living = run.members.iter().any(|id| {
            self.players.values().any(|p| {
                p.character.id == *id
                    && p.character.hp > 0.
                    && p.character.zone == spec.zone
                    && p.character.point().distance(spec.centre) < 25.
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
            || self.slimes[run.enemy].point().distance(spec.centre) > 13.;
        if reset {
            self.sleep_ambush(spec.tag);
            self.seasonal_hunt = None;
            self.emit_zone(spec.zone,json!({"type":"system","text":format!("{} fades. The summoning place falls silent.",spec.name)}));
        }
    }
    pub(super) fn festival_killed(&mut self, enemy: usize) {
        let Some(run) = self.seasonal_hunt.take() else {
            return;
        };
        if run.enemy != enemy {
            self.seasonal_hunt = Some(run);
            return;
        }
        let spec = run.spec;
        let seasons = self.seasonal.active();
        let Some(day) = crate::seasonal::period(spec.quest, &seasons) else {
            self.sleep_ambush(spec.tag);
            return;
        };
        let quest = self
            .maps
            .iter()
            .flat_map(|m| &m.quests)
            .find(|q| q.id == spec.quest)
            .cloned()
            .expect("seasonal daily quest");
        let sessions: Vec<_> = self
            .players
            .iter()
            .filter(|(_, p)| {
                run.members.contains(&p.character.id)
                    && p.merc.is_none()
                    && p.ambient.is_none()
                    && p.character.hp > 0.
                    && p.character.zone == spec.zone
                    && p.character.point().distance(spec.centre) <= 18.
                    && p.character.seasonal_started.get(spec.quest) == Some(&day)
                    && p.character
                        .quests
                        .iter()
                        .any(|q| q.id == spec.quest && !q.claimed)
            })
            .map(|(id, _)| *id)
            .collect();
        for session in sessions {
            let roll = if spec.chance > 0. { self.random() } else { 1. };
            let p = self.players.get_mut(&session).unwrap();
            quest_progress(
                &mut p.character,
                std::slice::from_ref(&quest),
                "kill",
                spec.kind,
            );
            if spec.chance > 0. && p.character.seasonal_rolls.get(spec.quest) != Some(&day) {
                p.character.seasonal_rolls.insert(spec.quest.into(), day);
                if wins_mount(roll, spec.chance) && p.character.grant_mount(spec.mount) {
                    let _=p.peer.try_send(json!({"type":"notice","ok":true,"text":format!("{} dropped a {}! It is permanently added to your mounts.",spec.name,spec.mount_name)}));
                } else {
                    let _=p.peer.try_send(json!({"type":"notice","ok":true,"text":format!("Your daily {}% {} roll is complete. Return to any city festival host.",(spec.chance*100.).round(),spec.mount_name)}));
                }
            }
        }
        self.save();
    }
}
