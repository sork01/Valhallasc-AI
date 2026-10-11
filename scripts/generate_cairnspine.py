#!/usr/bin/env python3
"""Seeded level 90–95 Cairnspine mountain, switchbacks and sealed Thunderheart Gate."""
import json,math,random
from pathlib import Path
import generate_gloamfen as fen
import generate_frostwake as frost
import mercenary_offers,spark_travel
from quest_gear_rewards import add_reward
ROOT=Path(__file__).resolve().parents[1];MAP=ROOT/'world/map.txt';ITEMS=ROOT/'world/items.txt'
XP=json.loads((ROOT/'world/levels.txt').read_text())
ZONE=27;NAME='The Cairnspine';ARRIVAL=(15,145);RETURN=(7,145);OLD_GATE=(151,54);OLD_ARRIVAL=(139,54)
ELITES={'cairnbehemoth','whitebarktitan','stormcondor'}
def obj(kind,x,y,r=0,**kw):return dict(kind=kind,x=round(x,2),y=round(y,2),r=r,v=kw.pop('v',0),**kw)
def npc(key,name,role,x,y,dialogue,offers=None,buys=False,art=None):
 out=dict(id='cairn_'+key,name=name,role=role,x=x,y=y,color='#d4b8aa',dialogue=dialogue,offers=offers or [],buys=buys,look=dict(skin='#b88b75',hair='#d9d0c2',style='long',hat='hood',hatColor='#786b7c'))
 if art:out['art']=art
 return out
def kill(kind,n,label):return dict(kind='kill',target=kind,count=n,label=label)
def talk(key,label):return dict(kind='talk',target='cairn_'+key,count=1,label=label)
def visit(key,label):return dict(kind='visit',target='cairn_'+key,count=1,label=label)
def bring(key,n,label):return dict(kind='bring',target=key,count=n,label=label)
def quest(key,title,giver,description,objectives,level,gold,requires=None,repeatable=False,**extra):
 return add_reward(dict(id='cairn_'+key,title=title,npc='cairn_'+giver,description=description,objectives=objectives,level=level,rewardXp=XP[level-1]//10,rewardGold=gold,requires='cairn_'+requires if requires else None,repeatable=repeatable,**extra))
def dist_path(x,y,paths):return frost.dist_path(x,y,paths)
def radius(o):return frost.radius(o)
def clear(x,y,r,objects,pad=0):return frost.clear(x,y,r,objects,pad)
def build():
 rng=random.Random(20261018)
 # Four wide mountain terraces connected by a serpentine main road and shorter cliff cuts.
 lower=[(7,145),(28,145),(47,137),(65,127),(82,132),(102,119),(128,126),(147,109)]
 east=[(147,109),(133,91),(105,85),(83,94),(56,91),(32,76)]
 west=[(32,76),(49,61),(77,56),(100,67),(127,58),(147,43)]
 crown=[(147,43),(130,29),(109,25),(87,34),(65,25),(48,37)]
 cuts=[[(47,137),(43,108),(56,91)],[(82,132),(83,94),(100,67)],[(128,126),(133,91),(127,58)],[(77,56),(87,34),(109,25)]]
 paths=[lower,east,west,crown,*cuts]
 objects=[obj('cairn_thunder_gate',145,20,width=9,depth=6,place='cairn_thunder'),
          obj('cairn_watchhall',24,134,width=4,depth=3),obj('cairn_watchhall',36,151,width=4,depth=3,v=1),
          obj('cairn_watchhall',46,145,width=4,depth=3,v=2),obj('cairn_signal',30,142,.8),
          obj('cairn_stonecircle',56,69,1.0),obj('cairn_whitegrove',109,74,1.0),
          obj('cairn_eyrie',127,42,1.1),obj('cairn_boulder_altar',78,39,1.1)]
 # Broad boulder arcs flank the roads instead of filling their crossing points.
 for kind,count,r in [('cairn_boulder',110,1.3),('cairn_dead_tree',78,.9),('cairn_slate_spire',48,.8),('cairn_pebble',90,.17),('cairn_windbanner',30,.15)]:
  placed=0
  for _ in range(120000):
   if placed==count:break
   x,y=rng.uniform(10,158),rng.uniform(9,158)
   if x<55 and y>128 or dist_path(x,y,paths)<(4.0 if r>.5 else 2.5):continue
   if math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<12 or math.hypot(x-145,y-20)<15:continue
   if kind=='cairn_dead_tree' and (x>129 or y<24):continue
   if not clear(x,y,r,objects,.7):continue
   objects.append(obj(kind,x,y,r,v=rng.randrange(4)));placed+=1
  assert placed==count,(kind,placed)
 spawns=[dict(kind='cairnbehemoth',x=64,y=46),dict(kind='whitebarktitan',x=111,y=62),dict(kind='stormcondor',x=133,y=41)]
 for kind,count in [('screeferret',10),('stoneibex',10),('slateraven',10),('ridgeadder',10)]:
  for _ in range(count):
   for _ in range(15000):
    x,y=rng.uniform(10,157),rng.uniform(12,157)
    if x<58 and y>123 or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<14:continue
    if dist_path(x,y,paths)<3.2 or math.hypot(x-145,y-20)<14:continue
    if not clear(x,y,1.2,objects,1.1):continue
    if any(math.hypot(x-s['x'],y-s['y'])<(14 if s['kind'] in ELITES else 5.5) for s in spawns):continue
    spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)));break
   else:raise RuntimeError('cannot place '+kind)
 folk=[
  npc('warden','Warden Mira Cairn','Boulderwatch warden',28,145,'The mountain road bends four times before the crown. Keep the stone markers in sight.',art='cairn_warden'),
  npc('healer','Pella Warmstone','Mountain healer',17,151,'The wind takes warmth quickly. Rest beside the signal brazier.',[dict(id='blessing',label='Receive a healing blessing',cost=0,heal=10000),dict(id='potion',label='Buy Health Potion',cost=30,item='health_potion',tiered=True)]),
  npc('surveyor','Daro Slatehand','Switchback surveyor',43,131,'Every boulder here has a name. The biggest one sometimes walks.',art='cairn_surveyor'),
  npc('trader','Kessa Ridgepack','Caravan trader',38,153,'I buy what the ridge gives up and sell what keeps travelers moving.',[dict(id='stew',label="Buy Traveler's Stew",cost=12,item='traveler_stew',tiered=True),dict(id='satchel',label='Buy Linen Satchel',cost=500,bag='linen_satchel')],True),
  npc('scout','Noll Farstride','Peak scout',58,119,'Ibex favor the west slopes. The dark ravens watch the upper terraces.',mercenary_offers.offers()),
  npc('stonesinger','Edda Flintvoice','Stone singer',54,74,'The behemoth answers the old cairn bells. Bring two allies before you ring them.',mercenary_offers.offers(),art='cairn_stonesinger'),
  npc('grovekeeper','Tala Whitebark','Bare grove keeper',102,83,'The leafless giant still grows. It remembers the mountain before these roads.',mercenary_offers.offers(),art='cairn_grovekeeper'),
  npc('windseer','Oren Highwind','Summit windseer',133,53,'The condor circles the gate. Five travelers should face it before approaching the seal.',mercenary_offers.offers(),art='cairn_windseer'),
  npc('stone','Cairnspine Meeting Stone','Gather a party · hire fighters',131,30,'Gather here before the Thunderheart Gate.',mercenary_offers.offers(open_=True),art='stone'),
 ]
 quests=[
  quest('welcome','The Four Turns','warden','Meet the healer, surveyor and peak scout at Boulderwatch.',[talk('healer','Meet Pella'),talk('surveyor','Meet Daro'),talk('scout','Meet Noll')],90,9200),
  quest('ferrets','Under the Scree','scout','Ferrets have burrowed beneath the lower cairn road.',[kill('screeferret',6,'Defeat Scree Ferrets')],90,10200,'welcome'),
  quest('ibex','Horns of the Ridge','scout','Bring ibex horn from the switchbacks.',[bring('ibex_horn',5,'Bring Ibex Horns')],91,11200,'ferrets'),
  quest('ravens','Black Wings Above','surveyor','Clear slate ravens from the upper path.',[kill('slateraven',6,'Defeat Slate Ravens')],92,12200,'ibex'),
  quest('adders','Among the Stones','surveyor','Ridge adders hide among the sun-warmed boulders.',[kill('ridgeadder',6,'Defeat Ridge Adders')],93,13300,'ravens'),
  quest('behemoth','The Walking Cairn','stonesinger','Three companions should face the Cairn Behemoth.',[kill('cairnbehemoth',1,'Defeat the Cairn Behemoth')],93,22000,'ravens',group=True,recommendedPlayers=3),
  quest('titan','Roots without Leaves','grovekeeper','Four companions should confront the Whitebark Titan.',[kill('whitebarktitan',1,'Defeat the Whitebark Titan')],94,27000,'adders',group=True,recommendedPlayers=4),
  quest('condor','Storm over Stone','windseer','Five companions must bring down the Storm Condor.',[kill('stormcondor',1,'Defeat the Storm Condor')],95,33000,'adders',group=True,recommendedPlayers=5),
  quest('gate','The Thunderheart Seal','windseer','Survey the sealed summit gate and consult the Meeting Stone.',[visit('thunder','Survey the Thunderheart Gate'),talk('stone','Consult the Meeting Stone')],95,17000,'adders'),
  quest('patrol','Hold the Switchbacks','warden','Patrol the lower and upper rock roads.',[kill('screeferret',3,'Defeat Scree Ferrets'),kill('ridgeadder',3,'Defeat Ridge Adders')],90,8100,'welcome',True),
 ]
 zone=dict(name=NAME,theme='cairnspine',tagline='Slate switchbacks, giant boulders and leafless white trees',size=168,levels=[90,95],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),paths=[[[x,y] for x,y in p] for p in paths],objects=objects,slimes=spawns,npcs=folk,
           places=[dict(id='cairn_thunder',name='The Thunderheart Gate',x=134,y=26,r=5),dict(id='cairn_stones',name='Singing Cairn',x=55,y=74,r=5),dict(id='cairn_grove',name='Whitebark Grove',x=106,y=78,r=5)],quests=quests,
           city=dict(name='Boulderwatch',x0=9,x1=55,y0=127,y1=161,plaza=dict(x=30,y=145),radius=7,entry=dict(x=15,y=145)),
           futureInstance=dict(name='The Thunderheart Gate',level=95,players=5,status='sealed',x=145,y=20,description='Two mountain monoliths hold a bronze storm-ring above a sealed stair into the peak.'),
           portals=[dict(id='cairn_frostwake_gate',name='The High Pass',x=RETURN[0],y=RETURN[1],r=1.2,to=26,tx=OLD_ARRIVAL[0],ty=OLD_ARRIVAL[1],look='cairnspine')])
 check(zone);return zone

def check(zone):
 seen,_=fen.flood(zone,ARRIVAL)
 for target in [*zone['npcs'],*zone['slimes'],*zone['portals'],*zone['places']]:assert seen[int(target['y']/.5),int(target['x']/.5)],f'unreachable: {target}'
 assert all(math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>=8 for s in zone['slimes'])
 assert len(zone['slimes'])==43 and len(zone['quests'])==10
 assert all(len('quest:accept:'+q['id'])<=32 for q in zone['quests'])

def open_year_gate(mountain):
 line=[(147,109),(151,114),(157,120)]
 mountain['objects']=[o for o in mountain['objects'] if dist_path(o['x'],o['y'],[line])>radius(o)+3.2]
 road=[[x,y] for x,y in line]
 mountain['paths']=[p for p in mountain['paths'] if p!=road]+[road]
 mountain['portals']=[p for p in mountain['portals'] if p['id']!='cairn_year_gate']
 mountain['portals'].append(dict(id='cairn_year_gate',name="Year's Ascent",x=157,y=120,r=1.3,to=28,tx=24,ty=359,look='yearwheel'))
 seen,_=fen.flood(mountain,(mountain['spawn']['x'],mountain['spawn']['y']))
 for x,y in [(157,120),(147,112)]:assert seen[int(y/.5),int(x/.5)],(x,y)
 assert all(math.hypot(s['x']-147,s['y']-112)>=8 for s in mountain['slimes'])

def main():
 world=json.loads(MAP.read_text());assert world['zones'][25]['name']=='Frostwake Shelf'
 later=world['zones'][ZONE-1:]
 while later and later[0].get('name')==NAME:later=later[1:]
 world['zones']=world['zones'][:ZONE-1]
 frost.open_cairn_gate(world['zones'][25]);world['zones'].append(build());world['zones'].extend(later)
 if any(z.get('name')=='The Yearwheel' for z in later):open_year_gate(world['zones'][26])
 spark_travel.ensure(world);MAP.write_text(json.dumps(world,indent=2)+'\n')
 items=json.loads(ITEMS.read_text())
 for key,name,sell in [('screeferret_pelt','Scree Ferret Pelt',2900),('ibex_horn','Stone Ibex Horn',3000),('slate_raven_feather','Slate Raven Feather',3200),('ridgeadder_scale','Ridge Adder Scale',3400),('behemoth_heartstone','Cairn Behemoth Heartstone',10000),('whitebark_core','Whitebark Titan Core',11500),('stormcondor_plume','Storm Condor Plume',14500)]:
  if not any(i['id']==key for i in items):items.append(dict(id=key,name=name,kind='material',rarity='common',sell=sell))
 ITEMS.write_text(json.dumps(items,indent=2)+'\n')
 print(f'{NAME}: {len(world["zones"][26]["objects"])} objects, 43 enemies, 10 quests')
if __name__=='__main__':main()
