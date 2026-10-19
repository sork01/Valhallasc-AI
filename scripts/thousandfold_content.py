"""Level-75 Thousandfold Pavilion encounters shared by map and sprite generators."""

ENEMIES = [
    dict(kind='pavilion_foldling', name='Paper Foldling', art='foldling', color='#ecc3d8',
         stats=[390000, 5200, 3.5, 1.3], profile=[.45, 1.2, 10, 10],
         ranged=None, slam=0, melee=0, boss=False),
    dict(kind='pavilion_inkmoth', name='Inkwing Moth', art='inkmoth', color='#8e9bd5',
         stats=[345000, 4600, 3.0, 1.45], profile=[.7, 1.75, 0, 12],
         ranged=[12, 10, '#9e9ce8', .95, 2, .22], slam=0, melee=0, boss=False),
    dict(kind='pavilion_silkguard', name='Silkguard', art='silkguard', color='#d3a6ba',
         stats=[450000, 6100, 2.5, 1.8], profile=[.85, 1.6, 8, 10],
         ranged=None, slam=3.0, melee=0, boss=False),
    dict(kind='pavilion_mirror', name='The Mirror Dancer', art='mirror', color='#d7bce9',
         stats=[1900000, 14500, 2.8, 2.15], profile=[.8, 1.7, 8, 12],
         ranged=None, slam=3.9, melee=0, boss=True),
    dict(kind='pavilion_weaver', name='The Thousandfold Weaver', art='weaver', color='#a9b5e8',
         stats=[2050000, 12100, 2.5, 2.2], profile=[.85, 2.05, 0, 14],
         ranged=[14, 10, '#c7b9fb', 1.15, 3, .28], slam=0, melee=0, boss=True),
    dict(kind='pavilion_sovereign', name='Sovereign of the Last Fold', art='sovereign', color='#efcaad',
         stats=[5600000, 18200, 2.1, 2.75], profile=[1.1, 2.15, 7, 16],
         ranged=[14, 11, '#f5d2be', 1.25, 5, .3], slam=4.6, melee=4.8, boss=True),
]

for enemy in ENEMIES:
    enemy.update(level=75, gold=8100 if enemy['boss'] else 1950,
                 material=enemy['kind'] + '_relic',
                 lootSource='thousandfold' if enemy['boss'] else None)

BOSSES = [enemy['kind'] for enemy in ENEMIES if enemy['boss']]

if __name__ == '__main__':
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    (root / 'world/thousandfold.txt').write_text(json.dumps(ENEMIES, indent=2) + '\n')
    path = root / 'world/items.txt'
    items = json.loads(path.read_text())
    ids = {i['id'] for i in items}
    for enemy in ENEMIES:
        if enemy['material'] not in ids:
            items.append(dict(id=enemy['material'], name=enemy['name'].removeprefix('The ') + ' Relic',
                              kind='material', rarity='common',
                              sell=4700 if enemy['boss'] else 2000))
    path.write_text(json.dumps(items, indent=2) + '\n')
