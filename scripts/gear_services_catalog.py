#!/usr/bin/env python3
"""Install Alderhaven's gearwright and the refinement crystal catalog once."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
items_path = root/'world/items.txt'
items = json.loads(items_path.read_text())
known = {i['id'] for i in items}
factors = {'common': 1, 'uncommon': 2, 'rare': 4, 'epic': 8, 'legendary': 12}
for rarity, factor in factors.items():
    id_ = 'refinement_crystal_'+rarity
    if id_ not in known:
        items.append(dict(id=id_, name=rarity.title()+' Refinement Crystal',
                          kind='material', rarity='common', sell=12*factor))
items_path.write_text(json.dumps(items, indent=2, ensure_ascii=False)+'\n')

map_path = root/'world/map.txt'
world = json.loads(map_path.read_text())
if not any(n['id'] == 'gearwright' for n in world['npcs']):
    offers = [dict(id='merge', label='Merge two equipment copies', cost=0),
              dict(id='refine', label='Refine one equipment copy', cost=0)]
    for rarity, factor in factors.items():
        offers.append(dict(id='crystal_'+rarity,
                           label='Buy '+rarity.title()+' Refinement Crystal',
                           cost=25*factor, item='refinement_crystal_'+rarity))
    world['npcs'].append(dict(id='gearwright', name='Alda Copperhand', role='Gearwright',
        x=36, y=91, color='#d5a474', dialogue='I can merge two matching spare pieces or refine any piece with matching crystals and gold. Choose copies carefully: a merge keeps the lower refinement rank.',
        offers=offers, buys=False, look=dict(skin='#bd9471',hair='#866d59',style='braid',hat='none',hatColor='#866d59')))
map_path.write_text(json.dumps(world, indent=2)+'\n')
