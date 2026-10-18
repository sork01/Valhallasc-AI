//! The signs before the final bosses (docs/boss-mechanics.md, `BOSSMECH-SIGN-ENGINE`): data of `world/boss-signs.txt`,
//! keyed by the final boss's kind, which is unique to its dungeon and the same in every private copy.
//!
//! A sign is the server's: it stands where the data says, and its words travel only in the answer to `sign_read`, so a
//! patched client cannot change them. The words of a sign are written for a child of about eight, in the same three
//! parts and the same four colours on every sign (the shared colour words live in `crate::bossmech::Effect`).
use serde::Deserialize;
use std::collections::BTreeMap;

/// A hero reads a sign from this close (tiles), the same reach as talking to a townsperson.
pub const READ_RANGE: f64 = 2.8;
/// The colours a sign's picture may show: red hurts, blue is safe, a dashed line is a path about to be used and
/// green is the gap in a wall.
pub const COLORS: [&str; 4] = ["red", "blue", "path", "green"];
/// The most characters in one part of a sign. About sixty words in all, at a child's reading speed.
pub const MAX_PART: usize = 150;

#[derive(Clone, Debug, Deserialize)]
pub struct SignDef {
    pub x: f64,
    pub y: f64,
    pub title: String,
    pub what: String,
    pub todo: String,
    pub tip: String,
    /// The telegraph colours the picture strip shows, in order.
    pub colors: Vec<String>,
}

/// The shipped table.
pub fn shipped() -> BTreeMap<String, SignDef> {
    let table: BTreeMap<String, SignDef> =
        serde_json::from_str(include_str!("../../world/boss-signs.txt"))
            .expect("valid boss signs table");
    for (kind, def) in &table {
        validate(kind, def).expect("boss signs table obeys the rules");
    }
    table
}

pub fn validate(kind: &str, def: &SignDef) -> Result<(), String> {
    if !def.x.is_finite() || !def.y.is_finite() {
        return Err(format!("{kind}: the sign has no position"));
    }
    for (name, text) in [
        ("title", &def.title),
        ("what", &def.what),
        ("todo", &def.todo),
        ("tip", &def.tip),
    ] {
        if text.trim().is_empty() {
            return Err(format!("{kind}: the sign's {name} is empty"));
        }
        if text.chars().count() > MAX_PART {
            return Err(format!(
                "{kind}: the sign's {name} is longer than {MAX_PART} characters"
            ));
        }
    }
    if def.colors.is_empty() || def.colors.len() > COLORS.len() {
        return Err(format!(
            "{kind}: a sign shows one to {} colours",
            COLORS.len()
        ));
    }
    for (i, color) in def.colors.iter().enumerate() {
        if !COLORS.contains(&color.as_str()) {
            return Err(format!("{kind}: unknown colour {color}"));
        }
        if def.colors[..i].contains(color) {
            return Err(format!("{kind}: colour {color} is shown twice"));
        }
    }
    Ok(())
}
