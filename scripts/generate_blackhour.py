#!/usr/bin/env python3
"""Append a physical broken clock/foundry. Seed-free, byte-stable, sealed until --open."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import generate_gloamfen as fen
import generate_undervault as vault
from blackhour_content import ENEMIES
from mercenary_offers import offers
from skaldholm_content import look

ROOT=Path(__file__).resolve().parents[1]
NAME,THEME,ZONE,PARENT,SIZE='The Black Hour Foundry','blackhour',44,28,160
GATE,LANDING,ARRIVAL=(208,200),(214,200),(80,143)
# The door stays shut until this quest is done: one shard from each seasonal dungeon's final boss (server/src/world/hour_shards.rs).
KEY_QUEST='null_keys'
SHARDS=[('hour_shard_bloom','Shard of the Bloomed Hour','The Blooming Labyrinth','Bloom Heart'),
        ('hour_shard_solar','Shard of the Solar Hour','The Solar Crucible','Solar Heart'),
        ('hour_shard_amber','Shard of the Amber Hour','The Amber Archive','Amber Memory'),
        ('hour_shard_silent','Shard of the Silent Hour','The Silent Solstice','Solstice Heart')]
PACKS=[(55,125),(35,98),(125,98),(105,125)]
ROOMS=[[63,133,97,153],[15,65,55,107],[105,65,145,107],[55,7,105,47]]

def obj(kind,x,y,**kw):
    return dict(kind=kind,x=round(x,2),y=round(y,2),r=0,v=kw.pop('v',0),**kw)

def floor_mask():
    yy,xx=np.mgrid[:SIZE,:SIZE];x,y=xx+.5,yy+.5
    radius=np.hypot(x-80,y-83)
    floor=(radius>=43)&(radius<=64)&(y>=62)
    # Two side flywheels and a genuinely circular final clock, not room rectangles.
    for cx,cy,r in [(35,86,23),(125,86,23),(80,27,24)]:
        floor|=np.hypot(x-cx,y-cy)<r
    floor|=(abs(x-80)<7)&(y>38)&(y<74)
    floor|=(abs(y-64)<6)&(x>35)&(x<125)
    floor|=(abs(x-80)<17)&(y>=132)&(y<153)
    # Open central sump: the two curving branches must be walked.
    floor&=~((np.hypot(x-80,y-85)<39)&(y>69)&(y<125))
    # Notched teeth, at the outside only, reinforce the clock outline.
    for k in range(12):
        a=math.tau*k/12;cx,cy=80+64*math.cos(a),83+64*math.sin(a)
        if cy>62:floor|=(abs(x-cx)<3)&(abs(y-cy)<3)
    return floor

def build():
    floor=floor_mask();vault.SIZE=SIZE;walls,_=vault.wall_pieces(floor)
    objects=[obj('null_wall',x,y,width=w,depth=d) for x,y,w,d in walls]
    used=floor.copy()
    for y in range(SIZE):
        for x in range(SIZE):
            if used[y,x]:continue
            x1=x
            while x1<min(x+8,SIZE) and not used[y,x1]:x1+=1
            y1=y+1
            while y1<min(y+8,SIZE) and not used[y1:y1+1,x:x1].any():y1+=1
            used[y:y1,x:x1]=True
            objects.append(obj('void',(x+x1)/2,(y+y1)/2,width=x1-x,depth=y1-y))
    objects += [obj('null_sump',80,100),obj('null_clock',80,9),obj('null_bellframe',35,65),
                obj('null_turbine',125,65),obj('null_gateway',80,151)]
    for i,(x,y) in enumerate([(68,137),(92,137),(68,148),(92,148)]):
        objects.append(obj('null_seal',x,y,v=i))
    for cx,cy in [(35,86),(125,86),(80,27)]:
        for side in (-1,1):objects.append(obj('null_furnace',cx+side*16,cy+8))
    for x,y in [(68,140),(92,140),(48,117),(112,117),(23,98),(137,98),(72,58),(88,58)]:
        objects.append(obj('null_lamp',x,y))
    spawns=[]
    for cx,cy in PACKS:
        for kind,dx,dy in [('null_hauler',-3,1),('null_breaker',3,1),('null_coil',0,-3)]:
            spawns.append(dict(kind=kind,x=cx+dx,y=cy+dy))
    spawns += [dict(kind='null_bell',x=35,y=77),dict(kind='null_conductor',x=125,y=77),dict(kind='null_hour',x=80,y=27)]
    return dict(name=NAME,theme=THEME,tagline='The hour between seasons burns here.',size=SIZE,
        levels=[99,99],min_level=99,players=5,copies=4,interior=True,sealedTemplate=True,
        final_boss='null_hour',spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),objects=objects,slimes=spawns,
        blackhourFloor=[''.join('=' if v else ' ' for v in row) for row in floor],
        rooms=ROOMS,paths=[[[80,143],[59,123],[35,100],[35,77],[44,66],[80,63],[80,27]],
                          [[80,143],[101,123],[125,100],[125,77],[116,66],[80,63]]],
        places=[dict(id='null_entry',name='The Broken Clock Rim',x=80,y=143,r=5),
                dict(id='null_west',name='The Twelve-Ton Bell',x=35,y=77,r=5),
                dict(id='null_east',name='The Dead Current',x=125,y=77,r=5),
                dict(id='null_crown',name='The Thirteenth Hour',x=80,y=27,r=5)],
        npcs=[dict(id='null_witness',name='Eydis, the Missing Minute',role='Last foundry worker',
            x=87,y=144,color='#b694e8',offers=[],look=look('#c8a6ab','#77678e','short','hood',hat_color='#41304e'),
            dialogue='The Yearwheel lost an hour. We built a furnace to find it, and something answered. Vark rings its shift bell; Iona feeds it dead current. Read the warning before the final clock. Blue equipment and five prepared fighters are the minimum.')],quests=[],city=None,
        portals=[dict(id='null_return',name='The Yearwheel',x=72,y=143,r=1.2,to=PARENT,tx=LANDING[0],ty=LANDING[1],look=THEME),
                 dict(id='null_clear',name='The Hour Restored',x=80,y=13,r=1.2,to=PARENT,tx=LANDING[0],ty=LANDING[1],look=THEME,after_clear=True)])

def install_parent(world):
    if not any(z['name']==NAME for z in world['zones']):return
    z=world['zones'][PARENT-1];assert z['name']=='The Yearwheel'
    line=[[200,200],list(GATE),list(LANDING)]
    z['paths']=[p for p in z['paths'] if p!=line]+[line]
    # Only loose scenery in the already open Equinox Crossing; preserve its axle.
    z['objects']=[o for o in z['objects'] if not(o['kind']!='year_axle' and
        (fen.dist_to_trail(line,o['x'],o['y'])<3+o.get('r',0) or math.hypot(o['x']-212,o['y']-205)<6+o.get('r',0)))]
    z['portals']=[p for p in z['portals'] if p['id']!='year_blackhour']+[
        dict(id='year_blackhour',name=NAME,x=GATE[0],y=GATE[1],r=1.3,to=ZONE,tx=ARRIVAL[0],ty=ARRIVAL[1],look=THEME,needs_quest=KEY_QUEST)]
    z['npcs']=[n for n in z['npcs'] if not n['id'].startswith('null_')]+[
        dict(id='null_guide',name='Sigrun Ashminute',role='Keeper of the missing hour',x=212,y=205,color='#b58be9',offers=offers(open_=True),
             dialogue='Below the Equinox axle lies the Black Hour Foundry. Five fighters in full blue equipment can survive its long shifts. Green equipment will not carry a party through. Silence Vark and return the missing minute.',look=look('#d4af9d','#77638a','braid','hood',hat_color='#45334f')),
        dict(id='null_rigger',name='Torv Coilbreaker',role='Former current master',x=218,y=205,color='#6ed7d6',offers=[],
             dialogue='Iona turned the four seasons into one dead current. Break her circuit with your party. Beyond her, the Thirteenth Hour still turns. Its warnings are written before the clock hall.',look=look('#be9d96','#79b8b5','short',None,None,'#293f4a'))]
    levels=json.loads((ROOT/'world/levels.txt').read_text())
    xp=(levels[98] if len(levels)>98 else levels[-1]+(99-len(levels))*2300)//10
    quests=[dict(id=KEY_QUEST,title='Four Hours Returned',npc='null_guide',description='Sigrun Ashminute can open the way to the Black Hour Foundry only when the four seasons give back the hours they keep. Bring her a shard from the last guardian of each: Bloom Heart in the Blooming Labyrinth, Solar Heart in the Solar Crucible, Amber Memory in the Amber Archive and Solstice Heart in the Silent Solstice. The shards fall only for heroes who have taken this quest.',
            objectives=[dict(kind='bring',target=i,count=1,label='Bring the '+n) for i,n,_,_ in SHARDS],rewardGold=30000,minLevel=99),
        dict(id='null_entry',title='The Missing Minute',npc='null_guide',description='Enter the Black Hour Foundry and speak to Eydis, the Missing Minute.',objectives=[dict(kind='talk',target='null_witness',count=1,label='Speak to Eydis')],rewardGold=24000,requires=KEY_QUEST),
        dict(id='null_bell',title='End the Endless Shift',npc='null_guide',description='Defeat Vark, the Twelve-Ton Bell, with your party.',objectives=[dict(kind='kill',target='null_bell',count=1,label='Defeat Vark')],group=True,recommendedPlayers=5,rewardGold=65000,rewardItem='null_pants',rewardCount=1),
        dict(id='null_current',title='Break the Dead Current',npc='null_rigger',description='Defeat Iona, Mistress of the Dead Current, with your party.',objectives=[dict(kind='kill',target='null_conductor',count=1,label='Defeat Iona')],group=True,recommendedPlayers=5,rewardGold=65000,rewardItem='null_accessory',rewardCount=1)]
    for q in quests:q.update(level=99,rewardXp=xp,repeatable=False);q.setdefault('requires',None)
    z['quests']=[q for q in z['quests'] if not q['id'].startswith('null_')]+quests

def check(w):
    for index,start in [(ZONE,ARRIVAL),(PARENT,(24,359))]:
        z=w['zones'][index-1];seen,_=fen.flood(z,start)
        for p in z['portals']+z['npcs']+z['slimes']:
            assert seen[int(p['y']/.5),int(p['x']/.5)],(index,p.get('id',p.get('kind')),p['x'],p['y'])
    for z in (w['zones'][PARENT-1],w['zones'][ZONE-1]):
        for p in z['portals']:
            if p['id'] not in ('year_blackhour','null_return','null_clear'):continue
            dst=w['zones'][p['to']-1]
            assert all(math.hypot(s['x']-p['tx'],s['y']-p['ty'])>8 for s in dst['slimes']),p
            assert all(math.hypot(q['x']-p['tx'],q['y']-p['ty'])>q['r']+1 for q in dst['portals']),p

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--open',action='store_true');a=p.parse_args()
    path=ROOT/'world/map.txt';w=json.loads(path.read_text())
    if not a.check:
        old=next((i for i,z in enumerate(w['zones'],1) if z['name']==NAME),None);assert old in (None,ZONE)
        z=build();z['sealedTemplate']=not a.open
        if old is None:assert len(w['zones'])==ZONE-1;w['zones'].append(z)
        else:w['zones'][ZONE-1]=z
        install_parent(w)
    check(w)
    if not a.check:
        path.write_text(json.dumps(w,indent=2,ensure_ascii=False)+'\n')
        (ROOT/'world/blackhour.txt').write_text(json.dumps(ENEMIES,indent=2,ensure_ascii=False)+'\n')
        path=ROOT/'world/items.txt';items=json.loads(path.read_text());have={i['id'] for i in items}
        for e in ENEMIES:
            if e['material'] not in have:items.append(dict(id=e['material'],name=e['name']+' Relic',kind='material',rarity='common',sell=14000 if e['boss'] else 3200))
        for i,n,_,_ in SHARDS:
            if i not in have:items.append(dict(id=i,name=n,kind='material',rarity='common',sell=0))
        path.write_text(json.dumps(items,indent=2,ensure_ascii=False)+'\n')
    print('Black Hour Foundry: clock rim, flywheels and suspended clock; all targets reachable')
if __name__=='__main__':main()
