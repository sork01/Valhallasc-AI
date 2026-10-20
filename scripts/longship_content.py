"""The Drowned Longship (level 35): a ship's crew and scavengers, not cathedral enemies."""
ENEMIES = [
 dict(kind='keel_crab',name='Copperclaw Scavenger',art='crab',color='#67b7a3',stats=[19500,920,2.8,1.4],profile=[.55,1.3,9,12],ranged=None,slam=0,melee=0,boss=False),
 dict(kind='keel_deckhand',name='Drowned Deckhand',art='deckhand',color='#c48256',stats=[22500,1020,3.1,1.5],profile=[.5,1.3,10,12],ranged=None,slam=0,melee=0,boss=False),
 dict(kind='keel_lantern',name='Bilge Lantern',art='lantern',color='#83dec4',stats=[17000,840,2.4,1.35],profile=[.8,1.8,0,13],ranged=[12,10,'#83e5cf',.9,1,0],slam=0,melee=0,boss=False),
 dict(kind='keel_cargomaw',name='Gullveig, the Cargo Maw',art='cargomaw',color='#d69b6a',stats=[175000,3000,2.0,2.2],profile=[1.,1.85,7,14],ranged=None,slam=3.6,melee=0,boss=True),
 dict(kind='keel_bosun',name='Bosun Brinehook',art='bosun',color='#78b5b4',stats=[185000,2700,0.,2.1],profile=[.9,1.9,0,14],ranged=[14,10,'#e5b987',1.,3,.22],slam=0,melee=0,boss=True),
 dict(kind='keel_captain',name='Captain Svala Nineknots',art='captain',color='#e1af72',stats=[270000,3300,2.0,2.4],profile=[1.1,1.9,6,16],ranged=None,slam=3.8,melee=0,boss=True),
]
for e in ENEMIES:
 e.update(level=35,gold=1850 if e['boss'] else 390,material=e['kind']+'_relic',lootSource='longship' if e['boss'] else None)
BOSSES=[e['kind'] for e in ENEMIES if e['boss']]
