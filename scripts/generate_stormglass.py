#!/usr/bin/env python3
"""Seeded, repeatable Stormglass Shore (zone 19, levels 60–65).

Run after generate_asterion.py. The Eye Below is only a sealed landmark:
there is deliberately no portal or instance map for it.
"""
import json
import math
import random
from pathlib import Path

import generate_gloamfen as fen
import mercenary_offers
import spark_travel
from quest_gear_rewards import add_reward

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
XP = json.loads((ROOT / 'world/levels.txt').read_text())
ZONE = 19
ARRIVAL = (13, 105)
RETURN = (7, 105)
CITY_GATE = (170, 88)
CITY_ARRIVAL = (160, 88)
NAME = 'The Stormglass Shore'


def obj(kind, x, y, r, **extra):
    return dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r, v=extra.pop('v', 0), **extra)


def npc(id_, name, role, x, y, dialogue, offers=None, buys=False):
    return dict(id='stormglass_' + id_, name=name, role=role, x=x, y=y,
                color='#a8dfe4', dialogue=dialogue, offers=offers or [], buys=buys,
                look=dict(skin='#ac806c', hair='#d7f4e8', style='long', hat='hood', hatColor='#31536b'))


def kill(kind, count, label):
    return dict(kind='kill', target=kind, count=count, label=label)


def talk(who, label):
    return dict(kind='talk', target='stormglass_' + who, count=1, label=label)


def visit(where, label):
    return dict(kind='visit', target='stormglass_' + where, count=1, label=label)


def bring(item, count, label):
    return dict(kind='bring', target=item, count=count, label=label)


def quest(id_, title, giver, description, objectives, level, gold, requires=None, repeatable=False, **extra):
    return add_reward(dict(id='stormglass_' + id_, title=title, npc='stormglass_' + giver,
                           description=description, objectives=objectives, level=level,
                           rewardXp=XP[level - 1] // 10, rewardGold=gold,
                           requires='stormglass_' + requires if requires else None,
                           repeatable=repeatable, **extra))


def people_and_quests():
    people = [
        npc('warden', 'Captain Thora Vale', 'Keeper of Breakwater Camp', 28, 101,
            'Asterion sent us to listen to the coast. The sea answers in thunder. Meet the crew before you follow its voice.'),
        npc('healer', 'Iven Saltmender', 'Storm physician', 35, 114,
            'Lightning leaves a wound that salt cannot clean. Rest by the blue lamps.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_health_potion', label='Buy Health Potion', cost=30, item='health_potion', tiered=True)]),
        npc('scout', 'Nera Kestrel', 'Cliff scout', 39, 101,
            'Gulls strike from the air, rays sail through the spray. The old sentinels wake whenever the tide turns.',
            mercenary_offers.offers()),
        npc('scholar', 'Orrin Glass', 'Tide historian', 45, 111,
            'These black pebbles are fused sand. The Eye Below was sealed before anyone remembers why.'),
        npc('trader', 'Bela Netwise', 'Quartermaster and material buyer', 29, 119,
            'I pay for what the tide leaves behind. Take provisions before you climb the cliffs.',
            [dict(id='buy_traveler_stew', label="Buy Traveler's Stew", cost=12, item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel', cost=500, bag='linen_satchel')], True),
        npc('watcher', 'Mara of the Last Light', 'Eye Below warden', 96, 34,
            'The Eye Below is sealed. Its stone remembers five voices, but no path opens yet. Learn what stalks this shore and return when the seal is ready.'),
        npc('stone', 'The Breakwater Meeting Stone', 'Gather a party · hire fighters', 91, 27,
            'The runes gather companions for 250 gold each. The Eye Below is sealed; this stone can still help a party face the shore.',
            mercenary_offers.offers(open_=True)),
    ]
    people[-1]['art'] = 'stone'
    quests = [
        quest('welcome', 'A Camp Against the Tide', 'warden', 'Meet Breakwater Camp’s physician, scout and historian.',
              [talk('healer', 'Meet Iven'), talk('scout', 'Meet Nera'), talk('scholar', 'Meet Orrin')], 60, 3200),
        quest('crabs', 'Claws in the Salt', 'scout', 'Drive the Saltclaws from the lower strand.',
              [kill('saltclaw', 6, 'Defeat Saltclaws')], 60, 3800, 'welcome'),
        quest('gulls', 'Wings Over Breakwater', 'scout', 'Stop the Stormgulls from circling the camp.',
              [kill('stormgull', 6, 'Defeat Stormgulls')], 61, 4100, 'crabs'),
        quest('rays', 'Glass in the Surf', 'scholar', 'Bring the fins of the rays that skim the middle shore.',
              [bring('glassfin', 5, 'Bring Glassfins')], 62, 4400, 'gulls'),
        quest('guards', 'The Tide Remembers', 'watcher', 'Silence the old Breaker Sentinels along the northern approach.',
              [kill('breakersentinel', 5, 'Defeat Breaker Sentinels')], 64, 5200, 'rays'),
        quest('eye', 'The Eye That Will Not Open', 'watcher', 'Inspect the sealed Eye and speak to the Meeting Stone. The descent is for a future expedition.',
              [visit('eye', 'Inspect the Eye Below'), talk('stone', 'Speak with the Meeting Stone')], 65, 6200, 'guards'),
        quest('heart', 'Heart of the Storm', 'warden', 'The living storm has taken shape on the high shore. Gather five companions.',
              [kill('maelstromheart', 1, 'Defeat the Maelstrom Heart')], 65, 9500, 'guards', group=True, recommendedPlayers=5),
        quest('patrol', 'Keep the Lamps Burning', 'warden', 'Thin the creatures gathering outside camp.',
              [kill('saltclaw', 3, 'Defeat Saltclaws'), kill('stormgull', 3, 'Defeat Stormgulls')],
              60, 2800, 'welcome', True),
    ]
    return people, quests


def path_distance(x, y, paths):
    best = 999
    for path in paths:
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            dx, dy = bx-ax, by-ay
            t = max(0, min(1, ((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            best = min(best, math.hypot(x-ax-t*dx, y-ay-t*dy))
    return best


def build():
    rng = random.Random(20261009)
    paths = [[(7,105),(30,105),(52,92),(67,72),(83,54),(103,31)],
             [(52,92),(26,74),(24,52),(42,34),(83,54)],
             [(67,72),(104,78),(109,55),(103,31)]]
    objects = [obj('breakwater_hut',25,109,0,width=4.5,depth=3.5),
               obj('breakwater_hut',41,108,0,width=4.5,depth=3.5),
               obj('breakwater_hut',19,119,0,width=4.5,depth=3.5),
               obj('tide_bell',32,110,.55),
               obj('stormlamp',18,98,.28),obj('stormlamp',43,99,.28),
               obj('stormlamp',47,118,.28),obj('stormlamp',33,117,.28),obj('meetingstone',89,25,1.7),
               obj('eye_arch',105,23,0,width=6,depth=4,place='stormglass_eye'),
               obj('tide_bell',92,36,.55,place='stormglass_bell')]
    for cx, cy, rx, ry in [(25,64,12,18),(71,39,15,10),(101,86,14,12)]:
        for a in range(0,360,24):
            x=cx+rx*math.cos(math.radians(a));y=cy+ry*math.sin(math.radians(a))
            if 5<x<123 and 5<y<123 and path_distance(x,y,paths)>4:
                objects.append(obj('stormglass_spire',x,y,.9))
    for kind,count,radius in [('saltpillar',85,.65),('blackpebble',100,.4),
                              ('seafoam',90,.1),('stormreed',75,.25)]:
        placed=0
        for _ in range(60000):
            if placed==count:break
            x,y=rng.uniform(6,122),rng.uniform(6,122)
            if (x<51 and y>93) or path_distance(x,y,paths)<3.7:continue
            if math.hypot(x-105,y-23)<11 or math.hypot(x-90,y-27)<8:continue
            if any(math.hypot(x-o['x'],y-o['y'])<radius+max(o['r'],o.get('width',0)/2,o.get('depth',0)/2)+1.1 for o in objects):continue
            objects.append(obj(kind,x,y,radius,v=rng.randrange(4)));placed+=1
        assert placed==count,(kind,placed)
    spawns=[dict(kind='maelstromheart',x=100,y=14)]
    for kind,count,lo,hi in [('saltclaw',11,87,100),('stormgull',10,65,87),
                             ('glassray',10,43,66),('breakersentinel',9,22,45)]:
        for _ in range(count):
            for _attempt in range(6000):
                x,y=rng.uniform(10,118),rng.uniform(lo,hi)
                if (x<51 and y>93) or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<12:continue
                if math.hypot(x-105,y-23)<12 or math.hypot(x-90,y-27)<9:continue
                if path_distance(x,y,paths)<2.7:continue
                if any(math.hypot(x-s['x'],y-s['y'])<(15 if s['kind']=='maelstromheart' else 6.2) for s in spawns):continue
                if any(math.hypot(x-o['x'],y-o['y'])<max(o['r'],o.get('width',0)/2,o.get('depth',0)/2)+1.8 for o in objects):continue
                spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)));break
            else:raise RuntimeError('cannot place '+kind)
    people,quests=people_and_quests()
    zone=dict(name=NAME,theme='stormglass',tagline='Black sand, white lightning, and a sealed eye beneath the sea',
              size=128,levels=[60,65],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),
              paths=[[[x,y] for x,y in p] for p in paths],objects=objects,slimes=spawns,npcs=people,
              places=[dict(id='stormglass_eye',name='The Eye Below',x=105,y=23,r=5),
                      dict(id='stormglass_bell',name='The Tide Bell',x=92,y=36,r=3)],
              quests=quests,city=dict(name='Breakwater Camp',x0=10,x1=49,y0=96,y1=124,
                                     plaza=dict(x=30,y=108),radius=6,entry=dict(x=13,y=105)),
              futureInstance=dict(name='The Eye Below',level=65,players=5,status='sealed',x=105,y=23,
                                  description='A sealed five-player descent beneath the stormglass sea.'),
              portals=[dict(id='stormglass_asterion_gate',name='The Stormglass Causeway',x=RETURN[0],y=RETURN[1],r=1.2,
                            to=17,tx=CITY_ARRIVAL[0],ty=CITY_ARRIVAL[1],look='stormglass')])
    check(zone)
    return zone


def check(zone):
    seen,grid=fen.flood(zone,ARRIVAL)
    for e in [*zone['npcs'],*zone['slimes'],*zone['portals'],dict(x=105,y=27),dict(x=92,y=38)]:
        assert seen[int(e['y']/.5),int(e['x']/.5)],f'unreachable: {e}'
    assert all(math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>=8 for s in zone['slimes'])
    assert all(math.hypot(s['x']-CITY_ARRIVAL[0],s['y']-CITY_ARRIVAL[1])>=8 for s in zone['slimes'])
    for q in zone['quests']:assert len('quest:accept:'+q['id'])<=32,q['id']
    assert len(zone['slimes'])==41 and len(zone['quests'])==8


def open_city_gate(city):
    city['objects']=[o for o in city['objects'] if not (o['x']>148 and 82<o['y']<94)]
    city['paths']=[p for p in city['paths'] if p!=[[134,88],[160,88],[170,88]]]
    city['paths'].append([[134,88],[160,88],[170,88]])
    city['portals']=[p for p in city['portals'] if p['id']!='asterion_stormglass_gate']
    city['portals'].append(dict(id='asterion_stormglass_gate',name='The Stormglass Causeway',x=CITY_GATE[0],y=CITY_GATE[1],
                                r=1.2,to=ZONE,tx=ARRIVAL[0],ty=ARRIVAL[1],look='stormglass'))
    seen,_=fen.flood(city,(city['spawn']['x'],city['spawn']['y']))
    assert seen[int(CITY_GATE[1]/.5),int(CITY_GATE[0]/.5)],'Asterion causeway blocked'


def main():
    world=json.loads(MAP.read_text())
    assert world['zones'][16]['name']=='Asterion' and world['zones'][17]['name']=='The Moonwell'
    later=world['zones'][ZONE:]
    world['zones']=world['zones'][:ZONE-1]
    open_city_gate(world['zones'][16])
    world['zones'].append(build())
    world['zones'].extend(later)
    spark_travel.ensure(world)
    MAP.write_text(json.dumps(world,indent=2)+'\n')
    items=json.loads(ITEMS.read_text())
    for id_,name,sell in [('saltclaw_shell','Saltclaw Shell',460),('stormgull_feather','Stormgull Feather',490),
                          ('glassfin','Glassfin',530),('breaker_core','Breaker Core',600),
                          ('stormheart','Stormheart',2200)]:
        if not any(i['id']==id_ for i in items):
            items.append(dict(id=id_,name=name,kind='material',rarity='common',sell=sell))
    ITEMS.write_text(json.dumps(items,indent=2)+'\n')
    print(f'{NAME}: {len(world["zones"][18]["objects"])} objects, 41 enemies, 8 quests')


if __name__=='__main__':main()
