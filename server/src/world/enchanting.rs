use super::*;
use crate::enchanting::{self as catalog, Command, Enchant, Enchant::*};

const SPARK_RANGE: f64 = 5.;
const ROD_RANGE: f64 = 4.;
const GROVE_RANGE: f64 = 4.;
const DECOY_RANGE: f64 = 5.;

#[derive(Default)]
pub(super) struct Session {
    quickhands: f64,
    speed: Option<(Enchant, f64, f64)>,
    barriers: Vec<Barrier>,
    spell_hits: Vec<f64>,
    spell_ready: f64,
    shield_skills: BTreeMap<usize, (String, f64, bool)>,
    mark: Option<(usize, f64)>,
    rod_hits: u8,
    rod: Option<Ground>,
    recent_casts: BTreeMap<String, f64>,
    borrowed_ready: f64,
    shake: bool,
    moon: Option<Ground>,
    ash: Option<(usize, f64)>,
    grove: Option<(Ground, f64)>,
    zone: Option<usize>,
}

#[derive(Clone, Copy)]
pub(super) struct Ground {
    point: Point,
    zone: usize,
    until: f64,
}

#[derive(Clone, Copy)]
pub(super) struct Decoy {
    field: Ground,
    owner: u64,
}

struct Barrier {
    source: Enchant,
    remaining: f64,
    until: f64,
}

#[derive(Clone, Copy)]
pub(super) enum Hit {
    Basic,
    Skill,
}

pub(super) struct SkillHit {
    enemy: usize,
    zone: usize,
    point: Point,
    killed: bool,
}

impl Player {
    fn available_enchant(&self, enchant: Enchant, now: f64) -> bool {
        self.character
            .enchanting
            .ready
            .get(&enchant)
            .is_none_or(|time| *time <= now)
            && self.character.wears_enchant(enchant)
    }

    fn start_enchant_cooldown(&mut self, enchant: Enchant, now: f64) {
        self.character
            .enchanting
            .ready
            .insert(enchant, now + enchant.recipe().cooldown);
        self.enchanting.zone = Some(self.character.zone);
    }

    fn enchant_speed(&mut self, effect: Enchant, until: f64, bonus: f64) {
        self.enchanting.speed = Some((effect, until, bonus));
    }

    fn enchant_barrier(&mut self, source: Enchant, fraction: f64, until: f64) {
        self.enchanting.zone = Some(self.character.zone);
        self.enchanting.barriers.retain(|b| b.source != source);
        self.enchanting.barriers.push(Barrier {
            source,
            remaining: self.character.max_hp() * fraction,
            until,
        });
    }

    pub(super) fn enchant_absorb(&mut self, mut damage: f64, time: f64) -> f64 {
        for b in self
            .enchanting
            .barriers
            .iter_mut()
            .filter(|b| b.until > time)
        {
            let absorbed = damage.min(b.remaining);
            b.remaining -= absorbed;
            damage -= absorbed;
        }
        damage
    }

    pub(super) fn enchant_attack_speed(&self, time: f64) -> f64 {
        if self.enchanting.quickhands > time && self.character.wears_enchant(Quickhands) {
            0.15
        } else {
            0.
        }
    }

    pub(super) fn enchant_move_speed(&self, time: f64) -> f64 {
        self.enchanting
            .speed
            .filter(|(effect, until, _)| *until > time && self.character.wears_enchant(*effect))
            .map_or(0., |(_, _, bonus)| bonus)
    }

    pub(super) fn enchant_cast_modifiers(&self, time: f64) -> (bool, bool) {
        let s = &self.enchanting;
        (
            s.spell_ready > time && self.character.wears_enchant(Spellweaver),
            s.borrowed_ready > time && self.character.wears_enchant(BorrowedTime),
        )
    }

    pub(super) fn enchant_cast(
        &mut self,
        skill: &str,
        discounted: bool,
        borrowed: bool,
        time: f64,
        now: f64,
    ) {
        if discounted {
            self.enchanting.spell_ready = 0.;
            self.start_enchant_cooldown(Spellweaver, now);
        }
        if borrowed {
            self.enchanting.borrowed_ready = 0.;
            self.start_enchant_cooldown(BorrowedTime, now);
        } else if self.enchanting.borrowed_ready <= time
            && self.available_enchant(BorrowedTime, now)
        {
            let casts = &mut self.enchanting.recent_casts;
            casts.retain(|_, cast| *cast + 8. >= time);
            casts.insert(skill.into(), time);
            if casts.len() >= 3 {
                casts.clear();
                self.enchanting.borrowed_ready = time + 6.;
            }
            self.enchanting.zone = Some(self.character.zone);
        }
    }
}

impl World {
    pub(super) fn enchanting_command(&mut self, session: u64, request: Command) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let open = matches!(request, Command::Open);
        let all = matches!(request, Command::Craft { all: true, .. });
        let mut staged = p.character.clone();
        let previous_skill = p.character.enchanting.proficiency.skill;
        let gear_count = p.character.gear_instances.len();
        let result = if !open
            && (p.character.hp <= 0.
                || p.combat_left > 0.
                || p.attack > 0.
                || p.character.spark_travel.is_some()
                || p.frozen
                || self.time < p.cutscene_until
                || self.trade_index(&p.character.id).is_some()
                || self.pvp_busy(&p.character.id))
        {
            Err("You can use Enchanting while alive and out of combat or travel.")
        } else {
            staged
                .enchant_action(request)
                .and_then(|(notice, training)| {
                    let notice = if let Some(training) = training {
                        staged.enchanting.proficiency.train_batch(
                            training.attempts,
                            training.quality,
                            training.cap,
                            crate::profession::MAX_SKILL,
                            || self.profession_roll(),
                        );
                        if all {
                            format!("Crafted {} enchant scrolls.", training.attempts)
                        } else {
                            notice.into()
                        }
                    } else {
                        notice.into()
                    };
                    if !open || staged.gear_instances.len() != gear_count {
                        self.store
                            .save_many([&staged].into_iter())
                            .map_err(|_| "The enchanting change could not be saved.")?;
                    }
                    Ok(notice)
                })
        };
        let p = self.players.get_mut(&session).unwrap();
        if result.is_ok() {
            p.character = staged;
        }
        let c = &p.character;
        let copies: Vec<_> = c
            .gear_instances
            .iter()
            .filter_map(|gear| {
                let piece = item(&gear.item)?;
                if piece.starter
                    || !matches!(
                        gear.rarity.as_str(),
                        "uncommon" | "rare" | "epic" | "legendary"
                    )
                {
                    return None;
                }
                Some(json!({"gear":gear,"worn":c.gear_instance_equipped(gear.id),"skillCap":catalog::equipment_skill_cap(gear)}))
            })
            .collect();
        let _ = p
            .peer
            .try_send(json!({"type":"enchanting","ok":result.is_ok(),
            "text":result.unwrap_or_else(|text| text.into()),"skill":c.enchanting.proficiency.skill,
            "maxSkill":crate::profession::MAX_SKILL,
            "trainingGearLevel":crate::profession::training_gear_level(c.enchanting.proficiency.skill),
            "craftSkillCaps":catalog::CATALOG.tiers.each_ref().map(|tier| tier.skill_cap()),
            "skillUp":c.enchanting.proficiency.skill > previous_skill,
            "recipes":c.enchanting.recipes,"inventory":c.inventory,"copies":copies}));
    }

    pub(super) fn enchant_now(&self) -> f64 {
        self.enchant_epoch + self.time
    }

    pub(super) fn enchant_pve(&self, session: u64) -> bool {
        self.players.get(&session).is_some_and(|p| {
            p.is_human()
                && !p.is_hidden()
                && !p.pvp_flag
                && p.pvp_fight <= 0.
                && p.character.hp > 0.
                && !self.pvp_busy(&p.character.id)
        })
    }

    pub(super) fn enchant_random(&mut self) -> f64 {
        self.enchant_rng = self
            .enchant_rng
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1);
        (self.enchant_rng >> 32) as f64 / 4294967296.
    }

    pub(super) fn enchant_recipe_drop(
        &mut self,
        owner: &str,
        zone: usize,
        point: Point,
        kind: &str,
        level: u32,
    ) {
        if level >= catalog::CATALOG.tiers[0].min_enemy_level {
            let chance = self.enchant_random();
            let choice = self.enchant_random();
            if let Some(recipe) =
                catalog::drop_recipe(level, is_elite(kind) || is_boss(kind), chance, choice)
            {
                self.loot_drop(owner, zone, point, &recipe.item("recipe"));
            }
        }
    }

    /// Resolve the actual hit first. Secondary damage uses the same monster and loot rules and skips equipment procs.
    pub(super) fn enchant_hit(
        &mut self,
        enemy: usize,
        session: u64,
        damage: f64,
        crit: bool,
        source: Hit,
    ) -> f64 {
        let dealt = self.hit_slime(enemy, session, damage, crit);
        if dealt <= 0.
            || !self.players.get(&session).is_some_and(|p| {
                p.character
                    .gear_instances
                    .iter()
                    .any(|g| g.enchant.is_some())
            })
            || !self.enchant_pve(session)
        {
            return dealt;
        }
        let target = &self.slimes[enemy];
        let hit = SkillHit {
            enemy,
            zone: target.zone,
            point: target.point(),
            killed: target.dead,
        };
        if matches!(source, Hit::Skill)
            && let Some(hits) = &mut self.enchant_skill_hits
        {
            hits.push(hit);
        } else {
            self.resolve_enchant_hit(session, hit, source, damage);
        }
        dealt
    }

    pub(super) fn finish_enchant_skill(&mut self, session: u64, skill: &str) {
        let Some(hits) = self.enchant_skill_hits.take() else {
            return;
        };
        self.cur_skill = skill.into();
        for hit in hits {
            self.resolve_enchant_hit(session, hit, Hit::Skill, 0.);
        }
        self.cur_skill.clear();
    }

    fn resolve_enchant_hit(&mut self, session: u64, hit: SkillHit, source: Hit, damage: f64) {
        match source {
            Hit::Basic => self.enchant_basic(session, hit.enemy, hit.zone, hit.point, damage),
            Hit::Skill => self.enchant_skill_hit(session, hit.enemy, hit.zone, hit.point),
        }
        if hit.killed {
            self.enchant_pass_mark(session, hit.enemy);
        }
    }

    fn enchant_basic(
        &mut self,
        session: u64,
        enemy: usize,
        zone: usize,
        point: Point,
        damage: f64,
    ) {
        let now = self.enchant_now();
        let time = self.time;
        let reference = self.set_basic_damage(session);
        let p = &self.players[&session];
        let double = p.available_enchant(DoubleTap, now) && !self.slimes[enemy].dead;
        let quick = p.available_enchant(Quickhands, now);
        let double = double && self.enchant_random() < 0.20;
        let quick = quick && self.enchant_random() < 0.15;
        let p = self.players.get_mut(&session).unwrap();
        if quick {
            p.start_enchant_cooldown(Quickhands, now);
            p.enchanting.quickhands = time + 8.;
        }
        if p.enchanting.spell_ready <= time && p.available_enchant(Spellweaver, now) {
            p.enchanting.spell_hits.retain(|hit| *hit + 8. >= time);
            p.enchanting.spell_hits.push(time);
            p.enchanting.zone = Some(zone);
            if p.enchanting.spell_hits.len() >= 3 {
                p.enchanting.spell_hits.clear();
                p.enchanting.spell_ready = time + 5.;
            }
        }
        if p.available_enchant(PassingSpark, now) {
            p.start_enchant_cooldown(PassingSpark, now);
            p.enchanting.mark = Some((enemy, reference));
        }
        let shieldbreak = p.character.wears_enchant(Shieldbreaker)
            && p.enchanting
                .shield_skills
                .get(&enemy)
                .is_some_and(|(_, _, ready)| *ready);
        if shieldbreak {
            p.enchanting.shield_skills.clear();
            p.start_enchant_cooldown(Shieldbreaker, now);
        }
        if p.available_enchant(LightningRod, now) {
            p.enchanting.zone = Some(zone);
            p.enchanting.rod_hits += 1;
            if p.enchanting.rod_hits == 5 {
                p.start_enchant_cooldown(LightningRod, now);
                p.enchanting.rod_hits = 0;
                p.enchanting.rod = Some(Ground {
                    point,
                    zone,
                    until: time + 5.,
                });
            }
        }
        if double {
            self.players
                .get_mut(&session)
                .unwrap()
                .start_enchant_cooldown(DoubleTap, now);
            self.enchant_damage(session, enemy, damage * 0.5, DoubleTap);
        }
        if shieldbreak {
            self.enchant_damage(session, enemy, damage * 0.6, Shieldbreaker);
        }
    }

    fn enchant_skill_hit(&mut self, session: u64, enemy: usize, zone: usize, point: Point) {
        let now = self.enchant_now();
        let time = self.time;
        let p = self.players.get_mut(&session).unwrap();
        if p.available_enchant(Shieldbreaker, now) {
            let chain = p
                .enchanting
                .shield_skills
                .entry(enemy)
                .or_insert_with(|| (self.cur_skill.clone(), time + 5., false));
            if !chain.2 {
                if chain.1 >= time && chain.0 != self.cur_skill {
                    chain.2 = true;
                } else {
                    *chain = (self.cur_skill.clone(), time + 5., false);
                }
            }
            p.enchanting.zone = Some(zone);
        }
        let Some(rod) = p.enchanting.rod.filter(|r| {
            r.until > time
                && r.zone == zone
                && point.distance(r.point) <= ROD_RANGE
                && p.character.wears_enchant(LightningRod)
        }) else {
            return;
        };
        p.enchanting.rod = None;
        let damage = self.set_basic_damage(session) * 0.45;
        for target in self
            .enchant_targets(session, rod.point, zone, ROD_RANGE, &[])
            .into_iter()
            .take(3)
        {
            self.enchant_damage(session, target, damage, LightningRod);
        }
    }

    fn enchant_targets(
        &self,
        session: u64,
        point: Point,
        zone: usize,
        radius: f64,
        skip: &[usize],
    ) -> Vec<usize> {
        self.enemies_near(zone, point, radius, skip)
            .into_iter()
            .filter(|&id| {
                let enemy = &self.slimes[id];
                point.distance(enemy.point()) <= radius
                    && (seasonal_hunt::for_kind(&enemy.kind).is_none()
                        || self.festival_member(&enemy.kind, session))
            })
            .collect()
    }

    fn enchant_pass_mark(&mut self, session: u64, enemy: usize) {
        let p = self.players.get_mut(&session).unwrap();
        let Some((marked, damage)) = p.enchanting.mark else {
            return;
        };
        if marked != enemy || !p.character.wears_enchant(PassingSpark) {
            return;
        }
        p.enchanting.mark = None;
        let zone = self.slimes[enemy].zone;
        let mut defeated = enemy;
        while let Some(next) = self
            .enchant_targets(
                session,
                self.slimes[defeated].point(),
                zone,
                SPARK_RANGE,
                &[defeated],
            )
            .first()
            .copied()
        {
            let dealt = self.enchant_damage(session, next, damage * 0.4, PassingSpark);
            if dealt <= 0. {
                return;
            }
            if !self.slimes[next].dead {
                self.players.get_mut(&session).unwrap().enchanting.mark = Some((next, damage));
                break;
            }
            defeated = next;
        }
    }

    fn enchant_damage(&mut self, session: u64, enemy: usize, damage: f64, effect: Enchant) -> f64 {
        if self.slimes[enemy].dead {
            return 0.;
        }
        let previous = std::mem::replace(&mut self.cur_skill, effect.item("proc"));
        let dealt = self.hit_monster(enemy, session, damage, false, true);
        self.cur_skill = previous;
        if dealt > 0. {
            let s = &self.slimes[enemy];
            self.enchant_field(session, effect, s.point(), s.zone, 0.8, 0.35);
        }
        dealt
    }

    pub(super) fn enchant_xp_kill(&mut self, session: u64) {
        let now = self.enchant_now();
        if self.enchant_pve(session) && self.players[&session].available_enchant(SecondWind, now) {
            let p = self.players.get_mut(&session).unwrap();
            p.start_enchant_cooldown(SecondWind, now);
            let max = p.character.max_hp();
            p.character.hp = (p.character.hp + max * 0.04).min(max);
            p.character
                .change_resource(p.character.max_resource() * 0.05);
        }
    }

    pub(super) fn enchant_heal(&mut self, caster: u64, target: u64, before: f64, gained: f64) {
        if caster == target
            || gained <= 0.
            || !self.enchant_pve(caster)
            || !self.enchant_pve(target)
        {
            return;
        }
        let now = self.enchant_now();
        let giver = &self.players[&caster];
        let recipient = &self.players[&target];
        if before < recipient.character.max_hp() * 0.4
            && giver.available_enchant(GuardianThread, now)
            && self
                .party_mates(&giver.character.id)
                .contains(&recipient.character.id)
        {
            self.players
                .get_mut(&caster)
                .unwrap()
                .start_enchant_cooldown(GuardianThread, now);
            self.players.get_mut(&target).unwrap().enchant_barrier(
                GuardianThread,
                0.10,
                self.time + 5.,
            );
        }
    }

    pub(super) fn enchant_dodge(&mut self, session: u64, zone: usize, point: Point) {
        let now = self.enchant_now();
        let time = self.time;
        let p = self.players.get_mut(&session).unwrap();
        if p.available_enchant(Slipstream, now) {
            p.start_enchant_cooldown(Slipstream, now);
            p.enchant_speed(Slipstream, time + 3., 0.20);
        }
        if p.available_enchant(Moonstep, now) {
            p.start_enchant_cooldown(Moonstep, now);
            let field = Ground {
                point,
                zone,
                until: time + 3.,
            };
            p.enchanting.moon = Some(field);
            for enemy in self.enchant_targets(session, point, zone, DECOY_RANGE, &[]) {
                let s = &mut self.slimes[enemy];
                if !is_elite(&s.kind)
                    && !is_boss(&s.kind)
                    && seasonal_hunt::for_kind(&s.kind).is_none()
                    && !crate::cathedral::enemy(&s.kind).is_some_and(|entry| entry.add)
                    && !s.kind.starts_with("es_")
                    && s.kind != raid_key::KIND
                {
                    s.enchant_decoy = Some(Decoy {
                        field,
                        owner: session,
                    });
                }
            }
        }
    }

    pub(super) fn enchant_incoming(
        &mut self,
        session: u64,
        attacker: Option<usize>,
        before: f64,
        dazed: bool,
        damage: f64,
    ) {
        let now = self.enchant_now();
        let time = self.time;
        let p = self.players.get_mut(&session).unwrap();
        if damage > 0. && dazed && p.available_enchant(ShakeItOff, now) {
            p.start_enchant_cooldown(ShakeItOff, now);
            p.daze *= 0.5;
            p.enchanting.shake = true;
        }
        if p.character.hp <= 0. && p.available_enchant(RiseFromAsh, now) && damage > 0. {
            p.start_enchant_cooldown(RiseFromAsh, now);
            p.character.hp = 1.;
            p.enchant_barrier(RiseFromAsh, 0.15, time + 4.);
            p.enchanting.ash = attacker.map(|id| (id, time + 4.));
        }
        if p.character.hp <= 0. {
            return;
        }
        let max = p.character.max_hp();
        for (effect, threshold, fraction, seconds) in
            [(Brace, 0.5, 0.08, 5.), (ArcaneBulwark, 0.4, 0.20, 6.)]
        {
            if before >= max * threshold
                && p.character.hp < max * threshold
                && p.available_enchant(effect, now)
            {
                p.start_enchant_cooldown(effect, now);
                p.enchant_barrier(effect, fraction, time + seconds);
            }
        }
        if before >= max * 0.4
            && p.character.hp < max * 0.4
            && p.available_enchant(HeartwoodGrove, now)
        {
            p.start_enchant_cooldown(HeartwoodGrove, now);
            let zone = p.character.zone;
            let point = p.character.point();
            p.enchanting.grove = Some((
                Ground {
                    point,
                    zone,
                    until: time + 6.,
                },
                time + 1.,
            ));
        }
    }

    pub(super) fn update_enchanting(&mut self, session: u64) {
        let time = self.time;
        let p = &self.players[&session];
        let Some(zone) = p.enchanting.zone else {
            return;
        };
        if zone != p.character.zone || !self.enchant_pve(session) {
            self.players.get_mut(&session).unwrap().enchanting = Session::default();
            return;
        }
        let p = self.players.get_mut(&session).unwrap();
        let s = &mut p.enchanting;
        s.barriers.retain(|b| b.remaining > 0. && b.until > time);
        s.shield_skills.retain(|&id, (_, until, ready)| {
            (*ready || *until >= time)
                && self
                    .slimes
                    .get(id)
                    .is_some_and(|s| !s.dead && s.zone == zone)
        });
        if s.mark.is_some_and(|(id, _)| {
            self.slimes
                .get(id)
                .is_none_or(|enemy| enemy.dead || enemy.zone != zone)
        }) || (s.mark.is_some() && !p.character.wears_enchant(PassingSpark))
        {
            s.mark = None;
        }
        if s.rod.is_some_and(|rod| rod.until <= time) {
            s.rod = None;
        }
        if s.shake && p.daze <= TICK {
            s.shake = false;
            p.enchant_speed(ShakeItOff, time + 3., 0.25);
        }
        if p.enchanting.moon.is_some_and(|field| field.until <= time) {
            p.enchanting.moon = None;
            p.enchant_speed(Moonstep, time + 3., 0.30);
        }
        if let Some((attacker, until)) = p.enchanting.ash {
            let shield = p
                .enchanting
                .barriers
                .iter()
                .any(|b| b.source == RiseFromAsh);
            let enemy = self
                .slimes
                .get(attacker)
                .filter(|s| s.zone == zone && !s.dead);
            if time >= until || !shield || enemy.is_none() {
                p.enchanting.ash = None;
            } else if let Some(enemy) = enemy
                && !self.maps[zone].line_clear(p.character.point(), enemy.point(), 0.05)
            {
                let max = p.character.max_hp();
                p.character.hp = (p.character.hp + max * 0.2).min(max);
                p.enchanting.ash = None;
            }
        }
        let Some((grove, next)) = p.enchanting.grove else {
            return;
        };
        if time + 1e-7 < next {
            return;
        }
        p.enchanting.grove = (next + 1. <= grove.until + 1e-7).then_some((grove, next + 1.));
        let owner = p.character.id.clone();
        let party = self.party_mates(&owner);
        let targets: Vec<_> = self
            .players
            .iter()
            .filter(|(id, p)| {
                p.character.zone == zone
                    && grove.point.distance(p.character.point()) <= GROVE_RANGE
                    && (p.character.id == owner || party.contains(&p.character.id))
                    && self.enchant_pve(**id)
            })
            .map(|(&id, _)| id)
            .collect();
        for id in targets {
            let p = self.players.get_mut(&id).unwrap();
            let max = p.character.max_hp();
            p.character.hp = (p.character.hp + max * 0.02).min(max);
        }
    }

    /// Moonstep supplies a ground target without creating a fake player or awarding the decoy loot.
    pub(super) fn enchant_decoy_update(&mut self, id: usize, bodies: &[(Point, f64)]) -> bool {
        let s = &self.slimes[id];
        let Some(decoy) = s.enchant_decoy else {
            return false;
        };
        let point = decoy.field.point;
        let zone = decoy.field.zone;
        let valid = decoy.field.until > self.time
            && self.enchant_pve(decoy.owner)
            && self.players[&decoy.owner].character.zone == zone
            && self.players[&decoy.owner].character.wears_enchant(Moonstep);
        let s = &mut self.slimes[id];
        if !valid {
            s.enchant_decoy = None;
            return false;
        }
        s.state = "chase".into();
        let mut at = s.point();
        let direction = at.direction(point);
        let travel = if s.set_root_left > 0. {
            0.
        } else {
            Slime::stats(&s.kind).2
                * TICK
                * if s.set_slow_left > 0. {
                    1. - s.set_slow
                } else {
                    1.
                }
        }
        .min((at.distance(point) - 0.65).max(0.));
        walk_with_actors(&self.maps[zone], &mut at, direction, travel, s.r, bodies);
        if !self.maps[zone].in_city(at) {
            s.x = at.x;
            s.y = at.y;
        }
        s.dir = if direction.x - direction.y >= 0. {
            1.
        } else {
            -1.
        };
        true
    }

    pub(super) fn enchant_fields(&self, zone: usize) -> Vec<Value> {
        let mut fields = vec![];
        for p in self.players.values().filter(|p| p.character.zone == zone) {
            let state = &p.enchanting;
            if let Some((id, _)) = state.mark
                && let Some(s) = self.slimes.get(id).filter(|s| s.zone == zone && !s.dead)
            {
                fields.push(json!({"enchant":PassingSpark,"x":s.x,"y":s.y,"radius":0.5}));
            }
            for (effect, field, radius) in [
                (LightningRod, state.rod, ROD_RANGE),
                (Moonstep, state.moon, DECOY_RANGE),
                (
                    HeartwoodGrove,
                    state.grove.map(|(field, _)| field),
                    GROVE_RANGE,
                ),
            ] {
                if let Some(field) = field.filter(|f| f.zone == zone && f.until > self.time) {
                    fields.push(json!({"enchant":effect,"x":field.point.x,"y":field.point.y,"radius":radius}));
                }
            }
        }
        fields
    }

    fn enchant_field(
        &self,
        session: u64,
        effect: Enchant,
        point: Point,
        zone: usize,
        radius: f64,
        duration: f64,
    ) {
        self.emit_zone(
            zone,
            json!({"type":"event","kind":"enchantEffect","enchant":effect,
            "actor":self.players[&session].character.id,"x":point.x,"y":point.y,"radius":radius,
            "duration":duration}),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::super::wyrd_tests::{at, drain, join, place, world};
    use super::*;
    use crate::enchanting::CATALOG;

    fn character(w: &mut World, session: u64) -> &mut Character {
        &mut w.players.get_mut(&session).unwrap().character
    }

    fn piece(kind: &str, rarity: &str, class: Class) -> &'static Item {
        ITEMS
            .iter()
            .find(|item| {
                item.kind == kind
                    && item.rarity == rarity
                    && !item.starter
                    && item.class.is_none_or(|c| c == class)
                    && item.variant.as_deref().is_none_or(|variant| {
                        !matches!(kind, "armor" | "weapon")
                            || equipment(class, kind, variant)
                                .is_some_and(|worn| worn.id == item.id)
                    })
            })
            .unwrap()
    }

    fn worn(w: &mut World, session: u64, kind: &str, rarity: &str, enchant: Enchant) -> u64 {
        let c = character(w, session);
        let item = piece(kind, rarity, c.look.class);
        c.level = 95;
        c.add_item(&item.id, 1);
        c.materialize_gear_instances();
        let copy = c
            .gear_instances
            .iter_mut()
            .find(|g| g.item == item.id)
            .unwrap();
        copy.enchant = Some(enchant);
        let id = copy.id;
        let slot = match kind {
            "armor" => "chest",
            "weapon" => "hands",
            "accessory" => "accessory1",
            other => other,
        };
        c.equip_slots(&[(slot.into(), item.id.clone())].into())
            .unwrap();
        assert!(c.wears_enchant(enchant));
        id
    }

    fn enemies(w: &mut World, coords: &[(f64, f64)]) {
        for (i, x) in coords.iter().enumerate() {
            let s = &mut w.slimes[i];
            s.x = x.0;
            s.hx = s.x;
            s.y = x.1;
            s.hy = s.y;
            s.kind = "slime".into();
            s.zone = 0;
            s.level = 1;
            s.dead = false;
            s.hp = 200.;
            s.max_hp = 200.;
        }
        for s in &mut w.slimes[coords.len()..] {
            if s.zone == 0 {
                s.dead = true;
            }
        }
    }

    fn hit(w: &mut World, enemy: usize, amount: f64, source: Hit) -> f64 {
        w.enchant_hit(enemy, 1, amount, false, source)
    }

    fn request(w: &mut World, rx: &mut mpsc::Receiver<Value>, request: Value) -> Value {
        w.profession_rng = 0;
        w.message(
            1,
            serde_json::from_value(json!({"type":"enchanting","request":request})).unwrap(),
        );
        drain(rx)
            .into_iter()
            .find(|v| v["type"] == "enchanting")
            .unwrap()
    }

    #[test]
    fn enchanting_profession_unlocks_and_spends_currency_atomically() {
        let mut w = world();
        let (tx, mut rx) = mpsc::channel(4096);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        let response = request(&mut w, &mut rx, json!({"op":"open"}));
        assert_eq!(response["skill"], 0);
        assert_eq!(response["maxSkill"], 300);
        assert!(
            serde_json::from_value::<ClientMessage>(
                json!({"type":"enchanting","request":{"op":"learn"}})
            )
            .is_err()
        );
        let train = |npc: &str| ClientMessage::Interact {
            npc: npc.into(),
            offer: Some("learn_enchanting".into()),
        };
        let master = w.maps[0]
            .npcs
            .iter()
            .find(|npc| npc.id == "alder_enchanting")
            .unwrap()
            .clone();
        let nearby = at(master.x, master.y);
        place(&mut w, 1, 0, at(master.x + 5., master.y));
        w.message(1, train(&master.id));
        assert_eq!(request(&mut w, &mut rx, json!({"op":"open"}))["skill"], 0);
        let apothecary = w.maps[0]
            .npcs
            .iter()
            .find(|npc| npc.id == "apothecary")
            .unwrap();
        let wrong = apothecary.position_at(w.time);
        place(&mut w, 1, 0, wrong);
        w.message(1, train("apothecary"));
        assert_eq!(request(&mut w, &mut rx, json!({"op":"open"}))["skill"], 0);
        w.time += 1.;
        place(&mut w, 1, 0, nearby);
        w.message(1, train(&master.id));
        assert!(
            drain(&mut rx)
                .iter()
                .any(|p| p["type"] == "dialogue" && p["enchantingSkill"] == 1)
        );
        assert_eq!(request(&mut w, &mut rx, json!({"op":"open"}))["skill"], 1);
        let epic = Shieldbreaker.item("recipe");
        let rare = DoubleTap.item("recipe");
        character(&mut w, 1).add_item(&epic, 1);
        character(&mut w, 1).add_item(&rare, 2);
        for enchant in [Shieldbreaker, DoubleTap] {
            assert_eq!(
                request(&mut w, &mut rx, json!({"op":"study","enchant":enchant}))["ok"],
                true
            );
        }
        assert_eq!(
            request(&mut w, &mut rx, json!({"op":"study","enchant":DoubleTap}))["ok"],
            false
        );
        assert_eq!(character(&mut w, 1).quantity(&rare), 1);
        let mut ids = vec![];
        for (rarity, resource, amount) in [
            ("uncommon", "enchant_dust", 2),
            ("rare", "enchant_essence", 2),
            ("epic", "enchant_shard", 2),
            ("legendary", "enchant_core", 1),
        ] {
            let piece = piece("necklace", rarity, Class::Warrior);
            let c = character(&mut w, 1);
            c.add_item(&piece.id, 2);
            c.materialize_gear_instances();
            let id = c
                .gear_instances
                .iter()
                .filter(|g| g.item == piece.id)
                .last()
                .unwrap()
                .id;
            ids.push(id);
            assert_eq!(
                request(&mut w, &mut rx, json!({"op":"disenchant","copy":id}))["ok"],
                true
            );
            let c = character(&mut w, 1);
            assert_eq!(c.quantity(&piece.id), 1);
            assert!(!c.gear_instances.iter().any(|g| g.id == id));
            assert_eq!(c.quantity(resource), amount);
        }
        assert_eq!(character(&mut w, 1).enchanting.proficiency.skill, 5);
        assert_eq!(
            request(
                &mut w,
                &mut rx,
                json!({"op":"craft","enchant":Shieldbreaker})
            )["ok"],
            false
        );
        character(&mut w, 1).add_item("enchant_dust", 2);
        assert_eq!(
            request(&mut w, &mut rx, json!({"op":"craft","enchant":DoubleTap}))["skill"],
            6
        );
        assert_eq!(character(&mut w, 1).quantity(&DoubleTap.item("scroll")), 1);
        character(&mut w, 1).add_item("enchant_dust", 4);
        let before = character(&mut w, 1).inventory.clone();
        assert_eq!(
            request(&mut w, &mut rx, json!({"op":"craft","enchant":DoubleTap}))["ok"],
            false
        );
        assert_eq!(
            character(&mut w, 1).inventory,
            before,
            "failed craft cannot spend the first material"
        );
        assert_eq!(
            request(&mut w, &mut rx, json!({"op":"disenchant","copy":ids[0]}))["ok"],
            false
        );
        let saved = w.store.load(token).unwrap().unwrap();
        assert_eq!(saved.enchanting.proficiency.skill, 6);
        assert_eq!(saved.enchanting.recipes, [DoubleTap, Shieldbreaker].into());
    }


    #[test]
    fn enchanting_bulk_scrolls_use_limiting_material_and_save_the_batch() {
        let mut w = world();
        let (tx, mut rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let c = character(&mut w, 1);
        c.enchanting.proficiency.skill = 28;
        c.enchanting.recipes.insert(DoubleTap);
        c.add_item("enchant_dust", 17);
        c.add_item("enchant_essence", 6);
        let craft = json!({"op":"craft","enchant":DoubleTap,"all":true});
        let packet = request(&mut w, &mut rx, craft.clone());
        assert_eq!(packet["ok"], true);
        assert_eq!(packet["skill"], 30);
        assert_eq!(packet["text"], "Crafted 3 enchant scrolls.");
        assert_eq!(request(&mut w, &mut rx, craft)["ok"], false);
        let saved = w.store.load(welcome["token"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(saved.quantity(&DoubleTap.item("scroll")), 3);
        assert_eq!(saved.quantity("enchant_dust"), 5);
        assert_eq!(saved.quantity("enchant_essence"), 0);
        assert_eq!(saved.enchanting.proficiency.skill, 30);
    }

    #[test]
    fn enchanting_applying_as_a_non_enchanter_preserves_a_copy_through_bank_and_replacement() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let gear = piece("weapon", "epic", Class::Warrior);
        let green = piece("weapon", "uncommon", Class::Warrior);
        let wrong = piece("necklace", "epic", Class::Warrior);
        let c = character(&mut w, 1);
        for (row, count) in [(gear, 2), (green, 1), (wrong, 1)] {
            c.add_item(&row.id, count);
        }
        c.add_item(&DoubleTap.item("scroll"), 1);
        c.add_item(&Shieldbreaker.item("scroll"), 1);
        c.materialize_gear_instances();
        let copy =
            |c: &Character, i: &Item| c.gear_instances.iter().find(|g| g.item == i.id).unwrap().id;
        let target = copy(c, gear);
        for invalid in [copy(c, green), copy(c, wrong), u64::MAX] {
            assert_eq!(
                request(
                    &mut w,
                    &mut rx,
                    json!({"op":"apply","enchant":DoubleTap,"copy":invalid})
                )["ok"],
                false
            );
        }
        assert_eq!(
            request(
                &mut w,
                &mut rx,
                json!({"op":"apply","enchant":DoubleTap,"copy":target})
            )["ok"],
            true
        );
        assert_eq!(
            request(
                &mut w,
                &mut rx,
                json!({"op":"apply","enchant":Shieldbreaker,"copy":target})
            )["ok"],
            false,
            "stale preview must not replace an enchant"
        );
        assert_eq!(
            request(
                &mut w,
                &mut rx,
                json!({"op":"apply","enchant":Shieldbreaker,"copy":target,"expected":DoubleTap})
            )["ok"],
            true
        );
        let c = character(&mut w, 1);
        assert_eq!(c.enchanting.proficiency.skill, 0);
        c.bank_deposit(&gear.id, 1, Some(target)).unwrap();
        let banked = c.bank.gear.first().unwrap();
        assert_eq!(banked.enchant, Some(Shieldbreaker));
        let mut value = serde_json::to_value(&*c).unwrap();
        value.as_object_mut().unwrap().remove("enchanting");
        let mut loaded: Character = serde_json::from_value(value).unwrap();
        loaded.bank_withdraw(&gear.id, 1, Some(target)).unwrap();
        assert_eq!(
            loaded
                .gear_instances
                .iter()
                .filter(|g| g.item == gear.id)
                .map(|g| g.enchant)
                .collect::<Vec<_>>(),
            [None, Some(Shieldbreaker)]
        );
    }

    #[test]
    fn enchanting_bands_gate_disenchanting_and_cheap_scrolls() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let c = character(&mut w, 1);
        c.enchanting.proficiency.initialize(29);
        let low = "necklace_moonstone_l5_green";
        let next = "necklace_moonstone_l10_green";
        c.add_item(low, 2);
        c.add_item(next, 1);
        c.materialize_gear_instances();
        let low_copies: Vec<_> = c
            .gear_instances
            .iter()
            .filter(|g| g.item == low)
            .map(|g| g.id)
            .collect();
        let next_copy = c.gear_instances.iter().find(|g| g.item == next).unwrap().id;
        let command = |copy| json!({"op":"disenchant","copy":copy});
        let first = request(&mut w, &mut rx, command(low_copies[0]));
        assert_eq!(first["skill"], 30);
        assert_eq!(first["trainingGearLevel"], 6);
        assert_eq!(first["craftSkillCaps"], json!([30, 90, 210]));
        let second = request(&mut w, &mut rx, command(low_copies[1]));
        assert_eq!(second["skill"], 30);
        assert_eq!(second["ok"], true);
        assert_eq!(character(&mut w, 1).quantity("enchant_dust"), 4);
        let c = character(&mut w, 1);
        c.enchanting.recipes.insert(DoubleTap);
        c.add_item("enchant_essence", 2);
        let crafted = request(&mut w, &mut rx, json!({"op":"craft","enchant":DoubleTap}));
        assert_eq!(crafted["ok"], true);
        assert_eq!(crafted["skill"], 30);
        assert_eq!(request(&mut w, &mut rx, command(next_copy))["skill"], 31);
    }

    #[test]
    fn enchanting_application_can_grant_the_last_skill_point_and_cannot_exceed_it() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let c = character(&mut w, 1);
        let gear = "warrior_weapon_royal_l50_purple";
        c.add_item(gear, 1);
        c.materialize_gear_instances();
        let item = c
            .gear_instances
            .iter_mut()
            .find(|g| g.item == gear)
            .unwrap();
        item.enchant = Some(DoubleTap);
        let copy = item.id;
        c.enchanting.proficiency.initialize(299);
        for enchant in [Shieldbreaker, DoubleTap] {
            c.add_item(&enchant.item("scroll"), 1);
        }
        let applied = request(
            &mut w,
            &mut rx,
            json!({"op":"apply","enchant":Shieldbreaker,"copy":copy,"expected":DoubleTap}),
        );
        assert_eq!(applied["skill"], 300);
        assert_eq!(applied["skillUp"], true);
        let applied = request(
            &mut w,
            &mut rx,
            json!({"op":"apply","enchant":DoubleTap,"copy":copy,"expected":Shieldbreaker}),
        );
        assert_eq!(applied["skill"], 300);
        assert_eq!(applied["skillUp"], false);
    }

    #[test]
    fn enchanting_blue_procs_use_real_hits_absorption_healing_and_timers() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        worn(&mut w, 1, "weapon", "rare", DoubleTap);
        worn(&mut w, 1, "gloves", "rare", Quickhands);
        worn(&mut w, 1, "armor", "rare", Brace);
        worn(&mut w, 1, "necklace", "rare", SecondWind);
        worn(&mut w, 1, "cloak", "rare", Slipstream);
        enemies(&mut w, &[(270., 225.), (273., 225.)]);
        place(&mut w, 1, 0, at(270., 224.));
        w.enchant_rng = 0; // deterministic Double Tap, then Quickhands fails its roll
        assert_eq!(hit(&mut w, 0, 20., Hit::Basic), 20.);
        assert_eq!(w.slimes[0].hp, 170.);
        w.enchant_rng = 0;
        hit(&mut w, 0, 20., Hit::Basic);
        assert_eq!(w.slimes[0].hp, 150., "Double Tap has a shared timer");
        assert_eq!(w.players[&1].enchant_attack_speed(w.time), 0.15);
        assert_eq!(w.players[&1].enchant_attack_speed(w.time + 8.), 0.);

        let max = w.players[&1].character.max_hp();
        character(&mut w, 1).hp = max * 0.49;
        w.enchant_incoming(1, Some(0), max * 0.51, false, max * 0.02);
        assert!((w.players[&1].enchanting.barriers[0].remaining - max * 0.08).abs() < 1e-9);
        assert_eq!(
            w.players
                .get_mut(&1)
                .unwrap()
                .enchant_absorb(max * 0.05, w.time),
            0.
        );
        assert_eq!(
            w.players
                .get_mut(&1)
                .unwrap()
                .enchant_absorb(max * 0.05, w.time + 5.),
            max * 0.05
        );
        w.enchant_dodge(1, 0, at(270., 224.));
        assert_eq!(w.players[&1].enchant_move_speed(w.time), 0.20);

        let before = w.players[&1].character.hp;
        character(&mut w, 1).resource = Some(0.);
        let resource = w.players[&1].character.max_resource();
        hit(&mut w, 0, 180., Hit::Skill);
        assert!((w.players[&1].character.hp - before - max * 0.04).abs() < 1e-8);
        assert!((w.players[&1].character.resource() - resource * 0.05).abs() < 1e-8);
    }

    #[test]
    fn enchanting_epic_spells_rings_and_slow_track_actual_combat_state() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        worn(&mut w, 1, "weapon", "epic", Shieldbreaker);
        worn(&mut w, 1, "gloves", "epic", Spellweaver);
        worn(&mut w, 1, "pants", "epic", ShakeItOff);
        worn(&mut w, 1, "armor", "epic", ArcaneBulwark);
        worn(&mut w, 1, "accessory", "epic", PassingSpark);
        let c = character(&mut w, 1);
        let ring = c.equipment["accessory1"].clone();
        let first = c.worn_gear_instance(&ring, 0).unwrap().id;
        c.add_item(&ring, 1);
        c.materialize_gear_instances();
        let second = c.worn_gear_instance(&ring, 1).unwrap().id;
        c.gear_instances
            .iter_mut()
            .find(|g| g.id == second)
            .unwrap()
            .enchant = Some(PassingSpark);
        c.equip_slots(&[("accessory2".into(), ring.clone())].into())
            .unwrap();
        enemies(&mut w, &[(270., 225.), (272., 225.), (274., 225.)]);
        hit(&mut w, 0, 4., Hit::Basic);
        let mark = w.players[&1].enchanting.mark;
        assert!(matches!(mark, Some((0, _))));
        hit(&mut w, 1, 4., Hit::Basic);
        assert_eq!(
            w.players[&1].enchanting.mark, mark,
            "a second ring shares the mark cooldown"
        );
        let p = w.players.get_mut(&1).unwrap();
        p.character
            .equip_slots(&[("accessory1".into(), "none".into())].into())
            .unwrap();
        assert_eq!(p.character.worn_gear_instance(&ring, 0).unwrap().id, second);
        assert!(!p.character.gear_instance_equipped(first));
        p.character
            .equip_slots(&[("accessory1".into(), ring.clone())].into())
            .unwrap();
        assert_eq!(p.character.worn_gear_instance(&ring, 1).unwrap().id, second);
        w.cur_skill = "one".into();
        hit(&mut w, 1, 5., Hit::Skill);
        w.time = 3.;
        w.cur_skill = "two".into();
        hit(&mut w, 1, 5., Hit::Skill);
        w.cur_skill.clear();
        let before = w.slimes[1].hp;
        hit(&mut w, 1, 20., Hit::Basic);
        assert_eq!(before - w.slimes[1].hp, 32.);
        assert_eq!(w.players[&1].enchant_cast_modifiers(w.time), (true, false));
        assert_eq!(
            w.players[&1].enchant_cast_modifiers(w.time + 5.),
            (false, false)
        );
        w.slimes[1].hp = 10000.;
        w.slimes[1].max_hp = 10000.;
        let before = w.slimes[1].hp;
        hit(&mut w, 0, 400., Hit::Basic);
        let dealt = before - w.slimes[1].hp;
        assert!(
            (dealt - mark.unwrap().1 * 0.4).abs() < 1e-8,
            "spark dealt {dealt}, mark stored {mark:?}"
        );
        assert_eq!(w.players[&1].enchanting.mark.unwrap().0, 1);
        let max = w.players[&1].character.max_hp();
        let p = w.players.get_mut(&1).unwrap();
        p.character.hp = max * 0.39;
        p.daze = 4.;
        w.enchant_incoming(1, Some(1), max * 0.41, true, max * 0.02);
        assert_eq!(w.players[&1].daze, 2.);
        assert_eq!(w.players[&1].enchanting.barriers[0].remaining, max * 0.20);
        w.players.get_mut(&1).unwrap().daze = 0.;
        w.update_enchanting(1);
        assert_eq!(w.players[&1].enchant_move_speed(w.time), 0.25);
    }

    #[test]
    fn enchanting_guardian_thread_and_grove_protect_living_party_members_only() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Priest);
        let _rx2 = join(&mut w, 2, Class::Warrior);
        let _rx3 = join(&mut w, 3, Class::Warrior);
        worn(&mut w, 1, "necklace", "epic", GuardianThread);
        worn(&mut w, 1, "shoulders", "legendary", HeartwoodGrove);
        let home = at(270., 224.);
        for id in 1..=3 {
            place(&mut w, id, 0, home);
        }
        let leader = w.players[&1].character.id.clone();
        let mate = w.players[&2].character.id.clone();
        w.message(
            1,
            ClientMessage::Social {
                command: SocialCommand::PartyInvite {
                    id: Some(mate),
                    name: None,
                },
            },
        );
        w.message(
            2,
            ClientMessage::Social {
                command: SocialCommand::PartyAccept { id: leader },
            },
        );
        let max = w.players[&2].character.max_hp();
        let before = max * 0.39;
        character(&mut w, 2).hp = before;
        w.heal_players(1, &[3, 2], 0.1);
        assert_eq!(w.players[&2].enchanting.barriers[0].remaining, max * 0.10);
        assert!(w.players[&3].enchanting.barriers.is_empty());
        for id in 1..=3 {
            let c = character(&mut w, id);
            c.hp = c.max_hp() * 0.39;
        }
        let max1 = w.players[&1].character.max_hp();
        w.enchant_incoming(1, Some(0), max1 * 0.41, false, max1 * 0.02);
        assert_eq!(w.enchant_fields(0)[0]["enchant"], "heartwood_grove");
        for t in 1..=6 {
            w.time = t as f64;
            w.update_enchanting(1);
        }
        assert!((w.players[&1].character.hp / max1 - 0.51).abs() < 1e-8);
        assert!((w.players[&2].character.hp / max - 0.51).abs() < 1e-8);
        assert_eq!(
            w.players[&3].character.hp / w.players[&3].character.max_hp(),
            0.39
        );
        assert!(w.enchant_fields(0).is_empty());
    }

    #[test]
    fn enchanting_legendary_procs_distinguish_hit_count_skill_cast_los_and_decoy_targets() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        worn(&mut w, 1, "weapon", "legendary", LightningRod);
        worn(&mut w, 1, "headgear", "legendary", BorrowedTime);
        worn(&mut w, 1, "armor", "legendary", RiseFromAsh);
        worn(&mut w, 1, "cloak", "legendary", Moonstep);
        let home = at(270., 224.);
        place(&mut w, 1, 0, home);
        enemies(
            &mut w,
            &[
                (270., 225.),
                (271., 225.),
                (272., 225.),
                (273., 225.),
                (279., 225.),
            ],
        );
        for _ in 0..4 {
            hit(&mut w, 0, 2., Hit::Basic);
        }
        assert!(w.enchant_fields(0).is_empty());
        hit(&mut w, 0, 2., Hit::Basic);
        assert_eq!(w.enchant_fields(0)[0]["enchant"], "lightning_rod");
        hit(&mut w, 4, 1., Hit::Skill);
        assert_eq!(w.enchant_fields(0).len(), 1);
        for s in &mut w.slimes[..3] {
            s.hp = 10000.;
            s.max_hp = 10000.;
        }
        let before = w.slimes[1].hp;
        let damage = w.set_basic_damage(1);
        hit(&mut w, 0, 1., Hit::Skill);
        assert!(w.enchant_fields(0).is_empty());
        let dealt = before - w.slimes[1].hp;
        assert!(
            (dealt - damage * 0.45).abs() < 1e-8,
            "lightning dealt {dealt} from a {damage} reference hit"
        );
        assert_eq!(w.slimes[3].hp, 200.);
        let now = w.enchant_now();
        for skill in ["one", "one", "two", "three"] {
            w.players
                .get_mut(&1)
                .unwrap()
                .enchant_cast(skill, false, false, w.time, now);
        }
        assert_eq!(w.players[&1].enchant_cast_modifiers(w.time), (false, true));
        w.players
            .get_mut(&1)
            .unwrap()
            .enchant_cast("four", false, true, w.time, now);
        assert_eq!(w.players[&1].enchant_cast_modifiers(w.time), (false, false));
        assert_eq!(
            w.players[&1].character.enchanting.ready[&BorrowedTime],
            now + 35.
        );

        w.slimes[1].kind = "big".into();
        w.enchant_dodge(1, 0, home);
        assert!(w.slimes[0].enchant_decoy.is_some());
        assert!(w.slimes[1].enchant_decoy.is_none());
        assert!(w.enchant_decoy_update(0, &[]));
        w.time = 3.;
        assert!(!w.enchant_decoy_update(0, &[]));
        w.update_enchanting(1);
        assert_eq!(w.players[&1].enchant_move_speed(3.), 0.30);

        let max = w.players[&1].character.max_hp();
        character(&mut w, 1).hp = 0.;
        w.enchant_incoming(1, Some(0), max, false, max);
        assert_eq!(w.players[&1].character.hp, 1.);
        w.slimes[0].x = -1000.;
        w.slimes[0].y = -1000.;
        assert!(!w.maps[0].line_clear(home, w.slimes[0].point(), 0.05));
        w.update_enchanting(1);
        assert!((w.players[&1].character.hp - 1. - max * 0.20).abs() < 1e-8);
        let saved = serde_json::to_value(&w.players[&1].character).unwrap();
        let c: Character = serde_json::from_value(saved).unwrap();
        assert_eq!(c.enchanting.ready[&RiseFromAsh], w.enchant_now() + 300.);
        character(&mut w, 1).hp = 0.;
        w.enchant_incoming(1, Some(0), max, false, max);
        assert_eq!(w.players[&1].character.hp, 0.);
    }

    #[test]
    fn enchanting_cast_uses_the_discount_and_half_cooldown_only_on_success() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        worn(&mut w, 1, "gloves", "epic", Spellweaver);
        worn(&mut w, 1, "headgear", "legendary", BorrowedTime);
        enemies(&mut w, &[(270., 225.)]);
        let c = character(&mut w, 1);
        c.resource = Some(c.max_resource());
        for skill in ["twinbolt", "fireball", "barrage"] {
            w.use_skill(1, skill, at(1., 0.));
        }
        for n in 0..3 {
            w.time = n as f64;
            hit(&mut w, 0, 1., Hit::Basic);
        }
        let p = &w.players[&1];
        let ward = skills::find(Class::Mage, "arcaneward")
            .unwrap()
            .at_level(p.character.level);
        let normal_cd = ward.cooldown * p.character.cooldown_multiplier();
        character(&mut w, 1).resource = Some(0.);
        w.use_skill(1, "arcaneward", at(1., 0.));
        assert_eq!(w.players[&1].enchant_cast_modifiers(w.time), (true, true));
        character(&mut w, 1).resource = Some(ward.cost * 0.7 + 1.);
        w.use_skill(1, "arcaneward", at(1., 0.));
        let p = &w.players[&1];
        assert!((p.character.resource() - 1.).abs() < 1e-9);
        assert_eq!(p.skill_cd["arcaneward"], normal_cd * 0.5);
        assert_eq!(p.enchant_cast_modifiers(w.time), (false, false));
    }

    #[test]
    fn enchanting_monster_drops_do_not_enter_old_tiers_and_vendors_charge_catalog_prices() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        assert_eq!(catalog::drop_recipe(9, true, 0., 0.), None);
        assert_eq!(catalog::drop_recipe(10, false, 0., 0.), Some(DoubleTap));
        assert_eq!(catalog::drop_recipe(35, false, 0., 0.), Some(ArcaneBulwark));
        assert_eq!(catalog::drop_recipe(65, false, 0., 0.), Some(LightningRod));
        assert_eq!(catalog::drop_recipe(65, false, 0.024, 0.), None);
        assert!(catalog::drop_recipe(65, true, 0.024, 0.).is_some());
        for row in &CATALOG.enchants {
            assert!(item(&row.id.item("recipe")).is_some());
            assert!(item(&row.id.item("scroll")).is_some());
        }
        let (zone, npc) = w
            .maps
            .iter()
            .enumerate()
            .find_map(|(zone, map)| {
                map.npcs
                    .iter()
                    .find(|npc| npc.id == "city_enchanting")
                    .map(|npc| (zone, npc.clone()))
            })
            .unwrap();
        let at = npc.position_at(w.time);
        place(&mut w, 1, zone, at);
        let price = npc
            .offers
            .iter()
            .find(|o| o.item.as_ref() == Some(&DoubleTap.item("recipe")))
            .unwrap()
            .cost;
        character(&mut w, 1).gold = price - 1;
        let order = || ClientMessage::Interact {
            npc: npc.id.clone(),
            offer: Some(format!("buy_{}", DoubleTap.item("recipe"))),
        };
        w.message(1, order());
        assert_eq!(character(&mut w, 1).quantity(&DoubleTap.item("recipe")), 0);
        w.time += 1.;
        character(&mut w, 1).gold = price;
        w.message(1, order());
        assert_eq!(character(&mut w, 1).gold, 0);
        assert_eq!(character(&mut w, 1).quantity(&DoubleTap.item("recipe")), 1);
        assert!(
            drain(&mut rx)
                .iter()
                .any(|event| event["type"] == "dialogue")
        );
    }

    #[test]
    fn enchanting_eligible_monster_drops_a_recipe_through_the_normal_loot_path() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        place(&mut w, 1, 0, at(270., 224.));
        enemies(&mut w, &[(270., 225.)]);
        w.slimes[0].level = 65;
        w.enchant_rng = 0;
        hit(&mut w, 0, 1000., Hit::Basic);
        let id = &w.players[&1].character.id;
        assert!(w.drops.iter().any(|drop| {
            drop.owner == *id
                && drop
                    .item
                    .as_deref()
                    .is_some_and(|item| item.starts_with("enchant_recipe_"))
        }));
    }

    #[test]
    fn enchanting_never_runs_pve_procs_while_flagged_or_from_secondary_damage() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        worn(&mut w, 1, "weapon", "rare", DoubleTap);
        worn(&mut w, 1, "necklace", "rare", SecondWind);
        enemies(&mut w, &[(270., 225.), (272., 225.)]);
        w.enchant_rng = 0;
        w.players.get_mut(&1).unwrap().pvp_flag = true;
        hit(&mut w, 0, 20., Hit::Basic);
        assert_eq!(w.slimes[0].hp, 180.);
        assert!(w.players[&1].character.enchanting.ready.is_empty());
        w.players.get_mut(&1).unwrap().pvp_flag = false;
        w.enchant_damage(1, 0, 10000., LightningRod);
        assert!(w.slimes[0].dead);
        assert!(
            !w.players[&1]
                .character
                .enchanting
                .ready
                .contains_key(&SecondWind)
        );
    }
}
