#!/usr/bin/env python3
"""Cel NPCs through PixelFlow: preview | build | export | verify (optional design keys).
Build only creates missing saves. Export always honours saved editor frames.
"""
import json, math, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import cathedral_reliquary_redraw as R
from make_crag_sprites import Palette, rgba
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'client/assets'
PLAN=json.loads((ROOT/'docs/npc-art-plan.txt').read_text());SPECS=PLAN['designs']
CLIPS=[('idle',6,6),('walk',8,10),('talk',6,6)]
MANIFEST=ASSETS/'npc.txt'

def mix(c,f):
 rgb=[int(c[i:i+2],16) for i in (1,3,5)]
 return '#'+''.join(f'{round(v*f if f<1 else v+(255-v)*(f-1)):02x}' for v in rgb)

def palette(s):
 identity=s.get('identity',{});skin=identity.get('skin',['#dca480','#b87d58','#e9bda1','#a66a51'][s['index']%4]);hair=identity.get('hair',['#694737','#e4d6ae','#353d62','#ab6250','#475b51','#75638d'][s['index']%6])
 groups=dict(cloth=[mix(s['coat'],v) for v in (.45,.7,1,1.45)],skin=[mix(skin,v) for v in (.65,1,1.5)],hair=[mix(hair,v) for v in (.6,1,1.4)],
  leather=['#3b2d35','#695052','#a17b63'],metal=['#46516b','#8aabc0','#d5ecf3'],gold=['#846039','#d8ad59','#ffe2a1'],
  cream=['#9c8e79','#e9d9bc','#fff3d6'],leaf=['#285948','#4e9b6e','#a2d68d'],glass=['#27657c','#60bdc4','#b9f2e9'])
 colors=dict(ink='#211c30',white='#fffdf7',shine='#ffffed',iris='#3d7896',mouth='#9c4e60',blush='#d98b8b')
 used={'#1a1118','#fffaf0'}
 for key,value in list(colors.items()):used.add(value)
 for name,values in groups.items():
  for i,c in enumerate(values):
   while c in used:c='#%06x'%((int(c[1:],16)+1)&0xffffff)
   colors[name+str(i)]=c;used.add(c)
 return Palette(colors)
PALETTES={k:palette(s) for k,s in SPECS.items()}
R.PALETTES.update({'npc_'+k:v for k,v in PALETTES.items()})

# Grip coordinates in each prop's original drawing. Place that point at the
# animated wrist, then paint the fingers in front of the handle.
GRIPS=dict(bottle=(29,37),alembic=(29,37),hammer=(29,36),bread=(20,26),
 mug=(34,29),scales=(29,30),bow=(38,40),book=(37,32),scroll=(37,32),
 trumpet=(24,50),flowers=(35,27),fish=(27,35),spool=(29,29),satchel=(23,28),
 lyre=(35,30),kite=(25,27),palette=(23,29),saw=(21,27),reins=(24,31),
 chest=(37,24),pearl=(29,26),orb=(29,26),seed=(29,26),waterjug=(36,36),
 grain=(35,28),fan=(22,30),key=(29,38),tablet=(35,30),compass=(29,34),
 bell=(30,54),telescope=(24,38))
SUPPORTS=dict(bread=(-20,26),book=(16,32),scroll=(16,32),chest=(18,24),tablet=(20,30),grain=(21,28))

def prop_offset(kind,hand):
 gx,gy=GRIPS[kind]
 return hand[0]-gx,hand[1]-gy

def prop(a,kind,hand):
 x,y=hand
 if kind in ('spear','staff','cane','harpoon','lantern'):
  # Long poles keep their grounded foot inside the frame for every build.
  tip=min(81,y+(17 if kind=='cane' else 48))
  a.c((x,4),(x,tip-5),1.5,1.5,'leather')
  if kind=='spear':
   a.band([(x-4,tip-10),(x,tip),(x+4,tip-10)],'metal');a.band([(x+1,tip-13),(x+10,tip-17),(x+1,tip-22)],'cloth')
  elif kind=='harpoon':
   a.band([(x-4,tip-12),(x,tip),(x+4,tip-12),(x,tip-10)],'metal');a.c((x,tip-7),(x+7,tip-10),1,1,'metal')
  elif kind=='lantern':
   a.c((x,tip-5),(x+9,tip-10),1,1,'leather');a.line((x+9,tip-10),(x+9,tip-19),'gold1',1);a.band([(x+3,tip-33),(x+12,tip-33),(x+12,tip-19),(x+3,tip-19)],'gold');a.e(x+7,tip-26,3,5,'glass')
  else:a.e(x+1,tip-5,4,3,'gold')
  return
 dx,dy=prop_offset(kind,hand);ox,lift=a.ox,a.lift
 a.ox+=dx;a.lift+=dy
 try:prop_shape(a,kind)
 finally:a.ox,a.lift=ox,lift

def prop_shape(a,kind):
 # Canonical shapes; animation is applied once by prop(), never independently.
 y=27
 if kind in ('bottle','alembic'):
  a.e(29,y+5,7,9,'glass');a.c((29,y+10),(29,y+19),2.4,2,'glass');a.c((26,y+20),(32,y+20),1.5,1.5,'gold')
  if kind=='alembic':a.c((29,y+18),(38,y+24),1.5,1.5,'glass');a.c((38,y+24),(39,y+6),1.5,1.5,'glass');a.e(38,y+2,4,5,'glass')
 elif kind=='hammer':
  a.c((27,24),(32,54),1.9,1.9,'leather');a.band([(23,52),(39,52),(39,62),(23,62)],'metal')
 elif kind=='bread':
  a.band([(-21,28),(22,28),(26,24),(-24,24)],'leather')
  for x in (-12,0,12):
   a.e(x,31,6,5,'gold');a.line((x-2,34),(x+1,30),'cream2',1)
 elif kind=='mug':
  a.e(33,y+2,6,7,'gold');a.e(33,y+2,3,4,'leather');a.band([(23,y-4),(31,y-4),(32,y+11),(23,y+11)],'leather');a.e(27,y+11,5,2.5,'cream')
 elif kind=='scales':
  a.c((29,22),(29,59),1.2,1.2,'gold');a.c((19,54),(40,54),1,1,'gold')
  for x in (20,39):a.line((x,54),(x,43),'gold1',1);a.e(x,42,5,2,'gold')
 elif kind=='bow':
  a.c((33,18),(39,40),1.4,1.4,'leather');a.c((39,40),(33,65),1.4,1.4,'leather');a.line((33,18),(33,65),'cream1',1)
 elif kind in ('book','scroll'):
  a.band([(15,31),(27,28),(39,32),(38,48),(27,45),(15,48)],'cream');a.line((27,29),(27,45),'leather1',1)
  for xx in (18,29):
   for yy in (35,39,43):a.line((xx,yy),(xx+7,yy+1),'leather1',1)
  if kind=='scroll':a.c((16,31),(16,49),2,2,'gold');a.c((39,32),(39,49),2,2,'gold')
 elif kind=='trumpet':
  a.c((18,48),(35,54),2,2,'gold');a.band([(34,50),(34,58),(42,62),(42,46)],'gold')
 elif kind=='flowers':
  a.band([(18,23),(37,23),(35,35),(21,35)],'leather')
  for i in range(5):
   x=20+i*3.4;y=39+i%3*3;a.c((28,31),(x,y),1,1,'leaf');a.e(x,y,3.1,3.4,'cloth');a.dot(x,y,'gold2',2)
 elif kind=='fish':
  a.c((27,43),(27,30),1,1,'cream');a.e(27,27,5,7,'metal');a.band([(24,21),(21,18),(32,18),(30,21)],'metal');a.dot(27,30,'ink',2)
 elif kind=='spool':
  a.c((29,25),(29,57),1,1,'leather');a.e(29,40,5,8,'cream');a.c((23,33),(35,33),1.5,1.5,'gold');a.c((23,47),(35,47),1.5,1.5,'gold')
 elif kind=='satchel':
  a.c((-12,47),(20,23),1.8,1.8,'leather');a.band([(15,16),(31,18),(31,35),(16,34)],'leather');a.band([(16,29),(31,31),(29,36),(17,36)],'gold');a.dot(23,28,'gold2',2)
 elif kind=='lyre':
  a.band([(20,23),(16,49),(23,55),(27,48),(34,54),(40,47),(36,23)],'gold');a.band([(24,30),(22,46),(34,46),(33,30)],'leather')
  for x in (25,28,31):a.line((x,30),(x,47),'cream2',1)
 elif kind=='kite':
  a.line((25,27),(32,69),'cream1',1);a.band([(32,58),(23,69),(32,81),(41,69)],'cloth');a.line((32,59),(32,79),'cream1',1)
 elif kind=='palette':
  a.e(29,33,10,7,'leather')
  for x,y,c in [(23,35,'cloth2'),(29,37,'leaf2'),(35,34,'gold2')]:a.dot(x,y,c,3)
  a.c((23,29),(33,58),1,1,'leather');a.c((33,58),(35,63),1.5,1,'cream')
 elif kind=='saw':
  a.band([(19,29),(36,47),(41,43),(24,25)],'metal')
  for k in range(6):a.band([(22+k*2.8,29+k*2.8),(24+k*2.8,27+k*2.8),(22+k*2.8,25+k*2.8)],'metal')
  a.e(21,27,5,4,'leather')
 elif kind=='reins':
  a.e(30,35,8,13,'leather');a.e(30,35,5,10,'cream');a.c((24,42),(20,30),1.1,1.1,'leather')
 elif kind=='chest':
  a.band([(16,17),(39,17),(39,32),(16,32)],'leather');a.e(27,32,12,5,'leather');a.c((20,18),(20,35),1.5,1.5,'gold');a.c((34,18),(34,35),1.5,1.5,'gold');a.dot(27,27,'gold2',3)
 elif kind in ('pearl','orb','seed','waterjug'):
  a.e(29,y+7,8,9,'cream' if kind=='pearl' else 'glass' if kind in ('orb','waterjug') else 'gold')
  if kind=='seed':a.c((29,y+11),(29,y+23),1,1,'leaf');a.e(25,y+21,5,2,'leaf')
  elif kind=='waterjug':a.c((25,y+14),(25,y+22),2,2,'cream');a.e(36,y+9,5,6,'gold');a.e(36,y+9,3,4,'glass')
  else:a.dot(26,y+12,'shine',3);a.c((22,y-1),(36,y-1),1.5,1.5,'gold')
 elif kind=='grain':
  a.band([(19,20),(37,20),(36,42),(21,42)],'cream')
  for i in range(5):
   x=23+i*3;a.c((x,34),(x-3,57+i%2*3),1,1,'gold');a.e(x-3,53+i%2*3,2,5,'gold')
 elif kind=='fan':
  for i in range(6):
   angle=.25+i*.35;a.band([(22,30),(22+math.cos(angle)*19,30+math.sin(angle)*19),(22+math.cos(angle+.35)*19,30+math.sin(angle+.35)*19)],'cloth');a.line((22,30),(22+math.cos(angle)*19,30+math.sin(angle)*19),'gold2',1)
 elif kind=='key':
  a.c((29,25),(29,57),1.5,1.5,'gold');a.e(29,61,6,6,'gold');a.e(29,61,3,3,'glass');a.c((29,30),(36,30),1.4,1.4,'gold');a.c((36,30),(36,35),1.4,1.4,'gold')
 elif kind=='tablet':
  a.band([(19,27),(37,27),(37,49),(19,49)],'metal')
  for i in range(4):a.line((22,31+i*4),(33,31+i*4),'gold2',1)
 elif kind=='compass':
  a.e(29,43,10,10,'gold');a.e(29,43,7,7,'cream');a.band([(29,51),(32,40),(26,37)],'cloth');a.dot(29,43,'gold2',2)
 elif kind=='bell':
  a.c((30,54),(30,62),1.5,1.5,'leather');a.band([(22,46),(25,54),(35,54),(39,46)],'gold');a.e(30,45,9,2,'gold');a.e(30,43,2,2,'metal')
 elif kind=='telescope':
  a.c((23,36),(38,57),3,3.5,'gold');a.e(39,58,4,4,'glass');a.c((22,37),(19,32),2,2,'leather')

def hair(a,style,hx,hy):
 if style=='shaved':a.e(hx,hy+9,9,3,'hair');return
 if style=='long':
  for s in (-1,1):a.c((hx+s*10,hy+5),(hx+s*12,hy-19),4.4,2,'hair')
 elif style in ('braid','pigtails','ponytail'):
  for s in ((-1,1) if style=='pigtails' else (-1,)):
   for k in range(5):a.e(hx+s*(12+math.sin(k)*2),hy+5-k*5,3.5-k*.3,4,'hair')
 elif style=='curls':
  for k in range(7):a.e(hx+math.cos(k*math.pi/6)*12,hy+math.sin(k*math.pi/6)*10,4,4,'hair')
 a.band([(hx-12,hy+1),(hx-11,hy+11),(hx-2,hy+15),(hx+9,hy+12),(hx+12,hy+3),(hx+5,hy+6),(hx+1,hy+11),(hx-5,hy+5)],'hair')
 if style=='spikes':
  for i in range(4):a.band([(hx-11+i*6,hy+7),(hx-8+i*6,hy+19),(hx-3+i*6,hy+9)],'hair')
 if style=='waves':a.c((hx-8,hy+10),(hx+10,hy+4),3,2,'hair')

def hat(a,kind,hx,hy):
 y=hy+11
 if kind in ('cap','beanie','beret','feather'):
  a.e(hx+(-3 if kind=='beret' else 0),y+2,14,5,'cloth');a.c((hx-12,y-1),(hx+15,y-1),1.8,1.8,'gold')
  if kind=='feather':a.c((hx+8,y+4),(hx+18,y+15),2,1,'cream')
 elif kind=='helm':
  a.band([(hx-13,y-9),(hx-13,y+5),(hx,y+11),(hx+13,y+5),(hx+13,y-9),(hx+8,y-9),(hx+8,y+1),(hx-8,y+1),(hx-8,y-9)],'metal');a.c((hx,y+9),(hx,y+2),1,1,'gold')
 elif kind in ('hood','veil'):
  a.band([(hx-15,hy-13),(hx-15,hy+8),(hx-4,hy+19),(hx+9,hy+15),(hx+15,hy+5),(hx+16,hy-14),(hx+11,hy-12),(hx+10,hy+6),(hx-9,hy+6),(hx-10,hy-13)],'cloth')
  if kind=='veil':a.band([(hx-9,hy-7),(hx+10,hy-7),(hx+12,hy-15),(hx-12,hy-15)],'cream')
 elif kind in ('turban','straw'):
  a.e(hx,y,20 if kind=='straw' else 15,4,'gold' if kind=='straw' else 'cream');a.e(hx,y+4,12,7,'gold' if kind=='straw' else 'cream');a.e(hx+7,y+6,3,3,'glass')
 elif kind=='toque':
  a.band([(hx-10,y-3),(hx+10,y-3),(hx+10,y+6),(hx-10,y+6)],'cream')
  for x in (-7,0,7):a.e(hx+x,y+8,6,5,'cream')
 elif kind=='ribbon':
  a.band([(hx-10,y),(hx-18,y+6),(hx-17,y-3),(hx-8,y-2),(hx-4,y+5),(hx-2,y-2)],'cloth');a.e(hx-9,y,3,3,'gold')
 elif kind in ('circlet','crown'):
  a.c((hx-12,y-2),(hx+12,y-2),1.5,1.5,'gold')
  for x in (-8,0,8):a.band([(hx+x-3,y-1),(hx+x,y+7),(hx+x+3,y-1)],'gold')
 elif kind in ('goggles','band','scarf'):
  a.c((hx-12,y),(hx+12,y),1.8,1.8,'leather')
  if kind=='goggles':
   for x in (-6,6):a.e(hx+x,y,4,3,'metal');a.e(hx+x,y,2,1.8,'glass')
  if kind=='scarf':a.band([(hx-10,hy-14),(hx+12,hy-14),(hx+9,hy-20),(hx-12,hy-18),(-27,hy-28),(-20,hy-19)],'cloth')

def ornament(a,s,hx,hy):
 k=s.get('ornament');y=min(hy+14,76)
 if k in ('leaf','wheat','orchid','mushroom','season'):
  for i in range(3):
   x=hx-9+i*8;a.c((x,y-2),(x,y+5),1,1,'leaf');a.e(x,y+4,4,2,'leaf' if k=='leaf' else 'gold' if k=='wheat' else 'cloth')
  if k=='mushroom':a.e(hx,y+5,16,5,'cloth');a.dot(hx-7,y+7,'cream2',2);a.dot(hx+6,y+6,'cream2',2)
 elif k in ('antler','branches','coral'):
  for side in (-1,1):
   a.c((hx+side*10,y-3),(hx+side*17,y+7),1.4,1,'cream' if k=='antler' else 'leaf' if k=='branches' else 'cloth');a.c((hx+side*14,y+2),(hx+side*20,y+2),1,1,'cream')
 elif k=='wings':
  for side in (-1,1):a.band([(side*10,39),(side*29,56),(side*25,40),(side*33,46),(side*24,30)],'cream')
 elif k=='rope':
  for i in range(5):a.e(-19+i*2,39-i*3,3,4,'gold')
 elif k in ('stars','crystal','rings','gears'):
  a.e(-25,54,8,8,'gold');a.e(-25,54,5,5,'glass')
  if k in ('stars','crystal'):a.band([(-25,67),(-19,55),(-25,45),(-31,55)],'glass')
  if k=='gears':
   for i in range(6):
    angle=i*math.tau/6;a.e(-25+math.cos(angle)*8,54+math.sin(angle)*8,2,2,'gold')
 elif k in ('ribbons','veil'):
  for side in (-1,1):a.band([(side*11,48),(side*23,30),(side*18,12),(side*25,19),(side*28,32),(side*14,53)],'cloth')
 elif k=='shell':a.band([(-21,44),(-30,55),(-33,42),(-23,35)],'cream')
 elif k=='fur':
  for i in range(7):a.e(-15+i*5,43+abs(i-3),4,3,'cream')
 elif k=='slate':a.band([(-22,40),(-26,56),(-17,53),(-12,42)],'metal')
 elif k=='chains':
  for i in range(5):a.e(-20+i*4,49-i*4,3,3,'metal');a.e(-20+i*4,49-i*4,1,1,'leather')

def draw(key,clip,n):
 s=SPECS[key];a=R.Art('npc_'+key,'walk' if clip=='walk' else 'idle',n if clip=='walk' else n%6)
 a.T['lean']=0
 build=s['build'];leg,th,w={'tall':(23,22,11),'broad':(17,22,17),'stocky':(12,23,19),'round':(13,24,20),'curvy':(17,22,14),'lean':(22,19,10),'stooped':(14,22,13),'short':(13,19,13),'child':(10,16,10),'merfolk':(19,21,12)}[build]
 phase=n*math.tau/8;walk=clip=='walk';swing=math.sin(phase)*4 if walk else 0;bob=abs(math.sin(phase))*1.4 if walk else (1-math.cos(n*math.tau/6))*.6
 gesture=(0,2,5,7,4,1)[n%6] if clip=='talk' else 0
 top=leg+th+bob;hx=4 if build=='stooped' else 0;hy=top+10
 if build in ('lean','tall'):a.band([(-w,top-2),(-w-4,12),(-w+4,17),(w+4,12),(w,top-2)],'cloth')
 if s.get('ornament')=='wings':ornament(a,s,hx,hy)
 if build=='merfolk':
  for i in range(6):a.e(math.sin(i*.7+phase*.2)*i,19-i*2.8,11-i*.9,6-i*.5,'glass')
  a.band([(5,5),(18,9),(15,2),(4,2),(-9,5),(-13,12)],'glass')
 else:
  for side in (-1,1):
   footx=side*(w*.43)+side*swing;up=max(0,side*math.sin(phase))*3 if walk else 0
   a.c((side*w*.43,leg),(footx,5+up),3.7,3,'leather');a.e(footx+1,3+up,5,2.6,'leather');a.line((footx-2,4+up),(footx+3,4+up),'gold1',1)
 if build in ('round','stocky'):a.e(0,leg+th*.45,w,th*.7,'cloth')
 else:a.band([(-w,top),(w,top),(w+(5 if build=='curvy' else 1),leg),(0,leg-4),(-w-2,leg)],'cloth')
 if s['name'] in ('smith','baker','innkeeper','carpenter') or s['prop'] in ('hammer','bread','mug','saw'):
  a.band([(-w*.55,top-5),(w*.55,top-5),(w*.7,leg-1),(-w*.7,leg-1)],'leather' if s['prop'] in ('hammer','saw') else 'cream')
 a.c((-w,leg+2),(w,leg+2),1.4,1.4,'gold');a.dot(0,leg+2,'gold2',3)
 right=(w+7,leg+8+(-swing if walk else gesture))
 left=(-(w+7),leg+8+(swing if walk else 0))
 if s['prop']=='satchel':right=(23,28+bob)
 if s['prop'] in SUPPORTS:
  dx,dy=prop_offset(s['prop'],right);sx,sy=SUPPORTS[s['prop']];left=(sx+dx,sy+dy)
 for side,hand in ((-1,left),(1,right)):
  a.c((side*w*.85,top-3),hand,4 if build in ('stocky','broad') else 3.2,2.4,'cloth');a.e(hand[0],hand[1],3.4,3.8,'skin')
 a.c((-5,top),(5,top),2,2,'cream')
 a.e(hx,hy,11.5 if build!='child' else 12,12.5,'skin')
 hair(a,s['hair'],hx,hy)
 a.eye(hx-4.4,hy+.5,2.6);a.eye(hx+5.5,hy+.7,2.7)
 a.line((hx-7,hy+5),(hx-2,hy+5.5),'hair0',1);a.line((hx+3,hy+5.5),(hx+8,hy+5),'hair0',1)
 a.dot(hx-9,hy-4,'blush',2);a.dot(hx+9,hy-4,'blush',2)
 a.line((hx-1,hy-7),(hx+3,hy-7),'mouth',1 if not gesture else 2)
 if s['hair']=='beard':a.band([(hx-9,hy-5),(hx,hy-8),(hx+10,hy-5),(hx+7,hy-16),(hx,hy-20),(hx-7,hy-14)],'hair')
 if build=='stooped':
  for side in (-1,1):a.e(hx+side*5,hy+1,4,3,'gold');a.e(hx+side*5,hy+1,2.5,1.8,'glass')
 hat(a,s['hat'],hx,hy)
 if s.get('ornament')!='wings':ornament(a,s,hx,hy)
 prop(a,s['prop'],right)
 for hand in ([left,right] if s['prop'] in SUPPORTS else [right]):
  a.e(hand[0],hand[1],3.4,3.8,'skin')
  a.line((hand[0]-1,hand[1]+1),(hand[0]+1,hand[1]+1),'skin0',1)
 return a.done()

def selected():return sys.argv[2:] or list(SPECS)
def frames(key):
 return {clip:[draw(key,clip,n) for n in range(count)] for clip,count,fps in CLIPS}
def validate(key,data):
 for clip,rows in data.items():
  for n,grid in enumerate(rows):
   yy,xx=np.nonzero(grid);assert len(xx) and xx.min()>0 and xx.max()<95 and yy.min()>0 and yy.max()<95,(key,clip,n,(xx.min(),xx.max(),yy.min(),yy.max()))
  assert len({x.tobytes() for x in rows})>=3,(key,clip,'static')
 return data

def pf_api():
 sys.path.insert(0,str(Path.home()/'.claude/skills/makesprites'));import pf
 original=pf.api
 def paced(*args,**kwargs):
  for attempt in range(8):
   time.sleep(.16)
   result=original(*args,**kwargs)
   if any(e.get('code')=='rate_limited' for e in result.get('errors',[])):
    print('PixelFlow rate limit: waiting for its request window',flush=True);time.sleep(10);continue
   return result
  raise RuntimeError('PixelFlow request window remains full')
 pf.api=paced;return pf

def metadata(saved):
 clips={};offset=0
 for row,(clip,count,fps) in enumerate(CLIPS):clips[clip]=dict(row=row,n=count,fps=fps,editorStart=offset);offset+=count
 return dict(frame=[96,96],anchor=[48,90],scale=1.4,clips=clips,sprites=saved,designs={k:dict(general=s['general'],name=s['name'],materials={name:PALETTES[k].hex[i] for name,i in PALETTES[k].names.items() if name.startswith(('skin','hair','cloth'))}) for k,s in SPECS.items()},npcs={n['id']:dict(art=n['art'],identity=n['identity'],color=n['color']) for n in PLAN['npcs']})

def preview():
 keys=selected();cols=8;cell=168;sheet=Image.new('RGB',(cols*cell,math.ceil(len(keys)/cols)*170),'#273444');d=ImageDraw.Draw(sheet)
 for i,key in enumerate(keys):
  data=validate(key,frames(key));im=rgba(data['idle'][0],PALETTES[key].hex).resize((144,144),Image.Resampling.NEAREST);x=i%cols*cell;y=i//cols*170;sheet.paste(im,(x+12,y),im);d.text((x+3,y+145),SPECS[key]['name'][:24],fill='#f1e8d0')
 out=ROOT/'test-results/npc-contact.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)

def build():
 api=pf_api();saved=json.loads(MANIFEST.read_text())['sprites'] if MANIFEST.exists() else {}
 existing=api.ids('valhallasc_npc_')
 for key in selected():
  if key in saved:continue
  data=validate(key,frames(key));name='valhallasc_npc_'+key
  sid=existing.get(name) or api.create(name,96,96,20,PALETTES[key].hex,fps=6)
  offset=0
  for clip,count,fps in CLIPS:
   for grid in data[clip]:api.draw_grid(sid,offset,0,grid);offset+=1
  saved[key]=sid;MANIFEST.write_text(json.dumps(metadata(saved),indent=2,ensure_ascii=False)+'\n');print(key,sid,flush=True)

def export(verify=False):
 api=pf_api();manifest=json.loads(MANIFEST.read_text());tops={};bounds={}
 for key in selected():
  sp,data=api.load(manifest['sprites'][key]);assert (sp['width'],sp['height'],len(data))==(96,96,20)
  sheet=Image.new('RGBA',(768,288));offset=0;top=0;box=[96,96,0,0];checked={}
  for row,(clip,count,fps) in enumerate(CLIPS):
   checked[clip]=[]
   for n in range(count):
    grid=data[offset][0];offset+=1;checked[clip].append(grid);ys,xs=np.nonzero(grid);top=max(top,90-int(ys.min()));box=[min(box[0],int(xs.min())),min(box[1],int(ys.min())),max(box[2],int(xs.max()+1)),max(box[3],int(ys.max()+1))];sheet.alpha_composite(Image.fromarray(api.to_rgba(grid,sp['palette'])),(n*96,row*96))
  validate(key,checked);tops[key]=top;bounds[key]=box;target=ASSETS/('npc_'+key+'.png')
  if verify:assert sheet.tobytes()==Image.open(target).convert('RGBA').tobytes(),key
  else:sheet.save(target,optimize=True)
  print(('verified ' if verify else 'exported ')+key,flush=True)
 if not verify:
  manifest['npcs']=metadata(manifest['sprites'])['npcs']
  manifest.setdefault('tops',{}).update(tops);manifest.setdefault('bounds',{}).update(bounds);MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')

def assign():
 manifest=json.loads(MANIFEST.read_text())
 assert set(manifest['sprites'])==set(SPECS), 'Build missing NPC designs before assigning them'
 manifest['npcs']=metadata(manifest['sprites'])['npcs']
 MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
 print(len(manifest['npcs']),'NPC identities assigned; saved artwork preserved')

if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else 'preview'
 {'preview':preview,'build':build,'export':export,'assign':assign,'verify':lambda:export(True)}[command]()
