//! Elite hunts fought outdoors can be hired for at their giver; open hiring stays with the dungeon Repair Smiths.
use super::wyrd_tests::{join, place, world};
use super::*;

/// Hunts without the group flag that were hired for at a stone before open hiring moved indoors.
const SPAN_HUNTS: [&str; 2] = ["sky_h_shardking", "sky_wr_alpha"];

#[test]
fn every_outdoor_elite_hunt_giver_rents_all_five_classes() {
    let w = world();
    let outdoors = || (0..w.maps.len()).filter(|&z| !w.is_instance(z));
    let mut hunts = 0;
    for quest in outdoors().flat_map(|z| &w.maps[z].quests) {
        if !(quest.group || SPAN_HUNTS.contains(&quest.id.as_str())) {
            continue;
        }
        let outdoor_prey = quest.objectives.iter().any(|o| {
            o.kind == "kill"
                && w.spawns
                    .iter()
                    .any(|s| s.kind == o.target && !w.is_instance(s.zone))
        });
        if !outdoor_prey {
            continue;
        }
        hunts += 1;
        let giver = outdoors()
            .flat_map(|z| &w.maps[z].npcs)
            .find(|n| n.id == quest.npc)
            .unwrap_or_else(|| panic!("{}: no giver outdoors", quest.id));
        let classes: std::collections::BTreeSet<_> = giver
            .offers
            .iter()
            .filter(|o| !o.open && !o.raid)
            .filter_map(|o| o.merc.as_deref())
            .filter(|merc| *merc != "dismiss")
            .collect();
        assert_eq!(classes.len(), 5, "{}: {} rents no fighters", quest.id, giver.id);
    }
    assert!(hunts >= 40, "only {hunts} outdoor elite hunts found");
}

#[test]
fn restored_elite_givers_hire_for_the_accepted_hunt_only() {
    for (quest, npc) in [
        ("ew_link", "ew_keeper"),
        ("veyr_queen", "ve_rs_corvin"),
        ("sky_h_shardking", "sky_brokk"),
    ] {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        let (zone, at) = (0..w.maps.len())
            .find_map(|z| {
                w.maps[z]
                    .npcs
                    .iter()
                    .find(|n| n.id == npc)
                    .map(|n| (z, n.position_at(0.)))
            })
            .unwrap();
        place(&mut w, 1, zone, at);
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 99;
        c.gold = 1_000_000;
        c.quests.clear();
        let hired = |w: &World| w.players.values().filter(|p| p.merc.is_some()).count();

        w.time += 1.;
        w.interact(1, npc, Some("merc_priest"));
        assert_eq!(hired(&w), 0, "{quest}: nothing to hire for without the quest");
        assert_eq!(w.players[&1].character.gold, 1_000_000);

        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .quests
            .push(QuestProgress {
                id: quest.into(),
                counts: vec![0],
                claimed: false,
                completions: 0,
            });
        w.time += 1.;
        w.interact(1, npc, Some("merc_priest"));
        assert_eq!(hired(&w), 1, "{quest}: {npc} hires");
        let merc = w.players.values().find(|p| p.merc.is_some()).unwrap();
        assert_eq!(merc.merc_quest.as_deref(), Some(quest));
        assert!(w.players[&1].character.gold < 1_000_000);

        // The hired fighter's killing blow counts for the hirer, with or without the group flag.
        let merc = *w
            .players
            .iter()
            .find(|(_, p)| p.merc.is_some())
            .unwrap()
            .0;
        let prey = w
            .maps
            .iter()
            .flat_map(|m| &m.quests)
            .find(|q| q.id == quest)
            .unwrap()
            .objectives[0]
            .target
            .clone();
        let slime = w
            .slimes
            .iter()
            .position(|s| s.kind == prey && !w.is_instance(s.zone))
            .unwrap_or_else(|| panic!("{quest}: no {prey} outdoors"));
        let (zone, at) = (w.slimes[slime].zone, w.slimes[slime].point());
        place(&mut w, 1, zone, at);
        place(&mut w, merc, zone, at);
        w.slimes[slime].dead = false;
        w.slimes[slime].hp = 1.;
        w.hit_slime(slime, merc, 1e12, false);
        let progress = w.players[&1]
            .character
            .quests
            .iter()
            .find(|p| p.id == quest)
            .unwrap();
        assert_eq!(progress.counts[0], 1, "{quest}: the hirer is credited");
    }
}
