//! Class resources use only authoritative combat and tick state.
use super::*;

impl World {
    pub(super) fn assist_combat(&mut self, caster: u64, sessions: &[u64]) {
        if sessions
            .iter()
            .any(|s| self.players.get(s).is_some_and(|p| p.combat_left > 0.))
        {
            self.players.get_mut(&caster).unwrap().combat_left = 5.;
        }
    }

    pub(super) fn update_resource(&mut self, session: u64) {
        let p = &self.players[&session];
        let engaged = !self.maps[p.character.zone].in_city(p.character.point())
            && self.slimes.iter().any(|s| {
                !s.dead
                    && s.zone == p.character.zone
                    && s.target == Some(session)
                    && matches!(s.state.as_str(), "chase" | "windup" | "lunge")
            });
        let p = self.players.get_mut(&session).unwrap();
        p.combat_left = if engaged {
            5.
        } else {
            (p.combat_left - TICK).max(0.)
        };
        p.character.resource = Some(p.character.resource());
        if p.character.hp <= 0. {
            return;
        }
        let amount = match p.character.look.class.resource_type() {
            "energy" => 10. * TICK,
            "rage" if p.combat_left <= 0. => -5. * TICK,
            "mana" if p.combat_left <= 0. => p.character.max_resource() * 0.05 * TICK,
            _ => 0.,
        };
        p.character.change_resource(amount);
    }
}
