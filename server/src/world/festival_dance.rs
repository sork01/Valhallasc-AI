//! Guided, collision-checked festival circuits; clients never submit lap progress.
use super::*;
const RADIUS: f64 = 1.8;
const ANGULAR_SPEED: f64 = std::f64::consts::TAU / 10.;
const FINISH: f64 = 2. * std::f64::consts::TAU;
pub(super) struct Circuit {
    season: String,
    zone: usize,
    centre: Point,
    angle: f64,
    progress: f64,
    approaching: bool,
    elapsed: f64,
}
impl Circuit {
    pub(super) fn view(&self) -> Value {
        json!({"season":self.season,"laps":self.progress/std::f64::consts::TAU,"approaching":self.approaching,"x":self.centre.x,"y":self.centre.y})
    }
}
impl World {
    pub(super) fn start_festival_dance(&mut self, session: u64, id: &str) -> Result<(), String> {
        let p = self.players.get(&session).ok_or("Dance unavailable.")?;
        let n = self.maps[p.character.zone]
            .npcs
            .iter()
            .find(|n| n.id == id && n.id.starts_with("festival_dance_"))
            .ok_or("Walk closer to the festival centerpiece.")?;
        let season =
            n.id.strip_prefix("festival_dance_")
                .and_then(|s| s.rsplit_once('_'))
                .map(|(s, _)| s)
                .ok_or("Dance unavailable.")?;
        if !self.seasonal.active().iter().any(|e| e.id == season) {
            return Err("This festival dance is not available now.".into());
        }
        let centre = Point { x: n.x, y: n.y };
        if p.character.point().distance(centre) > 2.8
            || p.merc.is_some()
            || p.ambient.is_some()
            || p.gauntlet
            || p.character.mounted
            || !p.can_dance()
        {
            return Err(
                "Gather near the centerpiece alive, dismounted and out of combat to dance.".into(),
            );
        }
        let map = &self.maps[p.character.zone];
        for i in 0..64 {
            let a = i as f64 * std::f64::consts::TAU / 64.;
            let b = (i + 1) as f64 * std::f64::consts::TAU / 64.;
            if !map.line_clear(orbit(centre, a), orbit(centre, b), PLAYER_RADIUS) {
                return Err("The dancing circle is obstructed.".into());
            }
        }
        let point = p.character.point();
        let angle = (point.y - centre.y).atan2(point.x - centre.x);
        if !map.line_clear(point, orbit(centre, angle), PLAYER_RADIUS) {
            return Err("Walk onto the clear dancing circle first.".into());
        }
        let season = season.to_string();
        let zone = p.character.zone;
        let p = self.players.get_mut(&session).unwrap();
        p.stop();
        p.moving = false;
        p.dance = Some(0.);
        p.festival_dance = Some(Circuit {
            season,
            zone,
            centre,
            angle,
            progress: 0.,
            approaching: true,
            elapsed: 0.,
        });
        let _=p.peer.try_send(json!({"type":"notice","ok":true,"text":"The festival dance begins. Complete two laps; move or fight to cancel."}));
        Ok(())
    }
    pub(super) fn update_festival_dances(&mut self) {
        let active = self.seasonal.active();
        let mut earned = false;
        let now = crate::festival::now();
        for p in self.players.values_mut() {
            if p.character.festival_spirit.until > 0 && p.character.festival_spirit.until <= now {
                p.character.festival_spirit.until = 0;
                earned = true;
                let _=p.peer.try_send(json!({"type":"notice","ok":true,"text":"Festival Spirit has expired. Dance two laps to earn it again during a festival."}));
            }
        }
        for p in self
            .players
            .values_mut()
            .filter(|p| p.festival_dance.is_some())
        {
            let mut run = p.festival_dance.take().unwrap();
            run.elapsed += TICK;
            let valid = p.dance.is_some()
                && p.can_dance()
                && !p.character.mounted
                && !p.moving
                && p.goal.is_none()
                && p.target.is_none()
                && p.character.zone == run.zone
                && active.iter().any(|e| e.id == run.season)
                && run.elapsed < 30.;
            if !valid {
                p.dance = None;
                let _=p.peer.try_send(json!({"type":"notice","ok":false,"text":"Festival dance cancelled. Complete two new laps to earn the buff."}));
                continue;
            }
            let before = p.character.point();
            let next_angle = if run.approaching {
                run.angle
            } else {
                run.angle + ANGULAR_SPEED * TICK
            };
            let target = orbit(run.centre, next_angle);
            let distance = before.distance(target);
            let allowed = if run.approaching {
                3. * TICK
            } else {
                RADIUS * ANGULAR_SPEED * TICK * 1.01
            };
            if distance > allowed + 0.01 && !run.approaching {
                p.dance = None;
                let _=p.peer.try_send(json!({"type":"notice","ok":false,"text":"Festival dance cancelled. Complete two new laps to earn the buff."}));
                continue;
            }
            let mut after = before;
            self.maps[run.zone].walk(
                &mut after,
                before.direction(target),
                distance.min(allowed),
                PLAYER_RADIUS,
            );
            if !run.approaching && after.distance(target) > 0.005 {
                p.dance = None;
                continue;
            }
            p.character.x = after.x;
            p.character.y = after.y;
            p.face = before.direction(target);
            if run.approaching {
                if after.distance(target) < 0.005 {
                    run.approaching = false;
                }
            } else {
                // Advance only after a legal movement step actually reaches the next ring point.
                let old_angle = (before.y - run.centre.y).atan2(before.x - run.centre.x);
                let new_angle = (after.y - run.centre.y).atan2(after.x - run.centre.x);
                let delta = (new_angle - old_angle + std::f64::consts::PI)
                    .rem_euclid(std::f64::consts::TAU)
                    - std::f64::consts::PI;
                if delta <= 0. || delta > ANGULAR_SPEED * TICK * 1.02 {
                    p.dance = None;
                    continue;
                }
                run.progress += delta;
                run.angle = next_angle;
            }
            if run.progress + 1e-7 >= FINISH {
                p.dance = None;
                p.character
                    .festival_spirit
                    .grant(crate::festival::now(), &run.season);
                earned = true;
                let _=p.peer.try_send(json!({"type":"notice","ok":true,"text":"Festival Spirit earned: +10% attack and +50% experience for two hours."}));
            } else {
                p.festival_dance = Some(run);
            }
        }
        if earned {
            self.save();
        }
    }
}
fn orbit(c: Point, a: f64) -> Point {
    Point {
        x: c.x + RADIUS * a.cos(),
        y: c.y + RADIUS * a.sin(),
    }
}
#[cfg(test)]
mod tests {
    use super::super::wyrd_tests::{at, calm, join, place, world};
    use super::*;
    fn fixture(unix: u64) -> World {
        let mut w = world();
        calm(&mut w);
        let _rx = join(&mut w, 1, Class::Warrior);
        w.seasonal.override_unix = Some(unix);
        w.seasonal.next_check = 0.;
        w.update_seasonal();
        place(&mut w, 1, 0, at(33.8, 83.));
        w
    }
    fn ticks(w: &mut World, n: usize) {
        for _ in 0..n {
            w.time += TICK;
            w.update_festival_dances();
            w.update_dances();
        }
    }
    #[test]
    fn festival_dance_all_six_seasons_all_cities_and_exact_two_laps() {
        for (season, unix) in [
            ("halloween", 1793055600),
            ("christmas", 1797289200),
            ("newyear", 1798498800),
            ("valentine", 1802214000),
            ("easter", 1806015600),
            ("solstice", 1813183200),
        ] {
            let mut w = fixture(unix);
            assert!(
                w.seasonal.active().iter().any(|e| e.id == season),
                "{season}"
            );
            for zone in [0, 4, 9, 17, 24] {
                let id = format!("festival_dance_{season}_{zone}");
                let n = w.maps[zone].npcs.iter().find(|n| n.id == id).unwrap();
                let c = at(n.x, n.y);
                for i in 0..64 {
                    assert!(w.maps[zone].line_clear(
                        orbit(c, i as f64 * std::f64::consts::TAU / 64.),
                        orbit(c, (i + 1) as f64 * std::f64::consts::TAU / 64.),
                        PLAYER_RADIUS
                    ));
                }
            }
            w.start_festival_dance(1, &format!("festival_dance_{season}_0"))
                .unwrap();
            ticks(&mut w, 399);
            assert_eq!(
                w.players[&1].character.festival_spirit.until, 0,
                "no early reward {season}"
            );
            assert!(w.players[&1].festival_dance.is_some());
            ticks(&mut w, 3);
            assert!(w.players[&1].festival_dance.is_none());
            assert_eq!(w.players[&1].character.festival_spirit.season, season);
            assert!(
                w.players[&1]
                    .character
                    .festival_spirit
                    .left(crate::festival::now())
                    >= 7199
            );
        }
    }
    #[test]
    fn festival_dance_actions_status_zone_and_displacement_interrupt_without_reward() {
        for action in [
            ClientMessage::Input { dx: 1., dy: 0. },
            ClientMessage::Move { x: 35., y: 83. },
            ClientMessage::Attack { fx: 1., fy: 0. },
            ClientMessage::Skill {
                id: "invalid".into(),
                fx: 1.,
                fy: 0.,
            },
            ClientMessage::Mount { mounted: true },
        ] {
            let mut w = fixture(1813183200);
            w.start_festival_dance(1, "festival_dance_solstice_0")
                .unwrap();
            ticks(&mut w, 20);
            w.message(1, action);
            ticks(&mut w, 450);
            assert_eq!(w.players[&1].character.festival_spirit.until, 0);
        }
        for mode in 0..7 {
            let mut w = fixture(1813183200);
            w.start_festival_dance(1, "festival_dance_solstice_0")
                .unwrap();
            ticks(&mut w, 20);
            let p = w.players.get_mut(&1).unwrap();
            match mode {
                0 => p.character.hp = 0.,
                1 => p.hurt = 1.,
                2 => p.stun = 1.,
                3 => p.root = 1.,
                4 => p.character.zone = 4,
                5 => p.character.x += 3.,
                _ => p.combat_left = 2.,
            }
            ticks(&mut w, 450);
            assert_eq!(w.players[&1].character.festival_spirit.until, 0, "{mode}");
        }
    }
    #[test]
    fn festival_dance_idle_stop_refusals_expiry_and_refresh_are_authoritative() {
        let mut w = fixture(1813183200);
        assert!(
            w.start_festival_dance(1, "festival_dance_christmas_0")
                .is_err()
        );
        assert!(w.start_festival_dance(1, "baker").is_err());
        w.players.get_mut(&1).unwrap().character.mounted = true;
        assert!(
            w.start_festival_dance(1, "festival_dance_solstice_0")
                .is_err()
        );
        w.players.get_mut(&1).unwrap().character.mounted = false;
        w.start_festival_dance(1, "festival_dance_solstice_0")
            .unwrap();
        w.message(1, ClientMessage::Stop);
        w.message(1, ClientMessage::Input { dx: 0., dy: 0. });
        ticks(&mut w, 30);
        assert!(w.players[&1].festival_dance.is_some());
        w.seasonal.override_unix = Some(1813960800);
        ticks(&mut w, 500);
        assert_eq!(w.players[&1].character.festival_spirit.until, 0);
        w.seasonal.override_unix = Some(1813183200);
        place(&mut w, 1, 0, at(33.8, 83.));
        w.players
            .get_mut(&1)
            .unwrap()
            .character
            .festival_spirit
            .grant(crate::festival::now() - 60, "easter");
        w.start_festival_dance(1, "festival_dance_solstice_0")
            .unwrap();
        ticks(&mut w, 405);
        assert!(
            w.players[&1]
                .character
                .festival_spirit
                .left(crate::festival::now())
                <= 7200
        );
        assert_eq!(w.players[&1].character.festival_spirit.season, "solstice");
    }
    #[test]
    fn festival_dance_disconnect_rejoin_keeps_buff_but_never_partial_progress() {
        let mut w = fixture(1813183200);
        w.start_festival_dance(1, "festival_dance_solstice_0")
            .unwrap();
        ticks(&mut w, 200);
        let character = w.players.remove(&1).unwrap().character;
        let (peer, _rx) = mpsc::channel(256);
        w.players.insert(2, Player::new(character, peer));
        ticks(&mut w, 500);
        assert!(w.players[&2].festival_dance.is_none());
        assert_eq!(w.players[&2].character.festival_spirit.until, 0);
        place(&mut w, 2, 0, at(33.8, 83.));
        w.start_festival_dance(2, "festival_dance_solstice_0")
            .unwrap();
        ticks(&mut w, 405);
        assert!(
            w.players[&2]
                .character
                .festival_spirit
                .left(crate::festival::now())
                > 0
        );
    }
}
