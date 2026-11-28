use super::wyrd_tests::{drain, join, world};
use super::*;

fn command(
    action: &str,
    npc: Option<&str>,
    class: Option<Class>,
    level: Option<u32>,
    gear: Option<&str>,
    kind: Option<&str>,
    count: Option<u32>,
) -> DebugCommand {
    DebugCommand::GmIsland {
        action: action.into(),
        npc: npc.map(str::to_owned),
        class,
        level,
        gear: gear.map(str::to_owned),
        kind: kind.map(str::to_owned),
        count,
    }
}
fn enter(w: &mut World) -> mpsc::Receiver<Value> {
    let rx = join(w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.gm = true;
    w.run_debug(1, command("enter", None, None, None, None, None, None))
        .unwrap();
    rx
}
fn beside(w: &mut World, npc: &str) {
    let z = w.gm_island_zone().unwrap();
    let n = w.maps[z].npcs.iter().find(|n| n.id == npc).unwrap();
    let p = w.players.get_mut(&1).unwrap();
    p.character.x = n.x + 1.;
    p.character.y = n.y;
    p.service_at = -99.;
    p.stop();
}

#[test]
fn gm_island_admission_ignores_test_shortcuts_and_forged_services() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let z = w.gm_island_zone().unwrap();
    w.test_commands = true;
    for c in [
        command("enter", None, None, None, None, None, None),
        command(
            "setup",
            Some("gmi_quartermaster"),
            Some(Class::Mage),
            Some(99),
            Some("rare"),
            None,
            None,
        ),
        DebugCommand::Teleport {
            zone: z,
            x: 212.,
            y: 337.,
        },
    ] {
        assert!(w.run_debug(1, c).is_err());
    }
    let gate = w.maps[0]
        .portals
        .iter()
        .find(|p| p.id == "gmi_gate")
        .unwrap()
        .clone();
    let p = w.players.get_mut(&1).unwrap();
    p.character.x = gate.x;
    p.character.y = gate.y;
    p.portal_at = -99.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 0);
    assert!(
        drain(&mut rx)
            .iter()
            .any(|p| p["text"] == "Only a GM may enter GM Island.")
    );
    w.players.get_mut(&1).unwrap().character.gm = true;
    w.players.get_mut(&1).unwrap().character.spark_travel = Some(SparkTravel {
        destination: "In flight".into(),
        stops: vec![],
        points: vec![],
        next: 0,
    });
    assert!(
        w.run_debug(
            1,
            DebugCommand::Teleport {
                zone: z,
                x: 212.,
                y: 337.
            }
        )
        .is_err(),
        "raw teleport cannot carry a saved flight into the island"
    );
    assert!(w.players[&1].character.gm_island_backup.is_none());
    w.players.get_mut(&1).unwrap().character.spark_travel = None;
    w.run_debug(1, command("enter", None, None, None, None, None, None))
        .unwrap();
    assert!(
        w.run_debug(
            1,
            command(
                "setup",
                Some("gmi_quartermaster"),
                Some(Class::Mage),
                Some(99),
                Some("rare"),
                None,
                None
            )
        )
        .is_err(),
        "range checked"
    );
    beside(&mut w, "gmi_trainer");
    assert!(
        w.run_debug(
            1,
            command(
                "setup",
                Some("gmi_trainer"),
                Some(Class::Mage),
                Some(99),
                Some("rare"),
                None,
                None
            )
        )
        .is_err(),
        "NPC role checked"
    );
    let _normal = join(&mut w, 2, Class::Warrior);
    assert!(
        w.run_debug(
            2,
            DebugCommand::Goto {
                name: "Hero1".into()
            }
        )
        .is_err(),
        "goto cannot follow a GM onto the island"
    );
}

#[test]
fn gm_island_six_villages_and_all_services_are_walkable_in_actual_collision() {
    let w = world();
    let z = w.gm_island_zone().unwrap();
    let m = &w.maps[z];
    assert_eq!(z, 47);
    assert_eq!(m.camps.len(), 6);
    assert!(
        !w.chest_area(z),
        "the laboratory never rolls treasure chests"
    );
    let weather = w.weather.view(z, None, 0);
    assert_eq!(weather["inside"], false);
    assert_eq!(weather["type"], "clear");
    assert_eq!(hosted_counts(m), (6, 0));
    assert_eq!(hosted_npc_count(m), 18);
    let land = m
        .shape_floor
        .iter()
        .map(|r| r.bytes().filter(|&c| c == b'#').count())
        .sum::<usize>();
    let meadow = w.maps[0]
        .shape_floor
        .iter()
        .map(|r| r.bytes().filter(|&c| c == b'#').count())
        .sum::<usize>();
    assert!((land as f64 / meadow as f64 - 1.).abs() < 0.03);
    let size = m.size as usize;
    let mut seen = vec![false; size * size];
    let start = m.spawn.y.floor() as usize * size + m.spawn.x.floor() as usize;
    let mut queue = std::collections::VecDeque::from([start]);
    seen[start] = true;
    while let Some(i) = queue.pop_front() {
        let x = i % size;
        let y = i / size;
        for (a, b) in [
            (x.wrapping_sub(1), y),
            (x + 1, y),
            (x, y.wrapping_sub(1)),
            (x, y + 1),
        ] {
            if a >= size
                || b >= size
                || seen[b * size + a]
                || m.shape_floor[b].as_bytes()[a] != b'#'
            {
                continue;
            }
            let at = Point {
                x: a as f64 + 0.5,
                y: b as f64 + 0.5,
            };
            let mut clear = at;
            m.collide(&mut clear, PLAYER_RADIUS);
            if clear.distance(at) > 1e-6 {
                continue;
            }
            seen[b * size + a] = true;
            queue.push_back(b * size + a);
        }
    }
    for n in &m.npcs {
        assert!(
            seen[n.y as usize * size + n.x as usize],
            "{} reachable",
            n.id
        );
    }
    for s in w.spawns.iter().filter(|s| s.zone == z) {
        assert!(seen[s.y as usize * size + s.x as usize]);
    }
    for g in &m.portals {
        assert!(seen[g.y as usize * size + g.x as usize]);
    }
    assert!(super::guards::hubs_for_map(m).is_empty());
}

#[test]
fn gm_island_dummy_survives_extreme_damage_and_measures_the_normal_hit() {
    let mut w = world();
    let _rx = enter(&mut w);
    let z = w.gm_island_zone().unwrap();
    let id = w
        .slimes
        .iter()
        .position(|s| s.zone == z && s.kind == gm_island::DUMMY)
        .unwrap();
    let at = w.slimes[id].point();
    let kills = w.players[&1].character.kills;
    assert_eq!(w.hit_slime(id, 1, 100., false), 100.);
    assert_eq!(w.damage_meter_view(z)["rows"][0]["damage"], 100.);
    w.hit_slime(id, 1, 1e30, true);
    w.update_slime(id);
    assert!(!w.slimes[id].dead);
    assert_eq!(w.slimes[id].hp, w.slimes[id].max_hp);
    assert_eq!(w.slimes[id].damage, 0.);
    assert_eq!(w.slimes[id].point().distance(at), 0.);
    assert_eq!(w.players[&1].character.kills, kills);
    assert!(w.drops.is_empty());
    w.time += 6.;
    w.update_slime(id);
    w.update_damage_meter();
    assert_eq!(w.damage_meter_view(z)["active"], false);
    beside(&mut w, "gmi_trainer");
    w.run_debug(
        1,
        command(
            "reset_dps",
            Some("gmi_trainer"),
            None,
            None,
            None,
            None,
            None,
        ),
    )
    .unwrap();
    assert_eq!(w.damage_meter_view(z)["rows"][0]["damage"], 0.);
}

#[test]
fn gm_island_all_class_loadouts_are_normal_and_original_character_survives_save() {
    let mut w = world();
    let _rx = enter(&mut w);
    let original =
        serde_json::to_value(w.players[&1].character.gm_island_backup.as_ref().unwrap()).unwrap();
    for class in gauntlet::CLASSES {
        beside(&mut w, "gmi_quartermaster");
        w.run_debug(
            1,
            command(
                "setup",
                Some("gmi_quartermaster"),
                Some(class),
                Some(60),
                Some("rare"),
                None,
                None,
            ),
        )
        .unwrap();
        let c = &w.players[&1].character;
        assert_eq!(c.look.class, class);
        assert_eq!(c.level, 60);
        assert_eq!(c.worn_slots().len(), 10);
        assert!(
            c.equipment
                .values()
                .all(|id| item(id).unwrap().rarity != "gm")
        );
        let roundtrip: Character =
            serde_json::from_value(serde_json::to_value(c).unwrap()).unwrap();
        assert_eq!(
            serde_json::to_value(roundtrip.gm_island_backup.unwrap()).unwrap(),
            original
        );
    }
    beside(&mut w, "gmi_ferryman");
    w.run_debug(
        1,
        command("leave", Some("gmi_ferryman"), None, None, None, None, None),
    )
    .unwrap();
    // The rested clock is stamped with the current second, which may have moved on since the checkpoint.
    let timeless = |mut v: Value| {
        v["rested"].as_object_mut().unwrap().remove("lastSeen");
        v
    };
    assert_eq!(
        timeless(serde_json::to_value(&w.players[&1].character).unwrap()),
        timeless(original)
    );
}

#[test]
fn gm_island_summons_use_new_bounded_slots_no_loot_and_leave_public_foes_untouched() {
    let mut w = world();
    let _rx = enter(&mut w);
    let z = w.gm_island_zone().unwrap();
    let prior: Vec<_> = w
        .slimes
        .iter()
        .map(|s| (s.id, s.kind.clone(), s.zone, s.hp, s.x, s.y))
        .collect();
    beside(&mut w, "gmi_summoner");
    let result = w
        .run_debug(
            1,
            command(
                "summon",
                Some("gmi_summoner"),
                None,
                Some(60),
                None,
                Some("green"),
                Some(2),
            ),
        )
        .unwrap();
    let ids: Vec<_> = result["ids"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_u64().unwrap() as usize)
        .collect();
    for (id, kind, zone, hp, x, y) in prior {
        let s = &w.slimes[id];
        assert_eq!((&s.kind, s.zone, s.hp, s.x, s.y), (&kind, zone, hp, x, y));
    }
    let id = ids[0];
    w.hit_slime(id, 1, 1e30, false);
    assert!(w.slimes[id].dead);
    assert!(w.drops.is_empty());
    w.update_slime(id);
    assert!(w.slimes[id].dead);
    beside(&mut w, "gmi_summoner");
    assert!(
        w.run_debug(
            1,
            command(
                "summon",
                Some("gmi_summoner"),
                None,
                Some(60),
                None,
                Some("green"),
                Some(24)
            )
        )
        .is_err()
    );
    beside(&mut w, "gmi_summoner");
    w.run_debug(
        1,
        command("clear", Some("gmi_summoner"), None, None, None, None, None),
    )
    .unwrap();
    assert!(ids.iter().all(|&id| w.slimes[id].dead));
    assert!(w.maps[z].gm_only);
}

#[test]
fn gm_island_mercenaries_are_limited_and_disappear_when_leaving() {
    let mut w = world();
    let _rx = enter(&mut w);
    beside(&mut w, "gmi_recruiter");
    w.run_debug(
        1,
        command(
            "mercs",
            Some("gmi_recruiter"),
            Some(Class::Priest),
            Some(60),
            None,
            None,
            Some(4),
        ),
    )
    .unwrap();
    assert_eq!(w.players.values().filter(|p| p.merc.is_some()).count(), 4);
    beside(&mut w, "gmi_recruiter");
    assert!(
        w.run_debug(
            1,
            command(
                "mercs",
                Some("gmi_recruiter"),
                Some(Class::Mage),
                Some(60),
                None,
                None,
                Some(1)
            )
        )
        .is_err()
    );
    w.run_debug(
        1,
        DebugCommand::Teleport {
            zone: 0,
            x: 276.,
            y: 226.,
        },
    )
    .unwrap();
    assert_eq!(w.players.values().filter(|p| p.merc.is_some()).count(), 0);
    assert!(w.players[&1].character.gm_island_backup.is_none());
}

#[test]
fn gm_island_saved_ordinary_character_is_returned_to_safe_public_ground() {
    let mut w = world();
    let (tx, _rx) = mpsc::channel(4096);
    let welcome = w
        .join(
            1,
            None,
            Some(Look {
                name: "SavedVisitor".into(),
                ..Look::default()
            }),
            tx,
        )
        .unwrap();
    let token = welcome["token"].as_str().unwrap().to_owned();
    let zone = w.gm_island_zone().unwrap();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.zone = zone;
    c.x = 212.;
    c.y = 337.;
    w.leave(1);
    let (tx, _rx) = mpsc::channel(4096);
    w.join(2, Some(token), None, tx).unwrap();
    let c = &w.players[&2].character;
    assert!(!c.gm);
    assert_eq!(c.zone, 0);
    assert_eq!((c.x, c.y), (w.maps[0].spawn.x, w.maps[0].spawn.y));
}

#[test]
fn gm_island_public_king_timer_ignores_the_sandbox_king() {
    let mut w = world();
    let _rx = enter(&mut w);
    beside(&mut w, "gmi_summoner");
    let z = w.gm_island_zone().unwrap();
    w.run_debug(
        1,
        command(
            "summon",
            Some("gmi_summoner"),
            None,
            Some(6),
            None,
            Some("big"),
            Some(1),
        ),
    )
    .unwrap();
    assert!(
        w.slimes
            .iter()
            .any(|s| s.kind == "big" && !s.dead && s.zone == z)
    );
    for s in w
        .slimes
        .iter_mut()
        .filter(|s| s.kind == "big" && s.zone != z)
    {
        s.dead = true;
    }
    w.next_king_spawn = 0.;
    w.update_king_spawn();
    assert!(
        w.slimes
            .iter()
            .any(|s| s.kind == "big" && !s.dead && s.zone == 0)
    );
}

#[test]
fn gm_island_reciprocal_gates_and_warden_return_never_bounce() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.gm = true;
    let zone = w.gm_island_zone().unwrap();
    let gate = w.maps[0]
        .portals
        .iter()
        .find(|p| p.id == "gmi_gate")
        .unwrap()
        .clone();
    for _ in 0..2 {
        let p = w.players.get_mut(&1).unwrap();
        p.character.zone = 0;
        p.character.x = gate.x;
        p.character.y = gate.y;
        p.portal_at = -99.;
        w.use_portal(1);
        assert_eq!(w.players[&1].character.zone, zone);
        beside(&mut w, "gmi_ferryman");
        w.run_debug(
            1,
            command("leave", Some("gmi_ferryman"), None, None, None, None, None),
        )
        .unwrap();
        let c = &w.players[&1].character;
        assert_eq!(c.zone, 0);
        assert!(
            c.point().distance(Point {
                x: gate.x,
                y: gate.y
            }) > gate.r.max(2.8)
        );
    }
    let p = w.players.get_mut(&1).unwrap();
    p.character.x = gate.x;
    p.character.y = gate.y;
    p.portal_at = -99.;
    w.use_portal(1);
    let gate = w.maps[zone].portals[0].clone();
    let p = w.players.get_mut(&1).unwrap();
    p.character.x = gate.x;
    p.character.y = gate.y;
    p.portal_at = -99.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 0);
    assert!(w.players[&1].character.gm_island_backup.is_none());
}

#[test]
fn gm_island_seasonal_bosses_fight_without_opening_public_hunts() {
    let mut w = world();
    let _rx = enter(&mut w);
    beside(&mut w, "gmi_summoner");
    let info = w
        .run_debug(1, command("info", None, None, None, None, None, None))
        .unwrap();
    for kind in [
        "grinch",
        "hollow_rider",
        "briarheart",
        "bloomwarden",
        "birchcrown",
        "starrocketeer",
    ] {
        assert!(
            info["enemies"]
                .as_array()
                .unwrap()
                .iter()
                .any(|e| e["kind"] == kind)
        );
    }
    let r = w
        .run_debug(
            1,
            command(
                "summon",
                Some("gmi_summoner"),
                None,
                Some(60),
                None,
                Some("grinch"),
                Some(1),
            ),
        )
        .unwrap();
    let id = r["ids"][0].as_u64().unwrap() as usize;
    let at = w.slimes[id].point();
    let p = w.players.get_mut(&1).unwrap();
    p.character.x = at.x + 3.;
    p.character.y = at.y;
    assert_eq!(w.hit_slime(id, 1, 100., false), 100.);
    w.update_slime(id);
    assert_eq!(w.slimes[id].target, Some(1));
    assert!(w.seasonal_hunt.is_none());
    w.hit_slime(id, 1, 1e30, false);
    assert!(w.slimes[id].dead);
    assert!(w.drops.is_empty());
    w.players.get_mut(&1).unwrap().character.zone = 0;
    assert!(
        !w.festival_member("grinch", 1),
        "calendar bypass applies only on the island"
    );
}

#[test]
fn gm_island_spark_destinations_stay_separate_and_are_free_on_the_island() {
    let mut w = world();
    let mut gm = enter(&mut w);
    let mut ordinary = join(&mut w, 2, Class::Warrior);
    let n = w.maps[0]
        .npcs
        .iter()
        .find(|n| n.travel_stop.is_some())
        .unwrap()
        .clone();
    let p = w.players.get_mut(&2).unwrap();
    p.character.x = n.x + 1.;
    p.character.y = n.y;
    w.spark_interact(2, &n.id, None);
    let reply = drain(&mut ordinary)
        .into_iter()
        .find(|p| p["type"] == "dialogue")
        .unwrap();
    assert!(
        reply["travel"]
            .as_array()
            .unwrap()
            .iter()
            .all(|o| !o["id"].as_str().unwrap().starts_with("gmi_"))
    );
    beside(&mut w, "gmi_travel_christmas");
    w.spark_interact(1, "gmi_travel_christmas", None);
    let reply = drain(&mut gm)
        .into_iter()
        .find(|p| p["type"] == "dialogue")
        .unwrap();
    let options = reply["travel"].as_array().unwrap();
    assert_eq!(options.len(), 5);
    assert!(
        options
            .iter()
            .all(|o| o["id"].as_str().unwrap().starts_with("gmi_")
                && o["cost"] == 0
                && o["available"] == true)
    );
}

#[test]
fn gm_island_recovery_revives_the_gm_without_making_mercenaries_immortal() {
    let mut w = world();
    let _rx = enter(&mut w);
    beside(&mut w, "gmi_recruiter");
    w.run_debug(
        1,
        command(
            "mercs",
            Some("gmi_recruiter"),
            Some(Class::Priest),
            Some(60),
            None,
            None,
            Some(1),
        ),
    )
    .unwrap();
    let merc = *w.players.keys().find(|&&s| s != 1).unwrap();
    w.players.get_mut(&merc).unwrap().character.hp = 0.;
    w.update_player(merc);
    assert!(w.players[&merc].character.hp <= 0.);
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    w.update_player(1);
    assert_eq!(w.players[&1].character.hp, w.players[&1].character.max_hp());
    let z = w.gm_island_zone().unwrap();
    assert_eq!(
        w.players[&1].character.point().distance(w.maps[z].spawn),
        0.
    );
}
