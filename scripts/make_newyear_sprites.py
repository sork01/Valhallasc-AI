#!/usr/bin/env python3
"""Original Starfire Rocketeer, five clips; persisted PixelFlow source and export."""
import json,math,sys
from pathlib import Path
from PIL import Image,ImageDraw
import mount_models as models
import mount_toon as toon
import make_mount_sprites as mounts
ROOT=Path(__file__).resolve().parents[1]
CLIPS={'idle':(6,6),'walk':(10,8),'attack':(12,8),'hurt':(10,4),'die':(8,8)}
MATS={'coat':['#282743','#46496d','#6b78a0','#9bafd1'],
 'red':['#692c4b','#a24764','#d96a80','#ffa297'],
 'skin':['#6c473d','#ac7152','#dcaa78','#f9d7a1'],
 'gold':models.GOLD,'white':models.WHITE,
 'eye':['#141c2e']*4,'flame':['#b24a32','#e7863f','#ffd582','#fff5bf']}
LOOK=toon.Look(MATS,{'eye':0,'white':3,'flame':2})
def frame(clip,k,n):
    ph=math.tau*k/n;walk=clip=='walk';swing=math.sin(math.pi*k/(n-1)) if clip=='attack' else 0
    bob=abs(math.sin(ph))*1.3 if walk else math.sin(ph)*.6
    prims=[toon.Ell((0,0,27+bob),(12,8,16),'coat'),toon.Ell((0,0,42+bob),(10,7,5),'red'),
           toon.Ell((0,0,18+bob),(12,8,2),'gold')]
    for side in [-1,1]:
        foot=toon.V(side*6,(math.cos(ph+(side>0)*math.pi)*5 if walk else 0),3)
        prims += [toon.limb((side*6,0,18+bob),foot,3.4,'coat'),toon.Ell(foot+toon.V(0,2,0),(4,5.5,3),'red')]
        hand=toon.V(side*17,4,30+bob+(14*swing if side==1 else 0))
        prims += [toon.limb((side*9,0,40+bob),hand,3.8,'coat'),toon.Ell(hand,(3,3,3),'skin')]
        if side==1:
            # Held brass firework wand with a flame-shaped star, not a normal gun.
            tip=hand+toon.V(0,2,22)
            prims += [toon.limb(hand,tip,1.4,'gold'),toon.Ell(tip,(4.5,3,5),'flame')]
            for a in range(5):
                ang=math.tau*a/5
                prims += [toon.cone(tip,tip+toon.V(math.cos(ang)*9,0,math.sin(ang)*9),2,'gold')]
    head=toon.V(0,0,54+bob)
    prims += [toon.Ell(head,(9,7,10),'skin'),toon.Ell(head+toon.V(0,0,7),(10,8,4),'coat')]
    for side in [-1,1]:
        eye=head+toon.V(side*4.5,6.5,1.5)
        prims += [toon.Ell(eye,(3.5,1.4,3.5),'gold'),toon.Ell(eye+toon.V(0,1,0),(2,1,2),'eye')]
    prims += [toon.Ell(head+toon.V(0,6,-4),(6,2.5,2),'white'),
              toon.cone(head+toon.V(0,0,9),head+toon.V(0,-1,25),8,'coat'),
              toon.Ell(head+toon.V(0,-1,25),(3,3,3),'gold')]
    # Two red/gold rockets on a backpack create a distinct silhouette.
    for side in [-1,1]:
        base=toon.V(side*10,-8,28+bob)
        prims += [toon.limb(base,base+toon.V(0,0,23),4.4,'red'),
                  toon.cone(base+toon.V(0,0,23),base+toon.V(0,0,31),4.5,'gold')]
    fall=k/(n-1) if clip=='die' else 0
    for p in prims:
        if fall:p.c[2]*=1-fall*.82;p.c[1]-=fall*7
    idx,_=toon.render(prims,toon.psi_for('SE'),LOOK,flash=clip=='hurt' and k==0)
    out=idx[34:130,32:128].copy()
    assert not(out[0].any() or out[-1].any() or out[:,0].any() or out[:,-1].any()),(clip,k)
    return out

def build():
    path=ROOT/'client/assets/newyear.txt'
    assert not path.exists(),'Preserve existing source: use export after PixelFlow edits'
    pf=mounts.pixel_api();sid=pf.create('valhallasc_newyear_starrocketeer_all',96,96,34,LOOK.palette,fps=10)
    # Save provenance immediately, including if a later API request needs retry.
    path.write_text(json.dumps(dict(sprites={'starrocketeer':sid}),indent=2)+'\n')
    i=0
    for clip,(_,n) in CLIPS.items():
        for k in range(n):
            grid=frame(clip,k,n)
            pf.draw_grid(sid,i,0,grid);i+=1
    print('PixelFlow Starfire Rocketeer',sid,flush=True)
def export():
    pf=mounts.pixel_api();path=ROOT/'client/assets/newyear.txt';meta=json.loads(path.read_text());sp,frames=pf.load(meta['sprites']['starrocketeer']);assert len(frames)==34
    atlas=Image.new('RGBA',(768,480));offset=0;clips={}
    for row,(clip,(fps,n)) in enumerate(CLIPS.items()):
        for k in range(n):atlas.paste(Image.fromarray(pf.to_rgba(frames[offset+k][0],sp['palette'])),(k*96,row*96))
        clips[clip]=dict(fps=fps,n=n,row=row,editorStart=offset);offset+=n
    atlas.save(ROOT/'client/assets/newyear_starrocketeer.png',optimize=True)
    meta.update(frame=[96,96],anchor=[48,90],kinds=['starrocketeer'],clips=clips)
    path.write_text(json.dumps(meta,indent=2)+'\n')
    print('Exported saved Starfire Rocketeer',flush=True)
if __name__=='__main__':
    {'build':build,'export':export}[sys.argv[1]]()
