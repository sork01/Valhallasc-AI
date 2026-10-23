//! RAID-PACKS: actual raid spawns, kill rewards and hired-brain measurements.
use super::ttk::*;
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;
use std::collections::BTreeSet;
const ZONE: usize = 46;

#[test]
fn raid_pack_equipment_index_keeps_catalog_selection() {
    for class in CLASSES {
        for piece in ITEMS.iter().filter(|i| i.variant.is_some()) {
            let variant = piece.variant.as_deref().unwrap();
            let scan = ITEMS
                .iter()
                .find(|i| {
                    i.class == Some(class)
                        && i.kind == piece.kind
                        && i.variant.as_deref() == Some(variant)
                })
                .or_else(|| {
                    ITEMS.iter().find(|i| {
                        i.class.is_none()
                            && i.source.as_deref() == Some("orange_pool")
                            && i.kind == piece.kind
                            && i.variant.as_deref() == Some(variant)
                    })
                });
            assert_eq!(
                equipment(class, &piece.kind, variant).map(|i| &i.id),
                scan.map(|i| &i.id)
            );
        }
        assert!(equipment(class, "weapon", "no_such_variant").is_none());
    }
}

#[test]
fn raid_pack_spawns_are_all_dungeon_elites_with_no_side_quests() {
    let w = world();
    let m = &w.maps[ZONE];
    assert!(!m.sealed_template && m.raid);
    let ordinary: Vec<_> = m
        .slimes
        .iter()
        .filter(|s| crate::cathedral::enemy(&s.kind).is_some_and(|e| e.raid_pack))
        .collect();
    assert_eq!(ordinary.len(), 40);
    assert!(m.slimes.len() >= ordinary.len());
    assert!(ordinary.iter().all(|s| is_elite(&s.kind)));
    assert!(ordinary.iter().all(|s| !is_boss(&s.kind)));
    let kinds: BTreeSet<_> = ordinary.iter().map(|s| s.kind.as_str()).collect();
    assert_eq!(kinds.len(), 4);
    let seen = flood(m, &blocked(m, &[]), at(62., 290.));
    for s in &ordinary {
        assert!(reached(m, &seen, at(s.x, s.y)), "{}", s.kind);
        let p = at(s.x, s.y);
        let mut q = p;
        m.collide(&mut q, PLAYER_RADIUS);
        assert!(q.distance(p) < 1e-6, "{} real collision at {p:?}", s.kind);
        assert_eq!(Slime::default_level(&s.kind), 99);
        assert!(item(material(&s.kind)).is_some());
    }
    assert!(Slime::ranged("cf_crawler").is_some());
    assert!(Slime::ranged("cf_caster").is_some());
    assert!(m.quests.is_empty(), "no separate elite quests in the raid");
    let data: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    for p in data["zones"][45]["forgePacks"].as_array().unwrap() {
        let centre = at(p["x"].as_f64().unwrap(), p["y"].as_f64().unwrap());
        assert_eq!(
            ordinary
                .iter()
                .filter(|s| at(s.x, s.y).distance(centre) < 8.)
                .count(),
            4
        );
    }
}

#[test]
fn raid_pack_interim_fixture_has_ten_slots_cloak_and_two_rings() {
    for class in CLASSES {
        let slots = normal_gear_of(class, 99, "raid_interim");
        assert_eq!(slots.len(), 10);
        assert_eq!(
            slots
                .iter()
                .filter(|(_, id)| item(id).unwrap().rarity == "legendary")
                .count(),
            6
        );
        assert!(slots.iter().any(|(s, _)| *s == "accessory2"));
        let mut c = Character::mercenary(class, 99, "Fixture");
        build_character(
            &mut c,
            &Case {
                rarity: "raid_interim",
                ..Case::new(class, 99)
            },
        );
        assert_eq!(c.equipment.len(), 8); // armor and weapon live in Look; eight extra slots
        assert!(c.equipment.contains_key("accessory2"));
        assert!(c.equipment.contains_key("cloak"));
    }
}

#[test]
fn raid_pack_kill_material_no_orange_and_copy_isolation() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    let id = w
        .slimes
        .iter()
        .position(|s| s.zone == ZONE && s.kind == "cf_brute")
        .unwrap();
    let other = w
        .slimes
        .iter()
        .find(|s| s.zone != ZONE && w.maps[s.zone].raid && s.kind == "cf_brute")
        .unwrap()
        .id;
    let point = w.slimes[id].point();
    place(&mut w, 1, ZONE, point);
    w.hit_slime(id, 1, 1e15, false);
    assert!(w.slimes[id].dead && !w.slimes[other].dead);
    assert!(
        w.drops
            .iter()
            .any(|d| d.item.as_deref() == Some("cf_brute_relic"))
    );
    assert!(
        !w.drops
            .iter()
            .filter_map(|d| d.item.as_deref().and_then(item))
            .any(|i| i.rarity == "legendary")
    );
}

#[test]
fn raid_pack_elites_fully_heal_on_evade_and_do_not_respawn_inside() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, ZONE, at(62., 290.));
    w.enter_instance(ZONE);
    for kind in ["cf_brute", "cf_crawler", "cf_caster", "cf_sentry"] {
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == ZONE && s.kind == kind)
            .unwrap();
        let s = &mut w.slimes[id];
        s.hp = s.max_hp * 0.1;
        s.state = "return".into();
        s.x = s.hx;
        s.y = s.hy;
        w.update_slime(id);
        assert_eq!(
            w.slimes[id].hp, w.slimes[id].max_hp,
            "{kind} heals on evade"
        );
        w.hit_slime(id, 1, 1e15, false);
        assert_eq!(w.slimes[id].respawn, 1e9);
        w.update_slime(id);
        w.update_slime(id);
        assert!(w.slimes[id].dead, "{kind} remains dead in the active raid");
    }
}

#[test]
fn raid_pack_purple_pool_is_unique_class_neutral_and_wearable_by_every_class() {
    let mut found = BTreeSet::new();
    for n in 0..3 {
        let piece = raid_pack_piece((n as f64 + 0.5) / 3.).unwrap();
        assert_eq!(piece.source.as_deref(), Some("chained_forge_packs"));
        assert_eq!((piece.rarity.as_str(), piece.required_level), ("epic", 99));
        assert!(piece.class.is_none());
        assert_eq!(piece.art.as_deref(), Some("regearcfpack"));
        found.insert(piece.kind.as_str());
        for class in CLASSES {
            let mut c = Character::mercenary(class, 99, "Loot fixture");
            c.add_item(&piece.id, 1);
            let slot = if piece.kind == "accessory" {
                "accessory1"
            } else {
                &piece.kind
            };
            c.equip_slots(&BTreeMap::from([(slot.into(), piece.id.clone())]))
                .unwrap();
        }
    }
    assert_eq!(found, BTreeSet::from(["pants", "necklace", "accessory"]));
}

#[test]
fn raid_pack_seeded_purple_rate_and_rebirth_kill_path() {
    // Pure seeded rolls, not gameplay farming. The same primitive used at a kill.
    for boost in [1, 5] {
        let mut rng = 20261022u64;
        let total: u32 = (0..100_000)
            .map(|_| {
                copies(RAID_EPIC_DROP_CHANCE, boost, || {
                    rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
                    (rng >> 32) as f64 / 4294967296.
                })
            })
            .sum();
        let rate = total as f64 / 100_000.;
        assert!(
            (rate - 0.03 * f64::from(boost)).abs() < 0.002,
            "boost {boost}: {rate}"
        );
    }
    // One deterministic kill per multiplier, including the maximum live rebirth multiplier.
    // Seed search touches only the PRNG, never kills enemies waiting for loot.
    for boost in [1, 5] {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 99;
        c.rebirth_tiers = [0, 0, 0, 0, boost - 1];
        assert_eq!(c.drop_multiplier(), boost);
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == ZONE && s.kind == "cf_brute")
            .unwrap();
        let p = w.slimes[id].point();
        place(&mut w, 1, ZONE, p);
        let seed = (1..10000u64)
            .find(|seed| {
                let mut r = *seed;
                let mut draw = || {
                    r = r.wrapping_mul(6364136223846793005).wrapping_add(1);
                    (r >> 32) as f64 / 4294967296.
                };
                // Skip the independent bag draw, then force the independent purple success.
                draw() > BAG_DROP_CHANCE * f64::from(boost) && draw() < 0.03
            })
            .unwrap();
        w.rng = seed;
        w.hit_slime(id, 1, 1e15, false);
        let pieces: Vec<_> = w
            .drops
            .iter()
            .filter_map(|d| d.item.as_deref().and_then(item))
            .filter(|i| i.source.as_deref() == Some("chained_forge_packs"))
            .collect();
        assert!(
            !pieces.is_empty(),
            "boost {boost}: independent purple roll reaches actual loot"
        );
        assert!(pieces.iter().all(|i| i.class.is_none()));
        assert!(
            w.drops
                .iter()
                .filter_map(|d| d.item.as_deref().and_then(item))
                .filter(|i| i.rarity == "epic")
                .all(|i| i.source.as_deref() == Some("chained_forge_packs"))
        );
        let relic = w
            .drops
            .iter()
            .find(|d| d.item.as_deref() == Some("cf_brute_relic"))
            .unwrap();
        assert_eq!(relic.quantity, boost);
    }
}

/// Each reported fight starts from the actual authored positions and uses the
/// same contract, skills and consumables as mercenaries in the playable world.
#[test]
#[ignore = "Optional diagnostics: owner deferred raid pack clear-time balance"]
fn raid_pack_measure_encounters() {
    let w = world();
    let map: Value = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
    let fights: Vec<(String, Vec<usize>)> = map["zones"][45]["forgePacks"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| {
            let centre = at(p["x"].as_f64().unwrap(), p["y"].as_f64().unwrap());
            (
                format!("pack{}", p["id"].as_u64().unwrap()),
                w.slimes
                    .iter()
                    .filter(|s| {
                        s.zone == ZONE
                            && crate::cathedral::enemy(&s.kind).is_some_and(|e| e.raid_pack)
                            && s.point().distance(centre) < 8.
                    })
                    .map(|s| s.id)
                    .collect(),
            )
        })
        .collect();
    let selected = std::env::var("RAID_PACK_FIGHTS").unwrap_or_default();
    let seeds = std::env::var("RAID_PACK_SEEDS")
        .ok()
        .and_then(|s| s.parse::<u64>().ok())
        .unwrap_or(1);
    let count = std::env::var("RAID_PACK_COUNT")
        .ok()
        .and_then(|s| s.parse::<usize>().ok())
        .unwrap_or(10);
    let class = match std::env::var("RAID_PACK_CLASS")
        .unwrap_or_default()
        .as_str()
    {
        "" | "warrior" => Class::Warrior,
        "mage" => Class::Mage,
        "assassin" => Class::Assassin,
        "priest" => Class::Priest,
        "hunter" => Class::Hunter,
        other => panic!("unknown class {other}"),
    };
    let mut ran = 0;
    let mut failed = vec![];
    for (name, ids) in fights
        .into_iter()
        .filter(|(n, _)| selected.is_empty() || selected.split(',').any(|s| s == n))
    {
        assert!(!ids.is_empty());
        let mut times = vec![];
        for seed in 1..=seeds {
            ran += 1;
            let case = Case {
                rarity: "raid_interim",
                cap: Some(1200.),
                consumables: true,
                run_to_end: true,
                ..Case::new(class, 99)
            };
            let out = run_raid_hired_party(&case, &ids, seed, count);
            eprintln!(
                "[raid-packs] {name} n={count} seed={seed} won={} time={:.2} falls={} left={:.4} unstuck={} dps={:?}",
                out.killed, out.seconds, out.deaths, out.enemy_left, out.unstuck, out.dps
            );
            times.push(out.seconds);
            if count == 1 && (out.killed || out.deaths == 0) {
                failed.push(format!("{name} n={count} seed{seed}: {out:?}"));
            }
        }
        times.sort_by(f64::total_cmp);
        let median = (times[(times.len() - 1) / 2] + times[times.len() / 2]) / 2.;
        eprintln!(
            "[raid-pack-band] {name} n={count} seeds={seeds} median={median:.2} fastest={:.2} slowest={:.2}",
            times[0],
            times[times.len() - 1]
        );
        // Owner, 2026-10-22: leave packs overpowered; clear-time calibration
        // and a guaranteed ten-fighter win are deferred to the owner's later fix.
    }
    assert!(ran > 0);
    assert!(failed.is_empty(), "{}", failed.join("\n"));
}

#[test]
#[ignore = "RAID-PACKS only: careless basic-attack control"]
fn raid_pack_careless_ten_without_defense_or_healing_lose() {
    let w = world();
    let pack = w
        .slimes
        .iter()
        .filter(|s| s.zone == ZONE && s.point().distance(at(145., 277.)) < 3.)
        .map(|s| s.id)
        .collect::<Vec<_>>();
    let case = Case {
        rarity: "raid_interim",
        rotation: Rotation::BasicOnly,
        cap: Some(720.),
        consumables: false,
        run_to_end: true,
        ..Case::new(Class::Warrior, 99)
    };
    let members = [CLASSES, CLASSES].concat();
    let out = run_party_pack_once(&case, &members, &pack, 1);
    eprintln!(
        "[raid-careless] won={} time={:.2} falls={} left={:.4}",
        out.killed, out.seconds, out.deaths, out.enemy_left
    );
    assert!(
        !out.killed && out.deaths == 10,
        "careless control must lose: {out:?}"
    );
}
