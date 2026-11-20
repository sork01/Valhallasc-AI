use super::*;
use std::collections::BTreeMap;

impl World {
    pub(super) fn transmogrify(
        &mut self,
        session: u64,
        npc: &str,
        changes: BTreeMap<String, String>,
    ) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let c = &p.character;
        let busy = self.trade_index(&c.id).is_some()
            || self.pvp_busy(&c.id)
            || self.time < p.cutscene_until;
        let valid = c.hp > 0.
            && p.combat_left <= 0.
            && !c.mounted
            && !busy
            && c.spark_travel.is_none()
            && !p.frozen
            && self.maps[c.zone].npcs.iter().any(|n| {
                n.id == npc
                    && n.offers.iter().any(|o| o.id == "transmogrify")
                    && c.point().distance(n.position_at(self.time)) <= 2.8
            });
        let result = if !valid {
            Err("Stand beside a Transmog Master, out of combat and dismounted.")
        } else {
            let mut next = c.clone();
            match next.apply_transmogs(&changes) {
                Err(e) => Err(e),
                Ok(fee) => match self.store.save_many([&next].into_iter()) {
                    Err(e) => {
                        tracing::error!(%e, "transmogrify save failed");
                        Err("Could not save the appearances. Nothing was changed.")
                    }
                    Ok(()) => {
                        let p = self.players.get_mut(&session).unwrap();
                        p.character = next;
                        p.stop();
                        Ok(fee)
                    }
                },
            }
        };
        match result {
            Ok(_) => self.interact(session, npc, None),
            Err(text) => {
                let _ = self.players[&session]
                    .peer
                    .try_send(json!({"type":"error","text":text}));
            }
        }
    }
}

#[cfg(test)]
#[path = "transmog_tests.rs"]
mod tests;
