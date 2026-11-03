use super::wyrd_tests::{at, calm, join, place, world};
use super::*;
fn date(w: &mut World, unix: u64) {
    w.seasonal.override_unix = Some(unix);
    w.seasonal.next_check = 0.;
    w.update_seasonal();
}
fn accept(w: &mut World, s: u64, npc: &str) {
    let (z, n) = w
        .maps
        .iter()
        .enumerate()
        .find_map(|(z, m)| m.npcs.iter().find(|n| n.id == npc).cloned().map(|n| (z, n)))
        .unwrap();
    place(w, s, z, at(n.x, n.y));
    w.time += 1.;
    w.interact(s, npc, Some("quest:accept:newyear_hunt"));
}
fn fixture() -> World {
    let mut w = world();
    calm(&mut w);
    date(&mut w, 1798498800);
    for s in 1..=5 {
        let _rx = join(&mut w, s, Class::Warrior);
        accept(&mut w, s, if s % 2 == 0 { "city_bard" } else { "baker" });
        w.players.get_mut(&s).unwrap().character.level = (s * 5 + u64::from(s == 5)) as u32;
    }
    let owner = w.players[&1].character.id.clone();
    for s in 2..=5 {
        let c = w.players[&s].character.clone();
        w.party_add_mercenary(&owner, &c).unwrap();
    }
    gather(&mut w);
    w
}
fn gather(w: &mut World) {
    for s in 1..=5 {
        place(
            w,
            s,
            2,
            if s == 1 {
                at(110.5, 100.)
            } else {
                at(100. + s as f64 * 0.7, 99.)
            },
        );
    }
}
#[test]
fn newyear_summon_scales_to_highest_and_freezes_five_participants() {
    let mut w = fixture();
    place(&mut w, 2, 2, at(110.5, 100.));
    w.summon_festival(2, seasonal_hunt::NEWYEAR).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    assert_eq!(w.slimes[e].level, 26);
    let hp = w.slimes[e].max_hp;
    w.players.get_mut(&5).unwrap().character.level = 99;
    assert_eq!(w.slimes[e].max_hp, hp);
    assert!(w.summon_festival(1, seasonal_hunt::NEWYEAR).is_err());
    let _rx = join(&mut w, 6, Class::Mage);
    place(&mut w, 6, 2, at(103., 101.));
    assert_eq!(w.hit_slime(e, 6, 1e12, false), 0.);
    assert_eq!(w.slimes[e].hp, hp);
    assert!(w.festival_view(seasonal_hunt::HALLOWEEN).is_null());
    assert!(w.festival_view(seasonal_hunt::CHRISTMAS).is_null());
    assert_eq!(w.festival_view(seasonal_hunt::NEWYEAR)["level"], 26);
}
#[test]
fn newyear_independent_daily_rolls_shared_city_claim_and_next_day() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 1234567;
    w.hit_slime(e, 1, 1e12, false);
    for s in 1..=5 {
        let c = &w.players[&s].character;
        assert_eq!(c.owns_mount("rocket"), s == 2 || s == 4);
        assert_eq!(c.seasonal_rolls["newyear_hunt"], 20261229);
        assert_eq!(
            c.quests
                .iter()
                .find(|q| q.id == "newyear_hunt")
                .unwrap()
                .counts[0],
            1
        );
    }
    let (z, n) = w
        .maps
        .iter()
        .enumerate()
        .find_map(|(z, m)| {
            m.npcs
                .iter()
                .find(|n| n.id == "nacre_gardener")
                .cloned()
                .map(|n| (z, n))
        })
        .unwrap();
    place(&mut w, 1, z, at(n.x, n.y));
    w.time += 1.;
    let gold = w.players[&1].character.gold;
    w.interact(1, "nacre_gardener", Some("quest:claim:newyear_hunt"));
    assert_eq!(w.players[&1].character.gold, gold + 300);
    assert_eq!(
        w.players[&1].character.seasonal_claims["newyear_hunt"],
        20261229
    );
    accept(&mut w, 1, "asterion_singer");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "newyear_hunt")
            .unwrap()
            .claimed
    );
    date(&mut w, 1798585200);
    accept(&mut w, 1, "asterion_singer");
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "newyear_hunt")
            .unwrap()
            .claimed
    );
    assert_eq!(
        w.players[&1].character.seasonal_started["newyear_hunt"],
        20261230
    );
    assert_eq!(
        w.players[&1].character.seasonal_rolls["newyear_hunt"],
        20261229
    );
}
#[test]
fn newyear_exact_five_percent_threshold_and_no_repeated_daily_award() {
    assert!(seasonal_hunt::wins_mount(0., 0.05));
    assert!(seasonal_hunt::wins_mount(0.049999, 0.05));
    assert!(!seasonal_hunt::wins_mount(0.05, 0.05));
    assert!(!seasonal_hunt::wins_mount(0.999, 0.05));
    let mut w = fixture();
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .grant_mount("horse");
    w.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert_eq!(w.players[&1].character.mount, "horse");
    let owned = w.players[&1].character.mounts.clone();
    gather(&mut w);
    for p in w.players.values_mut() {
        p.combat_left = 0.;
        p.character.hp = p.character.max_hp();
    }
    w.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert_eq!(w.players[&1].character.mounts, owned);
    let state = serde_json::to_string(&w.players[&1].character).unwrap();
    let loaded: Character = serde_json::from_str(&state).unwrap();
    assert_eq!(loaded.seasonal_rolls["newyear_hunt"], 20261229);
    assert!(loaded.owns_mount("rocket"));
}
#[test]
fn newyear_failed_roll_earns_quest_but_no_mount() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 1;
    w.hit_slime(e, 1, 1e12, false);
    assert!(
        w.players
            .values()
            .all(|p| !p.character.owns_mount("rocket"))
    );
}
#[test]
fn newyear_wipe_hires_and_january_third_cleanup() {
    let mut w = fixture();
    let owner = w.players[&1].character.id.clone();
    for s in 2..=5 {
        w.players.get_mut(&s).unwrap().merc = Some(owner.clone());
    }
    w.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    let enemy = w.seasonal_hunt.as_ref().unwrap().enemy;
    for p in w.players.values_mut() {
        p.character.hp = 0.;
    }
    for _ in 0..170 {
        w.update_festival_hunt();
    }
    assert!(w.seasonal_hunt.is_none());
    assert_eq!(w.slimes[enemy].state, "waiting");
    for p in w.players.values_mut() {
        p.character.hp = p.character.max_hp();
        p.combat_left = 0.;
    }
    gather(&mut w);
    w.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .grant_mount("rocket");
    date(&mut w, 1798930800);
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    assert_eq!(w.slimes[enemy].state, "waiting");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .all(|q| q.id != "newyear_hunt")
    );
    assert!(w.players[&1].character.owns_mount("rocket"));
    assert!(w.summon_festival(1, seasonal_hunt::NEWYEAR).is_err());
}
#[test]
fn newyear_city_scope_catalog_and_calendar_edges() {
    let mut w = world();
    date(&mut w, 1798498799);
    assert!(w.festival_view(seasonal_hunt::NEWYEAR).is_null());
    date(&mut w, 1798498800);
    assert!(!w.festival_view(seasonal_hunt::NEWYEAR).is_null());
    date(&mut w, 1798930799);
    assert!(!w.festival_view(seasonal_hunt::NEWYEAR).is_null());
    date(&mut w, 1798930800);
    assert!(w.festival_view(seasonal_hunt::NEWYEAR).is_null());
    let seasonal_quests: Vec<_> = w
        .maps
        .iter()
        .flat_map(|m| &m.quests)
        .filter(|q| crate::seasonal::quest_event(&q.id) == Some("newyear"))
        .collect();
    assert_eq!(seasonal_quests.len(), 1);
    assert_eq!(seasonal_quests[0].id, "newyear_hunt");
    assert!(crate::seasonal::daily("newyear_hunt"));
    assert!(w.festival_view(seasonal_hunt::CHRISTMAS).is_null());
    assert!(w.maps[2].line_clear(at(103., 100.), at(112., 100.), 1.2));
    assert_eq!(
        w.spawns
            .iter()
            .filter(|s| s.kind == "starrocketeer")
            .count(),
        1
    );
    for npc in ["baker", "city_bard", "nacre_gardener", "asterion_singer"] {
        assert!(crate::seasonal::giver("newyear_hunt", npc));
    }
}

#[test]
fn newyear_hires_never_roll_and_a_full_bag_cannot_lose_the_mount() {
    let mut w = fixture();
    let owner = w.players[&1].character.id.clone();
    for s in 2..=5 {
        w.players.get_mut(&s).unwrap().merc = Some(owner.clone());
    }
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.inventory = crate::items::ITEMS
        .iter()
        .filter(|i| i.kind == "material")
        .take(c.bag_capacity())
        .map(|i| crate::items::ItemStack {
            item: i.id.clone(),
            quantity: 1,
        })
        .collect();
    assert_eq!(c.bag_used(), c.bag_capacity());
    let cells = c.bag_used();
    w.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert!(w.players[&1].character.owns_mount("rocket"));
    assert_eq!(w.players[&1].character.bag_used(), cells);
    for s in 2..=5 {
        assert!(!w.players[&s].character.owns_mount("rocket"));
        assert!(
            !w.players[&s]
                .character
                .seasonal_rolls
                .contains_key("newyear_hunt")
        );
    }
}

#[test]
fn newyear_cross_year_daily_period_and_permanent_claimed_achievement() {
    let mut w = fixture();
    date(&mut w, 1798758000); // Jan 1 2027, Stockholm midnight.
    let active = w
        .seasonal
        .cached
        .iter()
        .find(|e| e.id == "newyear")
        .unwrap();
    assert_eq!(active.year, 2026);
    assert_eq!(active.day, 20270101);
    accept(&mut w, 1, "baker");
    assert_eq!(
        w.players[&1].character.seasonal_started["newyear_hunt"],
        20270101
    );
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.sync_achievements();
    assert!(!c.achievements.completed.contains("newyear"));
    c.quests
        .iter_mut()
        .find(|q| q.id == "newyear_hunt")
        .unwrap()
        .counts = vec![1];
    c.sync_achievements();
    assert!(!c.achievements.completed.contains("newyear"));
    let points = c.achievement_points();
    w.time += 1.;
    w.interact(1, "baker", Some("quest:claim:newyear_hunt"));
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.sync_achievements();
    assert!(c.achievements.completed.contains("newyear"));
    // This first quest also unlocks the existing five-point first-quest achievement.
    assert!(c.achievement_points() >= points + 25);
    assert_eq!(
        c.achievement_view()["entries"]
            .as_array()
            .unwrap()
            .iter()
            .find(|a| a["id"] == "newyear")
            .unwrap()["points"],
        25
    );
    let awarded = c.achievement_points();
    assert!(c.sync_achievements().is_empty());
    assert_eq!(c.achievement_points(), awarded);
    assert!(!c.owns_mount("rocket")); // Achievement does not require a mount roll win.
    assert_eq!(c.achievement_title(), "");
    let saved = serde_json::to_string(c).unwrap();
    let mut restored: Character = serde_json::from_str(&saved).unwrap();
    restored.quests.clear();
    restored.seasonal_claims.clear();
    assert!(restored.sync_achievements().is_empty());
    assert!(restored.achievements.completed.contains("newyear"));
    assert_eq!(seasonal_hunt::NEWYEAR.chance, 0.05);
    assert!(seasonal_hunt::wins_mount(
        0.049999,
        seasonal_hunt::NEWYEAR.chance
    ));
    assert!(!seasonal_hunt::wins_mount(
        0.05,
        seasonal_hunt::NEWYEAR.chance
    ));
    assert_eq!(crate::model::mount_def("rocket").unwrap().speed, 1.6);
    // Abandon/reaccept and a later winning RNG value cannot restore a spent attempt.
    let mut again = fixture();
    again.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    let enemy = again.seasonal_hunt.as_ref().unwrap().enemy;
    again.rng = 1;
    again.hit_slime(enemy, 1, 1e12, false);
    again.abandon_quest(1, "newyear_hunt");
    accept(&mut again, 1, "city_bard");
    gather(&mut again);
    for p in again.players.values_mut() {
        p.combat_left = 0.;
        p.character.hp = p.character.max_hp();
    }
    again.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    let enemy = again.seasonal_hunt.as_ref().unwrap().enemy;
    again.rng = 0;
    again.hit_slime(enemy, 1, 1e12, false);
    assert!(!again.players[&1].character.owns_mount("rocket"));
    assert_eq!(
        again.players[&1].character.seasonal_rolls["newyear_hunt"],
        20261229
    );
    let mut legacy = Character::mercenary(Class::Warrior, 1, "Legacy NY");
    legacy
        .seasonal_claims
        .insert("newyear_hunt".into(), 20251230);
    assert!(legacy.sync_achievements().contains(&"newyear".into()));
    assert!(legacy.sync_achievements().is_empty());
}
#[test]
fn newyear_requires_five_alive_nearby_dismounted_fighters_and_current_quest() {
    let mut w = fixture();
    for mode in 0..5 {
        let p = w.players.get_mut(&5).unwrap();
        p.character.hp = if mode == 0 { 0. } else { p.character.max_hp() };
        p.character.mounted = mode == 1;
        p.combat_left = if mode == 2 { 3. } else { 0. };
        p.character.zone = if mode == 3 { 0 } else { 2 };
        p.character.x = if mode == 4 { 140. } else { 103. };
        p.character.y = 100.;
        assert!(
            w.summon_festival(1, seasonal_hunt::NEWYEAR).is_err(),
            "mode {mode}"
        );
    }
    gather(&mut w);
    let p = w.players.get_mut(&5).unwrap();
    p.character.hp = p.character.max_hp();
    p.character.mounted = false;
    p.combat_left = 0.;
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .seasonal_started
        .insert("newyear_hunt".into(), 20261228);
    assert!(w.summon_festival(1, seasonal_hunt::NEWYEAR).is_err());
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .seasonal_started
        .insert("newyear_hunt".into(), 20261229);
    w.summon_festival(1, seasonal_hunt::NEWYEAR).unwrap();
    for session in 1..=5 {
        w.players.remove(&session);
    }
    for _ in 0..170 {
        w.update_festival_hunt();
    }
    assert!(w.seasonal_hunt.is_none());
}
