//! Final boss mechanics (docs/boss-mechanics.md): the numbers every mechanic shares, decided once in `BOSSMECH-RULES`.
//! The engine (`BOSSMECH-ENGINE`), the client, the signs and the harness read these and keep no copies, so a sign's
//! wording and a mechanic's real timing cannot drift apart.
#![allow(dead_code)] // until BOSSMECH-ENGINE reads these

/// An instant kill is cast for at least this long (seconds), a heavy hit for at least `HEAVY_HIT_MIN_CAST`.
pub const INSTANT_KILL_MIN_CAST: f64 = 5.;
pub const HEAVY_HIT_MIN_CAST: f64 = 3.;
/// The slowest class on foot (the Warrior) in tiles per second; every safe spot is measured at this speed.
pub const SLOWEST_PLAYER_SPEED: f64 = 5.2;
/// A safe spot must be reachable from anywhere in the arena within this share of the cast.
pub const REACH_SHARE: f64 = 0.6;

/// Whether a lethal effect lets the defences of the target change the outcome. All `false`: where you stand decides.
/// A dash is a shortcut across a telegraph, but its invulnerable frames do not make you survive standing in it.
pub const KILL_IGNORES_DEFENCE: bool = true;
pub const KILL_IGNORES_DODGE: bool = true;
pub const KILL_IGNORES_DASH_FRAMES: bool = true;
/// Test and GM god mode (`World::god_mode`, `Player::god`) still block every boss mechanic, so a manual test of a
/// fight is not ended by it. The telegraph, the cast and the log line are still produced, as "Would have been
/// killed by ...". Players in a city and hidden GMs are never targeted.
pub const GOD_MODE_BLOCKS: bool = true;
/// The soft enrage (`world/enrage.txt`) keeps counting through an invulnerable phase, so a shield cannot stall.
pub const ENRAGE_RUNS_DURING_INVULNERABLE: bool = true;
/// Open-world elites and the dungeons' middle bosses get no mechanics for now. Revisit after `BOSSMECH-CHECK`.
pub const COVERS_ELITES_AND_MIDDLE_BOSSES: bool = false;
/// The most players one marking mechanic may mark; never everyone (`mark` marks `min(this, party - 1)`, at least one).
pub const MAX_MARKED: usize = 3;

/// What a ground effect does when its cast ends.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Effect {
    /// Anyone it reaches dies.
    Kill,
    /// A large hit (not a kill); the share of health is chosen per mechanic.
    Heavy,
    /// Kills everyone *not* inside it (the safe-island shape).
    KillOutside,
}

/// What a telegraph tells the player; the same language in every dungeon and on every sign.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Telegraph {
    /// Red: this place will hurt.
    Danger,
    /// Blue: stand here.
    Safe,
    /// Dashed line: a path that is about to be used.
    Path,
    /// Green: the gap in a moving wall.
    Gap,
}

impl Telegraph {
    /// The fill colour the effects canvas draws it in (red, blue, pale gold, green).
    pub fn color(self) -> &'static str {
        match self {
            Self::Danger => "#e0453b",
            Self::Safe => "#3f9bea",
            Self::Path => "#f1e3b4",
            Self::Gap => "#4fc26b",
        }
    }
    /// The word the signs and the log use for it (the Swedish text is built from the same key).
    pub fn word(self) -> &'static str {
        match self {
            Self::Danger => "red",
            Self::Safe => "blue",
            Self::Path => "dashed line",
            Self::Gap => "green gap",
        }
    }
    /// Only the dashed path is drawn as a line; the others are filled shapes.
    pub fn dashed(self) -> bool {
        self == Self::Path
    }
}

impl Effect {
    /// The shortest cast the effect may have.
    pub fn min_cast(self) -> f64 {
        match self {
            Self::Kill | Self::KillOutside => INSTANT_KILL_MIN_CAST,
            Self::Heavy => HEAVY_HIT_MIN_CAST,
        }
    }
}

/// Whether a cast time is allowed for the effect.
pub fn cast_is_long_enough(effect: Effect, cast: f64) -> bool {
    cast.is_finite() && cast >= effect.min_cast()
}

/// The farthest anyone may have to run to safety: `SLOWEST_PLAYER_SPEED * REACH_SHARE * cast` tiles.
pub fn max_run_distance(cast: f64) -> f64 {
    if cast.is_finite() && cast > 0. {
        SLOWEST_PLAYER_SPEED * REACH_SHARE * cast
    } else {
        0.
    }
}

/// The text the log and the defeat screen show when a mechanic kills (docs/boss-mechanics.md rule 1).
pub fn death_message(ability: &str, would_have: bool) -> String {
    if would_have {
        format!("Would have been killed by {ability}")
    } else {
        format!("Killed by {ability}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Class;

    #[test]
    fn the_slowest_player_speed_is_the_slowest_class() {
        let slowest = [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ]
        .iter()
        .map(|c| c.speed())
        .fold(f64::INFINITY, f64::min);
        assert_eq!(SLOWEST_PLAYER_SPEED, slowest);
    }

    #[test]
    fn cast_times_have_a_floor_and_refuse_nonsense() {
        assert!(cast_is_long_enough(Effect::Kill, 5.));
        assert!(!cast_is_long_enough(Effect::Kill, 4.99));
        assert!(cast_is_long_enough(Effect::Heavy, 3.));
        assert!(!cast_is_long_enough(Effect::Heavy, 2.9));
        assert!(!cast_is_long_enough(Effect::KillOutside, 4.));
        assert!(!cast_is_long_enough(Effect::Kill, f64::NAN));
        assert!(!cast_is_long_enough(Effect::Kill, f64::INFINITY));
    }

    #[test]
    fn a_five_second_cast_lets_the_slowest_class_cross_fifteen_tiles() {
        assert!((max_run_distance(5.) - 15.6).abs() < 1e-9);
        assert!((max_run_distance(3.) - 9.36).abs() < 1e-9);
        assert_eq!(max_run_distance(0.), 0.);
        assert_eq!(max_run_distance(-1.), 0.);
        assert_eq!(max_run_distance(f64::NAN), 0.);
    }

    #[test]
    fn the_four_telegraphs_are_distinct_and_only_the_path_is_dashed() {
        let all = [
            Telegraph::Danger,
            Telegraph::Safe,
            Telegraph::Path,
            Telegraph::Gap,
        ];
        for (i, a) in all.iter().enumerate() {
            assert!(a.color().starts_with('#') && a.color().len() == 7);
            assert_eq!(a.dashed(), *a == Telegraph::Path);
            for b in &all[i + 1..] {
                assert_ne!(a.color(), b.color());
                assert_ne!(a.word(), b.word());
            }
        }
    }

    #[test]
    fn a_death_is_named_and_a_god_mode_player_is_told_what_would_have_happened() {
        assert_eq!(
            death_message("Toll of the Deep", false),
            "Killed by Toll of the Deep"
        );
        assert_eq!(
            death_message("Toll of the Deep", true),
            "Would have been killed by Toll of the Deep"
        );
    }

    #[test]
    fn the_decisions_are_the_ones_the_design_doc_states() {
        const {
            assert!(KILL_IGNORES_DEFENCE && KILL_IGNORES_DODGE && KILL_IGNORES_DASH_FRAMES);
            assert!(GOD_MODE_BLOCKS && ENRAGE_RUNS_DURING_INVULNERABLE);
            assert!(!COVERS_ELITES_AND_MIDDLE_BOSSES);
            assert!(MAX_MARKED == 3);
        }
    }
}
