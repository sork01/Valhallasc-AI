#!/usr/bin/env python3
"""Seeded 400-square end zone: four connected seasons, hubs, elite courts and sealed doors."""
import json, math, random
from pathlib import Path
import generate_gloamfen as fen
import generate_cairnspine as cairn
import mercenary_offers, progression_quests, spark_travel
from quest_gear_rewards import add_reward
ROOT=Path(__file__).resolve().parents[1];MAP=ROOT/'world/map.txt';ITEMS=ROOT/'world/items.txt'
XP=json.loads((ROOT/'world/levels.txt').read_text())
ZONE=28;NAME='The Yearwheel';SIZE=400;ARRIVAL=(24,359);RETURN=(11,359)
SEASONS={
 'sp':dict(name='Springmere',hub=(76,324),entrance=(48,229),door='The Blooming Labyrinth',ordinary='brooknewt',elites=['bloomtortoise','petalchimera','rainseraph'],elite_pos=[(53,274),(133,258),(157,336)],gate=(59,238),level=95,leader='Ilya Greenwake',givers=['Fenrik of the Roots','Vessa Petalglass','Aurel Rainhand'],medic='Marna Wellspring',trader='Kip Budbasket'),
 'su':dict(name='Solhaven',hub=(320,316),entrance=(352,248),door='The Solar Crucible',ordinary='sundarter',elites=['glasslion','sunwheel','firephoenix'],elite_pos=[(240,264),(293,242),(359,344)],gate=(342,258),level=96,leader='Sera Brightward',givers=['Tal Sunweaver','Oda of the Brass','Pax Firefeather'],medic='Nima Daywell',trader='Rook Goldgrain'),
 'au':dict(name='Harvestwatch',hub=(321,78),entrance=(352,151),door='The Amber Archive',ordinary='acornmimic',elites=['lanternowl','harvestreaper','ambermantis'],elite_pos=[(250,121),(291,177),(362,54)],gate=(341,160),level=97,leader='Haldan Coppersong',givers=['Mira Nightlantern','Tov the Thresher','Elen Amberline'],medic='Bera Hearthleaf',trader='Cori Caskwood'),
 'wi':dict(name='Rimehold',hub=(78,78),entrance=(47,150),door='The Silent Solstice',ordinary='snowstoat',elites=['rimesaber','snowgiant','longnightwyrm'],elite_pos=[(51,122),(124,154),(157,52)],gate=(58,159),level=97,leader='Ysra Snowglass',givers=['Viggo Icefang','Hessa Farfrost','Rune Nightstar'],medic='Tilda Warmmitt',trader='Sven Blueflask'),
}
MATERIALS=[('brooknewt','newt_ribbon','Brook Newt Ribbon',3600),('sundarter','sundarter_scale','Sundarter Scale',3800),('acornmimic','amber_acorn','Amber Acorn',4000),('snowstoat','stoat_silverfur','Silver Stoat Fur',4200),
 ('bloomtortoise','bloom_shell','Bloom Tortoise Shell',14500),('petalchimera','chimera_petal','Chimera Petal',15500),('rainseraph','seraph_rainfeather','Seraph Rainfeather',17000),
 ('glasslion','glasslion_mane','Glass Lion Mane',15500),('sunwheel','sunwheel_cog','Sunwheel Cog',17000),('firephoenix','phoenix_ember','Phoenix Ember',18500),
 ('lanternowl','lanternowl_eye','Lantern Owl Eye',16500),('harvestreaper','reaper_scythe_shard','Reaper Scythe Shard',18000),('ambermantis','amber_mantis_claw','Amber Mantis Claw',20000),
 ('rimesaber','rimesaber_fang','Rimesaber Fang',16500),('snowgiant','snowgiant_heart','Snow Giant Heart',18000),('longnightwyrm','longnight_scale','Longnight Scale',20000)]
def xp(level):return (XP[level-1] if level<=len(XP) else XP[-1]+(level-len(XP))*2300)//10
def obj(kind,x,y,r=0,**kw):return dict(kind=kind,x=round(x,2),y=round(y,2),r=r,v=kw.pop('v',0),**kw)
def npc(id_,name,role,x,y,dialogue,offers=None,buys=False,art=None,season=None):
 color={'sp':'#78b48a','su':'#e6b45c','au':'#bb835e','wi':'#9dbbd0'}[season]
 out=dict(id=id_,name=name,role=role,x=x,y=y,color=color,dialogue=dialogue,offers=offers or [],buys=buys,look=dict(skin='#c99d78',hair=color,style='long',hat='hood',hatColor=color))
 if art:out['art']=art
 return out
def quest(id_,title,giver,description,objectives,level,gold,requires=None,repeatable=False,**extra):
 return add_reward(dict(id=id_,title=title,npc=giver,description=description,objectives=objectives,level=level,rewardXp=xp(level),rewardGold=gold,requires=requires,repeatable=repeatable,**extra))
def talk(id_,label):return dict(kind='talk',target=id_,count=1,label=label)
def visit(id_,label):return dict(kind='visit',target=id_,count=1,label=label)
def kill(kind,n,label):return dict(kind='kill',target=kind,count=n,label=label)
def dist_path(x,y,paths):return cairn.dist_path(x,y,paths)
def clear(x,y,r,objects,pad=0):return cairn.clear(x,y,r,objects,pad)
def season_of(x,y):
 return 'sp' if x<200 and y>=200 else 'su' if x>=200 and y>=200 else 'au' if x>=200 else 'wi'
def build():
 rng=random.Random(20261019)
 # Interwoven hub loops and four spokes meet at the open Equinox Crossing.
 spring=[(11,359),(24,359),(76,324),(60,265),(80,228),(143,245),(166,313),(76,324)]
 summer=[(166,313),(219,333),(320,316),(358,270),(328,227),(263,241),(219,333)]
 autumn=[(328,227),(349,189),(321,78),(351,119),(320,164),(255,168),(321,78)]
 winter=[(255,168),(196,159),(155,70),(78,78),(46,122),(78,172),(150,163),(78,78)]
 spokes=[[(76,324),(146,270),(200,200)],[(320,316),(273,263),(200,200)],[(321,78),(265,141),(200,200)],[(78,78),(140,144),(200,200)]]
 rim=[[(80,228),(145,201),(200,200)],[(328,227),(267,205),(200,200)],[(255,168),(220,122),(200,200)],[(78,172),(136,195),(200,200)]]
 paths=[spring,summer,autumn,winter,*spokes,*rim]
 entrance_kind={'sp':'year_bloom_gate','su':'year_solar_gate','au':'year_amber_gate','wi':'year_solstice_gate'}
 props={'sp':[('year_bloomtree',100,1.0),('year_spring_pool',32,0),('year_bluebell',95,.12),('year_fern',72,.3)],
        'su':[('year_sunpine',98,1.05),('year_sunflower',93,.16),('year_goldenstone',63,.8),('year_citrus',40,.22)],
        'au':[('year_amberoak',100,1.0),('year_leafpile',104,.18),('year_mushroom',63,.22),('year_copperstone',48,.8)],
        'wi':[('year_frostbirch',100,.9),('year_snowdrift',104,.2),('year_iceobelisk',65,.8),('year_holly',42,.25)]}
 objects=[obj('year_axle',200,200,0)]
 for i,(key,s) in enumerate(SEASONS.items()):
  gx,gy=s['entrance'];hx,hy=s['hub'];objects.append(obj(entrance_kind[key],gx,gy,width=10,depth=7,place='yr_'+key+'_gate'))
  for dx,dy in [(-11,-9),(11,8)]:objects.append(obj('year_lodge',hx+dx,hy+dy,width=5,depth=4,v=i))
  objects.append(obj('year_lantern',hx,hy-8,.2,v=i))
  for kind,count,r in props[key]:
   placed=0
   for _ in range(150000):
    if placed==count:break
    x,y=rng.uniform(12,388),rng.uniform(12,388)
    if season_of(x,y)!=key:continue
    if math.hypot(x-hx,y-hy)<20 or math.hypot(x-gx,y-gy)<16:continue
    if any(math.hypot(x-ex,y-ey)<7 for ex,ey in s['elite_pos']):continue
    if math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<15 or dist_path(x,y,paths)<(4 if r>.5 else 2):continue
    if not clear(x,y,r,objects,.5):continue
    objects.append(obj(kind,x,y,r,v=rng.randrange(4)));placed+=1
   assert placed==count,(kind,placed)
 # The common crossing stays open; low markers distinguish each season's inner arch.
 for i,(key,s) in enumerate(SEASONS.items()):
  hx,hy=s['hub'];objects.append(obj('year_waymarker',hx+(12 if hx<200 else -12),hy+(12 if hy<200 else -12),.3,v=i))
 slimes=[]
 for key,s in SEASONS.items():
  for elite,(x,y) in zip(s['elites'],s['elite_pos']):
   assert clear(x,y,1.5,objects,1.0),(elite,x,y)
   slimes.append(dict(kind=elite,x=x,y=y))
  for _ in range(36):
   for _ in range(30000):
    x,y=rng.uniform(12,388),rng.uniform(12,388)
    if season_of(x,y)!=key:continue
    if math.hypot(x-s['hub'][0],y-s['hub'][1])<23 or math.hypot(x-s['entrance'][0],y-s['entrance'][1])<16:continue
    if math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<17 or math.hypot(x-200,y-200)<15:continue
    if dist_path(x,y,paths)<3.2 or not clear(x,y,1.3,objects,1.0):continue
    if any(math.hypot(x-a['x'],y-a['y'])<(14 if a['kind'] in s['elites'] else 6) for a in slimes):continue
    slimes.append(dict(kind=s['ordinary'],x=round(x,2),y=round(y,2)));break
   else:raise RuntimeError('enemy placement '+key)
 folk=[];quests=[];cities=[];places=[];instances=[]
 for i,(key,s) in enumerate(SEASONS.items()):
  hx,hy=s['hub'];prefix='yr_'+key+'_';lead=prefix+'lead';heal=prefix+'heal';trade=prefix+'trade';candidates=[prefix+str(j+1) for j in range(3)]
  folk.append(npc(lead,s['leader'],s['name']+' keeper',hx-4,hy-5,f'The {s["name"]} road circles our court. Follow its colored stones to the Equinox Crossing.',mercenary_offers.offers(open_=True),art='year_'+key+'_keeper',season=key))
  folk.append(npc(heal,s['medic'],s['name']+' healer',hx-9,hy+6,'Rest here and let this season put you right.',[dict(id='blessing',label='Receive a healing blessing',cost=0,heal=10000),dict(id='potion',label='Buy Health Potion',cost=30,item='health_potion',tiered=True)],season=key))
  folk.append(npc(trade,s['trader'],s['name']+' outfitter',hx+3,hy+8,'The road is long. Take food and a bag before you leave.',[dict(id='stew',label="Buy Traveler's Stew",cost=12,item='traveler_stew',tiered=True),dict(id='satchel',label='Buy Linen Satchel',cost=500,bag='linen_satchel')],True,season=key))
  for j,(eid,giver) in enumerate(zip(s['elites'],s['givers'])):
   folk.append(npc(candidates[j],giver,s['name']+' champion',hx+[-14,0,14][j],hy-16,'Bring allies to face the '+eid.replace('_',' ').title()+'.',mercenary_offers.offers(),season=key))
  intro=prefix+'intro'
  quests.append(quest(intro,'A Season in Motion',lead,'Meet the healer and outfitter, then secure the nearby road.',[talk(heal,'Meet '+s['medic']),talk(trade,'Meet '+s['trader']),kill(s['ordinary'],5,'Defeat '+s['ordinary'].replace('_',' ').title())],s['level'],15000))
  for j,(eid,giver) in enumerate(zip(s['elites'],candidates)):
   quests.append(quest(prefix+str(j+1),['The First Sign','The Second Sign','The Third Sign'][j],giver,'Gather a party and face the '+eid.replace('_',' ').title()+'.',[kill(eid,1,'Defeat '+eid.replace('_',' ').title())],min(99,s['level']+j),26000+j*8000,intro,group=True,recommendedPlayers=[3,4,5][j]))
  place='yr_'+key+'_gate';quests.append(quest(prefix+'gate','Door of the '+s['name'],lead,'Survey the sealed '+s['door']+' and report back.',[visit(place,'Survey '+s['door'])],min(99,s['level']+2),21000,intro))
  if key=='sp':
   quests.append(quest('yr_sp_bloom_trials','Petals of Glass',lead,'With your party, defeat the Thornkeeper and Petal Mirror in the Blooming Labyrinth.',[kill('bloom_thornkeeper',1,'Defeat the Thornkeeper'),kill('bloom_mirror',1,'Defeat the Petal Mirror'),kill('bloom_spore',3,'Defeat Glasspetal Spores')],97,37000,'yr_sp_gate',group=True,recommendedPlayers=5))
   quests.append(quest('yr_sp_bloom_final','Heart of the Labyrinth',lead,'Break the labyrinth heart with your party.',[kill('bloom_heart',1,'Defeat the Heart of the Labyrinth')],97,55000,'yr_sp_bloom_trials',group=True,recommendedPlayers=5))
  if key=='su':
   quests.append(quest('yr_su_solar_trials','Forged in Daylight',lead,'With your party, defeat the Ashwarden and Heliomancer in the Solar Crucible.',[kill('solar_ashwarden',1,'Defeat the Ashwarden'),kill('solar_heliomancer',1,'Defeat the Heliomancer'),kill('solar_emberling',3,'Defeat Cinderlings')],98,41000,'yr_su_gate',group=True,recommendedPlayers=5))
   quests.append(quest('yr_su_solar_final','The Last Ember',lead,'Quench the Heart of the Crucible with your party.',[kill('solar_heart',1,'Defeat the Heart of the Crucible')],98,61000,'yr_su_solar_trials',group=True,recommendedPlayers=5))
  if key=='au':
   quests.append(quest('yr_au_amber_trials','Pages of Autumn',lead,'With your party, defeat the Curator and Living Chronicle in the Amber Archive.',[kill('amber_curator',1,'Defeat the Curator'),kill('amber_chronicle',1,'Defeat the Living Chronicle'),kill('amber_page',3,'Defeat Living Pages')],99,45000,'yr_au_gate',group=True,recommendedPlayers=5))
   quests.append(quest('yr_au_amber_final','The Last Memory',lead,'Release the final memory from the Archive with your party.',[kill('amber_memory',1,'Defeat the Last Memory')],99,65000,'yr_au_amber_trials',group=True,recommendedPlayers=5))
  if key=='wi':
   quests.append(quest('yr_wi_sols_trials','The Longest Watch',lead,'With your party, defeat the Frost Watcher and Harbinger in the Silent Solstice.',[kill('solstice_watcher',1,'Defeat the Frost Watcher'),kill('solstice_harbinger',1,'Defeat the Harbinger'),kill('solstice_flurry',3,'Defeat Whispering Flurries')],99,45000,'yr_wi_gate',group=True,recommendedPlayers=5))
   quests.append(quest('yr_wi_sols_final','First Light',lead,'Break the Heart of the Longest Night with your party.',[kill('solstice_heart',1,'Defeat the Heart of the Longest Night')],99,65000,'yr_wi_sols_trials',group=True,recommendedPlayers=5))
  quests.append(quest(prefix+'patrol',s['name']+' Watch',lead,'Patrol the local road and keep its season safe.',[kill(s['ordinary'],8,'Defeat '+s['ordinary'].replace('_',' ').title())],s['level'],11000,intro,True))
  city=dict(name=s['name'],x0=hx-20,x1=hx+20,y0=hy-19,y1=hy+19,plaza=dict(x=hx,y=hy),radius=8,entry=dict(x=hx-12,y=hy))
  cities.append(city);places.append(dict(id=place,name=s['door'],x=s['gate'][0],y=s['gate'][1],r=8))
  instances.append(dict(name=s['door'],season=key,level=min(99,s['level']+2),players=5,status='open',x=s['entrance'][0],y=s['entrance'][1]))
 zone=dict(name=NAME,theme='yearwheel',tagline='Four seasons turn around the Equinox Crossing',size=SIZE,levels=[95,99],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),paths=[[[x,y] for x,y in p] for p in paths],objects=objects,slimes=slimes,npcs=folk,quests=quests,city=cities[0],camps=cities[1:],places=places,futureInstances=instances,
           portals=[dict(id='year_cairn_gate',name="Year's Ascent",x=RETURN[0],y=RETURN[1],r=1.3,to=27,tx=151,ty=114,look='yearwheel'),
                    dict(id='year_bloom_descent',name='The Blooming Labyrinth',x=48,y=237,r=1.2,to=36,tx=48,ty=82,look='blooming_labyrinth'),
                    dict(id='year_solar_descent',name='The Solar Crucible',x=352,y=256,r=1.2,to=37,tx=48,ty=82,look='solar_crucible'),
                    dict(id='year_amber_descent',name='The Amber Archive',x=352,y=159,r=1.2,to=38,tx=48,ty=82,look='amber_archive'),
                    dict(id='year_solstice_descent',name='The Silent Solstice',x=47,y=158,r=1.2,to=39,tx=48,ty=82,look='silent_solstice')])
 check(zone);return zone

def check(zone):
 seen,_=fen.flood(zone,ARRIVAL)
 for target in [*zone['npcs'],*zone['slimes'],*zone['portals'],*zone['places']]:
  assert seen[int(target['y']/.5),int(target['x']/.5)],f'unreachable: {target}'
 assert len(zone['slimes'])==156 and len(zone['quests'])==32 and len(zone['futureInstances'])==4
 assert all(len('quest:accept:'+q['id'])<=32 for q in zone['quests'])
 assert all(math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>=8 for s in zone['slimes'])

def main():
 world=json.loads(MAP.read_text());assert world['zones'][26]['name']=='The Cairnspine'
 later=world['zones'][ZONE-1:]
 while later and later[0].get('name')==NAME:later=later[1:]
 previous=world['zones'][ZONE-1]
 world['zones']=world['zones'][:ZONE-1]
 zone=build();progression_quests.keep_released_rewards_and_route_quest(previous,zone)
 cairn.open_year_gate(world['zones'][26]);world['zones'].append(zone);world['zones'].extend(later)
 from generate_blackhour import install_parent
 install_parent(world)
 spark_travel.ensure(world);MAP.write_text(json.dumps(world,indent=2)+'\n')
 items=json.loads(ITEMS.read_text())
 for _,key,name,sell in MATERIALS:
  if not any(i['id']==key for i in items):items.append(dict(id=key,name=name,kind='material',rarity='common',sell=sell))
 ITEMS.write_text(json.dumps(items,indent=2)+'\n')
 print(f'{NAME}: {len(world["zones"][27]["objects"])} objects, 156 enemies, {len(world["zones"][27]["quests"])} quests, four open entrances')
if __name__=='__main__':main()
