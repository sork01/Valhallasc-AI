//! `CUTSCENE-SERVER` (`world/cutscene.rs`): each crossing cutscene plays once per hero, only on a real crossing, and the hero is safe while it plays.
use super::cutscene::{Env, KINDS, scenes_for};
use super::wyrd_tests::{at, calm, drain, join, place, world};
use super::*;

const LAND: usize = 6; // the Wyrdwood
const BIFROST: usize = 7;
const DEEP: usize = 8;

/// The scene packets and announce texts a hero was sent since the last call.
fn heard(rx: &mut mpsc::Receiver<Value>) -> (Vec<Vec<String>>, Vec<String>) {
    let (mut scenes, mut said) = (vec![], vec![]);
    for m in drain(rx) {
        match m["type"].as_str() {
            Some("cutscene") => scenes.push(
                m["scenes"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|s| s.as_str().unwrap().to_string())
                    .collect(),
            ),
            Some("announce") => said.push(m["text"].as_str().unwrap().to_string()),
            _ => {}
        }
    }
    (scenes, said)
}

/// Stand the hero in `zone` having just walked through a gate, then run the tick.
fn cross(w: &mut World, to: usize) {
    place(w, 1, to, at(20., 20.));
    w.players.get_mut(&1).unwrap().portal_at = w.time;
    w.update_lead_shoes();
}
fn settle(w: &mut World, zone: usize) {
    place(w, 1, zone, at(20., 20.));
    w.update_lead_shoes();
}

#[test]
fn the_zones_are_the_right_kind_of_place() {
    let w = world();
    assert_eq!(Env::of(&w.maps[LAND]), Env::Land);
    assert_eq!(Env::of(&w.maps[BIFROST]), Env::Sky);
    assert_eq!(Env::of(&w.maps[DEEP]), Env::Sea);
    assert_eq!(Env::of(&w.maps[9]), Env::Sea);
    assert_eq!(
        Env::of(&w.maps[18]),
        Env::Sea,
        "the Moonwell shoes the hero, so it dives"
    );
    assert_eq!(Env::of(&w.maps[0]), Env::Land);
}

#[test]
fn the_scenes_of_each_crossing() {
    use Env::*;
    assert_eq!(scenes_for(Land, Sky), ["sky_up"]);
    assert_eq!(scenes_for(Sky, Land), ["sky_down"]);
    assert_eq!(scenes_for(Land, Sea), ["dive"]);
    assert_eq!(scenes_for(Sea, Land), ["surface"]);
    assert_eq!(scenes_for(Sky, Sea), ["sky_down", "dive"]);
    assert_eq!(scenes_for(Sea, Sky), ["surface", "sky_up"]);
    assert!(scenes_for(Sea, Sea).is_empty() && scenes_for(Land, Land).is_empty());
    assert_eq!(KINDS, ["sky_up", "sky_down", "dive", "surface"]);
}

#[test]
fn a_first_crossing_plays_once_and_the_shoes_announce_is_left_to_the_scene() {
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    settle(&mut w, LAND);
    drain(&mut rx);

    cross(&mut w, DEEP);
    let (scenes, said) = heard(&mut rx);
    assert_eq!(scenes, [["dive"]], "the first dive plays its scene");
    assert!(
        said.is_empty(),
        "the scene's caption says 'Equipping lead shoes' itself: {said:?}"
    );
    assert!(w.players[&1].shoed);
    assert!(
        w.players[&1]
            .character
            .cutscenes
            .contains(&"dive".to_string())
    );
    assert!(w.players[&1].cutscene_until > w.time + SCENE_ONE - 0.01);

    cross(&mut w, LAND);
    let (scenes, said) = heard(&mut rx);
    assert_eq!(scenes, [["surface"]]);
    assert!(said.is_empty());

    // The second time round nothing plays, and the plain announces come back.
    cross(&mut w, DEEP);
    let (scenes, said) = heard(&mut rx);
    assert!(scenes.is_empty());
    assert_eq!(said, ["Equipping lead shoes"]);
    cross(&mut w, LAND);
    let (scenes, said) = heard(&mut rx);
    assert!(scenes.is_empty());
    assert_eq!(said, ["Removing lead shoes"]);
}
const SCENE_ONE: f64 = super::cutscene::SCENE_SECONDS;

#[test]
fn the_updraft_plays_up_and_down_once_each() {
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    settle(&mut w, LAND);
    drain(&mut rx);
    cross(&mut w, BIFROST);
    assert_eq!(heard(&mut rx).0, [["sky_up"]]);
    cross(&mut w, LAND);
    assert_eq!(heard(&mut rx).0, [["sky_down"]]);
    cross(&mut w, BIFROST);
    cross(&mut w, LAND);
    assert!(heard(&mut rx).0.is_empty(), "both are seen now");
}

#[test]
fn bifrost_into_the_sea_falls_then_dives_and_sets_both_flags() {
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    settle(&mut w, BIFROST);
    drain(&mut rx);
    cross(&mut w, DEEP);
    assert_eq!(heard(&mut rx).0, [["sky_down", "dive"]]);
    let c = &w.players[&1].character;
    assert!(
        c.cutscenes.contains(&"sky_down".to_string()) && c.cutscenes.contains(&"dive".to_string())
    );
    assert!(
        w.players[&1].cutscene_until > w.time + 2. * SCENE_ONE - 0.01,
        "the grace covers two scenes"
    );
    // The sea back into Bifrost surfaces then rides the updraft, each only if unseen.
    cross(&mut w, BIFROST);
    assert_eq!(heard(&mut rx).0, [["surface", "sky_up"]]);
    // With the dive already seen, Bifrost into the sea plays only the fall that is still unseen.
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    w.players.get_mut(&1).unwrap().character.cutscenes = vec!["dive".into()];
    settle(&mut w, BIFROST);
    drain(&mut rx);
    cross(&mut w, DEEP);
    let (scenes, said) = heard(&mut rx);
    assert_eq!(scenes, [["sky_down"]]);
    assert_eq!(
        said,
        ["Equipping lead shoes"],
        "no dive scene, so the shoes are announced as plain text"
    );
}

#[test]
fn logging_in_inside_a_scene_zone_or_a_landing_that_is_no_crossing_plays_nothing() {
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    // Login: the first tick only learns where the hero is.
    place(&mut w, 1, DEEP, at(20., 20.));
    w.update_lead_shoes();
    let (scenes, said) = heard(&mut rx);
    assert!(scenes.is_empty());
    assert_eq!(said, ["Equipping lead shoes"], "the shoes still go on");
    assert!(w.players[&1].character.cutscenes.is_empty());
    // A Spark landing, a respawn or a teleport changes the zone without a gate: no scene, and the flag stays unset.
    settle(&mut w, LAND);
    settle(&mut w, BIFROST);
    settle(&mut w, DEEP);
    assert!(heard(&mut rx).0.is_empty());
    assert!(w.players[&1].character.cutscenes.is_empty());
}

#[test]
fn mercenaries_and_ambient_adventurers_get_nothing() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    let mut rx2 = join(&mut w, 2, Class::Mage);
    let owner = w.players[&1].character.id.clone();
    w.players.get_mut(&2).unwrap().merc = Some(owner);
    place(&mut w, 2, LAND, at(20., 20.));
    w.update_lead_shoes();
    place(&mut w, 2, DEEP, at(20., 20.));
    w.players.get_mut(&2).unwrap().portal_at = w.time;
    w.update_lead_shoes();
    assert!(heard(&mut rx2).0.is_empty());
    assert!(w.players[&2].character.cutscenes.is_empty());
    assert!(w.players[&2].env.is_none());
}

#[test]
fn a_test_server_plays_no_cutscene_until_a_test_asks_for_it() {
    let mut w = world();
    calm(&mut w);
    w.cutscene_opt_in = true; // what VALHALLA_TEST_COMMANDS=1 does in main.rs
    let mut rx = join(&mut w, 1, Class::Warrior);
    settle(&mut w, LAND);
    drain(&mut rx);
    cross(&mut w, BIFROST);
    let (scenes, _) = heard(&mut rx);
    assert!(scenes.is_empty(), "off by default on a test server");
    assert!(
        w.players[&1].character.cutscenes.is_empty(),
        "and the flag is left unset"
    );
    w.players.get_mut(&1).unwrap().cutscene_test = true;
    cross(&mut w, LAND);
    assert_eq!(heard(&mut rx).0, [["sky_down"]], "the opt-in turns them on");
}

#[test]
fn the_seen_list_is_saved_and_old_saves_without_it_load() {
    let mut c = Character::mercenary(Class::Warrior, 5, "Saved");
    c.cutscenes = vec!["dive".into(), "sky_up".into()];
    let json = serde_json::to_value(&c).unwrap();
    assert_eq!(json["cutscenes"], serde_json::json!(["dive", "sky_up"]));
    let back: Character = serde_json::from_value(json.clone()).unwrap();
    assert_eq!(back.cutscenes, c.cutscenes);
    let mut old = json;
    old.as_object_mut().unwrap().remove("cutscenes");
    let loaded: Character = serde_json::from_value(old).unwrap();
    assert!(
        loaded.cutscenes.is_empty(),
        "a save from before the cutscenes loads as 'none seen'"
    );
}

#[test]
fn nothing_hurts_the_hero_while_a_scene_plays_and_the_debug_op_exists() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    settle(&mut w, LAND);
    cross(&mut w, DEEP);
    let (hp, p) = {
        let p = &w.players[&1];
        (p.character.hp, p.character.point())
    };
    w.hurt_player_by(1, 50., p, "green", 1);
    assert_eq!(w.players[&1].character.hp, hp, "protected during the scene");
    w.time += 30.;
    w.hurt_player_by(1, 50., p, "green", 1);
    assert!(
        w.players[&1].character.hp < hp,
        "and hurt again once it is over"
    );
    let command: DebugCommand = serde_json::from_str(r#"{"op":"enable_cutscenes"}"#).unwrap();
    assert!(matches!(command, DebugCommand::EnableCutscenes));
}
