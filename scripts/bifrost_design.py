#!/usr/bin/env python3
"""Bifrost Reach as an authored map (zone 7 of the shapes pilot): no filler, the whole painted province used.

Runs in `zone_shapes.py apply` after the Wyrdwood's design (it writes the Stormrift's arrival). Bifrost is `gateOnly`: it floats over the
storm and is reached by updrafts only, so it has no seams and no margin of land past any border; every crossing stays a portal, now standing
on the pad the painting shows for it. The outline is only the frame (world map, minimap); the floor is the six painted islands and their
rainbow bridges (`bifrost_geometry.py`, read from the owner's painted atlas), everything else is void sky.

Moved as rigid blocks from `world/zone-shapes/preshape-07.txt` (the old layout): Heimdall's Perch with its people, buildings, roads and the
Span door, the Empty Seat circle, the Ember Grave Cross and its sleeper. Moved by id: every person, place, portal and quest keeps its id.
Everything else (scenery, spawns, roads, wards, outposts, elites, quests) is laid fresh on the new floor.

    python3 scripts/bifrost_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import copy
import heapq
import json
import math
import os
import random
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bifrost_content as content  # noqa: E402
import bifrost_geometry as G  # noqa: E402
from greenmeadow_design import ground_spans  # noqa: E402

MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-07.txt'
ZONE = 7
HUB_BLOCK = (47, 118, 101, 157)          # the old Perch with its houses, the Span door and the Empty Seat circle (old frame)
BLOCK_KINDS = ('lamp', 'house', 'chapel', 'stall', 'fountain', 'noticeboard', 'bench')
AWARENESS = {'skoll': 10., 'shardking': 12., 'heimdallr': 11.}
GATE_OF = {'sky_gate': 'stormrift_down', 'maelstrom_up': 'maelstrom_down', 'path_9_7': 'path_7_9', 'path_1_7': 'path_7_1'}

# the wards of the old design: (seconds, tag suffix, kind, count) per wave; the sleepers stand 2-7 tiles outside the circle
WARDS = {
    'sky_ward_wind': [(15, 'a', 'galehound', 1), (40, 'b', 'galehound', 1)],
    'sky_ward_vigil': [(10, 'a', 'einherjar', 1), (40, 'b', 'einherjar', 1), (65, 'c', 'skyray', 1)],
    'sky_ward_last': [(8, 'a', 'thunderroc', 2), (50, 'b', 'prismgolem', 2), (90, 'c', 'thunderroc', 2)],
}
HOLDS = {'sky_beacon_m': 'galehound', 'sky_rod_m': 'skyray', 'sky_nest_m': 'thunderroc'}

# where the old, unmoved places go: (island, hint, radius)
OLD_PLACES = {
    'sky_windcairn': ('nw', (60, 134), 4.0), 'sky_spire': ('south', (232, 300), 4.5), 'sky_pylon': ('pylon', None, 4.5),
    'sky_hallgate': ('north', (148, 80), 4.0), 'sky_ward_wind': ('nw', (78, 104), 4.5), 'sky_ward_vigil': ('north', (160, 62), 4.5),
    'sky_ward_last': ('ne', (262, 58), 4.5),
}
PAD_OF = {'stormrift_down': 'stormrift', 'maelstrom_down': 'maelstrom', 'path_7_9': 'nacre', 'path_7_1': 'crags'}

# spawn bands: kind, count, min spacing, island, optional (cx, cy, radius) sub-area
BANDS = [
    ('galehound', 34, 7.0, 'nw', None), ('galehound', 5, 7.0, 'hub', None),
    ('prismgolem', 8, 6.5, 'south', None), ('prismgolem', 8, 7.5, 'hub', None),
    ('skyray', 28, 8.0, 'se', None), ('skyray', 3, 8.0, 'pylon', None),
    ('einherjar', 3, 7.0, 'pylon', None), ('einherjar', 5, 7.0, 'nw', (146, 112, 24)), ('einherjar', 12, 7.0, 'ne', (236, 124, 46)),
    ('thunderroc', 18, 8.0, 'ne', (266, 90, 60)),
]
HUB_CLEAR = 12.0


# ---- small helpers ------------------------------------------------------------------------------------------------------------
class Spots:
    """Spatial hash of things a new object must keep away from."""
    def __init__(self):
        self.cells = {}

    def add(self, x, y, r):
        self.cells.setdefault((int(x) >> 2, int(y) >> 2), []).append((x, y, r))

    def free(self, x, y, r, gap):
        reach = int(r + gap + 3) // 4 + 1
        cx, cy = int(x) >> 2, int(y) >> 2
        for i in range(cx - reach, cx + reach + 1):
            for j in range(cy - reach, cy + reach + 1):
                for ox, oy, orr in self.cells.get((i, j), ()):
                    if math.hypot(ox - x, oy - y) < r + orr + gap:
                        return False
        return True


def radius(o):
    return o.get('r') or max(o.get('width', 0), o.get('depth', 0)) / 2 * 1.42


def solid_mask(objects, n, pad=.35):
    """Cells a walker (radius .35) cannot stand in: round objects by r, boxes by half sizes."""
    m = np.zeros((n, n), bool)
    for o in objects:
        if o['kind'] == 'void':
            continue
        if o.get('width') and o.get('depth'):
            hx, hy = o['width'] / 2 + pad, o['depth'] / 2 + pad
            m[max(0, int(o['y'] - hy)):min(n, int(o['y'] + hy) + 1), max(0, int(o['x'] - hx)):min(n, int(o['x'] + hx) + 1)] = True
        elif o.get('r'):
            rr = o['r'] + pad
            for j in range(max(0, int(o['y'] - rr)), min(n, int(o['y'] + rr) + 1)):
                for i in range(max(0, int(o['x'] - rr)), min(n, int(o['x'] + rr) + 1)):
                    if math.hypot(i + .5 - o['x'], j + .5 - o['y']) < rr:
                        m[j, i] = True
    return m


def reach_from(open_cells, start):
    lab, _ = ndimage.label(open_cells)
    c = lab[int(start[1]), int(start[0])]
    return (lab == c) if c else np.zeros_like(open_cells)


def dense(points, step=2.0):
    out = []
    for a, b in zip(points, points[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(k)]
    out.append(tuple(points[-1]))
    return out


def route(walk, edge, a, b):
    """A* over walkable cells, staying off the rim; returns a simplified polyline of cell centres."""
    n = walk.shape[0]
    walk = walk.copy()
    s, t = (int(a[0]), int(a[1])), (int(b[0]), int(b[1]))
    walk[s[1], s[0]] = walk[t[1], t[0]] = True
    g = {s: 0.}
    came = {}
    heap = [(0., s)]
    while heap:
        _, c = heapq.heappop(heap)
        if c == t:
            break
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not (dx or dy):
                    continue
                q = (c[0] + dx, c[1] + dy)
                if not (0 <= q[0] < n and 0 <= q[1] < n) or not walk[q[1], q[0]]:
                    continue
                step = math.hypot(dx, dy) * (1 + (6. if edge[q[1], q[0]] < 3 else 0.))
                ng = g[c] + step
                if ng < g.get(q, 1e18):
                    g[q] = ng
                    came[q] = c
                    heapq.heappush(heap, (ng + math.hypot(q[0] - t[0], q[1] - t[1]), q))
    assert t in g, f'no route from {a} to {b}'
    path = [t]
    while path[-1] != s:
        path.append(came[path[-1]])
    path = [(x + .5, y + .5) for x, y in reversed(path)]
    return simplify(path, walk, 1.3)


def simplify(pts, walk, tol):
    """Douglas-Peucker, but a chord must stay on walkable cells."""
    def chord_ok(p, q):
        k = max(1, int(math.dist(p, q) * 2))
        return all(walk[int(p[1] + (q[1] - p[1]) * i / k), int(p[0] + (q[0] - p[0]) * i / k)] for i in range(k + 1))

    def rec(lo, hi):
        p, q = pts[lo], pts[hi]
        far, fd = None, 0.
        for i in range(lo + 1, hi):
            x, y = pts[i]
            dx, dy = q[0] - p[0], q[1] - p[1]
            ln = math.hypot(dx, dy) or 1e-9
            dist = abs((x - p[0]) * dy - (y - p[1]) * dx) / ln
            if dist > fd:
                far, fd = i, dist
        if far is not None and (fd > tol or not chord_ok(p, q)):
            return rec(lo, far)[:-1] + rec(far, hi)
        return [p, q]
    out = rec(0, len(pts) - 1) if len(pts) > 2 else list(pts)
    return [[round(x, 1), round(y, 1)] for x, y in out]


def rim(walk, cx, cy, dx, dy):
    """The last walkable point walking from (cx, cy) in direction (dx, dy)."""
    x, y = cx, cy
    while walk[int(y + dy * .25), int(x + dx * .25)]:
        x += dx * .25
        y += dy * .25
    return x, y


# ---- the design ----------------------------------------------------------------------------------------------------------------
class Reach:
    def __init__(self, world, old):
        import zone_shapes as zs
        self.zs = zs
        self.world, self.old = world, old
        zone = world['zones'][6]
        self.zone = zone
        self.n = zone['size']
        self.shape = zone['shape']
        outline = zs.inside_mask([tuple(p) for p in self.shape['outline']], self.n)
        self.walk, self.span, self.isl, self.pads, self.brs = G.masks(self.shape['T'], self.n, outline)
        self.land_mask = np.zeros_like(self.walk)
        for m in self.isl.values():
            self.land_mask |= m
        self.edge = ndimage.distance_transform_edt(self.walk)
        self.span_dist = ndimage.distance_transform_edt(~self.span)
        self.rng = random.Random(20261107)
        self.spots = Spots()
        self.objects = []
        self.walked = []                       # (x, y, what): roads, places, people, gates (an elite keeps clear of these)

    def mask(self, name):
        return self.isl[name] if name in self.isl else self.pads[name]

    def bbox(self, name):
        ys, xs = np.nonzero(self.mask(name))
        return (ys.min(), ys.max() + 1), (xs.min(), xs.max() + 1)

    def add(self, kind, x, y, r=None, solid=True, **extra):
        o = dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r if r is not None else 0, v=extra.pop('v', 0))
        o.update(extra)
        self.objects.append(o)
        if solid:
            self.spots.add(x, y, radius(o))
        return o

    def find(self, name, hint, margin=5.0, clear=0., minimum=2.0):
        """The cell of an island (or pad) nearest a hint whose edge distance is at least `margin` and that keeps `clear` from the spots."""
        ys, xs = np.nonzero(self.mask(name) & (self.edge >= margin))
        order = np.argsort((xs + .5 - hint[0]) ** 2 + (ys + .5 - hint[1]) ** 2)
        for k in order:
            x, y = xs[k] + .5, ys[k] + .5
            if self.spots.free(x, y, minimum, clear):
                return x, y
        raise SystemExit(f'no clear spot on {name} near {hint}')

    def place_hub(self):
        """Where the old Perch stands: the whole block inside the central island with 4 tiles to spare."""
        x0, y0, x1, y1 = HUB_BLOCK
        w, h = x1 - x0, y1 - y0
        m = ndimage.binary_erosion(self.isl['hub'], iterations=4)
        ii = np.pad(m.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        best = None
        want = (176, 198)         # the Stormrift pad lies to the west, the bridge north and the L bridge east: stand a little west of the middle
        for oy in range(0, self.n - h):
            for ox in range(0, self.n - w):
                if ii[oy + h, ox + w] - ii[oy, ox + w] - ii[oy + h, ox] + ii[oy, ox] != w * h:
                    continue
                cost = (ox + w / 2 - want[0]) ** 2 + (oy + h / 2 - want[1]) ** 2
                if best is None or cost < best[0]:
                    best = (cost, ox, oy)
        assert best, 'the old Perch does not fit on the central island'
        self.D = (best[1] - x0, best[2] - y0)
        return self.D

    def shift(self, o):
        o = copy.deepcopy(o)
        o['x'] = round(o['x'] + self.D[0], 2)
        o['y'] = round(o['y'] + self.D[1], 2)
        return o

    def in_block(self, o):
        x0, y0, x1, y1 = HUB_BLOCK
        return x0 <= o['x'] <= x1 and y0 <= o['y'] <= y1


def design(world, write=False):
    old = json.loads(OLD.read_text())
    d = Reach(world, old)
    zone = d.zone
    n = d.n
    rng = d.rng
    D = d.place_hub()

    # ---- rigid blocks: the Perch (people, houses, roads, the Span door, the Empty Seat circle), the cross and its sleeper
    npcs = [d.shift(x) for x in old['npcs']]
    for o in [d.shift(o) for o in old['objects'] if o['kind'] in BLOCK_KINDS and d.in_block(o)]:
        d.objects.append(o)
        d.spots.add(o['x'], o['y'], radius(o))
    city = copy.deepcopy(old['city'])
    for k in ('x0', 'x1'):
        city[k] += D[0]
    for k in ('y0', 'y1'):
        city[k] += D[1]
    for k in ('plaza', 'entry'):
        city[k] = dict(x=city[k]['x'] + D[0], y=city[k]['y'] + D[1])
    hub_places = [d.shift(p) for p in old['places'] if p['id'].startswith('es_07_')]
    span_portal = d.shift(next(p for p in old['portals'] if p['id'] == 'sky_shattered_span'))
    span_road = [[a + D[0], b + D[1]] for a, b in next(p for p in old['paths'] if p[-1] == [58, 128])]
    spawn = dict(x=old['spawn']['x'] + D[0], y=old['spawn']['y'] + D[1])
    for x in npcs:
        d.walked.append((x['x'], x['y'], 'npc ' + x['id']))
        d.spots.add(x['x'], x['y'], .5)
    for p in hub_places:
        d.walked.append((p['x'], p['y'], 'place ' + p['id']))
        d.spots.add(p['x'], p['y'], p['r'])

    # ---- the four updrafts, each on its painted pad: gate near the rim facing its neighbour, arrival six tiles in
    gates = {}
    for pid, direction in (('stormrift_down', (-1, 0)), ('maelstrom_down', (1, 0)), ('path_7_9', (1, 0)), ('path_7_1', (0, 1))):
        cx, cy = G.PADS[PAD_OF[pid]][:2]
        rx, ry = rim(d.walk, cx, cy, *direction)
        gate = (round(rx - direction[0] * 2.0, 1), round(ry - direction[1] * 2.0, 1))
        arrival = (round(gate[0] - direction[0] * 6.0, 1), round(gate[1] - direction[1] * 6.0, 1))
        assert d.walk[int(arrival[1]), int(arrival[0])], f'{pid}: the arrival is off the floor'
        gates[pid] = dict(gate=gate, arrival=arrival, walk=list(direction))
        d.walked.append((gate[0], gate[1], 'gate ' + pid))
        d.spots.add(gate[0], gate[1], 3.0)
        d.spots.add(arrival[0], arrival[1], 3.0)
    for pid, g in gates.items():
        for dx in (-1.5, 1.5):
            d.add('post', g['gate'][0] + dx * abs(g['walk'][1]), g['gate'][1] + dx * abs(g['walk'][0]), .45)

    # ---- the outposts
    hamlets = content.HAMLETS
    for key, h in hamlets.items():
        isl = {'roost': 'nw', 'station': 'se', 'landing': 'ne'}[key]
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx, cy = h['x'] + sx * h['hw'], h['y'] + sy * h['hh']
                assert d.isl[isl][int(cy), int(cx)] and d.edge[int(cy), int(cx)] >= 3, f"{h['name']}: the camp's corner ({cx}, {cy}) is off its island"
        d.walked.append((h['x'], h['y'], 'camp ' + key))
    content.dress(d, hamlets)
    for h in hamlets.values():
        d.spots.add(h['x'], h['y'], 6.0)

    # ---- places
    places = []
    for p in old['places']:
        if p['id'].startswith('es_07_'):
            continue
        isl, hint, r = OLD_PLACES[p['id']]
        if hint is None:
            ys, xs = np.nonzero(d.mask(isl))
            hint = (xs.mean() + .5, ys.mean() + .5)
        x, y = d.find(isl, hint, margin=min(r + 1, 5), clear=r + 2, minimum=r)
        q = dict(p, x=round(x, 1), y=round(y, 1), r=r)
        q.pop('waves', None)
        places.append(q)
        d.spots.add(x, y, r)
        d.walked.append((x, y, 'place ' + p['id']))
    for p in content.PLACES:
        x, y = d.find(p['island'], p['hint'], margin=min(p['r'] + 1, 5), clear=p['r'] + 3, minimum=p['r'])
        places.append(dict(id=p['id'], name=p['name'], x=round(x, 1), y=round(y, 1), r=p['r']))
        d.spots.add(x, y, p['r'] + 1)
        d.walked.append((x, y, 'place ' + p['id']))
    for pid, name, pad in content.PADS:
        g = gates[next(k for k, v in PAD_OF.items() if v == pad)]
        places.append(dict(id=pid, name=name, x=round((g['gate'][0] + g['arrival'][0]) / 2, 1), y=round((g['gate'][1] + g['arrival'][1]) / 2, 1), r=3.0))
    byid = {p['id']: p for p in places}

    # ---- landmarks on the places
    for p in places:
        pid, x, y = p['id'], p['x'], p['y']
        if pid in WARDS:
            d.add('wardstone', x, y, .7, place=pid)
        elif pid in ('sky_windcairn', 'sky_beacon_m'):
            d.add('windcairn', x, y, .8, place=pid)
        elif pid in ('sky_spire', 'sky_rod_m', 'sky_nest_m'):
            d.add('spirelight', x, y, .9, place=pid)
        elif pid == 'sky_pylon':
            d.add('pylon', x, y, 1.3, place=pid)
        elif pid == 'sky_hallgate':
            d.add('hallgate', x, y, 0, width=5.0, depth=1.4, place=pid)
        elif pid == 'sky_bell':
            d.add('column', x, y, .55, place=pid)
        elif pid == 'sky_tally':
            for k in range(7):
                a = k / 7 * 2 * math.pi
                d.add('skyrock', x + 2.4 * math.cos(a), y + 2.4 * math.sin(a), .5)
        elif pid == 'sky_shardfield':
            for k in range(5):
                a = k / 5 * 2 * math.pi + .4
                d.add('prism', x + 2.2 * math.cos(a), y + 2.2 * math.sin(a), .6)
    nest = d.find('ne', (270, 56), margin=5, clear=8, minimum=2.3)
    d.add('nest', nest[0], nest[1], 2.3)

    # ---- roads: every hub and gate joined, on the floor, around the buildings
    solid0 = solid_mask(d.objects, n)
    pylon = byid['sky_pylon']
    nodes = {
        'plaza': (city['entry']['x'], city['entry']['y']), 'stormrift': gates['stormrift_down']['gate'], 'maelstrom': gates['maelstrom_down']['gate'],
        'nacre': gates['path_7_9']['gate'], 'crags': gates['path_7_1']['gate'], 'pylon': (pylon['x'], pylon['y'] + 3),
        'roost': (hamlets['roost']['x'], hamlets['roost']['y'] + 3), 'station': (hamlets['station']['x'], hamlets['station']['y'] + 3),
        'landing': (hamlets['landing']['x'], hamlets['landing']['y'] + 3),
        'hallgate': (byid['sky_hallgate']['x'], byid['sky_hallgate']['y'] + 2.5), 'spire': (byid['sky_spire']['x'], byid['sky_spire']['y'] + 2.5),
    }
    links = [('stormrift', 'plaza'), ('plaza', 'pylon'), ('pylon', 'roost'), ('pylon', 'landing'), ('pylon', 'hallgate'), ('plaza', 'spire'), ('spire', 'crags'),
             ('plaza', 'station'), ('station', 'maelstrom'), ('station', 'nacre')]
    roads = [route(d.walk & ~solid0, d.edge, nodes[a], nodes[b]) for a, b in links]
    roads.append(span_road)
    for road in roads:
        for p in dense(road, 2.0):
            d.walked.append((p[0], p[1], 'road'))
            d.spots.add(p[0], p[1], 2.6)

    # ---- the grave cross and its sleeper
    cx, cy = d.find('se', (330, 240), margin=6, clear=9, minimum=2.5)
    cross = dict(copy.deepcopy(old['crosses'][0]), x=round(cx, 1), y=round(cy, 1))
    d.spots.add(cx, cy, 4)

    # ---- the elites: the clearest ground on their island, awareness + 3 tiles from everything walked
    pts = [(x, y) for x, y, _ in d.walked]
    for c in [city] + content.camps(hamlets):
        for t in range(int(c['x0']), int(c['x1']) + 1, 2):
            pts += [(t, c['y0']), (t, c['y1'])]
        for u in range(int(c['y0']), int(c['y1']) + 1, 2):
            pts += [(c['x0'], u), (c['x1'], u)]
    elites = []
    for kind, isl in content.ELITES:
        ys, xs = np.nonzero(d.isl[isl] & (d.edge >= 8))
        cells = np.stack([xs + .5, ys + .5], 1)
        dist, _ = cKDTree(np.array(pts)).query(cells)
        for ex, ey, _k in elites:
            dist = np.minimum(dist, np.hypot(cells[:, 0] - ex, cells[:, 1] - ey) * 1.2)
        k = int(dist.argmax())
        assert dist[k] >= AWARENESS[kind] + 3, f'{kind} has only {dist[k]:.1f} tiles of clear ground on {isl}'
        elites.append((float(cells[k, 0]), float(cells[k, 1]), kind))
        d.spots.add(cells[k, 0], cells[k, 1], 5)
        pts.append((cells[k, 0], cells[k, 1]))

    # ---- scenery
    def scatter(kind, count, r, islands, margin=1.2, edge_min=3.0):
        done, tries = 0, 0
        while done < count and tries < 80000:
            tries += 1
            name = rng.choice(islands)
            (y0, y1), (x0, x1) = d.bbox(name)
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if not d.mask(name)[int(y), int(x)] or d.edge[int(y), int(x)] < edge_min or d.span_dist[int(y), int(x)] < 3.5:
                continue
            if not d.spots.free(x, y, r, margin):
                continue
            d.add(kind, x, y, r, v=rng.randrange(4))
            done += 1
        assert done == count, f'only {done} of {count} {kind}'
    every = ['nw', 'hub', 'north', 'ne', 'se', 'south']
    scatter('skypine', 70, .42, ['nw'])
    scatter('skypine', 14, .42, ['hub', 'north', 'ne'])
    scatter('prism', 26, .6, ['south'], margin=1.6)
    scatter('prism', 12, .6, ['se', 'ne'], margin=1.6)
    scatter('column', 22, .55, ['se'], margin=1.8)
    scatter('column', 18, .55, ['north'], margin=1.8)
    scatter('skyrock', 110, .45, every, margin=1.2)
    scatter('cloudpuff', 330, .3, every, margin=.8, edge_min=2.0)

    # ---- spawns
    spawns = []
    keep = [(p['x'], p['y'], p['r'] + 4.5) for p in places + hub_places]
    keep += [(h['x'], h['y'], max(h['hw'], h['hh']) + 7) for h in hamlets.values()]
    keep += [(g['gate'][0], g['gate'][1], 11.0) for g in gates.values()]
    for kind, count, spacing, isl, sub in BANDS:
        done, tries = 0, 0
        why = {}
        (y0, y1), (x0, x1) = d.bbox(isl)

        def no(reason):
            why[reason] = why.get(reason, 0) + 1
        while done < count and tries < 80000:
            tries += 1
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if not d.mask(isl)[int(y), int(x)]:
                continue
            if d.edge[int(y), int(x)] < 3.5:
                no('edge')
                continue
            if isl != 'pylon' and d.span_dist[int(y), int(x)] < 5.0:
                no('bridge')
                continue
            if sub and math.hypot(x - sub[0], y - sub[1]) > sub[2]:
                no('sub')
                continue
            if city['x0'] - HUB_CLEAR <= x <= city['x1'] + HUB_CLEAR and city['y0'] - HUB_CLEAR <= y <= city['y1'] + HUB_CLEAR:
                no('hub')
                continue
            if any(math.hypot(x - a, y - b) < r for a, b, r in keep):
                no('keep')
                continue
            if any(math.hypot(x - s['x'], y - s['y']) < (spacing if s['kind'] == kind else 6.5) for s in spawns):
                no('spacing')
                continue
            if any(math.hypot(x - e[0], y - e[1]) < AWARENESS[e[2]] + 3 for e in elites):
                no('elite')
                continue
            if not d.spots.free(x, y, .4, 2.0):
                no('spots')
                continue
            spawns.append(dict(x=round(x, 2), y=round(y, 2), kind=kind))
            done += 1
        assert done == count, f'only {done} of {count} {kind} on {isl}: rejected {why}'
    for ex, ey, kind in elites:
        spawns.append(dict(kind=kind, x=round(ex, 2), y=round(ey, 2)))
    plans = dict(WARDS)
    for pid, kind in HOLDS.items():
        plans[pid] = [(1, 'a', kind, 2), (11, 'b', kind, 2)]
    sleepers = []
    for pid, plan in plans.items():
        pl = byid[pid]
        isl = next(k for k, m in d.isl.items() if m[int(pl['y']), int(pl['x'])])
        pl['waves'] = []
        for at, sfx, kind, count in plan:
            tag = f'{pid}#{sfx}'
            pl['waves'].append(dict(at=at, tag=tag))
            got = 0
            for _ in range(40000):
                ang = rng.uniform(0, 2 * math.pi)
                dd = rng.uniform(pl['r'] + 2.4, pl['r'] + 7.0)
                x, y = pl['x'] + dd * math.cos(ang), pl['y'] + dd * math.sin(ang)
                if not (0 < x < n and 0 < y < n) or not d.isl[isl][int(y), int(x)] or d.edge[int(y), int(x)] < 3:
                    continue
                if any(math.hypot(x - q['x'], y - q['y']) < 3.0 for q in sleepers + spawns):
                    continue
                if not d.spots.free(x, y, .4, 1.4):
                    continue
                sleepers.append(dict(x=round(x, 2), y=round(y, 2), kind=kind, ambush=tag))
                got += 1
                if got == count:
                    break
            assert got == count, f'no room for the {tag} wave'
    spawns += sleepers
    spawns.append(dict(kind='ember_firelord', x=round(cx - 2.5, 2), y=round(cy, 2), ambush=f'raid_key:{ZONE}'))

    # ---- write the zone
    zone['spawn'] = spawn
    zone['shape']['placeAtSpawn'] = True        # saved characters are moved to the spawn (zone_shapes_migrate.py): this is not a rigid shift
    zone['city'] = city
    zone['npcs'] = npcs
    zone['places'] = hub_places + places
    zone['quests'] = copy.deepcopy(old['quests'])
    zone['crosses'] = [cross]
    zone['slimes'] = spawns
    zone['sky'] = [''.join('=' if d.span[j, i] else '#' if d.walk[j, i] else ' ' for i in range(n)) for j in range(n)]
    voids = d.zs.void_pieces(d.walk)
    for o in voids:
        o.pop('layout', None)
    zone['objects'] = voids + d.objects
    for p in zone['portals']:           # the live portals keep what the Wyrdwood's design and the seams wrote (arrival coordinates)
        if p['id'] == 'sky_shattered_span':
            p.update(x=span_portal['x'], y=span_portal['y'])
        else:
            g = gates[p['id']]
            p.update(x=g['gate'][0], y=g['gate'][1], walk=g['walk'])
    # region names for the HUD: each island and pad, the bridges between (a hub or an outpost names itself over its region)
    names = ['Windward Meadow', "Heimdall's Perch", 'The Hall of the Fallen', "The Roc's Eyrie", 'The Stormcrown', 'The Shardfields',
             'The Bifrost Pylon', 'The Stormrift Pad', 'The Maelstrom Pad', 'The Nacrehold Pad', 'The Rainbow Bridges']
    region = np.zeros((n, n), np.int16)
    region[d.walk] = len(names)
    for i, k in enumerate(('nw', 'hub', 'north', 'ne', 'se', 'south')):
        region[d.isl[k]] = i + 1
    for i, k in enumerate(('pylon', 'stormrift', 'maelstrom', 'nacre')):
        region[d.pads[k] & ~d.land_mask] = 7 + i
    zone['regions'] = dict(names=names, spans=ground_spans(region, d.walk))
    zone['paths'] = roads
    zone['atlasPaths'] = []
    zone['exitRoutes'] = [dict(portal=pid, points=[list(g['gate']), list(g['arrival'])]) for pid, g in gates.items()]
    content.install(zone, hamlets, [p for p in places])
    # the portals that arrive here
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] != ZONE:
                continue
            if p['id'] in GATE_OF:
                p['tx'], p['ty'] = gates[GATE_OF[p['id']]]['arrival']
            elif p['id'] in ('span_return', 'span_clear'):
                p['tx'], p['ty'] = span_portal['x'], span_portal['y'] + 5
    if write:
        content.record_mailboxes(zone, hamlets, ROOT / 'world/mailboxes.txt')

    problems = check(d, zone, gates, elites, spawn)
    stats = dict(land=int(d.walk.sum()), bridges=int(d.span.sum()), objects=len([o for o in zone['objects'] if o['kind'] != 'void']), voids=len(voids),
                 spawns=len(spawns), quests=len(zone['quests']), hub_shift=list(D), elites=[(k, round(x), round(y)) for x, y, k in elites])
    if problems:
        if os.environ.get('BIFROST_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


def check(d, zone, gates, elites, spawn):
    n = d.n
    problems = []
    objs = [o for o in zone['objects'] if o['kind'] != 'void']
    solid = solid_mask(objs, n)
    open_cells = d.walk & ~solid
    seen = reach_from(open_cells, (spawn['x'], spawn['y']))
    lost = int((open_cells & ~seen).sum())
    if lost > open_cells.sum() * .01:
        problems.append(f'{lost} open cells are cut off from the spawn')
    for t in zone['slimes']:
        if not d.walk[int(t['y']), int(t['x'])]:
            problems.append(f'spawn off the floor {t}')
        elif not seen[int(t['y']), int(t['x'])]:
            problems.append(f'unreachable spawn {t}')
    bare = solid_mask(objs, n, pad=0.)             # a person's own cell, not the walker's clearance: the camps' braziers sit close
    lab, _ = ndimage.label(d.walk)
    for npc in zone['npcs']:
        if bare[int(npc['y']), int(npc['x'])]:
            problems.append(f"{npc['id']} stands inside scenery at {npc['x']},{npc['y']}")
        elif not lab[int(npc['y']), int(npc['x'])] == lab[int(spawn['y']), int(spawn['x'])]:
            problems.append(f"unreachable npc {npc['id']} at {npc['x']},{npc['y']}")
    yy, xx = np.mgrid[0:n, 0:n]
    for p in zone['places']:
        disc = (np.hypot(xx + .5 - p['x'], yy + .5 - p['y']) <= p['r']) & seen         # some ground inside the circle can be walked to
        if not disc.any():
            problems.append(f"unreachable place {p['id']}")
    for pid, g in gates.items():
        a = g['arrival']
        if not seen[int(a[1]), int(a[0])]:
            problems.append(f'arrival of {pid} is cut off')
    for o in objs:
        if o['kind'] in ('house', 'chapel', 'stall', 'fountain', 'lamp', 'bench', 'noticeboard', 'tent') and not d.walk[int(o['y']), int(o['x'])]:
            problems.append(f"{o['kind']} at ({o['x']}, {o['y']}) hangs over the void")
    for road in zone['paths']:
        for p in dense(road, 1.0):
            if not d.walk[int(p[1]), int(p[0])]:
                problems.append(f'road leaves the floor at {p}')
    cover = np.zeros((n, n), np.int16)
    for o in zone['objects']:
        if o['kind'] == 'void':
            x0, x1 = int(round(o['x'] - o['width'] / 2)), int(round(o['x'] + o['width'] / 2))
            y0, y1 = int(round(o['y'] - o['depth'] / 2)), int(round(o['y'] + o['depth'] / 2))
            cover[y0:y1, x0:x1] += 1
    if not (cover[~d.walk] == 1).all() or (cover[d.walk] != 0).any():
        problems.append('void does not cover exactly the empty sky')

    def islands_cut(*bridges):
        m = solid.copy()
        for bridge in bridges:
            b = G.BRIDGES[bridge]
            mid = max(zip(b, b[1:]), key=lambda s: math.dist(*s))
            cx, cy = (mid[0][0] + mid[1][0]) / 2, (mid[0][1] + mid[1][1]) / 2
            m[int(cy - 3):int(cy + 4), int(cx - 3):int(cx + 4)] = True
        reach = reach_from(d.walk & ~m, (spawn['x'], spawn['y']))
        out = set()
        for name, mask in list(d.isl.items()) + [('pad:' + k, v) for k, v in d.pads.items()]:
            probe = mask & ~solid & (d.edge >= 3)
            if probe.any() and not (probe & reach).any():
                out.add(name)
        return out
    # the bridge graph has cycles (the Perch, the Stormrift pad, Windward Meadow and the pylon form a ring, as do the Perch, the Shardfields and
    # the Stormcrown): these are the cuts that must hold
    expect = [
        (('b_se_nacre',), {'pad:nacre'}),
        (('b_pad_nw', 'b_pylon_nw'), {'nw'}),
        (('b_pylon_north', 'b_north_ne'), {'north'}),
        (('b_hub_south', 'b_south_se'), {'south', 'pad:crags'}),
        (('b_pad_hub',), set()),
        (('b_hub_pylon',), set()),
    ]
    for ids, want in expect:
        got = islands_cut(*ids)
        if got != want:
            problems.append(f'closing {ids} cuts off {sorted(got)}, expected {sorted(want)}')
    for ex, ey, kind in elites:
        near = min((math.hypot(ex - x, ey - y), w) for x, y, w in d.walked)
        if near[0] < AWARENESS[kind] + 3:
            problems.append(f'{kind} stands {near[0]:.1f} tiles from a {near[1]}')
    counts = {}
    for s in zone['slimes']:
        counts[s['kind']] = counts.get(s['kind'], 0) + 1
    for kind, want in (('galehound', 40), ('prismgolem', 14), ('skyray', 25), ('einherjar', 18), ('thunderroc', 18)):
        if counts.get(kind, 0) < want:
            problems.append(f'only {counts.get(kind, 0)} {kind}')
    return problems


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = zone['size']
    img = Image.new('RGB', (n * scale, n * scale), (24, 18, 50))
    dr = ImageDraw.Draw(img)
    for j, row in enumerate(zone['sky']):
        for i, c in enumerate(row):
            if c != ' ':
                dr.rectangle([i * scale, j * scale, (i + 1) * scale - 1, (j + 1) * scale - 1], fill=(90, 150, 90) if c == '#' else (240, 150, 220))
    colours = {'skypine': (20, 90, 50), 'prism': (150, 220, 255), 'column': (230, 230, 240), 'skyrock': (120, 120, 140), 'cloudpuff': (225, 230, 245),
               'house': (190, 120, 80), 'chapel': (220, 130, 110), 'tent': (200, 170, 110), 'lamp': (255, 240, 120), 'stall': (210, 170, 90)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        c = colours.get(o['kind'], (255, 255, 255))
        if o.get('width') and o.get('depth'):
            dr.rectangle([(o['x'] - o['width'] / 2) * scale, (o['y'] - o['depth'] / 2) * scale, (o['x'] + o['width'] / 2) * scale, (o['y'] + o['depth'] / 2) * scale], fill=c)
        else:
            r = max(1.5, (o.get('r') or .3) * scale)
            dr.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    for road in zone['paths']:
        dr.line([(x * scale, y * scale) for x, y in road], fill=(255, 220, 150), width=2)
    kc = {'galehound': (230, 70, 70), 'prismgolem': (70, 210, 255), 'skyray': (210, 70, 210), 'einherjar': (240, 240, 70), 'thunderroc': (255, 150, 0)}
    for s in zone['slimes']:
        col = kc.get(s['kind'], (255, 255, 255))
        r = 9 if s['kind'] in ('skoll', 'shardking', 'heimdallr') else 3 if s.get('ambush') else 5
        dr.ellipse([s['x'] * scale - r, s['y'] * scale - r, s['x'] * scale + r, s['y'] * scale + r], outline=col, width=2)
    for npc in zone['npcs']:
        dr.rectangle([npc['x'] * scale - 2, npc['y'] * scale - 2, npc['x'] * scale + 2, npc['y'] * scale + 2], fill=(255, 255, 0))
    for p in zone['places']:
        dr.ellipse([(p['x'] - p['r']) * scale, (p['y'] - p['r']) * scale, (p['x'] + p['r']) * scale, (p['y'] + p['r']) * scale], outline=(0, 255, 255), width=1)
    for c in zone.get('camps', []) + [zone['city']]:
        dr.rectangle([c['x0'] * scale, c['y0'] * scale, c['x1'] * scale, c['y1'] * scale], outline=(255, 255, 255), width=1)
    for p in zone['portals']:
        dr.ellipse([p['x'] * scale - 6, p['y'] * scale - 6, p['x'] * scale + 6, p['y'] * scale + 6], outline=(255, 60, 60), width=3)
    img.save(out)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == 'plan':
        world = json.loads(MAP.read_text())
        d, stats = design(world, write=False)
        plan_picture(world['zones'][6], d, sys.argv[2])
        print(stats)
        return
    raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
