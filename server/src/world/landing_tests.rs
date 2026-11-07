use super::*;

fn world() -> (World, mpsc::Receiver<Value>) {
    let mut w = World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
    let (tx, rx) = mpsc::channel(4096);
    let look = Look {
        name: "Newcomer".into(),
        ..Look::default()
    };
    w.join(1, None, Some(look), tx).unwrap();
    (w, rx)
}
fn holds(w: &World, id: &str) -> usize {
    w.players[&1]
        .character
        .quests
        .iter()
        .filter(|q| q.id == id)
        .count()
}
fn walk_to(w: &mut World, x: f64, y: f64) {
    let c = &mut w.players.get_mut(&1).unwrap().character;
    (c.x, c.y) = (x, y);
    w.step();
}

#[test]
fn landing_a_new_hero_starts_on_the_dock_beside_the_ship() {
    let (w, _rx) = world();
    let dock = w.maps[0].dock.clone().expect("Greenmeadow has a dock");
    let c = &w.players[&1].character;
    assert_eq!(c.zone, 0);
    assert!(dock.contains(c.point()), "starts at {:?}", c.point());
    assert!(c.point().distance(dock.start) < 0.5);
    assert!(c.landing);
    // The pier stands out over the water: its far end is past the old shoreline, and walkable.
    let mut end = Point {
        x: (dock.x0 + dock.x1) / 2.,
        y: dock.y1 - 0.6,
    };
    let before = end;
    w.maps[0].collide(&mut end, PLAYER_RADIUS);
    assert!(end.distance(before) < 0.01, "the pier end is blocked");
    // ...and its sides are not: a hero cannot step off the pier into the sea.
    let mut beside = Point {
        x: dock.x1 + 0.7,
        y: dock.start.y,
    };
    let before = beside;
    w.maps[0].collide(&mut beside, PLAYER_RADIUS);
    assert!(
        beside.distance(before) > 0.3,
        "the sea beside the pier is walkable"
    );
    // The death rally and adventurers still use the old spawn by Alderhaven, far from the dock.
    assert!(w.maps[0].spawn.distance(dock.start) > 50.);
}

#[test]
fn landing_quest_finds_the_hero_once_when_they_step_off_the_dock() {
    let (mut w, _rx) = world();
    let dock = w.maps[0].dock.clone().unwrap();
    let id = dock.quest.clone();
    // Walking about on the pier gives nothing.
    walk_to(&mut w, dock.start.x, dock.y0 + 0.5);
    w.step();
    assert_eq!(holds(&w, &id), 0);
    assert!(w.players[&1].character.landing);
    // One step onto the beach: the quest arrives.
    walk_to(&mut w, dock.start.x - 4., dock.y0 - 1.);
    assert_eq!(holds(&w, &id), 1);
    assert!(!w.players[&1].character.landing);
    // Back on the pier and off again: still once.
    walk_to(&mut w, dock.start.x, dock.start.y);
    walk_to(&mut w, dock.start.x - 4., dock.y0 - 1.);
    assert_eq!(holds(&w, &id), 1);
    // It sends the hero to Wren, who gives the first quests.
    let q = w.maps[0].quests.iter().find(|q| q.id == id).unwrap();
    assert_eq!(q.npc, "guide");
    assert!(q.objectives.iter().all(|o| o.target == "guide"));
    assert!(
        w.maps[0]
            .quests
            .iter()
            .any(|q| q.npc == "guide" && q.id == "welcome")
    );
}

#[test]
fn landing_quest_never_finds_heroes_made_before_the_dock() {
    let (mut w, _rx) = world();
    let id = w.maps[0].dock.clone().unwrap().quest;
    // An old save has no `landing` flag (serde default false): wherever it stands, at any level, nothing arrives.
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.landing = false;
    c.level = 5;
    walk_to(&mut w, 250., 190.);
    walk_to(&mut w, 200., 270.);
    assert_eq!(holds(&w, &id), 0);
    let mut v = serde_json::to_value(&w.players[&1].character).unwrap();
    v.as_object_mut().unwrap().remove("landing");
    let old: Character = serde_json::from_value(v).unwrap();
    assert!(!old.landing);
}

#[test]
fn landing_quest_cannot_be_taken_from_wren_by_anyone() {
    let (mut w, _rx) = world();
    let id = w.maps[0].dock.clone().unwrap().quest;
    let q = w.maps[0]
        .quests
        .iter()
        .find(|q| q.id == id)
        .unwrap()
        .clone();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.landing = false;
    let (_, _, ok) = quest_action(c, &q, "accept");
    assert!(!ok, "a non-holder accepted the landing quest");
    assert_eq!(holds(&w, &id), 0);
}

#[test]
fn landing_quest_is_handed_in_to_wren() {
    let (mut w, _rx) = world();
    let dock = w.maps[0].dock.clone().unwrap();
    walk_to(&mut w, dock.start.x - 4., dock.y0 - 1.);
    let wren = w.maps[0]
        .npcs
        .iter()
        .find(|n| n.id == "guide")
        .unwrap()
        .position_at(w.time);
    walk_to(&mut w, wren.x, wren.y);
    let gold = w.players[&1].character.gold;
    w.players.get_mut(&1).unwrap().service_at = -10.;
    w.interact(1, "guide", None);
    w.players.get_mut(&1).unwrap().service_at = -10.;
    w.interact(1, "guide", Some(&format!("quest:claim:{}", dock.quest)));
    let c = &w.players[&1].character;
    let p = c.quests.iter().find(|q| q.id == dock.quest).unwrap();
    assert!(p.claimed, "not claimed: {:?}", p.counts);
    assert!(c.gold > gold);
}

#[test]
fn landing_quest_abandoned_and_restored_from_the_journal_is_held_again() {
    let (mut w, _rx) = world();
    let dock = w.maps[0].dock.clone().unwrap();
    walk_to(&mut w, dock.start.x - 4., dock.y0 - 1.);
    assert_eq!(holds(&w, &dock.quest), 1);
    w.message(
        1,
        ClientMessage::QuestAbandon {
            id: dock.quest.clone(),
        },
    );
    assert_eq!(holds(&w, &dock.quest), 0);
    w.step();
    assert_eq!(
        holds(&w, &dock.quest),
        0,
        "an abandoned landing quest came back by itself"
    );
    w.message(
        1,
        ClientMessage::QuestRestore {
            id: dock.quest.clone(),
        },
    );
    w.step();
    assert_eq!(holds(&w, &dock.quest), 1, "restoring did not bring it back");
    assert!(
        !w.players[&1]
            .character
            .abandoned_quests
            .contains(&dock.quest)
    );
}
