//! Read-only look at another character's gear and stat sheet. The server builds a whitelist packet from the
//! target's character: it never forwards the snapshot, so gold, bags, bank, quests and positions stay private.
use super::rolls::SHARE_RANGE;
use super::*;

/// A connection may ask to inspect at most this often (the window refreshes itself every few seconds).
const INSPECT_GAP: f64 = 0.25;

impl World {
    pub(super) fn inspect(&mut self, session: u64, id: &str) {
        let Some(me) = self.players.get_mut(&session) else {
            return;
        };
        if self.time - me.inspect_at < INSPECT_GAP {
            return;
        }
        me.inspect_at = self.time;
        let me_id = me.character.id.clone();
        let packet = self.inspect_view(&me_id, id);
        if let Some(p) = self.players.get(&session) {
            let _ = p.peer.try_send(packet);
        }
    }

    /// The answer for `asker` looking at `target`. Every refusal reads the same ("unavailable"), so a hidden game
    /// master, a stranger out of range and an unknown id cannot be told apart.
    fn inspect_view(&self, asker: &str, target: &str) -> Value {
        let refused = json!({"type":"inspect","id":target,"ok":false,"reason":"unavailable"});
        let (Some(a), Some((&target_session, b))) = (
            self.online(asker),
            self.players.iter().find(|(_, p)| p.character.id == target),
        ) else {
            return refused;
        };
        if asker == target || b.is_hidden() {
            return refused;
        }
        let near = a.character.zone == b.character.zone
            && a.character.point().distance(b.character.point()) <= SHARE_RANGE;
        let known =
            self.party_mates(asker).iter().any(|m| m == target) || self.is_friend(asker, target);
        if !near && !known {
            return refused;
        }
        let c = &b.character;
        // Gear copies come from the ledger the same way `gear_attributes` reads them, so refined and merged
        // pieces read right and repeats of one item pick successive copies.
        let mut seen = std::collections::BTreeMap::<&str, usize>::new();
        let slots: Vec<Value> = c
            .worn_slots()
            .into_iter()
            .map(|(slot, i)| {
                let occurrence = seen.entry(&i.id).or_default();
                let copy = c.worn_gear_instance(&i.id, *occurrence);
                *occurrence += 1;
                let (attack, defense, bonus, rarity, rank) = copy.map_or_else(
                    || (i.attack, i.defense, i.bonus_stats.clone(), i.rarity.clone(), 0),
                    |g| (g.attack, g.defense, g.effective_bonus_stats(), g.rarity.clone(), g.rank),
                );
                let bonus = hierlooms::attributes(i, c.level).unwrap_or(bonus);
                json!({"slot":slot,"item":i.id,"name":i.name,"rarity":rarity,"level":i.required_level,
                    "xpPercent":if hierlooms::is_hierloom(i) {100} else {0},
                    "class":i.class,"attack":attack,"defense":defense,"bonus":bonus,"rank":rank,
                    "usable":i.required_level <= c.level && i.class.is_none_or(|k| k == c.look.class)})
            })
            .collect();
        let (_, defense) = c.stats();
        let attack = self.raid_attack_power(target_session);
        let hired = b.merc.is_some();
        let real = !hired && b.ambient.is_none();
        json!({"type":"inspect","id":target,"ok":true,"name":c.look.name,"look":c.look,"level":c.level,
            "reborn":{"count":c.rebirth_count(),"tier":c.rebirth_highest_tier()},
            "hired":hired,"adventurer":b.ambient.is_some(),"slots":slots,
            "stats":{"hp":c.max_hp(),"resource":c.max_resource(),"resourceType":c.look.class.resource_type(),
                "attack":attack,"defense":defense,"attributes":c.attributes,"gearAttributes":c.gear_attributes(),
                "passiveAttributes":skills::passive_bonus(c.look.class, c.level),
                "critChance":c.crit_chance(),"dodgeChance":c.dodge_chance(),"hitChance":c.hit_chance(),
                "cooldownReduction":1.-c.cooldown_multiplier()},
            "setCounts":if real { json!(c.set_counts()) } else { json!({}) }})
    }
}

#[cfg(test)]
mod tests {
    use super::super::wyrd_tests::{drain, join, world};
    use super::*;
    use crate::items::GearInstance;

    fn id_of(w: &World, session: u64) -> String {
        w.players[&session].character.id.clone()
    }
    fn answer(rx: &mut mpsc::Receiver<Value>) -> Option<Value> {
        drain(rx).into_iter().find(|p| p["type"] == "inspect")
    }
    fn texts(rx: &mut mpsc::Receiver<Value>) -> Vec<String> {
        drain(rx)
            .iter()
            .filter(|p| p["type"] == "notice")
            .filter_map(|p| p["text"].as_str().map(str::to_owned))
            .collect()
    }
    /// A clear stretch of Greenmeadow outside the city.
    fn open_spot(w: &World) -> Point {
        let map = &w.maps[0];
        let size = map.size as f64;
        let mut y = 12.;
        while y < size - 12. {
            let mut x = 12.;
            while x < size - 12. {
                let p = Point { x, y };
                let mut q = p;
                map.collide(&mut q, PLAYER_RADIUS * 3.);
                if q.distance(p) < 0.01 && !map.in_city(p) {
                    return p;
                }
                x += 2.;
            }
            y += 2.;
        }
        panic!("no open spot");
    }
    fn place(w: &mut World, session: u64, at: Point) {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.x = at.x;
        c.y = at.y;
    }

    #[test]
    fn an_adventurer_declines_trade_and_duel_and_nothing_opens() {
        let mut w = world();
        w.ambient_enabled = true;
        let mut rx = join(&mut w, 1, Class::Warrior);
        for _ in 0..100 {
            w.step();
        }
        let (session, bot) = w
            .players
            .iter()
            .find(|(_, p)| p.ambient.is_some() && p.character.zone == 0)
            .map(|(s, p)| (*s, p.character.id.clone()))
            .expect("an adventurer");
        let spot = open_spot(&w);
        place(&mut w, 1, spot);
        place(
            &mut w,
            session,
            Point {
                x: spot.x + 1.,
                y: spot.y,
            },
        );
        drain(&mut rx);
        w.trade(1, TradeCommand::Request { id: bot.clone() });
        let packets = drain(&mut rx);
        assert!(w.trades.is_empty(), "no trade record for an adventurer");
        assert!(
            packets.iter().all(|p| p["type"] != "trade"),
            "no trade window"
        );
        assert!(packets.iter().any(|p| {
            p["text"]
                .as_str()
                .is_some_and(|t| t.contains("declined your trade request"))
        }));
        w.pvp_command(1, PvpCommand::DuelRequest { id: bot.clone() });
        let notes = texts(&mut rx);
        assert!(
            notes.iter().any(|t| t.contains("declined your duel")),
            "{notes:?}"
        );
        assert!(w.no_duel_pending(), "no challenge queued");
        // The refusal is not always the same sentence.
        let mut lines = std::collections::BTreeSet::new();
        for _ in 0..40 {
            w.tick += 7;
            w.trade(1, TradeCommand::Request { id: bot.clone() });
            lines.extend(texts(&mut rx));
        }
        assert!(lines.len() >= 3, "{lines:?}");
        // Out of reach, an adventurer is refused like a person (the request never goes out).
        place(
            &mut w,
            session,
            Point {
                x: spot.x + 30.,
                y: spot.y,
            },
        );
        w.trade(1, TradeCommand::Request { id: bot });
        assert!(texts(&mut rx).iter().any(|t| t.contains("four steps")));
    }

    #[test]
    fn inspect_answers_with_a_whitelist_and_hides_what_it_must() {
        let mut w = world();
        let mut rx1 = join(&mut w, 1, Class::Warrior);
        let mut rx2 = join(&mut w, 2, Class::Mage);
        let (one, two) = (id_of(&w, 1), id_of(&w, 2));
        let necklace = crate::items::ITEMS
            .iter()
            .find(|i| i.kind == "necklace" && i.rarity == "rare")
            .unwrap();
        {
            let c = &mut w.players.get_mut(&2).unwrap().character;
            c.gold = 987_654;
            c.equipment.insert("necklace".into(), necklace.id.clone());
            c.gear_instances.push(GearInstance {
                id: 41,
                item: necklace.id.clone(),
                rarity: "epic".into(),
                attack: 0.,
                defense: 0.,
                bonus_stats: Attributes {
                    strength: 3,
                    ..Attributes::default()
                },
                rolled_stats: Attributes::default(),
                rank: 2,
                trade_until: 0,
                trade_with: vec![],
                wear: 0,
            });
        }
        let at = open_spot(&w);
        place(&mut w, 1, at);
        place(
            &mut w,
            2,
            Point {
                x: at.x + 5.,
                y: at.y,
            },
        );
        drain(&mut rx1);
        w.inspect(1, &two);
        let reply = answer(&mut rx1).expect("an answer");
        assert_eq!(reply["ok"], true);
        assert_eq!(reply["name"], w.players[&2].character.look.name);
        assert_eq!(reply["level"], w.players[&2].character.level);
        assert_eq!(reply["hired"], false);
        let piece = reply["slots"]
            .as_array()
            .unwrap()
            .iter()
            .find(|s| s["slot"] == "necklace")
            .expect("the necklace slot");
        // The ledger copy, not the catalogue entry: epic, rank 2, three strength.
        assert_eq!(piece["rarity"], "epic");
        assert_eq!(piece["rank"], 2);
        assert_eq!(piece["bonus"]["strength"], 3);
        assert_eq!(piece["name"], necklace.name);
        // Chest and hands come from the class look, not the equipment map.
        for slot in ["chest", "hands"] {
            assert!(
                reply["slots"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|s| s["slot"] == slot),
                "{slot}"
            );
        }
        let c = &w.players[&2].character;
        let (attack, defense) = c.stats();
        assert_eq!(reply["stats"]["attack"].as_f64().unwrap(), attack);
        assert_eq!(reply["stats"]["defense"].as_f64().unwrap(), defense);
        assert_eq!(reply["stats"]["hp"].as_f64().unwrap(), c.max_hp());
        assert_eq!(
            reply["stats"]["critChance"].as_f64().unwrap(),
            c.crit_chance()
        );
        assert_eq!(
            reply["stats"]["attributes"]["strength"],
            c.attributes.strength
        );
        assert_eq!(reply["stats"]["resourceType"], "mana");
        for key in [
            "gold",
            "inventory",
            "bags",
            "quests",
            "x",
            "y",
            "zone",
            "gearInstances",
            "explored",
            "friends",
        ] {
            assert!(reply.get(key).is_none(), "{key} must not travel");
        }
        let text = reply.to_string();
        assert!(!text.contains("987654"), "gold amount leaked");
        // One request per quarter second per connection.
        w.inspect(1, &two);
        assert!(answer(&mut rx1).is_none(), "rate limited");
        w.time += 1.;
        // Out of range: refused, and the refusal is the same for a stranger, an unknown id and a hidden GM.
        place(
            &mut w,
            2,
            Point {
                x: at.x + 90.,
                y: at.y,
            },
        );
        w.inspect(1, &two);
        let far = answer(&mut rx1).unwrap();
        assert_eq!(far["ok"], false);
        w.time += 1.;
        w.inspect(1, "nobody");
        let unknown = answer(&mut rx1).unwrap();
        assert_eq!(far["reason"], unknown["reason"]);
        // Party or friends are reachable from afar.
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .friends
            .push(two.clone());
        w.time += 1.;
        w.inspect(1, &two);
        assert_eq!(answer(&mut rx1).unwrap()["ok"], true);
        w.players.get_mut(&1).unwrap().character.friends.clear();
        // A hidden GM cannot be inspected even when standing next to the asker.
        place(
            &mut w,
            2,
            Point {
                x: at.x + 3.,
                y: at.y,
            },
        );
        {
            let p = w.players.get_mut(&2).unwrap();
            p.character.gm = true;
            p.hidden = true;
        }
        w.time += 1.;
        w.inspect(1, &two);
        let hidden = answer(&mut rx1).unwrap();
        assert_eq!(hidden["ok"], false);
        assert_eq!(hidden["reason"], unknown["reason"]);
        // Nobody inspects themselves.
        w.time += 1.;
        w.inspect(1, &one);
        assert_eq!(answer(&mut rx1).unwrap()["ok"], false);
        // A hired fighter answers as an adventurer does, marked hired, with no set bonuses listed.
        {
            let p = w.players.get_mut(&2).unwrap();
            p.character.gm = false;
            p.merc = Some(one.clone());
        }
        w.time += 1.;
        w.inspect(1, &two);
        let hired = answer(&mut rx1).unwrap();
        assert_eq!(hired["ok"], true);
        assert_eq!(hired["hired"], true);
        assert_eq!(hired["setCounts"], json!({}));
        drain(&mut rx2);
    }
}
