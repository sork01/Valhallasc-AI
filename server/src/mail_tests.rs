use super::*;
use crate::items::{ITEMS, ItemStack};
use crate::model::{Look, Point};

fn fixture() -> (Store, Character, Character, String, String) {
    let mut store = Store::open(std::path::Path::new(":memory:")).unwrap();
    let (mut a, ta) = store
        .create(
            Look {
                name: "Mail Alice".into(),
                ..Look::default()
            },
            Point { x: 36., y: 83. },
        )
        .unwrap();
    let (b, tb) = store
        .create(
            Look {
                name: "Mail Bob".into(),
                ..Look::default()
            },
            Point { x: 36., y: 83. },
        )
        .unwrap();
    a.gold = 5000;
    a.add_item("slime_gel", 20);
    a.materialize_gear_instances();
    store.save_many([&a, &b].into_iter()).unwrap();
    (store, a, b, ta, tb)
}
fn letter(to: &Character, key: &str, gold: u32, attachments: Vec<Attachment>) -> Request {
    Request::Send {
        request: key.into(),
        recipient: to.look.name.to_uppercase(),
        subject: "A letter".into(),
        body: "Hello\n<plain text>".into(),
        gold,
        attachments,
    }
}
fn stack(id: &str, quantity: u32) -> Attachment {
    Attachment {
        item: id.into(),
        quantity,
        copy: None,
    }
}
fn send(
    store: &Store,
    a: &Character,
    b: &Character,
    gold: u32,
    items: Vec<Attachment>,
) -> (Character, i64) {
    let (a, p) = store
        .mail(a, letter(b, "mail-test-receipt-0001", gold, items))
        .unwrap();
    (a, p["sent"].as_i64().unwrap())
}
fn held(store: &Store, token: &str) -> Character {
    store.load(token).unwrap().unwrap()
}
fn mail_count(store: &Store) -> i64 {
    store
        .conn()
        .query_row("SELECT count(*) FROM mail", [], |r| r.get(0))
        .unwrap()
}

#[test]
fn mail_offline_delivery_exact_identity_read_collect_save_and_duplicate_receipts() {
    let (store, a, b, ta, tb) = fixture();
    let (a, id) = send(&store, &a, &b, 100, vec![stack("slime_gel", 3)]);
    assert_eq!((a.gold, a.quantity("slime_gel")), (4900, 17));
    assert_eq!(store.mail_unread(&b.id).unwrap(), 1);
    assert_eq!(held(&store, &ta).gold, 4900);
    assert_eq!(
        held(&store, &tb).gold,
        b.gold,
        "offline recipient unchanged until claim"
    );
    let (a, p) = store
        .mail(
            &a,
            letter(
                &b,
                "mail-test-receipt-0001",
                100,
                vec![stack("slime_gel", 3)],
            ),
        )
        .unwrap();
    assert_eq!(p["sent"], id);
    assert_eq!(a.gold, 4900);
    assert_eq!(mail_count(&store), 1);
    assert!(
        store.mail(&a, Request::Collect { id }).is_err(),
        "sender cannot claim recipient mail"
    );
    let (b, p) = store.mail(&b, Request::Read { id }).unwrap();
    assert_eq!(p["letters"][0]["body"], "Hello\n<plain text>");
    assert_eq!(store.mail_unread(&b.id).unwrap(), 0);
    let (b, _) = store.mail(&b, Request::Collect { id }).unwrap();
    assert_eq!((b.gold, b.quantity("slime_gel")), (100, 3));
    let (b, _) = store.mail(&b, Request::Collect { id }).unwrap();
    assert_eq!((b.gold, b.quantity("slime_gel")), (100, 3));
    assert_eq!(held(&store, &tb).quantity("slime_gel"), 3);
    store.mail(&b, Request::Delete { id }).unwrap();
    assert!(store.mail(&b, Request::Collect { id }).is_err());
    let (a, p) = store
        .mail(
            &a,
            letter(
                &b,
                "mail-test-receipt-0001",
                100,
                vec![stack("slime_gel", 3)],
            ),
        )
        .unwrap();
    assert_eq!(p["sent"], id);
    assert_eq!(a.gold, 4900);
    assert_eq!(mail_count(&store), 1, "deleted receipt retained");
}

#[test]
fn mail_unknown_self_npc_names_missing_funds_and_invalid_attachments_change_nothing() {
    let (store, a, b, ta, _) = fixture();
    let before = serde_json::to_value(&a).unwrap();
    for name in [
        a.look.name.as_str(),
        "No Such Character",
        "Brenna Coinwright",
        "Merc Warrior",
    ] {
        let mut req = letter(&b, "mail-test-invalid-0001", 0, vec![]);
        if let Request::Send { recipient, .. } = &mut req {
            *recipient = name.to_owned();
        }
        assert!(store.mail(&a, req).is_err());
    }
    let bad = [
        vec![stack("slime_gel", 0)],
        vec![stack("slime_gel", 21)],
        vec![stack("slime_gel", 1), stack("slime_gel", 1)],
        vec![stack("nonexistent", 1)],
        vec![Attachment {
            copy: Some(1),
            ..stack("slime_gel", 1)
        }],
        vec![stack("slime_gel", 1); ATTACHMENT_LIMIT + 1],
    ];
    for attachments in bad {
        assert!(
            store
                .mail(&a, letter(&b, "mail-test-invalid-0001", 1, attachments))
                .is_err()
        );
    }
    assert!(
        store
            .mail(&a, letter(&b, "mail-test-invalid-0001", 5001, vec![]))
            .is_err()
    );
    assert_eq!(serde_json::to_value(held(&store, &ta)).unwrap(), before);
    assert_eq!(mail_count(&store), 0);
}

#[test]
fn mail_all_bound_class_gear_refused_even_with_party_trade_permission() {
    let (mut store, mut a, b, _, _) = fixture();
    let bound: Vec<_> = ITEMS
        .iter()
        .filter(|i| is_gear(i) && i.class.is_some())
        .collect();
    assert!(!bound.is_empty());
    for i in bound {
        assert_eq!(
            ineligible(&i.id),
            Some("Bound class gear cannot be mailed.")
        );
    }
    let i = ITEMS
        .iter()
        .find(|i| is_gear(i) && i.class.is_some() && !i.starter)
        .unwrap();
    a.add_item(&i.id, 1);
    a.materialize_gear_instances();
    let g = a
        .gear_instances
        .iter_mut()
        .rev()
        .find(|g| g.item == i.id)
        .unwrap();
    g.open_trade_window(vec![b.id.clone()], unix_now() as u64);
    let id = g.id;
    store.save_many([&a].into_iter()).unwrap();
    let e = store
        .mail(
            &a,
            letter(
                &b,
                "mail-test-bound-0001",
                0,
                vec![Attachment {
                    copy: Some(id),
                    ..stack(&i.id, 1)
                }],
            ),
        )
        .unwrap_err();
    assert!(e.contains("Bound class gear"));
    assert_eq!(mail_count(&store), 0);
    for i in ITEMS.iter().filter(|i| {
        i.starter || i.rarity == GM_RARITY || i.kind == "mount_licence" || is_quest_item(i)
    }) {
        assert!(ineligible(&i.id).is_some(), "{}", i.id);
    }
}

#[test]
fn mail_selected_unbound_gear_preserves_properties_worn_copy_and_new_owner_ids() {
    let (mut store, mut a, mut b, ta, tb) = fixture();
    let i = ITEMS
        .iter()
        .find(|i| {
            is_gear(i) && ineligible(&i.id).is_none() && i.kind != "armor" && i.kind != "weapon"
        })
        .unwrap();
    a.add_item(&i.id, 3);
    a.equipment.insert(i.kind.clone(), i.id.clone());
    a.materialize_gear_instances();
    let ids: Vec<_> = a
        .gear_instances
        .iter()
        .filter(|g| g.item == i.id)
        .map(|g| g.id)
        .collect();
    assert!(a.equipped_count(i) > 0);
    let g = a
        .gear_instances
        .iter_mut()
        .find(|g| g.id == ids[2])
        .unwrap();
    g.rank = 3;
    g.wear = 70;
    g.attack = 123.4;
    g.rolled_stats.stamina = 17;
    g.trade_until = 900;
    g.trade_with = vec![b.id.clone()];
    let mut original = g.clone();
    b.add_item(&i.id, 1);
    b.materialize_gear_instances();
    store.save_many([&a, &b].into_iter()).unwrap();
    assert!(
        store
            .mail(
                &a,
                letter(
                    &b,
                    "mail-test-worn-0001",
                    0,
                    vec![Attachment {
                        copy: Some(ids[0]),
                        ..stack(&i.id, 1)
                    }]
                )
            )
            .is_err()
    );
    let (a, id) = send(
        &store,
        &a,
        &b,
        0,
        vec![Attachment {
            copy: Some(ids[2]),
            ..stack(&i.id, 1)
        }],
    );
    assert!(a.gear_instances.iter().any(|g| g.id == ids[0]));
    assert!(!a.gear_instances.iter().any(|g| g.id == ids[2]));
    let (b, _) = store.mail(&b, Request::Collect { id }).unwrap();
    let received = b.gear_instances.last().unwrap();
    assert!(
        received.id
            > b.gear_instances
                .iter()
                .filter(|g| g.id != received.id)
                .map(|g| g.id)
                .max()
                .unwrap()
    );
    original.id = received.id;
    original.clear_trade_window();
    assert_eq!(*received, original);
    assert_eq!(held(&store, &ta).quantity(&i.id), 2);
    assert_eq!(held(&store, &tb).quantity(&i.id), 2);
}

#[test]
fn mail_full_bags_gold_and_stack_overflow_leave_entire_escrow_available() {
    let (store, a, mut b, _, tb) = fixture();
    let (_, id) = send(&store, &a, &b, 100, vec![stack("slime_gel", 3)]);
    b.inventory = ITEMS
        .iter()
        .filter(|i| ineligible(&i.id).is_none() && i.id != "slime_gel")
        .take(b.bag_capacity())
        .map(|i| ItemStack {
            item: i.id.clone(),
            quantity: 1,
        })
        .collect();
    assert!(
        store
            .mail(&b, Request::Collect { id })
            .unwrap_err()
            .contains("full")
    );
    assert_eq!(held(&store, &tb).gold, 0);
    b.inventory.clear();
    b.gold = u32::MAX;
    assert!(
        store
            .mail(&b, Request::Collect { id })
            .unwrap_err()
            .contains("gold")
    );
    b.gold = 0;
    b.add_item("slime_gel", u32::MAX);
    assert!(
        store
            .mail(&b, Request::Collect { id })
            .unwrap_err()
            .contains("stack")
    );
    b.inventory.clear();
    let (b, _) = store.mail(&b, Request::Collect { id }).unwrap();
    assert_eq!((b.gold, b.quantity("slime_gel")), (100, 3));
}

#[test]
fn mail_failure_during_send_and_claim_rolls_back_character_and_escrow() {
    let (store, a, b, ta, tb) = fixture();
    store.conn().execute_batch("CREATE TRIGGER fail_mail_save BEFORE UPDATE OF state ON characters BEGIN SELECT RAISE(ABORT,'injected save failure'); END;").unwrap();
    assert!(
        store
            .mail(
                &a,
                letter(
                    &b,
                    "mail-test-failure-0001",
                    100,
                    vec![stack("slime_gel", 2)]
                )
            )
            .is_err()
    );
    assert_eq!(mail_count(&store), 0);
    assert_eq!(held(&store, &ta).gold, 5000);
    store
        .conn()
        .execute_batch("DROP TRIGGER fail_mail_save;")
        .unwrap();
    let (_, id) = send(&store, &a, &b, 100, vec![stack("slime_gel", 2)]);
    store.conn().execute_batch("CREATE TRIGGER fail_mail_save BEFORE UPDATE OF state ON characters BEGIN SELECT RAISE(ABORT,'injected save failure'); END;").unwrap();
    assert!(store.mail(&b, Request::Collect { id }).is_err());
    assert_eq!(held(&store, &tb).gold, 0);
    store
        .conn()
        .execute_batch("DROP TRIGGER fail_mail_save;")
        .unwrap();
    let (b, _) = store.mail(&b, Request::Collect { id }).unwrap();
    assert_eq!((b.gold, b.quantity("slime_gel")), (100, 2));
}

#[test]
fn mail_return_escrow_once_delete_protection_and_character_deletion_guard() {
    let (store, a, b, _, _) = fixture();
    let (a, id) = send(&store, &a, &b, 100, vec![stack("slime_gel", 2)]);
    assert!(store.mail(&b, Request::Delete { id }).is_err());
    // Attach characters to separate accounts; deletion must retain both identities until collection.
    for c in [&a, &b] {
        store
            .conn()
            .execute(
                "UPDATE characters SET account_id='test' WHERE id=?1",
                [&c.id],
            )
            .unwrap();
        assert!(!store.delete_account_character("test", &c.id).unwrap());
    }
    store.mail(&b, Request::Return { id }).unwrap();
    assert_eq!(store.mail_unread(&a.id).unwrap(), 1);
    assert!(store.mail(&b, Request::Collect { id }).is_err());
    assert!(store.mail(&a, Request::Return { id }).is_err());
    let (a, _) = store.mail(&a, Request::Collect { id }).unwrap();
    assert_eq!((a.gold, a.quantity("slime_gel")), (5000, 20));
    assert!(store.delete_account_character("test", &b.id).unwrap());
    store.mail(&a, Request::Delete { id }).unwrap();
}

#[test]
fn mail_limits_text_only_delivery_and_lookup_leak_no_credentials() {
    let (store, a, b, _, _) = fixture();
    let (_, p) = store
        .mail(
            &a,
            Request::Lookup {
                name: b.look.name.to_lowercase(),
            },
        )
        .unwrap();
    assert_eq!(p["found"], b.look.name);
    assert!(!p.to_string().contains("token"));
    let mut a = a;
    for n in 0..HOURLY_LIMIT {
        let (next, _) = store
            .mail(
                &a,
                letter(&b, &format!("mail-rate-receipt-{n:04}"), 0, vec![]),
            )
            .unwrap();
        a = next;
    }
    assert!(
        store
            .mail(&a, letter(&b, "mail-rate-overflow-0001", 0, vec![]))
            .unwrap_err()
            .contains("thirty")
    );
    assert_eq!(store.mail_unread(&b.id).unwrap(), HOURLY_LIMIT);
    store
        .conn()
        .execute("UPDATE mail SET created=0", [])
        .unwrap();
    store
        .conn()
        .execute("UPDATE mail SET deleted=0", [])
        .unwrap();
    // Inflate with valid rows from distinct senders to exercise the independent inbox cap.
    for n in HOURLY_LIMIT..INBOX_LIMIT {
        store.conn().execute("INSERT INTO mail(sender,recipient,sender_name,recipient_name,request,subject,body,contents,created) VALUES(?1,?2,'a','b',?1,'subject','body',?3,0)",params![format!("sender-{n}"),b.id,serde_json::to_string(&Contents::default()).unwrap()]).unwrap();
    }
    assert!(
        store
            .mail(&a, letter(&b, "mail-inbox-overflow-0001", 0, vec![]))
            .unwrap_err()
            .contains("full")
    );
}

#[test]
fn mail_reopen_database_after_send_and_claim_preserves_receipts() {
    let path =
        std::env::temp_dir().join(format!("valhallasc-mail-{}.sqlite", uuid::Uuid::new_v4()));
    let mut store = Store::open(&path).unwrap();
    let (mut a, ta) = store
        .create(
            Look {
                name: "Restart Alice".into(),
                ..Default::default()
            },
            Point { x: 36., y: 83. },
        )
        .unwrap();
    let (b, tb) = store
        .create(
            Look {
                name: "Restart Bob".into(),
                ..Default::default()
            },
            Point { x: 36., y: 83. },
        )
        .unwrap();
    a.gold = 100;
    store.save_many([&a].into_iter()).unwrap();
    let (_, id) = send(&store, &a, &b, 100, vec![]);
    drop(store);
    let store = Store::open(&path).unwrap();
    let a = held(&store, &ta);
    let b = held(&store, &tb);
    assert_eq!(a.gold, 0);
    assert_eq!(store.mail_unread(&b.id).unwrap(), 1);
    store.mail(&b, Request::Collect { id }).unwrap();
    drop(store);
    let store = Store::open(&path).unwrap();
    let b = held(&store, &tb);
    let (b, _) = store.mail(&b, Request::Collect { id }).unwrap();
    assert_eq!(b.gold, 100);
    let (a, p) = store
        .mail(&a, letter(&b, "mail-test-receipt-0001", 100, vec![]))
        .unwrap();
    assert_eq!(a.gold, 0);
    assert_eq!(p["sent"], id);
    drop(store);
    std::fs::remove_file(path).unwrap();
}

#[test]
fn dungeon_award_mail_persists_exact_bound_copy_and_receipt_after_collection() {
    let path = std::env::temp_dir().join(format!(
        "valhallasc-roll-mail-{}.sqlite",
        uuid::Uuid::new_v4()
    ));
    let mut store = Store::open(&path).unwrap();
    let (mut c, token) = store
        .create(Look::default(), Point { x: 36., y: 83. })
        .unwrap();
    let base = ITEMS
        .iter()
        .find(|i| is_gear(i) && i.class.is_some() && !i.starter)
        .unwrap();
    let mut gear = GearInstance::new(777, base);
    gear.rank = 3;
    gear.wear = 40;
    gear.attack += 7.;
    gear.rolled_stats.strength = 9;
    gear.open_trade_window(vec!["other-voter".into()], unix_now() as u64);
    for i in ITEMS.iter().filter(|i| i.kind == "material") {
        if c.bag_used() >= c.bag_capacity() {
            break;
        }
        c.add_item(&i.id, 1);
    }
    c.materialize_gear_instances();
    store.save_many([&c].into_iter()).unwrap();
    store
        .mail_roll_award(&c.id, &c.look.name, "award-receipt", &base.id, Some(&gear))
        .unwrap();
    store
        .mail_roll_award(&c.id, &c.look.name, "award-receipt", &base.id, Some(&gear))
        .unwrap();
    assert_eq!(mail_count(&store), 1);
    assert_eq!(
        store.mail(&c, Request::Open).unwrap().1["letters"][0]["systemAward"],
        true
    );
    let id = store.mail(&c, Request::Open).unwrap().1["letters"][0]["id"]
        .as_i64()
        .unwrap();
    let before = serde_json::to_value(&c).unwrap();
    assert!(store.mail(&c, Request::Collect { id }).is_err());
    assert_eq!(serde_json::to_value(held(&store, &token)).unwrap(), before);
    assert!(
        store.mail(&c, Request::Return { id }).is_err(),
        "system award cannot be returned"
    );
    c.inventory
        .retain(|s| item(&s.item).is_none_or(|i| i.kind != "material"));
    store.save_many([&c].into_iter()).unwrap();
    drop(store);
    let store = Store::open(&path).unwrap();
    let c = held(&store, &token);
    let (c, _) = store.mail(&c, Request::Collect { id }).unwrap();
    let mut expected = gear.clone();
    let received = c.gear_instances.iter().find(|g| g.item == base.id).unwrap();
    expected.id = received.id;
    assert_eq!(received, &expected);
    assert_eq!(c.quantity(&base.id), 1);
    let before = serde_json::to_value(&c).unwrap();
    let (c, _) = store.mail(&c, Request::Collect { id }).unwrap();
    assert_eq!(serde_json::to_value(&c).unwrap(), before);
    let (c, _) = store.mail(&c, Request::Delete { id }).unwrap();
    store
        .mail_roll_award(&c.id, &c.look.name, "award-receipt", &base.id, Some(&gear))
        .unwrap();
    assert_eq!(mail_count(&store), 1);
    assert_eq!(store.mail_unread(&c.id).unwrap(), 0);
    drop(store);
    std::fs::remove_file(path).unwrap();
}
