//! `QUEST-ITEM-DROPS` (docs/quest-items.md). A `bring` quest that asks for a monster material asks for its own quest item instead
//! (`scripts/quest_items.py`, `Item::quest_material`). The monsters that drop the material also drop that item, but only
//! * for a hero who holds the quest, has not claimed it and is still short of the item (what is in the bags and what already lies on the ground
//!   for them counts), and never beyond what is still needed;
//! * at the objective's own `dropChance` (30% to 80%), through the rebirth multiplier like every other drop;
//! * one copy per kill, handed in turn to the party members in range who still need it.
//! Handing the quest in keeps only what another quest still needs (`discard_excess_quest_items`), and `migrate_quest_items` brings old saves in line.
use super::*;

/// The objective that asks for `item` in the maps: its quest and drop chance.
fn objective_for<'a>(maps: &'a [Map], item: &str) -> Option<(&'a Quest, f64)> {
    maps.iter().flat_map(|m| &m.quests).find_map(|q| {
        q.objectives
            .iter()
            .find(|o| o.kind == "bring" && o.target == item)
            .map(|o| (q, o.drop_chance.unwrap_or(0.5)))
    })
}

/// How many of `item` the quests the hero holds (not claimed) ask for in all.
pub(super) fn wanted(c: &Character, maps: &[Map], item: &str) -> u32 {
    c.quests
        .iter()
        .filter(|p| !p.claimed)
        .filter_map(|p| maps.iter().flat_map(|m| &m.quests).find(|q| q.id == p.id))
        .flat_map(|q| &q.objectives)
        .filter(|o| o.kind == "bring" && o.target == item)
        .map(|o| o.count)
        .sum()
}

impl World {
    /// How many more of `item` this hero still has to find: what the quests ask for, less the bags and the drops already on the ground for them.
    pub(super) fn quest_item_short(&self, c: &Character, item: &str) -> u32 {
        let lying: u32 = self
            .drops
            .iter()
            .filter(|d| d.owner == c.id && d.item.as_deref() == Some(item))
            .map(|d| d.quantity.max(1))
            .sum();
        wanted(c, &self.maps, item).saturating_sub(c.quantity(item).saturating_add(lying))
    }

    /// The kill of a `kind` monster at `point`: the quest items of its material fall for the heroes who need them.
    pub(super) fn quest_item_drops(&mut self, kind: &str, zone: usize, point: Point, killer: &str, boost: u32) {
        let material = material(kind);
        let items: Vec<&'static Item> = ITEMS
            .iter()
            .filter(|i| i.quest_material.as_deref() == Some(material))
            .collect();
        if items.is_empty() {
            return;
        }
        let mut group = self.xp_group(killer, zone, point);
        if !group.iter().any(|id| id == killer) {
            group.push(killer.to_owned());
        }
        for item in items {
            let Some((quest, chance)) = objective_for(&self.maps, &item.id).map(|(q, c)| (q.id.clone(), c)) else {
                continue;
            };
            let needs = |w: &World, id: &String| {
                w.players.values().any(|p| {
                    p.merc.is_none()
                        && p.ambient.is_none()
                        && p.guard.is_none()
                        && p.character.id == *id
                        && p.character.quests.iter().any(|q| q.id == quest && !q.claimed)
                        && w.quest_item_short(&p.character, &item.id) > 0
                })
            };
            if !group.iter().any(|id| needs(self, id)) {
                continue;
            }
            for _ in 0..copies(chance, boost, || self.random()) {
                let needers: Vec<String> = group.iter().filter(|id| needs(self, id)).cloned().collect();
                if needers.is_empty() {
                    break;
                }
                let key = format!("quest-item:{}", item.id);
                let turn = self.loot_turns.entry(key).or_insert(0);
                let pick = needers[*turn % needers.len()].clone();
                *turn += 1;
                self.item_drop(&pick, zone, point, &item.id, 1);
            }
        }
    }
}

/// After a claim: whatever is left of a quest item this quest asked for, beyond what another held quest still asks for, goes (no gold).
/// Returns (item name, count) for each discarded stack.
pub(super) fn discard_excess_quest_items(c: &mut Character, quest: &Quest, maps: &[Map]) -> Vec<(String, u32)> {
    let mut gone = vec![];
    for o in quest.objectives.iter().filter(|o| o.kind == "bring") {
        let Some(i) = item(&o.target).filter(|i| is_quest_item(i) && i.quest_material.is_some()) else {
            continue;
        };
        let keep = wanted(c, maps, &o.target);
        let have = c.quantity(&o.target);
        if have > keep {
            c.consume_item(&o.target, have - keep);
            gone.push((i.name.clone(), have - keep));
        }
    }
    gone
}

/// One-way clean-up of an old save (`Character::quest_items_version` 0 -> 1): the progress a hero had in a remapped `bring` quest moves to the new quest
/// item (up to the count, from the ordinary material they carry), then quest items no held quest needs go, and the rest are cut back to the need.
/// Returns what was converted and removed, for the log.
pub(super) fn migrate_quest_items(c: &mut Character, maps: &[Map]) -> (u32, u32) {
    if c.quest_items_version >= 1 {
        return (0, 0);
    }
    c.quest_items_version = 1;
    let (mut converted, mut removed) = (0, 0);
    let held: Vec<Quest> = c
        .quests
        .iter()
        .filter(|p| !p.claimed)
        .filter_map(|p| maps.iter().flat_map(|m| &m.quests).find(|q| q.id == p.id))
        .cloned()
        .collect();
    for q in &held {
        for o in q.objectives.iter().filter(|o| o.kind == "bring") {
            let Some(from) = item(&o.target).and_then(|i| i.quest_material.as_deref()) else {
                continue;
            };
            let missing = o.count.saturating_sub(c.quantity(&o.target));
            let take = missing.min(c.quantity(from));
            if take > 0 && c.consume_item(from, take) {
                c.add_item(&o.target, take);
                converted += take;
            }
        }
    }
    // Quest items nobody asks for any more (and the bank's: a quest item cannot be banked) are not kept.
    let stray: Vec<String> = c
        .inventory
        .iter()
        .filter(|s| item(&s.item).is_some_and(is_quest_item) && item(&s.item).is_some_and(|i| i.quest_material.is_some()))
        .map(|s| s.item.clone())
        .collect();
    for id in stray {
        let keep = wanted(c, maps, &id);
        let have = c.quantity(&id);
        if have > keep {
            c.consume_item(&id, have - keep);
            removed += have - keep;
        }
    }
    let banked: Vec<String> = c
        .bank
        .items
        .iter()
        .filter(|s| item(&s.item).is_some_and(is_quest_item))
        .map(|s| s.item.clone())
        .collect();
    for id in banked {
        c.bank.items.retain(|s| s.item != id);
        c.bank.gear.retain(|g| g.item != id);
    }
    (converted, removed)
}
