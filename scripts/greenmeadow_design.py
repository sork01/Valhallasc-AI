#!/usr/bin/env python3
"""Greenmeadow as an authored map (zone 0 of the shapes pilot): no filler land, the whole outline used.

Runs as the last step of `zone_shapes.py apply`, after the seams, the Skaldholm vault and the wall exist, so the outline, the
borders and every crossing stay exactly as they were. It replaces all loose scenery, every spawn and the trails with the plan
below, which follows the owner's painted atlas (client/assets/world-atlas-painted.png; tile = atlas px - shape.T): the same road
lattice, the ponds in the north-east, the big tree clumps in the west and the beach on the south coast.

Fixed, never touched: Alderhaven and its NPCs, `cityEntrances`, the spawn point, the Ember Grave Cross and its sleeper, the Empty
Seat circles, the seam portals, the vault, the wall, the void.

    python3 scripts/greenmeadow_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import json
import math
import random
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import greenmeadow_content as content  # noqa: E402
MAP = ROOT / 'world/map.txt'
TAG = 'meadow_design_v1'
SEED = 20261106

# ---- the plan -------------------------------------------------------------------------------------------------------
# Every land cell belongs to the region of its nearest seed (seeds warped by noise), so no ground is left over.
REGIONS = {
    'home':      dict(name='Alderhaven Fields', seeds=[(250, 190), (262, 222), (232, 214), (285, 190)]),
    'wallside':  dict(name='The Wallside Pasture', seeds=[(125, 142), (165, 140), (205, 140), (232, 118)]),
    'grove':     dict(name='The Oldgrove', seeds=[(150, 165), (135, 195), (175, 205), (195, 170)]),
    'downs':     dict(name='The Westerling Downs', seeds=[(25, 222), (60, 215), (95, 190), (85, 240)]),
    'strand':    dict(name='The Saltgrass Strand', seeds=[(115, 268), (160, 262), (205, 275), (245, 283)]),
    'scarp':     dict(name='The Ironhide Scarp', seeds=[(262, 112), (300, 118), (340, 120), (290, 148)]),
    'meres':     dict(name='The Three Meres', seeds=[(372, 135), (365, 170), (330, 165)]),
    'orchard':   dict(name='The Applewick Orchards', seeds=[(320, 225), (350, 215), (385, 225), (345, 255)]),
    'hollowend': dict(name='Hollowend', seeds=[(300, 275), (345, 295), (392, 300), (405, 265)]),
}

# Traced from the painted atlas (tile coordinates). Alderhaven has a north and a south gate, so the east-west road of the painting
# passes under its south wall.
ROADS = [
    # the Great Road along the south of the country, Stonefold to the Canopy border
    [(92, 224), (112, 238), (135, 243), (165, 245), (195, 245), (225, 243), (250, 241), (275, 240), (300, 241), (325, 245), (345, 247), (375, 252), (396, 254)],
    # the king's way: Alderhaven's south gate to the Great Road and on to the Strand
    [(250, 202), (250, 214), (250, 241)],
    [(205, 245), (196, 262), (190, 270)],
    # the Alderhaven road, east and west of the south gate
    [(250, 207), (232, 206), (207, 207), (192, 186)],
    [(250, 207), (272, 206), (296, 198), (318, 188), (352, 186)],
    # the north road and the Crags way, as painted
    [(250, 172), (250, 158), (250, 143), (232, 151), (212, 164), (192, 186), (172, 186), (160, 192)],
    [(250, 143), (276, 138), (300, 134), (335, 126), (382, 118)],
    [(250, 143), (254, 128), (258, 112)],
    # the trunk from the fork to the Great Road, and the Oldgrove ride
    [(192, 186), (205, 212), (205, 245)],
    [(160, 192), (136, 202), (135, 243)],
    [(136, 202), (134, 170), (126, 156)],
    # the Skaldholm road: from the vault down through the pasture to the fork
    [(161.5, 124.5), (163, 138), (172, 150), (178, 168), (192, 186)],
    # the Downs way and the shore path
    [(92, 224), (66, 218), (40, 222)],
    [(112, 238), (102, 252), (94, 260)],
    # the east: lower road, Hollowend, and the Meres lane
    [(300, 241), (320, 252), (350, 265), (372, 282), (392, 300)],
    [(232, 262), (272, 266), (312, 267), (350, 265)],
    [(196, 262), (232, 262)],
    [(352, 186), (372, 172), (392, 150)],
    [(345, 247), (345, 232)],
    [(352, 186), (345, 210), (345, 232)],
    [(335, 126), (352, 150), (352, 186)],
]

PONDS = [(282, 117, 11, 6), (376, 144, 14, 8), (367, 162, 11, 6), (331, 146, 10, 6), (118, 216, 9, 6), (56, 240, 8, 5), (312, 300, 10, 6)]

HAMLETS = {
    'stonefold': dict(name='Stonefold', x=92, y=224, hw=15, hh=12),
    'saltby':    dict(name='Saltby', x=190, y=272, hw=16, hh=9),
    'applewick': dict(name='Applewick', x=345, y=232, hw=14, hh=12),
}

# Hunting grounds. Difficulty comes only from which kind stands where (a spawn has no level): green 2, blue and pink 3, yellow 4,
# beetle 5. The Fields are the gentlest; it climbs outward, to the Scarp under the Crags and to Hollowend.
SPAWNS = {
    'home':      {'green': 30, 'blue': 4},
    'wallside':  {'green': 14, 'blue': 12},
    'grove':     {'blue': 22, 'pink': 12},
    'downs':     {'pink': 22, 'blue': 8, 'yellow': 6},
    'strand':    {'blue': 20, 'green': 8},
    'scarp':     {'beetle': 15, 'yellow': 15},
    'meres':     {'pink': 15, 'yellow': 10},
    'orchard':   {'yellow': 22, 'pink': 6},
    'hollowend': {'yellow': 12, 'beetle': 7, 'pink': 6},
}
# The King Slime's two possible risings and the three elites' grounds.
KING = [(236, 128), (118, 224)]

R = {'tree': .42, 'bush': .30, 'rock': .40, 'oak_tree': 1.0, 'birch_tree': .68, 'apple_tree': .9, 'willow_tree': .85, 'hawthorn_bush': .34,
     'wildflowers': .12, 'haystack': .58, 'cairn_boulder': 1.3, 'flowers': .55}


class Noise:
    def __init__(self, seed):
        self.t = np.random.default_rng(seed).random((64, 64))

    def __call__(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        i, j = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = x - i, y - j
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        t = self.t
        a, b = t[j % 64, i % 64], t[j % 64, (i + 1) % 64]
        c, d = t[(j + 1) % 64, i % 64], t[(j + 1) % 64, (i + 1) % 64]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(noise, x, y, s):
    return noise(x * s, y * s) * .65 + noise(x * s * 2.3 + 17, y * s * 2.3 + 5) * .35


def seg_field(pts, xs, ys):
    """Distance from every cell centre to a polyline."""
    best = np.full(xs.shape, 1e9)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
        best = np.minimum(best, np.hypot(xs - ax - t * dx, ys - ay - t * dy))
    return best


class Grid:
    """Spatial hash of solid objects, for spacing checks."""
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


class Designer:
    def __init__(self, world):
        self.w = world
        self.n = world['size']
        self.floor = np.array([[c == '#' for c in row] for row in world['shapeFloor']])
        self.ys, self.xs = np.mgrid[0:self.n, 0:self.n] + .5
        self.rng = random.Random(SEED)
        self.noise = Noise(SEED)
        self.grid = Grid()
        self.objects = []
        self.road = np.full((self.n, self.n), 1e9)
        for road in ROADS:
            self.road = np.minimum(self.road, seg_field(road, self.xs, self.ys))
        # one cell-wide ring of shore keeps a walker's edge clear of scenery
        from zone_shapes import erode
        self.inner = erode(self.floor, 3)
        self.seam = np.full((self.n, self.n), 1e9)
        for p in world['portals']:
            if p.get('seam'):
                self.seam = np.minimum(self.seam, seg_field(p['seam']['points'], self.xs, self.ys))
        self.blocked = np.zeros((self.n, self.n), bool)   # no loose scenery or spawn here
        self.region = self.make_regions()
        self.zone_ids = list(REGIONS)

    def make_regions(self):
        wx = self.xs + (fbm(self.noise, self.xs, self.ys, .035) - .5) * 44
        wy = self.ys + (fbm(self.noise, self.xs + 90, self.ys + 40, .035) - .5) * 44
        best = np.full((self.n, self.n), 1e9)
        out = np.zeros((self.n, self.n), int)
        for i, r in enumerate(REGIONS.values()):
            for sx, sy in r['seeds']:
                d = np.hypot(wx - sx, wy - sy)
                out[d < best] = i
                best = np.minimum(best, d)
        return out

    def mask(self, name):
        return (self.region == list(REGIONS).index(name)) & self.floor

    def add(self, kind, x, y, r=None, solid=True, **extra):
        r = R.get(kind, 0) if r is None else r
        o = {'kind': kind, 'x': round(float(x), 2), 'y': round(float(y), 2), 'r': r, 'v': extra.pop('v', self.rng.randrange(4)), **extra, 'layout': TAG}
        self.objects.append(o)
        if solid:
            self.grid.add(o['x'], o['y'], max(r, (extra.get('width', 0) + extra.get('depth', 0)) / 4))
        return o

    def block(self, x0, y0, x1, y1):
        self.blocked[max(int(y0), 0):int(y1) + 1, max(int(x0), 0):int(x1) + 1] = True

    def block_disc(self, x, y, r):
        self.blocked |= np.hypot(self.xs - x, self.ys - y) < r

    def scatter(self, kinds, count, where, gap=.65, road=2.6):
        """`count` objects of the weighted `kinds` over the cells of `where`."""
        pts = np.argwhere(where & self.inner & ~self.blocked & (self.road > road))
        if not len(pts):
            return 0
        placed = 0
        for _ in range(count * 30):
            if placed == count:
                break
            j, i = pts[self.rng.randrange(len(pts))]
            x, y = i + self.rng.random(), j + self.rng.random()
            k = self.rng.choice(kinds)
            if self.grid.free(x, y, R[k], gap):
                self.add(k, x, y)
                placed += 1
        return placed

    # ---- features ---------------------------------------------------------------------------------------------------
    def pond(self, cx, cy, rx, ry):
        """A pond is a union of water circles (solid); the ground pass draws the mere around them."""
        step = 3.0
        y = cy - ry
        row = 0
        while y <= cy + ry:
            x = cx - rx + (step / 2 if row % 2 else 0)
            while x <= cx + rx:
                wob = 1 + (fbm(self.noise, x, y, .2) - .5) * .5
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= wob:
                    self.add('water', x, y, r=2.3)
                x += step
            y += step * .866
            row += 1
        self.block_disc(cx, cy, max(rx, ry) + 2.4)

    def hedge(self, pts, step=1.25, gaps=()):
        """A hedgerow: a line of bushes, broken at `gaps` (points where a walker gets through)."""
        for a, b in zip(pts, pts[1:]):
            ln = math.dist(a, b)
            for s in range(int(ln / step) + 1):
                x = a[0] + (b[0] - a[0]) * s * step / ln + self.rng.uniform(-.2, .2)
                y = a[1] + (b[1] - a[1]) * s * step / ln + self.rng.uniform(-.2, .2)
                if any(math.dist((x, y), g) < 2.6 for g in gaps) or self.road[int(y), int(x)] < 2.4:
                    continue
                if self.inner[int(y), int(x)] and not self.blocked[int(y), int(x)]:
                    self.add('hawthorn_bush', x, y)

    def field(self, x0, y0, x1, y1, stacks=3, scarecrow=False):
        """A tilled plot with a hedge on three sides (open on the road side) and haystacks."""
        self.ground[int(y0):int(y1), int(x0):int(x1)] = GROUND['field']
        gate = ((x0 + x1) / 2, y1)
        self.hedge([(x0, y1), (x0, y0), (x1, y0), (x1, y1)], gaps=[gate])
        for _ in range(stacks):
            x, y = self.rng.uniform(x0 + 2, x1 - 2), self.rng.uniform(y0 + 2, y1 - 2)
            if self.grid.free(x, y, .6, 1):
                self.add('haystack', x, y)
        if scarecrow:
            self.add('wicker_post', (x0 + x1) / 2, (y0 + y1) / 2, r=.9)
        self.block(x0, y0, x1, y1)

    def orchard(self, x0, y0, x1, y1):
        """Apple trees in rows, with aisles a player can walk down."""
        y = y0
        while y < y1:
            x = x0 + self.rng.uniform(0, 1)
            while x < x1:
                i, j = int(x), int(y)
                if self.inner[j, i] and self.road[j, i] > 3 and not self.blocked[j, i] and self.grid.free(x, y, .9, .8):
                    self.add('apple_tree', x + self.rng.uniform(-.25, .25), y + self.rng.uniform(-.25, .25))
                x += 5.5
            y += 6.5

    def stone_ring(self, cx, cy, radius, stones=9):
        for k in range(stones):
            a = k / stones * math.tau + .35
            x, y = cx + math.cos(a) * radius, cy + math.sin(a) * radius
            if self.road[int(y), int(x)] > 2.2:
                self.add('cairn_boulder', x, y, r=.9)
        self.block_disc(cx, cy, radius + 1.5)

    def hamlet_ground(self, h):
        self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)

    def build(self):
        w, rng = self.w, self.rng
        city = w['city']
        self.ground = np.zeros((self.n, self.n), np.uint8)
        # Everything Alderhaven owns stays, and stays clear.
        self.block(city['x0'] - 3, city['y0'] - 3, city['x1'] + 3, city['y1'] + 3)
        keep_kinds = ('void', 'rampart', 'tower')
        kept = []
        for o in w['objects']:
            inside = city['x0'] - 1 <= o['x'] <= city['x1'] + 1 and city['y0'] - 1 <= o['y'] <= city['y1'] + 1
            if o['kind'] in keep_kinds or inside:
                kept.append(o)
                if o['kind'] not in ('void',) and o['r'] + o.get('width', 0) > 0:
                    self.grid.add(o['x'], o['y'], max(o['r'], o.get('width', 0) / 2))
        for p in w['places'] + w['crosses']:
            self.block_disc(p['x'], p['y'], 5)
        for p in w['portals']:
            if not p.get('seam'):
                self.block_disc(p['x'], p['y'], 9)
                self.block_disc(p['x'], p['y'] + 8, 9)
        self.block_disc(w['spawn']['x'], w['spawn']['y'], 5)
        for e in w['cityEntrances']:
            for a in e['points']:
                self.block_disc(a[0], a[1], 4)
        self.blocked |= self.seam < 2.5
        for x, y in KING:
            self.block_disc(x, y, 4)
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 7)
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 2)
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3)
        for h in HAMLETS.values():
            self.hamlet_ground(h)

        # ponds first: everything else keeps away from them
        for p in PONDS:
            self.pond(*p)

        content.dress(self, HAMLETS)
        self.lay_ground()
        self.lay_farms()
        self.lay_regions()
        return kept + self.objects

    def lay_ground(self):
        """Ground classes beside plain grass. None within 16 tiles of a seam: the other side blends toward plain meadow."""
        G, g = GROUND, self.ground
        far = self.seam > 16 + fbm(self.noise, self.xs, self.ys, .09) * 14
        coast = self.coast_distance()
        rough = (fbm(self.noise, self.xs, self.ys, .11) - .5) * 9
        g[self.mask('strand') & (coast + rough < 26) & far] = G['sand']
        g[self.floor & (coast + rough * .5 < 7) & far & (self.xs > 100) & (self.xs < 300)] = G['sand']
        g[self.mask('downs') & far] = G['downs']
        g[self.mask('grove') & far] = G['forest']
        g[self.mask('hollowend') & far] = G['forest']
        g[self.mask('orchard') & far] = G['clover']
        g[self.mask('scarp') & far] = G['scarp']

    def coast_distance(self):
        out = np.full((self.n, self.n), 1e9)
        for e in self.w['shape']['edges']:
            if e['kind'] == 'coast':
                out = np.minimum(out, seg_field(e['points'], self.xs, self.ys))
        return out

    def lay_farms(self):
        """Alderhaven's own plots, south of the town, hedged, with the king's way through the middle."""
        for box, crow in (((216, 212, 240, 232), True), ((260, 212, 288, 232), False), ((216, 248, 244, 258), False), ((256, 248, 288, 260), True),
                          ((268, 170, 296, 188), True), ((208, 172, 230, 192), False)):
            self.field(*box, stacks=rng_stacks(self.rng), scarecrow=crow)

    def lay_regions(self):
        rng = self.rng
        dense = fbm(self.noise, self.xs + 200, self.ys + 300, .05)

        # The Oldgrove: real woodland, thinning into glades. The Hoar Oak stands in the biggest glade.
        hoar = (150, 186)
        self.block_disc(*hoar, 11)
        self.add('oak_tree', *hoar, r=1.6)
        self.ring(hoar, 9, 7, 'flowers')
        for spot in ((128, 172), (172, 216)):
            self.block_disc(*spot, 8)   # dens and clearings
        grove = self.mask('grove')
        self.scatter(['oak_tree', 'oak_tree', 'tree', 'tree', 'birch_tree'], 520, grove & (dense > .42), gap=.9)
        self.scatter(['tree', 'bush', 'birch_tree', 'hawthorn_bush'], 260, grove, gap=.8)
        self.scatter(['bush', 'wildflowers'], 120, grove & (dense <= .42), gap=.6)

        # The Wallside Pasture: open grazing under Skaldholm's wall, drystone cairns and solitary oaks along the lanes.
        side = self.mask('wallside')
        self.scatter(['oak_tree'], 30, side, gap=8)
        self.scatter(['bush', 'hawthorn_bush'], 150, side & (dense > .5), gap=.8)
        self.scatter(['rock', 'wildflowers', 'wildflowers'], 220, side, gap=.8)

        # The Westerling Downs: long pale grass, standing stones, wind-bent thorns.
        self.stone_ring(58, 222, 8)
        self.stone_ring(30, 222, 5, stones=6)
        downs = self.mask('downs')
        self.scatter(['cairn_boulder'], 26, downs, gap=9)
        self.scatter(['rock', 'rock', 'hawthorn_bush'], 300, downs, gap=1.2)
        self.scatter(['birch_tree', 'tree'], 60, downs & (dense > .55), gap=2)
        self.scatter(['wildflowers'], 160, downs, gap=.8)

        # The Saltgrass Strand: dunes and rock pools, the Tidewrack lying on the sand.
        wreck = (136, 276)
        self.block_disc(*wreck, 7)
        for dx, dy in ((-3, -1), (-1, 1), (1, -2), (3, 0), (4, 2), (-4, 2)):
            self.add('barrels', wreck[0] + dx, wreck[1] + dy, r=0, width=.6, depth=.6, color='', label='')
        for k in range(10):
            a = k / 10 * math.tau
            self.add('rock', wreck[0] + math.cos(a) * 6.2, wreck[1] + math.sin(a) * 3.8)
        strand = self.mask('strand')
        self.scatter(['rock'], 170, strand, gap=1.4)
        self.scatter(['bush', 'hawthorn_bush'], 170, strand & (self.ground == 0), gap=1)
        self.scatter(['tree'], 50, strand & (self.ground == 0), gap=4)

        # The Ironhide Scarp: bare stony ground rising to the Crags, boulder fields the beetles shelter in.
        scarp = self.mask('scarp')
        self.scatter(['rock'], 520, scarp & (dense > .4), gap=.8)
        self.scatter(['cairn_boulder'], 40, scarp, gap=6)
        self.scatter(['tree', 'bush'], 120, scarp & (self.seam > 12), gap=1.5)

        # The Three Meres: willows at the water, reeds of flowers, the old watermill between the two east meres.
        mill = (349, 158)
        self.block_disc(*mill, 7)
        self.add('watermill', *mill, r=0, width=6, depth=4)
        meres = self.mask('meres')
        water = np.full((self.n, self.n), 1e9)
        for x, y, rx, ry in PONDS:
            water = np.minimum(water, np.hypot((self.xs - x) * ry / rx, self.ys - y) - ry)
        self.scatter(['willow_tree'], 70, meres & (water < 9), gap=1.6)
        self.scatter(['willow_tree'], 12, (water < 7) & self.floor & ~meres, gap=1.6)
        self.scatter(['birch_tree', 'tree', 'bush', 'bush'], 190, meres, gap=1)
        self.scatter(['wildflowers'], 200, meres, gap=.6)

        # The Applewick Orchards: rows of apple trees, and the wild hives at the east end.
        hives = (384, 212)
        self.block_disc(*hives, 6)
        self.add('wild_hive', *hives, r=1.1)
        self.add('wild_hive', hives[0] - 4, hives[1] + 3, r=1.1)
        for box in ((302, 204, 333, 240), (358, 196, 396, 246), (302, 248, 342, 262), (318, 192, 340, 204)):
            self.orchard(*box)
        orch = self.mask('orchard')
        self.scatter(['hawthorn_bush', 'wildflowers', 'wildflowers'], 260, orch, gap=.8)

        # Hollowend: the old wood at the end of the land, a roofless chapel in its middle.
        chapel = (352, 308)
        self.block_disc(*chapel, 9)
        self.add('chapel', *chapel, r=0, width=6, depth=5, label='Hollowend Chapel')
        for dx, dy, wd, dp in ((-8, -6, .6, 4), (8, -6, .6, 3), (-6, 7, 4, .6), (6, 7, 3, .6)):
            self.add('wall', chapel[0] + dx, chapel[1] + dy, r=0, width=wd, depth=dp)
        hollow = self.mask('hollowend')
        self.scatter(['tree', 'tree', 'birch_tree', 'oak_tree'], 480, hollow & (dense > .4), gap=.9)
        self.scatter(['bush', 'hawthorn_bush', 'rock'], 240, hollow, gap=.8)

        # Around the town: hedge lines and verges, so the fields are not bare lawn between the plots.
        home = self.mask('home')
        self.scatter(['oak_tree'], 22, home, gap=7)
        self.scatter(['wildflowers', 'wildflowers', 'bush', 'hawthorn_bush'], 300, home, gap=.8)

    def ring(self, centre, radius, n, kind):
        for k in range(n):
            a = k / n * math.tau
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if self.road[int(y), int(x)] > 2.2:
                self.add(kind, x, y)

    # ---- spawns -----------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        tags = {t for *_, t in content.AMBUSH}
        kept = [s for s in w['slimes'] if s.get('ambush') and s['ambush'] not in tags]
        sleepers = list(kept) + [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        # ordinary enemies first: code and tests take the zone's first spawn as a plain slime
        out = list(sleepers)
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        for x, y in KING:
            out.append({'x': x, 'y': y, 'kind': 'big'})
            self.block_disc(x, y, 4)
        keep = self.blocked.copy()
        for h in HAMLETS.values():
            keep[max(h['y'] - h['hh'] - 12, 0):h['y'] + h['hh'] + 13, max(h['x'] - h['hw'] - 12, 0):h['x'] + h['hw'] + 13] = True
        city = w['city']
        keep[city['y0'] - 8:city['y1'] + 9, city['x0'] - 8:city['x1'] + 9] = True
        solid = Grid()
        for o in self.objects:
            solid.add(o['x'], o['y'], max(o['r'], (o.get('width', 0) + o.get('depth', 0)) / 4))
        for name, kinds in SPAWNS.items():
            pool = [k for k, c in kinds.items() for _ in range(c)]
            rng.shuffle(pool)
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 3.5) & (self.seam > 7))
            sep = 10.5
            placed = 0
            tries = 0
            while placed < len(pool) and tries < 40000:
                tries += 1
                if tries % 8000 == 0:
                    sep *= .85
                j, i = pts[rng.randrange(len(pts))]
                x, y = round(i + rng.random(), 2), round(j + rng.random(), 2)
                if any(math.hypot(x - s['x'], y - s['y']) < sep for s in out) or not solid.free(x, y, .8, .5):
                    continue
                out.append({'x': x, 'y': y, 'kind': pool[placed], 'layout': TAG})
                placed += 1
            assert placed == len(pool), f'{name}: placed {placed} of {len(pool)} spawns'
        ordinary = [t for t in out if t.get('layout') == TAG]
        camps = [(h['x'] - h['hw'] - 2, h['x'] + h['hw'] + 2, h['y'] - h['hh'] - 2, h['y'] + h['hh'] + 2) for h in HAMLETS.values()]
        # some tests stand a hero 40 tiles south-east of the first spawn, expecting open country
        safe = lambda x, y: any(a <= x <= b and c <= y <= d for a, b, c, d in camps) or x >= self.n or y >= self.n or not self.floor[int(y), int(x)]
        ordinary.sort(key=lambda t: (t['kind'] != 'green', safe(t['x'] + 40, t['y'] + 40)))
        return ordinary + [t for t in out if t.get('layout') != TAG]

    # ---- checks -----------------------------------------------------------------------------------------------------
    def solid_mask(self, objects):
        solid = ~self.floor
        for o in objects:
            if o['kind'] == 'void':
                continue
            wd, dp = o.get('width', 0), o.get('depth', 0)
            if wd > 0 and dp > 0:
                solid |= (abs(self.xs - o['x']) < wd / 2 + .3) & (abs(self.ys - o['y']) < dp / 2 + .3)
            elif o['r'] > 0:
                r = o['r'] + .3
                x0, x1, y0, y1 = int(o['x'] - r - 1), int(o['x'] + r + 2), int(o['y'] - r - 1), int(o['y'] + r + 2)
                sub = np.hypot(self.xs[y0:y1, x0:x1] - o['x'], self.ys[y0:y1, x0:x1] - o['y']) < r
                solid[y0:y1, x0:x1] |= sub
        return solid

    def reachable(self, solid, start):
        seen = np.zeros_like(solid)
        q = deque([start])
        seen[start[1], start[0]] = True
        while q:
            x, y = q.popleft()
            for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= a < self.n and 0 <= b < self.n and not solid[b, a] and not seen[b, a]:
                    seen[b, a] = True
                    q.append((a, b))
        return seen


GROUND = {'sand': 1, 'field': 2, 'downs': 3, 'forest': 4, 'clover': 5, 'scarp': 6}


def rng_stacks(rng):
    return rng.randint(2, 4)


def ground_spans(g, floor):
    """[y, x0, x1, kind] runs: small enough for world.js, exact on the client."""
    out = []
    for y in range(g.shape[0]):
        x = 0
        row = np.where(floor[y], g[y], 0)
        while x < g.shape[1]:
            k = int(row[x])
            e = x
            while e + 1 < g.shape[1] and row[e + 1] == k:
                e += 1
            if k:
                out.append([y, x, e, k])
            x = e + 1
    return out


def design(world, write=False):
    d = Designer(world)
    objects = d.build()
    solid = d.solid_mask(objects)
    s = world['spawn']
    seen = d.reachable(solid, (int(s['x']), int(s['y'])))
    d.reach = seen
    slimes = d.spawns()
    world['objects'] = objects
    world['slimes'] = slimes
    world['paths'] = [[list(p) for p in road] for road in ROADS]
    world['groundSpans'] = ground_spans(d.ground, d.floor)
    world['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, HAMLETS)
    if write:
        content.record_mailboxes(world, HAMLETS, ROOT / 'world/mailboxes.txt')
    # checks: the map must hold together as a map
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    assert lost < open_cells.sum() * .01, f'{lost} open cells are cut off from the spawn'
    for t in world['slimes']:
        assert d.floor[int(t['y']), int(t['x'])], f"spawn off land {t}"
        assert seen[int(t['y']), int(t['x'])], f"unreachable spawn {t}"
    for n in world['npcs']:
        if n['id'].startswith(('fold_', 'salt_', 'apple_')) or n['id'].startswith(('travel_stonefold', 'travel_saltby', 'travel_applewick', 'mailbox_0_stonefold', 'mailbox_0_saltby', 'mailbox_0_applewick')):
            assert seen[int(n['y']), int(n['x'])], f"unreachable npc {n['id']}"
    for p in world['places']:
        assert seen[int(p['y']), int(p['x'])], f"unreachable place {p['id']}"
    for road in ROADS:
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                assert d.floor[int(y), int(x)], f'road leaves the land at {x:.0f},{y:.0f}'
                c = world['city']
                inside = c['x0'] - 1 <= x <= c['x1'] + 1 and c['y0'] - 1 <= y <= c['y1'] + 1
                assert inside or not solid[int(y), int(x)], f'something stands on the road at {x:.0f},{y:.0f}'
    stats = dict(objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(slimes), lost=lost, land=int(d.floor.sum()),
                 reachable=int(seen.sum()))
    return d, stats


def plan_picture(world, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    pal = {0: (96, 150, 74), 1: (226, 208, 150), 2: (150, 112, 70), 3: (152, 164, 96), 4: (62, 108, 62), 5: (128, 170, 88), 6: (130, 120, 96)}
    a = np.zeros((n, n, 3), np.uint8)
    a[:] = (28, 44, 74)
    for k, c in pal.items():
        a[(d.ground == k) & d.floor] = c
    im = Image.fromarray(a).resize((n * scale, n * scale), Image.NEAREST)
    g = ImageDraw.Draw(im)
    for road in world['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(232, 214, 160), width=scale)
    col = {'water': (70, 130, 190), 'rock': (140, 140, 140), 'cairn_boulder': (190, 190, 190), 'apple_tree': (200, 90, 80), 'wildflowers': (230, 220, 120),
           'bush': (44, 96, 44), 'hawthorn_bush': (44, 96, 44), 'haystack': (230, 200, 90)}
    for o in world['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1)
        c = col.get(o['kind'], (24, 66, 30))
        if o['kind'] in ('rampart', 'tower', 'wall', 'house', 'chapel', 'vale_cottage', 'watermill'):
            c = (235, 235, 245)
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'green': (120, 240, 90), 'blue': (90, 170, 255), 'pink': (255, 130, 200), 'yellow': (255, 230, 70), 'beetle': (255, 70, 40), 'big': (255, 255, 255)}
    for s in world['slimes']:
        c = kc.get(s['kind'], (255, 0, 255))
        g.rectangle([s['x'] * scale - 2, s['y'] * scale - 2, s['x'] * scale + 2, s['y'] * scale + 2], fill=c, outline=(0, 0, 0))
    c = world['city']
    g.rectangle([c['x0'] * scale, c['y0'] * scale, c['x1'] * scale, c['y1'] * scale], outline=(255, 255, 255), width=2)
    for h in HAMLETS.values():
        g.rectangle([(h['x'] - h['hw']) * scale, (h['y'] - h['hh']) * scale, (h['x'] + h['hw']) * scale, (h['y'] + h['hh']) * scale], outline=(255, 255, 255), width=2)
        g.text((h['x'] * scale - 20, h['y'] * scale), h['name'], fill=(255, 255, 255))
    for i, r in enumerate(REGIONS.values()):
        ys, xs = np.nonzero(d.region == i)
        sx, sy = r['seeds'][0]
        g.text((sx * scale, sy * scale - 14), r['name'], fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    im.crop((0, 85 * scale, 424 * scale, 335 * scale)).save(out)


def main():
    sys.path.insert(0, str(ROOT / 'scripts'))
    world = json.loads(MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world, d, sys.argv[2])


if __name__ == '__main__':
    main()
