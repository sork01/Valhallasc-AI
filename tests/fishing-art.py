#!/usr/bin/env python3
"""Only fishing art: coverage, distinct cells, NPC poses/assignments and decoded cues.

MUTATE=icons|npc|sound changes in-memory candidates and must fail.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fish_catalog import pieces
from fisher_npcs import assign_art
from export_fishing_sounds import CUES
from make_fishing_art import render

A=ROOT/'client/assets'
read=lambda p:json.loads((ROOT/p).read_text())
meta=read('client/assets/fishing-icons.txt')
items={i['id']: i for i in pieces()}
ids=meta['order']
assert set(meta['at']) == set(ids) == set(items)
assert [k for source in meta['sources'] for k in source['order']] + meta['local'] == ids
assert len(meta['local']) == 42
baseline = lambda path: subprocess.check_output(['git', 'show', '143ae4d3:' + path], cwd=ROOT)
previous = json.loads(baseline('client/assets/fishing-icons.txt'))
before_atlas = np.array(Image.open(io.BytesIO(baseline('client/assets/fishing-icons.png'))).convert('RGBA'))
assert meta['sources'] == previous['sources']
assert all(0<len(source['order'])<=64 and source['sprite'] for source in meta['sources'])
assert meta['size']==48
atlas=np.array(Image.open(A/'fishing-icons.png').convert('RGBA'))
assert atlas.shape==(meta['rows']*48,meta['cols']*48,4)
signatures=set();coordinates=set()
for key in ids:
    x,y=meta['at'][key];assert (x,y) not in coordinates;coordinates.add((x,y))
    cell=atlas[y*48:(y+1)*48,x*48:(x+1)*48].copy()
    if os.environ.get('MUTATE')=='icons':cell[:]=0
    if key in previous['at']:
        assert (x,y) == tuple(previous['at'][key])
        assert np.array_equal(cell, before_atlas[y*48:(y+1)*48,x*48:(x+1)*48]), (key, 'original icon changed')
    else:
        assert np.array_equal(cell, np.array(render(items[key]))), (key, 'expert icon is stale')
    yy,xx=np.nonzero(cell[:,:,3]);assert len(xx)>40,(key,'blank')
    assert 0<xx.min()<=xx.max()<47 and 0<yy.min()<=yy.max()<47,(key,'clipped')
    signature=cell.tobytes();assert signature not in signatures,(key,'duplicate icon');signatures.add(signature)
assert set(np.unique(atlas[:,:,3]))=={0,255},'Hard pixel edges, actual transparency'

# Preserve old artwork and identities; the new fishing role is additive.
before=lambda p:json.loads(subprocess.check_output(['git','show','a1764688:'+p],cwd=ROOT))
old_fresh=before('client/assets/npcp.txt');fresh=read('client/assets/npcp.txt')
for field,value in old_fresh.items():
    if isinstance(value,dict):
        for k,v in value.items():assert fresh[field][k]==v,(field,k,'old NPC art changed')
    else:assert fresh[field]==value,field
world=read('world/map.txt');people=[n for area in [world,*world['zones']] for n in area['npcs'] if n['id'].startswith('fisher_')]
npcs=read('client/assets/npc.txt');old_npcs=before('client/assets/npc.txt')
if os.environ.get('MUTATE')=='npc':npcs['npcs'][people[0]['id']]['art']='fisher'
assert len(people)==23
for n in people:assert npcs['npcs'][n['id']]['art']=='fisher_rod',n['id']
for k,v in old_npcs['npcs'].items():
    if not k.startswith('fisher_'):assert npcs['npcs'][k]==v,k
again=json.loads(json.dumps(npcs));assign_art(again,world);assert again==npcs,'Assignment overlay is stable'
img=np.array(Image.open(A/'npcp_fisher_rod.png').convert('RGBA'))
assert img.shape==(288,768,4)
top=90
for row,(clip,count) in enumerate((('idle',6),('walk',8),('talk',6))):
    seen=set()
    for k in range(count):
        cell=img[row*96:(row+1)*96,k*96:(k+1)*96];yy,xx=np.nonzero(cell[:,:,3])
        assert 0<xx.min()<=xx.max()<95 and 0<yy.min()<=yy.max()<95,(clip,k,'clipped')
        assert yy.max()>=84,(clip,k,'floating feet')
        top=min(top,int(yy.min()));seen.add(cell.tobytes())
    assert len(seen)>=3,(clip,'static')
assert fresh['tops']['fisher_rod']==90-top

sounds=read('client/assets/fishing-sounds.txt');assert set(sounds['clips'])==set(CUES)
hashes=set()
for cue,duration in CUES.items():
    info=sounds['clips'][cue];target=A/info['file']
    assert info['sha256']==hashlib.sha256(target.read_bytes()).hexdigest(),cue
    assert info['sha256'] not in hashes;hashes.add(info['sha256'])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(target)]))['streams'][0]
    assert probe['channels']==1 and probe['sample_rate']=='44100',cue
    data=subprocess.check_output(['ffmpeg','-v','error','-i',str(target),'-f','f32le','pipe:1'])
    samples=np.frombuffer(data,dtype='<f4').copy()
    if os.environ.get('MUTATE')=='sound':samples[:]=0
    assert np.isfinite(samples).all() and .05<np.max(np.abs(samples))<.98,cue
    assert np.sqrt(np.mean(samples*samples))>.003,(cue,'silent')
    assert abs(len(samples)/44100-duration)<.08,(cue,'length')
    assert np.max(np.abs(samples[-220:]))<.05,(cue,'tail click')
print(f'PASS: {len(ids)} distinct icons, 23 Fishers / 20 poses, seven decoded cues; previous NPC artwork preserved')
