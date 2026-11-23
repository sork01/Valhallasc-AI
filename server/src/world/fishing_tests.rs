use super::*;

pub(super) fn angler() -> (World, mpsc::Receiver<Value>) {
    let mut world =
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
    let (tx, rx) = mpsc::channel(128);
    world
        .join(
            1,
            None,
            Some(Look {
                name: "Fisher".into(),
                ..Default::default()
            }),
            tx,
        )
        .unwrap();
    world.maps[0].fishing_spots.clear();
    world.rng = 1;
    let start = world.maps[0].dock.as_ref().unwrap().start;
    let p = world.players.get_mut(&1).unwrap();
    p.character.x = start.x;
    p.character.y = start.y;
    p.face = Point { x: 1., y: 0. };
    p.character.add_item("rod_twig_rod", 1);
    (world, rx)
}
fn cast(w: &mut World, time: f64) -> f64 {
    w.fish_press(1, time, false);
    let line = w.players[&1].fishing.line.expect("pier cast");
    line.deadline() - 1.2
}

#[test]
fn racial_tidekin_shortens_the_wait_for_water_bites_only() {
    let (mut w, _rx) = angler();
    w.world_clock.set(Some(12.), true).unwrap();
    w.maps[1].fishing_spots.clear();
    w.maps[1].objects =
        vec![serde_json::from_value(json!({"kind":"lava","x":53.,"y":50.,"r":2.})).unwrap()];
    for (zone, phase) in [(0, 0.9), (1, 1.0)] {
        w.weather.set(zone, "clear", None, daynight::unix_ms()).unwrap();
        if zone == 1 {
            let p = w.players.get_mut(&1).unwrap();
            (p.character.zone, p.character.x, p.character.y) = (1, 50., 50.);
            p.character.level = 5;
            p.character.add_item("rod_emberline_rod", 1);
        }
        let mut wait = Vec::new();
        for race in [Race::Human, Race::Tidekin] {
            let p = w.players.get_mut(&1).unwrap();
            p.fishing = Default::default();
            p.character.look.race = race;
            w.rng = 123;
            let bite = cast(&mut w, 20.);
            wait.push(bite - 20.5);
        }
        assert!((wait[0] * phase - wait[1]).abs() < 1e-9, "{zone}: {wait:?}");
    }
}

#[test]
fn fishing_deadline_bags_save_and_privacy() {
    let (mut w, mut rx) = angler();
    w.players.get_mut(&1).unwrap().character.rebirth_tiers = [0, 0, 0, 0, 2];
    let copies = w.players[&1].character.drop_multiplier();
    assert!(copies > 1);
    w.players.get_mut(&1).unwrap().character.mounted = true;
    let bite = cast(&mut w, 20.);
    assert!(!w.players[&1].character.mounted);
    w.fish_update(1, bite + 0.01);
    let mut view = w.snapshot_for(0);
    assert!(view["players"][0]["fishDeadline"].is_number());
    crate::visibility::filter_view(&mut view, "observer");
    assert!(view["players"][0]["fishDeadline"].is_null());
    assert_eq!(view["players"][0]["fishing"]["state"], "bite");
    let deadline = w.players[&1].fishing.line.unwrap().deadline();
    w.rng = 1; // deterministic species catch; junk/treasure are tested separately.
    w.fish_press(1, deadline + 0.25, false);
    w.fish_press(1, deadline + 0.25, false);
    let catch = std::iter::from_fn(|| rx.try_recv().ok())
        .find(|v| v["kind"] == "fish_catch")
        .unwrap();
    let c = &w.players[&1].character;
    let id = catch["item"].as_str().unwrap();
    assert_eq!(c.quantity(id), copies);
    assert_eq!(c.fishing.total, 1);
    let mut saved = serde_json::to_value(c).unwrap();
    let restored: Character = serde_json::from_value(saved.clone()).unwrap();
    assert_eq!(
        restored.fishing.species[id].best_kg,
        catch["kg"].as_u64().unwrap() as u32
    );
    saved.as_object_mut().unwrap().remove("fishing");
    assert_eq!(
        serde_json::from_value::<Character>(saved)
            .unwrap()
            .fishing
            .total,
        0
    );
    cast(&mut w, 50.);
    let deadline = w.players[&1].fishing.line.unwrap().deadline();
    w.fish_press(1, deadline + 0.251, false);
    assert_eq!(w.players[&1].character.fishing.total, 1);
}

#[test]
fn fishing_early_cooldown_fifth_miss_and_cancel() {
    let (mut w, mut rx) = angler();
    for i in 0..5 {
        let t = 20. + i as f64 * 20.;
        let bite = cast(&mut w, t);
        w.fish_press(1, bite - 0.001, false);
        assert!(w.players[&1].fishing.line.is_none());
        w.fish_press(1, bite + 0.5, false);
        assert!(w.players[&1].fishing.line.is_none());
    }
    assert!(
        std::iter::from_fn(|| rx.try_recv().ok())
            .any(|v| v["text"] == "You doze off. Cast again to keep fishing.")
    );
    let bite = cast(&mut w, 150.);
    w.players.get_mut(&1).unwrap().last_hurt += 1.;
    w.fish_press(1, bite + 0.01, false);
    assert_eq!(w.players[&1].character.fishing.total, 0);
    cast(&mut w, 180.);
    w.players.get_mut(&1).unwrap().character.x += 0.61;
    w.fish_update(1, 181.);
    assert!(w.players[&1].fishing.line.is_none());
}
#[test]
fn fishing_cast_blockers_and_full_bag_before_roll() {
    let (mut w, _rx) = angler();
    for blocked in 0..9 {
        let p = w.players.get_mut(&1).unwrap();
        let c = p.character.clone();
        match blocked {
            0 => p.combat_left = 1.,
            1 => p.cutscene_until = 100.,
            2 => p.character.hp = 0.,
            3 => p.merc = Some("hirer".into()),
            4 => p.character.inventory.clear(),
            5 => p.character.y -= 30.,
            6 => p.character.zone = 4,
            7 => p.fishing.shopping = true,
            _ => p.frozen = true,
        }
        w.fish_press(1, 10., false);
        assert!(w.players[&1].fishing.line.is_none(), "blocker {blocked}");
        let p = w.players.get_mut(&1).unwrap();
        p.character = c;
        p.combat_left = 0.;
        p.cutscene_until = 0.;
        p.merc = None;
        p.fishing.shopping = false;
        p.frozen = false;
    }
    let bite = cast(&mut w, 20.);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    for item in ITEMS.iter().filter(|i| i.kind == "fish") {
        c.add_item(&item.id, 1);
        if c.bag_used() >= c.bag_capacity() {
            break;
        }
    }
    assert!(c.bag_used() >= c.bag_capacity());
    let rng = w.rng;
    w.fish_press(1, bite + 0.1, false);
    assert_eq!(w.rng, rng);
    assert_eq!(w.players[&1].character.fishing.total, 0);
    assert!(
        serde_json::from_value::<ClientMessage>(json!({"type":"fish","deadline":123})).is_err()
    );
    assert!(matches!(
        serde_json::from_value::<ClientMessage>(json!({"type":"fish"})),
        Ok(ClientMessage::Fish { auto_aim: false })
    ));
}

#[test]
fn fishing_lava_shore_requires_matching_rod_and_direction() {
    let (mut w, _) = angler();
    // Isolate a known circle so touching another pool cannot make an invalid cast pass.
    w.maps[1].objects =
        vec![serde_json::from_value(json!({"kind":"lava","x":53.,"y":50.,"r":2.})).unwrap()];
    let p = w.players.get_mut(&1).unwrap();
    p.character.zone = 1;
    p.character.x = 50.;
    p.character.y = 50.;
    p.character.level = 5;
    w.fish_press(1, 10., false);
    assert!(w.players[&1].fishing.line.is_none());
    let p = w.players.get_mut(&1).unwrap();
    p.character.add_item("rod_emberline_rod", 1);
    p.face.x = -1.;
    w.fish_press(1, 12., false);
    assert!(w.players[&1].fishing.line.is_none());
    w.players.get_mut(&1).unwrap().face.x = 1.;
    let bite = cast(&mut w, 14.);
    let view = w.players[&1].snapshot();
    assert_eq!(view["fishing"]["lava"], true);
    assert!((51. ..55.).contains(&view["fishing"]["x"].as_f64().unwrap()));
    w.rng = 1;
    w.fish_press(1, bite + 0.01, false);
    let c = &w.players[&1].character;
    let id = c.fishing.species.keys().next().unwrap();
    let fish: Value = serde_json::from_str(include_str!("../../../world/fish.txt")).unwrap();
    assert!(
        fish.as_array()
            .unwrap()
            .iter()
            .any(|s| s["item"] == id.as_str() && s["habitat"] == "Lava")
    );
}

#[test]
fn fishing_rich_spot_rain_and_twilight_scale_wait() {
    let (mut w, _rx) = angler();
    let seed = w.rng;
    let start = 100.;
    w.world_clock.set(Some(12.), true).unwrap();
    w.weather
        .set(0, "clear", None, daynight::unix_ms())
        .unwrap();
    let wait = cast(&mut w, start) - start - 0.5;
    w.players.get_mut(&1).unwrap().fishing = Default::default();
    w.rng = seed;
    w.rich_fishing.insert(
        0,
        vec![fishing::RichSpot {
            point: Point { x: 205., y: 293.5 },
            remaining: 7,
            reserve: None,
        }],
    );
    w.world_clock.set(Some(18.), true).unwrap();
    w.weather
        .set(0, "rain", Some("light"), daynight::unix_ms())
        .unwrap();
    let shorter = cast(&mut w, start) - start - 0.5;
    assert!((shorter - wait * 0.75 * 0.85 * 0.9).abs() < 1e-8);
}

#[test]
fn fishing_achievements_real_hook_ignores_copies_junk_and_misses() {
    let (mut w, mut rx) = angler();
    w.players.get_mut(&1).unwrap().character.rebirth_tiers = [0, 0, 0, 0, 2];
    let bite = cast(&mut w, 20.);
    w.fish_press(1, bite - 0.01, false);
    w.update_achievements();
    assert!(
        !w.players[&1]
            .character
            .achievements
            .completed
            .contains("fish_1")
    );
    let bite = cast(&mut w, 50.);
    w.rng = 0;
    w.fish_press(1, bite + 0.1, false);
    w.update_achievements();
    assert_eq!(w.players[&1].character.fishing.total, 0);
    assert!(
        !w.players[&1]
            .character
            .achievements
            .completed
            .contains("fish_1")
    );
    let bite = cast(&mut w, 80.);
    w.rng = 35;
    w.fish_press(1, bite + 0.1, false);
    w.update_achievements();
    assert_eq!(w.players[&1].character.fishing.total, 0);
    assert!(
        !w.players[&1]
            .character
            .achievements
            .completed
            .contains("fish_1")
    );
    std::iter::from_fn(|| rx.try_recv().ok()).for_each(drop);
    // One deterministic hook lands multiple bag copies but earns just one catch.
    w.players.get_mut(&1).unwrap().character.fishing.total = 98;
    let bite = cast(&mut w, 110.);
    w.rng = 1;
    w.fish_press(1, bite + 0.1, false);
    w.update_achievements();
    let packets: Vec<_> = std::iter::from_fn(|| rx.try_recv().ok()).collect();
    let catch = packets.iter().find(|v| v["kind"] == "fish_catch").unwrap();
    assert!(catch["quantity"].as_u64().unwrap() > 1);
    assert_eq!(w.players[&1].character.fishing.total, 99);
    assert!(
        !w.players[&1]
            .character
            .achievements
            .completed
            .contains("fish_100")
    );
    let bite = cast(&mut w, 140.);
    w.rng = 1;
    w.fish_press(1, bite + 0.1, false);
    w.update_achievements();
    assert_eq!(w.players[&1].character.fishing.total, 100);
    assert!(
        w.players[&1]
            .character
            .achievements
            .completed
            .contains("fish_100")
    );
    let packets: Vec<_> = std::iter::from_fn(|| rx.try_recv().ok()).collect();
    assert_eq!(
        packets
            .iter()
            .filter(|v| v["type"] == "notice"
                && v["text"] == "Achievement earned: A Hundred Hooks (+10 points).")
            .count(),
        1
    );
    w.update_achievements();
    assert!(!std::iter::from_fn(|| rx.try_recv().ok()).any(|v| {
        v["text"]
            .as_str()
            .is_some_and(|s| s.starts_with("Achievement earned:"))
    }));
    let view = w.players[&1].character.achievement_view();
    assert!(
        view["entries"]
            .as_array()
            .unwrap()
            .iter()
            .any(|a| a["id"] == "fish_100" && a["progress"] == 100 && a["complete"] == true)
    );
}

#[test]
fn fishing_achievements_titles_survive_sqlite_reconnect_and_snapshot() {
    let (mut w, mut first_rx) = angler();
    std::iter::from_fn(|| first_rx.try_recv().ok()).for_each(drop);
    let (tx, mut rx) = mpsc::channel(256);
    let welcome = w
        .join(
            2,
            None,
            Some(Look {
                name: "Title Fisher".into(),
                ..Default::default()
            }),
            tx,
        )
        .unwrap();
    let token = welcome["token"].as_str().unwrap().to_owned();
    let c = &mut w.players.get_mut(&2).unwrap().character;
    c.fishing.total = 1000;
    c.fishing.legendary = 2;
    let lava = crate::achievements::catalog()
        .iter()
        .find(|a| a.id == "fish_log_lava")
        .unwrap();
    for id in &lava.members {
        c.fishing.species.insert(
            id.clone(),
            crate::model::FishRecord {
                count: 1,
                best_kg: 20,
            },
        );
    }
    w.update_achievements();
    let points = w.players[&2].character.achievement_points();
    for (id, title) in [("fish_1000", "the Angler"), ("fish_log_lava", "Lavacaster")] {
        w.message(
            2,
            ClientMessage::SelectTitle {
                achievement: id.into(),
            },
        );
        let snapshot = w.players[&2].snapshot();
        assert_eq!(snapshot["achievementTitle"], title);
        assert_eq!(snapshot["achievementTitlePosition"], "suffix");
        assert!(
            std::iter::from_fn(|| rx.try_recv().ok()).any(|m| m["type"] == "achievements"
                && m["selected"] == id
                && m["maximum"] == 4370)
        );
    }
    w.leave(2);
    let saved = w.store.load(&token).unwrap().unwrap();
    assert_eq!(saved.achievement_title(), "Lavacaster");
    assert_eq!(saved.achievement_points(), points);
    assert_eq!(saved.fishing.total, 1000);
    assert_eq!(saved.fishing.species.len(), lava.members.len());
    let (tx, mut rx) = mpsc::channel(256);
    let welcome = w.join(2, Some(token), None, tx).unwrap();
    assert!(
        welcome["snapshot"]["players"]
            .as_array()
            .unwrap()
            .iter()
            .any(|p| p["id"] == saved.id && p["achievementTitle"] == "Lavacaster")
    );
    w.update_achievements();
    assert_eq!(w.players[&2].character.achievement_points(), points);
    assert!(!std::iter::from_fn(|| rx.try_recv().ok()).any(|m| {
        m["text"]
            .as_str()
            .is_some_and(|text| text.starts_with("Achievement earned:"))
    }));
}

#[test]
fn fishing_client_shared_clock_is_unix_time() {
    let (w, _) = angler();
    let before = fishing::now();
    let snapshot = w.snapshot_for(0);
    let time = snapshot["fishingTime"].as_f64().expect("shared Unix clock");
    assert!((before..=fishing::now()).contains(&time));
    assert!(time > 1_700_000_000.);
}
