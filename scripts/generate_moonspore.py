#!/usr/bin/env python3
"""Rebuild the level 55–60 Moonspore Canopy and the Orrery's eastern gate."""
import json
import math
import random
from pathlib import Path

import generate_gloamfen as fen
import spark_travel
from quest_gear_rewards import add_reward

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
XP = json.loads((ROOT / 'world/levels.txt').read_text())
ZONE = 16
NAME = 'The Moonspore Canopy'
ARRIVAL = (16, 112)
RETURN = (9, 112)
ORRERY_GATE = (117, 112)
ORRERY_ARRIVAL = (107, 112)


def obj(kind, x, y, r, v=0, **extra):
    return dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r, v=v, **extra)


def npc(id_, name, role, x, y, dialogue, offers=None, buys=False):
    return dict(id='moonspore_' + id_, name=name, role=role, x=x, y=y,
                color='#a5e5ca', dialogue=dialogue, offers=offers or [], buys=buys,
                look=dict(hair='#bdeed5', skin='#d5b59e', style='long'))


def kill(kind, count, label):
    return dict(kind='kill', target=kind, count=count, label=label)


def bring(item, count, label):
    return dict(kind='bring', target=item, count=count, label=label)


def talk(person, label):
    return dict(kind='talk', target='moonspore_' + person, count=1, label=label)


def quest(id_, title, giver, description, objectives, level, gold, requires=None,
          repeatable=False, **extra):
    return add_reward(dict(id='moonspore_' + id_, title=title, npc='moonspore_' + giver,
                           description=description, objectives=objectives, level=level,
                           rewardXp=XP[level - 1] // 10, rewardGold=gold,
                           requires='moonspore_' + requires if requires else None,
                           repeatable=repeatable, **extra))


def content():
    import mercenary_offers as mo
    people = [
        npc('warden', 'Eira Lanternkeeper', 'Refuge warden', 27, 106,
            'The canopy glows because the old moon fell here. Meet our watchers, then help us keep its spores from swallowing the trails.'),
        npc('healer', 'Solvi Dewmender', 'Healer', 32, 116,
            'Come into the lamplight. Nothing that roots in shadow follows you here.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_health_potion', label='Buy Health Potion', cost=30, item='health_potion', tiered=True)]),
        npc('ranger', 'Tamsin Threadmark', 'Canopy ranger', 38, 106,
            'Silkwings veil the paths. The Widow waits among their threads in the eastern court.', mo.offers()),
        npc('scholar', 'Odo Sporeglass', 'Spore scholar', 38, 116,
            'The Mireheart feeds the western roots. Beyond both courts the Nightbloom has begun to wake.', mo.offers()),
        npc('trader', 'Pell Mosscoin', 'Provisioner and material buyer', 28, 121,
            'I buy everything the canopy sheds. A warm stew buys you a little more time beneath it.',
            [dict(id='buy_traveler_stew', label="Buy Traveler's Stew", cost=12, item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel', cost=500, bag='linen_satchel')], True),
        npc('seer', 'Ysra Palefern', 'Moonfall seer', 43, 112,
            'Each ring of the forest remembers a different moon. Listen for the one that has gone silent.'),
    ]
    quests = [
        quest('welcome', 'Lamps Beneath the Canopy', 'warden', 'Meet the wardens of Lamplight Refuge.',
              [talk('healer', 'Speak with Solvi'), talk('ranger', 'Speak with Tamsin'), talk('scholar', 'Speak with Odo')], 55, 1400),
        quest('grazers', 'Grazing on Moonlight', 'ranger', 'Drive the Glowcap Grazers away from the refuge lamps.',
              [kill('glowcapgrazer', 6, 'Defeat Glowcap Grazers')], 55, 1700, 'welcome'),
        quest('silkwings', 'Threads Across the Trail', 'ranger', 'Clear the moonlit threads woven across the eastern path.',
              [kill('silkwing', 6, 'Defeat Silkwings')], 56, 1850, 'grazers'),
        quest('roots', 'What Grows Below', 'scholar', 'Cut back the Rootlurkers feeding beneath the western grove.',
              [kill('rootlurker', 6, 'Defeat Rootlurkers')], 57, 2100, 'grazers'),
        quest('wraiths', 'Lanterns in the Mist', 'seer', 'The false lanterns in the upper ring lead travelers astray.',
              [kill('lanternwraith', 5, 'Defeat Lantern Wraiths')], 58, 2350, 'roots'),
        quest('caps', 'A Cure in the Cap', 'healer', 'Bring intact glowcaps for Solvi’s antidote.',
              [bring('glowcap', 5, 'Bring Glowcaps')], 55, 1750, 'welcome'),
        quest('silk', 'Silver Thread', 'trader', 'Pell needs silk to repair the refuge lantern screens.',
              [bring('moon_silk', 5, 'Bring Moon Silk')], 56, 1900, 'silkwings'),
        quest('mireheart', 'Heart of the Sinking Grove', 'scholar', 'The Mireheart poisons the western roots. Take two allies.',
              [kill('mireheart', 1, 'Defeat the Mireheart')], 58, 3600, 'roots', group=True, recommendedPlayers=3),
        quest('widow', 'The Silver Widow', 'ranger', 'The Widow has spun a second moon over the eastern court. Bring allies.',
              [kill('silverwidow', 1, 'Defeat the Silver Widow')], 59, 3900, 'silkwings', group=True, recommendedPlayers=3),
        quest('bloom', 'When the Moon Opens', 'seer', 'The Nightbloom has opened above the canopy. Gather a full group.',
              [kill('nightbloom', 1, 'Defeat the Nightbloom')], 60, 5700, 'wraiths', group=True, recommendedPlayers=5),
        quest('survey', 'Three Fallen Moons', 'warden', 'Make a complete circuit of the canopy and return with news.',
              [kill('glowcapgrazer', 3, 'Defeat Glowcap Grazers'), kill('silkwing', 3, 'Defeat Silkwings'),
               kill('rootlurker', 3, 'Defeat Rootlurkers'), kill('lanternwraith', 3, 'Defeat Lantern Wraiths')], 60, 3200, 'wraiths'),
        quest('patrol', 'Keep the Refuge Lit', 'warden', 'Thin the growth nearest our lamps each night.',
              [kill('glowcapgrazer', 4, 'Defeat Glowcap Grazers'), kill('silkwing', 4, 'Defeat Silkwings')], 55, 1500, 'welcome', True),
    ]
    return people, quests


def distance_to_path(x, y, paths):
    best = 999.
    for path in paths:
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            dx, dy = bx-ax, by-ay
            t = max(0., min(1., ((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            best = min(best, math.hypot(x-ax-dx*t, y-ay-dy*t))
    return best


def build():
    rng = random.Random(20261008)
    paths = [[(16,112),(32,107),(51,93),(63,76),(63,54),(64,17)],
             [(51,93),(29,72),(24,39),(24,32),(63,54)],
             [(51,93),(94,75),(101,40),(99,32),(63,54)]]
    objects = [obj('lamphouse',25,110,1.8,width=4,depth=3),
               obj('moonwell',36,111,.85),obj('moonaltar',64,8,1.4)]
    # Three open fungal rings. Missing arcs leave broad lanes to both elite courts.
    for cx,cy,radius,gap in [(63,80,19,235),(64,55,31,95),(64,34,42,270)]:
        for a in range(0,360,12):
            if abs((a-gap+180)%360-180)<24: continue
            x=cx+radius*math.cos(math.radians(a));y=cy+radius*math.sin(math.radians(a))
            if 5<x<123 and 5<y<123 and distance_to_path(x,y,paths)>4.2:
                objects.append(obj('mooncaps',x,y,1.05,a//12%4))
    for x,y in [(19,103),(46,106),(18,120),(43,120),(59,100),(37,80),(88,81),(27,52),(100,53)]:
        objects.append(obj('sporelamp',x,y,.35,rng.randrange(4)))
    for kind,count,radius in [('gloomstalk',110,.7),('moonstone',95,.46),
                              ('sporefern',105,.24),('glowmoss',70,.16)]:
        placed=0
        for _ in range(50000):
            if placed==count: break
            x,y=rng.uniform(6,122),rng.uniform(6,122)
            if (6<x<49 and y>102) or distance_to_path(x,y,paths)<3.3: continue
            if any(math.hypot(x-o['x'],y-o['y'])<radius+o['r']+1.25 for o in objects): continue
            objects.append(obj(kind,x,y,radius,rng.randrange(4)));placed+=1
        assert placed==count,(kind,placed)
    spawns=[dict(kind='mireheart',x=24,y=32),dict(kind='silverwidow',x=100,y=32),
            dict(kind='nightbloom',x=64,y=18)]
    for kind,count,lo,hi in [('glowcapgrazer',11,88,102),('silkwing',10,66,86),
                             ('rootlurker',10,45,66),('lanternwraith',9,25,45)]:
        for _ in range(count):
            for _attempt in range(5000):
                x,y=rng.uniform(10,118),rng.uniform(lo,hi)
                if (6<x<49 and y>102) or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<12: continue
                if any(math.hypot(x-s['x'],y-s['y'])<(14 if s['kind'] in ('mireheart','silverwidow','nightbloom') else 6) for s in spawns): continue
                if any(math.hypot(x-o['x'],y-o['y'])<o['r']+1.2 for o in objects): continue
                spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)));break
            else: raise RuntimeError(f'cannot place {kind}')
    people,quests=content()
    zone=dict(name=NAME,theme='moonspore',tagline='A fallen moon feeds a forest that glows after dark',size=128,
              levels=[55,60],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),
              paths=[[[x,y] for x,y in path] for path in paths],objects=objects,slimes=spawns,
              npcs=people,places=[],quests=quests,
              city=dict(name='Lamplight Refuge',x0=11,x1=48,y0=103,y1=125,
                        plaza=dict(x=29,y=112),radius=5,entry=dict(x=16,y=112)),
              portals=[dict(id='moonspore_orrery_gate',name='The Moonfall Arch',x=RETURN[0],y=RETURN[1],r=1.2,
                            to=15,tx=ORRERY_ARRIVAL[0],ty=ORRERY_ARRIVAL[1],look='moonspore')])
    check(zone)
    return zone


def check(zone):
    seen,_=fen.flood(zone,ARRIVAL)
    for entry in [dict(x=RETURN[0],y=RETURN[1]),*zone['slimes'],*zone['npcs']]:
        assert seen[int(entry['y']/.5),int(entry['x']/.5)],f'unreachable: {entry}'
    for s in zone['slimes']:
        assert math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>=8
    for q in zone['quests']:
        assert len('quest:accept:'+q['id'])<=32, f'{q["id"]} exceeds the interact offer limit'
    assert len(zone['slimes'])==43 and len(zone['quests'])==12 and len(zone['objects'])>=400


def open_orrery_gate(orrery):
    # Keep old spawn slots and IDs; clear a broad, unobstructed eastern approach.
    orrery['objects']=[o for o in orrery['objects']
                       if not (o['x']>101 and 106<=o['y']<=118)
                       and math.hypot(o['x']-ORRERY_GATE[0],o['y']-ORRERY_GATE[1])>o['r']+3]
    orrery['paths']=[p for p in orrery['paths'] if p!=[[45,109],[107,112],[117,112]]]
    orrery['paths'].append([[45,109],[107,112],[117,112]])
    orrery['portals']=[p for p in orrery['portals'] if p['id']!='orrery_moonspore_gate']
    orrery['portals'].append(dict(id='orrery_moonspore_gate',name='The Moonfall Arch',
                                  x=ORRERY_GATE[0],y=ORRERY_GATE[1],r=1.2,to=ZONE,
                                  tx=ARRIVAL[0],ty=ARRIVAL[1],look='moonspore'))
    seen,_=fen.flood(orrery, (orrery['spawn']['x'],orrery['spawn']['y']))
    assert seen[int(ORRERY_GATE[1]/.5),int(ORRERY_GATE[0]/.5)], 'Orrery approach is blocked'
    assert all(math.hypot(s['x']-ORRERY_ARRIVAL[0],s['y']-ORRERY_ARRIVAL[1])>=8 for s in orrery['slimes'])


def main():
    world=json.loads(MAP.read_text())
    later=world['zones'][ZONE:]
    world['zones']=world['zones'][:ZONE-1]
    assert len(world['zones'])==ZONE-1
    open_orrery_gate(world['zones'][ZONE-2])
    world['zones'].append(build())
    world['zones'].extend(later)
    if any(z.get('name')=='Asterion' for z in later):
        from generate_asterion import open_forest_gate
        open_forest_gate(world['zones'][ZONE-1])
    spark_travel.ensure(world)
    MAP.write_text(json.dumps(world,indent=2)+'\n')
    z=world['zones'][ZONE-1]
    print(f'{NAME}: {len(z["objects"])} objects, {len(z["slimes"])} enemies, {len(z["quests"])} quests')


if __name__=='__main__': main()
