//! A bounded, persistent record of real players' activity. Only a verified GM can read it.
use super::*;
use rusqlite::params;

const MAX_EVENTS: i64 = 5000;
const PAGE_SIZE: usize = 100;

impl Store {
    pub(crate) fn log_activity(
        &self,
        character: &str,
        actor: &str,
        category: &str,
        details: &str,
        warning: bool,
    ) {
        let details: String = details.chars().take(800).collect();
        let result = (|| -> rusqlite::Result<()> {
            let mut db = self.conn();
            let tx = db.transaction()?;
            tx.execute("INSERT INTO activity_log(at,character,actor,category,details,warning) VALUES (?1,?2,?3,?4,?5,?6)",
                params![daynight::unix_ms(), character, actor, category, details, warning])?;
            tx.execute("DELETE FROM activity_log WHERE id <= (SELECT COALESCE(MAX(id),0)-?1 FROM activity_log)", [MAX_EVENTS])?;
            tx.commit()
        })();
        if let Err(error) = result {
            tracing::warn!(%error, "activity log write failed");
        }
    }

    fn activity_page(
        &self,
        before: Option<i64>,
        query: &str,
        category: &str,
        warnings: bool,
    ) -> rusqlite::Result<Value> {
        let db = self.conn();
        let mut stmt = db.prepare(
            "SELECT id,at,character,actor,category,details,warning FROM activity_log
            WHERE (?1 IS NULL OR id < ?1) AND (?2='' OR actor LIKE ?3 OR details LIKE ?3)
              AND (?4='' OR category=?4) AND (?5=0 OR warning=1) ORDER BY id DESC LIMIT 101",
        )?;
        let mut rows: Vec<Value> = stmt.query_map(params![before, query, format!("%{query}%"), category, warnings], |r| {
            Ok(json!({"id":r.get::<_,i64>(0)?,"at":r.get::<_,i64>(1)?,"character":r.get::<_,String>(2)?,
                "actor":r.get::<_,String>(3)?,"category":r.get::<_,String>(4)?,"details":r.get::<_,String>(5)?,"warning":r.get::<_,bool>(6)?}))
        })?.collect::<Result<_,_>>()?;
        let more = rows.len() > PAGE_SIZE;
        rows.truncate(PAGE_SIZE);
        let next = more.then(|| rows.last().unwrap()["id"].clone());
        Ok(json!({"rows":rows,"next":next}))
    }
}

#[derive(Clone, Copy)]
pub(super) struct Seen {
    pub level: u32,
    pub zone: usize,
    pub dead: bool,
}

impl World {
    pub(super) fn audit_player(&self, session: u64, category: &str, details: &str, warning: bool) {
        if let Some(p) = self.players.get(&session).filter(|p| {
            p.merc.is_none() && p.ambient.is_none() && !p.gauntlet && p.escort.is_none()
        }) {
            self.store.log_activity(
                &p.character.id,
                &p.character.look.name,
                category,
                details,
                warning,
            );
        }
    }
    pub(super) fn audit_warning(&mut self, session: u64, details: &str) {
        if self
            .activity_warn_at
            .get(&session)
            .is_none_or(|last| self.time - last >= 5.)
        {
            self.activity_warn_at.insert(session, self.time);
            self.audit_player(session, "security", details, true);
        }
    }
    pub(super) fn audit_progress(&mut self) {
        for (&session, p) in &self.players {
            if p.merc.is_some() || p.ambient.is_some() || p.gauntlet || p.escort.is_some() {
                continue;
            }
            let now = Seen {
                level: p.character.level,
                zone: self.public_zone(p.character.zone),
                dead: p.character.hp <= 0.,
            };
            if let Some(old) = self.activity_seen.insert(session, now) {
                if old.level != now.level {
                    self.audit_player(
                        session,
                        "level",
                        &format!("Level changed from {} to {}.", old.level, now.level),
                        false,
                    );
                }
                if old.zone != now.zone {
                    self.audit_player(
                        session,
                        "travel",
                        &format!(
                            "Travelled from {} to {}.",
                            self.zone_name(old.zone),
                            self.zone_name(now.zone)
                        ),
                        false,
                    );
                }
                if old.dead != now.dead {
                    self.audit_player(
                        session,
                        "death",
                        &format!(
                            "{} in {}.",
                            if now.dead {
                                "Defeated"
                            } else {
                                "Returned to life"
                            },
                            self.zone_name(now.zone)
                        ),
                        false,
                    );
                }
            }
        }
    }
    pub(super) fn gm_activity(
        &self,
        session: u64,
        before: Option<i64>,
        query: &str,
        category: &str,
        warnings: bool,
    ) -> Result<Value, String> {
        // Deliberately stricter than test-world debug shortcuts: ordinary players never read other players' logs.
        if !self.players.get(&session).is_some_and(|p| p.character.gm) {
            return Err("Only the game master can read the activity log.".into());
        }
        if query.chars().count() > 80
            || before.is_some_and(|id| id <= 0)
            || ![
                "", "login", "logout", "level", "travel", "death", "trade", "gm", "security",
            ]
            .contains(&category)
        {
            return Err("Invalid activity log filter.".into());
        }
        self.store
            .activity_page(before, query.trim(), category, warnings)
            .map_err(|_| "Activity log is unavailable.".to_owned())
    }
}
