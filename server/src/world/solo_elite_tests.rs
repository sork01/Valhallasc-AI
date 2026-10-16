//! `ELITE-SOLO-TEST`: an elite or boss that its quest recommends 2 or more players for must not die to one player.
//!
//! The list comes from the quests in `world/map.txt` (`group` and `recommendedPlayers` of 2 or more) and the kill
//! objectives they name, so a new group elite joins the check without a hand-typed entry. Each kind is fought at its
//! quest's level by a lone character of every class using the kill-time rotation and every potion and meal. The
//! control is a party of exactly the recommended size, so a pass cannot just mean the fight is broken.
use super::ttk::*;
use super::wyrd_tests::world;
use super::*;

/// One group elite: the monster kind, the spawn the harness fights, the quest level and the party it wants.
#[derive(Clone, Debug)]
struct GroupElite {
    kind: String,
    spawn: usize,
    level: u32,
    players: u32,
}

fn group_elites() -> Vec<GroupElite> {
    let w = world();
    let mut found: BTreeMap<String, GroupElite> = BTreeMap::new();
    for map in &w.maps {
        for q in map
            .quests
            .iter()
            .filter(|q| q.group && q.recommended_players >= 2)
        {
            for o in q.objectives.iter().filter(|o| o.kind == "kill") {
                if !(is_elite(&o.target) || is_boss(&o.target)) {
                    continue;
                }
                let Some(spawn) = w.spawns.iter().position(|s| s.kind == o.target) else {
                    continue;
                };
                let entry = found.entry(o.target.clone()).or_insert(GroupElite {
                    kind: o.target.clone(),
                    spawn,
                    level: q.level,
                    players: 0,
                });
                entry.players = entry.players.max(q.recommended_players);
                entry.level = entry.level.max(q.level);
            }
        }
    }
    found.into_values().collect()
}

const PARTY: [Class; 5] = [
    Class::Warrior,
    Class::Priest,
    Class::Mage,
    Class::Hunter,
    Class::Assassin,
];

fn seeds() -> u64 {
    std::env::var("ELITE_SOLO_SEEDS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(2)
}

#[test]
fn every_group_elite_is_found_from_the_quests() {
    let list = group_elites();
    // A floor, not an exact count: new elites only add to it.
    assert!(list.len() >= 40, "only {} group elites found", list.len());
    for kind in [
        "cinderlord",
        "gloomroot",
        "oakhorn",
        "kraken",
        "mirrorqueen",
    ] {
        assert!(list.iter().any(|e| e.kind == kind), "{kind} is missing");
    }
    assert!(list.iter().all(|e| (2..=5).contains(&e.players)));
    assert_eq!(
        list.iter()
            .find(|e| e.kind == "cinderlord")
            .unwrap()
            .players,
        2
    );
}

fn solo_case(e: &GroupElite, class: Class, rarity: &'static str) -> Case {
    Case {
        consumables: true,
        rarity,
        target: Some(e.spawn),
        ..Case::new(class, e.level)
    }
}

/// `ELITE_SOLO_CLASS=mage` limits the lone-player runs to one class, so `scripts/elite-solo-parallel.sh` can run one
/// process per class at the same time.
fn classes() -> Vec<Class> {
    let wanted = std::env::var("ELITE_SOLO_CLASS").unwrap_or_default();
    let picked: Vec<Class> = CLASSES
        .into_iter()
        .filter(|c| wanted.is_empty() || format!("{c:?}").eq_ignore_ascii_case(&wanted))
        .collect();
    assert!(!picked.is_empty(), "unknown class {wanted}");
    picked
}

/// Runs every group elite against every class alone in `rarity` gear and returns the lone victories.
///
/// Every finished fight prints one line (run with `--nocapture`), so a long run shows its progress; a lone victory
/// is marked `SOLO KILL`.
fn solo_victories(rarity: &'static str) -> Vec<String> {
    let elites = group_elites();
    let classes = classes();
    let total = elites.len() * classes.len() * seeds() as usize;
    let (mut done, mut wins) = (0, vec![]);
    for e in &elites {
        for &class in &classes {
            for seed in 1..=seeds() {
                let (out, _) = run_once(&solo_case(e, class, rarity), seed);
                done += 1;
                let result = if out.killed {
                    format!("SOLO KILL in {:.0} s", out.seconds)
                } else if out.died {
                    format!(
                        "died after {:.0} s, elite at {:.0}%",
                        out.seconds,
                        out.enemy_left * 100.
                    )
                } else {
                    format!(
                        "survived {:.0} s, elite at {:.0}%",
                        out.seconds,
                        out.enemy_left * 100.
                    )
                };
                eprintln!(
                    "[{rarity} {done}/{total}] {} (level {}, {} players) vs lone {class:?} seed {seed}: {result}",
                    e.kind, e.level, e.players
                );
                if out.killed {
                    wins.push(format!(
                        "{} (level {}, {} players): a lone {class:?} won in {:.0} s, {rarity} gear",
                        e.kind, e.level, e.players, out.seconds
                    ));
                }
            }
        }
    }
    wins
}

#[test]
#[ignore = "slow, and red until ELITE-SOLO-FIX: run scripts/elite-solo-parallel.sh"]
fn no_lone_player_in_green_gear_kills_a_group_elite() {
    let wins = solo_victories(BASELINE_RARITY);
    assert!(wins.is_empty(), "solo kills:\n{}", wins.join("\n"));
}

#[test]
#[ignore = "slow, and red until ELITE-SOLO-FIX: run scripts/elite-solo-parallel.sh"]
fn no_lone_player_in_purple_gear_kills_a_group_elite() {
    let wins = solo_victories("epic");
    assert!(wins.is_empty(), "solo kills:\n{}", wins.join("\n"));
}

/// The party control wears `ELITE_PARTY_RARITY` gear (purple by default, the best ordinary set, the same tier the
/// lone-player comparison uses) and `ELITE_PARTY_SHARD=i/n` runs every n-th elite, so shards can run side by side.
fn party_rarity() -> &'static str {
    match std::env::var("ELITE_PARTY_RARITY").ok().as_deref() {
        Some("uncommon") => "uncommon",
        Some("rare") => "rare",
        _ => "epic",
    }
}
fn shard() -> (usize, usize) {
    std::env::var("ELITE_PARTY_SHARD")
        .ok()
        .and_then(|v| {
            let (i, n) = v.split_once('/')?;
            Some((i.parse().ok()?, n.parse().ok()?))
        })
        .unwrap_or((0, 1))
}

#[test]
#[ignore = "slow, and red until ELITE-SOLO-FIX: run scripts/elite-party-parallel.sh"]
fn a_party_of_the_recommended_size_kills_each_group_elite() {
    let (shard, shards) = shard();
    let mut failed = vec![];
    for (index, e) in group_elites().into_iter().enumerate() {
        if index % shards != shard {
            continue;
        }
        let members = &PARTY[..e.players as usize];
        let case = Case {
            consumables: true,
            rarity: party_rarity(),
            target: Some(e.spawn),
            ..Case::new(members[0], e.level)
        };
        let kills = (1..=seeds())
            .filter(|&seed| run_party_once(&case, members, seed))
            .count() as u64;
        eprintln!(
            "[party {} {}] {} (level {}): {} players killed it in {kills} of {} runs{}",
            party_rarity(),
            index + 1,
            e.kind,
            e.level,
            e.players,
            seeds(),
            if kills * 2 < seeds() {
                "  <-- PARTY CANNOT WIN"
            } else {
                ""
            }
        );
        if kills * 2 < seeds() {
            failed.push(format!(
                "{} (level {}): {} players killed it in {kills} of {} runs",
                e.kind,
                e.level,
                e.players,
                seeds()
            ));
        }
    }
    assert!(
        failed.is_empty(),
        "a full party cannot win:\n{}",
        failed.join("\n")
    );
}
