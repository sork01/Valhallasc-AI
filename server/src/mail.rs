//! Persisted, authoritative mail escrow. See docs/mailboxes.md.
use crate::items::{GM_RARITY, GearInstance, is_gear, is_quest_item, item};
use crate::model::Character;
use crate::store::{Store, name_key, unix_now};
use rusqlite::{OptionalExtension, params};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::BTreeSet;

pub const RANGE: f64 = 2.8;
pub const INBOX_LIMIT: u32 = 100;
pub const HOURLY_LIMIT: u32 = 30;
pub const ATTACHMENT_LIMIT: usize = 6;
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Attachment {
    pub item: String,
    pub quantity: u32,
    #[serde(default)]
    pub copy: Option<u64>,
}
#[derive(Debug, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case")]
pub enum Request {
    Open,
    Lookup {
        name: String,
    },
    Send {
        request: String,
        recipient: String,
        subject: String,
        body: String,
        gold: u32,
        attachments: Vec<Attachment>,
    },
    Read {
        id: i64,
    },
    Collect {
        id: i64,
    },
    Delete {
        id: i64,
    },
    Return {
        id: i64,
    },
}
#[derive(Clone, Debug, Default, Deserialize, Serialize)]
struct Contents {
    gold: u32,
    items: Vec<Attachment>,
    gear: Vec<GearInstance>,
}
impl Contents {
    fn pending(&self) -> bool {
        self.gold > 0 || !self.items.is_empty()
    }
}
fn storage(_: impl std::fmt::Display) -> String {
    "Mail could not be saved. Nothing was moved.".into()
}
pub fn ineligible(id: &str) -> Option<&'static str> {
    let Some(i) = item(id) else {
        return Some("Unknown item.");
    };
    if is_gear(i) && i.class.is_some() {
        return Some("Bound class gear cannot be mailed.");
    }
    if i.starter || i.rarity == GM_RARITY || i.kind == "mount_licence" {
        return Some("Starter gear, game master gear and mount licences cannot be mailed.");
    }
    if is_quest_item(i) {
        return Some("Quest items cannot be mailed.");
    }
    None
}
fn choices(c: &Character) -> Vec<Value> {
    let mut result = vec![];
    for stack in &c.inventory {
        let Some(i) = item(&stack.item) else {
            continue;
        };
        let worn = c.equipped_count(i);
        if is_gear(i) {
            for (index, g) in c
                .gear_instances
                .iter()
                .filter(|g| g.item == i.id)
                .enumerate()
            {
                let reason = if index < worn as usize {
                    Some("Worn pieces cannot be mailed.")
                } else {
                    ineligible(&i.id)
                };
                result.push(json!({"item":i.id,"quantity":1,"copy":g.id,"gear":g,"reason":reason}));
            }
        } else {
            result.push(json!({"item":i.id,"quantity":stack.quantity.saturating_sub(worn),"reason":ineligible(&i.id)}));
        }
    }
    result
}
fn take(c: &mut Character, gold: u32, attachments: &[Attachment]) -> Result<Contents, String> {
    if attachments.len() > ATTACHMENT_LIMIT {
        return Err("A letter can carry up to six attachments.".into());
    }
    c.gold = c
        .gold
        .checked_sub(gold)
        .ok_or("You do not have that much gold.")?;
    c.materialize_gear_instances();
    let mut contents = Contents {
        gold,
        ..Default::default()
    };
    let mut seen = BTreeSet::new();
    let mut copied = BTreeSet::new();
    for a in attachments {
        if let Some(reason) = ineligible(&a.item) {
            return Err(reason.into());
        }
        let i = item(&a.item).ok_or("Unknown item.")?;
        if a.quantity == 0 || !seen.insert((&a.item, a.copy)) {
            return Err("Choose each attachment once with a positive quantity.".into());
        }
        if c.quantity(&a.item).saturating_sub(c.equipped_count(i)) < a.quantity {
            return Err("You cannot mail items you do not own or have equipped.".into());
        }
        if is_gear(i) {
            if a.quantity != 1 {
                return Err("Choose one specific gear copy per attachment.".into());
            }
            let copy = a
                .copy
                .ok_or("Choose one specific gear copy per attachment.")?;
            if !copied.insert(copy) {
                return Err("Choose each attachment once with a positive quantity.".into());
            }
            let g = c
                .gear_instances
                .iter()
                .filter(|g| g.item == a.item)
                .skip(c.equipped_count(i) as usize)
                .find(|g| g.id == copy)
                .ok_or("That gear copy is not available to mail.")?
                .clone();
            contents.gear.push(g);
            c.gear_instances.retain(|g| g.id != copy);
        } else if a.copy.is_some() {
            return Err("Only gear comes in separate copies.".into());
        }
        if !c.consume_item(&a.item, a.quantity) {
            return Err("That attachment is no longer available.".into());
        }
        contents.items.push(a.clone());
    }
    Ok(contents)
}
fn receive(c: &mut Character, contents: &Contents) -> Result<(), String> {
    c.gold = c
        .gold
        .checked_add(contents.gold)
        .ok_or("You cannot carry that much gold.")?;
    c.materialize_gear_instances();
    for a in &contents.items {
        if item(&a.item).is_none() {
            return Err("An attachment is unavailable. Keep this letter for later.".into());
        }
        c.quantity(&a.item)
            .checked_add(a.quantity)
            .ok_or("That stack is too large for your bags.")?;
        c.add_item(&a.item, a.quantity);
    }
    for g in &contents.gear {
        let mut g = g.clone();
        g.id = c.next_gear_id;
        c.next_gear_id = c
            .next_gear_id
            .checked_add(1)
            .ok_or("That gear copy cannot be collected yet.")?;
        g.clear_trade_window();
        c.gear_instances.push(g);
    }
    if c.bag_used() > c.bag_capacity() {
        return Err("Your bags are full. Make room first.".into());
    }
    Ok(())
}
impl Store {
    pub fn mail_unread(&self, id: &str) -> rusqlite::Result<u32> {
        self.conn().query_row(
            "SELECT count(*) FROM mail WHERE recipient=?1 AND deleted=0 AND is_read=0",
            [id],
            |r| r.get(0),
        )
    }
    pub fn mail(
        &self,
        current: &Character,
        request: Request,
    ) -> Result<(Character, Value), String> {
        let mut db = self.conn();
        let tx = db.transaction().map_err(storage)?;
        let mut c = current.clone();
        c.materialize_gear_instances();
        let mut notice = "";
        let mut found = Value::Null;
        let mut sent = Value::Null;
        match request {
            Request::Open => {}
            Request::Lookup { name } => {
                let name: Option<String> = tx.query_row("SELECT json_extract(state,'$.look.name') FROM characters WHERE name_key=?1 AND rename_required=0 AND id<>?2", params![name_key(&name), c.id], |r| r.get(0)).optional().map_err(storage)?;
                found = json!(name.ok_or("No other character has that name.")?);
            }
            Request::Send {
                request,
                recipient,
                subject,
                body,
                gold,
                attachments,
            } => {
                if !(16..=80).contains(&request.len())
                    || !request
                        .bytes()
                        .all(|b| b.is_ascii_alphanumeric() || b == b'-')
                {
                    return Err("The letter needs a valid send receipt. Reopen compose.".into());
                }
                let previous: Option<i64> = tx
                    .query_row(
                        "SELECT id FROM mail WHERE sender=?1 AND request=?2",
                        params![c.id, request],
                        |r| r.get(0),
                    )
                    .optional()
                    .map_err(storage)?;
                if let Some(id) = previous {
                    sent = json!(id);
                    notice = "Letter already sent.";
                } else {
                    let subject = subject.trim();
                    if subject.is_empty()
                        || subject.chars().count() > 80
                        || body.chars().count() > 2000
                        || subject.chars().any(char::is_control)
                        || body
                            .chars()
                            .any(|ch| ch.is_control() && ch != '\n' && ch != '\t')
                    {
                        return Err("Use a subject of 1 to 80 characters and a message up to 2000 characters.".into());
                    }
                    let recipient: Option<(String,String)> = tx.query_row("SELECT id,json_extract(state,'$.look.name') FROM characters WHERE name_key=?1 AND rename_required=0 AND id<>?2", params![name_key(&recipient),c.id], |r| Ok((r.get(0)?,r.get(1)?))).optional().map_err(storage)?;
                    let (to, to_name) = recipient.ok_or("No other character has that name.")?;
                    let count: u32 = tx
                        .query_row(
                            "SELECT count(*) FROM mail WHERE recipient=?1 AND deleted=0",
                            [&to],
                            |r| r.get(0),
                        )
                        .map_err(storage)?;
                    if count >= INBOX_LIMIT {
                        return Err("That mailbox is full. Try again later.".into());
                    }
                    let count: u32 = tx
                        .query_row(
                            "SELECT count(*) FROM mail WHERE sender=?1 AND created>?2",
                            params![c.id, unix_now() - 3600],
                            |r| r.get(0),
                        )
                        .map_err(storage)?;
                    if count >= HOURLY_LIMIT {
                        return Err("You can send up to thirty letters per hour.".into());
                    }
                    let contents = take(&mut c, gold, &attachments)?;
                    tx.execute("INSERT INTO mail(sender,recipient,sender_name,recipient_name,request,subject,body,contents,created) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9)",params![c.id,to,c.look.name,to_name,request,subject,body,serde_json::to_string(&contents).map_err(storage)?,unix_now()]).map_err(storage)?;
                    sent = json!(tx.last_insert_rowid());
                    notice = "Letter sent.";
                }
            }
            action => {
                let id = match &action {
                    Request::Read { id }
                    | Request::Collect { id }
                    | Request::Delete { id }
                    | Request::Return { id } => *id,
                    _ => unreachable!(),
                };
                let row: Option<(String,String,bool,String)> = tx.query_row("SELECT contents,sender,returned,sender_name FROM mail WHERE id=?1 AND recipient=?2 AND deleted=0", params![id,c.id], |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional().map_err(storage)?;
                let (contents, sender, returned, sender_name) =
                    row.ok_or("That letter is no longer in your inbox.")?;
                let contents: Contents = serde_json::from_str(&contents).map_err(storage)?;
                match action {
                    Request::Read { .. } => {
                        tx.execute("UPDATE mail SET is_read=1 WHERE id=?1", [id])
                            .map_err(storage)?;
                    }
                    Request::Collect { .. } => {
                        receive(&mut c, &contents)?;
                        tx.execute(
                            "UPDATE mail SET contents=?1,is_read=1 WHERE id=?2",
                            params![
                                serde_json::to_string(&Contents::default()).map_err(storage)?,
                                id
                            ],
                        )
                        .map_err(storage)?;
                        notice = "Attachments collected.";
                    }
                    Request::Delete { .. } => {
                        if contents.pending() {
                            return Err(
                                "Collect or return the attachments before deleting this letter."
                                    .into(),
                            );
                        }
                        tx.execute(
                            "UPDATE mail SET deleted=1,subject='',body='' WHERE id=?1",
                            [id],
                        )
                        .map_err(storage)?;
                        notice = "Letter deleted.";
                    }
                    Request::Return { .. } => {
                        if returned || !contents.pending() {
                            return Err(
                                "Only an uncollected original letter can be returned.".into()
                            );
                        }
                        let exists: bool = tx
                            .query_row(
                                "SELECT EXISTS(SELECT 1 FROM characters WHERE id=?1)",
                                [&sender],
                                |r| r.get(0),
                            )
                            .map_err(storage)?;
                        if !exists {
                            return Err(
                                "The sender is unavailable. You can still collect this letter."
                                    .into(),
                            );
                        }
                        // Keep original sender/request for the permanent send receipt, swap only the delivery target.
                        tx.execute("UPDATE mail SET recipient=?1,recipient_name=?2,is_read=0,returned=1 WHERE id=?3",params![sender,sender_name,id]).map_err(storage)?;
                        notice = "Letter returned.";
                    }
                    _ => unreachable!(),
                }
            }
        }
        // The character and escrow share the same commit. Never acknowledge a partial save.
        if tx
            .execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![serde_json::to_string(&c).map_err(storage)?, c.id],
            )
            .map_err(storage)?
            != 1
        {
            return Err("The character is unavailable. Nothing was moved.".into());
        }
        let letters: Vec<Value> = tx.prepare("SELECT id,sender_name,recipient_name,subject,body,contents,created,is_read,returned FROM mail WHERE recipient=?1 AND deleted=0 ORDER BY id DESC").map_err(storage)?
            .query_map([&c.id], |r| Ok(json!({"id":r.get::<_,i64>(0)?,"sender":r.get::<_,String>(1)?,"recipient":r.get::<_,String>(2)?,"subject":r.get::<_,String>(3)?,"body":r.get::<_,String>(4)?,"contents":serde_json::from_str::<Value>(&r.get::<_,String>(5)?).unwrap_or(Value::Null),"created":r.get::<_,i64>(6)?,"read":r.get::<_,bool>(7)?,"returned":r.get::<_,bool>(8)?}))).map_err(storage)?.collect::<Result<_,_>>().map_err(storage)?;
        tx.commit().map_err(storage)?;
        let packet = json!({"type":"mail","ok":true,"notice":notice,"letters":letters,"found":found,"sent":sent,"choices":choices(&c),"gold":c.gold,"inventory":c.inventory,"gearInstances":c.gear_instances,"equipment":c.equipment,"bags":c.bags,"bagCapacity":c.bag_capacity()});
        Ok((c, packet))
    }
}

#[cfg(test)]
#[path = "mail_tests.rs"]
mod tests;
