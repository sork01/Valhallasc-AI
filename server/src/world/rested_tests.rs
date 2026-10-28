//! Real join/save/reward paths; advance saved timestamps instead of waiting or farming.
use super::wyrd_tests::{at, join, place, world};
use super::*;

#[test]
fn rested_legacy_account_character_accrues_since_installation_not_first_login() {
    let mut w = world();
    let account = w
        .store
        .create_account("rested-account", "unused")
        .unwrap()
        .unwrap();
    let (c, _) = w
        .store
        .create_for(Some(&account.id), Look::default(), w.maps[0].spawn)
        .unwrap();
    let mut state = serde_json::to_value(&c).unwrap();
    state.as_object_mut().unwrap().remove("rested");
    w.store
        .conn()
        .execute(
            "UPDATE characters SET state=?1 WHERE id=?2",
            rusqlite::params![state.to_string(), c.id],
        )
        .unwrap();
    w.store
        .conn()
        .execute(
            "UPDATE world_meta SET value=?1 WHERE key='rested_epoch'",
            [crate::store::unix_now() - 7200],
        )
        .unwrap();
    let (tx, _rx) = mpsc::channel(256);
    w.join_as(
        1,
        Identity::Account {
            id: account.id,
            gm: false,
            character: Some(c.id),
            look: None,
        },
        tx,
    )
    .unwrap();
    assert!((10.0..10.1).contains(&w.players[&1].character.rested.percent()));
    w.save();
    let before = w.players[&1].character.rested.reserve;
    let (tx, _rx) = mpsc::channel(256);
    assert!(w.join(2, None, Some(Look::default()), tx).is_ok());
    assert_eq!(
        w.players[&2].character.rested.reserve, 0,
        "a new hero cannot collect time from before creation"
    );
    assert_eq!(w.players[&1].character.rested.reserve, before);
}

#[test]
fn rested_disconnect_resume_restart_and_online_checkpoints() {
    let mut w = world();
    let (tx, _rx) = mpsc::channel(256);
    let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
    let token = welcome["token"].as_str().unwrap().to_owned();
    let now = crate::store::unix_now().max(0) as u64;
    w.players.get_mut(&1).unwrap().character.rested.last_seen = now - 144_000;
    // This is still an online character: a checkpoint must discard that elapsed time.
    w.save();
    assert_eq!(w.players[&1].character.rested.percent(), 0.);
    assert!(w.store.load(&token).unwrap().unwrap().rested.last_seen >= now);
    w.leave(1);
    let mut c = w.store.load(&token).unwrap().unwrap();
    c.rested.last_seen = now - 3_600;
    w.store.save_many([&c].into_iter()).unwrap();
    let (tx, _rx) = mpsc::channel(256);
    let welcome = w.join(2, Some(token.clone()), None, tx).unwrap();
    let percent = w.players[&2].character.rested.percent();
    assert!((5.0..5.1).contains(&percent));
    let hero = welcome["snapshot"]["players"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == c.id)
        .unwrap();
    assert_eq!(hero["rested"]["percent"], percent);
    let (tx, _rx) = mpsc::channel(256);
    assert!(w.join(3, Some(token.clone()), None, tx).is_err());
    w.leave(2);
    let mut c = w.store.load(&token).unwrap().unwrap();
    c.rested.last_seen = now - 144_000;
    w.store.save_many([&c].into_iter()).unwrap();
    // New world, same saved storage: server downtime accrues too.
    let mut restarted = World::with_level_spread(w.store.clone(), 0);
    let (tx, _rx) = mpsc::channel(256);
    restarted.join(4, Some(token), None, tx).unwrap();
    assert_eq!(restarted.players[&4].character.rested.percent(), 200.);
}

#[test]
fn rested_pending_save_is_used_instead_of_older_persisted_reserve() {
    let mut w = world();
    let (tx, _rx) = mpsc::channel(256);
    let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
    let token = welcome["token"].as_str().unwrap().to_owned();
    w.leave(1);
    let mut latest = w.store.load(&token).unwrap().unwrap();
    latest.rested.reserve = 3_600_000;
    latest.rested.last_seen = crate::store::unix_now().max(0) as u64;
    w.pending_saves.push(latest);
    let (tx, _rx) = mpsc::channel(256);
    w.join(2, Some(token), None, tx).unwrap();
    assert!((5.0..5.1).contains(&w.players[&2].character.rested.percent()));
}

#[test]
fn rested_actual_kill_and_quest_rewards_spend_the_same_reserve() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 50;
    c.rested.reserve = 144_000_000;
    let id = w.slimes.iter().position(|s| s.zone == 0).unwrap();
    let xp = w.slimes[id].xp;
    let point = at(w.slimes[id].x, w.slimes[id].y);
    place(&mut w, 1, 0, point);
    w.hit_slime(id, 1, 1e12, false);
    assert_eq!(w.players[&1].character.xp, xp * 3);
    let reserve = w.players[&1].character.rested.reserve;
    let quest = w.maps[1]
        .quests
        .iter()
        .find(|q| q.id == "crags_onward")
        .unwrap()
        .clone();
    let npc = w.maps[1]
        .npcs
        .iter()
        .find(|n| n.id == "crags_captain")
        .unwrap()
        .clone();
    let point = npc.position_at(w.time);
    place(&mut w, 1, 1, point);
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .quests
        .push(QuestProgress {
            id: quest.id.clone(),
            counts: quest.objectives.iter().map(|o| o.count).collect(),
            claimed: false,
            completions: 0,
        });
    w.interact(1, "crags_captain", Some("quest:claim:crags_onward"));
    assert_eq!(w.players[&1].character.xp, (xp + quest.reward_xp) * 3);
    assert!(w.players[&1].character.rested.reserve < reserve);
    // A rejected second turn-in cannot consume more reserve.
    let after = w.players[&1].character.rested.reserve;
    w.time += 0.6;
    w.interact(1, "crags_captain", Some("quest:claim:crags_onward"));
    assert_eq!(w.players[&1].character.rested.reserve, after);
}

#[test]
fn rested_party_members_spend_only_their_own_reserve() {
    let mut w = world();
    let _rx1 = join(&mut w, 1, Class::Warrior);
    let _rx2 = join(&mut w, 2, Class::Mage);
    let leader = w.players[&1].character.id.clone();
    let member = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(member),
            name: None,
        },
    );
    w.social(2, SocialCommand::PartyAccept { id: leader });
    let index = w.slimes.iter().position(|s| s.zone == 0).unwrap();
    let point = at(w.slimes[index].x, w.slimes[index].y);
    for session in [1, 2] {
        place(&mut w, session, 0, point);
        w.players.get_mut(&session).unwrap().character.level = 50;
    }
    w.players.get_mut(&1).unwrap().character.rested.reserve = 144_000_000;
    w.hit_slime(index, 1, 1e12, false);
    assert!(w.players[&2].character.xp > 0);
    assert_eq!(w.players[&1].character.xp, 3 * w.players[&2].character.xp);
    assert_eq!(w.players[&2].character.rested.reserve, 0);
}
