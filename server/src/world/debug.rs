//! Test-server shortcuts. They exist so automated tests can reach a state (level 20, a quest turned in, a far zone)
//! without hours of play, while every rule that is not the shortcut itself still runs: rewards, level-up events, unlocks,
//! drops, saves. `World::test_commands` stays off unless VALHALLA_TEST_COMMANDS=1, and the public service never sets it.
use super::*;

const MAX_DEBUG_LEVEL: u32 = 100;

impl World {
    pub(super) fn debug(&mut self, session: u64, reference: Option<u64>, command: DebugCommand) {
        let outcome = if self.test_commands {
            self.run_debug(session, command)
        } else {
            Err("Test commands are disabled on this server.".to_owned())
        };
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let packet = match outcome {
            Ok(result) => {
                json!({"type":"debug","ref":reference,"ok":true,"tick":self.tick,"result":result})
            }
            Err(text) => {
                json!({"type":"debug","ref":reference,"ok":false,"tick":self.tick,"error":text})
            }
        };
        let _ = p.peer.try_send(packet);
    }

    pub(super) fn run_debug(
        &mut self,
        session: u64,
        command: DebugCommand,
    ) -> Result<Value, String> {
        let p = self.players.get_mut(&session).ok_or("Unknown session.")?;
        let actor = p.character.id.clone();
        let point = p.character.point();
        let mut levels = 0;
        let result = match command {
            DebugCommand::SetLevel { level } => {
                if !(1..=MAX_DEBUG_LEVEL).contains(&level) {
                    return Err(format!("Level must be 1-{MAX_DEBUG_LEVEL}."));
                }
                let c = &mut p.character;
                let before = c.level;
                if level < before {
                    // Trained points beyond the lower budget would be impossible to earn.
                    c.attributes = Attributes::default();
                }
                c.level = level;
                c.xp = 0;
                c.hp = c.max_hp();
                levels = level.saturating_sub(before);
                json!({"level":level,"unlocked":skills::unlocked(c.look.class, before, level)})
            }
            DebugCommand::GiveXp { amount } => {
                let c = &mut p.character;
                let before = c.level;
                levels = c.grant_xp(amount);
                json!({"level":c.level,"xp":c.xp,"levels":levels,"unlocked":skills::unlocked(c.look.class, before, c.level)})
            }
            DebugCommand::SetGold { gold } => {
                p.character.gold = gold;
                json!({"gold":gold})
            }
            DebugCommand::SetHp { hp } => {
                if !hp.is_finite() || hp <= 0. {
                    return Err("hp must be above 0; use die to defeat the player.".into());
                }
                let c = &mut p.character;
                c.hp = hp.min(c.max_hp());
                p.dead_time = 0.;
                json!({"hp":c.hp,"maxHp":c.max_hp()})
            }
            DebugCommand::Die => {
                if p.character.hp <= 0. {
                    return Err("The player is already defeated.".into());
                }
                p.character.hp = 0.;
                p.dead_time = 0.;
                p.attack = 0.;
                p.buffs.clear();
                p.stop();
                p.apply_death_penalty();
                self.event("death", &actor, point, 0., false);
                self.save();
                json!({"dead":true})
            }
            DebugCommand::ResetStats => {
                p.character.attributes = Attributes::default();
                let c = &mut p.character;
                c.hp = c.hp.min(c.max_hp());
                json!({"statPoints":c.stat_points()})
            }
            DebugCommand::ResetCooldowns => {
                p.skill_cd.clear();
                p.cooldown = 0.;
                p.dash_cd = 0.;
                p.potion_cd = 0.;
                p.character.potion_ready = 0;
                json!({"cleared":true})
            }
            DebugCommand::SetGodMode { enabled } => {
                self.god_mode = enabled;
                json!({"godMode":enabled})
            }
            DebugCommand::Teleport { zone, x, y } => {
                if zone >= self.maps.len() {
                    return Err(format!("Unknown zone {zone}."));
                }
                if !x.is_finite() || !y.is_finite() {
                    return Err("Teleport needs finite coordinates.".into());
                }
                let mut arrival = Point { x, y };
                self.maps[zone].collide(&mut arrival, PLAYER_RADIUS);
                let time = self.time;
                p.character.zone = zone;
                p.character.x = arrival.x;
                p.character.y = arrival.y;
                p.portal_at = time;
                p.stop();
                p.attack = 0.;
                p.dash = 0.;
                self.separate_enemies();
                json!({"zone":zone,"x":arrival.x,"y":arrival.y})
            }
            DebugCommand::GiveItem {
                item: id,
                quantity,
                force,
            } => {
                let it = item(&id).ok_or_else(|| format!("Unknown item {id}."))?;
                if !(1..=9999).contains(&quantity) {
                    return Err("quantity must be 1-9999.".into());
                }
                let c = &mut p.character;
                if it.kind == "bag" {
                    if c.bags.len() >= 4 {
                        return Err("All four expansion bag slots are filled.".into());
                    }
                    c.bags.push(id.clone());
                } else {
                    if !force && !c.can_collect(&id) {
                        return Err("Bags are full (use force to ignore capacity).".into());
                    }
                    c.add_item(&id, quantity);
                }
                json!({"item":id,"owned":c.quantity(&id),"bags":c.bags,"bagCapacity":c.bag_capacity(),"bagUsed":c.bag_used()})
            }
            DebugCommand::TakeItem { item: id, quantity } => {
                let it = item(&id).ok_or_else(|| format!("Unknown item {id}."))?;
                let c = &mut p.character;
                if it.kind == "bag" {
                    let at = c
                        .bags
                        .iter()
                        .position(|b| *b == id)
                        .ok_or("That bag is not fitted.")?;
                    let removed = c.bags.remove(at);
                    if c.bag_used() > c.bag_capacity() {
                        c.bags.insert(at, removed);
                        return Err("Items would no longer fit without that bag.".into());
                    }
                } else {
                    let spare = c.quantity(&id).saturating_sub(c.equipped_count(it));
                    if quantity == 0 || quantity > spare {
                        return Err(format!(
                            "Only {spare} spare {id} can be taken (worn copies stay)."
                        ));
                    }
                    if let Some(stack) = c.inventory.iter_mut().find(|s| s.item == id) {
                        stack.quantity -= quantity;
                    }
                    c.inventory.retain(|s| s.quantity > 0);
                }
                json!({"item":id,"owned":c.quantity(&id),"bags":c.bags})
            }
            DebugCommand::DropItem { item: id, quantity } => {
                if item(&id).is_none() || quantity == 0 {
                    return Err(format!("Unknown item {id} or zero quantity."));
                }
                let zone = p.character.zone;
                self.item_drop(&actor, zone, point, &id, quantity);
                json!({"dropped":id,"quantity":quantity})
            }
            DebugCommand::Quest { id, action } => {
                let quests: Vec<Quest> = self
                    .maps
                    .iter()
                    .flat_map(|map| map.quests.clone())
                    .collect();
                if !quests.iter().any(|q| q.id == id) {
                    return Err(format!("Unknown quest {id}."));
                }
                let mut finished = vec![];
                let outcome = match action {
                    QuestDebug::Reset => {
                        p.character.quests.retain(|q| q.id != id);
                        Ok(0)
                    }
                    QuestDebug::Accept => {
                        let quest = quests.iter().find(|q| q.id == id).unwrap();
                        let (text, _, changed) = quest_action(&mut p.character, quest, "accept");
                        if changed { Ok(0) } else { Err(text) }
                    }
                    QuestDebug::Complete => complete_quest(&mut p.character, &quests, &id),
                    QuestDebug::Claim => {
                        let quest = quests.iter().find(|q| q.id == id).unwrap();
                        let (text, gained, changed) =
                            quest_action(&mut p.character, quest, "claim");
                        if changed {
                            finished.push(id.clone());
                            Ok(gained)
                        } else {
                            Err(text)
                        }
                    }
                    QuestDebug::Finish => {
                        finish_quest(&mut p.character, &quests, &id, &mut finished)
                    }
                };
                levels = outcome?;
                json!({"quest":p.character.quests.iter().find(|q| q.id == id),"claimed":finished,"levels":levels,"gold":p.character.gold})
            }
            DebugCommand::KillEnemy { id } => {
                let zone = p.character.zone;
                let enemy = self
                    .slimes
                    .get(id)
                    .filter(|s| !s.dead && s.zone == zone)
                    .ok_or("No living enemy with that id in your zone.")?;
                let (hp, kind, level) = (enemy.hp.max(1.), enemy.kind.clone(), enemy.level);
                // The ordinary kill path: XP, quest credit, gold and loot drops all belong to this player.
                self.hit_slime(id, session, hp, false);
                json!({"id":id,"kind":kind,"level":level})
            }
            DebugCommand::RespawnEnemy { id } => {
                let enemy = self.slimes.get_mut(id).ok_or("No enemy with that id.")?;
                if enemy.kind == "big" {
                    return Err("Kings come from the shared timer; use summon_king.".into());
                }
                if !enemy.dead {
                    return Err("That enemy is already alive.".into());
                }
                enemy.respawn = TICK;
                json!({"id":id,"respawning":true})
            }
            DebugCommand::SpawnEnemy { kind, x, y, level } => {
                if kind == "big" {
                    return Err("Kings come from the shared timer; use summon_king.".into());
                }
                if !x.is_finite() || !y.is_finite() {
                    return Err("x and y must be numbers.".into());
                }
                let level = level.unwrap_or_else(|| Slime::default_level(&kind));
                if !(1..=MAX_DEBUG_LEVEL).contains(&level) {
                    return Err(format!("Level must be 1-{MAX_DEBUG_LEVEL}."));
                }
                // Enemies are a fixed set of slots; a spawn moves one of the kind's slots here, so every ordinary rule applies.
                // After it dies it comes back at its own spawn point, not here.
                let id = self
                    .slimes
                    .iter()
                    .filter(|s| s.kind == kind)
                    .min_by_key(|s| (!s.dead, s.id))
                    .map(|s| s.id)
                    .ok_or("No enemy of that kind exists. Kinds: green, blue, pink, yellow, beetle, wisp, spider, wraith, golem.")?;
                let zone = self.players[&session].character.zone;
                let mut enemy = Slime::with_level(
                    id,
                    &SlimeSpawn {
                        x,
                        y,
                        kind: kind.clone(),
                        zone,
                    },
                    level,
                );
                let bodies = self.actor_bodies(zone, None, Some(id));
                let ground =
                    free_actor_position(&self.maps[zone], enemy.point(), enemy.r, &bodies, true)
                        .ok_or("There is no free ground near that spot.")?;
                (enemy.x, enemy.y, enemy.hx, enemy.hy, enemy.goal) =
                    (ground.x, ground.y, ground.x, ground.y, ground);
                self.slimes[id] = enemy;
                json!({"id":id,"kind":kind,"level":level,"zone":zone,"x":ground.x,"y":ground.y})
            }
            DebugCommand::SummonKing => {
                if self.slimes.iter().any(|s| s.kind == "big" && !s.dead) {
                    return Err("A King Slime is already alive.".into());
                }
                self.next_king_spawn = self.time;
                json!({"summoned":true})
            }
        };
        if levels > 0 {
            let point = self.players[&session].character.point();
            self.level_up_event(&actor, point, levels);
        }
        self.save();
        Ok(result)
    }
}

/// Fill every objective of an accepted-or-new quest without claiming it.
fn complete_quest(character: &mut Character, quests: &[Quest], id: &str) -> Result<u32, String> {
    let quest = quests.iter().find(|q| q.id == id).unwrap();
    if !character.quests.iter().any(|q| q.id == id && !q.claimed) {
        let (text, _, changed) = quest_action(character, quest, "accept");
        if !changed {
            return Err(text);
        }
    }
    let progress = character
        .quests
        .iter_mut()
        .find(|q| q.id == id)
        .expect("quest was just accepted");
    progress.counts = quest.objectives.iter().map(|o| o.count).collect();
    Ok(0)
}

/// Accept, fill and claim a quest, finishing any unmet prerequisite chain first. A one-time quest that is already
/// claimed is left alone.
fn finish_quest(
    character: &mut Character,
    quests: &[Quest],
    id: &str,
    finished: &mut Vec<String>,
) -> Result<u32, String> {
    let quest = quests
        .iter()
        .find(|q| q.id == id)
        .ok_or_else(|| format!("Unknown quest {id}."))?;
    let mut levels = 0;
    if let Some(required) = &quest.requires
        && !character
            .quests
            .iter()
            .any(|q| &q.id == required && q.completions > 0)
    {
        levels += finish_quest(character, quests, required, finished)?;
    }
    if character
        .quests
        .iter()
        .any(|q| q.id == id && q.claimed && !quest.repeatable)
    {
        return Ok(levels);
    }
    complete_quest(character, quests, id)?;
    let (text, gained, changed) = quest_action(character, quest, "claim");
    if !changed {
        return Err(text);
    }
    finished.push(id.to_owned());
    Ok(levels + gained)
}
