"""Authoritative Eye Below encounter data, shared with the map and sprite generators."""

ENEMIES = [
    dict(kind='eye_drifter', name='Silt Drifter', art='drifter', color='#6cb9c8',
         stats=[230000, 3300, 3.4, 1.4], profile=[.4, 1.1, 10, 10],
         ranged=None, slam=0, melee=0, boss=False),
    dict(kind='eye_lurker', name='Glassjaw Lurker', art='lurker', color='#a291c8',
         stats=[270000, 3900, 2.7, 1.65], profile=[.65, 1.35, 8, 9],
         ranged=None, slam=0, melee=0, boss=False),
    dict(kind='eye_adept', name='Veil Adept', art='adept', color='#99d8dc',
         stats=[215000, 2900, 2.3, 1.5], profile=[.8, 1.85, 0, 12],
         ranged=[12, 10, '#8ae6ee', .9, 2, .2], slam=0, melee=0, boss=False),
    dict(kind='eye_lenswarden', name='The Lenswarden', art='warden', color='#d7b287',
         stats=[1250000, 10500, 2.1, 2.2], profile=[1., 1.9, 7, 12],
         ranged=None, slam=3.8, melee=0, boss=True),
    dict(kind='eye_undertide', name='The Undertide Sibyl', art='sibyl', color='#93ddd3',
         stats=[1450000, 9200, 2.4, 2.2], profile=[.9, 2.2, 0, 14],
         ranged=[14, 10, '#a2fff0', 1.1, 3, .3], slam=0, melee=0, boss=True),
    dict(kind='eye_unblinking', name='The Unblinking Eye', art='eye', color='#f0ca8d',
         stats=[2200000, 14000, 2.0, 2.7], profile=[1.1, 2.0, 6, 16],
         ranged=[14, 11, '#f4d4a2', 1.2, 5, .3], slam=4.2, melee=4.5, boss=True),
]

for e in ENEMIES:
    e.update(level=65, gold=6800 if e['boss'] else 1550,
             material=e['kind'] + '_relic', lootSource='eye_below' if e['boss'] else None)

BOSSES = [e['kind'] for e in ENEMIES if e['boss']]
