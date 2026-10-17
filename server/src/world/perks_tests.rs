//! The rebirth perks in a running world (docs/rebirth.md, REBIRTH-PERKS): each one measured against an unreborn control
//! at the same seed, the drop multiplier over many kills and chests, and the promise that none of them changes combat.
use super::chests::boosted_ladder_rarity;
use super::wyrd_tests::{at, join, place, world};
use super::*;
use crate::perks::minus_percent;

/// A character who rebirthed once at each tier in `tiers`.
fn reborn(w: &mut World, tiers: [u32; 5]) {
    w.players.get_mut(&1).unwrap().character.rebirth_tiers = tiers;
}
/// Tier-5 rebirths that give a drop multiplier of `m` (and, with it, the other perks at their tier-5 values).
fn top_tier(m: u32) -> [u32; 5] {
    [0, 0, 0, 0, m - 1]
}
fn zone(w: &World, name: &str) -> usize {
    w.maps.iter().position(|m| m.name == name).unwrap()
}
fn kill(w: &mut World, id: usize, zone: usize, level: u32) {
    let spot = at(w.spawns[id].x, w.spawns[id].y);
    place(w, 1, zone, spot);
    w.slimes[id] = Slime::with_level(id, &w.spawns[id].clone(), level);
    w.hit_slime(id, 1, 1e12, false);
}
fn rarity_of(d: &Drop) -> &str {
    d.gear
        .as_ref()
        .map(|g| g.rarity.as_str())
        .or_else(|| d.item.as_deref().and_then(item).map(|i| i.rarity.as_str()))
        .unwrap_or("")
}
/// A count within a wide band around `want` (about five standard deviations for these sample sizes).
fn near(got: usize, want: f64, what: &str) {
    let slack = want * 0.18 + 6.;
    assert!(
        (got as f64 - want).abs() <= slack,
        "{what}: got {got}, wanted about {want}"
    );
}

#[derive(Default)]
struct Tally {
    gold_piles: Vec<u32>,
    material: u32,
    bags: usize,
    whistles: usize,
    gear: [usize; 5],
    orange: usize,
}

/// `kills` Rimesaber (an outdoor elite that drops a licence) killed by a hero with the given tiers.
fn elite_kills(tiers: [u32; 5], kills: usize) -> Tally {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    reborn(&mut w, tiers);
    let year = zone(&w, "The Yearwheel");
    let id = w
        .slimes
        .iter()
        .position(|s| s.zone == year && s.kind == "rimesaber")
        .unwrap();
    w.rng = 0x5eed;
    let mut t = Tally::default();
    for _ in 0..kills {
        w.drops.clear();
        kill(&mut w, id, year, 97);
        for d in &w.drops {
            match d.item.as_deref() {
                None => t.gold_piles.push(d.value),
                Some("rimesaber_fang") => t.material += d.quantity,
                Some("sabertooth_whistle") => t.whistles += 1,
                Some(i) if item(i).is_some_and(|i| i.kind == "bag") => t.bags += 1,
                Some(i) if d.gear.as_ref().is_some_and(|g| g.rarity == "legendary") => {
                    assert!(item(i).is_some());
                    t.orange += 1;
                }
                Some(_) => {
                    let at = RARITIES.iter().position(|r| *r == rarity_of(d)).unwrap();
                    t.gear[at] += 1;
                }
            }
        }
    }
    t
}

#[test]
fn an_elite_kill_pays_the_multiplier_in_gold_materials_bags_gear_and_the_licence() {
    let kills = 1200;
    let control = elite_kills([0; 5], kills);
    let base_gold = control.gold_piles[0];
    assert!(control.gold_piles.iter().all(|g| *g == base_gold));
    assert_eq!(control.gold_piles.len(), kills);
    assert_eq!(control.material as usize, kills, "one material per kill");
    assert_eq!(
        control.gear[RARITIES.iter().position(|r| *r == "uncommon").unwrap()],
        kills,
        "a green piece is guaranteed from an outdoor elite"
    );
    for m in [2u32, 5] {
        let tiers = top_tier(m);
        let t = elite_kills(tiers, kills);
        let mut who = Character::mercenary(Class::Warrior, 1, "Probe");
        who.rebirth_tiers = tiers;
        // One pile worth m times, then the gold bonus; the same on every kill.
        let pile = who.boosted_gold(base_gold * m);
        assert_eq!(t.gold_piles.len(), kills, "x{m} stays one pile per kill");
        assert!(t.gold_piles.iter().all(|g| *g == pile), "x{m}: {pile}");
        // One stack worth m times.
        assert_eq!(t.material as usize, kills * m as usize, "x{m} materials");
        // Bag 2%, whistle 4%.
        near(t.bags, kills as f64 * 0.02 * f64::from(m), "bags");
        near(t.whistles, kills as f64 * 0.04 * f64::from(m), "whistles");
        let uncommon = RARITIES.iter().position(|r| *r == "uncommon").unwrap();
        let rare = RARITIES.iter().position(|r| *r == "rare").unwrap();
        let epic = RARITIES.iter().position(|r| *r == "epic").unwrap();
        assert_eq!(t.gear[uncommon], kills * m as usize, "x{m} green copies");
        near(t.gear[rare], kills as f64 * 0.33 * f64::from(m), "blue");
        near(t.gear[epic], kills as f64 * 0.05 * f64::from(m), "purple");
    }
}

#[test]
fn the_multiplier_widens_every_ordinary_gear_band_and_the_orange_chance() {
    let kills = 3000;
    let mut found = vec![];
    for m in [1u32, 2, 5] {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        reborn(&mut w, top_tier(m));
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == 0 && !is_elite(&s.kind))
            .unwrap();
        w.rng = 77;
        let mut gear = 0;
        for _ in 0..kills {
            w.drops.clear();
            kill(&mut w, id, 0, 12);
            gear += w
                .drops
                .iter()
                .filter(|d| d.item.as_deref().and_then(item).is_some_and(is_gear))
                .count();
        }
        found.push(gear);
    }
    // 2% gray + 1.5% green + 0.03% blue + 0.01% purple per kill.
    let per_kill = 0.0354;
    for (gear, m) in found.iter().zip([1., 2., 5.]) {
        near(*gear, f64::from(kills as u32) * per_kill * m, "gear drops");
    }
    // The orange roll is one draw against its chance; the boosted roll divides the draw.
    let mut hits = [0usize; 2];
    for (slot, m) in [(0, 1u32), (1, 5)] {
        let mut x = 0.3;
        for _ in 0..200_000 {
            let mut first = true;
            let drew = roll_orange_boosted(m, || {
                x = (x + 0.618_033_988_749_895) % 1.;
                if std::mem::take(&mut first) { x } else { 0.5 }
            });
            hits[slot] += usize::from(drew.is_some());
        }
    }
    assert!(hits[0] > 0 && hits[1] >= hits[0] * 4, "{hits:?}");
}

#[test]
fn the_purple_copy_chance_of_a_set_piece_is_multiplied() {
    let mut counts = vec![];
    for m in [1u32, 2, 5] {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        reborn(&mut w, top_tier(m));
        let owner = w.players[&1].character.id.clone();
        let piece = boss_piece_for("hollowking", boss_slots("hollowking")[0], 0.5).unwrap();
        w.rng = 99;
        for _ in 0..4000 {
            w.set_piece_drop(&owner, 0, at(10., 10.), piece);
        }
        counts.push(w.drops.iter().filter(|d| rarity_of(d) == "epic").count());
    }
    for (got, m) in counts.iter().zip([1., 2., 5.]) {
        near(*got, 4000. * 0.05 * m, "purple copies");
    }
}

#[test]
fn a_boss_rolls_each_guaranteed_pool_once_per_step_of_the_multiplier() {
    let pools = boss_slots("hollowking").len();
    for m in [1u32, 2, 5] {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        reborn(&mut w, top_tier(m));
        let owner = w.players[&1].character.id.clone();
        w.boss_loot(&owner, "hollowking", 0, at(10., 10.));
        assert_eq!(w.drops.len(), pools * m as usize, "x{m}");
    }
}

#[test]
fn a_chest_opens_at_the_openers_multiplier() {
    let chest = |m: u32, dungeon: bool| {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        reborn(&mut w, top_tier(m));
        let owner = w.players[&1].character.id.clone();
        let zone = if dungeon {
            (0..w.maps.len())
                .find(|&z| w.is_instance(z) && w.maps[z].final_boss == "hollowking")
                .unwrap()
        } else {
            zone(&w, "The Yearwheel")
        };
        w.rng = 4242;
        let (mut gold, mut gear, mut sourced, mut material) = (vec![], 0, 0, 0);
        let chests = if dungeon { 1500 } else { 300 };
        for _ in 0..chests {
            w.drops.clear();
            w.chest_contents(&owner, zone, at(10., 10.));
            for d in &w.drops {
                match d.item.as_deref().and_then(item) {
                    None => gold.push(d.value),
                    Some(i) if i.kind == "material" => material += d.quantity,
                    Some(i) if i.source.is_some() => sourced += 1,
                    Some(i) if is_gear(i) => gear += 1,
                    Some(_) => {}
                }
            }
        }
        (gold, gear, sourced, material, chests)
    };
    let (control_gold, control_gear, _, control_material, chests) = chest(1, false);
    assert!(control_gold.iter().all(|g| *g == control_gold[0]));
    for m in [2u32, 5] {
        let (gold, gear, _, material, _) = chest(m, false);
        let mut who = Character::mercenary(Class::Warrior, 1, "Probe");
        who.rebirth_tiers = top_tier(m);
        // The pile is the unreborn pile times m, then the gold bonus.
        let base = control_gold[0];
        assert_eq!(gold.len(), chests, "one pile per chest");
        assert!(gold.iter().all(|g| *g == who.boosted_gold(base * m)));
        near(gear, control_gear as f64 * f64::from(m), "chest equipment");
        // The kind and the count are random and the sequences diverge, so compare the sizes.
        near(
            material as usize,
            f64::from(control_material * m),
            "stacks worth m times",
        );
    }
    // A dungeon chest also holds a piece of the dungeon's set with 6% chance, multiplied.
    let (_, _, plain, _, n) = chest(1, true);
    near(plain, n as f64 * 0.06, "set pieces at x1");
    let (_, _, boosted, _, _) = chest(5, true);
    near(boosted, n as f64 * 0.30, "set pieces at x5");
}

#[test]
fn the_chest_ladder_gives_purple_the_multiplier_and_takes_it_from_gray() {
    let share = |m: u32| {
        let steps = 100_000;
        let mut by = std::collections::BTreeMap::<&str, usize>::new();
        for n in 0..steps {
            *by.entry(boosted_ladder_rarity(n as f64 / steps as f64, m))
                .or_default() += 1;
        }
        move |r: &str| by.get(r).copied().unwrap_or(0) as f64 / steps as f64 * 100.
    };
    let (one, two, five) = (share(1), share(2), share(5));
    for (s, gray, green, blue, purple) in [
        (one, 62., 30., 7.5, 0.5),
        (two, 61.5, 30., 7.5, 1.),
        (five, 60., 30., 7.5, 2.5),
    ] {
        for (rarity, want) in [
            ("common", gray),
            ("uncommon", green),
            ("rare", blue),
            ("epic", purple),
        ] {
            assert!(
                (s(rarity) - want).abs() < 0.01,
                "{rarity}: {} vs {want}",
                s(rarity)
            );
        }
    }
}

#[test]
fn xp_gold_bags_fares_and_the_reset_price_follow_the_table() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let c = |w: &World| w.players[&1].character.clone();
    // Kill XP: a hero at level 20 gets exactly the boosted amount.
    let kill_xp = |tiers: [u32; 5]| {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        reborn(&mut w, tiers);
        w.players.get_mut(&1).unwrap().character.level = 20;
        let id = w.slimes.iter().position(|s| s.zone == 0).unwrap();
        let paid = w.slimes[id].xp;
        let level = w.slimes[id].level;
        kill(&mut w, id, 0, level);
        (w.players[&1].character.clone(), paid)
    };
    let (control, paid) = kill_xp([0; 5]);
    assert_eq!(control.xp, paid);
    for tiers in [[1, 0, 0, 0, 0], [5, 0, 0, 0, 0], [0, 0, 0, 0, 3]] {
        let (hero, paid) = kill_xp(tiers);
        assert_eq!(hero.xp, hero.boosted_xp(paid), "{tiers:?}");
    }
    // Bag cells and the stat-reset price.
    let before = c(&w);
    reborn(&mut w, [0, 0, 1, 0, 0]);
    let third = c(&w);
    assert_eq!(third.bag_capacity(), before.bag_capacity() + 2);
    assert_eq!(
        third.stat_reset_price(),
        before.stat_reset_price(),
        "tier 4 perk"
    );
    // A tier-4 rebirth also counts for the tier-3 perk.
    reborn(&mut w, [0, 0, 1, 1, 0]);
    let after = c(&w);
    assert_eq!(after.bag_capacity(), before.bag_capacity() + 4);
    assert_eq!(
        after.stat_reset_price(),
        minus_percent(before.stat_reset_price(), 10)
    );
    reborn(&mut w, [9, 9, 9, 9, 9]);
    let capped = c(&w);
    assert_eq!(capped.bag_capacity(), before.bag_capacity() + 10);
    assert_eq!(capped.stat_reset_price(), before.stat_reset_price() / 2);
    // A sale pays the gold bonus.
    let mut seller = Character::mercenary(Class::Warrior, 1, "Seller");
    seller.add_item("slime_gel", 1);
    let plain = {
        let mut s = seller.clone();
        s.sell_item("slime_gel", 1).unwrap()
    };
    seller.rebirth_tiers = [0, 2, 0, 0, 0];
    let paid = seller.sell_item("slime_gel", 1).unwrap();
    assert_eq!(paid, seller.boosted_gold(plain));
    assert!(paid > plain);
}

#[test]
fn spark_fares_are_cheaper_for_the_reborn() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    reborn(&mut w, [0, 0, 0, 2, 0]);
    let c = &w.players[&1].character;
    assert_eq!(c.spark_fare(40), 32);
    assert_eq!(c.spark_fare(20), 16);
    reborn(&mut w, [0, 0, 0, 9, 0]);
    assert_eq!(
        w.players[&1].character.spark_fare(20),
        10,
        "half at the cap"
    );
}

fn claim_onward(w: &mut World) {
    let zone = 1;
    w.players.get_mut(&1).unwrap().character.zone = zone;
    w.step();
    let here = w.maps[zone]
        .npcs
        .iter()
        .find(|n| n.id == "crags_captain")
        .unwrap()
        .position_at(w.time + 0.6);
    w.time += 0.6;
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.zone = zone;
    c.x = here.x;
    c.y = here.y;
    w.interact(1, "crags_captain", Some("quest:claim:crags_onward"));
}

#[test]
fn a_quest_pays_the_bonus_and_pays_again_after_a_rebirth() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    reborn(&mut w, [1, 1, 0, 0, 0]);
    {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 5;
        c.gold = 0;
    }
    w.step();
    let (xp, gold) = {
        let c = &w.players[&1].character;
        (c.xp, c.gold)
    };
    claim_onward(&mut w);
    let c = &w.players[&1].character;
    assert!(c.quests[0].claimed);
    let want = (xp_to_level(5) / 10, 100);
    assert_eq!(c.xp - xp, c.boosted_xp(want.0));
    assert_eq!(c.gold - gold, c.boosted_gold(want.1));
    assert!(c.gold - gold > 100);
    let said: Vec<String> = std::iter::from_fn(|| rx.try_recv().ok())
        .filter_map(|v| {
            v["text"]
                .as_str()
                .or(v["notice"].as_str())
                .map(str::to_owned)
        })
        .collect();
    assert!(
        said.iter().any(|t| t.contains(&format!(
            "+{} XP and +{} gold",
            c.boosted_xp(want.0),
            c.boosted_gold(want.1)
        ))),
        "the message names what was paid: {said:?}"
    );
    // A rebirth clears the ledger, and the same quest is earned and paid again.
    let level = {
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.level = 50;
        c.hp = c.max_hp();
        c.level
    };
    assert_eq!(level, 50);
    let spawn = at(30., 30.);
    w.players
        .get_mut(&1)
        .unwrap()
        .character
        .rebirth(spawn)
        .unwrap();
    assert!(w.players[&1].character.quests.is_empty());
    w.players.get_mut(&1).unwrap().character.level = 5;
    w.step();
    let (xp, gold) = {
        let c = &w.players[&1].character;
        (c.xp, c.gold)
    };
    claim_onward(&mut w);
    let c = &w.players[&1].character;
    assert!(c.quests[0].claimed && c.quests[0].completions == 1);
    assert!(c.gold > gold && c.xp > xp, "paid a second time");
}

#[test]
fn a_party_member_gets_their_own_bonus_on_the_shared_xp() {
    let mut w = world();
    let _a = join(&mut w, 1, Class::Warrior);
    let _b = join(&mut w, 2, Class::Mage);
    let (leader, member) = (
        w.players[&1].character.id.clone(),
        w.players[&2].character.id.clone(),
    );
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(member),
            name: None,
        },
    );
    w.social(2, SocialCommand::PartyAccept { id: leader });
    for session in [1, 2] {
        let c = &mut w.players.get_mut(&session).unwrap().character;
        c.level = 20;
        c.x = 10.;
        c.y = 10.;
    }
    w.players.get_mut(&2).unwrap().character.rebirth_tiers = [4, 0, 0, 0, 0];
    let id = w.slimes.iter().position(|s| s.zone == 0).unwrap();
    let level = w.slimes[id].level;
    let paid = w.slimes[id].xp;
    w.slimes[id].x = 10.;
    w.slimes[id].y = 10.;
    w.hit_slime(id, 1, 1e12, false);
    let (first, second) = (w.players[&1].character.xp, w.players[&2].character.xp);
    let share = super::partyxp::shared_xp(paid, 1);
    let _ = level;
    assert_eq!(first, share);
    assert_eq!(second, w.players[&2].character.boosted_xp(share));
    assert!(second > first);
}

#[test]
fn no_perk_changes_attack_defense_health_or_damage_taken() {
    let measure = |tiers: [u32; 5]| {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        {
            let c = &mut w.players.get_mut(&1).unwrap().character;
            c.level = 60;
            c.rebirth_tiers = tiers;
            c.hp = c.max_hp();
        }
        let c = w.players[&1].character.clone();
        let stats = (
            c.stats(),
            c.max_hp(),
            c.max_resource(),
            c.dodge_chance(),
            c.crit_chance(),
            c.stat_points(),
        );
        w.rng = 31;
        w.time = 100.;
        let id = w.slimes.iter().position(|s| s.zone == 0).unwrap();
        let spot = w.slimes[id].point();
        place(&mut w, 1, 0, at(spot.x + 40., spot.y + 40.));
        let level = w.slimes[id].level;
        let hp_before = w.players[&1].character.hp;
        let mut taken = vec![];
        for n in 0..12 {
            w.time += 1.;
            w.players.get_mut(&1).unwrap().last_hurt = -10.;
            let before = w.players[&1].character.hp;
            w.hurt_player_by(1, 50. + f64::from(n), spot, "slime", level);
            taken.push(before - w.players[&1].character.hp);
        }
        let dealt = {
            let before = w.slimes[id].hp;
            let damage = w.roll_damage(1, 1.);
            (damage, before)
        };
        (stats, hp_before, taken, dealt)
    };
    let control = measure([0; 5]);
    assert!(control.2.iter().any(|t| *t > 0.), "the probe takes damage");
    for tiers in [[5, 0, 0, 0, 0], [0, 0, 0, 0, 4], [9, 9, 9, 9, 9]] {
        assert_eq!(measure(tiers), control, "{tiers:?}");
    }
}

/// Source text before its first test module.
fn production(src: &str) -> &str {
    src.split("#[cfg(test)]").next().unwrap_or(src)
}
fn between<'a>(src: &'a str, from: &str, to: &str) -> &'a str {
    let start = src.find(from).unwrap_or_else(|| panic!("no {from}"));
    let end = src[start..].find(to).unwrap_or_else(|| panic!("no {to}")) + start;
    &src[start..end]
}

#[test]
fn every_drop_roll_goes_through_the_multiplier() {
    // Each roll primitive, in the kill rewards and the chest opener, has the multiplier within two lines.
    let world_src = include_str!("../world.rs");
    let chest_src = include_str!("chests.rs");
    let regions = [
        between(world_src, "fn hit_slime(", "fn item_drop("),
        between(chest_src, "fn chest_contents(", "/// `spawn_chest` op"),
    ];
    let primitives = [
        "roll_bag(",
        "roll_orange_boosted(",
        "roll_equipment(",
        "equipment_of_rarity(",
        "outdoor_elite_drop_chance(",
        "mount_licence_drop(",
        "ladder_rarity(",
        "set_piece_copy(",
        "boss_piece_for(",
        "gold_drop(",
        "loot_stack(",
    ];
    let mut checked = 0;
    for region in regions {
        let lines: Vec<&str> = region.lines().collect();
        for (n, line) in lines.iter().enumerate() {
            if line.trim_start().starts_with("//") {
                continue;
            }
            if primitives.iter().any(|p| line.contains(p)) {
                let window = lines[n.saturating_sub(3)..(n + 3).min(lines.len())].join("\n");
                assert!(
                    ["boost", "copies(", "pile_for(", "set_piece_drop("]
                        .iter()
                        .any(|m| window.contains(m)),
                    "a drop roll skips the rebirth multiplier: {line}"
                );
                checked += 1;
            }
        }
    }
    assert!(checked >= 12, "the audit saw only {checked} rolls");
    // The set piece's purple copy and the pool loop use the owner's multiplier.
    assert!(between(world_src, "fn boss_loot(", "fn item_drop(").contains("drop_multiplier_of"));
    // A new site that rolls drops elsewhere must be added to the regions above: none of the roll primitives may appear
    // in another production file outside the catalogue modules.
    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut stack = vec![dir];
    while let Some(path) = stack.pop() {
        for entry in std::fs::read_dir(path).unwrap().flatten() {
            let p = entry.path();
            if p.is_dir() {
                stack.push(p);
                continue;
            }
            let name = p.file_name().unwrap().to_string_lossy().into_owned();
            let allowed = [
                "items.rs",
                "orange.rs",
                "world.rs",
                "chests.rs",
                "perks.rs",
                "perks_tests.rs",
            ];
            if !name.ends_with(".rs")
                || name.ends_with("_tests.rs")
                || allowed.contains(&name.as_str())
            {
                continue;
            }
            let text = std::fs::read_to_string(&p).unwrap();
            for primitive in [
                "roll_bag(",
                "roll_orange_boosted(",
                "roll_equipment(",
                "mount_licence_drop(",
            ] {
                assert!(
                    !production(&text).contains(primitive),
                    "{name} rolls drops with {primitive} outside the audited sites"
                );
            }
        }
    }
}

#[test]
fn the_gryphon_egg_chance_is_multiplied_with_the_whistle() {
    let eggs = |m: u32| {
        let mut w = world();
        let _rx = join(&mut w, 1, Class::Warrior);
        reborn(&mut w, top_tier(m));
        let zone = (0..w.maps.len())
            .find(|&z| w.is_instance(z) && w.maps[z].final_boss == "thunder_heart")
            .unwrap();
        w.enter_instance(zone);
        let id = w
            .slimes
            .iter()
            .position(|s| s.zone == zone && s.kind == "thunder_heart")
            .unwrap();
        w.rng = 2026;
        let mut n = 0;
        for _ in 0..1500 {
            w.drops.clear();
            kill(&mut w, id, zone, 95);
            n += w
                .drops
                .iter()
                .filter(|d| d.item.as_deref() == Some("gryphon_egg"))
                .count();
        }
        n
    };
    near(eggs(1), 1500. * 0.03, "eggs at x1");
    near(eggs(2), 1500. * 0.06, "eggs at x2");
    near(eggs(5), 1500. * 0.15, "eggs at x5");
}

#[test]
fn the_snapshot_the_preview_friends_and_party_carry_what_the_panel_needs() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    let _other = join(&mut w, 2, Class::Mage);
    reborn(&mut w, [1, 0, 0, 0, 2]);
    let snap = w.players[&1].snapshot();
    let perks = snap["rebirthPerks"].as_array().unwrap();
    let find = |id: &str| perks.iter().find(|p| p["id"] == id).unwrap().clone();
    assert_eq!(find("xp")["value"], 30);
    assert_eq!(find("xp")["cap"], 50);
    assert_eq!(find("drops")["value"], 3);
    assert_eq!(find("drops")["unlock"], 5);
    assert_eq!(snap["mountTint"], 0);
    // The preview shows what one more rebirth at the current level adds.
    w.players.get_mut(&1).unwrap().character.level = 60;
    drain_all(&mut rx);
    w.message(1, ClientMessage::RebirthPreview);
    let packet = drain_all(&mut rx)
        .into_iter()
        .rev()
        .find(|v| v["type"] == "rebirthPreview")
        .unwrap();
    let after = |id: &str, key: &str| {
        packet[key]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["id"] == id)
            .unwrap()["value"]
            .clone()
    };
    assert_eq!(after("xp", "perks"), 30);
    assert_eq!(
        after("xp", "perksAfter"),
        40,
        "tier 2 also counts for the XP perk"
    );
    assert_eq!(
        after("gold", "perksAfter"),
        30,
        "the gold perk starts at tier 2 and counts all three"
    );
    assert_eq!(
        after("drops", "perksAfter"),
        3,
        "a tier-2 rebirth never raises the drops"
    );
    // Friends and the party frame show the tier.
    let (a, b) = (
        w.players[&1].character.id.clone(),
        w.players[&2].character.id.clone(),
    );
    w.social(
        1,
        SocialCommand::PartyInvite {
            id: Some(b.clone()),
            name: None,
        },
    );
    w.social(2, SocialCommand::PartyAccept { id: a.clone() });
    let party = w.party_value(0);
    let tier = |id: &str| {
        party["members"]
            .as_array()
            .unwrap()
            .iter()
            .find(|m| m["id"] == id)
            .unwrap()["reborn"]
            .clone()
    };
    assert_eq!((tier(&a), tier(&b)), (json!(5), json!(0)));
    assert_eq!(w.friend_entry(&a).unwrap()["reborn"], 5);
}

fn drain_all(rx: &mut mpsc::Receiver<Value>) -> Vec<Value> {
    std::iter::from_fn(|| rx.try_recv().ok()).collect()
}

#[test]
fn a_mount_coat_can_be_chosen_only_for_a_tier_reached_and_survives_a_rebirth() {
    let mut c = Character::mercenary(Class::Warrior, 50, "Rider");
    assert!(c.select_mount_tint(2).is_err(), "never reborn");
    assert!(c.select_mount_tint(0).is_ok());
    c.rebirth_tiers = [0, 1, 0, 0, 0];
    assert!(c.select_mount_tint(3).is_err(), "tier 3 is not reached");
    assert!(c.select_mount_tint(1).is_err(), "tier 1 has no coat");
    assert!(c.select_mount_tint(6).is_err());
    c.select_mount_tint(2).unwrap();
    assert_eq!(c.mount_tint, 2);
    c.hp = c.max_hp();
    c.rebirth(Point { x: 20., y: 20. }).unwrap();
    assert_eq!(c.mount_tint, 2, "cosmetic state is kept");
    c.select_mount_tint(0).unwrap();
    assert_eq!(c.mount_tint, 0);
}

#[test]
fn the_mount_coat_message_is_saved_and_a_bad_one_is_refused() {
    let mut w = world();
    let mut rx = join(&mut w, 1, Class::Warrior);
    reborn(&mut w, [0, 0, 1, 0, 0]);
    drain_all(&mut rx);
    w.message(1, ClientMessage::SelectMountTint { tier: 5 });
    assert_eq!(w.players[&1].character.mount_tint, 0);
    assert!(drain_all(&mut rx).iter().any(|v| v["type"] == "error"));
    w.message(1, ClientMessage::SelectMountTint { tier: 3 });
    assert_eq!(w.players[&1].character.mount_tint, 3);
    assert_eq!(w.players[&1].snapshot()["mountTint"], 3);
}
