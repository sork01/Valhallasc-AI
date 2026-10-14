#!/usr/bin/env python3
"""Seeded level 75–80 jungle basin after The Ribbonwild."""
import json, math, random
from pathlib import Path
import generate_gloamfen as fen
import mercenary_offers, progression_quests, spark_travel
from quest_gear_rewards import add_reward
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'world/map.txt'; ITEMS=ROOT/'world/items.txt'
XP=json.loads((ROOT/'world/levels.txt').read_text())
ZONE=22; NAME='The Tanglecrown'; ARRIVAL=(14,111); RETURN=(7,111)
OLD_GATE=(129,117); OLD_ARRIVAL=(120,113)
def obj(kind,x,y,r=0,**extra):return dict(kind=kind,x=round(x,2),y=round(y,2),r=r,v=extra.pop('v',0),**extra)
def npc(key,name,role,x,y,dialogue,offers=None,buys=False):
 return dict(id='tangle_'+key,name=name,role=role,x=x,y=y,color='#d6f1a2',dialogue=dialogue,offers=offers or [],buys=buys,look=dict(skin='#a96c4e',hair='#263d31',style='long',hat='hood',hatColor='#3d9d74'))
def kill(kind,n,label):return dict(kind='kill',target=kind,count=n,label=label)
def talk(key,label):return dict(kind='talk',target='tangle_'+key,count=1,label=label)
def visit(key,label):return dict(kind='visit',target='tangle_'+key,count=1,label=label)
def bring(key,n,label):return dict(kind='bring',target=key,count=n,label=label)
def quest(key,title,giver,description,objectives,level,gold,requires=None,repeatable=False,**extra):
 return add_reward(dict(id='tangle_'+key,title=title,npc='tangle_'+giver,description=description,objectives=objectives,level=level,rewardXp=XP[level-1]//10,rewardGold=gold,requires='tangle_'+requires if requires else None,repeatable=repeatable,**extra))
def people():
 folk=[
 npc('warden','Asha Banyan','Landing warden',30,108,'The rain changes every channel. Follow the raised roots toward the crown, and keep the old stone dry.'),
 npc('medic','Nilo Reed','Jungle healer',22,120,'The broad leaves keep medicine cool even at noon.',[dict(id='blessing',label='Receive a healing blessing',cost=0,heal=10000),dict(id='buy_health_potion',label='Buy Health Potion',cost=30,item='health_potion',tiered=True)]),
 npc('botanist','Tavi Moss','Orchid botanist',40,116,'The orchid mantises mimic flowers; the gliders carry pollen above the river.'),
 npc('trader','Koro Flint','Landing provisions',17,100,'I buy field finds and keep the boardwalk supplied.',[dict(id='stew',label="Buy Traveler's Stew",cost=12,item='traveler_stew',tiered=True),dict(id='satchel',label='Buy Linen Satchel',cost=500,bag='linen_satchel')],True),
 npc('tracker','Mara Vines','Canopy tracker',42,96,'The jaguar circles the high terrace. Listen for silence before it springs.',mercenary_offers.offers()),
 npc('scholar','Oru Slate','Temple scholar',103,39,'The Rain Crown is silent. Record its guardians before anyone opens the temple.'),
 npc('stone','Banyan Meeting Stone','Gather a party · hire fighters',92,48,'Gather companions for the jungle elites. The temple itself remains sealed.',mercenary_offers.offers(open_=True)),
 ]
 folk[0]['art']='tangle_warden';folk[5]['art']='tangle_scholar';folk[-1]['art']='stone'
 quests=[
 quest('welcome','The Landing Crew','warden','Meet the healer, botanist and tracker at Banyan Landing.',[talk('medic','Meet Nilo'),talk('botanist','Meet Tavi'),talk('tracker','Meet Mara')],75,7500),
 quest('mantises','Living Orchids','botanist','Clear the flower mimics from the low terraces.',[kill('orchidmantis',6,'Defeat Orchid Mantises')],75,8200,'welcome'),
 quest('gliders','Above the Green','botanist','Gather membrane from canopy gliders for shelter sails.',[bring('glider_membrane',5,'Bring Glider Membrane')],76,8800,'mantises'),
 quest('caimans','The Blackwater Edge','tracker','Drive caimans away from the boardwalk crossings.',[kill('poolcaiman',6,'Defeat Pool Caimans')],77,9400,'gliders'),
 quest('drums','When the Canopy Beats','warden','The drum gorillas shake fruit onto the landing.',[kill('drumgorilla',6,'Defeat Drum Gorillas')],78,10000,'caimans'),
 quest('anaconda','Coils of Jade','botanist','Three companions should confront the giant anaconda in the lower basin.',[kill('jadeanaconda',1,'Defeat the Jade Anaconda')],79,16000,'caimans',group=True,recommendedPlayers=3),
 quest('jaguar','The Crown Jaguar','tracker','Five companions are needed against the predator atop the high terrace.',[kill('crownjaguar',1,'Defeat the Crown Jaguar')],80,21000,'drums',group=True,recommendedPlayers=5),
 quest('temple','Eyes of the Rain Crown','scholar','Survey the sealed temple stairs and consult the Meeting Stone.',[visit('temple','Inspect the Rain Crown Temple'),talk('stone','Consult the Meeting Stone')],80,12000,'drums'),
 quest('crown_trials','The Rainbound Courts','scholar','Record the three temple guardians in a private expedition.',
       [kill('rain_crown_droplet',3,'Defeat Crowned Droplets'),kill('rain_crown_oracle',3,'Defeat Jade Rain Oracles'),kill('rain_crown_guard',3,'Defeat Monsoon Guards')],
       80,16500,'temple',group=True,recommendedPlayers=5),
 quest('crown_final','The Crown Remembers','scholar','Defeat the floodgate keeper, the sibyl and the Rain Crown in one private temple.',
       [kill('rain_crown_gatekeeper',1,'Defeat the Floodgate Keeper'),kill('rain_crown_sibyl',1,'Defeat the Rain Sibyl'),kill('rain_crown_sovereign',1,'Defeat the Rain Crown')],
       80,29000,'crown_trials',group=True,recommendedPlayers=5,rewardItem='accessory_amber_l80_blue'),
 quest('patrol','Keep the Boardwalks Safe','warden','Patrol the canopy and basin paths for travelers.',[kill('orchidmantis',3,'Defeat Orchid Mantises'),kill('poolcaiman',3,'Defeat Pool Caimans')],75,6400,'welcome',True),
 ]
 return folk,quests
def dist_path(x,y,paths):
 best=1e9
 for path in paths:
  for (ax,ay),(bx,by) in zip(path,path[1:]):
   dx,dy=bx-ax,by-ay;t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
   best=min(best,math.hypot(x-ax-t*dx,y-ay-t*dy))
 return best
def build():
 rng=random.Random(20261012)
 # A branching delta: the northern and eastern loops reconnect to the main ridge.
 main=[(7,111),(29,111),(43,98),(61,84),(75,68),(91,49),(110,29),(117,24)]
 west=[(43,98),(25,82),(28,58),(47,43),(75,68)]
 east=[(61,84),(87,96),(110,78),(103,59),(91,49)]
 north=[(47,43),(72,27),(93,29),(110,29)]
 paths=[main,west,east,north,[(25,82),(52,72),(75,68)],[(87,96),(92,48)]]
 objects=[
  obj('rain_crown_temple',120,23,open=True,place='tangle_temple'),
  obj('banyan_lodge',16,91,width=5,depth=4,v=0),obj('banyan_lodge',41,124,width=5,depth=4,v=1),
  obj('boardwalk_stall',15,121,width=3,depth=2,v=0),obj('boardwalk_stall',40,105,width=3,depth=2,v=1),
  obj('root_bridge',63,83,r=.7),obj('root_bridge',91,49,r=.7),
  obj('jade_pool',52,56,r=1.6,place='tangle_anaconda_pool'),
  obj('jaguar_totem',111,75,r=.8,place='tangle_jaguar_terrace'),
 ]
 # Water follows two braided channels. Trails leave dry ford gaps at crossings.
 for channel in range(2):
  for i in range(118):
   x=19+i*.93;y=(54+18*math.sin(x*.058)+channel*24+5*math.sin(x*.15))
   if 6<x<139 and 5<y<139 and dist_path(x,y,paths)>5.2 and not (x<52 and y>89):
    if all(math.hypot(x-o['x'],y-o['y'])>max(o['r'],o.get('width',0)/2,o.get('depth',0)/2)+1.6 for o in objects):
     objects.append(obj('jungle_water',x,y,.95,v=channel))
 # Real trunk and canopy silhouettes, spaced enough to leave all four loops playable.
 for kind,count,radius in [('kapok_tree',85,1.45),('strangler_fig',56,1.2),('banana_palm',72,.95),('hanging_vines',55,.18),('giant_fern',60,.42),('orchid_cluster',70,.08),('glow_mushroom',25,.08)]:
  placed=0
  for _ in range(120000):
   if placed==count:break
   x,y=rng.uniform(9,134),rng.uniform(8,132)
   if x<49 and y>91 or dist_path(x,y,paths)<(4.7 if radius>.9 else 3.2):continue
   if math.hypot(x-120,y-23)<15 or math.hypot(x-53,y-57)<11 or math.hypot(x-110,y-76)<12:continue
   if any(math.hypot(x-o['x'],y-o['y'])<radius+max(o['r'],o.get('width',0)/2,o.get('depth',0)/2)+.45 for o in objects):continue
   objects.append(obj(kind,x,y,radius,v=rng.randrange(4)));placed+=1
  assert placed==count,(kind,placed)
 for kind,x,y in [('kapok_tree',11,91),('banana_palm',47,109),('strangler_fig',49,127),('banana_palm',33,88)]:
  if dist_path(x,y,paths)>4 and all(math.hypot(x-o['x'],y-o['y'])>max(o['r'],o.get('width',0)/2,o.get('depth',0)/2)+1.7 for o in objects):objects.append(obj(kind,x,y,1.2))
 spawns=[dict(kind='jadeanaconda',x=57,y=57),dict(kind='crownjaguar',x=106,y=76)]
 for kind,count,lo,hi in [('orchidmantis',10,18,119),('canopyglider',10,13,112),('poolcaiman',10,40,127),('drumgorilla',10,25,122)]:
  for _ in range(count):
   for _attempt in range(16000):
    x,y=rng.uniform(10,134),rng.uniform(lo,hi)
    if x<50 and y>89 or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<12:continue
    if dist_path(x,y,paths)<3.2 or math.hypot(x-120,y-23)<15:continue
    if any(math.hypot(x-s['x'],y-s['y'])<(14 if s['kind'] in ('jadeanaconda','crownjaguar') else 6) for s in spawns):continue
    if any(math.hypot(x-o['x'],y-o['y'])<max(o['r'],o.get('width',0)/2,o.get('depth',0)/2)+1.8 for o in objects):continue
    spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)));break
   else:raise RuntimeError('cannot place '+kind)
 folk,quests=people()
 zone=dict(name=NAME,theme='tanglecrown',tagline='A rain-bright jungle of giant roots, braided waterways and an open crown temple',size=144,levels=[75,80],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),paths=[[[x,y] for x,y in path] for path in paths],objects=objects,slimes=spawns,npcs=folk,places=[dict(id='tangle_temple',name='Temple of the Rain Crown',x=112,y=26,r=4),dict(id='tangle_anaconda_pool',name='Jade Basin',x=53,y=57,r=5),dict(id='tangle_jaguar_terrace',name='High Jaguar Terrace',x=111,y=76,r=5)],quests=quests,city=dict(name='Banyan Landing',x0=9,x1=49,y0=90,y1=130,plaza=dict(x=29,y=110),radius=5,entry=dict(x=14,y=111)),futureInstance=dict(name='Temple of the Rain Crown',level=80,players=5,status='open',x=120,y=23,description='The jade eyes open into a private level-80 temple.'),portals=[dict(id='tangle_ribbon_gate',name='The Rootway',x=RETURN[0],y=RETURN[1],r=1.2,to=21,tx=OLD_ARRIVAL[0],ty=OLD_ARRIVAL[1],look='tanglecrown'),dict(id='tangle_rain_gate',name='Temple of the Rain Crown',x=117,y=24,r=1.2,to=32,tx=48,ty=83,look='rain_crown')])
 check(zone);return zone
def check(zone):
 seen,_=fen.flood(zone,ARRIVAL)
 for target in [*zone['npcs'],*zone['slimes'],*zone['portals'],dict(x=112,y=26),dict(x=72,y=27),dict(x=87,y=96)]:
  assert seen[int(target['y']/.5),int(target['x']/.5)],f'unreachable: {target}'
 assert all(math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>=8 for s in zone['slimes'])
 assert len(zone['slimes'])==42 and len(zone['quests'])==11
 assert all(len('quest:accept:'+q['id'])<=32 for q in zone['quests'])
def open_ribbon_gate(ribbon):
 line=[(97,93),(110,108),OLD_GATE]
 ribbon['objects']=[o for o in ribbon['objects'] if dist_path(o['x'],o['y'],[line])>max(o.get('r',0),o.get('width',0)/2,o.get('depth',0)/2)+3.2 or o['kind']=='grand_pavilion_gate']
 road=[[x,y] for x,y in line]
 ribbon['paths']=[p for p in ribbon['paths'] if p!=road]+[road]
 ribbon['portals']=[p for p in ribbon['portals'] if p['id']!='ribbon_tangle_gate']
 ribbon['portals'].append(dict(id='ribbon_tangle_gate',name='The Rootway',x=OLD_GATE[0],y=OLD_GATE[1],r=1.2,to=ZONE,tx=ARRIVAL[0],ty=ARRIVAL[1],look='tanglecrown'))
 seen,_=fen.flood(ribbon,(ribbon['spawn']['x'],ribbon['spawn']['y']))
 for x,y in [OLD_GATE,OLD_ARRIVAL]:assert seen[int(y/.5),int(x/.5)],(x,y)
 assert all(math.hypot(s['x']-OLD_ARRIVAL[0],s['y']-OLD_ARRIVAL[1])>=8 for s in ribbon['slimes'])
def main():
 world=json.loads(MAP.read_text());assert world['zones'][20]['name']=='The Ribbonwild'
 previous=world['zones'][ZONE-1]
 later=world['zones'][ZONE:];world['zones']=world['zones'][:ZONE-1]
 zone=build();progression_quests.keep_released_rewards_and_route_quest(previous,zone)
 open_ribbon_gate(world['zones'][20]);world['zones'].append(zone);world['zones'].extend(later)
 if later and later[0].get('name')=='Veyrroot Canopy':
  from generate_worldheart import open_jungle_gate
  open_jungle_gate(world['zones'][21])
 spark_travel.ensure(world);MAP.write_text(json.dumps(world,indent=2)+'\n')
 items=json.loads(ITEMS.read_text())
 for key,name,sell in [('mantis_petals','Orchid Mantis Petals',1180),('glider_membrane','Canopy Glider Membrane',1260),('caiman_scale','Blackwater Caiman Scale',1350),('gorilla_drumskin','Drum Gorilla Hide',1480),('anaconda_jade','Jade Anaconda Scale',5600),('jaguar_crown','Crown Jaguar Crest',7200)]:
  if not any(i['id']==key for i in items):items.append(dict(id=key,name=name,kind='material',rarity='common',sell=sell))
 ITEMS.write_text(json.dumps(items,indent=2)+'\n')
 print(f'{NAME}: {len(world["zones"][21]["objects"])} objects, 42 enemies, 11 base quests')
if __name__=='__main__':main()
