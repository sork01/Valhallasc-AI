"""Check the generated enchanting stock and items without changing the worktree."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('enchanting_catalog', ROOT / 'scripts/enchanting_catalog.py')
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)

def read(path):
    return json.loads((ROOT / path).read_text())

def generated(path):
    return json.loads((ROOT / path).read_text().split(' = ', 1)[1].strip().removesuffix(';'))

catalog = read('world/enchanting.txt')
world, items, art = read('world/map.txt'), read('world/items.txt'), read('client/assets/npc.txt')
original = copy.deepcopy((world, items, art))
overlay.apply(catalog, items, world, art)
assert (world, items, art) == original, 'the overlay must be idempotent'
assert catalog == generated('client/enchanting-data.js')
assert items == generated('client/items.js')
assert world == generated('client/world.js')
enchants = catalog['enchants']
assert len(enchants) == 16
assert len({e['id'] for e in enchants}) == len(enchants)
assert [sum(e['tier'] == n for e in enchants) for n in range(3)] == [5, 6, 5]
stock = {i['id']: i for i in items if i.get('source') == 'enchanting'}
assert len(stock) == 36
assert [t['skill'] for t in catalog['tiers']] == [1, 75, 180]
assert [t['vendorPrice'] for t in catalog['tiers']] == [250_000, 1_000_000, 4_000_000]
assert [m['rarity'] for m in catalog['materials'] if m['id'] == 'enchant_core'] == ['legendary']
assert all(e['cost'][-1] == (e['tier'] == 2) for e in enchants)
masters = {entry[0]: zone for zone, entry in overlay.MASTERS.items()}
seen = set()
for index, zone in enumerate([world, *world['zones']]):
    for npc in zone['npcs']:
        if npc['id'] in masters:
            assert index == masters[npc['id']]
            assert npc['offers'][0] == {'id':'learn_enchanting','label':'Learn Enchanting','cost':0}
            _, _, template = overlay.MASTERS[index]
            assert art['npcs'][npc['id']] == art['npcs'][template]
            without_master = {**zone, 'npcs': [other for other in zone['npcs'] if other['id'] != npc['id']]}
            # The deterministic overlay already verifies collision, portal clearance and reachability.
            anchor = next(other for other in zone['npcs'] if other['id'] == overlay.MASTERS[index][1])
            pos = overlay.reachable_service_position(without_master, anchor)
            assert (npc['x'], npc['y']) == tuple(round(value, 3) for value in pos)
            seen.add(npc['id'])
        else:
            assert not any(offer['id'] == 'learn_enchanting' for offer in npc['offers'])
        recipes = [offer for offer in npc['offers'] if offer['id'].startswith('buy_enchant_recipe_')]
        assert len(recipes) == (len(enchants) if npc['id'] in masters else 0)
        for offer, enchant in zip(recipes, enchants):
            tier = catalog['tiers'][enchant['tier']]
            assert offer['item'] == f"enchant_recipe_{enchant['id']}"
            assert offer['cost'] == tier['vendorPrice']
            assert stock[offer['item']]['rarity'] == tier['rarity']
assert set(masters) == seen
for enchant in enchants:
    rarity = catalog['tiers'][enchant['tier']]['rarity']
    assert any(row['rarity'] == rarity and row['kind'] == enchant['kind'] for row in items)
print('Enchanting catalog, sixteen recipes, reachable stock owners and generated client data agree')
