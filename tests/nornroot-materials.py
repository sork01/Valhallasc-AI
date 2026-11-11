#!/usr/bin/env python3
"""Assert semantic deaths in the actual exported art, including corpse-as-idle controls."""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BACKUP=Path('/media/raid/valhallasc-data/nornroot-slime-original-20261111')
sys.path.insert(0,str(ROOT/'scripts'))
import kindframe
from nornroot_slime_redraw import KINDS
from astral_slime_redraw import PALETTE,TEAL,PURPLE,BROWN,GOLD,AMBER,BONE
from rollback_nornroot_art import without_nornroot
meta=json.loads((ROOT/'client/assets/cathedral.txt').read_text())
base=json.loads((BACKUP/'client/assets/cathedral.txt').read_text())
checks=0


def check(value,label):
    global checks
    assert value,label
    checks+=1
    print(f'{checks}: {label}')


def cell(kind,clip,n):
    w,h,_,_=kindframe.frame_of(meta,kind)
    atlas=Image.open(ROOT/f'client/assets/cathedral_{kind}.png').convert('RGBA')
    row=meta['clips'][clip]['row']
    return np.array(atlas.crop((n*w,row*h,(n+1)*w,(row+1)*h)))


def material(im,ramp):
    colors=np.array([list(bytes.fromhex(PALETTE[i][1:])) for i in ramp])
    return (im[:,:,None,:3]==colors).all(-1).any(-1)&(im[:,:,3]>0)


def bounds(mask):
    y,x=np.nonzero(mask)
    assert len(y),'Material vanished'
    return int(x.min()),int(y.min()),int(x.max()),int(y.max())


check(without_nornroot(meta)==without_nornroot(base) and len([k for k in base['kinds'] if k not in KINDS])==140,'all 140 unrelated Cathedral kinds and manifest fields preserved')
hashes=json.loads((BACKUP/'manifest.txt').read_text())['unrelatedAtlasHashes']
check(all(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest for rel,digest in hashes.items()),f'all {len(hashes)} unrelated native atlases preserved')
selected=os.environ.get('NORNROOT_MATERIAL_KINDS',','.join(KINDS)).split(',')
assert selected and all(k in KINDS for k in selected)
for kind in selected:
    w,h,ax,ay=kindframe.frame_of(meta,kind)
    check((w,h,ax,ay)==(176,172,88,164),f'{kind}: declared frame and anchor')
    attacks=[cell(kind,'attack',n) for n in range(8)]
    deaths=[cell(kind,'die',n) for n in range(8)]
    check(len({im.tobytes() for im in attacks})==8 and len({im.tobytes() for im in deaths})==8,f'{kind}: eight distinct attack and death poses')
    lows=[bounds(im[:,:,3]>0)[3] for im in deaths]
    check(lows[-1]==ay and all(a<=b for a,b in zip(lows,lows[1:])),f'{kind}: death stays grounded or settles monotonically')
    idle,dead=cell(kind,'idle',0),deaths[-1]
    if os.environ.get('MUTATE_MATERIAL')==kind:dead=idle.copy()
    ib,db=bounds(idle[:,:,3]>0),bounds(dead[:,:,3]>0)
    height=lambda b:b[3]-b[1]+1
    width=lambda b:b[2]-b[0]+1
    if kind=='barrow_hound':
        check(height(db)<height(ib)*.7 and width(db)>width(ib)*.8,'Hound: intact anatomy lies low on its side with folded legs')
        check(material(dead,PURPLE).sum()>material(idle,PURPLE).sum()*.60,'Hound: fur and threadbound body survive the fall')
        check(material(idle,TEAL).sum()>0 and material(dead,TEAL).sum()==0,'Hound: glaring eye closes')
    elif kind=='barrow_scarab':
        check(material(dead,AMBER+GOLD).sum()>material(idle,AMBER+GOLD).sum()*.65,'Scarab: hard shell retains its amber volume and lit seam')
        check(material(idle,TEAL).sum()>material(dead,TEAL).sum(),'Scarab: eyes close as legs curl underneath the tipped shell')
        check(abs(width(db)-width(ib))>4,'Scarab: shell tips rigidly instead of remaining upright or melting')
    elif kind=='barrow_spinner':
        check(material(idle,TEAL).sum()>100 and material(dead,TEAL).sum()==0,'Spinner: spectral core and face unravel completely')
        check(height(db)<height(ib)*.5 and material(dead,GOLD).sum()>50,'Spinner: tangible spindle flanges settle on the ground')
    elif kind=='barrow_doorward':
        check(material(idle,TEAL).sum()>0 and material(dead,TEAL).sum()==0,'Arn: amber visor goes dark')
        check(height(db)<height(ib)*.85 and width(db)>width(ib)*.8,'Arn: rigid armour, mace and shield topple sideways')
        check(material(dead,AMBER+GOLD+BROWN).sum()>material(idle,AMBER+GOLD+BROWN).sum()*.65,'Arn: rigid pieces retain volume rather than squash')
    elif kind=='barrow_threadkeeper':
        check(height(db)<height(ib)*.85 and width(db)>width(ib)*.9,'Vessa: cloth and spindle fall sideways')
        check(material(dead,PURPLE).sum()>material(idle,PURPLE).sum()*.65 and len(set(map(tuple,dead[material(dead,PURPLE),:3])))>=4,'Vessa: shaded cloth folds remain after death')
        check(material(idle,TEAL).sum()>0 and material(dead,TEAL).sum()==0,'Vessa: stern eyes close in the fallen hood')
    else:
        check(height(db)<height(ib)*.85 and width(db)>width(ib)*1.05,'King: crowned upright silhouette breaks into a broad fallen corpse')
        check(material(dead,BONE).sum()>100 and material(dead,GOLD).sum()>100,'King: bones and crown remain solid relics')
        check(material(dead,TEAL).sum()<material(idle,TEAL).sum()*.65,'King: hollow eye lights go out; crown jewel remains')
print(f'nornroot-materials: {checks} checks')
