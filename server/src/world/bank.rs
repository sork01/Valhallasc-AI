//! The bank's requests (docs/bank.md). The rules are in `crate::bank`; this checks who may ask and where, applies a
//! request to a copy of the character, writes that copy to the store, and only then makes it the live character, so
//! a refused or failed request changes nothing and a successful one is saved before it can be seen. The world
//! handles one message at a time, so two browsers cannot both take the same item.
use super::*;
use crate::bank::BANK_RANGE;

pub(super) enum BankRequest {
    Open,
    Deposit {
        item: String,
        quantity: u32,
        copy: Option<u64>,
    },
    Withdraw {
        item: String,
        quantity: u32,
        copy: Option<u64>,
    },
    Gold {
        deposit: bool,
        amount: u32,
    },
    Expand,
}

impl World {
    pub(super) fn bank(&mut self, session: u64, npc_id: &str, request: BankRequest) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        let c = &p.character;
        let refusal = if c.hp <= 0. {
            Some("You cannot use the bank while defeated.")
        } else if p.combat_left > 0. {
            Some("Leave combat before using the bank.")
        } else if c.mounted {
            Some("Dismount first.")
        } else if c.spark_travel.is_some() {
            Some("You cannot use the bank while travelling.")
        } else if !self.maps[c.zone].npcs.iter().any(|n| {
            n.id == npc_id
                && n.offers.iter().any(|o| o.id == "bank")
                && c.point().distance(n.position_at(self.time)) <= BANK_RANGE
        }) {
            Some("Walk closer to the banker.")
        } else {
            None
        };
        if let Some(text) = refusal {
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
            return;
        }
        let mut next = p.character.clone();
        let name = |id: &str| item(id).map_or("item", |i| i.name.as_str()).to_owned();
        let done: Result<String, &'static str> = match request {
            BankRequest::Open => Ok(String::new()),
            BankRequest::Deposit {
                item,
                quantity,
                copy,
            } => next
                .bank_deposit(&item, quantity, copy)
                .map(|()| format!("Stored {quantity} {}.", name(&item))),
            BankRequest::Withdraw {
                item,
                quantity,
                copy,
            } => next
                .bank_withdraw(&item, quantity, copy)
                .map(|()| format!("Took {quantity} {}.", name(&item))),
            BankRequest::Gold { deposit, amount } => next.bank_gold(deposit, amount).map(|()| {
                if deposit {
                    format!("Stored {amount} gold.")
                } else {
                    format!("Took {amount} gold.")
                }
            }),
            BankRequest::Expand => next
                .bank_expand()
                .map(|cells| format!("The bank now holds {cells} cells.")),
        };
        let (notice, ok) = match done {
            Err(text) => (text.to_owned(), false),
            Ok(notice) if next.bank == p.character.bank => (notice, true),
            Ok(notice) => match self.store.save_many([&next].into_iter()) {
                Ok(()) => {
                    p.character = next;
                    (notice, true)
                }
                Err(e) => {
                    tracing::error!(%e, "bank request could not be saved; nothing was moved");
                    (
                        "The bank could not save that. Nothing was moved.".to_owned(),
                        false,
                    )
                }
            },
        };
        let c = &p.character;
        let _ = p.peer.try_send(json!({"type":"bank","npc":npc_id,"ok":ok,"notice":notice,
            "bank":c.bank.view(),"gold":c.gold,"inventory":c.inventory,"gearInstances":c.gear_instances,
            "equipment":c.equipment,"bags":c.bags,"bagCapacity":c.bag_capacity()}));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const PIECE: &str = "warrior_weapon_sword_l5_gray";
    fn world() -> World {
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
    }
    /// A world with one player (session 1) standing beside a banker, and the player's token.
    fn at_the_bank() -> (World, mpsc::Receiver<Value>, String) {
        let mut w = world();
        let (tx, rx) = mpsc::channel(512);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let (x, y) = {
            let c = &w.players[&1].character;
            (c.x, c.y)
        };
        w.maps[0].npcs.push(
            serde_json::from_value(json!({"id":"test_banker","name":"Test Banker","role":"banker",
                "x":x,"y":y,"dialogue":"Welcome.","offers":[{"id":"bank","label":"Bank","cost":0}]}))
            .unwrap(),
        );
        (w, rx, token)
    }
    fn send(w: &mut World, msg: ClientMessage) {
        w.message(1, msg);
    }
    fn deposit(w: &mut World, item: &str, quantity: u32) {
        send(
            w,
            ClientMessage::BankDeposit {
                npc: "test_banker".into(),
                item: item.into(),
                quantity,
                copy: None,
            },
        );
    }
    fn withdraw(w: &mut World, item: &str, quantity: u32) {
        send(
            w,
            ClientMessage::BankWithdraw {
                npc: "test_banker".into(),
                item: item.into(),
                quantity,
                copy: None,
            },
        );
    }
    /// The last packet of a type, with the others drained.
    fn last(rx: &mut mpsc::Receiver<Value>, kind: &str) -> Value {
        std::iter::from_fn(|| rx.try_recv().ok())
            .filter(|v| v["type"] == kind)
            .last()
            .unwrap_or(Value::Null)
    }
    fn state(w: &World) -> String {
        serde_json::to_string(&w.players[&1].character).unwrap()
    }

    #[test]
    fn a_stack_gold_and_an_expansion_go_through_the_banker_and_are_saved_before_they_are_seen() {
        let (mut w, mut rx, token) = at_the_bank();
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.add_item("slime_gel", 10);
            c.gold = 60_000;
        }
        deposit(&mut w, "slime_gel", 4);
        let reply = last(&mut rx, "bank");
        assert_eq!(reply["ok"], true, "{reply}");
        assert_eq!(reply["bank"]["items"][0]["quantity"], 4);
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 6);
        assert_eq!(
            w.store
                .load(&token)
                .unwrap()
                .unwrap()
                .bank
                .quantity("slime_gel"),
            4
        );
        send(
            &mut w,
            ClientMessage::BankGold {
                npc: "test_banker".into(),
                deposit: true,
                amount: 1_500,
            },
        );
        send(
            &mut w,
            ClientMessage::BankExpand {
                npc: "test_banker".into(),
            },
        );
        let reply = last(&mut rx, "bank");
        assert_eq!(reply["bank"]["capacity"], 60);
        assert_eq!(reply["bank"]["gold"], 1_500);
        assert_eq!(reply["gold"], 60_000 - 1_500 - 10_000);
        withdraw(&mut w, "slime_gel", 4);
        send(
            &mut w,
            ClientMessage::BankGold {
                npc: "test_banker".into(),
                deposit: false,
                amount: 1_500,
            },
        );
        let saved = w.store.load(&token).unwrap().unwrap();
        assert!(saved.bank.items.is_empty());
        assert_eq!(
            (saved.gold, saved.bank.gold, saved.bank.expansions),
            (50_000, 0, 1)
        );
        assert_eq!(saved.quantity("slime_gel"), 10);
        send(
            &mut w,
            ClientMessage::BankOpen {
                npc: "test_banker".into(),
            },
        );
        assert_eq!(last(&mut rx, "bank")["ok"], true);
    }
    #[test]
    fn a_gear_copy_with_its_refinement_survives_the_trip_through_the_messages() {
        let (mut w, mut rx, token) = at_the_bank();
        let fancy = {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.add_item(PIECE, 2);
            c.materialize_gear_instances();
            let g = c
                .gear_instances
                .iter_mut()
                .filter(|g| g.item == PIECE)
                .last()
                .unwrap();
            g.rarity = "epic".into();
            g.rank = 4;
            g.rolled_stats.agility = 9;
            g.clone()
        };
        send(
            &mut w,
            ClientMessage::BankDeposit {
                npc: "test_banker".into(),
                item: PIECE.into(),
                quantity: 1,
                copy: Some(fancy.id),
            },
        );
        let reply = last(&mut rx, "bank");
        assert_eq!(reply["bank"]["gear"][0]["rank"], 4, "{reply}");
        let saved = w.store.load(&token).unwrap().unwrap();
        assert_eq!(saved.bank.gear, vec![fancy.clone()]);
        withdraw(&mut w, PIECE, 1);
        let c = &w.players[&1].character;
        let back = c.gear_instances.last().unwrap();
        assert_eq!(
            (back.rarity.as_str(), back.rank, back.rolled_stats.agility),
            ("epic", 4, 9)
        );
        assert_ne!(back.id, fancy.id);
        assert_eq!(c.quantity(PIECE), 2);
    }
    #[test]
    fn nothing_changes_out_of_range_in_another_zone_defeated_in_combat_mounted_or_at_the_wrong_npc()
    {
        let (mut w, mut rx, _) = at_the_bank();
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item("slime_gel", 3);
        let before = state(&w);
        let reset = |w: &mut World| {
            let p = w.players.get_mut(&1).unwrap();
            p.character.hp = p.character.max_hp();
            p.combat_left = 0.;
            p.character.mounted = false;
        };
        let moved = |w: &mut World| w.players.get_mut(&1).unwrap().character.x += 3.;
        moved(&mut w);
        deposit(&mut w, "slime_gel", 1);
        w.players.get_mut(&1).unwrap().character.x -= 3.;
        send(
            &mut w,
            ClientMessage::BankDeposit {
                npc: "guide".into(),
                item: "slime_gel".into(),
                quantity: 1,
                copy: None,
            },
        );
        w.players.get_mut(&1).unwrap().character.zone = 1;
        deposit(&mut w, "slime_gel", 1);
        w.players.get_mut(&1).unwrap().character.zone = 0;
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        deposit(&mut w, "slime_gel", 1);
        reset(&mut w);
        w.players.get_mut(&1).unwrap().combat_left = 5.;
        deposit(&mut w, "slime_gel", 1);
        reset(&mut w);
        w.players.get_mut(&1).unwrap().character.mounted = true;
        deposit(&mut w, "slime_gel", 1);
        w.players.get_mut(&1).unwrap().character.mounted = false;
        let after = state(&w);
        assert_eq!(after, before);
        let errors: Vec<_> = std::iter::from_fn(|| rx.try_recv().ok())
            .filter(|v| v["type"] == "error")
            .map(|v| v["text"].as_str().unwrap().to_owned())
            .collect();
        assert!(errors.iter().any(|t| t.contains("closer")), "{errors:?}");
        assert!(errors.iter().any(|t| t.contains("defeated")), "{errors:?}");
        assert!(errors.iter().any(|t| t.contains("combat")), "{errors:?}");
        assert!(errors.iter().any(|t| t.contains("Dismount")), "{errors:?}");
        // And it works again once the reasons are gone.
        deposit(&mut w, "slime_gel", 1);
        assert_eq!(w.players[&1].character.bank.quantity("slime_gel"), 1);
    }
    #[test]
    fn a_refused_request_answers_with_the_unchanged_bank_and_a_double_request_moves_the_item_once()
    {
        let (mut w, mut rx, _) = at_the_bank();
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item("slime_gel", 1);
        deposit(&mut w, "slime_gel", 1);
        deposit(&mut w, "slime_gel", 1);
        let replies: Vec<_> = std::iter::from_fn(|| rx.try_recv().ok())
            .filter(|v| v["type"] == "bank")
            .collect();
        assert_eq!(replies.len(), 2);
        assert_eq!(
            (replies[0]["ok"].clone(), replies[1]["ok"].clone()),
            (json!(true), json!(false))
        );
        assert_eq!(replies[1]["bank"]["items"][0]["quantity"], 1);
        withdraw(&mut w, "slime_gel", 1);
        withdraw(&mut w, "slime_gel", 1);
        let c = &w.players[&1].character;
        assert_eq!(
            (c.quantity("slime_gel"), c.bank.quantity("slime_gel")),
            (1, 0)
        );
    }
    #[test]
    fn game_master_gear_and_worn_pieces_stay_out_and_a_legacy_banker_offer_is_harmless() {
        let (mut w, _rx, _) = at_the_bank();
        let gm = crate::items::GM_GEAR[0];
        w.players.get_mut(&1).unwrap().character.add_item(gm, 1);
        let worn = {
            let c = &w.players[&1].character;
            let (_, weapon) = c.gear();
            crate::items::equipment(c.look.class, "weapon", weapon)
                .unwrap()
                .id
                .clone()
        };
        let before = state(&w);
        deposit(&mut w, gm, 1);
        deposit(&mut w, &worn, 1);
        assert_eq!(state(&w), before);
        // Talking to the banker with the bank offer id does nothing but point at the window.
        w.time += 1.;
        w.interact(1, "test_banker", Some("bank"));
        assert_eq!(state(&w), before);
    }
    #[test]
    fn a_bank_survives_a_reload_and_a_long_random_run_loses_nothing() {
        let (mut w, _rx, token) = at_the_bank();
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.gold = 5_000;
            for (n, id) in ["slime_gel", "slime_gel", PIECE].iter().enumerate() {
                c.add_item(id, 3 + n as u32);
            }
        }
        let total = |w: &World| {
            let c = &w.players[&1].character;
            (
                c.quantity("slime_gel") + c.bank.quantity("slime_gel"),
                c.quantity(PIECE) + c.bank.quantity(PIECE),
                c.gold + c.bank.gold,
            )
        };
        let before = total(&w);
        let mut seed = 0x2545f4914f6cdd1d_u64;
        let mut next = move || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            seed
        };
        for _ in 0..400 {
            let id = ["slime_gel", PIECE][(next() % 2) as usize];
            let n = (next() % 6) as u32;
            match next() % 5 {
                0 | 1 => deposit(&mut w, id, n),
                2 | 3 => withdraw(&mut w, id, n),
                _ => send(
                    &mut w,
                    ClientMessage::BankGold {
                        npc: "test_banker".into(),
                        deposit: next() % 2 == 0,
                        amount: (next() % 2_000) as u32,
                    },
                ),
            }
            assert_eq!(total(&w), before);
        }
        let live = w.players[&1].character.bank.clone();
        assert_eq!(w.store.load(&token).unwrap().unwrap().bank, live);
        let c = &w.players[&1].character;
        let copies =
            c.bank.gear.len() + c.gear_instances.iter().filter(|g| g.item == PIECE).count();
        assert!(copies <= (c.quantity(PIECE) + c.bank.quantity(PIECE)) as usize);
    }
}
