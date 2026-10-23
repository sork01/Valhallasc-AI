//! Eldmarr: persistent cracked cells, time-driven heat and capacity-one seats.
//! All state belongs to one Fight and disappears on death, evade, wipe or reset.
use super::play::BossPlay;
use super::*;

type Cell = (i32, i32);
struct Standing {
    cell: Cell,
    time: f64,
}
struct CrackCell {
    age: f64,
}
#[derive(Default)]
struct Meter {
    heat: f64,
    fuse: Option<f64>,
}
struct Seating {
    left: f64,
    assignments: BTreeMap<u64, usize>,
}
pub(super) struct Eldmarr {
    phase: usize,
    pause: f64,
    phase_time: f64,
    joined: BTreeSet<u64>,
    outside: BTreeMap<u64, f64>,
    standing: BTreeMap<u64, Standing>,
    cracks: BTreeMap<Cell, CrackCell>,
    meters: BTreeMap<u64, Meter>,
    wells: usize,
    well_in: f64,
    seats_in: f64,
    seats: Option<Seating>,
}
impl Eldmarr {
    pub(super) fn from_def(def: &BossDef) -> Option<Self> {
        def.mechanics
            .iter()
            .any(|m| matches!(m.block, Block::Crack(_)))
            .then_some(Self {
                phase: 1,
                pause: 0.,
                phase_time: 0.,
                joined: BTreeSet::new(),
                outside: BTreeMap::new(),
                standing: BTreeMap::new(),
                cracks: BTreeMap::new(),
                meters: BTreeMap::new(),
                wells: 0,
                well_in: 30.,
                seats_in: 0.,
                seats: None,
            })
    }
    pub(super) fn view(&self) -> Value {
        json!({"phase":self.phase,"broken":if self.phase==1 {0} else {(self.phase-1)*3},
            "breathing":self.pause.max(0.),"floor":match self.phase {1=>"cracked",2=>"heated",3=>"table",_=>"unbound"}})
    }
    fn cracking(&self) -> bool {
        self.phase == 1 || self.phase == 4
    }
    fn heating(&self) -> bool {
        self.phase == 2 || self.phase == 4
    }
    fn seating(&self) -> bool {
        self.phase >= 3
    }
    fn tempo(&self) -> f64 {
        if self.phase == 4 { 1.25 } else { 1. }
    }
}
fn inside(a: Rect, p: Point) -> bool {
    p.x >= a.x0 && p.x <= a.x1 && p.y >= a.y0 && p.y <= a.y1
}
fn point(p: [f64; 2]) -> Point {
    Point { x: p[0], y: p[1] }
}
fn cell(p: Point, size: f64) -> Cell {
    ((p.x / size).floor() as i32, (p.y / size).floor() as i32)
}
fn cell_rect(c: Cell, size: f64) -> Rect {
    Rect {
        x0: c.0 as f64 * size,
        y0: c.1 as f64 * size,
        x1: (c.0 + 1) as f64 * size,
        y1: (c.1 + 1) as f64 * size,
    }
}
fn touches(a: Rect, p: Point, r: f64) -> bool {
    (p.x - p.x.clamp(a.x0, a.x1)).hypot(p.y - p.y.clamp(a.y0, a.y1)) <= r
}
fn blocks(
    def: &BossDef,
) -> Option<(
    &Mechanic,
    &bm::Crack,
    &Mechanic,
    &bm::Heat,
    &Mechanic,
    &bm::Seats,
)> {
    let (cm, c) = def.mechanics.iter().find_map(|m| {
        if let Block::Crack(c) = &m.block {
            Some((m, c))
        } else {
            None
        }
    })?;
    let (hm, h) = def.mechanics.iter().find_map(|m| {
        if let Block::Heat(h) = &m.block {
            Some((m, h))
        } else {
            None
        }
    })?;
    let (sm, s) = def.mechanics.iter().find_map(|m| {
        if let Block::Seats(s) = &m.block {
            Some((m, s))
        } else {
            None
        }
    })?;
    Some((cm, c, hm, h, sm, s))
}
fn wells(h: &bm::Heat, e: &Eldmarr, a: Rect, next: bool) -> Vec<[f64; 2]> {
    let mid = a.centre();
    let angle = ((e.wells + usize::from(next)) % 4) as f64 * std::f64::consts::FRAC_PI_2;
    h.points
        .iter()
        .map(|p| {
            let (x, y) = (p[0] - mid.x, p[1] - mid.y);
            [
                mid.x + x * angle.cos() - y * angle.sin(),
                mid.y + x * angle.sin() + y * angle.cos(),
            ]
        })
        .collect()
}
fn protected(c: Cell, size: f64, points: &[[f64; 2]], r: f64) -> bool {
    points
        .iter()
        .any(|p| touches(cell_rect(c, size), point(*p), r + BODY))
}

impl World {
    fn eld_members(&self, f: &Fight, e: &Eldmarr) -> Vec<(u64, Point)> {
        self.mech_players(f.zone)
            .into_iter()
            .filter(|(s, _)| e.joined.contains(s))
            .collect()
    }
    pub(super) fn eldmarr_cap_damage(&self, f: &Fight, id: usize, damage: f64) -> f64 {
        let Some(e) = &f.eld else { return damage };
        if id != f.boss {
            return damage;
        }
        if e.pause > 0. {
            return 0.;
        }
        let threshold = match e.phase {
            1 => 0.66,
            2 => 0.33,
            3 => 0.08,
            _ => 0.,
        };
        damage.min((self.slimes[id].hp - self.slimes[id].max_hp * threshold).max(0.))
    }
    pub(super) fn tick_eldmarr(&mut self, f: &mut Fight, def: &BossDef, share: f64) {
        let Some(mut e) = f.eld.take() else { return };
        let Some((cm, c, hm, h, sm, s)) = blocks(def) else {
            f.eld = Some(e);
            return;
        };
        // Hold the throne's authored position without cancelling normal attacks.
        // Enemy separation and knockbacks can move even a rooted monster; letting
        // ten melee fighters push him would drag the whole crew into old lava.
        let bodies = self.actor_bodies(f.zone, None, Some(f.boss));
        let boss = &self.slimes[f.boss];
        let home = Point {
            x: boss.hx,
            y: boss.hy,
        };
        let throne = free_actor_position(&self.maps[f.zone], home, boss.r, &bodies, true);
        let boss = &mut self.slimes[f.boss];
        boss.set_root_left = boss.set_root_left.max(HOLD);
        if let Some(p) = throne {
            boss.x = p.x;
            boss.y = p.y;
        }
        let alive = self.mech_players(f.zone);
        for (id, at) in &alive {
            if inside(f.arena, *at)
                || self.slimes[f.boss]
                    .contributors
                    .contains(&self.players[id].character.id)
            {
                e.joined.insert(*id);
            }
        }
        let mates = self.eld_members(f, &e);
        let living: BTreeSet<_> = mates.iter().map(|(id, _)| *id).collect();
        e.standing.retain(|id, _| living.contains(id));
        e.meters.retain(|id, _| living.contains(id));
        e.outside.retain(|id, _| living.contains(id));
        let next = match e.phase {
            1 if share <= 0.66 + 1e-9 => 2,
            2 if share <= 0.33 + 1e-9 => 3,
            3 if share <= 0.08 + 1e-9 => 4,
            _ => e.phase,
        };
        if next != e.phase {
            e.phase = next;
            e.phase_time = 0.;
            e.pause = if next < 4 { 10. } else { 0. };
            e.standing.clear();
            e.cracks.clear();
            e.meters.clear();
            e.seats = None;
            e.wells = 0;
            e.well_in = h.move_every;
            e.seats_in = s.first;
            let name = match next {
                2 => "Three Chains Break — Rising Heat",
                3 => "Six Chains Break — The Promised Table",
                _ => "Nine Chains Break — Eldmarr Unbound",
            };
            f.banner = Some((name.into(), 10.));
            self.mech_event(f.zone, "chains", name, f.arena.centre(), 3.);
        }
        if e.pause > 0. {
            e.pause = (e.pause - TICK).max(0.);
            self.hold_still(f.boss);
            f.eld = Some(e);
            return;
        }
        if e.phase == 1 && e.phase_time == 0. {
            f.banner = Some((cm.name.clone(), 8.));
        }
        e.phase_time += TICK;
        // A joined fighter cannot cancel a mechanic by walking out of its court.
        for (id, at) in &mates {
            if inside(f.arena, *at) {
                e.outside.remove(id);
            } else {
                let elapsed = e.outside.entry(*id).or_default();
                *elapsed += TICK;
                if *elapsed >= c.cast {
                    self.mech_kill(*id, "The Forge Floor", f.boss);
                }
            }
        }
        if e.heating() {
            e.well_in -= TICK * e.tempo();
            if e.well_in <= 0. {
                e.wells += 1;
                e.well_in += h.move_every;
            }
            let spots = wells(h, &e, f.arena, false);
            let mut cooling = BTreeSet::new();
            for p in &spots {
                let mut occupants: Vec<_> = mates
                    .iter()
                    .filter(|(_, at)| at.distance(point(*p)) <= h.r)
                    .collect();
                occupants.sort_by(|a, b| {
                    a.1.distance(point(*p))
                        .total_cmp(&b.1.distance(point(*p)))
                        .then(a.0.cmp(&b.0))
                });
                cooling.extend(occupants.into_iter().take(h.capacity).map(|(id, _)| *id));
            }
            // The table's warning suspends Heat, including live fuses: no plate
            // can demand a nine-second hold while a five-second fuse forces cooling.
            let table_warning =
                e.seating() && (e.seats.is_some() || e.seats_in <= TICK * e.tempo());
            for (id, _) in &mates {
                if table_warning {
                    continue;
                }
                let rate = e.tempo() / h.fill;
                let meter = e.meters.entry(*id).or_default();
                if cooling.contains(id) {
                    meter.heat = (meter.heat - h.cool * TICK).max(0.);
                    if meter.heat < 0.9 {
                        meter.fuse = None;
                    }
                } else {
                    meter.heat = (meter.heat + rate * TICK).min(1.);
                }
                if meter.heat >= 1. && meter.fuse.is_none() {
                    meter.fuse = Some(h.cast);
                    continue; // the first visible warning retains the entire cast
                }
                if let Some(left) = &mut meter.fuse {
                    *left -= TICK;
                    if *left <= 0. {
                        let at = self.players[id].character.point();
                        for (victim, pos) in &mates {
                            if pos.distance(at) <= h.blast {
                                self.mech_kill(*victim, &hm.name, f.boss);
                            }
                        }
                        meter.heat = 0.;
                        meter.fuse = None;
                        self.mech_event(f.zone, "heat", &hm.name, at, h.blast);
                    }
                }
            }
        }
        if e.seating() {
            e.seats_in -= TICK * e.tempo();
            let starting = e.seats.is_none() && e.seats_in <= 0.;
            if starting {
                e.seats = Some(Seating {
                    left: s.cast,
                    assignments: raid_bosses::assign(&mates, &s.points, &[1; 10]),
                });
                e.seats_in = s.every;
                f.banner = Some((sm.name.clone(), s.cast));
                // Capacity-one seats are always reachable, including in the combined phase.
                e.cracks
                    .retain(|cell, _| !protected(*cell, c.cell, &s.points, s.r));
                self.mech_event(f.zone, "cast", &sm.name, f.arena.centre(), s.cast);
            }
            if let Some(seats) = &mut e.seats {
                if !starting {
                    seats.left -= TICK;
                }
                // A fall/disconnect frees a seat, not an impossible permanent role.
                seats.assignments.retain(|id, _| living.contains(id));
                if seats.left <= 0. {
                    let mut safe = BTreeSet::new();
                    for p in &s.points {
                        let mut occupants: Vec<_> = mates
                            .iter()
                            .filter(|(id, at)| {
                                self.players[id].character.hp > 0. && at.distance(point(*p)) <= s.r
                            })
                            .collect();
                        occupants.sort_by(|a, b| {
                            a.1.distance(point(*p))
                                .total_cmp(&b.1.distance(point(*p)))
                                .then(a.0.cmp(&b.0))
                        });
                        if let Some((id, _)) = occupants.first() {
                            safe.insert(*id);
                        }
                    }
                    // Safe seats release stored Heat as the table lands. A
                    // suspended short fuse must not resume before cooling is reachable.
                    for id in &safe {
                        if let Some(meter) = e.meters.get_mut(id) {
                            meter.heat = 0.;
                            meter.fuse = None;
                        }
                    }
                    for (id, _) in &mates {
                        if !safe.contains(id) {
                            self.mech_kill(*id, &sm.name, f.boss);
                        }
                    }
                    self.mech_event(
                        f.zone,
                        "seats",
                        &sm.name,
                        f.arena.centre(),
                        safe.len() as f64,
                    );
                    e.seats = None;
                }
            }
        }
        if e.cracking() {
            let cool = wells(h, &e, f.arena, false);
            let heating = e.heating();
            let seating = e.seats.is_some();
            let tempo = e.tempo();
            let reserved = |p: Cell| {
                (heating && protected(p, c.cell, &cool, h.r))
                    || (seating && protected(p, c.cell, &s.points, s.r))
            };
            e.cracks.retain(|cell, crack| {
                crack.age += TICK;
                crack.age < c.cast + c.lava && !reserved(*cell)
            });
            for (id, at) in &mates {
                if self.players[id].character.hp <= 0. || !inside(f.arena, *at) {
                    continue;
                }
                let current = cell(*at, c.cell);
                let stood = e.standing.entry(*id).or_insert(Standing {
                    cell: current,
                    time: 0.,
                });
                if stood.cell != current {
                    stood.cell = current;
                    stood.time = 0.;
                }
                stood.time += TICK * tempo;
                if stood.time >= c.stand && !reserved(current) {
                    e.cracks.entry(current).or_insert(CrackCell { age: 0. });
                }
                if e.cracks.iter().any(|(cell, crack)| {
                    crack.age >= c.cast && touches(cell_rect(*cell, c.cell), *at, BODY)
                }) {
                    self.mech_kill(*id, &cm.name, f.boss);
                }
            }
        }
        f.eld = Some(e);
    }

    pub(super) fn eldmarr_danger(
        &self,
        f: &Fight,
        def: &BossDef,
        id: u64,
        at: Point,
        look: f64,
    ) -> Option<(String, f64)> {
        let e = f.eld.as_ref()?;
        if !e.joined.contains(&id) || e.pause > 0. {
            return None;
        }
        let (cm, c, hm, h, sm, s) = blocks(def)?;
        if !inside(f.arena, at) {
            return Some((
                cm.name.clone(),
                (c.cast - e.outside.get(&id).copied().unwrap_or(0.)).max(0.),
            ));
        }
        if e.cracking()
            && let Some(left) = e
                .cracks
                .iter()
                .filter(|(cell, _)| touches(cell_rect(**cell, c.cell), at, BODY))
                .map(|(_, v)| (c.cast - v.age - look).max(0.))
                .min_by(f64::total_cmp)
        {
            return Some((cm.name.clone(), left));
        }
        if let Some(seats) = &e.seats {
            let assigned = seats.assignments.get(&id).copied();
            let spot = assigned.and_then(|n| s.points.get(n));
            if spot.is_none_or(|p| at.distance(point(*p)) > s.r - BODY) {
                return Some((sm.name.clone(), seats.left));
            }
        }
        for (bearer, meter) in &e.meters {
            if let Some(left) = meter.fuse
                && let Some(p) = self.players.get(bearer)
                && p.character.hp > 0.
                && p.character.zone == f.zone
                && at.distance(p.character.point()) <= h.blast
            {
                return Some((hm.name.clone(), left));
            }
        }
        None
    }
    fn eldmarr_clear_path(
        &self,
        f: &Fight,
        e: &Eldmarr,
        c: &bm::Crack,
        origin: Point,
        a: Point,
        b: Point,
    ) -> bool {
        let steps = (a.distance(b) * 3.).ceil().max(1.) as usize;
        self.maps[f.zone].line_clear(a, b, PLAYER_RADIUS)
            && (1..=steps).all(|n| {
                let t = n as f64 / steps as f64;
                let p = Point {
                    x: a.x + (b.x - a.x) * t,
                    y: a.y + (b.y - a.y) * t,
                };
                inside(f.arena, p)
                    && !e.cracks.keys().any(|k| {
                        let rect = cell_rect(*k, c.cell);
                        !touches(rect, origin, BODY) && touches(rect, p, BODY + 0.15)
                    })
            })
    }

    /// Route a hired fighter round live and warned lava. The ordinary map's
    /// pathfinder knows stone, so persistent boss hazards need this small court search.
    fn eldmarr_route(
        &self,
        f: &Fight,
        e: &Eldmarr,
        c: &bm::Crack,
        me: Point,
        target: Point,
    ) -> Option<Point> {
        if !e.cracking() || e.cracks.is_empty() {
            return Some(target);
        }
        let safe = |p: Point| {
            inside(f.arena, p)
                && !e.cracks.keys().any(|k| {
                    let a = cell_rect(*k, c.cell);
                    !touches(a, me, BODY) && touches(a, p, BODY + 0.15)
                })
        };
        let clear = |a: Point, b: Point| self.eldmarr_clear_path(f, e, c, me, a, b);
        if clear(me, target) {
            return Some(target);
        }
        let start = (me.x.floor() as i32, me.y.floor() as i32);
        let at = |k: (i32, i32)| Point {
            x: k.0 as f64 + 0.5,
            y: k.1 as f64 + 0.5,
        };
        let mut queue = std::collections::VecDeque::from([start]);
        let mut previous = BTreeMap::from([(start, start)]);
        let mut end = None;
        while let Some(k) = queue.pop_front() {
            let p = if k == start { me } else { at(k) };
            if p.distance(target) <= 2. && clear(p, target) {
                end = Some(k);
                break;
            }
            for (dx, dy) in [
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ] {
                let q = (k.0 + dx, k.1 + dy);
                let pos = at(q);
                if previous.contains_key(&q) || !safe(pos) || !clear(p, pos) {
                    continue;
                }
                previous.insert(q, k);
                queue.push_back(q);
            }
        }
        let mut k = end?;
        while previous[&k] != start {
            k = previous[&k];
        }
        if k == start {
            Some(target)
        } else {
            Some(at(k))
        }
    }

    pub(super) fn eldmarr_play(&self, f: &Fight, def: &BossDef, id: u64) -> Option<BossPlay> {
        let e = f.eld.as_ref()?;
        if !e.joined.contains(&id) {
            return None;
        }
        let (_, c, _, h, _, s) = blocks(def)?;
        let me = self.players.get(&id)?.character.point();
        let answer = |goal: Option<Point>, hold_fire: bool, stay: bool| BossPlay {
            target: Some(f.boss),
            goal,
            hold_fire,
            stay,
        };
        if e.pause > 0. {
            return Some(answer(None, true, true));
        }
        if !inside(f.arena, me) {
            return Some(answer(Some(f.arena.centre()), true, false));
        }
        if let Some(seats) = &e.seats {
            let target = point(s.points[*seats.assignments.get(&id)?]);
            let goal = self.eldmarr_route(f, e, c, me, target);
            return Some(answer(
                goal,
                true,
                me.distance(target) < 0.25 || goal.is_none(),
            ));
        }
        if e.heating() && e.meters.contains_key(&id) {
            let points = wells(h, e, f.arena, false);
            let hot: Vec<_> = self
                .eld_members(f, e)
                .into_iter()
                .filter(|(id, at)| {
                    e.meters.get(id).is_some_and(|v| {
                        v.heat >= 0.5
                            || v.fuse.is_some()
                            || (v.heat > 0.08
                                && points.iter().any(|p| at.distance(point(*p)) <= h.r))
                    })
                })
                .collect();
            if hot.iter().any(|(who, _)| *who == id) {
                let assignments = raid_bosses::assign(&hot, &points, &[h.capacity; 4]);
                let target = point(points[*assignments.get(&id)?]);
                let goal = self.eldmarr_route(f, e, c, me, target);
                return Some(answer(
                    goal,
                    true,
                    me.distance(target) < 0.3 || goal.is_none(),
                ));
            }
            // A nearly empty meter rejoins the attack. Normal movement is handled by the shared brain.
        }
        if e.cracking() {
            let urgent = e
                .standing
                .get(&id)
                .is_some_and(|v| v.time >= c.stand * 0.65)
                || self.eldmarr_danger(f, def, id, me, 1.).is_some();
            if urgent {
                // Keep an escape until it is reached/clear. Rechoosing the
                // closest point to the boss every think oscillates at a cell
                // boundary, so melee never actually leaves the cracked tile.
                if let Some(goal) = self.boss.plans.get(&id).copied()
                    && me.distance(goal) > 0.3
                    && self.eldmarr_danger(f, def, id, goal, 2.).is_none()
                    && self.eldmarr_clear_path(f, e, c, me, me, goal)
                {
                    return Some(answer(Some(goal), true, false));
                }
                let mut candidates = vec![];
                for radius in [2.5, 4., 6., 8.] {
                    for n in 0..16 {
                        let angle = n as f64 * std::f64::consts::TAU / 16.;
                        let p = Point {
                            x: me.x + radius * angle.cos(),
                            y: me.y + radius * angle.sin(),
                        };
                        if inside(f.arena, p)
                            && cell(p, c.cell) != cell(me, c.cell)
                            && self.eldmarr_danger(f, def, id, p, 2.).is_none()
                            && self.eldmarr_clear_path(f, e, c, me, me, p)
                        {
                            candidates.push(p);
                        }
                    }
                }
                candidates.sort_by(|a, b| {
                    a.distance(self.slimes[f.boss].point())
                        .total_cmp(&b.distance(self.slimes[f.boss].point()))
                });
                if let Some(p) = candidates.first() {
                    return Some(answer(Some(*p), true, false));
                }
            }
        }
        None
    }

    pub(super) fn eldmarr_view(
        &self,
        f: &Fight,
        def: &BossDef,
        teles: &mut Vec<Value>,
        cast: &mut Value,
    ) {
        let Some(e) = &f.eld else { return };
        let Some((cm, c, hm, h, sm, s)) = blocks(def) else {
            return;
        };
        if e.pause > 0. {
            *cast = json!({"name":"The Forge Takes a Breath","left":e.pause,"total":10});
            return;
        }
        let circle = |p: [f64; 2], r: f64| json!({"t":"circle","x":p[0],"y":p[1],"r":r,"inner":0});
        for (cell, v) in &e.cracks {
            let a = cell_rect(*cell, c.cell);
            let lava = v.age >= c.cast;
            teles.push(json!({"id":format!("crack-{}-{}",cell.0,cell.1),"name":cm.name,"tele":"red",
                "shapes":[{"t":"rect","x0":a.x0,"y0":a.y0,"x1":a.x1,"y1":a.y1}],
                "left":(c.cast-v.age).max(0.),"total":c.cast,"lava":lava,"label":if lava {"Lava"} else {"Cracking Floor"}}));
        }
        if !e.outside.is_empty() {
            teles.push(json!({"id":"eld-boundary","name":cm.name,"tele":"blue","shapes":[{"t":"rect","x0":f.arena.x0,"y0":f.arena.y0,"x1":f.arena.x1,"y1":f.arena.y1}],
                "left":(c.cast-e.outside.values().copied().fold(0.,f64::max)).max(0.),"total":c.cast,"label":"Return to the throne hall"}));
        }
        if e.heating() {
            let mates = self.eld_members(f, e);
            for (n, p) in wells(h, e, f.arena, false).into_iter().enumerate() {
                let count = mates
                    .iter()
                    .filter(|(_, at)| at.distance(point(p)) <= h.r)
                    .count();
                teles.push(json!({"id":format!("well-{n}"),"name":hm.name,"tele":"blue","shapes":[circle(p,h.r)],"left":e.well_in/e.tempo(),"total":h.move_every/e.tempo(),
                    "label":"Cold Well","capacity":h.capacity,"count":count,"role":n+1,"coldWell":true}));
            }
            if e.well_in / e.tempo() <= 5. {
                for (n, p) in wells(h, e, f.arena, true).into_iter().enumerate() {
                    teles.push(json!({"id":format!("next-well-{n}"),"name":hm.name,"tele":"dashed line","shapes":[circle(p,h.r)],"left":e.well_in/e.tempo(),"total":5,"label":"Next Cold Well"}));
                }
            }
            for (id, meter) in &e.meters {
                let Some(p) = self.players.get(id) else {
                    continue;
                };
                let at = p.character.point();
                teles.push(json!({"id":format!("heat-{id}"),"name":hm.name,"tele":"red","shapes":if meter.fuse.is_some(){vec![circle([at.x,at.y],h.blast)]}else{vec![]},
                    "left":meter.fuse.unwrap_or(0.),"total":h.cast,"heat":meter.heat,"bearer":p.character.id,"heatFuse":meter.fuse}));
            }
        }
        if let Some(seats) = &e.seats {
            *cast = json!({"name":sm.name,"left":seats.left.max(0.),"total":s.cast});
            let mates = self.eld_members(f, e);
            for (n, p) in s.points.iter().enumerate() {
                let ids: Vec<_> = seats
                    .assignments
                    .iter()
                    .filter(|(_, seat)| **seat == n)
                    .filter_map(|(id, _)| self.players.get(id).map(|p| p.character.id.clone()))
                    .collect();
                let count = mates
                    .iter()
                    .filter(|(_, at)| at.distance(point(*p)) <= s.r)
                    .count();
                teles.push(json!({"id":format!("seat-{n}"),"name":sm.name,"tele":"blue","shapes":[circle(*p,s.r)],"left":seats.left.max(0.),"total":s.cast,
                    "label":"Seat","role":n+1,"capacity":1,"count":count,"players":ids,"seat":true}));
            }
        }
    }
}

#[cfg(test)]
#[path = "eldmarr_tests.rs"]
mod tests;
