use super::wyrd_tests::{at, calm, join, place, world};
use super::*;
#[test]
fn mounts_use_160_percent_actual_travel_for_every_mount_and_class() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    for class in [
        Class::Warrior,
        Class::Mage,
        Class::Assassin,
        Class::Priest,
        Class::Hunter,
    ] {
        for mount in crate::model::MOUNTS.iter() {
            assert_eq!(mount.speed, 1.6);
            let mut distances = Vec::new();
            for riding in [false, true] {
                place(&mut w, 1, 4, at(80., 140.));
                let p = w.players.get_mut(&1).unwrap();
                p.character.look.class = class;
                p.character.grant_mount(mount.id);
                p.character.select_mount(mount.id).unwrap();
                p.character.mounted = riding;
                p.input = at(0., -1.);
                p.goal = None;
                p.target = None;
                p.attack = 0.;
                p.daze = 0.;
                p.root = 0.;
                p.stun = 0.;
                p.buffs.clear();
                for _ in 0..20 {
                    w.time += TICK;
                    w.message(1, ClientMessage::Input { dx: 0., dy: -1. });
                    w.update_player(1);
                }
                distances.push(w.players[&1].character.point().distance(at(80., 140.)));
            }
            assert!(
                (distances[1] / distances[0] - 1.6).abs() < 1e-9,
                "{} {:?}: {:?}",
                mount.id,
                class,
                distances
            );
        }
    }
}
