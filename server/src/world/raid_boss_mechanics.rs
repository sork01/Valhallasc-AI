//! The first three Wardens: standing chains, bounded wind shelters and counted anvils.
//! All positions, capacity decisions, forced movement and damage belong to the server.
use super::play::BossPlay;
use super::*;

pub(super) struct RaidLive {
    pub(super) mech: usize,
    id: u64,
    left: f64,
    total: f64,
    active: bool,
    pulse: f64,
    groups: Vec<Vec<u64>>,
    assignments: BTreeMap<u64, usize>,
    progress: Vec<f64>,
    released: Vec<bool>,
    direction: Point,
}

fn point(p: [f64; 2]) -> Point {
    Point { x: p[0], y: p[1] }
}
fn inside(a: Rect, p: Point, margin: f64) -> bool {
    p.x >= a.x0 + margin && p.x <= a.x1 - margin && p.y >= a.y0 + margin && p.y <= a.y1 - margin
}

/// Small minimum-cost matching with capacity, rather than ten bots all choosing
/// the same nearest post. Stable session order keeps the choice steady per cast.
fn assign(mates: &[(u64, Point)], points: &[[f64; 2]], caps: &[usize]) -> BTreeMap<u64, usize> {
    let mut states = BTreeMap::from([(0u32, (0., Vec::<usize>::new()))]);
    for (_, at) in mates {
        let mut next: BTreeMap<u32, (f64, Vec<usize>)> = BTreeMap::new();
        for (code, (cost, route)) in states {
            for (i, p) in points.iter().enumerate() {
                let digit = 11u32.pow(i as u32);
                if ((code / digit) % 11) as usize >= caps[i] {
                    continue;
                }
                let distance = at.distance(point(*p));
                let total = cost + distance * distance;
                let new_code = code + digit;
                if next.get(&new_code).is_none_or(|(c, _)| total < *c) {
                    let mut path = route.clone();
                    path.push(i);
                    next.insert(new_code, (total, path));
                }
            }
        }
        states = next;
    }
    states
        .into_values()
        .min_by(|a, b| a.0.total_cmp(&b.0))
        .map(|(_, route)| mates.iter().zip(route).map(|((s, _), i)| (*s, i)).collect())
        .unwrap_or_default()
}

impl World {
    fn raid_cast_players(&self, fight: &Fight) -> Vec<(u64, Point)> {
        self.mech_players(fight.zone)
            .into_iter()
            .filter(|(_, p)| inside(fight.arena, *p, 0.))
            .collect()
    }
    fn raid_member_at(&self, fight: &Fight, session: u64) -> Option<Point> {
        self.mech_players(fight.zone)
            .into_iter()
            .find(|(s, _)| *s == session)
            .map(|(_, p)| p)
    }
    pub(super) fn start_raid_cast(&mut self, fight: &mut Fight, i: usize, m: &Mechanic) {
        let mut mates = self.raid_cast_players(fight);
        if mates.is_empty() {
            return;
        }
        let (cast, every, assignments, groups) = match &m.block {
            Block::Tether(t) => {
                // Fresh partners every pull/cast, from the world's seeded stream.
                let mut rng = self.mech_rng();
                for n in (1..mates.len()).rev() {
                    let k = (rng() * (n + 1) as f64) as usize;
                    mates.swap(n, k.min(n));
                }
                let mut groups: Vec<Vec<u64>> = mates
                    .chunks(2)
                    .map(|g| g.iter().map(|(s, _)| *s).collect())
                    .collect();
                if groups.len() > 1 && groups.last().is_some_and(|g| g.len() == 1) {
                    let last = groups.pop().unwrap();
                    groups.last_mut().unwrap().extend(last);
                }
                let assignments = groups
                    .iter()
                    .enumerate()
                    .flat_map(|(i, g)| g.iter().map(move |s| (*s, i)))
                    .collect();
                (t.cast, t.every, assignments, groups)
            }
            Block::Gust(g) => (
                g.cast,
                g.every,
                assign(&mates, &g.points, &vec![g.capacity; g.points.len()]),
                vec![],
            ),
            Block::Soak(s) => {
                let mut caps = vec![s.need; s.points.len()];
                for n in s.need * s.points.len()..mates.len() {
                    caps[(n - s.need * s.points.len()) % s.points.len()] += 1;
                }
                (s.cast, s.every, assign(&mates, &s.points, &caps), vec![])
            }
            _ => return,
        };
        // A zigzag builds pressure toward one corner before reversing. A
        // four-direction square would carry an idle crew safely in a loop.
        let direction = match fight.fired[i] % 16 {
            0 | 2 | 4 | 6 => Point { x: 1., y: 0. },
            1 | 3 | 5 | 7 => Point { x: 0., y: -1. },
            8 | 10 | 12 | 14 => Point { x: -1., y: 0. },
            _ => Point { x: 0., y: 1. },
        };
        fight.fired[i] += 1;
        fight.timer[i] = every;
        let count = groups.len();
        let id = self.fresh_id();
        fight.live.push(Live::Raid(RaidLive {
            mech: i,
            id,
            left: cast,
            total: cast,
            active: false,
            pulse: 0.,
            groups,
            assignments,
            progress: vec![0.; count],
            released: vec![false; count],
            direction,
        }));
        fight.banner = Some((m.name.clone(), cast));
        self.mech_event(
            fight.zone,
            "cast",
            &m.name,
            self.slimes[fight.boss].point(),
            cast,
        );
    }

    pub(super) fn tick_raid_cast(
        &mut self,
        fight: &mut Fight,
        m: &Mechanic,
        live: &mut RaidLive,
    ) -> bool {
        // Do not freeze the Warden for the entire warning: normal attacks remain a threat.
        live.left -= TICK;
        match &m.block {
            Block::Tether(t) => {
                if !live.active {
                    if live.left > 0. {
                        return true;
                    }
                    live.active = true;
                    live.left = t.duration;
                    live.total = t.duration;
                    fight.banner = Some((
                        "Chains tight! Hold the numbered anvils in order.".into(),
                        4.,
                    ));
                    self.mech_event(
                        fight.zone,
                        "heave",
                        &m.name,
                        self.slimes[fight.boss].point(),
                        t.duration,
                    );
                }
                live.pulse -= TICK;
                let pulse = live.pulse <= 0.;
                if pulse {
                    live.pulse = 1.;
                }
                let current = live.released.iter().position(|done| !done);
                for (i, group) in live.groups.iter().enumerate() {
                    if live.released[i] {
                        continue;
                    }
                    let alive: Vec<_> = group
                        .iter()
                        .filter_map(|s| self.raid_member_at(fight, *s).map(|p| (*s, p)))
                        .collect();
                    // A fallen partner never traps a survivor behind an impossible chain.
                    if alive.len() < 2 {
                        live.released[i] = true;
                        continue;
                    }
                    let taut = alive
                        .iter()
                        .any(|(_, a)| alive.iter().any(|(_, b)| a.distance(*b) > t.leash));
                    if taut && pulse {
                        for (s, _) in &alive {
                            self.mech_heavy(*s, t.heavy, &m.name, fight.boss);
                        }
                    }
                    if current == Some(i)
                        && !taut
                        && alive
                            .iter()
                            .all(|(_, p)| p.distance(point(t.points[i])) <= t.r)
                    {
                        live.progress[i] += TICK;
                        if live.progress[i] + 1e-6 >= t.hold {
                            live.released[i] = true;
                            self.mech_event(
                                fight.zone,
                                "chain_broken",
                                &m.name,
                                point(t.points[i]),
                                (i + 1) as f64,
                            );
                        }
                    } else {
                        live.progress[i] = 0.;
                    }
                }
                if live.released.iter().all(|done| *done) {
                    return false;
                }
                if live.left > 0. {
                    return true;
                }
                for (i, group) in live.groups.iter().enumerate() {
                    if !live.released[i] {
                        for s in group {
                            if self.raid_member_at(fight, *s).is_some() {
                                self.mech_heavy(*s, 0.9, &m.name, fight.boss);
                            }
                        }
                    }
                }
            }
            Block::Gust(g) => {
                if live.left > 0. {
                    return true;
                }
                let protected = self.gust_sheltered(fight, live, g);
                for s in live.assignments.keys().copied() {
                    if protected.contains(&s) {
                        continue;
                    }
                    let Some(mut at) = self.raid_member_at(fight, s) else {
                        continue;
                    };
                    let mut lethal = !inside(fight.arena, at, g.rim);
                    // Sweep the path: never teleport through a solid wall or across the lava rim.
                    for n in 0..(g.push / 0.2).ceil() as usize {
                        let step = 0.2_f64.min(g.push - n as f64 * 0.2);
                        let next = Point {
                            x: at.x + live.direction.x * step,
                            y: at.y + live.direction.y * step,
                        };
                        if !inside(fight.arena, next, g.rim) {
                            lethal = true;
                            break;
                        }
                        let mut collided = next;
                        self.maps[fight.zone].collide(&mut collided, PLAYER_RADIUS);
                        if collided.distance(next) > 1e-6 {
                            break;
                        }
                        at = next;
                    }
                    if let Some(p) = self.players.get_mut(&s) {
                        p.stop();
                        p.character.x = at.x;
                        p.character.y = at.y;
                    }
                    if lethal {
                        self.mech_kill(s, &m.name, fight.boss);
                    }
                }
            }
            Block::Soak(s) => {
                if live.left > 0. {
                    return true;
                }
                let occupants = self.soak_occupants(fight, s);
                let mut failed = false;
                for group in &occupants {
                    if group.len() < s.need {
                        failed = true;
                        for session in group {
                            self.mech_kill(*session, &m.name, fight.boss);
                        }
                    }
                }
                if failed {
                    for session in live.assignments.keys().copied() {
                        if self.raid_member_at(fight, session).is_some() {
                            self.mech_heavy(session, s.heavy, &m.name, fight.boss);
                        }
                    }
                }
            }
            _ => return false,
        }
        self.mech_event(
            fight.zone,
            "land",
            &m.name,
            self.slimes[fight.boss].point(),
            0.,
        );
        false
    }

    fn gust_sheltered(&self, fight: &Fight, live: &RaidLive, g: &bm::Gust) -> BTreeSet<u64> {
        let mut sheltered = BTreeSet::new();
        for post in &g.points {
            let mut near: Vec<_> = live
                .assignments
                .keys()
                .filter_map(|s| {
                    self.raid_member_at(fight, *s)
                        .map(|p| (*s, p.distance(point(*post))))
                })
                .filter(|(_, d)| *d <= g.r)
                .collect();
            near.sort_by(|a, b| a.1.total_cmp(&b.1).then(a.0.cmp(&b.0)));
            sheltered.extend(near.into_iter().take(g.capacity).map(|(s, _)| s));
        }
        sheltered
    }
    fn soak_occupants(&self, fight: &Fight, s: &bm::Soak) -> Vec<Vec<u64>> {
        let mates = self.raid_cast_players(fight);
        s.points
            .iter()
            .map(|p| {
                mates
                    .iter()
                    .filter(|(_, at)| at.distance(point(*p)) <= s.r)
                    .map(|(s, _)| *s)
                    .collect()
            })
            .collect()
    }

    pub(super) fn raid_cast_danger(
        &self,
        fight: &Fight,
        m: &Mechanic,
        live: &RaidLive,
        session: u64,
        at: Point,
    ) -> Option<f64> {
        let group = *live.assignments.get(&session)?;
        let unsafe_here = match &m.block {
            Block::Tether(t) => {
                !live.released[group]
                    && (live.groups[group]
                        .iter()
                        .filter(|s| **s != session)
                        .filter_map(|s| self.raid_member_at(fight, *s))
                        .any(|p| p.distance(at) > t.leash)
                        || at.distance(point(t.points[group])) > t.r)
            }
            Block::Gust(g) => at.distance(point(g.points[group])) > g.r,
            Block::Soak(s) => at.distance(point(s.points[group])) > s.r,
            _ => false,
        };
        unsafe_here.then_some(live.left.max(0.))
    }

    /// Numbered roles are recomputed each cast, never guessed independently by
    /// each mercenary. Hold the position until the cast lands or the chain breaks.
    pub(super) fn raid_boss_play(
        &self,
        fight: &Fight,
        def: &BossDef,
        session: u64,
    ) -> Option<BossPlay> {
        let live = fight.live.iter().find_map(|l| match l {
            Live::Raid(r) => Some(r),
            _ => None,
        })?;
        let group = *live.assignments.get(&session)?;
        let (at, r, done) = match &def.mechanics[live.mech].block {
            Block::Tether(t) => (point(t.points[group]), t.r, live.released[group]),
            Block::Gust(g) => (point(g.points[group]), g.r, false),
            Block::Soak(s) => (point(s.points[group]), s.r, false),
            _ => return None,
        };
        if done {
            return None;
        }
        let peers: Vec<_> = live
            .assignments
            .iter()
            .filter(|(_, i)| **i == group)
            .map(|(s, _)| *s)
            .collect();
        let index = peers.iter().position(|s| *s == session).unwrap_or(0);
        let angle = index as f64 / peers.len().max(1) as f64 * std::f64::consts::TAU;
        let goal = Point {
            x: at.x + angle.cos() * r * 0.3,
            y: at.y + angle.sin() * r * 0.3,
        };
        let me = self.players[&session].character.point();
        Some(BossPlay {
            goal: Some(goal),
            target: Some(fight.boss),
            hold_fire: true,
            stay: me.distance(goal) < 0.25,
        })
    }

    pub(super) fn raid_cast_view(
        &self,
        fight: &Fight,
        def: &BossDef,
        teles: &mut Vec<Value>,
        cast: &mut Value,
    ) {
        for live in &fight.live {
            let Live::Raid(live) = live else { continue };
            let m = &def.mechanics[live.mech];
            *cast = json!({"name":m.name,"left":live.left.max(0.),"total":live.total});
            let ids = |group: &[u64]| {
                group
                    .iter()
                    .filter_map(|s| self.players.get(s).map(|p| p.character.id.clone()))
                    .collect::<Vec<_>>()
            };
            let mut station = |index: usize,
                               at: Point,
                               r: f64,
                               count: usize,
                               need: usize,
                               capacity: usize,
                               kind: bm::Telegraph,
                               progress: f64,
                               current: bool| {
                let mut t = tele_json(
                    live.id + index as u64,
                    &m.name,
                    kind,
                    &[Shape::Circle {
                        x: at.x,
                        y: at.y,
                        r,
                        inner: 0.,
                    }],
                    live.left.max(0.),
                    live.total,
                    false,
                );
                t["role"] = json!(index + 1);
                t["count"] = json!(count);
                t["need"] = json!(need);
                t["capacity"] = json!(capacity);
                t["progress"] = json!(progress);
                t["current"] = json!(current);
                t["players"] = json!(ids(&live
                    .assignments
                    .iter()
                    .filter(|(_, g)| **g == index)
                    .map(|(s, _)| *s)
                    .collect::<Vec<_>>()));
                teles.push(t);
            };
            match &m.block {
                Block::Tether(t) => {
                    let current = live.released.iter().position(|done| !*done);
                    for (i, group) in live.groups.iter().enumerate() {
                        if live.released[i] {
                            continue;
                        }
                        let count = group
                            .iter()
                            .filter(|s| {
                                self.raid_member_at(fight, **s)
                                    .is_some_and(|p| p.distance(point(t.points[i])) <= t.r)
                            })
                            .count();
                        station(
                            i,
                            point(t.points[i]),
                            t.r,
                            count,
                            group.len(),
                            group.len(),
                            bm::Telegraph::Safe,
                            live.progress[i] / t.hold,
                            current == Some(i),
                        );
                    }
                    for (i, group) in live.groups.iter().enumerate() {
                        if live.released[i] {
                            continue;
                        }
                        let positions: Vec<_> = group
                            .iter()
                            .filter_map(|s| self.raid_member_at(fight, *s))
                            .collect();
                        let pairs = (0..positions.len())
                            .flat_map(|a| (a + 1..positions.len()).map(move |b| (a, b)));
                        for (a, b) in pairs {
                            let pair = [positions[a], positions[b]];
                            let taut = pair[0].distance(pair[1]) > t.leash;
                            let mut tele = tele_json(
                                live.id,
                                &m.name,
                                if taut && live.active {
                                    bm::Telegraph::Danger
                                } else {
                                    bm::Telegraph::Path
                                },
                                &[Shape::Lane {
                                    a: pair[0],
                                    b: pair[1],
                                    half: 0.08,
                                }],
                                live.left.max(0.),
                                live.total,
                                false,
                            );
                            tele["chain"] = json!(true);
                            tele["role"] = json!(i + 1);
                            tele["players"] = json!(ids(group));
                            teles.push(tele);
                        }
                    }
                }
                Block::Gust(g) => {
                    let mates = self.raid_cast_players(fight);
                    for (i, post) in g.points.iter().enumerate() {
                        let count = mates
                            .iter()
                            .filter(|(_, p)| p.distance(point(*post)) <= g.r)
                            .count();
                        station(
                            i,
                            point(*post),
                            g.r,
                            count,
                            0,
                            g.capacity,
                            bm::Telegraph::Safe,
                            0.,
                            false,
                        );
                    }
                    let a = fight.arena;
                    let rim = g.rim;
                    let bands = [
                        Rect {
                            x0: a.x0,
                            y0: a.y0,
                            x1: a.x1,
                            y1: a.y0 + rim,
                        },
                        Rect {
                            x0: a.x0,
                            y0: a.y1 - rim,
                            x1: a.x1,
                            y1: a.y1,
                        },
                        Rect {
                            x0: a.x0,
                            y0: a.y0,
                            x1: a.x0 + rim,
                            y1: a.y1,
                        },
                        Rect {
                            x0: a.x1 - rim,
                            y0: a.y0,
                            x1: a.x1,
                            y1: a.y1,
                        },
                    ];
                    teles.push(tele_json(
                        live.id,
                        &m.name,
                        bm::Telegraph::Danger,
                        &bands.into_iter().map(Shape::Arena).collect::<Vec<_>>(),
                        live.left.max(0.),
                        live.total,
                        false,
                    ));
                    let centre = Point {
                        x: (a.x0 + a.x1) / 2.,
                        y: (a.y0 + a.y1) / 2.,
                    };
                    let tip = Point {
                        x: centre.x + live.direction.x * g.push,
                        y: centre.y + live.direction.y * g.push,
                    };
                    let mut arrow = tele_json(
                        live.id,
                        &m.name,
                        bm::Telegraph::Path,
                        &[Shape::Lane {
                            a: centre,
                            b: tip,
                            half: 0.25,
                        }],
                        live.left.max(0.),
                        live.total,
                        false,
                    );
                    arrow["arrow"] = json!(true);
                    teles.push(arrow);
                }
                Block::Soak(s) => {
                    for (i, group) in self.soak_occupants(fight, s).iter().enumerate() {
                        station(
                            i,
                            point(s.points[i]),
                            s.r,
                            group.len(),
                            s.need,
                            0,
                            bm::Telegraph::Safe,
                            0.,
                            false,
                        );
                    }
                }
                _ => {}
            }
        }
    }
}
