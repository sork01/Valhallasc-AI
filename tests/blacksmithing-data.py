"""Catalog, gear budget, sprite exports, and stable overlay coverage."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import blacksmithing_catalog as overlay


def read(path):
    return json.loads((ROOT / path).read_text())


def generated(path):
    return json.loads((ROOT / path).read_text().split(' = ', 1)[1].strip().removesuffix(';'))


catalog = read('world/blacksmithing.txt')
world, items = read('world/map.txt'), read('world/items.txt')
regions = [world, *world['zones']]
veins = read('world/mining-veins.txt')
if os.getenv('MUTATE') == 'no-alternate':
    veins['0'] = veins['0'][:1]

assert len(catalog['tiers']) == 10
eligible = {str(i) for i,z in enumerate(regions) if z['slimes'] and not z.get('copies') and not z.get('interior')}
assert set(veins) == eligible
for key, points in veins.items():
    assert len(points) >= 2, f'No alternate vein location in {key}'
    assert len({(p['x'], p['y']) for p in points}) == len(points)

area, item_list = copy.deepcopy((world, items))
assert overlay.apply(catalog, area, item_list) == veins
assert (area, item_list) == (world, items), 'The overlay must be idempotent'
assert world == generated('client/world.js')
assert items == generated('client/items.js')
assert generated('client/blacksmithing-data.js') == {key:catalog[key] for key in ('tiers','picks','recipes')}

for i, area in enumerate(regions):
    for npc in area['npcs']:
        offers = [offer for offer in npc['offers'] if offer['id'] == overlay.WORKSHOP]
        assert bool(offers) == (npc['id'] in overlay.SMITHS.get(i, set()))
        if offers:
            shop = {o.get('item') for o in npc['offers']}
            assert {m['id'] for m in catalog['materials'] if 'price' in m} <= shop

by_id = {i['id']:i for i in items}
assert len(items) == len(by_id)
picks = catalog['picks']
assert [p['reaches'] for p in picks] == [1,3,5,7,9]
recipes = {r['item']:r for r in catalog['recipes']}
assert len(recipes) == len(catalog['recipes']) == 39
for tier, row in enumerate(catalog['tiers']):
    smelt, = [r for r in recipes.values() if r['method'] == 'smelt' and r['tier'] == tier]
    assert smelt['skill'] == max(tier * 30, 1)
    assert smelt['ingredients'][0] == [row['ore'], 2]
    assert smelt['ingredients'][1:] == ([['smith_charcoal', 1]] if tier == 2 else [])
    staple, = [r for r in recipes.values() if r['method'] == 'staple' and r['tier'] == tier]
    rare, = [r for r in recipes.values() if r['method'] == 'rare' and r['tier'] == tier]
    assert rare['ingredients'][0][1] == (staple['ingredients'][0][1] * 3 + 1) // 2
    assert rare['ingredients'][-1][1] == 2
    assert max(staple['skill'],rare['skill']) == max(1, tier * 30)
    if tier in [1,3,5,7]:
        index = (tier+1)//2
        upgrade = recipes[picks[index]['item']]
        assert upgrade['skill'] == tier*30
        assert picks[index-1]['reaches'] == tier
        assert upgrade['ingredients'] == [[picks[index-1]['item'],1],[smelt['item'],4],['smith_hardwood',2]]
        assert upgrade['cost'] > 0

modes = {'staple':'uncommon', 'rare':'rare', 'epic':'epic'}
for r in recipes.values():
    assert all(i in by_id and n > 0 for i,n in r['ingredients'])
    if r['method'] in modes:
        output = by_id[r['item']]
        assert output['rarity'] == modes[r['method']] and output['source'] == 'blacksmithing'
        if r['method'] == 'epic':
            ref = by_id[next(g['template'] for g in catalog['gear'] if g['id'] == output['id'])]
            assert r['skill'] == 300 and ref['requiredLevel'] == output['requiredLevel'] == 99
            assert output['attack'] <= ref['attack'] and output['defense'] <= ref['defense']
            assert all(n <= ref['bonusStats'][stat] for stat,n in output['bonusStats'].items())
        if r.get('plan'):
            assert by_id[r['plan']]['kind'] == 'smith_blueprint'

art = generated('client/blacksmithing-art.js')
expected = {i['id'] for i in items if i.get('source') == 'blacksmithing'
            and i['kind'] in {'material','mining_pick','smith_blueprint'}}
assert set(art['at']) == expected | {f'vein_{n}' for n in range(10)}
atlas = Image.open(ROOT / 'client/assets/blacksmithing.png').convert('RGBA')
cells = set()
for x,y in art['at'].values():
    size = art['size']
    pixels = atlas.crop((x*size,y*size,(x+1)*size,(y+1)*size))
    bounds = pixels.getbbox()
    assert bounds and min(bounds[:2]) > 0 and max(bounds[2:]) < size
    cells.add(pixels.tobytes())
assert len(cells) == len(art['at']) == 54
for cue, spec in read('client/assets/blacksmithing-sounds.txt')['clips'].items():
    file = ROOT / 'client/assets' / spec['file']
    assert hashlib.sha256(file.read_bytes()).hexdigest() == spec['sha256']
    decoded = subprocess.check_output(['ffmpeg','-v','error','-i',str(file),'-f','f32le','-ac','1','-ar','44100','pipe:1'])
    peak = np.max(np.abs(np.frombuffer(decoded,dtype='<f4')))
    assert .01 < peak < 1, f'{cue}: inaudible or clipped'
print(f'Blacksmithing data: {len(veins)} zone pools, {len(recipes)} recipes, {len(cells)} unique frames, three decoded cues')
