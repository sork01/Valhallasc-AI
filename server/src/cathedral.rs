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
    /// A sleeping helper of a final-boss mechanic (a singer, pearl, seed or cocoon): a kill gives experience only.
    #[serde(default)]
    pub add: bool,
}
pub static ENEMIES: LazyLock<Vec<Enemy>> = LazyLock::new(|| {
    let mut enemies: Vec<Enemy> = serde_json::from_str(include_str!("../../world/cathedral.txt"))
        .expect("valid cathedral catalog");
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/eye_below.txt"))
            .expect("valid Eye Below catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/elder_hollow.txt"))
            .expect("valid Elder Hollow catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/thousandfold.txt"))
            .expect("valid Thousandfold Pavilion catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/rain_crown.txt"))
            .expect("valid Rain Crown catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/seed_vault.txt"))
            .expect("valid Seed Vault catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/sunken_astrolabe.txt"))
            .expect("valid Sunken Astrolabe catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/thunderheart_gate.txt"))
            .expect("valid Thunderheart Gate catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/blooming_labyrinth.txt"))
            .expect("valid Blooming Labyrinth catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/solar_crucible.txt"))
            .expect("valid Solar Crucible catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/amber_archive.txt"))
            .expect("valid Amber Archive catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/silent_solstice.txt"))
            .expect("valid Silent Solstice catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/nornroot.txt"))
            .expect("valid Nornroot Barrow catalog"),
    );
    enemies.extend(
        serde_json::from_str::<Vec<Enemy>>(include_str!("../../world/skybridge.txt"))
            .expect("valid Shattered Span catalog"),
    );
    enemies
});
pub fn enemy(kind: &str) -> Option<&'static Enemy> {
    ENEMIES.iter().find(|e| e.kind == kind)
}
