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
    zones: Vec<usize>,
    #[serde(rename = "richZones")]
    rich_zones: Vec<usize>,
}
static FISH: LazyLock<Vec<Species>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/fish.txt")).expect("fish catalogue")
});
static RODS: LazyLock<Vec<Rod>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/rods.txt")).expect("rod catalogue")
});

static SKILL_WATERS: LazyLock<
    [Vec<usize>; (crate::profession::MAX_SKILL / crate::profession::SKILL_BAND) as usize],
> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/fishing-skill.txt"))
        .expect("fishing skill waters")
});

fn water_skill_cap(zone: usize, skill: u16) -> u16 {
    use crate::profession::{MAX_SKILL, SKILL_BAND, band_cap};
    let band = usize::from(skill / SKILL_BAND);
    if skill < MAX_SKILL && SKILL_WATERS[band].contains(&zone) {
        band_cap(skill)
    } else {
        0
    }
}

pub(super) struct RichSpot {
    pub(super) point: Point,
    pub(super) remaining: u32,
    pub(super) reserve: Option<Point>,
}

#[derive(Deserialize)]
struct ExtraLoot {
    item: String,
    category: String,
    habitat: String,
    weight: f64,
}
static EXTRA_LOOT: LazyLock<Vec<ExtraLoot>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/fishing-loot.txt")).expect("fishing loot")
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
    rich: Option<Point>,
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

#[derive(Deserialize)]
struct Water {
    habitat: String,
}

static WATERS: LazyLock<BTreeMap<usize, Water>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/fishing-waters.txt")).expect("fishing waters")
});

fn habitat(zone: usize) -> Option<&'static str> {
    WATERS.get(&zone).map(|water| water.habitat.as_str())
}
fn area_radius(o: &Obstacle, lava: bool) -> Option<f64> {
    use FishingSurface::*;
    match (lava, o.surface) {
        (true, Lava | EwLava) | (false, Water | JungleWater | JadePool) => Some(o.r),
        (false, Seafoam | YearSpringPool | FrostwakeFrozenPool | LapisOasis) => Some(o.r.max(1.)),
        _ => None,
    }
}
// Match the renderer's open-sea cells, rather than treating every void or border as water.
fn coast_landing(map: &Map, p: Point, face: Point, lava: bool) -> Option<Point> {
    #[cfg(test)]
    let mutation = std::env::var("MUTATE_FISH_COAST").unwrap_or_default();
    #[cfg(test)]
    if mutation == "disabled" {
        return None;
    }
    if lava {
        #[cfg(test)]
        if mutation != "lava" {
            return None;
        }
        #[cfg(not(test))]
        return None;
    }
    let at = |distance: f64| Point {
        x: p.x + face.x * distance,
        y: p.y + face.y * distance,
    };
    let sea = |point: Point| {
        if point.x < 0. || point.y < 0. {
            return false;
        }
        let (x, y) = (point.x.floor() as usize, point.y.floor() as usize);
        if map.shape_floor.get(y).and_then(|row| row.as_bytes().get(x)) != Some(&b' ') {
            return false;
        }
        let edge = map
            .shape_edge
            .get(y)
            .and_then(|row| row.as_bytes().get(x))
            .copied()
            .unwrap_or(b' ');
        #[cfg(test)]
        if mutation == "border" {
            return edge != b' ';
        }
        edge == b'c'
    };
    if sea(p) {
        return None;
    }
    let mut start: Option<f64> = None;
    let mut end = 6.;
    for step in 1..=48 {
        let distance = f64::from(step) / 8.;
        if sea(at(distance)) {
            if start.is_none() {
                if distance > 4. {
                    return None;
                }
                start = Some(distance);
            }
        } else if start.is_some() {
            end = distance - 0.125;
            break;
        }
    }
    let start = start?;
    let (lo, hi) = (start.max(3.), end.min(6.));
    if lo >= hi {
        return None;
    }
    let blocked = !map.line_clear(p, at((start - 0.125).max(0.)), 0.);
    #[cfg(test)]
    let blocked = blocked && mutation != "blocked";
    if blocked {
        return None;
    }
    let bobber = at((lo + hi) / 2.);
    if map
        .dock
        .as_ref()
        .and_then(|dock| dock.ship.as_ref())
        .is_some_and(|ship| {
            (bobber.x - ship.x).abs() < ship.beam / 2. && (ship.y0..=ship.y1).contains(&bobber.y)
        })
    {
        return None;
    }
    Some(bobber)
}

fn landing(map: &Map, p: Point, face: Point, lava: bool, auto_aim: bool) -> Option<Point> {
    // A shore cast needs room for the hero's whole collision footprint.
    // Validate on a copy: fishing must never move a hero out of lava or scenery.
    let mut shore = p;
    map.collide(&mut shore, PLAYER_RADIUS);
    if shore.distance(p) > 1e-8 {
        return None;
    }
    let mut ids = vec![];
    if let Some(grid) = map.grid.get(&map.objects, map.size) {
        grid.in_box(p.x - 7., p.y - 7., p.x + 7., p.y + 7., 0, &mut ids);
    } else {
        ids.extend(0..map.objects.len() as u32);
    }
    let cast = |direction| landing_along(map, p, direction, lava, &ids);
    let aimed = cast(face);
    if aimed.is_some() || !auto_aim {
        return aimed;
    }

    // Try the smallest turn first. The same shore and surface rules apply to every ray.
    let angle = face.y.atan2(face.x);
    (1..24).find_map(|step| {
        let turn = f64::from((step + 1) / 2) * std::f64::consts::TAU / 24.;
        let (y, x) = (angle + if step % 2 == 1 { turn } else { -turn }).sin_cos();
        cast(Point { x, y })
    })
}

// Intersect the facing ray with each nearby pool, then clamp the throw to the part over liquid.
fn landing_along(map: &Map, p: Point, face: Point, lava: bool, ids: &[u32]) -> Option<Point> {
    let at = |d: f64| Point {
        x: p.x + face.x * d,
        y: p.y + face.y * d,
    };
    let dock = map.dock.as_ref().filter(|d| d.contains(p));
    let mut nearest: Option<(f64, Point)> = None;
    for &id in ids {
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
    nearest.map(|(_, point)| point).or_else(|| {
        if dock.is_none() {
            coast_landing(map, p, face, lava)
        } else {
            None
        }
    })
}

impl World {
    pub(super) fn ensure_fishing_spots(&mut self, zone: usize) {
        if self.rich_fishing.contains_key(&zone) || self.maps[zone].fishing_spots.is_empty() {
            return;
        }
        let count = (4 + (self.random() * 5.) as usize)
            .min(self.maps[zone].fishing_spots.len().saturating_sub(1));
        self.rich_fishing.insert(zone, vec![]);
        for _ in 0..count {
            self.spawn_fishing_spot(zone, None);
        }
    }
    fn spawn_fishing_spot(&mut self, zone: usize, old: Option<Point>) {
        // Keep one alternate water location per spot clear of every other spot.
        // This guarantees relocation even in a zone with only a few tiny pools.
        let free: Vec<_> = self.maps[zone]
            .fishing_spots
            .iter()
            .copied()
            .filter(|point| {
                self.rich_fishing.get(&zone).is_none_or(|spots| {
                    spots.iter().all(|s| {
                        s.point.distance(*point) > 6.
                            && s.reserve.is_none_or(|p| p.distance(*point) > 6.)
                    })
                })
            })
            .collect();
        if free.len() < 2 {
            return;
        }
        let mut candidates: Vec<_> = free
            .iter()
            .copied()
            .filter(|point| old.is_none_or(|old| old.distance(*point) > 0.1))
            .collect();
        if let Some(old) = old {
            let distant: Vec<_> = candidates
                .iter()
                .copied()
                .filter(|p| p.distance(old) > 6.)
                .collect();
            if !distant.is_empty() {
                candidates = distant;
            }
        }
        if candidates.is_empty() {
            return;
        }
        let point = candidates[(self.random() * candidates.len() as f64) as usize];
        let reserve = free
            .iter()
            .copied()
            .filter(|p| p.distance(point) > 0.1)
            .min_by(|a, b| a.distance(point).total_cmp(&b.distance(point)));
        let remaining = 5 + (self.random() * 6.) as u32;
        self.rich_fishing.entry(zone).or_default().push(RichSpot {
            point,
            remaining,
            reserve,
        });
    }
    fn fishing_spot_caught(&mut self, zone: usize, point: Point) {
        let Some(spots) = self.rich_fishing.get_mut(&zone) else {
            return;
        };
        let Some(index) = spots.iter().position(|s| s.point.distance(point) < 0.001) else {
            return;
        };
        #[cfg(test)]
        if std::env::var("MUTATE_FISH_DATA").as_deref() == Ok("depletion") {
            return;
        }
        spots[index].remaining -= 1;
        if spots[index].remaining == 0 {
            spots.remove(index);
            self.spawn_fishing_spot(zone, Some(point));
        }
    }
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
    fn fishing_line(&mut self, session: u64, time: f64, auto_aim: bool) -> Result<Line, String> {
        if !self.can_fish(session) {
            return Err("You cannot fish right now.".into());
        }
        let p = &self.players[&session];
        let c = &p.character;
        if c.bag_used() >= c.bag_capacity() {
            return Err("Fishing needs a free bag cell.".into());
        }
        let habitat = habitat(c.zone).ok_or("There are no fish here.")?;
        let lava = habitat == "Lava";
        let map = &self.maps[c.zone];
        let bobber = landing(map, c.point(), p.face, lava, auto_aim).ok_or(if auto_aim {
            "Move closer to the shore to fish."
        } else {
            "Stand near the shore and face the water or lava."
        })?;
        let rich_point = self
            .rich_fishing
            .get(&c.zone)
            .and_then(|spots| spots.iter().find(|s| s.point.distance(bobber) <= 3.))
            .map(|s| s.point);
        let rich = rich_point.is_some();
        let required = RODS
            .iter()
            .filter(|r| r.zones.contains(&c.zone) || (rich && r.rich_zones.contains(&c.zone)))
            .max_by_key(|r| r.tier)
            .ok_or("There are no fish here.")?;
        let rod = RODS
            .iter()
            .filter(|r| {
                c.quantity(&r.item) > 0
                    && (!lava || r.lava)
                    && item(&r.item).is_some_and(|i| c.level >= i.required_level)
            })
            .max_by_key(|r| r.tier);
        if rod.is_none_or(|r| r.tier < required.tier) {
            let i = item(&required.item).unwrap();
            return Err(format!(
                "This water requires {} (level {}).",
                i.name, i.required_level
            ));
        }
        let rod = rod.unwrap();
        let stamp = daynight::unix_ms();
        let rain = self.weather.view(c.zone, map.template, stamp)["type"] == "rain";
        let hour = self.world_clock.hour_at(stamp);
        let twilight = (5. ..7.).contains(&hour) || (17. ..19.).contains(&hour);
        let scale = (1. - p.buff(BuffKind::FishingSpeed).min(0.5))
            * (1. - 0.06 * f64::from(rod.tier - 1))
            * if rich { 0.75 } else { 1. }
            * if rain { 0.85 } else { 1. }
            * if twilight { 0.9 } else { 1. }
            * if c.look.race == Race::Tidekin && !lava { 0.9 } else { 1. };
        let bonus = (1. + p.buff(BuffKind::FishingLuck))
            * (1. + 0.1 * f64::from(rod.tier - 1))
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
            rich: rich_point,
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
    pub(super) fn fish_press(&mut self, session: u64, time: f64, auto_aim: bool) {
        if self.players[&session].fishing.line.is_some() {
            // A second touch-cast request can arrive before the first cast is visible.
            if auto_aim {
                return;
            }
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
        self.ensure_fishing_spots(self.players[&session].character.zone);
        let line = match self.fishing_line(session, time, auto_aim) {
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
        if auto_aim {
            p.face = line.from.direction(line.bobber);
        }
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
        let rich = line.rich.filter(|point| {
            self.rich_fishing
                .get(&line.zone)
                .is_some_and(|spots| spots.iter().any(|s| s.point.distance(*point) < 0.001))
        });
        let bonus = if line.rich.is_some() && rich.is_none() {
            line.bonus / 3.
        } else {
            line.bonus
        };
        // Junk and treasure have their own bands; every award uses the rebirth copies helper.
        let extras: Vec<_> = EXTRA_LOOT
            .iter()
            .filter(|s| {
                s.habitat == "any"
                    || s.habitat
                        == if line.habitat == "Lava" {
                            "lava"
                        } else {
                            "water"
                        }
            })
            .collect();
        let extra_roll = self.random() * (98.5 + 8. + 1.5);
        if extra_roll < 9.5 {
            let category = if extra_roll < 8. { "junk" } else { "treasure" };
            let pool: Vec<_> = extras.iter().filter(|s| s.category == category).collect();
            let total: f64 = pool.iter().map(|s| s.weight).sum();
            let mut roll = self.random() * total;
            let s = pool
                .iter()
                .find(|s| {
                    roll -= s.weight;
                    roll <= 0.
                })
                .unwrap();
            let quantity = copies(1., multiplier, || self.random());
            let p = self.players.get_mut(&session).unwrap();
            if p.character
                .quantity(&s.item)
                .checked_add(quantity)
                .is_none()
            {
                self.fish_end(session, "This stack is full.", false, time);
                return;
            }
            p.character.add_item(&s.item, quantity);
            p.fishing.line = None;
            p.fishing.next = time + 1.;
            p.fishing.misses = 0;
            let _=p.peer.try_send(json!({"type":"event","kind":"fish_catch","actor":p.character.id,"item":s.item,"quantity":quantity,"rarity":item(&s.item).unwrap().rarity}));
            return;
        }
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
        let weights = [70., 22., 6. * bonus, 0.5 * bonus];
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
        let skill_roll = self.profession_roll();
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
        c.fishing.initialize_skill();
        let proficiency = &mut c.fishing.proficiency;
        let skill_cap = water_skill_cap(line.zone, proficiency.skill);
        let skill_up = proficiency
            .try_gain(band as u8, skill_cap, skill_roll)
            .then_some(proficiency.skill);
        c.fishing.total += 1;
        c.fishing.legendary += u64::from(band == 3);
        c.fishing.longest_streak = c.fishing.longest_streak.max(p.fishing.streak);
        let record = c.fishing.species.entry(s.item.clone()).or_default();
        record.count += 1;
        record.best_kg = record.best_kg.max(kg);
        let _=p.peer.try_send(json!({"type":"event","kind":"fish_catch","actor":c.id,"item":s.item,"quantity":quantity,"kg":kg,"rarity":item(&s.item).unwrap().rarity,"skillUp":skill_up}));
        if band == 3 {
            let actor = c.id.clone();
            let text = format!(
                "{0} caught {1} (ca {2} kg)!",
                c.look.name,
                item(&s.item).unwrap().name,
                kg
            );
            self.emit_zone(
                line.zone,
                json!({"type":"announce","kind":"treasure","actor":actor,"text":text}),
            );
        }
        if let Some(point) = rich {
            self.fishing_spot_caught(line.zone, point);
        }
    }
}

#[cfg(test)]
mod data_tests {
    use super::*;

    #[test]
    fn fishing_touch_cast_turns_toward_water_without_moving() {
        let (mut w, mut rx) = super::super::fishing_tests::angler();
        let p = &w.players[&1];
        let start = p.character.point();
        let away = [
            Point { x: -1., y: 0. },
            Point { x: 0., y: -1. },
            Point { x: 0., y: 1. },
        ]
        .into_iter()
        .find(|&face| landing(&w.maps[0], start, face, false, false).is_none())
        .expect("the dock has a direction without a valid cast");
        w.players.get_mut(&1).unwrap().face = away;

        w.fish_press(1, 20., false);
        assert!(w.players[&1].fishing.line.is_none());
        assert!(matches!(
            serde_json::from_value::<ClientMessage>(json!({"type":"fish","auto_aim":true})),
            Ok(ClientMessage::Fish { auto_aim: true })
        ));
        w.fish_press(1, 20., true);
        let player = &w.players[&1];
        let line = player.fishing.line.expect("touch cast finds water");
        assert_eq!(player.character.point().distance(start), 0.);
        let bobber = landing(&w.maps[0], start, player.face, false, false).unwrap();
        assert!(line.bobber.distance(bobber) < 1e-8);

        w.fish_press(1, 20.3, true);
        assert!(w.players[&1].fishing.line.is_some(), "repeated casts leave the line out");
        let hook = line.deadline() - 0.5;
        w.fish_press(1, hook, false);
        assert!(std::iter::from_fn(|| rx.try_recv().ok()).any(|v| v["kind"] == "fish_catch"));

        let p = w.players.get_mut(&1).unwrap();
        p.character.x = -10.;
        assert_eq!(
            w.fishing_line(1, hook + 2., true).err().as_deref(),
            Some("Move closer to the shore to fish.")
        );
    }

    #[test]
    fn fishing_data_all_candidates_pass_real_collision_and_cast() {
        let (w, _) = super::super::fishing_tests::angler();
        let points: Value =
            serde_json::from_str(include_str!("../../../world/fishing-spots.txt")).unwrap();
        for p in points.as_array().unwrap() {
            let zone = p["zone"].as_u64().unwrap() as usize;
            let shore: Point = serde_json::from_value(p["shore"].clone()).unwrap();
            let face: Point = serde_json::from_value(p["facing"].clone()).unwrap();
            let mut collided = shore;
            w.maps[zone].collide(&mut collided, PLAYER_RADIUS);
            assert!(
                collided.distance(shore) < 1e-8,
                "{}: blocked shore",
                p["id"]
            );
            let bobber = landing(&w.maps[zone], shore, face, habitat(zone) == Some("Lava"), false)
                .unwrap_or_else(|| panic!("{}: invalid cast", p["id"]));
            let expected: Point = serde_json::from_value(p.clone()).unwrap();
            assert!(
                bobber.distance(expected) < 1e-8,
                "{}: wrong bobber",
                p["id"]
            );
        }
    }

    #[test]
    fn fishing_data_random_spots_deplete_after_five_to_ten_fish_and_relocate() {
        let (mut w, _) = super::super::fishing_tests::angler();
        // A row of separated candidate waters gives every random draw room.
        w.maps[0].fishing_spots = (0..24)
            .map(|i| Point {
                x: f64::from(i) * 10.,
                y: 30.,
            })
            .collect();
        w.rng = 10;
        w.ensure_fishing_spots(0);
        let first: Vec<_> = w.rich_fishing[&0].iter().map(|s| s.point).collect();
        assert!((4..=8).contains(&first.len()));
        assert!(
            w.rich_fishing[&0]
                .iter()
                .all(|s| (5..=10).contains(&s.remaining))
        );
        let old = first[0];
        let limit = w.rich_fishing[&0][0].remaining;
        for _ in 1..limit {
            w.fishing_spot_caught(0, old);
            assert!(
                w.rich_fishing[&0]
                    .iter()
                    .any(|s| s.point.distance(old) < 0.001)
            );
        }
        w.fishing_spot_caught(0, old);
        assert_eq!(w.rich_fishing[&0].len(), first.len());
        assert!(
            w.rich_fishing[&0]
                .iter()
                .all(|s| s.point.distance(old) > 0.1)
        );
        let before: Vec<_> = w.rich_fishing[&0]
            .iter()
            .map(|s| (s.point.x, s.remaining))
            .collect();
        w.ensure_fishing_spots(0);
        assert_eq!(
            before,
            w.rich_fishing[&0]
                .iter()
                .map(|s| (s.point.x, s.remaining))
                .collect::<Vec<_>>()
        );
        let snapshot = w.snapshot_for(0);
        assert_eq!(
            snapshot["fishingSpots"].as_array().unwrap().len(),
            first.len()
        );
        assert!(snapshot["fishingSpots"][0].get("remaining").is_none());
        w.rich_fishing.remove(&0);
        w.rng = 20;
        w.ensure_fishing_spots(0);
        assert!(
            first.iter().any(|p| w.rich_fishing[&0]
                .iter()
                .all(|s| s.point.distance(*p) > 0.1)),
            "new random seed must change the active waters"
        );
    }

    #[test]
    fn fishing_data_every_zone_can_replace_depleted_spots() {
        let (mut w, _) = super::super::fishing_tests::angler();
        let original: Map = serde_json::from_str(include_str!("../../../world/map.txt")).unwrap();
        w.maps[0].fishing_spots = original.fishing_spots;
        w.rng = 123;
        for zone in [0, 1, 2, 3, 6, 19, 20, 22, 25, 26, 28, 45] {
            w.ensure_fishing_spots(zone);
            let count = w.rich_fishing[&zone].len();
            assert!((1..=8).contains(&count), "zone {zone}");
            for _ in 0..count * 2 {
                let point = w.rich_fishing[&zone][0].point;
                let remaining = w.rich_fishing[&zone][0].remaining;
                for _ in 0..remaining {
                    w.fishing_spot_caught(zone, point);
                }
                assert_eq!(
                    w.rich_fishing[&zone].len(),
                    count,
                    "zone {zone}: replacement must preserve spot count"
                );
                assert!(
                    w.rich_fishing[&zone]
                        .iter()
                        .all(|s| s.point.distance(point) > 0.1),
                    "zone {zone}: must relocate"
                );
            }
        }
    }

    #[test]
    fn fishing_skill_gives_existing_catches_one_time_credit() {
        let mut log: FishingLog = serde_json::from_value(json!({
            "total":40,"legendary":1,"longestStreak":5,"species":{}
        }))
        .unwrap();
        log.initialize_skill();
        assert_eq!(log.proficiency.skill, 21);
        assert!(log.proficiency.try_gain(0, 30, 0.));
        let mut reloaded: FishingLog =
            serde_json::from_value(serde_json::to_value(log).unwrap()).unwrap();
        reloaded.total = 1000;
        reloaded.initialize_skill();
        assert_eq!(reloaded.proficiency.skill, 22);
        let mut veteran = FishingLog {
            total: 1000,
            ..FishingLog::default()
        };
        veteran.initialize_skill();
        assert_eq!(veteran.proficiency.skill, 30);
    }

    #[test]
    fn fishing_skill_reaches_600_through_twenty_bands_at_real_shores() {
        use crate::profession::{MAX_SKILL, SKILL_BAND};
        let (mut w, mut rx) = super::super::fishing_tests::angler();
        let points: Value =
            serde_json::from_str(include_str!("../../../world/fishing-spots.txt")).unwrap();
        for rod in [
            "rod_magma_reel",
            "rod_starcatch_rod",
            "rod_worldwire_rod",
            "rod_rootbraid_rod",
            "rod_cairnsteel_rod",
        ] {
            w.players.get_mut(&1).unwrap().character.add_item(rod, 1);
        }
        let route = [
            0, 1, 2, 3, 6, 20, 22, 19, 25, 45, 7, 13, 14, 15, 16, 17, 21, 23, 24, 27,
        ];
        let levels = [
            50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 55, 60, 60, 80, 85, 85, 90,
        ];
        for (index, zone) in route.into_iter().enumerate() {
            let cap = (index as u16 + 1) * SKILL_BAND;
            assert_eq!(SKILL_WATERS[index][0], zone);
            assert_eq!(water_skill_cap(zone, cap - 1), cap);
            assert_eq!(water_skill_cap(zone, cap), 0);
            if index != 0 {
                assert_eq!(water_skill_cap(zone, cap - SKILL_BAND - 1), 0);
            }
            assert!(w.maps[zone].min_level <= levels[index]);
            let shore = points
                .as_array()
                .unwrap()
                .iter()
                .find(|p| p["zone"] == zone)
                .unwrap();
            let at: Point = serde_json::from_value(shore["shore"].clone()).unwrap();
            let face: Point = serde_json::from_value(shore["facing"].clone()).unwrap();
            let p = w.players.get_mut(&1).unwrap();
            p.face = face;
            p.character.zone = zone;
            p.character.level = levels[index];
            p.character.x = at.x;
            p.character.y = at.y;
            p.character.fishing.proficiency.skill = cap - 1;
            let line = w.fishing_line(1, 20., false).unwrap();
            w.rng = 1;
            w.profession_rng = 0;
            w.land_fish(1, line, 21.);
            let reply = std::iter::from_fn(|| rx.try_recv().ok())
                .find(|p| p["kind"] == "fish_catch")
                .unwrap();
            assert_eq!(reply["skillUp"], cap, "catch in zone {zone}");
            if matches!(cap, 30 | 300 | MAX_SKILL) {
                // A real catch still awards fish at the zone's skill cap.
                w.rng = 1;
                w.profession_rng = 0;
                w.land_fish(1, line, 22.);
                let reply = std::iter::from_fn(|| rx.try_recv().ok())
                    .find(|p| p["kind"] == "fish_catch")
                    .unwrap();
                assert!(reply["kg"].is_number());
                assert!(reply["skillUp"].is_null());
                assert_eq!(w.players[&1].character.fishing.proficiency.skill, cap);
            }
            // Empty the catch bag before moving to the next training waters.
            w.players
                .get_mut(&1)
                .unwrap()
                .character
                .inventory
                .retain(|stack| {
                    item(&stack.item).is_none_or(|definition| definition.kind != "fish")
                });
        }
        assert_eq!(w.players[&1].character.fishing.proficiency.skill, MAX_SKILL);
        assert_eq!(water_skill_cap(26, 270), 300);
        assert_eq!(water_skill_cap(28, 269), 0);
    }

    #[test]
    fn fishing_data_real_catches_spend_one_fish_per_hook_and_junk_spends_none() {
        let (mut w, mut rx) = super::super::fishing_tests::angler();
        w.players.get_mut(&1).unwrap().character.rebirth_tiers = [0, 0, 0, 0, 2];
        w.fish_press(1, 20., false);
        w.profession_rng = 0;
        let mut line = w.players[&1].fishing.line.unwrap();
        line.rich = Some(line.bobber);
        line.bonus *= 3.;
        w.rich_fishing.insert(
            0,
            vec![RichSpot {
                point: line.bobber,
                remaining: 5,
                reserve: None,
            }],
        );
        w.players.get_mut(&1).unwrap().fishing.line = Some(line);
        w.rng = 1;
        w.fish_press(1, line.deadline(), false);
        assert_eq!(w.rich_fishing[&0][0].remaining, 4);
        assert_eq!(w.players[&1].character.fishing.total, 1);
        assert_eq!(w.players[&1].character.fishing.proficiency.skill, 2);
        let caught = std::iter::from_fn(|| rx.try_recv().ok())
            .find(|v| v["kind"] == "fish_catch")
            .unwrap();
        assert_eq!(caught["skillUp"], 2);
        assert!(
            caught["quantity"].as_u64().unwrap() > 1,
            "rebirth multiplies copies, not spot use"
        );
        // Force the junk band on a lava cast without a timing sleep or random grind.
        line.habitat = "Lava";
        w.rng = 0;
        w.land_fish(1, line, 50.);
        assert_eq!(w.rich_fishing[&0][0].remaining, 4);
        assert_eq!(w.players[&1].character.fishing.total, 1);
        assert_eq!(w.players[&1].character.fishing.proficiency.skill, 2);
        let junk = std::iter::from_fn(|| rx.try_recv().ok())
            .find(|v| v["kind"] == "fish_catch")
            .unwrap();
        assert!(
            EXTRA_LOOT
                .iter()
                .any(|s| s.item == junk["item"] && s.category == "junk" && s.habitat == "lava")
        );
        assert!(junk.get("kg").is_none());
        w.rng = 35; // first draw is in the treasure band.
        w.land_fish(1, line, 70.);
        let treasure = std::iter::from_fn(|| rx.try_recv().ok())
            .find(|v| v["kind"] == "fish_catch")
            .unwrap();
        assert!(
            EXTRA_LOOT
                .iter()
                .any(|s| s.item == treasure["item"] && s.category == "treasure")
        );
        assert_eq!(w.rich_fishing[&0][0].remaining, 4);
        assert_eq!(
            w.players[&1]
                .character
                .quantity(junk["item"].as_str().unwrap()),
            junk["quantity"].as_u64().unwrap() as u32
        );
    }

    #[test]
    fn fishing_data_stacks_sell_bank_mail_and_bring() {
        let (mut w, _) = super::super::fishing_tests::angler();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.inventory.clear();
        for species in FISH.iter() {
            let i = item(&species.item).unwrap();
            assert_eq!(i.kind, "fish");
            assert!(!crate::items::is_gear(i));
            assert!(crate::mail::ineligible(&i.id).is_none());
        }
        let id = FISH[0].item.as_str();
        c.add_item(id, 7);
        assert_eq!(c.bag_used(), 1);
        c.bank_deposit(id, 3, None).unwrap();
        assert_eq!((c.quantity(id), c.bank.quantity(id)), (4, 3));
        c.bank_withdraw(id, 2, None).unwrap();
        assert_eq!((c.quantity(id), c.bank.quantity(id)), (6, 1));
        let q: Quest = serde_json::from_value(json!({"id":"fishing_test_bring","title":"Fish","npc":"test","requires":null,"repeatable":false,"level":1,"rewardXp":0,"rewardGold":0,"objectives":[{"kind":"bring","target":id,"count":5}]})).unwrap();
        c.quests.push(QuestProgress {
            id: q.id.clone(),
            ..Default::default()
        });
        q.sync_bring(c);
        assert!(q.ready(c.quests.last().unwrap()));
        q.take_bring(c);
        assert_eq!(c.quantity(id), 1);
        let gold = c.gold;
        let paid = c.sell_item(id, 1).unwrap();
        assert_eq!((c.quantity(id), c.gold), (0, gold + paid));
    }

    #[test]
    fn fishing_data_raw_fish_uses_meal_cooldown_and_small_heal() {
        let (mut w, _) = super::super::fishing_tests::angler();
        let i = item(&FISH[0].item).unwrap();
        let p = w.players.get_mut(&1).unwrap();
        p.character.hp = 1.;
        p.character.add_item(&i.id, 2);
        assert_eq!(
            super::super::consumables::health_amount(i, &p.character),
            i.heal
        );
        w.use_item(1, &i.id);
        assert_eq!(w.players[&1].character.quantity(&i.id), 1);
        assert_eq!(w.players[&1].meal_cd, 30.);
        w.use_item(1, &i.id);
        assert_eq!(w.players[&1].character.quantity(&i.id), 1);
    }
    #[test]
    fn fishing_workshop_best_rod_matches_water_or_lava_and_level() {
        let (mut w, _) = super::super::fishing_tests::angler();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 99;
        for rod in RODS.iter() {
            c.add_item(&rod.item, 1);
        }
        assert_eq!(w.fishing_line(1, 20., false).unwrap().tier, 10);
        w.players.get_mut(&1).unwrap().character.level = 85;
        assert_eq!(w.fishing_line(1, 20., false).unwrap().tier, 9);
        w.players.get_mut(&1).unwrap().character.level = 10;
        assert_eq!(w.fishing_line(1, 20., false).unwrap().tier, 3);
        w.maps[1].objects =
            vec![serde_json::from_value(json!({"kind":"lava","x":53.,"y":50.,"r":2.})).unwrap()];
        w.maps[1].grid = Default::default();
        let p = w.players.get_mut(&1).unwrap();
        p.character.zone = 1;
        p.character.x = 50.;
        p.character.y = 50.;
        p.character.level = 99;
        assert_eq!(w.fishing_line(1, 20., false).unwrap().tier, 10);
        w.players.get_mut(&1).unwrap().character.level = 5;
        assert_eq!(w.fishing_line(1, 20., false).unwrap().tier, 2);
    }
}

#[cfg(test)]
#[path = "fishing_lava_tests.rs"]
mod lava_tests;

#[cfg(test)]
#[path = "fishing_coast_tests.rs"]
mod coast_tests;

#[cfg(test)]
#[path = "fishing_progression_tests.rs"]
mod progression_tests;
