#!/usr/bin/env python3
"""Exported material semantics, retained anatomy and unrelated-art preservation."""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BACKUP=Path('/media/raid/valhallasc-data/emberwake-slime-original-20261111')
sys.path.insert(0,str(ROOT/'scripts'))
import emberwake_slime_redraw as R
from rollback_emberwake_art import without_emberwake
meta=json.loads(R.MANIFEST.read_text());base=json.loads((BACKUP/'client/assets/cathedral.txt').read_text())
checks=0

def check(value,label):
    global checks
    assert value,label
    checks+=1;print(f'{checks}: {label}')

def cell(kind,clip,n):
    w,h,_,_=R.kindframe.frame_of(meta,kind);row=meta['clips'][clip]['row']
    return np.array(Image.open(R.atlas_path(kind)).convert('RGBA').crop((n*w,row*h,(n+1)*w,(row+1)*h)))

def material(im,ramp):
    colors=np.array([list(bytes.fromhex(R.PALETTE[i][1:])) for i in ramp])
    return (im[:,:,None,:3]==colors).all(-1).any(-1)&(im[:,:,3]>0)

def bounds(mask):
    y,x=np.nonzero(mask);assert len(y),'material vanished'
    return int(x.min()),int(y.min()),int(x.max()),int(y.max())

check(without_emberwake(meta)==without_emberwake(base),'all 139 unrelated Cathedral kinds and manifest fields preserved')
hashes=json.loads((BACKUP/'manifest.txt').read_text())['unrelatedPngs']
check(all(hashlib.sha256((R.ASSETS/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),f'all {len(hashes)} unrelated native PNGs unchanged')
selected=os.environ.get('EMBERWAKE_MATERIAL_KINDS',','.join(R.KINDS)).split(',')
assert selected and all(k in R.KINDS for k in selected)
for kind in selected:
    w,h,ax,ay=R.kindframe.frame_of(meta,kind)
    attacks=[cell(kind,'attack',n) for n in range(8)];deaths=[cell(kind,'die',n) for n in range(8)]
    check(len({im.tobytes() for im in attacks})==len({im.tobytes() for im in deaths})==8,f'{kind}: eight distinct attacks and deaths')
    lows=[bounds(im[:,:,3]>0)[3] for im in deaths]
    check(lows[-1]==ay and all(a<=b for a,b in zip(lows,lows[1:])),f'{kind}: corpse rests on ground or descends monotonically')
    idle,dead=cell(kind,'idle',0),deaths[-1]
    if os.environ.get('MUTATE_MATERIAL')==kind:dead=idle.copy()
    check(material(idle,R.FIRE).sum()>0 and material(dead,R.FIRE).sum()==0,f'{kind}: molten core, eyes or wing veins cool and extinguish')
    check(material(dead,R.IRON).sum()>material(idle,R.IRON).sum()*.60,f'{kind}: rigid stone or iron remains solid through death')
    ib,db=bounds(idle[:,:,3]>0),bounds(dead[:,:,3]>0)
    if kind in ('ew_ashback','ew_slagjaw','ew_cinderhorn','ew_chainmaw'):
        check((dead[ay-7,:,3]>0).sum() > (idle[ay-7,:,3]>0).sum(),f'{kind}: folded limbs leave the broad fallen torso supporting the corpse')
    elif kind=='ew_glasswing':
        check(material(dead,R.GLASS).sum()>material(idle,R.GLASS).sum()*.55,'Glasswing: substantial solid glass panels remain after folding and cracking')
        check(db[2]-db[0]<(ib[2]-ib[0])*.85,'Glasswing: rigid wings fold at their roots on landing')
    elif kind=='ew_bellows':
        check(db[3]-db[1]<(ib[3]-ib[1])*.80,'Yrsa: knees buckle and bellows fall sideways')
        check(material(attacks[4],R.FIRE).sum()>material(idle,R.FIRE).sum()*2,'Yrsa: compression drives visible fire out of the two attached nozzles')
    else:
        check(db[3]-db[1]<(ib[3]-ib[1])*.75,'Uncrowned Ember: stone limbs buckle and torso slumps')
        gold=material(dead,R.GOLD);check(gold.sum()>30 and bounds(gold)[3]>=ay-4,'Uncrowned Ember: broken crown falls beside the body onto the ground')
print(f'emberwake-materials: {checks} checks')
