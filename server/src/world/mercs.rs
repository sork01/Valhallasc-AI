//! Mercenaries. The giver of a group quest (a quest with `group` and `recommendedPlayers`, today the Cinderlord and
//! Gloomroot elites) rents fighters for `MERC_COST` gold each, up to the number of players the quest wants. A mercenary is
//! an ordinary `Player` (so enemies fight it, a priest's mends reach it, it shows in the party and on every client)
//! whose input is decided here instead of by a socket: it joins its hirer's party, follows them, helps whatever they or
//! their party are fighting, uses its class's skills sensibly, drinks a potion when hurt, and is never saved.
//! Whatever a mercenary earns belongs to its hirer (see `World::credit_session`).
//! It leaves when its hirer logs out or leaves the party, when the hirer claims a group quest, or when sent away.
use super::*;

/// Gold for one mercenary, whatever its class.
pub const MERC_COST: u32 = 250;
/// Mercenary sessions live far above every socket's counter, so the two can never collide.
const MERC_BASE: u64 = 1 << 62;
/// A mercenary farther than this from its hirer (or in another zone) is carried to their side.
const MERC_LEASH: f64 = 26.;
/// Enemies attacking the party this close are fought without waiting for the hirer to pick a target.
const MERC_SIGHT: f64 = 14.;

fn class_named(name: &str) -> Option<Class> {
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
        self.players.values().filter(|p| p.merc.is_none()).count()
    }
    fn session_of(&self, character: &str) -> Option<u64> {
        self.players
            .iter()
            .find(|(_, p)| p.merc.is_none() && p.character.id == character)
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
            .filter(|(_, p)| p.merc.as_deref() == Some(owner))
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
        let _ = p.peer.try_send(json!({"type":"dialogue","npc":npc_json,"notice":notice,"gold":p.character.gold,"quests":p.character.quests,"inventory":p.character.inventory,"equipment":p.character.equipment,"bags":p.character.bags,"bagCapacity":p.character.bag_capacity(),"look":p.character.look}));
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
        let quest = self.maps[c.zone]
            .quests
            .iter()
            .find(|q| {
                q.group && q.npc == npc_id && c.quests.iter().any(|g| g.id == q.id && !g.claimed)
            })
            .ok_or("Take this elite quest first; I hire out fighters for the job itself.")?;
        let wanted = quest.recommended_players as usize;
        let owner = c.id.clone();
        let party = self.party_mates(&owner).len();
        if party >= wanted {
            return Err(format!(
                "{} wants {wanted} fighters and your party already has {party}.",
                quest.title
            ));
        }
        if c.gold < MERC_COST {
            return Err(format!("A mercenary costs {MERC_COST} gold."));
        }
        let level = c.level;
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
        self.players.insert(merc_session, merc);
        self.players.get_mut(&session).unwrap().character.gold -= MERC_COST;
        Ok(format!(
            "{name} joins your party for {MERC_COST} gold. The party is now {}/{wanted}.",
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
            .filter(|(_, p)| p.merc.is_some())
            .map(|(session, _)| *session)
            .collect();
        for session in mercs {
            let owner_id = self.players[&session].merc.clone().unwrap_or_default();
            let Some(owner) = self.session_of(&owner_id) else {
                self.remove_mercenary(session);
                continue;
            };
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
        let class = self.players[&session].character.look.class;
        // Keep the party alive first: a potion when low, then the class's healing and buffs.
        {
            let p = &self.players[&session];
            if p.character.hp < p.character.max_hp() * 0.45
                && p.potion_cd <= 0.
                && p.character.quantity("health_potion") > 0
            {
                self.use_item(session, "health_potion");
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
        let target_point = chosen
            .and_then(|id| self.slimes.get(id))
            .map(|s| (s.point(), s.r));
        let aim = target_point.map_or(Point::default(), |(t, _)| me.direction(t));
        let level = self.players[&session].character.level;
        for skill in skills::SKILLS
            .iter()
            .filter(|s| s.class == class && s.level <= level)
        {
            let p = &self.players[&session];
            if p.skill_cd.contains_key(&skill.id)
                || p.character.resource() < skill.cost
                || p.dash > 0.
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
}
