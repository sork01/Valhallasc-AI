//! The signs before the final bosses (docs/boss-mechanics.md, `BOSSMECH-SIGN-ENGINE`). The data and its rules are in
//! `crate::bosssign`; this file puts a sign into a dungeon's snapshot and answers a hero who reads it.
//!
//! A sign stands in a dungeon whose final boss has a mechanic in the live table, so the words never explain a fight
//! that is not there. Its text leaves the server only in the answer to `sign_read`.
use super::*;
use crate::bosssign::{self, READ_RANGE};

impl World {
    /// The sign standing in `zone` (a dungeon or any copy of it): the boss kind it is keyed by and its data.
    pub(super) fn sign_in(&self, zone: usize) -> Option<(&str, &bosssign::SignDef)> {
        let kind = self.maps[zone].final_boss.as_str();
        if kind.is_empty() || !self.boss.table.contains_key(kind) {
            return None;
        }
        self.signs.get_key_value(kind).map(|(k, v)| (k.as_str(), v))
    }
    /// What the snapshot says about the sign: where it stands and what it is called. Nothing it says.
    pub(super) fn signs_view(&self, zone: usize) -> Vec<Value> {
        self.sign_in(zone)
            .map(|(kind, def)| json!({"id":kind,"x":def.x,"y":def.y,"title":def.title}))
            .into_iter()
            .collect()
    }
    /// A hero reads the sign: the answer carries the whole text, or an error says why not.
    pub(super) fn sign_read(&mut self, session: u64, id: &str) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let answer = match self
            .sign_in(p.character.zone)
            .filter(|(kind, _)| *kind == id)
        {
            None => Err("There is no sign to read here."),
            Some((_, def))
                if p.character.hp <= 0.
                    || p.character.point().distance(Point { x: def.x, y: def.y }) > READ_RANGE =>
            {
                Err("Walk closer to read this sign.")
            }
            Some((kind, def)) => Ok(
                json!({"type":"sign","sign":kind,"title":def.title,"what":def.what,
                "todo":def.todo,"tip":def.tip,"colors":def.colors}),
            ),
        };
        let p = self.players.get_mut(&session).unwrap();
        match answer {
            Ok(answer) => {
                p.stop();
                p.attack = 0.;
                let _ = p.peer.try_send(answer);
            }
            Err(text) => {
                let _ = p.peer.try_send(json!({"type":"error","text":text}));
            }
        }
    }
}
