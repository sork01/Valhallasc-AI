//! The game master's test menu (`client/gmtest.js`, `/dungeon`, `/gauntlet`, `/tune`): enter any dungeon at its door, final
//! boss or a pack, with the dungeon's level, a full gear set and four hired fighters (nine in a raid); reset the copy; read or skip the
//! enrage clock; start an arena gauntlet at any quest level and fight; and change a few difficulty multipliers. Every op
//! is a `DebugCommand`, so it only runs for the verified GM character (or a private test world) and is logged.
//!
//! The multipliers belong to one dungeon copy (`Instance.tuning`) or one gauntlet run (`Run.opponent_*`), so they never
//! reach another player's copy or run, live in memory only and go away when the copy resets or the server restarts.
use super::gauntlet::{CLASSES, FIGHTS, gear_set};
use super::*;

/// A pack kind hits at least this many times harder than its base stats (`world/elite-power.txt`); ordinary elites do not.
const PACK_DAMAGE_FLOOR: f64 = 2.;
/// Spawns of pack kinds closer than this chain into one pack, and a pack has at least this many (as the solo tests count).
const PACK_LINK: f64 = 10.;
const PACK_MIN: usize = 3;
/// How far from a boss or pack the menu puts the hero.
const STAND_OFF: f64 = 6.;
const SHARE_MIN: f64 = 0.05;
const SHARE_MAX: f64 = 10.;

#[derive(Clone, Debug)]
pub(super) struct Tuning {
    /// Times the damage of a pack kind's blows and shots.
    pub pack_damage: f64,
    /// Times the health of the bosses in the copy.
    pub boss_health: f64,
    /// Times the enrage start of every boss in the copy.
    pub enrage_start: f64,
}

impl Default for Tuning {
    fn default() -> Self {
        Self {
            pack_damage: 1.,
            boss_health: 1.,
            enrage_start: 1.,
        }
    }
}

impl World {
    /// (damage share for this kind's blows, enrage start scale) in `zone`: both 1 outside a tuned dungeon copy.
    pub(super) fn tuned(&self, zone: usize, kind: &str) -> (f64, f64) {
        let Some(i) = self.instance_at(zone) else {
            return (1., 1.);
        };
        let t = &i.tuning;
        let pack = if t.pack_damage != 1. && crate::items::elite_power(kind).1 > PACK_DAMAGE_FLOOR {
            t.pack_damage
        } else {
            1.
        };
        (pack, t.enrage_start)
    }
    pub(super) fn tuned_enrage_factor(&self, zone: usize, kind: &str, fight: f64) -> f64 {
        crate::items::enrage_factor_scaled(kind, fight, self.tuned(zone, kind).1)
    }

    /// Template zones of the dungeons and raids the menu offers.
    pub(super) fn test_dungeons(&self) -> Vec<usize> {
        (0..self.maps.len())
            .filter(|&z| {
                let m = &self.maps[z];
                m.copies > 0 && m.template.is_none()
            })
            .collect()
    }
    fn test_merc_count(&self, zone: usize) -> usize {
        if self.maps[zone].raid {
            social::RAID_MAX - 1
        } else {
            social::PARTY_MAX - 1
        }
    }
    pub(super) fn dungeon_level(&self, zone: usize) -> u32 {
        let m = &self.maps[zone];
        m.levels.map_or(m.min_level, |l| l[0]).max(1)
    }
    pub(super) fn dungeon_boss(&self, zone: usize) -> Option<Point> {
        self.spawns
            .iter()
            .find(|s| s.zone == zone && s.ambush.is_none() && s.kind == self.maps[zone].final_boss)
            .map(|s| Point { x: s.x, y: s.y })
    }
    /// The first spawn of every pack (single-linkage clusters of pack-kind spawns), in spawn order.
    pub(super) fn dungeon_packs(&self, zone: usize) -> Vec<Point> {
        let boss = &self.maps[zone].final_boss;
        let spawns: Vec<&SlimeSpawn> = self
            .spawns
            .iter()
            .filter(|s| {
                s.zone == zone
                    && s.ambush.is_none()
                    && s.kind != *boss
                    && crate::items::elite_power(&s.kind).1 > PACK_DAMAGE_FLOOR
            })
            .collect();
        let mut group: Vec<usize> = (0..spawns.len()).collect();
        for a in 0..spawns.len() {
            for b in a + 1..spawns.len() {
                if (spawns[a].x - spawns[b].x).hypot(spawns[a].y - spawns[b].y) <= PACK_LINK {
                    let (from, to) = (group[b], group[a]);
                    for g in group.iter_mut().filter(|g| **g == from) {
                        *g = to;
                    }
                }
            }
        }
        let mut firsts = vec![];
        for (n, &g) in group.iter().enumerate() {
            if n == g && group.iter().filter(|&&o| o == g).count() >= PACK_MIN {
                firsts.push(Point {
                    x: spawns[n].x,
                    y: spawns[n].y,
                });
            }
        }
        firsts
    }
    pub(super) fn gauntlet_levels(&self) -> Vec<u32> {
        let mut levels: Vec<u32> = self
            .maps
            .iter()
            .flat_map(|m| m.quests.iter().filter_map(|q| q.gauntlet_level()))
            .collect();
        levels.sort_unstable();
        levels.dedup();
        levels
    }
    /// Live bosses of the copy `zone`: enemies with an enrage entry (an instance has no outdoor elites).
    fn copy_bosses(&self, zone: usize) -> Vec<usize> {
        (0..self.slimes.len())
            .filter(|&i| {
                let s = &self.slimes[i];
                s.zone == zone && !s.dead && crate::items::enrage(&s.kind).is_some()
            })
            .collect()
    }
    fn scale_boss_health(&mut self, zone: usize, ratio: f64) {
        for id in self.copy_bosses(zone) {
            let s = &mut self.slimes[id];
            s.max_hp *= ratio;
            s.hp = (s.hp * ratio).min(s.max_hp);
        }
    }

    fn tuning_json(&self, session: u64) -> Value {
        let zone = self.players.get(&session).map_or(0, |p| p.character.zone);
        let t = self.instance_at(zone).map(|i| i.tuning.clone());
        let run = self.gauntlets.iter().find(|r| r.owner == session);
        json!({
            "dungeon": t.as_ref().map(|t| json!({"pack_damage": t.pack_damage, "boss_health": t.boss_health, "enrage_start": t.enrage_start})),
            "gauntlet": run.map(|r| json!({"opponent_health": r.opponent_health, "opponent_damage": r.opponent_damage})),
        })
    }

    pub(super) fn gm_test_info(&self, session: u64) -> Result<Value, String> {
        self.players.get(&session).ok_or("Unknown session.")?;
        let dungeons: Vec<Value> = self
            .test_dungeons()
            .into_iter()
            .map(|z| {
                json!({
                    "zone": z,
                    "name": self.maps[z].name,
                    "level": self.dungeon_level(z),
                    "boss": self.maps[z].final_boss,
                    "packs": self.dungeon_packs(z).len(),
                    "sealed": self.maps[z].sealed_template,
                    "mercs": self.test_merc_count(z),
                })
            })
            .collect();
        Ok(json!({
            "supported": true,
            "dungeons": dungeons,
            "gauntletLevels": self.gauntlet_levels(),
            "fights": FIGHTS,
            "classes": CLASSES.map(|c| format!("{c:?}")),
            "tuning": self.tuning_json(session),
        }))
    }

    #[allow(clippy::too_many_arguments)]
    pub(super) fn gm_dungeon_enter(
        &mut self,
        session: u64,
        zone: usize,
        at: &str,
        pack: usize,
        level: bool,
        gear: Option<&str>,
        mercs: bool,
    ) -> Result<Value, String> {
        let p = self.players.get(&session).ok_or("Unknown session.")?;
        if p.character.hp <= 0. {
            return Err("You are defeated. Use /hp first.".into());
        }
        if self.gauntlets.iter().any(|r| r.owner == session) || self.pvp_busy(&p.character.id) {
            return Err("Finish the gauntlet or duel first.".into());
        }
        if !self.test_dungeons().contains(&zone) {
            return Err("That is not a dungeon the menu can enter.".into());
        }
        let rarity = match gear {
            None => None,
            Some("green") => Some("uncommon"),
            Some("blue") => Some("rare"),
            Some("purple") => Some("epic"),
            Some(other) => {
                return Err(format!(
                    "Unknown gear set {other}; use green, blue or purple."
                ));
            }
        };
        let door = self.maps[zone].spawn;
        let aim = match at {
            "door" => door,
            "boss" => self
                .dungeon_boss(zone)
                .ok_or("This dungeon has no final boss placed.")?,
            "pack" => *self.dungeon_packs(zone).get(pack).ok_or_else(|| {
                format!("This dungeon has {} packs.", self.dungeon_packs(zone).len())
            })?,
            other => return Err(format!("Unknown place {other}; use door, boss or pack.")),
        };
        // Stand a few tiles from the boss or pack, on the door's side.
        let stand = if at == "door" {
            aim
        } else {
            let away = aim.direction(door);
            Point {
                x: aim.x + away.x * STAND_OFF,
                y: aim.y + away.y * STAND_OFF,
            }
        };
        let dungeon_level = self.dungeon_level(zone);
        // Monsters and a party only see a visible hero, and a visible GM is hidden again after any zone change unless
        // `visible_zone` follows.
        if self.players[&session].character.gm {
            self.set_visibility(session, "on")?;
        }
        if level {
            self.run_debug(
                session,
                DebugCommand::SetLevel {
                    level: dungeon_level,
                },
            )?;
        }
        if let Some(rarity) = rarity {
            let p = self.players.get_mut(&session).unwrap();
            let set = gear_set(p.character.look.class, p.character.level, rarity);
            if set.is_empty() {
                return Err("No gear set of that colour exists at this level.".into());
            }
            // Two slots may want the same piece (the rings): each equipped slot needs its own copy.
            for (_, id) in &set {
                let wanted = set.iter().filter(|(_, other)| other == id).count() as u32;
                while p.character.quantity(id) < wanted {
                    p.character.add_item(id, 1);
                }
            }
            p.character.materialize_gear_instances();
            let equip: BTreeMap<String, String> = set
                .into_iter()
                .map(|(slot, id)| (slot.to_owned(), id))
                .collect();
            p.character.equip_slots(&equip).map_err(String::from)?;
        }
        if level || rarity.is_some() {
            let c = &mut self.players.get_mut(&session).unwrap().character;
            if c.stat_points() > 0 {
                let _ = c.allocate_recommended();
            }
        }
        let copy = self.instance_for(session, zone)?;
        self.enter_instance(copy);
        let mut arrival = stand;
        self.maps[copy].collide(&mut arrival, PLAYER_RADIUS);
        let time = self.time;
        let p = self.players.get_mut(&session).unwrap();
        p.character.zone = copy;
        p.visible_zone = copy;
        p.character.x = arrival.x;
        p.character.y = arrival.y;
        p.character.hp = p.character.max_hp();
        p.character.reset_resource();
        p.character.mounted = false;
        p.dead_time = 0.;
        p.fallen = false;
        p.portal_at = time;
        p.stop();
        p.attack = 0.;
        p.dash = 0.;
        let (owner, class, hero_level) = (
            p.character.id.clone(),
            p.character.look.class,
            p.character.level,
        );
        self.separate_enemies();
        let mut hired = 0;
        if mercs {
            let _ = self.dismiss_mercenaries(session);
            let fighters = [
                Class::Priest,
                Class::Mage,
                Class::Hunter,
                Class::Assassin,
                Class::Warrior,
            ];
            // Two of each class including the GM in a full raid, one of each in a dungeon.
            for merc in fighters
                .into_iter()
                .filter(|c| *c != class)
                .chain(fighters)
                .take(self.test_merc_count(zone))
            {
                if self
                    .place_mercenary(
                        &owner,
                        merc,
                        hero_level,
                        copy,
                        arrival,
                        self.maps[zone].raid,
                        None,
                    )
                    .is_err()
                {
                    break;
                }
                hired += 1;
            }
        }
        self.save();
        Ok(json!({
            "zone": self.public_zone(copy), "x": arrival.x, "y": arrival.y, "at": at,
            "level": hero_level, "gear": gear, "mercs": hired,
        }))
    }

    pub(super) fn gm_dungeon_reset(&mut self, session: u64) -> Result<Value, String> {
        let zone = self
            .players
            .get(&session)
            .ok_or("Unknown session.")?
            .character
            .zone;
        let boss_health = self
            .instance_at(zone)
            .ok_or("You are not in a dungeon copy.")?
            .tuning
            .boss_health;
        self.respawn_instance_zone(zone);
        if let Some(i) = self.instances.iter_mut().find(|i| i.zone == zone) {
            i.cleared = false;
            i.rally = None;
            i.grace_until = 0.;
        }
        self.scale_boss_health(zone, boss_health);
        for p in self
            .players
            .values_mut()
            .filter(|p| p.character.zone == zone)
        {
            p.character.hp = p.character.max_hp();
            p.dead_time = 0.;
            p.fallen = false;
        }
        Ok(json!({"reset": true, "tuning": self.tuning_json(session)}))
    }

    pub(super) fn gm_enrage(&mut self, session: u64, action: &str) -> Result<Value, String> {
        let zone = self
            .players
            .get(&session)
            .ok_or("Unknown session.")?
            .character
            .zone;
        self.instance_at(zone)
            .ok_or("You are not in a dungeon copy.")?;
        let bosses = self.copy_bosses(zone);
        match action {
            "status" => {}
            "skip" => {
                for &id in &bosses {
                    let scale = self.tuned(zone, &self.slimes[id].kind).1;
                    if let Some((start, _)) =
                        crate::items::enrage_scaled(&self.slimes[id].kind, scale)
                    {
                        self.slimes[id].fight = self.slimes[id].fight.max(start + 0.1);
                    }
                }
            }
            other => return Err(format!("Unknown action {other}; use status or skip.")),
        }
        let list: Vec<Value> = bosses
            .iter()
            .map(|&id| {
                let s = &self.slimes[id];
                let start = crate::items::enrage_scaled(&s.kind, self.tuned(zone, &s.kind).1).map(|e| e.0);
                json!({"kind": s.kind, "fight": s.fight, "start": start, "hp": s.hp, "maxHp": s.max_hp,
                       "engaged": !matches!(s.state.as_str(), "idle" | "wander" | "return")})
            })
            .collect();
        Ok(json!({"bosses": list,
            "note": "The clock runs only while a boss fights someone within 14 tiles; skip moves a boss that is fighting."}))
    }

    pub(super) fn gm_gauntlet(
        &mut self,
        session: u64,
        level: u32,
        fight: usize,
    ) -> Result<Value, String> {
        if !self.gauntlet_levels().contains(&level) {
            return Err(format!("There is no gauntlet quest at level {level}."));
        }
        if !(1..=FIGHTS).contains(&fight) {
            return Err(format!("Fight must be 1-{FIGHTS}."));
        }
        let p = self.players.get(&session).ok_or("Unknown session.")?;
        let zone = p.character.zone;
        if p.character.hp <= 0.
            || self.gauntlets.iter().any(|r| r.owner == session)
            || self.pvp_busy(&p.character.id)
            || p.character.spark_travel.is_some()
            || self.is_arena_zone(zone)
        {
            return Err("Finish what you are doing first.".into());
        }
        if self.is_instance(zone) {
            return Err(
                "Leave the dungeon first; the run returns you to where you start it.".into(),
            );
        }
        let arena = self
            .instances
            .iter()
            .find(|i| self.is_arena_zone(i.zone) && !i.active)
            .map(|i| i.zone)
            .ok_or("The Arena is full right now.")?;
        let returns = (zone, p.character.x, p.character.y);
        if p.character.gm {
            self.set_visibility(session, "on")?;
        }
        let text = self.gauntlet_launch(
            session,
            String::new(),
            level,
            arena,
            returns,
            CLASSES,
            fight - 1,
        );
        self.pvp_sync();
        Ok(
            json!({"level": level, "fight": fight, "class": format!("{:?}", CLASSES[fight - 1]), "text": text}),
        )
    }

    pub(super) fn gm_tune(&mut self, session: u64, key: &str, value: f64) -> Result<Value, String> {
        let zone = self
            .players
            .get(&session)
            .ok_or("Unknown session.")?
            .character
            .zone;
        if key == "reset" {
            let boss_ratio = self.instance_at(zone).map(|i| 1. / i.tuning.boss_health);
            if let Some(i) = self.instances.iter_mut().find(|i| i.zone == zone) {
                i.tuning = Tuning::default();
            }
            if let Some(ratio) = boss_ratio {
                self.scale_boss_health(zone, ratio);
            }
            if let Some(r) = self.gauntlets.iter_mut().find(|r| r.owner == session) {
                r.opponent_health = gauntlet::opponent_health();
                r.opponent_damage = gauntlet::opponent_damage();
            }
            return Ok(self.tuning_json(session));
        }
        if !value.is_finite() || !(SHARE_MIN..=SHARE_MAX).contains(&value) {
            return Err(format!(
                "A multiplier must be between {SHARE_MIN} and {SHARE_MAX}."
            ));
        }
        match key {
            "pack_damage" | "boss_health" | "enrage_start" => {
                let i = self
                    .instances
                    .iter_mut()
                    .find(|i| i.zone == zone)
                    .ok_or("Enter a dungeon copy first; the multipliers belong to it.")?;
                match key {
                    "pack_damage" => i.tuning.pack_damage = value,
                    "enrage_start" => i.tuning.enrage_start = value,
                    _ => {
                        let ratio = value / i.tuning.boss_health;
                        i.tuning.boss_health = value;
                        self.scale_boss_health(zone, ratio);
                    }
                }
            }
            "opponent_health" | "opponent_damage" => {
                let r = self
                    .gauntlets
                    .iter_mut()
                    .find(|r| r.owner == session)
                    .ok_or("Start a gauntlet run first; the multipliers belong to it.")?;
                if key == "opponent_health" {
                    r.opponent_health = value;
                } else {
                    r.opponent_damage = value;
                }
            }
            other => return Err(format!("Unknown multiplier {other}.")),
        }
        Ok(self.tuning_json(session))
    }
}
