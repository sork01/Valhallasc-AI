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

#[derive(Clone, Copy, Debug, Default, PartialEq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Class {
    #[default]
    Warrior,
    Mage,
    Assassin,
}
impl Class {
    pub fn health(self) -> f64 {
        match self {
            Self::Warrior => 120.,
            Self::Mage => 80.,
            Self::Assassin => 90.,
        }
    }
    pub fn speed(self) -> f64 {
        match self {
            Self::Warrior => 5.2,
            Self::Mage => 5.6,
            Self::Assassin => 6.6,
        }
    }
    pub fn reach(self) -> f64 {
        match self {
            Self::Warrior => 1.35,
            Self::Mage => 5.5,
            Self::Assassin => 1.1,
        }
    }
    pub fn duration(self) -> f64 {
        match self {
            Self::Warrior => 0.42,
            Self::Mage => 0.56,
            Self::Assassin => 0.4,
        }
    }
    pub fn impact(self) -> f64 {
        match self {
            Self::Warrior => 0.21,
            Self::Mage => 0.28,
            Self::Assassin => 0.2,
        }
    }
    pub fn cooldown(self) -> f64 {
        match self {
            Self::Warrior => 0.55,
            Self::Mage => 0.7,
            Self::Assassin => 0.46,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase", default)]
pub struct Look {
    pub name: String,
    pub class: Class,
    pub hair_color: u8,
    pub skin: u8,
    pub warrior_armor: String,
    pub warrior_weapon: String,
    pub mage_armor: String,
    pub mage_weapon: String,
    pub assassin_armor: String,
    pub assassin_weapon: String,
}
impl Default for Look {
    fn default() -> Self {
        Self {
            name: "Adventurer".into(),
            class: Class::Warrior,
            hair_color: 0,
            skin: 0,
            warrior_armor: "crimson".into(),
            warrior_weapon: "sword".into(),
            mage_armor: "apprentice".into(),
            mage_weapon: "ash".into(),
            assassin_armor: "shadow".into(),
            assassin_weapon: "daggers".into(),
        }
    }
}
impl Look {
    pub fn validate(&self) -> Result<(), &'static str> {
        let len = self.name.trim().chars().count();
        if !(2..=16).contains(&len) || self.name.chars().any(char::is_control) {
            return Err("Use a name of 2–16 characters.");
        }
        if self.hair_color > 5 || self.skin > 3 {
            return Err("Invalid appearance.");
        }
        if !["none", "crimson", "azure"].contains(&self.warrior_armor.as_str())
            || !["none", "sword", "royal"].contains(&self.warrior_weapon.as_str())
            || !["none", "apprentice", "runic"].contains(&self.mage_armor.as_str())
            || !["none", "ash", "crystal"].contains(&self.mage_weapon.as_str())
            || !["none", "shadow", "moon"].contains(&self.assassin_armor.as_str())
            || !["none", "daggers", "moonfang"].contains(&self.assassin_weapon.as_str())
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
        };
        let defense = match armor {
            "crimson" => 3.,
            "azure" | "runic" => 5.,
            "apprentice" | "shadow" => 2.,
            "moon" => 4.,
            _ => 0.,
        };
        let bonus = match weapon {
            "sword" | "ash" | "daggers" => 4.,
            "royal" | "moonfang" => 8.,
            "crystal" => 9.,
            _ => 0.,
        };
        (base + level as f64 * 4. + bonus, defense)
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
}
impl Character {
    pub fn max_hp(&self) -> f64 {
        self.look.class.health() + (self.level - 1) as f64 * 20.
    }
    pub fn xp_need(&self) -> u32 {
        (40. * (self.level as f64).powf(1.35)).round() as u32
    }
    pub fn point(&self) -> Point {
        Point {
            x: self.x,
            y: self.y,
        }
    }
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum ClientMessage {
    Join {
        version: u32,
        token: Option<String>,
        look: Option<Look>,
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
    Equip {
        armor: String,
        weapon: String,
    },
    Chat {
        text: String,
    },
    Ping {
        nonce: u64,
    },
}

#[derive(Clone, Deserialize)]
pub struct Obstacle {
    pub x: f64,
    pub y: f64,
    pub r: f64,
}
#[derive(Clone, Deserialize)]
pub struct SlimeSpawn {
    pub x: f64,
    pub y: f64,
    pub kind: String,
}
#[derive(Clone, Deserialize)]
pub struct Map {
    pub size: u32,
    pub spawn: Point,
    pub objects: Vec<Obstacle>,
    pub slimes: Vec<SlimeSpawn>,
}
impl Default for Map {
    fn default() -> Self {
        serde_json::from_str(include_str!("../../world/map.txt")).expect("valid bundled world map")
    }
}
impl Map {
    pub fn collide(&self, p: &mut Point, radius: f64) {
        for _ in 0..2 {
            for o in &self.objects {
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
    fn collision_blocks_dash_tunnelling_and_resolves_centres() {
        let map = Map {
            size: 72,
            spawn: Point::default(),
            slimes: vec![],
            objects: vec![Obstacle {
                x: 5.,
                y: 5.,
                r: 0.4,
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
