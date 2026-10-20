"""The Black Hour Foundry: level-99 giant industrial clockwork enemies."""
ENEMIES = [
    dict(kind='null_hauler', name='Kilnback Hauler', art='hauler', color='#a267e0',
         stats=[1110000,13900,2.4,1.6], profile=[.8,1.6,8,13], ranged=None, slam=3.4, melee=0, boss=False),
    dict(kind='null_breaker', name='Pendulum Breaker', art='breaker', color='#728ea9',
         stats=[1280000,16300,2.2,1.8], profile=[1.,1.8,8,13], ranged=None, slam=3.8, melee=0, boss=False),
    dict(kind='null_coil', name='Coil Cathedral', art='coil', color='#61e6dc',
         stats=[960000,13500,2.,1.5], profile=[.9,2.,0,14], ranged=[17,11,'#8af6eb',1.,3,.24], slam=0, melee=0, boss=False),
    dict(kind='null_bell', name='Vark, the Twelve-Ton Bell', art='bell', color='#bd8ae9',
         stats=[5500000,35300,2.,2.6], profile=[1.,2.,8,15], ranged=[18,10,'#be96f6',1.1,3,.25], slam=4., melee=4.5, boss=True),
    dict(kind='null_conductor', name='Iona, Mistress of the Dead Current', art='conductor', color='#67d9e8',
         stats=[5100000,33800,0.,2.6], profile=[1.,2.,0,15], ranged=[19,11,'#83f5ec',1.2,5,.28], slam=0, melee=0, boss=True),
    dict(kind='null_hour', name='The Thirteenth Hour', art='hour', color='#c5a4f4',
         stats=[15000000,45000,1.8,3.1], profile=[1.2,2.3,8,18], ranged=[20,12,'#b7f8ef',1.3,5,.3], slam=4.8, melee=5., boss=True),
]
for e in ENEMIES:
    e.update(level=99, gold=48000 if e['boss'] else 8500,
             material=e['kind']+'_relic', lootSource='blackhour' if e['boss'] else None)
BOSSES = [e['kind'] for e in ENEMIES if e['boss']]
