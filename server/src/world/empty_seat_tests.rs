use super::*;

fn world() -> World {
    World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
}
fn hero(w: &mut World, session: u64) -> mpsc::Receiver<Value> {
    let (tx, rx) = mpsc::channel(4096);
    w.join(session, None, Some(Look::default()), tx).unwrap();
    rx
}
fn quest(w: &World, id: &str) -> Quest {
    w.maps
        .iter()
        .flat_map(|m| &m.quests)
        .find(|q| q.id == id)
        .unwrap()
        .clone()
}
fn accept(w: &mut World, session: u64, id: &str) {
    let q = quest(w, id);
    let c = &mut w.players.get_mut(&session).unwrap().character;
    c.level = q.min_level;
    c.hp = c.max_hp();
    if let Some(prev) = &q.requires {
        c.quests.push(QuestProgress {
            id: prev.clone(),
            counts: vec![],
            claimed: true,
            completions: 1,
        });
    }
    assert!(quest_action(c, &q, "accept").2);
}
fn place(w: &mut World, session: u64, scene_id: &str) {
    let (zone, at) = w
        .maps
        .iter()
        .enumerate()
        .find_map(|(z, m)| {
            m.places
                .iter()
                .find(|p| p.id == scene_id)
                .map(|p| (z, Point { x: p.x, y: p.y }))
        })
        .unwrap();
    let p = w.players.get_mut(&session).unwrap();
    p.character.zone = zone;
    p.character.x = at.x;
    p.character.y = at.y;
    p.stop();
    p.moving = false;
    p.combat_left = 0.;
    p.stun = 0.;
}
fn ticks(w: &mut World, n: u32) {
    for _ in 0..n {
        w.time += TICK;
        w.update_empty_seat();
    }
}
fn progress(w: &World, session: u64, id: &str) -> Vec<u32> {
    w.players[&session]
        .character
        .quests
        .iter()
        .find(|p| p.id == id)
        .unwrap()
        .counts
        .clone()
}
#[test]
fn empty_seat_campaign_rewards_cover_all_classes_and_real_raid_without_changing_copies() {
    let w = world();
    let campaign: Vec<_> = w
        .maps
        .iter()
        .filter(|m| m.template.is_none())
        .flat_map(|m| &m.quests)
        .filter(|q| q.id.starts_with("es_"))
        .collect();
    assert_eq!(campaign.len(), 28);
    for i in 1..=28 {
        let q = campaign
            .iter()
            .find(|q| q.id == format!("es_{i:02}"))
            .unwrap();
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10);
        assert!(!q.repeatable && q.auto_level.is_none());
        assert!(format!("quest:accept:{}", q.id).len() <= 32);
        assert_eq!(q.requires, (i > 1).then(|| format!("es_{:02}", i - 1)));
        let rarity = if i == 26 {
            "epic"
        } else if i % 5 == 0 {
            "rare"
        } else {
            "uncommon"
        };
        for class in ["warrior", "mage", "assassin", "priest", "hunter"] {
            let choices = &q.reward_choices[class];
            assert_eq!(choices.len(), 2);
            assert_ne!(choices[0], choices[1]);
            for id in choices {
                let item = item(id).unwrap();
                assert_eq!(item.rarity, rarity);
                assert_eq!(serde_json::to_value(item.class).unwrap(), json!(class));
                assert!(item.required_level <= q.level);
            }
        }
    }
    assert_eq!(quest(&w, "es_27").objectives[0].target, "cf_eldmarr");
    assert_eq!(quest(&w, "es_28").min_level, 99);
    assert_eq!(w.maps.iter().filter(|m| m.template.is_none()).count(), 47);
    assert_eq!(w.instances.iter().filter(|i| i.template == 46).count(), 3);
    assert!(
        w.maps[45]
            .portals
            .iter()
            .any(|p| p.needs_quest.as_deref() == Some("raid_key"))
    );
    assert!(!w.maps[0].quests.iter().any(|q| q.id == "raid_key"));
    assert!(w.maps[45].quests.iter().any(|q| q.id == "raid_key"));
}
#[test]
fn empty_seat_sites_and_sleeping_summons_use_actual_server_collision() {
    let w = world();
    for (zone, map) in w
        .maps
        .iter()
        .enumerate()
        .filter(|(_, m)| m.template.is_none())
    {
        for p in map.places.iter().filter(|p| p.id.starts_with("es_")) {
            let at = Point { x: p.x, y: p.y };
            let mut actual = at;
            map.collide(&mut actual, PLAYER_RADIUS);
            assert!(actual.distance(at) < 0.01, "{} blocked", p.id);
            for source in &w.maps {
                for portal in source.portals.iter().filter(|p| p.to == zone) {
                    assert!(
                        at.distance(Point {
                            x: portal.tx,
                            y: portal.ty
                        }) >= 8.
                    );
                }
            }
        }
    }
    let summons: Vec<_> = w
        .slimes
        .iter()
        .filter(|s| s.kind.starts_with("es_foe_"))
        .collect();
    assert_eq!(summons.len(), 13);
    for s in summons {
        assert!(s.dead && s.state == "waiting");
        assert!(!w.maps[s.zone].in_city(s.point()));
        assert!(crate::cathedral::enemy(&s.kind).unwrap().add);
    }
}
#[test]
fn empty_seat_memory_requires_acceptance_stillness_and_unbroken_attention() {
    let mut w = world();
    let _rx = hero(&mut w, 1);
    place(&mut w, 1, "es_01_m");
    ticks(&mut w, 300);
    assert!(w.empty_seat_view(1).is_null());
    accept(&mut w, 1, "es_01");
    ticks(&mut w, 100);
    assert!(w.empty_seat_view(1)["elapsed"].as_f64().unwrap() > 4.);
    w.players.get_mut(&1).unwrap().moving = true;
    ticks(&mut w, 1);
    assert!(w.empty_seat_view(1).is_null());
    w.players.get_mut(&1).unwrap().moving = false;
    ticks(&mut w, 100);
    w.players.get_mut(&1).unwrap().last_hurt += 1.;
    ticks(&mut w, 1);
    assert!(w.empty_seat_view(1)["elapsed"].as_f64().unwrap() < 0.1);
    ticks(&mut w, 280);
    assert_eq!(progress(&w, 1, "es_01"), vec![1]);
    let restored: Character =
        serde_json::from_value(serde_json::to_value(&w.players[&1].character).unwrap()).unwrap();
    assert!(quest(&w, "es_01").ready(restored.quests.iter().find(|p| p.id == "es_01").unwrap()));
}
#[test]
fn empty_seat_flashback_is_ordered_and_death_cannot_finish_it() {
    let mut w = world();
    let _rx = hero(&mut w, 1);
    accept(&mut w, 1, "es_14");
    place(&mut w, 1, "es_14_2");
    ticks(&mut w, 400);
    assert_eq!(progress(&w, 1, "es_14"), vec![0; 3]);
    place(&mut w, 1, "es_14_0");
    ticks(&mut w, 100);
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    ticks(&mut w, 400);
    assert_eq!(progress(&w, 1, "es_14"), vec![0; 3]);
    let p = w.players.get_mut(&1).unwrap();
    p.character.hp = p.character.max_hp();
    for i in 0..3 {
        place(&mut w, 1, &format!("es_14_{i}"));
        ticks(&mut w, 361);
    }
    assert_eq!(progress(&w, 1, "es_14"), vec![1; 3]);
}
#[test]
fn empty_seat_echo_is_inert_without_quest_single_and_rearms_after_abandonment() {
    let mut w = world();
    let _rx = hero(&mut w, 1);
    place(&mut w, 1, "es_02_m");
    ticks(&mut w, 2);
    let id = w.slimes.iter().position(|s| s.kind == "es_foe_02").unwrap();
    assert!(w.slimes[id].dead);
    accept(&mut w, 1, "es_02");
    ticks(&mut w, 2);
    assert!(!w.slimes[id].dead);
    let hp = w.slimes[id].hp;
    ticks(&mut w, 100);
    assert_eq!(w.slimes[id].hp, hp);
    w.players.get_mut(&1).unwrap().character.zone = 0;
    ticks(&mut w, 241);
    assert!(w.slimes[id].dead);
    place(&mut w, 1, "es_02_m");
    ticks(&mut w, 1);
    assert!(!w.slimes[id].dead);
}
#[test]
fn empty_seat_summon_kill_credits_contributors_and_hires_without_farmable_rewards() {
    let mut w = world();
    let _a = hero(&mut w, 1);
    let _b = hero(&mut w, 2);
    let _c = hero(&mut w, 3);
    accept(&mut w, 1, "es_08");
    place(&mut w, 1, "es_08_m");
    place(&mut w, 2, "es_08_m");
    place(&mut w, 3, "es_08_m");
    let owner = w.players[&1].character.id.clone();
    w.players.get_mut(&2).unwrap().merc = Some(owner);
    ticks(&mut w, 1);
    let id = w.slimes.iter().position(|s| s.kind == "es_foe_08").unwrap();
    let before = serde_json::to_value(&w.players[&1].character).unwrap();
    let drops = w.drops.len();
    w.hit_slime(id, 2, 1., false);
    w.hit_slime(id, 3, 1e12, false);
    assert!(w.slimes[id].dead);
    assert_eq!(progress(&w, 1, "es_08"), vec![1]);
    let after = serde_json::to_value(&w.players[&1].character).unwrap();
    for key in ["xp", "gold", "inventory", "kills"] {
        assert_eq!(before[key], after[key]);
    }
    assert_eq!(w.drops.len(), drops);
    assert!(
        !w.players[&3]
            .character
            .quests
            .iter()
            .any(|q| q.id == "es_08")
    );
}
#[test]
fn empty_seat_rewards_refuse_wrong_class_full_bags_and_duplicate_claims() {
    let mut w = world();
    let _rx = hero(&mut w, 1);
    accept(&mut w, 1, "es_26");
    let q = quest(&w, "es_26");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.quests.iter_mut().find(|p| p.id == q.id).unwrap().counts = vec![1];
    let class = match c.look.class {
        Class::Warrior => "warrior",
        Class::Mage => "mage",
        Class::Assassin => "assassin",
        Class::Priest => "priest",
        Class::Hunter => "hunter",
    };
    let good = &q.reward_choices[class][0];
    let bad = &q.reward_choices[if class == "mage" { "warrior" } else { "mage" }][0];
    assert!(!quest_action_with_choice(c, &q, "claim", Some(bad)).2);
    // Fill every ordinary bag cell with distinct material stacks. Equipped gear remains outside the bag.
    for it in ITEMS
        .iter()
        .filter(|i| i.kind == "material" && !is_quest_item(i))
        .take(c.bag_capacity())
    {
        c.add_item(&it.id, 1);
    }
    assert!(!quest_action_with_choice(c, &q, "claim", Some(good)).2);
    c.inventory.retain(|s| s.item == "starter_gear");
    let before = c.quantity(good);
    assert!(quest_action_with_choice(c, &q, "claim", Some(good)).2);
    assert_eq!(c.quantity(good), before + 1);
    assert!(!quest_action_with_choice(c, &q, "claim", Some(good)).2);
}

#[test]
fn empty_seat_new_wards_and_bells_complete_with_existing_objective_rules() {
    let mut w = world();
    let _rx = hero(&mut w, 1);
    for qid in ["es_06", "es_15", "es_18"] {
        accept(&mut w, 1, qid);
        place(&mut w, 1, &format!("{qid}_m"));
        for _ in 0..20 {
            w.update_holds();
        }
        assert!(
            w.slimes
                .iter()
                .any(|s| !s.dead && s.kind.starts_with("es_foe_"))
        );
        for _ in 0..381 {
            w.update_holds();
        }
        assert_eq!(progress(&w, 1, qid), vec![20]);
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.kind.starts_with("es_foe_"))
                .all(|s| s.dead)
        );
    }
    for qid in ["es_07", "es_21", "es_23"] {
        accept(&mut w, 1, qid);
        for i in 0..3 {
            place(&mut w, 1, &format!("{qid}_{i}"));
            w.update_chimes();
        }
        assert_eq!(progress(&w, 1, qid), vec![3]);
    }
}

#[test]
fn empty_seat_real_raid_kill_in_all_copies_unlocks_the_homecoming() {
    let mut w = world();
    let _rx = hero(&mut w, 1);
    // The encounter itself is already covered by Eldmarr's own checks. Disable its phase shields
    // in this fixture so a real hit can exercise the new campaign's entrance-quest credit path.
    w.boss.table.remove("cf_eldmarr");
    let copies: Vec<_> = w
        .instances
        .iter()
        .filter(|i| i.template == 46)
        .map(|i| i.zone)
        .collect();
    for zone in copies {
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .retain(|p| p.id != "es_27");
        accept(&mut w, 1, "es_27");
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == zone && s.kind == "cf_eldmarr")
            .unwrap();
        let at = w.slimes[id].point();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = zone;
        c.x = at.x;
        c.y = at.y;
        w.hit_slime(id, 1, 1e14, false);
        assert!(w.slimes[id].dead);
        assert_eq!(progress(&w, 1, "es_27"), vec![1]);
    }
    let q = quest(&w, "es_27");
    assert!(quest_action(&mut w.players.get_mut(&1).unwrap().character, &q, "claim").2);
    accept(&mut w, 1, "es_28");
    place(&mut w, 1, "es_28_m");
    ticks(&mut w, 300);
    assert_eq!(
        progress(&w, 1, "es_28"),
        vec![0, 0],
        "Bram must hear the true name before the memorial"
    );
    let npc = w.maps[0].npcs.iter().find(|n| n.id == "smith").unwrap();
    let at = npc.position_at(w.time);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.x = at.x;
    c.y = at.y;
    w.interact(1, "smith", None);
    assert_eq!(progress(&w, 1, "es_28"), vec![1, 0]);
    place(&mut w, 1, "es_28_m");
    ticks(&mut w, 281);
    assert_eq!(progress(&w, 1, "es_28"), vec![1, 1]);
}
