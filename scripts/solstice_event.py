"""Annual Summer Solstice city errands/dressing and the Rimeveil daily Birchcrown Guardian summon."""
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GIVERS=['baker','city_bard','nacre_gardener','asterion_singer']
SPECS=[
 (0,'solstice_alder','Flowers for Every Door','baker',1,100,
  'Pip is weaving flower crowns for Summer Solstice. Ask Linden for blue and yellow ribbons, Mira for wildflowers and Tessa for strawberry cakes, then return to Pip.',
  [('talk','merchant','Ask Linden for blue and yellow ribbons'),('talk','apothecary','Gather wildflowers with Mira'),('talk','innkeeper','Arrange strawberry cakes with Tessa')]),
 (4,'solstice_skald','Raise the Midsummer Pole','city_bard',20,500,
  'Eira is raising a leafy midsummer pole with two wreath rings. Ask Brunhild for the crossbar fittings, Fenwick for dancing songs and Captain Ingrid to keep the dancing circle clear.',
  [('talk','city_smith','Arrange the pole fittings with Brunhild'),('talk','city_librarian','Find dancing songs with Fenwick'),('talk','city_captain','Keep the dancing circle clear with Ingrid')]),
 (9,'solstice_nacre','Wreaths upon the Water','nacre_gardener',40,1500,
  'Pelar is weaving wildflower wreaths for the long summer evening. Ask Ilo for warm lanterns and Syllene for a midsummer song, then leave a flower wreath at the Memorial of the Lost Choir.',
  [('talk','nacre_lamplighter','Arrange summer lanterns with Ilo'),('talk','nacre_singer','Ask Syllene for a midsummer song'),('visit','nacre_memorial','Leave a wildflower wreath at the memorial')]),
 (17,'solstice_aster','The Sunlit Garland','asterion_singer',60,2800,
  'Vela is stringing sunlit garlands beneath the stars. Ask Mora for the midsummer chime, Umi for birch branches and Nim for blue and yellow ribbons.',
  [('talk','asterion_bellkeeper','Arrange the midsummer chime with Mora'),('talk','asterion_gardener','Gather birch branches with Umi'),('talk','asterion_merchant','Arrange summer ribbons with Nim')]),
]
def event():return dict(id='solstice',calendar='juneSolstice',startOffset=-4,endOffsetExclusive=5,quests=[s[1] for s in SPECS]+['solstice_hunt'],dailyQuests=['solstice_hunt'],givers={'solstice_hunt':GIVERS})
def apply(world,levels):
 from compact_atlas import clear,connected
 zones=[world,*world['zones']];ids={s[1] for s in SPECS}|{'solstice_hunt'}
 for area in zones:
  area['quests']=[q for q in area.get('quests',[]) if q['id'] not in ids];area.pop('solsticeDecor',None)
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
  remap={'festivalPumpkins':'solsticeFlowers','festivalLantern':'solsticeLantern','festivalCandles':'solsticeFlowers','festivalWreath':'solsticeWreath','festivalWeb':'solsticeGarland','festivalBunting':'solsticeLights','festivalScarecrow':'solsticeBirch'}
  for i,o in enumerate(area.get('seasonDecor',[])):
   if not o.get('z') and street_centre(o['x'],o['y']):continue
   kind=remap[o['kind']]
   if kind=='solsticeBirch' and i%3==0:kind='solsticeTable'
   decor.append(dict(o,kind=kind,color={0:'#d74848',4:'#d2aa56',9:'#8bd8d2',17:'#c5a1df'}[zone]))
  # Authored plaza-side circles: routes/collision stay unchanged, space is cleared only of cosmetics.
  x,y={0:(32,83),4:(87,83),9:(93,100),17:(95,91)}[zone]
  assert hub['x0']+2<x<hub['x1']-2 and hub['y0']+2<y<hub['y1']-2
  assert all(math.hypot(x-n['x'],y-n['y'])>3 for n in area['npcs'])
  assert all(math.hypot(x-p['x'],y-p['y'])>7 for p in area['portals'])
  assert clear(area,(x,y),(x,y),2.5),f'{hub["name"]} needs clear dancing space'
  decor=[o for o in decor if o.get('z') or math.hypot(o['x']-x,o['y']-y)>4]
  decor.append(dict(kind='solsticePole',x=x,y=y,z=0,r=0,danceRadius=2.5,hub=hub['name']))
  if not any(o['kind']=='solsticeTable' for o in decor):
   # Alderhaven is compact: use a verified clear side of the northern square.
   table=next(o for o in decor if o['kind']=='solsticeFlowers' and
    clear(area,(o['x'],o['y']),(o['x'],o['y']),1.4))
   table['kind']='solsticeTable'
  area['solsticeDecor']=decor
  area['quests'].append(dict(id=id_,title=title,npc=npc,description=description,objectives=[dict(kind=k,target=t,label=l,count=1) for k,t,l in objectives],level=level,minLevel=level,rewardXp=levels[level-1]//10,rewardGold=gold,requires=None,repeatable=True,season='solstice'))
  host=next(n for n in area['npcs'] if n['id']==npc)
  host['offers']=[o for o in host['offers'] if not o['id'].startswith('solstice:hire:')]
  for cls in ['warrior','mage','assassin','priest','hunter']:
   host['offers'].append(dict(id='solstice:hire:'+cls,label='Hire '+('an ' if cls=='assassin' else 'a ')+cls.title(),merc=cls,cost=0,season='solstice',quest='solstice_hunt'))
 world['quests'].append(dict(id='solstice_hunt',title='The Birchcrown Guardian',npc='baker',givers=GIVERS,
  description='Gather five fighters at the Sunwoven Midsummer Pole in Rimeveil Glacier. Press the pole to summon the Birchcrown Guardian, a birch-bark guardian crowned with wildflowers and sunlight. It matches the highest party level. Hired fighters can help. Each eligible hero has one independent 5% Sunwoven Stag roll per Stockholm day. Return to any city festival host.',
  objectives=[dict(kind='kill',target='birchcrown',count=1,label='Defeat the summoned Birchcrown Guardian')],level=1,minLevel=1,rewardXp=levels[0]//10,rewardGold=300,requires=None,repeatable=True,group=True,recommendedPlayers=5,season='solstice',seasonCadence='daily',summonNpc='solstice_pole',summonZone=2))
 rime=zones[2];centre=(103.,100.);tree=(112.,100.)
 rime['slimes']=[s for s in rime['slimes'] if s['kind']!='birchcrown'];rime['npcs']=[n for n in rime['npcs'] if n['id']!='solstice_pole']
 assert clear(rime,centre,centre,9.5),'Summer Solstice clearing must be clear'
 reachable=connected(rime);assert int(tree[1])*rime['size']+int(tree[0]) in reachable,'Summer Solstice tree must be reachable'
 assert all(math.hypot(s['x']-centre[0],s['y']-centre[1])>=16 for s in rime['slimes'] if s['kind'] not in {'grinch','bloomwarden','birchcrown','briarheart','starrocketeer'})
 assert all(math.hypot(p['x']-centre[0],p['y']-centre[1])>=18 for p in rime['portals'])
 rime['slimes'].append(dict(kind='birchcrown',x=centre[0],y=centre[1],ambush='solstice:birchcrown'))
 rime['npcs'].append(dict(id='solstice_pole',name='Sunwoven Midsummer Pole',role='Summer Solstice summon',art='scenery',x=tree[0],y=tree[1],r=.4,color='#e1bc63',season='solstice',
  dialogue='Gather five living, dismounted fighters here with the daily Birchcrown Guardian quest. The guardian matches the highest party level. Each eligible hero has one independent 5% Sunwoven Stag roll per Stockholm day. Return to any city festival host.',offers=[dict(id='solstice:summon',label='Summon the Birchcrown Guardian',cost=0)],buys=False))
 rime['solsticeRitual']=dict(x=centre[0],y=centre[1],radius=9,tree=list(tree))
 return world
