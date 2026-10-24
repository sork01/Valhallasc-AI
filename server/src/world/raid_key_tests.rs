use super::*;
fn hero(w: &mut World, session: u64, active: bool) -> mpsc::Receiver<Value> {
    let (tx, rx) = mpsc::channel(4096);
    w.join(session, None, Some(Look::default()), tx).unwrap();
    let c = w.maps[0].crosses[0].clone();
    let p = w.players.get_mut(&session).unwrap();
    p.character.level = 99;
    p.character.hp = p.character.max_hp();
    p.character.x = c.x;
    p.character.y = c.y + 1.;
    if active {
        p.character.quests.push(QuestProgress {
            id: "raid_key".into(),
            counts: vec![0; 10],
            claimed: false,
            completions: 0,
        });
    }
    rx
}
fn world() -> World {
    World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
}
fn summon(w: &mut World) -> usize {
    let cross = w.maps[0].crosses[0].id.clone();
    w.start_raid_channel(1, &cross).unwrap();
    w.time += 3.;
    w.update_raid_key();
    w.slimes
        .iter()
        .position(|s| s.kind == raid_key::KIND && s.zone == 0 && !s.dead)
        .unwrap()
}
#[test]
fn raid_key_ten_crosses_have_safe_reachable_ground_and_sleepers() {
    let mut w = world();
    let _rx = hero(&mut w, 1, true);
    assert_eq!(w.maps.iter().map(|m| m.crosses.len()).sum::<usize>(), 10);
    for (zone, map) in w
        .maps
        .iter()
        .enumerate()
        .filter(|(_, m)| !m.crosses.is_empty())
    {
        let c = &map.crosses[0];
        let at = Point { x: c.x, y: c.y };
        let mut p = at;
        map.collide(&mut p, PLAYER_RADIUS);
        assert!(p.distance(at) < 0.01, "{}: cross blocked", c.id);
        assert!(!map.in_city(at));
        assert!(
            map.slimes
                .iter()
                .filter(|s| s.kind != raid_key::KIND)
                .all(|s| at.distance(Point { x: s.x, y: s.y }) >= 8.)
        );
        let enemy = w
            .slimes
            .iter()
            .find(|s| s.kind == raid_key::KIND && s.zone == zone)
            .unwrap();
        assert!(enemy.dead);
        assert_eq!(enemy.level, 99);
        assert!(crate::items::is_elite(&enemy.kind));
        assert!(item(&c.shard).is_some_and(crate::items::is_quest_item));
    }
}
#[test]
fn raid_key_inert_cross_refuses_missing_quest_piece_level_and_range() {
    let mut w = world();
    let _rx = hero(&mut w, 1, false);
    let id = w.maps[0].crosses[0].id.clone();
    assert!(w.start_raid_channel(1, &id).is_err());
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .quests
        .push(QuestProgress {
            id: "raid_key".into(),
            counts: vec![0; 10],
            claimed: false,
            completions: 0,
        });
    w.players.get_mut(&1).unwrap().character.level = 98;
    assert!(w.start_raid_channel(1, &id).is_err());
    w.players.get_mut(&1).unwrap().character.level = 99;
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .add_item("ember_shard_0", 1);
    assert!(w.start_raid_channel(1, &id).is_err());
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .inventory
        .retain(|s| s.item != "ember_shard_0");
    w.players.get_mut(&1).unwrap().character.x += 10.;
    assert!(w.start_raid_channel(1, &id).is_err());
    assert!(w.start_raid_channel(1, "raid_cross_1").is_err());
}
#[test]
fn raid_key_channel_is_three_seconds_interruptible_and_exclusive() {
    let mut w = world();
    let _a = hero(&mut w, 1, true);
    let _b = hero(&mut w, 2, true);
    let id = w.maps[0].crosses[0].id.clone();
    w.start_raid_channel(1, &id).unwrap();
    assert!(w.start_raid_channel(2, &id).is_err());
    w.time += 2.9;
    w.update_raid_key();
    assert!(
        w.slimes
            .iter()
            .filter(|s| s.kind == raid_key::KIND)
            .all(|s| s.dead)
    );
    w.players.get_mut(&1).unwrap().character.x += 0.1;
    w.update_raid_key();
    w.start_raid_channel(2, &id).unwrap();
    w.players.get_mut(&2).unwrap().last_hurt = w.time;
    w.update_raid_key();
    w.start_raid_channel(1, &id).unwrap();
    w.time += 3.;
    w.update_raid_key();
    let s = w
        .slimes
        .iter()
        .find(|s| s.kind == raid_key::KIND && !s.dead)
        .unwrap();
    assert!(s.hunt);
    assert_eq!(s.level, 99);
    assert_eq!(s.xp, 0);
    assert_eq!(s.gold, 0);
    assert!(w.start_raid_channel(2, &id).is_err());
}
#[test]
fn raid_key_private_shards_only_for_near_living_eligible_contributors() {
    let mut w = world();
    let mut receivers = Vec::new();
    for s in 1..=8 {
        receivers.push(hero(&mut w, s, s != 4));
    }
    let id = summon(&mut w);
    let owner = w.players[&2].character.id.clone();
    w.players.get_mut(&8).unwrap().merc = Some(owner);
    for s in [1, 3, 4, 5, 6, 7, 8] {
        w.hit_slime(id, s, 1., false);
    }
    w.players.get_mut(&3).unwrap().character.x = 90.;
    w.players.get_mut(&3).unwrap().character.y = 90.;
    w.players
        .get_mut(&5)
        .unwrap()
        .character
        .add_item("ember_shard_0", 1);
    let pending = w.players[&6].character.id.clone();
    let at = w.slimes[id].point();
    w.item_drop(&pending, 0, at, "ember_shard_0", 1);
    w.players.get_mut(&7).unwrap().character.hp = 0.;
    let (gold, xp) = (w.players[&1].character.gold, w.players[&1].character.xp);
    w.hit_slime(id, 1, 1e12, false);
    assert_eq!(w.players[&1].character.gold, gold);
    assert_eq!(w.players[&1].character.xp, xp);
    assert_eq!(w.drops.len(), 3);
    assert!(
        w.drops
            .iter()
            .all(|d| d.item.as_deref() == Some("ember_shard_0"))
    );
    for s in [1, 2, 6] {
        assert_eq!(
            w.drops
                .iter()
                .filter(|d| d.owner == w.players[&s].character.id)
                .count(),
            1
        );
    }
    for s in [3, 4, 5, 7, 8] {
        assert!(
            !w.drops
                .iter()
                .any(|d| d.owner == w.players[&s].character.id)
        );
    }
    assert!(
        w.start_raid_channel(1, "raid_cross_0").is_err(),
        "pending drop prevents duplicates"
    );
    w.players.get_mut(&3).unwrap().character.x = 38.;
    w.players.get_mut(&3).unwrap().character.y = 48.;
    assert!(
        w.start_raid_channel(3, "raid_cross_0").is_ok(),
        "death re-arms immediately for another hero"
    );
}
#[test]
fn raid_key_zone_empty_despawns_and_mercenary_cannot_hold_cross() {
    let mut w = world();
    let _a = hero(&mut w, 1, true);
    let _b = hero(&mut w, 2, true);
    let id = summon(&mut w);
    w.players.get_mut(&2).unwrap().merc = Some(w.players[&1].character.id.clone());
    w.players.get_mut(&1).unwrap().character.zone = 45;
    w.update_raid_key();
    assert!(w.slimes[id].dead);
    w.players.get_mut(&1).unwrap().character.zone = 0;
    assert!(w.start_raid_channel(1, "raid_cross_0").is_ok());
}
#[test]
fn raid_key_evade_fully_heals_and_herald_does_not_enter_sanctuary() {
    let mut w = world();
    let _a = hero(&mut w, 1, true);
    let id = summon(&mut w);
    w.slimes[id].hp = 1.;
    w.slimes[id].state = "return".into();
    w.slimes[id].x = w.slimes[id].hx;
    w.slimes[id].y = w.slimes[id].hy;
    w.update_slime(id);
    assert_eq!(w.slimes[id].hp, w.slimes[id].max_hp);
    w.slimes[id].x = 36.;
    w.slimes[id].y = 71.5;
    w.slimes[id].goal = Point { x: 36., y: 74. };
    w.slimes[id].state = "lunge".into();
    w.slimes[id].st = 1.;
    w.update_slime(id);
    assert!(!w.maps[0].in_city(w.slimes[id].point()));
}
#[test]
fn raid_key_door_needs_claim_and_keeps_all_shards_permanently() {
    let mut w = world();
    let _a = hero(&mut w, 1, true);
    w.time = 100.;
    if std::env::var_os("MUTATE_RAID_KEY_GATE").is_some() {
        w.maps[45]
            .portals
            .iter_mut()
            .find(|p| p.id == "ew_raid")
            .unwrap()
            .needs_quest = None;
    }
    let door = w.maps[45]
        .portals
        .iter()
        .find(|p| p.id == "ew_raid")
        .unwrap()
        .clone();
    let quest = w.maps[45]
        .quests
        .iter()
        .find(|q| q.id == "raid_key")
        .unwrap()
        .clone();
    let shards: Vec<_> = quest.objectives.iter().map(|o| o.target.clone()).collect();
    let p = w.players.get_mut(&1).unwrap();
    p.character.zone = 45;
    p.character.x = door.x;
    p.character.y = door.y;
    p.portal_at = -100.;
    for shard in &shards[..9] {
        p.character.add_item(shard, 1);
    }
    assert!(!quest_action(&mut p.character, &quest, "claim").2);
    w.use_portal(1);
    assert_eq!(
        w.players[&1].character.zone, 45,
        "nine shards cannot open the door"
    );
    let p = w.players.get_mut(&1).unwrap();
    p.character.add_item(&shards[9], 1);
    p.portal_at = -100.;
    assert!(quest_action(&mut p.character, &quest, "claim").2);
    assert_eq!(p.character.quantity("ember_key"), 1);
    assert!(shards.iter().all(|s| p.character.quantity(s) == 1));
    w.use_portal(1);
    assert!(w.maps[w.players[&1].character.zone].raid);
}

#[test]
fn raid_key_unkeyed_saved_raid_occupant_wakes_outside_without_grandfathering() {
    let mut w = world();
    let (tx, _rx) = mpsc::channel(4096);
    let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
    let token = welcome["token"].as_str().unwrap().to_string();
    let copy = w.instances.iter().find(|i| i.template == 46).unwrap().zone;
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.zone = copy;
    c.x = 84.;
    c.y = 272.;
    w.leave(1);
    let (tx, _rx) = mpsc::channel(4096);
    w.join(2, Some(token), None, tx).unwrap();
    let c = &w.players[&2].character;
    assert_eq!(c.zone, 45);
    assert!(c.point().distance(Point { x: 127., y: 25. }) < 1.);
    assert!(
        !c.quests
            .iter()
            .any(|q| q.id == "raid_key" && q.completions > 0)
    );
}
