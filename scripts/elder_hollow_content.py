"""Authoritative level-70 Elder Hollow encounters shared by map and sprite generators."""

ENEMIES = [
    dict(kind='elder_thornling', name='Thornling', art='thornling', color='#8eb86d',
         stats=[305000, 4200, 3.4, 1.35], profile=[.45, 1.15, 10, 9],
         ranged=None, slam=0, melee=0, boss=False),
    dict(kind='elder_moth', name='Lantern Moth', art='moth', color='#d7bf86',
         stats=[270000, 3700, 3.0, 1.4], profile=[.6, 1.7, 0, 12],
         ranged=[12, 10, '#efdb9b', .9, 2, .2], slam=0, melee=0, boss=False),
    dict(kind='elder_barkguard', name='Barkguard', art='barkguard', color='#8f7656',
         stats=[360000, 4800, 2.5, 1.75], profile=[.85, 1.55, 8, 10],
         ranged=None, slam=2.8, melee=0, boss=False),
    dict(kind='elder_gatekeeper', name='The Knotted Gatekeeper', art='gatekeeper', color='#b9a075',
         stats=[1650000, 12000, 2.2, 2.2], profile=[1., 1.85, 7, 12],
         ranged=None, slam=3.8, melee=0, boss=True),
    dict(kind='elder_matron', name='The Pollen Matron', art='matron', color='#cbb88a',
         stats=[1750000, 10200, 2.5, 2.1], profile=[.9, 2.0, 0, 14],
         ranged=[14, 10, '#f3d59c', 1.1, 3, .28], slam=0, melee=0, boss=True),
    dict(kind='elder_heart', name='Heart of the Elder', art='heart', color='#b5d18d',
         stats=[4700000, 15500, 2.0, 2.8], profile=[1.1, 2.1, 7, 16],
         ranged=[14, 11, '#d3f2a8', 1.2, 5, .3], slam=4.5, melee=4.7, boss=True),
]

for enemy in ENEMIES:
    enemy.update(level=70, gold=7400 if enemy['boss'] else 1750,
                 material=enemy['kind'] + '_relic',
                 lootSource='elder_hollow' if enemy['boss'] else None)

BOSSES = [enemy['kind'] for enemy in ENEMIES if enemy['boss']]

if __name__ == '__main__':
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    (root / 'world/elder_hollow.txt').write_text(json.dumps(ENEMIES, indent=2) + '\n')
