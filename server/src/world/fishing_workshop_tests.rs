use super::*;

fn visit(w: &mut World, zone: usize, npc_id: &str, offer: Option<&str>) {
    let n = w.maps[zone]
        .npcs
        .iter()
        .find(|n| n.id == npc_id)
        .unwrap()
        .clone();
    let p = w.players.get_mut(&1).unwrap();
    p.character.zone = zone;
    p.character.x = n.x;
    p.character.y = n.y;
    w.time += 1.;
    w.interact(1, npc_id, offer);
}
fn funded(w: &mut World, previous: &str, fish: &str, material: &str) {
    let p = w.players.get_mut(&1).unwrap();
    p.character.inventory.clear();
    p.character.level = 99;
    p.character.gold = 100_000;
    p.character.add_item(previous, 1);
    p.character.add_item(fish, 5);
    p.character.add_item(material, 1);
}
fn inventory(w: &World) -> Value {
    serde_json::to_value(&w.players[&1].character).unwrap()
}

#[test]
fn fishing_workshop_buys_twig_and_consumes_complete_rod_recipe_once() {
    let (mut w, mut rx) = fishing_tests::angler();
    w.players.get_mut(&1).unwrap().character.inventory.clear();
    w.players.get_mut(&1).unwrap().character.gold = 500;
    visit(&mut w, 0, "fisher_meadow_0", Some("buy_twig_rod"));
    assert_eq!(w.players[&1].character.gold, 450);
    assert_eq!(w.players[&1].character.quantity("rod_twig_rod"), 1);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.consume_item("rod_twig_rod", 1);
    c.add_item("rod_emberline_rod", 1);
    c.level = 10;
    c.add_item("fish_pier_sprat", 5);
    c.add_item("slime_gel", 1);
    visit(&mut w, 0, "fisher_meadow_0", Some("rod:2"));
    let c = &w.players[&1].character;
    assert_eq!(c.quantity("rod_willow_rod"), 1);
    assert_eq!(c.gold, 200);
    for id in ["rod_emberline_rod", "fish_pier_sprat", "slime_gel"] {
        assert_eq!(c.quantity(id), 0);
    }
    let after = inventory(&w);
    visit(&mut w, 0, "fisher_meadow_0", Some("rod:2"));
    assert_eq!(
        inventory(&w),
        after,
        "repeated action never charges twice without inputs"
    );
    let packets: Vec<_> = std::iter::from_fn(|| rx.try_recv().ok()).collect();
    assert!(packets.iter().any(|p| {
        p["fisherQuote"]
            .as_array()
            .is_some_and(|a| a.iter().any(|r| r["id"] == "rod:2"))
    }));
}

#[test]
fn fishing_workshop_failures_preserve_every_item_and_gold() {
    for failure in [
        "gold", "fish", "material", "rod", "level", "combat", "mount", "stun", "trade", "npc",
        "zone", "distance", "full",
    ] {
        let (mut w, _rx) = fishing_tests::angler();
        funded(&mut w, "rod_emberline_rod", "fish_pier_sprat", "slime_gel");
        let n = w.maps[0]
            .npcs
            .iter()
            .find(|n| n.id == "fisher_meadow_0")
            .unwrap()
            .clone();
        let p = w.players.get_mut(&1).unwrap();
        p.character.x = n.x;
        p.character.y = n.y;
        match failure {
            "gold" => p.character.gold = 249,
            "fish" => {
                p.character.consume_item("fish_pier_sprat", 1);
            }
            "material" => {
                p.character.consume_item("slime_gel", 1);
            }
            "rod" => {
                p.character.consume_item("rod_emberline_rod", 1);
            }
            "level" => p.character.level = 1,
            "combat" => p.combat_left = 5.,
            "mount" => p.character.mounted = true,
            "stun" => p.stun = 5.,
            "distance" => p.character.x += 10.,
            "full" => {
                // Each consumed stack remains, so the output would require an additional cell.
                p.character.add_item("rod_emberline_rod", 1);
                p.character.add_item("fish_pier_sprat", 1);
                p.character.add_item("slime_gel", 1);
                for i in ITEMS.iter().filter(|i| i.kind == "material") {
                    if p.character.bag_used() >= p.character.bag_capacity() {
                        break;
                    }
                    p.character.add_item(&i.id, 1);
                }
            }
            _ => {}
        }
        let before = inventory(&w);
        w.time += 1.;
        if failure == "trade" {
            let npc = w.maps[0]
                .npcs
                .iter()
                .find(|n| n.id == "fisher_meadow_0")
                .unwrap()
                .clone();
            assert!(
                fishing_workshop::purchase(w.players.get_mut(&1).unwrap(), &npc, "rod:2", true)
                    .is_err()
            );
        } else {
            w.interact(
                1,
                if failure == "npc" {
                    "smith"
                } else {
                    "fisher_meadow_0"
                },
                Some(if failure == "zone" {
                    "rod:magma"
                } else {
                    "rod:2"
                }),
            );
        }
        assert_eq!(inventory(&w), before, "failed {failure} changed character");
    }
}

#[test]
fn fishing_workshop_charm_is_consumed_only_with_a_successful_craft() {
    let (mut w, _) = fishing_tests::angler();
    funded(&mut w, "rod_emberline_rod", "fish_pier_sprat", "slime_gel");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.consume_item("fish_pier_sprat", 1);
    c.add_item("fishing_rod_charm", 1);
    visit(&mut w, 0, "fisher_meadow_0", Some("rod:2"));
    let c = &w.players[&1].character;
    assert_eq!(c.quantity("rod_willow_rod"), 1);
    assert_eq!(c.quantity("fishing_rod_charm"), 0);
    assert_eq!(c.quantity("fish_pier_sprat"), 0);
}

#[test]
fn fishing_workshop_all_rod_recipes_are_fulfilled_and_cooking_uses_shared_timer() {
    let recipes: Value =
        serde_json::from_str(include_str!("../../../world/fishing-workshop.txt")).unwrap();
    for r in recipes
        .as_array()
        .unwrap()
        .iter()
        .filter(|r| r["id"].as_str().unwrap().starts_with("rod:"))
    {
        let (mut w, _) = fishing_tests::angler();
        let zone = r["zones"][0].as_u64().unwrap() as usize;
        let npc = w.maps[zone]
            .npcs
            .iter()
            .find(|n| n.id.starts_with("fisher_"))
            .unwrap()
            .id
            .clone();
        let p = w.players.get_mut(&1).unwrap();
        p.character.inventory.clear();
        p.character.level = 99;
        p.character.gold = 100_000;
        for cost in r["ingredients"].as_array().unwrap() {
            p.character
                .add_item(cost[0].as_str().unwrap(), cost[1].as_u64().unwrap() as u32);
        }
        visit(&mut w, zone, &npc, Some(r["id"].as_str().unwrap()));
        assert_eq!(
            w.players[&1]
                .character
                .quantity(r["item"].as_str().unwrap()),
            1,
            "{r}"
        );
        assert_eq!(
            w.players[&1].character.gold,
            100_000 - r["cost"].as_u64().unwrap() as u32
        );
    }
    let (mut w, _) = fishing_tests::angler();
    let p = w.players.get_mut(&1).unwrap();
    p.character.gold = 100;
    p.character.add_item("fish_pier_sprat", 2);
    visit(&mut w, 0, "fisher_meadow_0", Some("cook:fish_pier_sprat"));
    let p = w.players.get_mut(&1).unwrap();
    p.character.hp = 1.;
    w.use_item(1, "dish_shore_grill");
    assert_eq!(w.players[&1].meal_cd, 30.);
    let c = &w.players[&1].character;
    assert_eq!(c.quantity("dish_shore_grill"), 0);
    assert_eq!(c.quantity("fish_pier_sprat"), 1);
    w.use_item(1, "fish_pier_sprat");
    assert_eq!(
        w.players[&1].character.quantity("fish_pier_sprat"),
        1,
        "raw and cooked meals share cooldown"
    );
}

#[test]
fn fishing_workshop_every_fisher_is_reachable_and_quests_consume_real_fish() {
    let (mut w, _) = fishing_tests::angler();
    let jobs: Vec<_> = w
        .maps
        .iter()
        .take(47)
        .enumerate()
        .flat_map(|(zone, m)| {
            m.npcs
                .iter()
                .filter(|n| n.id.starts_with("fisher_"))
                .map(move |n| (zone, n.clone()))
        })
        .collect();
    assert_eq!(jobs.len(), 23);
    for (zone, n) in jobs {
        let at = Point { x: n.x, y: n.y };
        let mut collision = at;
        w.maps[zone].collide(&mut collision, 0.4);
        assert!(collision.distance(at) < 0.001, "{} collision", n.id);
        let quests: Vec<_> = w.maps[zone]
            .quests
            .iter()
            .filter(|q| q.npc == n.id)
            .cloned()
            .collect();
        assert_eq!(quests.len(), 4);
        assert_eq!(quests.iter().filter(|q| q.repeatable).count(), 1);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.quests.clear();
        c.level = 99;
        c.gold = 1000;
        for q in quests {
            for _ in 0..if q.repeatable { 2 } else { 1 } {
                visit(&mut w, zone, &n.id, Some(&format!("quest:accept:{}", q.id)));
                let o = &q.objectives[0];
                let c = &mut w.players.get_mut(&1).unwrap().character;
                assert_eq!(item(&o.target).unwrap().kind, "fish");
                c.add_item(&o.target, o.count);
                let before = c.quantity(&o.target);
                visit(&mut w, zone, &n.id, Some(&format!("quest:claim:{}", q.id)));
                let c = &w.players[&1].character;
                assert_eq!(
                    c.quantity(&o.target),
                    before - o.count,
                    "{} real hand-in",
                    q.id
                );
                assert!(c.quests.iter().any(|p| p.id == q.id && p.claimed));
            }
        }
    }
}

#[test]
fn fishing_workshop_full_bags_can_use_the_cells_freed_by_ingredients() {
    let (mut w, _) = fishing_tests::angler();
    funded(&mut w, "rod_emberline_rod", "fish_pier_sprat", "slime_gel");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    for i in ITEMS
        .iter()
        .filter(|i| i.kind == "material" && i.id != "slime_gel")
    {
        if c.bag_used() >= c.bag_capacity() {
            break;
        }
        c.add_item(&i.id, 1);
    }
    let full = c.bag_used();
    assert_eq!(full, c.bag_capacity());
    visit(&mut w, 0, "fisher_meadow_0", Some("rod:2"));
    let c = &w.players[&1].character;
    assert_eq!(c.quantity("rod_willow_rod"), 1);
    assert_eq!(c.bag_used(), full - 2);
}
