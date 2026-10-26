//! Bounded integration checks: real loot/XP paths, with no encounter timing or farming.
use super::wyrd_tests::{at, join, place, world};
use super::*;
use crate::items::hierlooms::PIECES;

fn equip(c: &mut Character) {
    for (slot, id) in [
        ("accessory1", PIECES[0]),
        ("accessory2", PIECES[1]),
        ("necklace", PIECES[2]),
        ("cloak", PIECES[3]),
    ] {
        c.add_item(id, 1);
        c.equip_slots(&BTreeMap::from([(slot.into(), id.into())]))
            .unwrap();
    }
}

#[test]
fn hierloom_real_boss_loot_keeps_oranges_and_adds_a_collectible_golden_copy() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let owner = w.players[&1].character.id.clone();
    let zone = w
        .maps
        .iter()
        .position(|m| m.name == "The Chained Forge")
        .unwrap();
    let rules: Value =
        serde_json::from_str(include_str!("../../../world/raid-rewards.txt")).unwrap();
    for b in rules["bosses"].as_array().unwrap() {
        let kind = b["kind"].as_str().unwrap();
        w.drops.clear();
        // Deterministic first successful roll after the unchanged orange table's draws.
        w.rng = if kind == "cf_eldmarr" { 0 } else { 83 };
        place(&mut w, 1, zone, at(20., 20.));
        w.boss_loot(&owner, kind, zone, at(20., 20.));
        assert_eq!(
            w.drops
                .iter()
                .filter(|d| d.gear.as_ref().is_some_and(|g| g.rarity == "legendary"))
                .count(),
            if kind == "cf_eldmarr" { 4 } else { 2 }
        );
        let index = w
            .drops
            .iter()
            .position(|d| d.gear.as_ref().is_some_and(|g| g.rarity == "hierloom"))
            .expect("successful hierloom roll");
        assert_eq!(w.drops[index].col, "#ffd24a");
        let id = w.drops[index].item.clone().unwrap();
        let before = w.players[&1].character.quantity(&id);
        assert!(w.collect_drop(index, 1, &mut vec![]));
        assert_eq!(w.players[&1].character.quantity(&id), before + 1);
    }
}

#[test]
fn hierloom_kill_and_quest_xp_are_actually_paid_at_five_times_base() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 50;
    equip(c);
    let id = w.slimes.iter().position(|s| s.zone == 0).unwrap();
    let xp = w.slimes[id].xp;
    let point = at(w.slimes[id].x, w.slimes[id].y);
    place(&mut w, 1, 0, point);
    w.hit_slime(id, 1, 1e12, false);
    assert_eq!(w.players[&1].character.xp, xp * 5);
    // Ready a single existing talk/visit quest using a fixture rather than playing its route.
    let npc = w.maps[1]
        .npcs
        .iter()
        .find(|n| n.id == "crags_captain")
        .unwrap()
        .clone();
    let quest = w.maps[1]
        .quests
        .iter()
        .find(|q| q.id == "crags_onward")
        .unwrap();
    let reward = quest.reward_xp;
    let progress = QuestProgress {
        id: quest.id.clone(),
        counts: quest.objectives.iter().map(|o| o.count).collect(),
        claimed: false,
        completions: 0,
    };
    let spot = npc.position_at(w.time);
    place(&mut w, 1, 1, spot);
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .quests
        .push(progress);
    let before = w.players[&1].character.xp;
    w.interact(1, "crags_captain", Some("quest:claim:crags_onward"));
    assert_eq!(w.players[&1].character.xp - before, reward * 5);
}

#[test]
fn hierloom_party_drop_uses_need_greed_and_inspect_uses_the_targets_level() {
    let mut w = world();
    let mut a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Mage);
    let leader = w.players[&1].character.id.clone();
    let member = w.players[&2].character.id.clone();
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(member.clone()),
            name: None,
        },
    );
    w.social(2, SocialCommand::PartyAccept { id: leader.clone() });
    for session in [1, 2] {
        place(&mut w, session, 46, at(20., 20.));
    }
    let gear = GearInstance::new(0, item(PIECES[0]).unwrap());
    w.loot_drop_with_gear(&leader, 46, at(20., 20.), PIECES[0], Some(gear));
    assert_eq!(w.rolls.len(), 1);
    assert_eq!(w.rolls[0].item, PIECES[0]);
    assert_eq!(w.rolls[0].votes.len(), 2);
    let c = &mut w.players.get_mut(&2).unwrap().character;
    c.level = 40;
    equip(c);
    w.time += 1.;
    w.inspect(1, &member);
    let packet = std::iter::from_fn(|| a.try_recv().ok())
        .find(|v| v["type"] == "inspect")
        .unwrap();
    let slot = packet["slots"]
        .as_array()
        .unwrap()
        .iter()
        .find(|v| v["slot"] == "necklace")
        .unwrap();
    assert_eq!(slot["bonus"]["stamina"], 80);
    assert_eq!(slot["xpPercent"], 100);
    assert_eq!(slot["rarity"], "hierloom");
}
