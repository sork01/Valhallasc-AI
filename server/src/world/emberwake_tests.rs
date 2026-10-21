//! Only the new volcanic approach: real collision, portals, catalog and loot.
use super::wyrd_tests::{at, blocked, flood, join, place, reached, world};
use super::*;
const ZONE: usize = 45;

#[test]
fn emberwake_map_gates_and_outdoor_catalog() {
    let mut w = world();
    let m = &w.maps[ZONE];
    assert_eq!(m.name, "Emberwake Caldera");
    assert_eq!(w.weather.view(ZONE, None, 0)["inside"], false);
    let mut door = at(133., 20.);
    m.collide(&mut door, PLAYER_RADIUS);
    assert!(
        door.distance(at(133., 20.)) > 0.1,
        "sealed door has collision"
    );
    assert!(!m.interior && m.players == 0 && m.copies == 0);
    let grid = blocked(m, &[]);
    let seen = flood(m, &grid, at(22., 137.));
    for p in &m.portals {
        assert!(reached(m, &seen, at(p.x, p.y)));
        assert_eq!(p.to, 17);
    }
    for n in &m.npcs {
        assert!(reached(m, &seen, at(n.x, n.y)), "{}", n.id);
    }
    for s in &m.slimes {
        assert!(reached(m, &seen, at(s.x, s.y)), "{}", s.kind);
        assert!((95..=99).contains(&Slime::default_level(&s.kind)));
        assert!(!Slime::fixed_level(&s.kind));
        assert!(!is_boss(&s.kind));
    }
    assert_eq!(m.slimes.iter().filter(|s| is_elite(&s.kind)).count(), 3);
    assert_eq!(m.quests.iter().filter(|q| q.group).count(), 2);
    assert!(m.npcs.iter().any(|n| n.id == "ew_seal"));
    assert!(m.portals.iter().all(|p| p.id != "ew_raid"));
    let mut lava = at(30., 86.);
    m.collide(&mut lava, PLAYER_RADIUS);
    assert!(lava.distance(at(30., 86.)) > 0.1);
    // A bend's hot bank blocks movement while its adjacent cove is floor.
    for (point, impassable) in [(at(104., 82.), true), (at(104., 80.), false)] {
        let mut moved = point;
        m.collide(&mut moved, PLAYER_RADIUS);
        assert_eq!(moved.distance(point) > 0.1, impassable);
    }
    let mut bridge = at(81., 82.);
    m.collide(&mut bridge, PLAYER_RADIUS);
    assert!(
        bridge.distance(at(81., 82.)) < 0.01,
        "the causeway is actual floor"
    );
    for q in &m.quests {
        assert_eq!(q.reward_xp, crate::model::xp_to_level(q.level) / 10);
        assert!(format!("quest:accept:{}", q.id).len() <= 32);
    }
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, 17, at(90., 18.));
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, ZONE);
    assert!(w.players[&1].character.point().distance(at(22., 137.)) < 0.01);
    place(&mut w, 1, ZONE, at(14., 140.));
    w.time += PORTAL_DELAY;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 17);
    assert!(w.players[&1].character.point().distance(at(90., 25.)) < 0.01);
}

#[test]
fn emberwake_kills_pay_materials_and_keep_elite_rules() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.level = 99;
    for kind in [
        "ew_ashback",
        "ew_glasswing",
        "ew_slagjaw",
        "ew_cinderhorn",
        "ew_chainmaw",
        "ew_bellows",
        "ew_crown",
    ] {
        let i = w
            .slimes
            .iter()
            .position(|s| s.zone == ZONE && s.kind == kind)
            .unwrap();
        let point = w.slimes[i].point();
        place(&mut w, 1, ZONE, point);
        w.hit_slime(i, 1, 1e15, false);
        assert!(w.slimes[i].dead);
        assert_eq!(w.slimes[i].respawn, if is_elite(kind) { 600. } else { 22. });
        assert!(
            w.drops
                .iter()
                .any(|d| d.item.as_deref() == Some(format!("{kind}_relic").as_str())),
            "{kind}"
        );
    }
}
