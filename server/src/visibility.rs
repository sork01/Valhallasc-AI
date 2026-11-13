//! Final per-viewer snapshot filter. The shared watch snapshot stays inside the server;
//! every welcome and WebSocket snapshot passes through here before serialization.
use serde_json::{Value, json};
use std::collections::BTreeSet;

/// Player fields sent only to their owner (see `filter_view`). Everything else stays for other clients: what is drawn
/// (look, position, health, buffs, mount, `signatureWeapon`), PvP/trade/party flags and the nameplate title.
const OWN_ONLY: &[&str] = &[
    "quests",
    "inventory",
    "equipment",
    "gearInstances",
    "bags",
    "bagCapacity",
    "bagUsed",
    "attributes",
    "gearAttributes",
    "passiveAttributes",
    "statPoints",
    "attack",
    "defense",
    "critChance",
    "attackCooldown",
    "cooldownReduction",
    "dodgeChance",
    "hitChance",
    "xp",
    "xpNeed",
    "gold",
    "kills",
    "explored",
    "travelStops",
    "mountOwned",
    "mounts",
    "rebirthTiers",
    "rebirthPerks",
    "setCounts",
    "setCd",
    "skillCd",
    "potionCd",
    "mealCd",
    "atkCd",
    "dashCd",
    "resource",
    "maxResource",
    "resourceType",
    "abandonedQuests",
    "seasonalClaims",
    "seasonalRolls",
    "festivalBuff",
    "rested",
    "achievementPoints",
    "storyMemory",
    "resurrectionSickness",
    "effectiveAttributes",
];

pub fn filter_view(view: &mut Value, viewer: &str) {
    let viewer_ghost = view["players"]
        .as_array()
        .into_iter()
        .flatten()
        .any(|p| p["id"] == viewer && p["ghost"] == true);
    let hidden: Vec<(String, u64)> = view["players"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|p| p["hidden"] == true)
        .filter_map(|p| Some((p["id"].as_str()?.to_owned(), p["session"].as_u64()?)))
        .collect();
    let blocked_ids: BTreeSet<&str> = hidden
        .iter()
        .filter(|(id, _)| id != viewer)
        .map(|(id, _)| id.as_str())
        .collect();
    let blocked_sessions: BTreeSet<u64> = hidden
        .iter()
        .filter(|(id, _)| id != viewer)
        .map(|(_, session)| *session)
        .collect();
    if let Some(players) = view["players"].as_array_mut() {
        players.retain(|p| {
            let id = p["id"].as_str().unwrap_or("");
            if blocked_ids.contains(id) {
                return false;
            }
            if !viewer_ghost && p["ghost"] == true && id != viewer {
                return false;
            }
            true
        });
        for player in players {
            if let Some(object) = player.as_object_mut() {
                object.remove("session");
                if object.get("id").and_then(Value::as_str) != Some(viewer) {
                    object.remove("mailUnread");
                    // What only the owner's own client reads: nobody else needs your bags, quests or gold, and it is
                    // most of a player's ~2.7 KB. Inspect has its own whitelisted packet (`world/inspect.rs`).
                    for key in OWN_ONLY {
                        object.remove(*key);
                    }
                }
            }
        }
    }
    if let Some(across) = view["across"].as_array_mut() {
        for side in across {
            if let Some(players) = side["players"].as_array_mut() {
                players.retain(|p| {
                    let id = p["id"].as_str().unwrap_or("");
                    if blocked_ids.contains(id) || p["hidden"] == true {
                        return false;
                    }
                    if !viewer_ghost && p["ghost"] == true && id != viewer {
                        return false;
                    }
                    true
                });
            }
        }
    }
    if let Some(bolts) = view["bolts"].as_array_mut() {
        bolts.retain(|b| {
            !b["owner"]
                .as_u64()
                .is_some_and(|session| blocked_sessions.contains(&session))
        });
    }
    if let Some(drops) = view["drops"].as_array_mut() {
        drops.retain(|d| !blocked_ids.contains(d["owner"].as_str().unwrap_or("")));
    }
    if hidden.iter().any(|(id, _)| id == viewer) {
        let count = view["online"].as_u64().unwrap_or(0);
        view["online"] = json!(count + 1);
    }
}

/// Half-width (tiles) of the square around the viewer that still gets full enemy data. The client draws at most about
/// 48 tiles from the hero along an axis (portrait phone, 1600 px virtual width), plus a margin for tall sprites.
pub const CULL_HALF: f64 = 56.;

/// Per-viewer distance culling of a zone view: enemies farther than `CULL_HALF` tiles (either axis) from the viewer's
/// own hero are dropped, and listed as `far: [[x, y, big]]` dots so the minimap keeps showing them. Elites and bosses
/// are always kept, dead enemies are not dotted, dungeon copies (`instance`) are never culled, and neither is a view
/// that does not list the viewer. Things across a seam are culled by their distance to the viewer after undoing the seam
/// shift.
pub fn cull_view(view: &mut Value, viewer: &str) {
    if view.get("instance").is_some() {
        return;
    }
    let Some((vx, vy)) = view["players"]
        .as_array()
        .into_iter()
        .flatten()
        .find(|p| p["id"] == viewer)
        .and_then(|p| Some((p["x"].as_f64()?, p["y"].as_f64()?)))
    else {
        return;
    };
    let near = |x: Option<f64>, y: Option<f64>, dx: f64, dy: f64| match (x, y) {
        (Some(x), Some(y)) => (x - dx - vx).abs() <= CULL_HALF && (y - dy - vy).abs() <= CULL_HALF,
        _ => true,
    };
    let mut far: Vec<Value> = Vec::new();
    if let Some(slimes) = view["slimes"].as_array_mut() {
        slimes.retain(|s| {
            if s["elite"] == true || near(s["x"].as_f64(), s["y"].as_f64(), 0., 0.) {
                return true;
            }
            if s["dead"] != true {
                let round = |v: f64| (v * 10.).round() / 10.;
                far.push(json!([
                    round(s["x"].as_f64().unwrap_or(0.)),
                    round(s["y"].as_f64().unwrap_or(0.)),
                    u8::from(s["kind"] == "big")
                ]));
            }
            false
        });
    }
    if !far.is_empty() {
        view["far"] = Value::Array(far);
    }
    if let Some(across) = view["across"].as_array_mut() {
        for side in across {
            let (dx, dy) = (
                side["shift"][0].as_f64().unwrap_or(0.),
                side["shift"][1].as_f64().unwrap_or(0.),
            );
            for key in ["slimes", "players"] {
                if let Some(list) = side[key].as_array_mut() {
                    list.retain(|a| near(a["x"].as_f64(), a["y"].as_f64(), dx, dy));
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hidden_actor_and_owned_objects_are_absent_from_other_wire_views() {
        let raw = json!({"players":[{"id":"gm","hidden":true,"session":7,"x":19},{"id":"guest","hidden":false,"x":20}],
            "bolts":[{"owner":7,"x":19},{"owner":8,"x":20}],"drops":[{"owner":"gm","x":19},{"owner":"guest","x":20}],"online":1});
        let mut guest = raw.clone();
        filter_view(&mut guest, "guest");
        assert_eq!(guest["players"].as_array().unwrap().len(), 1);
        assert_eq!(guest["bolts"].as_array().unwrap().len(), 1);
        assert_eq!(guest["drops"].as_array().unwrap().len(), 1);
        assert_eq!(guest["online"], 1);
        assert!(!guest.to_string().contains("\"session\""));
        let mut gm = raw;
        filter_view(&mut gm, "gm");
        assert_eq!(gm["players"].as_array().unwrap().len(), 2);
        assert_eq!(gm["online"], 2);
        assert!(!gm.to_string().contains("\"session\""));
    }

    #[test]
    fn live_viewers_cannot_see_ghosts_in_zone_or_across_seam() {
        let raw = json!({
            "players": [
                {"id": "live", "hidden": false, "ghost": false, "session": 1, "x": 10},
                {"id": "spirit", "hidden": false, "ghost": true, "session": 2, "x": 12}
            ],
            "across": [{
                "to": 1,
                "shift": [0, 0],
                "players": [
                    {"id": "other_live", "hidden": false, "ghost": false, "x": 5},
                    {"id": "other_ghost", "hidden": false, "ghost": true, "x": 6}
                ]
            }],
            "bolts": [],
            "drops": [],
            "online": 2
        });
        let mut live_view = raw.clone();
        filter_view(&mut live_view, "live");
        let ids: Vec<_> = live_view["players"]
            .as_array()
            .unwrap()
            .iter()
            .map(|p| p["id"].as_str().unwrap())
            .collect();
        assert_eq!(ids, vec!["live"], "live viewer must not see ghost players");
        let across_ids: Vec<_> = live_view["across"][0]["players"]
            .as_array()
            .unwrap()
            .iter()
            .map(|p| p["id"].as_str().unwrap())
            .collect();
        assert_eq!(
            across_ids,
            vec!["other_live"],
            "live viewer must not see ghost players across a seam"
        );

        let mut ghost_view = raw;
        filter_view(&mut ghost_view, "spirit");
        assert_eq!(ghost_view["players"].as_array().unwrap().len(), 2);
        assert_eq!(
            ghost_view["across"][0]["players"]
                .as_array()
                .unwrap()
                .len(),
            2
        );
    }

    fn slime(id: u64, x: f64, y: f64, elite: bool, dead: bool, kind: &str) -> Value {
        json!({"id":id,"x":x,"y":y,"elite":elite,"dead":dead,"kind":kind})
    }
    fn cullable() -> Value {
        json!({"players":[{"id":"me","x":100.,"y":100.},{"id":"pal","x":300.,"y":300.}],
            "slimes":[slime(1,120.,90.,false,false,"green"), slime(2,100.+CULL_HALF+1.,100.,false,false,"green"),
                      slime(3,100.,100.-CULL_HALF-1.,false,false,"big"), slime(4,400.,400.,true,false,"king"),
                      slime(5,300.,300.,false,true,"green")],
            "across":[{"to":1,"shift":[-50.,0.],"slimes":[slime(10,60.,100.,false,false,"wisp"), slime(11,100.+CULL_HALF+51.,100.,false,false,"wisp")],
                       "players":[{"id":"far","x":300.,"y":100.},{"id":"near","x":30.,"y":100.}]}]})
    }
    fn ids(list: &Value) -> Vec<u64> {
        list.as_array()
            .unwrap()
            .iter()
            .filter_map(|s| s["id"].as_u64())
            .collect()
    }

    #[test]
    fn enemies_beyond_the_square_around_the_viewer_are_dropped_and_dotted() {
        let mut v = cullable();
        cull_view(&mut v, "me");
        assert_eq!(
            ids(&v["slimes"]),
            vec![1, 4],
            "near and elite stay; far ones go"
        );
        // Far living enemies become dots; the far dead one (id 5) is not dotted.
        assert_eq!(v["far"], json!([[157.0, 100.0, 0], [100.0, 43.0, 1]]));
    }

    #[test]
    fn across_entries_are_culled_by_distance_to_the_viewer_after_the_seam_shift() {
        let mut v = cullable();
        cull_view(&mut v, "me");
        assert_eq!(ids(&v["across"][0]["slimes"]), vec![10]);
        let kept: Vec<&str> = v["across"][0]["players"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|p| p["id"].as_str())
            .collect();
        assert_eq!(kept, vec!["near"]);
    }

    #[test]
    fn a_view_that_cannot_be_culled_is_left_alone() {
        let mut stranger = cullable();
        cull_view(&mut stranger, "nobody");
        assert_eq!(stranger, cullable(), "viewer not listed");
        let mut dungeon = cullable();
        dungeon["instance"] = json!({"cleared":false});
        let before = dungeon.clone();
        cull_view(&mut dungeon, "me");
        assert_eq!(dungeon, before, "instance copies are never culled");
    }

    #[test]
    fn other_players_lose_their_private_fields_but_the_owner_keeps_them() {
        let mut raw = json!({"players":[
            {"id":"me","x":1,"inventory":[1],"quests":[2],"gold":9,"xp":5,"skillCd":{},"signatureWeapon":"w"},
            {"id":"pal","x":2,"inventory":[1],"quests":[2],"gold":9,"xp":5,"skillCd":{},"signatureWeapon":"w","look":{"name":"Pal"},"hp":3,"buffs":[]}]});
        filter_view(&mut raw, "me");
        let me = &raw["players"][0];
        assert!(
            me["inventory"].is_array() && me["gold"] == 9 && me["quests"].is_array(),
            "owner keeps their own"
        );
        let pal = &raw["players"][1];
        for key in ["inventory", "quests", "gold", "xp", "skillCd"] {
            assert!(
                pal.get(key).is_none(),
                "another player's {key} reaches the viewer"
            );
        }
        for key in ["look", "hp", "buffs", "signatureWeapon", "x"] {
            assert!(
                pal.get(key).is_some(),
                "{key} is drawn for other players and must stay"
            );
        }
    }
}
