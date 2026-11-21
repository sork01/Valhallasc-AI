"""Add enchanting items and recipe stock to the finished world catalogs."""
import copy
import json
from pathlib import Path

from transmog_npcs import reachable_service_position

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'world/enchanting.txt'
MASTERS = {
    # Zone, trainer ID, nearby townsperson, existing regional artwork.
    0: ('alder_enchanting', 'apothecary', 'apothecary'),
    4: ('city_enchanting', 'city_smith', 'city_alchemist'),
    9: ('nacre_enchanting', 'nacre_smith', 'nacre_archivist'),
    17: ('asterion_enchanting', 'asterion_smith', 'asterion_archon'),
    24: ('hw_enchanting', 'hw_smith', 'heart_archivist'),
}
DIALOGUE = 'I can teach you Enchanting. Once trained, open your bags to disenchant gear, study recipes, and craft or apply scrolls.'


def assign_art(art, world):
    areas = [world, *world['zones']]
    for zone, (key, _, template) in MASTERS.items():
        if any(npc['id'] == key for npc in areas[zone]['npcs']):
            art['npcs'][key] = copy.deepcopy(art['npcs'][template])


def apply(catalog, items, world, art):
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
    areas = [world, *world['zones']]
    # Remove earlier generated offers from the draft and rebuild the dedicated trainers.
    for area in areas:
        for npc in area['npcs']:
            npc['offers'] = [offer for offer in npc['offers'] if not offer['id'].startswith('buy_enchant_recipe_')]
    for zone, (key, anchor, template) in MASTERS.items():
        area = areas[zone]
        area['npcs'] = [npc for npc in area['npcs'] if npc['id'] != key]
        at = next(npc for npc in area['npcs'] if npc['id'] == anchor)
        look = next(npc for npc in area['npcs'] if npc['id'] == template)
        pos = reachable_service_position(area, at)
        if pos is None:
            raise ValueError(f'No reachable Enchanting Master position for {anchor}')
        area['npcs'].append(dict(
            id=key, name='Enchanting Master', role='Enchanting trainer and recipe vendor',
            x=round(pos[0], 3), y=round(pos[1], 3), color=look['color'], look=copy.deepcopy(look.get('look', {})),
            dialogue=DIALOGUE, offers=[dict(id='learn_enchanting', label='Learn Enchanting', cost=0), *stock],
            buys=False,
        ))
    assign_art(art, world)


def main():
    catalog = json.loads(SOURCE.read_text())
    items_path = ROOT / 'world/items.txt'
    map_path = ROOT / 'world/map.txt'
    items = json.loads(items_path.read_text())
    world = json.loads(map_path.read_text())
    art_path = ROOT / 'client/assets/npc.txt'
    art = json.loads(art_path.read_text())
    apply(catalog, items, world, art)
    art_path.write_text(json.dumps(art, indent=2, ensure_ascii=False) + '\n')
    items_path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    map_path.write_text(json.dumps(world, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'client/enchanting-data.js').write_text("'use strict';\nwindow.ENCHANTING = " + SOURCE.read_text().strip() + ';\n')


if __name__ == '__main__':
    main()
