#!/usr/bin/env python3
"""Seeded, idempotent three-wing Drowned Cathedral; run sync-world and rebuild afterwards.

Three independent five-player instances (four private copies each) at levels 40/45/50.
Every boss and exit is flood checked. Existing maps and enemy IDs are preserved.
"""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import cathedral_content as C
import generate_gloamfen as fen
import generate_undervault as vault

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
FIRST = 10

def rect(x, y, w, d):
    return [x-w/2, y-d/2, x+w/2, y+d/2]

def build(wing, index):
    size, centers = wing['size'], wing['centers']
    rng = random.Random(20261025 + index)
    rooms = [rect(x,y,28 if index < 2 else 34,28 if index < 2 else 34) for x,y in centers]
    # Right galleries have long rectangular exhibition halls. The nave has broad transepts.
    if index == 1:
        rooms = [rect(x,y,32,24) for x,y in centers]
    paths = []
    for (ax,ay),(bx,by) in zip(centers,centers[1:]):
        width = 8 if index < 2 else 12
        bend = (bx,ay)
        for (x,y),(xx,yy) in [((ax,ay),bend),(bend,(bx,by))]:
            rooms.append([min(x,xx)-width/2,min(y,yy)-width/2,max(x,xx)+width/2,max(y,yy)+width/2])
        paths.append([[ax,ay],list(bend),[bx,by]])
    floor = np.zeros((size,size),bool)
    for x0,y0,x1,y1 in rooms:
        floor[max(0,int(y0)):min(size,int(y1)),max(0,int(x0)):min(size,int(x1))] = True
    vault.SIZE = size
    pieces, _ = vault.wall_pieces(floor)
    objects = [dict(kind='cathedralwall',x=round(x,2),y=round(y,2),r=max(w,d)/2,width=round(w,2),depth=round(d,2),v=index) for x,y,w,d in pieces]
    # Seal the entire non-floor, including beyond the visible walls, against dashes and knockback.
    used = floor.copy()
    for y in range(size):
        for x in range(size):
            if used[y,x]: continue
            x1=x+1
            while x1<size and not used[y,x1]: x1+=1
            y1=y+1
            while y1<size and not used[y1,x:x1].any(): y1+=1
            used[y:y1,x:x1]=True
            for yy in range(y,y1,8):
                for xx in range(x,x1,8):
                    w,d=min(8,x1-xx),min(8,y1-yy)
                    objects.append(dict(kind='void',x=xx+w/2,y=yy+d/2,r=max(w,d)/2,width=w,depth=d,v=0))
    slimes = []
    for n,(x,y) in enumerate(centers[1:],1):
        if n % 2 == 0:
            slimes.append(dict(kind=wing['bosses'][n//2-1],x=x,y=y))
        else:
            for kind,dx,dy in [('tidetemplar',-2.4,-1.6),('tidetemplar',2.4,-1.6),('tidecantor',0,3.2),(wing['exclusive'],3.4,3.4)]:
                slimes.append(dict(kind=kind,x=x+dx,y=y+dy))
    start = centers[0]
    up = (start[0]-6,start[1])
    end = (centers[-1][0],centers[-1][1]+8)
    keep = [(s['x'],s['y'],5) for s in slimes] + [(*start,8),(*up,4),(*end,4)]
    # Pillars around each hall, never across a passage. Wing-specific props make the architecture readable.
    for n,(x,y) in enumerate(centers):
        for dx,dy in [(-10,-10),(10,-10),(-10,10),(10,10)]:
            px,py = x+dx,y+dy
            if any(math.hypot(px-kx,py-ky)<kr+1 for kx,ky,kr in keep):
                continue
            objects.append(dict(kind='cathedralcolumn',x=px,y=py,r=.65,v=index))
        for dx in [-9,9]:
            objects.append(dict(kind='cathedrallamp',x=x+dx,y=y-10,r=.18,v=index))
        for dx,dy in [(-11,5),(11,5)]:
            px,py = x+dx,y+dy
            if not any(math.hypot(px-kx,py-ky)<kr+1 for kx,ky,kr in keep):
                objects.append(dict(kind=['cloisterbed','reliccase','navepew'][index],x=px,y=py,r=.7,v=rng.randrange(4)))
    return dict(name='The Drowned Cathedral — '+wing['name'],theme=wing['theme'],tagline=wing['tagline'],
                cathedralWing=wing['id'],size=size,levels=[wing['level']]*2,min_level=wing['level'],players=5,copies=4,
                final_boss=wing['bosses'][-1],spawn=dict(x=start[0],y=start[1]),rooms=rooms,paths=paths,
                objects=objects,slimes=slimes,portals=[
                    dict(id='cathedral_'+wing['id']+'_return',name='Nacrehold — Cathedral Doors',x=up[0],y=up[1],r=1.1,to=9,tx=wing['return_'][0],ty=wing['return_'][1],look='cathedral'),
                    dict(id='cathedral_'+wing['id']+'_exit',name='The Freed Tide',x=end[0],y=end[1],r=1.2,to=9,tx=wing['return_'][0],ty=wing['return_'][1],look='exit',after_clear=True)])

def open_cathedral(city, world):
    """Post-process the existing city; its generator calls this too, preserving open doors on rebuild."""
    if not any(z.get('cathedralWing') for z in world['zones']):
        return
    city['futureInstance'] = dict(name='The Drowned Cathedral',players=5,status='open',levels=[40,45,50],x=96,y=24,
                                  wings=[dict(name=w['name'],level=w['level'],zone=FIRST+i) for i,w in enumerate(C.WINGS)])
    city['portals'] = [p for p in city['portals'] if not p['id'].startswith('cathedral_')]
    for i,w in enumerate(C.WINGS):
        city['portals'].append(dict(id='cathedral_'+w['id'],name=w['name']+' — Level '+str(w['level']),
                                   x=w['door'][0],y=w['door'][1],r=1.1,to=FIRST+i,tx=w['centers'][0][0],ty=w['centers'][0][1],look='cathedral'))
    for n in city['npcs']:
        if n['id']=='nacre_warden':
            n.pop('text', None)
            n['dialogue']='The cathedral doors are open. The left Flooded Cloister calls for level 40, the right Coral Reliquary for 45, and the Grand Nave for 50. Bring a party of five; four bosses guard each wing. Vael holds the Heart of the Tide in the Grand Nave.'

def check(zone):
    seen,_ = fen.flood(zone,(zone['spawn']['x'],zone['spawn']['y']))
    for s in zone['slimes'] + zone['portals']:
        assert seen[int(s['y']/.5),int(s['x']/.5)], ('unreachable',zone['name'],s)
    assert sum(C.ENEMIES[[e['kind'] for e in C.ENEMIES].index(s['kind'])]['boss'] for s in zone['slimes']) == 4
    for s in zone['slimes']:
        assert math.hypot(s['x']-zone['spawn']['x'],s['y']-zone['spawn']['y'])>12

def plot(zones,path):
    im = Image.new('RGB',(1152,450),'#080c18')
    d = ImageDraw.Draw(im)
    for i,(z,w) in enumerate(zip(zones,C.WINGS)):
        k=360/z['size']; ox=i*384+12
        for x0,y0,x1,y1 in z['rooms']:
            d.rectangle([ox+x0*k,40+y0*k,ox+x1*k,40+y1*k],fill=['#27645f','#784c61','#47415f'][i])
        for s in z['slimes']:
            boss=next(e['boss'] for e in C.ENEMIES if e['kind']==s['kind'])
            x,y=ox+s['x']*k,40+s['y']*k
            r=5 if boss else 2
            d.ellipse([x-r,y-r,x+r,y+r],fill='#ffd178' if boss else '#b3e4ed')
            if boss:
                d.text((x+6,y-4),s['kind'],fill='#fff1c0')
        d.text((ox,12),w['name']+' / Level '+str(w['level']),fill=w['color'])
    im.save(path)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--plot'); args=p.parse_args()
    world=json.loads(MAP.read_text())
    old=world['zones'][:FIRST-1]
    assert len(old)==FIRST-1 and old[8]['name']=='Nacrehold'
    later=world['zones'][FIRST-1:]
    if later and later[0].get('cathedralWing'):
        assert [z.get('cathedralWing') for z in later[:3]] == [w['id'] for w in C.WINGS]
        later=later[3:]
    assert not any(z.get('cathedralWing') for z in later), 'Cathedral templates must stay at zones 10–12'
    zones=[build(w,i) for i,w in enumerate(C.WINGS)]
    for z in zones: check(z)
    world['zones']=old+zones+later
    open_cathedral(old[8],world)
    MAP.write_text(json.dumps(world,indent=2)+'\n')
    (ROOT/'world/cathedral.txt').write_text(json.dumps(C.ENEMIES,indent=2)+'\n')
    items_path=ROOT/'world/items.txt'; items=json.loads(items_path.read_text()); have={i['id'] for i in items}
    for e in C.ENEMIES:
        if e['material'] not in have:
            items.append(dict(id=e['material'],name=e['name']+(' Relic' if e['boss'] else ' Fragment'),kind='material',rarity='common',sell=1200 if e['boss'] else 180))
    items_path.write_text(json.dumps(items,indent=2))
    if args.plot: plot(zones,args.plot)
    print('Drowned Cathedral: three reachable private wings, levels 40/45/50, 12 unique bosses, 48 trash enemies.')

if __name__=='__main__': main()
