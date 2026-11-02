use super::wyrd_tests::{join, world};
use super::*;
fn festival(w: &mut World, unix: u64) {
    w.seasonal.override_unix = Some(unix);
    w.seasonal.next_check = 0.;
    w.update_seasonal();
}
fn talk(w: &mut World, quest: &Quest, action: &str) {
    let (zone, n) = w
        .maps
        .iter()
        .enumerate()
        .find_map(|(z, m)| {
            m.npcs
                .iter()
                .find(|n| n.id == quest.npc)
                .map(|n| (z, n.clone()))
        })
        .unwrap();
    let p = w.players.get_mut(&1).unwrap();
    p.character.zone = zone;
    p.character.x = n.x;
    p.character.y = n.y;
    p.character.level = 99;
    w.time += 1.;
    w.interact(1, &n.id, Some(&format!("quest:{action}:{}", quest.id)));
}
#[test]
fn seasonal_quests_pay_once_each_year_and_save_the_claim_year() {
    let mut w = world();
    festival(&mut w, 1792969200);
    let _rx = join(&mut w, 1, Class::Warrior);
    let q = w.maps[0]
        .quests
        .iter()
        .find(|q| q.id == "halloween_alder")
        .unwrap()
        .clone();
    let before = w.players[&1].character.gold;
    talk(&mut w, &q, "accept");
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .quests
        .iter_mut()
        .find(|g| g.id == q.id)
        .unwrap()
        .counts = vec![1; q.objectives.len()];
    talk(&mut w, &q, "claim");
    assert_eq!(w.players[&1].character.gold, before + q.reward_gold);
    assert_eq!(w.players[&1].character.seasonal_claims[&q.id], 2026);
    talk(&mut w, &q, "accept");
    talk(&mut w, &q, "claim");
    assert_eq!(w.players[&1].character.gold, before + q.reward_gold);
    let roundtrip: Character =
        serde_json::from_value(serde_json::to_value(&w.players[&1].character).unwrap()).unwrap();
    assert_eq!(roundtrip.seasonal_claims[&q.id], 2026);
    festival(&mut w, 1825023600); // November 2027, inside that year's festival.
    talk(&mut w, &q, "accept");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    assert!(!c.quests.iter().find(|g| g.id == q.id).unwrap().claimed);
    c.quests.iter_mut().find(|g| g.id == q.id).unwrap().counts = vec![1; q.objectives.len()];
    talk(&mut w, &q, "claim");
    assert_eq!(w.players[&1].character.gold, before + 2 * q.reward_gold);
    assert_eq!(w.players[&1].character.seasonal_claims[&q.id], 2027);
}
#[test]
fn seasonal_expiry_retires_unfinished_quests_and_refuses_forged_claims() {
    let mut w = world();
    festival(&mut w, 1794265199);
    let mut rx = join(&mut w, 1, Class::Warrior);
    let q = w.maps[0]
        .quests
        .iter()
        .find(|q| q.id == "halloween_alder")
        .unwrap()
        .clone();
    talk(&mut w, &q, "accept");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .any(|g| g.id == q.id && !g.claimed)
    );
    let before = w.players[&1].character.gold;
    festival(&mut w, 1794265200);
    assert!(!w.players[&1].character.quests.iter().any(|g| g.id == q.id));
    talk(&mut w, &q, "accept");
    talk(&mut w, &q, "claim");
    assert_eq!(w.players[&1].character.gold, before);
    assert!(std::iter::from_fn(|| rx.try_recv().ok()).any(|v| {
        v["text"]
            .as_str()
            .is_some_and(|s| s.contains("festival has ended"))
    }));
}
#[test]
fn seasonal_catalog_has_eight_valid_city_quests_and_old_saves_load() {
    let w = world();
    let quests: Vec<_> = w
        .maps
        .iter()
        .flat_map(|m| &m.quests)
        .filter(|q| crate::seasonal::quest_event(&q.id).is_some() && !crate::seasonal::daily(&q.id))
        .collect();
    assert_eq!(quests.len(), 8);
    for q in quests {
        assert_eq!(q.min_level, q.level);
        assert!(q.repeatable);
        assert!(q.objectives.len() >= 3);
        let map = w
            .maps
            .iter()
            .find(|m| m.quests.iter().any(|g| g.id == q.id))
            .unwrap();
        assert!(map.city.is_some() || !map.camps.is_empty());
        assert!(map.npcs.iter().any(|n| n.id == q.npc));
        for o in &q.objectives {
            assert!(match o.kind.as_str() {
                "talk" => map.npcs.iter().any(|n| n.id == o.target),
                "visit" => map.places.iter().any(|p| p.id == o.target),
                _ => false,
            });
        }
    }
    let mut old =
        serde_json::to_value(Character::mercenary(Class::Warrior, 1, "Old save")).unwrap();
    old.as_object_mut().unwrap().remove("seasonalClaims");
    old.as_object_mut().unwrap().remove("seasonalStarted");
    let c: Character = serde_json::from_value(old).unwrap();
    assert!(c.seasonal_claims.is_empty() && c.seasonal_started.is_empty());
}
#[test]
fn seasonal_clock_cannot_be_changed_by_a_production_gm() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.test_commands = false;
    w.players.get_mut(&1).unwrap().character.gm = true;
    assert!(
        w.run_debug(1, DebugCommand::SeasonTime { unix: Some(0) })
            .is_err()
    );
    assert!(w.seasonal.override_unix.is_none());
}
