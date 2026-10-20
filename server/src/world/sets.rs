//! Runtime effects of dungeon sets. Ownership and tier counts are derived from worn catalog pieces.
use super::*;

pub(super) enum Pending {
    Mirror {
        owner: u64,
        zone: usize,
        left: f64,
        hits: Vec<(usize, f64)>,
    },
    Seed {
        owner: u64,
        zone: usize,
        left: f64,
        at: Point,
        damage: f64,
    },
    Orbit {
        owner: u64,
        zone: usize,
        left: f64,
        damage: f64,
    },
    Pollen {
        owner: u64,
        target: u64,
        zone: usize,
        left: f64,
        rate: f64,
    },
    Burn {
        owner: u64,
        target: usize,
        zone: usize,
        left: f64,
        rate: f64,
    },
}

impl Pending {
    fn owner(&self) -> u64 {
        match self {
            Self::Mirror { owner, .. }
            | Self::Seed { owner, .. }
            | Self::Orbit { owner, .. }
            | Self::Pollen { owner, .. }
            | Self::Burn { owner, .. } => *owner,
        }
    }
    fn zone(&self) -> usize {
        match self {
            Self::Mirror { zone, .. }
            | Self::Seed { zone, .. }
            | Self::Orbit { zone, .. }
            | Self::Pollen { zone, .. }
            | Self::Burn { zone, .. } => *zone,
        }
    }
}

impl World {
    /// A fixed, noncritical basic hit is the reference for small signature damage.
    fn set_basic_damage(&self, session: u64) -> f64 {
        (self.players[&session].character.stats().0 * DAMAGE_DEALT_SCALE)
            .round()
            .max(1.)
    }

    fn set_hit(&mut self, session: u64, enemy: usize, damage: f64) {
        self.cur_skill = "set_bonus".into();
        self.hit_slime(enemy, session, damage, false);
        self.cur_skill.clear();
    }

    fn set_target(&self, zone: usize, at: Point, range: f64, excluded: &[usize]) -> Option<usize> {
        self.enemies_near(zone, at, range, excluded)
            .into_iter()
            .find(|&id| self.maps[zone].line_clear(at, self.slimes[id].point(), 0.05))
    }

    /// Returns the source whose 8-piece effect actually fired. A missing target does not spend its timer.
    pub(super) fn apply_set_signature(
        &mut self,
        session: u64,
        skill: &str,
        origin: Point,
        face: Point,
        primary: Option<usize>,
        before_hp: &[(usize, f64)],
    ) -> Option<String> {
        let p = self.players.get(&session)?;
        let zone = p.character.zone;
        let counts = p.character.set_counts();
        let source = set_catalog::rows(p.character.look.class)
            .find(|row| {
                row.trigger_skill == skill
                    && counts.get(&row.source).is_some_and(|n| *n >= 8)
                    && !p.set_cd.contains_key(&row.source)
            })?
            .source
            .clone();
        let basic = self.set_basic_damage(session);
        let mut applied = true;
        match source.as_str() {
            "nornroot" => {
                let c = &mut self.players.get_mut(&session).unwrap().character;
                c.hp = (c.hp + c.max_hp() * 0.04).min(c.max_hp());
            }
            "skybridge" => {
                if let Some(id) = self.set_target(zone, origin, 4., &[]) {
                    self.set_hit(session, id, basic * 0.16);
                } else {
                    applied = false;
                }
            }
            "undervault" => {
                let p = self.players.get_mut(&session).unwrap();
                p.set_shield = p.set_shield.max(p.character.max_hp() * 0.06);
                p.set_shield_left = 4.;
            }
            "cathedral_cloister" => {
                if let Some(id) = self.set_target(zone, origin, 4., &[]) {
                    let s = &self.slimes[id];
                    if is_boss(&s.kind) {
                        self.slimes[id].set_slow_left = 2.;
                        self.slimes[id].set_slow = 0.2;
                    } else {
                        let mut at = s.point();
                        let direction = at.direction(origin);
                        let bodies = self.actor_bodies(zone, None, Some(id));
                        walk_with_actors(&self.maps[zone], &mut at, direction, 1., s.r, &bodies);
                        self.slimes[id].x = at.x;
                        self.slimes[id].y = at.y;
                    }
                } else {
                    applied = false;
                }
            }
            "cathedral_reliquary" => {
                let target = self.allies_near(session, 4.).into_iter().min_by(|a, b| {
                    let a = &self.players[a].character;
                    let b = &self.players[b].character;
                    (a.hp / a.max_hp()).total_cmp(&(b.hp / b.max_hp()))
                });
                if let Some(target) = target {
                    let p = self.players.get_mut(&target).unwrap();
                    p.set_shield = p.set_shield.max(p.character.max_hp() * 0.05);
                    p.set_shield_left = 4.;
                } else {
                    applied = false;
                }
            }
            "cathedral_nave" => {
                for target in self.allies_near(session, 4.) {
                    let p = self.players.get_mut(&target).unwrap();
                    p.character.hp =
                        (p.character.hp + p.character.max_hp() * 0.03).min(p.character.max_hp());
                }
            }
            "moonwell" => {
                let p = self.players.get_mut(&session).unwrap();
                p.character
                    .change_resource(p.character.max_resource() * 0.05);
            }
            "eye_below" => {
                let excluded = primary.into_iter().collect::<Vec<_>>();
                let enemies = self.enemies_near(zone, origin, 4., &excluded);
                let mut n = 0;
                for id in enemies {
                    if !self.maps[zone].line_clear(origin, self.slimes[id].point(), 0.05) {
                        continue;
                    }
                    self.set_hit(session, id, basic * 0.12);
                    n += 1;
                    if n == 2 {
                        break;
                    }
                }
                applied = n > 0;
            }
            "elder_hollow" => {
                if let Some(id) = self.set_target(zone, origin, 4., &[]) {
                    let s = &mut self.slimes[id];
                    if is_boss(&s.kind) {
                        s.set_slow_left = 2.;
                        s.set_slow = 0.15;
                    } else {
                        s.set_root_left = 0.8;
                    }
                } else {
                    applied = false;
                }
            }
            "thousandfold" => {
                let hits = before_hp
                    .iter()
                    .filter_map(|&(id, hp)| {
                        self.slimes
                            .get(id)
                            .filter(|s| !s.dead && s.zone == zone && s.hp < hp)
                            .map(|s| (id, (hp - s.hp) * 0.2))
                    })
                    .collect::<Vec<_>>();
                if hits.is_empty() {
                    applied = false;
                } else {
                    self.set_pending.push(Pending::Mirror {
                        owner: session,
                        zone,
                        left: 0.6,
                        hits,
                    });
                }
            }
            "rain_crown" => self.players.get_mut(&session).unwrap().set_ranged_left = 4.,
            "seed_vault" => {
                let mut at = Point {
                    x: origin.x + face.x * 2.,
                    y: origin.y + face.y * 2.,
                };
                self.maps[zone].collide(&mut at, 0.1);
                self.set_pending.push(Pending::Seed {
                    owner: session,
                    zone,
                    left: 1.,
                    at,
                    damage: basic * 0.15,
                });
            }
            "sunken_astrolabe" => self.set_pending.push(Pending::Orbit {
                owner: session,
                zone,
                left: 3.,
                damage: basic * 0.18,
            }),
            "thunderheart_gate" => {
                if let Some(id) = self.set_target(zone, origin, 4., &[]) {
                    let s = &mut self.slimes[id];
                    if s.state == "windup" && !is_boss(&s.kind) {
                        s.state = "chase".into();
                        s.st = 0.;
                    }
                    s.atk_cd += 0.5;
                } else {
                    applied = false;
                }
            }
            "blooming_labyrinth" => {
                let target = self.allies_near(session, 5.).into_iter().min_by(|a, b| {
                    let a = &self.players[a].character;
                    let b = &self.players[b].character;
                    (a.hp / a.max_hp()).total_cmp(&(b.hp / b.max_hp()))
                });
                if let Some(target) = target {
                    let rate = self.players[&target].character.max_hp() * 0.01;
                    self.set_pending.push(Pending::Pollen {
                        owner: session,
                        target,
                        zone,
                        left: 4.,
                        rate,
                    });
                } else {
                    applied = false;
                }
            }
            "solar_crucible" => {
                if let Some(target) = self.set_target(zone, origin, 4., &[]) {
                    self.set_pending.push(Pending::Burn {
                        owner: session,
                        target,
                        zone,
                        left: 3.,
                        rate: basic * 0.06,
                    });
                } else {
                    applied = false;
                }
            }
            "amber_archive" => {
                self.players.get_mut(&session).unwrap().set_amber = Some((skill.into(), 5.))
            }
            "silent_solstice" => self.players.get_mut(&session).unwrap().set_stillness_left = 2.,
            _ => applied = false,
        }
        if !applied {
            return None;
        }
        self.players
            .get_mut(&session)
            .unwrap()
            .set_cd
            .insert(source.clone(), 20.);
        Some(source)
    }

    pub(super) fn update_set_effects(&mut self) {
        let mut still = vec![];
        for effect in std::mem::take(&mut self.set_pending) {
            let owner = effect.owner();
            let zone = effect.zone();
            if !self
                .players
                .get(&owner)
                .is_some_and(|p| p.character.hp > 0. && p.character.zone == zone)
            {
                continue;
            }
            match effect {
                Pending::Mirror {
                    owner,
                    zone,
                    left,
                    hits,
                } => {
                    if left > TICK {
                        still.push(Pending::Mirror {
                            owner,
                            zone,
                            left: left - TICK,
                            hits,
                        });
                    } else {
                        for (id, damage) in hits {
                            if self
                                .slimes
                                .get(id)
                                .is_some_and(|s| !s.dead && s.zone == zone)
                            {
                                self.set_hit(owner, id, damage);
                            }
                        }
                    }
                }
                Pending::Seed {
                    owner,
                    zone,
                    left,
                    at,
                    damage,
                } => {
                    if left > TICK {
                        still.push(Pending::Seed {
                            owner,
                            zone,
                            left: left - TICK,
                            at,
                            damage,
                        });
                    } else {
                        for id in self.enemies_near(zone, at, 2., &[]) {
                            if self.maps[zone].line_clear(at, self.slimes[id].point(), 0.05) {
                                self.set_hit(owner, id, damage);
                            }
                        }
                    }
                }
                Pending::Orbit {
                    owner,
                    zone,
                    left,
                    damage,
                } => {
                    if left > TICK {
                        still.push(Pending::Orbit {
                            owner,
                            zone,
                            left: left - TICK,
                            damage,
                        });
                    } else {
                        let at = self.players[&owner].character.point();
                        if let Some(id) = self.set_target(zone, at, 5., &[]) {
                            self.set_hit(owner, id, damage);
                        }
                    }
                }
                Pending::Pollen {
                    owner,
                    target,
                    zone,
                    left,
                    rate,
                } => {
                    if let Some(p) = self
                        .players
                        .get_mut(&target)
                        .filter(|p| p.character.hp > 0. && p.character.zone == zone)
                    {
                        p.character.hp =
                            (p.character.hp + rate * TICK.min(left)).min(p.character.max_hp());
                        if left > TICK {
                            still.push(Pending::Pollen {
                                owner,
                                target,
                                zone,
                                left: left - TICK,
                                rate,
                            });
                        }
                    }
                }
                Pending::Burn {
                    owner,
                    target,
                    zone,
                    left,
                    rate,
                } => {
                    if self
                        .slimes
                        .get(target)
                        .is_some_and(|s| !s.dead && s.zone == zone)
                    {
                        self.set_hit(owner, target, rate * TICK.min(left));
                        if left > TICK {
                            still.push(Pending::Burn {
                                owner,
                                target,
                                zone,
                                left: left - TICK,
                                rate,
                            });
                        }
                    }
                }
            }
        }
        self.set_pending.extend(still);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::items::ITEMS;

    fn world() -> World {
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
    }

    fn join(w: &mut World, session: u64, name: &str) -> String {
        let (peer, _rx) = mpsc::channel(512);
        w.join(
            session,
            None,
            Some(Look {
                name: name.into(),
                ..Look::default()
            }),
            peer,
        )
        .unwrap()["token"]
            .as_str()
            .unwrap()
            .to_owned()
    }

    fn wear(c: &mut Character, source: &str, count: usize) {
        c.level = 99;
        c.hp = c.max_hp();
        let mut slots = BTreeMap::new();
        for kind in [
            "armor",
            "weapon",
            "headgear",
            "shoulders",
            "gloves",
            "pants",
            "necklace",
            "accessory",
        ]
        .into_iter()
        .take(count)
        {
            let piece = ITEMS
                .iter()
                .find(|i| {
                    i.source.as_deref() == Some(source)
                        && i.kind == kind
                        && i.class.is_none_or(|class| class == c.look.class)
                })
                .unwrap();
            c.add_item(&piece.id, 1);
            let slot = match kind {
                "armor" => "chest",
                "weapon" => "hands",
                "accessory" => "accessory1",
                other => other,
            };
            slots.insert(slot.into(), piece.id.clone());
        }
        c.equip_slots(&slots).unwrap();
        c.resource = Some(c.max_resource());
    }

    #[test]
    fn rarity_refinement_and_duplicate_accessory_do_not_change_eight_distinct_slots() {
        let mut w = world();
        join(&mut w, 1, "Sets");
        let c = &mut w.players.get_mut(&1).unwrap().character;
        wear(c, "undervault", 8);
        assert_eq!(c.set_counts()["undervault"], 8);
        c.materialize_gear_instances();
        let mut merged = 0;
        for copy in c.gear_instances.iter_mut().filter(|copy| {
            ITEMS
                .iter()
                .any(|piece| piece.id == copy.item && piece.source.as_deref() == Some("undervault"))
        }) {
            if merged == 4 {
                break;
            }
            copy.rarity = "epic".into();
            copy.rank = 3;
            merged += 1;
        }
        assert_eq!(merged, 4, "four worn set copies are merged and refined");
        assert_eq!(c.set_counts()["undervault"], 8);
        let ring = c.equipment["accessory1"].clone();
        c.add_item(&ring, 1);
        c.equipment.insert("accessory2".into(), ring);
        assert_eq!(c.set_counts()["undervault"], 8);
        c.equip_slots(&BTreeMap::from([("necklace".into(), "none".into())]))
            .unwrap();
        assert_eq!(c.set_counts()["undervault"], 7);
        let cloister = ITEMS
            .iter()
            .find(|piece| {
                piece.source.as_deref() == Some("cathedral_cloister")
                    && piece.kind == "headgear"
                    && piece.class == Some(Class::Warrior)
            })
            .unwrap();
        c.add_item(&cloister.id, 1);
        c.equip_slots(&BTreeMap::from([("headgear".into(), cloister.id.clone())]))
            .unwrap();
        assert_eq!(c.set_counts()["undervault"], 6);
        assert_eq!(
            c.set_counts()["cathedral_cloister"],
            1,
            "swap immediately changes both set counts"
        );
        c.equipment.insert(
            "headgear".into(),
            "mage_headgear_apprentice_l20_vault".into(),
        );
        assert!(!c.set_counts().contains_key("cathedral_cloister"));
        assert_eq!(
            c.set_counts()["undervault"],
            6,
            "wrong-class pieces do not count"
        );
    }

    #[test]
    fn set_cooldown_power_signature_and_save_reload_follow_server_state() {
        let mut w = world();
        let token = join(&mut w, 1, "Sets");
        wear(
            &mut w.players.get_mut(&1).unwrap().character,
            "undervault",
            8,
        );
        let (sx, sy) = (w.slimes[0].x, w.slimes[0].y);
        for s in w.slimes.iter_mut().skip(1).filter(|s| s.zone == 0) {
            s.dead = true;
        }
        w.slimes[0].hp = 1_000_000.;
        w.slimes[0].max_hp = 1_000_000.;
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = sx - 0.8;
            c.y = sy;
            c.hp = c.max_hp();
            c.resource = Some(c.max_resource());
        }
        let ranked = skills::find(Class::Warrior, "shieldwall")
            .unwrap()
            .at_level(99);
        let ordinary = ranked.cooldown * w.players[&1].character.cooldown_multiplier();
        w.use_skill(1, "shieldwall", Point { x: 1., y: 0. });
        assert!((w.players[&1].skill_cd["shieldwall"] - ordinary * 0.85).abs() < 1e-8);
        let ranked = skills::find(Class::Warrior, "cleave").unwrap().at_level(99);
        let Effect::Cone { mult, .. } = ranked.effect else {
            panic!("cleave changed shape")
        };
        w.rng = 1234567;
        let expected = w.roll_damage(1, mult * 2.).0;
        w.rng = 1234567;
        w.use_skill(1, "cleave", Point { x: 1., y: 0. });
        assert!(
            (w.slimes[0].hp - (1_000_000. - expected)).abs() < 1e-8,
            "doubled rank-adjusted hit"
        );
        w.use_skill(1, "charge", Point { x: 1., y: 0. });
        assert!(w.players[&1].set_shield > 0.);
        assert!(w.players[&1].set_cd.contains_key("undervault"));
        assert_eq!(w.players[&1].snapshot()["setCounts"]["undervault"], 8);
        w.save();
        w.leave(1);
        let (peer, _rx) = mpsc::channel(512);
        w.join(2, Some(token), None, peer).unwrap();
        assert_eq!(w.players[&2].character.set_counts()["undervault"], 8);
        assert!(
            w.players[&2].set_cd.is_empty(),
            "signature timer is session state"
        );
    }

    #[test]
    fn pvp_basic_attack_cannot_trigger_set_signature() {
        let mut w = world();
        join(&mut w, 1, "SetA");
        join(&mut w, 2, "SetB");
        wear(
            &mut w.players.get_mut(&1).unwrap().character,
            "undervault",
            8,
        );
        let a = w.players[&1].character.id.clone();
        let b = w.players[&2].character.id.clone();
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.x = 9.;
            p.character.y = 8.;
            p.character.hp = p.character.max_hp();
        }
        {
            let p = w.players.get_mut(&2).unwrap();
            p.character.level = 99;
            p.character.x = 10.;
            p.character.y = 8.;
            p.character.hp = p.character.max_hp();
        }
        w.pvp_command(1, PvpCommand::DuelRequest { id: b.clone() });
        w.pvp_command(2, PvpCommand::DuelAccept { id: a });
        assert!(w.pvp_busy(&w.players[&1].character.id));
        let before = w.players[&2].character.hp;
        w.pvp_command(1, PvpCommand::Attack { id: b });
        assert!(w.players[&2].character.hp <= before && w.players[&2].character.hp > 1.);
        assert!(
            w.players[&1].set_cd.is_empty(),
            "a PvP basic attack cannot trigger a skill signature"
        );
    }

    #[test]
    fn undertow_keeps_enemy_spacing_when_pulling_toward_a_player() {
        let mut w = world();
        join(&mut w, 1, "Puller");
        wear(
            &mut w.players.get_mut(&1).unwrap().character,
            "cathedral_cloister",
            8,
        );
        for s in w.slimes.iter_mut().filter(|s| s.zone == 0) {
            s.dead = true;
        }
        w.slimes[0].dead = false;
        w.slimes[0].x = 12.;
        w.slimes[0].y = 12.;
        let p = &mut w.players.get_mut(&1).unwrap().character;
        p.x = 10.;
        p.y = 12.;
        let origin = p.point();
        assert_eq!(
            w.apply_set_signature(
                1,
                "groundslam",
                origin,
                Point { x: 1., y: 0. },
                Some(0),
                &[]
            )
            .as_deref(),
            Some("cathedral_cloister")
        );
        assert!(w.slimes[0].point().distance(origin) >= 1. - 1e-8);
        assert_ne!(
            (w.slimes[0].x.floor(), w.slimes[0].y.floor()),
            (origin.x.floor(), origin.y.floor())
        );
    }
}
