//! Temporary adventurers in shared maps occupied by real players. They use the normal Player combat and movement
//! code, but have no account, socket, save, party seat or dungeon access.
use super::*;
use std::collections::VecDeque;

const NAMES: &str = include_str!("../../../world/ambient_names.txt");
const CLASSES: [Class; 5] = [
    Class::Warrior,
    Class::Mage,
    Class::Assassin,
    Class::Priest,
    Class::Hunter,
];
const FIELD_CHAT: [&str; 10] = [
    "taking the long way around this time",
    "bags are nearly full again",
    "one more pull, then back to town",
    "the view out here is worth the walk",
    "that was closer than it looked",
    "need to mend this gear soon",
    "anyone seen the big one today?",
    "going to try the eastern trail",
    "these things keep coming back",
    "just checking the map a moment",
];
const TOWN_CHAT: [&str; 8] = [
    "selling a few things, then heading out",
    "anyone know a good route from here?",
    "finally made it back in one piece",
    "taking a breather before the next run",
    "I should have packed more potions",
    "the market is busy today",
    "need to sort these bags first",
    "heading out again in a minute",
];

pub(super) struct Ambient {
    phase: AmbientPhase,
    hub: Point,
    quest: Option<String>,
    route: VecDeque<Point>,
    kills_at_departure: u32,
    kills_per_trip: u32,
    hub_retry_at: f64,
    hub_wait: f64,
    hub_handled: bool,
    next_think: f64,
    next_chat: f64,
    last_point: Point,
    stuck_for: f64,
}

impl Ambient {
    pub(super) fn hub(&self) -> Point {
        self.hub
    }
    pub(super) fn on_respawn(&mut self, time: f64, point: Point) {
        self.phase = AmbientPhase::Hub;
        self.route.clear();
        self.hub_wait = time + 4.;
        self.hub_handled = false;
        self.next_think = time;
        self.last_point = point;
        self.stuck_for = 0.;
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum AmbientPhase {
    Farming,
    Returning,
    Hub,
}

fn ambient_quest_matches(target: &str, kind: &str) -> bool {
    target == kind
        || target == "any"
        || (target == "slime" && ["green", "blue", "pink", "yellow"].contains(&kind))
}

impl World {
    pub(super) fn visible_online(&self) -> usize {
        self.players.values().filter(|p| p.merc.is_none()).count()
    }

    pub(super) fn update_ambient(&mut self) {
        if !self.ambient_enabled {
            return;
        }
        let mut occupied: BTreeMap<usize, Vec<Point>> = BTreeMap::new();
        for p in self
            .players
            .values()
            .filter(|p| p.merc.is_none() && p.ambient.is_none())
        {
            if !self.is_instance(p.character.zone) {
                occupied
                    .entry(p.character.zone)
                    .or_default()
                    .push(p.character.point());
            }
        }
        self.ambient_targets
            .retain(|zone, _| occupied.contains_key(zone));
        let stale: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.ambient.is_some() && !occupied.contains_key(&p.character.zone))
            .map(|(session, _)| *session)
            .collect();
        for session in stale {
            if let Some(p) = self.players.remove(&session) {
                self.social_left(&p.character.id, &p.character.look.name, &[]);
            }
        }
        for (zone, _) in occupied {
            if !self.ambient_targets.contains_key(&zone) {
                let wanted = 3 + (self.random() * 4.) as usize;
                self.ambient_targets.insert(zone, wanted);
            }
            let wanted = self.ambient_targets[&zone];
            let current = self
                .players
                .values()
                .filter(|p| p.ambient.is_some() && p.character.zone == zone)
                .count();
            // One arrival every half second looks like people entering the map instead of a whole crowd popping in.
            if current < wanted && self.tick % 10 == 1 {
                self.spawn_ambient(zone);
            }
        }
        let sessions: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.ambient.is_some())
            .map(|(session, _)| *session)
            .collect();
        for session in sessions {
            self.ambient_think(session);
        }
    }

    fn ambient_levels(&self, zone: usize) -> [u32; 2] {
        self.maps[zone].levels.unwrap_or_else(|| {
            let levels: Vec<u32> = self.maps[zone].quests.iter().map(|q| q.level).collect();
            [
                levels.iter().copied().min().unwrap_or(1),
                levels.iter().copied().max().unwrap_or(5),
            ]
        })
    }

    fn ambient_name(&mut self) -> String {
        let names: Vec<&str> = NAMES.lines().filter(|name| !name.is_empty()).collect();
        let start = (self.random() * names.len() as f64) as usize;
        for offset in 0..names.len() {
            let name = names[(start + offset) % names.len()];
            if self
                .players
                .values()
                .all(|p| !p.character.look.name.eq_ignore_ascii_case(name))
            {
                return name.to_owned();
            }
        }
        format!("Traveler{}", self.merc_seq)
    }

    fn ambient_safe_point(&self, zone: usize, point: Point, city: bool) -> bool {
        let map = &self.maps[zone];
        let mut checked = point;
        map.collide(&mut checked, PLAYER_RADIUS);
        point.distance(checked) < 0.01
            && map.in_city(point) == city
            && map
                .portals
                .iter()
                .all(|g| point.distance(Point { x: g.x, y: g.y }) >= g.r + 1.)
            && self
                .players
                .values()
                .all(|p| p.character.zone != zone || p.character.point().distance(point) >= 2.)
            && self
                .slimes
                .iter()
                .all(|s| s.dead || s.zone != zone || s.point().distance(point) >= 2.5)
    }

    /// New arrivals begin in different hunting grounds, not gathered around whichever hub the real player uses.
    fn ambient_field_spot(&mut self, zone: usize, level: u32) -> Point {
        let grounds: Vec<Point> = self
            .slimes
            .iter()
            .filter(|s| {
                s.zone == zone
                    && !s.dead
                    && !is_elite(&s.kind)
                    && s.level <= level + 3
                    && !self.maps[zone].in_city(s.point())
                    && self.spawns[s.id].ambush.is_none()
            })
            .map(Slime::point)
            .collect();
        for _ in 0..80 {
            let base = if grounds.is_empty() {
                Point {
                    x: 2. + self.random() * (self.maps[zone].size as f64 - 4.),
                    y: 2. + self.random() * (self.maps[zone].size as f64 - 4.),
                }
            } else {
                grounds[(self.random() * grounds.len() as f64) as usize]
            };
            let angle = self.random() * std::f64::consts::TAU;
            let distance = if grounds.is_empty() {
                0.
            } else {
                3. + self.random() * 5.
            };
            let point = Point {
                x: base.x + angle.cos() * distance,
                y: base.y + angle.sin() * distance,
            };
            if self.ambient_safe_point(zone, point, grounds.is_empty())
                && (grounds.is_empty()
                    || grounds.iter().any(|ground| {
                        point.distance(*ground) < 9.
                            && pursuit::clear_line(&self.maps[zone], point, *ground, PLAYER_RADIUS)
                    }))
            {
                return point;
            }
        }
        // This is only reached if an occupied map offers no suitable random ground. Its normal spawn is already
        // collision-safe; the next decision still routes this adventurer toward an enemy or townsperson.
        let mut point = self.maps[zone].spawn;
        self.maps[zone].collide(&mut point, PLAYER_RADIUS);
        point
    }

    fn ambient_hub(&mut self, zone: usize, quest: Option<&str>) -> Point {
        let map = &self.maps[zone];
        let giver = quest
            .and_then(|id| map.quests.iter().find(|q| q.id == id))
            .and_then(|q| map.npcs.iter().find(|n| n.id == q.npc))
            .or_else(|| {
                map.quests
                    .first()
                    .and_then(|q| map.npcs.iter().find(|n| n.id == q.npc))
            })
            .or_else(|| map.npcs.first());
        let base = giver.map_or(map.spawn, |npc| npc.position_at(self.time));
        let city = map.in_city(base);
        for _ in 0..24 {
            let angle = self.random() * std::f64::consts::TAU;
            let distance = 1.4 + self.random() * 0.8;
            let point = Point {
                x: base.x + angle.cos() * distance,
                y: base.y + angle.sin() * distance,
            };
            if self.ambient_safe_point(zone, point, city) {
                return point;
            }
        }
        let mut point = base;
        self.maps[zone].collide(&mut point, PLAYER_RADIUS);
        point
    }

    fn ambient_gear(&mut self, class: Class, kind: &str, level: u32) -> Option<String> {
        let choices: Vec<&Item> = ITEMS
            .iter()
            .filter(|i| {
                i.kind == kind
                    && i.class == (if kind == "pants" { None } else { Some(class) })
                    && i.required_level <= level
                    && matches!(i.rarity.as_str(), "common" | "uncommon" | "rare")
                    && i.variant.is_some()
            })
            .collect();
        let highest = choices.iter().map(|i| i.required_level).max()?;
        let at_level: Vec<&Item> = choices
            .into_iter()
            .filter(|i| i.required_level == highest)
            .collect();
        let index = (self.random() * at_level.len() as f64) as usize;
        Some(at_level[index].id.clone())
    }

    fn ambient_quest(
        &mut self,
        zone: usize,
        level: u32,
        character: &Character,
        giver: Option<&str>,
    ) -> Option<String> {
        let choices: Vec<String> = self.maps[zone]
            .quests
            .iter()
            .filter(|q| {
                q.level <= level + 2
                    && q.objectives.len() == 1
                    && q.objectives[0].kind == "kill"
                    && giver.is_none_or(|id| q.npc == id)
                    && q.unlocked(character)
                    && !character
                        .quests
                        .iter()
                        .any(|p| p.id == q.id && (!p.claimed || !q.repeatable))
                    && self.maps[zone].npcs.iter().any(|n| n.id == q.npc)
                    && self.slimes.iter().any(|s| {
                        s.zone == zone
                            && !is_elite(&s.kind)
                            && s.level <= level + 3
                            && ambient_quest_matches(&q.objectives[0].target, &s.kind)
                    })
            })
            .map(|q| q.id.clone())
            .collect();
        (!choices.is_empty())
            .then(|| choices[(self.random() * choices.len() as f64) as usize].clone())
    }

    fn spawn_ambient(&mut self, zone: usize) {
        let name = self.ambient_name();
        let class = CLASSES[(self.random() * CLASSES.len() as f64) as usize];
        let [low, high] = self.ambient_levels(zone);
        let level = low + (self.random() * (high - low + 1) as f64) as u32;
        let point = self.ambient_field_spot(zone, level);
        let mut character = Character::mercenary(class, level, &name);
        character.look.gender = if self.random() < 0.5 {
            Gender::Female
        } else {
            Gender::Male
        };
        character.look.hair_color = (self.random() * 6.) as u8;
        character.look.skin = (self.random() * 4.) as u8;
        character.zone = zone;
        character.x = point.x;
        character.y = point.y;
        // A field arrival has already picked up work before the real player joined this map. Only these disposable
        // characters get an in-memory prior quest; subsequent hub visits use the ordinary interaction path.
        let quest = self
            .ambient_quest(zone, level, &character, None)
            .or_else(|| {
                self.maps[zone]
                    .quests
                    .iter()
                    .find(|q| {
                        q.objectives.len() == 1
                            && q.objectives[0].kind == "kill"
                            && q.level <= level + 2
                            && self.slimes.iter().any(|s| {
                                s.zone == zone
                                    && !is_elite(&s.kind)
                                    && ambient_quest_matches(&q.objectives[0].target, &s.kind)
                            })
                    })
                    .map(|q| q.id.clone())
            });
        if let Some(q) = quest
            .as_ref()
            .and_then(|id| self.maps[zone].quests.iter().find(|q| &q.id == id))
        {
            if let Some(required) = &q.requires {
                character.quests.push(QuestProgress {
                    id: required.clone(),
                    counts: vec![],
                    claimed: true,
                    completions: 1,
                });
            }
            let _ = quest_action(&mut character, q, "accept");
        }
        let hub = self.ambient_hub(zone, quest.as_deref());
        let mut worn = BTreeMap::new();
        for (kind, slot) in [
            ("armor", "chest"),
            ("weapon", "hands"),
            ("headgear", "headgear"),
            ("shoulders", "shoulders"),
            ("gloves", "gloves"),
            ("pants", "pants"),
        ] {
            if let Some(id) = self.ambient_gear(class, kind, level) {
                character.add_item(&id, 1);
                worn.insert(slot.to_owned(), id);
            }
        }
        let _ = character.equip_slots(&worn);
        character.hp = character.max_hp();
        character.reset_resource();
        let session = mercs::MERC_BASE + self.merc_seq;
        self.merc_seq += 1;
        let (peer, _unused) = mpsc::channel(1);
        let mut player = Player::new(character, peer);
        player.ambient = Some(Ambient {
            phase: AmbientPhase::Farming,
            hub,
            quest,
            route: VecDeque::new(),
            kills_at_departure: 0,
            kills_per_trip: 3 + (self.random() * 4.) as u32,
            hub_retry_at: 0.,
            hub_wait: 0.,
            hub_handled: false,
            next_think: self.time + self.random(),
            next_chat: self.time + 45. + self.random() * 75.,
            last_point: point,
            stuck_for: 0.,
        });
        self.players.insert(session, player);
    }

    fn ambient_route(&mut self, session: u64, to: Point) -> bool {
        let p = &self.players[&session];
        let from = p.character.point();
        let zone = p.character.zone;
        let route = if pursuit::clear_line(&self.maps[zone], from, to, PLAYER_RADIUS) {
            Some(vec![to])
        } else {
            self.pursuit
                .route(&self.maps[zone], zone, from, to, PLAYER_RADIUS)
        };
        let Some(route) = route else {
            return false;
        };
        let p = self.players.get_mut(&session).unwrap();
        p.goal = None;
        p.target = None;
        p.ambient.as_mut().unwrap().route = route.into();
        true
    }

    /// Returns true when the final waypoint has been reached.
    fn ambient_route_step(&mut self, session: u64) -> bool {
        let p = self.players.get_mut(&session).unwrap();
        if p.goal
            .is_some_and(|goal| p.character.point().distance(goal) > 0.55)
        {
            return false;
        }
        p.goal = p.ambient.as_mut().unwrap().route.pop_front();
        p.goal.is_none()
    }

    fn ambient_enemies(&self, session: u64, me: Point, zone: usize, level: u32) -> Vec<usize> {
        let quest_target = self.players[&session]
            .ambient
            .as_ref()
            .and_then(|brain| brain.quest.as_ref())
            .and_then(|id| self.maps[zone].quests.iter().find(|q| &q.id == id))
            .and_then(|q| q.objectives.first())
            .map(|o| o.target.as_str());
        let mut choices: Vec<&Slime> = self
            .slimes
            .iter()
            .filter(|s| {
                !s.dead
                    && s.zone == zone
                    && !is_elite(&s.kind)
                    && s.level <= level + 3
                    && s.target.is_none_or(|target| target == session)
                    && me.distance(s.point()) < 100.
                    && self
                        .players
                        .iter()
                        .all(|(other, p)| *other == session || p.target != Some(s.id))
            })
            .collect();
        let score = |s: &Slime| {
            me.distance(s.point())
                + if quest_target.is_some_and(|target| ambient_quest_matches(target, &s.kind)) {
                    -5.
                } else {
                    4.
                }
        };
        choices.sort_by(|a, b| score(a).total_cmp(&score(b)));
        choices.into_iter().take(6).map(|s| s.id).collect()
    }

    /// Returns false after a turn-in so the actor pauses, then asks the same giver for its next available job.
    fn ambient_hub_interact(&mut self, session: u64) -> bool {
        let zone = self.players[&session].character.zone;
        let brain = self.players[&session].ambient.as_ref().unwrap();
        let current = brain.quest.clone();
        let hub = brain.hub;
        let giver = current
            .as_ref()
            .and_then(|id| self.maps[zone].quests.iter().find(|q| &q.id == id))
            .map(|q| q.npc.clone())
            .or_else(|| {
                self.maps[zone]
                    .npcs
                    .iter()
                    .filter(|npc| self.maps[zone].quests.iter().any(|q| q.npc == npc.id))
                    .min_by(|a, b| {
                        a.position_at(self.time)
                            .distance(hub)
                            .total_cmp(&b.position_at(self.time).distance(hub))
                    })
                    .map(|npc| npc.id.clone())
            });
        let Some(npc) = giver else {
            return true;
        };
        if let Some(id) = current {
            let Some(quest) = self.maps[zone].quests.iter().find(|q| q.id == id) else {
                return true;
            };
            let progress = self.players[&session]
                .character
                .quests
                .iter()
                .find(|p| p.id == id);
            if progress.is_some_and(|p| quest.ready(p)) {
                self.interact(session, &npc, Some(&format!("quest:claim:{id}")));
                if self.players[&session]
                    .character
                    .quests
                    .iter()
                    .any(|p| p.id == id && p.claimed)
                {
                    let level = self.players[&session].character.level;
                    let character = self.players[&session].character.clone();
                    let next = self.ambient_quest(zone, level, &character, None);
                    let next_hub = next.as_ref().map(|id| self.ambient_hub(zone, Some(id)));
                    let brain = self
                        .players
                        .get_mut(&session)
                        .unwrap()
                        .ambient
                        .as_mut()
                        .unwrap();
                    brain.quest = next;
                    if let Some(hub) = next_hub {
                        brain.hub = hub;
                    }
                    return false;
                }
                return true;
            }
            if progress.is_none_or(|p| p.claimed) {
                self.interact(session, &npc, Some(&format!("quest:accept:{id}")));
            } else {
                self.interact(session, &npc, None);
            }
            return true;
        }
        let level = self.players[&session].character.level;
        let character = self.players[&session].character.clone();
        if let Some(id) = self.ambient_quest(zone, level, &character, Some(&npc)) {
            self.interact(session, &npc, Some(&format!("quest:accept:{id}")));
            self.players
                .get_mut(&session)
                .unwrap()
                .ambient
                .as_mut()
                .unwrap()
                .quest = Some(id);
        } else {
            self.interact(session, &npc, None);
        }
        true
    }

    fn ambient_think(&mut self, session: u64) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        if p.character.hp <= 0. {
            return;
        }
        let me = p.character.point();
        let zone = p.character.zone;
        let phase = p.ambient.as_ref().unwrap().phase;
        let target = p.target.filter(|id| {
            self.slimes.get(*id).is_some_and(|s| {
                !s.dead && s.zone == zone && s.target.is_none_or(|target| target == session)
            })
        });
        let chat_due = p.ambient.as_ref().unwrap().next_chat <= self.time
            && target.is_none()
            && p.combat_left <= 0.
            && self.players.values().any(|other| {
                other.merc.is_none()
                    && other.ambient.is_none()
                    && other.character.zone == zone
                    && other.character.point().distance(me) < 18.
            });
        if chat_due {
            let lines: &[&str] = if self.maps[zone].in_city(me) {
                &TOWN_CHAT
            } else {
                &FIELD_CHAT
            };
            let line = lines[(self.random() * lines.len() as f64) as usize];
            let next_chat = self.time + 120. + self.random() * 120.;
            let p = self.players.get_mut(&session).unwrap();
            p.ambient.as_mut().unwrap().next_chat = next_chat;
            let name = p.character.look.name.clone();
            let id = p.character.id.clone();
            self.emit_zone(zone, json!({"type":"chat","name":name,"id":id,"text":line}));
        }
        if self.tick.is_multiple_of(10) && target.is_some() {
            self.ai_combat(session, &[session], target);
        }
        let now = self.time;
        let hub_delay = 2. + ((session ^ self.tick) % 5) as f64 * 0.5;
        let next_trip_kills = 3 + ((session.wrapping_add(self.tick / 20)) % 4) as u32;
        let p = self.players.get_mut(&session).unwrap();
        let brain = p.ambient.as_mut().unwrap();
        if p.goal.is_some() && me.distance(brain.last_point) < 0.01 {
            brain.stuck_for += TICK;
        } else {
            brain.stuck_for = 0.;
        }
        brain.last_point = me;
        if brain.stuck_for > 2. {
            p.goal = None;
            brain.route.clear();
            brain.next_think = now + 1.;
            brain.stuck_for = 0.;
        }
        p.target = target;
        match phase {
            AmbientPhase::Hub => {
                p.target = None;
                p.goal = None;
                if now < brain.hub_wait {
                    return;
                }
                let hub = brain.hub;
                if me.distance(hub) > 2.5 {
                    if self.ambient_route(session, hub) {
                        self.players
                            .get_mut(&session)
                            .unwrap()
                            .ambient
                            .as_mut()
                            .unwrap()
                            .phase = AmbientPhase::Returning;
                        self.ambient_route_step(session);
                    } else {
                        let brain = self
                            .players
                            .get_mut(&session)
                            .unwrap()
                            .ambient
                            .as_mut()
                            .unwrap();
                        brain.quest = None;
                        brain.hub = me;
                    }
                    return;
                }
                if !brain.hub_handled {
                    let handled = self.ambient_hub_interact(session);
                    let brain = self
                        .players
                        .get_mut(&session)
                        .unwrap()
                        .ambient
                        .as_mut()
                        .unwrap();
                    brain.hub_handled = handled;
                    brain.hub_wait = now + if handled { hub_delay } else { 0.8 };
                    return;
                }
                let p = self.players.get_mut(&session).unwrap();
                let brain = p.ambient.as_mut().unwrap();
                brain.phase = AmbientPhase::Farming;
                brain.kills_at_departure = p.character.kills;
                brain.kills_per_trip = next_trip_kills;
                brain.next_think = now;
            }
            AmbientPhase::Returning => {
                let hub = brain.hub;
                if me.distance(hub) < 2.5 {
                    p.goal = None;
                    brain.route.clear();
                    brain.phase = AmbientPhase::Hub;
                    brain.hub_wait = now + hub_delay;
                    brain.hub_handled = false;
                    return;
                }
                if target.is_some() {
                    return;
                }
                if brain.route.is_empty() && p.goal.is_none() {
                    if now < brain.next_think {
                        return;
                    }
                    if !self.ambient_route(session, hub) {
                        self.players
                            .get_mut(&session)
                            .unwrap()
                            .ambient
                            .as_mut()
                            .unwrap()
                            .next_think = now + 10.;
                        return;
                    }
                }
                self.ambient_route_step(session);
                return;
            }
            AmbientPhase::Farming => {}
        }
        let (quest_ready, trip_done, hub, hub_retry_at, on_route, next_think, level) = {
            let p = &self.players[&session];
            let brain = p.ambient.as_ref().unwrap();
            let quest_ready = brain
                .quest
                .as_ref()
                .and_then(|id| self.maps[zone].quests.iter().find(|q| &q.id == id))
                .is_some_and(|q| {
                    p.character
                        .quests
                        .iter()
                        .find(|progress| progress.id == q.id)
                        .is_some_and(|progress| q.ready(progress))
                });
            (
                quest_ready,
                p.character.kills >= brain.kills_at_departure + brain.kills_per_trip,
                brain.hub,
                brain.hub_retry_at,
                !brain.route.is_empty() || p.goal.is_some(),
                brain.next_think,
                p.character.level,
            )
        };
        if (quest_ready || trip_done) && self.maps[zone].city.is_some() && now >= hub_retry_at {
            if self.ambient_route(session, hub) {
                self.players
                    .get_mut(&session)
                    .unwrap()
                    .ambient
                    .as_mut()
                    .unwrap()
                    .phase = AmbientPhase::Returning;
                self.ambient_route_step(session);
                return;
            }
            self.players
                .get_mut(&session)
                .unwrap()
                .ambient
                .as_mut()
                .unwrap()
                .hub_retry_at = now + 15.;
        }
        if target.is_some() {
            return;
        }
        if on_route {
            self.ambient_route_step(session);
            return;
        }
        if now < next_think {
            return;
        }
        for id in self.ambient_enemies(session, me, zone, level) {
            let at = self.slimes[id].point();
            if me.distance(at) < 12. && pursuit::clear_line(&self.maps[zone], me, at, PLAYER_RADIUS)
            {
                let p = self.players.get_mut(&session).unwrap();
                p.target = Some(id);
                p.goal = None;
                p.ambient.as_mut().unwrap().next_think = now + 1.;
                return;
            }
            if self.ambient_route(session, at) {
                self.ambient_route_step(session);
                self.players
                    .get_mut(&session)
                    .unwrap()
                    .ambient
                    .as_mut()
                    .unwrap()
                    .next_think = now + 1.;
                return;
            }
        }
        // Peaceful cities have no mobs: walk between townspeople and pause beside them instead of idling in a pack.
        let npcs: Vec<Point> = self.maps[zone]
            .npcs
            .iter()
            .map(|npc| npc.position_at(now))
            .filter(|at| me.distance(*at) > 5.)
            .collect();
        if !npcs.is_empty() && self.maps[zone].slimes.is_empty() {
            let at = npcs[(self.random() * npcs.len() as f64) as usize];
            let _ = self.ambient_route(session, at);
            self.ambient_route_step(session);
        }
        self.players
            .get_mut(&session)
            .unwrap()
            .ambient
            .as_mut()
            .unwrap()
            .next_think = now + 2. + self.random() * 3.;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    fn world() -> World {
        let mut w =
            World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
        w.rng = 12345;
        w.ambient_enabled = true;
        w.god_mode = true;
        w
    }

    fn join(w: &mut World, session: u64) -> mpsc::Receiver<Value> {
        let (peer, rx) = mpsc::channel(4096);
        w.join(session, None, Some(Look::default()), peer).unwrap();
        rx
    }

    fn ambient(w: &World, zone: usize) -> Vec<&Player> {
        w.players
            .values()
            .filter(|p| p.ambient.is_some() && p.character.zone == zone)
            .collect()
    }

    #[test]
    fn name_pool_has_one_hundred_distinct_valid_player_names() {
        let names: Vec<_> = NAMES.lines().collect();
        assert_eq!(names.len(), 100);
        assert_eq!(names.iter().collect::<HashSet<_>>().len(), 100);
        assert!(
            names
                .iter()
                .all(|name| (2..=16).contains(&name.chars().count()) && !name.contains("[GM]"))
        );
    }

    #[test]
    fn occupied_shared_map_gets_three_to_six_unsaved_adventurers_with_varied_looks() {
        let mut w = world();
        let _rx = join(&mut w, 1);
        for _ in 0..140 {
            w.step();
        }
        let bots = ambient(&w, 0);
        assert!((3..=6).contains(&bots.len()));
        assert_eq!(w.humans_online(), 1);
        assert_eq!(w.visible_online(), bots.len() + 1);
        assert_eq!(w.snapshot()["humansOnline"], 1);
        assert_eq!(
            w.snapshot_for(0)["players"].as_array().unwrap().len(),
            bots.len() + 1
        );
        let names: HashSet<_> = bots
            .iter()
            .map(|p| p.character.look.name.as_str())
            .collect();
        assert_eq!(names.len(), bots.len());
        assert!(bots.iter().all(|p| (1..=5).contains(&p.character.level)
            && p.character.look.validate().is_ok()
            && p.merc.is_none()));
        assert!(bots.iter().all(|p| !w.maps[0].in_city(p.character.point())));
        assert!(
            bots.iter()
                .all(|p| p.ambient.as_ref().unwrap().quest.is_some())
        );
        w.save();
        assert_eq!(
            w.store
                .conn()
                .query_row("SELECT COUNT(*) FROM characters", [], |r| r
                    .get::<_, u32>(0))
                .unwrap(),
            1
        );
    }

    #[test]
    fn bots_leave_empty_maps_and_never_enter_private_instances() {
        let mut w = world();
        let _rx = join(&mut w, 1);
        for _ in 0..120 {
            w.step();
        }
        assert!(!ambient(&w, 0).is_empty());
        w.players.get_mut(&1).unwrap().character.zone = 5;
        w.update_ambient();
        assert!(ambient(&w, 0).is_empty());
        assert!(ambient(&w, 5).is_empty());
        assert!(w.ambient_targets.is_empty());
        let city = w.maps[4].city.as_ref().unwrap();
        let plaza = Point {
            x: (city.x0 + city.x1) * 0.5,
            y: (city.y0 + city.y1) * 0.5,
        };
        let real = w.players.get_mut(&1).unwrap();
        real.character.zone = 4;
        real.character.x = plaza.x;
        real.character.y = plaza.y;
        for _ in 0..120 {
            w.step();
        }
        let bots = ambient(&w, 4);
        assert!((3..=6).contains(&bots.len()));
        assert!(bots.iter().all(|p| (11..=20).contains(&p.character.level)));
        assert!(bots.iter().all(|p| w.maps[4].in_city(p.character.point())));
        let first: Vec<_> = bots
            .iter()
            .map(|p| (p.character.id.clone(), p.character.point()))
            .collect();
        for _ in 0..240 {
            w.step();
        }
        assert!(first.iter().any(|(id, at)| {
            ambient(&w, 4)
                .iter()
                .any(|p| &p.character.id == id && p.character.point().distance(*at) > 2.)
        }));
    }

    #[test]
    fn a_defeated_adventurer_keeps_its_identity_respawns_at_the_hub_then_leaves() {
        let mut w = world();
        let _rx = join(&mut w, 1);
        for _ in 0..120 {
            w.step();
        }
        let wanted = ambient(&w, 0).len();
        let (session, dead) = w.players.iter().find(|(_, p)| p.ambient.is_some()).unwrap();
        let (session, id, hub) = (
            *session,
            dead.character.id.clone(),
            dead.ambient.as_ref().unwrap().hub,
        );
        w.players.get_mut(&session).unwrap().character.hp = 0.;
        for _ in 0..70 {
            w.step();
        }
        let revived = &w.players[&session];
        assert_eq!(revived.character.id, id);
        assert!(revived.character.hp > 0.);
        assert!(revived.character.point().distance(hub) < 0.5);
        assert_eq!(revived.ambient.as_ref().unwrap().phase, AmbientPhase::Hub);
        for _ in 0..240 {
            w.step();
        }
        assert_eq!(ambient(&w, 0).len(), wanted);
        assert!(w.players[&session].character.point().distance(hub) > 3.);
        assert_eq!(
            w.players[&session].ambient.as_ref().unwrap().phase,
            AmbientPhase::Farming
        );
    }

    #[test]
    fn a_ready_field_quest_is_claimed_after_visiting_its_giver() {
        let mut w = world();
        let _rx = join(&mut w, 1);
        for _ in 0..100 {
            w.step();
        }
        let (session, bot) = w
            .players
            .iter()
            .find(|(_, p)| {
                p.ambient
                    .as_ref()
                    .is_some_and(|brain| brain.quest.is_some())
            })
            .unwrap();
        let (session, quest_id, hub) = (
            *session,
            bot.ambient.as_ref().unwrap().quest.clone().unwrap(),
            bot.ambient.as_ref().unwrap().hub,
        );
        let quest = w.maps[0].quests.iter().find(|q| q.id == quest_id).unwrap();
        let needed = quest.objectives[0].count;
        let p = w.players.get_mut(&session).unwrap();
        p.character.x = hub.x;
        p.character.y = hub.y;
        p.target = None;
        p.goal = None;
        let progress = p
            .character
            .quests
            .iter_mut()
            .find(|q| q.id == quest_id)
            .unwrap();
        progress.counts[0] = needed;
        for _ in 0..130 {
            w.step();
        }
        assert!(
            w.players[&session]
                .character
                .quests
                .iter()
                .any(|q| q.id == quest_id && q.claimed)
        );
        assert_eq!(
            w.store
                .conn()
                .query_row("SELECT COUNT(*) FROM characters", [], |r| r
                    .get::<_, u32>(0))
                .unwrap(),
            1
        );
    }

    #[test]
    fn a_bot_uses_real_attacks_against_a_mob_without_crediting_the_human() {
        let mut w = world();
        let _rx = join(&mut w, 1);
        for _ in 0..100 {
            w.step();
        }
        let bot = *w
            .players
            .iter()
            .find(|(_, p)| p.ambient.is_some())
            .unwrap()
            .0;
        let enemy = w
            .slimes
            .iter()
            .position(|s| s.zone == 0 && s.kind == "green" && !s.dead)
            .unwrap();
        let point = w.slimes[enemy].point();
        let mut stand = Point {
            x: point.x + 1.3,
            y: point.y,
        };
        w.maps[0].collide(&mut stand, PLAYER_RADIUS);
        let p = w.players.get_mut(&bot).unwrap();
        p.character.x = stand.x;
        p.character.y = stand.y;
        p.target = Some(enemy);
        let before = w.slimes[enemy].hp;
        for _ in 0..70 {
            w.step();
        }
        assert!(w.slimes[enemy].hp < before || w.slimes[enemy].dead);
        assert_eq!(w.players[&1].character.kills, 0);
    }

    #[test]
    fn field_arrivals_seek_and_hit_mobs_without_manual_targets() {
        let mut w = world();
        let mut rx = join(&mut w, 1);
        for _ in 0..320 {
            w.step();
        }
        let ids: HashSet<_> = ambient(&w, 0)
            .iter()
            .map(|p| p.character.id.as_str())
            .collect();
        let events: Vec<_> = std::iter::from_fn(|| rx.try_recv().ok()).collect();
        assert!(events.iter().any(|packet| {
            packet["type"] == "event"
                && packet["kind"] == "hit"
                && packet["actor"].as_str().is_some_and(|id| ids.contains(id))
        }));
        assert_eq!(w.players[&1].character.kills, 0);
    }

    #[test]
    fn every_outdoor_quest_hub_has_a_collision_safe_route_to_mobs() {
        let mut w = world();
        for zone in [0, 1, 2, 3, 6, 7, 8, 13] {
            let quest = w.maps[zone]
                .quests
                .iter()
                .find(|q| q.objectives.iter().any(|o| o.kind == "kill"))
                .unwrap()
                .id
                .clone();
            let hub = w.ambient_hub(zone, Some(&quest));
            let mut targets: Vec<_> = w
                .slimes
                .iter()
                .filter(|s| s.zone == zone && !is_elite(&s.kind) && !s.dead)
                .map(Slime::point)
                .collect();
            targets.sort_by(|a, b| hub.distance(*a).total_cmp(&hub.distance(*b)));
            assert!(
                targets.into_iter().take(12).any(|target| {
                    w.pursuit
                        .route(&w.maps[zone], zone, hub, target, PLAYER_RADIUS)
                        .is_some()
                }),
                "{} has no route out of its quest hub",
                w.maps[zone].name
            );
        }
    }

    #[test]
    fn roster_lists_adventurers_and_they_decline_social_invitations() {
        let mut w = world();
        let mut rx = join(&mut w, 1);
        for _ in 0..100 {
            w.step();
        }
        let bot = ambient(&w, 0)[0].character.id.clone();
        w.social(1, SocialCommand::Who);
        let who = std::iter::from_fn(|| rx.try_recv().ok())
            .find(|packet| packet["type"] == "who")
            .unwrap();
        assert!(
            who["players"]
                .as_array()
                .unwrap()
                .iter()
                .any(|p| p["id"] == bot)
        );
        w.social(
            1,
            SocialCommand::FriendRequest {
                id: Some(bot),
                name: None,
            },
        );
        for _ in 0..80 {
            w.step();
        }
        let notices: Vec<_> = std::iter::from_fn(|| rx.try_recv().ok()).collect();
        assert!(notices.iter().any(|p| {
            p["text"]
                .as_str()
                .is_some_and(|s| s.contains("declined your friend request"))
        }));
    }
}
