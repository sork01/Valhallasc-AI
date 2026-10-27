use super::*;

fn world() -> World {
    let mut w = World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
    for session in 1..=2 {
        let (tx, _) = mpsc::channel(4096);
        w.join(session, None, Some(Look::default()), tx).unwrap();
    }
    w
}
fn quest(w: &World, id: &str) -> Quest {
    w.maps
        .iter()
        .flat_map(|m| &m.quests)
        .find(|q| q.id == id)
        .unwrap()
        .clone()
}
fn abandon(w: &mut World, id: &str) {
    w.message(1, ClientMessage::QuestAbandon { id: id.into() });
}
fn talk(w: &mut World, id: &str, action: &str) {
    let q = quest(w, id);
    let (zone, npc) = w
        .maps
        .iter()
        .enumerate()
        .find_map(|(z, m)| {
            m.npcs
                .iter()
                .find(|n| n.id == q.npc)
                .map(|n| (z, n.clone()))
        })
        .unwrap();
    let p = w.players.get_mut(&1).unwrap();
    p.character.zone = zone;
    let at = npc.position_at(w.time);
    p.character.x = at.x;
    p.character.y = at.y;
    p.character.hp = p.character.max_hp();
    p.service_at = -10.;
    let choice = (action == "claim")
        .then(|| q.reward_choices.get("warrior").and_then(|v| v.first()))
        .flatten();
    w.interact(
        1,
        &q.npc,
        Some(&format!(
            "quest:{action}:{id}{}",
            choice.map_or(String::new(), |c| format!(":{c}"))
        )),
    );
}
#[test]
fn quest_journal_abandon_resets_progress_without_rewards_and_is_personal() {
    let mut w = world();
    let q = quest(&w, "slime_patrol");
    for s in 1..=2 {
        let c = &mut w.players.get_mut(&s).unwrap().character;
        assert!(quest_action(c, &q, "accept").2);
        c.quests
            .iter_mut()
            .find(|p| p.id == q.id)
            .unwrap()
            .counts
            .fill(2);
    }
    let before = w.players[&1].character.clone();
    // The journal works away from the giver, including from another zone.
    w.players.get_mut(&1).unwrap().character.zone = 4;
    abandon(&mut w, &q.id);
    let c = &w.players[&1].character;
    assert!(!c.quests.iter().any(|p| p.id == q.id));
    assert_eq!(
        (c.xp, c.gold, c.inventory.clone()),
        (before.xp, before.gold, before.inventory)
    );
    assert_eq!(
        w.players[&2]
            .character
            .quests
            .iter()
            .find(|p| p.id == q.id)
            .unwrap()
            .counts,
        vec![2]
    );
    abandon(&mut w, "missing");
    abandon(&mut w, &q.id);
    talk(&mut w, &q.id, "accept");
    assert_eq!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|p| p.id == q.id)
            .unwrap()
            .counts,
        vec![0]
    );
    assert!(!w.players[&1].character.abandoned_quests.contains(&q.id));
}
#[test]
fn quest_journal_abandon_keeps_claimed_rewards_and_repeatable_history() {
    let mut w = world();
    let mut q = quest(&w, "meadow_bounty");
    q.requires = None;
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    assert!(quest_action(c, &q, "accept").2);
    let p = c.quests.iter_mut().find(|p| p.id == q.id).unwrap();
    p.counts = q.objectives.iter().map(|o| o.count).collect();
    // Bring objectives follow actual items, even after a reset.
    for o in &q.objectives {
        if o.kind == "bring" {
            c.add_item(&o.target, o.count);
        }
    }
    assert!(quest_action(c, &q, "claim").2);
    let paid = (c.gold, c.xp);
    abandon(&mut w, &q.id);
    assert_eq!(
        (w.players[&1].character.gold, w.players[&1].character.xp),
        paid
    );
    assert!(quest_action(&mut w.players.get_mut(&1).unwrap().character, &q, "accept").2);
    abandon(&mut w, &q.id);
    let p = w.players[&1]
        .character
        .quests
        .iter()
        .find(|p| p.id == q.id)
        .unwrap();
    assert!(p.claimed);
    assert_eq!(p.completions, 1);
    assert!(quest_action(&mut w.players.get_mut(&1).unwrap().character, &q, "accept").2);
    assert_eq!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|p| p.id == q.id)
            .unwrap()
            .completions,
        1
    );
}
#[test]
fn quest_journal_abandoned_automatic_quest_survives_save_and_can_be_retaken() {
    let mut w = world();
    let q = w
        .maps
        .iter()
        .flat_map(|m| &m.quests)
        .find(|q| q.auto_level.is_some() && q.handoff_to.is_none())
        .unwrap()
        .clone();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    sync_progression(c, &w.maps);
    abandon(&mut w, &q.id);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let saved = serde_json::to_value(&*c).unwrap();
    let mut restored: Character = serde_json::from_value(saved.clone()).unwrap();
    sync_progression(&mut restored, &w.maps);
    assert!(!restored.quests.iter().any(|p| p.id == q.id));
    assert!(quest_action(&mut restored, &q, "accept").2);
    assert!(!restored.abandoned_quests.contains(&q.id));
    let mut legacy = saved;
    legacy.as_object_mut().unwrap().remove("abandoned_quests");
    // Character's saved fields use their existing serialization convention.
    legacy.as_object_mut().unwrap().remove("abandonedQuests");
    assert!(
        serde_json::from_value::<Character>(legacy)
            .unwrap()
            .abandoned_quests
            .is_empty()
    );
}
#[test]
fn quest_journal_all_27_handoffs_are_immediate_level_independent_and_rewardless() {
    let mut w = world();
    assert_eq!(
        w.maps
            .iter()
            .filter(|m| m.template.is_none())
            .flat_map(|m| &m.quests)
            .filter(|q| q.handoff_to.is_some())
            .count(),
        27
    );
    for chapter in 1..=28 {
        let id = format!("es_{chapter:02}");
        let q = quest(&w, &id);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = q.min_level;
        c.hp = c.max_hp();
        c.inventory.clear();
        c.quests.clear();
        c.abandoned_quests.clear();
        if let Some(prev) = &q.requires {
            c.quests.push(QuestProgress {
                id: prev.clone(),
                claimed: true,
                completions: 1,
                counts: vec![],
            });
        }
        assert!(quest_action(c, &q, "accept").2);
        c.quests.iter_mut().find(|p| p.id == id).unwrap().counts =
            q.objectives.iter().map(|o| o.count).collect();
        talk(&mut w, &id, "claim");
        let c = &w.players[&1].character;
        assert!(c.quests.iter().any(|p| p.id == id && p.claimed));
        if chapter == 28 {
            assert!(
                !c.quests
                    .iter()
                    .any(|p| p.id.starts_with("es_go_") && !p.claimed)
            );
            continue;
        }
        let next = format!("es_{:02}", chapter + 1);
        let handoff = format!("es_go_{:02}", chapter + 1);
        let h = quest(&w, &handoff);
        assert!(
            c.quests.iter().any(|p| p.id == handoff && !p.claimed),
            "chapter {chapter}"
        );
        assert_eq!(h.handoff_to.as_deref(), Some(next.as_str()));
        assert_eq!(h.npc, quest(&w, &next).npc);
        assert_eq!((h.reward_xp, h.reward_gold), (0, 0));
        assert!(!c.quests.iter().any(|p| p.id == next));
        let next_q = quest(&w, &next);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        let reward_before = (c.xp, c.gold, c.inventory.clone());
        assert!(!quest_action(c, &h, "claim").2);
        if c.level < next_q.min_level {
            assert!(!quest_action(c, &next_q, "accept").2);
        }
        c.level = next_q.min_level;
        talk(&mut w, &next, "accept");
        let c = &w.players[&1].character;
        assert!(c.quests.iter().any(|p| p.id == next && !p.claimed));
        assert!(c.quests.iter().any(|p| p.id == handoff && p.claimed));
        assert_eq!((c.xp, c.gold, c.inventory.clone()), reward_before);
    }
}
#[test]
fn quest_journal_handoffs_backfill_old_progress_once_and_do_not_skip_started_chapters() {
    let mut w = world();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 2;
    c.quests.push(QuestProgress {
        id: "es_01".into(),
        claimed: true,
        completions: 1,
        counts: vec![1],
    });
    sync_progression(c, &w.maps);
    sync_progression(c, &w.maps);
    assert_eq!(c.quests.iter().filter(|p| p.id == "es_go_02").count(), 1);
    assert!(!c.quests.iter().any(|p| p.id == "es_go_03"));
    abandon(&mut w, "es_go_02");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    sync_progression(c, &w.maps);
    assert!(!c.quests.iter().any(|p| p.id == "es_go_02"));
    c.level = 7;
    let q = quest(&w, "es_02");
    assert!(quest_action(&mut w.players.get_mut(&1).unwrap().character, &q, "accept").2);
    sync_progression(&mut w.players.get_mut(&1).unwrap().character, &w.maps);
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .any(|p| p.id == "es_go_02")
    );
}

#[test]
fn quest_restore_automatic_routes_and_eldmarr_handoffs_from_journal_after_reload() {
    let mut w = world();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    c.zone = 4;
    c.quests.push(QuestProgress {
        id: "es_01".into(),
        claimed: true,
        completions: 1,
        counts: vec![1],
    });
    sync_progression(c, &w.maps);
    for id in ["crags_onward", "es_go_02"] {
        abandon(&mut w, id);
        let c = &w.players[&1].character;
        let restored: Character = serde_json::from_value(serde_json::to_value(c).unwrap()).unwrap();
        w.players.get_mut(&1).unwrap().character = restored;
        let before = w.players[&1].character.clone();
        let message: ClientMessage =
            serde_json::from_value(json!({"type":"quest_restore","id":id})).unwrap();
        w.message(1, message);
        let c = &w.players[&1].character;
        assert!(c.quests.iter().any(|q| q.id == id && !q.claimed));
        assert!(!c.abandoned_quests.iter().any(|q| q == id));
        assert_eq!(
            (c.zone, c.x, c.y, c.gold, c.xp, c.inventory.clone()),
            (
                before.zone,
                before.x,
                before.y,
                before.gold,
                before.xp,
                before.inventory
            )
        );
        assert!(!w.players[&2].character.quests.iter().any(|q| q.id == id));
        w.message(1, ClientMessage::QuestRestore { id: id.into() });
        assert_eq!(
            w.players[&1]
                .character
                .quests
                .iter()
                .filter(|q| q.id == id)
                .count(),
            1
        );
    }
}

#[test]
fn quest_restore_rejects_ineligible_quests_and_cannot_bypass_progression() {
    let mut w = world();
    let restore =
        |w: &mut World, id: &str| w.message(1, ClientMessage::QuestRestore { id: id.into() });
    restore(&mut w, "missing");
    restore(&mut w, "crags_onward");
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .any(|q| q.id == "crags_onward")
    );
    let q = quest(&w, "slime_patrol");
    assert!(quest_action(&mut w.players.get_mut(&1).unwrap().character, &q, "accept").2);
    abandon(&mut w, &q.id);
    restore(&mut w, &q.id);
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .any(|q| q.id == "slime_patrol")
    );
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 1;
    c.abandoned_quests
        .extend(["crags_onward".into(), "es_go_02".into()]);
    restore(&mut w, "crags_onward");
    restore(&mut w, "es_go_02");
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .any(|q| ["crags_onward", "es_go_02"].contains(&q.id.as_str()))
    );
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    c.quests.push(QuestProgress {
        id: "es_01".into(),
        claimed: true,
        completions: 1,
        counts: vec![1],
    });
    c.quests.push(QuestProgress {
        id: "es_02".into(),
        claimed: false,
        completions: 0,
        counts: vec![0],
    });
    restore(&mut w, "es_go_02");
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .any(|q| q.id == "es_go_02")
    );
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.quests.push(QuestProgress {
        id: "crags_onward".into(),
        claimed: true,
        completions: 1,
        counts: vec![1],
    });
    let before = c.clone();
    restore(&mut w, "crags_onward");
    let c = &w.players[&1].character;
    assert!(
        c.quests
            .iter()
            .find(|q| q.id == "crags_onward")
            .unwrap()
            .claimed
    );
    assert_eq!(
        (c.gold, c.xp, c.quests.len()),
        (before.gold, before.xp, before.quests.len())
    );
}
