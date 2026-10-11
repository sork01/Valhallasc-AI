#!/usr/bin/env python3
"""Seeded level 85–90 Frostwake Shelf glacier with three elite territories."""
import json, math, random
from pathlib import Path
import generate_gloamfen as fen
import generate_lapis_erg as lapis
import mercenary_offers, spark_travel
from quest_gear_rewards import add_reward
ROOT=Path(__file__).resolve().parents[1]; MAP=ROOT/'world/map.txt'; ITEMS=ROOT/'world/items.txt'
XP=json.loads((ROOT/'world/levels.txt').read_text())
ZONE=26; NAME='Frostwake Shelf'; ARRIVAL=(15,137); RETURN=(7,137)
OLD_GATE=(151,31); OLD_ARRIVAL=(138,34)
ELITES={'bellmammoth','auroramanta','crevasseleviathan'}
def obj(kind,x,y,r=0,**kw):return dict(kind=kind,x=round(x,2),y=round(y,2),r=r,v=kw.pop('v',0),**kw)
def npc(key,name,role,x,y,dialogue,offers=None,buys=False,art=None):
 out=dict(id='frostwake_'+key,name=name,role=role,x=x,y=y,color='#b5daef',dialogue=dialogue,offers=offers or [],buys=buys,look=dict(skin='#d7ae91',hair='#d9e9ee',style='long',hat='hood',hatColor='#4680a1'))
 if art:out['art']=art
 return out
def kill(kind,n,label):return dict(kind='kill',target=kind,count=n,label=label)
def talk(key,label):return dict(kind='talk',target='frostwake_'+key,count=1,label=label)
def visit(key,label):return dict(kind='visit',target='frostwake_'+key,count=1,label=label)
def bring(key,n,label):return dict(kind='bring',target=key,count=n,label=label)
def quest(key,title,giver,description,objectives,level,gold,requires=None,repeatable=False,**extra):
 return add_reward(dict(id='frostwake_'+key,title=title,npc='frostwake_'+giver,description=description,objectives=objectives,level=level,rewardXp=XP[level-1]//10,rewardGold=gold,requires='frostwake_'+requires if requires else None,repeatable=repeatable,**extra))
def dist_path(x,y,paths):return lapis.dist_path(x,y,paths)
def radius(o):return lapis.radius(o)
def clear(x,y,r,objects,pad=0):return lapis.clear(x,y,r,objects,pad)
def build():
 rng=random.Random(20261017)
 # A southern supply crescent feeds an outer loop, a central crossing and three remote courts.
 south=[(7,137),(25,137),(43,127),(62,118),(82,112),(107,120),(132,111)]
 west=[(43,127),(33,105),(28,83),(38,59),(53,38),(75,27)]
 north=[(75,27),(96,23),(122,30),(139,47),(132,71)]
 east=[(132,111),(139,87),(132,71),(122,30)]
 crossing=[(28,83),(55,82),(79,81),(105,78),(132,71)]
 inner=[(62,118),(69,99),(79,81),(79,69),(88,60),(96,23)]
 paths=[south,west,north,east,crossing,inner,[(38,59),(65,55),(88,60)],[(88,60),(109,93),(132,111)]]
 objects=[obj('frostwake_signal',29,130,.7),obj('frostwake_camp',23,126,width=4,depth=3,v=0),
          obj('frostwake_camp',35,141,width=4,depth=3,v=1),obj('frostwake_camp',45,135,width=4,depth=3,v=2),
          obj('frostwake_hearth',30,135,.8),obj('frostwake_obelisk',125,21,1.6),
          obj('frostwake_fossil',32,50,1.2),obj('frostwake_frozen_pool',79,69,0,v=0),
          obj('frostwake_frozen_pool',111,100,0,v=1),obj('frostwake_mammoth_bells',48,44,1.0),
          obj('frostwake_leviathan_rib',103,35,1.1)]
 # Blue fractures lie between the roads. Their graphic spans are nonblocking to preserve reachable routes.
 for j in range(13):
  x,y=48+j*7,94+math.sin(j*.75)*7
  objects.append(obj('frostwake_crevasse',x,y,0,v=j%4))
 for j in range(11):
  x,y=73+j*5.4,49+math.cos(j*.6)*7
  objects.append(obj('frostwake_crevasse',x,y,0,v=(j+2)%4))
 for kind,count,r in [('frostwake_snow_pine',62,1.0),('frostwake_ice_spire',82,.8),('frostwake_snowdrift',115,.25),('frostwake_lantern',38,.17),('frostwake_iceflower',54,.10)]:
  placed=0
  for _ in range(100000):
   if placed==count:break
   x,y=rng.uniform(9,151),rng.uniform(9,151)
   if x<52 and y>119 or dist_path(x,y,paths)<(3.5 if r>.5 else 2.0):continue
   if math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<12 or math.hypot(x-125,y-21)<9:continue
   if kind=='frostwake_snow_pine' and y<42:continue
   if not clear(x,y,r,objects,.55):continue
   objects.append(obj(kind,x,y,r,v=rng.randrange(4)));placed+=1
  assert placed==count,(kind,placed)
 spawns=[dict(kind='bellmammoth',x=48,y=32),dict(kind='auroramanta',x=128,y=53),dict(kind='crevasseleviathan',x=102,y=20)]
 for kind,count in [('snowhare',10),('iceotter',10),('frostheron',10),('glaciercrab',10)]:
  for _ in range(count):
   for _ in range(15000):
    x,y=rng.uniform(10,150),rng.uniform(12,145)
    if x<54 and y>116 or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<14:continue
    if dist_path(x,y,paths)<3.0 or not clear(x,y,1.1,objects,1):continue
    if any(math.hypot(x-s['x'],y-s['y'])<(13 if s['kind'] in ELITES else 5) for s in spawns):continue
    spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)));break
   else:raise RuntimeError('cannot place '+kind)
 folk=[
  npc('captain','Captain Svala Northlight','Shelf captain',29,137,'The blue fissures change with the snow. Follow our lantern road and keep your eyes on the aurora.',art='frostwake_captain'),
  npc('healer','Neri Warmhands','Snow healer',18,143,'Come close to the steam and thaw your fingers before the next crossing.',[dict(id='blessing',label='Receive a healing blessing',cost=0,heal=10000),dict(id='potion',label='Buy Health Potion',cost=30,item='health_potion',tiered=True)]),
  npc('surveyor','Orin Riftline','Crevasse surveyor',43,123,'The glass-blue breaks mark old pressure lines. The far rib belongs to something still awake.',art='frostwake_surveyor'),
  npc('trader','Halla Snowpack','Sled trader',39,140,'I will buy what you bring back from the ice.',[dict(id='stew',label="Buy Traveler's Stew",cost=12,item='traveler_stew',tiered=True),dict(id='satchel',label='Buy Linen Satchel',cost=500,bag='linen_satchel')],True),
  npc('scout','Jorren Skirl','Snow scout',54,113,'Hares hide under powder. Otters dive through the clear pools. Neither belongs near the supplies.',mercenary_offers.offers()),
  npc('bellkeeper','Ylva Bellward','Mammoth bellkeeper',36,67,'When the old mammoth moves, every bronze bell on the western shelf answers.',mercenary_offers.offers(),art='frostwake_bellkeeper'),
  npc('skywatcher','Vessa Aurora','Aurora watcher',119,70,'The manta swims through curtains of light above the eastern cliff.',mercenary_offers.offers(),art='frostwake_skywatcher'),
  npc('ribkeeper','Irik Deepice','Leviathan watcher',88,37,'The shape below the crevasse can swallow a whole caravan. Bring five companions.',mercenary_offers.offers(),art='frostwake_ribkeeper'),
  npc('stone','Frostwake Meeting Stone','Gather a party · hire fighters',116,29,'The last warm lantern before the deep ice.',mercenary_offers.offers(open_=True),art='stone'),
 ]
 quests=[
  quest('welcome','Lanterns on the Shelf','captain','Meet the healer, surveyor and snow scout.',[talk('healer','Meet Neri'),talk('surveyor','Meet Orin'),talk('scout','Meet Jorren')],85,8500),
  quest('hares','Tracks under Powder','scout','Clear snow hares from the sled road.',[kill('snowhare',6,'Defeat Snow Hares')],85,9400,'welcome'),
  quest('otters','Under Clear Ice','scout','Bring warm otter pelts from the frozen pools.',[bring('iceotter_pelt',5,'Bring Ice Otter Pelts')],86,10300,'hares'),
  quest('herons','White Wing Watch','surveyor','The frost herons crowd the central crossing.',[kill('frostheron',6,'Defeat Frost Herons')],87,11200,'otters'),
  quest('crabs','Crack the Shell','surveyor','Glacier crabs have crept into the blue fissures.',[kill('glaciercrab',6,'Defeat Glacier Crabs')],88,12100,'herons'),
  quest('mammoth','The Bells Begin','bellkeeper','Three companions should face the Bell Mammoth on the western shelf.',[kill('bellmammoth',1,'Defeat the Bell Mammoth')],88,20000,'herons',group=True,recommendedPlayers=3),
  quest('manta','A Sky Beneath Ice','skywatcher','Four companions must bring down the Aurora Manta.',[kill('auroramanta',1,'Defeat the Aurora Manta')],89,25000,'crabs',group=True,recommendedPlayers=4),
  quest('leviathan','The Deep Answer','ribkeeper','Five companions must silence the Crevasse Leviathan.',[kill('crevasseleviathan',1,'Defeat the Crevasse Leviathan')],90,31000,'crabs',group=True,recommendedPlayers=5),
  quest('aurora','Where the Light Falls','skywatcher','Trace the frozen pool and the aurora obelisk.',[visit('pool','Inspect the ice pool'),visit('obelisk','Inspect the obelisk')],89,14800,'herons'),
  quest('patrol','Keep the Lanterns','captain','Patrol the road between the ice pools.',[kill('snowhare',3,'Defeat Snow Hares'),kill('glaciercrab',3,'Defeat Glacier Crabs')],85,7600,'welcome',True),
 ]
 zone=dict(name=NAME,theme='frostwake',tagline='Blue crevasses, white snowfields and aurora-lit ice',size=160,levels=[85,90],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),paths=[[[x,y] for x,y in p] for p in paths],objects=objects,slimes=spawns,npcs=folk,
           places=[dict(id='frostwake_pool',name='Pool Beneath the Ice',x=79,y=74,r=5),dict(id='frostwake_obelisk',name='Aurora Obelisk',x=119,y=25,r=5),dict(id='frostwake_rib',name='Deep Ice Rib',x=96,y=37,r=5)],quests=quests,
           city=dict(name='Frostwake Station',x0=9,x1=53,y0=117,y1=151,plaza=dict(x=29,y=136),radius=7,entry=dict(x=15,y=137)),
           portals=[dict(id='frostwake_lapis_gate',name='The Snowline',x=RETURN[0],y=RETURN[1],r=1.2,to=25,tx=OLD_ARRIVAL[0],ty=OLD_ARRIVAL[1],look='frostwake')])
 check(zone);return zone

def check(zone):
 seen,_=fen.flood(zone,ARRIVAL)
 for target in [*zone['npcs'],*zone['slimes'],*zone['portals'],*zone['places']]:
  assert seen[int(target['y']/.5),int(target['x']/.5)],f'unreachable: {target}'
 assert all(math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>=8 for s in zone['slimes'])
 assert len(zone['slimes'])==43 and len(zone['quests'])==10
 assert all(len('quest:accept:'+q['id'])<=32 for q in zone['quests'])

def open_cairn_gate(glacier):
 line=[(139,47),(139,54),(151,54)]
 glacier['objects']=[o for o in glacier['objects'] if dist_path(o['x'],o['y'],[line])>radius(o)+3.2]
 road=[[x,y] for x,y in line]
 glacier['paths']=[p for p in glacier['paths'] if p!=road]+[road]
 glacier['portals']=[p for p in glacier['portals'] if p['id']!='frostwake_cairn_gate']
 glacier['portals'].append(dict(id='frostwake_cairn_gate',name='The High Pass',x=151,y=54,r=1.2,to=27,tx=15,ty=145,look='cairnspine'))
 seen,_=fen.flood(glacier,(glacier['spawn']['x'],glacier['spawn']['y']))
 for x,y in [(151,54),(139,54)]:assert seen[int(y/.5),int(x/.5)],(x,y)
 assert all(math.hypot(s['x']-139,s['y']-54)>=8 for s in glacier['slimes'])

def main():
 world=json.loads(MAP.read_text());assert world['zones'][24]['name']=='The Lapis Erg'
 later=world['zones'][ZONE-1:]
 while later and later[0].get('name')==NAME:later=later[1:]
 world['zones']=world['zones'][:ZONE-1]
 lapis.open_glacier_gate(world['zones'][24]);world['zones'].append(build());world['zones'].extend(later)
 if any(z.get('name')=='The Cairnspine' for z in later):open_cairn_gate(world['zones'][25])
 spark_travel.ensure(world);MAP.write_text(json.dumps(world,indent=2)+'\n')
 items=json.loads(ITEMS.read_text())
 for key,name,sell in [('snowhare_fur','Snow Hare Fur',2400),('iceotter_pelt','Ice Otter Pelt',2500),('heron_feather','Frost Heron Feather',2600),('glaciercrab_shell','Glacier Crab Shell',2800),('mammoth_bell','Mammoth Bell',8500),('manta_aurora','Aurora Manta Membrane',10000),('leviathan_fang','Crevasse Leviathan Fang',13000)]:
  if not any(i['id']==key for i in items):items.append(dict(id=key,name=name,kind='material',rarity='common',sell=sell))
 ITEMS.write_text(json.dumps(items,indent=2)+'\n')
 print(f'{NAME}: {len(world["zones"][25]["objects"])} objects, 43 enemies, 10 quests')
if __name__=='__main__':main()
