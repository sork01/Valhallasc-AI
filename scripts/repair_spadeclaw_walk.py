#!/usr/bin/env python3
"""Repair only the Badger's eight saved walk frames, retaining all editor work in other clips."""
import json,sys
import numpy as np
from PIL import Image
import make_sunward_sprites as sun
from make_crag_sprites import rgba

def main():
 api=sun.m._pf();manifest=sun.ASSETS/'sunward.txt';meta=json.loads(manifest.read_text());sid=meta['sprites']['spadebadger'];sp,frames=api.load(sid)
 assert sp['palette']==sun.PALETTES['spadebadger'].hex
 before=[f[0].copy() for f in frames];start=meta['clips']['walk']['editorStart']
 for n in range(8):
  grid=sun.cel.draw('spadebadger','walk',n);api.draw_grid(sid,start+n,0,grid)
 sp,after=api.load(sid)
 for n,grid in enumerate(before):
  if not start<=n<start+8:assert np.array_equal(grid,after[n][0]),('other clip changed',n)
 sheet=Image.new('RGBA',(768,480));raw={};offset=0
 for row,(clip,count) in enumerate(sun.m.CLIPS):
  raw[clip]=np.stack([after[offset+n][0] for n in range(count)])
  for n in range(count):sheet.alpha_composite(Image.fromarray(api.to_rgba(after[offset+n][0],sp['palette'])),(n*96,row*96))
  offset+=count
 target=sun.ASSETS/'sunward_spadebadger.png';sheet.save(target,optimize=True)
 np.savez_compressed(sun.ROOT/'scripts/sunward_spadebadger_raw.npz',**raw)
 for n in range(8):assert np.array_equal(raw['walk'][n],sun.cel.draw('spadebadger','walk',n))
 walk=[rgba(grid,sun.PALETTES['spadebadger'].hex).resize((288,288),Image.Resampling.NEAREST) for grid in raw['walk']]
 walk[0].save(sun.ROOT/'test-results/spadeclaw-walk.gif',save_all=True,append_images=walk[1:],duration=100,loop=0,disposal=2)
 print('Badger: 8 walk frames saved/exported; 26 other frames preserved; source and editor agree')
if __name__=='__main__':main()
