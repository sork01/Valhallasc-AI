#!/usr/bin/env python3
"""Build Asterion, the city of seven rings, and its private Moonwell dungeon.

Run after generate_moonspore.py. The generator keeps older zone ids and is byte-stable.
"""
import json
import math
import random
from pathlib import Path

import generate_gloamfen as fen
import generate_skaldholm as sk
import mercenary_offers
import spark_travel
from quest_gear_rewards import add_reward

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
XP = json.loads((ROOT / 'world/levels.txt').read_text())
CITY_ID, DUNGEON_ID = 17, 18
CITY_NAME, DUNGEON_NAME = 'Asterion', 'The Moonwell'
CENTRE = (90., 88.)
ARRIVAL, HOME_GATE = (90., 162.), (90., 171.)
FOREST_GATE, FOREST_ARRIVAL = (117., 112.), (107., 112.)
STONE, STAIRS = (119., 86.), (125., 93.)
COLORS = ['#b9e4dc', '#d9a8c9', '#e8cc8a', '#a9b8e8', '#b5d998', '#e8ac93', '#d0bbe8']


def object_(kind, x, y, r=0., **extra):
    return dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r, v=0, **extra)


def person(id_, name, role, x, y, color, dialogue, look=None, offers=None, buys=False, route=None, speed=0, phase=0):
    p = dict(id='asterion_' + id_, name=name, role=role, x=x, y=y, color=color,
             dialogue=dialogue, look=look or {}, offers=offers or [], buys=buys)
    if route:
        p.update(route=[[round(a, 2), round(b, 2)] for a, b in route], speed=speed, pause=1.2,
                 phase=phase, x=round(route[0][0], 2), y=round(route[0][1], 2))
    return p


def look(skin, hair, style, hat=None, hatColor=None, apron=None, beard=None, scale=1):
    return dict(skin=skin, hair=hair, style=style, **({'hat': hat, 'hatColor': hatColor} if hat else {}),
                **({'apron': apron} if apron else {}), **({'beard': beard} if beard else {}), scale=scale)


def q(id_, title, giver, description, objectives, level=60, gold=4000, requires=None, repeatable=False, **extra):
    return add_reward(dict(id='asterion_' + id_, title=title, npc='asterion_' + giver,
                           description=description, objectives=objectives, level=level,
                           rewardXp=XP[level - 1] // 10, rewardGold=gold,
                           requires='asterion_' + requires if requires else None,
                           repeatable=repeatable, **extra))


def talk(id_, label): return dict(kind='talk', target='asterion_' + id_, label=label, count=1)
def kill(kind, count, label): return dict(kind='kill', target=kind, label=label, count=count)
def bring(item, count, label): return dict(kind='bring', target=item, label=label, count=count)


def ring(radius, count=32, phase=0):
    return [(CENTRE[0] + radius * math.cos(phase + i * math.tau / count),
             CENTRE[1] + radius * math.sin(phase + i * math.tau / count)) for i in range(count)]


def people():
    p = [
        person('archon', 'Archon Seraphine Vey', 'Keeper of the Seven Rings', 85, 101, '#b7a5dd',
               'The city turns around an empty sky. Walk its rings, meet the voices that hold it together, then return to me.',
               look('#c78e6e','#f2e7d5','long','feather','#733a88')),
        person('cartographer', 'Ixo the Many-Eyed', 'Cartographer', 68, 83, '#78bfd3',
               'I chart alleys that move with the light. The deepest line on my map runs beneath the Meeting Stone.',
               look('#946f6b','#f1c765','bun','cap','#2d6e80')),
        person('bellkeeper', 'Mora Thirteenbells', 'Bellkeeper', 92, 62, '#e6bd73',
               'Every hour has a bell. The thirteenth is for those who have not come home from the Moonwell.',
               look('#e4aa86','#fbf0d0','bald','hood','#81604f')),
        person('gardener', 'Umi of the Roofs', 'Sky gardener', 58, 112, '#7dc3a2',
               'Each roof is a little garden. The moon fungus feeds the roots; the roots keep our city from cracking.',
               look('#6d493c','#c8f0d2','long','straw','#d0a456',apron='#508575')),
        person('healer', 'Doctor Pell Prism', 'Moonwell physician', 104, 104, '#d7e4f0',
               'Drink before you descend. Down there the water remembers every wound.',
               look('#735447','#d7e9f3','short','hood','#5187a3'),
               [dict(id='blessing',label='Receive a healing blessing',cost=0,heal=10000),
                dict(id='buy_health_potion',label='Buy Health Potion',cost=30,item='health_potion',tiered=True),
                dict(id='buy_mana_potion',label='Buy Mana Potion',cost=30,item='mana_potion',tiered=True)]),
        person('merchant', 'Nim Copperkite', 'Seven Rings provisioner', 72, 111, '#e6a77c',
               'Everything you find below has a buyer above. I also sell what keeps you alive long enough to sell it.',
               look('#b77f55','#493a67','bun','feather','#d8a344',apron='#b7594f'),
               [dict(id='buy_traveler_stew',label="Buy Traveler's Stew",cost=12,item='traveler_stew',tiered=True),
                dict(id='satchel',label='Buy Linen Satchel',cost=500,bag='linen_satchel')], True),
        person('stonewarden', 'Voss the Unmoored', 'Meeting Stone warden', 116, 94, '#9ec8dd',
               'The Stone gathers the lost. The Moonwell below it scatters the unready. Bring five if you want the bell to sound for your return.',
               look('#ae806d','#fcf6e3','long','helm','#6a91a8',beard='#ece0ce')),
        person('stone', 'The Asterion Meeting Stone', 'Gather a party · hire fighters', 120.5, 88.0, '#9ec8dd',
               'The runes call companions to this court. The stair beside the stone opens a private Moonwell for each party.',
               offers=mercenary_offers.offers(open_=True)),
        person('singer', 'Vela Glassvoice', 'City chorus', 92, 107, '#f0c690',
               'The streets are instruments. Stand at the centre and you can hear each ring answer the next.',
               look('#b47059','#2b274d','long','feather','#ffe7a1')),
        person('smith', 'Bramble Gilt', 'Glass-forged armourer', 108, 78, '#bd93a7',
               'The first crack in your armour is the most honest one. I can fit your starter kit, if the old pieces have failed.',
               look('#745c4e','#c79055','bald',apron='#533f56',beard='#c79055'),
               [dict(id='fitting',label='Replace and fit starter gear',cost=0,gear=True)]),
    ]
    props={'archon':'crown','cartographer':'map','bellkeeper':'bells','gardener':'vine',
           'healer':'prism','merchant':'kite','stonewarden':'key','singer':'lyre','smith':'hammer'}
    for n in p:
        if n['id'][9:] in props:n['look']['prop']=props[n['id'][9:]]
    next(n for n in p if n['id']=='asterion_stone')['art']='stone'
    names = [('Tavi Kite', 'Paper-wing courier', '#e2a8c0', '#aa7355', '#e9d4a2','feather'),
             ('Orro', 'Masked bell runner', '#91b7d9','#704f48','#e2d0e8','cap'),
             ('Jin Sunthread', 'Lantern mender', '#dfbd73','#b86d50','#2c3148','straw'),
             ('Dessa of Nine Doors', 'Door keeper', '#b7a1d9','#6e4e3f','#f7f0e1','hood'),
             ('Malo Inkhand', 'Map seller', '#81c3b4','#c99875','#292f55','cap'),
             ('Piri Starling', 'Rooftop dancer', '#ee9d83','#9d6d56','#d5d3f4','feather'),
             ('Rook the Lantern', 'Night watch', '#b3cf96','#795a4d','#e6b36c','helm'),
             ('Ari Copperglass', 'Messenger', '#9fc6e2','#bf886d','#2c3549','cap'),
             ('Yana Two-Moons', 'Glass painter', '#d8b4d9','#855e45','#f5e8d2','straw'),
             ('Kes of the Steps', 'Pilgrim', '#afcfb5','#674f41','#e7bf97','hood')]
    routes = [ring(16,48),ring(34,64),ring(56,80)]
    for i,(name,role,color,skin,hair,hat) in enumerate(names):
        route = routes[i%3]
        p.append(person('walker'+str(i),name,role,0,0,color,
                        'Every ring has a different sky. I am still looking for the one I was born under.',
                        dict(look(skin,hair,['bun','long','short'][i%3],hat,color,scale=.78 if i in (0,5) else 1),
                             prop=['kite','bells','lantern','key','map','lyre','prism','hammer','vine','crown'][i]),
                        route=route,speed=1.4+i%4*.35,phase=i*7.3))
    return p


def quests():
    return [
        q('welcome','The Seven Rings','archon','Meet the voices of Asterion and discover the Meeting Stone.',
          [talk('cartographer','Speak to Ixo'),talk('bellkeeper','Speak to Mora'),talk('gardener','Speak to Umi'),
           talk('stonewarden','Speak to Voss')],60,2800),
        q('lamps','A Thousand Little Suns','bellkeeper','Mora needs moon silk for the glass lanterns that guide the city.',
          [bring('moon_silk',6,'Bring Moon Silk')],60,3400,'welcome'),
        q('roots','The City Has Roots','gardener','Umi needs living caps and root fibres to repair the garden terraces.',
          [bring('glowcap',5,'Bring Glowcaps'),bring('root_heart',5,'Bring Rootlurker Heartwood')],60,3800,'welcome'),
        q('charts','A Map That Breathes','cartographer','Survey the hazards beneath the city by bringing back their traces.',
          [bring('wraith_lantern',5,'Bring Lantern Wraith Embers'),bring('widow_silk',2,'Bring Widow Silk')],60,4300,'welcome'),
        q('descent','The Thirteenth Bell','stonewarden','Go below the Meeting Stone and silence the Nightbloom echo that fills the Moonwell.',
          [kill('moonwell_echo',1,'Silence the Moonwell Echo'),
           kill('tideglass_heron',1,'Free the Tideglass Heron'),
           kill('hourpetal_stag',1,'Still the Hourpetal Stag'),
           kill('moonskein_weaver',1,'Unravel the Moonskein Weaver')],60,6900,'welcome',group=True,recommendedPlayers=5),
        q('market','The Night Market Never Sleeps','merchant','Bring fresh materials for the lantern merchants.',
          [bring('moon_silk',3,'Bring Moon Silk'),bring('glowcap',3,'Bring Glowcaps')],60,2000,'welcome',True),
    ]


def roads():
    r = [dict(t=2,x=90,y=88,r=12)]
    for a,b in [(16,20),(32,36),(54,58)]: r.append(dict(t=1,x=90,y=88,r0=a,r1=b))
    for x0,y0,x1,y1 in [(87,12,93,170),(10,85,170,91),(44,44,48,132),(132,44,136,132)]:
        r.append(dict(t=1,x0=x0,y0=y0,x1=x1,y1=y1))
    for x,y,rad in [(119,86,10),(60,62,7),(62,120,7),(119,120,7),(90,153,7)]:
        r.append(dict(t=2,x=x,y=y,r=rad))
    return r


def road_at(x,y):
    d=math.hypot(x-90,y-88)
    return (d<23 or any(a-3<d<b+3 for a,b in [(32,36),(54,58)])
            or abs(x-90)<5 or abs(y-88)<5 or abs(x-46)<4 and 44<y<132
            or abs(x-134)<4 and 44<y<132
            or any(math.hypot(x-a,y-b)<rad+4 for a,b,rad in [(119,86,10),(60,62,7),(62,120,7),(119,120,7),(90,153,7)]))


def city():
    rng=random.Random(20261009)
    b=sk.Builder(rng)
    b.add(object_('astrolabe',90,88,3.2),force=True)
    b.add(object_('meetingstone',*STONE,1.7),force=True)
    for x,y in [(60,62),(62,120),(119,120)]:b.add(object_('moonobelisk',x,y,1.1),force=True)
    for radius,count in [(25,36),(45,56),(68,80)]:
        for x,y in ring(radius,count):
            if not (15<x<165 and 15<y<155) or road_at(x,y):continue
            color=COLORS[rng.randrange(len(COLORS))]
            width,depth=rng.choice([(3.2,3.1),(3.8,3.4),(4.2,3.2)])
            o=object_('aetherhouse',x,y,0,width=width,depth=depth,color=color,label=f'{rng.randrange(1,999)} Glasswalk',sign='live')
            b.add(o,margin=.65)
    # Fill the outer wedge plots. The arrangement follows the rings rather than a rectangular street grid.
    attempts=0
    while sum(o['kind']=='aetherhouse' for o in b.objects)<130 and attempts<8000:
        attempts+=1
        x,y=rng.uniform(15,165),rng.uniform(16,151)
        if road_at(x,y):continue
        o=object_('aetherhouse',x,y,0,width=3.3,depth=3.1,color=rng.choice(COLORS),label=f'{rng.randrange(1,999)} Glasswalk',sign='live')
        b.add(o,margin=.95)
    for radius,count in [(20,32),(36,48),(57,64)]:
        for i,(x,y) in enumerate(ring(radius,count)):
            if i%3==0 and 10<x<170 and 10<y<160:b.add(object_('glasslamp',x,y,.15),force=True)
    for x,y in [(88,169),(92,169),(122,95),(128,95)]:b.add(object_('glasslamp',x,y,.15),force=True)
    assert sum(o['kind']=='aetherhouse' for o in b.objects)>=120
    for i,o in enumerate((o for o in b.objects if o['kind']=='aetherhouse'),1):
        o['label']=f'{i} Glasswalk'
    zone=dict(name=CITY_NAME,theme='asterion',tagline='Seven concentric streets beneath a sky of living glass',size=180,
              spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),paths=[],roads=roads(),objects=b.objects,slimes=[],npcs=people(),
              quests=quests(),city=dict(name=CITY_NAME,x0=10,x1=170,y0=10,y1=172,plaza=dict(x=90,y=88),radius=13,
                                         entry=dict(x=90,y=162)),
              portals=[dict(id='asterion_moonspore_gate',name='The Glassroot Causeway',x=HOME_GATE[0],y=HOME_GATE[1],r=1.2,
                            to=16,tx=FOREST_ARRIVAL[0],ty=FOREST_ARRIVAL[1],look='moonspore'),
                       dict(id='asterion_moonwell_stairs',name='The Moonwell Descent',x=STAIRS[0],y=STAIRS[1],r=1.2,
                            to=DUNGEON_ID,tx=21,ty=64,look='stairs_down')])
    seen,_=fen.flood(zone,ARRIVAL)
    for e in [*zone['npcs'],*zone['portals']]:
        x,y=e['x'],e['y']
        if e.get('route'):
            assert not sk.route_clear(fen.obstacle_grid(zone,.5,margin=.35),[tuple(pt) for pt in e['route']]),e['id']
        else:assert seen[int(y/.5),int(x/.5)],f'unreachable {e.get("id")}'
    return zone


def dungeon():
    # A chain of floating petal islands crosses the water, winding around its open central basin.
    # The mask, rather than repeated rectangular halls, owns both the visible shore and collision.
    size=128
    import numpy as np
    yy,xx=np.mgrid[:size,:size]
    floor=np.zeros((size,size),dtype=bool)
    islands=[(21,64,16,13),(42,47,17,14),(68,30,16,14),(91,59,18,16),(101,91,18,15),(104,107,16,15)]
    for x,y,rx,ry in islands:
        theta=np.arctan2(yy-y,xx-x)
        edge=1+.09*np.sin(theta*7+x)+.06*np.sin(theta*11+y)
        floor|=((xx-x)/rx)**2+((yy-y)/ry)**2 < edge**2
    routes=[[(21,64),(42,47)],[(42,47),(68,30)],[(68,30),(91,59)],[(91,59),(101,91)],[(101,91),(104,107)]]
    bridges=np.zeros_like(floor)
    for (ax,ay),(bx,by) in routes:
        t=np.clip(((xx-ax)*(bx-ax)+(yy-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2),0,1)
        bridge=(xx-ax-t*(bx-ax))**2+(yy-ay-t*(by-ay))**2 < 4.5**2
        bridges|=bridge;floor|=bridge
    # Only the islands are solid ground; causeways gleam like traversable glass.
    rows=[''.join('=' if bridges[y,x] else 'o' if floor[y,x] else ' ' for x in range(size)) for y in range(size)]
    used=floor.copy();objects=[]
    for y in range(size):
        x=0
        while x<size:
            if used[y,x]:x+=1;continue
            x1=x+1
            while x1<min(size,x+8) and not used[y,x1]:x1+=1
            y1=y+1
            while y1<min(size,y+8) and not used[y1,x:x1].any():y1+=1
            used[y:y1,x:x1]=True
            objects.append(object_('void',(x+x1)/2,(y+y1)/2,0,width=x1-x,depth=y1-y))
            x=x1
    mobs=[]
    for kind,pts in [('dew_moth',[(30,61),(33,55),(52,44),(57,37),(81,39),(86,48)]),
                     ('lumen_eel',[(42,57),(59,33),(78,39),(94,72),(97,84)]),
                     ('rootbell',[(29,51),(54,50),(73,37),(86,65),(107,88)]),
                     ('tideglass_heron',[(42,47)]),('hourpetal_stag',[(68,30)]),
                     ('moonskein_weaver',[(91,59)]),('moonwell_echo',[(104,107)])]:
        mobs.extend(dict(kind=kind,x=x,y=y) for x,y in pts)
    keep=[(s['x'],s['y'],6 if s['kind'] in ('tideglass_heron','hourpetal_stag','moonskein_weaver','moonwell_echo') else 2.5) for s in mobs]
    keep += [(21,64,8),(14,64,4),(109,116,5)]
    rng=random.Random(20261009)
    for x,y,_,_ in islands:
        objects.append(object_('moonmirror',x+8,y+7,.75))
        for n in range(8):
            a=n*math.tau/8+rng.uniform(-.2,.2);px=x+math.cos(a)*10;py=y+math.sin(a)*8
            if floor[round(py),round(px)] and all(math.hypot(px-kx,py-ky)>kr+1 for kx,ky,kr in keep):
                objects.append(object_('moonlily',px,py,.25,petals=5+n%3))
    for x,y in [(26,70),(36,43),(62,23),(83,54),(102,98),(111,111)]:
        if floor[y,x] and all(math.hypot(x-kx,y-ky)>kr+1 for kx,ky,kr in keep):objects.append(object_('moonreed',x,y,.2))
    zone=dict(name=DUNGEON_NAME,theme='moonwell',tagline='A floating garden where moonlight pools like water',size=size,
              levels=[60,60],players=5,min_level=60,copies=4,final_boss='moonwell_echo',
              spawn=dict(x=21,y=64),paths=[],moonwellFloor=rows,objects=objects,
              slimes=mobs,npcs=[],quests=[],
              portals=[dict(id='moonwell_stairs_up',name='The Stairs Up',x=14,y=64,r=1.2,to=CITY_ID,tx=127,ty=97,look='stairs_up'),
                       dict(id='moonwell_exit',name='The Rootway Home',x=109,y=116,r=1.2,to=CITY_ID,tx=127,ty=97,
                            after_clear=True,look='exit')])
    for s in mobs:
        if not floor[s['y']-2:s['y']+3,s['x']-2:s['x']+3].all():
            x0,y0=s['x'],s['y']
            choices=sorted(((math.hypot(x-x0,y-y0),x,y) for y in range(5,size-5) for x in range(5,size-5)
                            if floor[y-2:y+3,x-2:x+3].all() and all(math.hypot(x-q['x'],y-q['y'])>2.2 for q in mobs if q is not s)))
            assert choices[0][0]<5,s
            _,s['x'],s['y']=choices[0]
    seen,_=fen.flood(zone,(21,64))
    for s in [*mobs,*zone['portals']]:assert seen[int(s['y']/.5),int(s['x']/.5)],s
    assert all(floor[y,x] for x,y in [(21,64),(14,64),(42,47),(68,30),(91,59),(104,107),(109,116)])
    return zone


def open_forest_gate(forest):
    forest['objects']=[o for o in forest['objects'] if not (o['x']>102 and 105<o['y']<120)
                       and math.hypot(o['x']-FOREST_GATE[0],o['y']-FOREST_GATE[1])>o['r']+3]
    # Relocate existing slots in place: old global enemy IDs must remain stable.
    displaced=[s for s in forest['slimes'] if math.hypot(s['x']-FOREST_ARRIVAL[0],s['y']-FOREST_ARRIVAL[1])<9]
    for i,s in enumerate(displaced):s.update(x=96+i*4,y=97)
    forest['paths']=[p for p in forest['paths'] if p!=[[94,75],[107,112],[117,112]]]
    forest['paths'].append([[94,75],[107,112],[117,112]])
    forest['portals']=[p for p in forest['portals'] if p['id']!='moonspore_asterion_gate']
    forest['portals'].append(dict(id='moonspore_asterion_gate',name='The Glassroot Causeway',
                                  x=FOREST_GATE[0],y=FOREST_GATE[1],r=1.2,to=CITY_ID,
                                  tx=ARRIVAL[0],ty=ARRIVAL[1],look='asterion'))


def main():
    world=json.loads(MAP.read_text())
    assert world['zones'][15]['name']=='The Moonspore Canopy'
    later=world['zones'][DUNGEON_ID:]
    world['zones']=world['zones'][:CITY_ID-1]
    assert len(world['zones'])==16
    open_forest_gate(world['zones'][15])
    world['zones'].extend([city(),dungeon()])
    world['zones'].extend(later)
    if any(z.get('name')=='The Stormglass Shore' for z in later):
        from generate_stormglass import open_city_gate
        open_city_gate(world['zones'][CITY_ID-1])
    spark_travel.ensure(world)
    MAP.write_text(json.dumps(world,indent=2)+'\n')
    items=json.loads(ITEMS.read_text())
    materials=[('moon_dew','Moonwell Dew',240),('lumen_scale','Lumen Eel Scale',270),
               ('rootbell_seed','Rootbell Seed',300),('tideglass_plume','Tideglass Plume',1100),
               ('hourpetal_antler','Hourpetal Antler',1400),('moonskein_thread','Moonskein Thread',1700)]
    known={i['id'] for i in items}
    for id_,name,sell in materials:
        if id_ not in known:items.append(dict(id=id_,name=name,kind='material',rarity='common',sell=sell))
    ITEMS.write_text(json.dumps(items,indent=2)+'\n')
    print(f'{CITY_NAME}: {len(world["zones"][16]["objects"])} objects, {len(world["zones"][16]["npcs"])} NPCs; '
          f'{DUNGEON_NAME}: {len(world["zones"][17]["slimes"])} enemies')


if __name__=='__main__':main()
