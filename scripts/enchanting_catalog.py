"""Add enchanting items and recipe stock to the finished world catalogs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'world/enchanting.txt'
VENDORS = {'city_transmog', 'nacre_transmog', 'asterion_transmog', 'hw_transmog'}


def apply(catalog, items, world):
    items[:] = [item for item in items if item.get('source') != 'enchanting']
    for number, material in enumerate(catalog['materials'], 1):
        items.append({**{key: material[key] for key in ('id', 'name', 'rarity')},
                      'kind': 'material', 'sell': number * 10, 'source': 'enchanting'})
    stock = []
    for enchant in catalog['enchants']:
        tier = catalog['tiers'][enchant['tier']]
        for prefix, kind, title in [('recipe', 'enchant_recipe', 'Recipe'),
                                    ('scroll', 'enchant_scroll', 'Scroll')]:
            item_id = f"enchant_{prefix}_{enchant['id']}"
            name = f"{title}: {enchant['name']}"
            items.append({'id': item_id, 'name': name, 'kind': kind, 'rarity': tier['rarity'],
                          'sell': 25 * (enchant['tier'] + 1), 'source': 'enchanting'})
            if prefix == 'recipe':
                stock.append({'id': f'buy_{item_id}', 'label': name, 'item': item_id,
                              'cost': tier['vendorPrice']})
    found = set()
    for zone in [world, *world['zones']]:
        for npc in zone['npcs']:
            if npc['id'] in VENDORS:
                found.add(npc['id'])
                npc['offers'] = [o for o in npc['offers'] if not o['id'].startswith('buy_enchant_recipe_')] + stock
    if found != VENDORS:
        raise ValueError(f'Enchanting merchants missing: {sorted(VENDORS - found)}')


def main():
    catalog = json.loads(SOURCE.read_text())
    items_path = ROOT / 'world/items.txt'
    map_path = ROOT / 'world/map.txt'
    items = json.loads(items_path.read_text())
    world = json.loads(map_path.read_text())
    apply(catalog, items, world)
    items_path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    map_path.write_text(json.dumps(world, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'client/enchanting-data.js').write_text("'use strict';\nwindow.ENCHANTING = " + SOURCE.read_text().strip() + ';\n')


if __name__ == '__main__':
    main()
