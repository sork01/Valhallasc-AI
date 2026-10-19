"""Level-98 Solar Crucible encounter catalog; its entrance remains sealed."""
import json
from pathlib import Path

ENEMIES = [
    dict(kind='solar_emberling', name='Cinderling', art='emberling', color='#f6ad60', stats=[1010000, 13100, 3.5, 1.35], profile=[.5, 1.3, 10, 13], ranged=None, slam=0, melee=0, boss=False),
    dict(kind='solar_sunmoth', name='Sunmoth', art='sunmoth', color='#ffe095', stats=[890000, 12500, 3.5, 1.55], profile=[.7, 1.9, 0, 14], ranged=[16, 11, '#ffe7a1', 1, 2, .25], slam=0, melee=0, boss=False),
    dict(kind='solar_crucible_guard', name='Crucible Guard', art='guard', color='#c98259', stats=[1150000, 15100, 2.5, 1.9], profile=[1, 1.6, 9, 13], ranged=None, slam=3.8, melee=0, boss=False),
    dict(kind='solar_ashwarden', name='Ashwarden', art='ashwarden', color='#c78463', stats=[5100000, 33000, 2.5, 2.45], profile=[.9, 1.8, 10, 15], ranged=None, slam=4.9, melee=4.6, boss=True),
    dict(kind='solar_heliomancer', name='The Heliomancer', art='heliomancer', color='#ffe28b', stats=[4850000, 31400, 2.8, 2.4], profile=[.8, 2, 0, 15], ranged=[18, 11, '#fff3af', 1.25, 4, .29], slam=0, melee=0, boss=True),
    dict(kind='solar_heart', name='Heart of the Crucible', art='heart', color='#ffcf6c', stats=[8200000, 42000, 2.1, 3.1], profile=[1.2, 2.3, 10, 18], ranged=[19, 12, '#fff4bf', 1.5, 5, .33], slam=5.8, melee=5.8, boss=True),
    # Cinder, the ash half of the Heart once it divides (Twin Suns, docs/boss-mechanics.md). It takes the Heart's health when the
    # fight divides it, drops nothing and has its own art (boss_helper_cel_redraw.py).
    dict(kind='solar_cinder', name='Cinder of the Crucible', art='heart', color='#c8b6ab', stats=[7600000, 36000, 2.1, 3.0], profile=[1.2, 2.3, 10, 18], ranged=None, slam=6.0, melee=0, boss=False, add=True),
]
for enemy in ENEMIES:
    enemy.update(level=98, gold=21000 if enemy['boss'] else 5000,
                 material=enemy['kind']+'_relic', lootSource='solar_crucible' if enemy['boss'] else None)
BOSSES = [e['kind'] for e in ENEMIES if e['boss']]

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    (root/'world/solar_crucible.txt').write_text(json.dumps(ENEMIES, indent=2)+'\n')
    path = root/'world/items.txt'; items = json.loads(path.read_text()); ids = {i['id'] for i in items}
    for e in ENEMIES:
        if e['material'] not in ids:
            items.append(dict(id=e['material'], name=e['name']+' Relic', kind='material', rarity='common', sell=10000 if e['boss'] else 4400))
    path.write_text(json.dumps(items, indent=2)+'\n')
