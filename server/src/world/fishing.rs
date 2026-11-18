//! Fishing inputs carry no position, catch or timestamp. The world owns each line.
use super::*;
use serde::Deserialize;
use std::{sync::LazyLock, time::Instant};

const WINDOW: f64 = 1.2;
const GRACE: f64 = 0.25;
const CAST: f64 = 0.5;

// Unix seconds for clients, monotonic after startup so clock corrections cannot extend a bite.
pub(super) fn now() -> f64 {
    static CLOCK: LazyLock<(Instant, f64)> =
        LazyLock::new(|| (Instant::now(), daynight::unix_ms() as f64 / 1000.));
    CLOCK.1 + CLOCK.0.elapsed().as_secs_f64()
}

#[derive(Deserialize)]
struct Species {
    item: String,
    habitat: String,
    min_tier: u32,
    kg: [u32; 2],
    zone: Option<usize>,
}
#[derive(Deserialize)]
struct Rod {
    item: String,
    tier: u32,
    lava: bool,
}
static FISH: LazyLock<Vec<Species>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/fish.txt")).expect("fish catalogue")
});
static RODS: LazyLock<Vec<Rod>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/rods.txt")).expect("rod catalogue")
});

#[derive(Clone, Default)]
pub(super) struct Session {
    pub(super) line: Option<Line>,
    pub(super) shopping: bool,
    next: f64,
    misses: u8,
    streak: u64,
}
#[derive(Clone, Copy)]
pub(super) struct Line {
    from: Point,
    zone: usize,
    bobber: Point,
    tier: u32,
    habitat: &'static str,
    bonus: f64,
    hurt_at: f64,
    cast_end: f64,
    bite_at: f64,
    waiting: bool,
    pub(super) biting: bool,
}
impl Line {
    pub(super) fn deadline(self) -> f64 {
        self.bite_at + WINDOW
    }
    pub(super) fn view(self) -> Value {
        json!({"x":self.bobber.x,"y":self.bobber.y,"lava":self.habitat=="Lava",
               "state":if self.biting {"bite"} else if self.waiting {"waiting"} else {"cast"}})
    }
}

fn habitat(zone: usize) -> Option<&'static str> {
    Some(match zone {
        0 | 19 => "Shore",
        2 | 26 => "Cold",
        3 => "Swamp",
        6 | 20 => "Forest",
        22 => "Jungle",
        25 => "Oasis",
        28 => "Spring",
        1 | 45 => "Lava",
        _ => return None,
    })
}
fn area_radius(o: &Obstacle, lava: bool) -> Option<f64> {
    use FishingSurface::*;
    match (lava, o.surface) {
        (true, Lava | EwLava) | (false, Water | JungleWater | JadePool) => Some(o.r),
        (false, Seafoam | YearSpringPool | FrostwakeFrozenPool | LapisOasis) => Some(o.r.max(1.)),
        _ => None,
    }
}
// Intersect the facing ray with each nearby pool, then clamp the throw to the part over liquid.
fn landing(map: &Map, p: Point, face: Point, lava: bool) -> Option<Point> {
    let at = |d: f64| Point {
        x: p.x + face.x * d,
        y: p.y + face.y * d,
    };
    let mut nearest: Option<(f64, Point)> = None;
    let mut ids = vec![];
    if let Some(grid) = map.grid.get(&map.objects, map.size) {
        grid.in_box(p.x - 7., p.y - 7., p.x + 7., p.y + 7., 0, &mut ids);
    } else {
        ids.extend(0..map.objects.len() as u32);
    }
    let dock = map.dock.as_ref().filter(|d| d.contains(p));
    for id in ids {
        let o = &map.objects[id as usize];
        let (start, end) = if let Some(r) = area_radius(o, lava) {
            let dx = o.x - p.x;
            let dy = o.y - p.y;
            if dx.hypot(dy) < r {
                return None;
            }
            let along = dx * face.x + dy * face.y;
            let square = r * r - (dx * face.y - dy * face.x).powi(2);
            if square <= 0. {
                continue;
            }
            (along - square.sqrt(), along + square.sqrt())
        } else if o.surface == FishingSurface::Void && dock.is_some() {
            let interval = |pos: f64, dir: f64, center: f64, size: f64| {
                if dir.abs() < 1e-8 {
                    return ((pos - center).abs() < size / 2.)
                        .then_some((f64::NEG_INFINITY, f64::INFINITY));
                }
                let a = (center - size / 2. - pos) / dir;
                let b = (center + size / 2. - pos) / dir;
                Some((a.min(b), a.max(b)))
            };
            let Some((x0, x1)) = interval(p.x, face.x, o.x, o.width) else {
                continue;
            };
            let Some((y0, y1)) = interval(p.y, face.y, o.y, o.depth) else {
                continue;
            };
            (x0.max(y0), x1.min(y1))
        } else {
            continue;
        };
        let lo = start.max(3.);
        let hi = end.min(6.);
        if (0. ..=4.).contains(&start) && lo < hi && nearest.is_none_or(|(s, _)| start < s) {
            let bobber = at((lo + hi) / 2.);
            if let Some(ship) = dock.and_then(|d| d.ship.as_ref())
                && (bobber.x - ship.x).abs() < ship.beam / 2.
                && (ship.y0..=ship.y1).contains(&bobber.y)
            {
                continue;
            }
            nearest = Some((start, bobber));
        }
    }
    nearest.map(|(_, p)| p)
}

impl World {
    fn can_fish(&self, session: u64) -> bool {
        let p = &self.players[&session];
        let c = &p.character;
        p.is_human()
            && p.can_dance()
            && !c.ghost
            && self.time >= p.cutscene_until
            && !p.fishing.shopping
            && !self.maps[c.zone].underwater()
            && !self.is_instance(c.zone)
            && !self.is_arena_zone(c.zone)
            && !self.pvp_busy(&c.id)
            && self.trade_index(&c.id).is_none()
    }
    fn fishing_line(&mut self, session: u64, time: f64) -> Result<Line, &'static str> {
        if !self.can_fish(session) {
            return Err("You cannot fish right now.");
        }
        let p = &self.players[&session];
        let c = &p.character;
        if c.bag_used() >= c.bag_capacity() {
            return Err("Fishing needs a free bag cell.");
        }
        let habitat = habitat(c.zone).ok_or("There are no fish here.")?;
        let lava = habitat == "Lava";
        let rod = RODS
            .iter()
            .filter(|r| {
                r.lava == lava
                    && c.quantity(&r.item) > 0
                    && item(&r.item).is_some_and(|i| c.level >= i.required_level)
            })
            .max_by_key(|r| r.tier)
            .ok_or("Carry a suitable fishing rod.")?;
        let map = &self.maps[c.zone];
        let bobber = landing(map, c.point(), p.face, lava)
            .ok_or("Stand near the shore and face the water or lava.")?;
        let rich = map.fishing_spots.iter().any(|s| s.distance(bobber) <= 3.);
        let min_tier = match c.zone {
            2 | 3 if rich => 2,
            6 | 45 => 2,
            20 | 22 => 3,
            19 | 25 => 4,
            26 => 5,
            28 => 6,
            _ => 1,
        };
        if rod.tier < min_tier {
            return Err("This fishing spot needs a stronger rod.");
        }
        let stamp = daynight::unix_ms();
        let rain = self.weather.view(c.zone, map.template, stamp)["type"] == "rain";
        let hour = self.world_clock.hour_at(stamp);
        let twilight = (5. ..7.).contains(&hour) || (17. ..19.).contains(&hour);
        let scale = (1. - 0.06 * f64::from(rod.tier - 1))
            * if rich { 0.75 } else { 1. }
            * if rain { 0.85 } else { 1. }
            * if twilight { 0.9 } else { 1. };
        let bonus = (1. + 0.1 * f64::from(rod.tier - 1))
            * if rich { 3. } else { 1. }
            * if rain || twilight { 1.1 } else { 1. };
        Ok(Line {
            zone: c.zone,
            from: c.point(),
            hurt_at: p.last_hurt,
            habitat,
            bobber,
            tier: rod.tier,
            bonus,
            waiting: false,
            biting: false,
            cast_end: time + CAST,
            bite_at: time + CAST + (3. + 9. * self.random()) * scale,
        })
    }
    pub(super) fn fish_end(&mut self, session: u64, mut reason: &str, miss: bool, time: f64) {
        let p = self.players.get_mut(&session).unwrap();
        p.fishing.line = None;
        p.fishing.next = time + 1.;
        p.fishing.streak = 0;
        if miss {
            p.fishing.misses += 1;
            if p.fishing.misses == 5 {
                p.fishing.misses = 0;
                reason = "You doze off. Cast again to keep fishing.";
            }
        }
        let _ = p.peer.try_send(
            json!({"type":"event","kind":"fish_miss","actor":p.character.id,"text":reason}),
        );
    }
    pub(super) fn fish_update(&mut self, session: u64, time: f64) {
        let p = &self.players[&session];
        let Some(line) = p.fishing.line else { return };
        if !self.can_fish(session)
            || p.character.mounted
            || p.last_hurt != line.hurt_at
            || p.character.zone != line.zone
            || p.character.point().distance(line.from) > 0.6
        {
            self.fish_end(session, "Line pulled in.", false, time);
            return;
        }
        if time > line.deadline() + GRACE {
            self.fish_end(session, "It got away.", true, time);
            return;
        }
        let p = self.players.get_mut(&session).unwrap();
        let active = p.fishing.line.as_mut().unwrap();
        active.waiting = time >= line.cast_end;
        if time >= line.bite_at && !active.biting {
            active.biting = true;
            let _=p.peer.try_send(json!({"type":"event","kind":"fish_bite","actor":p.character.id,"deadline":line.deadline()}));
        }
    }
    pub(super) fn fish_press(&mut self, session: u64, time: f64) {
        if self.players[&session].fishing.line.is_some() {
            self.fish_update(session, time);
            let Some(line) = self.players[&session].fishing.line else {
                return;
            };
            if !line.biting {
                self.fish_end(session, "Too early.", true, time);
                return;
            }
            self.land_fish(session, line, time);
            return;
        }
        if time < self.players[&session].fishing.next {
            return;
        }
        let line = match self.fishing_line(session, time) {
            Ok(l) => l,
            Err(text) => {
                let _ = self.players[&session]
                    .peer
                    .try_send(json!({"type":"error","text":text}));
                return;
            }
        };
        let p = self.players.get_mut(&session).unwrap();
        p.stop();
        p.dance = None;
        p.character.mounted = false;
        p.fishing.line = Some(line);
        let _=p.peer.try_send(json!({"type":"event","kind":"fish_cast","actor":p.character.id,"x":line.bobber.x,"y":line.bobber.y}));
    }
    fn land_fish(&mut self, session: u64, line: Line, time: f64) {
        let c = &self.players[&session].character;
        if c.bag_used() >= c.bag_capacity() {
            self.fish_end(session, "Fishing needs a free bag cell.", false, time);
            return;
        }
        let multiplier = c.drop_multiplier();
        // Weights apply to the whole rarity band, independent of the number of eligible species.
        let mut bands: [Vec<&Species>; 4] = Default::default();
        for species in FISH.iter().filter(|s| {
            s.habitat == line.habitat
                && s.min_tier <= line.tier
                && s.zone.is_none_or(|z| z == line.zone)
        }) {
            let Some(i) = item(&species.item) else {
                continue;
            };
            let band = match i.rarity.as_str() {
                "common" => 0,
                "uncommon" => 1,
                "rare" => 2,
                "legendary" => 3,
                _ => continue,
            };
            bands[band].push(species);
        }
        let weights = [70., 22., 6. * line.bonus, 0.5 * line.bonus];
        let total: f64 = (0..4)
            .filter(|&i| !bands[i].is_empty())
            .map(|i| weights[i])
            .sum();
        if total == 0. {
            self.fish_end(session, "Nothing bit.", false, time);
            return;
        }
        let mut roll = self.random() * total;
        let band = (0..4)
            .find(|&i| {
                if bands[i].is_empty() {
                    return false;
                }
                roll -= weights[i];
                roll <= 0.
            })
            .unwrap();
        let pool = &bands[band];
        let s = pool[(self.random() * pool.len() as f64) as usize];
        let kg = s.kg[0] + (self.random() * f64::from(1 + s.kg[1] - s.kg[0])) as u32;
        let quantity = copies(1., multiplier, || self.random());
        let p = self.players.get_mut(&session).unwrap();
        let c = &mut p.character;
        if c.quantity(&s.item).checked_add(quantity).is_none() {
            self.fish_end(session, "This stack is full.", false, time);
            return;
        }
        c.add_item(&s.item, quantity);
        p.fishing.line = None;
        p.fishing.next = time + 1.;
        p.fishing.misses = 0;
        p.fishing.streak += 1;
        c.fishing.total += 1;
        c.fishing.legendary += u64::from(band == 3);
        c.fishing.longest_streak = c.fishing.longest_streak.max(p.fishing.streak);
        let record = c.fishing.species.entry(s.item.clone()).or_default();
        record.count += 1;
        record.best_kg = record.best_kg.max(kg);
        let _=p.peer.try_send(json!({"type":"event","kind":"fish_catch","actor":c.id,"item":s.item,"quantity":quantity,"kg":kg,"rarity":item(&s.item).unwrap().rarity}));
    }
}
