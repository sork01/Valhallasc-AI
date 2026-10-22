//! Focused Foundry integration and full-blue/green hired-brain calibration.
use super::ttk::*;
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;
const ZONE: usize = 44;
const YEARWHEEL: usize = 28;

/// The Foundry's key quest, finished: what the door wants.
fn key_quest_done(w: &mut World, id: u64) {
    w.players
        .get_mut(&id)
        .unwrap()
        .character
        .quests
        .push(QuestProgress {
            id: "null_keys".into(),
            counts: vec![1; 4],
            claimed: true,
            completions: 1,
        });
}

#[test]
fn blackhour_press_warns_and_spares_players_who_step_aside() {
    for low_health in [false, true] {
        let mut w = world();
        let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
        for s in &mut w.slimes {
            s.dead = true;
            s.respawn = 1e9;
        }
        let boss = w
            .slimes
            .iter()
            .position(|s| s.zone == ZONE && s.kind == "null_hour")
            .unwrap();
        w.slimes[boss].dead = false;
        w.slimes[boss].state = "chase".into();
        w.slimes[boss].target = Some(1);
        if low_health {
            w.slimes[boss].hp *= 0.3;
        }
        w.enter_instance(ZONE);
        place(&mut w, 1, ZONE, at(80., 31.));
        place(&mut w, 2, ZONE, at(80., 33.));
        let mut lane = None;
        for _ in 0..(30. / TICK) as usize {
            w.time += TICK;
            w.tick += 1;
            w.update_boss_mechanics();
            for view in w.boss_mech_view(ZONE) {
                if view["cast"]["name"] != "Midnight Press" {
                    continue;
                }
                let shape = &view["tele"][0]["shapes"][0];
                let ax = shape["x1"].as_f64().unwrap();
                let ay = shape["y1"].as_f64().unwrap();
                let bx = shape["x2"].as_f64().unwrap();
                let by = shape["y2"].as_f64().unwrap();
                let len = (bx - ax).hypot(by - ay);
                let mid = at((ax + bx) * 0.5, (ay + by) * 0.5);
                let offset = shape["half"].as_f64().unwrap() + 1.5;
                let safe = at(
                    mid.x - (by - ay) / len * offset,
                    mid.y + (bx - ax) / len * offset,
                );
                let mut resolved = safe;
                w.maps[ZONE].collide(&mut resolved, PLAYER_RADIUS);
                assert!(
                    resolved.distance(safe) < 1e-6,
                    "safe ground fits inside the real clock hall"
                );
                lane = Some((mid, safe));
                break;
            }
            if lane.is_some() {
                break;
            }
        }
        let (danger, safe) = lane.expect("visible Midnight Press warning");
        place(&mut w, 1, ZONE, safe);
        place(&mut w, 2, ZONE, danger);
        for _ in 0..(4.8 / TICK) as usize {
            w.time += TICK;
            w.tick += 1;
            w.update_boss_mechanics();
            assert!(
                w.players[&2].character.hp > 0.,
                "warning must precede lethal impact"
            );
        }
        for _ in 0..(0.5 / TICK) as usize {
            w.time += TICK;
            w.tick += 1;
            w.update_boss_mechanics();
        }
        assert!(
            w.players[&1].character.hp > 0.,
            "stepping sideways avoids the press"
        );
        assert!(w.players[&2].fallen && w.players[&2].character.hp <= 0.);
        if low_health {
            place(&mut w, 1, ZONE, danger);
            for _ in 0..(3.2 / TICK) as usize {
                w.time += TICK;
                w.tick += 1;
                w.update_boss_mechanics();
            }
            assert!(
                w.players[&1].fallen,
                "the wider final phase presses the same strip again"
            );
        }
    }
}

#[test]
fn blackhour_data_and_actual_collision() {
    let w = world();
    let m = &w.maps[ZONE];
    assert_eq!(
        (m.name.as_str(), m.min_level, m.players, m.copies),
        ("The Black Hour Foundry", 99, 5, 4)
    );
    assert!(m.interior && m.slimes.len() == 15);
    assert!(!m.sealed_template, "the validated Foundry entrance is open");
    for (kind, health) in [
        ("null_hauler", 18.),
        ("null_breaker", 18.),
        ("null_coil", 18.),
        ("null_bell", 15.),
        ("null_conductor", 15.),
        ("null_hour", 8.5),
    ] {
        let enemy = w
            .slimes
            .iter()
            .find(|s| s.zone == ZONE && s.kind == kind)
            .unwrap();
        let base = crate::cathedral::enemy(kind).unwrap();
        assert!(
            (enemy.max_hp - base.stats[0] * health).abs() < 0.1,
            "{kind}: measured health multiplier"
        );
    }
    for (kind, start) in [
        ("null_bell", 224.),
        ("null_conductor", 248.),
        ("null_hour", 608.),
    ] {
        assert_eq!(crate::items::enrage(kind), Some((start, 0.2)));
    }
    assert!(pursuit::grid_matches_collision(m, PLAYER_RADIUS));
    let seen = flood(m, &blocked(m, &[]), m.spawn);
    for p in m
        .slimes
        .iter()
        .map(|s| at(s.x, s.y))
        .chain(m.npcs.iter().map(|n| at(n.x, n.y)))
        .chain(m.portals.iter().map(|p| at(p.x, p.y)))
    {
        assert!(reached(m, &seen, p), "unreachable {p:?}");
    }
    for point in [at(80., 100.), at(3., 3.)] {
        let mut actual = point;
        m.collide(&mut actual, PLAYER_RADIUS);
        assert!(actual.distance(point) > 0.01);
    }
    let gear: Vec<_> = ITEMS
        .iter()
        .filter(|i| i.source.as_deref() == Some("blackhour"))
        .collect();
    assert_eq!(gear.len(), 29);
    assert!(
        gear.iter()
            .all(|i| i.rarity == "epic" && i.required_level == 99)
    );
    assert_eq!(w.maps[43].name, "The Drowned Longship");
    assert_eq!(w.instances.iter().filter(|i| i.template == ZONE).count(), 4);
    for p in &m.portals {
        let dst = &w.maps[p.to];
        let mut q = at(p.tx, p.ty);
        dst.collide(&mut q, PLAYER_RADIUS);
        assert!(q.distance(at(p.tx, p.ty)) < 1e-6);
        assert!(dst.slimes.iter().all(|s| at(s.x, s.y).distance(q) > 8.));
    }
}

fn enter(w: &mut World, id: u64) {
    place(w, id, 28, at(208., 200.));
    w.time += 2.;
    w.use_portal(id);
}

#[test]
fn blackhour_gate_private_copies_epic_loot_and_clear() {
    let mut w = world();
    w.maps[ZONE].sealed_template = false;
    let _receivers: Vec<_> = (1..=3).map(|id| join(&mut w, id, Class::Warrior)).collect();
    for id in 1..=3 {
        w.players.get_mut(&id).unwrap().character.level = 99;
    }
    w.players.get_mut(&1).unwrap().character.level = 98;
    enter(&mut w, 1);
    assert_eq!(w.players[&1].character.zone, 28);
    w.players.get_mut(&1).unwrap().character.level = 99;
    // Level 99 is not enough: the door wants the finished key quest.
    enter(&mut w, 1);
    assert_eq!(w.players[&1].character.zone, 28, "no quest, no door");
    for id in 1..=3 {
        key_quest_done(&mut w, id);
    }
    let ally = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(ally),
            name: None,
        },
    );
    w.social(
        2,
        SocialCommand::PartyAccept {
            id: w.players[&1].character.id.clone(),
        },
    );
    for id in 1..=3 {
        enter(&mut w, id);
    }
    let zone = w.players[&1].character.zone;
    let other = w.players[&3].character.zone;
    assert_eq!(zone, w.players[&2].character.zone);
    assert_ne!(zone, other);
    assert_eq!(w.public_zone(zone), ZONE);
    for id in 1..=2 {
        for q in ["null_bell", "null_current"] {
            w.players
                .get_mut(&id)
                .unwrap()
                .character
                .quests
                .push(QuestProgress {
                    id: q.into(),
                    counts: vec![0],
                    claimed: false,
                    completions: 0,
                });
        }
    }
    for (n, kind) in ["null_hour", "null_bell", "null_conductor"]
        .iter()
        .enumerate()
    {
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == zone && s.kind == *kind)
            .unwrap();
        let point = w.slimes[id].point();
        for s in 1..=2 {
            place(&mut w, s, zone, point);
        }
        w.hit_slime(id, 1, 1e12, false);
        assert_eq!(w.instance_cleared(zone), n == 2);
        assert!(!w.instance_cleared(other));
    }
    // Party votes hold their actual epic catalog pieces before pickup.
    assert_eq!(
        w.rolls.len(),
        4,
        "side bosses give one pool each, final gives two"
    );
    assert!(w.rolls.iter().all(|r| {
        item(&r.item)
            .is_some_and(|i| i.source.as_deref() == Some("blackhour") && i.rarity == "epic")
    }));
    assert!(
        w.players[&1]
            .character
            .quests
            .iter()
            .filter(|q| q.id.starts_with("null_") && q.id != "null_keys")
            .all(|q| q.counts == vec![1])
    );
    assert!(
        w.players[&2]
            .character
            .quests
            .iter()
            .filter(|q| q.id.starts_with("null_") && q.id != "null_keys")
            .all(|q| q.counts == vec![1])
    );
    assert_eq!(
        w.slimes
            .iter()
            .filter(|s| s.zone == other && !s.dead)
            .count(),
        15
    );
    place(&mut w, 1, zone, at(80., 13.));
    w.time += 2.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 28);
    place(&mut w, 2, zone, at(72., 143.));
    w.time += 2.;
    w.use_portal(2);
    assert_eq!(w.players[&2].character.zone, 28);
}

#[test]
fn blackhour_ordinary_kills_drop_their_material_and_only_purple_gear() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    for kind in ["null_hauler", "null_breaker", "null_coil"] {
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == ZONE && s.kind == kind)
            .unwrap();
        let point = w.slimes[id].point();
        place(&mut w, 1, ZONE, point);
        w.drops.clear();
        // Seed 9: bag misses, ordinary equipment roll succeeds. No farming loop.
        w.rng = 9;
        w.hit_slime(id, 1, 1e12, false);
        assert!(
            w.drops
                .iter()
                .any(|d| d.item.as_deref() == Some(&format!("{kind}_relic")))
        );
        let gear: Vec<_> = w
            .drops
            .iter()
            .filter_map(|d| d.item.as_deref().and_then(item))
            .filter(|i| is_gear(i))
            .collect();
        assert_eq!(gear.len(), 1, "one successful ordinary equipment roll");
        assert!(
            gear.iter()
                .all(|i| i.rarity == "epic" && i.source.as_deref() == Some("blackhour"))
        );
    }
}

#[test]
fn blackhour_chests_and_cold_restart_use_epic_equipment() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, ZONE, at(80., 143.));
    let owner = w.players[&1].character.id.clone();
    w.chest_contents(&owner, ZONE, at(80., 143.));
    let equipment: Vec<_> = w
        .drops
        .iter()
        .filter_map(|d| d.item.as_deref().and_then(item))
        .filter(|i| is_gear(i))
        .collect();
    assert!(equipment.len() >= 2);
    assert!(
        equipment
            .iter()
            .all(|i| i.source.as_deref() == Some("blackhour") && i.rarity == "epic")
    );
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 99;
    let mut slots = BTreeMap::new();
    for kind in [
        "armor",
        "headgear",
        "shoulders",
        "gloves",
        "weapon",
        "pants",
        "necklace",
        "cloak",
        "accessory",
    ] {
        let i = ITEMS
            .iter()
            .find(|i| {
                i.source.as_deref() == Some("blackhour")
                    && i.kind == kind
                    && i.class.is_none_or(|c| c == Class::Warrior)
            })
            .unwrap();
        c.add_item(&i.id, 1);
        slots.insert(
            match kind {
                "armor" => "chest",
                "weapon" => "hands",
                "accessory" => "accessory1",
                v => v,
            }
            .into(),
            i.id.clone(),
        );
    }
    c.equip_slots(&slots).unwrap();
    assert_eq!(c.set_counts()["blackhour"], 8);
    c.resource = Some(0.);
    let expected = c.max_resource() * 0.02;
    let shield = c.max_hp() * 0.05;
    assert_eq!(
        w.apply_set_signature(1, "whirlwind", at(80., 143.), at(1., 0.), None, &[])
            .as_deref(),
        Some("blackhour")
    );
    assert!((w.players[&1].character.resource() - expected).abs() < 1e-6);
    assert!((w.players[&1].set_shield - shield).abs() < 1e-6);
    assert!(
        w.apply_set_signature(1, "whirlwind", at(80., 143.), at(1., 0.), None, &[])
            .is_none()
    );
}

#[test]
#[ignore = "Foundry-only full fights, run with --ignored --nocapture"]
fn blackhour_blue_and_green_encounter_bands() {
    let w = world();
    let spawns: Vec<_> = w.slimes.iter().filter(|s| s.zone == ZONE).collect();
    let packs: Vec<Vec<usize>> = (0..4)
        .map(|p| spawns[p * 3..p * 3 + 3].iter().map(|s| s.id).collect())
        .collect();
    let mut fights: Vec<(String, Vec<usize>, f64)> = packs
        .into_iter()
        .enumerate()
        .map(|(i, p)| (format!("pack{}", i + 1), p, 120.))
        .collect();
    for s in &spawns[12..] {
        fights.push((
            s.kind.clone(),
            vec![s.id],
            if s.kind == "null_hour" { 300. } else { 180. },
        ));
    }
    let seeds = std::env::var("BLACKHOUR_SEEDS")
        .ok()
        .and_then(|s| s.parse::<u64>().ok())
        .unwrap_or(2);
    let wanted = std::env::var("BLACKHOUR_FIGHTS").unwrap_or_default();
    let rarities = std::env::var("BLACKHOUR_RARITIES").unwrap_or_default();
    let measure = std::env::var("BLACKHOUR_MEASURE").is_ok();
    let mut failed = vec![];
    let mut ran = 0;
    for (name, ids, min) in fights
        .into_iter()
        .filter(|(n, _, _)| wanted.is_empty() || wanted.split(',').any(|s| s == n))
    {
        for rarity in ["rare", "uncommon"]
            .into_iter()
            .filter(|r| rarities.is_empty() || rarities.split(',').any(|v| v == *r))
        {
            for seed in 1..=seeds {
                ran += 1;
                let case = Case {
                    rarity,
                    cap: Some(720.),
                    consumables: true,
                    run_to_end: true,
                    ..Case::new(Class::Warrior, 99)
                };
                let out = run_geared_hired_party(&case, &ids, seed);
                eprintln!(
                    "[blackhour] {name} {rarity} seed{seed}: won={} time={:.1} falls={} left={:.3} dps={:?}",
                    out.killed, out.seconds, out.deaths, out.enemy_left, out.dps
                );
                if !measure
                    && ((rarity == "rare" && (!out.killed || out.seconds < min))
                        || (rarity == "uncommon" && name == "null_hour" && out.killed))
                {
                    failed.push(format!("{name} {rarity} seed{seed}: {out:?}"));
                }
            }
        }
    }
    assert!(
        ran > 0,
        "the selected Foundry fights and rarities must exist"
    );
    assert!(failed.is_empty(), "{}", failed.join("\n"));
}

/// Walks a hero through a Yearwheel door, as the player would.
fn through(w: &mut World, id: u64, door: &str) {
    let p = w.maps[YEARWHEEL]
        .portals
        .iter()
        .find(|p| p.id == door)
        .unwrap()
        .clone();
    place(w, id, YEARWHEEL, at(p.x, p.y));
    w.time += 2.;
    w.use_portal(id);
}

#[test]
fn blackhour_door_opens_only_after_the_four_hour_shards_are_handed_in() {
    let mut w = world();
    let _receivers: Vec<_> = (1..=2).map(|id| join(&mut w, id, Class::Warrior)).collect();
    for id in 1..=2 {
        w.players.get_mut(&id).unwrap().character.level = 99;
    }
    let ally = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(ally),
            name: None,
        },
    );
    w.social(
        2,
        SocialCommand::PartyAccept {
            id: w.players[&1].character.id.clone(),
        },
    );
    let quest = w
        .maps
        .iter()
        .flat_map(|m| m.quests.iter())
        .find(|q| q.id == "null_keys")
        .unwrap()
        .clone();
    assert_eq!(quest.min_level, 99);
    assert_eq!(quest.objectives.len(), 4);
    // Obtainable at level 99 only.
    w.players.get_mut(&1).unwrap().character.level = 98;
    assert!(
        !quest_action(
            &mut w.players.get_mut(&1).unwrap().character,
            &quest,
            "accept"
        )
        .2
    );
    w.players.get_mut(&1).unwrap().character.level = 99;
    assert!(
        quest_action(
            &mut w.players.get_mut(&1).unwrap().character,
            &quest,
            "accept"
        )
        .2
    );
    // The follow-up quest inside the Foundry waits for it.
    let entry = w
        .maps
        .iter()
        .flat_map(|m| m.quests.iter())
        .find(|q| q.id == "null_entry")
        .unwrap();
    assert!(!entry.unlocked(&w.players[&1].character));
    // Hero 2 never took the quest: the four bosses drop nothing for them.
    for (n, (boss, shard)) in hour_shards::SHARDS.iter().enumerate() {
        let door = [
            "year_bloom_descent",
            "year_solar_descent",
            "year_amber_descent",
            "year_solstice_descent",
        ][n];
        for id in 1..=2 {
            through(&mut w, id, door);
        }
        let zone = w.players[&1].character.zone;
        assert_ne!(zone, YEARWHEEL, "{door} leads into the dungeon");
        assert_eq!(zone, w.players[&2].character.zone);
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == zone && s.kind == *boss)
            .unwrap_or_else(|| panic!("{boss} stands in its dungeon"));
        let point = w.slimes[id].point();
        for s in 1..=2 {
            place(&mut w, s, zone, point);
        }
        w.drops.clear();
        w.hit_slime(id, 1, 1e12, false);
        let mine = w.players[&1].character.id.clone();
        let theirs = w.players[&2].character.id.clone();
        let shards: Vec<_> = w
            .drops
            .iter()
            .filter(|d| d.item.as_deref() == Some(*shard))
            .collect();
        assert_eq!(
            shards.len(),
            1,
            "{boss}: one shard, for the hero on the quest"
        );
        assert_eq!(shards[0].owner, mine);
        assert!(!shards[0].open_to(&theirs), "{boss}: the shard is private");
        // The hero walks over it; it is in the bag and counts for the quest.
        for d in &mut w.drops {
            d.t = 1.;
        }
        w.update_drops();
        assert_eq!(w.players[&1].character.quantity(shard), 1, "{boss}");
        assert_eq!(w.players[&2].character.quantity(shard), 0, "{boss}");
        // A second kill while the shard is held drops no second one.
        let mut probe = w.players[&1].character.clone();
        quest.sync_bring(&mut probe);
        let counts = &probe
            .quests
            .iter()
            .find(|q| q.id == "null_keys")
            .unwrap()
            .counts;
        assert_eq!(counts.iter().sum::<u32>() as usize, n + 1, "{boss} counts");
        w.hour_shard_drops(boss, zone, point, &mine, std::slice::from_ref(&mine));
        assert!(w.drops.iter().all(|d| d.item.as_deref() != Some(*shard)));
        // Leave through the dungeon's own way out so the next door is the Yearwheel's.
        let back = w.maps[zone].portals.first().unwrap().clone();
        for id in 1..=2 {
            place(&mut w, id, zone, at(back.x, back.y));
            w.time += 2.;
            w.use_portal(id);
            assert_eq!(w.players[&id].character.zone, YEARWHEEL, "{boss} way out");
        }
    }
    // All four in the bag, but the quest is not handed in yet: the door stays shut.
    through(&mut w, 1, "year_blackhour");
    assert_eq!(w.players[&1].character.zone, YEARWHEEL);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    let (_, _, ok) = {
        let r = quest_action(c, &quest, "claim");
        (r.0, r.1, r.2)
    };
    assert!(ok, "four shards are enough to claim");
    for (_, shard) in hour_shards::SHARDS {
        assert_eq!(c.quantity(shard), 0, "handed in");
    }
    assert!(entry_unlocked(&w, 1));
    through(&mut w, 1, "year_blackhour");
    assert_ne!(w.players[&1].character.zone, YEARWHEEL, "the door opens");
    // The party mate who never did the quest is still turned away.
    through(&mut w, 2, "year_blackhour");
    assert_eq!(w.players[&2].character.zone, YEARWHEEL);
}

fn entry_unlocked(w: &World, id: u64) -> bool {
    w.maps
        .iter()
        .flat_map(|m| m.quests.iter())
        .find(|q| q.id == "null_entry")
        .unwrap()
        .unlocked(&w.players[&id].character)
}

#[test]
fn hour_shards_cannot_be_sold_or_traded() {
    for (_, shard) in hour_shards::SHARDS {
        let i = item(shard).unwrap();
        assert!(is_quest_item(i), "{shard}");
        let mut c = Character::mercenary(Class::Warrior, 99, "Probe");
        c.add_item(shard, 1);
        assert!(c.sell_item(shard, 1).is_err(), "{shard}");
        assert_eq!(c.quantity(shard), 1);
    }
}
