//! Admission quests use the real quest ledger and portal path, without combat grinding.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;

const GATES: [(usize, usize, &str, &str); 4] = [
    (6, 41, "wyrd_nornroot", "entry_norn"),
    (17, 18, "asterion_moonwell_stairs", "entry_moon"),
    (25, 34, "lapis_astrolabe_gate", "entry_astro"),
    (28, 39, "year_solstice_descent", "entry_solstice"),
];

fn talk(w: &mut World, npc: &str, offer: Option<&str>) {
    let (zone, n) = w
        .maps
        .iter()
        .enumerate()
        .find_map(|(z, m)| m.npcs.iter().find(|n| n.id == npc).map(|n| (z, n.clone())))
        .unwrap();
    place(w, 1, zone, n.position_at(w.time));
    w.time += 1.;
    w.interact(1, npc, offer);
}

fn enter(w: &mut World, parent: usize, door: &str) {
    let p = w.maps[parent]
        .portals
        .iter()
        .find(|p| p.id == door)
        .unwrap()
        .clone();
    place(w, 1, parent, at(p.x, p.y));
    w.time += 2.;
    w.use_portal(1);
}

#[test]
fn dungeon_admission_four_new_exterior_quests_preserve_existing_keys_and_reachable_sites() {
    let w = world();
    let dungeons: Vec<_> = w
        .maps
        .iter()
        .take(47)
        .filter(|m| m.copies > 0 && !m.raid)
        .collect();
    assert_eq!(dungeons.len(), 20);
    let gated: Vec<_> = w
        .maps
        .iter()
        .take(47)
        .flat_map(|m| &m.portals)
        .filter(|p| w.maps[p.to].copies > 0 && p.needs_quest.is_some())
        .collect();
    assert_eq!(gated.len(), 6, "four additions plus Foundry and Forge");
    assert!(
        gated
            .iter()
            .any(|p| p.needs_quest.as_deref() == Some("null_keys"))
    );
    assert!(
        gated
            .iter()
            .any(|p| p.needs_quest.as_deref() == Some("raid_key"))
    );
    for (parent, target, door, id) in GATES {
        let map = &w.maps[parent];
        let q = map.quests.iter().find(|q| q.id == id).unwrap();
        let p = map.portals.iter().find(|p| p.id == door).unwrap();
        assert_eq!(p.needs_quest.as_deref(), Some(id));
        assert_eq!(p.to, target);
        assert!(q.requires.is_none() && !q.repeatable && q.auto_level.is_none());
        assert_eq!(q.min_level, w.maps[target].min_level);
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10);
        assert!(format!("quest:accept:{id}").len() <= 32);
        let seen = flood(map, &blocked(map, &[]), map.spawn);
        for site in map.places.iter().filter(|s| s.id.starts_with("admit_")) {
            // The prop has a small solid foot; enter its surrounding objective circle.
            let point = at(site.x + 1.1, site.y);
            assert!(reached(map, &seen, point), "{} unreachable", site.id);
            let mut actual = point;
            map.collide(&mut actual, PLAYER_RADIUS);
            assert!(actual.distance(point) < 0.01, "{} blocked", site.id);
            assert!(map.objects.iter().any(|o| o.x == site.x && o.y == site.y));
            assert!(
                map.portals
                    .iter()
                    .all(|p| point.distance(at(p.x, p.y)) > p.r + site.r)
            );
        }
    }
}

#[test]
fn dungeon_admission_missing_active_and_ready_quests_cannot_open_any_new_door() {
    let mut w = world();
    if std::env::var_os("MUTATE_DUNGEON_ADMISSION").is_some() {
        for (parent, _, door, _) in GATES {
            w.maps[parent]
                .portals
                .iter_mut()
                .find(|p| p.id == door)
                .unwrap()
                .needs_quest = None;
        }
    }
    let mut rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    for (parent, target, door, id) in GATES {
        let q = w.maps[parent]
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap()
            .clone();
        for stage in 0..3 {
            if stage == 1 {
                assert!(
                    quest_action(&mut w.players.get_mut(&1).unwrap().character, &q, "accept").2
                );
            } else if stage == 2 {
                let progress = w
                    .players
                    .get_mut(&1)
                    .unwrap()
                    .character
                    .quests
                    .iter_mut()
                    .find(|p| p.id == id)
                    .unwrap();
                progress.counts = q.objectives.iter().map(|o| o.count).collect();
            }
            enter(&mut w, parent, door);
            assert_eq!(
                w.players[&1].character.zone, parent,
                "{id} stage {stage} bypassed"
            );
            assert!(
                std::iter::from_fn(|| rx.try_recv().ok()).any(|v| v["type"] == "error"
                    && v["text"].as_str().is_some_and(|t| t.contains(&q.title)))
            );
        }
        let p = w
            .players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .iter_mut()
            .find(|p| p.id == id)
            .unwrap();
        p.claimed = true;
        p.completions = 1;
        enter(&mut w, parent, door);
        assert_eq!(w.public_zone(w.players[&1].character.zone), target);
    }
}

#[test]
fn dungeon_admission_level_bell_expiry_and_vigil_pause_and_death() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    for (parent, _, _, id) in GATES {
        let q = w.maps[parent]
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap()
            .clone();
        w.players.get_mut(&1).unwrap().character.level = q.min_level - 1;
        talk(&mut w, &q.npc, Some(&format!("quest:accept:{id}")));
        assert!(!w.players[&1].character.quests.iter().any(|p| p.id == id));
    }
    w.players.get_mut(&1).unwrap().character.level = 99;
    talk(
        &mut w,
        "asterion_bellkeeper",
        Some("quest:accept:entry_moon"),
    );
    place(&mut w, 1, 17, at(93.1, 68.));
    w.update_chimes();
    assert_eq!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "entry_moon")
            .unwrap()
            .counts,
        [1]
    );
    place(&mut w, 1, 17, at(94., 72.));
    for _ in 0..501 {
        w.update_chimes();
    }
    assert_eq!(
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "entry_moon")
            .unwrap()
            .counts,
        [0]
    );
    talk(&mut w, "yr_wi_lead", Some("quest:accept:entry_solstice"));
    place(&mut w, 1, 28, at(58.1, 153.));
    for _ in 0..40 {
        w.update_holds();
    }
    let progress = |w: &World| {
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == "entry_solstice")
            .unwrap()
            .counts[2]
    };
    assert_eq!(progress(&w), 2);
    place(&mut w, 1, 28, at(62., 153.));
    for _ in 0..40 {
        w.update_holds();
    }
    assert_eq!(progress(&w), 2, "walking away pauses the vigil");
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    w.update_holds();
    assert_eq!(progress(&w), 0, "falling resets unfinished vigil progress");
}

#[test]
fn dungeon_admission_real_objectives_claim_save_and_reentry() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    for (parent, target, door, id) in GATES {
        let q = w.maps[parent]
            .quests
            .iter()
            .find(|q| q.id == id)
            .unwrap()
            .clone();
        talk(&mut w, &q.npc, Some(&format!("quest:accept:{id}")));
        assert!(w.players[&1].character.quests.iter().any(|p| p.id == id));
        for objective in &q.objectives {
            match objective.kind.as_str() {
                "talk" => talk(&mut w, &objective.target, None),
                "bring" => w
                    .players
                    .get_mut(&1)
                    .unwrap()
                    .character
                    .add_item(&objective.target, objective.count),
                // Kill credit is injected through the authoritative quest event; no balance fight is needed.
                "kill" => {
                    for _ in 0..objective.count {
                        quest_progress(
                            &mut w.players.get_mut(&1).unwrap().character,
                            &w.maps[parent].quests,
                            "kill",
                            &objective.target,
                        );
                    }
                }
                "visit" | "hold" | "chime" => {
                    let sites: Vec<_> = w.maps[parent]
                        .places
                        .iter()
                        .filter(|p| {
                            if objective.kind == "chime" {
                                p.chain == objective.target
                            } else {
                                p.id == objective.target
                            }
                        })
                        .cloned()
                        .collect();
                    for site in sites {
                        place(&mut w, 1, parent, at(site.x + 1.1, site.y));
                        match objective.kind.as_str() {
                            "visit" => {
                                sync_visits(&mut w.players.get_mut(&1).unwrap().character, &w.maps);
                            }
                            "chime" => w.update_chimes(),
                            _ => {
                                for _ in 0..(objective.count as f64 / TICK).round() as u32 {
                                    w.update_holds();
                                }
                            }
                        }
                    }
                }
                other => panic!("untested objective {other}"),
            }
        }
        talk(&mut w, &q.npc, Some(&format!("quest:claim:{id}")));
        let c = &w.players[&1].character;
        assert!(
            c.quests
                .iter()
                .any(|p| p.id == id && p.claimed && p.completions == 1),
            "{id} did not claim"
        );
        if id == "entry_astro" {
            assert_eq!(c.quantity("scorpion_glass"), 0);
        }
        let saved: Character = serde_json::from_str(&serde_json::to_string(c).unwrap()).unwrap();
        w.players.get_mut(&1).unwrap().character = saved;
        enter(&mut w, parent, door);
        assert_eq!(w.public_zone(w.players[&1].character.zone), target);
        let exit = w.maps[w.players[&1].character.zone]
            .portals
            .iter()
            .find(|p| !p.after_clear)
            .unwrap()
            .clone();
        let zone = w.players[&1].character.zone;
        place(&mut w, 1, zone, at(exit.x, exit.y));
        w.time += 2.;
        w.use_portal(1);
        assert_eq!(w.players[&1].character.zone, parent, "return stays open");
        enter(&mut w, parent, door);
        assert_eq!(
            w.public_zone(w.players[&1].character.zone),
            target,
            "unlock survives reentry"
        );
        while rx.try_recv().is_ok() {}
    }
}
