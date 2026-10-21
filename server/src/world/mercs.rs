//! Mercenaries. The giver of a group quest (a quest with `group` and `recommendedPlayers`, today the Cinderlord and
//! Gloomroot elites) rents fighters for `merc_price(hirer level)` gold each, up to the number of players the quest wants. A mercenary is
//! an ordinary `Player` (so enemies fight it, a priest's mends reach it, it shows in the party and on every client)
//! whose input is decided here instead of by a socket: it joins its hirer's party, follows them, helps whatever they or
//! their party are fighting, uses its class's skills sensibly, drinks a potion when hurt, and is never saved.
//! Whatever a mercenary earns belongs to its hirer (see `World::credit_session`).
//! It leaves when its hired objective is ready, its instance is cleared, its hirer logs out/leaves the party, or it is sent away.
use super::*;

/// (hirer level, gold for one mercenary): about five of that level's ordinary kills' gold (median `base_gold` of the
/// enemies whose default level falls in the decade, 2026-10-21), smoothed so it never falls, and 250 at level 1 as before.
/// Four fighters for one run therefore cost a real share of what the level earns, up to ~450,000 at level 99.
const MERC_PRICE_ANCHORS: [(u32, u32); 11] = [
    (1, 250),
    (10, 400),
    (20, 1_200),
    (30, 2_500),
    (40, 5_000),
    (50, 15_000),
    (60, 28_000),
    (70, 38_000),
    (80, 55_000),
    (90, 90_000),
    (99, 115_000),
];

/// Gold for one mercenary at the hirer's level, whatever its class (linear between the anchors, to the nearest 50).
/// The dialogue, the gold check and the payment all use this one function.
pub fn merc_price(level: u32) -> u32 {
    let level = level.clamp(1, 99);
    let at = MERC_PRICE_ANCHORS
        .iter()
        .position(|&(l, _)| l >= level)
        .unwrap_or(MERC_PRICE_ANCHORS.len() - 1);
    let (hi_l, hi_g) = MERC_PRICE_ANCHORS[at];
    if at == 0 || hi_l == level {
        return hi_g;
    }
    let (lo_l, lo_g) = MERC_PRICE_ANCHORS[at - 1];
    let t = f64::from(level - lo_l) / f64::from(hi_l - lo_l);
    let gold = f64::from(lo_g) + t * (f64::from(hi_g) - f64::from(lo_g));
    (gold / 50.).round() as u32 * 50
}
/// Mercenary sessions live far above every socket's counter, so the two can never collide.
pub(super) const MERC_BASE: u64 = 1 << 62;
/// A mercenary farther than this from its hirer (or in another zone) is carried to their side.
const MERC_LEASH: f64 = 26.;
/// Enemies attacking the party this close are fought without waiting for the hirer to pick a target.
const MERC_SIGHT: f64 = 14.;

pub(super) fn class_named(name: &str) -> Option<Class> {
    Some(match name {
        "warrior" => Class::Warrior,
        "mage" => Class::Mage,
        "assassin" => Class::Assassin,
        "priest" => Class::Priest,
        "hunter" => Class::Hunter,
        _ => return None,
    })
}
fn class_title(class: Class) -> &'static str {
    match class {
        Class::Warrior => "Warrior",
        Class::Mage => "Mage",
        Class::Assassin => "Assassin",
        Class::Priest => "Priest",
        Class::Hunter => "Hunter",
    }
}

impl World {
    pub(super) fn is_merc(&self, session: u64) -> bool {
        self.players.get(&session).is_some_and(|p| p.merc.is_some())
    }
    /// Players who are really connected.
    pub(super) fn humans_online(&self) -> usize {
        self.players
            .values()
            .filter(|p| p.merc.is_none() && p.ambient.is_none())
            .count()
    }
    pub(super) fn visible_humans_online(&self) -> usize {
        self.players
            .values()
            .filter(|p| p.merc.is_none() && p.ambient.is_none() && !p.is_hidden())
            .count()
    }
    pub(super) fn session_of(&self, character: &str) -> Option<u64> {
        self.players
            .iter()
            .find(|(_, p)| p.merc.is_none() && p.ambient.is_none() && p.character.id == character)
            .map(|(session, _)| *session)
    }
    /// Whose rewards a kill by `session` pays: the hirer's when it is a mercenary's.
    pub(super) fn credit_session(&self, session: u64) -> u64 {
        self.players
            .get(&session)
            .and_then(|p| p.merc.as_deref())
            .and_then(|owner| self.session_of(owner))
            .unwrap_or(session)
    }
    fn mercenaries_of(&self, owner: &str) -> Vec<u64> {
        self.players
            .iter()
            .filter(|(_, p)| p.merc.as_deref() == Some(owner) && p.escort.is_none())
            .map(|(session, _)| *session)
            .collect()
    }
    /// The offer this NPC makes that rents or dismisses mercenaries, if `offer_id` is one.
    pub(super) fn merc_offer(&self, session: u64, npc_id: &str, offer_id: &str) -> Option<String> {
        let zone = self.players.get(&session)?.character.zone;
        let npc = self.maps[zone].npcs.iter().find(|n| n.id == npc_id)?;
        npc.offers
            .iter()
            .find(|o| o.id == offer_id)
            .and_then(|o| o.merc.clone())
    }

    /// Handles a mercenary offer from a quest giver: checks the player is at the NPC, runs the hire or dismissal and
    /// answers with the usual dialogue packet carrying the result as its notice.
    pub(super) fn merc_interact(&mut self, session: u64, npc_id: &str, what: &str) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let zone = p.character.zone;
        let Some(npc) = self.maps[zone].npcs.iter().find(|n| n.id == npc_id) else {
            return;
        };
        if p.character.hp <= 0. || p.character.point().distance(npc.position_at(self.time)) > 2.8 {
            let _ = p.peer.try_send(
                json!({"type":"error","text":"Walk closer to speak with this townsperson."}),
            );
            return;
        }
        let npc_json = json!(npc);
        let notice = if self.time - p.service_at < 0.5 {
            "Please wait a moment before trying again.".to_owned()
        } else {
            self.players.get_mut(&session).unwrap().service_at = self.time;
            let result = if what == "dismiss" {
                self.dismiss_mercenaries(session)
            } else {
                self.hire_mercenary(session, what, npc_id)
            };
            match result {
                Ok(text) | Err(text) => text,
            }
        };
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let _ = p.peer.try_send(json!({"type":"dialogue","npc":npc_json,"notice":notice,"gold":p.character.gold,"level":p.character.level,"mercPrice":merc_price(p.character.level),"quests":p.character.quests,"inventory":p.character.inventory,"equipment":p.character.equipment,"bags":p.character.bags,"bagCapacity":p.character.bag_capacity(),"look":p.character.look}));
        self.save();
    }

    fn hire_mercenary(
        &mut self,
        session: u64,
        class: &str,
        npc_id: &str,
    ) -> Result<String, String> {
        let class = class_named(class).ok_or("There is no such fighter for hire.")?;
        let p = self.players.get(&session).ok_or("Unknown session.")?;
        let c = &p.character;
        // A group-quest giver rents fighters for that quest; the Meeting Stone rents them to anyone, for any party of up to five.
        let quest = self.maps[c.zone]
            .quests
            .iter()
            .find(|q| {
                q.group && q.npc == npc_id && c.quests.iter().any(|g| g.id == q.id && !g.claimed)
            })
            .map(|q| {
                (
                    q.recommended_players as usize,
                    q.title.clone(),
                    q.id.clone(),
                    q.ready(c.quests.iter().find(|g| g.id == q.id).unwrap()),
                )
            });
        let open = self.maps[c.zone]
            .npcs
            .iter()
            .find(|n| n.id == npc_id)
            .is_some_and(|n| {
                n.offers.iter().any(|o| {
                    o.open && o.merc.as_deref() == Some(class_title(class).to_lowercase().as_str())
                })
            });
        let (wanted, title, contract) = match quest {
            Some((_, _, _, true)) => {
                return Err(
                    "This objective is already complete. Your mercenaries' work is done.".into(),
                );
            }
            Some((wanted, title, id, false)) => (wanted, title, Some(id)),
            None if open => (social::PARTY_MAX, "The Meeting Stone".to_owned(), None),
            None => {
                return Err(
                    "Take this elite quest first; I hire out fighters for the job itself.".into(),
                );
            }
        };
        let owner = c.id.clone();
        let party = self.party_mates(&owner).len();
        if party >= wanted {
            return Err(format!(
                "{title} wants {wanted} fighters and your party already has {party}."
            ));
        }
        let level = c.level;
        let price = merc_price(level);
        if c.gold < price {
            return Err(format!("A mercenary costs {price} gold."));
        }
        let (zone, point) = (c.zone, c.point());
        let mut name = format!("Merc {}", class_title(class));
        let same = self
            .players
            .values()
            .filter(|p| p.merc.is_some() && p.character.look.name.starts_with(&name))
            .count();
        if same > 0 {
            name = format!("{name} {}", same + 1);
        }
        let mut character = Character::mercenary(class, level, &name);
        character.zone = zone;
        let mut arrival = Point {
            x: point.x + 1.5,
            y: point.y + 1.5,
        };
        self.maps[zone].collide(&mut arrival, PLAYER_RADIUS);
        character.x = arrival.x;
        character.y = arrival.y;
        self.party_add_mercenary(&owner, &character)?;
        let merc_session = MERC_BASE + self.merc_seq;
        self.merc_seq += 1;
        // Nobody reads a mercenary's socket: a closed channel makes every send a harmless no-op.
        let (tx, _rx) = mpsc::channel(1);
        let mut merc = Player::new(character, tx);
        merc.merc = Some(owner);
        merc.merc_quest = contract;
        self.players.insert(merc_session, merc);
        self.players.get_mut(&session).unwrap().character.gold -= price;
        Ok(format!(
            "{name} joins your party for {price} gold. The party is now {}/{wanted}.",
            party + 1
        ))
    }

    /// Sends every mercenary the player hired away.
    pub(super) fn dismiss_mercenaries(&mut self, session: u64) -> Result<String, String> {
        let owner = self
            .players
            .get(&session)
            .ok_or("Unknown session.")?
            .character
            .id
            .clone();
        let hired = self.mercenaries_of(&owner);
        if hired.is_empty() {
            return Err("You have no mercenaries.".into());
        }
        for merc in &hired {
            self.remove_mercenary(*merc);
        }
        Ok(format!("{} mercenary contract(s) ended.", hired.len()))
    }

    pub(super) fn remove_mercenary(&mut self, session: u64) {
        if let Some(p) = self.players.remove(&session) {
            self.leave_party(&p.character.id);
        }
    }

    /// Once per tick, before the players move: decide what every mercenary does.
    pub(super) fn update_mercenaries(&mut self) {
        let mercs: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.merc.is_some() && p.escort.is_none())
            .map(|(session, _)| *session)
            .collect();
        for session in mercs {
            let owner_id = self.players[&session].merc.clone().unwrap_or_default();
            let Some(owner) = self.session_of(&owner_id) else {
                self.remove_mercenary(session);
                continue;
            };
            let p = &self.players[&session];
            let hirer = &self.players[&owner].character;
            let objective_done = p.merc_quest.as_ref().is_some_and(|id| {
                hirer
                    .quests
                    .iter()
                    .find(|g| &g.id == id)
                    .is_none_or(|progress| {
                        progress.claimed
                            || self
                                .maps
                                .iter()
                                .flat_map(|m| &m.quests)
                                .find(|q| &q.id == id)
                                .is_none_or(|q| q.ready(progress))
                    })
            });
            let cleared =
                self.instance_cleared(p.character.zone) || self.instance_cleared(hirer.zone);
            if objective_done || cleared {
                let name = p.character.look.name.clone();
                let reason = if cleared {
                    "the instance is cleared"
                } else {
                    "the objective is complete"
                };
                let _ = self.players[&owner].peer.try_send(
                    json!({"type":"system","text":format!("{name} departs: {reason}." )}),
                );
                self.remove_mercenary(session);
                continue;
            }
            let mate_ids = self.party_mates(&owner_id);
            let merc_id = self.players[&session].character.id.clone();
            if !mate_ids.contains(&merc_id) {
                // The hirer left the party (or it broke up): the contract is over.
                self.remove_mercenary(session);
                continue;
            }
            self.merc_think(session, owner, &mate_ids);
        }
    }

    fn merc_think(&mut self, session: u64, owner: u64, mate_ids: &[String]) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        if p.character.hp <= 0. {
            return;
        }
        let me = p.character.point();
        let zone = p.character.zone;
        let owner_p = &self.players[&owner];
        if owner_p.character.spark_travel.is_some() {
            let p = self.players.get_mut(&session).unwrap();
            p.stop();
            p.attack = 0.;
            return;
        }
        let there = owner_p.character.point();
        let owner_target = owner_p.target;
        let mate_sessions: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, q)| mate_ids.contains(&q.character.id))
            .map(|(s, _)| *s)
            .collect();
        // Carried to the hirer's side when in another zone, or far away while the hirer is out of combat. During a
        // fight a mercenary who fell (and woke at the zone's start) must walk back like anyone else.
        if owner_p.character.zone != zone
            || (me.distance(there) > MERC_LEASH && owner_p.combat_left <= 0.)
        {
            let (to_zone, mut arrival) = (
                owner_p.character.zone,
                Point {
                    x: there.x + 1.5,
                    y: there.y + 1.5,
                },
            );
            self.maps[to_zone].collide(&mut arrival, PLAYER_RADIUS);
            let p = self.players.get_mut(&session).unwrap();
            p.character.zone = to_zone;
            p.character.x = arrival.x;
            p.character.y = arrival.y;
            p.stop();
            p.portal_at = self.time;
            return;
        }
        // What to fight: the hirer's target, else whatever is attacking the party nearby.
        let alive = |s: &Slime| !s.dead && s.zone == zone;
        let chosen = owner_target
            .filter(|id| self.slimes.get(*id).is_some_and(alive))
            .or_else(|| {
                self.slimes
                    .iter()
                    .filter(|s| {
                        alive(s)
                            && s.target.is_some_and(|t| mate_sessions.contains(&t))
                            && s.point().distance(me) < MERC_SIGHT
                    })
                    .min_by(|a, b| a.point().distance(me).total_cmp(&b.point().distance(me)))
                    .map(|s| s.id)
            });
        // A boss fight asks more of a fighter than a swing: step out of a telegraph, ground a charge, hold a brazier,
        // hit a shield's helpers first (`boss_play.rs`, the same brain the dungeon harness's bots use).
        let play = self.boss_play(session);
        let chosen = play.as_ref().and_then(|b| b.target).or(chosen);
        let hold_fire = play.as_ref().is_some_and(|b| b.hold_fire);
        self.ai_combat(
            session,
            &mate_sessions,
            if hold_fire { None } else { chosen },
        );
        if let Some(goal) = play.as_ref().and_then(|b| b.goal) {
            let p = self.players.get_mut(&session).unwrap();
            p.target = None;
            p.goal = Some(goal);
            return;
        }
        if play.as_ref().is_some_and(|b| b.stay) {
            // A wall or a spoke is on its way and this is a safe place: stand in it.
            let p = self.players.get_mut(&session).unwrap();
            p.target = None;
            p.goal = None;
            p.input = Point::default();
            return;
        }
        // Move: fight the chosen enemy, or keep to the hirer's side.
        let slot = {
            let mut hired: Vec<u64> = self.mercenaries_of(&self.players[&owner].character.id);
            hired.sort_unstable();
            hired.iter().position(|s| *s == session).unwrap_or(0) as f64
        };
        let p = self.players.get_mut(&session).unwrap();
        match chosen {
            Some(id) => {
                if p.target != Some(id) {
                    p.target = Some(id);
                    p.goal = None;
                    p.input = Point::default();
                }
            }
            None => {
                p.target = None;
                let angle = slot * 1.3 + 0.6;
                let goal = Point {
                    x: there.x + angle.cos() * 2.4,
                    y: there.y + angle.sin() * 2.4,
                };
                if me.distance(goal) > 1.6 {
                    p.goal = Some(goal);
                } else if me.distance(there) < 1. {
                    p.goal = None;
                }
            }
        }
    }

    /// The mercenaries' play for a fighter who is not a mercenary: the test harness's hirer and party use it, so every
    /// fighter in a fight plays by the same code. Fights `chosen` (or what the boss brain says) with the class's skills
    /// through `ai_combat`, steps out of telegraphs, holds fire when asked, and leaves walking and swinging to the engine.
    #[cfg(test)]
    pub(super) fn auto_play(&mut self, session: u64, mate_sessions: &[u64], chosen: Option<usize>) {
        let play = self.boss_play(session);
        let chosen = play.as_ref().and_then(|b| b.target).or(chosen);
        let hold_fire = play.as_ref().is_some_and(|b| b.hold_fire);
        self.ai_combat(
            session,
            mate_sessions,
            if hold_fire { None } else { chosen },
        );
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        if let Some(goal) = play.as_ref().and_then(|b| b.goal) {
            p.target = None;
            p.goal = Some(goal);
        } else if play.as_ref().is_some_and(|b| b.stay) {
            p.target = None;
            p.goal = None;
            p.input = Point::default();
        } else if let Some(id) = chosen {
            if p.target != Some(id) {
                p.target = Some(id);
                p.goal = None;
                p.input = Point::default();
            }
        } else {
            p.target = None;
        }
    }

    /// Combat decisions shared by hired mercenaries and independent adventurers. Movement and ownership stay separate.
    pub(super) fn ai_combat(&mut self, session: u64, mate_sessions: &[u64], chosen: Option<usize>) {
        let target = chosen
            .and_then(|id| self.slimes.get(id))
            .map(|s| (s.point(), s.r));
        self.ai_combat_at(session, mate_sessions, target);
    }

    /// `ai_combat` against a target given by position and body radius: a monster, or a player in a duel, arena or
    /// flagged fight (the duel matrix drives both duelists with this).
    pub(super) fn ai_combat_at(
        &mut self,
        session: u64,
        mate_sessions: &[u64],
        target_point: Option<(Point, f64)>,
    ) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        if p.character.hp <= 0. {
            return;
        }
        let me = p.character.point();
        let zone = p.character.zone;
        let class = p.character.look.class;
        // Keep the party alive first: one potion at a time (they share a cooldown), health before mana.
        {
            let p = &self.players[&session];
            let c = &p.character;
            let best = |wanted: &dyn Fn(&Item) -> bool| {
                c.inventory
                    .iter()
                    .filter_map(|s| item(&s.item))
                    .filter(|i| i.kind == "potion" && wanted(i) && i.required_level <= c.level)
                    .max_by(|a, b| (a.heal + a.mana).total_cmp(&(b.heal + b.mana)))
                    .map(|i| i.id.clone())
            };
            let drink = if p.potion_cd > 0. {
                None
            } else if c.hp < c.max_hp() * 0.45 {
                best(&|i| i.heal > 0.)
            } else if c.look.class.resource_type() == "mana"
                && c.resource() < c.max_resource() * 0.25
            {
                best(&|i| i.mana > 0.)
            } else {
                None
            };
            if let Some(id) = drink {
                self.use_item(session, &id);
            }
        }
        let hurt = |hp: f64, max: f64, fraction: f64| hp < max * fraction;
        let (own_hurt, wounded_near) = {
            let p = &self.players[&session];
            let own = hurt(p.character.hp, p.character.max_hp(), 0.55);
            let near = |range: f64| {
                self.players
                    .iter()
                    .filter(|(s, q)| {
                        mate_sessions.contains(s)
                            && q.character.hp > 0.
                            && q.character.zone == zone
                            && q.character.point().distance(me) <= range
                            && hurt(q.character.hp, q.character.max_hp(), 0.7)
                    })
                    .count()
            };
            (own, (near(8.), near(14.)))
        };
        let aim = target_point.map_or(Point::default(), |(t, _)| me.direction(t));
        let level = self.players[&session].character.level;
        for base in skills::SKILLS
            .iter()
            .filter(|s| s.class == class && s.level <= level)
        {
            let skill = base.at_level(level);
            let p = &self.players[&session];
            if p.skill_cd.contains_key(&skill.id)
                || p.character.resource() < skill.cost
                || p.dash > 0.
                || p.stun > 0.
            {
                continue;
            }
            let fire = match &skill.effect {
                Effect::Heal { .. } => own_hurt,
                Effect::Mend { range, .. } => {
                    if *range > 8. {
                        wounded_near.1 > 0
                    } else {
                        wounded_near.0 > 0
                    }
                }
                Effect::Buff { kind, .. } => {
                    target_point.is_some_and(|(t, _)| t.distance(me) < 10.)
                        && !p.buffs.iter().any(|b| b.kind == *kind)
                }
                Effect::Dash { .. } => false,
                Effect::Cone { reach, .. } => {
                    target_point.is_some_and(|(t, r)| t.distance(me) - r <= *reach)
                }
                Effect::Nova { radius, .. } => {
                    target_point.is_some_and(|(t, r)| t.distance(me) - r <= *radius)
                }
                Effect::Strike { range, .. } | Effect::Chain { range, .. } => {
                    target_point.is_some_and(|(t, r)| t.distance(me) - r <= *range)
                }
                Effect::Meteor { range, .. } => {
                    target_point.is_some_and(|(t, _)| t.distance(me) <= *range)
                }
                Effect::Volley { .. } => target_point.is_some_and(|(t, _)| t.distance(me) <= 9.),
            };
            if fire {
                self.use_skill(session, &skill.id, aim);
            }
        }
    }
}

#[cfg(test)]
mod price_tests {
    use super::merc_price;

    #[test]
    fn the_price_rises_with_the_hirers_level_and_never_falls() {
        assert_eq!(merc_price(1), 250);
        assert_eq!(merc_price(10), 400);
        assert_eq!(merc_price(15), 800);
        assert_eq!(merc_price(99), 115_000);
        assert_eq!((merc_price(0), merc_price(150)), (250, 115_000));
        for level in 1..99 {
            assert!(merc_price(level + 1) >= merc_price(level), "level {level}");
            assert_eq!(merc_price(level) % 50, 0, "level {level}");
        }
    }
}
