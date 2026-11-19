//! Seahorse quest rewards and environment rules through the authoritative inputs.
use super::wyrd_tests::{at, calm, cross_portal, drain, join, place, world};
use super::*;

fn ready(w: &mut World, zone: usize, mount: &str) {
    let start = if zone == 8 {
        at(100., 200.)
    } else {
        w.maps[zone].spawn
    };
    place(w, 1, zone, start);
    let p = w.players.get_mut(&1).unwrap();
    p.character.grant_mount(mount);
    p.character.select_mount(mount).unwrap();
    p.character.mounted = false;
    p.combat_left = 0.;
    p.cutscene_until = -99.;
}

#[test]
fn underwater_mount_environment_matrix_keeps_every_dungeon_closed_to_riding() {
    let w = world();
    for map in &w.maps {
        for mount in MOUNTS.iter() {
            let expected = map.players == 0
                && if mount.id == "seahorse" {
                    map.underwater()
                } else {
                    !map.underwater()
                };
            assert_eq!(
                map.allows_mount(mount.id),
                expected,
                "{} / {}",
                map.name,
                mount.id
            );
        }
        assert!(!map.allows_mount("unknown"));
    }
    assert!(w.maps[8].allows_mount("seahorse"));
    assert!(w.maps[9].allows_mount("seahorse"));
}

#[test]
fn underwater_mount_messages_refuse_land_mounts_in_both_zones_and_seahorses_on_land() {
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    for zone in [8, 9] {
        for mount in MOUNTS.iter().filter(|m| m.id != "seahorse") {
            ready(&mut w, zone, mount.id);
            w.message(1, ClientMessage::Mount { mounted: true });
            assert!(!w.players[&1].character.mounted, "{zone} / {}", mount.id);
            assert!(
                drain(&mut rx)
                    .iter()
                    .any(|v| v["text"] == "Only a seahorse can be ridden underwater.")
            );
        }
        ready(&mut w, zone, "seahorse");
        w.message(1, ClientMessage::Mount { mounted: true });
        assert!(w.players[&1].character.mounted);
        w.message(1, ClientMessage::Mount { mounted: false });
        assert!(!w.players[&1].character.mounted);
    }
    ready(&mut w, 0, "seahorse");
    w.message(1, ClientMessage::Mount { mounted: true });
    assert!(!w.players[&1].character.mounted);
    assert!(
        drain(&mut rx)
            .iter()
            .any(|v| v["text"] == "A seahorse can be ridden only underwater.")
    );
    ready(&mut w, 0, "horse");
    w.message(1, ClientMessage::Mount { mounted: true });
    assert!(
        w.players[&1].character.mounted,
        "ordinary riding on land is preserved"
    );
}

#[test]
fn underwater_mount_selection_dismounts_incompatible_choices_without_changing_ownership() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    for (zone, current, selected) in [(8, "seahorse", "horse"), (0, "horse", "seahorse")] {
        ready(&mut w, zone, current);
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .grant_mount(selected);
        w.message(1, ClientMessage::Mount { mounted: true });
        assert!(w.players[&1].character.mounted);
        w.message(
            1,
            ClientMessage::SelectMount {
                mount: "unknown".into(),
            },
        );
        assert!(w.players[&1].character.mounted);
        assert_eq!(w.players[&1].character.mount, current);
        w.message(
            1,
            ClientMessage::SelectMount {
                mount: selected.into(),
            },
        );
        let c = &w.players[&1].character;
        assert_eq!(c.mount, selected);
        assert!(!c.mounted);
        assert!(c.owns_mount(current) && c.owns_mount(selected));
    }
}

#[test]
fn underwater_mount_real_crossings_dismount_on_environment_changes_and_keep_the_tideway() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    // The Maelstrom is an ordinary gate, the Tideway is the authored seamless crossing.
    ready(&mut w, 7, "horse");
    w.message(1, ClientMessage::Mount { mounted: true });
    assert!(w.players[&1].character.mounted);
    let down = w.maps[7]
        .portals
        .iter()
        .find(|p| p.to == 8)
        .unwrap()
        .id
        .clone();
    cross_portal(&mut w, 1, 7, &down);
    assert_eq!(w.players[&1].character.zone, 8);
    assert!(!w.players[&1].character.mounted);
    ready(&mut w, 8, "seahorse");
    w.message(1, ClientMessage::Mount { mounted: true });
    cross_portal(&mut w, 1, 8, "nacre_gate");
    assert_eq!(w.players[&1].character.zone, 9);
    assert!(
        w.players[&1].character.mounted,
        "seahorse stays mounted across the underwater seam"
    );
    cross_portal(&mut w, 1, 9, "nacre_deep_gate");
    assert!(w.players[&1].character.mounted);
    cross_portal(&mut w, 1, 8, "maelstrom_up");
    let c = &w.players[&1].character;
    assert_eq!(c.zone, 7);
    assert!(!c.mounted);
    assert_eq!(c.mount, "seahorse", "selection survives surfacing");
}

#[test]
fn underwater_mount_invalid_state_is_removed_before_movement_and_valid_riding_keeps_combat_rules() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    for (zone, mount) in [(8, "horse"), (0, "seahorse")] {
        ready(&mut w, zone, mount);
        w.players.get_mut(&1).unwrap().character.mounted = true;
        w.update_player(1);
        assert!(!w.players[&1].character.mounted);
    }
    ready(&mut w, 8, "seahorse");
    w.players.get_mut(&1).unwrap().combat_left = 1.;
    w.message(1, ClientMessage::Mount { mounted: true });
    assert!(!w.players[&1].character.mounted);
    w.players.get_mut(&1).unwrap().combat_left = 0.;
    w.message(1, ClientMessage::Mount { mounted: true });
    assert!(w.players[&1].character.mounted);
    w.start_attack(1);
    assert!(!w.players[&1].character.mounted);
}

fn quest_visit(w: &mut World, action: &str) {
    let at = w.maps[8]
        .npcs
        .iter()
        .find(|n| n.id == "deep_healer")
        .unwrap()
        .position_at(w.time);
    place(w, 1, 8, at);
    w.time += 0.6;
    w.interact(1, "deep_healer", Some(action));
}

#[test]
fn underwater_mount_fishing_quest_consumes_real_fish_once_and_preserves_mount_selection() {
    let mut w = world();
    calm(&mut w);
    let (tx, mut rx) = mpsc::channel(4096);
    let hello = w.join(1, None, Some(Look::default()), tx).unwrap();
    let token = hello["token"].as_str().unwrap().to_owned();
    w.players.get_mut(&1).unwrap().character.level = 35;
    quest_visit(&mut w, "quest:accept:deep_seahorse");
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .any(|q| q.id == "deep_seahorse"),
        "welcome prerequisite"
    );
    let welcome = w.maps[8]
        .quests
        .iter()
        .find(|q| q.id == "deep_welcome")
        .unwrap()
        .clone();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    quest_action(c, &welcome, "accept");
    for o in &welcome.objectives {
        for _ in 0..o.count {
            quest_progress(c, std::slice::from_ref(&welcome), &o.kind, &o.target);
        }
    }
    assert!(quest_action(c, &welcome, "claim").2);
    c.grant_mount("horse");
    quest_visit(&mut w, "quest:accept:deep_seahorse");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .any(|q| q.id == "deep_seahorse")
    );
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .add_item("fish_pier_sprat", 10);
    quest_visit(&mut w, "quest:claim:deep_seahorse");
    assert!(!w.players[&1].character.owns_mount("seahorse"));
    assert_eq!(
        w.players[&1].character.quantity("fish_pier_sprat"),
        10,
        "missing herring consumes nothing"
    );
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .add_item("fish_saltby_herring", 5);
    quest_visit(&mut w, "quest:claim:deep_seahorse");
    let c = &w.players[&1].character;
    assert!(c.owns_mount("seahorse"));
    assert_eq!(c.mount, "horse");
    assert!(!c.mounted, "quest never mounts automatically");
    assert_eq!(c.quantity("fish_pier_sprat"), 0);
    assert_eq!(c.quantity("fish_saltby_herring"), 0);
    let gold = c.gold;
    quest_visit(&mut w, "quest:claim:deep_seahorse");
    assert_eq!(w.players[&1].character.gold, gold, "no replayed reward");
    assert_eq!(
        w.players[&1]
            .character
            .mounts
            .iter()
            .filter(|id| *id == "seahorse")
            .count(),
        1
    );
    w.message(
        1,
        ClientMessage::SelectMount {
            mount: "seahorse".into(),
        },
    );
    w.message(1, ClientMessage::Mount { mounted: true });
    assert!(w.players[&1].character.mounted);
    drain(&mut rx);
    w.leave(1);
    let (tx, _rx) = mpsc::channel(4096);
    w.join(1, Some(token), None, tx).unwrap();
    let c = &w.players[&1].character;
    assert!(c.owns_mount("seahorse") && c.mounted);
    assert_eq!(c.mount, "seahorse");
    assert!(
        c.quests
            .iter()
            .any(|q| q.id == "deep_seahorse" && q.claimed)
    );
}

#[test]
fn underwater_mount_login_sanitizes_old_riders_in_both_environments() {
    let mut w = world();
    let (tx, _rx) = mpsc::channel(4096);
    let hello = w.join(1, None, Some(Look::default()), tx).unwrap();
    let token = hello["token"].as_str().unwrap().to_owned();
    for (zone, mount) in [(8, "horse"), (0, "seahorse")] {
        ready(&mut w, zone, mount);
        w.players.get_mut(&1).unwrap().character.mounted = true;
        w.leave(1);
        let (tx, _rx) = mpsc::channel(4096);
        w.join(1, Some(token.clone()), None, tx).unwrap();
        let c = &w.players[&1].character;
        assert!(!c.mounted);
        assert_eq!(c.mount, mount);
        assert!(c.owns_mount(mount));
    }
}
