//! Eldmarr weapons. Transient effects are server owned, bounded, and never proc
//! from another proc or set bonus. The existing skill id retains its bar slot,
//! cost, cooldown and PvP numbers; only the equipped weapon grants the addition.
use super::*;

#[derive(Default)]
pub(super) struct State {
    pub(super) cooldown: BTreeMap<u64, f64>,
    pub(super) warm: BTreeMap<u64, f64>,
    stacks: BTreeMap<(u64, Target), (u32, f64)>,
    pub(super) pending: Vec<Pending>,
}
impl State {
    pub(super) fn cancel_active(&mut self, session: u64) {
        self.pending.retain(|p| p.owner != session);
        self.warm.remove(&session);
        self.stacks.retain(|(s, _), _| *s != session);
        // Keep the proc cooldown: swapping weapons must never bypass it.
    }
}
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub(super) enum Target {
    Enemy(usize),
    Player(u64),
}
#[derive(Clone, Copy)]
enum Effect {
    Burn(Target),
    Orbit,
    Ground(Point),
    Ward,
}
pub(super) struct Pending {
    owner: u64,
    zone: usize,
    effect: Effect,
    next: f64,
    ticks: u32,
    interval: f64,
    damage: f64,
    players: bool,
    player_share: f64,
}

pub(super) fn weapon(c: &Character) -> Option<&'static Item> {
    c.worn_items().into_iter().find(|i| {
        i.kind == "weapon"
            && i.source.as_deref() == Some(raid_rewards::SOURCE)
            && i.class == Some(c.look.class)
            && c.level >= i.required_level
    })
}

impl World {
    fn forge_basic(&self, session: u64) -> f64 {
        (self.raid_attack_power(session) * DAMAGE_DEALT_SCALE)
            .round()
            .max(1.)
    }

    fn forge_ready(&self, session: u64) -> bool {
        self.players
            .get(&session)
            .is_some_and(|p| p.character.hp > 0. && weapon(&p.character).is_some())
    }

    fn forge_at(&self, target: Target, zone: usize) -> Option<Point> {
        match target {
            Target::Enemy(id) => self
                .slimes
                .get(id)
                .filter(|s| !s.dead && s.zone == zone)
                .map(Slime::point),
            Target::Player(s) => self
                .players
                .get(&s)
                .filter(|p| p.character.hp > 0. && p.character.zone == zone)
                .map(|p| p.character.point()),
        }
    }

    /// The cap is per activation, shared across all targets/ticks; even a large
    /// critical skill cannot multiply it. Player damage still passes pvp_hit.
    pub(super) fn forge_hit(&mut self, owner: u64, target: Target, damage: f64) {
        self.forge_hit_limited(owner, target, damage, 1.);
    }
    fn forge_hit_limited(&mut self, owner: u64, target: Target, damage: f64, player_share: f64) {
        if !self.forge_ready(owner) {
            return;
        }
        let zone = self.players[&owner].character.zone;
        let Some(at) = self.forge_at(target, zone) else {
            return;
        };
        let from = self.players[&owner].character.point();
        if !self.maps[zone].line_clear(from, at, 0.05) {
            return;
        }
        let previous = std::mem::replace(&mut self.cur_skill, "chainforged_proc".into());
        match target {
            Target::Enemy(id) => {
                self.hit_slime(id, owner, damage, false);
            }
            Target::Player(s) => {
                let cap = self.players[&s].character.max_hp() * 0.03 * player_share;
                if cap < 1. {
                    self.cur_skill = previous;
                    return;
                }
                self.pvp_hit(owner, s, damage.min(cap), false);
            }
        }
        self.cur_skill = previous;
    }

    fn forge_targets(
        &self,
        owner: u64,
        at: Point,
        range: f64,
        players: bool,
        skip: Option<Target>,
    ) -> Vec<Target> {
        let zone = self.players[&owner].character.zone;
        let mut result = self
            .enemies_near(zone, at, range, &[])
            .into_iter()
            .map(Target::Enemy)
            .collect::<Vec<_>>();
        if players {
            result.extend(
                self.foes_near(owner, at, range, &[])
                    .into_iter()
                    .map(Target::Player),
            );
        }
        result.retain(|t| {
            Some(*t) != skip
                && self
                    .forge_at(*t, zone)
                    .is_some_and(|p| self.maps[zone].line_clear(at, p, 0.05))
        });
        result.sort_by(|a, b| {
            self.forge_at(*a, zone)
                .unwrap()
                .distance(at)
                .total_cmp(&self.forge_at(*b, zone).unwrap().distance(at))
        });
        result
    }

    fn forge_event(&mut self, session: u64, at: Point, kind: &str) {
        let p = &self.players[&session];
        self.emit_zone(
            p.character.zone,
            json!({"type":"event","kind":"forgeProc","actor":p.character.id,
            "x":at.x,"y":at.y,"fx":p.face.x,"fy":p.face.y,"weapon":p.character.look.class,"effect":kind}),
        );
    }

    pub(super) fn signature_hit(&mut self, session: u64, target: Target, dealt: f64) {
        if dealt <= 0.
            || !self.forge_ready(session)
            || self.cur_skill == "set_bonus"
            || self.cur_skill.starts_with("chainforged_")
            || self
                .signature
                .cooldown
                .get(&session)
                .is_some_and(|t| *t > self.time)
        {
            return;
        }
        let p = &self.players[&session];
        let class = p.character.look.class;
        if class == Class::Priest || (class == Class::Mage && self.cur_skill.is_empty()) {
            return;
        }
        let chance = match class {
            Class::Warrior => 0.08,
            Class::Mage | Class::Hunter => 0.10,
            Class::Assassin => 1.,
            _ => 0.,
        };
        if self.random() >= chance {
            return;
        }
        let p = &self.players[&session];
        let zone = p.character.zone;
        let origin = p.character.point();
        let face = p.face;
        let at = self.forge_at(target, zone).unwrap_or(origin);
        let basic = self.forge_basic(session);
        self.signature.cooldown.insert(session, self.time + 3.);
        match class {
            Class::Warrior => {
                let mut targets = self.forge_targets(session, origin, 12., true, None);
                targets.retain(|t| {
                    let q = self.forge_at(*t, zone).unwrap();
                    let d = origin.direction(q);
                    d.x * face.x + d.y * face.y >= 0.8
                });
                targets.truncate(3);
                let damage = (dealt * 0.6).min(basic * 0.6) / targets.len().max(1) as f64;
                for t in targets {
                    self.forge_hit(session, t, damage);
                }
            }
            Class::Mage => self.signature.pending.push(Pending {
                owner: session,
                zone,
                effect: Effect::Orbit,
                next: self.time + 1.5,
                ticks: 4,
                interval: 1.5,
                damage: basic * 0.12,
                players: true,
                player_share: 0.25,
            }),
            Class::Assassin => {
                let old = self
                    .signature
                    .stacks
                    .get(&(session, target))
                    .filter(|(_, until)| *until > self.time)
                    .map_or(0, |(n, _)| *n);
                let stacks = (old + 1).min(5);
                self.signature
                    .stacks
                    .insert((session, target), (stacks, self.time + 6.));
                // One burn per target: refresh replaces its unspent ticks, never duplicates them.
                self.signature.pending.retain(|p| {
                    !(p.owner == session && matches!(p.effect,Effect::Burn(t) if t==target))
                });
                self.signature.pending.push(Pending {
                    owner: session,
                    zone,
                    effect: Effect::Burn(target),
                    next: self.time + 1.,
                    ticks: 4,
                    interval: 1.,
                    damage: basic * 0.01 * f64::from(stacks),
                    players: true,
                    player_share: 0.25,
                });
            }
            Class::Hunter => {
                let mut targets = self.forge_targets(session, at, 6., true, Some(target));
                targets.truncate(2);
                let damage = (dealt * 0.5).min(basic * 0.3);
                for t in targets {
                    self.forge_hit(session, t, damage);
                }
            }
            _ => {}
        }
        self.forge_event(session, at, "proc");
    }

    /// Consume Warmth on the next effective heal, not on an overheal/fizzled cast.
    pub(super) fn signature_heal_multiplier(&mut self, session: u64, sessions: &[u64]) -> f64 {
        if !self.forge_ready(session) || self.players[&session].pvp_fight > 0. {
            return 1.;
        }
        if self
            .signature
            .warm
            .get(&session)
            .is_some_and(|t| *t > self.time)
            && sessions.iter().any(|s| {
                self.players
                    .get(s)
                    .is_some_and(|p| p.character.hp < p.character.max_hp())
            })
        {
            self.signature.warm.remove(&session);
            1.10
        } else {
            1.
        }
    }

    pub(super) fn signature_healed(&mut self, session: u64, target: u64, gained: f64) {
        if gained <= 0.
            || !self.forge_ready(session)
            || self.players[&session].character.look.class != Class::Priest
            || self
                .signature
                .cooldown
                .get(&session)
                .is_some_and(|t| *t > self.time)
            || self.random() >= 0.08
        {
            return;
        }
        self.signature.cooldown.insert(session, self.time + 3.);
        let p = self.players.get_mut(&target).unwrap();
        p.forge_ward = p
            .forge_ward
            .max(p.character.max_hp() * 0.03 * p.heal_factor_by(Class::Priest));
        p.forge_ward_left = 4.;
        let at = p.character.point();
        self.forge_event(session, at, "ward");
    }

    pub(super) fn signature_skill(&mut self, session: u64, id: &str) {
        if !self.forge_ready(session) {
            return;
        }
        let p = &self.players[&session];
        let c = &p.character;
        let class = c.look.class;
        let zone = c.zone;
        let origin = c.point();
        let face = p.face;
        let basic = self.forge_basic(session);
        let expected = match class {
            Class::Warrior => "earthshatter",
            Class::Mage => "arcaneward",
            Class::Assassin => "knifering",
            Class::Priest => "mend",
            Class::Hunter => "arrowstorm",
        };
        if id != expected {
            return;
        }
        match class {
            Class::Warrior | Class::Assassin => {
                // Short burning patches along the fissure / behind the knife ring.
                let at = if class == Class::Warrior {
                    Point {
                        x: origin.x + face.x * 2.,
                        y: origin.y + face.y * 2.,
                    }
                } else {
                    origin
                };
                let patches = if class == Class::Assassin { 3 } else { 1 };
                for n in 0..patches {
                    let center = Point {
                        x: at.x - face.x * n as f64 * 1.5,
                        y: at.y - face.y * n as f64 * 1.5,
                    };
                    self.signature.pending.push(Pending {
                        owner: session,
                        zone,
                        effect: Effect::Ground(center),
                        next: self.time + 1.,
                        ticks: 4,
                        interval: 1.,
                        damage: basic * 0.05 / f64::from(patches),
                        players: false,
                        player_share: 1.,
                    });
                }
            }
            Class::Mage => {
                let left = p.buffs.iter().find(|b| b.id == id).map_or(8., |b| b.left);
                self.signature.pending.push(Pending {
                    owner: session,
                    zone,
                    effect: Effect::Ward,
                    next: self.time + left,
                    ticks: 1,
                    interval: 1.,
                    damage: basic * 0.2,
                    players: false,
                    player_share: 1.,
                });
            }
            Class::Priest => {
                self.signature.warm.insert(session, self.time + 15.);
            }
            Class::Hunter => {
                let target = self
                    .forge_targets(session, origin, 8., false, None)
                    .into_iter()
                    .next();
                if let Some(t) = target {
                    self.forge_hit(session, t, basic * 0.2);
                }
            }
        }
        self.forge_event(session, origin, "skill");
    }

    pub(super) fn update_signatures(&mut self) {
        let mut pending = std::mem::take(&mut self.signature.pending);
        for mut p in pending.drain(..) {
            if !self.forge_ready(p.owner) || self.players[&p.owner].character.zone != p.zone {
                continue;
            }
            if self.time + 1e-6 >= p.next {
                let origin = self.players[&p.owner].character.point();
                let targets = match p.effect {
                    Effect::Burn(t) => vec![t],
                    Effect::Orbit => self
                        .forge_targets(p.owner, origin, 8., p.players, None)
                        .into_iter()
                        .take(1)
                        .collect(),
                    Effect::Ground(at) => self.forge_targets(p.owner, at, 2.5, p.players, None),
                    Effect::Ward => self.forge_targets(p.owner, origin, 3., p.players, None),
                };
                let damage = p.damage / targets.len().max(1) as f64;
                for t in targets {
                    self.forge_hit_limited(p.owner, t, damage, p.player_share);
                }
                p.ticks -= 1;
                p.next += p.interval;
            }
            if p.ticks > 0 {
                self.signature.pending.push(p);
            }
        }
        self.signature
            .cooldown
            .retain(|s, t| *t > self.time && self.players.contains_key(s));
        self.signature
            .warm
            .retain(|s, t| *t > self.time && self.players.contains_key(s));
        self.signature
            .stacks
            .retain(|(s, _), (_, t)| *t > self.time && self.players.contains_key(s));
    }
}
