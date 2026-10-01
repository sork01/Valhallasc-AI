//! Food and potions. Food heals over its duration and only one meal can work at a time (it is a `Regen` buff, so it
//! shows in the buff bar). A potion heals at once and starts one cooldown shared by every potion. Both leave the
//! inventory the moment they take effect, and neither is used at full health, so nothing is wasted.
use super::*;

impl World {
    pub(super) fn use_item(&mut self, session: u64, id: &str) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        let refuse = |p: &Player, text: &str| {
            let _ = p.peer.try_send(json!({"type":"error","text":text}));
        };
        let Some(it) =
            item(id).filter(|i| matches!(i.kind.as_str(), "food" | "potion") && i.heal > 0.)
        else {
            return refuse(p, "That item cannot be used.");
        };
        if p.character.hp <= 0. {
            return refuse(p, "You cannot use items while defeated.");
        }
        if p.character.quantity(id) == 0 {
            return refuse(p, "You do not have that item.");
        }
        let max = p.character.max_hp();
        if p.character.hp >= max {
            return refuse(p, "You are already at full health.");
        }
        let mut healed = 0.;
        if it.kind == "food" {
            if it.duration <= 0. {
                return refuse(p, "That item cannot be used.");
            }
            if p.buffs.iter().any(|b| b.kind == BuffKind::Regen) {
                return refuse(p, "You are still eating. Wait for your meal to finish.");
            }
            p.buffs.push(Buff {
                id: it.id.clone(),
                kind: BuffKind::Regen,
                amount: it.heal / it.duration,
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
            p.character.hp = (before + it.heal).min(max);
            healed = (p.character.hp - before).round();
            p.potion_cd = it.cooldown;
            p.character.potion_ready = unix_now() + it.cooldown.ceil() as u64;
        }
        if let Some(stack) = p.character.inventory.iter_mut().find(|s| s.item == id) {
            stack.quantity -= 1;
        }
        p.character.inventory.retain(|s| s.quantity > 0);
        let (actor, point, zone) = (
            p.character.id.clone(),
            p.character.point(),
            p.character.zone,
        );
        self.emit_zone(
            zone,
            json!({"type":"event","kind":"consume","item":id,"actor":actor,"x":point.x,"y":point.y,
                "value":healed,"crit":false}),
        );
        self.save();
    }

    /// One tick of the meal and of the potion cooldown. Runs before `update_player`, which ends the meal.
    pub(super) fn update_food(&mut self, session: u64) {
        let Some(p) = self.players.get_mut(&session) else {
            return;
        };
        p.potion_cd = (p.potion_cd - TICK).max(0.);
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
        let step = TICK.min(left);
        let before = p.character.hp;
        p.character.hp = (before + rate * step).min(max);
        p.food_shown += p.character.hp - before;
        // Announce what arrived about once a second, and the remainder when the meal ends.
        if (left - step).max(0.).ceil() < left.ceil() && p.food_shown >= 0.5 {
            let amount = p.food_shown.round();
            p.food_shown = 0.;
            let (actor, point) = (p.character.id.clone(), p.character.point());
            self.event("regen", &actor, point, amount, false);
        }
    }
}
