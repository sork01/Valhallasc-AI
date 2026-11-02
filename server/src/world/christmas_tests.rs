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
    w.interact(s, npc, Some("quest:accept:christmas_hunt"));
}
fn fixture() -> World {
    let mut w = world();
    calm(&mut w);
    date(&mut w, 1797289200);
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
fn christmas_summon_scales_to_highest_and_freezes_five_participants() {
    let mut w = fixture();
    place(&mut w, 2, 2, at(110.5, 100.));
    w.summon_festival(2, seasonal_hunt::CHRISTMAS).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    assert_eq!(w.slimes[e].level, 26);
    let hp = w.slimes[e].max_hp;
    w.players.get_mut(&5).unwrap().character.level = 99;
    assert_eq!(w.slimes[e].max_hp, hp);
    assert!(w.summon_festival(1, seasonal_hunt::CHRISTMAS).is_err());
    let _rx = join(&mut w, 6, Class::Mage);
    place(&mut w, 6, 2, at(103., 101.));
    assert_eq!(w.hit_slime(e, 6, 1e12, false), 0.);
    assert_eq!(w.slimes[e].hp, hp);
    assert!(w.festival_view(seasonal_hunt::HALLOWEEN).is_null());
    assert_eq!(w.festival_view(seasonal_hunt::CHRISTMAS)["level"], 26);
}
#[test]
fn christmas_independent_daily_rolls_shared_city_claim_and_next_day() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::CHRISTMAS).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 1234567;
    w.hit_slime(e, 1, 1e12, false);
    for s in 1..=5 {
        let c = &w.players[&s].character;
        assert_eq!(c.owns_mount("reindeer"), s == 2 || s == 4);
        assert_eq!(c.seasonal_rolls["christmas_hunt"], 20261215);
        assert_eq!(
            c.quests
                .iter()
                .find(|q| q.id == "christmas_hunt")
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
    w.interact(1, "nacre_gardener", Some("quest:claim:christmas_hunt"));
    assert_eq!(w.players[&1].character.gold, gold + 300);
    assert_eq!(
        w.players[&1].character.seasonal_claims["christmas_hunt"],
        20261215
    );
    accept(&mut w, 1, "asterion_singer");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "christmas_hunt")
            .unwrap()
            .claimed
    );
    date(&mut w, 1797375600);
    accept(&mut w, 1, "asterion_singer");
    assert!(
        !w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "christmas_hunt")
            .unwrap()
            .claimed
    );
    assert_eq!(
        w.players[&1].character.seasonal_started["christmas_hunt"],
        20261216
    );
    assert_eq!(
        w.players[&1].character.seasonal_rolls["christmas_hunt"],
        20261215
    );
}
#[test]
fn christmas_exact_five_percent_threshold_and_no_repeated_daily_award() {
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
    w.summon_festival(1, seasonal_hunt::CHRISTMAS).unwrap();
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
    w.summon_festival(1, seasonal_hunt::CHRISTMAS).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert_eq!(w.players[&1].character.mounts, owned);
    let state = serde_json::to_string(&w.players[&1].character).unwrap();
    let loaded: Character = serde_json::from_str(&state).unwrap();
    assert_eq!(loaded.seasonal_rolls["christmas_hunt"], 20261215);
    assert!(loaded.owns_mount("reindeer"));
}
#[test]
fn christmas_failed_roll_earns_quest_but_no_mount() {
    let mut w = fixture();
    w.summon_festival(1, seasonal_hunt::CHRISTMAS).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 1;
    w.hit_slime(e, 1, 1e12, false);
    assert!(
        w.players
            .values()
            .all(|p| !p.character.owns_mount("reindeer"))
    );
}
#[test]
fn christmas_wipe_hires_and_december_twenty_ninth_cleanup() {
    let mut w = fixture();
    let owner = w.players[&1].character.id.clone();
    for s in 2..=5 {
        w.players.get_mut(&s).unwrap().merc = Some(owner.clone());
    }
    w.summon_festival(1, seasonal_hunt::CHRISTMAS).unwrap();
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
    w.summon_festival(1, seasonal_hunt::CHRISTMAS).unwrap();
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .grant_mount("reindeer");
    date(&mut w, 1798498800);
    w.update_festival_hunt();
    assert!(w.seasonal_hunt.is_none());
    assert_eq!(w.slimes[enemy].state, "waiting");
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .all(|q| q.id != "christmas_hunt")
    );
    assert!(w.players[&1].character.owns_mount("reindeer"));
    assert!(w.summon_festival(1, seasonal_hunt::CHRISTMAS).is_err());
}
#[test]
fn christmas_city_scope_catalog_and_calendar_edges() {
    let mut w = world();
    date(&mut w, 1797289199);
    assert!(w.festival_view(seasonal_hunt::CHRISTMAS).is_null());
    date(&mut w, 1797289200);
    assert!(!w.festival_view(seasonal_hunt::CHRISTMAS).is_null());
    date(&mut w, 1798498799);
    assert!(!w.festival_view(seasonal_hunt::CHRISTMAS).is_null());
    date(&mut w, 1798498800);
    assert!(w.festival_view(seasonal_hunt::CHRISTMAS).is_null());
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let zones = std::iter::once(&data).chain(data["zones"].as_array().unwrap());
    let mut annual = 0;
    for (i, z) in zones.enumerate() {
        let count = z["christmasDecor"].as_array().map_or(0, Vec::len);
        assert_eq!(count > 0, [0, 4, 9, 17].contains(&i));
        for q in z["quests"].as_array().unwrap() {
            if q["season"] == "christmas" && q["seasonCadence"] != "daily" {
                annual += 1;
            }
        }
    }
    assert_eq!(annual, 4);
    assert!(w.maps[2].line_clear(at(103., 100.), at(112., 100.), 1.2));
    assert_eq!(w.spawns.iter().filter(|s| s.kind == "grinch").count(), 1);
    for npc in ["baker", "city_bard", "nacre_gardener", "asterion_singer"] {
        assert!(crate::seasonal::giver("christmas_hunt", npc));
    }
}

#[test]
fn christmas_hires_never_roll_and_a_full_bag_cannot_lose_the_mount() {
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
    w.summon_festival(1, seasonal_hunt::CHRISTMAS).unwrap();
    let e = w.seasonal_hunt.as_ref().unwrap().enemy;
    w.rng = 0;
    w.hit_slime(e, 1, 1e12, false);
    assert!(w.players[&1].character.owns_mount("reindeer"));
    assert_eq!(w.players[&1].character.bag_used(), cells);
    for s in 2..=5 {
        assert!(!w.players[&s].character.owns_mount("reindeer"));
        assert!(
            !w.players[&s]
                .character
                .seasonal_rolls
                .contains_key("christmas_hunt")
        );
    }
}
