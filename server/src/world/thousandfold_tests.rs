//! The open Pavilion has authoritative encounters and isolated party copies.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const PAVILION: usize = 31;

#[test]
fn thousandfold_encounters_are_reachable_through_the_open_entrance() {
    let w = world();
    let map = &w.maps[PAVILION];
    assert_eq!(map.name, "The Thousandfold Pavilion");
    assert!(!map.sealed_template);
    assert_eq!((map.min_level, map.players, map.copies), (75, 5, 4));
    assert_eq!(map.final_boss, "pavilion_sovereign");
    assert_eq!(map.slimes.len(), 12);
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == PAVILION) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 75);
        assert!(item(material(&s.kind)).is_some());
    }
    for kind in [
        "pavilion_foldling",
        "pavilion_inkmoth",
        "pavilion_silkguard",
        "pavilion_mirror",
        "pavilion_weaver",
        "pavilion_sovereign",
    ] {
        let e = crate::cathedral::enemy(kind).unwrap();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == PAVILION && s.kind == kind)
                .count(),
            if e.boss { 1 } else { 3 }
        );
        assert!(is_elite(kind));
        assert_eq!(is_boss(kind), e.boss);
        assert_eq!(Slime::default_level(kind), 75);
        assert_eq!(Slime::stats(kind).0, e.stats[0]);
        assert_eq!(material(kind), e.material);
    }
    assert!(Slime::ranged("pavilion_inkmoth").is_some());
    assert!(Slime::ranged("pavilion_weaver").is_some());
    assert!(Slime::ranged("pavilion_sovereign").is_some());
    assert!(Slime::slam_radius("pavilion_silkguard") >= 3.);
    assert!(Slime::slam_radius("pavilion_mirror") >= 3.9);
    for p in &map.portals {
        assert!(reached(map, &seen, at(p.x, p.y)));
    }
    assert!(
        w.maps[21]
            .portals
            .iter()
            .any(|p| p.to == PAVILION && p.id == "ribbon_pavilion_gate")
    );
    assert!(map.portals.iter().any(|p| p.after_clear && p.to == 21));
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}

#[test]
fn thousandfold_level_gate_and_party_copies() {
    let mut w = world();
    for (session, class) in [(1, Class::Warrior), (2, Class::Priest), (3, Class::Mage)] {
        let _ = join(&mut w, session, class);
        w.players.get_mut(&session).unwrap().character.level = 75;
    }
    let ally = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(ally),
            name: None,
        },
    );
    w.social(
        2,
        SocialCommand::PartyAccept {
            id: w.players[&1].character.id.clone(),
        },
    );
    w.players.get_mut(&1).unwrap().character.level = 74;
    place(&mut w, 1, 21, at(119., 65.));
    w.time += 1.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 21);
    w.players.get_mut(&1).unwrap().character.level = 75;
    for session in [1, 2, 3] {
        place(&mut w, session, 21, at(119., 65.));
        w.time += 1.;
        w.use_portal(session);
    }
    let copy = w.players[&1].character.zone;
    assert_eq!(w.public_zone(copy), PAVILION);
    assert_eq!(w.players[&2].character.zone, copy);
    assert_ne!(w.players[&3].character.zone, copy);
    place(&mut w, 1, copy, at(42., 83.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 21);
}

#[test]
fn thousandfold_quests_and_boss_loot_match_the_level_75_catalog() {
    let w = world();
    let quests = &w.maps[21].quests;
    let trials = quests.iter().find(|q| q.id == "ribbon_folds").unwrap();
    let final_quest = quests.iter().find(|q| q.id == "ribbon_final").unwrap();
    assert_eq!(trials.objectives.len(), 3);
    assert_eq!(final_quest.objectives.len(), 3);
    assert_eq!(final_quest.requires.as_deref(), Some("ribbon_folds"));
    assert_eq!(
        final_quest.reward_item.as_deref(),
        Some("accessory_amber_l75_blue")
    );
    for quest in [trials, final_quest] {
        assert!(quest.group);
        assert_eq!(quest.level, 75);
        assert_eq!(quest.reward_xp, xp_to_level(75) / 10);
    }
    for kind in ["pavilion_mirror", "pavilion_weaver", "pavilion_sovereign"] {
        for slots in boss_slots(kind) {
            let piece = boss_piece_for(kind, slots, 0.).unwrap();
            assert_eq!(piece.source.as_deref(), Some("thousandfold"));
            assert_eq!(piece.required_level, 75);
            assert_eq!(piece.rarity, "rare");
        }
    }
}
