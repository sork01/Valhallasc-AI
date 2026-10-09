//! Three Cathedral wings: collision, level gates, private copies, encounter rewards and complete clears.
use super::wyrd_tests::{at, blocked, drain, flood, join, place, reached, world};
use super::*;
use std::collections::BTreeSet;

const WINGS: [usize; 3] = [10, 11, 12];

#[test]
fn cathedral_pursuit_grids_match_authoritative_collision_for_walls_columns_and_void() {
    let w = world();
    for zone in WINGS {
        for radius in [0.4, 0.7] {
            assert!(
                pursuit::grid_matches_collision(&w.maps[zone], radius),
                "wing {zone}, radius {radius}"
            );
        }
    }
}

fn enter(w: &mut World, session: u64, wing: usize) {
    let p = w.maps[9]
        .portals
        .iter()
        .find(|p| p.to == wing)
        .unwrap()
        .clone();
    place(w, session, 9, at(p.x, p.y));
    w.time += 1.;
    w.use_portal(session);
}

#[test]
fn cathedral_three_wings_have_exact_levels_four_unique_bosses_and_distinct_floor_plans() {
    let w = world();
    let mut bosses = BTreeSet::new();
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    for (zone, level) in WINGS.into_iter().zip([40, 45, 50]) {
        let m = &w.maps[zone];
        assert_eq!(
            (m.levels, m.min_level, m.players, m.copies),
            (Some([level, level]), level, 5, 4)
        );
        assert_eq!(m.slimes.len(), 20);
        assert!(m.city.is_none());
        let kinds: Vec<_> = m.slimes.iter().filter(|s| is_boss(&s.kind)).collect();
        assert_eq!(kinds.len(), 4);
        for s in kinds {
            assert!(bosses.insert(s.kind.clone()), "boss reused across wings");
        }
        assert!(m.slimes.iter().any(|s| s.kind == m.final_boss));
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == zone)
                .all(|s| s.level == level && !s.dead)
        );
        assert_eq!(w.instances.iter().filter(|i| i.template == zone).count(), 4);
        assert!(raw["zones"][zone - 1]["cathedralWing"].is_string());
    }
    assert_eq!(bosses.len(), 12);
    assert_ne!(raw["zones"][9]["rooms"], raw["zones"][10]["rooms"]);
    assert_ne!(raw["zones"][10]["rooms"], raw["zones"][11]["rooms"]);
    assert_eq!(w.maps.iter().filter(|m| m.template.is_none()).count(), 20);
}

#[test]
fn cathedral_wing_specific_enemies_never_spawn_in_other_wings_or_outdoors() {
    let w = world();
    for (zone, kind) in WINGS
        .into_iter()
        .zip(["tideleech", "reliccrab", "abysszealot"])
    {
        assert_eq!(
            w.maps[zone]
                .slimes
                .iter()
                .filter(|s| s.kind == kind)
                .count(),
            4
        );
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.kind == kind)
                .all(|s| w.public_zone(s.zone) == zone)
        );
    }
    for zone in WINGS {
        assert_eq!(
            w.maps[zone]
                .slimes
                .iter()
                .filter(|s| s.kind == "tidetemplar")
                .count(),
            8
        );
        assert_eq!(
            w.maps[zone]
                .slimes
                .iter()
                .filter(|s| s.kind == "tidecantor")
                .count(),
            4
        );
    }
}

#[test]
fn cathedral_every_spawn_and_exit_is_reachable_on_real_collision_ground_and_nothing_walks_outside_floor()
 {
    let w = world();
    let raw: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    for zone in WINGS {
        let m = &w.maps[zone];
        let seen = flood(m, &blocked(m, &[]), m.spawn);
        for s in &m.slimes {
            let p = at(s.x, s.y);
            let mut c = p;
            m.collide(&mut c, 0.3 * Slime::stats(&s.kind).3);
            assert!(c.distance(p) < 1e-6, "{} at {zone} collides", s.kind);
            assert!(reached(m, &seen, p), "{} unreachable", s.kind);
            assert!(p.distance(m.spawn) > 12.);
        }
        for p in &m.portals {
            assert!(reached(m, &seen, at(p.x, p.y)));
        }
        let rects = raw["zones"][zone - 1]["rooms"].as_array().unwrap();
        for y in 0..m.size as usize {
            for x in 0..m.size as usize {
                if !seen[y * m.size as usize + x] {
                    continue;
                }
                assert!(
                    rects
                        .iter()
                        .any(|r| x as f64 + 0.5 >= r[0].as_f64().unwrap()
                            && x as f64 + 0.5 < r[2].as_f64().unwrap()
                            && y as f64 + 0.5 >= r[1].as_f64().unwrap()
                            && y as f64 + 0.5 < r[3].as_f64().unwrap()),
                    "reachable void in wing {zone}: {x},{y}"
                );
            }
        }
    }
}

#[test]
fn cathedral_portals_are_clear_paired_safe_and_cannot_bounce_or_bypass_the_level_gate() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    for (zone, level) in WINGS.into_iter().zip([40, 45, 50]) {
        w.players.get_mut(&1).unwrap().character.level = level - 1;
        enter(&mut w, 1, zone);
        assert_eq!(w.players[&1].character.zone, 9);
        assert!(drain(&mut rx).iter().any(|v| v["type"] == "error"));
        w.players.get_mut(&1).unwrap().character.level = level;
        enter(&mut w, 1, zone);
        assert_eq!(w.public_zone(w.players[&1].character.zone), zone);
        let c = w.players[&1].character.clone();
        let arrival = c.point();
        assert!(
            w.maps[c.zone]
                .portals
                .iter()
                .all(|p| arrival.distance(at(p.x, p.y)) > p.r + 0.5)
        );
        w.time += 1.;
        w.use_portal(1);
        assert_eq!(w.players[&1].character.point().distance(arrival), 0.);
        let p = w.maps[c.zone].portals[0].clone();
        let actual = w.players[&1].character.zone;
        place(&mut w, 1, actual, at(p.x, p.y));
        w.time += 1.;
        w.use_portal(1);
        assert_eq!(w.players[&1].character.zone, 9);
        let back = w.players[&1].character.point();
        let mut q = back;
        w.maps[9].collide(&mut q, PLAYER_RADIUS);
        assert!(q.distance(back) < 1e-6);
        assert!(
            w.maps[9]
                .portals
                .iter()
                .all(|p| back.distance(at(p.x, p.y)) > p.r + 0.5)
        );
    }
}

#[test]
fn cathedral_parties_share_a_copy_strangers_get_another_and_each_wing_allocates_independently() {
    let mut w = world();
    let _a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Priest);
    let _c = join(&mut w, 3, Class::Mage);
    let b = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(b),
            name: None,
        },
    );
    w.social(
        2,
        SocialCommand::PartyAccept {
            id: w.players[&1].character.id.clone(),
        },
    );
    for session in [1, 2, 3] {
        w.players.get_mut(&session).unwrap().character.level = 50;
    }
    for zone in WINGS {
        enter(&mut w, 1, zone);
        enter(&mut w, 2, zone);
        enter(&mut w, 3, zone);
        assert_eq!(w.players[&1].character.zone, w.players[&2].character.zone);
        assert_ne!(w.players[&1].character.zone, w.players[&3].character.zone);
        assert_eq!(w.public_zone(w.players[&3].character.zone), zone);
        let copy = w.players[&3].character.zone;
        let point = w.players[&3].character.point();
        w.run_debug(
            3,
            DebugCommand::Teleport {
                zone,
                x: point.x,
                y: point.y,
            },
        )
        .unwrap();
        assert_eq!(
            w.players[&3].character.zone, copy,
            "moving within a solo wing must keep its copy"
        );
    }
}

#[test]
fn cathedral_encounters_have_materials_fixed_levels_distinct_profiles_and_guaranteed_level_appropriate_loot()
 {
    let w = world();
    for e in crate::cathedral::ENEMIES.iter() {
        assert_eq!(Slime::default_level(&e.kind), e.level);
        assert!(Slime::fixed_level(&e.kind));
        assert!(is_elite(&e.kind));
        assert_eq!(is_boss(&e.kind), e.boss);
        assert!(item(material(&e.kind)).is_some());
        assert!(e.stats[0] > 20000. && e.stats[1] >= 800.);
        for s in w.slimes.iter().filter(|s| s.kind == e.kind) {
            assert_eq!(s.xp, enemy_xp(s.level) * if e.boss { 12 } else { 1 });
            assert!(s.gold >= 850);
        }
        if e.boss {
            for slots in boss_slots(&e.kind) {
                for n in 0..20 {
                    let i = boss_piece_for(&e.kind, slots, n as f64 / 20.).unwrap();
                    assert_eq!(i.rarity, "rare");
                    assert_eq!(i.required_level, e.level);
                    assert_eq!(i.source.as_deref(), e.loot_source.as_deref());
                    assert!(i.source.as_deref().unwrap().starts_with("cathedral_"));
                    assert!(slots.contains(&i.kind.as_str()));
                }
            }
        }
    }
    assert!(
        Slime::ranged("glasscantor").unwrap().speed > Slime::ranged("choirmother").unwrap().speed
    );
    assert!(Slime::slam_radius("tidejudicator") > Slime::slam_radius("bellkeeper"));
    assert!(Slime::attack_profile("pearlwidow").2 > Slime::attack_profile("rootabbot").2);
}

#[test]
fn cathedral_final_boss_first_does_not_clear_but_all_four_bosses_open_only_their_own_exit() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 50;
    for zone in WINGS {
        enter(&mut w, 1, zone);
        let mut ids: Vec<_> = w
            .slimes
            .iter()
            .filter(|s| s.zone == zone && is_boss(&s.kind))
            .map(|s| s.id)
            .collect();
        ids.sort_by_key(|id| w.slimes[*id].kind != w.maps[zone].final_boss);
        for (n, id) in ids.into_iter().enumerate() {
            let point = w.slimes[id].point();
            place(&mut w, 1, zone, point);
            let xp = w.slimes[id].xp;
            let before = lifetime_xp(&w.players[&1].character);
            w.hit_slime(id, 1, 1e9, false);
            let encounter = crate::cathedral::enemy(&w.slimes[id].kind).unwrap();
            let loot: Vec<_> = w
                .drops
                .iter()
                .filter(|d| d.zone == zone && d.point().distance(point) < 1.)
                .filter_map(|d| d.item.as_deref().and_then(item))
                .filter(|i| i.source.as_deref() == encounter.loot_source.as_deref())
                .collect();
            assert_eq!(
                loot.len(),
                boss_slots(&encounter.kind).len(),
                "guaranteed exclusive pieces from the real kill path"
            );
            if w.slimes[id].kind == w.maps[zone].final_boss {
                assert!(
                    loot.len() >= 2,
                    "the finale must drop at least two blue items"
                );
                assert!(loot.iter().all(|i| i.rarity == "rare"));
            }
            assert!(loot.iter().all(|i| i.required_level == encounter.level));
            assert!(w.slimes[id].dead && w.slimes[id].respawn > 1e8);
            assert_eq!(w.instance_cleared(zone), n == 3);
            assert_eq!(lifetime_xp(&w.players[&1].character), before + xp as u64);
            assert!(
                w.drops
                    .iter()
                    .any(|d| d.zone == zone
                        && d.item.as_deref() == Some(material(&w.slimes[id].kind)))
            );
        }
        assert_eq!(
            drain(&mut rx)
                .iter()
                .filter(|v| v["kind"] == "cleared")
                .count(),
            1
        );
        let other = w
            .instances
            .iter()
            .find(|i| i.template == zone && i.zone != zone)
            .unwrap()
            .zone;
        assert!(!w.instance_cleared(other));
    }
}

#[test]
fn cathedral_empty_copy_resets_bosses_loot_exit_and_shared_trash_keeps_the_wing_level() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 50;
    for zone in WINGS {
        enter(&mut w, 1, zone);
        let ids: Vec<_> = w
            .slimes
            .iter()
            .filter(|s| s.zone == zone && is_boss(&s.kind))
            .map(|s| s.id)
            .collect();
        for id in ids {
            w.hit_slime(id, 1, 1e9, false);
        }
        assert!(w.instance_cleared(zone));
        place(&mut w, 1, 9, at(96., 35.));
        w.update_instances();
        assert!(!w.instance_cleared(zone) && w.zone_idle(zone));
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == zone)
                .all(|s| !s.dead && s.hp == s.max_hp && s.level == w.maps[zone].min_level)
        );
        assert!(!w.drops.iter().any(|d| d.zone == zone));
    }
}

struct Run {
    won: bool,
    secs: f64,
    deaths: usize,
    left: f64,
    /// The lowest health fraction any member of the party reached (the healer's work).
    low: f64,
}
/// A trained wing-level warrior hirer with `classes` rented at the Meeting Stone, all standing `lead` units from the
/// middle of `ids`' enemies, fights until they are all down, the party is down, or `limit` seconds pass. Everything
/// else in the dungeon is out of the way.
fn fight(
    zone: usize,
    classes: &[&str],
    ids: &[usize],
    from: Point,
    limit: f64,
    seed: u64,
) -> (World, Run) {
    let mut w = world();
    w.rng = seed;
    let level = w.maps[zone].min_level;
    let potion = crate::items::best_tier("health_potion", level)
        .unwrap()
        .id
        .clone();
    let mut rx = join(&mut w, 1, Class::Warrior);
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = level;
        c.gold = 5000;
        c.attributes.strength = (level - 1) * 2;
        c.attributes.stamina = (level - 1) / 2;
        c.attributes.accuracy = 20;
        c.add_item(&potion, 3);
    }
    let stone = w.maps[9]
        .npcs
        .iter()
        .find(|n| n.id == "nacre_stone")
        .unwrap()
        .clone();
    place(
        &mut w,
        1,
        9,
        Point {
            x: stone.x,
            y: stone.y + 1.,
        },
    );
    for class in classes {
        w.time += 0.6;
        w.interact(1, "nacre_stone", Some(&format!("merc_{class}")));
    }
    assert_eq!(
        w.players.values().filter(|p| p.merc.is_some()).count(),
        classes.len()
    );
    enter(&mut w, 1, zone);
    for s in w.slimes.iter_mut().filter(|s| !ids.contains(&s.id)) {
        s.dead = true;
        s.respawn = 1e9;
    }
    place(&mut w, 1, zone, from);
    for (i, p) in w
        .players
        .values_mut()
        .filter(|p| p.merc.is_some())
        .enumerate()
    {
        p.character.x = from.x + 1. + i as f64 * 0.7;
        p.character.y = from.y + 1.;
        p.character.zone = zone;
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
                w.use_item(1, &potion);
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
            place(&mut w, s, zone, from);
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

#[test]
#[ignore = "manual encounter balance probe"]
fn cathedral_balance_probe() {
    let w = world();
    for zone in WINGS {
        for s in w
            .slimes
            .iter()
            .filter(|s| s.zone == zone && is_boss(&s.kind))
        {
            for classes in [
                &["warrior", "priest", "mage", "hunter"][..],
                &["warrior", "priest"][..],
                &[][..],
            ] {
                let (_, r) = fight(zone, classes, &[s.id], at(s.x - 6., s.y), 300., 123);
                println!(
                    "{} L{} party={} won={} time={:.1} deaths={} hp_left={:.0} low={:.2}",
                    s.kind,
                    s.level,
                    classes.len() + 1,
                    r.won,
                    r.secs,
                    r.deaths,
                    r.left,
                    r.low
                );
                if classes.len() == 4 {
                    assert!(
                        r.won && (80.0..=300.0).contains(&r.secs),
                        "{} needs a winnable five-hero fight in 80–300 seconds",
                        s.kind
                    );
                } else if classes.is_empty() || s.kind == w.maps[zone].final_boss {
                    assert!(!r.won, "{} should resist this undersized party", s.kind);
                }
            }
        }
    }
}

fn lifetime_xp(c: &Character) -> u64 {
    (1..c.level).map(|l| xp_to_level(l) as u64).sum::<u64>() + c.xp as u64
}
