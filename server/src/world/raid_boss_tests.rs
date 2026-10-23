//! Only RAID-BOSS-1..3: authoritative mechanics, roles, signs, loot and timings.
use super::*;
use crate::world::wyrd_tests::{join, world};

struct Rig {
    w: World,
    boss: usize,
    zone: usize,
    _rx: Vec<tokio::sync::mpsc::Receiver<Value>>,
}
impl Rig {
    fn new(kind: &str, count: u64) -> Self {
        let mut w = world();
        let zone = 46;
        w.enter_instance(zone);
        let boss = w
            .slimes
            .iter()
            .find(|s| s.zone == zone && s.kind == kind)
            .unwrap()
            .id;
        for s in &mut w.slimes {
            if s.id != boss {
                s.dead = true;
                s.respawn = 1e9;
            }
        }
        let home = w.slimes[boss].point();
        let mut rx = vec![];
        for session in 1..=count {
            rx.push(join(&mut w, session, Class::Warrior));
            let c = &mut w.players.get_mut(&session).unwrap().character;
            c.level = 99;
            c.zone = zone;
            c.x = home.x;
            c.y = home.y + 2.;
            c.hp = c.max_hp();
        }
        w.slimes[boss].state = "chase".into();
        w.slimes[boss].target = Some(1);
        w.slimes[boss].damage = 0.;
        Self {
            w,
            boss,
            zone,
            _rx: rx,
        }
    }
    fn run(&mut self, seconds: f64) {
        for _ in 0..(seconds / TICK).round() as usize {
            self.w.time += TICK;
            self.w.tick += 1;
            self.w.update_boss_mechanics();
        }
    }
    fn put(&mut self, s: u64, p: Point) {
        let c = &mut self.w.players.get_mut(&s).unwrap().character;
        c.x = p.x;
        c.y = p.y;
    }
    fn hp(&self, s: u64) -> f64 {
        self.w.players[&s].character.hp
    }
    fn view(&self) -> Value {
        self.w.boss_mech_view(self.zone).into_iter().next().unwrap()
    }
    fn roles(&mut self) {
        let answers: Vec<_> = self
            .w
            .players
            .keys()
            .copied()
            .collect::<Vec<_>>()
            .into_iter()
            .filter_map(|s| self.w.boss_play(s).and_then(|p| p.goal).map(|g| (s, g)))
            .collect();
        for (s, p) in answers {
            self.put(s, p);
        }
    }
}

#[test]
fn raid_boss_kettil_warns_pairs_all_ten_and_breaks_chains_in_order() {
    let mut r = Rig::new("cf_kettil", 10);
    r.run(10.2);
    let v = r.view();
    assert_eq!(v["cast"]["name"], "Taut Chain");
    let stations: Vec<_> = v["tele"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|t| t["need"].as_u64() == Some(2))
        .collect();
    assert_eq!(stations.len(), 5);
    let ids: BTreeSet<_> = stations
        .iter()
        .flat_map(|t| t["players"].as_array().unwrap())
        .map(|s| s.as_str().unwrap())
        .collect();
    assert_eq!(ids.len(), 10, "everyone has exactly one chain role");
    let before = r.hp(1);
    r.roles();
    r.run(8.5);
    assert_eq!(r.hp(1), before, "no hit during the full warning");
    r.run(2.);
    assert!(
        r.view()["tele"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|t| t["need"].as_u64())
            .count()
            < 5,
        "first chain released"
    );
    r.run(8.);
    assert!(
        r.view()["cast"].is_null(),
        "all five numbered anvils were held in order"
    );
    assert!((1..=10).all(|s| r.hp(s) > 0.));
}

#[test]
fn raid_boss_kettil_standing_leash_hurts_both_partners_and_not_other_halls() {
    let mut r = Rig::new("cf_kettil", 10);
    r._rx.push(join(&mut r.w, 11, Class::Warrior));
    let c = &mut r.w.players.get_mut(&11).unwrap().character;
    c.zone = r.zone;
    c.x = 209.;
    c.y = 272.;
    let bystander_hp = c.hp;
    r.run(10.2);
    let v = r.view();
    let station = v["tele"]
        .as_array()
        .unwrap()
        .iter()
        .find(|t| t["need"].as_u64() == Some(2))
        .unwrap();
    let group: Vec<_> = station["players"]
        .as_array()
        .unwrap()
        .iter()
        .map(|id| {
            *r.w.players
                .iter()
                .find(|(_, p)| p.character.id == id.as_str().unwrap())
                .unwrap()
                .0
        })
        .collect();
    r.roles();
    r.put(group[0], Point { x: 70., y: 260. });
    let before = r.hp(group[1]);
    r.run(9.5);
    assert!(
        r.hp(group[0]) < before && r.hp(group[1]) < before,
        "both ends take the standing leash hit"
    );
    // Losing a partner removes an impossible leash rather than repeatedly hurting the survivor.
    r.w.players.get_mut(&group[0]).unwrap().character.hp = 0.;
    let hp = r.hp(group[1]);
    r.run(1.);
    assert_eq!(r.hp(group[1]), hp);
    assert_eq!(
        r.hp(11),
        bystander_hp,
        "the next hall's fighter is never chained or hurt"
    );
}

#[test]
fn raid_boss_ysolt_caps_each_shelter_and_sweeps_unsheltered_players() {
    let mut r = Rig::new("cf_ysolt", 10);
    r.run(10.2);
    r.roles();
    let bm::Block::Gust(g) = &r.w.boss.table["cf_ysolt"].mechanics[0].block else {
        panic!()
    };
    let at = Point {
        x: g.points[0][0],
        y: g.points[0][1],
    };
    for s in 1..=4 {
        r.put(s, at);
    }
    r.run(10.1);
    assert_eq!(
        (1..=4)
            .filter(|s| r.w.players[s].character.point().distance(at) < 0.5)
            .count(),
        3,
        "only three are sheltered"
    );
    assert!(
        r.w.players[&4].character.point().distance(at) > 9.5,
        "the fourth is actually shoved"
    );
}

#[test]
fn raid_boss_ysolt_rim_kills_and_god_mode_still_blocks_the_kill() {
    for god in [false, true] {
        let mut r = Rig::new("cf_ysolt", 10);
        r.run(10.2);
        r.roles();
        r.put(1, Point { x: 224., y: 272. });
        r.w.players.get_mut(&1).unwrap().god = god;
        let protected = r.w.players[&2].character.point();
        r.run(10.1);
        assert_eq!(
            r.hp(1) > 0.,
            god,
            "position at the lava rim decides; GM god mode blocks death"
        );
        assert!(r.hp(2) > 0.);
        assert_eq!(r.w.players[&2].character.point().distance(protected), 0.);
    }
}

#[test]
fn raid_boss_hallgrim_needs_three_distinct_groups_and_rejects_dead_helpers() {
    let mut r = Rig::new("cf_hallgrim", 10);
    r.run(10.2);
    r.roles();
    let before = r.hp(1);
    r.run(8.1);
    assert!(
        (1..=10).all(|s| r.hp(s) == before),
        "three populated anvils land safely"
    );
    let mut r = Rig::new("cf_hallgrim", 10);
    r.run(10.2);
    r.roles();
    let v = r.view();
    let t = v["tele"]
        .as_array()
        .unwrap()
        .iter()
        .find(|t| t["need"].as_u64() == Some(3) && t["count"].as_u64() == Some(3))
        .unwrap();
    let group: Vec<u64> = t["players"]
        .as_array()
        .unwrap()
        .iter()
        .map(|id| {
            *r.w.players
                .iter()
                .find(|(_, p)| p.character.id == id.as_str().unwrap())
                .unwrap()
                .0
        })
        .collect();
    r.w.players.get_mut(&group[0]).unwrap().character.hp = 0.;
    let outsider = (1..=10).find(|s| !group.contains(s)).unwrap();
    r.run(8.1);
    assert!(
        group.iter().all(|s| r.hp(*s) <= 0.),
        "two living helpers do not meet three"
    );
    assert!(
        r.hp(outsider) > 0. && r.hp(outsider) < before,
        "a missed anvil hurts the whole crew"
    );
}

#[test]
fn raid_boss_hallgrim_lone_soaker_falls_and_a_five_player_idle_group_fails() {
    for count in [1, 5, 8] {
        let mut r = Rig::new("cf_hallgrim", count);
        r.run(10.2);
        r.roles();
        r.run(8.1);
        assert!(
            (1..=count).any(|s| r.hp(s) <= 0.),
            "{count} cannot fill three groups of three"
        );
    }
}

#[test]
fn raid_boss_casts_reset_on_evade_and_do_not_leak_into_other_copies() {
    for kind in ["cf_kettil", "cf_ysolt", "cf_hallgrim"] {
        let mut r = Rig::new(kind, 10);
        r.run(10.2);
        assert!(r.view()["cast"].is_object());
        let copy =
            r.w.instances
                .iter()
                .find(|i| i.template == 46 && i.zone != 46)
                .unwrap()
                .zone;
        assert!(r.w.boss_mech_view(copy).is_empty());
        assert_eq!(
            r.w.signs_view(copy).len(),
            3,
            "each raid copy has all three Warden signs"
        );
        r.w.slimes[r.boss].state = "return".into();
        r.run(0.1);
        assert!(r.w.boss_mech_view(r.zone).is_empty());
        r.w.slimes[r.boss].state = "chase".into();
        r.run(0.1);
        assert!(r.view()["cast"].is_null(), "fresh pull has fresh timer");
    }
}

#[test]
fn raid_boss_signs_loot_and_all_assigned_positions_obey_the_reach_rule() {
    let w = world();
    for kind in ["cf_kettil", "cf_ysolt", "cf_hallgrim"] {
        let def = &w.boss.table[kind];
        let map = &w.maps[46];
        let sign = &w.signs[kind];
        crate::bosssign::validate(kind, sign).unwrap();
        let spawn = w
            .spawns
            .iter()
            .find(|s| s.zone == 46 && s.kind == kind)
            .unwrap();
        assert!(
            Point {
                x: sign.x,
                y: sign.y
            }
            .distance(Point {
                x: spawn.x,
                y: spawn.y
            }) > 24.,
            "read before the Warden wakes"
        );
        assert_eq!(crate::items::raid_rewards::boss(kind).unwrap().drops, 2);
        let [x0, y0, x1, y1] = def.arena.unwrap();
        for m in &def.mechanics {
            let (points, r, cast) = match &m.block {
                bm::Block::Tether(t) => (&t.points, t.r, t.cast),
                bm::Block::Gust(g) => (&g.points, g.r, g.cast),
                bm::Block::Soak(s) => (&s.points, s.r, s.cast),
                _ => panic!(),
            };
            for y in y0 as i32..y1 as i32 {
                for x in x0 as i32..x1 as i32 {
                    let p = Point {
                        x: x as f64 + 0.5,
                        y: y as f64 + 0.5,
                    };
                    let mut free = p;
                    map.collide(&mut free, PLAYER_RADIUS);
                    if p.distance(free) > 1e-6 {
                        continue;
                    }
                    for at in points {
                        let at = Point { x: at[0], y: at[1] };
                        let distance = (p.distance(at) - r * 0.3).max(0.);
                        assert!(
                            distance <= bm::max_run_distance(cast),
                            "{kind}: {p:?} to {at:?} in {cast}s is too far: {distance}"
                        );
                        assert!(
                            map.line_clear(p, at, PLAYER_RADIUS),
                            "{kind}: court must have a clear route to {at:?}"
                        );
                    }
                }
            }
        }
    }
}

#[test]
#[ignore = "Boss-only ten-fighter calibration; use RAID_BOSSES/RAID_BOSS_SEEDS/RAID_BOSS_COUNT"]
fn raid_boss_measure_first_three() {
    use super::ttk::{Case, Foe, run_raid_hired_party};
    let w = world();
    let count = std::env::var("RAID_BOSS_COUNT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(10);
    let seeds = std::env::var("RAID_BOSS_SEEDS")
        .ok()
        .and_then(|s| s.parse::<u64>().ok())
        .unwrap_or(16);
    let first_seed = std::env::var("RAID_BOSS_FIRST_SEED")
        .ok()
        .and_then(|s| s.parse::<u64>().ok())
        .unwrap_or(1);
    let wanted = std::env::var("RAID_BOSSES").unwrap_or_default();
    let class = std::env::var("RAID_BOSS_CLASS")
        .ok()
        .and_then(|s| serde_json::from_value(json!(s)).ok())
        .unwrap_or(Class::Warrior);
    for kind in ["cf_kettil", "cf_ysolt", "cf_hallgrim"] {
        if !wanted.is_empty() && !wanted.split(',').any(|s| s == kind) {
            continue;
        }
        let id = w
            .slimes
            .iter()
            .find(|s| s.zone == 46 && s.kind == kind)
            .unwrap()
            .id;
        let case = Case {
            class,
            level: 99,
            foe: Foe::Elite,
            rarity: "raid_chainforged",
            target: Some(id),
            cap: Some(1200.),
            run_to_end: true,
            consumables: true,
            ..Case::new(class, 99)
        };
        let mut times = vec![];
        for seed in first_seed..first_seed + seeds {
            let out = run_raid_hired_party(&case, &[id], seed, count);
            eprintln!(
                "[raid-boss] {kind} n={count} seed={seed} won={} time={:.2} falls={} left={:.4} unstuck={} dps={:?}",
                out.killed, out.seconds, out.deaths, out.enemy_left, out.unstuck, out.dps
            );
            if out.killed {
                times.push(out.seconds);
            }
        }
        times.sort_by(f64::total_cmp);
        if !times.is_empty() {
            eprintln!(
                "[raid-boss-band] {kind} n={count} wins={}/{} median={:.2} fastest={:.2} slowest={:.2}",
                times.len(),
                seeds,
                times[times.len() / 2],
                times[0],
                times[times.len() - 1]
            );
        }
    }
}

#[test]
fn raid_boss_actual_kills_pay_two_orange_copies_per_warden_with_rebirth() {
    for kind in ["cf_kettil", "cf_ysolt", "cf_hallgrim"] {
        for boost in [1, 3] {
            let mut r = Rig::new(kind, 1);
            r.w.players.get_mut(&1).unwrap().character.rebirth_tiers = [0, 0, 0, 0, boost - 1];
            r.w.hit_slime(r.boss, 1, 1e12, false);
            assert!(r.w.slimes[r.boss].dead);
            let pieces: Vec<_> = r.w.drops.iter().filter_map(|d| d.gear.as_ref()).collect();
            assert_eq!(
                pieces.len(),
                2 * boost as usize,
                "{kind}: actual kill uses the guaranteed Warden table"
            );
            assert!(pieces.iter().all(|g| g.rarity == "legendary"
                && item(&g.item).unwrap().source.as_deref() == Some("chained_forge")));
            assert!(
                r.w.drops
                    .iter()
                    .filter_map(|d| d.item.as_deref().and_then(item))
                    .filter(|i| i.source.as_deref() == Some("chained_forge"))
                    .all(|i| i.kind != "weapon")
            );
        }
    }
}

#[test]
fn raid_boss_ysolts_wind_cannot_carry_an_idle_crew_in_a_safe_square_forever() {
    let mut r = Rig::new("cf_ysolt", 10);
    r.run(111.);
    assert!(
        (1..=10).any(|s| r.hp(s) <= 0.),
        "Unprotected fighters must move or shelter; the wind cannot cycle them safely forever"
    );
}

#[test]
fn raid_boss_escalations_finish_the_current_warning_before_starting_another() {
    for kind in ["cf_kettil", "cf_ysolt", "cf_hallgrim"] {
        let mut r = Rig::new(kind, 10);
        r.run(10.2);
        r.w.slimes[r.boss].hp = r.w.slimes[r.boss].max_hp * 0.3;
        r.run(2.);
        let v = r.view();
        let count = v["tele"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|t| t["need"].is_number())
            .count();
        assert_eq!(
            count,
            if kind == "cf_kettil" {
                5
            } else if kind == "cf_ysolt" {
                4
            } else {
                3
            },
            "{kind}: only one assignment is announced at a time"
        );
    }
}

#[test]
fn raid_boss_kettil_odd_crew_has_one_trio_with_all_three_leash_lines() {
    let mut r = Rig::new("cf_kettil", 9);
    r.run(10.2);
    let v = r.view();
    let tele = v["tele"].as_array().unwrap();
    assert_eq!(
        tele.iter()
            .filter(|t| t["need"].as_u64() == Some(3))
            .count(),
        1
    );
    assert_eq!(
        tele.iter().filter(|t| t["chain"] == true).count(),
        6,
        "three pairs and all three sides of the trio"
    );
    let assigned: BTreeSet<_> = tele
        .iter()
        .filter(|t| t["need"].is_number())
        .flat_map(|t| t["players"].as_array().unwrap())
        .map(|s| s.as_str().unwrap())
        .collect();
    assert_eq!(assigned.len(), 9);
}
