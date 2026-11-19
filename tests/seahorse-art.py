#!/usr/bin/env python3
"""Only the new mount: original sources, real atlas/depth coverage and preserved mounts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
meta=json.loads((ROOT/'client/assets/mounts_sprites.txt').read_text())
before=json.loads(subprocess.check_output(['git','show','054e7619:client/assets/mounts_sprites.txt'],cwd=ROOT))
for id,m in before['mounts'].items():
    assert meta['mounts'][id]==m, (id,'existing art metadata changed')
    for key in ['png','depth']:
        committed=subprocess.check_output(['git','show','054e7619:client/assets/'+m[key]],cwd=ROOT)
        assert (ROOT/'client/assets'/m[key]).read_bytes()==committed, (id,key)
assert set(meta['mounts'])==set(before['mounts'])|{'seahorse'}
m=meta['mounts']['seahorse'];assert len(m['sprites'])==len(set(m['sprites'].values()))==16
assert set(m['sprites'])=={f'mount_seahorse_{clip}_{d.lower()}' for clip in ['idle','run'] for d in meta['dirs']}
colour=np.array(Image.open(ROOT/'client/assets'/m['png']).convert('RGBA'))
depth=np.array(Image.open(ROOT/'client/assets'/m['depth']).convert('RGB'))
if os.environ.get('MUTATE')=='blank':colour[:]=0
if os.environ.get('MUTATE')=='depth':depth[:]=255
assert colour.shape==(2560,1280,4) and depth.shape==(2560,1280,3)
assert set(np.unique(colour[:,:,3]))=={0,255}
count=0
for clip,n in [('idle',4),('run',8)]:
    c=m['clips'][clip];assert c['n']==n and len(m['bob'][clip])==n
    facings=[]
    for d in range(8):
        hashes=[]
        for k in range(n):
            cell=colour[(c['row0']+d)*160:(c['row0']+d+1)*160,k*160:(k+1)*160]
            z=depth[(c['row0']+d)*160:(c['row0']+d+1)*160,k*160:(k+1)*160]
            yy,xx=np.nonzero(cell[:,:,3]);assert len(xx)>600,(clip,d,k,'blank')
            assert xx.min()>0 and xx.max()<159 and yy.min()>0 and yy.max()<159,(clip,d,k,'clipped')
            enc=z[:,:,0].astype(np.uint32)*256+z[:,:,1]
            assert np.all(enc[cell[:,:,3]>0]<65535),(clip,d,k,'missing depth')
            hashes.append(hashlib.sha256(cell.tobytes()).digest());count+=1
        assert len(set(hashes))>1,(clip,d,'static');facings.append(hashes[0])
    assert len(set(facings))==8,(clip,'facings duplicated')
print(f'Seahorse art: {count} colour/depth frames, 16 PixelFlow sources; all 11 prior mounts preserved')
