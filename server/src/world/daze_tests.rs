//! Rear-hit daze, using real damage and movement paths in a quiet private world.
use super::wyrd_tests::{at, calm, join, place, world};
use super::*;

fn setup() -> (World, mpsc::Receiver<Value>) {
    let mut w = world();
    calm(&mut w);
    let rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, 0, at(25., 25.));
    w.time = 10.;
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .attributes
        .dexterity = 20;
    assert!(!w.maps[0].in_city(at(25., 25.)));
    w.players.get_mut(&1).unwrap().face = at(1., 0.);
    (w, rx)
}

#[test]
fn daze_only_landed_rear_enemy_hits_roll_forty_percent_and_refresh_four_seconds() {
    let (mut w, _rx) = setup();
    let dodge = w.players[&1].character.dodge_chance();
    // Seeds 2 and 1 both get past dodge; their next rolls are .160 and .753 respectively.
    assert!(dodge < 0.345);
    for (seed, from, enemy, expected) in [
        (2, at(24., 25.), "slime", 4.),
        (1, at(24., 25.), "slime", 0.),
        (2, at(26., 25.), "slime", 0.),
        (2, at(25., 26.), "slime", 0.),
        (2, at(25., 25.), "slime", 0.),
        (2, at(24., 25.), "", 0.),
    ] {
        w.rng = seed;
        let p = w.players.get_mut(&1).unwrap();
        p.daze = 0.;
        p.last_hurt = 0.;
        p.character.hp = p.character.max_hp();
        w.hurt_player_by(1, 1., from, enemy, 1);
        assert_eq!(
            w.players[&1].daze, expected,
            "seed {seed}, {from:?}, {enemy}"
        );
    }
    // Probe rolls immediately below/above 40%, independently finding LCG input seeds.
    for (low, high, expected) in [(0.399, 0.4, 4.), (0.4, 0.401, 0.)] {
        let seed = (1_u64..100_000)
            .find(|seed| {
                let first = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                let next = first.wrapping_mul(6364136223846793005).wrapping_add(1);
                let roll = (next >> 32) as f64 / 4294967296.;
                (first >> 32) as f64 / 4294967296. > dodge && roll >= low && roll < high
            })
            .unwrap();
        w.rng = seed;
        let p = w.players.get_mut(&1).unwrap();
        p.last_hurt = 0.;
        p.daze = 0.;
        w.hurt_player_by(1, 1., at(24., 25.), "slime", 1);
        assert_eq!(w.players[&1].daze, expected);
    }
    w.rng = 2;
    let p = w.players.get_mut(&1).unwrap();
    p.daze = 2.;
    p.last_hurt = 0.;
    w.hurt_player_by(1, 1., at(24., 25.), "slime", 1);
    assert_eq!(w.players[&1].daze, 4., "refresh, never stack duration");
    assert_eq!(w.players[&1].snapshot()["daze"], 4.);
}

#[test]
fn daze_dodge_absorbed_immune_and_lethal_hits_do_not_leave_a_daze() {
    let (mut w, _rx) = setup();
    for mode in ["dodge", "shield", "god", "dash", "dead", "city", "lethal"] {
        place(&mut w, 1, 0, at(25., 25.));
        let p = w.players.get_mut(&1).unwrap();
        p.last_hurt = 0.;
        p.daze = 0.;
        p.god = mode == "god";
        p.dash = if mode == "dash" { 1. } else { 0. };
        p.set_shield = if mode == "shield" { 100. } else { 0. };
        if mode == "dodge" {
            p.buffs.push(Buff {
                id: "test".into(),
                kind: BuffKind::Dodge,
                amount: 0.95,
                left: 5.,
                time: 5.,
            });
        } else {
            p.buffs.clear();
        }
        if mode == "dead" {
            p.character.hp = 0.;
        }
        if mode == "city" {
            let city = w.maps[0].city.as_ref().unwrap();
            p.character.x = (city.x0 + city.x1) / 2.;
            p.character.y = (city.y0 + city.y1) / 2.;
        }
        w.rng = 2;
        w.hurt_player_by(
            1,
            if mode == "lethal" { 1e9 } else { 1. },
            at(24., 25.),
            "slime",
            1,
        );
        assert_eq!(w.players[&1].daze, 0., "{mode}");
    }
}

#[test]
fn daze_halves_walking_expires_and_does_not_block_attacks_or_dashes() {
    let (mut w, _rx) = setup();
    let travel = |w: &mut World, daze| {
        place(w, 1, 0, at(25., 25.));
        let p = w.players.get_mut(&1).unwrap();
        p.daze = daze;
        p.input = at(1., 0.);
        p.input_at = w.time;
        w.update_player(1);
        w.players[&1].character.x - 25.
    };
    let normal = travel(&mut w, 0.);
    assert!(normal > 0.);
    assert!((travel(&mut w, 4.) / normal - 0.5).abs() < 1e-8);
    let p = w.players.get_mut(&1).unwrap();
    p.stop();
    p.daze = 4.;
    for _ in 0..79 {
        w.update_player(1);
    }
    assert!(w.players[&1].daze > 0.);
    w.update_player(1);
    assert_eq!(w.players[&1].daze, 0.);
    let p = w.players.get_mut(&1).unwrap();
    p.daze = 4.;
    p.cooldown = 0.;
    w.message(1, ClientMessage::Attack { fx: 1., fy: 0. });
    assert!(w.players[&1].attack > 0.);
    let p = w.players.get_mut(&1).unwrap();
    p.character.level = 8;
    p.character.reset_resource();
    p.character.change_resource(100.);
    w.use_skill(1, "battlecry", at(1., 0.));
    assert!(w.players[&1].buffs.iter().any(|b| b.id == "battlecry"));
    let p = w.players.get_mut(&1).unwrap();
    p.attack = 0.;
    p.dash = 0.1;
    p.dash_direction = at(1., 0.);
    p.dash_speed = 10.;
    let before = p.character.x;
    w.update_player(1);
    assert!((w.players[&1].character.x - before - 10. * TICK).abs() < 1e-8);
}
