//! `AGGRO-LEVEL` (`docs/aggro-level.md`): an open-world monster notices a hero from further away the more levels it
//! is above them, and from nearer the more levels it is below.
use super::wyrd_tests::{at, calm, join, place, world};
use super::*;

const CRAGS: usize = 1;

#[test]
fn the_radius_follows_the_level_gap_within_its_limits() {
    let base = 10.;
    assert_eq!(aggro_radius(base, 20, 20), base);
    assert!((aggro_radius(base, 15, 10) - base * 1.6).abs() < 1e-9);
    assert!((aggro_radius(base, 10, 15) - base * 0.4).abs() < 1e-9);
    assert_eq!(aggro_radius(base, 60, 10), base * 2.0, "capped above");
    assert_eq!(aggro_radius(base, 1, 90), base * 0.35, "capped below");
    // The floor: 3 tiles, or the whole radius when that is already smaller.
    assert_eq!(aggro_radius(5., 1, 90), 3.);
    assert_eq!(aggro_radius(2., 1, 90), 2.);
    assert_eq!(aggro_radius(2., 90, 1), 4.);
}

/// Whether a fresh `green` of `monster_level` locks on to a hero of `hero_level` standing `distance` tiles away.
fn notices(monster_level: u32, hero_level: u32, distance: f64) -> bool {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    let home = w
        .spawns
        .iter()
        .find(|s| s.zone == CRAGS)
        .map(|s| Point { x: s.x, y: s.y })
        .expect("a Crags spawn");
    w.maps[CRAGS].objects.clear();
    w.slimes[0] = Slime::with_level(
        0,
        &SlimeSpawn {
            ambush: None,
            kind: "green".into(),
            zone: CRAGS,
            x: home.x,
            y: home.y,
        },
        monster_level,
    );
    place(&mut w, 1, CRAGS, at(home.x + distance, home.y));
    w.players.get_mut(&1).unwrap().character.level = hero_level;
    w.update_slime(0);
    w.slimes[0].target == Some(1)
}

#[test]
fn a_higher_level_monster_notices_from_further_and_a_lower_one_from_nearer() {
    let base = Slime::attack_profile("green").3;
    assert!(base > 4., "the test needs room to stand between the radii");
    // Same level: the old radius.
    assert!(notices(10, 10, base * 0.9));
    assert!(!notices(10, 10, base * 1.1));
    // Eight levels above (x1.96): it sees a hero well beyond the old radius.
    assert!(notices(18, 10, base * 1.6));
    assert!(!notices(10, 10, base * 1.6));
    // Eight levels below (x0.35): it ignores a hero it used to notice, but not one right next to it.
    assert!(!notices(10, 18, base * 0.6));
    assert!(notices(10, 18, 2.));
}
