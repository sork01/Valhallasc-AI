"""Level-80 Temple of the Rain Crown encounters shared by map and sprite generators."""
import json
from pathlib import Path

ENEMIES = [
    dict(kind='rain_crown_droplet', name='Crowned Droplet', art='droplet', color='#85dfd1',
         stats=[475000, 6100, 3.5, 1.25], profile=[.55, 1.35, 9, 11],
         ranged=None, slam=0, melee=0, boss=False),
    dict(kind='rain_crown_oracle', name='Jade Rain Oracle', art='oracle', color='#a0d8ae',
         stats=[430000, 5700, 3.0, 1.4], profile=[.75, 1.8, 0, 13],
         ranged=[13, 10, '#8ff0d9', 1, 2, .24], slam=0, melee=0, boss=False),
    dict(kind='rain_crown_guard', name='Monsoon Guard', art='guard', color='#6da6b3',
         stats=[570000, 7500, 2.6, 1.8], profile=[.9, 1.6, 8, 11],
         ranged=None, slam=3.1, melee=0, boss=False),
    dict(kind='rain_crown_gatekeeper', name='Keeper of the Floodgate', art='gatekeeper', color='#78c9bb',
         stats=[2450000, 16400, 2.8, 2.1], profile=[.85, 1.8, 9, 12],
         ranged=None, slam=4.1, melee=0, boss=True),
    dict(kind='rain_crown_sibyl', name='Sibyl of the Rain', art='sibyl', color='#b0dfc2',
         stats=[2600000, 14300, 2.5, 2.2], profile=[.9, 2.1, 0, 14],
         ranged=[15, 10, '#b7efde', 1.2, 3, .28], slam=0, melee=0, boss=True),
    dict(kind='rain_crown_sovereign', name='The Rain Crown', art='sovereign', color='#d4eab2',
         stats=[3900000, 21000, 2.2, 2.75], profile=[1.1, 2.2, 8, 16],
         ranged=[15, 11, '#c9f7dc', 1.35, 5, .32], slam=4.8, melee=5.0, boss=True),
]

for enemy in ENEMIES:
    enemy.update(level=80, gold=9400 if enemy['boss'] else 2250,
                 material=enemy['kind'] + '_relic',
                 lootSource='rain_crown' if enemy['boss'] else None)

BOSSES = [enemy['kind'] for enemy in ENEMIES if enemy['boss']]

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    (root / 'world/rain_crown.txt').write_text(json.dumps(ENEMIES, indent=2) + '\n')
    path = root / 'world/items.txt'
    items = json.loads(path.read_text())
    ids = {i['id'] for i in items}
    for enemy in ENEMIES:
        if enemy['material'] not in ids:
            items.append(dict(id=enemy['material'], name=enemy['name'].removeprefix('The ') + ' Relic',
                              kind='material', rarity='common',
                              sell=5400 if enemy['boss'] else 2300))
    path.write_text(json.dumps(items, indent=2) + '\n')
