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
    w.interact(s, npc, Some("quest:accept:valentine_hunt"));
}
fn fixture() -> World {
    let mut w = world();
    calm(&mut w);
    date(&mut w, 1802214000);
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

fn claim(w: &mut World, s: u64, npc: &str) {
    let (z, n) = w
        .maps
        .iter()
        .enumerate()
        .find_map(|(z, m)| m.npcs.iter().find(|n| n.id == npc).cloned().map(|n| (z, n)))
        .unwrap();
    place(w, s, z, at(n.x, n.y));
    w.time += 1.;
    w.interact(s, npc, Some("quest:claim:valentine_hunt"));
}
#[test]
fn valentines_calendar_boundaries_city_scope_and_safe_landmark() {
    let mut w = world();
    for (unix, active) in [
        (1802214000 - 1, false),
        (1802214000, true),
        (1802991600 - 1, true),
        (1802991600, false),
    ] {
        date(&mut w, unix);
        assert_eq!(!w.festival_view(seasonal_hunt::VALENTINE).is_null(), active);
    }
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let mut annual = 0;
    for (i, z) in std::iter::once(&data)
        .chain(data["zones"].as_array().unwrap())
        .enumerate()
    {
        let decor = z["valentineDecor"].as_array();
        assert_eq!(
            decor.is_some_and(|d| d.len() >= 20),
            [0, 4, 9, 17].contains(&i)
        );
        if let Some(decor) = decor {
            for o in decor {
                let c = &z["city"];
                assert!(
                    o["x"].as_f64().unwrap() > c["x0"].as_f64().unwrap()
                        && o["x"].as_f64().unwrap() < c["x1"].as_f64().unwrap()
                );
                assert!(
                    o["y"].as_f64().unwrap() > c["y0"].as_f64().unwrap()
                        && o["y"].as_f64().unwrap() < c["y1"].as_f64().unwrap()
                );
            }
        }
        annual += z["quests"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|q| q["season"] == "valentine" && q["seasonCadence"] != "daily")
            .count();
    }
    assert_eq!(annual, 4);
    assert_eq!(
        w.spawns.iter().filter(|s| s.kind == "briarheart").count(),
        1
    );
    assert!(w.maps[2].line_clear(at(103., 100.), at(112., 100.), 1.2));
    for n in ["baker", "city_bard", "nacre_gardener", "asterion_singer"] {
        assert!(crate::seasonal::giver("valentine_hunt", n));
    }
}
#[test]
fn valentines_highest_level_and_members_are_frozen_outsiders_cannot_hit() {
    let mut w = fixture();
    place(&mut w, 2, 2, at(110.5, 100.));
    w.summon_festival(2, seasonal_hunt::VALENTINE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    let hp = w.slimes[e].max_hp;
    assert_eq!(w.slimes[e].level, 26);
    w.players.get_mut(&5).unwrap().character.level = 99;
    assert_eq!(w.slimes[e].max_hp, hp);
    let _rx = join(&mut w, 6, Class::Mage);
    place(&mut w, 6, 2, at(103., 101.));
    assert_eq!(w.hit_slime(e, 6, 1e12, false), 0.);
    assert_eq!(w.slimes[e].hp, hp);
    assert!(w.summon_festival(1, seasonal_hunt::VALENTINE).is_err());
}
#[test]
fn valentines_admission_requires_five_alive_nearby_dismounted_and_calm() {
    let mut w = fixture();
    w.players.get_mut(&5).unwrap().character.hp = 0.;
    assert!(w.summon_festival(1, seasonal_hunt::VALENTINE).is_err());
    w.players.get_mut(&5).unwrap().character.hp = 100.;
    place(&mut w, 5, 2, at(80., 100.));
    assert!(w.summon_festival(1, seasonal_hunt::VALENTINE).is_err());
    gather(&mut w);
    w.players.get_mut(&5).unwrap().character.mounted = true;
    assert!(w.summon_festival(1, seasonal_hunt::VALENTINE).is_err());
    w.players.get_mut(&5).unwrap().character.mounted = false;
    w.players.get_mut(&5).unwrap().combat_left = 1.;
    assert!(w.summon_festival(1, seasonal_hunt::VALENTINE).is_err());
    w.players.get_mut(&5).unwrap().combat_left = 0.;
    let missing = w.players.remove(&5).unwrap();
    assert!(w.summon_festival(1, seasonal_hunt::VALENTINE).is_err());
    w.players.insert(5, missing);
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
}
#[test]
fn valentines_guaranteed_mount_on_claim_is_full_bag_safe_and_duplicate_safe() {
    let mut w = fixture();
    let owner = w.players[&1].character.id.clone();
    for s in 2..=5 {
        w.players.get_mut(&s).unwrap().merc = Some(owner.clone());
    }
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.grant_mount("horse");
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
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.hit_slime(e, 1, 1e12, false);
    assert!(!w.players[&1].character.owns_mount("roseheart"));
    assert!(
        !w.players[&1]
            .character
            .seasonal_rolls
            .contains_key("valentine_hunt")
    );
    claim(&mut w, 1, "nacre_gardener");
    let c = &w.players[&1].character;
    assert!(c.owns_mount("roseheart"));
    assert_eq!(c.mount, "horse");
    assert_eq!(c.bag_used(), cells);
    let owned = c.mounts.clone();
    claim(&mut w, 1, "asterion_singer");
    assert_eq!(w.players[&1].character.mounts, owned);
    for s in 2..=5 {
        assert!(!w.players[&s].character.owns_mount("roseheart"));
    }
    let state = serde_json::to_string(&w.players[&1].character).unwrap();
    let loaded: Character = serde_json::from_str(&state).unwrap();
    assert!(loaded.owns_mount("roseheart"));
    assert_eq!(loaded.seasonal_claims["valentine_hunt"], 20270210);
}
#[test]
fn valentines_shared_daily_claim_reset_and_repeated_mount_ownership() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.hit_slime(e, 1, 1e12, false);
    claim(&mut w, 1, "nacre_gardener");
    let owned = w.players[&1].character.mounts.clone();
    accept(&mut w, 1, "asterion_singer");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "valentine_hunt")
            .unwrap()
            .claimed
    );
    date(&mut w, 1802214000 + 86400);
    for s in 1..=5 {
        accept(&mut w, s, "baker");
        w.players.get_mut(&s).unwrap().combat_left = 0.;
    }
    gather(&mut w);
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.hit_slime(e, 1, 1e12, false);
    claim(&mut w, 1, "city_bard");
    assert_eq!(
        w.players[&1].character.seasonal_claims["valentine_hunt"],
        20270211
    );
    assert_eq!(w.players[&1].character.mounts, owned);
}
#[test]
fn valentines_kill_credit_excludes_dead_distant_disconnected_and_unaccepted() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.players.get_mut(&2).unwrap().character.hp = 0.;
    place(&mut w, 3, 2, at(80., 100.));
    w.players.remove(&4);
    w.players.get_mut(&5).unwrap().character.quests.clear();
    w.hit_slime(e, 1, 1e12, false);
    assert_eq!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "valentine_hunt")
            .unwrap()
            .counts[0],
        1
    );
    for s in [2, 3] {
        assert_eq!(
            w.players[&s]
                .character
                .quests
                .iter()
                .find(|q| q.id == "valentine_hunt")
                .unwrap()
                .counts[0],
            0
        );
    }
}
#[test]
fn valentines_wipe_disconnect_leash_timeout_and_expiry_retire_without_rewards() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    for p in w.players.values_mut() {
        p.character.hp = 0.;
    }
    for _ in 0..170 {
        w.update_festival_hunt();
    }
    assert!(w.seasonal_hunt.is_none());
    assert_eq!(w.slimes[e].state, "waiting");
    for p in w.players.values_mut() {
        p.character.hp = p.character.max_hp();
        p.combat_left = 0.;
    }
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.slimes[e].x = 130.;
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    w.time += 901.;
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    let players = std::mem::take(&mut w.players);
    for _ in 0..170 {
        w.update_festival_hunt();
    }
    assert!(w.seasonal_hunt.is_none());
    w.players = players;
    w.summon_festival(1, seasonal_hunt::VALENTINE).unwrap();
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .grant_mount("roseheart");
    date(&mut w, 1802991600);
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .all(|q| q.id != "valentine_hunt")
    );
    assert!(w.players[&1].character.owns_mount("roseheart"));
    assert!(w.summon_festival(1, seasonal_hunt::VALENTINE).is_err());
}
#[test]
fn valentines_claimed_set_prefix_points_idempotence_persistence_and_suffix_compatibility() {
    let mut c = Character::mercenary(Class::Warrior, 1, "Sork");
    let members = crate::achievements::catalog()
        .iter()
        .find(|a| a.id == "lovefool")
        .unwrap()
        .members
        .clone();
    for id in &members {
        c.quests.push(QuestProgress {
            id: id.clone(),
            counts: vec![1],
            claimed: false,
            completions: 0,
        });
    }
    c.sync_achievements();
    assert!(!c.achievements.completed.contains("lovefool"));
    assert!(c.select_achievement_title("lovefool").is_err());
    for id in &members[..4] {
        c.seasonal_claims.insert(id.clone(), 2026);
    }
    c.sync_achievements();
    let points = c.achievement_points();
    assert!(!c.achievements.completed.contains("lovefool"));
    c.seasonal_claims.insert("valentine_hunt".into(), 20270210);
    assert_eq!(
        c.sync_achievements()
            .iter()
            .filter(|a| a.as_str() == "lovefool")
            .count(),
        1
    );
    // The fifth distinct quest also earns the existing five-quest achievement (5 points).
    assert_eq!(c.achievement_points(), points + 30);
    assert_eq!(
        crate::achievements::catalog()
            .iter()
            .find(|a| a.id == "lovefool")
            .unwrap()
            .points,
        25
    );
    assert!(c.sync_achievements().is_empty());
    c.select_achievement_title("lovefool").unwrap();
    assert_eq!(c.achievement_title(), "Lovefool");
    assert_eq!(c.achievement_title_position(), "prefix");
    assert_eq!(c.look.name, "Sork");
    c.level = 50;
    c.hp = c.max_hp();
    c.grant_mount("roseheart");
    c.rebirth(at(36., 83.)).unwrap();
    assert_eq!(c.level, 1);
    assert!(c.owns_mount("roseheart"));
    let saved = serde_json::to_string(&c).unwrap();
    let mut loaded: Character = serde_json::from_str(&saved).unwrap();
    crate::seasonal::sync_character(&mut loaded, &[]);
    loaded.sync_achievements();
    assert_eq!(loaded.achievement_title(), "Lovefool");
    assert_eq!(loaded.achievement_title_position(), "prefix");
    loaded.achievements.completed.insert("merry".into());
    loaded.select_achievement_title("merry").unwrap();
    assert_eq!(loaded.achievement_title(), "the Merry");
    assert_eq!(loaded.achievement_title_position(), "suffix");
    assert_eq!(
        crate::model::mount_speed("roseheart"),
        Some(crate::model::MOUNT_SPEED)
    );
}
