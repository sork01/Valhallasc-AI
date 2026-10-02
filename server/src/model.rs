use serde::{Deserialize, Serialize};

pub const TICK: f64 = 0.05;
pub const MAX_PLAYERS: usize = 128;

#[derive(Clone, Copy, Debug, Default, Deserialize, Serialize)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}
impl Point {
    pub fn distance(self, other: Self) -> f64 {
        (self.x - other.x).hypot(self.y - other.y)
    }
    pub fn direction(self, other: Self) -> Self {
        normalize(other.x - self.x, other.y - self.y)
    }
}
pub fn normalize(x: f64, y: f64) -> Point {
    if !x.is_finite() || !y.is_finite() {
        return Point::default();
    }
    let n = x.hypot(y);
    if n < 1e-8 || !n.is_finite() {
        Point::default()
    } else {
        Point { x: x / n, y: y / n }
    }
}

/// Body type of the character's sprites. Every class has both; it changes only how the character looks.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Gender {
    #[default]
    Male,
    Female,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Class {
    #[default]
    Warrior,
    Mage,
    Assassin,
    Priest,
    Hunter,
}
impl Class {
    /// Classes that loose a projectile instead of hitting everything within reach.
    pub fn ranged(self) -> bool {
        matches!(self, Self::Mage | Self::Hunter)
    }
    pub fn health(self) -> f64 {
        match self {
            Self::Warrior => 120.,
            Self::Mage => 80.,
            Self::Assassin => 90.,
            Self::Priest => 100.,
            Self::Hunter => 95.,
        }
    }
    pub fn speed(self) -> f64 {
        match self {
            Self::Warrior => 5.2,
            Self::Mage => 5.6,
            Self::Assassin => 6.6,
            Self::Priest => 5.4,
            Self::Hunter => 6.,
        }
    }
    pub fn reach(self) -> f64 {
        match self {
            Self::Warrior => 1.35,
            Self::Mage => 5.5,
            Self::Assassin => 1.1,
            Self::Priest => 1.5,
            Self::Hunter => 7.,
        }
    }
    pub fn duration(self) -> f64 {
        match self {
            Self::Warrior => 0.42,
            Self::Mage => 0.56,
            Self::Assassin => 0.4,
            Self::Priest => 0.4,
            Self::Hunter => 0.4,
        }
    }
    pub fn impact(self) -> f64 {
        match self {
            Self::Warrior => 0.21,
            Self::Mage => 0.28,
            Self::Assassin => 0.2,
            Self::Priest => 0.2,
            Self::Hunter => 0.2,
        }
    }
    pub fn cooldown(self) -> f64 {
        match self {
            Self::Warrior => 0.55,
            Self::Mage => 0.7,
            Self::Assassin => 0.46,
            Self::Priest => 0.62,
            Self::Hunter => 0.58,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase", default)]
pub struct Look {
    pub name: String,
    pub class: Class,
    pub gender: Gender,
    pub hair_color: u8,
    pub skin: u8,
    pub warrior_armor: String,
    pub warrior_weapon: String,
    pub mage_armor: String,
    pub mage_weapon: String,
    pub assassin_armor: String,
    pub assassin_weapon: String,
    pub priest_armor: String,
    pub priest_weapon: String,
    pub hunter_armor: String,
    pub hunter_weapon: String,
    /// Worn head, shoulder and glove pieces of the character's own class (a variant name, or "none"). They come from
    /// the headgear, shoulders and gloves equipment slots and only change how the character looks.
    pub head: String,
    pub shoulders: String,
    pub gloves: String,
    /// Worn class-independent pieces (Ironhide Helm and Pauldrons, Duelist Gloves, Wayfarer Pants, Moonstone Necklace,
    /// Amber Ring): their `variant` in items.txt, or "none". The same art is drawn on every class. A generic helm,
    /// pauldrons or gloves occupy `head`, `shoulders` and `gloves` (they replace a class piece); the rest have layers of
    /// their own.
    pub pants: String,
    pub necklace: String,
    pub accessory: String,
}
/// Variant names of the class-independent pieces, per look field. Keep in step with scripts/generic_gear.py.
impl Default for Look {
    fn default() -> Self {
        Self {
            name: "Adventurer".into(),
            class: Class::Warrior,
            gender: Gender::Male,
            hair_color: 0,
            skin: 0,
            warrior_armor: "crimson".into(),
            warrior_weapon: "sword".into(),
            mage_armor: "apprentice".into(),
            mage_weapon: "ash".into(),
            assassin_armor: "shadow".into(),
            assassin_weapon: "daggers".into(),
            priest_armor: "pilgrim".into(),
            priest_weapon: "mace".into(),
            hunter_armor: "scout".into(),
            hunter_weapon: "shortbow".into(),
            head: "none".into(),
            shoulders: "none".into(),
            gloves: "none".into(),
            pants: "none".into(),
            necklace: "none".into(),
            accessory: "none".into(),
        }
    }
}
impl Look {
    /// A new character starts with nothing worn: worn pieces come from the equipment slots, never from the client's
    /// draft (which still carries the previous character's hood, helm or gloves).
    pub fn clear_worn(&mut self) {
        for piece in [
            &mut self.head,
            &mut self.shoulders,
            &mut self.gloves,
            &mut self.pants,
            &mut self.necklace,
            &mut self.accessory,
        ] {
            *piece = "none".into();
        }
    }
    pub fn validate(&self) -> Result<(), &'static str> {
        let len = self.name.trim().chars().count();
        if !(2..=16).contains(&len) || self.name.chars().any(char::is_control) {
            return Err("Use a name of 2–16 characters.");
        }
        if self.hair_color > 5 || self.skin > 3 {
            return Err("Invalid appearance.");
        }
        // Every worn name must be a piece in the catalog: the class's own armor and weapon for each class, the class's
        // own (or a class-independent) head, shoulders and gloves, and class-independent pants, necklace and ring.
        let known = |class: Option<Class>, kind: &str, piece: &String| {
            piece == "none"
                || crate::items::ITEMS.iter().any(|i| {
                    i.kind == kind
                        && i.variant.as_deref() == Some(piece.as_str())
                        && (i.class == class
                            || (class.is_some()
                                && i.class.is_none()
                                && kind != "armor"
                                && kind != "weapon"))
                })
        };
        let own = Some(self.class);
        let class_gear = [
            (Class::Warrior, &self.warrior_armor, &self.warrior_weapon),
            (Class::Mage, &self.mage_armor, &self.mage_weapon),
            (Class::Assassin, &self.assassin_armor, &self.assassin_weapon),
            (Class::Priest, &self.priest_armor, &self.priest_weapon),
            (Class::Hunter, &self.hunter_armor, &self.hunter_weapon),
        ];
        if class_gear.iter().any(|(class, armor, weapon)| {
            !known(Some(*class), "armor", armor) || !known(Some(*class), "weapon", weapon)
        }) || !known(own, "headgear", &self.head)
            || !known(own, "shoulders", &self.shoulders)
            || !known(own, "gloves", &self.gloves)
            || !known(None, "pants", &self.pants)
            || !known(None, "necklace", &self.necklace)
            || !known(None, "accessory", &self.accessory)
        {
            return Err("Invalid equipment.");
        }
        Ok(())
    }
    pub fn equip(&mut self, armor: &str, weapon: &str) -> Result<(), &'static str> {
        let mut next = self.clone();
        match self.class {
            Class::Warrior => {
                next.warrior_armor = armor.into();
                next.warrior_weapon = weapon.into();
            }
            Class::Mage => {
                next.mage_armor = armor.into();
                next.mage_weapon = weapon.into();
            }
            Class::Assassin => {
                next.assassin_armor = armor.into();
                next.assassin_weapon = weapon.into();
            }
            Class::Priest => {
                next.priest_armor = armor.into();
                next.priest_weapon = weapon.into();
            }
            Class::Hunter => {
                next.hunter_armor = armor.into();
                next.hunter_weapon = weapon.into();
            }
        }
        next.validate()?;
        *self = next;
        Ok(())
    }
    pub fn stats(&self, level: u32) -> (f64, f64) {
        let (base, armor, weapon) = match self.class {
            Class::Warrior => (
                22.,
                self.warrior_armor.as_str(),
                self.warrior_weapon.as_str(),
            ),
            Class::Mage => (20., self.mage_armor.as_str(), self.mage_weapon.as_str()),
            Class::Assassin => (
                18.,
                self.assassin_armor.as_str(),
                self.assassin_weapon.as_str(),
            ),
            Class::Priest => (20., self.priest_armor.as_str(), self.priest_weapon.as_str()),
            Class::Hunter => (19., self.hunter_armor.as_str(), self.hunter_weapon.as_str()),
        };
        // A piece above the character's level adds nothing (see Item::required_level).
        let worn = |kind, variant| {
            crate::items::equipment(self.class, kind, variant).filter(|i| i.required_level <= level)
        };
        let defense = worn("armor", armor).map_or(0., |i| i.defense);
        let bonus = worn("weapon", weapon).map_or(0., |i| i.attack);
        // Gear that carries both stats (green and better) brings its secondary one too.
        let attack_extra = worn("armor", armor).map_or(0., |i| i.attack);
        let defense_extra = worn("weapon", weapon).map_or(0., |i| i.defense);
        (
            base + level as f64 * 4. + bonus + attack_extra,
            defense + defense_extra,
        )
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Character {
    pub id: String,
    pub look: Look,
    pub x: f64,
    pub y: f64,
    pub hp: f64,
    pub level: u32,
    pub xp: u32,
    pub gold: u32,
    pub kills: u32,
    #[serde(default)]
    pub quests: Vec<QuestProgress>,
    #[serde(default)]
    pub inventory: Vec<crate::items::ItemStack>,
    #[serde(default)]
    pub equipment: std::collections::BTreeMap<String, String>,
    #[serde(default)]
    pub bags: Vec<String>,
    #[serde(default)]
    pub attributes: Attributes,
    /// Index of the zone the character stands in; 0 is Greenmeadow and Alderhaven.
    #[serde(default)]
    pub zone: usize,
    /// Character ids of mutual friends. Both sides list each other; names and levels are looked up when shown.
    #[serde(default)]
    pub friends: Vec<String>,
    /// Unix second when the potion cooldown ends. Wall-clock, so logging out or a restart cannot skip the wait.
    #[serde(default)]
    pub potion_ready: u64,
}
/// Permanently trained points. Base class combat values stay unchanged until trained.
#[derive(Clone, Debug, Default, Deserialize, Serialize, PartialEq)]
#[serde(default)]
pub struct Attributes {
    pub strength: u32,
    pub agility: u32,
    pub intellect: u32,
    pub stamina: u32,
    pub dexterity: u32,
    pub accuracy: u32,
}
/// XP to go from level L to L+1, for levels 1..=98, from world/levels.txt.
static LEVEL_XP: std::sync::LazyLock<Vec<u32>> = std::sync::LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/levels.txt")).expect("valid level table")
});
/// XP a character needs to go from `level` to the next. Past the end of the table each level adds what the last
/// one did, so nothing breaks above 98.
pub fn xp_to_level(level: u32) -> u32 {
    let table = &*LEVEL_XP;
    let level = level.max(1) as usize;
    match table.get(level - 1) {
        Some(need) => *need,
        None => {
            let last = table.len();
            let step = table[last - 1] - table[last - 2];
            table[last - 1] + step * (level - last) as u32
        }
    }
}
/// XP an enemy of `level` pays: 45 + 5 per level, so a same-level kill is half a level at level 1 and a fraction of a
/// percent at level 98.
pub fn enemy_xp(level: u32) -> u32 {
    45 + 5 * level.max(1)
}
impl Character {
    pub fn max_hp(&self) -> f64 {
        self.look.class.health()
            + self.level.saturating_sub(1) as f64 * 20.
            + self.attributes.stamina as f64 * 8.
    }
    pub fn stat_points(&self) -> u32 {
        let a = &self.attributes;
        self.level
            .saturating_sub(1)
            .saturating_mul(3)
            .saturating_sub(
                a.strength
                    .saturating_add(a.agility)
                    .saturating_add(a.intellect)
                    .saturating_add(a.stamina)
                    .saturating_add(a.dexterity)
                    .saturating_add(a.accuracy),
            )
    }
    pub fn allocate_stat(&mut self, stat: &str) -> Result<(), &'static str> {
        if self.hp <= 0. {
            return Err("You cannot train stats while defeated.");
        }
        if self.stat_points() == 0 {
            return Err("Level up to earn more stat points.");
        }
        if (stat == "accuracy" && self.attributes.accuracy >= 20)
            || (stat == "dexterity" && self.attributes.dexterity >= 70)
        {
            return Err("That stat has reached its maximum. Choose another stat.");
        }
        let value = match stat {
            "strength" => &mut self.attributes.strength,
            "agility" => &mut self.attributes.agility,
            "intellect" => &mut self.attributes.intellect,
            "stamina" => &mut self.attributes.stamina,
            "dexterity" => &mut self.attributes.dexterity,
            "accuracy" => &mut self.attributes.accuracy,
            _ => return Err("Unknown stat."),
        };
        *value += 1;
        if stat == "stamina" {
            self.hp = (self.hp + 8.).min(self.max_hp());
        }
        Ok(())
    }
    pub fn crit_chance(&self) -> f64 {
        ((if self.look.class == Class::Assassin {
            0.28
        } else {
            0.14
        }) + self.attributes.agility as f64 * 0.005)
            .min(0.60)
    }
    pub fn cooldown_multiplier(&self) -> f64 {
        1. - (self.attributes.intellect as f64 * 0.01).min(0.30)
    }
    pub fn dodge_chance(&self) -> f64 {
        (self.attributes.dexterity as f64 * 0.005).min(0.35)
    }
    pub fn hit_chance(&self) -> f64 {
        (0.90 + self.attributes.accuracy as f64 * 0.005).min(1.)
    }
    pub fn attack_cooldown(&self) -> f64 {
        (self.look.class.cooldown() * self.cooldown_multiplier()).max(self.look.class.duration())
    }
    pub fn xp_need(&self) -> u32 {
        xp_to_level(self.level)
    }
    pub fn point(&self) -> Point {
        Point {
            x: self.x,
            y: self.y,
        }
    }
    // Dying costs a third of the XP the current level needs. When the bar holds less than that the
    // difference comes out of the previous level, so a death can lower the level; level 1 stops at 0 XP.
    // Returns (xp lost, levels lost).
    pub fn lose_death_xp(&mut self) -> (u32, u32) {
        let mut owed = self.xp_need() / 3;
        let lost = owed;
        let mut levels = 0;
        while owed > 0 {
            if self.xp >= owed {
                self.xp -= owed;
                break;
            }
            owed -= self.xp;
            if self.level <= 1 {
                self.xp = 0;
                break;
            }
            self.level -= 1;
            levels += 1;
            self.xp = self.xp_need();
        }
        (lost, levels)
    }
    pub fn grant_xp(&mut self, xp: u32) -> u32 {
        self.xp = self.xp.saturating_add(xp);
        let mut levels = 0;
        while self.xp >= self.xp_need() && self.level < 1000 {
            self.xp -= self.xp_need();
            self.level += 1;
            self.hp = self.max_hp();
            levels += 1;
        }
        levels
    }
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct QuestProgress {
    pub id: String,
    pub counts: Vec<u32>,
    pub claimed: bool,
    pub completions: u32,
}

#[derive(Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Quest {
    pub id: String,
    pub title: String,
    pub npc: String,
    pub requires: Option<String>,
    pub repeatable: bool,
    /// Recommended character level; the XP reward is a tenth of what that level needs. Clients read it
    /// from client/world.js and a world test checks the reward, so the server itself never uses it.
    #[cfg_attr(not(test), allow(dead_code))]
    pub level: u32,
    pub reward_xp: u32,
    pub reward_gold: u32,
    pub objectives: Vec<QuestObjective>,
}
#[derive(Clone, Deserialize)]
pub struct QuestObjective {
    pub kind: String,
    pub target: String,
    pub count: u32,
}
impl Quest {
    pub fn unlocked(&self, character: &Character) -> bool {
        self.requires.as_ref().is_none_or(|id| {
            character
                .quests
                .iter()
                .any(|q| &q.id == id && q.completions > 0)
        })
    }
    pub fn ready(&self, progress: &QuestProgress) -> bool {
        !progress.claimed
            && self
                .objectives
                .iter()
                .enumerate()
                .all(|(i, o)| progress.counts.get(i).copied().unwrap_or(0) >= o.count)
    }
}

pub fn quest_progress(character: &mut Character, quests: &[Quest], kind: &str, target: &str) {
    for progress in character.quests.iter_mut().filter(|q| !q.claimed) {
        let Some(quest) = quests.iter().find(|q| q.id == progress.id) else {
            continue;
        };
        for (i, objective) in quest.objectives.iter().enumerate() {
            let matches = objective.target == target
                || objective.target == "any"
                || (objective.target == "slime"
                    && ["green", "blue", "pink", "yellow"].contains(&target));
            if objective.kind == kind
                && matches
                && let Some(count) = progress.counts.get_mut(i)
            {
                *count = count.saturating_add(1).min(objective.count);
            }
        }
    }
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum ClientMessage {
    Join {
        version: u32,
        token: Option<String>,
        look: Option<Box<Look>>,
        /// A login session from /api (an account join). `character` picks one the account owns; without it `look` makes a new one.
        #[serde(default)]
        session: Option<String>,
        #[serde(default)]
        character: Option<String>,
    },
    Input {
        dx: f64,
        dy: f64,
    },
    Stop,
    Move {
        x: f64,
        y: f64,
    },
    Target {
        id: usize,
    },
    Attack {
        fx: f64,
        fy: f64,
    },
    Dash {
        dx: f64,
        dy: f64,
    },
    Skill {
        id: String,
        fx: f64,
        fy: f64,
    },
    UseItem {
        item: String,
    },
    Equip {
        armor: Option<String>,
        weapon: Option<String>,
        #[serde(default)]
        slots: std::collections::BTreeMap<String, String>,
    },
    AllocateStat {
        stat: String,
    },
    Interact {
        npc: String,
        offer: Option<String>,
    },
    Chat {
        text: String,
    },
    /// Friends and parties (server/src/world/social.rs).
    Social {
        command: SocialCommand,
    },
    Ping {
        nonce: u64,
    },
    /// Test-server shortcuts (VALHALLA_TEST_COMMANDS=1); every other server refuses them.
    Debug {
        #[serde(default, rename = "ref")]
        reference: Option<u64>,
        command: DebugCommand,
    },
}

/// A target is the character id (from the friends list, the online list or an invite), or else a name that
/// must match exactly one online player.
#[derive(Debug, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum SocialCommand {
    Refresh,
    Who,
    FriendRequest {
        id: Option<String>,
        name: Option<String>,
    },
    FriendAccept {
        id: String,
    },
    FriendDecline {
        id: String,
    },
    FriendRemove {
        id: String,
    },
    PartyInvite {
        id: Option<String>,
        name: Option<String>,
    },
    PartyAccept {
        id: String,
    },
    PartyDecline {
        id: String,
    },
    PartyLeave,
    PartyKick {
        id: String,
    },
    PartyPromote {
        id: String,
    },
    PartyChat {
        text: String,
    },
}

#[derive(Debug, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum DebugCommand {
    SetLevel {
        level: u32,
    },
    GiveXp {
        amount: u32,
    },
    SetGold {
        gold: u32,
    },
    SetHp {
        hp: f64,
    },
    Die,
    ResetStats,
    ResetCooldowns,
    SetGodMode {
        enabled: bool,
    },
    Teleport {
        zone: usize,
        x: f64,
        y: f64,
    },
    GiveItem {
        item: String,
        quantity: u32,
        #[serde(default)]
        force: bool,
    },
    TakeItem {
        item: String,
        quantity: u32,
    },
    DropItem {
        item: String,
        quantity: u32,
    },
    Quest {
        id: String,
        action: QuestDebug,
    },
    KillEnemy {
        id: usize,
    },
    RespawnEnemy {
        id: usize,
    },
    /// Puts an enemy of this kind at (x, y) in the player's zone, on the nearest free ground. It reuses a dead enemy of
    /// that kind when there is one (else the first living one), at `level` (default: the kind's own level, no random spread).
    SpawnEnemy {
        kind: String,
        x: f64,
        y: f64,
        #[serde(default)]
        level: Option<u32>,
    },
    SummonKing,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QuestDebug {
    Accept,
    Complete,
    Claim,
    Finish,
    Reset,
}

#[derive(Clone, Deserialize)]
pub struct Obstacle {
    pub x: f64,
    pub y: f64,
    pub r: f64,
    #[serde(default)]
    pub width: f64,
    #[serde(default)]
    pub depth: f64,
}
#[derive(Clone, Deserialize, Serialize)]
pub struct Offer {
    pub id: String,
    pub label: String,
    pub cost: u32,
    #[serde(default)]
    pub heal: f64,
    #[serde(default)]
    pub gear: bool,
    #[serde(default)]
    pub bag: Option<String>,
    /// An item the offer sells (one per purchase).
    #[serde(default)]
    pub item: Option<String>,
}
#[derive(Clone, Deserialize, Serialize)]
pub struct Npc {
    pub id: String,
    pub name: String,
    pub role: String,
    pub x: f64,
    pub y: f64,
    pub dialogue: String,
    pub offers: Vec<Offer>,
    #[serde(default)]
    pub buys: bool,
}
#[derive(Clone, Deserialize)]
pub struct City {
    pub x0: f64,
    pub x1: f64,
    pub y0: f64,
    pub y1: f64,
}
impl City {
    pub fn contains(&self, point: Point) -> bool {
        point.x >= self.x0 && point.x <= self.x1 && point.y >= self.y0 && point.y <= self.y1
    }
}
#[derive(Clone, Deserialize)]
pub struct SlimeSpawn {
    pub x: f64,
    pub y: f64,
    pub kind: String,
    /// Filled in when the zones' spawns are flattened into the world's enemy list.
    #[serde(skip)]
    pub zone: usize,
}
/// Walking into this disc moves a player to another zone's arrival point.
#[derive(Clone, Deserialize, Serialize)]
pub struct Portal {
    pub id: String,
    pub name: String,
    pub x: f64,
    pub y: f64,
    pub r: f64,
    pub to: usize,
    pub tx: f64,
    pub ty: f64,
}
#[derive(Clone, Deserialize)]
pub struct Map {
    #[serde(default)]
    pub name: String,
    pub size: u32,
    pub spawn: Point,
    pub objects: Vec<Obstacle>,
    pub slimes: Vec<SlimeSpawn>,
    #[serde(default)]
    pub npcs: Vec<Npc>,
    #[serde(default)]
    pub quests: Vec<Quest>,
    pub city: Option<City>,
    #[serde(default)]
    pub portals: Vec<Portal>,
    /// Recommended character levels, shown when a portal is used.
    #[serde(default)]
    pub levels: Option<[u32; 2]>,
    /// Further zones; only the top-level map carries them, as zones 1, 2, ...
    #[serde(default)]
    pub zones: Vec<Map>,
}
impl Default for Map {
    fn default() -> Self {
        serde_json::from_str(include_str!("../../world/map.txt")).expect("valid bundled world map")
    }
}
impl Map {
    pub fn in_city(&self, point: Point) -> bool {
        self.city.as_ref().is_some_and(|city| city.contains(point))
    }
    pub fn collide(&self, p: &mut Point, radius: f64) {
        for _ in 0..2 {
            for o in &self.objects {
                if o.width > 0. && o.depth > 0. {
                    // Expanded footprints also prevent dashes through buildings and walls.
                    let hx = o.width / 2. + radius;
                    let hy = o.depth / 2. + radius;
                    let dx = p.x - o.x;
                    let dy = p.y - o.y;
                    if dx.abs() < hx && dy.abs() < hy {
                        if hx - dx.abs() < hy - dy.abs() {
                            p.x = o.x + if dx < 0. { -hx } else { hx };
                        } else {
                            p.y = o.y + if dy < 0. { -hy } else { hy };
                        }
                    }
                    continue;
                }
                let d = p.distance(Point { x: o.x, y: o.y });
                let min = radius + o.r;
                if d < min {
                    let n = if d < 1e-8 {
                        Point { x: 1., y: 0. }
                    } else {
                        normalize(p.x - o.x, p.y - o.y)
                    };
                    p.x = o.x + n.x * min;
                    p.y = o.y + n.y * min;
                }
            }
            p.x = p.x.clamp(0.7, self.size as f64 - 0.7);
            p.y = p.y.clamp(0.7, self.size as f64 - 0.7);
        }
    }
    pub fn walk(&self, p: &mut Point, direction: Point, distance: f64, radius: f64) {
        // Substeps prevent a dash from tunnelling through small obstacles.
        let steps = (distance.abs() / 0.15).ceil().max(1.) as usize;
        for _ in 0..steps {
            p.x += direction.x * distance / steps as f64;
            p.y += direction.y * distance / steps as f64;
            self.collide(p, radius);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gender_defaults_to_male_round_trips_and_rejects_unknown_values() {
        assert_eq!(Look::default().gender, Gender::Male);
        // A look saved before genders existed has no field and stays male.
        let old: Look = serde_json::from_str(r#"{"name":"Ragna","class":"mage"}"#).unwrap();
        assert_eq!(old.gender, Gender::Male);
        for class in ["warrior", "mage", "assassin", "priest", "hunter"] {
            let text = format!(r#"{{"name":"Freya","class":"{class}","gender":"female"}}"#);
            let look: Look = serde_json::from_str(&text).unwrap();
            assert_eq!(look.gender, Gender::Female, "{class}");
            assert!(look.validate().is_ok(), "{class}");
            let sent = serde_json::to_value(&look).unwrap();
            assert_eq!(
                sent["gender"], "female",
                "other players see it as lowercase text"
            );
        }
        assert!(serde_json::from_str::<Look>(r#"{"gender":"other"}"#).is_err());
        assert!(serde_json::from_str::<Look>(r#"{"gender":2}"#).is_err());
    }

    #[test]
    fn level_table_drives_xp_and_enemies_pay_forty_five_plus_five_per_level() {
        assert_eq!(
            [1, 2, 3, 4, 10, 25, 98].map(xp_to_level),
            [100, 200, 400, 600, 2100, 9600, 118300]
        );
        assert!(
            (1..98).all(|l| xp_to_level(l + 1) > xp_to_level(l)),
            "the table only grows"
        );
        assert_eq!(
            xp_to_level(99),
            118300 + 2300,
            "levels past the table keep the last step"
        );
        assert_eq!(xp_to_level(0), 100);
        assert_eq!([1, 2, 5, 10, 98].map(enemy_xp), [50, 55, 70, 95, 535]);
    }

    #[test]
    fn city_footprints_block_walks_and_dashes_but_gate_is_open() {
        let map = Map::default();
        let mut point = Point { x: 36., y: 70. };
        map.walk(&mut point, Point { x: 0., y: 1. }, 8., 0.3);
        assert!((point.y - 78.).abs() < 1e-6);
        assert!(map.in_city(point));
        point = Point { x: 43., y: 80. };
        map.walk(&mut point, Point { x: 0., y: -1. }, 6., 0.3);
        assert!(point.y >= 77.9 - 1e-8);
        point = Point { x: 22., y: 80. };
        map.walk(&mut point, Point { x: 1., y: 0. }, 4., 0.3);
        assert!(point.x <= 23.4 + 1e-8);
        for npc in &map.npcs {
            let original = Point { x: npc.x, y: npc.y };
            let mut resolved = original;
            map.collide(&mut resolved, 0.3);
            assert!(
                resolved.distance(original) < 1e-6,
                "{} stands inside an obstacle",
                npc.id
            );
        }
    }

    #[test]
    fn collision_blocks_dash_tunnelling_and_resolves_centres() {
        let map = Map {
            name: String::new(),
            size: 72,
            spawn: Point::default(),
            slimes: vec![],
            npcs: vec![],
            quests: vec![],
            city: None,
            portals: vec![],
            levels: None,
            zones: vec![],
            objects: vec![Obstacle {
                x: 5.,
                y: 5.,
                r: 0.4,
                width: 0.,
                depth: 0.,
            }],
        };
        let mut point = Point { x: 3., y: 5. };
        map.walk(&mut point, Point { x: 1., y: 0. }, 2.7, 0.3);
        assert!(point.x <= 4.3 + 1e-8);
        point = Point { x: 5., y: 5. };
        map.collide(&mut point, 0.3);
        assert!((point.distance(Point { x: 5., y: 5. }) - 0.7).abs() < 1e-8);
        point = Point { x: -100., y: 1000. };
        map.collide(&mut point, 0.3);
        assert_eq!(point.x, 0.7);
        assert_eq!(point.y, 71.3);
    }
}
