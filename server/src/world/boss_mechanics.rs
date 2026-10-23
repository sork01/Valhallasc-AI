//! The final boss mechanics engine (docs/boss-mechanics.md, `BOSSMECH-ENGINE`): one state machine per fight that runs
//! the data of `world/boss-mechanics.txt` against the live world. The data schema, the shapes and the fairness walk
//! are in `crate::bossmech`; this file is the part that touches players and monsters.
//!
//! A fight belongs to one boss slot, and a slot belongs to one dungeon copy, so two copies never share a timer, an
//! add or a shield. It starts when the boss is awake and fighting and ends the moment the boss dies, returns home or
//! its copy is reset: that is the wipe or the evade, and it puts every add back to sleep and every timer back to its
//! start (rule 6). The server alone decides every kill, shield and bar; the client only draws what `snapshot_for`
//! sends under `bossMech`.
//!
//! Adds are the sleeping monsters the map already knows how to hold (spawns with `ambush: <tag>`, dead until
//! something wakes them). A mechanic names the tag; the dungeon's data places the monsters.
use super::*;
use crate::bossmech::{
    self as bm, Block, BossDef, Cover, Effect, GapAt, MarkEffect, Mechanic, Rect, Shape, Side,
    SweepKind,
};
use std::collections::BTreeSet;
use std::sync::Arc;

/// An orb touches a player this close.
const ORB_REACH: f64 = 0.6;
/// A wall or lane hurts a player whose body overlaps it: the centre may be this far outside the band.
const BODY: f64 = PLAYER_RADIUS;
/// The bridge of light between a divided boss's bodies is drawn this long before it is lethal (rule 1: announced).
const BRIDGE_WARNING: f64 = 3.;
/// Seconds between the hits of a bridge that hurts instead of killing (`Split::bridge_hit`).
const BRIDGE_TICK: f64 = 1.;
/// How long a held body stays held after each refresh; refreshed every tick.
const HOLD: f64 = 0.2;
/// Charges the soft enrage of a static boss puts on every hero (owner, 2026-10-20), short of the limit.
const ENRAGE_STACKS: u32 = 11;
/// New spokes turn this long, dashed, before they hurt.
const SPOKES_ARM: f64 = 3.;

pub struct BossMech {
    /// Boss kind -> its mechanics. Tests replace it.
    pub(super) table: BTreeMap<String, Arc<BossDef>>,
    pub(super) fights: BTreeMap<usize, Fight>,
    next_id: u64,
    /// Where a fighter who is not at a keyboard is running to, kept between ticks (`boss_play.rs`).
    pub(super) plans: BTreeMap<u64, Point>,
    /// The brazier each fighter has taken to light (`boss_play.rs`).
    pub(super) stations: BTreeMap<u64, Point>,
    /// The half of a divided boss each fighter is working on, kept between ticks so the party does not change sides of
    /// the lethal bridge with every blow (`boss_play.rs`).
    pub(super) halves: BTreeMap<u64, usize>,
    /// Seconds a break had left when it was broken, one per dirge: what the harness reads to tune a bar.
    #[cfg(test)]
    pub(super) spare: Vec<f64>,
}
impl BossMech {
    pub fn new() -> Self {
        Self::with_table(bm::shipped())
    }
    pub fn with_table(table: BTreeMap<String, BossDef>) -> Self {
        Self {
            table: table.into_iter().map(|(k, v)| (k, Arc::new(v))).collect(),
            fights: BTreeMap::new(),
            next_id: 1,
            plans: BTreeMap::new(),
            stations: BTreeMap::new(),
            halves: BTreeMap::new(),
            #[cfg(test)]
            spare: vec![],
        }
    }
    /// A final boss fight is running in `zone` (a dungeon copy): whoever falls there stays down until it ends.
    pub(super) fn fight_in(&self, zone: usize) -> bool {
        self.fights.values().any(|f| f.zone == zone)
    }
}

/// Something running right now. Every variant knows the mechanic that started it (`mech`, an index of the boss's list).
enum Live {
    Zone(ZoneLive),
    Mark(MarkLive),
    Puddle(PuddleLive),
    Walls(WallsLive),
    Break(BreakLive),
    Gaze(GazeLive),
    Raid(raid_bosses::RaidLive),
}
impl Live {
    fn mech(&self) -> usize {
        match self {
            Self::Zone(z) => z.mech,
            Self::Mark(m) => m.mech,
            Self::Puddle(p) => p.mech,
            Self::Walls(w) => w.mech,
            Self::Break(b) => b.mech,
            Self::Gaze(g) => g.mech,
            Self::Raid(r) => r.mech,
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum ZPhase {
    Cast,
    /// Waiting between two casts of a `repeat`.
    Gap,
    /// Landed once; the same shape lands again after the next echo delay.
    Echo,
    Linger,
}
struct ZoneLive {
    mech: usize,
    id: u64,
    areas: Vec<Shape>,
    round: u32,
    phase: ZPhase,
    left: f64,
    total: f64,
    echo_i: usize,
    reported: BTreeSet<u64>,
}
struct MarkLive {
    mech: usize,
    id: u64,
    targets: Vec<u64>,
    wave: u32,
    gap: bool,
    left: f64,
    total: f64,
}
struct PuddleLive {
    mech: usize,
    id: u64,
    bearer: u64,
    areas: Vec<Shape>,
    left: f64,
    reported: BTreeSet<u64>,
}
struct WallLive {
    side: Side,
    /// The centre line of the band, along the axis it travels.
    pos: f64,
    /// Where the gap is centred, along the wall.
    gap_at: f64,
}
struct WallsLive {
    mech: usize,
    id: u64,
    warn_left: f64,
    warn_total: f64,
    walls: Vec<WallLive>,
}
struct BreakLive {
    mech: usize,
    left: f64,
    total: f64,
    needed: f64,
    dealt: f64,
}
struct GazeLive {
    mech: usize,
    id: u64,
    /// Seconds of warning left.
    left: f64,
    total: f64,
    from: Point,
    /// While the beam turns: the angle it points at and the radians it has turned so far.
    angle: f64,
    turned: f64,
    /// Cover that has shielded someone during this gaze (it takes one hit per gaze).
    shielded: BTreeSet<usize>,
}
struct SpokesLive {
    mech: usize,
    angle: f64,
    dir: f64,
    reverse_in: f64,
    warn_left: f64,
    /// Seconds the new spokes are shown (dashed) and turn but do not hurt yet: they begin at a random angle, possibly
    /// right where the party stands, and rule 1 says a lethal thing is announced first.
    arm: f64,
}
struct CoverLive {
    cover: Cover,
    regrow: f64,
    hits: u8,
    broken: bool,
    broken_for: f64,
}
struct Lit {
    at: Point,
    progress: f64,
    lit_left: f64,
}
struct LitGroup {
    mech: usize,
    r: f64,
    hold_for: f64,
    lit_for: f64,
    snuff_every: f64,
    snuff_in: f64,
    points: Vec<Lit>,
}
struct Orb {
    at: Point,
    target: u64,
    life: f64,
    speed: f64,
    tag: String,
    hold: f64,
}
struct Frozen {
    cocoon: usize,
    left: f64,
    name: String,
}
struct RodLive {
    at: Point,
    dark_left: f64,
}
/// Static: the charge each hero carries, the seconds each is grounded, the rods and the bursts still showing.
struct StaticLive {
    rods: Vec<RodLive>,
    rod_r: f64,
    limit: u32,
    warn_at: u32,
    charges: BTreeMap<u64, u32>,
    grounded: BTreeMap<u64, f64>,
    /// A detonation still on the floor: where, how wide, seconds left.
    bursts: Vec<(Point, f64, f64)>,
    /// The boss's enrage has loaded its stacks onto everyone (once per fight).
    enraged: bool,
}
struct BloomLive {
    slot: usize,
    left: f64,
    heal: f64,
    then: Option<String>,
}
struct ShieldLive {
    tag: String,
    adds: Vec<usize>,
    heal_per_s: f64,
    name: String,
}

pub(super) struct Fight {
    boss: usize,
    zone: usize,
    arena: Rect,
    clock: f64,
    /// Per mechanic: seconds until a timed one starts again.
    timer: Vec<f64>,
    /// Per mechanic: the steps of a threshold block that have fired (bit `n`).
    fired: Vec<u32>,
    live: Vec<Live>,
    shield: Option<ShieldLive>,
    /// Every sleeping monster this fight woke, to put back to sleep when it ends.
    woken: Vec<usize>,
    /// Woken monsters that stand still and never attack (pearls, seeds, cocoons).
    still: BTreeSet<usize>,
    stun_left: f64,
    vulnerable: f64,
    lit: Vec<LitGroup>,
    spokes: Vec<SpokesLive>,
    cover: Vec<CoverLive>,
    frozen: BTreeMap<u64, Frozen>,
    orbs: Vec<Orb>,
    blooms: Vec<BloomLive>,
    /// The other body of a divided boss.
    partner: Option<usize>,
    /// Seconds the bridge of light is shown but not yet lethal after a boss divides.
    bridge_wait: f64,
    /// Seconds until a bridge that hurts hits again.
    bridge_tick: f64,
    /// Bodies that fell while the other lives, and the seconds until they rise.
    downed: BTreeMap<usize, f64>,
    /// The twins have joined into one boss that takes this share of every blow (`Split::merge_defense`).
    merged: Option<f64>,
    /// The boss's soft enrage has begun (`items::enrage`): its gaze starts at once and its cover is gone.
    enraged: bool,
    /// A failed burst phase began the enrage: the boss's clock never falls below this (0 = not forced).
    enrage_floor: f64,
    banner: Option<(String, f64)>,
    stat: Option<StaticLive>,
}

impl Fight {
    /// Test builds: the shield's helpers still alive, for the harness trace.
    #[cfg(test)]
    pub(super) fn frozen_count(&self) -> usize {
        self.frozen.len()
    }
    #[cfg(test)]
    pub(super) fn live_gaze(&self) -> bool {
        self.live.iter().any(|l| matches!(l, Live::Gaze(_)))
    }
    #[cfg(test)]
    pub(super) fn shield_alive(&self, w: &World) -> Option<usize> {
        self.shield
            .as_ref()
            .map(|s| s.adds.iter().filter(|a| !w.slimes[**a].dead).count())
    }
}

/// What `hit_slime` should do with a blow.
pub(super) enum Incoming {
    /// The monster takes this much.
    Damage(f64),
    /// A shield or a downed body: nothing gets through.
    Immune,
}

impl World {
    /// Test servers only (`VALHALLA_TEST_COMMANDS=1` and `VALHALLA_BOSSMECH_FILE`): replaces the shipped table with the one in
    /// `path`, so a browser can watch a mechanic that no shipped boss has yet. The file obeys the same rules as the shipped one.
    pub fn load_boss_table_file(&mut self, path: &str) -> Result<(), String> {
        let text = std::fs::read_to_string(path).map_err(|e| format!("{path}: {e}"))?;
        let table: BTreeMap<String, BossDef> =
            serde_json::from_str(&text).map_err(|e| format!("{path}: {e}"))?;
        for (kind, def) in &table {
            bm::validate(kind, def)?;
        }
        self.boss = BossMech::with_table(table);
        Ok(())
    }

    // -----------------------------------------------------------------------------------------------------------
    // Hooks the rest of the world calls
    // -----------------------------------------------------------------------------------------------------------

    /// Once per tick, after the monsters have moved.
    pub(super) fn update_boss_mechanics(&mut self) {
        if self.boss.table.is_empty() && self.boss.fights.is_empty() {
            return;
        }
        let bosses: Vec<usize> = self
            .slimes
            .iter()
            .filter(|s| self.boss.table.contains_key(&s.kind))
            .map(|s| s.id)
            .collect();
        let stale: Vec<usize> = self
            .boss
            .fights
            .keys()
            .copied()
            .filter(|id| !self.boss_engaged(*id))
            .collect();
        for id in stale {
            self.end_boss_fight(id);
        }
        for id in bosses {
            if !self.boss_engaged(id) {
                continue;
            }
            let mut fight = match self.boss.fights.remove(&id) {
                Some(f) => f,
                None => self.begin_boss_fight(id),
            };
            self.tick_boss_fight(&mut fight);
            self.boss.fights.insert(id, fight);
        }
    }

    /// The boss is alive, awake and fighting (not walking home), in a copy someone is in.
    fn boss_engaged(&self, id: usize) -> bool {
        let s = &self.slimes[id];
        self.boss.table.contains_key(&s.kind)
            && !s.dead
            && !self.zone_idle(s.zone)
            && !matches!(
                s.state.as_str(),
                "idle" | "wander" | "return" | "waiting" | "dead"
            )
    }

    /// Ends a fight the way a wipe, an evade or a kill does: the sleepers sleep, the frozen walk, the timers go.
    pub(super) fn end_boss_fight(&mut self, id: usize) {
        let Some(fight) = self.boss.fights.remove(&id) else {
            return;
        };
        for slot in fight.woken.iter().copied().chain(fight.partner) {
            if self.spawns[slot].ambush.is_some() {
                self.slimes[slot] = self.dormant_enemy(slot);
            }
        }
        for session in fight.frozen.keys() {
            if let Some(p) = self.players.get_mut(session) {
                p.frozen = false;
            }
        }
        self.slimes[id].set_root_left = 0.;
    }

    /// A dungeon copy was reset: no fight survives it.
    pub(super) fn reset_boss_zone(&mut self, zone: usize) {
        let ids: Vec<usize> = self
            .boss
            .fights
            .iter()
            .filter(|(_, f)| f.zone == zone)
            .map(|(id, _)| *id)
            .collect();
        for id in ids {
            self.end_boss_fight(id);
        }
    }

    /// Asked by `hit_slime` before a blow lands.
    pub(super) fn boss_incoming(&self, id: usize, damage: f64) -> Incoming {
        let Some(fight) = self.fight_of(id) else {
            return Incoming::Damage(damage);
        };
        if fight.shield.is_some() && id == fight.boss {
            return Incoming::Immune;
        }
        if fight.downed.contains_key(&id) {
            return Incoming::Immune;
        }
        let mut damage = damage;
        if fight.stun_left > 0. && id == fight.boss {
            damage *= 1. + fight.vulnerable;
        }
        if let Some(defense) = fight.merged
            && id == fight.boss
        {
            damage *= defense;
        }
        // A body that would fall while its other half lives is left on one health and downed instead.
        if let Some(partner) = fight.partner {
            let other = if id == fight.boss {
                partner
            } else {
                fight.boss
            };
            let s = &self.slimes[id];
            if damage >= s.hp && !self.slimes[other].dead && !fight.downed.contains_key(&other) {
                return Incoming::Damage((s.hp - 1.).max(0.));
            }
        }
        Incoming::Damage(damage)
    }

    /// After a blow landed: break bars fill, a body goes down, a divided boss falls together.
    pub(super) fn boss_after_hit(&mut self, id: usize, session: u64, dealt: f64, killed: bool) {
        let Some(boss) = self.fight_of(id).map(|f| f.boss) else {
            return;
        };
        let (other, other_down) = {
            let fight = &self.boss.fights[&boss];
            let other = fight.partner.map(|p| if id == boss { p } else { boss });
            (other, other.is_some_and(|o| fight.downed.contains_key(&o)))
        };
        if let Some(fight) = self.boss.fights.get_mut(&boss) {
            for live in &mut fight.live {
                if let Live::Break(b) = live {
                    b.dealt += dealt;
                }
            }
        }
        if id == boss && !killed && dealt > 0. {
            self.add_static_charge(boss, session);
        }
        if killed && other_down {
            // The second body fell while the first lay downed: both are finished.
            let other = other.unwrap();
            if let Some(fight) = self.boss.fights.get_mut(&boss) {
                fight.downed.remove(&other);
            }
            self.hit_slime(other, session, 1e12, false);
            return;
        }
        if !killed
            && self.slimes[id].hp <= 1.
            && let Some(other) = other
            && !self.slimes[other].dead
        {
            if let Some(split) = self.split_def(boss).filter(|s| s.merge_hp > 0.) {
                // The twins join again: the Cinder goes back to sleep and the Heart carries on alone on a fixed share
                // of its health, with more defense.
                let (zone, at) = (self.slimes[boss].zone, self.slimes[boss].point());
                if let Some(cinder) = self.boss.fights.get(&boss).and_then(|f| f.partner) {
                    self.slimes[cinder] = self.dormant_enemy(cinder);
                }
                let s = &mut self.slimes[boss];
                s.hp = (s.max_hp * split.merge_hp).max(2.);
                if let Some(fight) = self.boss.fights.get_mut(&boss) {
                    fight.merged = Some(split.merge_defense);
                    fight.downed.clear();
                    fight.bridge_wait = 0.;
                    fight.banner = Some(("Twin Suns".into(), 4.));
                }
                self.mech_event(zone, "rise", "Twin Suns", at, 0.);
                return;
            }
            let revive = self.split_def(boss).map_or(10., |s| s.revive_after);
            if let Some(fight) = self.boss.fights.get_mut(&boss) {
                fight.downed.insert(id, revive);
            }
            let (zone, at) = (self.slimes[id].zone, self.slimes[id].point());
            self.mech_event(zone, "down", "", at, revive);
        }
    }

    /// A hero landed a blow on the boss: one more charge of Static, and a detonation at the limit.
    fn add_static_charge(&mut self, boss: usize, session: u64) {
        let share = {
            let s = &self.slimes[boss];
            if s.max_hp > 0. { s.hp / s.max_hp } else { 0. }
        };
        let Some(def) = self.boss.table.get(&self.slimes[boss].kind).cloned() else {
            return;
        };
        let Some((name, t)) = def.mechanics.iter().find_map(|m| match &m.block {
            Block::Static(t) if m.active_at(share) => Some((m.name.clone(), t.clone())),
            _ => None,
        }) else {
            return;
        };
        let Some(at) = self.players.get(&session).map(|p| p.character.point()) else {
            return;
        };
        let zone = self.slimes[boss].zone;
        let Some(fight) = self.boss.fights.get_mut(&boss) else {
            return;
        };
        let Some(st) = fight.stat.as_mut() else {
            return;
        };
        if st.grounded.contains_key(&session) {
            return;
        }
        let before = st.charges.get(&session).copied().unwrap_or(0);
        let now = before + t.per_hit;
        if now < t.limit {
            st.charges.insert(session, now);
            if before < t.warn_at && now >= t.warn_at {
                fight.banner = Some((name, 4.));
            }
            return;
        }
        st.charges.insert(session, 0);
        st.bursts.push((at, t.r, 0.8));
        let victims: Vec<u64> = self
            .mech_players(zone)
            .into_iter()
            .filter(|(_, p)| p.distance(at) <= t.r)
            .map(|(s, _)| s)
            .collect();
        for victim in victims {
            self.mech_kill(victim, &name, boss);
        }
        self.mech_event(zone, "land", &name, at, t.r);
    }

    /// A failed overload burst (`Break::overload`): one hero who is not grounded, picked at random, is loaded to the
    /// Static limit and detonates where they stand, taking everyone within the burst radius with them.
    fn overload(&mut self, fight: &mut Fight, name: &str) {
        let boss = fight.boss;
        let Some(def) = self.boss.table.get(&self.slimes[boss].kind).cloned() else {
            return;
        };
        let Some(r) = def.mechanics.iter().find_map(|m| match &m.block {
            Block::Static(t) => Some(t.r),
            _ => None,
        }) else {
            return;
        };
        let zone = fight.zone;
        let players = self.mech_players(zone);
        let grounded = |s: &u64| {
            fight
                .stat
                .as_ref()
                .is_some_and(|st| st.grounded.contains_key(s))
        };
        let chosen: Vec<(u64, Point)> = players
            .iter()
            .copied()
            .filter(|(s, _)| !grounded(s))
            .collect();
        if chosen.is_empty() {
            return;
        }
        let mut rng = self.mech_rng();
        let (session, at) = chosen[((rng() * chosen.len() as f64) as usize).min(chosen.len() - 1)];
        if let Some(st) = fight.stat.as_mut() {
            st.charges.insert(session, 0);
            st.bursts.push((at, r, 0.8));
        }
        for (victim, p) in players {
            if p.distance(at) <= r {
                self.mech_kill(victim, name, boss);
            }
        }
        self.mech_event(zone, "land", name, at, r);
    }

    /// Rods clear a hero who stands on a ready one; the timers of the charge, the grounding, the rods and the bursts run.
    fn tick_static(&mut self, fight: &mut Fight, m: &Mechanic, t: &bm::Static) {
        let players = self.mech_players(fight.zone);
        let boss = &self.slimes[fight.boss];
        let enraged = self.tuned_enrage_factor(boss.zone, &boss.kind, boss.fight) > 1.;
        let Some(st) = fight.stat.as_mut() else {
            return;
        };
        if enraged && !st.enraged {
            // The enrage loads every hero that is not grounded with `ENRAGE_STACKS`, short of the limit: the next
            // blow on the boss detonates them unless a rod clears the charge first.
            st.enraged = true;
            for (session, _) in &players {
                if !st.grounded.contains_key(session) {
                    let now = st.charges.get(session).copied().unwrap_or(0) + ENRAGE_STACKS;
                    st.charges
                        .insert(*session, now.min(t.limit.saturating_sub(1)));
                }
            }
            fight.banner = Some((m.name.clone(), 4.));
        }
        for r in &mut st.rods {
            r.dark_left = (r.dark_left - TICK).max(0.);
        }
        st.grounded.retain(|_, left| {
            *left -= TICK;
            *left > 0.
        });
        st.bursts.retain_mut(|b| {
            b.2 -= TICK;
            b.2 > 0.
        });
        st.charges
            .retain(|s, _| players.iter().any(|(p, _)| p == s));
        for (session, at) in &players {
            if st.grounded.contains_key(session) {
                continue;
            }
            let touched = st
                .rods
                .iter_mut()
                .find(|r| r.dark_left <= 0. && r.at.distance(*at) <= st.rod_r);
            if let Some(rod) = touched {
                rod.dark_left = t.dark;
                st.charges.remove(session);
                st.grounded.insert(*session, t.immune.max(TICK));
                let (zone, rod_at) = (fight.zone, rod.at);
                self.mech_event(zone, "shield", &m.name, rod_at, 0.);
            }
        }
    }

    fn split_def(&self, boss: usize) -> Option<bm::Split> {
        let def = self.boss.table.get(&self.slimes[boss].kind)?;
        def.mechanics.iter().find_map(|m| match &m.block {
            Block::Split(s) => Some(s.clone()),
            _ => None,
        })
    }

    /// The fight a slot belongs to: its own, or the one it is the divided partner of.
    fn fight_of(&self, id: usize) -> Option<&Fight> {
        self.boss
            .fights
            .get(&id)
            .or_else(|| self.boss.fights.values().find(|f| f.partner == Some(id)))
    }

    // -----------------------------------------------------------------------------------------------------------
    // Fight set-up and the tick
    // -----------------------------------------------------------------------------------------------------------

    fn begin_boss_fight(&mut self, id: usize) -> Fight {
        let s = &self.slimes[id];
        let def = self.boss.table[&s.kind].clone();
        let zone = s.zone;
        let arena = bm::arena_for_boss(&self.maps[zone], Point { x: s.hx, y: s.hy }, &def);
        let timer = def
            .mechanics
            .iter()
            .map(|m| match &m.block {
                Block::Zone(z) => z.first.unwrap_or(z.every),
                Block::Mark(k) => k.first.unwrap_or(k.every),
                Block::Sweep(w) => w.first.unwrap_or(w.every),
                Block::Break(b) => b.first.unwrap_or(b.every),
                Block::Gaze(g) => g.first.unwrap_or(g.every),
                Block::Adds(a) => a.first.unwrap_or(a.every),
                Block::Stasis(a) => a.first.unwrap_or(a.every),
                Block::Tether(t) => t.first,
                Block::Gust(g) => g.first,
                Block::Soak(s) => s.first,
                _ => 0.,
            })
            .collect();
        let mut lit = vec![];
        let mut cover = vec![];
        for (i, m) in def.mechanics.iter().enumerate() {
            match &m.block {
                Block::Hold(h) => lit.push(LitGroup {
                    mech: i,
                    r: h.r,
                    hold_for: h.hold_for,
                    lit_for: h.lit_for,
                    snuff_every: h.snuff_every,
                    snuff_in: h.snuff_every,
                    points: h
                        .points
                        .iter()
                        .map(|p| Lit {
                            at: Point { x: p[0], y: p[1] },
                            progress: 0.,
                            lit_left: 0.,
                        })
                        .collect(),
                }),
                Block::Gaze(g) => {
                    for c in &g.cover {
                        // Low-health variants describe the same physical pillars. Keep their damage when the
                        // variant changes instead of stacking a fresh, invisible copy behind each broken one.
                        if !cover.iter().any(|p: &CoverLive| {
                            p.cover.x == c.x && p.cover.y == c.y && p.cover.r == c.r
                        }) {
                            cover.push(CoverLive {
                                cover: *c,
                                regrow: g.regrow,
                                hits: 0,
                                broken: false,
                                broken_for: 0.,
                            });
                        }
                    }
                }
                _ => {}
            }
        }
        Fight {
            boss: id,
            zone,
            arena,
            clock: 0.,
            timer,
            fired: vec![0; def.mechanics.len()],
            live: vec![],
            shield: None,
            woken: vec![],
            still: BTreeSet::new(),
            stun_left: 0.,
            vulnerable: 0.,
            lit,
            spokes: vec![],
            cover,
            frozen: BTreeMap::new(),
            orbs: vec![],
            blooms: vec![],
            partner: None,
            bridge_wait: 0.,
            bridge_tick: 0.,
            downed: BTreeMap::new(),
            merged: None,
            enraged: false,
            enrage_floor: 0.,
            banner: None,
            stat: def.mechanics.iter().find_map(|m| match &m.block {
                Block::Static(t) => Some(StaticLive {
                    rods: t
                        .rods
                        .iter()
                        .map(|r| RodLive {
                            at: Point { x: r[0], y: r[1] },
                            dark_left: 0.,
                        })
                        .collect(),
                    rod_r: t.rod_r,
                    limit: t.limit,
                    warn_at: t.warn_at,
                    charges: BTreeMap::new(),
                    grounded: BTreeMap::new(),
                    bursts: vec![],
                    enraged: false,
                }),
                _ => None,
            }),
        }
    }

    /// The players a mechanic may target: awake, alive, in the zone, not in a city, not hidden, not frozen.
    fn mech_players(&self, zone: usize) -> Vec<(u64, Point)> {
        self.players
            .iter()
            .filter(|(_, p)| {
                p.character.zone == zone
                    && p.character.hp > 0.
                    && p.character.spark_travel.is_none()
                    && !p.is_hidden()
                    && !p.frozen
                    && !self.maps[zone].in_city(p.character.point())
            })
            .map(|(s, p)| (*s, p.character.point()))
            .collect()
    }

    /// A deterministic stream of numbers for one choice, drawn from the world's own generator.
    fn mech_rng(&mut self) -> impl FnMut() -> f64 + use<> {
        let mut state = (self.random() * 4294967296.) as u64 ^ 0x9E37_79B9_7F4A_7C15;
        move || {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            (state >> 11) as f64 / (1u64 << 53) as f64
        }
    }

    fn fresh_id(&mut self) -> u64 {
        let id = self.boss.next_id;
        self.boss.next_id += 1;
        id
    }

    fn mech_event(&self, zone: usize, phase: &str, name: &str, at: Point, value: f64) {
        self.emit_zone(
            zone,
            json!({"type":"event","kind":"bossmech","phase":phase,"name":name,"actor":"","x":at.x,"y":at.y,"value":value,"crit":false}),
        );
    }

    fn tick_boss_fight(&mut self, fight: &mut Fight) {
        let id = fight.boss;
        let def = self.boss.table[&self.slimes[id].kind].clone();
        fight.clock += TICK;
        if let Some((_, left)) = &mut fight.banner {
            *left -= TICK;
        }
        if fight.banner.as_ref().is_some_and(|(_, left)| *left <= 0.) {
            fight.banner = None;
        }
        let share = {
            let s = &self.slimes[id];
            if s.max_hp > 0. { s.hp / s.max_hp } else { 0. }
        };
        if fight.enrage_floor > 0. {
            let s = &mut self.slimes[id];
            s.fight = s.fight.max(fight.enrage_floor);
        }
        // Stun: the boss neither moves nor strikes, and takes extra damage.
        if fight.stun_left > 0. {
            fight.stun_left -= TICK;
            self.hold_still(id);
        }
        for slot in fight.still.iter().copied().collect::<Vec<_>>() {
            if !self.slimes[slot].dead {
                self.hold_still(slot);
            }
        }
        self.tick_split(fight, &def);
        for (i, m) in def.mechanics.iter().enumerate() {
            self.tick_mechanic(fight, i, m, share);
        }
        let mut live = std::mem::take(&mut fight.live);
        live.retain_mut(|l| self.tick_live(fight, &def, l));
        live.append(&mut fight.live);
        fight.live = live;
        self.tick_orbs_and_frozen(fight);
        self.tick_blooms(fight);
        self.tick_cover(fight);
        self.tick_shield(fight);
    }

    /// Keeps a monster where it stands for another moment: rooted, and unable to begin an attack.
    fn hold_still(&mut self, slot: usize) {
        let s = &mut self.slimes[slot];
        s.set_root_left = s.set_root_left.max(HOLD);
        s.atk_cd = s.atk_cd.max(HOLD);
    }

    fn tick_mechanic(&mut self, fight: &mut Fight, i: usize, m: &Mechanic, share: f64) {
        let id = fight.boss;
        let zone = fight.zone;
        let active = m.active_at(share);
        // Continuous blocks and thresholds first.
        match &m.block {
            Block::Hold(_) => {
                self.tick_hold(fight, i);
                return;
            }
            Block::Sweep(s) if matches!(s.kind, SweepKind::Spokes { .. }) => {
                self.tick_spokes(fight, i, m, active);
                return;
            }
            Block::Static(t) => {
                if active {
                    self.tick_static(fight, m, t);
                }
                return;
            }
            Block::Break(b) if b.at.is_some() => {
                self.tick_burst(fight, i, m, b);
                return;
            }
            Block::Shield(s) => {
                for (n, step) in s.steps.iter().enumerate() {
                    if fight.fired[i] & (1 << n) == 0 && share <= step.hp {
                        fight.fired[i] |= 1 << n;
                        self.raise_shield(fight, &m.name, step, s.heal_per_s);
                    }
                }
                return;
            }
            Block::Split(s) => {
                if fight.fired[i] == 0 && share <= s.hp {
                    fight.fired[i] = 1;
                    self.divide_boss(fight, &m.name, s);
                }
                return;
            }
            _ => {}
        }
        if !active {
            return;
        }
        // `every` is counted from one start to the next, so the timer runs while the ability is being cast too.
        fight.timer[i] -= TICK;
        if fight.timer[i] > 0. || fight.live.iter().any(|l| l.mech() == i) {
            return;
        }
        if matches!(m.block, Block::Tether(_) | Block::Gust(_) | Block::Soak(_))
            && fight.live.iter().any(|l| matches!(l, Live::Raid(_)))
        {
            return; // A low-health escalation waits for the current announced cast to finish.
        }
        let players = self.mech_players(zone);
        if players.is_empty() {
            return;
        }
        let at = self.slimes[id].point();
        match &m.block {
            Block::Tether(_) | Block::Gust(_) | Block::Soak(_) => {
                self.start_raid_cast(fight, i, m);
            }
            Block::Zone(z) => {
                fight.timer[i] = z.every;
                self.start_zone(fight, i, m, z, 0);
            }
            Block::Mark(k) => {
                fight.timer[i] = k.every;
                self.start_mark(fight, i, m, k, 0, &players);
            }
            Block::Sweep(s) => {
                fight.timer[i] = s.every;
                self.start_walls(fight, i, m, s);
            }
            Block::Break(b) => {
                fight.timer[i] = b.every;
                let needed = b.bar * self.slimes[id].max_hp;
                fight.live.push(Live::Break(BreakLive {
                    mech: i,
                    left: b.cast,
                    total: b.cast,
                    needed,
                    dealt: 0.,
                }));
                self.mech_event(zone, "cast", &m.name, at, b.cast);
                fight.banner = Some((m.name.clone(), b.cast));
            }
            Block::Gaze(g) => {
                fight.timer[i] = g.every;
                let fresh = self.fresh_id();
                let aim = players[0].1;
                fight.live.push(Live::Gaze(GazeLive {
                    mech: i,
                    id: fresh,
                    left: g.cast,
                    total: g.cast,
                    from: at,
                    angle: (aim.y - at.y).atan2(aim.x - at.x),
                    turned: 0.,
                    shielded: BTreeSet::new(),
                }));
                self.mech_event(zone, "cast", &m.name, at, g.cast);
                fight.banner = Some((m.name.clone(), g.cast));
            }
            Block::Adds(a) => {
                fight.timer[i] = a.every;
                for slot in self.wake_adds(fight, &a.tag, a.count, a.scatter, a.still) {
                    if let Some(b) = &a.bloom {
                        fight.blooms.push(BloomLive {
                            slot,
                            left: b.after,
                            heal: b.heal,
                            then: b.then.clone(),
                        });
                    }
                }
                self.mech_event(zone, "cast", &m.name, at, 0.);
                fight.banner = Some((m.name.clone(), 3.));
            }
            Block::Stasis(s) => {
                fight.timer[i] = s.every;
                self.launch_orbs(fight, &m.name, s, &players);
                self.mech_event(zone, "cast", &m.name, at, s.life);
                fight.banner = Some((m.name.clone(), 3.));
            }
            _ => {}
        }
    }

    // -----------------------------------------------------------------------------------------------------------
    // Hurting players
    // -----------------------------------------------------------------------------------------------------------

    /// Kills `session` with the named ability, or, for a god-mode player, says what would have. `false`: untouched.
    fn mech_kill(&mut self, session: u64, ability: &str, boss: usize) -> bool {
        let Some(p) = self.players.get(&session) else {
            return false;
        };
        let zone = p.character.zone;
        if p.character.hp <= 0.
            || p.frozen
            || p.is_hidden()
            || p.character.spark_travel.is_some()
            || self.maps[zone].in_city(p.character.point())
        {
            return false;
        }
        if bm::GOD_MODE_BLOCKS && (self.god_mode || p.god) {
            let text = bm::death_message(ability, true);
            let _ = p.peer.try_send(json!({"type":"system","text":text}));
            return false;
        }
        let kind = self.slimes[boss].kind.clone();
        let level = self.slimes[boss].level;
        let point = p.character.point();
        let actor = p.character.id.clone();
        let p = self.players.get_mut(&session).unwrap();
        p.combat_left = 5.;
        p.character.mounted = false;
        p.character.hp = 0.;
        p.last_hurt = self.time;
        p.hurt = 0.25;
        p.dead_time = 0.;
        p.fallen = true;
        p.attack = 0.;
        p.buffs.clear();
        p.stop();
        p.apply_death_penalty();
        let text = bm::death_message(ability, false);
        let _ = p.peer.try_send(json!({"type":"system","text":text}));
        self.event_with(
            "death",
            &actor,
            point,
            0.,
            false,
            json!({"enemy":kind,"level":level,"cause":ability}),
        );
        self.save();
        true
    }

    /// A heavy hit: `share` of the victim's maximum health, ignoring defence and dodge like a kill does.
    fn mech_heavy(&mut self, session: u64, share: f64, ability: &str, boss: usize) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let value = (p.character.max_hp() * share * self.raid_support(session).taken_multiplier())
            .round()
            .max(1.);
        if value >= p.character.hp {
            self.mech_kill(session, ability, boss);
            return;
        }
        if p.frozen
            || p.is_hidden()
            || p.character.hp <= 0.
            || p.character.spark_travel.is_some()
            || self.maps[p.character.zone].in_city(p.character.point())
        {
            return;
        }
        if bm::GOD_MODE_BLOCKS && (self.god_mode || p.god) {
            let text = bm::death_message(ability, true);
            let _ = p.peer.try_send(json!({"type":"system","text":text}));
            return;
        }
        let point = p.character.point();
        let actor = p.character.id.clone();
        let kind = self.slimes[boss].kind.clone();
        let level = self.slimes[boss].level;
        let p = self.players.get_mut(&session).unwrap();
        p.combat_left = 5.;
        p.character.mounted = false;
        p.character.hp -= value;
        p.last_hurt = self.time;
        p.hurt = 0.25;
        self.event_with(
            "hurt",
            &actor,
            point,
            value,
            false,
            json!({"enemy":kind,"level":level,"cause":ability}),
        );
    }

    /// Applies an effect to everyone `hit` says it reaches.
    fn land(
        &mut self,
        fight: &Fight,
        name: &str,
        effect: Effect,
        heavy: f64,
        hit: &dyn Fn(Point) -> bool,
    ) {
        let victims: Vec<u64> = self
            .mech_players(fight.zone)
            .into_iter()
            .filter(|(_, at)| hit(*at))
            .map(|(s, _)| s)
            .collect();
        for session in victims {
            match effect {
                Effect::Heavy => self.mech_heavy(session, heavy, name, fight.boss),
                _ => {
                    self.mech_kill(session, name, fight.boss);
                }
            }
        }
    }

    // -----------------------------------------------------------------------------------------------------------
    // Zones (and echoes)
    // -----------------------------------------------------------------------------------------------------------

    fn lit_discs(fight: &Fight) -> Vec<Shape> {
        fight
            .lit
            .iter()
            .flat_map(|g| {
                g.points
                    .iter()
                    .filter(|l| l.lit_left > 0.)
                    .map(|l| Shape::Circle {
                        x: l.at.x,
                        y: l.at.y,
                        r: g.r,
                        inner: 0.,
                    })
            })
            .collect()
    }

    fn resolve_shapes(&mut self, fight: &Fight, spec: &bm::ShapeSpec, cast: f64) -> Vec<Shape> {
        let players: Vec<Point> = self
            .mech_players(fight.zone)
            .into_iter()
            .map(|(_, p)| p)
            .collect();
        let lit = Self::lit_discs(fight);
        let mut rng = self.mech_rng();
        let ctx = bm::Ctx {
            map: &self.maps[fight.zone],
            arena: fight.arena,
            boss: self.slimes[fight.boss].point(),
            players: &players,
            lit: &lit,
            cast,
        };
        bm::resolve(spec, &ctx, &mut rng)
    }

    fn start_zone(&mut self, fight: &mut Fight, i: usize, m: &Mechanic, z: &bm::Zone, round: u32) {
        let areas = self.resolve_shapes(fight, &z.shape, z.cast);
        let id = self.fresh_id();
        fight.live.push(Live::Zone(ZoneLive {
            mech: i,
            id,
            areas,
            round,
            phase: ZPhase::Cast,
            left: z.cast,
            total: z.cast,
            echo_i: 0,
            reported: BTreeSet::new(),
        }));
        let at = self.slimes[fight.boss].point();
        self.mech_event(fight.zone, "cast", &m.name, at, z.cast);
        fight.banner = Some((m.name.clone(), z.cast));
    }

    fn tick_zone(&mut self, fight: &mut Fight, m: &Mechanic, zl: &mut ZoneLive) -> bool {
        let Block::Zone(z) = &m.block else {
            return false;
        };
        zl.left -= TICK;
        if zl.phase == ZPhase::Linger {
            for (session, at) in self.mech_players(fight.zone) {
                if bm::hurts(z.effect, &zl.areas, at) && zl.reported.insert(session) {
                    self.mech_kill(session, &m.name, fight.boss);
                }
            }
            return zl.left > 0. || Self::next_round(zl, z);
        }
        if zl.left > 0. {
            return true;
        }
        match zl.phase {
            ZPhase::Cast | ZPhase::Echo => {
                let areas = zl.areas.clone();
                let effect = z.effect;
                let hit: BTreeSet<u64> = self
                    .mech_players(fight.zone)
                    .into_iter()
                    .filter(|(_, p)| bm::hurts(effect, &areas, *p))
                    .map(|(session, _)| session)
                    .collect();
                self.land(fight, &m.name, effect, z.heavy, &|p| {
                    bm::hurts(effect, &areas, p)
                });
                let at = self.slimes[fight.boss].point();
                self.mech_event(fight.zone, "land", &m.name, at, 0.);
                if zl.phase == ZPhase::Echo {
                    zl.echo_i += 1;
                }
                if zl.echo_i < z.echo.len() {
                    zl.phase = ZPhase::Echo;
                    zl.left = z.echo[zl.echo_i];
                    zl.total = zl.left;
                    return true;
                }
                if z.linger > 0. {
                    zl.phase = ZPhase::Linger;
                    zl.left = z.linger;
                    zl.total = z.linger;
                    zl.reported = hit;
                    return true;
                }
                Self::next_round(zl, z)
            }
            ZPhase::Linger => unreachable!("lingering zones are handled above"),
            ZPhase::Gap => {
                if self.mech_players(fight.zone).is_empty() {
                    return false;
                }
                zl.areas = if z.alternate && zl.round % 2 == 1 {
                    zl.areas
                        .iter()
                        .map(|shape| match *shape {
                            Shape::Half { x, y, nx, ny } => Shape::Half {
                                x,
                                y,
                                nx: -nx,
                                ny: -ny,
                            },
                            other => other,
                        })
                        .collect()
                } else {
                    self.resolve_shapes(fight, &z.shape, z.cast)
                };
                zl.phase = ZPhase::Cast;
                zl.left = z.cast;
                zl.total = z.cast;
                zl.echo_i = 0;
                zl.reported.clear();
                zl.id = self.fresh_id();
                let at = self.slimes[fight.boss].point();
                self.mech_event(fight.zone, "cast", &m.name, at, z.cast);
                true
            }
        }
    }

    /// After a cast (and its echoes): the next of a `repeat`, or done.
    fn next_round(zl: &mut ZoneLive, z: &bm::Zone) -> bool {
        if zl.round + 1 < z.repeat {
            zl.round += 1;
            zl.phase = ZPhase::Gap;
            zl.left = z.repeat_gap.max(TICK);
            zl.total = zl.left;
            true
        } else {
            false
        }
    }

    // -----------------------------------------------------------------------------------------------------------
    // Marks
    // -----------------------------------------------------------------------------------------------------------

    fn start_mark(
        &mut self,
        fight: &mut Fight,
        i: usize,
        m: &Mechanic,
        k: &bm::Mark,
        wave: u32,
        players: &[(u64, Point)],
    ) {
        // Never everyone: at most `count`, at most MAX_MARKED, at most all but one, and at least one.
        let n = (k.count as usize)
            .min(bm::MAX_MARKED)
            .min(players.len().saturating_sub(1))
            .max(1)
            .min(players.len());
        let mut pool: Vec<u64> = players.iter().map(|(s, _)| *s).collect();
        let mut rng = self.mech_rng();
        let mut targets = vec![];
        while targets.len() < n && !pool.is_empty() {
            let at = ((rng() * pool.len() as f64) as usize).min(pool.len() - 1);
            targets.push(pool.swap_remove(at));
        }
        let id = self.fresh_id();
        fight.live.push(Live::Mark(MarkLive {
            mech: i,
            id,
            targets,
            wave,
            gap: false,
            left: k.cast,
            total: k.cast,
        }));
        let at = self.slimes[fight.boss].point();
        self.mech_event(fight.zone, "cast", &m.name, at, k.cast);
        fight.banner = Some((m.name.clone(), k.cast));
    }

    /// Where each marked player's ring or beam is right now: it follows them to the last moment.
    fn mark_shapes(&self, fight: &Fight, ml: &MarkLive, k: &bm::Mark) -> Vec<(u64, Vec<Shape>)> {
        let mut out = vec![];
        for session in &ml.targets {
            let Some(p) = self.players.get(session).filter(|p| p.character.hp > 0.) else {
                continue;
            };
            let at = p.character.point();
            let shapes = match k.effect {
                MarkEffect::Burst { r } => vec![Shape::Circle {
                    x: at.x,
                    y: at.y,
                    r,
                    inner: 0.,
                }],
                MarkEffect::Beam { bounces, width } => {
                    bm::beam_path(self.slimes[fight.boss].point(), at, fight.arena, bounces)
                        .windows(2)
                        .map(|w| Shape::Lane {
                            a: w[0],
                            b: w[1],
                            half: width / 2.,
                        })
                        .collect()
                }
            };
            out.push((*session, shapes));
        }
        out
    }

    fn tick_mark(&mut self, fight: &mut Fight, m: &Mechanic, ml: &mut MarkLive) -> bool {
        let Block::Mark(k) = &m.block else {
            return false;
        };
        ml.left -= TICK;
        if ml.left > 0. {
            return true;
        }
        if ml.gap {
            let players = self.mech_players(fight.zone);
            if players.is_empty() {
                return false;
            }
            let (wave, i) = (ml.wave, ml.mech);
            self.start_mark(fight, i, m, k, wave, &players);
            if let Some(Live::Mark(new)) = fight.live.pop() {
                *ml = new;
            }
            return true;
        }
        // The countdown ends: every mark resolves on everyone except its own bearer.
        for (bearer, shapes) in self.mark_shapes(fight, ml, k) {
            let victims: Vec<u64> = self
                .mech_players(fight.zone)
                .into_iter()
                .filter(|(s, at)| *s != bearer && shapes.iter().any(|sh| sh.contains(*at)))
                .map(|(s, _)| s)
                .collect();
            for &v in &victims {
                self.mech_kill(v, &m.name, fight.boss);
            }
            if k.linger > 0. {
                fight.live.push(Live::Puddle(PuddleLive {
                    mech: ml.mech,
                    id: self.fresh_id(),
                    bearer,
                    areas: shapes,
                    left: k.linger,
                    reported: victims.into_iter().collect(),
                }));
            }
        }
        let at = self.slimes[fight.boss].point();
        self.mech_event(fight.zone, "land", &m.name, at, 0.);
        if ml.wave + 1 < k.waves {
            ml.wave += 1;
            ml.gap = true;
            ml.left = k.wave_gap.max(TICK);
            ml.total = ml.left;
            return true;
        }
        false
    }

    fn tick_puddle(&mut self, fight: &Fight, m: &Mechanic, puddle: &mut PuddleLive) -> bool {
        puddle.left -= TICK;
        for (session, at) in self.mech_players(fight.zone) {
            if session != puddle.bearer
                && puddle.areas.iter().any(|shape| shape.contains(at))
                && puddle.reported.insert(session)
            {
                self.mech_kill(session, &m.name, fight.boss);
            }
        }
        puddle.left > 0.
    }

    // -----------------------------------------------------------------------------------------------------------
    // Sweeps: walls and spokes
    // -----------------------------------------------------------------------------------------------------------

    fn start_walls(&mut self, fight: &mut Fight, i: usize, m: &Mechanic, s: &bm::Sweep) {
        let SweepKind::Walls {
            warn,
            thickness,
            gap,
            walls,
            ..
        } = &s.kind
        else {
            return;
        };
        let a = fight.arena;
        let mut rng = self.mech_rng();
        let live: Vec<WallLive> = walls
            .iter()
            .map(|w| {
                let (lo, hi, pos) = match w.from {
                    Side::West => (a.y0, a.y1, a.x0 - thickness / 2.),
                    Side::East => (a.y0, a.y1, a.x1 + thickness / 2.),
                    Side::North => (a.x0, a.x1, a.y0 - thickness / 2.),
                    Side::South => (a.x0, a.x1, a.y1 + thickness / 2.),
                };
                let room = (hi - lo - gap).max(0.);
                let gap_at = match w.gap {
                    GapAt::Low => lo + gap / 2. + room * 0.15,
                    GapAt::High => hi - gap / 2. - room * 0.15,
                    GapAt::Middle => (lo + hi) / 2.,
                    GapAt::Random => lo + gap / 2. + rng() * room,
                };
                WallLive {
                    side: w.from,
                    pos,
                    gap_at,
                }
            })
            .collect();
        let id = self.fresh_id();
        // The warning shows each wall at the edge it will come from.
        fight.live.push(Live::Walls(WallsLive {
            mech: i,
            id,
            warn_left: *warn,
            warn_total: *warn,
            walls: live,
        }));
        let at = self.slimes[fight.boss].point();
        self.mech_event(fight.zone, "cast", &m.name, at, *warn);
        fight.banner = Some((m.name.clone(), *warn));
    }

    /// The edge a wall has passed once it has gone right across the arena.
    fn wall_is_past(a: Rect, thickness: f64, w: &WallLive) -> bool {
        match w.side {
            Side::West => w.pos > a.x1 + thickness / 2.,
            Side::East => w.pos < a.x0 - thickness / 2.,
            Side::North => w.pos > a.y1 + thickness / 2.,
            Side::South => w.pos < a.y0 - thickness / 2.,
        }
    }

    /// Whether the body of a player at `p` touches the solid part of the wall (the gap is clear of it).
    fn wall_hits(a: Rect, thickness: f64, gap: f64, w: &WallLive, p: Point) -> bool {
        let (across, along, lo, hi) = match w.side {
            Side::West | Side::East => (p.x, p.y, a.y0, a.y1),
            Side::North | Side::South => (p.y, p.x, a.x0, a.x1),
        };
        if (across - w.pos).abs() > thickness / 2. + BODY || along < lo - BODY || along > hi + BODY
        {
            return false;
        }
        (along - w.gap_at).abs() > gap / 2. - BODY
    }

    /// The solid parts of one wall as lanes, either side of its gap (what the client draws).
    fn wall_bands(a: Rect, thickness: f64, gap: f64, w: &WallLive) -> Vec<Shape> {
        let (horizontal, lo, hi) = match w.side {
            Side::West | Side::East => (false, a.y0, a.y1),
            Side::North | Side::South => (true, a.x0, a.x1),
        };
        let mut parts = vec![];
        for (s, e) in [(lo, w.gap_at - gap / 2.), (w.gap_at + gap / 2., hi)] {
            if e - s <= 0.01 {
                continue;
            }
            let (pa, pb) = if horizontal {
                (Point { x: s, y: w.pos }, Point { x: e, y: w.pos })
            } else {
                (Point { x: w.pos, y: s }, Point { x: w.pos, y: e })
            };
            parts.push(Shape::Lane {
                a: pa,
                b: pb,
                half: thickness / 2.,
            });
        }
        parts
    }

    fn tick_walls(&mut self, fight: &mut Fight, m: &Mechanic, wl: &mut WallsLive) -> bool {
        let Block::Sweep(s) = &m.block else {
            return false;
        };
        let SweepKind::Walls {
            speed,
            thickness,
            gap,
            ..
        } = &s.kind
        else {
            return false;
        };
        if wl.warn_left > 0. {
            wl.warn_left -= TICK;
            return true;
        }
        let a = fight.arena;
        for w in &mut wl.walls {
            let dir = match w.side {
                Side::West | Side::North => 1.,
                Side::East | Side::South => -1.,
            };
            w.pos += dir * speed * TICK;
        }
        let walls: Vec<(Side, f64, f64)> =
            wl.walls.iter().map(|w| (w.side, w.pos, w.gap_at)).collect();
        let (thickness, gap) = (*thickness, *gap);
        let hit = |p: Point| {
            walls.iter().any(|(side, pos, gap_at)| {
                Self::wall_hits(
                    a,
                    thickness,
                    gap,
                    &WallLive {
                        side: *side,
                        pos: *pos,
                        gap_at: *gap_at,
                    },
                    p,
                )
            })
        };
        self.land(fight, &m.name, Effect::Kill, 0., &hit);
        !wl.walls.iter().all(|w| Self::wall_is_past(a, thickness, w))
    }

    fn tick_spokes(&mut self, fight: &mut Fight, i: usize, m: &Mechanic, active: bool) {
        let Block::Sweep(sw) = &m.block else {
            return;
        };
        let SweepKind::Spokes {
            count,
            width,
            deg_per_s,
            reverse_every,
            reverse_warn,
            length,
        } = sw.kind.clone()
        else {
            return;
        };
        if !active {
            fight.spokes.retain(|s| s.mech != i);
            return;
        }
        let centre = fight.arena.centre();
        if !fight.spokes.iter().any(|s| s.mech == i) {
            let angle = self.random() * std::f64::consts::TAU;
            fight.spokes.push(SpokesLive {
                mech: i,
                angle,
                dir: 1.,
                reverse_in: reverse_every,
                warn_left: 0.,
                arm: SPOKES_ARM,
            });
            self.mech_event(fight.zone, "cast", &m.name, centre, 0.);
        }
        let mut flipped = false;
        let mut warning = false;
        let (angle, armed) = {
            let s = fight.spokes.iter_mut().find(|s| s.mech == i).unwrap();
            s.angle += s.dir * deg_per_s.to_radians() * TICK;
            s.arm = (s.arm - TICK).max(0.);
            if reverse_every > 0. {
                let before = s.reverse_in;
                s.reverse_in -= TICK;
                warning = before > reverse_warn && s.reverse_in <= reverse_warn;
                s.warn_left = if s.reverse_in <= reverse_warn {
                    s.reverse_in.max(0.)
                } else {
                    0.
                };
                if s.reverse_in <= 0. {
                    s.dir = -s.dir;
                    s.reverse_in = reverse_every;
                    s.warn_left = 0.;
                    flipped = true;
                }
            }
            (s.angle, s.arm <= 0.)
        };
        if warning {
            self.mech_event(fight.zone, "cast", &m.name, centre, reverse_warn);
        }
        if flipped {
            self.mech_event(fight.zone, "reverse", &m.name, centre, 0.);
        }
        let hit = |p: Point| {
            (0..count).any(|n| {
                let a = angle + n as f64 * std::f64::consts::TAU / count as f64;
                let tip = Point {
                    x: centre.x + a.cos() * length,
                    y: centre.y + a.sin() * length,
                };
                bm::segment_distance(p, centre, tip) <= width / 2. + BODY
            })
        };
        if armed {
            self.land(fight, &m.name, Effect::Kill, 0., &hit);
        }
    }

    // -----------------------------------------------------------------------------------------------------------
    // Running things
    // -----------------------------------------------------------------------------------------------------------

    /// Advances one running thing. `false`: it is finished and goes.
    fn tick_live(&mut self, fight: &mut Fight, def: &BossDef, live: &mut Live) -> bool {
        let m = &def.mechanics[live.mech()];
        match live {
            Live::Zone(zl) => self.tick_zone(fight, m, zl),
            Live::Mark(ml) => self.tick_mark(fight, m, ml),
            Live::Puddle(p) => self.tick_puddle(fight, m, p),
            Live::Walls(wl) => self.tick_walls(fight, m, wl),
            Live::Break(bl) => self.tick_break(fight, m, bl),
            Live::Gaze(gl) => self.tick_gaze(fight, m, gl),
            Live::Raid(r) => self.tick_raid_cast(fight, m, r),
        }
    }

    /// A burst phase (`Break::at`): once, when the boss's health, with its divided partner's, first falls to `at`, the
    /// party has `cast` seconds to deal `bar` of the boss's maximum health to either body.
    fn tick_burst(&mut self, fight: &mut Fight, i: usize, m: &Mechanic, b: &bm::Break) {
        let Some(at) = b.at else {
            return;
        };
        if fight.fired[i] != 0 {
            return;
        }
        let s = &self.slimes[fight.boss];
        let partner = fight.partner.map_or(0., |p| self.slimes[p].hp.max(0.));
        if s.max_hp <= 0. || (s.hp + partner) / s.max_hp > at {
            return;
        }
        fight.fired[i] = 1;
        let needed = b.bar * s.max_hp;
        let point = s.point();
        fight.live.push(Live::Break(BreakLive {
            mech: i,
            left: b.cast,
            total: b.cast,
            needed,
            dealt: 0.,
        }));
        self.mech_event(fight.zone, "cast", &m.name, point, b.cast);
        fight.banner = Some((m.name.clone(), b.cast));
    }

    fn tick_break(&mut self, fight: &mut Fight, m: &Mechanic, bl: &mut BreakLive) -> bool {
        let Block::Break(b) = &m.block else {
            return false;
        };
        let id = fight.boss;
        // The channel holds the boss where it is (a burst phase does not: the boss fights on).
        if !b.enrage && !b.overload {
            self.hold_still(id);
        }
        if bl.dealt >= bl.needed {
            #[cfg(test)]
            self.boss.spare.push(bl.left);
            fight.stun_left = b.stun;
            fight.vulnerable = b.vulnerable;
            let at = self.slimes[id].point();
            self.mech_event(fight.zone, "broken", &m.name, at, b.stun);
            return false;
        }
        bl.left -= TICK;
        if bl.left > 0. {
            return true;
        }
        if b.enrage {
            // Too slow: the enrage begins now and the boss's clock cannot fall back below its start.
            let kind = self.slimes[id].kind.clone();
            if let Some((start, _)) =
                crate::items::enrage_scaled(&kind, self.tuned(fight.zone, &kind).1)
            {
                fight.enrage_floor = start;
            }
            let at = self.slimes[id].point();
            self.mech_event(fight.zone, "land", &m.name, at, 0.);
            return false;
        }
        if b.overload {
            self.overload(fight, &m.name);
            return false;
        }
        // Too slow: the wail takes everyone in the fight.
        self.land(fight, &m.name, Effect::Kill, 0., &|_| true);
        let at = self.slimes[id].point();
        self.mech_event(fight.zone, "land", &m.name, at, 0.);
        false
    }

    // -----------------------------------------------------------------------------------------------------------
    // Gaze and cover
    // -----------------------------------------------------------------------------------------------------------

    /// Whether the eye at `from` sees `to`: no solid object and no standing cover in the way. The first piece of
    /// cover that blocks it is returned in `Err`.
    fn sight(&self, fight: &Fight, from: Point, to: Point) -> Result<(), Option<usize>> {
        if !self.maps[fight.zone].line_clear(from, to, 0.05) {
            return Err(None);
        }
        for (n, c) in fight.cover.iter().enumerate() {
            if !c.broken
                && bm::segment_distance(
                    Point {
                        x: c.cover.x,
                        y: c.cover.y,
                    },
                    from,
                    to,
                ) <= c.cover.r
            {
                return Err(Some(n));
            }
        }
        Ok(())
    }

    fn tick_gaze(&mut self, fight: &mut Fight, m: &Mechanic, gl: &mut GazeLive) -> bool {
        let Block::Gaze(g) = &m.block else {
            return false;
        };
        self.hold_still(fight.boss);
        if gl.left > 0. {
            gl.left = (gl.left - TICK).max(0.);
            if gl.left > 0. {
                return true;
            }
            if g.sweep <= 0. {
                // One look at the end of the warning.
                self.gaze_look(fight, gl, &m.name, None);
                self.finish_gaze(fight, gl);
                let at = self.slimes[fight.boss].point();
                self.mech_event(fight.zone, "land", &m.name, at, 0.);
                return false;
            }
            return true;
        }
        // The beam turns once round the room.
        let step = std::f64::consts::TAU * TICK / g.sweep;
        gl.angle += step;
        gl.turned += step;
        self.gaze_look(fight, gl, &m.name, Some(g.beam.to_radians()));
        if gl.turned >= std::f64::consts::TAU {
            self.finish_gaze(fight, gl);
            return false;
        }
        true
    }

    /// Each piece of cover that shielded someone during this gaze takes one hit; two break it.
    fn finish_gaze(&mut self, fight: &mut Fight, gl: &GazeLive) {
        for n in &gl.shielded {
            if let Some(c) = fight.cover.get_mut(*n) {
                c.hits += 1;
                if c.hits >= 2 {
                    c.broken = true;
                    c.broken_for = 0.;
                }
            }
        }
    }

    /// One look: everyone in line of sight (inside the beam, when it turns) is struck.
    fn gaze_look(&mut self, fight: &mut Fight, gl: &mut GazeLive, name: &str, beam: Option<f64>) {
        let mut victims = vec![];
        for (session, at) in self.mech_players(fight.zone) {
            if let Some(half) = beam {
                let mut turn = (at.y - gl.from.y).atan2(at.x - gl.from.x) - gl.angle;
                while turn > std::f64::consts::PI {
                    turn -= std::f64::consts::TAU;
                }
                while turn < -std::f64::consts::PI {
                    turn += std::f64::consts::TAU;
                }
                if turn.abs() > half {
                    continue;
                }
            }
            match self.sight(fight, gl.from, at) {
                Ok(()) => victims.push(session),
                Err(Some(n)) => {
                    gl.shielded.insert(n);
                }
                Err(None) => {}
            }
        }
        for v in victims {
            self.mech_kill(v, name, fight.boss);
        }
    }

    fn tick_cover(&mut self, fight: &mut Fight) {
        // Once the boss enrages the pillars crumble for good: a gaze nobody can hide from ends the fight.
        let boss = &self.slimes[fight.boss];
        let enraged = self.tuned_enrage_factor(boss.zone, &boss.kind, boss.fight) > 1.;
        if enraged && !fight.enraged {
            // With no cover left there is no safe spot, so the next gaze does not wait for its turn: it begins on the
            // next tick (a timer already at zero fires, a gaze already being cast runs on).
            fight.enraged = true;
            let def = &self.boss.table[&self.slimes[fight.boss].kind];
            for (i, m) in def.mechanics.iter().enumerate() {
                if matches!(m.block, Block::Gaze(_)) {
                    fight.timer[i] = 0.;
                }
            }
        }
        for c in &mut fight.cover {
            if enraged {
                c.broken = true;
                c.regrow = 0.;
                continue;
            }
            if c.broken && c.regrow > 0. {
                c.broken_for += TICK;
                if c.broken_for >= c.regrow {
                    c.broken = false;
                    c.hits = 0;
                    c.broken_for = 0.;
                }
            }
        }
    }

    // -----------------------------------------------------------------------------------------------------------
    // Shields, adds, blooms
    // -----------------------------------------------------------------------------------------------------------

    /// Wakes up to `count` sleeping monsters tagged `tag` in this dungeon copy and sends them at the party.
    fn wake_adds(
        &mut self,
        fight: &mut Fight,
        tag: &str,
        count: u32,
        scatter: bool,
        still: bool,
    ) -> Vec<usize> {
        let zone = fight.zone;
        // Sleepers first; when a long fight has used them all, a helper this fight woke and that has since died
        // (a seed, a cocoon) is put to work again, so a cycle that repeats every 30 s never runs out of bodies.
        let held: &[usize] = fight.shield.as_ref().map_or(&[], |sh| &sh.adds);
        let mut slots: Vec<usize> = (0..self.spawns.len())
            .filter(|i| {
                self.spawns[*i].zone == zone
                    && self.spawns[*i].ambush.as_deref() == Some(tag)
                    && self.slimes[*i].dead
                    && (self.slimes[*i].state == "waiting"
                        || (fight.woken.contains(i) && !held.contains(i)))
            })
            .collect();
        slots.sort_by_key(|i| self.slimes[*i].state != "waiting");
        slots.truncate(count as usize);
        let players = self.mech_players(zone);
        let mut woken = vec![];
        for slot in slots {
            let spawn = self.spawns[slot].clone();
            let mut enemy = Slime::with_level(slot, &spawn, Slime::default_level(&spawn.kind));
            let mut start = enemy.point();
            if scatter {
                let mut rng = self.mech_rng();
                let ctx = bm::Ctx {
                    map: &self.maps[zone],
                    arena: fight.arena,
                    boss: self.slimes[fight.boss].point(),
                    players: &[],
                    lit: &[],
                    cast: 5.,
                };
                start = bm::random_spot(&ctx, &mut rng);
            }
            let bodies = self.actor_bodies(zone, None, Some(slot));
            if let Some(point) =
                free_actor_position(&self.maps[zone], start, enemy.r, &bodies, true)
            {
                (enemy.x, enemy.y, enemy.hx, enemy.hy, enemy.goal) =
                    (point.x, point.y, point.x, point.y, point);
            }
            enemy.target = players
                .iter()
                .min_by(|a, b| {
                    a.1.distance(enemy.point())
                        .total_cmp(&b.1.distance(enemy.point()))
                })
                .map(|(s, _)| *s);
            enemy.hunt = true;
            enemy.state = "chase".into();
            let at = enemy.point();
            self.slimes[slot] = enemy;
            if !fight.woken.contains(&slot) {
                fight.woken.push(slot);
            }
            if still {
                fight.still.insert(slot);
            }
            woken.push(slot);
            self.mech_event(zone, "add", tag, at, 0.);
        }
        woken
    }

    fn raise_shield(
        &mut self,
        fight: &mut Fight,
        name: &str,
        step: &bm::ShieldStep,
        heal_per_s: f64,
    ) {
        let adds = self.wake_adds(fight, &step.tag, step.count, false, step.still);
        if adds.is_empty() {
            return;
        }
        fight.shield = Some(ShieldLive {
            tag: step.tag.clone(),
            adds,
            heal_per_s,
            name: name.into(),
        });
        let at = self.slimes[fight.boss].point();
        self.mech_event(fight.zone, "shield", name, at, 1.);
        fight.banner = Some((name.into(), 4.));
    }

    fn tick_shield(&mut self, fight: &mut Fight) {
        let Some(sh) = &fight.shield else {
            return;
        };
        if sh.adds.iter().all(|s| self.slimes[*s].dead) {
            let name = sh.name.clone();
            fight.shield = None;
            let at = self.slimes[fight.boss].point();
            self.mech_event(fight.zone, "shield", &name, at, 0.);
            return;
        }
        if sh.heal_per_s > 0. {
            let s = &mut self.slimes[fight.boss];
            s.hp = (s.hp + s.max_hp * sh.heal_per_s * TICK).min(s.max_hp);
        }
    }

    fn tick_blooms(&mut self, fight: &mut Fight) {
        let mut due = vec![];
        for b in &mut fight.blooms {
            b.left -= TICK;
        }
        fight.blooms.retain(|b| {
            if self.slimes[b.slot].dead {
                return false;
            }
            if b.left <= 0. {
                due.push((b.slot, b.heal, b.then.clone()));
                return false;
            }
            true
        });
        for (slot, heal, then) in due {
            let at = self.slimes[slot].point();
            self.slimes[slot] = self.dormant_enemy(slot);
            fight.still.remove(&slot);
            let s = &mut self.slimes[fight.boss];
            s.hp = (s.hp + s.max_hp * heal).min(s.max_hp);
            self.mech_event(fight.zone, "bloom", "", at, heal);
            let Some(tag) = then else {
                continue;
            };
            for w in self.wake_adds(fight, &tag, 1, false, false) {
                let bodies = self.actor_bodies(fight.zone, None, Some(w));
                let spot = free_actor_position(
                    &self.maps[fight.zone],
                    at,
                    self.slimes[w].r,
                    &bodies,
                    true,
                )
                .unwrap_or(at);
                let s = &mut self.slimes[w];
                (s.x, s.y, s.hx, s.hy, s.goal) = (spot.x, spot.y, spot.x, spot.y, spot);
            }
        }
    }

    // -----------------------------------------------------------------------------------------------------------
    // Holds
    // -----------------------------------------------------------------------------------------------------------

    fn tick_hold(&mut self, fight: &mut Fight, i: usize) {
        let players = self.mech_players(fight.zone);
        let Some(g) = fight.lit.iter_mut().find(|g| g.mech == i) else {
            return;
        };
        for l in &mut g.points {
            let inside = players.iter().any(|(_, p)| p.distance(l.at) <= g.r);
            if l.lit_left > 0. {
                l.lit_left -= TICK;
            } else if inside {
                l.progress += TICK;
                if l.progress >= g.hold_for {
                    l.progress = 0.;
                    l.lit_left = g.lit_for;
                }
            } else {
                l.progress = (l.progress - TICK).max(0.);
            }
        }
        if g.snuff_every > 0. {
            g.snuff_in -= TICK;
            if g.snuff_in <= 0. {
                g.snuff_in = g.snuff_every;
                if let Some(l) = g.points.iter_mut().find(|l| l.lit_left > 0.) {
                    l.lit_left = 0.;
                }
            }
        }
    }

    // -----------------------------------------------------------------------------------------------------------
    // Stasis: orbs and cocoons
    // -----------------------------------------------------------------------------------------------------------

    fn launch_orbs(
        &mut self,
        fight: &mut Fight,
        name: &str,
        s: &bm::Stasis,
        players: &[(u64, Point)],
    ) {
        let mut rng = self.mech_rng();
        let mut pool: Vec<u64> = players.iter().map(|(p, _)| *p).collect();
        for _ in 0..s.orbs {
            if pool.is_empty() {
                pool = players.iter().map(|(p, _)| *p).collect();
            }
            let at = ((rng() * pool.len() as f64) as usize).min(pool.len() - 1);
            fight.orbs.push(Orb {
                at: self.slimes[fight.boss].point(),
                target: pool.swap_remove(at),
                life: s.life,
                speed: s.speed,
                tag: s.tag.clone(),
                hold: s.hold,
            });
        }
        let _ = name;
    }

    fn tick_orbs_and_frozen(&mut self, fight: &mut Fight) {
        let mut touched = vec![];
        for orb in &mut fight.orbs {
            orb.life -= TICK;
            let Some(p) = self
                .players
                .get(&orb.target)
                .filter(|p| p.character.hp > 0. && !p.frozen)
            else {
                orb.life = 0.;
                continue;
            };
            let to = p.character.point();
            let d = orb.at.distance(to);
            if d <= ORB_REACH {
                touched.push((orb.target, orb.tag.clone(), orb.hold));
                orb.life = 0.;
                continue;
            }
            let step = (orb.speed * TICK).min(d);
            orb.at.x += (to.x - orb.at.x) / d * step;
            orb.at.y += (to.y - orb.at.y) / d * step;
        }
        fight.orbs.retain(|o| o.life > 0.);
        let name = self.stasis_name(fight.boss);
        for (session, tag, hold) in touched {
            // One sleeping cocoon of the tag becomes the amber round this player.
            // A sleeper first; once they are used up, a cocoon of this fight that was broken is put to work again.
            let fits = |i: &usize| {
                self.spawns[*i].zone == fight.zone
                    && self.spawns[*i].ambush.as_deref() == Some(tag.as_str())
                    && self.slimes[*i].dead
            };
            let Some(slot) = (0..self.spawns.len())
                .find(|i| fits(i) && self.slimes[*i].state == "waiting")
                .or_else(|| {
                    (0..self.spawns.len()).find(|i| {
                        fits(i)
                            && fight.woken.contains(i)
                            && !fight.frozen.values().any(|f| f.cocoon == *i)
                    })
                })
            else {
                continue;
            };
            let at = self.players[&session].character.point();
            let spawn = self.spawns[slot].clone();
            let mut cocoon = Slime::with_level(slot, &spawn, Slime::default_level(&spawn.kind));
            (cocoon.x, cocoon.y, cocoon.hx, cocoon.hy, cocoon.goal) = (at.x, at.y, at.x, at.y, at);
            cocoon.state = "idle".into();
            self.slimes[slot] = cocoon;
            if !fight.woken.contains(&slot) {
                fight.woken.push(slot);
            }
            fight.still.insert(slot);
            let p = self.players.get_mut(&session).unwrap();
            p.frozen = true;
            p.stop();
            p.attack = 0.;
            fight.frozen.insert(
                session,
                Frozen {
                    cocoon: slot,
                    left: hold,
                    name: name.clone(),
                },
            );
            self.mech_event(fight.zone, "frozen", &name, at, hold);
        }
        // A cocoon is broken (the player walks free) or the amber closes.
        let mut freed = vec![];
        let mut lost = vec![];
        for (session, f) in &mut fight.frozen {
            f.left -= TICK;
            if self.slimes[f.cocoon].dead {
                freed.push(*session);
            } else if f.left <= 0. {
                lost.push((*session, f.cocoon, f.name.clone()));
            }
        }
        for session in freed {
            fight.frozen.remove(&session);
            if let Some(p) = self.players.get_mut(&session) {
                p.frozen = false;
            }
        }
        for (session, cocoon, name) in lost {
            fight.frozen.remove(&session);
            fight.still.remove(&cocoon);
            self.slimes[cocoon] = self.dormant_enemy(cocoon);
            if let Some(p) = self.players.get_mut(&session) {
                p.frozen = false;
            }
            self.mech_kill(session, &name, fight.boss);
        }
    }

    fn stasis_name(&self, boss: usize) -> String {
        self.mechanic_name(boss, |b| matches!(b, Block::Stasis(_)))
    }

    /// The name of the boss's first mechanic of a block kind.
    fn mechanic_name(&self, boss: usize, which: impl Fn(&Block) -> bool) -> String {
        self.boss
            .table
            .get(&self.slimes[boss].kind)
            .and_then(|d| {
                d.mechanics
                    .iter()
                    .find(|m| which(&m.block))
                    .map(|m| m.name.clone())
            })
            .unwrap_or_default()
    }

    // -----------------------------------------------------------------------------------------------------------
    // Split
    // -----------------------------------------------------------------------------------------------------------

    fn divide_boss(&mut self, fight: &mut Fight, name: &str, s: &bm::Split) {
        let id = fight.boss;
        let Some(partner) = self
            .wake_adds(fight, &s.tag, 1, false, false)
            .first()
            .copied()
        else {
            return;
        };
        let half = (self.slimes[id].hp / 2.).ceil().max(2.);
        let max = self.slimes[id].max_hp;
        self.slimes[id].hp = half;
        let near = self.slimes[id].point();
        let bodies = self.actor_bodies(fight.zone, None, Some(partner));
        let side = free_actor_position(
            &self.maps[fight.zone],
            Point {
                x: near.x + 3.,
                y: near.y,
            },
            self.slimes[partner].r,
            &bodies,
            true,
        )
        .unwrap_or(near);
        let p = &mut self.slimes[partner];
        p.max_hp = max;
        p.hp = half;
        (p.x, p.y, p.hx, p.hy, p.goal) = (side.x, side.y, side.x, side.y, side);
        fight.partner = Some(partner);
        fight.bridge_wait = BRIDGE_WARNING;
        self.mech_event(fight.zone, "split", name, near, 0.);
        fight.banner = Some((name.into(), 4.));
    }

    fn tick_split(&mut self, fight: &mut Fight, def: &BossDef) {
        let Some(partner) = fight.partner else {
            return;
        };
        let Some((name, split)) = def.mechanics.iter().find_map(|m| match &m.block {
            Block::Split(s) => Some((m.name.clone(), s.clone())),
            _ => None,
        }) else {
            return;
        };
        let id = fight.boss;
        // A downed body lies still; its time runs out and it rises.
        for body in fight.downed.keys().copied().collect::<Vec<_>>() {
            self.hold_still(body);
            let left = fight.downed.get_mut(&body).unwrap();
            *left -= TICK;
            if *left > 0. {
                continue;
            }
            fight.downed.remove(&body);
            // The bridge of light is back with the body, so it is announced again like the first time (a party that
            // stood on the line while one body lay still was killed the instant it rose).
            fight.bridge_wait = BRIDGE_WARNING;
            let other = if body == id { partner } else { id };
            let s = &mut self.slimes[body];
            s.hp = (s.max_hp / 2.).max(2.);
            if !self.slimes[other].dead {
                self.slimes[other].damage *= 1. + split.survivor_bonus;
            }
            let at = self.slimes[body].point();
            self.mech_event(fight.zone, "rise", &name, at, split.survivor_bonus);
        }
        // The bridge of light between the two living bodies: shown at once, lethal after its warning.
        fight.bridge_wait = (fight.bridge_wait - TICK).max(0.);
        if split.bridge > 0.
            && fight.bridge_wait <= 0.
            && !self.slimes[id].dead
            && !self.slimes[partner].dead
            && fight.downed.is_empty()
        {
            let (a, b) = (self.slimes[id].point(), self.slimes[partner].point());
            let on_it = |p: Point| bm::segment_distance(p, a, b) <= split.bridge + BODY;
            if split.bridge_hit > 0. {
                fight.bridge_tick -= TICK;
                if fight.bridge_tick <= 0. {
                    fight.bridge_tick = BRIDGE_TICK;
                    self.land(fight, &name, Effect::Heavy, split.bridge_hit, &on_it);
                }
            } else {
                self.land(fight, &name, Effect::Kill, 0., &on_it);
            }
        }
    }

    // -----------------------------------------------------------------------------------------------------------
    // The danger query (for hired fighters and the harness)
    // -----------------------------------------------------------------------------------------------------------

    /// What would hurt `session`, standing at `at`, in the running fights of `zone`, and the soonest it lands: the
    /// ability's name and the seconds left. A mark never counts against its own bearer. `None`: safe where they stand.
    /// A break bar counts (it asks for damage, not a move); `bot_threat` is the query for where to stand.
    #[allow(dead_code)] // the whole-danger view: read by the tests that pin what each block reports
    pub(super) fn boss_danger(
        &self,
        zone: usize,
        session: u64,
        at: Point,
    ) -> Option<(String, f64)> {
        self.danger_list(zone, session, at, 0.)
            .into_iter()
            .map(|(name, left, _)| (name, left))
            .min_by(|a, b| a.1.total_cmp(&b.1))
    }

    /// Every ability that would hurt `session` standing at `at`: `(name, seconds until it lands, depends on where
    /// they stand)`. `look` seconds of lookahead are added for hazards that move (spokes).
    fn danger_list(
        &self,
        zone: usize,
        session: u64,
        at: Point,
        look: f64,
    ) -> Vec<(String, f64, bool)> {
        let mut found: Vec<(String, f64, bool)> = vec![];
        let mut note = |name: &str, left: f64, positional: bool| {
            found.push((name.to_string(), left.max(0.), positional));
        };
        for fight in self.boss.fights.values().filter(|f| f.zone == zone) {
            let Some(def) = self.boss.table.get(&self.slimes[fight.boss].kind) else {
                continue;
            };
            for live in &fight.live {
                let m = &def.mechanics[live.mech()];
                match (live, &m.block) {
                    (Live::Raid(r), _) => {
                        if let Some(left) = self.raid_cast_danger(fight, m, r, session, at) {
                            note(&m.name, left, true);
                        }
                    }
                    (Live::Zone(zl), Block::Zone(z))
                        if matches!(zl.phase, ZPhase::Cast | ZPhase::Echo | ZPhase::Linger) =>
                    {
                        if bm::hurts(z.effect, &zl.areas, at) {
                            note(
                                &m.name,
                                if zl.phase == ZPhase::Linger {
                                    0.
                                } else {
                                    zl.left
                                },
                                true,
                            );
                        }
                    }
                    (Live::Mark(ml), Block::Mark(k)) if !ml.gap => {
                        for (bearer, shapes) in self.mark_shapes(fight, ml, k) {
                            if bearer != session && shapes.iter().any(|sh| sh.contains(at)) {
                                note(&m.name, ml.left, true);
                            }
                        }
                    }
                    (Live::Puddle(p), Block::Mark(_)) => {
                        if session != p.bearer && p.areas.iter().any(|shape| shape.contains(at)) {
                            note(&m.name, 0., true);
                        }
                    }
                    (Live::Walls(wl), Block::Sweep(s)) => {
                        let SweepKind::Walls {
                            speed,
                            thickness,
                            gap,
                            ..
                        } = &s.kind
                        else {
                            continue;
                        };
                        for w in &wl.walls {
                            // How long until the wall's band reaches this point, if the point is not in the gap.
                            let (across, along, dir) = match w.side {
                                Side::West => (at.x, at.y, 1.),
                                Side::East => (at.x, at.y, -1.),
                                Side::North => (at.y, at.x, 1.),
                                Side::South => (at.y, at.x, -1.),
                            };
                            if (along - w.gap_at).abs() <= gap / 2. - BODY {
                                continue;
                            }
                            let ahead = (across - w.pos) * dir;
                            if ahead >= -(thickness / 2. + BODY) {
                                note(
                                    &m.name,
                                    wl.warn_left.max(0.) + (ahead - thickness / 2.).max(0.) / speed,
                                    true,
                                );
                            }
                        }
                    }
                    (Live::Break(bl), _) => {
                        note(&m.name, bl.left, false);
                    }
                    (Live::Gaze(gl), Block::Gaze(_))
                        if gl.left > 0. && self.sight(fight, gl.from, at).is_ok() =>
                    {
                        note(&m.name, gl.left, true);
                    }
                    // The beam is turning: it reaches this point when its centre is within `beam` of it, unless it
                    // has already passed (the rest of the turn is too short to come round again) or cover is in the way.
                    (Live::Gaze(gl), Block::Gaze(g))
                        if gl.left <= 0.
                            && g.sweep > 0.
                            && self.sight(fight, gl.from, at).is_ok() =>
                    {
                        let tau = std::f64::consts::TAU;
                        let half = g.beam.to_radians();
                        let mut ahead = (at.y - gl.from.y).atan2(at.x - gl.from.x) - gl.angle;
                        while ahead > std::f64::consts::PI {
                            ahead -= tau;
                        }
                        while ahead < -std::f64::consts::PI {
                            ahead += tau;
                        }
                        let travel = if ahead.abs() <= half {
                            0.
                        } else if ahead > 0. {
                            ahead - half
                        } else {
                            ahead + tau - half
                        };
                        if travel <= tau - gl.turned {
                            note(&m.name, travel / (tau / g.sweep), true);
                        }
                    }
                    _ => {}
                }
            }
            for sp in &fight.spokes {
                let Block::Sweep(s) = &def.mechanics[sp.mech].block else {
                    continue;
                };
                let SweepKind::Spokes {
                    count,
                    width,
                    length,
                    deg_per_s,
                    ..
                } = s.kind
                else {
                    continue;
                };
                let centre = fight.arena.centre();
                // The spokes turn: look ahead along their turn so a bot leaves before a spoke arrives.
                let mut t = 0.;
                while t <= look + 1e-9 {
                    let turned = sp.angle + sp.dir * deg_per_s.to_radians() * t;
                    let hit = t >= sp.arm
                        && (0..count).any(|n| {
                            let a = turned + n as f64 * std::f64::consts::TAU / count as f64;
                            let tip = Point {
                                x: centre.x + a.cos() * length,
                                y: centre.y + a.sin() * length,
                            };
                            bm::segment_distance(at, centre, tip) <= width / 2. + BODY
                        });
                    if hit {
                        note(&def.mechanics[sp.mech].name, t, true);
                        break;
                    }
                    t += 0.25;
                }
            }
            // A seeking orb that is about to touch this player, and the lethal bridge between a divided boss's bodies.
            for orb in fight.orbs.iter().filter(|o| o.target == session) {
                let d = orb.at.distance(at);
                if d <= ORB_REACH + 3. {
                    note(&self.stasis_name(fight.boss), d / orb.speed.max(0.1), true);
                }
            }
            if let (Some(partner), Some(split)) = (fight.partner, self.split_def(fight.boss))
                && split.bridge > 0.
                && !self.slimes[fight.boss].dead
                && !self.slimes[partner].dead
                && fight.downed.is_empty()
            {
                let (a, b) = (
                    self.slimes[fight.boss].point(),
                    self.slimes[partner].point(),
                );
                if bm::segment_distance(at, a, b) <= split.bridge + BODY + 1.2 {
                    note("Twin Suns", fight.bridge_wait, true);
                }
            }
        }
        found
    }

    /// Seconds until something that depends on where `session` stands would hurt them at `at` (a break bar, which asks
    /// for damage and not a move, is left out); `None`: safe there. The fighters that are not at a keyboard use this
    /// to choose where to stand (`boss_play`).
    pub(super) fn bot_threat(
        &self,
        zone: usize,
        session: u64,
        at: Point,
        look: f64,
    ) -> Option<f64> {
        self.danger_list(zone, session, at, look)
            .into_iter()
            .filter(|(_, _, positional)| *positional)
            .map(|(_, left, _)| left)
            .min_by(f64::total_cmp)
    }

    // -----------------------------------------------------------------------------------------------------------
    // What the client is told
    // -----------------------------------------------------------------------------------------------------------

    /// `bossMech` for one zone: every running fight in it, in the form `docs/boss-mechanics.md` rule 1 asks the
    /// client to draw. Empty when nothing is running.
    pub(super) fn boss_mech_view(&self, zone: usize) -> Vec<Value> {
        let mut out = vec![];
        for (id, fight) in self.boss.fights.iter().filter(|(_, f)| f.zone == zone) {
            let Some(def) = self.boss.table.get(&self.slimes[*id].kind) else {
                continue;
            };
            let mut teles: Vec<Value> = vec![];
            let mut cast = Value::Null;
            let mut brk = Value::Null;
            let mut marked = vec![];
            for live in &fight.live {
                let m = &def.mechanics[live.mech()];
                match (live, &m.block) {
                    (Live::Zone(zl), Block::Zone(z)) => {
                        if zl.phase == ZPhase::Gap {
                            continue;
                        }
                        let kind = if z.effect == Effect::KillOutside {
                            bm::Telegraph::Safe
                        } else {
                            bm::Telegraph::Danger
                        };
                        teles.push(tele_json(
                            zl.id,
                            &m.name,
                            kind,
                            &zl.areas,
                            zl.left,
                            zl.total,
                            zl.phase == ZPhase::Echo,
                        ));
                        if zl.phase == ZPhase::Cast {
                            cast = json!({"name":m.name,"left":zl.left,"total":zl.total});
                        }
                    }
                    (Live::Mark(ml), Block::Mark(k)) => {
                        if ml.gap {
                            continue;
                        }
                        let kind = if matches!(k.effect, MarkEffect::Beam { .. }) {
                            bm::Telegraph::Path
                        } else {
                            bm::Telegraph::Danger
                        };
                        for (bearer, shapes) in self.mark_shapes(fight, ml, k) {
                            if let Some(p) = self.players.get(&bearer) {
                                marked.push(p.character.id.clone());
                            }
                            teles.push(tele_json(
                                ml.id, &m.name, kind, &shapes, ml.left, ml.total, false,
                            ));
                        }
                        cast = json!({"name":m.name,"left":ml.left,"total":ml.total});
                    }
                    (Live::Puddle(p), Block::Mark(_)) => {
                        teles.push(tele_json(
                            p.id,
                            &m.name,
                            bm::Telegraph::Danger,
                            &p.areas,
                            0.,
                            0.,
                            false,
                        ));
                    }
                    (Live::Walls(wl), Block::Sweep(s)) => {
                        let SweepKind::Walls { thickness, gap, .. } = &s.kind else {
                            continue;
                        };
                        let warning = wl.warn_left > 0.;
                        let kind = if warning {
                            bm::Telegraph::Path
                        } else {
                            bm::Telegraph::Danger
                        };
                        for w in &wl.walls {
                            let bands = Self::wall_bands(fight.arena, *thickness, *gap, w);
                            teles.push(tele_json(
                                wl.id,
                                &m.name,
                                kind,
                                &bands,
                                wl.warn_left.max(0.),
                                wl.warn_total,
                                false,
                            ));
                            let (g0, g1) = (w.gap_at - gap / 2., w.gap_at + gap / 2.);
                            let (a, b) = match w.side {
                                Side::West | Side::East => {
                                    (Point { x: w.pos, y: g0 }, Point { x: w.pos, y: g1 })
                                }
                                Side::North | Side::South => {
                                    (Point { x: g0, y: w.pos }, Point { x: g1, y: w.pos })
                                }
                            };
                            let gap_shape = Shape::Lane {
                                a,
                                b,
                                half: thickness / 2.,
                            };
                            teles.push(tele_json(
                                wl.id,
                                &m.name,
                                bm::Telegraph::Gap,
                                &[gap_shape],
                                0.,
                                0.,
                                false,
                            ));
                        }
                        if warning {
                            cast = json!({"name":m.name,"left":wl.warn_left,"total":wl.warn_total});
                        }
                    }
                    (Live::Break(bl), _) => {
                        brk = json!({"name":m.name,"left":bl.left,"total":bl.total,"dealt":bl.dealt,"needed":bl.needed});
                        cast = json!({"name":m.name,"left":bl.left,"total":bl.total});
                    }
                    (Live::Gaze(gl), Block::Gaze(g)) => {
                        let shape = if gl.left <= 0. && g.sweep > 0. {
                            Shape::Cone {
                                x: gl.from.x,
                                y: gl.from.y,
                                dir: gl.angle,
                                half: g.beam.to_radians(),
                                length: fight.arena.diagonal(),
                            }
                        } else {
                            Shape::Circle {
                                x: gl.from.x,
                                y: gl.from.y,
                                r: 0.5,
                                inner: 0.,
                            }
                        };
                        let mut t = tele_json(
                            gl.id,
                            &m.name,
                            bm::Telegraph::Danger,
                            &[shape],
                            gl.left,
                            gl.total,
                            false,
                        );
                        t["gaze"] = json!(true);
                        teles.push(t);
                        if gl.left > 0. {
                            cast = json!({"name":m.name,"left":gl.left,"total":gl.total});
                        }
                    }
                    _ => {}
                }
            }
            for g in &fight.lit {
                for l in &g.points {
                    let shape = Shape::Circle {
                        x: l.at.x,
                        y: l.at.y,
                        r: g.r,
                        inner: 0.,
                    };
                    let mut t = tele_json(
                        0,
                        &def.mechanics[g.mech].name,
                        bm::Telegraph::Safe,
                        &[shape],
                        0.,
                        0.,
                        false,
                    );
                    t["lit"] = json!(l.lit_left > 0.);
                    t["litLeft"] = json!(l.lit_left.max(0.));
                    t["progress"] = json!((l.progress / g.hold_for).min(1.));
                    teles.push(t);
                }
            }
            for sp in &fight.spokes {
                let Block::Sweep(s) = &def.mechanics[sp.mech].block else {
                    continue;
                };
                let SweepKind::Spokes {
                    count,
                    width,
                    length,
                    ..
                } = s.kind
                else {
                    continue;
                };
                let centre = fight.arena.centre();
                let shapes: Vec<Shape> = (0..count)
                    .map(|n| {
                        let a = sp.angle + n as f64 * std::f64::consts::TAU / count as f64;
                        Shape::Lane {
                            a: centre,
                            b: Point {
                                x: centre.x + a.cos() * length,
                                y: centre.y + a.sin() * length,
                            },
                            half: width / 2.,
                        }
                    })
                    .collect();
                let mut t = tele_json(
                    0,
                    &def.mechanics[sp.mech].name,
                    if sp.arm > 0. {
                        bm::Telegraph::Path
                    } else {
                        bm::Telegraph::Danger
                    },
                    &shapes,
                    sp.arm,
                    if sp.arm > 0. { SPOKES_ARM } else { 0. },
                    false,
                );
                t["reversing"] = json!(sp.warn_left > 0.);
                t["reverseLeft"] = json!(sp.warn_left);
                teles.push(t);
            }
            // The bridge of light between a divided boss's bodies: a dashed path while it warns, then red.
            if let (Some(partner), Some(split)) = (fight.partner, self.split_def(fight.boss))
                && split.bridge > 0.
                && !self.slimes[fight.boss].dead
                && !self.slimes[partner].dead
                && fight.downed.is_empty()
            {
                let lane = Shape::Lane {
                    a: self.slimes[fight.boss].point(),
                    b: self.slimes[partner].point(),
                    half: split.bridge,
                };
                let warning = fight.bridge_wait > 0.;
                let kind = if warning {
                    bm::Telegraph::Path
                } else {
                    bm::Telegraph::Danger
                };
                let name = self.mechanic_name(fight.boss, |b| matches!(b, Block::Split(_)));
                teles.push(tele_json(
                    0,
                    &name,
                    kind,
                    &[lane],
                    fight.bridge_wait,
                    BRIDGE_WARNING,
                    false,
                ));
            }
            for c in &fight.cover {
                let shape = Shape::Circle {
                    x: c.cover.x,
                    y: c.cover.y,
                    r: c.cover.r,
                    inner: 0.,
                };
                teles.push(json!({"id":0,"name":"cover","tele":"cover","hits":c.hits,"standing":!c.broken,"shapes":[shape.view()],"left":0,"total":0}));
            }
            for orb in &fight.orbs {
                let shape = Shape::Circle {
                    x: orb.at.x,
                    y: orb.at.y,
                    r: ORB_REACH,
                    inner: 0.,
                };
                let mut t = tele_json(
                    0,
                    "orb",
                    bm::Telegraph::Danger,
                    &[shape],
                    orb.life,
                    0.,
                    false,
                );
                t["orb"] = json!(true);
                teles.push(t);
            }
            let mut stat = Value::Null;
            if let Some(st) = &fight.stat {
                let name = def
                    .mechanics
                    .iter()
                    .find(|m| matches!(m.block, Block::Static(_)))
                    .map_or("", |m| m.name.as_str());
                for r in &st.rods {
                    let shape = Shape::Circle {
                        x: r.at.x,
                        y: r.at.y,
                        r: st.rod_r,
                        inner: 0.,
                    };
                    let mut t = tele_json(0, name, bm::Telegraph::Safe, &[shape], 0., 0., false);
                    t["lit"] = json!(r.dark_left <= 0.);
                    t["litLeft"] = json!(r.dark_left);
                    t["rod"] = json!(true);
                    teles.push(t);
                }
                for (at, r, left) in &st.bursts {
                    let shape = Shape::Circle {
                        x: at.x,
                        y: at.y,
                        r: *r,
                        inner: 0.,
                    };
                    teles.push(tele_json(
                        0,
                        name,
                        bm::Telegraph::Danger,
                        &[shape],
                        *left,
                        0.8,
                        false,
                    ));
                }
                let by_id = |m: &BTreeMap<u64, u32>| -> BTreeMap<String, u32> {
                    m.iter()
                        .filter_map(|(s, n)| {
                            self.players.get(s).map(|p| (p.character.id.clone(), *n))
                        })
                        .collect()
                };
                stat = json!({
                    "name": name,
                    "limit": st.limit,
                    "warnAt": st.warn_at,
                    "radius": def.mechanics.iter().find_map(|m| match &m.block {
                        Block::Static(t) => Some(t.r),
                        _ => None,
                    }),
                    "charges": by_id(&st.charges),
                    "grounded": st.grounded.iter().filter_map(|(s, left)| {
                        self.players.get(s).map(|p| (p.character.id.clone(), *left))
                    }).collect::<BTreeMap<String, f64>>(),
                });
            }
            self.raid_cast_view(fight, def, &mut teles, &mut cast);
            let ids = |sessions: Vec<&u64>| -> Vec<String> {
                sessions
                    .into_iter()
                    .filter_map(|s| self.players.get(s).map(|p| p.character.id.clone()))
                    .collect()
            };
            out.push(json!({
                "boss": id,
                "clock": fight.clock,
                "cast": cast,
                "break": brk,
                "tele": teles,
                "marked": marked,
                "frozen": ids(fight.frozen.keys().collect()),
                "shield": fight.shield.as_ref().map(|s| json!({
                    "name": s.name,
                    "tag": s.tag,
                    "adds": s.adds.len(),
                    "alive": s.adds.iter().filter(|a| !self.slimes[**a].dead).count(),
                    "healPerSecond": s.heal_per_s,
                })),
                "stunned": fight.stun_left.max(0.),
                "static": stat,
                "partner": fight.partner,
                "downed": fight.downed.keys().collect::<Vec<_>>(),
                "banner": fight.banner.as_ref().map(|(t, _)| t),
            }));
        }
        out
    }
}

fn tele_json(
    id: u64,
    name: &str,
    kind: bm::Telegraph,
    shapes: &[Shape],
    left: f64,
    total: f64,
    echo: bool,
) -> Value {
    json!({
        "id": id,
        "name": name,
        "tele": kind.word(),
        "color": kind.color(),
        "dashed": kind.dashed(),
        "echo": echo,
        "shapes": shapes.iter().map(Shape::view).collect::<Vec<_>>(),
        "left": left,
        "total": total,
    })
}

#[path = "boss_play.rs"]
mod play;

#[cfg(test)]
#[path = "boss_mechanics_tests.rs"]
mod tests;

#[path = "raid_boss_mechanics.rs"]
mod raid_bosses;

#[cfg(test)]
#[path = "raid_boss_tests.rs"]
mod raid_tests;
