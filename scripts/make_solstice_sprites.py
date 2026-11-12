#!/usr/bin/env python3
"""Original birch-bark sun guardian, saved/exported through PixelFlow."""
import json,math,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import mount_models as models
import mount_toon as toon
import make_mount_sprites as mounts
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__' and (ROOT/'scripts/shared_slime_sources.txt').exists():
 import shared_slime_redraw as shared
 command=sys.argv[1] if len(sys.argv)>1 else 'preview'
 assert command not in ('update','refresh') and '--replace' not in sys.argv,'Use shared_slime_redraw.py refresh birchcrown to overwrite candidate frames explicitly'
 if command=='build':shared.build(['birchcrown'])
 else:dict(preview=shared.preview,export=shared.export,verify=shared.verify)[command]()
 raise SystemExit(0)

CLIPS={'idle':(6,6),'walk':(10,8),'attack':(12,8),'hurt':(10,4),'die':(8,8)}
MATS={'moss':['#294138','#47694b','#72955e','#b2c98a'],
 'bark':['#6a715a','#a0a58b','#d7d7bc','#faf0d3'],
 'petal':['#bd9c3c','#d8b94d','#efd372','#fff1ba'],
 'egg':['#315b70','#528ca2','#9fbfbd','#dbe2ba'],
 'eye':['#182f2b']*4,'gold':models.GOLD,'white':models.WHITE}
LOOK=toon.Look(MATS,{'eye':0,'white':3})
def frame(clip,k,n):
 ph=math.tau*k/n;walk=clip=='walk';swing=math.sin(math.pi*k/(n-1)) if clip=='attack' else 0
 bob=abs(math.sin(ph))*1.2 if walk else math.sin(ph)*.5
 prims=[toon.Ell((0,0,28+bob),(13,9,17),'bark'),toon.Ell((0,1,41+bob),(14,9,9),'moss')]
 for side in [-1,1]:
  foot=toon.V(side*8,math.cos(ph+(side>0)*math.pi)*5 if walk else 0,3)
  hand=toon.V(side*(19+3*swing),4+6*swing,28+bob+15*swing)
  prims += [toon.limb((side*7,0,24+bob),foot,4.5,'bark'),toon.Ell(foot+toon.V(0,3,0),(5,7,3),'moss'),
            toon.limb((side*11,0,42+bob),hand,4.2,'bark'),toon.Ell(hand,(4,4,5),'moss'),
            toon.Ell((side*12,1,43+bob),(7,6,6),'moss'),toon.Ell((side*12,5,43+bob),(4,1,4),'bark')]
 for i in range(5):
  prims += [toon.Ell(((-1)**i*4,8,18+i*5+bob),(5,1,.7),'eye')]
 head=toon.V(0,1,56+bob)
 prims += [toon.Ell(head,(10,8,11),'moss'),toon.Ell(head+toon.V(0,6,-2),(8,4,5),'moss')]
 for side in [-1,1]:
  prims += [toon.Ell(head+toon.V(side*4,7,1),(2,1.2,2.5),'gold'),toon.Ell(head+toon.V(side*4,8,1),(1,.7,1.8),'eye')]
 for i in range(9):
  a=math.tau*i/9;c=head+toon.V(math.cos(a)*8,math.sin(a)*6,8+math.sin(a)*1.5)
  prims += [toon.Ell(c,(2.4,2,6),'petal'),toon.Ell(c+toon.V(0,0,-2),(3,2,1),'gold')]
 for i in range(3):
  c=toon.V((i-1)*6,8,30+bob)
  prims += [toon.Ell(c,(3.5,1.3,5),'gold'),toon.Ell(c+toon.V(0,1,0),(1,1,2),'petal')]
 base=toon.V(21,4,9+bob+10*swing);tip=base+toon.V(-4,-1,55)
 prims += [toon.limb(base,tip,1.8,'bark')]
 for i in range(4):
  c=tip+toon.V((i-1.5)*3,0,-i*2)
  prims += [toon.Ell(c,(3,2,5),'petal'),toon.Ell(c+toon.V(-2,0,-5),(3,2,1.2),'moss')]
 fall=k/(n-1) if clip=='die' else 0
 if fall:
  for p in prims:p.c[2]=p.c[2]*(1-fall*.78)+3*fall;p.r[2]*=1-fall*.65
 idx,_=toon.render(prims,toon.psi_for('SE'),LOOK,flash=clip=='hurt' and k==0)
 out=idx[34:130,32:128].copy()
 assert not(out[0].any() or out[-1].any() or out[:,0].any() or out[:,-1].any()),(clip,k)
 return out

def render():return {c:[frame(c,k,n) for k in range(n)] for c,(_,n) in CLIPS.items()}
def preview(frames):
 out=ROOT/'test-results/solstice-art';out.mkdir(parents=True,exist_ok=True);table=LOOK.rgba_table()
 for c,rows in frames.items():
  sheet=Image.new('RGBA',(96*len(rows),110),'#344955');g=ImageDraw.Draw(sheet)
  for k,grid in enumerate(rows):sheet.alpha_composite(Image.fromarray(table[grid]),(k*96,0));g.text((k*96+3,96),f'{c} {k}',fill='white')
  sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(out/f'birchcrown_{c}.png')
def build(frames,update=False):
 pf=mounts.pixel_api();path=ROOT/'client/assets/solstice.txt';meta=json.loads(path.read_text()) if path.exists() else {};saved=meta.get('sprites',{}).get('birchcrown');assert update or not saved,'Use export to preserve saved art'
 sid=saved if update else pf.create('valhallasc_solstice_birchcrown_all',96,96,34,LOOK.palette,fps=10)
 i=0
 for rows in frames.values():
  for grid in rows:
   response=pf.api('draw',{'sprite_id':sid,'frame':i,'ops':[{'op':'grid','rows':grid.tolist(),'layer':0,'x':0,'y':0}]});assert response.get('ok'),response;i+=1
 meta['sprites']={'birchcrown':sid};path.write_text(json.dumps(meta,indent=2)+'\n');print('PixelFlow Birchcrown Guardian',sid,flush=True)
def export():
 pf=mounts.pixel_api();path=ROOT/'client/assets/solstice.txt';meta=json.loads(path.read_text());sp,frames=pf.load(meta['sprites']['birchcrown']);assert len(frames)==34
 atlas=Image.new('RGBA',(768,480));offset=0;clips={}
 for row,(c,(fps,n)) in enumerate(CLIPS.items()):
  for k in range(n):atlas.paste(Image.fromarray(pf.to_rgba(frames[offset+k][0],sp['palette'])),(k*96,row*96))
  clips[c]=dict(fps=fps,n=n,row=row,editorStart=offset);offset+=n
 atlas.save(ROOT/'client/assets/solstice_birchcrown.png',optimize=True);meta.update(frame=[96,96],anchor=[48,90],kinds=['birchcrown'],clips=clips);path.write_text(json.dumps(meta,indent=2)+'\n');print('Exported saved Birchcrown Guardian art',flush=True)
if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if command in ['preview','build','update']:
  frames=render();preview(frames)
  if command!='preview':build(frames,command=='update')
 elif command=='export':export()
