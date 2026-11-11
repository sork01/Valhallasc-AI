//! The opening cutscene (`INTRO-*`): a brand-new character sees one minute of the Grey Gull sailing to Greenmeadow with a narrator who tells
//! why the hero was summoned. It is kind `intro`, decided on the character's first tick after creation (`intro_pending`, filled by `join_as`;
//! `Character.landing` must still be set), and its packet says whether the player may skip it (the account already has another character).
//!
//! Crossing cutscenes (`CUTSCENE-*`, Beta 1.42.0): the first time a hero climbs up to Bifrost, comes down from it, dives into the sea
//! or comes back up, the client plays a short locked cutscene for it. The server only decides *whether* one plays and remembers it:
//! `Character.cutscenes` lists the kinds already seen, one `cutscene` packet carries the unseen ones in order, and a timed grace keeps
//! monsters off the hero while the client holds them still. Nothing here moves the hero; the crossing itself already happened.
use super::*;

/// Every kind, in the order the client names them (the four crossings and the opening).
#[cfg(test)]
pub const KINDS: [&str; 5] = ["sky_up", "sky_down", "dive", "surface", "intro"];
/// The opening cutscene's length on the client (seconds); the grace covers it with a margin.
pub const INTRO_SECONDS: f64 = 62.0;
/// How long one scene may last on the client (seconds, the longest of the four) and the extra margin of the grace.
pub const SCENE_SECONDS: f64 = 6.5;
const GRACE_MARGIN: f64 = 1.5;
/// A crossing counts only when the hero used a gate this recently: Spark landings, respawns and debug teleports are not crossings.
const CROSSING_WINDOW: f64 = 0.3;

/// What kind of place a zone is.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Env {
    Land,
    Sky,
    Sea,
}

impl Env {
    pub fn of(map: &Map) -> Env {
        if map.underwater() {
            Env::Sea
        } else if map.theme == "sky" {
            Env::Sky
        } else {
            Env::Land
        }
    }
}

/// The scenes a crossing from `from` to `to` can play, in order. Bifrost into the sea falls and then dives; the sea into Bifrost
/// surfaces and then rides the updraft.
pub fn scenes_for(from: Env, to: Env) -> Vec<&'static str> {
    use Env::*;
    match (from, to) {
        (Land, Sky) => vec!["sky_up"],
        (Sky, Land) => vec!["sky_down"],
        (Land, Sea) => vec!["dive"],
        (Sea, Land) => vec!["surface"],
        (Sky, Sea) => vec!["sky_down", "dive"],
        (Sea, Sky) => vec!["surface", "sky_up"],
        _ => vec![],
    }
}

impl Player {
    /// The unseen scenes for a crossing, in order.
    fn unseen(&self, from: Env, to: Env) -> Vec<&'static str> {
        scenes_for(from, to)
            .into_iter()
            .filter(|k| !self.character.cutscenes.iter().any(|seen| seen == k))
            .collect()
    }
}

impl World {
    /// What the lead-shoes tick learned about each hero this tick: the scenes to play (already recorded as seen).
    pub(super) fn crossing_scenes(&mut self, session: u64, now: Env) -> Vec<&'static str> {
        let time = self.time;
        let opt_in = self.cutscene_opt_in;
        let pending = self
            .players
            .get(&session)
            .filter(|p| p.env.is_none())
            .and_then(|p| self.intro_pending.remove(&p.character.id));
        let Some(p) = self.players.get_mut(&session) else {
            return vec![];
        };
        let before = p.env.replace(now);
        // The very first tick of a character created just now: the opening cutscene, once.
        if before.is_none() {
            let wanted = pending.is_some()
                && p.character.landing
                && !p.character.cutscenes.iter().any(|k| k == "intro")
                && !(opt_in && !p.cutscene_test);
            if !wanted {
                return vec![];
            }
            p.character.cutscenes.push("intro".into());
            p.cutscene_until = time + INTRO_SECONDS + GRACE_MARGIN;
            let _ = p.peer.try_send(
                json!({"type":"cutscene","scenes":["intro"],"skippable":pending == Some(true)}),
            );
            return vec!["intro"];
        }
        let Some(before) = before.filter(|b| *b != now) else {
            return vec![];
        };
        if time - p.portal_at > CROSSING_WINDOW || (opt_in && !p.cutscene_test) {
            return vec![];
        }
        let scenes = p.unseen(before, now);
        if scenes.is_empty() {
            return scenes;
        }
        for k in &scenes {
            p.character.cutscenes.push((*k).into());
        }
        p.cutscene_until = time + SCENE_SECONDS * scenes.len() as f64 + GRACE_MARGIN;
        let _ = p.peer.try_send(json!({"type":"cutscene","scenes":scenes}));
        scenes
    }
}
