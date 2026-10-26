//! The Empty Seat: personal memories and finite shared quest summons. No saved schema or zone IDs change.
use super::*;
use serde::Deserialize;
use std::sync::LazyLock;

#[derive(Clone, Deserialize)]
pub(super) struct Scene {
    pub id: String,
    pub quest: String,
    pub zone: usize,
    pub seconds: f64,
    #[serde(default)]
    pub enemy: Option<String>,
}
pub(super) static SCENES: LazyLock<Vec<Scene>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/empty-seat-scenes.txt"))
        .expect("valid Empty Seat scenes")
});
#[derive(Default)]
pub(super) struct State {
    memories: BTreeMap<u64, Memory>,
    away: BTreeMap<usize, f64>,
}
struct Memory {
    id: String,
    origin: Point,
    hurt_at: f64,
    elapsed: f64,
}

/// A scene may only advance the first unfinished objective, after its real acceptance.
fn pending(c: &Character, quest: &Quest, target: &str) -> Option<(usize, usize)> {
    let qi = c
        .quests
        .iter()
        .position(|p| p.id == quest.id && !p.claimed)?;
    let progress = &c.quests[qi];
    let oi = quest
        .objectives
        .iter()
        .enumerate()
        .find(|(i, o)| progress.counts.get(*i).copied().unwrap_or(0) < o.count)?
        .0;
    (quest.objectives[oi].target == target).then_some((qi, oi))
}
impl World {
    pub(super) fn empty_seat_view(&self, session: u64) -> Value {
        self.empty_seat
            .memories
            .get(&session)
            .map_or(Value::Null, |m| json!({"id":m.id,"elapsed":m.elapsed}))
    }
    fn empty_seat_candidate(&self, session: u64, scene: &Scene, reach: f64) -> bool {
        self.players.get(&session).is_some_and(|p| {
            let c = &p.character;
            c.zone == scene.zone
                && c.hp > 0.
                && p.merc.is_none()
                && p.ambient.is_none()
                && !p.gauntlet
                && !p.frozen
                && !c.mounted
                && c.spark_travel.is_none()
                && self.maps[c.zone]
                    .quests
                    .iter()
                    .find(|q| q.id == scene.quest)
                    .is_some_and(|q| c.level >= q.min_level && pending(c, q, &scene.id).is_some())
                && self.maps[c.zone]
                    .places
                    .iter()
                    .find(|p| p.id == scene.id)
                    .is_some_and(|place| {
                        c.point().distance(Point {
                            x: place.x,
                            y: place.y,
                        }) <= reach
                    })
        })
    }
    pub(super) fn update_empty_seat(&mut self) {
        // Closed peers cannot leave an orphaned channel in a later session.
        self.empty_seat
            .memories
            .retain(|session, _| self.players.contains_key(session));
        let sessions: Vec<_> = self.players.keys().copied().collect();
        let mut changed = false;
        for session in sessions {
            let scene = SCENES
                .iter()
                .find(|s| s.enemy.is_none() && self.empty_seat_candidate(session, s, 2.1));
            let Some(scene) = scene else {
                self.empty_seat.memories.remove(&session);
                continue;
            };
            let p = &self.players[&session];
            if p.moving || p.stun > 0. || p.dash > 0. || p.combat_left > 0. || p.attack > 0. {
                self.empty_seat.memories.remove(&session);
                continue;
            }
            let point = p.character.point();
            let hurt = p.last_hurt;
            let m = self
                .empty_seat
                .memories
                .entry(session)
                .or_insert_with(|| Memory {
                    id: scene.id.clone(),
                    origin: point,
                    hurt_at: hurt,
                    elapsed: 0.,
                });
            if m.id != scene.id || m.origin.distance(point) > 0.04 || m.hurt_at != hurt {
                *m = Memory {
                    id: scene.id.clone(),
                    origin: point,
                    hurt_at: hurt,
                    elapsed: 0.,
                };
            }
            m.elapsed += TICK;
            if m.elapsed + 1e-8 >= scene.seconds {
                let quest = self.maps[scene.zone]
                    .quests
                    .iter()
                    .find(|q| q.id == scene.quest)
                    .unwrap();
                let p = self.players.get_mut(&session).unwrap();
                if let Some((qi, oi)) = pending(&p.character, quest, &scene.id) {
                    p.character.quests[qi]
                        .counts
                        .resize(quest.objectives.len(), 0);
                    p.character.quests[qi].counts[oi] = 1;
                    let _ = p.peer.try_send(json!({"type":"notice","ok":true,
                        "text":"The memory is yours. Its words are kept in your quest journal."}));
                    changed = true;
                }
                self.empty_seat.memories.remove(&session);
            }
        }
        // One authored dormant slot per echo, shared by everyone nearby. Never duplicate it per player/tick.
        for scene in SCENES.iter().filter(|s| s.enemy.is_some()) {
            let tag = format!("empty-seat:{}", scene.id);
            let Some(id) = self
                .spawns
                .iter()
                .position(|s| s.zone == scene.zone && s.ambush.as_deref() == Some(&tag))
            else {
                continue;
            };
            let target = self
                .players
                .keys()
                .copied()
                .find(|s| self.empty_seat_candidate(*s, scene, 2.1));
            if self.slimes[id].dead {
                self.empty_seat.away.remove(&id);
                if let Some(session) = target {
                    // Preserve a brief death pose before allowing another eligible hero to call the echo.
                    if self.slimes[id].state != "waiting" && self.slimes[id].die_t < 2. {
                        continue;
                    }
                    let mut s = Slime::with_level(
                        id,
                        &self.spawns[id],
                        Slime::default_level(&self.spawns[id].kind),
                    );
                    let bodies = self.actor_bodies(scene.zone, None, Some(id));
                    let Some(at) =
                        free_actor_position(&self.maps[scene.zone], s.point(), s.r, &bodies, true)
                    else {
                        continue;
                    };
                    s.x = at.x;
                    s.y = at.y;
                    s.hunt = true;
                    s.target = Some(session);
                    s.state = "chase".into();
                    s.xp = 0;
                    s.gold = 0;
                    self.slimes[id] = s;
                    self.event("ambush", "", at, 0., false);
                }
            } else if self
                .players
                .keys()
                .any(|s| self.empty_seat_candidate(*s, scene, 45.))
            {
                self.empty_seat.away.remove(&id);
            } else {
                let away = self.empty_seat.away.entry(id).or_insert(0.);
                *away += TICK;
                if *away >= 12. {
                    self.sleep_ambush(&tag);
                    self.empty_seat.away.remove(&id);
                }
            }
        }
        if changed {
            self.save();
        }
    }
    /// A summoned memory gives only personal objective credit. No farmable XP, gold, materials or equipment.
    pub(super) fn empty_seat_killed(&mut self, id: usize) {
        let s = &self.slimes[id];
        let Some(scene) = SCENES
            .iter()
            .find(|scene| scene.zone == s.zone && scene.enemy.as_deref() == Some(&s.kind))
        else {
            return;
        };
        let at = s.point();
        let contributors = s.contributors.clone();
        let quest = self.maps[scene.zone]
            .quests
            .iter()
            .find(|q| q.id == scene.quest)
            .unwrap();
        let mut changed = false;
        for p in self.players.values_mut() {
            let c = &mut p.character;
            if c.zone != scene.zone
                || c.hp <= 0.
                || p.merc.is_some()
                || p.ambient.is_some()
                || p.gauntlet
                || c.point().distance(at) > rolls::SHARE_RANGE
                || !contributors.contains(&c.id)
            {
                continue;
            }
            if let Some((qi, oi)) = pending(c, quest, &scene.id) {
                c.quests[qi].counts.resize(quest.objectives.len(), 0);
                c.quests[qi].counts[oi] = 1;
                changed = true;
            }
        }
        if changed {
            self.save();
        }
    }
}
