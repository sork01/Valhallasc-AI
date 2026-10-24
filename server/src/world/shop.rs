//! Atomic merchant sales and connection-local buy-back (docs/shop-selling.md).
use super::*;
use crate::items::{GearInstance, is_gear};
use crate::model::SaleLine;

#[derive(Clone, Default)]
pub(super) struct Session {
    merchants: BTreeMap<String, Vec<Sold>>,
    next_id: u64,
}
#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct Sold {
    id: u64,
    item: String,
    quantity: u32,
    paid: u32,
    gear: Vec<GearInstance>,
}
pub(super) enum Request {
    Open,
    Sell(Vec<SaleLine>),
    BuyBack(u64),
}

fn sellable(i: &Item) -> bool {
    !i.starter && i.rarity != GM_RARITY && i.kind != "mount_licence" && !is_quest_item(i)
}

/// Operates only on the caller's staged character. A failure discards all preceding lines.
fn sell_lines(c: &mut Character, lines: &[SaleLine]) -> Result<(u32, Vec<Sold>), &'static str> {
    if lines.is_empty() || lines.len() > 256 {
        return Err("Choose between 1 and 256 sale entries.");
    }
    c.materialize_gear_instances();
    let mut sold = vec![];
    let mut total = 0_u32;
    let mut seen = std::collections::BTreeSet::new();
    for line in lines {
        if !seen.insert((&line.item, line.copy)) {
            return Err("An item appears twice in this sale.");
        }
        let catalog = item(&line.item).ok_or("Unknown item.")?;
        if !sellable(catalog) {
            return Err("That item cannot be sold.");
        }
        if let Some(id) = line.copy {
            if !is_gear(catalog) || line.quantity != 1 || c.gear_instance_equipped(id) {
                return Err("That gear copy is not available to sell.");
            }
            let at = c
                .gear_instances
                .iter()
                .position(|g| g.id == id && g.item == line.item)
                .ok_or("That gear copy is not available to sell.")?;
            let copy = c.gear_instances.remove(at);
            let front = c
                .gear_instances
                .iter()
                .enumerate()
                .filter(|(_, g)| g.item == line.item)
                .nth(c.equipped_count(catalog) as usize)
                .map_or(c.gear_instances.len(), |(at, _)| at);
            c.gear_instances.insert(front, copy);
        }
        let gear: Vec<_> = c
            .gear_instances
            .iter()
            .filter(|g| g.item == line.item)
            .skip(c.equipped_count(catalog) as usize)
            .take(line.quantity as usize)
            .cloned()
            .collect();
        let paid = c.sell_item(&line.item, line.quantity)?;
        total = total.checked_add(paid).ok_or("That sale is too large.")?;
        // Each physical gear copy has its own buy-back row; stacks retain their sold quantity.
        if is_gear(catalog) {
            let mut base = 0_u32;
            for copy in gear {
                let before = c.boosted_gold(base);
                base += catalog.sell
                    * if catalog.rarity == "rare" && copy.rarity == "epic" {
                        2
                    } else {
                        1
                    };
                sold.push(Sold {
                    id: 0,
                    item: line.item.clone(),
                    quantity: 1,
                    paid: c.boosted_gold(base) - before,
                    gear: vec![copy],
                });
            }
        } else {
            sold.push(Sold {
                id: 0,
                item: line.item.clone(),
                quantity: line.quantity,
                paid,
                gear: vec![],
            });
        }
    }
    Ok((total, sold))
}

fn remember(shop: &mut Session, npc: &str, sold: Vec<Sold>) {
    let rows = shop.merchants.entry(npc.to_owned()).or_default();
    for mut row in sold {
        shop.next_id += 1;
        row.id = shop.next_id;
        rows.push(row);
    }
    if rows.len() > 12 {
        rows.drain(..rows.len() - 12);
    }
}

/// Shared by older `sell:*` interactions; the surrounding dialogue path saves the character.
pub(super) fn legacy_sell(
    c: &mut Character,
    shop: &mut Session,
    npc: &str,
    sale: &str,
) -> Result<u32, &'static str> {
    let lines = if sale == "materials" {
        c.inventory
            .iter()
            .filter(|s| item(&s.item).is_some_and(|i| i.kind == "material" && !is_quest_item(i)))
            .map(|s| SaleLine {
                item: s.item.clone(),
                quantity: s.quantity,
                copy: None,
            })
            .collect::<Vec<_>>()
    } else {
        let (id, quantity) = sale.rsplit_once(':').ok_or("Invalid sale.")?;
        vec![SaleLine {
            item: id.into(),
            quantity: quantity.parse().map_err(|_| "Invalid sale quantity.")?,
            copy: None,
        }]
    };
    if lines.is_empty() {
        return Ok(0);
    }
    let mut next = c.clone();
    let (paid, sold) = sell_lines(&mut next, &lines)?;
    *c = next;
    remember(shop, npc, sold);
    Ok(paid)
}

impl World {
    pub(super) fn shop(&mut self, session: u64, npc: &str, request: Request) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        let valid = p.character.hp > 0.
            && p.character.spark_travel.is_none()
            && self.maps[p.character.zone].npcs.iter().any(|n| {
                n.id == npc
                    && n.buys
                    && p.character.point().distance(n.position_at(self.time)) <= 2.8
            });
        if !valid {
            let _ = p
                .peer
                .try_send(json!({"type":"shop","npc":npc,"ok":false,"closed":true,
                "notice":"Walk closer to a merchant who buys items."}));
            return;
        }
        p.stop();
        p.attack = 0.;
        let mut next = p.character.clone();
        let materialized = next.materialize_gear_instances();
        let mut shop = p.shop.clone();
        let mut paid = 0;
        let mut spent = 0;
        let mut changed = false;
        let result: Result<(), &'static str> = (|| {
            if !matches!(request, Request::Open) {
                if self.time - p.service_at < 0.5 {
                    return Err("Please wait a moment before trying again.");
                }
                p.service_at = self.time;
            }
            match request {
                Request::Open => {}
                Request::Sell(lines) => {
                    let (gold, sold) = sell_lines(&mut next, &lines)?;
                    remember(&mut shop, npc, sold);
                    paid = gold;
                    changed = true;
                }
                Request::BuyBack(id) => {
                    let rows = shop.merchants.entry(npc.to_owned()).or_default();
                    let at = rows
                        .iter()
                        .position(|row| row.id == id)
                        .ok_or("That buy-back item is no longer available.")?;
                    let row = &rows[at];
                    let catalog = item(&row.item).ok_or("Unknown item.")?;
                    if next.gold < row.paid {
                        return Err("You do not have enough gold to buy that back.");
                    }
                    if next.quantity(&row.item) <= next.equipped_count(catalog)
                        && next.bag_used() >= next.bag_capacity()
                    {
                        return Err("Your bags are full. Make room first.");
                    }
                    if next.quantity(&row.item).checked_add(row.quantity).is_none() {
                        return Err("That stack is too large for your bags.");
                    }
                    if row.gear.iter().any(|g| {
                        next.gear_instances
                            .iter()
                            .chain(&next.bank.gear)
                            .any(|held| held.id == g.id)
                    }) {
                        return Err("That gear copy is not available to buy back.");
                    }
                    next.gold -= row.paid;
                    next.add_item(&row.item, row.quantity);
                    next.gear_instances.extend(row.gear.clone());
                    spent = row.paid;
                    rows.remove(at);
                    changed = true;
                }
            }
            if changed || materialized {
                self.store.save_many([&next].into_iter()).map_err(|e| {
                    tracing::error!(%e, "merchant transaction could not be saved");
                    "The merchant could not save that. Nothing was moved."
                })?;
            }
            Ok(())
        })();
        let ok = result.is_ok();
        let notice = match result {
            Ok(()) => {
                p.character = next;
                p.shop = shop;
                if changed && spent > 0 {
                    format!("Bought back for {spent} gold.")
                } else if changed {
                    format!("Items sold for {paid} gold.")
                } else {
                    String::new()
                }
            }
            Err(text) => text.to_owned(),
        };
        let c = &p.character;
        let mut available = vec![];
        for stack in &c.inventory {
            let Some(i) = item(&stack.item).filter(|i| sellable(i)) else {
                continue;
            };
            let quantity = stack.quantity.saturating_sub(c.equipped_count(i));
            if quantity == 0 {
                continue;
            }
            if is_gear(i) {
                for g in c
                    .gear_instances
                    .iter()
                    .filter(|g| g.item == i.id)
                    .skip(c.equipped_count(i) as usize)
                {
                    let base = i.sell
                        * if i.rarity == "rare" && g.rarity == "epic" {
                            2
                        } else {
                            1
                        };
                    available.push(json!({"item":i.id,"copy":g.id,"quantity":1,"base":base,"rarity":g.rarity,"gear":g}));
                }
            } else {
                available
                    .push(json!({"item":i.id,"quantity":quantity,"base":i.sell,"rarity":i.rarity}));
            }
        }
        let _ = p
            .peer
            .try_send(json!({"type":"shop","npc":npc,"ok":ok,"notice":notice,
            "paid":if ok {paid} else {0},"spent":if ok {spent} else {0},"changed":ok && changed,
            "available":available,"buyBack":p.shop.merchants.get(npc).cloned().unwrap_or_default(),
            "goldPercent":c.rebirth_gold_percent(),"gold":c.gold,"inventory":c.inventory,
            "gearInstances":c.gear_instances,"equipment":c.equipment,"bags":c.bags}));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    const PIECE: &str = "warrior_weapon_sword_l5_gray";
    fn fixture() -> (World, mpsc::Receiver<Value>, String) {
        let mut w = super::super::wyrd_tests::world();
        let (tx, rx) = mpsc::channel(512);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let smith = w.maps[0].npcs.iter().find(|n| n.id == "smith").unwrap();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = smith.x;
        c.y = smith.y;
        c.gold = 10000;
        c.add_item("slime_gel", 5);
        c.add_item(PIECE, 3);
        c.materialize_gear_instances();
        w.time += 1.;
        (w, rx, token)
    }
    fn line(item: &str, quantity: u32, copy: Option<u64>) -> SaleLine {
        SaleLine {
            item: item.into(),
            quantity,
            copy,
        }
    }
    fn message(w: &mut World, rx: &mut mpsc::Receiver<Value>, request: Request) -> Value {
        while rx.try_recv().is_ok() {}
        w.time += 1.;
        w.shop(1, "smith", request);
        std::iter::from_fn(|| rx.try_recv().ok())
            .find(|v| v["type"] == "shop")
            .unwrap()
    }
    fn state(w: &World) -> Value {
        serde_json::to_value(&w.players[&1].character).unwrap()
    }
    fn copies(w: &World) -> Vec<GearInstance> {
        w.players[&1]
            .character
            .gear_instances
            .iter()
            .filter(|g| g.item == PIECE)
            .cloned()
            .collect()
    }

    #[test]
    fn shop_batch_exact_copy_price_wear_rebirth_persistence_and_buyback() {
        let (mut w, mut rx, token) = fixture();
        let rare = ITEMS
            .iter()
            .find(|i| i.rarity == "rare" && is_gear(i) && !i.starter)
            .unwrap();
        let fancy = {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.rebirth_tiers[1] = 1;
            c.add_item(&rare.id, 2);
            c.materialize_gear_instances();
            let g = c
                .gear_instances
                .iter_mut()
                .filter(|g| g.item == rare.id)
                .last()
                .unwrap();
            g.rarity = "epic".into();
            g.wear = 70;
            g.rank = 3;
            g.trade_until = 123456789;
            g.trade_with = vec!["voter".into()];
            g.rolled_stats.stamina = 19;
            g.clone()
        };
        let before = w.players[&1].character.gold;
        let expected = w.players[&1].character.boosted_gold(rare.sell * 2)
            + w.players[&1]
                .character
                .boosted_gold(item("slime_gel").unwrap().sell * 3);
        let reply = message(
            &mut w,
            &mut rx,
            Request::Sell(vec![
                line("slime_gel", 3, None),
                line(&rare.id, 1, Some(fancy.id)),
            ]),
        );
        assert_eq!(reply["ok"], true, "{reply}");
        assert_eq!(reply["paid"], expected);
        let c = &w.players[&1].character;
        assert_eq!(c.gold, before + expected);
        assert_eq!(c.quantity("slime_gel"), 2);
        assert!(!c.gear_instances.iter().any(|g| g.id == fancy.id));
        assert_eq!(w.store.load(&token).unwrap().unwrap().gold, c.gold);
        let id = reply["buyBack"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["item"] == rare.id)
            .unwrap()["id"]
            .as_u64()
            .unwrap();
        let reply = message(&mut w, &mut rx, Request::BuyBack(id));
        assert_eq!(reply["ok"], true, "{reply}");
        let back = w.players[&1]
            .character
            .gear_instances
            .iter()
            .find(|g| g.id == fancy.id)
            .unwrap();
        assert_eq!(back, &fancy);
        assert_eq!(
            w.store
                .load(&token)
                .unwrap()
                .unwrap()
                .gear_instances
                .iter()
                .find(|g| g.id == fancy.id),
            Some(&fancy)
        );
        let before = state(&w);
        assert_eq!(message(&mut w, &mut rx, Request::BuyBack(id))["ok"], false);
        assert_eq!(state(&w), before);
    }

    #[test]
    fn shop_batch_rolls_back_invalid_duplicate_equipped_starter_quest_and_overflow_lines() {
        let (mut w, mut rx, _) = fixture();
        let id = copies(&w)[0].id;
        let starter = ITEMS.iter().find(|i| i.starter).unwrap().id.clone();
        let quest = ITEMS.iter().find(|i| is_quest_item(i)).unwrap().id.clone();
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item(&starter, 1);
        w.players.get_mut(&1).unwrap().character.add_item(&quest, 1);
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .equipment
            .insert("hands".into(), PIECE.into());
        for bad in [
            line("unknown", 1, None),
            line("slime_gel", 99, None),
            line("slime_gel", 0, None),
            line(&starter, 1, None),
            line(&quest, 1, None),
            line(PIECE, 1, Some(id)),
            line(PIECE, 2, Some(copies(&w)[1].id)),
            line("slime_gel", 1, Some(id)),
        ] {
            let before = state(&w);
            let reply = message(
                &mut w,
                &mut rx,
                Request::Sell(vec![line("slime_gel", 1, None), bad]),
            );
            assert_eq!(reply["ok"], false, "{reply}");
            assert_eq!(reply["paid"], 0);
            assert_eq!(state(&w), before);
            assert!(w.players[&1].shop.merchants.is_empty());
        }
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.gold = u32::MAX;
        let before = state(&w);
        assert_eq!(
            message(
                &mut w,
                &mut rx,
                Request::Sell(vec![line("slime_gel", 1, None)])
            )["ok"],
            false
        );
        assert_eq!(state(&w), before);
    }

    #[test]
    fn shop_buyback_caps_twelve_is_merchant_local_and_clears_on_logout() {
        let (mut w, mut rx, token) = fixture();
        for _ in 0..13 {
            w.players
                .get_mut(&1)
                .unwrap()
                .character
                .add_item("slime_gel", 1);
            assert_eq!(
                message(
                    &mut w,
                    &mut rx,
                    Request::Sell(vec![line("slime_gel", 1, None)])
                )["ok"],
                true
            );
        }
        let reply = message(&mut w, &mut rx, Request::Open);
        assert_eq!(reply["buyBack"].as_array().unwrap().len(), 12);
        assert_eq!(reply["buyBack"][0]["id"], 2);
        assert_eq!(message(&mut w, &mut rx, Request::BuyBack(1))["ok"], false);
        let other = w.maps[0]
            .npcs
            .iter()
            .find(|n| n.buys && n.id != "smith")
            .unwrap()
            .clone();
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = other.x;
            c.y = other.y;
        }
        w.time += 1.;
        w.shop(1, &other.id, Request::BuyBack(2));
        let reply = std::iter::from_fn(|| rx.try_recv().ok())
            .filter(|v| v["type"] == "shop")
            .last()
            .unwrap();
        assert_eq!(reply["ok"], false);
        assert_eq!(reply["buyBack"], json!([]));
        w.leave(1);
        let (tx, _rx) = mpsc::channel(512);
        w.join(1, Some(token), None, tx).unwrap();
        assert!(w.players[&1].shop.merchants.is_empty());
    }

    #[test]
    fn shop_buyback_rejects_no_gold_full_bag_and_failed_storage_atomically() {
        let (mut w, mut rx, _) = fixture();
        let id = copies(&w)[0].id;
        let reply = message(
            &mut w,
            &mut rx,
            Request::Sell(vec![line(PIECE, 1, Some(id))]),
        );
        let sold = reply["buyBack"][0]["id"].as_u64().unwrap();
        w.players.get_mut(&1).unwrap().character.gold = 0;
        let before = state(&w);
        assert_eq!(
            message(&mut w, &mut rx, Request::BuyBack(sold))["ok"],
            false
        );
        assert_eq!(state(&w), before);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.gold = 10000;
            c.consume_item(PIECE, 2);
            c.gear_instances.retain(|g| g.item != PIECE);
            for i in ITEMS.iter().filter(|i| i.kind == "material") {
                if c.bag_used() >= c.bag_capacity() {
                    break;
                }
                c.add_item(&i.id, 1);
            }
        }
        let before = state(&w);
        assert_eq!(
            message(&mut w, &mut rx, Request::BuyBack(sold))["ok"],
            false
        );
        assert_eq!(state(&w), before);
        w.players.get_mut(&1).unwrap().character.inventory.pop();
        w.store.conn().execute_batch("CREATE TRIGGER fail_shop BEFORE UPDATE ON characters BEGIN SELECT RAISE(FAIL, 'test storage failure'); END;").unwrap();
        let before = state(&w);
        assert_eq!(
            message(&mut w, &mut rx, Request::BuyBack(sold))["ok"],
            false
        );
        assert_eq!(state(&w), before);
        assert_eq!(
            message(
                &mut w,
                &mut rx,
                Request::Sell(vec![line("slime_gel", 1, None)])
            )["ok"],
            false
        );
        assert_eq!(state(&w), before);
        assert_eq!(w.players[&1].shop.merchants["smith"].len(), 1);
        w.store
            .conn()
            .execute_batch("DROP TRIGGER fail_shop;")
            .unwrap();
        assert_eq!(message(&mut w, &mut rx, Request::BuyBack(sold))["ok"], true);
    }

    #[test]
    fn shop_rejects_remote_wrong_npc_dead_and_throttled_requests() {
        let (mut w, mut rx, _) = fixture();
        let lines = || vec![line("slime_gel", 1, None)];
        w.players.get_mut(&1).unwrap().character.x += 10.;
        let before = state(&w);
        assert_eq!(
            message(&mut w, &mut rx, Request::Sell(lines()))["closed"],
            true
        );
        assert_eq!(state(&w), before);
        w.players.get_mut(&1).unwrap().character.x -= 10.;
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        assert_eq!(
            message(&mut w, &mut rx, Request::Sell(lines()))["closed"],
            true
        );
        w.players.get_mut(&1).unwrap().character.hp = 1.;
        w.shop(1, "guide", Request::Sell(lines()));
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 5);
        message(&mut w, &mut rx, Request::Sell(lines()));
        w.shop(1, "smith", Request::Sell(lines()));
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 4);
    }

    #[test]
    fn shop_legacy_sales_still_work_and_preserve_buyback() {
        let (mut w, mut rx, _) = fixture();
        w.time += 1.;
        w.interact(1, "smith", Some("sell:slime_gel:2"));
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 3);
        let reply = message(&mut w, &mut rx, Request::Open);
        assert_eq!(reply["buyBack"][0]["quantity"], 2);
        w.time += 1.;
        w.interact(1, "smith", Some("sell:materials"));
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 0);
    }
}
