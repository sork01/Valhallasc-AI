//! `PRIEST-MEND-PROC`: a priest's normal hit can ready Mend and make it free for a moment. See
//! `docs/priest-mend-proc.md`.
use super::*;

/// Chance, per normal attack that damages a monster, to ready Mend.
const CHANCE: f64 = 0.10;
/// Seconds Mend then costs nothing.
const FREE_TIME: f64 = 4.;
const MEND: &str = "mend";

impl World {
    /// The proc never works in, or carries into, a fight between players.
    fn mend_proc_barred(&self, p: &Player) -> bool {
        self.alchemy_pvp(p) || self.pvp_busy(&p.character.id)
    }

    /// What `session` pays to cast `skill` now.
    pub(super) fn skill_price(&self, session: u64, skill: &skills::Skill) -> f64 {
        let free = skill.id == MEND
            && self
                .players
                .get(&session)
                .is_some_and(|p| p.mend_free_left > 0. && !self.mend_proc_barred(p));
        if free { 0. } else { skill.cost }
    }

    /// Called once for each normal swing that damaged at least one monster.
    pub(super) fn roll_mend_proc(&mut self, session: u64) {
        let eligible = self.players.get(&session).is_some_and(|p| {
            p.character.look.class == Class::Priest
                && p.character.hp > 0.
                && skills::find(Class::Priest, MEND).is_some_and(|s| p.character.level >= s.level)
                && !self.mend_proc_barred(p)
        });
        if !eligible || self.random() >= CHANCE {
            return;
        }
        if let Some(p) = self.players.get_mut(&session) {
            p.skill_cd.remove(MEND);
            p.mend_free_left = FREE_TIME;
        }
    }

    /// Death and PvP end the free time at once.
    pub(super) fn expire_mend_proc(&mut self, session: u64) {
        let lost = self.players.get(&session).is_some_and(|p| {
            p.mend_free_left > 0. && (p.character.hp <= 0. || self.mend_proc_barred(p))
        });
        if lost && let Some(p) = self.players.get_mut(&session) {
            p.mend_free_left = 0.;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::super::wyrd_tests::{join, place, world};
    use super::*;

    const OPEN: Point = Point { x: 276., y: 226. };

    /// A hero of `class` at `level` on open ground with one very tough monster in reach, facing it.
    fn rig(class: Class, level: u32) -> (World, mpsc::Receiver<Value>) {
        let mut w = world();
        w.resource_rng = 1; // This fixture isolates the free-Mend proc.
        let rx = join(&mut w, 1, class);
        w.players.get_mut(&1).unwrap().character.level = level;
        place(&mut w, 1, 0, OPEN);
        w.players.get_mut(&1).unwrap().face = Point { x: 1., y: 0. };
        let s = &mut w.slimes[0];
        (s.zone, s.x, s.y, s.dead) = (0, OPEN.x + 0.8, OPEN.y, false);
        (s.hp, s.max_hp) = (1e12, 1e12);
        (w, rx)
    }

    /// Swings once with Mend on cooldown; returns (the swing did damage, it readied Mend).
    fn swing(w: &mut World) -> (bool, bool) {
        let p = w.players.get_mut(&1).unwrap();
        p.skill_cd.insert(MEND.into(), 3.);
        p.mend_free_left = 0.;
        let before = w.slimes[0].hp;
        w.strike(1);
        let p = &w.players[&1];
        let readied = p.mend_free_left > 0.;
        assert_eq!(
            readied,
            !p.skill_cd.contains_key(MEND),
            "both halves of the proc"
        );
        if readied {
            assert_eq!(p.mend_free_left, 4.);
        }
        (w.slimes[0].hp < before, readied)
    }

    fn procs(w: &mut World, swings: u32) -> (u32, u32) {
        (0..swings).fold((0, 0), |(hits, ready), _| {
            let (hit, readied) = swing(w);
            assert!(hit || !readied, "a miss never readies Mend");
            (hits + u32::from(hit), ready + u32::from(readied))
        })
    }

    #[test]
    fn mend_proc_follows_about_one_landed_priest_hit_in_ten() {
        let (mut w, _rx) = rig(Class::Priest, 25);
        let (hits, ready) = procs(&mut w, 8000);
        assert!(hits < 8000, "the sample includes misses");
        let rate = f64::from(ready) / f64::from(hits);
        assert!((0.085..0.115).contains(&rate), "{ready} of {hits}");
    }

    #[test]
    fn mend_proc_needs_a_priest_who_knows_mend_and_a_monster_that_is_hit() {
        for (class, level) in [(Class::Warrior, 25), (Class::Priest, 3)] {
            let (mut w, _rx) = rig(class, level);
            assert_eq!(procs(&mut w, 600).1, 0, "{class:?} {level}");
        }
        let (mut w, _rx) = rig(Class::Priest, 25);
        w.players.get_mut(&1).unwrap().face = Point { x: -1., y: 0. };
        assert_eq!(procs(&mut w, 600), (0, 0), "nothing was hit");
    }

    /// A hurt level 25 priest with an empty mana bar and Mend ready.
    fn dry() -> (World, mpsc::Receiver<Value>) {
        let (mut w, rx) = rig(Class::Priest, 25);
        w.slimes[0].dead = true;
        let c = &mut w.players.get_mut(&1).unwrap().character;
        c.hp = c.max_hp() * 0.6;
        c.resource = Some(0.);
        (w, rx)
    }

    fn hp_and_mana(w: &World) -> (f64, f64) {
        let c = &w.players[&1].character;
        (c.hp, c.resource())
    }

    #[test]
    fn mend_proc_makes_only_mend_free() {
        let (mut w, _rx) = dry();
        let hurt = hp_and_mana(&w);
        w.use_skill(1, MEND, Point::default());
        assert_eq!(
            hp_and_mana(&w),
            hurt,
            "without the proc there is no mana to cast"
        );
        w.players.get_mut(&1).unwrap().mend_free_left = 4.;
        w.use_skill(1, "prayer", Point::default());
        assert_eq!(hp_and_mana(&w), hurt, "Prayer of Healing still costs mana");
        w.use_skill(1, MEND, Point::default());
        let after = hp_and_mana(&w);
        assert!(after.0 > hurt.0 && after.1 == 0., "{hurt:?} -> {after:?}");
        assert!(
            w.players[&1].skill_cd.contains_key(MEND),
            "the free cast still starts a cooldown"
        );
    }

    #[test]
    fn mend_proc_free_time_runs_out_after_four_seconds() {
        let (mut w, _rx) = dry();
        w.players.get_mut(&1).unwrap().mend_free_left = 4.;
        let mend = skills::find(Class::Priest, MEND).unwrap().at_level(25);
        for tick in 1..=(4. / TICK) as u32 {
            assert_eq!(w.skill_price(1, &mend), 0., "free at tick {tick}");
            w.update_player(1);
        }
        assert_eq!(w.skill_price(1, &mend), mend.cost);
    }

    #[test]
    fn mend_proc_never_works_between_players_and_ends_at_death() {
        let mend = skills::find(Class::Priest, MEND).unwrap().at_level(25);
        for flagged in [false, true] {
            let (mut w, _rx) = rig(Class::Priest, 25);
            let p = w.players.get_mut(&1).unwrap();
            if flagged {
                p.pvp_flag = true;
            } else {
                p.pvp_fight = 8.;
            }
            assert_eq!(procs(&mut w, 600).1, 0);
            w.players.get_mut(&1).unwrap().mend_free_left = 4.;
            assert_eq!(
                w.skill_price(1, &mend),
                mend.cost,
                "a held proc buys nothing in PvP"
            );
            w.update_player(1);
            assert_eq!(w.players[&1].mend_free_left, 0.);
        }
        let (mut w, _rx) = dry();
        let p = w.players.get_mut(&1).unwrap();
        (p.mend_free_left, p.character.hp) = (4., 0.);
        w.update_player(1);
        assert_eq!(w.players[&1].mend_free_left, 0.);
    }

    #[test]
    fn mend_proc_lets_a_computer_priest_cast_with_an_empty_mana_bar() {
        let (mut w, _rx) = dry();
        w.players.get_mut(&1).unwrap().character.inventory.clear(); // no potions
        let hurt = hp_and_mana(&w);
        w.ai_combat_at(1, &[1], None);
        assert_eq!(hp_and_mana(&w), hurt);
        w.players.get_mut(&1).unwrap().mend_free_left = 4.;
        w.ai_combat_at(1, &[1], None);
        assert!(hp_and_mana(&w).0 > hurt.0);
    }

    #[test]
    fn mend_proc_time_is_sent_to_its_owner_only() {
        let (mut w, _rx) = dry();
        let _other = join(&mut w, 2, Class::Warrior);
        place(&mut w, 2, 0, OPEN);
        w.players.get_mut(&1).unwrap().mend_free_left = 2.5;
        let id = w.players[&1].character.id.clone();
        let find = |v: &Value| {
            v["players"]
                .as_array()
                .unwrap()
                .iter()
                .find(|p| p["id"] == id.as_str())
                .unwrap()
                .clone()
        };
        let mut own = w.snapshot_for(0);
        crate::visibility::filter_view(&mut own, &id);
        assert_eq!(find(&own)["mendFree"], 2.5);
        let mut theirs = w.snapshot_for(0);
        crate::visibility::filter_view(&mut theirs, &w.players[&2].character.id);
        assert!(find(&theirs).get("mendFree").is_none());
    }
}
