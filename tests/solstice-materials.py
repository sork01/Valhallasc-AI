#!/usr/bin/env python3
"""Check exported Solstice materials. MUTATE_MATERIAL=kind challenges semantic death checks."""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BACKUP=Path('/media/raid/valhallasc-data/solstice-slime-original-20261111')
sys.path.insert(0,str(ROOT/'scripts'))
import kindframe
from solstice_slime_redraw import KINDS
from astral_slime_redraw import PALETTE,PEARL,AZURE,SLATE,TEAL,PURPLE,BROWN,GOLD
from rollback_solstice_art import without_solstice
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

check(without_solstice(meta)==without_solstice(base) and len([k for k in base['kinds'] if k not in KINDS])==140,'all 140 unrelated Cathedral kinds and manifest fields preserved')
hashes=json.loads((BACKUP/'manifest.txt').read_text())['unrelatedAtlasHashes']
check(all(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest for rel,digest in hashes.items()),f'all {len(hashes)} unrelated native atlases preserved')
for kind in KINDS:
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
    if kind=='solstice_flurry':
        check(height(db)<height(ib)*.3 and material(dead,PEARL).sum()>80,'Flurry: snow vortex disperses into a low drift')
        check(material(idle,AZURE).sum()>50 and material(dead,AZURE).sum()==0,'Flurry: frozen face disappears as the snow settles')
    elif kind=='solstice_owl':
        check(height(db)<height(ib)*.7 and width(db)>width(ib),'Owl: intact feathered body falls sideways')
        check(material(dead,SLATE).sum()>100 and material(dead,PEARL).sum()>100,'Owl: folded wings, head and feathered belly remain')
        check(material(idle,GOLD).sum()>material(dead,GOLD).sum(),'Owl: golden eyes close while beak and talons remain')
    elif kind=='solstice_guard':
        check(material(idle,TEAL).sum()>0 and material(dead,TEAL).sum()==0,'Guard: visor light extinguishes')
        check(height(db)<height(ib)*.9 and width(db)>width(ib),'Guard: rigid armour and shield topple sideways')
        check(material(dead,AZURE).sum()>400 and material(dead,BROWN).sum()>10,'Guard: plate and spear shaft remain intact')
    elif kind=='solstice_watcher':
        check(material(idle,PURPLE).sum()>30 and material(dead,PURPLE).sum()==0,'Watcher: huge eye goes dark and vanishes')
        check(width(db)>width(ib)*1.4 and height(db)<height(ib)*.65,'Watcher: hard ice halves separate into low shards')
        check(material(dead,AZURE).sum()>250 and material(dead,PEARL).sum()>50,'Watcher: separate ice fragments retain their facets')
    elif kind=='solstice_harbinger':
        check(material(idle,PURPLE).sum()>100 and material(dead,PURPLE).sum()==0,'Harbinger: spectral body and wings dissipate completely')
        check(height(db)<height(ib)*.25 and material(dead,PEARL).sum()>25,'Harbinger: only the fallen crescent relic remains')
    elif kind=='solstice_heart':
        check(material(idle,TEAL).sum()>20 and material(dead,TEAL).sum()==0,'Heart: central light extinguishes')
        check(width(db)>width(ib)*1.15 and height(db)<height(ib)*.7,'Heart: six rigid petals shatter outward and settle')
        check(material(dead,AZURE).sum()>300 and material(dead,PEARL).sum()>30,'Heart: grounded crystal shards retain their highlights')
print(f'solstice-materials: {checks} checks')
