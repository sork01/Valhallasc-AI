//! The game master's test menu (`gm_test.rs`): only the GM runs it, it enters, resets and tunes a copy without touching any
//! other, and a test gauntlet run reads and writes no quest.
use super::gauntlet::CLASSES;
use super::wyrd_tests::{drain, join, world};
use super::*;

fn undervault(w: &World) -> usize {
    w.maps
        .iter()
        .position(|m| m.name == "The Undervault" && m.template.is_none())
        .unwrap()
}
fn gm(w: &mut World, session: u64) -> mpsc::Receiver<Value> {
    let rx = join(w, session, Class::Warrior);
    w.players.get_mut(&session).unwrap().character.gm = true;
    rx
}
fn ok(w: &mut World, session: u64, command: DebugCommand) -> Value {
    w.run_debug(session, command).unwrap()
}
fn enter(w: &mut World, session: u64, zone: usize, at: &str) -> Value {
    ok(
        w,
        session,
        DebugCommand::GmDungeonEnter {
            zone,
            at: at.into(),
            pack: 0,
            level: true,
            gear: Some("blue".into()),
            mercs: true,
        },
    )
}

#[test]
fn only_the_gm_may_run_the_menu_ops() {
    let mut w = world();
    w.test_commands = false;
    let mut normal = join(&mut w, 1, Class::Warrior);
    w.debug(1, Some(7), DebugCommand::GmTestInfo);
    let answer = drain(&mut normal)
        .into_iter()
        .find(|v| v["type"] == "debug")
        .unwrap();
    assert_eq!(answer["ok"], false);
    let _gm_rx = gm(&mut w, 2);
    w.debug(2, Some(8), DebugCommand::GmTestInfo);
    let info = w.gm_test_info(2).unwrap();
    assert_eq!(info["supported"], true);
}

#[test]
fn the_menu_lists_every_open_dungeon_but_not_the_raid_and_the_gauntlet_levels() {
    let mut w = world();
    let _rx = gm(&mut w, 1);
    let info = w.gm_test_info(1).unwrap();
    let names: Vec<&str> = info["dungeons"]
        .as_array()
        .unwrap()
        .iter()
        .map(|d| d["name"].as_str().unwrap())
        .collect();
    assert!(names.contains(&"The Undervault") && names.contains(&"The Black Hour Foundry"));
    assert!(!names.contains(&"The Chained Forge"));
    assert!(names.len() >= 19, "{names:?}");
    assert!(!info["gauntletLevels"].as_array().unwrap().is_empty());
}

#[test]
fn entering_a_dungeon_puts_a_visible_hero_with_level_gear_and_four_hired_fighters_in_a_copy() {
    let mut w = world();
    let _rx = gm(&mut w, 1);
    let zone = undervault(&w);
    let out = enter(&mut w, 1, zone, "boss");
    let p = &w.players[&1];
    assert_eq!(out["mercs"], 4);
    assert_eq!(w.instance_at(p.character.zone).unwrap().template, zone);
    assert!(!p.is_hidden() && p.character.level == w.dungeon_level(zone));
    assert!(
        p.character.equipment.len() >= 8,
        "{:?}",
        p.character.equipment
    );
    let boss = w.dungeon_boss(zone).unwrap();
    let d = p.character.point().distance(boss);
    assert!(d > 2. && d < 12., "{d}");
    let hired = w
        .players
        .values()
        .filter(|q| q.merc.is_some() && q.character.zone == p.character.zone)
        .count();
    assert_eq!(hired, 4);
    // A second entry replaces the hired fighters instead of stacking them.
    enter(&mut w, 1, zone, "door");
    assert_eq!(w.players.values().filter(|q| q.merc.is_some()).count(), 4);
    // A non-dungeon zone and the raid are refused.
    assert!(
        w.gm_dungeon_enter(1, 0, "door", 0, false, None, false)
            .is_err()
    );
    let raid = w.maps.iter().position(|m| m.raid).unwrap();
    assert!(
        w.gm_dungeon_enter(1, raid, "door", 0, false, None, false)
            .is_err()
    );
}

#[test]
fn a_pack_jump_lands_near_a_pack() {
    let mut w = world();
    let _rx = gm(&mut w, 1);
    let zone = undervault(&w);
    assert!(!w.dungeon_packs(zone).is_empty());
    let out = w
        .gm_dungeon_enter(1, zone, "pack", 0, false, None, false)
        .unwrap();
    assert_eq!(out["at"], "pack");
    assert!(
        w.gm_dungeon_enter(1, zone, "pack", 999, false, None, false)
            .is_err()
    );
}

#[test]
fn tuning_belongs_to_the_gms_copy_and_goes_when_the_copy_resets() {
    let mut w = world();
    let _a = gm(&mut w, 1);
    let _b = join(&mut w, 2, Class::Mage);
    let zone = undervault(&w);
    enter(&mut w, 1, zone, "door");
    let mine = w.players[&1].character.zone;
    let pack = w
        .spawns
        .iter()
        .find(|s| s.zone == mine && crate::items::elite_power(&s.kind).1 > 2.)
        .map(|s| s.kind.clone())
        .unwrap();
    ok(
        &mut w,
        1,
        DebugCommand::GmTune {
            key: "pack_damage".into(),
            value: 0.5,
        },
    );
    ok(
        &mut w,
        1,
        DebugCommand::GmTune {
            key: "enrage_start".into(),
            value: 2.,
        },
    );
    assert_eq!(w.tuned(mine, &pack), (0.5, 2.));
    // A plain elite is no pack, so it keeps its damage; another copy and a normal player are untouched.
    assert_eq!(w.tuned(mine, "cinderlord").0, 1.);
    let other = w
        .instances
        .iter()
        .find(|i| i.template == zone && i.zone != mine)
        .unwrap()
        .zone;
    assert_eq!(w.tuned(other, &pack), (1., 1.));
    assert_eq!(w.tuned(0, &pack), (1., 1.));
    // The enrage start moves with the scale.
    let start = crate::items::enrage("hollowking").unwrap().0;
    assert_eq!(
        crate::items::enrage_factor_scaled("hollowking", start * 1.5, 2.),
        1.
    );
    assert!(w.tuned_enrage_factor(mine, "hollowking", start * 1.5) == 1.);
    assert!(w.tuned_enrage_factor(other, "hollowking", start * 1.5) > 1.);
    // Bad values and keys are refused; a reset clears everything.
    assert!(
        w.run_debug(
            1,
            DebugCommand::GmTune {
                key: "pack_damage".into(),
                value: 0.
            }
        )
        .is_err()
    );
    assert!(
        w.run_debug(
            1,
            DebugCommand::GmTune {
                key: "nope".into(),
                value: 1.
            }
        )
        .is_err()
    );
    ok(
        &mut w,
        1,
        DebugCommand::GmTune {
            key: "reset".into(),
            value: 0.,
        },
    );
    assert_eq!(w.tuned(mine, &pack), (1., 1.));
    // Multipliers need a copy (or a run) to belong to.
    let mut outside = world();
    let _rx = gm(&mut outside, 1);
    assert!(
        outside
            .run_debug(
                1,
                DebugCommand::GmTune {
                    key: "pack_damage".into(),
                    value: 0.5
                }
            )
            .is_err()
    );
}

#[test]
fn boss_health_scales_in_the_copy_survives_a_reset_and_returns_on_reset_of_the_tuning() {
    let mut w = world();
    let _rx = gm(&mut w, 1);
    let zone = undervault(&w);
    enter(&mut w, 1, zone, "boss");
    let mine = w.players[&1].character.zone;
    let boss = w
        .slimes
        .iter()
        .position(|s| s.zone == mine && s.kind == "hollowking")
        .unwrap();
    let base = w.slimes[boss].max_hp;
    ok(
        &mut w,
        1,
        DebugCommand::GmTune {
            key: "boss_health".into(),
            value: 0.5,
        },
    );
    assert!((w.slimes[boss].max_hp - base * 0.5).abs() < 1e-6);
    ok(&mut w, 1, DebugCommand::GmDungeonReset);
    assert!((w.slimes[boss].max_hp - base * 0.5).abs() < 1e-6);
    assert!(!w.slimes[boss].dead);
    ok(
        &mut w,
        1,
        DebugCommand::GmTune {
            key: "reset".into(),
            value: 0.,
        },
    );
    assert!((w.slimes[boss].max_hp - base).abs() < 1e-6);
    // The enrage skip moves a fighting boss to its start.
    w.slimes[boss].state = "chase".into();
    let out = ok(
        &mut w,
        1,
        DebugCommand::GmEnrage {
            action: "skip".into(),
        },
    );
    let start = crate::items::enrage("hollowking").unwrap().0;
    assert!(w.slimes[boss].fight > start);
    assert!(
        out["bosses"]
            .as_array()
            .unwrap()
            .iter()
            .any(|b| b["kind"] == "hollowking")
    );
}

#[test]
fn a_test_gauntlet_starts_at_the_chosen_fight_without_touching_a_quest() {
    let mut w = world();
    let _rx = gm(&mut w, 1);
    let level = w.gauntlet_levels()[0];
    let quests_before = json!(w.players[&1].character.quests);
    assert!(
        w.run_debug(
            1,
            DebugCommand::GmGauntlet {
                level: 1234,
                fight: 1
            }
        )
        .is_err()
    );
    assert!(
        w.run_debug(1, DebugCommand::GmGauntlet { level, fight: 6 })
            .is_err()
    );
    let out = ok(&mut w, 1, DebugCommand::GmGauntlet { level, fight: 3 });
    assert_eq!(out["class"], format!("{:?}", CLASSES[2]));
    let run = w.gauntlets.iter().find(|r| r.owner == 1).unwrap();
    assert!(run.quest.is_empty() && run.won == 2 && run.order == CLASSES);
    assert!(w.is_arena_zone(w.players[&1].character.zone));
    assert_eq!(json!(w.players[&1].character.quests), quests_before);
    // A second start is refused; opponent multipliers belong to the run.
    assert!(
        w.run_debug(1, DebugCommand::GmGauntlet { level, fight: 1 })
            .is_err()
    );
    ok(
        &mut w,
        1,
        DebugCommand::GmTune {
            key: "opponent_damage".into(),
            value: 0.25,
        },
    );
    let run = w.gauntlets.iter().find(|r| r.owner == 1).unwrap();
    assert_eq!(run.opponent_damage, 0.25);
    assert_eq!(gauntlet::opponent_damage(), 0.5);
    // The hero's own arena run is untouched by another hero's normal run values.
    ok(
        &mut w,
        1,
        DebugCommand::GmTune {
            key: "reset".into(),
            value: 0.,
        },
    );
    assert_eq!(w.gauntlets[0].opponent_damage, gauntlet::opponent_damage());
}
