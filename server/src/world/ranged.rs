//! Ranged enemies. A kind with `Slime::ranged` stops at its range, winds up, and releases one missile or a fan of them
//! (`fire_enemy_bolts`). A missile flies straight at a fixed speed, hits the first living hero it touches and stops at
//! the first wall, so cover works and a hero who steps aside while the windup ends is missed.
use super::*;

/// How much farther than the nominal range a missile flies before it fades.
const BOLT_OVERSHOOT: f64 = 3.;
/// A hero this close to the line of flight is hit (the hero's own radius is added).
const BOLT_RADIUS: f64 = 0.3;

#[derive(Clone, Serialize)]
pub(super) struct EnemyBolt {
    id: u64,
    pub(super) zone: usize,
    x: f64,
    y: f64,
    fx: f64,
    fy: f64,
    color: &'static str,
    size: f64,
    /// The kind that shot it, so the client can style the missile (arrow, bolt, ...).
    kind: String,
    /// Tiles per second, so clients can carry a missile between two snapshots.
    speed: f64,
    #[serde(skip)]
    life: f64,
    #[serde(skip)]
    damage: f64,
    #[serde(skip)]
    level: u32,
}

impl World {
    /// Releases `r.shots` missiles from enemy `id` towards `aim`, fanned over `r.spread` radians.
    pub(super) fn fire_enemy_bolts(&mut self, id: usize, aim: Point, r: &Ranged) {
        let s = &self.slimes[id];
        let from = s.point();
        let base = from.direction(aim);
        let (zone, kind, level) = (s.zone, s.kind.clone(), s.level);
        let (pack_damage, enrage_scale) = self.tuned(zone, &kind);
        let damage = s.damage
            * self.forge_attack_scale(id)
            * pack_damage
            * crate::items::enrage_factor_scaled(&s.kind, s.fight, enrage_scale);
        let angle = base.y.atan2(base.x);
        for shot in 0..r.shots {
            let offset = if r.shots > 1 {
                (shot as f64 / (r.shots - 1) as f64 - 0.5) * r.spread * 2.
            } else {
                0.
            };
            let (fy, fx) = (angle + offset).sin_cos();
            let bolt_id = self.entity();
            self.enemy_bolts.push(EnemyBolt {
                id: bolt_id,
                zone,
                x: from.x + fx * 0.6,
                y: from.y + fy * 0.6,
                fx,
                fy,
                color: r.color,
                size: r.size,
                kind: kind.clone(),
                speed: r.speed,
                life: (r.range + BOLT_OVERSHOOT) / r.speed,
                damage,
                level,
            });
        }
    }

    pub(super) fn update_enemy_bolts(&mut self) {
        let mut bolts = std::mem::take(&mut self.enemy_bolts);
        let mut hits: Vec<(u64, f64, Point, String, u32)> = vec![];
        bolts.retain_mut(|b| {
            let start = Point { x: b.x, y: b.y };
            b.x += b.fx * b.speed * TICK;
            b.y += b.fy * b.speed * TICK;
            b.life -= TICK;
            let end = Point { x: b.x, y: b.y };
            // A wall (or a pillar) stops it.
            let mut probe = end;
            self.maps[b.zone].collide(&mut probe, 0.05);
            if probe.distance(end) > 1e-6 || b.life <= 0. {
                return false;
            }
            let victim = self
                .players
                .iter()
                .filter(|(_, p)| {
                    p.character.hp > 0.
                        && p.character.zone == b.zone
                        && p.character.spark_travel.is_none()
                        && !p.is_hidden()
                })
                .map(|(session, p)| (segment_distance(p.character.point(), start, end), *session))
                .filter(|(d, _)| *d < PLAYER_RADIUS + BOLT_RADIUS * b.size.max(1.))
                .min_by(|a, c| a.0.total_cmp(&c.0));
            if let Some((_, session)) = victim {
                // Use the incoming direction, even when this tick carries the missile past the victim.
                let point = self.players[&session].character.point();
                let from = Point {
                    x: point.x - b.fx,
                    y: point.y - b.fy,
                };
                hits.push((session, b.damage, from, b.kind.clone(), b.level));
                return false;
            }
            true
        });
        self.enemy_bolts = bolts;
        for (session, damage, at, kind, level) in hits {
            self.hurt_player_by(session, damage, at, &kind, level);
        }
    }
}

#[cfg(test)]
mod daze_tests {
    use super::super::wyrd_tests::{at, calm, join, place, world};
    use super::*;

    #[test]
    fn daze_projectile_crossing_victim_uses_incoming_direction() {
        let mut w = world();
        calm(&mut w);
        let _rx = join(&mut w, 1, Class::Warrior);
        place(&mut w, 1, 0, at(25., 25.));
        w.time = 10.;
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .attributes
            .dexterity = 20;
        for (fx, expected) in [(1., 4.), (-1., 0.)] {
            let p = w.players.get_mut(&1).unwrap();
            p.face = at(1., 0.);
            p.daze = 0.;
            p.last_hurt = 0.;
            w.rng = 2;
            w.enemy_bolts.push(EnemyBolt {
                id: 1,
                zone: 0,
                x: 25. - fx * 0.6,
                y: 25.,
                fx,
                fy: 0.,
                color: "red",
                size: 1.,
                kind: "archer".into(),
                speed: 24.,
                life: 1.,
                damage: 1.,
                level: 1,
            });
            w.update_enemy_bolts();
            assert!(w.enemy_bolts.is_empty());
            assert_eq!(w.players[&1].daze, expected, "incoming x direction {fx}");
        }
    }
}
