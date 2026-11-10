//! `LEAD-SHOES` (`world/leadshoes.rs`): a hero under water is shod in lead, announced once, with no change to their stats.
use super::wyrd_tests::{at, calm, drain, join, place, world};
use super::*;

const MEADOW: usize = 0;

fn announces(rx: &mut mpsc::Receiver<Value>, text: &str) -> usize {
    drain(rx)
        .iter()
        .filter(|m| m["type"] == "announce" && m["text"] == text)
        .count()
}
fn shoe_announces(rx: &mut mpsc::Receiver<Value>) -> usize {
    announces(rx, "Equipping lead shoes")
}

#[test]
fn every_underwater_zone_is_listed_and_the_dry_ones_are_not() {
    let w = world();
    let under: Vec<usize> = (0..w.maps.len())
        .filter(|&z| w.maps[z].underwater())
        .collect();
    // Rán's Deep, Nacrehold, the three Cathedral wings, the Moonwell, the Longship; every private copy of an
    // underwater dungeon too (they are clones of the template, so they keep its theme).
    for zone in [8, 9, 10, 11, 12, 18, 43] {
        assert!(under.contains(&zone), "zone {zone} ({}) is under water", w.maps[zone].name);
    }
    for zone in [0, 1, 4, 7, 13, 17, 19, 44] {
        assert!(!under.contains(&zone), "zone {zone} ({}) is dry", w.maps[zone].name);
    }
}

#[test]
fn going_down_announces_the_shoes_once_and_surfacing_takes_them_off() {
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, MEADOW, at(20., 20.));
    w.update_lead_shoes();
    assert!(!w.players[&1].shoed);
    assert!(drain(&mut rx).iter().all(|m| m["type"] != "announce"), "dry land says nothing");

    let hp_before = w.players[&1].character.max_hp();
    let gear_before = w.players[&1].character.equipment.clone();
    let look_before = w.players[&1].character.look.clone();
    place(&mut w, 1, 8, at(20., 20.));
    w.update_lead_shoes();
    assert!(w.players[&1].shoed);
    assert_eq!(shoe_announces(&mut rx), 1);
    // Staying down does not repeat it, and nothing about the hero's gear or stats moves.
    w.update_lead_shoes();
    w.update_lead_shoes();
    assert_eq!(shoe_announces(&mut rx), 0);
    let c = &w.players[&1].character;
    assert_eq!(c.max_hp(), hp_before);
    assert_eq!(c.equipment, gear_before);
    assert_eq!(c.look, look_before);
    assert_eq!(w.player_view(1, &w.players[&1])["leadShoes"], true);

    // Between two underwater zones the shoes stay on, with no second announcement.
    place(&mut w, 1, 9, at(20., 20.));
    w.update_lead_shoes();
    assert!(w.players[&1].shoed);
    assert_eq!(shoe_announces(&mut rx), 0);

    place(&mut w, 1, MEADOW, at(20., 20.));
    w.update_lead_shoes();
    assert!(!w.players[&1].shoed);
    assert_eq!(w.player_view(1, &w.players[&1])["leadShoes"], false);
    let surfaced = drain(&mut rx);
    let said = |text: &str| {
        surfaced
            .iter()
            .filter(|m| m["type"] == "announce" && m["text"] == text)
            .count()
    };
    assert_eq!(said("Removing lead shoes"), 1, "surfacing announces the shoes coming off");
    assert_eq!(said("Equipping lead shoes"), 0);
    // Staying dry says nothing more.
    w.update_lead_shoes();
    assert_eq!(announces(&mut rx, "Removing lead shoes"), 0);
    // Going down again puts them on again.
    place(&mut w, 1, 43, at(20., 20.));
    w.update_lead_shoes();
    assert_eq!(shoe_announces(&mut rx), 1);
}
