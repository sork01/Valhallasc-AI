#!/usr/bin/env python3
"""Original rose-armoured thorn guardian, saved/exported through PixelFlow."""
import json,math,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import mount_models as models
import mount_toon as toon
import make_mount_sprites as mounts
ROOT=Path(__file__).resolve().parents[1]
CLIPS={'idle':(6,6),'walk':(10,8),'attack':(12,8),'hurt':(10,4),'die':(8,8)}
MATS={'bark':['#2d2638','#513448','#785064','#ab7b86'],
 'leaf':['#173b36','#2c6251','#509274','#8bb997'],
 'rose':['#5d163d','#9c2756','#d94477','#ff8ba5'],
 'heart':['#a44261','#e18098','#ffb9c7','#fff0db'],
 'eye':['#171f29']*4,'gold':models.GOLD,'white':models.WHITE}
LOOK=toon.Look(MATS,{'eye':0,'white':3})
def frame(clip,k,n):
 ph=math.tau*k/n;walk=clip=='walk';swing=math.sin(math.pi*k/(n-1)) if clip=='attack' else 0
 bob=abs(math.sin(ph))*1.2 if walk else math.sin(ph)*.5
 prims=[toon.Ell((0,0,29+bob),(12,8,16),'bark'),toon.Ell((0,1,40+bob),(14,8,9),'leaf')]
 for side in [-1,1]:
  foot=toon.V(side*8,math.cos(ph+(side>0)*math.pi)*5 if walk else 0,3)
  prims += [toon.limb((side*6,0,23+bob),foot,4,'bark'),toon.Ell(foot+toon.V(0,3,0),(5,7,3),'bark')]
  hand=toon.V(side*(19+6*swing),4+9*swing,24+bob+18*swing)
  prims += [toon.limb((side*11,0,41+bob),hand,4,'bark'),toon.Ell(hand,(4,4,5),'leaf')]
  for i in range(3):
   prims += [toon.cone((side*(10+i*2),-1,41+bob-i*2),(side*(16+i*3),-1,50+bob-i*3),2.4,'gold')]
  for i in range(3):
   prims += [toon.cone(hand+toon.V((i-1)*2,2,0),hand+toon.V((i-1)*2,5,-8),1.3,'bark')]
 # Layered petals form a tall asymmetric rose head around a glowing seed face.
 head=toon.V(0,1,56+bob)
 prims += [toon.Ell(head,(8,7,9),'heart')]
 for ring,count in [(0,7),(1,5)]:
  for i in range(count):
   a=math.tau*i/count+ring*.7
   prims += [toon.Ell(head+toon.V(math.cos(a)*(9-ring*3),-2+math.sin(a)*4,math.sin(a)*8+ring*2),(5.2-ring,4,7-ring),'rose')]
 for side in [-1,1]:
  prims += [toon.Ell(head+toon.V(side*3,7,1),(1.2,1,2),'eye'),toon.cone((side*7,-2,59+bob),(side*14,-5,74+bob),2.5,'gold')]
 prims += [toon.Ell((0,8,35+bob),(5,2,5),'heart')]
 for i in range(5):
  prims += [toon.cone((0,-6,28+i*4+bob),(math.sin(i)*6,-10,31+i*4+bob),1.8,'leaf')]
 fall=k/(n-1) if clip=='die' else 0
 if fall:
  for p in prims:p.c[2]*=1-fall*.83;p.c[1]-=fall*7
 idx,_=toon.render(prims,toon.psi_for('SE'),LOOK,flash=clip=='hurt' and k==0)
 out=idx[34:130,32:128].copy()
 assert not(out[0].any() or out[-1].any() or out[:,0].any() or out[:,-1].any()),(clip,k)
 return out

def render():return {c:[frame(c,k,n) for k in range(n)] for c,(_,n) in CLIPS.items()}
def preview(frames):
 out=ROOT/'test-results/valentines-art';out.mkdir(parents=True,exist_ok=True);table=LOOK.rgba_table()
 for c,rows in frames.items():
  sheet=Image.new('RGBA',(96*len(rows),110),'#344955');g=ImageDraw.Draw(sheet)
  for k,grid in enumerate(rows):sheet.alpha_composite(Image.fromarray(table[grid]),(k*96,0));g.text((k*96+3,96),f'{c} {k}',fill='white')
  sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(out/f'briarheart_{c}.png')
def build(frames,update=False):
 pf=mounts.pixel_api();path=ROOT/'client/assets/valentines.txt';meta=json.loads(path.read_text()) if path.exists() else {};saved=meta.get('sprites',{}).get('briarheart');assert update or not saved,'Use export to preserve saved art'
 sid=saved if update else pf.create('valhallasc_valentines_briarheart_all',96,96,34,LOOK.palette,fps=10)
 i=0
 for rows in frames.values():
  for grid in rows:
   response=pf.api('draw',{'sprite_id':sid,'frame':i,'ops':[{'op':'grid','rows':grid.tolist(),'layer':0,'x':0,'y':0}]});assert response.get('ok'),response;i+=1
 meta['sprites']={'briarheart':sid};path.write_text(json.dumps(meta,indent=2)+'\n');print('PixelFlow Briarheart',sid,flush=True)
def export():
 pf=mounts.pixel_api();path=ROOT/'client/assets/valentines.txt';meta=json.loads(path.read_text());sp,frames=pf.load(meta['sprites']['briarheart']);assert len(frames)==34
 atlas=Image.new('RGBA',(768,480));offset=0;clips={}
 for row,(c,(fps,n)) in enumerate(CLIPS.items()):
  for k in range(n):atlas.paste(Image.fromarray(pf.to_rgba(frames[offset+k][0],sp['palette'])),(k*96,row*96))
  clips[c]=dict(fps=fps,n=n,row=row,editorStart=offset);offset+=n
 atlas.save(ROOT/'client/assets/valentines_briarheart.png',optimize=True);meta.update(frame=[96,96],anchor=[48,90],kinds=['briarheart'],clips=clips);path.write_text(json.dumps(meta,indent=2)+'\n');print('Exported saved Briarheart art',flush=True)
if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if command in ['preview','build','update']:
  frames=render();preview(frames)
  if command!='preview':build(frames,command=='update')
 elif command=='export':export()
