//! The four hour shards that open the Black Hour Foundry. Each final boss of the four seasonal dungeons lets
//! one fall for every hero in its fight who has taken the quest and does not hold that shard yet. Nobody else
//! sees a shard: it lies on the ground as a private drop of the hero it belongs to.
use super::*;

/// The quest that wants the shards, and whose completion opens the Foundry's door (`Portal::needs_quest`).
pub const SHARD_QUEST: &str = "null_keys";
/// (final boss, shard): Blooming Labyrinth, Solar Crucible, Amber Archive, Silent Solstice.
pub const SHARDS: [(&str, &str); 4] = [
    ("bloom_heart", "hour_shard_bloom"),
    ("solar_heart", "hour_shard_solar"),
    ("amber_memory", "hour_shard_amber"),
    ("solstice_heart", "hour_shard_silent"),
];

impl World {
    /// Lets the boss's shard fall for each real hero of the fight who is on the quest and lacks it.
    pub(super) fn hour_shard_drops(
        &mut self,
        kind: &str,
        zone: usize,
        point: Point,
        killer: &str,
        party: &[String],
    ) {
        let Some(&(_, shard)) = SHARDS.iter().find(|(boss, _)| *boss == kind) else {
            return;
        };
        let mut heroes: Vec<&str> = std::iter::once(killer)
            .chain(party.iter().map(String::as_str))
            .collect();
        heroes.sort_unstable();
        heroes.dedup();
        let wanted: Vec<String> = heroes
            .into_iter()
            .filter(|id| {
                let Some(session) = self.session_of(id) else {
                    return false;
                };
                let c = &self.players[&session].character;
                c.quests.iter().any(|q| q.id == SHARD_QUEST && !q.claimed)
                    && c.quantity(shard) == 0
                    && !self
                        .drops
                        .iter()
                        .any(|d| d.owner == *id && d.item.as_deref() == Some(shard))
            })
            .map(str::to_owned)
            .collect();
        for id in wanted {
            self.item_drop(&id, zone, point, shard, 1);
        }
    }
}
