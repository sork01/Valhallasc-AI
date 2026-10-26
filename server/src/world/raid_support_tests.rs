//! Raid strength: presence, actual combat and authoritative display, without long fights.
use super::wyrd_tests::{at, drain, join, place, world};
use super::*;

const ZONE: usize = 46;

pub(super) fn crew(count: u64) -> (World, Vec<mpsc::Receiver<Value>>) {
    let mut w = world();
    let mut peers = vec![];
    for session in 1..=count {
        peers.push(join(&mut w, session, Class::Warrior));
        let p = w.players.get_mut(&session).unwrap();
        p.character.level = 99;
        p.character.hp = p.character.max_hp();
        place(&mut w, session, ZONE, at(145., 270.));
    }
    (w, peers)
}

#[test]
fn raid_support_counts_real_contracts_and_updates_on_copy_exit_and_disconnect() {
    let (mut w, _peers) = crew(1);
    assert_eq!(w.raid_support(1).others, 0);
    place(&mut w, 1, ZONE, at(35., 303.));
    w.players.get_mut(&1).unwrap().character.gold = 2_000_000;
    for (n, class) in [
        "mage", "assassin", "priest", "hunter", "warrior", "mage", "assassin", "priest", "hunter",
    ]
    .iter()
    .enumerate()
    {
        w.time += 1.;
        w.interact(1, "cf_quartermaster", Some(&format!("merc_{class}")));
        assert_eq!(w.raid_support(1).others, n + 1);
        assert_eq!(
            w.raid_support(1).attack_multiplier(),
            1. + (n + 1) as f64 * 2.
        );
    }
    assert_eq!(w.players.len(), 10);
    assert_eq!(w.players.values().filter(|p| p.merc.is_some()).count(), 9);
    for session in w.players.keys() {
        let bonus = w.raid_support(*session);
        assert_eq!(bonus.others, 9, "humans and mercenaries receive the bonus");
        assert_eq!(bonus.attack_multiplier(), 19.);
        assert!((bonus.taken_multiplier() - 0.55).abs() < 1e-12);
    }
    let merc = *w.players.keys().find(|s| **s != 1).unwrap();
    place(&mut w, merc, ZONE, at(110., 24.));
    w.players.get_mut(&merc).unwrap().character.hp = 0.;
    assert_eq!(
        w.raid_support(1).others,
        9,
        "distance and falling do not remove presence"
    );
    let copy = w
        .instances
        .iter()
        .find(|i| i.template == ZONE && i.zone != ZONE)
        .unwrap()
        .zone;
    place(&mut w, merc, copy, at(35., 303.));
    assert_eq!(w.raid_support(1).others, 8);
    assert_eq!(
        w.raid_support(merc).others,
        0,
        "other copies never contribute"
    );
    place(&mut w, merc, ZONE, at(35., 303.));
    assert_eq!(w.raid_support(1).others, 9);
    w.players.remove(&merc);
    assert_eq!(
        w.raid_support(1).others,
        8,
        "removed actors stop contributing immediately"
    );
    for p in w.players.values_mut() {
        p.character.zone = 5;
    }
    assert_eq!(
        w.raid_support(1).attack_multiplier(),
        1.,
        "ordinary dungeons have no raid bonus"
    );
    assert_eq!(w.raid_support(1).taken_multiplier(), 1.);
}

#[test]
fn raid_support_excludes_noncombat_actors_and_caps_at_nine_others() {
    let (mut w, _peers) = crew(2);
    assert_eq!(w.raid_support(1).others, 1);
    w.players.get_mut(&2).unwrap().gauntlet = true;
    assert_eq!(w.raid_support(1).others, 0);
    assert_eq!(w.raid_support(2).others, 0);
    let p = w.players.get_mut(&2).unwrap();
    p.gauntlet = false;
    p.character.gm = true;
    p.hidden = true;
    assert_eq!(
        w.raid_support(1).others,
        0,
        "an invisible GM cannot change the fight"
    );
    let (w, _peers) = crew(12); // Defensive cap even for a debug-created overflow.
    assert_eq!(w.raid_support(1).others, 9);
}

#[test]
fn raid_support_scales_seeded_attack_rolls_and_snapshot_without_changing_saved_stats() {
    let (mut w, _peers) = crew(10);
    let base = w.players[&1].character.stats().0;
    w.rng = 1;
    let full = w.roll_damage(1, 1.);
    assert!(full.0 > 0.);
    let snap = w.snapshot_for(ZONE);
    let hero = snap["players"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == w.players[&1].character.id)
        .unwrap();
    assert_eq!(hero["attack"], base * 19.);
    assert_eq!(
        hero["raidSupport"],
        json!({"others":9,"attackPercent":1800,"damageReductionPercent":45})
    );
    assert_eq!(
        w.players[&1].character.stats().0,
        base,
        "the bonus is never saved into gear or attributes"
    );
    for (session, p) in &mut w.players {
        if *session != 1 {
            p.character.zone = 45;
        }
    }
    w.rng = 1;
    let solo = w.roll_damage(1, 1.);
    assert_eq!(full.1, solo.1);
    assert!(
        (full.0 - solo.0 * 19.).abs() <= 10.,
        "only final hit rounding differs"
    );
    let snap = w.snapshot_for(ZONE);
    assert_eq!(snap["players"][0]["attack"], base);
    assert_eq!(snap["players"][0]["raidSupport"]["others"], 0);
    place(&mut w, 1, 45, at(20., 140.));
    assert!(
        w.snapshot_for(45)["players"]
            .as_array()
            .unwrap()
            .iter()
            .all(|p| p.get("raidSupport").is_none())
    );
}

#[test]
fn raid_support_reduces_real_monster_hits_and_stacks_with_shield() {
    let (mut w, _peers) = crew(10);
    let damage = w.players[&1].character.stats().1 + 4000.;
    let hit = |w: &mut World| {
        let p = w.players.get_mut(&1).unwrap();
        p.character.hp = p.character.max_hp();
        p.last_hurt = -99.;
        let before = p.character.hp;
        w.rng = 1;
        w.hurt_player_by(1, damage, at(145., 277.), "cf_brute", 99);
        before - w.players[&1].character.hp
    };
    assert_eq!(hit(&mut w), 550.);
    w.players.get_mut(&1).unwrap().buffs.push(Buff {
        id: "test_shield".into(),
        kind: BuffKind::Shield,
        amount: 0.5,
        left: 30.,
        time: 30.,
    });
    assert_eq!(hit(&mut w), 275.);
    w.players.get_mut(&1).unwrap().buffs.clear();
    for (session, p) in &mut w.players {
        if *session != 1 {
            p.character.zone = 45;
        }
    }
    assert_eq!(hit(&mut w), 1000.);
}

#[test]
fn raid_support_boosts_attack_based_healing() {
    let (mut w, _peers) = crew(10);
    let base = w.players[&1].character.stats().0;
    w.players.get_mut(&2).unwrap().character.hp = 1.;
    w.heal_players(1, &[2], 1.);
    assert_eq!(
        w.players[&2].character.hp,
        (1. + (base * 19.).round()).min(w.players[&2].character.max_hp())
    );
}

#[test]
fn raid_support_inspect_shows_the_same_effective_attack_and_cloak() {
    let (mut w, mut peers) = crew(10);
    let cloak = crate::items::ITEMS
        .iter()
        .find(|i| i.kind == "cloak" && i.required_level == 99)
        .unwrap();
    w.players
        .get_mut(&2)
        .unwrap()
        .character
        .equipment
        .insert("cloak".into(), cloak.id.clone());
    let target = w.players[&2].character.id.clone();
    drain(&mut peers[0]);
    w.inspect(1, &target);
    let reply = drain(&mut peers[0])
        .into_iter()
        .find(|p| p["type"] == "inspect")
        .unwrap();
    assert_eq!(reply["stats"]["attack"], w.raid_attack_power(2));
    assert!(
        reply["slots"]
            .as_array()
            .unwrap()
            .iter()
            .any(|s| s["slot"] == "cloak")
    );
}
