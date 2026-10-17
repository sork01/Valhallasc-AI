#!/usr/bin/env python3
"""The treasure chest as one editable PixelFlow sprite (CHEST-ART, docs/chests.md).

64x64, three clips: closed (6 frames, a glint travels over the lid), opening (6 frames, the lid swings back and the gold
lights up) and opened (2 frames, the pile shimmers). `build` makes the PixelFlow sprite (it discards hand edits),
`export` reads it back into client/assets/chest.png + chest.txt, `verify` compares them, `preview` writes
test-results/chest-cast.png on grounds from the game (grass, sand, snow, stone, water, dark) to judge readability.
"""
import json,math,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from make_crag_sprites import Palette,Frame,ellipsoid,polygon,gradient
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'client/assets'
SIZE=64;CROP=(16,24)          # drawn on the shared 96x96 canvas, cropped to 64x64
CLIPS=[('closed',6,6),('opening',6,12),('opened',2,4)]
ANGLES=[0,8,25,50,80,100]     # lid angle in degrees for the opening frames
COLORS=dict(wood0='#3d2212',wood1='#7a4423',wood2='#b2743a',metal0='#7a5a1c',metal1='#d6a738',metal2='#ffe08b',
            lin0='#4a1a1c',lin1='#7a2a2e',lin2='#a84a46',dark='#1d1210',glow='#fff2b0',white='#ffffff',rim='#f3d9a0')
P=Palette(COLORS)
WD=('wood0','wood1','wood2');MT=('metal0','metal1','metal2');LN=('lin0','lin1','lin2')
CX=48;BACK=46;FRONT=58;BASE=78   # hinge row, top of the front face, bottom of the chest

def paint(f,shape,ramp,dither=.12):
 if isinstance(shape,np.ndarray):shape=gradient(shape,28,44,68,80)
 f.paint(shape,P.ramp(*ramp),dither=dither)

def star(f,x,y,big=False):
 pts=[(x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)]
 if big:pts+=[(x-2,y),(x+2,y),(x,y-2),(x,y+2)]
 f.dots(pts,'white')

def lid(f,a,seen_from_below):
 """The lid hinged on the back edge, turned a degrees; a lid past the upright shows its lining."""
 r=math.radians(a);s=14
 yf=BACK+s*(.8*math.cos(r)-math.sin(r));hw=17+3*max(0,math.cos(r))
 quad=[(CX-17,BACK),(CX+17,BACK),(CX+hw,yf),(CX-hw,yf)]
 mask=polygon(quad)
 top=yf>BACK
 if seen_from_below:
  paint(f,gradient(mask,28,yf,68,BACK+4),LN,.05)
  f.line((CX-15,BACK+1),(CX+15,BACK+1),'lin0',1)
 else:
  paint(f,gradient(mask,CX-hw,yf,CX+hw,BACK),WD)
  for u in (-.55,.55):   # the two bands run from the hinge to the lip
   x0=CX+u*17;x1=CX+u*hw;f.line((x0,BACK+1),(x1,yf),'metal1',3)
  f.line((CX-17,BACK),(CX+17,BACK),'wood0',1)
 if a<60:   # the lip: the lid's front face, shorter as it turns
  h=max(2,round(6*math.cos(r)));lip=polygon([(CX-hw,yf),(CX+hw,yf),(CX+hw,yf+h),(CX-hw,yf+h)])
  paint(f,gradient(lip,0,yf,0,yf+h,.1,.7),WD,.05)
  for u in (-.55,.55):f.line((CX+u*hw,yf),(CX+u*hw,yf+h),'metal1',3)
  if a<30:f.flat(polygon([(CX-3,yf-1),(CX+3,yf-1),(CX+3,yf+h+4),(CX-3,yf+h+4)]),'metal2',True)   # the hasp

def body(f,a):
 """Interior (lit by what is inside), then the front face with its bands and lock."""
 g=max(0,min(1,(a-8)/55))
 inner=polygon([(CX-17,BACK),(CX+17,BACK),(CX+20,FRONT),(CX-20,FRONT)])
 fill='dark' if g<.15 else 'metal0' if g<.45 else 'metal1' if g<.8 else 'metal2'
 f.flat(inner,fill,True)
 if a>=20:
  paint(f,ellipsoid(CX,FRONT-4,17,5),MT,.4)
  for dx,dy in ((-9,-5),(-3,-7),(5,-6),(10,-4),(0,-4)):f.dots([(CX+dx,FRONT+dy),(CX+dx+1,FRONT+dy)],'glow')
 front=polygon([(CX-20,FRONT),(CX+20,FRONT),(CX+20,BASE),(CX-20,BASE)])
 paint(f,gradient(front,28,FRONT,68,BASE,.25,.9),WD)
 f.line((CX-20,FRONT+8),(CX+19,FRONT+8),'wood0',1)
 f.line((CX-20,BASE-5),(CX+19,BASE-5),'wood0',1)
 for u in (-14,14):
  f.flat(polygon([(CX+u-3,FRONT),(CX+u+3,FRONT),(CX+u+3,BASE),(CX+u-3,BASE)]),'metal1',True)
  f.line((CX+u-1,FRONT+1),(CX+u-1,BASE-1),'metal2',1)
  f.dots([(CX+u,FRONT+4),(CX+u,BASE-4)],'metal0')
 f.flat(polygon([(CX-5,FRONT+2),(CX+5,FRONT+2),(CX+5,FRONT+13),(CX-5,FRONT+13)]),'metal1',True)   # the lock plate
 f.line((CX-4,FRONT+3),(CX+4,FRONT+3),'metal2',1)
 f.dots([(CX,FRONT+7),(CX,FRONT+8),(CX,FRONT+9)],'dark')
 for x in (CX-19,CX+16):f.flat(polygon([(x,BASE),(x+3,BASE),(x+3,BASE+2),(x,BASE+2)]),'wood0',True)   # feet

SPARKS=[(34,34),(60,36),(40,29),(56,30),(48,27),(30,44),(66,45)]
def draw(clip,n):
 f=Frame(P)
 if clip=='closed':
  body(f,0);lid(f,0,False)
  x=[32,40,48,56,64,48][n];y=[52,50,49,50,52,50][n]
  if n==5:x,y=44,51
  star(f,x,y,n==2 or n==5)
 else:
  a=ANGLES[n] if clip=='opening' else 105
  below=a>=45
  if below:lid(f,a,True);body(f,a)
  else:body(f,a);lid(f,a,False)
  if clip=='opening' and a>=25:
   for k in range(min(n-1,len(SPARKS))):star(f,*SPARKS[k])
  if clip=='opened':
   for k,(x,y) in enumerate(SPARKS):
    if (k+n)%2==0:star(f,x,y,k%3==0)
 colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255] for j,c in enumerate(P.hex)],dtype=np.uint8)
 image=colors[f.a]
 return Image.fromarray(image,'RGBA'),f.a[CROP[1]:CROP[1]+SIZE,CROP[0]:CROP[0]+SIZE].copy()

def grids():
 out={}
 for clip,count,_ in CLIPS:
  out[clip]=[]
  for n in range(count):
   grid=draw(clip,n)[1]
   ys,xs=np.nonzero(grid)
   assert len(xs) and xs.min()>0 and xs.max()<SIZE-1 and ys.min()>0 and ys.max()<SIZE-1,(clip,n,'edge',xs.min(),xs.max(),ys.min(),ys.max())
   out[clip].append(grid)
  assert len({g.tobytes() for g in out[clip]})==count,(clip,'duplicate frames')
 return out

def rgba(grid):
 colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255] for j,c in enumerate(P.hex)],dtype=np.uint8)
 return Image.fromarray(colors[grid],'RGBA')

def metadata(sprite):
 start=0;clips={}
 for row,(clip,count,fps) in enumerate(CLIPS):
  clips[clip]=dict(fps=fps,n=count,row=row,editorStart=start);start+=count
 return dict(frame=[SIZE,SIZE],anchor=[32,48],clips=clips,sprite=sprite)

def _pf():
 sys.path.insert(0,str(Path.home()/'.claude/skills/makesprites'))
 import pf
 return pf

GROUNDS=[('grass','#5f8f4a'),('sand','#d9c58f'),('snow','#e9f0f5'),('stone','#7d7f86'),('water','#3d79a8'),('dark','#241f2b')]
def preview():
 data=grids()
 frames=[(c,n) for c,count,_ in CLIPS for n in range(count)]
 cell=SIZE*2
 sheet=Image.new('RGB',(7*cell+10,len(GROUNDS)*2*cell+10),'#444')
 for gi,(name,col) in enumerate(GROUNDS):
  for fi,(clip,n) in enumerate(frames):
   tile=Image.new('RGB',(cell,cell),col)
   img=rgba(data[clip][n]).resize((cell,cell),Image.Resampling.NEAREST)
   tile.paste(img,(0,0),img)
   sheet.paste(tile,(5+(fi%7)*cell,5+(gi*2+fi//7)*cell))
 out=ROOT/'test-results/chest-cast.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)

def build():
 path=ASSETS/'chest.txt'
 if path.exists():raise SystemExit('Chest sprite already exists; export preserves edits.')
 api=_pf();data=grids()
 np.savez_compressed(ROOT/'scripts/chest_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
 sid=api.create('valhallasc_chest',SIZE,SIZE,sum(c for _,c,_ in CLIPS),P.hex,fps=6)
 try:
  frame=0
  for clip,count,_ in CLIPS:
   for grid in data[clip]:api.draw_grid(sid,frame,0,grid);frame+=1
 except Exception:
  api.api('delete',{'sprite_id':sid});raise
 path.write_text(json.dumps(metadata(sid),indent=2)+'\n');print('chest',sid)

def export(verify=False):
 api=_pf();path=ASSETS/'chest.txt';sid=json.loads(path.read_text())['sprite']
 total=sum(c for _,c,_ in CLIPS)
 sp,frames=api.load(sid);assert (sp['width'],sp['height'],len(frames))==(SIZE,SIZE,total)
 out=Image.new('RGBA',(SIZE*6,SIZE*len(CLIPS)));offset=0
 for row,(clip,count,_) in enumerate(CLIPS):
  for n in range(count):out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*SIZE,row*SIZE))
  offset+=count
 target=ASSETS/'chest.png'
 if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),'chest';print('Chest PixelFlow atlas verified')
 else:out.save(target,optimize=True);print('exported chest')

if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build()
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 else:raise SystemExit('preview | build | export | verify')
