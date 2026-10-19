//! How a fighter who is not at a keyboard answers a boss's mechanics (`BOSSMECH-MERC`, `BOSSMECH-HARNESS`).
//!
//! The hired mercenaries and the dungeon harness's bots ask the same question here and get the same answer, so "a hired
//! party beats each mechanic as often as a human one" and "the harness bots play it right" are one claim. The brain reads
//! the fight's own state (the danger query of `boss_mechanics.rs`) and returns where to stand, what to hit and whether to
//! hold fire; it never touches a player. It does what a careful player does, no more: step out of a telegraph, stand on
//! a safe island, spread when marked, ground a charge on a rod, hold a brazier that is out, hit a shield's helpers and a
//! friend's cocoon first, finish a divided boss's weaker half.
use super::*;

/// How many braziers a party keeps lit.
const KEEP_LIT: usize = 3;
/// Seconds of warning a moving hazard (turning spokes) is looked at ahead of the present.
const LOOK: f64 = 1.2;

/// What the brain asks of a fighter this tick.
#[derive(Clone, Debug, Default, PartialEq)]
pub(in crate::world) struct BossPlay {
    /// Walk here: out of a telegraph's way, to a rod or a brazier, away from friends while marked.
    pub goal: Option<Point>,
    /// Hit this instead of what was picked: a shield's helpers, a seed, a friend's cocoon, the weaker half of a divided boss.
    pub target: Option<usize>,
    /// Do not swing: the fighter is running to a rod or holding a brazier.
    pub hold_fire: bool,
    /// Stay exactly here (no walking to a target, no dash): the spot is safe from a wall or a spoke that is on its way.
    pub stay: bool,
}

impl World {
    /// The answer for `session`, or `None` when no boss fight runs where they are (or they are down or frozen).
    pub(in crate::world) fn boss_play(&mut self, session: u64) -> Option<BossPlay> {
        let Some((play, plan, station)) = self.think(session) else {
            self.boss.plans.remove(&session);
            self.boss.stations.remove(&session);
            self.boss.halves.remove(&session);
            return None;
        };
        match play.target {
            Some(t)
                if self
                    .boss
                    .fights
                    .values()
                    .any(|f| f.partner.is_some() && (f.boss == t || f.partner == Some(t))) =>
            {
                self.boss.halves.insert(session, t);
            }
            _ => {
                self.boss.halves.remove(&session);
            }
        }
        match plan {
            Some(g) => {
                self.boss.plans.insert(session, g);
            }
            None => {
                self.boss.plans.remove(&session);
            }
        }
        match station {
            Some(g) => {
                self.boss.stations.insert(session, g);
            }
            None => {
                self.boss.stations.remove(&session);
            }
        }
        Some(play)
    }

    /// The brain: the answer, and the place the fighter is running to (kept from one tick to the next).
    fn think(&self, session: u64) -> Option<(BossPlay, Option<Point>, Option<Point>)> {
        let p = self.players.get(&session)?;
        if p.character.hp <= 0. || p.frozen {
            return None;
        }
        let zone = p.character.zone;
        let me = p.character.point();
        let fight = self
            .boss
            .fights
            .values()
            .filter(|f| f.zone == zone)
            .min_by(|a, b| {
                self.slimes[a.boss]
                    .point()
                    .distance(me)
                    .total_cmp(&self.slimes[b.boss].point().distance(me))
            })?;
        let def = self.boss.table.get(&self.slimes[fight.boss].kind)?;
        let mates = self.mech_players(zone);
        let mut play = BossPlay {
            target: self.play_target(fight, session, me, &mates),
            ..BossPlay::default()
        };
        let brazier = self.brazier_goal(fight, session, &mates);
        // Running is not swinging: a dash toward the boss would undo the step out of its telegraph. A place chosen to
        // run to is kept until it is reached or goes bad, or two equally near places would be swapped every tick.
        // Walls and spokes are dodged by planning ahead; everything else by stepping to the nearest safe place.
        let moving = Self::has_moving(fight);
        let planned = if moving {
            self.plan_moving(zone, fight, def, me)
        } else {
            Err(())
        };
        if matches!(planned, Ok(None)) {
            play.stay = true;
        }
        // Standing right on the edge of a telegraph counts as standing in it: a step of the boss or a rounding error
        // is all it takes.
        let on_edge = |p: Point| {
            self.bot_threat(zone, session, p, LOOK).is_some()
                || [(0.5, 0.), (-0.5, 0.), (0., 0.5), (0., -0.5)]
                    .iter()
                    .any(|(dx, dy)| {
                        self.bot_threat(
                            zone,
                            session,
                            Point {
                                x: p.x + dx,
                                y: p.y + dy,
                            },
                            LOOK,
                        )
                        .is_some()
                    })
        };
        let flee = if let Ok(goal) = planned {
            goal
        } else if on_edge(me) {
            self.boss
                .plans
                .get(&session)
                .copied()
                .filter(|g| {
                    g.distance(me) > 0.3 && self.bot_threat(zone, session, *g, LOOK).is_none()
                })
                .or_else(|| self.flee_spot(zone, fight, session, me))
        } else {
            None
        };
        // A kill zone that is up (the dark of the Longest Night) is no time to walk off safe ground to light a brazier.
        let zone_up = fight
            .live
            .iter()
            .any(|l| matches!(l, Live::Zone(z) if z.phase != ZPhase::Linger || z.left > 0.));
        if let Some(spot) = flee {
            play.goal = Some(spot);
            play.hold_fire = true;
        } else if fight.live.iter().any(|l| match l {
            Live::Zone(z) => z.phase != ZPhase::Linger || z.left > 0.,
            Live::Mark(_) | Live::Puddle(_) => true,
            _ => false,
        }) && self
            .spread_spot(zone, fight, def, session, me, &mates)
            .is_none()
            && Self::rod_goal(fight, session, me).is_none()
            && (brazier.is_none() || zone_up)
        {
            // A telegraph is up and this place is outside it: stay out until it has landed.
            play.stay = true;
        } else if let Some(spot) = self.spread_spot(zone, fight, def, session, me, &mates) {
            play.goal = Some(spot);
            play.hold_fire = true;
        } else if let Some(spot) = self.bridge_station(fight, def, play.target, me) {
            play.goal = Some(spot);
        } else if let Some(rod) = Self::rod_goal(fight, session, me) {
            play.goal = Some(rod);
            play.hold_fire = true;
        } else if let Some(b) = brazier {
            play.goal = Some(b);
            play.hold_fire = true;
        }
        let station = if play.goal.is_some() && !play.hold_fire {
            None
        } else {
            brazier
        };
        Some((play, flee, station))
    }

    fn free_ground(&self, zone: usize, p: Point) -> bool {
        let mut q = p;
        self.maps[zone].collide(&mut q, PLAYER_RADIUS);
        q.distance(p) < 1e-6
    }

    /// The nearest safe place to the boss within reach of a telegraph's remaining time, when `me` is not safe. When
    /// nothing is safe (two walls with their gaps on opposite sides), the place that stays safe longest: the next
    /// tick moves on from it again.
    fn flee_spot(&self, zone: usize, fight: &Fight, session: u64, me: Point) -> Option<Point> {
        let left = self.bot_threat(zone, session, me, LOOK)?;
        let boss = self.slimes[fight.boss].point();
        let reach = (bm::SLOWEST_PLAYER_SPEED * left.max(0.5) + 1.).min(16.);
        let arena = fight.arena;
        // (a thin line: a hero pressed against a wall fails the full-width test in every direction and would be left
        // with nowhere to run)
        let open_at =
            |p: Point| self.free_ground(zone, p) && self.maps[zone].line_clear(me, p, 0.05);
        let open = |p: Point| {
            p.x >= arena.x0 + 0.5
                && p.x <= arena.x1 - 0.5
                && p.y >= arena.y0 + 0.5
                && p.y <= arena.y1 - 0.5
                && open_at(p)
        };
        // Against a dark that kills outside the braziers' light the way out is a burning brazier, which a ring of samples
        // misses when it is far off: go to the nearest one that is still lit when the dark falls and that can be reached in
        // time. (The dead no longer come back to try again, so a fighter left in the dark is a fighter lost.)
        let mut lights: Vec<Point> = fight
            .lit
            .iter()
            .flat_map(|g| g.points.iter().map(move |l| (l, g.r)))
            .filter(|(l, _)| l.lit_left > left)
            .flat_map(|(l, r)| {
                // a brazier is a solid prop: stand beside it, well inside its light
                [0.5, 0.75].into_iter().flat_map(move |k| {
                    (0..12).map(move |i| {
                        let a = f64::from(i) / 12. * std::f64::consts::TAU;
                        Point {
                            x: l.at.x + r * k * a.cos(),
                            y: l.at.y + r * k * a.sin(),
                        }
                    })
                })
            })
            .filter(|p| p.distance(me) <= bm::SLOWEST_PLAYER_SPEED * left * 0.9 && open_at(*p))
            .collect();
        lights.sort_by(|a, b| a.distance(me).total_cmp(&b.distance(me)));
        if let Some(at) = lights
            .into_iter()
            .find(|at| self.bot_threat(zone, session, *at, LOOK).is_none())
        {
            return Some(at);
        }
        let mut longest: Option<(f64, f64, Point)> = None;
        let mut found: Option<(f64, Point)> = None;
        let mut found_ring: Option<f64> = None;
        let mut ring = 1.;
        while ring <= reach {
            let mut best: Option<(f64, Point)> = None;
            for k in 0..24 {
                let a = f64::from(k) / 24. * std::f64::consts::TAU;
                let p = Point {
                    x: me.x + ring * a.cos(),
                    y: me.y + ring * a.sin(),
                };
                if !open(p) {
                    continue;
                }
                match self.bot_threat(zone, session, p, LOOK) {
                    None => {
                        // a margin, so the place is not on the very edge of what is dangerous
                        let edge = [(0.7, 0.), (-0.7, 0.), (0., 0.7), (0., -0.7)].iter().any(
                            |(dx, dy)| {
                                self.bot_threat(
                                    zone,
                                    session,
                                    Point {
                                        x: p.x + dx,
                                        y: p.y + dy,
                                    },
                                    LOOK,
                                )
                                .is_some()
                            },
                        );
                        // Near the boss, except against a divided boss: there the farther from the bridge between the
                        // bodies the better (a line that sweeps catches whoever stands at its edge).
                        let d = match fight.partner {
                            Some(partner) => -bm::segment_distance(
                                p,
                                self.slimes[fight.boss].point(),
                                self.slimes[partner].point(),
                            ),
                            None => p.distance(boss),
                        };
                        if !edge && best.is_none_or(|(b, _)| d < b) {
                            best = Some((d, p));
                        }
                    }
                    Some(t) => {
                        if t > left + 0.3
                            && longest
                                .is_none_or(|(l, d, _)| t > l + 0.05 || (t > l - 0.05 && ring < d))
                        {
                            longest = Some((t, ring, p));
                        }
                    }
                }
            }
            if let Some((_, p)) = best {
                if fight.partner.is_none() {
                    return Some(p);
                }
                found_ring.get_or_insert(ring);
                found = found
                    .filter(|(b, _): &(f64, Point)| *b <= best.unwrap().0)
                    .or(best);
            }
            if found_ring.is_some_and(|r| ring >= r + 3.) {
                return found.map(|(_, p)| p);
            }
            ring += 1.;
        }
        found.map(|(_, p)| p).or(longest.map(|(_, _, p)| p))
    }

    /// A marked fighter goes where the mark (a ring, or a beam that bounces) misses their friends.
    fn spread_spot(
        &self,
        zone: usize,
        fight: &Fight,
        def: &BossDef,
        session: u64,
        me: Point,
        mates: &[(u64, Point)],
    ) -> Option<Point> {
        let ml = fight.live.iter().find_map(|l| match l {
            Live::Mark(m) if !m.gap && m.targets.contains(&session) => Some(m),
            _ => None,
        })?;
        let Block::Mark(k) = &def.mechanics[ml.mech].block else {
            return None;
        };
        let others: Vec<Point> = mates
            .iter()
            .filter(|(s, _)| *s != session)
            .map(|(_, p)| *p)
            .collect();
        if others.is_empty() {
            return None;
        }
        let boss = self.slimes[fight.boss].point();
        let margin = |p: Point| -> f64 {
            match k.effect {
                MarkEffect::Burst { r } => {
                    others
                        .iter()
                        .map(|o| o.distance(p))
                        .fold(f64::MAX, f64::min)
                        - r
                }
                MarkEffect::Beam { bounces, width } => {
                    let path = bm::beam_path(boss, p, fight.arena, bounces);
                    others
                        .iter()
                        .flat_map(|o| {
                            path.windows(2)
                                .map(|w| bm::segment_distance(*o, w[0], w[1]))
                                .collect::<Vec<_>>()
                        })
                        .fold(f64::MAX, f64::min)
                        - width / 2.
                        - BODY
                }
            }
        };
        let arena = fight.arena;
        let reach = (bm::SLOWEST_PLAYER_SPEED * ml.left.max(0.5) * 0.9).min(18.);
        let mut best = (margin(me), me);
        let mut ring = 0.;
        while ring <= reach {
            for k in 0..(if ring == 0. { 1 } else { 20 }) {
                let a = f64::from(k) / 20. * std::f64::consts::TAU;
                let p = Point {
                    x: me.x + ring * a.cos(),
                    y: me.y + ring * a.sin(),
                };
                if p.x < arena.x0 + 0.5
                    || p.x > arena.x1 - 0.5
                    || p.y < arena.y0 + 0.5
                    || p.y > arena.y1 - 0.5
                    || !self.free_ground(zone, p)
                    || !self.maps[zone].line_clear(me, p, PLAYER_RADIUS)
                {
                    continue;
                }
                let m = margin(p);
                if m > best.0 + 0.05 {
                    best = (m, p);
                }
            }
            if best.0 >= 1.5 {
                break;
            }
            ring += 1.;
        }
        (best.1.distance(me) > 0.2).then_some(best.1)
    }

    /// Against a divided boss the lethal bridge joins the two bodies: fight a body from its far side, away from the line.
    fn bridge_station(
        &self,
        fight: &Fight,
        def: &BossDef,
        target: Option<usize>,
        me: Point,
    ) -> Option<Point> {
        let partner = fight.partner?;
        let bridge = def.mechanics.iter().find_map(|m| match &m.block {
            Block::Split(s) if s.bridge > 0. => Some(s.bridge),
            _ => None,
        })?;
        let body = target.filter(|t| *t == fight.boss || *t == partner)?;
        let other = if body == fight.boss {
            partner
        } else {
            fight.boss
        };
        if self.slimes[body].dead || self.slimes[other].dead || !fight.downed.is_empty() {
            return None;
        }
        let (at, from) = (self.slimes[body].point(), self.slimes[other].point());
        let away = from.direction(at);
        if away.x == 0. && away.y == 0. {
            return None;
        }
        let reach = self.slimes[body].r + bridge + 1.2;
        let station = Point {
            x: at.x + away.x * reach,
            y: at.y + away.y * reach,
        };
        (station.distance(me) > 0.8).then_some(station)
    }

    /// A fighter whose charge of Static is near the limit walks to the nearest ready rod (else the one that wakes first).
    fn rod_goal(fight: &Fight, session: u64, me: Point) -> Option<Point> {
        let st = fight.stat.as_ref()?;
        if st.grounded.contains_key(&session)
            || st.charges.get(&session).copied().unwrap_or(0) < st.warn_at
        {
            return None;
        }
        st.rods
            .iter()
            .filter(|r| r.dark_left <= 0.)
            .map(|r| r.at)
            .min_by(|a, b| a.distance(me).total_cmp(&b.distance(me)))
            .or_else(|| {
                st.rods
                    .iter()
                    .min_by(|a, b| a.dark_left.total_cmp(&b.dark_left))
                    .map(|r| r.at)
            })
    }

    /// When fewer than `KEEP_LIT` braziers burn or are being lit, a fighter takes the nearest dark one nobody has taken
    /// and keeps it until it burns: the claim is kept between ticks, or two fighters would swap places for ever.
    fn brazier_goal(&self, fight: &Fight, session: u64, mates: &[(u64, Point)]) -> Option<Point> {
        let me = mates.iter().find(|(s, _)| *s == session)?.1;
        for g in &fight.lit {
            let dark = |l: &Lit| l.lit_left <= 0.;
            let claimed = |at: Point, by_other: bool| {
                self.boss.stations.iter().any(|(s, c)| {
                    (!by_other || *s != session)
                        && c.distance(at) < 0.1
                        && mates.iter().any(|(m, _)| m == s)
                })
            };
            // my claim, while the place is still dark
            if let Some(mine) = self.boss.stations.get(&session)
                && g.points
                    .iter()
                    .any(|l| dark(l) && l.at.distance(*mine) < 0.1)
            {
                return Some(*mine);
            }
            let burning = g.points.iter().filter(|l| !dark(l)).count();
            let taken = g
                .points
                .iter()
                .filter(|l| dark(l) && claimed(l.at, true))
                .count();
            if burning + taken >= KEEP_LIT {
                continue;
            }
            if let Some(l) = g
                .points
                .iter()
                .filter(|l| dark(l) && !claimed(l.at, true))
                .min_by(|a, b| a.at.distance(me).total_cmp(&b.at.distance(me)))
            {
                // only the nearest of the free fighters goes
                let nearer = mates.iter().any(|(s, p)| {
                    *s != session
                        && p.distance(l.at) < me.distance(l.at)
                        && !self.boss.stations.contains_key(s)
                });
                if !nearer {
                    return Some(l.at);
                }
            }
        }
        None
    }

    /// Whether a fight has hazards that move on a schedule (walls, turning spokes).
    fn has_moving(fight: &Fight) -> bool {
        !fight.spokes.is_empty() || fight.live.iter().any(|l| matches!(l, Live::Walls(_)))
    }

    /// Dodging walls and spokes by search through space and time: a grid of one-tile cells, steps of a quarter second.
    /// `Ok(None)`: staying put is safe for the whole horizon; `Ok(Some(p))`: run to `p` (a little way along a path that
    /// survives it); `Err`: nothing survives (the caller falls back on the greedy answer).
    fn plan_moving(
        &self,
        zone: usize,
        fight: &Fight,
        def: &BossDef,
        me: Point,
    ) -> Result<Option<Point>, ()> {
        const DT: f64 = 0.25;
        const CELL: f64 = 0.5;
        const PAD: f64 = 0.5;
        // How far a fighter can get in one step at the slowest class's speed, in cells.
        const REACH_CELLS: i64 = 2;
        struct WallsAt {
            warn: f64,
            speed: f64,
            thickness: f64,
            gap: f64,
            walls: Vec<(Side, f64, f64)>,
        }
        struct SpokesAt {
            angle: f64,
            dir: f64,
            reverse_in: f64,
            reverse_every: f64,
            rate: f64,
            count: u32,
            width: f64,
            length: f64,
        }
        let mut walls: Vec<WallsAt> = vec![];
        let mut spokes: Vec<SpokesAt> = vec![];
        for live in &fight.live {
            if let Live::Walls(wl) = live
                && let Block::Sweep(sw) = &def.mechanics[wl.mech].block
                && let SweepKind::Walls {
                    speed,
                    thickness,
                    gap,
                    ..
                } = &sw.kind
            {
                walls.push(WallsAt {
                    warn: wl.warn_left.max(0.),
                    speed: *speed,
                    thickness: *thickness + PAD * 2.,
                    gap: (*gap - PAD * 2.).max(1.),
                    walls: wl.walls.iter().map(|w| (w.side, w.pos, w.gap_at)).collect(),
                });
            }
        }
        for sp in &fight.spokes {
            if let Block::Sweep(sw) = &def.mechanics[sp.mech].block
                && let SweepKind::Spokes {
                    count,
                    width,
                    deg_per_s,
                    reverse_every,
                    length,
                    ..
                } = sw.kind
            {
                spokes.push(SpokesAt {
                    angle: sp.angle,
                    dir: sp.dir,
                    reverse_in: sp.reverse_in,
                    reverse_every,
                    rate: deg_per_s.to_radians(),
                    count,
                    width: width + PAD * 2.,
                    length,
                });
            }
        }
        if walls.is_empty() && spokes.is_empty() {
            return Ok(None);
        }
        let arena = fight.arena;
        let centre = arena.centre();
        let horizon = walls
            .iter()
            .map(|w| w.warn + (arena.width().max(arena.height()) + w.thickness) / w.speed + 0.5)
            .fold(3., f64::max)
            .min(10.);
        let steps = (horizon / DT).ceil() as usize;
        let hazard = |p: Point, t: f64| -> bool {
            for w in &walls {
                for (side, pos, gap_at) in &w.walls {
                    let dir = match side {
                        Side::West | Side::North => 1.,
                        Side::East | Side::South => -1.,
                    };
                    let at = WallLive {
                        side: *side,
                        pos: pos + dir * w.speed * (t - w.warn).max(0.),
                        gap_at: *gap_at,
                    };
                    if Self::wall_hits(arena, w.thickness, w.gap, &at, p) {
                        return true;
                    }
                }
            }
            for sp in &spokes {
                // the angle after `t` seconds, turning back every `reverse_every`
                let (mut angle, mut dir, mut next, mut left) = (sp.angle, sp.dir, sp.reverse_in, t);
                while left > 0. {
                    let run = if sp.reverse_every > 0. {
                        left.min(next.max(0.))
                    } else {
                        left
                    };
                    angle += dir * sp.rate * run;
                    left -= run;
                    if sp.reverse_every > 0. && left > 0. {
                        dir = -dir;
                        next = sp.reverse_every;
                    }
                }
                let hit = (0..sp.count).any(|n| {
                    let a = angle + f64::from(n) * std::f64::consts::TAU / f64::from(sp.count);
                    let tip = Point {
                        x: centre.x + a.cos() * sp.length,
                        y: centre.y + a.sin() * sp.length,
                    };
                    bm::segment_distance(p, centre, tip) <= sp.width / 2. + BODY
                });
                if hit {
                    return true;
                }
            }
            false
        };
        let cols = (arena.width() / CELL).floor() as i64;
        let rows = (arena.height() / CELL).floor() as i64;
        if cols < 2 || rows < 2 {
            return Err(());
        }
        let centre_of = |i: i64| Point {
            x: arena.x0 + (i % cols) as f64 * CELL + CELL / 2.,
            y: arena.y0 + (i / cols) as f64 * CELL + CELL / 2.,
        };
        let n = (cols * rows) as usize;
        let free: Vec<bool> = (0..n as i64)
            .map(|i| self.free_ground(zone, centre_of(i)))
            .collect();
        let start = {
            let cx = (((me.x - arena.x0) / CELL).floor() as i64).clamp(0, cols - 1);
            let cy = (((me.y - arena.y0) / CELL).floor() as i64).clamp(0, rows - 1);
            (cy * cols + cx) as usize
        };
        // Staying where they stand: does it survive the whole horizon?
        if (1..=steps).all(|k| !hazard(me, k as f64 * DT)) && !hazard(me, 0.) {
            return Ok(None);
        }
        let mut parent: Vec<Vec<i32>> = vec![vec![-2; n]; steps + 1];
        parent[0][start] = -1;
        for k in 0..steps {
            let t = (k + 1) as f64 * DT;
            // a cell is safe at the step if its centre is (checked once per layer)
            let safe: Vec<bool> = (0..n)
                .map(|c| free[c] && !hazard(centre_of(c as i64), t))
                .collect();
            // Staying put first, so a path moves only as far as it has to; then every step a fighter can take.
            for c in 0..n {
                if parent[k][c] != -2 && safe[c] {
                    parent[k + 1][c] = c as i32;
                }
            }
            for c in 0..n {
                if parent[k][c] == -2 {
                    continue;
                }
                let (cx, cy) = ((c as i64) % cols, (c as i64) / cols);
                for dy in -REACH_CELLS..=REACH_CELLS {
                    for dx in -REACH_CELLS..=REACH_CELLS {
                        if ((dx * dx + dy * dy) as f64).sqrt() * CELL
                            > bm::SLOWEST_PLAYER_SPEED * DT
                        {
                            continue;
                        }
                        let (nx, ny) = (cx + dx, cy + dy);
                        if nx < 0 || ny < 0 || nx >= cols || ny >= rows {
                            continue;
                        }
                        let nc = (ny * cols + nx) as usize;
                        if safe[nc] && parent[k + 1][nc] == -2 {
                            // the middle of the step must be safe too, or a diagonal cuts through a wall
                            let (a, b) = (centre_of(c as i64), centre_of(nc as i64));
                            let mid = Point {
                                x: (a.x + b.x) / 2.,
                                y: (a.y + b.y) / 2.,
                            };
                            if !hazard(mid, t - DT / 2.) {
                                parent[k + 1][nc] = c as i32;
                            }
                        }
                    }
                }
            }
        }
        let boss = self.slimes[fight.boss].point();
        let Some(end) = (0..n).filter(|c| parent[steps][*c] != -2).min_by(|a, b| {
            centre_of(*a as i64)
                .distance(boss)
                .total_cmp(&centre_of(*b as i64).distance(boss))
        }) else {
            return Err(());
        };
        // Walk the path back to the second step and run there.
        let mut cell = end;
        let mut path = vec![end];
        for k in (1..=steps).rev() {
            cell = parent[k][cell] as usize;
            path.push(cell);
        }
        path.reverse();
        let goal = centre_of(path[1.min(path.len() - 1)] as i64);
        Ok((goal.distance(me) > 0.3).then_some(goal))
    }

    /// What to hit before the boss: a friend's cocoon, a shield's helpers, a seed, a helper that is coming for the
    /// fighter, the weaker half of a divided boss. `None`: the boss (or whatever the caller picked).
    fn play_target(
        &self,
        fight: &Fight,
        session: u64,
        me: Point,
        mates: &[(u64, Point)],
    ) -> Option<usize> {
        let alive = |s: &usize| !self.slimes[*s].dead;
        let dist = |s: &usize| self.slimes[*s].point().distance(me);
        let rank = {
            let mut ids: Vec<u64> = mates.iter().map(|(s, _)| *s).collect();
            ids.sort_unstable();
            ids.iter().position(|s| *s == session).unwrap_or(0)
        };
        if let Some(cocoon) = fight
            .frozen
            .iter()
            .filter(|(s, _)| **s != session)
            .map(|(_, f)| f.cocoon)
            .filter(alive)
            .min_by(|a, b| dist(a).total_cmp(&dist(b)))
        {
            return Some(cocoon);
        }
        if let Some(shield) = &fight.shield {
            let mut left: Vec<usize> = shield.adds.iter().copied().filter(alive).collect();
            left.sort_unstable();
            if !left.is_empty() {
                return Some(left[rank % left.len()]);
            }
        }
        let mut seeds: Vec<usize> = fight.blooms.iter().map(|b| b.slot).filter(alive).collect();
        seeds.sort_unstable();
        if !seeds.is_empty() {
            return Some(seeds[rank % seeds.len()]);
        }
        if let Some(helper) = fight
            .woken
            .iter()
            .copied()
            .filter(|s| {
                alive(s) && !fight.still.contains(s) && Some(*s) != fight.partner && dist(s) <= 7.
            })
            .min_by(|a, b| dist(a).total_cmp(&dist(b)))
        {
            return Some(helper);
        }
        if let Some(partner) = fight.partner {
            let open = |s: &usize| alive(s) && !fight.downed.contains_key(s);
            let hp = |s: &usize| self.slimes[*s].hp;
            // Stay on the half already chosen until the other has a fifth more health: the one with more health left is
            // the one to hit so the two come down together, but a choice made again with every blow sends the whole party
            // back and forth across the bridge of light.
            if let Some(kept) = self
                .boss
                .halves
                .get(&session)
                .copied()
                .filter(|h| (*h == fight.boss || *h == partner) && open(h))
                && let Some(other) = [fight.boss, partner].into_iter().find(|s| *s != kept)
                && (!open(&other) || hp(&other) <= hp(&kept) * 1.2)
            {
                return Some(kept);
            }
            return [fight.boss, partner]
                .into_iter()
                .filter(open)
                // the one with more health left, so the two come down together
                .max_by(|a, b| hp(a).total_cmp(&hp(b)));
        }
        None
    }
}
