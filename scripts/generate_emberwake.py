#!/usr/bin/env python3
"""Seeded public volcanic approach to Eldmarr's sealed door (file zone 45).

python3 scripts/generate_emberwake.py [--check]
The raid door is scenery and a readable seal until RAID-MAP/RAID-OPEN.
"""
import argparse
import json
import math
import random
from pathlib import Path
import generate_gloamfen as fen
from mercenary_offers import offers
from skaldholm_content import look
from emberwake_content import ENEMIES

ROOT = Path(__file__).resolve().parents[1]
NAME, THEME, ZONE, PARENT, SIZE = 'Emberwake Caldera', 'emberwake', 45, 17, 160
GATE, LANDING, ARRIVAL = (90,18), (90,25), (22,137)
ROAD = [[22,137],[35,123],[47,104],[71,96],[84,76],[106,65],[122,45],[133,26]]

def obj(kind,x,y,r=0,**kw):
    return dict(kind=kind,x=x,y=y,r=r,v=0,**kw)

def npc(id,name,role,x,y,text,service=False):
    return dict(id='ew_'+id,name=name,role=role,x=x,y=y,color='#697184',dialogue=text,
        offers=offers(open_=True) if service else [],
        look=look('#c69a7b','#533c39','braid','hood',apron='#70615b',hat_color='#654f5a'))

def river(x):
    return 82 + 12*math.sin((x-20)/29)

def build():
    rng=random.Random(20261021)
    objects=[]
    # An actual unwalkable molten channel crossed by the road's broad causeway.
    # Overlapping discs form winding banks with coves and varying width. Art
    # samples this same union, so there are no square caps or invisible walls.
    for step in range(189):
        x=5+step*.8
        y=river(x)+1.15*math.sin(x/7.3)+.45*math.sin(x/3.7)
        radius=3.9+.85*math.sin(x/8.1)+.45*math.cos(x/3.9)
        radius=min(radius,fen.dist_to_trail(ROAD,x,y)-2.7,
            .6+(x-5)*.55,.6+(155.4-x)*.55)
        if radius<.45: continue
        objects.append(obj('ew_lava',round(x,3),round(y,3),round(radius,3)))
    objects += [obj('ew_door',133,20,width=10,depth=3),
        obj('meetingstone',125,27),obj('ew_tablet',133,22.8),obj('ew_echo',137,27.5),
        obj('ew_shackle',60,114),obj('ew_shackle',111,79),
        obj('ew_vent',18,83),obj('ew_vent',135,99),obj('ew_vent',101,31)]
    spawns=[dict(kind='ew_chainmaw',x=112,y=118),dict(kind='ew_bellows',x=43,y=45),
        dict(kind='ew_crown',x=128,y=65)]
    for kind,cx,cy in [('ashback',36,124),('glasswing',55,109),('slagjaw',89,67),('cinderhorn',117,42)]:
        for dx,dy in [(-11,-1),(10,8),(-8,-11),(12,-10),(20,2),(0,-18)]:
            x,y=cx+dx,cy+dy
            if abs(y-river(x))<9: y+=18
            if fen.dist_to_trail(ROAD,x,y)<5: x-=7
            if any(math.hypot(x-s['x'],y-s['y'])<5 for s in spawns):continue
            spawns.append(dict(kind='ew_'+kind,x=x,y=y))
    folk=[npc('guide','Svala Ashroad','Caldera pathfinder',27,137,
        'The flagstones in Asterion are warm because the first forge never went out. Follow the old chain road to the sealed door. Leave the glowing river to the stones.'),
        npc('keeper','Hedda Linkkeeper','Keeper of the first shackle',32,132,
        'Chainmaw carries a broken link from the first chain. Bring companions and end its watch.' ,True),
        npc('smith','Orri Hearthmender','Keeper of the bellows',118,38,
        'Yrsa feeds air into the mountain. Silence the living bellows before the last chain cracks.',True),
        npc('stone','The Emberwake Meeting Stone','Gather a party · hire fighters',127,29,
        'Gather here before the Nine-Chain Door. The raid is sealed. This stone calls the usual outdoor company; the raid will allow ten fighters in total.',True),
        npc('seal','The Nine-Chain Door','Sealed entrance',133,24,
        'Nine Wardens hold nine chains. Beyond them waits Eldmarr, the Ember-Lord. The door is sealed.'),
        npc('echo','The Voice Below','Eldmarr speaks through the stone',137,29,
        'I warmed the roots when your gods had no hall. They built their table on my fire and left no seat for me. Tell them I am coming.')]
    folk[3]['art']='stone';folk[3]['look']={}
    folk[4]['art']='scenery';folk[5]['art']='scenery'
    keep=folk+[dict(x=ARRIVAL[0],y=ARRIVAL[1]),dict(x=14,y=140)]
    spawns=[s for s in spawns if all(math.hypot(s['x']-n['x'],s['y']-n['y'])>10 for n in keep)]
    for _ in range(150):
        x,y=rng.uniform(7,153),rng.uniform(7,153)
        if abs(y-river(x))<10 or fen.dist_to_trail(ROAD,x,y)<5:continue
        if any(math.hypot(x-s['x'],y-s['y'])<4 for s in spawns+keep):continue
        if any(math.hypot(x-o['x'],y-o['y'])<3 for o in objects):continue
        objects.append(obj('ew_basalt',round(x,2),round(y,2),.85))
    for x,y in ROAD[1:-1]: objects.append(obj('ew_lantern',x+3,y+3))
    q=[]
    def quest(id,title,giver,desc,objectives,level,requires=None,**kw):
        levels=json.loads((ROOT/'world/levels.txt').read_text())
        q.append(dict(id='ew_'+id,title=title,npc='ew_'+giver,description=desc,objectives=objectives,
            level=level,rewardXp=(levels[level-1] if level<=len(levels) else levels[-1]+(level-len(levels))*2300)//10,rewardGold=22000 if level<99 else 35000,
            requires='ew_'+requires if requires else None,repeatable=False,**kw))
    def kill(kind,n,label):return dict(kind='kill',target='ew_'+kind,count=n,label=label)
    quest('warm','Warm Stones, Old Lies','guide','Find the old chain road and speak to Hedda Linkkeeper.',
        [dict(kind='talk',target='ew_keeper',count=1,label='Speak to Hedda Linkkeeper')],95)
    quest('road','Keep the Chain Road','guide','Drive the ashbacks and glasswings from the road. The mountain is waking.',
        [kill('ashback',3,'Defeat Ashback Salamanders'),kill('glasswing',3,'Defeat Obsidian Glasswings')],96,'warm')
    quest('link','The First Broken Link','keeper','Gather companions and defeat Chainmaw at the eastern shackle.',
        [kill('chainmaw',1,'Defeat Chainmaw')],97,group=True,recommendedPlayers=3)
    quest('breath','Breath Under the Mountain','smith','Gather companions and silence Yrsa, the Living Bellows, in the western basin.',
        [kill('bellows',1,'Defeat Yrsa, the Living Bellows')],99,group=True,recommendedPlayers=5)
    quest('voice','A Seat at the Table','guide','Follow the old chain road to the Nine-Chain Door. Hear the voice below and bring its words to Svala.',
        [dict(kind='talk',target='ew_echo',count=1,label='Hear the voice of Eldmarr')],99,'road')
    return dict(name=NAME,theme=THEME,tagline='Nine chains hold a fire that remembers.',size=SIZE,
        levels=[95,99],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),interior=False,
        objects=objects,slimes=spawns,npcs=folk,quests=q,city=None,paths=[ROAD],
        places=[dict(id='ew_road',name='The Old Chain Road',x=47,y=104,r=5),
            dict(id='ew_causeway',name='The Basalt Causeway',x=81,y=82,r=5),
            dict(id='ew_door',name='The Nine-Chain Door',x=133,y=26,r=4)],
        portals=[dict(id='ew_return',name='Asterion',x=14,y=140,r=1.3,to=PARENT,tx=LANDING[0],ty=LANDING[1],look=THEME)])

def install_parent(w):
    if not any(z['name']==NAME for z in w['zones']):return
    z=w['zones'][PARENT-1]
    road=[[90,42],[90,25],[90,18]]
    z['paths']=[p for p in z['paths'] if p!=road]+[road]
    # This north radial spoke is reserved for the gate. Remove intersecting
    # buildings as well as their collision, then prove the whole city still joins.
    z['objects']=[o for o in z['objects'] if not(fen.dist_to_trail(road,o['x'],o['y'])<5+max(o.get('r',0),o.get('width',0)/2))]
    z['portals']=[p for p in z['portals'] if p['id']!='asterion_emberwake']+[
        dict(id='asterion_emberwake',name=NAME,x=GATE[0],y=GATE[1],r=1.3,to=ZONE,tx=ARRIVAL[0],ty=ARRIVAL[1],look=THEME)]
    z['npcs']=[n for n in z['npcs'] if n['id']!='ew_citysmith']+[
        npc('citysmith','Runa Coalhand','Smith of the sleeping forge',95,27,
            'The flagstones are warm and the well has cracked. The old forge is only sleeping. Nine chains hold Eldmarr beneath this mountain.')]
    z['objects']=[o for o in z['objects'] if o['kind'] not in ('ew_well','ew_warmstone')]+[
        obj('ew_well',96,34),obj('ew_warmstone',91,31),obj('ew_warmstone',88,29)]

def check(w):
    lava=[o for o in w['zones'][ZONE-1]['objects'] if o['kind']=='ew_lava']
    assert lava and all(o['r']>0 and 'width' not in o and 'depth' not in o for o in lava)
    for index,start in [(ZONE,ARRIVAL),(PARENT,(90,162))]:
        z=w['zones'][index-1];seen,_=fen.flood(z,start)
        for p in z['portals']+z['npcs']+z['slimes']:
            assert seen[int(p['y']/.5),int(p['x']/.5)],(index,p.get('id',p.get('kind')),p['x'],p['y'])
    for index,pid in [(ZONE,'ew_return'),(PARENT,'asterion_emberwake')]:
        p=next(p for p in w['zones'][index-1]['portals'] if p['id']==pid)
        z=w['zones'][p['to']-1]
        assert all(math.hypot(s['x']-p['tx'],s['y']-p['ty'])>8 for s in z['slimes'])
        assert all(math.hypot(q['x']-p['tx'],q['y']-p['ty'])>q['r']+1 for q in z['portals'])
    print('Emberwake: both gates, all NPCs and spawns reachable; safe arrivals; raid door sealed')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');a=parser.parse_args()
    path=ROOT/'world/map.txt';w=json.loads(path.read_text())
    if not a.check:
        if len(w['zones'])==ZONE-1:w['zones'].append(build())
        else:
            assert w['zones'][ZONE-1]['name']==NAME
            w['zones'][ZONE-1]=build()
        install_parent(w)
    check(w)
    if a.check:return
    path.write_text(json.dumps(w,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'world/emberwake.txt').write_text(json.dumps(ENEMIES,indent=2,ensure_ascii=False)+'\n')
    path=ROOT/'world/items.txt';items=json.loads(path.read_text());have={i['id'] for i in items}
    for e in ENEMIES:
        if e['material'] not in have:items.append(dict(id=e['material'],name=e['name']+' Relic',kind='material',rarity='common',sell=10000 if e['elite'] else 2500))
    path.write_text(json.dumps(items,indent=2,ensure_ascii=False)+'\n')

if __name__=='__main__':main()
