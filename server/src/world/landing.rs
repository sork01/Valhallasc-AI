//! Greenmeadow's landing dock (zone shapes pilot; scripts/greenmeadow_dock.py). A new character starts on the pier beside
//! the ship. The moment they step off it, the landing quest finds them and points them to Wren, who gives the first
//! quests. Characters made before the dock existed never get it: only creation sets `Character::landing`.

use super::*;

impl World {
    /// Where a brand-new character appears: the dock when zone 0 has one, else the old spawn.
    pub(super) fn newcomer_start(&self) -> Point {
        self.maps[0]
            .dock
            .as_ref()
            .map_or(self.maps[0].spawn, |d| d.start)
    }
    /// Marks a just-created character as arriving by ship (only when zone 0 has a dock to arrive on).
    pub(super) fn arrive(&self, mut c: Character) -> Character {
        c.landing = self.landings && self.maps[0].dock.is_some();
        c
    }
}

/// Grants the landing quests once the character stands anywhere but on the dock (another zone counts too): the dock's own
/// quest first, then every other zone-0 quest marked `landing` (the direction to the Empty Seat's first chapter). Returns
/// the titles that arrived now, the dock's quest first. Quests already held or abandoned are skipped.
pub(super) fn step_off(c: &mut Character, maps: &[Map]) -> Vec<String> {
    let mut arrived = vec![];
    if !c.landing {
        return arrived;
    }
    let Some(dock) = maps[0].dock.as_ref() else {
        return arrived;
    };
    if c.zone == 0 && dock.contains(c.point()) {
        return arrived;
    }
    c.landing = false;
    let first = maps[0].quests.iter().filter(|q| q.id == dock.quest);
    let rest = maps[0]
        .quests
        .iter()
        .filter(|q| q.landing && q.id != dock.quest);
    for quest in first.chain(rest) {
        if c.quests.iter().any(|q| q.id == quest.id) || c.abandoned_quests.contains(&quest.id) {
            continue;
        }
        c.quests.push(QuestProgress {
            id: quest.id.clone(),
            counts: vec![0; quest.objectives.len()],
            claimed: false,
            completions: 0,
        });
        arrived.push(quest.title.clone());
    }
    arrived
}

/// The skipper's welcome: once per connection, a moment after a hero who arrived by ship appears on the dock.
pub(super) fn greeting(p: &mut Player, maps: &[Map]) -> Option<(String, String)> {
    let c = &p.character;
    if !c.landing || p.greet_in <= 0. || c.zone != 0 {
        return None;
    }
    let dock = maps[0].dock.as_ref()?;
    if !dock.contains(c.point()) {
        return None;
    }
    p.greet_in -= TICK;
    if p.greet_in > 0. {
        return None;
    }
    Some((dock.greeter.clone()?, dock.greeting.clone()?))
}
