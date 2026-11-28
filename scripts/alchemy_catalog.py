#!/usr/bin/env python3
"""Overlay Alchemy workshops and generate flower pools from finished terrain."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from fishing_spots import SCALE, SURFACES, clear_of_hubs_and_seams, radius, walkable

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'alchemy'
WORKSHOP = 'alchemy_workshop'
# City, workshop id, name, anchor, local flower. New counters use an open
# point near an established landmark and keep the rest of the city intact.
WORKSHOPS = {
    0: ('alchemy_alderhaven', 'Maera Petalbrook', (257, 196), 'alchemy_meadowgold'),
    4: ('city_alchemist', None, (37.5, 66.3), 'alchemy_lantern_lily'),
    9: ('alchemy_nacrehold', 'Neris Shellcup', (146, 107), 'alchemy_tideglass_anemone'),
    17: ('alchemy_asterion', 'Lio Sporeglass', (61, 109), 'alchemy_sporebell'),
    24: ('alchemy_heartwood', 'Yrsa Mosskettle', (145, 158), 'alchemy_heartvine_bloom'),
}
DIALOGUE = 'Bring flowers and empty bottles to my counter. I can teach you recipes and help you brew them.'


def point_objects(area, kinds):
    return [obj for obj in area['objects'] if obj['kind'] in kinds]


def nearby(pos, obj, distance):
    return math.hypot(pos[0] - obj['x'], pos[1] - obj['y']) < distance


def inside_city(area, x, y):
    c = area['city']
    return c['x0'] < x < c['x1'] and c['y0'] < y < c['y1']


def open_ground(area, reachable, stride):
    floor = area.get('shapeFloor')
    for row, col in np.argwhere(reachable[2::stride, 2::stride]):
        iy, ix = int(row) * stride + 2, int(col) * stride + 2
        x, y = (ix + .5) / SCALE, (iy + .5) / SCALE
        if floor and floor[int(y)][int(x)] != '#':
            continue
        exits = [(iy + dy, ix + dx) for dy, dx in [(0, 2), (2, 0), (0, -2), (-2, 0)]]
        if sum(0 <= a < reachable.shape[0] and 0 <= b < reachable.shape[1] and reachable[a, b]
               for a, b in exits) >= 2:
            yield x, y


def candidates(area, reachable, zone, veins):
    surfaces = point_objects(area, SURFACES)
    hazards = [*area.get('portals', []), *area.get('npcs', []), *veins]
    regions = {}
    if zone == 6:
        for y, lo, hi, index in area['regions']['spans']:
            for x in range(lo, hi + 1):
                regions[x, y] = index
    result = {False: [], True: []}
    for pos in open_ground(area, reachable, SCALE * 4):
        if not clear_of_hubs_and_seams(area, *pos):
            continue
        if any(nearby(pos, obj, radius(obj) + 3) for obj in surfaces):
            continue
        if any(nearby(pos, obj, 6) for obj in hazards) or any(nearby(pos, obj, 4) for obj in area['slimes']):
            continue
        if regions and (int(pos[0]), int(pos[1])) not in regions:
            continue
        inner = regions.get((int(pos[0]), int(pos[1])), 0) >= 10
        result[inner].append(pos)
    return result


def spread(points, origin, separation, limit):
    remaining = points.copy()
    selected = [min(remaining, key=lambda pos: math.dist(pos, origin))]
    remaining.remove(selected[0])
    distances = [math.dist(pos, selected[0]) for pos in remaining]
    while remaining and len(selected) < limit:
        index = max(range(len(remaining)), key=distances.__getitem__)
        if distances.pop(index) < separation:
            break
        pos = remaining.pop(index)
        selected.append(pos)
        distances = [min(distance, math.dist(other, pos)) for other, distance in zip(remaining, distances)]
    return [dict(x=x, y=y) for x, y in selected]


def workshop(area, zone, reachable, stock, npc_index):
    ident, name, anchor, flower = WORKSHOPS[zone]
    surfaces = point_objects(area, SURFACES)
    grounds = [pos for pos in open_ground(area, reachable, 2) if inside_city(area, *pos)
               and not any(nearby(pos, obj, radius(obj) + 1) for obj in surfaces)
               and not any(nearby(pos, obj, 3) for obj in area.get('portals', []))]
    if name:
        nearby_npcs = area['npcs']
        x, y = min((pos for pos in grounds if not any(nearby(pos, n, 2.4) for n in nearby_npcs)),
                   key=lambda pos: math.dist(pos, anchor))
        look = (dict(species='merfolk', female=True, tail='#63c6ab', skin='#92c9bc',
                     hair='#46314b', style='long') if zone == 9
                else dict(skin='#bd8064' if zone == 17 else '#e3ae83', hair='#704b51',
                          style='bun', apron='#4e7469', prop='alembic'))
        npc = dict(id=ident, name=name, role='Alchemist', x=x, y=y, color='#4e7469',
                   dialogue=DIALOGUE, look=look, offers=[])
        area['npcs'].insert(npc_index, npc)
    else:
        npc = next(n for n in area['npcs'] if n['id'] == ident)
    def alchemy_offer(offer):
        return offer['id'] == WORKSHOP or offer['id'].startswith('buy_alchemy_')

    offers = npc['offers']
    start = next((i for i, offer in enumerate(offers) if alchemy_offer(offer)), len(offers))
    offers[:] = [offer for offer in offers if not alchemy_offer(offer)]
    offers[start:start] = [dict(id=WORKSHOP, label='Alchemy workshop', cost=0), *stock]
    pos = npc['x'], npc['y']
    patches = [p for p in grounds if 3 <= math.dist(pos, p) <= 18
               and not any(nearby(p, n, 2.4) for n in area['npcs'])]
    if not patches:
        raise ValueError(f"{area['name']}: no reachable garden")
    return flower, spread(patches, pos, 3.5, 5)


def apply(catalog, world, items, veins):
    start = next((i for i, item in enumerate(items) if item.get('source') == SOURCE), len(items))
    original = [i for i in items if i.get('source') != SOURCE]
    new = []
    stock = []
    for supply in catalog['supplies']:
        new.append(dict(id=supply['item'], name=supply['name'], kind='material', rarity='common',
                        sell=supply['price'] // 5, source=SOURCE))
        stock.append(dict(id='buy_' + supply['item'], label='Buy ' + supply['name'],
                          item=supply['item'], cost=supply['price']))
    for flower in catalog['flowers']:
        new.append(dict(id=flower['item'], name=flower['name'], kind='material', rarity='common',
                        sell=2 + flower['band'], source=SOURCE))
    for recipe in catalog['recipes']:
        new.append(dict(id=recipe['item'], name=recipe['name'],
                        kind='alchemy_flask' if recipe['flask'] else 'potion',
                        rarity='epic' if recipe.get('boss') else 'rare' if recipe.get('formula') else 'uncommon',
                        requiredLevel=recipe['level'], duration=2700 if recipe['flask'] else 15,
                        cooldown=0 if recipe['flask'] else 60, sell=4 + recipe['level'], source=SOURCE))
        if recipe.get('formula'):
            new.append(dict(id=recipe['formula'], name='Formula: ' + recipe['name'],
                            kind='alchemy_formula', rarity='epic' if recipe.get('boss') else 'rare',
                            sell=25, source=SOURCE))
    if len({i['id'] for i in original + new}) != len(original) + len(new):
        raise ValueError('Alchemy item ID is already in the catalog')
    items[:] = original[:start] + new + original[start:]

    areas = [world, *world['zones']]
    by_id = {flower['item']: index for index, flower in enumerate(catalog['flowers'])}
    pools = {}
    positions = {}
    for flower in catalog['flowers']:
        zone = flower['zone']
        if zone not in positions:
            walk = walkable(areas[zone])
            positions[zone] = walk, candidates(areas[zone], walk, zone, veins.get(str(zone), []))
        area = areas[zone]
        points = positions[zone][1][flower['band'] == 5]
        origin = area['spawn']['x'], area['spawn']['y']
        active = 2 if flower['band'] == 4 else 1 if flower['band'] == 5 else 3
        if not points:
            raise ValueError(f"{area['name']}: no reachable {flower['name']} patches")
        pools.setdefault(zone, []).append(dict(flower=by_id[flower['item']], active=active,
                                                points=spread(points, origin, 10, 10)))
    for zone, (ident, name, *_rest) in WORKSHOPS.items():
        area = areas[zone]
        npcs = area['npcs']
        npc_index = next((i for i, npc in enumerate(npcs) if npc['id'] == ident), len(npcs))
        if name and npc_index < len(npcs):
            npcs.pop(npc_index)
        reachable = positions[zone][0] if zone in positions else walkable(area)
        flower, points = workshop(area, zone, reachable, stock, npc_index)
        pools.setdefault(zone, []).append(dict(flower=by_id[flower], active=1, points=points))
    for zone, groups in pools.items():
        for group in groups:
            if len(group['points']) <= group['active']:
                raise ValueError(f"{areas[zone]['name']}: every pool needs an unused alternate")
    return dict(sorted(pools.items()))


# The new counters' artwork: the town alchemist's player-style design, and a Nacre townsperson's for the merfolk counter.
HUMAN_ART, MERFOLK_ART = 'alchemist', 'special_nacre_healer'


def assign_art(manifest, world):
    """Give every Alchemist this overlay adds a saved design (the older city alchemist keeps theirs)."""
    added = {ident for ident, name, *_ in WORKSHOPS.values() if name}
    for area in [world, *world['zones']]:
        for npc in area['npcs']:
            if npc['id'] in added:
                art = MERFOLK_ART if npc['look'].get('species') == 'merfolk' else HUMAN_ART
                manifest['npcs'][npc['id']] = dict(art=art, identity=dict(npc['look']), color=npc['color'])


def publish(name, key, data):
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    (ROOT / f'client/{name}.js').write_text(f"'use strict';\nwindow.{key} = {encoded};\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-catalogs', action='store_true')
    args = parser.parse_args()
    def read(name):
        return json.loads((ROOT / f'world/{name}.txt').read_text())
    world, items, catalog = read('map'), read('items'), read('alchemy')
    pools = apply(catalog, world, items, read('mining-veins'))
    for name, data in [('map', world), ('items', items), ('flower-patches', pools)]:
        (ROOT / f'world/{name}.txt').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    art_path = ROOT / 'client/assets/npc.txt'
    art = json.loads(art_path.read_text())
    assign_art(art, world)
    art_path.write_text(json.dumps(art, indent=2, ensure_ascii=False) + '\n')
    sources = {zone: [p['flower'] for p in groups] for zone, groups in pools.items()}
    formula_zones = {area['final_boss']: zone for zone, area in enumerate([world, *world['zones']])
                     if area.get('final_boss')}
    publish('alchemy-data', 'ALCHEMY_DATA', {**catalog, 'sources': sources, 'formulaZones': formula_zones})
    if args.publish_catalogs:
        publish('world', 'WORLD_MAP', world)
        publish('items', 'WORLD_ITEMS', items)
    print(f"Alchemy pools: {sum(len(g) for g in pools.values())} across {len(pools)} zones")


if __name__ == '__main__':
    main()
