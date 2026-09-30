use crate::model::{Character, Look, Point};
use rusqlite::{Connection, OptionalExtension, params};
use sha2::{Digest, Sha256};
use uuid::Uuid;

pub struct Store {
    db: Connection,
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
            .map(|s| serde_json::from_str(&s).map_err(Into::into))
            .transpose()
    }
    pub fn create(
        &self,
        look: Look,
        spawn: Point,
    ) -> Result<(Character, String), Box<dyn std::error::Error>> {
        // A bearer key resumes a guest character, not an account/password login.
        let token = format!("{}{}", Uuid::new_v4().simple(), Uuid::new_v4().simple());
        let c = Character {
            id: Uuid::new_v4().to_string(),
            hp: look.class.health(),
            look,
            x: spawn.x,
            y: spawn.y,
            level: 1,
            xp: 0,
            gold: 0,
            kills: 0,
        };
        self.db.execute(
            "INSERT INTO characters(id,token_hash,state) VALUES(?1,?2,?3)",
            params![c.id, hash(&token), serde_json::to_string(&c)?],
        )?;
        Ok((c, token))
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
        s.save_many(std::iter::once(&c)).unwrap();
        let restored = s.load(&token).unwrap().unwrap();
        assert_eq!(restored.gold, 81);
        assert_eq!(restored.look.warrior_weapon, "royal");
        assert!(s.load(&"a".repeat(64)).unwrap().is_none());
        assert!(s.load("anything").unwrap().is_none());
        let stored: String =
            s.db.query_row("SELECT token_hash FROM characters", [], |r| r.get(0))
                .unwrap();
        assert_ne!(stored, token);
    }
}
