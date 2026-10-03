//! Party XP and party level. Inside a party the XP of a kill is shared: every real player who is alive, in the zone
//! and near the body gets a cut of the enemy's XP set by the **party level**, which runs from 1 to 5:
//!
//! | party level | each member's XP (percent of what a lone hero would get) |
//! |---|---|
//! | 1 | 40 |
//! | 2 | 55 |
//! | 3 | 70 |
//! | 4 | 85 |
//! | 5 | 100 |
//!
//! A fresh party is worth less than playing alone and a seasoned one is worth exactly as much, so a party never
//! beats a solo hero on XP per kill, but fights faster and safer. The level is earned by killing together: each kill
//! shared by two or more members adds fellowship points to every member who took part (`kill_points`: an ordinary
//! enemy 1, an elite 5, a boss 15). Enemies far below the party's strongest member earn nothing, so the level cannot be
//! ground out on trivial monsters. The points live on the character (`Character::party_points`) and the party's
//! level comes from their average over the members who are online, so a restart does not reset it, a party that is
//! rebuilt keeps it, and a newcomer pulls a veteran party's level down only by their share of the average.
//!
//! Hired mercenaries take no XP and do not count as members: a hirer fighting alongside their hired fighters is
//! still alone and keeps the whole XP. Nothing changes for a hero with nobody in range.
use super::*;

/// Highest party level.
pub const PARTY_LEVEL_MAX: u32 = 5;
/// Fellowship points (average over the members) at which the party reaches level 2, 3, 4 and 5.
pub const PARTY_LEVEL_AT: [u32; 4] = [40, 120, 260, 450];
/// Percent of an enemy's XP that each member gets at party level 1..=5.
pub const PARTY_XP_PERCENT: [u32; 5] = [40, 55, 70, 85, 100];
/// An enemy more than this many levels below the strongest member earns the party no fellowship points.
pub const TRIVIAL_GAP: u32 = 6;

/// The party level that `points` (average per member) reach.
pub fn party_level(points: u32) -> u32 {
    1 + PARTY_LEVEL_AT.iter().filter(|at| points >= **at).count() as u32
}
/// Percent of the XP each member gets at this party level.
pub fn xp_percent(level: u32) -> u32 {
    PARTY_XP_PERCENT[level.clamp(1, PARTY_LEVEL_MAX) as usize - 1]
}
/// One member's share of `xp`: at least 1 when there is anything to share.
pub fn shared_xp(xp: u32, level: u32) -> u32 {
    if xp == 0 {
        return 0;
    }
    ((xp as u64 * xp_percent(level) as u64 + 50) / 100).max(1) as u32
}
/// Fellowship points a kill is worth.
pub fn kill_points(kind: &str) -> u32 {
    if is_boss(kind) {
        15
    } else if is_elite(kind) {
        5
    } else {
        1
    }
}

impl World {
    /// The real players of `id`'s party (`id` included, alive or not) who are in the zone near the body, sorted by id.
    /// Mercenaries are never in it.
    fn xp_group(&self, id: &str, zone: usize, point: Point) -> Vec<String> {
        let mut group: Vec<String> = self
            .party_mates(id)
            .into_iter()
            .filter(|m| {
                self.players.values().any(|p| {
                    p.merc.is_none()
                        && p.character.id == *m
                        && p.character.zone == zone
                        && (m == id || p.character.hp > 0.)
                        && p.character.point().distance(point) <= rolls::SHARE_RANGE
                })
            })
            .collect();
        group.sort();
        group
    }
    /// Average fellowship points over the online real players of `id`'s party.
    pub(super) fn party_points_of(&self, id: &str) -> u32 {
        let points: Vec<u32> = self
            .party_mates(id)
            .iter()
            .filter_map(|m| {
                self.players
                    .values()
                    .find(|p| p.merc.is_none() && p.character.id == *m)
            })
            .map(|p| p.character.party_points)
            .collect();
        if points.is_empty() {
            return 0;
        }
        (points.iter().map(|p| *p as u64).sum::<u64>() / points.len() as u64) as u32
    }
    /// What the party panel shows: level, percent, and the points between this level and the next.
    pub(super) fn party_xp_value(&self, id: &str) -> Value {
        let points = self.party_points_of(id);
        let level = party_level(points);
        let from = if level == 1 {
            0
        } else {
            PARTY_LEVEL_AT[level as usize - 2]
        };
        let next = PARTY_LEVEL_AT.get(level as usize - 1).copied();
        json!({"level":level,"maxLevel":PARTY_LEVEL_MAX,"xpPercent":xp_percent(level),"points":points,
            "from":from,"next":next})
    }
    /// Pays the XP of a kill whose rewards belong to `credit` and returns what `credit` got and the levels it gained.
    /// A hero with nobody to share with gets all of it.
    pub(super) fn share_xp(
        &mut self,
        credit: &str,
        zone: usize,
        point: Point,
        xp: u32,
        enemy_level: u32,
        kind: &str,
    ) -> (u32, u32) {
        let group = self.xp_group(credit, zone, point);
        if group.len() < 2 || !group.iter().any(|g| g == credit) {
            return (xp, self.grant(credit, xp));
        }
        let before = party_level(self.party_points_of(credit));
        let strongest = group
            .iter()
            .filter_map(|g| self.online(g))
            .map(|p| p.character.level)
            .max()
            .unwrap_or(1);
        if enemy_level + TRIVIAL_GAP >= strongest {
            let points = kill_points(kind);
            for p in self.players.values_mut() {
                if group.contains(&p.character.id) {
                    p.character.party_points = p.character.party_points.saturating_add(points);
                }
            }
        }
        let level = party_level(self.party_points_of(credit));
        let share = shared_xp(xp, level);
        let mut mine = (share, 0);
        for member in &group {
            let levels = self.grant(member, share);
            if member == credit {
                mine.1 = levels;
                continue;
            }
            let at = self.online(member).map(|p| p.character.point());
            if let Some(at) = at {
                self.event_with(
                    "partyXp",
                    member,
                    at,
                    share as f64,
                    false,
                    json!({"enemy":kind,"level":enemy_level,"xp":share}),
                );
                if levels > 0 {
                    self.level_up_event(member, at, levels);
                }
            }
        }
        if level > before {
            let text = format!(
                "Your party reached party level {level}! Each member now earns {}% of an enemy's XP{}.",
                xp_percent(level),
                if level == PARTY_LEVEL_MAX {
                    ", as much as fighting alone"
                } else {
                    ""
                }
            );
            for member in &group {
                self.tell(member, text.clone(), true);
            }
        }
        if let Some(i) = self.party_index(credit) {
            self.push_party(i);
        }
        mine
    }
    /// Gives `xp` to the online character `id`; returns the levels gained.
    fn grant(&mut self, id: &str, xp: u32) -> u32 {
        self.players
            .values_mut()
            .find(|p| p.merc.is_none() && p.character.id == id)
            .map_or(0, |p| p.character.grant_xp(xp))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn world() -> World {
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
    }
    /// Joins `names` at level 20 and puts them in one party, standing together.
    fn party(w: &mut World, names: &[&str]) -> Vec<(u64, String, mpsc::Receiver<Value>)> {
        let mut out = vec![];
        for (n, name) in names.iter().enumerate() {
            let (tx, rx) = mpsc::channel(512);
            let look = Look {
                name: (*name).into(),
                ..Look::default()
            };
            let session = n as u64 + 1;
            let welcome = w.join(session, None, Some(look), tx).unwrap();
            let id: String = welcome["id"].as_str().unwrap().into();
            w.players.get_mut(&session).unwrap().character.level = 20;
            out.push((session, id, rx));
        }
        for (session, id, _) in out.iter().skip(1) {
            let leader = out[0].1.clone();
            w.social(
                out[0].0,
                SocialCommand::PartyInvite {
                    id: Some(id.clone()),
                    name: None,
                },
            );
            w.social(*session, SocialCommand::PartyAccept { id: leader });
        }
        out
    }
    fn xp_of(w: &World, session: u64) -> u32 {
        w.players[&session].character.xp
    }
    fn set_points(w: &mut World, points: u32) {
        for p in w.players.values_mut() {
            p.character.party_points = points;
        }
    }
    fn spot(w: &World) -> Point {
        w.players[&1].character.point()
    }

    #[test]
    fn the_level_curve_rises_to_exactly_a_lone_heros_xp() {
        assert_eq!(party_level(0), 1);
        assert_eq!(party_level(39), 1);
        assert_eq!(party_level(40), 2);
        assert_eq!(party_level(449), 4);
        assert_eq!(party_level(450), 5);
        assert_eq!(party_level(u32::MAX), PARTY_LEVEL_MAX);
        let pct: Vec<u32> = (1..=5).map(xp_percent).collect();
        assert!(
            pct.windows(2).all(|w| w[0] < w[1]),
            "every level pays more: {pct:?}"
        );
        assert_eq!(pct[4], 100);
        assert_eq!(shared_xp(1000, 5), 1000);
        assert_eq!(shared_xp(1000, 1), 400);
        assert_eq!(shared_xp(1, 1), 1, "a share is never rounded away");
        assert_eq!(shared_xp(0, 3), 0);
        assert!(
            kill_points("slime") < kill_points("big")
                && kill_points("big") < kill_points("hollowking")
        );
    }

    #[test]
    fn a_party_shares_the_xp_by_party_level() {
        for level in 1..=5 {
            let mut w = world();
            let who = party(&mut w, &["Ann", "Bob", "Cat"]);
            set_points(
                &mut w,
                if level == 1 {
                    0
                } else {
                    PARTY_LEVEL_AT[level as usize - 2]
                },
            );
            let at = spot(&w);
            let (paid, _) = w.share_xp(&who[0].1, 0, at, 1000, 20, "slime");
            let want = shared_xp(1000, level);
            assert_eq!(paid, want);
            for (session, _, _) in &who {
                assert_eq!(xp_of(&w, *session), want, "party level {level}");
            }
        }
    }

    #[test]
    fn alone_or_with_mates_out_of_reach_the_whole_xp_is_kept() {
        let mut w = world();
        let who = party(&mut w, &["Ann"]);
        let at = spot(&w);
        assert_eq!(w.share_xp(&who[0].1, 0, at, 1000, 20, "slime").0, 1000);
        assert_eq!(xp_of(&w, 1), 1000);
        assert_eq!(
            w.players[&1].character.party_points, 0,
            "nobody to be a party with"
        );
        // Mates who are far away or dead take no part, and the killer is paid in full.
        let mut w = world();
        let who = party(&mut w, &["Ann", "Bob", "Cat"]);
        w.players.get_mut(&2).unwrap().character.x += rolls::SHARE_RANGE + 5.;
        w.players.get_mut(&3).unwrap().character.hp = 0.;
        let at = spot(&w);
        assert_eq!(w.share_xp(&who[0].1, 0, at, 1000, 20, "slime").0, 1000);
        assert_eq!((xp_of(&w, 2), xp_of(&w, 3)), (0, 0));
    }

    #[test]
    fn a_kill_together_earns_every_member_fellowship_points_and_the_level_up_is_announced() {
        let mut w = world();
        let mut who = party(&mut w, &["Ann", "Bob"]);
        let at = spot(&w);
        for _ in 0..39 {
            w.share_xp(&who[0].1, 0, at, 10, 20, "slime");
        }
        assert_eq!(w.players[&1].character.party_points, 39);
        assert_eq!(w.party_xp_value(&who[0].1)["level"], 1);
        for (_, _, rx) in who.iter_mut() {
            while rx.try_recv().is_ok() {}
        }
        w.share_xp(&who[0].1, 0, at, 10, 20, "slime");
        assert_eq!(w.party_xp_value(&who[1].1)["level"], 2);
        let said: Vec<String> = std::iter::from_fn(|| who[1].2.try_recv().ok())
            .filter(|v| v["type"] == "notice")
            .map(|v| v["text"].as_str().unwrap().to_owned())
            .collect();
        assert!(
            said.iter()
                .any(|t| t.contains("party level 2") && t.contains("55%")),
            "{said:?}"
        );
    }

    #[test]
    fn trivial_enemies_earn_no_points_and_bosses_earn_many() {
        let mut w = world();
        let who = party(&mut w, &["Ann", "Bob"]);
        let at = spot(&w);
        w.share_xp(&who[0].1, 0, at, 10, 20 - TRIVIAL_GAP - 1, "slime");
        assert_eq!(w.players[&1].character.party_points, 0);
        assert!(xp_of(&w, 2) > 0, "the XP is still shared");
        w.share_xp(&who[0].1, 0, at, 10, 20, "hollowking");
        assert_eq!(w.players[&2].character.party_points, 15);
    }

    #[test]
    fn the_party_level_is_the_average_of_the_members() {
        let mut w = world();
        let who = party(&mut w, &["Ann", "Bob", "Cat"]);
        for (session, points) in [(1, 450), (2, 450), (3, 0)] {
            w.players.get_mut(&session).unwrap().character.party_points = points;
        }
        // 300 on average: level 4, not 5 and not 1.
        assert_eq!(w.party_xp_value(&who[0].1)["level"], 4);
        let v = w.party_xp_value(&who[0].1);
        assert_eq!(
            (v["from"].as_u64(), v["next"].as_u64()),
            (Some(260), Some(450))
        );
    }

    #[test]
    fn a_member_who_levels_from_a_shared_kill_is_told() {
        let mut w = world();
        let mut who = party(&mut w, &["Ann", "Bob"]);
        set_points(&mut w, 450);
        let need = w.players[&2].character.xp_need();
        let at = spot(&w);
        w.share_xp(&who[0].1, 0, at, need, 20, "slime");
        assert_eq!(w.players[&2].character.level, 21);
        let kinds: Vec<String> = std::iter::from_fn(|| who[1].2.try_recv().ok())
            .filter(|v| v["type"] == "event")
            .map(|v| v["kind"].as_str().unwrap().to_owned())
            .collect();
        assert!(
            kinds.contains(&"partyXp".to_owned()) && kinds.contains(&"levelup".to_owned()),
            "{kinds:?}"
        );
    }

    #[test]
    fn the_party_value_carries_the_level() {
        let mut w = world();
        let who = party(&mut w, &["Ann", "Bob"]);
        set_points(&mut w, 120);
        w.share_xp(&who[0].1, 0, spot(&w), 10, 20, "slime");
        let i = w.party_index(&who[0].1).unwrap();
        let v = w.party_value(i);
        assert_eq!(v["xp"]["level"], 3);
        assert_eq!(v["xp"]["xpPercent"], 70);
    }
}
