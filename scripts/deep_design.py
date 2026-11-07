#!/usr/bin/env python3
"""Rán's Deep as an authored map on its atlas outline (zone 8 of the shapes pilot): the sea floor under the storm, the whole outline used.

Owner request 2026-11-07: "reshape rans deep and remake the zone and quests to fit the new shape, no fillers, keep the portals/updrafts since this
place should be inaccessible without them. The only place it should have a seamless against is nacrehold, but that comes after nacrehold's reshape."
It keeps the Deep's own style (the coral labyrinth, the open Shallows, Keelhaven, the tidebells, the Kraken, Hvitserk and the Ghostmaw, the
underwater look, black water beyond the outer reef): only the geometry is new.

Runs in `zone_shapes.py apply` after Bifrost's design. The zone is `designOnly` (zone-shapes.txt): it keeps the outline floor (`shapeFloor`), takes no
filler, and places its own gates (`place_portals` skips it). `seamWith` lets it seam with Nacrehold only, later: the band along the Nacrehold border is
kept free now (no scenery within 2.5 tiles, no spawn within 7, no building within 20) so that seam cannot reshuffle this design.

Everything that is not the plan below comes from `world/zone-shapes/preshape-08.txt` (the old layout): Keelhaven moves as one block, with its people, houses,
lamps, the Longship's door and its two people; every quest id and person id stays.

    python3 scripts/deep_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import copy
import heapq
import itertools
import json
import math
import os
import random
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-08.txt'
ZONE = 8
STEP = .5
SPEED = 5.2                       # the slowest class (warrior), tiles per second

# ---- the plan ------------------------------------------------------------------------------------------------------------------
PITCH, THICK = 16, 3.0            # a cell of the Net: 16 tiles, walls 3 thick, corridors 13 wide (as the old Net)
OX, OY, COLS, ROWS = 8, 14, 15, 10
SOUTH_WALL = OY + ROWS * PITCH    # the Net's south wall; the Shallows lie below it
ENTRY = (5, 9)                    # the cell behind the Pearl Gate, the Net's one door
PIECE = 4.0                       # longest wall rectangle
RIM = 3                           # the outer reef wall: three tiles inside the outline
BRAID = .55
# rooms of the Net that are one open node each: Ran's Court (the Kraken) and the two camps inside the Net
BLOCKS = {
    'court': [(7, 2), (8, 2), (7, 3), (8, 3)],
    'lantern': [(1, 5), (2, 5), (1, 6), (2, 6)],
    'gatewatch': [(13, 6), (14, 6), (13, 7), (14, 7)],
}
BLOCK_OF = {c: k for k, cells in BLOCKS.items() for c in cells}
HUB_X = 96                        # Keelhaven stands under the Pearl Gate
HUB_Y0 = 190                      # top of Keelhaven's sanctuary
BELL_R = 2.6
AWARENESS = {'kraken': 14., 'hvitserk': 10., 'ghostmaw': 12.}
SEED = 20261107
MAZE_SEED = 275                    # found by search_seed(): the Court is the deepest room, the Gatewatch deep too, Lanternrest in the first half


# ---- small helpers ---------------------------------------------------------------------------------------------------------------
def key(a, b):
    return (a, b) if a <= b else (b, a)


def neighbours(c, r):
    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = c + dc, r + dr
        if 0 <= a < COLS and 0 <= b < ROWS:
            yield a, b


def cell_box(c, r):
    """(x0, y0, x1, y1) of a cell's floor, inside the walls."""
    h = THICK / 2
    return (OX + c * PITCH + h, OY + r * PITCH + h, OX + (c + 1) * PITCH - h, OY + (r + 1) * PITCH - h)


def cell_centre(c, r):
    return (OX + (c + .5) * PITCH, OY + (r + .5) * PITCH)


def cell_of(x, y):
    return int((x - OX) // PITCH), int((y - OY) // PITCH)


def hash2(a, b, s=0):
    h = (a * 374761393 + b * 668265263 + s * 2147483647) & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    return ((h ^ (h >> 16)) & 0xffffffff) / 4294967296


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


# ---- the lattice and the maze ----------------------------------------------------------------------------------------------------
def lattice(W):
    """Cells of the Net that exist on this outline: the ones whose floor box holds enough walkable ground to be a room.
    -> (kept set, dropped set). A dropped cell is left to the sea (void)."""
    kept, dropped = set(), set()
    for r in range(ROWS):
        for c in range(COLS):
            x0, y0, x1, y1 = cell_box(c, r)
            sub = W[int(y0):int(y1), int(x0):int(x1)]
            frac = sub.sum() / max(1, sub.size)
            if frac >= .5 and sub.sum() >= 60 and ndimage.distance_transform_edt(np.pad(sub, 1)).max() >= 3.2:
                kept.add((c, r))
            else:
                dropped.add((c, r))
    return kept, dropped


def maze(kept, seed, braid=BRAID):
    """-> (doors, depth): `doors` the open pairs between different nodes; `depth` cell -> steps from ENTRY. Every block is one node."""
    rng = random.Random(seed)
    node = {c: BLOCK_OF.get(c, c) for c in kept}
    adj = {}
    for a in sorted(kept):
        for b in neighbours(*a):
            if b in kept and node[a] != node[b]:
                adj.setdefault(node[a], []).append((node[b], key(a, b)))
    start = node[ENTRY]
    seen, stack, doors = {start}, [start], set()
    while stack:
        n = stack[-1]
        options = [(m, d) for m, d in adj.get(n, []) if m not in seen]
        if not options:
            stack.pop()
            continue
        m, d = rng.choice(options)
        doors.add(d)
        seen.add(m)
        stack.append(m)
    degree = {}
    for a, b in doors:
        degree[node[a]] = degree.get(node[a], 0) + 1
        degree[node[b]] = degree.get(node[b], 0) + 1
    ends = sorted((n for n in set(node.values()) if degree.get(n, 0) == 1 and n != start and n not in BLOCKS), key=str)
    for n in ends:
        if rng.random() < braid:
            options = [(m, d) for m, d in adj.get(n, []) if m not in BLOCKS and d not in doors]
            if options:
                doors.add(rng.choice(options)[1])
    nodes = set(node.values())
    if seen != nodes:
        return None, {}
    return doors, depths(kept, doors)


def open_pairs(kept, doors):
    pairs = set(doors)
    for cells in BLOCKS.values():
        for a in cells:
            for b in neighbours(*a):
                if b in cells:
                    pairs.add(key(a, b))
    return pairs


def depths(kept, doors):
    pairs = open_pairs(kept, doors)
    d = {ENTRY: 0}
    queue = [ENTRY]
    for c in queue:
        for n in neighbours(*c):
            if n in kept and n not in d and key(c, n) in pairs:
                d[n] = d[c] + 1
                queue.append(n)
    return d


def block_doors(doors, name):
    return sorted(d for d in doors if (d[0] in BLOCKS[name]) != (d[1] in BLOCKS[name]))


def search_seed(kept, limit=900):
    """Seeds whose Court has exactly two doors and lies deep, whose far camp (the Gatewatch) lies deep too and whose Lantern camp lies in the first half;
    every camp has at least two doors. Best first."""
    out = []
    for seed in range(limit):
        doors, depth = maze(kept, seed)
        if doors is None or len(depth) != len(kept) or len(block_doors(doors, 'court')) != 2:
            continue
        if any(len(block_doors(doors, b)) < 2 for b in ('lantern', 'gatewatch')):
            continue
        ranked = sorted(v for c, v in depth.items() if c not in BLOCK_OF)
        pct = lambda cell: sum(1 for v in ranked if v <= depth[cell]) / len(ranked)
        court, lantern, gate = pct(BLOCKS['court'][0]), pct(BLOCKS['lantern'][0]), pct(BLOCKS['gatewatch'][0])
        if not (.3 <= lantern <= .62 and gate >= .6 and court >= .75):
            continue
        out.append((court + .4 * gate - abs(lantern - .45) + .004 * max(ranked), seed, court, lantern, gate, max(ranked)))
    return sorted(out, reverse=True)


def wall_rects(kept, doors):
    """Every wall of the Net as (x, y, width, depth) rectangles of at most PIECE: between rooms that are not joined, against dropped cells, and the
    Net's south wall."""
    pairs = open_pairs(kept, doors)
    h = THICK / 2
    segments = []
    for r in range(ROWS):
        for c in range(COLS):
            if (c, r) not in kept:
                continue
            for dc, dr in ((1, 0), (0, 1)):
                n = (c + dc, r + dr)
                inside = n[0] < COLS and n[1] < ROWS
                if inside and n in kept and key((c, r), n) in pairs:
                    continue
                if dr and not inside and c == ENTRY[0]:                      # the Pearl Gate
                    continue
                if dc:
                    x = OX + (c + 1) * PITCH
                    segments.append((x - h, OY + r * PITCH - h, x + h, OY + (r + 1) * PITCH + h))
                else:
                    y = OY + (r + 1) * PITCH
                    segments.append((OX + c * PITCH - h, y - h, OX + (c + 1) * PITCH + h, y + h))
            if r == 0 or (c, r - 1) not in kept:
                y = OY + r * PITCH
                segments.append((OX + c * PITCH - h, y - h, OX + (c + 1) * PITCH + h, y + h))
            if c == 0 or (c - 1, r) not in kept:
                x = OX + c * PITCH
                segments.append((x - h, OY + r * PITCH - h, x + h, OY + (r + 1) * PITCH + h))
    out = []
    for x0, y0, x1, y1 in segments:
        w, d = x1 - x0, y1 - y0
        if w >= d:
            n = max(1, math.ceil(w / PIECE))
            for k in range(n):
                a, b = x0 + w * k / n, x0 + w * (k + 1) / n
                out.append(((a + b) / 2, (y0 + y1) / 2, b - a, d))
        else:
            n = max(1, math.ceil(d / PIECE))
            for k in range(n):
                a, b = y0 + d * k / n, y0 + d * (k + 1) / n
                out.append(((x0 + x1) / 2, (a + b) / 2, w, b - a))
    seen, uniq = set(), []                           # the same wall is asked for from both sides: keep one of each
    for x, y, w, d in out:
        k = (round(x, 1), round(y, 1), round(w, 1), round(d, 1))
        if k not in seen:
            seen.add(k)
            uniq.append((x, y, w, d))
    return uniq


def band_of_cells(depth):
    """cell -> quartile 0..3 of the depth ranking of the Net's ordinary cells (ties broken by position)."""
    cells = sorted((c for c in depth if c not in BLOCK_OF), key=lambda c: (depth[c], c[1], c[0]))
    return {c: min(3, k * 4 // len(cells)) for k, c in enumerate(cells)}


# ---- geometry of the shaped zone ------------------------------------------------------------------------------------------------------
def geometry(zone):
    import zone_shapes as zs
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    W = zs.erode(F, RIM)
    W[:int(OY)] = False
    W[:, :OX] = False
    W[:, OX + COLS * PITCH:] = False
    kept, dropped = lattice(W)
    for c, r in dropped:                          # a dropped cell is left to the reef
        x0, y0, x1, y1 = cell_box(c, r)
        W[int(y0 - 1.5):int(y1 + 1.5), int(x0 - 1.5):int(x1 + 1.5)] = False
    return F, W, kept, dropped


def seam_band(zone):
    """Distance from every cell to the Nacrehold border: the future seam (zone-shapes.txt `seamWith`)."""
    from greenmeadow_design import seg_field
    n = zone['size']
    ys, xs = np.mgrid[0:n, 0:n] + .5
    out = np.full((n, n), 1e9)
    for e in zone['shape']['edges']:
        if e['kind'] == 'shared' and e['other'] == 9:
            out = np.minimum(out, seg_field(e['points'], xs, ys))
    return out


def hop_table(kept, doors):
    pairs = open_pairs(kept, doors)
    out = {}
    for a in kept:
        d = {a: 0}
        queue = [a]
        for c in queue:
            for n in neighbours(*c):
                if n in kept and n not in d and key(c, n) in pairs:
                    d[n] = d[c] + 1
                    queue.append(n)
        out[a] = d
    return out


def tour(hops, cells):
    best = None
    for order in itertools.permutations(cells):
        total = sum(hops[a][b] for a, b in zip(order, order[1:]))
        if best is None or total < best:
            best = total
    return best


CHAINS = {'deep_harbour': 35, 'deep_net': 45, 'deep_rans': 50}
BELLS = {'deep_harbour': 3, 'deep_net': 4, 'deep_rans': 5}
BELL_LABELS = {'deep_harbour': 'Harbour Bell', 'deep_net': 'Bell of the Net', 'deep_rans': "Bell of Rán"}
ROMAN = ['I', 'II', 'III', 'IV', 'V']


def pick_bells(depth, band, hops, rng, skip=0):
    """-> {'deep_net': [cells], 'deep_rans': [cells]}: sets of cells whose tour is 52-68 % (net) / 55-70 % (rans) of the distance a slowest-class hero
    covers while the first bell still rings, widest spread first. `skip` takes the next best set (the real walk is checked afterwards)."""
    out = {}
    cc = (7.5, 2.5)
    specs = {
        'deep_net': (4, [c for c in depth if c not in BLOCK_OF and band[c] in (1, 2) and depth[c] >= 6], .52, .68),
        'deep_rans': (5, [c for c in depth if c not in BLOCK_OF and abs(c[0] - cc[0]) <= 3.2 and abs(c[1] - cc[1]) <= 3.2], .70, .85),
    }
    for chain, (n, pool, lo, hi) in specs.items():
        window = SPEED * CHAINS[chain]
        pool = sorted(pool)
        found = []
        sample = random.Random(SEED + n)
        for _ in range(60000):
            combo = tuple(sorted(sample.sample(pool, n)))
            if any(hops[a][b] < 2 for a, b in itertools.combinations(combo, 2)):
                continue
            t = tour(hops, combo) * PITCH
            if lo * window <= t <= hi * window:
                xs, ys = [cell_centre(*c)[0] for c in combo], [cell_centre(*c)[1] for c in combo]
                found.append(((max(xs) - min(xs)) * (max(ys) - min(ys)), combo))
        assert found, f'no bell set for {chain}'
        found = sorted(set(found), key=lambda t: (-t[0], t[1]))
        out[chain] = list(found[min(skip, len(found) - 1)][1])
    return out


def bell_position(cell, chain, k):
    cx, cy = cell_centre(*cell)
    return (round(cx + (hash2(cell[0], cell[1], 11 + k) - .5) * 7, 2), round(cy + (hash2(cell[0], cell[1], 23 + k) - .5) * 7, 2))


def trail(kept, doors, depth, goal):
    """The shortest route of cells from ENTRY to `goal` (a cell)."""
    pairs = open_pairs(kept, doors)
    path = [goal]
    while path[-1] != ENTRY:
        c = path[-1]
        path.append(min((n for n in neighbours(*c) if n in depth and key(c, n) in pairs and depth[n] < depth[c]), key=lambda n: (depth[n], n)))
    return path[::-1]


def distance_fields(blocked, sources):
    """True walking distance (8 neighbours, octile) from each source to every cell of the 0.5 grid, in tiles."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    n = blocked.shape[0]
    idx = np.arange(n * n).reshape(n, n)
    rows, cols, vals = [], [], []
    for dj, di in ((0, 1), (1, 0), (1, 1), (1, -1)):
        j0, j1 = 0, n - dj
        i0, i1 = (0, n - di) if di >= 0 else (-di, n)
        a = idx[j0:j1, i0:i1]
        b = idx[j0 + dj:j1 + dj, i0 + di:i1 + di]
        ok = ~blocked[j0:j1, i0:i1] & ~blocked[j0 + dj:j1 + dj, i0 + di:i1 + di]
        if di and dj:                                              # a diagonal step must not cut a corner
            ok &= ~blocked[j0:j1, i0 + di:i1 + di] & ~blocked[j0 + dj:j1 + dj, i0:i1]
        rows.append(a[ok])
        cols.append(b[ok])
        vals.append(np.full(ok.sum(), STEP * (math.sqrt(2) if di and dj else 1)))
    r, c, v = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
    graph = coo_matrix((np.concatenate([v, v]), (np.concatenate([r, c]), np.concatenate([c, r]))), shape=(n * n, n * n)).tocsr()
    starts = [int(y / STEP) * n + int(x / STEP) for x, y in sources]
    return dijkstra(graph, directed=False, indices=starts).reshape(len(sources), n, n)


# ---- the design ------------------------------------------------------------------------------------------------------------------------
class Deep:
    def __init__(self, world, old):
        import zone_shapes as zs
        self.zs = zs
        self.world, self.old = world, old
        self.zone = world['zones'][ZONE - 1]
        self.n = self.zone['size']
        self.F, self.W, self.kept, self.dropped = geometry(self.zone)
        n = self.n
        self.ys, self.xs = np.mgrid[0:n, 0:n] + .5
        self.edge = ndimage.distance_transform_edt(self.W)
        self.nacre = seam_band(self.zone)
        self.south = self.W & (self.ys > SOUTH_WALL + 2)           # the Shallows
        self.rng = random.Random(SEED)
        self.spots = Spots()
        self.objects = []
        self.walked = []                       # (x, y, what): roads, places, people, gates (an elite keeps clear of these)

    def add(self, kind, x, y, r=None, solid=True, **extra):
        o = dict(kind=kind, x=round(float(x), 2), y=round(float(y), 2), r=r if r is not None else 0, v=extra.pop('v', 0))
        o.update(extra)
        self.objects.append(o)
        if solid:
            self.spots.add(x, y, radius(o))
        return o

    def find(self, hint, margin=4.0, clear=0., minimum=2.0, region=None, nacre=0.):
        """The walkable cell nearest a hint whose edge distance is at least `margin`, that keeps `clear` from the spots and `nacre` from the Nacrehold border."""
        mask = self.W & (self.edge >= margin) & (self.nacre >= nacre)
        if region is not None:
            mask &= region
        ys, xs = np.nonzero(mask)
        order = np.argsort((xs + .5 - hint[0]) ** 2 + (ys + .5 - hint[1]) ** 2)
        for k in order[:40000]:
            x, y = xs[k] + .5, ys[k] + .5
            if self.spots.free(x, y, minimum, clear):
                return x, y
        raise SystemExit(f'no clear spot near {hint}')

    def cell_region(self, c, r, pad=0):
        x0, y0, x1, y1 = cell_box(c, r)
        m = np.zeros((self.n, self.n), bool)
        m[int(y0 - pad):int(y1 + pad), int(x0 - pad):int(x1 + pad)] = True
        return m


def solid_mask(objects, n, pad=.35):
    """Cells a walker (radius .35) cannot stand in: round objects by r, boxes by half sizes."""
    m = np.zeros((n, n), bool)
    for o in objects:
        if o['kind'] == 'void':
            hx, hy = o['width'] / 2, o['depth'] / 2
            m[max(0, int(o['y'] - hy)):min(n, int(o['y'] + hy) + 1), max(0, int(o['x'] - hx)):min(n, int(o['x'] + hx) + 1)] = True
        elif o.get('width') and o.get('depth'):
            hx, hy = o['width'] / 2 + pad, o['depth'] / 2 + pad
            m[max(0, int(o['y'] - hy)):min(n, int(o['y'] + hy) + 1), max(0, int(o['x'] - hx)):min(n, int(o['x'] + hx) + 1)] = True
        elif o.get('r'):
            rr = o['r'] + pad
            for j in range(max(0, int(o['y'] - rr)), min(n, int(o['y'] + rr) + 1)):
                for i in range(max(0, int(o['x'] - rr)), min(n, int(o['x'] + rr) + 1)):
                    if math.hypot(i + .5 - o['x'], j + .5 - o['y']) < rr:
                        m[j, i] = True
    return m


def design(world, write=False):
    import deep_pilot_content as content
    import generate_gloamfen as fen
    from greenmeadow_design import ground_spans
    old = json.loads(OLD.read_text())
    d = Deep(world, old)
    zone, n, rng = d.zone, d.n, d.rng
    kept = d.kept
    doors, depth = maze(kept, MAZE_SEED)
    assert doors is not None
    assert len(depth) == len(kept), 'the maze does not reach every cell'
    band = band_of_cells(depth)
    hops = hop_table(kept, doors)
    court = BLOCKS['court']
    cx0, cy0 = OX + 8 * PITCH, OY + 3 * PITCH                 # the middle of the 2 x 2 Court

    # ---- Keelhaven moves as one block: people, houses, lamps, the Longship's door and its two people
    D = (HUB_X - 80, HUB_Y0 - 143)

    def shift(o):
        o = copy.deepcopy(o)
        o['x'] = round(o['x'] + D[0], 2)
        o['y'] = round(o['y'] + D[1], 2)
        return o
    box = (50, 141, 100, 175)
    hub_kinds = ('lamp', 'house', 'chapel', 'stall', 'fountain', 'noticeboard', 'bench')
    for o in [shift(o) for o in old['objects'] if o['kind'] in hub_kinds and box[0] <= o['x'] <= box[2] and box[1] <= o['y'] <= box[3]]:
        d.objects.append(o)
        d.spots.add(o['x'], o['y'], radius(o))
    npcs = [shift(x) for x in old['npcs']]
    for x in npcs:
        assert box[0] <= x['x'] - D[0] <= box[2] and box[1] <= x['y'] - D[1] <= box[3], f"{x['id']} stands outside Keelhaven's block"
        d.walked.append((x['x'], x['y'], 'npc ' + x['id']))
        d.spots.add(x['x'], x['y'], .5)
    city = copy.deepcopy(old['city'])
    for k in ('x0', 'x1'):
        city[k] += D[0]
    for k in ('y0', 'y1'):
        city[k] += D[1]
    for k in ('plaza', 'entry'):
        city[k] = dict(x=city[k]['x'] + D[0], y=city[k]['y'] + D[1])
    assert city['y1'] <= 220 and np.all(d.nacre[int(city['y1']), int(city['x0']):int(city['x1'])] >= 20), 'Keelhaven stands within 20 tiles of the Nacrehold border'
    spawn = dict(x=old['spawn']['x'] + D[0], y=old['spawn']['y'] + D[1])
    longship = shift(next(p for p in old['portals'] if p['id'] == 'deep_longship'))
    d.walked.append((longship['x'], longship['y'], 'gate deep_longship'))
    d.spots.add(longship['x'], longship['y'], 3.0)

    # ---- walls: the Net, the reef massif round it and under the dropped cells, the outer reef along the outline
    def reef(x, y, w, dp, tag=None):
        o = dict(kind='reefwall', x=round(x, 2), y=round(y, 2), r=0, v=int(hash2(int(x * 4), int(y * 4), 3) * 4), width=round(w, 2), depth=round(dp, 2))
        if tag:
            o[tag] = 1
        return o
    walls = []
    for x, y, w, dp in wall_rects(kept, doors):
        if d.F[min(n - 1, int(y)), min(n - 1, int(x))]:
            walls.append(reef(x, y, w, dp))
    massif = []
    solid = d.F & ~d.W
    for gy in range(0, n, 3):
        for gx in range(0, n, 3):
            if solid[gy:gy + 3, gx:gx + 3].sum() >= 6:
                massif.append(reef(gx + 1.5, gy + 1.5, 3.0, 3.0, tag='rim'))
    for o in walls + massif:
        d.objects.append(o)
        d.spots.add(o['x'], o['y'], radius(o) * (.8 if o.get('rim') else 1.0))

    # ---- the three outposts
    hamlets = copy.deepcopy(content.HAMLETS)
    for key, h in hamlets.items():
        if h['room']:
            cells = BLOCKS[h['room']]
            h['x'] = OX + (min(c for c, _ in cells) + 1) * PITCH
            h['y'] = OY + (min(r for _, r in cells) + 1) * PITCH
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx, cy = h['x'] + sx * h['hw'], h['y'] + sy * h['hh']
                assert d.W[int(cy), int(cx)], f"{h['name']}: the camp's corner ({cx}, {cy}) is off the floor"
        assert np.all(d.nacre[int(h['y'] + h['hh']), int(h['x'] - h['hw']):int(h['x'] + h['hw'])] >= 20), f"{h['name']} stands within 20 tiles of the Nacrehold border"
        d.walked.append((h['x'], h['y'], 'camp ' + key))
    content.dress(d, hamlets)
    for h in hamlets.values():
        d.spots.add(h['x'], h['y'], 6.0)

    # ---- the crossings: Deep places its own gates (place_portals skips it); the Maelstrom and the Tideway keep their look and their far ends
    gates = {}

    def rim(x, y, dx, dy):
        while d.W[int(y + dy * .25), int(x + dx * .25)]:
            x += dx * .25
            y += dy * .25
        return x, y
    for pid, (cx, cy, direction) in {'maelstrom_up': (60, 208, (-1, 0)), 'nacre_gate': (HUB_X, 224, (0, 1)),
                                     'path_8_13': (hamlets['gatewatch']['x'], hamlets['gatewatch']['y'], (1, 0))}.items():
        rx, ry = rim(cx, cy, *direction)
        gate = (round(rx - direction[0] * 2.0, 1), round(ry - direction[1] * 2.0, 1))
        arrival = (round(gate[0] - direction[0] * 6.0, 1), round(gate[1] - direction[1] * 6.0, 1))
        assert d.W[int(arrival[1]), int(arrival[0])], f'{pid}: the arrival is off the floor'
        gates[pid] = dict(gate=gate, arrival=arrival, walk=list(direction))
        d.walked.append((gate[0], gate[1], 'gate ' + pid))
        d.spots.add(gate[0], gate[1], 3.0)
        d.spots.add(arrival[0], arrival[1], 3.0)
    for pid, g in gates.items():
        for dx in (-1.5, 1.5):
            d.add('post', g['gate'][0] + dx * abs(g['walk'][1]), g['gate'][1] + dx * abs(g['walk'][0]), .45)

    # ---- places and bells
    seed_skip = int(os.environ.get('DEEP_BELL_SKIP', '0'))
    bells = pick_bells(depth, band, hops, rng, seed_skip)
    taken = {c for cells in bells.values() for c in cells}
    garden = max((c for c in depth if c not in BLOCK_OF and c not in taken), key=lambda c: (depth[c], c[1], c[0]))
    cdoor = min(block_doors(doors, 'court'), key=lambda dd: min(depth[dd[0]], depth[dd[1]]))
    outer, inner = (cdoor[0], cdoor[1]) if cdoor[0] not in court else (cdoor[1], cdoor[0])
    ox_, oy_ = cell_centre(*outer)
    ix_, iy_ = cell_centre(*inner)
    mx, my = (ox_ + ix_) / 2, (oy_ + iy_) / 2
    dist = math.hypot(ox_ - mx, oy_ - my)
    gx_, gy_ = cell_centre(*garden)
    places = []
    pg = (HUB_X, SOUTH_WALL + 3.5)
    places.append(dict(id='deep_pearlgate', name='the Pearl Gate', x=pg[0], y=pg[1], r=3.5))
    places.append(dict(id='deep_garden', name='the Abyssal Garden', x=round(gx_, 2), y=round(gy_, 2), r=4.5))
    places.append(dict(id='deep_courtdoor', name='the Court Door', x=round(mx + (ox_ - mx) / dist * 4.5, 2), y=round(my + (oy_ - my) / dist * 4.5, 2), r=4.0))
    for p in places:
        d.walked.append((p['x'], p['y'], 'place ' + p['id']))
        d.spots.add(p['x'], p['y'], p['r'])
    # the Shallows' named places
    S = d.south
    nag = d.find((150, 214), margin=6, clear=5, minimum=4.5, region=S, nacre=20)
    places.append(dict(id='deep_longship', name='the Wreck of Naglfar', x=round(nag[0], 1), y=round(nag[1], 1), r=4.5))
    d.spots.add(nag[0], nag[1], 5.5)
    chap = d.find((214, 198), margin=6, clear=5, minimum=4.5, region=S, nacre=20)
    places.append(dict(id='deep_chapel', name='the Drowned Chapel', x=round(chap[0], 1), y=round(chap[1], 1), r=4.5))
    d.spots.add(chap[0], chap[1], 5.5)
    for p in places[-2:]:
        d.walked.append((p['x'], p['y'], 'place ' + p['id']))
    # harbour bells
    harbour = [('a1', 'the West Buoy Bell', HUB_X - 46, 206.0), ('a2', 'the Pearl Gate Bell', HUB_X, SOUTH_WALL + 9.0), ('a3', 'the East Buoy Bell', HUB_X + 46, 206.0)]
    for suffix, name, x, y in harbour:
        x, y = d.find((x, y), margin=5, clear=2, minimum=BELL_R, region=S, nacre=20)
        places.append(dict(id=f'deep_harbour_{suffix}', name=name, x=round(x, 2), y=round(y, 2), r=BELL_R, chain='deep_harbour', burn=CHAINS['deep_harbour']))
        d.spots.add(x, y, 3.5)
        d.walked.append((x, y, 'bell'))
    for chain in ('deep_net', 'deep_rans'):
        for k, cell in enumerate(sorted(bells[chain], key=lambda c: (c[1], c[0]))):
            x, y = bell_position(cell, chain, k)
            places.append(dict(id=f'{chain}_{k + 1}', name=f'the {BELL_LABELS[chain]} {ROMAN[k]}', x=x, y=y, r=BELL_R, chain=chain, burn=CHAINS[chain]))
            d.walked.append((x, y, 'bell'))
    # the places the new quests visit
    for spec in content.PLACES:
        kind, where = spec['where']
        if kind == 'gate':
            g = gates[where]
            x, y = (g['gate'][0] + g['arrival'][0]) / 2, (g['gate'][1] + g['arrival'][1]) / 2
        elif kind == 'cell':
            c, r = where
            x, y = d.find(cell_centre(c, r), margin=4, clear=.5, minimum=1.0, region=d.cell_region(c, r, 0))
        else:
            x, y = d.find(where, margin=5, clear=3, minimum=spec['r'], region=S, nacre=20)
        places.append(dict(id=spec['id'], name=spec['name'], x=round(x, 1), y=round(y, 1), r=spec['r']))
        d.spots.add(x, y, spec['r'] + 1)
        d.walked.append((x, y, 'place ' + spec['id']))
    byid = {p['id']: p for p in places}
    # the Empty Seat circle and the Ember Grave Cross keep their ids
    es_place = next(p for p in old['places'] if p['id'].startswith('es_08_'))
    ex, ey = d.find((150, 228), margin=6, clear=6, minimum=4, region=S, nacre=20)
    es = dict(es_place, x=round(ex, 1), y=round(ey, 1))
    d.spots.add(ex, ey, 5)
    d.walked.append((ex, ey, 'place es'))
    cxx, cyy = d.find((132, 184), margin=5, clear=7, minimum=3, region=S & (d.ys < 196) & (d.xs > 124), nacre=20)
    cross = dict(copy.deepcopy(old['crosses'][0]), x=round(cxx, 1), y=round(cyy, 1))
    d.spots.add(cxx, cyy, 4)
    d.walked.append((cxx, cyy, 'cross'))

    # ---- landmarks on the places
    for p in places:
        pid, x, y = p['id'], p['x'], p['y']
        if p.get('chain'):
            d.add('tidebell', x, y, .8, place=pid)
        elif pid == 'deep_longship':
            for dx, dy, v in [(-3.2, -1.5, 0), (-1.0, -2.4, 1), (1.2, -2.6, 2), (3.1, -1.4, 3), (4.0, 1.2, 0), (-4.0, 1.4, 1)]:
                d.add('shiprib', x + dx, y + dy, 1.3, v=v, place=pid)
        elif pid == 'deep_chapel':
            for k in range(6):
                a = k * math.pi / 5 + math.pi
                d.add('sunkencolumn', x + 5.2 * math.cos(a), y + 4.0 * math.sin(a) + 1.5, .55, v=k % 4, place=pid)
        elif pid == 'deep_pearlgate':
            for dx in (-7.0, 7.0):
                d.add('sunkencolumn', x + dx, SOUTH_WALL + 1.2, .55, v=1)
        elif pid == 'deep_garden':
            for k in range(6):
                a = k * 2 * math.pi / 6 + .4
                d.add('anemone', x + 3.4 * math.cos(a), y + 2.8 * math.sin(a), .5, v=k % 4)
        elif pid == 'deep_lr_lamp':
            d.add('pearllamp', x, y, .2, v=1, place=pid)
            for k in range(5):
                a = k * 2 * math.pi / 5 + .3
                d.add('anemone', x + 2.4 * math.cos(a), y + 2.2 * math.sin(a), .5, v=k % 4)
        elif pid == 'deep_gw_vents':
            for dx, dy in ((-2.2, -1.2), (2.0, 1.4), (0.2, 2.6)):
                d.add('vent', x + dx, y + dy, .4)
        elif pid == 'deep_dw_stones':
            for k in range(5):                                   # a ring with gaps wide enough to walk through
                a = k / 5 * 2 * math.pi + .3
                d.add('deeprock', x + 2.9 * math.cos(a), y + 2.9 * math.sin(a), .5, v=k % 4)
    for a, b in block_doors(doors, 'court'):             # columns flank each door of Rán's Court
        (ax, ay), (bx, by) = cell_centre(*(a if a not in court else b)), cell_centre(*(b if b in court else a))
        mx2, my2 = (ax + bx) / 2, (ay + by) / 2
        horizontal = abs(ax - bx) > abs(ay - by)
        for s in (-1, 1):
            d.add('sunkencolumn', mx2 + (0 if horizontal else s * 6.9), my2 + (s * 6.9 if horizontal else 0), .55, v=2, court=1)

    # ---- the trail: from Keelhaven's north edge through the Pearl Gate and the Net to the nearer Court door
    cells_route = trail(kept, doors, depth, outer)
    path = [(HUB_X, city['y0'] - 1.0), (HUB_X, SOUTH_WALL + 3.0)] + [tuple(round(v, 2) for v in cell_centre(*c)) for c in cells_route]
    for a, b in zip(path, path[1:]):
        for k in range(int(math.dist(a, b) / 2) + 1):
            t = k * 2 / max(math.dist(a, b), 1e-9)
            d.walked.append((a[0] + (b[0] - a[0]) * min(t, 1), a[1] + (b[1] - a[1]) * min(t, 1), 'road'))

    # ---- the elites and the spawn bands
    spawns = []
    spawns.append(dict(x=float(cx0), y=float(cy0), kind='kraken'))
    d.spots.add(cx0, cy0, 6)
    from scipy.spatial import cKDTree
    pts = [(x, y) for x, y, _ in d.walked]
    for c in [city] + content.camps(hamlets):
        for t in range(int(c['x0']), int(c['x1']) + 1, 2):
            pts += [(t, c['y0']), (t, c['y1'])]
        for u in range(int(c['y0']), int(c['y1']) + 1, 2):
            pts += [(c['x0'], u), (c['x1'], u)]
    tree = cKDTree(np.array(pts))
    # Hvitserk: the open Shallows, awareness + 3 tiles from everything walked, at least 26 tiles from the Naglfar's wreck so a visit does not pull him
    ok = S & (d.nacre >= 22) & (d.edge >= 8)
    cells = np.stack([d.xs[ok], d.ys[ok]], 1)
    dist, _ = tree.query(cells)
    good = dist >= AWARENESS['hvitserk'] + 3
    for pl in places:                                     # the elites keep well away from the places a solo quest sends a hero to
        good &= np.hypot(cells[:, 0] - pl['x'], cells[:, 1] - pl['y']) >= pl['r'] + 14
    want = (172, 186)
    score = np.where(good, -np.hypot(cells[:, 0] - want[0], cells[:, 1] - want[1]), -1e9)
    k = int(score.argmax())
    assert score[k] > -1e8, 'no clear ground for Hvitserk'
    hv = (float(cells[k, 0]), float(cells[k, 1]))
    spawns.append(dict(x=round(hv[0], 2), y=round(hv[1], 2), kind='hvitserk'))
    d.spots.add(hv[0], hv[1], 5)
    # the Ghostmaw: the deepest free corridor, two hops from the garden and one from every bell
    lair = next(c for c in sorted((c for c in depth if c not in BLOCK_OF and c not in taken | {garden}), key=lambda c: (-depth[c], c[1], c[0]))
                if hops[c][garden] >= 2 and all(hops[c][t] >= 1 for t in taken | {garden}))
    lx, ly = cell_centre(*lair)
    spawns.append(dict(x=round(lx, 2), y=round(ly, 2), kind='ghostmaw'))
    d.spots.add(lx, ly, 6)
    elites = [(cx0, cy0, 'kraken'), (hv[0], hv[1], 'hvitserk'), (lx, ly, 'ghostmaw')]

    keep = [(p['x'], p['y'], p['r'] + (5.0 if p.get('chain') else 6.0)) for p in places]
    keep += [(h['x'], h['y'], max(h['hw'], h['hh']) + 8) for h in hamlets.values()]
    keep += [(g['gate'][0], g['gate'][1], 15.0) for g in gates.values()]
    keep += [(longship['x'], longship['y'], 9.0), (ex, ey, 9.0), (cxx, cyy, 9.0)]
    BANDS = [('angler', 16, 9.0, 0), ('moray', 16, 9.0, 1), ('siren', 16, 9.0, 2), ('shellback', 14, 9.5, 3), ('draugr', 26, 9.0, 'wings')]
    for kind, count, spacing, where in BANDS:
        placed, tries = 0, 0
        cells_of_band = [c for c in sorted(depth) if c not in BLOCK_OF and band[c] == where] if where != 'wings' else []
        while placed < count and tries < 80000:
            tries += 1
            if where == 'wings':
                x, y = rng.uniform(12, n - 12), rng.uniform(SOUTH_WALL + 6, n - 12)
                if not d.south[int(y), int(x)] or d.nacre[int(y), int(x)] < 14 or (city['x0'] - 9 <= x <= city['x1'] + 9 and city['y0'] - 9 <= y <= city['y1'] + 9):
                    continue
            else:
                c = rng.choice(cells_of_band)
                x0, y0, x1, y1 = cell_box(*c)
                x, y = rng.uniform(x0 + 3.8, x1 - 3.8), rng.uniform(y0 + 3.8, y1 - 3.8)
                if not d.W[int(y), int(x)]:
                    continue
            if d.edge[int(y), int(x)] < 4 or any(math.hypot(x - a, y - b) < r for a, b, r in keep):
                continue
            if any(math.hypot(x - s['x'], y - s['y']) < (spacing if s['kind'] == kind else 7.0) for s in spawns):
                continue
            if any(math.hypot(x - e[0], y - e[1]) < AWARENESS[e[2]] + 3 for e in elites):
                continue
            if not d.spots.free(x, y, .4, 2.0):
                continue
            spawns.append(dict(x=round(x, 2), y=round(y, 2), kind=kind))
            placed += 1
        assert placed == count, f'only {placed} of {count} {kind}'
    # sleepers: the Empty Seat's shadow and the Ember Key's guardian keep their records
    for s in old['slimes']:
        if s['kind'] == 'es_foe_08':
            spawns.append(dict(s, x=round(ex + 2, 2), y=round(ey, 2)))
        elif s['kind'] == 'ember_firelord':
            spawns.append(dict(s, x=round(cxx - 2.5, 2), y=round(cyy, 2)))
    for q in spawns:
        d.spots.add(q['x'], q['y'], .4)

    # ---- scenery
    def free(x, y, r, margin):
        return d.spots.free(x, y, r, margin) and not any(math.hypot(x - p['x'], y - p['y']) < p['r'] + 1.2 for p in places) and \
            not any(math.hypot(x - s['x'], y - s['y']) < 3 for s in spawns)

    def put(kind, x, y, r, v):
        if not d.W[int(y), int(x)] or d.nacre[int(y), int(x)] < 2.5 or d.edge[int(y), int(x)] < r + 1.2:
            return False
        o = d.add(kind, x, y, r, v=v)
        return o

    def scatter_cells(kind, per_cell, r, margin=1.0):
        count = 0
        for cell in sorted(depth):
            k = per_cell(cell)
            x0, y0, x1, y1 = cell_box(*cell)
            for _ in range(k):
                for _try in range(40):
                    x, y = rng.uniform(x0 + r + 1, x1 - r - 1), rng.uniform(y0 + r + 1, y1 - r - 1)
                    if math.hypot(x - cx0, y - cy0) < 6 and cell in court and kind not in ('coral', 'anemone'):
                        continue
                    if cell in court and kind not in ('coral', 'anemone'):
                        continue
                    if cell in BLOCK_OF and BLOCK_OF[cell] != 'court':
                        continue                                   # the camps are dressed by hand
                    if free(x, y, r, margin) and put(kind, x, y, r, rng.randrange(4)):
                        count += 1
                        break
        return count

    def scatter_south(kind, count, r, margin=1.0):
        placed, tries = 0, 0
        while placed < count and tries < 60000:
            tries += 1
            x, y = rng.uniform(12, n - 12), rng.uniform(SOUTH_WALL + 4, n - 8)
            if not d.south[int(y), int(x)] or (city['x0'] - 2 <= x <= city['x1'] + 2 and city['y0'] - 2 <= y <= city['y1'] + 2):
                continue
            if any(h['x'] - h['hw'] - 1 <= x <= h['x'] + h['hw'] + 1 and h['y'] - h['hh'] - 1 <= y <= h['y'] + h['hh'] + 1 for h in hamlets.values()):
                continue
            if free(x, y, r, margin) and put(kind, x, y, r, rng.randrange(4)):
                placed += 1
        assert placed >= count * .9, f'only {placed} of {count} {kind}'

    scatter_cells('kelp', lambda c: 2 + int(hash2(c[0], c[1], 5) * 3), .35)
    scatter_cells('coral', lambda c: 1 + int(hash2(c[0], c[1], 6) * 2.4), .6, margin=1.2)
    scatter_cells('deeprock', lambda c: int(hash2(c[0], c[1], 7) * 2.2), .8, margin=1.4)
    scatter_cells('clam', lambda c: 1 if hash2(c[0], c[1], 8) < .3 else 0, .55, margin=1.4)
    scatter_cells('vent', lambda c: 1 if hash2(c[0], c[1], 9) < .22 else 0, .4, margin=2.0)
    scatter_cells('anchor', lambda c: 1 if hash2(c[0], c[1], 12) < .12 else 0, .5, margin=1.6)
    scatter_cells('shiprib', lambda c: 1 if hash2(c[0], c[1], 13) < .1 else 0, 1.3, margin=1.8)
    scatter_cells('anemone', lambda c: 5 if c in court else 0, .5, margin=1.2)
    scatter_south('kelp', 150, .35)
    scatter_south('coral', 90, .6, margin=1.2)
    scatter_south('deeprock', 62, .8, margin=1.4)
    scatter_south('clam', 24, .55, margin=1.4)
    scatter_south('vent', 18, .4, margin=2.0)
    scatter_south('anchor', 14, .5, margin=1.6)
    scatter_south('shiprib', 14, 1.3, margin=1.8)
    scatter_south('sunkencolumn', 12, .55, margin=1.8)
    # pearl lamps beside the trail
    walked_len, lamp_every = 0.0, 13.0
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        while walked_len < length:
            side = 1 if int(walked_len + ax + ay) % 2 else -1
            x, y = ax + ux * walked_len - uy * 2.6 * side, ay + uy * walked_len + ux * 2.6 * side
            if free(x, y, .2, .6) and d.W[int(y), int(x)] and not (city['x0'] <= x <= city['x1'] and city['y0'] <= y <= city['y1']):
                d.add('pearllamp', x, y, .2, v=int(hash2(int(x), int(y), 4) * 3))
            walked_len += lamp_every
        walked_len -= length

    # ---- write the zone
    zone['spawn'] = spawn
    zone['shape']['placeAtSpawn'] = True          # saved characters are moved to the spawn (zone_shapes_migrate.py): this is not a rigid shift
    zone.pop('bounds', None)
    zone['city'] = city
    zone['npcs'] = npcs
    zone['places'] = [es] + places
    zone['quests'] = copy.deepcopy(old['quests'])
    zone['crosses'] = [cross]
    zone['slimes'] = spawns
    voids = d.zs.void_pieces(d.W)
    for o in voids:
        o.pop('layout', None)
    zone['objects'] = voids + d.objects
    zone['paths'] = [[list(p) for p in path]]
    zone['atlasPaths'] = []
    for p in zone['portals']:
        if p['id'] == 'deep_longship':
            p.update(x=longship['x'], y=longship['y'])
        else:
            g = gates[p['id']]
            p.update(x=g['gate'][0], y=g['gate'][1], walk=g['walk'])
    zone['exitRoutes'] = [dict(portal=pid, points=[list(g['gate']), list(g['arrival'])]) for pid, g in gates.items()]
    names = ['The Pearl Shallows', 'The Naglfar Flats', 'The Chapel Reach', 'The Lantern Maze', 'The Moray Gardens', 'The Siren Halls', 'The Shellback Deeps', "Rán's Court"]
    region = np.zeros((n, n), np.int16)
    region[d.south] = 1 + (d.xs[d.south] >= 130).astype(np.int16) + (d.xs[d.south] >= 186).astype(np.int16)
    for cell in kept:
        x0, y0, x1, y1 = cell_box(*cell)
        region[int(y0 - 1.5):int(y1 + 1.5), int(x0 - 1.5):int(x1 + 1.5)] = 8 if cell in court else 4 + band.get(cell, 3 if cell in BLOCK_OF else 0)
    zone['regions'] = dict(names=names, spans=ground_spans(region, d.W))
    content.install(zone, hamlets, [p for p in places if p['id'] in {s['id'] for s in content.PLACES}])
    arrivals = {'maelstrom_down': gates['maelstrom_up']['arrival'], 'nacre_deep_gate': gates['nacre_gate']['arrival'], 'path_13_8': gates['path_8_13']['arrival'],
                'keel_return': (longship['x'], longship['y'] + 5), 'keel_clear': (longship['x'], longship['y'] + 5)}
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals:
                p['tx'], p['ty'] = arrivals[p['id']]
    if write:
        content.record_mailboxes(zone, hamlets, ROOT / 'world/mailboxes.txt')
    d.bells, d.gates, d.hamlets, d.places, d.band, d.hops, d.doors, d.depth = bells, gates, hamlets, places, band, hops, doors, depth
    d.city, d.spawn, d.elites, d.lair, d.garden, d.cdoor, d.court_centre = city, spawn, elites, lair, garden, cdoor, (cx0, cy0)
    problems = check(d, zone, fen)
    stats = dict(kept=len(kept), dropped=len(d.dropped), walls=len(walls), massif=len(massif), objects=len([o for o in zone['objects'] if o['kind'] != 'void']),
                 voids=len(voids), spawns=len(spawns), quests=len(zone['quests']), maxdepth=max(depth.values()), elites=[(k, round(x), round(y)) for x, y, k in elites])
    if problems:
        if os.environ.get('DEEP_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


# ---- checks ------------------------------------------------------------------------------------------------------------------------------
def cellat(grid, x, y):
    return grid[int(y / STEP), int(x / STEP)]


def probe(blocked, reach, p):
    """Where a hero stands to be in a place: its middle, or a point just beside it when a landmark stands there. Must be reachable."""
    for dx, dy in ((0, 0), (0, 2.0), (2.0, 0), (0, -2.0), (-2.0, 0), (1.5, 1.5), (-1.5, 1.5)):
        x, y = p['x'] + dx, p['y'] + dy
        if not blocked[int(y / STEP), int(x / STEP)] and reach[int(y / STEP), int(x / STEP)]:
            return x, y
    raise AssertionError(f"{p['id']} has no free point to stand on")


def check(d, zone, fen):
    """Everything a hero must reach is reachable, the Net closes where it should, every bell chain can be rung in time (and not too easily), and nothing
    stands where it should not."""
    problems = []
    n = d.n
    sx, sy = d.spawn['x'], d.spawn['y']
    full, blocked = fen.flood(zone, (sx, sy))
    probes = {}
    for p in zone['places']:
        try:
            probes[p['id']] = probe(blocked, full, p)
        except AssertionError as e:
            problems.append(str(e))
    targets = [(x['id'], x['x'], x['y']) for x in zone['npcs']] + [(s['kind'], s['x'], s['y']) for s in zone['slimes']] + [(pid, x, y) for pid, (x, y) in probes.items()]
    for pid, g in d.gates.items():
        targets += [(pid + ' arrival', *g['arrival']), (pid + ' gate', g['gate'][0] - g['walk'][0] * 2, g['gate'][1] - g['walk'][1] * 2)]
    for name, x, y in targets:
        if not cellat(full, x, y):
            problems.append(f'{name} at ({x}, {y}) is unreachable from the spawn')
    # the Net has one door: closing it cuts off everything inside and nothing in the Shallows
    door_x = OX + (ENTRY[0] + .5) * PITCH
    reach, _ = fen.flood(zone, (sx, sy), [(door_x, SOUTH_WALL, 8.0)])
    inside = [t for t in targets if t[2] < SOUTH_WALL - 1]
    outside = [t for t in targets if t[2] > SOUTH_WALL + 12]
    if any(cellat(reach, x, y) for _, x, y in inside):
        problems.append('closing the Pearl Gate leaves part of the Net reachable: ' + str([t[0] for t in inside if cellat(reach, t[1], t[2])][:6]))
    if not all(cellat(reach, x, y) for _, x, y in outside):
        problems.append('closing the Pearl Gate cuts off part of the Shallows: ' + str([t[0] for t in outside if not cellat(reach, t[1], t[2])][:6]))
    # Rán's Court has exactly two doors
    seals = []
    for a, b in block_doors(d.doors, 'court'):
        (ox, oy), (ix, iy) = cell_centre(*a), cell_centre(*b)
        seals.append(((ox + ix) / 2, (oy + iy) / 2, 8.0))
    both, _ = fen.flood(zone, (sx, sy), seals)
    one = [fen.flood(zone, (sx, sy), [s])[0] for s in seals]
    boss = d.court_centre
    if cellat(both, *boss):
        problems.append('the Kraken can be reached with both Court doors closed')
    for k, r in enumerate(one):
        if not cellat(r, *boss):
            problems.append(f'closing only Court door {k} cuts off the Kraken: the doors are not independent')
    for name, x, y in targets:
        c = cell_of(x, y)
        if c in BLOCKS['court'] or name == 'kraken' or any(math.hypot(x - sx_, y - sy_) < 10.0 for sx_, sy_, _ in seals):
            continue
        if not cellat(both, x, y):
            problems.append(f'{name} is cut off by the Court doors')
    # every spawn stands in the cell quartile of its kind
    want_band = {'angler': 0, 'moray': 1, 'siren': 2, 'shellback': 3}
    for s in zone['slimes']:
        if s['kind'] in want_band:
            c = cell_of(s['x'], s['y'])
            if d.band.get(c) != want_band[s['kind']]:
                problems.append(f"a {s['kind']} stands in a cell of quartile {d.band.get(c)} at ({s['x']}, {s['y']})")
        elif s['kind'] == 'draugr' and s['y'] < SOUTH_WALL:
            problems.append(f"a draugr stands in the Net at ({s['x']}, {s['y']})")
    # bells: every chain's best tour is a fraction of what the slowest class walks while the first bell rings
    chains = {}
    for p in zone['places']:
        if p.get('chain'):
            chains.setdefault(p['chain'], []).append(p)
    for chain, items in chains.items():
        if len(items) != BELLS[chain]:
            problems.append(f'{chain} has {len(items)} bells')
        spots = [probes[p['id']] for p in items]
        dist = distance_fields(blocked, spots)
        at = [(int(y / STEP), int(x / STEP)) for x, y in spots]
        best = min(sum(dist[a][at[b]] for a, b in zip(order, order[1:])) for order in itertools.permutations(range(len(items))))
        window = SPEED * CHAINS[chain]
        if not .47 <= best / window <= .78:
            problems.append(f'{chain}: the best tour is {best:.0f} tiles, {best / window:.0%} of the {window:.0f} the slowest hero covers in {CHAINS[chain]} s (want 47-78 %)')
        if min(dist[a][at[b]] for a in range(len(items)) for b in range(len(items)) if a != b) < 12:
            problems.append(f'{chain}: two bells are closer than 12 tiles')
        d.tours = getattr(d, 'tours', {})
        d.tours[chain] = round(best / window, 2)
    # people stand on free ground
    soft = fen.obstacle_grid(zone, STEP, margin=.35)
    for x in zone['npcs']:
        if cellat(soft, x['x'], x['y']):
            problems.append(f"{x['id']} stands inside scenery at ({x['x']}, {x['y']})")
        if not d.W[int(x['y']), int(x['x'])]:
            problems.append(f"{x['id']} stands off the floor")
    for name, (x, y) in [(pid + ' arrival', g['arrival']) for pid, g in d.gates.items()] + [('spawn', (sx, sy))]:
        if cellat(blocked, x, y):
            problems.append(f'the {name} is blocked')
    for p in zone['places']:
        if p['id'] in probes and math.hypot(probes[p['id']][0] - p['x'], probes[p['id']][1] - p['y']) > p['r'] - .5:
            problems.append(f"{p['id']} cannot be stood in")
    # the elites keep clear of everything walked
    for ex, ey, kind in d.elites:
        near = min((math.hypot(ex - x, ey - y), w) for x, y, w in d.walked if w not in ('road',) or kind != 'kraken')
        if kind != 'kraken' and near[0] < AWARENESS[kind] + 3:
            problems.append(f'{kind} stands {near[0]:.1f} tiles from a {near[1]}')
    for e in [s for s in zone['slimes'] if s['kind'] in ('hvitserk', 'ghostmaw')]:
        for pl in zone['places']:
            need = pl['r'] + (10.0 if pl.get('chain') else 12.0)
            if math.hypot(e['x'] - pl['x'], e['y'] - pl['y']) < need:
                problems.append(f"{e['kind']} stands within {need:.0f} of {pl['id']}")
    live = [s for s in zone['slimes'] if not s.get('ambush')]
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if math.hypot(a['x'] - b['x'], a['y'] - b['y']) < 6.0:
                problems.append(f"{a['kind']} and {b['kind']} stand within 6 at ({a['x']}, {a['y']})")
    for s in zone['slimes']:
        if cellat(blocked, s['x'], s['y']):
            problems.append(f"{s['kind']} at ({s['x']}, {s['y']}) stands in scenery")
        if d.nacre[int(s['y']), int(s['x'])] < 7:
            problems.append(f"{s['kind']} stands within 7 tiles of the Nacrehold border")
        if not d.W[int(s['y']), int(s['x'])]:
            problems.append(f"{s['kind']} stands off the floor")
        for pid, g in d.gates.items():
            if math.hypot(s['x'] - g['arrival'][0], s['y'] - g['arrival'][1]) < 8:
                problems.append(f"{s['kind']} is within 8 of the arrival of {pid}")
        if (d.city['x0'] - 8 <= s['x'] <= d.city['x1'] + 8 and d.city['y0'] - 8 <= s['y'] <= d.city['y1'] + 8):
            problems.append(f"{s['kind']} at ({s['x']}, {s['y']}) is within 8 of Keelhaven")
    for o in zone['objects']:
        if o['kind'] in ('house', 'chapel', 'stall', 'fountain', 'lamp', 'bench', 'noticeboard', 'tent') and d.nacre[int(o['y']), int(o['x'])] < 20:
            problems.append(f"{o['kind']} at ({o['x']}, {o['y']}) stands within 20 tiles of the Nacrehold border")
    cover = np.zeros((n, n), np.int16)
    for o in zone['objects']:
        if o['kind'] == 'void':
            x0, x1 = int(round(o['x'] - o['width'] / 2)), int(round(o['x'] + o['width'] / 2))
            y0, y1 = int(round(o['y'] - o['depth'] / 2)), int(round(o['y'] + o['depth'] / 2))
            cover[y0:y1, x0:x1] += 1
    if not (cover[~d.W] == 1).all() or (cover[d.W] != 0).any():
        problems.append('void does not cover exactly the cells that are not floor')
    return problems


# ---- the picture -----------------------------------------------------------------------------------------------------------------------
def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = zone['size']
    img = Image.new('RGB', (n * scale, n * scale), (5, 10, 20))
    dr = ImageDraw.Draw(img)
    for j in range(n):
        for i in range(n):
            if d.F[j, i]:
                dr.rectangle([i * scale, j * scale, (i + 1) * scale - 1, (j + 1) * scale - 1], fill=(55, 105, 115) if d.W[j, i] else (140, 60, 90))
    colours = {'reefwall': (225, 150, 190), 'kelp': (40, 150, 80), 'coral': (240, 120, 100), 'deeprock': (110, 110, 130), 'pearllamp': (255, 240, 150),
               'anemone': (200, 90, 220), 'clam': (230, 230, 230), 'sunkencolumn': (220, 220, 235), 'shiprib': (170, 130, 90), 'vent': (250, 190, 90),
               'house': (190, 120, 80), 'chapel': (220, 130, 110), 'tent': (200, 170, 110), 'lamp': (255, 240, 120), 'stall': (210, 170, 90), 'tidebell': (255, 215, 0)}
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
    kc = {'angler': (240, 240, 70), 'moray': (255, 150, 0), 'siren': (210, 70, 210), 'shellback': (70, 210, 255), 'draugr': (230, 70, 70)}
    for s in zone['slimes']:
        col = kc.get(s['kind'], (255, 255, 255))
        r = 9 if s['kind'] in ('kraken', 'hvitserk', 'ghostmaw') else 3 if s.get('ambush') else 5
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
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])
        print(stats, getattr(d, 'tours', {}))
        return
    raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
