"""Annual Christmas city errands/dressing and the Rimeveil daily Grinch summon."""
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GIVERS=['baker','city_bard','nacre_gardener','asterion_singer','hw_baker']
SPECS=[
 (0,'christmas_alder','A Gift for Every Hearth','baker',1,100,
  'Pip wants every home to have a little Christmas joy. Ask Linden for gift boxes, Mira for bright ribbons, and Tessa for hot chocolate, then bring their good wishes back to Pip.',
  [('talk','merchant','Arrange gift boxes with Linden'),('talk','apothecary','Ask Mira for Christmas ribbons'),('talk','innkeeper','Arrange hot chocolate with Tessa')]),
 (4,'christmas_skald','The Winter Bell Choir','city_bard',20,500,
  'Eira is gathering a Christmas choir. Ask Brunhild for little bells, Fenwick for an old carol, and Captain Ingrid to welcome the singers at the city gate.',
  [('talk','city_smith','Ask Brunhild for Christmas bells'),('talk','city_librarian','Find a Christmas carol with Fenwick'),('talk','city_captain','Invite Captain Ingrid to the choir')]),
 (9,'christmas_nacre','Pearls on the Christmas Tree','nacre_gardener',40,1500,
  'Pelar is dressing Nacrehold for Christmas. Ask Ilo for pearl lights and Syllene for a carol, then visit the Memorial of the Lost Choir to leave a warm Christmas wish before returning.',
  [('talk','nacre_lamplighter','Arrange pearl lights with Ilo'),('talk','nacre_singer','Ask Syllene for a Christmas carol'),('visit','nacre_memorial','Leave a Christmas wish at the memorial')]),
 (17,'christmas_aster','The Star Above Every Door','asterion_singer',60,2800,
  'Vela wants Christmas to shine across Asterion. Ask Mora to ring the Christmas bells, Umi for evergreen roof garlands, and Nim for gifts beneath the stars.',
  [('talk','asterion_bellkeeper','Arrange the Christmas bells with Mora'),('talk','asterion_gardener','Plan evergreen garlands with Umi'),('talk','asterion_merchant','Arrange Christmas gifts with Nim')]),
 (24,'christmas_heart','A Candle in Every Burl','hw_baker',80,4500,
  'Olle is baking for the whole tree. Ask Pim for candle wax, Saga for woollen ribbons, and Marit for hot sap cider, then bring their good wishes back to Olle.',
  [('talk','hw_lamplighter','Ask Pim for candle wax'),('talk','hw_weaver','Ask Saga for woollen ribbons'),('talk','hw_innkeeper','Arrange hot sap cider with Marit')]),
]
def event():return dict(id='christmas',start=[12,15],endExclusive=[12,29],quests=[s[1] for s in SPECS]+['christmas_hunt'],dailyQuests=['christmas_hunt'],givers={'christmas_hunt':GIVERS})
def apply(world,levels):
 from compact_atlas import clear,connected
 zones=[world,*world['zones']];ids={s[1] for s in SPECS}|{'christmas_hunt'}
 for area in zones:
  area['quests']=[q for q in area.get('quests',[]) if q['id'] not in ids];area.pop('christmasDecor',None)
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
  remap={'festivalPumpkins':'christmasGifts','festivalLantern':'christmasLantern','festivalCandles':'christmasCandles','festivalWreath':'christmasWreath','festivalWeb':'christmasGarland','festivalBunting':'christmasLights','festivalScarecrow':'christmasTree'}
  for i,o in enumerate(area.get('seasonDecor',[])):
   if not o.get('z') and street_centre(o['x'],o['y']):continue
   kind=remap[o['kind']]
   if kind=='christmasTree' and i%3==0:kind='christmasSnowman'
   decor.append(dict(o,kind=kind,color={0:'#d74848',4:'#d2aa56',9:'#8bd8d2',17:'#c5a1df',24:'#9fd06a'}[zone]))
  # A district centrepiece where there is room; protect doorways and street centres.
  candidates=[o for o in decor if not o.get('z') and
   hub['x0']+2<o['x']<hub['x1']-2 and hub['y0']+2<o['y']<hub['y1']-2 and
   all(math.hypot(o['x']-n['x'],o['y']-n['y'])>4 for n in area['npcs']) and
   all(math.hypot(o['x']-p['x'],o['y']-p['y'])>10 for p in area['portals']) and
   clear(area,(o['x'],o['y']),(o['x'],o['y']),1.7)]
  if candidates:
   centre=min(candidates,key=lambda o:abs(math.hypot(o['x']-hub['plaza']['x'],o['y']-hub['plaza']['y'])-(hub['radius']+4)))
   decor=[o for o in decor if o.get('z') or o is centre or math.hypot(o['x']-centre['x'],o['y']-centre['y'])>4]
   centre['kind']='christmasGrandTree'
  area['christmasDecor']=decor
  area['quests'].append(dict(id=id_,title=title,npc=npc,description=description,objectives=[dict(kind=k,target=t,label=l,count=1) for k,t,l in objectives],level=level,minLevel=level,rewardXp=levels[level-1]//10,rewardGold=gold,requires=None,repeatable=True,season='christmas'))
  host=next(n for n in area['npcs'] if n['id']==npc)
  host['offers']=[o for o in host['offers'] if not o['id'].startswith('christmas:hire:')]
  for cls in ['warrior','mage','assassin','priest','hunter']:
   host['offers'].append(dict(id='christmas:hire:'+cls,label='Hire '+('an ' if cls=='assassin' else 'a ')+cls.title(),merc=cls,cost=0,season='christmas',quest='christmas_hunt'))
 world['quests'].append(dict(id='christmas_hunt',title='The Grinch',npc='baker',givers=GIVERS,
  description='Gather five fighters at the great Christmas tree in Rimeveil Glacier. Press the tree to summon the Grinch and recover the stolen presents. He matches the highest level in your party. Hired fighters can help. Each eligible hero has one independent 5% Red-nosed Reindeer roll per day. Return to any city festival host.',
  objectives=[dict(kind='kill',target='grinch',count=1,label='Defeat the summoned Grinch')],level=1,minLevel=1,rewardXp=levels[0]//10,rewardGold=300,requires=None,repeatable=True,group=True,recommendedPlayers=5,season='christmas',seasonCadence='daily',summonNpc='christmas_tree',summonZone=2))
 rime=zones[2];centre=(103.,100.);tree=(112.,100.)
 rime['slimes']=[s for s in rime['slimes'] if s['kind']!='grinch'];rime['npcs']=[n for n in rime['npcs'] if n['id']!='christmas_tree']
 foliage={'pine','snowpine','tree','rock','frostpine','icecrystal','crystal','snowdrift','bush'}
 rime['objects']=[o for o in rime['objects'] if o['kind'] not in foliage or math.hypot(o['x']-centre[0],o['y']-centre[1])>o.get('r',0)+10.5]
 assert clear(rime,centre,centre,9.5),'Christmas clearing must be clear'
 reachable=connected(rime);assert int(tree[1])*rime['size']+int(tree[0]) in reachable,'Christmas tree must be reachable'
 assert all(math.hypot(s['x']-centre[0],s['y']-centre[1])>=16 for s in rime['slimes'])
 assert all(math.hypot(p['x']-centre[0],p['y']-centre[1])>=18 for p in rime['portals'])
 rime['slimes'].append(dict(kind='grinch',x=centre[0],y=centre[1],ambush='christmas:grinch'))
 rime['npcs'].append(dict(id='christmas_tree',name='The Great Christmas Tree',role='Christmas summon',art='scenery',x=tree[0],y=tree[1],r=.4,color='#e1bc63',season='christmas',
  dialogue='Press the Christmas tree while on The Grinch daily quest to summon him with five fighters. He matches the highest level in the party. Each eligible hero has one independent 5% reindeer roll per day.',offers=[dict(id='christmas:summon',label='Summon the Grinch',cost=0)],buys=False))
 rime['christmasRitual']=dict(x=centre[0],y=centre[1],radius=9,tree=list(tree))
 return world
