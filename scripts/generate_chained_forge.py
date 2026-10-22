#!/usr/bin/env python3
"""The Chained Forge: sealed level-99 raid floor. No enemies until RAID-PACKS/BOSS.

python3 scripts/generate_chained_forge.py [--check | --open]
Rebuild preserves an opened entrance; --open is reserved for RAID-OPEN.
"""
import argparse
import json
import math
from collections import deque
from pathlib import Path
import numpy as np
from mercenary_offers import offers
from skaldholm_content import look

ROOT = Path(__file__).resolve().parents[1]
ZONE, PARENT, SIZE = 46, 45, 320
NAME, THEME = 'The Chained Forge', 'chained_forge'
ARRIVAL, DESCENT = (30, 303), (62, 290)
# Each hall has its own silhouette and room for the approved ten-fighter mechanic.
HALLS = [
    ('link', 'The First Link', 84, 272, 33, 29, 'cf_kettil'),
    ('bellows', 'The Iron Lung', 209, 272, 36, 29, 'cf_ysolt'),
    ('anvil', 'The Three Anvils', 270, 204, 32, 30, 'cf_hallgrim'),
    ('slag', 'The Numbered Forge', 164, 201, 35, 29, 'cf_sigrun'),
    ('valves', 'The Divided Crucible', 55, 201, 33, 30, 'cf_dagfinn'),
    ('quench', 'The Brand Gallery', 52, 117, 32, 30, 'cf_thorbjorg'),
    ('rhythm', 'The Cinder Floor', 156, 121, 34, 29, 'cf_ragnhild'),
    ('water', 'The Quenching Wells', 268, 122, 33, 29, 'cf_orm'),
    ('mirror', 'The Last Chain', 266, 43, 32, 29, 'cf_hildr'),
    ('throne', 'The Promised Table', 111, 43, 40, 34, 'cf_eldmarr'),
]
LEGS = [
    [DESCENT, (75, 283), (84, 272)],
    [(84, 272), (145, 277), (209, 272)],
    [(209, 272), (265, 260), (278, 234), (270, 204)],
    [(270, 204), (220, 194), (164, 201)],
    [(164, 201), (111, 208), (55, 201)],
    [(55, 201), (42, 161), (52, 117)],
    [(52, 117), (104, 109), (156, 121)],
    [(156, 121), (212, 132), (268, 122)],
    [(268, 122), (279, 82), (266, 43)],
    [(266, 43), (204, 34), (157, 46), (111, 43)],
]

def obj(kind, x, y, **kw):
    return dict(kind=kind, x=round(float(x), 3), y=round(float(y), 3), r=0, v=kw.pop('v', 0), **kw)

def segment_distance(x, y, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = np.clip(((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy), 0, 1)
    return np.hypot(x-a[0]-t*dx, y-a[1]-t*dy)

def floor_mask(scale=1):
    yy, xx = np.mgrid[:SIZE, :SIZE]
    x, y = xx+.5, yy+.5
    floor = np.zeros((SIZE, SIZE), dtype=bool)
    for i, (_, _, cx, cy, rx, ry, _) in enumerate(HALLS):
        u, v = np.abs((x-cx)/(rx*scale)), np.abs((y-cy)/(ry*scale))
        if i in (0, 2, 6, 8):
            shape = (np.maximum(u, v) < 1) & (u+v < 1.48)  # octagonal iron courts
        elif i in (3, 5):
            shape = (u**4+v**4 < 1)  # round-cornered furnaces
        else:
            shape = u*u+v*v < 1
        floor |= shape
    for i, leg in enumerate(LEGS):
        for a, b in zip(leg, leg[1:]):
            floor |= segment_distance(x, y, a, b) < (5.5 if i in (2, 5, 8) else 7)
    # Four side forges reserve optional packs off the main road.
    for cx, cy in [(145, 299), (222, 219), (110, 177), (210, 102)]:
        floor |= ((x-cx)/12)**2+((y-cy)/11)**2 < 1
    for a,b in [((145,277),(145,299)),((220,194),(222,219)),((111,208),(110,177)),((212,132),(210,102))]:
        floor |= segment_distance(x,y,a,b) < 4.5
    # Isolated muster chamber. Only the ten-fighter inner gate reaches the descent.
    floor &= ~((x < 48) & (y > 286))
    floor |= (x >= 18) & (x < 43) & (y >= 291) & (y < 314)
    floor &= (x > 5) & (y > 5) & (x < 315) & (y < 315)
    return floor

def chosen_floor():
    lo, hi = .7, 1.1
    for _ in range(24):
        mid = (lo+hi)/2
        if floor_mask(mid).sum() < 32100: lo = mid
        else: hi = mid
    return floor_mask(hi), hi

def rectangles(mask):
    """Exact disjoint solid complement, merged vertically: no invisible walkable void."""
    active, out = {}, []
    for y, row in enumerate(~mask):
        edges = np.flatnonzero(np.diff(np.r_[False, row, False].astype(int)))
        runs = set(zip(edges[::2].tolist(), edges[1::2].tolist()))
        for run in list(active):
            if run not in runs:
                out.append((*run, active.pop(run), y))
        for run in runs: active.setdefault(run, y)
    out.extend((*run, y0, SIZE) for run,y0 in active.items())
    return sorted(out, key=lambda r:(r[2],r[0],r[3],r[1]))

def checkpoint(leg, hall, scale):
    # Last point before the court, on the clear approach (outside awareness range).
    _,_,cx,cy,rx,ry,_ = hall
    a = leg[-2]; dx,dy = a[0]-cx,a[1]-cy
    t = 1/math.sqrt((dx/(rx*scale))**2+(dy/(ry*scale))**2)
    length = math.hypot(dx,dy)
    return (round(cx+dx*(t+8/length),2), round(cy+dy*(t+8/length),2))

def build():
    floor, scale = chosen_floor()
    objects = [obj('void', (x0+x1)/2, (y0+y1)/2, width=x1-x0, depth=y1-y0)
               for x0,x1,y0,y1 in rectangles(floor)]
    halls, places, rooms = [], [], []
    for i, (key,name,x,y,rx,ry,boss) in enumerate(HALLS):
        cp = checkpoint(LEGS[i], HALLS[i], scale)
        if i == 0: cp = DESCENT
        halls.append(dict(id=key,name=name,x=x,y=y,rx=round(rx*scale,2),ry=round(ry*scale,2),
                          boss=boss,checkpoint=dict(x=cp[0],y=cp[1]),route=LEGS[i]))
        places.extend([dict(id=f'cf_hall_{i+1}',name=name,x=x,y=y,r=6),
                       dict(id=f'cf_checkpoint_{i+1}',name='Rally '+str(i+1),x=cp[0],y=cp[1],r=2)])
        rooms.append([x-16,y-15,x+16,y+15])
        objects.extend([obj('cf_rally',cp[0]+1,cp[1]+1,v=i),obj('cf_pylon',x-rx*scale+5,y+2,v=i),
                        obj('cf_pylon',x+rx*scale-5,y+2,v=i)])
        # Different workshop landmarks, placed outside the central mechanic floor.
        landmark=['cf_chain','cf_bellows','cf_anvil','cf_furnace','cf_valve','cf_quench','cf_speaker','cf_quench','cf_mirror','cf_throne'][i]
        objects.append(obj(landmark,x,y-ry*scale+6,v=i))
        objects.append(obj('cf_vent',x+13,y+12,v=i))
    # Art uses actual floor boundaries for the lava banks and bridge edges.
    objects += [obj('cf_lavafall',250,243),obj('cf_lavafall',65,158),
                obj('cf_lavafall',293,80),obj('cf_lavafall',184,54),
                obj('cf_gateway',30,294),obj('cf_lantern',23,306),obj('cf_lantern',39,306)]
    for i,leg in enumerate(LEGS):
        for a,b in zip(leg,leg[1:]):
            n=max(1,int(math.dist(a,b)//16))
            for k in range(1,n+1):
                t=k/(n+1);x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
                objects.append(obj('cf_lantern',x+2,y+2,v=i))
    # Even r=0 scenery has a player-radius footprint in the authoritative engine.
    # Keep every landmark and light off the authored walking centreline and arrivals.
    segments=[(a,b) for leg in LEGS for a,b in zip(leg,leg[1:])]
    keep=[ARRIVAL,DESCENT,(22,303),(30,296),(57,292),(111,24)]
    keep += [(h['checkpoint']['x'],h['checkpoint']['y']) for h in halls]
    for o in objects:
        if not o['kind'].startswith('cf_'):continue
        original=(o['x'],o['y'])
        candidates=[original]+[(original[0]+r*math.cos(a*math.pi/4),original[1]+r*math.sin(a*math.pi/4))
                               for r in range(2,9) for a in range(8)]
        for x,y in candidates:
            if all(float(segment_distance(x,y,a,b))>1.25 for a,b in segments) and all(math.hypot(x-a,y-b)>1.25 for a,b in keep):
                o['x'],o['y']=round(x,3),round(y,3);break
        else:raise AssertionError(('no clear scenery position',o))
    packs=[dict(id=i+1,x=x,y=y,mandatory=i<6) for i,(x,y) in enumerate([
        (145,277),(274,239),(220,194),(111,208),(44,158),(278,82),
        (145,299),(222,219),(110,177),(210,102)])]
    contract=offers()
    for offer in contract:
        if offer['merc']!='dismiss': offer['raid']=True
    folk=[dict(id='cf_quartermaster',name='Quartermaster Halla',role='Raid contracts',x=36,y=303,
        color='#75d7d5',offers=contract,look=look('#c99b7a','#58414c','braid','hood',hat_color='#433344'),
        dialogue='Hire your missing fighters here. Ten fighters must pass the inner gate together. Each contract costs the normal hire price. If you fall, your fighters wake with you at the last rally mark. Leaving the raid ends their contracts.')]
    places.insert(0,dict(id='cf_muster',name='The Muster Chamber',x=30,y=303,r=12))
    return dict(name=NAME,theme=THEME,tagline='Nine chains. One broken promise.',size=SIZE,
        levels=[99,99],min_level=99,players=10,copies=3,raid=True,interior=True,sealedTemplate=True,
        final_boss='cf_eldmarr',spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),objects=objects,slimes=[],
        npcs=folk,quests=[],city=None,rooms=rooms,paths=LEGS,
        forgeFloor=[''.join('=' if v else ' ' for v in row) for row in floor],
        forgeHalls=halls,forgePacks=packs,places=places,
        portals=[dict(id='cf_return',name='Emberwake Caldera',x=22,y=303,r=1.2,to=PARENT,tx=127,ty=25,look=THEME),
                 dict(id='cf_begin',name='The Ten-Fighter Gate',x=30,y=296,r=1.2,to=ZONE,tx=DESCENT[0],ty=DESCENT[1],look=THEME),
                 dict(id='cf_retreat',name='The Muster Chamber',x=57,y=292,r=1.2,to=ZONE,tx=30,ty=307,look=THEME,muster=True),
                 dict(id='cf_clear',name='The Forge Released',x=111,y=24,r=1.2,to=PARENT,tx=127,ty=25,look=THEME,after_clear=True)])

def install_parent(w):
    if len(w['zones']) < ZONE:return
    z=w['zones'][PARENT-1]
    z['portals']=[p for p in z['portals'] if p['id']!='ew_raid']+[
        dict(id='ew_raid',name=NAME,x=133,y=24,r=1.2,to=ZONE,tx=30,ty=303,look=THEME,muster=True)]
    for n in z['npcs']:
        if n['id']=='ew_stone':n['dialogue']='Gather here before the Nine-Chain Door. Outdoor companies still hold five fighters. Raid contracts are signed with Quartermaster Halla in the muster chamber beyond the door.'
        if n['id']=='ew_seal':
            n['x'],n['y']=130,24
            n['dialogue']='Nine Wardens hold nine chains. Beyond them waits Eldmarr, the Ember-Lord. The raid is sealed. When the seal is lifted, gather your ten fighters in the muster chamber.'

def check(w):
    z=w['zones'][ZONE-1];mask=np.array([[c=='=' for c in row] for row in z['forgeFloor']])
    def reachable(start):
        seen=set();q=deque([(int(start[0]),int(start[1]))])
        while q:
            x,y=q.popleft()
            if (x,y) in seen or not (0<=x<SIZE and 0<=y<SIZE) or not mask[y,x]:continue
            seen.add((x,y));q.extend([(x-1,y),(x+1,y),(x,y-1),(x,y+1)])
        return seen
    main,muster=reachable(DESCENT),reachable(ARRIVAL)
    assert main.isdisjoint(muster),'muster must be physically separate from the raid floor'
    assert len(main)+len(muster)==int(mask.sum()),'all floor belongs to the descent or muster'
    assert 31800 <= mask.sum() <= 32400,mask.sum()
    for target in z['places']+z['portals']+z['npcs']+z['forgePacks']+z['slimes']:
        assert (int(target['x']),int(target['y'])) in main|muster,target
    for h in z['forgeHalls']:
        for x,y in h['route']:
            assert (int(x),int(y)) in main,(h['id'],x,y)
        assert (int(h['checkpoint']['x']),int(h['checkpoint']['y'])) in main,h
    for src in (z,w['zones'][PARENT-1]):
        for p in src['portals']:
            if p['id'] not in ('ew_raid','cf_return','cf_begin','cf_retreat','cf_clear'):continue
            dst=w['zones'][p['to']-1]
            assert all(math.hypot(p['tx']-q['x'],p['ty']-q['y'])>q['r']+1 for q in dst['portals']),p
            assert all(math.hypot(p['tx']-s['x'],p['ty']-s['y'])>=8 for s in dst['slimes']),p
    times=[round(sum(math.dist(a,b) for a,b in zip(p,p[1:]))/5.2,2) for p in LEGS]
    print(json.dumps(dict(floor=int(mask.sum()),raidFloor=len(main),musterFloor=len(muster),halls=10,
        packSites=len(z['forgePacks']),mandatory=6,legSeconds=times,walkSeconds=round(sum(times),2))))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');parser.add_argument('--open',action='store_true')
    args=parser.parse_args();path=ROOT/'world/map.txt';w=json.loads(path.read_text())
    if not args.check:
        old=w['zones'][ZONE-1] if len(w['zones'])>=ZONE else None
        if old:assert old['name']==NAME
        z=build();z['sealedTemplate']=not(args.open or old and not old.get('sealedTemplate',True))
        # Later tasks own actual encounters and quests; rebuilding the floor preserves them.
        if old:
            for key in ('slimes','quests'):z[key]=old.get(key,[])
            z['npcs'] += [n for n in old['npcs'] if n['id']!='cf_quartermaster']
        if old:w['zones'][ZONE-1]=z
        else:
            assert len(w['zones'])==ZONE-1
            w['zones'].append(z)
        install_parent(w)
    check(w)
    if not args.check:path.write_text(json.dumps(w,indent=2,ensure_ascii=False)+'\n')

if __name__=='__main__':main()
