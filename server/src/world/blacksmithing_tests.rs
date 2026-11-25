use super::*;
use crate::profession::Skill;

fn smiths() -> (World, String, Vec<mpsc::Receiver<Value>>) {
    let mut world =
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
    world.smith_rng = 1;
    let mut receivers = vec![];
    let mut token = String::new();
    for (id, name) in [(1, "Bramson"), (2, "Anvilson")] {
        let (tx, rx) = mpsc::channel(256);
        let joined = world
            .join(
                id,
                None,
                Some(Look {
                    name: name.into(),
                    ..Default::default()
                }),
                tx,
            )
            .unwrap();
        if id == 1 {
            token = joined["token"].as_str().unwrap().to_owned();
        }
        receivers.push(rx);
    }
    (world, token, receivers)
}

fn player_at(world: &mut World, session: u64, zone: usize, point: Point) -> &mut Player {
    let p = world.players.get_mut(&session).unwrap();
    p.stop();
    p.character.zone = zone;
    p.character.x = point.x;
    p.character.y = point.y;
    p
}

fn smith_at(world: &mut World) -> Point {
    world.maps[0]
        .npcs
        .iter()
        .find(|n| n.id == TRAINER)
        .unwrap()
        .position_at(world.time)
}

fn train(world: &mut World, session: u64) {
    let at = smith_at(world);
    player_at(world, session, 0, at);
    world.blacksmithing_command(
        session,
        Command::Train {
            npc: TRAINER.into(),
        },
    );
    assert_eq!(world.players[&session].character.quantity(STARTER_PICK), 1);
}

fn start(world: &mut World, session: u64, vein: Vein, zone: usize) {
    // Stand just beside the vein on its validated walkable approach.
    player_at(world, session, zone, vein.point);
    world.message(session, ClientMessage::Mine { id: vein.id });
    assert!(world.players[&session].mining.is_some());
}

fn command(world: &mut World, request: Command) {
    world.message(1, ClientMessage::Blacksmithing { request });
}

#[test]
fn blacksmithing_candidates_pass_authoritative_collision_and_have_a_replacement() {
    let (mut w, _, _) = smiths();
    for (zone, points) in CANDIDATES.iter() {
        let map = &w.maps[*zone];
        assert!(!w.is_instance(*zone) && !map.interior);
        assert!(CATALOG.tier(*zone).is_some());
        for p in points {
            let mut point = *p;
            map.collide(&mut point, PLAYER_RADIUS);
            assert_eq!(*p, point, "collision in {}", map.name);
            assert!(!map.in_city(*p));
            let clear = [(-1.5, 0.), (1.5, 0.), (0., -1.5), (0., 1.5)]
                .into_iter()
                .filter(|(x, y)| {
                    let stand = Point {
                        x: p.x + x,
                        y: p.y + y,
                    };
                    let mut pushed = stand;
                    map.collide(&mut pushed, PLAYER_RADIUS);
                    pushed == stand && map.line_clear(stand, *p, 0.05)
                })
                .count();
            assert!(clear >= 1, "no clear approach in {} to {p:?}", map.name);
        }
        w.ensure_veins(*zone);
        let active = &w.mining_veins[zone];
        assert_eq!(active.len(), 3.min(points.len() - 1));
        assert!(active.iter().all(|vein| (3..=5).contains(&vein.pulls)));
    }
}

#[test]
fn blacksmithing_movement_damage_distance_and_full_bags_do_not_spend_pulls() {
    let (mut w, _, mut replies) = smiths();
    train(&mut w, 1);
    w.ensure_veins(0);
    let vein = w.mining_veins[&0][0];
    start(&mut w, 1, vein, 0);
    w.message(1, ClientMessage::Input { dx: 1., dy: 0. });
    assert!(w.players[&1].mining.is_none());
    start(&mut w, 1, vein, 0);
    w.time += DURATION;
    w.hurt_player(1, 25., vein.point);
    assert!(w.players[&1].mining.is_none());
    w.update_mining(1);
    let far = Point {
        x: vein.point.x + REACH + 1.,
        y: vein.point.y,
    };
    let p = player_at(&mut w, 1, 0, far);
    p.combat_left = 0.;
    p.hurt = 0.;
    w.message(1, ClientMessage::Mine { id: vein.id });
    assert!(w.players[&1].mining.is_none());
    let p = w.players.get_mut(&1).unwrap();
    for resource in ITEMS
        .iter()
        .filter(|i| i.kind == "material" && i.id != CATALOG.tiers[0].ore)
    {
        if p.character.bag_used() >= p.character.bag_capacity() {
            break;
        }
        p.character.add_item(&resource.id, 1);
    }
    start(&mut w, 1, vein, 0);
    w.time += DURATION;
    w.update_mining(1);
    assert_eq!(w.mining_veins[&0][0].pulls, vein.pulls);
    assert_eq!(w.players[&1].character.quantity(&CATALOG.tiers[0].ore), 0);
    // Existing material stacks can still receive ore when every slot is used.
    let ore = &CATALOG.tiers[0].ore;
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let filler = c
        .inventory
        .iter()
        .find(|stack| item(&stack.item).is_some_and(|i| i.kind == "material"))
        .unwrap()
        .item
        .clone();
    assert!(c.consume_item(&filler, 1));
    c.add_item(ore, 1);
    assert_eq!(c.bag_used(), c.bag_capacity());
    start(&mut w, 1, vein, 0);
    w.time += DURATION;
    w.update_mining(1);
    assert!(w.players[&1].character.quantity(ore) > 1);
    assert_eq!(w.mining_veins[&0][0].pulls, vein.pulls - 1);
    let mining: Vec<_> = std::iter::from_fn(|| replies[0].try_recv().ok())
        .filter(|p| p["type"] == "mining" && p["state"] == "error")
        .collect();
    assert!(
        mining
            .iter()
            .any(|p| p["text"] == "Your bags are full. Make room first.")
    );
}

#[test]
fn blacksmithing_untrained_miner_gets_trainer_directions() {
    let (mut w, _, mut replies) = smiths();
    w.ensure_veins(0);
    let vein = w.mining_veins[&0][0];
    player_at(&mut w, 1, 0, vein.point);
    w.message(1, ClientMessage::Mine { id: vein.id });
    assert!(w.players[&1].mining.is_none());
    assert!(std::iter::from_fn(|| replies[0].try_recv().ok()).any(|v| {
        v["type"] == "mining"
            && v["state"] == "error"
            && v["text"] == "Learn Blacksmithing from Bram Emberforge in Alderhaven first."
    }));
}

#[test]
fn blacksmithing_simultaneous_last_pull_relocates_once_and_persists_once() {
    let (mut w, token, mut replies) = smiths();
    train(&mut w, 1);
    train(&mut w, 2);
    w.ensure_veins(0);
    w.mining_veins.get_mut(&0).unwrap()[0].pulls = 1;
    let vein = w.mining_veins[&0][0];
    start(&mut w, 1, vein, 0);
    start(&mut w, 2, vein, 0);
    w.time += DURATION;
    w.update_mining(1);
    w.update_mining(2);
    let ore = &CATALOG.tiers[0].ore;
    let first = w.players[&1].character.quantity(ore);
    assert!((1..=2).contains(&first));
    assert_eq!(w.players[&2].character.quantity(ore), 0);
    assert_eq!(w.mining_veins[&0].len(), 3);
    assert!(
        !w.mining_veins[&0]
            .iter()
            .any(|v| v.id == vein.id || v.point == vein.point)
    );
    assert!(
        !w.snapshot_for(0)["miningVeins"][0]
            .as_object()
            .unwrap()
            .contains_key("pulls")
    );
    let loaded = w.store.load(&token).unwrap().unwrap();
    assert_eq!(loaded.quantity(ore), first);
    assert_eq!(
        loaded.blacksmithing.proficiency,
        w.players[&1].character.blacksmithing.proficiency
    );
    assert!(
        std::iter::from_fn(|| replies[1].try_recv().ok())
            .any(|p| p["text"] == "That vein has moved.")
    );
}

#[test]
fn blacksmithing_mining_trains_every_band_with_its_pick_and_never_an_earlier_band() {
    let (mut w, _, _) = smiths();
    train(&mut w, 1);
    let route = [0, 1, 2, 3, 6, 7, 8, 13, 14, 15];
    for (band, zone) in route.into_iter().enumerate() {
        let tier = CATALOG.tier(zone).unwrap();
        let entry = &CATALOG.tiers[tier];
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.inventory.clear();
        c.blacksmithing.proficiency = Skill::default();
        c.blacksmithing
            .proficiency
            .initialize(training_cap(band) - 1);
        let pick = CATALOG.picks.iter().find(|p| p.reaches >= tier).unwrap();
        w.ensure_veins(zone);
        let vein = w.mining_veins[&zone][0];
        player_at(&mut w, 1, zone, vein.point);
        assert!(w.mine_target(&w.players[&1], vein.id).is_err());
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item(&pick.item, 1);
        w.smith_rng = 0;
        start(&mut w, 1, vein, zone);
        w.time += DURATION;
        w.update_mining(1);
        let skill = w.players[&1].character.blacksmithing.proficiency.skill;
        assert_eq!(skill, training_cap(band), "band {band}");
        let qty = w.players[&1].character.quantity(&entry.ore);
        start(&mut w, 1, vein, zone);
        w.time += DURATION;
        w.update_mining(1);
        assert_eq!(
            w.players[&1].character.blacksmithing.proficiency.skill,
            skill
        );
        assert!(w.players[&1].character.quantity(&entry.ore) > qty);
    }
    assert_eq!(
        w.players[&1].character.blacksmithing.proficiency.skill,
        300
    );
}

#[test]
fn blacksmithing_expert_mining_advances_a_saved_skill_through_all_ten_regions() {
    let (mut w, token, mut replies) = smiths();
    train(&mut w, 1);
    let legacy = &CATALOG.picks[4].item;
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.blacksmithing.proficiency.skill = 300;
    c.add_item(legacy, 1);
    c.add_item(&CATALOG.picks.last().unwrap().item, 1);
    w.save();
    assert_eq!(
        w.store
            .load(&token)
            .unwrap()
            .unwrap()
            .blacksmithing
            .proficiency
            .skill,
        300
    );

    let first = CATALOG.training_zones[10][0];
    let wrong = CATALOG.training_zones[11][0];
    let pick = CATALOG.expert_pick(330).unwrap();
    assert_eq!(training_view(300).unwrap()["pick"], pick.item);
    w.ensure_veins(first);
    let vein = w.mining_veins[&first][0];
    w.smith_rng = 0;
    start(&mut w, 1, vein, first);
    w.time += DURATION;
    w.update_mining(1);
    let done = std::iter::from_fn(|| replies[0].try_recv().ok())
        .find(|packet| packet["type"] == "mining" && packet["state"] == "done")
        .unwrap();
    assert_eq!(done["skill"], 300, "the old pick cannot gain expert skill");
    assert_eq!(done["quantity"], 1, "the old pick can still gather ore");
    assert_eq!(done["requiredPick"], pick.item);
    w.players.get_mut(&1).unwrap().character.add_item(&pick.item, 1);
    for (zone, skill) in [(wrong, 300), (first, 301)] {
        w.ensure_veins(zone);
        let vein = w.mining_veins[&zone][0];
        w.smith_rng = 0;
        start(&mut w, 1, vein, zone);
        w.time += DURATION;
        w.update_mining(1);
        assert_eq!(
            w.players[&1].character.blacksmithing.proficiency.skill, skill,
            "zone {zone}"
        );
    }
    for (index, zones) in CATALOG.training_zones.iter().enumerate().skip(10) {
        let cap = training_cap(index);
        let zone = zones[0];
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.blacksmithing.proficiency.skill = cap - 1;
        let pick = CATALOG.expert_pick(cap).unwrap();
        if c.quantity(&pick.item) == 0 {
            c.add_item(&pick.item, 1);
        }
        w.ensure_veins(zone);
        w.smith_rng = 0;
        for _ in 0..2 {
            let vein = w.mining_veins[&zone][0];
            start(&mut w, 1, vein, zone);
            w.time += DURATION;
            w.update_mining(1);
            assert_eq!(
                w.players[&1].character.blacksmithing.proficiency.skill, cap,
                "zone {zone}"
            );
        }
    }
    assert_eq!(
        w.store
            .load(&token)
            .unwrap()
            .unwrap()
            .blacksmithing
            .proficiency
            .skill,
        600
    );
    assert!(
        training_view(600).is_none(),
        "a capped character has no next training band"
    );
}

#[test]
fn blacksmithing_expert_pick_chain_crafts_and_masterwork_yields_extra_ore() {
    let (mut w, token, mut replies) = smiths();
    train(&mut w, 1);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.add_item(&CATALOG.picks[4].item, 1);
    c.gold = 300_000;
    for (previous, pick) in CATALOG.picks[4..].iter().zip(&CATALOG.picks[5..]) {
        let recipe = CATALOG.recipe(&pick.item).unwrap();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        for (item, quantity) in &recipe.ingredients[1..] {
            c.add_item(item, *quantity);
        }
        let cost_before = c.gold;
        c.blacksmithing.proficiency.skill = recipe.skill - 1;
        let craft = || Command::Craft { npc: TRAINER.into(), recipe: pick.item.clone(), all: true };
        command(&mut w, craft());
        let c = &mut w.players.get_mut(&1).unwrap().character;
        assert_eq!(c.quantity(&pick.item), 0);
        assert_eq!(c.quantity(&previous.item), 1);
        assert_eq!(c.gold, cost_before);
        c.blacksmithing.proficiency.skill = recipe.skill;
        command(&mut w, craft());
        let c = w.store.load(&token).unwrap().unwrap();
        assert_eq!(c.quantity(&pick.item), 1);
        assert_eq!(c.quantity(&previous.item), 0);
        assert_eq!(c.gold, cost_before - recipe.cost);
        assert_eq!(c.blacksmithing.proficiency.skill, recipe.skill);
    }

    let zone = CATALOG.training_zones.last().unwrap()[0];
    w.ensure_veins(zone);
    let vein = w.mining_veins[&zone][0];
    w.smith_rng = 0;
    start(&mut w, 1, vein, zone);
    w.time += DURATION;
    w.update_mining(1);
    let done = std::iter::from_fn(|| replies[0].try_recv().ok())
        .find(|packet| packet["type"] == "mining" && packet["state"] == "done")
        .unwrap();
    assert_eq!(done["quantity"], 2, "masterwork adds one ore to the roll");
    assert_eq!(done["skill"], 600);
}

#[test]
fn blacksmithing_expert_forge_all_advances_matching_bands_and_caps_at_600() {
    let (mut w, token, mut replies) = smiths();
    train(&mut w, 1);
    for (tier, skill, count, expected) in [(7, 329, 2, 331), (9, 331, 1, 331), (9, 599, 2, 600)] {
        let recipe = CATALOG
            .recipes
            .iter()
            .find(|r| r.tier == tier && r.method == Method::Staple)
            .unwrap();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.blacksmithing.proficiency.skill = skill;
        c.blacksmithing.recipes.insert(recipe.item.clone());
        for (item, quantity) in &recipe.ingredients {
            c.add_item(item, quantity * count);
        }
        let prior = c.quantity(&recipe.item);
        w.smith_rng = 0;
        command(
            &mut w,
            Command::Craft {
                npc: TRAINER.into(),
                recipe: recipe.item.clone(),
                all: true,
            },
        );
        let c = &w.players[&1].character;
        assert_eq!(c.quantity(&recipe.item), prior + count);
        assert_eq!(c.blacksmithing.proficiency.skill, expected);
    }
    let reply = std::iter::from_fn(|| replies[0].try_recv().ok())
        .filter(|packet| packet["type"] == "blacksmithing")
        .last()
        .unwrap();
    assert_eq!(reply["maxSkill"], 600);
    assert!(reply["training"].is_null());
    assert_eq!(
        w.store
            .load(&token)
            .unwrap()
            .unwrap()
            .blacksmithing
            .proficiency
            .skill,
        600
    );
}

#[test]
fn blacksmithing_workshop_validates_station_and_preserves_transactions_and_gear_copies() {
    let (mut w, token, mut replies) = smiths();
    let smith = smith_at(&mut w);
    player_at(
        &mut w,
        1,
        0,
        Point {
            x: smith.x - 10.,
            y: smith.y,
        },
    );
    command(
        &mut w,
        Command::Train {
            npc: TRAINER.into(),
        },
    );
    assert!(w.players[&1].character.blacksmithing.is_untrained());
    train(&mut w, 1);
    let recipe = CATALOG
        .recipes
        .iter()
        .find(|r| r.method == Method::Staple)
        .unwrap();
    let item = &recipe.item;
    let smelt = CATALOG
        .recipes
        .iter()
        .find(|r| r.method == Method::Smelt)
        .unwrap();
    let learn = || Command::Learn {
        npc: TRAINER.into(),
        recipe: item.clone(),
    };
    let craft = |recipe: &str| Command::Craft {
        all: false,
        npc: TRAINER.into(),
        recipe: recipe.into(),
    };
    command(&mut w, learn());
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.add_item(&smelt.ingredients[0].0, 2);
    command(&mut w, craft(&smelt.item));
    assert_eq!(w.players[&1].character.blacksmithing.proficiency.skill, 1);
    command(&mut w, craft(item));
    assert_eq!(
        w.players[&1].character.quantity(&smelt.item),
        1,
        "failure keeps the bar"
    );
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let (first, count) = &recipe.ingredients[0];
    let (second, _) = &recipe.ingredients[1];
    c.add_item(first, *count);
    command(&mut w, craft(item));
    assert_eq!(
        w.players[&1].character.quantity(first),
        count + 1,
        "partial consumption rolled back"
    );
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.add_item(second, 2);
    c.level = 4;
    command(&mut w, craft(item));
    let mut loaded = w.store.load(&token).unwrap().unwrap();
    assert!(loaded.blacksmithing.recipes.contains(item));
    assert_eq!(loaded.quantity(item), 1);
    assert_eq!(
        loaded
            .gear_instances
            .iter()
            .filter(|g| &g.item == item)
            .count(),
        1
    );
    loaded
        .equip_slots(&BTreeMap::from([("gloves".into(), item.clone())]))
        .unwrap();
    assert_eq!(loaded.equipment["gloves"], *item);
    assert!(
        std::iter::from_fn(|| replies[0].try_recv().ok())
            .any(|packet| packet["output"] == item.as_str())
    );
}

#[test]
fn blacksmithing_failed_save_preserves_ore_gold_ingredients_and_vein_charges() {
    let (mut w, _, mut replies) = smiths();
    train(&mut w, 1);
    let recipe = CATALOG
        .recipes
        .iter()
        .find(|r| r.method == Method::Smelt)
        .unwrap();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    for (ingredient, quantity) in &recipe.ingredients {
        c.add_item(ingredient, *quantity);
    }
    c.gold = 999;
    let before = c.inventory.clone();
    w.store.conn().execute_batch(
        "CREATE TRIGGER refuse_smith_save BEFORE UPDATE ON characters BEGIN SELECT RAISE(FAIL, 'test'); END;"
    ).unwrap();
    command(
        &mut w,
        Command::Craft {
            all: false,
            npc: TRAINER.into(),
            recipe: recipe.item.clone(),
        },
    );
    assert_eq!(w.players[&1].character.inventory, before);
    assert_eq!(w.players[&1].character.gold, 999);
    w.ensure_veins(0);
    let vein = w.mining_veins[&0][0];
    start(&mut w, 1, vein, 0);
    w.time += DURATION;
    w.update_mining(1);
    assert_eq!(w.mining_veins[&0][0].pulls, vein.pulls);
    assert_eq!(w.players[&1].character.inventory, before);
    assert_eq!(w.players[&1].character.blacksmithing.proficiency.skill, 1);
    let failures: Vec<_> = std::iter::from_fn(|| replies[0].try_recv().ok())
        .filter(|packet| packet["text"] == "The Blacksmithing change could not be saved.")
        .collect();
    assert_eq!(failures.len(), 2);
}

#[test]
fn blacksmithing_pick_upgrades_require_the_previous_pick_fees_and_the_right_band() {
    let (mut w, _, _) = smiths();
    train(&mut w, 1);
    for recipe in CATALOG
        .recipes
        .iter()
        .filter(|r| r.method == Method::Upgrade)
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        let previous = &recipe.ingredients[0].0;
        assert_eq!(c.quantity(previous), 1);
        for (id, count) in &recipe.ingredients[1..] {
            c.add_item(id, *count);
        }
        c.blacksmithing.proficiency.skill = recipe.skill - 1;
        c.gold = recipe.cost;
        let craft = || Command::Craft {
            all: false,
            npc: TRAINER.into(),
            recipe: recipe.item.clone(),
        };
        command(&mut w, craft());
        let c = &mut w.players.get_mut(&1).unwrap().character;
        assert_eq!(c.quantity(previous), 1);
        assert_eq!(c.gold, recipe.cost);
        c.blacksmithing.proficiency.skill = recipe.skill;
        command(&mut w, craft());
        let c = &w.players[&1].character;
        assert_eq!(c.quantity(previous), 0);
        assert_eq!(c.quantity(&recipe.item), 1);
        assert_eq!(c.gold, 0);
        assert_eq!(c.blacksmithing.proficiency.skill, recipe.skill);
    }
}

#[test]
fn blacksmithing_rare_ingredients_come_from_the_primary_training_zones() {
    let (w, _, _) = smiths();
    for recipe in CATALOG.recipes.iter().filter(|r| r.method == Method::Rare) {
        let z = recipe.drop_zone.unwrap_or(CATALOG.tiers[recipe.tier].zones[0]);
        let material_id = &recipe.ingredients.last().unwrap().0;
        assert!(
            w.slimes
                .iter()
                .any(|s| s.zone == z && material(&s.kind) == material_id),
            "missing ingredient source for {}",
            recipe.item
        );
    }
}

#[test]
fn blacksmithing_expert_plans_reach_their_intended_loot_pools_and_craft_at_600() {
    let (mut w, token, _) = smiths();
    train(&mut w, 1);
    for recipe in CATALOG.recipes.iter().filter(|r| r.drop_zone.is_some()) {
        let zone = recipe.drop_zone.unwrap();
        let map = &w.maps[zone];
        let level = map.levels.unwrap()[0];
        let plan = recipe.plan.as_deref();
        assert_eq!(CATALOG.drop_plan(zone, map, "green", level, (0., 0.75)), plan);
        assert_ne!(CATALOG.drop_plan(zone, map, "green", level, (0., 0.)), plan);
        assert_eq!(CATALOG.drop_plan(zone, map, "green", level, (0.015, 0.75)), None);
    }

    let boss = &w.maps[44];
    let master = CATALOG
        .recipes
        .iter()
        .find(|r| r.method == Method::Epic && r.skill == 600)
        .unwrap();
    assert_eq!(
        CATALOG.drop_plan(44, boss, &boss.final_boss, 99, (0., 0.65)),
        master.plan.as_deref()
    );
    let plan = master.plan.as_ref().unwrap();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.blacksmithing.proficiency.skill = 599;
    c.add_item(plan, 1);
    for (ingredient, quantity) in &master.ingredients {
        c.add_item(ingredient, *quantity);
    }
    command(&mut w, Command::Study { plan: plan.clone() });
    let craft = || Command::Craft { npc: TRAINER.into(), recipe: master.item.clone(), all: false };
    command(&mut w, craft());
    let c = &mut w.players.get_mut(&1).unwrap().character;
    assert!(c.blacksmithing.recipes.contains(&master.item));
    assert_eq!(c.quantity(&master.item), 0);
    c.blacksmithing.proficiency.skill = 600;
    command(&mut w, craft());
    let saved = w.store.load(&token).unwrap().unwrap();
    assert_eq!(saved.quantity(&master.item), 1);
    assert!(saved.gear_instances.iter().any(|copy| copy.item == master.item && copy.rarity == "epic"));
}

#[test]
fn blacksmithing_blueprints_follow_actual_loot_and_study_before_epic_unlock() {
    let (mut w, token, _) = smiths();
    train(&mut w, 1);
    let rare = CATALOG
        .recipes
        .iter()
        .find(|r| r.method == Method::Rare)
        .unwrap();
    let plan = rare.plan.as_ref().unwrap();
    let green = w
        .slimes
        .iter()
        .position(|s| s.zone == 0 && s.kind == "green")
        .unwrap();
    let point = w.slimes[green].point();
    player_at(&mut w, 1, 0, point);
    w.smith_rng = 0; // The first roll is zero, so the normal kill awards a plan.
    w.hit_slime(green, 1, 1e6, false);
    assert!(
        w.drops
            .iter()
            .any(|d| d.item.as_deref() == Some(plan.as_str()))
    );
    assert!(
        CATALOG
            .drop_plan(0, &w.maps[0], "ember_firelord", 99, (0., 0.))
            .is_none()
    );
    assert!(
        CATALOG
            .drop_plan(4, &w.maps[4], "green", 1, (0., 0.))
            .is_none()
    );
    let epic = CATALOG
        .recipes
        .iter()
        .find(|r| r.method == Method::Epic)
        .unwrap();
    let boss = &w.maps[44];
    assert_eq!(
        CATALOG.drop_plan(44, boss, &boss.final_boss, 99, (0., 0.)),
        epic.plan.as_deref()
    );
    assert!(
        CATALOG
            .drop_plan(44, boss, "null_gear", 99, (0., 0.))
            .is_none()
    );
    let plan = epic.plan.clone().unwrap();
    let smith = smith_at(&mut w);
    let p = player_at(&mut w, 1, 0, smith);
    p.combat_left = 0.;
    p.character.add_item(&plan, 2);
    command(&mut w, Command::Study { plan: plan.clone() });
    command(&mut w, Command::Study { plan: plan.clone() });
    let loaded = w.store.load(&token).unwrap().unwrap();
    assert!(loaded.blacksmithing.recipes.contains(&epic.item));
    assert_eq!(loaded.quantity(&plan), 1);
    command(
        &mut w,
        Command::Craft {
            all: false,
            npc: TRAINER.into(),
            recipe: epic.item.clone(),
        },
    );
    assert_eq!(w.players[&1].character.quantity(&epic.item), 0);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.blacksmithing.proficiency.skill = 300;
    for (ingredient, qty) in &epic.ingredients {
        c.add_item(ingredient, *qty);
    }
    command(
        &mut w,
        Command::Craft {
            all: false,
            npc: TRAINER.into(),
            recipe: epic.item.clone(),
        },
    );
    assert_eq!(w.players[&1].character.quantity(&epic.item), 1);
    assert!(
        w.players[&1]
            .character
            .gear_instances
            .iter()
            .any(|copy| copy.item == epic.item && copy.rarity == "epic")
    );
}

#[test]
fn blacksmithing_bulk_smelting_and_forging_fit_bags_and_save_every_copy() {
    let (mut w, token, _) = smiths();
    train(&mut w, 1);
    let bar = CATALOG.recipes.iter().find(|r| r.method == Method::Smelt).unwrap();
    let gear = CATALOG.recipes.iter().find(|r| r.method == Method::Staple).unwrap();
    let craft = |recipe: &str| serde_json::from_value(json!({
        "op":"craft","npc":TRAINER,"recipe":recipe,"all":true,
    })).unwrap();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let (ore, amount) = &bar.ingredients[0];
    c.add_item(ore, amount * 7 + 1);
    command(&mut w, craft(&bar.item));
    let c = &mut w.players.get_mut(&1).unwrap().character;
    assert_eq!(c.quantity(&bar.item), 7);
    assert_eq!(c.quantity(ore), 1);
    assert_eq!(c.blacksmithing.proficiency.skill, 1, "smelting gives no skill");

    c.blacksmithing.recipes.insert(gear.item.clone());
    for (id, quantity) in &gear.ingredients {
        c.add_item(id, quantity * 4);
    }
    for filler in ITEMS.iter().filter(|i| i.kind == "material") {
        if c.bag_used() + 2 >= c.bag_capacity() {
            break;
        }
        c.add_item(&filler.id, 1);
    }
    let before = c.clone();
    assert_eq!(before.bag_used() + 2, before.bag_capacity());
    command(&mut w, craft(&gear.item));
    let saved = w.store.load(&token).unwrap().unwrap();
    assert_eq!(saved.quantity(&gear.item), 2);
    assert_eq!(saved.gear_instances.iter().filter(|g| g.item == gear.item).count(), 2);
    assert_eq!(saved.bag_used(), saved.bag_capacity());
    for (id, quantity) in &gear.ingredients {
        assert_eq!(saved.quantity(id), before.quantity(id) - quantity * 2);
    }
}
