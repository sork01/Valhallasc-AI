"""Annual Valentine city errands/dressing and the Rimeveil daily Briarheart summon."""
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GIVERS=['baker','city_bard','nacre_gardener','asterion_singer']
SPECS=[
 (0,'valentine_alder','A Heart at Every Hearth','baker',1,100,
  "Pip wants nobody to feel forgotten on Valentine's Day. Ask Linden for letter paper, Mira for rose ribbons, and Tessa for heart biscuits, then bring their kind wishes back to Pip.",
  [('talk','merchant','Ask Linden for letter paper'),('talk','apothecary','Ask Mira for rose ribbons'),('talk','innkeeper','Arrange heart biscuits with Tessa')]),
 (4,'valentine_skald','A Ballad for Brave Hearts','city_bard',20,500,
  "Eira is writing a Valentine's ballad for the people who keep Skaldholm safe. Ask Brunhild for a heart pendant, Fenwick for a love poem, and Captain Ingrid to join the singing.",
  [('talk','city_smith','Ask Brunhild for a heart pendant'),('talk','city_librarian','Find a love poem with Fenwick'),('talk','city_captain','Invite Captain Ingrid to the singing')]),
 (9,'valentine_nacre','Roses for the Remembered','nacre_gardener',40,1500,
  "Pelar is sharing roses for Valentine's Day. Ask Ilo for pink pearl lights and Syllene for a gentle song, then leave a rose at the Memorial of the Lost Choir.",
  [('talk','nacre_lamplighter','Arrange pink pearl lights with Ilo'),('talk','nacre_singer','Ask Syllene for a gentle love song'),('visit','nacre_memorial','Leave a rose at the memorial')]),
 (17,'valentine_aster','Written in the Stars','asterion_singer',60,2800,
  "Vela is preparing Valentine's wishes beneath Asterion's stars. Ask Mora for the opening chime, Umi for rose garlands, and Nim for sealed wish letters.",
  [('talk','asterion_bellkeeper','Arrange the opening chime with Mora'),('talk','asterion_gardener','Plan rose garlands with Umi'),('talk','asterion_merchant','Arrange sealed wish letters with Nim')]),
]
def event():return dict(id='valentine',start=[2,10],endExclusive=[2,19],quests=[s[1] for s in SPECS]+['valentine_hunt'],dailyQuests=['valentine_hunt'],givers={'valentine_hunt':GIVERS})
def apply(world,levels):
 from compact_atlas import clear,connected
 zones=[world,*world['zones']];ids={s[1] for s in SPECS}|{'valentine_hunt'}
 for area in zones:
  area['quests']=[q for q in area.get('quests',[]) if q['id'] not in ids];area.pop('valentineDecor',None)
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
  remap={'festivalPumpkins':'valentineRoses','festivalLantern':'valentineLantern','festivalCandles':'valentineCandles','festivalWreath':'valentineWreath','festivalWeb':'valentineGarland','festivalBunting':'valentineLights','festivalScarecrow':'valentineHeart'}
  for i,o in enumerate(area.get('seasonDecor',[])):
   if not o.get('z') and street_centre(o['x'],o['y']):continue
   kind=remap[o['kind']]
   if kind=='valentineHeart' and i%3==0:kind='valentineBouquet'
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
   centre['kind']='valentineGrandHeart'
  area['valentineDecor']=decor
  area['quests'].append(dict(id=id_,title=title,npc=npc,description=description,objectives=[dict(kind=k,target=t,label=l,count=1) for k,t,l in objectives],level=level,minLevel=level,rewardXp=levels[level-1]//10,rewardGold=gold,requires=None,repeatable=True,season='valentine'))
  host=next(n for n in area['npcs'] if n['id']==npc)
  host['offers']=[o for o in host['offers'] if not o['id'].startswith('valentine:hire:')]
  for cls in ['warrior','mage','assassin','priest','hunter']:
   host['offers'].append(dict(id='valentine:hire:'+cls,label='Hire '+('an ' if cls=='assassin' else 'a ')+cls.title(),merc=cls,cost=0,season='valentine',quest='valentine_hunt'))
 world['quests'].append(dict(id='valentine_hunt',title='The Briarheart',npc='baker',givers=GIVERS,
  description='Gather five fighters at the Roseheart Shrine in Rimeveil Glacier. Press the shrine to summon the Briarheart, a thorn guardian holding the festival roses. It matches the highest party level. Hired fighters can help. Claim this daily quest at any city festival host to earn the Roseheart Unicorn, guaranteed. One claim per Stockholm day.',
  objectives=[dict(kind='kill',target='briarheart',count=1,label='Defeat the summoned Briarheart')],level=1,minLevel=1,rewardXp=levels[0]//10,rewardGold=300,rewardMount='roseheart',requires=None,repeatable=True,group=True,recommendedPlayers=5,season='valentine',seasonCadence='daily',summonNpc='valentine_shrine',summonZone=2))
 rime=zones[2];centre=(103.,100.);tree=(112.,100.)
 rime['slimes']=[s for s in rime['slimes'] if s['kind']!='briarheart'];rime['npcs']=[n for n in rime['npcs'] if n['id']!='valentine_shrine']
 foliage={'pine','snowpine','tree','rock','frostpine','icecrystal','crystal','snowdrift','bush'}
 rime['objects']=[o for o in rime['objects'] if o['kind'] not in foliage or math.hypot(o['x']-centre[0],o['y']-centre[1])>o.get('r',0)+10.5]
 assert clear(rime,centre,centre,9.5),'Valentine clearing must be clear'
 reachable=connected(rime);assert int(tree[1])*rime['size']+int(tree[0]) in reachable,'Valentine tree must be reachable'
 assert all(math.hypot(s['x']-centre[0],s['y']-centre[1])>=16 for s in rime['slimes'] if s['kind']!='grinch')
 assert all(math.hypot(p['x']-centre[0],p['y']-centre[1])>=18 for p in rime['portals'])
 rime['slimes'].append(dict(kind='briarheart',x=centre[0],y=centre[1],ambush='valentine:briarheart'))
 rime['npcs'].append(dict(id='valentine_shrine',name='Roseheart Shrine',role='Valentine summon',art='scenery',x=tree[0],y=tree[1],r=.4,color='#e1bc63',season='valentine',
  dialogue='Gather five living, dismounted fighters here with the daily Briarheart quest. The guardian matches the highest party level. Claim the completed quest at any city festival host for a guaranteed Roseheart Unicorn. One claim per Stockholm day.',offers=[dict(id='valentine:summon',label='Summon the Briarheart',cost=0)],buys=False))
 rime['valentineRitual']=dict(x=centre[0],y=centre[1],radius=9,tree=list(tree))
 return world
