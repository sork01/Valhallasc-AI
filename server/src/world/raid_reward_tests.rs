//! Focused rewards checks: no encounter grind or boss tuning.
use super::signature::Target;
use super::wyrd_tests::{at, join, place, world};
use super::*;

fn rig(class: Class) -> World {
    let mut w = world();
    let _ = join(&mut w, 1, class);
    let c = Character::mercenary(class, 99, "Forge Tester");
    w.players.get_mut(&1).unwrap().character = c;
    let key = format!("chainforged_{class:?}_weapon").to_lowercase();
    let c = &mut w.players.get_mut(&1).unwrap().character;
    c.add_item(&key, 1);
    c.equip_slots(&BTreeMap::from([("hands".into(), key)]))
        .unwrap();
    place(&mut w, 1, 1, at(60., 60.));
    w.players.get_mut(&1).unwrap().face = at(1., 0.);
    w.maps[1].objects.clear();
    for (n, s) in w.slimes.iter_mut().enumerate() {
        s.dead = n >= 3;
        if n < 3 {
            s.zone = 1;
            s.x = 61. + n as f64;
            s.y = 60.;
            s.hp = 1e9;
            s.max_hp = 1e9;
            s.state = "idle".into();
        }
    }
    w
}

#[test]
fn raid_rewards_all_damage_procs_are_capped_and_cannot_chain_or_repeat_early() {
    for class in [Class::Warrior, Class::Mage, Class::Assassin, Class::Hunter] {
        let mut w = rig(class);
        let basic = w.raid_attack_power(1) * DAMAGE_DEALT_SCALE;
        let before = w.slimes.iter().take(3).map(|s| s.hp).sum::<f64>();
        w.cur_skill = if class == Class::Mage {
            "fireball".into()
        } else {
            String::new()
        };
        for _ in 0..1000 {
            w.signature_hit(1, Target::Enemy(0), 1e6);
            if w.signature.cooldown.contains_key(&1) {
                break;
            }
        }
        assert!(
            w.signature.cooldown.contains_key(&1),
            "{class:?}: proc fired"
        );
        let pending = w.signature.pending.len();
        let hp = w.slimes[0].hp;
        for _ in 0..10 {
            w.signature_hit(1, Target::Enemy(0), 1e6);
        }
        assert_eq!(w.signature.pending.len(), pending);
        assert_eq!(w.slimes[0].hp, hp);
        w.cur_skill = "chainforged_proc".into();
        w.signature.cooldown.clear();
        w.signature_hit(1, Target::Enemy(0), 1e6);
        assert!(w.signature.cooldown.is_empty(), "no recursive proc");
        for _ in 0..120 {
            w.time += TICK;
            w.update_signatures();
        }
        let lost = before - w.slimes.iter().take(3).map(|s| s.hp).sum::<f64>();
        assert!(lost > 0., "{class:?}: actual damage");
        assert!(
            lost <= basic * 0.61 + 4.,
            "{class:?}: {lost} exceeds per-proc budget {basic}"
        );
    }
}

#[test]
fn raid_rewards_replacements_keep_skill_cost_cooldown_and_disappear_on_unequip() {
    for (class, id) in [
        (Class::Warrior, "earthshatter"),
        (Class::Mage, "arcaneward"),
        (Class::Assassin, "knifering"),
        (Class::Hunter, "arrowstorm"),
    ] {
        let mut w = rig(class);
        w.slimes[0].hp = 1e9;
        let before = w.slimes[0].hp;
        w.signature_skill(1, id);
        for _ in 0..400 {
            w.time += TICK;
            w.update_signatures();
        }
        assert!(w.slimes[0].hp < before, "{class:?}: granted addition works");
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.equip_slots(&BTreeMap::from([("hands".into(), "none".into())]))
            .unwrap();
        let hp = w.slimes[0].hp;
        w.signature_skill(1, id);
        for _ in 0..400 {
            w.time += TICK;
            w.update_signatures();
        }
        assert_eq!(w.slimes[0].hp, hp, "{class:?}: addition gone");
        assert!(w.players[&1].snapshot()["signatureWeapon"].is_null());
    }
}

#[test]
fn raid_rewards_priest_warmth_ward_and_pvp_heal_factor_are_bounded() {
    let mut w = rig(Class::Priest);
    w.players.get_mut(&1).unwrap().character.hp = 1.;
    w.signature_skill(1, "mend");
    assert_eq!(w.signature_heal_multiplier(1, &[1]), 1.10);
    assert_eq!(w.signature_heal_multiplier(1, &[1]), 1.);
    w.players.get_mut(&1).unwrap().pvp_fight = 10.;
    let max = w.players[&1].character.max_hp();
    for _ in 0..1000 {
        w.signature_healed(1, 1, 100.);
        if w.signature.cooldown.contains_key(&1) {
            break;
        }
    }
    let shield = w.players[&1].forge_ward;
    assert!(
        shield > 0.
            && shield <= max * 0.03 * pvp::PVP_DAMAGE_SCALE * pvp::PVP_PRIEST_HEAL_SCALE + 1e-6
    );
    w.signature_healed(1, 1, 100.);
    assert_eq!(w.players[&1].forge_ward, shield);
    w.signature.cooldown.clear();
    w.signature_healed(1, 1, 0.);
    assert!(w.signature.cooldown.is_empty(), "overheal grants no ward");
}

#[test]
fn raid_rewards_player_procs_obey_consent_cap_and_no_lifesteal() {
    let mut w = rig(Class::Assassin);
    let _ = join(&mut w, 2, Class::Warrior);
    w.players.get_mut(&2).unwrap().character =
        Character::mercenary(Class::Warrior, 99, "Other Tester");
    place(&mut w, 2, 1, at(61., 60.));
    let before = w.players[&2].character.hp;
    for _ in 0..20 {
        w.forge_hit(1, Target::Player(2), 1e9);
    }
    assert_eq!(w.players[&2].character.hp, before, "no consent, no hit");
    w.players.get_mut(&1).unwrap().pvp_flag = true;
    w.players.get_mut(&2).unwrap().pvp_flag = true;
    w.players.get_mut(&1).unwrap().character.hp = 10.;
    let before = w.players[&2].character.hp;
    let cap = before * 0.03;
    for _ in 0..20 {
        w.forge_hit(1, Target::Player(2), 1e9);
        if w.players[&2].character.hp < before {
            break;
        }
    }
    let lost = before - w.players[&2].character.hp;
    assert!(
        lost > 0. && lost <= cap,
        "legal, capped PvP hit {lost}/{cap}"
    );
    assert_eq!(w.players[&1].character.hp, 10., "no lifesteal");
    assert!(w.players[&1].pvp_fight > 0.);
}

#[test]
fn raid_rewards_loot_uses_saved_orange_copies_and_rebirth_multiplier() {
    for boost in [1, 5] {
        let mut w = rig(Class::Warrior);
        w.players.get_mut(&1).unwrap().character.rebirth_tiers = [0, 0, 0, 0, boost - 1];
        let owner = w.players[&1].character.id.clone();
        let at = w.players[&1].character.point();
        w.boss_loot(&owner, "cf_eldmarr", 1, at);
        let gear = w
            .drops
            .iter()
            .filter_map(|d| d.gear.as_ref())
            .collect::<Vec<_>>();
        assert_eq!(gear.len(), 4 * boost as usize);
        assert_eq!(
            gear.iter()
                .filter(|g| item(&g.item).unwrap().kind == "weapon")
                .count(),
            2 * boost as usize
        );
        for g in gear {
            assert_eq!(g.rarity, "legendary");
            let json = serde_json::to_string(g).unwrap();
            let saved: GearInstance = serde_json::from_str(&json).unwrap();
            assert_eq!(saved, *g);
        }
    }
}

#[test]
fn raid_rewards_real_casts_keep_the_original_skill_slot_cost_and_cooldown() {
    for (class, id) in [
        (Class::Warrior, "earthshatter"),
        (Class::Mage, "arcaneward"),
        (Class::Assassin, "knifering"),
        (Class::Priest, "mend"),
        (Class::Hunter, "arrowstorm"),
    ] {
        let mut w = rig(class);
        let p = w.players.get_mut(&1).unwrap();
        p.character.change_resource(1000.);
        p.character.hp = 1.;
        let skill = skills::find(class, id).unwrap().at_level(99);
        let resource = p.character.resource();
        let cooldown = skill.cooldown * p.character.cooldown_multiplier();
        w.use_skill(1, id, at(1., 0.));
        assert_eq!(
            w.players[&1].skill_cd.len(),
            1,
            "{class:?}: no extra slot or cooldown"
        );
        assert_eq!(w.players[&1].skill_cd[id], cooldown);
        if class != Class::Warrior {
            assert_eq!(w.players[&1].character.resource(), resource - skill.cost);
        }
    }
}

#[test]
fn raid_rewards_swapping_cancels_warmth_and_preserves_the_proc_cooldown() {
    let mut w = rig(Class::Priest);
    w.signature_skill(1, "mend");
    w.signature.cooldown.insert(1, w.time + 3.);
    w.message(
        1,
        ClientMessage::Equip {
            armor: None,
            weapon: None,
            slots: BTreeMap::from([("hands".into(), "none".into())]),
        },
    );
    assert!(w.signature.warm.is_empty());
    assert!(w.signature.cooldown.contains_key(&1));
    w.message(
        1,
        ClientMessage::Equip {
            armor: None,
            weapon: None,
            slots: BTreeMap::from([("hands".into(), "chainforged_priest_weapon".into())]),
        },
    );
    w.players.get_mut(&1).unwrap().character.hp = 1.;
    assert_eq!(w.signature_heal_multiplier(1, &[1]), 1.);
    assert!(w.signature.cooldown.contains_key(&1));
}

#[test]
fn raid_rewards_ember_ward_is_spent_by_monster_and_player_hits() {
    let mut w = rig(Class::Priest);
    let _ = join(&mut w, 2, Class::Warrior);
    w.players.get_mut(&2).unwrap().character =
        Character::mercenary(Class::Warrior, 99, "Ward Attacker");
    place(&mut w, 2, 1, at(61., 60.));
    let p = w.players.get_mut(&1).unwrap();
    p.forge_ward = 100.;
    p.forge_ward_left = 4.;
    let hp = p.character.hp;
    // A fixed one-damage floor, entirely absorbed by this weapon's ward.
    for _ in 0..30 {
        w.hurt_player(1, 1., at(61., 60.));
        if w.players[&1].forge_ward < 100. {
            break;
        }
    }
    assert!(w.players[&1].forge_ward < 100.);
    assert_eq!(w.players[&1].character.hp, hp);
    w.players.get_mut(&1).unwrap().pvp_flag = true;
    w.players.get_mut(&2).unwrap().pvp_flag = true;
    let before = w.players[&1].forge_ward;
    for _ in 0..30 {
        w.pvp_hit(2, 1, 1., false);
        if w.players[&1].forge_ward < before {
            break;
        }
    }
    assert!(w.players[&1].forge_ward < before);
    assert_eq!(w.players[&1].character.hp, hp);
}
