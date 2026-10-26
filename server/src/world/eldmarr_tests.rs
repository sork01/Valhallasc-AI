//! Eldmarr only: deterministic mechanic checks, no kill-time/win-rate sweeps.
use super::*;
use crate::world::wyrd_tests::{join, world};
struct Rig {
    w: World,
    boss: usize,
    rx: Vec<tokio::sync::mpsc::Receiver<Value>>,
}
impl Rig {
    fn new(n: u64) -> Self {
        let mut w = world();
        w.enter_instance(46);
        let boss = w
            .slimes
            .iter()
            .find(|s| s.zone == 46 && s.kind == "cf_eldmarr")
            .unwrap()
            .id;
        for s in &mut w.slimes {
            if s.id != boss {
                s.dead = true;
                s.respawn = 1e9;
            }
        }
        let at = w.slimes[boss].point();
        let mut rx = vec![];
        for id in 1..=n {
            rx.push(join(&mut w, id, Class::Warrior));
            let c = &mut w.players.get_mut(&id).unwrap().character;
            c.level = 99;
            c.zone = 46;
            c.x = at.x;
            c.y = at.y + 2.;
            c.hp = c.max_hp();
        }
        let s = &mut w.slimes[boss];
        s.state = "chase".into();
        s.target = Some(1);
        s.damage = 0.;
        Self { w, boss, rx }
    }
    fn run(&mut self, t: f64) {
        for _ in 0..(t / TICK).round() as usize {
            self.w.time += TICK;
            self.w.tick += 1;
            self.w.update_boss_mechanics();
        }
    }
    fn put(&mut self, id: u64, at: Point) {
        let c = &mut self.w.players.get_mut(&id).unwrap().character;
        c.x = at.x;
        c.y = at.y;
    }
    fn hp(&self, id: u64) -> f64 {
        self.w.players[&id].character.hp
    }
    fn view(&self) -> Value {
        self.w
            .boss_mech_view(46)
            .into_iter()
            .find(|v| v["boss"] == self.boss)
            .unwrap()
    }
    fn phase(&mut self, n: usize) {
        self.run(TICK);
        for phase in 2..=n {
            self.w.slimes[self.boss].hp = self.w.slimes[self.boss].max_hp
                * match phase {
                    2 => 0.66,
                    3 => 0.33,
                    _ => 0.08,
                };
            self.run(TICK);
            if phase < 4 {
                self.run(10.);
            }
        }
    }
    fn spots(&self, key: &str) -> Vec<Point> {
        self.view()["tele"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|t| t[key] == true)
            .map(|t| Point {
                x: t["shapes"][0]["x"].as_f64().unwrap(),
                y: t["shapes"][0]["y"].as_f64().unwrap(),
            })
            .collect()
    }
    fn roles(&mut self) {
        let ids: Vec<_> = self.w.players.keys().copied().collect();
        let goals: Vec<_> = ids
            .into_iter()
            .filter_map(|id| self.w.boss_play(id).and_then(|b| b.goal).map(|p| (id, p)))
            .collect();
        for (id, p) in goals {
            self.put(id, p);
        }
    }
}
#[test]
fn eldmarr_crack_warns_then_kills_camper_and_cools() {
    let mut r = Rig::new(2);
    r.run(3.2);
    let v = r.view();
    let crack = v["tele"]
        .as_array()
        .unwrap()
        .iter()
        .find(|t| t["label"] == "Cracking Floor")
        .unwrap();
    assert_eq!(crack["total"], 8.);
    assert!(!crack["lava"].as_bool().unwrap());
    let old = r.w.players[&1].character.point();
    r.put(
        2,
        Point {
            x: old.x + 4.,
            y: old.y,
        },
    );
    r.run(7.5);
    assert!(r.hp(1) > 0., "the full eight-second warning is harmless");
    r.run(0.6);
    assert_eq!(r.hp(1), 0.);
    assert!(r.hp(2) > 0., "moving clear avoids the original cell");
    assert!(r.w.players[&1].fallen);
    let key = cell(old, 2.);
    r.w.players.get_mut(&2).unwrap().character.hp = 0.;
    // Tick the same live engine while the original cell cools; do not start a fight/grind.
    let mut f = r.w.boss.fights.remove(&r.boss).unwrap();
    let def = r.w.boss.table["cf_eldmarr"].clone();
    f.eld.as_mut().unwrap().cracks.get_mut(&key).unwrap().age = 47.99;
    r.w.tick_eldmarr(&mut f, &def, 1.);
    assert!(!f.eld.as_ref().unwrap().cracks.contains_key(&key));
}
#[test]
fn eldmarr_floor_tracks_cells_and_actual_brain_moves_before_cracking() {
    let mut r = Rig::new(10);
    r.run(2.1);
    let at = r.w.players[&1].character.point();
    let b = r.w.boss_play(1).unwrap();
    assert!(b.hold_fire);
    let goal = b.goal.unwrap();
    assert_ne!(cell(at, 2.), cell(goal, 2.));
    assert!(r.w.maps[46].line_clear(at, goal, PLAYER_RADIUS));
    r.roles();
    r.run(1.2);
    assert!(
        r.view()["tele"]
            .as_array()
            .unwrap()
            .iter()
            .all(|t| t["lava"].is_null()),
        "movement resets dwell"
    );
    r.run(2.);
    assert!(!r.view()["tele"].as_array().unwrap().is_empty());
}
#[test]
fn eldmarr_health_gates_two_breaths_and_unbound_combines_three_blocks() {
    let mut r = Rig::new(1);
    let Incoming::Damage(damage) = r.w.boss_incoming(r.boss, 1e15) else {
        panic!()
    };
    assert!(
        (damage - r.w.slimes[r.boss].max_hp * 0.34).abs() < 0.01,
        "opening blow cannot skip phases"
    );
    r.run(TICK);
    for (health, phase) in [(0.66, 2), (0.33, 3), (0.08, 4)] {
        r.w.slimes[r.boss].hp = r.w.slimes[r.boss].max_hp * health;
        r.run(TICK);
        assert_eq!(r.view()["throne"]["phase"], phase);
        assert_eq!(r.view()["throne"]["broken"], (phase - 1) * 3);
        if phase < 4 {
            assert_eq!(r.view()["cast"]["name"], "The Forge Takes a Breath");
            assert!(matches!(
                r.w.boss_incoming(r.boss, 1e15),
                Incoming::Damage(0.)
            ));
            r.run(9.8);
            assert!(r.hp(1) > 0.);
            assert!(r.view()["throne"]["breathing"].as_f64().unwrap() > 0.);
            r.run(0.3);
        }
    }
    r.w.god_mode = true;
    r.run(11.);
    let v = r.view();
    assert_eq!(v["cast"]["name"], "A Seat for Everyone");
    let t = v["tele"].as_array().unwrap();
    assert_eq!(t.iter().filter(|t| t["seat"] == true).count(), 10);
    assert_eq!(t.iter().filter(|t| t["coldWell"] == true).count(), 4);
    assert!(
        t.iter().any(|t| !t["lava"].is_null()),
        "cracks, wells and seats coexist"
    );
    assert_eq!(
        v["cast"]["total"], 9.,
        "faster tempo never shortens a lethal warning"
    );
}
#[test]
fn eldmarr_heat_capacity_counts_real_occupants_and_cooling_cancels_fuse() {
    let mut r = Rig::new(5);
    r.phase(2);
    let well = r.spots("coldWell")[0];
    for id in 1..=4 {
        r.put(id, well);
    }
    r.run(2.);
    let e = r.w.boss.fights[&r.boss].eld.as_ref().unwrap();
    assert!((1..=3).all(|id| e.meters[&id].heat < 0.001));
    assert!(
        e.meters[&4].heat > 0.06,
        "the fourth body cannot cool at a full well"
    );
    assert!(
        e.meters[&5].heat > 0.06,
        "heat comes from time, without an attack"
    );
    {
        let e =
            r.w.boss
                .fights
                .get_mut(&r.boss)
                .unwrap()
                .eld
                .as_mut()
                .unwrap();
        let m = e.meters.get_mut(&5).unwrap();
        m.heat = 1.;
        m.fuse = Some(5.);
    }
    r.put(5, r.spots("coldWell")[1]);
    r.run(1.);
    let e = r.w.boss.fights[&r.boss].eld.as_ref().unwrap();
    assert!(e.meters[&5].heat < 0.9 && e.meters[&5].fuse.is_none());
    assert!(r.hp(5) > 0.);
}
#[test]
fn eldmarr_heat_warns_five_seconds_blasts_neighbours_and_moves_wells() {
    let mut r = Rig::new(3);
    r.phase(2);
    r.w.boss
        .fights
        .get_mut(&r.boss)
        .unwrap()
        .eld
        .as_mut()
        .unwrap()
        .meters
        .entry(1)
        .or_default()
        .heat = 1.;
    r.run(TICK);
    let view = r.view();
    let t = view["tele"]
        .as_array()
        .unwrap()
        .iter()
        .find(|t| t["heatFuse"].is_number())
        .unwrap();
    assert_eq!(t["total"], 5.);
    assert_eq!(t["shapes"][0]["r"], 5.);
    let at = r.w.players[&1].character.point();
    r.put(
        3,
        Point {
            x: at.x + 6.,
            y: at.y,
        },
    );
    r.run(4.7);
    assert!(r.hp(1) > 0. && r.hp(2) > 0.);
    r.run(0.4);
    assert_eq!(r.hp(1), 0.);
    assert_eq!(r.hp(2), 0.);
    assert!(r.hp(3) > 0.);
    let old = r.spots("coldWell");
    r.w.god_mode = true;
    r.run(20.);
    assert!(
        r.view()["tele"]
            .as_array()
            .unwrap()
            .iter()
            .any(|t| t["label"] == "Next Cold Well")
    );
    r.run(5.);
    assert_ne!(old, r.spots("coldWell"));
}
#[test]
fn eldmarr_seats_assign_ten_distinct_roles_and_only_one_body_per_plate() {
    let mut r = Rig::new(10);
    r.phase(3);
    r.run(12.2);
    let v = r.view();
    let plates: Vec<_> = v["tele"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|t| t["seat"] == true)
        .collect();
    assert_eq!(plates.len(), 10);
    let roles: BTreeSet<_> = plates
        .iter()
        .flat_map(|t| t["players"].as_array().unwrap())
        .map(|s| s.as_str().unwrap())
        .collect();
    assert_eq!(roles.len(), 10);
    assert!(plates.iter().all(|t| t["capacity"] == 1));
    r.roles();
    let at = r.w.players[&1].character.point();
    r.put(2, at);
    r.run(8.9);
    assert_eq!(r.hp(2), 0.);
    assert!(r.hp(1) > 0.);
    assert!((3..=10).all(|id| r.hp(id) > 0.));
    assert_eq!(
        r.w.players.values().filter(|p| p.character.hp > 0.).count(),
        9,
        "a stack cannot share a safe island"
    );
}
#[test]
fn eldmarr_seats_fall_frees_spare_and_leaving_court_does_not_cancel_danger() {
    let mut r = Rig::new(10);
    r.phase(3);
    r.run(12.1);
    r.roles();
    let spare = r.w.players[&1].character.point();
    r.w.players.get_mut(&1).unwrap().character.hp = 0.;
    r.put(2, spare);
    let a = r.w.boss.fights[&r.boss].arena;
    r.put(
        3,
        Point {
            x: a.x1 + 1.,
            y: a.y1,
        },
    );
    r.run(9.);
    assert!(
        r.hp(2) > 0.,
        "a surviving friend may use a fallen friend's spare seat"
    );
    assert_eq!(r.hp(3), 0.);
    assert!(r.w.players[&3].fallen);
}
#[test]
fn eldmarr_combined_phase_never_puts_lava_in_a_well_or_live_seat() {
    let mut r = Rig::new(10);
    r.phase(4);
    r.w.god_mode = true;
    r.run(10.);
    let v = r.view();
    let t = v["tele"].as_array().unwrap();
    let safe: Vec<_> = t
        .iter()
        .filter(|t| t["seat"] == true || t["coldWell"] == true)
        .map(|t| Point {
            x: t["shapes"][0]["x"].as_f64().unwrap(),
            y: t["shapes"][0]["y"].as_f64().unwrap(),
        })
        .collect();
    let f = r.w.boss.fights.get_mut(&r.boss).unwrap();
    let e = f.eld.as_mut().unwrap();
    for p in &safe {
        e.cracks.insert(cell(*p, 2.), CrackCell { age: 10. });
    }
    r.run(TICK);
    let e = r.w.boss.fights[&r.boss].eld.as_ref().unwrap();
    assert!(safe.iter().all(|p| !e.cracks.contains_key(&cell(*p, 2.))));
}
#[test]
fn eldmarr_court_paths_warning_budget_and_sign_match_the_shipped_fight() {
    let r = Rig::new(10);
    let def = &r.w.boss.table["cf_eldmarr"];
    bm::validate("cf_eldmarr", def).unwrap();
    assert_eq!(def.mechanics.len(), 3);
    let (_, c, _, h, _, s) = blocks(def).unwrap();
    assert_eq!(c.cast, 8.);
    assert_eq!(h.capacity, 3);
    assert_eq!(s.cast, 9.);
    let a = bm::arena_for_boss(&r.w.maps[46], r.w.slimes[r.boss].point(), def);
    for x in a.x0 as i32..a.x1 as i32 {
        for y in a.y0 as i32..a.y1 as i32 {
            let at = Point {
                x: x as f64 + 0.5,
                y: y as f64 + 0.5,
            };
            let mut free = at;
            r.w.maps[46].collide(&mut free, PLAYER_RADIUS);
            if at.distance(free) > 1e-6 {
                continue;
            }
            for p in &s.points {
                assert!(at.distance(point(*p)) <= bm::max_run_distance(s.cast));
                assert!(
                    r.w.maps[46].line_clear(at, point(*p), PLAYER_RADIUS),
                    "{at:?} to {p:?}"
                );
            }
        }
    }
    let sign = &r.w.signs["cf_eldmarr"];
    crate::bosssign::validate("cf_eldmarr", sign).unwrap();
    assert!(
        sign.what.contains("8 seconds")
            && sign.todo.contains("5 seconds")
            && sign.tip.contains("9 seconds")
    );
    assert!(!r.w.maps[46].sealed_template);
    assert_eq!(r.w.maps[46].final_boss, "cf_eldmarr");
    let rule = crate::items::raid_rewards::boss("cf_eldmarr").unwrap();
    assert!(rule.drops > 0);
}
#[test]
fn eldmarr_state_is_copy_local_resets_and_fallen_stay_down_past_fifteen_minutes() {
    let mut r = Rig::new(2);
    r.phase(2);
    r.run(1.);
    let copy =
        r.w.instances
            .iter()
            .find(|i| i.template == 46 && i.zone != 46)
            .unwrap()
            .zone;
    r.w.players.get_mut(&2).unwrap().character.zone = copy;
    r.run(TICK);
    assert!(
        !r.w.boss.fights[&r.boss]
            .eld
            .as_ref()
            .unwrap()
            .meters
            .contains_key(&2)
    );
    {
        let p = r.w.players.get_mut(&1).unwrap();
        p.character.hp = 0.;
        p.fallen = true;
        p.dead_time = 1000.;
    }
    r.w.update_player(1);
    assert_eq!(r.hp(1), 0.);
    assert!(r.w.players[&1].fallen);
    r.w.reset_boss_zone(46);
    assert!(!r.w.boss.fights.contains_key(&r.boss));
    assert!(r.w.boss_mech_view(46).is_empty());
}
#[test]
fn eldmarr_clear_announces_once_opens_exit_and_leaves_reward_chest() {
    let mut r = Rig::new(1);
    let at = r.w.slimes[r.boss].point();
    while r.rx[0].try_recv().is_ok() {}
    r.w.clear_instance(46, at);
    r.w.clear_instance(46, at);
    let mut announcements = 0;
    while let Ok(v) = r.rx[0].try_recv() {
        if v["type"] == "announce" && v["kind"] == "boss" {
            announcements += 1;
        }
    }
    assert_eq!(announcements, 1);
    assert!(r.w.instances.iter().find(|i| i.zone == 46).unwrap().cleared);
    assert_eq!(
        r.w.chests
            .list
            .iter()
            .filter(|c| c.zone == 46 && c.x == 111. && c.y == 29.)
            .count(),
        1
    );
    let exit = r.w.maps[46].portals.iter().find(|p| p.after_clear).unwrap();
    assert!(exit.after_clear);
    assert!(
        !r.w.instances
            .iter()
            .find(|i| i.template == 46 && i.zone != 46)
            .unwrap()
            .cleared
    );
}

#[test]
fn eldmarr_actual_final_hit_awards_two_oranges_two_signatures_and_clears() {
    let mut r = Rig::new(1);
    r.phase(4);
    r.w.hit_slime(r.boss, 1, 1e15, false);
    assert!(r.w.slimes[r.boss].dead);
    assert!(r.w.instances.iter().find(|i| i.zone == 46).unwrap().cleared);
    let pieces: Vec<_> =
        r.w.drops
            .iter()
            .filter_map(|d| d.gear.as_ref())
            .filter(|g| {
                crate::items::item(&g.item)
                    .is_some_and(|i| i.source.as_deref() == Some("chained_forge"))
            })
            .collect();
    assert_eq!(pieces.len(), 4);
    assert!(pieces.iter().all(|g| g.rarity == "legendary"));
    assert_eq!(
        pieces
            .iter()
            .filter(|g| crate::items::item(&g.item).unwrap().kind == "weapon")
            .count(),
        2
    );
}
#[test]
fn eldmarr_schema_refuses_missing_base_mechanic_and_shortened_warning() {
    let r = Rig::new(1);
    let def = r.w.boss.table["cf_eldmarr"].as_ref();
    let mut missing = def.clone();
    missing.mechanics.remove(1);
    assert!(bm::validate("cf_eldmarr", &missing).is_err());
    for n in 0..3 {
        let mut bad = def.clone();
        match &mut bad.mechanics[n].block {
            Block::Crack(c) => c.cast = 4.9,
            Block::Heat(h) => h.cast = 4.9,
            Block::Seats(s) => s.cast = 4.9,
            _ => panic!(),
        }
        assert!(bm::validate("cf_eldmarr", &bad).is_err());
    }
}
#[test]
fn eldmarr_hired_fighters_receive_live_seat_roles_and_cooling_goals() {
    let mut r = Rig::new(1);
    let at = r.w.slimes[r.boss].point();
    crate::world::ttk::hire_mercenaries(
        &mut r.w,
        &[
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ],
        46,
        Point {
            x: at.x,
            y: at.y + 2.,
        },
    );
    assert_eq!(r.w.players.values().filter(|p| p.merc.is_some()).count(), 9);
    r.phase(2);
    r.run(16.);
    let hired: Vec<_> =
        r.w.players
            .iter()
            .filter(|(_, p)| p.merc.is_some())
            .map(|(id, _)| *id)
            .collect();
    let mut wells = BTreeSet::new();
    for id in &hired {
        let play = r.w.boss_play(*id).unwrap();
        let p = play.goal.unwrap();
        wells.insert(((p.x * 1000.).round() as i64, (p.y * 1000.).round() as i64));
        assert!(play.hold_fire);
    }
    assert!(
        wells.len() >= 3,
        "nine actual hires split between capacity-limited wells"
    );
    r.w.slimes[r.boss].hp = r.w.slimes[r.boss].max_hp * 0.33;
    r.run(10.2);
    r.run(12.2);
    let goals: BTreeSet<_> = hired
        .iter()
        .map(|id| r.w.boss_play(*id).unwrap().goal.unwrap())
        .map(|p| ((p.x * 1000.).round() as i64, (p.y * 1000.).round() as i64))
        .collect();
    assert_eq!(goals.len(), 9, "real hired fighters get distinct seats");
}

#[test]
fn eldmarr_brain_routes_round_lava_and_table_warning_pauses_heat_fuses() {
    let mut r = Rig::new(1);
    r.phase(4);
    let f = r.w.boss.fights.get_mut(&r.boss).unwrap();
    let e = f.eld.as_mut().unwrap();
    e.meters.entry(1).or_default().heat = 1.;
    e.meters.get_mut(&1).unwrap().fuse = Some(0.2);
    e.seats_in = 0.;
    r.run(TICK);
    let e = r.w.boss.fights[&r.boss].eld.as_ref().unwrap();
    let fuse = e.meters[&1].fuse;
    r.run(1.);
    assert_eq!(
        r.w.boss.fights[&r.boss].eld.as_ref().unwrap().meters[&1].fuse,
        fuse
    );
    assert!(
        r.hp(1) > 0.,
        "the table never demands a seat and a cooling well at once"
    );
    let centre = r.w.slimes[r.boss].point();
    let me = Point {
        x: centre.x - 4.,
        y: centre.y,
    };
    let target = Point {
        x: centre.x + 4.,
        y: centre.y,
    };
    r.put(1, me);
    let f = r.w.boss.fights.get_mut(&r.boss).unwrap();
    let e = f.eld.as_mut().unwrap();
    let blocker = cell(centre, 2.);
    e.cracks.insert(blocker, CrackCell { age: 10. });
    let def = r.w.boss.table["cf_eldmarr"].clone();
    let (_, c, _, _, _, _) = blocks(&def).unwrap();
    let f = &r.w.boss.fights[&r.boss];
    let step =
        r.w.eldmarr_route(f, f.eld.as_ref().unwrap(), c, me, target)
            .unwrap();
    assert!(
        step.distance(target) > 0.1,
        "a live patch prevents the direct shortcut"
    );
    assert!(!touches(cell_rect(blocker, 2.), step, BODY));
}

#[test]
fn eldmarr_hired_movement_obeys_real_ai_cadence_through_each_phase() {
    let mut r = Rig::new(1);
    r.w.rng = 77;
    let boss = r.w.slimes[r.boss].clone();
    let spawn = r.w.spawns[r.boss].clone();
    r.w.slimes = vec![boss];
    r.w.slimes[0].id = 0;
    // Isolate movement from damage output: this check must not end because
    // the scripted final health band is killed before its mechanics run.
    r.w.slimes[0].max_hp = 1e15;
    r.w.slimes[0].hp = 1e15;
    r.w.spawns = vec![spawn];
    r.boss = 0;
    let at = r.w.slimes[0].point();
    crate::world::ttk::hire_mercenaries(
        &mut r.w,
        &[
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ],
        46,
        Point {
            x: at.x,
            y: at.y + 2.,
        },
    );
    let ids: Vec<_> = r.w.players.keys().copied().collect();
    // No enemy attack pressure or kill-time assertion: this is a movement/roles
    // integration check, with actual merc_think, player movement and mechanics.
    for (phase, seconds) in [(1, 18.), (2, 42.), (3, 34.), (4, 32.)] {
        if phase > 1 {
            r.w.slimes[0].hp = r.w.slimes[0].max_hp
                * match phase {
                    2 => 0.66,
                    3 => 0.33,
                    _ => 0.08,
                };
        }
        for _ in 0..(seconds / TICK).round() as usize {
            // A real connection consumes events continuously. A full private
            // receiver is correctly disconnected by World::step.
            while r.rx[0].try_recv().is_ok() {}
            r.w.auto_play(1, &ids, Some(0));
            r.w.slimes[0].damage = 0.;
            r.w.slimes[0].fight = 0.;
            r.w.step();
            if r.w.players.values().any(|p| p.character.hp <= 0.) {
                let events: Vec<_> = std::iter::from_fn(|| r.rx[0].try_recv().ok())
                    .filter(|v| v["kind"] == "death")
                    .collect();
                eprintln!(
                    "phase {phase} time={} boss={:?} deaths={events:?} snapshot={}",
                    r.w.time,
                    r.w.slimes[0].point(),
                    r.view()
                );
                for (id, p) in &r.w.players {
                    eprintln!(
                        "actor {id} at={:?} goal={:?} target={:?}",
                        p.character.point(),
                        p.goal,
                        p.target
                    );
                }
            }
            assert!(
                r.w.players.values().all(|p| p.character.hp > 0.),
                "movement failed in phase {phase}: {:?}",
                r.w.players
                    .iter()
                    .filter(|(_, p)| p.character.hp <= 0.)
                    .map(|(id, p)| (*id, p.character.point()))
                    .collect::<Vec<_>>()
            );
        }
        assert_eq!(r.w.players.len(), 10, "the real hired crew stays connected");
        assert!(r.w.players.values().all(|p| p.character.zone == 46));
        assert!(
            r.w.boss.fights.contains_key(&r.boss),
            "phase {phase} lost fight: state={} hp={} dead={} at={:?}",
            r.w.slimes[0].state,
            r.w.slimes[0].hp,
            r.w.slimes[0].dead,
            r.w.slimes[0].point()
        );
        assert_eq!(r.view()["throne"]["phase"], phase);
    }
}

#[test]
fn eldmarr_successful_seat_cools_before_a_short_fuse_can_resume() {
    let mut r = Rig::new(1);
    r.phase(4);
    let e =
        r.w.boss
            .fights
            .get_mut(&r.boss)
            .unwrap()
            .eld
            .as_mut()
            .unwrap();
    e.meters.entry(1).or_default().heat = 1.;
    e.meters.get_mut(&1).unwrap().fuse = Some(0.1);
    e.seats_in = 0.;
    r.run(TICK);
    r.roles();
    r.run(9.1);
    assert!(r.hp(1) > 0.);
    let e = r.w.boss.fights[&r.boss].eld.as_ref().unwrap();
    assert!(e.meters[&1].heat < 0.01 && e.meters[&1].fuse.is_none());
}

#[test]
fn eldmarr_throne_anchor_preserves_enemy_spacing() {
    let mut r = Rig::new(2);
    let home = r.w.slimes[r.boss].point();
    r.put(1, home);
    r.put(
        2,
        Point {
            x: home.x + 0.1,
            y: home.y + 0.1,
        },
    );
    r.run(TICK);
    let boss = &r.w.slimes[r.boss];
    assert!(boss.point().distance(home) < 4.);
    let bodies = r.w.actor_bodies(46, None, Some(r.boss));
    assert!(!actor_blocked(boss.point(), boss.r, &bodies));
}

#[test]
fn eldmarr_floor_escape_goal_is_kept_until_the_fighter_leaves_the_cell() {
    let mut r = Rig::new(1);
    r.run(2.1);
    let from = r.w.players[&1].character.point();
    let goal = r.w.boss_play(1).unwrap().goal.unwrap();
    let d = from.direction(goal);
    r.put(
        1,
        Point {
            x: from.x + d.x * 0.1,
            y: from.y + d.y * 0.1,
        },
    );
    r.run(0.1);
    let next = r.w.boss_play(1).unwrap().goal.unwrap();
    assert!(
        goal.distance(next) < 1e-8,
        "escape must not oscillate between equally near tiles"
    );
}

/// The hirer and nine mercenaries fight Eldmarr through `stages` of (boss health share, seconds), counting how many
/// fall to a mechanic (owner reports 2026-10-26: hires dying to the cracking floor and, in the finale, to everything).
/// Without `human` every fighter plays the full boss brain. With `human` the hirer is a person who stands at the boss
/// and swings (never dies, never cools); with `walk` they also keep changing cell. Either way only the nine
/// mercenaries play by the real `merc_think` cadence around them.
fn crew_floor_deaths(human: bool, walk: bool, stages: &[(f64, f64)], seed: u64) -> usize {
    let mut r = Rig::new(1);
    r.w.rng = seed;
    let boss = r.w.slimes[r.boss].clone();
    let spawn = r.w.spawns[r.boss].clone();
    r.w.slimes = vec![boss];
    r.w.slimes[0].id = 0;
    r.w.slimes[0].max_hp = 1e15;
    r.w.slimes[0].hp = 1e15;
    r.w.spawns = vec![spawn];
    r.boss = 0;
    let at = r.w.slimes[0].point();
    crate::world::ttk::hire_mercenaries(
        &mut r.w,
        &[
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ],
        46,
        Point {
            x: at.x,
            y: at.y + 2.,
        },
    );
    let ids: Vec<_> = r.w.players.keys().copied().collect();
    if human {
        let p = r.w.players.get_mut(&1).unwrap();
        p.god = true;
        p.target = Some(0);
    }
    let mut dead = BTreeSet::new();
    let mut stage_end = 0;
    let mut stage = 0;
    for n in 0.. {
        if n >= stage_end {
            let Some((share, seconds)) = stages.get(stage) else {
                break;
            };
            r.w.slimes[0].hp = r.w.slimes[0].max_hp * share;
            stage_end = n + (seconds / TICK).round() as usize;
            stage += 1;
        }
        while r.rx[0].try_recv().is_ok() {}
        if !human {
            r.w.auto_play(1, &ids, Some(0));
        }
        r.w.slimes[0].damage = 0.;
        r.w.slimes[0].fight = 0.;
        if walk && n % 50 == 0 {
            // A person who keeps moving: a new spot beside the boss every 2.5 s.
            let angle = (n / 50) as f64 * 2.4;
            let to = Point {
                x: at.x + 2.6 * angle.cos(),
                y: at.y + 2.6 * angle.sin(),
            };
            r.w.players.get_mut(&1).unwrap().target = None;
            r.w.players.get_mut(&1).unwrap().goal = Some(to);
        }
        r.w.step();
        for (id, p) in &r.w.players {
            if p.character.hp <= 0. && dead.insert(*id) {
                let lava = r.w.boss.fights[&0].eld.as_ref().is_some_and(|e| {
                    e.cracks.iter().any(|(k, v)| {
                        v.age >= 8. && touches(cell_rect(*k, 2.), p.character.point(), BODY)
                    })
                });
                eprintln!(
                    "t={:.1} floor_lava={lava} fighter {id} died at {:?}, boss at {:?}, cracks={}",
                    n as f64 * TICK,
                    p.character.point(),
                    r.w.slimes[0].point(),
                    r.w.boss.fights[&0]
                        .eld
                        .as_ref()
                        .map_or(0, |e| e.cracks.len())
                );
            }
        }
    }
    dead.len()
}
const PHASES: [(f64, f64); 4] = [(1., 150.), (0.65, 60.), (0.32, 60.), (0.05, 200.)];
#[test]
fn eldmarr_hired_crew_survives_every_phase_for_minutes() {
    for seed in [77, 5] {
        assert_eq!(
            crew_floor_deaths(false, false, &PHASES, seed),
            0,
            "seed {seed}"
        );
    }
}
#[test]
fn eldmarr_mercenaries_survive_the_long_first_phase_beside_a_standing_or_walking_human() {
    assert_eq!(crew_floor_deaths(true, false, &[(1., 300.)], 77), 0);
    assert_eq!(crew_floor_deaths(true, true, &[(1., 200.)], 77), 0);
}
#[test]
fn eldmarr_mercenaries_survive_the_unbound_phase_beside_a_standing_human() {
    // The human never cools, so their fuse blasts again and again: the hires must keep out of it and off the floor.
    assert_eq!(crew_floor_deaths(true, false, &[(0.05, 150.)], 77), 0);
}
