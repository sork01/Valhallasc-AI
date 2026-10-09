#!/usr/bin/env python3
"""Five original Stormglass silhouettes, editable in PixelFlow.

preview checks all 170 frames and makes a contact sheet. build creates one
PixelFlow sprite per kind; export preserves editor changes. Never use
build --replace unless discarding those changes is intended.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import make_moonspore_sprites as m
from make_crag_sprites import Palette, ellipsoid, polygon, gradient

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
KINDS=['saltclaw','stormgull','glassray','breakersentinel','maelstromheart']
RAMPS={
 'saltclaw':('#15252f','#35616c','#77aeb3','#d5e6d6','#9af4ea'),
 'stormgull':('#1c2940','#536c83','#adc8cc','#f2f1db','#8fe8ff'),
 'glassray':('#17263d','#315b80','#5fa6b5','#b7eee5','#8cf4ff'),
 'breakersentinel':('#192431','#4b5a67','#8298a0','#d3d3c4','#ffe6a1'),
 'maelstromheart':('#171b38','#38486e','#697fa5','#bac8dc','#f3efff'),
}
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],glow=v[4],
                         dark='#101825',white='#fffef2',accent='#e6aa85')) for k,v in RAMPS.items()}

def fill(f,shape):
 if isinstance(shape,np.ndarray):shape=gradient(shape,20,8,76,84)
 f.paint(shape,f.p.ramp('ink','shadow','body','light'),dither=.18)
def dark(f,shape):f.paint(shape,f.p.ramp('dark','ink','shadow'),dither=.13)
def glow(f,shape):f.paint(shape,f.p.ramp('shadow','glow','white'),dither=.1)
def line(f,a,b,c='body',w=3):
 f.line(a,b,'ol',w+2);f.line(a,b,c,w)
def eye(f,x,y):
 dark(f,ellipsoid(x,y,4,4));glow(f,ellipsoid(x,y,2,2));f.dots([(x-1,y-1)],'white')

def crab(f,x,y,s,hit):
 for side in (-1,1):
  for j in range(3):
   yy=y+58+j*6;line(f,(x+side*19,yy),(x+side*(29+j*3),yy+14),'shadow',3)
  line(f,(x+side*19,y+47),(x+side*(34 if hit else 29),y+33),'body',6)
  fill(f,polygon([(x+side*29,y+27),(x+side*41,y+31),(x+side*35,y+41),(x+side*27,y+36)]))
  line(f,(x+side*31,y+33),(x+side*42,y+22),'glow',2)
 fill(f,ellipsoid(x,y+55,25,17));fill(f,ellipsoid(x,y+45,20,15))
 for j in (-1,1):line(f,(x+j*8,y+38),(x+j*9,y+30),'shadow',3);eye(f,x+j*9,y+29)
 f.line((x-16,y+58),(x+16,y+58),'glow',2)

def gull(f,x,y,s,hit):
 for side in (-1,1):
  wing=polygon([(x+side*8,y+50),(x+side*(25+s),y+24),(x+side*40,y+9),(x+side*34,y+46),(x+side*17,y+61)])
  f.paint(gradient(wing,x-40,y+9,x+40,y+62),f.p.ramp('ink','shadow','body','light'),dither=.12)
  line(f,(x+side*16,y+44),(x+side*36,y+25),'light',2)
 fill(f,ellipsoid(x,y+51,13,20));fill(f,ellipsoid(x,y+28,11,12))
 fill(f,polygon([(x+8,y+27),(x+27,y+32),(x+8,y+36)]));eye(f,x+4,y+26)
 for side in (-1,1):line(f,(x+side*5,y+67),(x+side*8,y+83),'shadow',3)
 if hit:line(f,(x+21,y+34),(x+40,y+50),'glow',2)

def ray(f,x,y,s,hit):
 # Diamond-winged surf ray with a long glass tail; distinct from birds and crabs.
 for side in (-1,1):
  wing=polygon([(x,y+45),(x+side*(35+s),y+26),(x+side*29,y+55),(x+side*8,y+64)])
  f.paint(gradient(wing,x-38,y+23,x+38,y+67),f.p.ramp('ink','shadow','body','light'),dither=.08)
  line(f,(x+side*7,y+45),(x+side*31,y+33),'glow',2)
 fill(f,ellipsoid(x,y+50,13,16));line(f,(x,y+61),(x+s,y+85),'shadow',4)
 for side in (-1,1):eye(f,x+side*6,y+45)
 if hit:glow(f,ellipsoid(x,y+52,6,8))

def sentinel(f,x,y,s,hit):
 # A ruin's walking breakwater: broad stone shoulders, narrow rune face.
 for side in (-1,1):
  line(f,(x+side*12,y+62),(x+side*19,y+82),'shadow',9)
  fill(f,ellipsoid(x+side*20,y+82,9,5))
  line(f,(x+side*22,y+39),(x+side*(34 if hit else 29),y+69),'body',9)
  fill(f,polygon([(x+side*15,y+36),(x+side*26,y+27),(x+side*36,y+39),(x+side*23,y+48)]))
 fill(f,polygon([(x-22,y+39),(x-15,y+21),(x+15,y+21),(x+22,y+39),(x+17,y+67),(x-17,y+67)]))
 dark(f,ellipsoid(x,y+22,15,17));glow(f,ellipsoid(x,y+24,7,6))
 for j in (-1,0,1):line(f,(x+j*8,y+41),(x+j*7,y+58),'glow',2)

def heart(f,x,y,s,hit):
 # A crown of storm glass around an empty, luminous eye, with wave tentacles.
 for side in (-1,1):
  for j in range(3):
   yy=y+50+j*6;line(f,(x+side*15,yy),(x+side*(27+j*4),y+80-j*2),'shadow',5)
  fill(f,polygon([(x+side*9,y+34),(x+side*25,y+9),(x+side*18,y+39)]))
  line(f,(x+side*18,y+38),(x+side*39,y+50),'glow',3)
 fill(f,ellipsoid(x,y+50,23,23));dark(f,ellipsoid(x,y+49,16,16))
 glow(f,ellipsoid(x,y+49,11,11));dark(f,ellipsoid(x,y+49,5,6))
 for j in range(5):
  a=j*math.tau/5+s*.025
  glow(f,ellipsoid(x+math.cos(a)*25,y+49+math.sin(a)*20,3,3))
 if hit:
  for side in (-1,1):line(f,(x+side*28,y+47),(x+side*41,y+31),'glow',2)

DRAWERS=dict(saltclaw=crab,stormgull=gull,glassray=ray,breakersentinel=sentinel,maelstromheart=heart)
m.KINDS=KINDS;m.PALETTES=PALETTES;m.DRAWERS=DRAWERS
m.ROOT=ROOT;m.ASSETS=ASSETS

def metadata(sprites):
 meta=m.metadata(sprites);meta['kinds']=KINDS;return meta

def preview():
 for k in KINDS:m.grids(k)
 sheet=Image.new('RGB',(5*205+12,4*220+40),'#1a2638');d=ImageDraw.Draw(sheet)
 for col,k in enumerate(KINDS):
  for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
   pose=m.draw(k,clip,n).resize((192,192),Image.Resampling.NEAREST)
   sheet.paste(pose,(10+col*205,28+row*220),pose)
   d.text((10+col*205,8+row*220),f'{k} {clip}',fill='#d5f5ef')
 out=ROOT/'test-results/stormglass-enemies.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)

def pf():return m._pf()

def build():
 path=ASSETS/'stormglass.txt'
 if path.exists():raise SystemExit('Stormglass sprites already exist; export preserves edits. Refusing replacement.')
 api=pf();sprites={}
 for k in KINDS:
  data=m.grids(k)
  np.savez_compressed(ROOT/'scripts'/f'stormglass_{k}_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
  sid=api.create('valhallasc_stormglass_'+k+'_all',96,96,34,PALETTES[k].hex,fps=10)
  frame=0
  try:
   for clip,count in m.CLIPS:
    for grid in data[clip]:api.draw_grid(sid,frame,0,grid);frame+=1
  except Exception:
   api.api('delete',{'sprite_id':sid});raise
  sprites[k]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n');print(k,sid,flush=True)

def export(verify=False):
 api=pf();path=ASSETS/'stormglass.txt';sprites=json.loads(path.read_text())['sprites']
 for k in KINDS:
  sp,frames=api.load(sprites[k]);assert(sp['width'],sp['height'],len(frames))==(96,96,34)
  out=Image.new('RGBA',(96*8,96*len(m.CLIPS)));offset=0
  for row,(clip,count) in enumerate(m.CLIPS):
   for n in range(count):out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*96,row*96))
   offset+=count
  target=ASSETS/f'stormglass_{k}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),k
  else:out.save(target,optimize=True);print('exported',k,flush=True)
 if verify:print('Five PixelFlow sprites and 170 frames verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')

if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build()
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 else:raise SystemExit('preview | build | export | verify')
