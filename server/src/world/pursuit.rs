//! Dungeon pursuit follows connected floor around walls. Distance fields are shared by enemies chasing the same
//! target in the same copy, refreshed at most twice a second; static grids are shared by template and body size.
use super::*;
use std::collections::VecDeque;

const CELL: f64 = 0.5;

#[derive(Default)]
pub(super) struct Pursuit {
    grids: BTreeMap<(usize, u32), Grid>,
    fields: BTreeMap<(usize, u64, u32), Field>,
}
struct Grid {
    side: usize,
    free: Vec<bool>,
}
struct Field {
    goal: usize,
    built: f64,
    distance: Vec<u32>,
}

pub(super) fn clear_line(map: &Map, from: Point, to: Point, radius: f64) -> bool {
    let steps = (from.distance(to) / 0.2).ceil().max(1.) as usize;
    (1..=steps).all(|i| {
        let f = i as f64 / steps as f64;
        let p = Point {
            x: from.x + (to.x - from.x) * f,
            y: from.y + (to.y - from.y) * f,
        };
        let mut q = p;
        map.collide(&mut q, radius);
        q.distance(p) < 1e-8
    })
}

impl Grid {
    fn new(map: &Map, radius: f64) -> Self {
        let side = (map.size as f64 / CELL) as usize;
        let mut free: Vec<bool> = (0..side * side)
            .map(|i| {
                let x = (i % side) as f64 * CELL + CELL / 2.;
                let y = (i / side) as f64 * CELL + CELL / 2.;
                x >= 0.7 && y >= 0.7 && x <= map.size as f64 - 0.7 && y <= map.size as f64 - 0.7
            })
            .collect();
        // Rasterise each expanded obstacle only over the cells it covers. Scanning every obstacle for every
        // cell pauses the simulation for seconds when a large dungeon first needs a pursuit route.
        for o in &map.objects {
            let rectangular = o.width > 0. && o.depth > 0.;
            let hx = if rectangular { o.width / 2. } else { o.r } + radius;
            let hy = if rectangular { o.depth / 2. } else { o.r } + radius;
            let begin = |n: f64| ((n / CELL).floor() as isize).clamp(0, side as isize) as usize;
            let end = |n: f64| ((n / CELL).ceil() as isize).clamp(0, side as isize) as usize;
            for y in begin(o.y - hy)..end(o.y + hy) {
                for x in begin(o.x - hx)..end(o.x + hx) {
                    let dx = x as f64 * CELL + CELL / 2. - o.x;
                    let dy = y as f64 * CELL + CELL / 2. - o.y;
                    if (rectangular && dx.abs() < hx && dy.abs() < hy)
                        || (!rectangular && dx.hypot(dy) < hx)
                    {
                        free[y * side + x] = false;
                    }
                }
            }
        }
        Self { side, free }
    }
    fn point(&self, i: usize) -> Point {
        Point {
            x: (i % self.side) as f64 * CELL + CELL / 2.,
            y: (i / self.side) as f64 * CELL + CELL / 2.,
        }
    }
    fn neighbors(&self, i: usize) -> impl Iterator<Item = usize> + '_ {
        let (x, y) = (i % self.side, i / self.side);
        [
            x.checked_sub(1).map(|x| y * self.side + x),
            (x + 1 < self.side).then_some(i + 1),
            y.checked_sub(1).map(|y| y * self.side + x),
            (y + 1 < self.side).then_some(i + self.side),
        ]
        .into_iter()
        .flatten()
        .filter(|i| self.free[*i])
    }
    /// Connect real positions beside walls to a visible grid cell, without snapping through an obstacle.
    fn anchor(&self, map: &Map, p: Point, radius: f64) -> Option<usize> {
        let (x, y) = ((p.x / CELL) as i32, (p.y / CELL) as i32);
        let mut candidates: Vec<_> = (-3..=3)
            .flat_map(|dy| (-3..=3).map(move |dx| (x + dx, y + dy)))
            .filter(|(x, y)| {
                *x >= 0 && *y >= 0 && (*x as usize) < self.side && (*y as usize) < self.side
            })
            .map(|(x, y)| y as usize * self.side + x as usize)
            .filter(|i| self.free[*i])
            .collect();
        candidates.sort_by(|a, b| {
            p.distance(self.point(*a))
                .total_cmp(&p.distance(self.point(*b)))
        });
        candidates
            .into_iter()
            .find(|i| clear_line(map, p, self.point(*i), radius))
    }
    fn field(&self, goal: usize, time: f64) -> Field {
        let mut distance = vec![u32::MAX; self.free.len()];
        let mut queue = VecDeque::from([goal]);
        distance[goal] = 0;
        while let Some(i) = queue.pop_front() {
            for next in self.neighbors(i) {
                if distance[next] == u32::MAX {
                    distance[next] = distance[i] + 1;
                    queue.push_back(next);
                }
            }
        }
        Field {
            goal,
            built: time,
            distance,
        }
    }
}

#[cfg(test)]
pub(super) fn grid_matches_collision(map: &Map, radius: f64) -> bool {
    let grid = Grid::new(map, radius);
    (0..grid.free.len()).step_by(11).all(|i| {
        let p = grid.point(i);
        let mut q = p;
        map.collide(&mut q, radius);
        grid.free[i] == (q.distance(p) < 1e-8)
    })
}

impl Pursuit {
    pub(super) fn retain(&mut self, players: &BTreeMap<u64, Player>) {
        self.fields.retain(|(zone, session, _), _| {
            players
                .get(session)
                .is_some_and(|p| p.character.zone == *zone && p.character.hp > 0.)
        });
    }
    pub(super) fn toward(
        &mut self,
        map: &Map,
        template: usize,
        enemy: &Slime,
        session: u64,
        target: Point,
        time: f64,
    ) -> Option<Point> {
        let from = enemy.point();
        if from.distance(target) < 3. && clear_line(map, from, target, enemy.r) {
            return Some(target);
        }
        // Round up, so a cached grid is safe for every body in its tenth-unit bucket.
        let body = (enemy.r * 10.).ceil() as u32;
        let radius = body as f64 / 10.;
        let grid = self
            .grids
            .entry((template, body))
            .or_insert_with(|| Grid::new(map, radius));
        let goal = grid.anchor(map, target, radius)?;
        let start = grid.anchor(map, from, radius)?;
        let field = self
            .fields
            .entry((enemy.zone, session, body))
            .or_insert_with(|| grid.field(goal, time));
        if goal != field.goal && time - field.built >= 0.5 {
            *field = grid.field(goal, time);
        }
        if field.distance[start] == u32::MAX {
            return None;
        }
        let next = grid
            .neighbors(start)
            .filter(|i| field.distance[*i] < field.distance[start])
            .min_by_key(|i| field.distance[*i])
            .map(|i| grid.point(i))?;
        Some(if clear_line(map, from, next, enemy.r) {
            next
        } else {
            grid.point(start)
        })
    }
}
