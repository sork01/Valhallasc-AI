//! Outpost and town guards that protect open-world hubs against lured or stray enemies without
//! trivializing zone elites or leaking player XP/loot/quest credit (`OUTPOST-GUARDS`).
use super::*;

/// Session ID floor for outpost guards (`1 << 61`), disjoint from real sessions and `MERC_BASE` (`1 << 62`).
pub(super) const GUARD_BASE: u64 = 1 << 61;
/// Seconds before a fallen guard returns to their post, preventing respawn-zerging against elites.
pub(super) const GUARD_RESPAWN_DELAY: f64 = 25.0;
const GUARDS_PER_HUB: usize = 2;
/// Maximum distance from a hub rectangle before any living enemy triggers a guard response.
const GUARD_AGGRO_CLOSE: f64 = 3.0;
/// Extended perimeter radius for enemies actively chasing, winding up, lunging, or returning from a lure.
const GUARD_AGGRO_ACTIVE: f64 = 6.5;
/// Hard leash beyond a hub rectangle: guards break off beyond this distance and return to post.
const GUARD_TETHER: f64 = 12.0;

#[derive(Clone)]
pub(super) struct Guard {
    pub hub: City,
    pub post: Point,
    pub home_face: Point,
}

/// Shortest Euclidean distance from `point` to the axis-aligned `hub` sanctuary box (0 inside).
pub(super) fn dist_to_rect(hub: &City, point: Point) -> f64 {
    let dx = if point.x < hub.x0 {
        hub.x0 - point.x
    } else if point.x > hub.x1 {
        point.x - hub.x1
    } else {
        0.
    };
    let dy = if point.y < hub.y0 {
        hub.y0 - point.y
    } else if point.y > hub.y1 {
        point.y - hub.y1
    } else {
        0.
    };
    dx.hypot(dy)
}

/// All distinct outposts/towns in an open-world hostile zone that should be guarded.
pub(super) fn hubs_for_map(map: &Map) -> Vec<(City, bool)> {
    if map.template.is_some()
        || map.copies > 0
        || map.raid
        || !map.slimes.iter().any(|s| s.ambush.is_none())
    {
        return Vec::new();
    }
    let mut hubs: Vec<(City, bool)> = Vec::new();
    let matches_existing = |existing: &[(City, bool)], candidate: &City| {
        let cx = (candidate.x0 + candidate.x1) * 0.5;
        let cy = (candidate.y0 + candidate.y1) * 0.5;
        existing.iter().any(|(h, _)| {
            let hx = (h.x0 + h.x1) * 0.5;
            let hy = (h.y0 + h.y1) * 0.5;
            (hx - cx).abs() < 1.0 && (hy - cy).abs() < 1.0
        })
    };
    if let Some(city) = &map.city {
        hubs.push((city.clone(), true));
    }
    for camp in &map.camps {
        if !matches_existing(&hubs, camp) {
            hubs.push((camp.clone(), false));
        }
    }
    hubs
}

fn clear_guard_spot(map: &Map, p: Point, chosen: &[Point], radius: f64) -> bool {
    let margin = 0.5;
    let size = map.size as f64;
    if p.x < margin || p.y < margin || p.x > size - margin || p.y > size - margin {
        return false;
    }
    if map.dock.as_ref().is_some_and(|d| d.contains(p)) {
        return false;
    }
    if map.portals.iter().any(|q| p.distance(Point { x: q.x, y: q.y }) < q.r + 1.5) {
        return false;
    }
    if map
        .npcs
        .iter()
        .any(|n| p.distance(Point { x: n.x, y: n.y }) < 1.2)
    {
        return false;
    }
    if chosen.iter().any(|c| c.distance(p) < 1.8) {
        return false;
    }
    let mut moved = p;
    map.collide(&mut moved, radius);
    moved.distance(p) < 0.05
}

/// Picks up to `count` obstacle-free guard posts near the perimeter of `hub`,
/// preferring spots with wide walkable clearance so guards are never pinched against cliffs or walls.
fn find_guard_posts(map: &Map, hub: &City, count: usize) -> Vec<Point> {
    let cx = (hub.x0 + hub.x1) * 0.5;
    let cy = (hub.y0 + hub.y1) * 0.5;
    let hx = ((hub.x1 - hub.x0) * 0.5).max(2.0);
    let hy = ((hub.y1 - hub.y0) * 0.5).max(2.0);
    let dx = (hx - 0.8).max(1.4);
    let dy = (hy - 0.8).max(1.4);
    let anchors = [
        Point { x: cx + dx, y: cy + dy * 0.45 },
        Point { x: cx - dx, y: cy - dy * 0.45 },
        Point { x: cx, y: cy + dy },
        Point { x: cx, y: cy - dy },
        Point { x: cx + dx * 0.6, y: cy - dy * 0.6 },
        Point { x: cx - dx * 0.6, y: cy + dy * 0.6 },
        Point { x: cx + dx, y: cy },
        Point { x: cx - dx, y: cy },
        Point { x: cx + dx * 0.45, y: cy },
        Point { x: cx - dx * 0.45, y: cy },
        Point { x: cx, y: cy },
    ];
    let mut chosen = Vec::with_capacity(count);
    for clearance in [PLAYER_RADIUS + 0.8, PLAYER_RADIUS] {
        for anchor in anchors {
            if chosen.len() >= count {
                break;
            }
            if clear_guard_spot(map, anchor, &chosen, clearance) {
                chosen.push(anchor);
                continue;
            }
            'ring: for radius in [0.8, 1.6, 2.4, 3.2] {
                for step in 0..8 {
                    let angle = (step as f64) * std::f64::consts::TAU / 8.0;
                    let cand = Point {
                        x: anchor.x + angle.cos() * radius,
                        y: anchor.y + angle.sin() * radius,
                    };
                    if clear_guard_spot(map, cand, &chosen, clearance) {
                        chosen.push(cand);
                        break 'ring;
                    }
                }
            }
        }
    }
    chosen
}

fn threatens_hub(hub: &City, slime: &Slime) -> bool {
    let d = dist_to_rect(hub, slime.point());
    d <= GUARD_TETHER
        && (d <= GUARD_AGGRO_CLOSE
            || (d <= GUARD_AGGRO_ACTIVE && !matches!(slime.state.as_str(), "idle" | "wander")))
}

impl World {
    pub(super) fn update_guards(&mut self) {
        if !self.guards_enabled {
            self.players.retain(|_, p| p.guard.is_none());
            return;
        }
        let mut occupied = vec![false; self.maps.len()];
        for p in self.players.values().filter(|p| p.guard.is_none() && p.merc.is_none() && p.ambient.is_none()) {
            if let Some(flag) = occupied.get_mut(p.character.zone) {
                *flag = true;
            }
        }
        // Despawn guards whose zone has emptied of live activity.
        self.players
            .retain(|_, p| p.guard.is_none() || occupied.get(p.character.zone).copied().unwrap_or(false));

        // Spawn guards for newly occupied eligible zones.
        for (zone, &is_occupied) in occupied.iter().enumerate() {
            if !is_occupied {
                continue;
            }
            if self
                .players
                .values()
                .any(|p| p.guard.is_some() && p.character.zone == zone)
            {
                continue;
            }
            self.spawn_zone_guards(zone);
        }

        // Drive combat and patrol/post return for every living guard.
        let sessions: Vec<u64> = self
            .players
            .iter()
            .filter(|(_, p)| p.guard.is_some() && p.character.hp > 0.)
            .map(|(&session, _)| session)
            .collect();
        for session in sessions {
            self.guard_think(session);
        }
    }

    fn spawn_zone_guards(&mut self, zone: usize) {
        let hubs = hubs_for_map(&self.maps[zone]);
        if hubs.is_empty() {
            return;
        }
        let level = self.maps[zone].levels.map_or(5, |[_, hi]| hi);
        for (hub, is_city) in hubs {
            let posts = find_guard_posts(&self.maps[zone], &hub, GUARDS_PER_HUB);
            let cx = (hub.x0 + hub.x1) * 0.5;
            let cy = (hub.y0 + hub.y1) * 0.5;
            for (slot_idx, post) in posts.into_iter().enumerate() {
                let name = if is_city {
                    "Town Guard"
                } else {
                    "Outpost Guard"
                };
                let mut character = Character::mercenary(Class::Warrior, level, name);
                // Guards carry no potion stacks (they cannot chug potions to tank zone elites).
                character.inventory.clear();
                character.look.gender = if (zone + slot_idx).is_multiple_of(2) {
                    Gender::Male
                } else {
                    Gender::Female
                };
                character.look.hair_color = 4;
                character.look.skin = ((zone + slot_idx) % 4) as u8;
                character.zone = zone;
                character.x = post.x;
                character.y = post.y;

                let mut worn = BTreeMap::new();
                for (kind, slot) in [
                    ("armor", "chest"),
                    ("weapon", "hands"),
                    ("headgear", "headgear"),
                    ("shoulders", "shoulders"),
                    ("gloves", "gloves"),
                    ("pants", "pants"),
                ] {
                    if let Some(id) = self.gear_for_npc(
                        Class::Warrior,
                        kind,
                        level,
                        &["common", "uncommon"],
                    ) {
                        character.add_item(&id, 1);
                        worn.insert(slot.to_owned(), id);
                    }
                }
                let _ = character.equip_slots(&worn);
                let _ = character.allocate_recommended();
                character.hp = character.max_hp();
                character.reset_resource();

                let home_face = {
                    let dx = post.x - cx;
                    let dy = post.y - cy;
                    if dx * dx + dy * dy > 1e-4 {
                        normalize(dx, dy)
                    } else {
                        normalize(1., 1.)
                    }
                };
                let session = GUARD_BASE + self.merc_seq;
                self.merc_seq += 1;
                let (peer, _unused) = mpsc::channel(1);
                let mut player = Player::new(character, peer);
                player.face = home_face;
                player.guard = Some(Guard {
                    hub: hub.clone(),
                    post,
                    home_face,
                });
                self.players.insert(session, player);
            }
        }
    }

    fn guard_think(&mut self, session: u64) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let Some(guard) = p.guard.clone() else {
            return;
        };
        let zone = p.character.zone;
        let me = p.character.point();
        let current = p.target.filter(|&id| {
            self.slimes.get(id).is_some_and(|s| {
                !s.dead && s.zone == zone && dist_to_rect(&guard.hub, s.point()) <= GUARD_TETHER
            })
        });
        let target = current.or_else(|| {
            self.slimes
                .iter()
                .filter(|s| !s.dead && s.zone == zone && threatens_hub(&guard.hub, s))
                .min_by(|a, b| {
                    a.point()
                        .distance(me)
                        .total_cmp(&b.point().distance(me))
                })
                .map(|s| s.id)
        });

        // Break off cleanly if chasing pulled the guard past the tether radius itself.
        let target = if target.is_some() && dist_to_rect(&guard.hub, me) > GUARD_TETHER + 1.0 {
            None
        } else {
            target
        };

        if let Some(sid) = target {
            if let Some(p) = self.players.get_mut(&session) {
                p.target = Some(sid);
                p.goal = None;
            }
            if self.tick.is_multiple_of(16) {
                self.ai_combat(session, &[], Some(sid));
            }
        } else if let Some(p) = self.players.get_mut(&session) {
            p.target = None;
            if me.distance(guard.post) > 0.25 {
                p.goal = Some(guard.post);
            } else {
                p.goal = None;
                p.face = guard.home_face;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::super::wyrd_tests::{at, calm, join, place, world};
    use super::*;

    #[test]
    fn all_open_hostile_hubs_spawn_clear_guards_and_hide_them_from_player_lists() {
        let mut w = world();
        calm(&mut w);
        w.guards_enabled = true;
        let _rx = join(&mut w, 1, Class::Warrior);

        let mut total_hubs = 0usize;
        for zone in 0..w.maps.len() {
            let hubs = hubs_for_map(&w.maps[zone]);
            let spawn = w.maps[zone].spawn;
            place(&mut w, 1, zone, spawn);
            w.step_inner();

            let guards: Vec<&Player> = w
                .players
                .values()
                .filter(|p| p.guard.is_some() && p.character.zone == zone)
                .collect();
            assert_eq!(
                guards.len(),
                hubs.len() * GUARDS_PER_HUB,
                "zone {zone} ({}) guard count",
                w.maps[zone].name
            );
            total_hubs += hubs.len();

            for g in &guards {
                let mut pos = g.character.point();
                w.maps[zone].collide(&mut pos, PLAYER_RADIUS);
                assert!(
                    pos.distance(g.character.point()) < 0.05,
                    "zone {zone} guard spawned inside obstacle at {:?}",
                    g.character.point()
                );
                assert!(
                    !w.maps[zone]
                        .portals
                        .iter()
                        .any(|q| pos.distance(Point { x: q.x, y: q.y }) < q.r + 1.4),
                    "zone {zone} guard overlapping portal"
                );
            }

            let snap = w.snapshot_for(zone);
            assert_eq!(snap["players"].as_array().unwrap().len(), 1);
            assert_eq!(snap["guards"].as_array().unwrap().len(), guards.len());
            assert_eq!(w.humans_online(), 1);
            assert_eq!(w.visible_online(), 1);
            assert_eq!(w.online_roster().len(), 1);
        }
        assert_eq!(total_hubs, 90, "expected 90 open-world hostile hubs");

        // Moving into an unguarded zone (e.g. an instance copy) clears all open-world guards.
        let instance_zone = w.instances[0].zone;
        let instance_spawn = w.maps[instance_zone].spawn;
        place(&mut w, 1, instance_zone, instance_spawn);
        w.step_inner();
        assert_eq!(
            w.players.values().filter(|p| p.guard.is_some()).count(),
            0,
            "guards must despawn when zone becomes empty"
        );
    }

    #[test]
    fn guards_engage_and_defeat_stray_enemy_then_return_without_rewarding_player() {
        let mut w = world();
        calm(&mut w);
        w.guards_enabled = true;
        let _rx = join(&mut w, 1, Class::Warrior);
        // Park hero safely inside Greenmeadow city sanctuary, out of combat range.
        let hub = hubs_for_map(&w.maps[0])[0].0.clone();
        place(
            &mut w,
            1,
            0,
            at((hub.x0 + hub.x1) * 0.5, (hub.y0 + hub.y1) * 0.5),
        );
        w.step_inner();

        let guard_sessions: Vec<u64> = w
            .players
            .iter()
            .filter(|(_, p)| p.guard.is_some() && p.guard.as_ref().unwrap().hub.x0 == hub.x0)
            .map(|(&s, _)| s)
            .collect();
        assert_eq!(guard_sessions.len(), 2);

        // Place a non-elite zone mob right outside the perimeter walking onto the edge.
        let stray = w
            .slimes
            .iter()
            .find(|s| s.zone == 0 && !s.elite && s.kind != "big" && w.spawns[s.id].ambush.is_none())
            .expect("normal greenmeadow enemy")
            .id;
        let spawn_point = at(hub.x1 + 2.0, (hub.y0 + hub.y1) * 0.5);
        w.slimes[stray] = Slime::with_level(
            stray,
            &SlimeSpawn {
                x: spawn_point.x,
                y: spawn_point.y,
                kind: w.slimes[stray].kind.clone(),
                ambush: None,
                zone: 0,
            },
            w.maps[0].levels.map_or(5, |[_, hi]| hi),
        );
        w.slimes[stray].state = "chase".into();
        w.slimes[stray].target = Some(guard_sessions[0]);

        let mut killed_at = None;
        for step in 1..=(30. / TICK) as usize {
            w.step_inner();
            if w.slimes[stray].dead && killed_at.is_none() {
                killed_at = Some(step as f64 * TICK);
            }
            if killed_at.is_some()
                && guard_sessions.iter().all(|s| {
                    let p = &w.players[s];
                    p.character.point().distance(p.guard.as_ref().unwrap().post) < 0.35
                })
            {
                break;
            }
        }
        let ttk = killed_at.expect("guards must defeat the stray enemy");
        assert!(ttk > 0.8, "guards should not one-shot foes (ttk={ttk:.2}s)");
        assert!(ttk < 20.0, "guards took too long to clear stray (ttk={ttk:.2}s)");

        for s in guard_sessions {
            let p = &w.players[&s];
            assert!(
                p.character.point().distance(p.guard.as_ref().unwrap().post) < 0.35,
                "guard did not return to post"
            );
            assert!(p.target.is_none());
        }
        let hero = &w.players[&1].character;
        assert_eq!(hero.xp, 0);
        assert_eq!(hero.gold, 0);
        assert_eq!(hero.kills, 0);
        assert!(w.drops.is_empty(), "guard kills must drop no loot");
    }

    #[test]
    fn guards_do_not_trivialize_elites_and_guard_assisted_kills_deny_rewards() {
        let mut w = world();
        calm(&mut w);
        w.guards_enabled = true;
        let _rx = join(&mut w, 1, Class::Warrior);
        // Zone 0 elite (`oldtusker`).
        let elite_id = w
            .slimes
            .iter()
            .find(|s| s.zone == 0 && s.kind == "oldtusker")
            .expect("oldtusker in Greenmeadow")
            .id;
        let hub = hubs_for_map(&w.maps[0])[0].0.clone();
        place(
            &mut w,
            1,
            0,
            at((hub.x0 + hub.x1) * 0.5, (hub.y0 + hub.y1) * 0.5),
        );
        w.step_inner();

        let edge = at(hub.x1 + 1.5, (hub.y0 + hub.y1) * 0.5);
        w.slimes[elite_id] = Slime::with_level(
            elite_id,
            &SlimeSpawn {
                x: edge.x,
                y: edge.y,
                kind: "oldtusker".into(),
                ambush: None,
                zone: 0,
            },
            Slime::default_level("oldtusker"),
        );
        w.slimes[elite_id].state = "chase".into();

        // Simulate 15s: elite should NOT be killed easily by guards (and at least hurt/defeat guards).
        for _ in 0..(15. / TICK) as usize {
            w.step_inner();
        }
        assert!(
            !w.slimes[elite_id].dead,
            "two guards must not easily solo a zone elite"
        );
        assert!(
            w.slimes[elite_id].guard_damage > 0.,
            "guard should have engaged and recorded guard_damage on the elite"
        );

        // Now player lands the final blow on the guard-assisted elite -> must receive 0 XP/gold/kills/drops.
        let hero = w.players.get_mut(&1).unwrap();
        hero.character.level = 20;
        hero.character.x = edge.x + 1.0;
        hero.character.y = edge.y;
        w.slimes[elite_id].hp = 1.;
        w.hit_slime(elite_id, 1, 50., false);
        assert!(w.slimes[elite_id].dead);
        let hero = &w.players[&1].character;
        assert_eq!(hero.xp, 0, "guard-tainted elite must grant 0 XP");
        assert_eq!(hero.gold, 0, "guard-tainted elite must grant 0 gold");
        assert_eq!(hero.kills, 0, "guard-tainted elite must grant 0 kills");
        assert!(w.drops.is_empty(), "guard-tainted elite must drop no loot");
    }

    #[test]
    fn high_zone_guards_keep_balanced_ttk_and_reengage_returning_enemy() {
        let mut w = world();
        calm(&mut w);
        w.guards_enabled = true;
        let _rx = join(&mut w, 1, Class::Warrior);

        let (zone, _) = w
            .maps
            .iter()
            .enumerate()
            .filter(|(z, m)| {
                m.copies == 0
                    && !m.raid
                    && !hubs_for_map(m).is_empty()
                    && w.slimes
                        .iter()
                        .any(|s| s.zone == *z && !s.elite && s.kind != "big" && w.spawns[s.id].ambush.is_none())
            })
            .max_by_key(|(_, m)| m.levels.map_or(1, |[_, hi]| hi))
            .expect("high-level hostile open-world zone");

        let hub = hubs_for_map(&w.maps[zone])[0].0.clone();
        place(&mut w, 1, zone, at((hub.x0 + hub.x1) * 0.5, (hub.y0 + hub.y1) * 0.5));
        w.step_inner();

        let guard_pos = w
            .players
            .values()
            .find(|p| p.character.zone == zone && p.guard.as_ref().is_some_and(|g| (g.hub.x0 - hub.x0).abs() < 0.1))
            .map(|p| p.guard.as_ref().unwrap().post)
            .expect("spawned guard in high zone");

        let stray = w
            .slimes
            .iter()
            .find(|s| s.zone == zone && !s.elite && s.kind != "big" && w.spawns[s.id].ambush.is_none())
            .expect("normal enemy in high zone")
            .id;
        let edge = [(2.0, 0.0), (-2.0, 0.0), (0.0, 2.0), (0.0, -2.0)]
            .into_iter()
            .map(|(dx, dy)| at(guard_pos.x + dx, guard_pos.y + dy))
            .find(|&p| {
                let mut moved = p;
                w.maps[zone].collide(&mut moved, PLAYER_RADIUS);
                moved.distance(p) < 0.05 && dist_to_rect(&hub, p) <= GUARD_AGGRO_CLOSE
            })
            .unwrap_or(guard_pos);
        w.slimes[stray] = Slime::with_level(
            stray,
            &SlimeSpawn {
                x: edge.x,
                y: edge.y,
                kind: w.slimes[stray].kind.clone(),
                ambush: None,
                zone,
            },
            w.maps[zone].levels.map_or(30, |[_, hi]| hi),
        );
        // Simulate an enemy retreating from an in-city player past the guard perimeter.
        w.slimes[stray].state = "return".into();

        let mut saw_reengage = false;
        let mut killed_at = None;
        for step in 1..=(30. / TICK) as usize {
            w.step_inner();
            if w.slimes[stray].guard_damage > 0. && !w.slimes[stray].dead && w.slimes[stray].state == "chase" {
                saw_reengage = true;
            }
            if w.slimes[stray].dead {
                killed_at = Some(step as f64 * TICK);
                break;
            }
        }
        assert!(saw_reengage, "returning foe hit by guard should switch back to chase");
        let ttk = killed_at.expect("high-zone guards must defeat stray enemy");
        assert!(ttk > 0.8, "high-zone guards should not one-shot foes (ttk={ttk:.2}s)");
        // 30 s: the guards' class rotations changed with AOE-SKILL-AT-20 (an area skill at 20 instead of Charge), which shifts this a few seconds.
        assert!(ttk < 30.0, "high-zone guards took too long (ttk={ttk:.2}s)");
    }
}

