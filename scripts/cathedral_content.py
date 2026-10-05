"""Drowned Cathedral encounter catalog, shared by map, sprite and music generators."""
WINGS = [
    dict(id='cloister', name='Flooded Cloister', level=40, size=160, theme='cathedral_left',
         door=(84, 28), return_=(84, 34), color='#64daca',
         tagline='The left wing: drowned gardens, broken bells and the bound choir',
         centers=[(24,140),(24,104),(60,104),(100,104),(136,104),(136,64),(100,64),(100,24),(60,24)],
         exclusive='tideleech', bosses=['bellkeeper','mournsister','rootabbot','choirmother']),
    dict(id='reliquary', name='Coral Reliquary', level=45, size=160, theme='cathedral_right',
         door=(108, 28), return_=(108, 34), color='#f29cb4',
         tagline='The right wing: rose-coral galleries, pearl tombs and stolen relics',
         centers=[(136,140),(100,140),(100,104),(64,104),(64,68),(100,68),(136,68),(136,28),(100,28)],
         exclusive='reliccrab', bosses=['pearlwidow','glasscantor','relicwarden','coralregent']),
    dict(id='nave', name='Grand Nave', level=50, size=192, theme='cathedral_main',
         door=(96, 28.5), return_=(96, 35), color='#d5b9ff',
         tagline='The main wing: black marble, drowned stars and the Heart of the Tide',
         centers=[(96,172),(96,136),(40,136),(40,88),(96,88),(152,88),(152,40),(112,40),(72,40)],
         exclusive='abysszealot', bosses=['chainmarshal','starseraph','tidejudicator','hierophant']),
]

# hp, damage, speed, visual scale; windup/cooldown/charge/awareness; ranged missile and slam use existing combat rules.
def enemy(kind, name, level, hp, damage, speed, scale, profile, art, color, boss=False,
          ranged=None, slam=0, melee=0, variant=0):
    return dict(kind=kind, name=name, level=level, stats=[hp,round(damage*.65) if boss else damage,speed,scale], profile=profile,
                art=art, color=color, boss=boss, gold=(4000 + level*40 if boss else 850 + level*8),
                material='cathedral_'+kind, ranged=ranged, slam=slam, melee=melee, variant=variant)

ENEMIES = [
    enemy('tidetemplar','Drowned Templar',40,34000,1050,2.5,1.4,[.65,1.5,7.5,9],'knight','#84bbb7'),
    enemy('tidecantor','Bound Cantor',40,26000,800,2.4,1.25,[.75,2.3,0,12],'cantor','#8cd4ee',ranged=[11,9,'#89e4ea',.9,2,.18]),
    enemy('tideleech','Cloister Tide Leech',40,28000,900,3.6,1.35,[.3,1,11,9],'leech','#78b78a'),
    enemy('reliccrab','Reliquary Crab',45,48000,1400,2.1,1.6,[.9,1.8,6,8],'crab','#e999b0',slam=2.8),
    enemy('abysszealot','Abyssal Zealot',50,47000,1250,2.8,1.35,[.8,2,0,13],'cantor','#b295e8',ranged=[12,11,'#c6a3ff',1,3,.3],variant=1),
    enemy('bellkeeper','Orrin, the Sunken Bellkeeper',40,240000,3000,2.2,2,[1.1,2.1,7,11],'bell','#70cbbc',True,slam=3.8),
    enemy('mournsister','Sister Veyra of the Stillwater',40,260000,2000,2.5,1.8,[.9,2.6,0,14],'cantor','#a3d9e5',True,ranged=[12,9,'#a3e6ff',1.1,3,.36],variant=2),
    enemy('rootabbot','Abbot Thorne, the Kelpbound',40,300000,3400,1.9,2.2,[1.15,2.3,6,11],'root','#7aaa75',True,slam=4.2),
    enemy('choirmother','Elyss, Mother of the Bound Choir',40,330000,2300,2.4,2,[1,2.2,0,14],'choir','#74e8db',True,ranged=[13,10,'#72f4e0',1.2,5,.28],variant=3),
    enemy('pearlwidow','Neritha, the Pearl Widow',45,300000,2900,3.1,2,[.65,1.6,10,12],'spider','#f1b4c7',True,variant=4),
    enemy('glasscantor','Ilyr, Cantor of Shattered Glass',45,330000,2400,2.5,1.9,[.8,2.2,0,14],'glass','#e5a4de',True,ranged=[13,14,'#ffa8de',.8,5,.38]),
    enemy('relicwarden','Sarkhos, Warden of the Reliquary',45,350000,3800,2.3,2.1,[1,2,8,12],'crab','#df957c',True,slam=3.5,variant=5),
    enemy('coralregent','Queen Avariel, the Coral Regent',45,400000,3000,2.6,2.1,[.9,1.9,8.5,14],'regent','#ec8db9',True,ranged=[13,10,'#ffb9d5',1,3,.24],melee=4.5,slam=3.2),
    enemy('chainmarshal','Vargast, Marshal of the Drowned Chains',50,370000,4100,2.6,2.1,[1,1.8,9,12],'chain','#909daf',True,slam=3.6),
    enemy('starseraph','Astrael, the Fallen Tide Seraph',50,390000,3000,2.8,2,[.9,2.3,0,15],'seraph','#d0c9ef',True,ranged=[14,12,'#d9c4ff',1,5,.3]),
    enemy('tidejudicator','The Blind Tide Judicator',50,420000,4500,2,2.3,[1.2,2.4,7,12],'judge','#c2bbaa',True,slam=4.5),
    enemy('hierophant','High Hierophant Vael, Heart of the Tide',50,480000,3500,2.6,2.2,[1,2,9,15],'hierophant','#b392ed',True,ranged=[14,11,'#be9dff',1.25,5,.32],melee=4.8,slam=4),
]
