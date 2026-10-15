//! Enemies in zones nobody is in are not simulated (they rest at their post), but dead ones still respawn and a zone
//! that gets a visitor wakes up at once. The random-number sequence is the same as when every enemy was simulated.
use super::wyrd_tests::{at, join, place, world};
use super::*;

const CRAGS: usize = 1;

fn crags_positions(w: &World) -> Vec<(f64, f64)> {
    w.slimes
        .iter()
        .filter(|s| s.zone == CRAGS)
        .map(|s| (s.x, s.y))
        .collect()
}

#[test]
fn an_empty_zone_does_not_move_but_a_visited_one_does() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, 0, at(60., 60.));
    let before = crags_positions(&w);
    assert!(!before.is_empty());
    for _ in 0..120 {
        w.step();
    }
    assert_eq!(
        crags_positions(&w),
        before,
        "nobody is in the Crags, so nothing there moves"
    );
    // A visitor wakes the zone: the same enemies wander again.
    let arrival = w.maps[CRAGS].spawn;
    place(&mut w, 1, CRAGS, arrival);
    for _ in 0..200 {
        w.step();
    }
    assert_ne!(
        crags_positions(&w),
        before,
        "with a visitor the enemies move"
    );
}

#[test]
fn dead_enemies_in_an_empty_zone_still_respawn() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, 0, at(60., 60.));
    let id = w.slimes.iter().position(|s| s.zone == CRAGS).unwrap();
    w.slimes[id].dead = true;
    w.slimes[id].respawn = 1.;
    for _ in 0..(1.5 / TICK) as usize {
        w.step();
    }
    assert!(!w.slimes[id].dead, "the timer ran while nobody was there");
}

#[test]
fn an_enemy_that_is_chasing_keeps_being_simulated_in_an_empty_zone() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, 0, at(60., 60.));
    let id = w.slimes.iter().position(|s| s.zone == CRAGS).unwrap();
    w.slimes[id].state = "return".into();
    assert!(!w.slimes[id].is_dormant());
    w.slimes[id].state = "idle".into();
    w.slimes[id].target = Some(9);
    assert!(!w.slimes[id].is_dormant());
    w.slimes[id].target = None;
    assert!(w.slimes[id].is_dormant());
}

#[test]
fn skipping_idle_enemies_keeps_the_random_sequence_of_the_full_simulation() {
    // Every simulated or skipped enemy accounts for exactly two draws per tick, as before the skipping existed.
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, 0, at(60., 60.));
    for s in w.slimes.iter_mut().filter(|s| s.zone != CRAGS) {
        s.dead = true;
        s.respawn = 1e9;
    }
    let simulated = w.slimes.iter().filter(|s| !w.zone_idle(s.zone)).count() as u64;
    w.rng = 99;
    let mut expected = w.rng;
    for _ in 0..30 {
        for _ in 0..simulated * 2 {
            expected = expected.wrapping_mul(6364136223846793005).wrapping_add(1);
        }
        w.step();
    }
    assert_eq!(w.rng, expected, "two draws per enemy per tick");
}
