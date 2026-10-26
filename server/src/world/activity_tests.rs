use super::wyrd_tests::{calm, drain, join, world};
use super::*;

fn page(w: &World, category: &str) -> Value {
    w.gm_activity(9, None, "", category, false).unwrap()
}
fn gm(w: &mut World) -> mpsc::Receiver<Value> {
    let rx = join(w, 9, Class::Mage);
    w.players.get_mut(&9).unwrap().character.gm = true;
    rx
}
#[test]
fn activity_tracks_ordinary_players_but_only_gm_can_read_even_with_test_commands() {
    let mut w = world();
    calm(&mut w);
    let mut rx = join(&mut w, 1, Class::Warrior);
    let _gm = gm(&mut w);
    assert_eq!(page(&w, "login")["rows"].as_array().unwrap().len(), 2);
    w.test_commands = true;
    drain(&mut rx);
    w.debug(
        1,
        Some(7),
        DebugCommand::GmActivity {
            before: None,
            query: String::new(),
            category: String::new(),
            warnings: false,
        },
    );
    let reply = drain(&mut rx).into_iter().find(|r| r["ref"] == 7).unwrap();
    assert_eq!(reply["ok"], false);
    assert!(reply.get("result").is_none());
    assert!(w.snapshot_for(0).get("activity").is_none());
    w.players.get_mut(&1).unwrap().character.grant_xp(500);
    w.audit_progress();
    assert!(
        page(&w, "level")["rows"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r["character"] == w.players[&1].character.id)
    );
    w.players.get_mut(&1).unwrap().character.zone = 4;
    w.players.get_mut(&1).unwrap().character.hp = 0.;
    w.audit_progress();
    assert_eq!(page(&w, "travel")["rows"].as_array().unwrap().len(), 1);
    assert_eq!(page(&w, "death")["rows"].as_array().unwrap().len(), 1);
    w.leave(1);
    assert_eq!(page(&w, "logout")["rows"].as_array().unwrap().len(), 1);
    assert!(w.gm_activity(9, None, "", "unknown", false).is_err());
}
#[test]
fn activity_records_completed_normal_trade_and_sanitizes_unauthorized_commands() {
    let mut w = world();
    calm(&mut w);
    let _a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Mage);
    let _gm = gm(&mut w);
    let a = w.players[&1].character.id.clone();
    let b = w.players[&2].character.id.clone();
    let point = w.players[&1].character.point();
    w.players.get_mut(&2).unwrap().character.x = point.x;
    w.players.get_mut(&2).unwrap().character.y = point.y;
    w.players.get_mut(&1).unwrap().character.gold = 100;
    w.players.get_mut(&2).unwrap().character.gold = 0;
    w.trade(1, TradeCommand::Request { id: b });
    w.trade(2, TradeCommand::Accept { id: a });
    w.trade(
        1,
        TradeCommand::Offer {
            items: vec![],
            gold: 25,
        },
    );
    w.trade(1, TradeCommand::Confirm);
    w.trade(2, TradeCommand::Confirm);
    assert_eq!(w.players[&1].character.gold, 75);
    assert_eq!(w.players[&2].character.gold, 25);
    assert_eq!(page(&w, "trade")["rows"].as_array().unwrap().len(), 2);
    w.debug(
        1,
        None,
        DebugCommand::GiveItem {
            item: "DO_NOT_RECORD_RAW_ARGUMENT".into(),
            force: false,
            quantity: 1,
        },
    );
    w.debug(1, None, DebugCommand::SetLevel { level: 99 });
    let warnings = w.gm_activity(9, None, "", "", true).unwrap();
    assert_eq!(
        warnings["rows"].as_array().unwrap().len(),
        1,
        "warning spam throttled"
    );
    assert!(warnings.to_string().contains("Unauthorized"));
    assert!(!warnings.to_string().contains("DO_NOT_RECORD"));
    assert_eq!(w.players[&1].character.level, 1);
}
#[test]
fn activity_is_bounded_paged_filtered_and_survives_reopen() {
    let path = std::env::temp_dir().join(format!(
        "valhallasc-activity-{}.sqlite",
        uuid::Uuid::new_v4()
    ));
    {
        let store = Store::open(&path).unwrap();
        {
            let mut db = store.conn();
            let tx = db.transaction().unwrap();
            tx.execute_batch("WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<5000) INSERT INTO activity_log(at,character,actor,category,details,warning) SELECT 0,'id','Regular','login','Login fixture',0 FROM n;").unwrap();
            tx.commit().unwrap();
        }
        store.log_activity(
            "last",
            "Special Player",
            "security",
            "Rejected attempt",
            true,
        );
    }
    {
        let store = Store::open(&path).unwrap();
        assert_eq!(
            store
                .conn()
                .query_row("SELECT COUNT(*) FROM activity_log", [], |r| r
                    .get::<_, i64>(0))
                .unwrap(),
            5000
        );
        let mut w = World::with_level_spread(store, 0);
        let _gm = gm(&mut w);
        let first = page(&w, "");
        assert_eq!(first["rows"].as_array().unwrap().len(), 100);
        let second = w
            .gm_activity(9, first["next"].as_i64(), "", "", false)
            .unwrap();
        assert!(second["rows"][0]["id"].as_i64() < first["rows"][99]["id"].as_i64());
        let filtered = w
            .gm_activity(9, None, "Special Player", "security", true)
            .unwrap();
        assert_eq!(filtered["rows"].as_array().unwrap().len(), 1);
        assert_eq!(
            w.gm_activity(9, None, "' OR 1=1 --", "", false).unwrap()["rows"],
            json!([])
        );
        assert_eq!(
            w.store
                .conn()
                .query_row("PRAGMA quick_check", [], |r| r.get::<_, String>(0))
                .unwrap(),
            "ok"
        );
    }
    std::fs::remove_file(path).unwrap();
}
