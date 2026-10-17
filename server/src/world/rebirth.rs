//! Rebirth, the world side (docs/rebirth.md, REBIRTH-SERVER): the refusals that need other state than the character's
//! own, the preview with its confirmation nonce, and the single authoritative `rebirth` action.
use super::*;
use crate::rebirth::REBIRTH_MAX_TIER;

/// Seconds a preview's nonce stays valid.
pub(super) const NONCE_LIFETIME: f64 = 60.;

/// The confirmation a preview hands out. It is tied to the level and rebirth count it was issued for, so a stale or
/// scripted client cannot spend it on a different state.
#[derive(Clone, Debug)]
pub(super) struct Nonce {
    value: String,
    expires: f64,
    level: u32,
    count: u32,
}

impl World {
    /// The drop rate multiplier of the character `id` (the credited hero of a kill, the opener of a chest), 1 when
    /// they are not online. One multiplier reaches each kill, so a party's shared loot is never boosted twice.
    pub(super) fn drop_multiplier_of(&self, id: &str) -> u32 {
        self.online(id).map_or(1, |p| p.character.drop_multiplier())
    }
    /// A gold pile `base` for `id`, with their drop multiplier and then their rebirth gold bonus.
    pub(super) fn pile_for(&self, id: &str, base: u32) -> u32 {
        self.online(id).map_or(base, |p| {
            p.character
                .boosted_gold(base.saturating_mul(p.character.drop_multiplier()))
        })
    }
    /// Why this player cannot be reborn now, or None.
    fn rebirth_blocker(&self, session: u64) -> Option<String> {
        let p = self.players.get(&session)?;
        let c = &p.character;
        if let Some(text) = c.rebirth_blocker() {
            return Some(text);
        }
        let refused = |text: &str| Some(text.to_owned());
        if p.combat_left > 0. {
            return refused("Leave combat before you are reborn.");
        }
        if self.escort_of(&c.id).is_some() {
            return refused("Finish the escort before you are reborn.");
        }
        if self.is_arena_zone(c.zone) || self.pvp_busy(&c.id) {
            return refused("Finish the duel or arena match before you are reborn.");
        }
        if self.is_instance(c.zone) {
            return refused("Leave the dungeon before you are reborn.");
        }
        if self.trade_index(&c.id).is_some() {
            return refused("Finish your trade before you are reborn.");
        }
        None
    }
    fn rebirth_error(&self, session: u64, text: &str) {
        if let Some(p) = self.players.get(&session) {
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
        }
    }
    /// Answers whether a rebirth is possible and what it costs, and issues the nonce `rebirth` needs.
    pub(super) fn rebirth_preview(&mut self, session: u64) {
        let reason = self.rebirth_blocker(session);
        let time = self.time;
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        let c = &p.character;
        let (gear_off, cells_needed) = c.rebirth_gear_cost();
        let reason = reason.or_else(|| {
            (cells_needed > 0).then(|| {
                format!(
                    "Free {cells_needed} bag cells first: your high-level gear goes into the bags."
                )
            })
        });
        p.rebirth_nonce = match reason {
            Some(_) => None,
            None => Some(Nonce {
                value: uuid::Uuid::new_v4().to_string(),
                expires: time + NONCE_LIFETIME,
                level: c.level,
                count: c.rebirth_count(),
            }),
        };
        let _ = p.peer.try_send(json!({
            "type":"rebirthPreview","ok":reason.is_none(),"reason":reason.unwrap_or_default(),
            "level":c.level,"tier":c.rebirth_tier_now(),"maxTier":REBIRTH_MAX_TIER,
            "count":c.rebirth_count(),"tiers":c.rebirth_tiers,
            "gearOff":gear_off,"cellsNeeded":cells_needed,
            "perks":c.rebirth_perks(),"perksAfter":c.rebirth_tier_now().map(|t| c.rebirth_perks_after(t)),
            "nonce":p.rebirth_nonce.as_ref().map(|n| n.value.clone()),"lifetime":NONCE_LIFETIME,
        }));
    }
    /// Rebirths the player if every rule allows it and `nonce` is the live one from their last preview.
    pub(super) fn rebirth(&mut self, session: u64, nonce: &str) {
        if let Some(text) = self.rebirth_blocker(session) {
            return self.rebirth_error(session, &text);
        }
        let spawn = self.maps[0].spawn;
        let time = self.time;
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        let held = p.rebirth_nonce.take();
        let valid = held.as_ref().is_some_and(|n| {
            n.value == nonce
                && n.expires >= time
                && n.level == p.character.level
                && n.count == p.character.rebirth_count()
        });
        if !valid {
            return self.rebirth_error(session, "Ask again to confirm the rebirth.");
        }
        let tier = match p.character.rebirth(spawn) {
            Ok(tier) => tier,
            Err(text) => return self.rebirth_error(session, &text),
        };
        p.stop();
        p.attack = 0.;
        p.buffs.clear();
        let id = p.character.id.clone();
        let count = p.character.rebirth_count();
        let _ = p.peer.try_send(json!({
            "type":"notice","ok":true,
            "text":format!("You are reborn! Tier {tier}, rebirth number {count}. Your journey starts again.")
        }));
        self.event("rebirth", &id, spawn, tier as f64, false);
        self.save();
    }
}

#[cfg(test)]
mod tests {
    use super::super::wyrd_tests::{at, drain, join, place, world};
    use super::*;

    fn nonce_of(rx: &mut mpsc::Receiver<Value>) -> (Value, Option<String>) {
        let packet = drain(rx)
            .into_iter()
            .rev()
            .find(|v| v["type"] == "rebirthPreview")
            .expect("a preview answer");
        let nonce = packet["nonce"].as_str().map(str::to_owned);
        (packet, nonce)
    }
    fn errors(rx: &mut mpsc::Receiver<Value>) -> Vec<String> {
        drain(rx)
            .into_iter()
            .filter(|v| v["type"] == "error")
            .filter_map(|v| v["text"].as_str().map(str::to_owned))
            .collect()
    }
    fn level(w: &mut World, session: u64, level: u32) {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.level = level;
        c.hp = c.max_hp();
    }

    #[test]
    fn the_preview_names_the_tier_and_a_confirmed_rebirth_resets_in_one_save() {
        let mut w = world();
        let (tx, mut rx) = mpsc::channel(4096);
        let token = w
            .join(
                1,
                None,
                Some(Look {
                    class: Class::Warrior,
                    ..Look::default()
                }),
                tx,
            )
            .unwrap()["token"]
            .as_str()
            .unwrap()
            .to_owned();
        level(&mut w, 1, 70);
        w.players.get_mut(&1).unwrap().character.gold = 999;
        drain(&mut rx);
        w.message(1, ClientMessage::RebirthPreview);
        let (packet, nonce) = nonce_of(&mut rx);
        assert_eq!(
            (packet["ok"].as_bool(), packet["tier"].as_u64()),
            (Some(true), Some(3))
        );
        w.message(
            1,
            ClientMessage::Rebirth {
                nonce: nonce.unwrap(),
            },
        );
        let c = &w.players[&1].character;
        assert_eq!(
            (c.level, c.rebirth_tiers, c.gold),
            (1, [0, 0, 1, 0, 0], 999)
        );
        let seen = drain(&mut rx);
        assert!(
            seen.iter()
                .any(|v| v["kind"] == "rebirth" && v["value"] == 3.)
        );
        assert!(
            seen.iter().any(|v| v["type"] == "notice"
                && v["text"].as_str().is_some_and(|t| t.contains("reborn")))
        );
        let snap = w.players[&1].snapshot();
        assert_eq!(snap["reborn"], json!({"count":1,"tier":3}));
        assert_eq!(snap["rebirthTiers"], json!([0, 0, 1, 0, 0]));
        // The save holds it.
        let saved = w.store.load(&token).unwrap().unwrap();
        assert_eq!((saved.level, saved.rebirth_tiers), (1, [0, 0, 1, 0, 0]));
    }

    #[test]
    fn the_nonce_cannot_be_forged_replayed_expired_or_moved_to_another_state() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Mage);
        level(&mut w, 1, 90);
        drain(&mut rx);
        w.message(
            1,
            ClientMessage::Rebirth {
                nonce: "guess".into(),
            },
        );
        assert_eq!(w.players[&1].character.level, 90, "no preview, no rebirth");
        assert!(errors(&mut rx)[0].contains("confirm"));

        w.message(1, ClientMessage::RebirthPreview);
        let (_, nonce) = nonce_of(&mut rx);
        let nonce = nonce.unwrap();
        w.message(
            1,
            ClientMessage::Rebirth {
                nonce: "wrong".into(),
            },
        );
        assert_eq!(w.players[&1].character.level, 90);
        w.message(
            1,
            ClientMessage::Rebirth {
                nonce: nonce.clone(),
            },
        );
        assert_eq!(
            w.players[&1].character.level, 90,
            "a wrong try spends the nonce"
        );

        w.message(1, ClientMessage::RebirthPreview);
        let (_, nonce) = nonce_of(&mut rx);
        let nonce = nonce.unwrap();
        w.time += NONCE_LIFETIME + 1.;
        w.message(1, ClientMessage::Rebirth { nonce });
        assert_eq!(w.players[&1].character.level, 90, "expired");

        w.message(1, ClientMessage::RebirthPreview);
        let (_, nonce) = nonce_of(&mut rx);
        let nonce = nonce.unwrap();
        level(&mut w, 1, 80);
        w.message(
            1,
            ClientMessage::Rebirth {
                nonce: nonce.clone(),
            },
        );
        assert_eq!(w.players[&1].character.level, 80, "issued for level 90");
        level(&mut w, 1, 90);
        w.message(1, ClientMessage::RebirthPreview);
        let (_, nonce) = nonce_of(&mut rx);
        let nonce = nonce.unwrap();
        drain(&mut rx);
        w.message(
            1,
            ClientMessage::Rebirth {
                nonce: nonce.clone(),
            },
        );
        assert_eq!(w.players[&1].character.rebirth_tiers, [0, 0, 0, 0, 1]);
        // Replay: the nonce is spent and the hero is level 1.
        w.message(1, ClientMessage::Rebirth { nonce });
        assert_eq!(w.players[&1].character.rebirth_tiers, [0, 0, 0, 0, 1]);
        assert_eq!(w.players[&1].character.level, 1);
    }

    #[test]
    fn every_refusal_answers_with_its_reason_and_changes_nothing() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let mut rx2 = join(&mut w, 2, Class::Warrior);
        level(&mut w, 1, 55);
        level(&mut w, 2, 55);
        let ask = |w: &mut World, rx: &mut mpsc::Receiver<Value>| {
            let held = w.players[&1].character.level;
            drain(rx);
            w.message(1, ClientMessage::RebirthPreview);
            let (packet, nonce) = nonce_of(rx);
            assert!(nonce.is_none() && packet["ok"] == false);
            // Even a guessed nonce does nothing.
            w.message(1, ClientMessage::Rebirth { nonce: "x".into() });
            assert_eq!(w.players[&1].character.level, held);
            assert_eq!(w.players[&1].character.rebirth_count(), 0);
            packet["reason"].as_str().unwrap().to_owned()
        };

        level(&mut w, 1, 49);
        assert!(ask(&mut w, &mut rx).contains("level 50"));
        level(&mut w, 1, 55);

        w.players.get_mut(&1).unwrap().combat_left = 5.;
        assert!(ask(&mut w, &mut rx).contains("combat"));
        w.players.get_mut(&1).unwrap().combat_left = 0.;

        w.players.get_mut(&1).unwrap().character.mounted = true;
        assert!(ask(&mut w, &mut rx).contains("Dismount"));
        w.players.get_mut(&1).unwrap().character.mounted = false;

        w.players.get_mut(&1).unwrap().character.hp = 0.;
        assert!(ask(&mut w, &mut rx).contains("defeated"));
        level(&mut w, 1, 55);

        let arena = w.maps.iter().position(|m| m.name == "The Arena").unwrap();
        place(&mut w, 1, arena, at(10., 10.));
        let why = ask(&mut w, &mut rx);
        assert!(why.contains("arena"), "{why}");
        let copy = w.instances[0].zone;
        place(&mut w, 1, copy, at(10., 10.));
        assert!(ask(&mut w, &mut rx).contains("dungeon"));
        place(&mut w, 1, 0, at(20., 20.));
        place(&mut w, 2, 0, at(21., 20.));
        level(&mut w, 1, 55);

        let other = w.players[&2].character.id.clone();
        w.message(
            1,
            ClientMessage::Trade {
                command: crate::model::TradeCommand::Request { id: other },
            },
        );
        assert!(
            w.trade_index(&w.players[&1].character.id.clone()).is_some(),
            "a trade is open"
        );
        assert!(ask(&mut w, &mut rx).contains("trade"));
        drain(&mut rx2);
    }

    #[test]
    fn a_legacy_player_snapshot_reports_never_reborn() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Hunter);
        let snap = w.players[&1].snapshot();
        assert_eq!(snap["reborn"], json!({"count":0,"tier":0}));
    }
}
