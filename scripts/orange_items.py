#!/usr/bin/env python3
"""Sync all fifty orange catalog entries from world/orange_rules.txt.

The manifest owns the roll ranges; catalog minima are only a fallback for test shortcuts
or older saves without a per-copy record. Real kills save sampled GearInstances.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rules = json.loads((ROOT / 'world/orange_rules.txt').read_text())
catalog_path = ROOT / 'world/items.txt'
catalog = json.loads(catalog_path.read_text())
catalog = [item for item in catalog if item.get('source') != 'orange_pool']
for piece in rules['pieces']:
    assert piece['class'] is None and piece['requiredLevel'] == 1
    catalog.append(dict(id=piece['id'], name=piece['name'], kind=piece['slot'],
                        rarity='legendary', requiredLevel=1, sell=500,
                        attack=piece['rolls']['attack'][0],
                        defense=piece['rolls']['defense'][0],
                        bonusStats={key: piece['rolls'][key][0]
                                    for key in ('stamina', 'accuracy', 'dexterity')},
                        **{'class': None}, variant=piece['id'],
                        source='orange_pool'))
assert len({i['id'] for i in catalog}) == len(catalog)
catalog_path.write_text(json.dumps(catalog, indent=2) + '\n')
print('Synced 50 orange catalog pieces')
