//! Spark Travel: discovered, connected stops, authoritative fares and uninterrupted airborne journeys.
use super::*;

const LEG_COST: u32 = 20;
const SPEED: f64 = 3.;
/// Tiles of flight one more stop on a route has to save: about a second and a half in the air.
const LEG_HANDICAP: f64 = 20.;

impl World {
    /// Entering a master's own city or camp discovers that stop, without opening a dialogue
    /// or granting talk-objective credit. Flying over a hub does not count as a visit.
    pub(super) fn update_spark_discovery(&mut self) {
        let mut changed = false;
        for player in self.players.values_mut() {
            let c = &mut player.character;
            if c.hp <= 0.
                || c.spark_travel.is_some()
                || player.merc.is_some()
                || player.ambient.is_some()
                || player.guard.is_some()
            {
                continue;
            }
            let Some(map) = self.maps.get(c.zone) else {
                continue;
            };
            if map.copies > 0 || map.template.is_some() {
                continue;
            }
            let here = c.point();
            for npc in &map.npcs {
                let Some(name) = &npc.travel_stop else {
                    continue;
                };
                if c.travel_stops.contains(&npc.id) {
                    continue;
                }
                let at = npc.position_at(self.time);
                let entered = map
                    .city
                    .iter()
                    .chain(&map.camps)
                    .any(|hub| hub.contains(here) && hub.contains(at));
                if entered || here.distance(at) <= 2.8 {
                    c.travel_stops.push(npc.id.clone());
                    let _ = player.peer.try_send(json!({"type":"announce","kind":"info",
                        "text":format!("Discovered {name} for Spark Travel.")}));
                    changed = true;
                }
            }
        }
        if changed {
            self.save();
        }
    }

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

    /// Every station outside the private copies, in map order.
    fn spark_stations(&self) -> Vec<(usize, &Npc)> {
        self.maps
            .iter()
            .enumerate()
            .filter(|(_, m)| m.copies == 0 && m.template.is_none())
            .flat_map(|(zone, m)| m.npcs.iter().map(move |n| (zone, n)))
            .filter(|(_, n)| n.travel_stop.is_some())
            .collect()
    }

    /// One leg as it is flown: straight over a zone, or to the crossing that makes the shortest
    /// flight and on from its far side. `None` when the two zones share no open crossing.
    fn spark_leg(&self, a: (usize, &Npc), b: (usize, &Npc)) -> Option<(f64, Option<&Portal>)> {
        let (from, to) = (Point { x: a.1.x, y: a.1.y }, Point { x: b.1.x, y: b.1.y });
        if a.0 == b.0 {
            return Some((from.distance(to), None));
        }
        self.maps[a.0]
            .portals
            .iter()
            .filter(|g| g.to == b.0 && !g.after_clear)
            .map(|g| {
                let length = from.distance(Point { x: g.x, y: g.y })
                    + Point { x: g.tx, y: g.ty }.distance(to);
                (length, Some(g))
            })
            .min_by(|x, y| x.0.total_cmp(&y.0))
    }

    /// The fastest route to every station that can be reached: the least flight, where one more
    /// stop has to save `LEG_HANDICAP` tiles to be worth making. Unknown stops cannot be bypassed.
    fn spark_routes(&self, from: &str) -> BTreeMap<String, Vec<String>> {
        let stations = self.spark_stations();
        let index: BTreeMap<&str, usize> = stations
            .iter()
            .enumerate()
            .map(|(i, (_, n))| (n.id.as_str(), i))
            .collect();
        let mut cost = vec![f64::INFINITY; stations.len()];
        let mut prev = vec![usize::MAX; stations.len()];
        let mut done = vec![false; stations.len()];
        let Some(&start) = index.get(from) else {
            return BTreeMap::new();
        };
        cost[start] = 0.;
        // Stations are few: a plain scan keeps equal routes in map order, the same on every run.
        while let Some(at) = (0..stations.len())
            .filter(|&i| !done[i] && cost[i].is_finite())
            .min_by(|&a, &b| cost[a].total_cmp(&cost[b]))
        {
            done[at] = true;
            for link in &stations[at].1.travel_links {
                let Some(&next) = index.get(link.as_str()) else {
                    continue;
                };
                let Some((length, _)) = self.spark_leg(stations[at], stations[next]) else {
                    continue;
                };
                if cost[at] + length + LEG_HANDICAP < cost[next] {
                    cost[next] = cost[at] + length + LEG_HANDICAP;
                    prev[next] = at;
                }
            }
        }
        (0..stations.len())
            .filter(|&i| done[i])
            .map(|i| {
                let mut route = vec![stations[i].1.id.clone()];
                let mut at = i;
                while prev[at] != usize::MAX {
                    at = prev[at];
                    route.push(stations[at].1.id.clone());
                }
                route.reverse();
                (stations[i].1.id.clone(), route)
            })
            .collect()
    }

    fn spark_route(&self, from: &str, to: &str) -> Option<Vec<String>> {
        self.spark_routes(from).remove(to)
    }

    fn spark_options(&self, session: u64, from: &str) -> Vec<Value> {
        let c = &self.players[&session].character;
        let routes = self.spark_routes(from);
        self.maps.iter().filter(|m| m.copies == 0 && m.template.is_none()).flat_map(|m| &m.npcs)
            .filter(|n| n.travel_stop.is_some() && n.id != from).map(|n| {
                let route = routes.get(&n.id);
                let missing: Vec<_> = route.into_iter().flatten().filter(|id| !c.travel_stops.contains(id)).filter_map(|id| self.travel_master(id).map(|(_, n)| n.travel_stop.clone().unwrap())).collect();
                let cost = route.map(|r| c.spark_fare((r.len() as u32 - 1) * LEG_COST));
                let stops: Vec<_> = route.into_iter().flatten().filter_map(|id| self.travel_master(id).map(|(_, n)| n.travel_stop.clone().unwrap())).collect();
                let reason = if route.is_none() { "No connected Spark Travel route.".into() }
                    else if !missing.is_empty() { format!("Visit {} to discover its travel master first.", missing.join(", ")) }
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
                "Visit {} to discover its travel master first.",
                self.travel_master(id)
                    .unwrap()
                    .1
                    .travel_stop
                    .as_ref()
                    .unwrap()
            ));
        }
        let cost = c.spark_fare((stops.len() as u32 - 1) * LEG_COST);
        if c.gold < cost {
            return Err(format!(
                "Spark Travel costs {}. You do not have enough.",
                money_text(cost)
            ));
        }
        let mut points = vec![];
        for pair in stops.windows(2) {
            let from = self.travel_master(&pair[0]).unwrap();
            let (b, next) = self.travel_master(&pair[1]).unwrap();
            let (_, gate) = self
                .spark_leg(from, (b, next))
                .ok_or("This Spark Travel leg has no gate.")?;
            if let Some(gate) = gate {
                if c.level < self.maps[b].min_level {
                    return Err("You are below this route's required level.".into());
                }
                points.push(SparkPoint {
                    zone: from.0,
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
        p.character.mounted = false;
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
        let _ = p.peer.try_send(json!({"type":"notice","ok":true,"text":format!("Spark Travel to {destination}: {}.", money_text(cost))}));
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
        p.spark_at = self.time;
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
    // The fastest flight from Alderhaven to the Rimeward Camp crosses Skaldholm.
    const B: &str = "travel_skaldholm";
    const C: &str = "travel_rimeward";
    const D: &str = "travel_lanternmere";

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
        // Fourteen hubs when this was written; every zone since has added one, and each is checked below.
        assert!(hubs.len() >= 14, "{} hubs", hubs.len());
        for (index, map) in hubs {
            let masters: Vec<_> = map
                .npcs
                .iter()
                .filter(|n| n.travel_stop.is_some())
                .collect();
            // one master in every hub: the Wyrdwood has two hubs, Hollowmoot and Skuldwatch.
            // Nacrehold's camps are the districts of the one city, which share its master.
            let hubs = if map.name == "Nacrehold" {
                1
            } else {
                1 + map.camps.len()
            };
            assert_eq!(masters.len(), hubs, "{}", map.name);
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
        // Neighbouring hubs are one leg; a farther hub takes three.
        assert_eq!(w.spark_route(A, C).unwrap(), [A, B, C]);
        assert_eq!(w.spark_route(D, B).unwrap(), [D, B]);
        assert_eq!(w.spark_route(A, B).unwrap(), [A, B]);
        assert_eq!(
            w.spark_route(A, "travel_cinderwatch").unwrap(),
            [A, "travel_cinderwatch"]
        );
        let far = w.spark_route(A, "travel_hollowmoot").unwrap();
        assert_eq!((far.first().map(String::as_str), far.len()), (Some(A), 4));
    }

    /// What a route costs the search: its flight plus the handicap of every leg.
    fn weighed(w: &World, route: &[String]) -> f64 {
        route
            .windows(2)
            .map(|pair| {
                let a = w.travel_master(&pair[0]).unwrap();
                let b = w.travel_master(&pair[1]).unwrap();
                w.spark_leg(a, b).unwrap().0 + LEG_HANDICAP
            })
            .sum()
    }

    #[test]
    fn spark_routes_are_the_fastest_flights_between_every_pair_of_stations() {
        let (w, _, _) = world(Class::Warrior);
        let stations = w.spark_stations();
        let n = stations.len();
        assert!(n >= 94, "{n} stations");
        // A second opinion, worked out another way: all pairs at once.
        let mut best = vec![vec![f64::INFINITY; n]; n];
        for (i, a) in stations.iter().enumerate() {
            best[i][i] = 0.;
            for link in &a.1.travel_links {
                let j = stations
                    .iter()
                    .position(|s| &s.1.id == link)
                    .unwrap_or_else(|| panic!("{} links to {link}, no station", a.1.id));
                let (length, _) = w
                    .spark_leg(*a, stations[j])
                    .unwrap_or_else(|| panic!("{} to {link} has no open crossing", a.1.id));
                assert!(stations[j].1.travel_links.contains(&a.1.id), "{link} back");
                best[i][j] = length + LEG_HANDICAP;
            }
        }
        for k in 0..n {
            for i in 0..n {
                for j in 0..n {
                    best[i][j] = best[i][j].min(best[i][k] + best[k][j]);
                }
            }
        }
        for (i, a) in stations.iter().enumerate() {
            let routes = w.spark_routes(&a.1.id);
            assert_eq!(routes.len(), n, "every station is reached from {}", a.1.id);
            for (j, b) in stations.iter().enumerate() {
                let route = &routes[&b.1.id];
                assert_eq!(
                    (route.first(), route.last()),
                    (Some(&a.1.id), Some(&b.1.id))
                );
                let unique: std::collections::BTreeSet<_> = route.iter().collect();
                assert_eq!(unique.len(), route.len(), "{route:?} visits a stop twice");
                assert!(
                    (weighed(&w, route) - best[i][j]).abs() < 1e-6,
                    "{route:?} takes {} where {} is possible",
                    weighed(&w, route),
                    best[i][j]
                );
            }
        }
        // Under the first-found route with the fewest legs this flight went by Rootfoot, three times as far.
        let route = w.spark_route("travel_banyan", "travel_gladewatch").unwrap();
        assert!(weighed(&w, &route) < 300., "{route:?}");
    }

    #[test]
    fn spark_links_follow_the_crossings_that_exist_now() {
        let (w, _, _) = world(Class::Warrior);
        let stations = w.spark_stations();
        let linked =
            |a: &Npc, b: &Npc| a.travel_links.contains(&b.id) && b.travel_links.contains(&a.id);
        let nearest = |zone: usize, x: f64, y: f64| {
            stations
                .iter()
                .filter(|s| s.0 == zone)
                .min_by(|a, b| {
                    let at = Point { x, y };
                    at.distance(Point { x: a.1.x, y: a.1.y })
                        .total_cmp(&at.distance(Point { x: b.1.x, y: b.1.y }))
                })
                .map(|s| s.1)
        };
        // Two stations of one zone are a straight flight apart.
        for a in &stations {
            for b in stations.iter().filter(|b| b.0 == a.0 && b.1.id != a.1.id) {
                assert!(linked(a.1, b.1), "{} and {}", a.1.id, b.1.id);
                assert_eq!(w.spark_route(&a.1.id, &b.1.id).unwrap().len(), 2);
            }
        }
        // Every crossing between two zones with stations joins the stations nearest to it.
        let mut crossings = 0;
        for (zone, map) in w.maps.iter().enumerate() {
            for gate in map.portals.iter().filter(|g| !g.after_clear) {
                let back = w.maps[gate.to]
                    .portals
                    .iter()
                    .any(|g| g.to == zone && !g.after_clear);
                let (Some(a), Some(b)) = (
                    nearest(zone, gate.x, gate.y),
                    nearest(gate.to, gate.tx, gate.ty),
                ) else {
                    continue;
                };
                if !back || zone == gate.to {
                    continue;
                }
                assert!(linked(a, b), "{} joins {} and {}", gate.id, a.id, b.id);
                crossings += 1;
            }
        }
        assert!(crossings >= 90, "{crossings} crossings carry a link");
    }

    #[test]
    fn spark_talk_can_still_discover_a_nearby_master_and_saves_once() {
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
        assert!(third["reason"].as_str().unwrap().contains("Skaldholm"));
    }

    #[test]
    fn spark_hub_entry_discovers_and_persists_without_talking_or_repeating_the_notice() {
        let (mut w, mut rx, token) = world(Class::Warrior);
        let hub = w.maps[0].city.as_ref().unwrap().clone();
        let point = Point {
            x: hub.x0 + 1.,
            y: hub.y0 + 1.,
        };
        let master = w.travel_master(A).unwrap().1.position_at(w.time);
        assert!(point.distance(master) > 2.8);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = 0;
        c.x = point.x;
        c.y = point.y;
        let gold = c.gold;
        drain(&mut rx);
        w.update_spark_discovery();
        w.update_spark_discovery();
        assert_eq!(w.players[&1].character.travel_stops, [A]);
        assert_eq!(w.players[&1].character.gold, gold);
        assert_eq!(w.store.load(&token).unwrap().unwrap().travel_stops, [A]);
        let packets = drain(&mut rx);
        assert_eq!(
            packets.iter().filter(|p| p["type"] == "announce").count(),
            1
        );
        assert!(!packets.iter().any(|p| p["type"] == "dialogue"));
    }

    #[test]
    fn spark_hub_entry_requires_a_living_grounded_hero_and_unlocks_only_the_visited_hub() {
        let (mut w, _, _) = world(Class::Warrior);
        stand(&mut w, A);
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        w.update_spark_discovery();
        assert!(w.players[&1].character.travel_stops.is_empty());
        w.players.get_mut(&1).unwrap().character.hp = 120.;
        // The ordinary flight path passes over hubs, but must not discover them in transit.
        w.players.get_mut(&1).unwrap().character.spark_travel = Some(SparkTravel {
            destination: "Skaldholm".into(),
            stops: vec![],
            points: vec![],
            next: 0,
        });
        w.update_spark_discovery();
        assert!(w.players[&1].character.travel_stops.is_empty());
        w.players.get_mut(&1).unwrap().character.spark_travel = None;
        stand(&mut w, "travel_stonefold");
        w.update_spark_discovery();
        assert_eq!(w.players[&1].character.travel_stops, ["travel_stonefold"]);
        stand(&mut w, "travel_saltby");
        w.update_spark_discovery();
        assert_eq!(
            w.players[&1].character.travel_stops,
            ["travel_stonefold", "travel_saltby"]
        );
    }

    #[test]
    fn spark_missing_intermediate_and_unknown_destinations_cannot_spend_gold() {
        let (mut w, _, _) = world(Class::Mage);
        talk(&mut w, A);
        talk(&mut w, C);
        stand(&mut w, A);
        assert!(w.spark_start(1, A, C).unwrap_err().contains("Skaldholm"));
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
