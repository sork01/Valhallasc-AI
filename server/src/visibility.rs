//! Final per-viewer snapshot filter. The shared watch snapshot stays inside the server;
//! every welcome and WebSocket snapshot passes through here before serialization.
use serde_json::{Value, json};
use std::collections::BTreeSet;

pub fn filter_view(view: &mut Value, viewer: &str) {
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
        players.retain(|p| !blocked_ids.contains(p["id"].as_str().unwrap_or("")));
        for player in players {
            if let Some(object) = player.as_object_mut() {
                object.remove("session");
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
}
