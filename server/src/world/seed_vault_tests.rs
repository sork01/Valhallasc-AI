//! The Seed Vault is an open, populated private instance with linked heartwood quests.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

#[test]
fn seed_vault_has_safe_open_routes_boss_rewards_and_quests() {
    let w = world();
    let map = &w.maps[33];
    assert_eq!(map.name, "The Seed Vault");
    assert!(!map.sealed_template);
    assert_eq!((map.min_level, map.players, map.copies), (80, 5, 4));
    assert_eq!(map.final_boss, "seed_worldseed");
    assert_eq!(map.slimes.iter().filter(|s| s.ambush.is_none()).count(), 12);
    assert_eq!(map.portals.len(), 2);
    assert!(map.portals.iter().any(|p| p.after_clear));
    assert!(w.maps[24].portals.iter().any(|p| p.to == 33));
    assert_eq!(w.instances.iter().filter(|i| i.template == 33).count(), 4);
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == 33) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 80);
        assert!(item(material(&s.kind)).is_some());
    }
    for p in &map.portals {
        assert!(reached(map, &seen, at(p.x, p.y)));
    }
    for kind in [
        "seed_mote",
        "seed_amberwing",
        "seed_rootguard",
        "seed_warden",
        "seed_germinator",
        "seed_worldseed",
    ] {
        let e = crate::cathedral::enemy(kind).unwrap();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 33 && s.kind == kind)
                .count(),
            if e.boss { 1 } else { 3 }
        );
        assert_eq!(Slime::default_level(kind), 80);
        assert_eq!(material(kind), e.material);
    }
    assert!(Slime::ranged("seed_amberwing").is_some());
    assert!(Slime::slam_radius("seed_warden") > 4.);
    let quests = &w.maps[24].quests;
    let trials = quests.iter().find(|q| q.id == "heart_seed_trials").unwrap();
    let finale = quests.iter().find(|q| q.id == "heart_seed_final").unwrap();
    assert_eq!(finale.requires.as_deref(), Some("heart_seed_trials"));
    assert_eq!(
        finale.reward_item.as_deref(),
        Some("accessory_amber_l80_blue")
    );
    for q in [trials, finale] {
        assert!(q.group);
        assert_eq!(q.level, 80);
        assert_eq!(q.reward_xp, xp_to_level(80) / 10);
    }
    for kind in ["seed_warden", "seed_germinator", "seed_worldseed"] {
        for slots in boss_slots(kind) {
            let piece = boss_piece_for(kind, slots, 0.).unwrap();
            assert_eq!(piece.source.as_deref(), Some("seed_vault"));
            assert_eq!(piece.required_level, 80);
        }
    }
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}
