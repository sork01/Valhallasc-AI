use super::*;

fn coast_map() -> Map {
    Map {
        size: 20,
        objects: vec![],
        grid: Default::default(),
        dock: None,
        shape_floor: vec!["##########          ".into(); 20],
        shape_edge: vec!["          cccccccccc".into(); 20],
        ..Map::default()
    }
}

#[test]
fn fishing_coast_accepts_sea_and_rejects_land_seams_lava_and_blockers() {
    let mut map = coast_map();
    let shore = Point { x: 8., y: 10.5 };
    let face = Point { x: 1., y: 0. };
    let bobber = coast_landing(&map, shore, face, false).expect("open coast cast");
    assert_eq!(bobber, Point { x: 12.5, y: 10.5 });
    assert!(
        coast_landing(&map, shore, face, true).is_none(),
        "a lava line cannot use sea"
    );
    assert!(
        coast_landing(&map, Point { x: 5., ..shore }, face, false).is_none(),
        "far from sea"
    );
    assert!(
        coast_landing(&map, bobber, face, false).is_none(),
        "standing in sea"
    );
    assert!(
        coast_landing(&map, shore, Point { x: -1., y: 0. }, false).is_none(),
        "facing land"
    );
    map.shape_edge = vec!["          AAAAAAAAAA".into(); 20];
    assert!(
        coast_landing(&map, shore, face, false).is_none(),
        "a seam is not sea"
    );
    map.shape_edge = vec!["          llllllllll".into(); 20];
    assert!(
        coast_landing(&map, shore, face, false).is_none(),
        "a cliff is not sea"
    );
    map.shape_edge = vec!["          cccccccccc".into(); 20];
    map.shape_floor = vec!["####################".into(); 20];
    assert!(
        coast_landing(&map, shore, face, false).is_none(),
        "land wins over edge metadata"
    );
    map.shape_floor = vec!["##########          ".into(); 20];
    map.objects.push(Obstacle {
        x: 9.,
        y: 10.5,
        r: 0.,
        width: 0.5,
        depth: 1.,
        surface: Default::default(),
    });
    assert!(
        coast_landing(&map, shore, face, false).is_none(),
        "cannot cast through a wall"
    );
}

#[test]
fn fishing_coast_real_greenmeadow_casts_do_not_move_the_angler() {
    let (mut world, _rx) = super::super::fishing_tests::angler();
    world.players.get_mut(&1).unwrap().character.level = 99;
    world
        .players
        .get_mut(&1)
        .unwrap()
        .character
        .add_item("rod_worldwire_rod", 1);
    let zone = 0;
    {
        let mut witnesses = Vec::new();
        let map = &world.maps[zone];
        for (y, row) in map.shape_floor.iter().enumerate() {
            for (x, cell) in row.bytes().enumerate() {
                if cell == b' ' {
                    continue;
                }
                let shore = Point {
                    x: x as f64 + 0.5,
                    y: y as f64 + 0.5,
                };
                if map.dock.as_ref().is_some_and(|dock| dock.contains(shore)) {
                    continue;
                }
                if witnesses
                    .iter()
                    .any(|(old, _): &(Point, Point)| old.distance(shore) < 20.)
                {
                    continue;
                }
                let mut resolved = shore;
                map.collide(&mut resolved, PLAYER_RADIUS);
                if resolved.distance(shore) > 1e-8 {
                    continue;
                }
                for face in [
                    Point { x: 1., y: 0. },
                    Point { x: -1., y: 0. },
                    Point { x: 0., y: 1. },
                    Point { x: 0., y: -1. },
                ] {
                    if coast_landing(map, shore, face, false).is_some() {
                        witnesses.push((shore, face));
                        break;
                    }
                }
                if witnesses.len() == 6 {
                    break;
                }
            }
            if witnesses.len() == 6 {
                break;
            }
        }
        assert_eq!(
            witnesses.len(),
            6,
            "zone {zone} has multiple real coastal shores"
        );
        for (shore, face) in witnesses {
            let p = world.players.get_mut(&1).unwrap();
            p.character.zone = zone;
            p.character.fishing.proficiency.skill = water_skill_requirement(zone).unwrap();
            p.character.x = shore.x;
            p.character.y = shore.y;
            p.face = face;
            p.fishing = Default::default();
            let before = p.character.point();
            world.fish_press(1, 100., false);
            let line = world.players[&1].fishing.line.expect("ordinary coast cast");
            assert!(line.bobber.distance(before) >= 3. && line.bobber.distance(before) <= 6.);
            assert_eq!(line.habitat, habitat(zone).unwrap());
            assert_eq!(world.players[&1].character.point(), before);
        }
    }
}
