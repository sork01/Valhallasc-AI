#!/usr/bin/env python3
"""Nine editable 34-frame PixelFlow sprites for The Ribbonwild."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import make_moonspore_sprites as m
import ribbonwild_cel_redraw as cel
from make_crag_sprites import Palette, ellipsoid, polygon, gradient, rgba

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
KINDS=['ribbongecko','balloonbeetle','paintedmacaw','jesterling',
       'paradegryphon','maskcolossus','ribbon_host','ribbon_keeper','ribbon_travel']
RAMPS={
 'ribbongecko':('#263850','#237d9b','#31c7bd','#93eee2','#fff3ad','#f165aa'),
 'balloonbeetle':('#3d3158','#8056a8','#b277db','#e7a2f3','#fff0b5','#f2ca53'),
 'paintedmacaw':('#303453','#345dba','#52bbdf','#f3d75d','#fff4cf','#ef5d8c'),
 'jesterling':('#423052','#9b4ab2','#d36ab3','#f4bf78','#fff4c8','#65d1aa'),
 'paradegryphon':('#383548','#8753a0','#bc7cba','#f7bb72','#fff3ba','#67c8d9'),
 'maskcolossus':('#34324d','#7364b1','#ae94dc','#f5d48a','#fff5c8','#e96c9c'),
 'ribbon_host':('#3c3550','#9c557f','#e476a3','#f5c481','#fff3d1','#6cc9b6'),
 'ribbon_keeper':('#343956','#686dc0','#a094df','#e8c899','#fff0d0','#ee77a8'),
 'ribbon_travel':('#30435a','#4e9abb','#75d7ca','#e9ce79','#fff5cf','#ed7bb7'),
}
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],
                          glow=v[4],accent=v[5],dark='#1c2430',white='#fffbea'))
          for k,v in RAMPS.items()}


def paint(f,shape,colors=('ink','shadow','body','light')):
 if isinstance(shape,np.ndarray):shape=gradient(shape,12,6,85,84)
 f.paint(shape,f.p.ramp(*colors),dither=.1)


def line(f,a,b,color='body',width=3):
 f.line(a,b,'ol',width+2);f.line(a,b,color,width)


def eye(f,x,y):
 paint(f,ellipsoid(x,y,3,3),('dark','ink','shadow'))
 f.dots([(x-1,y-1)],'white')


def gecko(f,x,y,s,hit):
 # Low reptile, long curled streamer tail and splayed toes.
 line(f,(x-22,y+63),(x-39,y+49+s),'accent',8)
 line(f,(x-39,y+49+s),(x-36,y+31+s),'accent',6)
 paint(f,ellipsoid(x-3,y+60,29,13))
 for xx in (-18,-5,15,24):
  line(f,(x+xx,y+68),(x+xx+s,y+82),'shadow',4)
  for j in (-1,1):line(f,(x+xx+s,y+82),(x+xx+s+j*5,y+84),'glow',1)
 paint(f,ellipsoid(x+25,y+52,14,11))
 paint(f,ellipsoid(x+35,y+56,10,5),('shadow','body','light','glow'))
 eye(f,x+25,y+45)
 for i in range(4):paint(f,ellipsoid(x-19+i*12,y+52,3,5),('accent','accent','glow'))
 if hit:line(f,(x+34,y+58),(x+45,y+61),'accent',2)


def beetle(f,x,y,s,hit):
 # A round beetle hangs beneath two buoyant silk balloons.
 for side in (-1,1):
  line(f,(x+side*10,y+55),(x+side*(22+s),y+21),'light',2)
  paint(f,ellipsoid(x+side*23,y+19,14,16),('shadow','body','light','glow'))
  line(f,(x+side*21,y+8),(x+side*27,y+4),'accent',2)
 for xx in (-19,-9,10,19):line(f,(x+xx,y+66),(x+xx+s,y+79),'shadow',4)
 paint(f,ellipsoid(x,y+60,28,18))
 paint(f,ellipsoid(x,y+54,24,14),('accent','body','light','glow'))
 line(f,(x,y+42),(x,y+66),'accent',2)
 paint(f,ellipsoid(x+23,y+64,8,7))
 eye(f,x+26,y+61)
 if hit:line(f,(x-31,y+57),(x-42,y+48),'glow',2)


def macaw(f,x,y,s,hit):
 # Broad asymmetric wings, pointed tail and strong hooked beak.
 for side in (-1,1):
  wing=polygon([(x+side*9,y+44),(x+side*(33+s),y+14),
                (x+side*43,y+42),(x+side*28,y+62)])
  paint(f,wing,('ink','shadow','accent','light'))
  for j in range(3):line(f,(x+side*(24+j*6),y+38),(x+side*(29+j*4),y+52),'glow',2)
 for j in (-1,0,1):line(f,(x+j*5,y+67),(x+j*10,y+85),'accent',3)
 paint(f,ellipsoid(x,y+53,15,23))
 paint(f,ellipsoid(x+5,y+28,13,12))
 paint(f,polygon([(x+13,y+31),(x+29,y+36),(x+20,y+47),(x+12,y+40)]),('ink','accent','light'))
 eye(f,x+8,y+26)
 for j in range(3):line(f,(x-5+j*5,y+18),(x-9+j*5,y+8),'accent',2)


def jester(f,x,y,s,hit):
 # Small masked performer with a zigzag cap and three floating juggling balls.
 for side in (-1,1):line(f,(x+side*8,y+63),(x+side*(10+s),y+84),'shadow',6)
 paint(f,polygon([(x-19,y+37),(x+19,y+37),(x+26,y+72),(x-25,y+72)]))
 for side in (-1,1):line(f,(x+side*17,y+45),(x+side*(31 if hit else 26),y+57),'accent',5)
 paint(f,ellipsoid(x,y+25,14,13),('ink','shadow','light','glow'))
 eye(f,x-5,y+25);eye(f,x+5,y+25)
 paint(f,polygon([(x-24,y+18),(x-18,y+3),(x-5,y+15),(x+9,y+1),
                  (x+25,y+18),(x+10,y+13),(x-6,y+20)]),('shadow','accent','light','glow'))
 for bx,by in [(-31,34),(31,28),(38,53)]:
  paint(f,ellipsoid(x+bx,y+by+s%3,5,5),('accent','light','glow'))


def gryphon(f,x,y,s,hit):
 # Four-legged beast, eagle head, giant fanned wings and a feather tail.
 line(f,(x-25,y+56),(x-42,y+34+s),'accent',8)
 for side in (-1,1):
  wing=polygon([(x+side*5,y+52),(x+side*(33+s),y+10),
                (x+side*43,y+30),(x+side*23,y+63)])
  paint(f,wing,('ink','shadow','accent','light'))
  for j in range(3):line(f,(x+side*(28+j*4),y+27),(x+side*(38+j*2),y+42),'glow',2)
 paint(f,ellipsoid(x-4,y+64,29,16))
 for xx in (-22,-9,16,25):line(f,(x+xx,y+70),(x+xx+s,y+84),'shadow',6)
 paint(f,ellipsoid(x+24,y+44,14,15))
 paint(f,polygon([(x+27,y+47),(x+43,y+51),(x+30,y+59)]),('ink','accent','glow'))
 eye(f,x+28,y+38)
 for j in range(4):line(f,(x+12+j*5,y+31),(x+13+j*6,y+9+j%2*4),'accent',3)


def colossus(f,x,y,s,hit):
 # Huge upright carnival mask on stilts, crowned by a fan of silk panels.
 for side in (-1,1):
  line(f,(x+side*16,y+61),(x+side*(19+s),y+84),'shadow',9)
  line(f,(x+side*19,y+43),(x+side*(38 if hit else 32),y+64),'body',10)
  paint(f,ellipsoid(x+side*37,y+65,7,8),('accent','light','glow'))
 paint(f,polygon([(x-25,y+36),(x+25,y+36),(x+28,y+72),(x-27,y+72)]))
 for j in (-1,0,1):line(f,(x+j*13,y+43),(x+j*12+4,y+72),'accent',3)
 paint(f,ellipsoid(x,y+25,19,20),('ink','shadow','light','glow'))
 for side in (-1,1):paint(f,ellipsoid(x+side*8,y+24,5,4),('ink','shadow','dark'))
 paint(f,polygon([(x-4,y+34),(x+4,y+34),(x,y+39)]),('accent','accent','glow'))
 for j in range(-3,4):
  line(f,(x+j*6,y+7),(x+j*9,y+1+abs(j)*3),'accent',4)
  paint(f,ellipsoid(x+j*9,y+2+abs(j)*3,3,3),('light','glow'))


def person(f,x,y,s,hit,role):
 for side in (-1,1):line(f,(x+side*8,y+66),(x+side*(9+s),y+84),'shadow',6)
 paint(f,polygon([(x-17,y+34),(x+17,y+34),(x+22,y+77),(x-22,y+77)]))
 for j in (-1,0,1):line(f,(x+j*10,y+42),(x+j*11,y+73),'accent',3)
 paint(f,ellipsoid(x,y+23,12,14),('shadow','light','glow'))
 eye(f,x+4,y+22)
 if role=='host':
  paint(f,polygon([(x-23,y+16),(x+22,y+16),(x+15,y+6),(x-15,y+6)]),('accent','light','glow'))
  line(f,(x+19,y+42),(x+34,y+60),'accent',5)
  paint(f,polygon([(x+32,y+59),(x+42,y+39),(x+44,y+66)]),('accent','light','glow'))
 elif role=='keeper':
  paint(f,polygon([(x-17,y+13),(x,y+1),(x+18,y+13)]),('shadow','body','accent'))
  line(f,(x+23,y+73),(x+23,y+8),'accent',4)
  paint(f,ellipsoid(x+23,y+8,8,6),('accent','light','glow'))
 else:
  paint(f,polygon([(x-27,y+13),(x+26,y+13),(x+13,y+5),(x-13,y+5)]),('accent','light','glow'))
  paint(f,ellipsoid(x-22,y+55,11,17))
  line(f,(x+25,y+72),(x+25,y+15),'accent',4)
  paint(f,polygon([(x+24,y+14),(x+42,y+24),(x+24,y+34)]),('accent','light','glow'))


DRAWERS=dict(ribbongecko=gecko,balloonbeetle=beetle,paintedmacaw=macaw,
             jesterling=jester,paradegryphon=gryphon,maskcolossus=colossus,
             ribbon_host=lambda f,x,y,s,h:person(f,x,y,s,h,'host'),
             ribbon_keeper=lambda f,x,y,s,h:person(f,x,y,s,h,'keeper'),
             ribbon_travel=lambda f,x,y,s,h:person(f,x,y,s,h,'travel'))
# The six enemies are the cel-shaded redraw in ribbonwild_cel_redraw.py (2026-10-18). The three NPCs keep the old
# drawers above, so `m._old_draw` (the pre-redraw Frame pipeline) still serves them.
PALETTES.update(cel.PALETTES)
m.KINDS=KINDS;m.PALETTES=PALETTES;m.DRAWERS=DRAWERS;m.ROOT=ROOT;m.ASSETS=ASSETS
m.draw=lambda kind,clip,n:rgba(cel.draw(kind,clip,n),PALETTES[kind].hex) if kind in cel.KINDS else m._old_draw(kind,clip,n)


def metadata(sprites):
 meta=m.metadata(sprites);meta['kinds']=KINDS;return meta


def preview():
 for kind in KINDS:m.grids(kind)
 sheet=Image.new('RGB',(9*205+12,4*220+40),'#28344a');d=ImageDraw.Draw(sheet)
 for col,kind in enumerate(KINDS):
  for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
   pose=m.draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
   sheet.paste(pose,(10+col*205,28+row*220),pose)
   d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#fff2d3')
 out=ROOT/'test-results/ribbonwild-cast.png';out.parent.mkdir(exist_ok=True)
 sheet.save(out);print(out)


def build(replace=False):
 path=ASSETS/'ribbonwild.txt'
 api=m._pf();sprites={};kinds=KINDS
 if path.exists():
  if not replace:raise SystemExit('Ribbonwild sprites already exist; export preserves edits. build --replace redoes the six enemies only.')
  sprites=json.loads(path.read_text())['sprites'];kinds=list(cel.KINDS)
  for kind in kinds:assert api.api('delete',{'sprite_id':sprites.pop(kind)}).get('ok')
 for kind in kinds:
  data=m.grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'ribbonwild_{kind}_raw.npz',
                      **{clip:np.stack(rows) for clip,rows in data.items()})
  sid=api.create('valhallasc_ribbonwild_'+kind+'_all',96,96,34,
                 PALETTES[kind].hex,fps=10)
  frame=0
  try:
   for clip,count in m.CLIPS:
    for grid in data[clip]:api.draw_grid(sid,frame,0,grid);frame+=1
  except Exception:
   api.api('delete',{'sprite_id':sid});raise
  sprites[kind]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
  print(kind,sid,flush=True)


def export(verify=False):
 api=m._pf();path=ASSETS/'ribbonwild.txt'
 sprites=json.loads(path.read_text())['sprites']
 for kind in KINDS:
  sp,frames=api.load(sprites[kind]);assert(sp['width'],sp['height'],len(frames))==(96,96,34)
  out=Image.new('RGBA',(96*8,96*len(m.CLIPS)));offset=0
  for row,(clip,count) in enumerate(m.CLIPS):
   for n in range(count):
    out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*96,row*96))
   offset+=count
  target=ASSETS/f'ribbonwild_{kind}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),kind
  else:out.save(target,optimize=True);print('exported',kind,flush=True)
 if verify:print('Nine PixelFlow sprites and 306 frames verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')


if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build('--replace' in sys.argv[2:])
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 else:raise SystemExit('preview | build [--replace] | export | verify')
