//! A cosmetic, server-owned chat emote. No character/save or combat-stat changes.
use super::*;

impl Player {
    fn can_dance(&self) -> bool {
        self.character.hp > 0.
            && self.combat_left <= 0.
            && self.pvp_fight <= 0.
            && self.attack <= 0.
            && self.dash <= 0.
            && self.hurt <= 0.
            && self.stun <= 0.
            && self.root <= 0.
            && !self.frozen
            && self.character.spark_travel.is_none()
    }
}

impl World {
    pub(super) fn toggle_dance(&mut self, session: u64) {
        let p = self.players.get_mut(&session).unwrap();
        if p.dance.take().is_some() {
            return;
        }
        if !p.can_dance() {
            let _ = p.peer.try_send(json!({"type":"notice","ok":false,
                "text":"You can dance when you are alive, out of combat and free to move."}));
            return;
        }
        p.stop();
        p.moving = false;
        p.character.mounted = false;
        p.dance = Some(0.);
    }

    pub(super) fn update_dances(&mut self) {
        // Run after combat so damage, death and status changes stop a dance in this tick.
        for p in self.players.values_mut().filter(|p| p.dance.is_some()) {
            if !p.can_dance()
                || p.moving
                || p.goal.is_some()
                || p.target.is_some()
                || p.character.mounted
            {
                p.dance = None;
            } else if let Some(time) = &mut p.dance {
                *time += TICK;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dancer() -> (World, mpsc::Receiver<Value>) {
        let mut w =
            World::with_level_spread(Store::open(std::path::Path::new(":memory:")).unwrap(), 0);
        let (tx, rx) = mpsc::channel(256);
        w.join(1, None, Some(Look::default()), tx).unwrap();
        (w, rx)
    }

    fn command(w: &mut World) {
        w.time += 1.1;
        w.message(
            1,
            ClientMessage::Chat {
                text: " /DANCE ".into(),
            },
        );
    }

    #[test]
    fn dance_chat_toggles_and_snapshots_both_bodies_without_broadcasting_command() {
        let (mut w, mut rx) = dancer();
        for gender in [Gender::Male, Gender::Female] {
            w.players.get_mut(&1).unwrap().character.look.gender = gender;
            command(&mut w);
            assert_eq!(w.players[&1].snapshot()["danceT"], 0.);
            w.update_dances();
            assert_eq!(w.snapshot_for(0)["players"][0]["danceT"], TICK);
            w.message(1, ClientMessage::Input { dx: 0., dy: 0. });
            w.message(1, ClientMessage::Stop);
            assert!(
                w.players[&1].dance.is_some(),
                "chat focus/idle keep dancing"
            );
            command(&mut w);
            assert!(w.players[&1].snapshot()["danceT"].is_null());
        }
        while let Ok(packet) = rx.try_recv() {
            assert_ne!(
                packet["type"], "chat",
                "the command must not become a bubble/chat line"
            );
        }
    }

    #[test]
    fn dance_dismounts_clears_autoattack_and_stops_on_actions() {
        let (mut w, _rx) = dancer();
        let p = w.players.get_mut(&1).unwrap();
        p.character.mounted = true;
        p.target = Some(0);
        p.goal = Some(Point { x: 50., y: 50. });
        command(&mut w);
        let p = &w.players[&1];
        assert!(!p.character.mounted && p.target.is_none() && p.goal.is_none());
        let at = p.character.point();
        for action in [
            ClientMessage::Input { dx: 1., dy: 0. },
            ClientMessage::Move {
                x: at.x + 1.,
                y: at.y,
            },
            ClientMessage::Attack { fx: 1., fy: 0. },
            ClientMessage::Skill {
                id: "not_a_skill".into(),
                fx: 1.,
                fy: 0.,
            },
            ClientMessage::Dash { dx: 1., dy: 0. },
        ] {
            w.players.get_mut(&1).unwrap().dance = Some(0.);
            w.message(1, action);
            assert!(w.players[&1].dance.is_none());
        }
    }

    #[test]
    fn dance_refuses_combat_death_stun_and_travel_and_interrupts_after_damage() {
        let (mut w, _rx) = dancer();
        command(&mut w);
        w.players.get_mut(&1).unwrap().combat_left = 5.;
        w.update_dances();
        assert!(w.players[&1].dance.is_none());
        command(&mut w);
        assert!(w.players[&1].dance.is_none());
        let p = w.players.get_mut(&1).unwrap();
        p.combat_left = 0.;
        p.character.hp = 0.;
        command(&mut w);
        assert!(w.players[&1].dance.is_none());
        let p = w.players.get_mut(&1).unwrap();
        p.character.hp = 1.;
        p.stun = 1.;
        command(&mut w);
        assert!(w.players[&1].dance.is_none());
        let p = w.players.get_mut(&1).unwrap();
        p.stun = 0.;
        p.frozen = true;
        command(&mut w);
        assert!(w.players[&1].dance.is_none());
        let p = w.players.get_mut(&1).unwrap();
        p.frozen = false;
        p.dance = Some(1.);
        p.hurt = 0.25;
        w.update_dances();
        assert!(w.players[&1].dance.is_none());
        let p = w.players.get_mut(&1).unwrap();
        p.hurt = 0.;
        p.character.spark_travel = Some(SparkTravel {
            destination: "alderhaven".into(),
            stops: vec![],
            points: vec![],
            next: 0,
        });
        command(&mut w);
        assert!(w.players[&1].dance.is_none());
    }
}
