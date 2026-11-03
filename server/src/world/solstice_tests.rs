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
    w.interact(s, npc, Some("quest:accept:solstice_hunt"));
}
fn fixture() -> World {
    let mut w = world();
    calm(&mut w);
    date(&mut w, 1813183200);
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
fn solstice_calendar_boundaries_city_scope_and_safe_landmark() {
    let mut w = world();
    for (unix, active) in [
        (1813183200 - 1, false),
        (1813183200, true),
        (1813960800 - 1, true),
        (1813960800, false),
    ] {
        date(&mut w, unix);
        assert_eq!(!w.festival_view(seasonal_hunt::SOLSTICE).is_null(), active);
    }
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let mut annual = 0;
    for (i, z) in std::iter::once(&data)
        .chain(data["zones"].as_array().unwrap())
        .enumerate()
    {
        let decor = z["solsticeDecor"].as_array();
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
            .filter(|q| q["season"] == "solstice" && q["seasonCadence"] != "daily")
            .count();
    }
    assert_eq!(annual, 4);
    assert_eq!(
        w.spawns.iter().filter(|s| s.kind == "birchcrown").count(),
        1
    );
    assert!(w.maps[2].line_clear(at(103., 100.), at(112., 100.), 1.2));
    for n in ["baker", "city_bard", "nacre_gardener", "asterion_singer"] {
        assert!(crate::seasonal::giver("solstice_hunt", n));
    }
}
#[test]
fn solstice_highest_level_and_members_are_frozen_outsiders_cannot_hit() {
    let mut w = fixture();
    place(&mut w, 2, 2, at(110.5, 100.));
    w.summon_festival(2, seasonal_hunt::SOLSTICE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    let hp = w.slimes[e].max_hp;
    assert_eq!(w.slimes[e].level, 26);
    w.players.get_mut(&5).unwrap().character.level = 99;
    assert_eq!(w.slimes[e].max_hp, hp);
    let _rx = join(&mut w, 6, Class::Mage);
    place(&mut w, 6, 2, at(103., 101.));
    assert_eq!(w.hit_slime(e, 6, 1e12, false), 0.);
    assert_eq!(w.slimes[e].hp, hp);
    assert!(w.summon_festival(1, seasonal_hunt::SOLSTICE).is_err());
}
#[test]
fn solstice_admission_requires_five_alive_nearby_dismounted_and_calm() {
    let mut w = fixture();
    w.players.get_mut(&5).unwrap().character.hp = 0.;
    assert!(w.summon_festival(1, seasonal_hunt::SOLSTICE).is_err());
    w.players.get_mut(&5).unwrap().character.hp = 100.;
    place(&mut w, 5, 2, at(80., 100.));
    assert!(w.summon_festival(1, seasonal_hunt::SOLSTICE).is_err());
    gather(&mut w);
    w.players.get_mut(&5).unwrap().character.mounted = true;
    assert!(w.summon_festival(1, seasonal_hunt::SOLSTICE).is_err());
    w.players.get_mut(&5).unwrap().character.mounted = false;
    w.players.get_mut(&5).unwrap().combat_left = 1.;
    assert!(w.summon_festival(1, seasonal_hunt::SOLSTICE).is_err());
    w.players.get_mut(&5).unwrap().combat_left = 0.;
    let missing = w.players.remove(&5).unwrap();
    assert!(w.summon_festival(1, seasonal_hunt::SOLSTICE).is_err());
    w.players.insert(5, missing);
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
}
#[test]
fn solstice_independent_daily_rolls_shared_city_claim_and_next_day() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 1234567;
    w.hit_slime(e, 1, 1e12, false);
    for s in 1..=5 {
        let c = &w.players[&s].character;
        assert_eq!(c.owns_mount("sunwoven"), s == 2 || s == 4);
        assert_eq!(c.seasonal_rolls["solstice_hunt"], 20270617);
        assert_eq!(
            c.quests
                .iter()
                .find(|q| q.id == "solstice_hunt")
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
    w.interact(1, "nacre_gardener", Some("quest:claim:solstice_hunt"));
    assert_eq!(w.players[&1].character.gold, gold + 300);
    assert_eq!(
        w.players[&1].character.seasonal_claims["solstice_hunt"],
        20270617
    );
    accept(&mut w, 1, "asterion_singer");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "solstice_hunt")
            .unwrap()
            .claimed
    );
    date(&mut w, 1813269600);
    accept(&mut w, 1, "asterion_singer");
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "solstice_hunt")
            .unwrap()
            .claimed
    );
    assert_eq!(
        w.players[&1].character.seasonal_started["solstice_hunt"],
        20270618
    );
    assert_eq!(
        w.players[&1].character.seasonal_rolls["solstice_hunt"],
        20270617
    );
}
#[test]
fn solstice_exact_five_percent_threshold_and_no_repeated_daily_award() {
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
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert_eq!(w.players[&1].character.mount, "horse");
    assert_eq!(w.players[&1].character.bag_used(), cells);
    let owned = w.players[&1].character.mounts.clone();
    gather(&mut w);
    for p in w.players.values_mut() {
        p.combat_left = 0.;
        p.character.hp = p.character.max_hp();
    }
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert_eq!(w.players[&1].character.mounts, owned);
    let state = serde_json::to_string(&w.players[&1].character).unwrap();
    let loaded: Character = serde_json::from_str(&state).unwrap();
    assert_eq!(loaded.seasonal_rolls["solstice_hunt"], 20270617);
    assert!(loaded.owns_mount("sunwoven"));
}
#[test]
fn solstice_failed_roll_earns_quest_but_no_mount() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 1;
    w.hit_slime(e, 1, 1e12, false);
    assert!(
        w.players
            .values()
            .all(|p| !p.character.owns_mount("sunwoven"))
    );
    assert!(
        w.players
            .values()
            .all(|p| p.character.seasonal_rolls["solstice_hunt"] == 20270617)
    );
    // Abandon/reaccept an unclaimed run cannot restore the already consumed roll.
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.quests.retain(|q| q.id != "solstice_hunt");
    c.seasonal_started.remove("solstice_hunt");
    accept(&mut w, 1, "asterion_singer");
    for p in w.players.values_mut() {
        p.combat_left = 0.;
    }
    gather(&mut w);
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert!(!w.players[&1].character.owns_mount("sunwoven"));
    assert_eq!(
        w.players[&1].character.seasonal_rolls["solstice_hunt"],
        20270617
    );
}
#[test]
fn solstice_hires_count_as_fighters_but_never_receive_rolls_or_rewards() {
    let mut w = fixture();
    let owner = w.players[&1].character.id.clone();
    for s in 2..=5 {
        w.players.get_mut(&s).unwrap().merc = Some(owner.clone());
    }
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert!(w.players[&1].character.owns_mount("sunwoven"));
    for s in 2..=5 {
        let c = &w.players[&s].character;
        assert!(!c.owns_mount("sunwoven"));
        assert!(!c.seasonal_rolls.contains_key("solstice_hunt"));
    }
}
#[test]
fn solstice_kill_credit_excludes_dead_distant_disconnected_and_unaccepted() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
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
            .find(|q| q.id == "solstice_hunt")
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
                .find(|q| q.id == "solstice_hunt")
                .unwrap()
                .counts[0],
            0
        );
    }
}
#[test]
fn solstice_wipe_disconnect_leash_timeout_and_expiry_retire_without_rewards() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
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
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.slimes[e].x = 130.;
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    w.time += 901.;
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    let players = std::mem::take(&mut w.players);
    for _ in 0..170 {
        w.update_festival_hunt();
    }
    assert!(w.seasonal_hunt.is_none());
    w.players = players;
    w.summon_festival(1, seasonal_hunt::SOLSTICE).unwrap();
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .grant_mount("sunwoven");
    date(&mut w, 1813960800);
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .all(|q| q.id != "solstice_hunt")
    );
    assert!(w.players[&1].character.owns_mount("sunwoven"));
    assert!(w.summon_festival(1, seasonal_hunt::SOLSTICE).is_err());
}
