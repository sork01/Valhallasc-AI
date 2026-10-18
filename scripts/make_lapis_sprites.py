#!/usr/bin/env python3
"""Eleven editable PixelFlow atlases for the Lapis Erg; preview/build/export/verify."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import make_moonspore_sprites as m
import lapis_cel_redraw as cel
from make_crag_sprites import Palette,ellipsoid,polygon,gradient
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'client/assets'
KINDS=['sandhopper','dunefennec','glassscorpion','sunvulture','dunecolossus','mirageroc','lapis_keeper','lapis_cartographer','lapis_warden','lapis_seer','lapis_travel']
RAMPS={
 'sandhopper':('#514039','#8b6446','#ca9958','#edca82','#f8eab5','#5ca9a3'),
 'dunefennec':('#493c3b','#9c6b52','#d6a278','#f4d5a3','#fff0cc','#73b9b5'),
 'glassscorpion':('#263f52','#3b7d8a','#71bed0','#c7e7df','#f6e6bd','#e3a354'),
 'sunvulture':('#4a3947','#906f67','#c69b76','#ecd5a1','#fff0bb','#68b6bf'),
 'dunecolossus':('#55434d','#966f5a','#d2a274','#ecd1a0','#f8e6b6','#4eaeb3'),
 'mirageroc':('#30485b','#5e8893','#8dc3c6','#e9dfbb','#fff0c1','#dfa25f'),
 'lapis_keeper':('#3a4b57','#4a7b85','#76b6b9','#ddc9a4','#fff1c8','#e1a960'),
 'lapis_cartographer':('#3b4458','#667486','#9e9ba0','#ddc9a4','#fff1ca','#e3b75a'),
 'lapis_warden':('#4a4654','#937b69','#c6a37a','#e8cf9f','#fff1c7','#69b7b6'),
 'lapis_seer':('#38465b','#60789d','#8ea7bb','#dfd1b8','#fff3ce','#e6bd77'),
 'lapis_travel':('#334a57','#4d919b','#80c4c0','#ddc9a5','#fff2ca','#e5aa67'),
}
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],glow=v[4],accent=v[5],dark='#222a35',white='#fff9e7')) for k,v in RAMPS.items()}
def paint(f,shape,colors=('ink','shadow','body','light')):
 if isinstance(shape,np.ndarray):shape=gradient(shape,12,6,85,84)
 f.paint(shape,f.p.ramp(*colors),dither=.1)
def line(f,a,b,c='body',w=3):f.line(a,b,'ol',w+2);f.line(a,b,c,w)
def eye(f,x,y):paint(f,ellipsoid(x,y,3,3),('dark','ink','shadow'));f.dots([(x-1,y-1)],'white')
def hopper(f,x,y,s,hit):
 for side in [-1,1]:
  line(f,(x+side*13,y+59),(x+side*29,y+45+s),'shadow',5)
  line(f,(x+side*29,y+45+s),(x+side*35,y+82),'body',5)
  line(f,(x+side*35,y+82),(x+side*42,y+84),'light',3)
  line(f,(x+side*13,y+58),(x+side*18,y+81),'body',4)
 paint(f,ellipsoid(x,y+56,23,17));paint(f,ellipsoid(x+19,y+37,12,11),('shadow','body','light','glow'))
 for side in [-1,1]:line(f,(x+19+side*5,y+28),(x+19+side*12,y+9),'accent',2)
 eye(f,x+25,y+38)
 if hit:line(f,(x+25,y+55),(x+39,y+44),'accent',3)
def fennec(f,x,y,s,hit):
 line(f,(x-24,y+61),(x-40,y+47+s),'body',10)
 paint(f,ellipsoid(x-39,y+43+s,10,11),('shadow','light','glow'))
 for xx in [-17,-3,16,29]:line(f,(x+xx,y+65),(x+xx+s,y+83),'shadow',5)
 paint(f,ellipsoid(x,y+55,27,17));paint(f,ellipsoid(x+22,y+36,15,13),('shadow','body','light','glow'))
 for side in [-1,1]:
  paint(f,polygon([(x+21+side*8,y+31),(x+21+side*13,y+6),(x+23+side*17,y+31)]),('ink','accent','light'))
 eye(f,x+28,y+36)
 if hit:line(f,(x+33,y+46),(x+43,y+51),'accent',2)
def scorpion(f,x,y,s,hit):
 for side in [-1,1]:
  for j in range(3):line(f,(x+side*(8+j*7),y+58),(x+side*(18+j*7),y+78+j%2*4),'shadow',3)
  line(f,(x+side*15,y+48),(x+side*31,y+38),'body',6)
  paint(f,polygon([(x+side*28,y+37),(x+side*42,y+29),(x+side*40,y+41)]),('shadow','body','glow'))
 paint(f,ellipsoid(x,y+59,25,15));paint(f,ellipsoid(x-15,y+48,15,13),('shadow','body','light','glow'))
 line(f,(x+21,y+54),(x+35,y+47+s),'body',8)
 line(f,(x+35,y+47+s),(x+36,y+21+s),'light',7)
 paint(f,polygon([(x+31,y+20+s),(x+39,y+14+s),(x+42,y+26+s)]),('ink','accent','glow'))
 eye(f,x-22,y+46)
def vulture(f,x,y,s,hit):
 for side in [-1,1]:
  paint(f,polygon([(x+side*5,y+43),(x+side*(34+s),y+19),(x+side*41,y+49),(x+side*19,y+60)]),('ink','shadow','body','light'))
  for j in range(3):line(f,(x+side*(22+j*5),y+46),(x+side*(27+j*5),y+60),'light',2)
  line(f,(x+side*7,y+64),(x+side*7,y+82),'shadow',4)
 paint(f,ellipsoid(x,y+52,15,21));paint(f,ellipsoid(x+5,y+28,10,11),('shadow','body','light','glow'))
 paint(f,polygon([(x+12,y+30),(x+25,y+34),(x+16,y+40)]),('ink','accent','light'))
 eye(f,x+8,y+27)
def colossus(f,x,y,s,hit):
 for side in [-1,1]:
  line(f,(x+side*14,y+56),(x+side*(18+s),y+81),'shadow',11)
  line(f,(x+side*25,y+38),(x+side*(35 if hit else 30),y+72),'body',12)
  paint(f,ellipsoid(x+side*(35 if hit else 30),y+74,8,8),('ink','shadow','light'))
 paint(f,polygon([(x-25,y+33),(x+25,y+33),(x+19,y+66),(x-19,y+66)]))
 for xx in [-12,0,12]:line(f,(x+xx,y+39),(x+xx-5,y+57),'accent',2)
 paint(f,ellipsoid(x,y+19,18,16),('shadow','body','light','glow'))
 for side in [-1,1]:paint(f,polygon([(x+side*16,y+18),(x+side*28,y+6),(x+side*26,y+31)]),('ink','body','light'))
 eye(f,x-6,y+19);eye(f,x+6,y+19)
def roc(f,x,y,s,hit):
 for side in [-1,1]:
  paint(f,polygon([(x+side*8,y+42),(x+side*(27+s),y+8),(x+side*40,y+20),(x+side*28,y+54),(x+side*12,y+61)]),('ink','shadow','body','light'))
  for j in range(3):line(f,(x+side*(26+j*5),y+43),(x+side*(32+j*4),y+67),'accent',2)
  line(f,(x+side*8,y+62),(x+side*11,y+82),'shadow',5)
 paint(f,ellipsoid(x,y+51,19,25));paint(f,ellipsoid(x+7,y+25,13,15),('shadow','body','light','glow'))
 paint(f,polygon([(x+15,y+27),(x+39,y+37),(x+18,y+41)]),('ink','accent','light'))
 for j in [-1,0,1]:line(f,(x+j*5,y+16),(x+j*8,y+4),'accent',2)
 eye(f,x+11,y+25)
def person(f,x,y,s,hit,role):
 for side in [-1,1]:line(f,(x+side*8,y+62),(x+side*(9+s),y+83),'shadow',6)
 paint(f,polygon([(x-18,y+34),(x+18,y+34),(x+23,y+74),(x-23,y+74)]))
 paint(f,ellipsoid(x,y+23,12,13),('shadow','light','glow'));eye(f,x+4,y+22)
 if role=='keeper':
  paint(f,polygon([(x-23,y+14),(x,y+4),(x+23,y+14),(x+16,y+23),(x-16,y+23)]),('shadow','body','accent'))
  line(f,(x-27,y+69),(x-27,y+15),'accent',4);paint(f,ellipsoid(x-27,y+16,7,8),('accent','glow'))
 elif role=='cartographer':
  paint(f,polygon([(x-21,y+14),(x,y+5),(x+21,y+14)]),('shadow','body','accent'))
  line(f,(x+27,y+71),(x+27,y+12),'accent',3);paint(f,ellipsoid(x+27,y+11,8,8),('accent','glow'))
  paint(f,polygon([(x+12,y+48),(x+31,y+42),(x+29,y+62),(x+14,y+66)]),('shadow','accent','glow'))
 elif role=='warden':
  paint(f,polygon([(x-25,y+13),(x,y+2),(x+25,y+13),(x+17,y+21),(x-17,y+21)]),('shadow','body','accent'))
  for side in [-1,1]:line(f,(x+side*20,y+45),(x+side*28,y+74),'accent',5)
 elif role=='seer':
  paint(f,polygon([(x-19,y+16),(x,y+1),(x+19,y+16)]),('shadow','body','accent'))
  line(f,(x+24,y+67),(x+24,y+9),'accent',4);paint(f,ellipsoid(x+24,y+7,9,11),('accent','glow'))
  for side in [-1,1]:line(f,(x+side*20,y+48),(x+side*29,y+63),'light',3)
 else:
  paint(f,polygon([(x-25,y+14),(x+25,y+14),(x+16,y+4),(x-16,y+4)]),('shadow','accent','glow'))
  line(f,(x+27,y+70),(x+27,y+12),'accent',4)
  paint(f,polygon([(x+26,y+12),(x+42,y+25),(x+26,y+32)]),('accent','light','glow'))
DRAWERS=dict(sandhopper=hopper,dunefennec=fennec,glassscorpion=scorpion,sunvulture=vulture,dunecolossus=colossus,mirageroc=roc,
             lapis_keeper=lambda f,x,y,s,h:person(f,x,y,s,h,'keeper'),lapis_cartographer=lambda f,x,y,s,h:person(f,x,y,s,h,'cartographer'),
             lapis_warden=lambda f,x,y,s,h:person(f,x,y,s,h,'warden'),lapis_seer=lambda f,x,y,s,h:person(f,x,y,s,h,'seer'),lapis_travel=lambda f,x,y,s,h:person(f,x,y,s,h,'travel'))
# The six enemies are the cel-shaded redraw in lapis_cel_redraw.py (2026-10-18). The NPCs keep the old drawers above, so
# `m._old_draw` (the pre-redraw Frame pipeline) still serves them.
PALETTES.update(cel.PALETTES)
m.KINDS=KINDS;m.PALETTES=PALETTES;m.DRAWERS=DRAWERS;m.ROOT=ROOT;m.ASSETS=ASSETS
from make_crag_sprites import rgba
m.draw=lambda kind,clip,n:rgba(cel.draw(kind,clip,n),PALETTES[kind].hex) if kind in cel.KINDS else m._old_draw(kind,clip,n)

def metadata(sprites):
 meta=m.metadata(sprites);meta['kinds']=KINDS;return meta
def preview():
 for kind in KINDS:m.grids(kind)
 sheet=Image.new('RGB',(len(KINDS)*205+12,4*220+40),'#384a4b');d=ImageDraw.Draw(sheet)
 for col,kind in enumerate(KINDS):
  for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
   pose=m.draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
   sheet.paste(pose,(10+col*205,28+row*220),pose)
   d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#fff2d3')
 out=ROOT/'test-results/lapis-cast.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
def build(replace=False):
 path=ASSETS/'lapis.txt'
 api=m._pf();sprites={};kinds=KINDS
 if path.exists():
  if not replace:raise SystemExit('Lapis sprites already exist; export preserves edits. build --replace redoes the redrawn enemies only.')
  sprites=json.loads(path.read_text())['sprites'];kinds=list(cel.KINDS)
  for kind in kinds:assert api.api('delete',{'sprite_id':sprites.pop(kind)}).get('ok')
 for kind in kinds:
  data=m.grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'lapis_{kind}_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
  sid=api.create('valhallasc_lapis_'+kind+'_all',96,96,34,PALETTES[kind].hex,fps=10)
  frame=0
  try:
   for clip,count in m.CLIPS:
    for grid in data[clip]:api.draw_grid(sid,frame,0,grid);frame+=1
  except Exception:
   api.api('delete',{'sprite_id':sid});raise
  sprites[kind]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
  print(kind,sid,flush=True)
def export(verify=False):
 api=m._pf();path=ASSETS/'lapis.txt';sprites=json.loads(path.read_text())['sprites']
 for kind in KINDS:
  sp,frames=api.load(sprites[kind]);assert(sp['width'],sp['height'],len(frames))==(96,96,34)
  out=Image.new('RGBA',(96*8,96*len(m.CLIPS)));offset=0
  for row,(clip,count) in enumerate(m.CLIPS):
   for n in range(count):out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*96,row*96))
   offset+=count
  target=ASSETS/f'lapis_{kind}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),kind
  else:out.save(target,optimize=True);print('exported',kind,flush=True)
 if verify:print('Lapis PixelFlow atlases verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build('--replace' in sys.argv[2:])
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 else:raise SystemExit('preview | build [--replace] | export | verify')
