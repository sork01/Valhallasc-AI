#!/usr/bin/env python3
"""Stock existing green class weapons at ordinary vendors: level 10, 20, ... 90.

Applied by sync-world after gear/cloak generation; no new items, stats or art.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
LEVELS = tuple(range(10, 100, 10))


def price(level):
    return 10 * level * level


def apply(items, world):
    stock = {}
    for cls in CLASSES:
        for level in LEVELS:
            matches = [i for i in items if i['kind'] == 'weapon' and i.get('class') == cls
                       and i['rarity'] == 'uncommon' and i.get('requiredLevel') == level
                       and not i.get('source')]
            assert len(matches) == 1, (cls, level, len(matches))
            item = matches[0]
            item.update(family=f'vendor_weapon_{cls}', price=price(level))
            stock[cls, level] = item
    vendors = 0
    for area in [world, *world['zones']]:
        for npc in area.get('npcs', []):
            if not (npc.get('buys') or npc.get('role') == 'Armorer'):
                continue
            vendors += 1
            offers = npc.setdefault('offers', [])
            for cls in CLASSES:
                offer = dict(id=f'buy_green_weapon_{cls}', label=f'Buy {stock[cls, 10]["name"]}',
                             item=stock[cls, 10]['id'], tiered=True, cost=price(10))
                existing = next((i for i, o in enumerate(offers) if o['id'] == offer['id']), None)
                if existing is None:
                    offers.append(offer)
                else:
                    offers[existing] = offer
    return vendors


def main():
    item_path, map_path = ROOT / 'world/items.txt', ROOT / 'world/map.txt'
    items, world = json.loads(item_path.read_text()), json.loads(map_path.read_text())
    vendors = apply(items, world)
    for path, value in [(item_path, items), (map_path, world)]:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    print(f'Green weapons: {len(CLASSES) * len(LEVELS)} existing pieces, {vendors} vendors')


if __name__ == '__main__':
    main()
