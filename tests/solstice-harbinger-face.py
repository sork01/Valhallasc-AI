#!/usr/bin/env python3
"""Check the face, separate hands and shaded robe in exported Harbinger art."""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import kindframe
from astral_slime_redraw import PALETTE,BONE,TEAL,OUTLINE,PURPLE
meta=json.loads((ROOT/'client/assets/cathedral.txt').read_text())
w,h,ax,ay=kindframe.frame_of(meta,'solstice_harbinger')
atlas=Image.open(os.environ.get('MUTATE_FACE_PNG',ROOT/'client/assets/cathedral_solstice_harbinger.png')).convert('RGBA')

def mask(im,colors):
    rgb=np.array([list(bytes.fromhex(PALETTE[i][1:])) for i in colors])
    return (im[:,:,None,:3]==rgb).all(-1).any(-1)&(im[:,:,3]>0)

def components(bits):
    todo=set(zip(*np.nonzero(bits)));groups=[]
    while todo:
        start=todo.pop();group={start};stack=[start]
        while stack:
            y,x=stack.pop()
            for dy,dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
                p=(y+dy,x+dx)
                if p in todo:todo.remove(p);group.add(p);stack.append(p)
        groups.append(group)
    return sorted(groups,key=len,reverse=True)

checks=0
for clip in ('idle','walk','attack','hurt'):
    spec=meta['clips'][clip]
    for n in range(spec['n']):
        if clip=='hurt' and n==0:continue # White hit flash deliberately conceals all materials.
        im=np.array(atlas.crop((n*w,spec['row']*h,(n+1)*w,(spec['row']+1)*h)))
        eyes=components(mask(im,TEAL))
        assert len(eyes)>=2 and min(map(len,eyes[:2]))>=3,(clip,n,'two visible bright eyes')
        eye_points=np.array(list(eyes[0]|eyes[1]));ey,ex=eye_points.mean(axis=0)
        # Mouth and nose must be inside the lower face, below and between the eyes.
        dark=mask(im,[OUTLINE])
        center=round(ex);top=round(ey)+4
        assert dark[top:top+8,center-4:center+5].sum()>=4,(clip,n,'readable mouth below the eyes')
        hands=components(mask(im,BONE))
        assert len(hands)>=2 and min(map(len,hands[:2]))>=35,(clip,n,'two substantial visible hands')
        centers=[np.array(list(g)).mean(axis=0) for g in hands[:2]]
        assert abs(centers[0][1]-centers[1][1])>=20,(clip,n,'hands are separate at the sleeve ends')
        robe=np.array([mask(im,[color]).sum() for color in PURPLE])
        assert robe.min()>=20 and robe.max()/robe.sum()<.65,(clip,n,'robe has substantial shadows, midtones and highlights')
        checks+=5
backup=Path('/media/raid/valhallasc-data/solstice-harbinger-before-face-fix-20261111')
other=json.loads((backup/'other-atlas-hashes.json').read_text())
assert all(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==sha for rel,sha in other.items()),'unrelated enemy atlases changed'
print(f'Harbinger face/hands/robe: {checks} checks across 25 living poses; {len(other)} other atlases unchanged')
