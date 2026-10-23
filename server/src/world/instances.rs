//! Dungeons (instances). A map with `copies: N` exists N times: the zone itself and N-1 extra copies the world appends
//! after the file's zones. A party that walks into the dungeon's portal gets a copy of its own (the one a party
//! mate is already in, else a free one), so nobody else shares its enemies, bosses or loot. A copy is only simulated
//! while someone is inside; when the last hero leaves it is reset (every enemy back, the exit closed again).
//! Clients never see the copies: every snapshot reports the template's zone number, so the client has one zone.
use super::*;

#[derive(Clone, Debug)]
pub(super) struct Instance {
    /// The zone number of this copy (the template itself for the first one).
    pub zone: usize,
    /// The zone every copy copies, and what clients are told.
    pub template: usize,
    /// Someone is inside and the enemies have been touched.
    pub active: bool,
    /// The final boss is down: `after_clear` portals work.
    pub cleared: bool,
    pub rally: Option<Point>,
    pub grace_until: f64,
    pub empty_since: Option<f64>,
    pub members: Vec<String>,
    /// A game master's in-memory test multipliers for this copy (`gm_test.rs`); reset with the copy.
    pub tuning: super::gm_test::Tuning,
}

impl World {
    /// Appends the extra copies of every dungeon to `maps` and lists all copies.
    pub(super) fn make_instances(maps: &mut Vec<Map>) -> Vec<Instance> {
        let mut instances = vec![];
        for template in 0..maps.len() {
            let copies = maps[template].copies as usize;
            if copies == 0 {
                continue;
            }
            instances.push(Instance {
                zone: template,
                template,
                active: false,
                cleared: false,
                rally: None,
                grace_until: 0.,
                empty_since: None,
                members: vec![],
                tuning: Default::default(),
            });
            for _ in 1..copies {
                let mut copy = maps[template].clone();
                copy.copies = 0;
                copy.template = Some(template);
                maps.push(copy);
                instances.push(Instance {
                    zone: maps.len() - 1,
                    template,
                    active: false,
                    cleared: false,
                    rally: None,
                    grace_until: 0.,
                    empty_since: None,
                    members: vec![],
                    tuning: Default::default(),
                });
            }
        }
        instances
    }
    pub(super) fn instance_at(&self, zone: usize) -> Option<&Instance> {
        self.instances.iter().find(|i| i.zone == zone)
    }
    pub(super) fn is_instance(&self, zone: usize) -> bool {
        self.instance_at(zone).is_some()
    }
    /// The zone number clients are told for `zone`.
    pub(super) fn public_zone(&self, zone: usize) -> usize {
        self.instance_at(zone).map_or(zone, |i| i.template)
    }
    /// A dungeon copy nobody is in: nothing in it moves.
    pub(super) fn zone_idle(&self, zone: usize) -> bool {
        self.instance_at(zone).is_some_and(|i| !i.active)
    }
    pub(super) fn instance_cleared(&self, zone: usize) -> bool {
        self.instance_at(zone).is_some_and(|i| i.cleared)
    }
    /// Which copy of dungeon `template` `session` enters: the one a party mate (or hired fighter) is already in, else
    /// the first free one.
    pub(super) fn instance_for(&self, session: u64, template: usize) -> Result<usize, String> {
        let me = &self.players[&session].character;
        // Moving within a wing keeps its existing copy, even for a solo visitor.
        if self
            .instance_at(me.zone)
            .is_some_and(|i| i.template == template)
        {
            return Ok(me.zone);
        }
        let mates = self.party_mates(&me.id);
        for q in self.players.values() {
            if q.character.id != me.id
                && mates.contains(&q.character.id)
                && self
                    .instance_at(q.character.zone)
                    .is_some_and(|i| i.template == template)
            {
                return Ok(q.character.zone);
            }
        }
        if let Some(i) = self.instances.iter().find(|i| {
            i.template == template
                && i.active
                && self.maps[i.zone].raid
                && i.members.contains(&me.id)
                && !self
                    .players
                    .values()
                    .any(|p| p.character.zone == i.zone && p.merc.is_none())
        }) {
            return Ok(i.zone);
        }
        self.instances
            .iter()
            .find(|i| i.template == template && !i.active)
            .map(|i| i.zone)
            .ok_or_else(|| {
                format!(
                    "Every copy of {} is in use right now. Try again in a few minutes.",
                    self.zone_name(template)
                )
            })
    }
    /// Someone walked in: the copy is live.
    pub(super) fn enter_instance(&mut self, zone: usize) {
        if let Some(i) = self.instances.iter_mut().find(|i| i.zone == zone) {
            i.active = true;
        }
    }
    /// Once per tick: a copy whose last hero has left is reset.
    pub(super) fn update_instances(&mut self) {
        for index in 0..self.instances.len() {
            let zone = self.instances[index].zone;
            if !self.instances[index].active {
                continue;
            }
            let humans: Vec<String> = self
                .players
                .values()
                .filter(|p| p.character.zone == zone && p.merc.is_none() && p.ambient.is_none())
                .map(|p| p.character.id.clone())
                .collect();
            if !humans.is_empty() {
                self.instances[index].empty_since = None;
                for id in humans {
                    let mates = self.party_mates(&id);
                    for mate in mates {
                        if !self.instances[index].members.contains(&mate) {
                            self.instances[index].members.push(mate);
                        }
                    }
                }
            } else if self.maps[zone].raid {
                let since = *self.instances[index].empty_since.get_or_insert(self.time);
                if self.time - since >= 1200. {
                    self.reset_instance(index);
                }
            } else if !self.players.values().any(|p| p.character.zone == zone) {
                self.reset_instance(index);
            }
        }
    }

    /// Every enemy back at its post at full health, shots and loot gone, the exit closed.
    pub(super) fn reset_instance(&mut self, index: usize) {
        let zone = self.instances[index].zone;
        self.respawn_instance_zone(zone);
        self.instances[index].active = false;
        self.instances[index].cleared = false;
        self.instances[index].rally = None;
        self.instances[index].grace_until = 0.;
        self.instances[index].empty_since = None;
        self.instances[index].members.clear();
        self.instances[index].tuning = Default::default();
    }
    /// The enemy half of `reset_instance`: every enemy back at its post, shots, loot and chests gone.
    pub(super) fn respawn_instance_zone(&mut self, zone: usize) {
        self.reset_boss_zone(zone);
        for id in 0..self.spawns.len() {
            if self.spawns[id].zone == zone {
                let enemy = self.fresh_enemy(id);
                self.slimes[id] = enemy;
                self.place_enemy(id);
            }
        }
        self.bolts.retain(|b| b.zone != zone);
        self.enemy_bolts.retain(|b| b.zone != zone);
        self.drops.retain(|d| d.zone != zone);
        self.clear_chests(zone);
    }
    /// The final boss fell: open the exit and tell everyone inside.
    pub(super) fn clear_instance(&mut self, zone: usize, at: Point) {
        let Some(i) = self.instances.iter_mut().find(|i| i.zone == zone) else {
            return;
        };
        i.cleared = true;
        let text = format!(
            "{} is cleared. A portal opens where the last foe fell.",
            self.maps[zone].name
        );
        for p in self.players.values().filter(|p| p.character.zone == zone) {
            let _ = p.peer.try_send(json!({"type":"system","text":text}));
        }
        self.emit_zone(
            zone,
            json!({"type":"event","kind":"cleared","actor":"","x":at.x,"y":at.y,"value":0,"crit":false}),
        );
    }
}
