#!/usr/bin/env python3
"""Seeded level 80-85 Lapis Erg desert: three oases and a buried astrolabe."""
import json, math, random
from pathlib import Path
import generate_gloamfen as fen
import mercenary_offers, progression_quests, spark_travel
from quest_gear_rewards import add_reward
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'world/map.txt'; ITEMS=ROOT/'world/items.txt'
XP=json.loads((ROOT/'world/levels.txt').read_text())
ZONE=25; NAME='The Lapis Erg'; ARRIVAL=(14,128); RETURN=(7,128)
OLD_GATE=(119,95); OLD_ARRIVAL=(107,102)
ELITES={'dunecolossus','mirageroc'}
def obj(kind,x,y,r=0,**kw):return dict(kind=kind,x=round(x,2),y=round(y,2),r=r,v=kw.pop('v',0),**kw)
def npc(key,name,role,x,y,dialogue,offers=None,buys=False,art=None):
 out=dict(id='lapis_'+key,name=name,role=role,x=x,y=y,color='#b7e5dc',dialogue=dialogue,offers=offers or [],buys=buys,look=dict(skin='#a77250',hair='#3b4156',style='long',hat='hood',hatColor='#228c98'))
 if art:out['art']=art
 return out
def kill(kind,n,label):return dict(kind='kill',target=kind,count=n,label=label)
def talk(key,label):return dict(kind='talk',target='lapis_'+key,count=1,label=label)
def visit(key,label):return dict(kind='visit',target='lapis_'+key,count=1,label=label)
def bring(key,n,label):return dict(kind='bring',target=key,count=n,label=label)
def quest(key,title,giver,description,objectives,level,gold,requires=None,repeatable=False,**extra):
 return add_reward(dict(id='lapis_'+key,title=title,npc='lapis_'+giver,description=description,objectives=objectives,level=level,rewardXp=XP[level-1]//10,rewardGold=gold,requires='lapis_'+requires if requires else None,repeatable=repeatable,**extra))
def dist_path(x,y,paths):
 best=1e9
 for path in paths:
  for (ax,ay),(bx,by) in zip(path,path[1:]):
   dx,dy=bx-ax,by-ay;t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
   best=min(best,math.hypot(x-ax-t*dx,y-ay-t*dy))
 return best
def radius(o):return max(o.get('r',0),o.get('width',0)/2,o.get('depth',0)/2)
def clear(x,y,r,objects,pad=0):return all(math.hypot(x-o['x'],y-o['y'])>r+radius(o)+pad for o in objects)
def build():
 rng=random.Random(20261016)
 # The route bends around three water basins and loops along a ridge of blue salt.
 main=[(7,128),(27,128),(42,113),(56,99),(75,90),(91,73),(111,57),(130,43),(139,29)]
 west=[(42,113),(29,92),(34,68),(49,55),(74,45),(91,73)]
 east=[(56,99),(82,116),(107,110),(129,92),(111,57)]
 north=[(49,55),(65,29),(92,21),(118,22),(139,29)]
 paths=[main,west,east,north,[(34,68),(54,78),(75,90)],[(107,110),(105,81),(91,73)],[(74,45),(103,41),(118,22)]]
 objects=[obj('lapis_astrolabe',140,23,r=0,place='lapis_vault',open=True),
          obj('lapis_oasis',37,116,0,v=0),obj('lapis_oasis',67,71,0,v=1),obj('lapis_oasis',116,95,0,v=2),
          obj('lapis_caravan_tent',22,119,width=4,depth=3,v=0),obj('lapis_caravan_tent',33,137,width=4,depth=3,v=1),
          obj('lapis_caravan_tent',43,128,width=4,depth=3,v=2),obj('lapis_well',29,126,1),
          obj('lapis_mirror',62,69,1.2),obj('lapis_roc_nest',123,84,1.4),obj('lapis_salt_arch',99,35,1.3)]
 # Leave wide, sunlit routes; vary sparse silhouettes between ochre dunes and water.
 for kind,count,r in [('lapis_date_palm',78,1.05),('lapis_sandstone',65,.9),('lapis_salt_spire',38,.8),
                      ('lapis_dunegrass',96,.18),('lapis_silk_flag',32,.13),('lapis_blue_flower',60,.08)]:
  placed=0
  for _ in range(100000):
   if placed==count:break
   x,y=rng.uniform(9,151),rng.uniform(9,151)
   if x<50 and y>108 or dist_path(x,y,paths)<(3.7 if r>.5 else 2.4):continue
   if math.hypot(x-140,y-23)<13 or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<11:continue
   # More palms close to water, more stone in dry reaches.
   water=min(math.hypot(x-a,y-b) for a,b in [(37,116),(67,71),(116,95)])
   if kind=='lapis_date_palm' and water>34:continue
   if kind=='lapis_salt_spire' and water<15:continue
   if not clear(x,y,r,objects,.6):continue
   objects.append(obj(kind,x,y,r,v=rng.randrange(4)));placed+=1
  assert placed==count,(kind,placed)
 spawns=[dict(kind='dunecolossus',x=69,y=37),dict(kind='mirageroc',x=125,y=84)]
 for kind,count,lo,hi in [('sandhopper',10,18,137),('dunefennec',10,15,135),('glassscorpion',10,15,125),('sunvulture',10,15,125)]:
  for _ in range(count):
   for attempt in range(15000):
    x,y=rng.uniform(10,151),rng.uniform(lo,hi)
    if x<51 and y>107 or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<13:continue
    if dist_path(x,y,paths)<3.1 or math.hypot(x-140,y-23)<14:continue
    if not clear(x,y,1.2,objects,1.1):continue
    if any(math.hypot(x-s['x'],y-s['y'])<(13 if s['kind'] in ELITES else 5.5) for s in spawns):continue
    spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)));break
   else:raise RuntimeError('cannot place '+kind)
 folk=[
  npc('keeper','Sahra Bluewell','Oasis keeper',27,131,'The Lapis Erg has three waters. Follow the brass markers; the dunes move, but the wells do not.',art='lapis_keeper'),
  npc('healer','Nima Reedglass','Water healer',17,135,'Rest by the date palms. I keep clean water and tinctures for travelers.',[dict(id='blessing',label='Receive a healing blessing',cost=0,heal=10000),dict(id='potion',label='Buy Health Potion',cost=30,item='health_potion',tiered=True)]),
  npc('cartographer','Ivo Starfold','Desert cartographer',40,122,'The buried astrolabe charts the sky below us. Its iris now opens for prepared parties.',art='lapis_cartographer'),
  npc('trader','Basma Silk','Caravan trader',36,136,'Lapis dye, dates and dune maps. I will buy what the desert gives you.',[dict(id='stew',label="Buy Traveler's Stew",cost=12,item='traveler_stew',tiered=True),dict(id='satchel',label='Buy Linen Satchel',cost=500,bag='linen_satchel')],True),
  npc('scout','Tarek Windstep','Dune scout',51,105,'The fennecs cross the north flats at dusk. The scorpions favor the glassy salt.',mercenary_offers.offers()),
  npc('warden','Ruma Sunward','Oasis warden',77,86,'The stone giant stirs beyond the mirrored pool. Bring two friends before you face it.',mercenary_offers.offers(),art='lapis_warden'),
  npc('seer','Laleh of the Lens','Astrolabe seer',127,45,'The Sunken Astrolabe is open beneath its turning lenses. Bring five travelers.',art='lapis_seer'),
  npc('stone','Lapis Meeting Stone','Gather a party · hire fighters',130,38,'Gather here before descending into the Sunken Astrolabe.',mercenary_offers.offers(open_=True),art='stone'),
 ]
 quests=[
  quest('welcome','Three Waters','keeper','Meet the healer, cartographer and scout at Azure Wells.',[talk('healer','Meet Nima'),talk('cartographer','Meet Ivo'),talk('scout','Meet Tarek')],80,8000),
  quest('hoppers','Dune Dancers','scout','Sandhoppers have taken the low caravan track.',[kill('sandhopper',6,'Defeat Sandhoppers')],80,9200,'welcome'),
  quest('fennecs','Under the Date Palms','scout','Gather fennec fur for the night shelter.',[bring('fennec_fur',5,'Bring Fennec Fur')],81,10000,'hoppers'),
  quest('scorpions','The Blue Salt','cartographer','Clear glass scorpions from the route to the mirrored oasis.',[kill('glassscorpion',6,'Defeat Glass Scorpions')],82,10900,'fennecs'),
  quest('vultures','Wings over Water','keeper','Keep sun vultures from the eastern water basin.',[kill('sunvulture',6,'Defeat Sun Vultures')],83,11800,'scorpions'),
  quest('colossus','The Walking Dune','warden','Three companions should confront the dune colossus beyond the mirrored pool.',[kill('dunecolossus',1,'Defeat the Dune Colossus')],84,19000,'scorpions',group=True,recommendedPlayers=3),
  quest('roc','The Mirage Roc','seer','Five companions must face the roc above the eastern oasis.',[kill('mirageroc',1,'Defeat the Mirage Roc')],85,26000,'vultures',group=True,recommendedPlayers=5),
  quest('astrolabe','The Buried Sky','seer','Inspect the open astrolabe and consult the Meeting Stone.',[visit('vault','Inspect the Sunken Astrolabe'),talk('stone','Consult the Meeting Stone')],85,14000,'vultures'),
  quest('astro_trials','The Meridian Wardens','seer','Defeat the first two wardens and the mechanisms that protect the Sunken Astrolabe.',[kill('astro_warden',1,'Defeat the Meridian Warden'),kill('astro_navigator',1,'Defeat the Lost Navigator'),kill('astro_gearling',3,'Defeat Brass Gearlings')],85,23000,'astrolabe',group=True,recommendedPlayers=5),
  quest('astro_final','Axis of the Buried Sky','seer','Destroy the buried axis and bring its starlight back to Azure Wells.',[kill('astro_axis',1,'Defeat the Axis of the Buried Sky')],85,36000,'astro_trials',group=True,recommendedPlayers=5,rewardItem='accessory_amber_l85_blue'),
  quest('patrol','Follow the Blue Wells','keeper','Patrol the desert routes between the basins.',[kill('sandhopper',3,'Defeat Sandhoppers'),kill('glassscorpion',3,'Defeat Glass Scorpions')],80,7000,'welcome',True),
 ]
 zone=dict(name=NAME,theme='lapiserg',tagline='Ochre dunes, turquoise oases, date palms and a sunken brass astrolabe',size=160,levels=[80,85],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),paths=[[[x,y] for x,y in path] for path in paths],objects=objects,slimes=spawns,npcs=folk,
           places=[dict(id='lapis_vault',name='The Sunken Astrolabe',x=132,y=29,r=5),dict(id='lapis_mirror',name='Mirrored Oasis',x=67,y=72,r=5),dict(id='lapis_east',name='Eastern Oasis',x=112,y=92,r=5)],quests=quests,
           city=dict(name='Azure Wells',x0=10,x1=50,y0=108,y1=148,plaza=dict(x=29,y=128),radius=6,entry=dict(x=14,y=128)),
           futureInstance=dict(name='The Sunken Astrolabe',level=85,players=5,status='open',x=140,y=23,description='A vast brass lens rises from the dune; a spiral stair descends beneath its open iris.'),
           portals=[dict(id='lapis_canopy_gate',name='The Sunroad',x=RETURN[0],y=RETURN[1],r=1.2,to=23,tx=OLD_ARRIVAL[0],ty=OLD_ARRIVAL[1],look='lapiserg'),dict(id='lapis_astrolabe_gate',name='The Sunken Astrolabe',x=140,y=26,r=1.2,to=34,tx=48,ty=82,look='sunken_astrolabe')])
 check(zone);return zone

def check(zone):
 seen,_=fen.flood(zone,ARRIVAL)
 for target in [*zone['npcs'],*zone['slimes'],*zone['portals'],*zone['places']]:
  assert seen[int(target['y']/.5),int(target['x']/.5)],f'unreachable: {target}'
 assert all(math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>=8 for s in zone['slimes'])
 assert len(zone['slimes'])==42 and len(zone['quests'])==11
 assert all(len('quest:accept:'+q['id'])<=32 for q in zone['quests'])

def open_canopy_gate(canopy):
 line=[(92,100),(107,102),OLD_GATE]
 canopy['objects']=[o for o in canopy['objects'] if dist_path(o['x'],o['y'],[line])>radius(o)+3.5 or o['kind']=='worldheart_trunk']
 road=[[x,y] for x,y in line]
 canopy['paths']=[p for p in canopy['paths'] if p!=road]+[road]
 canopy['portals']=[p for p in canopy['portals'] if p['id']!='canopy_lapis_gate']
 canopy['portals'].append(dict(id='canopy_lapis_gate',name='The Sunroad',x=OLD_GATE[0],y=OLD_GATE[1],r=1.2,to=ZONE,tx=ARRIVAL[0],ty=ARRIVAL[1],look='lapiserg'))
 seen,_=fen.flood(canopy,(canopy['spawn']['x'],canopy['spawn']['y']))
 for x,y in [OLD_GATE,OLD_ARRIVAL]:assert seen[int(y/.5),int(x/.5)],(x,y)
 assert all(math.hypot(s['x']-OLD_ARRIVAL[0],s['y']-OLD_ARRIVAL[1])>=8 for s in canopy['slimes'])

def open_glacier_gate(desert):
 line=[(139,29),(138,34),(151,31)]
 desert['objects']=[o for o in desert['objects'] if dist_path(o['x'],o['y'],[line])>radius(o)+3.1 or o['kind']=='lapis_astrolabe']
 road=[[x,y] for x,y in line]
 desert['paths']=[p for p in desert['paths'] if p!=road]+[road]
 desert['portals']=[p for p in desert['portals'] if p['id']!='lapis_frostwake_gate']
 desert['portals'].append(dict(id='lapis_frostwake_gate',name='The Snowline',x=151,y=31,r=1.2,to=26,tx=15,ty=137,look='frostwake'))
 seen,_=fen.flood(desert,(desert['spawn']['x'],desert['spawn']['y']))
 for x,y in [(151,31),(138,34)]:assert seen[int(y/.5),int(x/.5)],(x,y)
 assert all(math.hypot(s['x']-138,s['y']-34)>=8 for s in desert['slimes'])

def main():
 world=json.loads(MAP.read_text());assert world['zones'][22]['name']=='Veyrroot Canopy'
 later=world['zones'][ZONE-1:]
 while later and later[0].get('name')==NAME:later=later[1:]
 previous=world['zones'][ZONE-1]
 world['zones']=world['zones'][:ZONE-1]
 zone=build();progression_quests.keep_released_rewards_and_route_quest(previous,zone)
 open_canopy_gate(world['zones'][22]);world['zones'].append(zone);world['zones'].extend(later)
 if any(z.get('name')=='Frostwake Shelf' for z in later):open_glacier_gate(world['zones'][24])
 spark_travel.ensure(world);MAP.write_text(json.dumps(world,indent=2)+'\n')
 items=json.loads(ITEMS.read_text())
 for key,name,sell in [('sandhopper_chitin','Sandhopper Chitin',1900),('fennec_fur','Dune Fennec Fur',2100),('scorpion_glass','Glass Scorpion Shard',2200),('vulture_quill','Sun Vulture Quill',2300),('colossus_core','Dune Colossus Core',7800),('roc_plume','Mirage Roc Plume',9200)]:
  if not any(i['id']==key for i in items):items.append(dict(id=key,name=name,kind='material',rarity='common',sell=sell))
 ITEMS.write_text(json.dumps(items,indent=2)+'\n')
 print(f'{NAME}: {len(world["zones"][24]["objects"])} objects, 42 enemies, {len(world["zones"][24]["quests"])} quests')
if __name__=='__main__':main()
