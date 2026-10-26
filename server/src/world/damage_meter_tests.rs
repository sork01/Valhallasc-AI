//! Meter accounting uses actual hit_slime damage, never player-provided totals.
use super::wyrd_tests::{at, calm, join, place, world};
use super::*;

#[test]
fn damage_meter_separates_hires_caps_overkill_freezes_and_resets_next_pull() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, 46, at(35., 303.));
    let owner = w.players[&1].character.id.clone();
    w.place_mercenary(&owner, Class::Mage, 99, 46, at(35., 303.), true, None)
        .unwrap();
    let merc = *w.players.keys().find(|&&s| s != 1).unwrap();
    let merc_id = w.players[&merc].character.id.clone();
    let enemies: Vec<_> = w
        .spawns
        .iter()
        .enumerate()
        .filter(|(_, s)| s.zone == 46 && !is_boss(&s.kind))
        .take(2)
        .map(|(id, _)| id)
        .collect();
    for &id in &enemies {
        w.slimes[id] = Slime::with_level(id, &w.spawns[id], 99);
        w.slimes[id].hp = 1000.;
    }
    let row = |view: &Value, id: &str| {
        view["rows"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["id"] == id)
            .unwrap()
            .clone()
    };
    assert_eq!(row(&w.damage_meter_view(46), &merc_id)["damage"], 0.);
    w.time = 2.;
    assert_eq!(w.hit_slime(enemies[0], 1, 100., false), 100.);
    w.cur_skill = "fireball".into();
    assert_eq!(w.hit_slime(enemies[0], merc, 50., false), 50.);
    assert_eq!(w.hit_slime(enemies[0], 1, 0., false), 0.);
    w.time = 4.;
    w.update_damage_meter();
    let view = w.damage_meter_view(46);
    assert_eq!(row(&view, &owner)["damage"], 100.);
    assert_eq!(row(&view, &owner)["dps"], 50.);
    assert_eq!(row(&view, &merc_id)["damage"], 50.);
    assert_eq!(row(&view, &merc_id)["dps"], 25.);
    assert_eq!(row(&view, &merc_id)["hired"], true);
    w.slimes[enemies[0]].hp = 20.;
    assert_eq!(w.hit_slime(enemies[0], 1, 5000., false), 20.);
    w.time = 6.;
    w.update_damage_meter();
    let last = w.damage_meter_view(46);
    assert_eq!(last["active"], false);
    assert_eq!(row(&last, &owner)["damage"], 120.);
    w.time = 100.;
    w.update_damage_meter();
    assert_eq!(w.damage_meter_view(46), last);
    assert_eq!(w.hit_slime(enemies[1], merc, 75., false), 75.);
    let next = w.damage_meter_view(46);
    assert_eq!(next["active"], true);
    assert_eq!(row(&next, &owner)["damage"], 0.);
    assert_eq!(row(&next, &merc_id)["damage"], 75.);
    assert!(
        w.damage_meter_view(107)["rows"]
            .as_array()
            .unwrap()
            .is_empty(),
        "another copy sees no data"
    );
}

#[test]
fn damage_meter_never_counts_dead_or_hidden_attackers() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let enemy = w
        .slimes
        .iter()
        .position(|s| s.zone == 0 && !s.dead)
        .unwrap();
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    assert_eq!(w.hit_slime(enemy, 1, 100., false), 0.);
    assert_eq!(w.damage_meter_view(0)["rows"][0]["damage"], 0.);
    let p = w.players.get_mut(&1).unwrap();
    p.character.hp = p.character.max_hp();
    p.character.gm = true;
    p.hidden = true;
    assert!(
        w.damage_meter_view(0)["rows"]
            .as_array()
            .unwrap()
            .is_empty()
    );
    let p = w.players.get(&1).unwrap();
    w.damage_meter.record(1., 0, enemy, p, 100.);
    w.time = 5.;
    assert!(
        w.damage_meter_view(0)["rows"]
            .as_array()
            .unwrap()
            .is_empty()
    );
}
