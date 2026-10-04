//! Friends and parties.
//!
//! Friendship is mutual and persistent (`Character::friends` holds character ids on both sides). A party is
//! transient: up to `PARTY_MAX` members, one leader, kept only in memory. Requests and invites are in memory too and
//! lapse after `INVITE_LIFETIME` or when either side disconnects. Everything is addressed by character id, because
//! names are not unique; a name is accepted only when exactly one online player carries it.
use super::*;

pub const PARTY_MAX: usize = 5;
pub const FRIENDS_MAX: usize = 50;
const INVITE_LIFETIME: f64 = 60.;
/// A member who disconnects keeps their party seat this long, so a dropped connection that reconnects is not a kick.
const PARTY_GRACE: f64 = 60.;
const PENDING_FRIEND_REQUESTS: usize = 10;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum InviteKind {
    Friend,
    Party,
}
impl InviteKind {
    fn word(self) -> &'static str {
        match self {
            Self::Friend => "friend request",
            Self::Party => "party invite",
        }
    }
    fn tag(self) -> &'static str {
        match self {
            Self::Friend => "friend",
            Self::Party => "party",
        }
    }
}
#[derive(Clone, Debug)]
struct Invite {
    kind: InviteKind,
    from: String,
    to: String,
    expires: f64,
}
/// Name, class and level are remembered so a member who is offline for a moment still has a row.
#[derive(Clone, Debug)]
struct Member {
    id: String,
    name: String,
    class: Class,
    level: u32,
}
#[derive(Clone, Debug)]
struct Party {
    leader: String,
    members: Vec<Member>,
}
#[derive(Default)]
pub struct Social {
    invites: Vec<Invite>,
    parties: Vec<Party>,
    // Party members who are disconnected, and the time they dropped.
    away: BTreeMap<String, f64>,
}

impl World {
    pub(super) fn online(&self, id: &str) -> Option<&Player> {
        self.players.values().find(|p| p.character.id == id)
    }
    pub(super) fn name_of(&self, id: &str) -> String {
        self.online(id)
            .map_or_else(|| "Someone".into(), |p| p.character.look.name.clone())
    }
    fn is_friend(&self, a: &str, b: &str) -> bool {
        self.online(a)
            .is_some_and(|p| p.character.friends.iter().any(|f| f == b))
    }
    /// Character ids of everyone in `id`'s party, `id` included; just `id` when not in one.
    pub(super) fn party_mates(&self, id: &str) -> Vec<String> {
        match self.party_index(id) {
            Some(i) => self.social.parties[i]
                .members
                .iter()
                .map(|m| m.id.clone())
                .collect(),
            None => vec![id.to_string()],
        }
    }
    pub(super) fn party_index(&self, id: &str) -> Option<usize> {
        self.social
            .parties
            .iter()
            .position(|p| p.members.iter().any(|m| m.id == id))
    }
    fn invite_position(&self, kind: InviteKind, from: &str, to: &str) -> Option<usize> {
        self.social
            .invites
            .iter()
            .position(|i| i.kind == kind && i.from == from && i.to == to)
    }
    /// A short message shown in the chat log and the social panel. `ok` is false for a refusal.
    pub(super) fn tell(&self, id: &str, text: impl Into<String>, ok: bool) {
        if let Some(p) = self.online(id) {
            let _ = p
                .peer
                .try_send(json!({"type":"notice","ok":ok,"text":text.into()}));
        }
    }
    fn find_target(
        &self,
        me: &str,
        id: Option<&str>,
        name: Option<&str>,
    ) -> Result<String, String> {
        if let Some(id) = id {
            if id == me {
                return Err("You cannot choose yourself.".into());
            }
            return self
                .online(id)
                .filter(|p| p.merc.is_none())
                .map(|p| p.character.id.clone())
                .ok_or_else(|| "That player is not online.".into());
        }
        let name = name.map(str::trim).filter(|n| !n.is_empty());
        let Some(name) = name else {
            return Err("Name a player or choose one from the list.".into());
        };
        let wanted = name.to_lowercase();
        let mut found = self.players.values().filter(|p| {
            p.merc.is_none()
                && p.character.id != me
                && p.character.look.name.to_lowercase() == wanted
        });
        match (found.next(), found.next()) {
            (Some(p), None) => Ok(p.character.id.clone()),
            (Some(_), Some(_)) => Err(format!(
                "Several players are named {name}. Choose one from the Online list."
            )),
            _ if self
                .online(me)
                .is_some_and(|p| p.character.look.name.to_lowercase() == wanted) =>
            {
                Err("You cannot choose yourself.".into())
            }
            _ => Err(format!("No player named {name} is online.")),
        }
    }

    // ----- state sent to clients -----
    fn friend_entry(&self, id: &str) -> Option<Value> {
        if let Some(p) = self.online(id) {
            let c = &p.character;
            return Some(
                json!({"id":c.id,"name":c.look.name,"class":c.look.class,"level":c.level,"online":true,"place":self.zone_name(c.zone)}),
            );
        }
        self.store.summary(id).map(|s| {
            json!({"id":id,"name":s.name,"class":s.class,"level":s.level,"online":false,"place":null})
        })
    }
    pub(super) fn party_value(&self, index: usize) -> Value {
        let party = &self.social.parties[index];
        let members: Vec<Value> = party
            .members
            .iter()
            .map(|m| match self.online(&m.id) {
                Some(p) => {
                    let c = &p.character;
                    json!({"id":m.id,"name":m.name,"class":c.look.class,"level":c.level,"hp":c.hp.max(0.),"maxHp":c.max_hp(),
                        "zone":c.zone,"place":self.zone_name(c.zone),"online":true,"dead":c.hp<=0.,
                        "quests":c.quests.iter().filter(|q| !q.claimed).map(|q| json!({"id":q.id,"counts":q.counts})).collect::<Vec<_>>()})
                }
                None => json!({"id":m.id,"name":m.name,"class":m.class,"level":m.level,"hp":0,"maxHp":0,"zone":null,
                    "place":null,"online":false,"dead":false,"quests":[]}),
            })
            .collect();
        json!({"leader":party.leader,"max":PARTY_MAX,"members":members,"xp":self.party_xp_value(&party.leader)})
    }
    fn social_state(&self, id: &str) -> Value {
        let Some(p) = self.online(id) else {
            return Value::Null;
        };
        let mut friends: Vec<Value> = p
            .character
            .friends
            .iter()
            .filter_map(|f| self.friend_entry(f))
            .collect();
        friends.sort_by_key(|f| {
            (
                !f["online"].as_bool().unwrap_or(false),
                f["name"].as_str().unwrap_or_default().to_lowercase(),
            )
        });
        let invite = |i: &Invite, other: &str| {
            let (class, level) = self.online(other).map_or((Class::Warrior, 1), |p| {
                (p.character.look.class, p.character.level)
            });
            json!({"kind":i.kind.tag(),"id":other,"name":self.name_of(other),"class":class,"level":level,
                "left":(i.expires-self.time).max(0.)})
        };
        let incoming: Vec<Value> = self
            .social
            .invites
            .iter()
            .filter(|i| i.to == id)
            .map(|i| invite(i, &i.from))
            .collect();
        let outgoing: Vec<Value> = self
            .social
            .invites
            .iter()
            .filter(|i| i.from == id)
            .map(|i| invite(i, &i.to))
            .collect();
        let party = self.party_index(id).map(|i| self.party_value(i));
        json!({"type":"social","friends":friends,"incoming":incoming,"outgoing":outgoing,"party":party,
            "friendsMax":FRIENDS_MAX})
    }
    fn push_social(&self, ids: &[&str]) {
        for id in ids {
            if let Some(p) = self.online(id) {
                let _ = p.peer.try_send(self.social_state(id));
            }
        }
    }
    pub(super) fn push_party(&self, index: usize) {
        let packet = json!({"type":"party","party":self.party_value(index)});
        for m in &self.social.parties[index].members {
            if let Some(p) = self.online(&m.id) {
                let _ = p.peer.try_send(packet.clone());
            }
        }
    }
    fn push_party_members(&self, index: usize) {
        let ids: Vec<&str> = self.social.parties[index]
            .members
            .iter()
            .map(|m| m.id.as_str())
            .collect();
        self.push_social(&ids);
    }

    // ----- connection lifecycle -----
    pub(super) fn social_joined(&mut self, id: &str, name: &str, friends: &[String]) {
        let back = self.social.away.remove(id).is_some();
        for f in friends {
            if self.online(f).is_some() {
                self.tell(f, format!("{name} came online."), true);
                self.push_social(&[f]);
            }
        }
        if back && let Some(i) = self.party_index(id) {
            self.push_party_members(i);
        }
        // Quiet for players with no friends and no party, so their stream is unchanged.
        if !friends.is_empty() || self.party_index(id).is_some() {
            self.push_social(&[id]);
        }
    }
    /// Called after the character has left `players`.
    pub(super) fn social_left(&mut self, id: &str, name: &str, friends: &[String]) {
        let mut others: Vec<String> = vec![];
        self.social.invites.retain(|i| {
            if i.from == id || i.to == id {
                others.push(if i.from == id {
                    i.to.clone()
                } else {
                    i.from.clone()
                });
                false
            } else {
                true
            }
        });
        for other in &others {
            self.push_social(&[other]);
        }
        if let Some(i) = self.party_index(id) {
            self.social.away.insert(id.to_owned(), self.time);
            self.push_party_members(i);
        }
        for f in friends {
            if self.online(f).is_some() {
                self.tell(f, format!("{name} went offline."), true);
                self.push_social(&[f]);
            }
        }
    }
    /// Every half second: lapse invites, drop party members who stayed away, and refresh party health.
    pub(super) fn update_social(&mut self) {
        let now = self.time;
        let mut lapsed = vec![];
        self.social.invites.retain(|i| {
            if i.expires <= now {
                lapsed.push(i.clone());
                false
            } else {
                true
            }
        });
        for i in &lapsed {
            let text = format!(
                "{} did not answer your {}.",
                self.name_of(&i.to),
                i.kind.word()
            );
            self.tell(&i.from, text, false);
            self.push_social(&[&i.from, &i.to]);
        }
        let gone: Vec<String> = self
            .social
            .away
            .iter()
            .filter(|(_, since)| now - **since >= PARTY_GRACE)
            .map(|(id, _)| id.clone())
            .collect();
        for id in gone {
            self.leave_party(&id);
        }
        for i in 0..self.social.parties.len() {
            let levels: Vec<(String, Class, u32)> = self.social.parties[i]
                .members
                .iter()
                .filter_map(|m| {
                    self.online(&m.id)
                        .map(|p| (m.id.clone(), p.character.look.class, p.character.level))
                })
                .collect();
            for (id, class, level) in levels {
                if let Some(m) = self.social.parties[i]
                    .members
                    .iter_mut()
                    .find(|m| m.id == id)
                {
                    m.class = class;
                    m.level = level;
                }
            }
            self.push_party(i);
        }
    }

    // ----- commands -----
    pub(super) fn social(&mut self, session: u64, command: SocialCommand) {
        let Some(me) = self.players.get(&session).map(|p| p.character.id.clone()) else {
            return;
        };
        let result = match command {
            SocialCommand::Refresh => {
                self.push_social(&[&me]);
                Ok(())
            }
            SocialCommand::Who => {
                self.send_who(&me);
                Ok(())
            }
            SocialCommand::FriendRequest { id, name } => {
                self.friend_request(&me, id.as_deref(), name.as_deref())
            }
            SocialCommand::FriendAccept { id } => self.friend_accept(&me, &id),
            SocialCommand::FriendDecline { id } => self.decline(InviteKind::Friend, &me, &id),
            SocialCommand::FriendRemove { id } => self.friend_remove(&me, &id),
            SocialCommand::PartyInvite { id, name } => {
                self.party_invite(&me, id.as_deref(), name.as_deref())
            }
            SocialCommand::PartyAccept { id } => self.party_accept(&me, &id),
            SocialCommand::PartyDecline { id } => self.decline(InviteKind::Party, &me, &id),
            SocialCommand::PartyLeave => {
                if self.party_index(&me).is_none() {
                    Err("You are not in a party.".to_owned())
                } else {
                    self.leave_party(&me);
                    self.tell(&me, "You left the party.", true);
                    Ok(())
                }
            }
            SocialCommand::PartyKick { id } => self.party_kick(&me, &id),
            SocialCommand::PartyPromote { id } => self.party_promote(&me, &id),
            SocialCommand::PartyChat { text } => self.party_chat(session, &me, &text),
        };
        if let Err(text) = result {
            self.tell(&me, text, false);
        }
    }
    fn send_who(&self, me: &str) {
        let (friends, party): (Vec<&str>, Vec<&str>) = (
            self.online(me)
                .map(|p| p.character.friends.iter().map(String::as_str).collect())
                .unwrap_or_default(),
            self.party_index(me)
                .map(|i| {
                    self.social.parties[i]
                        .members
                        .iter()
                        .map(|m| m.id.as_str())
                        .collect()
                })
                .unwrap_or_default(),
        );
        let mut players: Vec<Value> = self
            .players
            .values()
            .filter(|p| p.merc.is_none())
            .map(|p| {
                let c = &p.character;
                json!({"id":c.id,"name":c.look.name,"class":c.look.class,"level":c.level,"place":self.zone_name(c.zone),
                    "self":c.id==me,"friend":friends.contains(&c.id.as_str()),"party":party.contains(&c.id.as_str()),
                    "inParty":self.party_index(&c.id).is_some()})
            })
            .collect();
        players.sort_by_key(|p| p["name"].as_str().unwrap_or_default().to_lowercase());
        if let Some(p) = self.online(me) {
            let _ = p.peer.try_send(json!({"type":"who","players":players}));
        }
    }
    fn add_invite(&mut self, kind: InviteKind, from: &str, to: &str) {
        self.social.invites.push(Invite {
            kind,
            from: from.to_owned(),
            to: to.to_owned(),
            expires: self.time + INVITE_LIFETIME,
        });
    }
    fn decline(&mut self, kind: InviteKind, me: &str, from: &str) -> Result<(), String> {
        let Some(at) = self.invite_position(kind, from, me) else {
            return Err(format!("That {} is no longer pending.", kind.word()));
        };
        self.social.invites.remove(at);
        let text = format!("{} declined your {}.", self.name_of(me), kind.word());
        self.tell(from, text, false);
        self.tell(me, format!("Declined the {}.", kind.word()), true);
        self.push_social(&[me, from]);
        Ok(())
    }

    fn friend_request(
        &mut self,
        me: &str,
        id: Option<&str>,
        name: Option<&str>,
    ) -> Result<(), String> {
        let target = self.find_target(me, id, name)?;
        let their = self.name_of(&target);
        if self.is_friend(me, &target) {
            return Err(format!("{their} is already your friend."));
        }
        // They already asked us: asking back is accepting.
        if self
            .invite_position(InviteKind::Friend, &target, me)
            .is_some()
        {
            return self.friend_accept(me, &target);
        }
        if self
            .invite_position(InviteKind::Friend, me, &target)
            .is_some()
        {
            return Err(format!("You already sent {their} a friend request."));
        }
        let pending = self
            .social
            .invites
            .iter()
            .filter(|i| i.kind == InviteKind::Friend && i.from == me)
            .count();
        if pending >= PENDING_FRIEND_REQUESTS {
            return Err("You have too many friend requests waiting for an answer.".into());
        }
        if self
            .online(me)
            .is_some_and(|p| p.character.friends.len() >= FRIENDS_MAX)
        {
            return Err(format!("Your friends list is full ({FRIENDS_MAX})."));
        }
        self.add_invite(InviteKind::Friend, me, &target);
        self.tell(me, format!("Friend request sent to {their}."), true);
        let mine = self.name_of(me);
        self.tell(&target, format!("{mine} wants to be your friend."), true);
        self.push_social(&[me, &target]);
        Ok(())
    }
    fn friend_accept(&mut self, me: &str, from: &str) -> Result<(), String> {
        let Some(at) = self.invite_position(InviteKind::Friend, from, me) else {
            return Err("That friend request is no longer pending.".into());
        };
        self.social.invites.remove(at);
        let Some(requester) = self.online(from) else {
            return Err("They are offline right now. Ask again when they are back.".into());
        };
        let (their, mine) = (self.name_of(from), self.name_of(me));
        if requester.character.friends.len() >= FRIENDS_MAX {
            return Err(format!("{their}'s friends list is full."));
        }
        if self
            .online(me)
            .is_some_and(|p| p.character.friends.len() >= FRIENDS_MAX)
        {
            return Err(format!("Your friends list is full ({FRIENDS_MAX})."));
        }
        // Both asked each other at the same moment: the second request is moot.
        self.social.invites.retain(|i| {
            !(i.kind == InviteKind::Friend
                && ((i.from == me && i.to == from) || (i.from == from && i.to == me)))
        });
        for p in self.players.values_mut() {
            let c = &mut p.character;
            if c.id == me {
                c.friends.push(from.to_owned());
            } else if c.id == from {
                c.friends.push(me.to_owned());
            }
        }
        self.save();
        self.tell(me, format!("You and {their} are now friends."), true);
        self.tell(from, format!("You and {mine} are now friends."), true);
        self.push_social(&[me, from]);
        Ok(())
    }
    fn friend_remove(&mut self, me: &str, friend: &str) -> Result<(), String> {
        if !self.is_friend(me, friend) {
            return Err("They are not on your friends list.".into());
        }
        let their = self
            .online(friend)
            .map(|p| p.character.look.name.clone())
            .or_else(|| self.store.summary(friend).map(|s| s.name))
            .unwrap_or_else(|| "them".into());
        for p in self.players.values_mut() {
            let c = &mut p.character;
            if c.id == me {
                c.friends.retain(|f| f != friend);
            } else if c.id == friend {
                c.friends.retain(|f| f != me);
            }
        }
        if self.online(friend).is_none() {
            // An offline character is edited in the database. A save that failed earlier is still queued in
            // memory and would write the old list back, so fix that copy too.
            if let Err(e) = self.store.remove_friend(friend, me) {
                tracing::error!(%e,"could not remove a friend from an offline character");
            }
            for c in self.pending_saves.iter_mut().filter(|c| c.id == friend) {
                c.friends.retain(|f| f != me);
            }
        }
        self.save();
        self.tell(me, format!("Removed {their} from your friends."), true);
        self.push_social(&[me, friend]);
        Ok(())
    }

    fn party_invite(
        &mut self,
        me: &str,
        id: Option<&str>,
        name: Option<&str>,
    ) -> Result<(), String> {
        let target = self.find_target(me, id, name)?;
        let their = self.name_of(&target);
        let mine = self.party_index(me);
        let size = mine.map_or(1, |i| self.social.parties[i].members.len());
        if let Some(i) = mine {
            if self.social.parties[i].leader != me {
                return Err("Only the party leader can invite.".into());
            }
            if self.party_index(&target) == Some(i) {
                return Err(format!("{their} is already in your party."));
            }
        }
        if self.party_index(&target).is_some() {
            return Err(format!("{their} is already in a party."));
        }
        if self
            .invite_position(InviteKind::Party, me, &target)
            .is_some()
        {
            return Err(format!("You already invited {their}."));
        }
        // Invites never promise more seats than the party has left.
        let pending = self
            .social
            .invites
            .iter()
            .filter(|i| i.kind == InviteKind::Party && i.from == me)
            .count();
        if size + pending >= PARTY_MAX {
            return Err(if size >= PARTY_MAX {
                format!("Your party is full ({PARTY_MAX}/{PARTY_MAX}).")
            } else {
                "Your open invites already fill the party.".into()
            });
        }
        self.add_invite(InviteKind::Party, me, &target);
        self.tell(me, format!("Party invite sent to {their}."), true);
        let mine_name = self.name_of(me);
        self.tell(
            &target,
            format!("{mine_name} invited you to a party."),
            true,
        );
        self.push_social(&[me, &target]);
        Ok(())
    }
    fn party_accept(&mut self, me: &str, from: &str) -> Result<(), String> {
        let Some(at) = self.invite_position(InviteKind::Party, from, me) else {
            return Err("That party invite is no longer pending.".into());
        };
        self.social.invites.remove(at);
        self.push_social(&[me, from]);
        if self.party_index(me).is_some() {
            return Err("You are already in a party. Leave it first.".into());
        }
        let Some(leader) = self.online(from) else {
            return Err("They are offline right now.".into());
        };
        let joiner = |id: &str, p: &Character| Member {
            id: id.to_owned(),
            name: p.look.name.clone(),
            class: p.look.class,
            level: p.level,
        };
        let inviter = joiner(from, &leader.character);
        let me_member = {
            let Some(p) = self.online(me) else {
                return Ok(());
            };
            joiner(me, &p.character)
        };
        let their = inviter.name.clone();
        let index = match self.party_index(from) {
            Some(i) => {
                if self.social.parties[i].leader != from {
                    return Err(format!("{their} is no longer the party leader."));
                }
                if self.social.parties[i].members.len() >= PARTY_MAX {
                    return Err(format!("That party is full ({PARTY_MAX}/{PARTY_MAX})."));
                }
                self.social.parties[i].members.push(me_member);
                i
            }
            None => {
                self.social.parties.push(Party {
                    leader: from.to_owned(),
                    members: vec![inviter, me_member],
                });
                self.social.parties.len() - 1
            }
        };
        // Whoever else invited this player is now too late, and so are invites between party members.
        let seated: Vec<String> = self.social.parties[index]
            .members
            .iter()
            .map(|m| m.id.clone())
            .collect();
        let mut late = vec![];
        self.social.invites.retain(|i| {
            let stale = i.kind == InviteKind::Party
                && (i.to == me || (i.from == me && seated.contains(&i.to)));
            if stale {
                late.push(if i.to == me {
                    i.from.clone()
                } else {
                    i.to.clone()
                });
            }
            !stale
        });
        for other in &late {
            self.push_social(&[other]);
        }
        let mine_name = self.name_of(me);
        for m in self.social.parties[index].members.clone() {
            if m.id == me {
                self.tell(&m.id, format!("You joined {their}'s party."), true);
            } else {
                self.tell(&m.id, format!("{mine_name} joined the party."), true);
            }
        }
        self.push_party_members(index);
        Ok(())
    }
    /// Removes one member. A party of one disbands; a leaving leader hands over to the longest-standing member.
    pub(super) fn leave_party(&mut self, id: &str) {
        let Some(i) = self.party_index(id) else {
            return;
        };
        self.social.away.remove(id);
        let party = &mut self.social.parties[i];
        party.members.retain(|m| m.id != id);
        let mut touched: Vec<String> = party.members.iter().map(|m| m.id.clone()).collect();
        touched.push(id.to_owned());
        if party.members.len() < 2 {
            let rest = self.social.parties.remove(i);
            for m in rest.members {
                self.social.away.remove(&m.id);
                self.tell(&m.id, "The party was disbanded.", true);
            }
        } else if party.leader == id {
            party.leader = party.members[0].id.clone();
            let (leader, ids) = (
                party.members[0].name.clone(),
                party
                    .members
                    .iter()
                    .map(|m| m.id.clone())
                    .collect::<Vec<_>>(),
            );
            for member in ids {
                self.tell(&member, format!("{leader} is now the party leader."), true);
            }
        }
        let ids: Vec<&str> = touched.iter().map(String::as_str).collect();
        self.push_social(&ids);
    }
    /// Seats a hired mercenary in `owner`'s party (making one with them when they have none).
    pub(super) fn party_add_mercenary(
        &mut self,
        owner: &str,
        merc: &Character,
    ) -> Result<(), String> {
        let member = |id: &str, c: &Character| Member {
            id: id.to_owned(),
            name: c.look.name.clone(),
            class: c.look.class,
            level: c.level,
        };
        let merc_member = member(&merc.id, merc);
        let index = match self.party_index(owner) {
            Some(i) => {
                if self.social.parties[i].members.len() >= PARTY_MAX {
                    return Err(format!("Your party is full ({PARTY_MAX}/{PARTY_MAX})."));
                }
                self.social.parties[i].members.push(merc_member);
                i
            }
            None => {
                let Some(me) = self.online(owner).map(|p| member(owner, &p.character)) else {
                    return Err("You are not online.".into());
                };
                self.social.parties.push(Party {
                    leader: owner.to_owned(),
                    members: vec![me, merc_member],
                });
                self.social.parties.len() - 1
            }
        };
        self.push_party_members(index);
        Ok(())
    }
    fn party_member_of(&self, me: &str, target: &str) -> Result<usize, String> {
        let i = self.party_index(me).ok_or("You are not in a party.")?;
        if self.social.parties[i].leader != me {
            return Err("Only the party leader can do that.".into());
        }
        if target == me {
            return Err("You cannot choose yourself.".into());
        }
        if !self.social.parties[i]
            .members
            .iter()
            .any(|m| m.id == target)
        {
            return Err("That player is not in your party.".into());
        }
        Ok(i)
    }
    fn party_kick(&mut self, me: &str, target: &str) -> Result<(), String> {
        let i = self.party_member_of(me, target)?;
        let name = self.social.parties[i]
            .members
            .iter()
            .find(|m| m.id == target)
            .map_or_else(String::new, |m| m.name.clone());
        self.tell(target, "You were removed from the party.", false);
        self.leave_party(target);
        self.tell(me, format!("Removed {name} from the party."), true);
        Ok(())
    }
    fn party_promote(&mut self, me: &str, target: &str) -> Result<(), String> {
        let i = self.party_member_of(me, target)?;
        if self.online(target).is_some_and(|p| p.merc.is_some()) {
            return Err("A mercenary cannot lead a party.".into());
        }
        self.social.parties[i].leader = target.to_owned();
        let name = self.name_of(target);
        for m in self.social.parties[i].members.clone() {
            self.tell(&m.id, format!("{name} is now the party leader."), true);
        }
        self.push_party_members(i);
        Ok(())
    }
    fn party_chat(&mut self, session: u64, me: &str, text: &str) -> Result<(), String> {
        let text = text.trim();
        if text.is_empty() || text.chars().count() > 240 || text.chars().any(char::is_control) {
            return Ok(());
        }
        let i = self.party_index(me).ok_or("You are not in a party.")?;
        let Some(p) = self.players.get_mut(&session) else {
            return Ok(());
        };
        if self.time - p.chat_at < 1. {
            return Err("Please wait a moment before chatting again.".into());
        }
        p.chat_at = self.time;
        let packet = json!({"type":"chat","channel":"party","name":p.character.look.name,"id":me,"text":text});
        for m in &self.social.parties[i].members {
            if let Some(p) = self.online(&m.id) {
                let _ = p.peer.try_send(packet.clone());
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Player {
        session: u64,
        id: String,
        token: String,
        rx: mpsc::Receiver<Value>,
        // Everything received so far, and how much of it heard() already returned.
        seen: Vec<Value>,
        cursor: usize,
    }
    fn world() -> World {
        World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0)
    }
    fn add(w: &mut World, session: u64, name: &str) -> Player {
        let (tx, rx) = mpsc::channel(512);
        let look = Look {
            name: name.into(),
            ..Look::default()
        };
        let welcome = w.join(session, None, Some(look), tx).unwrap();
        Player {
            session,
            id: welcome["id"].as_str().unwrap().into(),
            token: welcome["token"].as_str().unwrap().into(),
            rx,
            seen: vec![],
            cursor: 0,
        }
    }
    fn rejoin(w: &mut World, session: u64, token: &str) -> Player {
        let (tx, rx) = mpsc::channel(512);
        let welcome = w.join(session, Some(token.into()), None, tx).unwrap();
        Player {
            session,
            id: welcome["id"].as_str().unwrap().into(),
            token: token.into(),
            rx,
            seen: vec![],
            cursor: 0,
        }
    }
    fn party_of(w: &World, who: &Player) -> Option<Vec<String>> {
        w.party_index(&who.id).map(|i| {
            w.social.parties[i]
                .members
                .iter()
                .map(|m| m.name.clone())
                .collect()
        })
    }
    fn say(w: &mut World, who: &Player, command: SocialCommand) {
        w.social(who.session, command);
    }
    fn by_name(name: &str) -> SocialCommand {
        SocialCommand::FriendRequest {
            id: None,
            name: Some(name.into()),
        }
    }
    fn invite_by_id(who: &Player) -> SocialCommand {
        SocialCommand::PartyInvite {
            id: Some(who.id.clone()),
            name: None,
        }
    }
    fn accept_party(from: &Player) -> SocialCommand {
        SocialCommand::PartyAccept {
            id: from.id.clone(),
        }
    }
    /// Everything this player was told since the last call.
    fn heard(who: &mut Player) -> Vec<Value> {
        while let Ok(v) = who.rx.try_recv() {
            who.seen.push(v);
        }
        let new = who.seen[who.cursor..].to_vec();
        who.cursor = who.seen.len();
        new
    }
    fn notices(who: &mut Player) -> Vec<String> {
        heard(who)
            .into_iter()
            .filter(|v| v["type"] == "notice")
            .map(|v| v["text"].as_str().unwrap().to_owned())
            .collect()
    }
    /// The newest full state this player has received, whether or not heard() already returned it.
    fn latest_state(who: &mut Player) -> Value {
        heard(who);
        who.seen
            .iter()
            .rfind(|v| v["type"] == "social")
            .cloned()
            .expect("a social state")
    }
    fn refused(who: &mut Player, needle: &str) {
        let said = heard(who);
        assert!(
            said.iter().any(|v| v["type"] == "notice"
                && v["ok"] == false
                && v["text"].as_str().unwrap().contains(needle)),
            "expected a refusal containing {needle:?}, got {said:?}"
        );
    }
    fn befriend(w: &mut World, a: &Player, b: &Player, b_name: &str) {
        say(w, a, by_name(b_name));
        say(w, b, SocialCommand::FriendAccept { id: a.id.clone() });
    }

    #[test]
    fn friendship_is_mutual_saved_and_listed_with_online_state() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let mut bob = add(&mut w, 2, "Bob");
        // Players with no friends and no party hear nothing extra on joining.
        assert!(heard(&mut ann).iter().all(|v| v["type"] != "social"));
        say(&mut w, &ann, by_name("bob"));
        assert!(
            notices(&mut ann)
                .iter()
                .any(|t| t.contains("Friend request sent to Bob"))
        );
        let state = latest_state(&mut bob);
        assert_eq!(state["incoming"][0]["id"], ann.id);
        assert_eq!(state["incoming"][0]["kind"], "friend");
        assert!(state["friends"].as_array().unwrap().is_empty());
        say(
            &mut w,
            &bob,
            SocialCommand::FriendAccept { id: ann.id.clone() },
        );
        assert_eq!(w.players[&1].character.friends, vec![bob.id.clone()]);
        assert_eq!(w.players[&2].character.friends, vec![ann.id.clone()]);
        let state = latest_state(&mut ann);
        assert_eq!(state["friends"][0]["name"], "Bob");
        assert_eq!(state["friends"][0]["online"], true);
        assert!(state["incoming"].as_array().unwrap().is_empty());
        assert!(state["outgoing"].as_array().unwrap().is_empty());
        // Both sides are saved at once.
        assert_eq!(
            w.store.load(&ann.token).unwrap().unwrap().friends,
            vec![bob.id.clone()]
        );
        assert_eq!(
            w.store.load(&bob.token).unwrap().unwrap().friends,
            vec![ann.id.clone()]
        );
        // Going offline is announced, and the offline friend stays listed with the last known level.
        w.leave(2);
        let said = notices(&mut ann);
        assert!(said.iter().any(|t| t == "Bob went offline."), "{said:?}");
        let state = latest_state(&mut ann);
        assert_eq!(state["friends"][0]["online"], false);
        assert_eq!(state["friends"][0]["name"], "Bob");
        assert_eq!(state["friends"][0]["level"], 1);
        let mut bob = rejoin(&mut w, 3, &bob.token);
        assert!(notices(&mut ann).iter().any(|t| t == "Bob came online."));
        assert_eq!(latest_state(&mut bob)["friends"][0]["name"], "Ann");
        assert_eq!(latest_state(&mut ann)["friends"][0]["online"], true);
    }

    #[test]
    fn friend_requests_follow_the_rules() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let mut bob = add(&mut w, 2, "Bob");
        let twin_a = add(&mut w, 3, "Twin");
        let twin_b = add(&mut w, 4, "twin");
        say(&mut w, &ann, by_name("Ann"));
        refused(&mut ann, "yourself");
        say(
            &mut w,
            &ann,
            SocialCommand::FriendRequest {
                id: Some(ann.id.clone()),
                name: None,
            },
        );
        refused(&mut ann, "yourself");
        say(&mut w, &ann, by_name("Nobody"));
        refused(&mut ann, "No player named Nobody");
        say(&mut w, &ann, by_name("  "));
        refused(&mut ann, "Name a player");
        say(
            &mut w,
            &ann,
            SocialCommand::FriendRequest {
                id: Some("missing".into()),
                name: None,
            },
        );
        refused(&mut ann, "not online");
        // Two players called Twin: a name is ambiguous, an id is not.
        say(&mut w, &ann, by_name("TWIN"));
        refused(&mut ann, "Several players are named TWIN");
        say(
            &mut w,
            &ann,
            SocialCommand::FriendRequest {
                id: Some(twin_b.id.clone()),
                name: None,
            },
        );
        assert!(
            notices(&mut ann)
                .iter()
                .any(|t| t.contains("Friend request sent to twin"))
        );
        say(
            &mut w,
            &ann,
            SocialCommand::FriendRequest {
                id: Some(twin_b.id.clone()),
                name: None,
            },
        );
        refused(&mut ann, "already sent");
        // A decline tells the sender and clears both lists.
        say(
            &mut w,
            &twin_b,
            SocialCommand::FriendDecline { id: ann.id.clone() },
        );
        assert!(
            notices(&mut ann)
                .iter()
                .any(|t| t.contains("twin declined your friend request"))
        );
        assert!(
            latest_state(&mut ann)["outgoing"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        say(
            &mut w,
            &twin_b,
            SocialCommand::FriendAccept { id: ann.id.clone() },
        );
        // Asking someone who already asked you is accepting.
        say(&mut w, &ann, by_name("Bob"));
        say(&mut w, &bob, by_name("Ann"));
        assert_eq!(w.players[&1].character.friends, vec![bob.id.clone()]);
        assert!(w.social.invites.is_empty());
        say(&mut w, &ann, by_name("Bob"));
        refused(&mut ann, "already your friend");
        // An answer to a request that never existed does nothing.
        say(
            &mut w,
            &bob,
            SocialCommand::FriendAccept {
                id: twin_a.id.clone(),
            },
        );
        refused(&mut bob, "no longer pending");
    }

    #[test]
    fn requests_lapse_and_vanish_with_a_disconnect() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let mut bob = add(&mut w, 2, "Bob");
        let cat = add(&mut w, 3, "Cat");
        say(&mut w, &ann, by_name("Bob"));
        say(&mut w, &ann, invite_by_id(&cat));
        heard(&mut ann);
        heard(&mut bob);
        w.time += INVITE_LIFETIME + 1.;
        w.update_social();
        assert!(w.social.invites.is_empty());
        let said = notices(&mut ann);
        assert!(
            said.iter()
                .any(|t| t == "Bob did not answer your friend request."),
            "{said:?}"
        );
        assert!(
            said.iter()
                .any(|t| t == "Cat did not answer your party invite."),
            "{said:?}"
        );
        assert!(
            latest_state(&mut bob)["incoming"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        say(
            &mut w,
            &bob,
            SocialCommand::FriendAccept { id: ann.id.clone() },
        );
        refused(&mut bob, "no longer pending");
        // A request to someone who then disconnects disappears; so does one from them.
        say(&mut w, &ann, by_name("Bob"));
        say(&mut w, &bob, invite_by_id(&cat));
        w.leave(2);
        assert!(w.social.invites.is_empty());
        assert!(
            latest_state(&mut ann)["outgoing"]
                .as_array()
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn removing_a_friend_works_online_and_offline() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let mut bob = add(&mut w, 2, "Bob");
        let cat = add(&mut w, 3, "Cat");
        befriend(&mut w, &ann, &bob, "Bob");
        befriend(&mut w, &ann, &cat, "Cat");
        say(
            &mut w,
            &ann,
            SocialCommand::FriendRemove { id: bob.id.clone() },
        );
        assert!(w.players[&1].character.friends == vec![cat.id.clone()]);
        assert!(w.players[&2].character.friends.is_empty());
        assert!(
            latest_state(&mut bob)["friends"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        assert_eq!(w.store.load(&bob.token).unwrap().unwrap().friends.len(), 0);
        say(
            &mut w,
            &ann,
            SocialCommand::FriendRemove { id: bob.id.clone() },
        );
        refused(&mut ann, "not on your friends list");
        // Cat is offline when removed; her saved character loses Ann without any other field changing.
        w.leave(3);
        let before = w.store.load(&cat.token).unwrap().unwrap();
        assert_eq!(before.friends, vec![ann.id.clone()]);
        say(
            &mut w,
            &ann,
            SocialCommand::FriendRemove { id: cat.id.clone() },
        );
        assert!(
            notices(&mut ann)
                .iter()
                .any(|t| t == "Removed Cat from your friends.")
        );
        let after = w.store.load(&cat.token).unwrap().unwrap();
        assert!(after.friends.is_empty());
        assert_eq!(after.inventory, before.inventory);
        let cat = rejoin(&mut w, 4, &cat.token);
        assert!(w.players[&4].character.friends.is_empty());
        assert_eq!(cat.id, before.id);
        // Removing a stranger or yourself does nothing.
        say(
            &mut w,
            &ann,
            SocialCommand::FriendRemove { id: ann.id.clone() },
        );
        refused(&mut ann, "not on your friends list");
    }

    #[test]
    fn the_friends_list_has_a_ceiling() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let bob = add(&mut w, 2, "Bob");
        w.players.get_mut(&1).unwrap().character.friends =
            (0..FRIENDS_MAX).map(|i| format!("ghost-{i}")).collect();
        say(&mut w, &ann, by_name("Bob"));
        refused(&mut ann, "friends list is full");
        // A full list on the other side blocks the acceptance and keeps both lists unchanged.
        w.players.get_mut(&1).unwrap().character.friends.clear();
        say(&mut w, &ann, by_name("Bob"));
        w.players.get_mut(&1).unwrap().character.friends =
            (0..FRIENDS_MAX).map(|i| format!("ghost-{i}")).collect();
        let mut bob = bob;
        say(
            &mut w,
            &bob,
            SocialCommand::FriendAccept { id: ann.id.clone() },
        );
        refused(&mut bob, "friends list is full");
        assert_eq!(w.players[&2].character.friends.len(), 0);
        assert_eq!(w.players[&1].character.friends.len(), FRIENDS_MAX);
    }

    #[test]
    fn a_party_holds_five_and_a_sixth_is_refused() {
        let mut w = world();
        let mut leader = add(&mut w, 1, "Lead");
        let mut members: Vec<Player> = (2..=5)
            .map(|s| add(&mut w, s, &format!("Mem{s}")))
            .collect();
        let mut sixth = add(&mut w, 6, "Mem6");
        for m in &members {
            say(&mut w, &leader, invite_by_id(m));
        }
        // Four open invites already fill the party.
        say(&mut w, &leader, invite_by_id(&sixth));
        refused(&mut leader, "already fill the party");
        for m in &members {
            say(&mut w, m, accept_party(&leader));
        }
        assert_eq!(party_of(&w, &leader).unwrap().len(), PARTY_MAX);
        assert_eq!(w.social.parties[0].leader, leader.id);
        say(&mut w, &leader, invite_by_id(&sixth));
        refused(&mut leader, "party is full");
        // A member cannot invite either; only the leader may.
        say(&mut w, &members[0], invite_by_id(&sixth));
        refused(&mut members[0], "Only the party leader can invite");
        assert!(party_of(&w, &sixth).is_none());
        // Everyone sees the same five, with the leader marked.
        let state = latest_state(&mut members[3]);
        assert_eq!(state["party"]["members"].as_array().unwrap().len(), 5);
        assert_eq!(state["party"]["leader"], leader.id);
        assert_eq!(state["party"]["max"], 5);
        assert!(w.social.invites.is_empty());
        // Someone leaving frees the seat for the sixth.
        let mut gone = members.remove(0);
        say(&mut w, &gone, SocialCommand::PartyLeave);
        assert!(
            notices(&mut gone)
                .iter()
                .any(|t| t == "You left the party.")
        );
        assert!(latest_state(&mut gone)["party"].is_null());
        say(&mut w, &leader, invite_by_id(&sixth));
        say(&mut w, &sixth, accept_party(&leader));
        assert_eq!(party_of(&w, &leader).unwrap().len(), PARTY_MAX);
        assert_eq!(w.social.parties.len(), 1);
        let _ = heard(&mut sixth);
    }

    #[test]
    fn party_invites_refuse_players_who_are_taken() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let bob = add(&mut w, 2, "Bob");
        let mut cat = add(&mut w, 3, "Cat");
        let dan = add(&mut w, 4, "Dan");
        say(&mut w, &ann, invite_by_id(&ann));
        refused(&mut ann, "yourself");
        say(&mut w, &ann, invite_by_id(&bob));
        say(&mut w, &ann, invite_by_id(&bob));
        refused(&mut ann, "already invited");
        say(&mut w, &bob, accept_party(&ann));
        say(&mut w, &ann, invite_by_id(&bob));
        refused(&mut ann, "already in your party");
        // Cat leads her own party with Dan, so Ann cannot invite her and she cannot join Ann.
        say(&mut w, &cat, invite_by_id(&dan));
        say(&mut w, &dan, accept_party(&cat));
        say(&mut w, &ann, invite_by_id(&cat));
        refused(&mut ann, "already in a party");
        say(&mut w, &cat, invite_by_id(&bob));
        refused(&mut cat, "already in a party");
        // An invite sent earlier fails once the invitee is elsewhere.
        let mut eve = add(&mut w, 5, "Eve");
        say(&mut w, &ann, invite_by_id(&eve));
        say(&mut w, &cat, invite_by_id(&eve));
        say(&mut w, &eve, accept_party(&cat));
        assert!(
            latest_state(&mut ann)["outgoing"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        say(&mut w, &eve, accept_party(&ann));
        refused(&mut eve, "no longer pending");
        let mut names = party_of(&w, &cat).unwrap();
        names.sort();
        assert_eq!(names, ["Cat", "Dan", "Eve"]);
        say(
            &mut w,
            &eve,
            SocialCommand::PartyAccept {
                id: "nobody".into(),
            },
        );
        refused(&mut eve, "no longer pending");
        let _ = heard(&mut cat);
    }

    #[test]
    fn leaders_can_kick_promote_and_hand_over() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let mut bob = add(&mut w, 2, "Bob");
        let mut cat = add(&mut w, 3, "Cat");
        for p in [&bob, &cat] {
            say(&mut w, &ann, invite_by_id(p));
            say(&mut w, p, accept_party(&ann));
        }
        say(
            &mut w,
            &bob,
            SocialCommand::PartyKick { id: cat.id.clone() },
        );
        refused(&mut bob, "Only the party leader");
        say(
            &mut w,
            &bob,
            SocialCommand::PartyPromote { id: bob.id.clone() },
        );
        refused(&mut bob, "Only the party leader");
        say(
            &mut w,
            &ann,
            SocialCommand::PartyKick { id: ann.id.clone() },
        );
        refused(&mut ann, "yourself");
        say(
            &mut w,
            &ann,
            SocialCommand::PartyKick {
                id: "stranger".into(),
            },
        );
        refused(&mut ann, "not in your party");
        say(
            &mut w,
            &ann,
            SocialCommand::PartyPromote { id: bob.id.clone() },
        );
        assert_eq!(w.social.parties[0].leader, bob.id);
        assert!(
            notices(&mut cat)
                .iter()
                .any(|t| t == "Bob is now the party leader.")
        );
        // The new leader removes Cat.
        say(
            &mut w,
            &bob,
            SocialCommand::PartyKick { id: cat.id.clone() },
        );
        assert!(
            notices(&mut cat)
                .iter()
                .any(|t| t == "You were removed from the party.")
        );
        assert!(party_of(&w, &cat).is_none());
        assert!(latest_state(&mut cat)["party"].is_null());
        // A party of two disbands when its leader leaves.
        say(&mut w, &bob, SocialCommand::PartyLeave);
        assert!(w.social.parties.is_empty());
        assert!(
            notices(&mut ann)
                .iter()
                .any(|t| t == "The party was disbanded.")
        );
        assert!(latest_state(&mut ann)["party"].is_null());
        say(&mut w, &ann, SocialCommand::PartyLeave);
        refused(&mut ann, "not in a party");
        // With three members, the leader leaving hands the party to the longest-standing member.
        for p in [&bob, &cat] {
            say(&mut w, &ann, invite_by_id(p));
            say(&mut w, p, accept_party(&ann));
        }
        say(&mut w, &ann, SocialCommand::PartyLeave);
        assert_eq!(party_of(&w, &bob).unwrap(), ["Bob", "Cat"]);
        assert_eq!(w.social.parties[0].leader, bob.id);
    }

    #[test]
    fn a_dropped_member_keeps_their_seat_for_a_minute() {
        let mut w = world();
        let ann = add(&mut w, 1, "Ann");
        let mut bob = add(&mut w, 2, "Bob");
        let cat = add(&mut w, 3, "Cat");
        for p in [&bob, &cat] {
            say(&mut w, &ann, invite_by_id(p));
            say(&mut w, p, accept_party(&ann));
        }
        heard(&mut bob);
        w.leave(3);
        assert_eq!(party_of(&w, &ann).unwrap().len(), 3);
        w.update_social();
        let party = heard(&mut bob)
            .into_iter()
            .rfind(|v| v["type"] == "party")
            .unwrap();
        let cat_row = party["party"]["members"]
            .as_array()
            .unwrap()
            .iter()
            .find(|m| m["name"] == "Cat")
            .unwrap()
            .clone();
        assert_eq!(cat_row["online"], false);
        w.time += PARTY_GRACE - 10.;
        w.update_social();
        assert_eq!(party_of(&w, &ann).unwrap().len(), 3);
        // Reconnecting inside the minute restores the seat and the party view.
        let mut cat = rejoin(&mut w, 4, &cat.token);
        assert!(w.social.away.is_empty());
        assert_eq!(
            latest_state(&mut cat)["party"]["members"]
                .as_array()
                .unwrap()
                .len(),
            3
        );
        w.time += PARTY_GRACE;
        w.update_social();
        assert_eq!(party_of(&w, &cat).unwrap().len(), 3);
        // Staying away past the minute gives the seat up; a leader who stays away hands over.
        w.leave(1);
        w.leave(4);
        w.time += PARTY_GRACE - 1.;
        w.update_social();
        assert_eq!(party_of(&w, &bob).unwrap().len(), 3);
        w.time += 2.;
        w.update_social();
        assert!(
            w.social.parties.is_empty(),
            "everyone else stayed away, so the party dissolves"
        );
        assert!(w.social.away.is_empty());
        assert!(latest_state_for(&mut bob).is_null());
    }
    fn latest_state_for(who: &mut Player) -> Value {
        latest_state(who)["party"].clone()
    }

    #[test]
    fn party_chat_reaches_only_the_party_and_is_rate_limited() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let mut bob = add(&mut w, 2, "Bob");
        let mut cat = add(&mut w, 3, "Cat");
        say(
            &mut w,
            &ann,
            SocialCommand::PartyChat {
                text: "hello".into(),
            },
        );
        refused(&mut ann, "not in a party");
        say(&mut w, &ann, invite_by_id(&bob));
        say(&mut w, &bob, accept_party(&ann));
        heard(&mut ann);
        heard(&mut bob);
        heard(&mut cat);
        w.time += 2.;
        say(
            &mut w,
            &bob,
            SocialCommand::PartyChat {
                text: "  rally at the gate  ".into(),
            },
        );
        for who in [&mut ann, &mut bob] {
            let chat: Vec<Value> = heard(who)
                .into_iter()
                .filter(|v| v["type"] == "chat")
                .collect();
            assert_eq!(chat.len(), 1);
            assert_eq!(chat[0]["channel"], "party");
            assert_eq!(chat[0]["name"], "Bob");
            assert_eq!(chat[0]["text"], "rally at the gate");
        }
        assert!(heard(&mut cat).iter().all(|v| v["type"] != "chat"));
        say(
            &mut w,
            &bob,
            SocialCommand::PartyChat {
                text: "again".into(),
            },
        );
        refused(&mut bob, "wait a moment");
        w.time += 2.;
        for bad in ["", "   ", "a\u{7}b", &"x".repeat(241)] {
            say(&mut w, &bob, SocialCommand::PartyChat { text: bad.into() });
        }
        assert!(heard(&mut ann).iter().all(|v| v["type"] != "chat"));
    }

    #[test]
    fn who_lists_everyone_with_their_relationship() {
        let mut w = world();
        let mut ann = add(&mut w, 1, "Ann");
        let bob = add(&mut w, 2, "Bob");
        let cat = add(&mut w, 3, "Cat");
        befriend(&mut w, &ann, &bob, "Bob");
        say(&mut w, &ann, invite_by_id(&cat));
        say(&mut w, &cat, accept_party(&ann));
        heard(&mut ann);
        say(&mut w, &ann, SocialCommand::Who);
        let who = heard(&mut ann)
            .into_iter()
            .find(|v| v["type"] == "who")
            .unwrap();
        let rows = who["players"].as_array().unwrap();
        let row = |name: &str| rows.iter().find(|p| p["name"] == name).unwrap();
        assert_eq!(rows.len(), 3);
        assert_eq!(row("Ann")["self"], true);
        assert_eq!(row("Bob")["friend"], true);
        assert_eq!(row("Bob")["inParty"], false);
        assert_eq!(row("Cat")["party"], true);
        assert_eq!(row("Cat")["friend"], false);
    }

    #[test]
    fn health_changes_reach_the_party_every_half_second() {
        let mut w = world();
        let ann = add(&mut w, 1, "Ann");
        let mut bob = add(&mut w, 2, "Bob");
        say(&mut w, &ann, invite_by_id(&bob));
        say(&mut w, &bob, accept_party(&ann));
        w.players.get_mut(&1).unwrap().character.hp = 17.;
        heard(&mut bob);
        for _ in 0..10 {
            w.step();
        }
        let party = heard(&mut bob)
            .into_iter()
            .rfind(|v| v["type"] == "party")
            .unwrap();
        let row = party["party"]["members"]
            .as_array()
            .unwrap()
            .iter()
            .find(|m| m["name"] == "Ann")
            .unwrap()
            .clone();
        assert_eq!(row["hp"].as_f64(), Some(w.players[&1].character.hp));
        assert!(
            row["hp"].as_f64().unwrap() < 30.,
            "the pushed value is the damaged one"
        );
        assert_eq!(row["maxHp"], 120.);
        assert_eq!(row["place"], "Greenmeadow");
    }

    #[test]
    fn social_messages_parse_strictly() {
        let parse = |text: &str| serde_json::from_str::<ClientMessage>(text);
        assert!(matches!(
            parse(r#"{"type":"social","command":{"op":"friend_request","name":"Ann"}}"#),
            Ok(ClientMessage::Social {
                command: SocialCommand::FriendRequest { .. }
            })
        ));
        assert!(matches!(
            parse(r#"{"type":"social","command":{"op":"party_leave"}}"#),
            Ok(ClientMessage::Social {
                command: SocialCommand::PartyLeave
            })
        ));
        assert!(
            parse(r#"{"type":"social","command":{"op":"friend_remove","id":"a","extra":1}}"#)
                .is_err()
        );
        assert!(parse(r#"{"type":"social","command":{"op":"party_disband"}}"#).is_err());
        assert!(parse(r#"{"type":"social","command":{"op":"friend_accept"}}"#).is_err());
    }

    fn priest(w: &mut World, session: u64, name: &str, level: u32) -> Player {
        let (tx, rx) = mpsc::channel(512);
        let look = Look {
            name: name.into(),
            class: Class::Priest,
            ..Look::default()
        };
        let welcome = w.join(session, None, Some(look), tx).unwrap();
        w.players.get_mut(&session).unwrap().character.level = level;
        Player {
            session,
            id: welcome["id"].as_str().unwrap().into(),
            token: welcome["token"].as_str().unwrap().into(),
            rx,
            seen: vec![],
            cursor: 0,
        }
    }
    fn team(w: &mut World, leader: &Player, others: &[&Player]) {
        for other in others {
            say(w, leader, invite_by_id(other));
            say(w, other, accept_party(leader));
        }
    }
    fn hp(w: &World, who: &Player) -> f64 {
        w.players[&who.session].character.hp
    }
    fn set_hp(w: &mut World, who: &Player, hp: f64) {
        w.players.get_mut(&who.session).unwrap().character.hp = hp;
    }

    #[test]
    fn a_priest_mends_the_most_wounded_party_member_in_range_and_never_a_stranger() {
        let mut w = world();
        let mut pia = priest(&mut w, 1, "Pia", 10);
        let mut ann = add(&mut w, 2, "Ann");
        let bob = add(&mut w, 3, "Bob");
        let stranger = add(&mut w, 4, "Sam");
        team(&mut w, &pia, &[&ann, &bob]);
        let pia_full = w.players[&1].character.max_hp();
        set_hp(&mut w, &pia, pia_full);
        set_hp(&mut w, &ann, 20.);
        set_hp(&mut w, &bob, 60.);
        set_hp(&mut w, &stranger, 10.);
        heard(&mut pia);
        heard(&mut ann);
        w.use_skill(1, "mend", Point::default());
        // One target: the most wounded fraction. The stranger is not in the party, so is never healed.
        assert!(hp(&w, &ann) > 60., "{}", hp(&w, &ann));
        assert_eq!(hp(&w, &bob), 60.);
        assert_eq!(hp(&w, &stranger), 10.);
        let told: Vec<_> = heard(&mut ann)
            .into_iter()
            .filter(|v| v["kind"] == "healed")
            .collect();
        assert_eq!(told.len(), 1);
        assert_eq!(told[0]["actor"], ann.id);
        assert_eq!(told[0]["from"], pia.id);
        assert!(told[0]["value"].as_f64().unwrap() > 40.);
        assert!(w.players[&1].skill_cd.contains_key("mend"));
        // The cap is the target's maximum health.
        let full = w.players[&2].character.max_hp();
        set_hp(&mut w, &ann, full - 1.);
        set_hp(&mut w, &bob, full);
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        w.use_skill(1, "mend", Point::default());
        assert_eq!(hp(&w, &ann), full);
        // A party member out of range is skipped, and with nobody hurt in range the skill fizzles for free.
        set_hp(&mut w, &ann, full);
        set_hp(&mut w, &bob, 30.);
        w.players.get_mut(&3).unwrap().character.x += 40.;
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        heard(&mut pia);
        w.use_skill(1, "mend", Point::default());
        assert_eq!(hp(&w, &bob), 30.);
        assert!(!w.players[&1].skill_cd.contains_key("mend"));
        assert!(
            heard(&mut pia)
                .iter()
                .any(|v| v["type"] == "error" && v["text"] == "Nobody nearby needs healing.")
        );
    }

    #[test]
    fn a_priest_alone_heals_themself_and_a_prayer_reaches_up_to_five() {
        let mut w = world();
        let pia = priest(&mut w, 1, "Pia", 10);
        set_hp(&mut w, &pia, 40.);
        w.use_skill(1, "mend", Point::default());
        assert!(hp(&w, &pia) > 40.);
        let mut members = vec![];
        for n in 0..5u64 {
            members.push(add(&mut w, 10 + n, &format!("Mate{n}")));
        }
        let refs: Vec<&Player> = members.iter().take(4).collect();
        team(&mut w, &pia, &refs);
        for m in &members[..4] {
            set_hp(&mut w, m, 30.);
        }
        set_hp(&mut w, &pia, 30.);
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        w.use_skill(1, "prayer", Point::default());
        for m in &members[..4] {
            assert!(hp(&w, m) > 30., "a prayer heals every wounded member");
        }
        assert!(hp(&w, &pia) > 30.);
        // The fifth mate never joined the party (it holds the priest and four), so a prayer leaves them hurt.
        set_hp(&mut w, &members[4], 30.);
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        w.use_skill(1, "prayer", Point::default());
        assert_eq!(hp(&w, &members[4]), 30.);
    }

    #[test]
    fn priest_blessings_and_pulses_reach_party_members_in_range_only() {
        let mut w = world();
        let pia = priest(&mut w, 1, "Pia", 20);
        let ann = add(&mut w, 2, "Ann");
        let far = add(&mut w, 3, "Far");
        let stranger = add(&mut w, 4, "Sam");
        team(&mut w, &pia, &[&ann, &far]);
        w.players.get_mut(&3).unwrap().character.x += 30.;
        w.use_skill(1, "blessing", Point::default());
        let blessed = |w: &World, s: u64| w.players[&s].buff(BuffKind::Damage);
        assert_eq!(blessed(&w, 1), 0.3);
        assert_eq!(blessed(&w, 2), 0.3);
        assert_eq!(blessed(&w, 3), 0.);
        assert_eq!(blessed(&w, 4), 0.);
        // Holy Nova heals the party in range even with no enemy to hit; a stranger gets nothing.
        for who in [&pia, &ann, &stranger] {
            set_hp(&mut w, who, 25.);
        }
        w.use_skill(1, "holynova", Point::default());
        assert!(hp(&w, &pia) > 25. && hp(&w, &ann) > 25.);
        assert_eq!(hp(&w, &stranger), 25.);
        // A dead party member is never healed.
        set_hp(&mut w, &ann, 0.);
        w.players.get_mut(&1).unwrap().skill_cd.clear();
        w.use_skill(1, "heavenswrath", Point::default());
        assert_eq!(hp(&w, &ann), 0.);
    }

    #[test]
    fn a_priest_fights_alone_with_a_mace_and_smite() {
        let mut w = world();
        let pia = priest(&mut w, 1, "Pia", 4);
        let c = &w.players[&pia.session].character;
        assert_eq!(c.look.class, Class::Priest);
        assert_eq!(
            (c.look.priest_armor.as_str(), c.look.priest_weapon.as_str()),
            ("pilgrim", "mace")
        );
        assert_eq!(c.max_hp(), 100. + 3. * 20.);
        assert_eq!(c.stats().0, 20. + 4. * 4. + 4.);
        assert!(Class::Priest.reach() > Class::Assassin.reach());
    }
}
