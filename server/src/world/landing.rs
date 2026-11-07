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
        c.landing = self.maps[0].dock.is_some();
        c
    }
}

/// Grants the landing quest once the character stands anywhere but on the dock (another zone counts too). Returns the
/// quest's title when it arrived now. A character who already holds it, or abandoned it, is only un-flagged.
pub(super) fn step_off(c: &mut Character, maps: &[Map]) -> Option<String> {
    if !c.landing {
        return None;
    }
    let dock = maps[0].dock.as_ref()?;
    if c.zone == 0 && dock.contains(c.point()) {
        return None;
    }
    c.landing = false;
    let quest = maps[0].quests.iter().find(|q| q.id == dock.quest)?;
    if c.quests.iter().any(|q| q.id == quest.id) || c.abandoned_quests.contains(&quest.id) {
        return None;
    }
    c.quests.push(QuestProgress {
        id: quest.id.clone(),
        counts: vec![0; quest.objectives.len()],
        claimed: false,
        completions: 0,
    });
    Some(quest.title.clone())
}
