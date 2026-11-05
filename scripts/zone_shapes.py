#!/usr/bin/env python3
"""Zone shapes: give a square zone the outline its province has on the painted world atlas.

Design (docs/zone-shapes.md). The old square layout is the SOURCE: this overlay never edits it in place.

  python3 scripts/zone_shapes.py unshape   restore every shaped zone from world/zone-shapes/preshape-<z>.txt
  python3 scripts/zone_shapes.py apply     save the current (old-layout) zone to its sidecar, then shape it

sync-world runs `unshape` first (so every generator and overlay sees the old square layout and its old
coordinates) and `apply` just before compact_atlas (so portals are placed on the real shared borders).
Never run a zone generator on a shaped zone: run `unshape` first (the generators refuse).

What `apply` does to a zone (rule `nofloor`, owner decision 2026-11-05):
  * the atlas outline is scaled to tiles (k tiles per atlas px, never shrinking the zone's old area, always
    holding the city footprint), smoothed once per shared chain (neighbours get identical borders), centred in
    a square grid whose side is a multiple of 8;
  * the old square is a CORE that keeps its content unchanged: it is translated as a block to the spot inside
    the outline where its old border gates land nearest their shared borders;
  * the rest of the outline is filled with scenery, trails and spawns at the old densities;
  * everything outside the outline becomes `void` collision (the Bifrost mechanism), `shapeFloor` rows tell
    the client what to draw, `shapeEdge` rows tell it what the outside is (coast, border, outer land);
  * portals to neighbours are placed by compact_atlas on the shared chains (`shape.edges`).
Seeded and byte-stable.
"""
import argparse
import copy
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import atlas_geography  # noqa: E402

MAP = ROOT / 'world/map.txt'
SIDE = ROOT / 'world/zone-shapes'
CONFIG = ROOT / 'world/zone-shapes.txt'
TAG = 'shape_v1'
VOID_PIECE = 12
EDGE_BAND = 14
SEAM_MARGIN = 2.4
STRUCTURAL = {'wall', 'lamp', 'house', 'flowers', 'post', 'void', 'lava', 'water'}
ELITE_OR_SCRIPTED = ('big', 'cinderlord', 'ember_firelord', 'es_')

# Per-zone fill style. `decor`: kinds scattered at the old density; `rivers`: Crags lava rivers continue.
FILL = {
    0: dict(spawn_sep=5.0, spawn_feature='city_distance', decor=('tree', 'bush', 'rock')),
    1: dict(spawn_sep=7.0, spawn_feature='y', decor=('rock', 'tree', 'bush', 'spire'), rivers=True),
    16: dict(spawn_sep=5.0, spawn_feature='city_distance', decor=('gloomstalk', 'sporefern', 'moonstone', 'glowmoss', 'mooncaps'),
         elites=('mireheart', 'silverwidow', 'nightbloom')),
}


def config():
    return json.loads(CONFIG.read_text())


# ---- the old layout view of a zone ------------------------------------------------------------------------------------
def view_keys(world, z):
    zone = world if z == 0 else world['zones'][z - 1]
    skip = {'zones', 'atlas'} if z == 0 else set()
    return zone, [k for k in zone if k not in skip]


def get_view(world, z):
    zone, keys = view_keys(world, z)
    return {k: copy.deepcopy(zone[k]) for k in keys}


def set_view(world, z, view):
    """Replace the zone's own keys by `view`, keeping the key order of map.txt (a stable diff)."""
    zone, keys = view_keys(world, z)
    skip = {'zones', 'atlas'} if z == 0 else set()
    current = list(zone)
    ordered = {}
    for k in current:
        if k in skip:
            ordered[k] = zone[k]
        elif k in view:
            ordered[k] = copy.deepcopy(view[k])
    for k in view:
        if k not in ordered:
            ordered[k] = copy.deepcopy(view[k])
    zone.clear()
    zone.update(ordered)


def zone_of(world, z):
    return world if z == 0 else world['zones'][z - 1]


# ---- geometry ----------------------------------------------------------------------------------------------------------
def area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def chaikin(pts, rounds=2):
    for _ in range(rounds):
        if len(pts) < 3:
            return pts
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out.append((a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25))
            out.append((a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75))
        out.append(pts[-1])
        pts = out
    return pts


def inside_mask(poly, n):
    """Cell (x, y) is floor when its centre lies inside the polygon (even-odd rule, vectorised)."""
    ys, xs = np.mgrid[0:n, 0:n]
    px, py = xs + .5, ys + .5
    inside = np.zeros((n, n), dtype=bool)
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if y1 == y2:
            continue
        cond = (y1 > py) != (y2 > py)
        xint = (x2 - x1) * (py - y1) / (y2 - y1) + x1
        inside ^= cond & (px < xint)
    return inside


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = 0 if dx == dy == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def chain_distance(p, polyline):
    return min(seg_dist(p, a, b) for a, b in zip(polyline, polyline[1:]))


def erode(mask, r):
    m = mask.copy()
    for _ in range(r):
        e = m.copy()
        e[1:] &= m[:-1]
        e[:-1] &= m[1:]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        e[0] = e[-1] = False
        e[:, 0] = e[:, -1] = False
        m = e
    return m


def dilate(mask, r):
    m = mask.copy()
    for _ in range(r):
        d = m.copy()
        d[1:] |= m[:-1]
        d[:-1] |= m[1:]
        d[:, 1:] |= m[:, :-1]
        d[:, :-1] |= m[:, 1:]
        m = d
    return m


def void_pieces(floor):
    """Cover every non-floor cell with bounded collision rectangles (same scheme as generate_bifrost)."""
    wall = ~floor
    n = floor.shape[0]
    used = np.zeros_like(wall)
    rects = []
    for j in range(n):
        i = 0
        while i < n:
            if wall[j, i] and not used[j, i]:
                i1 = i
                while i1 + 1 < n and wall[j, i1 + 1] and not used[j, i1 + 1]:
                    i1 += 1
                j1 = j
                while j1 + 1 < n and wall[j1 + 1, i:i1 + 1].all() and not used[j1 + 1, i:i1 + 1].any():
                    j1 += 1
                used[j:j1 + 1, i:i1 + 1] = True
                rects.append((i, j, i1 + 1, j1 + 1))
                i = i1 + 1
            else:
                i += 1
    out = []
    for x0, y0, x1, y1 in rects:
        w, d = x1 - x0, y1 - y0
        if w >= d:
            for a in range(x0, x1, VOID_PIECE):
                b = min(a + VOID_PIECE, x1)
                out.append(((a + b) / 2, (y0 + y1) / 2, b - a, d))
        else:
            for a in range(y0, y1, VOID_PIECE):
                b = min(a + VOID_PIECE, y1)
                out.append(((x0 + x1) / 2, (a + b) / 2, w, b - a))
    return [{'kind': 'void', 'x': round(x, 2), 'y': round(y, 2), 'r': round(max(w, d) / 2, 2), 'width': round(w, 2),
             'depth': round(d, 2), 'layout': TAG} for x, y, w, d in out]


# ---- atlas outlines: runs by edge class, smoothed once per shared chain ---------------------------------------------
def is_water(rgb):
    r, g, b = rgb
    return b >= g - 6 and b - r > 12


def inside_pt(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


class Atlas:
    def __init__(self):
        atlas, _ = atlas_geography.generate()
        self.atlas = atlas
        self.polys = {r['zone']: [tuple(p) for p in r['outline'][0]] for r in atlas['regions']}
        self.pairs = {(l['a'], l['b']): l for l in atlas['links']}
        self.neighbours = defaultdict(set)
        for a, b in self.pairs:
            self.neighbours[a].add(b)
            self.neighbours[b].add(a)
        self.owners = defaultdict(list)
        for z, p in self.polys.items():
            for a, b in zip(p, p[1:] + p[:1]):
                self.owners[tuple(sorted((a, b)))].append(z)
        self.img = Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB')
        self.ps = self.img.size[0] / atlas['width']

    def edge_key(self, z, a, b):
        zs = self.owners[tuple(sorted((a, b)))]
        if len(zs) == 2:
            other = [o for o in zs if o != z][0]
            return ('shared', other) if tuple(sorted(zs)) in self.pairs else ('corner', other)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        ln = math.hypot(nx, ny) or 1
        poly = self.polys[z]
        sgn = 1 if not inside_pt((mx + nx / ln * 14, my + ny / ln * 14), poly) else -1
        W, H = self.atlas['width'], self.atlas['height']

        def at(dist):
            q = (max(0, min(W - 1, mx + sgn * nx / ln * dist)), max(0, min(H - 1, my + sgn * ny / ln * dist)))
            return q, self.img.getpixel((min(self.img.size[0] - 1, int(q[0] * self.ps)), min(self.img.size[1] - 1, int(q[1] * self.ps))))
        q14, _ = at(14)
        if any(o != z and inside_pt(q14, p) for o, p in self.polys.items()):
            return ('gap', None)
        # A pale beach strip lies between the province and the sea: any open water within 60 px outward makes it coast.
        water = sum(1 for d in (12, 24, 36, 48, 60) if is_water(at(d)[1]))
        return ('coast', None) if water >= 2 else ('land', None)

    def runs(self, z):
        """Maximal runs of equal edge class around the outline, each from junction to junction (atlas coords)."""
        p = self.polys[z]
        n = len(p)
        keys = [self.edge_key(z, p[i], p[(i + 1) % n]) for i in range(n)]
        start = next((i for i in range(n) if keys[i] != keys[i - 1]), 0)
        runs = []
        i = 0
        while i < n:
            k = keys[(start + i) % n]
            pts = [p[(start + i) % n]]
            j = i
            while j < n and keys[(start + j) % n] == k:
                pts.append(p[(start + j + 1) % n])
                j += 1
            runs.append((k, pts))
            i = j
        return runs


# ---- scale and placement -----------------------------------------------------------------------------------------------
def city_fits(poly, s, cw, ch):
    x0 = min(q[0] for q in poly)
    y0 = min(q[1] for q in poly)
    pts = [((q[0] - x0) * s, (q[1] - y0) * s) for q in poly]
    n = math.ceil(max(max(p[0] for p in pts), max(p[1] for p in pts))) + 2
    m = inside_mask(pts, n)
    for yy in range(0, n, 2):
        for xx in range(0, n, 2):
            if all(0 <= int(yy + ch * fy) < n and 0 <= int(xx + cw * fx) < n and m[int(yy + ch * fy), int(xx + cw * fx)]
                   for fx in (0, .25, .5, .75, 1) for fy in (0, .25, .5, .75, 1)):
                return True
    return False


def zone_scale(cfg, atlas, z, old):
    s = cfg['k']
    s = max(s, math.sqrt(old['size'] ** 2 / area(atlas.polys[z])))
    c = old.get('city')
    if c:
        cw, ch = c['x1'] - c['x0'], c['y1'] - c['y0']
        while not city_fits(atlas.polys[z], s, cw, ch) and s < cfg['k'] * 8:
            s *= 1.04
    return s


def ceil8(v):
    return (v + 7) // 8 * 8


def shape_geometry(cfg, atlas, z, old):
    s = zone_scale(cfg, atlas, z, old)
    poly = atlas.polys[z]
    x0 = min(q[0] for q in poly)
    y0 = min(q[1] for q in poly)
    # Tile coordinates are atlas * s - T with an INTEGER T per zone, so two shaped zones differ by a whole-tile shift
    # (their cell grids, noise and rasterised borders then line up exactly across a seam).
    fx, fy = x0 * s - math.floor(x0 * s), y0 * s - math.floor(y0 * s)
    W = math.ceil((max(q[0] for q in poly) - x0) * s + fx)
    H = math.ceil((max(q[1] for q in poly) - y0) * s + fy)
    n = ceil8(max(W, H))
    offx, offy = (n - W) // 2, (n - H) // 2
    Tx, Ty = math.floor(x0 * s) - offx, math.floor(y0 * s) - offy
    tx = lambda q: (q[0] * s - Tx, q[1] * s - Ty)
    runs = []
    outline = []
    for key, pts in atlas.runs(z):
        sm = [tx(q) for q in pts]
        sm = chaikin(sm, 2) if key[0] in ('shared', 'corner') or len(sm) > 2 else sm
        runs.append(dict(kind=key[0], other=key[1], points=[[round(a, 2), round(b, 2)] for a, b in sm]))
        outline.extend(sm[:-1])
    floor = inside_mask(outline, n)
    return dict(scale=s, size=n, T=[Tx, Ty], bbox=[W, H], outline=[[round(a, 2), round(b, 2)] for a, b in outline], runs=runs, floor=floor)


def edge_rows(geom, neighbours):
    """One char per cell: which kind of edge the outside cell borders (A.. border with shape.neighbours[i], c coast, l land, g gap)."""
    n = geom['size']
    floor = geom['floor']
    band = dilate(floor, EDGE_BAND) & ~floor
    pts = []
    for run in geom['runs']:
        ch = {'corner': 'b', 'coast': 'c', 'land': 'l', 'gap': 'g'}.get(run['kind'])
        if run['kind'] == 'shared':
            ch = chr(ord('A') + neighbours.index(run['other']))   # border with that neighbour (index into shape.neighbours)
        for a, b in zip(run['points'], run['points'][1:]):
            steps = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1])))
            for i in range(steps + 1):
                pts.append((a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps, ch))
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    chs = [p[2] for p in pts]
    rows = []
    for y in range(n):
        row = []
        for x in range(n):
            if band[y, x]:
                d = (xs - (x + .5)) ** 2 + (ys - (y + .5)) ** 2
                row.append(chs[int(d.argmin())])
            else:
                row.append(' ')
        rows.append(''.join(row))
    return rows


def floor_rows(floor):
    return [''.join('#' if v else ' ' for v in row) for row in floor]


def choose_offset(geom, old, z, atlas, world):
    """Where the old square sits in the new frame: fully inside the outline, old border gates near their chains."""
    n, S0 = geom['size'], old['size']
    mask = erode(geom['floor'], 2)
    integral = np.pad(mask.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    full = S0 * S0
    cx = np.mean([p[0] for p in geom['outline']])
    cy = np.mean([p[1] for p in geom['outline']])
    chains = defaultdict(list)
    for run in geom['runs']:
        if run['kind'] == 'shared':
            chains[run['other']].append(run['points'])
    best = None
    for oy in range(0, n - S0 + 1):
        for ox in range(0, n - S0 + 1):
            c = integral[oy + S0, ox + S0] - integral[oy, ox + S0] - integral[oy + S0, ox] + integral[oy, ox]
            if c != full:
                continue
            cost = 0.
            for p in old['portals']:
                if p['to'] in chains and p['to'] in atlas.neighbours[z]:
                    q = (p['x'] + ox, p['y'] + oy)
                    cost += min(chain_distance(q, pl) for pl in chains[p['to']]) ** 2
            cost += .05 * ((ox + S0 / 2 - cx) ** 2 + (oy + S0 / 2 - cy) ** 2)
            if best is None or cost < best[0]:
                best = (cost, ox, oy)
    if best is None:
        raise SystemExit(f'zone {z}: the {S0}x{S0} old square does not fit inside the outline with a 2 tile margin')
    return best[1], best[2]


# ---- translation of a zone view ---------------------------------------------------------------------------------------
def shift_xy(d, dx, dy, kx='x', ky='y'):
    if kx in d and ky in d:
        d[kx] += dx
        d[ky] += dy


def shift_view(view, dx, dy):
    shift_xy(view['spawn'], dx, dy)
    for key in ('objects', 'slimes', 'npcs', 'places', 'crosses'):
        for o in view.get(key, []):
            shift_xy(o, dx, dy)
    for c in [view['city']] + list(view.get('camps', [])) if view.get('city') else list(view.get('camps', [])):
        c['x0'] += dx
        c['x1'] += dx
        c['y0'] += dy
        c['y1'] += dy
        for k in ('plaza', 'entry'):
            if k in c:
                shift_xy(c[k], dx, dy)
    for p in view.get('portals', []):
        shift_xy(p, dx, dy)
    for key in ('paths', 'atlasPaths'):
        view[key] = [[[a + dx, b + dy] for a, b in path] for path in view.get(key, [])]
    for e in view.get('exitRoutes', []):
        e['points'] = [[a + dx, b + dy] for a, b in e['points']]
    for e in view.get('cityEntrances', []):
        e['points'] = [[a + dx, b + dy] for a, b in e['points']]
        if 'opening' in e:
            shift_xy(e['opening'], dx, dy)
        if 'street' in e:
            e['street'] += dx if e.get('axis') == 'y' else dy
        shift_xy(e, dx, dy)
    for key in ('seasonDecor', 'christmasDecor', 'easterDecor', 'solsticeDecor', 'valentineDecor'):
        for o in view.get(key, []):
            shift_xy(o, dx, dy)
    for r in view.get('roads', []):
        for kx, ky in (('x', 'y'), ('x0', 'y0'), ('x1', 'y1')):
            shift_xy(r, dx, dy, kx, ky)


def shift_incoming(world, targets, sign):
    """Portals elsewhere that arrive in a shifted zone carry arrival coordinates in that zone's frame."""
    for zi in range(1 + len(world['zones'])):
        for p in zone_of(world, zi).get('portals', []):
            to = p['to']
            if to in targets and 'tx' in p and zi not in targets:
                p['tx'] += sign * targets[to][0]
                p['ty'] += sign * targets[to][1]


# ---- fill ---------------------------------------------------------------------------------------------------------------
def dist_to_paths(x, y, paths):
    best = 99.
    for path in paths:
        for a, b in zip(path, path[1:]):
            best = min(best, seg_dist((x, y), a, b))
    return best


def separated(x, y, r, objects, margin):
    for o in objects:
        if o.get('width') and o.get('depth'):
            dx = max(0, abs(x - o['x']) - o['width'] / 2)
            dy = max(0, abs(y - o['y']) - o['depth'] / 2)
            if math.hypot(dx, dy) <= r + margin:
                return False
        elif math.hypot(x - o['x'], y - o['y']) <= r + o.get('r', 0) + margin:
            return False
    return True


def fill_zone(z, view, geom, off, rng):
    """Scenery, lava rivers and spawns for the part of the outline the old square does not cover."""
    style = FILL[z]
    n, S0 = geom['size'], view['_old_size']
    floor = geom['floor']
    ox, oy = off
    core = np.zeros((n, n), dtype=bool)
    core[oy:oy + S0, ox:ox + S0] = True
    free = erode(floor, 2) & ~dilate(core, 0)
    city = view['city']
    cell_area = int(free.sum())
    old_free = S0 * S0 - (city['x1'] - city['x0']) * (city['y1'] - city['y0'])
    old_objects = [o for o in view['objects'] if o.get('layout') != TAG]
    kinds = style['decor']
    count = {k: sum(1 for o in old_objects if o['kind'] == k) for k in kinds}
    radius = {k: next(o['r'] for o in old_objects if o['kind'] == k) for k in kinds}
    paths = view.get('paths', [])
    existing = list(view['objects'])
    adds = []
    if style.get('rivers'):
        import generate_crags as gc
        lo, hi = ox, ox + S0
        inner = erode(floor, 1)
        for river in gc.RIVERS:
            fords = [river[3] + ox, ox - 52, ox + S0 + 52]
            xs = np.arange(0, n, 1.3) + .4
            for x in xs:
                if lo <= x - .0 < hi:
                    continue
                yy = gc.river_y(river, x - ox) + oy + rng.uniform(-.3, .3)
                if any(abs(x - f) < gc.FORD for f in fords):
                    continue
                if not (1.5 < yy < n - 1.5 and 0 <= int(x) < n and inner[int(yy), int(x)]):
                    continue
                adds.append({'kind': 'lava', 'x': round(float(x), 2), 'y': round(float(yy), 2), 'r': round(rng.uniform(1.25, 1.5), 2),
                             'v': rng.randrange(4), 'layout': TAG})
        existing = existing + adds
    spawns_old = [s for s in view['slimes'] if not s['kind'].startswith(ELITE_OR_SCRIPTED) and s['kind'] not in style.get('elites', ())]
    plaza = city['plaza']
    for k in kinds:
        want = round(count[k] * cell_area / old_free)
        placed = 0
        free_pts = np.argwhere(free)
        for _ in range(want * 400):
            if placed == want:
                break
            j, i = free_pts[rng.randrange(len(free_pts))]
            x, y = round(i + rng.random(), 2), round(j + rng.random(), 2)
            if dist_to_paths(x, y, paths) < (2.4 if k == 'tree' else 1.8):
                continue
            if any(math.hypot(x - s['x'], y - s['y']) < 3.2 + radius[k] for s in view['slimes']):
                continue
            if any(math.hypot(x - p['x'], y - p['y']) < 6 for p in view['portals']):
                continue
            if not separated(x, y, radius[k], existing + adds, .65):
                continue
            adds.append({'kind': k, 'x': x, 'y': y, 'r': radius[k], 'v': rng.randrange(4), 'layout': TAG})
            placed += 1
    # spawns: old density, kind picked from the old spawn whose distance feature is closest
    def feature(x, y):
        if style['spawn_feature'] == 'y':
            return min(max(y - oy, 0), S0)
        return math.hypot(x - plaza['x'], y - plaza['y'])
    ranked = sorted((feature(s['x'], s['y']), s['kind']) for s in spawns_old)
    want = round(len(spawns_old) * cell_area / old_free)
    sp = []
    pts = np.argwhere(erode(floor, 4) & ~core)
    solid = view['objects'] + adds
    for _ in range(want * 400):
        if len(sp) == want:
            break
        j, i = pts[rng.randrange(len(pts))]
        x, y = round(i + rng.random(), 2), round(j + rng.random(), 2)
        if any(math.hypot(x - t['x'], y - t['y']) < style['spawn_sep'] for t in view['slimes'] + sp):
            continue
        if any(math.hypot(x - p['x'], y - p['y']) < 12 for p in view['portals']):
            continue
        if not separated(x, y, .8, solid, 1.3):
            continue
        f = feature(x, y)
        near = sorted(ranked, key=lambda t: abs(t[0] - f))[:6]
        sp.append({'x': x, 'y': y, 'kind': near[rng.randrange(len(near))][1], 'layout': TAG})
    view['objects'].extend(adds)
    view['slimes'].extend(sp)
    return len(adds), len(sp)


# ---- portals on the shared chains (reuses compact_atlas's reachability and clearance tests) ---------------------------
def chain_endpoint(ca, z, other, prev, fixed):
    """The crossing sits just inside the shared border chain: trigger point, arrival six tiles further in, outward axis."""
    n = z['size']
    chains = [e['points'] for e in z['shape']['edges'] if e['kind'] == 'shared' and e['other'] == other]
    assert chains, f"{z['name']}: no shared border with zone {other}"
    chain = max(chains, key=lambda c: sum(math.dist(a, b) for a, b in zip(c, c[1:])))
    pts = []
    for a, b in zip(chain, chain[1:]):
        steps = max(1, int(math.dist(a, b)))
        pts += [(a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps) for i in range(steps + 1)]
    px = np.array(pts)
    mid = pts[len(pts) // 2]
    cells = np.array(sorted(prev))
    xs, ys = cells % n + .5, cells // n + .5
    d2 = (xs[:, None] - px[None, :, 0]) ** 2 + (ys[:, None] - px[None, :, 1]) ** 2
    near, dist = d2.argmin(axis=1), np.sqrt(d2.min(axis=1))
    candidates = []
    for k in np.nonzero((dist >= 5) & (dist <= 14))[0]:
        p = (float(xs[k]), float(ys[k]))
        q = pts[int(near[k])]
        vx, vy = p[0] - q[0], p[1] - q[1]
        ln = math.hypot(vx, vy) or 1
        a = (p[0] + vx / ln * 6, p[1] + vy / ln * 6)
        if int(a[1]) * n + int(a[0]) not in prev:
            continue
        if any(math.hypot(c[0] - s['x'], c[1] - s['y']) < 8.5 for c in (p, a) for s in z['slimes']):
            continue
        if any(math.hypot(c[0] - s['x'], c[1] - s['y']) < 9 for c in (p, a) for s in fixed):
            continue
        if any(math.hypot(c[0] - s['x'], c[1] - s['y']) < 3 for c in (p, a) for s in z.get('npcs', [])):
            continue
        candidates.append((float(dist[k]) * 2 + math.dist(p, mid) * .12, p, a, (q[0] - p[0], q[1] - p[1])))
    for _, p, a, out in sorted(candidates):
        if ca.clear(z, p, a):
            return p, a, ca.direction((0, 0), out)
    raise SystemExit(f"{z['name']}: no safe reachable gate toward zone {other}")


def make_seams(zones, shifted):
    """Two shaped zones at one tile scale share a border you can cross anywhere: B is A shifted by a constant."""
    seams = {}
    for i in shifted:
        for j in shifted:
            if i == j:
                continue
            a, b = zones[i]['shape'], zones[j]['shape']
            runs = [e for e in a['edges'] if e['kind'] == 'shared' and e['other'] == j]
            if not runs or abs(a['k'] - b['k']) > 1e-9:
                continue
            run = max(runs, key=lambda e: len(e['points']))
            shift = [a['T'][0] - b['T'][0], a['T'][1] - b['T'][1]]   # whole tiles: B's cell = A's cell + shift
            # the same border, seen from the other side, must be this line shifted
            other = [e for e in b['edges'] if e['kind'] == 'shared' and e['other'] == i]
            mine = np.array(run['points'])
            theirs = np.array(max(other, key=lambda e: len(e['points']))['points']) - np.array(shift)
            gap = max(min(np.linalg.norm(theirs - q, axis=1)) for q in mine)
            assert gap < 0.6, f'zones {i}/{j}: border does not match across the seam ({gap:.2f} tiles)'
            # which side of the polyline the neighbour lies: test a point 2 tiles off the middle of the longest segment
            k = max(range(len(run['points']) - 1), key=lambda m: math.dist(run['points'][m], run['points'][m + 1]))
            (x1, y1), (x2, y2) = run['points'][k], run['points'][k + 1]
            ln = math.hypot(x2 - x1, y2 - y1)
            nx, ny = -(y2 - y1) / ln, (x2 - x1) / ln
            rows = zones[i]['shapeFloor']
            mx, my = (x1 + x2) / 2 + nx * 2, (y1 + y2) / 2 + ny * 2
            side = 1 if rows[int(my)][int(mx)] != '#' else -1
            seams[i, j] = dict(points=[tuple(q) for q in run['points']], shift=shift, side=side)
    return seams


def place_portals(world, shifted):
    """Atlas crossings of shaped zones move onto the real shared chains; neighbours' arrivals follow."""
    import compact_atlas as ca
    zones = [world] + world['zones']
    landing = {}
    seams = make_seams(zones, shifted)
    for i in sorted(shifted):
        z = zones[i]
        for path in z.get('atlasPaths', []):
            if path in z['paths']:
                z['paths'].remove(path)
        z['atlasPaths'] = []
        prev = ca.connected(z)
        links = [p for p in z['portals'] if p['to'] in ca.OUTDOORS and p['to'] in zones[i]['shape'].get('neighbours', []) and (i, p['to']) not in seams]
        fixed = [p for p in z['portals'] if p not in links]
        for p in sorted(links, key=lambda p: p['to']):
            point, arrival, side = chain_endpoint(ca, z, p['to'], prev, fixed)
            landing[i, p['to']] = (point, arrival, side)
            fixed.append(dict(x=point[0], y=point[1]))
            fixed.append(dict(x=arrival[0], y=arrival[1]))
    for (i, j), (point, arrival, side) in landing.items():
        p = next(q for q in zones[i]['portals'] if q['to'] == j)
        p.update(x=point[0], y=point[1], walk=list(side))
        if (j, i) in landing:
            p.update(tx=landing[j, i][1][0], ty=landing[j, i][1][1])
        back = next((q for q in zones[j]['portals'] if q['to'] == i), None)
        if back is not None and j not in shifted:
            back.update(tx=arrival[0], ty=arrival[1])
    for (i, j), seam in seams.items():
        z = zones[i]
        old = next((q for q in z['portals'] if q['to'] == j), None)
        pts = seam['points']
        mid = pts[len(pts) // 2]
        portal = dict(id=old['id'] if old else f'seam_{i}_{j}', name=zones[j]['name'], x=mid[0], y=mid[1], r=1.1, to=j, tx=mid[0] + seam['shift'][0],
                      ty=mid[1] + seam['shift'][1], seam=dict(points=[[round(a, 2), round(b, 2)] for a, b in pts], shift=seam['shift'], side=seam['side']))
        if old:
            z['portals'][z['portals'].index(old)] = portal
        else:
            z['portals'].append(portal)
    for i in sorted(shifted):
        z = zones[i]
        for p in z['portals']:
            if (i, p['to']) not in landing:
                continue
            prev = ca.connected(z, [q for q in z['portals'] if q is not p])
            assert int(p['y']) * z['size'] + int(p['x']) in prev, f"{i}: {p['id']} cut off by another crossing"
            entrance = next((e for e in z.get('cityEntrances', []) if e.get('portal') == p['id']), None)
            path = entrance['points'] if entrance else ca.approach(z, prev, (p['x'], p['y']))
            if path not in z['paths']:
                z['paths'].append(path)
                z['atlasPaths'].append(path)
        ca.exit_routes(z)
    ca.sync_travel_links(zones)


# ---- unshape / apply ---------------------------------------------------------------------------------------------------
def unshape(world, cfg):
    offsets = {}
    for z in cfg['zones']:
        zone = zone_of(world, z)
        side = SIDE / f'preshape-{z:02d}.txt'
        if 'shape' not in zone:
            continue
        offsets[z] = zone['shape']['offset']
        set_view(world, z, json.loads(side.read_text()))
    shift_incoming(world, {z: o for z, o in offsets.items()}, -1)
    return offsets


def apply(world, cfg):
    atlas = Atlas()
    SIDE.mkdir(exist_ok=True)
    shifted = {}
    olds = {z: get_view(world, z) for z in cfg['zones']}
    geoms = {z: shape_geometry(cfg, atlas, z, olds[z]) for z in cfg['zones']}
    for z in cfg['zones']:
        zone = zone_of(world, z)
        assert 'shape' not in zone, f'zone {z} is already shaped: run unshape first'
        old = olds[z]
        (SIDE / f'preshape-{z:02d}.txt').write_text(json.dumps(old, indent=1, ensure_ascii=False) + '\n')
        geom = geoms[z]
        ox, oy = choose_offset(geom, old, z, atlas, world)
        view = copy.deepcopy(old)
        S0 = view['size']
        view['_old_size'] = S0
        shift_view(view, ox, oy)
        rng = random.Random(20261105 + z)
        added = fill_zone(z, view, geom, (ox, oy), rng)
        del view['_old_size']
        # Land runs SEAM_MARGIN tiles past a seam border so a walker can step across the line (the server then moves it).
        margin = np.zeros_like(geom['floor'])
        n = geom['size']
        ys, xs = np.mgrid[0:n, 0:n]
        for j in cfg['zones']:
            if j != z and abs(geoms[j]['scale'] - geom['scale']) < 1e-9:
                for run in geom['runs']:
                    if run['kind'] == 'shared' and run['other'] == j:
                        for a, b in zip(run['points'], run['points'][1:]):
                            dx, dy = b[0] - a[0], b[1] - a[1]
                            t = np.clip(((xs + .5 - a[0]) * dx + (ys + .5 - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
                            margin |= np.hypot(xs + .5 - a[0] - t * dx, ys + .5 - a[1] - t * dy) <= SEAM_MARGIN
        margin &= ~geom['floor']
        voids = void_pieces(geom['floor'] | margin)
        view['objects'] = [o for o in view['objects'] if o['kind'] != 'void'] + voids
        view['size'] = geom['size']
        view['shape'] = dict(rule=cfg['rule'], k=round(geom['scale'], 4), offset=[ox, oy], core=S0, bbox=geom['bbox'], T=geom['T'],
                             outline=geom['outline'], edges=geom['runs'], neighbours=sorted(atlas.neighbours[z]))
        view['shapeFloor'] = floor_rows(geom['floor'])
        view['shapeEdge'] = edge_rows(geom, sorted(atlas.neighbours[z]))
        check(z, view, geom)
        set_view(world, z, view)
        shifted[z] = (ox, oy)
        print(f"zone {z}: {S0}x{S0} -> {geom['size']}x{geom['size']} (bbox {geom['bbox'][0]}x{geom['bbox'][1]}, k {geom['scale']:.3f}), "
              f"core at ({ox},{oy}), +{added[0]} objects, +{added[1]} spawns, {len(voids)} void pieces")
    shift_incoming(world, shifted, 1)
    place_portals(world, shifted)
    return shifted


def check(z, view, geom):
    floor = geom['floor']
    n = geom['size']

    def ok(x, y):
        return 0 <= int(x) < n and 0 <= int(y) < n and floor[int(y), int(x)]
    bad = []
    for key in ('slimes', 'npcs', 'places', 'crosses'):
        bad += [(key, o['x'], o['y']) for o in view.get(key, []) if not ok(o['x'], o['y'])]
    assert ok(view['spawn']['x'], view['spawn']['y']), f'zone {z}: spawn outside the outline'
    assert not bad, f'zone {z}: content outside the outline: {bad[:5]}'
    c = view['city']
    assert all(ok(x, y) for x in (c['x0'], c['x1']) for y in (c['y0'], c['y1'])), f'zone {z}: city outside the outline'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['unshape', 'apply'])
    args = ap.parse_args()
    cfg = config()
    raw = MAP.read_text()
    world = json.loads(raw)
    assert json.dumps(world, indent=2, ensure_ascii=False) + '\n' == raw, 'map.txt must keep its canonical layout'
    if args.command == 'unshape':
        done = unshape(world, cfg)
        print(f'unshaped zones {sorted(done)}')
    else:
        apply(world, cfg)
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
