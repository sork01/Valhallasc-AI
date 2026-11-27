//! Class resources use only authoritative combat and tick state.
use super::*;

// Half the former combat generation (0.5 dealt / 1.0 taken), before the normal resource cap.
pub(super) const RAGE_DEALT_RATE: f64 = 0.25;
pub(super) const RAGE_TAKEN_RATE: f64 = 0.5;
const MANA_RETURN_CHANCE: f64 = 0.10;
const MANA_RETURN_FRACTION: f64 = 0.20;

impl World {
    /// One roll after an accepted cast resolves, including free skills and AI casts.
    /// Separate from combat/enchantment randomness; returns only the mana actually restored.
    pub(super) fn roll_cast_mana(&mut self, session: u64) -> f64 {
        let eligible = self.players.get(&session).is_some_and(|p| {
            matches!(p.character.look.class, Class::Mage | Class::Priest) && p.character.hp > 0.
        });
        if !eligible {
            return 0.;
        }
        self.resource_rng = self
            .resource_rng
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1);
        let roll = (self.resource_rng >> 32) as f64 / 4294967296.;
        if roll >= MANA_RETURN_CHANCE {
            return 0.;
        }
        let c = &mut self.players.get_mut(&session).unwrap().character;
        let before = c.resource();
        c.change_resource(c.max_resource() * MANA_RETURN_FRACTION);
        c.resource() - before
    }

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
                    && self.maps[s.zone].line_clear(s.point(), p.character.point(), 0.05)
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
            "energy" if p.character.look.class == Class::Hunter => 15. * TICK,
            "energy" => 10. * TICK,
            "rage" if p.combat_left <= 0. => -5. * TICK,
            // Out of combat mana returns quickly; in a fight a trickle keeps a healer going (a mend every few seconds).
            "mana" => {
                p.character.max_resource() * if p.combat_left <= 0. { 0.05 } else { 0.015 } * TICK
            }
            _ => 0.,
        };
        p.character.change_resource(amount);
    }
}
