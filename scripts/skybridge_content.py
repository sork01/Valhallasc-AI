"""Level-30 The Shattered Span catalog; shared by map, art and runtime exports."""
ENEMIES = [
    dict(kind='span_lynx', name='Prism Lynx', color='#76d8f0', art='lynx',
         stats=[15500, 680, 3.2, 1.38], profile=[.45, 1.15, 10, 12], ranged=None, slam=0, melee=0, boss=False),
    dict(kind='span_sentinel', name='Bifrost Sentinel', color='#f0be68', art='sentinel',
         stats=[18000, 740, 2.7, 1.48], profile=[.6, 1.35, 8.5, 12], ranged=None, slam=0, melee=0, boss=False),
    dict(kind='span_caster', name='Arcane Refractor', color='#d694f5', art='caster',
         stats=[13500, 620, 2.4, 1.35], profile=[.8, 1.85, 0, 13],
         ranged=[12, 10, '#8fe8ff', .9, 1, 0], slam=0, melee=0, boss=False),
    dict(kind='span_warden', name='Torstein, Keeper of the Toll', color='#e8b85c', art='warden',
         stats=[115000, 2200, 2.2, 2.1], profile=[1., 1.85, 7, 14], ranged=None, slam=3.6, melee=0, boss=True),
    dict(kind='span_weaver', name='Sunniva, the Spectrum Weaver', color='#c88cf2', art='weaver',
         stats=[122000, 1950, 0.0, 2.0], profile=[.9, 1.9, 0, 14],
         ranged=[14, 10, '#f0a8ff', 1.1, 3, .22], slam=0, melee=0, boss=True),
    dict(kind='span_archon', name='Bifrost Archon Vaelor', color='#7ce6ff', art='archon',
         stats=[185000, 2550, 2.1, 2.4], profile=[1.1, 1.9, 6, 16], ranged=None, slam=3.9, melee=0, boss=True),
]
for e in ENEMIES:
    e.update(level=30, gold=1450 if e['boss'] else 340,
             material=e['kind'] + '_relic', lootSource='skybridge' if e['boss'] else None)
BOSSES = [e['kind'] for e in ENEMIES if e['boss']]
