//! How the extra mounts are obtained (docs/mounts.md, MOUNT-SOURCES): the Banyan Run raptor chain, the Dune-wrangler,
//! the Gryphon hatching, and the two bound licences with their drop rolls.
use super::rolls::{can_need, rollable};
use super::wyrd_tests::{at, blocked, calm, drain, flood, join, place, reached, world};
use super::*;

fn zone(w: &World, name: &str) -> usize {
    w.maps.iter().position(|m| m.name == name).unwrap()
}
fn talk(w: &mut World, zone: usize, npc: &str, offer: Option<&str>) {
    place(w, 1, zone, at(0., 0.));
    w.time += 0.6;
    let here = w.maps[zone]
        .npcs
        .iter()
        .find(|n| n.id == npc)
        .unwrap()
        .position_at(w.time);
    place(w, 1, zone, here);
    w.interact(1, npc, offer);
}
/// Every text the player was sent, errors and notices alike.
fn heard(rx: &mut mpsc::Receiver<Value>) -> Vec<String> {
    drain(rx)
        .into_iter()
        .filter_map(|v| v["text"].as_str().map(str::to_owned))
        .collect()
}
fn hero(w: &mut World, level: u32, gold: u32) {
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = level;
    c.gold = gold;
}
fn owns(w: &World, id: &str) -> bool {
    w.players[&1].character.owns_mount(id)
}

#[test]
fn the_catalog_holds_two_bound_licences_and_the_horse_offer_names_its_mount() {
    for (id, mount) in [
        ("sabertooth_whistle", "sabertooth"),
        ("gryphon_egg", "gryphon"),
    ] {
        let i = item(id).unwrap();
        assert_eq!(
            (i.kind.as_str(), i.mount.as_deref()),
            ("mount_licence", Some(mount))
        );
        assert_eq!(i.required_level, mount_def(mount).unwrap().level);
        assert!(rollable(&i.rarity), "{id} is rolled for in a party");
    }
    let w = world();
    let greta = w.maps[zone(&w, "Skaldholm")]
        .npcs
        .iter()
        .find(|n| n.id == "city_stable")
        .unwrap();
    assert_eq!(greta.offers[0].mount.as_deref(), Some("horse"));
    assert_eq!(greta.offers[0].cost, 500_000);
}

#[test]
fn the_dune_wrangler_sells_the_lizard_at_level_eighty_for_160000_gold() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let erg = zone(&w, "The Lapis Erg");
    let offer = &w.maps[erg]
        .npcs
        .iter()
        .find(|n| n.id == "lapis_wrangler")
        .unwrap()
        .offers[0];
    assert_eq!(
        (offer.cost, offer.mount.as_deref()),
        (160_000, Some("lizard"))
    );
    hero(&mut w, 79, 1_000_000);
    talk(&mut w, erg, "lapis_wrangler", Some("buy_lizard"));
    assert!(!owns(&w, "lizard"), "level 80 is required");
    hero(&mut w, 80, 159_999);
    talk(&mut w, erg, "lapis_wrangler", Some("buy_lizard"));
    assert!(!owns(&w, "lizard"), "the price is authoritative");
    hero(&mut w, 80, 160_000);
    talk(&mut w, erg, "lapis_wrangler", Some("buy_lizard"));
    assert!(owns(&w, "lizard"));
    assert_eq!(w.players[&1].character.gold, 0);
    assert_eq!(
        w.players[&1].character.mount, "lizard",
        "a first mount is selected"
    );
    hero(&mut w, 80, 160_000);
    talk(&mut w, erg, "lapis_wrangler", Some("buy_lizard"));
    assert_eq!(w.players[&1].character.gold, 160_000, "no second purchase");
}

#[test]
fn oren_highwind_hatches_a_gryphon_egg_for_250000_gold_at_level_ninety_five() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let cairn = zone(&w, "The Cairnspine");
    let offer = w.maps[cairn]
        .npcs
        .iter()
        .find(|n| n.id == "cairn_windseer")
        .unwrap()
        .offers
        .iter()
        .find(|o| o.id == "hatch_gryphon")
        .unwrap();
    assert_eq!(
        (offer.cost, offer.mount.as_deref(), offer.needs.as_deref()),
        (250_000, Some("gryphon"), Some("gryphon_egg"))
    );
    hero(&mut w, 95, 1_000_000);
    talk(&mut w, cairn, "cairn_windseer", Some("hatch_gryphon"));
    assert!(!owns(&w, "gryphon"), "no egg, no hatching");
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .add_item("gryphon_egg", 1);
    hero(&mut w, 94, 1_000_000);
    talk(&mut w, cairn, "cairn_windseer", Some("hatch_gryphon"));
    assert!(!owns(&w, "gryphon"), "level 95 is required");
    hero(&mut w, 95, 249_999);
    talk(&mut w, cairn, "cairn_windseer", Some("hatch_gryphon"));
    assert!(
        !owns(&w, "gryphon") && w.players[&1].character.quantity("gryphon_egg") == 1,
        "the fee is authoritative"
    );
    hero(&mut w, 95, 250_000);
    talk(&mut w, cairn, "cairn_windseer", Some("hatch_gryphon"));
    let c = &w.players[&1].character;
    assert!(
        c.owns_mount("gryphon") && c.gold == 0 && c.quantity("gryphon_egg") == 0,
        "the egg and the gold are spent"
    );
}

#[test]
fn a_licence_grants_its_mount_once_and_is_kept_when_it_would_do_nothing() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.add_item("sabertooth_whistle", 2);
    c.level = 94;
    w.message(
        1,
        ClientMessage::UseItem {
            item: "sabertooth_whistle".into(),
        },
    );
    assert!(!owns(&w, "sabertooth"), "below level 95 the whistle waits");
    assert!(heard(&mut rx).iter().any(|t| t.contains("needs level 95")));
    w.players.get_mut(&1).unwrap().character.level = 95;
    w.message(
        1,
        ClientMessage::UseItem {
            item: "sabertooth_whistle".into(),
        },
    );
    assert!(owns(&w, "sabertooth"));
    assert_eq!(w.players[&1].character.quantity("sabertooth_whistle"), 1);
    w.message(
        1,
        ClientMessage::UseItem {
            item: "sabertooth_whistle".into(),
        },
    );
    assert_eq!(
        w.players[&1].character.quantity("sabertooth_whistle"),
        1,
        "a spare is never consumed uselessly"
    );
    assert!(heard(&mut rx).iter().any(|t| t.contains("already own")));
    let c = &mut w.players.get_mut(&1).unwrap().character;
    assert!(
        c.sell_item("sabertooth_whistle", 1).is_err(),
        "a licence cannot be sold"
    );
    assert_eq!(c.quantity("sabertooth_whistle"), 1);
}

#[test]
fn only_a_character_without_the_mount_may_need_its_licence() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let egg = item("gryphon_egg").unwrap();
    assert!(can_need(&w.players[&1].character, egg));
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .grant_mount("gryphon");
    assert!(
        !can_need(&w.players[&1].character, egg),
        "an owner can only greed or pass"
    );
}

#[test]
fn the_licence_drop_table_names_the_rimesaber_and_the_final_thunderheart_boss() {
    assert_eq!(
        mount_licence_drop("rimesaber", false),
        Some(("sabertooth_whistle", 0.04))
    );
    assert_eq!(
        mount_licence_drop("thunder_heart", true),
        Some(("gryphon_egg", 0.03))
    );
    assert_eq!(
        mount_licence_drop("thunder_heart", false),
        None,
        "only the dungeon's last boss"
    );
    assert_eq!(mount_licence_drop("snowgiant", true), None);
}

#[test]
fn the_rimesaber_drops_the_whistle_about_four_times_in_a_hundred_kills() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let year = zone(&w, "The Yearwheel");
    let id = w
        .slimes
        .iter()
        .position(|s| s.zone == year && s.kind == "rimesaber")
        .unwrap();
    let kills = 1500;
    let mut whistles = 0;
    for _ in 0..kills {
        let spot = at(w.spawns[id].x, w.spawns[id].y);
        place(&mut w, 1, year, spot);
        w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), 97);
        w.drops.clear();
        w.hit_slime(id, 1, 1e12, false);
        whistles += w
            .drops
            .iter()
            .filter(|d| d.item.as_deref() == Some("sabertooth_whistle"))
            .count();
    }
    // 60 expected, standard deviation about 7.6: a 5-sigma band
    assert!(
        (25..=95).contains(&whistles),
        "{whistles} whistles in {kills} kills"
    );
}

#[test]
fn the_banyan_run_is_four_steps_ending_in_an_escort_that_grants_the_raptor() {
    let w = world();
    let jungle = zone(&w, "The Tanglecrown");
    let m = &w.maps[jungle];
    let chain: Vec<&Quest> = (1..=4)
        .map(|n| {
            m.quests
                .iter()
                .find(|q| q.id == format!("tangle_banyan_{n}"))
                .unwrap()
        })
        .collect();
    assert!(
        chain
            .iter()
            .all(|q| q.npc == "tangle_tracker" && !q.repeatable)
    );
    assert_eq!(chain[0].requires.as_deref(), Some("tangle_welcome"));
    for pair in chain.windows(2) {
        assert_eq!(pair[1].requires.as_deref(), Some(pair[0].id.as_str()));
    }
    assert_eq!(
        chain[0].objectives.iter().map(|o| o.count).sum::<u32>(),
        25,
        "25 canopy monsters"
    );
    assert!(chain[0].objectives.iter().all(|o| o.kind == "kill"));
    assert_eq!(
        chain[1].objectives.iter().map(|o| o.count).sum::<u32>(),
        10,
        "ten materials"
    );
    assert!(
        chain[1]
            .objectives
            .iter()
            .all(|o| o.kind == "bring" && item(&o.target).unwrap().kind == "material")
    );
    assert!(
        chain[2].group
            && chain[2].recommended_players == 3
            && is_elite(&chain[2].objectives[0].target),
        "one elite fight"
    );
    assert_eq!(chain[3].objectives[0].kind, "escort");
    assert_eq!(
        chain
            .iter()
            .filter_map(|q| q.reward_mount.as_deref())
            .collect::<Vec<_>>(),
        ["raptor"]
    );
    assert!(chain[3].reward_mount.is_some(), "the escort pays the mount");
    assert_eq!(chain[0].level, 75, "it opens at the raptor's level");
    for q in &chain {
        assert_eq!(q.reward_xp, xp_to_level(q.level) / 10, "{}", q.id);
    }
}

#[test]
fn the_hatchling_bearers_route_is_clear_ground_down_to_mara_vines() {
    let w = world();
    let jungle = zone(&w, "The Tanglecrown");
    let m = &w.maps[jungle];
    let bearer = m.npcs.iter().find(|n| n.id == "tangle_hatchling").unwrap();
    let def = bearer.escort.clone().unwrap();
    let mara = m.npcs.iter().find(|n| n.id == "tangle_tracker").unwrap();
    assert_eq!(
        (def.quest.as_str(), bearer.offers.len()),
        ("tangle_banyan_4", 0)
    );
    let route: Vec<Point> = std::iter::once(at(bearer.x, bearer.y))
        .chain(def.route.iter().map(|p| at(p[0], p[1])))
        .collect();
    let grid = blocked(m, &[]);
    let seen = flood(m, &grid, at(bearer.x, bearer.y));
    for p in &route {
        let mut foot = *p;
        m.collide(&mut foot, PLAYER_RADIUS);
        assert!(foot.distance(*p) < 1e-6, "{p:?} is blocked");
        assert!(reached(m, &seen, *p), "{p:?} cannot be walked to");
    }
    let end = *route.last().unwrap();
    assert!(
        end.distance(at(mara.x, mara.y)) < 2.8,
        "the journey ends within Mara's earshot"
    );
}

#[test]
fn finishing_the_banyan_run_pays_the_raptor_once_and_it_is_saved() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let jungle = zone(&w, "The Tanglecrown");
    let q = w.maps[jungle]
        .quests
        .iter()
        .find(|q| q.id == "tangle_banyan_4")
        .unwrap()
        .clone();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 80;
    c.quests.push(QuestProgress {
        id: "tangle_banyan_3".into(),
        claimed: true,
        completions: 1,
        ..Default::default()
    });
    assert!(quest_action(c, &q, "accept").2);
    c.quests.iter_mut().find(|p| p.id == q.id).unwrap().counts = vec![1];
    let (text, _, changed) = quest_action(c, &q, "claim");
    assert!(changed && text.contains("raptor"), "{text}");
    assert_eq!(
        (c.mounts.clone(), c.mount.as_str()),
        (vec!["raptor".to_string()], "raptor")
    );
    assert!(c.mount_owned);
}

#[test]
fn the_hatchling_bearer_joins_only_a_hero_on_the_last_step_and_walks_to_mara() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let jungle = zone(&w, "The Tanglecrown");
    let owner = w.players[&1].character.id.clone();
    let q = w.maps[jungle]
        .quests
        .iter()
        .find(|q| q.id == "tangle_banyan_4")
        .unwrap()
        .clone();
    calm(&mut w);
    talk(&mut w, jungle, "tangle_hatchling", None);
    assert!(w.escort_of(&owner).is_none(), "no quest, no escort");
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.level = 80;
    c.quests.push(QuestProgress {
        id: "tangle_banyan_3".into(),
        claimed: true,
        completions: 1,
        ..Default::default()
    });
    assert!(quest_action(c, &q, "accept").2);
    talk(&mut w, jungle, "tangle_hatchling", None);
    let session = w.escort_of(&owner).expect("Tamsin joins");
    assert_eq!(w.players[&session].character.look.name, "Tamsin Reedfoot");
    // she walks the route beside her hero and reaches the last waypoint
    for _ in 0..(120. / TICK) as usize {
        let there = w.players[&session].character.point();
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.x = there.x + 1.;
        c.y = there.y + 1.;
        c.hp = c.max_hp();
        w.step();
        w.players.get_mut(&1).unwrap().last_hurt = w.time;
        if w.players
            .get(&session)
            .is_none_or(|e| e.escort.as_ref().unwrap().arrived())
        {
            break;
        }
    }
    let progress = w.players[&1]
        .character
        .quests
        .iter()
        .find(|p| p.id == "tangle_banyan_4")
        .unwrap();
    assert_eq!(progress.counts, vec![1], "the escort objective is done");
}
