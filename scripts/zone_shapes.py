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
    # Gloamfen is a chain of lanes: ridges (thicket walls) with one gap each, so the ridges run on to the outline and the
    # filler spawns follow the lane they are in. Hydras live on the island only; Hollow Rider is the Halloween spawn.
    3: dict(spawn_sep=7.0, spawn_feature='lane', decor=('tree', 'bush', 'rock', 'spire'), ridges=True, lanes=True,
            elites=('gloomroot', 'hollow_rider'), no_fill=('hydra',)),
    # Rimeveil is a spiral of ice rings around the summit: difficulty runs by ring, so the land outside the rings takes the outermost
    # ring's kinds (feature = distance from the summit, not from the camp). The seasonal bosses sleep at the ritual clearing.
    # Wyrdwood is a triangle (apex north) that the old square cannot sit inside at k = 1.0: the old layout is warped into it, then the authored design replaces it.
    6: dict(spawn_sep=7.0, spawn_feature='city_distance', decor=('tree', 'bush', 'crag', 'pine', 'rock'), warp=True, elites=('oakhorn', 'hrungnir', 'ember_firelord')),
    2: dict(spawn_sep=7.0, spawn_feature='summit', summit=(64, 64), decor=('tree', 'rock', 'bush', 'spire'),
            elites=('grinch', 'bloomwarden', 'birchcrown', 'briarheart', 'starrocketeer')),
}


def config():
    return json.loads(CONFIG.read_text())


def gate_only_zones():
    """Zones whose every crossing stays a portal (never a seam, never a margin of land past the border): Bifrost Reach floats over the
    storm and is reached by updrafts only (owner, 2026-11-07: "keep the portals/updrafts since this place should be inaccessible without them")."""
    return set(config().get('gateOnly', []))


def design_only_zones():
    """Zones that keep their outline floor but take no filler: the old layout is moved as a block and the zone's own design
    (scripts/<zone>_design.py) replaces everything, placing its own gates (Rán's Deep: owner, 2026-11-07)."""
    return set(config().get('designOnly', []))


def rebuild_zones():
    """Zones whose old layout is NOT moved into the new frame (it cannot fit): the view is emptied and the zone's design rebuilds it from
    world/zone-shapes/preshape-<zone>.txt (Nacrehold, owner 2026-11-07)."""
    return set(config().get('rebuild', []))


def seam_allowed(i, j):
    """`seamWith` {zone: [neighbours]}: a zone listed there may seam ONLY with those neighbours (the Deep: only Nacrehold, owner 2026-11-07)."""
    rule = config().get('seamWith', {})
    return all(str(a) not in rule or b in rule[str(a)] for a, b in ((i, j), (j, i)))


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
    if z in design_only_zones():        # a design-only zone is authored on its outline at the one scale (a seam needs equal scales): no area floor, no city fit
        return s
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
    ritual = view.get('halloweenRitual')
    if ritual:
        shift_xy(ritual, dx, dy)
        ritual['lantern'] = [ritual['lantern'][0] + dx, ritual['lantern'][1] + dy]
    for key in ('christmasRitual', 'easterRitual', 'solsticeRitual', 'valentineRitual'):
        if key in view:
            shift_xy(view[key], dx, dy)
            view[key]['tree'] = [view[key]['tree'][0] + dx, view[key]['tree'][1] + dy]
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



# ---- warp: the whole old layout is bent into the outline (zones whose old square cannot sit inside it) -----------------
WARP_MIN_TOP, WARP_MIN_BOTTOM = 90, 56


class Warp:
    """Row-wise area-preserving map of the old square [0,S0]^2 onto the outline rows where it is wide enough.

    A row keeps its order and its ridges stay ridges (a ridge along a row stays along a row), so lanes, gaps, the lake and
    the town keep their topology; only distances stretch. Rows narrower than WARP_MIN_BOTTOM (the tip) and the spike
    above the wide part are left to the filler."""
    def __init__(self, geom, S0):
        n = geom['size']
        inner = erode(geom['floor'], 1)
        L = np.full(n, np.nan)
        R = np.full(n, np.nan)
        for y in range(n):
            xs = np.nonzero(inner[y])[0]
            if len(xs):
                L[y], R[y] = xs[0], xs[-1] + 1
        W = 5
        Ls = np.full(n, np.nan)
        Rs = np.full(n, np.nan)
        for y in range(n):
            lo, hi = max(0, y - W), min(n, y + W + 1)
            if not np.isnan(L[lo:hi]).any():
                Ls[y], Rs[y] = L[lo:hi].max(), R[lo:hi].min()
        w = Rs - Ls
        y0 = next(y for y in range(n) if w[y] >= WARP_MIN_TOP)
        y1 = y0
        while y1 + 1 < n and w[y1 + 1] >= WARP_MIN_BOTTOM:
            y1 += 1
        self.S0, self.y0, self.y1 = S0, y0, y1 + 1
        self.rows = np.arange(y0, y1 + 1)
        cum = np.concatenate([[0], np.cumsum(w[y0:y1 + 1])])
        self.v_edges = cum / cum[-1] * S0
        self.y_edges = np.arange(y0, y1 + 2, dtype=float)
        self.Ls, self.Rs = Ls, Rs
        centres = np.arange(y0, y1 + 1) + .5
        self.centres = centres
        self.Lc, self.Rc = Ls[y0:y1 + 1], Rs[y0:y1 + 1]
        self.n = n

    def __call__(self, x, y):
        Y = float(np.interp(min(max(y, 0), self.S0), self.v_edges, self.y_edges))
        lo = float(np.interp(Y, self.centres, self.Lc)) + .5
        hi = float(np.interp(Y, self.centres, self.Rc)) - .5
        return round(lo + min(max(x, 0), self.S0) / self.S0 * (hi - lo), 2), round(Y, 2)

    def region(self):
        m = np.zeros((self.n, self.n), dtype=bool)
        for y in range(self.y0, self.y1):
            m[y, int(math.ceil(self.Ls[y])):int(self.Rs[y])] = True
        return m


def dense(path, step=3.0):
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [[a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k] for i in range(1, k + 1)]
    return out


def warp_view(view, F):
    """Same job as shift_view, with the warp as the map."""
    def mv(d, kx='x', ky='y'):
        if kx in d and ky in d:
            d[kx], d[ky] = F(d[kx], d[ky])
    mv(view['spawn'])
    for key in ('objects', 'slimes', 'npcs', 'places', 'crosses'):
        for o in view.get(key, []):
            mv(o)
    for c in ([view['city']] if view.get('city') else []) + list(view.get('camps', [])):
        corners = [F(x, y) for x in (c['x0'], c['x1']) for y in (c['y0'], c['y1'])]
        c['x0'], c['x1'] = min(q[0] for q in corners), max(q[0] for q in corners)
        c['y0'], c['y1'] = min(q[1] for q in corners), max(q[1] for q in corners)
        for k in ('plaza', 'entry'):
            if k in c:
                mv(c[k])
    for p in view.get('portals', []):
        mv(p)
    for key in ('paths', 'atlasPaths'):
        view[key] = [[list(F(a, b)) for a, b in dense(path)] for path in view.get(key, [])]
    for e in view.get('exitRoutes', []):
        e['points'] = [list(F(a, b)) for a, b in dense(e['points'])]
    ritual = view.get('halloweenRitual')
    if ritual:
        mv(ritual)
        ritual['lantern'] = list(F(*ritual['lantern']))
    assert not view.get('cityEntrances') and not view.get('roads'), 'warp: cityEntrances/roads are not mapped'


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


def gloam_gaps():
    import generate_gloamfen as gg
    return [(gx, gy, gg.GAP_HALF + 1.2) for gx, gy in gg.GAPS]


def lane_labels(objects, floor, n, gaps):
    """Component label (0 = blocked) of every cell with the ridge gaps plugged: the lanes of a ridge-and-gap zone."""
    from scipy import ndimage
    blocked = ~floor
    ys, xs = np.mgrid[0:n, 0:n]
    cx, cy = xs + .5, ys + .5
    for o in objects:
        if o['kind'] not in ('thicket', 'water', 'void'):
            continue
        if o['kind'] == 'void':
            x0, x1 = o['x'] - o['width'] / 2, o['x'] + o['width'] / 2
            y0, y1 = o['y'] - o['depth'] / 2, o['y'] + o['depth'] / 2
            blocked[max(0, int(y0)):min(n, int(math.ceil(y1))), max(0, int(x0)):min(n, int(math.ceil(x1)))] = True
            continue
        r = o['r'] + .5
        j0, j1 = max(0, int(o['y'] - r)), min(n, int(o['y'] + r) + 1)
        i0, i1 = max(0, int(o['x'] - r)), min(n, int(o['x'] + r) + 1)
        blocked[j0:j1, i0:i1] |= (cx[j0:j1, i0:i1] - o['x']) ** 2 + (cy[j0:j1, i0:i1] - o['y']) ** 2 <= r * r
    for gx, gy, gr in gaps:
        blocked |= (cx - gx) ** 2 + (cy - gy) ** 2 <= gr * gr
    labels, _ = ndimage.label(~blocked)
    return labels


def fill_zone(z, view, geom, off, rng, core=None, F=None):
    """Scenery, lava rivers and spawns for the part of the outline the old square does not cover."""
    style = FILL[z]
    n, S0 = geom['size'], view['_old_size']
    floor = geom['floor']
    ox, oy = off
    if core is None:
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
    if style.get('ridges'):
        import generate_gloamfen as gg
        inner = erode(floor, 1)
        if F is None:
            runs = [[(0.0, gg.R1_Y), (-float(n), gg.R1_Y)], [(float(S0), gg.R1_Y), (S0 + float(n), gg.R1_Y)],
                    [(0.0, gg.R2_Y), (-float(n), gg.R2_Y)], [(92.0, float(S0)), (92.0, S0 + float(n))]]
            runs = [[(x + ox, y + oy) for x, y in run] for run in runs]
        else:
            # a warped ridge ends at the conservative outline row extent: run each end on, straight, to the void
            runs = []
            for end, inward in (((0.0, gg.R1_Y), (8.0, gg.R1_Y)), ((float(S0), gg.R1_Y), (S0 - 8.0, gg.R1_Y)),
                                ((0.0, gg.R2_Y), (8.0, gg.R2_Y)), ((92.0, float(S0)), (92.0, S0 - 8.0))):
                P, Q = F(*end), F(*inward)
                d = (P[0] - Q[0], P[1] - Q[1])
                ln = math.hypot(*d)
                runs.append([P, (P[0] + d[0] / ln * n, P[1] + d[1] / ln * n)])
        thickets = [o for o in view['objects'] if o['kind'] == 'thicket']
        for run in runs:
            for o in gg.ridge(run, rng):
                i, j = int(o['x']), int(o['y'])
                if 0 <= i < n and 0 <= j < n and inner[j, i] and not (F is None and core[j, i]):
                    if any(math.hypot(o['x'] - t['x'], o['y'] - t['y']) < 1.0 for t in thickets):
                        continue
                    o['layout'] = TAG
                    adds.append(o)
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
        if style['spawn_feature'] == 'summit':
            return math.hypot(x - style['summit'][0] - ox, y - style['summit'][1] - oy)
        return math.hypot(x - plaza['x'], y - plaza['y'])
    lane_of = None
    if style.get('lanes'):
        spawns_old = [s for s in spawns_old if s['kind'] not in style.get('no_fill', ())]
        lane_of = lane_labels(view['objects'] + adds, floor, n, [(*(F(g[0], g[1]) if F else (g[0] + ox, g[1] + oy)), g[2]) for g in gloam_gaps()])
        lane_spawns = defaultdict(list)
        for s in spawns_old:
            lane_spawns[lane_of[int(s['y']), int(s['x'])]].append(s)
        lane_spawns.pop(0, None)
        laned = np.isin(lane_of, list(lane_spawns))
        old_cells = int((laned & core).sum())
        new_cells = int((laned & ~core & erode(floor, 4)).sum())
        want = round(len(spawns_old) * new_cells / max(old_cells, 1))
        ranked = []
    else:
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
        if lane_of is not None:
            here = lane_spawns.get(lane_of[int(y), int(x)])
            if not here:
                continue   # the town strip and any pocket without an old spawn stay empty
            near = sorted(here, key=lambda t: math.hypot(t['x'] - x, t['y'] - y))[:6]
            sp.append({'x': x, 'y': y, 'kind': near[rng.randrange(len(near))]['kind'], 'layout': TAG})
            continue
        f = feature(x, y)
        near = sorted(ranked, key=lambda t: abs(t[0] - f))[:6]
        sp.append({'x': x, 'y': y, 'kind': near[rng.randrange(len(near))][1], 'layout': TAG})
    view['objects'].extend(adds)
    view['slimes'].extend(sp)
    if lane_of is not None:
        seen = {}
        for k in ('toad', 'croc', 'knight'):
            ids = {int(lane_of[int(t['y']), int(t['x'])]) for t in view['slimes'] if t['kind'] == k} - {0}
            assert len(ids) == 1, f'zone {z}: the {k} lane is split or lost across components {ids}'
            seen[k] = ids.pop()
        assert len(set(seen.values())) == 3, f'zone {z}: lanes are connected around the ridges: {seen}'
    return len(adds), len(sp)


# ---- portals on the shared chains (reuses compact_atlas's reachability and clearance tests) ---------------------------
def chain_endpoint(ca, z, other, prev, fixed, vault=False):
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
    lo, hi = (2., 3.5) if vault else (5., 14.)
    for k in np.nonzero((dist >= lo) & (dist <= hi))[0]:
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
        score = float(dist[k]) * 2 + math.dist(p, mid) * .12
        if vault:   # the vault is an axis-aligned arch: put it where the wall runs straight along an axis
            i0, i1 = max(0, int(near[k]) - 8), min(len(pts) - 1, int(near[k]) + 8)
            tx, ty = abs(pts[i1][0] - pts[i0][0]), abs(pts[i1][1] - pts[i0][1])
            score += min(tx, ty) / max(tx, ty, 1e-9) * 60
        candidates.append((score, p, a, (q[0] - p[0], q[1] - p[1])))
    for _, p, a, out in sorted(candidates):
        if ca.clear(z, p, a):
            return p, a, ca.direction((0, 0), out)
    raise SystemExit(f"{z['name']}: no safe reachable gate toward zone {other}")


def make_seams(zones, shifted):
    """Two shaped zones at one tile scale share a border you can cross anywhere: B is A shifted by a constant."""
    seams = {}
    gate_only = gate_only_zones()
    for i in shifted:
        for j in shifted:
            if i == j or i in gate_only or j in gate_only or not seam_allowed(i, j):
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


def fitted_vault(zones, i, lm, fit, axis):
    """`wallFit` (world/zone-shapes.txt): the wall's ends sit on the ends of its border run, so a shaped neighbour's seam meets the wall and
    never runs through it. `corner` is the end of the run that takes the city's own corner, which fixes where along the wall the vault
    stands; `line` (optional) is the end the straight wall line passes through. Returns (along, across of the wall line, across of the old border) at the vault."""
    z, city = zones[i], zones[lm]
    run = max((e['points'] for e in z['shape']['edges'] if e['kind'] == 'shared' and e['other'] == lm),
              key=lambda r: sum(math.dist(a, b) for a, b in zip(r, r[1:])))
    ai = 0 if axis == 'x' else 1
    bi = 1 - ai
    ends = {'lo': min(run, key=lambda q: q[bi]), 'hi': max(run, key=lambda q: q[bi])}
    assert fit['corner'] == 'lo', 'wallFit: only the low corner is used so far'
    back = next(p for p in city['portals'] if p['to'] == i)
    carch = next(a for a in city['exitArches'] if a['portal'] == back['id'])
    cb = city['city']
    along = ends['lo'][bi] + (carch['x'], carch['y'])[bi] - (cb['x0'], cb['y0'])[bi]
    if 'at' in fit:         # Skaldholm rebuild: the vault stands where the city's main street meets the wall (an atlas coordinate along the wall)
        along = fit['at'] - z['shape']['T'][bi]
    for a, b in zip(run, run[1:]):
        if (a[bi] - along) * (b[bi] - along) <= 0 and a[bi] != b[bi]:
            border = a[ai] + (b[ai] - a[ai]) * (along - a[bi]) / (b[bi] - a[bi])
            return along, fit['c'] if 'c' in fit else ends[fit['line']][ai] if 'line' in fit else border, border
    raise SystemExit(f'zone {i}: the fitted vault lies past the end of its wall')


def place_portals(world, shifted, landmarks=(), axes=None, fits=None):
    """Atlas crossings of shaped zones move onto the real shared chains; neighbours' arrivals follow."""
    import compact_atlas as ca
    zones = [world] + world['zones']
    landing = {}
    seams = make_seams(zones, shifted)
    gate_only = gate_only_zones() | design_only_zones()
    for i in sorted(shifted):
        if i in gate_only:      # a sky zone keeps its own gates: its design (bifrost_design.py) places every updraft (the Deep's design too)
            continue
        z = zones[i]
        for path in z.get('atlasPaths', []):
            if path in z['paths']:
                z['paths'].remove(path)
        z['atlasPaths'] = []
        prev = ca.connected(z)
        links = [p for p in z['portals'] if p['to'] in ca.OUTDOORS and p['to'] in zones[i]['shape'].get('neighbours', []) and (i, p['to']) not in seams]
        fixed = [p for p in z['portals'] if p not in links]
        for p in sorted(links, key=lambda p: p['to']):
            if p['to'] in landmarks and str(i) in (fits or {}):
                axis = axes[str(i)]
                along, across, border = fitted_vault(zones, i, p['to'], fits[str(i)], axis)
                back = next(q for q in zones[p['to']]['portals'] if q['to'] == i)
                wx, wy = -back['walk'][0], -back['walk'][1]                     # outward: into the city
                out = wx if axis == 'x' else wy
                inner = min((across, border), key=lambda v: v * out)            # land today: the wall's fill does not exist yet
                line = (inner, along) if axis == 'x' else (along, inner)
                point = (line[0] - wx * 3, line[1] - wy * 3)
                arrival = (point[0] - wx * 6, point[1] - wy * 6)
                side = [wx, wy]
                near = lambda o, r: seg_dist((o['x'], o['y']), point, arrival) < r
                z['slimes'] = [s for s in z['slimes'] if s.get('layout') != TAG or not near(s, 8.5)]
                z['objects'] = [o for o in z['objects'] if o['kind'] not in ('tree', 'bush', 'rock', 'spire') or not near(o, 2.5 + o.get('r', 0))]
                assert ca.clear(z, point, arrival), f"zone {i}: the fitted vault at {point} is blocked"
            else:
                point, arrival, side = chain_endpoint(ca, z, p['to'], prev, fixed, vault=p['to'] in landmarks)
            landing[i, p['to']] = (point, arrival, side)
            fixed.append(dict(x=point[0], y=point[1]))
            fixed.append(dict(x=arrival[0], y=arrival[1]))
    for (i, j), (point, arrival, side) in landing.items():
        p = next(q for q in zones[i]['portals'] if q['to'] == j)
        p.update(x=point[0], y=point[1], walk=list(side))
        if (j, i) in landing:
            p.update(tx=landing[j, i][1][0], ty=landing[j, i][1][1])
        back = next((q for q in zones[j]['portals'] if q['to'] == i), None)
        if back is not None and (j not in shifted or j in gate_only):
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
        if i in gate_only:
            continue
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



# ---- landmark walls: a neighbour city drawn as a wall along the shared border, with a vault you walk through ---------------
WALL_STEP, WALL_IN, VAULT_HALF = 2.0, 1.6, 5.9
WALL_TOL = 2.5      # a city wall is straight: the border run is simplified to segments within this many tiles of it


def simplify_run(pts, tol):
    """Douglas-Peucker: the fewest straight segments that stay within `tol` tiles of the polyline (ends kept)."""
    pts = [tuple(p) for p in pts]
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    L = math.dist(a, b) or 1e-9
    dev = [abs((b[0] - a[0]) * (a[1] - q[1]) - (a[0] - q[0]) * (b[1] - a[1])) / L for q in pts[1:-1]]
    k = max(range(len(dev)), key=dev.__getitem__)
    if dev[k] <= tol:
        return [a, b]
    return simplify_run(pts[:k + 2], tol)[:-1] + simplify_run(pts[k + 1:], tol)


REGION_DEPTH, STRIP_DEPTH = 90., 4.


def _any_inside(mask, quad):
    """Does the convex-ish polygon `quad` contain a True cell centre of `mask`? (ray casting over the bounding box)"""
    n = mask.shape[0]
    xs = [q[0] for q in quad]; ys = [q[1] for q in quad]
    x0, x1 = max(0, int(min(xs))), min(n - 1, int(max(xs)) + 1)
    y0, y1 = max(0, int(min(ys))), min(n - 1, int(max(ys)) + 1)
    if x0 > x1 or y0 > y1:
        return False
    sub = mask[y0:y1 + 1, x0:x1 + 1]
    gy, gx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    px, py = gx + .5, gy + .5
    inside = np.zeros(sub.shape, dtype=bool)
    m = len(quad)
    for i in range(m):
        ax, ay = quad[i]; bx, by = quad[(i + 1) % m]
        if ay == by:
            continue
        cond = ((ay > py) != (by > py)) & (px < (bx - ax) * (py - ay) / (by - ay) + ax)
        inside ^= cond
    return bool((inside & sub).any())


def vault_regions(runs, land_probe, land=None):
    """Where each side of a landmark's wall owns the ground (the wall line is the straightened border, in this zone's frame):
    `city` = beyond the line, `land` = this zone's side, `strip` = the 4 tiles just past the line (the city's own wall stands there, and is
    replaced by ours). Each is a polygon [x, y, ...]; both frames use the same ones (docs/zone-shapes-pilot.md, "Vault seamlessness")."""
    out = []
    for r in runs:
        r = [tuple(q) for q in r]
        segn = []
        for a, b in zip(r, r[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1e-9
            nx, ny = -dy / ln, dx / ln
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            side = sum((1 if land_probe(mx + nx * d, my + ny * d) else 0) - (1 if land_probe(mx - nx * d, my - ny * d) else 0) for d in (3, 5, 8))
            segn.append((nx, ny) if side >= 0 else (-nx, -ny))              # inland normal
        vn = []
        for k in range(len(r)):
            ns = [segn[j] for j in (k - 1, k) if 0 <= j < len(segn)]
            sx, sy = sum(n[0] for n in ns), sum(n[1] for n in ns)
            ln = math.hypot(sx, sy) or 1e-9
            k_ = min(1.5, 1 / max(.66, ln / len(ns)))                       # keep the strip's width through a bend
            vn.append((sx / ln * k_, sy / ln * k_))
        # Past the two ends of the wall line the ground still has an owner: the city side runs on along the end tangents (as far as it
        # does not cover this zone's own land), so nothing beyond the run is left unowned (the Crags' arch stands at the end of its run).
        ext = [0., 0.]
        for end, (a_, b_) in enumerate(((r[1], r[0]), (r[-2], r[-1]))):
            tx, ty = b_[0] - a_[0], b_[1] - a_[1]
            ln = math.hypot(tx, ty) or 1e-9
            tx, ty = tx / ln, ty / ln
            for E in (90., 60., 40., 25., 12., 0.):
                far = (b_[0] + tx * E, b_[1] + ty * E)
                vn_ = vn[0] if end == 0 else vn[-1]
                quad = [b_, far, (far[0] - vn_[0] * REGION_DEPTH, far[1] - vn_[1] * REGION_DEPTH), (b_[0] - vn_[0] * REGION_DEPTH, b_[1] - vn_[1] * REGION_DEPTH)]
                if E == 0 or land is None or not _any_inside(land, quad):
                    ext[end] = E
                    break
        r2 = list(r); vn2 = list(vn)
        for end, E in enumerate(ext):
            if not E:
                continue
            a_, b_ = (r[1], r[0]) if end == 0 else (r[-2], r[-1])
            tx, ty = b_[0] - a_[0], b_[1] - a_[1]
            ln = math.hypot(tx, ty) or 1e-9
            q = (b_[0] + tx / ln * E, b_[1] + ty / ln * E)
            if end == 0:
                r2.insert(0, q); vn2.insert(0, vn[0])
            else:
                r2.append(q); vn2.append(vn[-1])
        r, vn = r2, vn2
        def band(d0, d1):               # polygon between the line offset by d0 and by d1 (positive = inland)
            return [round(c, 2) for q, n in zip(r, vn) for c in (q[0] + n[0] * d0, q[1] + n[1] * d0)] + \
                   [round(c, 2) for q, n in reversed(list(zip(r, vn))) for c in (q[0] + n[0] * d1, q[1] + n[1] * d1)]
        out.append(dict(city=band(0, -REGION_DEPTH), land=band(0, REGION_DEPTH), strip=band(0, -STRIP_DEPTH)))
    return out


def axis_wall(rows, run, axis, c, lim=None):
    """The wall line is the straight axis-aligned line `axis` = c (the city's own wall is straight): along the run's extent the floor is
    cut to it, and the land between it and the old border fills in. Returns (floor, lost)."""
    n = len(rows)
    old = np.array([[ch == '#' for ch in row] for row in rows])
    if axis == 'y':
        new, lost = axis_wall([''.join('#' if v else ' ' for v in col) for col in old.T], [(q[1], q[0]) for q in run], 'x', c, lim)
        return new.T, lost.T
    pts = [tuple(q) for q in run]
    y0, y1 = min(q[1] for q in pts), max(q[1] for q in pts)
    if lim:
        y0, y1 = max(y0, lim[0]), min(y1, lim[1])
    band = old[max(0, int(y0)):min(n, int(y1) + 1)]
    east, west = int(band[:, int(c) + 1:].sum()), int(band[:, :int(c)].sum())
    inland = 1 if east >= west else -1        # the land is on the side that holds more of it
    new = old.copy()
    for y in range(int(math.floor(y0)), int(math.ceil(y1)) + 1):
        if not 0 <= y < n:
            continue
        # where the old border crosses this row
        xs = [a[0] + (b[0] - a[0]) * ((y + .5) - a[1]) / (b[1] - a[1]) for a, b in zip(pts, pts[1:]) if (a[1] - (y + .5)) * (b[1] - (y + .5)) <= 0 and b[1] != a[1]]
        xb = xs[0] if xs else c
        for x in range(n):
            cx = x + .5
            if (cx - c) * inland < 0:
                new[y, x] = False                                   # beyond the wall line
            elif (cx - xb) * inland < 0:
                new[y, x] = True                                    # between the line and the old border: land now
    return new, old & ~new


def straighten(rows, runs_orig, runs_simp, tol):
    """Floor mask with the border along `runs_simp` (straight): cells on the city side of the line go, cells between the line and the
    old border fill in. Only the perpendicular band of each run is touched (nothing past a run's two ends). Returns (floor, lost)."""
    n = len(rows)
    old = np.array([[c == '#' for c in row] for row in rows])
    new = old.copy()
    ys, xs = np.mgrid[0:n, 0:n]
    cx, cy = xs + .5, ys + .5
    D = tol + 3
    # distance to the original chain: only cells close to the old border may fill in
    near_old = np.full((n, n), 1e9)
    for r in runs_orig:
        for a, b in zip(r, r[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = np.clip(((cx - a[0]) * dx + (cy - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
            near_old = np.minimum(near_old, np.hypot(cx - a[0] - t * dx, cy - a[1] - t * dy))
    for r in runs_simp:
        segs = list(zip(r, r[1:]))
        best = np.full((n, n), 1e9)
        sd = np.zeros((n, n))
        ok = np.zeros((n, n), dtype=bool)
        for si, (a, b) in enumerate(segs):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1e-9
            nx, ny = -dy / ln, dx / ln
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            def land(px, py):
                return 0 <= int(py) < n and 0 <= int(px) < n and old[int(py), int(px)]
            side = sum((1 if land(mx + nx * d, my + ny * d) else 0) - (1 if land(mx - nx * d, my - ny * d) else 0) for d in (3, 5, 8))
            if side < 0:
                nx, ny = -nx, -ny
            traw = ((cx - a[0]) * dx + (cy - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9)
            t = np.clip(traw, 0, 1)
            dist = np.hypot(cx - a[0] - t * dx, cy - a[1] - t * dy)
            sdist = (cx - a[0]) * nx + (cy - a[1]) * ny
            beyond = ((si == 0) & (traw < 0)) | ((si == len(segs) - 1) & (traw > 1))   # past a run's end: another border starts there
            better = (dist < best) & ~beyond & (dist <= D)
            best = np.where(better, dist, best)
            sd = np.where(better, sdist, sd)
            ok |= better
        inside = ok & (sd >= 0)
        new = np.where(ok, np.where(inside, old | (inside & (sd <= tol + 1) & (near_old <= tol + 1.5)), False), new)
    return new, old & ~new


def build_walls(world, shifted, landmarks, margins, cfg_axes=None, fits=None):
    """Skaldholm's wall (docs/zone-shapes-pilot.md): along every border a shaped zone has with a landmark city, ramparts and
    towers (the city's own art, real collision objects) with a vault at the gate you walk through to enter the city.

    The vault IS the city's own arch seen from this zone: the two share one doorway, so a crossing keeps your place relative to it
    (`Portal.vault` = the offset between the two frames, the arrival is `here + offset`): you walk under the vault, past the arch's
    centre, and you are under the city's arch, with the street ahead. A small pocket of land is added just beyond the wall to stand on."""
    import compact_atlas as ca
    zones = [world] + world['zones']
    for i in sorted(shifted):
        z = zones[i]
        for lm in landmarks:
            runs = [e['points'] for e in z['shape']['edges'] if e['kind'] == 'shared' and e['other'] == lm]
            gate = next((p for p in z['portals'] if p['to'] == lm and 'seam' not in p), None)
            if not runs or gate is None:
                continue
            n = z['size']
            city = zones[lm]
            back = next(p for p in city['portals'] if p['to'] == i)
            carch = next(a for a in city['exitArches'] if a['portal'] == back['id'])
            carch_ = [carch]
            simp = [simplify_run(r, WALL_TOL) for r in runs]
            orig_floor = np.array([[c == '#' for c in row] for row in z['shapeFloor']])
            axis = (cfg_axes or {}).get(str(i))
            if axis:       # one straight, axis-aligned wall along the city's own wall (carch is vertical for a vertical wall)
                assert (axis == 'x') == bool(carch_[0]['vertical']), f"zone {i}: the wall axis {axis} does not match the city arch"
                longest = max(runs, key=lambda r: sum(math.dist(a, b) for a, b in zip(r, r[1:])))
                gx_, gy_ = gate['x'], gate['y']
                feet_ = []
                for a, b in zip(longest, longest[1:]):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    t = max(0., min(1., ((gx_ - a[0]) * dx + (gy_ - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
                    feet_.append((a[0] + t * dx, a[1] + t * dy))
                qf = min(feet_, key=lambda p_: math.dist(p_, (gx_, gy_)))
                ai = 0 if axis == 'x' else 1            # the coordinate that is constant along the wall
                bi = 1 - ai
                if str(i) in (fits or {}):
                    along_, across_, _ = fitted_vault(zones, i, lm, fits[str(i)], axis)
                    qf = (across_, along_) if axis == 'x' else (along_, across_)
                c_ = round(qf[ai], 2)
                band_ = orig_floor if axis == 'x' else orig_floor.T
                rows_ = band_[max(0, int(min(q[bi] for q in longest))):int(max(q[bi] for q in longest)) + 1]
                inland = 1 if rows_[:, int(c_) + 1:].sum() >= rows_[:, :int(c_)].sum() else -1
                # the city's own corners in this frame: where its wall turns away, ours turns with it (and the land past the corner stays)
                cb = city['city']
                off = (carch['x'], carch['y'])[bi] - qf[bi]
                lo_c, hi_c = ((cb['y0'] - 1, cb['y1'] + 1) if axis == 'x' else (cb['x0'] - 1, cb['x1'] + 1))
                lo_c, hi_c = lo_c - off, hi_c - off
                def across_at(v):
                    for a_, b_ in zip(longest, longest[1:]):
                        if (a_[bi] - v) * (b_[bi] - v) <= 0 and a_[bi] != b_[bi]:
                            return a_[ai] + (b_[ai] - a_[ai]) * (v - a_[bi]) / (b_[bi] - a_[bi])
                    return None
                ends = sorted(longest, key=lambda q: q[bi])
                e_lo, e_hi = min(longest, key=lambda q: q[bi]), max(longest, key=lambda q: q[bi])
                pt = lambda across, along: (across, along) if axis == 'x' else (along, across)
                lo, hi = e_lo[bi], e_hi[bi]
                head, tail = [], []
                if inland * (e_lo[ai] - c_) < -3 and lo < lo_c + 1.2:
                    lo = lo_c + 1.2
                    head = [pt(across_at(lo), lo)]
                if inland * (e_hi[ai] - c_) < -3 and hi > hi_c - 1.2:
                    hi = hi_c - 1.2
                    tail = [pt(across_at(hi), hi)]
                lo, hi = round(lo, 2), round(hi, 2)
                simp = [head + [pt(c_, lo), pt(c_, hi)] + tail]
                floor_now, lost = axis_wall(z['shapeFloor'], longest, axis, c_, (lo, hi))
            else:
                floor_now, lost = straighten(z['shapeFloor'], runs, simp, WALL_TOL)
            assert not any(lost[int(o['y']), int(o['x'])] for k in ('npcs', 'places', 'crosses') for o in z.get(k, [])), f'zone {i}: a straight wall would cut off an NPC, place or cross'
            assert not lost[int(z['spawn']['y']), int(z['spawn']['x'])], f'zone {i}: a straight wall would cut off the spawn'
            c_ = z['city']
            assert not any(lost[int(y), int(x)] for x in (c_['x0'], c_['x1']) for y in (c_['y0'], c_['y1'])), f'zone {i}: a straight wall would cut the city'
            rows = floor_rows(floor_now)
            runs = simp
            on = lambda x, y: 0 <= int(y) < n and 0 <= int(x) < n and rows[int(y)][int(x)] == '#'
            wx, wy = gate['walk']
            assert [wx, wy] == [-back['walk'][0], -back['walk'][1]], f"zone {i}: the vault and the city's arch face different ways"
            hw = carch['halfWidth']
            # the arch on the wall line, 1.2 tiles inland of the border point nearest the gate, axis-aligned like the city's arch
            def foot(a, b, g):
                dx, dy = b[0] - a[0], b[1] - a[1]
                t = max(0., min(1., ((g[0] - a[0]) * dx + (g[1] - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
                return (a[0] + t * dx, a[1] + t * dy)
            feet = [foot(a, b, (gate['x'], gate['y'])) for r in runs for a, b in zip(r, r[1:])]
            q = min(feet, key=lambda c: math.dist(c, (gate['x'], gate['y'])))
            A = (round(q[0] - wx * 1.2, 2), round(q[1] - wy * 1.2, 2))
            arch = dict(x=A[0], y=A[1], vertical=carch['vertical'], halfWidth=hw, towers=carch['towers'], portal=gate['id'], name=zones[lm]['name'])
            adds, towers = [], []
            wall_in = 1.2 if axis else WALL_IN      # an axis wall stands exactly on the city's own wall (the arch is 1.2 inland of the line)
            px, py = -wy, wx                                   # across the opening
            if carch['towers']:                                # the vault's own towers, as in the city's wall: half width + 1.7 each side
                for sgn in (-1, 1):
                    towers.append((A[0] + px * sgn * (hw + 1.7), A[1] + py * sgn * (hw + 1.7)))
            flank = list(towers)
            if axis:
                # The wall IS the city's wall: its own pieces, copied into this frame (same art, same place, real collision), and generated
                # ramparts only where the city has no wall (past its corners).
                sx_, sy_ = carch['x'] - A[0], carch['y'] - A[1]
                def line_dist(x, y):
                    best = 1e9
                    for r in runs:
                        for a_, b_ in zip(r, r[1:]):
                            dx, dy = b_[0] - a_[0], b_[1] - a_[1]
                            t = max(0., min(1., ((x - a_[0]) * dx + (y - a_[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
                            best = min(best, math.hypot(x - a_[0] - t * dx, y - a_[1] - t * dy))
                    return best
                copies = [dict(o, x=round(o['x'] - sx_, 2), y=round(o['y'] - sy_, 2), layout=TAG) for o in city['objects']
                          if o['kind'] in ('rampart', 'tower') and line_dist(o['x'] - sx_, o['y'] - sy_) <= 2.2]
                adds.extend(o for o in copies if o['kind'] == 'rampart')
                ctow = [(o['x'], o['y']) for o in copies if o['kind'] == 'tower']
                towers = ctow + [t for t in towers if not any(math.dist(t, q_) < 2 for q_ in ctow)]
                covered = lambda x, y: any(abs(x - o['x']) <= o['width'] / 2 + .9 and abs(y - o['y']) <= o['depth'] / 2 + .9 for o in copies)
                for r in runs:
                    for a_, b_ in zip(r, r[1:]):
                        ln = math.dist(a_, b_) or 1e-9
                        tx, ty = (b_[0] - a_[0]) / ln, (b_[1] - a_[1]) / ln
                        mx, my = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
                        nx, ny = -ty, tx
                        if not on(mx + nx * 4, my + ny * 4):
                            nx, ny = -nx, -ny
                        run_len = 0.
                        for k in range(1, int(ln / WALL_STEP)):
                            cx, cy = a_[0] + tx * k * WALL_STEP + nx * wall_in, a_[1] + ty * k * WALL_STEP + ny * wall_in
                            run_len += WALL_STEP
                            lx, ly = a_[0] + tx * k * WALL_STEP, a_[1] + ty * k * WALL_STEP    # on the line itself: a leg along a seam has land on neither side
                            if math.dist((cx, cy), A) <= hw + 1.9 or any(math.dist(t, (cx, cy)) < 2.2 for t in towers) or covered(cx, cy) or covered(lx, ly):
                                continue
                            w, d = (2.8, 1.8) if abs(tx) >= abs(ty) else (1.8, 2.8)
                            adds.append(dict(kind='rampart', x=round(cx, 2), y=round(cy, 2), r=0, v=0, width=w, depth=d, color='#d7d3bc', label='', layout=TAG))
            for r in ([] if axis else runs):
                pts = []
                for u, v in zip(r, r[1:]):
                    steps = max(1, int(math.dist(u, v) / WALL_STEP))
                    pts += [(u[0] + (v[0] - u[0]) * j / steps, u[1] + (v[1] - u[1]) * j / steps) for j in range(steps)]
                pts.append(tuple(r[-1]))
                run_len = 0.
                for j in range(2, len(pts) - 2):        # leave the ends free: a seam or another border starts there
                    p0, p1 = pts[j - 2], pts[j + 2]
                    tx, ty = p1[0] - p0[0], p1[1] - p0[1]
                    ln = math.hypot(tx, ty) or 1
                    nx, ny = -ty / ln, tx / ln
                    c = pts[j]
                    if not on(c[0] + nx * 3, c[1] + ny * 3):
                        nx, ny = -nx, -ny
                    cx, cy = c[0] + nx * wall_in, c[1] + ny * wall_in
                    run_len += WALL_STEP
                    if math.dist((cx, cy), A) <= hw + 1.9 or any(math.dist(t, (cx, cy)) < 2.2 for t in flank):
                        continue                          # the opening and the flank towers
                    if run_len % 28 < WALL_STEP and not any(math.dist(t, (cx, cy)) < 8 for t in towers):
                        towers.append((cx, cy))
                        continue
                    ax, ay = abs(tx), abs(ty)
                    w, d = (2.8, 1.8) if ax >= 2 * ay else (1.8, 2.8) if ay >= 2 * ax else (2.3, 2.3)
                    adds.append(dict(kind='rampart', x=round(cx, 2), y=round(cy, 2), r=0, v=0, width=w, depth=d, color='#d7d3bc', label='', layout=TAG))
            for tx_, ty_ in towers:
                adds.append(dict(kind='tower', x=round(tx_, 2), y=round(ty_, 2), r=0, v=0, width=3.4, depth=3.4, color='#4a7a9a', label='', layout=TAG))
            # scenery under the wall goes; a spawn too close would be walled in
            def hit(o):
                for w_ in adds:
                    if math.hypot(o['x'] - w_['x'], o['y'] - w_['y']) < max(w_['width'], w_['depth']) / 2 + (o.get('r', .5) or .5) + .9:
                        return True
                return False
            # a pocket of land just beyond the wall (the border line is the wall's outer face): the strip you stand on under the vault
            floor = np.array([[c == '#' for c in row] for row in rows])
            ys, xs = np.mgrid[0:n, 0:n]
            dx_, dy_ = xs + .5 - A[0], ys + .5 - A[1]
            along, across = dx_ * wx + dy_ * wy, dx_ * px + dy_ * py
            pocket = (along >= -1.0) & (along <= 6.2) & (np.abs(across) <= hw + 1.0)
            floor = floor | pocket
            z['shapeFloor'] = floor_rows(floor)
            z['objects'] = [o for o in z['objects'] if o['kind'] != 'void' and (o['kind'] in STRUCTURAL or not (hit(o) or lost[int(o['y']) % n, int(o['x']) % n]))]
            z['objects'].extend(void_pieces(floor | margins[i]))
            z['slimes'] = [s for s in z['slimes'] if not hit(dict(s, r=1.5)) and not lost[int(s['y']), int(s['x'])]]
            # the ground beyond the straight wall is the neighbour's: edge rows of the changed band say so
            code = chr(ord('A') + z['shape']['neighbours'].index(lm))
            er = [list(r_) for r_ in z['shapeEdge']]
            band = dilate(floor, EDGE_BAND) & ~floor
            near = dilate(floor != orig_floor, EDGE_BAND)
            seamed = {chr(ord('A') + z['shape']['neighbours'].index(p_['to'])) for p_ in z['portals'] if 'seam' in p_}
            for yy in range(n):
                for xx in range(n):
                    if floor[yy, xx]:
                        er[yy][xx] = ' '
                    elif near[yy, xx] and band[yy, xx] and er[yy][xx] not in seamed:    # beside a seam the ground stays the seam neighbour's
                        er[yy][xx] = code
            z['shapeEdge'] = [''.join(r_) for r_ in er]
            z['objects'].extend(adds)
            z['exitArches'] = [e for e in z.get('exitArches', []) if e['portal'] != gate['id']] + [arch]
            # Both gates sit just past the arch's centre (the server also triggers up to 2.8 tiles before its portal) and carry the
            # one offset between the two frames: this zone's A is the city's own arch.
            shift = [round(carch['x'] - A[0], 2), round(carch['y'] - A[1], 2)]
            if str(i) in (fits or {}):                         # the road was laid to the old border: carry it on to the arch
                for path in z['paths']:
                    if math.dist(path[0], (gate['x'], gate['y'])) < 1.5:    # ca.approach runs from the gate back to the road
                        path.insert(0, [A[0], A[1]])
            gate['x'], gate['y'], gate['r'] = round(A[0] + wx * 3.0, 2), round(A[1] + wy * 3.0, 2), 1.2
            # the doorway is clear: scenery of the city standing in its own opening would block it and show from one side only
            city['objects'] = [o for o in city['objects'] if not (o['kind'] in ('tree', 'bush', 'rock', 'flowers')
                               and abs((o['x'] - carch['x']) * wx + (o['y'] - carch['y']) * wy) <= 3
                               and abs((o['x'] - carch['x']) * -wy + (o['y'] - carch['y']) * wx) <= hw + 1)]
            gate['vault'] = shift
            gate['vault_half'] = back['vault_half'] = hw
            back['x'], back['y'], back['r'] = round(carch['x'] - wx * 3.0, 2), round(carch['y'] - wy * 3.0, 2), 1.2
            back['vault'] = [-shift[0], -shift[1]]
            gate['tx'], gate['ty'] = round(gate['x'] + shift[0], 2), round(gate['y'] + shift[1], 2)
            back['tx'], back['ty'] = round(back['x'] - shift[0], 2), round(back['y'] - shift[1], 2)
            for e in city.get('cityEntrances', []):
                if e.get('portal') == back['id']:
                    e['points'][0] = [back['x'], back['y']]
            prev = ca.connected(z)
            assert int(gate['y']) * n + int(gate['x']) in prev, f"zone {i}: the vault gate to {lm} is cut off by the wall (A {A}, gate {gate['x']},{gate['y']}, walk {wx},{wy}, on land {on(gate['x'], gate['y'])}, pocket cells {int(pocket.sum())}, arch hw {hw})"
            ca.exit_routes(z)
            ca.exit_routes(city)
            # a region's ends stop at land, this zone's or a seam neighbour's (Skaldholm has shaped zones on every side)
            taken = floor_now.copy()
            for p_ in z['portals']:
                if 'seam' in p_:
                    other = np.array([[c == '#' for c in row] for row in zones[p_['to']]['shapeFloor']])
                    sx_, sy_ = p_['seam']['shift']
                    js, is_ = np.nonzero(other)
                    js, is_ = js - sy_, is_ - sx_
                    keep = (js >= 0) & (js < n) & (is_ >= 0) & (is_ < n)
                    taken[js[keep], is_[keep]] = True
            regs = vault_regions(runs, lambda x, y: 0 <= int(y) < n and 0 <= int(x) < n and floor_now[int(y), int(x)], taken)
            z['shape'].setdefault('vaultRegions', []).extend(dict(r_, to=lm, portal=gate['id']) for r_ in regs)
            print(f"zone {i}: wall to {zones[lm]['name']}: {len(adds) - len(towers)} ramparts, {len(towers)} towers, vault at {A}, shift {shift}")

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
    if cfg.get('cityRebuild'):      # AFTER the neighbours' shift_incoming(-1), which also rewrote the city's back portals
        import skaldholm_rebuild
        skaldholm_rebuild.restore(world)
    return offsets


def phantom_gate(world, z, design):
    """Run a finished zone's design as if the Wyrdwood border were still a gate. The Crags' and Rimeveil's designs were approved before the
    Wyrdwood was shaped; a gate blocks a disc of scenery and spawns round it, and without that disc every seeded scatter draws different
    points, so the whole zone would reshuffle. The gate's old record is in world/zone-shapes/late-gates.txt; the real crossing is the seam.
    A later seam has its own record under the key "<zone>:<other zone>" (the Crags' gate to the Obsidian Orrery, 2026-11-08), kept only while that seam exists."""
    zone = zone_of(world, z)
    side = json.loads((SIDE / 'late-gates.txt').read_text())
    records = []
    if side.get(str(z)) and 6 in config()['zones']:
        records.append(('phantom_wyrd_gate', side[str(z)]))
    for key, rec in side.items():
        if key.startswith(f'{z}:') and any(p.get('seam') and p['to'] == rec['portal']['to'] for p in zone['portals']):
            records.append((f"phantom_{rec['portal']['id']}", rec))
    if not records:
        return design(world, write=True)
    for pid, rec in records:
        zone['portals'].append(dict(copy.deepcopy(rec['portal']), id=pid))
    try:
        return design(world, write=True)
    finally:
        gone = {pid for pid, _ in records}
        zone['portals'] = [p for p in zone['portals'] if p['id'] not in gone]


def apply(world, cfg):
    atlas = Atlas()
    SIDE.mkdir(exist_ok=True)
    if cfg.get('cityRebuild'):      # the old city, before build_walls edits its back portals
        import skaldholm_rebuild
        skaldholm_rebuild.save_sidecar(world)
    shifted = {}
    margins = {}
    gate_only = set(cfg.get('gateOnly', []))
    design_only = design_only_zones()
    olds = {z: get_view(world, z) for z in cfg['zones']}
    geoms = {z: shape_geometry(cfg, atlas, z, olds[z]) for z in cfg['zones']}
    for z in cfg['zones']:
        zone = zone_of(world, z)
        assert 'shape' not in zone, f'zone {z} is already shaped: run unshape first'
        old = olds[z]
        (SIDE / f'preshape-{z:02d}.txt').write_text(json.dumps(old, indent=1, ensure_ascii=False) + '\n')
        geom = geoms[z]
        view = copy.deepcopy(old)
        S0 = view['size']
        view['_old_size'] = S0
        rng = random.Random(20261105 + z)
        warp = None
        if FILL.get(z, {}).get('warp'):
            ox = oy = 0
            warp = Warp(geom, S0)
            warp_view(view, warp)
            added = fill_zone(z, view, geom, (0, 0), rng, core=warp.region(), F=warp)
        elif z in rebuild_zones():       # the old city cannot sit inside the outline: nothing is moved, the design rebuilds the zone (placeholders keep the outline check honest)
            ox = oy = 0
            for key in ('objects', 'slimes', 'npcs', 'places', 'crosses'):
                if key in view:
                    view[key] = []
            c = geom['floor']
            ys_, xs_ = np.nonzero(erode(c, 12))
            k_ = len(xs_) // 2
            view['spawn'] = dict(x=int(xs_[k_]) + .5, y=int(ys_[k_]) + .5)
            view['npcs'] = [dict(n, x=view['spawn']['x'], y=view['spawn']['y']) for n in old['npcs'] if n.get('travelStop')]     # the Spark Travel master stays, so the neighbours keep their link to it
            view['city'] = dict(view['city'], x0=int(xs_[k_]) - 2, x1=int(xs_[k_]) + 3, y0=int(ys_[k_]) - 2, y1=int(ys_[k_]) + 3)
            added = (0, 0)
        elif z in gate_only or z in design_only:       # a sky zone (or a design-only one): the old layout is moved as a block and nothing fills the rest (its design replaces it)
            ox, oy = choose_offset(geom, old, z, atlas, world)
            shift_view(view, ox, oy)
            added = (0, 0)
        else:
            ox, oy = choose_offset(geom, old, z, atlas, world)
            shift_view(view, ox, oy)
            added = fill_zone(z, view, geom, (ox, oy), rng)
        del view['_old_size']
        # Land runs SEAM_MARGIN tiles past a seam border so a walker can step across the line (the server then moves it).
        margin = np.zeros_like(geom['floor'])
        n = geom['size']
        ys, xs = np.mgrid[0:n, 0:n]
        for j in cfg['zones']:
            if j != z and j not in gate_only and z not in gate_only and seam_allowed(z, j) and abs(geoms[j]['scale'] - geom['scale']) < 1e-9:
                for run in geom['runs']:
                    if run['kind'] == 'shared' and run['other'] == j:
                        for a, b in zip(run['points'], run['points'][1:]):
                            dx, dy = b[0] - a[0], b[1] - a[1]
                            t = np.clip(((xs + .5 - a[0]) * dx + (ys + .5 - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
                            margin |= np.hypot(xs + .5 - a[0] - t * dx, ys + .5 - a[1] - t * dy) <= SEAM_MARGIN
        margin &= ~geom['floor']
        margins[z] = margin
        if z in gate_only:         # walkable = the old islands and bridges moved into the new frame; the rest of the grid is sky
            walk = np.zeros_like(geom['floor'])
            for y, row in enumerate(view['sky']):
                for x, c in enumerate(row):
                    if c != ' ':
                        walk[y + oy, x + ox] = True
            view['sky'] = [''.join('#' if v else ' ' for v in r) for r in walk]
            voids = void_pieces(walk)
        else:
            voids = void_pieces(geom['floor'] | margin)
        view['objects'] = [o for o in view['objects'] if o['kind'] != 'void'] + voids
        view['size'] = geom['size']
        view['shape'] = dict(rule=cfg['rule'], k=round(geom['scale'], 4), offset=[ox, oy], core=S0, bbox=geom['bbox'], T=geom['T'],
                             outline=geom['outline'], edges=geom['runs'], neighbours=sorted(atlas.neighbours[z]))
        if warp:
            view['shape']['warp'] = [warp.y0, warp.y1]
        if z not in gate_only:     # a sky zone is drawn from its `sky` rows; the outline is only the frame for the world map
            view['shapeFloor'] = floor_rows(geom['floor'])
            view['shapeEdge'] = edge_rows(geom, sorted(atlas.neighbours[z]))
        check(z, view, geom)
        set_view(world, z, view)
        shifted[z] = (ox, oy)
        print(f"zone {z}: {'warped ' if warp else ''}{S0}x{S0} -> {geom['size']}x{geom['size']} (bbox {geom['bbox'][0]}x{geom['bbox'][1]}, k {geom['scale']:.3f}), "
              f"core at ({ox},{oy}), +{added[0]} objects, +{added[1]} spawns, {len(voids)} void pieces")
    shift_incoming(world, shifted, 1)
    place_portals(world, shifted, cfg.get('landmarks', []), cfg.get('wallAxis'), cfg.get('wallFit'))
    build_walls(world, shifted, cfg.get('landmarks', []), margins, cfg.get('wallAxis'), cfg.get('wallFit'))
    if cfg.get('cityRebuild'):      # the wing is Greenmeadow's land and the south-west corner is a corner, before any design runs
        import skaldholm_rebuild
        skaldholm_rebuild.prepare(world, margins)
    # Greenmeadow is an authored map: scenery, spawns, trails and quests are replaced last, on the finished outline, seams and vault.
    if 0 in cfg['zones']:
        import greenmeadow_design
        print('greenmeadow', greenmeadow_design.design(world, write=True)[1])
    if 1 in cfg['zones']:
        import crags_design
        d, stats = phantom_gate(world, 1, crags_design.design)
        print('crags', stats)
        if 6 in cfg['zones']:
            print('crags late seam trim', greenmeadow_design.late_trim(world['zones'][0], d))
    if 2 in cfg['zones']:
        import rimeveil_design
        d, stats = phantom_gate(world, 2, rimeveil_design.design)
        print('rimeveil', stats)
        if 6 in cfg['zones']:
            print('rimeveil late seam trim', greenmeadow_design.late_trim(world['zones'][1], d))
    if 3 in cfg['zones']:
        import gloamfen_design
        print('gloamfen', gloamfen_design.design(world, write=True)[1])
    if 6 in cfg['zones']:
        import wyrdwood_design
        print('wyrdwood', wyrdwood_design.design(world, write=True)[1])
    if 7 in cfg['zones']:       # after the Wyrdwood: it writes the Stormrift's arrival, and every other updraft here is re-pointed
        import bifrost_design
        print('bifrost', bifrost_design.design(world, write=True)[1])
    if 8 in cfg['zones']:       # after Bifrost: it wrote the Maelstrom's far end, and the Deep re-points every crossing that arrives here
        import deep_design
        print('deep', deep_design.design(world, write=True)[1])
        if 9 in cfg['zones']:       # Nacrehold's seam opens the south border: the approved design above ran unchanged
            print('deep seam', deep_design.late_seam(world, margins[8]))
    if 9 in cfg['zones']:       # after the Deep: the city is rebuilt on its outline, the Tideway is the seam
        import nacre_design
        print('nacrehold', nacre_design.design(world, margins[9], write=True)[1])
    if 13 in cfg['zones']:      # after the Deep and Nacrehold: it rewrites the arrivals of their crossings into Astralhollow (and the Prismwaste's and the Orrery's)
        import astral_design
        print('astralhollow', astral_design.design(world, write=True)[1])
    if 15 in cfg['zones']:      # after Astralhollow: it rewrites the arrivals of its crossings (the Crags', Nacrehold's, the Prismwaste's, Stormglass's and Emberwake's) and fills its seams to Astralhollow and the Moonspore Canopy
        import orrery_design
        print('orrery', orrery_design.design(world, write=True)[1])
    if 14 in cfg['zones']:      # after Astralhollow and the Orrery: both reserved/left the Prismwaste border (their gates became its seams); it rewrites the arrivals of Stormglass's and Cairnspine's crossings
        import prism_design
        print('prismwaste', prism_design.design(world, write=True)[1])
    if 19 in cfg['zones']:      # after the Prismwaste and the Orrery: both left their Stormglass border clear (their gates became its seams); it rewrites the arrivals of Asterion's, Sunward's, Frostwake's and Emberwake's crossings and the Eye's way back
        import storm_design
        print('stormglass', storm_design.design(world, write=True)[1])
    if 45 in cfg['zones']:      # after the Stormglass Flats (its south gate became the seam): it rewrites the arrivals of the Orrery's, the Ribbonwild's and the raid's crossings and makes the Nine-Chain Door camp
        import ember_design
        print('emberwake', ember_design.design(world, write=True)[1])
    if 21 in cfg['zones']:      # after Emberwake (its east gate became the seam; its design dropped the spawns and lava near it): it rewrites the arrivals of Sunward's, the Tanglecrown's and the Pavilion's crossings
        import ribbon_design
        print('ribbonwild', ribbon_design.design(world, write=True)[1])
    if 22 in cfg['zones']:      # after the Ribbonwild (its south-east gate became the seam; its design dropped the spawns near it): it rewrites the arrivals of Sunward's, the Veyrroot Canopy's and the temple's crossings
        import tangle_design
        print('tanglecrown', tangle_design.design(world, write=True)[1])
    if 25 in cfg['zones']:      # after compact_atlas: it rewrites the arrivals of Sunward's, the Veyrroot Canopy's and the astrolabe's crossings and closes the Yearwheel (a wall, no portal on either side)
        import lapis_design
        print('lapis', lapis_design.design(world, write=True)[1])
    if 2 in cfg['zones'] and 3 in cfg['zones']:
        trim_corner_seam(world)
        align_corner_wall(world, margins)
    if cfg.get('cityRebuild'):      # last: the neighbours' walls are final, the city is made in the middle of them
        import skaldholm_rebuild
        skaldholm_rebuild.south_west_corner(world, margins)
        skaldholm_rebuild.rebuild(world)
        skaldholm_rebuild.even_flank_wall(world)
        skaldholm_rebuild.wing_gate(world, margins)
        skaldholm_rebuild.seam_tower(world)
    if 0 in cfg['zones']:       # last of all: the pier is cut out of zone 0's final voids (scripts/greenmeadow_dock.py)
        import greenmeadow_dock
        print('greenmeadow dock', greenmeadow_dock.build(world, json.loads((ROOT / 'world/levels.txt').read_text())))
    if 16 in cfg['zones'] and 45 in cfg['zones']:      # Emberwake's seam arrived after the Canopy's fill: only its spawns within 7 tiles of the seam and the loose scenery within 2.5 go
        print('canopy seam trim', trim_late_seam(world, 16, 45))
    # really last: a road crosses every seam (owner, 2026-11-07), laid on the finished designs so no seeded scatter moves (scripts/seam_roads.py)
    import seam_roads
    for line in seam_roads.build(world, [z for z in seam_roads.ROAD_ZONES if z in cfg['zones']]):
        print('seam road', line)
    if 19 in cfg['zones']:      # the Stormglass Shore is no shore: every text that names it follows (scripts/storm_design.py)
        import storm_design
        storm_design.rename(world)
    return shifted


def trim_late_seam(world, z, to, spawn_dist=7.0, loose_dist=2.5):
    """A seam that arrived after zone `z` was filled or designed (Emberwake's, 2026-11-08, against the Moonspore Canopy): a hero must not wake a pack while
    crossing and no loose scenery stands on the line. Only the spawns within `spawn_dist` of the seam to `to` and the loose objects within `loose_dist` go;
    nothing else moves. Returns (spawns, objects) dropped."""
    zone = zone_of(world, z)
    n = zone['size']
    ys, xs = np.mgrid[0:n, 0:n] + .5
    field = np.full((n, n), 1e9)
    for p in zone['portals']:
        if p.get('seam') and p['to'] == to:
            pts = p['seam']['points']
            for a, b in zip(pts, pts[1:]):
                dx, dy = b[0] - a[0], b[1] - a[1]
                t = np.clip(((xs - a[0]) * dx + (ys - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
                field = np.minimum(field, np.hypot(xs - a[0] - t * dx, ys - a[1] - t * dy))
    at = lambda o: field[min(max(int(o['y']), 0), n - 1), min(max(int(o['x']), 0), n - 1)]
    keep = [t for t in zone['slimes'] if at(t) > spawn_dist]
    gone = len(zone['slimes']) - len(keep)
    zone['slimes'] = keep
    loose = [o for o in zone['objects'] if o['kind'] != 'void' and o.get('layout') == TAG and at(o) < loose_dist]
    zone['objects'] = [o for o in zone['objects'] if o not in loose]
    return gone, len(loose)


def align_corner_wall(world, margins):
    """Skaldholm's west wall is one straight line: Gloamfen's wall (x = 245.93 in its frame) carries on straight into Rimeveil (x = 226.93 in Rimeveil's frame,
    shift [19, -230]). Each zone fits the city's wall to its own border, so the two used to meet 10 tiles apart, joined by a stub along Gloamfen's north wall
    (owner, 2026-11-06: \"make the straight wall from Gloamfen continue straight in Rimeveil\"). Rimeveil's leg moves 10.07 tiles west, its corner tower and north wall
    with it; the land east of the new line is the city's; Gloamfen's stub goes."""
    rime, fen = world['zones'][1], world['zones'][2]
    old_x, new_x = 237.0, 245.93 - 19.0
    d = round(new_x - old_x, 2)                                            # -10.07
    n = rime['size']
    # --- Rimeveil: the leg and the corner tower move, the north wall grows west to meet it
    pieces = [o for o in rime['objects'] if o['kind'] in ('rampart', 'tower') and o.get('layout') == TAG]
    leg = [o for o in pieces if abs(o['x'] - old_x) < .05 and 245 < o['y'] < 296]
    assert len(leg) == 8, f'the leg of Rimeveil\'s wall changed: {len(leg)} pieces'
    for o in leg:
        o['x'] = round(o['x'] + d, 2)
    north = sorted((o for o in pieces if o['kind'] == 'rampart' and abs(o['y'] - 251.8) < .05), key=lambda o: o['x'])
    step = north[1]['x'] - north[0]['x']
    x = north[0]['x'] - step
    while x > new_x + 1.5:
        rime['objects'].append(dict(north[0], x=round(x, 2)))
        x -= step
    floor = np.array([[c == '#' for c in row] for row in rime['shapeFloor']])
    cut = np.zeros_like(floor)
    cut[253:, int(new_x + .9) + 1:250] = True                        # the leg's band only: the vault's pocket at x ~ 269 stays
    cut &= floor
    floor &= ~cut
    ys, xs = np.nonzero(cut)
    gone = lambda o: new_x + .9 <= o['x'] and o['y'] >= 252.7 and o['kind'] != 'void'
    rime['objects'] = [o for o in rime['objects'] if o['kind'] in ('rampart', 'tower') and o.get('layout') == TAG or not gone(o)]
    rime['slimes'] = [t for t in rime['slimes'] if not (new_x + .9 <= t['x'] and t['y'] >= 252.7)]
    rime['shapeFloor'] = floor_rows(floor)
    # the stretch of the border that no longer crosses (x > 222 in Rimeveil's frame, 241 in Gloamfen's) is an ordinary edge again: voids right at the land
    m_r = margins[2].copy()
    m_r[280:, int(CORNER_CUT_X - 19):] = False
    rime['objects'] = [o for o in rime['objects'] if o['kind'] != 'void'] + void_pieces(floor | m_r)
    code = chr(ord('A') + rime['shape']['neighbours'].index(4))
    er = [list(r_) for r_ in rime['shapeEdge']]
    band = dilate(floor, EDGE_BAND) & ~floor
    near = dilate(cut, EDGE_BAND)
    seamed = {chr(ord('A') + rime['shape']['neighbours'].index(p_['to'])) for p_ in rime['portals'] if 'seam' in p_}
    for yy in range(n):
        for xx in range(n):
            if floor[yy, xx]:
                er[yy][xx] = ' '
            elif near[yy, xx] and band[yy, xx] and er[yy][xx] not in seamed:
                er[yy][xx] = code
    rime['shapeEdge'] = [''.join(r_) for r_ in er]
    for reg in rime['shape'].get('vaultRegions', []):
        for key in ('land', 'strip', 'city'):
            pts = reg[key]
            for i in range(0, len(pts), 2):
                if abs(pts[i] - 238.2) < .05 and 250 < pts[i + 1] < 296:
                    pts[i] = round(pts[i] + d, 2)
                elif abs(pts[i] - 242.2) < .05 and 250 < pts[i + 1] < 296:
                    pts[i] = round(pts[i] + d, 2)
    # --- Gloamfen: the stub along the north wall east of the corner goes, and the lip of land beside it
    fen['objects'] = [o for o in fen['objects'] if not (o['kind'] == 'rampart' and o.get('layout') == TAG and abs(o['y'] - 62.0) < .05 and o['x'] > 247)]
    ffloor = np.array([[c == '#' for c in row] for row in fen['shapeFloor']])
    fcut = np.zeros_like(ffloor)
    fcut[:64, 247:] = True
    fcut &= ffloor
    ffloor &= ~fcut
    fen['shapeFloor'] = floor_rows(ffloor)
    m_f = margins[3].copy()
    m_f[:75, int(CORNER_CUT_X):] = False
    fen['objects'] = [o for o in fen['objects'] if o['kind'] != 'void'] + void_pieces(ffloor | m_f)
    margins[3] = m_f
    fcode = chr(ord('A') + fen['shape']['neighbours'].index(4))
    fer = [list(r_) for r_ in fen['shapeEdge']]
    fband = dilate(ffloor, EDGE_BAND) & ~ffloor
    fnear = dilate(fcut, EDGE_BAND)
    fseamed = {chr(ord('A') + fen['shape']['neighbours'].index(p_['to'])) for p_ in fen['portals'] if 'seam' in p_}
    for yy in range(fen['size']):
        for xx in range(fen['size']):
            if ffloor[yy, xx]:
                fer[yy][xx] = ' '
            elif fnear[yy, xx] and fband[yy, xx] and fer[yy][xx] not in fseamed:
                fer[yy][xx] = fcode
    fen['shapeEdge'] = [''.join(r_) for r_ in fer]
    print(f'corner wall aligned: Rimeveil leg moved {d}, {int(cut.sum())} Rimeveil and {int(fcut.sum())} Gloamfen cells handed to the city')


CORNER_CUT_X = 241.0


def trim_corner_seam(world):
    """Rimeveil's and Gloamfen's shared border ends at Skaldholm's north-west wall corner, past the point where Gloamfen's land stops (x ~ 246, Gloamfen's frame):
    a hero walking down Rimeveil's side of the wall into the last wedge used to cross there and arrive inside the wall, shut in (owner, 2026-11-06). The seam portals
    stop at x = CORNER_CUT_X (Gloamfen's frame); the wedge is a dead end against the wall."""
    rime, fen = world['zones'][1], world['zones'][2]
    for z, to, to_fen in ((fen, 2, True), (rime, 3, False)):
        portal = next(p for p in z['portals'] if p.get('seam') and p['to'] == to)
        seam = portal['seam']
        dx, dy = (0., 0.) if to_fen else (float(seam['shift'][0]), float(seam['shift'][1]))      # this zone's frame -> Gloamfen's
        pts = [[x + dx, y + dy] for x, y in seam['points']]
        out = []
        for k, a in enumerate(pts):
            if a[0] <= CORNER_CUT_X:
                out.append(a)
            if k + 1 < len(pts) and (a[0] <= CORNER_CUT_X) != (pts[k + 1][0] <= CORNER_CUT_X):
                b = pts[k + 1]
                t = (CORNER_CUT_X - a[0]) / (b[0] - a[0])
                out.append([CORNER_CUT_X, a[1] + (b[1] - a[1]) * t])
        out = [[round(x - dx, 2), round(y - dy, 2)] for x, y in out]
        assert len(out) >= 2, 'the corner trim emptied a seam'
        seam['points'] = out


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
    c = view.get('city')        # an outdoor zone without a hub rectangle (Emberwake) has none until its design makes one
    assert not c or all(ok(x, y) for x in (c['x0'], c['x1']) for y in (c['y0'], c['y1'])), f'zone {z}: city outside the outline'


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
