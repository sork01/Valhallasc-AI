#!/usr/bin/env python3
"""Exported metal/current semantics, physical corpse volume and preservation."""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BACKUP=Path('/media/raid/valhallasc-data/foundry-slime-original-20261111')
sys.path.insert(0,str(ROOT/'scripts'))
import foundry_slime_redraw as R
from rollback_foundry_art import without_foundry
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


check(without_foundry(meta)==without_foundry(base),'all 140 unrelated Cathedral kinds and other manifest fields preserved')
hashes=json.loads((BACKUP/'manifest.txt').read_text())['unrelatedPngs']
check(all(hashlib.sha256((R.ASSETS/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),f'all {len(hashes)} unrelated native PNGs unchanged')
selected=os.environ.get('FOUNDRY_MATERIAL_KINDS',','.join(R.KINDS)).split(',')
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
    check(material(idle,R.CURRENT).sum()>8 and material(dead,R.CURRENT).sum()==0,f'{kind}: current and illuminated facial apertures shut off')
    metal=R.IRON+R.AMETHYST+R.GOLD
    check(material(dead,metal).sum()>material(idle,metal).sum()*.65,f'{kind}: forged metal retains solid mass, never melts or dissipates')
    # Material orientation and mechanism checks differ by the machine's anatomy.
    ib,db=bounds(idle[:,:,3]>0),bounds(dead[:,:,3]>0)
    if kind=='null_hauler':
        check(abs(db[0]-ib[0])>=8 and abs(db[2]-ib[2])>=4,'Hauler: kiln and attached exhaust stacks tip off the four piston legs')
        check(material(dead,R.IRON).sum()>500,'Hauler: ribs, stacks, head and feet remain iron')
    elif kind=='null_breaker':
        check(db[3]-db[1]<(ib[3]-ib[1])*.85,'Breaker: legs buckle and armoured body and axe lie sideways')
        check(material(dead,R.GOLD).sum()>50,'Breaker: physical pendulum shaft and counterweight remain')
    elif kind=='null_coil':
        check(db[2]-db[0]<(ib[2]-ib[0])*.90,'Coil: organ-pipe array rotates onto its side')
        check(material(attacks[4],R.CURRENT).sum()>material(idle,R.CURRENT).sum()*1.3,'Coil: current lashes extend from the terminal array during the strike')
    elif kind=='null_bell':
        check(db[3]-db[1]<(ib[3]-ib[1])*.88,'Vark: cast bell rolls sideways and legs fold')
        check(material(dead,R.AMETHYST).sum()>material(idle,R.AMETHYST).sum()*.65,'Vark: solid bell crown and skirt remain after the clapper darkens')
    elif kind=='null_conductor':
        check(db[3]-db[1]<(ib[3]-ib[1])*.75 and db[2]-db[0]>ib[2]-ib[0],'Iona: mask, gear halo and articulated current arms settle sideways')
        check(material(attacks[4],R.CURRENT).sum()>material(idle,R.CURRENT).sum(),'Iona: six-arm cast carries visible current along connected appendages')
    else:
        check(abs(db[0]-ib[0])>12 and db[2]-db[0]<(ib[2]-ib[0])*.9,'Thirteenth Hour: clock chassis rolls and limbs fold into its fallen case')
        check(material(dead,R.GOLD).sum()>50,'Thirteenth Hour: physical hour marks and gear teeth survive shutdown')
print(f'foundry-materials: {checks} checks')
