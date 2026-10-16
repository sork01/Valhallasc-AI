//! Dungeon difficulty rules (owner, 2026-10-16): a lone player may or may not beat a single dungeon mob (not a
//! rule, only reported), but a pack of mobs must definitely kill a lone player, and so must a boss.
//!
//! The dungeons are the instance templates (`copies > 0`). A *boss* is any monster that appears once in its dungeon or
//! is its final boss; a *mob* is a kind that appears more than once. A *pack* is a group of three or more mobs whose
//! spawns chain together within `PACK_LINK` tiles of each other, which is how far they would wake each other. Every
//! fight is a lone character at the dungeon's level in the stated gear with every potion and meal, played with the
//! kill-time rotation (`ttk.rs`). Fights print one line each (run with `--nocapture`); a failure of a rule is marked.
use super::ttk::*;
use super::wyrd_tests::world;
use super::*;

/// A rule that has failed once has failed: by default each test stops at the first violation.
/// `DUNGEON_SOLO_FAIL_FAST=0` collects every violation (used to calibrate).
fn fail_fast() -> bool {
    std::env::var("DUNGEON_SOLO_FAIL_FAST").map_or(true, |v| v != "0")
}

/// How long a fight may last before it counts as not won or lost (the same three minutes as the elite rules).
const CAP_SECONDS: f64 = 180.;
const PACK_LINK: f64 = 10.;
const PACK_MIN: usize = 3;

#[derive(Clone, Debug)]
struct Dungeon {
    name: String,
    level: u32,
    /// One spawn per mob kind (the first one).
    mobs: Vec<(String, usize)>,
    /// Spawn ids of each pack of `PACK_MIN` or more mobs.
    packs: Vec<Vec<usize>>,
    bosses: Vec<(String, usize)>,
}

/// `DUNGEON_SOLO_DUNGEONS=undervault,moonwell` keeps only the dungeons whose name contains one of the words (calibration).
fn dungeons() -> Vec<Dungeon> {
    let wanted: Vec<String> = std::env::var("DUNGEON_SOLO_DUNGEONS")
        .unwrap_or_default()
        .split(',')
        .map(|w| w.trim().to_lowercase())
        .filter(|w| !w.is_empty())
        .collect();
    // `DUNGEON_SOLO_KINDS=hollowking,thrall` keeps only those bosses, mobs and the packs that contain one of them.
    let kinds: Vec<String> = std::env::var("DUNGEON_SOLO_KINDS")
        .unwrap_or_default()
        .split(',')
        .map(|k| k.trim().to_string())
        .filter(|k| !k.is_empty())
        .collect();
    let w = world();
    let mut out = vec![];
    for (zone, map) in w.maps.iter().enumerate() {
        if map.copies == 0 || map.template.is_some() {
            continue;
        }
        if !wanted.is_empty() && !wanted.iter().any(|w| map.name.to_lowercase().contains(w)) {
            continue;
        }
        let ids: Vec<usize> = (0..w.spawns.len())
            .filter(|&i| w.spawns[i].zone == zone)
            .collect();
        let mut count: BTreeMap<&str, usize> = BTreeMap::new();
        for &i in &ids {
            *count.entry(w.spawns[i].kind.as_str()).or_default() += 1;
        }
        let is_mob = |kind: &str| count[kind] > 1 && kind != map.final_boss && !is_boss(kind);
        let mut mobs: Vec<(String, usize)> = vec![];
        let mut bosses = vec![];
        for &i in &ids {
            let kind = &w.spawns[i].kind;
            if is_mob(kind) {
                if !mobs.iter().any(|(k, _)| k == kind) {
                    mobs.push((kind.clone(), i));
                }
            } else {
                bosses.push((kind.clone(), i));
            }
        }
        // Single-linkage clusters of mob spawns.
        let mob_ids: Vec<usize> = ids
            .iter()
            .copied()
            .filter(|&i| is_mob(&w.spawns[i].kind))
            .collect();
        let mut group: Vec<usize> = (0..mob_ids.len()).collect();
        for a in 0..mob_ids.len() {
            for b in a + 1..mob_ids.len() {
                let (pa, pb) = (&w.spawns[mob_ids[a]], &w.spawns[mob_ids[b]]);
                if (pa.x - pb.x).hypot(pa.y - pb.y) <= PACK_LINK {
                    let (from, to) = (group[b], group[a]);
                    for g in group.iter_mut().filter(|g| **g == from) {
                        *g = to;
                    }
                }
            }
        }
        let mut packs: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
        for (n, &g) in group.iter().enumerate() {
            packs.entry(g).or_default().push(mob_ids[n]);
        }
        let level = map.levels.map_or(map.min_level, |l| l[0]).max(1);
        let kept = |kind: &str| kinds.is_empty() || kinds.iter().any(|k| k == kind);
        let bosses: Vec<(String, usize)> = bosses.into_iter().filter(|(k, _)| kept(k)).collect();
        let mobs: Vec<(String, usize)> = mobs.into_iter().filter(|(k, _)| kept(k)).collect();
        out.push(Dungeon {
            name: map.name.clone(),
            level,
            mobs,
            packs: packs
                .into_values()
                .filter(|p| p.len() >= PACK_MIN)
                .filter(|p| p.iter().any(|&i| kept(&w.spawns[i].kind)))
                .collect(),
            bosses,
        });
    }
    out
}

fn seeds() -> u64 {
    std::env::var("DUNGEON_SOLO_SEEDS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(2)
}
/// `DUNGEON_SOLO_CLASS=mage` (or `mage,priest`) limits the runs to one class so `scripts/dungeon-solo-parallel.sh` can run them side by side.
fn classes() -> Vec<Class> {
    let wanted = std::env::var("DUNGEON_SOLO_CLASS").unwrap_or_default();
    let picked: Vec<Class> = CLASSES
        .into_iter()
        .filter(|c| {
            wanted.is_empty()
                || wanted
                    .split(',')
                    .any(|w| format!("{c:?}").eq_ignore_ascii_case(w.trim()))
        })
        .collect();
    assert!(!picked.is_empty(), "unknown class {wanted}");
    picked
}
fn case(d: &Dungeon, class: Class, rarity: &'static str, above: u32) -> Case {
    Case {
        consumables: true,
        rarity,
        enemy_level: Some(d.level),
        cap: Some(CAP_SECONDS),
        ..Case::new(class, d.level + above)
    }
}
fn describe(out: &Outcome) -> String {
    if out.killed {
        format!(
            "CLEARED in {:.0} s, lowest health {:.0}%",
            out.seconds,
            out.lowest_hp_fraction * 100.
        )
    } else if out.died {
        format!(
            "died after {:.0} s, enemy at {:.0}%",
            out.seconds,
            out.enemy_left * 100.
        )
    } else {
        format!(
            "survived {:.0} s, enemy at {:.0}%",
            out.seconds,
            out.enemy_left * 100.
        )
    }
}

#[test]
fn the_dungeons_are_found_with_mobs_packs_and_bosses() {
    let list = dungeons();
    assert!(list.len() >= 15, "only {} dungeons", list.len());
    let undervault = list.iter().find(|d| d.name == "The Undervault").unwrap();
    assert_eq!(undervault.level, 20);
    assert!(undervault.mobs.len() >= 3 && undervault.packs.len() >= 8);
    assert!(undervault.bosses.iter().any(|(k, _)| k == "hollowking"));
    assert!(
        list.iter()
            .all(|d| !d.mobs.is_empty() && d.bosses.len() >= 3)
    );
    assert!(list.iter().map(|d| d.packs.len()).sum::<usize>() >= 30);
}

/// Not a rule: a single mob may be soloable or not. This only prints how each class fares, one line per fight.
#[test]
#[ignore = "report only: run scripts/dungeon-solo-parallel.sh"]
fn report_how_a_lone_player_fares_against_single_dungeon_mobs() {
    let mut done = 0;
    for d in dungeons() {
        for (kind, spawn) in &d.mobs {
            for class in classes() {
                for seed in 1..=seeds() {
                    let mut c = case(&d, class, BASELINE_RARITY, 0);
                    c.target = Some(*spawn);
                    let (out, _) = run_once(&c, seed);
                    done += 1;
                    eprintln!(
                        "[mob {done}] {} L{} {kind} vs lone {class:?} seed {seed}: {}",
                        d.name,
                        d.level,
                        describe(&out)
                    );
                }
            }
        }
    }
}

#[test]
#[ignore = "slow: run scripts/dungeon-solo-parallel.sh"]
fn a_dungeon_pack_kills_a_lone_player() {
    let (mut failed, mut done) = (vec![], 0);
    for d in dungeons() {
        for pack in &d.packs {
            for class in classes() {
                for seed in 1..=seeds() {
                    let out = run_pack_once(&case(&d, class, BASELINE_RARITY, 0), pack, seed);
                    done += 1;
                    eprintln!(
                        "[pack {done}] {} L{} pack of {} vs lone {class:?} seed {seed}: {}{}",
                        d.name,
                        d.level,
                        pack.len(),
                        describe(&out),
                        if out.died {
                            ""
                        } else {
                            "  <-- LONE PLAYER SURVIVED A PACK"
                        }
                    );
                    if !out.died {
                        failed.push(format!(
                            "{} pack of {}: lone {class:?} seed {seed} {}",
                            d.name,
                            pack.len(),
                            describe(&out)
                        ));
                        if fail_fast() {
                            panic!("a pack must kill a lone player:\n{}", failed.join("\n"));
                        }
                    }
                }
            }
        }
    }
    assert!(
        failed.is_empty(),
        "a pack must kill a lone player:\n{}",
        failed.join("\n")
    );
}

/// A boss must kill a lone player: in every fight, in green or purple gear at the dungeon's level, the character is the
/// one who dies. Purple gear five levels above may clear it (owner, 2026-10-16: fine), so it is only reported. Bosses
/// a lone player can kill get a soft enrage (`world/enrage.txt`); Choir, Colossus, Hollowking, Bloom Heart and Solstice
/// Heart have none, see `docs/dungeon-solo-report.md`.
#[test]
#[ignore = "slow: run scripts/dungeon-solo-parallel.sh"]
fn a_dungeon_boss_kills_a_lone_player() {
    let (mut failed, mut done) = (vec![], 0);
    for d in dungeons() {
        for (kind, spawn) in &d.bosses {
            for (rarity, above) in [(BASELINE_RARITY, 0), ("epic", 0)] {
                for class in classes() {
                    for seed in 1..=seeds() {
                        let mut c = case(&d, class, rarity, above);
                        c.target = Some(*spawn);
                        let (out, _) = run_once(&c, seed);
                        done += 1;
                        eprintln!(
                            "[boss {done}] {} L{} {kind} vs lone {class:?} {rarity}+{above} seed {seed}: {}{}",
                            d.name,
                            d.level,
                            describe(&out),
                            if out.died {
                                ""
                            } else {
                                "  <-- LONE PLAYER SURVIVED A BOSS"
                            }
                        );
                        if !out.died {
                            failed.push(format!(
                                "{} {kind}: lone {class:?} {rarity}+{above} seed {seed} {}",
                                d.name,
                                describe(&out)
                            ));
                            if fail_fast() {
                                panic!("a boss must kill a lone player:\n{}", failed.join("\n"));
                            }
                        }
                    }
                }
            }
        }
    }
    assert!(
        failed.is_empty(),
        "a boss must kill a lone player:\n{}",
        failed.join("\n")
    );
}

const PARTY: [Class; 5] = [
    Class::Warrior,
    Class::Priest,
    Class::Mage,
    Class::Hunter,
    Class::Assassin,
];

/// The control for both rules: a party of five in ordinary green gear at the dungeon's level, with every potion and
/// meal, must beat every pack and every boss in the dungeon (`DUNGEON_PARTY_RARITY=epic` tries purple gear).
/// `DUNGEON_PARTY_SHARD=i/n` runs every n-th dungeon so shards can run side by side.
#[test]
#[ignore = "slow: run scripts/dungeon-party-parallel.sh"]
fn a_party_of_five_beats_every_dungeon_pack_and_boss() {
    let rarity = match std::env::var("DUNGEON_PARTY_RARITY").ok().as_deref() {
        Some("epic") => "epic",
        Some("rare") => "rare",
        _ => BASELINE_RARITY,
    };
    let (shard, shards): (usize, usize) = std::env::var("DUNGEON_PARTY_SHARD")
        .ok()
        .and_then(|v| {
            let (i, n) = v.split_once('/')?;
            Some((i.parse().ok()?, n.parse().ok()?))
        })
        .unwrap_or((0, 1));
    let mut failed = vec![];
    for (index, d) in dungeons().into_iter().enumerate() {
        if index % shards != shard {
            continue;
        }
        let mut groups: Vec<(String, Vec<usize>)> = d
            .packs
            .iter()
            .map(|p| (format!("pack of {}", p.len()), p.clone()))
            .collect();
        groups.extend(
            d.bosses
                .iter()
                .map(|(k, s)| (format!("boss {k}"), vec![*s])),
        );
        for (what, ids) in groups {
            let case = Case {
                consumables: true,
                rarity,
                enemy_level: Some(d.level),
                cap: Some(CAP_SECONDS),
                ..Case::new(PARTY[0], d.level)
            };
            let runs: Vec<_> = (1..=seeds())
                .map(|seed| run_party_pack_once(&case, &PARTY, &ids, seed))
                .collect();
            let wins = runs.iter().filter(|r| r.killed).count() as u64;
            let detail = runs
                .iter()
                .map(|r| {
                    format!(
                        "{:.0} s, {} died, enemy at {:.0}%",
                        r.seconds,
                        r.deaths,
                        r.enemy_left * 100.
                    )
                })
                .collect::<Vec<_>>()
                .join("; ");
            let bad = wins * 2 < seeds();
            eprintln!(
                "[party5 {rarity}] {} L{} {what}: five players won {wins} of {} runs ({detail}){}",
                d.name,
                d.level,
                seeds(),
                if bad {
                    "  <-- PARTY OF FIVE CANNOT WIN"
                } else {
                    ""
                }
            );
            if bad {
                failed.push(format!("{} {what}: won {wins} of {}", d.name, seeds()));
                if fail_fast() {
                    panic!("a party of five must beat it:\n{}", failed.join("\n"));
                }
            }
        }
    }
    assert!(
        failed.is_empty(),
        "a party of five must beat every pack and boss:\n{}",
        failed.join("\n")
    );
}

/// Do dungeon monsters actually hurt? `DUNGEON_SOLO_DUNGEONS=undervault DUNGEON_SOLO_CLASS=priest cargo test dungeon_probe -- --ignored --nocapture`
/// prints damage, hits and health for every boss and the first mob of the chosen dungeons, in green and purple gear.
#[test]
#[ignore = "debug probe"]
fn dungeon_probe() {
    for d in dungeons() {
        for (kind, spawn) in d.bosses.iter().chain(d.mobs.iter().take(1)) {
            for class in classes() {
                for rarity in [BASELINE_RARITY, "epic"] {
                    let mut c = case(&d, class, rarity, 0);
                    c.target = Some(*spawn);
                    let (out, summary) = run_once(&c, 1);
                    eprintln!(
                        "{} L{} {kind} vs {class:?} {rarity}: enemy hp {:.0} dmg {:.0} level {}; hero hp {:.0}; took {:.0} in {} hits, lowest {:.0}%, {}",
                        d.name,
                        d.level,
                        summary.enemy_hp,
                        summary.enemy_damage,
                        summary.enemy_level,
                        summary.character_hp,
                        out.damage_taken,
                        out.hits_taken,
                        out.lowest_hp_fraction * 100.,
                        describe(&out)
                    );
                }
            }
        }
    }
}

/// Prints what each dungeon holds, for planning: `cargo test dungeon_inventory -- --ignored --nocapture`.
#[test]
#[ignore = "report only"]
fn dungeon_inventory() {
    let w = world();
    for d in dungeons() {
        let packs: Vec<String> = d
            .packs
            .iter()
            .map(|p| {
                let mut kinds: BTreeMap<&str, usize> = BTreeMap::new();
                for &i in p {
                    *kinds.entry(w.spawns[i].kind.as_str()).or_default() += 1;
                }
                kinds
                    .iter()
                    .map(|(k, n)| format!("{n}x{k}"))
                    .collect::<Vec<_>>()
                    .join("+")
            })
            .collect();
        eprintln!(
            "{} L{}: mobs {:?}; bosses {:?}; {} packs: {}",
            d.name,
            d.level,
            d.mobs.iter().map(|m| &m.0).collect::<Vec<_>>(),
            d.bosses.iter().map(|m| &m.0).collect::<Vec<_>>(),
            packs.len(),
            packs.join(", ")
        );
    }
}
