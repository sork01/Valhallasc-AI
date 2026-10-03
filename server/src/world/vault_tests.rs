//! The Undervault: the dungeon under Skaldholm (zone 5), its private copies, ranged enemies, bosses and the Meeting Stone.
use super::*;

const SKALD: usize = 4;
const VAULT: usize = 5;

fn world() -> World {
    World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
}
fn join(w: &mut World, id: u64, class: Class) -> mpsc::Receiver<Value> {
    let (tx, rx) = mpsc::channel(4096);
    let look = Look {
        class,
        ..Look::default()
    };
    w.join(id, None, Some(look), tx).unwrap();
    rx
}
fn drain(rx: &mut mpsc::Receiver<Value>) -> Vec<Value> {
    std::iter::from_fn(|| rx.try_recv().ok()).collect()
}
fn free_for_player(map: &Map, p: Point) -> bool {
    let mut q = p;
    map.collide(&mut q, PLAYER_RADIUS);
    q.distance(p) < 1e-6
}
/// Breadth-first walk over free ground, half a unit per step (the same probe the zone tests use).
fn walk_steps(map: &Map, start: Point) -> std::collections::HashMap<(i32, i32), u32> {
    let cell = |p: Point| ((p.x / 0.5) as i32, (p.y / 0.5) as i32);
    let centre = |c: (i32, i32)| Point {
        x: (c.0 as f64 + 0.5) * 0.5,
        y: (c.1 as f64 + 0.5) * 0.5,
    };
    let limit = (map.size as f64 / 0.5) as i32;
    let mut seen = std::collections::HashMap::new();
    let mut queue = std::collections::VecDeque::new();
    seen.insert(cell(start), 0);
    queue.push_back(cell(start));
    while let Some(c) = queue.pop_front() {
        let d = seen[&c];
        for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
            let n = (c.0 + dx, c.1 + dy);
            if n.0 < 0 || n.1 < 0 || n.0 >= limit || n.1 >= limit || seen.contains_key(&n) {
                continue;
            }
            if free_for_player(map, centre(n)) {
                seen.insert(n, d + 1);
                queue.push_back(n);
            }
        }
    }
    seen
}
/// Puts a hero on the stairs down in Skaldholm and lets the portal run.
fn take_the_stairs(w: &mut World, session: u64) {
    w.players.get_mut(&session).unwrap().character.level = 20;
    step_on_the_stairs(w, session);
}
/// The same without making the hero level 20 first.
fn step_on_the_stairs(w: &mut World, session: u64) {
    let door = w.maps[SKALD]
        .portals
        .iter()
        .find(|p| p.to == VAULT)
        .unwrap()
        .clone();
    let c = &mut w.players.get_mut(&session).unwrap().character;
    c.zone = SKALD;
    c.x = door.x;
    c.y = door.y;
    w.time += 1.;
    w.step();
}
fn zone_of(w: &World, session: u64) -> usize {
    w.players[&session].character.zone
}
/// A hero standing at `at` in `zone`, awake (full health, no cooldown for a portal).
fn place(w: &mut World, session: u64, zone: usize, at: Point) {
    let c = &mut w.players.get_mut(&session).unwrap().character;
    c.zone = zone;
    c.x = at.x;
    c.y = at.y;
    c.hp = c.max_hp();
}
fn first(w: &World, zone: usize, kind: &str) -> usize {
    w.slimes
        .iter()
        .position(|s| s.zone == zone && s.kind == kind)
        .unwrap()
}

#[test]
fn the_undervault_is_a_five_player_dungeon_with_four_private_copies_four_bosses_and_a_way_out() {
    let w = world();
    let vault = &w.maps[VAULT];
    assert_eq!(vault.name, "The Undervault");
    assert_eq!(
        (
            vault.copies,
            vault.players,
            vault.levels,
            vault.final_boss.as_str()
        ),
        (4, 5, Some([20, 20]), "hollowking")
    );
    assert!(vault.city.is_none(), "no safe ground in a dungeon");
    // The world keeps three more copies after every file zone; clients are told the template's number.
    assert_eq!(w.maps.len(), 9);
    assert_eq!(w.instances.len(), 4);
    for (n, i) in w.instances.iter().enumerate() {
        assert_eq!(
            (i.template, i.zone),
            (VAULT, if n == 0 { VAULT } else { 5 + n })
        );
        assert!(!i.active && !i.cleared);
        if n > 0 {
            assert_eq!(w.maps[i.zone].template, Some(VAULT));
            assert_eq!(w.maps[i.zone].objects.len(), vault.objects.len());
        }
    }
    // Every copy has the same fifty enemies: 25 thralls, 12 archers, 9 acolytes and one of each boss.
    let count = |zone: usize, kind: &str| {
        w.slimes
            .iter()
            .filter(|s| s.zone == zone && s.kind == kind)
            .count()
    };
    for zone in [5, 6, 7, 8] {
        let counts: Vec<_> = [
            "thrall",
            "archer",
            "acolyte",
            "gatewarden",
            "choir",
            "colossus",
            "hollowking",
        ]
        .iter()
        .map(|k| count(zone, k))
        .collect();
        assert_eq!(counts, [25, 12, 9, 1, 1, 1, 1], "zone {zone}");
        assert_eq!(w.slimes.iter().filter(|s| s.zone == zone).count(), 50);
    }
    // The file's own enemies keep their old ids: the copies come after everything else.
    assert!(
        w.slimes
            .iter()
            .take(w.spawns.iter().filter(|s| s.zone < VAULT).count())
            .all(|s| s.zone < VAULT)
    );
    // The stairs down in Skaldholm lead to the template; the dungeon has stairs up and an exit that needs a clear.
    let down: Vec<_> = w.maps[SKALD]
        .portals
        .iter()
        .filter(|p| p.to == VAULT)
        .collect();
    assert_eq!(down.len(), 1);
    assert_eq!(
        (down[0].tx, down[0].ty),
        (vault.spawn.x, vault.spawn.y),
        "the stairs set you down at the dungeon's start"
    );
    assert_eq!(vault.portals.len(), 2);
    assert!(!vault.portals[0].after_clear && vault.portals[1].after_clear);
    assert!(vault.portals.iter().all(|p| p.to == SKALD));
    for p in &w.maps[SKALD].portals {
        assert!(p.id != "undervault_stairs" || p.r < 1.3);
    }
    // Arrival points are outside every gate of the zone they land in.
    for map in &w.maps {
        for p in &map.portals {
            for q in &w.maps[p.to].portals {
                let arrival = Point { x: p.tx, y: p.ty };
                assert!(
                    arrival.distance(Point { x: q.x, y: q.y }) > q.r + 0.5,
                    "{} arrives inside {}",
                    p.id,
                    q.id
                );
            }
        }
    }
    assert!(
        w.spawns
            .iter()
            .filter(|s| s.zone == VAULT)
            .all(|s| Point { x: s.x, y: s.y }.distance(vault.spawn) > 12.)
    );
}

#[test]
fn the_dungeon_is_one_long_walk_that_meets_the_four_bosses_in_order_and_every_enemy_stands_on_free_ground()
 {
    let w = world();
    let map = &w.maps[VAULT];
    let steps = walk_steps(map, map.spawn);
    let reach = |p: Point| {
        steps
            .get(&((p.x / 0.5) as i32, (p.y / 0.5) as i32))
            .copied()
    };
    for s in w.spawns.iter().filter(|s| s.zone == VAULT) {
        let at = Point { x: s.x, y: s.y };
        assert!(
            free_for_player(map, at),
            "{} at {at:?} stands on free ground",
            s.kind
        );
        assert!(reach(at).is_some(), "{} at {at:?} can be walked to", s.kind);
    }
    for p in &map.portals {
        assert!(
            reach(Point { x: p.x, y: p.y }).is_some(),
            "{} can be walked to",
            p.id
        );
    }
    let order: Vec<_> = ["gatewarden", "choir", "colossus", "hollowking"]
        .iter()
        .map(|k| {
            let s = w
                .spawns
                .iter()
                .find(|s| s.zone == VAULT && s.kind == *k)
                .unwrap();
            reach(Point { x: s.x, y: s.y }).unwrap() as f64 * 0.5
        })
        .collect();
    assert!(
        order.windows(2).all(|p| p[0] < p[1]),
        "bosses in order along the walk: {order:?}"
    );
    assert!(
        order[3] > 250.,
        "a real dungeon: {} tiles to the last boss",
        order[3]
    );
    // The walls hold: stone right beside the corridors cannot be entered.
    for at in [
        Point { x: 40., y: 100. },
        Point { x: 70., y: 80. },
        Point { x: 5., y: 110. },
        Point { x: 126., y: 60. },
    ] {
        assert!(reach(at).is_none(), "{at:?} is solid rock");
    }
}

#[test]
fn a_party_is_given_its_own_copy_strangers_get_another_and_a_full_house_is_turned_away() {
    let mut w = world();
    let mut rxs: Vec<_> = (1..=6).map(|s| join(&mut w, s, Class::Warrior)).collect();
    take_the_stairs(&mut w, 1);
    assert_eq!(zone_of(&w, 1), 5, "the first hero gets the first copy");
    let c = &w.players[&1].character;
    let start = w.maps[VAULT].spawn;
    assert_eq!(
        (c.x, c.y),
        (start.x, start.y),
        "set down at the foot of the stairs"
    );
    assert!(w.instances[0].active);
    // A stranger does not share it.
    take_the_stairs(&mut w, 2);
    assert_eq!(zone_of(&w, 2), 6);
    // A party mate of the first hero joins the first copy even though others are free.
    let (a, b) = (
        w.players[&1].character.id.clone(),
        w.players[&3].character.id.clone(),
    );
    w.party_add_mercenary(&a, &w.players[&3].character.clone())
        .unwrap();
    assert_eq!(w.party_mates(&b).len(), 2);
    take_the_stairs(&mut w, 3);
    assert_eq!(zone_of(&w, 3), 5, "a party enters together");
    // Copies three and four go to the next two strangers; the sixth hero finds the house full.
    take_the_stairs(&mut w, 4);
    take_the_stairs(&mut w, 5);
    assert_eq!((zone_of(&w, 4), zone_of(&w, 5)), (7, 8));
    drain(&mut rxs[5]);
    take_the_stairs(&mut w, 6);
    assert_eq!(zone_of(&w, 6), SKALD, "no copy is free: still in Skaldholm");
    let told: Vec<_> = drain(&mut rxs[5]);
    assert!(
        told.iter()
            .any(|v| v["type"] == "error" && v["text"].as_str().unwrap().contains("in use")),
        "{told:?}"
    );
    // Leaving frees a copy.
    w.leave(2);
    w.step();
    assert!(!w.instances[1].active, "an empty copy is reset");
    take_the_stairs(&mut w, 6);
    assert_eq!(zone_of(&w, 6), 6);
}

fn view_index(snapshot: &Value, id: &str) -> usize {
    snapshot["zones"]
        .as_array()
        .unwrap()
        .iter()
        .position(|z| {
            z["players"]
                .as_array()
                .is_some_and(|p| p.iter().any(|p| p["id"] == id))
        })
        .unwrap()
}

#[test]
fn copies_do_not_share_enemies_players_or_snapshots_and_clients_are_told_the_template_zone() {
    let mut w = world();
    let _a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Mage);
    take_the_stairs(&mut w, 1);
    take_the_stairs(&mut w, 2);
    assert_eq!((zone_of(&w, 1), zone_of(&w, 2)), (5, 6));
    let (t5, t6) = (first(&w, 5, "thrall"), first(&w, 6, "thrall"));
    assert_ne!(t5, t6);
    let (x, y) = (w.slimes[t5].x, w.slimes[t5].y);
    // Both heroes stand beside the same thrall of their own copy; only the first copy's thrall is hurt.
    for s in [1, 2] {
        let zone = zone_of(&w, s);
        place(&mut w, s, zone, Point { x: x - 1.5, y });
    }
    w.hit_slime(t5, 1, 100., false);
    assert_eq!(w.slimes[t6].hp, w.slimes[t6].max_hp);
    assert!(w.slimes[t5].hp < w.slimes[t5].max_hp);
    // A hero cannot target or strike an enemy of another copy.
    w.message(2, ClientMessage::Target { id: t5 });
    assert_eq!(w.players[&2].target, None);
    assert_eq!(w.hit_slime(t5, 2, 100., false), 0.);
    // Snapshots: each copy lists only its own hero and enemies, all labelled with the template's zone.
    let all = w.snapshot();
    let zones = all["zones"].as_array().unwrap();
    assert_eq!(zones.len(), 9);
    for (copy, who) in [(5usize, 1u64), (6, 2)] {
        let v = &zones[copy];
        let players = v["players"].as_array().unwrap();
        assert_eq!(players.len(), 1);
        assert_eq!(players[0]["id"], w.players[&who].character.id.as_str());
        assert!(players.iter().all(|p| p["zone"] == 5));
        let slimes = v["slimes"].as_array().unwrap();
        assert_eq!(slimes.len(), 50);
        assert!(slimes.iter().all(|s| s["zone"] == 5));
        assert_eq!(v["instance"]["cleared"], false);
    }
    // An unused copy sends no enemies at all.
    assert!(zones[7]["slimes"].as_array().unwrap().is_empty());
    // main.rs picks the view that lists the hero, so each client gets its own copy.
    assert_eq!(view_index(&all, &w.players[&2].character.id), 6);
}

#[test]
fn a_dungeon_copy_resets_when_its_last_hero_leaves_and_a_hero_who_logged_out_inside_wakes_at_the_door()
 {
    let mut w = world();
    let _a = join(&mut w, 1, Class::Warrior);
    take_the_stairs(&mut w, 1);
    let id = first(&w, 5, "thrall");
    w.hit_slime(id, 1, 1_000_000., false);
    assert!(w.slimes[id].dead);
    assert_eq!(
        w.slimes[id].respawn, 1e9,
        "nothing respawns inside a dungeon"
    );
    // Standing in the hall, the hero is far from the thrall: nothing wakes it up or brings it back.
    for _ in 0..200 {
        w.step();
    }
    assert!(w.slimes[id].dead, "still dead after ten seconds");
    w.drops.push(Drop {
        id: 99,
        owner: "x".into(),
        zone: 5,
        x: 20.,
        y: 110.,
        z: 0.,
        value: 5,
        item: None,
        quantity: 0,
        t: 0.,
        col: "#fff",
    });
    // The hero walks out by the stairs up; the copy resets.
    let up = w.maps[VAULT].portals[0].clone();
    place(&mut w, 1, 5, Point { x: up.x, y: up.y });
    w.time += 1.;
    w.step();
    assert_eq!(zone_of(&w, 1), SKALD);
    let c = &w.players[&1].character;
    assert!(Point { x: c.x, y: c.y }.distance(Point { x: up.tx, y: up.ty }) < 1.);
    w.step();
    assert!(
        !w.slimes[id].dead && w.slimes[id].hp == w.slimes[id].max_hp,
        "back at its post"
    );
    assert!(w.drops.iter().all(|d| d.zone != 5));
    assert!(!w.instances[0].active);
    // A character saved inside a copy comes back at the stairs.
    let (tx, _rx) = mpsc::channel(64);
    let look = Look::default();
    let welcome = {
        let (tx2, _rx2) = mpsc::channel(64);
        w.leave(1);
        w.join(7, None, Some(look), tx2).unwrap()
    };
    let token = welcome["token"].as_str().unwrap().to_owned();
    place(&mut w, 7, 7, Point { x: 60., y: 110. });
    w.leave(7);
    let welcome = w.join(8, Some(token), None, tx).unwrap();
    assert_eq!(welcome["type"], "welcome");
    let c = &w.players[&8].character;
    assert_eq!(c.zone, SKALD);
    assert!(
        c.x > 100. && c.y > 118.,
        "beside the Meeting Stone: {}, {}",
        c.x,
        c.y
    );
}

/// Everything in the first copy is out of the way except `keep`, and a hero stands at `hero` (awake, level 20).
fn arena(w: &mut World, keep: usize, enemy_at: Point, hero_at: Point) -> mpsc::Receiver<Value> {
    let rx = join(w, 1, Class::Warrior);
    take_the_stairs(w, 1);
    for s in w.slimes.iter_mut().filter(|s| s.id != keep) {
        s.dead = true;
        s.respawn = 1e9;
    }
    let s = &mut w.slimes[keep];
    (s.x, s.y, s.hx, s.hy) = (enemy_at.x, enemy_at.y, enemy_at.x, enemy_at.y);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 20;
    place(w, 1, VAULT, hero_at);
    rx
}

#[test]
fn an_archer_stops_at_range_shoots_a_missile_that_hurts_and_backs_away_when_crowded() {
    let mut w = world();
    let archer = first(&w, VAULT, "archer");
    let mut rx = arena(
        &mut w,
        archer,
        Point { x: 10., y: 111. },
        Point { x: 18., y: 111. },
    );
    let mut seen_bolt = None;
    let mut hurt = 0.;
    let (mut closest, mut farthest) = (f64::MAX, 0f64);
    for _ in 0..(8. / TICK) as usize {
        w.step();
        let d = w.slimes[archer]
            .point()
            .distance(w.players[&1].character.point());
        closest = closest.min(d);
        farthest = farthest.max(d);
        if seen_bolt.is_none() {
            seen_bolt = w.enemy_bolts.first().cloned();
        }
        for v in drain(&mut rx) {
            if v["kind"] == "hurt" {
                assert_eq!(v["enemy"], "archer");
                hurt += v["value"].as_f64().unwrap();
            }
        }
    }
    let bolt = seen_bolt.expect("the archer shot");
    let view = serde_json::to_value(&bolt).unwrap();
    assert_eq!(
        (view["zone"].as_u64(), view["kind"].as_str()),
        (Some(5), Some("archer"))
    );
    assert!(view["color"].is_string() && view["fx"].is_number());
    assert!(hurt > 0., "an arrow found the hero");
    assert!(closest > 3.4, "it never walks up to melee: {closest:.1}");
    // Crowded at two units, it backs off to a comfortable distance and shoots again.
    let near = Point {
        x: w.slimes[archer].x + 2.,
        y: w.slimes[archer].y,
    };
    place(&mut w, 1, VAULT, near);
    for _ in 0..(1.5 / TICK) as usize {
        w.step();
    }
    let d = w.slimes[archer]
        .point()
        .distance(w.players[&1].character.point());
    assert!(d > 3.5, "backed away: {d:.1}");
    assert!(farthest < 11., "it never wanders off: {farthest:.1}");
}

#[test]
fn missiles_stop_at_walls_fan_out_for_a_volley_and_miss_a_hero_who_has_left_the_line() {
    let mut w = world();
    let choir = first(&w, VAULT, "choir");
    let _rx = arena(
        &mut w,
        choir,
        Point { x: 10., y: 111. },
        Point { x: 25., y: 105. },
    );
    // A single shot into the west wall dies there and nobody is hurt.
    let ranged = Slime::ranged("archer").unwrap();
    w.fire_enemy_bolts(choir, Point { x: 0., y: 111. }, &ranged);
    assert_eq!(w.enemy_bolts.len(), 1);
    // The wall is about four tiles away, a quarter of a second at this speed; the missile would fly for nearly a second.
    for _ in 0..8 {
        w.update_enemy_bolts();
    }
    assert!(
        w.enemy_bolts.is_empty(),
        "the wall stopped it long before it would have faded"
    );
    // The same shot into open ground is still flying at that moment.
    w.fire_enemy_bolts(choir, Point { x: 25., y: 111. }, &ranged);
    for _ in 0..8 {
        w.update_enemy_bolts();
    }
    assert_eq!(w.enemy_bolts.len(), 1, "open ground does not stop it");
    w.enemy_bolts.clear();
    assert_eq!(w.players[&1].character.hp, w.players[&1].character.max_hp());
    // The Choir's volley is three missiles fanned over 0.68 radians.
    let r = Slime::ranged("choir").unwrap();
    assert_eq!((r.shots, r.range as u32), (3, 11));
    w.fire_enemy_bolts(choir, Point { x: 25., y: 111. }, &r);
    let angles: Vec<f64> = w
        .enemy_bolts
        .iter()
        .map(|b| serde_json::to_value(b).unwrap())
        .map(|v| v["fy"].as_f64().unwrap().atan2(v["fx"].as_f64().unwrap()))
        .collect();
    assert_eq!(angles.len(), 3);
    assert!(
        (angles[0] + 0.34).abs() < 1e-9
            && angles[1].abs() < 1e-9
            && (angles[2] - 0.34).abs() < 1e-9,
        "{angles:?}"
    );
    // A hero standing off the line of every missile is never hit: the shots pass above and below.
    place(
        &mut w,
        1,
        VAULT,
        Point {
            x: 30.,
            y: 111. + 6.,
        },
    );
    for _ in 0..60 {
        w.update_enemy_bolts();
    }
    assert_eq!(w.players[&1].character.hp, w.players[&1].character.max_hp());
    // Missiles are zone-bound: another copy's hero standing in the line is not hit either.
    let _b = join(&mut w, 2, Class::Warrior);
    take_the_stairs(&mut w, 2);
    assert_eq!(zone_of(&w, 2), 6);
    place(&mut w, 2, 6, Point { x: 14., y: 111. });
    w.fire_enemy_bolts(choir, Point { x: 25., y: 111. }, &r);
    for _ in 0..30 {
        w.update_enemy_bolts();
    }
    assert_eq!(w.players[&2].character.hp, w.players[&2].character.max_hp());
}

#[test]
fn the_gatewarden_pounds_the_ground_hurting_everyone_inside_the_ring_and_nobody_outside() {
    let mut w = world();
    let boss = first(&w, VAULT, "gatewarden");
    let at = Point { x: 12., y: 111. };
    let mut rx = arena(
        &mut w,
        boss,
        at,
        Point {
            x: at.x + 2.5,
            y: at.y,
        },
    );
    let _b = join(&mut w, 2, Class::Warrior);
    let _c = join(&mut w, 3, Class::Warrior);
    for s in [2, 3] {
        w.party_add_mercenary(
            &w.players[&1].character.id.clone(),
            &w.players[&s].character.clone(),
        )
        .unwrap();
        take_the_stairs(&mut w, s);
        assert_eq!(zone_of(&w, s), VAULT);
    }
    for s in 1..=3 {
        w.players.get_mut(&s).unwrap().character.level = 20;
    }
    place(
        &mut w,
        2,
        VAULT,
        Point {
            x: at.x,
            y: at.y - 3.3,
        },
    );
    place(
        &mut w,
        3,
        VAULT,
        Point {
            x: at.x,
            y: at.y + 7.,
        },
    );
    let before: Vec<f64> = (1..=3).map(|s| w.players[&s].character.hp).collect();
    let mut rings = 0;
    for _ in 0..(3. / TICK) as usize {
        w.step();
        for v in drain(&mut rx) {
            if v["kind"] == "slam" {
                rings += 1;
                assert_eq!(v["value"], 3.6);
            }
        }
    }
    let after: Vec<f64> = (1..=3).map(|s| w.players[&s].character.hp).collect();
    assert!(rings >= 1, "the ring is announced");
    assert!(after[0] < before[0], "hero 1 stood beside the boss");
    assert!(after[1] < before[1], "hero 2 at 3.3 is inside the 3.6 ring");
    assert_eq!(after[2], before[2], "hero 3 at 7 is outside it");
}

fn dialogue_notice(rx: &mut mpsc::Receiver<Value>) -> String {
    std::iter::from_fn(|| rx.try_recv().ok())
        .filter(|v| v["type"] == "dialogue")
        .last()
        .map_or_else(String::new, |v| {
            v["notice"].as_str().unwrap_or("").to_owned()
        })
}
fn mercs_of(w: &World) -> Vec<&Player> {
    w.players.values().filter(|p| p.merc.is_some()).collect()
}

#[test]
fn the_meeting_stone_hires_fighters_for_any_party_of_up_to_five_with_no_quest_and_for_gold() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let stone = w.maps[SKALD]
        .npcs
        .iter()
        .find(|n| n.id == "city_meetingstone")
        .unwrap()
        .clone();
    assert_eq!(stone.offers.len(), 6, "five classes and a dismissal");
    assert!(
        stone
            .offers
            .iter()
            .filter(|o| o.merc.as_deref() != Some("dismiss"))
            .all(|o| o.open && o.cost == 250)
    );
    let at = |w: &mut World, x: f64, y: f64| {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        (c.zone, c.x, c.y) = (SKALD, x, y);
    };
    let hire = |w: &mut World, rx: &mut mpsc::Receiver<Value>, class: &str| {
        w.time += 0.6;
        w.interact(1, "city_meetingstone", Some(&format!("merc_{class}")));
        dialogue_notice(rx)
    };
    // Far away: refused. Close, without gold: refused with the price.
    at(&mut w, 60., 100.);
    w.time += 0.6;
    w.interact(1, "city_meetingstone", Some("merc_mage"));
    assert!(drain(&mut rx).iter().any(|v| v["type"] == "error"));
    at(&mut w, stone.x, stone.y + 1.);
    w.players.get_mut(&1).unwrap().character.level = 20;
    assert!(hire(&mut w, &mut rx, "mage").contains("250 gold"));
    // With gold: no quest needed, one seat at a time up to a party of five.
    w.players.get_mut(&1).unwrap().character.gold = 1100;
    for (n, class) in ["priest", "mage", "hunter", "warrior"].iter().enumerate() {
        let text = hire(&mut w, &mut rx, class);
        assert!(text.contains("joins your party"), "{class}: {text}");
        assert!(text.contains(&format!("{}/5", n + 2)), "{text}");
    }
    assert_eq!(w.players[&1].character.gold, 100);
    assert_eq!(mercs_of(&w).len(), 4);
    let owner = w.players[&1].character.id.clone();
    assert_eq!(w.party_mates(&owner).len(), 5);
    let text = hire(&mut w, &mut rx, "assassin");
    assert!(text.contains("already has 5"), "{text}");
    assert_eq!(w.players[&1].character.gold, 100, "nothing was charged");
    // A mercenary is the hirer's level and follows through the stairs into the dungeon.
    assert!(mercs_of(&w).iter().all(|m| m.character.level == 20));
    take_the_stairs(&mut w, 1);
    assert_eq!(zone_of(&w, 1), VAULT);
    for _ in 0..5 {
        w.step();
    }
    assert!(
        mercs_of(&w).iter().all(|m| m.character.zone == VAULT),
        "the party arrives together"
    );
    // They can be sent away again, anywhere the Stone listens.
    at(&mut w, stone.x, stone.y + 1.);
    w.time += 0.6;
    w.interact(1, "city_meetingstone", Some("merc_dismiss"));
    assert!(dialogue_notice(&mut rx).contains("ended"));
    assert!(mercs_of(&w).is_empty());
}

/// Three nearby party members and a fourth in another private copy; only heroes 1 and 2 hit the boss.
fn kill_with_party(w: &mut World, kind: &str) -> Vec<mpsc::Receiver<Value>> {
    let boss = first(w, VAULT, kind);
    let rxs: Vec<_> = [Class::Warrior, Class::Mage, Class::Priest, Class::Hunter]
        .iter()
        .enumerate()
        .map(|(n, c)| join(w, n as u64 + 1, *c))
        .collect();
    take_the_stairs(w, 1);
    take_the_stairs(w, 4);
    assert_ne!(zone_of(w, 4), VAULT);
    let leader = w.players[&1].character.id.clone();
    for s in 2..=4 {
        w.party_add_mercenary(&leader, &w.players[&s].character.clone())
            .unwrap();
    }
    for s in 2..=3 {
        take_the_stairs(w, s);
        assert_eq!(zone_of(w, s), VAULT);
    }
    let at = w.slimes[boss].point();
    for s in 1..=3 {
        place(
            w,
            s,
            VAULT,
            Point {
                x: at.x - 2.,
                y: at.y + s as f64,
            },
        );
    }
    w.slimes[boss].hp = 100.;
    w.hit_slime(boss, 2, 10., false);
    w.hit_slime(boss, 1, 1_000_000., false);
    assert!(w.slimes[boss].dead);
    rxs
}

#[test]
fn every_boss_drops_shared_random_gear_and_every_nearby_party_member_rolls_once_per_piece() {
    for (kind, pieces) in [
        ("gatewarden", 1),
        ("choir", 1),
        ("colossus", 1),
        ("hollowking", 2),
    ] {
        let mut w = world();
        w.rng = 3;
        let mut rxs = kill_with_party(&mut w, kind);
        let starts: Vec<Vec<Value>> = rxs
            .iter_mut()
            .map(|rx| {
                drain(rx)
                    .into_iter()
                    .filter(|v| {
                        v["type"] == "roll"
                            && v["op"] == "start"
                            && v["item"]
                                .as_str()
                                .and_then(item)
                                .is_some_and(|i| i.source.as_deref() == Some("undervault"))
                    })
                    .collect()
            })
            .collect();
        assert_eq!(
            starts[0].len(),
            pieces,
            "{kind}: one roll per pool, regardless of contributors"
        );
        assert_eq!(starts[1].len(), pieces);
        assert_eq!(
            starts[2].len(),
            pieces,
            "a nearby party member need not hit the boss"
        );
        assert!(
            starts[3].is_empty(),
            "a member in another private copy cannot roll"
        );
        assert!(
            w.drops.iter().all(|d| d
                .item
                .as_deref()
                .and_then(item)
                .is_none_or(|i| i.source.as_deref() != Some("undervault"))),
            "boss pieces wait for their rolls"
        );
        for (n, start) in starts[0].iter().enumerate() {
            let id = start["id"].as_u64().unwrap();
            let piece = item(start["item"].as_str().unwrap()).unwrap();
            assert_eq!((piece.rarity.as_str(), piece.required_level), ("rare", 20));
            assert!(boss_slots(kind)[n].contains(&piece.kind.as_str()));
            let blue = item(&piece.id.replace("_l20_vault", "_l20_blue")).unwrap();
            assert!(
                (piece.attack - blue.attack * 1.15).abs() < 0.06
                    && (piece.defense - blue.defense * 1.15).abs() < 0.06
            );
            assert!(
                piece.name != blue.name && piece.art == blue.art && piece.variant != blue.variant
            );
            for s in 1..=3 {
                assert_eq!(starts[s - 1][n]["id"], id);
                assert_eq!(
                    starts[s - 1][n]["need"],
                    rolls::can_need(&w.players[&(s as u64)].character, piece)
                );
                let choice = if s != 3 {
                    RollChoice::Pass
                } else if starts[2][n]["need"] == true {
                    RollChoice::Need
                } else {
                    RollChoice::Greed
                };
                w.roll_vote(s as u64, id, choice);
            }
        }
        w.update_rolls();
        let drops: Vec<_> = w
            .drops
            .iter()
            .filter(|d| {
                d.item
                    .as_deref()
                    .and_then(item)
                    .is_some_and(|i| i.source.as_deref() == Some("undervault"))
            })
            .collect();
        assert_eq!(
            drops.len(),
            pieces,
            "one award per piece, no personal copies"
        );
        assert!(
            drops
                .iter()
                .all(|d| d.owner == w.players[&3].character.id && d.quantity == 1)
        );
        let boss = &w.slimes[first(&w, VAULT, kind)];
        assert_eq!(boss.xp, enemy_xp(boss.level) * 12);
    }
}

#[test]
fn solo_boss_loot_can_be_for_another_class_and_never_needs_a_roll() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    take_the_stairs(&mut w, 1);
    let owner = w.players[&1].character.id.clone();
    let at = w.slimes[first(&w, VAULT, "hollowking")].point();
    for _ in 0..20 {
        w.boss_loot(&owner, "hollowking", VAULT, at);
    }
    assert!(w.rolls.is_empty());
    assert_eq!(w.drops.len(), 40, "two pieces per king kill");
    assert!(w.drops.iter().all(|d| d.owner == owner && d.quantity == 1));
    assert!(
        w.drops
            .iter()
            .filter_map(|d| d.item.as_deref().and_then(item))
            .any(|i| i.class.is_some_and(|c| c != Class::Warrior)),
        "solo drops are not fitted to the killer's class"
    );
}

#[test]
fn a_mercenarys_boss_kill_starts_one_shared_roll_with_the_hirer() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 20;
        c.gold = 1000;
    }
    let stone = w.maps[SKALD]
        .npcs
        .iter()
        .find(|n| n.id == "city_meetingstone")
        .unwrap()
        .clone();
    place(
        &mut w,
        1,
        SKALD,
        Point {
            x: stone.x,
            y: stone.y + 1.,
        },
    );
    w.time += 0.6;
    w.interact(1, "city_meetingstone", Some("merc_priest"));
    let merc = *w.players.iter().find(|(_, p)| p.merc.is_some()).unwrap().0;
    take_the_stairs(&mut w, 1);
    let boss = first(&w, VAULT, "gatewarden");
    for _ in 0..3 {
        w.step();
    }
    let at = w.slimes[boss].point();
    place(
        &mut w,
        1,
        VAULT,
        Point {
            x: at.x - 20.,
            y: at.y,
        },
    );
    place(
        &mut w,
        merc,
        VAULT,
        Point {
            x: at.x - 2.,
            y: at.y,
        },
    );
    w.slimes[boss].hp = 50.;
    w.hit_slime(boss, merc, 1_000_000., false);
    assert!(w.slimes[boss].dead);
    let starts: Vec<_> = drain(&mut rx)
        .into_iter()
        .filter(|v| {
            v["type"] == "roll"
                && v["op"] == "start"
                && v["item"]
                    .as_str()
                    .and_then(item)
                    .is_some_and(|i| i.source.as_deref() == Some("undervault"))
        })
        .collect();
    assert_eq!(
        starts.len(),
        1,
        "the hirer and fighter share one boss piece"
    );
    w.roll_vote(1, starts[0]["id"].as_u64().unwrap(), RollChoice::Pass);
    w.update_rolls();
    assert!(
        w.drops.iter().all(|d| d
            .item
            .as_deref()
            .and_then(item)
            .is_none_or(|i| i.source.as_deref() != Some("undervault"))),
        "the mercenary wins and keeps the piece"
    );
}

#[test]
fn killing_the_hollow_king_opens_the_way_out_and_the_portal_works_only_then() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    take_the_stairs(&mut w, 1);
    let exit = w.maps[VAULT]
        .portals
        .iter()
        .find(|p| p.after_clear)
        .unwrap()
        .clone();
    // Closed: standing on it does nothing.
    place(
        &mut w,
        1,
        VAULT,
        Point {
            x: exit.x,
            y: exit.y,
        },
    );
    w.time += 1.;
    for _ in 0..10 {
        w.step();
    }
    assert_eq!(zone_of(&w, 1), VAULT, "the exit is closed");
    assert_eq!(w.snapshot_for(VAULT)["instance"]["cleared"], false);
    // The other bosses do not open it; the last one does.
    let king = first(&w, VAULT, "hollowking");
    for kind in ["gatewarden", "choir", "colossus"] {
        let id = first(&w, VAULT, kind);
        let near = Point {
            x: w.slimes[id].x - 2.,
            y: w.slimes[id].y,
        };
        place(&mut w, 1, VAULT, near);
        w.slimes[id].hp = 1.;
        w.hit_slime(id, 1, 100., false);
        assert!(!w.instance_cleared(VAULT), "{kind} is not the last");
    }
    drain(&mut rx);
    let at = w.slimes[king].point();
    place(
        &mut w,
        1,
        VAULT,
        Point {
            x: at.x - 2.,
            y: at.y,
        },
    );
    w.slimes[king].hp = 1.;
    w.hit_slime(king, 1, 100., false);
    assert!(w.instance_cleared(VAULT));
    assert_eq!(w.snapshot_for(VAULT)["instance"]["cleared"], true);
    let told = drain(&mut rx);
    assert!(
        told.iter()
            .any(|v| v["type"] == "system" && v["text"].as_str().unwrap().contains("cleared")),
        "{told:?}"
    );
    assert!(told.iter().any(|v| v["kind"] == "cleared"));
    // Another copy is not cleared by it.
    assert!(!w.instance_cleared(6));
    // Now the portal carries the hero out beside the stairs in Skaldholm.
    place(
        &mut w,
        1,
        VAULT,
        Point {
            x: exit.x,
            y: exit.y,
        },
    );
    w.time += 1.;
    w.step();
    let c = &w.players[&1].character;
    assert_eq!((c.zone, c.x, c.y), (SKALD, exit.tx, exit.ty));
    // With everyone gone the copy is whole again: the king lives and the way out is shut.
    w.step();
    assert!(!w.slimes[king].dead && !w.instance_cleared(VAULT));
}

// ---- balance simulations -------------------------------------------------------------------------------------------

struct Run {
    won: bool,
    secs: f64,
    deaths: usize,
    left: f64,
    /// The lowest health fraction any member of the party reached (the healer's work).
    low: f64,
}
/// A trained level-20 warrior hirer with `classes` rented at the Meeting Stone, all standing `lead` units from the
/// middle of `ids`' enemies, fights until they are all down, the party is down, or `limit` seconds pass. Everything
/// else in the dungeon is out of the way.
fn fight(classes: &[&str], ids: &[usize], from: Point, limit: f64, seed: u64) -> (World, Run) {
    let mut w = world();
    w.rng = seed;
    let mut rx = join(&mut w, 1, Class::Warrior);
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 20;
        c.gold = 5000;
        c.attributes.strength = 40;
        c.attributes.stamina = 10;
        c.attributes.accuracy = 7;
        c.add_item("health_potion_l20", 3);
    }
    let stone = w.maps[SKALD]
        .npcs
        .iter()
        .find(|n| n.id == "city_meetingstone")
        .unwrap()
        .clone();
    place(
        &mut w,
        1,
        SKALD,
        Point {
            x: stone.x,
            y: stone.y + 1.,
        },
    );
    for class in classes {
        w.time += 0.6;
        w.interact(1, "city_meetingstone", Some(&format!("merc_{class}")));
    }
    assert_eq!(mercs_of(&w).len(), classes.len());
    take_the_stairs(&mut w, 1);
    for s in w
        .slimes
        .iter_mut()
        .filter(|s| s.zone == VAULT && !ids.contains(&s.id))
    {
        s.dead = true;
        s.respawn = 1e9;
    }
    place(&mut w, 1, VAULT, from);
    for (i, p) in w
        .players
        .values_mut()
        .filter(|p| p.merc.is_some())
        .enumerate()
    {
        p.character.x = from.x + 1. + i as f64 * 0.7;
        p.character.y = from.y + 1.;
        p.character.zone = VAULT;
        p.character.hp = p.character.max_hp();
    }
    let mut deaths = 0;
    let mut was_dead = std::collections::HashSet::new();
    let mut result = Run {
        won: false,
        secs: 0.,
        deaths: 0,
        left: 0.,
        low: 1.,
    };
    for _ in 0..(limit / TICK) as usize {
        if w.players[&1].character.hp > 0. {
            let me = w.players[&1].character.point();
            let near = ids
                .iter()
                .copied()
                .filter(|i| !w.slimes[*i].dead)
                .min_by(|a, b| {
                    w.slimes[*a]
                        .point()
                        .distance(me)
                        .total_cmp(&w.slimes[*b].point().distance(me))
                });
            if let Some(id) = near {
                if w.players[&1].target != Some(id) {
                    w.message(1, ClientMessage::Target { id });
                }
                let aim = me.direction(w.slimes[id].point());
                for skill in [
                    "battlecry",
                    "shieldwall",
                    "cleave",
                    "whirlwind",
                    "charge",
                    "groundslam",
                ] {
                    w.use_skill(1, skill, aim);
                }
            }
            let c = &w.players[&1].character;
            if c.hp <= c.max_hp() - 350. {
                w.use_item(1, "health_potion_l20");
            }
        }
        w.step();
        drain(&mut rx);
        let mut back = vec![];
        for (s, p) in &w.players {
            if p.character.hp <= 0. && was_dead.insert(*s) {
                deaths += 1;
            }
            if p.character.hp > 0. && was_dead.remove(s) {
                back.push(*s);
            }
        }
        for p in w.players.values().filter(|p| p.character.hp > 0.) {
            result.low = result.low.min(p.character.hp / p.character.max_hp());
        }
        // A fallen hero wakes at the dungeon's start; a real player runs back, so put them at the fight again.
        for s in back {
            place(&mut w, s, VAULT, from);
        }
        if ids.iter().all(|i| w.slimes[*i].dead) {
            result.won = true;
            break;
        }
        if w.players.values().all(|p| p.character.hp <= 0.) {
            break;
        }
    }
    result.secs = w.time;
    result.deaths = deaths;
    result.left = ids.iter().map(|i| w.slimes[*i].hp).sum();
    (w, result)
}
/// A free spot `distance` from `at` on the open side of the arena (towards the middle of the map).
fn open_spot(w: &World, at: Point, distance: f64) -> Point {
    (0..16)
        .map(|k| k as f64 * std::f64::consts::TAU / 16.)
        .map(|a| Point {
            x: at.x + a.cos() * distance,
            y: at.y + a.sin() * distance,
        })
        .find(|p| free_for_player(&w.maps[VAULT], *p))
        .expect("an open spot")
}
fn pack_ids(w: &World, centre: (f64, f64)) -> Vec<usize> {
    w.spawns
        .iter()
        .enumerate()
        .filter(|(_, s)| {
            s.zone == VAULT && ((s.x - centre.0).powi(2) + (s.y - centre.1).powi(2)).sqrt() < 6.
        })
        .map(|(i, _)| i)
        .collect()
}

const FULL: [&str; 4] = ["warrior", "priest", "mage", "hunter"];

#[test]
fn a_lone_hero_dies_to_a_trash_pack_while_a_hired_party_clears_it_without_a_death() {
    let w0 = world();
    for (centre, name) in [((57., 101.), "barracks"), ((104., 52.), "ossuary")] {
        let ids = pack_ids(&w0, centre);
        assert_eq!(ids.len(), 4, "{name}: a pack of four");
        let from = Point {
            x: centre.0 - 9.,
            y: centre.1 + 4.,
        };
        let (_, alone) = fight(&[], &ids, from, 120., 5);
        assert!(
            !alone.won && alone.deaths >= 1,
            "{name}: a lone hero falls ({:.0}s, {} deaths)",
            alone.secs,
            alone.deaths
        );
        let (_, five) = fight(&FULL, &ids, from, 120., 5);
        assert!(
            five.won && five.deaths == 0,
            "{name}: the hired five win with no death ({:.0}s)",
            five.secs
        );
        assert!(
            five.secs > 12. && five.secs < 70.,
            "{name}: a pack takes a real fight, not a blink: {:.0}s",
            five.secs
        );
        assert!(
            five.low < 0.9,
            "{name}: the party is actually hurt (lowest {:.0}%)",
            five.low * 100.
        );
        let (_, three) = fight(&["priest", "mage"], &ids, from, 160., 5);
        assert!(three.won, "{name}: three heroes with a healer still win");
        assert!(
            three.secs > five.secs && three.low < five.low,
            "{name}: but slower and nearer the edge"
        );
    }
}

#[test]
fn the_first_two_bosses_are_two_to_three_minute_fights_for_a_full_party() {
    let w0 = world();
    for (kind, low, high) in [("gatewarden", 90., 220.), ("choir", 120., 280.)] {
        let id = first(&w0, VAULT, kind);
        let from = open_spot(&w0, w0.slimes[id].point(), 8.);
        let (w, r) = fight(&FULL, &[id], from, 400., 5);
        assert!(r.won, "{kind} falls to the hired five (left {:.0})", r.left);
        assert!(
            r.secs > low && r.secs < high,
            "{kind} takes {:.0}s, expected {low}-{high}",
            r.secs
        );
        assert!(
            w.slimes[id].dead && w.slimes[id].max_hp >= 80000.,
            "{kind} is a long fight: {} HP",
            w.slimes[id].max_hp
        );
        assert!(
            r.low < 0.6,
            "{kind} hurts the party (lowest {:.0}%)",
            r.low * 100.
        );
    }
}

#[test]
fn the_colossus_and_the_hollow_king_need_five_and_a_healer_the_king_beating_a_party_of_three() {
    let w0 = world();
    let colossus = first(&w0, VAULT, "colossus");
    let from = open_spot(&w0, w0.slimes[colossus].point(), 8.);
    let (_, r) = fight(&FULL, &[colossus], from, 400., 5);
    assert!(
        r.won && r.secs > 100. && r.secs < 300.,
        "the colossus falls to the five in {:.0}s",
        r.secs
    );
    let king = first(&w0, VAULT, "hollowking");
    let from = open_spot(&w0, w0.slimes[king].point(), 8.);
    let (_, five) = fight(&FULL, &[king], from, 500., 5);
    assert!(
        five.won,
        "the king falls to the hired five (left {:.0})",
        five.left
    );
    assert!(
        five.secs > 150. && five.secs < 420.,
        "the last fight is the longest: {:.0}s",
        five.secs
    );
    let (_, three) = fight(&["warrior", "priest"], &[king], from, 400., 5);
    assert!(
        !three.won && three.left > 5000.,
        "a hirer with a warrior and a priest cannot finish the king in {:.0}s (left {:.0})",
        three.secs,
        three.left
    );
}

#[test]
#[ignore]
fn vault_balance_probe() {
    let full = ["warrior", "priest", "mage", "hunter"];
    for (name, centre) in [
        ("barracks pack 1", (57., 101.)),
        ("ossuary pack 2", (104., 52.)),
        ("cistern pack 3", (49., 9.)),
    ] {
        for classes in [&full[..], &["priest", "mage"][..], &[][..]] {
            let w0 = world();
            let ids = pack_ids(&w0, centre);
            let from = Point {
                x: centre.0 - 9.,
                y: centre.1 + 4.,
            };
            let (_, r) = fight(classes, &ids, from, 240., 5);
            println!(
                "{name} ({} foes) vs hero+{classes:?}: won {} in {:.0}s, {} deaths, lowest {:.0}%, {:.0} hp left",
                ids.len(),
                r.won,
                r.secs,
                r.deaths,
                r.low * 100.,
                r.left
            );
        }
    }
    for kind in ["gatewarden", "choir", "colossus", "hollowking"] {
        for classes in [&full[..], &["warrior", "priest"][..]] {
            let w0 = world();
            let id = first(&w0, VAULT, kind);
            let from = open_spot(&w0, w0.slimes[id].point(), 8.);
            let (w, r) = fight(classes, &[id], from, 400., 5);
            println!(
                "{kind} (hp {:.0}) vs hero+{classes:?}: won {} in {:.0}s, {} deaths, lowest {:.0}%, {:.0} hp left",
                w.slimes[id].max_hp,
                r.won,
                r.secs,
                r.deaths,
                r.low * 100.,
                r.left
            );
        }
    }
}

#[test]
fn the_door_asks_for_level_twenty_for_every_hero_even_in_a_party_with_one_inside() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Priest);
    assert_eq!(w.maps[VAULT].min_level, 20);
    w.players.get_mut(&1).unwrap().character.level = 19;
    step_on_the_stairs(&mut w, 1);
    assert_eq!(zone_of(&w, 1), SKALD, "level 19 stays out");
    let told = drain(&mut rx);
    assert!(
        told.iter()
            .any(|v| v["type"] == "error" && v["text"].as_str().unwrap().contains("level 20")),
        "{told:?}"
    );
    assert!(!w.instances[0].active, "and wakes nothing");
    // A level-20 hero goes in; their level-19 party mate still cannot follow.
    take_the_stairs(&mut w, 2);
    assert_eq!(zone_of(&w, 2), VAULT);
    let (a, b) = (
        w.players[&2].character.id.clone(),
        w.players[&1].character.id.clone(),
    );
    w.party_add_mercenary(&a, &w.players[&1].character.clone())
        .unwrap();
    assert_eq!(w.party_mates(&b).len(), 2);
    w.time += 1.;
    step_on_the_stairs(&mut w, 1);
    assert_eq!(zone_of(&w, 1), SKALD);
    w.players.get_mut(&1).unwrap().character.level = 20;
    w.time += 1.;
    step_on_the_stairs(&mut w, 1);
    assert_eq!(zone_of(&w, 1), VAULT, "level 20 follows into the same copy");
}

#[test]
fn instance_pursuit_keeps_every_kind_aggroed_across_the_winding_dungeon() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.god_mode = true;
    let start = w.slimes[first(&w, VAULT, "thrall")].point();
    let end = w.slimes[first(&w, VAULT, "hollowking")].point();
    place(&mut w, 1, VAULT, end);
    for s in &mut w.slimes {
        s.dead = true;
        s.respawn = 1e9;
    }
    for kind in [
        "thrall",
        "archer",
        "acolyte",
        "gatewarden",
        "choir",
        "colossus",
        "hollowking",
    ] {
        let id = first(&w, VAULT, kind);
        let s = &mut w.slimes[id];
        s.dead = false;
        s.x = start.x;
        s.y = start.y;
        s.hx = start.x;
        s.hy = start.y;
        s.target = Some(1);
        s.state = "chase".into();
        let reach = Slime::ranged(kind).map_or(3., |r| r.range + 0.5);
        for _ in 0..12000 {
            w.time += TICK;
            w.update_slime(id);
            let s = &w.slimes[id];
            assert_eq!(s.target, Some(1), "{kind} dropped its target");
            assert_ne!(s.state, "return", "{kind} leashed home");
            let mut collision = s.point();
            w.maps[VAULT].collide(&mut collision, s.r);
            assert!(
                collision.distance(s.point()) < 1e-6,
                "{kind} crossed a wall"
            );
            if s.point().distance(end) < reach {
                break;
            }
        }
        assert!(
            w.slimes[id].point().distance(end) < reach,
            "{kind} stopped at {:?}, target {end:?}",
            w.slimes[id].point()
        );
        w.slimes[id].dead = true;
    }
}

#[test]
fn instance_pursuit_retargets_after_death_but_never_crosses_private_copies() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let _rx2 = join(&mut w, 2, Class::Mage);
    let id = first(&w, VAULT, "thrall");
    let end = w.slimes[first(&w, VAULT, "hollowking")].point();
    place(&mut w, 1, VAULT, end);
    place(&mut w, 2, VAULT, end);
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    w.slimes[id].target = Some(1);
    w.slimes[id].state = "chase".into();
    w.update_slime(id);
    assert_eq!(
        w.slimes[id].target,
        Some(2),
        "the living ally is pursued beyond awareness range"
    );
    place(&mut w, 2, 6, end);
    w.update_slime(id);
    assert_eq!(w.slimes[id].target, None);
    assert_eq!(w.slimes[id].state, "return");
}

#[test]
fn outdoor_enemies_still_drop_aggro_at_their_normal_leash() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let id = first(&w, 0, "green");
    let home = w.slimes[id].point();
    place(
        &mut w,
        1,
        0,
        Point {
            x: home.x + 12.,
            y: home.y,
        },
    );
    w.slimes[id].target = Some(1);
    w.slimes[id].state = "chase".into();
    w.update_slime(id);
    assert_eq!(w.slimes[id].target, None);
    assert_eq!(w.slimes[id].state, "return");
}

#[test]
fn a_cleared_instance_dismisses_its_mercenaries_after_the_final_kills_loot_is_created() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let _rx2 = join(&mut w, 2, Class::Warrior);
    w.god_mode = true;
    let stone = w.maps[SKALD]
        .npcs
        .iter()
        .find(|n| n.id == "city_meetingstone")
        .unwrap()
        .clone();
    for session in [1, 2] {
        place(
            &mut w,
            session,
            SKALD,
            Point {
                x: stone.x,
                y: stone.y + 1.,
            },
        );
        w.players.get_mut(&session).unwrap().character.gold = 1000;
        w.time += 0.6;
        w.interact(session, "city_meetingstone", Some("merc_priest"));
        take_the_stairs(&mut w, session);
        w.update_mercenaries();
    }
    assert_eq!(zone_of(&w, 1), VAULT);
    assert_eq!(zone_of(&w, 2), 6);
    let owner = w.players[&1].character.id.clone();
    let merc = *w
        .players
        .iter()
        .find(|(_, p)| p.merc.as_ref() == Some(&owner))
        .unwrap()
        .0;
    // A completed unrelated quest must not end a Meeting Stone contract.
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .quests
        .push(QuestProgress {
            id: "crags_cinderlord".into(),
            counts: vec![1],
            ..Default::default()
        });
    w.update_mercenaries();
    assert!(w.players.contains_key(&merc));
    let boss = first(&w, VAULT, "gatewarden");
    let at = w.slimes[boss].point();
    place(
        &mut w,
        1,
        VAULT,
        Point {
            x: at.x - 2.,
            y: at.y,
        },
    );
    place(
        &mut w,
        merc,
        VAULT,
        Point {
            x: at.x - 3.,
            y: at.y,
        },
    );
    w.slimes[boss].hp = 1.;
    w.hit_slime(boss, merc, 100., false);
    w.update_mercenaries();
    assert!(
        w.players.contains_key(&merc),
        "an earlier boss does not clear the instance"
    );
    let king = first(&w, VAULT, "hollowking");
    let at = w.slimes[king].point();
    place(
        &mut w,
        1,
        VAULT,
        Point {
            x: at.x - 2.,
            y: at.y,
        },
    );
    place(
        &mut w,
        merc,
        VAULT,
        Point {
            x: at.x - 3.,
            y: at.y,
        },
    );
    drain(&mut rx);
    w.slimes[king].hp = 1.;
    w.hit_slime(king, merc, 100., false);
    assert!(w.instance_cleared(VAULT));
    assert_eq!(w.players[&1].character.kills, 2);
    let starts = drain(&mut rx)
        .into_iter()
        .filter(|v| {
            v["type"] == "roll"
                && v["op"] == "start"
                && v["item"]
                    .as_str()
                    .is_some_and(|s| s.ends_with("_l20_vault"))
        })
        .count();
    assert_eq!(
        starts, 2,
        "final loot rolls exist before mercenary dismissal"
    );
    // A dead mercenary departs too; the other private party remains hired.
    w.players.get_mut(&merc).unwrap().character.hp = 0.;
    w.update_mercenaries();
    assert!(!w.players.contains_key(&merc));
    assert_eq!(mercs_of(&w).len(), 1);
    assert_eq!(mercs_of(&w)[0].character.zone, 6);
    assert_eq!(w.party_mates(&owner).len(), 1);
}

#[test]
fn instance_pursuit_routes_a_ranged_enemy_around_a_close_wall_before_shooting() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.god_mode = true;
    let id = first(&w, VAULT, "archer");
    let radius = w.slimes[id].r;
    // A connected room split by a short wall: the player is in bow range, but the path goes around the end.
    let mut wall = w.maps[VAULT].objects[0].clone();
    wall.x = 40.;
    wall.y = 40.;
    wall.width = 1.;
    wall.depth = 8.;
    w.maps[VAULT].objects = vec![wall];
    let start = Point { x: 38.5, y: 40. };
    let end = Point { x: 41.5, y: 40. };
    place(&mut w, 1, VAULT, end);
    for s in &mut w.slimes {
        s.dead = true;
        s.respawn = 1e9;
    }
    let s = &mut w.slimes[id];
    s.dead = false;
    s.x = start.x;
    s.y = start.y;
    s.target = Some(1);
    s.state = "chase".into();
    assert!(!pursuit::clear_line(&w.maps[VAULT], start, end, radius));
    w.update_slime(id);
    assert_eq!(
        w.slimes[id].state, "chase",
        "a close target behind a wall requires pursuit, not a volley into the wall"
    );
    for _ in 0..6000 {
        w.time += TICK;
        w.update_slime(id);
        assert_eq!(w.slimes[id].target, Some(1));
        if w.slimes[id].state == "windup" {
            break;
        }
    }
    assert_eq!(
        w.slimes[id].state, "windup",
        "the archer follows connected floor until it can shoot"
    );
    assert!(pursuit::clear_line(
        &w.maps[VAULT],
        w.slimes[id].point(),
        end,
        radius
    ));
}
