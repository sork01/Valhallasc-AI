//! The Eye Below: the open entrance, private party copies and complete reward path.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const SHORE: usize = 19;
const EYE: usize = 29;

fn enter(w: &mut World, session: u64) {
    place(w, session, SHORE, at(105., 27.));
    w.time += 1.;
    w.use_portal(session);
}

#[test]
fn eye_below_map_has_open_safe_routes_and_six_editable_enemy_kinds() {
    let w = world();
    let map = &w.maps[EYE];
    assert_eq!(
        (map.name.as_str(), map.min_level, map.players, map.copies),
        ("The Eye Below", 65, 5, 4)
    );
    assert!(!map.sealed_template);
    assert_eq!(map.final_boss, "eye_unblinking");
    assert_eq!(w.instances.iter().filter(|i| i.template == EYE).count(), 4);
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == EYE) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 65);
        assert!(item(material(&s.kind)).is_some());
    }
    assert_eq!(map.slimes.len(), 12);
    for kind in [
        "eye_drifter",
        "eye_lurker",
        "eye_adept",
        "eye_lenswarden",
        "eye_undertide",
        "eye_unblinking",
    ] {
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == EYE && s.kind == kind)
                .count(),
            if is_boss(kind) { 1 } else { 3 }
        );
        assert!(crate::cathedral::enemy(kind).is_some());
    }
    assert!(Slime::ranged("eye_adept").is_some());
    assert!(Slime::ranged("eye_undertide").is_some());
    assert!(Slime::slam_radius("eye_lenswarden") > 3.);
    for p in &map.portals {
        assert!(reached(map, &seen, at(p.x, p.y)));
    }
    assert!(
        w.maps[SHORE]
            .portals
            .iter()
            .any(|p| p.to == EYE && p.id == "stormglass_eye_descent")
    );
    assert!(
        w.maps[SHORE]
            .quests
            .iter()
            .any(|q| q.id == "stormglass_ward"
                && q.objectives.len() == 3
                && q.reward_item.as_deref() == Some("accessory_amber_l65_eye"))
    );
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}

#[test]
fn eye_below_level_gate_and_party_copy_isolation() {
    let mut w = world();
    for (session, class) in [(1, Class::Warrior), (2, Class::Priest), (3, Class::Mage)] {
        let _ = join(&mut w, session, class);
    }
    let id = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(id),
            name: None,
        },
    );
    w.social(
        2,
        SocialCommand::PartyAccept {
            id: w.players[&1].character.id.clone(),
        },
    );
    for session in [1, 2, 3] {
        w.players.get_mut(&session).unwrap().character.level = 65;
    }
    w.players.get_mut(&1).unwrap().character.level = 64;
    enter(&mut w, 1);
    assert_eq!(w.players[&1].character.zone, SHORE);
    w.players.get_mut(&1).unwrap().character.level = 65;
    enter(&mut w, 1);
    enter(&mut w, 2);
    enter(&mut w, 3);
    let copy = w.players[&1].character.zone;
    assert_eq!(copy, w.players[&2].character.zone);
    assert_ne!(copy, w.players[&3].character.zone);
    assert_eq!(w.public_zone(copy), EYE);
    assert_eq!(w.public_zone(w.players[&3].character.zone), EYE);
    place(&mut w, 1, copy, at(42., 82.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, SHORE);
    assert_eq!(w.players[&2].character.zone, copy);
}

#[test]
fn eye_below_boss_kills_credit_living_party_in_copy_and_drop_exclusive_gear() {
    let mut w = world();
    for (session, class) in [(1, Class::Warrior), (2, Class::Priest), (3, Class::Mage)] {
        let _ = join(&mut w, session, class);
        w.players.get_mut(&session).unwrap().character.level = 65;
        w.players
            .get_mut(&session)
            .unwrap()
            .character
            .quests
            .push(QuestProgress {
                id: "stormglass_ward".into(),
                counts: vec![0, 0, 0],
                claimed: false,
                completions: 0,
            });
    }
    let id = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(id),
            name: None,
        },
    );
    w.social(
        2,
        SocialCommand::PartyAccept {
            id: w.players[&1].character.id.clone(),
        },
    );
    enter(&mut w, 1);
    enter(&mut w, 2);
    enter(&mut w, 3);
    let copy = w.players[&1].character.zone;
    // The healer stays near the arrival, outside the usual XP/quest radius.
    place(&mut w, 2, copy, at(48., 82.));
    let owner = w.players[&1].character.id.clone();
    let healer = w.players[&2].character.id.clone();
    for (n, kind) in ["eye_unblinking", "eye_lenswarden", "eye_undertide"]
        .iter()
        .enumerate()
    {
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == copy && s.kind == *kind)
            .unwrap();
        let point = w.slimes[id].point();
        place(&mut w, 1, copy, point);
        if n == 2 {
            place(&mut w, 2, copy, at(point.x + 1., point.y));
        }
        w.hit_slime(id, 1, 1e9, false);
        assert_eq!(w.instance_cleared(copy), n == 2);
        let loot: Vec<_> = w
            .drops
            .iter()
            .filter(|d| d.zone == copy && d.point().distance(point) < 1.)
            .filter_map(|d| d.item.as_deref().and_then(item))
            .filter(|i| i.source.as_deref() == Some("eye_below"))
            .collect();
        let rolls: Vec<_> = w
            .rolls
            .iter()
            .filter(|r| r.zone == copy && r.at.distance(point) < 1.)
            .filter(|r| item(&r.item).is_some_and(|i| i.source.as_deref() == Some("eye_below")))
            .collect();
        assert_eq!(loot.len() + rolls.len(), boss_slots(kind).len());
        assert!(
            loot.iter()
                .all(|i| i.required_level == 65 && i.rarity == "rare")
        );
        assert!(
            rolls.iter().all(
                |r| item(&r.item).is_some_and(|i| i.required_level == 65 && i.rarity == "rare")
            )
        );
        assert!(
            w.drops
                .iter()
                .any(|d| d.zone == copy && d.item.as_deref() == Some(material(kind)))
        );
        assert!(
            w.drops
                .iter()
                .filter(|d| d.zone == copy && d.point().distance(point) < 1.)
                .all(|d| d.owner == owner || d.owner == healer)
        );
        if n == 2 {
            assert!(
                rolls
                    .iter()
                    .all(|r| r.votes.iter().any(|(who, _)| who == &owner)
                        && r.votes.iter().any(|(who, _)| who == &healer))
            );
        }
    }
    for session in [1, 2] {
        assert_eq!(
            w.players[&session].character.quests.last().unwrap().counts,
            vec![1, 1, 1]
        );
    }
    assert_eq!(
        w.players[&3].character.quests.last().unwrap().counts,
        vec![0, 0, 0]
    );
    assert!(!w.instance_cleared(w.players[&3].character.zone));
}
