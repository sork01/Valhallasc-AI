//! `QUEST-ITEM-DROPS` (world/quest_drops.rs): quest-only items for the `bring` quests drop only while needed, at their own chance, to the
//! party members who still need them in turn; a hand-in discards the excess; old saves are converted.
use super::quest_drops::{discard_excess_quest_items, migrate_quest_items, wanted};
use super::wyrd_tests::{calm, join, place, world};
use super::*;

/// A remapped `bring` quest: (quest, its quest item, the material it comes from, the objective count, the chance).
fn remapped(w: &World) -> Vec<(Quest, String, String, u32, f64)> {
    w.maps
        .iter()
        .flat_map(|m| &m.quests)
        .flat_map(|q| {
            q.objectives.iter().filter_map(move |o| {
                let i = item(&o.target)?;
                let from = i.quest_material.clone()?;
                Some((q.clone(), i.id.clone(), from, o.count, o.drop_chance.unwrap_or(-1.)))
            })
        })
        .collect()
}
/// One remapped quest whose material a plain monster kind drops, with that kind.
fn pick(w: &World) -> (Quest, String, String, u32, f64, String) {
    remapped(w)
        .into_iter()
        .find_map(|(q, id, from, count, chance)| {
            let kind = ["green", "blue", "pink", "yellow", "beetle"].into_iter().find(|k| material(k) == from)?;
            Some((q, id, from, count, chance, kind.to_string()))
        })
        .expect("a remapped bring quest whose material a basic slime drops")
}
fn take_quest(w: &mut World, session: u64, quest: &Quest) {
    let c = &mut w.players.get_mut(&session).unwrap().character;
    c.quests.push(QuestProgress {
        id: quest.id.clone(),
        counts: vec![0; quest.objectives.len()],
        claimed: false,
        completions: 0,
    });
}
fn lying(w: &World, id: &str, item: &str) -> u32 {
    w.drops.iter().filter(|d| d.owner == id && d.item.as_deref() == Some(item)).map(|d| d.quantity.max(1)).sum()
}
fn id_of(w: &World, session: u64) -> String {
    w.players[&session].character.id.clone()
}

#[test]
fn every_bring_objective_asks_for_an_unsellable_item_and_every_remapped_chance_lies_between_30_and_80_percent() {
    let w = world();
    let mut remapped_count = 0;
    for q in w.maps.iter().flat_map(|m| &m.quests) {
        for o in q.objectives.iter().filter(|o| o.kind == "bring") {
            let i = item(&o.target).unwrap_or_else(|| panic!("{}: unknown {}", q.id, o.target));
            assert!(is_quest_item(i), "{}: {} is still sold by merchants", q.id, i.id);
            if i.quest_material.is_some() {
                remapped_count += 1;
                let chance = o.drop_chance.unwrap_or_else(|| panic!("{} has no dropChance", q.id));
                assert!((0.30..=0.80).contains(&chance), "{}: {chance}", q.id);
                assert!(item(i.quest_material.as_deref().unwrap()).is_some_and(|m| m.sell > 0 && m.kind == "material"));
            }
        }
    }
    assert!(remapped_count >= 100, "{remapped_count} remapped objectives");
}

#[test]
fn no_quest_no_drop_and_drops_stop_at_the_need() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    let (quest, item_id, _from, count, _chance, kind) = pick(&w);
    let me = id_of(&w, 1);
    let at = w.players[&1].character.point();
    let zone = w.players[&1].character.zone;
    // Without the quest nothing falls, however many monsters die.
    for _ in 0..300 {
        w.quest_item_drops(&kind, zone, at, &me, 1);
    }
    assert_eq!(lying(&w, &me, &item_id), 0, "not on the quest");
    // On the quest: it falls until what lies there plus what is held makes the count, and then it stops.
    take_quest(&mut w, 1, &quest);
    for _ in 0..2000 {
        w.quest_item_drops(&kind, zone, at, &me, 1);
    }
    assert_eq!(lying(&w, &me, &item_id), count, "exactly the count, no more");
    // Picked-up copies count as held: still nothing more falls.
    w.drops.retain(|d| d.item.as_deref() != Some(&item_id));
    w.players.get_mut(&1).unwrap().character.add_item(&item_id, count);
    for _ in 0..500 {
        w.quest_item_drops(&kind, zone, at, &me, 5);
    }
    assert_eq!(lying(&w, &me, &item_id), 0, "the rebirth multiplier cannot push past the need");
    // A claimed quest asks for nothing.
    w.players.get_mut(&1).unwrap().character.consume_item(&item_id, count);
    w.players.get_mut(&1).unwrap().character.quests.iter_mut().for_each(|q| q.claimed = true);
    for _ in 0..500 {
        w.quest_item_drops(&kind, zone, at, &me, 1);
    }
    assert_eq!(lying(&w, &me, &item_id), 0);
}

#[test]
fn the_observed_rate_is_the_objectives_own_chance() {
    let mut w = world();
    calm(&mut w);
    let _rx = join(&mut w, 1, Class::Warrior);
    let (quest, item_id, _from, _count, chance, kind) = pick(&w);
    let me = id_of(&w, 1);
    let at = w.players[&1].character.point();
    let zone = w.players[&1].character.zone;
    take_quest(&mut w, 1, &quest);
    let trials = 4000;
    let mut hits = 0;
    for _ in 0..trials {
        w.drops.retain(|d| d.item.as_deref() != Some(&item_id));
        w.quest_item_drops(&kind, zone, at, &me, 1);
        hits += lying(&w, &me, &item_id).min(1);
    }
    let rate = f64::from(hits) / f64::from(trials);
    let spread = 4. * (chance * (1. - chance) / f64::from(trials)).sqrt();
    assert!((rate - chance).abs() <= spread.max(0.03), "{rate} against {chance}");
}

#[test]
fn a_party_hands_each_copy_to_the_next_member_who_still_needs_it_and_skips_the_rest() {
    let mut w = world();
    calm(&mut w);
    let _a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Mage);
    let _c = join(&mut w, 3, Class::Priest);
    let (quest, item_id, _from, count, _chance, kind) = pick(&w);
    let (zone, at) = (w.players[&1].character.zone, w.players[&1].character.point());
    for s in [2, 3] {
        place(&mut w, s, zone, at);
    }
    let (ids, leader) = ([id_of(&w, 1), id_of(&w, 2), id_of(&w, 3)], id_of(&w, 1));
    for s in [2, 3] {
        w.social(1, SocialCommand::PartyInvite { id: Some(id_of(&w, s)), name: None });
        w.social(s, SocialCommand::PartyAccept { id: leader.clone() });
    }
    // Only the warrior and the priest hold the quest.
    take_quest(&mut w, 1, &quest);
    take_quest(&mut w, 3, &quest);
    let mut given = std::collections::BTreeMap::<String, u32>::new();
    for _ in 0..400 {
        w.quest_item_drops(&kind, zone, at, &ids[0], 1);
        for d in w.drops.drain(..).filter(|d| d.item.as_deref() == Some(&item_id)) {
            *given.entry(d.owner).or_default() += d.quantity.max(1);
        }
        for s in [1, 3] {
            // Pick the copies up straight away so the need never closes.
            let c = &mut w.players.get_mut(&s).unwrap().character;
            let have = c.quantity(&item_id);
            if have > 0 {
                c.consume_item(&item_id, have);
            }
        }
    }
    assert_eq!(given.get(&ids[1]), None, "the mage is not on the quest and gets nothing");
    let (a, c) = (given[&ids[0]], given[&ids[2]]);
    assert!(a > 0 && c > 0 && a.abs_diff(c) <= 1, "taken in turn: {a} and {c}");
    let _ = count;
}

#[test]
fn a_hand_in_discards_only_what_no_other_quest_needs() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let (quest, item_id, _from, count, _chance, _kind) = pick(&w);
    let name = item(&item_id).unwrap().name.clone();
    take_quest(&mut w, 1, &quest);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.add_item(&item_id, count + 3);
    // Claimed: the quest's own count goes in the hand-in, and the three extra copies are discarded.
    quest.take_bring(c);
    c.quests.iter_mut().for_each(|q| q.claimed = true);
    let gone = discard_excess_quest_items(c, &quest, &w.maps);
    assert_eq!(gone, vec![(name, 3)]);
    assert_eq!(c.quantity(&item_id), 0);
    assert_eq!(wanted(c, &w.maps, &item_id), 0);
    // A quest item another held quest still asks for stays. (Pretend a second quest asks for the same item.)
    let other_id = w.maps.iter().flat_map(|m| &m.quests).find(|q| q.id != quest.id && q.has_bring()).unwrap().id.clone();
    for q in w.maps.iter_mut().flat_map(|m| &mut m.quests).filter(|q| q.id == other_id) {
        q.objectives.iter_mut().filter(|o| o.kind == "bring").take(1).for_each(|o| {
            o.target = item_id.clone();
            o.count = 2;
        });
    }
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.quests.push(QuestProgress { id: other_id.clone(), counts: vec![0; 4], claimed: false, completions: 0 });
    c.quests.iter_mut().filter(|q| q.id == quest.id).for_each(|q| q.claimed = true);
    c.add_item(&item_id, 5);
    let gone = discard_excess_quest_items(c, &quest, &w.maps);
    assert_eq!(c.quantity(&item_id), 2, "the other quest still needs two");
    assert_eq!(gone[0].1, 3);
}

#[test]
fn an_old_save_converts_its_progress_and_loses_the_quest_items_nobody_needs() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let (quest, item_id, from, count, _chance, _kind) = pick(&w);
    take_quest(&mut w, 1, &quest);
    let stray = remapped(&w).into_iter().find(|r| r.1 != item_id).unwrap().1;
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.quest_items_version = 0;
    c.add_item(&from, count + 4);
    c.add_item(&stray, 3);
    let (converted, removed) = migrate_quest_items(c, &w.maps);
    assert_eq!(converted, count, "up to the count of the held material becomes the quest item");
    assert_eq!(c.quantity(&item_id), count);
    assert_eq!(c.quantity(&from), 4, "the rest is ordinary, sellable material");
    assert_eq!((c.quantity(&stray), removed), (0, 3), "a quest item no held quest needs is removed");
    assert_eq!(c.quest_items_version, 1);
    // Once only.
    c.add_item(&stray, 1);
    assert_eq!(migrate_quest_items(c, &w.maps), (0, 0));
    assert_eq!(c.quantity(&stray), 1);
}

#[test]
fn the_migration_keeps_banked_shards_and_keys_but_a_quest_item_cannot_be_banked() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let (_quest, item_id, _from, _count, _chance, _kind) = pick(&w);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.quest_items_version = 0;
    c.bank.items.push(ItemStack { item: "ember_shard_0".into(), quantity: 2 });
    c.bank.items.push(ItemStack { item: item_id.clone(), quantity: 3 });
    migrate_quest_items(c, &w.maps);
    assert_eq!(c.bank.quantity("ember_shard_0"), 2, "raid-key progress in the bank survives");
    assert_eq!(c.bank.quantity(&item_id), 0, "a banked remapped quest item is dropped");
    // And nothing new goes in.
    c.add_item(&item_id, 2);
    assert!(c.bank_deposit(&item_id, 2, None).is_err());
    assert_eq!(c.quantity(&item_id), 2);
}

/// Release rehearsal (`REHEARSE_DB=<copy of the live database> cargo test rehearse_migration -- --ignored --nocapture`): every stored
/// character goes through the tutorial v2 step, the level clamp and the quest-item migration, and the counts are printed.
#[test]
#[ignore = "needs REHEARSE_DB, a copy of the live database"]
fn rehearse_migration_on_a_copy_of_the_live_database() {
    let Ok(path) = std::env::var("REHEARSE_DB") else {
        return;
    };
    let w = world();
    let db = rusqlite::Connection::open(path).unwrap();
    let mut stmt = db.prepare("SELECT state FROM characters").unwrap();
    let states: Vec<String> = stmt.query_map([], |r| r.get(0)).unwrap().map(Result::unwrap).collect();
    assert!(!states.is_empty());
    for state in states {
        let mut c: Character = serde_json::from_str(&state).expect("a stored character decodes");
        let before = (c.level, c.tutorial_version, c.tutorial_done.len(), c.inventory.len(), c.bank.items.len());
        c.migrate_tutorial();
        c.clamp_level();
        let (converted, removed) = migrate_quest_items(&mut c, &w.maps);
        assert!(c.level <= MAX_LEVEL && c.bag_used() <= c.bag_capacity().max(c.bag_used()));
        println!(
            "{:<12} level {:>2} tutorial v{}->v{} done {}->{} converted {} removed {} bag cells {}/{} bank {}",
            c.look.name, c.level, before.1, c.tutorial_version, before.2, c.tutorial_done.len(), converted, removed, c.bag_used(), c.bag_capacity(), c.bank.used()
        );
    }
}
