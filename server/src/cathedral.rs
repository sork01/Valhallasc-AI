//! The Drowned Cathedral's shared encounter catalog. Art and map generators read the same source.
use serde::Deserialize;
use std::sync::LazyLock;

#[derive(Deserialize)]
pub struct Enemy {
    pub kind: String,
    pub level: u32,
    pub stats: [f64; 4],
    pub profile: [f64; 4],
    pub boss: bool,
    pub gold: u32,
    pub material: String,
    #[serde(rename = "lootSource")]
    pub loot_source: Option<String>,
    pub ranged: Option<(f64, f64, String, f64, u32, f64)>,
    pub slam: f64,
    pub melee: f64,
}
pub static ENEMIES: LazyLock<Vec<Enemy>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/cathedral.txt"))
        .expect("valid cathedral catalog")
});
pub fn enemy(kind: &str) -> Option<&'static Enemy> {
    ENEMIES.iter().find(|e| e.kind == kind)
}
