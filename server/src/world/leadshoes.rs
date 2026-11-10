//! Lead shoes: a hero under water (a zone whose theme is in `UNDERWATER_THEMES`) is shod in lead, so the sea floor is
//! walked, not swum. It is an overlay, not an item: no slot, nothing in the bag, no stat changes (the hero keeps exactly the
//! stats of the gear already worn), and nothing saved, since `Player::shoed` is derived from the zone every tick (a hero who
//! logs in under water is shod on the first tick). Because it is no slot, there is no way to take the shoes off; they leave
//! when the hero surfaces. Going down announces "Equipping lead shoes" once and surfacing "Removing lead shoes".
use super::*;

impl World {
    pub(super) fn update_lead_shoes(&mut self) {
        let maps = &self.maps;
        for p in self.players.values_mut() {
            if p.merc.is_some() || p.ambient.is_some() {
                continue;
            }
            let under = maps.get(p.character.zone).is_some_and(Map::underwater);
            if under == p.shoed {
                continue;
            }
            p.shoed = under;
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
}
