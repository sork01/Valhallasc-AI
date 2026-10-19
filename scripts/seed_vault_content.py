"""Level-80 Seed Vault encounters shared by map and editable sprite generators."""
import json
from pathlib import Path

ENEMIES = [
    dict(kind='seed_mote', name='Awakened Seedling', art='mote', color='#bdd77b',
         stats=[505000, 6500, 3.4, 1.25], profile=[.5, 1.3, 10, 11],
         ranged=None, slam=0, melee=0, boss=False),
    dict(kind='seed_amberwing', name='Amberwing Moth', art='amberwing', color='#e8bd76',
         stats=[455000, 5850, 3.1, 1.45], profile=[.7, 1.8, 0, 13],
         ranged=[13, 10, '#eacb83', 1, 2, .22], slam=0, melee=0, boss=False),
    dict(kind='seed_rootguard', name='Heartroot Guard', art='rootguard', color='#9ac284',
         stats=[585000, 7750, 2.55, 1.8], profile=[.9, 1.55, 8, 11],
         ranged=None, slam=3.2, melee=0, boss=False),
    dict(kind='seed_warden', name='Warden of Rings', art='warden', color='#9fc67c',
         stats=[2520000, 16800, 2.8, 2.1], profile=[.85, 1.75, 9, 12],
         ranged=None, slam=4.2, melee=0, boss=True),
    dict(kind='seed_germinator', name='The Germinator', art='germinator', color='#d9c986',
         stats=[2710000, 14800, 2.5, 2.2], profile=[.9, 2.1, 0, 14],
         ranged=[15, 10, '#d7e7a6', 1.2, 3, .29], slam=0, melee=0, boss=True),
    dict(kind='seed_worldseed', name='Heart of the Worldseed', art='worldseed', color='#e4dc9c',
         stats=[6600000, 22000, 2.2, 2.75], profile=[1.1, 2.2, 8, 16],
         ranged=[15, 11, '#f0e9b9', 1.35, 5, .31], slam=4.9, melee=5.1, boss=True),
    # Adds of Germination (docs/boss-mechanics.md): they drop nothing and have their own art (boss_helper_cel_redraw.py).
    dict(kind='seed_sprout', name='Worldseed Seed', art='mote', color='#e9d78e',
         stats=[60000, 3000, 1, 1.0], profile=[.9, 1.8, 0, 6],
         ranged=None, slam=0, melee=0, boss=False, add=True),
    dict(kind='seed_treant', name='Bloom Treant', art='rootguard', color='#b6d98c',
         stats=[120000, 7000, 2.4, 2.0], profile=[.9, 1.55, 8, 11],
         ranged=None, slam=3.0, melee=0, boss=False, add=True),
]

for enemy in ENEMIES:
    enemy.update(level=80, gold=9600 if enemy['boss'] else 2320,
                 material=enemy['kind'] + '_relic',
                 lootSource='seed_vault' if enemy['boss'] else None)
BOSSES = [enemy['kind'] for enemy in ENEMIES if enemy['boss']]

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    (root / 'world/seed_vault.txt').write_text(json.dumps(ENEMIES, indent=2) + '\n')
    path = root / 'world/items.txt'
    items = json.loads(path.read_text())
    ids = {item['id'] for item in items}
    for enemy in ENEMIES:
        if enemy['material'] not in ids:
            items.append(dict(id=enemy['material'], name=enemy['name'].removeprefix('The ') + ' Relic',
                              kind='material', rarity='common', sell=5500 if enemy['boss'] else 2350))
    path.write_text(json.dumps(items, indent=2) + '\n')
