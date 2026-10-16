//! Food restores health and the class resource over time. Potions restore either immediately and share a persistent cooldown.
use super::*;

/// Mana amounts are catalog units. Rage and energy have a 100-point cap, so map each tier to roughly the same
/// share of a normally equipped mana user's pool at the item's required level. Old potion/meal stacks keep their IDs.
pub(super) fn resource_amount(it: &Item, c: &Character) -> f64 {
    if c.look.class.resource_type() == "mana" {
        it.mana
    } else {
        (it.mana / (100. + 15. * f64::from(it.required_level.saturating_sub(1)))).min(1.)
            * c.max_resource()
    }
}

/// Food and health potions keep their catalog floor, but heal at least 40% of
/// the drinker's maximum health. This also applies to old stacks after a level-up.
pub(super) fn health_amount(it: &Item, c: &Character) -> f64 {
    if it.heal <= 0. {
        0.
    } else {
        it.heal.max((c.max_hp() * 0.4).round())
    }
}

impl World {
    pub(super) fn use_item(&mut self, session: u64, id: &str) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        let refuse = |p: &Player, text: &str| {
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
        };
        let Some(it) = item(id).filter(|i| {
            matches!(i.kind.as_str(), "food" | "potion") && (i.heal > 0. || i.mana > 0.)
        }) else {
            return refuse(p, "That item cannot be used.");
        };
        if p.character.hp <= 0. {
            return refuse(p, "You cannot use items while defeated.");
        }
        if p.character.level < it.required_level {
            let text = format!("{} needs level {}.", it.name, it.required_level);
            return refuse(p, &text);
        }
        if p.character.quantity(id) == 0 {
            return refuse(p, "You do not have that item.");
        }
        let max = p.character.max_hp();
        let needs_health = it.heal > 0. && p.character.hp < max;
        let needs_resource = it.mana > 0. && p.character.resource() < p.character.max_resource();
        if !needs_health && !needs_resource {
            return refuse(
                p,
                if it.heal > 0. && it.mana == 0. {
                    "You are already at full health."
                } else if it.heal > 0. {
                    "Your health and resource are already full."
                } else {
                    "Your resource is already full."
                },
            );
        }
        let mut healed = 0.;
        let mut restored_resource = 0.;
        if it.kind == "food" {
            if it.duration <= 0. {
                return refuse(p, "That item cannot be used.");
            }
            if p.buffs.iter().any(|b| b.kind == BuffKind::Regen) {
                return refuse(p, "You are still eating. Wait for your meal to finish.");
            }
            if p.meal_cd > 0. {
                let text = format!(
                    "Meals are still recovering: {} s left.",
                    p.meal_cd.ceil().max(1.)
                );
                return refuse(p, &text);
            }
            p.meal_cd = it.cooldown.max(it.duration);
            p.character.meal_ready = unix_now() + p.meal_cd.ceil() as u64;
            p.buffs.push(Buff {
                id: it.id.clone(),
                kind: BuffKind::Regen,
                amount: health_amount(it, &p.character) / it.duration,
                left: it.duration,
                time: it.duration,
            });
            p.food_shown = 0.;
        } else {
            if p.potion_cd > 0. {
                let text = format!(
                    "Potions are still recovering: {} s left.",
                    p.potion_cd.round().max(1.)
                );
                return refuse(p, &text);
            }
            let before = p.character.hp;
            p.character.hp = (before + health_amount(it, &p.character)).min(max);
            healed = (p.character.hp - before).round();
            if it.mana > 0. {
                let before = p.character.resource();
                let amount = resource_amount(it, &p.character);
                p.character.change_resource(amount);
                restored_resource = (p.character.resource() - before).round();
            }
            p.potion_cd = it.cooldown;
            p.character.potion_ready = unix_now() + it.cooldown.ceil() as u64;
        }
        if let Some(stack) = p.character.inventory.iter_mut().find(|s| s.item == id) {
            stack.quantity -= 1;
        }
        p.character.inventory.retain(|s| s.quantity > 0);
        let (actor, point, zone, resource_type) = (
            p.character.id.clone(),
            p.character.point(),
            p.character.zone,
            p.character.look.class.resource_type(),
        );
        self.emit_zone(
            zone,
            json!({"type":"event","kind":"consume","item":id,"actor":actor,"x":point.x,"y":point.y,
                "value":healed,"mana":restored_resource,"resourceType":resource_type,"crit":false}),
        );
        self.save();
    }

    /// One tick of the meal and of the potion cooldown. Runs before `update_player`, which ends the meal.
    pub(super) fn update_food(&mut self, session: u64) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        p.potion_cd = (p.potion_cd - TICK).max(0.);
        p.meal_cd = (p.meal_cd - TICK).max(0.);
        if p.character.hp <= 0. {
            p.buffs.retain(|b| b.kind != BuffKind::Regen);
            p.food_shown = 0.;
            return;
        }
        let max = p.character.max_hp();
        let Some(meal) = p.buffs.iter().find(|b| b.kind == BuffKind::Regen) else {
            return;
        };
        let (rate, left) = (meal.amount, meal.left);
        let resource_rate =
            item(&meal.id).map_or(0., |i| resource_amount(i, &p.character) / i.duration);
        let step = TICK.min(left);
        let before = p.character.hp;
        p.character.hp = (before + rate * step).min(max);
        p.food_shown += p.character.hp - before;
        p.character.change_resource(resource_rate * step);
        // Announce what arrived about once a second, and the remainder when the meal ends.
        if (left - step).max(0.).ceil() < left.ceil() && p.food_shown >= 0.5 {
            let amount = p.food_shown.round();
            p.food_shown = 0.;
            let (actor, point) = (p.character.id.clone(), p.character.point());
            self.event("regen", &actor, point, amount, false);
        }
    }
}
