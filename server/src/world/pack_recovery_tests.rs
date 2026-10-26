//! Short death/recovery sequences; no encounter balance or kill-time runs.
use super::wyrd_tests::{at, calm, join, place, world};
use super::*;

struct Rig {
    w: World,
    _rx: mpsc::Receiver<Value>,
    mercs: Vec<u64>,
    enemies: Vec<usize>,
    zone: usize,
}
impl Rig {
    fn new(zone: usize) -> Self {
        let mut w = world();
        calm(&mut w);
        let rx = join(&mut w, 1, Class::Warrior);
        w.players.get_mut(&1).unwrap().character.level = w.dungeon_level(zone);
        w.enter_instance(zone);
        let enemies: Vec<_> = w
            .spawns
            .iter()
            .enumerate()
            .filter(|(_, s)| s.zone == zone && s.ambush.is_none() && !is_boss(&s.kind))
            .take(3)
            .map(|(id, _)| id)
            .collect();
        let point = at(w.spawns[enemies[0]].x + 3., w.spawns[enemies[0]].y + 3.);
        place(&mut w, 1, zone, point);
        let owner = w.players[&1].character.id.clone();
        for class in [Class::Mage, Class::Hunter] {
            w.place_mercenary(
                &owner,
                class,
                w.dungeon_level(zone),
                zone,
                point,
                w.maps[zone].raid,
                None,
            )
            .unwrap();
        }
        let mercs = w.players.keys().filter(|&&s| s != 1).copied().collect();
        for &id in &enemies {
            w.slimes[id] = Slime::with_level(id, &w.spawns[id], w.dungeon_level(zone));
            let s = &mut w.slimes[id];
            s.state = "chase".into();
            s.target = Some(1);
            s.damage = 0.;
        }
        w.update_pack_fights();
        Self {
            w,
            _rx: rx,
            mercs,
            enemies,
            zone,
        }
    }
    fn kill(&mut self, session: u64) {
        // Keep the lethal-hit fixture deterministic without bypassing real damage/death handling.
        self.w.players.get_mut(&session).unwrap().buffs.push(Buff {
            id: "test-no-dodge".into(),
            kind: BuffKind::Dodge,
            amount: -1.,
            left: 1.,
            time: 1.,
        });
        self.w.players.get_mut(&session).unwrap().last_hurt = -99.;
        self.w
            .hurt_player_by(session, 1e12, at(0., 0.), "cf_brute", 99);
        assert_eq!(self.w.players[&session].character.hp, 0.);
        self.w.update_pack_fights();
    }
    fn respawn_owner(&mut self) {
        self.w.players.get_mut(&1).unwrap().dead_time = 3.2;
        self.w.update_player(1);
        assert!(self.w.players[&1].character.hp > 0.);
    }
}

#[test]
fn pack_recovery_owner_returns_to_entrance_while_hires_keep_fighting() {
    for zone in [5, 46] {
        let mut r = Rig::new(zone);
        r.w.instances
            .iter_mut()
            .find(|i| i.zone == zone)
            .unwrap()
            .rally = Some(at(151., 45.));
        let positions: Vec<_> = r
            .mercs
            .iter()
            .map(|s| r.w.players[s].character.point())
            .collect();
        r.kill(1);
        r.respawn_owner();
        assert!(
            r.w.players[&1]
                .character
                .point()
                .distance(r.w.maps[zone].spawn)
                < 1.
        );
        for &session in &r.mercs {
            r.w.players.get_mut(&session).unwrap().combat_left = 0.;
        }
        r.w.update_mercenaries();
        for (&session, before) in r.mercs.iter().zip(positions) {
            let p = &r.w.players[&session];
            assert!(
                p.character.point().distance(before) < 1.,
                "hire was carried away"
            );
            assert!(
                p.target.is_some_and(|id| r.enemies.contains(&id)),
                "hire stopped fighting"
            );
        }
        for id in r.enemies {
            r.w.update_slime(id);
            assert_ne!(r.w.slimes[id].target, Some(1));
        }
    }
}

#[test]
fn pack_recovery_full_wipe_resets_only_living_mobs_even_after_owner_respawn() {
    let mut r = Rig::new(46);
    let killed = r.enemies[2];
    r.w.slimes[killed].dead = true;
    let other =
        r.w.slimes
            .iter()
            .position(|s| s.zone != 46 && s.kind == "cf_brute")
            .unwrap();
    let other_hp = r.w.slimes[other].hp;
    for &id in &r.enemies[..2] {
        r.w.slimes[id].x += 9.;
        r.w.slimes[id].hp = 1.;
    }
    r.kill(1);
    r.respawn_owner();
    let merc = r.mercs[0];
    r.kill(merc);
    r.w.players.get_mut(&merc).unwrap().dead_time = 10.;
    r.w.update_player(merc);
    assert!(r.w.players[&merc].character.hp > 0.);
    assert!(r.w.pack_fights[&r.zone].downed.contains(&merc));
    let last = r.mercs[1];
    r.kill(last);
    assert!(!r.w.pack_fights.contains_key(&r.zone));
    for &id in &r.enemies[..2] {
        let s = &r.w.slimes[id];
        assert!(s.target.is_none());
        assert_eq!(s.hp, s.max_hp);
        assert!(s.point().distance(at(r.w.spawns[id].x, r.w.spawns[id].y)) < 1.);
        r.w.update_slime(id);
        assert!(
            r.w.slimes[id].target.is_none(),
            "chased the respawned owner"
        );
    }
    assert!(
        r.w.slimes[killed].dead,
        "a killed mob must not be resurrected"
    );
    assert_eq!(
        r.w.slimes[other].hp, other_hp,
        "other copies must stay untouched"
    );
}

#[test]
fn pack_recovery_survivors_finish_the_pull_then_rejoin_the_hirer() {
    let mut r = Rig::new(46);
    r.kill(1);
    r.respawn_owner();
    for id in r.enemies {
        r.w.slimes[id].dead = true;
    }
    r.w.update_pack_fights();
    assert!(!r.w.pack_fights.contains_key(&r.zone));
    for &session in &r.mercs {
        r.w.players.get_mut(&session).unwrap().combat_left = 0.;
    }
    r.w.update_mercenaries();
    for session in r.mercs {
        assert!(
            r.w.players[&session]
                .character
                .point()
                .distance(r.w.players[&1].character.point())
                < 4.
        );
    }
}

#[test]
fn pack_recovery_keeps_existing_boss_fallen_rules() {
    let mut r = Rig::new(46);
    let id =
        r.w.spawns
            .iter()
            .position(|s| s.zone == 46 && r.w.boss.table.contains_key(&s.kind))
            .unwrap();
    r.w.slimes[id] = Slime::with_level(id, &r.w.spawns[id], 99);
    let point = at(r.w.slimes[id].x + 2., r.w.slimes[id].y);
    place(&mut r.w, 1, 46, point);
    r.w.slimes[id].target = Some(1);
    r.w.slimes[id].state = "chase".into();
    r.w.update_boss_mechanics();
    assert!(r.w.boss.fight_in(46));
    r.kill(1);
    r.w.players.get_mut(&1).unwrap().dead_time = 10.;
    r.w.update_player(1);
    assert!(r.w.players[&1].fallen && r.w.players[&1].character.hp == 0.);
    assert!(!r.w.players[&1].pack_death);
}

#[test]
fn pack_recovery_fallen_hire_respawns_after_the_pack_is_defeated() {
    for zone in [5, 46] {
        let mut r = Rig::new(zone);
        let merc = r.mercs[0];
        r.kill(merc);
        for &id in &r.enemies {
            r.w.slimes[id].dead = true;
        }
        for _ in 0..70 {
            r.w.update_pack_fights();
            r.w.update_player(merc);
        }
        let p = &r.w.players[&merc];
        assert!(
            p.character.hp > 0.,
            "fallen hire stayed dead after pack clear"
        );
        assert!(!p.fallen && !p.pack_death);
    }
}

#[test]
fn pack_recovery_fallen_hire_respawns_while_the_pack_is_still_fighting() {
    for zone in [5, 46] {
        let mut r = Rig::new(zone);
        let merc = r.mercs[0];
        r.kill(merc);
        for _ in 0..70 {
            r.w.update_pack_fights();
            r.w.update_player(merc);
        }
        let p = &r.w.players[&merc];
        assert!(p.character.hp > 0., "pack combat held a fallen hire down");
        assert!(!p.fallen && !p.pack_death);
        assert!(p.character.point().distance(r.w.maps[zone].spawn) < 1.);
        let fight = &r.w.pack_fights[&zone];
        assert!(
            fight.downed.contains(&merc),
            "an entrance respawn rejoined the pull"
        );
        assert!(r.enemies.iter().all(|&id| !r.w.slimes[id].dead));
    }
}
