use crate::model::{Character, Class, Look, Point};
use rusqlite::{Connection, OptionalExtension, params};
use sha2::{Digest, Sha256};
use uuid::Uuid;

pub struct Store {
    db: Connection,
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
        Ok(Self { db })
    }
    pub fn load(&self, token: &str) -> Result<Option<Character>, Box<dyn std::error::Error>> {
        if token.len() != 64 || !token.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Ok(None);
        }
        let state: Option<String> = self
            .db
            .query_row(
                "SELECT state FROM characters WHERE token_hash=?1",
                [hash(token)],
                |r| r.get(0),
            )
            .optional()?;
        state
            .map(|s| {
                let value: serde_json::Value = serde_json::from_str(&s)?;
                let legacy = value.get("inventory").is_none();
                let legacy_bags = value.get("bags").is_none();
                let mut character: Character = serde_json::from_value(value)?;
                if legacy {
                    character.seed_inventory();
                }
                if legacy_bags {
                    while character.bag_used() > character.bag_capacity()
                        && character.bags.len() < 4
                    {
                        character.bags.push("traveler_pack".into());
                    }
                }
                Ok(character)
            })
            .transpose()
    }
    pub fn create(
        &self,
        mut look: Look,
        spawn: Point,
    ) -> Result<(Character, String), Box<dyn std::error::Error>> {
        // A bearer key resumes a guest character, not an account/password login.
        let token = format!("{}{}", Uuid::new_v4().simple(), Uuid::new_v4().simple());
        // Appearance is client-selected; starter equipment and ownership are server-issued.
        let defaults = Look::default();
        look.warrior_armor = defaults.warrior_armor;
        look.warrior_weapon = defaults.warrior_weapon;
        look.mage_armor = defaults.mage_armor;
        look.mage_weapon = defaults.mage_weapon;
        look.assassin_armor = defaults.assassin_armor;
        look.assassin_weapon = defaults.assassin_weapon;
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
        self.db.execute(
            "INSERT INTO characters(id,token_hash,state) VALUES(?1,?2,?3)",
            params![c.id, hash(&token), serde_json::to_string(&c)?],
        )?;
        Ok((c, token))
    }
    pub fn summary(&self, id: &str) -> Option<Summary> {
        let state: String = self
            .db
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
            .db
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
            self.db.execute(
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
        let tx = self.db.transaction()?;
        for c in characters {
            tx.execute(
                "UPDATE characters SET state=?1 WHERE id=?2",
                params![serde_json::to_string(c)?, c.id],
            )?;
        }
        tx.commit()?;
        Ok(())
    }
}
fn hash(token: &str) -> String {
    format!("{:x}", Sha256::digest(token.as_bytes()))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn persistence_and_invalid_keys() {
        let mut s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (mut c, token) = s.create(Look::default(), Point { x: 36., y: 60. }).unwrap();
        c.gold = 81;
        c.level = 3;
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
        let stored: String =
            s.db.query_row("SELECT token_hash FROM characters", [], |r| r.get(0))
                .unwrap();
        assert_ne!(stored, token);
    }

    #[test]
    fn old_characters_receive_points_for_existing_levels_once() {
        let mut s = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (mut c, token) = s.create(Look::default(), Point::default()).unwrap();
        c.grant_xp(568);
        let mut old = serde_json::to_value(&c).unwrap();
        old.as_object_mut().unwrap().remove("attributes");
        s.db.execute(
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
        s.db.execute(
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
        s.db.execute(
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
        s.db.execute(
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
        for i in crate::items::ITEMS.iter().filter(|i| i.kind != "bag") {
            c.add_item(&i.id, 1);
        }
        let mut old = serde_json::to_value(&c).unwrap();
        old.as_object_mut().unwrap().remove("bags");
        s.db.execute(
            "UPDATE characters SET state=?1 WHERE id=?2",
            params![old.to_string(), c.id],
        )
        .unwrap();
        let restored = s.load(&token).unwrap().unwrap();
        assert_eq!(restored.inventory, c.inventory);
        assert_eq!(restored.bags, vec!["traveler_pack"]);
        assert!(restored.bag_used() <= restored.bag_capacity());
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
        s.db.execute(
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
