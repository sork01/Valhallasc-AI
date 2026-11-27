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

/// Opposite sides of an actual authored Ran's Deep wall, with room for both actors.
pub(super) fn deep_wall_pair(w: &World) -> (Point, Point) {
    let map = &w.maps[8];
    map.objects.iter().filter(|o| o.width > 0. && o.depth > 0.).find_map(|o| {
        let (a, b) = if o.width <= o.depth {
            (at(o.x - o.width / 2. - 2., o.y), at(o.x + o.width / 2. + 2., o.y))
        } else {
            (at(o.x, o.y - o.depth / 2. - 2.), at(o.x, o.y + o.depth / 2. + 2.))
        };
        let free = |p: Point| {
            let mut q = p;
            map.collide(&mut q, 1.6);
            q.distance(p) < 1e-8 && !map.in_city(p)
        };
        (a.distance(b) < 8. && free(a) && free(b) && !map.line_clear(a, b, 0.05)).then_some((a, b))
    }).expect("an authored wall with free floor on both sides")
}

#[test]
fn aggro_level_deep_walls_block_notice_and_stale_combat_but_open_floor_still_aggros() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    let (monster, hero) = deep_wall_pair(&w);
    place(&mut w, 1, 8, hero);
    w.players.get_mut(&1).unwrap().character.level = 35;
    w.slimes[0] = Slime::with_level(0, &SlimeSpawn {
        ambush: None, kind: "moray".into(), zone: 8, x: monster.x, y: monster.y,
    }, 35);
    w.update_slime(0);
    assert_eq!(w.slimes[0].target, None, "a nearby hero behind the wall is unseen");
    for state in ["chase", "windup", "lunge"] {
        w.slimes[0].target = Some(1);
        w.slimes[0].state = state.into();
        w.players.get_mut(&1).unwrap().combat_left = 5.;
        for _ in 0..102 { w.update_resource(1); }
        assert_eq!(w.players[&1].combat_left, 0., "{state} through a wall must not renew combat");
    }
    w.slimes[0].kind = "siren".into();
    w.slimes[0].state = "chase".into();
    w.slimes[0].atk_cd = 0.;
    w.update_slime(0);
    assert_ne!(w.slimes[0].state, "windup", "even an existing ranged target cannot be attacked through the wall");
    // With sight restored, the same monster engages and refreshes combat.
    w.maps[8].objects.clear();
    w.slimes[0].target = None;
    w.slimes[0].state = "idle".into();
    w.update_slime(0);
    assert_eq!(w.slimes[0].target, Some(1));
    w.update_resource(1);
    assert_eq!(w.players[&1].combat_left, 5.);
}
