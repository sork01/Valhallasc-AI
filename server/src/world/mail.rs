use super::*;
impl World {
    pub(super) fn mail(&mut self, session: u64, npc: &str, request: crate::mail::Request) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let c = &p.character;
        let refusal = if p.merc.is_some() || p.ambient.is_some() {
            Some("Only player characters can use mail.")
        } else if c.hp <= 0. {
            Some("You cannot use mail while defeated.")
        } else if p.frozen {
            Some("You cannot use mail right now.")
        } else if p.combat_left > 0. {
            Some("Leave combat before using mail.")
        } else if c.mounted {
            Some("Dismount first.")
        } else if c.spark_travel.is_some() {
            Some("You cannot use mail while travelling.")
        } else if self.trade_index(&c.id).is_some() {
            Some("Finish your trade before using mail.")
        } else if !self.maps[c.zone].npcs.iter().any(|n| {
            n.id == npc
                && n.offers.iter().any(|o| o.id == "mail")
                && c.point().distance(n.position_at(self.time)) <= crate::mail::RANGE
        }) {
            Some("Walk closer to a mailbox.")
        } else {
            None
        };
        let notify_others = matches!(
            &request,
            crate::mail::Request::Send { .. } | crate::mail::Request::Return { .. }
        );
        let outcome = match refusal {
            Some(reason) => Err(reason.to_owned()),
            None => self.store.mail(c, request),
        };
        let mut packet = match outcome {
            Ok((next, packet)) => {
                self.players.get_mut(&session).unwrap().character = next;
                packet
            }
            Err(notice) => json!({"type":"mail","ok":false,"notice":notice}),
        };
        packet["npc"] = json!(npc);
        let notify_others = notify_others && packet["ok"] == true;
        let _ = self.players[&session].peer.try_send(packet);
        for (peer_session, p) in self.players.iter().filter(|(peer_session, p)| {
            (**peer_session == session || notify_others) && p.merc.is_none() && p.ambient.is_none()
        }) {
            if let Ok(counts) = self.store.mail_counts(&p.character.id) {
                let previous = self.mail_unread.insert(p.character.id.clone(), counts);
                if previous != Some(counts) || *peer_session == session {
                    let _ = p.peer.try_send(json!({"type":"mail_unread","count":counts.0,"total":counts.1}));
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (World, mpsc::Receiver<Value>, mpsc::Receiver<Value>) {
        let mut w =
            World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
        let (tx, rx) = mpsc::channel(512);
        w.join(
            1,
            None,
            Some(Look {
                name: "Mail Sender".into(),
                ..Default::default()
            }),
            tx,
        )
        .unwrap();
        let (tx, other) = mpsc::channel(512);
        w.join(
            2,
            None,
            Some(Look {
                name: "Mail Recipient".into(),
                ..Default::default()
            }),
            tx,
        )
        .unwrap();
        let box_npc = w.maps[0]
            .npcs
            .iter()
            .find(|n| n.offers.iter().any(|o| o.id == "mail"))
            .unwrap();
        let (x, y) = (box_npc.x, box_npc.y);
        for p in w.players.values_mut() {
            p.character.x = x;
            p.character.y = y;
        }
        (w, rx, other)
    }
    fn last(rx: &mut mpsc::Receiver<Value>) -> Value {
        let mut last = Value::Null;
        while let Ok(p) = rx.try_recv() {
            if p["type"] == "mail" {
                last = p;
            }
        }
        last
    }
    fn open(w: &mut World, npc: &str) {
        w.message(
            1,
            ClientMessage::Mail {
                npc: npc.into(),
                request: crate::mail::Request::Open,
            },
        );
    }
    #[test]
    fn mail_world_access_rechecks_range_combat_life_mount_travel_and_service_identity() {
        let (mut w, mut rx, _) = fixture();
        let npc = w.maps[0]
            .npcs
            .iter()
            .find(|n| n.offers.iter().any(|o| o.id == "mail"))
            .unwrap()
            .id
            .clone();
        open(&mut w, &npc);
        assert_eq!(last(&mut rx)["ok"], true);
        open(&mut w, "guide");
        assert_eq!(last(&mut rx)["ok"], false);
        w.players.get_mut(&1).unwrap().character.x += 10.;
        open(&mut w, &npc);
        assert_eq!(last(&mut rx)["ok"], false);
        w.players.get_mut(&1).unwrap().character.x -= 10.;
        w.players.get_mut(&1).unwrap().combat_left = 2.;
        open(&mut w, &npc);
        assert!(last(&mut rx)["notice"].as_str().unwrap().contains("combat"));
        w.players.get_mut(&1).unwrap().combat_left = 0.;
        w.players.get_mut(&1).unwrap().character.mounted = true;
        open(&mut w, &npc);
        assert_eq!(last(&mut rx)["notice"], "Dismount first.");
        w.players.get_mut(&1).unwrap().character.mounted = false;
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        open(&mut w, &npc);
        assert!(
            last(&mut rx)["notice"]
                .as_str()
                .unwrap()
                .contains("defeated")
        );
        w.players.get_mut(&1).unwrap().character.hp = 100.;
        w.players.get_mut(&1).unwrap().character.spark_travel = Some(crate::model::SparkTravel {
            destination: "Skaldholm".into(),
            stops: vec![],
            points: vec![],
            next: 0,
        });
        open(&mut w, &npc);
        assert!(
            last(&mut rx)["notice"]
                .as_str()
                .unwrap()
                .contains("travelling")
        );
        w.players.get_mut(&1).unwrap().character.spark_travel = None;
        // NPCs and hires never have persisted recipient identities; automated actors cannot act as senders either.
        w.players.get_mut(&1).unwrap().merc = Some("owner".into());
        open(&mut w, &npc);
        assert_eq!(last(&mut rx)["ok"], false);
    }
    #[test]
    fn mail_online_delivery_notifications_and_private_snapshot_counts() {
        let (mut w, mut rx, mut other) = fixture();
        let npc = w.maps[0]
            .npcs
            .iter()
            .find(|n| n.offers.iter().any(|o| o.id == "mail"))
            .unwrap()
            .id
            .clone();
        w.message(
            1,
            ClientMessage::Mail {
                npc,
                request: crate::mail::Request::Send {
                    request: "world-mail-receipt-0001".into(),
                    recipient: "Mail Recipient".into(),
                    subject: "Hello".into(),
                    body: "Online letter".into(),
                    gold: 0,
                    attachments: vec![],
                },
            },
        );
        assert_eq!(last(&mut rx)["ok"], true);
        let mut notified = false;
        while let Ok(p) = other.try_recv() {
            if p["type"] == "mail_unread" && p["count"] == 1 {
                notified = true;
            }
        }
        assert!(notified);
        let id = w.players[&1].character.id.clone();
        let other_id = w.players[&2].character.id.clone();
        let mut v = w.snapshot_for(0);
        crate::visibility::filter_view(&mut v, &id);
        assert!(
            v["players"]
                .as_array()
                .unwrap()
                .iter()
                .find(|p| p["id"] == other_id)
                .unwrap()
                .get("mailUnread")
                .is_none()
        );
        assert_eq!(
            v["players"]
                .as_array()
                .unwrap()
                .iter()
                .find(|p| p["id"] == id)
                .unwrap()["mailUnread"],
            0
        );
    }
    #[test]
    fn mail_all_authored_hub_mailboxes_have_safe_reachable_approaches_and_work() {
        let (mut w, mut rx, _) = fixture();
        let directory: Vec<Value> =
            serde_json::from_str(include_str!("../../../world/mailboxes.txt")).unwrap();
        let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
        let zones: Vec<_> = std::iter::once(&raw)
            .chain(raw["zones"].as_array().unwrap())
            .collect();
        let mut hubs = std::collections::BTreeSet::new();
        for (zi, z) in zones.iter().enumerate() {
            for c in std::iter::once(&z["city"]).chain(z["camps"].as_array().into_iter().flatten())
            {
                if let Some(name) = c["name"].as_str() {
                    hubs.insert((zi, name.to_owned()));
                }
            }
            for n in z["npcs"].as_array().unwrap() {
                if let Some(name) = n["travelStop"].as_str() {
                    hubs.insert((zi, name.to_owned()));
                }
            }
        }
        let recorded = directory
            .iter()
            .map(|d| {
                (
                    d["zone"].as_u64().unwrap() as usize,
                    d["hub"].as_str().unwrap().to_owned(),
                )
            })
            .collect();
        assert_eq!(hubs, recorded);
        assert_eq!(hubs.len(), directory.len());
        for d in directory {
            let zi = d["zone"].as_u64().unwrap() as usize;
            let id = d["id"].as_str().unwrap();
            let map = &w.maps[zi];
            let n = map.npcs.iter().find(|n| n.id == id).unwrap();
            let point = Point { x: n.x, y: n.y };
            let mut resolved = point;
            map.collide(&mut resolved, 0.6);
            assert!(point.distance(resolved) < 0.01, "{} blocked", d["hub"]);
            let anchor = Point {
                x: d["anchor"]["x"].as_f64().unwrap(),
                y: d["anchor"]["y"].as_f64().unwrap(),
            };
            assert!(map.line_clear(anchor, point, 0.4), "{} approach", d["hub"]);
            assert!(
                map.portals
                    .iter()
                    .all(|p| point.distance(Point { x: p.x, y: p.y }) > p.r + 1.5)
            );
            let p = w.players.get_mut(&1).unwrap();
            p.character.zone = zi;
            p.character.x = point.x;
            p.character.y = point.y;
            open(&mut w, id);
            assert_eq!(last(&mut rx)["ok"], true, "{} opens", d["hub"]);
        }
    }
}
