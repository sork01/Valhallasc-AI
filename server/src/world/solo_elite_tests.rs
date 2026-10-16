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
    for map in w
        .maps
        .iter()
        .filter(|m| m.copies == 0 && m.template.is_none())
    {
        for q in map
            .quests
            .iter()
            .filter(|q| q.group && q.recommended_players >= 2)
        {
            for o in q.objectives.iter().filter(|o| o.kind == "kill") {
                if !(is_elite(&o.target) || is_boss(&o.target)) {
                    continue;
                }
                // Only monsters that live in the open world: a dungeon's mobs and bosses are quest targets too, but
                // they follow the rules of `dungeon_solo_tests`.
                let Some(spawn) = w.spawns.iter().position(|s| {
                    s.kind == o.target
                        && w.maps[s.zone].copies == 0
                        && w.maps[s.zone].template.is_none()
                }) else {
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
    // `ELITE_SOLO_KINDS=cinderlord,kraken` limits a run to those kinds (calibrating a few elites at a time).
    let only = std::env::var("ELITE_SOLO_KINDS").unwrap_or_default();
    found
        .into_values()
        .filter(|e| only.is_empty() || only.split(',').any(|k| k == e.kind))
        .collect()
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
    // The open world only: dungeon mobs and bosses follow `dungeon_solo_tests`. A floor, not an exact count.
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

/// How long a lone player may fight an elite before it counts as not killed: three minutes, long enough for a patient
/// player with potions, and the same for both rules ("too easy" and "possible").
const SOLO_CAP_SECONDS: f64 = 180.;

/// A lone character `above` levels over the elite, in `rarity` gear, with every potion and meal.
fn solo_case(e: &GroupElite, class: Class, rarity: &'static str, above: u32) -> Case {
    Case {
        consumables: true,
        rarity,
        target: Some(e.spawn),
        enemy_level: Some(e.level),
        cap: Some(SOLO_CAP_SECONDS),
        ..Case::new(class, e.level + above)
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

/// A test that has failed once has failed: by default the lone-player tests stop at the first violation.
/// `ELITE_SOLO_FAIL_FAST=0` collects every violation instead (used to calibrate the elites).
fn fail_fast() -> bool {
    std::env::var("ELITE_SOLO_FAIL_FAST").is_ok_and(|v| v != "0")
        || std::env::var("ELITE_SOLO_FAIL_FAST").is_err()
}

/// Runs every group elite against every class alone, `above` levels over it, in `rarity` gear, and returns how many
/// fights each elite lost to the lone player (kind -> wins).
///
/// `until_win` stops after the first lone win: of the whole run (the rule "nobody wins" has already failed) or, with
/// `per_elite`, of that elite only (the rule "somebody can win" is already met).
///
/// Every finished fight prints one line (run with `--nocapture`), so a long run shows its progress; a lone victory
/// is marked `SOLO KILL`.
fn lone_wins(
    rarity: &'static str,
    above: u32,
    until_win: bool,
    per_elite: bool,
) -> BTreeMap<String, u32> {
    let elites = group_elites();
    let classes = classes();
    let total = elites.len() * classes.len() * seeds() as usize;
    let (mut done, mut wins) = (0, BTreeMap::new());
    for e in &elites {
        let entry: &mut u32 = wins.entry(e.kind.clone()).or_default();
        for &class in &classes {
            for seed in 1..=seeds() {
                let (out, _) = run_once(&solo_case(e, class, rarity, above), seed);
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
                    "[{rarity}+{above} {done}/{total}] {} (level {}, {} players) vs lone {class:?} seed {seed}: {result}",
                    e.kind, e.level, e.players
                );
                *entry += u32::from(out.killed);
                if out.killed && until_win && !per_elite {
                    return wins;
                }
                if out.killed && until_win && per_elite {
                    break;
                }
            }
            if *entry > 0 && until_win && per_elite {
                break;
            }
        }
    }
    wins
}

// The owner's rule (2026-10-16): a group elite is not for a lone player at its own level in ordinary green gear, but
// it is soloable with good enough gear or about five levels above it.
#[test]
#[ignore = "slow (about 12 minutes on 4 cores): run scripts/elite-solo-parallel.sh"]
fn lone_player_in_green_gear_at_the_same_level_cannot_kill_a_group_elite() {
    let easy: Vec<_> = lone_wins(BASELINE_RARITY, 0, fail_fast(), false)
        .into_iter()
        .filter(|&(_, wins)| wins > 0)
        .map(|(kind, wins)| format!("{kind}: {wins} lone kills"))
        .collect();
    assert!(
        easy.is_empty(),
        "too easy for one player:\n{}",
        easy.join("\n")
    );
}

#[test]
#[ignore = "slow (about 12 minutes on 4 cores): run scripts/elite-solo-parallel.sh"]
fn lone_player_can_kill_every_group_elite_with_purple_gear_or_five_levels_above() {
    // Somebody winning once is enough, so each elite stops at its first lone win.
    let (purple, above) = (
        lone_wins("epic", 0, true, true),
        lone_wins(BASELINE_RARITY, 5, true, true),
    );
    let hopeless: Vec<_> = purple
        .iter()
        .filter(|&(kind, &wins)| wins == 0 && above[kind] == 0)
        .map(|(kind, _)| kind.clone())
        .collect();
    assert!(
        hopeless.is_empty(),
        "no lone class wins in purple gear or five levels above:\n{}",
        hopeless.join("\n")
    );
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
#[ignore = "slow: run scripts/elite-party-parallel.sh"]
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
            cap: Some(SOLO_CAP_SECONDS),
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
