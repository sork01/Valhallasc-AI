//! Short-lived, two-player exchanges. Offers never reserve inventory; the final confirmation validates both
//! complete character states and writes them in one SQLite transaction before publishing either result.
use super::*;

const TRADE_RANGE: f64 = 4.0;
const REQUEST_LIFETIME: f64 = 30.0;
const OPEN_LIFETIME: f64 = 120.0;
const MAX_OFFER_STACKS: usize = 12;

#[derive(Clone, Debug, Default)]
struct Offer {
    items: Vec<ItemStack>,
    gold: u32,
    ready: bool,
}
#[derive(Clone, Debug)]
pub(super) struct Trade {
    from: String,
    to: String,
    accepted: bool,
    expires: f64,
    offers: [Offer; 2],
}
impl Trade {
    fn side(&self, id: &str) -> Option<usize> {
        if self.from == id {
            Some(0)
        } else if self.to == id {
            Some(1)
        } else {
            None
        }
    }
    fn other(&self, id: &str) -> &str {
        if self.from == id {
            &self.to
        } else {
            &self.from
        }
    }
}

impl World {
    pub(super) fn trade_index(&self, id: &str) -> Option<usize> {
        self.trades.iter().position(|t| t.side(id).is_some())
    }
    fn trade_pair_valid(&self, a: &str, b: &str) -> Result<(), String> {
        self.trade_pair_checks(a, b, false)
    }
    /// `adventurer_ok` lets an adventurer pass, for the one request that they then decline.
    fn trade_pair_checks(&self, a: &str, b: &str, adventurer_ok: bool) -> Result<(), String> {
        let left = self.online(a).ok_or("A player went offline.")?;
        let right = self.online(b).ok_or("A player went offline.")?;
        if [left, right].iter().any(|p| {
            p.merc.is_some()
                || (p.ambient.is_some() && !adventurer_ok)
                || p.is_hidden()
                || p.character.hp <= 0.
                || p.character.spark_travel.is_some()
        }) {
            return Err("Both players must be alive and available to trade.".into());
        }
        let x = &left.character;
        let y = &right.character;
        if x.zone != y.zone || (x.x - y.x).hypot(x.y - y.y) > TRADE_RANGE {
            return Err("Move within four steps of each other to trade.".into());
        }
        Ok(())
    }
    fn push_trade(&self, index: usize) {
        let t = &self.trades[index];
        for (id, side) in [(&t.from, 0), (&t.to, 1)] {
            if let Some(p) = self.online(id) {
                let other = t.other(id);
                let packet = json!({"type":"trade","state":if t.accepted { "open" } else if side == 0 { "pending" } else { "request" },
                    "partner":{"id":other,"name":self.name_of(other)},"mine":{"items":t.offers[side].items,"gold":t.offers[side].gold,"ready":t.offers[side].ready},
                    "theirs":{"items":t.offers[1-side].items,"gold":t.offers[1-side].gold,"ready":t.offers[1-side].ready},
                    "left":(t.expires-self.time).max(0.)});
                let _ = p.peer.try_send(packet);
            }
        }
    }
    fn close_trade(&mut self, index: usize, text: &str, completed: bool) {
        let trade = self.trades.remove(index);
        for id in [&trade.from, &trade.to] {
            if let Some(p) = self.online(id) {
                let _ = p.peer.try_send(json!({"type":"trade","state":if completed { "complete" } else { "closed" },"text":text}));
            }
            self.tell(id, text, completed);
        }
    }
    pub(super) fn trade_left(&mut self, id: &str) {
        if let Some(i) = self.trade_index(id) {
            self.close_trade(i, "Trade ended because a player disconnected.", false);
        }
    }
    pub(super) fn update_trades(&mut self) {
        for i in (0..self.trades.len()).rev() {
            let t = &self.trades[i];
            let reason = if t.expires <= self.time {
                Some("Trade request or offer expired.".to_owned())
            } else {
                self.trade_pair_valid(&t.from, &t.to).err()
            };
            if let Some(reason) = reason {
                self.close_trade(i, &reason, false);
            }
        }
    }
    pub(super) fn trade(&mut self, session: u64, command: TradeCommand) {
        let Some(me) = self.players.get(&session).map(|p| p.character.id.clone()) else {
            return;
        };
        let result = match command {
            TradeCommand::Request { id } => self.trade_request(&me, &id),
            TradeCommand::Accept { id } => self.trade_accept(&me, &id),
            TradeCommand::Decline { id } => self.trade_decline(&me, &id),
            TradeCommand::Offer { items, gold } => self.trade_offer(&me, items, gold),
            TradeCommand::Confirm => self.trade_confirm(&me),
            TradeCommand::Cancel => self.trade_cancel(&me),
        };
        if let Err(text) = result {
            self.audit_warning(session, &format!("Trade refused: {text}"));
            self.tell(&me, text, false);
        }
    }
    fn trade_request(&mut self, me: &str, other: &str) -> Result<(), String> {
        if me == other {
            return Err("You cannot trade with yourself.".into());
        }
        if self.trade_index(me).is_some() || self.trade_index(other).is_some() {
            return Err("One of you is already trading.".into());
        }
        let adventurer = self.online(other).is_some_and(|p| p.ambient.is_some());
        self.trade_pair_checks(me, other, adventurer)?;
        if adventurer {
            self.ambient_declines(me, other, false);
            return Ok(());
        }
        self.trades.push(Trade {
            from: me.into(),
            to: other.into(),
            accepted: false,
            expires: self.time + REQUEST_LIFETIME,
            offers: [Offer::default(), Offer::default()],
        });
        self.push_trade(self.trades.len() - 1);
        Ok(())
    }
    fn trade_accept(&mut self, me: &str, from: &str) -> Result<(), String> {
        let i = self.trade_index(me).ok_or("No trade request is waiting.")?;
        if self.trades[i].accepted || self.trades[i].to != me || self.trades[i].from != from {
            return Err("No matching trade request is waiting.".into());
        }
        self.trade_pair_valid(me, from)?;
        self.trades[i].accepted = true;
        self.trades[i].expires = self.time + OPEN_LIFETIME;
        self.push_trade(i);
        Ok(())
    }
    fn trade_decline(&mut self, me: &str, from: &str) -> Result<(), String> {
        let i = self.trade_index(me).ok_or("No trade request is waiting.")?;
        if self.trades[i].accepted || self.trades[i].to != me || self.trades[i].from != from {
            return Err("No matching trade request is waiting.".into());
        }
        self.close_trade(i, "Trade request declined.", false);
        Ok(())
    }
    fn trade_cancel(&mut self, me: &str) -> Result<(), String> {
        let i = self.trade_index(me).ok_or("You are not trading.")?;
        self.close_trade(i, "Trade cancelled.", false);
        Ok(())
    }
    fn trade_offer(&mut self, me: &str, items: Vec<ItemStack>, gold: u32) -> Result<(), String> {
        let i = self.trade_index(me).ok_or("You are not trading.")?;
        if !self.trades[i].accepted {
            return Err("Wait for the other player to accept.".into());
        }
        let other = self.trades[i].other(me).to_owned();
        self.trade_pair_valid(me, &other)?;
        let who = &self.online(me).unwrap().character;
        validate_offer(
            who,
            &Offer {
                items: items.clone(),
                gold,
                ready: false,
            },
            &other,
            unix_now(),
        )?;
        let side = self.trades[i].side(me).unwrap();
        self.trades[i].offers[side] = Offer {
            items,
            gold,
            ready: false,
        };
        self.trades[i].offers[1 - side].ready = false;
        self.trades[i].expires = self.time + OPEN_LIFETIME;
        self.push_trade(i);
        Ok(())
    }
    fn trade_confirm(&mut self, me: &str) -> Result<(), String> {
        let i = self.trade_index(me).ok_or("You are not trading.")?;
        if !self.trades[i].accepted {
            return Err("Wait for the other player to accept.".into());
        }
        let t = self.trades[i].clone();
        self.trade_pair_valid(&t.from, &t.to)?;
        let side = t.side(me).unwrap();
        validate_offer(
            &self.online(me).unwrap().character,
            &t.offers[side],
            t.other(me),
            unix_now(),
        )?;
        self.trades[i].offers[side].ready = true;
        if !self.trades[i].offers[1 - side].ready {
            self.push_trade(i);
            return Ok(());
        }
        let a = self.online(&t.from).unwrap().character.clone();
        let b = self.online(&t.to).unwrap().character.clone();
        match settle_trade(&a, &b, &t.offers[0], &t.offers[1], unix_now()) {
            Ok((next_a, next_b)) => {
                self.store
                    .save_many([&next_a, &next_b].into_iter())
                    .map_err(|e| format!("Trade could not be saved: {e}"))?;
                let describe = |offer: &Offer| {
                    format!(
                        "{} gold; {}",
                        offer.gold,
                        offer
                            .items
                            .iter()
                            .map(|stack| format!(
                                "{} x{}",
                                item(&stack.item).map_or(stack.item.as_str(), |i| i.name.as_str()),
                                stack.quantity
                            ))
                            .collect::<Vec<_>>()
                            .join(", ")
                    )
                };
                self.store.log_activity(
                    &a.id,
                    &a.look.name,
                    "trade",
                    &format!(
                        "Traded with {}. Gave {}. Received {}.",
                        b.look.name,
                        describe(&t.offers[0]),
                        describe(&t.offers[1])
                    ),
                    false,
                );
                self.store.log_activity(
                    &b.id,
                    &b.look.name,
                    "trade",
                    &format!(
                        "Traded with {}. Gave {}. Received {}.",
                        a.look.name,
                        describe(&t.offers[1]),
                        describe(&t.offers[0])
                    ),
                    false,
                );
                self.players
                    .values_mut()
                    .find(|p| p.character.id == t.from)
                    .unwrap()
                    .character = next_a;
                self.players
                    .values_mut()
                    .find(|p| p.character.id == t.to)
                    .unwrap()
                    .character = next_b;
                self.close_trade(i, "Trade completed.", true);
            }
            Err(error) => {
                self.close_trade(i, &format!("Trade cancelled: {error}"), false);
                return Err(error);
            }
        }
        Ok(())
    }
}

/// `receiver` is the other side's character id and `now` the wall clock in Unix seconds: a class piece is
/// bound to its owner, except a rolled copy inside its hand-off window to a voter of that roll.
fn validate_offer(who: &Character, offer: &Offer, receiver: &str, now: u64) -> Result<(), String> {
    if offer.items.len() > MAX_OFFER_STACKS {
        return Err("A trade can offer up to twelve item stacks.".into());
    }
    if offer.gold > who.gold {
        return Err("You do not have that much gold.".into());
    }
    let mut seen = std::collections::BTreeSet::new();
    for stack in &offer.items {
        if stack.quantity == 0 || !seen.insert(&stack.item) {
            return Err("Choose each offered item once with a positive quantity.".into());
        }
        let i = item(&stack.item).ok_or("Unknown item in trade.")?;
        if i.starter || i.rarity == GM_RARITY || i.kind == "mount_licence" {
            return Err("Starter and game master gear cannot be traded.".into());
        }
        if is_quest_item(i) {
            return Err("Quest items cannot be traded.".into());
        }
        if stack.quantity
            > who
                .quantity(&stack.item)
                .saturating_sub(who.equipped_count(i))
        {
            return Err("You cannot trade items you do not own or have equipped.".into());
        }
        if is_gear(i)
            && i.class.is_some()
            && who.tradeable_copies(&i.id, receiver, now).len() < stack.quantity as usize
        {
            return Err(format!(
                "{} is class gear, bound to its owner. It can only be sold.",
                i.name
            ));
        }
    }
    Ok(())
}
fn settle_trade(
    a: &Character,
    b: &Character,
    ao: &Offer,
    bo: &Offer,
    now: u64,
) -> Result<(Character, Character), String> {
    validate_offer(a, ao, &b.id, now)?;
    validate_offer(b, bo, &a.id, now)?;
    let mut next_a = a.clone();
    let mut next_b = b.clone();
    next_a.gold = a
        .gold
        .checked_sub(ao.gold)
        .and_then(|g| g.checked_add(bo.gold))
        .ok_or("Gold amount is too large.")?;
    next_b.gold = b
        .gold
        .checked_sub(bo.gold)
        .and_then(|g| g.checked_add(ao.gold))
        .ok_or("Gold amount is too large.")?;
    move_items(&mut next_a, &mut next_b, ao, &b.id, now)?;
    move_items(&mut next_b, &mut next_a, bo, &a.id, now)?;
    if next_a.bag_used() > next_a.bag_capacity() || next_b.bag_used() > next_b.bag_capacity() {
        return Err("The trade would overfill a player's bags.".into());
    }
    Ok((next_a, next_b))
}
fn move_items(
    giver: &mut Character,
    receiver: &mut Character,
    offer: &Offer,
    receiver_id: &str,
    now: u64,
) -> Result<(), String> {
    for s in &offer.items {
        if item(&s.item).is_some_and(is_gear) {
            giver.materialize_gear_instances();
            receiver.materialize_gear_instances();
            let worn = item(&s.item).map_or(0, |i| giver.equipped_count(i)) as usize;
            // A class piece moves only as a copy whose window is open for the receiver.
            let bound = item(&s.item).is_some_and(|i| i.class.is_some());
            let moved: Vec<_> = giver
                .gear_instances
                .iter()
                .filter(|g| g.item == s.item)
                .skip(worn)
                .filter(|g| !bound || g.tradeable_to(receiver_id, now))
                .take(s.quantity as usize)
                .cloned()
                .collect();
            if moved.len() != s.quantity as usize {
                return Err("The offered gear copies are no longer available.".into());
            }
            let ids: std::collections::BTreeSet<_> = moved.iter().map(|g| g.id).collect();
            giver.gear_instances.retain(|g| !ids.contains(&g.id));
            for mut copy in moved {
                copy.id = receiver.next_gear_id;
                copy.clear_trade_window();
                receiver.next_gear_id += 1;
                receiver.gear_instances.push(copy);
            }
        }
        let held = giver
            .inventory
            .iter_mut()
            .find(|x| x.item == s.item)
            .unwrap();
        held.quantity -= s.quantity;
        let received = receiver
            .quantity(&s.item)
            .checked_add(s.quantity)
            .ok_or("Item stack is too large.")?;
        if let Some(stack) = receiver.inventory.iter_mut().find(|x| x.item == s.item) {
            stack.quantity = received;
        } else {
            receiver.inventory.push(ItemStack {
                item: s.item.clone(),
                quantity: received,
            });
        }
    }
    giver.inventory.retain(|s| s.quantity > 0);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    const NOW: u64 = 1_000_000;
    fn world() -> World {
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
    }
    fn add(w: &mut World, session: u64, name: &str) -> (String, String) {
        let (tx, _rx) = mpsc::channel(128);
        let look = Look {
            name: name.into(),
            ..Look::default()
        };
        let welcome = w.join(session, None, Some(look), tx).unwrap();
        (
            welcome["id"].as_str().unwrap().into(),
            welcome["token"].as_str().unwrap().into(),
        )
    }
    fn items(id: &str, quantity: u32) -> Vec<ItemStack> {
        vec![ItemStack {
            item: id.into(),
            quantity,
        }]
    }
    #[test]
    fn no_golden_piece_can_be_offered_in_a_trade() {
        for id in crate::items::GM_GEAR {
            let mut gm = Character::mercenary(Class::Warrior, 20, "Gm");
            gm.add_item(id, 3);
            let offer = Offer {
                items: items(id, 1),
                gold: 0,
                ready: false,
            };
            assert!(validate_offer(&gm, &offer, "bob", NOW).is_err(), "{id}");
        }
    }
    #[test]
    fn trade_preserves_a_refined_copys_rolls_and_rank() {
        let id = "warrior_weapon_sword_l5_gray";
        let mut alice = Character::mercenary(Class::Warrior, 20, "Alice");
        let mut bob = Character::mercenary(Class::Warrior, 20, "Bob");
        alice.add_item(id, 1);
        alice.materialize_gear_instances();
        let copy = alice
            .gear_instances
            .iter_mut()
            .find(|g| g.item == id)
            .unwrap();
        copy.rarity = "rare".into();
        copy.rank = 3;
        copy.rolled_stats.strength = 7;
        copy.open_trade_window(vec!["bob".into()], NOW);
        let source = copy.clone();
        move_items(
            &mut alice,
            &mut bob,
            &Offer {
                items: items(id, 1),
                gold: 0,
                ready: false,
            },
            "bob",
            NOW,
        )
        .unwrap();
        assert_eq!(alice.quantity(id), 0);
        assert!(alice.gear_instances.iter().all(|g| g.item != id));
        let received = bob.gear_instances.iter().find(|g| g.item == id).unwrap();
        assert_eq!(
            (
                received.rarity.as_str(),
                received.rank,
                received.rolled_stats.strength
            ),
            ("rare", 3, 7)
        );
        assert_eq!(
            (
                received.attack,
                received.defense,
                received.bonus_stats.clone()
            ),
            (source.attack, source.defense, source.bonus_stats)
        );
    }
    #[test]
    fn trade_preserves_purple_dungeon_set_piece() {
        let piece = crate::items::ITEMS
            .iter()
            .find(|i| {
                i.source.as_deref() == Some("undervault")
                    && i.class == Some(Class::Warrior)
                    && i.kind == "weapon"
            })
            .unwrap();
        let mut alice = Character::mercenary(Class::Warrior, 20, "Alice");
        let mut bob = Character::mercenary(Class::Warrior, 20, "Bob");
        alice.add_item(&piece.id, 1);
        alice.materialize_gear_instances();
        let epic = crate::items::set_piece_copy(piece, 0.).unwrap();
        let held = alice
            .gear_instances
            .iter_mut()
            .find(|g| g.item == piece.id)
            .unwrap();
        let old_id = held.id;
        *held = GearInstance {
            id: old_id,
            ..epic.clone()
        };
        held.open_trade_window(vec!["bob".into()], NOW);
        move_items(
            &mut alice,
            &mut bob,
            &Offer {
                items: items(&piece.id, 1),
                gold: 0,
                ready: false,
            },
            "bob",
            NOW,
        )
        .unwrap();
        let received = bob
            .gear_instances
            .iter()
            .find(|g| g.item == piece.id)
            .unwrap();
        assert_eq!(received.rarity, "epic");
        assert_eq!(received.attack, epic.attack);
        assert_eq!(received.rolled_stats, epic.rolled_stats);
    }
    /// One catalog piece per class and rarity, so every class and every rarity present is covered.
    fn class_pieces() -> Vec<&'static Item> {
        let mut seen = std::collections::BTreeSet::new();
        ITEMS
            .iter()
            .filter(|i| {
                is_gear(i)
                    && i.class.is_some()
                    && !i.starter
                    && i.rarity != GM_RARITY
                    && !is_quest_item(i)
                    && seen.insert((format!("{:?}", i.class), i.rarity.clone()))
            })
            .collect()
    }
    fn offer(id: &str, quantity: u32) -> Offer {
        Offer {
            items: items(id, quantity),
            gold: 0,
            ready: false,
        }
    }
    #[test]
    fn class_gear_of_every_class_and_rarity_cannot_be_offered() {
        let pieces = class_pieces();
        assert!(
            pieces.len() >= 10,
            "{} class/rarity combinations",
            pieces.len()
        );
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            assert!(pieces.iter().any(|i| i.class == Some(class)), "{class:?}");
        }
        for i in pieces {
            let mut alice = Character::mercenary(Class::Warrior, 20, "Alice");
            alice.add_item(&i.id, 2);
            alice.materialize_gear_instances();
            let error = validate_offer(&alice, &offer(&i.id, 1), "bob", NOW).unwrap_err();
            assert!(error.contains("bound to its owner"), "{}: {error}", i.id);
        }
    }
    #[test]
    fn neutral_gear_materials_and_potions_still_trade() {
        let neutral = ITEMS
            .iter()
            .find(|i| {
                is_gear(i)
                    && i.class.is_none()
                    && !i.starter
                    && i.rarity != GM_RARITY
                    && !is_quest_item(i)
            })
            .expect("a class-neutral piece");
        let mut alice = Character::mercenary(Class::Warrior, 20, "Alice");
        let potion = ITEMS.iter().find(|i| i.kind == "potion").unwrap();
        for id in [neutral.id.as_str(), "slime_gel", potion.id.as_str()] {
            alice.add_item(id, 1);
            validate_offer(&alice, &offer(id, 1), "bob", NOW)
                .unwrap_or_else(|e| panic!("{id}: {e}"));
        }
        let bob = Character::mercenary(Class::Mage, 20, "Bob");
        let (next_a, next_b) =
            settle_trade(&alice, &bob, &offer(&neutral.id, 1), &Offer::default(), NOW).unwrap();
        assert_eq!(
            (next_a.quantity(&neutral.id), next_b.quantity(&neutral.id)),
            (0, 1)
        );
    }
    #[test]
    fn a_hand_built_offer_of_a_bound_piece_is_refused_at_settle() {
        let piece = class_pieces()[0];
        let mut alice = Character::mercenary(Class::Warrior, 20, "Alice");
        let bob = Character::mercenary(Class::Warrior, 20, "Bob");
        alice.add_item(&piece.id, 1);
        // Offered by either side, with or without the other side's counter offer.
        assert!(settle_trade(&alice, &bob, &offer(&piece.id, 1), &Offer::default(), NOW).is_err());
        assert!(settle_trade(&bob, &alice, &Offer::default(), &offer(&piece.id, 1), NOW).is_err());
        assert_eq!(alice.quantity(&piece.id), 1);
    }
    #[test]
    fn a_rolled_piece_can_be_handed_to_a_voter_once_inside_two_hours() {
        let piece = class_pieces()[0];
        let mut alice = Character::mercenary(Class::Warrior, 20, "Alice");
        let bob = Character::mercenary(Class::Warrior, 20, "Bob");
        let cat = Character::mercenary(Class::Warrior, 20, "Cat");
        alice.add_item(&piece.id, 1);
        alice.materialize_gear_instances();
        alice
            .gear_instances
            .iter_mut()
            .find(|g| g.item == piece.id)
            .unwrap()
            .open_trade_window(vec![bob.id.clone()], NOW);
        // Nobody but a voter of the roll may receive it.
        assert!(validate_offer(&alice, &offer(&piece.id, 1), &cat.id, NOW).is_err());
        assert!(settle_trade(&alice, &cat, &offer(&piece.id, 1), &Offer::default(), NOW).is_err());
        // The last second of the window still works; the first after it does not.
        let end = NOW + 7_200;
        validate_offer(&alice, &offer(&piece.id, 1), &bob.id, end - 1).unwrap();
        assert!(validate_offer(&alice, &offer(&piece.id, 1), &bob.id, end).is_err());
        let (a, b) =
            settle_trade(&alice, &bob, &offer(&piece.id, 1), &Offer::default(), NOW).unwrap();
        assert_eq!((a.quantity(&piece.id), b.quantity(&piece.id)), (0, 1));
        let received = b
            .gear_instances
            .iter()
            .find(|g| g.item == piece.id)
            .unwrap();
        assert_eq!((received.trade_until, received.trade_with.len()), (0, 0));
        // One hand-off only: the receiver cannot pass it on, to the giver or anyone else.
        for to in [&alice.id, &cat.id] {
            assert!(validate_offer(&b, &offer(&piece.id, 1), to, NOW).is_err());
        }
    }
    #[test]
    fn the_hand_off_window_survives_a_save_and_is_judged_by_the_wall_clock() {
        let piece = class_pieces()[0];
        let mut alice = Character::mercenary(Class::Warrior, 20, "Alice");
        alice.add_item(&piece.id, 1);
        alice.materialize_gear_instances();
        alice
            .gear_instances
            .iter_mut()
            .find(|g| g.item == piece.id)
            .unwrap()
            .open_trade_window(vec!["bob".into()], NOW);
        let loaded: Character =
            serde_json::from_str(&serde_json::to_string(&alice).unwrap()).unwrap();
        validate_offer(&loaded, &offer(&piece.id, 1), "bob", NOW + 3_600).unwrap();
        assert!(validate_offer(&loaded, &offer(&piece.id, 1), "bob", NOW + 7_200).is_err());
        // An old save has neither field and loads as a bound piece.
        let mut json: serde_json::Value = serde_json::to_value(&alice).unwrap();
        for g in json["gearInstances"].as_array_mut().unwrap() {
            g.as_object_mut().unwrap().remove("tradeUntil");
            g.as_object_mut().unwrap().remove("tradeWith");
        }
        let old: Character = serde_json::from_value(json).unwrap();
        assert!(validate_offer(&old, &offer(&piece.id, 1), "bob", NOW).is_err());
    }
    #[test]
    fn selling_refining_and_merging_clear_the_window() {
        let piece = class_pieces()[0];
        let mut alice = Character::mercenary(Class::Warrior, 20, "Alice");
        alice.add_item(&piece.id, 3);
        alice.materialize_gear_instances();
        for g in alice
            .gear_instances
            .iter_mut()
            .filter(|g| g.item == piece.id)
        {
            g.open_trade_window(vec!["bob".into()], NOW);
        }
        let id = alice
            .gear_instances
            .iter()
            .find(|g| g.item == piece.id)
            .unwrap()
            .id;
        let (refined, ..) = alice.preview_refine(id).unwrap();
        assert_eq!((refined.trade_until, refined.trade_with.len()), (0, 0));
        let other = alice
            .gear_instances
            .iter()
            .find(|g| g.item == piece.id && g.id != id)
            .unwrap()
            .id;
        let merged = alice.preview_merge(id, other).unwrap();
        assert_eq!((merged.trade_until, merged.trade_with.len()), (0, 0));
        let sold_before = alice.quantity(&piece.id);
        alice.sell_item(&piece.id, 1).unwrap();
        assert_eq!(
            alice.quantity(&piece.id),
            sold_before - 1,
            "selling a class piece still works"
        );
    }

    #[test]
    fn a_confirmed_trade_exchanges_and_saves_both_characters_once() {
        let mut w = world();
        let (alice, akey) = add(&mut w, 1, "Alice");
        let (bob, bkey) = add(&mut w, 2, "Bob");
        w.players.get_mut(&1).unwrap().character.gold = 50;
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item("slime_gel", 3);
        w.players.get_mut(&2).unwrap().character.gold = 20;
        w.players
            .get_mut(&2)
            .unwrap()
            .character
            .add_item("blue_gel", 2);
        w.trade(1, TradeCommand::Request { id: bob.clone() });
        w.trade(2, TradeCommand::Accept { id: alice.clone() });
        w.trade(
            1,
            TradeCommand::Offer {
                items: items("slime_gel", 2),
                gold: 10,
            },
        );
        w.trade(
            2,
            TradeCommand::Offer {
                items: items("blue_gel", 1),
                gold: 5,
            },
        );
        w.trade(1, TradeCommand::Confirm);
        assert_eq!(
            w.players[&1].character.gold, 50,
            "one confirmation cannot move gold"
        );
        w.trade(2, TradeCommand::Confirm);
        assert!(w.trades.is_empty());
        let a = &w.players[&1].character;
        let b = &w.players[&2].character;
        assert_eq!(
            (a.gold, a.quantity("slime_gel"), a.quantity("blue_gel")),
            (45, 1, 1)
        );
        assert_eq!(
            (b.gold, b.quantity("slime_gel"), b.quantity("blue_gel")),
            (25, 2, 1)
        );
        let saved_a = w.store.load(&akey).unwrap().unwrap();
        let saved_b = w.store.load(&bkey).unwrap().unwrap();
        assert_eq!((saved_a.gold, saved_a.quantity("blue_gel")), (45, 1));
        assert_eq!((saved_b.gold, saved_b.quantity("slime_gel")), (25, 2));
    }
    #[test]
    fn invalid_offers_and_full_bags_cannot_transfer() {
        let mut w = world();
        add(&mut w, 1, "Alice");
        add(&mut w, 2, "Bob");
        let mut a = w.players[&1].character.clone();
        let mut b = w.players[&2].character.clone();
        a.gold = 5;
        a.add_item("slime_gel", 1);
        assert!(
            validate_offer(
                &a,
                &Offer {
                    items: items("warrior_weapon_sword", 1),
                    ..Offer::default()
                },
                "bob",
                NOW
            )
            .is_err()
        );
        a.add_item("warrior_weapon_royal", 1);
        a.equip_owned("crimson", "royal").unwrap();
        assert!(
            validate_offer(
                &a,
                &Offer {
                    items: items("warrior_weapon_royal", 1),
                    ..Offer::default()
                },
                "bob",
                NOW
            )
            .is_err()
        );
        assert!(
            validate_offer(
                &a,
                &Offer {
                    items: items("slime_gel", 2),
                    ..Offer::default()
                },
                "bob",
                NOW
            )
            .is_err()
        );
        assert!(
            validate_offer(
                &a,
                &Offer {
                    gold: 6,
                    ..Offer::default()
                },
                "bob",
                NOW
            )
            .is_err()
        );
        assert!(
            validate_offer(
                &a,
                &Offer {
                    items: items("slime_gel", 1).into_iter().cycle().take(2).collect(),
                    ..Offer::default()
                },
                "bob",
                NOW
            )
            .is_err()
        );
        for i in ITEMS
            .iter()
            .filter(|i| i.kind == "material" && i.id != "slime_gel")
        {
            if b.bag_used() == b.bag_capacity() {
                break;
            }
            b.add_item(&i.id, 1);
        }
        assert_eq!(b.bag_used(), b.bag_capacity());
        let before = (a.quantity("slime_gel"), b.quantity("slime_gel"));
        assert!(
            settle_trade(
                &a,
                &b,
                &Offer {
                    items: items("slime_gel", 1),
                    ..Offer::default()
                },
                &Offer::default(),
                NOW
            )
            .is_err()
        );
        assert_eq!((a.quantity("slime_gel"), b.quantity("slime_gel")), before);
    }
    #[test]
    fn changing_an_offer_clears_both_confirmations_and_disconnect_cancels() {
        let mut w = world();
        let (alice, _) = add(&mut w, 1, "Alice");
        let (bob, _) = add(&mut w, 2, "Bob");
        w.trade(1, TradeCommand::Request { id: bob });
        w.trade(2, TradeCommand::Accept { id: alice });
        w.trade(1, TradeCommand::Confirm);
        assert!(w.trades[0].offers[0].ready);
        w.trade(
            2,
            TradeCommand::Offer {
                items: vec![],
                gold: 0,
            },
        );
        assert!(!w.trades[0].offers[0].ready);
        w.leave(2);
        assert!(w.trades.is_empty());
    }
    #[test]
    fn requests_require_proximity_and_open_trades_end_when_players_separate() {
        let mut w = world();
        let (alice, _) = add(&mut w, 1, "Alice");
        let (bob, _) = add(&mut w, 2, "Bob");
        let at = w.players[&2].character.x;
        w.players.get_mut(&2).unwrap().character.x = at + 10.;
        w.trade(1, TradeCommand::Request { id: bob.clone() });
        assert!(w.trades.is_empty());
        w.players.get_mut(&2).unwrap().character.x = at;
        w.trade(1, TradeCommand::Request { id: bob });
        w.trade(2, TradeCommand::Accept { id: alice });
        assert_eq!(w.trades.len(), 1);
        w.players.get_mut(&2).unwrap().character.x = at + 10.;
        w.update_trades();
        assert!(w.trades.is_empty());
    }
}
