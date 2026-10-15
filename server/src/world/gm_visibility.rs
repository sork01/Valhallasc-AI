//! Transient GM visibility. Only a server-verified GM character can change it.
use super::*;

impl World {
    pub(super) fn set_visibility(&mut self, session: u64, mode: &str) -> Result<Value, String> {
        let p = self.players.get(&session).ok_or("Unknown session.")?;
        if !p.character.gm {
            return Err("Test commands are disabled on this server.".into());
        }
        let currently_hidden = p.is_hidden();
        let should_hide = match mode {
            "query" => return Ok(json!({"hidden":currently_hidden})),
            "on" => false,
            "off" => true,
            "toggle" => !currently_hidden,
            _ => return Err("Use /vis, /vis on, /vis off or /vis toggle.".into()),
        };
        if should_hide && (self.is_arena_zone(p.character.zone) || self.pvp_busy(&p.character.id)) {
            return Err("Leave the arena or duel before hiding.".into());
        }
        if should_hide && !p.hidden {
            let (id, name, friends) = (
                p.character.id.clone(),
                p.character.look.name.clone(),
                p.character.friends.clone(),
            );
            if self.party_index(&id).is_some() {
                self.social(session, SocialCommand::PartyLeave);
            }
            self.trade_left(&id);
            self.pvp_left(&id);
            let p = self.players.get_mut(&session).unwrap();
            p.hidden = true;
            p.pvp_flag = false;
            self.social_left(&id, &name, &friends);
        } else if !should_hide && currently_hidden {
            let p = self.players.get_mut(&session).unwrap();
            p.hidden = false;
            p.visible_zone = p.character.zone;
            let (id, name, friends) = (
                p.character.id.clone(),
                p.character.look.name.clone(),
                p.character.friends.clone(),
            );
            self.social_joined(&id, &name, &friends);
        }
        Ok(json!({"hidden":self.players[&session].is_hidden()}))
    }

    pub(super) fn hide_gms_after_zone_change(&mut self) {
        let changed: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.character.gm && !p.hidden && p.character.zone != p.visible_zone)
            .map(|(session, _)| *session)
            .collect();
        for session in changed {
            let zone = self.players[&session].character.zone;
            if self.is_arena_zone(zone) {
                self.players.get_mut(&session).unwrap().visible_zone = zone;
                continue;
            }
            let id = self.players[&session].character.id.clone();
            self.pvp_left(&id);
            let _ = self.set_visibility(session, "off");
        }
    }
}
