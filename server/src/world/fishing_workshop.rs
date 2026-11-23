//! Fisher recipes are quoted from embedded data and applied to a clone, then committed once.
use super::*;
use serde::Deserialize;
use std::sync::LazyLock;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Recipe {
    id: String,
    item: String,
    cost: u32,
    ingredients: Vec<(String, u32)>,
    zones: Vec<usize>,
}
static RECIPES: LazyLock<Vec<Recipe>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../../world/fishing-workshop.txt"))
        .expect("Fisher recipes")
});

fn ingredients(recipe: &Recipe, c: &Character) -> Vec<(String, u32)> {
    let mut costs = recipe.ingredients.clone();
    if recipe.id.starts_with("rod:")
        && c.quantity("fishing_rod_charm") > 0
        && let Some((_, count)) = costs
            .iter_mut()
            .find(|(id, _)| item(id).is_some_and(|i| i.kind == "fish"))
    {
        *count -= 1;
        costs.push(("fishing_rod_charm".into(), 1));
    }
    costs
}

pub(super) fn quotes(npc: &Npc, c: &Character) -> Value {
    Value::Array(
        RECIPES
            .iter()
            .filter(|r| r.zones.contains(&c.zone) && npc.offers.iter().any(|o| o.id == r.id))
            .map(|r| json!({"id":r.id,"item":r.item,"cost":r.cost,"ingredients":ingredients(r,c)}))
            .collect(),
    )
}

pub(super) fn purchase(
    p: &Player,
    npc: &Npc,
    id: &str,
    trading: bool,
) -> Result<(Character, u32), &'static str> {
    let all = id.starts_with("cook_all:");
    let recipe_id = id.replacen("cook_all:", "cook:", usize::from(all));
    let recipe = RECIPES
        .iter()
        .find(|r| {
            r.id == recipe_id
                && r.zones.contains(&p.character.zone)
                && npc.offers.iter().any(|o| o.id == recipe_id)
        })
        .ok_or("This Fisher does not offer that recipe.")?;
    if !p.can_dance() || trading {
        return Err("Finish fighting or trading before using the Fisher workshop.");
    }
    if p.character.mounted {
        return Err("Dismount before using the Fisher workshop.");
    }
    let output = item(&recipe.item).ok_or("That recipe is unavailable.")?;
    if p.character.level < output.required_level {
        return Err("You need a higher level for that recipe.");
    }
    let costs = ingredients(recipe, &p.character);
    let mut next = p.character.clone();
    let count = next.produce_recipe(
        &recipe.item,
        recipe.cost,
        all,
        costs.iter().map(|(id, count)| (std::iter::once(id.as_str()), *count)),
        "You do not have the ingredients for that recipe.",
    )?;
    Ok((next, count))
}
