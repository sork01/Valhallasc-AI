//! Focused checks of Wardens 5–9; never simulates the rest of the raid.
use super::*;
fn threshold(r: &mut Rig, share: f64) {
    r.w.slimes[r.boss].hp = r.w.slimes[r.boss].max_hp * share;
    r.run(0.1);
}
fn tele(r: &Rig, field: &str) -> Vec<Value> {
    r.view()["tele"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|t| !t[field].is_null())
        .cloned()
        .collect()
}
fn maxhp(r: &Rig, s: u64) -> f64 {
    r.w.players[&s].character.max_hp()
}
#[test]
fn raid_warden_dagfinn_counts_continuous_holds_and_repeats_at_forty() {
    let mut r = Rig::new("cf_dagfinn", 10);
    r.run(0.1);
    assert!(r.view()["cast"].is_null());
    for share in [0.7, 0.4] {
        threshold(&mut r, share);
        assert_eq!(r.view()["cast"]["name"], "Two Valves");
        assert_eq!(r.w.hit_slime(r.boss, 1, 1e12, false), 0.);
        r.roles();
        r.run(9.7);
        assert!(tele(&r, "held").iter().all(|t| t["held"] == 0.));
        r.run(10.);
        assert!(
            tele(&r, "held")
                .iter()
                .all(|t| t["held"].as_f64().unwrap() > 9.)
        );
        r.run(11.);
        assert!(
            r.view()["cast"].is_null(),
            "both islands held twenty seconds"
        );
        assert!((1..=10).all(|s| r.hp(s) > 0.));
    }
    assert!(r.w.hit_slime(r.boss, 1, 10., false) > 0.);
}
#[test]
fn raid_warden_dagfinn_missing_people_reset_progress_and_failed_valve_wipes_crew() {
    let mut r = Rig::new("cf_dagfinn", 10);
    threshold(&mut r, 0.7);
    r.roles();
    r.run(15.);
    let side = if r.w.players[&1].character.x < 55. {
        0
    } else {
        1
    };
    let move_ids: Vec<_> =
        r.w.players
            .iter()
            .filter(|(_, p)| usize::from(p.character.x >= 55.) == side)
            .map(|(s, _)| *s)
            .take(3)
            .collect();
    for s in move_ids {
        r.put(
            s,
            Point {
                x: if side == 0 { 45. } else { 65. },
                y: 211.,
            },
        );
    }
    r.run(0.1);
    assert_eq!(tele(&r, "held")[side]["held"], 0.);
    r.run(20.);
    let failed: Vec<_> =
        r.w.players
            .values()
            .filter(|p| usize::from(p.character.x >= 55.) == side)
            .collect();
    assert!(failed.iter().all(|p| p.character.hp == 0.));
    assert!(
        r.w.players.values().all(|p| p.character.hp == 0.),
        "one failed valve wipes the participating crew, including the completed side"
    );
}
#[test]
fn raid_warden_dagfinn_lava_warning_and_copy_local_lift_reset() {
    let mut r = Rig::new("cf_dagfinn", 1);
    threshold(&mut r, 0.7);
    let hp = r.hp(1);
    r.run(9.5);
    assert_eq!(r.hp(1), hp);
    r.run(1.);
    assert_eq!(r.hp(1), 0.);
    let mut r = Rig::new("cf_dagfinn", 1);
    r.w.time = 2.;
    let lift = r.w.maps[r.zone]
        .portals
        .iter()
        .find(|p| p.id == "cf_lift_out")
        .unwrap()
        .clone();
    r.put(
        1,
        Point {
            x: lift.x,
            y: lift.y,
        },
    );
    r.w.use_portal(1);
    assert_eq!(
        r.w.players[&1].character.x, lift.x,
        "locked while Dagfinn lives"
    );
    r.w.slimes[r.boss].dead = true;
    r.w.use_portal(1);
    assert_eq!(
        r.w.players[&1].character.point(),
        Point {
            x: lift.tx,
            y: lift.ty
        }
    );
    assert_eq!(r.w.players[&1].character.zone, r.zone);
    let copy =
        r.w.instances
            .iter()
            .find(|i| i.template == 46 && i.zone != 46)
            .unwrap()
            .zone;
    r.w.respawn_instance_zone(copy);
    r.w.enter_instance(copy);
    let cb =
        r.w.slimes
            .iter()
            .find(|s| s.zone == copy && s.kind == "cf_dagfinn")
            .unwrap()
            .id;
    r.w.players.get_mut(&1).unwrap().character.zone = copy;
    r.w.time += 2.;
    r.put(
        1,
        Point {
            x: lift.x,
            y: lift.y,
        },
    );
    r.w.use_portal(1);
    assert_eq!(
        r.w.players[&1].character.x, lift.x,
        "other copy stays locked"
    );
    r.w.slimes[cb].dead = true;
    r.w.use_portal(1);
    assert_eq!(r.w.players[&1].character.zone, copy);
    assert_eq!(r.w.players[&1].character.x, lift.tx);
    let index = r.w.instances.iter().position(|i| i.zone == copy).unwrap();
    r.w.reset_instance(index);
    assert!(!r.w.slimes[cb].dead);
}
#[test]
fn raid_warden_thorbjorg_three_fuses_pass_by_real_contact_and_immunity() {
    let mut r = Rig::new("cf_thorbjorg", 10);
    r.run(10.2);
    assert_eq!(tele(&r, "bearer").len(), 3);
    // Separate everyone so only the intentionally touching pair can exchange.
    for s in 1..=10 {
        r.put(
            s,
            Point {
                x: 38. + s as f64 * 2.6,
                y: 108.,
            },
        );
    }
    let t = tele(&r, "bearer")[0].clone();
    let bearer = t["bearer"].as_str().unwrap().to_string();
    let receiver = t["receiver"].as_str().unwrap().to_string();
    let b =
        *r.w.players
            .iter()
            .find(|(_, p)| p.character.id == bearer)
            .unwrap()
            .0;
    let next =
        *r.w.players
            .iter()
            .find(|(_, p)| p.character.id == receiver)
            .unwrap()
            .0;
    r.run(7.9);
    let at = r.w.players[&b].character.point();
    r.put(
        b,
        Point {
            x: at.x,
            y: at.y + 3.,
        },
    );
    r.put(
        next,
        Point {
            x: at.x,
            y: at.y + 3.,
        },
    );
    r.run(0.1);
    let brands = tele(&r, "bearer");
    assert!(
        brands
            .iter()
            .any(|t| t["bearer"] == receiver && t["fuse"].as_f64().unwrap() > 7.8)
    );
    assert!(!brands.iter().any(|t| t["bearer"] == bearer));
    r.run(1.2);
    assert!(
        !tele(&r, "bearer").iter().any(|t| t["bearer"] == bearer),
        "giver cannot immediately take it back"
    );
}
#[test]
fn raid_warden_thorbjorg_expiry_kills_nearby_but_spares_other_halls_and_god() {
    let mut r = Rig::new("cf_thorbjorg", 10);
    r.w.players.get_mut(&2).unwrap().god = true;
    r.put(10, Point { x: 156., y: 121. });
    let hp = r.hp(10);
    r.run(25.9);
    assert!(r.hp(1) > 0., "warning plus fuse is not shortened");
    r.run(0.3);
    assert_eq!(r.hp(1), 0.);
    assert!(r.hp(2) > 0.);
    assert_eq!(r.hp(10), hp);
}
#[test]
fn raid_warden_ragnhild_grid_has_thirty_six_numbered_tiles_and_real_four_beats() {
    let mut r = Rig::new("cf_ragnhild", 10);
    r.run(10.2);
    let ts = tele(&r, "beat");
    assert_eq!(ts.len(), 36);
    assert!((1..=4).all(|n| ts.iter().any(|t| t["beat"] == n)));
    let hp = r.hp(1);
    r.roles();
    r.run(4.5);
    assert_eq!(r.hp(1), hp);
    for _ in 0..32 {
        r.roles();
        r.run(0.05);
    }
    assert!(
        (1..=10).all(|s| r.hp(s) == hp),
        "crossing the 1/2 boundary answers the four beats"
    );
    assert!(r.view()["cast"].is_null());
}
#[test]
fn raid_warden_ragnhild_idle_tiles_hurt_and_new_cue_changes_the_numbers() {
    let mut r = Rig::new("cf_ragnhild", 1);
    r.run(10.2);
    let tiles = tele(&r, "beat");
    let t = tiles.iter().find(|t| t["beat"] == 1).unwrap();
    let sh = &t["shapes"][0];
    r.put(
        1,
        Point {
            x: (sh["x0"].as_f64().unwrap() + sh["x1"].as_f64().unwrap()) * 0.5,
            y: (sh["y0"].as_f64().unwrap() + sh["y1"].as_f64().unwrap()) * 0.5,
        },
    );
    let hp = r.hp(1);
    r.run(5.);
    assert!(r.hp(1) < hp);
    r.run(13.);
    let next = tele(&r, "beat");
    assert_eq!(next.len(), 36);
    assert_ne!(tiles[0]["beat"], next[0]["beat"]);
}
fn carry_all(r: &mut Rig) {
    let points = match &r.w.boss.table["cf_orm"].mechanics[0].block {
        bm::Block::Carry(c) => c.points.clone(),
        _ => panic!(),
    };
    for s in 1..=10 {
        r.put(
            s,
            Point {
                x: points[(s - 1) as usize][0],
                y: points[(s - 1) as usize][1],
            },
        );
    }
    r.run(0.1);
}
#[test]
fn raid_warden_orm_ten_flasks_slow_carriers_and_six_throws_quench_fifteen_seconds() {
    let mut r = Rig::new("cf_orm", 10);
    r.run(0.1);
    let base = r.w.slimes[r.boss].hp;
    assert_eq!(r.w.hit_slime(r.boss, 1, 100., false), 50.);
    carry_all(&mut r);
    assert_eq!(tele(&r, "carrier").len(), 10);
    for s in 1..=10 {
        assert_eq!(r.w.forge_carry_speed(s), 0.6);
    }
    let at = r.w.slimes[r.boss].point();
    for s in 1..=6 {
        r.put(s, at);
    }
    r.run(0.1);
    assert_eq!(r.view()["cast"]["name"], "Quenched");
    assert_eq!(r.w.hit_slime(r.boss, 1, 100., false), 200.);
    assert!(r.w.slimes[r.boss].hp < base);
    assert_eq!(r.w.forge_carry_speed(7), 1.);
    r.run(15.1);
    assert_eq!(r.view()["cast"]["name"], "Molten");
    assert_eq!(
        tele(&r, "well").len() + tele(&r, "carrier").len(),
        10,
        "all flasks refill; fighters already at wells may immediately collect theirs"
    );
}
#[test]
fn raid_warden_orm_failed_throw_window_recovers_and_fallen_carrier_returns_flask() {
    let mut r = Rig::new("cf_orm", 10);
    r.run(0.1);
    carry_all(&mut r);
    let at = r.w.slimes[r.boss].point();
    for s in 1..=5 {
        r.put(s, at);
    }
    r.run(0.1);
    r.run(5.1);
    for s in 6..=10 {
        r.put(s, at);
    }
    r.run(0.1);
    assert_eq!(r.view()["cast"]["name"], "Molten");
    r.run(5.2);
    assert_eq!(
        tele(&r, "well").len(),
        10,
        "expired throws replenish a failed attempt"
    );
    carry_all(&mut r);
    r.w.players.get_mut(&1).unwrap().character.hp = 0.;
    r.run(0.1);
    assert_eq!(r.w.forge_carry_speed(1), 1.);
    assert_eq!(tele(&r, "well").len(), 1);
}
#[test]
fn raid_warden_hildr_warning_hold_fire_actual_reflection_and_expiry() {
    let mut r = Rig::new("cf_hildr", 10);
    r.run(15.2);
    assert!(!tele(&r, "reflect")[0]["reflect"].as_bool().unwrap());
    for s in 1..=10 {
        assert!(r.w.boss_play(s).unwrap().hold_fire);
    }
    let hp = r.hp(1);
    r.w.hit_slime(r.boss, 1, 100., false);
    assert_eq!(r.hp(1), hp);
    r.run(5.);
    assert_eq!(tele(&r, "reflect")[0]["reflect"], true);
    r.w.hit_slime(r.boss, 1, 100., false);
    assert!(r.hp(1) < hp);
    assert!((hp - r.hp(1) - (maxhp(&r, 1) * 0.9 * 0.55).round()).abs() < 1e-5);
    assert_eq!(r.hp(2), hp, "only the attacker is reflected");
    r.run(8.);
    let hp = r.hp(2);
    r.w.hit_slime(r.boss, 2, 100., false);
    assert_eq!(r.hp(2), hp);
}
#[test]
fn raid_warden_five_new_encounters_reset_and_have_real_orange_rewards() {
    for kind in [
        "cf_dagfinn",
        "cf_thorbjorg",
        "cf_ragnhild",
        "cf_orm",
        "cf_hildr",
    ] {
        let mut r = Rig::new(kind, 1);
        crate::bosssign::validate(kind, &r.w.signs[kind]).unwrap();
        bm::validate(kind, &r.w.boss.table[kind]).unwrap();
        assert!(!r.w.maps[46].sealed_template);
        r.run(16.);
        r.w.slimes[r.boss].state = "return".into();
        r.run(0.1);
        assert!(r.w.boss_mech_view(r.zone).is_empty());
        assert_eq!(r.w.forge_carry_speed(1), 1.);
        r.w.slimes[r.boss].state = "chase".into();
        r.w.slimes[r.boss].hp = r.w.slimes[r.boss].max_hp;
        r.run(0.1);
        let copy =
            r.w.instances
                .iter()
                .find(|i| i.template == 46 && i.zone != 46)
                .unwrap()
                .zone;
        assert!(r.w.boss_mech_view(copy).is_empty());
        r.w.end_boss_fight(r.boss);
        r.w.hit_slime(r.boss, 1, 1e13, false);
        assert!(r.w.slimes[r.boss].dead, "{kind}");
        let gear: Vec<_> =
            r.w.drops
                .iter()
                .filter_map(|d| d.gear.as_ref())
                .filter(|g| {
                    crate::items::item(&g.item)
                        .is_some_and(|i| i.source.as_deref() == Some("chained_forge"))
                })
                .collect();
        assert_eq!(gear.len(), 2, "{kind}");
        assert!(
            gear.iter()
                .all(|g| g.rarity == "legendary" && item(&g.item).unwrap().kind != "weapon")
        );
        assert!(!r.w.instance_cleared(r.zone));
    }
}

#[test]
fn raid_warden_orm_actual_walk_and_dash_are_slowed_and_reset_releases_flask() {
    let mut r = Rig::new("cf_orm", 10);
    r.run(0.1);
    carry_all(&mut r);
    let before = r.w.players[&1].character.point();
    let speed = r.w.players[&1].character.look.class.speed();
    let now = r.w.time;
    let p = r.w.players.get_mut(&1).unwrap();
    p.input = Point { x: 1., y: 0. };
    p.input_at = now;
    r.w.update_player(1);
    let after = r.w.players[&1].character.point();
    assert!((before.distance(after) - speed * TICK * 0.6).abs() < 1e-6);
    let p = r.w.players.get_mut(&1).unwrap();
    p.dash = 0.2;
    p.dash_speed = 15.;
    p.dash_direction = Point { x: 1., y: 0. };
    r.w.update_player(1);
    assert!((after.distance(r.w.players[&1].character.point()) - 15. * TICK * 0.6).abs() < 1e-6);
    r.w.end_boss_fight(r.boss);
    assert_eq!(r.w.forge_carry_speed(1), 1.);
}

#[test]
fn raid_warden_relay_brain_keeps_all_brands_moving_and_uses_the_whole_crew() {
    let mut r = Rig::new("cf_thorbjorg", 10);
    r.run(10.1);
    let mut bearers = BTreeSet::new();
    for _ in 0..810 {
        for t in tele(&r, "bearer") {
            bearers.insert(t["bearer"].as_str().unwrap().to_owned());
        }
        r.roles();
        r.run(TICK);
        assert!(
            (1..=10).all(|s| r.hp(s) > 0.),
            "a scripted handoff goal must permit real contact and two tiles of travel"
        );
    }
    assert_eq!(
        bearers.len(),
        10,
        "receivers rotate through all ten fighters"
    );
}

#[test]
fn raid_warden_new_schema_rejects_impossible_counts_and_unfair_timing() {
    let w = world();
    for kind in [
        "cf_dagfinn",
        "cf_thorbjorg",
        "cf_ragnhild",
        "cf_orm",
        "cf_hildr",
    ] {
        let mut bad = (**w.boss.table.get(kind).unwrap()).clone();
        match &mut bad.mechanics[0].block {
            bm::Block::Valves(v) => v.need = 6,
            bm::Block::Relay(r) => r.immunity = r.fuse,
            bm::Block::Grid(g) => g.cast = 1.,
            bm::Block::Carry(c) => c.need = 11,
            bm::Block::Reflect(r) => r.duration = -1.,
            _ => panic!(),
        }
        assert!(bm::validate(kind, &bad).is_err(), "{kind}");
    }
}

#[test]
fn raid_warden_leaving_the_court_cannot_cancel_a_cast_already_joined() {
    let outside = Point { x: 84., y: 272. };
    let mut r = Rig::new("cf_ragnhild", 1);
    r.run(10.1);
    r.put(1, outside);
    let hp = r.hp(1);
    r.run(4.7);
    assert_eq!(r.hp(1), hp);
    r.run(1.6);
    assert_eq!(
        r.hp(1),
        0.,
        "a joined dancer outside the grid is hit on each beat"
    );
    let mut r = Rig::new("cf_thorbjorg", 1);
    r.run(10.1);
    r.put(1, outside);
    r.run(15.5);
    assert!(r.hp(1) > 0.);
    r.run(1.);
    assert_eq!(r.hp(1), 0., "leaving does not discard a carried brand");
    let mut r = Rig::new("cf_dagfinn", 1);
    threshold(&mut r, 0.7);
    r.put(1, outside);
    r.run(35.1);
    assert_eq!(r.hp(1), 0., "leaving does not escape a failed hold");
}

#[test]
fn raid_warden_orm_can_reach_a_carrier_at_the_wells_with_real_projectiles() {
    let mut r = Rig::new("cf_orm", 1);
    r.run(0.1);
    let at = r.w.slimes[r.boss].point();
    r.put(
        1,
        Point {
            x: at.x + 7.,
            y: at.y,
        },
    );
    let ranged = Slime::ranged("cf_orm").expect("the anchored Warden must reach his wells");
    assert!(ranged.range >= 7.);
    assert_eq!(ranged.shots, 3);
    assert_eq!(r.w.forge_attack_scale(r.boss), 2.);
    let hp = r.hp(1);
    r.w.slimes[r.boss].damage = hp;
    let target = r.w.players[&1].character.point();
    r.w.fire_enemy_bolts(r.boss, target, &ranged);
    assert_eq!(r.w.enemy_bolts.len(), 3);
    for _ in 0..30 {
        r.w.update_enemy_bolts();
    }
    assert!(
        r.hp(1) < hp,
        "Molten's normal attack must reach beyond melee distance"
    );
}

#[test]
fn raid_warden_dagfinn_cannot_be_bypassed_by_stacking_one_island() {
    let mut r = Rig::new("cf_dagfinn", 10);
    threshold(&mut r, 0.7);
    for session in 1..=10 {
        r.put(session, Point { x: 49., y: 201. });
    }
    r.run(34.7);
    assert!((1..=10).all(|s| r.hp(s) > 0.));
    r.run(0.5);
    assert!(
        (1..=10).all(|s| r.hp(s) == 0.),
        "both islands must actually complete their holds"
    );
}
