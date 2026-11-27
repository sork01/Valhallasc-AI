use super::*;

impl Character {
    /// Recipe ingredient groups use distinct item IDs. Items within a group are interchangeable.
    /// The result is paid for and fitted in one transaction, including slots freed by ingredients.
    pub(crate) fn produce_recipe<'a, Alternatives>(
        &mut self,
        output: &str,
        fee: u32,
        all: bool,
        ingredients: impl Iterator<Item = (Alternatives, u32)> + Clone,
        missing: &'static str,
    ) -> Result<u32, &'static str>
    where
        Alternatives: IntoIterator<Item = &'a str>,
    {
        const FULL: &str = "Your bags are full. Make room first.";
        let output_item = item(output).ok_or("That recipe is unavailable.")?;
        let ingredients = ingredients.filter(|(_, needed)| *needed > 0);
        let mut count = if all { u32::MAX } else { 1 };
        if fee > 0 {
            count = count.min(self.gold / fee);
            if count == 0 {
                return Err("You cannot afford that recipe.");
            }
        }
        for (alternatives, needed) in ingredients.clone() {
            let owned: u64 = alternatives
                .into_iter()
                .map(|id| u64::from(self.quantity(id)))
                .sum();
            count = u64::from(count).min(owned / u64::from(needed)) as u32;
        }
        if count == 0 {
            return Err(missing);
        }
        count = count.min(u32::MAX - self.quantity(output));
        let gear = is_gear(output_item);
        if gear {
            count = count.min(self.bag_capacity() as u32);
        }

        while count > 0 {
            let mut staged = self.clone();
            for (alternatives, needed) in ingredients.clone() {
                let mut remaining = u64::from(needed) * u64::from(count);
                for id in alternatives {
                    let used = remaining.min(u64::from(staged.quantity(id))) as u32;
                    if used > 0 {
                        staged.consume_item(id, used);
                        remaining -= u64::from(used);
                    }
                }
                if remaining > 0 {
                    return Err(missing);
                }
            }
            if gear {
                let room = staged.bag_capacity().saturating_sub(staged.bag_used()) as u32;
                if room < count {
                    // Reducing the batch can leave more ingredient stacks in the bags.
                    count = room;
                    continue;
                }
            } else if !staged.can_collect(output) {
                return Err(FULL);
            }

            staged.gold -= fee * count;
            staged.add_item(output, count);
            *self = staged;
            return Ok(count);
        }
        Err(FULL)
    }
}
