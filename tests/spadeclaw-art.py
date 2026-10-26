#!/usr/bin/env python3
"""Read saved art, prove moving front claws, and protect the other four clips."""
import io,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import make_sunward_sprites as sun
# Pin the pre-fix artwork so committing this test cannot repair its mutation.
old=np.array(Image.open(io.BytesIO(subprocess.check_output(['git','show','476a52055485dae8b9178598b75164eda2bea17a:client/assets/sunward_spadebadger.png'],cwd=ROOT))).convert('RGBA'))
sheet=old if '--mutate' in sys.argv else np.array(Image.open(ROOT/'client/assets/sunward_spadebadger.png').convert('RGBA'))
palette=sun.PALETTES['spadebadger'];claws=np.array([[int(palette.hex[i][j:j+2],16) for j in (1,3,5)] for k,i in palette.names.items() if k.startswith('claw')])
poses=[]
for n in range(8):
 frame=sheet[96:192,n*96:(n+1)*96];crop=frame[76:92,48:90,:3]
 poses.append(np.any(np.all(crop[:,:,None,:]==claws[None,None,:,:],axis=3),axis=2).tobytes())
assert len(set(poses))>=5, 'front spade claws must have at least five different planted/lifted poses'
for row in (0,2,3,4):assert np.array_equal(old[row*96:(row+1)*96],sheet[row*96:(row+1)*96]),'another clip changed'
for n in range(8):assert sheet[96:192,n*96:(n+1)*96].tobytes()==sun.rgba(sun.cel.draw('spadebadger','walk',n),palette.hex).tobytes(),'source/export disagreement'
print('Spadeclaw: 8 walk frames, moving front claws, coordinated source gait; other clips intact')
