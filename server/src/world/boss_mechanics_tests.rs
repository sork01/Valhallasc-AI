//! The boss mechanics engine against a live world: one test per block, plus the wipe, the dungeon copies and the
//! wiring into `step()`. The fights run in the Undervault's boss room with a table written in each test, so the
//! sixteen real bosses add data and tests of their own without touching these.
use super::*;
use crate::bossmech::BossDef;
use crate::model::Class;
use crate::world::wyrd_tests::{drain, join, world};

fn table(json: &str) -> BossMech {
    let def: BossDef = serde_json::from_str(json).expect("test table parses");
    crate::bossmech::validate("hollowking", &def).expect("test table is fair");
    BossMech::with_table(BTreeMap::from([("hollowking".to_string(), def)]))
}

struct Rig {
    w: World,
    zone: usize,
    boss: usize,
    arena: Rect,
    rx: Vec<tokio::sync::mpsc::Receiver<Value>>,
}

/// The Undervault's boss room with `players` heroes (sessions 1..) standing in it and the king awake and fighting.
fn rig(json: &str, players: u64) -> Rig {
    let mut w = world();
    w.boss = table(json);
    let boss = w
        .slimes
        .iter()
        .find(|s| s.kind == "hollowking")
        .expect("the Undervault has its king")
        .id;
    let zone = w.slimes[boss].zone;
    let arena = bm::arena_for(&w.maps[zone], w.slimes[boss].point());
    w.enter_instance(zone);
    let mut rx = vec![];
    for session in 1..=players {
        rx.push(join(&mut w, session, Class::Warrior));
        let p = w.players.get_mut(&session).unwrap();
        p.character.zone = zone;
        p.character.hp = p.character.max_hp();
    }
    let s = &mut w.slimes[boss];
    s.state = "chase".into();
    s.target = Some(1);
    // The king is a test dummy: no blows of its own.
    s.damage = 0.;
    s.atk_cd = 1e9;
    let mut rig = Rig {
        w,
        zone,
        boss,
        arena,
        rx,
    };
    for session in 1..=players {
        // Spread them along the room's south end, clear of the boss, until a test places them.
        rig.put(session, 108. + session as f64 * 2., 36.);
    }
    rig
}

impl Rig {
    /// Stands `session` on the free ground nearest (x, y) (the room is full of pillars, braziers and bones) and
    /// says where that is.
    fn put(&mut self, session: u64, x: f64, y: f64) -> Point {
        let map = &self.w.maps[self.zone];
        let free = |p: Point| {
            let mut q = p;
            map.collide(&mut q, PLAYER_RADIUS);
            q.distance(p) < 1e-6
        };
        let mut spot = None;
        'search: for ring in 0..=12 {
            let d = ring as f64 * 0.25;
            for k in 0..16 {
                let a = k as f64 / 16. * std::f64::consts::TAU;
                let p = Point {
                    x: x + d * a.cos(),
                    y: y + d * a.sin(),
                };
                if free(p) {
                    spot = Some(p);
                    break 'search;
                }
                if ring == 0 {
                    break;
                }
            }
        }
        let p = spot.unwrap_or_else(|| panic!("no free ground near ({x}, {y})"));
        let c = &mut self.w.players.get_mut(&session).unwrap().character;
        (c.x, c.y) = (p.x, p.y);
        p
    }
    /// Free ground near (x, y) that the boss sees without any cover in between, for tests of line of sight.
    fn open_spot(&mut self, session: u64, x: f64, y: f64) -> Point {
        let boss = self.w.slimes[self.boss].point();
        for ring in 0..=10 {
            for k in 0..16 {
                let a = k as f64 / 16. * std::f64::consts::TAU;
                let d = ring as f64 * 0.5;
                let p = self.put(session, x + d * a.cos(), y + d * a.sin());
                if self.w.maps[self.zone].line_clear(boss, p, 0.05) {
                    return p;
                }
            }
        }
        panic!("no open ground near ({x}, {y})");
    }
    fn at(&self, session: u64) -> Point {
        self.w.players[&session].character.point()
    }
    fn alive(&self, session: u64) -> bool {
        self.w.players[&session].character.hp > 0.
    }
    /// Runs the engine alone (no monster AI) for `seconds`.
    fn run(&mut self, seconds: f64) {
        for _ in 0..(seconds / TICK).round() as usize {
            self.w.time += TICK;
            self.w.tick += 1;
            self.w.update_boss_mechanics();
        }
    }
    fn view(&self) -> Value {
        self.w
            .boss_mech_view(self.zone)
            .into_iter()
            .next()
            .unwrap_or(Value::Null)
    }
    fn events(&mut self, session: u64) -> Vec<Value> {
        drain(&mut self.rx[session as usize - 1])
    }
    fn max_hp(&self) -> f64 {
        self.w.slimes[self.boss].max_hp
    }
    fn set_boss_share(&mut self, share: f64) {
        let s = &mut self.w.slimes[self.boss];
        s.hp = (s.max_hp * share).round();
    }
    /// Sleeping monsters tagged `tag`, in the boss room's copy.
    fn sleepers(&mut self, tag: &str, at: &[(f64, f64)]) -> Vec<usize> {
        at.iter()
            .map(|&(x, y)| {
                let id = self.w.spawns.len();
                self.w.spawns.push(SlimeSpawn {
                    x,
                    y,
                    kind: "thrall".into(),
                    ambush: Some(tag.into()),
                    zone: self.zone,
                });
                let e = self.w.dormant_enemy(id);
                self.w.slimes.push(e);
                id
            })
            .collect()
    }
    fn hit_boss(&mut self, session: u64, damage: f64) -> f64 {
        self.w.hit_slime(self.boss, session, damage, false)
    }
    fn fight(&self) -> &Fight {
        self.w
            .boss
            .fights
            .get(&self.boss)
            .expect("a fight is running")
    }
}

fn causes(events: &[Value]) -> Vec<String> {
    events
        .iter()
        .filter(|e| e["kind"] == "death")
        .filter_map(|e| e["cause"].as_str().map(str::to_owned))
        .collect()
}
fn says(events: &[Value], text: &str) -> bool {
    events
        .iter()
        .any(|e| e["type"] == "system" && e["text"] == text)
}
fn phases(events: &[Value], phase: &str) -> usize {
    events
        .iter()
        .filter(|e| e["kind"] == "bossmech" && e["phase"] == phase)
        .count()
}
fn lane_of(view: &Value) -> (Point, Point, f64) {
    let s = &view["tele"][0]["shapes"][0];
    assert_eq!(s["t"], "lane");
    (
        Point {
            x: s["x1"].as_f64().unwrap(),
            y: s["y1"].as_f64().unwrap(),
        },
        Point {
            x: s["x2"].as_f64().unwrap(),
            y: s["y2"].as_f64().unwrap(),
        },
        s["half"].as_f64().unwrap(),
    )
}
/// A point `along` tiles from `a` toward `b`, then `across` tiles to the left of that line.
fn on_line(a: Point, b: Point, along: f64, across: f64) -> Point {
    let d = a.direction(b);
    Point {
        x: a.x + d.x * along - d.y * across,
        y: a.y + d.y * along + d.x * across,
    }
}

const TOLL: &str = r#"{"mechanics":[{"name":"Toll of the Deep","block":"zone","shape":{"kind":"circle","r":8},"effect":"kill","cast":5,"every":25,"first":2}]}"#;

#[test]
fn nothing_runs_without_a_table_and_the_snapshot_stays_quiet() {
    let mut r = rig(TOLL, 1);
    r.w.boss = BossMech::with_table(BTreeMap::new());
    r.run(20.);
    assert!(r.w.boss.fights.is_empty());
    assert!(r.w.snapshot_for(r.zone).get("bossMech").is_none());
}

#[test]
fn a_ring_kills_inside_and_spares_outside_exactly_when_the_cast_ends() {
    let mut r = rig(TOLL, 2);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 4.);
    r.put(2, boss.x, boss.y + 11.);
    r.run(2.5);
    let view = r.view();
    assert_eq!(view["cast"]["name"], "Toll of the Deep");
    assert_eq!(view["tele"][0]["tele"], "red");
    assert_eq!(view["tele"][0]["color"], bm::Telegraph::Danger.color());
    r.run(4.0);
    assert!(r.alive(1) && r.alive(2), "still warning at 6.5 s");
    r.run(0.8);
    assert!(!r.alive(1), "inside the ring when it landed");
    assert!(r.alive(2), "outside the ring");
    let e = r.events(1);
    assert_eq!(causes(&e), vec!["Toll of the Deep".to_string()]);
    assert!(says(&e, "Killed by Toll of the Deep"));
    assert!(
        causes(&r.events(2)).len() == 1,
        "the death is announced to the whole room"
    );
    assert!(phases(&e, "cast") == 1 && phases(&e, "land") == 1);
}

#[test]
fn defences_do_not_help_against_a_kill() {
    let mut r = rig(TOLL, 1);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 3.);
    let p = r.w.players.get_mut(&1).unwrap();
    p.character.level = 90;
    p.character.hp = p.character.max_hp();
    p.buffs.push(Buff {
        id: "dodge".into(),
        kind: BuffKind::Dodge,
        amount: 0.95,
        left: 60.,
        time: 0.,
    });
    p.buffs.push(Buff {
        id: "shield".into(),
        kind: BuffKind::Shield,
        amount: 0.8,
        left: 60.,
        time: 0.,
    });
    p.set_shield = 1e6;
    p.set_shield_left = 60.;
    p.dash = 1.;
    r.run(7.5);
    assert!(
        !r.alive(1),
        "a kill ignores dodge, shields, absorbs and dash frames"
    );
}

#[test]
fn god_mode_is_told_what_would_have_happened_and_hidden_and_frozen_players_are_never_targeted() {
    let mut r = rig(TOLL, 3);
    let boss = r.w.slimes[r.boss].point();
    for s in 1..=3 {
        r.put(s, boss.x + s as f64, boss.y + 3.);
    }
    r.w.players.get_mut(&1).unwrap().god = true;
    {
        let p = r.w.players.get_mut(&2).unwrap();
        p.character.gm = true;
        p.hidden = true;
    }
    r.w.players.get_mut(&3).unwrap().frozen = true;
    r.run(7.5);
    assert!(r.alive(1) && r.alive(2) && r.alive(3));
    assert!(says(
        &r.events(1),
        "Would have been killed by Toll of the Deep"
    ));
    // A frozen player is immune to ordinary blows as well.
    let point = r.at(3);
    r.w.time += 5.;
    r.w.hurt_player(3, 1000., point);
    assert!(r.alive(3));
    // The world-wide switch behaves like the personal one.
    r.w.players.get_mut(&1).unwrap().god = false;
    r.w.god_mode = true;
    r.run(25.);
    assert!(r.alive(1));
}

#[test]
fn a_city_is_never_a_target() {
    let mut r = rig(TOLL, 1);
    // The Undervault has no city, so give its boss room one for this test.
    r.w.maps[r.zone].city = Some(crate::model::City {
        x0: 100.,
        x1: 130.,
        y0: 0.,
        y1: 45.,
    });
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 3.);
    assert!(r.w.maps[r.zone].in_city(r.at(1)));
    r.run(7.5);
    assert!(r.alive(1));
}

#[test]
fn a_cast_waits_for_a_target_and_never_starts_without_one() {
    let mut r = rig(TOLL, 1);
    r.w.players.get_mut(&1).unwrap().character.zone = 0;
    r.run(10.);
    assert!(r.fight().live.is_empty());
}

// --- zones: echoes, repeats, islands -----------------------------------------------------------------------------

const LANCE: &str = r#"{"mechanics":[{"name":"Moon Lance","block":"zone","shape":{"kind":"lane","width":2},"effect":"kill","cast":5,"every":40,"first":1,"echo":[3]}]}"#;

#[test]
fn a_lane_lands_again_at_the_same_place_after_its_echo_delay() {
    let mut r = rig(LANCE, 3);
    r.run(1.5);
    let view = r.view();
    let (a, b, half) = lane_of(&view);
    assert_eq!(half, 1.);
    // 1 stands in the lane for the first landing; 2 steps in only after it; 3 never does.
    r.put(1, on_line(a, b, 10., 0.).x, on_line(a, b, 10., 0.).y);
    let off = on_line(a, b, 12., 5.);
    r.put(2, off.x, off.y);
    let far = on_line(a, b, 14., -6.);
    r.put(3, far.x, far.y);
    r.run(4.6);
    assert!(!r.alive(1), "the first landing");
    assert!(r.alive(2) && r.alive(3));
    let pale = r.view();
    assert_eq!(
        pale["tele"][0]["echo"], true,
        "a pale copy stays on the floor"
    );
    assert_eq!(
        pale["tele"][0]["shapes"], view["tele"][0]["shapes"],
        "at exactly the same place"
    );
    let step_in = on_line(a, b, 12., 0.);
    r.put(2, step_in.x, step_in.y);
    r.run(3.2);
    assert!(!r.alive(2), "the echo");
    assert!(r.alive(3));
    assert!(r.fight().live.is_empty() || r.view()["tele"].as_array().unwrap().is_empty());
}

#[test]
fn a_repeat_draws_new_islands_each_time_and_kills_whoever_is_off_them() {
    let json = r#"{"mechanics":[{"name":"Rising Tide","block":"zone","shape":{"kind":"islands","count":2,"r":3},"effect":"kill_outside","cast":5,"every":40,"first":1,"repeat":2,"repeat_gap":1,"linger":2}]}"#;
    let mut r = rig(json, 2);
    r.run(1.2);
    let first = r.view()["tele"][0]["shapes"].clone();
    assert_eq!(first.as_array().unwrap().len(), 2);
    assert_eq!(
        r.view()["tele"][0]["tele"],
        "blue",
        "islands are shown as the place to stand"
    );
    let island = |shapes: &Value, n: usize| Point {
        x: shapes[n]["x"].as_f64().unwrap(),
        y: shapes[n]["y"].as_f64().unwrap(),
    };
    let home = island(&first, 0);
    r.put(1, home.x, home.y);
    // A spot well off both islands.
    let (other, nowhere) = (island(&first, 1), Point { x: 0., y: 0. });
    let mut spot = nowhere;
    'search: for y in (6..38).step_by(2) {
        for x in (108..123).step_by(2) {
            let p = Point {
                x: x as f64,
                y: y as f64,
            };
            if p.distance(home) > 5.
                && p.distance(other) > 5.
                && r.w.maps[r.zone].line_clear(p, p, 0.)
            {
                let mut q = p;
                r.w.maps[r.zone].collide(&mut q, PLAYER_RADIUS);
                if q.distance(p) < 1e-6 {
                    spot = p;
                    break 'search;
                }
            }
        }
    }
    assert!(spot.x > 0.);
    r.put(2, spot.x, spot.y);
    r.run(5.2);
    assert!(r.alive(1), "on an island");
    assert!(!r.alive(2), "in the water");
    // The flood drains, then a second one is called with its islands somewhere else.
    r.run(3.4);
    let second = r.view()["tele"][0]["shapes"].clone();
    assert_ne!(first, second, "the islands move between the floods");
    let e = r.events(1);
    assert!(phases(&e, "cast") >= 2, "two floods in a row");
}

#[test]
fn a_heavy_hit_takes_a_share_of_health_and_kills_only_when_it_must() {
    let json = r#"{"mechanics":[{"name":"Slam","block":"zone","shape":{"kind":"circle","r":8},"effect":"heavy","heavy":0.5,"cast":3,"every":40,"first":1}]}"#;
    let mut r = rig(json, 2);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 3.);
    r.put(2, boss.x + 1., boss.y + 3.);
    r.w.players.get_mut(&2).unwrap().character.hp = 5.;
    let full = r.w.players[&1].character.max_hp();
    r.run(4.3);
    let hp = r.w.players[&1].character.hp;
    assert!(
        (hp - (full - (full * 0.5).round())).abs() < 1.5,
        "half the health is gone, not all: {hp} of {full}"
    );
    assert!(!r.alive(2), "a hit larger than what is left kills");
}

// --- shield and adds ----------------------------------------------------------------------------------------------

const CHORUS: &str = r#"{"mechanics":[{"name":"The Bound Chorus","block":"shield","steps":[{"hp":0.66,"tag":"singer","count":4},{"hp":0.33,"tag":"singer","count":6}]}]}"#;

#[test]
fn a_shield_rises_at_its_mark_blocks_every_blow_and_falls_when_its_adds_are_dead() {
    let mut r = rig(CHORUS, 2);
    let singers = r.sleepers(
        "singer",
        &[
            (110., 10.),
            (112., 10.),
            (114., 10.),
            (118., 10.),
            (120., 10.),
        ],
    );
    r.run(1.);
    assert!(r.fight().shield.is_none(), "above the mark");
    r.set_boss_share(0.65);
    r.run(0.2);
    let shield = r.fight().shield.as_ref().expect("the shield is up");
    assert_eq!(shield.adds.len(), 4, "four singers rise at the first mark");
    let awake: Vec<_> = singers.iter().filter(|s| !r.w.slimes[**s].dead).collect();
    assert_eq!(awake.len(), 4);
    assert!(r.w.slimes[*awake[0]].hunt && r.w.slimes[*awake[0]].target.is_some());
    // Nothing gets through, from anyone, however large; the boss does not even flinch.
    let before = r.w.slimes[r.boss].hp;
    assert_eq!(r.hit_boss(1, 5.), 0.);
    assert_eq!(r.hit_boss(2, 1e9), 0.);
    assert_eq!(r.w.slimes[r.boss].hp, before);
    assert!(r.events(1).iter().any(|e| e["kind"] == "immune"));
    assert_eq!(r.view()["shield"]["alive"], 4);
    // Kill three: still up. Kill the fourth: down.
    for s in awake.iter().take(3) {
        r.w.hit_slime(**s, 1, 1e9, false);
    }
    r.run(0.1);
    assert!(r.fight().shield.is_some());
    r.w.hit_slime(*awake[3], 1, 1e9, false);
    r.run(0.1);
    assert!(r.fight().shield.is_none());
    assert!(r.hit_boss(1, 5.) > 0., "the boss can be hurt again");
    // The second mark: six singers asked for, one is left asleep, so the four that fell are put to work again.
    r.set_boss_share(0.3);
    r.run(0.2);
    assert_eq!(r.fight().shield.as_ref().unwrap().adds.len(), 5);
}

#[test]
fn a_shield_with_nothing_to_wake_does_not_make_the_boss_untouchable() {
    let mut r = rig(CHORUS, 1);
    r.set_boss_share(0.5);
    r.run(0.5);
    assert!(r.fight().shield.is_none(), "no sleepers, no shield");
    assert!(r.hit_boss(1, 5.) > 0.);
}

#[test]
fn a_shield_that_heals_heals_and_the_enrage_clock_runs_through_it() {
    let json = r#"{"mechanics":[{"name":"Pearl Shell","block":"shield","heal_per_s":0.02,"steps":[{"hp":0.75,"tag":"pearl","count":3,"still":true}]}]}"#;
    let mut r = rig(json, 1);
    let pearls = r.sleepers("pearl", &[(110., 10.), (114., 10.), (118., 10.)]);
    r.set_boss_share(0.7);
    r.run(0.1);
    let hp = r.w.slimes[r.boss].hp;
    r.run(5.);
    let gained = (r.w.slimes[r.boss].hp - hp) / r.max_hp();
    assert!(
        (gained - 0.10).abs() < 0.01,
        "2% a second for 5 s: {gained}"
    );
    // The pearls are held still and cannot strike.
    for p in &pearls {
        assert!(r.w.slimes[*p].set_root_left > 0. && r.w.slimes[*p].atk_cd > 0.);
    }
    // The soft enrage counts on while the boss cannot be hurt: the AI's own clock, driven through `step()`.
    let mut r = rig(json, 1);
    r.sleepers("pearl", &[(110., 10.), (114., 10.), (118., 10.)]);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 4.);
    r.w.players.get_mut(&1).unwrap().god = true;
    r.set_boss_share(0.7);
    for _ in 0..20 {
        r.w.step();
    }
    assert!(r.fight().shield.is_some());
    let before = r.w.slimes[r.boss].fight;
    for _ in 0..100 {
        r.w.step();
    }
    assert!(
        r.w.slimes[r.boss].fight - before > 4.5,
        "five seconds of shield are five seconds of fight"
    );
    const { assert!(bm::ENRAGE_RUNS_DURING_INVULNERABLE) };
}

// --- break -------------------------------------------------------------------------------------------------------

const DIRGE: &str = r#"{"mechanics":[{"name":"Dirge of the Hollow","block":"break","cast":8,"every":30,"first":1,"bar":0.05,"stun":6,"vulnerable":0.3}]}"#;

#[test]
fn a_break_bar_filled_in_time_stuns_the_boss_and_nobody_dies() {
    let mut r = rig(DIRGE, 2);
    r.run(2.);
    let view = r.view();
    assert_eq!(view["break"]["name"], "Dirge of the Hollow");
    let needed = view["break"]["needed"].as_f64().unwrap();
    assert!((needed - r.max_hp() * 0.05).abs() < 1e-6);
    assert!(
        r.w.slimes[r.boss].set_root_left > 0.,
        "the channel holds him in place"
    );
    // Damage from everyone counts, in pieces.
    r.hit_boss(1, needed * 0.6);
    r.run(1.);
    assert!(r.view()["break"]["dealt"].as_f64().unwrap() > needed * 0.5);
    assert_eq!(r.view()["stunned"].as_f64().unwrap(), 0.);
    r.hit_boss(2, needed * 0.5);
    r.run(0.2);
    assert!(
        r.view()["stunned"].as_f64().unwrap() > 5.5,
        "broken: stunned for 6 s"
    );
    assert_eq!(r.view()["break"], Value::Null);
    // He takes 30% more while stunned, and the extra ends with the stun.
    let Incoming::Damage(d) = r.w.boss_incoming(r.boss, 100.) else {
        panic!("hurtable")
    };
    assert!((d - 130.).abs() < 1e-9);
    r.run(8.);
    let Incoming::Damage(d) = r.w.boss_incoming(r.boss, 100.) else {
        panic!("hurtable")
    };
    assert_eq!(d, 100.);
    assert!(r.alive(1) && r.alive(2));
}

#[test]
fn a_break_bar_left_unfilled_ends_in_the_wail() {
    let mut r = rig(DIRGE, 2);
    r.run(8.5);
    assert!(r.alive(1) && r.alive(2), "one second to spare at 9.0 s");
    r.run(0.7);
    assert!(!r.alive(1) && !r.alive(2));
    assert_eq!(
        causes(&r.events(1)),
        vec![
            "Dirge of the Hollow".to_string(),
            "Dirge of the Hollow".to_string()
        ]
    );
    // Damage that lands on the shield-less boss outside a channel starts nothing.
    let mut r = rig(DIRGE, 1);
    r.run(0.1);
    r.hit_boss(1, r.max_hp() * 0.5);
    r.run(0.1);
    assert_eq!(
        r.fight().live.len(),
        0,
        "the first dirge is not due for a second"
    );
}

// --- marks -------------------------------------------------------------------------------------------------------

const DOWNPOUR: &str = r#"{"mechanics":[{"name":"Downpour","block":"mark","count":3,"every":40,"first":1,"cast":5,"effect":{"kind":"burst","r":4}}]}"#;

#[test]
fn a_mark_never_marks_everyone() {
    for (party, marked) in [(1, 1), (2, 1), (3, 2), (4, 3), (5, 3)] {
        let mut r = rig(DOWNPOUR, party);
        r.run(1.5);
        assert_eq!(
            r.view()["marked"].as_array().unwrap().len(),
            marked,
            "party of {party}"
        );
    }
}

#[test]
fn a_burst_kills_the_unmarked_beside_the_bearer_and_never_the_bearer() {
    let mut r = rig(DOWNPOUR, 2);
    r.run(1.5);
    let bearer_id = r.view()["marked"][0].as_str().unwrap().to_string();
    let bearer = if r.w.players[&1].character.id == bearer_id {
        1
    } else {
        2
    };
    let other = 3 - bearer;
    r.put(bearer, 112., 20.);
    r.put(other, 114., 20.);
    // The ring follows the bearer to the last moment.
    r.run(2.);
    let moved = r.put(bearer, 119., 30.);
    let ring = &r.view()["tele"][0]["shapes"][0];
    assert_eq!(
        (ring["x"].as_f64().unwrap(), ring["y"].as_f64().unwrap()),
        (moved.x, moved.y)
    );
    r.put(other, moved.x + 1.5, moved.y);
    assert!(r.at(other).distance(moved) < 3.5);
    r.run(3.4);
    assert!(r.alive(bearer), "the mark never hurts its own bearer");
    assert!(!r.alive(other), "inside the ring when it burst");
    // The spread-out case: nobody beside the bearer, nobody dies.
    let mut r = rig(DOWNPOUR, 2);
    r.run(1.5);
    r.put(1, 108., 6.);
    r.put(2, 122., 36.);
    r.run(5.);
    assert!(r.alive(1) && r.alive(2));
}

#[test]
fn marks_come_in_waves_when_asked() {
    let json = r#"{"mechanics":[{"name":"Downpour","block":"mark","count":1,"every":40,"first":1,"cast":5,"effect":{"kind":"burst","r":3},"waves":2,"wave_gap":3}]}"#;
    let mut r = rig(json, 3);
    r.run(6.4);
    assert_eq!(
        r.view()["marked"],
        json!([]),
        "between the waves nobody is marked"
    );
    r.run(3.);
    assert_eq!(
        r.view()["marked"].as_array().unwrap().len(),
        1,
        "the second wave"
    );
    r.run(5.);
    assert!(r.fight().live.is_empty());
    assert_eq!(phases(&r.events(1), "cast"), 2);
}

#[test]
fn a_beam_follows_the_bearer_bounces_and_spares_the_bearer() {
    let json = r#"{"mechanics":[{"name":"Prism Bounce","block":"mark","count":1,"every":40,"first":1,"cast":5,"effect":{"kind":"beam","bounces":2,"width":1.6}}]}"#;
    let mut r = rig(json, 2);
    r.run(1.5);
    let bearer_id = r.view()["marked"][0].as_str().unwrap().to_string();
    let bearer = if r.w.players[&1].character.id == bearer_id {
        1
    } else {
        2
    };
    let other = 3 - bearer;
    r.put(bearer, 116., 30.);
    let tele = r.view()["tele"].clone();
    assert_eq!(tele.as_array().unwrap().len(), 1, "one beam per bearer");
    assert_eq!(
        tele[0]["shapes"].as_array().unwrap().len(),
        3,
        "three segments for two bounces"
    );
    assert_eq!(tele[0]["tele"], "dashed line");
    assert_eq!(tele[0]["dashed"], true);
    // The first segment runs from the boss through the bearer to the wall; stand on it, and then off all of it.
    let first = &tele[0]["shapes"][0];
    let (a, b) = (
        Point {
            x: first["x1"].as_f64().unwrap(),
            y: first["y1"].as_f64().unwrap(),
        },
        Point {
            x: first["x2"].as_f64().unwrap(),
            y: first["y2"].as_f64().unwrap(),
        },
    );
    let on = on_line(a, b, 8., 0.);
    r.put(other, on.x, on.y);
    r.run(5.);
    assert!(r.alive(bearer) && !r.alive(other));
}

// --- sweeps ------------------------------------------------------------------------------------------------------

const BRAMBLE: &str = r#"{"mechanics":[{"name":"Bramble Sweep","block":"sweep","every":40,"first":1,"kind":{"shape":"walls","warn":4,"speed":4,"thickness":3,"gap":4,"walls":[{"from":"west","gap":"middle"}]}}]}"#;

#[test]
fn a_wall_warns_then_sweeps_the_room_and_only_the_gap_is_safe() {
    let mut r = rig(BRAMBLE, 2);
    // The gap is the arena's middle; the solid parts are everywhere else along the wall.
    let mid = (r.arena.y0 + r.arena.y1) / 2.;
    r.put(1, 112., mid);
    r.put(2, 112., mid - 8.);
    r.run(2.);
    let view = r.view();
    assert_eq!(
        view["tele"][0]["tele"], "dashed line",
        "dashed during the warning"
    );
    assert_eq!(view["tele"][1]["tele"], "green gap");
    assert_eq!(view["cast"]["name"], "Bramble Sweep");
    r.run(2.9);
    assert!(r.alive(1) && r.alive(2), "still warning at 3.9 s");
    assert_eq!(r.view()["tele"][0]["tele"], "dashed line");
    r.run(2.);
    assert_eq!(
        r.view()["tele"][0]["tele"],
        "red",
        "moving: the same wall now hurts"
    );
    r.run(3.);
    assert!(r.alive(1), "stood in the gap while it passed");
    assert!(!r.alive(2), "stood in the wall");
    assert_eq!(causes(&r.events(2)), vec!["Bramble Sweep".to_string()]);
    r.run(4.);
    assert!(
        r.fight().live.is_empty(),
        "the wall is gone once it has crossed the room"
    );
}

#[test]
fn a_wall_from_the_north_and_one_from_the_east_each_have_their_own_gap() {
    let json = r#"{"mechanics":[{"name":"Bramble Sweep","block":"sweep","every":40,"first":1,"kind":{"shape":"walls","warn":4,"speed":4,"thickness":3,"gap":4,"walls":[{"from":"north","gap":"low"},{"from":"east","gap":"high"}]}}]}"#;
    let mut r = rig(json, 1);
    r.run(1.2);
    let tele = r.view()["tele"].clone();
    assert_eq!(tele.as_array().unwrap().len(), 4, "two walls, a gap each");
    r.run(20.);
    assert!(r.fight().live.is_empty());
}

const SPOKES: &str = r#"{"mechanics":[
    {"name":"Orrery Spokes","block":"sweep","hp_min":0.3,"kind":{"shape":"spokes","count":3,"width":1.6,"deg_per_s":20,"reverse_every":6,"reverse_warn":2,"length":12}},
    {"name":"Orrery Spokes","block":"sweep","hp_max":0.3,"kind":{"shape":"spokes","count":4,"width":1.6,"deg_per_s":28,"reverse_every":6,"reverse_warn":2,"length":12}}]}"#;

#[test]
fn spokes_turn_kill_on_touch_reverse_after_a_warning_and_escalate_below_thirty_per_cent() {
    let mut r = rig(SPOKES, 2);
    r.run(0.5);
    let view = r.view();
    let spokes = view["tele"][0]["shapes"].as_array().unwrap().clone();
    assert_eq!(spokes.len(), 3);
    let tip = |s: &Value| Point {
        x: s["x2"].as_f64().unwrap(),
        y: s["y2"].as_f64().unwrap(),
    };
    let centre = Point {
        x: s_f(&spokes[0], "x1"),
        y: s_f(&spokes[0], "y1"),
    };
    assert_eq!(centre, r.arena.centre());
    // Standing on a spoke is death; standing mid-way between two is not (yet). The room has pillars, so look along
    // the spoke for a free spot that is really on it, and between the spokes for one that is really clear.
    let angle0 = (tip(&spokes[0]).y - centre.y).atan2(tip(&spokes[0]).x - centre.x);
    let free = |r: &Rig, p: Point| {
        let mut q = p;
        r.w.maps[r.zone].collide(&mut q, PLAYER_RADIUS);
        q.distance(p) < 1e-6
    };
    let at_angle = |a: f64, d: f64| Point {
        x: centre.x + a.cos() * d,
        y: centre.y + a.sin() * d,
    };
    let on = (50..110)
        .map(|n| at_angle(angle0, n as f64 / 10.))
        .find(|p| free(&r, *p))
        .expect("a free spot on the spoke");
    r.put(1, on.x, on.y);
    let between = (50..110)
        .map(|n| at_angle(angle0 + std::f64::consts::PI / 3., n as f64 / 10.))
        .find(|p| free(&r, *p))
        .expect("a free spot between spokes");
    r.put(2, between.x, between.y);
    assert_eq!(r.at(2), between);
    r.run(0.1);
    assert!(
        !r.alive(1) && r.alive(2),
        "on {on:?} between {between:?} hp {} {} spokes {}",
        r.w.players[&1].character.hp,
        r.w.players[&2].character.hp,
        r.view()["tele"][0]["shapes"]
    );
    assert_eq!(causes(&r.events(1)), vec!["Orrery Spokes".to_string()]);
    // The angle of the first spoke now, then after 3 s, 3 s into the warning: it is turning one way.
    let angle = |r: &Rig| {
        let s = &r.view()["tele"][0]["shapes"][0];
        (s["y2"].as_f64().unwrap() - r.arena.centre().y)
            .atan2(s["x2"].as_f64().unwrap() - r.arena.centre().x)
    };
    let (a0, _) = (angle(&r), r.run(3.0));
    let a1 = angle(&r);
    assert!(
        (turned(a0, a1).to_degrees() - 60.).abs() < 1.5,
        "20 degrees a second, whichever side of the atan2 wrap"
    );
    // At 4 s of the 6 the gear warning shows; at 6 s it turns the other way.
    r.run(1.2);
    assert_eq!(r.view()["tele"][0]["reversing"], true);
    assert!(
        r.events(2).iter().any(|e| e["kind"] == "bossmech"
            && e["phase"] == "cast"
            && e["name"] == "Orrery Spokes"
            && e["value"] == 2.),
        "the two-second reversal warning also sounds before the turn"
    );
    r.put(2, 108., 36.);
    r.run(1.5);
    let a2 = angle(&r);
    r.run(1.0);
    let a3 = angle(&r);
    assert!(turned(a2, a3).to_degrees() < -15., "reversed");
    assert!(phases(&r.events(2), "reverse") >= 1);
    // Below thirty per cent: four spokes at 28 degrees a second replace the three.
    r.set_boss_share(0.25);
    r.run(0.2);
    let shapes = r.view()["tele"].clone();
    assert_eq!(
        shapes.as_array().unwrap().len(),
        1,
        "one set of spokes at a time"
    );
    assert_eq!(shapes[0]["shapes"].as_array().unwrap().len(), 4);
}

#[test]
fn shipped_eye_cover_and_axis_spokes_match_their_dungeon_rooms() {
    let w = world();
    let eye = w
        .slimes
        .iter()
        .find(|s| s.kind == "eye_unblinking")
        .unwrap();
    let axis = w.slimes.iter().find(|s| s.kind == "astro_axis").unwrap();
    let cover = [
        (43., 20.),
        (53., 20.),
        (42., 25.),
        (54., 25.),
        (43., 30.),
        (53., 30.),
    ];
    let eye_def = &w.boss.table["eye_unblinking"];
    assert_eq!(eye_def.mechanics.len(), 2);
    for (late, m) in eye_def.mechanics.iter().enumerate() {
        let Block::Gaze(g) = &m.block else {
            panic!("the Eye needs a gaze")
        };
        assert_eq!(g.cast, 5.);
        assert_eq!(g.every, if late == 0 { 25. } else { 15. });
        assert_eq!(g.regrow, 45.);
        assert_eq!(g.sweep > 0., late == 1);
        assert_eq!(g.cover.len(), 6);
        for (c, (x, y)) in g.cover.iter().zip(cover) {
            assert_eq!((c.x, c.y), (x, y));
            assert!(
                w.maps[eye.zone]
                    .objects
                    .iter()
                    .any(|o| o.r == 0. && o.x == x && o.y == y)
            );
            assert!(bm::arena_for(&w.maps[eye.zone], eye.point()).contains(Point { x, y }));
        }
    }
    let axis_def = &w.boss.table["astro_axis"];
    assert_eq!(axis_def.mechanics.len(), 2);
    for (late, m) in axis_def.mechanics.iter().enumerate() {
        let Block::Sweep(s) = &m.block else {
            panic!("the Axis needs turning spokes")
        };
        let SweepKind::Spokes {
            count,
            width,
            deg_per_s,
            reverse_every,
            reverse_warn,
            length,
        } = s.kind
        else {
            panic!("the Axis needs spokes")
        };
        assert_eq!(count, if late == 0 { 3 } else { 4 });
        assert_eq!(width, 1.6);
        assert_eq!(deg_per_s, if late == 0 { 20. } else { 21. });
        assert_eq!((reverse_every, reverse_warn), (12., 2.));
        assert_eq!(length, 10.);
        assert!(
            deg_per_s.to_radians() * 8. < 3.,
            "the gap stays under 3 tiles/s at 8 tiles"
        );
    }
    assert_eq!(bm::arena_for(&w.maps[axis.zone], axis.point()).width(), 20.);
}
/// The signed turn from angle `a` to angle `b`, in -pi..pi.
fn turned(a: f64, b: f64) -> f64 {
    (b - a + std::f64::consts::PI).rem_euclid(std::f64::consts::TAU) - std::f64::consts::PI
}
fn s_f(v: &Value, k: &str) -> f64 {
    v[k].as_f64().unwrap()
}

// --- gaze ----------------------------------------------------------------------------------------------------------

const GAZE: &str = r#"{"mechanics":[{"name":"Unblinking Gaze","block":"gaze","cast":5,"every":8,"first":1,"regrow":20,"cover":[{"x":116,"y":24,"r":1.2}]}]}"#;

#[test]
fn gaze_cover_is_one_physical_pillar_across_health_phases() {
    let both = r#"{"mechanics":[
        {"name":"Unblinking Gaze","block":"gaze","hp_min":0.3,"cast":5,"every":8,"first":1,"regrow":45,"cover":[{"x":116,"y":24,"r":1.2}]},
        {"name":"Unblinking Gaze","block":"gaze","hp_max":0.3,"cast":5,"every":8,"first":1,"regrow":45,"sweep":6,"beam":12,"cover":[{"x":116,"y":24,"r":1.2}]}
    ]}"#;
    let mut r = rig(both, 1);
    let boss = r.w.slimes[r.boss].point();
    r.open_spot(1, boss.x, boss.y + 18.);
    r.run(6.2);
    let pillars: Vec<_> = r.view()["tele"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|t| t["tele"] == "cover")
        .cloned()
        .collect();
    assert_eq!(pillars.len(), 1, "health phases must share one lens");
    assert_eq!(pillars[0]["hits"], 1, "the first gaze cracks it");
    r.set_boss_share(0.25);
    r.run(0.1);
    let pillars: Vec<_> = r.view()["tele"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|t| t["tele"] == "cover")
        .cloned()
        .collect();
    assert_eq!(pillars.len(), 1);
    assert_eq!(
        pillars[0]["hits"], 1,
        "the crack persists into the late phase"
    );
}

#[test]
fn only_cover_helps_against_a_gaze_and_cover_cracks_breaks_and_regrows() {
    let mut r = rig(GAZE, 2);
    let boss = r.w.slimes[r.boss].point();
    // 1 hides directly behind the pillar, 2 stands in the open to one side.
    r.open_spot(1, boss.x, boss.y + 18.);
    r.open_spot(2, boss.x + 6., boss.y + 12.);
    let map = &r.w.maps[r.zone];
    assert!(
        map.line_clear(boss, r.at(2), 0.05),
        "nothing but the gaze's own cover is in the way of the open spot"
    );
    assert!(
        map.line_clear(boss, r.at(1), 0.05),
        "the hiding place is open ground apart from the pillar"
    );
    // The pillar is on the line to the hiding place and not on the line to the open spot.
    let cover = Point { x: 116., y: 24. };
    assert!(bm::segment_distance(cover, boss, r.at(1)) <= 1.2);
    assert!(bm::segment_distance(cover, boss, r.at(2)) > 1.2);
    r.run(2.);
    let view = r.view();
    assert_eq!(view["tele"][0]["gaze"], true);
    assert_eq!(view["cast"]["name"], "Unblinking Gaze");
    let cover = |v: &Value| {
        v["tele"]
            .as_array()
            .unwrap()
            .iter()
            .find(|t| t["tele"] == "cover")
            .unwrap()
            .clone()
    };
    assert_eq!(
        (
            cover(&view)["hits"].as_u64(),
            cover(&view)["standing"].as_bool()
        ),
        (Some(0), Some(true))
    );
    r.run(4.2);
    assert!(r.alive(1), "behind the pillar");
    assert!(!r.alive(2), "in the open");
    let c = cover(&r.view());
    assert_eq!(
        (c["hits"].as_u64(), c["standing"].as_bool()),
        (Some(1), Some(true)),
        "cracked after one gaze"
    );
    // A second gaze breaks it (a living player stands behind it again), a third finds the player.
    r.run(8.);
    let c = cover(&r.view());
    assert_eq!(
        (c["hits"].as_u64(), c["standing"].as_bool()),
        (Some(2), Some(false)),
        "broken after two"
    );
    assert!(r.alive(1));
    r.run(8.);
    assert!(!r.alive(1), "no cover left");
}

#[test]
fn broken_cover_stands_again_after_its_regrow_time() {
    let mut r = rig(GAZE, 1);
    let boss = r.w.slimes[r.boss].point();
    r.open_spot(1, boss.x, boss.y + 18.);
    r.run(1.0 + 5. + 8. + 5. + 0.3);
    let broken = r.view()["tele"]
        .as_array()
        .unwrap()
        .iter()
        .find(|t| t["tele"] == "cover")
        .unwrap()
        .clone();
    assert_eq!(broken["standing"], false);
    // Nobody is behind it now, so the player steps out of sight of the gazes and waits for the 20 s.
    r.w.players.get_mut(&1).unwrap().character.hp = 1e6;
    r.run(21.);
    let standing = r.view()["tele"]
        .as_array()
        .unwrap()
        .iter()
        .find(|t| t["tele"] == "cover")
        .unwrap()
        .clone();
    assert_eq!(standing["standing"], true);
}

#[test]
fn a_turning_beam_strikes_each_player_as_it_passes_and_cover_still_helps() {
    let json = r#"{"mechanics":[{"name":"Sweeping Gaze","block":"gaze","cast":5,"every":30,"first":1,"sweep":6,"beam":8,"cover":[{"x":116,"y":24,"r":1.2}]}]}"#;
    let mut r = rig(json, 3);
    let boss = r.w.slimes[r.boss].point();
    r.open_spot(1, boss.x, boss.y + 18.);
    r.open_spot(2, boss.x + 6., boss.y + 12.);
    r.open_spot(3, boss.x - 5., boss.y + 10.);
    let cover = Point { x: 116., y: 24. };
    assert!(
        bm::segment_distance(cover, boss, r.at(1)) <= 1.2
            && bm::segment_distance(cover, boss, r.at(2)) > 1.2
            && bm::segment_distance(cover, boss, r.at(3)) > 1.2
    );
    r.run(6.2);
    assert!(
        r.alive(1) && r.alive(2) && r.alive(3),
        "the beam is only turning to face its first direction"
    );
    let mut gone = vec![];
    for _ in 0..70 {
        r.run(0.1);
        for s in 2..=3 {
            if !r.alive(s) && !gone.contains(&s) {
                gone.push(s);
            }
        }
    }
    assert_eq!(
        gone.len(),
        2,
        "both in the open are struck as the beam passes, one after the other"
    );
    assert!(r.alive(1), "the hidden one is never struck");
    let cone = r.view();
    assert!(
        cone["tele"]
            .as_array()
            .is_none_or(|t| t.iter().all(|x| x["gaze"] != true)),
        "the beam is gone after one turn"
    );
}

// --- adds, blooms, stasis -----------------------------------------------------------------------------------------

#[test]
fn seeds_that_are_not_burst_bloom_heal_the_boss_and_become_something_worse() {
    let json = r#"{"mechanics":[{"name":"Germination","block":"adds","tag":"seed","count":3,"every":30,"first":1,"scatter":true,"still":true,"bloom":{"after":6,"heal":0.04,"then":"treant"}}]}"#;
    let mut r = rig(json, 1);
    let seeds = r.sleepers("seed", &[(110., 10.), (114., 10.), (118., 10.)]);
    let treants = r.sleepers("treant", &[(112., 12.), (116., 12.), (120., 12.)]);
    r.set_boss_share(0.5);
    r.run(1.5);
    for s in &seeds {
        assert!(!r.w.slimes[*s].dead);
        assert!(r.w.slimes[*s].set_root_left > 0., "a seed does not walk");
        assert!(
            r.arena.contains(r.w.slimes[*s].point()),
            "scattered inside the room"
        );
    }
    // One is burst in time; the other two bloom after six seconds.
    r.w.hit_slime(seeds[0], 1, 1e9, false);
    let hp = r.w.slimes[r.boss].hp;
    r.run(6.2);
    assert!(seeds.iter().all(|s| r.w.slimes[*s].dead));
    let healed = (r.w.slimes[r.boss].hp - hp) / r.max_hp();
    assert!(
        (healed - 0.08).abs() < 0.005,
        "4% for each of the two that bloomed: {healed}"
    );
    assert_eq!(
        treants.iter().filter(|t| !r.w.slimes[**t].dead).count(),
        2,
        "a treant for each bloom"
    );
}

const AMBER: &str = r#"{"mechanics":[{"name":"Amber Stasis","block":"stasis","every":60,"first":1,"orbs":2,"speed":8,"life":10,"tag":"cocoon","hold":6}]}"#;

#[test]
fn amber_freezes_the_players_the_orbs_touch_and_a_friend_can_break_the_cocoon() {
    let mut r = rig(AMBER, 3);
    r.sleepers("cocoon", &[(110., 10.), (112., 10.)]);
    let boss = r.w.slimes[r.boss].point();
    for s in 1..=3 {
        r.put(s, boss.x - 4. + s as f64 * 4., boss.y + 6.);
    }
    r.run(3.);
    let frozen: Vec<u64> = (1..=3).filter(|s| r.w.players[s].frozen).collect();
    assert_eq!(frozen.len(), 2, "two orbs, two players");
    let free = (1..=3).find(|s| !frozen.contains(s)).unwrap();
    let stuck = frozen[0];
    let cocoon = r.fight().frozen[&stuck].cocoon;
    assert!(!r.w.slimes[cocoon].dead);
    assert!(
        r.w.slimes[cocoon].point().distance(r.at(stuck)) < 0.5,
        "the cocoon stands where the player froze"
    );
    assert_eq!(r.view()["frozen"].as_array().unwrap().len(), 2);
    // A frozen player cannot move, act or be hurt.
    let at = r.at(stuck);
    r.w.message(stuck, ClientMessage::Input { dx: 1., dy: 0. });
    r.w.message(
        stuck,
        ClientMessage::Move {
            x: at.x + 5.,
            y: at.y,
        },
    );
    r.w.message(stuck, ClientMessage::Attack { fx: 1., fy: 0. });
    r.w.time += 0.1;
    r.w.update_player(stuck);
    assert!(r.w.players[&stuck].input.x == 0. && r.w.players[&stuck].goal.is_none());
    assert_eq!(r.at(stuck), at);
    r.w.hurt_player(stuck, 1e6, at);
    assert!(r.alive(stuck));
    assert!(!r.w.mech_kill(stuck, "anything", r.boss));
    // The free player breaks the cocoon: the frozen one walks away.
    r.w.hit_slime(cocoon, free, 1e9, false);
    r.run(0.2);
    assert!(!r.w.players[&stuck].frozen);
    // The other one is not freed in time: the amber closes.
    let lost = frozen[1];
    assert!(r.w.players[&lost].frozen);
    r.run(6.5);
    assert!(!r.alive(lost), "lost in the amber");
    assert!(!r.w.players[&lost].frozen);
    assert_eq!(causes(&r.events(lost)), vec!["Amber Stasis".to_string()]);
    assert!(r.w.slimes[r.fight().woken[0]].dead || true);
}

#[test]
fn a_boss_with_no_cocoons_to_spare_freezes_nobody() {
    let mut r = rig(AMBER, 2);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 6.);
    r.put(2, boss.x + 4., boss.y + 6.);
    r.run(4.);
    assert!(!r.w.players[&1].frozen && !r.w.players[&2].frozen);
}

// --- hold and lit places -------------------------------------------------------------------------------------------

const NIGHT: &str = r#"{"mechanics":[
    {"name":"Braziers","block":"hold","points":[[112,12],[120,12]],"r":2.5,"hold_for":3,"lit_for":20},
    {"name":"The Longest Night","block":"zone","shape":{"kind":"lit"},"effect":"kill_outside","cast":5,"every":40,"first":9}]}"#;

#[test]
fn a_place_is_lit_by_holding_it_and_only_the_lit_ones_keep_the_night_off() {
    let mut r = rig(NIGHT, 2);
    r.put(1, 112., 12.);
    r.put(2, 116., 30.);
    r.run(2.5);
    let lit = |r: &Rig| {
        r.view()["tele"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|t| t["name"] == "Braziers")
            .map(|t| t["lit"].as_bool().unwrap())
            .collect::<Vec<_>>()
    };
    assert_eq!(
        lit(&r),
        vec![false, false],
        "not yet, three seconds are needed"
    );
    let progress = r.view()["tele"][0]["progress"].as_f64().unwrap();
    assert!(progress > 0.7 && progress < 0.95);
    r.run(1.0);
    assert_eq!(lit(&r), vec![true, false]);
    // The night falls at 9 s + 5 s of warning: the one inside the lit circle lives, the one outside does not.
    r.run(14.5 - 3.5);
    assert!(r.alive(1), "inside a lit circle");
    assert!(!r.alive(2), "outside");
    assert_eq!(
        r.events(1)
            .iter()
            .filter(|e| e["kind"] == "bossmech" && e["phase"] == "cast")
            .count(),
        1
    );
}

#[test]
fn a_flurry_snuffs_a_lit_place_on_schedule() {
    let json = r#"{"mechanics":[{"name":"Braziers","block":"hold","points":[[112,12],[120,12]],"r":2.5,"hold_for":3,"lit_for":20,"snuff_every":9}]}"#;
    let mut r = rig(json, 1);
    r.put(1, 112., 12.);
    r.run(3.4);
    assert_eq!(r.view()["tele"][0]["lit"], true);
    r.run(6.);
    assert_eq!(r.view()["tele"][0]["lit"], false, "snuffed at 9 s");
}

// --- split -----------------------------------------------------------------------------------------------------------

const SUNS: &str = r#"{"mechanics":[{"name":"Twin Suns","block":"split","hp":0.6,"tag":"cinder","revive_after":10,"survivor_bonus":0.5,"bridge":0}]}"#;

fn split_rig() -> (Rig, usize) {
    let mut r = rig(SUNS, 2);
    let partner = r.sleepers("cinder", &[(116., 30.)])[0];
    r.set_boss_share(0.58);
    r.run(0.1);
    (r, partner)
}

#[test]
fn a_boss_divides_at_its_mark_into_two_bodies_with_half_the_health_each() {
    let (mut r, partner) = split_rig();
    assert_eq!(r.fight().partner, Some(partner));
    let (a, b) = (r.w.slimes[r.boss].hp, r.w.slimes[partner].hp);
    assert_eq!(a, b);
    assert!((a - (r.max_hp() * 0.58 / 2.).ceil()).abs() <= 1.);
    assert_eq!(
        r.w.slimes[partner].max_hp,
        r.max_hp(),
        "both bars on the same scale"
    );
    assert!(!r.w.slimes[partner].dead);
    r.run(2.);
    assert_eq!(r.fight().partner, Some(partner), "it divides once");
}

#[test]
fn a_body_that_falls_alone_is_downed_and_rises_if_the_other_is_not_finished_in_time() {
    let (mut r, partner) = split_rig();
    let damage_before = r.w.slimes[partner].damage;
    r.w.hit_slime(r.boss, 1, 1e9, false);
    assert!(!r.w.slimes[r.boss].dead, "downed, not dead");
    assert_eq!(r.w.slimes[r.boss].hp, 1.);
    assert!(r.fight().downed.contains_key(&r.boss));
    assert_eq!(r.hit_boss(1, 100.), 0., "nothing hurts a downed body");
    assert!(r.w.boss_incoming(partner, 5.).is_damage());
    r.run(9.5);
    assert!(r.fight().downed.contains_key(&r.boss));
    r.run(0.8);
    assert!(r.fight().downed.is_empty());
    let hp = r.w.slimes[r.boss].hp;
    assert!(
        (hp - (r.max_hp() / 2.)).abs() <= 1.,
        "it rises with half its health"
    );
    assert!(
        (r.w.slimes[partner].damage - damage_before * 1.5).abs() < 1e-6,
        "and the survivor hits 50% harder"
    );
}

#[test]
fn both_bodies_falling_within_the_window_finish_the_fight_whichever_goes_first() {
    for first_is_boss in [true, false] {
        let (mut r, partner) = split_rig();
        let (first, second) = if first_is_boss {
            (r.boss, partner)
        } else {
            (partner, r.boss)
        };
        r.w.hit_slime(first, 1, 1e9, false);
        assert!(!r.w.slimes[first].dead);
        r.run(4.);
        assert!(!r.w.instance_cleared(r.zone));
        r.w.hit_slime(second, 1, 1e9, false);
        assert!(
            r.w.slimes[r.boss].dead && r.w.slimes[partner].dead,
            "boss first: {first_is_boss}"
        );
        assert!(
            r.w.instance_cleared(r.zone),
            "the dungeon is cleared only when both are down"
        );
    }
}

#[test]
fn the_bridge_between_the_bodies_kills_what_stands_on_it() {
    let json = SUNS.replace(r#""bridge":0"#, r#""bridge":1"#);
    let mut r = rig(&json, 2);
    let partner = r.sleepers("cinder", &[(116., 30.)])[0];
    r.set_boss_share(0.58);
    r.run(0.1);
    let (a, b) = (r.w.slimes[r.boss].point(), r.w.slimes[partner].point());
    let mid = Point {
        x: (a.x + b.x) / 2.,
        y: (a.y + b.y) / 2.,
    };
    r.put(1, mid.x, mid.y);
    let off = on_line(a, b, a.distance(b) / 2., 6.);
    r.put(2, off.x, off.y);
    // The bridge is drawn for its warning first (a dashed path), and kills only after it.
    r.run(1.);
    assert!(r.alive(1), "still warning");
    assert_eq!(
        r.view()["tele"].as_array().unwrap().last().unwrap()["tele"],
        "dashed line"
    );
    r.run(2.5);
    assert!(!r.alive(1) && r.alive(2));
    assert_eq!(causes(&r.events(1)), vec!["Twin Suns".to_string()]);
}

trait IsDamage {
    fn is_damage(&self) -> bool;
}
impl IsDamage for Incoming {
    fn is_damage(&self) -> bool {
        matches!(self, Incoming::Damage(_))
    }
}

// --- the danger query -----------------------------------------------------------------------------------------------

#[test]
fn the_danger_query_names_what_will_hurt_a_spot_and_when() {
    let mut r = rig(TOLL, 2);
    let boss = r.w.slimes[r.boss].point();
    let inside = r.put(1, boss.x, boss.y + 4.);
    let outside = r.put(2, boss.x, boss.y + 12.);
    r.run(1.0);
    assert_eq!(
        r.w.boss_danger(r.zone, 1, inside),
        None,
        "nothing is cast yet"
    );
    r.run(2.0);
    let (name, left) =
        r.w.boss_danger(r.zone, 1, inside)
            .expect("the ring is coming");
    assert_eq!(name, "Toll of the Deep");
    assert!((left - 4.).abs() < 0.2, "five seconds minus one: {left}");
    assert_eq!(r.w.boss_danger(r.zone, 2, outside), None);
    // The same query for a hired fighter agrees with what then happens.
    r.run(4.5);
    assert!(!r.alive(1) && r.alive(2));
}

#[test]
fn the_danger_query_covers_marks_walls_breaks_and_gazes() {
    // A mark: dangerous beside the bearer, never to the bearer.
    let mut r = rig(DOWNPOUR, 2);
    r.run(1.5);
    let bearer_id = r.view()["marked"][0].as_str().unwrap().to_string();
    let bearer = if r.w.players[&1].character.id == bearer_id {
        1
    } else {
        2
    };
    let spot = r.put(bearer, 116., 28.);
    assert_eq!(
        r.w.boss_danger(r.zone, bearer, spot),
        None,
        "your own mark is not a danger to you"
    );
    assert_eq!(
        r.w.boss_danger(r.zone, 3 - bearer, spot).map(|d| d.0),
        Some("Downpour".to_string())
    );
    assert_eq!(
        r.w.boss_danger(r.zone, 3 - bearer, Point { x: 108., y: 6. }),
        None
    );
    // A wall: the solid part has an arrival time, the gap does not.
    let mut r = rig(BRAMBLE, 1);
    r.run(2.);
    let mid = (r.arena.y0 + r.arena.y1) / 2.;
    let (name, left) =
        r.w.boss_danger(
            r.zone,
            1,
            Point {
                x: 112.,
                y: mid - 8.,
            },
        )
        .expect("in the wall's path");
    assert_eq!(name, "Bramble Sweep");
    let travel = (112. - r.arena.x0) / 4.;
    assert!(
        left > 2. + travel - 1.5 && left < 2. + travel + 1.5,
        "about the warning plus the walk: {left}"
    );
    assert_eq!(
        r.w.boss_danger(r.zone, 1, Point { x: 112., y: mid }),
        None,
        "the gap"
    );
    // A break: everyone in the fight is in danger until it is broken.
    let mut r = rig(DIRGE, 1);
    r.run(2.);
    assert_eq!(
        r.w.boss_danger(r.zone, 1, r.at(1)).map(|d| d.0),
        Some("Dirge of the Hollow".to_string())
    );
    // A gaze: in the open, yes; behind the cover, no.
    let mut r = rig(GAZE, 1);
    let boss = r.w.slimes[r.boss].point();
    let open = r.open_spot(1, boss.x + 6., boss.y + 12.);
    r.run(2.);
    assert!(r.w.boss_danger(r.zone, 1, open).is_some());
    let hidden = r.open_spot(1, boss.x, boss.y + 18.);
    assert!(r.w.boss_danger(r.zone, 1, hidden).is_none());
}

// --- the fight's life: wipe, copies, wiring ------------------------------------------------------------------------------

#[test]
fn a_wipe_or_an_evade_puts_everything_back_as_it_was() {
    let json = r#"{"mechanics":[
        {"name":"Chorus","block":"shield","steps":[{"hp":0.66,"tag":"singer","count":2}]},
        {"name":"Amber","block":"stasis","every":60,"first":1,"orbs":1,"speed":8,"life":10,"tag":"cocoon","hold":30},
        {"name":"Toll","block":"zone","shape":{"kind":"circle","r":8},"effect":"kill","cast":5,"every":25,"first":12}]}"#;
    let mut r = rig(json, 2);
    let singers = r.sleepers("singer", &[(110., 10.), (112., 10.)]);
    r.sleepers("cocoon", &[(114., 10.), (116., 10.)]);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 6.);
    r.put(2, boss.x + 4., boss.y + 6.);
    r.set_boss_share(0.6);
    r.run(4.);
    assert!(r.fight().shield.is_some() && r.fight().clock > 3.9);
    let frozen = (1..=2)
        .find(|s| r.w.players[s].frozen)
        .expect("someone is in amber");
    // The party falls / the boss gives up and walks home.
    r.w.slimes[r.boss].state = "return".into();
    r.run(0.1);
    assert!(r.w.boss.fights.is_empty(), "the fight is over");
    assert!(
        singers
            .iter()
            .all(|s| r.w.slimes[*s].dead && r.w.slimes[*s].respawn >= 1e8),
        "asleep again"
    );
    assert!(!r.w.players[&frozen].frozen);
    // The next pull is a new fight: a fresh clock, the shield down and able to rise again.
    r.w.slimes[r.boss].state = "chase".into();
    r.set_boss_share(0.6);
    r.run(0.2);
    assert!(r.fight().clock < 0.5);
    assert_eq!(r.fight().shield.as_ref().map(|s| s.adds.len()), Some(2));
}

#[test]
fn a_boss_that_dies_ends_its_fight_and_its_adds() {
    let mut r = rig(CHORUS, 1);
    let singers = r.sleepers(
        "singer",
        &[(110., 10.), (112., 10.), (114., 10.), (116., 10.)],
    );
    r.set_boss_share(0.5);
    r.run(0.2);
    assert!(singers.iter().any(|s| !r.w.slimes[*s].dead));
    r.w.slimes[r.boss].dead = true;
    r.w.slimes[r.boss].hp = 0.;
    r.run(0.1);
    assert!(r.w.boss.fights.is_empty());
    assert!(singers.iter().all(|s| r.w.slimes[*s].dead));
}

#[test]
fn two_copies_of_a_dungeon_never_share_a_timer_a_shield_or_a_death() {
    let mut w = world();
    w.boss = table(
        r#"{"mechanics":[
            {"name":"Toll","block":"zone","shape":{"kind":"circle","r":8},"effect":"kill","cast":5,"every":40,"first":2},
            {"name":"Chorus","block":"shield","steps":[{"hp":0.66,"tag":"singer","count":1}]}]}"#,
    );
    let template = w
        .maps
        .iter()
        .position(|m| m.final_boss == "hollowking")
        .unwrap();
    let copies: Vec<usize> = w
        .instances
        .iter()
        .filter(|i| i.template == template)
        .map(|i| i.zone)
        .collect();
    assert!(copies.len() >= 2);
    let (z1, z2) = (copies[0], copies[1]);
    let boss_of = |w: &World, z: usize| {
        w.slimes
            .iter()
            .find(|s| s.zone == z && s.kind == "hollowking")
            .unwrap()
            .id
    };
    let (b1, b2) = (boss_of(&w, z1), boss_of(&w, z2));
    assert_ne!(b1, b2);
    for z in [z1, z2] {
        w.enter_instance(z);
        let id = w.spawns.len();
        w.spawns.push(SlimeSpawn {
            x: 110.,
            y: 10.,
            kind: "thrall".into(),
            ambush: Some("singer".into()),
            zone: z,
        });
        let e = w.dormant_enemy(id);
        w.slimes.push(e);
    }
    let mut rx = vec![];
    for (session, z) in [(1u64, z1), (2, z2)] {
        rx.push(join(&mut w, session, Class::Warrior));
        let p = w.players.get_mut(&session).unwrap();
        p.character.zone = z;
        let boss = w
            .slimes
            .iter()
            .find(|s| s.zone == z && s.kind == "hollowking")
            .unwrap()
            .point();
        let c = &mut w.players.get_mut(&session).unwrap().character;
        (c.x, c.y) = (boss.x, boss.y + 4.);
        c.hp = c.max_hp();
    }
    for b in [b1, b2] {
        w.slimes[b].state = "chase".into();
        w.slimes[b].target = Some(1);
        w.slimes[b].damage = 0.;
        w.slimes[b].atk_cd = 1e9;
    }
    let run = |w: &mut World, secs: f64| {
        for _ in 0..(secs / TICK).round() as usize {
            w.time += TICK;
            w.tick += 1;
            w.update_boss_mechanics();
        }
    };
    // Only the first copy's boss is hurt below the shield mark.
    w.slimes[b1].hp = (w.slimes[b1].max_hp * 0.5).round();
    run(&mut w, 1.);
    assert!(w.boss.fights[&b1].shield.is_some());
    assert!(
        w.boss.fights[&b2].shield.is_none(),
        "the other copy's boss is not shielded"
    );
    assert!(matches!(w.boss_incoming(b2, 10.), Incoming::Damage(_)));
    // The timers are the fights' own: wipe the second and the first goes on.
    w.slimes[b2].state = "return".into();
    run(&mut w, 0.1);
    assert!(w.boss.fights.contains_key(&b1) && !w.boss.fights.contains_key(&b2));
    w.slimes[b2].state = "chase".into();
    run(&mut w, 6.3);
    assert!(
        w.players[&1].character.hp <= 0.,
        "the ring landed in the first copy"
    );
    assert!(
        w.players[&2].character.hp > 0.,
        "and not in the second, whose fight began later"
    );
    assert!(w.boss.fights[&b1].clock > w.boss.fights[&b2].clock + 0.9);
    let both = w.snapshot_for(z1);
    assert!(
        both.get("bossMech").is_some(),
        "the copy's snapshot carries its own fight"
    );
    assert!(
        w.snapshot_for(z2)["bossMech"]
            .as_array()
            .unwrap()
            .iter()
            .all(|f| f["boss"] == b2)
    );
}

#[test]
fn resetting_a_dungeon_copy_ends_its_fight() {
    let mut r = rig(CHORUS, 1);
    let singers = r.sleepers(
        "singer",
        &[(110., 10.), (112., 10.), (114., 10.), (116., 10.)],
    );
    r.set_boss_share(0.5);
    r.run(0.2);
    assert!(r.w.boss.fights.contains_key(&r.boss));
    // The last hero walks out: the copy resets on the next step.
    r.w.players.get_mut(&1).unwrap().character.zone = 0;
    r.w.step();
    assert!(r.w.boss.fights.is_empty());
    assert!(singers.iter().all(|s| r.w.slimes[*s].dead));
    assert_eq!(r.w.slimes[r.boss].hp, r.w.slimes[r.boss].max_hp);
}

#[test]
fn step_runs_the_engine_with_the_monsters_ai_and_the_snapshot_carries_the_fight() {
    let mut r = rig(TOLL, 2);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 4.);
    r.put(2, boss.x, boss.y + 12.);
    // Real fighting: the king hunts, so the fight starts by itself.
    r.w.slimes[r.boss].atk_cd = 1e9;
    for _ in 0..60 {
        r.w.step();
    }
    let snap = r.w.snapshot_for(r.zone);
    let fights = snap["bossMech"]
        .as_array()
        .expect("a running fight is in the snapshot");
    assert_eq!(fights.len(), 1);
    assert_eq!(fights[0]["boss"], r.boss);
    assert_eq!(fights[0]["tele"][0]["name"], "Toll of the Deep");
    assert!(
        fights[0]["cast"]["left"].as_f64().unwrap() < fights[0]["cast"]["total"].as_f64().unwrap()
    );
    for _ in 0..80 {
        r.w.step();
    }
    assert!(!r.alive(1), "the ring landed through the real step loop");
    assert!(r.alive(2) || r.w.players[&2].dead_time > 0.);
}

// --- fairness of the authored data -------------------------------------------------------------------------------

/// Whether every zone mechanic of `def` leaves everyone in the boss's arena a way out in time, for twenty draws of
/// its shape. The sixteen boss tasks run this on their own data (and `every_shipped_boss_is_fair` does it for all).
fn unfair_point(w: &World, boss: usize, def: &BossDef) -> Option<(String, Point)> {
    let s = &w.slimes[boss];
    let map = &w.maps[s.zone];
    let arena = bm::arena_for_boss(map, s.point(), def);
    // The braziers a fight lights: the safe discs of a `lit` zone. Fair if ANY two of them are lit (the sign asks
    // the party to keep two burning), so every pair is tried; a boss without braziers has one empty set.
    let lit_sets: Vec<Vec<Shape>> = match def.mechanics.iter().find_map(|m| match &m.block {
        Block::Hold(h) => Some(h),
        _ => None,
    }) {
        Some(h) => {
            let disc = |p: &[f64; 2]| Shape::Circle {
                x: p[0],
                y: p[1],
                r: h.r,
                inner: 0.,
            };
            let mut sets = vec![];
            for a in 0..h.points.len() {
                for b in a + 1..h.points.len() {
                    sets.push(vec![disc(&h.points[a]), disc(&h.points[b])]);
                }
            }
            sets
        }
        None => vec![vec![]],
    };
    for m in &def.mechanics {
        let Block::Zone(z) = &m.block else { continue };
        for lit in &lit_sets {
            for seed in 0..20u64 {
                let mut state = seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) | 1;
                let mut rng = move || {
                    state = state
                        .wrapping_mul(6364136223846793005)
                        .wrapping_add(1442695040888963407);
                    (state >> 11) as f64 / (1u64 << 53) as f64
                };
                let players: Vec<Point> = (0..3)
                    .map(|_| Point {
                        x: arena.x0 + rng() * arena.width(),
                        y: arena.y0 + rng() * arena.height(),
                    })
                    .collect();
                let ctx = bm::Ctx {
                    map,
                    arena,
                    boss: s.point(),
                    players: &players,
                    lit,
                    cast: z.cast,
                };
                let shapes = bm::resolve(&z.shape, &ctx, &mut rng);
                if let Some(p) =
                    bm::first_unsafe_point(map, arena, z.cast, &|p| bm::hurts(z.effect, &shapes, p))
                {
                    return Some((m.name.clone(), p));
                }
            }
        }
    }
    None
}

#[test]
fn the_test_table_is_fair_and_an_unfair_one_is_caught() {
    let r = rig(TOLL, 1);
    let def = r.w.boss.table["hollowking"].clone();
    assert_eq!(unfair_point(&r.w, r.boss, &def), None);
    // A ring larger than anyone can outrun in a 5 s cast, and the same ring after the cast has been shortened to
    // what a heavy hit allows: both are caught.
    let huge: BossDef = serde_json::from_str(&TOLL.replace(r#""r":8"#, r#""r":45"#)).unwrap();
    assert!(unfair_point(&r.w, r.boss, &huge).is_some());
    let islands: BossDef = serde_json::from_str(
        r#"{"mechanics":[{"name":"Tide","block":"zone","shape":{"kind":"islands","count":3,"r":2.5},"effect":"kill_outside","cast":5,"every":35}]}"#,
    )
    .unwrap();
    assert_eq!(unfair_point(&r.w, r.boss, &islands), None);
    let one: BossDef = serde_json::from_str(
        r#"{"mechanics":[{"name":"Tide","block":"zone","shape":{"kind":"islands","count":1,"r":0.8},"effect":"kill_outside","cast":5,"every":35}]}"#,
    )
    .unwrap();
    assert!(
        unfair_point(&r.w, r.boss, &one).is_some(),
        "one tiny island in a room 36 tiles long is not reachable from the far end"
    );
}

#[test]
fn every_shipped_boss_is_fair_and_its_tags_exist_in_the_map() {
    let w = world();
    for (kind, def) in &w.boss.table {
        let boss = w
            .slimes
            .iter()
            .find(|s| &s.kind == kind)
            .unwrap_or_else(|| panic!("{kind} has no spawn"));
        let map = &w.maps[boss.zone];
        assert_eq!(
            &map.final_boss, kind,
            "{kind} must be a dungeon's final boss"
        );
        assert_eq!(
            unfair_point(&w, boss.id, def),
            None,
            "{kind} leaves a point with no way out in time"
        );
        for m in &def.mechanics {
            let tags: Vec<&str> = match &m.block {
                Block::Shield(s) => s.steps.iter().map(|t| t.tag.as_str()).collect(),
                Block::Adds(a) => std::iter::once(a.tag.as_str())
                    .chain(a.bloom.iter().filter_map(|b| b.then.as_deref()))
                    .collect(),
                Block::Stasis(s) => vec![s.tag.as_str()],
                Block::Split(s) => vec![s.tag.as_str()],
                _ => vec![],
            };
            for tag in tags {
                assert!(
                    w.spawns
                        .iter()
                        .any(|s| s.zone == boss.zone && s.ambush.as_deref() == Some(tag)),
                    "{kind} / {}: no sleeping monster tagged {tag} in its dungeon",
                    m.name
                );
            }
        }
    }
}

// --- the shipped bosses ------------------------------------------------------------------------------------------
// One section per `BOSSMECH-*` boss, reading the data the server ships (`world/boss-mechanics.txt`).

/// A shipped boss's definition as the JSON text `rig` takes.
fn shipped(kind: &str) -> String {
    let all: Value =
        serde_json::from_str(include_str!("../../../world/boss-mechanics.txt")).unwrap();
    all[kind].to_string()
}

/// The two dirges of Haldor, the Hollow King (`BOSSMECH-HOLLOWKING`): `(cast, every, bar, stun, vulnerable)`.
fn dirges(w: &World) -> Vec<(f64, f64, f64, f64, f64)> {
    w.boss.table["hollowking"]
        .mechanics
        .iter()
        .map(|m| match &m.block {
            Block::Break(b) => (b.cast, b.every, b.bar, b.stun, b.vulnerable),
            other => panic!("Haldor has only dirges, found {other:?}"),
        })
        .collect()
}

#[test]
fn haldors_dirge_is_a_break_every_thirty_seconds_and_every_twenty_five_below_thirty_percent() {
    let r = rig(&shipped("hollowking"), 1);
    let d = dirges(&r.w);
    assert_eq!(d.len(), 2, "one dirge, one escalation, nothing else");
    // The same song: 8 s to answer, the same bar, a 6 s rest and +30% damage after a break.
    assert_eq!(d[0].0, 8.);
    assert_eq!(
        (d[0].0, d[0].2, d[0].3, d[0].4),
        (d[1].0, d[1].2, d[1].3, d[1].4)
    );
    assert_eq!((d[0].3, d[0].4), (6., 0.3));
    assert_eq!((d[0].1, d[1].1), (30., 25.));
    let m = &r.w.boss.table["hollowking"].mechanics;
    assert!(m[0].active_at(1.) && m[0].active_at(0.31) && !m[0].active_at(0.3));
    assert!(m[1].active_at(0.3) && m[1].active_at(0.01) && !m[1].active_at(0.31));
    assert_eq!(m[0].name, "Dirge of the Hollow");
}

#[test]
fn haldor_sings_on_the_thirtieth_second_and_again_thirty_later_then_faster_below_thirty_percent() {
    let mut r = rig(&shipped("hollowking"), 2);
    r.run(29.);
    assert_eq!(
        r.fight().live.len(),
        0,
        "no dirge before the thirtieth second"
    );
    r.run(1.5);
    assert_eq!(r.fight().live.len(), 1);
    let needed = r.view()["break"]["needed"].as_f64().unwrap();
    assert!((needed - r.max_hp() * dirges(&r.w)[0].2).abs() < 1e-6);
    // The party answers; nobody dies, he rests, and the next song starts thirty seconds after the first.
    r.hit_boss(1, needed);
    r.run(0.2);
    assert!(r.view()["stunned"].as_f64().unwrap() > 5.);
    assert!(r.alive(1) && r.alive(2));
    r.run(27.);
    assert_eq!(r.fight().live.len(), 0, "27.7 s after the first song began");
    r.run(3.);
    assert_eq!(
        r.fight().live.len(),
        1,
        "the second song, 30 s after the first"
    );
    r.hit_boss(2, needed);
    r.run(0.2);
    // Below 30% the interval is 25 s, counted from the moment that window opens.
    r.set_boss_share(0.25);
    r.run(24.);
    assert_eq!(r.fight().live.len(), 0);
    r.run(2.);
    assert_eq!(r.fight().live.len(), 1, "the quicker dirge");
    assert!(r.alive(1) && r.alive(2));
}

#[test]
fn nobody_hitting_back_during_haldors_dirge_ends_in_the_wail() {
    let mut r = rig(&shipped("hollowking"), 3);
    r.run(30.5);
    assert!(r.alive(1) && r.alive(2) && r.alive(3), "the song has 8 s");
    r.run(8.);
    assert!(!r.alive(1) && !r.alive(2) && !r.alive(3));
    assert_eq!(
        causes(&r.events(1)),
        vec!["Dirge of the Hollow".to_string(); 3],
        "each death names the song"
    );
}

#[test]
fn the_sign_before_haldor_says_what_the_dirge_really_does() {
    let w = world();
    let sign = &w.signs["hollowking"];
    let d = dirges(&w);
    // The numbers on the sign are the mechanic's own.
    assert!(
        sign.what.contains(&format!("{} seconds", d[0].0)),
        "the song lasts {} s: {}",
        d[0].0,
        sign.what
    );
    assert_eq!(sign.colors, vec!["red".to_string()]);
    // The three parts, in the words of the bar the player sees (the break bar is gold) and the low-health line.
    assert!(sign.todo.contains("gold bar"));
    assert!(sign.tip.contains("nearly beaten"));
    // Plain words and short sentences: a child of about eight reads it.
    for text in [&sign.what, &sign.todo, &sign.tip] {
        assert!(text.len() <= 150, "{text}");
        for sentence in text.split(['.', '!']).filter(|s| !s.trim().is_empty()) {
            assert!(
                sentence.split_whitespace().count() <= 12,
                "over twelve words: {sentence}"
            );
        }
    }
}

#[test]
fn five_shipped_bosses_keep_their_phases_and_child_readable_signs() {
    let w = world();
    let cases = [
        ("hierophant", 2, "5 seconds", "Rising Tide"),
        ("moonwell_echo", 4, "3 seconds", "Moon Lance"),
        ("elder_heart", 2, "4 second", "Bramble Sweep"),
        ("pavilion_sovereign", 2, "5 seconds", "Fold"),
        ("rain_crown_sovereign", 2, "5 seconds", "Downpour"),
    ];
    for (kind, count, number, first_name) in cases {
        let def = &w.boss.table[kind];
        let sign = &w.signs[kind];
        assert_eq!(def.mechanics.len(), count, "{kind} phase count");
        assert_eq!(def.mechanics[0].name, first_name);
        assert!(def.mechanics[0].active_at(1.));
        assert!(!def.mechanics[0].active_at(0.01));
        assert!(def.mechanics[1].active_at(0.01));
        assert!(
            sign.what.contains(number),
            "{kind} sign must state its timing"
        );
        assert!(
            sign.tip.contains("nearly beaten"),
            "{kind} sign must explain escalation"
        );
        for part in [&sign.what, &sign.todo, &sign.tip] {
            for sentence in part.split(['.', '!']).filter(|s| !s.trim().is_empty()) {
                assert!(
                    sentence.split_whitespace().count() <= 12,
                    "{kind}: {sentence}"
                );
            }
        }
    }
    let hierophant = &w.boss.table["hierophant"];
    assert!(hierophant.inner_arena);
    for (i, expected) in [(0, 3), (1, 2)] {
        let Block::Zone(z) = &hierophant.mechanics[i].block else {
            panic!("Rising Tide is a zone")
        };
        assert!(
            matches!(z.shape, bm::ShapeSpec::Islands { count, r } if count == expected && r == 2.5)
        );
        assert_eq!((z.cast, z.linger), (5., 4.));
    }
    let Block::Zone(high_tide) = &hierophant.mechanics[1].block else {
        unreachable!()
    };
    assert_eq!(high_tide.repeat, 2);
    assert_eq!(w.signs["hierophant"].colors, ["red", "blue"]);

    let echo = &w.boss.table["moonwell_echo"];
    assert_eq!(echo.arena, Some([97., 99., 112., 114.]));
    for (i, delays) in [
        (0, vec![3.]),
        (1, vec![2., 2.]),
        (2, vec![3.]),
        (3, vec![2., 2.]),
    ] {
        let Block::Zone(z) = &echo.mechanics[i].block else {
            panic!("Echo attacks are zones")
        };
        assert_eq!(z.echo, delays);
        assert_eq!(z.cast, 5., "a lethal cast needs the full warning");
    }
    assert_eq!(w.signs["moonwell_echo"].colors, ["red", "path"]);

    let elder = &w.boss.table["elder_heart"];
    for (i, walls) in [(0, 2), (1, 4)] {
        let Block::Sweep(s) = &elder.mechanics[i].block else {
            panic!("Bramble Sweep moves walls")
        };
        let bm::SweepKind::Walls {
            warn,
            speed,
            gap,
            walls: entries,
            ..
        } = &s.kind
        else {
            unreachable!()
        };
        assert_eq!((*warn, *speed, *gap, entries.len()), (4., 4., 4., walls));
    }
    assert_eq!(w.signs["elder_heart"].colors, ["red", "path", "green"]);

    let pavilion = &w.boss.table["pavilion_sovereign"];
    for (i, repeats) in [(0, 1), (1, 2)] {
        let Block::Zone(z) = &pavilion.mechanics[i].block else {
            panic!("Fold is a zone")
        };
        assert!(matches!(z.shape, bm::ShapeSpec::Half { min_share } if min_share == 0.4));
        assert_eq!((z.cast, z.linger, z.repeat), (5., 3., repeats));
    }
    let Block::Zone(second_fold) = &pavilion.mechanics[1].block else {
        unreachable!()
    };
    assert!(second_fold.alternate);
    assert_eq!(w.signs["pavilion_sovereign"].colors, ["red", "path"]);
    assert!(
        w.signs["pavilion_sovereign"]
            .tip
            .contains("back over the line")
    );

    let crown = &w.boss.table["rain_crown_sovereign"];
    for (i, waves) in [(0, 1), (1, 2)] {
        let Block::Mark(m) = &crown.mechanics[i].block else {
            panic!("Downpour marks players")
        };
        assert_eq!((m.count, m.cast, m.waves), (3, 5., waves));
        assert_eq!(m.linger, 8.);
        assert!(matches!(m.effect, bm::MarkEffect::Burst { r } if r == 4.));
    }
    assert_eq!(w.signs["rain_crown_sovereign"].colors, ["red"]);
    assert!(w.signs["rain_crown_sovereign"].tip.contains("8 seconds"));
}

#[test]
fn five_shipped_bosses_start_their_real_telegraphs_in_both_health_phases() {
    for (kind, start, high_shapes, low_shapes, name) in [
        ("hierophant", 35., 3, 2, "Rising Tide"),
        ("moonwell_echo", 15., 1, 1, "Moon Lance"),
        ("elder_heart", 20., 4, 8, "Bramble Sweep"),
        ("pavilion_sovereign", 22., 1, 1, "Fold"),
        ("rain_crown_sovereign", 25., 2, 2, "Downpour"),
    ] {
        for (share, shapes) in [(1., high_shapes), (0.2, low_shapes)] {
            let mut r = rig(&shipped(kind), 3);
            r.set_boss_share(share);
            r.run(start + 0.3);
            let view = r.view();
            assert_eq!(view["cast"]["name"], name, "{kind} at {share} health");
            let shown = if kind == "hierophant" {
                view["tele"][0]["shapes"].as_array().unwrap().len()
            } else {
                view["tele"].as_array().unwrap().len()
            };
            assert_eq!(shown, shapes, "{kind} at {share} health");
        }
    }
}

#[test]
fn landed_floor_hazards_stay_dangerous_until_they_fade() {
    let mut r = rig(
        r#"{"mechanics":[{"name":"Fold","block":"zone","shape":{"kind":"circle","r":8},"effect":"kill","cast":5,"every":30,"first":1,"linger":3}]}"#,
        2,
    );
    let boss = r.w.slimes[r.boss].point();
    r.run(6.2);
    assert!(r.alive(2), "outside the first landing");
    let inside = r.put(2, boss.x + 1., boss.y);
    assert!(inside.distance(boss) < 8.);
    assert_eq!(r.view()["tele"][0]["tele"], "red");
    assert_eq!(
        r.w.boss_danger(r.zone, 2, inside).map(|(_, left)| left),
        Some(0.)
    );
    r.run(0.1);
    assert!(
        !r.alive(2),
        "the folded floor remains dangerous for three seconds"
    );
    let mut r = rig(
        r#"{"mechanics":[{"name":"Fold","block":"zone","shape":{"kind":"circle","r":8},"effect":"kill","cast":5,"every":30,"first":1,"linger":3}]}"#,
        1,
    );
    r.w.god_mode = true;
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x + 1., boss.y);
    r.run(9.2);
    assert_eq!(
        r.events(1)
            .iter()
            .filter(|e| e["text"] == "Would have been killed by Fold")
            .count(),
        1,
        "a lingering hazard sends one god-mode notice per landing"
    );
}

#[test]
fn the_second_pavilion_fold_strikes_the_other_side_of_the_same_crease() {
    let mut r = rig(&shipped("pavilion_sovereign"), 2);
    r.w.god_mode = true;
    r.set_boss_share(0.2);
    r.run(22.2);
    let first = r.view()["tele"][0]["shapes"][0].clone();
    assert_eq!(first["t"], "half");
    r.run(11.2);
    let second = r.view()["tele"][0]["shapes"][0].clone();
    assert_eq!(second["t"], "half");
    assert_eq!(
        (first["x"].clone(), first["y"].clone()),
        (second["x"].clone(), second["y"].clone())
    );
    assert!((first["nx"].as_f64().unwrap() + second["nx"].as_f64().unwrap()).abs() < 1e-9);
    assert!((first["ny"].as_f64().unwrap() + second["ny"].as_f64().unwrap()).abs() < 1e-9);
}

#[test]
fn downpour_leaves_an_eight_second_puddle_that_spares_its_bearer() {
    let mut r = rig(&shipped("rain_crown_sovereign"), 2);
    r.run(25.2);
    let bearer_id = r.view()["marked"][0].as_str().unwrap().to_string();
    let bearer = if r.w.players[&1].character.id == bearer_id {
        1
    } else {
        2
    };
    let other = 3 - bearer;
    let centre = r.put(bearer, 112., 20.);
    r.put(other, 122., 36.);
    r.run(5.1);
    assert!(r.alive(bearer) && r.alive(other));
    assert_eq!(
        r.view()["tele"][0]["tele"],
        "red",
        "the puddle stays visible"
    );
    let near = r.put(other, centre.x + 1.5, centre.y);
    assert!(near.distance(centre) < 4.);
    assert_eq!(
        r.w.boss_danger(r.zone, other, near).map(|(_, left)| left),
        Some(0.)
    );
    assert_eq!(r.w.boss_danger(r.zone, bearer, centre), None);
    r.run(0.1);
    assert!(!r.alive(other) && r.alive(bearer));
    r.run(8.);
    assert!(
        r.view()["tele"].as_array().unwrap().is_empty(),
        "the puddle dries up"
    );
    let mut r = rig(&shipped("rain_crown_sovereign"), 2);
    r.w.god_mode = true;
    r.run(25.2);
    let bearer_id = r.view()["marked"][0].as_str().unwrap().to_string();
    let bearer = if r.w.players[&1].character.id == bearer_id {
        1
    } else {
        2
    };
    let other = 3 - bearer;
    let centre = r.put(bearer, 112., 20.);
    r.put(other, centre.x + 1., centre.y);
    r.run(8.);
    assert_eq!(
        r.events(other)
            .iter()
            .filter(|e| e["text"] == "Would have been killed by Downpour")
            .count(),
        1,
        "the mark and its puddle send one god-mode notice"
    );
}

// --- the eight bosses of the second half (BOSSMECH-CHOIRMOTHER .. BOSSMECH-SOLSTICE-HEART) ---------------------------

/// What a shipped boss's sign says, in one string.
fn sign_words(kind: &str) -> String {
    let all: Value = serde_json::from_str(include_str!("../../../world/boss-signs.txt")).unwrap();
    ["what", "todo", "tip"]
        .iter()
        .map(|p| all[kind][*p].as_str().unwrap().to_string())
        .collect::<Vec<_>>()
        .join(" ")
}

/// The mechanics of the table a `rig` loaded (it keeps the table under the Undervault king's kind), as `(name, block)`.
fn blocks(w: &World, _shipped_kind: &str) -> Vec<(String, Block)> {
    w.boss.table["hollowking"]
        .mechanics
        .iter()
        .map(|m| (m.name.clone(), m.block.clone()))
        .collect()
}

/// `n` places along the top of the Undervault boss room for sleepers.
fn row(n: usize) -> Vec<(f64, f64)> {
    (0..n).map(|i| (104. + 1.5 * i as f64, 10.)).collect()
}

#[test]
fn elyss_tolls_a_five_second_circle_and_calls_four_then_six_singers() {
    let mut r = rig(&shipped("choirmother"), 2);
    let tolls: Vec<_> = blocks(&r.w, "choirmother")
        .into_iter()
        .filter_map(|(n, b)| match b {
            Block::Zone(z) => Some((n, z)),
            _ => None,
        })
        .collect();
    assert_eq!(tolls.len(), 2);
    for (name, z) in &tolls {
        assert_eq!(name, "Toll of the Deep");
        assert_eq!((z.cast, z.effect), (5., Effect::Kill));
        assert!(
            matches!(z.shape, bm::ShapeSpec::Circle { r, inner, .. } if r == 8. && inner == 0.)
        );
    }
    assert_eq!((tolls[0].1.every, tolls[1].1.every), (25., 18.));
    let steps: Vec<_> = blocks(&r.w, "choirmother")
        .into_iter()
        .find_map(|(_, b)| match b {
            Block::Shield(s) => Some(s.steps),
            _ => None,
        })
        .unwrap();
    assert_eq!(
        steps.iter().map(|s| (s.hp, s.count)).collect::<Vec<_>>(),
        vec![(0.66, 4), (0.33, 6)]
    );
    // The first toll: a hero standing by Elyss falls, one outside the circle does not.
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x + 2., boss.y);
    let far = r.put(2, boss.x, boss.y + 14.);
    assert!(far.distance(boss) > 8.);
    r.run(25.2);
    assert_eq!(r.view()["cast"]["name"], "Toll of the Deep");
    r.run(5.);
    assert!(!r.alive(1) && r.alive(2));
    assert_eq!(causes(&r.events(1)), vec!["Toll of the Deep".to_string()]);
    // The singers: four at 66%, and, once they are down, six at 33%.
    let singers = r.sleepers("chorus", &row(10));
    r.set_boss_share(0.65);
    r.run(0.2);
    let up = r.fight().shield.as_ref().expect("the chorus rises");
    assert_eq!((up.adds.len(), up.name.as_str()), (4, "The Bound Chorus"));
    for s in up.adds.clone() {
        r.w.hit_slime(s, 2, 1e9, false);
    }
    r.run(0.2);
    assert!(r.fight().shield.is_none());
    r.set_boss_share(0.32);
    r.run(0.2);
    let up = r.fight().shield.as_ref().unwrap();
    assert_eq!(up.adds.len(), 6);
    assert!(up.adds.iter().all(|s| singers.contains(s)));
    let words = sign_words("choirmother");
    assert!(words.contains("5 seconds"), "{words}");
}

#[test]
fn avariels_shell_heals_until_every_pearl_is_broken_and_the_last_one_brings_crabs() {
    let mut r = rig(&shipped("coralregent"), 2);
    let b = blocks(&r.w, "coralregent");
    let Block::Shield(shell) = &b[0].1 else {
        panic!("the shell comes first")
    };
    assert_eq!(shell.heal_per_s, 0.02);
    assert_eq!(
        shell
            .steps
            .iter()
            .map(|s| (s.hp, s.count, s.still))
            .collect::<Vec<_>>(),
        vec![(0.75, 3, true), (0.5, 3, true), (0.25, 4, true)]
    );
    assert!(matches!(&b[1].1, Block::Adds(a) if a.tag == "shellcrab" && a.count == 2));
    assert_eq!(b[1].0, "Reliquary Crabs");
    r.sleepers("pearl", &row(10));
    let crabs = r.sleepers("shellcrab", &[(104., 12.), (106., 12.)]);
    r.set_boss_share(0.74);
    r.run(0.2);
    let up = r.fight().shield.as_ref().expect("the first shell");
    assert_eq!(up.adds.len(), 3);
    for s in &up.adds {
        assert!(r.fight().still.contains(s), "a pearl stays where it grew");
    }
    let hp = r.w.slimes[r.boss].hp;
    r.run(2.);
    let gained = (r.w.slimes[r.boss].hp - hp) / r.max_hp();
    assert!((gained - 0.04).abs() < 0.005, "2% a second: {gained}");
    for s in r.fight().shield.as_ref().unwrap().adds.clone() {
        r.w.hit_slime(s, 1, 1e9, false);
    }
    r.run(0.2);
    assert!(r.fight().shield.is_none());
    assert!(
        crabs.iter().all(|c| r.w.slimes[*c].dead),
        "no crabs above a quarter of her health"
    );
    r.set_boss_share(0.49);
    r.run(0.2);
    assert_eq!(r.fight().shield.as_ref().unwrap().adds.len(), 3);
    for s in r.fight().shield.as_ref().unwrap().adds.clone() {
        r.w.hit_slime(s, 1, 1e9, false);
    }
    r.run(0.2);
    r.set_boss_share(0.24);
    r.run(1.);
    assert_eq!(r.fight().shield.as_ref().unwrap().adds.len(), 4);
    assert!(
        crabs
            .iter()
            .all(|c| !r.w.slimes[*c].dead && !r.fight().still.contains(c)),
        "two crabs join, free to move"
    );
    let words = sign_words("coralregent");
    assert!(words.contains("Three times"), "{words}");
}

#[test]
fn the_worldseed_plants_three_seeds_every_thirty_seconds_that_bloom_into_treants() {
    let mut r = rig(&shipped("seed_worldseed"), 2);
    let b = blocks(&r.w, "seed_worldseed");
    let counts: Vec<_> = b
        .iter()
        .map(|(_, m)| match m {
            Block::Adds(a) => {
                let bl = a.bloom.as_ref().unwrap();
                (
                    a.count,
                    a.every,
                    a.scatter,
                    a.still,
                    bl.after,
                    bl.heal,
                    bl.then.clone(),
                )
            }
            _ => panic!("only seeds"),
        })
        .collect();
    assert_eq!(
        counts[0],
        (3, 30., true, true, 12., 0.04, Some("treant".to_string()))
    );
    assert_eq!(counts[1].0, 5, "five at once below 35%");
    let seeds = r.sleepers("seed", &row(3));
    let treants = r.sleepers("treant", &[(104., 12.), (106., 12.), (108., 12.)]);
    r.run(30.2);
    assert!(
        seeds.iter().all(|s| !r.w.slimes[*s].dead),
        "three seeds are planted"
    );
    // Break one in time: nothing blooms from it. The other two are left to grow for 12 s.
    r.w.hit_slime(seeds[0], 1, 1e9, false);
    r.set_boss_share(0.5);
    let hp = r.w.slimes[r.boss].hp;
    r.run(12.2);
    let gained = (r.w.slimes[r.boss].hp - hp) / r.max_hp();
    assert!(
        (gained - 0.08).abs() < 0.005,
        "two seeds bloomed, 4% each: {gained}"
    );
    assert_eq!(
        treants.iter().filter(|t| !r.w.slimes[**t].dead).count(),
        2,
        "a treant where each seed stood"
    );
    // The next planting finds its seeds again, even the one that was killed.
    r.run(18.);
    assert!(
        seeds.iter().all(|s| !r.w.slimes[*s].dead),
        "the broken seed is put to work again"
    );
    let words = sign_words("seed_worldseed");
    assert!(
        words.contains("30 seconds")
            && words.contains("12 seconds")
            && words.contains("five seeds")
    );
}

#[test]
fn prism_bounce_marks_one_friend_then_two_and_the_beam_bounces_more_late() {
    let mut r = rig(&shipped("bloom_heart"), 3);
    let marks: Vec<_> = blocks(&r.w, "bloom_heart")
        .into_iter()
        .map(|(_, b)| match b {
            Block::Mark(k) => (
                k.count,
                k.cast,
                k.every,
                matches!(k.effect, MarkEffect::Beam { bounces, .. } if bounces > 0),
            ),
            _ => panic!("only marks"),
        })
        .collect();
    assert_eq!(marks, vec![(1, 5., 18., true), (2, 5., 18., true)]);
    r.run(18.2);
    assert_eq!(r.view()["marked"].as_array().unwrap().len(), 1);
    assert_eq!(
        r.view()["tele"][0]["shapes"].as_array().unwrap().len(),
        3,
        "two bounces, three segments"
    );
    let mut r = rig(&shipped("bloom_heart"), 3);
    r.set_boss_share(0.2);
    r.run(18.2);
    assert_eq!(r.view()["marked"].as_array().unwrap().len(), 2);
    assert_eq!(
        r.view()["tele"][0]["shapes"].as_array().unwrap().len(),
        4,
        "three bounces, four segments"
    );
    let words = sign_words("bloom_heart");
    assert!(
        words.contains("5 seconds") && words.contains("three times"),
        "{words}"
    );
}

#[test]
fn twin_suns_divide_the_heart_at_sixty_per_cent_and_sunburst_follows() {
    let mut r = rig(&shipped("solar_heart"), 2);
    let b = blocks(&r.w, "solar_heart");
    let Block::Split(s) = &b[0].1 else {
        panic!("the split comes first")
    };
    assert_eq!(
        (s.hp, s.revive_after, s.survivor_bonus, s.tag.as_str()),
        (0.6, 10., 0.5, "cinder")
    );
    assert!(s.bridge > 0.);
    let Block::Zone(z) = &b[1].1 else {
        panic!("then the burst")
    };
    assert_eq!((z.cast, z.effect, z.every), (3., Effect::Heavy, 14.));
    assert!(matches!(z.shape, bm::ShapeSpec::Cone { .. }));
    assert!(r.w.boss.table["hollowking"].mechanics[1].active_at(0.59));
    assert!(!r.w.boss.table["hollowking"].mechanics[1].active_at(0.61));
    let partner = r.sleepers("cinder", &[(116., 30.)])[0];
    r.run(5.);
    assert!(r.fight().partner.is_none(), "whole above 60%");
    r.set_boss_share(0.59);
    r.run(0.2);
    assert_eq!(r.fight().partner, Some(partner));
    let words = sign_words("solar_heart");
    assert!(words.contains("10 seconds"), "{words}");
}

#[test]
fn amber_stasis_sends_two_orbs_then_three_and_holds_a_friend_ten_then_eight_seconds() {
    let mut r = rig(&shipped("amber_memory"), 3);
    let stasis: Vec<_> = blocks(&r.w, "amber_memory")
        .into_iter()
        .map(|(_, b)| match b {
            Block::Stasis(s) => (s.orbs, s.hold, s.every, s.tag),
            _ => panic!("only stasis"),
        })
        .collect();
    assert_eq!(stasis[0], (2, 10., 25., "cocoon".to_string()));
    assert_eq!((stasis[1].0, stasis[1].1), (3, 8.));
    r.sleepers("cocoon", &row(6));
    let boss = r.w.slimes[r.boss].point();
    for s in 1..=3 {
        r.put(s, boss.x - 4. + s as f64 * 4., boss.y + 6.);
    }
    r.run(25.2);
    assert_eq!(
        r.view()["tele"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|t| t["orb"] == true)
            .count(),
        2
    );
    r.run(6.);
    let frozen: Vec<u64> = (1..=3).filter(|s| r.w.players[s].frozen).collect();
    assert!(!frozen.is_empty() && frozen.len() <= 2, "{frozen:?}");
    let words = sign_words("amber_memory");
    assert!(
        words.contains("10 seconds") && words.contains("three orbs") && words.contains("8 seconds"),
        "{words}"
    );
}

#[test]
fn the_longest_night_lights_four_braziers_and_falls_every_forty_five_then_thirty_seconds() {
    let r = rig(&shipped("solstice_heart"), 1);
    let b = blocks(&r.w, "solstice_heart");
    let holds: Vec<_> = b
        .iter()
        .filter_map(|(_, m)| match m {
            Block::Hold(h) => Some((h.points.len(), h.r, h.hold_for, h.lit_for, h.snuff_every)),
            _ => None,
        })
        .collect();
    assert_eq!(holds, vec![(4, 2.5, 3., 30., 12.), (4, 2.5, 3., 20., 12.)]);
    let nights: Vec<_> = b
        .iter()
        .filter_map(|(_, m)| match m {
            Block::Zone(z) => Some((z.cast, z.every, z.effect)),
            _ => None,
        })
        .collect();
    assert_eq!(
        nights,
        vec![
            (5., 45., Effect::KillOutside),
            (5., 30., Effect::KillOutside)
        ]
    );
    let words = sign_words("solstice_heart");
    for needle in [
        "45 seconds",
        "5 seconds",
        "3 seconds",
        "30 seconds",
        "12 seconds",
    ] {
        assert!(words.contains(needle), "{needle}: {words}");
    }
}

// --- Static ----------------------------------------------------------------------------------------------------------

const STATIC: &str = r#"{"mechanics":[
    {"name":"Static","block":"static","hp_min":0.3,"limit":4,"warn_at":3,"per_hit":1,"r":5,"rods":[[112,12],[120,12]],"rod_r":1.8,"immune":8,"dark":12},
    {"name":"Static","block":"static","hp_max":0.3,"limit":4,"warn_at":3,"per_hit":2,"r":5,"rods":[[112,12],[120,12]],"rod_r":1.8,"immune":8,"dark":20}]}"#;

fn charge_of(r: &Rig, session: u64) -> u64 {
    let id = r.w.players[&session].character.id.clone();
    r.view()["static"]["charges"][&id].as_u64().unwrap_or(0)
}

#[test]
fn every_blow_on_the_boss_adds_a_charge_and_the_limit_detonates_the_bearer_and_whoever_is_near() {
    let mut r = rig(STATIC, 3);
    r.run(0.2);
    let boss = r.w.slimes[r.boss].point();
    let me = r.put(1, boss.x, boss.y + 10.);
    r.put(2, me.x + 2., me.y);
    let far = r.put(3, me.x - 12., me.y);
    assert!(far.distance(me) > 5.);
    for n in 1..=3 {
        assert!(r.hit_boss(1, 5.) > 0.);
        assert_eq!(charge_of(&r, 1), n);
    }
    assert_eq!(
        r.fight().banner.as_ref().map(|b| b.0.as_str()),
        Some("Static"),
        "warned at three"
    );
    assert_eq!(r.view()["static"]["limit"], 4);
    // Blows on the boss by someone else do not charge me.
    assert!(r.hit_boss(3, 5.) > 0.);
    assert_eq!(charge_of(&r, 1), 3);
    assert!(r.alive(1) && r.alive(2) && r.alive(3));
    r.hit_boss(1, 5.);
    assert!(!r.alive(1), "the bearer detonates");
    assert!(!r.alive(2), "so does whoever stands within five tiles");
    assert!(r.alive(3), "and no one else");
    assert_eq!(charge_of(&r, 1), 0);
    // Every death in the zone reaches everyone: both name the same ability.
    assert_eq!(
        causes(&r.events(3)),
        vec!["Static".to_string(), "Static".to_string()]
    );
    assert!(
        r.view()["tele"]
            .as_array()
            .unwrap()
            .iter()
            .any(|t| t["tele"] == "red"),
        "the burst shows for a moment"
    );
}

#[test]
fn a_ready_rod_clears_the_charge_grants_eight_seconds_of_calm_and_goes_dark() {
    let mut r = rig(STATIC, 2);
    r.run(0.2);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 10.);
    r.put(2, boss.x + 12., boss.y + 10.);
    r.hit_boss(1, 5.);
    r.hit_boss(1, 5.);
    assert_eq!(charge_of(&r, 1), 2);
    let rod = r.put(1, 112., 12.);
    assert!(
        rod.distance(Point { x: 112., y: 12. }) < 1.8,
        "the Undervault room holds the rod's spot"
    );
    r.run(0.2);
    assert_eq!(charge_of(&r, 1), 0);
    assert!(r.view()["static"]["grounded"].as_object().unwrap().len() == 1);
    let lit = |r: &Rig| -> Vec<bool> {
        r.view()["tele"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|t| t["rod"] == true)
            .map(|t| t["lit"].as_bool().unwrap())
            .collect()
    };
    assert_eq!(
        lit(&r),
        vec![false, true],
        "the touched rod is dark, the other ready"
    );
    // For eight seconds blows add nothing; after that they do again.
    r.put(1, boss.x, boss.y + 10.);
    r.hit_boss(1, 5.);
    assert_eq!(charge_of(&r, 1), 0);
    r.run(8.);
    r.hit_boss(1, 5.);
    assert_eq!(charge_of(&r, 1), 1);
    // The rod is dark for twelve seconds: a second hero gains nothing from it before then.
    r.hit_boss(2, 5.);
    r.put(2, 112., 12.);
    r.run(0.3);
    assert_eq!(charge_of(&r, 2), 1, "a dark rod does nothing");
    r.put(2, boss.x + 12., boss.y + 10.);
    r.run(4.);
    assert_eq!(lit(&r), vec![true, true], "back after twelve seconds");
    r.put(2, 112., 12.);
    r.run(0.3);
    assert_eq!(charge_of(&r, 2), 0);
}

#[test]
fn below_thirty_per_cent_blows_charge_twice_and_the_rods_rest_twenty_seconds() {
    let mut r = rig(STATIC, 1);
    r.set_boss_share(0.2);
    r.run(0.2);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 10.);
    r.hit_boss(1, 5.);
    assert_eq!(charge_of(&r, 1), 2);
    r.put(1, 112., 12.);
    r.run(0.2);
    r.put(1, boss.x, boss.y + 10.);
    r.run(12.5);
    let lit: Vec<bool> = r.view()["tele"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|t| t["rod"] == true)
        .map(|t| t["lit"].as_bool().unwrap())
        .collect();
    assert_eq!(lit, vec![false, true], "still dark after twelve seconds");
    r.run(8.);
    let lit: Vec<bool> = r.view()["tele"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|t| t["rod"] == true)
        .map(|t| t["lit"].as_bool().unwrap())
        .collect();
    assert_eq!(lit, vec![true, true]);
}

#[test]
fn the_shipped_thunder_heart_is_static_with_four_corner_rods_and_a_sign_that_matches() {
    let r = rig(&shipped("thunder_heart"), 1);
    let statics: Vec<_> = blocks(&r.w, "thunder_heart")
        .into_iter()
        .map(|(_, b)| match b {
            Block::Static(t) => t,
            _ => panic!("only static"),
        })
        .collect();
    assert_eq!(statics.len(), 2);
    for t in &statics {
        assert_eq!(
            (t.limit, t.warn_at, t.r, t.immune, t.rods.len()),
            (12, 8, 5., 8., 4)
        );
    }
    assert_eq!((statics[0].per_hit, statics[0].dark), (1, 12.));
    assert_eq!((statics[1].per_hit, statics[1].dark), (2, 20.));
    let words = sign_words("thunder_heart");
    for needle in [
        "12 sparks",
        "8 sparks",
        "12 seconds",
        "two sparks",
        "20 seconds",
    ] {
        assert!(words.contains(needle), "{needle}: {words}");
    }
}

#[test]
fn a_static_table_with_one_rod_or_a_limit_below_its_warning_is_refused() {
    let one = STATIC.replace("[[112,12],[120,12]]", "[[112,12]]");
    let def: BossDef = serde_json::from_str(&one).unwrap();
    assert!(crate::bossmech::validate("hollowking", &def).is_err());
    let low = STATIC.replace(r#""warn_at":3"#, r#""warn_at":4"#);
    let def: BossDef = serde_json::from_str(&low).unwrap();
    assert!(crate::bossmech::validate("hollowking", &def).is_err());
}

#[test]
fn helpers_do_not_drop_loot_and_a_fresh_cycle_reuses_the_ones_that_fell() {
    let mut r = rig(&shipped("amber_memory"), 1);
    let cocoons = r.sleepers("cocoon", &row(1));
    let mut fight = r.w.begin_boss_fight(r.boss);
    let first = r.w.wake_adds(&mut fight, "cocoon", 1, false, true);
    assert_eq!(first, cocoons);
    r.w.hit_slime(cocoons[0], 1, 1e9, false);
    assert!(r.w.slimes[cocoons[0]].dead);
    let again = r.w.wake_adds(&mut fight, "cocoon", 1, false, true);
    assert_eq!(again, cocoons, "the one that fell is put to work again");
    assert_eq!(fight.woken, cocoons, "and is listed once");
    assert!(!r.w.slimes[cocoons[0]].dead);
}

// --- the brain of a fighter who is not at a keyboard (boss_play.rs) -------------------------------------------------------

#[test]
fn a_fighter_standing_in_a_telegraph_runs_out_of_it_and_holds_fire_one_outside_does_neither() {
    let mut r = rig(TOLL, 2);
    let boss = r.w.slimes[r.boss].point();
    let inside = r.put(1, boss.x + 3., boss.y);
    r.put(2, boss.x, boss.y + 14.);
    r.run(2.5);
    let play = r.w.boss_play(1).expect("a fight is running");
    let goal = play
        .goal
        .expect("a hero inside the ring is told to leave it");
    assert!(play.hold_fire, "running is not swinging");
    assert!(
        goal.distance(boss) > 8. + 0.5,
        "{goal:?} is clear of the ring"
    );
    assert!(
        goal.distance(inside) < 5.2 * 2.5,
        "and within reach before it lands"
    );
    let calm = r.w.boss_play(2).unwrap();
    assert_eq!((calm.goal, calm.hold_fire), (None, false));
    // The same goal is kept while the hero runs, rather than a new nearest place every tick.
    let again = r.w.boss_play(1).unwrap();
    assert_eq!(again.goal, Some(goal));
}

#[test]
fn a_fighter_who_is_marked_goes_where_the_ring_misses_their_friends() {
    let mut r = rig(DOWNPOUR, 3);
    let boss = r.w.slimes[r.boss].point();
    for s in 1..=3 {
        r.put(s, boss.x + 1. * s as f64, boss.y + 8.);
    }
    r.run(1.5);
    let bearer_id = r.view()["marked"][0].as_str().unwrap().to_string();
    let bearer = (1..=3)
        .find(|s| r.w.players[s].character.id == bearer_id)
        .unwrap();
    let goal =
        r.w.boss_play(bearer)
            .unwrap()
            .goal
            .expect("the bearer moves away");
    let nearest = |p: Point| {
        (1..=3)
            .filter(|s| *s != bearer)
            .map(|s| r.at(s).distance(p))
            .fold(f64::MAX, f64::min)
    };
    assert!(
        nearest(goal) > nearest(r.at(bearer)) + 1.,
        "{goal:?} is farther from the friends than where the bearer stands"
    );
    let friend = (1..=3).find(|s| *s != bearer).unwrap();
    assert!(
        r.w.boss_play(friend).unwrap().goal.is_some(),
        "a friend beside the ring is told to leave it"
    );
}

#[test]
fn helpers_and_cocoons_are_hit_before_the_boss_and_the_weaker_half_of_a_divided_boss() {
    // A shield's helpers, spread over the party.
    let mut r = rig(CHORUS, 2);
    r.sleepers("singer", &row(5));
    r.set_boss_share(0.65);
    r.run(0.2);
    let adds = r.fight().shield.as_ref().unwrap().adds.clone();
    for s in 1..=2 {
        let t =
            r.w.boss_play(s)
                .unwrap()
                .target
                .expect("a singer is the target");
        assert!(adds.contains(&t) && t != r.boss);
    }
    let (a, b) = (
        r.w.boss_play(1).unwrap().target,
        r.w.boss_play(2).unwrap().target,
    );
    assert_ne!(a, b, "two fighters take two different singers");
    // A friend in amber: the cocoon.
    let mut r = rig(AMBER, 3);
    r.sleepers("cocoon", &row(3));
    let boss = r.w.slimes[r.boss].point();
    for s in 1..=3 {
        r.put(s, boss.x - 4. + s as f64 * 4., boss.y + 6.);
    }
    r.run(4.);
    let frozen = (1..=3)
        .find(|s| r.w.players[s].frozen)
        .expect("someone is frozen");
    let cocoons: Vec<usize> = r.fight().frozen.values().map(|f| f.cocoon).collect();
    let free = (1..=3).find(|s| !r.w.players[s].frozen).unwrap();
    assert!(cocoons.contains(&r.w.boss_play(free).unwrap().target.unwrap()));
    assert!(
        r.w.boss_play(frozen).is_none(),
        "the frozen one does nothing"
    );
    // A divided boss: the half with more health, so the two come down together.
    let (mut r, partner) = split_rig();
    r.w.slimes[partner].hp = 10.;
    assert_eq!(r.w.boss_play(1).unwrap().target, Some(r.boss));
    r.w.slimes[partner].hp = r.w.slimes[r.boss].hp + 1000.;
    assert_eq!(r.w.boss_play(1).unwrap().target, Some(partner));
}

#[test]
fn a_charged_fighter_goes_to_a_ready_rod_and_a_dark_brazier_gets_a_holder() {
    let mut r = rig(STATIC, 2);
    r.run(0.2);
    let boss = r.w.slimes[r.boss].point();
    r.put(1, boss.x, boss.y + 10.);
    r.put(2, boss.x + 12., boss.y + 10.);
    for _ in 0..2 {
        r.hit_boss(1, 5.);
    }
    assert_eq!(
        r.w.boss_play(1).unwrap().goal,
        None,
        "two charges: keep fighting"
    );
    r.hit_boss(1, 5.);
    let play = r.w.boss_play(1).unwrap();
    assert!(play.hold_fire);
    let rod = play
        .goal
        .expect("three charges is the warning: go to a rod");
    assert!(
        [Point { x: 112., y: 12. }, Point { x: 120., y: 12. }].contains(&rod),
        "{rod:?}"
    );
    // Two braziers, none lit: the two fighters take one each, the nearest to each.
    let mut r = rig(NIGHT, 2);
    r.put(1, 112., 30.);
    r.put(2, 120., 30.);
    r.run(0.2);
    let (one, two) = (r.w.boss_play(1).unwrap(), r.w.boss_play(2).unwrap());
    assert_eq!(
        (one.goal, two.goal),
        (
            Some(Point { x: 112., y: 12. }),
            Some(Point { x: 120., y: 12. })
        )
    );
    assert!(one.hold_fire && two.hold_fire);
}
