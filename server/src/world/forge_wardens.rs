//! Wardens five through nine. Per-fight state is discarded on evade/wipe/reset.
//! Pickup, passing, counting, damage and timing are based only on server actors.
use super::play::BossPlay;
use super::*;

pub(super) struct ForgeLive {
    pub(super) mech: usize,
    id: u64,
    left: f64,
    elapsed: f64,
    stage: Stage,
}
enum Stage {
    Valves {
        progress: [f64; 2],
        assignments: BTreeMap<u64, usize>,
    },
    Relay {
        brands: Vec<Brand>,
        immune: BTreeMap<u64, f64>,
    },
    Grid {
        beat: usize,
        offset: usize,
        players: BTreeSet<u64>,
    },
    Carry {
        available: Vec<bool>,
        carriers: BTreeMap<u64, usize>,
        throws: Vec<f64>,
        quenched: f64,
    },
    Reflect,
}
struct Brand {
    bearer: u64,
    fuse: f64,
    passed: f64,
    last_at: Point,
    handoffs: usize,
}
fn pt(p: [f64; 2]) -> Point {
    Point { x: p[0], y: p[1] }
}
fn within(a: Rect, p: Point) -> bool {
    p.x >= a.x0 && p.x <= a.x1 && p.y >= a.y0 && p.y <= a.y1
}
fn centre(a: Rect) -> Point {
    Point {
        x: (a.x0 + a.x1) * 0.5,
        y: (a.y0 + a.y1) * 0.5,
    }
}
fn live_forge(f: &Fight) -> impl Iterator<Item = &ForgeLive> {
    f.live.iter().filter_map(|l| {
        if let Live::Forge(v) = l {
            Some(v)
        } else {
            None
        }
    })
}
fn grid_cell(a: Rect, p: Point) -> (usize, usize) {
    (
        (((p.x - a.x0) / (a.x1 - a.x0) * 6.).floor() as usize).min(5),
        (((p.y - a.y0) / (a.y1 - a.y0) * 6.).floor() as usize).min(5),
    )
}
fn grid_number(x: usize, y: usize, offset: usize) -> usize {
    (x + 2 * (y % 2) + offset) % 4 + 1
}

impl World {
    fn forge_members(&self, f: &Fight) -> Vec<(u64, Point)> {
        self.mech_players(f.zone)
            .into_iter()
            .filter(|(s, p)| {
                within(f.arena, *p)
                    || self.slimes[f.boss]
                        .contributors
                        .contains(&self.players[s].character.id)
            })
            .collect()
    }
    fn forge_member_position(&self, f: &Fight, s: u64) -> Option<Point> {
        self.mech_players(f.zone)
            .into_iter()
            .find(|(id, _)| *id == s)
            .map(|(_, p)| p)
    }
    fn forge_joined(&self, f: &Fight, session: u64, at: Point) -> bool {
        within(f.arena, at)
            || self.slimes[f.boss]
                .contributors
                .contains(&self.players[&session].character.id)
            || live_forge(f).any(|l| match &l.stage {
                Stage::Valves { assignments, .. } => assignments.contains_key(&session),
                Stage::Relay { brands, .. } => brands.iter().any(|b| b.bearer == session),
                Stage::Grid { players, .. } => players.contains(&session),
                Stage::Carry { carriers, .. } => carriers.contains_key(&session),
                Stage::Reflect => false,
            })
    }
    pub(super) fn tick_forge_continuous(
        &mut self,
        f: &mut Fight,
        i: usize,
        m: &Mechanic,
        share: f64,
    ) {
        if f.live.iter().any(|l| l.mech() == i) {
            return;
        }
        match &m.block {
            Block::Valves(v) => {
                let Some(n) =
                    v.at.iter()
                        .enumerate()
                        .find(|(n, h)| share <= **h && f.fired[i] & (1 << n) == 0)
                        .map(|(n, _)| n)
                else {
                    return;
                };
                f.fired[i] |= 1 << n;
                let mates = self.forge_members(f);
                let half = mates.len().div_ceil(2);
                let assignments =
                    raid_bosses::assign(&mates, &v.points, &[half, mates.len() - half]);
                let id = self.fresh_id();
                f.live.push(Live::Forge(ForgeLive {
                    mech: i,
                    id,
                    left: v.cast + v.duration,
                    elapsed: 0.,
                    stage: Stage::Valves {
                        progress: [0.; 2],
                        assignments,
                    },
                }));
                f.banner = Some((m.name.clone(), v.cast));
            }
            Block::Carry(c) => {
                let id = self.fresh_id();
                f.live.push(Live::Forge(ForgeLive {
                    mech: i,
                    id,
                    left: 0.,
                    elapsed: 0.,
                    stage: Stage::Carry {
                        available: vec![true; c.points.len()],
                        carriers: BTreeMap::new(),
                        throws: vec![],
                        quenched: 0.,
                    },
                }));
            }
            _ => {}
        }
    }
    pub(super) fn start_forge_cast(&mut self, f: &mut Fight, i: usize, m: &Mechanic) {
        let mates = self.forge_members(f);
        if mates.is_empty() {
            return;
        }
        let (cast, every, stage) = match &m.block {
            Block::Relay(r) => {
                let shift = (f.fired[i] as usize * 3) % mates.len();
                let brands = (0..r.count.min(mates.len()))
                    .map(|n| Brand {
                        bearer: mates[(shift + n) % mates.len()].0,
                        fuse: r.fuse,
                        passed: -100.,
                        last_at: mates[(shift + n) % mates.len()].1,
                        handoffs: 0,
                    })
                    .collect();
                (
                    r.cast,
                    r.every,
                    Stage::Relay {
                        brands,
                        immune: BTreeMap::new(),
                    },
                )
            }
            Block::Grid(g) => (
                g.cast,
                g.every,
                Stage::Grid {
                    beat: 0,
                    offset: (f.fired[i] as usize) % 4,
                    players: mates.iter().map(|(s, _)| *s).collect(),
                },
            ),
            Block::Reflect(r) => (r.cast, r.every, Stage::Reflect),
            _ => return,
        };
        f.fired[i] += 1;
        f.timer[i] = every;
        let id = self.fresh_id();
        f.live.push(Live::Forge(ForgeLive {
            mech: i,
            id,
            left: cast,
            elapsed: 0.,
            stage,
        }));
        f.banner = Some((m.name.clone(), cast));
        self.mech_event(f.zone, "cast", &m.name, self.slimes[f.boss].point(), cast);
    }
    pub(super) fn tick_forge_cast(
        &mut self,
        f: &mut Fight,
        m: &Mechanic,
        l: &mut ForgeLive,
    ) -> bool {
        l.elapsed += TICK;
        l.left -= TICK;
        match (&m.block, &mut l.stage) {
            (
                Block::Valves(v),
                Stage::Valves {
                    progress,
                    assignments,
                },
            ) => {
                self.hold_still(f.boss);
                if l.elapsed < v.cast {
                    return true;
                }
                let mates = self.forge_members(f);
                let mid = centre(f.arena).x;
                for (s, p) in &mates {
                    if (p.x - mid).abs() < 1. {
                        self.mech_kill(*s, &m.name, f.boss);
                    }
                }
                for (n, held) in progress.iter_mut().enumerate() {
                    let count = mates
                        .iter()
                        .filter(|(s, p)| {
                            self.players[s].character.hp > 0. && p.distance(pt(v.points[n])) <= v.r
                        })
                        .count();
                    if count >= v.need {
                        *held = (*held + TICK).min(v.hold);
                    } else {
                        *held = 0.;
                    }
                }
                if progress.iter().all(|p| *p + 1e-6 >= v.hold) {
                    return false;
                }
                if l.left > 1e-6 {
                    return true;
                }
                // Both valves are mandatory. An empty failed island must not let
                // everybody stack on the other valve and skip the split entirely.
                let victims: BTreeSet<_> = assignments
                    .keys()
                    .copied()
                    .chain(self.forge_members(f).iter().map(|(s, _)| *s))
                    .collect();
                for session in victims {
                    self.mech_kill(session, &m.name, f.boss);
                }
                false
            }
            (Block::Relay(r), Stage::Relay { brands, immune }) => {
                if l.elapsed < r.cast {
                    return true;
                }
                if l.elapsed >= r.cast + r.duration {
                    return false;
                }
                let mates = self.mech_players(f.zone);
                brands.retain(|b| mates.iter().any(|(s, _)| *s == b.bearer));
                immune.retain(|_, until| *until > l.elapsed);
                let mut exploded = vec![];
                for n in 0..brands.len() {
                    brands[n].fuse -= TICK;
                    let b = &brands[n];
                    let Some(at) = mates.iter().find(|(s, _)| *s == b.bearer).map(|(_, p)| *p)
                    else {
                        continue;
                    };
                    // Expiry is authoritative and cannot be rescued by a late touch.
                    if b.fuse <= 1e-6 {
                        #[cfg(test)]
                        eprintln!(
                            "[relay-expired] bearer={} at={at:?} travelled={:.2} handoffs={} eligible={:?}",
                            b.bearer,
                            at.distance(b.last_at),
                            b.handoffs,
                            mates
                                .iter()
                                .filter(|(s, _)| !immune.contains_key(s)
                                    && !brands.iter().any(|b| b.bearer == *s))
                                .collect::<Vec<_>>()
                        );
                        exploded.push((n, at));
                        continue;
                    }
                    if l.elapsed - b.passed < 1. || at.distance(b.last_at) < 2. {
                        continue;
                    }
                    let receiver = mates
                        .iter()
                        .filter(|(s, p)| {
                            *s != b.bearer
                                && !immune.contains_key(s)
                                && !brands.iter().any(|brand| brand.bearer == *s)
                                && at.distance(*p) <= r.touch
                        })
                        .min_by(|(sa, pa), (sb, pb)| {
                            at.distance(*pa)
                                .total_cmp(&at.distance(*pb))
                                .then(sa.cmp(sb))
                        })
                        .map(|(s, _)| *s);
                    if let Some(s) = receiver {
                        let old = brands[n].bearer;
                        immune.insert(old, l.elapsed + r.immunity);
                        let handoffs = brands[n].handoffs + 1;
                        brands[n] = Brand {
                            bearer: s,
                            fuse: r.fuse,
                            passed: l.elapsed,
                            last_at: at,
                            handoffs,
                        };
                        self.mech_event(f.zone, "brand_pass", &m.name, at, r.fuse);
                    }
                }
                for (n, at) in exploded.into_iter().rev() {
                    brands.remove(n);
                    for (s, p) in &mates {
                        if p.distance(at) <= r.blast {
                            self.mech_kill(*s, &m.name, f.boss);
                        }
                    }
                }
                !brands.is_empty()
            }
            (
                Block::Grid(g),
                Stage::Grid {
                    beat,
                    offset,
                    players,
                },
            ) => {
                players.extend(self.forge_members(f).iter().map(|(s, _)| *s));
                while *beat < 4 && l.elapsed + 1e-6 >= g.cast + *beat as f64 * 60. / g.bpm {
                    *beat += 1;
                    for (s, p) in self
                        .mech_players(f.zone)
                        .into_iter()
                        .filter(|(s, _)| players.contains(s))
                    {
                        let (x, y) = grid_cell(f.arena, p);
                        if !within(f.arena, p) || grid_number(x, y, *offset) == *beat {
                            self.mech_heavy(s, g.heavy, &m.name, f.boss);
                        }
                    }
                    self.mech_event(f.zone, "beat", &m.name, centre(f.arena), *beat as f64);
                }
                *beat < 4
            }
            (
                Block::Carry(c),
                Stage::Carry {
                    available,
                    carriers,
                    throws,
                    quenched,
                },
            ) => {
                // A fixed throwing target keeps all ten wells useful and makes the window readable.
                self.slimes[f.boss].set_root_left = HOLD;
                let mates = self.forge_members(f);
                let lost: Vec<_> = carriers
                    .iter()
                    .filter(|(s, _)| !mates.iter().any(|(id, _)| id == *s))
                    .map(|(s, n)| (*s, *n))
                    .collect();
                for (s, n) in lost {
                    carriers.remove(&s);
                    available[n] = true;
                }
                if *quenched > 0. {
                    *quenched = (*quenched - TICK).max(0.);
                    if *quenched <= 1e-6 {
                        available.fill(true);
                        carriers.clear();
                        throws.clear();
                    }
                    return true;
                }
                throws.retain(|t| l.elapsed - *t <= c.window);
                for (s, p) in &mates {
                    if carriers.contains_key(s) {
                        continue;
                    }
                    if let Some(n) = c
                        .points
                        .iter()
                        .enumerate()
                        .position(|(n, w)| available[n] && p.distance(pt(*w)) <= c.r)
                    {
                        available[n] = false;
                        carriers.insert(*s, n);
                    }
                }
                let boss = self.slimes[f.boss].point();
                let ready: Vec<_> = carriers
                    .keys()
                    .filter(|s| {
                        self.forge_member_position(f, **s)
                            .is_some_and(|p| p.distance(boss) <= c.throw_r)
                    })
                    .copied()
                    .collect();
                for s in ready {
                    carriers.remove(&s);
                    throws.push(l.elapsed);
                }
                if throws.len() >= c.need {
                    *quenched = c.quenched;
                    carriers.clear();
                    f.banner = Some(("Quenched! Strike now!".into(), c.quenched));
                    self.mech_event(f.zone, "quench", &m.name, boss, c.quenched);
                } else if carriers.is_empty() && available.iter().all(|a| !*a) && throws.is_empty()
                {
                    // A missed five-second window never makes a pull impossible.
                    available.fill(true);
                }
                true
            }
            (Block::Reflect(r), Stage::Reflect) => l.elapsed < r.cast + r.duration,
            _ => false,
        }
    }
    pub(super) fn forge_cap_damage(&self, f: &Fight, id: usize, damage: f64) -> f64 {
        if id != f.boss {
            return damage;
        }
        let def = &self.boss.table[&self.slimes[id].kind];
        for (i, m) in def.mechanics.iter().enumerate() {
            if let Block::Valves(v) = &m.block {
                for (n, threshold) in v.at.iter().enumerate() {
                    if f.fired[i] & (1 << n) == 0 {
                        return damage.min(
                            (self.slimes[id].hp - self.slimes[id].max_hp * threshold).max(0.),
                        );
                    }
                }
            }
        }
        damage
    }
    pub(super) fn forge_incoming_scale(&self, f: &Fight, id: usize) -> f64 {
        if id != f.boss {
            return 1.;
        }
        for l in live_forge(f) {
            match &l.stage {
                Stage::Valves { .. } => return 0.,
                Stage::Carry { quenched, .. } => return if *quenched > 0. { 2. } else { 0.5 },
                _ => {}
            }
        }
        1.
    }
    pub(in crate::world) fn forge_attack_scale(&self, boss: usize) -> f64 {
        self.boss.fights.get(&boss).map_or(1., |f| {
            if live_forge(f).any(|l| matches!(&l.stage,Stage::Carry{quenched,..} if *quenched<=0.))
            {
                2.
            } else {
                1.
            }
        })
    }
    pub(super) fn forge_reflect_hit(&mut self, boss: usize, session: u64) {
        let hit = self.boss.fights.get(&boss).and_then(|f| {
            let def = &self.boss.table[&self.slimes[boss].kind];
            live_forge(f).find_map(|l| match (&def.mechanics[l.mech].block, &l.stage) {
                (Block::Reflect(r), Stage::Reflect) if l.elapsed >= r.cast => {
                    Some((def.mechanics[l.mech].name.clone(), r.heavy))
                }
                _ => None,
            })
        });
        if let Some((name, heavy)) = hit {
            self.mech_heavy(session, heavy, &name, boss);
        }
    }
    pub(in crate::world) fn forge_carry_speed(&self, session: u64) -> f64 {
        self.boss
            .fights
            .values()
            .find_map(|f| {
                live_forge(f).find_map(|l| {
                    if let Stage::Carry { carriers, .. } = &l.stage
                        && carriers.contains_key(&session)
                        && let Block::Carry(c) =
                            &self.boss.table[&self.slimes[f.boss].kind].mechanics[l.mech].block
                    {
                        Some(c.speed)
                    } else {
                        None
                    }
                })
            })
            .unwrap_or(1.)
    }
    pub(super) fn forge_danger(
        &self,
        f: &Fight,
        m: &Mechanic,
        l: &ForgeLive,
        session: u64,
        at: Point,
        look: f64,
    ) -> Option<f64> {
        let actual = self.forge_member_position(f, session)?;
        if !self.forge_joined(f, session, actual) {
            return None;
        }
        match (&m.block, &l.stage) {
            (Block::Valves(v), Stage::Valves { progress, .. }) => {
                let side = usize::from(at.x >= centre(f.arena).x);
                if (at.x - centre(f.arena).x).abs() < 1. {
                    Some((v.cast - l.elapsed).max(0.))
                } else {
                    (progress[side] < v.hold && at.distance(pt(v.points[side])) > v.r)
                        .then_some(l.left)
                }
            }
            (Block::Relay(r), Stage::Relay { brands, .. }) => brands
                .iter()
                .filter_map(|b| {
                    let p = self.forge_member_position(f, b.bearer)?;
                    (p.distance(at) <= r.blast).then_some((r.cast - l.elapsed).max(0.) + b.fuse)
                })
                .min_by(f64::total_cmp),
            (Block::Grid(g), Stage::Grid { beat, offset, .. }) => {
                if !within(f.arena, at) {
                    return Some((g.cast + *beat as f64 * 60. / g.bpm - l.elapsed - look).max(0.));
                }
                let (x, y) = grid_cell(f.arena, at);
                let number = grid_number(x, y, *offset);
                (number > *beat).then_some(
                    (g.cast + (number - 1) as f64 * 60. / g.bpm - l.elapsed - look).max(0.),
                )
            }
            _ => None,
        }
    }
    fn relay_receiver(&self, f: &Fight, l: &ForgeLive, bearer: u64) -> Option<u64> {
        let Stage::Relay { brands, immune } = &l.stage else {
            return None;
        };
        // Reserve a different receiver per brand, rotating session order after every pass.
        let mates = self.forge_members(f);
        let mut used = BTreeSet::new();
        let mut urgent: Vec<_> = brands.iter().collect();
        urgent.sort_by(|a, b| a.fuse.total_cmp(&b.fuse).then(a.bearer.cmp(&b.bearer)));
        for b in urgent {
            let receiver = mates
                .iter()
                .filter(|(s, _)| {
                    !brands.iter().any(|b| b.bearer == *s)
                        && !used.contains(s)
                        && !immune.contains_key(s)
                })
                .min_by(|(sa, pa), (sb, pb)| {
                    let at = self.forge_member_position(f, b.bearer).unwrap();
                    pa.distance(at).total_cmp(&pb.distance(at)).then(
                        (u8::from(*sa <= b.bearer), *sa).cmp(&(u8::from(*sb <= b.bearer), *sb)),
                    )
                })
                .map(|(s, _)| *s);
            if let Some(s) = receiver {
                used.insert(s);
            }
            if b.bearer == bearer {
                return receiver;
            }
        }
        None
    }
    pub(super) fn forge_boss_play(
        &self,
        f: &Fight,
        def: &BossDef,
        session: u64,
    ) -> Option<BossPlay> {
        let me = self.forge_member_position(f, session)?;
        if !self.forge_joined(f, session, me) {
            return None;
        }
        for l in live_forge(f) {
            let m = &def.mechanics[l.mech];
            let goal = match (&m.block, &l.stage) {
                (Block::Valves(v), Stage::Valves { assignments, .. }) => {
                    pt(v.points[*assignments.get(&session)?])
                }
                (Block::Reflect(_), Stage::Reflect) => {
                    // Stop at the start of the warning so spells already in flight can finish.
                    return Some(BossPlay {
                        target: Some(f.boss),
                        hold_fire: true,
                        stay: true,
                        goal: None,
                    });
                }
                (Block::Relay(_), Stage::Relay { brands, .. }) => {
                    let mut meeting = None;
                    for (n, b) in brands.iter().enumerate() {
                        let receiver = self.relay_receiver(f, l, b.bearer);
                        if b.bearer == session || receiver == Some(session) {
                            let mid = centre(f.arena);
                            let mut goal = Point {
                                x: mid.x + (n as f64 - 1.) * 4.,
                                y: mid.y + if b.handoffs % 2 == 0 { 4. } else { -4. },
                            };
                            // A handoff can happen before its marked meeting point.
                            // Never wait there if it would fail the two-tile travel rule.
                            if goal.distance(b.last_at) < 2.5 {
                                goal.y = 2. * mid.y - goal.y;
                            }
                            meeting = Some(goal);
                            break;
                        }
                    }
                    meeting?
                }
                (Block::Grid(_), Stage::Grid { beat, offset, .. }) => {
                    // Stand beside a 1/2 boundary during the cue, cross it just after beat 1.
                    // The two centres are 0.5 tiles apart: reachable inside one 0.4-second beat.
                    let a = f.arena;
                    let dx = (a.x1 - a.x0) / 6.;
                    let dy = (a.y1 - a.y0) / 6.;
                    let mut best = None::<(f64, Point)>;
                    for y in 0..6 {
                        for x in 0..5 {
                            let n = grid_number(x, y, *offset);
                            let next = grid_number(x + 1, y, *offset);
                            if !((n == 1 && next == 2) || (n == 2 && next == 1)) {
                                continue;
                            }
                            let side = if *beat == 0 {
                                if n == 2 { -1. } else { 1. }
                            } else if n == 1 {
                                -1.
                            } else {
                                1.
                            };
                            let g = Point {
                                x: a.x0 + (x + 1) as f64 * dx + side * 0.25,
                                y: a.y0 + (y as f64 + 0.5) * dy,
                            };
                            let distance = g.distance(me);
                            if best.as_ref().is_none_or(|(d, _)| distance < *d) {
                                best = Some((distance, g));
                            }
                        }
                    }
                    best?.1
                }
                (
                    Block::Carry(c),
                    Stage::Carry {
                        available,
                        carriers,
                        quenched,
                        ..
                    },
                ) => {
                    if *quenched > 0. {
                        return None;
                    }
                    if carriers.contains_key(&session) {
                        self.slimes[f.boss].point()
                    } else {
                        // Assign from a stable session list, even after the first players collect theirs.
                        let members = self.forge_members(f);
                        let index = members.iter().position(|(s, _)| *s == session)?;
                        if available[index % c.points.len()] {
                            pt(c.points[index % c.points.len()])
                        } else if let Some((_, p)) = c
                            .points
                            .iter()
                            .enumerate()
                            .filter(|(n, _)| available[*n])
                            .min_by(|(_, a), (_, b)| {
                                me.distance(pt(**a)).total_cmp(&me.distance(pt(**b)))
                            })
                        {
                            pt(*p)
                        } else {
                            return None;
                        }
                    }
                }
                _ => continue,
            };
            return Some(BossPlay {
                goal: Some(goal),
                target: Some(f.boss),
                hold_fire: true,
                stay: me.distance(goal) < 0.12,
            });
        }
        None
    }
    pub(super) fn forge_cast_view(
        &self,
        f: &Fight,
        def: &BossDef,
        teles: &mut Vec<Value>,
        cast: &mut Value,
    ) {
        let circle = |p: Point, r: f64| json!({"t":"circle","x":p.x,"y":p.y,"r":r,"inner":0});
        for l in live_forge(f) {
            let m = &def.mechanics[l.mech];
            let mut tele = |suffix: usize,
                            color: &str,
                            shapes: Vec<Value>,
                            label: String,
                            left: f64,
                            total: f64,
                            extra: Value| {
                let mut v = json!({"id":format!("{}-{suffix}",l.id),"name":m.name,"tele":color,"dashed":color=="dashed line",
                    "shapes":shapes,"left":left.max(0.),"total":total,"label":label});
                if let Some(o) = extra.as_object() {
                    v.as_object_mut().unwrap().extend(o.clone());
                }
                teles.push(v);
            };
            match (&m.block, &l.stage) {
                (Block::Valves(v), Stage::Valves { progress, .. }) => {
                    *cast = json!({"name":m.name,"left":l.left.max(0.),"total":v.cast+v.duration});
                    let mid = centre(f.arena).x;
                    tele(
                        0,
                        "red",
                        vec![
                            json!({"t":"rect","x0":mid-1.,"x1":mid+1.,"y0":f.arena.y0,"y1":f.arena.y1}),
                        ],
                        "Lava divide".into(),
                        v.cast - l.elapsed,
                        v.cast,
                        json!({}),
                    );
                    let members = self.forge_members(f);
                    for (n, held) in progress.iter().enumerate() {
                        let count = members
                            .iter()
                            .filter(|(_, p)| p.distance(pt(v.points[n])) <= v.r)
                            .count();
                        tele(
                            n + 1,
                            "blue",
                            vec![circle(pt(v.points[n]), v.r)],
                            format!("Valve {}", n + 1),
                            l.left,
                            v.cast + v.duration,
                            json!({"need":v.need,"count":count,"progress":*held/v.hold,"held":held,"holdTotal":v.hold}),
                        );
                    }
                }
                (Block::Relay(r), Stage::Relay { brands, .. }) => {
                    let prep = (r.cast - l.elapsed).max(0.);
                    *cast = json!({"name":m.name,"left":(r.cast+r.duration-l.elapsed).max(0.),"total":r.cast+r.duration});
                    for (n, b) in brands.iter().enumerate() {
                        if let Some(p) = self.forge_member_position(f, b.bearer) {
                            let receiver = self.relay_receiver(f, l, b.bearer);
                            let ids = |s| self.players.get(&s).map(|p| p.character.id.clone());
                            tele(
                                n,
                                "red",
                                vec![circle(p, r.blast)],
                                format!("Brand {}", n + 1),
                                prep + b.fuse,
                                if prep > 0. { r.cast + r.fuse } else { r.fuse },
                                json!({"bearer":ids(b.bearer),"receiver":receiver.and_then(ids),"fuse":b.fuse}),
                            );
                            if let Some(q) = receiver.and_then(|s| self.forge_member_position(f, s))
                            {
                                tele(
                                    n + 10,
                                    "dashed line",
                                    vec![
                                        json!({"t":"lane","x1":p.x,"y1":p.y,"x2":q.x,"y2":q.y,"half":0.08}),
                                    ],
                                    "Pass the brand".into(),
                                    prep + b.fuse,
                                    r.fuse,
                                    json!({}),
                                );
                            }
                        }
                    }
                }
                (Block::Grid(g), Stage::Grid { beat, offset, .. }) => {
                    *cast = json!({"name":m.name,"left":(g.cast+3.*60./g.bpm-l.elapsed).max(0.),"total":g.cast+3.*60./g.bpm});
                    let a = f.arena;
                    tele(
                        99,
                        "dashed line",
                        vec![json!({"t":"rect","x0":a.x0,"x1":a.x1,"y0":a.y0,"y1":a.y1})],
                        "Stay inside the numbered floor".into(),
                        g.cast - l.elapsed,
                        g.cast,
                        json!({}),
                    );
                    let dx = (a.x1 - a.x0) / 6.;
                    let dy = (a.y1 - a.y0) / 6.;
                    for y in 0..6 {
                        for x in 0..6 {
                            let number = grid_number(x, y, *offset);
                            let left = g.cast + (number - 1) as f64 * 60. / g.bpm - l.elapsed;
                            tele(
                                y * 6 + x,
                                if number > *beat { "red" } else { "blue" },
                                vec![
                                    json!({"t":"rect","x0":a.x0+x as f64*dx,"x1":a.x0+(x+1) as f64*dx,"y0":a.y0+y as f64*dy,"y1":a.y0+(y+1) as f64*dy}),
                                ],
                                number.to_string(),
                                left,
                                g.cast + (number - 1) as f64 * 60. / g.bpm,
                                json!({"beat":number,"landed":number<=*beat}),
                            );
                        }
                    }
                }
                (
                    Block::Carry(c),
                    Stage::Carry {
                        available,
                        carriers,
                        throws,
                        quenched,
                    },
                ) => {
                    *cast = json!({"name":if *quenched>0. {"Quenched"}else{"Molten"},"left":if *quenched>0. {*quenched}else{throws.first().map_or(0.,|t|c.window-(l.elapsed-t))},"total":if *quenched>0. {c.quenched}else{c.window}});
                    for (n, p) in c.points.iter().enumerate() {
                        if available[n] {
                            tele(
                                n,
                                "blue",
                                vec![circle(pt(*p), c.r)],
                                "Take water".into(),
                                0.,
                                0.,
                                json!({"well":n+1}),
                            );
                        }
                    }
                    tele(
                        20,
                        if *quenched > 0. {
                            "blue"
                        } else {
                            "dashed line"
                        },
                        vec![circle(self.slimes[f.boss].point(), c.throw_r)],
                        format!("Water: {}/{}", throws.len(), c.need),
                        *quenched,
                        c.quenched,
                        json!({"water":throws.len(),"needWater":c.need,"quenched":*quenched>0.}),
                    );
                    for (n, s) in carriers.keys().enumerate() {
                        if let Some(p) = self.forge_member_position(f, *s) {
                            tele(
                                n + 30,
                                "blue",
                                vec![circle(p, 0.7)],
                                "Carrying water".into(),
                                0.,
                                0.,
                                json!({"carrier":self.players[s].character.id,"speed":c.speed}),
                            );
                        }
                    }
                }
                (Block::Reflect(r), Stage::Reflect) => {
                    let active = l.elapsed >= r.cast;
                    let left = if active {
                        r.cast + r.duration - l.elapsed
                    } else {
                        r.cast - l.elapsed
                    };
                    *cast = json!({"name":if active {"Mirror Plate: hold fire!"}else{&m.name},"left":left.max(0.),"total":if active {r.duration}else{r.cast}});
                    tele(
                        0,
                        "dashed line",
                        vec![circle(self.slimes[f.boss].point(), 3.5)],
                        if active {
                            "HOLD FIRE"
                        } else {
                            "Stop attacks before the glow"
                        }
                        .into(),
                        left,
                        if active { r.duration } else { r.cast },
                        json!({"color":"#fffaf0","reflect":active}),
                    );
                }
                _ => {}
            }
        }
    }
}
