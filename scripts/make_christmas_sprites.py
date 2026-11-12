#!/usr/bin/env python3
"""Original Grinch elite: 34 cel frames, saved through PixelFlow and exported."""
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
 assert command not in ('update','refresh') and '--replace' not in sys.argv,'Use shared_slime_redraw.py refresh grinch to overwrite candidate frames explicitly'
 if command=='build':shared.build(['grinch'])
 else:dict(preview=shared.preview,export=shared.export,verify=shared.verify)[command]()
 raise SystemExit(0)

CLIPS={'idle':(6,6),'walk':(10,8),'attack':(12,8),'hurt':(10,4),'die':(8,8)}
MATS={'fur':['#285331','#4b7d32','#83b441','#b8db67'],
 'coat':['#601e35','#a52e3c','#d6504a','#f17b62'],
 'trim':['#b5b6a3','#dbdac2','#f0ecd4','#fff9e4'],
 'sack':['#493b24','#75623a','#a08a50','#d6bd72'],
 'ribbon':['#4e203e','#943e5b','#d66a85','#f69eae'],
 'eye':['#1b2924']*4,'iris':['#bda744','#e5cc57','#fff180','#fff9bd'],
 'gold':models.GOLD,'white':models.WHITE,'leather':models.LEATHER}
LOOK=toon.Look(MATS,{'eye':0,'white':3})

def frame(clip,k,n):
 ph=math.tau*k/n;run=clip=='walk';swing=math.sin(math.pi*k/(n-1)) if clip=='attack' else 0
 bob=abs(math.sin(ph))*1.3 if run else math.sin(ph)*.55
 prims=[toon.Ell((0,0,26+bob),(13,9,16),'coat'),toon.Ell((0,0,40+bob),(9,7,10),'coat'),
        toon.Ell((0,-2,43+bob),(10,7,4),'trim'),toon.Ell((0,0,15+bob),(13,9,2.3),'trim')]
 # Long green fingers, a stolen present sack and a broad, mischievous furry face.
 for side in [-1,1]:
  hip=toon.V(side*6,0,16+bob);foot=toon.V(side*7,(math.cos(ph+(side>0)*math.pi)*5 if run else 0),2)
  prims += [toon.limb(hip,foot,3.3,'fur'),toon.Ell(foot+toon.V(0,3,0),(4,6,3),'fur')]
  shoulder=toon.V(side*9,0,42+bob);hand=toon.V(side*(18+5*swing),6+side*math.sin(ph)*2,27+bob+20*swing)
  prims += [toon.limb(shoulder,hand,4,'coat'),toon.Ell(hand,(4,3,3),'trim')]
  for finger in range(3):prims += [toon.cone(hand+toon.V((finger-1)*1.7,2,-1),hand+toon.V((finger-1)*2.2,6+finger%2,-4),1,'fur')]
 head=toon.V(0,1,54+bob)
 prims += [toon.Ell(head,(11,8.3,10),'fur'),toon.Ell(head+toon.V(0,5,-4),(10,5.5,5.7),'fur'),
           toon.Ell(head+toon.V(0,8.8,-1),(2.8,2.3,2),'fur')]
 for side in [-1,1]:
  prims += [toon.Ell(head+toon.V(side*5,7,2),(3.4,1.2,2.4),'iris'),toon.Ell(head+toon.V(side*5,8.1,2),(1.3,.9,1.8),'eye'),
            toon.limb(head+toon.V(side*2,7,7),head+toon.V(side*9,6,5),1.1,'fur'),
            toon.cone(head+toon.V(side*9,0,0),head+toon.V(side*15,-1,-3),3,'fur')]
 for i in range(7):
  x=-7+i*2.3;prims += [toon.Ell(head+toon.V(x,8.4,-5+abs(x)*.35),(.95,.9,.65),'eye')]
 # Drooping red Santa cap with cream brim and pompom.
 prims += [toon.Ell(head+toon.V(0,-1,8),(10.5,8,2),'trim'),toon.cone(head+toon.V(0,-1,9),head+toon.V(4,-2,24),8.8,'coat'),
           toon.cone(head+toon.V(4,-2,23),head+toon.V(12,-2,15),3.6,'coat'),toon.Ell(head+toon.V(13,-2,14),(3.5,3.5,3.5),'trim'),
           toon.Ell((-12,-7,28+bob),(9,7,13),'sack'),toon.limb((-12,-7,40+bob),(-8,-2,44+bob),1.8,'ribbon'),
           toon.Ell((-16,-8,37+bob),(5,5,4),'coat'),toon.limb((-21,-8,37+bob),(-11,-8,37+bob),1,'gold')]
 fall=k/(n-1) if clip=='die' else 0
 if fall:
  for p in prims:p.c[2]*=1-fall*.83;p.c[1]-=fall*8
 idx,_=toon.render(prims,toon.psi_for('SE'),LOOK,flash=clip=='hurt' and k==0)
 out=idx[34:130,32:128].copy()
 assert not(out[0].any() or out[-1].any() or out[:,0].any() or out[:,-1].any()),(clip,k)
 return out

def render():return {c:[frame(c,k,n) for k in range(n)] for c,(_,n) in CLIPS.items()}
def preview(frames):
 out=ROOT/'test-results/christmas-art';out.mkdir(parents=True,exist_ok=True);table=LOOK.rgba_table()
 for c,rows in frames.items():
  sheet=Image.new('RGBA',(96*len(rows),110),'#344955');g=ImageDraw.Draw(sheet)
  for k,grid in enumerate(rows):sheet.alpha_composite(Image.fromarray(table[grid]),(k*96,0));g.text((k*96+3,96),f'{c} {k}',fill='white')
  sheet.resize((sheet.width*3,sheet.height*3),Image.Resampling.NEAREST).save(out/f'grinch_{c}.png')
def build(frames,update=False):
 pf=mounts.pixel_api();path=ROOT/'client/assets/christmas.txt';meta=json.loads(path.read_text()) if path.exists() else {};saved=meta.get('sprites',{}).get('grinch');assert update or not saved,'Use export to preserve saved art'
 sid=saved if update else pf.create('valhallasc_christmas_grinch_all',96,96,34,LOOK.palette,fps=10)
 i=0
 for rows in frames.values():
  for grid in rows:
   response=pf.api('draw',{'sprite_id':sid,'frame':i,'ops':[{'op':'grid','rows':grid.tolist(),'layer':0,'x':0,'y':0}]});assert response.get('ok'),response;i+=1
 meta['sprites']={'grinch':sid};path.write_text(json.dumps(meta,indent=2)+'\n');print('PixelFlow Grinch',sid,flush=True)
def export():
 pf=mounts.pixel_api();path=ROOT/'client/assets/christmas.txt';meta=json.loads(path.read_text());sp,frames=pf.load(meta['sprites']['grinch']);assert len(frames)==34
 atlas=Image.new('RGBA',(768,480));offset=0;clips={}
 for row,(c,(fps,n)) in enumerate(CLIPS.items()):
  for k in range(n):atlas.paste(Image.fromarray(pf.to_rgba(frames[offset+k][0],sp['palette'])),(k*96,row*96))
  clips[c]=dict(fps=fps,n=n,row=row,editorStart=offset);offset+=n
 atlas.save(ROOT/'client/assets/christmas_grinch.png',optimize=True);meta.update(frame=[96,96],anchor=[48,90],kinds=['grinch'],clips=clips);path.write_text(json.dumps(meta,indent=2)+'\n');print('Exported saved Grinch art',flush=True)
if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if command in ['preview','build','update']:
  frames=render();preview(frames)
  if command!='preview':build(frames,command=='update')
 elif command=='export':export()
