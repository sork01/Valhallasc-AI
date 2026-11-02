//! Focused owner-reported pickup and gate regressions. No combat or grinding.
use super::wyrd_tests::{join, world};
use super::*;

#[test]
fn owner_fixes_unfittable_bag_stays_put_solo_and_party_with_full_inventory() {
    for party in [false, true] {
        let mut w = world();
        let _a = join(&mut w, 1, Class::Warrior);
        let _b = party.then(|| join(&mut w, 2, Class::Mage));
        for p in w.players.values_mut() {
            p.character.inventory.clear();
            p.character.bags = vec!["linen_satchel".into(); 4];
            p.character.x = 30.;
            p.character.y = 30.;
            let capacity = p.character.bag_capacity();
            for i in ITEMS.iter().filter(|i| i.kind == "material").take(capacity) {
                p.character.add_item(&i.id, 1);
            }
            assert_eq!(p.character.bag_used(), capacity);
        }
        let owner = w.players[&1].character.id.clone();
        if party {
            let id = w.players[&2].character.id.clone();
            w.social(
                1,
                SocialCommand::PartyInvite {
                    id: Some(id),
                    name: None,
                },
            );
            w.social(2, SocialCommand::PartyAccept { id: owner.clone() });
            assert_eq!(w.party_mates(&owner).len(), 2);
        }
        let point = Point { x: 32., y: 30. };
        w.loot_drop(&owner, 0, point, "linen_satchel");
        w.drops[0].t = 1.;
        for n in 0..30 {
            w.players.get_mut(&1).unwrap().character.x = 30. + f64::from(n % 5) * 0.2;
            w.update_drops();
            assert_eq!(
                w.drops[0].point().distance(point),
                0.,
                "refused magnet moved pile"
            );
        }
        assert!(
            w.loot_turns.is_empty(),
            "preflight must not consume party turns"
        );
        assert_eq!(w.players[&1].character.bags.len(), 4);
        if party {
            w.players.get_mut(&2).unwrap().character.bags.pop();
            for _ in 0..10 {
                w.update_drops();
            }
            assert!(
                w.drops.is_empty(),
                "party member with a free bag slot can take it"
            );
            assert_eq!(w.players[&2].character.bags.len(), 4);
        }
    }
}

#[test]
fn owner_fixes_wider_gate_approach_keeps_arrivals_and_access_rules() {
    let mut w = world();
    let _rx = join(&mut w, 1, Class::Warrior);
    let portal = w.maps[0]
        .portals
        .iter()
        .find(|p| p.to == 1)
        .unwrap()
        .clone();
    let side = portal.walk.unwrap();
    let length = f64::from(side[0]).hypot(f64::from(side[1]));
    let direction = Point {
        x: f64::from(side[0]) / length,
        y: f64::from(side[1]) / length,
    };
    let here = Point {
        x: portal.x - direction.x * 2.6,
        y: portal.y - direction.y * 2.6,
    };
    assert!(
        here.distance(Point {
            x: portal.x,
            y: portal.y
        }) > portal.r
    );
    let p = w.players.get_mut(&1).unwrap();
    p.character.x = here.x;
    p.character.y = here.y;
    p.character.level = 10;
    p.input = direction;
    p.moving = true;
    p.portal_at = -99.;
    w.use_portal(1);
    assert_eq!(
        w.players[&1].character.zone, 1,
        "approach just outside the old disc should cross"
    );
    w.use_portal(1);
    assert_eq!(
        w.players[&1].character.zone, 1,
        "cooldown prevents immediate bounce"
    );
    w.time += PORTAL_DELAY + 1.;
    w.use_portal(1);
    assert_eq!(
        w.players[&1].character.zone, 1,
        "outward movement after arrival must not bounce"
    );
    // The same wider approach still honors the destination level requirement.
    w.maps[1].min_level = 20;
    let p = w.players.get_mut(&1).unwrap();
    p.character.zone = 0;
    p.character.x = here.x;
    p.character.y = here.y;
    p.moving = true;
    p.input = direction;
    p.portal_at = -99.;
    w.use_portal(1);
    assert_eq!(w.players[&1].character.zone, 0);
}
