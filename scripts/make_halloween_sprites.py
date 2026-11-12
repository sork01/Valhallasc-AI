#!/usr/bin/env python3
"""Original Hollow Rider: render 34 frames, save/edit via PixelFlow, export the saved atlas."""
import json
import math
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
import mount_models as models
import mount_toon as toon
import make_mount_sprites as mounts
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__' and (ROOT/'scripts/shared_slime_sources.txt').exists():
 import shared_slime_redraw as shared
 command=sys.argv[1] if len(sys.argv)>1 else 'preview'
 assert command not in ('update','refresh') and '--replace' not in sys.argv,'Use shared_slime_redraw.py refresh hollow_rider to overwrite candidate frames explicitly'
 if command=='build':shared.build(['hollow_rider'])
 else:dict(preview=shared.preview,export=shared.export,verify=shared.verify)[command]()
 raise SystemExit(0)

CLIPS={'idle':(6,6),'walk':(10,8),'attack':(12,8),'hurt':(10,4),'die':(8,8)}
MATS={**models.NIGHTMARE,'pumpkin':['#683025','#b64e21','#e28a2b','#ffc658'],'ember':['#ffe2a1','#ffe3a2','#ffe4a3','#ffe5a4'],'cloak':['#201726','#34243b','#53334d','#815066']}
LOOK=toon.Look(MATS,{**models.FLAT,'flame':2,'ember':3})

def frame(clip,k,n):
    prims,bob=models.nightmare('run' if clip=='walk' else 'idle',k,n)
    ph=math.tau*k/n;swing=math.sin(math.pi*k/(n-1)) if clip=='attack' else 0
    fall=(k/(n-1)) if clip=='die' else 0
    z=46+bob
    prims += [toon.Ell((0,-8,z+24),(11,6,23),'cloak'),toon.Ell((0,-1,z+28),(8,6,14),'armor'),toon.Ell((0,-1,z+43),(11,7,3),'armor'),toon.Ell((0,-1,z+45),(5,4,1.2),'coat2')]
    for side in [-1,1]:
        prims += [toon.Ell((side*10,-1,z+39),(5,5,5),'armor'),toon.limb((side*8,-1,z+36),(side*16,6,z+24),3.4,'armor'),toon.limb((side*8,-1,z+12),(side*12,8,z-3),3.2,'armor')]
    # A held, carved jack-o'-lantern, not a head on the open collar.
    pumpkin=toon.V(19,10,z+30+swing*6)
    prims += [toon.Ell(pumpkin,(12,11,12),'pumpkin'),toon.cone(pumpkin+toon.V(0,0,9),pumpkin+toon.V(2,-1,15),2,'gold')]
    for y in [-4,4]:prims += [toon.Ell(pumpkin+toon.V(10,y,3),(1.8,2,2.5),'ember')]
    prims += [toon.Ell(pumpkin+toon.V(11,0,-4),(1.5,5,1.8),'ember')]
    # Sweeping crescent scythe: a distinct windup silhouette and visible follow-through.
    a=toon.V(-16,1,z+12);b=toon.V(-16+7*swing,17,z+61-22*swing)
    prims += [toon.limb(a,b,1.6,'gold')]
    for i in range(6):
        f=i/5;q=b+toon.V(-i*3.2,math.sin(f*math.pi)*5,-f*6)
        prims += [toon.Ell(q,(3.8,1.1,1.5),'armor'),toon.Ell(q+toon.V(0,1,.6),(3.3,.7,.8),'ember')]
    if fall:
        for p in prims:p.c[2]=p.c[2]*(1-fall*.78);p.c[0]+=math.sin(p.c[1]*.08)*fall*5
    idx,_=toon.render(prims,toon.psi_for('E'),LOOK,flash=clip=='hurt' and k==0)
    # Render at native class resolution, then place the sprite around the enemy anchor (48,90).
    image=Image.fromarray(idx).resize((88,88),Image.Resampling.NEAREST)
    out=np.zeros((96,96),np.uint8);out[22:96,4:92]=np.asarray(image)[:74]
    assert not(out[0].any() or out[-1].any() or out[:,0].any() or out[:,-1].any()),(clip,k)
    return out

def render():return {c:[frame(c,k,n) for k in range(n)] for c,(_,n) in CLIPS.items()}

def preview(frames):
    out=ROOT/'test-results/nightmare-art';out.mkdir(parents=True,exist_ok=True);table=LOOK.rgba_table()
    for c,items in frames.items():
        sheet=Image.new('RGBA',(96*len(items),110),'#384834');g=ImageDraw.Draw(sheet)
        for k,f in enumerate(items):sheet.alpha_composite(Image.fromarray(table[f]),(k*96,0));g.text((k*96+4,96),f'{c} {k}',fill='white')
        sheet.resize((sheet.width*2,sheet.height*2),Image.Resampling.NEAREST).save(out/f'hollow_rider_{c}.png')

def build(frames,update=False):
    pf=mounts.pixel_api();path=ROOT/'client/assets/halloween.txt';meta=json.loads(path.read_text()) if path.exists() else {}
    saved=meta.get('sprites',{}).get('hollow_rider')
    assert update or not saved,'Use export to preserve saved art'
    sid=saved if update else pf.create('valhallasc_halloween_hollow_rider_all',96,96,34,LOOK.palette,fps=10)
    i=0
    for items in frames.values():
        for grid in items:
            r=pf.api('draw',{'sprite_id':sid,'frame':i,'ops':[{'op':'grid','rows':grid.tolist(),'layer':0,'x':0,'y':0}]});assert r.get('ok'),r;i+=1
    meta['sprites']={'hollow_rider':sid};path.write_text(json.dumps(meta,indent=2)+'\n');print('PixelFlow Hollow Rider',sid,flush=True)

def export():
    pf=mounts.pixel_api();path=ROOT/'client/assets/halloween.txt';meta=json.loads(path.read_text());sp,frames=pf.load(meta['sprites']['hollow_rider']);assert len(frames)==34
    atlas=Image.new('RGBA',(96*8,96*5));offset=0;clips={}
    for row,(c,(fps,n)) in enumerate(CLIPS.items()):
        for k in range(n):atlas.paste(Image.fromarray(pf.to_rgba(frames[offset+k][0],sp['palette'])),(k*96,row*96))
        clips[c]=dict(fps=fps,n=n,row=row,editorStart=offset);offset+=n
    atlas.save(ROOT/'client/assets/halloween_hollow_rider.png',optimize=True)
    meta.update(frame=[96,96],anchor=[48,90],kinds=['hollow_rider'],clips=clips)
    path.write_text(json.dumps(meta,indent=2)+'\n');print('Exported saved Halloween elite art',flush=True)

if __name__=='__main__':
    command=sys.argv[1] if len(sys.argv)>1 else 'preview'
    if command in ['preview','build','update']:
        frames=render();preview(frames)
        if command in ['build','update']:build(frames,command=='update')
    elif command=='export':export()
