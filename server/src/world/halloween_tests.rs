use super::wyrd_tests::{at, calm, join, place, world};
use super::*;
fn festival(w: &mut World, unix: u64) {
    w.seasonal.override_unix = Some(unix);
    w.seasonal.next_check = 0.;
    w.update_seasonal();
}
fn accept(w: &mut World, s: u64, npc: &str) {
    let (z, n) = w
        .maps
        .iter()
        .enumerate()
        .find_map(|(z, m)| m.npcs.iter().find(|n| n.id == npc).cloned().map(|n| (z, n)))
        .unwrap();
    place(w, s, z, Point { x: n.x, y: n.y });
    w.time += 1.;
    w.interact(s, npc, Some("quest:accept:halloween_hunt"));
}
fn party(w: &mut World) {
    let owner = w.players[&1].character.id.clone();
    for s in 2..=5 {
        let c = w.players[&s].character.clone();
        w.party_add_mercenary(&owner, &c).unwrap();
    }
}
fn fixture() -> World {
    let mut w = world();
    calm(&mut w);
    festival(&mut w, 1792969200);
    for s in 1..=5 {
        let _rx = join(&mut w, s, Class::Warrior);
        accept(&mut w, s, if s % 2 == 0 { "city_bard" } else { "baker" });
        w.players.get_mut(&s).unwrap().character.level = (s * 5 + u64::from(s == 5)) as u32;
    }
    party(&mut w);
    for s in 1..=5 {
        place(
            &mut w,
            s,
            3,
            if s == 1 {
                at(105., 31.)
            } else {
                at(102. + s as f64 * 0.5, 30.)
            },
        );
    }
    w
}
#[test]
fn halloween_summon_requires_five_and_freezes_average_level_and_membership() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::HALLOWEEN).unwrap();
    let enemy = w.seasonal_hunt.as_ref().unwrap().enemy;
    assert_eq!(w.slimes[enemy].level, 16);
    let hp = w.slimes[enemy].max_hp;
    w.players.get_mut(&5).unwrap().character.level = 99;
    assert_eq!(w.slimes[enemy].max_hp, hp);
    assert!(w.summon_festival(1, seasonal_hunt::HALLOWEEN).is_err());
    let _rx = join(&mut w, 6, Class::Mage);
    place(&mut w, 6, 3, at(105., 25.));
    let before = w.slimes[enemy].hp;
    assert_eq!(w.hit_slime(enemy, 6, 1e9, false), 0.);
    assert_eq!(w.slimes[enemy].hp, before);
    w.time += 901.;
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    w.leave_party(&w.players[&5].character.id.clone());
    assert!(w.summon_festival(1, seasonal_hunt::HALLOWEEN).is_err());
}
#[test]
fn halloween_kill_rolls_once_and_daily_claim_is_shared_across_all_cities() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::HALLOWEEN).unwrap();
    let enemy = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(enemy, 1, 1e12, false);
    for s in 1..=5 {
        assert_eq!(
            w.players[&s].character.seasonal_rolls["halloween_hunt"],
            20261026
        );
        assert_eq!(
            w.players[&s]
                .character
                .quests
                .iter()
                .find(|q| q.id == "halloween_hunt")
                .unwrap()
                .counts[0],
            1
        );
    }
    assert!(w.players[&1].character.owns_mount("nightmare"));
    let q = w.maps[0]
        .quests
        .iter()
        .find(|q| q.id == "halloween_hunt")
        .unwrap()
        .clone();
    let n = w.maps[9]
        .npcs
        .iter()
        .find(|n| n.id == "nacre_gardener")
        .unwrap()
        .clone();
    place(&mut w, 1, 9, Point { x: n.x, y: n.y });
    w.time += 1.;
    let gold = w.players[&1].character.gold;
    w.interact(1, &n.id, Some("quest:claim:halloween_hunt"));
    assert_eq!(w.players[&1].character.gold, gold + q.reward_gold);
    accept(&mut w, 1, "asterion_singer");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "halloween_hunt")
            .unwrap()
            .claimed
    );
    festival(&mut w, 1793055600);
    accept(&mut w, 1, "city_bard");
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "halloween_hunt")
            .unwrap()
            .claimed
    );
    assert!(w.players[&1].character.owns_mount("nightmare"));
}
#[test]
fn halloween_november_tenth_retires_quest_summon_and_boss_but_keeps_mount() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::HALLOWEEN).unwrap();
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .grant_mount("nightmare");
    festival(&mut w, 1794265200);
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    assert!(w.summon_festival(1, seasonal_hunt::HALLOWEEN).is_err());
    assert!(w.festival_view(seasonal_hunt::HALLOWEEN).is_null());
    assert!(w.players[&1].character.owns_mount("nightmare"));
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .any(|q| q.id == "halloween_hunt")
    );
}
#[test]
fn halloween_mount_roll_exact_threshold_and_completed_ledger_survive_save() {
    assert!(seasonal_hunt::wins_mount(0., 0.01));
    assert!(seasonal_hunt::wins_mount(0.009999, 0.01));
    assert!(!seasonal_hunt::wins_mount(0.01, 0.01));
    assert!(!seasonal_hunt::wins_mount(0.999, 0.01));
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::HALLOWEEN).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    let c = &w.players[&1].character;
    let restored: Character = serde_json::from_value(serde_json::to_value(c).unwrap()).unwrap();
    assert_eq!(restored.seasonal_rolls, c.seasonal_rolls);
    assert!(restored.owns_mount("nightmare"));
    for s in 1..=5 {
        w.players.get_mut(&s).unwrap().combat_left = 0.;
        place(
            &mut w,
            s,
            3,
            if s == 1 {
                at(105., 31.)
            } else {
                at(102. + s as f64 * 0.5, 30.)
            },
        );
    }
    w.summon_festival(1, seasonal_hunt::HALLOWEEN).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    let old = w.players[&1].character.mounts.clone();
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert_eq!(w.players[&1].character.mounts, old);
}
#[test]
fn halloween_wipe_reset_hired_eligibility_and_bystander_safety() {
    let mut w = fixture();
    let owner = w.players[&1].character.id.clone();
    for s in 2..=5 {
        w.players.get_mut(&s).unwrap().merc = Some(owner.clone());
    }
    w.summon_festival(1, seasonal_hunt::HALLOWEEN).unwrap();
    let enemy = w.seasonal_hunt.as_ref().unwrap().enemy;
    let _rx = join(&mut w, 6, Class::Warrior);
    place(&mut w, 6, 3, at(105., 23.));
    let hp = w.players[&6].character.hp;
    for _ in 0..100 {
        w.update_slime(enemy);
    }
    assert_eq!(w.players[&6].character.hp, hp);
    for s in 1..=5 {
        w.players.get_mut(&s).unwrap().character.hp = 0.;
    }
    for _ in 0..170 {
        w.update_festival_hunt();
    }
    assert!(w.seasonal_hunt.is_none());
    assert_eq!(w.slimes[enemy].state, "waiting");
}
#[test]
fn halloween_data_only_four_cities_are_dressed_and_ritual_is_clear() {
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    for (i, z) in std::iter::once(&data)
        .chain(data["zones"].as_array().unwrap())
        .enumerate()
    {
        let decor = z["seasonDecor"].as_array();
        if [0, 4, 9, 17, 24].contains(&i) {
            assert!(decor.unwrap().len() >= 24);
            let city = &z["city"];
            for o in decor.unwrap() {
                assert!(
                    o["x"].as_f64().unwrap() > city["x0"].as_f64().unwrap()
                        && o["x"].as_f64().unwrap() < city["x1"].as_f64().unwrap()
                );
                assert!(
                    o["y"].as_f64().unwrap() > city["y0"].as_f64().unwrap()
                        && o["y"].as_f64().unwrap() < city["y1"].as_f64().unwrap()
                );
            }
        } else {
            assert!(decor.is_none());
        }
    }
    let w = world();
    assert!(w.maps[3].line_clear(at(105., 23.), at(105., 32.), PLAYER_RADIUS));
    assert_eq!(
        w.maps[3]
            .slimes
            .iter()
            .filter(|s| s.kind == "hollow_rider")
            .count(),
        1
    );
}
