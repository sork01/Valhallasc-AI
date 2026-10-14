"""Level-85 Sunken Astrolabe encounter catalog and salvage."""
import json
from pathlib import Path

ENEMIES = [
    dict(kind='astro_gearling', name='Brass Gearling', art='gearling', color='#c99b59', stats=[640000, 7900, 3.5, 1.25], profile=[.55, 1.25, 9, 12], ranged=None, slam=0, melee=0, boss=False),
    dict(kind='astro_starling', name='Fallen Starling', art='starling', color='#88c9d8', stats=[560000, 7300, 3.15, 1.5], profile=[.65, 1.9, 0, 13], ranged=[13, 10, '#a9e8f1', 1, 2, .22], slam=0, melee=0, boss=False),
    dict(kind='astro_sentinel', name='Orrery Sentinel', art='sentinel', color='#ad9874', stats=[740000, 9100, 2.6, 1.8], profile=[.9, 1.5, 8, 12], ranged=None, slam=3.4, melee=0, boss=False),
    dict(kind='astro_warden', name='Meridian Warden', art='warden', color='#c9a969', stats=[3100000, 19800, 2.8, 2.2], profile=[.85, 1.7, 10, 13], ranged=None, slam=4.3, melee=0, boss=True),
    dict(kind='astro_navigator', name='The Lost Navigator', art='navigator', color='#8cbcc8', stats=[3300000, 18600, 2.5, 2.3], profile=[.9, 2.0, 0, 14], ranged=[15, 10, '#b3edec', 1.2, 3, .28], slam=0, melee=0, boss=True),
    dict(kind='astro_axis', name='Axis of the Buried Sky', art='axis', color='#e6ca85', stats=[4900000, 26000, 2.2, 2.8], profile=[1.1, 2.2, 9, 16], ranged=[16, 11, '#f8e9b0', 1.35, 5, .31], slam=5, melee=5.2, boss=True),
]
for enemy in ENEMIES:
    enemy.update(level=85, gold=12500 if enemy['boss'] else 3000,
                 material=enemy['kind']+'_relic', lootSource='sunken_astrolabe' if enemy['boss'] else None)
BOSSES = [e['kind'] for e in ENEMIES if e['boss']]

if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    (root/'world/sunken_astrolabe.txt').write_text(json.dumps(ENEMIES,indent=2)+'\n')
    path=root/'world/items.txt';items=json.loads(path.read_text());ids={i['id'] for i in items}
    for e in ENEMIES:
        if e['material'] not in ids:
            items.append(dict(id=e['material'],name=e['name'].removeprefix('The ')+' Relic',kind='material',rarity='common',sell=7000 if e['boss'] else 2950))
    path.write_text(json.dumps(items,indent=2)+'\n')
