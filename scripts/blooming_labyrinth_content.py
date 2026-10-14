"""Level-97 Blooming Labyrinth encounters; entrance remains sealed."""
import json
from pathlib import Path

ENEMIES = [
    dict(kind='bloom_spore', name='Glasspetal Spore', art='spore', color='#b8e8af', stats=[940000, 11900, 3.1, 1.3], profile=[.5, 1.3, 10, 13], ranged=None, slam=0, melee=0, boss=False),
    dict(kind='bloom_moth', name='Prismwing Moth', art='moth', color='#e8a8d1', stats=[830000, 11400, 3.5, 1.55], profile=[.7, 1.9, 0, 14], ranged=[15, 11, '#f9d7ed', 1, 2, .25], slam=0, melee=0, boss=False),
    dict(kind='bloom_guard', name='Vineglass Guardian', art='guard', color='#94bd8e', stats=[1080000, 13700, 2.5, 1.9], profile=[1, 1.6, 9, 13], ranged=None, slam=3.7, melee=0, boss=False),
    dict(kind='bloom_thornkeeper', name='Thornkeeper', art='thornkeeper', color='#88bc75', stats=[4800000, 30500, 2.5, 2.45], profile=[.9, 1.8, 10, 15], ranged=None, slam=4.8, melee=4.5, boss=True),
    dict(kind='bloom_mirror', name='Petal Mirror', art='mirror', color='#e3a9d8', stats=[4500000, 28700, 2.8, 2.4], profile=[.8, 2.0, 10, 15], ranged=[17, 11, '#ffe6f4', 1.25, 4, .29], slam=0, melee=0, boss=True),
    dict(kind='bloom_heart', name='Heart of the Labyrinth', art='heart', color='#f2c5dc', stats=[7000000, 39000, 2.1, 3.1], profile=[1.2, 2.3, 10, 18], ranged=[18, 12, '#f8f6df', 1.5, 5, .33], slam=5.6, melee=5.6, boss=True),
]
for enemy in ENEMIES:
    enemy.update(level=97, gold=19000 if enemy['boss'] else 4600,
                 material=enemy['kind']+'_relic', lootSource='blooming_labyrinth' if enemy['boss'] else None)
BOSSES=[e['kind'] for e in ENEMIES if e['boss']]

if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    (root/'world/blooming_labyrinth.txt').write_text(json.dumps(ENEMIES,indent=2)+'\n')
    path=root/'world/items.txt';items=json.loads(path.read_text());ids={i['id'] for i in items}
    for e in ENEMIES:
        if e['material'] not in ids:
            items.append(dict(id=e['material'],name=e['name']+' Relic',kind='material',rarity='common',sell=9000 if e['boss'] else 4000))
    path.write_text(json.dumps(items,indent=2)+'\n')
