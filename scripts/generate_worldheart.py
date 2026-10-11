#!/usr/bin/env python3
"""Seeded level-80 city in and around a single giant jungle tree."""
import json, math, random
from pathlib import Path
import generate_gloamfen as fen
import mercenary_offers, spark_travel
from quest_gear_rewards import add_reward

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'world/map.txt'; ITEMS=ROOT/'world/items.txt'
XP=json.loads((ROOT/'world/levels.txt').read_text())
OUTSIDE=23; INSIDE=24
JUNGLE_GATE=(138,80); JUNGLE_ARRIVAL=(132,80)
OUT_GATE=(7,95); OUT_ARRIVAL=(15,95)
HOLLOW_GATE=(56,72); HOLLOW_ARRIVAL=(56,65)
IN_GATE=(48,87); IN_ARRIVAL=(48,80)

def obj(kind,x,y,r=0,**extra):return dict(kind=kind,x=round(x,2),y=round(y,2),r=r,v=extra.pop('v',0),**extra)
def npc(key,name,role,x,y,dialogue,offers=None,buys=False,art=None):
    result=dict(id='heart_'+key,name=name,role=role,x=x,y=y,color='#e4f7ae',dialogue=dialogue,
                offers=offers or [],buys=buys,look=dict(skin='#ad7857',hair='#28574b',style='long',hat='hood',hatColor='#569e66'))
    if art:result['art']=art
    return result
def talk(key,label):return dict(kind='talk',target='heart_'+key,count=1,label=label)
def visit(key,label):return dict(kind='visit',target='heart_'+key,count=1,label=label)
def quest(key,title,giver,description,objectives,gold=10000,requires=None,repeatable=False):
    return add_reward(dict(id='heart_'+key,title=title,npc='heart_'+giver,description=description,
                           objectives=objectives,level=80,rewardXp=XP[79]//10,rewardGold=gold,
                           requires='heart_'+requires if requires else None,repeatable=repeatable))
def distance(x,y,paths):
    d=1e9
    for path in paths:
        for (ax,ay),(bx,by) in zip(path,path[1:]):
            vx,vy=bx-ax,by-ay;t=max(0,min(1,((x-ax)*vx+(y-ay)*vy)/(vx*vx+vy*vy)))
            d=min(d,math.hypot(x-ax-t*vx,y-ay-t*vy))
    return d
def clear(o,objects,pad=0):
    return all(math.hypot(o['x']-a['x'],o['y']-a['y'])>o.get('r',0)+max(a.get('r',0),a.get('width',0)/2,a.get('depth',0)/2)+pad for a in objects)

def outside():
    rng=random.Random(20261014)
    # The approach climbs a living root. Three branches join a ring of decks
    # round the trunk; two outlying bridges form a second, higher circuit.
    paths=[[(7,95),(20,95),(36,87),(56,88),(76,87),(91,73)],
           [(36,87),(25,68),(33,44),(50,29),(73,30),(91,47),(91,73)],
           [(56,88),(56,72),(74,63),(91,47)],
           [(25,68),(19,35),(38,18),(50,29)],
           [(91,73),(109,85),(112,53),(91,47)],
           [(76,87),(92,100),(109,85)]]
    objects=[obj('worldheart_trunk',56,49,9),obj('hollow_arch',56,74,0,place='heart_hollow'),
             obj('canopy_market',39,95,1.1),obj('canopy_market',74,96,1.1,v=1),
             obj('sunleaf_observatory',91,44,0,place='heart_observatory'),
             obj('suspended_garden',24,66,1.2),obj('suspended_garden',109,84,1.2,v=1)]
    # The huge crown is art; its inhabited walkways stay free of collision.
    for kind,count,r in [('buttress_root',44,1.2),('hanging_pod',30,.75),('leaf_lantern',52,.12),
                         ('epiphyte_garden',50,.25),('branch_rail',38,.16)]:
        placed=0
        for _ in range(150000):
            if placed==count:break
            x,y=rng.uniform(8,119),rng.uniform(8,117)
            if 22<x<88 and 67<y<104 or distance(x,y,paths)<(3.7 if r>.6 else 2.4):continue
            if math.hypot(x-56,y-49)<12 or math.hypot(x-OUT_ARRIVAL[0],y-OUT_ARRIVAL[1])<10:continue
            o=obj(kind,x,y,r,v=rng.randrange(4))
            if not clear(o,objects,.7):continue
            objects.append(o);placed+=1
        assert placed==count,(kind,placed)
    folk=[
        npc('matriarch','Iria Sunbark','Canopy matriarch',54,92,'Veyrroot is a city grown from one living tree. Its bridges circle the crown; its oldest halls lie within the trunk.',art='heart_matriarch'),
        npc('ranger','Telo Branchstep','Bridge keeper',34,82,'The bridges carry visitors between the gardens, market and high observatory. I keep every route clear.'),
        npc('apiarist','Miri Nectar','Nectar keeper',79,80,'Our lanterns gather daylight in their amber vessels. Follow their glow to the eastern market.'),
        npc('healer','Ena Dew','Leaf healer',28,95,'Rest here. The tree carries cool water into every balcony.',[dict(id='blessing',label='Receive a healing blessing',cost=0,heal=10000),dict(id='potion',label='Buy Health Potion',cost=30,item='health_potion',tiered=True)]),
        npc('trader','Boro Coil','Canopy trader',43,100,'My wares travel in leaf baskets, never carts.',[dict(id='stew',label="Buy Traveler's Stew",cost=12,item='traveler_stew',tiered=True),dict(id='satchel',label='Buy Linen Satchel',cost=500,bag='linen_satchel')],True),
        npc('lookout','Sela Highleaf','Crown lookout',88,57,'From the upper loop you can see both the jungle and the golden heartwood windows.'),
        npc('stone','Crown Meeting Stone','Gather a party · hire fighters',68,77,'Meet your companions here before the Seed Vault opens.',mercenary_offers.offers(open_=True),art='stone'),
    ]
    quests=[
        quest('welcome','A City Above the Rain','matriarch','Meet the healer, ranger and nectar keeper on the branching decks.',[talk('healer','Meet Ena'),talk('ranger','Meet Telo'),talk('apiarist','Meet Miri')],8500),
        quest('walkways','The Living Walk','ranger','Follow the upper branch to the observatory and meet its lookout.',[visit('observatory','Visit the Sunleaf Observatory'),talk('lookout','Meet Sela Highleaf')],9400,'welcome'),
        quest('lanterns','Light in the Leaves','apiarist','Trace the eastern lantern walk and speak with the trader who tends its vessels.',[visit('lantern_walk','Walk the lantern bridge'),talk('trader','Speak with Boro Coil')],10200,'walkways'),
        quest('gardens','The High Gardens','lookout','Find the hanging gardens, then ask Ena how their cool water reaches the city.',[visit('garden_walk','Visit the hanging gardens'),talk('healer','Speak with Ena Dew')],10800,'lanterns'),
        quest('market','A Market in the Canopy','ranger','Cross the western market deck and meet the traders beneath the crown.',[visit('market_walk','Visit the canopy market'),talk('trader','Meet Boro Coil')],11600,'gardens'),
        quest('circuits','The Crown Circuit','matriarch','Inspect the observatory and the trunk door before entering the heartwood.',[visit('observatory','Visit the Sunleaf Observatory'),visit('hollow','Find the Hollow Arch')],12000,'welcome'),
        quest('patrol','Keep the Branches Bright','ranger','Make another circuit from the observatory to the Hollow Arch.',[visit('observatory','Visit the Sunleaf Observatory'),visit('hollow','Visit the Hollow Arch')],7200,'welcome',True),
    ]
    zone=dict(name='Veyrroot Canopy',theme='worldtree',tagline='An open-air city of ring decks, vine bridges and sunlit rooms in a colossal jungle tree',
              size=128,levels=[80,80],spawn=dict(x=OUT_ARRIVAL[0],y=OUT_ARRIVAL[1]),paths=[[list(p) for p in path] for path in paths],
              objects=objects,slimes=[],npcs=folk,places=[dict(id='heart_observatory',name='Sunleaf Observatory',x=87,y=44,r=4),dict(id='heart_hollow',name='Hollow Arch',x=56,y=70,r=4),
                                                          dict(id='heart_lantern_walk',name='Lantern Walk',x=76,y=87,r=4),dict(id='heart_garden_walk',name='Hanging Gardens',x=25,y=68,r=4),
                                                          dict(id='heart_market_walk',name='Canopy Market',x=36,y=87,r=4)],quests=quests,
              city=dict(name='Veyrroot Canopy',x0=20,x1=95,y0=65,y1=105,plaza=dict(x=56,y=88),radius=7,entry=dict(x=15,y=95)),
              portals=[dict(id='canopy_jungle_gate',name='The Living Root',x=OUT_GATE[0],y=OUT_GATE[1],r=1.2,to=22,tx=JUNGLE_ARRIVAL[0],ty=JUNGLE_ARRIVAL[1],look='worldtree'),
                       dict(id='canopy_hollow_gate',name='The Hollow Arch',x=HOLLOW_GATE[0],y=HOLLOW_GATE[1],r=1.2,to=INSIDE,tx=IN_ARRIVAL[0],ty=IN_ARRIVAL[1],look='heartwood')])
    check(zone);return zone

def inside():
    # A complete second floor: living galleries bend around the luminous pith,
    # with hollowed chambers and a door in the upper heartwood.
    paths=[[(48,87),(48,75),(48,63),(35,57),(24,43),(34,28),(48,22)],
           [(48,63),(63,57),(73,42),(62,27),(48,22)],
           [(24,43),(38,43),(48,48),(60,43),(73,42)],
           [(35,57),(30,70),(48,75),(67,69),(63,57)],
           [(34,28),(48,34),(62,27)]]
    objects=[obj('heartwood_vault',48,14,0,place='heart_seed_door'),
             obj('heartwood_core',48,48,0),obj('hollow_lift',42,82,0),
             obj('amber_library',25,31,1.2),obj('pith_forge',70,55,1.2),
             obj('root_loom',26,65,1.1),obj('seed_chapel',72,30,1.2)]
    rng=random.Random(20261015)
    for kind,count,r in [('heartwood_column',18,.65),('glow_sconce',32,.06),('amber_window',18,.06),('root_bench',12,.55)]:
        placed=0
        for _ in range(100000):
            if placed==count:break
            x,y=rng.uniform(14,82),rng.uniform(13,80)
            if distance(x,y,paths)<2.3 or math.hypot(x-48,y-87)<9 or math.hypot(x-48,y-18)<9:continue
            o=obj(kind,x,y,r,v=rng.randrange(4))
            if not clear(o,objects,.6):continue
            objects.append(o);placed+=1
        assert placed==count,(kind,placed)
    folk=[
        npc('archivist','Oli Amberleaf','Heartwood archivist',30,35,'The tree remembers every season in amber rings. The Seed Vault is older than the city.',art='heart_archivist'),
        npc('carver','Ruva Rootsong','Living wood carver',69,61,'We coax halls from the wood. We never cut the pith.'),
        npc('oracle','Veya of the Pith','Pith oracle',49,45,'I hear a second heartbeat behind the Seed Vault door. It answers only to the old crown.',art='heart_oracle'),
        npc('custodian','Mosslet','Seed Vault custodian',48,25,'The door opens when the tree is ready. Its inner chambers are sealed for now.'),
    ]
    quests=[
        quest('rings','What the Rings Remember','archivist','Visit the living core and speak with the oracle.',[visit('core','Read the living rings'),talk('oracle','Consult Veya')],12500),
        quest('seed_vault','The Unopened Seed','oracle','Climb to the sealed Seed Vault and speak with its custodian.',[visit('seed_door','Inspect the Seed Vault entrance'),talk('custodian','Speak to Mosslet')],15000,'rings'),
    ]
    zone=dict(name='Veyrroot Heartwood',theme='heartwood',tagline='The inhabited hollow of the world-tree: amber libraries, living rooms and a sealed seed vault',
              size=96,levels=[80,80],spawn=dict(x=IN_ARRIVAL[0],y=IN_ARRIVAL[1]),paths=[[list(p) for p in path] for path in paths],
              objects=objects,slimes=[],npcs=folk,places=[dict(id='heart_core',name='The Living Pith',x=48,y=53,r=4),
                                                        dict(id='heart_seed_door',name='The Seed Vault',x=48,y=20,r=4)],quests=quests,
              city=dict(name='Veyrroot Heartwood',x0=14,x1=82,y0=12,y1=88,plaza=dict(x=48,y=48),radius=5,entry=dict(x=48,y=80)),
              futureInstance=dict(name='The Seed Vault',level=80,players=5,status='sealed',x=48,y=14,
                                  description='An enormous living iris of bark and amber closes the chambers in the tree\'s heart.'),
              portals=[dict(id='hollow_canopy_gate',name='The Hollow Arch',x=IN_GATE[0],y=IN_GATE[1],r=1.2,to=OUTSIDE,tx=HOLLOW_ARRIVAL[0],ty=HOLLOW_ARRIVAL[1],look='worldtree')])
    check(zone);return zone

def check(zone):
    seen,_=fen.flood(zone,(zone['spawn']['x'],zone['spawn']['y']))
    for target in [*zone['npcs'],*zone['slimes'],*zone['portals'],*zone['places']]:
        assert seen[int(target['y']/.5),int(target['x']/.5)],f'{zone["name"]}: unreachable {target}'
    assert all(math.hypot(s['x']-zone['spawn']['x'],s['y']-zone['spawn']['y'])>=8 for s in zone['slimes'])
    assert all(len('quest:accept:'+q['id'])<=32 for q in zone['quests'])

def open_jungle_gate(jungle):
    line=[(109,78),(121,79),JUNGLE_GATE]
    jungle['objects']=[o for o in jungle['objects'] if distance(o['x'],o['y'],[line])>max(o.get('r',0),o.get('width',0)/2,o.get('depth',0)/2)+3.5 or o['kind']=='rain_crown_temple']
    road=[list(p) for p in line]
    jungle['paths']=[p for p in jungle['paths'] if p!=road]+[road]
    jungle['portals']=[p for p in jungle['portals'] if p['id']!='tangle_worldheart_gate']
    jungle['portals'].append(dict(id='tangle_worldheart_gate',name='The Living Root',x=JUNGLE_GATE[0],y=JUNGLE_GATE[1],r=1.2,
                                 to=OUTSIDE,tx=OUT_ARRIVAL[0],ty=OUT_ARRIVAL[1],look='worldtree'))
    seen,_=fen.flood(jungle,(jungle['spawn']['x'],jungle['spawn']['y']))
    for x,y in [JUNGLE_GATE,JUNGLE_ARRIVAL]:assert seen[int(y/.5),int(x/.5)],(x,y)
    assert all(math.hypot(s['x']-JUNGLE_ARRIVAL[0],s['y']-JUNGLE_ARRIVAL[1])>=8 for s in jungle['slimes'])

def main():
    world=json.loads(MAP.read_text());assert world['zones'][21]['name']=='The Tanglecrown'
    suffix=world['zones'][OUTSIDE-1:]
    while len(suffix)>=2 and suffix[0].get('name')=='Veyrroot Canopy' and suffix[1].get('name')=='Veyrroot Heartwood':suffix=suffix[2:]
    later=suffix
    world['zones']=world['zones'][:OUTSIDE-1]
    open_jungle_gate(world['zones'][21]);world['zones']+=[outside(),inside()];world['zones']+=later
    if later and later[0].get('name')=='The Lapis Erg':
        from generate_lapis_erg import open_canopy_gate
        open_canopy_gate(world['zones'][22])
    spark_travel.ensure(world)
    MAP.write_text(json.dumps(world,indent=2)+'\n')
    items=json.loads(ITEMS.read_text())
    for key,name,sell in [('sapbeetle_resin','Sap Beetle Resin',1560),('hornet_amber','Lantern Hornet Amber',1650),
                          ('mosslemur_fur','Moss Lemur Fur',1720),('barkmimic_chip','Bark Mimic Chip',1840)]:
        if not any(i['id']==key for i in items):items.append(dict(id=key,name=name,kind='material',rarity='common',sell=sell))
    ITEMS.write_text(json.dumps(items,indent=2)+'\n')
    print('Veyrroot: outside',len(world['zones'][22]['objects']),'objects /',len(world['zones'][22]['slimes']),'enemies; inside',len(world['zones'][23]['objects']),'objects')
if __name__=='__main__':main()
