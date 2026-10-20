//! Treasure chests (`CHEST-SERVER`; rules in `docs/chests.md`). Chests are runtime state: never saved, and a restart
//! clears them. Each area (an open map with monsters, or one running dungeon copy) counts down `CHEST_ROLL_INTERVAL`
//! only while a living player is inside, and a roll has a `CHEST_SPAWN_CHANCE` of placing one chest on a reachable tile.
//! Nothing is rolled for the contents until somebody opens it.
use super::*;
use std::collections::VecDeque;

/// One roll per area per interval, in seconds.
pub const CHEST_ROLL_INTERVAL: f64 = 120.;
/// Chance that a roll creates a chest.
pub const CHEST_SPAWN_CHANCE: f64 = 0.10;
/// Seconds before an unopened chest despawns.
pub const CHEST_LIFETIME: f64 = 180.;
/// A roll while a chest is up does nothing (it is not banked).
pub const CHEST_MAX_PER_AREA: usize = 1;
/// Distance from the chest centre to open it, in tiles.
pub const CHEST_OPEN_RANGE: f64 = 2.0;
/// Minimum walking distance from the arrival point, and straight-line distance from every portal, in tiles.
pub const CHEST_MIN_ARRIVAL_DISTANCE: f64 = 14.;
/// Candidate tiles tried before the roll is skipped.
pub const CHEST_PLACEMENT_TRIES: usize = 40;
/// Distance a chest keeps from monster homes, NPCs, portals, drops and players.
const CHEST_CLEARANCE: f64 = 3.;
/// Equipment rolls inside one chest and the ladder each uses (cumulative edges: gray, green, blue, purple).
const CHEST_GEAR_ROLLS: usize = 2;
const CHEST_LADDER: [(&str, f64); 4] = [
    ("common", 0.62),
    ("uncommon", 0.92),
    ("rare", 0.995),
    ("epic", 1.0),
];
/// Extra chance, in a dungeon chest, of one blue piece from that dungeon's own set.
const CHEST_SET_PIECE_CHANCE: f64 = 0.06;
/// Gold is this many times the average kill gold of the area's monster kinds.
const CHEST_GOLD_KILLS: f64 = 5.;
const CHEST_SET_SLOTS: [&str; 8] = [
    "armor",
    "headgear",
    "shoulders",
    "gloves",
    "weapon",
    "pants",
    "necklace",
    "accessory",
];
/// How many finished chests are remembered, to answer a late "open" with the right sentence.
const CHEST_MEMORY: usize = 64;

#[derive(Clone, Serialize)]
pub(super) struct Chest {
    pub id: u64,
    pub zone: usize,
    pub x: f64,
    pub y: f64,
    /// Seconds until it vanishes.
    pub left: f64,
    /// Sessions that have been told it exists (everyone present at spawn, and anyone arriving later, once).
    #[serde(skip)]
    pub told: Vec<u64>,
}

/// World state owned by this module.
pub(super) struct Chests {
    pub list: Vec<Chest>,
    /// Seconds left until the next roll, per area (a zone number; a dungeon copy has its own). Paused while empty.
    pub timers: BTreeMap<usize, f64>,
    /// Chest placement uses its own generator, so chests never disturb the seeded combat and loot rolls.
    pub rng: u64,
    /// Cached walking grids, by template zone: `true` is blocked.
    grids: BTreeMap<usize, Vec<bool>>,
    /// Cached walking distance in tiles from the arrival point, by template zone (`u16::MAX`: unreachable).
    fields: BTreeMap<usize, Vec<u16>>,
    /// Chests that are gone: `true` when opened, `false` when they vanished.
    finished: VecDeque<(u64, bool)>,
    /// The roll interval; tests shorten it.
    pub interval: f64,
    /// Rolls made so far (a roll is one draw against `CHEST_SPAWN_CHANCE`).
    pub rolls: u64,
}
impl Chests {
    pub(super) fn new(seed: u64) -> Self {
        Self {
            list: vec![],
            timers: BTreeMap::new(),
            rng: seed | 1,
            grids: BTreeMap::new(),
            fields: BTreeMap::new(),
            finished: VecDeque::new(),
            interval: CHEST_ROLL_INTERVAL,
            rolls: 0,
        }
    }
    fn random(&mut self) -> f64 {
        self.rng = self
            .rng
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.rng >> 32) as f64 / 4294967296.
    }
    fn finish(&mut self, id: u64, opened: bool) {
        self.finished.push_back((id, opened));
        while self.finished.len() > CHEST_MEMORY {
            self.finished.pop_front();
        }
    }
}

/// The ladder rarity for a roll in [0, 1).
#[cfg(test)]
fn ladder_rarity(roll: f64) -> &'static str {
    boosted_ladder_rarity(roll, 1)
}
/// The ladder at drop multiplier `boost`: the purple band grows by the multiplier and the lower bands slide down to
/// make room, so their own widths stay and gray absorbs the difference (docs/rebirth.md).
pub(super) fn boosted_ladder_rarity(roll: f64, boost: u32) -> &'static str {
    let purple_start = CHEST_LADDER[CHEST_LADDER.len() - 2].1;
    let shift = (1. - purple_start) * f64::from(boost.max(1) - 1);
    CHEST_LADDER
        .iter()
        .find(|(_, edge)| roll < *edge - shift)
        .map_or("epic", |(rarity, _)| rarity)
}
pub(super) fn in_room(room: &[f64; 4], p: Point) -> bool {
    p.x >= room[0] && p.x < room[2] + 1. && p.y >= room[1] && p.y < room[3] + 1.
}

/// A one-tile grid of the map: `true` where a walking character cannot stand.
pub(super) fn blocked_grid(map: &Map) -> Vec<bool> {
    let n = map.size as usize;
    let mut grid = vec![false; n * n];
    let margin = 1.2;
    for j in 0..n {
        for i in 0..n {
            let (x, y) = (i as f64 + 0.5, j as f64 + 0.5);
            if x < margin
                || y < margin
                || x > map.size as f64 - margin
                || y > map.size as f64 - margin
            {
                grid[j * n + i] = true;
            }
        }
    }
    for o in &map.objects {
        let (hx, hy) = if o.width > 0. && o.depth > 0. {
            (o.width / 2. + PLAYER_RADIUS, o.depth / 2. + PLAYER_RADIUS)
        } else {
            (o.r + PLAYER_RADIUS, o.r + PLAYER_RADIUS)
        };
        let (x0, x1) = (
            ((o.x - hx).floor().max(0.)) as usize,
            ((o.x + hx).ceil().max(0.)) as usize,
        );
        let (y0, y1) = (
            ((o.y - hy).floor().max(0.)) as usize,
            ((o.y + hy).ceil().max(0.)) as usize,
        );
        for j in y0..=y1.min(n - 1) {
            for i in x0..=x1.min(n - 1) {
                let (x, y) = (i as f64 + 0.5, j as f64 + 0.5);
                let hit = if o.width > 0. && o.depth > 0. {
                    (x - o.x).abs() < hx && (y - o.y).abs() < hy
                } else {
                    (x - o.x).hypot(y - o.y) < hx
                };
                if hit {
                    grid[j * n + i] = true;
                }
            }
        }
    }
    grid
}
/// Walking distance in tiles from `from` over the free cells of `grid` (four-way steps).
pub(super) fn distance_field(map: &Map, grid: &[bool], from: Point) -> Vec<u16> {
    let n = map.size as usize;
    let mut dist = vec![u16::MAX; n * n];
    let (fx, fy) = ((from.x as usize).min(n - 1), (from.y as usize).min(n - 1));
    let mut queue = VecDeque::new();
    // The arrival point may sit on a blocked cell's edge; start from the nearest free cell around it.
    'seed: for r in 0..4_i32 {
        for dy in -r..=r {
            for dx in -r..=r {
                let (x, y) = (fx as i32 + dx, fy as i32 + dy);
                if x >= 0
                    && y >= 0
                    && (x as usize) < n
                    && (y as usize) < n
                    && !grid[y as usize * n + x as usize]
                {
                    dist[y as usize * n + x as usize] = 0;
                    queue.push_back((x as usize, y as usize));
                    break 'seed;
                }
            }
        }
    }
    while let Some((x, y)) = queue.pop_front() {
        let d = dist[y * n + x];
        for (dx, dy) in [(1_i32, 0_i32), (-1, 0), (0, 1), (0, -1)] {
            let (nx, ny) = (x as i32 + dx, y as i32 + dy);
            if nx < 0 || ny < 0 || nx as usize >= n || ny as usize >= n {
                continue;
            }
            let at = ny as usize * n + nx as usize;
            if !grid[at] && dist[at] == u16::MAX {
                dist[at] = d.saturating_add(1);
                queue.push_back((nx as usize, ny as usize));
            }
        }
    }
    dist
}

impl World {
    /// The copy-independent zone whose geometry `zone` shares.
    fn chest_template(&self, zone: usize) -> usize {
        self.instance_at(zone).map_or(zone, |i| i.template)
    }
    /// Whether `zone` currently counts as a chest area (see `docs/chests.md`).
    pub(super) fn chest_area(&self, zone: usize) -> bool {
        let map = &self.maps[zone];
        if map.slimes.is_empty() {
            return false;
        }
        match self.instance_at(zone) {
            None => map.copies == 0 && map.template.is_none(),
            Some(i) => {
                i.active
                    && !i.cleared
                    && !self.slimes.iter().any(|s| {
                        s.zone == zone && !s.dead && is_boss(&s.kind) && s.target.is_some()
                    })
            }
        }
    }
    fn chest_occupied(&self, zone: usize) -> bool {
        self.players.values().any(|p| {
            p.character.zone == zone
                && p.character.hp > 0.
                && p.merc.is_none()
                && p.ambient.is_none()
        })
    }
    /// Once per tick: despawn, announce, and count the roll timers down.
    pub(super) fn update_chests(&mut self) {
        // Lifetime.
        let mut gone = vec![];
        for c in &mut self.chests.list {
            c.left -= TICK;
            if c.left <= 0. {
                gone.push((c.id, c.zone));
            }
        }
        for (id, zone) in gone {
            self.chests.list.retain(|c| c.id != id);
            self.chests.finish(id, false);
            self.chest_say(zone, "The treasure chest has vanished.");
        }
        // Tell anybody who has not heard (a late arrival once, everyone at the moment of the spawn).
        let sessions: Vec<(u64, usize)> = self
            .players
            .iter()
            .filter(|(_, p)| p.character.hp > 0.)
            .map(|(s, p)| (*s, p.character.zone))
            .collect();
        for chest in &mut self.chests.list {
            for &(session, zone) in &sessions {
                if zone == chest.zone && !chest.told.contains(&session) {
                    chest.told.push(session);
                    if let Some(p) = self.players.get(&session) {
                        let minutes = (chest.left / 60.).ceil().max(1.) as u32;
                        let text = format!(
                            "A treasure chest has appeared! It will vanish in {minutes} minute{}.",
                            if minutes == 1 { "" } else { "s" }
                        );
                        let _ = p.peer.try_send(json!({"type":"system","text":text}));
                    }
                }
            }
        }
        // Roll timers.
        let areas: Vec<usize> = (0..self.maps.len())
            .filter(|&z| self.chest_area(z) && self.chest_occupied(z))
            .collect();
        for zone in areas {
            let interval = self.chests.interval;
            let left = self.chests.timers.entry(zone).or_insert(interval);
            *left -= TICK;
            if *left > 0. {
                continue;
            }
            *left = interval;
            if self.chests.list.iter().filter(|c| c.zone == zone).count() >= CHEST_MAX_PER_AREA {
                continue;
            }
            self.chests.rolls += 1;
            if self.chests.random() < CHEST_SPAWN_CHANCE {
                self.spawn_chest(zone);
            }
        }
    }
    fn chest_say(&self, zone: usize, text: &str) {
        for p in self.players.values().filter(|p| p.character.zone == zone) {
            let _ = p.peer.try_send(json!({"type":"system","text":text}));
        }
    }
    /// Creates a chest in `zone` on a placed tile; false when no tile fit (the roll is skipped and logged).
    pub(super) fn spawn_chest(&mut self, zone: usize) -> bool {
        let Some(at) = self.chest_spot(zone) else {
            tracing::info!(zone, "no free tile for a treasure chest; roll skipped");
            return false;
        };
        let id = self.entity();
        self.chests.list.push(Chest {
            id,
            zone,
            x: at.x,
            y: at.y,
            left: CHEST_LIFETIME,
            told: vec![],
        });
        true
    }
    /// A tile for a new chest in `zone`, or `None` after `CHEST_PLACEMENT_TRIES` failures.
    pub(super) fn chest_spot(&mut self, zone: usize) -> Option<Point> {
        let template = self.chest_template(zone);
        let mut candidates = vec![];
        for _ in 0..CHEST_PLACEMENT_TRIES {
            candidates.push((self.chests.random(), self.chests.random()));
        }
        if !self.chests.grids.contains_key(&template) {
            let grid = blocked_grid(&self.maps[template]);
            let field = distance_field(&self.maps[template], &grid, self.maps[template].spawn);
            self.chests.grids.insert(template, grid);
            self.chests.fields.insert(template, field);
        }
        let map = &self.maps[zone];
        let n = map.size as usize;
        let grid = &self.chests.grids[&template];
        let field = &self.chests.fields[&template];
        let dungeon = self.instance_at(zone).is_some();
        let bosses: Vec<Point> = self
            .slimes
            .iter()
            .filter(|s| s.zone == zone && is_boss(&s.kind))
            .map(|s| Point { x: s.hx, y: s.hy })
            .collect();
        let homes: Vec<Point> = self
            .spawns
            .iter()
            .filter(|s| s.zone == zone)
            .map(|s| Point { x: s.x, y: s.y })
            .collect();
        let living_bosses: Vec<Point> = self
            .slimes
            .iter()
            .filter(|s| s.zone == zone && !s.dead && is_boss(&s.kind))
            .map(|s| s.point())
            .collect();
        let final_room: Vec<&[f64; 4]> = map
            .rooms
            .iter()
            .filter(|r| bosses.iter().any(|b| in_room(r, *b)))
            .collect();
        let mut npcs: Vec<Point> = map.npcs.iter().map(|n| n.position_at(self.time)).collect();
        // A boss sign is as unwelcome a neighbour as a townsperson (BOSSMECH-SIGN-ENGINE).
        npcs.extend(
            self.signs
                .get(&map.final_boss)
                .map(|d| Point { x: d.x, y: d.y }),
        );
        let players: Vec<Point> = self
            .players
            .values()
            .filter(|p| p.character.zone == zone)
            .map(|p| p.character.point())
            .collect();
        let drops: Vec<Point> = self
            .drops
            .iter()
            .filter(|d| d.zone == zone)
            .map(|d| d.point())
            .collect();
        let others: Vec<Point> = self
            .chests
            .list
            .iter()
            .filter(|c| c.zone == zone)
            .map(|c| Point { x: c.x, y: c.y })
            .collect();
        'tries: for (rx, ry) in candidates {
            let (cx, cy) = (
                ((rx * n as f64) as usize).min(n - 1),
                ((ry * n as f64) as usize).min(n - 1),
            );
            let at = Point {
                x: cx as f64 + 0.5,
                y: cy as f64 + 0.5,
            };
            let steps = field[cy * n + cx];
            if grid[cy * n + cx] || steps == u16::MAX || (steps as f64) < CHEST_MIN_ARRIVAL_DISTANCE
            {
                continue;
            }
            // The chest and the character who opens it must both stand on free ground, so the cell around it is free.
            for (dx, dy) in [(1_i32, 0_i32), (-1, 0), (0, 1), (0, -1)] {
                let (x, y) = (cx as i32 + dx, cy as i32 + dy);
                if x < 0
                    || y < 0
                    || x as usize >= n
                    || y as usize >= n
                    || grid[y as usize * n + x as usize]
                {
                    continue 'tries;
                }
            }
            if map.portals.iter().any(|p| {
                at.distance(Point { x: p.x, y: p.y })
                    < CHEST_MIN_ARRIVAL_DISTANCE.min(CHEST_CLEARANCE * 2.)
            }) || homes
                .iter()
                .chain(&npcs)
                .chain(&players)
                .chain(&drops)
                .chain(&others)
                .any(|p| at.distance(*p) < CHEST_CLEARANCE)
            {
                continue;
            }
            if map.in_city(at) {
                continue;
            }
            if dungeon {
                if !map.rooms.is_empty() && !map.rooms.iter().any(|r| in_room(r, at)) {
                    continue;
                }
                if final_room.iter().any(|r| in_room(r, at))
                    || map
                        .rooms
                        .iter()
                        .any(|r| living_bosses.iter().any(|b| in_room(r, *b)) && in_room(r, at))
                    || bosses.iter().any(|b| at.distance(*b) < 8.)
                {
                    continue;
                }
            }
            return Some(at);
        }
        None
    }
    /// The level of the strongest monster of `zone`, and the average kill gold and the kinds present.
    fn chest_area_profile(&self, zone: usize) -> (u32, f64, Vec<String>) {
        let mut top = 1;
        let mut gold = 0.;
        let mut count = 0.;
        let mut kinds: Vec<String> = vec![];
        for s in self.slimes.iter().filter(|s| s.zone == zone) {
            top = top.max(s.level);
            gold += s.gold as f64;
            count += 1.;
            if !kinds.contains(&s.kind) && !is_boss(&s.kind) {
                kinds.push(s.kind.clone());
            }
        }
        (top, if count > 0. { gold / count } else { 0. }, kinds)
    }
    /// A player asks to open chest `id`.
    pub(super) fn open_chest(&mut self, session: u64, id: u64) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let refuse = |text: &str| {
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
        };
        if p.character.hp <= 0. {
            return refuse("You cannot open a chest while defeated.");
        }
        let Some(at) = self.chests.list.iter().position(|c| c.id == id) else {
            return match self.chests.finished.iter().find(|(f, _)| *f == id) {
                Some((_, true)) => refuse("Someone already opened this chest."),
                Some((_, false)) => refuse("That chest has vanished."),
                None => refuse("There is no such chest."),
            };
        };
        let chest = &self.chests.list[at];
        if chest.zone != p.character.zone || chest.left <= 0. {
            return refuse("There is no such chest.");
        }
        if p.character.point().distance(Point {
            x: chest.x,
            y: chest.y,
        }) > CHEST_OPEN_RANGE
        {
            return refuse("Move closer to open the chest.");
        }
        let (owner, name, zone, point) = (
            p.character.id.clone(),
            p.character.look.name.clone(),
            chest.zone,
            Point {
                x: chest.x,
                y: chest.y,
            },
        );
        self.chests.list.remove(at);
        self.chests.finish(id, true);
        if self.hidden_actor(&owner) {
            self.chest_say(zone, "A treasure chest was opened.");
        } else {
            self.chest_say(zone, &format!("{name} opened the treasure chest."));
        }
        self.emit_zone(
            zone,
            json!({"type":"event","kind":"chestOpen","actor":owner,"x":point.x,"y":point.y,"value":0,"crit":false}),
        );
        self.chest_contents(&owner, zone, point);
    }
    /// Rolls and drops what a chest holds, as an ordinary shared drop for the opener's party.
    pub(super) fn chest_contents(&mut self, owner: &str, zone: usize, point: Point) {
        let (top, average_gold, kinds) = self.chest_area_profile(zone);
        // The opener's rebirth drop multiplier reaches every roll below (docs/rebirth.md).
        let boost = self.drop_multiplier_of(owner);
        let gold = (average_gold * CHEST_GOLD_KILLS).round() as u32;
        if gold > 0 {
            let gold = self.pile_for(owner, gold);
            self.gold_drop(owner, zone, point, gold);
        }
        if !kinds.is_empty() {
            let kind = kinds[(self.random() * kinds.len() as f64) as usize % kinds.len()].clone();
            let count = 3 + (self.random() * 3.) as u32;
            let material = material(&kind);
            for _ in 0..count.min(5) {
                self.loot_stack(owner, zone, point, material, boost);
            }
        }
        for _ in 0..CHEST_GEAR_ROLLS * boost as usize {
            if self.maps[zone].final_boss == "null_hour" {
                let choice = self.random();
                if let Some(piece) = boss_piece_for("null_hour", &CHEST_SET_SLOTS, choice) {
                    self.loot_drop(owner, zone, point, &piece.id);
                }
                continue;
            }
            let rarity = boosted_ladder_rarity(self.random(), boost);
            let choice = self.random();
            if let Some(piece) = equipment_of_rarity(rarity, top, choice) {
                self.loot_drop(owner, zone, point, &piece.id);
            }
        }
        if self.maps[zone].final_boss != "null_hour"
            && let Some(gear) = roll_orange_boosted(boost, || self.random())
        {
            self.loot_drop_with_gear(owner, zone, point, &gear.item.clone(), Some(gear));
        }
        if self.is_instance(zone) {
            let pieces = copies(CHEST_SET_PIECE_CHANCE, boost, || self.random());
            for _ in 0..pieces {
                let boss = self.maps[zone].final_boss.clone();
                let choice = self.random();
                if let Some(piece) = boss_piece_for(&boss, &CHEST_SET_SLOTS, choice) {
                    self.set_piece_drop(owner, zone, point, piece);
                }
            }
        }
    }
    /// `spawn_chest` op of the test shortcuts: a chest next to the player (or on a placed tile) for browser checks.
    pub(super) fn debug_spawn_chest(
        &mut self,
        session: u64,
        distance: Option<f64>,
    ) -> Result<Value, String> {
        let p = self.players.get(&session).ok_or("Unknown session.")?;
        let (zone, here, face) = (p.character.zone, p.character.point(), p.face);
        let at = match distance {
            Some(d) if d.is_finite() && (0.5..=30.).contains(&d) => {
                let mut at = Point {
                    x: here.x + face.x * d,
                    y: here.y + face.y * d,
                };
                self.maps[zone].collide(&mut at, PLAYER_RADIUS);
                at
            }
            Some(_) => return Err("distance must be between 0.5 and 30 tiles.".into()),
            None => self
                .chest_spot(zone)
                .ok_or("No free tile for a chest in this zone.")?,
        };
        let id = self.entity();
        self.chests.list.push(Chest {
            id,
            zone,
            x: at.x,
            y: at.y,
            left: CHEST_LIFETIME,
            told: vec![],
        });
        Ok(json!({"id": id, "x": at.x, "y": at.y, "left": CHEST_LIFETIME}))
    }
    /// A dungeon copy closed or reset: its chests vanish without a message and its timer starts over.
    pub(super) fn clear_chests(&mut self, zone: usize) {
        let gone: Vec<u64> = self
            .chests
            .list
            .iter()
            .filter(|c| c.zone == zone)
            .map(|c| c.id)
            .collect();
        for id in gone {
            self.chests.finish(id, false);
        }
        self.chests.list.retain(|c| c.zone != zone);
        self.chests.timers.remove(&zone);
    }
}

#[cfg(test)]
mod tests {
    use super::super::wyrd_tests::{at, calm, drain, join, place, world};
    use super::*;

    const CRAGS: usize = 1;
    fn open_zones(w: &World) -> Vec<usize> {
        (0..w.maps.len())
            .filter(|&z| {
                w.maps[z].copies == 0
                    && w.maps[z].template.is_none()
                    && !w.maps[z].slimes.is_empty()
            })
            .collect()
    }

    #[test]
    fn the_constants_match_the_rules_document() {
        let doc = include_str!("../../../docs/chests.md");
        for (name, value) in [
            ("CHEST_ROLL_INTERVAL", "120 s"),
            ("CHEST_SPAWN_CHANCE", "0.10"),
            ("CHEST_LIFETIME", "180 s"),
            ("CHEST_MAX_PER_AREA", "1"),
            ("CHEST_OPEN_RANGE", "2.0 tiles"),
            ("CHEST_MIN_ARRIVAL_DISTANCE", "14 tiles"),
            ("CHEST_PLACEMENT_TRIES", "40"),
        ] {
            let row = doc
                .lines()
                .find(|l| l.contains(&format!("`{name}`")))
                .unwrap_or_else(|| panic!("{name}"));
            assert!(row.contains(value), "{name}: {row}");
        }
        assert_eq!(CHEST_ROLL_INTERVAL, 120.);
        assert_eq!(CHEST_SPAWN_CHANCE, 0.10);
        assert_eq!(CHEST_LIFETIME, 180.);
        assert_eq!(CHEST_MAX_PER_AREA, 1);
        assert_eq!(CHEST_OPEN_RANGE, 2.0);
        assert_eq!(CHEST_MIN_ARRIVAL_DISTANCE, 14.);
        assert_eq!(CHEST_PLACEMENT_TRIES, 40);
    }

    #[test]
    fn the_ladder_is_gray_62_green_30_blue_7_5_purple_half_a_percent() {
        assert_eq!(ladder_rarity(0.0), "common");
        assert_eq!(ladder_rarity(0.619), "common");
        assert_eq!(ladder_rarity(0.62), "uncommon");
        assert_eq!(ladder_rarity(0.919), "uncommon");
        assert_eq!(ladder_rarity(0.92), "rare");
        assert_eq!(ladder_rarity(0.994), "rare");
        assert_eq!(ladder_rarity(0.995), "epic");
        assert_eq!(ladder_rarity(0.999), "epic");
    }

    #[test]
    fn only_open_zones_with_monsters_are_areas_and_cities_never_are() {
        let w = world();
        let areas: Vec<usize> = (0..w.maps.len()).filter(|&z| w.chest_area(z)).collect();
        assert_eq!(areas, open_zones(&w));
        assert_eq!(
            areas.len(),
            19,
            "19 open zones, as docs/chest-eligibility.txt says"
        );
        assert!(!w.chest_area(4), "Skaldholm has no monsters");
        let dungeon = w.instances.iter().find(|i| i.template == 5).unwrap().zone;
        assert!(
            !w.chest_area(dungeon),
            "a dungeon copy nobody is in is not an area"
        );
    }

    #[test]
    fn every_open_zone_finds_a_reachable_tile_far_from_the_arrival_point() {
        let mut w = world();
        for zone in open_zones(&w) {
            let mut found = 0;
            for _ in 0..10 {
                if let Some(p) = w.chest_spot(zone) {
                    found += 1;
                    let map = &w.maps[zone];
                    let n = map.size as usize;
                    let steps = w.chests.fields[&zone][p.y as usize * n + p.x as usize];
                    assert!(
                        steps != u16::MAX && steps as f64 >= CHEST_MIN_ARRIVAL_DISTANCE,
                        "zone {zone}"
                    );
                    let mut q = p;
                    map.collide(&mut q, PLAYER_RADIUS);
                    assert!(
                        q.distance(p) < 1e-6,
                        "zone {zone}: the chest stands on free ground"
                    );
                    assert!(!map.in_city(p));
                }
            }
            assert!(found >= 5, "zone {zone} placed only {found} of 10 chests");
        }
    }

    #[test]
    fn an_occupied_area_rolls_every_interval_and_an_empty_one_pauses() {
        let mut w = world();
        calm(&mut w);
        w.chests.interval = 1.;
        let _rx = join(&mut w, 1, Class::Warrior);
        place(&mut w, 1, 0, at(60., 60.));
        // Empty zone 1 never starts counting; the occupied zone does.
        for _ in 0..(3. / TICK) as usize {
            w.step();
        }
        assert!(!w.chests.timers.contains_key(&CRAGS));
        assert!(w.chests.timers.contains_key(&0));
        // Leaving pauses the countdown; it is kept, not reset.
        let kept = w.chests.timers[&0];
        place(&mut w, 1, 4, at(60., 60.));
        for _ in 0..40 {
            w.step();
        }
        assert_eq!(w.chests.timers[&0], kept);
    }

    #[test]
    fn about_a_tenth_of_rolls_spawn_one_chest_and_only_one_at_a_time() {
        let mut w = world();
        calm(&mut w);
        w.chests.interval = 0.05;
        w.chests.rng = 12345;
        let _rx = join(&mut w, 1, Class::Warrior);
        place(&mut w, 1, 0, at(60., 60.));
        let mut spawned = 0;
        for _ in 0..2500 {
            let before = w.chests.list.len();
            w.step();
            if w.chests.list.len() > before {
                spawned += 1;
            }
            assert!(w.chests.list.iter().filter(|c| c.zone == 0).count() <= CHEST_MAX_PER_AREA);
            // Open each as it appears so the next roll can spawn.
            if let Some(c) = w.chests.list.first().cloned() {
                place(&mut w, 1, 0, at(c.x, c.y));
                w.open_chest(1, c.id);
                place(&mut w, 1, 0, at(60., 60.));
            }
        }
        let rolls = w.chests.rolls;
        assert!(rolls > 2000, "{rolls} rolls");
        let rate = spawned as f64 / rolls as f64;
        assert!(
            (rate - CHEST_SPAWN_CHANCE).abs() < 0.03,
            "{spawned}/{rolls} = {rate}"
        );
    }

    #[test]
    fn a_chest_vanishes_after_three_minutes_and_says_so() {
        let mut w = world();
        calm(&mut w);
        let mut rx = join(&mut w, 1, Class::Warrior);
        place(&mut w, 1, 0, at(60., 60.));
        assert!(w.spawn_chest(0));
        let id = w.chests.list[0].id;
        w.step();
        let said: Vec<String> = drain(&mut rx)
            .into_iter()
            .filter_map(|v| v["text"].as_str().map(str::to_owned))
            .collect();
        assert!(
            said.iter()
                .any(|t| t.contains("treasure chest has appeared") && t.contains("3 minutes")),
            "{said:?}"
        );
        assert_eq!(
            w.chests.list[0].left,
            CHEST_LIFETIME - TICK,
            "a new chest lives three minutes"
        );
        w.chests.list[0].left = 0.2;
        for _ in 0..8 {
            w.step();
        }
        assert!(w.chests.list.is_empty());
        let said: Vec<String> = drain(&mut rx)
            .into_iter()
            .filter_map(|v| v["text"].as_str().map(str::to_owned))
            .collect();
        assert!(
            said.contains(&"The treasure chest has vanished.".to_string()),
            "{said:?}"
        );
        w.open_chest(1, id);
        let err = drain(&mut rx);
        assert!(
            err.iter().any(|v| v["text"] == "That chest has vanished."),
            "{err:?}"
        );
    }

    #[test]
    fn opening_needs_range_and_a_living_hero_and_the_first_opener_wins() {
        let mut w = world();
        calm(&mut w);
        let mut rx1 = join(&mut w, 1, Class::Warrior);
        let mut rx2 = join(&mut w, 2, Class::Mage);
        place(&mut w, 1, 0, at(60., 60.));
        place(&mut w, 2, 0, at(61., 60.));
        assert!(w.spawn_chest(0));
        let chest = w.chests.list[0].clone();
        w.open_chest(1, chest.id);
        assert!(
            drain(&mut rx1)
                .iter()
                .any(|v| v["text"] == "Move closer to open the chest.")
        );
        assert_eq!(w.chests.list.len(), 1, "too far");
        place(&mut w, 1, 0, at(chest.x + CHEST_OPEN_RANGE + 0.5, chest.y));
        w.open_chest(1, chest.id);
        assert_eq!(w.chests.list.len(), 1, "just out of range");
        place(&mut w, 1, 0, at(chest.x + CHEST_OPEN_RANGE - 0.1, chest.y));
        place(&mut w, 2, 0, at(chest.x, chest.y + 1.));
        w.players.get_mut(&2).unwrap().character.hp = 0.;
        w.open_chest(2, chest.id);
        assert!(
            drain(&mut rx2)
                .iter()
                .any(|v| v["text"] == "You cannot open a chest while defeated.")
        );
        assert_eq!(w.chests.list.len(), 1, "the dead cannot open it");
        w.players.get_mut(&2).unwrap().character.hp = 10.;
        w.open_chest(1, chest.id);
        assert!(w.chests.list.is_empty());
        w.open_chest(2, chest.id);
        assert!(
            drain(&mut rx2)
                .iter()
                .any(|v| v["text"] == "Someone already opened this chest.")
        );
        assert!(w.drops.iter().any(|d| d.value > 0), "gold dropped");
        assert!(w.drops.iter().all(|d| d.zone == 0));
    }

    #[test]
    fn a_chest_holds_gold_a_material_and_two_gear_rolls_and_is_rolled_when_opened() {
        let mut w = world();
        calm(&mut w);
        let _rx = join(&mut w, 1, Class::Warrior);
        place(&mut w, 1, CRAGS, at(60., 60.));
        let before = w.drops.len();
        w.chest_contents(&w.players[&1].character.id.clone(), CRAGS, at(60., 60.));
        let drops = &w.drops[before..];
        let gold: u32 = drops.iter().map(|d| d.value).sum();
        let (_, average, kinds) = w.chest_area_profile(CRAGS);
        assert_eq!(gold, (average * 5.).round() as u32);
        let materials: Vec<_> = drops
            .iter()
            .filter_map(|d| d.item.as_deref())
            .filter(|id| item(id).is_some_and(|i| i.kind == "material"))
            .collect();
        assert!((3..=5).contains(&materials.len()), "{materials:?}");
        assert!(materials.iter().all(|m| *m == materials[0]));
        assert!(kinds.iter().any(|k| material(k) == materials[0]));
        let gear = drops
            .iter()
            .filter_map(|d| d.item.as_deref())
            .filter(|id| item(id).is_some_and(is_gear))
            .count();
        assert!(gear <= CHEST_GEAR_ROLLS + 1, "{gear}");
    }

    #[test]
    fn a_full_bag_loses_nothing_because_the_loot_lies_on_the_ground() {
        let mut w = world();
        calm(&mut w);
        let _rx = join(&mut w, 1, Class::Warrior);
        place(&mut w, 1, 0, at(60., 60.));
        assert!(w.spawn_chest(0));
        let c = w.chests.list[0].clone();
        place(&mut w, 1, 0, at(c.x, c.y));
        w.open_chest(1, c.id);
        assert!(!w.drops.is_empty());
        assert!(
            w.drops
                .iter()
                .all(|d| (d.x - c.x).abs() < 1e-9 && (d.y - c.y).abs() < 1e-9)
        );
        let chest_items: std::collections::BTreeSet<String> =
            w.drops.iter().filter_map(|d| d.item.clone()).collect();
        let filler: Vec<String> = ITEMS
            .iter()
            .filter(|i| i.kind != "bag" && !chest_items.contains(&i.id))
            .map(|i| i.id.clone())
            .take(w.players[&1].character.bag_capacity())
            .collect();
        let hero = &mut w.players.get_mut(&1).unwrap().character;
        for id in filler {
            if hero.bag_used() < hero.bag_capacity() {
                hero.add_item(&id, 1);
            }
        }
        assert_eq!(hero.bag_used(), hero.bag_capacity());
        let before = w.drops.iter().filter(|d| d.item.is_some()).count();
        for drop in &mut w.drops {
            drop.t = 1.;
        }
        w.update_drops();
        assert_eq!(
            w.drops.iter().filter(|d| d.item.is_some()).count(),
            before,
            "full bags keep the chest items on the ground"
        );
        assert!(
            w.players[&1].character.gold > 0,
            "the gold is still collected"
        );
    }

    #[test]
    fn a_dungeon_copy_rolls_only_while_active_and_loses_its_chest_when_it_resets() {
        let mut w = world();
        let copy = w.instances.iter().find(|i| i.template == 5).unwrap().zone;
        let _rx = join(&mut w, 1, Class::Warrior);
        let arrival = w.maps[copy].spawn;
        place(&mut w, 1, copy, arrival);
        assert!(!w.chest_area(copy), "not active yet");
        w.enter_instance(copy);
        assert!(w.chest_area(copy));
        assert!(
            w.spawn_chest(copy),
            "a tile fits inside the Undervault rooms"
        );
        let chest = w.chests.list[0].clone();
        let map = &w.maps[copy];
        assert!(map.rooms.iter().any(|r| in_room(r, at(chest.x, chest.y))));
        // The final boss's room is never used.
        let boss = w
            .slimes
            .iter()
            .find(|s| s.zone == copy && s.kind == map.final_boss)
            .unwrap()
            .point();
        assert!(
            map.rooms
                .iter()
                .filter(|r| in_room(r, boss))
                .all(|r| !in_room(r, at(chest.x, chest.y)))
        );
        // Cleared copies stop rolling.
        let index = w.instances.iter().position(|i| i.zone == copy).unwrap();
        w.instances[index].cleared = true;
        assert!(!w.chest_area(copy));
        w.instances[index].cleared = false;
        // The last hero leaves: the copy resets and the chest goes without a message.
        w.chests.timers.insert(copy, 5.);
        place(&mut w, 1, 0, at(60., 60.));
        w.step();
        assert!(w.chests.list.iter().all(|c| c.zone != copy));
        assert!(!w.chests.timers.contains_key(&copy));
    }

    #[test]
    fn a_late_arrival_is_told_once_and_the_snapshot_lists_the_chest() {
        let mut w = world();
        calm(&mut w);
        assert!(w.spawn_chest(0));
        let mut rx = join(&mut w, 1, Class::Warrior);
        place(&mut w, 1, 0, at(60., 60.));
        w.step();
        w.step();
        let told = drain(&mut rx)
            .into_iter()
            .filter(|v| {
                v["text"]
                    .as_str()
                    .is_some_and(|t| t.contains("treasure chest has appeared"))
            })
            .count();
        assert_eq!(told, 1);
        let snapshot = w.snapshot_for(0);
        assert_eq!(snapshot["chests"].as_array().unwrap().len(), 1);
        assert!(snapshot["chests"][0]["left"].as_f64().unwrap() > 170.);
        assert!(
            w.snapshot_for(CRAGS)["chests"]
                .as_array()
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn dungeon_copies_keep_chests_and_announcements_private() {
        let mut w = world();
        calm(&mut w);
        let copies: Vec<usize> = w
            .instances
            .iter()
            .filter(|i| i.template == 5)
            .map(|i| i.zone)
            .take(2)
            .collect();
        assert_eq!(copies.len(), 2);
        let mut first = join(&mut w, 1, Class::Warrior);
        let mut second = join(&mut w, 2, Class::Mage);
        for (session, zone) in [(1, copies[0]), (2, copies[1])] {
            let arrival = w.maps[zone].spawn;
            place(&mut w, session, zone, arrival);
            w.enter_instance(zone);
        }
        assert!(w.spawn_chest(copies[0]));
        w.step();
        let first_text = drain(&mut first);
        let second_text = drain(&mut second);
        assert!(first_text.iter().any(|v| {
            v["text"]
                .as_str()
                .is_some_and(|t| t.contains("treasure chest has appeared"))
        }));
        assert!(!second_text.iter().any(|v| {
            v["text"]
                .as_str()
                .is_some_and(|t| t.contains("treasure chest has appeared"))
        }));
        assert_eq!(
            w.snapshot_for(copies[0])["chests"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
        assert!(
            w.snapshot_for(copies[1])["chests"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        let id = w.chests.list[0].id;
        w.open_chest(2, id);
        assert!(
            drain(&mut second)
                .iter()
                .any(|v| v["text"] == "There is no such chest.")
        );
        assert_eq!(w.chests.list[0].id, id);
        let at = at(w.chests.list[0].x, w.chests.list[0].y);
        place(&mut w, 1, copies[0], at);
        w.open_chest(1, id);
        assert!(w.chests.list.is_empty());
        assert!(drain(&mut first).iter().any(|v| {
            v["text"]
                .as_str()
                .is_some_and(|t| t.contains("opened the treasure chest"))
        }));
        assert!(!drain(&mut second).iter().any(|v| {
            v["text"]
                .as_str()
                .is_some_and(|t| t.contains("opened the treasure chest"))
        }));
    }

    #[test]
    fn chest_survives_an_outdoor_reconnect_and_party_shares_its_pile() {
        let mut w = world();
        calm(&mut w);
        let (tx, mut first) = mpsc::channel(256);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let id = welcome["id"].as_str().unwrap().to_owned();
        let mut second = join(&mut w, 2, Class::Mage);
        let mate = w.players[&2].character.id.clone();
        place(&mut w, 1, 0, at(60., 60.));
        place(&mut w, 2, 0, at(61., 60.));
        w.social(
            1,
            SocialCommand::PartyInvite {
                id: Some(mate.clone()),
                name: None,
            },
        );
        w.social(2, SocialCommand::PartyAccept { id: id.clone() });
        assert_eq!(w.party_mates(&id).len(), 2);
        assert!(w.spawn_chest(0));
        let chest = w.chests.list[0].clone();
        w.leave(1);
        let (tx, mut resumed) = mpsc::channel(256);
        let resume = w.join(3, Some(token), None, tx).unwrap();
        assert_eq!(resume["id"], id);
        assert_eq!(resume["snapshot"]["chests"][0]["id"], chest.id);
        w.step();
        assert!(drain(&mut resumed).iter().any(|v| {
            v["text"]
                .as_str()
                .is_some_and(|t| t.contains("treasure chest has appeared"))
        }));
        place(&mut w, 3, 0, at(chest.x, chest.y));
        place(&mut w, 2, 0, at(chest.x + 1., chest.y));
        w.open_chest(3, chest.id);
        assert!(
            w.drops
                .iter()
                .any(|d| d.group.contains(&id) && d.group.contains(&mate))
        );
        assert!(drain(&mut second).iter().any(|v| {
            v["text"]
                .as_str()
                .is_some_and(|t| t.contains("opened the treasure chest"))
        }));
        let _ = drain(&mut first);
    }
}
