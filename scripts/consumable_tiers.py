#!/usr/bin/env python3
"""Adds the tiered potions and food to world/items.txt: a new tier every ten levels (1, 10, 20 ... 90).

Run `python3 scripts/consumable_tiers.py`, then `node scripts/sync-world.cjs` and rebuild Rust. Idempotent: the level-1 items
(health_potion, mana_potion, traveler_stew) are kept as the first tier and given a `family` and a `price`; every other tier
is regenerated. A vendor offer marked `tiered` sells the best tier of its family that the buyer's level allows (see
world/consumables.rs and client/city.js); an item cannot be used below its `requiredLevel`. Rarity colours the tier in the
bag: common, green, blue (level 20), purple, then orange.
"""
import json
import pathlib

ITEMS = pathlib.Path(__file__).resolve().parents[1] / 'world' / 'items.txt'
LEVELS = [1] + list(range(10, 100, 10))
RARITY = ['common', 'uncommon', 'rare', 'epic'] + ['legendary'] * 6
# About 70% of a warrior's health (120 + 20/level) and 60% of a mana pool (100 + about 21/level) at the tier's level.
HEAL = [100, 210, 350, 490, 630, 770, 910, 1050, 1190, 1330]
MANA = [100, 170, 300, 430, 550, 680, 810, 930, 1060, 1190]
POTION_PRICE = [30, 60, 110, 180, 270, 380, 520, 700, 900, 1150]
FOOD_PRICE = [12, 25, 45, 75, 115, 165, 225, 300, 390, 500]
PREFIX = ['', 'Greater ', 'Superior ', 'Grand ', 'Supreme ', 'Heroic ', 'Mythic ', 'Legendary ', 'Divine ', 'Eternal ']
FOOD = ["Traveler's Stew", 'Hearty Stew', "Ranger's Feast", "Warden's Feast", "Captain's Banquet", "Champion's Banquet",
        "Hero's Banquet", "King's Banquet", "Emperor's Banquet", "Immortal's Banquet"]
FAMILIES = {
    'health_potion': dict(kind='potion', base='health_potion', name=lambda t: PREFIX[t] + 'Health Potion', price=POTION_PRICE,
                          extra=lambda t: dict(heal=HEAL[t], cooldown=60)),
    'mana_potion': dict(kind='potion', base='mana_potion', name=lambda t: PREFIX[t] + 'Mana Potion', price=POTION_PRICE,
                        extra=lambda t: dict(mana=MANA[t], cooldown=60)),
    'traveler_stew': dict(kind='food', base='traveler_stew', name=lambda t: FOOD[t], price=FOOD_PRICE,
                          extra=lambda t: dict(heal=HEAL[t], duration=8, mana=MANA[t])),
}


def tier_id(family, t):
    return family if t == 0 else f'{family}_l{LEVELS[t]}'


def main():
    raw = ITEMS.read_text()
    items = json.loads(raw)
    assert json.dumps(items, indent=2, ensure_ascii=False) + '\n' == raw, 'items.txt is not in the canonical layout'
    generated = {tier_id(f, t) for f in FAMILIES for t in range(1, len(LEVELS))}
    items = [i for i in items if i['id'] not in generated]
    for family, spec in FAMILIES.items():
        at = next(k for k, i in enumerate(items) if i['id'] == spec['base'])
        first = items[at]
        first.update(family=family, price=spec['price'][0], requiredLevel=1)
        new = []
        for t in range(1, len(LEVELS)):
            item = dict(id=tier_id(family, t), name=spec['name'](t), kind=spec['kind'], rarity=RARITY[t],
                        requiredLevel=LEVELS[t], sell=spec['price'][t] // 4, **spec['extra'](t), family=family, price=spec['price'][t])
            new.append(item)
        items[at + 1:at + 1] = new
    ITEMS.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    print('Consumable tiers:', len(generated), 'items added or refreshed across', len(FAMILIES), 'families')


if __name__ == '__main__':
    main()
