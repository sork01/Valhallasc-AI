#!/usr/bin/env python3
"""Twenty-four editable PixelFlow cast atlases for the four-season Yearwheel."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import make_moonspore_sprites as m
import yearwheel_cel_redraw as cel
from make_crag_sprites import Palette,ellipsoid,polygon,gradient
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'client/assets'
KINDS=['brooknewt','sundarter','acornmimic','snowstoat','bloomtortoise','petalchimera','rainseraph','glasslion','sunwheel','firephoenix','lanternowl','harvestreaper','ambermantis','rimesaber','snowgiant','longnightwyrm',
 'year_sp_keeper','year_su_keeper','year_au_keeper','year_wi_keeper','year_sp_travel','year_su_travel','year_au_travel','year_wi_travel']
RAMPS={
 'brooknewt':('#224353','#4f8080','#76b69e','#b5dfb2','#ecf5c4','#e6a76f'),
 'sundarter':('#563b32','#a97142','#dda258','#f1d58a','#fff4ba','#e6804f'),
 'acornmimic':('#3b322d','#795641','#aa7952','#d7b079','#f6dda0','#d3844e'),
 'snowstoat':('#354452','#718c9d','#b8d1d8','#f0f1e8','#f9f9f5','#91bdd0'),
 'bloomtortoise':('#294539','#53805d','#85ad78','#cde29b','#f4f0c2','#eda6a0'),
 'petalchimera':('#483952','#936487','#c68ca7','#f1c8bb','#fff2d2','#8edab2'),
 'rainseraph':('#2d4962','#5c8b9f','#91c8cb','#d7f4e4','#f5ffea','#89a9ec'),
 'glasslion':('#5b3c3d','#ae7761','#dfaa7a','#f8d39b','#fff3c9','#e8a7a0'),
 'sunwheel':('#4d3d36','#aa714b','#dba05b','#f5cc79','#fff2ad','#e9754f'),
 'firephoenix':('#52333b','#a75142','#dc7b4b','#f4bb66','#fff2ab','#f26a4c'),
 'lanternowl':('#373447','#655d6b','#a08778','#e0bd88','#fff0b7','#efa869'),
 'harvestreaper':('#40343d','#715360','#a97c69','#d7a36e','#f7d69d','#d48b56'),
 'ambermantis':('#3f3937','#836454','#be8c5c','#dfb477','#f8dfa4','#d9774a'),
 'rimesaber':('#2b4055','#5e839d','#95b5c4','#d6e3df','#fbf6e7','#7ac0d5'),
 'snowgiant':('#304153','#66849a','#9fb9c4','#d9e3e1','#f6f4e8','#8fc4d2'),
 'longnightwyrm':('#222f4f','#3f5c7a','#6a92a4','#a7cfd3','#e2f1e8','#9ab7e9'),
}
for key,pal in {'sp':('#344d41','#688976','#9fc5a1','#dfebbc','#fff6d3','#e8aa9d'),'su':('#624734','#a77c4d','#d6ad6e','#f0d49b','#fff4c7','#ef9870'),'au':('#493743','#92634e','#bc8d65','#dbc19a','#fff0c8','#dc9a68'),'wi':('#314657','#6b8798','#9fbdc7','#dae5e4','#f9f9f5','#95c9d5')}.items():
 RAMPS['year_'+key+'_keeper']=pal;RAMPS['year_'+key+'_travel']=pal
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],glow=v[4],accent=v[5],dark='#182633',white='#ffffff')) for k,v in RAMPS.items()}
def paint(f,shape,colors=('ink','shadow','body','light')):
 if isinstance(shape,np.ndarray):shape=gradient(shape,12,6,85,84)
 f.paint(shape,f.p.ramp(*colors),dither=.1)
def line(f,a,b,c='body',w=3):f.line(a,b,'ol',w+2);f.line(a,b,c,w)
def eye(f,x,y):paint(f,ellipsoid(x,y,3,3),('dark','ink','shadow'));f.dots([(x-1,y-1)],'white')
def legs(f,x,y,s,w=15,n=2):
 for i in range(n):
  # Four feet must emerge from beneath the torso, rather than outside it.
  xx=x+(i-(n-1)/2)*(w if n==2 else w/2)
  toe=xx+s*.3
  line(f,(xx,y+53),(toe,y+87),'shadow',7)
  paint(f,ellipsoid(toe,y+87,6,3),('ink','shadow','body','light'))
def brooknewt(f,x,y,s,h):
 line(f,(x-23,y+59),(x-39,y+69+s),'shadow',8);legs(f,x,y,s,24)
 paint(f,ellipsoid(x-4,y+56,28,12));paint(f,ellipsoid(x+23,y+48,15,11),('shadow','body','light','glow'))
 for j in range(3):paint(f,ellipsoid(x-16+j*12,y+47,3,4),('accent','glow'))
 eye(f,x+29,y+44)
def sundarter(f,x,y,s,h):
 line(f,(x-22,y+65),(x-37,y+78+s),'shadow',6);legs(f,x,y,s,24)
 # One translucent sun sail follows the spine, with an uneven rounded rim.
 paint(f,polygon([(x-23,y+53),(x-24,y+43),(x-19,y+37),(x-15,y+38),
                  (x-11,y+43),(x-7,y+32),(x-3,y+30),(x+1,y+35),
                  (x+4,y+42),(x+9,y+38),(x+13,y+39),(x+18,y+50)]),
       ('ink','shadow','accent','light'))
 for bx,by,tx,ty in [(-19,49,-19,39),(-5,48,-4,34),(9,48,11,40)]:
  line(f,(x+bx,y+by),(x+tx,y+ty),'glow',1)
 paint(f,ellipsoid(x,y+57,26,11));paint(f,ellipsoid(x+24,y+47,11,10),('shadow','body','light','glow'))
 eye(f,x+27,y+45)
def acornmimic(f,x,y,s,h):
 legs(f,x,y,s,20)
 paint(f,ellipsoid(x,y+55,23,27));paint(f,polygon([(x-24,y+35),(x-16,y+23),(x+17,y+23),(x+25,y+35),(x+15,y+43),(x-16,y+43)]),('ink','shadow','accent','light'))
 line(f,(x,y+23),(x+4,y+10),'shadow',4);eye(f,x+9,y+53)
def snowstoat(f,x,y,s,h):
 line(f,(x-23,y+60),(x-38,y+58+s),'light',7);legs(f,x,y,s,20)
 paint(f,ellipsoid(x-4,y+60,29,12));paint(f,ellipsoid(x+24,y+49,13,12),('shadow','body','light','glow'))
 for side in [-1,1]:paint(f,ellipsoid(x+20+side*8,y+38,4,5),('ink','light','glow'))
 eye(f,x+29,y+47)
def bloomtortoise(f,x,y,s,h):
 legs(f,x,y,s,31)
 paint(f,ellipsoid(x-3,y+57,32,21));paint(f,ellipsoid(x+29,y+55,11,10),('shadow','body','light','glow'))
 for j in range(5):
  xx=x-23+j*11;line(f,(xx,y+43),(xx,y+25-j%2*4),'accent',3)
  paint(f,ellipsoid(xx,y+22-j%2*4,6,6),('accent','glow'))
 eye(f,x+32,y+52)
def petalchimera(f,x,y,s,h):
 legs(f,x,y,s,24,4);line(f,(x-25,y+52),(x-35,y+24+s),'accent',7)
 paint(f,ellipsoid(x,y+55,27,18));paint(f,ellipsoid(x+20,y+36,17,18),('shadow','body','light','glow'))
 for j in range(6):
  a=j*6.283/6;paint(f,ellipsoid(x+20+int(np.cos(a)*17),y+36+int(np.sin(a)*18),5,9),('accent','body','light','glow'))
 for side in [-1,1]:
  bx=x+20+side*8
  line(f,(bx,y+30),(bx+side*3,y+16),'shadow',5)
  line(f,(bx+side*3,y+16),(bx+side*11,y+10),'accent',3)
  line(f,(bx+side*2,y+22),(bx-side*5,y+14),'accent',3)
  paint(f,ellipsoid(bx+side*11,y+10,3,4),('shadow','accent','light','glow'))
 eye(f,x+27,y+34)
def rainseraph(f,x,y,s,h):
 for side in [-1,1]:
  paint(f,polygon([(x+side*7,y+40),(x+side*(35+s),y+12),(x+side*29,y+64)]),('ink','shadow','body','light'))
  line(f,(x+side*8,y+62),(x+side*11,y+88),'shadow',6)
  paint(f,ellipsoid(x+side*11,y+88,6,2),('ink','shadow','body','light'))
 paint(f,ellipsoid(x,y+55,15,21));paint(f,ellipsoid(x,y+27,12,13),('shadow','body','light','glow'))
 for j in range(3):line(f,(x-20+j*20,y+37),(x-22+j*20,y+64),'accent',2)
 eye(f,x+5,y+26)
def glasslion(f,x,y,s,h):
 legs(f,x,y,s,26,4);line(f,(x-28,y+53),(x-36,y+29+s),'accent',5)
 paint(f,ellipsoid(x-4,y+55,27,17));paint(f,ellipsoid(x+23,y+39,19,21),('ink','accent','body','light'))
 # Fused-glass curls form a continuous mane around the face.
 for px,py,rx,ry in [(12,27,9,12),(21,19,10,11),(32,20,10,11),(40,30,8,12),
                     (39,45,8,11),(29,53,11,8),(17,52,11,8)]:
  paint(f,ellipsoid(x+px,y+py,rx,ry),('ink','accent','body','light'))
 for px,py in [(15,20),(26,14),(38,23),(40,43)]:
  line(f,(x+px,y+py),(x+px+3,y+py-4),'glow',2)
 paint(f,ellipsoid(x+28,y+38,10,10),('shadow','body','light','glow'));eye(f,x+32,y+35)
def sunwheel(f,x,y,s,h):
 legs(f,x,y,s,28)
 paint(f,ellipsoid(x,y+48,31,30),('ink','shadow','accent','glow'));paint(f,ellipsoid(x,y+48,21,20),('shadow','body','light','glow'))
 for j in range(8):
  a=j*6.283/8;line(f,(x+int(np.cos(a)*21),y+48+int(np.sin(a)*20)),(x+int(np.cos(a)*31),y+48+int(np.sin(a)*30)),'accent',4)
 eye(f,x+7,y+45)
def firephoenix(f,x,y,s,h):
 for side in [-1,1]:paint(f,polygon([(x+side*8,y+48),(x+side*(34+s),y+13),(x+side*29,y+50),(x+side*13,y+64)]),('ink','accent','body','glow'))
 paint(f,ellipsoid(x,y+52,16,22));paint(f,ellipsoid(x+10,y+31,11,11),('shadow','body','light','glow'))
 for j in range(3):paint(f,polygon([(x-11+j*11,y+70),(x-17+j*11,y+85),(x-5+j*11,y+78)]),('ink','accent','glow'))
 for side in [-1,1]:
  line(f,(x+side*7,y+67),(x+side*10,y+87),'shadow',5)
  paint(f,ellipsoid(x+side*10,y+88,6,2),('ink','shadow','accent','light'))
 paint(f,polygon([(x+17,y+29),(x+33,y+35),(x+16,y+40)]),('ink','accent','glow'));eye(f,x+12,y+28)
def lanternowl(f,x,y,s,h):
 for side in [-1,1]:paint(f,polygon([(x+side*13,y+42),(x+side*32,y+30+s),(x+side*24,y+69)]),('ink','shadow','body','light'))
 paint(f,ellipsoid(x,y+52,25,27));
 for side in [-1,1]:
  paint(f,ellipsoid(x+side*10,y+37,10,12),('shadow','light','glow'))
  eye(f,x+side*10,y+36)
 for side in [-1,1]:
  paint(f,polygon([(x+side*8,y+29),(x+side*17,y+19),(x+side*23,y+13),(x+side*22,y+28),(x+side*17,y+35)]),('ink','shadow','accent','light'))
  line(f,(x+side*14,y+29),(x+side*21,y+18),'light',2)
 paint(f,polygon([(x-5,y+49),(x+5,y+49),(x,y+57)]),('ink','accent','glow'))
 for side in [-1,1]:
  line(f,(x+side*9,y+67),(x+side*10,y+88),'shadow',5)
  paint(f,ellipsoid(x+side*10,y+88,6,2),('ink','shadow','accent','light'))
def harvestreaper(f,x,y,s,h):
 legs(f,x,y,s,16);paint(f,polygon([(x-20,y+36),(x+20,y+36),(x+27,y+76),(x-27,y+76)]))
 paint(f,ellipsoid(x,y+25,14,14),('shadow','body','light','glow'))
 line(f,(x+25,y+70),(x+27,y+8),'shadow',4)
 line(f,(x+27,y+8),(x+41,y+9),'accent',4)
 line(f,(x+41,y+9),(x+31,y+24),'light',3)
 for side in [-1,1]:line(f,(x+side*18,y+45),(x+side*29,y+59),'shadow',6)
 eye(f,x+5,y+25)
def ambermantis(f,x,y,s,h):
 legs(f,x,y,s,14);paint(f,ellipsoid(x,y+55,15,25));paint(f,ellipsoid(x,y+28,16,13),('shadow','body','light','glow'))
 for side in [-1,1]:
  line(f,(x+side*15,y+42),(x+side*33,y+30+s),'accent',7)
  line(f,(x+side*33,y+30+s),(x+side*39,y+54),'light',5)
  # Jointed antennae are rooted in the head, with light catching their tips.
  line(f,(x+side*9,y+23),(x+side*13,y+16),'shadow',4)
  line(f,(x+side*13,y+16),(x+side*25,y+10),'accent',3)
  paint(f,ellipsoid(x+side*25,y+10,3,3),('shadow','accent','light','glow'))
 eye(f,x+7,y+26)
def rimesaber(f,x,y,s,h):
 legs(f,x,y,s,26,4);line(f,(x-27,y+52),(x-38,y+35+s),'shadow',6)
 paint(f,ellipsoid(x-3,y+55,27,17));paint(f,ellipsoid(x+24,y+39,17,18),('shadow','body','light','glow'))
 # Forked ice antlers rise from the skull; each tine joins a thicker beam.
 for side in [-1,1]:
  bx=x+24+side*9
  line(f,(bx,y+29),(bx+side*4,y+18),'shadow',6)
  line(f,(bx+side*4,y+18),(bx+side*12,y+10),'body',4)
  line(f,(bx+side*3,y+21),(bx-side*4,y+13),'light',3)
  line(f,(bx+side*9,y+13),(bx+side*10,y+5),'light',2)
 for side in [-1,1]:line(f,(x+24+side*6,y+43),(x+23+side*6,y+61),'glow',4)
 eye(f,x+29,y+36)
def snowgiant(f,x,y,s,h):
 legs(f,x,y,s,25)
 for side in [-1,1]:line(f,(x+side*20,y+35),(x+side*32,y+65+s),'shadow',12)
 paint(f,ellipsoid(x,y+52,28,26));paint(f,ellipsoid(x,y+27,19,18),('shadow','body','light','glow'))
 # Heavy swept horns and a broad brow keep the giant's face readable.
 for side in [-1,1]:
  line(f,(x+side*15,y+31),(x+side*26,y+21),'shadow',10)
  line(f,(x+side*26,y+21),(x+side*27,y+11),'body',7)
  paint(f,ellipsoid(x+side*27,y+11,4,5),('ink','shadow','light','glow'))
  line(f,(x+side*17,y+26),(x+side*25,y+19),'glow',2)
 paint(f,ellipsoid(x,y+18,15,7),('ink','shadow','body','light'))
 eye(f,x+8,y+24)
def longnightwyrm(f,x,y,s,h):
 # The dorsal membrane is one scalloped sail rooted along the whole back.
 paint(f,polygon([(x-36,y+70),(x-35,y+59),(x-33,y+54),(x-29,y+52),
                  (x-25,y+55),(x-21,y+49),(x-18,y+47),(x-14,y+48),
                  (x-10,y+54),(x-4,y+45),(x,y+44),(x+4,y+48),
                  (x+9,y+45),(x+12,y+39),(x+16,y+38),(x+20,y+47),
                  (x+19,y+65),(x+7,y+73),(x-12,y+74)]),
       ('ink','shadow','accent','light'))
 for bx,by,tx,ty in [(-28,64,-29,54),(-15,63,-18,49),(-1,64,0,47),(13,55,14,41)]:
  line(f,(x+bx,y+by),(x+tx,y+ty),'light',2)
 line(f,(x-33,y+70),(x-17,y+54+s),'shadow',13);line(f,(x-17,y+54+s),(x+3,y+66),'body',15)
 line(f,(x+3,y+66),(x+22,y+41),'shadow',16);paint(f,ellipsoid(x+22,y+35,16,15),('shadow','body','light','glow'))
 paint(f,ellipsoid(x-5,y+78,18,12),('ink','shadow','body','light'))
 for side in [-1,1]:
  line(f,(x+22+side*8,y+27),(x+20+side*11,y+15),'shadow',5)
  line(f,(x+20+side*11,y+15),(x+15+side*15,y+9),'accent',3)
  line(f,(x+20+side*11,y+16),(x+24+side*10,y+11),'light',2)
 eye(f,x+27,y+34)
def person(f,x,y,s,h,season,travel):
 legs(f,x,y,s,18)
 paint(f,polygon([(x-19,y+36),(x+19,y+36),(x+24,y+74),(x-24,y+74)]))
 for side in [-1,1]:line(f,(x+side*18,y+43),(x+side*25,y+67),'body',7)
 paint(f,ellipsoid(x,y+25,12,14),('shadow','light','glow'));eye(f,x+5,y+24)
 if travel:
  paint(f,polygon([(x-25,y+10),(x,y+0),(x+24,y+10),(x+18,y+20),(x-18,y+20)]),('ink','accent','light'))
  line(f,(x+28,y+73),(x+28,y+9),'accent',4)
  paint(f,polygon([(x+28,y+9),(x+41,y+22),(x+28,y+34)]),('accent','light','glow'))
 else:
  paint(f,polygon([(x-22,y+12),(x-13,y+1),(x+14,y+1),(x+22,y+12)]),('ink','body','light'))
  if season=='sp':paint(f,ellipsoid(x-29,y+55,8,11),('accent','glow'))
  elif season=='su':paint(f,ellipsoid(x+28,y+17,8,8),('accent','glow'))
  elif season=='au':line(f,(x-27,y+70),(x-27,y+10),'accent',5)
  else:paint(f,polygon([(x+24,y+50),(x+35,y+41),(x+31,y+62)]),('accent','light','glow'))
DRAWERS={k:v for k,v in locals().copy().items() if k in KINDS and callable(v)}
for season in ['sp','su','au','wi']:
 DRAWERS['year_'+season+'_keeper']=lambda f,x,y,s,h,key=season:person(f,x,y,s,h,key,False)
 DRAWERS['year_'+season+'_travel']=lambda f,x,y,s,h,key=season:person(f,x,y,s,h,key,True)
# The sixteen creatures are the cel-shaded redraw in yearwheel_cel_redraw.py (2026-10-18). The eight year_* NPCs keep the old
# drawers above, so `m._old_draw` (the pre-redraw Frame pipeline) still serves them.
PALETTES.update(cel.PALETTES)
m.KINDS=KINDS;m.PALETTES=PALETTES;m.DRAWERS=DRAWERS;m.ROOT=ROOT;m.ASSETS=ASSETS
from make_crag_sprites import rgba
m.draw=lambda kind,clip,n:rgba(cel.draw(kind,clip,n),PALETTES[kind].hex) if kind in cel.KINDS else m._old_draw(kind,clip,n)
# Keep the contact feet at the atlas anchor through walk and attack frames.
_base_pose=m.pose
def grounded_pose(clip,n):
 dx,_,sway=_base_pose(clip,n)
 if clip=='walk' and n==6:sway-=2
 if clip=='walk' and n==7:dx,sway=1,2
 return dx,0,sway
m.pose=grounded_pose
def metadata(sprites):
 meta=m.metadata(sprites);meta['kinds']=KINDS;return meta
def preview():
 sheet=Image.new('RGB',(8*205+12,3*220+40),'#303c4a');d=ImageDraw.Draw(sheet)
 for i,kind in enumerate(KINDS):
  col,row=i%8,i//8
  pose=m.draw(kind,'idle',2).resize((192,192),Image.Resampling.NEAREST)
  sheet.paste(pose,(10+col*205,28+row*220),pose)
  d.text((10+col*205,8+row*220),kind,fill='#f5e8cd')
 out=ROOT/'test-results/yearwheel-cast.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
def build(replace=False):
 path=ASSETS/'yearwheel.txt'
 import time
 api=m._pf();sprites={};kinds=KINDS
 if path.exists():
  sprites=json.loads(path.read_text())['sprites']
  if replace:
   kinds=list(cel.KINDS)
   for kind in kinds:
    if kind in sprites:assert api.api('delete',{'sprite_id':sprites.pop(kind)}).get('ok')
 for kind in kinds:
  if kind in sprites:continue
  data=m.grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'yearwheel_{kind}_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
  sid=api.create('valhallasc_yearwheel_'+kind+'_all',96,96,34,PALETTES[kind].hex,fps=10)
  frame=0
  try:
   for clip,count in m.CLIPS:
    for grid in data[clip]:
     api.draw_grid(sid,frame,0,grid);frame+=1;time.sleep(.13)
  except Exception:
   api.api('delete',{'sprite_id':sid});raise
  sprites[kind]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
  print(kind,sid,flush=True)
def export(verify=False):
 api=m._pf();path=ASSETS/'yearwheel.txt';sprites=json.loads(path.read_text())['sprites']
 for kind in KINDS:
  sp,frames=api.load(sprites[kind]);assert(sp['width'],sp['height'],len(frames))==(96,96,34)
  out=Image.new('RGBA',(96*8,96*len(m.CLIPS)));offset=0
  for row,(clip,count) in enumerate(m.CLIPS):
   for n in range(count):out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*96,row*96))
   offset+=count
  target=ASSETS/f'yearwheel_{kind}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),kind
  else:out.save(target,optimize=True);print('exported',kind,flush=True)
 if verify:print('Yearwheel PixelFlow atlases verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
def repair(kinds=None):
 import time
 api=m._pf();sprites=json.loads((ASSETS/'yearwheel.txt').read_text())['sprites']
 kinds=kinds or KINDS[:16]
 if any(kind not in KINDS[:16] for kind in kinds):raise ValueError('repair accepts creature kinds only')
 for kind in kinds:
  data=m.grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'yearwheel_{kind}_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
  frame=0
  for clip,count in m.CLIPS:
   for grid in data[clip]:
    api.draw_grid(sprites[kind],frame,0,grid);frame+=1;time.sleep(.14)
  print('repaired',kind,flush=True)
 export()
if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build('--replace' in sys.argv[2:])
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 elif cmd=='repair':repair(sys.argv[2:] or None)
 else:raise SystemExit('preview | build [--replace] | export | verify | repair [creature kinds...]')
