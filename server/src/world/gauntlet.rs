//! Arena gauntlet quests (`docs/arena-quests.md`). A quest giver sends the hero into a private Arena copy where five
//! opponents, one per class in a random order, are fought one at a time under PvP rules. After every win the hero is
//! healed and a countdown runs; losing, running out of time or leaving ends the run and costs nothing. Winning the fifth
//! fight makes the quest ready to hand in. A run lives only in memory: nothing of it is saved.
//!
//! An opponent is a real `Player` flagged `gauntlet` with `merc` set to the hero's character id, like an escort: it is
//! never saved, never counted as online and never put in a party. `pvp_legal` lets the hero and the hero's own opponent
//! hurt each other and nobody else.
use super::mercs::{MERC_BASE, class_title, merc_price};
use super::*;

/// Fights in one run: one per class.
pub(super) const FIGHTS: usize = 5;
const COUNTDOWN: f64 = 10.;
/// A fight that is still going after this many seconds is lost. As long as an arena match (the duel matrix's longest
/// decided pair, Priest against Priest at level 30, takes 173 s).
const FIGHT_TIME: f64 = 300.;
const HERO_SPOT: Point = Point { x: 9., y: 16. };
const OPPONENT_SPOT: Point = Point { x: 23., y: 16. };
pub(super) const CLASSES: [Class; FIGHTS] = [
    Class::Warrior,
    Class::Mage,
    Class::Assassin,
    Class::Priest,
    Class::Hunter,
];
/// An opponent has this share of the health its level and gear give it: every blow that lands on it is worth
/// `1 / OPPONENT_HEALTH` times as much (owner, 2026-10-21: "30% easier to win the arena"). Test builds read
/// `GAUNTLET_OPPONENT_HEALTH` to measure other values without a rebuild.
const OPPONENT_HEALTH: f64 = 0.7;
pub(super) fn opponent_health() -> f64 {
    #[cfg(test)]
    if let Some(v) = std::env::var("GAUNTLET_OPPONENT_HEALTH")
        .ok()
        .and_then(|v| v.parse::<f64>().ok())
    {
        return v;
    }
    OPPONENT_HEALTH
}
/// An opponent's blows on the hero are worth this share of what its level and gear give it (owner, 2026-10-23: "ease up
/// the arena quests by 50%"). Test builds read `GAUNTLET_OPPONENT_DAMAGE` to measure other values without a rebuild.
const OPPONENT_DAMAGE: f64 = 0.5;
pub(super) fn opponent_damage() -> f64 {
    #[cfg(test)]
    if let Some(v) = std::env::var("GAUNTLET_OPPONENT_DAMAGE")
        .ok()
        .and_then(|v| v.parse::<f64>().ok())
    {
        return v;
    }
    OPPONENT_DAMAGE
}
/// The worn slots of a plain level-appropriate set: the equipment slot and the catalog kind that fills it.
const SLOTS: [(&str, &str); 10] = [
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

pub(super) struct Run {
    /// The hero's session.
    pub(super) owner: u64,
    pub(super) quest: String,
    pub(super) level: u32,
    /// The private Arena copy.
    pub(super) zone: usize,
    /// Where the hero stood at the giver.
    pub(super) returns: (usize, f64, f64),
    pub(super) order: [Class; FIGHTS],
    pub(super) won: usize,
    pub(super) opponent: Option<u64>,
    /// The end of the countdown while nobody stands in the ring, the cap of the fight while someone does.
    pub(super) until: f64,
    /// Set by `pvp_hit` when a fighter reaches the one health floor; settled at the next tick.
    pub(super) fallen: Option<u64>,
    /// The share of health and of damage the opponents get in this run (a game master's test run changes them).
    pub(super) opponent_health: f64,
    pub(super) opponent_damage: f64,
}

/// The progression set of green pieces for `level` (the set of the level rounded down to a multiple of 5, 99 uses 95),
/// one per slot, as the duel matrix and the kill-time grid dress an ordinary character.
fn green_gear(class: Class, level: u32) -> Vec<(&'static str, String)> {
    gear_set(class, level, "uncommon")
}

/// `green_gear` in another rarity (`uncommon`, `rare` or `epic`): purple exists only at the tens from 10 to 90, so a level
/// snaps down to one of those. Used by the game master's test menu as well.
pub(super) fn gear_set(class: Class, level: u32, rarity: &str) -> Vec<(&'static str, String)> {
    let want = if rarity == "epic" {
        (level / 10 * 10).clamp(10, 90)
    } else {
        (level / 5 * 5).clamp(5, 95)
    };
    let colour = match rarity {
        "epic" => "purple",
        "rare" => "blue",
        _ => "green",
    };
    SLOTS
        .iter()
        .filter_map(|&(slot, kind)| {
            let want = if kind == "cloak" && level >= 99 {
                99
            } else {
                want
            };
            let pieces: Vec<&Item> = ITEMS
                .iter()
                .filter(|i| {
                    i.kind == kind
                        && i.rarity == rarity
                        && i.required_level == want
                        && i.source.is_none()
                        && !i.starter
                        && i.class.is_none_or(|c| c == class)
                })
                .collect();
            let named: Vec<&Item> = pieces
                .iter()
                .copied()
                .filter(|i| i.id.ends_with(&format!("_l{want}_{colour}")))
                .collect();
            let chosen = if named.is_empty() { &pieces } else { &named };
            chosen.first().map(|piece| (slot, piece.id.clone()))
        })
        .collect()
}

/// An opponent: `class` at `level` in plain green gear with its attribute points spent, at full health and resource.
pub(super) fn opponent_character(class: Class, level: u32, name: &str) -> Character {
    let mut character = Character::mercenary(class, level, name);
    character.inventory.clear();
    character.attributes = Attributes::default();
    let mut equip = BTreeMap::new();
    for (slot, id) in green_gear(class, level) {
        character.add_item(&id, 1);
        equip.insert(slot.to_string(), id);
    }
    let _ = character.equip_slots(&equip);
    if character.stat_points() > 0 {
        let _ = character.allocate_recommended();
    }
    character.hp = character.max_hp();
    character.reset_resource();
    character
}

/// The distance `pvp_attack` allows for a class.
fn attack_range(class: Class) -> f64 {
    class.reach().max(if class.ranged() { 8. } else { 1.8 })
}

impl World {
    /// Whether `a` and `b` are a hero and that hero's own opponent in a live run (either way round).
    pub(super) fn gauntlet_pair(&self, a: u64, b: u64) -> bool {
        self.gauntlets.iter().any(|r| {
            (r.owner == a && r.opponent == Some(b)) || (r.owner == b && r.opponent == Some(a))
        })
    }

    /// A fighter reached the one health floor: remember it, the next tick settles the fight. If both fall in the same
    /// tick the hero's fall counts.
    pub(super) fn gauntlet_fall(&mut self, fallen: u64) {
        if let Some(run) = self
            .gauntlets
            .iter_mut()
            .find(|r| r.owner == fallen || r.opponent == Some(fallen))
            && (run.fallen.is_none() || run.owner == fallen)
        {
            run.fallen = Some(fallen);
        }
    }

    /// What the hero's client shows: which fight, the countdown or the cap, and who the opponent is.
    pub(super) fn gauntlet_view(&self, session: u64) -> Value {
        let Some(run) = self.gauntlets.iter().find(|r| r.owner == session) else {
            return Value::Null;
        };
        let left = (run.until - self.time).max(0.).ceil();
        let opponent = run.opponent.and_then(|s| self.players.get(&s)).map(|p| {
            json!({"id":p.character.id,"name":p.character.look.name,"class":format!("{:?}", p.character.look.class).to_lowercase()})
        });
        json!({
            "quest": run.quest,
            "level": run.level,
            "fight": run.won + 1,
            "of": FIGHTS,
            "countdown": if run.opponent.is_none() { json!(left) } else { Value::Null },
            "ends": if run.opponent.is_some() { json!(left) } else { Value::Null },
            "next": if run.opponent.is_none() { json!(format!("{:?}", run.order[run.won]).to_lowercase()) } else { Value::Null },
            "opponent": opponent,
        })
    }

    /// A fight start or a result: the big centre line (kind `quest`), which the client also writes to the chat log.
    fn announce(&self, id: &str, text: impl Into<String>) {
        if let Some(p) = self.online(id) {
            let _ = p
                .peer
                .try_send(json!({"type":"announce","kind":"quest","text":text.into()}));
        }
    }

    /// The hero asks a giver to enter the Arena. The reply is a notice.
    pub(super) fn gauntlet_interact(&mut self, session: u64, npc_id: &str) {
        let id = self
            .players
            .get(&session)
            .map(|p| p.character.id.clone())
            .unwrap_or_default();
        match self.gauntlet_start(session, npc_id) {
            Ok(text) => self.tell(&id, text, true),
            // A refusal answers with the dialogue again, so the clicked offer button is never left disabled.
            Err(text) => {
                let Some(p) = self.players.get(&session) else {
                    return;
                };
                if let Some(npc) = self.maps[p.character.zone]
                    .npcs
                    .iter()
                    .find(|n| n.id == npc_id)
                {
                    let _ = p.peer.try_send(json!({"type":"dialogue","npc":json!(npc),"notice":text,"gold":p.character.gold,"level":p.character.level,"mercPrice":merc_price(p.character.level),"quests":p.character.quests,"inventory":p.character.inventory,"equipment":p.character.equipment,"bags":p.character.bags,"bagCapacity":p.character.bag_capacity(),"look":p.character.look}));
                }
            }
        }
        self.pvp_sync();
    }

    fn gauntlet_start(&mut self, session: u64, npc_id: &str) -> Result<String, String> {
        let p = self.players.get(&session).ok_or("Unknown session.")?;
        let c = &p.character;
        let zone = c.zone;
        let npc = self.maps[zone]
            .npcs
            .iter()
            .find(|n| n.id == npc_id)
            .ok_or("Nobody here offers that.")?;
        if c.hp <= 0. || c.point().distance(npc.position_at(self.time)) > 2.8 {
            return Err("Walk closer to speak with this townsperson.".into());
        }
        if self.gauntlets.iter().any(|r| r.owner == session)
            || self.pvp_busy(&c.id)
            || p.is_hidden()
            || c.spark_travel.is_some()
            || self.is_arena_zone(zone)
        {
            return Err("Finish what you are doing first.".into());
        }
        // The lowest arena quest taken and not yet won or handed in.
        let (level, quest_id) = self.maps[zone]
            .quests
            .iter()
            .filter(|q| q.npc == npc_id)
            .filter_map(|q| Some((q.gauntlet_level()?, q)))
            .filter(|(_, q)| {
                c.quests
                    .iter()
                    .any(|g| g.id == q.id && !g.claimed && !q.ready(g))
            })
            .min_by_key(|(level, _)| *level)
            .map(|(level, q)| (level, q.id.clone()))
            .ok_or("Take one of my arena quests first. A quest you have already won is handed in here.")?;
        let arena = self
            .instances
            .iter()
            .find(|i| self.is_arena_zone(i.zone) && !i.active)
            .map(|i| i.zone)
            .ok_or("The Arena is full right now. Try again in a few minutes.")?;
        let returns = (zone, c.x, c.y);
        let mut order = CLASSES;
        for i in (1..FIGHTS).rev() {
            order.swap(i, (self.random() * (i + 1) as f64) as usize % (i + 1));
        }
        Ok(self.gauntlet_launch(session, quest_id, level, arena, returns, order, 0))
    }

    /// Moves the hero into the private Arena copy `arena` and starts the countdown of fight `won + 1`. An empty `quest_id`
    /// is a game master's test run: it reads and writes no quest.
    #[allow(clippy::too_many_arguments)]
    pub(super) fn gauntlet_launch(
        &mut self,
        session: u64,
        quest_id: String,
        level: u32,
        arena: usize,
        returns: (usize, f64, f64),
        order: [Class; FIGHTS],
        won: usize,
    ) -> String {
        let p = self.players.get_mut(&session).unwrap();
        p.character.zone = arena;
        p.character.x = HERO_SPOT.x;
        p.character.y = HERO_SPOT.y;
        p.character.hp = p.character.max_hp();
        p.character.reset_resource();
        p.character.mounted = false;
        p.combat_left = 0.;
        p.stop();
        p.attack = 0.;
        p.cooldown = 0.;
        p.buffs.clear();
        if let Some(g) = p.character.quests.iter_mut().find(|g| g.id == quest_id) {
            g.counts = vec![0];
        }
        self.enter_instance(arena);
        self.gauntlets.push(Run {
            owner: session,
            quest: quest_id,
            level,
            zone: arena,
            returns,
            order,
            won,
            opponent: None,
            until: self.time + COUNTDOWN,
            fallen: None,
            opponent_health: opponent_health(),
            opponent_damage: opponent_damage(),
        });
        self.save();
        format!(
            "The gauntlet begins: {FIGHTS} fights, one against each class. The first starts in {COUNTDOWN:.0} seconds."
        )
    }

    /// Once per tick: spawn the next opponent, settle a finished fight, drive the opponent.
    pub(super) fn update_gauntlets(&mut self) {
        let mut i = 0;
        while i < self.gauntlets.len() {
            if self.gauntlet_tick(i) {
                i += 1;
            }
        }
    }

    /// Returns false when the run ended and was removed.
    fn gauntlet_tick(&mut self, i: usize) -> bool {
        let (owner, zone, opponent, until, fallen) = {
            let r = &self.gauntlets[i];
            (r.owner, r.zone, r.opponent, r.until, r.fallen)
        };
        match self.players.get(&owner) {
            Some(p) if p.character.zone == zone => {}
            // The hero is gone or was moved out by something else (a debug teleport): nothing to give back.
            _ => {
                self.gauntlet_end(i, false, false, "");
                return false;
            }
        }
        let Some(opponent) = opponent else {
            if self.time >= until {
                self.gauntlet_spawn(i);
            }
            return true;
        };
        if !self.players.contains_key(&opponent) {
            self.gauntlet_end(
                i,
                true,
                false,
                "The opponent left the ring. The gauntlet is over.",
            );
            return false;
        }
        if let Some(fallen) = fallen {
            if fallen == owner {
                self.gauntlet_end(
                    i,
                    true,
                    false,
                    "You were defeated. The gauntlet is over; talk to the giver to try again.",
                );
                return false;
            }
            return self.gauntlet_won_fight(i);
        }
        if self.time >= until {
            self.gauntlet_end(
                i,
                true,
                false,
                "Time ran out. The gauntlet is over; talk to the giver to try again.",
            );
            return false;
        }
        self.gauntlet_play(opponent, owner);
        true
    }

    /// The hero beat the standing opponent. Returns false when that was the fifth and the run ended.
    fn gauntlet_won_fight(&mut self, i: usize) -> bool {
        let (owner, opponent) = (self.gauntlets[i].owner, self.gauntlets[i].opponent);
        if let Some(o) = opponent {
            self.players.remove(&o);
        }
        self.gauntlets[i].won += 1;
        let won = self.gauntlets[i].won;
        if won >= FIGHTS {
            self.gauntlet_end(
                i,
                true,
                true,
                if self.gauntlets[i].quest.is_empty() {
                    "All five opponents are down. (Test run: no quest.)"
                } else {
                    "All five opponents are down. The quest is ready to hand in."
                },
            );
            return false;
        }
        self.gauntlet_restore(owner);
        let quest = self.gauntlets[i].quest.clone();
        if let Some(g) = self
            .players
            .get_mut(&owner)
            .and_then(|p| p.character.quests.iter_mut().find(|g| g.id == quest))
        {
            g.counts = vec![won as u32];
        }
        let id = self.players[&owner].character.id.clone();
        let run = &mut self.gauntlets[i];
        run.opponent = None;
        run.fallen = None;
        run.until = self.time + COUNTDOWN;
        self.announce(
            &id,
            format!("Fight {won} of {FIGHTS} won. Health and mana restored; the next one starts in {COUNTDOWN:.0} seconds."),
        );
        self.pvp_sync();
        true
    }

    /// Full health and mana, no stun, root, wound or ward, nothing left of the last fight's tension.
    fn gauntlet_restore(&mut self, owner: u64) {
        if let Some(p) = self.players.get_mut(&owner) {
            p.character.hp = p.character.max_hp();
            p.character.reset_resource();
            p.cooldown = 0.;
            p.stun = 0.;
            p.root = 0.;
            p.wound_left = 0.;
            p.pvp_fight = 0.;
            p.absorb_left = 0.;
            p.combat_left = 0.;
            p.stop();
        }
    }

    /// Ends run `i`: the opponent is removed, the progress is stored, and with `back` the hero returns to the giver.
    /// `completed` makes the quest ready; anything else resets its progress. A run that ends leaves its Arena copy empty,
    /// which `update_instances` then resets and frees.
    fn gauntlet_end(&mut self, i: usize, back: bool, completed: bool, text: &str) {
        let run = self.gauntlets.remove(i);
        if let Some(o) = run.opponent {
            self.players.remove(&o);
        }
        self.gauntlet_restore(run.owner);
        let Some(p) = self.players.get_mut(&run.owner) else {
            return;
        };
        if let Some(g) = p.character.quests.iter_mut().find(|g| g.id == run.quest)
            && !g.claimed
        {
            g.counts = vec![if completed { FIGHTS as u32 } else { 0 }];
        }
        if back {
            let (zone, x, y) = run.returns;
            p.character.zone = zone;
            p.character.x = x;
            p.character.y = y;
        }
        let id = p.character.id.clone();
        if !text.is_empty() {
            self.announce(&id, text);
        }
        self.save();
        self.pvp_sync();
    }

    /// The hero left (logged out, forfeited): the same as a lost run, without a message to a hero who is gone.
    pub(super) fn gauntlet_abort(&mut self, owner: u64, text: &str) {
        if let Some(i) = self.gauntlets.iter().position(|r| r.owner == owner) {
            self.gauntlet_end(i, true, false, text);
        }
    }

    /// Puts the next opponent in the ring: this class at the quest's level in plain green gear.
    fn gauntlet_spawn(&mut self, i: usize) {
        let run = &self.gauntlets[i];
        let (owner, level, zone, class) = (run.owner, run.level, run.zone, run.order[run.won]);
        let (fight, owner_id) = (run.won + 1, self.players[&owner].character.id.clone());
        let name = format!("Arena {}", class_title(class));
        let mut character = opponent_character(class, level, &name);
        character.zone = zone;
        let mut spot = OPPONENT_SPOT;
        self.maps[zone].collide(&mut spot, PLAYER_RADIUS);
        character.x = spot.x;
        character.y = spot.y;
        let session = MERC_BASE + self.merc_seq;
        self.merc_seq += 1;
        // Nobody reads an opponent's socket: a closed channel makes every send a harmless no-op.
        let (tx, _rx) = mpsc::channel(1);
        let mut opponent = Player::new(character, tx);
        opponent.merc = Some(owner_id.clone());
        opponent.gauntlet = true;
        self.players.insert(session, opponent);
        let run = &mut self.gauntlets[i];
        run.opponent = Some(session);
        run.fallen = None;
        run.until = self.time + FIGHT_TIME;
        self.announce(
            &owner_id,
            format!("Fight {fight} of {FIGHTS}: {name}. Defeat it before time runs out."),
        );
        self.pvp_sync();
    }

    /// One tick of the opponent: close in, swing, and let the mercenaries' skill code cast (the duel matrix's driver).
    pub(super) fn gauntlet_play(&mut self, me: u64, foe: u64) {
        let (class, hp, here, has_goal) = {
            let p = &self.players[&me];
            let c = &p.character;
            (c.look.class, c.hp, c.point(), p.goal.is_some())
        };
        if hp <= 0. {
            return;
        }
        let there = self.players[&foe].character.point();
        let distance = here.distance(there);
        if distance - PLAYER_RADIUS > class.reach() * 0.9 {
            self.message(
                me,
                ClientMessage::Move {
                    x: there.x,
                    y: there.y,
                },
            );
        } else if has_goal {
            self.message(me, ClientMessage::Stop);
        }
        let ready = {
            let p = &self.players[&me];
            p.cooldown <= 0. && p.dash <= 0. && p.stun <= 0.
        };
        if ready
            && distance <= attack_range(class)
            && (!class.ranged()
                || self.maps[self.players[&me].character.zone].line_clear(here, there, 0.05))
        {
            let foe_id = self.players[&foe].character.id.clone();
            self.pvp_command(me, PvpCommand::Attack { id: foe_id });
        }
        self.ai_combat_at(me, &[], Some((there, PLAYER_RADIUS)));
    }
}
