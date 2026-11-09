"""Shared, byte-stable four-city dance landmarks for every registered season."""
import math
POSITIONS={0:(32,83),4:(87,83),9:(93,100),17:(95,91),24:(36,60)}
KINDS={'solstice':('solsticePole','Midsummer Pole'),'christmas':('christmasGrandTree','Christmas Tree'),
 'valentine':('valentineGrandHeart','Valentine Heart'),'easter':('easterGrandEgg','Easter Egg'),
 'halloween':('festivalPumpkins','Halloween Pumpkin'),'newyear':('newyearLaunchpad','New Year Rocket')}
def apply(world,events):
 from compact_atlas import clear,connected
 areas=[world,*world['zones']]
 for z in areas:
  z['npcs']=[n for n in z['npcs'] if not n['id'].startswith('festival_dance_')]
 for zone,(x,y) in POSITIONS.items():
  a=areas[zone];assert clear(a,(x,y),(x,y),2.5),'Dance circle must be clear'
  assert int(y)*a['size']+int(x) in connected(a)
  for key in ['seasonDecor','christmasDecor','easterDecor','solsticeDecor','valentineDecor']:
   if key in a:a[key]=[o for o in a[key] if o.get('z') or math.hypot(o['x']-x,o['y']-y)>3.2]
  for e in events:
   season=e['id'];kind,name=KINDS.get(season,('solsticeFlowers','Festival Flowers'))
   a['npcs'].append(dict(id=f'festival_dance_{season}_{zone}',name=name,role='Festival dance',art='scenery',x=x,y=y,r=0,season=season,
    dialogue='Dance two full laps around this centerpiece to receive Festival Spirit: +10% attack and +50% experience for two hours. Move or fight to cancel. The timer continues offline; another completed dance refreshes it.',
    offers=[dict(id='festival:dance',label='Dance two laps · earn Festival Spirit',cost=0)],buys=False))
   # Scenery goes through the normal client depth list; no collision geometry changes.
   a['npcs'][-1]['festivalArt']=kind
 return world
