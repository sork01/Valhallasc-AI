use crate::model::{Character, Class, Look, Point};
use rusqlite::{Connection, OptionalExtension, params};
use sha2::{Digest, Sha256};
use std::sync::{Arc, Mutex, MutexGuard};
use uuid::Uuid;

/// One SQLite connection shared by the world loop (saves) and the account API (logins), so an in-memory database in
/// tests sees both. Every call holds the lock only for its own statements.
#[derive(Clone)]
pub struct Store {
    db: Arc<Mutex<Connection>>,
}
/// What a friends list shows about a character who is offline.
pub struct Summary {
    pub name: String,
    pub class: Class,
    pub level: u32,
}
impl Store {
    pub fn open(path: &std::path::Path) -> Result<Self, Box<dyn std::error::Error>> {
        if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
            std::fs::create_dir_all(parent)?;
        }
        let db = Connection::open(path)?;
        db.busy_timeout(std::time::Duration::from_secs(2))?;
        db.execute_batch("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
            CREATE TABLE IF NOT EXISTS characters (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, state TEXT NOT NULL);")?;
        // Characters saved before accounts existed have no owner.
        let owned = db
            .prepare("PRAGMA table_info(characters)")?
            .query_map([], |r| r.get::<_, String>(1))?
            .any(|name| name.is_ok_and(|n| n == "account_id"));
        if !owned {
            db.execute_batch("ALTER TABLE characters ADD COLUMN account_id TEXT;")?;
        }
        db.execute_batch(
            "CREATE INDEX IF NOT EXISTS characters_account ON characters(account_id);
            CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, kind TEXT NOT NULL, username TEXT NOT NULL,
                display TEXT NOT NULL, pw_hash TEXT, created INTEGER NOT NULL, UNIQUE(kind, username));
            CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL, expires INTEGER NOT NULL);",
        )?;
        Ok(Self {
            db: Arc::new(Mutex::new(db)),
        })
    }
    pub(crate) fn conn(&self) -> MutexGuard<'_, Connection> {
        self.db.lock().unwrap_or_else(|e| e.into_inner())
    }
    pub fn load(&self, token: &str) -> Result<Option<Character>, Box<dyn std::error::Error>> {
        if token.len() != 64 || !token.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Ok(None);
        }
        let state: Option<String> = self
            .conn()
            .query_row(
                "SELECT state FROM characters WHERE token_hash=?1 AND account_id IS NULL",
                [hash(token)],
                |r| r.get(0),
            )
            .optional()?;
        state.map(|s| decode(&s)).transpose()
    }
    /// A character owned by `account`. An account's characters have no resumable key; its login session is the credential.
    pub fn load_for_account(
        &self,
        account: &str,
        character: &str,
    ) -> Result<Option<Character>, Box<dyn std::error::Error>> {
        let state: Option<String> = self
            .conn()
            .query_row(
                "SELECT state FROM characters WHERE id=?1 AND account_id=?2",
                [character, account],
                |r| r.get(0),
            )
            .optional()?;
        state.map(|s| decode(&s)).transpose()
    }
    pub fn create(
        &self,
        look: Look,
        spawn: Point,
    ) -> Result<(Character, String), Box<dyn std::error::Error>> {
        self.create_for(None, look, spawn)
    }
    /// With `account` the character belongs to that account and the returned key is never issued to anyone.
    pub fn create_for(
        &self,
        account: Option<&str>,
        mut look: Look,
        spawn: Point,
    ) -> Result<(Character, String), Box<dyn std::error::Error>> {
        let token = random_key();
        // Appearance is client-selected; starter equipment and ownership are server-issued.
        let defaults = Look::default();
        look.warrior_armor = defaults.warrior_armor;
        look.warrior_weapon = defaults.warrior_weapon;
        look.mage_armor = defaults.mage_armor;
        look.mage_weapon = defaults.mage_weapon;
        look.assassin_armor = defaults.assassin_armor;
        look.assassin_weapon = defaults.assassin_weapon;
        look.priest_armor = defaults.priest_armor;
        look.priest_weapon = defaults.priest_weapon;
        look.hunter_armor = defaults.hunter_armor;
        look.hunter_weapon = defaults.hunter_weapon;
        look.head = defaults.head;
        look.shoulders = defaults.shoulders;
        look.gloves = defaults.gloves;
        look.pants = defaults.pants;
        look.necklace = defaults.necklace;
        look.accessory = defaults.accessory;
        let mut c = Character {
            id: Uuid::new_v4().to_string(),
            hp: look.class.health(),
            look,
            x: spawn.x,
            y: spawn.y,
            level: 1,
            xp: 0,
            gold: 0,
            kills: 0,
            quests: vec![],
            inventory: vec![],
            equipment: Default::default(),
            bags: vec![],
            attributes: Default::default(),
            zone: 0,
            friends: vec![],
            potion_ready: 0,
        };
        c.seed_inventory();
        self.conn().execute(
            "INSERT INTO characters(id,token_hash,state,account_id) VALUES(?1,?2,?3,?4)",
            params![c.id, hash(&token), serde_json::to_string(&c)?, account],
        )?;
        Ok((c, token))
    }
    pub fn summary(&self, id: &str) -> Option<Summary> {
        let state: String = self
            .conn()
            .query_row("SELECT state FROM characters WHERE id=?1", [id], |r| {
                r.get(0)
            })
            .optional()
            .ok()??;
        let v: serde_json::Value = serde_json::from_str(&state).ok()?;
        Some(Summary {
            name: v["look"]["name"].as_str()?.to_owned(),
            class: serde_json::from_value(v["look"]["class"].clone()).unwrap_or_default(),
            level: v["level"].as_u64().unwrap_or(1) as u32,
        })
    }
    /// Drops `friend` from an offline character's list. Only the `friends` field is edited in the stored JSON, so a
    /// legacy save keeps every field (such as a missing `inventory`) that load() migrates.
    pub fn remove_friend(&self, id: &str, friend: &str) -> Result<(), Box<dyn std::error::Error>> {
        let state: Option<String> = self
            .conn()
            .query_row("SELECT state FROM characters WHERE id=?1", [id], |r| {
                r.get(0)
            })
            .optional()?;
        let Some(state) = state else {
            return Ok(());
        };
        let mut v: serde_json::Value = serde_json::from_str(&state)?;
        if let Some(list) = v.get_mut("friends").and_then(|f| f.as_array_mut()) {
            list.retain(|f| f.as_str() != Some(friend));
            self.conn().execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![v.to_string(), id],
            )?;
        }
        Ok(())
    }
    pub fn save_many<'a>(
        &mut self,
        characters: impl Iterator<Item = &'a Character>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let mut db = self.conn();
        let tx = db.transaction()?;
        for c in characters {
            tx.execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![serde_json::to_string(c)?, c.id],
            )?;
        }
        tx.commit()?;
        Ok(())
    }

    // ---------- accounts ----------
    /// A new game account. `Ok(None)` when the name is taken (names compare without case).
    pub fn create_account(
        &self,
        username: &str,
        pw_hash: &str,
    ) -> Result<Option<Account>, Box<dyn std::error::Error>> {
        let id = Uuid::new_v4().to_string();
        let inserted = self.conn().execute(
            "INSERT OR IGNORE INTO accounts(id,kind,username,display,pw_hash,created) VALUES(?1,'game',?2,?3,?4,?5)",
            params![id, username.to_lowercase(), username, pw_hash, unix_now()],
        )?;
        Ok((inserted == 1).then(|| Account {
            id,
            kind: AccountKind::Game,
            name: username.to_owned(),
        }))
    }
    /// A game account and its password hash, for checking a login.
    pub fn game_account(
        &self,
        username: &str,
    ) -> Result<Option<(Account, String)>, Box<dyn std::error::Error>> {
        Ok(self
            .conn()
            .query_row(
                "SELECT id,display,pw_hash FROM accounts WHERE kind='game' AND username=?1",
                [username.to_lowercase()],
                |r| {
                    Ok((
                        Account {
                            id: r.get(0)?,
                            kind: AccountKind::Game,
                            name: r.get(1)?,
                        },
                        r.get::<_, Option<String>>(2)?.unwrap_or_default(),
                    ))
                },
            )
            .optional()?)
    }
    /// The account for a site SSO user, created on first use. It has no password here.
    pub fn sso_account(&self, username: &str) -> Result<Account, Box<dyn std::error::Error>> {
        let conn = self.conn();
        conn.execute(
            "INSERT OR IGNORE INTO accounts(id,kind,username,display,pw_hash,created) VALUES(?1,'sso',?2,?3,NULL,?4)",
            params![Uuid::new_v4().to_string(), username.to_lowercase(), username, unix_now()],
        )?;
        Ok(conn.query_row(
            "SELECT id,display FROM accounts WHERE kind='sso' AND username=?1",
            [username.to_lowercase()],
            |r| {
                Ok(Account {
                    id: r.get(0)?,
                    kind: AccountKind::Sso,
                    name: r.get(1)?,
                })
            },
        )?)
    }
    /// Issues a login session; only its hash is stored.
    pub fn new_session(&self, account: &str) -> Result<String, Box<dyn std::error::Error>> {
        let token = random_key();
        let conn = self.conn();
        conn.execute("DELETE FROM sessions WHERE expires<?1", [unix_now()])?;
        conn.execute(
            "INSERT INTO sessions(token_hash,account_id,expires) VALUES(?1,?2,?3)",
            params![hash(&token), account, unix_now() + SESSION_SECS],
        )?;
        Ok(token)
    }
    /// The account behind a live session. Using a session more than a day old renews it for another 30 days.
    pub fn session_account(
        &self,
        token: &str,
    ) -> Result<Option<Account>, Box<dyn std::error::Error>> {
        if token.len() != 64 || !token.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Ok(None);
        }
        let conn = self.conn();
        let now = unix_now();
        let found = conn
            .query_row(
                "SELECT a.id,a.kind,a.display,s.expires FROM sessions s JOIN accounts a ON a.id=s.account_id
                 WHERE s.token_hash=?1 AND s.expires>?2",
                params![hash(token), now],
                |r| {
                    Ok((
                        Account {
                            id: r.get(0)?,
                            kind: if r.get::<_, String>(1)? == "sso" {
                                AccountKind::Sso
                            } else {
                                AccountKind::Game
                            },
                            name: r.get(2)?,
                        },
                        r.get::<_, i64>(3)?,
                    ))
                },
            )
            .optional()?;
        let Some((account, expires)) = found else {
            return Ok(None);
        };
        if expires < now + SESSION_SECS - 86_400 {
            conn.execute(
                "UPDATE sessions SET expires=?1 WHERE token_hash=?2",
                params![now + SESSION_SECS, hash(token)],
            )?;
        }
        Ok(Some(account))
    }
    pub fn end_session(&self, token: &str) -> Result<(), Box<dyn std::error::Error>> {
        self.conn()
            .execute("DELETE FROM sessions WHERE token_hash=?1", [hash(token)])?;
        Ok(())
    }
    /// An account's characters, oldest first, as the character picker shows them.
    pub fn account_characters(
        &self,
        account: &str,
    ) -> Result<Vec<CharacterEntry>, Box<dyn std::error::Error>> {
        let conn = self.conn();
        let mut query =
            conn.prepare("SELECT id,state FROM characters WHERE account_id=?1 ORDER BY rowid")?;
        let rows = query.query_map([account], |r| {
            Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?))
        })?;
        let mut list = vec![];
        for row in rows {
            let (id, state) = row?;
            let v: serde_json::Value = serde_json::from_str(&state)?;
            list.push(CharacterEntry {
                id,
                look: v["look"].clone(),
                level: v["level"].as_u64().unwrap_or(1) as u32,
            });
        }
        Ok(list)
    }
    pub fn account_character_count(
        &self,
        account: &str,
    ) -> Result<usize, Box<dyn std::error::Error>> {
        Ok(self.conn().query_row(
            "SELECT COUNT(*) FROM characters WHERE account_id=?1",
            [account],
            |r| r.get::<_, i64>(0),
        )? as usize)
    }
    /// Permanently deletes one of the account's characters. False when it isn't theirs.
    pub fn delete_account_character(
        &self,
        account: &str,
        character: &str,
    ) -> Result<bool, Box<dyn std::error::Error>> {
        Ok(self.conn().execute(
            "DELETE FROM characters WHERE id=?1 AND account_id=?2",
            [character, account],
        )? == 1)
    }
}
/// A login session lasts 30 days from its last use.
const SESSION_SECS: i64 = 30 * 86_400;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AccountKind {
    Game,
    Sso,
}
#[derive(Clone, Debug)]
pub struct Account {
    pub id: String,
    pub kind: AccountKind,
    pub name: String,
}
pub struct CharacterEntry {
    pub id: String,
    pub look: serde_json::Value,
    pub level: u32,
}
pub(crate) fn unix_now() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_secs() as i64)
}
fn random_key() -> String {
    format!("{}{}", Uuid::new_v4().simple(), Uuid::new_v4().simple())
}
/// Reads a stored character, migrating saves from before inventory and bags existed.
fn decode(state: &str) -> Result<Character, Box<dyn std::error::Error>> {
    let value: serde_json::Value = serde_json::from_str(state)?;
    let legacy = value.get("inventory").is_none();
    let legacy_bags = value.get("bags").is_none();
    let mut character: Character = serde_json::from_value(value)?;
    if legacy {
        character.seed_inventory();
    }
    if legacy_bags {
        while character.bag_used() > character.bag_capacity() && character.bags.len() < 4 {
            character.bags.push("traveler_pack".into());
        }
    }
    // Catalog growth (new starter pieces) and the look layers reach existing saves here.
    character.grant_missing_starters();
    character.sync_look();
    Ok(character)
}
fn hash(token: &str) -> String {
    format!("{:x}", Sha256::digest(token.as_bytes()))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn gender_is_kept_through_create_save_and_load() {
        let mut s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let look = Look {
            class: Class::Hunter,
            gender: crate::model::Gender::Female,
            ..Look::default()
        };
        let (mut c, token) = s.create(look, Point::default()).unwrap();
        assert_eq!(c.look.gender, crate::model::Gender::Female);
        c.gold = 5;
        s.save_many([&c].into_iter()).unwrap();
        let loaded = s.load(&token).unwrap().unwrap();
        assert_eq!(loaded.look.gender, crate::model::Gender::Female);
        assert_eq!(loaded.look.class, Class::Hunter);
        let (plain, _) = s.create(Look::default(), Point::default()).unwrap();
        assert_eq!(plain.look.gender, crate::model::Gender::Male);
    }
    #[test]
    fn persistence_and_invalid_keys() {
        let mut s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (mut c, token) = s.create(Look::default(), Point { x: 36., y: 60. }).unwrap();
        c.gold = 81;
        c.level = 20;
        c.look.equip("azure", "royal").unwrap();
        c.add_item("warrior_armor_azure", 1);
        c.add_item("warrior_weapon_royal", 1);
        c.add_item("mage_weapon_crystal", 2);
        c.add_item("slime_gel", 7);
        c.purchase_bag("adventurer_satchel", 24).unwrap();
        c.add_item("necklace_upgrade", 1);
        c.equip_slots(&[("necklace".into(), "necklace_upgrade".into())].into())
            .unwrap();
        c.quests.push(crate::model::QuestProgress {
            id: "welcome".into(),
            counts: vec![1, 0, 1],
            claimed: false,
            completions: 0,
        });
        s.save_many(std::iter::once(&c)).unwrap();
        let restored = s.load(&token).unwrap().unwrap();
        assert_eq!(restored.gold, 57);
        assert_eq!(restored.look.warrior_weapon, "royal");
        assert_eq!(restored.quests[0].counts, vec![1, 0, 1]);
        assert_eq!(restored.inventory, c.inventory);
        assert_eq!(restored.equipment, c.equipment);
        assert_eq!(restored.bags, c.bags);
        assert_eq!(restored.stats(), c.stats());
        assert!(s.load(&"a".repeat(64)).unwrap().is_none());
        assert!(s.load("anything").unwrap().is_none());
        let stored: String = s
            .conn()
            .query_row("SELECT token_hash FROM characters", [], |r| r.get(0))
            .unwrap();
        assert_ne!(stored, token);
    }

    #[test]
    fn old_characters_receive_points_for_existing_levels_once() {
        let mut s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (mut c, token) = s.create(Look::default(), Point::default()).unwrap();
        c.grant_xp(300);
        let mut old = serde_json::to_value(&c).unwrap();
        old.as_object_mut().unwrap().remove("attributes");
        s.conn()
            .execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![old.to_string(), c.id],
            )
            .unwrap();
        let mut restored = s.load(&token).unwrap().unwrap();
        assert_eq!(restored.stat_points(), 6);
        restored.allocate_stat("dexterity").unwrap();
        restored.allocate_stat("accuracy").unwrap();
        s.save_many(std::iter::once(&restored)).unwrap();
        let resumed = s.load(&token).unwrap().unwrap();
        assert_eq!(resumed.stat_points(), 4);
        assert_eq!(resumed.attributes.dexterity, 1);
        assert_eq!(resumed.attributes.accuracy, 1);
    }
    #[test]
    fn existing_characters_without_quests_still_resume() {
        let s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (c, token) = s.create(Look::default(), Point::default()).unwrap();
        let mut old = serde_json::to_value(&c).unwrap();
        old.as_object_mut().unwrap().remove("quests");
        old.as_object_mut().unwrap().remove("equipment");
        s.conn()
            .execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![old.to_string(), c.id],
            )
            .unwrap();
        assert!(s.load(&token).unwrap().unwrap().quests.is_empty());
        assert!(s.load(&token).unwrap().unwrap().equipment.is_empty());
    }
    #[test]
    fn characters_saved_before_friends_resume_with_none_and_keep_friends_after() {
        let mut s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (mut c, token) = s.create(Look::default(), Point::default()).unwrap();
        let mut old = serde_json::to_value(&c).unwrap();
        old.as_object_mut().unwrap().remove("friends");
        s.conn()
            .execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![old.to_string(), c.id],
            )
            .unwrap();
        assert!(s.load(&token).unwrap().unwrap().friends.is_empty());
        // Removing a friend from a save that never had the field changes nothing, and stays loadable.
        s.remove_friend(&c.id, "someone").unwrap();
        assert!(s.load(&token).unwrap().unwrap().friends.is_empty());
        c.friends = vec!["a".into(), "b".into()];
        s.save_many(std::iter::once(&c)).unwrap();
        assert_eq!(s.load(&token).unwrap().unwrap().friends, ["a", "b"]);
        s.remove_friend(&c.id, "a").unwrap();
        assert_eq!(s.load(&token).unwrap().unwrap().friends, ["b"]);
        s.remove_friend("no-such-character", "b").unwrap();
        let summary = s.summary(&c.id).unwrap();
        assert_eq!((summary.name.as_str(), summary.level), ("Adventurer", 1));
        assert!(s.summary("no-such-character").is_none());
    }
    #[test]
    fn characters_saved_before_zones_resume_in_the_meadow_and_keep_their_zone_after() {
        let s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (mut c, token) = s.create(Look::default(), Point::default()).unwrap();
        let mut old = serde_json::to_value(&c).unwrap();
        old.as_object_mut().unwrap().remove("zone");
        s.conn()
            .execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![old.to_string(), c.id],
            )
            .unwrap();
        assert_eq!(s.load(&token).unwrap().unwrap().zone, 0);
        c.zone = 1;
        let mut s = s;
        s.save_many(std::iter::once(&c)).unwrap();
        assert_eq!(s.load(&token).unwrap().unwrap().zone, 1);
    }
    #[test]
    fn unlimited_inventory_migration_preserves_every_item_and_grants_only_needed_bags() {
        let mut s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (mut c, token) = s.create(Look::default(), Point::default()).unwrap();
        // One item in eight of the catalog (it holds hundreds of pieces): still more than the backpack holds.
        for i in crate::items::ITEMS
            .iter()
            .filter(|i| i.kind != "bag")
            .step_by(8)
        {
            c.add_item(&i.id, 1);
        }
        let mut old = serde_json::to_value(&c).unwrap();
        old.as_object_mut().unwrap().remove("bags");
        s.conn()
            .execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![old.to_string(), c.id],
            )
            .unwrap();
        let restored = s.load(&token).unwrap().unwrap();
        assert_eq!(restored.inventory, c.inventory);
        // Every item fits, with no bag to spare: dropping the last one would overflow.
        assert!(!restored.bags.is_empty() && restored.bags.iter().all(|b| b == "traveler_pack"));
        assert!(restored.bag_used() <= restored.bag_capacity());
        let mut fewer = restored.clone();
        fewer.bags.pop();
        assert!(fewer.bag_used() > fewer.bag_capacity());
        s.save_many(std::iter::once(&restored)).unwrap();
        assert_eq!(s.load(&token).unwrap().unwrap().bags, restored.bags);
    }

    #[test]
    fn legacy_gear_is_migrated_once_and_new_characters_cannot_request_upgrades() {
        let mut s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let look = Look {
            warrior_armor: "azure".into(),
            warrior_weapon: "royal".into(),
            ..Look::default()
        };
        let (mut c, token) = s.create(look, Point::default()).unwrap();
        assert_eq!(c.look.warrior_weapon, "sword");
        assert_eq!(c.quantity("warrior_weapon_royal"), 0);
        c.look.equip("azure", "royal").unwrap();
        let mut old = serde_json::to_value(&c).unwrap();
        old.as_object_mut().unwrap().remove("inventory");
        s.conn()
            .execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![old.to_string(), c.id],
            )
            .unwrap();
        let mut restored = s.load(&token).unwrap().unwrap();
        assert_eq!(restored.quantity("warrior_weapon_royal"), 1);
        assert_eq!(restored.quantity("warrior_armor_azure"), 1);
        restored.equip_owned("crimson", "sword").unwrap();
        restored.sell_item("warrior_weapon_royal", 1).unwrap();
        s.save_many(std::iter::once(&restored)).unwrap();
        assert_eq!(
            s.load(&token)
                .unwrap()
                .unwrap()
                .quantity("warrior_weapon_royal"),
            0
        );
    }
}
