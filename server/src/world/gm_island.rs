//! The GM's isolated festival island. Admission and services never use test_commands.
use super::*;
use std::collections::BTreeSet;

pub(super) const DUMMY: &str = "gmi_dummy";
pub(super) const DUMMY_HP: f64 = 1e12;
const SUMMON: &str = "gmi_summon";
const MAX_SUMMONS: usize = 24;
const ARENA: [f64; 4] = [185., 175., 239., 223.];

impl World {
    pub(super) fn gm_island_zone(&self) -> Option<usize> {
        self.maps
            .iter()
            .position(|m| m.gm_only && m.template.is_none())
    }

    pub(super) fn gm_island_before_travel(
        &mut self,
        session: u64,
        zone: usize,
    ) -> Result<(), String> {
        let p = self.players.get(&session).ok_or("Unknown session.")?;
        if self.maps.get(zone).is_some_and(|m| m.gm_only) {
            if !p.character.gm {
                return Err("Only a GM may enter GM Island.".into());
            }
            if p.character.hp <= 0.
                || p.character.spark_travel.is_some()
                || self.pvp_busy(&p.character.id)
                || self.trade_index(&p.character.id).is_some()
                || self.gauntlets.iter().any(|r| r.owner == session)
                || self.is_instance(p.character.zone)
            {
                return Err("Finish your current activity before visiting GM Island.".into());
            }
            if p.character.gm_island_backup.is_none() {
                let backup = p.character.clone();
                self.players
                    .get_mut(&session)
                    .unwrap()
                    .character
                    .gm_island_backup = Some(Box::new(backup));
            }
            let stops: Vec<_> = self.maps[zone]
                .npcs
                .iter()
                .filter(|n| n.travel_stop.is_some())
                .map(|n| n.id.clone())
                .collect();
            let c = &mut self.players.get_mut(&session).unwrap().character;
            for stop in stops {
                if !c.travel_stops.contains(&stop) {
                    c.travel_stops.push(stop);
                }
            }
        } else if p.character.gm_island_backup.is_some() {
            self.gm_island_restore(session);
        }
        Ok(())
    }

    fn gm_island_restore(&mut self, session: u64) {
        let _ = self.dismiss_mercenaries(session);
        if let Some(backup) = self
            .players
            .get_mut(&session)
            .and_then(|p| p.character.gm_island_backup.take())
        {
            let peer = self.players[&session].peer.clone();
            let mut restored = *backup;
            let map = &self.maps[restored.zone];
            let at = restored.point();
            let near_gate = |point: Point| {
                map.portals
                    .iter()
                    .any(|g| point.distance(Point { x: g.x, y: g.y }) <= g.r.max(2.8) + 0.5)
            };
            if near_gate(at) {
                let safe = [6., 10., 14.]
                    .into_iter()
                    .flat_map(|r| {
                        [
                            (1., 0.),
                            (0., 1.),
                            (-1., 0.),
                            (0., -1.),
                            (1., 1.),
                            (-1., 1.),
                            (1., -1.),
                            (-1., -1.),
                        ]
                        .map(move |(x, y)| Point {
                            x: at.x + x * r,
                            y: at.y + y * r,
                        })
                    })
                    .find(|&point| {
                        let mut clear = point;
                        map.collide(&mut clear, PLAYER_RADIUS);
                        point.distance(clear) < 1e-6 && !near_gate(point)
                    })
                    .unwrap_or(map.spawn);
                restored.x = safe.x;
                restored.y = safe.y;
            }
            let mut p = Player::new(restored, peer);
            p.hidden = true;
            p.visible_zone = p.character.zone;
            self.players.insert(session, p);
        }
        if let Some(zone) = self.gm_island_zone() {
            self.gm_island_clear(zone);
        }
    }

    fn gm_island_clear(&mut self, zone: usize) {
        self.reset_boss_zone(zone);
        for s in &mut self.slimes {
            if self.spawns[s.id].ambush.as_deref() == Some(SUMMON) {
                s.dead = true;
                s.hp = 0.;
                s.respawn = 1e9;
                s.target = None;
                s.state = "waiting".into();
            } else if s.zone == zone && s.kind == DUMMY {
                s.target = None;
                s.state = "idle".into();
                s.hp = s.max_hp;
                s.set_root_left = 0.;
                s.set_slow_left = 0.;
            }
        }
        self.enemy_bolts.retain(|b| b.zone != zone);
        self.bolts.retain(|b| b.zone != zone);
        self.drops.retain(|d| d.zone != zone);
        self.damage_meter.reset(zone);
        for p in self
            .players
            .values_mut()
            .filter(|p| p.character.zone == zone)
        {
            p.stop();
            p.target = None;
            p.attack = 0.;
            p.dash = 0.;
            p.combat_left = 0.;
        }
    }

    /// One dummy, no zone-wide searches. Arena slots are bounded and never respawn.
    pub(super) fn update_gm_island_enemy(&mut self, id: usize) -> bool {
        let s = &mut self.slimes[id];
        if s.kind == DUMMY {
            s.dead = false;
            s.hp = s.max_hp;
            s.x = s.hx;
            s.y = s.hy;
            s.hop = 0.;
            s.state = "idle".into();
            s.hurt_t = (s.hurt_t - TICK).max(0.);
            if self.time - s.st > 5. {
                s.target = None;
            }
            return true;
        }
        if self.spawns[id].ambush.as_deref() == Some(SUMMON) {
            if s.dead {
                return true;
            }
            if s.x < ARENA[0] || s.y < ARENA[1] || s.x > ARENA[2] || s.y > ARENA[3] {
                s.x = s.hx;
                s.y = s.hy;
                s.target = None;
                s.state = "idle".into();
                s.hp = s.max_hp;
            }
        }
        false
    }

    fn gm_island_info(&self, session: u64) -> Value {
        let mut kinds: BTreeSet<String> = self
            .spawns
            .iter()
            .filter(|s| s.kind != DUMMY && s.ambush.as_deref() != Some(SUMMON))
            .map(|s| s.kind.clone())
            .collect();
        kinds.insert("big".into());
        kinds.extend(
            [
                seasonal_hunt::HALLOWEEN,
                seasonal_hunt::CHRISTMAS,
                seasonal_hunt::VALENTINE,
                seasonal_hunt::EASTER,
                seasonal_hunt::SOLSTICE,
                seasonal_hunt::NEWYEAR,
            ]
            .map(|s| s.kind.to_owned()),
        );
        json!({"zone":self.gm_island_zone(),"classes":gauntlet::CLASSES,
            "level":self.players[&session].character.level,
            "enemies":kinds.into_iter().map(|kind| json!({"level":Slime::default_level(&kind),
                "boss":is_elite(&kind),"kind":kind})).collect::<Vec<_>>(),
            "maxSummons":MAX_SUMMONS})
    }

    /// Intercept island service NPCs before generic free offers are considered.
    pub(super) fn gm_island_interact(&mut self, session: u64, npc_id: &str) -> bool {
        let Some(zone) = self.gm_island_zone() else {
            return false;
        };
        let Some(npc) = self.maps[zone]
            .npcs
            .iter()
            .find(|n| n.id == npc_id && n.offers.iter().any(|o| o.id.starts_with("gmi:")))
            .cloned()
        else {
            return false;
        };
        let p = &self.players[&session];
        if !p.character.gm
            || p.character.zone != zone
            || p.character.hp <= 0.
            || p.character.point().distance(npc.position_at(self.time)) > 2.8
        {
            let _ = p.peer.try_send(
                json!({"type":"error","text":"Only a nearby GM may use this island service."}),
            );
            return true;
        }
        let info = self.gm_island_info(session);
        let p = self.players.get_mut(&session).unwrap();
        p.stop();
        p.attack = 0.;
        let c = &p.character;
        let _ = p
            .peer
            .try_send(json!({"type":"dialogue","npc":npc,"notice":"",
            "gmIsland":info,"gm":true,"gold":c.gold,"level":c.level,
            "inventory":c.inventory,"equipment":c.equipment,"gearInstances":c.gear_instances,
            "bags":c.bags,"look":c.look,"quests":c.quests}));
        true
    }

    #[allow(clippy::too_many_arguments)]
    pub(super) fn gm_island_command(
        &mut self,
        session: u64,
        action: &str,
        npc_id: Option<&str>,
        kind: Option<&str>,
        level: Option<u32>,
        class: Option<Class>,
        gear: Option<&str>,
        count: Option<u32>,
    ) -> Result<Value, String> {
        let p = self.players.get(&session).ok_or("Unknown session.")?;
        if !p.character.gm {
            return Err("Only a GM may use GM Island.".into());
        }
        let zone = self.gm_island_zone().ok_or("GM Island is unavailable.")?;
        if action == "info" {
            return Ok(self.gm_island_info(session));
        }
        if action == "enter" {
            if p.character.hp <= 0.
                || p.character.spark_travel.is_some()
                || self.pvp_busy(&p.character.id)
                || self.trade_index(&p.character.id).is_some()
                || self.gauntlets.iter().any(|r| r.owner == session)
                || self.is_instance(p.character.zone)
            {
                return Err("Finish your current activity before visiting GM Island.".into());
            }
            self.gm_island_before_travel(session, zone)?;
            let spawn = self.maps[zone].spawn;
            let _ = self.dismiss_mercenaries(session);
            let p = self.players.get_mut(&session).unwrap();
            p.character.zone = zone;
            p.character.x = spawn.x;
            p.character.y = spawn.y;
            p.character.mounted = false;
            p.hidden = false;
            p.visible_zone = zone;
            p.stop();
            p.target = None;
            p.portal_at = self.time;
            self.save();
            return Ok(json!({"zone":zone,"x":spawn.x,"y":spawn.y}));
        }
        if p.character.zone != zone {
            return Err("Visit GM Island first.".into());
        }
        let service = match action {
            "setup" => "setup",
            "summon" | "clear" => "summon",
            "mercs" | "dismiss" => "mercs",
            "reset_dps" | "refresh" => "training",
            "leave" => "travel",
            _ => return Err("Unknown island service.".into()),
        };
        let npc = self.maps[zone]
            .npcs
            .iter()
            .find(|n| {
                Some(n.id.as_str()) == npc_id
                    && n.offers.iter().any(|o| o.id == format!("gmi:{service}"))
            })
            .ok_or("Choose the island service NPC first.")?;
        if p.character.hp <= 0.
            || p.character.spark_travel.is_some()
            || p.character.point().distance(npc.position_at(self.time)) > 2.8
        {
            return Err("Walk closer to the island service NPC.".into());
        }
        if self.time - p.service_at < 0.5 {
            return Err("Please wait a moment before trying again.".into());
        }
        let level = level.unwrap_or(p.character.level);
        if !(1..=MAX_LEVEL).contains(&level) {
            return Err("Level must be 1-99.".into());
        }
        self.players.get_mut(&session).unwrap().service_at = self.time;
        let result = match action {
            "setup" => self.gm_island_setup(
                session,
                class.unwrap_or(self.players[&session].character.look.class),
                level,
                gear.unwrap_or("uncommon"),
            )?,
            "summon" => self.gm_island_summon(
                zone,
                kind.ok_or("Choose an enemy kind.")?,
                level,
                count.unwrap_or(1),
            )?,
            "clear" => {
                self.gm_island_clear(zone);
                json!({"cleared":true})
            }
            "mercs" => {
                let class = class.ok_or("Choose a mercenary class.")?;
                let count = count.unwrap_or(1);
                let owner = self.players[&session].character.id.clone();
                let hired = self
                    .players
                    .values()
                    .filter(|p| p.merc.as_deref() == Some(&owner))
                    .count();
                if count == 0 || hired + count as usize > 4 {
                    return Err("GM Island allows at most four hired fighters.".into());
                }
                for _ in 0..count {
                    self.place_mercenary(
                        &owner,
                        class,
                        level,
                        zone,
                        self.players[&session].character.point(),
                        false,
                        None,
                    )?;
                }
                json!({"hired":count})
            }
            "dismiss" => {
                let _ = self.dismiss_mercenaries(session);
                json!({"dismissed":true})
            }
            "reset_dps" => {
                self.damage_meter.reset(zone);
                for p in self
                    .players
                    .values_mut()
                    .filter(|p| p.character.zone == zone)
                {
                    p.target = None;
                    p.stop();
                    p.attack = 0.;
                    p.dash = 0.;
                }
                self.bolts.retain(|b| b.zone != zone);
                json!({"reset":true})
            }
            "refresh" => {
                let p = self.players.get_mut(&session).unwrap();
                p.character.hp = p.character.max_hp();
                p.character.resource = Some(p.character.max_resource());
                p.skill_cd.clear();
                p.potion_cd = 0.;
                p.meal_cd = 0.;
                p.character.potion_ready = 0;
                p.character.meal_ready = 0;
                p.combat_left = 0.;
                json!({"refreshed":true})
            }
            "leave" => {
                self.gm_island_restore(session);
                let p = self.players.get_mut(&session).unwrap();
                p.visible_zone = p.character.zone;
                p.stop();
                p.target = None;
                p.skill_cd.clear();
                p.buffs.clear();
                p.portal_at = self.time;
                json!({"restored":true,"zone":p.character.zone})
            }
            _ => unreachable!(),
        };
        self.save();
        Ok(result)
    }

    fn gm_island_setup(
        &mut self,
        session: u64,
        class: Class,
        level: u32,
        rarity: &str,
    ) -> Result<Value, String> {
        if !["common", "uncommon", "rare", "epic", "legendary"].contains(&rarity) {
            return Err("Choose a valid equipment rarity.".into());
        }
        let old = &self.players[&session].character;
        let backup = old
            .gm_island_backup
            .clone()
            .ok_or("Re-enter GM Island to save your original character first.")?;
        let mut c = Character::mercenary(class, level, &old.look.name);
        c.id = old.id.clone();
        c.gm = true;
        c.look.gender = old.look.gender;
        c.look.race = old.look.race;
        c.travel_stops = old.travel_stops.clone();
        c.zone = old.zone;
        c.x = old.x;
        c.y = old.y;
        c.gm_island_backup = Some(backup);
        let slots = [
            ("chest", "armor"),
            ("headgear", "headgear"),
            ("shoulders", "shoulders"),
            ("gloves", "gloves"),
            ("hands", "weapon"),
            ("pants", "pants"),
            ("necklace", "necklace"),
            ("cloak", "cloak"),
            ("accessory1", "accessory"),
            ("accessory2", "accessory"),
        ];
        let mut equipped = BTreeMap::new();
        for (slot, kind) in slots {
            let piece = ITEMS
                .iter()
                .filter(|i| {
                    i.kind == kind
                        && i.rarity == rarity
                        && i.required_level <= level
                        && i.source.is_none()
                        && i.class.is_none_or(|c| c == class)
                })
                .max_by(|a, b| {
                    a.required_level
                        .cmp(&b.required_level)
                        .then_with(|| (a.attack + a.defense).total_cmp(&(b.attack + b.defense)))
                });
            if let Some(piece) = piece {
                c.add_item(&piece.id, 1);
                equipped.insert(slot.to_owned(), piece.id.clone());
            }
        }
        if equipped.is_empty() && rarity != "common" {
            return Err("No equipment of that rarity exists at this level.".into());
        }
        c.materialize_gear_instances();
        c.equip_slots(&equipped).map_err(String::from)?;
        c.hp = c.max_hp();
        c.reset_resource();
        let _ = self.dismiss_mercenaries(session);
        let zone = c.zone;
        let peer = self.players[&session].peer.clone();
        let mut p = Player::new(c, peer);
        p.hidden = false;
        p.visible_zone = zone;
        p.service_at = self.time;
        self.players.insert(session, p);
        self.damage_meter.reset(zone);
        Ok(json!({"class":class,"level":level,"gear":rarity,"equipped":equipped.len()}))
    }

    fn gm_island_summon(
        &mut self,
        zone: usize,
        kind: &str,
        level: u32,
        count: u32,
    ) -> Result<Value, String> {
        if kind == DUMMY
            || (seasonal_hunt::for_kind(kind).is_none()
                && !self
                    .spawns
                    .iter()
                    .any(|s| s.kind == kind && s.ambush.as_deref() != Some(SUMMON)))
        {
            return Err("Choose a monster or boss from the island catalogue.".into());
        }
        let active = self
            .slimes
            .iter()
            .filter(|s| !s.dead && self.spawns[s.id].ambush.as_deref() == Some(SUMMON))
            .count();
        if count == 0 || active + count as usize > MAX_SUMMONS {
            return Err("The arena allows at most 24 summoned enemies.".into());
        }
        let mut ids = vec![];
        for _ in 0..count {
            let id = self
                .slimes
                .iter()
                .find(|s| s.dead && self.spawns[s.id].ambush.as_deref() == Some(SUMMON))
                .map_or(self.slimes.len(), |s| s.id);
            let spawn = SlimeSpawn {
                kind: kind.into(),
                x: 212.,
                y: 195.,
                zone,
                ambush: Some(SUMMON.into()),
            };
            let mut enemy = Slime::with_level(id, &spawn, level);
            enemy.xp = 0;
            enemy.gold = 0;
            // Reserve the slot first: actor_bodies reads the excluded enemy's radius.
            if id == self.slimes.len() {
                self.spawns.push(spawn);
                self.slimes.push(enemy);
            } else {
                self.spawns[id] = spawn;
                self.slimes[id] = enemy;
            }
            let bodies = self.actor_bodies(zone, None, Some(id));
            let enemy = &mut self.slimes[id];
            let Some(point) =
                free_actor_position(&self.maps[zone], enemy.point(), enemy.r, &bodies, true)
            else {
                enemy.dead = true;
                enemy.hp = 0.;
                enemy.respawn = 1e9;
                enemy.state = "waiting".into();
                return Err("There is no free ground in the arena.".into());
            };
            self.spawns[id].x = point.x;
            self.spawns[id].y = point.y;
            enemy.x = point.x;
            enemy.y = point.y;
            enemy.hx = point.x;
            enemy.hy = point.y;
            enemy.goal = point;
            ids.push(id);
        }
        Ok(json!({"ids":ids,"kind":kind,"level":level}))
    }
}
