#!/usr/bin/env python3
"""Reconcile every final atlas cell with actual browser measurements after any source refresh."""
import hashlib,json,sys
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import shared_slime_redraw as R
capture=json.loads((R.OUT/'browser-proof.json').read_text());result={}
assert set(capture)==set(R.KINDS),'Every kind needs a positive browser capture'
for kind in R.KINDS:
 m=capture[kind];w,h,ax,ay=R.kind_frame(kind);im=Image.open(R.atlas_path(kind)).convert('RGBA')
 assert m['source']==R.registry()[kind] and m['frame']==[w,h,ax,ay]
 frames=[]
 for row,(clip,(_,count)) in enumerate(R.CLIPS.items()):
  for n in range(count):
   data=im.crop((n*w,row*h,(n+1)*w,(row+1)*h)).tobytes();value=7
   for i,byte in enumerate(data):value=(value*31+byte+i)&0xffffffff
   actual=next(f for f in m['rows'] if f['clip']==clip and f['n']==n)
   assert actual['hash']==value,(kind,clip,n,'browser capture predates final art; rerun only this kind')
   frames.append(dict(clip=clip,n=n,sha256=hashlib.sha256(data).hexdigest()))
 result[kind]=dict(source=R.registry()[kind],atlasSha256=hashlib.sha256(R.atlas_path(kind).read_bytes()).hexdigest(),browserFrames=frames)
 print(kind,'34 browser measurements equal final atlas')
(R.OUT/'current-browser-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
print('All 238 final frames have current real-browser coverage')
