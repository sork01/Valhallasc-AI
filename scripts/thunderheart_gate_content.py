"""Level-95 Thunderheart Gate encounters and exclusive boss loot."""
import json
from pathlib import Path

ENEMIES = [
    dict(kind='thunder_spark', name='Forked Spark', art='spark', color='#b9d8f2', stats=[860000, 11200, 3.5, 1.3], profile=[.55, 1.25, 10, 12], ranged=None, slam=0, melee=0, boss=False),
    dict(kind='thunder_ray', name='Stormglass Ray', art='ray', color='#8faedc', stats=[770000, 10400, 3.1, 1.55], profile=[.65, 1.95, 0, 13], ranged=[14, 11, '#b9ddff', 1, 2, .23], slam=0, melee=0, boss=False),
    dict(kind='thunder_guard', name='Slatebound Guard', art='guard', color='#8f9baa', stats=[990000, 12800, 2.55, 1.85], profile=[.95, 1.6, 9, 12], ranged=None, slam=3.5, melee=0, boss=False),
    dict(kind='thunder_conductor', name='Storm Conductor', art='conductor', color='#c0d1e6', stats=[4200000, 27500, 2.7, 2.3], profile=[.9, 1.8, 10, 14], ranged=[16, 11, '#d7f1ff', 1.2, 3, .27], slam=4.5, melee=0, boss=True),
    dict(kind='thunder_bastion', name='The Thunder Bastion', art='bastion', color='#a8b6c8', stats=[4600000, 29000, 2.35, 2.55], profile=[1.0, 1.6, 9, 15], ranged=None, slam=5.1, melee=4.8, boss=True),
    dict(kind='thunder_heart', name='Heart of the Stormgate', art='heart', color='#e0e4f2', stats=[6500000, 36500, 2.1, 3.0], profile=[1.15, 2.25, 10, 17], ranged=[17, 12, '#e7f5ff', 1.4, 5, .32], slam=5.5, melee=5.5, boss=True),
]
for enemy in ENEMIES:
    enemy.update(level=95,gold=17000 if enemy['boss'] else 4200,
                 material=enemy['kind']+'_relic',lootSource='thunderheart_gate' if enemy['boss'] else None)
BOSSES=[e['kind'] for e in ENEMIES if e['boss']]

if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    (root/'world/thunderheart_gate.txt').write_text(json.dumps(ENEMIES,indent=2)+'\n')
    path=root/'world/items.txt';items=json.loads(path.read_text());ids={i['id'] for i in items}
    for e in ENEMIES:
        if e['material'] not in ids:
            items.append(dict(id=e['material'],name=e['name'].removeprefix('The ')+' Relic',kind='material',rarity='common',sell=8500 if e['boss'] else 3700))
    path.write_text(json.dumps(items,indent=2)+'\n')
