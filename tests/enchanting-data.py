"""Check the generated enchanting stock and items without changing the worktree."""
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('enchanting_catalog', ROOT / 'scripts/enchanting_catalog.py')
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)

def read(path):
    return json.loads((ROOT / path).read_text())

def generated(path):
    return json.loads((ROOT / path).read_text().split(' = ', 1)[1].strip().removesuffix(';'))

catalog = read('world/enchanting.txt')
world, items = read('world/map.txt'), read('world/items.txt')
original = copy.deepcopy((world, items))
overlay.apply(catalog, items, world)
assert (world, items) == original, 'the overlay must be idempotent'
assert catalog == generated('client/enchanting-data.js')
assert items == generated('client/items.js')
assert world == generated('client/world.js')
enchants = catalog['enchants']
assert len(enchants) == 16
assert len({e['id'] for e in enchants}) == len(enchants)
assert [sum(e['tier'] == n for e in enchants) for n in range(3)] == [5, 6, 5]
stock = {i['id']: i for i in items if i.get('source') == 'enchanting'}
assert len(stock) == 36
assert [t['skill'] for t in catalog['tiers']] == [1, 25, 60]
assert [t['vendorPrice'] for t in catalog['tiers']] == [250_000, 1_000_000, 4_000_000]
assert [m['rarity'] for m in catalog['materials'] if m['id'] == 'enchant_core'] == ['legendary']
assert all(e['cost'][-1] == (e['tier'] == 2) for e in enchants)
for zone in [world, *world['zones']]:
    for npc in zone['npcs']:
        recipes = [offer for offer in npc['offers'] if offer['id'].startswith('buy_enchant_recipe_')]
        assert len(recipes) == (len(enchants) if npc['id'] in overlay.VENDORS else 0)
        for offer, enchant in zip(recipes, enchants):
            tier = catalog['tiers'][enchant['tier']]
            assert offer['item'] == f"enchant_recipe_{enchant['id']}"
            assert offer['cost'] == tier['vendorPrice']
            assert stock[offer['item']]['rarity'] == tier['rarity']
for enchant in enchants:
    rarity = catalog['tiers'][enchant['tier']]['rarity']
    assert any(row['rarity'] == rarity and row['kind'] == enchant['kind'] for row in items)
print('Enchanting catalog, sixteen recipes, reachable stock owners and generated client data agree')
