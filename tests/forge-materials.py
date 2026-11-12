#!/usr/bin/env python3
"""Exported material semantics, anatomy, borrowed sources and preservation."""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BACKUP=Path('/media/raid/valhallasc-data/forge-slime-original-20261111')
sys.path.insert(0,str(ROOT/'scripts'))
import forge_slime_redraw as R
from rollback_forge_art import without_forge
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

check(without_forge(meta)==without_forge(base),'all 120 unrelated Cathedral kinds and shared manifest fields preserved')
hashes=json.loads((BACKUP/'manifest.txt').read_text())['unrelatedPngs']
check(all(hashlib.sha256((R.ASSETS/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),f'all {len(hashes)} unrelated native PNGs unchanged')
for alias,source in R.ALIASES.items():
    check(meta['sprites'][alias]==meta['sprites'][source] and meta['tops'][alias]==meta['tops'][source] and R.kindframe.frame_of(meta,alias)==R.kind_frame(source),f'{alias}: correct borrowed source, health bar and frame')
selected=os.environ.get('FORGE_MATERIAL_KINDS',','.join(R.KINDS)).split(',')
assert selected and all(k in R.KINDS for k in selected)
for kind in selected:
    w,h,ax,ay=R.kindframe.frame_of(meta,kind)
    attacks=[cell(kind,'attack',n) for n in range(8)];deaths=[cell(kind,'die',n) for n in range(8)]
    check(len({im.tobytes() for im in attacks})==len({im.tobytes() for im in deaths})==8,f'{kind}: eight distinct attack and death poses')
    idle,dead=cell(kind,'idle',0),deaths[-1]
    if os.environ.get('MUTATE_MATERIAL')==kind:dead=idle.copy()
    ib,db=bounds(idle[:,:,3]>0),bounds(dead[:,:,3]>0)
    check(bounds(dead[:,:,3]>0)[3]==ay,f'{kind}: final corpse or fragments reach the anchor row')
    if kind=='cf_caster':
        lows=[bounds(im[:,:,3]>0)[3] for im in deaths]
        check(all(a<=b for a,b in zip(lows,lows[1:])) and lows[0]<ay-12,f'{kind}: iron crucible descends from hover')
        check(material(idle,R.FIRE).sum()>80 and material(dead,R.FIRE).sum()==0,f'{kind}: flame face and jets gutter out completely')
        check(material(dead,R.IRON).sum()>100,f'{kind}: solid fallen crucible remains')
    elif kind=='cf_ingot':
        check(db[2]-db[0]>ib[2]-ib[0]+10,'Numbered Ingot: two rigid halves separate and broken fragments scatter')
        check(material(dead,R.FIRE).sum()==0 and material(idle,R.FIRE).sum()>30,'Numbered Ingot: glowing shield metal cools')
        source=next(e for e in R.WARDENS if e['kind']==kind)
        check(source['stats'][1]==0 and source['profile']==[0,1,0,0],'Numbered Ingot: warning pulse preserves its harmless stationary mechanics')
    elif kind=='cf_crawler':
        check(material(dead,R.FIRE).sum()==0 and material(idle,R.FIRE).sum()>20,'Crawler: vents and six-eye furnace shut down')
        check(db[2]-db[0] < (ib[2]-ib[0])*.9,'Crawler: articulated legs curl over the tipped rigid carapace')
    else:
        # Retained armour/cloth and a shorter, wider body prove a fallen rig, not a faded idle.
        check(db[3]-db[1] < (ib[3]-ib[1])*(.95 if kind=='cf_orm' else .86),f'{kind}: knees buckle and body tips sideways' + (' with retained rigid cooling tank' if kind=='cf_orm' else ''))
        check(material(dead,R.IRON).sum()>100,f'{kind}: substantial rigid iron remains in its fallen body and equipment')
        if material(idle,R.FIRE).sum()>5:
            check(material(dead,R.FIRE).sum()==0,f'{kind}: furnace eyes, ribs or burning equipment extinguish')
        if kind=='cf_hildr':check(material(dead,R.GLASS).sum()>material(idle,R.GLASS).sum()*.65,'Hildr: substantial solid mirror plates remain after falling')
        if kind=='cf_eldmarr':check(material(dead,R.GOLD).sum()>90,'Eldmarr: broken crown and forge chains remain with the giant')
print(f'forge-materials: {checks} checks')
