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
        let (zone, kind, level, damage) = (s.zone, s.kind.clone(), s.level, s.damage);
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
                })
                .map(|(session, p)| (segment_distance(p.character.point(), start, end), *session))
                .filter(|(d, _)| *d < PLAYER_RADIUS + BOLT_RADIUS * b.size.max(1.))
                .min_by(|a, c| a.0.total_cmp(&c.0));
            if let Some((_, session)) = victim {
                hits.push((session, b.damage, end, b.kind.clone(), b.level));
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
