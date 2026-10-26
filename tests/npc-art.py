#!/usr/bin/env python3
"""The new NPC art's actual silhouettes, animations, identities and saved manifest."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import make_npc_sprites as npc
plan=json.loads((ROOT/'docs/npc-art-plan.txt').read_text());meta=json.loads((ROOT/'client/assets/npc.txt').read_text())
assert len([s for s in plan['designs'].values() if s['general']])>=24
assert set(meta['sprites'])==set(plan['designs'])
world=json.loads((ROOT/'world/map.txt').read_text());people=[n for z in [world]+world['zones'] for n in z.get('npcs',[]) if n.get('art') not in ('stone','scenery')]
assert set(meta['npcs'])=={n['id'] for n in people}
silhouettes=set();full=set()
for key,spec in plan['designs'].items():
 sheet=np.array(Image.open(ROOT/f'client/assets/npc_{key}.png').convert('RGBA'))
 assert sheet.shape==(288,768,4)
 assert set(np.unique(sheet[:,:,3]))<={0,255}
 if spec['general']:
  pose=sheet[:96,:96];silhouettes.add(hashlib.sha256((pose[:,:,3]>0).tobytes()).hexdigest());full.add(hashlib.sha256(pose.tobytes()).hexdigest())
 for clip,c in meta['clips'].items():
  frames=[sheet[c['row']*96:(c['row']+1)*96,n*96:(n+1)*96] for n in range(c['n'])]
  assert len({a.tobytes() for a in frames})>=3,(key,clip)
  for frame in frames:
   y,x=np.nonzero(frame[:,:,3]);assert x.min()>0 and x.max()<95 and y.min()>0 and y.max()<95,(key,clip)
  if clip=='walk' and spec['build']!='merfolk':
   # Ankles/feet below the coat must move independently of breathing/head motion.
   assert len({f[81:91,24:74].tobytes() for f in frames})>=3,(key,'feet frozen')
 assert meta['tops'][key]>35 and len(meta['bounds'][key])==4
assert len(silhouettes)>=20 and len(full)>=24,(len(silhouettes),len(full))
for person in people:
 assignment=meta['npcs'][person['id']];spec=plan['designs'][assignment['art']]
 if person.get('art') or person.get('look',{}).get('species')=='merfolk':assert not spec['general'],person['id']
 if person.get('look',{}).get('species')=='merfolk':assert spec['build']=='merfolk'
print(f'NPC art: {len(plan["designs"])} designs, {len(people)} identities, {len(silhouettes)} general silhouettes; all frames/anchors/feet checked')
