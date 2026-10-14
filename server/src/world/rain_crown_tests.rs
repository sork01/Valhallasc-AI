//! The Rain Crown Temple is an open, populated private instance.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

#[test]
fn rain_crown_floor_and_quests_are_ready_with_open_gate() {
    let w = world();
    let map = &w.maps[32];
    assert_eq!(map.name, "Temple of the Rain Crown");
    assert!(!map.sealed_template);
    assert_eq!((map.min_level, map.players, map.copies), (80, 5, 4));
    assert_eq!(map.final_boss, "rain_crown_sovereign");
    assert_eq!(map.slimes.len(), 12);
    assert_eq!(map.portals.len(), 2);
    assert!(map.portals.iter().any(|p| p.after_clear));
    assert!(w.maps[22].portals.iter().any(|p| p.to == 32));
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == 32) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 80);
        assert!(item(material(&s.kind)).is_some());
    }
    for kind in [
        "rain_crown_droplet",
        "rain_crown_oracle",
        "rain_crown_guard",
        "rain_crown_gatekeeper",
        "rain_crown_sibyl",
        "rain_crown_sovereign",
    ] {
        let e = crate::cathedral::enemy(kind).unwrap();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 32 && s.kind == kind)
                .count(),
            if e.boss { 1 } else { 3 }
        );
        assert_eq!(Slime::default_level(kind), 80);
        assert_eq!(material(kind), e.material);
    }
    assert!(Slime::ranged("rain_crown_oracle").is_some());
    assert!(Slime::slam_radius("rain_crown_gatekeeper") > 4.);
    assert!(reached(map, &seen, at(map.portals[0].x, map.portals[0].y)));
    let quests = &w.maps[22].quests;
    let trials = quests
        .iter()
        .find(|q| q.id == "tangle_crown_trials")
        .unwrap();
    let final_quest = quests
        .iter()
        .find(|q| q.id == "tangle_crown_final")
        .unwrap();
    assert_eq!(final_quest.requires.as_deref(), Some("tangle_crown_trials"));
    assert_eq!(
        final_quest.reward_item.as_deref(),
        Some("accessory_amber_l80_blue")
    );
    for q in [trials, final_quest] {
        assert_eq!(q.objectives.len(), 3);
        assert!(q.group);
        assert_eq!(q.level, 80);
        assert_eq!(q.reward_xp, xp_to_level(80) / 10);
    }
    for kind in [
        "rain_crown_gatekeeper",
        "rain_crown_sibyl",
        "rain_crown_sovereign",
    ] {
        for slots in boss_slots(kind) {
            let piece = boss_piece_for(kind, slots, 0.).unwrap();
            assert_eq!(piece.source.as_deref(), Some("rain_crown"));
            assert_eq!(piece.required_level, 80);
        }
    }
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}
