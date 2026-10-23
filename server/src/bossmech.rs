//! Final boss mechanics (docs/boss-mechanics.md): the numbers every mechanic shares, decided once in `BOSSMECH-RULES`.
//! The engine (`BOSSMECH-ENGINE`), the client, the signs and the harness read these and keep no copies, so a sign's
//! wording and a mechanic's real timing cannot drift apart.
//!
//! This file holds the pure half of the engine: the data schema of `world/boss-mechanics.txt`, the shapes and their
//! geometry, the safety-reachability walk and the table validator. The state machine that runs it against a live
//! fight is `world/boss_mechanics.rs`.
use crate::model::{Map, Point};
use serde::Deserialize;
use serde_json::{Value, json};
use std::collections::BTreeMap;

/// An instant kill is cast for at least this long (seconds), a heavy hit for at least `HEAVY_HIT_MIN_CAST`.
pub const INSTANT_KILL_MIN_CAST: f64 = 5.;
pub const HEAVY_HIT_MIN_CAST: f64 = 3.;
/// The slowest class on foot (the Warrior) in tiles per second; every safe spot is measured at this speed.
pub const SLOWEST_PLAYER_SPEED: f64 = 5.2;
/// A safe spot must be reachable from anywhere in the arena within this share of the cast.
pub const REACH_SHARE: f64 = 0.6;

/// Whether a lethal effect lets the defences of the target change the outcome. All `false`: where you stand decides.
/// A dash is a shortcut across a telegraph, but its invulnerable frames do not make you survive standing in it.
#[allow(dead_code)] // a policy flag that tests pin; the engine has no branch for the other value
pub const KILL_IGNORES_DEFENCE: bool = true;
#[allow(dead_code)] // a policy flag that tests pin; the engine has no branch for the other value
pub const KILL_IGNORES_DODGE: bool = true;
#[allow(dead_code)] // a policy flag that tests pin; the engine has no branch for the other value
pub const KILL_IGNORES_DASH_FRAMES: bool = true;
/// Test and GM god mode (`World::god_mode`, `Player::god`) still block every boss mechanic, so a manual test of a
/// fight is not ended by it. The telegraph, the cast and the log line are still produced, as "Would have been
/// killed by ...". Players in a city and hidden GMs are never targeted.
pub const GOD_MODE_BLOCKS: bool = true;
/// The soft enrage (`world/enrage.txt`) keeps counting through an invulnerable phase, so a shield cannot stall.
#[allow(dead_code)] // a policy flag that tests pin; the engine has no branch for the other value
pub const ENRAGE_RUNS_DURING_INVULNERABLE: bool = true;
/// Open-world elites and the dungeons' middle bosses get no mechanics for now. Revisit after `BOSSMECH-CHECK`.
#[allow(dead_code)] // a policy flag that tests pin; the engine has no branch for the other value
pub const COVERS_ELITES_AND_MIDDLE_BOSSES: bool = false;
/// The most players one marking mechanic may mark; never everyone (`mark` marks `min(this, party - 1)`, at least one).
pub const MAX_MARKED: usize = 3;

/// A sweeping wall gives its warning (dashed lines) for at least this long before it moves.
pub const SWEEP_MIN_WARN: f64 = 4.;
/// Spokes that reverse show a gear symbol for at least this long first.
pub const SPOKE_REVERSE_MIN_WARN: f64 = 2.;
/// A marked player's ring or beam may not be fired sooner than the instant-kill floor either.
pub const MARK_MIN_CAST: f64 = INSTANT_KILL_MIN_CAST;

/// What a ground effect does when its cast ends.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
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

// ---------------------------------------------------------------------------------------------------------------
// The data: `world/boss-mechanics.txt`, keyed by the final boss's monster kind.
// ---------------------------------------------------------------------------------------------------------------
fn one_u() -> u32 {
    1
}

/// A boss's mechanics, in the order they are listed. Each is independent and keeps its own timer.
#[derive(Clone, Debug, Deserialize)]
pub struct BossDef {
    pub mechanics: Vec<Mechanic>,
    /// Use the smallest authored room containing the boss when a larger room overlaps it.
    #[serde(default)]
    pub inner_arena: bool,
    /// Encounter bounds for a boss in a map without authored rooms.
    #[serde(default)]
    pub arena: Option<[f64; 4]>,
}

/// One named ability. `name` is what the cast bar shows and what a death says ("Killed by <name>").
#[derive(Clone, Debug, Deserialize)]
pub struct Mechanic {
    pub name: String,
    /// Active while the boss's health share is at most this (an escalation lists a second entry with a lower one).
    #[serde(default = "one")]
    pub hp_max: f64,
    /// ... and above this.
    #[serde(default)]
    pub hp_min: f64,
    #[serde(flatten)]
    pub block: Block,
}
impl Mechanic {
    pub fn active_at(&self, hp_share: f64) -> bool {
        hp_share <= self.hp_max && hp_share > self.hp_min
    }
}

/// The building blocks of docs/boss-mechanics.md. `echo` is a field of `zone`, not a block of its own.
#[derive(Clone, Debug, Deserialize)]
#[serde(tag = "block", rename_all = "snake_case")]
pub enum Block {
    Zone(Zone),
    Shield(Shield),
    Adds(Adds),
    Mark(Mark),
    Sweep(Sweep),
    Break(Break),
    Stasis(Stasis),
    Split(Split),
    Hold(Hold),
    Gaze(Gaze),
    Static(Static),
    Tether(Tether),
    Gust(Gust),
    Soak(Soak),
    Valves(Valves),
    Relay(Relay),
    Grid(Grid),
    Carry(Carry),
    Reflect(Reflect),
    Crack(Crack),
    Heat(Heat),
    Seats(Seats),
}

/// A standing leash: all fighters form pairs (one trio for an odd crew),
/// hold their numbered anvil in order, and break their chain together.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Tether {
    pub cast: f64,
    pub every: f64,
    pub first: f64,
    pub duration: f64,
    pub leash: f64,
    pub heavy: f64,
    pub points: Vec<[f64; 2]>,
    pub r: f64,
    pub hold: f64,
}

/// Wind pushes unsheltered fighters toward a lethal, visibly marked rim.
/// Each iron post shelters a bounded number; the server assigns no immunity
/// merely because a client drew itself beside one.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Gust {
    pub cast: f64,
    pub every: f64,
    pub first: f64,
    pub push: f64,
    pub points: Vec<[f64; 2]>,
    pub r: f64,
    pub capacity: usize,
    pub rim: f64,
}

/// Each anvil needs a separate group. Missing one harms the whole crew and
/// strikes down the fighters trying to hold that anvil without enough help.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Soak {
    pub cast: f64,
    pub every: f64,
    pub first: f64,
    pub points: Vec<[f64; 2]>,
    pub r: f64,
    pub need: usize,
    pub heavy: f64,
}

/// Counted, continuous holds on opposite sides of a temporary lava divide.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Valves {
    pub at: Vec<f64>,
    pub cast: f64,
    pub duration: f64,
    pub points: Vec<[f64; 2]>,
    pub r: f64,
    pub need: usize,
    pub hold: f64,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Relay {
    pub cast: f64,
    pub first: f64,
    pub every: f64,
    pub duration: f64,
    pub count: usize,
    pub fuse: f64,
    pub immunity: f64,
    pub touch: f64,
    pub blast: f64,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Grid {
    pub cast: f64,
    pub first: f64,
    pub every: f64,
    pub bpm: f64,
    pub heavy: f64,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Carry {
    pub points: Vec<[f64; 2]>,
    pub r: f64,
    pub throw_r: f64,
    pub need: usize,
    pub window: f64,
    pub quenched: f64,
    pub speed: f64,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Reflect {
    pub cast: f64,
    pub first: f64,
    pub every: f64,
    pub duration: f64,
    pub heavy: f64,
}

/// Eldmarr's persistent floor remembers actual cells stood on by living actors.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Crack {
    pub stand: f64,
    pub cast: f64,
    pub lava: f64,
    pub cell: f64,
}
/// Time-driven heat, with bounded cooling and a visible detonation fuse.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Heat {
    pub fill: f64,
    pub cool: f64,
    pub cast: f64,
    pub blast: f64,
    pub move_every: f64,
    pub capacity: usize,
    pub r: f64,
    pub points: Vec<[f64; 2]>,
}
/// Unlike safe islands, each throne plate can shelter exactly one living actor.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Seats {
    pub cast: f64,
    pub every: f64,
    pub first: f64,
    pub r: f64,
    pub points: Vec<[f64; 2]>,
}

/// A ground shape with a cast time and an effect.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Zone {
    pub shape: ShapeSpec,
    pub effect: Effect,
    /// The share of the victim's maximum health a `heavy` effect takes.
    #[serde(default)]
    pub heavy: f64,
    pub cast: f64,
    pub every: f64,
    /// Seconds from the start of the fight to the first cast (default: `every`).
    #[serde(default)]
    pub first: Option<f64>,
    /// How many times in a row it is cast (the shape is chosen again each time).
    #[serde(default = "one_u")]
    pub repeat: u32,
    #[serde(default)]
    pub repeat_gap: f64,
    /// On a repeated half-room cast, fold the opposite side of the same crease.
    #[serde(default)]
    pub alternate: bool,
    /// After it lands, the same shape lands again after each of these delays, with a pale copy kept on the floor.
    #[serde(default)]
    pub echo: Vec<f64>,
    /// Seconds a landed shape stays drawn (flood draining, puddles). Only the picture lingers.
    #[serde(default)]
    pub linger: f64,
}

/// Where a circle is centred.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum At {
    #[default]
    Boss,
    /// On a random living player of the fight.
    Target,
    /// At a random free spot of the arena.
    Random,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum ShapeSpec {
    /// A disc, or a ring when `inner` is above zero.
    Circle {
        r: f64,
        #[serde(default)]
        inner: f64,
        #[serde(default)]
        at: At,
    },
    /// From the boss toward a random player; `half_angle` in degrees.
    Cone { half_angle: f64, length: f64 },
    /// From the boss through a random player to the far wall, `width` tiles wide.
    Lane { width: f64 },
    /// A crease through the arena at a random angle; the other half stays at least `min_share` of the arena.
    Half { min_share: f64 },
    /// The whole arena.
    Arena,
    /// `count` safe discs; with `kill_outside` they are where you must stand.
    Islands { count: u32, r: f64 },
    /// The lit points of the boss's `hold` block (safe discs, for `kill_outside`).
    Lit,
}

/// While it stands the boss takes no damage until every add of its tag is dead.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Shield {
    /// Numbered helpers: only the lowest living slot is vulnerable.
    #[serde(default)]
    pub ordered: Option<Ordered>,
    pub steps: Vec<ShieldStep>,
    /// The share of maximum health the boss heals each second while shielded.
    #[serde(default)]
    pub heal_per_s: f64,
}
/// Each newly vulnerable object gets its own announced deadline.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Ordered {
    pub deadline: f64,
    pub heavy: f64,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ShieldStep {
    /// The shield rises when the boss's health share first drops to this.
    pub hp: f64,
    pub tag: String,
    pub count: u32,
    /// The woken monsters stand still and never attack (pearls, seeds).
    #[serde(default)]
    pub still: bool,
}

/// Wakes `count` sleeping monsters of `tag` (map spawns with `ambush: tag`) at set times.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Adds {
    pub tag: String,
    pub count: u32,
    pub every: f64,
    #[serde(default)]
    pub first: Option<f64>,
    /// Put each at a random free spot of the arena instead of its authored place.
    #[serde(default)]
    pub scatter: bool,
    /// The woken monsters stand still and never attack (seeds).
    #[serde(default)]
    pub still: bool,
    #[serde(default)]
    pub bloom: Option<Bloom>,
}
/// An add still alive `after` seconds blooms: it goes, the boss heals, and a `then` add may take its place.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Bloom {
    pub after: f64,
    pub heal: f64,
    #[serde(default)]
    pub then: Option<String>,
}

/// A countdown on chosen players that resolves at the end. A marked player is never hurt by their own mark.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Mark {
    pub count: u32,
    pub every: f64,
    #[serde(default)]
    pub first: Option<f64>,
    pub cast: f64,
    pub effect: MarkEffect,
    /// Waves in a row (each marks again), `wave_gap` seconds apart.
    #[serde(default = "one_u")]
    pub waves: u32,
    #[serde(default)]
    pub wave_gap: f64,
    /// Seconds a burst's red puddle remains dangerous after it lands.
    #[serde(default)]
    pub linger: f64,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum MarkEffect {
    /// A disc round the marked player kills every other player in it.
    Burst { r: f64 },
    /// A beam from the boss through the marked player bounces off the arena walls and kills everyone on it.
    Beam { bounces: u32, width: f64 },
}

/// Something that moves across the arena on a schedule.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Sweep {
    pub kind: SweepKind,
    #[serde(default)]
    pub every: f64,
    #[serde(default)]
    pub first: Option<f64>,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(tag = "shape", rename_all = "snake_case", deny_unknown_fields)]
pub enum SweepKind {
    /// Walls of `thickness` tiles shown as dashed lines for `warn` seconds, then moving at `speed` tiles/s.
    Walls {
        warn: f64,
        speed: f64,
        thickness: f64,
        /// The width of the green gap in each wall.
        gap: f64,
        walls: Vec<WallSpec>,
    },
    /// `count` lethal lanes turning round the arena's centre; they reverse every `reverse_every` seconds after a
    /// warning of `reverse_warn`.
    Spokes {
        count: u32,
        width: f64,
        deg_per_s: f64,
        reverse_every: f64,
        reverse_warn: f64,
        length: f64,
    },
}
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WallSpec {
    pub from: Side,
    #[serde(default)]
    pub gap: GapAt,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Side {
    West,
    East,
    North,
    South,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GapAt {
    #[default]
    Random,
    /// Toward the low coordinate (west or north end of the wall).
    Low,
    High,
    Middle,
}

/// A channel the party cancels by dealing damage: the boss is stunned and takes more. Failing it kills everyone.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Break {
    pub cast: f64,
    pub every: f64,
    #[serde(default)]
    pub first: Option<f64>,
    /// The damage that breaks it, as a share of the boss's maximum health.
    pub bar: f64,
    pub stun: f64,
    /// Extra damage the boss takes while stunned (0.3 is +30%).
    pub vulnerable: f64,
    /// A burst phase instead of a repeating break: it begins once, when the boss's health (with its divided partner's)
    /// first falls to this share, and `cast` is the time to deal `bar`.
    #[serde(default)]
    pub at: Option<f64>,
    /// Too slow does not kill: the soft enrage (`items::enrage`) begins and stays on.
    #[serde(default)]
    pub enrage: bool,
    /// Too slow does not kill everyone: one random hero who is not grounded is loaded to the Static limit and
    /// detonates where they stand (needs a `static` block; mutually exclusive with `enrage`).
    #[serde(default)]
    pub overload: bool,
}

/// Seeking orbs freeze whoever they touch until allies break the cocoon, or until `hold` seconds are up.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Stasis {
    pub every: f64,
    #[serde(default)]
    pub first: Option<f64>,
    pub orbs: u32,
    pub speed: f64,
    pub life: f64,
    /// The sleeping monsters (one per frozen player) that become the cocoons.
    pub tag: String,
    pub hold: f64,
}

/// At `hp` the boss divides: a partner of `tag` wakes and both keep half the remaining health.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Split {
    pub hp: f64,
    pub tag: String,
    /// A body that falls while the other lives is downed this long; then it rises with half its health.
    pub revive_after: f64,
    /// The survivor's extra damage for each rise (0.5 is +50%).
    pub survivor_bonus: f64,
    /// Half-width of the lethal bridge between the two bodies; 0 for none.
    #[serde(default)]
    pub bridge: f64,
    /// When a body falls while the other lives the two join again into one boss left on this share of its maximum
    /// health, instead of the fallen one lying down and rising (0: the downed body rises as `revive_after` says).
    #[serde(default)]
    pub merge_hp: f64,
    /// The joined boss takes this share of every blow (0.5 is half: more defense). Only with `merge_hp`.
    #[serde(default = "one")]
    pub merge_defense: f64,
    /// The bridge hits whoever stands on it for this share of their health once a second instead of killing at once
    /// (0: it kills). A step off it survives; standing on it does not.
    #[serde(default)]
    pub bridge_hit: f64,
}

fn one() -> f64 {
    1.
}

/// Places that a player lights by standing in them for `hold_for` seconds; a lit place stays lit `lit_for`.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Hold {
    pub points: Vec<[f64; 2]>,
    pub r: f64,
    pub hold_for: f64,
    pub lit_for: f64,
    /// One lit place goes out this often (0: never).
    #[serde(default)]
    pub snuff_every: f64,
}

/// Every blow a player lands on the boss adds `per_hit` charges to that player. At `limit` the player detonates: a
/// lethal burst of radius `r` at their feet (it takes everyone near them, the bearer included). Standing on a ready
/// rod clears the charge and gives `immune` seconds in which no charge builds; the rod is dark for `dark` seconds.
/// The banner shows at `warn_at` charges.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Static {
    pub limit: u32,
    pub warn_at: u32,
    pub per_hit: u32,
    pub r: f64,
    pub rods: Vec<[f64; 2]>,
    pub rod_r: f64,
    pub immune: f64,
    pub dark: f64,
}

/// Line of sight: after `cast` seconds the boss sees everyone it has a clear line to. `cover` blocks it.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Gaze {
    pub cast: f64,
    pub every: f64,
    #[serde(default)]
    pub first: Option<f64>,
    #[serde(default)]
    pub cover: Vec<Cover>,
    /// A broken piece of cover stands again after this long.
    #[serde(default)]
    pub regrow: f64,
    /// Zero: one look at the end of the cast. Above zero: a beam turns once round the room in this many seconds.
    #[serde(default)]
    pub sweep: f64,
    /// Half-angle of the turning beam, in degrees.
    #[serde(default)]
    pub beam: f64,
}
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Cover {
    pub x: f64,
    pub y: f64,
    pub r: f64,
}

/// The shipped table (`world/boss-mechanics.txt`). The sixteen bosses are added one task at a time.
pub fn shipped() -> BTreeMap<String, BossDef> {
    // Test builds may read another table (`BOSSMECH_TABLE_FILE=path`), so tuning a burst phase needs no rebuild.
    #[cfg(test)]
    let text = std::env::var("BOSSMECH_TABLE_FILE").map_or_else(
        |_| include_str!("../../world/boss-mechanics.txt").to_string(),
        |path| std::fs::read_to_string(path).expect("readable BOSSMECH_TABLE_FILE"),
    );
    #[cfg(not(test))]
    let text = include_str!("../../world/boss-mechanics.txt").to_string();
    let table: BTreeMap<String, BossDef> =
        serde_json::from_str(&text).expect("valid boss mechanics table");
    for (kind, def) in &table {
        validate(kind, def).expect("boss mechanics table obeys the rules");
    }
    table
}

// ---------------------------------------------------------------------------------------------------------------
// Rectangles and shapes
// ---------------------------------------------------------------------------------------------------------------

/// The fighting area of a boss: its room, else the whole map.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Rect {
    pub x0: f64,
    pub y0: f64,
    pub x1: f64,
    pub y1: f64,
}
impl Rect {
    pub fn contains(self, p: Point) -> bool {
        p.x >= self.x0 && p.x <= self.x1 && p.y >= self.y0 && p.y <= self.y1
    }
    pub fn centre(self) -> Point {
        Point {
            x: (self.x0 + self.x1) / 2.,
            y: (self.y0 + self.y1) / 2.,
        }
    }
    pub fn width(self) -> f64 {
        self.x1 - self.x0
    }
    pub fn height(self) -> f64 {
        self.y1 - self.y0
    }
    pub fn diagonal(self) -> f64 {
        self.width().hypot(self.height())
    }
}

/// The room of `map` that holds `at` (or the nearest one); a map without rooms is one big arena.
pub fn arena_for(map: &Map, at: Point) -> Rect {
    let whole = Rect {
        x0: 0.7,
        y0: 0.7,
        x1: map.size as f64 - 0.7,
        y1: map.size as f64 - 0.7,
    };
    let mut best: Option<(f64, Rect)> = None;
    for r in &map.rooms {
        let rect = Rect {
            x0: r[0],
            y0: r[1],
            x1: r[2],
            y1: r[3],
        };
        let d = (rect.x0 - at.x).max(at.x - rect.x1).max(0.)
            + (rect.y0 - at.y).max(at.y - rect.y1).max(0.);
        if best.is_none_or(|(b, _)| d < b) {
            best = Some((d, rect));
        }
    }
    best.map_or(whole, |(_, r)| r)
}

/// A smaller boss chamber nested inside a larger authored room can be the encounter arena.
pub fn arena_for_boss(map: &Map, at: Point, def: &BossDef) -> Rect {
    if let Some([x0, y0, x1, y1]) = def.arena {
        return Rect { x0, y0, x1, y1 };
    }
    if !def.inner_arena {
        return arena_for(map, at);
    }
    map.rooms
        .iter()
        .filter(|r| at.x >= r[0] && at.x <= r[2] && at.y >= r[1] && at.y <= r[3])
        .min_by(|a, b| ((a[2] - a[0]) * (a[3] - a[1])).total_cmp(&((b[2] - b[0]) * (b[3] - b[1]))))
        .map_or_else(
            || arena_for(map, at),
            |r| Rect {
                x0: r[0],
                y0: r[1],
                x1: r[2],
                y1: r[3],
            },
        )
}

/// A shape on the floor, in map coordinates.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Shape {
    Circle {
        x: f64,
        y: f64,
        r: f64,
        inner: f64,
    },
    /// `dir` and `half` in radians.
    Cone {
        x: f64,
        y: f64,
        dir: f64,
        half: f64,
        length: f64,
    },
    Lane {
        a: Point,
        b: Point,
        half: f64,
    },
    /// The side of the line through (x, y) that the normal (nx, ny) points to.
    Half {
        x: f64,
        y: f64,
        nx: f64,
        ny: f64,
    },
    Arena(Rect),
}
impl Shape {
    pub fn contains(&self, p: Point) -> bool {
        match *self {
            Self::Circle { x, y, r, inner } => {
                let d = (p.x - x).hypot(p.y - y);
                d <= r && d >= inner
            }
            Self::Cone {
                x,
                y,
                dir,
                half,
                length,
            } => {
                let (dx, dy) = (p.x - x, p.y - y);
                let d = dx.hypot(dy);
                if d > length {
                    return false;
                }
                if d < 1e-9 {
                    return true;
                }
                let mut turn = dy.atan2(dx) - dir;
                while turn > std::f64::consts::PI {
                    turn -= 2. * std::f64::consts::PI;
                }
                while turn < -std::f64::consts::PI {
                    turn += 2. * std::f64::consts::PI;
                }
                turn.abs() <= half
            }
            Self::Lane { a, b, half } => segment_distance(p, a, b) <= half,
            Self::Half { x, y, nx, ny } => (p.x - x) * nx + (p.y - y) * ny > 0.,
            Self::Arena(rect) => rect.contains(p),
        }
    }
    /// The picture the client draws.
    pub fn view(&self) -> Value {
        match *self {
            Self::Circle { x, y, r, inner } => {
                json!({"t":"circle","x":x,"y":y,"r":r,"inner":inner})
            }
            Self::Cone {
                x,
                y,
                dir,
                half,
                length,
            } => json!({"t":"cone","x":x,"y":y,"dir":dir,"half":half,"length":length}),
            Self::Lane { a, b, half } => {
                json!({"t":"lane","x1":a.x,"y1":a.y,"x2":b.x,"y2":b.y,"half":half})
            }
            Self::Half { x, y, nx, ny } => json!({"t":"half","x":x,"y":y,"nx":nx,"ny":ny}),
            Self::Arena(r) => json!({"t":"rect","x0":r.x0,"y0":r.y0,"x1":r.x1,"y1":r.y1}),
        }
    }
}

/// Distance from `p` to the segment `a`-`b`.
pub fn segment_distance(p: Point, a: Point, b: Point) -> f64 {
    let (dx, dy) = (b.x - a.x, b.y - a.y);
    let t = (((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy).max(1e-12)).clamp(0., 1.);
    p.distance(Point {
        x: a.x + dx * t,
        y: a.y + dy * t,
    })
}

/// The bounce path of a beam: from `from` toward `toward`, reflected off the arena's walls `bounces` times.
/// Returns the corner points, `bounces + 2` of them (start, each wall hit, and the last wall hit).
pub fn beam_path(from: Point, toward: Point, arena: Rect, bounces: u32) -> Vec<Point> {
    let mut path = vec![from];
    let (mut x, mut y) = (from.x, from.y);
    let (mut dx, mut dy) = {
        let d = from.direction(toward);
        if d.x == 0. && d.y == 0. {
            (1., 0.)
        } else {
            (d.x, d.y)
        }
    };
    for _ in 0..=bounces {
        let tx = if dx > 1e-12 {
            (arena.x1 - x) / dx
        } else if dx < -1e-12 {
            (arena.x0 - x) / dx
        } else {
            f64::INFINITY
        };
        let ty = if dy > 1e-12 {
            (arena.y1 - y) / dy
        } else if dy < -1e-12 {
            (arena.y0 - y) / dy
        } else {
            f64::INFINITY
        };
        let t = tx.min(ty).max(0.);
        if !t.is_finite() {
            break;
        }
        x += dx * t;
        y += dy * t;
        path.push(Point { x, y });
        if tx <= ty {
            dx = -dx;
        }
        if ty <= tx {
            dy = -dy;
        }
    }
    path
}

/// Whether anything of `shapes` reaches `p`, for the effect. `kill_outside` flips it: hurt unless inside.
pub fn hurts(effect: Effect, shapes: &[Shape], p: Point) -> bool {
    let inside = shapes.iter().any(|s| s.contains(p));
    match effect {
        Effect::Kill | Effect::Heavy => inside,
        Effect::KillOutside => !inside,
    }
}

// ---------------------------------------------------------------------------------------------------------------
// Fair play: can everyone get out in time?
// ---------------------------------------------------------------------------------------------------------------

const GRID_STEP: f64 = 0.5;

fn walkable(map: &Map, p: Point) -> bool {
    let mut q = p;
    map.collide(&mut q, crate::world::PLAYER_RADIUS);
    q.distance(p) < 1e-6
}
/// The first walkable point of `arena` that cannot get to a point `hurt` is false for within
/// `max_run_distance(cast)` tiles of walking at the slowest class's speed (rule 2 of the design doc), or `None`
/// when everyone can. Players may run out of the room, so the walk covers the ground round the arena as far as a
/// cast allows; only the arena's own points are checked. Walking is measured on a half-tile grid with eight
/// directions.
pub fn first_unsafe_point(
    map: &Map,
    arena: Rect,
    cast: f64,
    hurt: &dyn Fn(Point) -> bool,
) -> Option<Point> {
    let reach = max_run_distance(cast);
    let size = map.size as f64;
    let walk = Rect {
        x0: (arena.x0 - reach).max(0.7),
        y0: (arena.y0 - reach).max(0.7),
        x1: (arena.x1 + reach).min(size - 0.7),
        y1: (arena.y1 + reach).min(size - 0.7),
    };
    let nx = (walk.width() / GRID_STEP).floor() as usize + 1;
    let ny = (walk.height() / GRID_STEP).floor() as usize + 1;
    let at = |i: usize, j: usize| Point {
        x: walk.x0 + i as f64 * GRID_STEP,
        y: walk.y0 + j as f64 * GRID_STEP,
    };
    let mut open = vec![false; nx * ny];
    let mut safe = vec![false; nx * ny];
    for j in 0..ny {
        for i in 0..nx {
            let p = at(i, j);
            open[j * nx + i] = walkable(map, p);
            safe[j * nx + i] = open[j * nx + i] && !hurt(p);
        }
    }
    // Multi-source Dijkstra from every safe cell, in integer thousandths of a tile.
    const STRAIGHT: u64 = (GRID_STEP * 1000.) as u64;
    const DIAGONAL: u64 = (GRID_STEP * 1000. * std::f64::consts::SQRT_2) as u64;
    let mut dist = vec![u64::MAX; nx * ny];
    let mut heap = std::collections::BinaryHeap::new();
    for (n, s) in safe.iter().enumerate() {
        if *s {
            dist[n] = 0;
            heap.push(std::cmp::Reverse((0_u64, n)));
        }
    }
    while let Some(std::cmp::Reverse((d, n))) = heap.pop() {
        if d > dist[n] {
            continue;
        }
        let (i, j) = ((n % nx) as i64, (n / nx) as i64);
        for (di, dj) in [
            (-1, -1),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        ] {
            let (a, b) = (i + di, j + dj);
            if a < 0 || b < 0 || a >= nx as i64 || b >= ny as i64 {
                continue;
            }
            let m = b as usize * nx + a as usize;
            if !open[m] {
                continue;
            }
            let next = d + if di != 0 && dj != 0 {
                DIAGONAL
            } else {
                STRAIGHT
            };
            if next < dist[m] {
                dist[m] = next;
                heap.push(std::cmp::Reverse((next, m)));
            }
        }
    }
    (0..ny)
        .flat_map(|j| (0..nx).map(move |i| (i, j)))
        .filter(|(i, j)| {
            let n = j * nx + i;
            open[n] && !safe[n] && arena.contains(at(*i, *j))
        })
        .find(|(i, j)| dist[j * nx + i] as f64 / 1000. > reach)
        .map(|(i, j)| at(i, j))
}

// ---------------------------------------------------------------------------------------------------------------
// Choosing a shape at the start of a cast
// ---------------------------------------------------------------------------------------------------------------

/// What the choice of a shape depends on.
pub struct Ctx<'a> {
    pub map: &'a Map,
    pub arena: Rect,
    pub boss: Point,
    /// Where the fight's living players stand.
    pub players: &'a [Point],
    /// The safe discs of the boss's lit places.
    pub lit: &'a [Shape],
    pub cast: f64,
}

/// A random walkable point of the arena, a tile in from its walls where it can be.
pub fn random_spot(ctx: &Ctx, rng: &mut dyn FnMut() -> f64) -> Point {
    let a = ctx.arena;
    let inset = 1_f64.min(a.width() / 4.).min(a.height() / 4.);
    for _ in 0..40 {
        let p = Point {
            x: a.x0 + inset + rng() * (a.width() - 2. * inset),
            y: a.y0 + inset + rng() * (a.height() - 2. * inset),
        };
        if walkable(ctx.map, p) {
            return p;
        }
    }
    a.centre()
}

fn pick(points: &[Point], rng: &mut dyn FnMut() -> f64) -> Option<Point> {
    (!points.is_empty())
        .then(|| points[((rng() * points.len() as f64) as usize).min(points.len() - 1)])
}

/// Turns a spec into the shapes of one cast.
pub fn resolve(spec: &ShapeSpec, ctx: &Ctx, rng: &mut dyn FnMut() -> f64) -> Vec<Shape> {
    match *spec {
        ShapeSpec::Circle { r, inner, at } => {
            let c = match at {
                At::Boss => ctx.boss,
                At::Target => pick(ctx.players, rng).unwrap_or(ctx.boss),
                At::Random => random_spot(ctx, rng),
            };
            vec![Shape::Circle {
                x: c.x,
                y: c.y,
                r,
                inner,
            }]
        }
        ShapeSpec::Cone { half_angle, length } => {
            let aim = pick(ctx.players, rng).map_or_else(
                || rng() * std::f64::consts::TAU,
                |p| (p.y - ctx.boss.y).atan2(p.x - ctx.boss.x),
            );
            vec![Shape::Cone {
                x: ctx.boss.x,
                y: ctx.boss.y,
                dir: aim,
                half: half_angle.to_radians(),
                length,
            }]
        }
        ShapeSpec::Lane { width } => {
            let aim = pick(ctx.players, rng).map_or_else(
                || rng() * std::f64::consts::TAU,
                |p| (p.y - ctx.boss.y).atan2(p.x - ctx.boss.x),
            );
            let reach = ctx.arena.diagonal();
            vec![Shape::Lane {
                a: ctx.boss,
                b: Point {
                    x: ctx.boss.x + aim.cos() * reach,
                    y: ctx.boss.y + aim.sin() * reach,
                },
                half: width / 2.,
            }]
        }
        ShapeSpec::Half { min_share } => vec![random_half(ctx, min_share, rng)],
        ShapeSpec::Arena => vec![Shape::Arena(ctx.arena)],
        ShapeSpec::Islands { count, r } => islands(ctx, count.max(1), r, rng),
        ShapeSpec::Lit => ctx.lit.to_vec(),
    }
}

/// The share of the arena (on a 16 by 16 sample) a half-plane covers.
fn half_share(arena: Rect, half: &Shape) -> f64 {
    let n = 16;
    let mut inside = 0;
    for j in 0..n {
        for i in 0..n {
            let p = Point {
                x: arena.x0 + (i as f64 + 0.5) / n as f64 * arena.width(),
                y: arena.y0 + (j as f64 + 0.5) / n as f64 * arena.height(),
            };
            if half.contains(p) {
                inside += 1;
            }
        }
    }
    inside as f64 / (n * n) as f64
}

/// A crease at a random angle through the arena. The hurt half is never more than `1 - min_share` of it.
fn random_half(ctx: &Ctx, min_share: f64, rng: &mut dyn FnMut() -> f64) -> Shape {
    let c = ctx.arena.centre();
    let reach = ctx.arena.diagonal() / 2.;
    let mut best = Shape::Half {
        x: c.x,
        y: c.y,
        nx: 1.,
        ny: 0.,
    };
    for _ in 0..60 {
        let angle = rng() * std::f64::consts::TAU;
        let offset = (rng() * 2. - 1.) * reach * 0.5;
        let (nx, ny) = (angle.cos(), angle.sin());
        let half = Shape::Half {
            x: c.x + nx * offset,
            y: c.y + ny * offset,
            nx,
            ny,
        };
        let share = half_share(ctx.arena, &half);
        // Both sides must be worth standing on and fighting from, and the hurt one a real threat.
        if share <= 1. - min_share && share >= min_share {
            return half;
        }
        best = half;
    }
    // No luck in sixty tries: halve the arena along a random line through its centre.
    if let Shape::Half { nx, ny, .. } = best {
        return Shape::Half {
            x: c.x,
            y: c.y,
            nx,
            ny,
        };
    }
    best
}

/// `count` safe discs of radius `r`: the first at random, each next at the walkable point farthest from the others,
/// retried until nobody in the arena is further from safety than the cast allows (or twenty tries, then the best).
fn islands(ctx: &Ctx, count: u32, r: f64, rng: &mut dyn FnMut() -> f64) -> Vec<Shape> {
    let a = ctx.arena;
    let mut cells = vec![];
    let mut y = a.y0 + 0.5;
    while y < a.y1 {
        let mut x = a.x0 + 0.5;
        while x < a.x1 {
            let p = Point { x, y };
            if walkable(ctx.map, p) {
                cells.push(p);
            }
            x += 1.;
        }
        y += 1.;
    }
    if cells.is_empty() {
        return vec![Shape::Circle {
            x: a.centre().x,
            y: a.centre().y,
            r,
            inner: 0.,
        }];
    }
    let mut best: Option<(usize, Vec<Shape>)> = None;
    for _ in 0..20 {
        let first = cells[((rng() * cells.len() as f64) as usize).min(cells.len() - 1)];
        let mut centres = vec![first];
        while (centres.len() as u32) < count {
            let next = cells
                .iter()
                .copied()
                .map(|p| {
                    let d = centres
                        .iter()
                        .map(|c| c.distance(p))
                        .fold(f64::INFINITY, f64::min);
                    (d + rng() * 0.3, p)
                })
                .max_by(|x, y| x.0.total_cmp(&y.0))
                .map(|(_, p)| p)
                .unwrap();
            centres.push(next);
        }
        let shapes: Vec<Shape> = centres
            .iter()
            .map(|c| Shape::Circle {
                x: c.x,
                y: c.y,
                r,
                inner: 0.,
            })
            .collect();
        let bad = first_unsafe_point(ctx.map, a, ctx.cast, &|p| {
            !shapes.iter().any(|s| s.contains(p))
        })
        .map_or(0, |_| 1);
        if bad == 0 {
            return shapes;
        }
        if best.as_ref().is_none_or(|(b, _)| bad < *b) {
            best = Some((bad, shapes));
        }
    }
    best.unwrap().1
}

// ---------------------------------------------------------------------------------------------------------------
// Checking a table
// ---------------------------------------------------------------------------------------------------------------

/// A wall's green gap is at least this wide (tiles), so a player and a friend fit through together.
pub const MIN_WALL_GAP: f64 = 2.;

/// The distance from the arena's centre the spokes' angular speed is measured at (docs/boss-mechanics.md, no. 11).
pub const SPOKE_REFERENCE_RADIUS: f64 = 8.;

/// Whether a boss's definition obeys the rules that can be checked without a map: the cast floors, positive
/// timings, the share limits. `Err` names the mechanic and the rule.
fn finite_points(points: &[[f64; 2]]) -> bool {
    !points.is_empty() && points.iter().flatten().all(|v| v.is_finite())
}

pub fn validate(kind: &str, def: &BossDef) -> Result<(), String> {
    let bad = |m: &Mechanic, why: &str| Err(format!("{kind} / {}: {why}", m.name));
    if def.mechanics.is_empty() {
        return Err(format!("{kind}: no mechanics"));
    }
    if let Some([x0, y0, x1, y1]) = def.arena
        && (def.inner_arena
            || ![x0, y0, x1, y1].iter().all(|v| v.is_finite())
            || x0 >= x1
            || y0 >= y1)
    {
        return Err(format!(
            "{kind}: arena bounds are invalid or conflict with inner_arena"
        ));
    }
    let eld_counts = [
        def.mechanics
            .iter()
            .filter(|m| matches!(m.block, Block::Crack(_)))
            .count(),
        def.mechanics
            .iter()
            .filter(|m| matches!(m.block, Block::Heat(_)))
            .count(),
        def.mechanics
            .iter()
            .filter(|m| matches!(m.block, Block::Seats(_)))
            .count(),
    ];
    if eld_counts.iter().any(|n| *n > 0) && eld_counts != [1, 1, 1] {
        return Err(format!(
            "{kind}: Eldmarr needs exactly one crack, heat and seats block"
        ));
    }
    let positive = |v: f64| v.is_finite() && v > 0.;
    for m in &def.mechanics {
        if m.name.trim().is_empty() {
            return Err(format!("{kind}: a mechanic has no name"));
        }
        if !(m.hp_min >= 0. && m.hp_min < m.hp_max && m.hp_max <= 1.) {
            return bad(m, "health window must satisfy 0 <= hp_min < hp_max <= 1");
        }
        match &m.block {
            Block::Zone(z) => {
                if !cast_is_long_enough(z.effect, z.cast) {
                    return bad(m, "cast is shorter than the floor for its effect");
                }
                if z.repeat == 0 || z.repeat > 4 {
                    return bad(m, "repeat must be 1 to 4");
                }
                if z.alternate && (z.repeat < 2 || !matches!(z.shape, ShapeSpec::Half { .. })) {
                    return bad(m, "alternating sides need a repeated half-room zone");
                }
                if !z.linger.is_finite()
                    || z.linger < 0.
                    || (z.linger > 0. && z.effect == Effect::Heavy)
                {
                    return bad(
                        m,
                        "linger must be nonnegative and cannot repeat a heavy hit",
                    );
                }
                // `every` runs from start to start, so a whole sequence (casts, echoes, lingering and gaps) fits.
                let rounds = z.repeat as f64;
                let length = rounds * (z.cast + z.echo.iter().sum::<f64>() + z.linger)
                    + (rounds - 1.) * z.repeat_gap;
                if !positive(z.every) || z.every <= length {
                    return bad(
                        m,
                        "every must exceed the whole sequence of casts, gaps and echoes",
                    );
                }
                if z.effect == Effect::Heavy && !(z.heavy > 0. && z.heavy <= 1.) {
                    return bad(m, "a heavy effect needs a share of health in (0, 1]");
                }
                if z.echo.iter().any(|d| !positive(*d)) {
                    return bad(m, "echo delays must be positive");
                }
                let islands = matches!(z.shape, ShapeSpec::Islands { .. } | ShapeSpec::Lit);
                if islands != (z.effect == Effect::KillOutside) {
                    return bad(
                        m,
                        "islands and lit places go with kill_outside, and only they do",
                    );
                }
                match z.shape {
                    ShapeSpec::Circle { r, inner, .. }
                        if !(positive(r) && inner >= 0. && inner < r) =>
                    {
                        return bad(m, "a circle needs 0 <= inner < r");
                    }
                    ShapeSpec::Cone { half_angle, length }
                        if !(positive(length) && half_angle > 0. && half_angle < 180.) =>
                    {
                        return bad(m, "a cone needs a half angle in (0, 180) and a length");
                    }
                    ShapeSpec::Lane { width } if !positive(width) => {
                        return bad(m, "a lane needs a width");
                    }
                    ShapeSpec::Half { min_share } if !(0.2..0.5).contains(&min_share) => {
                        return bad(
                            m,
                            "the safe half must be at least 0.2 and below 0.5 of the arena",
                        );
                    }
                    ShapeSpec::Islands { count, r } if count == 0 || !positive(r) => {
                        return bad(m, "islands need a count and a radius");
                    }
                    _ => {}
                }
            }
            Block::Shield(s) => {
                if s.steps.is_empty()
                    || s.steps.iter().any(|t| {
                        !(t.hp > 0. && (t.hp < 1. || (s.ordered.is_some() && t.hp == 1.)))
                            || t.count == 0
                            || t.tag.is_empty()
                    })
                {
                    return bad(
                        m,
                        "a shield needs steps with hp in (0, 1), a tag and a count",
                    );
                }
                if let Some(o) = &s.ordered
                    && (!o.deadline.is_finite()
                        || o.deadline < HEAVY_HIT_MIN_CAST
                        || !o.heavy.is_finite()
                        || o.heavy <= 0.
                        || o.heavy > 1.
                        || s.steps.iter().any(|t| !t.still || t.count < 2))
                {
                    return bad(
                        m,
                        "ordered shields need a full heavy-hit warning, heavy in (0, 1], and stationary numbered helpers",
                    );
                }
                if s.steps.windows(2).any(|w| w[0].hp <= w[1].hp) {
                    return bad(m, "shield steps go from high health to low");
                }
                if !(s.heal_per_s >= 0. && s.heal_per_s < 0.2) {
                    return bad(m, "heal_per_s must be in [0, 0.2)");
                }
            }
            Block::Static(t) => {
                if t.limit < 2 || t.warn_at == 0 || t.warn_at >= t.limit {
                    return bad(
                        m,
                        "static needs a limit of at least 2 and a warning below it",
                    );
                }
                if t.per_hit == 0 || t.per_hit >= t.limit || !positive(t.r) {
                    return bad(
                        m,
                        "static needs charges per hit below the limit and a radius",
                    );
                }
                if t.rods.len() < 2
                    || !positive(t.rod_r)
                    || !positive(t.dark)
                    || !t.immune.is_finite()
                    || t.immune < 0.
                {
                    return bad(
                        m,
                        "static needs at least two rods (not everyone fits on one), a rod radius and a dark time",
                    );
                }
            }
            Block::Adds(a) => {
                if a.tag.is_empty() || a.count == 0 || !positive(a.every) {
                    return bad(m, "adds need a tag, a count and an interval");
                }
                if let Some(b) = &a.bloom
                    && !(positive(b.after) && b.heal >= 0. && b.heal < 1.)
                {
                    return bad(m, "a bloom needs a time and a heal share below 1");
                }
            }
            Block::Mark(k) => {
                if k.cast < MARK_MIN_CAST || !k.cast.is_finite() {
                    return bad(
                        m,
                        "a mark resolves lethally, so its cast is at least the instant-kill floor",
                    );
                }
                if k.count == 0 || k.count as usize > MAX_MARKED {
                    return bad(m, "a mark marks 1 to MAX_MARKED players");
                }
                if !positive(k.every) || k.every <= k.cast || k.waves == 0 || k.waves > 3 {
                    return bad(m, "every must exceed the cast; waves 1 to 3");
                }
                if k.waves > 1 && !positive(k.wave_gap) {
                    return bad(m, "waves need a gap");
                }
                if !k.linger.is_finite()
                    || k.linger < 0.
                    || (k.linger > 0. && !matches!(k.effect, MarkEffect::Burst { .. }))
                {
                    return bad(
                        m,
                        "only burst marks may leave a nonnegative puddle duration",
                    );
                }
                match k.effect {
                    MarkEffect::Burst { r } if !positive(r) => {
                        return bad(m, "a burst needs a radius");
                    }
                    MarkEffect::Beam { bounces, width } if bounces > 4 || !positive(width) => {
                        return bad(m, "a beam needs a width and at most 4 bounces");
                    }
                    _ => {}
                }
            }
            Block::Sweep(s) => match &s.kind {
                SweepKind::Walls {
                    warn,
                    speed,
                    thickness,
                    gap,
                    walls,
                } => {
                    if *warn < SWEEP_MIN_WARN || !warn.is_finite() {
                        return bad(
                            m,
                            "a wall shows its dashed line for at least SWEEP_MIN_WARN",
                        );
                    }
                    if !(positive(*speed) && positive(*thickness) && *gap >= MIN_WALL_GAP)
                        || walls.is_empty()
                    {
                        return bad(
                            m,
                            "a wall needs a speed, a thickness, a gap a player fits through, and walls",
                        );
                    }
                    if !positive(s.every) {
                        return bad(m, "walls need an interval");
                    }
                }
                SweepKind::Spokes {
                    count,
                    width,
                    deg_per_s,
                    reverse_every,
                    reverse_warn,
                    length,
                } => {
                    if *count == 0
                        || !positive(*width)
                        || !positive(*length)
                        || !positive(*deg_per_s)
                    {
                        return bad(m, "spokes need a count, a width, a length and a speed");
                    }
                    if deg_per_s.to_radians() * SPOKE_REFERENCE_RADIUS >= SLOWEST_PLAYER_SPEED {
                        return bad(
                            m,
                            "the gap between spokes must be slower than the slowest player 8 tiles out",
                        );
                    }
                    if *reverse_every > 0. && *reverse_warn < SPOKE_REVERSE_MIN_WARN {
                        return bad(
                            m,
                            "a reversal is announced for at least SPOKE_REVERSE_MIN_WARN",
                        );
                    }
                }
            },
            Block::Break(b) if b.enrage || b.overload => {
                if b.enrage && b.overload {
                    return bad(m, "a burst phase either enrages or overloads, not both");
                }
                if b.overload
                    && (!cast_is_long_enough(Effect::Kill, b.cast)
                        || !def
                            .mechanics
                            .iter()
                            .any(|o| matches!(o.block, Block::Static(_))))
                {
                    return bad(
                        m,
                        "an overload kills a hero, so its window is at least the floor, and the boss needs a static block",
                    );
                }
                if !b.at.is_some_and(|at| at > 0. && at < 1.)
                    || !positive(b.cast)
                    || !(b.bar > 0. && b.bar < 1.)
                    || !(b.stun >= 0. && b.vulnerable >= 0. && b.vulnerable <= 2.)
                {
                    return bad(
                        m,
                        "a burst phase needs a health share in (0, 1), a window, a bar share in (0, 1) and a non-negative stun",
                    );
                }
            }
            Block::Break(b) => {
                if !cast_is_long_enough(Effect::Kill, b.cast)
                    || !positive(b.every)
                    || b.every <= b.cast
                {
                    return bad(
                        m,
                        "a break's failure kills, so its cast is at least the floor and shorter than every",
                    );
                }
                if !(b.bar > 0. && b.bar < 1.)
                    || !positive(b.stun)
                    || !(b.vulnerable >= 0. && b.vulnerable <= 2.)
                {
                    return bad(
                        m,
                        "a break needs a bar share in (0, 1), a stun and a vulnerability",
                    );
                }
            }
            Block::Stasis(s) => {
                if s.orbs == 0
                    || !positive(s.speed)
                    || !positive(s.life)
                    || !positive(s.every)
                    || s.tag.is_empty()
                    || !positive(s.hold)
                {
                    return bad(
                        m,
                        "stasis needs orbs, a speed, a life, an interval, a cocoon tag and a hold time",
                    );
                }
            }
            Block::Split(s) => {
                if !(s.hp > 0. && s.hp < 1.)
                    || s.tag.is_empty()
                    || !positive(s.revive_after)
                    || s.survivor_bonus < 0.
                    || s.bridge < 0.
                    || !(0. ..1.).contains(&s.bridge_hit)
                    || !(0. ..1.).contains(&s.merge_hp)
                    || !(s.merge_defense > 0. && s.merge_defense <= 1.)
                {
                    return bad(
                        m,
                        "a split needs hp in (0, 1), a partner tag, a revive time, a merge health in [0, 1) and a merge defense in (0, 1]",
                    );
                }
            }
            Block::Hold(h) => {
                if h.points.is_empty()
                    || !positive(h.r)
                    || !positive(h.hold_for)
                    || !positive(h.lit_for)
                    || h.snuff_every < 0.
                {
                    return bad(
                        m,
                        "a hold needs points, a radius, a hold time and a lit time",
                    );
                }
            }
            Block::Tether(t) => {
                if !cast_is_long_enough(Effect::Kill, t.cast)
                    || !positive(t.duration)
                    || !positive(t.every)
                    || t.every <= t.cast + t.duration
                    || !positive(t.first)
                    || !positive(t.leash)
                    || !positive(t.r)
                    || !positive(t.hold)
                    || t.hold * 5. > t.duration
                    || !(t.heavy > 0. && t.heavy <= 1.)
                    || t.points.len() != 5
                    || !finite_points(&t.points)
                {
                    return bad(
                        m,
                        "tether needs five anvils, a fair warning, positive leash/hold, and time to break all five chains",
                    );
                }
            }
            Block::Gust(g) => {
                if !cast_is_long_enough(Effect::Kill, g.cast)
                    || !positive(g.first)
                    || !positive(g.every)
                    || g.every <= g.cast
                    || !positive(g.push)
                    || !positive(g.r)
                    || !positive(g.rim)
                    || g.capacity == 0
                    || g.capacity > 10
                    || g.points.len() != 4
                    || g.points.len() * g.capacity < 10
                    || !finite_points(&g.points)
                {
                    return bad(
                        m,
                        "gust needs a lethal warning and at least ten shelter places with positive radii and push",
                    );
                }
            }
            Block::Soak(t) => {
                if !cast_is_long_enough(Effect::Kill, t.cast)
                    || !positive(t.first)
                    || !positive(t.every)
                    || t.every <= t.cast
                    || !positive(t.r)
                    || t.need == 0
                    || t.need > 10
                    || t.points.len() != 3
                    || t.need * t.points.len() > 10
                    || t.points.len() < 2
                    || !(t.heavy > 0. && t.heavy <= 1.)
                    || !finite_points(&t.points)
                    || t.points.iter().enumerate().any(|(i, a)| {
                        t.points[..i]
                            .iter()
                            .any(|b| (a[0] - b[0]).hypot(a[1] - b[1]) <= 2. * t.r)
                    })
                {
                    return bad(
                        m,
                        "soak needs separate circles, a lethal warning and a count a ten-fighter crew can meet",
                    );
                }
            }
            Block::Valves(v) => {
                if v.at != [0.7, 0.4]
                    || v.cast < 5.
                    || v.duration < v.hold
                    || v.hold <= 0.
                    || v.points.len() != 2
                    || !finite_points(&v.points)
                    || !positive(v.r)
                    || v.need == 0
                    || v.need * 2 > 10
                {
                    return bad(
                        m,
                        "valves need two counted stations, 70/40 thresholds and time for continuous holds",
                    );
                }
            }
            Block::Relay(r) => {
                if r.cast < 5.
                    || r.count != 3
                    || r.fuse < 5.
                    || r.immunity <= 0.
                    || r.immunity >= r.fuse
                    || r.duration <= r.fuse
                    || r.every <= r.cast + r.duration
                    || !positive(r.touch)
                    || !positive(r.blast)
                    || !positive(r.first)
                {
                    return bad(
                        m,
                        "relay needs three brands, fair fuses, positive touch/blast and non-overlapping casts",
                    );
                }
            }
            Block::Grid(g) => {
                if g.cast < 5.
                    || !positive(g.first)
                    || !positive(g.bpm)
                    || g.bpm > 150.
                    || g.every <= g.cast + 240. / g.bpm
                    || !(g.heavy > 0. && g.heavy <= 1.)
                {
                    return bad(
                        m,
                        "grid needs a full cue and four readable beats no faster than 150 BPM",
                    );
                }
            }
            Block::Carry(c) => {
                if c.points.len() != 10
                    || !finite_points(&c.points)
                    || c.need != 6
                    || !positive(c.r)
                    || !positive(c.throw_r)
                    || !positive(c.window)
                    || !positive(c.quenched)
                    || !(c.speed > 0. && c.speed < 1.)
                {
                    return bad(
                        m,
                        "carry needs ten wells, six throws and positive pickup/window/quench/speed rules",
                    );
                }
            }
            Block::Reflect(r) => {
                if r.cast < 5.
                    || !positive(r.first)
                    || !positive(r.duration)
                    || r.every <= r.cast + r.duration
                    || !(r.heavy > 0. && r.heavy <= 1.)
                {
                    return bad(
                        m,
                        "reflect needs a full warning, a finite pause and a heavy hit",
                    );
                }
            }
            Block::Crack(c) => {
                if !positive(c.stand)
                    || !positive(c.cell)
                    || !positive(c.lava)
                    || !cast_is_long_enough(Effect::Kill, c.cast)
                {
                    return bad(
                        m,
                        "crack needs finite dwell/cell/lava and a full lethal warning",
                    );
                }
            }
            Block::Heat(h) => {
                if h.points.len() != 4
                    || !finite_points(&h.points)
                    || h.capacity != 3
                    || !positive(h.fill)
                    || !positive(h.cool)
                    || !positive(h.r)
                    || !positive(h.blast)
                    || !positive(h.move_every)
                    || h.move_every < 10.
                    || !cast_is_long_enough(Effect::Kill, h.cast)
                {
                    return bad(
                        m,
                        "heat needs four three-person wells and a full detonation warning",
                    );
                }
            }
            Block::Seats(s) => {
                if s.points.len() != 10
                    || !finite_points(&s.points)
                    || !positive(s.r)
                    || !positive(s.first)
                    || !positive(s.every)
                    || s.every <= s.cast
                    || !cast_is_long_enough(Effect::KillOutside, s.cast)
                    || s.points.iter().enumerate().any(|(i, a)| {
                        s.points[..i]
                            .iter()
                            .any(|b| (a[0] - b[0]).hypot(a[1] - b[1]) <= 2. * s.r)
                    })
                {
                    return bad(
                        m,
                        "seats need ten separate one-person plates and a full lethal warning",
                    );
                }
            }
            Block::Gaze(g) => {
                if !cast_is_long_enough(Effect::Kill, g.cast)
                    || !positive(g.every)
                    || g.every <= g.cast
                {
                    return bad(
                        m,
                        "a gaze kills, so its cast is at least the floor and shorter than every",
                    );
                }
                if g.cover.iter().any(|c| !positive(c.r))
                    || g.regrow < 0.
                    || g.sweep < 0.
                    || g.beam < 0.
                {
                    return bad(
                        m,
                        "cover needs a radius; regrow, sweep and beam cannot be negative",
                    );
                }
                if g.sweep > 0. && !(g.beam > 0. && g.beam < 90.) {
                    return bad(
                        m,
                        "a turning gaze needs a beam half-angle in (0, 90) degrees",
                    );
                }
            }
        }
    }
    Ok(())
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

    // --- the engine's pure half ---------------------------------------------------------------------------------

    fn open_map(size: usize) -> Map {
        Map {
            size: size as _,
            objects: vec![],
            rooms: vec![],
            city: None,
            camps: vec![],
            ..Map::default()
        }
    }
    fn lcg(seed: u64) -> impl FnMut() -> f64 {
        let mut state = seed;
        move || {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            (state >> 11) as f64 / (1u64 << 53) as f64
        }
    }
    fn parse(json: &str) -> BossDef {
        serde_json::from_str(json).expect("parses")
    }
    const EVERY_BLOCK: &str = r#"{"mechanics":[
        {"name":"Toll","block":"zone","shape":{"kind":"circle","r":8},"effect":"kill","cast":5,"every":25},
        {"name":"Flood","block":"zone","shape":{"kind":"islands","count":3,"r":2.5},"effect":"kill_outside","cast":5,"every":35,"repeat":2,"repeat_gap":1,"linger":4},
        {"name":"Lance","block":"zone","shape":{"kind":"lane","width":2},"effect":"kill","cast":5,"every":15,"echo":[3]},
        {"name":"Chorus","block":"shield","steps":[{"hp":0.66,"tag":"singer","count":4},{"hp":0.33,"tag":"singer","count":6}],"heal_per_s":0.02},
        {"name":"Seeds","block":"adds","tag":"seed","count":3,"every":30,"scatter":true,"still":true,"bloom":{"after":12,"heal":0.04,"then":"treant"}},
        {"name":"Downpour","block":"mark","count":3,"every":25,"cast":5,"effect":{"kind":"burst","r":4},"waves":2,"wave_gap":3},
        {"name":"Bramble","block":"sweep","every":20,"kind":{"shape":"walls","warn":4,"speed":4,"thickness":3,"gap":4,"walls":[{"from":"west","gap":"low"},{"from":"east","gap":"high"}]}},
        {"name":"Spokes","block":"sweep","kind":{"shape":"spokes","count":3,"width":1.6,"deg_per_s":20,"reverse_every":12,"reverse_warn":2,"length":16}},
        {"name":"Dirge","block":"break","cast":8,"every":30,"bar":0.05,"stun":6,"vulnerable":0.3},
        {"name":"Amber","block":"stasis","every":25,"orbs":2,"speed":3,"life":10,"tag":"cocoon","hold":10},
        {"name":"Twin Suns","block":"split","hp":0.6,"tag":"cinder","revive_after":10,"survivor_bonus":0.5,"bridge":1},
        {"name":"Night","block":"hold","points":[[10,10],[20,10]],"r":2.5,"hold_for":3,"lit_for":30,"snuff_every":12},
        {"name":"Gaze","block":"gaze","cast":5,"every":30,"cover":[{"x":5,"y":5,"r":1}],"regrow":45}
    ]}"#;

    #[test]
    fn every_block_parses_and_obeys_the_rules() {
        let def = parse(EVERY_BLOCK);
        assert_eq!(def.mechanics.len(), 13);
        validate("everything", &def).unwrap();
        // The windows default to the whole fight.
        assert!(def.mechanics[0].active_at(1.) && def.mechanics[0].active_at(0.01));
    }

    #[test]
    fn the_shipped_table_is_valid() {
        // `shipped()` validates every entry and would panic.
        let table = shipped();
        for (kind, def) in &table {
            validate(kind, def).unwrap();
        }
    }

    #[test]
    fn a_typo_in_the_data_is_an_error_not_a_silent_default() {
        for bad in [
            r#"{"mechanics":[{"name":"x","block":"zone","shape":{"kind":"circle","r":8},"effect":"kill","cast":5,"every":25,"casst":6}]}"#,
            r#"{"mechanics":[{"name":"x","block":"zone","shape":{"kind":"circle","rr":8},"effect":"kill","cast":5,"every":25}]}"#,
            r#"{"mechanics":[{"name":"x","block":"zone","shape":{"kind":"circle","r":8},"effect":"smite","cast":5,"every":25}]}"#,
            r#"{"mechanics":[{"name":"x","block":"wibble"}]}"#,
        ] {
            assert!(serde_json::from_str::<BossDef>(bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn the_rules_of_the_design_doc_are_enforced_on_the_data() {
        let zone = |effect: &str, shape: &str, cast: f64, extra: &str| {
            parse(&format!(
                r#"{{"mechanics":[{{"name":"z","block":"zone","shape":{shape},"effect":"{effect}","cast":{cast},"every":40{extra}}}]}}"#
            ))
        };
        let circle = r#"{"kind":"circle","r":6}"#;
        assert!(validate("b", &zone("kill", circle, 5., "")).is_ok());
        assert!(
            validate("b", &zone("kill", circle, 4.9, "")).is_err(),
            "an instant kill needs 5 s"
        );
        assert!(validate("b", &zone("heavy", circle, 3., r#","heavy":0.5"#)).is_ok());
        assert!(
            validate("b", &zone("heavy", circle, 2.9, r#","heavy":0.5"#)).is_err(),
            "a heavy hit needs 3 s"
        );
        assert!(
            validate("b", &zone("heavy", circle, 3., "")).is_err(),
            "a heavy hit names its share"
        );
        assert!(validate("b", &zone("kill", circle, 5., r#","echo":[0]"#)).is_err());
        assert!(
            validate("b", &zone("kill_outside", circle, 5., "")).is_err(),
            "kill_outside needs somewhere to stand"
        );
        let islands = r#"{"kind":"islands","count":3,"r":2.5}"#;
        assert!(validate("b", &zone("kill_outside", islands, 5., "")).is_ok());
        assert!(
            validate("b", &zone("kill", islands, 5., "")).is_err(),
            "islands are where you must stand"
        );
        assert!(
            validate(
                "b",
                &zone("kill", r#"{"kind":"half","min_share":0.1}"#, 5., "")
            )
            .is_err()
        );
        assert!(
            validate(
                "b",
                &zone("kill", r#"{"kind":"half","min_share":0.4}"#, 5., "")
            )
            .is_ok()
        );
        let slow = EVERY_BLOCK.replace(
            r#""cast":5,"effect":{"kind":"burst""#,
            r#""cast":4,"effect":{"kind":"burst""#,
        );
        assert!(
            validate("b", &parse(&slow)).is_err(),
            "a mark's burst is lethal, so 5 s"
        );
        let many = EVERY_BLOCK.replace(
            r#""count":3,"every":25,"cast":5"#,
            r#""count":4,"every":25,"cast":5"#,
        );
        assert!(
            validate("b", &parse(&many)).is_err(),
            "never more than MAX_MARKED"
        );
        let quick = EVERY_BLOCK.replace(r#""warn":4,"speed":4"#, r#""warn":3,"speed":4"#);
        assert!(
            validate("b", &parse(&quick)).is_err(),
            "walls are shown for 4 s"
        );
        let tight = EVERY_BLOCK.replace(r#""gap":4,"walls""#, r#""gap":1,"walls""#);
        assert!(
            validate("b", &parse(&tight)).is_err(),
            "a gap two players fit through"
        );
        let fast = EVERY_BLOCK.replace(r#""deg_per_s":20"#, r#""deg_per_s":45"#);
        assert!(
            validate("b", &parse(&fast)).is_err(),
            "the gap between spokes must be walkable"
        );
        let silent = EVERY_BLOCK.replace(r#""reverse_warn":2"#, r#""reverse_warn":1"#);
        assert!(
            validate("b", &parse(&silent)).is_err(),
            "a reversal is announced for 2 s"
        );
        let wail = EVERY_BLOCK.replace(
            r#""cast":8,"every":30,"bar""#,
            r#""cast":4,"every":30,"bar""#,
        );
        assert!(
            validate("b", &parse(&wail)).is_err(),
            "a break that fails kills everyone"
        );
        let blink = EVERY_BLOCK.replace(
            r#""cast":5,"every":30,"cover""#,
            r#""cast":4,"every":30,"cover""#,
        );
        assert!(
            validate("b", &parse(&blink)).is_err(),
            "a gaze kills, so 5 s"
        );
        let order = EVERY_BLOCK.replace(
            r#"{"hp":0.33,"tag":"singer","count":6}"#,
            r#"{"hp":0.9,"tag":"singer","count":6}"#,
        );
        assert!(
            validate("b", &parse(&order)).is_err(),
            "shield steps go from high health to low"
        );
        let window = EVERY_BLOCK.replacen(
            r#""name":"Toll","#,
            r#""name":"Toll","hp_max":0.2,"hp_min":0.5,"#,
            1,
        );
        assert!(validate("b", &parse(&window)).is_err());
        assert!(
            validate(
                "b",
                &BossDef {
                    mechanics: vec![],
                    inner_arena: false,
                    arena: None
                }
            )
            .is_err()
        );
    }

    #[test]
    fn shapes_contain_what_they_cover() {
        let at = |x: f64, y: f64| Point { x, y };
        let disc = Shape::Circle {
            x: 10.,
            y: 10.,
            r: 3.,
            inner: 0.,
        };
        assert!(disc.contains(at(12., 10.)) && !disc.contains(at(13.5, 10.)));
        let ring = Shape::Circle {
            x: 10.,
            y: 10.,
            r: 5.,
            inner: 3.,
        };
        assert!(
            ring.contains(at(14., 10.))
                && !ring.contains(at(11., 10.))
                && !ring.contains(at(16., 10.))
        );
        // A cone pointing west (angle pi) must work across the wrap of atan2.
        let cone = Shape::Cone {
            x: 10.,
            y: 10.,
            dir: std::f64::consts::PI,
            half: 0.5,
            length: 8.,
        };
        assert!(
            cone.contains(at(4., 10.)) && cone.contains(at(4., 10.5)) && cone.contains(at(4., 9.5))
        );
        assert!(
            !cone.contains(at(16., 10.))
                && !cone.contains(at(1., 10.))
                && !cone.contains(at(5., 14.))
        );
        let lane = Shape::Lane {
            a: at(0., 5.),
            b: at(20., 5.),
            half: 1.,
        };
        assert!(
            lane.contains(at(10., 5.9))
                && !lane.contains(at(10., 6.1))
                && !lane.contains(at(25., 5.))
        );
        let half = Shape::Half {
            x: 10.,
            y: 10.,
            nx: 1.,
            ny: 0.,
        };
        assert!(half.contains(at(11., 0.)) && !half.contains(at(9., 0.)));
        let arena = Shape::Arena(Rect {
            x0: 2.,
            y0: 2.,
            x1: 8.,
            y1: 8.,
        });
        assert!(arena.contains(at(5., 5.)) && !arena.contains(at(9., 5.)));
    }

    #[test]
    fn kill_outside_hurts_exactly_those_outside() {
        let safe = [Shape::Circle {
            x: 10.,
            y: 10.,
            r: 2.,
            inner: 0.,
        }];
        let (inside, outside) = (Point { x: 10., y: 11. }, Point { x: 14., y: 10. });
        assert!(
            !hurts(Effect::KillOutside, &safe, inside)
                && hurts(Effect::KillOutside, &safe, outside)
        );
        assert!(hurts(Effect::Kill, &safe, inside) && !hurts(Effect::Kill, &safe, outside));
        assert!(hurts(Effect::Heavy, &safe, inside) && !hurts(Effect::Heavy, &safe, outside));
    }

    #[test]
    fn a_beam_bounces_off_the_walls_the_stated_number_of_times() {
        let arena = Rect {
            x0: 0.,
            y0: 0.,
            x1: 10.,
            y1: 10.,
        };
        let path = beam_path(Point { x: 5., y: 5. }, Point { x: 9., y: 5. }, arena, 2);
        assert_eq!(path.len(), 4);
        let xs: Vec<f64> = path.iter().map(|p| p.x).collect();
        assert_eq!(xs, vec![5., 10., 0., 10.]);
        assert!(path.iter().all(|p| (p.y - 5.).abs() < 1e-9));
        // A diagonal ray reflects off both axes in turn and stays inside the arena.
        let diag = beam_path(Point { x: 2., y: 3. }, Point { x: 6., y: 5. }, arena, 3);
        assert_eq!(diag.len(), 5);
        assert!(diag.iter().all(|p| arena.contains(*p)));
        for w in diag.windows(2).skip(1) {
            let on_wall = |p: Point| {
                p.x.abs() < 1e-9
                    || (p.x - 10.).abs() < 1e-9
                    || p.y.abs() < 1e-9
                    || (p.y - 10.).abs() < 1e-9
            };
            assert!(on_wall(w[0]) && on_wall(w[1]));
        }
        // No bounces is one straight segment; a degenerate aim still gives a path.
        assert_eq!(
            beam_path(Point { x: 5., y: 5. }, Point { x: 5., y: 5. }, arena, 0).len(),
            2
        );
    }

    #[test]
    fn the_arena_is_the_room_the_boss_stands_in() {
        let mut map = open_map(100);
        map.rooms = vec![[10., 10., 20., 20.], [50., 50., 70., 60.]];
        let room = arena_for(&map, Point { x: 55., y: 55. });
        assert_eq!((room.x0, room.y0, room.x1, room.y1), (50., 50., 70., 60.));
        // Nearest room when the boss stands in a corridor.
        let near = arena_for(&map, Point { x: 24., y: 15. });
        assert_eq!(near.x0, 10.);
        let whole = arena_for(&open_map(100), Point { x: 5., y: 5. });
        assert_eq!((whole.x0, whole.x1), (0.7, 99.3));
    }

    #[test]
    fn a_ring_as_big_as_the_room_can_still_be_escaped_through_the_door_but_not_a_slow_one() {
        // A 20 by 20 arena, a lethal disc of radius 12 in its middle: the middle is 12 tiles from safety.
        let map = open_map(60);
        let arena = Rect {
            x0: 20.,
            y0: 20.,
            x1: 40.,
            y1: 40.,
        };
        let hurt = |p: Point| p.distance(arena.centre()) <= 12.;
        assert_eq!(
            first_unsafe_point(&map, arena, 5., &hurt),
            None,
            "15.6 tiles of running allowed"
        );
        assert!(
            first_unsafe_point(&map, arena, 3., &hurt).is_some(),
            "9.36 tiles are not enough"
        );
        // Walls that the walkers cannot pass count: seal the arena in and the disc becomes a trap.
        let mut sealed = open_map(60);
        sealed.objects = vec![
            crate::model::Obstacle {
                x: 30.,
                y: 19.,
                width: 24.,
                depth: 1.,
                r: 0.,
            },
            crate::model::Obstacle {
                x: 30.,
                y: 41.,
                width: 24.,
                depth: 1.,
                r: 0.,
            },
            crate::model::Obstacle {
                x: 18.,
                y: 30.,
                width: 1.,
                depth: 24.,
                r: 0.,
            },
            crate::model::Obstacle {
                x: 42.,
                y: 30.,
                width: 1.,
                depth: 24.,
                r: 0.,
            },
        ];
        let everywhere = |p: Point| p.distance(arena.centre()) <= 15.;
        assert!(
            first_unsafe_point(&sealed, arena, 5., &everywhere).is_some(),
            "walled in, with the whole box lethal"
        );
        assert_eq!(
            first_unsafe_point(&open_map(60), arena, 5., &everywhere),
            None,
            "but the same ring is fine in the open"
        );
    }

    #[test]
    fn islands_always_leave_everyone_within_reach_of_one() {
        let map = open_map(60);
        let arena = Rect {
            x0: 20.,
            y0: 20.,
            x1: 44.,
            y1: 40.,
        };
        for seed in 0..20 {
            let mut rng = lcg(seed);
            let ctx = Ctx {
                map: &map,
                arena,
                boss: arena.centre(),
                players: &[],
                lit: &[],
                cast: 5.,
            };
            let shapes = resolve(&ShapeSpec::Islands { count: 3, r: 2.5 }, &ctx, &mut rng);
            assert_eq!(shapes.len(), 3);
            assert_eq!(
                first_unsafe_point(&map, arena, 5., &|p| hurts(Effect::KillOutside, &shapes, p)),
                None,
                "seed {seed}"
            );
            for s in &shapes {
                let Shape::Circle { x, y, .. } = s else {
                    panic!()
                };
                assert!(arena.contains(Point { x: *x, y: *y }));
            }
        }
    }

    #[test]
    fn a_half_never_takes_more_of_the_arena_than_the_rule_allows() {
        let map = open_map(60);
        let arena = Rect {
            x0: 20.,
            y0: 20.,
            x1: 44.,
            y1: 40.,
        };
        for seed in 0..50 {
            let mut rng = lcg(seed);
            let ctx = Ctx {
                map: &map,
                arena,
                boss: arena.centre(),
                players: &[],
                lit: &[],
                cast: 5.,
            };
            let shapes = resolve(&ShapeSpec::Half { min_share: 0.4 }, &ctx, &mut rng);
            let share = half_share(arena, &shapes[0]);
            assert!(
                (0.2 - 1e-9..=0.6 + 1e-9).contains(&share),
                "seed {seed}: {share}"
            );
        }
    }

    #[test]
    fn shapes_resolve_without_a_player_and_follow_one_when_there_is() {
        let map = open_map(60);
        let arena = Rect {
            x0: 20.,
            y0: 20.,
            x1: 44.,
            y1: 40.,
        };
        let boss = arena.centre();
        let player = Point { x: 40., y: 22. };
        let mut rng = lcg(1);
        let none = Ctx {
            map: &map,
            arena,
            boss,
            players: &[],
            lit: &[],
            cast: 5.,
        };
        for spec in [
            ShapeSpec::Cone {
                half_angle: 30.,
                length: 10.,
            },
            ShapeSpec::Lane { width: 2. },
            ShapeSpec::Circle {
                r: 3.,
                inner: 0.,
                at: At::Target,
            },
            ShapeSpec::Circle {
                r: 3.,
                inner: 0.,
                at: At::Random,
            },
            ShapeSpec::Arena,
            ShapeSpec::Lit,
        ] {
            let _ = resolve(&spec, &none, &mut rng);
        }
        let with = Ctx {
            map: &map,
            arena,
            boss,
            players: &[player],
            lit: &[],
            cast: 5.,
        };
        let lane = resolve(&ShapeSpec::Lane { width: 2. }, &with, &mut rng);
        assert!(
            lane[0].contains(player),
            "a lane runs through the player it aims at"
        );
        let cone = resolve(
            &ShapeSpec::Cone {
                half_angle: 20.,
                length: 30.,
            },
            &with,
            &mut rng,
        );
        assert!(cone[0].contains(player));
        let on_target = resolve(
            &ShapeSpec::Circle {
                r: 3.,
                inner: 0.,
                at: At::Target,
            },
            &with,
            &mut rng,
        );
        assert!(on_target[0].contains(player));
        let lit = [Shape::Circle {
            x: 25.,
            y: 25.,
            r: 2.,
            inner: 0.,
        }];
        let ctx = Ctx { lit: &lit, ..with };
        assert_eq!(resolve(&ShapeSpec::Lit, &ctx, &mut rng), lit.to_vec());
    }
}
