"""Check that gathering and its upgrades become available in map order."""

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / 'world' / f'{name}.txt').read_text())


world = load('map')
areas = [world, *world['zones']]
levels = [area.get('levels', [60 if index == 17 else 1])[0]
          for index, area in enumerate(areas)]


def regional_bands(bands):
    assert len(bands) == 20
    by_level = [min(levels[zone] for zone in band) for band in bands]
    assert by_level == sorted(by_level), by_level


fishing = load('fishing-skill')
mining = load('blacksmithing')['trainingZones']
for bands in (fishing, mining):
    regional_bands(bands)
    assert bands[4:6] == [[6], [7]]
assert fishing[6] == [13] and mining[6:8] == [[8], [13]]
assert mining[7:11] == [[13], [14], [15], [16]]

alchemy = load('alchemy')
flowers = {flower['item']: flower for flower in alchemy['flowers']}
regional_bands([[f['zone'] for f in flowers.values() if f['band'] == band] for band in range(20)])
assert flowers['alchemy_rainbow_aster']['band'] == 6
assert flowers['alchemy_tideglass_anemone']['band'] == 7
for recipe in alchemy['recipes']:
    band = recipe['skill'] // 30
    ingredient_bands = {flowers[name]['band'] for names, _ in recipe['ingredients'] for name in names if name in flowers}
    assert max(ingredient_bands) <= band, recipe['item']
    if band < 20 and not recipe.get('formula'):
        assert band in ingredient_bands, recipe['item']

waters = load('fishing-waters')
fish = {species['item']: species for species in load('fish')}
rods = {row['item']: row for row in load('rods')}
assert set(waters) == {str(zone) for band in fishing for zone in band}
required = {zone: rod for rod in rods.values() for zone in rod['zones']}
assert required[7]['item'] == 'rod_reedglass_rod'
assert all(rod['level'] <= levels[zone] for zone, rod in required.items())

source = (ROOT / 'server/src/items.rs').read_text().split('pub fn material(', 1)[1].split('\npub fn ', 1)[0]
material = dict(re.findall(r'"(\w+)"\s*=>\s*"(\w+)"', source))
for recipe in load('fishing-workshop'):
    if recipe['item'] not in rods:
        continue
    output = rods[recipe['item']]
    prior = rods[recipe['ingredients'][0][0]]
    species = fish[recipe['ingredients'][1][0]]
    component = recipe['ingredients'][2][0]
    first_required = min((levels[zone] for zone in output['zones']), default=output['level'])
    catch_zones = [int(zone) for zone, water in waters.items() if water['habitat'] == species['habitat']
                   and species.get('zone') in (None, int(zone))]
    assert any(max(levels[zone], prior['level']) <= first_required
               and max(required[zone]['tier'], species['min_tier']) <= prior['tier']
               for zone in catch_zones), recipe['id']
    assert any(levels[index] <= first_required and any(material.get(s['kind'], 'slime_gel') == component for s in area['slimes'])
               for index, area in enumerate(areas)), (recipe['id'], component)
    assert any(levels[zone] <= first_required for zone in recipe['zones']), recipe['id']

print('Map order checked for all 20 gathering bands, every rod upgrade, and every Alchemy recipe')
