#!/usr/bin/env python3
"""Build the level 50–55 Obsidian Orrery beyond the Prismwaste, reproducibly."""
import json
import math
import random
from pathlib import Path

import generate_gloamfen as fen
import spark_travel
from quest_gear_rewards import add_reward

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
ZONE = 15
NAME = 'The Obsidian Orrery'
ARRIVAL = (16, 112)
RETURN = (9, 112)
PRISM_GATE = (117, 49)
PRISM_ARRIVAL = (107, 49)


def obj(kind, x, y, r, v=0, **extra):
    return dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r, v=v, **extra)


def npc(id_, name, role, x, y, dialogue, offers=None, buys=False):
    return dict(id='orrery_' + id_, name=name, role=role, x=x, y=y,
                color='#efc879', dialogue=dialogue, offers=offers or [], buys=buys,
                look=dict(hair='#ddbd92', skin='#c99770', style='short'))


def quest(id_, title, giver, description, objectives, level, gold, requires=None,
          repeatable=False, **extra):
    return add_reward(dict(id='orrery_' + id_, title=title, npc='orrery_' + giver,
                           description=description, objectives=objectives, level=level,
                           rewardXp=LEVELS[level - 1] // 10, rewardGold=gold,
                           requires='orrery_' + requires if requires else None,
                           repeatable=repeatable, **extra))


def kill(kind, count, label):
    return dict(kind='kill', target=kind, count=count, label=label)


def bring(item, count, label):
    return dict(kind='bring', target=item, count=count, label=label)


def talk(person, label):
    return dict(kind='talk', target='orrery_' + person, count=1, label=label)


def content():
    import mercenary_offers as mo
    people = [
        npc('keeper', 'Ilyra Cogsong', 'Keeper of the Stillpoint', 27, 106,
            'The great machine has no master now. Meet our crew before its gears begin to turn.'),
        npc('healer', 'Neris Brasshand', 'Healer', 32, 116,
            'The Stillpoint is the only place where the hour does not bite.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_health_potion', label='Buy Health Potion', cost=30, item='health_potion', tiered=True)]),
        npc('scout', 'Rook Vesper', 'Gear trail scout', 38, 106,
            'Bronze mantises and loose gearlings have crossed the southern ring. We need their numbers cut.', mo.offers()),
        npc('scholar', 'Edda Pendulum', 'Chronicle scholar', 38, 116,
            'The Matron winds the western clock. Beyond her, the Epoch Engine keeps an hour that should have ended.', mo.offers()),
        npc('trader', 'Oren Flint', 'Provisioner and material buyer', 28, 121,
            'Bring me the machine fragments you recover. I can pay and provision the next excursion.',
            [dict(id='buy_traveler_stew', label="Buy Traveler's Stew", cost=12, item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel', cost=500, bag='linen_satchel')], True),
    ]
    quests = [
        quest('welcome', 'The Stillpoint', 'keeper', 'Meet the people keeping time in the refuge.',
              [talk('healer','Speak with Neris'),talk('scout','Speak with Rook'),talk('scholar','Speak with Edda')],50,1200),
        quest('mantises', 'Bronze in the Grass', 'scout', 'Drive the cutting mantises from the lower ring.',
              [kill('bronzemantis',6,'Defeat Bronze Mantises')],50,1500,'welcome'),
        quest('gearlings', 'Teeth of the Machine', 'keeper', 'Clear the skittering gears from the main ascent.',
              [kill('gearling',6,'Defeat Gearlings')],51,1650,'mantises'),
        quest('teeth', 'A Broken Sequence', 'scholar', 'Collect teeth from the escaped gearlings so Edda can stop the clock.',
              [bring('gearling_tooth',5,'Bring Gearling Teeth')],51,1700,'gearlings'),
        quest('seers', 'The Future They Saw', 'scout', 'Silence the seers that fire from the upper ring.',
              [kill('orbitseer',6,'Defeat Orbit Seers')],52,1800,'gearlings'),
        quest('guards', 'Last Watch', 'scholar', 'The chronoguards still defend the core. Break their formation.',
              [kill('chronoguard',5,'Defeat Chronoguards')],53,2000,'seers'),
        quest('matron', 'The Pendulum Matron', 'scout', 'The western winding court belongs to the Matron. Bring allies.',
              [kill('pendulummatron',1,'Defeat the Pendulum Matron')],54,3100,'guards',group=True,recommendedPlayers=3),
        quest('engine', 'The Stolen Hour', 'scholar', 'Shut down the Epoch Engine at the northern crown. Bring a full group.',
              [kill('epochengine',1,'Defeat the Epoch Engine')],55,4600,'guards',group=True,recommendedPlayers=5),
        quest('survey', 'One Unbroken Hour', 'keeper', 'Make the ascent safe from the lower ring to the crown.',
              [kill('bronzemantis',3,'Defeat Bronze Mantises'),kill('gearling',3,'Defeat Gearlings'),
               kill('orbitseer',3,'Defeat Orbit Seers'),kill('chronoguard',3,'Defeat Chronoguards')],55,2800,'guards'),
        quest('patrol', 'Keep the Stillpoint', 'keeper', 'Clear the machinery wandering nearest the refuge.',
              [kill('bronzemantis',4,'Defeat Bronze Mantises'),kill('gearling',4,'Defeat Gearlings')],50,1200,'welcome',True),
    ]
    return people, quests


def dist_to_path(x, y, paths):
    best = 999.
    for path in paths:
        for (ax,ay),(bx,by) in zip(path,path[1:]):
            dx,dy=bx-ax,by-ay
            t=max(0.,min(1.,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            best=min(best,math.hypot(x-ax-dx*t,y-ay-dy*t))
    return best


def build():
    rng=random.Random(20261008)
    paths=[[(16,112),(30,109),(48,98),(65,85),(55,67),(78,51),(65,31),(64,16)],
           [(48,98),(90,87),(78,51)],[(55,67),(22,49),(36,31),(64,16)]]
    objects=[]
    # Concentric broken clock rings: each gap meets a marked path.
    for cx,cy,radius,gap in [(64,76,20,230),(64,54,30,150),(64,37,43,295)]:
        for a in range(0,360,10):
            if abs((a-gap+180)%360-180)<20:
                continue
            x=cx+radius*math.cos(math.radians(a));y=cy+radius*math.sin(math.radians(a))
            if not 5<x<123 or not 5<y<123 or dist_to_path(x,y,paths)<3.8:
                continue
            objects.append(obj('clockwall',x,y,1.05,a//10%4))
    objects += [obj('stillpoint',25,111,1.7,width=4,depth=3),
                obj('hourpillar',19,105,.7),obj('hourpillar',45,109,.7),
                obj('epoch_crown',64,9,1.6)]
    for kind,count,radius in [('blackspire',105,.72),('cogstone',95,.48),('timegrass',100,.22)]:
        placed=0
        for _ in range(40000):
            if placed==count: break
            x,y=rng.uniform(6,122),rng.uniform(6,122)
            if (6<x<49 and y>102) or dist_to_path(x,y,paths)<3.2: continue
            if any(math.hypot(x-o['x'],y-o['y'])<radius+o['r']+1.2 for o in objects): continue
            objects.append(obj(kind,x,y,radius,rng.randrange(4)));placed+=1
        assert placed==count,(kind,placed)
    spawns=[dict(kind='pendulummatron',x=24,y=34),dict(kind='epochengine',x=64,y=21)]
    for kind,count,lo,hi in [('bronzemantis',11,88,102),('gearling',10,70,86),
                             ('orbitseer',10,47,65),('chronoguard',9,25,43)]:
        for _ in range(count):
            for _attempt in range(4000):
                x,y=rng.uniform(10,118),rng.uniform(lo,hi)
                if (6<x<49 and y>102) or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<12: continue
                if any(math.hypot(x-s['x'],y-s['y'])<(15 if s['kind'] in ('pendulummatron','epochengine') else 6) for s in spawns): continue
                if any(math.hypot(x-o['x'],y-o['y'])<o['r']+1.2 for o in objects): continue
                spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)));break
            else: raise RuntimeError(f'cannot place {kind}')
    people,quests=content()
    zone=dict(name=NAME,theme='orrery',tagline='The great clock is keeping a stolen hour',size=128,levels=[50,55],
              spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),
              paths=[[[x,y] for x,y in path] for path in paths],objects=objects,slimes=spawns,
              npcs=people,places=[],quests=quests,
              city=dict(name='The Stillpoint',x0=11,x1=48,y0=103,y1=125,
                        plaza=dict(x=29,y=112),radius=5,entry=dict(x=16,y=112)),
              portals=[dict(id='orrery_prism_gate',name='The Hourglass Pass',x=RETURN[0],y=RETURN[1],r=1.2,
                            to=14,tx=PRISM_ARRIVAL[0],ty=PRISM_ARRIVAL[1],look='orrery')])
    check(zone)
    return zone


def check(zone):
    seen,_=fen.flood(zone,ARRIVAL)
    for x,y,label in [(RETURN[0],RETURN[1],'return gate'),(24,34,'Matron'),(64,21,'Engine')]:
        assert seen[int(y/.5),int(x/.5)],f'{label} unreachable'
    for entry in zone['slimes']+zone['npcs']:
        assert seen[int(entry['y']/.5),int(entry['x']/.5)],f'{entry} unreachable'
    for s in zone['slimes']:
        assert math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>8
    assert len(zone['objects'])>=300 and len(zone['slimes'])==42


def open_prism_gate(prism):
    prism['objects']=[o for o in prism['objects'] if math.hypot(o['x']-PRISM_GATE[0],o['y']-PRISM_GATE[1])>o['r']+3
                      and not (46<=o['y']<=52 and o['x']>104)]
    # Preserve its slot and therefore every older global enemy ID.
    for spawn in prism['slimes']:
        if math.hypot(spawn['x']-PRISM_ARRIVAL[0],spawn['y']-PRISM_ARRIVAL[1]) <= 9:
            assert spawn['kind']=='glassharrier'
            spawn.update(x=113,y=70)
    if len(prism['slimes']) == 41:
        prism['slimes'].append(dict(kind='glassharrier',x=113,y=70))
    assert len(prism['slimes']) == 42
    prism['portals']=[p for p in prism['portals'] if p['id']!='prism_orrery_gate']
    prism['portals'].append(dict(id='prism_orrery_gate',name='The Hourglass Pass',x=PRISM_GATE[0],y=PRISM_GATE[1],r=1.2,
                                 to=ZONE,tx=ARRIVAL[0],ty=ARRIVAL[1],look='orrery'))


def main():
    world=json.loads(MAP.read_text())
    later=world['zones'][ZONE:]
    world['zones']=world['zones'][:ZONE-1]
    assert len(world['zones'])==ZONE-1
    open_prism_gate(world['zones'][13])
    world['zones'].append(build())
    world['zones'].extend(later)
    if any(z.get('name')=='The Moonspore Canopy' for z in later):
        from generate_moonspore import open_orrery_gate
        open_orrery_gate(world['zones'][ZONE-1])
    spark_travel.ensure(world)
    MAP.write_text(json.dumps(world,indent=2)+'\n')
    z=world['zones'][ZONE-1]
    print(f'{NAME}: {len(z["objects"])} objects, {len(z["slimes"])} enemies, {len(z["quests"])} quests')


if __name__=='__main__': main()
