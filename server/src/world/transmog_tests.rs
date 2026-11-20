use super::super::wyrd_tests::drain;
use super::*;

fn fixture() -> (World, mpsc::Receiver<Value>, String, String) {
    let mut w = World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
    let (tx, rx) = mpsc::channel(512);
    let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
    let token = welcome["token"].as_str().unwrap().to_owned();
    let npc = w.maps[4]
        .npcs
        .iter()
        .find(|n| n.id == "city_transmog")
        .unwrap()
        .clone();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.zone = 4;
    c.x = npc.x;
    c.y = npc.y;
    let id = crate::items::ITEMS
        .iter()
        .find(|i| {
            i.kind == "armor"
                && i.class == Some(Class::Warrior)
                && i.rarity == "epic"
                && i.required_level > 50
        })
        .unwrap()
        .id
        .clone();
    c.add_item(&id, 1);
    c.gold = 50_000;
    (w, rx, token, id)
}
fn apply(w: &mut World, id: &str) {
    w.message(
        1,
        ClientMessage::Transmogrify {
            npc: "city_transmog".into(),
            changes: BTreeMap::from([("chest".into(), id.into())]),
        },
    );
}

#[test]
fn transmog_world_applies_saves_dialogue_owner_privacy_and_inspect_real_items() {
    let (mut w, mut rx, token, id) = fixture();
    let old = w.players[&1].character.look.clone();
    let stats = w.players[&1].character.stats();
    apply(&mut w, &id);
    let c = &w.players[&1].character;
    assert_eq!(c.gold, 49_500);
    assert_eq!(c.wardrobe.slots["chest"], id);
    assert_eq!(
        serde_json::to_value(&c.look).unwrap(),
        serde_json::to_value(&old).unwrap()
    );
    assert_eq!(c.stats(), stats);
    let saved = w.store.load(&token).unwrap().unwrap();
    assert_eq!(saved.wardrobe.slots["chest"], id);
    assert_eq!(saved.gold, c.gold);
    assert!(saved.wardrobe.unlocked.contains(&id));
    let dialogue = drain(&mut rx)
        .into_iter()
        .find(|p| p["type"] == "dialogue")
        .unwrap();
    assert!(
        dialogue["wardrobe"]
            .as_array()
            .unwrap()
            .contains(&json!(id))
    );
    assert_eq!(dialogue["transmogPrice"], 500);
    assert_eq!(dialogue["transmogs"]["chest"], id);
    let owner = w.players[&1].snapshot();
    assert_ne!(
        owner["look"]["warriorArmor"],
        owner["equippedLook"]["warriorArmor"]
    );
    let mut other = json!({"players":[owner], "events":[]});
    crate::visibility::filter_view(&mut other, "stranger");
    for key in ["equippedLook", "wardrobe", "transmogs"] {
        assert!(other["players"][0].get(key).is_none(), "{key}");
    }
    assert_eq!(
        other["players"][0]["look"]["warriorArmor"],
        item(&id).unwrap().variant.as_deref().unwrap()
    );
    let (tx, mut rx2) = mpsc::channel(512);
    w.join(
        2,
        None,
        Some(Look {
            name: "Watcher".into(),
            ..Look::default()
        }),
        tx,
    )
    .unwrap();
    let at = w.players[&1].character.point();
    let watcher = w.players.get_mut(&2).unwrap();
    watcher.character.zone = 4;
    watcher.character.x = at.x + 2.;
    watcher.character.y = at.y;
    // Use the real inspect request, whose answer is deliberately whitelisted.
    w.inspect(2, &saved.id);
    let inspect = drain(&mut rx2)
        .into_iter()
        .find(|p| p["type"] == "inspect")
        .unwrap();
    assert_eq!(inspect["ok"], true);
    assert_eq!(inspect["transmogs"]["chest"], id);
    assert_eq!(
        inspect["look"]["warriorArmor"],
        other["players"][0]["look"]["warriorArmor"]
    );
    let chest = inspect["slots"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["slot"] == "chest")
        .unwrap();
    assert_ne!(chest["item"], id);
    assert_eq!(
        chest["item"],
        crate::items::equipment(Class::Warrior, "armor", &old.warrior_armor)
            .unwrap()
            .id
    );
    assert!(inspect.get("wardrobe").is_none());
    assert!(inspect.get("gold").is_none());
}

#[test]
fn transmog_world_refuses_wrong_npc_range_life_combat_mount_and_trade_without_charging() {
    let (mut w, mut rx, token, id) = fixture();
    let original = w.players[&1].character.point();
    for state in [
        "distance",
        "dead",
        "combat",
        "mount",
        "travel",
        "frozen",
        "cutscene",
        "wrong_npc",
    ] {
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.x = original.x;
            p.character.hp = 100.;
            p.combat_left = 0.;
            p.character.mounted = false;
            p.character.spark_travel = None;
            p.frozen = false;
            p.cutscene_until = 0.;
            match state {
                "distance" => p.character.x += 100.,
                "dead" => p.character.hp = 0.,
                "combat" => p.combat_left = 3.,
                "mount" => p.character.mounted = true,
                "travel" => {
                    p.character.spark_travel = Some(crate::model::SparkTravel {
                        destination: "Test".into(),
                        stops: vec![],
                        points: vec![],
                        next: 0,
                    })
                }
                "frozen" => p.frozen = true,
                "cutscene" => p.cutscene_until = w.time + 5.,
                _ => {}
            }
        }
        if state == "wrong_npc" {
            w.transmogrify(
                1,
                "city_smith",
                BTreeMap::from([("chest".into(), id.clone())]),
            );
        } else {
            apply(&mut w, &id);
        }
        assert_eq!(w.players[&1].character.gold, 50_000, "{state}");
        assert!(w.players[&1].character.wardrobe.slots.is_empty(), "{state}");
        drain(&mut rx);
    }
    assert!(
        w.store
            .load(&token)
            .unwrap()
            .unwrap()
            .wardrobe
            .slots
            .is_empty()
    );
}

#[test]
fn transmog_world_pending_trade_blocks_changes() {
    let (mut w, _rx, _, id) = fixture();
    let (tx, _other_rx) = mpsc::channel(512);
    w.join(
        2,
        None,
        Some(Look {
            name: "Trader".into(),
            ..Look::default()
        }),
        tx,
    )
    .unwrap();
    let at = w.players[&1].character.point();
    let other = w.players.get_mut(&2).unwrap();
    other.character.zone = 4;
    other.character.x = at.x + 1.;
    other.character.y = at.y;
    let target = other.character.id.clone();
    w.trade(1, TradeCommand::Request { id: target });
    assert!(w.trade_index(&w.players[&1].character.id).is_some());
    apply(&mut w, &id);
    assert_eq!(w.players[&1].character.gold, 50_000);
    assert!(w.players[&1].character.wardrobe.slots.is_empty());
}

#[test]
fn transmog_world_four_city_masters_are_real_and_reachable() {
    let (w, _, _, _) = fixture();
    for (zone, name) in [
        (4, "city_transmog"),
        (9, "nacre_transmog"),
        (17, "asterion_transmog"),
        (24, "hw_transmog"),
    ] {
        let map = &w.maps[zone];
        let npc = map.npcs.iter().find(|n| n.id == name).unwrap();
        assert_eq!(npc.role, "Equipment appearances");
        assert!(npc.offers.iter().any(|o| o.id == "transmogrify"));
        let at = Point { x: npc.x, y: npc.y };
        let mut resolved = at;
        map.collide(&mut resolved, PLAYER_RADIUS);
        assert!(
            at.distance(resolved) < 0.001,
            "{name} intersects an obstacle"
        );
    }
    assert_eq!(
        w.maps
            .iter()
            .flat_map(|m| &m.npcs)
            .filter(|n| n.offers.iter().any(|o| o.id == "transmogrify"))
            .count(),
        4
    );
}
