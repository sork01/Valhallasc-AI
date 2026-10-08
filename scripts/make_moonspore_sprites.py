#!/usr/bin/env python3
"""Draw and round-trip seven Moonspore enemies through the makesprites/PixelFlow workflow.

preview | build [--replace] | export | verify | contact. Build --replace deletes
only these sprites and discards their editor changes; export preserves edits.
"""
import json
import math
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from make_crag_sprites import AY, Frame, Palette, ellipsoid, polygon, gradient

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
KINDS=['glowcapgrazer','silkwing','rootlurker','lanternwraith','mireheart','silverwidow','nightbloom']
CLIPS=[('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
W=H=96
RAMPS={
 'glowcapgrazer':('#203333','#457060','#8bbc83','#ddedb0','#bbffae'),
 'silkwing':('#263342','#546879','#b5b3ae','#f5e1be','#c7f8ee'),
 'rootlurker':('#292c36','#584c48','#94816a','#c9ae83','#a2f6c8'),
 'lanternwraith':('#272d46','#545579','#9b97b2','#e3d5cb','#b8ffa5'),
 'mireheart':('#2b3430','#4e6850','#8d9d6a','#c4c994','#efb9ba'),
 'silverwidow':('#2d2d43','#65647b','#b7b5c2','#e9dfdc','#e9b9ff'),
 'nightbloom':('#252b43','#514965','#9f749d','#dfb5c4','#eafca1'),
}
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],glow=v[4],
                         dark='#151b2b',white='#fff9ed',accent='#e9a4b2')) for k,v in RAMPS.items()}

def shade(f,shape):f.paint(shape,f.p.ramp('ink','shadow','body','light'),dither=.22)
def dark(f,shape):f.paint(shape,f.p.ramp('dark','ink','shadow'),dither=.15)
def glow(f,shape):f.paint(shape,f.p.ramp('shadow','glow','white'),dither=.12)
def line(f,a,b,c='body',w=2):
 f.line(a,b,'ol',w+2);f.line(a,b,c,w)
def eye(f,x,y,r=3):
 dark(f,ellipsoid(x,y,r+1,r+1));glow(f,ellipsoid(x,y,r,r));f.dots([(x-1,y-1)],'white')

def grazer(f,x,y,s,hit):
 for side in (-1,1):
  line(f,(x+side*13,y+60),(x+side*(17+s),y+82),'shadow',6)
  shade(f,ellipsoid(x+side*(17+s),y+81,8,5))
 shade(f,ellipsoid(x,y+54,30,17))
 shade(f,ellipsoid(x+23,y+48,13,12));eye(f,x+28,y+46,3)
 for j in (-1,0,1):
  xx=x+j*15
  line(f,(xx,y+45),(xx+j*2,y+20),'shadow',5)
  glow(f,ellipsoid(xx+j*2,y+18,11 if j else 15,6))
  f.line((xx-7,y+18),(xx+7,y+18),'light',2)
 if hit:line(f,(x+33,y+49),(x+42,y+40),'glow',3)

def silkwing(f,x,y,s,hit):
 for side in (-1,1):
  wing=polygon([(x+side*7,y+37),(x+side*(33+s),y+12),(x+side*39,y+43),(x+side*22,y+58)])
  f.paint(gradient(wing,x-42,y+12,x+42,y+59),f.p.ramp('ink','shadow','body','light'),dither=.1)
  glow(f,ellipsoid(x+side*25,y+35,6,7))
 shade(f,ellipsoid(x,y+46,10,25));dark(f,ellipsoid(x,y+25,10,9))
 for side in (-1,1):line(f,(x+side*5,y+21),(x+side*14,y+8),'light',2)
 eye(f,x+4,y+26,3)
 if hit:line(f,(x+11,y+48),(x+39,y+54),'glow',2)

def lurker(f,x,y,s,hit):
 for side in (-1,1):
  line(f,(x+side*10,y+62),(x+side*(19+s),y+83),'shadow',7)
  line(f,(x+side*17,y+80),(x+side*28,y+84),'light',2)
  line(f,(x+side*18,y+45),(x+side*(35 if hit else 28),y+56),'body',7)
  for j in range(3):line(f,(x+side*(30+j*3),y+56),(x+side*(34+j*3),y+65),'light',2)
 shade(f,ellipsoid(x,y+48,21,24));shade(f,ellipsoid(x,y+23,16,15))
 for j in (-1,0,1):line(f,(x+j*10,y+14),(x+j*12,y+2),'shadow',3)
 eye(f,x-6,y+24,3);eye(f,x+6,y+24,3)
 f.line((x-8,y+52),(x+8,y+57),'glow',2)

def wraith(f,x,y,s,hit):
 for j in range(7):
  xx=x+(j-3)*6
  line(f,(xx,y+57),(xx+math.sin(j+s)*5,y+78+j%3*3),'shadow',3)
 shade(f,ellipsoid(x,y+45,23,23));dark(f,ellipsoid(x,y+26,17,17))
 for side in (-1,1):
  line(f,(x+side*17,y+47),(x+side*(35 if hit else 27),y+49),'light',5)
  glow(f,ellipsoid(x+side*29,y+50,5,7))
 eye(f,x-7,y+26,3);eye(f,x+7,y+26,3)
 glow(f,ellipsoid(x,y+47,10,12));dark(f,ellipsoid(x,y+47,6,7))

def heart(f,x,y,s,hit):
 for side in (-1,1):
  line(f,(x+side*13,y+59),(x+side*31,y+82),'shadow',9)
  line(f,(x+side*25,y+80),(x+side*39,y+84),'body',4)
  line(f,(x+side*20,y+38),(x+side*(38 if hit else 31),y+53),'shadow',8)
 shade(f,ellipsoid(x,y+47,25,30));dark(f,ellipsoid(x,y+23,19,17))
 glow(f,ellipsoid(x,y+49,13,15));f.line((x-8,y+49),(x+6,y+57),'accent',3)
 for side in (-1,1):
  line(f,(x+side*13,y+13),(x+side*27,y+2),'body',5)
  glow(f,ellipsoid(x+side*26,y+5,5,4))
 eye(f,x-8,y+26,3);eye(f,x+8,y+26,3)

def widow(f,x,y,s,hit):
 for side in (-1,1):
  for j in range(3):
   yy=y+43+j*8
   line(f,(x+side*16,yy),(x+side*(27+j*4),yy-11+s/3),'shadow',4)
   line(f,(x+side*(27+j*4),yy-11+s/3),(x+side*(37+j*2),y+82),'light',3)
 shade(f,ellipsoid(x,y+55,26,20));dark(f,ellipsoid(x+5,y+54,17,15))
 glow(f,ellipsoid(x+5,y+54,8,8))
 shade(f,ellipsoid(x-17,y+35,14,12))
 for j in (-1,0,1):eye(f,x-20+j*6,y+34,2)
 if hit:
  for side in (-1,1):line(f,(x+side*19,y+42),(x+side*40,y+25),'glow',2)

def bloom(f,x,y,s,hit):
 line(f,(x,y+50),(x,y+85),'shadow',11)
 for side in (-1,1):
  line(f,(x,y+67),(x+side*30,y+81),'body',6)
  line(f,(x+side*12,y+61),(x+side*35,y+48),'body',5)
  shade(f,ellipsoid(x+side*28,y+48,10,5))
 for j in range(8):
  a=j*math.tau/8+s*.01
  px=x+math.cos(a)*22;py=y+33+math.sin(a)*20
  petal=ellipsoid(px,py,11,18,a+math.pi/2)
  f.paint(petal,f.p.ramp('ink','shadow','body','light'),dither=.16)
 glow(f,ellipsoid(x,y+32,17,17));dark(f,ellipsoid(x,y+32,9,9));eye(f,x,y+32,5)
 if hit:
  for j in range(4):
   a=j*math.pi/2;line(f,(x+math.cos(a)*20,y+32+math.sin(a)*19),
                       (x+math.cos(a)*41,y+32+math.sin(a)*33),'glow',2)

DRAWERS={'glowcapgrazer':grazer,'silkwing':silkwing,'rootlurker':lurker,
 'lanternwraith':wraith,'mireheart':heart,'silverwidow':widow,'nightbloom':bloom}

def pose(clip,n):
 if clip=='idle':return 0,[0,1,2,1,0,1][n],n-2
 if clip=='walk':return [0,-1,1,3,2,0,-1,0][n],[0,1,4,7,5,1,0,0][n],[0,-2,3,5,2,-3,-2,0][n]
 if clip=='attack':return [0,-1,-3,-4,4,3,1,0][n],[0,0,1,0,3,2,1,0][n],n-3
 if clip=='hurt':return [2,1,-1,0][n],[0,2,1,0][n],n-1
 return 0,0,n

def draw(kind,clip,n):
 f=Frame(PALETTES[kind]);dx,lift,sway=pose(clip,n)
 DRAWERS[kind](f,48+dx,-lift,sway,clip=='attack' and n in (3,4,5))
 if clip=='idle':f.dots([(32+n*4,39+n%3),(33+n*4,39+n%3)],'glow')
 if clip=='hurt' and n==0:f.whiten()
 if clip=='hurt' and n==1:
  yy,xx=np.indices(f.a.shape);f.a[(f.a>0)&(f.a!=f.p['ol'])&((xx+yy)%3==0)]=f.p['flash']
 if clip=='die':
  if n==0:f.whiten()
  if n>=2:
   ys,xs=np.nonzero(f.a);body=f.a[ys.min():ys.max()+1,xs.min():xs.max()+1]
   height=max(5,round(body.shape[0]*[1,1,.72,.49,.31,.18,.11,.07][n]))
   image=Image.fromarray(body).resize((body.shape[1],height),Image.Resampling.NEAREST)
   f.a[:]=0;px=max(1,min(W-body.shape[1]-1,xs.min()));py=min(H-height-5,AY-height)
   f.a[py:py+height,px:px+body.shape[1]]=np.array(image)
   for j in range(3):f.line((27+j*17+n%4,85),(31+j*17+n%4,81-n%3),'light',1)
 colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255]
                  for j,c in enumerate(f.p.hex)],dtype=np.uint8)
 image=Image.fromarray(colors[f.a],'RGBA').resize((88,88),Image.Resampling.NEAREST)
 framed=Image.new('RGBA',(W,H));framed.alpha_composite(image,(4,7));return framed

def _pf():
 sys.path.insert(0,str(Path.home()/'.claude/skills/makesprites'))
 import pf
 return pf

def metadata(sprites):
 start=0;clips={}
 for row,(clip,count) in enumerate(CLIPS):
  clips[clip]=dict(fps=10,n=count,row=row,editorStart=start);start+=count
 return dict(frame=[W,H],anchor=[48,90],kinds=KINDS,clips=clips,sprites=sprites)

def grids(kind):
 colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255]
                  for j,c in enumerate(PALETTES[kind].hex)],dtype=np.uint8)
 out={}
 for clip,count in CLIPS:
  out[clip]=[]
  for n in range(count):
   image=np.array(draw(kind,clip,n));grid=np.zeros((H,W),dtype=np.uint8)
   for j,rgba in enumerate(colors[1:],1):grid[np.all(image==rgba,axis=2)]=j
   assert np.array_equal(colors[grid],image),(kind,clip,n,'palette mismatch')
   ys,xs=np.nonzero(grid)
   assert len(xs) and xs.min()>0 and xs.max()<W-1 and ys.min()>0 and ys.max()<H-1,(kind,clip,n,'edge')
   out[clip].append(grid)
  assert len({g.tobytes() for g in out[clip]})>=count-1,(kind,clip,'static')
 return out

def build(replace=False):
 pf=_pf();path=ASSETS/'moonspore.txt'
 meta=json.loads(path.read_text()) if path.exists() else {};sprites=meta.get('sprites',{})
 if sprites and not replace:raise SystemExit('Sprites already exist; export preserves editor edits. build --replace discards them.')
 if replace:
  for sid in sprites.values():assert pf.api('delete',{'sprite_id':sid}).get('ok')
  sprites={}
 for kind in KINDS:
  data=grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'moonspore_{kind}_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
  sid=pf.create('valhallasc_moonspore_'+kind+'_all',W,H,34,PALETTES[kind].hex,fps=10)
  frame=0
  try:
   for clip,count in CLIPS:
    for grid in data[clip]:pf.draw_grid(sid,frame,0,grid);frame+=1
  except Exception:
   pf.api('delete',{'sprite_id':sid});raise
  sprites[kind]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
  print(kind,sid,'34 frames',flush=True)

def export(verify=False):
 pf=_pf();path=ASSETS/'moonspore.txt';sprites=json.loads(path.read_text())['sprites']
 for kind in KINDS:
  sp,frames=pf.load(sprites[kind]);assert (sp['width'],sp['height'],len(frames))==(W,H,34)
  out=Image.new('RGBA',(W*8,H*len(CLIPS)));offset=0
  for row,(clip,count) in enumerate(CLIPS):
   for n in range(count):out.alpha_composite(Image.fromarray(pf.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*W,row*H))
   offset+=count
  target=ASSETS/f'moonspore_{kind}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),kind
  else:out.save(target,optimize=True);print('exported',kind,flush=True)
 if verify:print('Seven PixelFlow sprites, 238 frames and atlases verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')

def contact():
 sheet=Image.new('RGB',(7*205+12,4*220+40),'#25332c');d=ImageDraw.Draw(sheet)
 for col,kind in enumerate(KINDS):
  for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
   pose=draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
   sheet.paste(pose,(10+col*205,28+row*220),pose)
   d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#d7f3c4')
 out=ROOT/'test-results/moonspore-enemies.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)

def main():
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview';ASSETS.mkdir(exist_ok=True)
 if cmd=='build':build('--replace' in sys.argv[2:])
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 elif cmd=='preview':
  for kind in KINDS:grids(kind)
  contact()
 elif cmd=='contact':contact()
 else:raise SystemExit('preview | build [--replace] | export | verify | contact')
if __name__=='__main__':main()
