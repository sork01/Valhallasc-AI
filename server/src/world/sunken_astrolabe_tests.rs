//! The open Sunken Astrolabe and Thunderheart encounter catalog.
use super::wyrd_tests::{at, blocked, flood, reached, world};
use super::*;

#[test]
fn sunken_astrolabe_navigator_has_space_without_pulling_the_axis_in_every_copy() {
    use super::wyrd_tests::{calm, join, place};

    let mut w = world();
    calm(&mut w);
    let _receiver = join(&mut w, 1, Class::Warrior);
    let copies: Vec<_> = w
        .instances
        .iter()
        .filter(|i| i.template == 34)
        .map(|i| i.zone)
        .collect();
    assert_eq!(copies.len(), 4);
    for zone in copies {
        let navigator = w
            .slimes
            .iter()
            .position(|s| s.zone == zone && s.kind == "astro_navigator")
            .unwrap();
        let axis = w
            .slimes
            .iter()
            .position(|s| s.zone == zone && s.kind == "astro_axis")
            .unwrap();
        let center = at(w.spawns[navigator].x, w.spawns[navigator].y);
        let seen = flood(
            &w.maps[zone],
            &blocked(&w.maps[zone], &[]),
            w.maps[zone].spawn,
        );
        let sign = &w.signs["astro_axis"];
        assert!(reached(&w.maps[zone], &seen, at(sign.x, sign.y)));
        // Ten tiles for the party to spread/kite, plus four tiles of idle wandering.
        for n in 0..16 {
            let angle = n as f64 * std::f64::consts::TAU / 16.;
            let point = at(center.x + 10. * angle.cos(), center.y + 10. * angle.sin());
            let mut resolved = point;
            w.maps[zone].collide(&mut resolved, PLAYER_RADIUS);
            assert!(
                resolved.distance(point) < 1e-6,
                "Navigator needs room to kite"
            );
            assert!(reached(&w.maps[zone], &seen, point));
            for id in [navigator, axis] {
                w.slimes[id] = Slime::with_level(id, &w.spawns[id], 85);
            }
            assert!(
                point.distance(w.slimes[axis].point()) > Slime::attack_profile("astro_axis").3 + 4.,
                "Axis can reach the Navigator fight in copy {zone}"
            );
            place(&mut w, 1, zone, point);
            w.update_slime(navigator);
            w.update_slime(axis);
            assert!(
                w.slimes[navigator].target.is_some(),
                "Navigator should engage"
            );
            assert!(
                w.slimes[axis].target.is_none(),
                "Axis joined the Navigator fight in copy {zone}"
            );
            assert_eq!(w.slimes[axis].fight, 0.);
        }
    }
}

#[test]
fn sunken_astrolabe_has_safe_open_routes_quests_and_boss_loot() {
    let w = world();
    let map = &w.maps[34];
    assert_eq!(map.name, "The Sunken Astrolabe");
    assert!(!map.sealed_template);
    assert_eq!((map.min_level, map.players, map.copies), (85, 5, 4));
    assert_eq!(map.final_boss, "astro_axis");
    assert_eq!(map.slimes.len(), 12);
    assert_eq!(map.portals.len(), 2);
    assert!(map.portals.iter().any(|p| p.after_clear));
    assert!(w.maps[25].portals.iter().any(|p| p.to == 34));
    assert_eq!(w.instances.iter().filter(|i| i.template == 34).count(), 4);
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == 34) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 85);
        assert!(item(material(&s.kind)).is_some());
    }
    for p in &map.portals {
        assert!(reached(map, &seen, at(p.x, p.y)));
    }
    for kind in [
        "astro_gearling",
        "astro_starling",
        "astro_sentinel",
        "astro_warden",
        "astro_navigator",
        "astro_axis",
    ] {
        let e = crate::cathedral::enemy(kind).unwrap();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 34 && s.kind == kind)
                .count(),
            if e.boss { 1 } else { 3 }
        );
        assert_eq!(Slime::default_level(kind), 85);
    }
    assert!(Slime::ranged("astro_starling").is_some());
    assert!(Slime::slam_radius("astro_warden") > 4.);
    let quests = &w.maps[25].quests;
    let trials = quests
        .iter()
        .find(|q| q.id == "lapis_astro_trials")
        .unwrap();
    let finale = quests.iter().find(|q| q.id == "lapis_astro_final").unwrap();
    assert_eq!(finale.requires.as_deref(), Some("lapis_astro_trials"));
    assert_eq!(
        finale.reward_item.as_deref(),
        Some("accessory_amber_l85_blue")
    );
    for q in [trials, finale] {
        assert!(q.group);
        assert_eq!(q.level, 85);
        assert_eq!(q.reward_xp, xp_to_level(85) / 10);
    }
    let all_pieces: std::collections::BTreeSet<_> = crate::items::ITEMS
        .iter()
        .filter(|i| i.source.as_deref() == Some("sunken_astrolabe"))
        .map(|i| i.id.as_str())
        .collect();
    assert_eq!(all_pieces.len(), 29);
    let mut reachable = std::collections::BTreeSet::new();
    for kind in ["astro_warden", "astro_navigator", "astro_axis"] {
        for slots in boss_slots(kind) {
            for n in 0..100 {
                let piece = boss_piece_for(kind, slots, n as f64 / 100.).unwrap();
                assert_eq!(piece.source.as_deref(), Some("sunken_astrolabe"));
                assert_eq!(piece.required_level, 85);
                reachable.insert(piece.id.as_str());
            }
        }
    }
    assert_eq!(reachable, all_pieces);
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}

#[test]
fn thunderheart_foes_and_open_gate_are_authoritative() {
    let w = world();
    let map = &w.maps[35];
    assert_eq!(map.name, "The Thunderheart Gate");
    assert!(!map.sealed_template);
    assert_eq!((map.min_level, map.players, map.copies), (95, 5, 4));
    assert_eq!(map.final_boss, "thunder_heart");
    assert_eq!(map.slimes.len(), 12);
    assert_eq!(map.portals.len(), 2);
    assert!(map.portals.iter().any(|p| p.after_clear));
    assert!(w.maps[27].portals.iter().any(|p| p.to == 35));
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == 35) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 95);
        assert!(item(material(&s.kind)).is_some());
    }
    for kind in [
        "thunder_spark",
        "thunder_ray",
        "thunder_guard",
        "thunder_conductor",
        "thunder_bastion",
        "thunder_heart",
    ] {
        let e = crate::cathedral::enemy(kind).unwrap();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 35 && s.kind == kind)
                .count(),
            if e.boss { 1 } else { 3 }
        );
        assert_eq!(Slime::default_level(kind), 95);
    }
    assert!(Slime::ranged("thunder_ray").is_some());
    assert!(Slime::slam_radius("thunder_bastion") > 5.);
    let quests = &w.maps[27].quests;
    let trials = quests
        .iter()
        .find(|q| q.id == "cairn_storm_trials")
        .unwrap();
    let finale = quests
        .iter()
        .find(|q| q.id == "cairn_thunder_final")
        .unwrap();
    assert_eq!(finale.requires.as_deref(), Some("cairn_storm_trials"));
    assert_eq!(
        finale.reward_item.as_deref(),
        Some("accessory_amber_l95_blue")
    );
    for q in [trials, finale] {
        assert!(q.group);
        assert_eq!(q.reward_xp, xp_to_level(95) / 10);
    }
    let all_pieces: std::collections::BTreeSet<_> = crate::items::ITEMS
        .iter()
        .filter(|i| i.source.as_deref() == Some("thunderheart_gate"))
        .map(|i| i.id.as_str())
        .collect();
    assert_eq!(all_pieces.len(), 29);
    let mut reachable = std::collections::BTreeSet::new();
    for kind in ["thunder_conductor", "thunder_bastion", "thunder_heart"] {
        for slots in boss_slots(kind) {
            for n in 0..100 {
                let piece = boss_piece_for(kind, slots, n as f64 / 100.).unwrap();
                assert_eq!(piece.source.as_deref(), Some("thunderheart_gate"));
                assert_eq!(piece.required_level, 95);
                reachable.insert(piece.id.as_str());
            }
        }
    }
    assert_eq!(reachable, all_pieces);
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}

#[test]
fn blooming_labyrinth_opens_with_party_quests_and_level_97_bosses() {
    let w = world();
    let map = &w.maps[36];
    assert_eq!(map.name, "The Blooming Labyrinth");
    assert!(!map.sealed_template);
    assert_eq!((map.min_level, map.players, map.copies), (97, 5, 4));
    assert_eq!(map.final_boss, "bloom_heart");
    assert_eq!(map.slimes.len(), 12);
    assert_eq!(map.portals.len(), 2);
    assert!(map.portals.iter().any(|p| p.after_clear));
    assert!(w.maps[28].portals.iter().any(|p| p.to == 36));
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == 36) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 97);
        assert!(item(material(&s.kind)).is_some());
    }
    let quests = &w.maps[28].quests;
    let trials = quests
        .iter()
        .find(|q| q.id == "yr_sp_bloom_trials")
        .unwrap();
    let finale = quests.iter().find(|q| q.id == "yr_sp_bloom_final").unwrap();
    assert_eq!(finale.requires.as_deref(), Some("yr_sp_bloom_trials"));
    assert_eq!(
        finale.reward_item.as_deref(),
        Some("necklace_moonstone_l95_blue")
    );
    for q in [trials, finale] {
        assert!(q.group);
        assert_eq!(q.level, 97);
        assert_eq!(q.reward_xp, xp_to_level(97) / 10);
    }
    let all_pieces: std::collections::BTreeSet<_> = crate::items::ITEMS
        .iter()
        .filter(|i| i.source.as_deref() == Some("blooming_labyrinth"))
        .map(|i| i.id.as_str())
        .collect();
    assert_eq!(all_pieces.len(), 29);
    let mut reachable = std::collections::BTreeSet::new();
    for kind in ["bloom_thornkeeper", "bloom_mirror", "bloom_heart"] {
        assert_eq!(Slime::default_level(kind), 97);
        for slots in boss_slots(kind) {
            for n in 0..100 {
                let piece = boss_piece_for(kind, slots, n as f64 / 100.).unwrap();
                assert_eq!(piece.source.as_deref(), Some("blooming_labyrinth"));
                assert_eq!(piece.required_level, 95);
                reachable.insert(piece.id.as_str());
            }
        }
    }
    assert_eq!(reachable, all_pieces);
    assert!(Slime::ranged("bloom_moth").is_some());
    assert!(Slime::slam_radius("bloom_thornkeeper") > 4.);
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}

#[test]
fn solar_crucible_opens_with_party_quests_bosses_and_gear() {
    let w = world();
    let map = &w.maps[37];
    assert_eq!(map.name, "The Solar Crucible");
    assert!(!map.sealed_template);
    assert_eq!((map.min_level, map.players, map.copies), (98, 5, 4));
    assert_eq!(map.final_boss, "solar_heart");
    assert_eq!(map.slimes.iter().filter(|s| s.ambush.is_none()).count(), 12);
    assert_eq!(map.portals.len(), 2);
    assert!(w.maps[28].portals.iter().any(|p| p.to == 37));
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == 37) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 98);
        assert!(item(material(&s.kind)).is_some());
    }
    let quests = &w.maps[28].quests;
    let trials = quests
        .iter()
        .find(|q| q.id == "yr_su_solar_trials")
        .unwrap();
    let finale = quests.iter().find(|q| q.id == "yr_su_solar_final").unwrap();
    assert_eq!(finale.requires.as_deref(), Some("yr_su_solar_trials"));
    assert_eq!(
        finale.reward_item.as_deref(),
        Some("accessory_amber_l95_blue")
    );
    for q in [trials, finale] {
        assert!(q.group);
        assert_eq!(q.level, 98);
        assert_eq!(q.reward_xp, xp_to_level(98) / 10);
    }
    let all_pieces: std::collections::BTreeSet<_> = crate::items::ITEMS
        .iter()
        .filter(|i| i.source.as_deref() == Some("solar_crucible"))
        .map(|i| i.id.as_str())
        .collect();
    assert_eq!(all_pieces.len(), 29);
    let mut reachable = std::collections::BTreeSet::new();
    for kind in ["solar_ashwarden", "solar_heliomancer", "solar_heart"] {
        assert_eq!(Slime::default_level(kind), 98);
        for slots in boss_slots(kind) {
            for n in 0..100 {
                let piece = boss_piece_for(kind, slots, n as f64 / 100.).unwrap();
                assert_eq!(piece.source.as_deref(), Some("solar_crucible"));
                assert_eq!(piece.required_level, 95);
                reachable.insert(piece.id.as_str());
            }
        }
    }
    assert_eq!(reachable, all_pieces);
    assert!(Slime::ranged("solar_sunmoth").is_some());
    assert!(Slime::slam_radius("solar_ashwarden") > 4.);
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}

#[test]
fn amber_archive_and_silent_solstice_have_distinct_encounters_quests_and_loot() {
    let w = world();
    for (zone, theme, bosses, trials, finale, reward) in [
        (
            38,
            "amber_archive",
            ["amber_curator", "amber_chronicle", "amber_memory"],
            "yr_au_amber_trials",
            "yr_au_amber_final",
            "necklace_moonstone_l95_blue",
        ),
        (
            39,
            "silent_solstice",
            ["solstice_watcher", "solstice_harbinger", "solstice_heart"],
            "yr_wi_sols_trials",
            "yr_wi_sols_final",
            "accessory_amber_l95_blue",
        ),
    ] {
        let map = &w.maps[zone];
        assert_eq!(
            map.name,
            if zone == 38 {
                "The Amber Archive"
            } else {
                "The Silent Solstice"
            }
        );
        assert!(!map.sealed_template);
        assert_eq!((map.min_level, map.players, map.copies), (99, 5, 4));
        assert_eq!(map.final_boss, bosses[2]);
        assert_eq!(
            (
                map.slimes.iter().filter(|s| s.ambush.is_none()).count(),
                map.portals.len()
            ),
            (12, 2)
        );
        assert!(map.portals[1].after_clear);
        assert!(w.maps[28].portals.iter().any(|p| p.to == zone));
        let seen = flood(map, &blocked(map, &[]), map.spawn);
        for s in w.slimes.iter().filter(|s| s.zone == zone) {
            assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
            assert!(s.point().distance(map.spawn) > 8.);
            assert_eq!(s.level, 99);
            assert!(item(material(&s.kind)).is_some());
        }
        let quests = &w.maps[28].quests;
        let trial = quests.iter().find(|q| q.id == trials).unwrap();
        let final_quest = quests.iter().find(|q| q.id == finale).unwrap();
        assert_eq!(final_quest.requires.as_deref(), Some(trials));
        assert_eq!(final_quest.reward_item.as_deref(), Some(reward));
        for q in [trial, final_quest] {
            assert!(q.group);
            assert_eq!(q.level, 99);
            assert_eq!(q.reward_xp, xp_to_level(99) / 10);
        }
        let all_pieces: std::collections::BTreeSet<_> = crate::items::ITEMS
            .iter()
            .filter(|i| i.source.as_deref() == Some(theme))
            .map(|i| i.id.as_str())
            .collect();
        assert_eq!(all_pieces.len(), 29);
        let mut reachable = std::collections::BTreeSet::new();
        for kind in bosses {
            assert_eq!(Slime::default_level(kind), 99);
            for slots in boss_slots(kind) {
                for n in 0..100 {
                    let piece = boss_piece_for(kind, slots, n as f64 / 100.).unwrap();
                    assert_eq!(piece.source.as_deref(), Some(theme));
                    reachable.insert(piece.id.as_str());
                }
            }
        }
        assert_eq!(reachable, all_pieces);
        assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
    }
}
