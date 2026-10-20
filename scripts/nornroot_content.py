"""Level-25 Nornroot Barrow catalog; shared by map, art and runtime exports."""
ENEMIES = [
    dict(kind='barrow_scarab', name='Graveamber Scarab', color='#d99a48', art='scarab',
         stats=[11000, 500, 2.8, 1.35], profile=[.55, 1.3, 9, 12], ranged=None, slam=0, melee=0, boss=False),
    dict(kind='barrow_hound', name='Threadbound Hound', color='#827cc8', art='hound',
         stats=[12500, 550, 3.3, 1.45], profile=[.45, 1.15, 10, 12], ranged=None, slam=0, melee=0, boss=False),
    dict(kind='barrow_spinner', name='Spindle Shade', color='#9dd3ba', art='spinner',
         stats=[9500, 460, 2.4, 1.35], profile=[.8, 1.8, 0, 13],
         ranged=[12, 10, '#eacb85', .9, 1, 0], slam=0, melee=0, boss=False),
    dict(kind='barrow_doorward', name='Arn, the Amber Doorward', color='#c59d68', art='doorward',
         stats=[85000, 1800, 2.2, 2.1], profile=[1., 1.8, 7, 14], ranged=None, slam=3.5, melee=0, boss=True),
    dict(kind='barrow_threadkeeper', name='Vessa, Keeper of Threads', color='#b78ebf', art='keeper',
         stats=[90000, 1600, 0.0, 2.0], profile=[.9, 1.9, 0, 14],
         ranged=[14, 10, '#e6b7e6', 1.1, 3, .22], slam=0, melee=0, boss=True),
    dict(kind='barrow_fatebound', name='The Unwritten King', color='#e3c77b', art='king',
         stats=[140000, 2100, 2.1, 2.4], profile=[1.1, 1.9, 6, 16], ranged=None, slam=3.8, melee=0, boss=True),
]
for e in ENEMIES:
    e.update(level=25, gold=1100 if e['boss'] else 260,
             material=e['kind'] + '_relic', lootSource='nornroot' if e['boss'] else None)
BOSSES = [e['kind'] for e in ENEMIES if e['boss']]
