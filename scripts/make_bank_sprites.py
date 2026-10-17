#!/usr/bin/env python3
"""Five editable PixelFlow banker atlases, one per big city (BANK-ART, docs/bank.md).

Each atlas is 96x96, two clips (idle 6, talk 6): the banker on the left and a strongbox or counter prop of the city's own
on the right, in a palette of its own. `build` makes the PixelFlow sprites (it discards hand edits), `export` reads them
back into client/assets/bank_<city>.png + bank.txt, `verify` compares them, `preview` writes test-results/bank-cast.png.
"""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from make_crag_sprites import Palette,ellipsoid,polygon,gradient,capsule
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'client/assets'
W=H=96
CLIPS=[('idle',6),('talk',6)]
KINDS=['bank_alderhaven','bank_skaldholm','bank_nacrehold','bank_astralhollow','bank_asterion']
# robe ramp (ink..glow), skin, hair, hat, prop wood/metal, gold, accent glow
SPEC={
 'bank_alderhaven':dict(robe=('#2f3b2a','#4f6b3e','#7e9a56','#b7c97b'),skin=('#a9714f','#d99d78','#f3c9a4'),hair=('#4b2d19','#7a4a2a'),hat=('#6b5320','#a8873a'),
                        wood=('#3a2412','#6b4423','#9a6a37'),metal=('#5c4a22','#c9a24b','#f1d98a'),glow='#fff0b0',extra='#efe3c4'),
 'bank_skaldholm':dict(robe=('#26303f','#44556f','#6d82a3','#a3b4cf'),skin=('#a06a4a','#d39d78','#eec3a0'),hair=('#6e695f','#b9b2a4'),hat=('#3d4856','#6d7e93'),
                       wood=('#2c2c33','#4b4f5c','#747a8a'),metal=('#4a4e5a','#9aa3b3','#d3dae6'),glow='#e6f2ff',extra='#8a6a3c'),
 'bank_nacrehold':dict(robe=('#3e2a4a','#8a5f94','#c78fc0','#efc9e6'),skin=('#5f9c89','#8fcab6','#c1ece0'),hair=('#2f5663','#5f8f9c'),hat=('#3d6a73','#6fa5ad'),
                       wood=('#4c5a6b','#8e9fb0','#d5dde5'),metal=('#8a5a78','#e2b7d6','#fff0f8'),glow='#fff7ff',extra='#e8d8b8'),
 'bank_astralhollow':dict(robe=('#1b2250','#2f3c86','#5a6ed0','#9fb4ff'),skin=('#9c7f6e','#d1b29c','#ecd5c0'),hair=('#6a7fb8','#a9c0f0'),hat=('#202864','#3d4a96'),
                          wood=('#16183a','#2c3278','#4d58b0'),metal=('#6a5fb0','#c9d4ff','#ffffff'),glow='#e8f0ff',extra='#ffe9a8'),
 'bank_asterion':dict(robe=('#33264f','#5b45a0','#8a74d0','#cdbff0'),skin=('#86523a','#b97e5c','#dba98a'),hair=('#a99e8e','#f2e7d5'),hat=('#3b2c6e','#6a54b8'),
                      wood=('#46433f','#8a8478','#d8d0c0'),metal=('#6e5420','#d8b24c','#fff0a8'),glow='#fff7d8',extra='#f2e7d5'),
}
def palette(kind):
 s=SPEC[kind];c={}
 for i,n in enumerate(s['robe']):c[f'robe{i}']=n
 for i,n in enumerate(s['skin']):c[f'skin{i}']=n
 for i,n in enumerate(s['hair']):c[f'hair{i}']=n
 for i,n in enumerate(s['hat']):c[f'hat{i}']=n
 for i,n in enumerate(s['wood']):c[f'wood{i}']=n
 for i,n in enumerate(s['metal']):c[f'metal{i}']=n
 c.update(glow=s['glow'],extra=s['extra'],dark='#171420',white='#fffdf5',mouth='#7a3b3b',tail='#d8a0cc')
 seen={'#1a1118','#fffaf0'}  # the shared outline and flash colours
 for name,value in c.items():   # identical hex values are merged by PixelFlow, so nudge repeats
  while value in seen:value='#%02x%02x%02x'%(int(value[1:3],16),int(value[3:5],16),(int(value[5:7],16)+1)%256)
  seen.add(value);c[name]=value
 return Palette(c)
PALETTES={k:palette(k) for k in KINDS}

def paint(f,shape,ramp,dither=.12):
 if isinstance(shape,np.ndarray):shape=gradient(shape,12,6,85,84)
 f.paint(shape,f.p.ramp(*ramp),dither=dither)
def line(f,a,b,c,w=3):f.line(a,b,'ol',w+2);f.line(a,b,c,w)
R=lambda n:tuple(f'robe{i}' for i in range(n));S=('skin0','skin1','skin2');WD=('wood0','wood1','wood2');MT=('metal0','metal1','metal2')

def head(f,x,y,talk,blink,hair=None,hat=None,beard=False):
 paint(f,ellipsoid(x,y+25,11,13),S)
 if beard:paint(f,polygon([(x-11,y+27),(x+11,y+27),(x+8,y+44),(x,y+49),(x-8,y+44)]),('hair0','hair1','hair1'))
 if blink:f.line((x+3,y+24),(x+8,y+24),'dark',1)
 else:f.dots([(x+4,y+23),(x+4,y+24),(x+7,y+23),(x+7,y+24)],'dark')
 if talk:f.flat(polygon([(x+3,y+31),(x+8,y+31),(x+6,y+35)]),'mouth')
 elif not beard:f.line((x+3,y+31),(x+7,y+31),'mouth',1)

def chest(f,cx,y,glint,kind):
 """The prop beside the banker. cx is its centre; the base stands on y+84."""
 if kind=='bank_alderhaven':                    # banded wooden strongbox with a coin stack and a small ledger
  paint(f,polygon([(cx-19,y+60),(cx+19,y+60),(cx+19,y+84),(cx-19,y+84)]),WD)
  paint(f,ellipsoid(cx,y+60,19,10),WD)
  for dx in (-11,0,11):f.line((cx+dx,y+51),(cx+dx,y+84),'metal1',2)
  f.flat(polygon([(cx-3,y+63),(cx+3,y+63),(cx+3,y+70),(cx-3,y+70)]),'metal2',True)
  for j in range(4):paint(f,ellipsoid(cx-10,y+50-j*3,6,2),MT,.05)
  paint(f,polygon([(cx+3,y+47),(cx+16,y+44),(cx+17,y+53),(cx+4,y+55)]),('hat0','hat1','extra'))
 elif kind=='bank_skaldholm':                   # iron-bound chest with rivets and a hanging padlock, a round shield behind
  paint(f,ellipsoid(cx+6,y+56,16,16),('wood0','wood1','metal1'))
  f.line((cx+6,y+42),(cx+6,y+70),'metal2',2);f.line((cx-10,y+56),(cx+22,y+56),'metal2',2)
  paint(f,polygon([(cx-20,y+62),(cx+20,y+62),(cx+20,y+84),(cx-20,y+84)]),MT)
  paint(f,polygon([(cx-20,y+54),(cx+20,y+54),(cx+17,y+64),(cx-17,y+64)]),MT)
  for dx in (-15,-5,5,15):f.dots([(cx+dx,y+57),(cx+dx,y+78)],'metal2')
  f.line((cx-20,y+70),(cx+20,y+70),'wood0',2)
  paint(f,polygon([(cx-4,y+66),(cx+4,y+66),(cx+4,y+76),(cx-4,y+76)]),('hat0','hat1','hat1'))
  f.dots([(cx,y+70),(cx,y+71)],'dark')
 elif kind=='bank_nacrehold':                   # a great open clam on a rock, holding a pearl
  paint(f,ellipsoid(cx,y+82,22,7),('wood0','wood1','wood2'))
  paint(f,ellipsoid(cx,y+70,20,13),('metal0','metal1','metal2'))
  paint(f,polygon([(cx-20,y+66),(cx-14,y+42),(cx,y+37),(cx+14,y+42),(cx+20,y+66),(cx,y+60)]),('metal0','metal1','metal2'))
  for dx in (-12,-6,0,6,12):f.line((cx+dx//2,y+58),(cx+dx,y+41+abs(dx)//3),'metal0',1)
  paint(f,ellipsoid(cx,y+64,6,6),('wood2','white','white'),.02)
  f.dots([(cx-2,y+62),(cx-2,y+63)],'glow') if not glint else f.dots([(cx-2,y+62),(cx-1,y+61),(cx-3,y+62),(cx-2,y+60),(cx-2,y+64)],'glow')
 elif kind=='bank_astralhollow':                # a star-studded chest under a floating ledger
  paint(f,polygon([(cx-19,y+62),(cx+19,y+62),(cx+19,y+84),(cx-19,y+84)]),WD)
  paint(f,ellipsoid(cx,y+62,19,9),WD)
  f.line((cx-19,y+70),(cx+19,y+70),'metal1',2)
  for dx,dy in ((-12,66),(8,74),(13,64),(-4,77),(-14,78)):f.dots([(cx+dx,y+dy),(cx+dx,y+dy-1),(cx+dx-1,y+dy),(cx+dx+1,y+dy)],'extra')
  lift=[0,1,2,2,1,0][glint]
  paint(f,polygon([(cx-11,y+36-lift),(cx+11,y+34-lift),(cx+12,y+49-lift),(cx-10,y+51-lift)]),('wood0','wood1','robe3'))
  f.line((cx,y+35-lift),(cx,y+50-lift),'metal2',1)
  f.dots([(cx-6,y+41-lift),(cx+6,y+44-lift),(cx+5,y+39-lift)],'extra')
 else:                                          # a marble pedestal under a brass balance, a coin in one pan
  paint(f,polygon([(cx-15,y+62),(cx+15,y+62),(cx+18,y+84),(cx-18,y+84)]),WD)
  paint(f,polygon([(cx-18,y+57),(cx+18,y+57),(cx+16,y+64),(cx-16,y+64)]),WD)
  f.line((cx,y+57),(cx,y+30),'metal1',3);f.dots([(cx,y+27),(cx,y+28),(cx-1,y+28),(cx+1,y+28)],'metal2')
  tilt=[0,1,1,0,-1,-1][glint]
  f.line((cx-15,y+33-tilt),(cx+15,y+33+tilt),'metal1',2)
  for side in (-1,1):
   py=y+33+side*tilt
   f.line((cx+side*15,py),(cx+side*15,py+10),'metal0',1)
   paint(f,ellipsoid(cx+side*15,py+13,8,3),MT,.05)
  f.flat(polygon([(cx-19,y+39-tilt),(cx-15,y+39-tilt),(cx-15,y+42-tilt),(cx-19,y+42-tilt)]),'metal2')

def body(f,x,y,talk,b,kind):
 """Banker at x; b is the breath (0..1) and moves the upper body, talk raises a hand."""
 arm=(x+24,y+60-(10 if talk else 0)-b)
 if kind=='bank_nacrehold':
  for dx,dy,rx,ry in [(1,67,12,9),(0,74,12,8),(-4,80,11,6),(-11,83,9,4)]:paint(f,ellipsoid(x+dx,y+dy,rx,ry),('robe0','robe1','robe2','robe3'),.05)
  paint(f,polygon([(x-16,y+80),(x-30,y+70),(x-31,y+84),(x-18,y+83)]),('robe0','robe1','robe2'))
  paint(f,polygon([(x-16,y+82),(x-31,y+86),(x-28,y+76)]),('robe0','robe1','robe3'))
  paint(f,polygon([(x-11,y+36-b),(x+11,y+36-b),(x+10,y+64),(x-10,y+64)]),S)
  paint(f,ellipsoid(x-5,y+45-b,6,5),('tail','robe3','robe3'));paint(f,ellipsoid(x+5,y+45-b,6,5),('tail','robe3','robe3'))
 else:
  for side in (-1,1):line(f,(x+side*8,y+68),(x+side*9,y+83),'robe0',6)
  paint(f,polygon([(x-16,y+36-b),(x+16,y+36-b),(x+22,y+80),(x-22,y+80)]),R(4) if kind!='bank_skaldholm' else R(4))
 if kind=='bank_alderhaven':paint(f,polygon([(x-10,y+50),(x+10,y+50),(x+14,y+80),(x-14,y+80)]),('hat1','extra','extra'))
 if kind=='bank_skaldholm':
  paint(f,polygon([(x-16,y+36-b),(x+16,y+36-b),(x+18,y+60),(x-18,y+60)]),MT)
  for j in range(4):f.line((x-16,y+41+j*5-b),(x+16,y+41+j*5-b),'metal0',1)
  f.line((x-18,y+62),(x+18,y+62),'hat1',3)
 if kind=='bank_astralhollow':
  for dx,dy in ((-9,48),(8,56),(-4,68),(11,72),(-12,76)):f.dots([(x+dx,y+dy),(x+dx,y+dy-1),(x+dx+1,y+dy)],'extra')
 if kind=='bank_asterion':
  f.line((x-12,y+38-b),(x+12,y+70),'metal1',3);f.line((x-22,y+66),(x+22,y+66),'metal0',2)
 if kind=='bank_skaldholm':line(f,(x-18,y+42-b),(x-26,y+66),'robe1',9)
 else:line(f,(x-16,y+42-b),(x-24,y+66),'skin1' if kind=='bank_nacrehold' else 'robe1',8)
 line(f,(x+16,y+42-b),arm,'skin1' if kind=='bank_nacrehold' else 'robe1',8 if kind!='bank_skaldholm' else 9)
 for p in ((x-24,y+68),arm):paint(f,ellipsoid(p[0],p[1]+3,4,4),S)
 head(f,x,y-b,talk,b==1 and kind!='bank_nacrehold' and False,beard=kind=='bank_skaldholm')

def hair_hat(f,x,y,b,kind):
 y=y-b
 if kind=='bank_alderhaven':
  paint(f,polygon([(x-13,y+22),(x-11,y+8),(x,y+4),(x+12,y+8),(x+13,y+22),(x+9,y+16),(x-9,y+16)]),('hair0','hair1','hair1'))
  paint(f,ellipsoid(x,y+5,8,5),('hair0','hair1','hair1'))
  paint(f,ellipsoid(x,y+9,15,7),('hat0','hat1','hat1'))
  line(f,(x-12,y+14),(x-14,y+26),'hat1',3)
 elif kind=='bank_skaldholm':
  paint(f,polygon([(x-13,y+18),(x-12,y+6),(x,y+0),(x+12,y+6),(x+13,y+18),(x+7,y+16),(x,y+12),(x-7,y+16)]),('hat0','hat1','hat1'))
  f.line((x,y+0),(x,y+16),'metal2',2)
  for sd in (-1,1):paint(f,polygon([(x+sd*12,y+6),(x+sd*20,y-1),(x+sd*15,y+12)]),('wood2','extra','extra'))
 elif kind=='bank_nacrehold':
  paint(f,polygon([(x-13,y+24),(x-12,y+9),(x,y+4),(x+12,y+9),(x+13,y+24),(x+9,y+20),(x-9,y+20)]),('hair0','hair1','hair1'))
  paint(f,polygon([(x-14,y+14),(x-17,y+40),(x-12,y+54),(x-9,y+30)]),('hair0','hair1','hair1'))
  paint(f,ellipsoid(x-1,y+7,5,4),('wood0','wood1','wood2'),.02)
 elif kind=='bank_astralhollow':
  paint(f,polygon([(x-15,y+34),(x-14,y+10),(x-5,y+0),(x+5,y+0),(x+14,y+10),(x+15,y+34),(x+11,y+34),(x+12,y+17),(x+6,y+12),(x-6,y+12),(x-12,y+17),(x-11,y+34)]),('hat0','hat1','hat1'))
  line(f,(x-9,y+24),(x-12,y+54),'hair1',3);paint(f,ellipsoid(x-12,y+56,3,3),('extra','extra','white'))
  f.dots([(x,y+4),(x,y+5)],'extra')
 else:
  paint(f,polygon([(x-13,y+22),(x-12,y+8),(x,y+2),(x+12,y+8),(x+13,y+22),(x+8,y+18),(x-8,y+18)]),('hair0','hair1','hair1'))
  paint(f,ellipsoid(x,y+6,15,6),('hat0','hat1','hat1'))
  line(f,(x+8,y+6),(x+17,y+2),'extra',3);line(f,(x+8,y+6),(x+22,y+2),'hair1',2)

def draw(kind,clip,n):
 f=Frame(PALETTES[kind]);x=36;oy=4
 b=[0,0,1,1,1,0][n] if clip=='idle' else [0,1,0,1,0,1][n]
 talk=clip=='talk' and n%2==1
 chest(f,65,oy,n,kind)
 body(f,x,oy,talk,b,kind)
 hair_hat(f,x,oy,b,kind)
 if clip=='idle' and n==4:f.line((x+3,24+oy),(x+8,24+oy),'dark',1)
 sx,sy=[(58,52),(64,49),(72,51),(78,55),(70,58),(62,57)][n]   # a travelling glint over the prop, so no two frames match
 f.dots([(sx,sy+oy),(sx-1,sy+oy),(sx+1,sy+oy),(sx,sy+oy-1),(sx,sy+oy+1)],'white')
 colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255] for j,c in enumerate(f.p.hex)],dtype=np.uint8)
 return Image.fromarray(colors[f.a],'RGBA')
from make_crag_sprites import Frame

def grids(kind):
 colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255] for j,c in enumerate(PALETTES[kind].hex)],dtype=np.uint8)
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

def icon_grid():
 """The bank window's 48x48 icon: the Alderhaven strongbox with its coin stack and ledger, alone, cropped from a frame."""
 kind='bank_alderhaven';f=Frame(PALETTES[kind]);chest(f,48,-2,0,kind)
 return f.a[36:84,24:72].copy()

def metadata(sprites):
 start=0;clips={}
 for row,(clip,count) in enumerate(CLIPS):
  clips[clip]=dict(fps=6,n=count,row=row,editorStart=start);start+=count
 return dict(frame=[W,H],anchor=[48,90],kinds=KINDS,clips=clips,sprites=sprites)

def _pf():
 sys.path.insert(0,str(Path.home()/'.claude/skills/makesprites'))
 import pf
 return pf

def preview():
 for kind in KINDS:grids(kind)
 sheet=Image.new('RGB',(len(KINDS)*300+12,2*300+40),'#6f8a5a');d=ImageDraw.Draw(sheet)
 for col,kind in enumerate(KINDS):
  for row,(clip,n) in enumerate([('idle',2),('talk',1)]):
   pose=draw(kind,clip,n).resize((288,288),Image.Resampling.NEAREST)
   sheet.paste(pose,(10+col*300,28+row*300),pose);d.text((10+col*300,8),kind,fill='#fff')
 out=ROOT/'test-results/bank-cast.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)

def build_icon(api,path,sprites):
 sid=api.create('valhallasc_bank_icon',48,48,1,PALETTES['bank_alderhaven'].hex,fps=1)
 try:api.draw_grid(sid,0,0,icon_grid())
 except Exception:
  api.api('delete',{'sprite_id':sid});raise
 sprites['icon']=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n');print('icon',sid)

def build():
 path=ASSETS/'bank.txt'
 if path.exists():raise SystemExit('Bank sprites already exist; export preserves edits.')
 api=_pf();sprites={}
 for kind in KINDS:
  data=grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'{kind}_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
  sid=api.create('valhallasc_'+kind,W,H,12,PALETTES[kind].hex,fps=6)
  frame=0
  try:
   for clip,count in CLIPS:
    for grid in data[clip]:api.draw_grid(sid,frame,0,grid);frame+=1
  except Exception:
   api.api('delete',{'sprite_id':sid});raise
  sprites[kind]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
  print(kind,sid,flush=True)
 build_icon(api,path,sprites)

def export(verify=False):
 api=_pf();path=ASSETS/'bank.txt';sprites=json.loads(path.read_text())['sprites']
 for kind in KINDS:
  sp,frames=api.load(sprites[kind]);assert (sp['width'],sp['height'],len(frames))==(W,H,12)
  out=Image.new('RGBA',(W*6,H*len(CLIPS)));offset=0
  for row,(clip,count) in enumerate(CLIPS):
   for n in range(count):out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*W,row*H))
   offset+=count
  target=ASSETS/f'{kind}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),kind
  else:out.save(target,optimize=True);print('exported',kind,flush=True)
 sp,frames=api.load(sprites['icon']);assert (sp['width'],sp['height'],len(frames))==(48,48,1)
 icon=Image.fromarray(api.to_rgba(frames[0][0],sp['palette']),'RGBA');target=ASSETS/'bank_icon.png'
 if verify:assert icon.tobytes()==Image.open(target).convert('RGBA').tobytes(),'icon'
 else:icon.save(target,optimize=True);print('exported icon')
 if verify:print('Bank PixelFlow atlases and icon verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')

if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build()
 elif cmd=='icon':
  path=ASSETS/'bank.txt';sprites=json.loads(path.read_text())['sprites']
  if 'icon' in sprites:raise SystemExit('icon exists')
  build_icon(_pf(),path,sprites)
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 else:raise SystemExit('preview | build | icon | export | verify')
