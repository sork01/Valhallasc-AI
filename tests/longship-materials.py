#!/usr/bin/env python3
"""Semantic material checks on exported Longship art, with idle-as-corpse mutations."""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BACKUP=Path('/media/raid/valhallasc-data/longship-slime-original-20261111')
sys.path.insert(0,str(ROOT/'scripts'))
import longship_slime_redraw as R
from rollback_longship_art import without_longship
meta=json.loads(R.MANIFEST.read_text())
base=json.loads((BACKUP/'client/assets/cathedral.txt').read_text())
checks=0


def check(value,label):
    global checks
    assert value,label
    checks+=1
    print(f'{checks}: {label}')


def cell(kind,clip,n):
    w,h,_,_=R.kindframe.frame_of(meta,kind)
    row=meta['clips'][clip]['row']
    return np.array(Image.open(R.atlas_path(kind)).convert('RGBA').crop((n*w,row*h,(n+1)*w,(row+1)*h)))


def material(im,ramp):
    colors=np.array([list(bytes.fromhex(R.PALETTE[i][1:])) for i in ramp])
    return (im[:,:,None,:3]==colors).all(-1).any(-1)&(im[:,:,3]>0)


def bounds(mask):
    y,x=np.nonzero(mask)
    assert len(y),'material vanished'
    return int(x.min()),int(y.min()),int(x.max()),int(y.max())


check(without_longship(meta)==without_longship(base),'all 140 unrelated Cathedral kinds and manifest fields preserved')
hashes=json.loads((BACKUP/'manifest.txt').read_text())['unrelatedPngs']
check(all(hashlib.sha256((R.ASSETS/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),f'all {len(hashes)} unrelated native PNGs unchanged')
selected=os.environ.get('LONGSHIP_MATERIAL_KINDS',','.join(R.KINDS)).split(',')
assert selected and all(k in R.KINDS for k in selected)
for kind in selected:
    w,h,ax,ay=R.kindframe.frame_of(meta,kind)
    check((w,h,ax,ay)==R.kind_frame(kind),f'{kind}: declared frame and anchor')
    attacks=[cell(kind,'attack',n) for n in range(8)]
    deaths=[cell(kind,'die',n) for n in range(8)]
    check(len({im.tobytes() for im in attacks})==len({im.tobytes() for im in deaths})==8,f'{kind}: eight distinct attacks and deaths')
    lows=[bounds(im[:,:,3]>0)[3] for im in deaths]
    check(lows[-1]==ay and all(a<=b for a,b in zip(lows,lows[1:])),f'{kind}: death grounded or descends monotonically')
    idle,dead=cell(kind,'idle',0),deaths[-1]
    if os.environ.get('MUTATE_MATERIAL')==kind:dead=idle.copy()
    ib,db=bounds(idle[:,:,3]>0),bounds(dead[:,:,3]>0)
    height=lambda bb:bb[3]-bb[1]+1
    width=lambda bb:bb[2]-bb[0]+1
    if kind=='keel_crab':
        check(height(db)<height(ib)*.85,'Scavenger: shell tips sideways and jointed legs fold')
        check(material(dead,R.models.COPPER).sum()>material(idle,R.models.COPPER).sum()*.65,'Scavenger: intact copper shell and pincers retain volume')
        check(material(idle,R.AMBER).sum()>0 and material(dead,R.AMBER).sum()==0,'Scavenger: stalk eyes go dark')
    elif kind=='keel_cargomaw':
        check(width(db)<width(ib)*.92,'Cargo Maw: legs buckle inward around the tipped rigid chest')
        check(material(dead,R.models.WOOD).sum()>material(idle,R.models.WOOD).sum()*.70,'Cargo Maw: wooden chest stays solid')
        check(material(idle,R.TEAL).sum()>material(dead,R.TEAL).sum()*1.2,'Cargo Maw: lockhole eyes darken and limbs fold')
    elif kind=='keel_lantern':
        check(height(db)<height(ib)*.70 and width(db)>width(ib)*1.2,'Bilge Lantern: cage falls sideways onto the floor')
        check(material(dead,R.models.COPPER).sum()>material(idle,R.models.COPPER).sum()*.65,'Bilge Lantern: rigid copper cage and handle remain intact')
        glow=[int(material(im,R.TEAL+R.PEARL).sum()) for im in deaths]
        check(glow[0]>100 and glow[-1]==0 and all(a>=b for a,b in zip(glow,glow[1:])) and material(dead,R.TEAL+R.PEARL).sum()==0,'Bilge Lantern: flame extinguishes monotonically, no glowing corpse')
    else:
        check(height(db)<height(ib)*.80,f'{kind}: crew body and carried weapon lie sideways')
        check(material(dead,R.models.NAVY).sum()>200 and len(set(map(tuple,dead[material(dead,R.models.NAVY),:3])))>=4,f'{kind}: coat and limbs retain shaded volume')
        check(material(dead,R.models.SEA).sum()>material(idle,R.models.SEA).sum()*.65,f'{kind}: drowned face and articulated hands remain physical')
print(f'longship-materials: {checks} checks')
