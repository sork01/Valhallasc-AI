//! Mining channels and workshop transactions resolve on the world thread.
use super::*;
use crate::blacksmithing::{
    CANDIDATES, CATALOG, Command, Method, STARTER_PICK, TRAINER, WORKSHOP, training_cap,
};

const REACH: f64 = 2.6;
const DURATION: f64 = 1.8;

#[derive(Clone, Copy, Serialize)]
pub(super) struct Vein {
    id: u64,
    #[serde(flatten)]
    point: Point,
    tier: usize,
    #[serde(skip)]
    pulls: u8,
}

#[derive(Clone, Copy)]
pub(super) struct Mining {
    pub(super) vein: u64,
    zone: usize,
    origin: Point,
    hp: f64,
    until: f64,
}

fn skill_for(tier: usize) -> u16 {
    if tier == 0 { 1 } else { training_cap(tier - 1) }
}

pub(super) fn workshop_view(npc: &Npc, c: &Character) -> Option<Value> {
    npc.offers
        .iter()
        .any(|offer| offer.id == WORKSHOP)
        .then(|| {
            json!({"skill":c.blacksmithing.proficiency.skill,"recipes":c.blacksmithing.recipes,
            "trainer":c.zone == 0 && npc.id == TRAINER})
        })
}

fn workshop_action(
    c: &mut Character,
    request: &Command,
    roll: f64,
) -> Result<(&'static str, Option<String>), &'static str> {
    let progress = &c.blacksmithing;
    let skill = progress.proficiency.skill;
    if let Command::Train { .. } = request {
        if skill > 0 {
            return Err("You already know Blacksmithing.");
        }
        if !c.can_collect(STARTER_PICK) {
            return Err("Your bags are full. Make room first.");
        }
        c.blacksmithing.proficiency.initialize(1);
        c.add_item(STARTER_PICK, 1);
        return Ok((
            "You learned Blacksmithing and received a starter pick.",
            None,
        ));
    }
    if skill == 0 {
        return Err("Learn Blacksmithing from Bram Emberforge in Alderhaven.");
    }
    let recipe = match request {
        Command::Study { plan } => CATALOG.plan(plan),
        Command::Learn { recipe, .. } | Command::Craft { recipe, .. } => CATALOG.recipe(recipe),
        Command::Train { .. } => unreachable!(),
    }
    .ok_or("That Blacksmithing recipe is unavailable.")?;

    match request {
        Command::Learn { .. } => {
            if recipe.method != Method::Staple {
                return Err("This blueprint must be found as loot.");
            }
            if skill < recipe.skill {
                return Err("Your Blacksmithing skill is too low.");
            }
            if !c.blacksmithing.recipes.insert(recipe.item.clone()) {
                return Err("You already know this blueprint.");
            }
            Ok(("You learned the blueprint.", None))
        }
        Command::Study { plan } => {
            if progress.recipes.contains(&recipe.item) {
                return Err("You already know this blueprint.");
            }
            if !c.consume_item(plan, 1) {
                return Err("That blueprint is missing from your bags.");
            }
            c.blacksmithing.recipes.insert(recipe.item.clone());
            Ok(("You learned the blueprint.", None))
        }
        Command::Craft { .. } => {
            if skill < recipe.skill {
                return Err("Your Blacksmithing skill is too low.");
            }
            let gear = matches!(recipe.method, Method::Staple | Method::Rare | Method::Epic);
            if gear && !progress.recipes.contains(&recipe.item) {
                return Err("Learn this blueprint before forging it.");
            }
            if c.gold < recipe.cost {
                return Err("You cannot afford that recipe.");
            }
            for (item, count) in &recipe.ingredients {
                if !c.consume_item(item, *count) {
                    return Err("You do not have the ingredients for that recipe.");
                }
            }
            if !c.can_collect(&recipe.item) || c.quantity(&recipe.item) == u32::MAX {
                return Err("Your bags are full. Make room first.");
            }
            c.gold -= recipe.cost;
            c.add_item(&recipe.item, 1);
            if gear {
                c.materialize_gear_instances();
                let quality = match recipe.method {
                    Method::Epic => 2,
                    Method::Rare => 1,
                    _ => 0,
                };
                c.blacksmithing
                    .proficiency
                    .try_gain(quality, training_cap(recipe.tier), roll);
            }
            let message = match recipe.method {
                Method::Smelt => "You smelted a bar.",
                Method::Upgrade => "You forged a new mining pick.",
                _ => "You forged equipment.",
            };
            Ok((message, Some(recipe.item.clone())))
        }
        Command::Train { .. } => unreachable!(),
    }
}

impl World {
    fn smith_available(&self, p: &Player) -> bool {
        p.is_human()
            && p.can_dance()
            && !p.character.mounted
            && self.time >= p.cutscene_until
            && self.trade_index(&p.character.id).is_none()
            && !self.pvp_busy(&p.character.id)
    }

    pub(super) fn blacksmithing_command(&mut self, session: u64, request: Command) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let npc = match &request {
            Command::Train { npc } | Command::Learn { npc, .. } | Command::Craft { npc, .. } => {
                Some(npc.clone())
            }
            Command::Study { .. } => None,
        };
        let result = if !self.smith_available(p) {
            Err("You can use Blacksmithing while alive, dismounted and out of combat or travel.")
        } else if npc.as_ref().is_some_and(|id| {
            let c = &p.character;
            let map = &self.maps[c.zone];
            !map.npcs.iter().any(|n| {
                n.id == *id
                    && c.point().distance(n.position_at(self.time)) <= 2.8
                    && n.offers.iter().any(|offer| offer.id == WORKSHOP)
                    && (!matches!(request, Command::Train { .. }) || c.zone == 0 && n.id == TRAINER)
            })
        }) {
            Err("Walk closer to the smith to use this workshop.")
        } else {
            let mut staged = p.character.clone();
            workshop_action(&mut staged, &request, self.smith_roll()).and_then(|action| {
                self.store
                    .save_many([&staged].into_iter())
                    .map_err(|_| "The Blacksmithing change could not be saved.")?;
                self.players.get_mut(&session).unwrap().character = staged;
                Ok(action)
            })
        };
        let p = &self.players[&session];
        let c = &p.character;
        let (text, output) = result
            .as_ref()
            .map(|(text, output)| (*text, output.as_deref()))
            .unwrap_or_else(|text| (*text, None));
        let _ = p.peer.try_send(
            json!({"type":"blacksmithing","npc":npc,"ok":result.is_ok(),"text":text,
            "skill":c.blacksmithing.proficiency.skill,"recipes":c.blacksmithing.recipes,
            "gold":c.gold,"inventory":c.inventory,"output":output}),
        );
    }

    pub(super) fn ensure_veins(&mut self, zone: usize) {
        let Some(points) = CANDIDATES.get(&zone) else {
            return;
        };
        if self.mining_veins.contains_key(&zone) || self.is_instance(zone) {
            return;
        }
        self.mining_veins.insert(zone, vec![]);
        for _ in 0..3.min(points.len().saturating_sub(1)) {
            self.spawn_vein(zone, None);
        }
    }

    fn spawn_vein(&mut self, zone: usize, old: Option<Point>) {
        let Some(tier) = CATALOG.tier(zone) else {
            return;
        };
        let choices: Vec<_> = CANDIDATES[&zone]
            .iter()
            .copied()
            .filter(|point| {
                old != Some(*point)
                    && self.mining_veins[&zone]
                        .iter()
                        .all(|vein| vein.point != *point)
            })
            .collect();
        if choices.is_empty() {
            return;
        }
        let point = choices[(self.smith_roll() * choices.len() as f64) as usize];
        let id = self.entity();
        let pulls = 3 + (self.smith_roll() * 3.) as u8;
        self.mining_veins.get_mut(&zone).unwrap().push(Vein {
            id,
            point,
            tier,
            pulls,
        });
    }

    fn mine_target(&self, p: &Player, vein_id: u64) -> Result<Vein, &'static str> {
        if !self.smith_available(p) || p.fishing.line.is_some() {
            return Err("You need to be free to move before mining.");
        }
        let c = &p.character;
        let vein = self
            .mining_veins
            .get(&c.zone)
            .and_then(|veins| veins.iter().find(|v| v.id == vein_id))
            .copied()
            .ok_or("That vein has moved.")?;
        if c.point().distance(vein.point) > REACH
            || !self.maps[c.zone].line_clear(c.point(), vein.point, 0.05)
        {
            return Err("Move closer to the ore vein.");
        }
        if c.blacksmithing.proficiency.skill < skill_for(vein.tier) {
            return Err("Your Blacksmithing skill is too low.");
        }
        if !CATALOG
            .picks
            .iter()
            .any(|pick| pick.reaches >= vein.tier && c.quantity(&pick.item) > 0)
        {
            return Err("You need a stronger mining pick in your bags.");
        }
        Ok(vein)
    }

    fn mining_notice(p: &Player, state: &str, text: &'static str) {
        let _ = p
            .peer
            .try_send(json!({"type":"mining","state":state,"text":text}));
    }

    pub(super) fn start_mining(&mut self, session: u64, id: u64) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        if p.mining.is_some() {
            return;
        }
        let vein = match self.mine_target(p, id) {
            Ok(vein) => vein,
            Err(text) => return Self::mining_notice(p, "error", text),
        };
        let p = self.players.get_mut(&session).unwrap();
        p.stop();
        p.dance = None;
        let origin = p.character.point();
        p.face = normalize(vein.point.x - origin.x, vein.point.y - origin.y);
        p.mining = Some(Mining {
            vein: id,
            zone: p.character.zone,
            origin,
            hp: p.character.hp,
            until: self.time + DURATION,
        });
        let _ = p
            .peer
            .try_send(json!({"type":"mining","state":"started","vein":id,"duration":DURATION}));
    }

    pub(super) fn interrupt_mining(p: &mut Player) {
        if p.mining.take().is_some() {
            Self::mining_notice(p, "error", "Mining interrupted.");
        }
    }

    pub(super) fn update_mining(&mut self, session: u64) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let Some(channel) = p.mining else { return };
        if p.character.zone != channel.zone
            || p.character.point() != channel.origin
            || p.character.hp < channel.hp
        {
            return Self::interrupt_mining(self.players.get_mut(&session).unwrap());
        }
        let vein = match self.mine_target(p, channel.vein) {
            Ok(vein) => vein,
            Err(text) => {
                let p = self.players.get_mut(&session).unwrap();
                p.mining = None;
                return Self::mining_notice(p, "error", text);
            }
        };
        if self.time < channel.until {
            return;
        }
        let mut staged = p.character.clone();
        let previous = staged.blacksmithing.proficiency.skill;
        let ore = &CATALOG.tiers[vein.tier].ore;
        let p = self.players.get_mut(&session).unwrap();
        p.mining = None;
        if !staged.can_collect(ore) {
            return Self::mining_notice(p, "error", "Your bags are full. Make room first.");
        }
        let quantity = 1 + (self.smith_roll() * 2.) as u32;
        if staged.quantity(ore).checked_add(quantity).is_none() {
            return Self::mining_notice(
                &self.players[&session],
                "error",
                "Your bags are full. Make room first.",
            );
        }
        staged.add_item(ore, quantity);
        staged
            .blacksmithing
            .proficiency
            .try_gain(0, training_cap(vein.tier), self.smith_roll());
        let p = self.players.get_mut(&session).unwrap();
        if self.store.save_many([&staged].into_iter()).is_err() {
            return Self::mining_notice(p, "error", "The Blacksmithing change could not be saved.");
        }
        p.character = staged;
        let _ = p.peer.try_send(json!({"type":"mining","state":"done","vein":vein.id,"item":ore,"quantity":quantity,
            "skill":p.character.blacksmithing.proficiency.skill,"skillUp":p.character.blacksmithing.proficiency.skill > previous}));
        let veins = self.mining_veins.get_mut(&channel.zone).unwrap();
        let index = veins.iter().position(|v| v.id == vein.id).unwrap();
        veins[index].pulls -= 1;
        if veins[index].pulls == 0 {
            veins.remove(index);
            self.spawn_vein(channel.zone, Some(vein.point));
        }
    }

    pub(super) fn smith_blueprint_drop(
        &mut self,
        owner: &str,
        zone: usize,
        at: Point,
        kind: &str,
        level: u32,
    ) {
        let map = &self.maps[zone];
        let final_boss = map.final_boss == kind;
        if CATALOG.tier(zone).is_none() && !final_boss {
            return;
        }
        let rolls = (self.smith_roll(), self.smith_roll());
        if let Some(plan) = CATALOG.drop_plan(zone, &self.maps[zone], kind, level, rolls) {
            self.loot_drop(owner, zone, at, plan);
        }
    }
}

#[cfg(test)]
#[path = "blacksmithing_tests.rs"]
mod tests;
