//! Party loot. Inside a party every drop is shared instead of belonging to the killer:
//!
//! * gold is split evenly between the party members who are in the zone and near the body (the remainder goes
//!   round robin);
//! * gray gear and materials go round robin, one recipient per drop;
//! * green, blue, purple and orange gear is rolled for: need (only for a piece your class can wear at your level),
//!   greed or pass, 1-100 with need beating greed, thirty seconds to answer, nobody who stays silent can win.
//!
//! Only real players count: a mercenary has no vote and takes no share. A hero with nobody to share with (alone, or
//! alone with hired fighters) keeps the old rule, so everything drops for them. Boss gear (`boss_loot`) stays
//! personal on purpose: every hero who fought gets a piece fitted to their class.
use super::*;

/// Seconds a roll waits for the votes before the silent members count as passing.
pub const ROLL_SECONDS: f64 = 30.;
/// Party members farther than this from the body (or in another zone) take no part in a drop.
pub const SHARE_RANGE: f64 = 60.;

pub(super) struct Roll {
    id: u64,
    item: String,
    zone: usize,
    at: Point,
    /// The killer, who takes the piece when everybody passes.
    owner: String,
    expires: f64,
    votes: BTreeMap<String, Option<RollChoice>>,
}

/// Green and better is rolled for; gray gear and materials are not.
pub fn rollable(rarity: &str) -> bool {
    matches!(rarity, "uncommon" | "rare" | "epic" | "legendary")
}
/// Whether this character may need the piece: it is gear, their class can wear it and their level is high enough.
pub fn can_need(c: &Character, i: &Item) -> bool {
    is_gear(i) && i.class.is_none_or(|k| k == c.look.class) && i.required_level <= c.level
}

impl World {
    /// The real players who share a drop of `owner` at `point` in `zone`, sorted by character id. Just `owner` when
    /// there is nobody to share with.
    fn loot_group(&self, owner: &str, zone: usize, point: Point) -> Vec<String> {
        let mut group: Vec<String> = self
            .party_mates(owner)
            .into_iter()
            .filter(|id| {
                self.players.values().any(|p| {
                    p.merc.is_none()
                        && p.character.id == *id
                        && p.character.zone == zone
                        && p.character.point().distance(point) <= SHARE_RANGE
                })
            })
            .collect();
        group.sort();
        if group.len() < 2 || !group.iter().any(|id| id == owner) {
            return vec![owner.to_owned()];
        }
        group
    }
    /// The next member in line. The turn is kept per group (keyed by its first member), so two parties never
    /// disturb each other's order.
    fn next_in_line(&mut self, group: &[String]) -> String {
        let turn = self.loot_turns.entry(group[0].clone()).or_insert(0);
        let who = group[*turn % group.len()].clone();
        *turn += 1;
        who
    }
    /// Gold from a kill: split evenly inside a party, the odd coins going to whoever is next in line.
    pub(super) fn gold_drop(&mut self, owner: &str, zone: usize, point: Point, value: u32) {
        let group = self.loot_group(owner, zone, point);
        let n = group.len() as u32;
        let mut shares = vec![value / n; group.len()];
        for _ in 0..value % n {
            let who = self.next_in_line(&group);
            let at = group.iter().position(|g| *g == who).unwrap();
            shares[at] += 1;
        }
        for (who, share) in group.iter().zip(shares) {
            if share == 0 {
                continue;
            }
            let id = self.entity();
            self.drops.push(Drop {
                id,
                owner: who.clone(),
                zone,
                x: point.x,
                y: point.y,
                z: 8.,
                value: share,
                item: None,
                quantity: 0,
                t: 0.,
                col: "#ffe066",
            });
        }
    }
    /// An item from a kill. Gray gear and materials go to the next member in line; green and better is rolled for.
    pub(super) fn loot_drop(&mut self, owner: &str, zone: usize, point: Point, item_id: &str) {
        let group = self.loot_group(owner, zone, point);
        if group.len() < 2 {
            return self.item_drop(owner, zone, point, item_id, 1);
        }
        let rarity = item(item_id).map_or("common", |i| i.rarity.as_str());
        if !rollable(rarity) {
            let who = self.next_in_line(&group);
            return self.item_drop(&who, zone, point, item_id, 1);
        }
        let id = self.entity();
        let can_need: Vec<bool> = group
            .iter()
            .map(|g| {
                self.players
                    .values()
                    .find(|p| p.character.id == *g)
                    .zip(item(item_id))
                    .is_some_and(|(p, i)| can_need(&p.character, i))
            })
            .collect();
        for (who, need) in group.iter().zip(can_need) {
            if let Some(p) = self.players.values().find(|p| p.character.id == *who) {
                let _ = p
                    .peer
                    .try_send(json!({"type":"roll","op":"start","id":id,"item":item_id,
                    "seconds":ROLL_SECONDS,"need":need}));
            }
        }
        self.rolls.push(Roll {
            id,
            item: item_id.into(),
            zone,
            at: point,
            owner: owner.into(),
            expires: self.time + ROLL_SECONDS,
            votes: group.into_iter().map(|g| (g, None)).collect(),
        });
    }
    pub(super) fn roll_vote(&mut self, session: u64, id: u64, choice: RollChoice) {
        let Some(p) = self.players.get(&session) else {
            return;
        };
        let me = p.character.id.clone();
        let refuse = |text: &str| {
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
        };
        let Some(roll) = self.rolls.iter().find(|r| r.id == id) else {
            return refuse("That roll is already over.");
        };
        match roll.votes.get(&me) {
            None => return refuse("You are not rolling for that piece."),
            Some(Some(_)) => return refuse("You already answered that roll."),
            Some(None) => {}
        }
        if choice == RollChoice::Need
            && !item(&roll.item).is_some_and(|i| can_need(&p.character, i))
        {
            return refuse(
                "You cannot use that piece: Need is for gear your class can wear at your level. Choose Greed or Pass.",
            );
        }
        let _ = p
            .peer
            .try_send(json!({"type":"roll","op":"voted","id":id,"choice":choice}));
        if let Some(roll) = self.rolls.iter_mut().find(|r| r.id == id) {
            roll.votes.insert(me, Some(choice));
        }
    }
    /// Closes every roll that is fully answered or out of time.
    pub(super) fn update_rolls(&mut self) {
        if self.rolls.is_empty() {
            return;
        }
        let online: Vec<String> = self
            .players
            .values()
            .filter(|p| p.merc.is_none())
            .map(|p| p.character.id.clone())
            .collect();
        let now = self.time;
        let (done, open): (Vec<Roll>, Vec<Roll>) =
            std::mem::take(&mut self.rolls).into_iter().partition(|r| {
                r.expires <= now
                    || r.votes
                        .iter()
                        .all(|(who, vote)| vote.is_some() || !online.contains(who))
            });
        self.rolls = open;
        for roll in done {
            self.finish_roll(roll);
        }
    }
    fn finish_roll(&mut self, roll: Roll) {
        let name_of = |w: &World, id: &str| {
            w.players
                .values()
                .find(|p| p.character.id == id)
                .map(|p| p.character.look.name.clone())
        };
        // (id, name, choice, value) for everyone still here; someone who left cannot win.
        let mut rolled = vec![];
        for (who, vote) in &roll.votes {
            let Some(name) = name_of(self, who) else {
                continue;
            };
            let choice = vote.unwrap_or(RollChoice::Pass);
            let value = if choice == RollChoice::Pass {
                0
            } else {
                1 + (self.random() * 100.) as u32
            };
            rolled.push((who.clone(), name, choice, value));
        }
        let rank = |c: RollChoice| match c {
            RollChoice::Need => 2,
            RollChoice::Greed => 1,
            RollChoice::Pass => 0,
        };
        let mut winner: Option<&(String, String, RollChoice, u32)> = None;
        for entry in rolled.iter().filter(|e| e.2 != RollChoice::Pass) {
            if winner.is_none_or(|w| (rank(entry.2), entry.3) > (rank(w.2), w.3)) {
                winner = Some(entry);
            }
        }
        let item_name = item(&roll.item).map_or("a piece of gear", |i| i.name.as_str());
        let words = |c: RollChoice| match c {
            RollChoice::Need => "Need",
            RollChoice::Greed => "Greed",
            RollChoice::Pass => "Pass",
        };
        let list = rolled
            .iter()
            .map(|(_, name, c, v)| {
                if *c == RollChoice::Pass {
                    format!("{name} (Pass)")
                } else {
                    format!("{name} ({} {v})", words(*c))
                }
            })
            .collect::<Vec<_>>()
            .join(", ");
        let (recipient, text) = match winner {
            Some((id, name, ..)) => (
                id.clone(),
                format!("Roll for {item_name}: {list}. {name} wins it."),
            ),
            None => {
                let keeper = rolled.iter().find(|e| e.0 == roll.owner).or(rolled.first());
                match keeper {
                    Some((id, name, ..)) => (
                        id.clone(),
                        format!("Everyone passed on {item_name}: {list}. {name} gets it."),
                    ),
                    None => return,
                }
            }
        };
        for (who, ..) in &rolled {
            if let Some(p) = self.players.values().find(|p| p.character.id == *who) {
                let _ = p
                    .peer
                    .try_send(json!({"type":"roll","op":"end","id":roll.id}));
                let _ = p.peer.try_send(json!({"type":"system","text":text}));
            }
        }
        self.item_drop(&recipient, roll.zone, roll.at, &roll.item, 1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn world() -> World {
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
    }
    /// Joins `names` as level-20 players (warrior, mage, priest in turn), all in one party, standing together.
    fn party(w: &mut World, names: &[&str]) -> Vec<(u64, String, mpsc::Receiver<Value>)> {
        let classes = [Class::Warrior, Class::Mage, Class::Priest];
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
            let c = &mut w.players.get_mut(&session).unwrap().character;
            c.level = 20;
            c.look.class = classes[n % 3];
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
    fn heard(rx: &mut mpsc::Receiver<Value>) -> Vec<Value> {
        let mut v = vec![];
        while let Ok(m) = rx.try_recv() {
            v.push(m);
        }
        v
    }
    fn spot(w: &World) -> Point {
        w.players[&1].character.point()
    }
    fn owned_by(w: &World, id: &str) -> Vec<Drop> {
        w.drops.iter().filter(|d| d.owner == id).cloned().collect()
    }
    /// A green piece only the given class can use, at level 20 or below.
    fn green_for(class: Class) -> &'static Item {
        ITEMS
            .iter()
            .find(|i| {
                i.rarity == "uncommon"
                    && is_gear(i)
                    && !i.starter
                    && i.source.is_none()
                    && i.class == Some(class)
                    && i.required_level <= 20
            })
            .expect("a green piece for the class")
    }
    fn vote(w: &mut World, who: &(u64, String, mpsc::Receiver<Value>), id: u64, c: RollChoice) {
        w.roll_vote(who.0, id, c);
    }
    fn roll_id(heard: &[Value]) -> u64 {
        heard
            .iter()
            .find(|v| v["type"] == "roll" && v["op"] == "start")
            .expect("a roll start")["id"]
            .as_u64()
            .unwrap()
    }

    #[test]
    fn gold_is_split_between_party_members_with_the_odd_coins_shared_out() {
        let mut w = world();
        let who = party(&mut w, &["Ann", "Bob", "Cat"]);
        let at = spot(&w);
        w.gold_drop(&who[0].1, 0, at, 10);
        let shares: Vec<u32> = who
            .iter()
            .map(|(_, id, _)| owned_by(&w, id).iter().map(|d| d.value).sum())
            .collect();
        assert_eq!(
            shares.iter().sum::<u32>(),
            10,
            "no coin is lost: {shares:?}"
        );
        assert!(shares.iter().all(|s| *s == 3 || *s == 4), "{shares:?}");
        // Solo, the killer keeps all of it.
        let mut solo = world();
        let who = party(&mut solo, &["Dan"]);
        let at = spot(&solo);
        solo.gold_drop(&who[0].1, 0, at, 10);
        assert_eq!(owned_by(&solo, &who[0].1)[0].value, 10);
        assert_eq!(solo.drops.len(), 1);
    }

    #[test]
    fn far_or_absent_members_take_no_share() {
        let mut w = world();
        let who = party(&mut w, &["Ann", "Bob"]);
        // Bob wanders off beyond the sharing range.
        w.players.get_mut(&2).unwrap().character.x += SHARE_RANGE + 5.;
        let at = spot(&w);
        w.gold_drop(&who[0].1, 0, at, 9);
        assert_eq!(w.drops.len(), 1);
        assert_eq!(owned_by(&w, &who[0].1)[0].value, 9);
    }

    #[test]
    fn gray_drops_go_round_robin() {
        let mut w = world();
        let who = party(&mut w, &["Ann", "Bob", "Cat"]);
        let at = spot(&w);
        for _ in 0..6 {
            w.loot_drop(&who[0].1, 0, at, "slime_gel");
        }
        for (_, id, _) in &who {
            assert_eq!(owned_by(&w, id).len(), 2, "two each, not all to the killer");
        }
        assert!(w.rolls.is_empty(), "gray items are never rolled for");
    }

    #[test]
    fn green_gear_is_rolled_for_and_need_beats_greed() {
        let mut w = world();
        let mut who = party(&mut w, &["Ann", "Bob", "Cat"]);
        let at = spot(&w);
        let piece = green_for(Class::Mage);
        w.loot_drop(&who[0].1, 0, at, &piece.id);
        assert!(
            w.drops.is_empty(),
            "nothing lies on the ground until the roll ends"
        );
        let started: Vec<Vec<Value>> = who.iter_mut().map(|(_, _, rx)| heard(rx)).collect();
        let id = roll_id(&started[0]);
        // Only the mage can need a mage piece.
        let need: Vec<bool> = started
            .iter()
            .map(|h| h.iter().find(|v| v["op"] == "start").unwrap()["need"] == true)
            .collect();
        assert_eq!(need, vec![false, true, false]);
        // A warrior's Need is refused and leaves the vote open.
        vote(&mut w, &who[0], id, RollChoice::Need);
        assert!(heard(&mut who[0].2).iter().any(|v| v["type"] == "error"));
        vote(&mut w, &who[0], id, RollChoice::Greed);
        vote(&mut w, &who[2], id, RollChoice::Greed);
        w.update_rolls();
        assert_eq!(w.rolls.len(), 1, "waiting for the mage");
        // The mage's Need beats both greeds whatever the dice say.
        vote(&mut w, &who[1], id, RollChoice::Need);
        w.update_rolls();
        assert!(w.rolls.is_empty());
        assert_eq!(owned_by(&w, &who[1].1).len(), 1);
        assert_eq!(
            owned_by(&w, &who[1].1)[0].item.as_deref(),
            Some(piece.id.as_str())
        );
        assert!(owned_by(&w, &who[0].1).is_empty() && owned_by(&w, &who[2].1).is_empty());
        let text = heard(&mut who[2].2)
            .into_iter()
            .find(|v| v["type"] == "system")
            .expect("a result line")["text"]
            .as_str()
            .unwrap()
            .to_owned();
        assert!(
            text.contains("Bob wins it") && text.contains("Bob (Need"),
            "{text}"
        );
        // Voting again is refused: the roll is over.
        vote(&mut w, &who[2], id, RollChoice::Greed);
        assert!(heard(&mut who[2].2).iter().any(|v| v["type"] == "error"));
    }

    #[test]
    fn silence_counts_as_a_pass_and_an_all_pass_goes_to_the_killer() {
        let mut w = world();
        let mut who = party(&mut w, &["Ann", "Bob", "Cat"]);
        let at = spot(&w);
        let piece = green_for(Class::Warrior);
        // Bob is the killer; nobody answers, so after thirty seconds the piece falls to him.
        w.loot_drop(&who[1].1, 0, at, &piece.id);
        let id = roll_id(&heard(&mut who[0].2));
        w.time += ROLL_SECONDS - 1.;
        w.update_rolls();
        assert_eq!(w.rolls.len(), 1);
        w.time += 2.;
        w.update_rolls();
        assert!(w.rolls.is_empty());
        assert_eq!(owned_by(&w, &who[1].1).len(), 1);
        assert!(
            heard(&mut who[2].2)
                .iter()
                .any(|v| v["op"] == "end" && v["id"] == id)
        );
        // Anyone who said Greed beats a silent table.
        w.drops.clear();
        w.loot_drop(&who[1].1, 0, at, &piece.id);
        let id = roll_id(&heard(&mut who[0].2));
        vote(&mut w, &who[0], id, RollChoice::Pass);
        vote(&mut w, &who[2], id, RollChoice::Greed);
        w.time += ROLL_SECONDS + 1.;
        w.update_rolls();
        assert_eq!(owned_by(&w, &who[2].1).len(), 1);
    }

    #[test]
    fn nobody_rolls_alone() {
        let mut w = world();
        let who = party(&mut w, &["Ann"]);
        let at = spot(&w);
        let piece = green_for(Class::Warrior);
        w.loot_drop(&who[0].1, 0, at, &piece.id);
        assert!(w.rolls.is_empty());
        assert_eq!(owned_by(&w, &who[0].1).len(), 1);
    }

    #[test]
    fn mercenaries_neither_roll_nor_share() {
        let mut w = world();
        let mut who = party(&mut w, &["Ann", "Bob"]);
        // Hire a fighter into Ann's party through the real path.
        let mut merc = Character::mercenary(Class::Priest, 20, "Merc Priest");
        merc.zone = 0;
        merc.x = w.players[&1].character.x;
        merc.y = w.players[&1].character.y;
        w.party_add_mercenary(&who[0].1, &merc).unwrap();
        let (tx, _rx) = mpsc::channel(1);
        let mut hired = Player::new(merc, tx);
        hired.merc = Some(who[0].1.clone());
        w.players.insert(7_000_000, hired);
        let at = spot(&w);
        w.gold_drop(&who[0].1, 0, at, 12);
        let total: u32 = w.drops.iter().map(|d| d.value).sum();
        assert_eq!(total, 12);
        assert!(
            w.drops
                .iter()
                .all(|d| d.owner == who[0].1 || d.owner == who[1].1)
        );
        let piece = green_for(Class::Warrior);
        w.loot_drop(&who[0].1, 0, at, &piece.id);
        let h = heard(&mut who[0].2);
        let id = roll_id(&h);
        assert_eq!(
            w.rolls[0].votes.len(),
            2,
            "two humans vote, the fighter does not"
        );
        let _ = id;
    }

    #[test]
    fn every_vault_enemy_is_elite_and_roll_messages_parse_strictly() {
        for kind in [
            "thrall",
            "archer",
            "acolyte",
            "gatewarden",
            "choir",
            "colossus",
            "hollowking",
        ] {
            assert!(is_elite(kind), "{kind}");
            assert!(
                Slime::new(
                    0,
                    &SlimeSpawn {
                        kind: kind.into(),
                        x: 1.,
                        y: 1.,
                        zone: 0
                    }
                )
                .elite
            );
        }
        assert!(!is_elite("blue"));
        let ok: ClientMessage =
            serde_json::from_str(r#"{"type":"roll","id":7,"choice":"greed"}"#).unwrap();
        assert!(matches!(
            ok,
            ClientMessage::Roll {
                id: 7,
                choice: RollChoice::Greed
            }
        ));
        assert!(
            serde_json::from_str::<ClientMessage>(r#"{"type":"roll","id":7,"choice":"win"}"#)
                .is_err()
        );
        assert!(
            serde_json::from_str::<ClientMessage>(
                r#"{"type":"roll","id":7,"choice":"need","x":1}"#
            )
            .is_err()
        );
    }
}
