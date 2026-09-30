use crate::{model::*, store::Store};
use serde::Serialize;
use serde_json::{Value, json};
use std::collections::BTreeMap;
use tokio::sync::{mpsc, oneshot, watch};

pub type Peer = mpsc::Sender<Value>;
const KING_SPAWN_MIN: f64 = 300.;
const KING_SPAWN_MAX: f64 = 600.;
pub enum Command {
    Join {
        session: u64,
        token: Option<String>,
        look: Option<Look>,
        peer: Peer,
        reply: oneshot::Sender<Result<Value, String>>,
    },
    Message {
        session: u64,
        message: ClientMessage,
    },
    Leave {
        session: u64,
    },
    Shutdown {
        reply: oneshot::Sender<()>,
    },
}

struct Player {
    character: Character,
    peer: Peer,
    input: Point,
    input_at: f64,
    goal: Option<Point>,
    target: Option<usize>,
    face: Point,
    moving: bool,
    walk: f64,
    attack: f64,
    cooldown: f64,
    hit: bool,
    hurt: f64,
    last_hurt: f64,
    dead_time: f64,
    dash: f64,
    dash_cd: f64,
    dash_direction: Point,
    chat_at: f64,
    service_at: f64,
}
impl Player {
    fn new(character: Character, peer: Peer) -> Self {
        Self {
            character,
            peer,
            input: Point::default(),
            input_at: -99.,
            goal: None,
            target: None,
            face: normalize(1., 1.),
            moving: false,
            walk: 0.,
            attack: 0.,
            cooldown: 0.,
            hit: false,
            hurt: 0.,
            last_hurt: -99.,
            dead_time: 0.,
            dash: 0.,
            dash_cd: 0.,
            dash_direction: Point::default(),
            chat_at: -99.,
            service_at: -99.,
        }
    }
    fn snapshot(&self) -> Value {
        let c = &self.character;
        json!({"id":c.id,"look":c.look,"x":c.x,"y":c.y,"hp":c.hp,"maxHp":c.max_hp(),"level":c.level,
            "xp":c.xp,"xpNeed":c.xp_need(),"gold":c.gold,"kills":c.kills,"fx":self.face.x,"fy":self.face.y,
            "moving":self.moving,"walk":self.walk,"atkT":self.attack,"atkCd":self.cooldown,"hurtT":self.hurt,
            "dead":c.hp<=0.,"deadT":self.dead_time,"dashT":self.dash,"dashCd":self.dash_cd})
    }
    fn stop(&mut self) {
        self.input = Point::default();
        self.goal = None;
        self.target = None;
    }
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct Slime {
    id: usize,
    kind: String,
    x: f64,
    y: f64,
    hx: f64,
    hy: f64,
    hp: f64,
    max_hp: f64,
    r: f64,
    state: String,
    st: f64,
    dir: f64,
    hop: f64,
    hop_v: f64,
    hurt_t: f64,
    rec_t: f64,
    land_t: f64,
    dead: bool,
    die_t: f64,
    respawn: f64,
    atk_cd: f64,
    blink: f64,
    seed: f64,
    windup_time: f64,
    #[serde(skip)]
    target: Option<u64>,
    #[serde(skip)]
    goal: Point,
    #[serde(skip)]
    hit: bool,
}
impl Slime {
    fn stats(kind: &str) -> (f64, f64, f64, f64, u32) {
        match kind {
            "blue" => (80., 10., 2.4, 1.05, 16),
            "pink" => (70., 9., 2.1, 1., 15),
            "yellow" => (90., 11., 2.2, 1.05, 20),
            "big" => (600., 30., 2.2, 1.75, 75),
            "beetle" => (240., 22., 2.8, 1.3, 32),
            _ => (60., 8., 1.9, 1., 12),
        }
    }
    // Windup, recovery cooldown, charge speed, awareness radius.
    fn attack_profile(kind: &str) -> (f64, f64, f64, f64) {
        match kind {
            "big" => (0.35, 0.85, 8., 7.5),
            "beetle" => (0.4, 1.1, 7.5, 7.),
            _ => (0.45, 1.3, 6., 5.5),
        }
    }
    fn new(id: usize, s: &SlimeSpawn) -> Self {
        let (hp, _, _, scale, _) = Self::stats(&s.kind);
        Self {
            id,
            kind: s.kind.clone(),
            x: s.x,
            y: s.y,
            hx: s.x,
            hy: s.y,
            hp,
            max_hp: hp,
            r: 0.3 * scale,
            state: "idle".into(),
            st: 1.,
            dir: 1.,
            hop: 0.,
            hop_v: 0.,
            hurt_t: 0.,
            rec_t: 0.,
            land_t: 0.,
            dead: false,
            die_t: 0.,
            respawn: 0.,
            atk_cd: 1.,
            blink: 2.,
            seed: id as f64,
            windup_time: Self::attack_profile(&s.kind).0,
            target: None,
            goal: Point { x: s.x, y: s.y },
            hit: false,
        }
    }
    fn point(&self) -> Point {
        Point {
            x: self.x,
            y: self.y,
        }
    }
}
#[derive(Clone, Serialize)]
struct Bolt {
    id: u64,
    owner: u64,
    x: f64,
    y: f64,
    fx: f64,
    fy: f64,
    t: f64,
    color: &'static str,
    #[serde(skip)]
    damage: f64,
    #[serde(skip)]
    crit: bool,
}
#[derive(Clone, Serialize)]
struct Drop {
    id: u64,
    owner: String,
    x: f64,
    y: f64,
    z: f64,
    value: u32,
    t: f64,
    col: &'static str,
}

pub struct World {
    map: Map,
    store: Store,
    players: BTreeMap<u64, Player>,
    slimes: Vec<Slime>,
    bolts: Vec<Bolt>,
    drops: Vec<Drop>,
    // Failed disconnect writes are retried by the next periodic transaction.
    pending_saves: Vec<Character>,
    time: f64,
    tick: u64,
    rng: u64,
    next_entity: u64,
    next_king_spawn: f64,
}
impl World {
    pub fn new(store: Store) -> Self {
        let map = Map::default();
        let slimes = map
            .slimes
            .iter()
            .enumerate()
            .map(|(i, s)| {
                let mut enemy = Slime::new(i, s);
                if s.kind == "big" {
                    // Keep stable entity IDs while hiding kings until the world timer fires.
                    enemy.dead = true;
                    enemy.hp = 0.;
                    enemy.state = "waiting".into();
                    enemy.die_t = 2.;
                }
                enemy
            })
            .collect();
        let mut world = Self {
            map,
            store,
            players: BTreeMap::new(),
            slimes,
            bolts: vec![],
            drops: vec![],
            pending_saves: vec![],
            time: 0.,
            tick: 0,
            rng: u64::from_le_bytes(uuid::Uuid::new_v4().as_bytes()[..8].try_into().unwrap()),
            next_entity: 1,
            next_king_spawn: 0.,
        };
        world.next_king_spawn = world.king_spawn_delay();
        world
    }
    fn random(&mut self) -> f64 {
        self.rng = self.rng.wrapping_mul(6364136223846793005).wrapping_add(1);
        (self.rng >> 32) as f64 / 4294967296.
    }
    fn entity(&mut self) -> u64 {
        let id = self.next_entity;
        self.next_entity += 1;
        id
    }
    fn king_spawn_delay(&mut self) -> f64 {
        KING_SPAWN_MIN + self.random() * (KING_SPAWN_MAX - KING_SPAWN_MIN)
    }
    fn update_king_spawn(&mut self) {
        if self.time < self.next_king_spawn
            || self.slimes.iter().any(|s| s.kind == "big" && !s.dead)
        {
            return;
        }
        let locations: Vec<_> = self
            .slimes
            .iter()
            .filter(|s| s.kind == "big")
            .map(|s| s.id)
            .collect();
        if locations.is_empty() {
            return;
        }
        let id = locations[(self.random() * locations.len() as f64) as usize];
        self.slimes[id] = Slime::new(id, &self.map.slimes[id]);
        self.emit(json!({"type":"system","text":"A King Slime has emerged in Greenmeadow!"}));
    }
    fn emit(&self, value: Value) {
        for p in self.players.values() {
            let _ = p.peer.try_send(value.clone());
        }
    }
    fn event(&self, kind: &str, actor: &str, p: Point, value: f64, crit: bool) {
        self.emit(json!({"type":"event","kind":kind,"actor":actor,"x":p.x,"y":p.y,"value":value,"crit":crit}));
    }
    pub fn snapshot(&self) -> Value {
        json!({"type":"snapshot","tick":self.tick,"time":self.time,
        "players":self.players.values().map(Player::snapshot).collect::<Vec<_>>(), "slimes":self.slimes,
        "bolts":self.bolts,"drops":self.drops,"online":self.players.len()})
    }

    fn join(
        &mut self,
        session: u64,
        token: Option<String>,
        look: Option<Look>,
        peer: Peer,
    ) -> Result<Value, String> {
        if self.players.len() >= MAX_PLAYERS {
            return Err("This world is full. Try again later.".into());
        }
        let (mut c, issued) = if let Some(token) = token {
            let c = self
                .store
                .load(&token)
                .map_err(|e| {
                    tracing::error!(%e,"character load failed");
                    "Character storage is unavailable.".to_owned()
                })?
                .ok_or("This character key is invalid. Choose New Character to start again.")?;
            (c, None)
        } else {
            let mut look = look.ok_or("Create a character first.")?;
            look.name = look.name.trim().into();
            look.validate()?;
            let (c, token) = self.store.create(look, self.map.spawn).map_err(|e| {
                tracing::error!(%e,"character creation failed");
                "Could not save your character.".to_owned()
            })?;
            (c, Some(token))
        };
        if self.players.values().any(|p| p.character.id == c.id) {
            return Err("This character is already online in another window.".into());
        }
        if let Some(saved) = self.pending_saves.iter().rev().find(|p| p.id == c.id) {
            c = saved.clone();
        }
        let mut point = c.point();
        self.map.collide(&mut point, 0.3);
        c.x = point.x;
        c.y = point.y;
        let id = c.id.clone();
        let name = c.look.name.clone();
        self.players.insert(session, Player::new(c, peer));
        self.emit(json!({"type":"system","text":format!("{name} entered Greenmeadow.")}));
        Ok(json!({"type":"welcome","version":1,"id":id,"token":issued,"snapshot":self.snapshot()}))
    }
    fn leave(&mut self, session: u64) {
        if let Some(p) = self.players.remove(&session) {
            let name = p.character.look.name.clone();
            self.pending_saves.push(p.character);
            self.save();
            self.emit(json!({"type":"system","text":format!("{name} left Greenmeadow.")}));
        }
    }
    fn save(&mut self) {
        // Pending versions precede live versions; an online character always wins.
        match self.store.save_many(
            self.pending_saves
                .iter()
                .chain(self.players.values().map(|p| &p.character)),
        ) {
            Ok(()) => self.pending_saves.clear(),
            Err(e) => tracing::error!(%e,"save failed; retrying on next save tick"),
        }
    }
    fn message(&mut self, session: u64, message: ClientMessage) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        match message {
            ClientMessage::Input { dx, dy }
                if dx.is_finite() && dy.is_finite() && dx.abs() <= 1. && dy.abs() <= 1. =>
            {
                p.input = normalize(dx, dy);
                p.input_at = self.time;
                if dx != 0. || dy != 0. {
                    p.goal = None;
                    p.target = None;
                }
            }
            ClientMessage::Stop => p.stop(),
            ClientMessage::Move { x, y } if x.is_finite() && y.is_finite() => {
                p.goal = Some(Point {
                    x: x.clamp(0.7, self.map.size as f64 - 0.7),
                    y: y.clamp(0.7, self.map.size as f64 - 0.7),
                });
                p.target = None;
                p.input = Point::default();
            }
            ClientMessage::Target { id } if self.slimes.get(id).is_some_and(|s| !s.dead) => {
                p.target = Some(id);
                p.goal = None;
                p.input = Point::default();
            }
            ClientMessage::Attack { fx, fy } if fx.is_finite() && fy.is_finite() => {
                let face = normalize(fx, fy);
                if face.x != 0. || face.y != 0. {
                    p.face = face;
                }
                self.start_attack(session);
            }
            ClientMessage::Dash { dx, dy }
                if dx.is_finite()
                    && dy.is_finite()
                    && p.character.hp > 0.
                    && p.character.look.class == Class::Assassin
                    && p.dash_cd <= 0. =>
            {
                let dir = normalize(dx, dy);
                p.dash_direction = if dir.x == 0. && dir.y == 0. {
                    p.face
                } else {
                    dir
                };
                p.face = p.dash_direction;
                p.dash = 0.18;
                p.dash_cd = 1.2;
                p.attack = 0.;
                p.hurt = 0.;
                p.stop();
                let id = p.character.id.clone();
                let point = p.character.point();
                self.event("shadowstep", &id, point, 0., false);
            }
            ClientMessage::Equip { armor, weapon } => {
                if let Err(text) = p.character.look.equip(&armor, &weapon) {
                    let _ = p.peer.try_send(json!({"type":"error","text":text}));
                }
            }
            ClientMessage::Interact { npc, offer } => {
                self.interact(session, &npc, offer.as_deref());
            }
            ClientMessage::Chat { text } => {
                let text = text.trim();
                if self.time - p.chat_at < 1. {
                    let _=p.peer.try_send(json!({"type":"error","text":"Please wait a moment before chatting again."}));
                    return;
                }
                if text.is_empty()
                    || text.chars().count() > 240
                    || text.chars().any(char::is_control)
                {
                    return;
                }
                p.chat_at = self.time;
                let name = p.character.look.name.clone();
                let id = p.character.id.clone();
                self.emit(json!({"type":"chat","name":name,"id":id,"text":text}));
            }
            ClientMessage::Ping { nonce } => {
                let _ = p.peer.try_send(json!({"type":"pong","nonce":nonce}));
            }
            _ => {}
        }
    }
    fn interact(&mut self, session: u64, npc_id: &str, offer_id: Option<&str>) {
        let Some(npc) = self.map.npcs.iter().find(|npc| npc.id == npc_id) else {
            return;
        };
        let p = self.players.get_mut(&session).unwrap();
        if p.character.hp <= 0. || p.character.point().distance(Point { x: npc.x, y: npc.y }) > 2.8
        {
            let _ = p.peer.try_send(
                json!({"type":"error","text":"Walk closer to speak with this townsperson."}),
            );
            return;
        }
        p.stop();
        p.attack = 0.;
        let mut notice = String::new();
        if let Some(id) = offer_id {
            if self.time - p.service_at < 0.5 {
                return;
            }
            p.service_at = self.time;
            let Some(offer) = npc.offers.iter().find(|offer| offer.id == id) else {
                return;
            };
            if offer.heal > 0. && p.character.hp >= p.character.max_hp() {
                notice =
                    "You are already at full health. Save it for after your next adventure!".into();
            } else if p.character.gold < offer.cost {
                notice = format!("You need {} gold for this service.", offer.cost);
            } else {
                p.character.gold -= offer.cost;
                if offer.heal > 0. {
                    p.character.hp = (p.character.hp + offer.heal).min(p.character.max_hp());
                    notice = "Feeling better? Safe travels!".into();
                }
                if offer.gear {
                    let (armor, weapon) = match p.character.look.class {
                        Class::Warrior => ("azure", "royal"),
                        Class::Mage => ("runic", "crystal"),
                        Class::Assassin => ("moon", "moonfang"),
                    };
                    p.character
                        .look
                        .equip(armor, weapon)
                        .expect("valid shop equipment");
                    notice = "All fitted! Your new equipment is ready for the meadow.".into();
                }
            }
        }
        let _ = p
            .peer
            .try_send(json!({"type":"dialogue","npc":npc,"notice":notice,"gold":p.character.gold}));
    }
    fn start_attack(&mut self, session: u64) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        if p.character.hp <= 0. || p.cooldown > 0. || p.dash > 0. {
            return;
        }
        p.attack = 0.0001;
        p.hit = false;
        p.cooldown = p.character.look.class.cooldown();
        let kind = if p.character.look.class == Class::Mage {
            "cast"
        } else {
            "swing"
        };
        let id = p.character.id.clone();
        let point = p.character.point();
        self.event(kind, &id, point, 0., false);
    }
    pub fn step(&mut self) {
        self.time += TICK;
        self.tick += 1;
        self.update_king_spawn();
        let sessions: Vec<_> = self.players.keys().copied().collect();
        for session in sessions {
            self.update_player(session);
        }
        for i in 0..self.slimes.len() {
            self.update_slime(i);
        }
        self.update_bolts();
        self.update_drops();
        let stale: Vec<_> = self
            .players
            .iter()
            .filter(|(_, p)| p.peer.is_closed() || p.peer.capacity() == 0)
            .map(|(id, _)| *id)
            .collect();
        for session in stale {
            self.leave(session);
        }
        if self.tick.is_multiple_of(100) {
            self.save();
        }
    }
    fn update_player(&mut self, session: u64) {
        let p = self.players.get_mut(&session).unwrap();
        p.cooldown = (p.cooldown - TICK).max(0.);
        p.hurt = (p.hurt - TICK).max(0.);
        p.dash_cd = (p.dash_cd - TICK).max(0.);
        if p.character.hp <= 0. {
            p.moving = false;
            p.dead_time += TICK;
            p.stop();
            if p.dead_time >= 3.2 {
                p.character.x = self.map.spawn.x;
                p.character.y = self.map.spawn.y;
                p.character.hp = p.character.max_hp();
                p.dead_time = 0.;
                p.attack = 0.;
                p.cooldown = 0.;
                let id = p.character.id.clone();
                self.event("respawn", &id, self.map.spawn, 0., false);
            }
            return;
        }
        if self.time - p.last_hurt > 5. {
            p.character.hp = (p.character.hp + 3. * TICK).min(p.character.max_hp());
        }
        let mut strike = false;
        if p.attack > 0. {
            p.attack += TICK;
            if !p.hit && p.attack >= p.character.look.class.impact() {
                p.hit = true;
                strike = true;
            }
            if p.attack >= p.character.look.class.duration() {
                p.attack = 0.;
            }
        }
        let mut dir = Point::default();
        let mut travel = 0.;
        let mut auto_attack = false;
        if self.time - p.input_at > 0.3 {
            p.input = Point::default();
        }
        if p.input.x != 0. || p.input.y != 0. {
            dir = p.input;
            travel = f64::INFINITY;
        } else if let Some(id) = p.target {
            if let Some(s) = self.slimes.get(id).filter(|s| !s.dead) {
                let distance = p.character.point().distance(s.point());
                let facing = p.character.point().direction(s.point());
                if distance - s.r <= p.character.look.class.reach() {
                    p.face = facing;
                    auto_attack = true;
                } else {
                    dir = facing;
                    travel = distance;
                }
            } else {
                p.target = None;
            }
        } else if let Some(goal) = p.goal {
            travel = p.character.point().distance(goal);
            if travel < 0.12 {
                p.goal = None;
                travel = 0.;
            } else {
                dir = p.character.point().direction(goal);
            }
        }
        let mut distance =
            (p.character.look.class.speed() * TICK * if p.attack > 0. { 0.25 } else { 1. })
                .min(travel);
        if p.dash > 0. {
            dir = p.dash_direction;
            distance = 15. * p.dash.min(TICK);
            p.dash = (p.dash - TICK).max(0.);
        }
        p.moving = distance > 0. && (dir.x != 0. || dir.y != 0.);
        if p.moving {
            let mut point = p.character.point();
            self.map.walk(&mut point, dir, distance, 0.3);
            p.character.x = point.x;
            p.character.y = point.y;
            p.walk += TICK * 11.;
            if p.attack <= 0. {
                p.face = dir;
            }
        }
        if strike {
            self.strike(session);
        }
        if auto_attack {
            self.start_attack(session);
        }
    }
    fn strike(&mut self, session: u64) {
        let p = &self.players[&session];
        let point = p.character.point();
        let face = p.face;
        let class = p.character.look.class;
        let base = p.character.look.stats(p.character.level).0;
        let reach = class.reach();
        let crit = self.random() < if class == Class::Assassin { 0.28 } else { 0.14 };
        let damage = (base * (0.8 + self.random() * 0.4) * if crit { 2. } else { 1. }).round();
        if class == Class::Mage {
            let id = self.entity();
            self.bolts.push(Bolt {
                id,
                owner: session,
                x: point.x,
                y: point.y,
                fx: face.x,
                fy: face.y,
                t: 0.,
                color: "#c5a5ff",
                damage,
                crit,
            });
            return;
        }
        let hit: Vec<_> = self
            .slimes
            .iter()
            .filter(|s| {
                if s.dead {
                    return false;
                }
                let d = point.distance(s.point());
                let facing = point.direction(s.point());
                d - s.r < reach && (d < 0.6 || facing.x * face.x + facing.y * face.y > 0.15)
            })
            .map(|s| s.id)
            .collect();
        for id in hit {
            self.hit_slime(id, session, damage, crit);
        }
    }
    fn hit_slime(&mut self, id: usize, session: u64, damage: f64, crit: bool) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        if p.character.hp <= 0. {
            return;
        }
        let actor = p.character.id.clone();
        let s = &mut self.slimes[id];
        if s.dead {
            return;
        }
        s.hp = (s.hp - damage).max(0.);
        s.hurt_t = 0.4;
        s.target = Some(session);
        let point = s.point();
        let killed = s.hp <= 0.;
        let xp = Slime::stats(&s.kind).4;
        let kind = s.kind.clone();
        if killed {
            s.dead = true;
            s.die_t = 0.;
            s.respawn = if kind == "big" { 0. } else { 22. };
            s.state = "dead".into();
        }
        self.event("hit", &actor, point, damage, crit);
        if killed {
            if kind == "big" {
                self.next_king_spawn = self.time + self.king_spawn_delay();
            }
            let p = self.players.get_mut(&session).unwrap();
            p.character.kills += 1;
            p.character.xp += xp;
            let mut levels = 0;
            while p.character.xp >= p.character.xp_need() && p.character.level < 1000 {
                p.character.xp -= p.character.xp_need();
                p.character.level += 1;
                p.character.hp = p.character.max_hp();
                levels += 1;
            }
            self.event("slimeDie", &actor, point, 0., false);
            if levels > 0 {
                let point = self.players[&session].character.point();
                self.event("levelup", &actor, point, levels as f64, false);
            }
            let id = self.entity();
            let value = match kind.as_str() {
                "big" => 30,
                "beetle" => 10,
                _ => 3 + (self.random() * 4.) as u32,
            };
            self.drops.push(Drop {
                id,
                owner: actor,
                x: point.x,
                y: point.y,
                z: 8.,
                value,
                t: 0.,
                col: "#ffe066",
            });
        }
    }
    fn update_slime(&mut self, id: usize) {
        let wander = self.random();
        let angle = self.random() * std::f64::consts::TAU;
        let s = &mut self.slimes[id];
        let (windup, cooldown, charge_speed, awareness) = Slime::attack_profile(&s.kind);
        s.hurt_t = (s.hurt_t - TICK).max(0.);
        s.rec_t = (s.rec_t - TICK).max(0.);
        s.land_t = (s.land_t - TICK).max(0.);
        if s.dead {
            s.die_t += TICK;
            if s.kind == "big" {
                // Kings use the shared rare-spawn timer, never the ordinary respawn loop.
                return;
            }
            s.respawn -= TICK;
            if s.respawn <= 0. {
                let spawn = &self.map.slimes[id];
                *s = Slime::new(id, spawn);
            }
            return;
        }
        s.st -= TICK;
        s.atk_cd = (s.atk_cd - TICK).max(0.);
        s.blink -= TICK;
        if s.blink < -0.15 {
            s.blink = 2. + wander * 3.;
        }
        s.hop_v -= 20. * TICK;
        s.hop = (s.hop + s.hop_v * TICK).max(0.);
        if s.hop <= 0. {
            if s.hop_v < 0. {
                s.land_t = 0.15;
            }
            s.hop_v = 0.;
        }
        let nearest = self
            .players
            .iter()
            .filter(|(_, p)| p.character.hp > 0. && !self.map.in_city(p.character.point()))
            .map(|(id, p)| {
                (
                    *id,
                    p.character.point(),
                    s.point().distance(p.character.point()),
                )
            })
            .filter(|(_, _, d)| *d < awareness)
            .min_by(|a, b| a.2.total_cmp(&b.2));
        let target = s.target.and_then(|id| {
            self.players
                .get(&id)
                .filter(|p| p.character.hp > 0. && !self.map.in_city(p.character.point()))
                .map(|p| {
                    (
                        id,
                        p.character.point(),
                        s.point().distance(p.character.point()),
                    )
                })
        });
        let target = target.filter(|(_, _, d)| *d < 9.).or(nearest);
        if s.state != "return"
            && s.state != "windup"
            && s.state != "lunge"
            && let Some((id, _, _)) = target
        {
            s.target = Some(id);
            s.state = "chase".into();
        }
        let (_, damage, speed, _, _) = Slime::stats(&s.kind);
        let mut goal = None;
        let mut movement = speed * TICK;
        let mut hit = None;
        match s.state.as_str() {
            "idle" if s.st <= 0. => {
                s.goal = Point {
                    x: s.hx + angle.cos() * (1. + wander * 3.),
                    y: s.hy + angle.sin() * (1. + wander * 3.),
                };
                s.state = "wander".into();
                s.st = 3.;
            }
            "wander" => {
                if s.st <= 0. || s.point().distance(s.goal) < 0.3 {
                    s.state = "idle".into();
                    s.st = 1. + wander * 2.5;
                } else {
                    goal = Some(s.goal);
                    movement *= 0.55;
                }
            }
            "chase" => {
                if let Some((_, point, d)) =
                    target.filter(|_| s.point().distance(Point { x: s.hx, y: s.hy }) < 14.)
                {
                    if d < 1.15 + s.r && s.atk_cd <= 0. {
                        s.state = "windup".into();
                        s.st = windup;
                        s.goal = point;
                    } else {
                        goal = Some(point);
                    }
                } else {
                    s.state = "return".into();
                    s.target = None;
                }
            }
            "windup" => {
                if s.st <= 0. {
                    s.state = "lunge".into();
                    s.st = 0.3;
                    s.hit = false;
                    s.hop_v = 6.;
                    if let Some((_, point, _)) = target {
                        s.goal = point;
                    }
                }
            }
            "lunge" => {
                goal = Some(s.goal);
                movement = charge_speed * TICK;
                if let Some((id, _, d)) = target
                    && !s.hit
                    && d < 0.9 + s.r
                {
                    s.hit = true;
                    hit = Some(id);
                }
                if s.st <= 0. {
                    s.state = "chase".into();
                    s.atk_cd = cooldown;
                    s.rec_t = 0.22;
                }
            }
            "return" => {
                let home = Point { x: s.hx, y: s.hy };
                if s.point().distance(home) < 0.4 {
                    s.state = "idle".into();
                    s.st = 1.;
                    s.hp = (s.hp + s.max_hp * 0.5).min(s.max_hp);
                } else {
                    goal = Some(home);
                }
            }
            _ => {}
        }
        if let Some(goal) = goal {
            let mut point = s.point();
            let direction = point.direction(goal);
            movement = movement.min(point.distance(goal));
            self.map.walk(&mut point, direction, movement, s.r);
            if self.map.in_city(point) {
                point = s.point();
                s.target = None;
                s.state = "return".into();
            }
            s.x = point.x;
            s.y = point.y;
            s.dir = if direction.x - direction.y >= 0. {
                1.
            } else {
                -1.
            };
            if s.hop <= 0. && s.state != "lunge" {
                s.hop_v = 4.;
            }
        }
        let point = s.point();
        if let Some(session) = hit {
            self.hurt_player(session, damage, point);
        }
    }
    fn hurt_player(&mut self, session: u64, damage: f64, _from: Point) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        if p.character.hp <= 0.
            || self.map.in_city(p.character.point())
            || p.dash > 0.
            || self.time - p.last_hurt < 0.65
        {
            return;
        }
        let value = (damage - p.character.look.stats(p.character.level).1).max(1.);
        p.character.hp = (p.character.hp - value).max(0.);
        p.last_hurt = self.time;
        p.hurt = 0.25;
        let point = p.character.point();
        let actor = p.character.id.clone();
        let dead = p.character.hp <= 0.;
        if dead {
            p.dead_time = 0.;
            p.attack = 0.;
            p.stop();
        }
        self.event("hurt", &actor, point, value, false);
        if dead {
            self.event("death", &actor, point, 0., false);
        }
    }
    fn update_bolts(&mut self) {
        let mut bolts = std::mem::take(&mut self.bolts);
        for b in &mut bolts {
            if !self
                .players
                .get(&b.owner)
                .is_some_and(|p| p.character.hp > 0.)
            {
                b.t = 1.;
                continue;
            }
            let start = Point { x: b.x, y: b.y };
            b.x += b.fx * 12. * TICK;
            b.y += b.fy * 12. * TICK;
            b.t += TICK;
            let end = Point { x: b.x, y: b.y };
            let first = self
                .slimes
                .iter()
                .filter(|s| !s.dead && segment_distance(s.point(), start, end) < s.r + 0.22)
                .min_by(|a, c| {
                    start
                        .distance(a.point())
                        .total_cmp(&start.distance(c.point()))
                })
                .map(|s| s.id);
            if let Some(id) = first {
                self.hit_slime(id, b.owner, b.damage, b.crit);
                b.t = 1.;
            }
        }
        bolts.retain(|b| b.t < 0.65);
        self.bolts = bolts;
    }
    fn update_drops(&mut self) {
        let mut rewards = vec![];
        for d in &mut self.drops {
            d.t += TICK;
            if d.t < 0.6 {
                continue;
            }
            if let Some((_, p)) = self
                .players
                .iter_mut()
                .find(|(_, p)| p.character.id == d.owner && p.character.hp > 0.)
            {
                let point = Point { x: d.x, y: d.y };
                let distance = point.distance(p.character.point());
                if distance < 3. {
                    let dir = point.direction(p.character.point());
                    let travel = (9. * TICK).min(distance);
                    d.x += dir.x * travel;
                    d.y += dir.y * travel;
                    if distance < 0.5 {
                        p.character.gold += d.value;
                        rewards.push((d.owner.clone(), p.character.point(), d.value));
                        d.t = 61.;
                    }
                }
            }
        }
        self.drops.retain(|d| d.t < 60.);
        for (id, p, value) in rewards {
            self.event("pickup", &id, p, value as f64, false);
        }
    }
    pub async fn run(
        mut self,
        mut commands: mpsc::Receiver<Command>,
        snapshots: watch::Sender<Value>,
    ) {
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(50));
        interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
        loop {
            tokio::select! {
                _=interval.tick()=>{ self.step(); if self.tick.is_multiple_of(2) {snapshots.send_replace(self.snapshot());} }
                command=commands.recv()=>match command {
                    Some(Command::Join{session,token,look,peer,reply})=>{let _=reply.send(self.join(session,token,look,peer));}
                    Some(Command::Message{session,message})=>self.message(session,message),
                    Some(Command::Leave{session})=>self.leave(session),
                    Some(Command::Shutdown{reply})=>{self.save();let _=reply.send(());break;}
                    None=>{self.save();break;}
                }
            }
        }
    }
}
fn segment_distance(p: Point, a: Point, b: Point) -> f64 {
    let dx = b.x - a.x;
    let dy = b.y - a.y;
    let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy).max(1e-12);
    p.distance(Point {
        x: a.x + dx * t.clamp(0., 1.),
        y: a.y + dy * t.clamp(0., 1.),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn world() -> World {
        World::new(Store::open(std::path::Path::new(":memory:")).unwrap())
    }
    fn join(w: &mut World, id: u64, class: Class) -> mpsc::Receiver<Value> {
        let (tx, rx) = mpsc::channel(256);
        let look = Look {
            class,
            ..Look::default()
        };
        w.join(id, None, Some(look), tx).unwrap();
        rx
    }
    #[test]
    fn king_timer_spawns_one_random_location_and_announces_it() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        assert!((KING_SPAWN_MIN..KING_SPAWN_MAX).contains(&w.next_king_spawn));
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.kind == "big")
                .all(|s| s.dead && s.hp == 0. && s.die_t >= 2.)
        );
        let deadline = w.next_king_spawn;
        w.time = deadline - TICK;
        w.update_king_spawn();
        assert!(w.slimes.iter().filter(|s| s.kind == "big").all(|s| s.dead));
        w.time = deadline;
        w.update_king_spawn();
        let kings: Vec<_> = w
            .slimes
            .iter()
            .filter(|s| s.kind == "big" && !s.dead)
            .collect();
        assert_eq!(kings.len(), 1);
        assert_eq!(kings[0].hp, 600.);
        let id = kings[0].id;
        assert_eq!(kings[0].x, w.map.slimes[id].x);
        assert_eq!(kings[0].y, w.map.slimes[id].y);
        assert_eq!(rx.try_recv().unwrap()["type"], "system"); // Join notice.
        assert!(
            rx.try_recv().unwrap()["text"]
                .as_str()
                .unwrap()
                .contains("King Slime")
        );
        w.time += KING_SPAWN_MAX * 10.;
        w.update_king_spawn();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.kind == "big" && !s.dead)
                .count(),
            1
        );
        assert!(rx.try_recv().is_err());

        // Both timer length and location vary with the server RNG, deterministically here.
        let mut locations = std::collections::BTreeSet::new();
        let mut delays = std::collections::BTreeSet::new();
        for seed in 1..=32 {
            let mut w = world();
            w.rng = seed;
            let delay = w.king_spawn_delay();
            assert!((KING_SPAWN_MIN..KING_SPAWN_MAX).contains(&delay));
            delays.insert(delay.to_bits());
            w.time = w.next_king_spawn;
            w.update_king_spawn();
            locations.insert(
                w.slimes
                    .iter()
                    .find(|s| s.kind == "big" && !s.dead)
                    .unwrap()
                    .id,
            );
        }
        assert_eq!(locations.len(), 2);
        assert!(delays.len() > 1);
    }

    #[test]
    fn king_defeat_reschedules_without_fast_respawn_or_duplicate_rewards() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.time = w.next_king_spawn;
        w.update_king_spawn();
        let id = w
            .slimes
            .iter()
            .find(|s| s.kind == "big" && !s.dead)
            .unwrap()
            .id;
        w.hit_slime(id, 1, 1000., false);
        let deadline = w.next_king_spawn;
        assert!((KING_SPAWN_MIN..KING_SPAWN_MAX).contains(&(deadline - w.time)));
        w.hit_slime(id, 1, 1000., false);
        assert_eq!(w.next_king_spawn, deadline);
        assert_eq!(w.players[&1].character.kills, 1);
        assert_eq!(w.players[&1].character.xp, 75);
        assert_eq!(w.drops.len(), 1);
        assert_eq!(w.drops[0].value, 30);
        for _ in 0..500 {
            w.time += TICK;
            w.update_king_spawn();
            w.update_slime(id);
        }
        assert!(
            w.slimes[id].dead,
            "Kings must not use the normal 22-second respawn"
        );
        w.time = deadline - TICK;
        w.update_king_spawn();
        assert!(w.slimes.iter().filter(|s| s.kind == "big").all(|s| s.dead));
        w.time = deadline;
        w.update_king_spawn();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.kind == "big" && !s.dead)
                .count(),
            1
        );
        assert_eq!(
            w.slimes
                .iter()
                .find(|s| s.kind == "big" && !s.dead)
                .unwrap()
                .hp,
            600.
        );
        assert_eq!(w.players[&1].character.kills, 1);
    }

    #[test]
    fn harder_enemies_spawn_clear_and_charge_with_authoritative_damage() {
        let w = world();
        assert_eq!(w.slimes.iter().filter(|s| s.kind == "beetle").count(), 5);
        for s in &w.slimes {
            let mut point = s.point();
            w.map.collide(&mut point, s.r);
            assert!(
                point.distance(s.point()) < 1e-6,
                "{} spawn is blocked",
                s.kind
            );
            assert!(!w.map.in_city(s.point()));
        }
        for (kind, hp, damage, windup) in [("beetle", 240., 22., 0.4), ("big", 600., 30., 0.35)] {
            let mut w = world();
            let _rx = join(&mut w, 1, Class::Warrior);
            let point = w.players[&1].character.point();
            // Arrange one enemy nearby; exercise its actual chase, windup and charge AI.
            w.slimes[0] = Slime::new(
                0,
                &SlimeSpawn {
                    kind: kind.into(),
                    x: point.x + 1.,
                    y: point.y,
                },
            );
            w.slimes[0].atk_cd = 0.;
            w.update_slime(0);
            assert_eq!(w.slimes[0].max_hp, hp);
            assert_eq!(w.slimes[0].state, "windup");
            assert_eq!(w.snapshot()["slimes"][0]["windupTime"], windup);
            assert_eq!(w.players[&1].character.hp, 120.);
            for _ in 0..20 {
                w.time += TICK;
                w.update_slime(0);
            }
            let defense = w.players[&1].character.look.stats(1).1;
            assert_eq!(w.players[&1].character.hp, 120. - (damage - defense));
        }
    }

    #[test]
    fn slower_leveling_requires_fourteen_green_kills_and_carries_remaining_xp() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        assert_eq!(w.players[&1].character.xp_need(), 160);
        for _ in 0..13 {
            w.hit_slime(0, 1, 1000., false);
            w.slimes[0].respawn = TICK;
            w.update_slime(0);
        }
        assert_eq!(w.players[&1].character.level, 1);
        assert_eq!(w.players[&1].character.xp, 156);
        w.hit_slime(0, 1, 1000., false);
        assert_eq!(w.players[&1].character.level, 2);
        assert_eq!(w.players[&1].character.xp, 8);
        assert_eq!(w.players[&1].character.xp_need(), 408);
        assert_eq!(w.players[&1].character.hp, 140.);
    }

    #[test]
    fn beetle_rewards_once_and_respawns_with_full_health() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        let id = w.slimes.iter().position(|s| s.kind == "beetle").unwrap();
        w.hit_slime(id, 1, 1000., false);
        w.hit_slime(id, 1, 1000., false);
        assert_eq!(w.players[&1].character.kills, 1);
        assert_eq!(w.players[&1].character.xp, 32);
        assert_eq!(w.drops.len(), 1);
        assert_eq!(w.drops[0].value, 10);
        w.slimes[id].respawn = TICK;
        w.update_slime(id);
        assert!(!w.slimes[id].dead);
        assert_eq!(w.slimes[id].hp, 240.);
        assert_eq!(w.slimes[id].kind, "beetle");
    }

    #[test]
    fn npc_services_check_distance_price_health_and_offer_ids() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(rx.try_recv().unwrap()["type"], "system");
        assert_eq!(rx.try_recv().unwrap()["type"], "error");
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = 42.;
        c.y = 78.5;
        c.hp = 40.;
        c.gold = 7;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.hp, 40.);
        assert_eq!(w.players[&1].character.gold, 7);
        w.time += 1.;
        w.players.get_mut(&1).unwrap().character.gold = 8;
        w.interact(1, "apothecary", Some("unknown"));
        assert_eq!(w.players[&1].character.gold, 8);
        w.time += 1.;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.hp, 100.);
        assert_eq!(w.players[&1].character.gold, 0);
        // Repeated requests cannot bypass the service cooldown.
        w.players.get_mut(&1).unwrap().character.gold = 8;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.gold, 8);
        w.time += 1.;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.hp, 120.);
        w.time += 1.;
        w.players.get_mut(&1).unwrap().character.gold = 8;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(
            w.players[&1].character.gold, 8,
            "full-health shoppers are not charged"
        );
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        w.time += 1.;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.hp, 0.);
    }

    #[test]
    fn sanctuary_heals_and_armorer_fits_each_class_and_city_is_safe() {
        for class in [Class::Warrior, Class::Mage, Class::Assassin] {
            let mut w = world();
            let _rx = join(&mut w, 1, class);
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = 30.;
            c.y = 78.5;
            c.hp = 10.;
            w.interact(1, "healer", Some("blessing"));
            assert_eq!(w.players[&1].character.hp, class.health());
            assert_eq!(w.players[&1].character.gold, 0);
            w.time += 1.;
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = 31.;
            c.y = 88.;
            w.interact(1, "smith", Some("fitting"));
            assert!(w.players[&1].character.look.validate().is_ok());
            assert!(w.players[&1].character.look.stats(1).1 > 0.);
            w.hurt_player(1, 1000., Point::default());
            assert_eq!(w.players[&1].character.hp, class.health());
            // A slime pursuing an adventurer loses its target at the city gate.
            w.slimes[0].x = 36.;
            w.slimes[0].y = 71.5;
            w.slimes[0].target = Some(1);
            w.slimes[0].state = "chase".into();
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = 36.;
            c.y = 73.;
            w.update_slime(0);
            assert!(w.slimes[0].target.is_none());
            assert!(!w.map.in_city(w.slimes[0].point()));
        }
    }

    #[test]
    fn movement_is_normalized_and_stale_input_stops() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let start = w.players[&1].character.point();
        w.message(1, ClientMessage::Input { dx: 1., dy: 1. });
        w.step();
        assert!((start.distance(w.players[&1].character.point()) - 5.2 * TICK).abs() < 1e-6);
        for _ in 0..20 {
            w.step();
        }
        let point = w.players[&1].character.point();
        for _ in 0..20 {
            w.step();
        }
        assert!(point.distance(w.players[&1].character.point()) < 1e-8);
        w.message(1, ClientMessage::Move { x: f64::NAN, y: 5. });
        assert!(w.players[&1].goal.is_none());
        w.message(1, ClientMessage::Input { dx: 100., dy: 0. });
        assert_eq!(w.players[&1].input.x, 0.);
    }
    #[test]
    fn shared_kill_rewards_once_and_slime_respawns() {
        let mut w = world();
        let _a = join(&mut w, 1, Class::Warrior);
        let _b = join(&mut w, 2, Class::Mage);
        w.hit_slime(0, 1, 1000., false);
        w.hit_slime(0, 2, 1000., false);
        assert!(w.slimes[0].dead);
        assert_eq!(w.players[&1].character.kills, 1);
        assert_eq!(w.players[&2].character.kills, 0);
        assert_eq!(w.drops.len(), 1);
        assert_eq!(w.players[&1].character.xp, 12);
        w.slimes[0].respawn = TICK;
        w.step();
        assert!(!w.slimes[0].dead);
        assert_eq!(w.slimes[0].hp, 60.);
    }
    #[test]
    fn attack_cooldown_range_equipment_and_respawn() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.start_attack(1);
        w.start_attack(1);
        assert_eq!(w.players[&1].cooldown, 0.55);
        let health: Vec<_> = w.slimes.iter().map(|s| s.hp).collect();
        w.strike(1);
        assert_eq!(w.slimes.iter().map(|s| s.hp).collect::<Vec<_>>(), health);
        w.message(
            1,
            ClientMessage::Equip {
                armor: "azure".into(),
                weapon: "royal".into(),
            },
        );
        assert_eq!(w.players[&1].character.look.stats(1), (34., 5.));
        w.message(
            1,
            ClientMessage::Equip {
                armor: "godmode".into(),
                weapon: "royal".into(),
            },
        );
        assert_eq!(w.players[&1].character.look.warrior_armor, "azure");
        w.hurt_player(1, 1000., Point::default());
        assert_eq!(w.players[&1].character.hp, 0.);
        w.players.get_mut(&1).unwrap().dead_time = 3.2;
        w.step();
        assert_eq!(w.players[&1].character.hp, 120.);
        assert_eq!(w.players[&1].character.look.warrior_weapon, "royal");
    }
    #[test]
    fn projectile_hits_nearest_and_dash_is_class_limited() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        for (i, s) in w.slimes.iter_mut().enumerate() {
            s.x = 50. + i as f64;
            s.y = 50.;
        }
        w.slimes[0].x = 36.3;
        w.slimes[0].y = 60.;
        w.slimes[1].x = 36.5;
        w.slimes[1].y = 60.;
        w.players.get_mut(&1).unwrap().face = Point { x: 1., y: 0. };
        w.strike(1);
        w.update_bolts();
        assert!(w.slimes[0].hp < 60.);
        assert_eq!(w.slimes[1].hp, 60.);
        assert!(w.bolts.is_empty());
        w.message(1, ClientMessage::Dash { dx: 1., dy: 0. });
        assert_eq!(w.players[&1].dash, 0.);
        let _b = join(&mut w, 2, Class::Assassin);
        w.message(2, ClientMessage::Dash { dx: 1., dy: 0. });
        assert_eq!(w.players[&2].dash, 0.18);
        w.message(2, ClientMessage::Dash { dx: 0., dy: 1. });
        assert_eq!(w.players[&2].dash_direction.x, 1.);
    }
    #[test]
    fn duplicate_character_session_is_rejected() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_string();
        let (tx, _rx2) = mpsc::channel(256);
        assert!(
            w.join(2, Some(token.clone()), None, tx)
                .unwrap_err()
                .contains("already online")
        );
        w.players.get_mut(&1).unwrap().character.gold = 42;
        w.leave(1);
        let (tx, _rx3) = mpsc::channel(256);
        w.join(3, Some(token), None, tx).unwrap();
        assert_eq!(w.players[&3].character.gold, 42);
    }

    #[test]
    fn only_the_living_killer_collects_a_drop() {
        let mut w = world();
        let _a = join(&mut w, 1, Class::Mage);
        let _b = join(&mut w, 2, Class::Warrior);
        w.hit_slime(0, 1, 1000., false);
        let point = Point {
            x: w.drops[0].x,
            y: w.drops[0].y,
        };
        w.drops[0].t = 1.;
        let other = &mut w.players.get_mut(&2).unwrap().character;
        other.x = point.x;
        other.y = point.y;
        w.update_drops();
        assert_eq!(w.players[&2].character.gold, 0);
        assert_eq!(w.drops.len(), 1);
        let owner = &mut w.players.get_mut(&1).unwrap().character;
        owner.x = point.x;
        owner.y = point.y;
        owner.hp = 0.;
        w.update_drops();
        assert_eq!(w.players[&1].character.gold, 0);
        w.players.get_mut(&1).unwrap().character.hp = 80.;
        let value = w.drops[0].value;
        w.update_drops();
        assert_eq!(w.players[&1].character.gold, value);
        assert!(w.drops.is_empty());
        w.update_drops();
        assert_eq!(w.players[&1].character.gold, value);
    }
}
