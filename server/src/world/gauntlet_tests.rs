//! Arena gauntlet quests (`docs/arena-quests.md`): the quest data, a whole run of five fights and its reward, the ways a
//! run ends without one, and that an opponent is nobody's player but the hero's foe.
use super::gauntlet::{FIGHTS, opponent_character};
use super::ttk::{Case, build_character};
use super::wyrd_tests::{drain, join, world};
use super::*;

const SKALD: usize = 4;
const NACRE: usize = 9;

/// A level-`level` hero standing at `npc` in `zone`, in plain green gear.
fn hero(
    w: &mut World,
    session: u64,
    class: Class,
    level: u32,
    zone: usize,
    npc: &str,
) -> mpsc::Receiver<Value> {
    let rx = join(w, session, class);
    let case = Case::new(class, level);
    let at = w.maps[zone]
        .npcs
        .iter()
        .find(|n| n.id == npc)
        .map(|n| (n.x, n.y))
        .unwrap();
    let p = w.players.get_mut(&session).unwrap();
    build_character(&mut p.character, &case);
    p.character.zone = zone;
    p.character.x = at.0;
    p.character.y = at.1 + 0.5;
    rx
}
/// A talk to `npc` with `offer`, after the half second the service guard wants.
fn offer(w: &mut World, session: u64, npc: &str, offer: &str) {
    w.time += 1.;
    w.interact(session, npc, Some(offer));
}
fn counts(w: &World, session: u64, quest: &str) -> Vec<u32> {
    w.players[&session]
        .character
        .quests
        .iter()
        .find(|g| g.id == quest)
        .map(|g| g.counts.clone())
        .unwrap_or_default()
}
/// Steps until the run of `session` has an opponent standing.
fn until_opponent(w: &mut World, rx: &mut mpsc::Receiver<Value>, session: u64) -> u64 {
    for _ in 0..600 {
        w.step();
        drain(rx);
        if let Some(o) = w
            .gauntlets
            .iter()
            .find(|r| r.owner == session)
            .and_then(|r| r.opponent)
        {
            return o;
        }
    }
    panic!("no opponent appeared");
}
/// The hero lands blows until the opponent is down to the floor, then the world settles the fight.
fn beat(w: &mut World, session: u64, opponent: u64) {
    for _ in 0..40 {
        if w.gauntlets
            .iter()
            .any(|r| r.owner == session && r.fallen.is_some())
        {
            break;
        }
        w.pvp_hit(session, opponent, 1e9, false);
    }
    w.step();
}

#[test]
fn every_hub_offers_nine_trials_with_a_blue_weapon_for_each_class() {
    let w = world();
    let mut hubs = 0;
    for (zone, giver) in [
        (0, "guide"),
        (4, "city_steward"),
        (9, "nacre_archivist"),
        (13, "astral_steward"),
        (17, "asterion_archon"),
    ] {
        hubs += 1;
        let map = &w.maps[zone];
        assert!(
            map.npcs
                .iter()
                .find(|n| n.id == giver)
                .unwrap()
                .offers
                .iter()
                .any(|o| o.id == "gauntlet")
        );
        let trials: Vec<_> = map
            .quests
            .iter()
            .filter(|q| q.gauntlet_level().is_some())
            .collect();
        let levels: Vec<u32> = trials.iter().map(|q| q.gauntlet_level().unwrap()).collect();
        assert_eq!(levels, [20, 30, 40, 50, 60, 70, 80, 90, 99], "zone {zone}");
        for q in trials {
            assert_eq!(
                (q.npc.as_str(), q.min_level, q.level),
                (giver, q.level, q.level)
            );
            assert_eq!(q.objectives.len(), 1);
            assert_eq!(q.objectives[0].count, FIGHTS as u32);
            assert!(format!("quest:accept:{}", q.id).len() <= 32);
            for class in ["warrior", "mage", "assassin", "priest", "hunter"] {
                let [id] = q.reward_choices[class].as_slice() else {
                    panic!("one weapon")
                };
                let it = item(id).unwrap();
                assert_eq!(
                    (it.kind.as_str(), it.rarity.as_str()),
                    ("weapon", "rare"),
                    "{id}"
                );
            }
        }
    }
    assert_eq!(hubs, 5);
}

#[test]
fn a_run_of_five_fights_pays_the_quest_and_frees_the_arena() {
    let mut w = world();
    let mut rx = hero(&mut w, 1, Class::Warrior, 20, SKALD, "city_steward");
    let humans = w.humans_online();
    let gold = w.players[&1].character.gold;
    offer(&mut w, 1, "city_steward", "gauntlet");
    assert!(w.gauntlets.is_empty(), "no quest taken yet");
    offer(&mut w, 1, "city_steward", "quest:accept:arena_skald_20");
    assert_eq!(counts(&w, 1, "arena_skald_20"), [0]);
    offer(&mut w, 1, "city_steward", "gauntlet");
    drain(&mut rx);
    let arena = w.gauntlets[0].zone;
    assert!(w.is_arena_zone(arena) && w.players[&1].character.zone == arena);
    assert_eq!(w.humans_online(), humans);
    let mut seen = vec![];
    for fight in 1..=FIGHTS {
        let opponent = until_opponent(&mut w, &mut rx, 1);
        let o = &w.players[&opponent];
        assert!(
            o.gauntlet
                && o.merc.is_some()
                && o.character.level == 20
                && o.character.hp == o.character.max_hp()
        );
        seen.push(o.character.look.class);
        assert_eq!(w.humans_online(), humans, "an opponent is nobody's player");
        assert!(w.pvp_legal(1, opponent) && w.pvp_legal(opponent, 1));
        // Hurt and stunned going into the win: the next fight starts from full health, nothing left over.
        let p = w.players.get_mut(&1).unwrap();
        (p.character.hp, p.stun, p.wound_left) = (5., 3., 4.);
        beat(&mut w, 1, opponent);
        assert!(
            !w.players.contains_key(&opponent),
            "the beaten opponent leaves the ring"
        );
        if fight < FIGHTS {
            let me = &w.players[&1].character;
            assert_eq!(me.hp, me.max_hp(), "healed after fight {fight}");
            assert_eq!(
                (w.players[&1].stun, w.players[&1].wound_left),
                (0., 0.),
                "statuses cleared"
            );
            assert_eq!(counts(&w, 1, "arena_skald_20"), [fight as u32]);
            assert_eq!(w.gauntlets[0].opponent, None);
        }
    }
    seen.sort_by_key(|c| format!("{c:?}"));
    let mut all = [
        Class::Warrior,
        Class::Mage,
        Class::Assassin,
        Class::Priest,
        Class::Hunter,
    ];
    all.sort_by_key(|c| format!("{c:?}"));
    assert_eq!(seen, all, "one opponent of every class");
    assert!(w.gauntlets.is_empty());
    assert_eq!(w.players[&1].character.zone, SKALD);
    assert_eq!(counts(&w, 1, "arena_skald_20"), [5]);
    assert_eq!(w.players.len(), 1);
    w.step();
    assert!(
        !w.instances.iter().any(|i| i.zone == arena && i.active),
        "the copy is free again"
    );
    // Handed in: the blue weapon, experience and gold.
    offer(
        &mut w,
        1,
        "city_steward",
        "quest:claim:arena_skald_20:warrior_weapon_sword_l20_blue",
    );
    let me = &w.players[&1].character;
    assert_eq!(me.quantity("warrior_weapon_sword_l20_blue"), 1);
    assert!(
        me.gold > gold
            && me
                .quests
                .iter()
                .any(|g| g.id == "arena_skald_20" && g.claimed)
    );
    // Once: neither the same quest nor the same level at another giver can be taken again.
    offer(&mut w, 1, "city_steward", "gauntlet");
    assert!(w.gauntlets.is_empty());
}

#[test]
fn a_lost_timed_out_or_abandoned_run_resets_and_costs_nothing() {
    let mut w = world();
    let mut rx = hero(&mut w, 1, Class::Mage, 20, SKALD, "city_steward");
    offer(&mut w, 1, "city_steward", "quest:accept:arena_skald_20");
    let xp = w.players[&1].character.xp;
    let start = |w: &mut World, rx: &mut mpsc::Receiver<Value>| {
        offer(w, 1, "city_steward", "gauntlet");
        drain(rx);
        assert_eq!(w.gauntlets.len(), 1);
    };
    // Lost: the hero is the one that reaches the floor.
    start(&mut w, &mut rx);
    let opponent = until_opponent(&mut w, &mut rx, 1);
    for _ in 0..40 {
        if w.gauntlets[0].fallen.is_some() {
            break;
        }
        w.pvp_hit(opponent, 1, 1e9, false);
    }
    assert_eq!(
        w.players[&1].character.hp, 1.,
        "a duel's floor: nobody dies"
    );
    w.step();
    assert!(w.gauntlets.is_empty() && !w.players.contains_key(&opponent));
    let me = &w.players[&1].character;
    assert_eq!((me.zone, me.hp == me.max_hp(), me.xp), (SKALD, true, xp));
    assert_eq!(counts(&w, 1, "arena_skald_20"), [0]);
    // Timed out.
    start(&mut w, &mut rx);
    until_opponent(&mut w, &mut rx, 1);
    w.gauntlets[0].until = w.time;
    w.step();
    assert!(
        w.gauntlets.is_empty() && w.players.len() == 1 && w.players[&1].character.zone == SKALD
    );
    // Forfeited from the ring.
    start(&mut w, &mut rx);
    until_opponent(&mut w, &mut rx, 1);
    w.pvp_command(1, PvpCommand::ArenaLeave);
    assert!(
        w.gauntlets.is_empty() && w.players.len() == 1 && w.players[&1].character.zone == SKALD
    );
    // Logged out in the middle of a fight: nothing of the run is left.
    start(&mut w, &mut rx);
    let opponent = until_opponent(&mut w, &mut rx, 1);
    w.leave(1);
    assert!(w.gauntlets.is_empty() && w.players.is_empty() && !w.players.contains_key(&opponent));
    w.step();
    assert!(
        !w.instances
            .iter()
            .any(|i| w.is_arena_zone(i.zone) && i.active)
    );
}

#[test]
fn an_opponent_hurts_only_its_own_hero_and_runs_do_not_share_a_ring() {
    let mut w = world();
    let mut a = hero(&mut w, 1, Class::Warrior, 20, SKALD, "city_steward");
    let mut b = hero(&mut w, 2, Class::Hunter, 20, SKALD, "city_steward");
    for s in [1, 2] {
        offer(&mut w, s, "city_steward", "quest:accept:arena_skald_20");
        offer(&mut w, s, "city_steward", "gauntlet");
    }
    drain(&mut a);
    drain(&mut b);
    assert_eq!(w.gauntlets.len(), 2);
    assert_ne!(
        w.gauntlets[0].zone, w.gauntlets[1].zone,
        "a private ring each"
    );
    let (oa, ob) = (
        until_opponent(&mut w, &mut a, 1),
        until_opponent(&mut w, &mut b, 2),
    );
    assert!(w.pvp_legal(1, oa) && w.pvp_legal(2, ob));
    assert!(
        !w.pvp_legal(1, ob) && !w.pvp_legal(2, oa) && !w.pvp_legal(1, 2) && !w.pvp_legal(oa, ob)
    );
    // One arena trial per level, whichever giver it came from, and none above the hero's level.
    let mut c = hero(&mut w, 3, Class::Priest, 30, SKALD, "city_steward");
    offer(&mut w, 3, "city_steward", "quest:accept:arena_skald_20");
    assert_eq!(counts(&w, 3, "arena_skald_20"), [0]);
    let at = w.maps[NACRE]
        .npcs
        .iter()
        .find(|n| n.id == "nacre_archivist")
        .map(|n| (n.x, n.y))
        .unwrap();
    let p = w.players.get_mut(&3).unwrap();
    (p.character.zone, p.character.x, p.character.y) = (NACRE, at.0, at.1 + 0.5);
    offer(&mut w, 3, "nacre_archivist", "quest:accept:arena_nacre_20");
    assert!(
        counts(&w, 3, "arena_nacre_20").is_empty(),
        "level 20 was taken at the other giver"
    );
    offer(&mut w, 3, "nacre_archivist", "quest:accept:arena_nacre_30");
    assert_eq!(counts(&w, 3, "arena_nacre_30"), [0]);
    offer(&mut w, 3, "nacre_archivist", "quest:accept:arena_nacre_40");
    assert!(
        counts(&w, 3, "arena_nacre_40").is_empty(),
        "level 40 is not open at level 30"
    );
    drain(&mut c);
}

#[test]
fn an_opponent_closes_in_and_fights_back() {
    let mut w = world();
    let mut rx = hero(&mut w, 1, Class::Warrior, 20, SKALD, "city_steward");
    offer(&mut w, 1, "city_steward", "quest:accept:arena_skald_20");
    offer(&mut w, 1, "city_steward", "gauntlet");
    let opponent = until_opponent(&mut w, &mut rx, 1);
    let start = w.players[&1]
        .character
        .point()
        .distance(w.players[&opponent].character.point());
    assert!(start > 10., "they start across the ring");
    // The hero stands still: within a minute the opponent has walked up and landed a blow, or the run is already over.
    for _ in 0..1200 {
        w.step();
        drain(&mut rx);
        let me = &w.players[&1].character;
        if me.hp < me.max_hp() || w.gauntlets.is_empty() {
            break;
        }
    }
    let me = &w.players[&1].character;
    assert!(
        me.hp < me.max_hp() || w.gauntlets.is_empty(),
        "the opponent never hurt the hero"
    );
    if let Some(o) = w.players.get(&opponent) {
        assert!(
            w.players[&1]
                .character
                .point()
                .distance(o.character.point())
                < start
        );
    }
}

#[test]
fn every_opponent_wears_a_full_green_set_of_its_level() {
    for class in [
        Class::Warrior,
        Class::Mage,
        Class::Assassin,
        Class::Priest,
        Class::Hunter,
    ] {
        for level in [20, 30, 40, 50, 60, 70, 80, 90, 99] {
            let c = opponent_character(class, level, "Arena Test");
            let want = (level / 5 * 5).clamp(5, 95);
            let worn = c.worn_items();
            let green: Vec<_> = worn
                .iter()
                .filter(|i| {
                    i.rarity == "uncommon"
                        && i.required_level == want
                        && i.class.is_none_or(|k| k == class)
                })
                .collect();
            assert_eq!(
                green.len(),
                8,
                "{class:?} at {level}: {:?}",
                worn.iter().map(|i| &i.id).collect::<Vec<_>>()
            );
            assert_eq!(
                (c.level, c.hp, c.stat_points()),
                (level, c.max_hp(), 0),
                "{class:?} at {level}"
            );
            assert!(
                c.inventory
                    .iter()
                    .all(|s| item(&s.item).is_some_and(|i| i.kind != "potion")),
                "no potions"
            );
        }
    }
}

#[test]
fn an_opponent_has_seventy_percent_of_the_health_a_player_would() {
    let mut w = world();
    let mut rx = hero(&mut w, 1, Class::Warrior, 40, SKALD, "city_steward");
    offer(&mut w, 1, "city_steward", "quest:accept:arena_skald_40");
    offer(&mut w, 1, "city_steward", "gauntlet");
    let opponent = until_opponent(&mut w, &mut rx, 1);
    // The same blow on the same body, once as an opponent and once as an ordinary player.
    let loss = |w: &mut World| -> f64 {
        for _ in 0..80 {
            let max = w.players[&opponent].character.max_hp();
            w.players.get_mut(&opponent).unwrap().character.hp = max;
            w.pvp_hit(1, opponent, 400., false);
            let hp = w.players[&opponent].character.hp;
            if hp < max {
                return max - hp;
            }
        }
        panic!("every blow was dodged");
    };
    let scaled = loss(&mut w);
    w.players.get_mut(&opponent).unwrap().gauntlet = false;
    let plain = loss(&mut w);
    assert!(plain > 10., "a blow big enough to measure: {plain}");
    assert!(
        (scaled - plain / 0.7).abs() <= 1.5,
        "opponent lost {scaled}, a player {plain}"
    );
}

/// One class against the five opponents of a run, driven by the mercenaries' brain on both sides, `seeds` times: how many
/// runs were won and how many fights of each kind were won. Prints one line; `GAUNTLET_SEEDS` sets the number of runs.
fn measure(class: Class, level: u32) -> String {
    let seeds: u64 = std::env::var("GAUNTLET_SEEDS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(6);
    let (mut passed, mut fights, mut won_fights) = (0, 0, 0);
    for seed in 1..=seeds {
        let mut w = world();
        w.rng = seed;
        let mut rx = hero(&mut w, 1, class, level, SKALD, "city_steward");
        let quest = format!("arena_skald_{level}");
        w.players.get_mut(&1).unwrap().character.level = level.max(20);
        offer(&mut w, 1, "city_steward", &format!("quest:accept:{quest}"));
        offer(&mut w, 1, "city_steward", "gauntlet");
        assert_eq!(
            w.gauntlets.len(),
            1,
            "the run did not start for {class:?} at {level}"
        );
        let mut won_seen = 0;
        for _ in 0..60_000 {
            w.step();
            drain(&mut rx);
            let Some(run) = w.gauntlets.first() else {
                break;
            };
            won_seen = run.won;
            if let Some(opponent) = run.opponent {
                w.gauntlet_play(1, opponent);
            }
        }
        let ready = counts(&w, 1, &quest) == [5];
        passed += ready as u32;
        // Fights won: a won run is five; a lost run stopped at the wins it had when it ended.
        let wins = if ready { 5 } else { won_seen as u32 };
        won_fights += wins;
        fights += if ready { 5 } else { wins + 1 };
    }
    format!("RATE level {level} {class:?}: runs {passed}/{seeds}, fights {won_fights}/{fights}")
}
macro_rules! rates {
    ($($name:ident: $level:expr),*) => {$(
        #[test]
        #[ignore]
        fn $name() {
            for class in [Class::Warrior, Class::Mage, Class::Assassin, Class::Priest, Class::Hunter] {
                println!("{}", measure(class, $level));
            }
        }
    )*};
}
rates!(rates_20: 20, rates_30: 30, rates_40: 40, rates_50: 50, rates_60: 60, rates_70: 70, rates_80: 80, rates_90: 90, rates_99: 99);
