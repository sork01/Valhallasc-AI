//! Lead shoes: a hero under water (a zone whose theme is in `UNDERWATER_THEMES`) is shod in lead, so the sea floor is
//! walked, not swum. It is an overlay, not an item: no slot, nothing in the bag, no stat changes (the hero keeps exactly the
//! stats of the gear already worn), and nothing saved, since `Player::shoed` is derived from the zone every tick (a hero who
//! logs in under water is shod on the first tick). Because it is no slot, there is no way to take the shoes off; they leave
//! when the hero surfaces. Going down announces "Equipping lead shoes" once and surfacing "Removing lead shoes", unless the
//! crossing plays its cutscene (`world/cutscene.rs`), whose captions say the same.
use super::cutscene::Env;
use super::*;

impl World {
    pub(super) fn update_lead_shoes(&mut self) {
        let sessions: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.merc.is_none() && p.ambient.is_none() && p.guard.is_none())
            .map(|(s, _)| *s)
            .collect();
        let mut changed = false;
        for session in sessions {
            let Some(env) = self
                .players
                .get(&session)
                .and_then(|p| self.maps.get(p.character.zone))
                .map(Env::of)
            else {
                continue;
            };
            let scenes = self.crossing_scenes(session, env);
            changed |= !scenes.is_empty();
            let under = env == Env::Sea;
            let Some(p) = self.players.get_mut(&session) else {
                continue;
            };
            if under == p.shoed {
                continue;
            }
            p.shoed = under;
            let covered = scenes.contains(&if under { "dive" } else { "surface" });
            if !covered {
                let text = if under {
                    "Equipping lead shoes"
                } else {
                    "Removing lead shoes"
                };
                let _ = p
                    .peer
                    .try_send(json!({"type":"announce","kind":"info","text":text}));
            }
        }
        if changed {
            self.save();
        }
    }
}
