use crate::{
    items::*,
    model::*,
    skills::{self, BuffKind, Effect},
    store::Store,
};
use serde::Serialize;
use serde_json::{Value, json};
use std::collections::BTreeMap;
use tokio::sync::{mpsc, oneshot, watch};

mod ambient;
#[cfg(test)]
mod cathedral_tests;
mod chime;
mod consumables;
mod debug;
#[cfg(test)]
mod deep_tests;
mod escort;
mod hold;
mod instances;
mod mercs;
#[cfg(test)]
mod nacre_tests;
mod partyxp;
mod pursuit;
mod ranged;
#[cfg(test)]
mod resource_tests;
mod resources;
mod rolls;
#[cfg(test)]
mod sky_tests;
mod social;
mod travel;
#[cfg(test)]
mod vault_tests;
#[cfg(test)]
mod wyrd_tests;

pub type Peer = mpsc::Sender<Value>;
const KING_SPAWN_MIN: f64 = 300.;
const KING_SPAWN_MAX: f64 = 600.;
const PLAYER_RADIUS: f64 = 0.3;
/// Every enemy rolls its level within this distance of its kind's default level.
pub const LEVEL_SPREAD: i32 = 2;
/// Health and damage change by this fraction per level from the default; gold changes by 10%. XP does not scale
/// this way: an enemy pays `enemy_xp(level)`, set by its own level alone.
const LEVEL_HP_DAMAGE: f64 = 0.12;
/// Fights ran too fast, so every hit a player lands and every hit a player takes is cut to this share.
const DAMAGE_DEALT_SCALE: f64 = 0.25;
const DAMAGE_TAKEN_SCALE: f64 = 0.25;
/// A player cannot take another portal for this long after arriving. Arrival points sit outside every gate, so this only
/// guards against bouncing; it must stay below the walk from an arrival point to its gate (about 0.65 s).
const PORTAL_DELAY: f64 = 0.5;
/// Who is joining: an anonymous guest (a server-issued key, or a look for a new character) or a logged-in account
/// (a character it owns, or a look for a new one). The account id comes from a checked login session.
pub enum Identity {
    Guest {
        token: Option<String>,
        look: Option<Look>,
    },
    Account {
        id: String,
        /// The login is a game master's (`Account::is_gm`): it may hold one extra, administrator character.
        gm: bool,
        character: Option<String>,
        look: Option<Look>,
    },
}
/// Ordinary characters one account may hold. A game master's account has one more slot, for the administrator character.
pub const MAX_ACCOUNT_CHARACTERS: usize = 5;
// A Join carries a whole Look and is sent once per connection, so boxing it would only add noise.
#[allow(clippy::large_enum_variant)]
pub enum Command {
    Join {
        session: u64,
        identity: Identity,
        peer: Peer,
        reply: oneshot::Sender<Result<Value, String>>,
    },
    Message {
        session: u64,
        message: ClientMessage,
    },
    Leave {
        session: u64,
    },
    Shutdown {
        reply: oneshot::Sender<()>,
    },
}

struct Player {
    character: Character,
    peer: Peer,
    input: Point,
    input_at: f64,
    goal: Option<Point>,
    target: Option<usize>,
    face: Point,
    moving: bool,
    walk: f64,
    attack: f64,
    cooldown: f64,
    hit: bool,
    hurt: f64,
    last_hurt: f64,
    combat_left: f64,
    dead_time: f64,
    dash: f64,
    dash_cd: f64,
    dash_direction: Point,
    dash_speed: f64,
    dash_mult: f64,
    dash_hits: Vec<usize>,
    dash_skill: String,
    skill_cd: BTreeMap<String, f64>,
    buffs: Vec<Buff>,
    /// Seconds until any potion can be drunk again.
    potion_cd: f64,
    /// Food healing not yet announced to the client.
    food_shown: f64,
    chat_at: f64,
    service_at: f64,
    bag_notice_at: f64,
    portal_at: f64,
    /// Personal god mode of a game master (the debug command `set_god_mode`): no damage for this player only.
    god: bool,
    /// Set on a hired mercenary: the character id of the player who hired it (see world/mercs.rs).
    merc: Option<String>,
    /// The particular group objective this fighter was hired for; Meeting Stone hires have no quest contract.
    merc_quest: Option<String>,
    /// A temporary autonomous adventurer in an occupied shared zone.
    ambient: Option<ambient::Ambient>,
    /// Set on a stranded person walking an escort quest's route (see world/escort.rs). Always with `merc` set to the
    /// character being escorted for, so an escort is never saved, counted as online or put in a party.
    escort: Option<escort::Escort>,
}
impl Player {
    // Called once when hp reaches 0: the XP penalty, then a notice naming what it cost.
    fn apply_death_penalty(&mut self) {
        let (lost, levels) = self.character.lose_death_xp();
        self.character.resource = Some(0.);
        self.combat_left = 0.;
        let text = if levels > 0 {
            format!(
                "You lost {lost} XP and dropped to level {}.",
                self.character.level
            )
        } else {
            format!("You lost {lost} XP.")
        };
        let _ = self
            .peer
            .try_send(json!({"type":"notice","ok":false,"text":text}));
    }
    fn new(mut character: Character, peer: Peer) -> Self {
        if character.hp <= 0. {
            character.resource = Some(0.);
        } else if character.look.class.resource_type() != "mana" {
            character.reset_resource();
        }
        character.resource = Some(character.resource());
        let potion_cd = character.potion_cooldown_left();
        Self {
            character,
            peer,
            input: Point::default(),
            input_at: -99.,
            goal: None,
            target: None,
            face: normalize(1., 1.),
            moving: false,
            walk: 0.,
            attack: 0.,
            cooldown: 0.,
            hit: false,
            hurt: 0.,
            last_hurt: -99.,
            combat_left: 0.,
            dead_time: 0.,
            dash: 0.,
            dash_cd: 0.,
            dash_direction: Point::default(),
            dash_speed: 15.,
            dash_mult: 0.,
            dash_hits: vec![],
            dash_skill: String::new(),
            skill_cd: BTreeMap::new(),
            buffs: vec![],
            potion_cd,
            food_shown: 0.,
            chat_at: -99.,
            service_at: -99.,
            bag_notice_at: -99.,
            portal_at: -99.,
            god: false,
            merc: None,
            merc_quest: None,
            ambient: None,
            escort: None,
        }
    }
    fn snapshot(&self) -> Value {
        let c = &self.character;
        json!({"id":c.id,"look":c.look,"zone":c.zone,"x":c.x,"y":c.y,"r":PLAYER_RADIUS,"hp":c.hp,"maxHp":c.max_hp(),"level":c.level,
            "xp":c.xp,"xpNeed":c.xp_need(),"gold":c.gold,"kills":c.kills,"quests":c.quests,"inventory":c.inventory,"equipment":c.equipment,"bags":c.bags,"bagCapacity":c.bag_capacity(),"bagUsed":c.bag_used(),"fx":self.face.x,"fy":self.face.y,
            "attributes":c.attributes,"gearAttributes":c.gear_attributes(),"statPoints":c.stat_points(),"attack":c.stats().0,"defense":c.stats().1,"critChance":c.crit_chance(),"attackCooldown":c.attack_cooldown(),"cooldownReduction":1.-c.cooldown_multiplier(),"dodgeChance":c.dodge_chance(),"hitChance":c.hit_chance(),
            "moving":self.moving,"walk":self.walk,"atkT":self.attack,"atkCd":self.cooldown,"hurtT":self.hurt,
            "dead":c.hp<=0.,"deadT":self.dead_time,"dashT":self.dash,"dashCd":self.dash_cd,
            "resource":c.resource(),"maxResource":c.max_resource(),"resourceType":c.look.class.resource_type(),"inCombat":self.combat_left>0.,
            "skillCd":self.skill_cd,"buffs":self.buffs,"potionCd":self.potion_cd,"explored":c.explored,"gm":c.gm,"god":self.god,"travelStops":c.travel_stops,"sparkTravel":c.spark_travel,
            "escort":self.escort.as_ref().map(|e| json!({"npc":e.npc,"owner":e.owner}))})
    }
    /// The sum of every active buff of one kind.
    fn buff(&self, kind: BuffKind) -> f64 {
        self.buffs
            .iter()
            .filter(|b| b.kind == kind)
            .map(|b| b.amount)
            .sum()
    }
    fn stop(&mut self) {
        self.input = Point::default();
        self.goal = None;
        self.target = None;
    }
}

#[derive(Clone, Serialize)]
struct Buff {
    id: String,
    kind: BuffKind,
    #[serde(skip)]
    amount: f64,
    left: f64,
    time: f64,
}
/// How a ranged kind shoots (see `Slime::ranged`).
struct Ranged {
    range: f64,
    speed: f64,
    color: &'static str,
    size: f64,
    shots: u32,
    spread: f64,
}
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct Slime {
    id: usize,
    kind: String,
    elite: bool,
    zone: usize,
    level: u32,
    x: f64,
    y: f64,
    hx: f64,
    hy: f64,
    hp: f64,
    max_hp: f64,
    r: f64,
    state: String,
    st: f64,
    dir: f64,
    hop: f64,
    hop_v: f64,
    hurt_t: f64,
    rec_t: f64,
    land_t: f64,
    dead: bool,
    die_t: f64,
    respawn: f64,
    atk_cd: f64,
    blink: f64,
    seed: f64,
    windup_time: f64,
    #[serde(skip)]
    damage: f64,
    #[serde(skip)]
    xp: u32,
    #[serde(skip)]
    gold: u32,
    #[serde(skip)]
    target: Option<u64>,
    #[serde(skip)]
    goal: Point,
    #[serde(skip)]
    hit: bool,
    /// The attack in progress is a shot (or a volley), not a blow.
    #[serde(skip)]
    volley: bool,
    /// An ambusher sent after an escort: it pursues its target without a leash, like a dungeon's enemies.
    #[serde(skip)]
    hunt: bool,
    /// Character IDs, so reconnecting does not lose participation. Cleared on evade/respawn.
    #[serde(skip)]
    contributors: std::collections::BTreeSet<String>,
}
impl Slime {
    // Health, damage, speed and body scale of a default-level enemy.
    fn stats(kind: &str) -> (f64, f64, f64, f64) {
        if let Some(e) = crate::cathedral::enemy(kind) {
            let [hp, damage, speed, scale] = e.stats;
            return (hp, damage, speed, scale);
        }
        match kind {
            "blue" => (80., 10., 2.4, 1.05),
            "pink" => (70., 9., 2.1, 1.),
            "yellow" => (90., 11., 2.2, 1.05),
            "big" => (600., 30., 2.2, 1.75),
            "beetle" => (240., 22., 2.8, 1.3),
            "wisp" => (280., 34., 3.4, 0.95),
            "spider" => (420., 42., 3., 1.2),
            "wraith" => (520., 52., 2.6, 1.15),
            "golem" => (1100., 64., 1.9, 1.5),
            // Two level-10 heroes, with skills and healing, rather than an ordinary solo pull.
            "cinderlord" => (2400., 180., 2.5, 1.7),
            "crab" => (900., 60., 2.8, 1.1),
            "wolf" => (1000., 72., 3.6, 1.2),
            "yeti" => (1900., 88., 2.2, 1.6),
            "wyrm" => (2200., 100., 2.8, 1.5),
            "toad" => (2000., 92., 3., 1.3),
            "croc" => (2800., 112., 3.2, 1.5),
            "knight" => (3400., 130., 2.4, 1.4),
            "hydra" => (5200., 150., 2.2, 1.8),
            // Five level-20 heroes with a healer who must triage: two hits fell a non-tank, so no party without a healer gets through.
            "gloomroot" => (90000., 1500., 2.3, 2.1),
            // The Undervault, tuned for five level-20 heroes with a healer. Trash packs of three or four; the
            // bosses are fights of one to two minutes each (see the vault_* simulations in the tests).
            "thrall" => (6500., 380., 2.6, 1.15),
            "archer" => (4200., 300., 2.4, 1.1),
            "acolyte" => (4600., 320., 2.3, 1.1),
            "gatewarden" => (80000., 1000., 2.4, 1.9),
            "choir" => (100000., 600., 2.3, 1.6),
            "colossus" => (110000., 1300., 1.9, 2.3),
            "hollowking" => (130000., 900., 2.6, 2.1),
            // The Wyrdwood (levels 21-29): a charging boar, a feather-shooting crow, a ground-pounding troll,
            // a thread-bolt witch and a very fast ram. Oakhorn (three heroes) and Hrungnir (five) are its elites.
            "boar" => (5600., 165., 3.4, 1.35),
            "crow" => (4300., 150., 3.0, 1.1),
            "troll" => (9500., 210., 2., 1.9),
            "weaver" => (7600., 190., 2.4, 1.2),
            "ram" => (11500., 255., 3.4, 1.5),
            "oakhorn" => (60000., 1300., 2.8, 2.),
            "hrungnir" => (150000., 2600., 2.2, 2.3),
            // Bifrost Reach (levels 30-35): a fast cloud-wolf, a slamming crystal golem, a lightning-shooting ray,
            // a sword-and-shield dead hero and a diving storm roc.
            "galehound" => (12500., 275., 3.8, 1.35),
            "prismgolem" => (17500., 330., 1.9, 1.8),
            "skyray" => (13500., 300., 2.8, 1.5),
            "einherjar" => (18500., 370., 2.6, 1.35),
            "thunderroc" => (22000., 440., 3.2, 1.75),
            // Ran's Deep (levels 35-40): a slow drowned sailor, a lamp-fishing angler that shoots a bead of light,
            // a fast charging moray, a three-bolt siren, a ground-pounding shellback turtle and, for five heroes,
            // the Kraken in the middle of the Net.
            "draugr" => (24000., 470., 2.4, 1.4),
            "angler" => (20500., 440., 2.8, 1.3),
            "moray" => (27000., 540., 3.5, 1.55),
            "siren" => (23500., 520., 2.6, 1.25),
            "shellback" => (40000., 700., 1.8, 1.95),
            "kraken" => (280000., 4400., 2.2, 2.5),
            // Two more elites for three heroes: the drowned captain of Naglfar (a quest) and the Ghostmaw, a huge pale moray that
            // guards the deepest corridors (no quest).
            "hvitserk" => (150000., 2600., 2.4, 2.),
            "ghostmaw" => (190000., 3000., 3.3, 2.1),
            // Astralhollow (levels 40-45): moth swarms, crystal wyrms, orbiting beetles,
            // eclipse dryads and slow meteor golems.
            "voidmoth" => (30000., 560., 3.8, 1.15),
            "crystalwyrm" => (36000., 680., 3.1, 1.45),
            "orbitbeetle" => (42000., 760., 2.7, 1.55),
            "eclipsedryad" => (39000., 720., 2.5, 1.5),
            "meteorgolem" => (60000., 980., 1.8, 1.95),
            _ => (60., 8., 1.9, 1.),
        }
    }
    // The level an enemy of this kind has before its random spread is applied.
    pub fn default_level(kind: &str) -> u32 {
        if let Some(e) = crate::cathedral::enemy(kind) {
            return e.level;
        }
        match kind {
            "blue" | "pink" => 3,
            "yellow" => 4,
            "beetle" => 5,
            "big" => 6,
            "wisp" => 5,
            "spider" => 7,
            "wraith" => 8,
            "golem" => 10,
            "cinderlord" => 10,
            "crab" => 10,
            "wolf" => 12,
            "yeti" => 13,
            "wyrm" => 15,
            "toad" => 15,
            "croc" => 17,
            "knight" => 18,
            "hydra" => 20,
            "gloomroot" => 20,
            "thrall" | "archer" => 19,
            "acolyte" | "gatewarden" | "choir" => 20,
            "colossus" | "hollowking" => 21,
            "boar" => 21,
            "crow" => 23,
            "troll" | "oakhorn" => 25,
            "weaver" => 27,
            "ram" => 29,
            "hrungnir" => 30,
            "galehound" => 30,
            "prismgolem" => 31,
            "skyray" => 32,
            "einherjar" => 33,
            "thunderroc" => 35,
            "draugr" => 35,
            "angler" => 36,
            "moray" => 37,
            "siren" => 38,
            "shellback" => 39,
            "kraken" => 40,
            "hvitserk" => 37,
            "ghostmaw" => 39,
            "voidmoth" => 40,
            "crystalwyrm" => 41,
            "orbitbeetle" => 42,
            "eclipsedryad" => 43,
            "meteorgolem" => 45,
            _ => 2,
        }
    }
    // Gold carried by a default-level enemy; ordinary slimes add a small random amount.
    fn base_gold(kind: &str) -> u32 {
        if let Some(e) = crate::cathedral::enemy(kind) {
            return e.gold;
        }
        match kind {
            "big" => 30,
            "beetle" => 10,
            "wisp" => 18,
            "spider" => 26,
            "wraith" => 36,
            "golem" => 55,
            "cinderlord" => 100,
            "crab" => 60,
            "wolf" => 78,
            "yeti" => 105,
            "wyrm" => 150,
            "toad" => 165,
            "croc" => 205,
            "knight" => 245,
            "hydra" => 360,
            "gloomroot" => 1200,
            "thrall" => 280,
            "archer" => 290,
            "acolyte" => 320,
            "gatewarden" => 1500,
            "choir" => 1800,
            "colossus" => 2200,
            "hollowking" => 3500,
            "boar" => 270,
            "crow" => 290,
            "troll" => 330,
            "weaver" => 360,
            "ram" => 400,
            "oakhorn" => 2000,
            "hrungnir" => 3000,
            "galehound" => 430,
            "prismgolem" => 460,
            "skyray" => 490,
            "einherjar" => 520,
            "thunderroc" => 600,
            "draugr" => 640,
            "angler" => 680,
            "moray" => 720,
            "siren" => 770,
            "shellback" => 830,
            "kraken" => 4500,
            "hvitserk" => 2500,
            "ghostmaw" => 3200,
            "voidmoth" => 900,
            "crystalwyrm" => 980,
            "orbitbeetle" => 1060,
            "eclipsedryad" => 1140,
            "meteorgolem" => 1450,
            _ => 0,
        }
    }
    // Windup, recovery cooldown, charge speed, awareness radius.
    fn attack_profile(kind: &str) -> (f64, f64, f64, f64) {
        if let Some(e) = crate::cathedral::enemy(kind) {
            let [windup, cooldown, charge, awareness] = e.profile;
            return (windup, cooldown, charge, awareness);
        }
        match kind {
            "big" => (0.35, 0.85, 8., 7.5),
            "beetle" => (0.4, 1.1, 7.5, 7.),
            "wisp" => (0.35, 1., 8.5, 7.5),
            "spider" => (0.4, 1.1, 8., 7.5),
            "wraith" => (0.5, 1.2, 7.5, 8.),
            "golem" => (0.6, 1.5, 6., 6.5),
            "cinderlord" => (0.65, 1.25, 7., 7.),
            "crab" => (0.4, 1., 8., 7.),
            "wolf" => (0.3, 0.9, 9.5, 9.),
            "yeti" => (0.7, 1.6, 6.5, 7.),
            "wyrm" => (0.5, 1.2, 8.5, 8.5),
            "toad" => (0.45, 1., 8.5, 7.),
            "croc" => (0.35, 1.1, 10., 8.5),
            "knight" => (0.6, 1.4, 6.5, 7.5),
            "hydra" => (0.55, 1.3, 7.5, 9.),
            "gloomroot" => (0.85, 1.5, 7.5, 8.5),
            "thrall" => (0.45, 1.2, 7.5, 8.),
            "archer" => (0.6, 1.8, 0., 11.),
            "acolyte" => (0.7, 2.2, 0., 11.),
            "gatewarden" => (0.9, 1.8, 7., 9.),
            "choir" => (0.8, 2.6, 0., 13.),
            "colossus" => (1., 2.2, 6., 9.),
            "hollowking" => (0.8, 1.7, 8., 14.),
            "boar" => (0.3, 0.9, 11., 9.),
            "crow" => (0.5, 1.7, 0., 11.),
            "troll" => (0.8, 1.6, 6., 7.5),
            "weaver" => (0.7, 2.2, 0., 12.),
            "ram" => (0.25, 0.8, 12., 10.),
            // Oakhorn lowers its antlers for a full second before the stampede.
            "oakhorn" => (1., 1.5, 12., 10.),
            "hrungnir" => (0.9, 1.9, 7., 14.),
            "galehound" => (0.28, 0.85, 12., 10.),
            "prismgolem" => (0.8, 1.7, 6., 7.5),
            "skyray" => (0.5, 1.8, 0., 12.),
            "einherjar" => (0.55, 1.3, 7.5, 8.5),
            "thunderroc" => (0.35, 1.0, 13., 11.),
            "draugr" => (0.55, 1.3, 7.5, 8.5),
            "angler" => (0.6, 1.9, 0., 12.),
            "moray" => (0.25, 0.8, 13., 10.),
            "siren" => (0.7, 2.2, 0., 12.5),
            "shellback" => (0.9, 1.8, 6., 7.5),
            // The Kraken coils for a full second before its slam.
            "kraken" => (1., 2., 7., 14.),
            "hvitserk" => (0.9, 1.6, 7., 10.),
            "ghostmaw" => (0.35, 0.9, 12., 11.),
            "voidmoth" => (0.35, 0.9, 11., 10.),
            "crystalwyrm" => (0.45, 1.1, 10., 9.),
            "orbitbeetle" => (0.55, 1.3, 8., 8.),
            "eclipsedryad" => (0.7, 1.7, 7., 10.),
            "meteorgolem" => (1.0, 2.0, 5.5, 7.),
            _ => (0.45, 1.3, 6., 5.5),
        }
    }
    /// Kinds that shoot instead of striking: how far, how fast the missile flies, its colour and size, and how many
    /// fly at once (spread across `spread` radians). The shot is released when the windup ends, so a hero who walks
    /// out of the line in that moment is missed.
    fn ranged(kind: &str) -> Option<Ranged> {
        if let Some(e) = crate::cathedral::enemy(kind) {
            return e
                .ranged
                .as_ref()
                .map(|(range, speed, color, size, shots, spread)| Ranged {
                    range: *range,
                    speed: *speed,
                    color: color.as_str(),
                    size: *size,
                    shots: *shots,
                    spread: *spread,
                });
        }
        let (range, speed, color, size, shots, spread) = match kind {
            "archer" => (10., 14., "#f1e2b0", 0.5, 1, 0.),
            "acolyte" => (10., 9., "#b46bff", 0.8, 1, 0.),
            "choir" => (11., 9., "#7be0ff", 0.9, 3, 0.34),
            "hollowking" => (12., 10., "#9cff8f", 1.0, 5, 0.24),
            "crow" => (11., 11., "#c9d2e8", 0.5, 2, 0.16),
            "weaver" => (11., 8.5, "#ffd86b", 0.9, 3, 0.3),
            "hrungnir" => (13., 14., "#bfe8ff", 1.1, 3, 0.22),
            "skyray" => (12., 12., "#9fe8ff", 0.7, 2, 0.18),
            "angler" => (12., 8., "#9ffff0", 1.1, 1, 0.),
            "siren" => (12.5, 9., "#ff9ae8", 0.9, 3, 0.3),
            "kraken" => (13., 11., "#5a4aa8", 1.3, 3, 0.26),
            _ => return None,
        };
        Some(Ranged {
            range,
            speed,
            color,
            size,
            shots,
            spread,
        })
    }
    /// A ranged kind that also fights toe to toe: it shoots only from farther than this.
    fn melee_inside(kind: &str) -> f64 {
        if let Some(e) = crate::cathedral::enemy(kind) {
            return e.melee;
        }
        if matches!(kind, "hollowking" | "hrungnir" | "kraken") {
            4.5
        } else {
            0.
        }
    }
    /// Radius of the ground-pound a kind does instead of a single blow (0: an ordinary strike). It lands when the
    /// windup ends, on everyone inside, so the wind-up is the warning.
    fn slam_radius(kind: &str) -> f64 {
        if let Some(e) = crate::cathedral::enemy(kind) {
            return e.slam;
        }
        match kind {
            "gatewarden" => 3.6,
            "colossus" => 4.,
            "hollowking" => 3.2,
            "troll" => 2.6,
            "prismgolem" => 3.0,
            "hrungnir" => 3.6,
            "shellback" => 3.2,
            "kraken" => 4.0,
            "hvitserk" => 3.0,
            _ => 0.,
        }
    }
    /// What fraction of its blow a ground-pound deals to each hero in the ring (it hits everyone at once).
    fn slam_factor(kind: &str) -> f64 {
        match kind {
            "gatewarden" => 0.45,
            "colossus" => 0.4,
            _ => 0.5,
        }
    }
    /// Dungeon enemies keep one level (the Undervault is tuned for exactly level 20 heroes).
    fn fixed_level(kind: &str) -> bool {
        if crate::cathedral::enemy(kind).is_some() {
            return true;
        }
        matches!(
            kind,
            "thrall" | "archer" | "acolyte" | "gatewarden" | "choir" | "colossus" | "hollowking"
        )
    }
    /// Bosses pay a multiple of an ordinary kill's XP.
    fn xp_multiplier(kind: &str) -> u32 {
        if is_boss(kind) { 12 } else { 1 }
    }
    fn level_scale(kind: &str, level: u32, per_level: f64) -> f64 {
        (1. + per_level * (level as f64 - Self::default_level(kind) as f64)).max(0.2)
    }
    #[cfg(test)]
    fn new(id: usize, s: &SlimeSpawn) -> Self {
        Self::with_level(id, s, Self::default_level(&s.kind))
    }
    fn with_level(id: usize, s: &SlimeSpawn, level: u32) -> Self {
        let (hp, damage, _, scale) = Self::stats(&s.kind);
        let strength = Self::level_scale(&s.kind, level, LEVEL_HP_DAMAGE);
        let hp = (hp * strength).round();
        Self {
            id,
            kind: s.kind.clone(),
            elite: is_elite(&s.kind),
            zone: s.zone,
            level,
            x: s.x,
            y: s.y,
            hx: s.x,
            hy: s.y,
            hp,
            max_hp: hp,
            r: 0.3 * scale,
            state: "idle".into(),
            st: 1.,
            dir: 1.,
            hop: 0.,
            hop_v: 0.,
            hurt_t: 0.,
            rec_t: 0.,
            land_t: 0.,
            dead: false,
            die_t: 0.,
            respawn: 0.,
            atk_cd: 1.,
            blink: 2.,
            seed: id as f64,
            windup_time: Self::attack_profile(&s.kind).0,
            damage: (damage * strength).round(),
            xp: enemy_xp(level) * Self::xp_multiplier(&s.kind),
            gold: (Self::base_gold(&s.kind) as f64 * Self::level_scale(&s.kind, level, 0.1)).round()
                as u32,
            target: None,
            goal: Point { x: s.x, y: s.y },
            hit: false,
            volley: false,
            hunt: false,
            contributors: Default::default(),
        }
    }
    fn point(&self) -> Point {
        Point {
            x: self.x,
            y: self.y,
        }
    }
}
#[derive(Clone, Serialize)]
struct Bolt {
    id: u64,
    owner: u64,
    zone: usize,
    x: f64,
    y: f64,
    fx: f64,
    fy: f64,
    t: f64,
    color: String,
    size: f64,
    #[serde(skip)]
    damage: f64,
    #[serde(skip)]
    crit: bool,
    #[serde(skip)]
    pierce: bool,
    #[serde(skip)]
    blast: f64,
    #[serde(skip)]
    hits: Vec<usize>,
    /// The skill that fired this bolt (empty for a basic attack), for the system log.
    #[serde(skip)]
    skill: String,
}
#[derive(Clone, Serialize)]
struct Drop {
    id: u64,
    owner: String,
    zone: usize,
    x: f64,
    y: f64,
    z: f64,
    value: u32,
    item: Option<String>,
    quantity: u32,
    t: f64,
    col: &'static str,
    /// A party's shared pile: every member who was near the body when it fell may take it (the pickup rules are in
    /// `rolls.rs`). Empty means the pile belongs to `owner` alone.
    #[serde(skip)]
    group: Vec<String>,
}

impl Drop {
    fn point(&self) -> Point {
        Point {
            x: self.x,
            y: self.y,
        }
    }
    /// Whether this character may take the pile: its owner, or any member of the party it was shared with.
    fn open_to(&self, id: &str) -> bool {
        self.owner == id || self.group.iter().any(|g| g == id)
    }
}

pub struct World {
    // Zone 0 is Greenmeadow with Alderhaven; later zones come from the map's `zones`.
    maps: Vec<Map>,
    // Every zone's enemy spawns in one list, so enemy ids stay stable and global.
    spawns: Vec<SlimeSpawn>,
    store: Store,
    players: BTreeMap<u64, Player>,
    slimes: Vec<Slime>,
    bolts: Vec<Bolt>,
    // Missiles shot by ranged enemies (world/ranged.rs).
    enemy_bolts: Vec<ranged::EnemyBolt>,
    // The private copies of every dungeon (world/instances.rs).
    instances: Vec<instances::Instance>,
    pursuit: pursuit::Pursuit,
    drops: Vec<Drop>,
    // Party loot rolls in progress (world/rolls.rs).
    rolls: Vec<rolls::Roll>,
    // Whose turn the next round-robin drop is, per party (keyed by its first member's character id).
    loot_turns: BTreeMap<String, usize>,
    // Failed disconnect writes are retried by the next periodic transaction.
    pending_saves: Vec<Character>,
    time: f64,
    tick: u64,
    rng: u64,
    next_entity: u64,
    next_king_spawn: f64,
    // The skill whose damage is being applied right now (empty: a basic attack); hit events carry it for the system log.
    cur_skill: String,
    /// Counter for mercenary sessions.
    merc_seq: u64,
    /// Desired autonomous adventurers in each currently occupied shared zone.
    ambient_targets: BTreeMap<usize, usize>,
    pub ambient_enabled: bool,
    level_spread: i32,
    // Test servers only (VALHALLA_GOD_MODE=1): enemies still fight, but players take no damage.
    pub god_mode: bool,
    // Test servers only (VALHALLA_START_LEVEL): new characters begin at this level; loaded ones are untouched.
    pub start_level: u32,
    // Test servers only (VALHALLA_TEST_COMMANDS=1): players may send `debug` shortcuts. Never set on the public service.
    pub test_commands: bool,
    // Friend requests, party invites and parties. Nothing here is persisted except `Character::friends`.
    social: social::Social,
    // Hold objectives in progress (world/hold.rs).
    hold: hold::Holds,
    chime: chime::Chimes,
}
impl World {
    // Production code reads VALHALLA_LEVEL_SPREAD in main; tests that want real random levels use this.
    #[cfg(test)]
    pub fn new(store: Store) -> Self {
        Self::with_level_spread(store, LEVEL_SPREAD)
    }
    pub fn with_level_spread(store: Store, level_spread: i32) -> Self {
        let mut first = Map::default();
        let extra = std::mem::take(&mut first.zones);
        let mut maps = vec![first];
        maps.extend(extra);
        let instances = Self::make_instances(&mut maps);
        let spawns: Vec<SlimeSpawn> = maps
            .iter()
            .enumerate()
            .flat_map(|(zone, map)| {
                map.slimes
                    .iter()
                    .map(move |s| SlimeSpawn { zone, ..s.clone() })
            })
            .collect();
        let mut world = Self {
            maps,
            spawns,
            store,
            players: BTreeMap::new(),
            slimes: vec![],
            bolts: vec![],
            enemy_bolts: vec![],
            instances,
            pursuit: pursuit::Pursuit::default(),
            drops: vec![],
            rolls: vec![],
            loot_turns: BTreeMap::new(),
            pending_saves: vec![],
            time: 0.,
            tick: 0,
            rng: u64::from_le_bytes(uuid::Uuid::new_v4().as_bytes()[..8].try_into().unwrap()),
            next_entity: 1,
            next_king_spawn: 0.,
            cur_skill: String::new(),
            merc_seq: 0,
            ambient_targets: BTreeMap::new(),
            ambient_enabled: false,
            level_spread,
            god_mode: false,
            start_level: 1,
            test_commands: false,
            social: social::Social::default(),
            hold: hold::Holds::default(),
            chime: chime::Chimes::default(),
        };
        for id in 0..world.spawns.len() {
            let enemy = world.fresh_enemy(id);
            world.slimes.push(enemy);
        }
        world.next_king_spawn = world.king_spawn_delay();
        for id in 0..world.slimes.len() {
            world.place_enemy(id);
        }
        world
    }
    /// A new enemy for spawn `id`, at full health and a freshly rolled level (kings start hidden until the world timer).
    fn fresh_enemy(&mut self, id: usize) -> Slime {
        let spawn = self.spawns[id].clone();
        if spawn.ambush.is_some() {
            // Ambushers sleep until their escort's journey passes them.
            return self.dormant_enemy(id);
        }
        let level = if crate::cathedral::enemy(&spawn.kind).is_some() {
            self.maps[spawn.zone]
                .levels
                .map_or_else(|| Slime::default_level(&spawn.kind), |l| l[0])
        } else {
            self.roll_level(&spawn.kind)
        };
        let mut enemy = Slime::with_level(id, &spawn, level);
        if spawn.kind == "big" {
            // Keep stable entity IDs while hiding kings until the world timer fires.
            enemy.dead = true;
            enemy.hp = 0.;
            enemy.state = "waiting".into();
            enemy.die_t = 2.;
        }
        enemy
    }
    /// Moves a living enemy off whatever it overlaps; one that finds no room starts dead and respawns at once.
    fn place_enemy(&mut self, id: usize) {
        if self.slimes[id].dead {
            return;
        }
        let zone = self.slimes[id].zone;
        let bodies = self.actor_bodies(zone, None, Some(id));
        if let Some(point) = free_actor_position(
            &self.maps[zone],
            self.slimes[id].point(),
            self.slimes[id].r,
            &bodies,
            true,
        ) {
            self.slimes[id].x = point.x;
            self.slimes[id].y = point.y;
        } else {
            self.slimes[id].dead = true;
            self.slimes[id].die_t = 2.;
            self.slimes[id].respawn = TICK;
        }
    }
    // A kind's default level, moved by a uniform random whole number within the spread.
    fn roll_level(&mut self, kind: &str) -> u32 {
        let default = Slime::default_level(kind) as i32;
        if self.level_spread <= 0 || Slime::fixed_level(kind) {
            return default as u32;
        }
        let offset = (self.random() * (2 * self.level_spread + 1) as f64) as i32;
        (default + offset.min(2 * self.level_spread) - self.level_spread).max(1) as u32
    }
    fn random(&mut self) -> f64 {
        self.rng = self.rng.wrapping_mul(6364136223846793005).wrapping_add(1);
        (self.rng >> 32) as f64 / 4294967296.
    }
    fn entity(&mut self) -> u64 {
        let id = self.next_entity;
        self.next_entity += 1;
        id
    }
    fn king_spawn_delay(&mut self) -> f64 {
        KING_SPAWN_MIN + self.random() * (KING_SPAWN_MAX - KING_SPAWN_MIN)
    }
    fn actor_bodies(
        &self,
        zone: usize,
        player: Option<u64>,
        enemy: Option<usize>,
    ) -> Vec<(Point, f64)> {
        let player_gap = enemy
            .map(|id| (1. - self.slimes[id].r).max(PLAYER_RADIUS))
            .unwrap_or(PLAYER_RADIUS);
        self.players
            .iter()
            .filter(|(id, p)| {
                Some(**id) != player
                    && p.character.hp > 0.
                    && p.character.zone == zone
                    && p.character.spark_travel.is_none()
            })
            .map(|(_, p)| (p.character.point(), player_gap))
            .chain(
                self.slimes
                    .iter()
                    .filter(|s| Some(s.id) != enemy && !s.dead && s.zone == zone)
                    .map(|s| (s.point(), s.r)),
            )
            .collect()
    }
    fn separate_enemies(&mut self) {
        for id in 0..self.slimes.len() {
            if self.slimes[id].dead || self.zone_idle(self.slimes[id].zone) {
                continue;
            }
            let bodies = self.actor_bodies(self.slimes[id].zone, None, Some(id));
            let enemy = &self.slimes[id];
            if !actor_blocked(enemy.point(), enemy.r, &bodies) {
                continue;
            }
            let mut candidate = enemy.point();
            for (other, radius) in &bodies {
                if same_cell(candidate, *other) || candidate.distance(*other) < enemy.r + radius {
                    let direction = if candidate.distance(*other) < 1e-8 {
                        Point { x: 1., y: 0. }
                    } else {
                        other.direction(candidate)
                    };
                    candidate = Point {
                        x: other.x + direction.x * (enemy.r + radius + 0.01),
                        y: other.y + direction.y * (enemy.r + radius + 0.01),
                    };
                }
            }
            if let Some(point) =
                free_actor_position(&self.maps[enemy.zone], candidate, enemy.r, &bodies, true)
            {
                self.slimes[id].x = point.x;
                self.slimes[id].y = point.y;
            }
        }
    }
    fn update_king_spawn(&mut self) {
        if self.time < self.next_king_spawn
            || self.slimes.iter().any(|s| s.kind == "big" && !s.dead)
        {
            return;
        }
        let locations: Vec<_> = self
            .slimes
            .iter()
            .filter(|s| s.kind == "big")
            .map(|s| s.id)
            .collect();
        if locations.is_empty() {
            return;
        }
        let id = locations[(self.random() * locations.len() as f64) as usize];
        let spawn = self.spawns[id].clone();
        let level = self.roll_level("big");
        let mut enemy = Slime::with_level(id, &spawn, level);
        let bodies = self.actor_bodies(enemy.zone, None, Some(id));
        let Some(point) = free_actor_position(
            &self.maps[enemy.zone],
            enemy.point(),
            enemy.r,
            &bodies,
            true,
        ) else {
            return;
        };
        enemy.x = point.x;
        enemy.y = point.y;
        self.slimes[id] = enemy;
        self.emit(json!({"type":"system","text":"A King Slime has emerged in Greenmeadow!"}));
    }
    fn emit(&self, value: Value) {
        for p in self.players.values() {
            let _ = p.peer.try_send(value.clone());
        }
    }
    // Combat and pickup events carry coordinates, so only players in that zone receive them.
    fn emit_zone(&self, zone: usize, value: Value) {
        for p in self.players.values().filter(|p| p.character.zone == zone) {
            let _ = p.peer.try_send(value.clone());
        }
    }
    fn zone_of(&self, actor: &str) -> usize {
        self.players
            .values()
            .find(|p| p.character.id == actor)
            .map_or(0, |p| p.character.zone)
    }
    fn event(&self, kind: &str, actor: &str, p: Point, value: f64, crit: bool) {
        self.emit_zone(self.zone_of(actor), json!({"type":"event","kind":kind,"actor":actor,"x":p.x,"y":p.y,"value":value,"crit":crit}));
    }
    /// An event with extra fields (who was hit, by what) merged in, for the client's system log.
    fn event_with(&self, kind: &str, actor: &str, p: Point, value: f64, crit: bool, extra: Value) {
        let mut v = json!({"type":"event","kind":kind,"actor":actor,"x":p.x,"y":p.y,"value":value,"crit":crit});
        if let (Some(o), Some(e)) = (v.as_object_mut(), extra.as_object()) {
            o.extend(e.clone());
        }
        self.emit_zone(self.zone_of(actor), v);
    }
    // What one client needs: its own zone's players, enemies, bolts and drops. Zones are separate maps, so
    // nothing about another zone is ever sent to this client.
    pub fn snapshot_for(&self, zone: usize) -> Value {
        let idle = self.zone_idle(zone);
        let mut view = json!({"type":"snapshot","tick":self.tick,"time":self.time,
        "players":self.players.iter().filter(|(_, p)| p.character.zone == zone).map(|(session, p)| {
            let mut view = p.snapshot();
            // The bells a hero has ringing and how long each has left (only listed while there are any).
            let bells = self.chime.view(*session);
            if !bells.is_empty() {
                view["bells"] = json!(bells.iter().map(|(place, left)| json!({"place":place,"left":left})).collect::<Vec<_>>());
            }
            view
        }).collect::<Vec<_>>(),
        "slimes":self.slimes.iter().filter(|s| s.zone == zone && !idle).collect::<Vec<_>>(),
        "bolts":self.bolts.iter().filter(|b| b.zone == zone).collect::<Vec<_>>(),
        "ebolts":self.enemy_bolts.iter().filter(|b| b.zone == zone).collect::<Vec<_>>(),
        "drops":self.drops.iter().filter(|d| d.zone == zone).collect::<Vec<_>>(),
        "online":self.visible_online()});
        if let Some(instance) = self.instance_at(zone) {
            view["instance"] = json!({"cleared":instance.cleared});
            // A private copy is told it is the template zone, so a client has one dungeon whatever copy it stands in.
            if instance.template != zone {
                for key in ["players", "slimes", "bolts", "ebolts", "drops"] {
                    for item in view[key].as_array_mut().into_iter().flatten() {
                        item["zone"] = json!(instance.template);
                    }
                }
            }
        }
        view
    }
    // Published to every connection: one complete view per zone. Each connection forwards only the view
    // that holds its own character; `tick` and `online` also sit at the top for the health route.
    pub fn snapshot(&self) -> Value {
        json!({"tick":self.tick,"online":self.visible_online(),"humansOnline":self.humans_online(),
        "zones":(0..self.maps.len()).map(|zone| self.snapshot_for(zone)).collect::<Vec<_>>()})
    }

    #[cfg(test)]
    fn join(
        &mut self,
        session: u64,
        token: Option<String>,
        look: Option<Look>,
        peer: Peer,
    ) -> Result<Value, String> {
        self.join_as(session, Identity::Guest { token, look }, peer)
    }
    fn join_as(&mut self, session: u64, identity: Identity, peer: Peer) -> Result<Value, String> {
        if self.humans_online() >= MAX_PLAYERS {
            return Err("This world is full. Try again later.".into());
        }
        let storage = |e: Box<dyn std::error::Error>| {
            tracing::error!(%e,"character storage failed");
            "Character storage is unavailable.".to_owned()
        };
        let (mut c, issued) = match identity {
            Identity::Guest {
                token: Some(token), ..
            } => {
                let c =
                    self.store.load(&token).map_err(storage)?.ok_or(
                        "This character key is invalid. Choose New Character to start again.",
                    )?;
                (c, None)
            }
            Identity::Account {
                id,
                character: Some(character),
                ..
            } => {
                let c = self
                    .store
                    .load_for_account(&id, &character)
                    .map_err(storage)?
                    .ok_or("That character is not on your account. Pick one from your list.")?;
                (c, None)
            }
            Identity::Account {
                id,
                gm,
                character: None,
                look,
            } => {
                let mut look = look.ok_or("Create a character first.")?;
                look.name = look.name.trim().into();
                look.clear_worn();
                // The reserved name asks for the administrator character; the server then builds it itself.
                let wants_gm = look.name_is_reserved();
                if wants_gm {
                    if !gm || look.name != GM_NAME {
                        return Err("That name is reserved.".into());
                    }
                    if self.store.account_has_gm(&id).map_err(storage)? {
                        return Err("You already have your [GM] character.".into());
                    }
                    look.class = Class::Warrior;
                    look.gender = Gender::Male;
                }
                look.validate()?;
                if !wants_gm
                    && self.store.account_character_count(&id).map_err(storage)?
                        >= MAX_ACCOUNT_CHARACTERS
                {
                    return Err(format!(
                        "Your account already has {MAX_ACCOUNT_CHARACTERS} characters. Delete one first."
                    ));
                }
                let (c, _) = self
                    .store
                    .create_character(Some(&id), look, self.maps[0].spawn, wants_gm)
                    .map_err(storage)?;
                (self.with_start_level(c), None)
            }
            Identity::Guest { token: None, look } => {
                let mut look = look.ok_or("Create a character first.")?;
                look.name = look.name.trim().into();
                look.clear_worn();
                if look.name_is_reserved() {
                    return Err("That name is reserved.".into());
                }
                look.validate()?;
                let (c, token) = self
                    .store
                    .create(look, self.maps[0].spawn)
                    .map_err(storage)?;
                (self.with_start_level(c), Some(token))
            }
        };
        if self.players.values().any(|p| p.character.id == c.id) {
            return Err("This character is already online in another window.".into());
        }
        if let Some(saved) = self.pending_saves.iter().rev().find(|p| p.id == c.id) {
            c = saved.clone();
        }
        if c.zone >= self.maps.len() {
            // A zone that no longer exists sends the character back to the start.
            c.zone = 0;
            c.x = self.maps[0].spawn.x;
            c.y = self.maps[0].spawn.y;
        }
        // A dungeon copy is gone once nobody is in it: a hero who logged out inside wakes at its door.
        if self.is_instance(c.zone)
            && let Some(door) = self.maps[c.zone].portals.iter().find(|p| !p.after_clear)
        {
            (c.zone, c.x, c.y) = (door.to, door.tx, door.ty);
        }
        let mut point = c.point();
        if c.spark_travel.is_none() {
            self.maps[c.zone].collide(&mut point, PLAYER_RADIUS);
        }
        c.x = point.x;
        c.y = point.y;
        let id = c.id.clone();
        let name = c.look.name.clone();
        let place = self.zone_name(c.zone).to_owned();
        let friends = c.friends.clone();
        self.players.insert(session, Player::new(c, peer));
        self.social_joined(&id, &name, &friends);
        self.separate_enemies();
        self.emit(json!({"type":"system","text":format!("{name} entered {place}.")}));
        let zone = self.players[&session].character.zone;
        Ok(
            json!({"type":"welcome","version":1,"id":id,"token":issued,"snapshot":self.snapshot_for(zone)}),
        )
    }
    /// Test servers may start new characters above level 1 (VALHALLA_START_LEVEL).
    fn with_start_level(&self, mut c: Character) -> Character {
        if self.start_level > 1 {
            c.level = self.start_level;
            c.hp = c.max_hp();
        }
        c
    }
    fn zone_name(&self, zone: usize) -> &str {
        match self.maps[zone].name.as_str() {
            "" => "Greenmeadow",
            name => name,
        }
    }
    fn leave(&mut self, session: u64) {
        if self
            .players
            .get(&session)
            .is_some_and(|p| p.ambient.is_some())
        {
            if let Some(p) = self.players.remove(&session) {
                self.social_left(&p.character.id, &p.character.look.name, &[]);
            }
            return;
        }
        if self.is_merc(session) {
            return self.remove_mercenary(session);
        }
        let _ = self.dismiss_mercenaries(session);
        if let Some(p) = self.players.remove(&session) {
            let name = p.character.look.name.clone();
            let place = self.zone_name(p.character.zone).to_owned();
            self.social_left(&p.character.id, &name, &p.character.friends);
            self.pending_saves.push(p.character);
            self.save();
            self.emit(json!({"type":"system","text":format!("{name} left {place}.")}));
        }
    }
    fn save(&mut self) {
        // Pending versions precede live versions; an online character always wins.
        match self.store.save_many(
            self.pending_saves.iter().chain(
                self.players
                    .values()
                    .filter(|p| p.merc.is_none() && p.ambient.is_none())
                    .map(|p| &p.character),
            ),
        ) {
            Ok(()) => self.pending_saves.clear(),
            Err(e) => tracing::error!(%e,"save failed; retrying on next save tick"),
        }
    }
    fn message(&mut self, session: u64, message: ClientMessage) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        if p.character.spark_travel.is_some()
            && !matches!(
                message,
                ClientMessage::Chat { .. }
                    | ClientMessage::Social { .. }
                    | ClientMessage::Roll { .. }
                    | ClientMessage::Ping { .. }
            )
        {
            return;
        }
        match message {
            ClientMessage::Input { dx, dy }
                if dx.is_finite() && dy.is_finite() && dx.abs() <= 1. && dy.abs() <= 1. =>
            {
                p.input = normalize(dx, dy);
                p.input_at = self.time;
                if dx != 0. || dy != 0. {
                    p.goal = None;
                    p.target = None;
                }
            }
            ClientMessage::Stop => p.stop(),
            ClientMessage::Move { x, y } if x.is_finite() && y.is_finite() => {
                let size = self.maps[p.character.zone].size as f64;
                p.goal = Some(Point {
                    x: x.clamp(0.7, size - 0.7),
                    y: y.clamp(0.7, size - 0.7),
                });
                p.target = None;
                p.input = Point::default();
            }
            ClientMessage::Target { id }
                if self
                    .slimes
                    .get(id)
                    .is_some_and(|s| !s.dead && s.zone == p.character.zone) =>
            {
                p.target = Some(id);
                p.goal = None;
                p.input = Point::default();
            }
            ClientMessage::Attack { fx, fy } if fx.is_finite() && fy.is_finite() => {
                let face = normalize(fx, fy);
                if face.x != 0. || face.y != 0. {
                    p.face = face;
                }
                self.start_attack(session);
            }
            ClientMessage::Dash { dx, dy }
                if dx.is_finite()
                    && dy.is_finite()
                    && p.character.hp > 0.
                    && p.character.look.class == Class::Assassin
                    && p.dash_cd <= 0. =>
            {
                if p.character.resource() < 20. {
                    let _ = p.peer.try_send(
                        json!({"type":"error","text":"Not enough energy: Shadowstep costs 20."}),
                    );
                    return;
                }
                p.character.change_resource(-20.);
                let dir = normalize(dx, dy);
                p.dash_direction = if dir.x == 0. && dir.y == 0. {
                    p.face
                } else {
                    dir
                };
                p.face = p.dash_direction;
                p.dash = 0.18;
                p.dash_speed = 15.;
                p.dash_mult = 0.;
                p.dash_cd = 1.2 * p.character.cooldown_multiplier();
                p.attack = 0.;
                p.hurt = 0.;
                p.stop();
                let id = p.character.id.clone();
                let point = p.character.point();
                self.event("shadowstep", &id, point, 0., false);
            }
            ClientMessage::Skill { id, fx, fy } if fx.is_finite() && fy.is_finite() => {
                self.use_skill(session, &id, normalize(fx, fy));
            }
            ClientMessage::UseItem { item } => {
                self.use_item(session, &item);
            }
            ClientMessage::Equip {
                armor,
                weapon,
                slots,
            } => {
                p.stop();
                p.attack = 0.;
                let mut next = p.character.clone();
                let (current_armor, current_weapon) = next.gear();
                let armor = armor.unwrap_or_else(|| current_armor.into());
                let weapon = weapon.unwrap_or_else(|| current_weapon.into());
                let result = next
                    .look
                    .equip(&armor, &weapon)
                    .and_then(|()| next.equip_slots(&slots))
                    .and_then(|()| next.check_required_levels(&p.character));
                if let Err(text) = result {
                    let _ = p.peer.try_send(json!({"type":"error","text":text}));
                } else if next.look != p.character.look || next.equipment != p.character.equipment {
                    p.character = next;
                    self.save();
                }
            }
            ClientMessage::AllocateStat { stat } => match p.character.allocate_stat(&stat) {
                Ok(()) => self.save(),
                Err(text) => {
                    let _ = p.peer.try_send(json!({"type":"error","text":text}));
                }
            },
            ClientMessage::Interact { npc, offer } => {
                self.interact(session, &npc, offer.as_deref());
            }
            ClientMessage::Chat { text } => {
                let text = text.trim();
                if self.time - p.chat_at < 1. {
                    let _=p.peer.try_send(json!({"type":"error","text":"Please wait a moment before chatting again."}));
                    return;
                }
                if text.is_empty()
                    || text.chars().count() > 240
                    || text.chars().any(char::is_control)
                {
                    return;
                }
                p.chat_at = self.time;
                let name = p.character.look.name.clone();
                let id = p.character.id.clone();
                self.emit(json!({"type":"chat","name":name,"id":id,"text":text}));
            }
            ClientMessage::Social { command } => {
                self.social(session, command);
            }
            ClientMessage::Roll { id, choice } => self.roll_vote(session, id, choice),
            ClientMessage::Ping { nonce } => {
                let _ = p.peer.try_send(json!({"type":"pong","nonce":nonce}));
            }
            ClientMessage::Debug { reference, command } => {
                self.debug(session, reference, command);
            }
            _ => {}
        }
    }
    fn interact(&mut self, session: u64, npc_id: &str, offer_id: Option<&str>) {
        if self.travel_master(npc_id).is_some() {
            return self.spark_interact(session, npc_id, offer_id);
        }
        if let Some(what) = offer_id.and_then(|id| self.merc_offer(session, npc_id, id)) {
            return self.merc_interact(session, npc_id, &what);
        }
        // A stranded person joins whoever has taken their escort quest.
        let escort_note = self.try_start_escort(session, npc_id);
        let p = self.players.get_mut(&session).unwrap();
        let map = &self.maps[p.character.zone];
        let Some(npc) = map.npcs.iter().find(|npc| npc.id == npc_id) else {
            return;
        };
        // Walking townspeople are wherever the world clock puts them.
        if p.character.hp <= 0. || p.character.point().distance(npc.position_at(self.time)) > 2.8 {
            let _ = p.peer.try_send(
                json!({"type":"error","text":"Walk closer to speak with this townsperson."}),
            );
            return;
        }
        p.stop();
        p.attack = 0.;
        // A talk objective can name someone in another zone (the city's errands), so every zone's quests are checked.
        for area in &self.maps {
            quest_progress(&mut p.character, &area.quests, "talk", npc_id);
        }
        let mut notice = escort_note.unwrap_or_default();
        let mut levels = 0;
        let mut quest_changed = false;
        if let Some(id) = offer_id {
            if self.time - p.service_at < 0.5 {
                // Reply so a pending client button is never left disabled.
                notice = "Please wait a moment before trying again.".into();
            } else {
                p.service_at = self.time;
                if let Some(action) = id.strip_prefix("quest:") {
                    if let Some((action, id)) = action.split_once(':')
                        && let Some(quest) =
                            map.quests.iter().find(|q| q.id == id && q.npc == npc_id)
                    {
                        (notice, levels, quest_changed) =
                            quest_action(&mut p.character, quest, action);
                    }
                } else if let Some(sale) = id.strip_prefix("sell:") {
                    if !npc.buys {
                        notice = "This townsperson does not buy items.".into();
                    } else {
                        let mut next = p.character.clone();
                        let result = if sale == "materials" {
                            let stacks = next.inventory.clone();
                            let mut total = Ok(0_u32);
                            for stack in stacks {
                                if item(&stack.item).is_some_and(|i| i.kind == "material") {
                                    match next.sell_item(&stack.item, stack.quantity) {
                                        Ok(value) => total = total.map(|sum| sum + value),
                                        Err(text) => {
                                            total = Err(text);
                                            break;
                                        }
                                    }
                                }
                            }
                            total
                        } else if let Some((id, quantity)) = sale.rsplit_once(':') {
                            quantity
                                .parse::<u32>()
                                .map_err(|_| "Invalid sale quantity.")
                                .and_then(|quantity| next.sell_item(id, quantity))
                        } else {
                            Err("Invalid sale.")
                        };
                        match result {
                            Ok(value) => {
                                p.character = next;
                                quest_changed = true;
                                notice = format!("Items sold for {value} gold.");
                            }
                            Err(text) => notice = text.into(),
                        }
                    }
                } else {
                    let Some(offer) = npc.offers.iter().find(|offer| offer.id == id) else {
                        return;
                    };
                    if offer.heal > 0. && p.character.hp >= p.character.max_hp() {
                        notice =
                    "You are already at full health. Save it for after your next adventure!".into();
                    } else if let Some(bag) = &offer.bag {
                        match p.character.purchase_bag(bag, offer.cost) {
                            Ok(capacity) => {
                                notice = format!("Bag fitted! You now have {capacity} bag slots.");
                                quest_changed = true;
                            }
                            Err(text) => notice = text.into(),
                        }
                    } else if let Some(sold) = &offer.item {
                        // A tiered offer sells the best tier of the line for the buyer's level, at that tier's price.
                        let level = p.character.level;
                        let stock = item(sold).map(|base| {
                            if offer.tiered {
                                base.family
                                    .as_deref()
                                    .and_then(|f| best_tier(f, level))
                                    .unwrap_or(base)
                            } else {
                                base
                            }
                        });
                        let cost = match stock {
                            Some(i) if offer.tiered => i.price,
                            _ => offer.cost,
                        };
                        match stock {
                            None => notice = "That item is not for sale.".into(),
                            Some(_) if p.character.gold < cost => {
                                notice = format!("You need {cost} gold for this purchase.");
                            }
                            Some(i) if !p.character.can_collect(&i.id) => {
                                notice = "Your bags are full. Make room first.".into();
                            }
                            Some(i) => {
                                p.character.gold -= cost;
                                p.character.add_item(&i.id, 1);
                                notice = format!("Bought {}.", i.name);
                                quest_changed = true;
                            }
                        }
                    } else if p.character.gold < offer.cost {
                        notice = format!("You need {} gold for this service.", offer.cost);
                    } else {
                        quest_changed = true;
                        p.character.gold -= offer.cost;
                        if offer.heal > 0. {
                            p.character.hp =
                                (p.character.hp + offer.heal).min(p.character.max_hp());
                            notice = "Feeling better? Safe travels!".into();
                        }
                        if offer.gear {
                            let (armor, weapon) = match p.character.look.class {
                                Class::Warrior => ("crimson", "sword"),
                                Class::Mage => ("apprentice", "ash"),
                                Class::Assassin => ("shadow", "daggers"),
                                Class::Priest => ("pilgrim", "mace"),
                                Class::Hunter => ("scout", "shortbow"),
                            };
                            let mut fitted = p.character.clone();
                            for (kind, variant) in [("armor", armor), ("weapon", weapon)] {
                                let i = equipment(p.character.look.class, kind, variant).unwrap();
                                if fitted.quantity(&i.id) == 0 {
                                    fitted.add_item(&i.id, 1);
                                }
                            }
                            match fitted.equip_owned(armor, weapon) {
                                Ok(()) => {
                                    p.character = fitted;
                                    notice = "Starter gear fitted! Hunt enemies for rare upgrades."
                                        .into();
                                }
                                Err(text) => notice = text.into(),
                            }
                        }
                    }
                }
            }
        }
        let _ = p
            .peer
            .try_send(json!({"type":"dialogue","npc":npc,"notice":notice,"gold":p.character.gold,"level":p.character.level,"quests":p.character.quests,"inventory":p.character.inventory,"equipment":p.character.equipment,"bags":p.character.bags,"bagCapacity":p.character.bag_capacity(),"look":p.character.look}));
        let actor = p.character.id.clone();
        let point = p.character.point();
        if levels > 0 {
            self.level_up_event(&actor, point, levels);
        }
        if quest_changed {
            self.save();
        }
    }
    fn start_attack(&mut self, session: u64) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        if p.character.hp <= 0. || p.cooldown > 0. || p.dash > 0. {
            return;
        }
        p.combat_left = 5.;
        p.attack = 0.0001;
        p.hit = false;
        p.cooldown = p.character.attack_cooldown() / (1. + p.buff(BuffKind::Haste));
        let kind = if p.character.look.class.ranged() {
            "cast"
        } else {
            "swing"
        };
        let id = p.character.id.clone();
        let point = p.character.point();
        self.event(kind, &id, point, 0., false);
    }
    pub fn step(&mut self) {
        self.time += TICK;
        self.tick += 1;
        self.update_king_spawn();
        self.update_instances();
        self.update_ambient();
        self.update_mercenaries();
        self.update_escorts();
        self.update_holds();
        self.update_chimes();
        let sessions: Vec<_> = self.players.keys().copied().collect();
        for session in sessions {
            self.update_food(session);
            self.update_player(session);
        }
        // Players pass through actors; enemies yield before their own movement.
        self.separate_enemies();
        self.pursuit.retain(&self.players);
        for i in 0..self.slimes.len() {
            if !self.zone_idle(self.slimes[i].zone) {
                self.update_slime(i);
            }
        }
        self.update_bolts();
        self.update_enemy_bolts();
        self.update_drops();
        self.update_rolls();
        let stale: Vec<_> = self
            .players
            .iter()
            .filter(|(_, p)| {
                p.merc.is_none()
                    && p.ambient.is_none()
                    && (p.peer.is_closed() || p.peer.capacity() == 0)
            })
            .map(|(id, _)| *id)
            .collect();
        for session in stale {
            self.leave(session);
        }
        if self.tick.is_multiple_of(10) {
            self.update_social();
        }
        if self.tick.is_multiple_of(100) {
            self.save();
        }
    }
    fn update_player(&mut self, session: u64) {
        self.update_resource(session);
        let p = self.players.get_mut(&session).unwrap();
        p.cooldown = (p.cooldown - TICK).max(0.);
        p.hurt = (p.hurt - TICK).max(0.);
        p.dash_cd = (p.dash_cd - TICK).max(0.);
        p.skill_cd.retain(|_, left| {
            *left -= TICK;
            *left > 0.
        });
        p.buffs.retain_mut(|b| {
            b.left -= TICK;
            b.left > 0.
        });
        if p.character.spark_travel.is_some() {
            self.update_spark(session);
            return;
        }
        if p.character.hp <= 0. {
            p.moving = false;
            p.dead_time += TICK;
            p.stop();
            if p.dead_time >= 3.2 {
                let map = &self.maps[p.character.zone];
                let mut point = map.spawn;
                map.collide(&mut point, PLAYER_RADIUS);
                p.character.x = point.x;
                p.character.y = point.y;
                p.character.hp = p.character.max_hp();
                p.character.reset_resource();
                p.combat_left = 0.;
                p.dead_time = 0.;
                p.attack = 0.;
                p.cooldown = 0.;
                let id = p.character.id.clone();
                self.event("respawn", &id, point, 0., false);
            }
            return;
        }
        if self.time - p.last_hurt > 5. {
            p.character.hp = (p.character.hp + 3. * TICK).min(p.character.max_hp());
        }
        let public = self
            .instances
            .iter()
            .find(|i| i.zone == p.character.zone)
            .map_or(p.character.zone, |i| i.template);
        if p.ambient.is_none() {
            p.character
                .explore_in(public, self.maps[p.character.zone].size);
            for title in sync_progression(&mut p.character, &self.maps) {
                let _ = p.peer.try_send(json!({"type":"system","text":format!(
                    "A new quest has found you: {title}. Follow it in your journal (Q)."
                )}));
            }
            for place in sync_visits(&mut p.character, &self.maps) {
                let _ = p.peer.try_send(
                    json!({"type":"notice","ok":true,"text":format!("You have reached {place}.")}),
                );
            }
        }
        // Hand-in quests follow the bag, so the journal counts what the player carries right now.
        for i in 0..p.character.quests.len() {
            if p.character.quests[i].claimed {
                continue;
            }
            let id = &p.character.quests[i].id;
            let quest = self
                .maps
                .iter()
                .flat_map(|m| m.quests.iter())
                .find(|q| &q.id == id && q.has_bring());
            if let Some(quest) = quest {
                quest.sync_bring(&mut p.character);
            }
        }
        let mut strike = false;
        if p.attack > 0. {
            p.attack += TICK;
            if !p.hit && p.attack >= p.character.look.class.impact() {
                p.hit = true;
                strike = true;
            }
            if p.attack >= p.character.look.class.duration() {
                p.attack = 0.;
            }
        }
        let mut dir = Point::default();
        let mut travel = 0.;
        let mut auto_attack = false;
        if self.time - p.input_at > 0.3 {
            p.input = Point::default();
        }
        if p.input.x != 0. || p.input.y != 0. {
            dir = p.input;
            travel = f64::INFINITY;
        } else if let Some(id) = p.target {
            if let Some(s) = self
                .slimes
                .get(id)
                .filter(|s| !s.dead && s.zone == p.character.zone)
            {
                let distance = p.character.point().distance(s.point());
                let facing = p.character.point().direction(s.point());
                if distance - s.r <= p.character.look.class.reach() {
                    p.face = facing;
                    auto_attack = true;
                } else {
                    dir = facing;
                    travel = (distance - s.r - p.character.look.class.reach()).max(0.);
                }
            } else {
                p.target = None;
            }
        } else if let Some(goal) = p.goal {
            travel = p.character.point().distance(goal);
            if travel < 0.12 {
                p.goal = None;
                travel = 0.;
            } else {
                dir = p.character.point().direction(goal);
            }
        }
        let mut distance = (p
            .escort
            .as_ref()
            .map_or(p.character.look.class.speed(), |e| e.speed())
            * (1. + p.buff(BuffKind::Haste))
            * TICK
            * if p.attack > 0. { 0.25 } else { 1. })
        .min(travel);
        let mut dash_sweep = false;
        if p.dash > 0. {
            dir = p.dash_direction;
            distance = p.dash_speed * p.dash.min(TICK);
            p.dash = (p.dash - TICK).max(0.);
            dash_sweep = p.dash_mult > 0.;
        }
        p.moving = false;
        if distance > 0. && (dir.x != 0. || dir.y != 0.) {
            let mut point = p.character.point();
            self.maps[p.character.zone].walk(&mut point, dir, distance, PLAYER_RADIUS);
            p.moving = point.distance(p.character.point()) > 1e-8;
            p.character.x = point.x;
            p.character.y = point.y;
            p.walk += TICK * 11.;
            if p.attack <= 0. {
                p.face = dir;
            }
        }
        if dash_sweep {
            self.dash_sweep(session);
        }
        if strike {
            self.strike(session);
        }
        if auto_attack {
            self.start_attack(session);
        }
        if self.players[&session].ambient.is_none() {
            self.use_portal(session);
        }
    }
    // Stepping into a portal disc moves the player; the zone is never client-chosen.
    fn use_portal(&mut self, session: u64) {
        let p = &self.players[&session];
        if p.character.hp <= 0. || self.time - p.portal_at < PORTAL_DELAY || p.escort.is_some() {
            return;
        }
        let here = p.character.point();
        let cleared = self.instance_cleared(p.character.zone);
        let Some(mut portal) = self.maps[p.character.zone]
            .portals
            .iter()
            .find(|portal| {
                (!portal.after_clear || cleared)
                    && here.distance(Point {
                        x: portal.x,
                        y: portal.y,
                    }) < portal.r
            })
            .cloned()
        else {
            return;
        };
        if portal.to >= self.maps.len() {
            return;
        }
        // A dungeon's door asks for its level, whoever you are with.
        let need = self.maps[portal.to].min_level;
        if p.character.level < need {
            let text = format!(
                "{} is for heroes of level {need} and above. You are level {}.",
                self.maps[portal.to].name, p.character.level
            );
            let p = self.players.get_mut(&session).unwrap();
            p.portal_at = self.time;
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
            return;
        }
        // A dungeon's door leads to a private copy: the party's own, or a free one.
        if self.maps[portal.to].copies > 0 {
            match self.instance_for(session, portal.to) {
                Ok(copy) => portal.to = copy,
                Err(text) => {
                    let p = self.players.get_mut(&session).unwrap();
                    p.portal_at = self.time;
                    let _ = p.peer.try_send(json!({"type":"error","text":text}));
                    return;
                }
            }
        }
        if self.is_instance(portal.to) {
            self.enter_instance(portal.to);
        }
        let p = &self.players[&session];
        let actor = p.character.id.clone();
        self.event("portal", &actor, here, 0., false);
        let mut arrival = Point {
            x: portal.tx,
            y: portal.ty,
        };
        self.maps[portal.to].collide(&mut arrival, PLAYER_RADIUS);
        let time = self.time;
        let p = self.players.get_mut(&session).unwrap();
        p.character.zone = portal.to;
        p.character.x = arrival.x;
        p.character.y = arrival.y;
        p.portal_at = time;
        p.stop();
        p.attack = 0.;
        p.dash = 0.;
        let name = self.maps[portal.to].name.clone();
        let party = self.maps[portal.to].players;
        let text = match self.maps[portal.to].levels {
            Some([low, high]) if party > 0 => format!(
                "You step through {} into {name}, a dungeon of your own. Recommended level {}, {party} players.",
                portal.name,
                if low == high {
                    low.to_string()
                } else {
                    format!("{low}–{high}")
                }
            ),
            Some([low, high]) => format!(
                "You step through {} into {name}. Recommended levels {low}–{high}.",
                portal.name
            ),
            None => format!("You step through {} into {name}.", portal.name),
        };
        let _ = p.peer.try_send(json!({"type":"system","text":text}));
        self.separate_enemies();
        self.event("portal", &actor, arrival, 0., false);
        self.save();
    }
    /// One attack roll: the server alone decides misses, crits and damage (buffs included).
    fn roll_damage(&mut self, session: u64, mult: f64) -> (f64, bool) {
        let p = &self.players[&session];
        let base = p.character.stats().0 * (1. + p.buff(BuffKind::Damage)) * mult;
        let crit_chance = (p.character.crit_chance() + p.buff(BuffKind::Crit)).min(1.);
        let hit_chance = p.character.hit_chance();
        let crit = self.random() < crit_chance;
        let damage = if self.random() < hit_chance {
            (base * DAMAGE_DEALT_SCALE * (0.8 + self.random() * 0.4) * if crit { 2. } else { 1. })
                .round()
                .max(1.)
        } else {
            0.
        };
        (damage, crit)
    }
    fn strike(&mut self, session: u64) {
        let p = &self.players[&session];
        let point = p.character.point();
        let zone = p.character.zone;
        let face = p.face;
        let class = p.character.look.class;
        let reach = class.reach();
        let (damage, crit) = self.roll_damage(session, 1.);
        if class.ranged() {
            let id = self.entity();
            let (color, size) = if class == Class::Hunter {
                ("#e8c27a", 6.)
            } else {
                ("#c5a5ff", 9.)
            };
            self.bolts.push(Bolt {
                id,
                owner: session,
                zone,
                x: point.x,
                y: point.y,
                fx: face.x,
                fy: face.y,
                t: 0.,
                color: color.into(),
                size,
                damage,
                crit,
                pierce: false,
                blast: 0.,
                hits: vec![],
                skill: String::new(),
            });
            return;
        }
        let hit: Vec<_> = self
            .slimes
            .iter()
            .filter(|s| {
                if s.dead || s.zone != zone {
                    return false;
                }
                let d = point.distance(s.point());
                let facing = point.direction(s.point());
                d - s.r < reach && (d < 0.6 || facing.x * face.x + facing.y * face.y > 0.15)
            })
            .map(|s| s.id)
            .collect();
        for id in hit {
            self.hit_slime(id, session, damage, crit);
        }
    }
    /// Announces a level gain to the zone, with the new level and the skills it unlocks.
    fn level_up_event(&self, actor: &str, point: Point, levels: u32) {
        let Some(p) = self.players.values().find(|p| p.character.id == actor) else {
            return;
        };
        let level = p.character.level;
        let unlocked =
            skills::unlocked(p.character.look.class, level.saturating_sub(levels), level);
        self.emit_zone(
            p.character.zone,
            json!({"type":"event","kind":"levelup","actor":actor,"x":point.x,"y":point.y,"value":levels as f64,"crit":false,"level":level,"unlocked":unlocked}),
        );
    }
    /// Enemies in the player's zone within `radius` of `at` (measured to the enemy's edge), nearest first.
    fn enemies_near(&self, zone: usize, at: Point, radius: f64, skip: &[usize]) -> Vec<usize> {
        let mut found: Vec<_> = self
            .slimes
            .iter()
            .filter(|s| {
                !s.dead
                    && s.zone == zone
                    && !skip.contains(&s.id)
                    && at.distance(s.point()) - s.r < radius
            })
            .map(|s| (at.distance(s.point()), s.id))
            .collect();
        found.sort_by(|a, b| a.0.total_cmp(&b.0));
        found.into_iter().map(|(_, id)| id).collect()
    }
    /// Skills are validated and resolved here; the client only names one and an aim direction.
    fn use_skill(&mut self, session: u64, id: &str, aim: Point) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        let class = p.character.look.class;
        let Some(skill) = skills::find(class, id) else {
            let _ = p.peer.try_send(
                json!({"type":"error","text":"That skill is not available to your class."}),
            );
            return;
        };
        if p.character.level < skill.level {
            let text = format!("{} unlocks at level {}.", skill.name, skill.level);
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
            return;
        }
        if p.character.hp <= 0. || p.dash > 0. || p.skill_cd.contains_key(id) {
            return;
        }
        if aim.x != 0. || aim.y != 0. {
            p.face = aim;
        }
        let face = p.face;
        let origin = p.character.point();
        let zone = p.character.zone;
        let actor = p.character.id.clone();
        let target = p.target;
        let melee = !matches!(
            skill.effect,
            Effect::Buff { .. } | Effect::Heal { .. } | Effect::Mend { .. }
        );
        // Single-target skills fizzle without spending their cooldown.
        let single = match &skill.effect {
            Effect::Strike { range, .. } | Effect::Chain { range, .. } => Some(*range),
            _ => None,
        };
        if let Some(range) = single
            && self.enemies_near(zone, origin, range, &[]).is_empty()
        {
            let p = &self.players[&session];
            let _ = p
                .peer
                .try_send(json!({"type":"error","text":"No enemy in range."}));
            return;
        }
        if let Effect::Mend { range, .. } = &skill.effect
            && self.wounded_allies(session, *range).is_empty()
        {
            let p = &self.players[&session];
            let _ = p
                .peer
                .try_send(json!({"type":"error","text":"Nobody nearby needs healing."}));
            return;
        }
        let p = self.players.get_mut(&session).unwrap();
        if p.character.resource() < skill.cost {
            let text = format!(
                "Not enough {}: {} costs {}.",
                class.resource_type(),
                skill.name,
                skill.cost
            );
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
            return;
        }
        p.character.change_resource(-skill.cost);
        p.skill_cd.insert(
            id.to_string(),
            skill.cooldown * p.character.cooldown_multiplier(),
        );
        if melee && !matches!(skill.effect, Effect::Dash { mult, .. } if mult == 0.) {
            p.combat_left = 5.;
            p.attack = 0.0001;
            p.hit = true;
            p.cooldown = p.cooldown.max(0.35);
        }
        let mut dealt = 0.;
        let mut points: Vec<[f64; 2]> = vec![];
        let mut healed = 0.;
        let mut value = 0.;
        self.cur_skill = id.to_string();
        match &skill.effect {
            Effect::Cone { reach, dot, mult } => {
                value = *reach;
                let hit: Vec<_> = self
                    .enemies_near(zone, origin, *reach, &[])
                    .into_iter()
                    .filter(|&i| {
                        let s = &self.slimes[i];
                        let d = origin.distance(s.point());
                        let facing = origin.direction(s.point());
                        d < 0.6 || facing.x * face.x + facing.y * face.y > *dot
                    })
                    .collect();
                for i in hit {
                    let (damage, crit) = self.roll_damage(session, *mult);
                    dealt += self.hit_slime(i, session, damage, crit);
                }
            }
            Effect::Nova { radius, mult } => {
                value = *radius;
                for i in self.enemies_near(zone, origin, *radius, &[]) {
                    let (damage, crit) = self.roll_damage(session, *mult);
                    dealt += self.hit_slime(i, session, damage, crit);
                }
            }
            Effect::Volley {
                count,
                spread,
                mult,
                pierce,
                blast,
                color,
                size,
            } => {
                let base = face.y.atan2(face.x);
                let ring = *spread >= std::f64::consts::TAU - 0.01;
                for n in 0..*count {
                    let offset = if ring {
                        n as f64 * std::f64::consts::TAU / *count as f64
                    } else if *count > 1 {
                        -spread / 2. + n as f64 * spread / (*count - 1) as f64
                    } else {
                        0.
                    };
                    let angle = base + offset;
                    let (damage, crit) = self.roll_damage(session, *mult);
                    let bolt_id = self.entity();
                    self.bolts.push(Bolt {
                        id: bolt_id,
                        owner: session,
                        zone,
                        x: origin.x,
                        y: origin.y,
                        fx: angle.cos(),
                        fy: angle.sin(),
                        t: 0.,
                        color: color.clone(),
                        size: *size,
                        damage,
                        crit,
                        pierce: *pierce,
                        blast: *blast,
                        hits: vec![],
                        skill: id.to_string(),
                    });
                }
                value = *count as f64;
            }
            Effect::Dash { speed, time, mult } => {
                let p = self.players.get_mut(&session).unwrap();
                p.dash_direction = face;
                p.dash = *time;
                p.dash_speed = *speed;
                p.dash_mult = *mult;
                p.dash_hits.clear();
                p.dash_skill = id.to_string();
                p.attack = 0.;
                p.hurt = 0.;
                p.stop();
                value = speed * time;
            }
            Effect::Strike { hits, mult, range } => {
                value = *hits as f64;
                for _ in 0..*hits {
                    let Some(&i) = self.enemies_near(zone, origin, *range, &[]).first() else {
                        break;
                    };
                    points.push([self.slimes[i].x, self.slimes[i].y]);
                    let (damage, crit) = self.roll_damage(session, *mult);
                    dealt += self.hit_slime(i, session, damage, crit);
                }
            }
            Effect::Chain {
                targets,
                mult,
                range,
            } => {
                let mut from = origin;
                let mut hit = vec![];
                for n in 0..*targets {
                    let reach = if n == 0 { *range } else { 4.5 };
                    let Some(&i) = self.enemies_near(zone, from, reach, &hit).first() else {
                        break;
                    };
                    hit.push(i);
                    from = self.slimes[i].point();
                    points.push([from.x, from.y]);
                    let (damage, crit) = self.roll_damage(session, *mult);
                    dealt += self.hit_slime(i, session, damage, crit);
                }
            }
            Effect::Meteor {
                range,
                radius,
                mult,
            } => {
                let aimed = target
                    .and_then(|i| self.slimes.get(i))
                    .filter(|s| !s.dead && s.zone == zone && origin.distance(s.point()) <= *range)
                    .map(|s| s.point());
                let mut center = aimed.unwrap_or(Point {
                    x: origin.x + face.x * range * 0.75,
                    y: origin.y + face.y * range * 0.75,
                });
                self.maps[zone].collide(&mut center, 0.1);
                points.push([center.x, center.y]);
                value = *radius;
                for i in self.enemies_near(zone, center, *radius, &[]) {
                    let (damage, crit) = self.roll_damage(session, *mult);
                    dealt += self.hit_slime(i, session, damage, crit);
                }
            }
            Effect::Buff {
                kind,
                amount,
                time,
                range,
            } => {
                let sessions = if *range > 0. {
                    self.allies_near(session, *range)
                } else {
                    vec![session]
                };
                self.assist_combat(session, &sessions);
                for target in sessions {
                    let p = self.players.get_mut(&target).unwrap();
                    p.buffs.retain(|b| b.id != id);
                    p.buffs.push(Buff {
                        id: id.to_string(),
                        kind: *kind,
                        amount: *amount,
                        left: *time,
                        time: *time,
                    });
                    if target != session {
                        let at = p.character.point();
                        points.push([at.x, at.y]);
                    }
                }
                value = *time;
            }
            Effect::Mend {
                mult,
                range,
                targets,
            } => {
                let mut wounded = self.wounded_allies(session, *range);
                wounded.truncate(*targets as usize);
                points = self.heal_players(session, &wounded, *mult);
            }
            Effect::Heal { fraction } => {
                let p = self.players.get_mut(&session).unwrap();
                let before = p.character.hp;
                p.character.hp =
                    (before + p.character.max_hp() * fraction).min(p.character.max_hp());
                healed = (p.character.hp - before).round();
            }
        }
        self.cur_skill.clear();
        if let Some(pulse) = &skill.pulse {
            let wounded = self.wounded_allies(session, pulse.range);
            points.extend(self.heal_players(session, &wounded, pulse.mult));
        }
        if skill.lifesteal > 0. && dealt > 0. {
            let p = self.players.get_mut(&session).unwrap();
            let before = p.character.hp;
            p.character.hp = (before + dealt * skill.lifesteal).min(p.character.max_hp());
            healed = (p.character.hp - before).round();
        }
        let origin = self.players[&session].character.point();
        self.emit_zone(
            zone,
            json!({"type":"event","kind":"skill","skill":id,"actor":actor,"x":origin.x,"y":origin.y,
                "fx":face.x,"fy":face.y,"value":value,"crit":false,"points":points,"heal":healed}),
        );
    }
    /// Sessions of the living party members (the caster included) in the caster's zone within `range`.
    fn allies_near(&self, session: u64, range: f64) -> Vec<u64> {
        let me = &self.players[&session];
        let (zone, at) = (me.character.zone, me.character.point());
        let mates = self.party_mates(&me.character.id);
        let mut found: Vec<u64> = self
            .players
            .iter()
            .filter(|(s, p)| {
                p.character.hp > 0.
                    && (**s == session
                        || (mates.contains(&p.character.id)
                            && p.character.zone == zone
                            && at.distance(p.character.point()) <= range))
            })
            .map(|(s, _)| *s)
            .collect();
        found.sort_unstable();
        found
    }
    /// Allies in range who are missing health, the most hurt (lowest fraction) first.
    fn wounded_allies(&self, session: u64, range: f64) -> Vec<u64> {
        let mut found: Vec<(f64, u64)> = self
            .allies_near(session, range)
            .into_iter()
            .filter_map(|s| {
                let c = &self.players[&s].character;
                (c.hp < c.max_hp()).then(|| (c.hp / c.max_hp(), s))
            })
            .collect();
        found.sort_by(|a, b| a.0.total_cmp(&b.0).then(a.1.cmp(&b.1)));
        found.into_iter().map(|(_, s)| s).collect()
    }
    /// Heals each session for `mult` times the caster's attack power and announces it with a `healed` event.
    /// Returns the healed players' positions for the skill's visual effect.
    fn heal_players(&mut self, caster: u64, sessions: &[u64], mult: f64) -> Vec<[f64; 2]> {
        let amount = (self.players[&caster].character.stats().0 * mult).round();
        let from = self.players[&caster].character.id.clone();
        let mut points = vec![];
        self.assist_combat(caster, sessions);
        for s in sessions {
            let Some(p) = self.players.get_mut(s) else {
                continue;
            };
            let before = p.character.hp;
            p.character.hp = (before + amount).min(p.character.max_hp());
            let (gained, at, id, zone) = (
                (p.character.hp - before).round(),
                p.character.point(),
                p.character.id.clone(),
                p.character.zone,
            );
            points.push([at.x, at.y]);
            self.emit_zone(
                zone,
                json!({"type":"event","kind":"healed","actor":id,"from":from,"x":at.x,"y":at.y,"value":gained,"crit":false}),
            );
        }
        points
    }
    /// Enemies a damaging dash passes through, each hit once.
    fn dash_sweep(&mut self, session: u64) {
        let p = &self.players[&session];
        let (point, zone, mult) = (p.character.point(), p.character.zone, p.dash_mult);
        let skip = p.dash_hits.clone();
        self.cur_skill = p.dash_skill.clone();
        for i in self.enemies_near(zone, point, 0.9, &skip) {
            let (damage, crit) = self.roll_damage(session, mult);
            self.hit_slime(i, session, damage, crit);
            if let Some(p) = self.players.get_mut(&session) {
                p.dash_hits.push(i);
            }
        }
        self.cur_skill.clear();
    }
    /// Returns the health the enemy actually lost.
    fn hit_slime(&mut self, id: usize, session: u64, damage: f64, crit: bool) -> f64 {
        let Some(p) = self.players.get(&session) else {
            return 0.;
        };
        if p.character.hp <= 0. {
            return 0.;
        }
        let actor = p.character.id.clone();
        // A mercenary's kills, loot and quest progress are its hirer's.
        let credit = self.credit_session(session);
        let credit_id = self
            .players
            .get(&credit)
            .map_or_else(|| actor.clone(), |c| c.character.id.clone());
        let s = &mut self.slimes[id];
        if s.dead || s.zone != p.character.zone {
            return 0.;
        }
        let p = self.players.get_mut(&session).unwrap();
        p.combat_left = 5.;
        if damage <= 0. {
            let point = s.point();
            self.event("miss", &actor, point, 0., false);
            return 0.;
        }
        let dealt = damage.min(s.hp);
        if p.character.look.class == Class::Warrior {
            p.character.change_resource(dealt * 0.5);
        }
        if is_elite(&s.kind) {
            s.contributors.insert(actor.clone());
            s.contributors.insert(credit_id.clone());
        }
        s.hp = (s.hp - damage).max(0.);
        s.hurt_t = 0.4;
        s.target = Some(session);
        let point = s.point();
        let killed = s.hp <= 0.;
        let xp = s.xp;
        let gold = s.gold;
        let zone = s.zone;
        let kind = s.kind.clone();
        let level = s.level;
        if killed {
            s.dead = true;
            s.die_t = 0.;
            // Nothing in a dungeon comes back until the dungeon itself resets.
            s.respawn = match kind.as_str() {
                _ if self.instances.iter().any(|i| i.zone == zone) => 1e9,
                _ if self.spawns[id].ambush.is_some() => 1e9,
                "big" => 0.,
                "cinderlord" => 180.,
                "gloomroot" | "hrungnir" | "kraken" | "hvitserk" => 300.,
                "ghostmaw" => 600.,
                "oakhorn" => 180.,
                _ => 22.,
            };
            s.state = "dead".into();
        }
        self.event_with(
            "hit",
            &actor,
            point,
            damage,
            crit,
            json!({"enemy":kind,"level":level,"skill":self.cur_skill,"killed":killed}),
        );
        if killed {
            // Quest kill credit goes to the killer, and also to every living real member of their party who is near
            // the body (the people who share the XP). Elite kills also credit nearby contributors outside the
            // party, but only for quests marked `group`. Each person is credited once.
            let contributors = self.slimes[id].contributors.clone();
            let party = self.xp_group(&credit_id, zone, point);
            for (&other, player) in &mut self.players {
                let c = &mut player.character;
                if other == credit || other == session || c.hp <= 0. || c.zone != zone {
                    continue;
                }
                if party.contains(&c.id) {
                    quest_progress(c, &self.maps[zone].quests, "kill", &kind);
                } else if is_elite(&kind)
                    && c.point().distance(point) <= 12.
                    && contributors.contains(&c.id)
                {
                    for q in self.maps[zone].quests.iter().filter(|q| q.group) {
                        quest_progress(c, std::slice::from_ref(q), "kill", &kind);
                    }
                }
            }
            if kind == "big" {
                self.next_king_spawn = self.time + self.king_spawn_delay();
            }
            let p = self.players.get_mut(&credit).unwrap();
            p.character.kills += 1;
            quest_progress(&mut p.character, &self.maps[zone].quests, "kill", &kind);
            // A party shares the XP (see `partyxp.rs`); alone, the killer's hero gets all of it.
            let (xp, levels) = self.share_xp(&credit_id, zone, point, xp, level, &kind);
            self.event_with(
                "slimeDie",
                &credit_id,
                point,
                0.,
                false,
                json!({"enemy":kind,"level":level,"xp":xp}),
            );
            if levels > 0 {
                let point = self.players[&credit].character.point();
                self.level_up_event(&credit_id, point, levels);
            }
            let value = if gold > 0 {
                gold
            } else {
                3 + (self.random() * 4.) as u32
            };
            self.gold_drop(&credit_id, zone, point, value);
            self.loot_drop(&credit_id, zone, point, material(&kind));
            if is_boss(&kind) {
                self.boss_loot(&credit_id, &kind, zone, point);
            }
            let cathedral = crate::cathedral::enemy(&self.maps[zone].final_boss).is_some();
            if (cathedral
                && is_boss(&kind)
                && self
                    .slimes
                    .iter()
                    .filter(|s| s.zone == zone && is_boss(&s.kind))
                    .all(|s| s.dead))
                || (!cathedral
                    && !self.maps[zone].final_boss.is_empty()
                    && self.maps[zone].final_boss == kind)
            {
                self.clear_instance(zone, point);
            }
            if is_elite(&kind) && !self.is_instance(zone) {
                for rarity in ["uncommon", "rare", "epic", "common", "legendary"] {
                    if self.random() < outdoor_elite_drop_chance(rarity) {
                        let choice = self.random();
                        if let Some(i) = equipment_of_rarity(rarity, level, choice) {
                            self.loot_drop(&credit_id, zone, point, &i.id);
                        }
                    }
                }
            } else {
                let chance = self.random();
                let choice = self.random();
                if let Some(i) = roll_equipment(&kind, level, chance, choice) {
                    self.loot_drop(&credit_id, zone, point, &i.id);
                }
            }
        }
        dealt
    }
    /// One random piece across all classes per boss slot pool. Party members roll just as for world gear;
    /// alone, the credited hero (the hirer for a mercenary kill) owns it.
    fn boss_loot(&mut self, owner: &str, kind: &str, zone: usize, point: Point) {
        for slots in boss_slots(kind) {
            let choice = self.random();
            if let Some(piece) = boss_piece_for(kind, slots, choice) {
                self.loot_drop(owner, zone, point, &piece.id);
            }
        }
    }
    fn item_drop(&mut self, owner: &str, zone: usize, point: Point, item_id: &str, quantity: u32) {
        let id = self.entity();
        self.drops.push(Drop {
            id,
            owner: owner.into(),
            zone,
            x: point.x,
            y: point.y,
            z: 8.,
            value: 0,
            item: Some(item_id.into()),
            quantity,
            t: 0.,
            col: rarity_color(item(item_id).map_or("common", |i| i.rarity.as_str())),
            group: vec![],
        });
    }
    fn update_slime(&mut self, id: usize) {
        let wander = self.random();
        let angle = self.random() * std::f64::consts::TAU;
        let zone = self.slimes[id].zone;
        let dungeon = self.instance_at(zone).map(|i| i.template);
        let bodies = self.actor_bodies(zone, None, Some(id));
        // A respawning enemy rolls a fresh level; kings come from the shared timer instead.
        let respawn_level = {
            let s = &self.slimes[id];
            (s.dead && s.kind != "big" && s.respawn - TICK <= 0.).then(|| s.kind.clone())
        }
        .map(|kind| self.roll_level(&kind));
        let map = &self.maps[zone];
        let s = &mut self.slimes[id];
        if s.target.is_some_and(|session| {
            self.players
                .get(&session)
                .is_some_and(|p| p.character.spark_travel.is_some())
        }) {
            s.target = None;
        }
        let (windup, cooldown, charge_speed, awareness) = Slime::attack_profile(&s.kind);
        let hunting = dungeon.is_some() || s.hunt;
        s.hurt_t = (s.hurt_t - TICK).max(0.);
        s.rec_t = (s.rec_t - TICK).max(0.);
        s.land_t = (s.land_t - TICK).max(0.);
        if s.dead {
            s.die_t += TICK;
            if s.kind == "big" {
                // Kings use the shared rare-spawn timer, never the ordinary respawn loop.
                return;
            }
            s.respawn -= TICK;
            if s.respawn <= 0. {
                let spawn = &self.spawns[id];
                let mut enemy = Slime::with_level(id, spawn, respawn_level.unwrap_or(s.level));
                if let Some(point) = free_actor_position(map, enemy.point(), enemy.r, &bodies, true)
                {
                    enemy.x = point.x;
                    enemy.y = point.y;
                    *s = enemy;
                }
            }
            return;
        }
        s.st -= TICK;
        s.atk_cd = (s.atk_cd - TICK).max(0.);
        s.blink -= TICK;
        if s.blink < -0.15 {
            s.blink = 2. + wander * 3.;
        }
        s.hop_v -= 20. * TICK;
        s.hop = (s.hop + s.hop_v * TICK).max(0.);
        if s.hop <= 0. {
            if s.hop_v < 0. {
                s.land_t = 0.15;
            }
            s.hop_v = 0.;
        }
        let nearest = self
            .players
            .iter()
            .filter(|(_, p)| {
                p.character.hp > 0.
                    && p.character.zone == zone
                    && p.character.spark_travel.is_none()
                    && !map.in_city(p.character.point())
            })
            .map(|(id, p)| {
                (
                    *id,
                    p.character.point(),
                    s.point().distance(p.character.point()),
                )
            })
            .filter(|(_, _, d)| *d < awareness || (hunting && s.target.is_some()))
            .min_by(|a, b| a.2.total_cmp(&b.2));
        let target = s.target.and_then(|id| {
            self.players
                .get(&id)
                .filter(|p| {
                    p.character.hp > 0.
                        && p.character.zone == zone
                        && p.character.spark_travel.is_none()
                        && !map.in_city(p.character.point())
                })
                .map(|p| {
                    (
                        id,
                        p.character.point(),
                        s.point().distance(p.character.point()),
                    )
                })
        });
        let target = target.filter(|(_, _, d)| hunting || *d < 9.).or(nearest);
        if s.state != "return"
            && s.state != "windup"
            && s.state != "lunge"
            && let Some((id, _, _)) = target
        {
            s.target = Some(id);
            s.state = "chase".into();
        }
        let speed = Slime::stats(&s.kind).2;
        let damage = s.damage;
        let mut goal = None;
        let mut movement = speed * TICK;
        let mut hit = None;
        // Set when the windup of a ranged attack ends: where to shoot. A ground-pound lists everyone it lands on.
        let mut fire = None;
        let mut slammed: Vec<u64> = vec![];
        let mut slam_now = false;
        let ranged = Slime::ranged(&s.kind);
        let slam = Slime::slam_radius(&s.kind);
        match s.state.as_str() {
            "idle" if s.st <= 0. => {
                s.goal = Point {
                    x: s.hx + angle.cos() * (1. + wander * 3.),
                    y: s.hy + angle.sin() * (1. + wander * 3.),
                };
                s.state = "wander".into();
                s.st = 3.;
            }
            "wander" => {
                if s.st <= 0. || s.point().distance(s.goal) < 0.3 {
                    s.state = "idle".into();
                    s.st = 1. + wander * 2.5;
                } else {
                    goal = Some(s.goal);
                    movement *= 0.55;
                }
            }
            "chase" => {
                if let Some((_, point, d)) = target
                    .filter(|_| hunting || s.point().distance(Point { x: s.hx, y: s.hy }) < 14.)
                {
                    let attack_reach = ranged
                        .as_ref()
                        .map_or(1.15 + s.r + if slam > 0. { 0.9 } else { 0. }, |r| r.range);
                    let visible = dungeon.is_none()
                        || d > attack_reach
                        || pursuit::clear_line(map, s.point(), point, s.r);
                    let shoots = ranged.as_ref().is_some_and(|r| {
                        visible && d > Slime::melee_inside(&s.kind) + s.r && d < r.range * 3.
                    });
                    if let (true, Some(r)) = (shoots, ranged.as_ref()) {
                        if d <= r.range && s.atk_cd <= 0. {
                            s.state = "windup".into();
                            s.st = windup;
                            s.goal = point;
                            s.volley = true;
                        } else if d > r.range * 0.85 {
                            goal = Some(point);
                        } else if d < r.range * 0.35
                            && matches!(
                                s.kind.as_str(),
                                "archer" | "acolyte" | "crow" | "weaver" | "skyray"
                            )
                        {
                            // Too close for comfort: back away from the hero while the shot recovers.
                            let away = point.direction(s.point());
                            goal = Some(Point {
                                x: s.x + away.x * 3.,
                                y: s.y + away.y * 3.,
                            });
                            movement *= 0.8;
                        }
                    } else if visible
                        && d < 1.15 + s.r + if slam > 0. { 0.9 } else { 0. }
                        && s.atk_cd <= 0.
                    {
                        s.state = "windup".into();
                        s.st = windup;
                        s.goal = point;
                        s.volley = false;
                    } else {
                        goal = Some(point);
                    }
                } else {
                    s.state = "return".into();
                    s.target = None;
                    s.contributors.clear();
                }
            }
            "windup" => {
                if s.st <= 0. {
                    s.state = "lunge".into();
                    s.st = 0.3;
                    s.hit = false;
                    s.hop_v = 6.;
                    if let Some((_, point, _)) = target {
                        s.goal = point;
                    }
                }
            }
            "lunge" if s.volley => {
                // A shot: stand still, release once.
                if !s.hit {
                    s.hit = true;
                    fire = Some(s.goal);
                }
                if s.st <= 0. {
                    s.state = "chase".into();
                    s.atk_cd = cooldown;
                    s.rec_t = 0.22;
                }
            }
            "lunge" if slam > 0. => {
                // A ground-pound: everyone inside the radius is hit at the instant the windup ends.
                if !s.hit {
                    s.hit = true;
                    slam_now = true;
                    let centre = s.point();
                    slammed = self
                        .players
                        .iter()
                        .filter(|(_, p)| {
                            p.character.hp > 0.
                                && p.character.zone == zone
                                && p.character.point().distance(centre) <= slam + PLAYER_RADIUS
                        })
                        .map(|(id, _)| *id)
                        .collect();
                }
                if s.st <= 0. {
                    s.state = "chase".into();
                    s.atk_cd = cooldown;
                    s.rec_t = 0.22;
                }
            }
            "lunge" => {
                goal = Some(s.goal);
                movement = charge_speed * TICK;
                if let Some((id, _, d)) = target
                    && !s.hit
                    && d < 0.9 + s.r
                {
                    s.hit = true;
                    hit = Some(id);
                }
                if s.st <= 0. {
                    s.state = "chase".into();
                    s.atk_cd = cooldown;
                    s.rec_t = 0.22;
                }
            }
            "return" => {
                s.contributors.clear();
                let home = Point { x: s.hx, y: s.hy };
                if s.point().distance(home) < 0.4 {
                    s.state = "idle".into();
                    s.st = 1.;
                    s.hp = if matches!(
                        s.kind.as_str(),
                        "cinderlord"
                            | "gloomroot"
                            | "oakhorn"
                            | "hrungnir"
                            | "kraken"
                            | "hvitserk"
                            | "ghostmaw"
                    ) || is_boss(&s.kind)
                    {
                        s.max_hp
                    } else {
                        (s.hp + s.max_hp * 0.5).min(s.max_hp)
                    };
                } else {
                    goal = Some(home);
                }
            }
            _ => {}
        }
        if let Some(mut goal) = goal {
            if let Some(template) = dungeon
                && s.state == "chase"
                && let Some((session, point, _)) = target
                && goal.distance(point) < 1e-8
                && let Some(waypoint) = self
                    .pursuit
                    .toward(map, template, s, session, point, self.time)
            {
                goal = waypoint;
            }
            let mut point = s.point();
            let direction = point.direction(goal);
            movement = movement.min(point.distance(goal));
            walk_with_actors(map, &mut point, direction, movement, s.r, &bodies);
            if map.in_city(point) {
                point = s.point();
                s.target = None;
                s.state = "return".into();
            }
            s.x = point.x;
            s.y = point.y;
            s.dir = if direction.x - direction.y >= 0. {
                1.
            } else {
                -1.
            };
            if s.hop <= 0. && s.state != "lunge" {
                s.hop_v = 4.;
            }
        }
        let point = s.point();
        let (kind, level) = (s.kind.clone(), s.level);
        if let Some(session) = hit {
            self.hurt_player_by(session, damage, point, &kind, level);
        }
        if slam_now {
            // The ring is announced to the zone once, on the tick the pound lands.
            self.emit_zone(
                zone,
                json!({"type":"event","kind":"slam","actor":"","x":point.x,"y":point.y,"value":slam,"crit":false}),
            );
        }
        for session in slammed {
            self.hurt_player_by(
                session,
                damage * Slime::slam_factor(&kind),
                point,
                &kind,
                level,
            );
        }
        if let (Some(aim), Some(r)) = (fire, ranged) {
            self.fire_enemy_bolts(id, aim, &r);
        }
    }
    #[cfg(test)]
    fn hurt_player(&mut self, session: u64, damage: f64, from: Point) {
        self.hurt_player_by(session, damage, from, "", 0);
    }
    /// `enemy` is the attacker's kind and `level` its level, shown in the system log.
    fn hurt_player_by(&mut self, session: u64, damage: f64, _from: Point, enemy: &str, level: u32) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        if p.character.spark_travel.is_some() {
            return;
        }
        if p.character.hp > 0. && !self.maps[p.character.zone].in_city(p.character.point()) {
            self.players.get_mut(&session).unwrap().combat_left = 5.;
        }
        let p = &self.players[&session];
        if self.god_mode
            || p.god
            || p.character.hp <= 0.
            || self.maps[p.character.zone].in_city(p.character.point())
            || p.dash > 0.
            || self.time - p.last_hurt < 0.65
        {
            return;
        }
        // Being attacked counts as combat even when god mode or a dodge prevents damage.
        let dodge_chance = (p.character.dodge_chance() + p.buff(BuffKind::Dodge)).min(0.95);
        let actor = p.character.id.clone();
        let point = p.character.point();
        if dodge_chance > 0. && self.random() < dodge_chance {
            self.players.get_mut(&session).unwrap().last_hurt = self.time;
            self.event_with(
                "dodge",
                &actor,
                point,
                0.,
                false,
                json!({"enemy":enemy,"level":level}),
            );
            return;
        }
        let p = self.players.get_mut(&session).unwrap();
        let shield = p.buff(BuffKind::Shield).min(0.8);
        let mut value = ((damage - p.character.stats().1).max(1.) * DAMAGE_TAKEN_SCALE)
            .round()
            .max(1.);
        if shield > 0. {
            value = (value * (1. - shield)).round().max(1.);
        }
        let taken = value.min(p.character.hp);
        if p.character.look.class == Class::Warrior {
            p.character.change_resource(taken);
        }
        p.character.hp = (p.character.hp - value).max(0.);
        p.last_hurt = self.time;
        p.hurt = 0.25;
        let point = p.character.point();
        let actor = p.character.id.clone();
        let dead = p.character.hp <= 0.;
        if dead {
            p.dead_time = 0.;
            p.attack = 0.;
            p.buffs.clear();
            p.stop();
            p.apply_death_penalty();
        }
        self.event_with(
            "hurt",
            &actor,
            point,
            value,
            false,
            json!({"enemy":enemy,"level":level}),
        );
        if dead {
            self.event_with(
                "death",
                &actor,
                point,
                0.,
                false,
                json!({"enemy":enemy,"level":level}),
            );
            self.save();
        }
    }
    fn update_bolts(&mut self) {
        let mut bolts = std::mem::take(&mut self.bolts);
        for b in &mut bolts {
            if !self
                .players
                .get(&b.owner)
                .is_some_and(|p| p.character.hp > 0.)
            {
                b.t = 1.;
                continue;
            }
            let start = Point { x: b.x, y: b.y };
            b.x += b.fx * 12. * TICK;
            b.y += b.fy * 12. * TICK;
            b.t += TICK;
            let end = Point { x: b.x, y: b.y };
            let mut hit: Vec<_> = self
                .slimes
                .iter()
                .filter(|s| {
                    !s.dead
                        && s.zone == b.zone
                        && !b.hits.contains(&s.id)
                        && segment_distance(s.point(), start, end) < s.r + 0.22
                })
                .map(|s| (start.distance(s.point()), s.id))
                .collect();
            hit.sort_by(|a, c| a.0.total_cmp(&c.0));
            if !b.pierce {
                hit.truncate(1);
            }
            self.cur_skill = b.skill.clone();
            for (_, id) in hit {
                b.hits.push(id);
                if b.blast > 0. {
                    // The explosion centres on the first enemy touched and hits everything near it.
                    let center = self.slimes[id].point();
                    for near in self.enemies_near(b.zone, center, b.blast, &[]) {
                        self.hit_slime(near, b.owner, b.damage, b.crit);
                    }
                } else {
                    self.hit_slime(id, b.owner, b.damage, b.crit);
                }
                if !b.pierce {
                    b.t = 1.;
                }
            }
            self.cur_skill.clear();
        }
        bolts.retain(|b| b.t < 0.65);
        self.bolts = bolts;
    }
    fn update_drops(&mut self) {
        let mut taken = vec![];
        for i in 0..self.drops.len() {
            self.drops[i].t += TICK;
            if self.drops[i].t < 0.6 {
                continue;
            }
            let (point, zone) = (self.drops[i].point(), self.drops[i].zone);
            // The nearest hero who may take it; a party's pile is open to every member.
            let nearest = self
                .players
                .iter()
                .filter(|(_, p)| {
                    p.merc.is_none()
                        && p.character.hp > 0.
                        && p.character.zone == zone
                        && p.character.spark_travel.is_none()
                        && self.drops[i].open_to(&p.character.id)
                })
                .map(|(&s, p)| (s, p.character.point()))
                .min_by(|a, b| point.distance(a.1).total_cmp(&point.distance(b.1)));
            let Some((session, at)) = nearest else {
                continue;
            };
            let distance = point.distance(at);
            if distance < 3. {
                let dir = point.direction(at);
                let travel = (9. * TICK).min(distance);
                let d = &mut self.drops[i];
                d.x += dir.x * travel;
                d.y += dir.y * travel;
                if distance < 0.5 {
                    taken.push((i, session));
                }
            }
        }
        let mut rewards = vec![];
        let mut spent = vec![];
        for (i, session) in taken {
            if self.collect_drop(i, session, &mut rewards) {
                spent.push(i);
            }
        }
        for i in spent {
            self.drops[i].t = 61.;
        }
        self.drops.retain(|d| d.t < 60.);
        if !rewards.is_empty() {
            self.save();
        }
        for (id, p, value, item_id, quantity, by) in rewards {
            if let Some(item_id) = item_id {
                self.emit_zone(
                    self.zone_of(&id),
                    json!({"type":"event","kind":"itemPickup","actor":id,"x":p.x,"y":p.y,
                    "item":item_id,"quantity":quantity,"name":item(&item_id).map(|i| &i.name),"by":by}),
                );
            } else {
                self.event_with("pickup", &id, p, value as f64, false, json!({"by":by}));
            }
        }
    }
    pub async fn run(
        mut self,
        mut commands: mpsc::Receiver<Command>,
        snapshots: watch::Sender<Value>,
    ) {
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(50));
        interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
        loop {
            tokio::select! {
                _=interval.tick()=>{ self.step(); if self.tick.is_multiple_of(2) {snapshots.send_replace(self.snapshot());} }
                command=commands.recv()=>match command {
                    Some(Command::Join{session,identity,peer,reply})=>{let _=reply.send(self.join_as(session,identity,peer));}
                    Some(Command::Message{session,message})=>self.message(session,message),
                    Some(Command::Leave{session})=>self.leave(session),
                    Some(Command::Shutdown{reply})=>{self.save();let _=reply.send(());break;}
                    None=>{self.save();break;}
                }
            }
        }
    }
}
fn same_cell(a: Point, b: Point) -> bool {
    a.x.floor() == b.x.floor() && a.y.floor() == b.y.floor()
}

fn actor_blocked(point: Point, radius: f64, bodies: &[(Point, f64)]) -> bool {
    bodies
        .iter()
        .any(|(other, r)| same_cell(point, *other) || point.distance(*other) < radius + r - 1e-8)
}

fn free_actor_position(
    map: &Map,
    origin: Point,
    radius: f64,
    bodies: &[(Point, f64)],
    enemy: bool,
) -> Option<Point> {
    let clear = |mut point: Point| {
        map.collide(&mut point, radius);
        let mut checked = point;
        map.collide(&mut checked, radius);
        (point.distance(checked) < 1e-8
            && !actor_blocked(point, radius, bodies)
            && (!enemy || !map.in_city(point)))
        .then_some(point)
    };
    if let Some(point) = clear(origin) {
        return Some(point);
    }
    for ring in 1_i32..=16 {
        let mut candidates = vec![];
        for dx in -ring..=ring {
            for dy in -ring..=ring {
                if dx.abs().max(dy.abs()) == ring {
                    candidates.push(Point {
                        x: origin.x.floor() + dx as f64 + 0.5,
                        y: origin.y.floor() + dy as f64 + 0.5,
                    });
                }
            }
        }
        candidates.sort_by(|a, b| origin.distance(*a).total_cmp(&origin.distance(*b)));
        if let Some(point) = candidates.into_iter().find_map(clear) {
            return Some(point);
        }
    }
    None
}

fn walk_with_actors(
    map: &Map,
    point: &mut Point,
    direction: Point,
    distance: f64,
    radius: f64,
    bodies: &[(Point, f64)],
) {
    let steps = (distance.abs() / 0.1).ceil().max(1.) as usize;
    let dx = direction.x * distance / steps as f64;
    let dy = direction.y * distance / steps as f64;
    for _ in 0..steps {
        let previous = *point;
        // Full motion first; slide along a blocked actor's tile on either axis.
        for offset in [
            Point { x: dx, y: dy },
            Point { x: dx, y: 0. },
            Point { x: 0., y: dy },
        ] {
            let mut next = previous;
            map.walk(
                &mut next,
                normalize(offset.x, offset.y),
                offset.x.hypot(offset.y),
                radius,
            );
            if !actor_blocked(next, radius, bodies)
                && bodies
                    .iter()
                    .all(|(other, r)| segment_distance(*other, previous, next) >= radius + r - 1e-8)
            {
                *point = next;
                break;
            }
        }
    }
}

// Only called after the NPC's range, living-player and cooldown checks.
fn quest_action(character: &mut Character, quest: &Quest, action: &str) -> (String, u32, bool) {
    let refused = |text: &str| (text.to_owned(), 0, false);
    if !quest.unlocked(character) {
        return refused("Finish the earlier quest first.");
    }
    if action == "accept" && quest.auto_level.is_some() {
        return refused("This quest finds you by itself when you are ready for it.");
    }
    let prior = character.quests.iter().position(|q| q.id == quest.id);
    match action {
        "accept" => {
            if prior.is_some_and(|i| !character.quests[i].claimed || !quest.repeatable) {
                return refused("You have already taken this quest.");
            }
            let progress = QuestProgress {
                id: quest.id.clone(),
                counts: vec![0; quest.objectives.len()],
                claimed: false,
                completions: prior.map_or(0, |i| character.quests[i].completions),
            };
            if let Some(i) = prior {
                character.quests[i] = progress;
            } else {
                character.quests.push(progress);
            }
            quest.sync_bring(character);
            (
                format!(
                    "Quest accepted: {}. Follow it in your journal (Q).",
                    quest.title
                ),
                0,
                true,
            )
        }
        "claim" => {
            let Some(i) = prior else {
                return refused("Accept this quest before collecting its reward.");
            };
            quest.sync_bring(character);
            if !quest.ready(&character.quests[i]) {
                return refused("Complete the objectives before collecting your reward.");
            }
            let mut next = character.clone();
            quest.take_bring(&mut next);
            if let Some(id) = &quest.reward_item {
                if !next.can_collect(id) {
                    return refused("Your bags are full. Make room for the quest reward.");
                }
                next.add_item(id, 1);
            }
            *character = next;
            character.quests[i].claimed = true;
            character.quests[i].completions = character.quests[i].completions.saturating_add(1);
            character.gold = character.gold.saturating_add(quest.reward_gold);
            let levels = character.grant_xp(quest.reward_xp);
            (
                format!(
                    "Quest complete: {}! +{} XP and +{} gold.{}",
                    quest.title,
                    quest.reward_xp,
                    quest.reward_gold,
                    quest
                        .reward_item
                        .as_deref()
                        .and_then(item)
                        .map_or(String::new(), |i| format!(" Received {}.", i.name))
                ),
                levels,
                true,
            )
        }
        _ => refused("Unknown quest action."),
    }
}

fn segment_distance(p: Point, a: Point, b: Point) -> f64 {
    let dx = b.x - a.x;
    let dy = b.y - a.y;
    let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy).max(1e-12);
    p.distance(Point {
        x: a.x + dx * t.clamp(0., 1.),
        y: a.y + dy * t.clamp(0., 1.),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    // Fixed levels keep health, damage and XP exact; level rolls have their own tests.
    fn world() -> World {
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
    }
    // The zones a client knows: the file's zones, not the extra private copies of a dungeon.
    fn zone_count(w: &World) -> usize {
        w.maps.iter().filter(|m| m.template.is_none()).count()
    }
    fn join(w: &mut World, id: u64, class: Class) -> mpsc::Receiver<Value> {
        let (tx, rx) = mpsc::channel(256);
        let look = Look {
            class,
            ..Look::default()
        };
        w.join(id, None, Some(look), tx).unwrap();
        rx
    }
    fn quest_interact(w: &mut World, npc: &str, offer: Option<&str>) {
        let zone = w.players[&1].character.zone;
        let n = w.maps[zone].npcs.iter().find(|n| n.id == npc).unwrap();
        w.time += 0.6;
        let here = n.position_at(w.time);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = here.x;
        c.y = here.y;
        w.interact(1, npc, offer);
    }

    #[test]
    fn cinderlord_credits_nearby_living_contributors_only_for_the_group_quest() {
        // contributor 2 is valid, 3 never hits, 4 is dead, 5 is far away, 6 is in another zone.
        let mut w = world();
        let id = w
            .slimes
            .iter()
            .position(|s| s.kind == "cinderlord")
            .unwrap();
        let point = w.slimes[id].point();
        let q = w.maps[1]
            .quests
            .iter()
            .find(|q| q.id == "crags_cinderlord")
            .unwrap()
            .clone();
        let _receivers: Vec<_> = (1..=6)
            .map(|session| join(&mut w, session, Class::Warrior))
            .collect();
        for session in 1..=6 {
            let c = &mut w.players.get_mut(&session).unwrap().character;
            c.zone = 1;
            c.x = point.x + 2.;
            c.y = point.y;
            assert!(quest_action(c, &q, "accept").2);
            c.quests.push(QuestProgress {
                id: "crags_bounty".into(),
                counts: vec![0],
                ..Default::default()
            });
            if session != 3 {
                w.hit_slime(id, session, 1., false);
            }
        }
        w.players.get_mut(&4).unwrap().character.hp = 0.;
        w.players.get_mut(&5).unwrap().character.x = point.x - 20.;
        w.players.get_mut(&6).unwrap().character.zone = 0;
        w.hit_slime(id, 1, 10000., false);
        for session in 1..=6 {
            let c = &w.players[&session].character;
            assert_eq!(
                c.quests[0].counts,
                vec![u32::from(session <= 2)],
                "session {session}"
            );
            assert_eq!(
                c.quests[1].counts,
                vec![u32::from(session == 1)],
                "ordinary bounty stays killer-only"
            );
            assert_eq!(c.kills, u32::from(session == 1));
        }
        assert_eq!(w.slimes[id].respawn, 180.);
        assert!(w.slimes[id].elite);
        assert!(
            w.drops
                .iter()
                .all(|d| d.owner == w.players[&1].character.id)
        );
        w.hit_slime(id, 2, 10000., false);
        assert_eq!(w.players[&2].character.quests[0].counts, vec![1]);
        w.slimes[id].respawn = TICK;
        w.update_slime(id);
        assert!(!w.slimes[id].dead && w.slimes[id].contributors.is_empty());
    }

    #[test]
    fn cinderlord_evade_clears_contributors_and_restores_all_health() {
        let mut w = world();
        let id = w
            .slimes
            .iter()
            .position(|s| s.kind == "cinderlord")
            .unwrap();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.players.get_mut(&1).unwrap().character.zone = 1;
        w.hit_slime(id, 1, 500., false);
        assert_eq!(w.slimes[id].contributors.len(), 1);
        w.slimes[id].state = "return".into();
        w.update_slime(id);
        assert!(w.slimes[id].contributors.is_empty());
        assert_eq!(w.slimes[id].hp, w.slimes[id].max_hp);
    }

    #[test]
    fn cinderlord_gear_reward_checks_capacity_and_is_saved_once() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(4096);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        w.players.get_mut(&1).unwrap().character.zone = 1;
        quest_interact(
            &mut w,
            "crags_captain",
            Some("quest:accept:crags_cinderlord"),
        );
        let q = w.maps[1]
            .quests
            .iter()
            .find(|q| q.id == "crags_cinderlord")
            .unwrap()
            .clone();
        let reward = q.reward_item.as_deref().unwrap();
        assert_eq!(item(reward).unwrap().rarity, "rare");
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.quests.iter_mut().find(|p| p.id == q.id).unwrap().counts = vec![1];
        for i in ITEMS.iter().filter(|i| i.kind == "material") {
            if c.bag_used() == c.bag_capacity() {
                break;
            }
            c.add_item(&i.id, 1);
        }
        assert_eq!(c.bag_used(), c.bag_capacity());
        let before = serde_json::to_value(&*c).unwrap();
        assert!(quest_action(c, &q, "claim").0.contains("bags are full"));
        assert_eq!(serde_json::to_value(&*c).unwrap(), before);
        let free = c
            .inventory
            .iter()
            .find(|s| item(&s.item).unwrap().kind == "material")
            .unwrap()
            .item
            .clone();
        c.inventory.retain(|s| s.item != free);
        let gold = c.gold;
        quest_interact(
            &mut w,
            "crags_captain",
            Some("quest:claim:crags_cinderlord"),
        );
        let saved = w.store.load(&token).unwrap().unwrap();
        assert_eq!(saved.quantity(reward), 1);
        assert_eq!(saved.gold, gold + q.reward_gold);
        assert!(
            saved
                .quests
                .iter()
                .any(|p| p.id == q.id && p.claimed && p.completions == 1)
        );
        quest_interact(
            &mut w,
            "crags_captain",
            Some("quest:claim:crags_cinderlord"),
        );
        assert_eq!(w.players[&1].character.quantity(reward), 1);
        assert_eq!(w.players[&1].character.gold, saved.gold);
    }

    #[test]
    fn cinderlord_two_level_ten_warriors_win_but_one_cannot_trade_hits() {
        for seed in [1, 42, 123] {
            for count in [1, 2] {
                let mut w = world();
                w.rng = seed;
                let id = w
                    .slimes
                    .iter()
                    .position(|s| s.kind == "cinderlord")
                    .unwrap();
                let point = w.slimes[id].point();
                for s in w.slimes.iter_mut().filter(|s| s.id != id) {
                    s.dead = true;
                    s.respawn = 10000.;
                }
                let mut receivers: Vec<_> = (1..=count)
                    .map(|session| join(&mut w, session, Class::Warrior))
                    .collect();
                for session in 1..=count {
                    let c = &mut w.players.get_mut(&session).unwrap().character;
                    c.zone = 1;
                    c.x = point.x + if session == 1 { -2. } else { 2. };
                    c.y = point.y;
                    c.level = 10;
                    c.hp = c.max_hp();
                    c.attributes.strength = 20;
                    c.attributes.accuracy = 7;
                    c.add_item("health_potion", 1);
                    w.message(session, ClientMessage::Target { id });
                }
                for _ in 0..(90. / TICK) as usize {
                    for session in 1..=count {
                        if w.players[&session].character.hp <= 0. {
                            continue;
                        }
                        let aim = w.players[&session]
                            .character
                            .point()
                            .direction(w.slimes[id].point());
                        for skill in ["battlecry", "shieldwall", "cleave", "whirlwind"] {
                            w.use_skill(session, skill, aim);
                        }
                        if w.players[&session].character.hp
                            <= w.players[&session].character.max_hp() - 100.
                        {
                            w.use_item(session, "health_potion");
                        }
                    }
                    w.step();
                    for rx in receivers.iter_mut() {
                        while rx.try_recv().is_ok() {}
                    }
                    if w.slimes[id].dead || w.players.values().all(|p| p.character.hp <= 0.) {
                        break;
                    }
                }
                assert_eq!(
                    w.slimes[id].dead,
                    count == 2,
                    "seed {seed}, {count} player(s), enemy HP {}, time {}",
                    w.slimes[id].hp,
                    w.time
                );
                if count == 2 {
                    assert!(
                        w.players.values().all(|p| p.character.hp > 0.),
                        "both survive, seed {seed}"
                    );
                }
            }
        }
    }

    #[test]
    fn gloomroot_beats_any_party_of_trained_level_twenty_warriors_without_a_healer() {
        // Warriors only (no healer, one potion each): the Colossus hits too hard to trade blows with, so a party needs a
        // healer (or a hired Priest). One to five all fall without finishing it. Seeded, deterministic.
        for count in [1usize, 2, 3, 4, 5] {
            let mut w = world();
            w.rng = 7;
            let id = w.slimes.iter().position(|s| s.kind == "gloomroot").unwrap();
            let point = w.slimes[id].point();
            assert_eq!(w.slimes[id].zone, 3);
            for s in w.slimes.iter_mut().filter(|s| s.id != id) {
                s.dead = true;
                s.respawn = 10000.;
            }
            let mut receivers: Vec<_> = (1..=count)
                .map(|session| join(&mut w, session as u64, Class::Warrior))
                .collect();
            for session in 1..=count as u64 {
                let c = &mut w.players.get_mut(&session).unwrap().character;
                c.zone = 3;
                c.x = point.x - 3. + session as f64;
                c.y = point.y;
                c.level = 20;
                c.hp = c.max_hp();
                c.attributes.strength = 40;
                c.attributes.stamina = 10;
                c.attributes.accuracy = 7;
                c.add_item("health_potion", 1);
                w.message(session, ClientMessage::Target { id });
            }
            let mut deaths = 0;
            let mut was_dead = vec![false; count + 1];
            for _ in 0..(300. / TICK) as usize {
                for session in 1..=count as u64 {
                    if w.players[&session].character.hp <= 0. {
                        continue;
                    }
                    let aim = w.players[&session]
                        .character
                        .point()
                        .direction(w.slimes[id].point());
                    for skill in [
                        "battlecry",
                        "shieldwall",
                        "cleave",
                        "whirlwind",
                        "charge",
                        "groundslam",
                    ] {
                        w.use_skill(session, skill, aim);
                    }
                    let c = &w.players[&session].character;
                    if c.hp <= c.max_hp() - 100. {
                        w.use_item(session, "health_potion");
                    }
                }
                w.step();
                for rx in receivers.iter_mut() {
                    while rx.try_recv().is_ok() {}
                }
                for (session, was) in was_dead.iter_mut().enumerate().skip(1) {
                    let dead = w.players[&(session as u64)].character.hp <= 0.;
                    deaths += usize::from(dead && !*was);
                    *was = dead;
                }
                if w.slimes[id].dead {
                    break;
                }
            }
            assert!(
                !w.slimes[id].dead,
                "{count} warrior(s) without a healer must not win: enemy HP {} of {}, time {:.0}",
                w.slimes[id].hp, w.slimes[id].max_hp, w.time
            );
            assert!(deaths >= 1, "{count} player(s): somebody falls: {deaths}");
        }
    }

    #[test]
    fn gloomroot_credits_every_nearby_contributor_pays_a_blue_ring_and_resets_whole() {
        let mut w = world();
        let id = w.slimes.iter().position(|s| s.kind == "gloomroot").unwrap();
        let point = w.slimes[id].point();
        let q = w.maps[3]
            .quests
            .iter()
            .find(|q| q.id == "fen_gloomroot")
            .unwrap()
            .clone();
        assert!(q.group && q.level == 20);
        assert_eq!(q.reward_xp, xp_to_level(20) / 10);
        let reward = q.reward_item.as_deref().unwrap();
        assert_eq!(item(reward).unwrap().rarity, "rare", "a blue piece");
        assert!(
            item(reward).unwrap().class.is_none(),
            "wearable by every class"
        );
        assert_eq!(item(reward).unwrap().required_level, 20);
        // sessions 1-5 contribute and stand close; 6 contributes from far away; 7 never hits.
        let _receivers: Vec<_> = (1..=7)
            .map(|session| join(&mut w, session, Class::Warrior))
            .collect();
        for session in 1..=7 {
            let c = &mut w.players.get_mut(&session).unwrap().character;
            c.zone = 3;
            c.x = point.x + 2.;
            c.y = point.y;
            c.quests.push(QuestProgress {
                id: "fen_hydra".into(),
                claimed: true,
                completions: 1,
                ..Default::default()
            });
            assert!(quest_action(c, &q, "accept").2, "session {session}");
            if session != 7 {
                w.hit_slime(id, session, 1., false);
            }
        }
        w.players.get_mut(&6).unwrap().character.x = point.x - 20.;
        w.hit_slime(id, 1, 1e9, false);
        for session in 1..=7 {
            let c = &w.players[&session].character;
            let progress = c.quests.iter().find(|p| p.id == "fen_gloomroot").unwrap();
            assert_eq!(
                progress.counts,
                vec![u32::from(session <= 5)],
                "session {session}"
            );
        }
        assert_eq!(w.slimes[id].respawn, 300.);
        assert!(w.slimes[id].elite);
        // The reward is the same guaranteed piece for each of the five, and a full claim saves it.
        for session in 1..=5 {
            let c = &mut w.players.get_mut(&session).unwrap().character;
            let (text, _, changed) = quest_action(c, &q, "claim");
            assert!(changed, "{text}");
            assert_eq!(c.quantity(reward), 1);
        }
        // Evading restores every point of health and forgets who helped.
        w.slimes[id].respawn = TICK;
        w.update_slime(id);
        w.hit_slime(id, 1, 5000., false);
        assert_eq!(w.slimes[id].contributors.len(), 1);
        w.slimes[id].state = "return".into();
        w.update_slime(id);
        assert!(w.slimes[id].contributors.is_empty());
        assert_eq!(w.slimes[id].hp, w.slimes[id].max_hp);
    }

    fn dialogue_notice(rx: &mut mpsc::Receiver<Value>) -> String {
        std::iter::from_fn(|| rx.try_recv().ok())
            .filter(|v| v["type"] == "dialogue")
            .last()
            .map_or_else(String::new, |v| {
                v["notice"].as_str().unwrap_or("").to_owned()
            })
    }
    fn mercs_of(w: &World) -> Vec<&Player> {
        w.players.values().filter(|p| p.merc.is_some()).collect()
    }
    fn at_giver(w: &mut World, zone: usize, npc: &str) {
        let n = w.maps[zone].npcs.iter().find(|n| n.id == npc).unwrap();
        let here = n.position_at(w.time);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = zone;
        c.x = here.x;
        c.y = here.y;
    }
    fn hire(
        w: &mut World,
        rx: &mut mpsc::Receiver<Value>,
        zone: usize,
        npc: &str,
        class: &str,
    ) -> String {
        at_giver(w, zone, npc);
        w.time += 0.6;
        w.interact(1, npc, Some(&format!("merc_{class}")));
        dialogue_notice(rx)
    }

    #[test]
    fn a_giver_hires_mercenaries_only_for_the_active_group_quest_against_gold_and_party_room() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        w.players.get_mut(&1).unwrap().character.level = 10;
        // No quest taken yet.
        let text = hire(&mut w, &mut rx, 1, "crags_captain", "mage");
        assert!(text.contains("Take this elite quest first"), "{text}");
        assert!(mercs_of(&w).is_empty());
        at_giver(&mut w, 1, "crags_captain");
        w.time += 0.6;
        w.interact(1, "crags_captain", Some("quest:accept:crags_cinderlord"));
        drain(&mut rx);
        // Too poor.
        let text = hire(&mut w, &mut rx, 1, "crags_captain", "mage");
        assert!(text.contains("250 gold"), "{text}");
        w.players.get_mut(&1).unwrap().character.gold = 600;
        let text = hire(&mut w, &mut rx, 1, "crags_captain", "mage");
        assert!(text.contains("Merc Mage joins your party"), "{text}");
        let merc = mercs_of(&w)[0];
        assert_eq!(
            (
                merc.character.look.class,
                merc.character.level,
                merc.character.look.name.as_str()
            ),
            (Class::Mage, 10, "Merc Mage")
        );
        assert!(merc.character.hp > 0. && merc.character.attributes.intellect > 0);
        assert_eq!(w.players[&1].character.gold, 350);
        let owner = w.players[&1].character.id.clone();
        assert_eq!(
            w.party_mates(&owner).len(),
            2,
            "the mercenary is in the party"
        );
        // A two-player quest is full at two.
        let text = hire(&mut w, &mut rx, 1, "crags_captain", "warrior");
        assert!(text.contains("wants 2 fighters"), "{text}");
        assert_eq!((w.players[&1].character.gold, mercs_of(&w).len()), (350, 1));
        // The mercenary is not a player: not counted online, not in the who list, not saved.
        assert_eq!(w.snapshot()["online"], 1);
        let merc_id = mercs_of(&w)[0].character.id.clone();
        w.save();
        assert!(w.store.summary(&merc_id).is_none());
        // Dismissal ends the party and the contract.
        w.time += 0.6;
        w.interact(1, "crags_captain", Some("merc_dismiss"));
        assert!(dialogue_notice(&mut rx).contains("ended"));
        assert!(mercs_of(&w).is_empty());
        assert_eq!(w.party_mates(&owner).len(), 1);
        // Another giver's offers do nothing for this quest.
        let text = hire(&mut w, &mut rx, 1, "crags_scout", "mage");
        assert!(text.is_empty() || !text.contains("joins"), "{text}");
    }

    #[test]
    fn the_five_player_quest_lets_you_pick_the_four_classes_and_fills_only_the_empty_seats() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 20;
            c.gold = 2000;
            c.quests.push(QuestProgress {
                id: "fen_hydra".into(),
                claimed: true,
                completions: 1,
                ..Default::default()
            });
        }
        at_giver(&mut w, 3, "fen_reeve");
        w.time += 0.6;
        w.interact(1, "fen_reeve", Some("quest:accept:fen_gloomroot"));
        drain(&mut rx);
        for class in ["priest", "mage", "hunter", "warrior"] {
            let text = hire(&mut w, &mut rx, 3, "fen_reeve", class);
            assert!(text.contains("joins your party"), "{class}: {text}");
        }
        let mut classes: Vec<_> = mercs_of(&w)
            .iter()
            .map(|p| p.character.look.class)
            .collect();
        classes.sort_by_key(|c| format!("{c:?}"));
        assert_eq!(
            classes,
            vec![Class::Hunter, Class::Mage, Class::Priest, Class::Warrior]
        );
        assert_eq!(w.players[&1].character.gold, 1000);
        let text = hire(&mut w, &mut rx, 3, "fen_reeve", "priest");
        assert!(text.contains("wants 5 fighters"), "{text}");
        // Two of one class get distinct names.
        w.time += 0.6;
        w.interact(1, "fen_reeve", Some("merc_dismiss"));
        drain(&mut rx);
        hire(&mut w, &mut rx, 3, "fen_reeve", "warrior");
        hire(&mut w, &mut rx, 3, "fen_reeve", "warrior");
        let mut names: Vec<_> = mercs_of(&w)
            .iter()
            .map(|p| p.character.look.name.clone())
            .collect();
        names.sort();
        assert_eq!(names, vec!["Merc Warrior", "Merc Warrior 2"]);
    }

    #[test]
    fn a_hirer_with_a_party_rents_only_the_remaining_seats() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let _rx2 = join(&mut w, 2, Class::Mage);
        let _rx3 = join(&mut w, 3, Class::Priest);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 20;
            c.gold = 2000;
            c.quests.push(QuestProgress {
                id: "fen_hydra".into(),
                claimed: true,
                completions: 1,
                ..Default::default()
            });
        }
        // Players 1, 2 and 3 form a party of three.
        let ids: Vec<String> = (1..=3)
            .map(|s| w.players[&s].character.id.clone())
            .collect();
        let first = w.players[&1].character.clone();
        w.party_add_mercenary(&ids[0], &w.players[&2].character.clone())
            .unwrap();
        w.party_add_mercenary(&ids[0], &w.players[&3].character.clone())
            .unwrap();
        assert_eq!(w.party_mates(&first.id).len(), 3);
        at_giver(&mut w, 3, "fen_reeve");
        w.time += 0.6;
        w.interact(1, "fen_reeve", Some("quest:accept:fen_gloomroot"));
        drain(&mut rx);
        assert!(hire(&mut w, &mut rx, 3, "fen_reeve", "hunter").contains("joins"));
        assert!(hire(&mut w, &mut rx, 3, "fen_reeve", "mage").contains("joins"));
        let text = hire(&mut w, &mut rx, 3, "fen_reeve", "priest");
        assert!(text.contains("already has 5"), "{text}");
        assert_eq!(mercs_of(&w).len(), 2);
        assert_eq!(w.players[&1].character.gold, 1500);
    }

    #[test]
    fn mercenaries_leave_with_their_hirer_when_the_party_breaks_and_when_the_group_objective_is_ready()
     {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 10;
            c.gold = 2000;
        }
        let owner = w.players[&1].character.id.clone();
        let start = |w: &mut World, rx: &mut mpsc::Receiver<Value>| {
            at_giver(w, 1, "crags_captain");
            w.time += 0.6;
            w.interact(1, "crags_captain", Some("quest:accept:crags_cinderlord"));
            drain(rx);
            assert!(hire(w, rx, 1, "crags_captain", "priest").contains("joins"));
        };
        start(&mut w, &mut rx);
        // Leaving the party ends the contract on the next tick.
        w.leave_party(&owner);
        w.step();
        assert!(mercs_of(&w).is_empty());
        // Completing the objective does too, before returning to claim the reward.
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .retain(|q| q.id != "crags_cinderlord");
        start(&mut w, &mut rx);
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .iter_mut()
            .find(|q| q.id == "crags_cinderlord")
            .unwrap()
            .counts = vec![1];
        w.step();
        assert!(
            mercs_of(&w).is_empty(),
            "completion ended the contract before claim"
        );
        let purse = w.players[&1].character.gold;
        assert!(hire(&mut w, &mut rx, 1, "crags_captain", "mage").contains("already complete"));
        assert_eq!(w.players[&1].character.gold, purse);
        w.time += 0.6;
        w.interact(1, "crags_captain", Some("quest:claim:crags_cinderlord"));
        drain(&mut rx);
        assert!(
            w.players[&1]
                .character
                .quests
                .iter()
                .any(|q| q.id == "crags_cinderlord" && q.claimed)
        );
        assert!(mercs_of(&w).is_empty());
        // And the hirer leaving the world takes them along.
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .retain(|q| q.id != "crags_cinderlord");
        start(&mut w, &mut rx);
        w.leave(1);
        assert!(mercs_of(&w).is_empty() && w.players.is_empty());
        assert_eq!(w.party_mates(&owner).len(), 1);
    }

    #[test]
    fn a_mercenary_follows_fights_the_hirers_target_and_everything_it_earns_is_the_hirers() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 10;
            c.gold = 600;
        }
        for s in w.slimes.iter_mut() {
            s.dead = true;
            s.respawn = 10000.;
        }
        assert!(
            hire(&mut w, &mut rx, 1, "crags_captain", "warrior").contains("Take this elite quest")
        );
        at_giver(&mut w, 1, "crags_captain");
        w.time += 0.6;
        w.interact(1, "crags_captain", Some("quest:accept:crags_cinderlord"));
        drain(&mut rx);
        assert!(hire(&mut w, &mut rx, 1, "crags_captain", "warrior").contains("joins"));
        let merc = *w.players.iter().find(|(_, p)| p.merc.is_some()).unwrap().0;
        // It keeps to its hirer: walk the hirer away and the mercenary catches up.
        let far = {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x += 12.;
            c.point()
        };
        for _ in 0..200 {
            w.step();
        }
        let d = w.players[&merc].character.point().distance(far);
        assert!(d < 4., "the mercenary follows: {d}");
        // Taking the hirer through a gate carries it along.
        w.players.get_mut(&1).unwrap().character.zone = 0;
        w.players.get_mut(&1).unwrap().character.x = 36.;
        w.players.get_mut(&1).unwrap().character.y = 60.;
        w.step();
        assert_eq!(w.players[&merc].character.zone, 0);
        w.players.get_mut(&1).unwrap().character.zone = 1;
        w.players.get_mut(&1).unwrap().character.x = 44.;
        w.players.get_mut(&1).unwrap().character.y = 80.;
        w.step();
        // A wisp attacks the hirer: the mercenary fights it even though the hirer chose no target.
        let wisp = w.slimes.iter().position(|s| s.kind == "wisp").unwrap();
        {
            let p = w.players[&1].character.point();
            let s = &mut w.slimes[wisp];
            s.dead = false;
            s.hp = 1_000_000.;
            s.max_hp = 1_000_000.;
            s.x = p.x + 3.;
            s.y = p.y;
            s.zone = 1;
            s.target = Some(1);
        }
        let before = w.slimes[wisp].hp;
        for _ in 0..100 {
            w.step();
            w.slimes[wisp].target = Some(1);
        }
        assert!(
            w.slimes[wisp].hp < before,
            "the mercenary attacked the wisp"
        );
        assert_eq!(w.players[&merc].target, Some(wisp));
        // Its kill pays the hirer: XP, a kill, the quest credit and the loot owner.
        let owner = w.players[&1].character.id.clone();
        let xp = (w.players[&1].character.level, w.players[&1].character.xp);
        w.slimes[wisp].hp = 1.;
        w.hit_slime(wisp, merc, 1000., false);
        assert!(w.slimes[wisp].dead);
        let hirer = &w.players[&1].character;
        assert_eq!(hirer.kills, 1);
        assert!((hirer.level, hirer.xp) > xp, "the hirer got the XP");
        assert_eq!(w.players[&merc].character.kills, 0);
        assert!(w.drops.iter().all(|d| d.owner == owner));
        assert!(!w.drops.is_empty());
    }

    #[test]
    fn a_priest_mercenary_mends_a_wounded_hirer_and_attackers_choose_among_mercenaries_too() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 20;
            c.gold = 600;
            c.zone = 1;
        }
        for s in w.slimes.iter_mut() {
            s.dead = true;
            s.respawn = 10000.;
        }
        at_giver(&mut w, 1, "crags_captain");
        w.time += 0.6;
        w.interact(1, "crags_captain", Some("quest:accept:crags_cinderlord"));
        drain(&mut rx);
        assert!(hire(&mut w, &mut rx, 1, "crags_captain", "priest").contains("joins"));
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.hp = p.character.max_hp() * 0.3;
            p.last_hurt = 1.0e9;
        }
        let low = w.players[&1].character.hp;
        for _ in 0..60 {
            w.step();
            w.players.get_mut(&1).unwrap().last_hurt = 1.0e9;
        }
        let now = w.players[&1].character.hp;
        // Natural regeneration is off (recent hurt); only a mend can have raised it.
        assert!(
            now > low + 10.,
            "the priest mended the hirer: {low} -> {now}"
        );
    }

    #[test]
    fn a_hired_party_beats_the_cinderlord_where_a_lone_hero_cannot() {
        // The hirer plays like the other balance tests; the single mercenary is the server's own AI.
        for (hired, expect_win) in [(false, false), (true, true)] {
            let mut w = world();
            w.rng = 11;
            let mut receivers = [join(&mut w, 1, Class::Warrior)];
            let id = w
                .slimes
                .iter()
                .position(|s| s.kind == "cinderlord")
                .unwrap();
            let point = w.slimes[id].point();
            for s in w.slimes.iter_mut().filter(|s| s.id != id) {
                s.dead = true;
                s.respawn = 10000.;
            }
            {
                let c = &mut w.players.get_mut(&1).unwrap().character;
                c.zone = 1;
                c.x = point.x - 2.;
                c.y = point.y;
                c.level = 10;
                c.gold = 500;
                c.hp = c.max_hp();
                c.attributes.strength = 20;
                c.attributes.accuracy = 7;
                c.add_item("health_potion", 1);
            }
            at_giver(&mut w, 1, "crags_captain");
            w.time += 0.6;
            w.interact(1, "crags_captain", Some("quest:accept:crags_cinderlord"));
            if hired {
                w.time += 0.6;
                w.interact(1, "crags_captain", Some("merc_warrior"));
                assert_eq!(mercs_of(&w).len(), 1);
            }
            {
                let c = &mut w.players.get_mut(&1).unwrap().character;
                c.x = point.x - 2.;
                c.y = point.y;
            }
            for p in w.players.values_mut().filter(|p| p.merc.is_some()) {
                p.character.x = point.x + 2.;
                p.character.y = point.y;
            }
            w.message(1, ClientMessage::Target { id });
            for _ in 0..(150. / TICK) as usize {
                if w.players[&1].character.hp > 0. {
                    let aim = w.players[&1]
                        .character
                        .point()
                        .direction(w.slimes[id].point());
                    for skill in ["battlecry", "shieldwall", "cleave", "whirlwind"] {
                        w.use_skill(1, skill, aim);
                    }
                    let c = &w.players[&1].character;
                    if c.hp <= c.max_hp() - 100. {
                        w.use_item(1, "health_potion");
                    }
                }
                w.step();
                for rx in receivers.iter_mut() {
                    while rx.try_recv().is_ok() {}
                }
                if w.slimes[id].dead || w.players.is_empty() {
                    break;
                }
            }
            assert_eq!(
                w.slimes[id].dead, expect_win,
                "hired {hired}: enemy HP {} of {}",
                w.slimes[id].hp, w.slimes[id].max_hp
            );
            if expect_win {
                assert_eq!(
                    w.players[&1]
                        .character
                        .quests
                        .iter()
                        .find(|q| q.id == "crags_cinderlord")
                        .unwrap()
                        .counts,
                    vec![1],
                    "the hirer gets the quest credit"
                );
            }
        }
    }

    #[test]
    fn a_hirer_with_four_mercenaries_takes_the_gloomroot_and_one_with_two_does_not() {
        // The hirer is a trained level-20 warrior; the four seats are the server's AI: a warrior, a priest, a mage and a hunter.
        for (classes, wins) in [
            (vec!["warrior", "priest", "mage", "hunter"], true),
            (vec!["warrior", "priest"], false),
        ] {
            let mut w = world();
            w.rng = 5;
            let mut receivers = [join(&mut w, 1, Class::Warrior)];
            let id = w.slimes.iter().position(|s| s.kind == "gloomroot").unwrap();
            let point = w.slimes[id].point();
            for s in w.slimes.iter_mut().filter(|s| s.id != id) {
                s.dead = true;
                s.respawn = 10000.;
            }
            {
                let c = &mut w.players.get_mut(&1).unwrap().character;
                c.level = 20;
                c.gold = 5000;
                c.attributes.strength = 40;
                c.attributes.stamina = 10;
                c.attributes.accuracy = 7;
                c.add_item("health_potion", 1);
                c.quests.push(QuestProgress {
                    id: "fen_hydra".into(),
                    claimed: true,
                    completions: 1,
                    ..Default::default()
                });
            }
            at_giver(&mut w, 3, "fen_reeve");
            w.time += 0.6;
            w.interact(1, "fen_reeve", Some("quest:accept:fen_gloomroot"));
            for class in &classes {
                w.time += 0.6;
                w.interact(1, "fen_reeve", Some(&format!("merc_{class}")));
            }
            assert_eq!(mercs_of(&w).len(), classes.len());
            {
                let c = &mut w.players.get_mut(&1).unwrap().character;
                c.x = point.x - 3.;
                c.y = point.y;
                c.hp = c.max_hp();
            }
            for (i, p) in w
                .players
                .values_mut()
                .filter(|p| p.merc.is_some())
                .enumerate()
            {
                p.character.x = point.x + 2. + i as f64;
                p.character.y = point.y + 2.;
            }
            w.message(1, ClientMessage::Target { id });
            let mut deaths = 0;
            for _ in 0..(300. / TICK) as usize {
                if w.players[&1].character.hp > 0. {
                    let aim = w.players[&1]
                        .character
                        .point()
                        .direction(w.slimes[id].point());
                    for skill in [
                        "battlecry",
                        "shieldwall",
                        "cleave",
                        "whirlwind",
                        "charge",
                        "groundslam",
                    ] {
                        w.use_skill(1, skill, aim);
                    }
                    let c = &w.players[&1].character;
                    if c.hp <= c.max_hp() - 100. {
                        w.use_item(1, "health_potion");
                    }
                }
                w.step();
                for rx in receivers.iter_mut() {
                    while rx.try_recv().is_ok() {}
                }
                deaths = deaths.max(w.players.values().filter(|p| p.character.hp <= 0.).count());
                if w.slimes[id].dead {
                    break;
                }
            }
            assert_eq!(
                w.slimes[id].dead, wins,
                "{classes:?}: enemy HP {} of {}, {deaths} deaths, time {:.0}",
                w.slimes[id].hp, w.slimes[id].max_hp, w.time
            );
            if wins {
                assert!(
                    w.time >= 120.,
                    "the fight lasts at least two minutes: {:.0} s",
                    w.time
                );
                assert!(deaths <= 3, "and lose at most three: {deaths}");
                assert_eq!(
                    w.players[&1]
                        .character
                        .quests
                        .iter()
                        .find(|q| q.id == "fen_gloomroot")
                        .unwrap()
                        .counts,
                    vec![1],
                    "the hirer is credited, whoever landed the blow"
                );
            }
        }
    }

    #[test]
    fn a_tiered_vendor_sells_the_best_tier_for_the_buyers_level_and_a_potion_needs_its_level() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Mage);
        let buy = |w: &mut World, rx: &mut mpsc::Receiver<Value>, level: u32, gold: u32| {
            {
                let c = &mut w.players.get_mut(&1).unwrap().character;
                c.level = level;
                c.gold = gold;
            }
            quest_interact(w, "apothecary", Some("buy_health_potion"));
            dialogue_notice(rx)
        };
        // Level 1: the original potion for 30 gold.
        let text = buy(&mut w, &mut rx, 1, 100);
        assert_eq!(text, "Bought Health Potion.");
        assert_eq!(w.players[&1].character.gold, 70);
        // Level 10 and 20: the stronger tiers at their own prices.
        let text = buy(&mut w, &mut rx, 10, 100);
        assert_eq!(text, "Bought Greater Health Potion.");
        assert_eq!(w.players[&1].character.gold, 40);
        let text = buy(&mut w, &mut rx, 20, 100);
        assert!(text.contains("need 110 gold"), "{text}");
        let text = buy(&mut w, &mut rx, 20, 300);
        assert_eq!(text, "Bought Superior Health Potion.");
        assert_eq!(w.players[&1].character.gold, 190);
        assert_eq!(w.players[&1].character.quantity("health_potion_l20"), 1);
        // Stew and mana follow the same rule.
        w.players.get_mut(&1).unwrap().character.gold = 500;
        quest_interact(&mut w, "baker", Some("buy_traveler_stew"));
        assert!(dialogue_notice(&mut rx).contains("Ranger's Feast"));
        quest_interact(&mut w, "apothecary", Some("buy_mana_potion"));
        assert!(dialogue_notice(&mut rx).contains("Superior Mana Potion"));
        // A potion cannot be used below its level, and is not spent.
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 5;
            c.hp = 1.;
        }
        w.use_item(1, "health_potion_l20");
        let c = &w.players[&1].character;
        assert_eq!((c.hp, c.quantity("health_potion_l20")), (1., 1));
        w.players.get_mut(&1).unwrap().character.level = 20;
        w.players.get_mut(&1).unwrap().character.hp = 1.;
        w.use_item(1, "health_potion_l20");
        let c = &w.players[&1].character;
        assert_eq!(c.quantity("health_potion_l20"), 0);
        assert!(c.hp >= 350.);
    }

    #[test]
    fn a_mercenary_drinks_its_mana_potion_when_low_and_a_health_potion_when_hurt() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 20;
            c.gold = 600;
            c.zone = 1;
        }
        for s in w.slimes.iter_mut() {
            s.dead = true;
            s.respawn = 10000.;
        }
        at_giver(&mut w, 1, "crags_captain");
        w.time += 0.6;
        w.interact(1, "crags_captain", Some("quest:accept:crags_cinderlord"));
        drain(&mut rx);
        assert!(hire(&mut w, &mut rx, 1, "crags_captain", "mage").contains("joins"));
        let merc = *w.players.iter().find(|(_, p)| p.merc.is_some()).unwrap().0;
        w.players.get_mut(&merc).unwrap().character.resource = Some(10.);
        w.step();
        let p = &w.players[&merc];
        assert_eq!(
            p.character.quantity("mana_potion_l20"),
            2,
            "it drank a mana potion"
        );
        assert!(p.character.resource() > 250.);
        // The potions share a cooldown, so a wound right after waits.
        w.players.get_mut(&merc).unwrap().character.hp = 5.;
        w.step();
        assert_eq!(w.players[&merc].character.quantity("health_potion_l20"), 3);
        w.players.get_mut(&merc).unwrap().potion_cd = 0.;
        w.step();
        assert_eq!(w.players[&merc].character.quantity("health_potion_l20"), 2);
    }

    #[test]
    fn progression_quests_come_every_five_levels_and_each_names_the_zone_it_leads_to() {
        let w = world();
        let mut found: Vec<(u32, usize)> = Vec::new();
        for (zone, area) in w.maps.iter().enumerate() {
            for q in area.quests.iter().filter(|q| q.auto_level.is_some()) {
                assert_eq!(
                    q.auto_level,
                    Some(q.level),
                    "{} arrives at its own level",
                    q.id
                );
                assert!(q.requires.is_none() && !q.repeatable, "{}", q.id);
                assert_eq!(q.objectives.len(), 1, "{}", q.id);
                assert_eq!(q.objectives[0].kind, "reach");
                assert_eq!(q.objectives[0].target, area.name, "{} leads here", q.id);
                assert!(
                    area.npcs.iter().any(|n| n.id == q.npc),
                    "{} is handed in here",
                    q.id
                );
                found.push((q.level, zone));
            }
        }
        found.sort();
        assert_eq!(
            found,
            vec![(5, 1), (10, 2), (15, 3), (20, 4), (22, 6), (30, 7), (35, 8)]
        );
    }

    #[test]
    fn a_progression_quest_arrives_at_its_level_completes_on_arrival_and_pays_at_the_captain() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let quests = |w: &World| w.players[&1].character.quests.clone();
        w.step();
        assert!(quests(&w).is_empty(), "nothing before level 5");
        w.players.get_mut(&1).unwrap().character.level = 4;
        w.step();
        assert!(quests(&w).is_empty(), "level 4 is still too early");
        // The captain cannot hand it out early either, even if a client asks.
        w.players.get_mut(&1).unwrap().character.zone = 1;
        quest_interact(&mut w, "crags_captain", Some("quest:accept:crags_onward"));
        assert!(quests(&w).is_empty(), "it is never offered");
        w.players.get_mut(&1).unwrap().character.zone = 0;
        while rx.try_recv().is_ok() {}

        w.players.get_mut(&1).unwrap().character.level = 5;
        w.step();
        let q = quests(&w);
        assert_eq!(
            (q.len(), q[0].id.as_str(), q[0].counts.clone()),
            (1, "crags_onward", vec![0])
        );
        let mut told = false;
        while let Ok(m) = rx.try_recv() {
            told |= m["type"] == "system"
                && m["text"].as_str().unwrap().contains("Onward to the Crags");
        }
        assert!(told, "the player is told a quest has found them");
        w.step();
        assert_eq!(quests(&w).len(), 1, "it is granted once");

        // Not done in the meadow, so the captain refuses the reward.
        w.players.get_mut(&1).unwrap().character.zone = 1;
        quest_interact(&mut w, "crags_captain", Some("quest:claim:crags_onward"));
        assert!(!quests(&w)[0].claimed, "claimed only after it was reached");
        w.players.get_mut(&1).unwrap().character.zone = 0;
        // Standing in the Crags completes it, and the captain pays out.
        let (xp, gold) = {
            let c = &w.players[&1].character;
            (c.xp, c.gold)
        };
        w.players.get_mut(&1).unwrap().character.zone = 1;
        w.step();
        assert_eq!(quests(&w)[0].counts, vec![1]);
        quest_interact(&mut w, "crags_captain", Some("quest:claim:crags_onward"));
        let c = &w.players[&1].character;
        assert!(c.quests[0].claimed && c.quests[0].completions == 1);
        assert_eq!(c.gold, gold + 100);
        assert_eq!(c.xp, xp + xp_to_level(5) / 10);
    }

    #[test]
    fn a_character_who_already_explored_the_zone_has_reached_it() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 20;
            c.explored = vec![0, 0, 0b100, 0];
        }
        w.step();
        let c = &w.players[&1].character;
        let ids: Vec<(&str, u32)> = c
            .quests
            .iter()
            .map(|q| (q.id.as_str(), q.counts[0]))
            .collect();
        assert_eq!(
            ids,
            vec![
                ("crags_onward", 0),
                ("rime_onward", 1),
                ("fen_onward", 0),
                ("city_onward", 0)
            ],
            "only the glacier was visited before; the others still need the trip"
        );
        // Taking the quest off the ledger is not a thing: a second step adds nothing.
        w.step();
        assert_eq!(w.players[&1].character.quests.len(), 4);
    }

    #[test]
    fn crags_hub_catalog_is_connected_and_has_valid_quests() {
        let w = world();
        let map = &w.maps[1];
        assert_eq!(map.npcs.len(), 5);
        assert_eq!(map.quests.len(), 14);
        assert_eq!(map.quests.iter().filter(|q| q.repeatable).count(), 2);
        let mut ids = std::collections::HashSet::new();
        let mut npc_ids = std::collections::HashSet::new();
        for area in &w.maps {
            for npc in &area.npcs {
                assert!(npc_ids.insert(&npc.id), "globally unique NPC ids");
            }
            for q in &area.quests {
                assert!(ids.insert(&q.id), "globally unique persistent quest ids");
                assert!(area.npcs.iter().any(|n| n.id == q.npc));
                assert!(q.reward_xp > 0 && q.reward_gold > 0 && !q.objectives.is_empty());
                if let Some(id) = &q.reward_item {
                    assert!(
                        item(id).is_some_and(is_gear),
                        "valid gear reward for {}",
                        q.id
                    );
                }
                let need = xp_to_level(q.level);
                assert!(q.level >= 1, "{} needs a recommended level", q.id);
                assert_eq!(
                    q.reward_xp,
                    need / 10,
                    "{} pays a tenth of level {}'s XP",
                    q.id,
                    q.level
                );
                let mut chain = std::collections::HashSet::new();
                let mut next = Some(q);
                while let Some(step) = next {
                    assert!(chain.insert(&step.id), "quest prerequisites must not cycle");
                    next = step.requires.as_ref().map(|id| {
                        area.quests
                            .iter()
                            .find(|q| &q.id == id)
                            .expect("valid prerequisite")
                    });
                }
                for o in &q.objectives {
                    assert!(o.count > 0);
                    match o.kind.as_str() {
                        // A talk objective may name someone in another map (Skaldholm's errands).
                        "talk" => assert!(
                            w.maps
                                .iter()
                                .any(|m| m.npcs.iter().any(|n| n.id == o.target))
                        ),
                        "kill" => assert!(
                            o.target == "any"
                                || o.target == "slime"
                                || area.slimes.iter().any(|s| s.kind == o.target)
                        ),
                        "bring" => assert!(item(&o.target).is_some_and(|i| i.kind == "material")),
                        "reach" => assert!(w.maps.iter().any(|m| m.name == o.target)),
                        "visit" | "hold" => assert!(area.places.iter().any(|p| p.id == o.target)),
                        "chime" => assert!(area.places.iter().any(|p| p.chain == o.target)),
                        "escort" => assert!(
                            area.npcs
                                .iter()
                                .any(|n| n.id == o.target && n.escort.is_some())
                        ),
                        _ => panic!("unsupported objective"),
                    }
                }
            }
        }
        for npc in &map.npcs {
            let point = Point { x: npc.x, y: npc.y };
            let mut clear = point;
            map.collide(&mut clear, PLAYER_RADIUS);
            assert!(
                point.distance(clear) < 1e-6,
                "NPC stands on accessible ground"
            );
            assert!(map.in_city(point), "NPC is protected by camp sanctuary");
            assert!(
                w.slimes
                    .iter()
                    .filter(|s| s.zone == 1)
                    .all(|s| s.point().distance(point) > 8.)
            );
        }
    }

    #[test]
    fn crags_tour_checks_zone_giver_prerequisites_and_saves_its_reward() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        w.interact(1, "crags_captain", Some("quest:accept:crags_welcome"));
        assert!(w.players[&1].character.quests.is_empty(), "wrong zone");
        w.players.get_mut(&1).unwrap().character.zone = 1;
        quest_interact(&mut w, "crags_scout", Some("quest:accept:crags_wisps"));
        quest_interact(&mut w, "crags_supplier", Some("quest:accept:crags_welcome"));
        assert!(
            w.players[&1].character.quests.is_empty(),
            "locked or wrong giver"
        );
        quest_interact(&mut w, "crags_captain", Some("quest:accept:crags_welcome"));
        quest_interact(&mut w, "crags_scout", None);
        quest_interact(&mut w, "crags_healer", None);
        quest_interact(&mut w, "crags_supplier", None);
        assert_eq!(w.players[&1].character.quests[0].counts, vec![1, 1, 1]);
        quest_interact(&mut w, "crags_captain", Some("quest:claim:crags_welcome"));
        assert_eq!(w.players[&1].character.gold, 40);
        assert_eq!(
            w.store.load(token).unwrap().unwrap().quests[0].completions,
            1
        );
        quest_interact(&mut w, "crags_captain", Some("quest:claim:crags_welcome"));
        assert_eq!(w.players[&1].character.gold, 40, "no duplicate reward");
        quest_interact(&mut w, "crags_scout", Some("quest:accept:crags_wisps"));
        assert_eq!(w.players[&1].character.quests[1].counts, vec![0]);
    }

    #[test]
    fn crags_kills_credit_only_local_accepted_quests_and_the_killer() {
        let mut w = world();
        let _r1 = join(&mut w, 1, Class::Warrior);
        let _r2 = join(&mut w, 2, Class::Mage);
        quest_interact(&mut w, "gatekeeper", Some("quest:accept:slime_patrol"));
        w.players.get_mut(&1).unwrap().character.quests[0].completions = 1;
        quest_interact(&mut w, "merchant", Some("quest:accept:meadow_bounty"));
        w.players.get_mut(&1).unwrap().character.zone = 1;
        w.players.get_mut(&2).unwrap().character.zone = 1;
        quest_interact(&mut w, "crags_captain", Some("quest:accept:crags_welcome"));
        w.players.get_mut(&1).unwrap().character.quests[2].completions = 1;
        quest_interact(&mut w, "crags_scout", Some("quest:accept:crags_wisps"));
        quest_interact(&mut w, "crags_supplier", Some("quest:accept:crags_bounty"));
        let index = w
            .slimes
            .iter()
            .position(|s| s.zone == 1 && s.kind == "wisp")
            .unwrap();
        w.hit_slime(index, 1, 10000., false);
        let c = &w.players[&1].character;
        assert_eq!(
            c.quests[1].counts,
            vec![0],
            "meadow bounty excludes Crags kills"
        );
        assert_eq!(c.quests[3].counts, vec![1]);
        assert_eq!(c.quests[4].counts, vec![1]);
        assert!(w.players[&2].character.quests.is_empty());
        let index = w
            .slimes
            .iter()
            .position(|s| s.zone == 1 && s.kind == "spider")
            .unwrap();
        w.hit_slime(index, 1, 10000., false);
        assert_eq!(
            w.players[&1].character.quests[3].counts,
            vec![1],
            "kind-specific objective"
        );
        assert_eq!(w.players[&1].character.quests[4].counts, vec![2]);
        w.players.get_mut(&1).unwrap().character.zone = 0;
        let index = w
            .slimes
            .iter()
            .position(|s| s.zone == 0 && s.kind == "green")
            .unwrap();
        w.hit_slime(index, 1, 10000., false);
        assert_eq!(w.players[&1].character.quests[1].counts, vec![1]);
        assert_eq!(
            w.players[&1].character.quests[4].counts,
            vec![2],
            "Crags bounty excludes meadow kills"
        );
    }

    #[test]
    fn cinderwatch_sanctuary_heals_and_makes_pursuing_enemies_yield() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.players.get_mut(&1).unwrap().character.zone = 1;
        w.players.get_mut(&1).unwrap().character.hp = 10.;
        quest_interact(&mut w, "crags_healer", Some("blessing"));
        assert_eq!(w.players[&1].character.hp, 120.);
        assert_eq!(w.players[&1].character.gold, 0);
        w.hurt_player(1, 1000., Point::default());
        assert_eq!(w.players[&1].character.hp, 120., "camp blocks enemy damage");
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == 1 && s.kind == "wisp")
            .unwrap();
        w.slimes[id].x = 46.;
        w.slimes[id].y = 75.;
        w.slimes[id].target = Some(1);
        w.slimes[id].state = "chase".into();
        w.update_slime(id);
        assert!(w.slimes[id].target.is_none(), "camp drops chase targets");
        assert!(!w.maps[1].in_city(w.slimes[id].point()));
    }

    // ---- Rimeveil Glacier (zone 2, levels 10-15) ----
    const GLACIER_CENTER: Point = Point { x: 64., y: 52. };
    const GLACIER_RINGS: [f64; 4] = [48., 37., 26., 15.];

    fn free_for_player(map: &Map, p: Point) -> bool {
        let mut q = p;
        map.collide(&mut q, PLAYER_RADIUS);
        q.distance(p) < 1e-6
    }

    // Breadth-first walk over free ground, half a unit per step; the steps it takes to reach every free cell.
    fn walk_steps(map: &Map, start: Point) -> std::collections::HashMap<(i32, i32), u32> {
        let cell = |p: Point| ((p.x / 0.5) as i32, (p.y / 0.5) as i32);
        let centre = |c: (i32, i32)| Point {
            x: (c.0 as f64 + 0.5) * 0.5,
            y: (c.1 as f64 + 0.5) * 0.5,
        };
        let limit = (map.size as f64 / 0.5) as i32;
        let mut seen = std::collections::HashMap::new();
        let mut queue = std::collections::VecDeque::new();
        seen.insert(cell(start), 0);
        queue.push_back(cell(start));
        while let Some(c) = queue.pop_front() {
            let d = seen[&c];
            for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
                let n = (c.0 + dx, c.1 + dy);
                if n.0 < 0 || n.1 < 0 || n.0 >= limit || n.1 >= limit || seen.contains_key(&n) {
                    continue;
                }
                if free_for_player(map, centre(n)) {
                    seen.insert(n, d + 1);
                    queue.push_back(n);
                }
            }
        }
        seen
    }

    #[test]
    fn rimeveil_zone_data_has_four_kinds_in_their_bands_with_levels_ten_to_fifteen() {
        let w = world();
        assert_eq!(zone_count(&w), 14);
        let map = &w.maps[2];
        assert_eq!(map.name, "Rimeveil Glacier");
        assert_eq!(map.levels, Some([10, 15]));
        assert_eq!(map.size, 128);
        let mut counts = std::collections::BTreeMap::new();
        for s in w.slimes.iter().filter(|s| s.zone == 2) {
            *counts.entry(s.kind.as_str()).or_insert(0) += 1;
            assert!(
                (10..=15).contains(&Slime::default_level(&s.kind)),
                "{} default level",
                s.kind
            );
        }
        assert_eq!(
            counts,
            std::collections::BTreeMap::from([("crab", 9), ("wolf", 8), ("wyrm", 4), ("yeti", 6)])
        );
        // Enemy ids of the older zones are unchanged: the new zone's enemies come last.
        let first = w.slimes.iter().position(|s| s.zone == 2).unwrap();
        assert!(w.slimes[..first].iter().all(|s| s.zone < 2) && first == 59);
        // Each kind keeps to its own ring: crabs on the outer shelf, wyrms in the summit bowl.
        let band = |kind: &str| {
            let radii: Vec<f64> = w
                .slimes
                .iter()
                .filter(|s| s.zone == 2 && s.kind == kind)
                .map(|s| s.point().distance(GLACIER_CENTER))
                .collect();
            (
                radii.iter().cloned().fold(f64::MAX, f64::min),
                radii.iter().cloned().fold(0., f64::max),
            )
        };
        let (lo, hi) = band("crab");
        assert!(
            lo > GLACIER_RINGS[1] && hi < GLACIER_RINGS[0],
            "crabs {lo}-{hi}"
        );
        let (lo, hi) = band("wolf");
        assert!(
            lo > GLACIER_RINGS[2] && hi < GLACIER_RINGS[1],
            "wolves {lo}-{hi}"
        );
        let (lo, hi) = band("yeti");
        assert!(
            lo > GLACIER_RINGS[3] && hi < GLACIER_RINGS[2],
            "yetis {lo}-{hi}"
        );
        let (_, hi) = band("wyrm");
        assert!(hi < GLACIER_RINGS[3], "wyrms stay in the bowl: {hi}");
        // The Crags gate to the glacier and the way back.
        let up = w.maps[1]
            .portals
            .iter()
            .find(|p| p.id == "rimeveil_gate")
            .expect("the Crags have a north gate");
        assert_eq!(up.to, 2);
        assert_eq!(
            w.maps[1].portals[0].id, "meadow_gate",
            "the meadow gate stays first"
        );
        let back = &map.portals[0];
        assert_eq!((back.id.as_str(), back.to), ("crags_gate", 1));
        assert_eq!((back.tx, back.ty), (up.x + 0., up.y + 4.5));
    }

    #[test]
    fn rimeveil_walls_form_a_spiral_with_one_gap_per_ring_and_every_actor_can_be_reached() {
        let w = world();
        let map = &w.maps[2];
        // One gap in each ring, on the south, north, south and north side in turn.
        for (k, radius) in GLACIER_RINGS.iter().enumerate() {
            let open: Vec<f64> = (0..720)
                .map(|i| i as f64 * 0.5 - 180.)
                .filter(|deg| {
                    let a = deg.to_radians();
                    free_for_player(
                        map,
                        Point {
                            x: GLACIER_CENTER.x + radius * a.cos(),
                            y: GLACIER_CENTER.y + radius * a.sin(),
                        },
                    )
                })
                .collect();
            assert!(!open.is_empty(), "ring {k} is sealed");
            let want = if k % 2 == 0 { 90. } else { -90. };
            // Open angles are one run round `want` (no wrap-around because the gaps sit at +-90).
            // A gap is about 6 units wide, so it spans fewer degrees on the big rings than on the small ones.
            let tolerance = (5.0_f64 / radius).asin().to_degrees();
            assert!(
                open.iter().all(|d| (d - want).abs() < tolerance),
                "ring {k} has more than one opening: {:?}",
                (open.first(), open.last())
            );
        }
        // Everything stands on ground a player can reach from the arrival point.
        let start = Point {
            x: map.spawn.x,
            y: map.spawn.y,
        };
        let steps = walk_steps(map, start);
        let reach = |p: Point| {
            steps
                .get(&((p.x / 0.5) as i32, (p.y / 0.5) as i32))
                .copied()
        };
        for s in w.slimes.iter().filter(|s| s.zone == 2) {
            assert!(
                reach(s.point()).is_some(),
                "{} at {},{} is walled off",
                s.kind,
                s.x,
                s.y
            );
        }
        for n in &map.npcs {
            assert!(
                reach(Point { x: n.x, y: n.y }).is_some(),
                "{} is walled off",
                n.id
            );
        }
        let gate = &map.portals[0];
        assert!(
            reach(Point {
                x: gate.x,
                y: gate.y - 2.
            })
            .is_some()
        );
        // The summit is the end of the spiral: the walk is far longer than the straight line.
        let walk = reach(GLACIER_CENTER).expect("the summit is reachable") as f64 * 0.5;
        let straight = start.distance(GLACIER_CENTER);
        assert!(
            walk > 3.5 * straight && walk < 700.,
            "walk {walk} units against a straight line of {straight}"
        );
        // Every gap is a real choke point: the path to the summit passes through all four.
        assert!(
            reach(Point { x: 64., y: 100. }).is_some()
                && reach(Point { x: 64., y: 15. }).is_some()
                && reach(Point { x: 64., y: 78. }).is_some()
                && reach(Point { x: 64., y: 37. }).is_some()
        );
    }

    #[test]
    fn rimeveil_monsters_have_their_own_stats_levels_rewards_and_materials() {
        for (kind, level, hp, damage, windup, gold, material_id) in [
            ("crab", 10, 900., 60., 0.4, 60, "rime_shell"),
            ("wolf", 12, 1000., 72., 0.3, 78, "frost_pelt"),
            ("yeti", 13, 1900., 88., 0.7, 105, "yeti_horn"),
            ("wyrm", 15, 2200., 100., 0.5, 150, "wyrm_scale"),
        ] {
            assert_eq!(Slime::default_level(kind), level);
            assert_ne!(
                Slime::stats(kind),
                Slime::stats("green"),
                "{kind} has stats"
            );
            assert_eq!(Slime::attack_profile(kind).0, windup);
            assert_eq!(crate::items::material(kind), material_id);
            let spawn = || SlimeSpawn {
                ambush: None,
                kind: kind.into(),
                x: 64.,
                y: 60.,
                zone: 2,
            };
            // Default level: the table values; two levels up: +24% health and damage, +20% gold, XP by level.
            let base = Slime::with_level(0, &spawn(), level);
            assert_eq!((base.max_hp, base.damage, base.gold), (hp, damage, gold));
            assert_eq!(base.xp, enemy_xp(level));
            let up = Slime::with_level(0, &spawn(), level + 2);
            assert_eq!(up.max_hp, (hp * 1.24_f64).round());
            assert_eq!(up.damage, (damage * 1.24_f64).round());
            assert_eq!(up.gold, (gold as f64 * 1.2).round() as u32);
            assert_eq!(up.xp, enemy_xp(level + 2));
        }
    }

    #[test]
    fn a_kill_in_rimeveil_pays_its_rolled_level_and_drops_its_material_in_that_zone() {
        for (kind, material_id) in [
            ("crab", "rime_shell"),
            ("wolf", "frost_pelt"),
            ("yeti", "yeti_horn"),
            ("wyrm", "wyrm_scale"),
        ] {
            let mut w = world();
            let _rx = join(&mut w, 1, Class::Warrior);
            w.players.get_mut(&1).unwrap().character.zone = 2;
            let id = w
                .slimes
                .iter()
                .position(|s| s.zone == 2 && s.kind == kind)
                .unwrap();
            let level = Slime::default_level(kind) + 1;
            w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), level);
            let (xp, gold) = (w.slimes[id].xp, w.slimes[id].gold);
            w.hit_slime(id, 1, 1_000_000., false);
            let c = &w.players[&1].character;
            let paid: u32 = (1..c.level).map(xp_to_level).sum::<u32>() + c.xp;
            assert_eq!(paid, xp, "{kind} xp");
            assert_eq!(
                w.drops.iter().find(|d| d.item.is_none()).unwrap().value,
                gold
            );
            assert!(
                w.drops
                    .iter()
                    .any(|d| d.item.as_deref() == Some(material_id)),
                "{kind} material"
            );
            assert!(w.drops.iter().all(|d| d.zone == 2));
        }
    }

    #[test]
    fn rimeward_camp_has_a_travel_master_and_valid_quests_levelled_ten_to_fifteen() {
        let w = world();
        let map = &w.maps[2];
        assert_eq!(
            map.city.as_ref().map(|c| (c.x0, c.x1, c.y0, c.y1)),
            Some((52., 76., 108., 121.))
        );
        assert_eq!(map.npcs.len(), 6);
        assert_eq!(map.quests.len(), 14);
        assert!(
            map.quests.len() >= 10,
            "a questhub needs at least ten quests"
        );
        assert_eq!(map.quests.iter().filter(|q| q.repeatable).count(), 2);
        let mut roots = 0;
        for q in &map.quests {
            assert!(q.id.starts_with("rime_") && q.npc.starts_with("rime_"));
            assert!((10..=15).contains(&q.level), "{} level {}", q.id, q.level);
            assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
            assert!(q.reward_gold >= 200);
            roots += (q.requires.is_none() && q.auto_level.is_none()) as usize;
            if let Some(id) = &q.requires {
                let prereq = map
                    .quests
                    .iter()
                    .find(|p| &p.id == id)
                    .expect("prerequisite is in the camp");
                assert!(prereq.level <= q.level, "{} unlocks upward", q.id);
            }
            for o in &q.objectives {
                match o.kind.as_str() {
                    "talk" => assert!(map.npcs.iter().any(|n| n.id == o.target)),
                    "kill" => {
                        assert!(o.target == "any" || map.slimes.iter().any(|s| s.kind == o.target))
                    }
                    "reach" => assert!(w.maps.iter().any(|m| m.name == o.target)),
                    other => panic!("objective {other}"),
                }
            }
        }
        assert_eq!(roots, 1, "one introduction unlocks everything");
        // Every kind has at least one hunt, the last one needs all four, and the levels climb.
        for kind in ["crab", "wolf", "yeti", "wyrm"] {
            assert!(
                map.quests
                    .iter()
                    .any(|q| q.objectives.iter().any(|o| o.target == kind)),
                "no {kind} hunt"
            );
        }
        let vanguard = map.quests.iter().find(|q| q.id == "rime_vanguard").unwrap();
        assert_eq!(vanguard.objectives.len(), 4);
        // The hub itself: NPCs on free ground inside the sanctuary, no enemy within eight units.
        for npc in &map.npcs {
            let point = Point { x: npc.x, y: npc.y };
            assert!(
                free_for_player(map, point),
                "{} stands on free ground",
                npc.id
            );
            assert!(map.in_city(point));
            assert!(
                w.slimes
                    .iter()
                    .filter(|s| s.zone == 2)
                    .all(|s| s.point().distance(point) > 8.)
            );
        }
        assert!(
            map.in_city(map.spawn),
            "the arrival point is inside the sanctuary"
        );
    }

    #[test]
    fn the_rimeward_tour_checks_giver_zone_prerequisites_and_pays_each_reward_once() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        // Out of zone the giver is not reachable.
        w.interact(1, "rime_warden", Some("quest:accept:rime_welcome"));
        assert!(w.players[&1].character.quests.is_empty());
        w.players.get_mut(&1).unwrap().character.zone = 2;
        quest_interact(&mut w, "rime_tracker", Some("quest:accept:rime_crabs"));
        quest_interact(&mut w, "rime_trader", Some("quest:accept:rime_welcome"));
        assert!(
            w.players[&1].character.quests.is_empty(),
            "locked or wrong giver"
        );
        quest_interact(&mut w, "rime_warden", Some("quest:accept:rime_welcome"));
        for npc in [
            "rime_tracker",
            "rime_healer",
            "rime_trader",
            "rime_loremaster",
        ] {
            quest_interact(&mut w, npc, None);
        }
        assert_eq!(w.players[&1].character.quests[0].counts, vec![1, 1, 1, 1]);
        quest_interact(&mut w, "rime_warden", Some("quest:claim:rime_welcome"));
        let (xp, gold) = (xp_to_level(10) / 10, 200);
        let c = &w.players[&1].character;
        assert_eq!(c.gold, gold);
        let paid: u32 = (1..c.level).map(xp_to_level).sum::<u32>() + c.xp;
        assert_eq!(paid, xp);
        assert_eq!(
            w.store.load(token).unwrap().unwrap().quests[0].completions,
            1
        );
        quest_interact(&mut w, "rime_warden", Some("quest:claim:rime_welcome"));
        assert_eq!(w.players[&1].character.gold, gold, "no duplicate reward");
        quest_interact(&mut w, "rime_tracker", Some("quest:accept:rime_crabs"));
        assert_eq!(w.players[&1].character.quests[1].counts, vec![0]);
    }

    #[test]
    fn rimeveil_kills_credit_only_rimeveil_quests_and_the_killer() {
        let mut w = world();
        let _r1 = join(&mut w, 1, Class::Warrior);
        let _r2 = join(&mut w, 2, Class::Mage);
        for id in [1, 2] {
            w.players.get_mut(&id).unwrap().character.zone = 2;
        }
        quest_interact(&mut w, "rime_warden", Some("quest:accept:rime_welcome"));
        w.players.get_mut(&1).unwrap().character.quests[0].completions = 1;
        quest_interact(&mut w, "rime_tracker", Some("quest:accept:rime_crabs"));
        quest_interact(&mut w, "rime_trader", Some("quest:accept:rime_bounty"));
        let kill = |w: &mut World, zone: usize, kind: &str| {
            let i = w
                .slimes
                .iter()
                .position(|s| s.zone == zone && s.kind == kind)
                .unwrap();
            w.hit_slime(i, 1, 1_000_000., false);
        };
        kill(&mut w, 2, "crab");
        let counts = |w: &World| {
            w.players[&1]
                .character
                .quests
                .iter()
                .map(|q| (q.id.clone(), q.counts.clone()))
                .collect::<Vec<_>>()
        };
        let find = |w: &World, id: &str| counts(w).into_iter().find(|(q, _)| q == id).unwrap().1;
        assert_eq!(find(&w, "rime_crabs"), vec![1]);
        assert_eq!(find(&w, "rime_bounty"), vec![1]);
        assert!(
            w.players[&2].character.quests.is_empty(),
            "only the killer is credited"
        );
        kill(&mut w, 2, "wolf");
        assert_eq!(find(&w, "rime_crabs"), vec![1], "kind-specific");
        assert_eq!(find(&w, "rime_bounty"), vec![2]);
        // A Crags kill counts for nothing here, and a glacier kill nothing for the Crags.
        kill(&mut w, 1, "golem");
        assert_eq!(
            find(&w, "rime_bounty"),
            vec![2],
            "Crags enemies do not count"
        );
        w.players.get_mut(&1).unwrap().character.zone = 1;
        quest_interact(&mut w, "crags_captain", Some("quest:accept:crags_welcome"));
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .last_mut()
            .unwrap()
            .completions = 1;
        quest_interact(&mut w, "crags_supplier", Some("quest:accept:crags_bounty"));
        let before = find(&w, "crags_bounty");
        kill(&mut w, 2, "yeti");
        assert_eq!(
            find(&w, "crags_bounty"),
            before,
            "glacier enemies do not count for the Crags"
        );
    }

    #[test]
    fn the_crags_north_gate_leads_to_rimeveil_saves_the_zone_and_the_way_back_works() {
        let mut w = world();
        let (tx, mut rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let up = w.maps[1]
            .portals
            .iter()
            .find(|p| p.id == "rimeveil_gate")
            .unwrap()
            .clone();
        let back = w.maps[2].portals[0].clone();
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.zone = 1;
            c.x = up.x;
            c.y = up.y + 4.;
        }
        w.message(
            1,
            ClientMessage::Move {
                x: up.x,
                y: up.y - 1.,
            },
        );
        for _ in 0..200 {
            w.time += TICK;
            w.update_player(1);
            if w.players[&1].character.zone == 2 {
                break;
            }
        }
        let c = &w.players[&1].character;
        assert_eq!(c.zone, 2);
        assert!(c.point().distance(Point { x: up.tx, y: up.ty }) < 1e-6);
        assert_eq!(
            w.store.load(&token).unwrap().unwrap().zone,
            2,
            "the zone saves at once"
        );
        assert_eq!(w.snapshot_for(2)["players"][0]["zone"], 2);
        assert!(w.snapshot_for(1)["players"].as_array().unwrap().is_empty());
        let mut texts = vec![];
        while let Ok(v) = rx.try_recv() {
            if v["type"] == "system" {
                texts.push(v["text"].as_str().unwrap().to_owned());
            }
        }
        assert!(
            texts
                .iter()
                .any(|t| t.contains("Rimeveil Glacier") && t.contains("10–15")),
            "{texts:?}"
        );
        // No instant bounce on the arrival point; then the way back lands at the Crags' north gate.
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = back.x;
            c.y = back.y;
        }
        w.update_player(1);
        assert_eq!(w.players[&1].character.zone, 2);
        w.time += PORTAL_DELAY + 0.1;
        w.update_player(1);
        assert_eq!(w.players[&1].character.zone, 1);
        assert!(
            w.players[&1].character.point().distance(Point {
                x: back.tx,
                y: back.ty
            }) < 1e-6
        );
        // A dead player cannot cross, and dying in Rimeveil respawns at Rimeward Camp.
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.zone = 2;
            p.character.x = 10.;
            p.character.y = 10.;
            p.character.hp = 0.;
            p.dead_time = 3.3;
        }
        w.update_player(1);
        let c = &w.players[&1].character;
        assert_eq!(c.zone, 2);
        assert_eq!(c.hp, c.max_hp());
        assert!(c.point().distance(w.maps[2].spawn) < 1.);
    }

    #[test]
    fn rimeveil_is_isolated_from_the_other_zones_and_its_camp_is_a_sanctuary() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let _rx2 = join(&mut w, 2, Class::Mage);
        w.players.get_mut(&1).unwrap().character.zone = 2;
        w.players.get_mut(&2).unwrap().character.zone = 1;
        let snapshot = w.snapshot();
        assert_eq!(snapshot["zones"].as_array().unwrap().len(), w.maps.len());
        for (zone, count) in [(0, 32), (1, 27), (2, 27)] {
            let view = w.snapshot_for(zone);
            assert_eq!(
                view["slimes"].as_array().unwrap().len(),
                count,
                "zone {zone} enemies"
            );
            assert!(
                view["slimes"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .all(|s| s["zone"] == zone)
            );
        }
        // A Crags player cannot target or provoke a glacier enemy standing at the same coordinates.
        let crab = w
            .slimes
            .iter()
            .position(|s| s.zone == 2 && s.kind == "crab")
            .unwrap();
        let spot = w.slimes[crab].point();
        {
            let c = &mut w.players.get_mut(&2).unwrap().character;
            c.x = spot.x;
            c.y = spot.y + 1.;
        }
        w.message(2, ClientMessage::Target { id: crab });
        assert_ne!(w.players[&2].target, Some(crab));
        w.slimes[crab].atk_cd = 0.;
        w.update_slime(crab);
        assert_eq!(w.slimes[crab].state, "idle", "no chase across zones");
        // The camp heals, blocks damage and makes a pursuing enemy let go.
        w.players.get_mut(&1).unwrap().character.hp = 10.;
        quest_interact(&mut w, "rime_healer", Some("blessing"));
        let c = &w.players[&1].character;
        assert_eq!(c.hp, c.max_hp());
        w.hurt_player(1, 1000., Point::default());
        assert_eq!(
            w.players[&1].character.hp,
            w.players[&1].character.max_hp(),
            "camp blocks enemy damage"
        );
        w.slimes[crab].x = 64.;
        w.slimes[crab].y = 107.;
        w.slimes[crab].target = Some(1);
        w.slimes[crab].state = "chase".into();
        w.update_slime(crab);
        assert!(w.slimes[crab].target.is_none(), "camp drops chase targets");
        assert!(!w.maps[2].in_city(w.slimes[crab].point()));
    }

    #[test]
    fn rimeveil_enemies_reroll_a_fresh_level_on_respawn() {
        let mut w = World::new(Store::open(std::path::Path::new(":memory:")).unwrap());
        let _rx = join(&mut w, 1, Class::Warrior);
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == 2 && s.kind == "wolf")
            .unwrap();
        let mut seen = std::collections::BTreeSet::new();
        for _ in 0..80 {
            w.slimes[id].dead = true;
            w.slimes[id].respawn = TICK;
            w.update_slime(id);
            assert!(!w.slimes[id].dead);
            let level = w.slimes[id].level;
            assert!((10..=14).contains(&level));
            let expected = (1000. * (1. + 0.12 * (level as f64 - 12.))).round();
            assert_eq!((w.slimes[id].max_hp, w.slimes[id].hp), (expected, expected));
            seen.insert(level);
        }
        assert!(seen.len() >= 4, "levels barely vary: {seen:?}");
    }

    // ---- Gloamfen (zone 3, levels 15-20) ----
    const FEN_LAKE: Point = Point { x: 66., y: 76. };
    const FEN_GAPS: [(f64, f64); 3] = [(18., 37.), (40., 93.), (92., 113.)];
    const FEN_MOUTH: (f64, f64) = (88.5, 76.);

    // The same breadth-first walk with extra wall discs, used to close one choke point at a time.
    fn walk_steps_sealed(
        map: &Map,
        start: Point,
        seals: &[(f64, f64, f64)],
    ) -> std::collections::HashMap<(i32, i32), u32> {
        let mut sealed = map.clone();
        for &(x, y, r) in seals {
            sealed.objects.push(crate::model::Obstacle {
                x,
                y,
                r,
                width: 0.,
                depth: 0.,
            });
        }
        walk_steps(&sealed, start)
    }

    #[test]
    fn gloamfen_zone_data_has_four_kinds_with_levels_fifteen_to_twenty_and_a_gate_pair() {
        let w = world();
        assert_eq!(zone_count(&w), 14);
        let map = &w.maps[3];
        assert_eq!(map.name, "Gloamfen");
        assert_eq!(map.levels, Some([15, 20]));
        assert_eq!(map.size, 128);
        let mut counts = std::collections::BTreeMap::new();
        for s in w.slimes.iter().filter(|s| s.zone == 3) {
            *counts.entry(s.kind.as_str()).or_insert(0) += 1;
            assert!(
                (15..=20).contains(&Slime::default_level(&s.kind)),
                "{} default level",
                s.kind
            );
        }
        assert_eq!(
            counts,
            std::collections::BTreeMap::from([
                ("croc", 9),
                ("gloomroot", 1),
                ("hydra", 4),
                ("knight", 8),
                ("toad", 10)
            ])
        );
        // The new zone's enemies come last, so every older enemy id is unchanged.
        let first = w.slimes.iter().position(|s| s.zone == 3).unwrap();
        assert!(w.slimes[..first].iter().all(|s| s.zone < 3) && first == 86);
        // The summit gate in the glacier and the way back (the glacier's first portal stays the Crags gate).
        let up = w.maps[2]
            .portals
            .iter()
            .find(|p| p.id == "fen_gate")
            .expect("the summit has a gate");
        assert_eq!(up.to, 3);
        assert_eq!(w.maps[2].portals[0].id, "crags_gate");
        let back = &map.portals[0];
        assert_eq!((back.id.as_str(), back.to), ("summit_gate", 2));
        assert_eq!((back.tx, back.ty), (up.x, up.y + 4.5));
        assert_eq!((up.tx, up.ty), (map.spawn.x, map.spawn.y));
        // No glacier enemy was left beside the new arrival point.
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 2)
                .all(|s| s.point().distance(Point {
                    x: back.tx,
                    y: back.ty
                }) > 8.)
        );
    }

    #[test]
    fn gloamfen_is_a_c_shaped_route_round_the_lake_with_a_choke_point_before_every_band() {
        let w = world();
        let map = &w.maps[3];
        let start = Point {
            x: map.spawn.x,
            y: map.spawn.y,
        };
        let reachable = |seals: &[(f64, f64, f64)]| {
            let steps = walk_steps_sealed(map, start, seals);
            move |p: Point| {
                steps
                    .get(&((p.x / 0.5) as i32, (p.y / 0.5) as i32))
                    .copied()
            }
        };
        let open_kinds = |reach: &dyn Fn(Point) -> Option<u32>| {
            let mut kinds = std::collections::BTreeSet::new();
            for s in w.slimes.iter().filter(|s| s.zone == 3) {
                if reach(s.point()).is_some() {
                    kinds.insert(s.kind.clone());
                }
            }
            kinds.into_iter().collect::<Vec<_>>()
        };
        // Closing each choke in turn cuts off exactly the bands beyond it, so the order is forced.
        let seal = |x: f64, y: f64, r: f64| (x, y, r);
        let closed = [
            (vec![seal(FEN_GAPS[0].0, FEN_GAPS[0].1, 4.8)], vec![]),
            (vec![seal(FEN_GAPS[1].0, FEN_GAPS[1].1, 4.8)], vec!["toad"]),
            (
                vec![seal(FEN_GAPS[2].0, FEN_GAPS[2].1, 4.8)],
                vec!["croc", "toad"],
            ),
            (
                vec![seal(FEN_MOUTH.0, FEN_MOUTH.1, 3.)],
                vec!["croc", "gloomroot", "knight", "toad"],
            ),
        ];
        for (seals, want) in &closed {
            let reach = reachable(seals);
            assert_eq!(&open_kinds(&reach), want, "sealing {seals:?}");
            // The town is always reachable: the walls only cut the fen.
            for n in &map.npcs {
                assert!(reach(Point { x: n.x, y: n.y }).is_some(), "{}", n.id);
            }
        }
        // Nothing is walled off when every gap is open, and the lake itself is not walkable.
        let reach = reachable(&[]);
        assert_eq!(
            open_kinds(&reach),
            vec!["croc", "gloomroot", "hydra", "knight", "toad"]
        );
        for n in &map.npcs {
            assert!(reach(Point { x: n.x, y: n.y }).is_some());
        }
        let gate = &map.portals[0];
        assert!(
            reach(Point {
                x: gate.x,
                y: gate.y + 2.
            })
            .is_some()
        );
        assert!(
            !free_for_player(map, Point { x: 50., y: 76. }),
            "the mere is water"
        );
        assert!(!free_for_player(map, Point { x: 66., y: 62. }));
        assert!(free_for_player(map, FEN_LAKE), "the island is dry");
        assert!(
            reach(Point { x: 80., y: 76. }).is_some(),
            "the causeway can be walked"
        );
        // Each band keeps to its own side of the lake.
        let stand = |kind: &str| -> Vec<Point> {
            w.slimes
                .iter()
                .filter(|s| s.zone == 3 && s.kind == kind)
                .map(|s| s.point())
                .collect()
        };
        assert!(
            stand("toad")
                .iter()
                .all(|p| p.y > 38. && p.y < 92. && p.x < 66.),
            "toads on the west bank"
        );
        assert!(
            stand("croc").iter().all(|p| p.y > 95. && p.x < 92.),
            "crocodiles on the south shore"
        );
        assert!(
            stand("knight").iter().all(|p| p.x > 92. && p.y > 38.),
            "knights on the east bank"
        );
        assert!(
            stand("hydra").iter().all(|p| p.distance(FEN_LAKE) < 9.8),
            "hydras on the island"
        );
        // The walk to the island is far longer than the straight line: a real tour round the lake.
        let steps = walk_steps(map, start);
        let walk = *steps
            .get(&((FEN_LAKE.x / 0.5) as i32, (FEN_LAKE.y / 0.5) as i32))
            .expect("the island is reachable") as f64
            * 0.5;
        assert!(
            walk > 2.2 * start.distance(FEN_LAKE) && walk < 900.,
            "walk {walk}"
        );
    }

    #[test]
    fn gloamfen_monsters_have_their_own_stats_levels_rewards_and_materials() {
        for (kind, level, hp, damage, windup, gold, material_id) in [
            ("toad", 15, 2000., 92., 0.45, 165, "toad_gland"),
            ("croc", 17, 2800., 112., 0.35, 205, "croc_hide"),
            ("knight", 18, 3400., 130., 0.6, 245, "drowned_gauntlet"),
            ("hydra", 20, 5200., 150., 0.55, 360, "hydra_fang"),
            (
                "gloomroot",
                20,
                90000.,
                1500.,
                0.85,
                1200,
                "gloomroot_heartwood",
            ),
        ] {
            assert_eq!(Slime::default_level(kind), level);
            assert_ne!(
                Slime::stats(kind),
                Slime::stats("green"),
                "{kind} has stats"
            );
            assert_eq!(Slime::attack_profile(kind).0, windup);
            assert_eq!(crate::items::material(kind), material_id);
            let spawn = || SlimeSpawn {
                ambush: None,
                kind: kind.into(),
                x: 64.,
                y: 60.,
                zone: 3,
            };
            let base = Slime::with_level(0, &spawn(), level);
            assert_eq!((base.max_hp, base.damage, base.gold), (hp, damage, gold));
            assert_eq!(base.xp, enemy_xp(level));
            let up = Slime::with_level(0, &spawn(), level + 2);
            assert_eq!(up.max_hp, (hp * 1.24_f64).round());
            assert_eq!(up.damage, (damage * 1.24_f64).round());
            assert_eq!(up.gold, (gold as f64 * 1.2).round() as u32);
            assert_eq!(up.xp, enemy_xp(level + 2));
        }
    }

    #[test]
    fn a_kill_in_gloamfen_pays_its_rolled_level_and_drops_its_material_in_that_zone() {
        for (kind, material_id) in [
            ("toad", "toad_gland"),
            ("croc", "croc_hide"),
            ("knight", "drowned_gauntlet"),
            ("hydra", "hydra_fang"),
        ] {
            let mut w = world();
            let _rx = join(&mut w, 1, Class::Warrior);
            w.players.get_mut(&1).unwrap().character.zone = 3;
            let id = w
                .slimes
                .iter()
                .position(|s| s.zone == 3 && s.kind == kind)
                .unwrap();
            let level = Slime::default_level(kind) + 1;
            w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), level);
            let (xp, gold) = (w.slimes[id].xp, w.slimes[id].gold);
            w.hit_slime(id, 1, 1_000_000., false);
            let c = &w.players[&1].character;
            let paid: u32 = (1..c.level).map(xp_to_level).sum::<u32>() + c.xp;
            assert_eq!(paid, xp, "{kind} xp");
            assert_eq!(
                w.drops.iter().find(|d| d.item.is_none()).unwrap().value,
                gold
            );
            assert!(
                w.drops
                    .iter()
                    .any(|d| d.item.as_deref() == Some(material_id)),
                "{kind} material"
            );
            assert!(w.drops.iter().all(|d| d.zone == 3));
        }
    }
    #[test]
    fn every_outdoor_elite_kill_guarantees_green_equipment() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        for kind in [
            "cinderlord",
            "gloomroot",
            "oakhorn",
            "hrungnir",
            "hvitserk",
            "kraken",
        ] {
            let id = w.slimes.iter().position(|s| s.kind == kind).unwrap();
            let zone = w.slimes[id].zone;
            assert!(!w.is_instance(zone));
            w.players.get_mut(&1).unwrap().character.zone = zone;
            let before = w.drops.len();
            w.hit_slime(id, 1, 1_000_000., false);
            let greens: Vec<_> = w.drops[before..]
                .iter()
                .filter_map(|d| d.item.as_deref().and_then(item))
                .filter(|i| is_gear(i) && i.rarity == "uncommon")
                .collect();
            assert_eq!(greens.len(), 1, "{kind} must drop one guaranteed green");
            assert!(greens[0].required_level <= max_drop_level(w.slimes[id].level));
        }
    }

    #[test]
    fn every_quest_hub_has_two_green_rewards_and_a_hard_blue_reward() {
        let w = world();
        let hard = [
            (0, "king_challenge"),
            (1, "crags_cinderlord"),
            (2, "rime_wyrm_hunt"),
            (3, "fen_gloomroot"),
            (4, "city_tribute"),
            (6, "wyrd_oakhorn"),
            (7, "sky_ward_vigil"),
            (8, "deep_captain"),
            (9, "nacre_cathedral"),
            (13, "astral_survey"),
        ];
        for (zone, hard_id) in hard {
            let quests = &w.maps[zone].quests;
            let greens = quests
                .iter()
                .filter(|q| {
                    q.reward_item
                        .as_deref()
                        .and_then(item)
                        .is_some_and(|i| is_gear(i) && i.rarity == "uncommon")
                })
                .count();
            assert!(
                greens >= 2,
                "{} needs two green quest rewards",
                w.maps[zone].name
            );
            let quest = quests.iter().find(|q| q.id == hard_id).unwrap();
            let gear = item(quest.reward_item.as_deref().unwrap()).unwrap();
            assert_eq!(gear.rarity, "rare", "{hard_id} must award blue gear");
            assert!(!quest.repeatable);
        }
        for id in ["wyrd_trolls", "wyrd_weavers"] {
            let q = w.maps[6].quests.iter().find(|q| q.id == id).unwrap();
            assert_eq!(
                item(q.reward_item.as_deref().unwrap()).unwrap().rarity,
                "uncommon"
            );
        }
        let q = w.maps[6]
            .quests
            .iter()
            .find(|q| q.id == "wyrd_vanguard")
            .unwrap();
        assert_eq!(
            item(q.reward_item.as_deref().unwrap()).unwrap().rarity,
            "rare"
        );
        for id in [
            "crags_expedition",
            "rime_vanguard",
            "fen_vanguard",
            "wyrd_seal",
            "sky_vanguard",
            "deep_vanguard",
            "nacre_smithwork",
            "astral_golems",
        ] {
            let q = w
                .maps
                .iter()
                .flat_map(|m| &m.quests)
                .find(|q| q.id == id)
                .unwrap();
            assert_eq!(
                item(q.reward_item.as_deref().unwrap()).unwrap().rarity,
                "rare",
                "{id}"
            );
        }
    }

    #[test]
    fn lanternmere_has_a_travel_master_and_valid_quests_levelled_fifteen_to_twenty() {
        let w = world();
        let map = &w.maps[3];
        assert_eq!(
            map.city.as_ref().map(|c| (c.x0, c.x1, c.y0, c.y1)),
            Some((40., 88., 6., 31.))
        );
        assert_eq!(map.npcs.len(), 8);
        assert_eq!(map.quests.len(), 18);
        assert_eq!(map.quests.iter().filter(|q| q.repeatable).count(), 3);
        let mut roots = 0;
        for q in &map.quests {
            assert!(q.id.starts_with("fen_") && q.npc.starts_with("fen_"));
            assert!((15..=20).contains(&q.level), "{} level {}", q.id, q.level);
            assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
            assert!(q.reward_gold >= 300);
            roots += (q.requires.is_none() && q.auto_level.is_none()) as usize;
            if let Some(id) = &q.requires {
                let prereq = map
                    .quests
                    .iter()
                    .find(|p| &p.id == id)
                    .expect("prerequisite is in the town");
                assert!(prereq.level <= q.level, "{} unlocks upward", q.id);
            }
            assert!(map.npcs.iter().any(|n| n.id == q.npc), "{} giver", q.id);
            for o in &q.objectives {
                match o.kind.as_str() {
                    "talk" => assert!(map.npcs.iter().any(|n| n.id == o.target)),
                    "kill" => {
                        assert!(o.target == "any" || map.slimes.iter().any(|s| s.kind == o.target))
                    }
                    "reach" => assert!(w.maps.iter().any(|m| m.name == o.target)),
                    other => panic!("objective {other}"),
                }
            }
        }
        assert_eq!(roots, 1, "one introduction unlocks everything");
        for kind in ["toad", "croc", "knight", "hydra"] {
            assert!(
                map.quests
                    .iter()
                    .any(|q| q.objectives.iter().any(|o| o.target == kind)),
                "no {kind} hunt"
            );
        }
        let vanguard = map.quests.iter().find(|q| q.id == "fen_vanguard").unwrap();
        assert_eq!(vanguard.objectives.len(), 4);
        let welcome = map.quests.iter().find(|q| q.id == "fen_welcome").unwrap();
        assert_eq!(welcome.objectives.len(), 6, "meet everyone else in town");
        // The town: NPCs on free ground inside the sanctuary, no enemy within eight units, buildings in the way of nobody.
        for npc in &map.npcs {
            let point = Point { x: npc.x, y: npc.y };
            assert!(
                free_for_player(map, point),
                "{} stands on free ground",
                npc.id
            );
            assert!(map.in_city(point), "{} is inside the town", npc.id);
            assert!(
                w.slimes
                    .iter()
                    .filter(|s| s.zone == 3)
                    .all(|s| s.point().distance(point) > 8.)
            );
        }
        assert!(
            map.in_city(map.spawn),
            "the arrival point is inside the sanctuary"
        );
        assert!(
            map.objects.iter().filter(|o| o.width > 0.).count() >= 8,
            "houses, stalls and benches"
        );
    }

    #[test]
    fn the_lanternmere_tour_checks_giver_zone_prerequisites_and_pays_each_reward_once() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        // Out of zone the giver is not reachable.
        w.interact(1, "fen_reeve", Some("quest:accept:fen_welcome"));
        assert!(w.players[&1].character.quests.is_empty());
        w.players.get_mut(&1).unwrap().character.zone = 3;
        quest_interact(&mut w, "fen_ranger", Some("quest:accept:fen_toads"));
        quest_interact(&mut w, "fen_trader", Some("quest:accept:fen_welcome"));
        assert!(
            w.players[&1].character.quests.is_empty(),
            "locked or wrong giver"
        );
        quest_interact(&mut w, "fen_reeve", Some("quest:accept:fen_welcome"));
        for npc in [
            "fen_lamplighter",
            "fen_healer",
            "fen_trader",
            "fen_ranger",
            "fen_scholar",
            "fen_ferryman",
        ] {
            quest_interact(&mut w, npc, None);
        }
        assert_eq!(
            w.players[&1].character.quests[0].counts,
            vec![1, 1, 1, 1, 1, 1]
        );
        quest_interact(&mut w, "fen_reeve", Some("quest:claim:fen_welcome"));
        let (xp, gold) = (xp_to_level(15) / 10, 300);
        let c = &w.players[&1].character;
        assert_eq!(c.gold, gold);
        let paid: u32 = (1..c.level).map(xp_to_level).sum::<u32>() + c.xp;
        assert_eq!(paid, xp);
        assert_eq!(
            w.store.load(token).unwrap().unwrap().quests[0].completions,
            1
        );
        quest_interact(&mut w, "fen_reeve", Some("quest:claim:fen_welcome"));
        assert_eq!(w.players[&1].character.gold, gold, "no duplicate reward");
        quest_interact(&mut w, "fen_ranger", Some("quest:accept:fen_toads"));
        assert_eq!(w.players[&1].character.quests[1].counts, vec![0]);
    }

    #[test]
    fn gloamfen_kills_credit_only_gloamfen_quests_and_the_killer() {
        let mut w = world();
        let _r1 = join(&mut w, 1, Class::Warrior);
        let _r2 = join(&mut w, 2, Class::Mage);
        for id in [1, 2] {
            w.players.get_mut(&id).unwrap().character.zone = 3;
        }
        quest_interact(&mut w, "fen_reeve", Some("quest:accept:fen_welcome"));
        w.players.get_mut(&1).unwrap().character.quests[0].completions = 1;
        quest_interact(&mut w, "fen_ranger", Some("quest:accept:fen_toads"));
        quest_interact(&mut w, "fen_trader", Some("quest:accept:fen_bounty"));
        let kill = |w: &mut World, zone: usize, kind: &str| {
            let i = w
                .slimes
                .iter()
                .position(|s| s.zone == zone && s.kind == kind)
                .unwrap();
            w.hit_slime(i, 1, 1_000_000., false);
        };
        let find = |w: &World, id: &str| {
            w.players[&1]
                .character
                .quests
                .iter()
                .find(|q| q.id == id)
                .unwrap()
                .counts
                .clone()
        };
        kill(&mut w, 3, "toad");
        assert_eq!(find(&w, "fen_toads"), vec![1]);
        assert_eq!(find(&w, "fen_bounty"), vec![1]);
        assert!(
            w.players[&2].character.quests.is_empty(),
            "only the killer is credited"
        );
        kill(&mut w, 3, "hydra");
        assert_eq!(find(&w, "fen_toads"), vec![1], "kind-specific");
        assert_eq!(find(&w, "fen_bounty"), vec![2]);
        kill(&mut w, 2, "wyrm");
        assert_eq!(
            find(&w, "fen_bounty"),
            vec![2],
            "glacier enemies do not count in the fen"
        );
        // And a fen kill counts for nothing at the glacier camp.
        w.players.get_mut(&1).unwrap().character.zone = 2;
        quest_interact(&mut w, "rime_warden", Some("quest:accept:rime_welcome"));
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .last_mut()
            .unwrap()
            .completions = 1;
        quest_interact(&mut w, "rime_trader", Some("quest:accept:rime_bounty"));
        let before = find(&w, "rime_bounty");
        kill(&mut w, 3, "knight");
        assert_eq!(
            find(&w, "rime_bounty"),
            before,
            "fen enemies do not count at the glacier"
        );
    }

    #[test]
    fn the_summit_gate_leads_to_gloamfen_saves_the_zone_and_the_way_back_works() {
        let mut w = world();
        let (tx, mut rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let up = w.maps[2]
            .portals
            .iter()
            .find(|p| p.id == "fen_gate")
            .unwrap()
            .clone();
        let back = w.maps[3].portals[0].clone();
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.zone = 2;
            c.x = up.x;
            c.y = up.y + 4.;
        }
        w.message(
            1,
            ClientMessage::Move {
                x: up.x,
                y: up.y - 1.,
            },
        );
        for _ in 0..200 {
            w.time += TICK;
            w.update_player(1);
            if w.players[&1].character.zone == 3 {
                break;
            }
        }
        let c = &w.players[&1].character;
        assert_eq!(c.zone, 3);
        assert!(c.point().distance(Point { x: up.tx, y: up.ty }) < 1e-6);
        assert_eq!(
            w.store.load(&token).unwrap().unwrap().zone,
            3,
            "the zone saves at once"
        );
        assert_eq!(w.snapshot_for(3)["players"][0]["zone"], 3);
        assert!(w.snapshot_for(2)["players"].as_array().unwrap().is_empty());
        let mut texts = vec![];
        while let Ok(v) = rx.try_recv() {
            if v["type"] == "system" {
                texts.push(v["text"].as_str().unwrap().to_owned());
            }
        }
        assert!(
            texts
                .iter()
                .any(|t| t.contains("Gloamfen") && t.contains("15–20")),
            "{texts:?}"
        );
        // No instant bounce on the arrival point; then the way back lands at the glacier summit gate.
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = back.x;
            c.y = back.y;
        }
        w.update_player(1);
        assert_eq!(w.players[&1].character.zone, 3);
        w.time += PORTAL_DELAY + 0.1;
        w.update_player(1);
        assert_eq!(w.players[&1].character.zone, 2);
        assert!(
            w.players[&1].character.point().distance(Point {
                x: back.tx,
                y: back.ty
            }) < 1e-6
        );
        // Dying in Gloamfen respawns in Lanternmere.
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.zone = 3;
            p.character.x = 10.;
            p.character.y = 60.;
            p.character.hp = 0.;
            p.dead_time = 3.3;
        }
        w.update_player(1);
        let c = &w.players[&1].character;
        assert_eq!(c.zone, 3);
        assert_eq!(c.hp, c.max_hp());
        assert!(c.point().distance(w.maps[3].spawn) < 1.);
    }

    #[test]
    fn gloamfen_is_isolated_from_the_other_zones_and_lanternmere_is_a_sanctuary() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let _rx2 = join(&mut w, 2, Class::Mage);
        w.players.get_mut(&1).unwrap().character.zone = 3;
        w.players.get_mut(&2).unwrap().character.zone = 2;
        for (zone, count) in [(0, 32), (1, 27), (2, 27), (3, 32)] {
            let view = w.snapshot_for(zone);
            assert_eq!(
                view["slimes"].as_array().unwrap().len(),
                count,
                "zone {zone} enemies"
            );
            assert!(
                view["slimes"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .all(|s| s["zone"] == zone)
            );
        }
        // A glacier player cannot target or provoke a toad standing at the same coordinates.
        let toad = w
            .slimes
            .iter()
            .position(|s| s.zone == 3 && s.kind == "toad")
            .unwrap();
        let spot = w.slimes[toad].point();
        {
            let c = &mut w.players.get_mut(&2).unwrap().character;
            c.x = spot.x;
            c.y = spot.y + 1.;
        }
        w.message(2, ClientMessage::Target { id: toad });
        assert_ne!(w.players[&2].target, Some(toad));
        w.slimes[toad].atk_cd = 0.;
        w.update_slime(toad);
        assert_eq!(w.slimes[toad].state, "idle", "no chase across zones");
        // The town heals, blocks damage and makes a pursuing enemy let go.
        w.players.get_mut(&1).unwrap().character.hp = 10.;
        quest_interact(&mut w, "fen_healer", Some("blessing"));
        let c = &w.players[&1].character;
        assert_eq!(c.hp, c.max_hp());
        w.hurt_player(1, 1000., Point::default());
        assert_eq!(
            w.players[&1].character.hp,
            w.players[&1].character.max_hp(),
            "the town blocks enemy damage"
        );
        w.slimes[toad].x = 64.;
        w.slimes[toad].y = 35.;
        w.slimes[toad].target = Some(1);
        w.slimes[toad].state = "chase".into();
        w.update_slime(toad);
        assert!(
            w.slimes[toad].target.is_none(),
            "the town drops chase targets"
        );
        assert!(!w.maps[3].in_city(w.slimes[toad].point()));
    }

    // ---- Skaldholm (zone 4): a walled city with no enemies, walking townspeople and hand-in quests ----
    const CITY: usize = 4;

    #[test]
    fn skaldholm_is_a_big_enemy_free_city_with_a_hundred_houses_a_wall_and_a_gate_pair() {
        let w = world();
        let map = &w.maps[CITY];
        assert_eq!(
            zone_count(&w),
            14,
            "Skaldholm is the fifth map; Astralhollow is the fourteenth public map"
        );
        assert_eq!(map.name, "Skaldholm");
        assert_eq!(map.size, 160);
        assert_eq!(map.size % 8, 0, "whole ground chunks");
        assert!(map.slimes.is_empty() && w.slimes.iter().all(|s| s.zone != CITY));
        assert!(
            map.levels.is_none(),
            "a safe city has no recommended levels"
        );
        let count = |kind: &str| {
            let text = include_str!("../../world/map.txt");
            let all: serde_json::Value = serde_json::from_str(text).unwrap();
            all["zones"][CITY - 1]["objects"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|o| o["kind"] == kind)
                .count()
        };
        // 100 timber houses with a street-and-number sign, plus the halls: a hall, an archive, a guildhall, an inn, a smithy ...
        let houses = {
            let text = include_str!("../../world/map.txt");
            let all: serde_json::Value = serde_json::from_str(text).unwrap();
            all["zones"][CITY - 1]["objects"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|o| o["kind"] == "house" && o["sign"] == "live")
                .count()
        };
        assert!(
            (100..=104).contains(&houses),
            "about a hundred houses, got {houses}"
        );
        assert!(count("rampart") >= 60 && count("tower") >= 9);
        assert_eq!(count("grandfountain"), 1);
        assert_eq!(count("meetingstone"), 1);
        assert!(count("stall") >= 14 && count("lamp") >= 30);
        // The great fountain sits in the middle of the plaza the city names.
        let city = map.city.as_ref().unwrap();
        assert!(!city.contains(map.spawn), "you arrive outside the wall");
        assert!(map.in_city(Point { x: 80., y: 76. }));
        // Gates: the glacier's Skaldholm Gate brings you to the forecourt, the Glacier Gate takes you back to its arrival.
        let up = w.maps[2]
            .portals
            .iter()
            .find(|p| p.id == "city_gate")
            .unwrap();
        let down = &map.portals[0];
        assert_eq!((up.to, down.to), (CITY, 2));
        assert_eq!((up.tx, up.ty), (map.spawn.x, map.spawn.y));
        assert_eq!(down.id, "glacier_gate");
        assert!(down.tx == up.x && (down.ty - (up.y + 4.5)).abs() < 1e-6);
        let outside_gate = |gate: &Portal, p: Point| {
            p.distance(Point {
                x: gate.x,
                y: gate.y,
            }) > gate.r + 0.5
        };
        assert!(
            outside_gate(down, map.spawn),
            "the forecourt arrival is clear of the Glacier Gate"
        );
        assert!(
            outside_gate(
                up,
                Point {
                    x: down.tx,
                    y: down.ty
                }
            ),
            "the summit arrival is clear of the Skaldholm Gate"
        );
        // The glacier keeps all four of its wyrms, and no glacier spawn stands within 8 of any place a gate drops you.
        let wyrms = w
            .slimes
            .iter()
            .filter(|s| s.zone == 2 && s.kind == "wyrm")
            .count();
        assert_eq!(wyrms, 4);
        for s in w.slimes.iter().filter(|s| s.zone == 2) {
            for gate in w
                .maps
                .iter()
                .flat_map(|m| m.portals.iter())
                .filter(|p| p.to == 2)
            {
                assert!(
                    s.point().distance(Point {
                        x: gate.tx,
                        y: gate.ty
                    }) > 8.0,
                    "a {} stands at {:?}, too near an arrival point",
                    s.kind,
                    s.point()
                );
            }
        }
        // Everything solid is inside the map.
        for o in &map.objects {
            assert!(o.x > 0. && o.y > 0. && o.x < 160. && o.y < 160.);
        }
    }

    #[test]
    fn skaldholm_people_stand_on_free_ground_and_everything_is_reachable_on_foot_from_the_gate() {
        let w = world();
        let map = &w.maps[CITY];
        let start = map.spawn;
        let steps = walk_steps(map, start);
        let reach = |p: Point| {
            steps
                .get(&((p.x / 0.5) as i32, (p.y / 0.5) as i32))
                .copied()
        };
        let mut ids = std::collections::HashSet::new();
        let mut walkers = 0;
        for npc in &map.npcs {
            assert!(
                (npc.id.starts_with("city_") || npc.id == "travel_skaldholm")
                    && ids.insert(&npc.id),
                "{} is unique",
                npc.id
            );
            if npc.route.is_empty() {
                let p = Point { x: npc.x, y: npc.y };
                assert!(free_for_player(map, p), "{} stands on free ground", npc.id);
                assert!(
                    reach(p).is_some(),
                    "{} can be reached from the gate",
                    npc.id
                );
                assert!(map.in_city(p), "{} is inside the walls", npc.id);
            } else {
                walkers += 1;
            }
        }
        assert!(map.npcs.len() >= 40, "{} people", map.npcs.len());
        assert!(walkers >= 12, "{walkers} walk");
        // The plaza, the stone court, the gate and the far corners can all be walked to.
        for (name, p) in [
            ("plaza", Point { x: 80., y: 66. }),
            ("stone court", Point { x: 100., y: 123. }),
            ("return gate", Point { x: 80., y: 153. }),
            ("garden", Point { x: 27.4, y: 34. }),
            ("orchard", Point { x: 121.4, y: 30. }),
        ] {
            assert!(reach(p).is_some(), "{name} is reachable");
        }
        // The wall holds: the long way round the outside never gets in, so the Great Gate is the only door.
        assert!(
            !free_for_player(map, Point { x: 30., y: 12. }),
            "the north wall is solid"
        );
        assert!(
            !free_for_player(map, Point { x: 16., y: 100. }),
            "the west wall is solid"
        );
        assert!(
            free_for_player(map, Point { x: 80., y: 140. }),
            "the Great Gate is open"
        );
        let gate_walk = *reach(Point { x: 80., y: 68. }).as_ref().unwrap() as f64 * 0.5;
        assert!(
            gate_walk > 78. && gate_walk < 110.,
            "the forecourt to the plaza is a real walk: {gate_walk}"
        );
    }

    #[test]
    fn walking_townspeople_follow_their_loop_pause_at_corners_and_never_cross_scenery() {
        let walker: Npc = serde_json::from_value(json!({
            "id": "t", "name": "T", "role": "r", "x": 0.0, "y": 0.0, "dialogue": "", "offers": [],
            "route": [[0.0, 0.0], [10.0, 0.0], [10.0, 5.0]], "speed": 2.0, "pause": 1.0, "phase": 0.5
        }))
        .unwrap();
        let diagonal = 125f64.sqrt();
        let cycle = 1. + 5. + 1. + 2.5 + 1. + diagonal / 2.;
        for (time, x, y) in [
            (0.0, 0.0, 0.0),  // pausing at the first corner
            (1.0, 1.0, 0.0),  // half a second into the first leg
            (6.0, 10.0, 0.0), // pausing at the second corner
            (8.0, 10.0, 3.0),
            (
                11.0 - 0.5,
                10.0 - 0.894_427_190_999_916,
                5.0 - 0.447_213_595_499_958,
            ),
            (16.0, 0.0, 0.0),
        ] {
            let p = walker.position_at(time);
            assert!(
                (p.x - x).abs() < 1e-6 && (p.y - y).abs() < 1e-6,
                "t={time}: {p:?} want ({x},{y})"
            );
        }
        // Periodic, continuous and never faster than its speed.
        for t in [0.3, 4.7, 9.9, 13.1] {
            let (a, b) = (walker.position_at(t), walker.position_at(t + cycle));
            assert!(a.distance(b) < 1e-6, "periodic at {t}");
            let step = a.distance(walker.position_at(t + 0.05));
            assert!(step <= 2.0 * 0.05 + 1e-9, "no jumps at {t}");
        }
        // A person without a loop (or without a speed) stays where the map put them.
        let still: Npc = serde_json::from_value(json!({
            "id": "s", "name": "S", "role": "r", "x": 3.0, "y": 4.0, "dialogue": "", "offers": [],
            "route": [[0.0, 0.0], [10.0, 0.0]], "speed": 0.0
        }))
        .unwrap();
        assert_eq!(
            (still.position_at(99.).x, still.position_at(99.).y),
            (3., 4.)
        );
        // The city's walkers: every point of every loop is clear ground, at every moment they move.
        let w = world();
        let map = &w.maps[CITY];
        let walkers: Vec<_> = map.npcs.iter().filter(|n| !n.route.is_empty()).collect();
        assert!(walkers.len() >= 12);
        for npc in &walkers {
            assert!(
                npc.speed > 0. && npc.speed < 4. && npc.pause >= 0.,
                "{} walks at a human pace",
                npc.id
            );
            let mut t = 0.;
            while t < 300. {
                let p = npc.position_at(t);
                assert!(
                    free_for_player(map, p),
                    "{} would walk through scenery at t={t}: {p:?}",
                    npc.id
                );
                assert!(map.in_city(p), "{} stays inside the walls", npc.id);
                t += 0.5;
            }
            let start = npc.position_at(-npc.phase);
            assert!(
                start.distance(Point {
                    x: npc.route[0][0],
                    y: npc.route[0][1]
                }) < 1e-6,
                "{} starts at its first corner",
                npc.id
            );
        }
        assert!(
            walkers.iter().any(|n| n.pause > 0.) && walkers.iter().any(|n| n.pause == 0.),
            "strollers and loiterers"
        );
        let a = walkers.iter().find(|n| n.id == "city_kid_lotta").unwrap();
        let b = walkers.iter().find(|n| n.id == "city_kid_pelle").unwrap();
        assert!(
            a.position_at(10.).distance(b.position_at(10.)) > 3.,
            "the children are spread round the fountain"
        );
    }

    #[test]
    fn talking_to_a_walking_person_checks_the_distance_to_where_they_are_now() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, None, Some(Look::default()), tx).unwrap();
        w.players.get_mut(&1).unwrap().character.zone = CITY;
        let walker = w.maps[CITY]
            .npcs
            .iter()
            .find(|n| n.id == "city_watch_trade")
            .unwrap()
            .clone();
        // Where the watchman was at t=3 and at t=40 are far apart.
        let (a, b) = (walker.position_at(3.), walker.position_at(40.));
        assert!(a.distance(b) > 10., "{a:?} {b:?}");
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = a.x;
            c.y = a.y;
        }
        w.time = 3.;
        w.players.get_mut(&1).unwrap().service_at = -99.;
        let mut rx = {
            let (tx, rx) = mpsc::channel(256);
            w.players.get_mut(&1).unwrap().peer = tx;
            rx
        };
        w.interact(1, "city_watch_trade", None);
        let first = rx.try_recv().unwrap();
        assert_eq!(
            first["type"], "dialogue",
            "standing at the watchman's place at t=3 works: {first}"
        );
        // Standing in the same place at t=40, the watchman has long gone.
        w.time = 40.;
        w.interact(1, "city_watch_trade", None);
        let second = rx.try_recv().unwrap();
        assert_eq!(second["type"], "error");
        assert!(second["text"].as_str().unwrap().contains("closer"));
        // ... and walking up to where they are now works again.
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = b.x + 1.0;
            c.y = b.y;
        }
        w.interact(1, "city_watch_trade", None);
        assert_eq!(rx.try_recv().unwrap()["type"], "dialogue");
    }

    #[test]
    fn skaldholm_has_eleven_valid_quests_mostly_errands_between_the_maps() {
        let w = world();
        let map = &w.maps[CITY];
        assert_eq!(map.quests.len(), 12);
        assert_eq!(map.quests.iter().filter(|q| q.repeatable).count(), 1);
        let all_npcs: Vec<(usize, &Npc)> = w
            .maps
            .iter()
            .enumerate()
            .flat_map(|(z, m)| m.npcs.iter().map(move |n| (z, n)))
            .collect();
        let (mut roots, mut far_talk, mut bring_quests) = (0, std::collections::BTreeSet::new(), 0);
        for q in &map.quests {
            assert!(q.id.starts_with("city_") && q.npc.starts_with("city_"));
            assert!((11..=20).contains(&q.level), "{} level {}", q.id, q.level);
            assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
            assert!(q.reward_gold >= 250, "{}", q.id);
            roots += (q.requires.is_none() && q.auto_level.is_none()) as usize;
            if let Some(id) = &q.requires {
                let prereq = map
                    .quests
                    .iter()
                    .find(|p| &p.id == id)
                    .expect("the prerequisite is in the city");
                assert!(prereq.level <= q.level, "{} unlocks upward", q.id);
            }
            assert!(map.npcs.iter().any(|n| n.id == q.npc), "{} giver", q.id);
            assert!(q.objectives.iter().all(|o| o.count >= 1));
            bring_quests += q.has_bring() as usize;
            for o in &q.objectives {
                match o.kind.as_str() {
                    "talk" => {
                        let (zone, _) = all_npcs
                            .iter()
                            .find(|(_, n)| n.id == o.target)
                            .unwrap_or_else(|| panic!("{} names {}", q.id, o.target));
                        if *zone != CITY {
                            far_talk.insert(*zone);
                        }
                    }
                    "bring" => {
                        let wanted = crate::items::item(&o.target)
                            .unwrap_or_else(|| panic!("{} asks for {}", q.id, o.target));
                        assert_eq!(wanted.kind, "material", "{}", q.id);
                    }
                    "reach" => assert!(w.maps.iter().any(|m| m.name == o.target)),
                    other => panic!("{} has a {other} objective", q.id),
                }
            }
        }
        assert_eq!(roots, 1, "one introduction unlocks everything");
        assert!(bring_quests >= 6, "{bring_quests} hand-in quests");
        assert_eq!(
            far_talk.into_iter().collect::<Vec<_>>(),
            vec![0, 1, 2, 3],
            "people to meet in all four earlier maps"
        );
        // A material from each earlier map is wanted somewhere.
        for item in [
            "slime_gel",
            "ember_core",
            "frost_pelt",
            "toad_gland",
            "hydra_fang",
        ] {
            assert!(
                map.quests
                    .iter()
                    .any(|q| q.objectives.iter().any(|o| o.target == item)),
                "{item}"
            );
        }
        // The people who give errands and sell things.
        for id in [
            "city_captain",
            "city_steward",
            "city_herald",
            "city_alchemist",
            "city_smith",
            "city_guildmaster",
            "city_healer",
            "city_bard",
            "city_librarian",
            "city_stonewarden",
        ] {
            assert!(map.npcs.iter().any(|n| n.id == id), "{id}");
        }
        let guild = map
            .npcs
            .iter()
            .find(|n| n.id == "city_guildmaster")
            .unwrap();
        assert!(guild.buys && guild.offers.len() == 2);
        assert!(
            map.npcs
                .iter()
                .any(|n| n.offers.iter().any(|o| o.heal >= 10000.)),
            "a healer"
        );
    }

    #[test]
    fn a_talk_objective_is_credited_when_you_speak_to_someone_in_another_map() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, None, Some(Look::default()), tx).unwrap();
        // Accept the herald's letters (the welcome quest first, since it unlocks them).
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.zone = CITY;
            c.quests.push(QuestProgress {
                id: "city_welcome".into(),
                counts: vec![1; 5],
                claimed: true,
                completions: 1,
            });
        }
        // Talking in another map before accepting counts for nothing.
        for (zone, npc) in [(0, "gatekeeper"), (1, "crags_captain")] {
            w.players.get_mut(&1).unwrap().character.zone = zone;
            quest_interact(&mut w, npc, None);
        }
        assert!(
            w.players[&1]
                .character
                .quests
                .iter()
                .all(|q| q.id == "city_welcome")
        );
        w.players.get_mut(&1).unwrap().character.zone = CITY;
        quest_interact(&mut w, "city_herald", Some("quest:accept:city_seals"));
        assert_eq!(w.players[&1].character.quests[1].counts, vec![0, 0, 0, 0]);
        // Now walk the four maps: each leader ticks off one objective, in any order, and a repeat adds nothing.
        for (zone, npc) in [
            (2, "rime_warden"),
            (0, "gatekeeper"),
            (3, "fen_reeve"),
            (0, "gatekeeper"),
            (1, "crags_captain"),
        ] {
            w.players.get_mut(&1).unwrap().character.zone = zone;
            quest_interact(&mut w, npc, None);
        }
        assert_eq!(w.players[&1].character.quests[1].counts, vec![1, 1, 1, 1]);
        // Speaking to the herald with the quest done pays out once.
        w.players.get_mut(&1).unwrap().character.zone = CITY;
        quest_interact(&mut w, "city_herald", Some("quest:claim:city_seals"));
        let c = &w.players[&1].character;
        assert_eq!(c.gold, 520);
        assert!(c.quests[1].claimed && c.quests[1].completions == 1);
        // Kills are still credited only inside the killer's own zone: a kill in the glacier touches no city quest.
        let mut c2 = c.clone();
        quest_progress(&mut c2, &w.maps[2].quests, "kill", "crab");
        assert_eq!(c2.quests[1].counts, vec![1, 1, 1, 1]);
    }

    fn give(w: &mut World, item: &str, n: u32) {
        w.players.get_mut(&1).unwrap().character.add_item(item, n);
    }
    fn counts(w: &World, quest: &str) -> Vec<u32> {
        w.players[&1]
            .character
            .quests
            .iter()
            .find(|q| q.id == quest)
            .unwrap()
            .counts
            .clone()
    }
    fn city_player(w: &mut World) {
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, None, Some(Look::default()), tx).unwrap();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = CITY;
        c.quests.push(QuestProgress {
            id: "city_welcome".into(),
            counts: vec![1; 5],
            claimed: true,
            completions: 1,
        });
    }

    #[test]
    fn hand_in_objectives_count_the_bag_take_exactly_the_items_and_pay_once() {
        let mut w = world();
        city_player(&mut w);
        // Materials gathered before accepting already count.
        give(&mut w, "slime_gel", 10);
        give(&mut w, "blue_gel", 3);
        quest_interact(&mut w, "city_alchemist", Some("quest:accept:city_gel"));
        assert_eq!(
            counts(&w, "city_gel"),
            vec![8, 3],
            "up to the count, from the bag"
        );
        // Short of the blue gel: the reward is refused and nothing is taken.
        quest_interact(&mut w, "city_alchemist", Some("quest:claim:city_gel"));
        assert_eq!(w.players[&1].character.gold, 0);
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 10);
        assert!(
            !w.players[&1]
                .character
                .quests
                .iter()
                .find(|q| q.id == "city_gel")
                .unwrap()
                .claimed
        );
        // A tick later the count follows the bag as items arrive and leave.
        give(&mut w, "blue_gel", 5);
        w.update_player(1);
        assert_eq!(counts(&w, "city_gel"), vec![8, 4], "capped at the count");
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .sell_item("slime_gel", 5)
            .unwrap();
        w.update_player(1);
        assert_eq!(
            counts(&w, "city_gel"),
            vec![5, 4],
            "selling takes progress back"
        );
        quest_interact(&mut w, "city_alchemist", Some("quest:claim:city_gel"));
        assert_eq!(
            w.players[&1].character.gold,
            5 * 3,
            "no reward while a hand-in is short (only the sale gold)"
        );
        give(&mut w, "slime_gel", 4);
        quest_interact(&mut w, "city_alchemist", Some("quest:claim:city_gel"));
        let c = &w.players[&1].character;
        assert_eq!(c.gold, 480 + 15, "reward paid");
        // Exactly 8 and 4 were taken: 9 gel - 8 = 1, 8 blue - 4 = 4.
        assert_eq!((c.quantity("slime_gel"), c.quantity("blue_gel")), (1, 4));
        assert!(
            c.quests
                .iter()
                .find(|q| q.id == "city_gel")
                .unwrap()
                .claimed
        );
        let before = c.gold;
        quest_interact(&mut w, "city_alchemist", Some("quest:claim:city_gel"));
        assert_eq!(w.players[&1].character.gold, before, "no second reward");
        assert_eq!(
            w.players[&1].character.quantity("slime_gel"),
            1,
            "nothing more is taken"
        );
        // The count freezes once claimed: later items do not change a finished quest.
        give(&mut w, "slime_gel", 20);
        w.update_player(1);
        assert_eq!(
            counts(&w, "city_gel"),
            vec![8, 4],
            "a finished quest keeps its count"
        );
    }

    #[test]
    fn the_standing_order_can_be_handed_in_again_and_again() {
        let mut w = world();
        city_player(&mut w);
        quest_interact(&mut w, "city_guildmaster", Some("quest:accept:city_order"));
        for round in 1..=2u32 {
            give(&mut w, "magma_fang", 3);
            give(&mut w, "rime_shell", 4);
            w.update_player(1);
            assert_eq!(counts(&w, "city_order"), vec![3, 3]);
            quest_interact(&mut w, "city_guildmaster", Some("quest:claim:city_order"));
            let c = &w.players[&1].character;
            assert_eq!(
                c.quests
                    .iter()
                    .find(|q| q.id == "city_order")
                    .unwrap()
                    .completions,
                round
            );
            assert_eq!(c.quantity("magma_fang"), 0);
            assert_eq!(
                c.quantity("rime_shell"),
                round,
                "one spare shell per round stays in the bag"
            );
            quest_interact(&mut w, "city_guildmaster", Some("quest:accept:city_order"));
            // Accepting again re-counts what is already in the bag (the spare shells), never the handed-in ones.
            assert_eq!(counts(&w, "city_order"), vec![0, round]);
        }
        assert_eq!(w.players[&1].character.gold, 2 * 540);
    }

    #[test]
    fn the_whole_city_questline_runs_from_the_gate_captain_to_the_steward() {
        let mut w = world();
        city_player(&mut w);
        w.players.get_mut(&1).unwrap().character.quests.clear();
        // Welcome: five people to meet.
        quest_interact(&mut w, "city_captain", Some("quest:accept:city_welcome"));
        for npc in [
            "city_herald",
            "city_librarian",
            "city_guildmaster",
            "city_stonewarden",
            "city_healer",
        ] {
            quest_interact(&mut w, npc, None);
        }
        quest_interact(&mut w, "city_captain", Some("quest:claim:city_welcome"));
        // Errands: people in the other maps ...
        quest_interact(&mut w, "city_herald", Some("quest:accept:city_seals"));
        quest_interact(&mut w, "city_bard", Some("quest:accept:city_hearths"));
        quest_interact(&mut w, "city_librarian", Some("quest:accept:city_archive"));
        for (zone, npc) in [
            (0, "gatekeeper"),
            (0, "baker"),
            (1, "crags_captain"),
            (1, "crags_scout"),
            (2, "rime_warden"),
            (2, "rime_loremaster"),
            (3, "fen_reeve"),
            (3, "fen_ferryman"),
            (3, "fen_scholar"),
        ] {
            w.players.get_mut(&1).unwrap().character.zone = zone;
            quest_interact(&mut w, npc, None);
        }
        w.players.get_mut(&1).unwrap().character.zone = CITY;
        quest_interact(&mut w, "city_herald", Some("quest:claim:city_seals"));
        quest_interact(&mut w, "city_bard", Some("quest:claim:city_hearths"));
        // ... and goods from them.
        for (npc, quest, items) in [
            (
                "city_alchemist",
                "city_gel",
                vec![("slime_gel", 8), ("blue_gel", 4)],
            ),
            (
                "city_smith",
                "city_forge",
                vec![("ember_core", 4), ("magma_fang", 3)],
            ),
            (
                "city_guildmaster",
                "city_pelts",
                vec![("frost_pelt", 4), ("yeti_horn", 2)],
            ),
            (
                "city_alchemist",
                "city_marsh",
                vec![("toad_gland", 4), ("croc_hide", 3)],
            ),
            (
                "city_librarian",
                "city_archive",
                vec![("drowned_gauntlet", 3)],
            ),
            (
                "city_stonewarden",
                "city_stone",
                vec![("hydra_fang", 2), ("wyrm_scale", 2), ("basalt_heart", 2)],
            ),
            (
                "city_steward",
                "city_tribute",
                vec![
                    ("ironhide_shell", 2),
                    ("ash_veil", 2),
                    ("rime_shell", 2),
                    ("croc_hide", 2),
                ],
            ),
        ] {
            quest_interact(&mut w, npc, Some(&format!("quest:accept:{quest}")));
            for (item, n) in items {
                give(&mut w, item, n);
            }
            w.update_player(1);
            quest_interact(&mut w, npc, Some(&format!("quest:claim:{quest}")));
        }
        let c = &w.players[&1].character;
        for q in &w.maps[CITY].quests {
            // A progression quest finds the player by itself and is handed in on arrival, not in this chain.
            if !q.repeatable && q.auto_level.is_none() {
                let p = c
                    .quests
                    .iter()
                    .find(|p| p.id == q.id)
                    .unwrap_or_else(|| panic!("{} never accepted", q.id));
                assert!(p.claimed && p.completions == 1, "{} finished", q.id);
            }
        }
        let gold: u32 = w.maps[CITY]
            .quests
            .iter()
            .filter(|q| !q.repeatable && q.auto_level.is_none())
            .map(|q| q.reward_gold)
            .sum();
        assert_eq!(c.gold, gold, "every reward paid once");
        assert!(
            c.inventory
                .iter()
                .all(|s| item(&s.item).unwrap().kind != "material"),
            "every handed-in item was taken: {:?}",
            c.inventory
        );
        let xp: u32 = w.maps[CITY]
            .quests
            .iter()
            .filter(|q| !q.repeatable && q.auto_level.is_none())
            .map(|q| q.reward_xp)
            .sum();
        let paid: u32 = (1..c.level).map(xp_to_level).sum::<u32>() + c.xp;
        assert_eq!(paid, xp, "every experience reward paid once");
    }

    #[test]
    fn the_skaldholm_gate_pair_saves_the_zone_and_dying_in_the_city_respawns_there() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let up = w.maps[2]
            .portals
            .iter()
            .find(|p| p.id == "city_gate")
            .unwrap()
            .clone();
        let back = w.maps[CITY].portals[0].clone();
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.zone = 2;
            c.x = up.x;
            c.y = up.y + 4.;
        }
        w.message(
            1,
            ClientMessage::Move {
                x: up.x,
                y: up.y - 1.,
            },
        );
        for _ in 0..200 {
            w.time += TICK;
            w.update_player(1);
            if w.players[&1].character.zone == CITY {
                break;
            }
        }
        let c = &w.players[&1].character;
        assert_eq!(c.zone, CITY);
        assert!(c.point().distance(Point { x: up.tx, y: up.ty }) < 1e-6);
        assert_eq!(
            w.store.load(&token).unwrap().unwrap().zone,
            CITY,
            "the zone saves at once"
        );
        assert_eq!(w.snapshot_for(CITY)["players"][0]["zone"], CITY);
        assert!(w.snapshot_for(2)["players"].as_array().unwrap().is_empty());
        assert!(
            w.snapshot_for(CITY)["slimes"]
                .as_array()
                .unwrap()
                .is_empty(),
            "no enemies in the city"
        );
        // The Glacier Gate takes the player back to the summit bowl, beside the Skaldholm Gate.
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = back.x;
            c.y = back.y;
        }
        w.time += PORTAL_DELAY + 0.1;
        w.update_player(1);
        assert_eq!(w.players[&1].character.zone, 2);
        assert!(
            w.players[&1].character.point().distance(Point {
                x: back.tx,
                y: back.ty
            }) < 1e-6
        );
        // The city's enemy-free ground is a sanctuary.
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.zone = CITY;
            p.character.x = 40.;
            p.character.y = 60.;
            p.character.hp = 0.;
            p.dead_time = 3.3;
        }
        w.update_player(1);
        let c = &w.players[&1].character;
        assert_eq!(c.zone, CITY);
        assert_eq!(c.hp, c.max_hp());
        assert!(c.point().distance(w.maps[CITY].spawn) < 1.);
    }

    #[test]
    fn gloamfen_enemies_reroll_a_fresh_level_on_respawn() {
        let mut w = World::new(Store::open(std::path::Path::new(":memory:")).unwrap());
        let _rx = join(&mut w, 1, Class::Warrior);
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == 3 && s.kind == "croc")
            .unwrap();
        let mut seen = std::collections::BTreeSet::new();
        for _ in 0..80 {
            w.slimes[id].dead = true;
            w.slimes[id].respawn = TICK;
            w.update_slime(id);
            assert!(!w.slimes[id].dead);
            let level = w.slimes[id].level;
            assert!((15..=19).contains(&level));
            let expected = (2800. * (1. + 0.12 * (level as f64 - 17.))).round();
            assert_eq!((w.slimes[id].max_hp, w.slimes[id].hp), (expected, expected));
            seen.insert(level);
        }
        assert!(seen.len() >= 4, "levels barely vary: {seen:?}");
    }

    #[test]
    fn sales_check_vendor_range_life_quantity_cooldown_and_save_immediately() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .add_item("slime_gel", 3);
        w.interact(1, "merchant", Some("sell:slime_gel:3"));
        assert_eq!(w.players[&1].character.gold, 0);
        quest_interact(&mut w, "guide", Some("sell:slime_gel:3"));
        assert_eq!(w.players[&1].character.gold, 0);
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        quest_interact(&mut w, "merchant", Some("sell:slime_gel:3"));
        assert_eq!(w.players[&1].character.gold, 0);
        w.players.get_mut(&1).unwrap().character.hp = 120.;
        quest_interact(&mut w, "merchant", Some("sell:slime_gel:4"));
        quest_interact(&mut w, "merchant", Some("sell:slime_gel:0"));
        quest_interact(&mut w, "merchant", Some("sell:unknown:1"));
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 3);
        quest_interact(&mut w, "merchant", Some("sell:slime_gel:1"));
        w.interact(1, "merchant", Some("sell:slime_gel:1"));
        assert_eq!(w.players[&1].character.gold, 3);
        let saved = w.store.load(token).unwrap().unwrap();
        assert_eq!(saved.gold, 3);
        assert_eq!(saved.quantity("slime_gel"), 2);
        quest_interact(&mut w, "smith", Some("sell:materials"));
        assert_eq!(w.players[&1].character.gold, 9);
        quest_interact(&mut w, "smith", Some("sell:materials"));
        assert_eq!(w.players[&1].character.gold, 9);
    }

    #[test]
    fn slot_requests_save_immediately_and_invalid_batches_leave_all_gear_unchanged() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        let hero = &mut w.players.get_mut(&1).unwrap().character;
        hero.level = 15; // the Ironhide Helm needs level 15
        hero.add_item("headgear_upgrade", 1);
        w.message(
            1,
            ClientMessage::Equip {
                armor: None,
                weapon: None,
                slots: [("headgear".into(), "headgear_upgrade".into())].into(),
            },
        );
        let saved = w.store.load(token).unwrap().unwrap();
        assert_eq!(
            saved.equipment.get("headgear").map(String::as_str),
            Some("headgear_upgrade")
        );
        let helm = item("headgear_upgrade").unwrap();
        let expected: (f64, f64) = (22. + 60. + 4. + helm.attack, 3. + helm.defense);
        assert!(
            (saved.stats().0 - expected.0).abs() < 1e-9
                && (saved.stats().1 - expected.1).abs() < 1e-9
        );
        w.message(
            1,
            ClientMessage::Equip {
                armor: Some("none".into()),
                weapon: None,
                slots: [("necklace".into(), "necklace_upgrade".into())].into(),
            },
        );
        assert_eq!(w.players[&1].character.look.warrior_armor, "crimson");
        assert_eq!(w.store.load(token).unwrap().unwrap().stats(), saved.stats());
    }
    #[test]
    fn full_bags_leave_new_loot_on_ground_but_collect_stacks_and_gold() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        let room = 16 - c.bag_used();
        for i in ITEMS
            .iter()
            .filter(|i| i.kind != "bag" && !(i.class == Some(Class::Warrior) && i.starter))
            .take(room)
        {
            c.add_item(&i.id, 1);
        }
        let actor = c.id.clone();
        let point = c.point();
        w.item_drop(&actor, 0, point, "headgear_upgrade", 1);
        w.item_drop(&actor, 0, point, "slime_gel", 2);
        w.drops.push(Drop {
            id: 99999,
            owner: actor,
            zone: 0,
            x: point.x,
            y: point.y,
            z: 0.,
            value: 7,
            item: None,
            quantity: 0,
            t: 1.,
            col: "#ffe066",
            group: vec![],
        });
        for drop in &mut w.drops {
            drop.t = 1.;
        }
        w.update_drops();
        assert_eq!(w.players[&1].character.quantity("headgear_upgrade"), 0);
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 3);
        assert_eq!(w.players[&1].character.gold, 7);
        assert_eq!(w.drops.len(), 1);
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .sell_item("blue_gel", 1)
            .unwrap();
        w.update_drops();
        assert_eq!(w.players[&1].character.quantity("headgear_upgrade"), 1);
        assert_eq!(w.players[&1].character.bag_used(), 16);
        assert!(w.drops.is_empty());
    }
    #[test]
    fn bag_vendor_checks_range_funds_cooldown_and_saves_purchases() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        assert_eq!(
            w.maps[0]
                .npcs
                .iter()
                .find(|n| n.id == "merchant")
                .unwrap()
                .offers
                .len(),
            1
        );
        w.players.get_mut(&1).unwrap().character.gold = 1100;
        w.interact(1, "merchant", Some("satchel"));
        assert!(w.players[&1].character.bags.is_empty());
        quest_interact(&mut w, "merchant", Some("satchel"));
        assert_eq!(w.players[&1].character.gold, 600);
        assert_eq!(w.players[&1].character.bag_capacity(), 22);
        assert_eq!(
            w.store.load(token).unwrap().unwrap().bags,
            vec!["linen_satchel"]
        );
        w.interact(1, "merchant", Some("satchel"));
        assert_eq!(w.players[&1].character.bags.len(), 1);
        quest_interact(&mut w, "merchant", Some("pack"));
        assert_eq!(w.players[&1].character.bag_capacity(), 22);
        assert_eq!(w.players[&1].character.gold, 600);
        quest_interact(&mut w, "merchant", Some("satchel"));
        assert_eq!(w.players[&1].character.bags.len(), 2);
        assert_eq!(w.players[&1].character.gold, 100);
        quest_interact(&mut w, "merchant", Some("satchel"));
        assert_eq!(w.players[&1].character.bags.len(), 2);
        assert_eq!(w.players[&1].character.gold, 100);
    }
    #[test]
    fn stat_training_is_authoritative_and_saves_immediately() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        w.message(
            1,
            ClientMessage::AllocateStat {
                stat: "strength".into(),
            },
        );
        assert_eq!(w.players[&1].character.attributes.strength, 0);
        w.players.get_mut(&1).unwrap().character.grant_xp(100);
        for stat in ["fake", "strength", "stamina", "accuracy", "dexterity"] {
            w.message(1, ClientMessage::AllocateStat { stat: stat.into() });
        }
        let c = &w.players[&1].character;
        assert_eq!(c.stat_points(), 0);
        assert_eq!(c.attributes.strength, 1);
        assert_eq!(c.attributes.dexterity, 0);
        assert_eq!(c.max_hp(), 148.);
        let saved = w.store.load(token).unwrap().unwrap();
        assert_eq!(saved.attributes, c.attributes);
        assert_eq!(saved.stat_points(), 0);
        let snapshot = w.players[&1].snapshot();
        assert_eq!(snapshot["statPoints"], 0);
        assert_eq!(snapshot["hitChance"], c.hit_chance());
        assert_eq!(snapshot["attack"], c.stats().0);
    }
    #[test]
    fn misses_do_not_damage_or_reward_and_dexterity_avoids_real_damage() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let before = w.slimes[0].hp;
        w.hit_slime(0, 1, 0., true);
        assert_eq!(w.slimes[0].hp, before);
        assert_eq!(w.players[&1].character.kills, 0);
        assert_eq!(w.players[&1].character.xp, 0);
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .attributes
            .dexterity = 70;
        let mut dodges = 0;
        let mut hits = 0;
        for _ in 0..60 {
            w.time += 1.;
            let before = w.players[&1].character.hp;
            w.hurt_player(1, 5., Point::default());
            if w.players[&1].character.hp == before {
                dodges += 1;
            } else {
                hits += 1;
            }
        }
        assert!(dodges > 0 && hits > 0);
    }
    #[test]
    fn mob_drops_include_all_class_upgrades_and_collected_items_save() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(4096);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap();
        let id = w.slimes.iter().position(|s| s.kind == "beetle").unwrap();
        let point = w.slimes[id].point();
        // Sample across the growing catalog, keeping the pieces within the test's bag capacity.
        let candidates: Vec<_> = ITEMS.iter().filter(|i| is_gear(i) && !i.starter).collect();
        let gear: Vec<_> = candidates
            .iter()
            .copied()
            .step_by(candidates.len().div_ceil(30))
            .collect();
        assert!(gear.len() > 20 && gear.len() <= 34);
        // Real kills drop the material; gear is rolled so rarely that the pieces are dropped through the same
        // item_drop path the roll uses (the roll itself is covered in items.rs).
        w.slimes[id] = Slime::new(id, &w.maps[0].slimes[id]);
        w.hit_slime(id, 1, 1000., false);
        let owner = w.players[&1].character.id.clone();
        for i in &gear {
            w.item_drop(&owner, 0, point, &i.id, 1);
        }
        for i in &gear {
            assert!(
                w.drops
                    .iter()
                    .any(|d| d.item.as_deref() == Some(i.id.as_str())),
                "{} never dropped",
                i.id
            );
        }
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = point.x;
        c.y = point.y;
        // Four satchels: the whole gear pool no longer fits the 16-cell backpack.
        c.bags = vec!["linen_satchel".to_string(); 4];
        for d in &mut w.drops {
            d.t = 1.;
        }
        w.update_drops();
        let saved = w.store.load(token).unwrap().unwrap();
        assert_eq!(saved.quantity("ironhide_shell"), 1);
        for i in &gear {
            assert!(saved.quantity(&i.id) > 0);
        }
        assert_eq!(
            saved.look.warrior_weapon, "sword",
            "Loot never auto-equips gear"
        );
        assert!(w.drops.is_empty());
    }

    #[test]
    fn town_quest_checks_range_life_giver_objectives_and_single_reward() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.interact(1, "guide", Some("quest:accept:welcome"));
        assert!(w.players[&1].character.quests.is_empty());
        quest_interact(&mut w, "gatekeeper", Some("quest:accept:welcome"));
        assert!(w.players[&1].character.quests.is_empty());
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        quest_interact(&mut w, "guide", Some("quest:accept:welcome"));
        assert!(w.players[&1].character.quests.is_empty());
        w.players.get_mut(&1).unwrap().character.hp = 40.;
        quest_interact(&mut w, "healer", None); // Earlier conversations do not count.
        quest_interact(&mut w, "guide", Some("quest:accept:welcome"));
        assert_eq!(w.players[&1].character.quests[0].counts, vec![0, 0, 0]);
        quest_interact(&mut w, "guide", Some("quest:claim:welcome"));
        assert_eq!(w.players[&1].character.gold, 0);
        quest_interact(&mut w, "healer", None);
        quest_interact(&mut w, "healer", None);
        quest_interact(&mut w, "guide", Some("quest:accept:welcome"));
        assert_eq!(w.players[&1].character.quests[0].counts, vec![1, 0, 0]);
        quest_interact(&mut w, "smith", None);
        quest_interact(&mut w, "innkeeper", None);
        quest_interact(&mut w, "innkeeper", Some("quest:claim:welcome"));
        assert_eq!(w.players[&1].character.gold, 0);
        w.players.get_mut(&1).unwrap().character.xp = 95;
        quest_interact(&mut w, "guide", Some("quest:claim:welcome"));
        let c = &w.players[&1].character;
        assert_eq!((c.level, c.xp, c.gold), (2, 5, 12));
        assert_eq!(c.hp, c.max_hp());
        assert!(c.quests[0].claimed);
        quest_interact(&mut w, "guide", Some("quest:claim:welcome"));
        quest_interact(&mut w, "guide", Some("quest:accept:welcome"));
        assert_eq!(w.players[&1].character.gold, 12);
        assert_eq!(w.players[&1].character.quests[0].completions, 1);
    }

    #[test]
    fn combat_quests_credit_only_accepted_matching_killer_and_unlock_on_turn_in() {
        let mut w = world();
        let _rx1 = join(&mut w, 1, Class::Warrior);
        let _rx2 = join(&mut w, 2, Class::Mage);
        quest_interact(&mut w, "smith", Some("quest:accept:ironhide_hunt"));
        assert!(w.players[&1].character.quests.is_empty());
        w.hit_slime(0, 1, 1000., false);
        quest_interact(&mut w, "gatekeeper", Some("quest:accept:slime_patrol"));
        assert_eq!(w.players[&1].character.quests[0].counts, vec![0]);
        let beetle = w.slimes.iter().position(|s| s.kind == "beetle").unwrap();
        w.hit_slime(beetle, 1, 1000., false);
        assert_eq!(w.players[&1].character.quests[0].counts, vec![0]);
        for _ in 0..6 {
            w.slimes[0] = Slime::new(0, &w.maps[0].slimes[0]);
            w.hit_slime(0, 1, 1000., false);
            w.hit_slime(0, 2, 1000., false); // Dead enemies cannot grant a second credit.
        }
        assert_eq!(w.players[&1].character.quests[0].counts, vec![6]);
        assert!(w.players[&2].character.quests.is_empty());
        quest_interact(&mut w, "smith", Some("quest:accept:ironhide_hunt"));
        assert_eq!(w.players[&1].character.quests.len(), 1);
        quest_interact(&mut w, "gatekeeper", Some("quest:claim:slime_patrol"));
        quest_interact(&mut w, "smith", Some("quest:accept:ironhide_hunt"));
        assert_eq!(w.players[&1].character.quests[1].counts, vec![0]);
        for _ in 0..2 {
            w.slimes[beetle] = Slime::new(beetle, &w.maps[0].slimes[beetle]);
            w.hit_slime(beetle, 1, 1000., false);
        }
        quest_interact(&mut w, "smith", Some("quest:claim:ironhide_hunt"));
        quest_interact(&mut w, "gatekeeper", Some("quest:accept:king_challenge"));
        let king = w.slimes.iter().position(|s| s.kind == "big").unwrap();
        w.slimes[king] = Slime::new(king, &w.maps[0].slimes[king]);
        w.hit_slime(king, 1, 1000., false);
        quest_interact(&mut w, "gatekeeper", Some("quest:claim:king_challenge"));
        assert_eq!(w.players[&1].character.gold, 24 + 35 + 60);
    }

    #[test]
    fn repeatable_bounty_resets_and_claims_survive_restart() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        quest_interact(&mut w, "gatekeeper", Some("quest:accept:slime_patrol"));
        for _ in 0..6 {
            quest_progress(
                &mut w.players.get_mut(&1).unwrap().character,
                &w.maps[0].quests,
                "kill",
                "green",
            );
        }
        quest_interact(&mut w, "gatekeeper", Some("quest:claim:slime_patrol"));
        quest_interact(&mut w, "merchant", Some("quest:accept:meadow_bounty"));
        for target in [
            "green", "blue", "pink", "yellow", "beetle", "big", "green", "green",
        ] {
            quest_progress(
                &mut w.players.get_mut(&1).unwrap().character,
                &w.maps[0].quests,
                "kill",
                target,
            );
        }
        quest_interact(&mut w, "merchant", Some("quest:claim:meadow_bounty"));
        let saved = w.store.load(&token).unwrap().unwrap(); // Claim saves immediately.
        assert_eq!(saved.gold, 49);
        assert_eq!(saved.quests[1].completions, 1);
        w.players.get_mut(&1).unwrap().character = saved;
        quest_interact(&mut w, "merchant", Some("quest:claim:meadow_bounty"));
        assert_eq!(w.players[&1].character.gold, 49);
        quest_interact(&mut w, "merchant", Some("quest:accept:meadow_bounty"));
        let saved = w.store.load(&token).unwrap().unwrap();
        assert_eq!(saved.quests[1].counts, vec![0]);
        assert!(!saved.quests[1].claimed);
        assert_eq!(saved.quests[1].completions, 1);
        quest_interact(&mut w, "merchant", Some("quest:claim:meadow_bounty"));
        assert_eq!(w.players[&1].character.gold, 49);
    }

    #[test]
    fn every_class_can_defeat_an_enemy_from_separate_tiles() {
        for class in [Class::Warrior, Class::Assassin, Class::Mage] {
            for diagonal in [false, true] {
                let mut w = world();
                let _rx = join(&mut w, 1, class);
                w.maps[0].objects.clear();
                for s in &mut w.slimes {
                    s.dead = true;
                    s.respawn = 1000.;
                }
                let start = w.players[&1].character.point();
                w.slimes[0] = Slime::new(
                    0,
                    &SlimeSpawn {
                        ambush: None,
                        kind: "green".into(),
                        zone: 0,
                        x: start.x + 3.5,
                        y: start.y + if diagonal { 3.5 } else { 0. },
                    },
                );
                w.message(1, ClientMessage::Target { id: 0 });
                for _ in 0..360 {
                    w.step();
                    if w.slimes[0].dead {
                        break;
                    }
                    let p = w.players[&1].character.point();
                    assert!(!same_cell(p, w.slimes[0].point()));
                    assert!(p.distance(w.slimes[0].point()) >= 1. - 1e-8);
                }
                assert!(
                    w.slimes[0].dead,
                    "{class:?} combat must work across tile edges"
                );
                assert!(w.players[&1].character.hp > 0.);
                assert_eq!(w.players[&1].character.kills, 1);
            }
        }
    }

    #[test]
    fn enemies_block_each_other_but_players_can_walk_and_dash_through_actors() {
        let map = Map {
            name: String::new(),
            size: 96,
            spawn: Point::default(),
            objects: vec![],
            slimes: vec![],
            npcs: vec![],
            quests: vec![],
            city: None,
            camps: vec![],
            places: vec![],
            portals: vec![],
            levels: None,
            zones: vec![],
            copies: 0,
            final_boss: String::new(),
            players: 0,
            min_level: 0,
            template: None,
        };
        let blocker = Point { x: 21.9, y: 20.5 };
        for (start, direction, distance) in [
            (Point { x: 20.5, y: 20.5 }, Point { x: 1., y: 0. }, 4.),
            (Point { x: 20.5, y: 19.5 }, normalize(1., 1.), 4.),
        ] {
            let mut point = start;
            walk_with_actors(
                &map,
                &mut point,
                direction,
                distance,
                PLAYER_RADIUS,
                &[(blocker, 0.3)],
            );
            assert!(!same_cell(point, blocker));
            assert!(point.distance(blocker) >= 0.6 - 1e-8);
            // Even a long enemy charge cannot pass through an occupied tile.
            if start.y == blocker.y {
                assert!(point.x < 21.);
            }
        }
        let mut w = world();
        let _a = join(&mut w, 1, Class::Assassin);
        let _b = join(&mut w, 2, Class::Warrior);
        assert!(same_cell(
            w.players[&1].character.point(),
            w.players[&2].character.point()
        ));
        assert!(
            w.players[&1]
                .character
                .point()
                .distance(w.players[&2].character.point())
                < 1e-8
        );
        let start = w.players[&1].character.point();
        w.slimes[0] = Slime::new(
            0,
            &SlimeSpawn {
                ambush: None,
                kind: "green".into(),
                zone: 0,
                x: start.x + 1.5,
                y: start.y,
            },
        );
        w.slimes[0].state = "windup".into();
        w.slimes[0].st = 100.;
        w.message(1, ClientMessage::Dash { dx: 1., dy: 0. });
        for _ in 0..5 {
            w.update_player(1);
        }
        assert!(w.players[&1].character.x > w.slimes[0].x + 0.5);
        let goal = w.players[&2].character.point();
        w.players.get_mut(&1).unwrap().dash = 0.;
        w.message(
            1,
            ClientMessage::Move {
                x: goal.x,
                y: goal.y,
            },
        );
        for _ in 0..60 {
            w.update_player(1);
        }
        assert!(same_cell(w.players[&1].character.point(), goal));
        w.players.get_mut(&1).unwrap().character.x = w.slimes[0].x;
        w.players.get_mut(&1).unwrap().character.y = w.slimes[0].y;
        w.separate_enemies();
        assert!(
            w.slimes[0]
                .point()
                .distance(w.players[&1].character.point())
                >= 1. - 1e-8
        );
        assert!(!same_cell(
            w.slimes[0].point(),
            w.players[&1].character.point()
        ));
        w.maps[0].objects.clear();
        let destination = Point {
            x: start.x + 6.,
            y: start.y,
        };
        w.message(
            1,
            ClientMessage::Move {
                x: destination.x,
                y: destination.y,
            },
        );
        for _ in 0..60 {
            w.step();
            assert!(
                w.slimes[0]
                    .point()
                    .distance(w.players[&1].character.point())
                    >= 1. - 1e-8
            );
            assert!(!same_cell(
                w.slimes[0].point(),
                w.players[&1].character.point()
            ));
        }
        assert!(w.players[&1].character.point().distance(destination) < 0.15);
    }

    #[test]
    fn enemies_cannot_stack_or_charge_through_players_and_dead_bodies_do_not_block() {
        let mut w = world();
        w.maps[0].objects.clear(); // Isolate actor collision from scenery in this lane.
        let _rx = join(&mut w, 1, Class::Warrior);
        let player = w.players[&1].character.point();
        w.slimes[0] = Slime::new(
            0,
            &SlimeSpawn {
                ambush: None,
                kind: "beetle".into(),
                zone: 0,
                x: player.x + 1.,
                y: player.y,
            },
        );
        w.slimes[0].state = "lunge".into();
        w.slimes[0].st = 0.3;
        w.slimes[0].target = Some(1);
        w.slimes[0].goal = player;
        for _ in 0..12 {
            w.update_slime(0);
            assert!(!same_cell(w.slimes[0].point(), player));
            assert!(w.slimes[0].point().distance(player) >= 1. - 1e-8);
        }
        assert!(
            w.players[&1].character.hp < 120.,
            "Charge damage still lands at contact"
        );
        let blocked = w.slimes[0].point();
        w.slimes[1] = Slime::new(
            1,
            &SlimeSpawn {
                ambush: None,
                kind: "green".into(),
                zone: 0,
                x: blocked.x + 2.,
                y: blocked.y,
            },
        );
        w.slimes[1].state = "wander".into();
        w.slimes[1].st = 100.;
        w.slimes[1].goal = blocked;
        w.slimes[0].state = "windup".into();
        w.slimes[0].st = 100.;
        // Put the player out of awareness so this exercises wandering against another enemy.
        w.players.get_mut(&1).unwrap().character.x = 70.;
        for _ in 0..100 {
            w.update_slime(1);
            assert!(!same_cell(w.slimes[0].point(), w.slimes[1].point()));
        }
        w.slimes[0].dead = true;
        let mut entered = false;
        for _ in 0..100 {
            w.update_slime(1);
            entered |= same_cell(w.slimes[1].point(), blocked);
        }
        assert!(entered, "A dead enemy releases its occupied tile");
    }

    #[test]
    fn players_can_share_respawn_and_saved_tiles_while_enemies_spawn_clear() {
        let mut w = world();
        let _a = join(&mut w, 1, Class::Warrior);
        let _b = join(&mut w, 2, Class::Mage);
        let occupied = w.players[&1].character.point();
        let p = w.players.get_mut(&2).unwrap();
        p.character.hp = 0.;
        p.dead_time = 3.2;
        w.update_player(2);
        assert!(same_cell(w.players[&2].character.point(), occupied));
        let enemy_spawn = w.maps[0].slimes[0].clone();
        w.players.get_mut(&1).unwrap().character.x = enemy_spawn.x;
        w.players.get_mut(&1).unwrap().character.y = enemy_spawn.y;
        w.slimes[0].dead = true;
        w.slimes[0].respawn = TICK;
        w.update_slime(0);
        assert!(!w.slimes[0].dead);
        assert!(!same_cell(
            w.slimes[0].point(),
            w.players[&1].character.point()
        ));
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(3, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let saved = w.players[&3].character.point();
        w.leave(3);
        w.players.get_mut(&2).unwrap().character.x = saved.x;
        w.players.get_mut(&2).unwrap().character.y = saved.y;
        let (tx, _rx) = mpsc::channel(256);
        w.join(4, Some(token), None, tx).unwrap();
        assert!(same_cell(w.players[&4].character.point(), saved));
        let locations: Vec<_> = w.maps[0]
            .slimes
            .iter()
            .filter(|s| s.kind == "big")
            .cloned()
            .collect();
        for (session, spawn) in [1, 2].into_iter().zip(locations) {
            w.players.get_mut(&session).unwrap().character.x = spawn.x;
            w.players.get_mut(&session).unwrap().character.y = spawn.y;
        }
        w.time = w.next_king_spawn;
        w.update_king_spawn();
        let king = w
            .slimes
            .iter()
            .find(|s| s.kind == "big" && !s.dead)
            .unwrap();
        assert!(!actor_blocked(
            king.point(),
            king.r,
            &w.actor_bodies(king.zone, None, Some(king.id))
        ));
    }

    #[test]
    fn king_timer_spawns_one_random_location_and_announces_it() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        assert!((KING_SPAWN_MIN..KING_SPAWN_MAX).contains(&w.next_king_spawn));
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.kind == "big")
                .all(|s| s.dead && s.hp == 0. && s.die_t >= 2.)
        );
        let deadline = w.next_king_spawn;
        w.time = deadline - TICK;
        w.update_king_spawn();
        assert!(w.slimes.iter().filter(|s| s.kind == "big").all(|s| s.dead));
        w.time = deadline;
        w.update_king_spawn();
        let kings: Vec<_> = w
            .slimes
            .iter()
            .filter(|s| s.kind == "big" && !s.dead)
            .collect();
        assert_eq!(kings.len(), 1);
        assert_eq!(kings[0].hp, 600.);
        let id = kings[0].id;
        assert_eq!(kings[0].x, w.maps[0].slimes[id].x);
        assert_eq!(kings[0].y, w.maps[0].slimes[id].y);
        assert_eq!(rx.try_recv().unwrap()["type"], "system"); // Join notice.
        assert!(
            rx.try_recv().unwrap()["text"]
                .as_str()
                .unwrap()
                .contains("King Slime")
        );
        w.time += KING_SPAWN_MAX * 10.;
        w.update_king_spawn();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.kind == "big" && !s.dead)
                .count(),
            1
        );
        assert!(rx.try_recv().is_err());

        // Both timer length and location vary with the server RNG, deterministically here.
        let mut locations = std::collections::BTreeSet::new();
        let mut delays = std::collections::BTreeSet::new();
        for seed in 1..=32 {
            let mut w = world();
            w.rng = seed;
            let delay = w.king_spawn_delay();
            assert!((KING_SPAWN_MIN..KING_SPAWN_MAX).contains(&delay));
            delays.insert(delay.to_bits());
            w.time = w.next_king_spawn;
            w.update_king_spawn();
            locations.insert(
                w.slimes
                    .iter()
                    .find(|s| s.kind == "big" && !s.dead)
                    .unwrap()
                    .id,
            );
        }
        assert_eq!(locations.len(), 2);
        assert!(delays.len() > 1);
    }

    #[test]
    fn king_defeat_reschedules_without_fast_respawn_or_duplicate_rewards() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.time = w.next_king_spawn;
        w.update_king_spawn();
        let id = w
            .slimes
            .iter()
            .find(|s| s.kind == "big" && !s.dead)
            .unwrap()
            .id;
        w.hit_slime(id, 1, 1000., false);
        let deadline = w.next_king_spawn;
        assert!((KING_SPAWN_MIN..KING_SPAWN_MAX).contains(&(deadline - w.time)));
        w.hit_slime(id, 1, 1000., false);
        assert_eq!(w.next_king_spawn, deadline);
        assert_eq!(w.players[&1].character.kills, 1);
        assert_eq!(w.players[&1].character.xp, 75);
        assert_eq!(w.drops.iter().filter(|d| d.item.is_none()).count(), 1);
        assert_eq!(
            w.drops
                .iter()
                .filter(|d| d
                    .item
                    .as_deref()
                    .is_some_and(|id| item(id).unwrap().kind == "material"))
                .count(),
            1
        );
        assert_eq!(w.drops[0].value, 30);
        for _ in 0..500 {
            w.time += TICK;
            w.update_king_spawn();
            w.update_slime(id);
        }
        assert!(
            w.slimes[id].dead,
            "Kings must not use the normal 22-second respawn"
        );
        w.time = deadline - TICK;
        w.update_king_spawn();
        assert!(w.slimes.iter().filter(|s| s.kind == "big").all(|s| s.dead));
        w.time = deadline;
        w.update_king_spawn();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.kind == "big" && !s.dead)
                .count(),
            1
        );
        assert_eq!(
            w.slimes
                .iter()
                .find(|s| s.kind == "big" && !s.dead)
                .unwrap()
                .hp,
            600.
        );
        assert_eq!(w.players[&1].character.kills, 1);
    }

    #[test]
    fn harder_enemies_spawn_clear_and_charge_with_authoritative_damage() {
        let w = world();
        assert_eq!(w.slimes.iter().filter(|s| s.kind == "beetle").count(), 7);
        for s in &w.slimes {
            let mut point = s.point();
            w.maps[s.zone].collide(&mut point, s.r);
            assert!(
                point.distance(s.point()) < 1e-6,
                "{} spawn is blocked",
                s.kind
            );
            assert!(!w.maps[s.zone].in_city(s.point()));
        }
        for (kind, hp, damage, windup) in [("beetle", 240., 22., 0.4), ("big", 600., 30., 0.35)] {
            let mut w = world();
            let _rx = join(&mut w, 1, Class::Warrior);
            let point = w.players[&1].character.point();
            // Arrange one enemy nearby; exercise its actual chase, windup and charge AI.
            w.slimes[0] = Slime::new(
                0,
                &SlimeSpawn {
                    ambush: None,
                    kind: kind.into(),
                    zone: 0,
                    x: point.x + 1.,
                    y: point.y,
                },
            );
            w.slimes[0].atk_cd = 0.;
            w.update_slime(0);
            assert_eq!(w.slimes[0].max_hp, hp);
            assert_eq!(w.slimes[0].state, "windup");
            assert_eq!(w.snapshot_for(0)["slimes"][0]["windupTime"], windup);
            assert_eq!(w.players[&1].character.hp, 120.);
            for _ in 0..20 {
                w.time += TICK;
                w.update_slime(0);
            }
            let defense = w.players[&1].character.look.stats(1).1;
            let taken = ((damage - defense) * DAMAGE_TAKEN_SCALE).round().max(1.);
            assert_eq!(w.players[&1].character.hp, 120. - taken);
        }
    }

    #[test]
    fn god_mode_stops_all_player_damage_and_is_off_by_default() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        assert!(!w.god_mode);
        w.time += 5.;
        w.hurt_player(1, 30., Point::default());
        assert!(w.players[&1].character.hp < 120., "normal worlds hurt");
        w.god_mode = true;
        let hp = w.players[&1].character.hp;
        w.time += 5.;
        w.hurt_player(1, 500., Point::default());
        assert_eq!(w.players[&1].character.hp, hp);
    }

    #[test]
    fn zone_data_is_valid_and_portals_connect_clear_arrival_points() {
        let w = world();
        assert_eq!(zone_count(&w), 14);
        assert_eq!(w.spawns.len(), w.slimes.len());
        assert_eq!(w.maps[1].name, "Emberfall Crags");
        assert_eq!(w.maps[1].levels, Some([5, 10]));
        for kind in ["wisp", "spider", "wraith", "golem"] {
            assert!(
                w.slimes.iter().any(|s| s.kind == kind && s.zone == 1),
                "no {kind} in the Crags"
            );
            assert_ne!(
                Slime::stats(kind),
                Slime::stats("green"),
                "{kind} has stats"
            );
            assert!(Slime::default_level(kind) >= 5);
        }
        assert!(
            w.slimes
                .iter()
                .filter(|s| s.zone == 0)
                .all(|s| Slime::default_level(&s.kind) <= 6)
        );
        for s in &w.slimes {
            let mut point = s.point();
            w.maps[s.zone].collide(&mut point, s.r);
            assert!(
                point.distance(s.point()) < 1e-6,
                "{} spawn is blocked",
                s.kind
            );
            assert!(!w.maps[s.zone].in_city(s.point()));
        }
        for (zone, map) in w.maps.iter().enumerate() {
            assert!(!map.portals.is_empty(), "zone {zone} has no portal");
            for portal in &map.portals {
                let target = &w.maps[portal.to];
                let mut arrival = Point {
                    x: portal.tx,
                    y: portal.ty,
                };
                target.collide(&mut arrival, PLAYER_RADIUS);
                assert!(
                    arrival.distance(Point {
                        x: portal.tx,
                        y: portal.ty
                    }) < 1e-6
                );
                assert!(
                    target.portals.iter().all(|back| arrival.distance(Point {
                        x: back.x,
                        y: back.y
                    }) > back.r + 0.5),
                    "arrival from {} would trigger a portal at once",
                    portal.id
                );
                assert!(
                    target
                        .portals
                        .iter()
                        .any(|back| back.to == w.public_zone(zone)),
                    "{} has no way back",
                    portal.id
                );
            }
        }
        // No enemy starts near either arrival point.
        for (zone, map) in w.maps.iter().enumerate() {
            for portal in &map.portals {
                for s in w.slimes.iter().filter(|s| s.zone == portal.to) {
                    assert!(
                        s.point().distance(Point {
                            x: portal.tx,
                            y: portal.ty
                        }) > 8.,
                        "{} spawns beside the arrival from zone {zone}",
                        s.kind
                    );
                }
            }
        }
    }

    #[test]
    fn enemy_levels_roll_two_either_side_of_each_kinds_default() {
        let mut w = World::new(Store::open(std::path::Path::new(":memory:")).unwrap());
        for s in &w.slimes {
            let default = if crate::cathedral::enemy(&s.kind).is_some() {
                w.maps[s.zone].min_level
            } else {
                Slime::default_level(&s.kind)
            };
            assert!(
                (default.saturating_sub(2).max(1)..=default + 2).contains(&s.level),
                "{} level {} is outside {default}±2",
                s.kind,
                s.level
            );
            // A dungeon's enemies never roll (they stay at their level) and a view of an unused copy lists none.
            if w.is_instance(s.zone) {
                assert_eq!(
                    s.level, default,
                    "{} keeps its level inside a dungeon",
                    s.kind
                );
                continue;
            }
            let view = w.snapshot_for(s.zone);
            let listed = view["slimes"]
                .as_array()
                .unwrap()
                .iter()
                .find(|e| e["id"] == s.id)
                .unwrap();
            assert_eq!(listed["level"], s.level);
            assert_eq!(listed["zone"], s.zone);
        }
        for kind in [
            "green", "blue", "beetle", "big", "wisp", "spider", "wraith", "golem",
        ] {
            let default = Slime::default_level(kind) as i32;
            let mut seen = std::collections::BTreeSet::new();
            let kills = 1000;
            for _ in 0..kills {
                seen.insert(w.roll_level(kind) as i32);
            }
            let expected: std::collections::BTreeSet<_> =
                ((default - 2).max(1)..=default + 2).collect();
            assert_eq!(
                seen, expected,
                "{kind} should cover its whole spread, never below 1"
            );
        }
        // With no spread every enemy sits exactly on its default.
        let w = world();
        assert!(w.slimes.iter().all(|s| s.level
            == if crate::cathedral::enemy(&s.kind).is_some() {
                w.maps[s.zone].min_level
            } else {
                Slime::default_level(&s.kind)
            }));
    }

    #[test]
    fn level_changes_health_damage_xp_and_gold_around_the_default() {
        let spawn = |kind: &str| SlimeSpawn {
            ambush: None,
            kind: kind.into(),
            x: 10.,
            y: 10.,
            zone: 0,
        };
        let base = Slime::with_level(0, &spawn("beetle"), 5);
        assert_eq!(
            (base.max_hp, base.damage, base.xp, base.gold),
            (240., 22., 70, 10)
        );
        let high = Slime::with_level(0, &spawn("beetle"), 7);
        assert_eq!(
            (high.max_hp, high.damage, high.xp, high.gold),
            (298., 27., 80, 12)
        );
        let low = Slime::with_level(0, &spawn("beetle"), 3);
        assert_eq!(
            (low.max_hp, low.damage, low.xp, low.gold),
            (182., 17., 60, 8)
        );
        assert_eq!(high.r, base.r, "level never changes body size");
        // A kill pays the rolled enemy's XP and gold, not the kind's default.
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let id = w.slimes.iter().position(|s| s.kind == "beetle").unwrap();
        w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), 7);
        w.hit_slime(id, 1, 5000., false);
        assert_eq!(w.players[&1].character.xp, 80);
        assert_eq!(w.drops.iter().find(|d| d.item.is_none()).unwrap().value, 12);
    }

    #[test]
    fn respawning_enemies_roll_a_fresh_level() {
        let mut w = World::new(Store::open(std::path::Path::new(":memory:")).unwrap());
        let _rx = join(&mut w, 1, Class::Warrior);
        let id = w.slimes.iter().position(|s| s.kind == "spider").unwrap();
        let mut seen = std::collections::BTreeSet::new();
        for _ in 0..80 {
            w.slimes[id].dead = true;
            w.slimes[id].respawn = TICK;
            w.update_slime(id);
            assert!(!w.slimes[id].dead);
            let level = w.slimes[id].level;
            assert!((5..=9).contains(&level));
            let expected = (420. * (1. + 0.12 * (level as f64 - 7.))).round();
            assert_eq!(w.slimes[id].max_hp, expected);
            assert_eq!(w.slimes[id].hp, expected);
            seen.insert(level);
        }
        assert!(seen.len() >= 4, "levels barely vary: {seen:?}");
    }

    #[test]
    fn portals_move_players_between_zones_save_the_zone_and_never_bounce() {
        let mut w = world();
        let (tx, mut rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let gate = w.maps[0].portals[0].clone();
        let back = w.maps[1].portals[0].clone();
        assert_eq!(w.players[&1].character.zone, 0);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = gate.x;
            c.y = gate.y + 4.;
        }
        // A real walk goal north through the gate; the server decides the zone change.
        w.message(
            1,
            ClientMessage::Move {
                x: gate.x,
                y: gate.y - 1.,
            },
        );
        for _ in 0..200 {
            w.time += TICK;
            w.update_player(1);
            if w.players[&1].character.zone == 1 {
                break;
            }
        }
        let c = &w.players[&1].character;
        assert_eq!(c.zone, 1);
        assert!(
            c.point().distance(Point {
                x: gate.tx,
                y: gate.ty
            }) < 1e-6
        );
        assert_eq!(w.snapshot_for(1)["players"][0]["zone"], 1);
        assert!(
            w.snapshot_for(0)["players"].as_array().unwrap().is_empty(),
            "players appear only in their own zone's view"
        );
        assert_eq!(
            w.store.load(&token).unwrap().unwrap().zone,
            1,
            "the zone saves at once"
        );
        let mut texts = vec![];
        while let Ok(v) = rx.try_recv() {
            if v["type"] == "system" {
                texts.push(v["text"].as_str().unwrap().to_owned());
            }
        }
        assert!(
            texts
                .iter()
                .any(|t| t.contains("Emberfall Crags") && t.contains("5–10")),
            "{texts:?}"
        );
        // Standing on the arrival point or inside the way back too soon does nothing.
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = back.x;
            c.y = back.y;
        }
        w.update_player(1);
        assert_eq!(w.players[&1].character.zone, 1, "no instant bounce");
        w.time += PORTAL_DELAY + 0.1;
        w.update_player(1);
        assert_eq!(w.players[&1].character.zone, 0);
        assert!(
            w.players[&1].character.point().distance(Point {
                x: back.tx,
                y: back.ty
            }) < 1e-6
        );
        // Resuming a saved zone puts the character back where it was.
        w.players.get_mut(&1).unwrap().character.zone = 1;
        w.players.get_mut(&1).unwrap().character.x = 40.;
        w.players.get_mut(&1).unwrap().character.y = 80.;
        w.leave(1);
        let (tx, _rx2) = mpsc::channel(256);
        w.join(2, Some(token.clone()), None, tx).unwrap();
        assert_eq!(w.players[&2].character.zone, 1);
        assert!(
            w.players[&2]
                .character
                .point()
                .distance(Point { x: 40., y: 80. })
                < 1e-6
        );
    }

    #[test]
    fn a_dead_player_cannot_use_a_portal_and_respawns_in_their_own_zone() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        let gate = w.maps[0].portals[0].clone();
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.x = gate.x;
            p.character.y = gate.y;
            p.character.hp = 0.;
        }
        w.update_player(1);
        assert_eq!(w.players[&1].character.zone, 0);
        // Dying in the Crags brings you back at the Crags' own camp, healed.
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.zone = 1;
            p.character.x = 10.;
            p.character.y = 10.;
            p.dead_time = 3.3;
        }
        w.update_player(1);
        let c = &w.players[&1].character;
        assert_eq!(c.zone, 1);
        assert_eq!(c.hp, c.max_hp());
        assert!(c.point().distance(w.maps[1].spawn) < 1.);
    }

    #[test]
    fn zones_do_not_share_targets_attacks_events_or_drops() {
        let mut w = world();
        let mut rx1 = join(&mut w, 1, Class::Warrior);
        let (tx2, mut rx2) = mpsc::channel(256);
        w.join(2, None, Some(Look::default()), tx2).unwrap();
        let wisp = w.slimes.iter().position(|s| s.kind == "wisp").unwrap();
        let spot = w.slimes[wisp].point();
        // A meadow player cannot target, hit or aggravate a Crags enemy standing at the same coordinates.
        {
            let p = w.players.get_mut(&1).unwrap();
            p.character.x = spot.x - 0.9;
            p.character.y = spot.y;
            p.face = Point { x: 1., y: 0. };
        }
        w.message(1, ClientMessage::Target { id: wisp });
        assert!(
            w.players[&1].target.is_none(),
            "other-zone targets are refused"
        );
        for _ in 0..20 {
            w.strike(1);
        }
        assert_eq!(w.slimes[wisp].hp, w.slimes[wisp].max_hp);
        w.slimes[wisp].atk_cd = 0.;
        w.update_slime(wisp);
        assert_eq!(w.slimes[wisp].state, "idle", "no chase across zones");
        // Once the player stands in the Crags the same enemy is a valid target and hurts.
        w.players.get_mut(&1).unwrap().character.zone = 1;
        w.message(1, ClientMessage::Target { id: wisp });
        assert_eq!(w.players[&1].target, Some(wisp));
        for _ in 0..20 {
            w.strike(1);
        }
        assert!(w.slimes[wisp].hp < w.slimes[wisp].max_hp);
        // Events go only to the zone they happened in.
        while rx1.try_recv().is_ok() {}
        while rx2.try_recv().is_ok() {}
        let actor = w.players[&1].character.id.clone();
        w.event("hit", &actor, spot, 5., false);
        assert!(rx1.try_recv().is_ok_and(|v| v["kind"] == "hit"));
        assert!(
            rx2.try_recv().is_err(),
            "a Crags event must not reach the meadow"
        );
        // A kill's loot belongs to the Crags: the killer cannot collect it from the meadow.
        w.hit_slime(wisp, 1, 100_000., false);
        assert!(w.drops.iter().all(|d| d.zone == 1) && !w.drops.is_empty());
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.zone = 0;
        c.x = spot.x;
        c.y = spot.y;
        for d in &mut w.drops {
            d.t = 1.;
        }
        let gold = w.players[&1].character.gold;
        w.update_drops();
        assert_eq!(w.players[&1].character.gold, gold);
        assert!(!w.drops.is_empty());
        w.players.get_mut(&1).unwrap().character.zone = 1;
        w.update_drops();
        assert!(w.players[&1].character.gold > gold);
    }

    #[test]
    fn crag_monsters_charge_with_their_own_authoritative_damage_and_rewards() {
        for (kind, hp, damage, windup, gold, material_id, xp) in [
            ("wisp", 280., 34., 0.35, 18, "ember_core", 70),
            ("spider", 420., 42., 0.4, 26, "magma_fang", 80),
            ("wraith", 520., 52., 0.5, 36, "ash_veil", 85),
            ("golem", 1100., 64., 0.6, 55, "basalt_heart", 95),
        ] {
            let mut w = world();
            let _rx = join(&mut w, 1, Class::Warrior);
            let id = w.slimes.iter().position(|s| s.kind == kind).unwrap();
            {
                let p = w.players.get_mut(&1).unwrap();
                p.character.zone = 1;
                p.character.x = w.slimes[id].x - 1.;
                p.character.y = w.slimes[id].y;
                p.character.hp = 1000.;
            }
            let point = w.players[&1].character.point();
            w.slimes[id] = Slime::new(
                id,
                &SlimeSpawn {
                    ambush: None,
                    kind: kind.into(),
                    x: point.x + 1.,
                    y: point.y,
                    zone: 1,
                },
            );
            w.slimes[id].atk_cd = 0.;
            w.update_slime(id);
            assert_eq!(w.slimes[id].max_hp, hp, "{kind} health");
            assert_eq!(w.slimes[id].state, "windup", "{kind} winds up");
            let view = w.snapshot_for(1);
            let listed = view["slimes"]
                .as_array()
                .unwrap()
                .iter()
                .find(|e| e["id"] == id)
                .unwrap();
            assert_eq!(listed["windupTime"], windup);
            for _ in 0..60 {
                w.time += TICK;
                w.update_slime(id);
                if w.players[&1].character.hp < 1000. {
                    break;
                }
            }
            let defense = w.players[&1].character.look.stats(1).1;
            let taken = ((damage - defense) * DAMAGE_TAKEN_SCALE).round().max(1.);
            assert_eq!(w.players[&1].character.hp, 1000. - taken, "{kind} damage");
            // Killing one pays its XP, gold and material in its own zone.
            w.hit_slime(id, 1, 100_000., false);
            let c = &w.players[&1].character;
            assert_eq!(c.kills, 1);
            let paid: u32 = (1..c.level).map(xp_to_level).sum::<u32>() + c.xp;
            assert_eq!(paid, xp, "{kind} xp");
            assert_eq!(
                w.drops.iter().find(|d| d.item.is_none()).unwrap().value,
                gold,
                "{kind} gold"
            );
            assert!(
                w.drops
                    .iter()
                    .any(|d| d.item.as_deref() == Some(material_id)),
                "{kind} material"
            );
        }
    }

    #[test]
    fn leveling_follows_the_level_table_and_carries_remaining_xp() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        assert_eq!(w.players[&1].character.xp_need(), 100);
        w.hit_slime(0, 1, 1000., false);
        w.slimes[0].respawn = TICK;
        w.update_slime(0);
        assert_eq!(w.players[&1].character.level, 1);
        assert_eq!(
            w.players[&1].character.xp, 55,
            "a level-2 green pays 45 + 5 x 2"
        );
        w.hit_slime(0, 1, 1000., false);
        assert_eq!(w.players[&1].character.level, 2);
        assert_eq!(w.players[&1].character.xp, 10);
        assert_eq!(w.players[&1].character.xp_need(), 200);
        assert_eq!(w.players[&1].character.hp, 140.);
    }

    #[test]
    fn beetle_rewards_once_and_respawns_with_full_health() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        let id = w.slimes.iter().position(|s| s.kind == "beetle").unwrap();
        w.hit_slime(id, 1, 1000., false);
        w.hit_slime(id, 1, 1000., false);
        assert_eq!(w.players[&1].character.kills, 1);
        assert_eq!(w.players[&1].character.xp, 70);
        assert_eq!(w.drops.iter().filter(|d| d.item.is_none()).count(), 1);
        assert_eq!(
            w.drops
                .iter()
                .filter(|d| d
                    .item
                    .as_deref()
                    .is_some_and(|id| item(id).unwrap().kind == "material"))
                .count(),
            1
        );
        assert_eq!(w.drops[0].value, 10);
        w.slimes[id].respawn = TICK;
        w.update_slime(id);
        assert!(!w.slimes[id].dead);
        assert_eq!(w.slimes[id].hp, 240.);
        assert_eq!(w.slimes[id].kind, "beetle");
    }

    #[test]
    fn npc_services_check_distance_price_health_and_offer_ids() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(rx.try_recv().unwrap()["type"], "system");
        assert_eq!(rx.try_recv().unwrap()["type"], "error");
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = 42.;
        c.y = 78.5;
        c.hp = 40.;
        c.gold = 7;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.hp, 40.);
        assert_eq!(w.players[&1].character.gold, 7);
        w.time += 1.;
        w.players.get_mut(&1).unwrap().character.gold = 8;
        w.interact(1, "apothecary", Some("unknown"));
        assert_eq!(w.players[&1].character.gold, 8);
        w.time += 1.;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.hp, 100.);
        assert_eq!(w.players[&1].character.gold, 0);
        // Repeated requests cannot bypass the service cooldown.
        w.players.get_mut(&1).unwrap().character.gold = 8;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.gold, 8);
        w.time += 1.;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.hp, 120.);
        w.time += 1.;
        w.players.get_mut(&1).unwrap().character.gold = 8;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(
            w.players[&1].character.gold, 8,
            "full-health shoppers are not charged"
        );
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        w.time += 1.;
        w.interact(1, "apothecary", Some("tonic"));
        assert_eq!(w.players[&1].character.hp, 0.);
    }

    #[test]
    fn sanctuary_heals_and_armorer_fits_each_class_and_city_is_safe() {
        for class in [Class::Warrior, Class::Mage, Class::Assassin] {
            let mut w = world();
            let _rx = join(&mut w, 1, class);
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = 30.;
            c.y = 78.5;
            c.hp = 10.;
            w.interact(1, "healer", Some("blessing"));
            assert_eq!(w.players[&1].character.hp, class.health());
            assert_eq!(w.players[&1].character.gold, 0);
            w.time += 1.;
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = 31.;
            c.y = 88.;
            w.interact(1, "smith", Some("fitting"));
            assert!(w.players[&1].character.look.validate().is_ok());
            assert!(w.players[&1].character.look.stats(1).1 > 0.);
            w.hurt_player(1, 1000., Point::default());
            assert_eq!(w.players[&1].character.hp, class.health());
            // A slime pursuing an adventurer loses its target at the city gate.
            w.slimes[0].x = 36.;
            w.slimes[0].y = 71.5;
            w.slimes[0].target = Some(1);
            w.slimes[0].state = "chase".into();
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.x = 36.;
            c.y = 73.;
            w.update_slime(0);
            assert!(w.slimes[0].target.is_none());
            assert!(!w.maps[0].in_city(w.slimes[0].point()));
        }
    }

    #[test]
    fn movement_is_normalized_and_stale_input_stops() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let start = w.players[&1].character.point();
        w.message(1, ClientMessage::Input { dx: 1., dy: 1. });
        w.step();
        assert!((start.distance(w.players[&1].character.point()) - 5.2 * TICK).abs() < 1e-6);
        for _ in 0..20 {
            w.step();
        }
        let point = w.players[&1].character.point();
        for _ in 0..20 {
            w.step();
        }
        assert!(point.distance(w.players[&1].character.point()) < 1e-8);
        w.message(1, ClientMessage::Move { x: f64::NAN, y: 5. });
        assert!(w.players[&1].goal.is_none());
        w.message(1, ClientMessage::Input { dx: 100., dy: 0. });
        assert_eq!(w.players[&1].input.x, 0.);
    }
    #[test]
    fn shared_kill_rewards_once_and_slime_respawns() {
        let mut w = world();
        let _a = join(&mut w, 1, Class::Warrior);
        let _b = join(&mut w, 2, Class::Mage);
        w.hit_slime(0, 1, 1000., false);
        w.hit_slime(0, 2, 1000., false);
        assert!(w.slimes[0].dead);
        assert_eq!(w.players[&1].character.kills, 1);
        assert_eq!(w.players[&2].character.kills, 0);
        assert_eq!(w.drops.iter().filter(|d| d.item.is_none()).count(), 1);
        assert_eq!(
            w.drops
                .iter()
                .filter(|d| d
                    .item
                    .as_deref()
                    .is_some_and(|id| item(id).unwrap().kind == "material"))
                .count(),
            1
        );
        assert_eq!(w.players[&1].character.xp, 55);
        w.slimes[0].respawn = TICK;
        w.step();
        assert!(!w.slimes[0].dead);
        assert_eq!(w.slimes[0].hp, 60.);
    }
    #[test]
    fn attack_cooldown_range_equipment_and_respawn() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.start_attack(1);
        w.start_attack(1);
        assert_eq!(w.players[&1].cooldown, 0.55);
        let health: Vec<_> = w.slimes.iter().map(|s| s.hp).collect();
        w.strike(1);
        assert_eq!(w.slimes.iter().map(|s| s.hp).collect::<Vec<_>>(), health);
        assert_eq!(w.players[&1].character.look.stats(1), (30., 3.));
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.add_item("warrior_armor_azure_l10_purple", 1);
        c.add_item("warrior_weapon_royal_l10_purple", 1);
        // The purple level 10 armor and sword need level 10: owned but refused at level 1, worn at 20.
        let azure_armor = || ClientMessage::Equip {
            slots: Default::default(),
            armor: Some("azure_l10_purple".into()),
            weapon: None,
        };
        w.message(1, azure_armor());
        assert_eq!(w.players[&1].character.look.warrior_armor, "crimson");
        w.players.get_mut(&1).unwrap().character.level = 20;
        let (azure, royal) = (
            item("warrior_armor_azure_l10_purple").unwrap(),
            item("warrior_weapon_royal_l10_purple").unwrap(),
        );
        w.message(1, azure_armor());
        w.message(
            1,
            ClientMessage::Equip {
                slots: Default::default(),
                armor: None,
                weapon: Some("royal_l10_purple".into()),
            },
        );
        assert_eq!(
            w.players[&1].character.look.stats(20),
            (
                22. + 80. + royal.attack + azure.attack,
                azure.defense + royal.defense
            )
        );
        w.message(
            1,
            ClientMessage::Equip {
                slots: Default::default(),
                armor: Some("godmode".into()),
                weapon: Some("royal_l10_purple".into()),
            },
        );
        assert_eq!(
            w.players[&1].character.look.warrior_armor,
            "azure_l10_purple"
        );
        w.hurt_player(1, 1000., Point::default());
        assert_eq!(w.players[&1].character.hp, 0.);
        w.players.get_mut(&1).unwrap().dead_time = 3.2;
        w.step();
        assert_eq!(
            w.players[&1].character.hp,
            w.players[&1].character.max_hp(),
            "level 20 respawns at full health"
        );
        assert_eq!(
            w.players[&1].character.look.warrior_weapon,
            "royal_l10_purple"
        );
    }
    #[test]
    fn projectile_hits_nearest_and_dash_is_class_limited() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        for (i, s) in w.slimes.iter_mut().enumerate() {
            s.x = 50. + i as f64;
            s.y = 50.;
        }
        w.slimes[0].x = 36.3;
        w.slimes[0].y = 60.;
        w.slimes[1].x = 36.5;
        w.slimes[1].y = 60.;
        w.players.get_mut(&1).unwrap().face = Point { x: 1., y: 0. };
        // A strike can miss (10% hit chance loss), so fire until one bolt lands.
        for _ in 0..40 {
            w.strike(1);
            w.update_bolts();
            if w.slimes[0].hp < 60. {
                break;
            }
        }
        assert!(w.slimes[0].hp < 60.);
        assert_eq!(w.slimes[1].hp, 60.);
        assert!(w.bolts.is_empty());
        w.message(1, ClientMessage::Dash { dx: 1., dy: 0. });
        assert_eq!(w.players[&1].dash, 0.);
        let _b = join(&mut w, 2, Class::Assassin);
        w.message(2, ClientMessage::Dash { dx: 1., dy: 0. });
        assert_eq!(w.players[&2].dash, 0.18);
        w.message(2, ClientMessage::Dash { dx: 0., dy: 1. });
        assert_eq!(w.players[&2].dash_direction.x, 1.);
    }
    #[test]
    fn duplicate_character_session_is_rejected() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_string();
        let (tx, _rx2) = mpsc::channel(256);
        assert!(
            w.join(2, Some(token.clone()), None, tx)
                .unwrap_err()
                .contains("already online")
        );
        w.players.get_mut(&1).unwrap().character.gold = 42;
        w.leave(1);
        let (tx, _rx3) = mpsc::channel(256);
        w.join(3, Some(token), None, tx).unwrap();
        assert_eq!(w.players[&3].character.gold, 42);
    }

    #[test]
    fn account_characters_are_owned_resumed_and_capped_and_leave_no_key() {
        let mut w = world();
        let ann = w.store.sso_account("Ann").unwrap();
        let bob = w.store.sso_account("Bob").unwrap();
        let join_account =
            |w: &mut World, session, who: &str, character: Option<String>, look: Option<Look>| {
                let (tx, rx) = mpsc::channel(256);
                let result = w.join_as(
                    session,
                    Identity::Account {
                        id: who.to_owned(),
                        gm: false,
                        character,
                        look,
                    },
                    tx,
                );
                (result, rx)
            };
        let look = |name: &str| Look {
            name: name.into(),
            ..Look::default()
        };
        let (welcome, _rx) = join_account(&mut w, 1, &ann.id, None, Some(look("Annie")));
        let welcome = welcome.unwrap();
        assert!(
            welcome["token"].is_null(),
            "an account character is never issued a key"
        );
        let id = welcome["id"].as_str().unwrap().to_owned();
        assert_eq!(w.store.account_characters(&ann.id).unwrap().len(), 1);
        w.players.get_mut(&1).unwrap().character.gold = 77;
        w.leave(1);
        // Resumes by id for its own account, with what it earned...
        let (welcome, _rx) = join_account(&mut w, 2, &ann.id, Some(id.clone()), None);
        welcome.unwrap();
        assert_eq!(w.players[&2].character.gold, 77);
        // ...once at a time...
        let (again, _rx2) = join_account(&mut w, 3, &ann.id, Some(id.clone()), None);
        assert!(again.unwrap_err().contains("already online"));
        w.leave(2);
        // ...and never for another account, nor through the guest key path.
        let (stolen, _rx3) = join_account(&mut w, 4, &bob.id, Some(id.clone()), None);
        assert!(stolen.unwrap_err().contains("not on your account"));
        let (tx, _rx4) = mpsc::channel(256);
        assert!(w.join(5, Some("a".repeat(64)), None, tx).is_err());
        // A new character needs a valid look and room under the cap.
        let (nameless, _rx5) = join_account(&mut w, 6, &ann.id, None, None);
        assert!(nameless.unwrap_err().contains("Create a character"));
        for n in 1..MAX_ACCOUNT_CHARACTERS {
            let (made, _rx) = join_account(
                &mut w,
                10 + n as u64,
                &ann.id,
                None,
                Some(look(&format!("Alt{n}"))),
            );
            made.unwrap();
            w.leave(10 + n as u64);
        }
        assert_eq!(
            w.store.account_characters(&ann.id).unwrap().len(),
            MAX_ACCOUNT_CHARACTERS
        );
        let (full, _rx6) = join_account(&mut w, 30, &ann.id, None, Some(look("TooMany")));
        assert!(full.unwrap_err().contains("already has"));
        assert_eq!(
            w.store.account_characters(&ann.id).unwrap().len(),
            MAX_ACCOUNT_CHARACTERS
        );
        // Guests are unaffected: they still get a key and no owner.
        let (tx, _rx7) = mpsc::channel(256);
        let guest = w.join(40, None, Some(Look::default()), tx).unwrap();
        assert!(guest["token"].is_string());
        assert_eq!(w.store.account_characters(&bob.id).unwrap().len(), 0);
    }

    #[test]
    fn only_the_living_killer_collects_a_drop() {
        let mut w = world();
        let _a = join(&mut w, 1, Class::Mage);
        let _b = join(&mut w, 2, Class::Warrior);
        w.hit_slime(0, 1, 1000., false);
        let point = Point {
            x: w.drops[0].x,
            y: w.drops[0].y,
        };
        for d in &mut w.drops {
            d.t = 1.;
        }
        let other = &mut w.players.get_mut(&2).unwrap().character;
        other.x = point.x;
        other.y = point.y;
        w.update_drops();
        assert_eq!(w.players[&2].character.gold, 0);
        assert_eq!(w.drops.iter().filter(|d| d.item.is_none()).count(), 1);
        assert_eq!(
            w.drops
                .iter()
                .filter(|d| d
                    .item
                    .as_deref()
                    .is_some_and(|id| item(id).unwrap().kind == "material"))
                .count(),
            1
        );
        let owner = &mut w.players.get_mut(&1).unwrap().character;
        owner.x = point.x;
        owner.y = point.y;
        owner.hp = 0.;
        w.update_drops();
        assert_eq!(w.players[&1].character.gold, 0);
        w.players.get_mut(&1).unwrap().character.hp = 80.;
        let value = w.drops[0].value;
        w.update_drops();
        assert_eq!(w.players[&1].character.gold, value);
        assert!(w.drops.is_empty());
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 1);
        assert_eq!(w.players[&2].character.quantity("slime_gel"), 0);
        w.update_drops();
        assert_eq!(w.players[&1].character.gold, value);
    }

    // ---- skills ----
    /// Parks every enemy far away with huge health so a test places only the ones it needs.
    fn arena(w: &mut World, level: u32) -> Point {
        for (i, s) in w.slimes.iter_mut().enumerate() {
            s.x = 85. + (i % 8) as f64 * 1.5;
            s.y = 5. + (i / 8) as f64 * 1.5;
            s.hp = 1.0e6;
        }
        let p = w.players.get_mut(&1).unwrap();
        p.character.level = level;
        p.character.resource = Some(p.character.max_resource());
        p.character.attributes.accuracy = 20;
        p.face = Point { x: 1., y: 0. };
        p.character.point()
    }
    fn put(w: &mut World, i: usize, at: Point, dx: f64, dy: f64) {
        w.slimes[i].x = at.x + dx;
        w.slimes[i].y = at.y + dy;
        w.slimes[i].hp = 1.0e6;
    }
    fn hp_lost(w: &World, i: usize) -> bool {
        w.slimes[i].hp < 1.0e6
    }
    fn skill(w: &mut World, id: &str) {
        w.use_skill(1, id, Point { x: 1., y: 0. });
    }
    fn events(rx: &mut mpsc::Receiver<Value>, kind: &str) -> Vec<Value> {
        let mut found = vec![];
        while let Ok(v) = rx.try_recv() {
            if v["type"] == "event" && v["kind"] == kind {
                found.push(v);
            }
        }
        found
    }
    #[test]
    fn skills_unlock_by_level_and_a_locked_skill_costs_nothing() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let at = arena(&mut w, 1);
        put(&mut w, 0, at, 1., 0.);
        while rx.try_recv().is_ok() {}
        skill(&mut w, "cleave");
        let error = rx.try_recv().unwrap();
        assert_eq!(error["text"], "Cleave unlocks at level 2.");
        assert!(!hp_lost(&w, 0) && w.players[&1].skill_cd.is_empty());
        w.use_skill(1, "twinbolt", Point { x: 1., y: 0. });
        assert_eq!(rx.try_recv().unwrap()["type"], "error");
        w.players.get_mut(&1).unwrap().character.level = 2;
        skill(&mut w, "cleave");
        assert!(hp_lost(&w, 0));
        let left = w.players[&1].skill_cd["cleave"];
        assert!((left - 3. * w.players[&1].character.cooldown_multiplier()).abs() < 1e-9);
        assert_eq!(w.snapshot_for(0)["players"][0]["skillCd"]["cleave"], left);
        // On cooldown: a second cast changes nothing.
        let hp = w.slimes[0].hp;
        skill(&mut w, "cleave");
        assert_eq!(w.slimes[0].hp, hp);
        for _ in 0..61 {
            w.update_player(1);
        }
        assert!(w.players[&1].skill_cd.is_empty());
    }
    #[test]
    fn a_dead_player_and_a_dashing_player_cannot_cast() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let at = arena(&mut w, 20);
        put(&mut w, 0, at, 1., 0.);
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        skill(&mut w, "whirlwind");
        assert!(!hp_lost(&w, 0));
        let p = w.players.get_mut(&1).unwrap();
        p.character.hp = 50.;
        p.dash = 0.1;
        skill(&mut w, "whirlwind");
        assert!(!hp_lost(&w, 0) && w.players[&1].skill_cd.is_empty());
    }
    #[test]
    fn cone_hits_the_front_arc_and_nova_hits_everything_in_radius_only() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let at = arena(&mut w, 20);
        put(&mut w, 0, at, 1.2, 0.);
        put(&mut w, 1, at, 0., 1.2);
        put(&mut w, 2, at, -1.5, 0.);
        put(&mut w, 3, at, 4., 0.);
        skill(&mut w, "cleave");
        assert!(hp_lost(&w, 0) && hp_lost(&w, 1));
        assert!(!hp_lost(&w, 2) && !hp_lost(&w, 3));
        skill(&mut w, "whirlwind");
        assert!(hp_lost(&w, 2) && !hp_lost(&w, 3));
        skill(&mut w, "earthshatter");
        assert!(hp_lost(&w, 3));
    }
    #[test]
    fn skill_kills_grant_the_xp_and_a_level_up_names_the_skills_it_unlocks() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Mage);
        let at = arena(&mut w, 1);
        let need = w.players[&1].character.xp_need();
        w.players.get_mut(&1).unwrap().character.xp = need - 1;
        put(&mut w, 0, at, 1., 0.);
        w.slimes[0].hp = 1.;
        w.hit_slime(0, 1, 5., false);
        let ups = events(&mut rx, "levelup");
        assert_eq!(ups.len(), 1);
        assert_eq!(ups[0]["level"], 2);
        assert_eq!(ups[0]["unlocked"], json!(["twinbolt"]));
        assert_eq!(ups[0]["value"], 1.);
        // A multi-level jump lists every skill passed.
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 7;
        let id = w.players[&1].character.id.clone();
        w.level_up_event(&id, at, 4);
        let ups = events(&mut rx, "levelup");
        assert_eq!(
            ups.last().unwrap()["unlocked"],
            json!(["arcaneward", "fireball"])
        );
    }
    #[test]
    fn buffs_scale_damage_cut_incoming_damage_expire_and_clear_on_death() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        arena(&mut w, 20);
        w.players.get_mut(&1).unwrap().character.attributes.accuracy = 20;
        let plain: f64 = (0..200).map(|_| w.roll_damage(1, 1.).0).sum();
        skill(&mut w, "battlecry");
        assert_eq!(
            w.snapshot_for(0)["players"][0]["buffs"][0]["id"],
            "battlecry"
        );
        let buffed: f64 = (0..200).map(|_| w.roll_damage(1, 1.).0).sum();
        assert!(buffed > plain * 1.2, "{buffed} vs {plain}");
        // Incoming damage: 40 against the starting defence, with and without the wall.
        let hp = |w: &mut World, shield: bool| {
            let p = w.players.get_mut(&1).unwrap();
            p.character.hp = p.character.max_hp();
            p.last_hurt = -99.;
            p.buffs.clear();
            if shield {
                p.skill_cd.clear();
                skill(w, "shieldwall");
            }
            let before = w.players[&1].character.hp;
            w.hurt_player(1, 40., Point::default());
            before - w.players[&1].character.hp
        };
        let open = hp(&mut w, false);
        let walled = hp(&mut w, true);
        assert!(
            walled > 0. && (walled - (open * 0.5).round()).abs() <= 1.,
            "{walled} vs {open}"
        );
        for _ in 0..121 {
            w.update_player(1);
        }
        assert!(w.players[&1].buffs.is_empty());
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        skill(&mut w, "berserk");
        assert_eq!(w.players[&1].buff(BuffKind::Haste), 0.4);
        w.players.get_mut(&1).unwrap().last_hurt = -99.;
        w.hurt_player(1, 1.0e6, Point::default());
        assert!(w.players[&1].buffs.is_empty());
    }
    #[test]
    fn evasion_and_deadly_focus_raise_dodge_and_crit() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Assassin);
        arena(&mut w, 20);
        let base_dodge = w.players[&1].character.dodge_chance();
        skill(&mut w, "evasion");
        skill(&mut w, "deadlyfocus");
        let p = &w.players[&1];
        assert_eq!(p.buff(BuffKind::Dodge), 0.5);
        assert_eq!(p.buff(BuffKind::Crit), 0.4);
        assert!(base_dodge + p.buff(BuffKind::Dodge) <= 0.95 + base_dodge);
        // Recasting refreshes rather than stacks.
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        skill(&mut w, "evasion");
        assert_eq!(w.players[&1].buff(BuffKind::Dodge), 0.5);
    }
    #[test]
    fn healing_is_capped_and_lifesteal_returns_a_share_of_damage_dealt() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let at = arena(&mut w, 20);
        let max = w.players[&1].character.max_hp();
        w.players.get_mut(&1).unwrap().character.hp = 10.;
        skill(&mut w, "secondwind");
        assert_eq!(w.players[&1].character.hp, 10. + (max * 0.4).min(max - 10.));
        w.players.get_mut(&1).unwrap().character.hp = max - 1.;
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        skill(&mut w, "secondwind");
        assert_eq!(w.players[&1].character.hp, max);
        let beat = events(&mut rx, "skill");
        assert_eq!(beat.last().unwrap()["heal"], 1.);
        put(&mut w, 0, at, 1., 0.);
        w.players.get_mut(&1).unwrap().character.hp = 5.;
        skill(&mut w, "titanswrath");
        let dealt = 1.0e6 - w.slimes[0].hp;
        assert!(dealt > 0.);
        assert!((w.players[&1].character.hp - (5. + dealt * 0.25).min(max)).abs() < 1.);
    }
    #[test]
    fn dashes_hit_each_enemy_once_and_blink_only_moves() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Assassin);
        let at = arena(&mut w, 20);
        put(&mut w, 0, at, 2., 0.);
        w.use_skill(1, "lunge", Point { x: 1., y: 0. });
        let mut hits = 0;
        let mut last = 1.0e6;
        for _ in 0..8 {
            w.update_player(1);
            if w.slimes[0].hp < last {
                hits += 1;
                last = w.slimes[0].hp;
            }
        }
        assert_eq!(hits, 1, "one dash strikes an enemy once");
        assert!(
            w.players[&1].character.x > at.x + 1.5,
            "the lunge moved the player"
        );
        assert_eq!(w.players[&1].dash, 0.);
        let _b = join(&mut w, 2, Class::Mage);
        let (m, start) = (2, w.players[&2].character.point());
        w.players.get_mut(&2).unwrap().character.level = 10;
        w.use_skill(m, "blink", Point { x: 1., y: 0. });
        for _ in 0..4 {
            w.update_player(2);
        }
        let moved = w.players[&2].character.x - start.x;
        assert!(moved > 3., "blink travels {moved}");
        assert_eq!(w.players[&2].dash_mult, 0.);
        assert!(w.players[&2].attack == 0., "blink plays no attack");
    }
    #[test]
    fn volleys_fire_the_right_bolts_and_fireball_explodes_on_neighbours() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Mage);
        let at = arena(&mut w, 20);
        skill(&mut w, "twinbolt");
        assert_eq!(w.bolts.len(), 2);
        assert!((w.bolts[0].fy + w.bolts[1].fy).abs() < 1e-9 && w.bolts[0].fy != 0.);
        w.bolts.clear();
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        skill(&mut w, "barrage");
        assert_eq!(w.bolts.len(), 5);
        w.bolts.clear();
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        put(&mut w, 0, at, 3., 0.);
        put(&mut w, 1, at, 3., 1.5);
        put(&mut w, 2, at, 3., 6.);
        skill(&mut w, "fireball");
        for _ in 0..20 {
            w.update_bolts();
        }
        assert!(
            hp_lost(&w, 0) && hp_lost(&w, 1),
            "the blast hits the neighbour"
        );
        assert!(!hp_lost(&w, 2));
        assert!(w.bolts.is_empty());
    }
    #[test]
    fn knife_ring_goes_every_direction_and_each_knife_hits_alone() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Assassin);
        let at = arena(&mut w, 20);
        skill(&mut w, "knifering");
        assert_eq!(w.bolts.len(), 12);
        let sum: (f64, f64) = w
            .bolts
            .iter()
            .fold((0., 0.), |a, b| (a.0 + b.fx, a.1 + b.fy));
        assert!(
            sum.0.abs() < 1e-6 && sum.1.abs() < 1e-6,
            "evenly spread: {sum:?}"
        );
        put(&mut w, 0, at, 0., -3.);
        for _ in 0..20 {
            w.update_bolts();
        }
        assert!(hp_lost(&w, 0));
        assert!(w.slimes[0].hp > 1.0e6 - 1000., "only one knife reached it");
    }
    #[test]
    fn strike_skills_need_an_enemy_and_flurry_lands_every_hit() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Assassin);
        let at = arena(&mut w, 20);
        while rx.try_recv().is_ok() {}
        skill(&mut w, "flurry");
        assert_eq!(rx.try_recv().unwrap()["text"], "No enemy in range.");
        assert!(w.players[&1].skill_cd.is_empty(), "a fizzled cast is free");
        put(&mut w, 0, at, 1.5, 0.);
        skill(&mut w, "flurry");
        assert!(hp_lost(&w, 0));
        assert!(w.players[&1].skill_cd.contains_key("flurry"));
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        let mut rx2 = {
            let (tx, rx) = mpsc::channel(256);
            w.players.get_mut(&1).unwrap().peer = tx;
            rx
        };
        skill(&mut w, "flurry");
        let mut count = 0;
        let mut skill_points = 0;
        while let Ok(v) = rx2.try_recv() {
            if v["kind"] == "hit" || v["kind"] == "miss" {
                count += 1;
            }
            if v["kind"] == "skill" {
                skill_points = v["points"].as_array().unwrap().len();
            }
        }
        assert_eq!(count, 4);
        assert_eq!(skill_points, 4);
    }
    #[test]
    fn chain_lightning_jumps_to_distinct_enemies_and_meteor_lands_on_the_target() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Mage);
        let at = arena(&mut w, 20);
        for n in 0..6 {
            put(&mut w, n, at, 2. + n as f64 * 2., 0.);
        }
        skill(&mut w, "chainlightning");
        let lost = (0..6).filter(|&n| hp_lost(&w, n)).count();
        assert_eq!(lost, 5, "five targets, never the same one twice");
        let cast = events(&mut rx, "skill");
        assert_eq!(cast.last().unwrap()["points"].as_array().unwrap().len(), 5);
        // Meteor: centred on the selected enemy, hitting its neighbours but not distant ones.
        for n in 0..6 {
            put(&mut w, n, at, 40., 0.);
        }
        put(&mut w, 0, at, 4., 3.);
        put(&mut w, 1, at, 5., 3.);
        put(&mut w, 2, at, 4., -3.);
        w.players.get_mut(&1).unwrap().target = Some(0);
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        skill(&mut w, "meteor");
        assert!(hp_lost(&w, 0) && hp_lost(&w, 1) && !hp_lost(&w, 2));
        // With no target it lands on the ground ahead.
        for n in 0..6 {
            put(&mut w, n, at, 40., 0.);
        }
        put(&mut w, 3, at, 4.5, 0.);
        w.players.get_mut(&1).unwrap().target = None;
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        skill(&mut w, "meteor");
        assert!(hp_lost(&w, 3));
    }
    #[test]
    fn skills_are_zone_local_and_use_only_the_players_own_class_table() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let at = arena(&mut w, 20);
        put(&mut w, 0, at, 1., 0.);
        w.slimes[0].zone = 1;
        skill(&mut w, "whirlwind");
        assert!(!hp_lost(&w, 0), "enemies in another zone are untouched");
        w.use_skill(1, "meteor", Point { x: 1., y: 0. });
        assert!(
            w.players[&1].skill_cd.contains_key("whirlwind")
                && !w.players[&1].skill_cd.contains_key("meteor")
        );
    }
    #[test]
    fn start_level_applies_only_to_new_characters_and_defaults_to_one() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        assert_eq!(w.players[&1].character.level, 1);
        let token = welcome["token"].as_str().unwrap().to_string();
        w.leave(1);
        w.start_level = 9;
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, Some(token), None, tx).unwrap();
        assert_eq!(
            w.players[&1].character.level, 1,
            "a saved character is not boosted"
        );
        let (tx, _rx) = mpsc::channel(256);
        w.join(
            2,
            None,
            Some(Look {
                name: "Other".into(),
                ..Look::default()
            }),
            tx,
        )
        .unwrap();
        let c = &w.players[&2].character;
        assert_eq!((c.level, c.hp), (9, c.max_hp()));
    }

    fn debug_world() -> (World, mpsc::Receiver<Value>) {
        let mut w = world();
        w.test_commands = true;
        let rx = join(&mut w, 1, Class::Warrior);
        (w, rx)
    }
    fn dbg(w: &mut World, command: DebugCommand) -> Result<Value, String> {
        w.run_debug(1, command)
    }
    fn ch(w: &World) -> &Character {
        &w.players[&1].character
    }
    fn packets(rx: &mut mpsc::Receiver<Value>, kind: &str) -> Vec<Value> {
        let mut found = vec![];
        while let Ok(v) = rx.try_recv() {
            if v["type"] == kind {
                found.push(v);
            }
        }
        found
    }

    #[test]
    fn combat_events_name_the_enemy_and_the_skill_for_the_system_log() {
        let (mut w, mut rx) = debug_world();
        let kind = w.slimes[0].kind.clone();
        let level = w.slimes[0].level;
        w.slimes[0].zone = w.players[&1].character.zone;
        w.slimes[0].dead = false;
        w.slimes[0].hp = w.slimes[0].max_hp;
        w.cur_skill = "cleave".into();
        w.hit_slime(0, 1, 3., false);
        w.cur_skill.clear();
        let point = w.players[&1].character.point();
        w.time = 10.;
        w.players.get_mut(&1).unwrap().god = false;
        w.hurt_player_by(1, 20., point, &kind, level);
        let events = packets(&mut rx, "event");
        let hit = events.iter().find(|e| e["kind"] == "hit").unwrap();
        assert_eq!(hit["enemy"], kind.as_str());
        assert_eq!(hit["level"], level);
        assert_eq!(hit["skill"], "cleave");
        assert_eq!(hit["killed"], false);
        let hurt = events.iter().find(|e| e["kind"] == "hurt").unwrap();
        assert_eq!(hurt["enemy"], kind.as_str());
        assert_eq!(hurt["level"], level);
        w.slimes[0].hp = 1.;
        w.hit_slime(0, 1, 50., false);
        let die = packets(&mut rx, "event")
            .into_iter()
            .find(|e| e["kind"] == "slimeDie")
            .unwrap();
        assert_eq!(die["enemy"], kind.as_str());
        assert!(die["xp"].as_u64().unwrap() > 0);
    }

    #[test]
    fn debug_commands_are_refused_unless_the_server_enables_them() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        assert!(!w.test_commands, "off by default");
        w.message(
            1,
            serde_json::from_str(
                r#"{"type":"debug","ref":7,"command":{"op":"set_level","level":20}}"#,
            )
            .unwrap(),
        );
        assert_eq!(ch(&w).level, 1);
        let reply = packets(&mut rx, "debug").pop().unwrap();
        assert_eq!(
            (reply["ok"].clone(), reply["ref"].clone()),
            (json!(false), json!(7))
        );
        w.test_commands = true;
        w.message(
            1,
            serde_json::from_str(
                r#"{"type":"debug","ref":8,"command":{"op":"set_level","level":20}}"#,
            )
            .unwrap(),
        );
        assert_eq!(ch(&w).level, 20);
        let reply = packets(&mut rx, "debug").pop().unwrap();
        assert_eq!(
            (reply["ok"].clone(), reply["ref"].clone()),
            (json!(true), json!(8))
        );
        // Unknown operations and fields never parse.
        assert!(
            serde_json::from_str::<ClientMessage>(
                r#"{"type":"debug","command":{"op":"set_level","level":2,"hp":9}}"#
            )
            .is_err()
        );
        assert!(
            serde_json::from_str::<ClientMessage>(r#"{"type":"debug","command":{"op":"nuke"}}"#)
                .is_err()
        );
    }

    #[test]
    fn set_level_restores_health_announces_unlocks_and_lowering_resets_trained_stats() {
        let (mut w, mut rx) = debug_world();
        let result = dbg(&mut w, DebugCommand::SetLevel { level: 20 }).unwrap();
        let c = ch(&w);
        assert_eq!((c.level, c.xp, c.hp), (20, 0, c.max_hp()));
        assert_eq!(result["unlocked"].as_array().unwrap().len(), 10);
        let up = packets(&mut rx, "event")
            .into_iter()
            .find(|e| e["kind"] == "levelup")
            .unwrap();
        assert_eq!(up["level"], 20);
        w.players.get_mut(&1).unwrap().character.attributes.strength = 5;
        dbg(&mut w, DebugCommand::SetLevel { level: 3 }).unwrap();
        assert_eq!(ch(&w).attributes, Attributes::default());
        assert_eq!(ch(&w).stat_points(), 6);
        assert!(dbg(&mut w, DebugCommand::SetLevel { level: 0 }).is_err());
        assert!(dbg(&mut w, DebugCommand::SetLevel { level: 101 }).is_err());
        dbg(&mut w, DebugCommand::GiveXp { amount: 2_000 }).unwrap();
        assert!(ch(&w).level > 3, "xp still levels through grant_xp");
    }

    #[test]
    fn teleport_collides_changes_zone_and_survives_a_save() {
        let mut w = world();
        w.test_commands = true;
        let (tx, _rx) = mpsc::channel(256);
        let token = w.join(1, None, Some(Look::default()), tx).unwrap()["token"]
            .as_str()
            .unwrap()
            .to_owned();
        let near = w.maps[1].spawn;
        let result = dbg(
            &mut w,
            DebugCommand::Teleport {
                zone: 1,
                x: near.x,
                y: near.y,
            },
        )
        .unwrap();
        assert_eq!(result["zone"], 1);
        assert_eq!(ch(&w).zone, 1);
        // An obstacle centre is pushed out, a far coordinate is clamped inside the map.
        let o = w.maps[0].objects[0].clone();
        dbg(
            &mut w,
            DebugCommand::Teleport {
                zone: 0,
                x: o.x,
                y: o.y,
            },
        )
        .unwrap();
        let mut again = ch(&w).point();
        w.maps[0].collide(&mut again, PLAYER_RADIUS);
        assert!(again.distance(ch(&w).point()) < 1e-6);
        dbg(
            &mut w,
            DebugCommand::Teleport {
                zone: 0,
                x: 9_999.,
                y: -9_999.,
            },
        )
        .unwrap();
        let size = w.maps[0].size as f64;
        assert!(ch(&w).x <= size - 0.7 && ch(&w).y >= 0.7);
        assert!(
            dbg(
                &mut w,
                DebugCommand::Teleport {
                    zone: 99,
                    x: 5.,
                    y: 5.
                }
            )
            .is_err()
        );
        assert!(
            dbg(
                &mut w,
                DebugCommand::Teleport {
                    zone: 0,
                    x: f64::NAN,
                    y: 1.
                }
            )
            .is_err()
        );
        dbg(
            &mut w,
            DebugCommand::Teleport {
                zone: 1,
                x: near.x,
                y: near.y,
            },
        )
        .unwrap();
        w.leave(1);
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, Some(token), None, tx).unwrap();
        assert_eq!(ch(&w).zone, 1, "teleport saves the character");
    }

    #[test]
    fn give_and_take_items_respect_capacity_equipment_and_bags() {
        let (mut w, _rx) = debug_world();
        dbg(
            &mut w,
            DebugCommand::GiveItem {
                item: "slime_gel".into(),
                quantity: 30,
                force: false,
            },
        )
        .unwrap();
        assert_eq!(ch(&w).quantity("slime_gel"), 30);
        assert!(
            dbg(
                &mut w,
                DebugCommand::GiveItem {
                    item: "nope".into(),
                    quantity: 1,
                    force: false
                }
            )
            .is_err()
        );
        assert!(
            dbg(
                &mut w,
                DebugCommand::GiveItem {
                    item: "slime_gel".into(),
                    quantity: 0,
                    force: false
                }
            )
            .is_err()
        );
        // Fill every cell: more distinct items than the 16-cell backpack exist, so the last ones are refused.
        let all: Vec<String> = ITEMS
            .iter()
            .filter(|i| i.kind != "bag")
            .map(|i| i.id.clone())
            .collect();
        for id in &all {
            let _ = dbg(
                &mut w,
                DebugCommand::GiveItem {
                    item: id.clone(),
                    quantity: 1,
                    force: false,
                },
            );
        }
        assert_eq!(
            ch(&w).bag_used(),
            ch(&w).bag_capacity(),
            "bags fill to capacity and stop"
        );
        let missing = all
            .iter()
            .find(|id| ch(&w).quantity(id) == 0)
            .unwrap()
            .clone();
        assert!(
            dbg(
                &mut w,
                DebugCommand::GiveItem {
                    item: missing.clone(),
                    quantity: 1,
                    force: false
                }
            )
            .is_err()
        );
        // A fitted bag is a bag, not a stack, adds its cells even when the pack is full, and stops at four.
        dbg(
            &mut w,
            DebugCommand::GiveItem {
                item: "linen_satchel".into(),
                quantity: 1,
                force: false,
            },
        )
        .unwrap();
        assert_eq!(ch(&w).bag_capacity(), 22);
        dbg(
            &mut w,
            DebugCommand::GiveItem {
                item: missing.clone(),
                quantity: 1,
                force: false,
            },
        )
        .unwrap();
        for _ in 0..3 {
            dbg(
                &mut w,
                DebugCommand::GiveItem {
                    item: "linen_satchel".into(),
                    quantity: 1,
                    force: false,
                },
            )
            .unwrap();
        }
        assert_eq!(ch(&w).bag_capacity(), 16 + 4 * 6);
        assert!(
            dbg(
                &mut w,
                DebugCommand::GiveItem {
                    item: "linen_satchel".into(),
                    quantity: 1,
                    force: false
                }
            )
            .is_err()
        );
        // Force ignores capacity: with every cell used, a stack of a new item still lands.
        let stuffed = ITEMS
            .iter()
            .find(|i| i.kind == "material")
            .unwrap()
            .id
            .clone();
        dbg(
            &mut w,
            DebugCommand::GiveItem {
                item: stuffed.clone(),
                quantity: 5,
                force: true,
            },
        )
        .unwrap();
        assert!(ch(&w).quantity(&stuffed) >= 5);
        // A bag cannot be taken while its cells hold items.
        for id in &all {
            let _ = dbg(
                &mut w,
                DebugCommand::GiveItem {
                    item: id.clone(),
                    quantity: 1,
                    force: false,
                },
            );
        }
        dbg(
            &mut w,
            DebugCommand::TakeItem {
                item: "linen_satchel".into(),
                quantity: 1,
            },
        )
        .ok();
        assert!(ch(&w).bag_used() <= ch(&w).bag_capacity());
        // Worn copies cannot be taken; spare ones can.
        let worn = ch(&w).look.warrior_weapon.clone();
        let worn_id = equipment(Class::Warrior, "weapon", &worn)
            .unwrap()
            .id
            .clone();
        let owned = ch(&w).quantity(&worn_id);
        assert!(
            dbg(
                &mut w,
                DebugCommand::TakeItem {
                    item: worn_id.clone(),
                    quantity: owned
                }
            )
            .is_err(),
            "the worn copy stays"
        );
        dbg(
            &mut w,
            DebugCommand::TakeItem {
                item: worn_id.clone(),
                quantity: owned - 1,
            },
        )
        .unwrap();
        assert_eq!(ch(&w).quantity(&worn_id), 1);
        let gel = ch(&w).quantity("slime_gel");
        dbg(
            &mut w,
            DebugCommand::TakeItem {
                item: "slime_gel".into(),
                quantity: gel,
            },
        )
        .unwrap();
        assert_eq!(ch(&w).quantity("slime_gel"), 0);
        assert!(ch(&w).inventory.iter().all(|s| s.quantity > 0));
    }

    #[test]
    fn dropped_items_are_collected_through_the_ordinary_pickup() {
        let (mut w, _rx) = debug_world();
        dbg(
            &mut w,
            DebugCommand::DropItem {
                item: "royal_jelly".into(),
                quantity: 2,
            },
        )
        .unwrap();
        assert_eq!(w.drops.len(), 1);
        for _ in 0..60 {
            w.step();
        }
        assert_eq!(ch(&w).quantity("royal_jelly"), 2);
    }

    #[test]
    fn finishing_a_hand_in_quest_by_shortcut_puts_the_items_in_the_bag_and_takes_them_again() {
        let (mut w, _rx) = debug_world();
        let result = dbg(
            &mut w,
            DebugCommand::Quest {
                id: "city_tribute".into(),
                action: QuestDebug::Finish,
            },
        )
        .unwrap();
        let claimed: Vec<_> = result["claimed"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_str().unwrap())
            .collect();
        assert_eq!(
            claimed,
            ["city_welcome", "city_archive", "city_stone", "city_tribute"]
        );
        let gold: u32 = w.maps[CITY]
            .quests
            .iter()
            .filter(|q| claimed.contains(&q.id.as_str()))
            .map(|q| q.reward_gold)
            .sum();
        assert_eq!(ch(&w).gold, gold);
        assert!(
            ch(&w)
                .inventory
                .iter()
                .all(|s| item(&s.item).unwrap().kind != "material"),
            "every handed-in item was taken: {:?}",
            ch(&w).inventory
        );
    }

    #[test]
    fn finishing_a_quest_walks_its_prerequisites_and_pays_each_reward_once() {
        let (mut w, _rx) = debug_world();
        let chain: Vec<_> = w.maps[0]
            .quests
            .iter()
            .map(|q| (q.id.clone(), q.requires.clone()))
            .collect();
        let (deep, _) = chain.iter().find(|(_, r)| r.is_some()).unwrap().clone();
        let result = dbg(
            &mut w,
            DebugCommand::Quest {
                id: deep.clone(),
                action: QuestDebug::Finish,
            },
        )
        .unwrap();
        let claimed: Vec<_> = result["claimed"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_str().unwrap().to_owned())
            .collect();
        assert!(
            claimed.len() >= 2 && claimed.last() == Some(&deep),
            "prerequisites first, then the quest"
        );
        let reward_gold: u32 = w.maps[0]
            .quests
            .iter()
            .filter(|q| claimed.contains(&q.id))
            .map(|q| q.reward_gold)
            .sum();
        assert_eq!(ch(&w).gold, reward_gold);
        for id in &claimed {
            let q = ch(&w).quests.iter().find(|q| &q.id == id).unwrap();
            assert!(q.claimed && q.completions == 1);
        }
        // Finishing a one-time quest twice pays nothing more.
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: deep.clone(),
                action: QuestDebug::Finish,
            },
        )
        .unwrap();
        assert_eq!(ch(&w).gold, reward_gold);
        // A repeatable quest pays again on every finish.
        let repeat = w.maps[0]
            .quests
            .iter()
            .find(|q| q.repeatable)
            .unwrap()
            .id
            .clone();
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: repeat.clone(),
                action: QuestDebug::Finish,
            },
        )
        .unwrap();
        let once = ch(&w)
            .quests
            .iter()
            .find(|q| q.id == repeat)
            .unwrap()
            .completions;
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: repeat.clone(),
                action: QuestDebug::Finish,
            },
        )
        .unwrap();
        assert_eq!(
            ch(&w)
                .quests
                .iter()
                .find(|q| q.id == repeat)
                .unwrap()
                .completions,
            once + 1
        );
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: repeat.clone(),
                action: QuestDebug::Reset,
            },
        )
        .unwrap();
        assert!(ch(&w).quests.iter().all(|q| q.id != repeat));
        assert!(
            dbg(
                &mut w,
                DebugCommand::Quest {
                    id: "nope".into(),
                    action: QuestDebug::Finish
                }
            )
            .is_err()
        );
    }

    #[test]
    fn quest_steps_follow_the_real_rules_one_at_a_time() {
        let (mut w, _rx) = debug_world();
        let (id, needs) = w.maps[0]
            .quests
            .iter()
            .find(|q| q.requires.is_some())
            .map(|q| (q.id.clone(), q.requires.clone().unwrap()))
            .unwrap();
        assert!(
            dbg(
                &mut w,
                DebugCommand::Quest {
                    id: id.clone(),
                    action: QuestDebug::Accept
                }
            )
            .is_err(),
            "accept still needs the prerequisite"
        );
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: needs.clone(),
                action: QuestDebug::Accept,
            },
        )
        .unwrap();
        assert!(
            dbg(
                &mut w,
                DebugCommand::Quest {
                    id: needs.clone(),
                    action: QuestDebug::Claim
                }
            )
            .is_err(),
            "claim needs filled objectives"
        );
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: needs.clone(),
                action: QuestDebug::Complete,
            },
        )
        .unwrap();
        let q = ch(&w).quests.iter().find(|q| q.id == needs).unwrap();
        assert!(!q.claimed);
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: needs.clone(),
                action: QuestDebug::Claim,
            },
        )
        .unwrap();
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: id.clone(),
                action: QuestDebug::Accept,
            },
        )
        .unwrap();
    }

    #[test]
    fn kill_enemy_uses_the_real_kill_path_for_xp_quests_and_loot() {
        let (mut w, _rx) = debug_world();
        let target = w.slimes.iter().find(|s| s.kind == "green").unwrap().id;
        let zone = w.slimes[target].zone;
        let at = w.slimes[target].point();
        dbg(
            &mut w,
            DebugCommand::Teleport {
                zone,
                x: at.x + 3.,
                y: at.y,
            },
        )
        .unwrap();
        let bounty = w.maps[0]
            .quests
            .iter()
            .find(|q| q.objectives.iter().any(|o| o.kind == "kill"))
            .unwrap()
            .id
            .clone();
        dbg(
            &mut w,
            DebugCommand::Quest {
                id: bounty.clone(),
                action: QuestDebug::Accept,
            },
        )
        .ok();
        let (xp, kills) = (ch(&w).xp, ch(&w).kills);
        dbg(&mut w, DebugCommand::KillEnemy { id: target }).unwrap();
        assert!(w.slimes[target].dead);
        assert_eq!(ch(&w).kills, kills + 1);
        assert!(ch(&w).xp > xp);
        assert!(
            w.drops
                .iter()
                .any(|d| d.item.as_deref() == Some("slime_gel")),
            "material drops for the killer"
        );
        assert!(
            dbg(&mut w, DebugCommand::KillEnemy { id: target }).is_err(),
            "already dead"
        );
        assert!(dbg(&mut w, DebugCommand::KillEnemy { id: 99_999 }).is_err());
        let far = w.slimes.iter().find(|s| s.zone == 1).unwrap().id;
        assert!(
            dbg(&mut w, DebugCommand::KillEnemy { id: far }).is_err(),
            "other zones are out of reach"
        );
        dbg(&mut w, DebugCommand::RespawnEnemy { id: target }).unwrap();
        w.step();
        assert!(!w.slimes[target].dead);
        assert!(
            dbg(&mut w, DebugCommand::RespawnEnemy { id: target }).is_err(),
            "alive already"
        );
    }

    #[test]
    fn spawn_enemy_puts_a_fighting_enemy_where_asked_in_the_players_zone() {
        let (mut w, _rx) = debug_world();
        let here = w.players[&1].character.point();
        let spot = Point {
            x: here.x + 4.,
            y: here.y,
        };
        let spawned = dbg(
            &mut w,
            DebugCommand::SpawnEnemy {
                kind: "yellow".into(),
                x: spot.x,
                y: spot.y,
                level: Some(9),
            },
        )
        .unwrap();
        let id = spawned["id"].as_u64().unwrap() as usize;
        let e = &w.slimes[id];
        assert_eq!(
            (e.kind.as_str(), e.level, e.dead, e.zone),
            ("yellow", 9, false, w.players[&1].character.zone)
        );
        assert!(
            e.point().distance(spot) < 1.5,
            "lands on the spot or the nearest free ground"
        );
        assert_eq!(
            e.hp,
            Slime::with_level(
                id,
                &SlimeSpawn {
                    ambush: None,
                    x: 0.,
                    y: 0.,
                    kind: "yellow".into(),
                    zone: 0
                },
                9
            )
            .hp
        );
        assert!((spawned["x"].as_f64().unwrap() - e.x).abs() < 1e-9);
        assert!(
            w.players[&1].character.point().distance(e.point()) >= 1.,
            "never on top of the player"
        );
        // The default level is the kind's own, with no random spread.
        let again = dbg(
            &mut w,
            DebugCommand::SpawnEnemy {
                kind: "yellow".into(),
                x: spot.x,
                y: spot.y + 3.,
                level: None,
            },
        )
        .unwrap();
        assert_eq!(again["level"], Slime::default_level("yellow"));
        // It is an ordinary enemy: the real kill path pays out.
        let (xp, kills) = (ch(&w).xp, ch(&w).kills);
        dbg(
            &mut w,
            DebugCommand::KillEnemy {
                id: again["id"].as_u64().unwrap() as usize,
            },
        )
        .unwrap();
        assert_eq!(ch(&w).kills, kills + 1);
        assert!(ch(&w).xp > xp);
        // A dead slot is reused before a living enemy is moved.
        let dead = w
            .slimes
            .iter()
            .find(|s| s.dead && s.kind == "yellow")
            .unwrap()
            .id;
        let reuse = dbg(
            &mut w,
            DebugCommand::SpawnEnemy {
                kind: "yellow".into(),
                x: spot.x,
                y: spot.y + 3.,
                level: None,
            },
        )
        .unwrap();
        assert_eq!(reuse["id"], dead);
    }

    #[test]
    fn spawn_enemy_refuses_kings_unknown_kinds_bad_levels_and_numbers() {
        let (mut w, _rx) = debug_world();
        let bad = |kind: &str, x: f64, level: Option<u32>| DebugCommand::SpawnEnemy {
            kind: kind.into(),
            x,
            y: 40.,
            level,
        };
        assert!(
            dbg(&mut w, bad("big", 40., None))
                .unwrap_err()
                .contains("summon_king")
        );
        assert!(
            dbg(&mut w, bad("dragon", 40., None))
                .unwrap_err()
                .contains("No enemy of that kind")
        );
        assert!(dbg(&mut w, bad("green", f64::NAN, None)).is_err());
        assert!(dbg(&mut w, bad("green", f64::INFINITY, None)).is_err());
        assert!(dbg(&mut w, bad("green", 40., Some(0))).is_err());
        assert!(dbg(&mut w, bad("green", 40., Some(101))).is_err());
        // Disabled servers refuse it like every other shortcut.
        w.test_commands = false;
        let (tx, mut rx) = mpsc::channel(8);
        w.players.get_mut(&1).unwrap().peer = tx;
        w.debug(1, Some(7), bad("green", 40., None));
        assert_eq!(rx.try_recv().unwrap()["ok"], false);
    }

    #[test]
    fn a_spawned_enemy_never_lands_in_the_city_or_inside_an_obstacle() {
        let (mut w, _rx) = debug_world();
        let city = w.maps[0]
            .city
            .as_ref()
            .expect("the meadow has a city")
            .clone();
        let centre = Point {
            x: (city.x0 + city.x1) / 2.,
            y: (city.y0 + city.y1) / 2.,
        };
        let spawned = dbg(
            &mut w,
            DebugCommand::SpawnEnemy {
                kind: "green".into(),
                x: centre.x,
                y: centre.y,
                level: None,
            },
        )
        .unwrap();
        let at = Point {
            x: spawned["x"].as_f64().unwrap(),
            y: spawned["y"].as_f64().unwrap(),
        };
        assert!(!w.maps[0].in_city(at), "enemies stay out of the sanctuary");
        let (ox, oy) = (w.maps[0].objects[0].x, w.maps[0].objects[0].y);
        let inside = dbg(
            &mut w,
            DebugCommand::SpawnEnemy {
                kind: "green".into(),
                x: ox,
                y: oy,
                level: None,
            },
        )
        .unwrap();
        let mut moved = Point {
            x: inside["x"].as_f64().unwrap(),
            y: inside["y"].as_f64().unwrap(),
        };
        let before = moved;
        w.maps[0].collide(&mut moved, 0.3);
        assert!(moved.distance(before) < 1e-6, "not inside a tree or a wall");
    }

    #[test]
    fn king_can_be_summoned_once_and_never_respawned_by_id() {
        let (mut w, _rx) = debug_world();
        let king = w.slimes.iter().find(|s| s.kind == "big").unwrap().id;
        assert!(dbg(&mut w, DebugCommand::RespawnEnemy { id: king }).is_err());
        dbg(&mut w, DebugCommand::SummonKing).unwrap();
        w.step();
        assert_eq!(
            w.slimes
                .iter()
                .filter(|s| s.kind == "big" && !s.dead)
                .count(),
            1
        );
        assert!(dbg(&mut w, DebugCommand::SummonKing).is_err());
    }

    fn join_gm(
        w: &mut World,
        session: u64,
        account: &crate::store::Account,
        name: &str,
    ) -> Result<(), String> {
        let (tx, rx) = mpsc::channel(256);
        std::mem::forget(rx);
        w.join_as(
            session,
            Identity::Account {
                id: account.id.clone(),
                gm: account.is_gm(),
                character: None,
                look: Some(Look {
                    name: name.into(),
                    class: Class::Mage,
                    gender: Gender::Female,
                    ..Look::default()
                }),
            },
            tx,
        )
        .map(|_| ())
    }

    #[test]
    fn only_the_sso_login_sork_is_a_game_master() {
        let w = world();
        assert!(w.store.sso_account("Sork").unwrap().is_gm());
        assert!(w.store.sso_account("sork").unwrap().is_gm());
        assert!(!w.store.sso_account("Ann").unwrap().is_gm());
        let game = w.store.create_account("Sork", "x").unwrap().unwrap();
        assert!(
            !game.is_gm(),
            "a game account may pick any free name but gets nothing"
        );
    }

    #[test]
    fn the_gm_character_is_an_extra_slot_built_by_the_server() {
        let mut w = world();
        let sork = w.store.sso_account("Sork").unwrap();
        // Five ordinary characters fill the ordinary slots; the sixth is the administrator.
        for n in 0..MAX_ACCOUNT_CHARACTERS {
            join_gm(&mut w, 1, &sork, &format!("Hero{n}")).unwrap();
            w.leave(1);
        }
        assert!(
            join_gm(&mut w, 1, &sork, "Hero9").is_err(),
            "the ordinary cap still holds"
        );
        // Whatever class and body the client asks for, the server builds the golden male Warrior.
        join_gm(&mut w, 1, &sork, GM_NAME).unwrap();
        let c = &w.players[&1].character;
        assert!(c.gm);
        assert_eq!(c.look.name, "[GM]Sork");
        assert_eq!(
            (c.look.class, c.look.gender),
            (Class::Warrior, Gender::Male)
        );
        assert_eq!(
            (
                c.look.warrior_armor.as_str(),
                c.look.warrior_weapon.as_str(),
                c.look.head.as_str()
            ),
            ("gm", "gm", "gm")
        );
        for id in GM_GEAR {
            assert_eq!(c.quantity(id), 1, "{id}");
        }
        assert!(c.bag_used() <= c.bag_capacity());
        assert_eq!(w.store.account_characters(&sork.id).unwrap().len(), 6);
        assert_eq!(w.store.account_character_count(&sork.id).unwrap(), 5);
        w.leave(1);
        assert!(
            join_gm(&mut w, 1, &sork, GM_NAME).is_err(),
            "only one administrator character"
        );
        // The stored character comes back as the administrator.
        let entry = w.store.account_characters(&sork.id).unwrap().pop().unwrap();
        assert!(entry.gm);
    }

    #[test]
    fn nobody_else_can_take_a_gm_name_or_the_golden_gear() {
        let mut w = world();
        let ann = w.store.sso_account("Ann").unwrap();
        let game = w.store.create_account("Sork", "x").unwrap().unwrap();
        for who in [&ann, &game] {
            assert!(join_gm(&mut w, 1, who, GM_NAME).is_err());
            assert!(join_gm(&mut w, 1, who, "[gm]Ann").is_err());
            assert!(join_gm(&mut w, 1, who, "Ann [GM]").is_err());
        }
        let sork = w.store.sso_account("Sork").unwrap();
        assert!(
            join_gm(&mut w, 1, &sork, "[GM]Other").is_err(),
            "even Sork gets only [GM]Sork"
        );
        let (tx, _rx) = mpsc::channel(8);
        let look = Look {
            name: "[GM]Guest".into(),
            ..Look::default()
        };
        assert!(w.join(2, None, Some(look), tx).is_err(), "guests too");
        // A look that asks for the gear in its draft is reset to the starters.
        let (tx, _rx) = mpsc::channel(8);
        let look = Look {
            warrior_armor: "gm".into(),
            warrior_weapon: "gm".into(),
            ..Look::default()
        };
        w.join(3, None, Some(look), tx).unwrap();
        let c = &w.players[&3].character;
        assert!(!c.gm);
        assert_eq!(
            (
                c.look.warrior_armor.as_str(),
                c.look.warrior_weapon.as_str()
            ),
            ("crimson", "sword")
        );
        let mut c = c.clone();
        assert!(
            c.equip_owned("gm", "gm").is_err(),
            "not owned, so not wearable"
        );
        c.add_item("warrior_weapon_gm", 1);
        assert!(c.sell_item("warrior_weapon_gm", 1).is_err());
    }

    #[test]
    fn a_game_master_runs_the_debug_commands_on_a_public_server_and_nobody_else_does() {
        let mut w = world();
        assert!(!w.test_commands);
        let sork = w.store.sso_account("Sork").unwrap();
        join_gm(&mut w, 1, &sork, GM_NAME).unwrap();
        let _ = join(&mut w, 2, Class::Warrior);
        let (tx, mut gm_rx) = mpsc::channel(64);
        w.players.get_mut(&1).unwrap().peer = tx;
        let run = |w: &mut World, session: u64, text: &str| {
            w.message(
                session,
                serde_json::from_str(&format!(r#"{{"type":"debug","ref":1,"command":{text}}}"#))
                    .unwrap(),
            );
        };
        run(&mut w, 1, r#"{"op":"set_level","level":30}"#);
        assert_eq!(w.players[&1].character.level, 30);
        assert_eq!(packets(&mut gm_rx, "debug").pop().unwrap()["ok"], true);
        run(
            &mut w,
            1,
            r#"{"op":"give_item","item":"slime_gel","quantity":3}"#,
        );
        assert_eq!(w.players[&1].character.quantity("slime_gel"), 3);
        run(&mut w, 1, r#"{"op":"teleport","zone":1,"x":40.0,"y":40.0}"#);
        assert_eq!(w.players[&1].character.zone, 1);
        // Another player is refused every one of them.
        run(&mut w, 2, r#"{"op":"set_level","level":30}"#);
        assert_eq!(w.players[&2].character.level, 1);
        // God mode is personal: the world flag stays off and the other player still takes damage.
        run(&mut w, 1, r#"{"op":"set_god_mode","enabled":true}"#);
        assert!(w.players[&1].god && !w.god_mode && !w.players[&2].god);
        assert_eq!(w.players[&1].snapshot()["god"], true);
        assert_eq!(w.players[&1].snapshot()["gm"], true);
        let before = w.players[&1].character.hp;
        w.hurt_player(1, 50., Point::default());
        assert_eq!(w.players[&1].character.hp, before);
        run(&mut w, 2, r#"{"op":"set_god_mode","enabled":true}"#);
        assert!(!w.god_mode && !w.players[&2].god, "refused for a non-GM");
        // Goto finds a player by name, in any zone.
        let name = w.players[&2].character.look.name.clone();
        let zone = w.players[&2].character.zone;
        run(
            &mut w,
            1,
            &format!(r#"{{"op":"goto","name":"{}"}}"#, name.to_uppercase()),
        );
        assert_eq!(w.players[&1].character.zone, zone);
        run(&mut w, 1, r#"{"op":"goto","name":"nobody"}"#);
        assert_eq!(packets(&mut gm_rx, "debug").pop().unwrap()["ok"], false);
    }

    #[test]
    fn die_hp_cooldowns_stats_and_god_mode_shortcuts() {
        let (mut w, _rx) = debug_world();
        dbg(&mut w, DebugCommand::SetLevel { level: 20 }).unwrap();
        w.players
            .get_mut(&1)
            .unwrap()
            .skill_cd
            .insert("whirlwind".into(), 9.);
        w.players.get_mut(&1).unwrap().cooldown = 5.;
        dbg(&mut w, DebugCommand::ResetCooldowns).unwrap();
        assert!(w.players[&1].skill_cd.is_empty() && w.players[&1].cooldown == 0.);
        dbg(&mut w, DebugCommand::Die).unwrap();
        assert!(ch(&w).hp <= 0.);
        assert!(dbg(&mut w, DebugCommand::Die).is_err());
        assert!(dbg(&mut w, DebugCommand::SetHp { hp: 0. }).is_err());
        dbg(&mut w, DebugCommand::SetHp { hp: 1e9 }).unwrap();
        assert_eq!(ch(&w).hp, ch(&w).max_hp(), "revives and clamps to max");
        dbg(&mut w, DebugCommand::SetGold { gold: 777 }).unwrap();
        assert_eq!(ch(&w).gold, 777);
        // Dying at level 20 with an empty bar cost a level.
        dbg(&mut w, DebugCommand::SetLevel { level: 20 }).unwrap();
        w.players.get_mut(&1).unwrap().character.attributes.strength = 4;
        dbg(&mut w, DebugCommand::ResetStats).unwrap();
        assert_eq!(ch(&w).stat_points(), 57);
        assert!(!w.god_mode);
        dbg(&mut w, DebugCommand::SetGodMode { enabled: true }).unwrap();
        assert!(w.god_mode);
    }

    #[test]
    fn dying_costs_a_third_of_the_level_and_can_lower_it() {
        let (mut w, mut rx) = debug_world();
        dbg(&mut w, DebugCommand::SetLevel { level: 5 }).unwrap();
        let need = ch(&w).xp_need();
        w.players.get_mut(&1).unwrap().character.xp = need / 2;
        drain(&mut rx);
        dbg(&mut w, DebugCommand::Die).unwrap();
        assert_eq!((ch(&w).level, ch(&w).xp), (5, need / 2 - need / 3));
        let text = drain(&mut rx)
            .iter()
            .find(|v| v["type"] == "notice")
            .map(|v| v["text"].to_string())
            .unwrap();
        assert!(text.contains(&format!("{} XP", need / 3)), "{text}");

        // Not enough on the bar: the rest comes out of the previous level.
        dbg(&mut w, DebugCommand::SetHp { hp: 1e9 }).unwrap();
        w.players.get_mut(&1).unwrap().character.xp = 10;
        dbg(&mut w, DebugCommand::Die).unwrap();
        let c = ch(&w);
        assert_eq!(c.level, 4);
        assert_eq!(c.xp, c.xp_need() - (need / 3 - 10));
        assert!(
            drain(&mut rx)
                .iter()
                .any(|v| v["text"].as_str().is_some_and(|t| t.contains("level 4")))
        );
    }

    #[test]
    fn death_penalty_stops_at_level_one_with_no_xp() {
        let (mut w, _rx) = debug_world();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 1;
        c.xp = 20;
        assert_eq!(c.lose_death_xp(), (33, 0));
        assert_eq!((c.level, c.xp), (1, 0));
        c.level = 2;
        c.xp = 0;
        let (_, levels) = c.lose_death_xp();
        assert_eq!(levels, 1);
        assert_eq!(c.level, 1);
        assert_eq!(c.xp, c.xp_need() - 66);
    }

    // ----- food and potions -----
    fn drain(rx: &mut mpsc::Receiver<Value>) -> Vec<Value> {
        std::iter::from_fn(|| rx.try_recv().ok()).collect()
    }
    fn hurt_to(w: &mut World, hp: f64) {
        let p = w.players.get_mut(&1).unwrap();
        p.character.hp = hp;
        // A recent hit keeps natural regeneration out of the arithmetic.
        p.last_hurt = 1.0e9;
    }
    fn hp(w: &World) -> f64 {
        w.players[&1].character.hp
    }
    fn have(w: &World, id: &str) -> u32 {
        w.players[&1].character.quantity(id)
    }
    fn seconds(w: &mut World, s: f64) {
        for _ in 0..(s / TICK).round() as usize {
            w.step();
        }
    }
    fn gold(w: &World) -> u32 {
        w.players[&1].character.gold
    }
    fn stock(w: &mut World, id: &str, n: u32) {
        w.players.get_mut(&1).unwrap().character.add_item(id, n);
    }

    #[test]
    fn baker_and_apothecary_sell_food_and_potions_for_gold_in_range_with_room() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        w.players.get_mut(&1).unwrap().character.gold = 100;
        w.time += 1.;
        w.interact(1, "baker", Some("buy_traveler_stew"));
        assert_eq!(have(&w, "traveler_stew"), 0, "too far away to buy");
        quest_interact(&mut w, "baker", Some("buy_traveler_stew"));
        quest_interact(&mut w, "baker", Some("buy_traveler_stew"));
        assert_eq!((have(&w, "traveler_stew"), gold(&w)), (2, 76));
        quest_interact(&mut w, "baker", Some("buy_health_potion"));
        assert_eq!(
            have(&w, "health_potion"),
            0,
            "the baker does not sell potions"
        );
        quest_interact(&mut w, "apothecary", Some("buy_health_potion"));
        assert_eq!((have(&w, "health_potion"), gold(&w)), (1, 46));
        w.players.get_mut(&1).unwrap().character.gold = 29;
        quest_interact(&mut w, "apothecary", Some("buy_health_potion"));
        assert_eq!(
            (have(&w, "health_potion"), gold(&w)),
            (1, 29),
            "29 gold is not enough"
        );
        for id in ["traveler_stew", "health_potion"] {
            let it = item(id).unwrap();
            assert!(
                it.sell > 0 && it.sell < 12,
                "{id} sells for less than it costs"
            );
        }
        // A full pack refuses a new kind of item but still takes more of one it already holds.
        w.players.get_mut(&1).unwrap().character.gold = 100;
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .inventory
            .retain(|s| s.item != "health_potion");
        let c = &mut w.players.get_mut(&1).unwrap().character;
        for i in ITEMS.iter().filter(|i| i.kind == "material") {
            if c.bag_used() >= c.bag_capacity() {
                break;
            }
            c.add_item(&i.id, 1);
        }
        for i in ITEMS
            .iter()
            .filter(|i| i.rarity != "common" && i.kind != "material")
        {
            if c.bag_used() >= c.bag_capacity() {
                break;
            }
            c.add_item(&i.id, 1);
        }
        assert_eq!(c.bag_used(), c.bag_capacity(), "fixture fills the pack");
        quest_interact(&mut w, "apothecary", Some("buy_health_potion"));
        assert_eq!(have(&w, "health_potion"), 0, "no room for a new stack");
        assert_eq!(gold(&w), 100, "nothing is charged without room");
        quest_interact(&mut w, "baker", Some("buy_traveler_stew"));
        assert_eq!(
            (have(&w, "traveler_stew"), gold(&w)),
            (3, 88),
            "an existing stack still grows"
        );
    }

    #[test]
    fn a_potion_heals_at_once_shares_one_sixty_second_cooldown_and_is_never_wasted() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        let max = w.players[&1].character.max_hp();
        stock(&mut w, "health_potion", 3);
        hurt_to(&mut w, max);
        w.use_item(1, "health_potion");
        assert_eq!(have(&w, "health_potion"), 3, "full health keeps the potion");
        assert!(drain(&mut rx).iter().any(|m| m["type"] == "error"));
        hurt_to(&mut w, 1.);
        w.use_item(1, "health_potion");
        assert_eq!(
            (hp(&w), have(&w, "health_potion")),
            (101., 2),
            "100 HP, immediately"
        );
        let seen = drain(&mut rx);
        let drunk = seen.iter().find(|m| m["kind"] == "consume").unwrap();
        assert_eq!(
            (drunk["item"].as_str(), drunk["value"].as_f64()),
            (Some("health_potion"), Some(100.))
        );
        assert!(
            (w.snapshot_for(0)["players"][0]["potionCd"]
                .as_f64()
                .unwrap()
                - 60.)
                .abs()
                < 1e-9
        );
        // The cooldown refuses a second potion without spending it.
        hurt_to(&mut w, 1.);
        seconds(&mut w, 30.);
        w.use_item(1, "health_potion");
        assert_eq!((hp(&w), have(&w, "health_potion")), (1., 2));
        let text = drain(&mut rx)
            .iter()
            .find(|m| m["type"] == "error")
            .unwrap()["text"]
            .to_string();
        assert!(text.contains("30 s"), "{text}");
        seconds(&mut w, 29.9);
        w.use_item(1, "health_potion");
        assert_eq!(have(&w, "health_potion"), 2, "still cooling down at 59.9 s");
        seconds(&mut w, 0.2);
        w.use_item(1, "health_potion");
        assert_eq!(
            (hp(&w), have(&w, "health_potion")),
            (101., 1),
            "ready after 60 s"
        );
        // Healing stops at the maximum.
        hurt_to(&mut w, max - 10.);
        seconds(&mut w, 60.2);
        w.use_item(1, "health_potion");
        assert_eq!((hp(&w), have(&w, "health_potion")), (max, 0));
        assert_eq!(
            drain(&mut rx)
                .iter()
                .rfind(|m| m["kind"] == "consume")
                .unwrap()["value"],
            10.
        );
    }

    #[test]
    fn food_heals_a_hundred_over_eight_seconds_and_only_one_meal_works_at_a_time() {
        let mut w = world();
        let mut rx = join(&mut w, 1, Class::Warrior);
        stock(&mut w, "traveler_stew", 3);
        hurt_to(&mut w, 1.);
        w.use_item(1, "traveler_stew");
        assert_eq!(
            (hp(&w), have(&w, "traveler_stew")),
            (1., 2),
            "nothing arrives at once"
        );
        let snap = w.snapshot_for(0);
        let buff = &snap["players"][0]["buffs"][0];
        assert_eq!(
            (
                buff["id"].as_str(),
                buff["kind"].as_str(),
                buff["time"].as_f64()
            ),
            (Some("traveler_stew"), Some("regen"), Some(8.))
        );
        seconds(&mut w, 4.);
        assert!(
            (hp(&w) - 51.).abs() < 1.,
            "half after four seconds, got {}",
            hp(&w)
        );
        // A second meal is refused and keeps its place in the pack.
        let mut ticks: Vec<_> = drain(&mut rx)
            .into_iter()
            .filter(|m| m["kind"] == "regen")
            .collect();
        w.use_item(1, "traveler_stew");
        assert_eq!(have(&w, "traveler_stew"), 2);
        assert_eq!(w.players[&1].buffs.len(), 1, "no stacking");
        let refused = drain(&mut rx);
        assert!(refused.iter().any(|m| m["type"] == "error"));
        ticks.extend(refused.into_iter().filter(|m| m["kind"] == "regen"));
        seconds(&mut w, 4.1);
        assert!(
            (hp(&w) - 101.).abs() < 0.01,
            "exactly 100 in all, got {}",
            hp(&w)
        );
        assert!(w.players[&1].buffs.is_empty());
        seconds(&mut w, 2.);
        assert!(
            (hp(&w) - 101.).abs() < 0.01,
            "the meal does not keep healing"
        );
        // The announced pieces add up to the meal, about once a second.
        ticks.extend(drain(&mut rx).into_iter().filter(|m| m["kind"] == "regen"));
        assert!(
            (7..=9).contains(&ticks.len()),
            "{} announcements",
            ticks.len()
        );
        let total: f64 = ticks.iter().map(|m| m["value"].as_f64().unwrap()).sum();
        assert!(
            (total - 100.).abs() <= ticks.len() as f64 * 0.5,
            "announced {total}"
        );
        // Once it is over another can be eaten.
        hurt_to(&mut w, 1.);
        w.use_item(1, "traveler_stew");
        assert_eq!(have(&w, "traveler_stew"), 1);
        seconds(&mut w, 8.1);
        assert!((hp(&w) - 101.).abs() < 0.01);
    }

    #[test]
    fn food_stops_at_full_health_and_ends_with_the_player_and_potions_work_during_it() {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let max = w.players[&1].character.max_hp();
        stock(&mut w, "traveler_stew", 2);
        stock(&mut w, "health_potion", 1);
        hurt_to(&mut w, max);
        w.use_item(1, "traveler_stew");
        assert_eq!(have(&w, "traveler_stew"), 2, "no meal at full health");
        hurt_to(&mut w, max - 30.);
        w.use_item(1, "traveler_stew");
        seconds(&mut w, 8.1);
        assert_eq!(hp(&w), max, "capped at the maximum");
        // Food and a potion are different effects and may overlap.
        hurt_to(&mut w, 1.);
        w.use_item(1, "traveler_stew");
        seconds(&mut w, 1.);
        w.use_item(1, "health_potion");
        assert!(
            hp(&w) > 100.,
            "the potion lands during the meal: {}",
            hp(&w)
        );
        // Dying ends the meal.
        stock(&mut w, "traveler_stew", 1);
        w.players.get_mut(&1).unwrap().character.hp = 0.;
        w.step();
        assert!(w.players[&1].buffs.is_empty());
        w.use_item(1, "traveler_stew");
        assert!(w.players[&1].buffs.is_empty(), "the dead cannot eat");
        assert_eq!(have(&w, "traveler_stew"), 1);
    }

    #[test]
    fn only_owned_usable_items_can_be_used_and_the_pack_is_saved() {
        let mut w = world();
        let (tx, mut rx) = mpsc::channel(256);
        let look = Look {
            class: Class::Mage,
            ..Look::default()
        };
        let welcome = w.join(1, None, Some(look), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        hurt_to(&mut w, 1.);
        for id in [
            "traveler_stew",
            "health_potion",
            "slime_gel",
            "mage_armor_runic",
            "nonsense",
            "linen_satchel",
        ] {
            w.use_item(1, id);
        }
        let errors = drain(&mut rx)
            .into_iter()
            .filter(|m| m["type"] == "error")
            .count();
        assert_eq!(errors, 6, "every refusal tells the player");
        assert_eq!(
            (hp(&w), w.players[&1].buffs.len(), w.players[&1].potion_cd),
            (1., 0, 0.)
        );
        stock(&mut w, "health_potion", 1);
        w.use_item(1, "health_potion");
        assert_eq!(have(&w, "health_potion"), 0);
        assert!(
            w.players[&1]
                .character
                .inventory
                .iter()
                .all(|s| s.quantity > 0),
            "no empty stacks"
        );
        let stored = w.store.load(&token).unwrap().unwrap();
        assert_eq!(
            stored.quantity("health_potion"),
            0,
            "the drunk potion is saved"
        );
    }

    #[test]
    fn the_potion_cooldown_survives_logging_out_and_a_cleared_cooldown_stays_cleared() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        stock(&mut w, "health_potion", 3);
        hurt_to(&mut w, 1.);
        w.use_item(1, "health_potion");
        let ready = w.players[&1].character.potion_ready;
        assert!(
            (ready as i64 - unix_now() as i64 - 60).abs() <= 1,
            "the end is saved as a wall-clock second"
        );
        // Leaving and returning cannot skip the wait; the drunk potion and the end time are both saved.
        w.leave(1);
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, Some(token.clone()), None, tx).unwrap();
        let left = w.players[&1].potion_cd;
        assert!(
            left > 58. && left <= 60.,
            "still waiting after a relog: {left}"
        );
        hurt_to(&mut w, 1.);
        w.use_item(1, "health_potion");
        assert_eq!(
            (hp(&w), have(&w, "health_potion")),
            (1., 2),
            "the relog did not reset the cooldown"
        );
        // A cooldown that has already passed does not come back.
        w.leave(1);
        let mut saved = w.store.load(&token).unwrap().unwrap();
        saved.potion_ready = unix_now().saturating_sub(5);
        w.store.save_many(std::iter::once(&saved)).unwrap();
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, Some(token), None, tx).unwrap();
        assert_eq!(w.players[&1].potion_cd, 0.);
        // The test shortcut clears both halves, or a relog would bring the wait back.
        hurt_to(&mut w, 1.);
        w.use_item(1, "health_potion");
        assert!(w.players[&1].potion_cd > 0.);
        w.test_commands = true;
        w.debug(1, None, DebugCommand::ResetCooldowns);
        assert_eq!(
            (
                w.players[&1].potion_cd,
                w.players[&1].character.potion_ready
            ),
            (0., 0)
        );
    }
    #[test]
    fn standing_in_a_cell_uncovers_it_and_the_fog_is_saved_per_zone() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        w.step();
        // The meadow is 96 wide, so the spawn (36, 60) is the middle cell of the middle row: bit 4.
        assert_eq!(w.players[&1].character.explored, [1 << 4]);
        assert_eq!(w.players[&1].snapshot()["explored"], json!([1 << 4]));
        // Walking within the cell adds nothing; stepping into the next one adds exactly one.
        w.players.get_mut(&1).unwrap().character.x = 40.;
        w.step();
        assert_eq!(w.players[&1].character.explored, [1 << 4]);
        w.players.get_mut(&1).unwrap().character.x = 70.;
        w.step();
        assert_eq!(w.players[&1].character.explored, [(1 << 4) | (1 << 5)]);
        // Another zone has its own mask, and the first stays as it was.
        w.test_commands = true;
        w.debug(
            1,
            None,
            DebugCommand::Teleport {
                zone: 1,
                x: 48.,
                y: 86.,
            },
        );
        w.step();
        assert_eq!(
            w.players[&1].character.explored,
            [(1 << 4) | (1 << 5), 1 << 7]
        );
        // It survives logging out and back in.
        w.leave(1);
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, Some(token), None, tx).unwrap();
        assert_eq!(
            w.players[&1].character.explored,
            [(1 << 4) | (1 << 5), 1 << 7]
        );
    }

    #[test]
    fn the_test_shortcut_uncovers_every_cell_of_every_zone() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, None, Some(Look::default()), tx).unwrap();
        w.test_commands = true;
        w.debug(1, None, DebugCommand::ExploreAll);
        assert_eq!(w.players[&1].character.explored, vec![511; zone_count(&w)]);
        w.test_commands = false;
        w.players.get_mut(&1).unwrap().character.explored.clear();
        w.debug(1, None, DebugCommand::ExploreAll);
        assert!(
            w.players[&1].character.explored.is_empty(),
            "the public service refuses it"
        );
    }

    #[test]
    fn the_dead_uncover_nothing() {
        let mut w = world();
        let (tx, _rx) = mpsc::channel(256);
        w.join(1, None, Some(Look::default()), tx).unwrap();
        let p = w.players.get_mut(&1).unwrap();
        p.character.hp = 0.;
        p.character.x = 80.;
        p.character.y = 10.;
        w.step();
        assert_eq!(w.players[&1].character.explored, Vec::<u16>::new());
    }
}
