//! `DROP-EPIC-CHECK`: the purple roll is made per dropped set piece, through the real boss-loot path, at about 5%.
//! The per-piece stat, merge, refine, trade, sale and save checks live beside the code in `items.rs` and `trade.rs`.
use super::wyrd_tests::{at, calm, join, place, world};
use super::*;

fn kills(seed: u64, boss: &str, count: usize) -> (usize, usize, usize, usize) {
    let mut w = world();
    calm(&mut w);
    w.rng = seed;
    let _rx = join(&mut w, 1, Class::Warrior);
    place(&mut w, 1, 0, at(60., 60.));
    let owner = w.players[&1].character.id.clone();
    for _ in 0..count {
        w.boss_loot(&owner, boss, 0, at(60., 60.));
    }
    let pieces: Vec<_> = w
        .drops
        .iter()
        .filter(|d| {
            d.item
                .as_deref()
                .and_then(item)
                .is_some_and(|i| i.source.is_some())
        })
        .collect();
    let purple = pieces
        .iter()
        .filter(|d| d.gear.as_ref().is_some_and(|g| g.rarity == "epic"))
        .count();
    // Nothing but a purple copy carries a gear instance here, and a drop's pile shows its own rarity.
    let carried = pieces.iter().filter(|d| d.gear.is_some()).count();
    let purple_piles_coloured = pieces
        .iter()
        .filter(|d| d.gear.is_some() && d.col == "#b45cff")
        .count();
    assert_eq!(carried, purple);
    assert_eq!(purple_piles_coloured, purple, "the pile is coloured purple");
    (pieces.len(), purple, w.drops.len(), carried)
}

#[test]
fn boss_kills_roll_about_five_percent_purple_per_dropped_set_piece_and_not_per_kill() {
    assert_eq!(
        EPIC_SET_DROP_CHANCE, 0.05,
        "docs/epic-set-drops.md: 5% per dropped set piece"
    );
    for (boss, seed) in [("hollowking", 11), ("moonwell_echo", 29)] {
        let slots = boss_slots(boss).len();
        assert!(slots >= 2, "{boss} drops at least two set pieces per kill");
        let count = 1500;
        let (pieces, purple, _, _) = kills(seed, boss, count);
        assert_eq!(
            pieces,
            count * slots,
            "{boss}: every pool drops a set piece"
        );
        let rate = purple as f64 / pieces as f64;
        assert!(
            (rate - EPIC_SET_DROP_CHANCE).abs() < 0.015,
            "{boss}: {purple} of {pieces} set pieces were purple ({rate:.3})"
        );
        // Per kill the chance is higher than 5% because every pool rolls; it must not be 5% per kill.
        let per_kill = purple as f64 / count as f64;
        assert!(
            per_kill > EPIC_SET_DROP_CHANCE * (slots as f64 - 0.5) * 0.8,
            "{boss}: {per_kill:.3} purple per kill with {slots} pools"
        );
    }
}

#[test]
fn only_dungeon_set_pieces_can_ever_be_purple_copies() {
    for piece in ITEMS
        .iter()
        .filter(|i| i.source.is_none() || i.rarity != "rare")
    {
        assert!(
            set_piece_copy(piece, 0.).is_none(),
            "{} has no purple copy",
            piece.id
        );
    }
    assert!(
        ITEMS
            .iter()
            .filter(
                |i| i.rarity == "rare" && i.source.as_deref().is_some_and(|s| s != "orange_pool")
            )
            .all(|i| set_piece_copy(i, 0.).is_some())
    );
}
