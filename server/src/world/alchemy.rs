//! Authoritative flower gathering, workshop transactions and PvE brews.
use super::*;
use crate::alchemy::{
    ActiveBrew, CATALOG, Command, PATCHES, POTION_COOLDOWN, Stat, TRAINER, WORKSHOP,
};
use crate::profession::{SKILL_BAND, gathering_requirement};

const REACH: f64 = 2.6;
const PICK_TIME: f64 = 1.5;

#[derive(Clone, Copy, Serialize)]
pub(super) struct FlowerPatch {
    id: u64,
    #[serde(flatten)]
    point: Point,
    flower: usize,
    #[serde(skip)]
    pool: usize,
    #[serde(skip)]
    picks: u8,
}

#[derive(Clone, Copy)]
pub(super) struct Picking {
    patch: u64,
    zone: usize,
    origin: Point,
    hp: f64,
    until: f64,
}

pub(super) fn workshop_view(npc: &Npc, c: &Character) -> Option<Value> {
    npc.offers
        .iter()
        .any(|offer| offer.id == WORKSHOP)
        .then(|| {
            json!({"skill":c.alchemy.proficiency.skill,"recipes":c.alchemy.recipes,
            "trainer":c.zone == 0 && npc.id == TRAINER})
        })
}

fn workshop_action(
    c: &mut Character,
    request: &Command,
    roll: impl FnMut() -> f64,
) -> Result<(String, Option<String>), &'static str> {
    let skill = c.alchemy.proficiency.skill;
    if let Command::Train { .. } = request {
        if skill > 0 {
            return Err("You already know Alchemy.");
        }
        c.alchemy.proficiency.initialize(1);
        return Ok(("You learned Alchemy.".into(), None));
    }
    if skill == 0 {
        return Err("Learn Alchemy from Maera in Alderhaven.");
    }

    let recipe = match request {
        Command::Learn { recipe, .. } | Command::Brew { recipe, .. } => CATALOG.recipe(recipe),
        Command::Study { formula } => CATALOG.formula(formula),
        Command::Train { .. } => unreachable!(),
    }
    .ok_or("That Alchemy recipe is unavailable.")?;
    let known = c.alchemy.recipes.contains(&recipe.item);

    match request {
        Command::Learn { .. } => {
            if recipe.formula.is_some() {
                return Err("Find a formula to learn this recipe.");
            }
            if skill < recipe.skill {
                return Err("Your Alchemy skill is too low.");
            }
        }
        Command::Study { formula } => {
            if known {
                return Err("You already know this recipe.");
            }
            if !c.consume_item(formula, 1) {
                return Err("That formula is missing from your bags.");
            }
        }
        Command::Brew { all, .. } => {
            if skill < recipe.skill {
                return Err("Your Alchemy skill is too low.");
            }
            if !known {
                return Err("Learn this recipe before brewing it.");
            }
            let costs = recipe
                .ingredients
                .iter()
                .map(|(ids, count)| (ids.iter().map(String::as_str), *count));
            let count = c.produce_recipe(
                &recipe.item,
                0,
                *all,
                costs,
                "You do not have the ingredients for that recipe.",
            )?;
            let cap = (recipe.skill / SKILL_BAND + 1) * SKILL_BAND;
            c.alchemy.proficiency.train_batch(
                count, 0, cap, crate::alchemy::MAX_SKILL, crate::alchemy::MAX_SKILL, roll,
            );
            let message = if *all {
                format!("Brewed {} Alchemy items.", count)
            } else {
                "You brewed an Alchemy item.".into()
            };
            return Ok((message, Some(recipe.item.clone())));
        }
        Command::Train { .. } => unreachable!(),
    }
    if !c.alchemy.recipes.insert(recipe.item.clone()) {
        return Err("You already know this recipe.");
    }
    Ok(("You learned the recipe.".into(), None))
}

impl Player {
    fn active_alchemy(
        &self,
        now: u64,
    ) -> impl Iterator<Item = (&'static crate::alchemy::Recipe, u64)> {
        let enabled = !self.alchemy_suppressed && self.character.hp > 0.;
        self.character
            .alchemy
            .flask
            .iter()
            .chain(self.alchemy_potion.iter())
            .filter(move |_| enabled)
            .filter_map(move |brew| brew.active(now))
    }

    pub(super) fn alchemy_modifier(&self, stat: Stat) -> f64 {
        if self.alchemy_potion.is_none() && self.character.alchemy.flask.is_none() {
            return 0.;
        }
        self.active_alchemy(unix_now())
            .map(|(recipe, _)| recipe.modifier(stat))
            .fold(0., f64::max)
    }

    pub(super) fn alchemy_buffs(&self) -> Vec<Value> {
        if self.alchemy_potion.is_none() && self.character.alchemy.flask.is_none() {
            return Vec::new();
        }
        self.active_alchemy(unix_now()).map(|(recipe, left)| {
            json!({"id":recipe.item,"kind":"alchemy","left":left,"time":recipe.duration()})
        }).collect()
    }

    pub(super) fn suppress_alchemy(&mut self, suppress: bool) {
        self.alchemy_suppressed = suppress;
        let health = self.alchemy_modifier(Stat::Health);
        if self.character.alchemy_health != health {
            self.character.alchemy_health = health;
            self.character.hp = self.character.hp.min(self.character.max_hp());
        }
    }
}

impl World {
    pub(super) fn alchemy_pvp(&self, p: &Player) -> bool {
        p.pvp_flag
            || p.pvp_fight > 0.
            || self.is_arena_zone(p.character.zone)
            || self.in_duel(&p.character.id)
    }

    pub(super) fn refresh_alchemy(&mut self, session: u64) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        if p.alchemy_potion.is_none() && p.character.alchemy.flask.is_none() {
            return;
        }
        let suppress = self.alchemy_pvp(p);
        let now = unix_now();
        let p = self.players.get_mut(&session).unwrap();
        if p.character.hp <= 0. || p.alchemy_potion.as_ref().is_some_and(|b| b.until <= now) {
            p.alchemy_potion = None;
        }
        if p.character
            .alchemy
            .flask
            .as_ref()
            .is_some_and(|b| b.until <= now)
        {
            p.character.alchemy.flask = None;
        }
        p.suppress_alchemy(suppress);
    }

    pub(super) fn alchemy_command(&mut self, session: u64, request: Command) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let npc = match &request {
            Command::Train { npc } | Command::Learn { npc, .. } | Command::Brew { npc, .. } => {
                Some(npc.as_str())
            }
            Command::Study { .. } => None,
        };
        let c = &p.character;
        let result = if !p.is_human()
            || !p.can_dance()
            || c.mounted
            || self.time < p.cutscene_until
            || self.trade_index(&c.id).is_some()
            || self.alchemy_pvp(p)
        {
            Err("Use Alchemy while alive, dismounted and out of combat.")
        } else if npc.is_some_and(|id| {
            !self.maps[c.zone].npcs.iter().any(|n| {
                n.id == id
                    && c.point().distance(n.position_at(self.time)) <= 2.8
                    && n.offers.iter().any(|offer| offer.id == WORKSHOP)
                    && (!matches!(request, Command::Train { .. }) || c.zone == 0 && n.id == TRAINER)
            })
        }) {
            Err("Walk closer to the alchemist to use this workshop.")
        } else {
            let mut staged = c.clone();
            workshop_action(&mut staged, &request, || self.alchemy_roll()).and_then(|action| {
                self.store
                    .save_many([&staged].into_iter())
                    .map_err(|_| "The Alchemy change could not be saved.")?;
                self.players.get_mut(&session).unwrap().character = staged;
                Ok(action)
            })
        };
        let p = &self.players[&session];
        let c = &p.character;
        let (text, output) = match &result {
            Ok((text, output)) => (text.as_str(), output.as_deref()),
            Err(text) => (*text, None),
        };
        let _ = p.peer.try_send(
            json!({"type":"alchemy","npc":npc,"ok":result.is_ok(),"text":text,
            "skill":c.alchemy.proficiency.skill,"recipes":c.alchemy.recipes,
            "inventory":c.inventory,"output":output}),
        );
    }

    pub(super) fn use_brew(&mut self, session: u64, recipe: &'static crate::alchemy::Recipe) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let c = &p.character;
        let error = if !p.is_human()
            || c.hp <= 0.
            || c.spark_travel.is_some()
            || self.time < p.cutscene_until
            || self.trade_index(&c.id).is_some()
        {
            Some("You cannot use that brew right now.".to_string())
        } else if self.alchemy_pvp(p) {
            Some("Alchemy brews are only available in PvE.".to_string())
        } else if c.level < recipe.level {
            let name = item(&recipe.item).map_or(recipe.item.as_str(), |it| it.name.as_str());
            Some(format!("{} needs level {}.", name, recipe.level))
        } else if c.quantity(&recipe.item) == 0 {
            Some("You do not have that item.".to_string())
        } else if recipe.flask && p.combat_left > 0. {
            Some("You can only drink a flask out of combat.".to_string())
        } else if !recipe.flask && p.potion_cd > 0. {
            Some(format!(
                "Potions are still recovering: {} s left.",
                p.potion_cd.round().max(1.)
            ))
        } else {
            None
        };
        if let Some(text) = error {
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
            return;
        }

        let now = unix_now();
        let active = ActiveBrew {
            item: recipe.item.clone(),
            until: now + recipe.duration(),
        };
        let mut staged = c.clone();
        staged.consume_item(&recipe.item, 1);
        if recipe.flask {
            staged.alchemy.flask = Some(active.clone());
            staged.alchemy_health = recipe.modifier(Stat::Health);
            staged.hp = staged.hp.min(staged.max_hp());
        } else {
            staged.potion_ready = now + POTION_COOLDOWN;
        }
        if self.store.save_many([&staged].into_iter()).is_err() {
            let _ = p
                .peer
                .try_send(json!({"type":"error","text":"The Alchemy change could not be saved."}));
            return;
        }
        let p = self.players.get_mut(&session).unwrap();
        p.character = staged;
        p.alchemy_suppressed = false;
        if !recipe.flask {
            p.alchemy_potion = Some(active);
            p.potion_cd = POTION_COOLDOWN as f64;
        }
        let (id, point) = (p.character.id.clone(), p.character.point());
        self.event_with(
            "consume",
            &id,
            point,
            0.,
            false,
            json!({"item":recipe.item,"alchemy":true}),
        );
    }

    pub(super) fn ensure_flowers(&mut self, zone: usize) {
        let Some(pools) = PATCHES.get(&zone) else {
            return;
        };
        if self.flower_patches.contains_key(&zone)
            || self.is_instance(zone)
            || self.is_arena_zone(zone)
        {
            return;
        }
        self.flower_patches.insert(zone, Vec::new());
        for (pool, spec) in pools.iter().enumerate() {
            for _ in 0..spec.active {
                self.spawn_flower(zone, pool, None);
            }
        }
    }

    fn spawn_flower(&mut self, zone: usize, pool: usize, old: Option<Point>) {
        let spec = &PATCHES[&zone][pool];
        let choices: Vec<_> = spec
            .points
            .iter()
            .copied()
            .filter(|point| {
                old != Some(*point)
                    && self.flower_patches[&zone]
                        .iter()
                        .all(|patch| patch.point != *point)
            })
            .collect();
        if choices.is_empty() {
            return;
        }
        let point = choices[(self.alchemy_roll() * choices.len() as f64) as usize];
        let id = self.entity();
        let picks = 3 + (self.alchemy_roll() * 3.) as u8;
        self.flower_patches
            .get_mut(&zone)
            .unwrap()
            .push(FlowerPatch {
                id,
                point,
                flower: spec.flower,
                pool,
                picks,
            });
    }

    fn flower_target(&self, p: &Player, id: u64) -> Result<FlowerPatch, &'static str> {
        let c = &p.character;
        if !p.is_human()
            || c.hp <= 0.
            || c.mounted
            || c.spark_travel.is_some()
            || p.frozen
            || p.dash > 0.
            || p.stun > 0.
            || p.root > 0.
            || self.time < p.cutscene_until
            || self.alchemy_pvp(p)
            || p.fishing.line.is_some()
            || p.mining.is_some()
            || self.trade_index(&c.id).is_some()
        {
            return Err("You need to be free to move before picking flowers.");
        }
        let patch = self
            .flower_patches
            .get(&c.zone)
            .and_then(|patches| patches.iter().find(|patch| patch.id == id))
            .copied()
            .ok_or("That flower patch has moved.")?;
        if c.point().distance(patch.point) > REACH
            || !self.maps[c.zone].line_clear(c.point(), patch.point, 0.05)
        {
            return Err("Move closer to the flower patch.");
        }
        if c.alchemy.proficiency.skill < gathering_requirement(CATALOG.flowers[patch.flower].band) {
            return Err("Your Alchemy skill is too low.");
        }
        Ok(patch)
    }

    fn picking_notice(p: &Player, text: &'static str) {
        let _ = p
            .peer
            .try_send(json!({"type":"picking","state":"error","text":text}));
    }

    pub(super) fn start_picking(&mut self, session: u64, id: u64) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        if p.picking.is_some() {
            return;
        }
        let patch = match self.flower_target(p, id) {
            Ok(patch) => patch,
            Err(text) => return Self::picking_notice(p, text),
        };
        let hour = self.world_clock.hour_at(daynight::unix_ms());
        let duration = if p.character.look.race == Race::Mothkin && !(5. ..20.).contains(&hour) {
            PICK_TIME / 1.15
        } else {
            PICK_TIME
        };
        let p = self.players.get_mut(&session).unwrap();
        p.stop();
        p.dance = None;
        let origin = p.character.point();
        if origin != patch.point {
            p.face = origin.direction(patch.point);
        }
        p.picking = Some(Picking {
            patch: id,
            zone: p.character.zone,
            origin,
            hp: p.character.hp,
            until: self.time + duration,
        });
        let _ = p
            .peer
            .try_send(json!({"type":"picking","state":"started","patch":id,"duration":duration}));
    }

    pub(super) fn interrupt_picking(p: &mut Player) {
        if p.picking.take().is_some() {
            Self::picking_notice(p, "Picking interrupted.");
        }
    }

    pub(super) fn update_picking(&mut self, session: u64) {
        let p = &self.players[&session];
        let Some(channel) = p.picking else { return };
        if p.character.zone != channel.zone
            || p.character.point() != channel.origin
            || p.character.hp < channel.hp
        {
            return Self::interrupt_picking(self.players.get_mut(&session).unwrap());
        }
        let patch = match self.flower_target(p, channel.patch) {
            Ok(patch) => patch,
            Err(text) => {
                let p = self.players.get_mut(&session).unwrap();
                p.picking = None;
                return Self::picking_notice(p, text);
            }
        };
        if self.time < channel.until {
            return;
        }
        let mut staged = p.character.clone();
        let flower = &CATALOG.flowers[patch.flower];
        let previous = staged.alchemy.proficiency.skill;
        let count = 1 + (self.alchemy_roll() * 2.) as u32;
        let roll = self.alchemy_roll();
        let p = self.players.get_mut(&session).unwrap();
        p.picking = None;
        if !staged.can_collect(&flower.item)
            || staged.quantity(&flower.item).checked_add(count).is_none()
        {
            return Self::picking_notice(p, "Your bags are full. Make room first.");
        }
        staged.add_item(&flower.item, count);
        staged.alchemy.train_gathering(flower.band, roll);
        if self.store.save_many([&staged].into_iter()).is_err() {
            return Self::picking_notice(p, "The Alchemy change could not be saved.");
        }
        p.character = staged;
        let skill = p.character.alchemy.proficiency.skill;
        let _ = p
            .peer
            .try_send(json!({"type":"picking","state":"done","patch":patch.id,
            "item":flower.item,"quantity":count,"skill":skill,"skillUp":skill > previous}));
        let patches = self.flower_patches.get_mut(&channel.zone).unwrap();
        let index = patches
            .iter()
            .position(|other| other.id == patch.id)
            .unwrap();
        patches[index].picks -= 1;
        if patches[index].picks == 0 {
            patches.swap_remove(index);
            self.spawn_flower(channel.zone, patch.pool, Some(patch.point));
        }
    }

    pub(super) fn alchemy_formula_drop(
        &mut self,
        owner: &str,
        zone: usize,
        at: Point,
        kind: &str,
        level: u32,
    ) {
        let boss = &self.maps[zone].final_boss == kind && level == 99;
        let trailwind = zone == 27 && crate::items::is_elite(kind);
        if !boss && !trailwind {
            return;
        }
        let recipe = CATALOG.recipes.iter().find(|recipe| {
            if trailwind {
                recipe.formula.is_some() && recipe.boss.is_none()
            } else {
                recipe.boss.as_deref() == Some(kind)
            }
        });
        if let Some(formula) = recipe.and_then(|recipe| recipe.formula.as_deref()) {
            let chance = if trailwind { 0.05 } else { 0.20 };
            if self.alchemy_roll() < chance {
                self.loot_drop(owner, zone, at, formula);
            }
        }
    }
}

#[cfg(test)]
#[path = "alchemy_tests.rs"]
mod tests;
