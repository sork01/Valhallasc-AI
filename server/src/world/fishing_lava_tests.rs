use super::*;

fn pool(w: &mut World, zone: usize, kind: &str, rod: &str) {
    w.maps[zone].objects =
        vec![serde_json::from_value(json!({"kind":kind,"x":53.,"y":50.,"r":2.})).unwrap()];
    w.maps[zone].grid = Default::default();
    w.maps[zone].fishing_spots.clear();
    w.rich_fishing.clear();
    let p = w.players.get_mut(&1).unwrap();
    p.character.zone = zone;
    p.character.x = 50.;
    p.character.y = 50.;
    p.character.level = 99;
    p.character.inventory.clear();
    p.character.fishing = Default::default();
    p.character.add_item(rod, 1);
    p.face = Point { x: 1., y: 0. };
    p.fishing = Session::default();
}

#[test]
fn fishing_lava_cast_requires_the_whole_hero_on_clear_shore() {
    let (mut w, _) = super::super::fishing_tests::angler();
    for (zone, kind) in [(1, "lava"), (45, "ew_lava")] {
        pool(&mut w, zone, kind, "rod_magma_reel");
        // The centre is on dry land but half the hero's feet overlap the lava.
        // The old centre-only test accepted this cast. Use the real collision radius.
        for x in [51. - PLAYER_RADIUS / 2., 53.] {
            w.players.get_mut(&1).unwrap().character.x = x;
            let from = w.players[&1].character.point();
            let mut corrected = from;
            w.maps[zone].collide(&mut corrected, PLAYER_RADIUS);
            assert!(corrected.distance(from) > 0.01);
            assert!(w.fishing_line(1, 20.).is_err(), "zone {zone}, x {x}");
            assert_eq!(w.players[&1].character.point().distance(from), 0.);
        }
        // A rock on the shore also makes the origin invalid; casting must not push us out.
        w.players.get_mut(&1).unwrap().character.x = 50.;
        w.maps[zone]
            .objects
            .push(serde_json::from_value(json!({"kind":"rock","x":50.,"y":50.,"r":0.5})).unwrap());
        w.maps[zone].grid = Default::default();
        assert!(w.fishing_line(1, 20.).is_err(), "blocked shore in {zone}");
    }
}

#[test]
fn fishing_lava_rods_surfaces_zone_and_level_are_enforced() {
    let (mut w, _) = super::super::fishing_tests::angler();
    for (zone, surface) in [(1, "lava"), (45, "ew_lava")] {
        pool(&mut w, zone, surface, "rod_worldwire_rod");
        assert!(w.fishing_line(1, 20.).is_err(), "water rod in lava {zone}");
        let p = w.players.get_mut(&1).unwrap();
        p.character.add_item("rod_emberline_rod", 1);
        p.character.level = 4;
        assert!(w.fishing_line(1, 20.).is_err(), "underlevel Emberline");
        w.players.get_mut(&1).unwrap().character.level = 5;
        assert_eq!(w.fishing_line(1, 20.).is_ok(), zone == 1);
        let p = w.players.get_mut(&1).unwrap();
        p.character.add_item("rod_magma_reel", 1);
        p.character.level = 44;
        assert_eq!(w.fishing_line(1, 20.).is_ok(), zone == 1);
        w.players.get_mut(&1).unwrap().character.level = 45;
        assert_eq!(w.fishing_line(1, 20.).unwrap().tier, 2);
        w.players.get_mut(&1).unwrap().face.x = -1.;
        assert!(w.fishing_line(1, 20.).is_err(), "facing away");
        w.players.get_mut(&1).unwrap().face.x = 1.;
        w.maps[zone].objects[0].surface = FishingSurface::Water;
        w.maps[zone].grid = Default::default();
        assert!(
            w.fishing_line(1, 20.).is_err(),
            "lava zone water is not lava"
        );
    }
    for rod in ["rod_emberline_rod", "rod_magma_reel"] {
        pool(&mut w, 0, "water", rod);
        assert!(w.fishing_line(1, 20.).is_err(), "lava rod in water: {rod}");
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item("rod_twig_rod", 1);
        assert_eq!(w.fishing_line(1, 20.).unwrap().tier, 1);
        w.maps[0].objects[0].surface = FishingSurface::Lava;
        w.maps[0].grid = Default::default();
        assert!(
            w.fishing_line(1, 20.).is_err(),
            "water zone lava is not water"
        );
    }
}

#[test]
fn fishing_lava_all_real_shores_cast_without_moving_or_crossing_lava() {
    let (mut w, _) = super::super::fishing_tests::angler();
    let points: Value =
        serde_json::from_str(include_str!("../../../world/fishing-spots.txt")).unwrap();
    for zone in [1, 45] {
        let candidates: Vec<_> = points
            .as_array()
            .unwrap()
            .iter()
            .filter(|p| p["zone"] == zone)
            .collect();
        assert!(!candidates.is_empty(), "zone {zone}: no lava shores");
        for point in candidates {
            let from: Point = serde_json::from_value(point["shore"].clone()).unwrap();
            let face: Point = serde_json::from_value(point["facing"].clone()).unwrap();
            let p = w.players.get_mut(&1).unwrap();
            p.character.zone = zone;
            p.character.level = if zone == 1 { 5 } else { 45 };
            p.character.inventory.clear();
            p.character.add_item(
                if zone == 1 {
                    "rod_emberline_rod"
                } else {
                    "rod_magma_reel"
                },
                1,
            );
            p.character.x = from.x;
            p.character.y = from.y;
            p.face = face;
            p.fishing = Session::default();
            let hp = p.character.hp;
            w.fish_press(1, 20.);
            let p = &w.players[&1];
            let line = p
                .fishing
                .line
                .unwrap_or_else(|| panic!("{}: cast rejected", point["id"]));
            assert_eq!(line.view()["lava"], true);
            let expected: Point = serde_json::from_value(point.clone()).unwrap();
            assert!(line.bobber.distance(expected) < 1e-8, "{}", point["id"]);
            assert_eq!(p.character.point().distance(from), 0.);
            assert_eq!(p.character.hp, hp);
            let mut walk = from;
            w.maps[zone].walk(&mut walk, face, 6., PLAYER_RADIUS);
            assert!(walk.distance(line.bobber) > PLAYER_RADIUS);
            // Overlapping pools use an iterative collision solver (0.001-tile tolerance).
            assert!(
                w.maps[zone]
                    .objects
                    .iter()
                    .filter(|o| area_radius(o, true).is_some())
                    .all(|o| walk.distance(Point { x: o.x, y: o.y }) >= o.r + PLAYER_RADIUS - 1e-3),
                "{}: walking entered lava",
                point["id"]
            );
        }
    }
}

#[test]
fn fishing_lava_catches_use_local_species_junk_tiers_and_legendaries() {
    let (mut w, mut rx) = super::super::fishing_tests::angler();
    // Fixed RNG draws exercise each band directly, with no repeated fishing/grinding.
    for (zone, kind, rod, legendary) in [
        (1, "lava", "rod_emberline_rod", "fish_phoenix_koi"),
        (45, "ew_lava", "rod_magma_reel", "fish_sunfire_ray"),
    ] {
        pool(&mut w, zone, kind, rod);
        for (seed, expected) in [
            (0, "fishing_cooled_slag"),
            (3, "fishing_charred_branch"),
            (2, "fish_ash_barb"),
            (1434, legendary),
        ] {
            let time = 20. + seed as f64 * 20.;
            let p = w.players.get_mut(&1).unwrap();
            p.fishing = Session::default();
            p.character.rebirth_tiers = [0, 0, 0, 0, 2];
            let from = p.character.point();
            let hp = p.character.hp;
            w.fish_press(1, time);
            let line = w.players[&1].fishing.line.unwrap();
            w.rng = seed;
            w.fish_press(1, line.deadline());
            let catch = std::iter::from_fn(|| rx.try_recv().ok())
                .find(|v| v["kind"] == "fish_catch")
                .unwrap();
            assert_eq!(catch["item"], expected, "zone {zone}, seed {seed}");
            let c = &w.players[&1].character;
            assert_eq!(c.point().distance(from), 0.);
            assert_eq!(c.hp, hp);
            assert_eq!(
                c.quantity(expected),
                catch["quantity"].as_u64().unwrap() as u32
            );
            assert_eq!(catch["quantity"], c.drop_multiplier());
            if let Some(species) = FISH.iter().find(|s| s.item == expected) {
                let kg = catch["kg"].as_u64().unwrap() as u32;
                assert!((species.kg[0]..=species.kg[1]).contains(&kg));
                assert_eq!(c.fishing.species[expected].count, 1);
                if expected == legendary {
                    assert_eq!(catch["rarity"], "legendary");
                    assert_eq!(c.fishing.legendary, 1);
                }
            } else {
                assert!(catch.get("kg").is_none());
                assert!(!c.fishing.species.contains_key(expected));
            }
        }
        // Emberline cannot roll the tier-two rare even when the rarity draw is high.
        w.players.get_mut(&1).unwrap().fishing = Session::default();
        let line = w.fishing_line(1, 100.).unwrap();
        w.rng = 53;
        w.land_fish(1, line, 110.);
        let catch = std::iter::from_fn(|| rx.try_recv().ok())
            .find(|v| v["kind"] == "fish_catch")
            .unwrap();
        assert_eq!(catch["rarity"] == "rare", zone == 45);
        assert_eq!(catch["item"] == "fish_obsidian_gar", zone == 45);
        assert!(
            !w.players[&1]
                .character
                .fishing
                .species
                .contains_key(if zone == 1 {
                    "fish_sunfire_ray"
                } else {
                    "fish_phoenix_koi"
                })
        );
    }
}

#[test]
fn fishing_lava_active_spots_spend_one_fish_and_damage_cancels() {
    let (mut w, _) = super::super::fishing_tests::angler();
    for (zone, kind) in [(1, "lava"), (45, "ew_lava")] {
        pool(&mut w, zone, kind, "rod_magma_reel");
        let line = w.fishing_line(1, 20.).unwrap();
        w.rich_fishing.insert(
            zone,
            vec![RichSpot {
                point: line.bobber,
                remaining: 5,
                reserve: None,
            }],
        );
        w.players.get_mut(&1).unwrap().character.rebirth_tiers = [0, 0, 0, 0, 2];
        w.fish_press(1, 20.);
        let line = w.players[&1].fishing.line.unwrap();
        assert!(line.rich.is_some());
        w.rng = 0;
        w.fish_press(1, line.deadline());
        assert_eq!(w.rich_fishing[&zone][0].remaining, 5, "junk spends no fish");
        w.fish_press(1, 50.);
        let line = w.players[&1].fishing.line.unwrap();
        w.rng = 2;
        w.fish_press(1, line.deadline());
        assert_eq!(
            w.rich_fishing[&zone][0].remaining, 4,
            "rebirth spends one fish"
        );
        w.fish_press(1, 80.);
        let line = w.players[&1].fishing.line.unwrap();
        let total = w.players[&1].character.fishing.total;
        let inventory = serde_json::to_value(&w.players[&1].character.inventory).unwrap();
        w.rng = 2; // An uncancelled line would award a real fish, never a log-free junk roll.
        w.players.get_mut(&1).unwrap().last_hurt += 1.;
        w.fish_press(1, line.deadline());
        assert!(w.players[&1].fishing.line.is_none());
        assert_eq!(w.players[&1].character.fishing.total, total);
        assert_eq!(
            serde_json::to_value(&w.players[&1].character.inventory).unwrap(),
            inventory
        );
        assert_eq!(w.rich_fishing[&zone][0].remaining, 4);
    }
}
