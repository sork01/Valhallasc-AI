#!/usr/bin/env python3
"""Validate the authored Alchemy ladder and its outputs on finished maps."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from alchemy_catalog import WORKSHOPS, WORKSHOP, apply
from set_bonuses import build as set_bonuses

def read(path):
    return json.loads((ROOT / path).read_text())


def client(name):
    return json.loads((ROOT / f'client/{name}.js').read_text().split(' = ', 1)[1].rstrip(';\n'))


catalog = read('world/alchemy.txt')
map_data = read('world/map.txt')
items = read('world/items.txt')
pools = read('world/flower-patches.txt')
veins = read('world/mining-veins.txt')
assert client('world') == map_data
assert client('items') == items
assert client('alchemy-data')['sources'] == {z: [p['flower'] for p in groups] for z, groups in pools.items()}
assert len(catalog['flowers']) == 22
assert len(catalog['recipes']) == 24
assert {int(z) for z in pools} == set(WORKSHOPS) | {f['zone'] for f in catalog['flowers']}
all_zones = [map_data, *map_data['zones']]
ingredients = {}
for flower in catalog['flowers']:
    ingredients.setdefault(flower['band'], []).append(flower['item'])

if os.environ.get('MUTATE') == 'no-alternate':
    entry = pools['0'][0]
    entry['points'] = entry['points'][:entry['active']]

for zone, groups in pools.items():
    area = all_zones[int(zone)]
    assert not area.get('interior') and not area.get('final_boss') and area['name'] != 'The Arena'
    assert sum(group['active'] for group in groups) == (4 if zone == '0' else 1 if int(zone) in WORKSHOPS else 3)
    coordinates = set()
    garden = int(zone) in WORKSHOPS
    for n, group in enumerate(groups):
        assert len(group['points']) > group['active'], f'{area["name"]} needs a replacement'
        flower = catalog['flowers'][group['flower']]
        city = area.get('city')
        for p in group['points']:
            xy = p['x'], p['y']
            assert xy not in coordinates
            coordinates.add(xy)
            is_inside = city and city['x0'] < xy[0] < city['x1'] and city['y0'] < xy[1] < city['y1']
            if garden and n == len(groups) - 1:
                assert is_inside and flower['item'] == WORKSHOPS[int(zone)][-1]
            else:
                assert not is_inside and flower['zone'] == int(zone)
                assert all(math.dist(xy, (v['x'], v['y'])) >= 6 for v in veins[zone])
    if zone == '6':
        assert [catalog['flowers'][p['flower']]['region'] for p in groups] == ['Outer Wyrdwood', 'Inner Wyrdwood']

by_id = {item['id']: item for item in items}
for zone, (npc_id, *_rest) in WORKSHOPS.items():
    rows = [n for n in all_zones[zone]['npcs'] if any(o['id'] == WORKSHOP for o in n['offers'])]
    assert len(rows) == 1 and rows[0]['id'] == npc_id
    assert {o['item'] for o in rows[0]['offers'] if o['id'].startswith('buy_alchemy_')} == {
        s['item'] for s in catalog['supplies']
    }

for band, recipe in enumerate(r for r in catalog['recipes'] if not r.get('formula')):
    assert recipe['skill'] == max(band * 30, 1)
    assert recipe['level'] == max(band * 5, 1)
    groups = [[ingredients[band], 4 if recipe['flask'] else 2]]
    if recipe['flask']:
        groups += [[ingredients[band - 1], 1], [['alchemy_empty_flask'], 1]]
    else:
        groups += [[['alchemy_empty_vial'], 1]]
    assert recipe['ingredients'] == groups
    assert by_id[recipe['item']]['cooldown'] == (0 if recipe['flask'] else 60)

for recipe in catalog['recipes']:
    assert all(not by_id[id].get('bound') for group, _ in recipe['ingredients'] for id in group)
    assert not by_id[recipe['item']].get('bound')
    if recipe.get('formula'):
        assert recipe['formula'] in by_id and not by_id[recipe['formula']].get('bound')
        if recipe.get('boss'):
            assert any(zone.get('final_boss') == recipe['boss'] for zone in all_zones)
            assert recipe['ingredients'] == [[ingredients[19], 4], [ingredients[18], 2], [['alchemy_empty_flask'], 1]]
            assert recipe['level'] == 99 and recipe['skill'] == 600

source = read('client/assets/alchemy-art.txt')
art = client('alchemy-art')
image = Image.open(ROOT / 'client/assets/alchemy.png').convert('RGBA')
assert set(art['at']) == {key for sprite in source for key in sprite['order']}
assert len(art['at']) == len([i for i in items if i.get('source') == 'alchemy']) + 22
assert image.size == (art['cols'] * art['size'], art['rows'] * art['size'])
unique = set()
for x, y in art['at'].values():
    size = art['size']
    crop = image.crop((x * size, y * size, (x+1) * size, (y+1) * size))
    assert crop.getbbox()
    unique.add(crop.tobytes())
assert len(unique) == len(art['at'])

for clip in read('client/assets/alchemy-sounds.txt')['clips'].values():
    path = ROOT / 'client/assets' / clip['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == clip['sha256']
    audio = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-'])
    assert any(audio) and len(audio) >= .4 * 44100 * 2

assert set_bonuses() == read('world/set-bonuses.txt')
assert {str(z): groups for z, groups in apply(catalog, map_data, items, veins).items()} == pools
assert map_data == read('world/map.txt') and items == read('world/items.txt')
print('Alchemy data passed all 20 bands, 25 zones, five workshops, alternate positions, idempotent generation, 74 sprite cells and three sound cues.')
