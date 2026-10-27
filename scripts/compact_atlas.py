#!/usr/bin/env python3
"""Final, deterministic geography overlay, run by sync-world after content overlays.

Only shared outdoor neighbours receive new routes. Dungeon/interior doors and all
access flags remain owned by their zone generators. No zone/copy IDs change.
"""
import json
import math
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
from atlas_geography import generate

ATLAS, _OWNERSHIP = generate()
REGIONS = {r['zone']: r for r in ATLAS['regions']}
OUTDOORS = set(REGIONS) | {17}


def sky_landing(z):
    """A small passing place on the western bridge; keep the rest of the void solid."""
    x0, y0, x1, y1 = 30, 70, 49, 83
    for y in range(y0, y1):
        row = list(z['sky'][y])
        for x in range(x0, x1):
            if row[x] == ' ': row[x] = '='
        z['sky'][y] = ''.join(row)
    objects = []
    for o in z['objects']:
        if o['kind'] != 'void':
            objects.append(o); continue
        a, b, c, d = o['x']-o['width']/2, o['y']-o['depth']/2, o['x']+o['width']/2, o['y']+o['depth']/2
        if a >= x1 or c <= x0 or b >= y1 or d <= y0:
            objects.append(o); continue
        # Subtract only the landing rectangle; do not open surrounding empty sky.
        left, right = max(a, x0), min(c, x1)
        for ax, ay, bx, by in [(a,b,left,d),(right,b,c,d),(left,b,right,max(b,y0)),(left,min(d,y1),right,d)]:
            if bx > ax and by > ay:
                objects.append(dict(o, x=(ax+bx)/2, y=(ay+by)/2, width=bx-ax, depth=by-ay, r=(bx-ax)/2))
    z['objects'] = objects


def blocked(z, radius=.38):
    """Rasterize exactly the server's round/rectangular collision footprints."""
    n = z['size']
    grid = bytearray(n * n)
    for o in z['objects']:
        x, y = o['x'], o['y']
        rect = o.get('width', 0) > 0 and o.get('depth', 0) > 0
        hx, hy = ((o['width']/2+radius, o['depth']/2+radius) if rect else
                  (o.get('r', 0)+radius, o.get('r', 0)+radius))
        for iy in range(max(0, math.floor(y-hy)), min(n, math.ceil(y+hy))):
            for ix in range(max(0, math.floor(x-hx)), min(n, math.ceil(x+hx))):
                dx, dy = abs(ix+.5-x), abs(iy+.5-y)
                hit = (dx < hx and dy < hy) if rect else dx*dx+dy*dy < hx*hx
                if hit:
                    grid[iy*n+ix] = 1
    return grid


def connected(z, avoid=()):
    n = z['size']; walls = blocked(z, .6)
    for portal in avoid:
        x, y, r = portal['x'], portal['y'], portal['r']+.65
        for iy in range(max(1, math.floor(y-r)), min(n-1, math.ceil(y+r))):
            for ix in range(max(1, math.floor(x-r)), min(n-1, math.ceil(x+r))):
                if math.hypot(ix+.5-x, iy+.5-y) < r:
                    walls[iy*n+ix] = 1
    start = int(z['spawn']['y'])*n + int(z['spawn']['x'])
    assert not walls[start], f"{z['name']}: blocked spawn"
    prev = {start: None}; queue = deque([start])
    while queue:
        c = queue.popleft(); x, y = c % n, c // n
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            nx, ny = x+dx, y+dy; k = ny*n+nx
            if 1 <= nx < n-1 and 1 <= ny < n-1 and not walls[k] and k not in prev:
                prev[k] = c; queue.append(k)
    return prev


def clear(z, a, b, radius=.8):
    """Continuous segment test using the same inflated shapes as Map::line_clear."""
    dx, dy = b[0]-a[0], b[1]-a[1]; length = dx*dx+dy*dy
    for o in z['objects']:
        if o.get('width', 0) > 0 and o.get('depth', 0) > 0:
            lo, hi = 0., 1.
            for v, d, mid, half in [(a[0], dx, o['x'], o['width']/2+radius),
                                    (a[1], dy, o['y'], o['depth']/2+radius)]:
                if abs(d) < 1e-10:
                    if abs(v-mid) > half: break
                else:
                    t1, t2 = (mid-half-v)/d, (mid+half-v)/d
                    lo, hi = max(lo, min(t1, t2)), min(hi, max(t1, t2))
                    if lo > hi: break
            else: return False
        else:
            t = max(0, min(1, ((o['x']-a[0])*dx+(o['y']-a[1])*dy)/length)) if length else 0
            if math.hypot(a[0]+dx*t-o['x'], a[1]+dy*t-o['y']) <= o.get('r', 0)+radius:
                return False
    return True


def endpoint(z, side, prev, fixed, preferred=.5):
    n = z['size']; sx, sy = side
    candidates = []
    reach = .46 if z.get('sky') else .34
    for depth in range(5, math.ceil(n*reach)):
        for lateral in range(math.ceil(n*.12), math.floor(n*.88)):
            p = (depth+.5 if sx < 0 else n-depth-.5 if sx > 0 else lateral+.5,
                 depth+.5 if sy < 0 else n-depth-.5 if sy > 0 else lateral+.5)
            a = (p[0]-sx*6, p[1]-sy*6)
            if (p[0]-n/2)*sx+(p[1]-n/2)*sy <= abs((p[0]-n/2)*sy-(p[1]-n/2)*sx): continue
            if any(int(q[1])*n+int(q[0]) not in prev for q in [p, a]): continue
            if any(math.hypot(q[0]-s['x'], q[1]-s['y']) < 8.5 for q in [p, a] for s in z['slimes']): continue
            if any(math.hypot(q[0]-s['x'], q[1]-s['y']) < 9 for q in [p, a] for s in fixed): continue
            if any(math.hypot(q[0]-s['x'], q[1]-s['y']) < 3 for q in [p, a] for s in z.get('npcs', [])): continue
            candidates.append((depth*2+abs(lateral+.5-n*preferred)*.12, p, a))
    for _, p, a in sorted(candidates):
        # Sky bridges are narrow: put their trigger on a broad landing so
        # other travellers can pass it without being forced through the gate.
        if clear(z, p, a):
            return p, a
    raise AssertionError(f"{z['name']}: no safe reachable gate on {side}")


def approach(z, prev, p):
    n = z['size']; k = int(p[1])*n+int(p[0]); points = []
    while k is not None:
        points.append([k % n+.5, k // n+.5]); k = prev[k]
    # Collapse collinear grid steps only, so a road never cuts a collision corner.
    result = []
    for point in points:
        if len(result) >= 2 and ((result[-1][0]-result[-2][0])*(point[1]-result[-1][1]) ==
                                 (result[-1][1]-result[-2][1])*(point[0]-result[-1][0])):
            result[-1] = point
        else: result.append(point)
    return result


def direction(a, b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    return ((1 if dx>0 else -1),0) if abs(dx)>=abs(dy) else (0,(1 if dy>0 else -1))


def sync_travel_links(zones):
    masters={n['id']:(i,n) for i,z in enumerate(zones) for n in z.get('npcs',[]) if n.get('travelStop')}
    for id_,(i,n) in masters.items():
        n['travelLinks']=[other for other in n.get('travelLinks',[]) if other in masters and masters[other][0]==i]
    for i,z in enumerate(zones):
        mine=[n for n in z.get('npcs',[]) if n.get('travelStop')]
        if not mine:continue
        for p in z['portals']:
            other=[n for n in zones[p['to']].get('npcs',[]) if n.get('travelStop')]
            if not other or i==p['to']:continue
            a=min(mine,key=lambda n:math.hypot(n['x']-p['x'],n['y']-p['y']))
            b=min(other,key=lambda n:math.hypot(n['x']-p['tx'],n['y']-p['ty']))
            if b['id'] not in a['travelLinks']:a['travelLinks'].append(b['id'])
            if a['id'] not in b['travelLinks']:b['travelLinks'].append(a['id'])


def apply(world):
    zones=[world]+world['zones']; sky_landing(zones[7])
    pairs=[(p['a'],p['b']) for p in ATLAS['links']]+[(17,19)]
    linked={tuple(sorted(pair)) for pair in pairs}
    # Geographic neighbours replace obsolete crossings from earlier layouts. Dungeon
    # doors, key checks and all saved zone IDs are preserved.
    for i in OUTDOORS:
        z=zones[i]
        for path in z.pop('atlasPaths',[]):
            if path in z.get('paths',[]):z['paths'].remove(path)
        z['atlasPaths']=[]
        z['portals']=[p for p in z['portals'] if p['to'] not in OUTDOORS or tuple(sorted((i,p['to']))) in linked]
    endpoints={}; sides={}
    for i in sorted(OUTDOORS):
        z=zones[i];prev=connected(z)
        fixed=[p for p in z['portals'] if p['to'] not in OUTDOORS]
        targets=sorted(b if a==i else a for a,b in pairs if i in (a,b))
        for j in targets:
            if {i,j}=={17,19}:
                side=(0,-1) if i==17 else (0,1);preferred=.65
            else:
                a,b=REGIONS[i]['seed'],REGIONS[j]['seed'];side=direction(a,b)
                dx,dy=b[0]-a[0],b[1]-a[1]
                preferred=max(.16,min(.84,.5+.3*(dy/abs(dx) if side[0] else dx/abs(dy))))
            point,arrival=endpoint(z,side,prev,fixed,preferred)
            endpoints[i,j]=(point,arrival);sides[i,j]=side
            fixed.extend([dict(x=point[0],y=point[1]),dict(x=arrival[0],y=arrival[1])])
    for i,j in pairs:
        for a,b in [(i,j),(j,i)]:
            z=zones[a];p=next((p for p in z['portals'] if p['to']==b),None)
            if p is None:
                p=dict(id=f'path_{a}_{b}',name=zones[b]['name'],r=2.,to=b);z['portals'].append(p)
            point,_=endpoints[a,b];_,arrival=endpoints[b,a]
            p.update(name=zones[b]['name'],x=point[0],y=point[1],tx=arrival[0],ty=arrival[1],walk=list(sides[a,b]))
            p.pop('look',None)
    for i in sorted(OUTDOORS):
        z=zones[i]
        for p in z['portals']:
            if p['to'] not in OUTDOORS:continue
            prev=connected(z,[q for q in z['portals'] if q is not p])
            assert int(p['y'])*z['size']+int(p['x']) in prev,f"{i}: {p['id']} cut off by another crossing"
            path=approach(z,prev,(p['x'],p['y']))
            if path not in z.setdefault('paths',[]):z['paths'].append(path);z['atlasPaths'].append(path)
    world['atlas']=ATLAS
    sync_travel_links(zones)
    return len(pairs),sum(1 for i in OUTDOORS for p in zones[i]['portals'] if p['to'] in OUTDOORS)


def main():
    world = json.loads(MAP.read_text()); pairs, added = apply(world)
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False)+'\n')
    print(f'Organic atlas: {len(REGIONS)} regions, {pairs} path pairs, {added} directed crossings')


if __name__ == '__main__':
    main()
