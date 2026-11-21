use super::*;

const MEADOW: &str = "alchemy_meadowgold";
const POTION: &str = "alchemy_meadowgold_potion";
const FLASK: &str = "alchemy_cinderheart_flask";
const HEALTH: &str = "alchemy_tideglass_flask";
const VIAL: &str = "alchemy_empty_vial";

fn fixture() -> (World, String) {
    let mut w = World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
    w.alchemy_rng = 0;
    let mut token = String::new();
    for (id, name) in [(1, "Herbcraft"), (2, "Greencraft")] {
        let (tx, rx) = mpsc::channel(256);
        let joined = w
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
        // These tests assert authoritative state directly.
        drop(rx);
        if id == 1 {
            token = joined["token"].as_str().unwrap().into();
        }
    }
    (w, token)
}

fn at(w: &mut World, session: u64, zone: usize, point: Point) -> &mut Player {
    let p = w.players.get_mut(&session).unwrap();
    p.stop();
    p.character.zone = zone;
    p.character.x = point.x;
    p.character.y = point.y;
    p
}

fn trainer(w: &World) -> Point {
    w.maps[0]
        .npcs
        .iter()
        .find(|n| n.id == TRAINER)
        .unwrap()
        .position_at(w.time)
}

fn train(w: &mut World, session: u64) {
    at(w, session, 0, trainer(w));
    w.alchemy_command(
        session,
        Command::Train {
            npc: TRAINER.into(),
        },
    );
    assert_eq!(w.players[&session].character.alchemy.proficiency.skill, 1);
}

fn pick(w: &mut World, session: u64, patch: FlowerPatch) {
    at(w, session, 0, patch.point);
    w.message(session, ClientMessage::PickFlower { id: patch.id });
    assert!(w.players[&session].picking.is_some());
}

#[test]
fn alchemy_environment_pools_have_walkable_replacements_and_workshops() {
    let (mut w, _) = fixture();
    assert_eq!(PATCHES.len(), 25);
    for (&zone, pools) in PATCHES.iter() {
        let area = &w.maps[zone];
        assert!(!w.is_instance(zone) && !w.is_arena_zone(zone) && !area.interior);
        for pool in pools {
            assert!(pool.points.len() > pool.active);
            for &point in &pool.points {
                let mut actual = point;
                area.collide(&mut actual, PLAYER_RADIUS);
                assert_eq!(actual, point, "collision in {}", area.name);
                assert!(
                    [(-1., 0.), (1., 0.), (0., -1.), (0., 1.)]
                        .iter()
                        .any(|(x, y)| {
                            let from = Point {
                                x: point.x + x,
                                y: point.y + y,
                            };
                            let mut actual = from;
                            area.collide(&mut actual, PLAYER_RADIUS);
                            from == actual && area.line_clear(from, point, 0.05)
                        }),
                    "no real approach to {point:?} in {}",
                    area.name
                );
            }
        }
        for npc in area
            .npcs
            .iter()
            .filter(|npc| npc.offers.iter().any(|o| o.id == WORKSHOP))
        {
            let expected = npc.position_at(0.);
            let mut actual = expected;
            area.collide(&mut actual, PLAYER_RADIUS);
            assert_eq!(actual, expected, "{} workshop is blocked", area.name);
        }
        w.ensure_flowers(zone);
        let patches = &w.flower_patches[&zone];
        assert_eq!(
            patches.len(),
            pools.iter().map(|pool| pool.active).sum::<usize>()
        );
        assert!(patches.iter().all(|patch| (3..=5).contains(&patch.picks)));
    }
    for zone in [5, 10, 40, 44] {
        w.ensure_flowers(zone);
        assert!(!w.flower_patches.contains_key(&zone));
    }
}

#[test]
fn alchemy_last_pick_is_saved_once_and_relocates_for_both_players() {
    let (mut w, token) = fixture();
    train(&mut w, 1);
    train(&mut w, 2);
    w.ensure_flowers(0);
    w.flower_patches.get_mut(&0).unwrap()[0].picks = 1;
    let patch = w.flower_patches[&0][0];
    pick(&mut w, 1, patch);
    pick(&mut w, 2, patch);
    w.time += PICK_TIME;
    w.update_picking(1);
    w.update_picking(2);
    let one = &w.players[&1].character;
    assert!((1..=2).contains(&one.quantity(MEADOW)));
    assert_eq!(w.players[&2].character.quantity(MEADOW), 0);
    let saved = w.store.load(&token).unwrap().unwrap();
    assert_eq!(saved.quantity(MEADOW), one.quantity(MEADOW));
    assert_eq!(saved.alchemy.proficiency, one.alchemy.proficiency);
    let live = &w.flower_patches[&0];
    assert_eq!(live.len(), 4);
    assert!(
        !live
            .iter()
            .any(|p| p.id == patch.id || p.point == patch.point)
    );
    let view = w.snapshot_for(0);
    assert_eq!(view["flowerPatches"].as_array().unwrap().len(), 4);
    assert!(view["flowerPatches"][0].get("picks").is_none());
}

#[test]
fn alchemy_movement_damage_reach_and_bags_preserve_pick_charges() {
    let (mut w, _) = fixture();
    train(&mut w, 1);
    w.ensure_flowers(0);
    let patch = w.flower_patches[&0][0];
    pick(&mut w, 1, patch);
    w.message(1, ClientMessage::Input { dx: 1., dy: 0. });
    assert!(w.players[&1].picking.is_none());
    pick(&mut w, 1, patch);
    w.hurt_player(1, 30., patch.point);
    assert!(w.players[&1].picking.is_none());
    let far = Point {
        x: patch.point.x + REACH + 1.,
        y: patch.point.y,
    };
    at(&mut w, 1, 0, far);
    w.message(1, ClientMessage::PickFlower { id: patch.id });
    assert!(w.players[&1].picking.is_none());
    let c = &mut w.players.get_mut(&1).unwrap().character;
    for i in ITEMS
        .iter()
        .filter(|i| i.kind == "material" && i.id != MEADOW)
    {
        if c.bag_used() >= c.bag_capacity() {
            break;
        }
        c.add_item(&i.id, 1);
    }
    pick(&mut w, 1, patch);
    w.time += PICK_TIME;
    w.update_picking(1);
    assert_eq!(w.players[&1].character.quantity(MEADOW), 0);
    assert_eq!(w.flower_patches[&0][0].picks, patch.picks);
}

#[test]
fn alchemy_harvest_and_staple_brews_independently_can_award_the_last_point_of_every_band() {
    for (band, recipe) in CATALOG
        .recipes
        .iter()
        .filter(|r| r.formula.is_none())
        .enumerate()
    {
        let mut c = Character::mercenary(Class::Warrior, 1, "Test Brewer");
        let end = (band as u16 + 1) * SKILL_BAND;
        c.alchemy.proficiency.skill = end - 1;
        if band > 0 {
            c.alchemy.train(band as u16 - 1, 0.);
            assert_eq!(c.alchemy.proficiency.skill, end - 1);
        }
        let mut harvest = c.alchemy.clone();
        for roll in [0.999, 0.999] {
            harvest.train(band as u16, roll);
            assert_eq!(harvest.proficiency.skill, end - 1);
        }
        harvest.train(band as u16, 0.999);
        assert_eq!(harvest.proficiency.skill, end);

        c.alchemy.recipes.insert(recipe.item.clone());
        let brew = Command::Brew {
            npc: TRAINER.into(),
            recipe: recipe.item.clone(),
        };
        for expected in [end - 1, end - 1, end] {
            for (ids, count) in &recipe.ingredients {
                // At the two alternative bands, use a mixed group.
                for n in 0..*count {
                    c.add_item(&ids[n as usize % ids.len()], 1);
                }
            }
            assert!(workshop_action(&mut c, &brew, 0.999).is_ok());
            assert_eq!(c.alchemy.proficiency.skill, expected);
        }
    }
}

#[test]
fn alchemy_workshop_and_gathering_roll_back_on_failed_save_and_missing_ingredients() {
    let (mut w, _) = fixture();
    train(&mut w, 1);
    let learn = Command::Learn {
        npc: TRAINER.into(),
        recipe: POTION.into(),
    };
    let brew = Command::Brew {
        npc: TRAINER.into(),
        recipe: POTION.into(),
    };
    w.alchemy_command(1, learn);
    w.players.get_mut(&1).unwrap().character.add_item(MEADOW, 4);
    w.alchemy_command(1, brew.clone());
    let c = &mut w.players.get_mut(&1).unwrap().character;
    assert_eq!(c.quantity(MEADOW), 4);
    c.add_item(VIAL, 1);
    let before = c.inventory.clone();
    w.store.conn().execute_batch(
        "CREATE TRIGGER refuse_alchemy_save BEFORE UPDATE ON characters BEGIN SELECT RAISE(FAIL, 'test'); END;"
    ).unwrap();
    w.alchemy_command(1, brew);
    w.ensure_flowers(0);
    let patch = w.flower_patches[&0][0];
    pick(&mut w, 1, patch);
    w.time += PICK_TIME;
    w.update_picking(1);
    assert_eq!(w.players[&1].character.inventory, before);
    assert_eq!(w.players[&1].character.alchemy.proficiency.skill, 1);
    assert_eq!(w.flower_patches[&0][0].picks, patch.picks);
}

#[test]
fn alchemy_brews_share_potion_cooldown_preserve_meals_and_expire_through_death_and_login() {
    let (mut w, token) = fixture();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    for id in [POTION, FLASK, HEALTH, "health_potion"] {
        c.add_item(id, 2);
    }
    c.hp = 40.;
    let p = w.players.get_mut(&1).unwrap();
    p.buffs.push(Buff {
        id: "meal:test".into(),
        kind: BuffKind::Damage,
        amount: 0.03,
        left: 300.,
        time: 300.,
    });
    w.use_item(1, "health_potion");
    w.use_item(1, POTION);
    assert_eq!(w.players[&1].character.quantity(POTION), 2);
    w.use_item(1, FLASK);
    let p = w.players.get_mut(&1).unwrap();
    assert_eq!(p.alchemy_modifier(Stat::Damage), 0.02);
    p.potion_cd = 0.;
    w.use_item(1, POTION);
    w.use_item(1, "health_potion");
    let p = &w.players[&1];
    assert_eq!(p.character.quantity("health_potion"), 1);
    assert_eq!(p.potion_cd, 60.);
    assert_eq!(p.alchemy_modifier(Stat::Damage), 0.04);
    assert_eq!(p.buff(BuffKind::Damage), 0.03);
    assert_eq!(p.alchemy_buffs().len(), 2);

    let saved = w.store.load(&token).unwrap().unwrap();
    assert!(saved.potion_cooldown_left() >= 59.);
    assert_eq!(saved.alchemy.flask.as_ref().unwrap().item, FLASK);
    let (tx, _) = mpsc::channel(8);
    let rejoined = Player::new(saved, tx);
    assert_eq!(rejoined.alchemy_modifier(Stat::Damage), 0.02);
    assert_eq!(rejoined.alchemy_buffs().len(), 1);

    w.players.get_mut(&1).unwrap().character.hp = 0.;
    w.refresh_alchemy(1);
    assert!(w.players[&1].alchemy_potion.is_none());
    assert!(w.players[&1].character.alchemy.flask.is_some());
    w.players.get_mut(&1).unwrap().character.hp = 1.;
    w.use_item(1, HEALTH);
    let p = &mut w.players.get_mut(&1).unwrap();
    assert_eq!(p.character.alchemy_health, 0.02);
    p.character.alchemy.flask.as_mut().unwrap().until = unix_now();
    w.refresh_alchemy(1);
    assert_eq!(w.players[&1].character.alchemy_health, 0.);
    assert!(w.players[&1].alchemy_buffs().is_empty());
}

#[test]
fn alchemy_is_suppressed_in_arenas_and_world_pvp_and_recovers_after_return() {
    let (mut w, _) = fixture();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    c.add_item(HEALTH, 2);
    c.add_item(POTION, 1);
    w.use_item(1, HEALTH);
    let original = w.players[&1]
        .character
        .alchemy
        .flask
        .as_ref()
        .unwrap()
        .until;
    let p = w.players.get_mut(&1).unwrap();
    p.pvp_flag = true;
    w.refresh_alchemy(1);
    w.use_item(1, POTION);
    let p = w.players.get_mut(&1).unwrap();
    assert_eq!(p.character.quantity(POTION), 1);
    assert_eq!(p.character.alchemy_health, 0.);
    assert!(p.alchemy_buffs().is_empty());
    p.pvp_flag = false;
    p.character.zone = 40;
    w.refresh_alchemy(1);
    assert!(w.players[&1].alchemy_buffs().is_empty());
    w.players.get_mut(&1).unwrap().character.zone = 0;
    w.refresh_alchemy(1);
    let c = &w.players[&1].character;
    assert_eq!(c.alchemy_health, 0.02);
    assert_eq!(c.alchemy.flask.as_ref().unwrap().until, original);
}

#[test]
fn alchemy_formulas_drop_from_approved_enemy_groups_and_teach_once() {
    let (mut w, token) = fixture();
    train(&mut w, 1);
    let id = w.players[&1].character.id.clone();
    let point = trainer(&w);
    for (zone, kind, level, formula) in [
        (27, "cairnbehemoth", 93, "alchemy_trailwind_potion_formula"),
        (
            44,
            "null_hour",
            99,
            "alchemy_flask_of_the_turning_year_formula",
        ),
        (
            46,
            "cf_eldmarr",
            99,
            "alchemy_flask_of_the_ashen_ward_formula",
        ),
        (
            39,
            "solstice_heart",
            99,
            "alchemy_flask_of_the_quiet_grove_formula",
        ),
    ] {
        assert_eq!(Slime::default_level(kind), level);
        w.alchemy_rng = 0;
        w.alchemy_formula_drop(&id, zone, point, kind, level);
        assert!(
            w.drops
                .iter()
                .any(|drop| drop.zone == zone && drop.item.as_deref() == Some(formula))
        );
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.add_item(formula, 2);
        let study = Command::Study {
            formula: formula.into(),
        };
        w.alchemy_command(1, study.clone());
        w.alchemy_command(1, study);
        assert_eq!(w.players[&1].character.quantity(formula), 1);
    }
    let saved = w.store.load(&token).unwrap().unwrap();
    assert_eq!(saved.alchemy.recipes.len(), 4);
}

#[test]
fn alchemy_duel_suppresses_existing_flask_before_the_first_hit() {
    let (mut w, _) = fixture();
    w.ensure_flowers(0);
    let point = w.flower_patches[&0][0].point;
    let attacker = at(&mut w, 1, 0, point);
    attacker.character.level = 99;
    attacker.character.add_item(HEALTH, 1);
    let attacker_id = attacker.character.id.clone();
    let defender_id = at(&mut w, 2, 0, point).character.id.clone();
    w.use_item(1, HEALTH);
    let boosted = w.players[&1].character.max_hp();
    w.message(
        1,
        ClientMessage::Pvp {
            command: PvpCommand::DuelRequest { id: defender_id },
        },
    );
    w.message(
        2,
        ClientMessage::Pvp {
            command: PvpCommand::DuelAccept {
                id: attacker_id.clone(),
            },
        },
    );
    assert!(w.in_duel(&attacker_id));
    assert!(w.players[&1].character.max_hp() < boosted);
    assert!(w.players[&1].alchemy_buffs().is_empty());
    w.message(
        1,
        ClientMessage::Pvp {
            command: PvpCommand::DuelCancel,
        },
    );
    assert!(!w.in_duel(&attacker_id));
    assert_eq!(w.players[&1].character.max_hp(), boosted);
    assert_eq!(w.players[&1].alchemy_buffs().len(), 1);
}

#[test]
fn alchemy_healing_bonus_belongs_to_the_caster_and_only_benefits_pve_targets() {
    let (mut w, _) = fixture();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    c.add_item("alchemy_starwhisper_potion", 1);
    let base = w.raid_attack_power(1);
    let mult = 40. / base;
    w.players.get_mut(&2).unwrap().character.hp = 1.;
    w.heal_players(1, &[2], mult);
    assert_eq!(w.players[&2].character.hp, 41.);

    w.use_item(1, "alchemy_starwhisper_potion");
    w.players.get_mut(&2).unwrap().character.hp = 1.;
    w.heal_players(1, &[2], mult);
    assert_eq!(w.players[&2].character.hp, 44.);

    let ally = w.players.get_mut(&2).unwrap();
    ally.character.hp = 1.;
    ally.pvp_flag = true;
    w.heal_players(1, &[2], mult);
    assert_eq!(w.players[&2].character.hp, 41.);
}
