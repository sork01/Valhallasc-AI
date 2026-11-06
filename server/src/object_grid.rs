//! A uniform grid over a map's obstacles, so collision and sight lines look only at what is near instead of scanning the whole
//! zone. Results are exactly those of the full scan (`grid_matches_the_full_scan` in model.rs): each cell lists its obstacles in
//! file order, and an obstacle is in every cell its bounding box touches. Built on first use; a map whose obstacle list is not the
//! one the grid was built from (tests and the kill-time harness edit theirs) falls back to the scan.
use crate::model::Obstacle;
use std::sync::OnceLock;

const CELL: f64 = 4.;
/// Covers rounding in the `p - radius` bounds: a query may only ever be too wide.
const PAD: f64 = 1e-6;

pub struct Grid {
    side: usize,
    /// Cell `c` lists `items[start[c]..start[c + 1]]`, ascending.
    start: Vec<u32>,
    items: Vec<u32>,
    source: (usize, usize),
}

fn extent(o: &Obstacle) -> (f64, f64) {
    if o.width > 0. && o.depth > 0. {
        (o.width / 2., o.depth / 2.)
    } else {
        (o.r, o.r)
    }
}

impl Grid {
    fn new(objects: &[Obstacle], size: u32) -> Self {
        let side = (size as f64 / CELL).ceil() as usize + 1;
        let cell = |v: f64| ((v / CELL).floor() as isize).clamp(0, side as isize - 1) as usize;
        let span = |o: &Obstacle| {
            let (hx, hy) = extent(o);
            (
                cell(o.x - hx),
                cell(o.x + hx),
                cell(o.y - hy),
                cell(o.y + hy),
            )
        };
        let mut start = vec![0u32; side * side + 1];
        for o in objects {
            let (x0, x1, y0, y1) = span(o);
            for y in y0..=y1 {
                for x in x0..=x1 {
                    start[y * side + x + 1] += 1;
                }
            }
        }
        for c in 1..start.len() {
            start[c] += start[c - 1];
        }
        let mut next = start.clone();
        let mut items = vec![0u32; start[side * side] as usize];
        for (id, o) in objects.iter().enumerate() {
            let (x0, x1, y0, y1) = span(o);
            for y in y0..=y1 {
                for x in x0..=x1 {
                    items[next[y * side + x] as usize] = id as u32;
                    next[y * side + x] += 1;
                }
            }
        }
        Self {
            side,
            start,
            items,
            source: (objects.as_ptr() as usize, objects.len()),
        }
    }
    fn cell(&self, v: f64) -> usize {
        ((v / CELL).floor() as isize).clamp(0, self.side as isize - 1) as usize
    }
    fn list(&self, x: usize, y: usize) -> &[u32] {
        let c = y * self.side + x;
        &self.items[self.start[c] as usize..self.start[c + 1] as usize]
    }
    /// Obstacles whose bounding box may touch the box, numbers ascending and from `from` on, into `out`.
    pub fn in_box(&self, x0: f64, y0: f64, x1: f64, y1: f64, from: u32, out: &mut Vec<u32>) {
        out.clear();
        let (cx0, cx1) = (self.cell(x0 - PAD), self.cell(x1 + PAD));
        let (cy0, cy1) = (self.cell(y0 - PAD), self.cell(y1 + PAD));
        for y in cy0..=cy1 {
            for x in cx0..=cx1 {
                let list = self.list(x, y);
                let skip = list.partition_point(|id| *id < from);
                out.extend_from_slice(&list[skip..]);
            }
        }
        if cx0 != cx1 || cy0 != cy1 {
            out.sort_unstable();
            out.dedup();
        }
    }
    /// True if `hit` is true for any obstacle near the segment. Walks the cell columns the segment crosses, so a long sight line
    /// does not pay for the whole box around it. An obstacle may be offered more than once.
    pub fn along(
        &self,
        (ax, ay): (f64, f64),
        (bx, by): (f64, f64),
        radius: f64,
        mut hit: impl FnMut(u32) -> bool,
    ) -> bool {
        let reach = radius + PAD;
        let (dx, dy) = (bx - ax, by - ay);
        let (c0, c1) = (self.cell(ax.min(bx) - reach), self.cell(ax.max(bx) + reach));
        for cx in c0..=c1 {
            // The part of the segment within `reach` of this column; the edge columns also hold what lies outside the grid.
            let left = if cx == 0 {
                f64::NEG_INFINITY
            } else {
                cx as f64 * CELL - reach
            };
            let right = if cx == self.side - 1 {
                f64::INFINITY
            } else {
                (cx + 1) as f64 * CELL + reach
            };
            let (t0, t1) = if dx.abs() < 1e-12 {
                (0., 1.)
            } else {
                let (u, v) = ((left - ax) / dx, (right - ax) / dx);
                (u.min(v).clamp(0., 1.), u.max(v).clamp(0., 1.))
            };
            let (ya, yb) = (ay + t0 * dy, ay + t1 * dy);
            for cy in self.cell(ya.min(yb) - reach)..=self.cell(ya.max(yb) + reach) {
                if self.list(cx, cy).iter().any(|id| hit(*id)) {
                    return true;
                }
            }
        }
        false
    }
}

/// A map's grid. Cloning a map (private dungeon copies) starts empty: the copy builds its own on first use.
#[derive(Default)]
pub struct GridSlot(OnceLock<Grid>);

impl Clone for GridSlot {
    fn clone(&self) -> Self {
        Self::default()
    }
}

impl GridSlot {
    pub fn get(&self, objects: &[Obstacle], size: u32) -> Option<&Grid> {
        let grid = self.0.get_or_init(|| Grid::new(objects, size));
        (grid.source == (objects.as_ptr() as usize, objects.len())).then_some(grid)
    }
}
