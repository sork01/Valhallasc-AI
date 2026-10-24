//! Ember Key crosses: authoritative interruptible channels, shared heralds and personal shards.
use super::rolls::SHARE_RANGE;
use super::*;

pub const QUEST: &str = "raid_key";
pub const KIND: &str = "ember_firelord";
const CHANNEL_TIME: f64 = 3.;
const REACH: f64 = 2.6;

#[derive(Default)]
pub(super) struct State {
    channels: BTreeMap<usize, Channel>,
}
struct Channel {
    session: u64,
    cross: RaidCross,
    origin: Point,
    hurt_at: f64,
    started: f64,
}
impl World {
    fn raid_cross_slot(&self, zone: usize) -> Option<usize> {
        self.spawns
            .iter()
            .position(|s| s.zone == zone && s.kind == KIND)
    }
    fn wants_ember_shard(&self, session: u64, cross: &RaidCross) -> bool {
        let p = &self.players[&session];
        p.merc.is_none()
            && p.ambient.is_none()
            && !p.gauntlet
            && p.character.level >= 99
            && p.character
                .quests
                .iter()
                .any(|q| q.id == QUEST && !q.claimed)
            && p.character.quantity(&cross.shard) == 0
            && !self
                .drops
                .iter()
                .any(|d| d.owner == p.character.id && d.item.as_deref() == Some(&cross.shard))
    }
    pub(super) fn start_raid_channel(&mut self, session: u64, id: &str) -> Result<(), String> {
        let p = self.players.get(&session).ok_or("Unknown hero.")?;
        let zone = p.character.zone;
        let cross = self.maps[zone]
            .crosses
            .iter()
            .find(|c| c.id == id)
            .cloned()
            .ok_or("There is no cross here.")?;
        if p.character.hp <= 0.
            || p.stun > 0.
            || p.dash > 0.
            || p.character.spark_travel.is_some()
            || !self.wants_ember_shard(session, &cross)
        {
            return Err(
                "The cross is silent. You must need its Ember Shard for The Ember Key.".into(),
            );
        }
        let origin = p.character.point();
        let at = Point {
            x: cross.x,
            y: cross.y,
        };
        if origin.distance(at) > REACH || !self.maps[zone].line_clear(origin, at, 0.05) {
            return Err("Stand beside the cross to commune with it.".into());
        }
        let slot = self.raid_cross_slot(zone).ok_or("The cross is silent.")?;
        if !self.slimes[slot].dead || self.raid_key.channels.contains_key(&zone) {
            return Err("This cross is already awakening a Firelord.".into());
        }
        if p.character.mounted {
            return Err("Dismount before communing with the cross.".into());
        }
        // One hero can channel only one cross; explicit interaction ends walking and attacking.
        self.raid_key.channels.retain(|_, c| c.session != session);
        let p = self.players.get_mut(&session).unwrap();
        p.stop();
        p.attack = 0.;
        p.moving = false;
        self.raid_key.channels.insert(
            zone,
            Channel {
                session,
                cross,
                origin,
                hurt_at: p.last_hurt,
                started: self.time,
            },
        );
        Ok(())
    }
    pub(super) fn update_raid_key(&mut self) {
        let cancelled: Vec<_> = self
            .raid_key
            .channels
            .iter()
            .filter_map(|(&zone, c)| {
                let valid = self.players.get(&c.session).is_some_and(|p| {
                    p.character.zone == zone
                        && p.character.hp > 0.
                        && p.stun <= 0.
                        && !p.frozen
                        && p.character.spark_travel.is_none()
                        && p.dash <= 0.
                        && !p.character.mounted
                        && !p.moving
                        && p.character.point().distance(c.origin) < 0.03
                        && p.last_hurt == c.hurt_at
                        && self.wants_ember_shard(c.session, &c.cross)
                });
                (!valid).then_some(zone)
            })
            .collect();
        for zone in cancelled {
            self.raid_key.channels.remove(&zone);
        }
        let ready: Vec<_> = self
            .raid_key
            .channels
            .iter()
            .filter(|(_, c)| self.time - c.started + 1e-9 >= CHANNEL_TIME)
            .map(|(&z, _)| z)
            .collect();
        for zone in ready {
            let c = self.raid_key.channels.remove(&zone).unwrap();
            let Some(id) = self.raid_cross_slot(zone) else {
                continue;
            };
            if !self.slimes[id].dead {
                continue;
            }
            let mut s = Slime::with_level(id, &self.spawns[id], 99);
            let bodies = self.actor_bodies(zone, None, Some(id));
            let Some(at) = free_actor_position(&self.maps[zone], s.point(), s.r, &bodies, true)
            else {
                continue;
            };
            s.x = at.x;
            s.y = at.y;
            s.hunt = true;
            s.target = Some(c.session);
            s.state = "chase".into();
            s.hop = 1.5;
            s.xp = 0;
            s.gold = 0;
            self.slimes[id] = s;
            self.emit_zone(
                zone,
                json!({"type":"event","kind":"emberSummon","x":at.x,"y":at.y,"cross":c.cross.id}),
            );
        }
        // Hires and ambient actors never keep a shared summon alive after its humans leave.
        for id in 0..self.slimes.len() {
            let s = &self.slimes[id];
            if s.kind != KIND || s.dead {
                continue;
            }
            let zone = s.zone;
            if !self.players.values().any(|p| {
                p.character.zone == zone && p.merc.is_none() && p.ambient.is_none() && !p.gauntlet
            }) {
                let s = &mut self.slimes[id];
                s.dead = true;
                s.hp = 0.;
                s.state = "waiting".into();
                s.respawn = 1e9;
                s.contributors.clear();
                s.target = None;
            }
        }
    }
    pub(super) fn raid_key_drops(&mut self, id: usize, zone: usize, at: Point) {
        let Some(cross) = self.maps[zone].crosses.first().cloned() else {
            return;
        };
        let contributors = self.slimes[id].contributors.clone();
        let heroes: Vec<_> = self
            .players
            .iter()
            .filter(|(session, p)| {
                p.character.zone == zone
                    && p.character.hp > 0.
                    && p.character.point().distance(at) <= SHARE_RANGE
                    && contributors.contains(&p.character.id)
                    && self.wants_ember_shard(**session, &cross)
            })
            .map(|(_, p)| p.character.id.clone())
            .collect();
        for hero in heroes {
            self.item_drop(&hero, zone, at, &cross.shard, 1);
        }
    }
    pub(super) fn raid_cross_view(&self, zone: usize) -> Vec<Value> {
        self.maps[zone]
            .crosses
            .iter()
            .map(|c| {
                let channel = self.raid_key.channels.get(&zone);
                let alive = self
                    .raid_cross_slot(zone)
                    .is_some_and(|id| !self.slimes[id].dead);
                json!({"id":c.id,"alive":alive,"channel":channel.map(|ch| json!({
                    "actor":self.players.get(&ch.session).map(|p| &p.character.id),
                    "left":(CHANNEL_TIME-(self.time-ch.started)).max(0.)
                }))})
            })
            .collect()
    }
}
