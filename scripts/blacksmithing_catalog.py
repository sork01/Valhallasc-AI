#!/usr/bin/env python3
"""Add smith stock and deterministic mining candidates to the finished world."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from fishing_spots import SCALE, SURFACES, clear_of_hubs_and_seams, radius, walkable

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'blacksmithing'
WORKSHOP = 'blacksmithing_workshop'
SMITHS = {
    0: {'smith'}, 1: {'anvil_bror'}, 4: {'city_smith'}, 6: {'wyrd_smith'},
    7: {'sky_brokk'}, 8: {'deep_ketil', 'deep_gw_hallbjorn'}, 9: {'nacre_smith'},
    13: {'astral_cw_oren'}, 17: {'asterion_smith', 'ew_citysmith'},
    22: {'tg_sp_odile'}, 24: {'hw_smith'}, 45: {'ew_smith', 'ew_cw_sten'},
}


def candidates(area):
    reachable = walkable(area)
    surfaces = [o for o in area['objects'] if o['kind'] in SURFACES]
    floor = area.get('shapeFloor')
    points = []
    stride = SCALE * 4
    for iy, ix in np.argwhere(reachable[2::stride, 2::stride]):
        x, y = (int(ix) * stride + 2.5) / SCALE, (int(iy) * stride + 2.5) / SCALE
        if floor and floor[int(y)][int(x)] != '#':
            continue
        if not clear_of_hubs_and_seams(area, x, y):
            continue
        if any(math.hypot(x - p['x'], y - p['y']) < 7 for p in area.get('portals', [])):
            continue
        if any(math.hypot(x - s['x'], y - s['y']) <= radius(s) + 3 for s in surfaces):
            continue
        if any(math.hypot(x - p['x'], y - p['y']) < 4 for p in area['slimes']):
            continue
        # The half-tile flood supplies a walkable approach. Require standable
        # ground on at least two sides so the sprite can be reached from either.
        half_x, half_y = int(x * SCALE), int(y * SCALE)
        if sum(reachable[half_y + dy, half_x + dx] for dx, dy in [(0, 3), (3, 0), (0, -3), (-3, 0)]
               if 0 <= half_y + dy < reachable.shape[0] and 0 <= half_x + dx < reachable.shape[1]) < 2:
            continue
        points.append((x, y))

    picked = []
    if points:
        # Seed the spread near the arrival to put at least one candidate on
        # familiar ground, then cover different parts of the connected terrain.
        spawn = area['spawn']
        nearest = min(range(len(points)), key=lambda i: math.dist(points[i], (spawn['x'], spawn['y'])))
        picked.append(points.pop(nearest))
        distances = [math.dist(point, picked[0]) for point in points]
        while points and len(picked) < 10:
            farthest = max(range(len(points)), key=distances.__getitem__)
            if distances.pop(farthest) < 12:
                break
            point = points.pop(farthest)
            picked.append(point)
            distances = [min(distance, math.dist(pos, point)) for pos, distance in zip(points, distances)]
    if len(picked) < 2:
        raise ValueError(f"{area['name']}: only {len(picked)} reachable mining candidates")
    return [dict(x=x, y=y) for x, y in picked]


def apply(catalog, world, items):
    # Replace the Blacksmithing block in place, preserving later profession overlays.
    start = next((i for i, item in enumerate(items) if item.get('source') == SOURCE), len(items))
    items[:] = [i for i in items if i.get('source') != SOURCE]
    original = {i['id']: i for i in items}
    entries = []
    picks = {p['item'] for p in catalog['picks']}
    stock = []
    for material in catalog['materials']:
        entry = dict(id=material['id'], name=material['name'], source=SOURCE, rarity='common',
                     sell=material.get('sell', 0), kind='mining_pick' if material['id'] in picks else 'material')
        entries.append(entry)
        if 'price' in material:
            stock.append(dict(id='buy_' + entry['id'], label='Buy ' + entry['name'],
                              item=entry['id'], cost=material['price']))
    for spec in catalog['gear']:
        template = original[spec['template']]
        entry = {key: template[key] for key in ('kind', 'rarity', 'class', 'attack', 'defense', 'bonusStats', 'tint')
                 if key in template}
        factor = .90 if entry['rarity'] == 'epic' else 1.
        for key in ('attack', 'defense'):
            entry[key] = round(entry.get(key, 0) * factor, 1)
        if 'bonusStats' in entry:
            entry['bonusStats'] = {key: int(value * factor) for key, value in entry['bonusStats'].items()}
        entry.update(id=spec['id'], name=spec['name'], source=SOURCE, sell=template['sell'],
                     requiredLevel=spec['level'], variant=spec['id'], art=template.get('art', template['variant']))
        entries.append(entry)
    by_id = original | {i['id']: i for i in entries}
    for recipe in catalog['recipes']:
        if recipe.get('plan'):
            gear = by_id[recipe['item']]
            entries.append(dict(id=recipe['plan'], name='Blueprint: ' + gear['name'], kind='smith_blueprint',
                              rarity=gear['rarity'], sell=gear['sell'] // 2, source=SOURCE))
    items[start:start] = entries

    regions = [world, *world['zones']]
    for zone, area in enumerate(regions):
        smiths = SMITHS.get(zone, set())
        for npc in area.get('npcs', []):
            npc['offers'] = [o for o in npc['offers'] if o['id'] != WORKSHOP and not o['id'].startswith('buy_smith_')]
            if npc['id'] in smiths:
                npc['offers'].extend([dict(id=WORKSHOP, label='Blacksmithing workshop', cost=0), *stock])
        if smiths - {npc['id'] for npc in area.get('npcs', [])}:
            raise ValueError(f"Missing town smith in zone {zone}")
    return {str(zone): candidates(regions[zone]) for tier in catalog['tiers'] for zone in tier['zones']}


def write(path, data, **options):
    (ROOT / path).write_text(json.dumps(data, ensure_ascii=False, **options) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-catalogs', action='store_true',
                        help='also refresh the two client catalogs from the finished world')
    args = parser.parse_args()
    read = lambda path: json.loads((ROOT / path).read_text())
    catalog = read('world/blacksmithing.txt')
    world, items = read('world/map.txt'), read('world/items.txt')
    veins = apply(catalog, world, items)
    write('world/mining-veins.txt', veins, indent=2)
    write('world/map.txt', world, indent=2)
    write('world/items.txt', items, indent=2)
    client_catalog = {key: catalog[key] for key in ('tiers', 'picks', 'recipes')}
    results = {'blacksmithing-data': ('BLACKSMITHING_DATA', client_catalog)}
    if args.publish_catalogs:
        results.update(world=('WORLD_MAP', world), items=('WORLD_ITEMS', items))
    for filename, (key, data) in results.items():
        encoded = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        (ROOT / f'client/{filename}.js').write_text(f"'use strict';\nwindow.{key} = {encoded};\n")
    print('Mining candidates:', ', '.join(f"{key}={len(value)}" for key, value in veins.items()))


if __name__ == '__main__':
    main()
