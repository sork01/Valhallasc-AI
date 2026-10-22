//! Raid-only recovery. Encounters and helpers remain owned by the boss engine.
use super::*;

impl World {
    /// Capture a wipe before ordinary respawn or the boss's return erases the encounter.
    pub(super) fn update_raid_wipes(&mut self) {
        let zones: Vec<usize> = self
            .instances
            .iter()
            .filter(|i| i.active && self.maps[i.zone].raid)
            .map(|i| i.zone)
            .collect();
        for zone in zones {
            let crew: Vec<u64> = self
                .players
                .iter()
                .filter(|(_, p)| p.character.zone == zone && p.ambient.is_none())
                .map(|(s, _)| *s)
                .collect();
            if crew.is_empty() || crew.iter().any(|s| self.players[s].character.hp > 0.) {
                continue;
            }
            let Some(boss) = self
                .slimes
                .iter()
                .find(|s| {
                    s.zone == zone
                        && !s.dead
                        && (is_boss(&s.kind) || self.boss.table.contains_key(&s.kind))
                        && (!matches!(s.state.as_str(), "idle" | "wander" | "waiting")
                            || self.boss.fights.contains_key(&s.id))
                })
                .map(|s| s.id)
            else {
                continue;
            };
            let home = Point {
                x: self.slimes[boss].hx,
                y: self.slimes[boss].hy,
            };
            let hall = self.maps[zone]
                .places
                .iter()
                .filter(|p| p.id.starts_with("cf_hall_"))
                .min_by(|a, b| {
                    home.distance(Point { x: a.x, y: a.y })
                        .total_cmp(&home.distance(Point { x: b.x, y: b.y }))
                });
            let checkpoint = hall
                .and_then(|h| {
                    self.maps[zone]
                        .places
                        .iter()
                        .find(|p| p.id == h.id.replace("cf_hall_", "cf_checkpoint_"))
                })
                .map_or(self.maps[zone].spawn, |p| Point { x: p.x, y: p.y });
            self.end_boss_fight(boss);
            self.slimes[boss] = self.fresh_enemy(boss);
            self.place_enemy(boss);
            self.bolts.retain(|b| b.zone != zone);
            self.enemy_bolts.retain(|b| b.zone != zone);
            let instance = self.instances.iter_mut().find(|i| i.zone == zone).unwrap();
            instance.rally = Some(checkpoint);
            instance.grace_until = self.time + 60.;
            for session in crew {
                let p = self.players.get_mut(&session).unwrap();
                p.fallen = false;
                p.dead_time = 0.;
                let _ = p.peer.try_send(json!({"type":"system","text":"The raid regroups at the hall's rally mark. Your contracts remain. You have sixty seconds to regroup; attacking ends the grace."}));
            }
        }
    }
}
