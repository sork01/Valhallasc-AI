//! Seasonal expiration happens in real time, including during an open menu.
use super::*;
impl World {
    pub(super) fn update_seasonal(&mut self) {
        if self.time < self.seasonal.next_check {
            return;
        }
        self.seasonal.next_check = self.time + 1.;
        let active = self.seasonal.active();
        self.seasonal.cached = active.clone();
        let mut changed = false;
        for p in self.players.values_mut() {
            if crate::seasonal::sync_character(&mut p.character, &active) {
                changed = true;
                if p.merc.is_none() && p.ambient.is_none() {
                    let _=p.peer.try_send(json!({"type":"system","text":"The festival has ended. Unfinished seasonal quests have been retired; completed rewards are kept."}));
                }
            }
        }
        if changed {
            self.save();
        }
    }
}
