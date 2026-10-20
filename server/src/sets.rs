use crate::model::Class;
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, sync::LazyLock};

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SetRow {
    pub source: String,
    pub class: Class,
    pub stat: String,
    pub cooldown_skill: String,
    pub double_skill: String,
    pub trigger_skill: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Signature {
    pub name: String,
    pub description: String,
}

#[derive(Deserialize)]
struct Catalog {
    signatures: BTreeMap<String, Signature>,
    entries: Vec<SetRow>,
}

static CATALOG: LazyLock<Catalog> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../world/set-bonuses.txt"))
        .expect("valid dungeon set bonus catalog")
});

pub fn rows(class: Class) -> impl Iterator<Item = &'static SetRow> {
    CATALOG.entries.iter().filter(move |row| row.class == class)
}

pub fn is_set(source: &str) -> bool {
    CATALOG.signatures.contains_key(source)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{items::ITEMS, skills};
    use std::collections::BTreeSet;

    #[test]
    fn set_matrix_covers_every_source_class_and_has_distinct_combinations() {
        let sources: BTreeSet<_> = ITEMS
            .iter()
            .filter_map(|item| item.source.as_deref())
            .filter(|source| *source != "orange_pool")
            .collect();
        assert_eq!(sources.len(), 18);
        assert_eq!(CATALOG.entries.len(), sources.len() * 5);
        assert_eq!(CATALOG.signatures.len(), sources.len());
        for class in [
            Class::Warrior,
            Class::Mage,
            Class::Assassin,
            Class::Priest,
            Class::Hunter,
        ] {
            let rows: Vec<_> = rows(class).collect();
            assert_eq!(rows.len(), sources.len());
            let mut seen = BTreeSet::new();
            for row in rows {
                assert!(sources.contains(row.source.as_str()));
                assert!(seen.insert((&row.cooldown_skill, &row.double_skill, &row.trigger_skill)));
                let level = ITEMS
                    .iter()
                    .find(|item| item.source.as_deref() == Some(&row.source))
                    .unwrap()
                    .required_level;
                for id in [&row.cooldown_skill, &row.double_skill, &row.trigger_skill] {
                    assert!(skills::find(class, id).is_some_and(|skill| skill.level <= level));
                }
            }
        }
        assert_eq!(
            CATALOG
                .signatures
                .values()
                .map(|s| &s.name)
                .collect::<BTreeSet<_>>()
                .len(),
            sources.len()
        );
    }
}
