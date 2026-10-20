//! Opt-in player combat. The server owns consent, matchmaking, hit rolls, damage and match results.
use super::*;

const REQUEST_TIME: f64 = 45.;
const DUEL_RANGE: f64 = 25.;
const DUEL_RETURN_TIME: f64 = 10.;
const ARENA_TIME: f64 = 300.;
/// Every blow that lands on a player (basic attack, skill, bolt) is scaled by this on top of `DAMAGE_TAKEN_SCALE`, so a
/// duel lasts longer than the same fight against a monster. Healing in a PvP fight is scaled by it too, or halving the
/// damage would double what healing is worth.
pub(super) const PVP_DAMAGE_SCALE: f64 = 0.5;
/// A hunter's blows on players deal this much more (owner, 2026-10-20: +25%, then another +10%), applied to the damage
/// before defence.
const PVP_HUNTER_DAMAGE: f64 = 1.35;
/// Seconds after a blow dealt or taken in which a player's healing is scaled the same way (`Player::heal_factor`).
const PVP_FIGHT_TIME: f64 = 10.;
/// A priest's own healing in a PvP fight is scaled by this on top of `PVP_DAMAGE_SCALE` (owner, 2026-10-20), so it comes to
/// a quarter: the priest's sustain, not the damage cut, kept it unbeaten.
pub(super) const PVP_PRIEST_HEAL_SCALE: f64 = 0.5;

#[derive(Default)]
pub(super) struct Pvp {
    requests: Vec<Duel>,
    duels: Vec<Duel>,
    queue: Vec<Queue>,
    matches: Vec<Match>,
}
#[derive(Clone)]
struct Duel {
    from: String,
    to: String,
    expires: f64,
    zone: usize,
    center: Point,
    outside: [Option<f64>; 2],
}
#[derive(Clone)]
struct Queue {
    size: usize,
    members: Vec<String>,
}
struct Match {
    zone: usize,
    teams: [Vec<String>; 2],
    returns: BTreeMap<String, (usize, f64, f64)>,
    ends: f64,
}

impl World {
    pub(super) fn is_arena_zone(&self, zone: usize) -> bool {
        self.maps.get(zone).is_some_and(|m| m.name == "The Arena")
    }
    pub(super) fn pvp_busy(&self, id: &str) -> bool {
        self.pvp.duels.iter().any(|d| d.from == id || d.to == id)
            || self
                .pvp
                .queue
                .iter()
                .any(|q| q.members.iter().any(|m| m == id))
            || self
                .pvp
                .matches
                .iter()
                .any(|m| m.teams.iter().flatten().any(|p| p == id))
    }
    fn pvp_sync(&self) {
        for p in self
            .players
            .values()
            .filter(|p| p.merc.is_none() && p.ambient.is_none())
        {
            let id = &p.character.id;
            let requests: Vec<Value> = self.pvp.requests.iter().filter(|d| d.to == *id)
                .map(|d| json!({"id":d.from,"name":self.name_of(&d.from),"left":(d.expires-self.time).max(0.).ceil()})).collect();
            let duel = self
                .pvp
                .duels
                .iter()
                .find(|d| d.from == *id || d.to == *id)
                .map(|d| {
                    let side = if d.from == *id { 0 } else { 1 };
                    let other = if side == 0 { &d.to } else { &d.from };
                    let return_in = d.outside[side].map(|since| (DUEL_RETURN_TIME-(self.time-since)).max(0.).ceil() as u32);
                    let opponent_return_in = d.outside[1-side].map(|since| (DUEL_RETURN_TIME-(self.time-since)).max(0.).ceil() as u32);
                    json!({"id":other,"name":self.name_of(other),"range":DUEL_RANGE,"returnIn":return_in,"opponentReturnIn":opponent_return_in})
                });
            let queue = self
                .pvp
                .queue
                .iter()
                .find(|q| q.members.contains(id))
                .map(|q| q.size);
            let arena = self.pvp.matches.iter().find(|m| m.teams.iter().flatten().any(|a| a == id))
                .map(|m| json!({"size":m.teams[0].len(),"teams":m.teams,"ends":(m.ends-self.time).max(0.).ceil()}));
            let _ = p.peer.try_send(json!({"type":"pvp","flag":p.pvp_flag,"requests":requests,"duel":duel,"queue":queue,"arena":arena}));
        }
    }
    pub(super) fn pvp_command(&mut self, session: u64, command: PvpCommand) {
        let Some(me) = self.players.get(&session).map(|p| p.character.id.clone()) else {
            return;
        };
        let refresh = !matches!(command, PvpCommand::Attack { .. });
        let result = match command {
            PvpCommand::Refresh => Ok(()),
            PvpCommand::Flag { enabled } => self.pvp_flag(&me, enabled),
            PvpCommand::DuelRequest { id } => self.pvp_request(&me, &id),
            PvpCommand::DuelAccept { id } => self.pvp_accept(&me, &id),
            PvpCommand::DuelDecline { id } => {
                self.pvp.requests.retain(|d| !(d.from == id && d.to == me));
                Ok(())
            }
            PvpCommand::DuelCancel => {
                self.pvp.requests.retain(|d| d.from != me);
                if let Some(i) = self
                    .pvp
                    .duels
                    .iter()
                    .position(|d| d.from == me || d.to == me)
                {
                    self.pvp_finish_duel(i, None);
                }
                Ok(())
            }
            PvpCommand::ArenaQueue { size } => self.pvp_queue(&me, size),
            PvpCommand::ArenaLeave => self.pvp_arena_leave(&me),
            PvpCommand::Attack { id } => self.pvp_attack(session, &id),
        };
        if let Err(text) = result {
            self.tell(&me, text, false);
        }
        if refresh {
            self.pvp_sync();
        }
    }
    fn pvp_flag(&mut self, me: &str, enabled: bool) -> Result<(), String> {
        if self.pvp_busy(me) {
            return Err("Leave your duel or arena queue first.".into());
        }
        let p = self.online(me).ok_or("You are offline.")?;
        if p.is_hidden()
            || p.character.hp <= 0.
            || self.is_arena_zone(p.character.zone)
            || p.combat_left > 0.
        {
            return Err("You cannot change your flag during combat or an arena match.".into());
        }
        let session = *self
            .players
            .iter()
            .find(|(_, p)| p.character.id == me)
            .unwrap()
            .0;
        self.players.get_mut(&session).unwrap().pvp_flag = enabled;
        self.tell(
            me,
            if enabled {
                "World PvP enabled. Other flagged players may attack you outside sanctuaries."
            } else {
                "World PvP disabled."
            },
            true,
        );
        Ok(())
    }
    fn pvp_request(&mut self, me: &str, target: &str) -> Result<(), String> {
        if me == target || self.pvp_busy(me) || self.pvp_busy(target) {
            return Err("That duel is unavailable.".into());
        }
        let a = self.online(me).ok_or("You are offline.")?;
        let b = self.online(target).ok_or("That player is offline.")?;
        if a.merc.is_some()
            || b.merc.is_some()
            || a.is_hidden()
            || b.is_hidden()
            || a.ambient.is_some()
            || b.ambient.is_some()
            || a.character.spark_travel.is_some()
            || b.character.spark_travel.is_some()
            || a.character.hp <= 0.
            || b.character.hp <= 0.
            || a.character.zone != b.character.zone
            || self.is_arena_zone(a.character.zone)
            || a.character.point().distance(b.character.point()) > DUEL_RANGE
            || self.maps[a.character.zone].in_city(a.character.point())
            || self.maps[b.character.zone].in_city(b.character.point())
        {
            return Err("Both players must be alive and nearby outside a sanctuary.".into());
        }
        let zone = a.character.zone;
        let center = a.character.point();
        self.pvp.requests.retain(|d| d.from != me && d.to != target);
        self.pvp.requests.push(Duel {
            from: me.into(),
            to: target.into(),
            expires: self.time + REQUEST_TIME,
            zone,
            center,
            outside: [None, None],
        });
        self.tell(
            me,
            format!("Duel challenge sent to {}.", self.name_of(target)),
            true,
        );
        self.tell(
            target,
            format!(
                "{} challenged you to a duel. Open Social > PvP to accept.",
                self.name_of(me)
            ),
            true,
        );
        Ok(())
    }
    fn pvp_accept(&mut self, me: &str, from: &str) -> Result<(), String> {
        let i = self
            .pvp
            .requests
            .iter()
            .position(|d| d.from == from && d.to == me && d.expires > self.time)
            .ok_or("That challenge has expired.")?;
        if self.pvp_busy(me) || self.pvp_busy(from) {
            return Err("One player is already fighting.".into());
        }
        let a = self.online(me).ok_or("You are offline.")?;
        let b = self.online(from).ok_or("The challenger is offline.")?;
        if a.character.spark_travel.is_some()
            || b.character.spark_travel.is_some()
            || a.character.hp <= 0.
            || b.character.hp <= 0.
            || a.character.zone != b.character.zone
            || a.character.point().distance(b.character.point()) > DUEL_RANGE
            || self.maps[a.character.zone].in_city(a.character.point())
            || self.maps[b.character.zone].in_city(b.character.point())
        {
            return Err("Both players must still be nearby outside a sanctuary.".into());
        }
        let zone = a.character.zone;
        let center = Point {
            x: (a.character.x + b.character.x) / 2.,
            y: (a.character.y + b.character.y) / 2.,
        };
        let mut duel = self.pvp.requests.remove(i);
        duel.expires = self.time + ARENA_TIME;
        duel.zone = zone;
        duel.center = center;
        duel.outside = [None, None];
        self.pvp.duels.push(duel);
        self.tell(
            me,
            "Duel started. First to one health loses; no XP is lost.",
            true,
        );
        self.tell(
            from,
            "Duel started. First to one health loses; no XP is lost.",
            true,
        );
        Ok(())
    }
    fn pvp_queue(&mut self, me: &str, size: usize) -> Result<(), String> {
        if !(1..=3).contains(&size) {
            return Err("Choose 1v1, 2v2 or 3v3.".into());
        }
        if self.pvp_busy(me) {
            return Err("You are already in PvP.".into());
        }
        let members = if size == 1 {
            vec![me.into()]
        } else {
            if self.party_leader(me) != Some(me) {
                return Err("Only the party leader can queue.".into());
            }
            let members = self.party_mates(me);
            if members.len() != size {
                return Err("Your party must have exactly the requested size.".into());
            }
            members
        };
        let first = self.online(me).ok_or("You are offline.")?;
        for id in &members {
            let p = self.online(id).ok_or("All teammates must be online.")?;
            if p.character.hp <= 0.
                || p.is_hidden()
                || p.character.zone != first.character.zone
                || self.is_arena_zone(p.character.zone)
                || p.character.spark_travel.is_some()
                || self.pvp_busy(id)
            {
                return Err("All teammates must be alive, together and available.".into());
            }
        }
        self.pvp.queue.push(Queue { size, members });
        self.pvp_matchmake();
        Ok(())
    }
    fn pvp_matchmake(&mut self) {
        let invalid: Vec<_> = self
            .pvp
            .queue
            .iter()
            .enumerate()
            .filter(|(_, q)| !self.pvp_queue_valid(q))
            .map(|(i, _)| i)
            .collect();
        let changed = !invalid.is_empty();
        for i in invalid.into_iter().rev() {
            let q = self.pvp.queue.remove(i);
            for id in q.members {
                self.tell(
                    &id,
                    "Arena queue canceled: your team changed or is no longer ready.",
                    false,
                );
            }
        }
        if changed {
            self.pvp_sync();
        }
        let mut pair = None;
        for i in 0..self.pvp.queue.len() {
            for j in i + 1..self.pvp.queue.len() {
                if self.pvp.queue[i].size == self.pvp.queue[j].size {
                    pair = Some((i, j));
                    break;
                }
            }
            if pair.is_some() {
                break;
            }
        }
        let Some((i, j)) = pair else {
            return;
        };
        let Some(zone) = self
            .instances
            .iter()
            .find(|i| self.is_arena_zone(i.zone) && !i.active)
            .map(|i| i.zone)
        else {
            return;
        };
        let b = self.pvp.queue.remove(j);
        let a = self.pvp.queue.remove(i);
        let mut returns = BTreeMap::new();
        for (side, team) in [a.members.as_slice(), b.members.as_slice()]
            .iter()
            .enumerate()
        {
            for (lane, id) in team.iter().enumerate() {
                let session = *self
                    .players
                    .iter()
                    .find(|(_, p)| p.character.id == *id)
                    .unwrap()
                    .0;
                let p = self.players.get_mut(&session).unwrap();
                returns.insert(id.clone(), (p.character.zone, p.character.x, p.character.y));
                p.character.zone = zone;
                p.character.x = if side == 0 { 9. } else { 23. };
                p.character.y = 13. + lane as f64 * 3.;
                p.character.hp = p.character.max_hp();
                p.character.reset_resource();
                p.character.mounted = false;
                p.combat_left = 0.;
                p.stop();
                p.attack = 0.;
                p.cooldown = 0.;
                p.buffs.clear();
                let _ = p.peer.try_send(json!({"type":"notice","ok":true,"text":format!("{}v{} arena started. Defeat every opponent to win.",a.size,a.size)}));
            }
        }
        self.enter_instance(zone);
        self.pvp.matches.push(Match {
            zone,
            teams: [a.members, b.members],
            returns,
            ends: self.time + ARENA_TIME,
        });
        self.save();
    }
    fn pvp_queue_valid(&self, q: &Queue) -> bool {
        if q.members.len() != q.size {
            return false;
        }
        if q.size > 1 {
            let leader = &q.members[0];
            if self.party_leader(leader) != Some(leader.as_str()) {
                return false;
            }
            let party = self.party_mates(leader);
            if party.len() != q.size || !q.members.iter().all(|id| party.contains(id)) {
                return false;
            }
        }
        let Some(first) = self.online(&q.members[0]) else {
            return false;
        };
        q.members.iter().all(|id| {
            self.online(id).is_some_and(|p| {
                p.character.hp > 0.
                    && p.character.zone == first.character.zone
                    && !self.is_arena_zone(p.character.zone)
                    && p.character.spark_travel.is_none()
            })
        })
    }
    fn pvp_arena_leave(&mut self, me: &str) -> Result<(), String> {
        let queued = self
            .pvp
            .queue
            .iter()
            .position(|q| q.members.iter().any(|id| id == me));
        if let Some(i) = queued {
            self.pvp.queue.remove(i);
            return Ok(());
        }
        if let Some(i) = self
            .pvp
            .matches
            .iter()
            .position(|m| m.teams.iter().flatten().any(|id| id == me))
        {
            let side = if self.pvp.matches[i].teams[0].iter().any(|id| id == me) {
                1
            } else {
                0
            };
            self.pvp_finish_match(i, Some(side));
            return Ok(());
        }
        Err("You are not in an arena queue or match.".into())
    }
    fn pvp_attack(&mut self, session: u64, target: &str) -> Result<(), String> {
        let a = self.players.get(&session).ok_or("You are offline.")?;
        let me = a.character.id.clone();
        let b = self.online(target).ok_or("Target is offline.")?;
        if me == target
            || a.is_hidden()
            || b.is_hidden()
            || a.character.zone != b.character.zone
            || a.character.hp <= 0.
            || b.character.hp <= 0.
            || a.character.spark_travel.is_some()
            || b.character.spark_travel.is_some()
            || a.cooldown > 0.
            || a.dash > 0.
            || a.stun > 0.
        {
            return Err("Target is unavailable.".into());
        }
        let point = a.character.point();
        let target_point = b.character.point();
        let zone = a.character.zone;
        if !self.is_arena_zone(zone)
            && (self.maps[zone].in_city(point) || self.maps[zone].in_city(target_point))
        {
            return Err("PvP cannot take place in a sanctuary.".into());
        }
        let duel = self
            .pvp
            .duels
            .iter()
            .position(|d| (d.from == me && d.to == target) || (d.from == target && d.to == me));
        if let Some(i) = duel {
            let d = &self.pvp.duels[i];
            if d.zone != zone
                || point.distance(d.center) > DUEL_RANGE
                || target_point.distance(d.center) > DUEL_RANGE
            {
                return Err("Return to the duel area before attacking.".into());
            }
        }
        let legal = self
            .players
            .iter()
            .find(|(_, p)| p.character.id == target)
            .is_some_and(|(d, _)| self.pvp_legal(session, *d));
        if !legal {
            return Err("PvP requires a duel, opposing arena teams, or two flagged players outside a sanctuary.".into());
        }
        if point.distance(target_point)
            > a.character
                .look
                .class
                .reach()
                .max(if a.character.look.class.ranged() {
                    8.
                } else {
                    1.8
                })
        {
            return Err("Target is out of range.".into());
        }
        if a.character.look.class.ranged() && !self.maps[zone].line_clear(point, target_point, 0.05)
        {
            return Err("A wall blocks your shot.".into());
        }
        let direction = point.direction(target_point);
        let p = self.players.get_mut(&session).unwrap();
        p.face = direction;
        p.character.mounted = false;
        p.combat_left = 5.;
        p.cooldown = p.character.attack_cooldown() / (1. + p.buff(BuffKind::Haste));
        p.attack = 0.0001;
        let (damage, crit) = self.roll_damage(session, 1.);
        let defender_session = *self
            .players
            .iter()
            .find(|(_, p)| p.character.id == target)
            .unwrap()
            .0;
        self.pvp_hit(session, defender_session, damage, crit);
        Ok(())
    }
    /// Whether `attacker` may hurt `defender` right now: opposing arena teams, the partner of a duel inside its ring, or
    /// two flagged players who are not party mates. Never in a sanctuary (the arena excepted), never a mercenary,
    /// ambient adventurer, hidden or fallen player. Basic attacks and skills share this rule.
    pub(super) fn pvp_legal(&self, attacker: u64, defender: u64) -> bool {
        let (Some(a), Some(b)) = (self.players.get(&attacker), self.players.get(&defender)) else {
            return false;
        };
        if attacker == defender
            || a.merc.is_some()
            || b.merc.is_some()
            || a.ambient.is_some()
            || b.ambient.is_some()
            || a.is_hidden()
            || b.is_hidden()
            || a.character.zone != b.character.zone
            || a.character.hp <= 0.
            || b.character.hp <= 0.
            || a.character.spark_travel.is_some()
            || b.character.spark_travel.is_some()
        {
            return false;
        }
        let (me, target) = (&a.character.id, &b.character.id);
        let zone = a.character.zone;
        let (here, there) = (a.character.point(), b.character.point());
        if !self.is_arena_zone(zone)
            && (self.maps[zone].in_city(here) || self.maps[zone].in_city(there))
        {
            return false;
        }
        if let Some(m) = self.pvp.matches.iter().find(|m| m.zone == zone) {
            return m.teams.iter().any(|team| team.contains(me))
                && !m
                    .teams
                    .iter()
                    .any(|team| team.contains(me) && team.contains(target));
        }
        if let Some(d) = self
            .pvp
            .duels
            .iter()
            .find(|d| (d.from == *me && d.to == *target) || (d.from == *target && d.to == *me))
        {
            return d.zone == zone
                && here.distance(d.center) <= DUEL_RANGE
                && there.distance(d.center) <= DUEL_RANGE;
        }
        a.pvp_flag && b.pvp_flag && !self.party_mates(me).iter().any(|id| id == target)
    }
    /// The sessions `session` may hurt with a skill within `radius` of `at` (their body counts as `PLAYER_RADIUS`),
    /// nearest first: the players' counterpart of `enemies_near`.
    pub(super) fn foes_near(&self, session: u64, at: Point, radius: f64, skip: &[u64]) -> Vec<u64> {
        if self.pvp.duels.is_empty()
            && self.pvp.matches.is_empty()
            && !self.players.get(&session).is_some_and(|p| p.pvp_flag)
        {
            return vec![];
        }
        let mut found: Vec<_> = self
            .players
            .iter()
            .filter(|(s, p)| {
                !skip.contains(s)
                    && at.distance(p.character.point()) - PLAYER_RADIUS < radius
                    && self.pvp_legal(session, **s)
            })
            .map(|(s, p)| (at.distance(p.character.point()), *s))
            .collect();
        found.sort_by(|a, b| a.0.total_cmp(&b.0).then(a.1.cmp(&b.1)));
        found.into_iter().map(|(_, s)| s).collect()
    }
    /// One blow of `damage` from `attacker` to `defender` (a basic attack, a skill or a bolt): dodge, defence, shield,
    /// the 1 health floor of duels and arenas, and the end of the duel, match or world fight. Returns the health the
    /// defender lost; 0 when the blow is not legal, misses or is dodged.
    pub(super) fn pvp_hit(&mut self, attacker: u64, defender: u64, damage: f64, crit: bool) -> f64 {
        if !self.pvp_legal(attacker, defender) {
            return 0.;
        }
        let session = attacker;
        let defender_session = defender;
        let damage = if self.players[&attacker].character.look.class == Class::Hunter {
            damage * PVP_HUNTER_DAMAGE
        } else {
            damage
        };
        let me = self.players[&attacker].character.id.clone();
        let target = self.players[&defender].character.id.clone();
        let zone = self.players[&attacker].character.zone;
        let target_point = self.players[&defender].character.point();
        let arena = self.pvp.matches.iter().position(|m| m.zone == zone);
        let duel = self
            .pvp
            .duels
            .iter()
            .position(|d| (d.from == me && d.to == target) || (d.from == target && d.to == me));
        let mut taken_total = 0.;
        let dodge = self.players[&defender_session].character.dodge_chance()
            + self.players[&defender_session].buff(BuffKind::Dodge);
        let dodged = damage > 0. && self.random() < dodge.min(0.95);
        let p = self.players.get_mut(&defender_session).unwrap();
        let shield = p.buff(BuffKind::Shield).min(0.8);
        let value = if damage <= 0. || dodged {
            0.
        } else {
            (((damage - p.character.stats().1).max(1.) * DAMAGE_TAKEN_SCALE * PVP_DAMAGE_SCALE)
                .round()
                .max(1.)
                * (1. - shield))
                .round()
                .max(1.)
        };
        // A ward soaks up what lands before it reaches the health; the blow still counts as landed.
        let landed = value > 0.;
        let value = if landed && p.absorb_left > 0. && p.absorb > 0. {
            let soaked = value.min(p.absorb);
            p.absorb -= soaked;
            value - soaked
        } else {
            value
        };
        if value > 0. {
            let hp = if arena.is_some() || duel.is_some() {
                (p.character.hp - value).max(1.)
            } else {
                (p.character.hp - value).max(0.)
            };
            let taken = p.character.hp - hp;
            taken_total = taken;
            p.character.hp = hp;
            p.hurt = 0.25;
            p.combat_left = 5.;
            p.character.mounted = false;
            if p.character.look.class == Class::Warrior {
                p.character.change_resource(taken);
            }
        }
        if landed {
            for session in [attacker, defender_session] {
                if let Some(p) = self.players.get_mut(&session) {
                    p.pvp_fight = PVP_FIGHT_TIME;
                }
            }
            // A skill that stuns, roots or wounds (cuts the healing of) the player it hurts: not when the blow missed or
            // was dodged.
            let class = self.players[&attacker].character.look.class;
            let (stun, root, wound, wound_time) = skills::find(class, &self.cur_skill)
                .map_or((0., 0., 0., 0.), |s| {
                    (s.stun, s.root, s.wound, s.wound_time)
                });
            if stun > 0. || root > 0. || wound > 0. {
                let p = self.players.get_mut(&defender_session).unwrap();
                let (stunned, rooted, wounded) = (
                    p.stun <= 0. && stun > 0.,
                    p.root <= 0. && root > 0.,
                    p.wound_left <= 0. && wound > 0.,
                );
                p.stun = p.stun.max(stun);
                p.root = p.root.max(root);
                if wound > 0. {
                    p.wound = if p.wound_left > 0. {
                        p.wound.max(wound)
                    } else {
                        wound
                    };
                    p.wound_left = p.wound_left.max(wound_time);
                }
                if stun > 0. {
                    p.stop();
                    p.attack = 0.;
                }
                if stunned {
                    self.tell(
                        &target,
                        format!("You are stunned for {stun} seconds."),
                        false,
                    );
                }
                if rooted {
                    self.tell(
                        &target,
                        format!("You are rooted for {root} seconds."),
                        false,
                    );
                }
                if wounded {
                    self.tell(
                        &target,
                        format!(
                            "Your healing is reduced by {}% for {wound_time} seconds.",
                            (wound * 100.).round()
                        ),
                        false,
                    );
                }
            }
        }
        if taken_total > 0. {
            // Damage dealt feeds a warrior's rage here as it does against monsters (`hit_slime`).
            if let Some(p) = self.players.get_mut(&session)
                && p.character.look.class == Class::Warrior
            {
                p.character.change_resource(taken_total * 0.5);
            }
            #[cfg(test)]
            {
                *self.damage_log.entry(session).or_default() += taken_total;
                let entry = self
                    .damage_by_source
                    .entry((session, self.cur_skill.clone()))
                    .or_default();
                entry.0 += taken_total;
                entry.1 += 1;
            }
        }
        let defeated = value > 0.
            && self.players[&defender_session].character.hp
                <= if arena.is_some() || duel.is_some() {
                    1.
                } else {
                    0.
                };
        let actor = self.players[&defender_session].character.id.clone();
        self.event_with(
            if dodged { "dodge" } else { "hurt" },
            &actor,
            target_point,
            value,
            crit,
            json!({"enemy":self.name_of(&me),"pvp":true}),
        );
        if defeated {
            if let Some(i) = arena {
                if self.pvp.matches[i].teams.iter().any(|team| {
                    team.iter()
                        .all(|id| self.online(id).is_none_or(|p| p.character.hp <= 1.))
                }) {
                    let winner = if self.pvp.matches[i].teams[0]
                        .iter()
                        .all(|id| self.online(id).is_none_or(|p| p.character.hp <= 1.))
                    {
                        1
                    } else {
                        0
                    };
                    self.pvp_finish_match(i, Some(winner));
                }
            } else if let Some(i) = duel {
                self.pvp_finish_duel(i, Some(me));
            } else {
                let p = self.players.get_mut(&defender_session).unwrap();
                p.dead_time = 0.;
                p.buffs.clear();
                p.stop();
                p.pvp_flag = false;
                self.event_with(
                    "death",
                    &actor,
                    target_point,
                    0.,
                    false,
                    json!({"enemy":self.name_of(&me),"pvp":true}),
                );
                self.tell(
                    &actor,
                    "Defeated in world PvP. No XP was lost; your PvP flag is off.",
                    false,
                );
                self.save();
            }
        }
        taken_total
    }
    fn pvp_finish_duel(&mut self, i: usize, winner: Option<String>) {
        let d = self.pvp.duels.remove(i);
        let text = winner.map_or_else(
            || "Duel ended without a winner.".to_string(),
            |id| format!("{} wins the duel!", self.name_of(&id)),
        );
        for id in [&d.from, &d.to] {
            if let Some(p) = self.players.values_mut().find(|p| p.character.id == *id) {
                p.stun = 0.;
                p.root = 0.;
                p.wound_left = 0.;
                p.pvp_fight = 0.;
                p.absorb_left = 0.;
            }
            self.tell(id, text.clone(), true);
        }
        self.pvp_sync();
    }
    fn pvp_finish_match(&mut self, i: usize, winner: Option<usize>) {
        let m = self.pvp.matches.remove(i);
        let text = winner.map_or_else(
            || "Arena match ended in a draw.".to_string(),
            |side| format!("Team {} wins the arena!", side + 1),
        );
        for (id, (zone, x, y)) in m.returns {
            if let Some(p) = self.players.values_mut().find(|p| p.character.id == id) {
                p.character.zone = zone;
                p.character.x = x;
                p.character.y = y;
                p.character.hp = p.character.max_hp();
                p.character.reset_resource();
                p.cooldown = 0.;
                p.stun = 0.;
                p.root = 0.;
                p.wound_left = 0.;
                p.pvp_fight = 0.;
                p.absorb_left = 0.;
                p.combat_left = 0.;
                p.stop();
                let _ = p
                    .peer
                    .try_send(json!({"type":"notice","ok":true,"text":text}));
            }
        }
        self.save();
        self.pvp_sync();
    }
    pub(super) fn pvp_left(&mut self, id: &str) {
        self.pvp.requests.retain(|d| d.from != id && d.to != id);
        self.pvp
            .queue
            .retain(|q| !q.members.iter().any(|m| m == id));
        if let Some(i) = self
            .pvp
            .duels
            .iter()
            .position(|d| d.from == id || d.to == id)
        {
            self.pvp_finish_duel(i, None);
        }
        if let Some(i) = self
            .pvp
            .matches
            .iter()
            .position(|m| m.teams.iter().flatten().any(|m| m == id))
        {
            let winner = if self.pvp.matches[i].teams[0].iter().any(|m| m == id) {
                1
            } else {
                0
            };
            self.pvp_finish_match(i, Some(winner));
        }
        self.pvp_sync();
    }
    pub(super) fn update_pvp(&mut self) {
        let before = self.pvp.requests.len();
        self.pvp.requests.retain(|d| d.expires > self.time);
        if self.pvp.requests.len() != before {
            self.pvp_sync();
        }
        let mut finished = Vec::new();
        let mut notices = Vec::new();
        for i in 0..self.pvp.duels.len() {
            let d = &self.pvp.duels[i];
            let participants = [d.from.clone(), d.to.clone()];
            let gone = participants
                .iter()
                .any(|id| self.online(id).is_none_or(|p| p.character.hp <= 0.));
            if gone || d.expires <= self.time {
                finished.push((i, None));
                continue;
            }
            let outside: [bool; 2] = std::array::from_fn(|side| {
                let p = self.online(&participants[side]).unwrap();
                p.character.zone != d.zone
                    || p.character.point().distance(d.center) > DUEL_RANGE
                    || self.maps[p.character.zone].in_city(p.character.point())
            });
            let d = &mut self.pvp.duels[i];
            for side in 0..2 {
                match (outside[side], d.outside[side]) {
                    (true, None) => {
                        d.outside[side] = Some(self.time);
                        notices.push((
                            participants[side].clone(),
                            "Return to the duel area within 10 seconds or forfeit.".to_string(),
                        ));
                    }
                    (false, Some(_)) => {
                        d.outside[side] = None;
                        notices.push((
                            participants[side].clone(),
                            "You returned to the duel area. The timer stopped.".to_string(),
                        ));
                    }
                    _ => {}
                }
            }
            let forfeit = d
                .outside
                .map(|since| since.is_some_and(|at| self.time - at >= DUEL_RETURN_TIME));
            if forfeit[0] || forfeit[1] {
                let winner = match forfeit {
                    [true, false] => Some(d.to.clone()),
                    [false, true] => Some(d.from.clone()),
                    _ => None,
                };
                finished.push((i, winner));
            }
        }
        for (id, text) in notices {
            self.tell(&id, text, true);
        }
        for (i, winner) in finished.into_iter().rev() {
            self.pvp_finish_duel(i, winner);
        }
        if !self.pvp.duels.is_empty() {
            self.pvp_sync();
        }
        let expired: Vec<_> = self
            .pvp
            .matches
            .iter()
            .enumerate()
            .filter(|(_, m)| m.ends <= self.time)
            .map(|(i, _)| i)
            .collect();
        for i in expired.into_iter().rev() {
            self.pvp_finish_match(i, None);
        }
        self.pvp_matchmake();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    thread_local! {
        /// The players' message queues, kept open so stepping the world does not drop anybody; `tick` empties them.
        static RECEIVERS: std::cell::RefCell<Vec<mpsc::Receiver<Value>>> = const { std::cell::RefCell::new(Vec::new()) };
    }
    fn tick(w: &mut World, steps: usize) {
        for _ in 0..steps {
            w.step();
            RECEIVERS.with(|r| {
                for rx in r.borrow_mut().iter_mut() {
                    while rx.try_recv().is_ok() {}
                }
            });
        }
    }
    fn world() -> World {
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
    }
    fn add(w: &mut World, session: u64, name: &str) -> String {
        let (tx, rx) = mpsc::channel(4096);
        RECEIVERS.with(|r| r.borrow_mut().push(rx));
        let welcome = w
            .join(
                session,
                None,
                Some(Look {
                    name: name.into(),
                    ..Look::default()
                }),
                tx,
            )
            .unwrap();
        let p = w.players.get_mut(&session).unwrap();
        p.character.x = 8. + session as f64;
        p.character.y = 8.;
        welcome["id"].as_str().unwrap().into()
    }
    #[test]
    fn consent_and_duel_ko_do_not_consume_xp() {
        let mut w = world();
        let a = add(&mut w, 1, "Alice");
        let b = add(&mut w, 2, "Bob");
        assert_eq!(w.players[&1].snapshot()["pvpSupported"], true);
        assert!(w.pvp_attack(1, &b).is_err());
        w.pvp_command(1, PvpCommand::DuelRequest { id: b.clone() });
        assert_eq!(w.pvp.requests.len(), 1);
        w.pvp_command(2, PvpCommand::DuelAccept { id: a.clone() });
        assert_eq!(w.pvp.duels.len(), 1);
        w.players.get_mut(&1).unwrap().character.attributes.accuracy = 20;
        w.players.get_mut(&2).unwrap().character.hp = 2.;
        w.pvp_attack(1, &b).unwrap();
        assert!(w.pvp.duels.is_empty());
        assert_eq!(w.players[&2].character.hp, 1.);
        assert_eq!(w.players[&2].character.xp, 0);
        assert!(w.players[&2].character.hp >= 1.);
    }
    #[test]
    fn ranged_pvp_refuses_a_target_behind_a_wall() {
        let mut w = world();
        let a = add(&mut w, 1, "Alice");
        let b = add(&mut w, 2, "Bob");
        w.players.get_mut(&1).unwrap().character.look.class = Class::Hunter;
        w.pvp_command(1, PvpCommand::DuelRequest { id: b.clone() });
        w.pvp_command(2, PvpCommand::DuelAccept { id: a });
        w.maps[0].objects = vec![crate::model::Obstacle {
            x: 9.5,
            y: 8.,
            r: 0.,
            width: 0.2,
            depth: 2.,
        }];
        let hp = w.players[&2].character.hp;
        assert_eq!(w.pvp_attack(1, &b), Err("A wall blocks your shot.".into()));
        assert_eq!(w.players[&1].cooldown, 0.);
        assert_eq!(w.players[&2].character.hp, hp);
    }
    #[test]
    fn duel_range_gives_ten_seconds_to_return_before_forfeit() {
        let mut w = world();
        let a = add(&mut w, 1, "Alice");
        let b = add(&mut w, 2, "Bob");
        w.pvp_command(1, PvpCommand::DuelRequest { id: b });
        w.pvp_command(2, PvpCommand::DuelAccept { id: a });
        w.players.get_mut(&2).unwrap().character.x = 45.;
        w.players.get_mut(&2).unwrap().character.y = 45.;
        w.update_pvp();
        assert_eq!(w.pvp.duels[0].outside[1], Some(0.));
        w.time = 9.9;
        w.update_pvp();
        assert_eq!(w.pvp.duels.len(), 1);
        w.players.get_mut(&2).unwrap().character.x = 10.;
        w.players.get_mut(&2).unwrap().character.y = 8.;
        w.update_pvp();
        assert_eq!(w.pvp.duels[0].outside[1], None);
        w.players.get_mut(&2).unwrap().character.x = 45.;
        w.players.get_mut(&2).unwrap().character.y = 45.;
        w.update_pvp();
        assert_eq!(w.pvp.duels[0].outside[1], Some(9.9));
        w.time = 19.8;
        w.update_pvp();
        assert_eq!(w.pvp.duels.len(), 1);
        w.time = 20.;
        w.update_pvp();
        assert!(w.pvp.duels.is_empty());
    }
    #[test]
    fn world_flag_requires_both_sides_and_clears_on_defeat() {
        let mut w = world();
        let a = add(&mut w, 1, "Alice");
        let b = add(&mut w, 2, "Bob");
        w.pvp_command(1, PvpCommand::Flag { enabled: true });
        assert!(w.pvp_attack(1, &b).is_err());
        w.pvp_command(2, PvpCommand::Flag { enabled: true });
        w.players.get_mut(&2).unwrap().character.hp = 1.;
        for _ in 0..20 {
            w.players.get_mut(&1).unwrap().cooldown = 0.;
            if w.players[&2].character.hp <= 0. {
                break;
            }
            w.pvp_attack(1, &b).unwrap();
        }
        assert_eq!(w.players[&2].character.hp, 0.);
        assert!(!w.players[&2].pvp_flag);
        assert_eq!(w.players[&2].character.xp, 0);
        assert!(w.pvp_attack(1, &a).is_err());
    }
    #[test]
    fn arena_queues_make_private_match_and_restore_players() {
        let mut w = world();
        let a = add(&mut w, 1, "Alice");
        let b = add(&mut w, 2, "Bob");
        w.pvp_command(1, PvpCommand::ArenaQueue { size: 1 });
        assert_eq!(w.pvp.queue.len(), 1);
        w.pvp_command(2, PvpCommand::ArenaQueue { size: 1 });
        assert!(w.pvp.queue.is_empty());
        assert_eq!(w.pvp.matches.len(), 1);
        let zone = w.pvp.matches[0].zone;
        assert!(w.is_arena_zone(zone));
        assert_eq!(w.public_zone(zone), 40);
        assert_eq!(w.players[&1].character.zone, zone);
        assert_eq!(w.players[&2].character.zone, zone);
        assert!(w.pvp_attack(1, &b).is_err()); // opposite ends of the ring
        w.pvp_command(1, PvpCommand::ArenaLeave);
        assert!(w.pvp.matches.is_empty());
        assert_eq!(w.players[&1].character.zone, 0);
        assert_eq!(w.players[&2].character.zone, 0);
        assert!(w.online(&a).is_some());
    }
    #[test]
    fn arena_winner_is_last_team_standing_without_xp_loss() {
        let mut w = world();
        let _a = add(&mut w, 1, "Alice");
        let b = add(&mut w, 2, "Bob");
        w.pvp_command(1, PvpCommand::ArenaQueue { size: 1 });
        w.pvp_command(2, PvpCommand::ArenaQueue { size: 1 });
        let p = w.players.get_mut(&1).unwrap();
        p.character.x = 22.;
        p.character.y = 13.;
        p.character.attributes.accuracy = 20;
        w.players.get_mut(&2).unwrap().character.hp = 2.;
        w.pvp_attack(1, &b).unwrap();
        assert!(w.pvp.matches.is_empty());
        assert_eq!(w.players[&1].character.zone, 0);
        assert_eq!(w.players[&2].character.zone, 0);
        assert_eq!(w.players[&2].character.xp, 0);
    }
    #[test]
    fn arena_rejects_wrong_party_size_and_keeps_old_copy_ids() {
        let mut w = world();
        let _a = add(&mut w, 1, "Alice");
        assert!(w.pvp_queue(&w.players[&1].character.id.clone(), 2).is_err());
        assert_eq!(w.maps[40].name, "The Arena");
        assert!(
            w.instance_at(40).is_none(),
            "public arena template stays inert"
        );
        assert!(w.is_arena_zone(w.maps.len() - 1));
    }
    #[test]
    fn party_teams_queue_at_two_and_three_and_cannot_hit_allies() {
        for size in [2, 3] {
            let mut w = world();
            let ids: Vec<_> = (1..=size * 2)
                .map(|n| add(&mut w, n as u64, &format!("Hero{n}")))
                .collect();
            for side in 0..2 {
                let leader = side * size;
                for member in leader + 1..leader + size {
                    w.message(
                        (leader + 1) as u64,
                        ClientMessage::Social {
                            command: SocialCommand::PartyInvite {
                                id: Some(ids[member].clone()),
                                name: None,
                            },
                        },
                    );
                    w.message(
                        (member + 1) as u64,
                        ClientMessage::Social {
                            command: SocialCommand::PartyAccept {
                                id: ids[leader].clone(),
                            },
                        },
                    );
                }
            }
            w.pvp_command(1, PvpCommand::ArenaQueue { size });
            w.pvp_command((size + 1) as u64, PvpCommand::ArenaQueue { size });
            assert_eq!(w.pvp.matches.len(), 1, "{size}v{size} should start");
            assert_eq!(w.pvp.matches[0].teams[0].len(), size);
            assert!(
                w.pvp_attack(1, &ids[1]).is_err(),
                "friendly fire is refused"
            );
            w.pvp_command(1, PvpCommand::ArenaLeave);
            assert!(w.pvp.matches.is_empty());
            w.pvp_command(1, PvpCommand::ArenaQueue { size });
            assert_eq!(w.pvp.queue.len(), 1);
            w.message(
                2,
                ClientMessage::Social {
                    command: SocialCommand::PartyLeave,
                },
            );
            w.update_pvp();
            assert!(w.pvp.queue.is_empty(), "changed parties leave the queue");
        }
    }

    /// Three mages in a row at level 40: 1 casts, 2 is next to it, 3 stands behind 2.
    fn mages() -> (World, [String; 3]) {
        let mut w = world();
        let ids = [
            add(&mut w, 1, "Alice"),
            add(&mut w, 2, "Bob"),
            add(&mut w, 3, "Cara"),
        ];
        for session in 1..=3 {
            let c = &mut w.players.get_mut(&session).unwrap().character;
            c.look.class = Class::Mage;
            c.level = 40;
            c.hp = c.max_hp();
            c.reset_resource();
        }
        w.players.get_mut(&1).unwrap().character.attributes.accuracy = 20;
        (w, ids)
    }
    fn hp(w: &World, session: u64) -> f64 {
        w.players[&session].character.hp
    }
    #[test]
    fn skills_hurt_the_duel_partner_and_nobody_else() {
        for skill in ["arcanestorm", "chainlightning", "meteor", "lifedrain"] {
            let (mut w, ids) = mages();
            w.pvp_command(1, PvpCommand::DuelRequest { id: ids[1].clone() });
            w.pvp_command(2, PvpCommand::DuelAccept { id: ids[0].clone() });
            let max = [hp(&w, 2), hp(&w, 3)];
            w.use_skill(1, skill, Point { x: 1., y: 0. });
            assert!(hp(&w, 2) < max[0], "{skill} did not hurt the partner");
            assert!(hp(&w, 2) >= 1., "{skill} took the partner below 1 health");
            assert_eq!(hp(&w, 3), max[1], "{skill} hurt a bystander");
        }
    }
    #[test]
    fn skills_hurt_nobody_without_a_duel_an_arena_or_two_flags() {
        let (mut w, _) = mages();
        let max = hp(&w, 2);
        w.use_skill(1, "arcanestorm", Point { x: 1., y: 0. });
        assert_eq!(hp(&w, 2), max, "no consent at all");
        w.players.get_mut(&1).unwrap().pvp_flag = true;
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        w.use_skill(1, "arcanestorm", Point { x: 1., y: 0. });
        assert_eq!(hp(&w, 2), max, "only the caster was flagged");
        w.players.get_mut(&2).unwrap().pvp_flag = true;
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        w.use_skill(1, "arcanestorm", Point { x: 1., y: 0. });
        assert!(hp(&w, 2) < max, "both flagged");
        assert_eq!(hp(&w, 3), max, "the unflagged bystander");
    }
    #[test]
    fn a_skill_bolt_hurts_a_duelist_but_a_basic_bolt_does_not() {
        let (mut w, ids) = mages();
        w.pvp_command(1, PvpCommand::DuelRequest { id: ids[1].clone() });
        w.pvp_command(2, PvpCommand::DuelAccept { id: ids[0].clone() });
        let max = hp(&w, 2);
        w.players.get_mut(&1).unwrap().face = Point { x: 1., y: 0. };
        w.strike(1);
        assert!(!w.bolts.is_empty());
        for _ in 0..30 {
            w.update_bolts();
        }
        assert_eq!(hp(&w, 2), max, "the basic bolt is not a PvP blow");
        w.bolts.clear();
        w.use_skill(1, "twinbolt", Point { x: 1., y: 0. });
        assert!(!w.bolts.is_empty());
        for _ in 0..30 {
            w.update_bolts();
        }
        assert!(hp(&w, 2) < max, "the skill bolt landed");
        assert_eq!(hp(&w, 3), max);
    }
    #[test]
    fn a_skill_cannot_take_a_duelist_below_one_health_and_ends_the_duel() {
        let (mut w, ids) = mages();
        w.pvp_command(1, PvpCommand::DuelRequest { id: ids[1].clone() });
        w.pvp_command(2, PvpCommand::DuelAccept { id: ids[0].clone() });
        w.players.get_mut(&2).unwrap().character.hp = 2.;
        w.use_skill(1, "arcanestorm", Point { x: 1., y: 0. });
        assert_eq!(hp(&w, 2), 1.);
        assert!(w.pvp.duels.is_empty(), "the duel ended");
    }
    #[test]
    fn skills_cannot_hurt_a_party_mate_in_world_pvp() {
        let (mut w, ids) = mages();
        w.message(
            1,
            ClientMessage::Social {
                command: SocialCommand::PartyInvite {
                    id: Some(ids[1].clone()),
                    name: None,
                },
            },
        );
        w.message(
            2,
            ClientMessage::Social {
                command: SocialCommand::PartyAccept { id: ids[0].clone() },
            },
        );
        assert!(w.party_mates(&ids[0]).contains(&ids[1]));
        w.players.get_mut(&1).unwrap().pvp_flag = true;
        w.players.get_mut(&2).unwrap().pvp_flag = true;
        let max = hp(&w, 2);
        w.use_skill(1, "arcanestorm", Point { x: 1., y: 0. });
        assert_eq!(hp(&w, 2), max);
    }
    #[test]
    fn arena_skills_reach_the_other_team_and_never_the_own() {
        let mut w = world();
        let ids: Vec<_> = (1..=4)
            .map(|n| add(&mut w, n as u64, &format!("Hero{n}")))
            .collect();
        for (leader, member) in [(0usize, 1usize), (2, 3)] {
            w.message(
                (leader + 1) as u64,
                ClientMessage::Social {
                    command: SocialCommand::PartyInvite {
                        id: Some(ids[member].clone()),
                        name: None,
                    },
                },
            );
            w.message(
                (member + 1) as u64,
                ClientMessage::Social {
                    command: SocialCommand::PartyAccept {
                        id: ids[leader].clone(),
                    },
                },
            );
        }
        w.pvp_command(1, PvpCommand::ArenaQueue { size: 2 });
        w.pvp_command(3, PvpCommand::ArenaQueue { size: 2 });
        assert_eq!(w.pvp.matches.len(), 1);
        assert!(!w.pvp_legal(1, 2), "an ally");
        assert!(!w.pvp_legal(1, 1), "oneself");
        assert!(w.pvp_legal(1, 3) && w.pvp_legal(1, 4), "the other team");
        assert!(
            w.foes_near(1, w.players[&1].character.point(), 1000., &[])
                .len()
                == 2
        );
    }
    /// The mages of `mages()` with player 1 turned into `class` at level 40.
    fn stunner(class: Class) -> (World, [String; 3]) {
        let (mut w, ids) = mages();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.look.class = class;
        c.reset_resource();
        c.change_resource(100.);
        // A sturdy target, so one stunning blow does not end the duel (which would free the stun).
        let c = &mut w.players.get_mut(&2).unwrap().character;
        c.level = 99;
        c.hp = c.max_hp();
        w.pvp_command(1, PvpCommand::DuelRequest { id: ids[1].clone() });
        w.pvp_command(2, PvpCommand::DuelAccept { id: ids[0].clone() });
        (w, ids)
    }
    #[test]
    fn warrior_assassin_and_hunter_each_have_a_three_second_stun_skill_of_about_fifteen_seconds() {
        for (class, id) in [
            (Class::Warrior, "earthshatter"),
            (Class::Assassin, "knifering"),
            (Class::Hunter, "rainofarrows"),
        ] {
            let skill = skills::find(class, id).unwrap();
            assert_eq!(skill.stun, 3., "{id}");
            assert!(
                (12. ..=15.).contains(&skill.cooldown),
                "{id}: {}",
                skill.cooldown
            );
        }
        let stunners: Vec<_> = skills::SKILLS.iter().filter(|s| s.stun > 0.).collect();
        assert_eq!(stunners.len(), 3, "only those three stun");
        let storm = skills::find(Class::Mage, "arcanestorm").unwrap();
        assert_eq!((storm.root, storm.stun), (3., 0.));
        assert!((12. ..=15.).contains(&storm.cooldown));
        let rooters: Vec<_> = skills::SKILLS.iter().filter(|s| s.root > 0.).collect();
        assert_eq!(rooters.len(), 1, "only Arcane Storm roots");
    }
    #[test]
    fn a_stunning_skill_holds_the_player_it_hits_for_three_seconds() {
        for (class, id) in [
            (Class::Warrior, "earthshatter"),
            (Class::Assassin, "knifering"),
            (Class::Hunter, "rainofarrows"),
        ] {
            let (mut w, _) = stunner(class);
            for _ in 0..40 {
                w.players.get_mut(&1).unwrap().character.attributes.accuracy = 100;
                w.use_skill(1, id, Point { x: 1., y: 0. });
                tick(&mut w, 40);
                if w.players[&2].stun > 0. || w.pvp.duels.is_empty() {
                    break;
                }
                w.players.get_mut(&1).unwrap().skill_cd.clear();
                let c = &mut w.players.get_mut(&1).unwrap().character;
                c.reset_resource();
                c.change_resource(100.);
                w.players.get_mut(&2).unwrap().character.hp = w.players[&2].character.max_hp();
            }
            let stun = w.players[&2].stun;
            assert!(stun > 0. && stun <= 3., "{id}: stun {stun}");
            assert_eq!(w.players[&3].stun, 0., "a bystander is not stunned");
            let at = w.players[&2].character.point();
            w.message(
                2,
                ClientMessage::Move {
                    x: at.x + 5.,
                    y: at.y,
                },
            );
            w.players.get_mut(&2).unwrap().skill_cd.clear();
            w.use_skill(2, "arcanestorm", Point { x: -1., y: 0. });
            assert!(w.players[&2].skill_cd.is_empty(), "no cast while stunned");
            w.players.get_mut(&2).unwrap().cooldown = 0.;
            assert!(
                w.pvp_attack(2, &w.players[&1].character.id.clone())
                    .is_err()
            );
            for _ in 0..30 {
                w.step();
            }
            assert_eq!(
                w.players[&2].character.point(),
                at,
                "{id}: no walking while stunned"
            );
            tick(&mut w, 40);
            assert_eq!(w.players[&2].stun, 0., "the stun wears off");
        }
    }
    #[test]
    fn skills_without_a_stun_and_the_end_of_a_duel_leave_no_stun() {
        let (mut w, _) = stunner(Class::Warrior);
        w.players.get_mut(&1).unwrap().character.attributes.accuracy = 100;
        w.use_skill(1, "cleave", Point { x: 1., y: 0. });
        assert_eq!(w.players[&2].stun, 0., "cleave does not stun");
        w.players.get_mut(&2).unwrap().stun = 2.;
        w.pvp_command(1, PvpCommand::DuelCancel);
        assert_eq!(
            w.players[&2].stun, 0.,
            "the duel's end frees a stunned duelist"
        );
    }
    #[test]
    fn a_blow_on_a_player_is_scaled_by_the_pvp_damage_scale() {
        let (mut w, _) = mages();
        w.players.get_mut(&2).unwrap().character.hp = w.players[&2].character.max_hp();
        w.players.get_mut(&1).unwrap().pvp_flag = true;
        w.players.get_mut(&2).unwrap().pvp_flag = true;
        let defence = w.players[&2].character.stats().1;
        let damage = 4000.;
        let before = hp(&w, 2);
        let mut lost = 0.;
        for _ in 0..20 {
            let taken = w.pvp_hit(1, 2, damage, false);
            if taken > 0. {
                lost = taken;
                break;
            }
        }
        let expected = ((damage - defence) * DAMAGE_TAKEN_SCALE * PVP_DAMAGE_SCALE).round();
        assert_eq!(lost, expected);
        // Less than the same blow would take off the player in a fight against a monster.
        let from_a_monster = ((damage - defence) * DAMAGE_TAKEN_SCALE).round();
        assert!(lost < from_a_monster, "{lost} against {from_a_monster}");
        assert_eq!(before - hp(&w, 2), expected);
    }
    #[test]
    fn a_rooting_skill_stops_walking_and_dashes_but_not_attacks_or_casts() {
        let (mut w, ids) = stunner(Class::Mage);
        // Player 2 is a level 99 mage too (blink is a dash), standing next to player 1.
        w.players.get_mut(&1).unwrap().character.attributes.accuracy = 100;
        for _ in 0..40 {
            w.use_skill(1, "arcanestorm", Point { x: 1., y: 0. });
            if w.players[&2].root > 0. {
                break;
            }
            w.players.get_mut(&1).unwrap().skill_cd.clear();
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.reset_resource();
            w.players.get_mut(&2).unwrap().character.hp = w.players[&2].character.max_hp();
        }
        let root = w.players[&2].root;
        assert!(root > 0. && root <= 3., "root {root}");
        assert_eq!(w.players[&2].stun, 0., "a root is not a stun");
        assert_eq!(w.players[&3].root, 0.);
        let at = w.players[&2].character.point();
        w.message(
            2,
            ClientMessage::Move {
                x: at.x + 5.,
                y: at.y,
            },
        );
        w.message(2, ClientMessage::Input { dx: 1., dy: 0. });
        tick(&mut w, 20);
        assert_eq!(
            w.players[&2].character.point(),
            at,
            "no walking while rooted"
        );
        w.players.get_mut(&2).unwrap().skill_cd.clear();
        w.use_skill(2, "blink", Point { x: 1., y: 0. });
        assert!(
            !w.players[&2].skill_cd.contains_key("blink"),
            "no dash while rooted"
        );
        assert_eq!(w.players[&2].character.point(), at);
        w.use_skill(2, "twinbolt", Point { x: -1., y: 0. });
        assert!(
            w.players[&2].skill_cd.contains_key("twinbolt"),
            "casting still works"
        );
        w.players.get_mut(&2).unwrap().cooldown = 0.;
        assert!(w.pvp_attack(2, &ids[0]).is_ok(), "attacking still works");
        tick(&mut w, 40);
        assert_eq!(w.players[&2].root, 0., "the root wears off");
        w.message(
            2,
            ClientMessage::Move {
                x: at.x + 2.,
                y: at.y,
            },
        );
        tick(&mut w, 20);
        assert!(w.players[&2].character.point() != at, "free to walk again");
    }
    #[test]
    fn warrior_assassin_mage_and_hunter_each_have_a_long_skill_that_halves_healing_for_ten_seconds()
    {
        for (class, id) in [
            (Class::Warrior, "titanswrath"),
            (Class::Assassin, "thousandcuts"),
            (Class::Mage, "starfall"),
            (Class::Hunter, "arrowstorm"),
        ] {
            let skill = skills::find(class, id).unwrap();
            assert_eq!((skill.wound, skill.wound_time), (0.5, 10.), "{id}");
            assert!(skill.cooldown >= 28., "{id}: {} s", skill.cooldown);
        }
        let all: Vec<_> = skills::SKILLS.iter().filter(|s| s.wound > 0.).collect();
        assert_eq!(all.len(), 4, "the priest has none");
        assert!(all.iter().all(|s| s.class != Class::Priest));
    }
    #[test]
    fn a_wounding_skill_cuts_the_healing_of_the_player_it_hits_and_wears_off() {
        let (mut w, _) = stunner(Class::Warrior);
        w.players.get_mut(&1).unwrap().character.attributes.accuracy = 100;
        for _ in 0..40 {
            w.use_skill(1, "titanswrath", Point { x: 1., y: 0. });
            if w.players[&2].wound_left > 0. {
                break;
            }
            w.players.get_mut(&1).unwrap().skill_cd.clear();
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.reset_resource();
            c.change_resource(100.);
            w.players.get_mut(&2).unwrap().character.hp = w.players[&2].character.max_hp();
        }
        let p = &w.players[&2];
        assert_eq!(p.wound, 0.5);
        // Half from the wound, and the PvP scale because the blow that wounded also started a fight.
        assert_eq!(p.heal_factor(), 0.5 * PVP_DAMAGE_SCALE);
        assert!(p.wound_left > 9. && p.wound_left <= 10., "{}", p.wound_left);
        assert_eq!(w.players[&3].wound_left, 0., "a bystander");
        tick(&mut w, 205);
        assert_eq!(w.players[&2].wound_left, 0., "wears off");
        assert_eq!(w.players[&2].heal_factor(), 1.);
    }
    #[test]
    fn a_wound_halves_skill_heals_lifesteal_and_potions() {
        // Second Wind heals 40% of the maximum health.
        let heal_gain = |wounded: bool| {
            let (mut w, _) = mages();
            let c = &mut w.players.get_mut(&2).unwrap().character;
            c.look.class = Class::Warrior;
            c.level = 40;
            c.reset_resource();
            c.change_resource(100.);
            c.hp = c.max_hp() * 0.2;
            if wounded {
                let p = w.players.get_mut(&2).unwrap();
                p.wound = 0.5;
                p.wound_left = 10.;
            }
            let before = hp(&w, 2);
            w.use_skill(2, "secondwind", Point { x: 1., y: 0. });
            hp(&w, 2) - before
        };
        let (free, cut) = (heal_gain(false), heal_gain(true));
        assert!(free > 0.);
        assert!((cut - free / 2.).abs() < 1., "{cut} against {free}");
        // A health potion.
        let potion = |wounded: bool| {
            let (mut w, _) = mages();
            let id = crate::items::best_tier("health_potion", 40)
                .unwrap()
                .id
                .clone();
            let p = w.players.get_mut(&2).unwrap();
            p.character.add_item(&id, 1);
            p.character.hp = p.character.max_hp() * 0.2;
            if wounded {
                p.wound = 0.5;
                p.wound_left = 10.;
            }
            let before = hp(&w, 2);
            w.use_item(2, &id);
            hp(&w, 2) - before
        };
        let (free, cut) = (potion(false), potion(true));
        assert!(free > 0.);
        assert!((cut - free / 2.).abs() < 1., "{cut} against {free}");
    }
    #[test]
    fn healing_is_scaled_like_damage_while_in_a_pvp_fight() {
        let (mut w, _) = stunner(Class::Warrior);
        {
            let c = &mut w.players.get_mut(&2).unwrap().character;
            c.look.class = Class::Warrior;
            c.reset_resource();
            c.change_resource(100.);
        }
        assert_eq!(w.players[&2].heal_factor(), 1., "no fight yet");
        for _ in 0..40 {
            if w.pvp_hit(1, 2, 400., false) > 0. {
                break;
            }
        }
        for session in [1, 2] {
            let p = &w.players[&session];
            assert!(p.pvp_fight > 9. && p.pvp_fight <= 10., "{}", p.pvp_fight);
            assert_eq!(p.heal_factor(), PVP_DAMAGE_SCALE);
        }
        assert_eq!(w.players[&3].heal_factor(), 1., "a bystander heals in full");
        // Second Wind (40% of the maximum) heals PVP_DAMAGE_SCALE as much as outside a fight.
        let max = w.players[&2].character.max_hp();
        let gain = |w: &mut World| {
            let p = w.players.get_mut(&2).unwrap();
            p.character.hp = max * 0.2;
            p.skill_cd.clear();
            p.character.change_resource(100.);
            w.use_skill(2, "secondwind", Point { x: -1., y: 0. });
            hp(w, 2) - max * 0.2
        };
        let scaled = gain(&mut w);
        w.players.get_mut(&2).unwrap().pvp_fight = 0.;
        let free = gain(&mut w);
        assert!(free > 0.);
        assert!(
            (scaled - free * PVP_DAMAGE_SCALE).abs() < 1.,
            "{scaled} against {free}"
        );
        w.players.get_mut(&2).unwrap().pvp_fight = PVP_FIGHT_TIME;
        tick(&mut w, 205);
        // The duel may have ended meanwhile, which clears the flag; either way it is gone after ten seconds.
        assert_eq!(w.players[&2].heal_factor(), 1.);
        // The end of a duel clears it at once.
        let (mut w, _) = stunner(Class::Warrior);
        for _ in 0..40 {
            if w.pvp_hit(1, 2, 400., false) > 0. {
                break;
            }
        }
        assert!(w.players[&2].pvp_fight > 0.);
        w.pvp_command(1, PvpCommand::DuelCancel);
        assert_eq!(w.players[&2].heal_factor(), 1.);
    }
    #[test]
    fn a_hunter_deals_a_quarter_more_to_players_and_nobody_else_does() {
        let taken = |class: Class| {
            let (mut w, _) = mages();
            w.players.get_mut(&1).unwrap().character.look.class = class;
            w.players.get_mut(&1).unwrap().pvp_flag = true;
            w.players.get_mut(&2).unwrap().pvp_flag = true;
            for _ in 0..40 {
                let before = hp(&w, 2);
                if w.pvp_hit(1, 2, 4000., false) > 0. {
                    return (before - hp(&w, 2), w.players[&2].character.stats().1);
                }
            }
            panic!("never landed");
        };
        let (hunter, defence) = taken(Class::Hunter);
        let (warrior, _) = taken(Class::Warrior);
        assert_eq!(
            hunter,
            ((4000. * PVP_HUNTER_DAMAGE - defence) * DAMAGE_TAKEN_SCALE * PVP_DAMAGE_SCALE).round()
        );
        assert_eq!(
            warrior,
            ((4000. - defence) * DAMAGE_TAKEN_SCALE * PVP_DAMAGE_SCALE).round()
        );
        assert!(hunter > warrior);
    }
}
