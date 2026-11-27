#!/usr/bin/env python3
"""Append the GM's permanent festival island. Safe to run last in sync-world, twice.

No existing zone is regenerated. File zone IDs stay stable; appended instance IDs
move by one on first installation (see docs/gm-island.md).
"""
import json
import copy
import math
import random
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZE, CX, CY = 424, 212, 212
TOWNS = [
    ("christmas", "Hollyhaven", 145, 122, "Christmas village", "christmasGrandTree", "christmasGifts", "year_holly"),
    ("newyear", "Midnight Quay", 273, 122, "New Year village", "newyearLaunchpad", "festivalLantern", "year_iceobelisk"),
    ("halloween", "Pumpkin Hollow", 315, 217, "Halloween village", "festivalPumpkins", "festivalPumpkins", "year_leafpile"),
    ("solstice", "Sunribbon", 275, 302, "Midsummer village", "solsticePole", "solsticeFlowers", "year_sunpine"),
    ("easter", "Blossombell", 145, 302, "Easter village", "easterGrandEgg", "easterBasket", "year_bloomtree"),
    ("valentine", "Roseheart", 106, 217, "Valentine village", "valentineGrandHeart", "valentineRoses", "year_bloomtree"),
]


def distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / (dx*dx+dy*dy or 1)))
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


def build():
    rng = random.Random(20261127)
    floor = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            a = math.atan2((y-CY)/138, (x-CX)/158)
            coast = 1 + .025*math.sin(5*a) + .012*math.cos(9*a)
            row.append('#' if ((x-CX)/158)**2 + ((y-CY)/138)**2 < coast else ' ')
        floor.append(''.join(row))
    edges = [''.join(' ' if c == '#' else 'c' for c in row) for row in floor]
    z = dict(name="GM Island", theme="gm_island", gmOnly=True, size=SIZE,
             spawn=dict(x=212, y=337), objects=[], npcs=[], quests=[], slimes=[],
             city=None, camps=[], portals=[], places=[], shapeFloor=floor, shapeEdge=edges,
             paths=[], gmIsland=dict(arena=[184, 174, 240, 224], dummyYard=[176, 256, 248, 282], towns=[]))
    objects = z['objects']

    def obj(kind, x, y, r=0, **extra):
        objects.append(dict(kind=kind, x=x, y=y, r=r, v=rng.randrange(4), **extra))

    def npc(id_, name, role, x, y, dialogue, service=None, art='special_travel_springmere'):
        n = dict(id='gmi_'+id_, name=name, role=role, x=x, y=y, color='#d9bc73',
                 dialogue=dialogue, offers=[], art=art)
        if service:
            n['offers'] = [dict(id='gmi:'+service, label='Open '+role, cost=0)]
        z['npcs'].append(n)
        return n

    centres = [(t[2], t[3]) for t in TOWNS]
    for _, _, x, y, *_ in TOWNS:
        z['paths'].append([[212, 240], [x, y]])
    z['paths'] += [[[212, 337], [212, 282], [212, 240], [212, 224]],
                   [[176, 269], [248, 269]], [[184, 229], [240, 229]],
                   [list(p) for p in centres + centres[:1]]]
    for season, name, x, y, role, centre, detail, tree in TOWNS:
        z['gmIsland']['towns'].append(dict(id=season, name=name, x=x, y=y))
        z['camps'].append(dict(name=name, x0=x-21, x1=x+21, y0=y-19, y1=y+19,
                               plaza=dict(x=x, y=y), radius=5, entry=dict(x=x, y=y+18)))
        z['places'].append(dict(id='gmi_'+season, name=name, x=x, y=y, r=18))
        obj(centre, x, y-3, .8)
        for i, (dx, dy) in enumerate([(-13,-10),(13,-10),(-13,11),(13,11)]):
            obj('meadow_cottage', x+dx, y+dy, width=5, depth=4,
                style='stone' if season in ('christmas','newyear') else 'thatch', label=name)
            obj(detail, x+dx+3, y+dy+3, .3)
        for dx, dy in [(-18,-15),(18,-15),(-18,15),(18,15)]:
            obj(tree, x+dx, y+dy, .6)
        npc('host_'+season, name+' Keeper', role, x+3, y+4,
            role+' all year round. The island paths lead to the arena and the training yard.')
        master = npc('travel_'+season, 'Spark Keeper of '+name, 'Travel Master', x-4, y+4,
                     'Fly between the island villages. These routes never leave GM Island.')
        master['travelStop'] = name
        master['travelLinks'] = ['gmi_travel_'+s for s, *_ in TOWNS if s != season]
    npc('summoner', 'Edda the Summoner', 'Arena summoner', 242, 229,
        'Choose any monster or boss. Each summon is a new island opponent; the original world stays untouched.', 'summon')
    npc('quartermaster', 'Torvald the Quartermaster', 'Gear and level', 184, 233,
        'Choose a level, class and a full equipment set. Your original character is saved until you leave.', 'setup')
    npc('mentor', 'Saga the Class Mentor', 'Class mentor', 190, 237,
        'All five classes are available. Recommended attributes and normal class damage make comparisons fair.', 'setup')
    npc('recruiter', 'Runa the Recruiter', 'Mercenary recruiter', 242, 235,
        'Summon up to four companions of any class for free. They stay on the island.', 'mercs')
    npc('trainer', 'Bjorn the Trainer', 'DPS training', 172, 269,
        'The dummies cannot die, move or attack. Reset the DPS meter here, or heal and clear your cooldowns.', 'training')
    npc('ferryman', 'Isle Warden', 'Island travel', 216, 335,
        'GM Island is private. Leaving restores your character and removes your island summons.', 'travel')
    for i, level in enumerate((1, 20, 40, 60, 80, 99)):
        z['slimes'].append(dict(kind='gmi_dummy', x=182+i*12, y=265, level=level))
    # Broken railings leave four broad, walkable arena entrances.
    for x in range(184, 241, 4):
        if abs(x-212)>6:
            for y in (174,224): obj('gmi_rail', x, y, width=3.7, depth=.4)
    for y in range(178,224,4):
        if abs(y-199)>6:
            for x in (184,240): obj('gmi_rail', x,y,width=.4,depth=3.7)
    for x,y in ((184,174),(240,174),(184,224),(240,224)):
        obj('gmi_pillar',x,y,.65)
    segments = [(a,b) for path in z['paths'] for a,b in zip(path,path[1:])]
    # Seeded scenery follows six holiday groves; keep roads and all services open.
    for _ in range(1150):
        x,y = rng.randrange(52,374),rng.randrange(72,352)
        if floor[y][x]!='#' or min(distance((x,y),a,b) for a,b in segments)<5: continue
        if 166<x<255 and 162<y<290: continue
        if any(math.hypot(x-tx,y-ty)<29 for tx,ty in centres): continue
        town = min(TOWNS,key=lambda t:math.hypot(x-t[2],y-t[3]))
        obj(town[-1], x+.5,y+.5,.55)
    validate(z)
    return z


def validate(z):
    blocked=set()
    for o in z['objects']:
        rx=o.get('width',0)/2+.45 if o.get('width') else o['r']+.45
        ry=o.get('depth',0)/2+.45 if o.get('depth') else o['r']+.45
        # Ground decals have no collision geometry.
        if o['kind']=='gmi_target_pad': continue
        for y in range(math.floor(o['y']-ry),math.ceil(o['y']+ry)+1):
            for x in range(math.floor(o['x']-rx),math.ceil(o['x']+rx)+1):
                if abs(x+.5-o['x'])<rx and abs(y+.5-o['y'])<ry: blocked.add((x,y))
    start=(int(z['spawn']['x']),int(z['spawn']['y']))
    seen={start}; todo=deque([start])
    while todo:
        x,y=todo.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            a,b=p
            if p not in seen and p not in blocked and 0<=a<SIZE and 0<=b<SIZE and z['shapeFloor'][b][a]=='#':
                seen.add(p);todo.append(p)
    for p in z['npcs']+z['slimes']+z['places']:
        assert (int(p['x']),int(p['y'])) in seen, p
    assert len(seen)>64000, len(seen)


def install():
    file=ROOT/'world/map.txt'
    m=json.loads(file.read_text())
    existing=[i for i,z in enumerate(m['zones']) if z.get('gmOnly')]
    index=existing[0] if existing else len(m['zones'])
    z=build()
    z['portals']=[dict(id='gmi_return',name='Greenmeadow',x=212,y=343,r=1.5,to=0,
                       tx=m['spawn']['x'],ty=m['spawn']['y'])]
    if existing: m['zones'][index]=z
    else: m['zones'].append(z)
    m['portals']=[p for p in m['portals'] if p['id']!='gmi_gate']
    m['portals'].append(dict(id='gmi_gate', name='GM Island', x=276,y=226,r=1.5,
                             to=index+1,tx=212,ty=337,gmOnly=True))
    file.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
    install_art(z)
    print('GM Island: zone',index+1,'land',sum(r.count('#') for r in z['shapeFloor']),
          'NPCs',len(z['npcs']),'objects',len(z['objects']))


def install_art(z):
    """Assign existing player-style designs without altering a single atlas."""
    file=ROOT/'client/assets/npc.txt'
    meta=json.loads(file.read_text())
    aliases={'gmi_quartermaster':'smith','gmi_mentor':'healer',
             'gmi_recruiter':'gatekeeper','gmi_trainer':'gatekeeper','gmi_ferryman':'dock_skipper'}
    meta['npcs']={k:v for k,v in meta['npcs'].items() if not k.startswith('gmi_')}
    for n in z['npcs']:
        meta['npcs'][n['id']]=copy.deepcopy(meta['npcs'][aliases.get(n['id'],'travel_springmere')])
    file.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')


def detach():
    """Public generators must see the pre-island world, including its portal list."""
    file=ROOT/'world/map.txt'
    m=json.loads(file.read_text())
    indices=[i for i,z in enumerate(m['zones']) if z.get('gmOnly')]
    if indices:
        assert len(indices)==1, 'Expected one GM island'
        index=indices[0]
        if index==len(m['zones'])-1:
            m['zones'].pop()
        else:
            # Later generators may append zones: reserve this ID while public
            # overlays run, rather than shifting any of those later zone IDs.
            m['zones'][index]=dict(name='GM Island',theme='gm_island',gmOnly=True,
                size=SIZE,spawn=dict(x=212,y=337),objects=[],slimes=[],npcs=[],
                quests=[],portals=[],city=None)
    m['portals']=[p for p in m['portals'] if p['id']!='gmi_gate']
    file.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':
    detach() if '--detach' in sys.argv else install()
