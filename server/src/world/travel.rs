//! Spark Travel: discovered, connected stops, authoritative fares and uninterrupted airborne journeys.
use super::*;
use std::collections::{BTreeSet, VecDeque};

const LEG_COST: u32 = 20;
const SPEED: f64 = 3.;

impl World {
    pub(super) fn spark_interact(&mut self, session: u64, npc_id: &str, offer: Option<&str>) {
        let p = &self.players[&session];
        let (zone, npc) = self.travel_master(npc_id).unwrap();
        if p.character.hp <= 0.
            || p.character.spark_travel.is_some()
            || p.character.zone != zone
            || p.character.point().distance(npc.position_at(self.time)) > 2.8
        {
            let _ = p
                .peer
                .try_send(json!({"type":"error","text":"Walk closer to the travel master."}));
            return;
        }
        let npc = npc.clone();
        let p = self.players.get_mut(&session).unwrap();
        p.stop();
        p.attack = 0.;
        for map in &self.maps {
            quest_progress(&mut p.character, &map.quests, "talk", npc_id);
        }
        let mut notice = String::new();
        if offer.is_none() && !p.character.travel_stops.iter().any(|id| id == npc_id) {
            p.character.travel_stops.push(npc_id.to_owned());
            notice = format!(
                "Discovered {} for Spark Travel.",
                npc.travel_stop.as_ref().unwrap()
            );
            self.save();
        }
        if let Some(offer) = offer {
            let p = self.players.get_mut(&session).unwrap();
            if self.time - p.service_at < 0.5 {
                notice = "Please wait a moment before trying again.".into();
            } else {
                p.service_at = self.time;
                match offer.strip_prefix("spark:") {
                    Some(to) => match self.spark_start(session, npc_id, to) {
                        Ok(()) => return,
                        Err(text) => notice = text,
                    },
                    None => notice = "Choose a Spark Travel destination.".into(),
                }
            }
        }
        let options = self.spark_options(session, npc_id);
        let p = &self.players[&session];
        let c = &p.character;
        let _ = p.peer.try_send(json!({"type":"dialogue","npc":npc,"notice":notice,"gold":c.gold,"level":c.level,"quests":c.quests,"inventory":c.inventory,"equipment":c.equipment,"bags":c.bags,"look":c.look,"travel":options,"travelStops":c.travel_stops}));
    }
    pub(super) fn travel_master(&self, id: &str) -> Option<(usize, &Npc)> {
        self.maps
            .iter()
            .enumerate()
            .filter(|(_, m)| m.copies == 0 && m.template.is_none())
            .find_map(|(zone, m)| {
                m.npcs
                    .iter()
                    .find(|n| n.id == id && n.travel_stop.is_some())
                    .map(|n| (zone, n))
            })
    }

    /// Find the shortest physical route first. Unknown intermediate stops cannot be bypassed.
    fn spark_route(&self, from: &str, to: &str) -> Option<Vec<String>> {
        self.travel_master(to)?;
        let mut queue = VecDeque::from([vec![from.to_owned()]]);
        let mut seen = BTreeSet::from([from.to_owned()]);
        while let Some(route) = queue.pop_front() {
            let last = route.last()?;
            if last == to {
                return Some(route);
            }
            let (_, master) = self.travel_master(last)?;
            for next in &master.travel_links {
                if self.travel_master(next).is_some() && seen.insert(next.clone()) {
                    let mut path = route.clone();
                    path.push(next.clone());
                    queue.push_back(path);
                }
            }
        }
        None
    }

    fn spark_options(&self, session: u64, from: &str) -> Vec<Value> {
        let c = &self.players[&session].character;
        self.maps.iter().filter(|m| m.copies == 0 && m.template.is_none()).flat_map(|m| &m.npcs)
            .filter(|n| n.travel_stop.is_some() && n.id != from).map(|n| {
                let route = self.spark_route(from, &n.id);
                let missing: Vec<_> = route.iter().flatten().filter(|id| !c.travel_stops.contains(id)).filter_map(|id| self.travel_master(id).map(|(_, n)| n.travel_stop.clone().unwrap())).collect();
                let cost = route.as_ref().map(|r| (r.len() as u32 - 1) * LEG_COST);
                let stops: Vec<_> = route.iter().flatten().filter_map(|id| self.travel_master(id).map(|(_, n)| n.travel_stop.clone().unwrap())).collect();
                let reason = if route.is_none() { "No connected Spark Travel route.".into() }
                    else if !missing.is_empty() { format!("Talk to the travel master at {} first.", missing.join(", ")) }
                    else if c.gold < cost.unwrap_or(0) { "Not enough gold.".into() } else { String::new() };
                json!({"id":n.id,"name":n.travel_stop,"cost":cost,"stops":stops,"missing":missing,"available":reason.is_empty(),"reason":reason})
            }).collect()
    }

    fn spark_start(&mut self, session: u64, from: &str, to: &str) -> Result<(), String> {
        let c = &self.players[&session].character;
        if c.hp <= 0. || c.spark_travel.is_some() {
            return Err("You cannot start Spark Travel now.".into());
        }
        let (zone, master) = self
            .travel_master(from)
            .ok_or("This is not a travel master.")?;
        if zone != c.zone || c.point().distance(master.position_at(self.time)) > 2.8 {
            return Err("Walk closer to the travel master.".into());
        }
        let stops = self
            .spark_route(from, to)
            .filter(|r| r.len() > 1)
            .ok_or("Choose a connected destination.")?;
        if let Some(id) = stops.iter().find(|id| !c.travel_stops.contains(id)) {
            return Err(format!(
                "Talk to the travel master at {} first.",
                self.travel_master(id)
                    .unwrap()
                    .1
                    .travel_stop
                    .as_ref()
                    .unwrap()
            ));
        }
        let cost = (stops.len() as u32 - 1) * LEG_COST;
        if c.gold < cost {
            return Err(format!(
                "Spark Travel costs {cost} gold. You do not have enough."
            ));
        }
        let mut points = vec![];
        for pair in stops.windows(2) {
            let (a, _) = self.travel_master(&pair[0]).unwrap();
            let (b, next) = self.travel_master(&pair[1]).unwrap();
            if a != b {
                let gate = self.maps[a]
                    .portals
                    .iter()
                    .find(|g| g.to == b && !g.after_clear)
                    .ok_or("This Spark Travel leg has no gate.")?;
                if c.level < self.maps[b].min_level {
                    return Err("You are below this route's required level.".into());
                }
                points.push(SparkPoint {
                    zone: a,
                    x: gate.x,
                    y: gate.y,
                    stop: None,
                });
                points.push(SparkPoint {
                    zone: b,
                    x: gate.tx,
                    y: gate.ty,
                    stop: None,
                });
            }
            points.push(SparkPoint {
                zone: b,
                x: next.x,
                y: next.y,
                stop: Some(pair[1].clone()),
            });
        }
        let destination = self
            .travel_master(to)
            .unwrap()
            .1
            .travel_stop
            .clone()
            .unwrap();
        let p = self.players.get_mut(&session).unwrap();
        p.character.gold -= cost;
        p.character.spark_travel = Some(SparkTravel {
            destination: destination.clone(),
            stops,
            points,
            next: 0,
        });
        p.stop();
        p.attack = 0.;
        p.dash = 0.;
        p.combat_left = 0.;
        // Old missiles and hostile targets cannot follow the spark or grant kills in flight.
        self.bolts.retain(|b| b.owner != session);
        for enemy in &mut self.slimes {
            if enemy.target == Some(session) {
                enemy.target = None;
            }
        }
        let p = &self.players[&session];
        let _ = p.peer.try_send(json!({"type":"notice","ok":true,"text":format!("Spark Travel to {destination}: {cost} gold.")}));
        self.save();
        Ok(())
    }

    /// A flight may cross a gate and reach a waypoint during one tick; preserve the remaining distance budget.
    pub(super) fn update_spark(&mut self, session: u64) -> bool {
        let p = self.players.get_mut(&session).unwrap();
        let Some(flight) = p.character.spark_travel.as_mut() else {
            return false;
        };
        let mut budget = p.character.look.class.speed() * SPEED * TICK;
        let mut visited = vec![];
        while let Some(point) = flight.points.get(flight.next) {
            let goal = Point {
                x: point.x,
                y: point.y,
            };
            if p.character.zone != point.zone {
                p.character.zone = point.zone;
                p.character.x = goal.x;
                p.character.y = goal.y;
                p.portal_at = self.time;
            } else {
                let here = Point {
                    x: p.character.x,
                    y: p.character.y,
                };
                let distance = here.distance(goal);
                let dir = here.direction(goal);
                if distance > 1e-8 {
                    p.face = dir;
                }
                let step = budget.min(distance);
                p.character.x += dir.x * step;
                p.character.y += dir.y * step;
                budget -= step;
                if step + 1e-8 < distance {
                    break;
                }
                p.character.x = goal.x;
                p.character.y = goal.y;
            }
            if let Some(id) = &point.stop {
                visited.push(id.clone());
            }
            flight.next += 1;
        }
        let finished = flight.next >= flight.points.len();
        let destination = flight.destination.clone();
        p.moving = !finished;
        p.walk += TICK * SPEED;
        for stop in visited {
            let _ = p.peer.try_send(json!({"type":"event","kind":"sparkStop","actor":p.character.id,"stop":stop,"x":p.character.x,"y":p.character.y}));
        }
        if finished {
            p.character.spark_travel = None;
            p.stop();
            p.portal_at = self.time;
            let _ = p.peer.try_send(json!({"type":"notice","ok":true,"text":format!("Spark Travel arrived at {destination}." )}));
            self.save();
        }
        true
    }
}

#[cfg(test)]
mod spark_tests {
    use super::*;
    const A: &str = "travel_alderhaven";
    const B: &str = "travel_cinderwatch";
    const C: &str = "travel_rimeward";
    const D: &str = "travel_lanternmere";
    const E: &str = "travel_skaldholm";

    fn world(class: Class) -> (World, mpsc::Receiver<Value>, String) {
        let mut w =
            World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
        let (tx, rx) = mpsc::channel(256);
        let packet = w
            .join(
                1,
                None,
                Some(Look {
                    class,
                    ..Look::default()
                }),
                tx,
            )
            .unwrap();
        w.players.get_mut(&1).unwrap().character.gold = 200;
        (w, rx, packet["token"].as_str().unwrap().into())
    }
    fn stand(w: &mut World, id: &str) {
        let (zone, n) = w.travel_master(id).unwrap();
        let point = n.position_at(w.time);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = zone;
        c.x = point.x;
        c.y = point.y;
        w.time += 0.6;
    }
    fn talk(w: &mut World, id: &str) {
        stand(w, id);
        w.interact(1, id, None);
    }
    fn drain(rx: &mut mpsc::Receiver<Value>) -> Vec<Value> {
        std::iter::from_fn(|| rx.try_recv().ok()).collect()
    }

    #[test]
    fn spark_every_hub_has_one_clear_master_and_a_reciprocal_connected_network() {
        let (w, _, _) = world(Class::Warrior);
        let hubs: Vec<_> = w
            .maps
            .iter()
            .enumerate()
            .filter(|(_, m)| m.city.is_some())
            .collect();
        assert_eq!(hubs.len(), 8);
        for (index, map) in hubs {
            let masters: Vec<_> = map
                .npcs
                .iter()
                .filter(|n| n.travel_stop.is_some())
                .collect();
            // one master in every hub: the Wyrdwood has two hubs, Hollowmoot and Skuldwatch
            assert_eq!(masters.len(), 1 + map.camps.len());
            for n in masters {
                let point = n.position_at(0.);
                let mut resolved = point;
                map.collide(&mut resolved, PLAYER_RADIUS);
                assert!(resolved.distance(point) < 1e-8, "{} blocked", n.id);
                assert!(map.in_city(point));
                assert!(
                    map.portals
                        .iter()
                        .all(|g| point.distance(Point { x: g.x, y: g.y }) > g.r + 1.)
                );
                for link in &n.travel_links {
                    let (zone, next) = w.travel_master(link).unwrap();
                    assert!(next.travel_links.contains(&n.id));
                    // a link to another zone goes through a gate; a link inside the zone is a flight over the river
                    assert!(zone == index || map.portals.iter().any(|g| g.to == zone));
                }
            }
        }
        assert_eq!(w.spark_route(A, C).unwrap(), [A, B, C]);
        assert_eq!(w.spark_route(D, E).unwrap(), [D, C, E]);
        assert_eq!(w.spark_route(A, E).unwrap(), [A, B, C, E]);
    }

    #[test]
    fn spark_discovery_requires_living_nearby_talk_and_saves_once() {
        let (mut w, mut rx, token) = world(Class::Warrior);
        w.interact(1, A, None);
        assert!(w.players[&1].character.travel_stops.is_empty());
        stand(&mut w, A);
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        w.interact(1, A, None);
        assert!(w.players[&1].character.travel_stops.is_empty());
        w.players.get_mut(&1).unwrap().character.hp = 120.;
        talk(&mut w, A);
        talk(&mut w, A);
        assert_eq!(w.players[&1].character.travel_stops, [A]);
        assert_eq!(w.store.load(&token).unwrap().unwrap().travel_stops, [A]);
        let packets = drain(&mut rx);
        let options = &packets
            .iter()
            .rev()
            .find(|p| p["type"] == "dialogue")
            .unwrap()["travel"];
        let third = options
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["id"] == C)
            .unwrap();
        assert_eq!(third["cost"], 40);
        assert_eq!(third["available"], false);
        assert!(third["reason"].as_str().unwrap().contains("Cinderwatch"));
    }

    #[test]
    fn spark_missing_intermediate_and_unknown_destinations_cannot_spend_gold() {
        let (mut w, _, _) = world(Class::Mage);
        talk(&mut w, A);
        talk(&mut w, C);
        stand(&mut w, A);
        assert!(w.spark_start(1, A, C).unwrap_err().contains("Cinderwatch"));
        assert!(w.spark_start(1, A, "bogus").is_err());
        assert!(w.spark_start(1, A, A).is_err());
        assert!(w.spark_start(1, A, B).is_err());
        assert_eq!(w.players[&1].character.gold, 200);
        assert!(w.players[&1].character.spark_travel.is_none());
    }

    #[test]
    fn spark_fare_is_per_leg_in_both_directions_and_refuses_poor_remote_dead_heroes() {
        let (mut w, _, _) = world(Class::Mage);
        for id in [A, B, C] {
            talk(&mut w, id);
        }
        assert!(w.spark_start(1, A, C).is_err()); // at the other master
        stand(&mut w, A);
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        assert!(w.spark_start(1, A, C).is_err());
        w.players.get_mut(&1).unwrap().character.hp = 80.;
        w.players.get_mut(&1).unwrap().character.gold = 39;
        assert!(w.spark_start(1, A, C).is_err());
        assert_eq!(w.players[&1].character.gold, 39);
        w.players.get_mut(&1).unwrap().character.gold = 40;
        w.spark_start(1, A, C).unwrap();
        assert_eq!(w.players[&1].character.gold, 0);
        assert!(w.spark_start(1, A, C).is_err());
        for _ in 0..1000 {
            w.update_spark(1);
        }
        assert_eq!(w.players[&1].character.zone, 2);
        w.players.get_mut(&1).unwrap().character.gold = 20;
        w.spark_start(1, C, B).unwrap();
        assert_eq!(w.players[&1].character.gold, 0);
    }

    #[test]
    fn spark_follows_every_stop_at_three_times_each_class_speed_and_lands_on_clear_ground() {
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let (mut w, mut rx, _) = world(class);
            for id in [A, B, C] {
                talk(&mut w, id);
            }
            stand(&mut w, A);
            drain(&mut rx);
            w.spark_start(1, A, C).unwrap();
            let before = w.players[&1].character.point();
            w.update_spark(1);
            assert!(
                (before.distance(w.players[&1].character.point()) - class.speed() * 3. * TICK)
                    .abs()
                    < 1e-8
            );
            let mut ticks = 1;
            while w.players[&1].character.spark_travel.is_some() {
                w.update_spark(1);
                ticks += 1;
                assert!(ticks < 1000);
            }
            let c = &w.players[&1].character;
            assert_eq!(c.zone, 2);
            assert_eq!(c.gold, 160);
            let point = w.travel_master(C).unwrap().1.position_at(w.time);
            assert!(c.point().distance(point) < 1e-8);
            let stops: Vec<_> = drain(&mut rx)
                .into_iter()
                .filter(|p| p["kind"] == "sparkStop")
                .map(|p| p["stop"].as_str().unwrap().to_owned())
                .collect();
            assert_eq!(stops, [B, C]);
            assert_eq!(c.travel_stops.len(), 3);
        }
    }

    #[test]
    fn spark_is_airborne_does_not_aggro_take_damage_attack_or_accept_ground_actions() {
        let (mut w, mut rx, _) = world(Class::Assassin);
        talk(&mut w, A);
        talk(&mut w, B);
        stand(&mut w, A);
        w.spark_start(1, A, B).unwrap();
        // Place the flying hero directly over a slime, outside the city's sanctuary.
        let at = w.slimes[0].point();
        let p = w.players.get_mut(&1).unwrap();
        p.character.x = at.x;
        p.character.y = at.y;
        p.character.hp = 50.;
        p.character.spark_travel.as_mut().unwrap().points[0] = SparkPoint {
            zone: 0,
            x: at.x + 30.,
            y: at.y,
            stop: None,
        };
        w.slimes[0].target = Some(1);
        let before = w.players[&1].character.point();
        w.message(1, ClientMessage::Stop);
        w.message(1, ClientMessage::Move { x: 1., y: 1. });
        w.message(1, ClientMessage::Attack { fx: 1., fy: 0. });
        w.message(1, ClientMessage::Dash { dx: 1., dy: 0. });
        w.message(
            1,
            ClientMessage::Skill {
                id: "fan_knives".into(),
                fx: 1.,
                fy: 0.,
            },
        );
        w.message(
            1,
            ClientMessage::Interact {
                npc: A.into(),
                offer: None,
            },
        );
        w.hurt_player_by(1, 9999., at, "green", 2);
        assert_eq!(w.players[&1].character.hp, 50.);
        assert_eq!(w.players[&1].combat_left, 0.);
        assert!(w.players[&1].goal.is_none());
        assert_eq!(w.players[&1].attack, 0.);
        assert_eq!(w.players[&1].dash, 0.);
        assert!(
            w.actor_bodies(0, None, Some(0))
                .iter()
                .all(|(p, _)| p.distance(before) > 1e-8)
        );
        for _ in 0..20 {
            w.step();
            drain(&mut rx);
        }
        assert_eq!(w.players[&1].character.hp, 50.);
        assert!(w.slimes.iter().all(|s| s.target != Some(1)));
        assert_eq!(w.players[&1].character.kills, 0);
    }

    #[test]
    fn spark_restart_resumes_the_paid_journey_and_preserves_discovery() {
        let (mut w, mut rx, token) = world(Class::Warrior);
        for id in [A, B, C] {
            talk(&mut w, id);
        }
        stand(&mut w, A);
        w.spark_start(1, A, C).unwrap();
        for _ in 0..15 {
            w.update_spark(1);
        }
        w.leave(1);
        drain(&mut rx);
        let mut resumed = World::with_level_spread(w.store.clone(), 0);
        let (tx, mut rx) = mpsc::channel(256);
        resumed.join(2, Some(token.clone()), None, tx).unwrap();
        assert_eq!(resumed.players[&2].character.gold, 160);
        assert_eq!(resumed.players[&2].character.travel_stops, [A, B, C]);
        assert!(resumed.players[&2].character.spark_travel.is_some());
        for _ in 0..1000 {
            resumed.update_spark(2);
            drain(&mut rx);
        }
        let saved = resumed.store.load(&token).unwrap().unwrap();
        assert_eq!(saved.zone, 2);
        assert_eq!(saved.gold, 160);
        assert!(saved.spark_travel.is_none());
    }
}
