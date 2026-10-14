//! The Elder Hollow: the open entrance, private party copies and complete reward path.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const VALE: usize = 20;
const ELDER: usize = 30;

fn enter(w: &mut World, session: u64) {
    place(w, session, VALE, at(106., 22.));
    w.time += 1.;
    w.use_portal(session);
}

#[test]
fn elder_hollow_map_has_open_safe_routes_and_six_editable_enemy_kinds() {
    let w = world();
    let map = &w.maps[ELDER];
    assert_eq!(
        (map.name.as_str(), map.min_level, map.players, map.copies),
        ("The Elder Hollow", 70, 5, 4)
    );
    assert!(!map.sealed_template);
    assert_eq!(map.final_boss, "elder_heart");
    assert_eq!(
        w.instances.iter().filter(|i| i.template == ELDER).count(),
        4
    );
    let seen = flood(map, &blocked(map, &[]), map.spawn);
    for s in w.slimes.iter().filter(|s| s.zone == ELDER) {
        assert!(reached(map, &seen, s.point()), "{} unreachable", s.kind);
        assert!(s.point().distance(map.spawn) > 8.);
        assert_eq!(s.level, 70);
        assert!(item(material(&s.kind)).is_some());
    }
    assert_eq!(map.slimes.len(), 12);
    for kind in [
        "elder_thornling",
        "elder_moth",
        "elder_barkguard",
        "elder_gatekeeper",
        "elder_matron",
        "elder_heart",
    ] {
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.zone == ELDER && s.kind == kind)
                .count(),
            if is_boss(kind) { 1 } else { 3 }
        );
        assert!(crate::cathedral::enemy(kind).is_some());
    }
    assert!(Slime::ranged("elder_moth").is_some());
    assert!(Slime::ranged("elder_matron").is_some());
    assert!(Slime::slam_radius("elder_gatekeeper") > 3.);
    for p in &map.portals {
        assert!(reached(map, &seen, at(p.x, p.y)));
    }
    assert!(
        w.maps[VALE]
            .portals
            .iter()
            .any(|p| p.to == ELDER && p.id == "sun_elder_gate")
    );
    assert!(
        w.maps[VALE]
            .quests
            .iter()
            .any(|q| q.id == "sun_hollow_heart"
                && q.objectives.len() == 3
                && q.reward_item.as_deref() == Some("accessory_amber_l70_elder"))
    );
    assert!(pursuit::grid_matches_collision(map, PLAYER_RADIUS));
}

#[test]
fn elder_hollow_level_gate_and_party_copy_isolation() {
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
        w.players.get_mut(&session).unwrap().character.level = 70;
    }
    w.players.get_mut(&1).unwrap().character.level = 64;
    enter(&mut w, 1);
    assert_eq!(w.players[&1].character.zone, VALE);
    w.players.get_mut(&1).unwrap().character.level = 70;
    enter(&mut w, 1);
    enter(&mut w, 2);
    enter(&mut w, 3);
    let copy = w.players[&1].character.zone;
    assert_eq!(copy, w.players[&2].character.zone);
    assert_ne!(copy, w.players[&3].character.zone);
    assert_eq!(w.public_zone(copy), ELDER);
    assert_eq!(w.public_zone(w.players[&3].character.zone), ELDER);
    place(&mut w, 1, copy, at(42., 83.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, VALE);
    assert_eq!(w.players[&2].character.zone, copy);
}

#[test]
fn elder_hollow_ordinary_kills_advance_the_entrance_quest() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let character = &mut w.players.get_mut(&1).unwrap().character;
    character.level = 70;
    character.quests.push(QuestProgress {
        id: "sun_roots".into(),
        counts: vec![1, 1],
        claimed: true,
        completions: 1,
    });
    character.quests.push(QuestProgress {
        id: "sun_hollow_trials".into(),
        counts: vec![0, 0, 0],
        claimed: false,
        completions: 0,
    });
    enter(&mut w, 1);
    let copy = w.players[&1].character.zone;
    for kind in ["elder_thornling", "elder_moth", "elder_barkguard"] {
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == copy && s.kind == kind)
            .unwrap();
        let point = w.slimes[id].point();
        place(&mut w, 1, copy, point);
        w.hit_slime(id, 1, 1e9, false);
    }
    assert_eq!(
        w.players[&1].character.quests.last().unwrap().counts,
        [1, 1, 1]
    );
}

#[test]
fn elder_hollow_boss_kills_credit_living_party_in_copy_and_drop_exclusive_gear() {
    let mut w = world();
    for (session, class) in [(1, Class::Warrior), (2, Class::Priest), (3, Class::Mage)] {
        let _ = join(&mut w, session, class);
        w.players.get_mut(&session).unwrap().character.level = 70;
        for prerequisite in ["sun_roots", "sun_hollow_trials"] {
            w.players
                .get_mut(&session)
                .unwrap()
                .character
                .quests
                .push(QuestProgress {
                    id: prerequisite.into(),
                    counts: vec![1; if prerequisite == "sun_roots" { 2 } else { 3 }],
                    claimed: true,
                    completions: 1,
                });
        }
        w.players
            .get_mut(&session)
            .unwrap()
            .character
            .quests
            .push(QuestProgress {
                id: "sun_hollow_heart".into(),
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
    place(&mut w, 2, copy, at(48., 83.));
    let owner = w.players[&1].character.id.clone();
    let healer = w.players[&2].character.id.clone();
    for (n, kind) in ["elder_heart", "elder_gatekeeper", "elder_matron"]
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
            .filter(|i| i.source.as_deref() == Some("elder_hollow"))
            .collect();
        let rolls: Vec<_> = w
            .rolls
            .iter()
            .filter(|r| r.zone == copy && r.at.distance(point) < 1.)
            .filter(|r| item(&r.item).is_some_and(|i| i.source.as_deref() == Some("elder_hollow")))
            .collect();
        assert_eq!(loot.len() + rolls.len(), boss_slots(kind).len());
        assert!(
            loot.iter()
                .all(|i| i.required_level == 70 && i.rarity == "rare")
        );
        assert!(
            rolls.iter().all(
                |r| item(&r.item).is_some_and(|i| i.required_level == 70 && i.rarity == "rare")
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
    place(&mut w, 1, copy, at(48., 12.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, VALE);
    assert!(w.players[&1].character.point().distance(at(106., 27.)) < 1.);
    let quest = w.maps[VALE]
        .quests
        .iter()
        .find(|q| q.id == "sun_hollow_heart")
        .unwrap()
        .clone();
    let character = &mut w.players.get_mut(&1).unwrap().character;
    let gold = character.gold;
    let (message, _, changed) = quest_action(character, &quest, "claim");
    assert!(changed, "{message}");
    assert_eq!(character.gold, gold + quest.reward_gold);
    assert!(
        character
            .inventory
            .iter()
            .any(|stack| stack.item == "accessory_amber_l70_elder")
    );
    assert!(!quest_action(character, &quest, "claim").2);
}
