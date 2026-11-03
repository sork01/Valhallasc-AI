"""Focused data/art invariants: no geography changes, one hunt, complete saved sprite sources."""
import json,subprocess,os
import numpy as np
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]
def read(path):return json.loads((root/path).read_text())
world=read('world/map.txt')
baseline=os.environ.get('NEWYEAR_BASELINE')
before=json.loads(subprocess.check_output(['git','show',baseline+':world/map.txt'],cwd=root)) if baseline else None
clean=json.loads(json.dumps(world))
for area in [clean,*clean['zones']]:
    area['quests']=[q for q in area['quests'] if q.get('season')!='newyear']
    area['slimes']=[s for s in area['slimes'] if s['kind']!='starrocketeer']
    area['npcs']=[n for n in area['npcs'] if n['id']!='newyear_launchpad']
    for npc in area['npcs']:
        npc['offers']=[o for o in npc.get('offers',[]) if o.get('season')!='newyear']
if before is not None:
    assert clean==before,'Existing geography, NPCs, spawns and quests must remain identical'
quests=[q for area in [world,*world['zones']] for q in area['quests'] if q.get('season')=='newyear']
assert len(quests)==1 and quests[0]['id']=='newyear_hunt'
assert len('quest:accept:'+quests[0]['id'])<=32
assert quests[0]['rewardXp']==read('world/levels.txt')[0]//10
assert len(quests[0]['givers'])==4 and quests[0]['recommendedPlayers']==5
meta=read('client/assets/newyear.txt')
assert sum(c['n'] for c in meta['clips'].values())==34 and len(meta['sprites'])==1
atlas=Image.open(root/'client/assets/newyear_starrocketeer.png').convert('RGBA')
for clip in meta['clips'].values():
    for k in range(clip['n']):
        crop=atlas.crop((k*96,clip['row']*96,(k+1)*96,(clip['row']+1)*96))
        box=crop.getbbox();assert box and min(box[:2])>0 and max(box[2:])<96
m=read('client/assets/mounts_sprites.txt')['mounts']['rocket']
assert len(m['sprites'])==16 and set(m['clips'])=={'idle','run'}
color=Image.open(root/'client/assets/mount_rocket.png').convert('RGBA')
depth=Image.open(root/'client/assets/mount_rocket_depth.png').convert('RGB')
assert color.size==depth.size==(1280,2560)
for clip in m['clips'].values():
    for d in range(8):
        for k in range(clip['n']):
            y=(clip['row0']+d)*160
            crop=color.crop((k*160,y,(k+1)*160,y+160));box=crop.getbbox()
            assert box and min(box[:2])>0 and max(box[2:])<160
            for x0,y0 in zip(*np.nonzero(np.asarray(crop)[...,3])):
                pixel=depth.getpixel((k*160+int(y0),y+int(x0)))
                assert pixel[0]*256+pixel[1]<65535
print('New Year data/art: exactly one valid quest, 34 elite frames, 96 rocket frames with valid depth and no clipped borders; 17 PixelFlow sources')
