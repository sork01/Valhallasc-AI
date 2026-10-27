//! Authoritative quest abandonment from anywhere in the journal.
use super::*;

impl World {
    pub(super) fn abandon_quest(&mut self, session: u64, id: &str) {
        let Some(quest) = self
            .maps
            .iter()
            .flat_map(|m| &m.quests)
            .find(|q| q.id == id)
            .cloned()
        else {
            return;
        };
        let p = self.players.get_mut(&session).unwrap();
        let Some(i) = p
            .character
            .quests
            .iter()
            .position(|q| q.id == id && !q.claimed)
        else {
            return;
        };
        // Keep repeatable completion history: dropping a new bounty cannot revoke old unlocks.
        if p.character.quests[i].completions > 0 {
            p.character.quests[i].claimed = true;
            p.character.quests[i].counts.clear();
        } else {
            p.character.quests.remove(i);
        }
        if !p.character.abandoned_quests.iter().any(|q| q == id) {
            p.character.abandoned_quests.push(id.to_owned());
        }
        let owner = p.character.id.clone();
        let _ = p.peer.try_send(json!({"type":"notice","ok":true,"text":format!("Quest abandoned: {}. You can take it again from its questgiver.", quest.title)}));
        if quest.gauntlet_level().is_some() {
            self.gauntlet_abort(session, "The quest was abandoned.");
        }
        if let Some(escort) = self.escort_of(&owner).filter(|s| {
            self.players[s]
                .escort
                .as_ref()
                .is_some_and(|e| e.quest == id)
        }) {
            self.remove_escort(escort);
        }
        self.empty_seat.cancel(session, id);
        if quest.objectives.iter().any(|o| o.kind == "hold") {
            self.hold.ticks.remove(&session);
        }
        self.chime.cancel_quest(session, &quest, &self.maps);
        // Quest-bound hires end through the ordinary contract checks on the next tick.
        self.save();
    }
}
