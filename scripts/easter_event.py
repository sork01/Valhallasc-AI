"""Annual Easter city errands/dressing and the Rimeveil daily Bloomwarden summon."""
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GIVERS=['baker','city_bard','nacre_gardener','asterion_singer']
SPECS=[
 (0,'easter_alder','An Egg for Every Hearth','baker',1,100,
  'Pip wants to share painted Easter eggs with every home. Ask Linden for egg baskets, Mira for pastel dyes and Tessa for spring buns, then bring their good wishes back to Pip.',
  [('talk','merchant','Arrange egg baskets with Linden'),('talk','apothecary','Ask Mira for pastel egg dyes'),('talk','innkeeper','Arrange spring buns with Tessa')]),
 (4,'easter_skald','The Spring Bell Parade','city_bard',20,500,
  'Eira is planning a spring parade. Ask Brunhild for little bells, Fenwick for a spring ballad and Captain Ingrid to welcome the Easter parade at the city gate.',
  [('talk','city_smith','Ask Brunhild for spring bells'),('talk','city_librarian','Find a spring ballad with Fenwick'),('talk','city_captain','Invite Captain Ingrid to the Easter parade')]),
 (9,'easter_nacre','Pearls of a New Spring','nacre_gardener',40,1500,
  'Pelar is filling Nacrehold with spring flowers and painted pearl eggs. Ask Ilo for pearl lights and Syllene for a spring song, then leave an Easter flower at the Memorial of the Lost Choir.',
  [('talk','nacre_lamplighter','Arrange spring pearl lights with Ilo'),('talk','nacre_singer','Ask Syllene for a spring song'),('visit','nacre_memorial','Leave an Easter flower at the memorial')]),
 (17,'easter_aster','A Basket of Starlight','asterion_singer',60,2800,
  'Vela is preparing Easter baskets beneath the stars. Ask Mora for a spring chime, Umi for blossom ribbons and Nim for little star-painted eggs.',
  [('talk','asterion_bellkeeper','Arrange the spring chime with Mora'),('talk','asterion_gardener','Plan blossom ribbons with Umi'),('talk','asterion_merchant','Arrange star-painted eggs with Nim')]),
]
def event():return dict(id='easter',calendar='gregorianEaster',startOffset=-2,endOffsetExclusive=9,quests=[s[1] for s in SPECS]+['easter_hunt'],dailyQuests=['easter_hunt'],givers={'easter_hunt':GIVERS})
def apply(world,levels):
 from compact_atlas import clear,connected
 zones=[world,*world['zones']];ids={s[1] for s in SPECS}|{'easter_hunt'}
 for area in zones:
  area['quests']=[q for q in area.get('quests',[]) if q['id'] not in ids];area.pop('easterDecor',None)
 for zone,id_,title,npc,level,gold,description,objectives in SPECS:
  area=zones[zone];hub=area['city'];decor=[]
  def street_centre(x,y):
   if zone==0:return abs(x-36)<1.3 and (y<79 or y>87)
   for r in area.get('roads',[]):
    if 'x0' not in r:continue
    dx,dy=r['x1']-r['x0'],r['y1']-r['y0']
    if dy>dx*3 and abs(x-(r['x0']+r['x1'])/2)<1.4 and r['y0']-1<y<r['y1']+1:return True
    if dx>dy*3 and abs(y-(r['y0']+r['y1'])/2)<1.4 and r['x0']-1<x<r['x1']+1:return True
   return False
  remap={'festivalPumpkins':'easterFlowers','festivalLantern':'easterLantern','festivalCandles':'easterCandles','festivalWreath':'easterWreath','festivalWeb':'easterGarland','festivalBunting':'easterLights','festivalScarecrow':'easterEgg'}
  for i,o in enumerate(area.get('seasonDecor',[])):
   if not o.get('z') and street_centre(o['x'],o['y']):continue
   kind=remap[o['kind']]
   if kind=='easterEgg' and i%3==0:kind='easterBasket'
   decor.append(dict(o,kind=kind,color={0:'#d74848',4:'#d2aa56',9:'#8bd8d2',17:'#c5a1df'}[zone]))
  # A district centrepiece where there is room; protect doorways and street centres.
  candidates=[o for o in decor if not o.get('z') and
   hub['x0']+2<o['x']<hub['x1']-2 and hub['y0']+2<o['y']<hub['y1']-2 and
   all(math.hypot(o['x']-n['x'],o['y']-n['y'])>4 for n in area['npcs']) and
   all(math.hypot(o['x']-p['x'],o['y']-p['y'])>10 for p in area['portals']) and
   clear(area,(o['x'],o['y']),(o['x'],o['y']),1.7)]
  if candidates:
   centre=min(candidates,key=lambda o:abs(math.hypot(o['x']-hub['plaza']['x'],o['y']-hub['plaza']['y'])-(hub['radius']+4)))
   decor=[o for o in decor if o.get('z') or o is centre or math.hypot(o['x']-centre['x'],o['y']-centre['y'])>4]
   centre['kind']='easterGrandEgg'
  area['easterDecor']=decor
  area['quests'].append(dict(id=id_,title=title,npc=npc,description=description,objectives=[dict(kind=k,target=t,label=l,count=1) for k,t,l in objectives],level=level,minLevel=level,rewardXp=levels[level-1]//10,rewardGold=gold,requires=None,repeatable=True,season='easter'))
  host=next(n for n in area['npcs'] if n['id']==npc)
  host['offers']=[o for o in host['offers'] if not o['id'].startswith('easter:hire:')]
  for cls in ['warrior','mage','assassin','priest','hunter']:
   host['offers'].append(dict(id='easter:hire:'+cls,label='Hire '+('an ' if cls=='assassin' else 'a ')+cls.title(),merc=cls,cost=0,season='easter',quest='easter_hunt'))
 world['quests'].append(dict(id='easter_hunt',title='The Bloomwarden',npc='baker',givers=GIVERS,
  description='Gather five fighters at the Springtide Egg Basket in Rimeveil Glacier. Press the shrine to summon the Bloomwarden, a moss-and-blossom guardian protecting the painted eggs. It matches the highest party level. Hired fighters can help. Each eligible hero has one independent 5% Springtide Bunny roll per Stockholm day. Return to any city festival host.',
  objectives=[dict(kind='kill',target='bloomwarden',count=1,label='Defeat the summoned Bloomwarden')],level=1,minLevel=1,rewardXp=levels[0]//10,rewardGold=300,requires=None,repeatable=True,group=True,recommendedPlayers=5,season='easter',seasonCadence='daily',summonNpc='easter_shrine',summonZone=2))
 rime=zones[2];centre=(103.,100.);tree=(112.,100.)
 rime['slimes']=[s for s in rime['slimes'] if s['kind']!='bloomwarden'];rime['npcs']=[n for n in rime['npcs'] if n['id']!='easter_shrine']
 foliage={'pine','snowpine','tree','rock','frostpine','icecrystal','crystal','snowdrift','bush'}
 rime['objects']=[o for o in rime['objects'] if o['kind'] not in foliage or math.hypot(o['x']-centre[0],o['y']-centre[1])>o.get('r',0)+10.5]
 assert clear(rime,centre,centre,9.5),'Easter clearing must be clear'
 reachable=connected(rime);assert int(tree[1])*rime['size']+int(tree[0]) in reachable,'Easter tree must be reachable'
 assert all(math.hypot(s['x']-centre[0],s['y']-centre[1])>=16 for s in rime['slimes'] if s['kind'] not in {'grinch','bloomwarden','birchcrown','briarheart','starrocketeer'})
 assert all(math.hypot(p['x']-centre[0],p['y']-centre[1])>=18 for p in rime['portals'])
 rime['slimes'].append(dict(kind='bloomwarden',x=centre[0],y=centre[1],ambush='easter:bloomwarden'))
 rime['npcs'].append(dict(id='easter_shrine',name='Springtide Egg Basket',role='Easter summon',art='scenery',x=tree[0],y=tree[1],r=.4,color='#e1bc63',season='easter',
  dialogue='Gather five living, dismounted fighters here with the daily Bloomwarden quest. The guardian matches the highest party level. Each eligible hero has one independent 5% Springtide Bunny roll per Stockholm day. Return to any city festival host.',offers=[dict(id='easter:summon',label='Summon the Bloomwarden',cost=0)],buys=False))
 rime['easterRitual']=dict(x=centre[0],y=centre[1],radius=9,tree=list(tree))
 return world
