use super::*;
impl World {
    pub(super) fn update_achievements(&mut self) {
        for p in self
            .players
            .values_mut()
            .filter(|p| p.merc.is_none() && p.ambient.is_none())
        {
            for id in p.character.sync_achievements() {
                let a = crate::achievements::catalog()
                    .iter()
                    .find(|a| a.id == id)
                    .unwrap();
                let _ = p.peer.try_send(json!({"type":"notice","ok":true,
                    "text":format!("Achievement earned: {} (+{} points).", a.name, a.points)}));
            }
        }
    }
    pub(super) fn achievements(&mut self, session: u64, title: Option<&str>) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        if p.merc.is_some() || p.ambient.is_some() {
            return;
        }
        p.character.sync_achievements();
        if let Some(title) = title
            && let Err(text) = p.character.select_achievement_title(title)
        {
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
        }
        let _ = p.peer.try_send(p.character.achievement_view());
        if title.is_some() {
            self.save();
        }
    }
    /// Matches quest boss credit: a living killer/hirer and living party members in this copy.
    pub(super) fn achievement_boss_credit(
        &mut self,
        credit: u64,
        zone: usize,
        kind: &str,
        party: &[String],
    ) {
        if !is_boss(kind) {
            return;
        }
        for (&session, p) in &mut self.players {
            if p.merc.is_none()
                && p.ambient.is_none()
                && p.character.hp > 0.
                && p.character.zone == zone
                && (session == credit || party.contains(&p.character.id))
            {
                p.character.achievements.bosses.insert(kind.to_owned());
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::super::wyrd_tests::{drain, join, world};
    use super::*;
    #[test]
    fn achievements_boss_credit_excludes_dead_strangers_other_copies_and_hires() {
        let mut w = world();
        let mut receivers = vec![];
        for session in 1..=7 {
            receivers.push(join(&mut w, session, Class::Warrior));
        }
        w.ambient_enabled = true;
        w.tick = 1;
        w.update_ambient();
        let ambient_session = *w
            .players
            .iter()
            .find(|(_, p)| p.ambient.is_some())
            .unwrap()
            .0;
        let brain = w.players.remove(&ambient_session).unwrap().ambient;
        let ids: Vec<_> = (1..=7)
            .map(|s| w.players[&s].character.id.clone())
            .collect();
        for p in w.players.values_mut() {
            p.character.zone = 46;
        }
        w.players.get_mut(&3).unwrap().character.hp = 0.;
        w.players.get_mut(&4).unwrap().character.zone = 0;
        w.players.get_mut(&5).unwrap().merc = Some(ids[0].clone());
        // 6 is an unrelated living bystander. 7 represents an ambient adventurer.
        w.players.get_mut(&7).unwrap().ambient = brain;
        let party = vec![
            ids[1].clone(),
            ids[2].clone(),
            ids[3].clone(),
            ids[4].clone(),
            ids[6].clone(),
        ];
        w.achievement_boss_credit(1, 46, "cf_eldmarr", &party);
        w.achievement_boss_credit(1, 46, "cf_eldmarr", &party);
        w.update_achievements();
        for s in [1, 2] {
            assert_eq!(w.players[&s].character.achievements.bosses.len(), 1);
        }
        for s in 3..=7 {
            assert!(w.players[&s].character.achievements.bosses.is_empty());
        }
        w.achievement_boss_credit(1, 46, "green", &party);
        assert_eq!(w.players[&1].character.achievements.bosses.len(), 1);
    }
    #[test]
    fn achievements_actual_kill_requests_title_refusals_and_store_reload() {
        let mut w = world();
        let (tx, mut rx) = mpsc::channel(4096);
        let welcome = w.join(1, None, Some(Look::default()), tx).unwrap();
        let token = welcome["token"].as_str().unwrap().to_owned();
        let boss = w
            .slimes
            .iter()
            .position(|s| s.kind == "gatewarden")
            .unwrap();
        w.players.get_mut(&1).unwrap().character.zone = w.slimes[boss].zone;
        w.slimes[boss].dead = false;
        w.slimes[boss].hp = 1.;
        w.hit_slime(boss, 1, 100., false);
        w.update_achievements();
        assert!(
            w.players[&1]
                .character
                .achievements
                .completed
                .contains("kills_1")
        );
        assert!(
            w.players[&1]
                .character
                .achievements
                .bosses
                .contains("gatewarden")
        );
        let notices = drain(&mut rx)
            .iter()
            .filter(|v| {
                v["text"]
                    .as_str()
                    .is_some_and(|s| s.starts_with("Achievement earned:"))
            })
            .count();
        assert!(notices > 0);
        w.update_achievements();
        assert!(!drain(&mut rx).iter().any(|v| {
            v["text"]
                .as_str()
                .is_some_and(|s| s.starts_with("Achievement earned:"))
        }));
        w.players.get_mut(&1).unwrap().character.explored = vec![511; 47];
        w.message(1, ClientMessage::Achievements);
        w.message(
            1,
            ClientMessage::SelectTitle {
                achievement: "explorer".into(),
            },
        );
        assert_eq!(w.players[&1].snapshot()["achievementTitle"], "The Explorer");
        let points = w.players[&1].character.achievement_points();
        w.message(
            1,
            ClientMessage::SelectTitle {
                achievement: "forge".into(),
            },
        );
        assert_eq!(w.players[&1].character.achievement_title(), "The Explorer");
        let messages = drain(&mut rx);
        assert!(messages.iter().any(|m| m["type"] == "error"));
        assert!(
            messages.iter().any(|m| m["type"] == "achievements"
                && m["maximum"] == 685
                && m["points"] == points)
        );
        w.leave(1);
        let saved = w.store.load(&token).unwrap().unwrap();
        assert_eq!(saved.achievement_points(), points);
        assert_eq!(saved.achievement_title(), "The Explorer");
        let (tx, _rx) = mpsc::channel(4096);
        w.join(1, Some(token), None, tx).unwrap();
        assert_eq!(w.players[&1].character.achievement_points(), points);
        assert_eq!(w.players[&1].character.achievement_title(), "The Explorer");
    }
}
