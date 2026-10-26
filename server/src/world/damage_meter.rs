//! Actual PvE HP removed, per actor and per current/last zone encounter. Never saved.
use super::*;
use std::collections::BTreeSet;

#[derive(Default)]
pub(super) struct Meter {
    fights: BTreeMap<usize, Fight>,
}
struct Fight {
    start: f64,
    end: Option<f64>,
    enemies: BTreeSet<usize>,
    rows: BTreeMap<String, Value>,
}

impl Meter {
    pub(super) fn record(&mut self, time: f64, zone: usize, enemy: usize, p: &Player, damage: f64) {
        if !damage.is_finite()
            || damage <= 0.
            || p.ambient.is_some()
            || p.escort.is_some()
            || p.gauntlet
            || p.is_hidden()
        {
            return;
        }
        let f = self.fights.entry(zone).or_insert_with(|| Fight {
            start: time,
            end: None,
            enemies: BTreeSet::new(),
            rows: BTreeMap::new(),
        });
        if f.end.is_some() {
            *f = Fight {
                start: time,
                end: None,
                enemies: BTreeSet::new(),
                rows: BTreeMap::new(),
            };
        }
        f.enemies.insert(enemy);
        let row = f.rows.entry(p.character.id.clone()).or_insert_with(|| {
            json!({
                "id":p.character.id,"name":p.character.look.name,"class":p.character.look.class,
                "hired":p.merc.is_some(),"damage":0.,
            })
        });
        row["damage"] = json!(row["damage"].as_f64().unwrap_or(0.) + damage);
    }

    pub(super) fn reset(&mut self, zone: usize) {
        self.fights.remove(&zone);
    }
}

impl World {
    pub(super) fn update_damage_meter(&mut self) {
        for (&zone, f) in &mut self.damage_meter.fights {
            // A fighter may die after damaging only the first enemy in a pack.
            // Keep that row and its clock while the rest of the pull continues,
            // including enemies the surviving fighters have not hit yet.
            let pull_active = self.pack_fights.contains_key(&zone) || self.boss.fight_in(zone);
            if f.end.is_none()
                && !pull_active
                && !f.enemies.iter().any(|&id| {
                    let s = &self.slimes[id];
                    !s.dead && s.zone == zone && s.state != "return" && s.target.is_some()
                })
            {
                f.end = Some(self.time);
            }
        }
        self.damage_meter.fights.retain(|zone, _| {
            self.players
                .values()
                .any(|p| p.character.zone == *zone && p.merc.is_none() && p.ambient.is_none())
        });
    }

    pub(super) fn damage_meter_view(&self, zone: usize) -> Value {
        let f = self.damage_meter.fights.get(&zone);
        let elapsed = f.map_or(0., |f| (f.end.unwrap_or(self.time) - f.start).max(0.));
        let mut rows = f.map_or_else(BTreeMap::new, |f| f.rows.clone());
        for p in self.players.values().filter(|p| {
            p.character.zone == zone
                && p.ambient.is_none()
                && p.escort.is_none()
                && !p.gauntlet
                && !p.is_hidden()
        }) {
            rows.entry(p.character.id.clone()).or_insert_with(|| {
                json!({
                    "id":p.character.id,"name":p.character.look.name,"class":p.character.look.class,
                    "hired":p.merc.is_some(),"damage":0.,
                })
            });
        }
        let mut rows: Vec<_> = rows
            .into_values()
            .map(|mut row| {
                row["dps"] = json!(row["damage"].as_f64().unwrap_or(0.) / elapsed.max(1.));
                row
            })
            .collect();
        rows.sort_by(|a, b| {
            b["damage"]
                .as_f64()
                .unwrap_or(0.)
                .total_cmp(&a["damage"].as_f64().unwrap_or(0.))
                .then_with(|| a["id"].as_str().cmp(&b["id"].as_str()))
        });
        json!({"active":f.is_some_and(|f| f.end.is_none()),"elapsed":elapsed,"rows":rows})
    }
}
