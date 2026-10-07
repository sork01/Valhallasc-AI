//! Temporary adventurers in shared maps occupied by real players. They use the normal Player combat and movement
//! code, but have no account, socket, save, party seat or dungeon access.
use super::*;

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
    next_think: f64,
    next_chat: f64,
    last_point: Point,
    stuck_for: f64,
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
            .filter(|(_, p)| {
                p.ambient.is_some()
                    && (p.character.hp <= 0. || !occupied.contains_key(&p.character.zone))
            })
            .map(|(session, _)| *session)
            .collect();
        for session in stale {
            if let Some(p) = self.players.remove(&session) {
                self.social_left(&p.character.id, &p.character.look.name, &[]);
            }
        }
        for (zone, anchors) in occupied {
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
                self.spawn_ambient(zone, &anchors);
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

    fn ambient_spot(&mut self, zone: usize, anchors: &[Point]) -> Point {
        for _ in 0..40 {
            let anchor = anchors[(self.random() * anchors.len() as f64) as usize];
            let angle = self.random() * std::f64::consts::TAU;
            let distance = 6. + self.random() * 10.;
            let desired = Point {
                x: anchor.x + angle.cos() * distance,
                y: anchor.y + angle.sin() * distance,
            };
            let map = &self.maps[zone];
            let mut point = desired;
            map.collide(&mut point, PLAYER_RADIUS);
            if point.distance(desired) > 0.5
                || (map.in_city(anchor) && !map.in_city(point))
                || map
                    .portals
                    .iter()
                    .any(|g| point.distance(Point { x: g.x, y: g.y }) < g.r + 1.)
                || self
                    .players
                    .values()
                    .any(|p| p.character.zone == zone && p.character.point().distance(point) < 2.)
                || self
                    .slimes
                    .iter()
                    .any(|s| !s.dead && s.zone == zone && s.point().distance(point) < 3.)
            {
                continue;
            }
            return point;
        }
        // Players may share a tile. Their known-safe position is a better last resort than placing an arrival in a
        // building, outside the city, or on an enemy.
        anchors[0]
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

    fn spawn_ambient(&mut self, zone: usize, anchors: &[Point]) {
        let name = self.ambient_name();
        let class = CLASSES[(self.random() * CLASSES.len() as f64) as usize];
        let [low, high] = self.ambient_levels(zone);
        let level = low + (self.random() * (high - low + 1) as f64) as u32;
        let point = self.ambient_spot(zone, anchors);
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
            next_think: self.time + self.random() * 3.,
            next_chat: self.time + 45. + self.random() * 75.,
            last_point: point,
            stuck_for: 0.,
        });
        self.players.insert(session, player);
    }

    fn ambient_clear_path(&self, zone: usize, from: Point, to: Point) -> bool {
        let mut walked = from;
        let distance = from.distance(to);
        self.maps[zone].walk(&mut walked, from.direction(to), distance, PLAYER_RADIUS);
        walked.distance(to) < 0.6
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
        let target = p.target.filter(|id| {
            self.slimes.get(*id).is_some_and(|s| {
                !s.dead && s.zone == zone && s.target.is_none_or(|target| target == session)
            })
        });
        let chat_due = p
            .ambient
            .as_ref()
            .is_some_and(|brain| brain.next_chat <= self.time)
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
        if self.tick.is_multiple_of(10) {
            self.ai_combat(session, &[session], target);
        }
        let now = self.time;
        let p = self.players.get_mut(&session).unwrap();
        let brain = p.ambient.as_mut().unwrap();
        if p.goal.is_some() && me.distance(brain.last_point) < 0.01 {
            brain.stuck_for += TICK;
        } else {
            brain.stuck_for = 0.;
        }
        brain.last_point = me;
        if brain.stuck_for > 1.5 {
            p.goal = None;
            brain.next_think = now;
            brain.stuck_for = 0.;
        }
        p.target = target;
        if target.is_some() || now < brain.next_think {
            return;
        }
        let choose_fight = self.random() < 0.45;
        let enemy = if choose_fight {
            self.slimes
                .iter()
                .filter(|s| {
                    !s.dead
                        && s.zone == zone
                        && !is_elite(&s.kind)
                        && s.target.is_none()
                        && s.point().distance(me) < 11.
                        && self.ambient_clear_path(zone, me, s.point())
                        && self.players.iter().all(|(other, p)| {
                            *other == session || p.ambient.is_none() || p.target != Some(s.id)
                        })
                })
                .min_by(|a, b| me.distance(a.point()).total_cmp(&me.distance(b.point())))
                .map(|s| s.id)
        } else {
            None
        };
        let delay = 2. + self.random() * 3.;
        if let Some(id) = enemy {
            let p = self.players.get_mut(&session).unwrap();
            p.target = Some(id);
            p.goal = None;
            p.ambient.as_mut().unwrap().next_think = now + delay;
            return;
        }
        let wander = self.random() < 0.8;
        let goal = if wander {
            let angle = self.random() * std::f64::consts::TAU;
            let length = 2. + self.random() * 8.;
            let desired = Point {
                x: me.x + angle.cos() * length,
                y: me.y + angle.sin() * length,
            };
            let mut point = desired;
            self.maps[zone].collide(&mut point, PLAYER_RADIUS);
            (point.distance(desired) < 0.5
                && (!self.maps[zone].in_city(me) || self.maps[zone].in_city(point))
                && self.ambient_clear_path(zone, me, point))
            .then_some(point)
        } else {
            None
        };
        let p = self.players.get_mut(&session).unwrap();
        p.goal = goal;
        p.ambient.as_mut().unwrap().next_think = now + delay;
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
    }

    #[test]
    fn defeated_adventurers_are_replaced_to_keep_the_live_population() {
        let mut w = world();
        let _rx = join(&mut w, 1);
        for _ in 0..120 {
            w.step();
        }
        let wanted = ambient(&w, 0).len();
        let old_ids: Vec<_> = ambient(&w, 0)
            .iter()
            .map(|p| p.character.id.clone())
            .collect();
        let dead = w
            .players
            .values_mut()
            .find(|p| p.ambient.is_some())
            .unwrap();
        dead.character.hp = 0.;
        for _ in 0..20 {
            w.step();
        }
        let living = ambient(&w, 0);
        assert_eq!(living.len(), wanted);
        assert!(living.iter().all(|p| p.character.hp > 0.));
        assert!(living.iter().any(|p| !old_ids.contains(&p.character.id)));
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
