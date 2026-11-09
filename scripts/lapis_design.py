#!/usr/bin/env python3
"""The Lapis Erg as an authored map (zone 25 of the shapes pilot): no filler land, the whole outline used, and a wall against the Yearwheel.

Owner request 2026-11-09: "for pilot. reshape lapis erg. and remake the zone and quests to fit the new shape. no fillers. put a wall towards yearwheel". Owner answers: keep the
Sunward Vale, Veyrroot Canopy and Sunken Astrolabe crossings; **the Yearwheel gets no portal at all from here, just a wall covering it up** (no gate, no arch); keep both elites and
add one with no quest; three outposts. The wall is built from the game's own isometric `rampart` and `tower` objects (the city wall art, real collision), never a flat drawing.

The outline at k = 1.0 is grid 296 with 41,194 land tiles (the old square held 25,600): a wedge, the Yearwheel along its curved north-west side (the wall), the sea along the long
north-east diagonal, the Veyrroot Canopy's jungle along the south and Sunward Vale along the west. The painting shows a sand sea cut by a faceted net of pale trails, three round blue
oases (south-west, middle, east), a dark mesa in the north-east and dune ridges in the south. The zone keeps its own style: date palms, sandstone, salt spires, silk flags,
caravan tents and the brass astrolabe.

Runs in `zone_shapes.py apply` after the Tanglecrown's design. The zone is `designOnly` + `rebuild` (zone-shapes.txt, `seamWith {25: []}`: none of its neighbours is on the pilot yet,
so it has NO seam; the day Sunward Vale, the Veyrroot Canopy or the Yearwheel is shaped, its design must list 25): the old 160 square is not moved, everything is made here from
`world/zone-shapes/preshape-25.txt` (the people, places, quests, the astrolabe's door keep their ids). The Yearwheel crossing is closed on both sides: `close_yearwheel`.

    python3 scripts/lapis_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import copy
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lapis_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-25.txt'

ZONE = 25
YEARWHEEL = 28
HAM = content.HAMLETS
SPAWN = (46.0, 190.0)            # Azure Wells' own entry, inside the west gate of the city
WALL_IN = 1.7                    # the wall stands this far inside the border (its outer face is the border)
WALL_STEP = 2.0
TOWER_EVERY = 28.0
WALL_COLOR, TOWER_COLOR = '#d7c8a0', '#2f6f9a'       # sandstone and lapis blue (the roof)
WALL_KEEP = 10.0                 # no spawn within this many tiles of the wall

REGIONS = {
    'wells':     dict(name='The Azure Reach', seeds=[(60, 196), (44, 232), (82, 236)]),
    'strand':    dict(name='The Sunward Strand', seeds=[(22, 130), (22, 172), (24, 232)]),
    'dancers':   dict(name='The Dancing Flats', seeds=[(98, 190), (82, 150), (102, 216)]),
    'groves':    dict(name='The Date Palm Groves', seeds=[(118, 134), (104, 116), (136, 150), (120, 160)]),
    'stair':     dict(name='The Pale Stair', seeds=[(95, 72), (80, 92), (112, 84)]),
    'walking':   dict(name='The Walking Dune', seeds=[(58, 96), (44, 112), (70, 114)]),
    'saltarch':  dict(name='The Salt Arch', seeds=[(100, 52), (72, 62), (128, 54)]),
    'terraces':  dict(name='The Brass Terraces', seeds=[(130, 80), (148, 90), (142, 66)]),
    'crag':      dict(name='The Roc Crag', seeds=[(203, 130), (196, 112), (212, 146)]),
    'basin':     dict(name='The Eastern Basin', seeds=[(209, 168), (188, 182), (228, 186)]),
    'pans':      dict(name='The Blue Salt Pans', seeds=[(160, 216), (130, 224), (188, 226)]),
    'glass':     dict(name='The Glass Dunes', seeds=[(246, 226), (232, 208), (268, 238)]),
    'coast':     dict(name='The Salt Coast', seeds=[(158, 72), (178, 98), (228, 152), (264, 204)]),
    'wallside':  dict(name='The Wheel Wall Verge', seeds=[(30, 70), (62, 50), (22, 94), (102, 44)]),
}
GROUND = {'sand': 1, 'dune': 2, 'palm': 3, 'shore': 4, 'salt': 5, 'brass': 6, 'rock': 7, 'coast': 8, 'glass': 9}
REGION_GROUND = {'wells': 'sand', 'strand': 'palm', 'dancers': 'dune', 'groves': 'palm', 'stair': 'sand', 'walking': 'dune', 'saltarch': 'salt', 'terraces': 'brass', 'crag': 'rock',
                 'basin': 'sand', 'pans': 'salt', 'glass': 'glass', 'coast': 'coast', 'wallside': 'rock'}

R = {'lapis_dunegrass': .18, 'lapis_date_palm': 1.05, 'lapis_sandstone': .9, 'lapis_blue_flower': .08, 'lapis_salt_spire': .8, 'lapis_silk_flag': .13, 'lapis_caravan_tent': 1.5,
     'lapis_well': 1.0, 'lapis_mirror': 1.2, 'lapis_roc_nest': 1.4, 'lapis_salt_arch': 1.3, 'water': 4.3}
TALL = ('lapis_date_palm', 'lapis_salt_spire')

# scenery per 1000 land tiles of the region (x DENSITY_SCALE)
DENSITY_SCALE = 1.25
DENSITY = {
    'wells':    [('lapis_dunegrass', 6), ('lapis_date_palm', 3.5), ('lapis_sandstone', 2.5), ('lapis_blue_flower', 3)],
    'strand':   [('lapis_date_palm', 7), ('lapis_dunegrass', 6), ('lapis_blue_flower', 5), ('lapis_sandstone', 2)],
    'dancers':  [('lapis_dunegrass', 9), ('lapis_sandstone', 3), ('lapis_blue_flower', 2), ('lapis_date_palm', 1.5)],
    'groves':   [('lapis_date_palm', 9), ('lapis_dunegrass', 5), ('lapis_blue_flower', 5), ('lapis_sandstone', 1.5)],
    'stair':    [('lapis_dunegrass', 8), ('lapis_sandstone', 5), ('lapis_salt_spire', 2), ('lapis_date_palm', 1.5)],
    'walking':  [('lapis_dunegrass', 9), ('lapis_sandstone', 4), ('lapis_salt_spire', 1.5)],
    'saltarch': [('lapis_salt_spire', 5), ('lapis_sandstone', 4), ('lapis_dunegrass', 6)],
    'terraces': [('lapis_sandstone', 8), ('lapis_dunegrass', 4), ('lapis_salt_spire', 2), ('lapis_date_palm', 1)],
    'crag':     [('lapis_sandstone', 9), ('lapis_dunegrass', 4), ('lapis_salt_spire', 2)],
    'basin':    [('lapis_date_palm', 5), ('lapis_dunegrass', 6), ('lapis_blue_flower', 5), ('lapis_sandstone', 2)],
    'pans':     [('lapis_salt_spire', 6), ('lapis_sandstone', 3), ('lapis_dunegrass', 4)],
    'glass':    [('lapis_salt_spire', 4), ('lapis_sandstone', 5), ('lapis_dunegrass', 4)],
    'coast':    [('lapis_dunegrass', 7), ('lapis_salt_spire', 3), ('lapis_sandstone', 3), ('lapis_date_palm', 1.5)],
    'wallside': [('lapis_sandstone', 5), ('lapis_dunegrass', 6), ('lapis_salt_spire', 2)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): hoppers round the Wells, fennecs through the palms and the north, scorpions on the
# salt and glass, vultures on the mesas and round the eastern water
SPAWN_SCALE = 1.2
SPAWN_DENSITY = {
    'wells':    {'sandhopper': 1.6},
    'strand':   {'sandhopper': 1.8, 'dunefennec': .6},
    'dancers':  {'sandhopper': 2.6, 'dunefennec': .6},
    'groves':   {'dunefennec': 3.0, 'sandhopper': .5},
    'stair':    {'dunefennec': 2.2, 'sandhopper': .6},
    'walking':  {'dunefennec': 1.2, 'sandhopper': 1.2},
    'saltarch': {'dunefennec': 2.0},
    'terraces': {'sunvulture': 1.8, 'glassscorpion': .8},
    'crag':     {'sunvulture': 2.6},
    'basin':    {'sunvulture': 3.0, 'glassscorpion': .6},
    'pans':     {'glassscorpion': 3.6},
    'glass':    {'glassscorpion': 3.0, 'sunvulture': .8},
    'coast':    {'glassscorpion': 1.0, 'sunvulture': 1.2},
    'wallside': {'dunefennec': 1.0},
}


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def gates(F):
    """The rim gates stand 2.5 tiles in from the last land cell, arrival six tiles inside: id -> (x, y, walk, arrival). The Yearwheel has none (a wall)."""
    out = {}
    y = 186
    x0 = int(np.nonzero(F[y])[0].min())
    out['path_25_20'] = (x0 + 2.5, y + .5, (-1, 0), (x0 + 8.5, y + .5))
    x = 135
    y1 = int(np.nonzero(F[:, x])[0].max())
    out['lapis_canopy_gate'] = (x + .5, y1 - 1.5, (0, 1), (x + .5, y1 - 7.5))
    return out


def roads(G):
    sw, vr = G['path_25_20'], G['lapis_canopy_gate']
    entry = [(sw[0], sw[1]), sw[3], (30, 188), (44, 190), (60, 190), (76, 188), (92, 168)]
    trunk = [(92, 168), (92, 140), (93, 118), (94, 98), (95, 70), (94, 54)]
    astro = [(93, 118), (110, 106), (128, 96), (131, 90), (130, 78), (130, 67)]
    mid = [(92, 168), (104, 160), (118, 150), (140, 156), (166, 166), (186, 172), (210, 176), (226, 180)]
    south = [(80, 196), (100, 206), (126, 208), (150, 205), (142, 214), (vr[3][0], vr[3][1]), (vr[0], vr[1])]
    east = [(150, 205), (176, 212), (200, 214), (236, 206)]
    link = [(186, 172), (190, 190), (200, 214)]
    return [entry, trunk, astro, mid, south, east, link]


class Lapis(Designer):
    TAG, SEED = 'lapis_design_v1', 20261109
    LATE_SEAMS = set()

    def __init__(self, world, old):
        self.old = old
        self.F = np.array([[c == '#' for c in row] for row in world['shapeFloor']])
        self.G = gates(self.F)
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        self.wall_field = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] == YEARWHEEL:
                self.wall_field = np.minimum(self.wall_field, seg_field(e['points'], self.xs, self.ys))
        self.pooled = np.full((self.n, self.n), 1e9)
        self.wall = []

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.wall_field[iy, ix] > 4
                and self.grid.free(x, y, R.get(kind, .5) if r is None else r, .3))

    def ring_of(self, centre, radius, n, kind, rot=.3, gaps=(), **extra):
        k = 0
        for i in range(n):
            a = i / n * math.tau + rot
            deg = math.degrees(a) % 360
            if any(min(abs(deg - c), 360 - abs(deg - c)) < half for c, half in gaps):
                continue
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if self.ok(x, y, kind, lane=2.0):
                self.add(kind, x, y, **extra)
                k += 1
        return k

    def fill(self, name, kinds, gap=.8, road=2.8):
        area = int(self.mask(name).sum())
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per * DENSITY_SCALE / 1000))
            tall = kind in TALL
            placed += self.scatter([kind], k, self.mask(name) & (self.wall_field > 4), gap=1.6 if tall else gap, road=3.4 if tall else road)
        return placed

    # ---- the Wheel Wall ----------------------------------------------------------------------------------------------------
    def build_wall(self):
        """A solid wall of isometric ramparts and towers along the whole Yearwheel border, 1.7 tiles inside it, with NO gate: it covers the old way up. Pieces are 2 tiles apart along the
        border and overlap, so nothing slips between them; a tower stands at both ends and about every 28 tiles."""
        runs = [e['points'] for e in self.w['shape']['edges'] if e['kind'] == 'shared' and e['other'] == YEARWHEEL]
        assert len(runs) == 1, 'one border run with the Yearwheel'
        pts = [tuple(p) for p in runs[0]]
        # the walking line, 1.7 tiles inland of the border chain
        line = []
        for a, b in zip(pts, pts[1:]):
            ln = math.dist(a, b)
            nx, ny = -(b[1] - a[1]) / ln, (b[0] - a[0]) / ln
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            land = lambda s: bool(self.F[min(max(int(my + ny * s * 5), 0), self.n - 1), min(max(int(mx + nx * s * 5), 0), self.n - 1)])
            if not land(1):
                nx, ny = -nx, -ny
            k = max(1, int(ln / .5))
            for i in range(k + 1):
                t = i / k
                line.append((a[0] + (b[0] - a[0]) * t + nx * WALL_IN, a[1] + (b[1] - a[1]) * t + ny * WALL_IN, (b[0] - a[0]) / ln, (b[1] - a[1]) / ln))
        # points every WALL_STEP of arc length
        out, acc, last = [], 0.0, None
        for p in line:
            if last is not None:
                acc += math.dist(last[:2], p[:2])
            if last is None or acc >= WALL_STEP:
                out.append(p)
                acc = 0.0
            last = p
        out.append(line[-1])
        towers, dist = [], 0.0
        pieces = []
        for i, (cx, cy, tx, ty) in enumerate(out):
            if i:
                dist += math.dist(out[i - 1][:2], (cx, cy))
            ends = i in (0, len(out) - 1)
            if ends or (dist - (towers[-1][3] if towers else 0)) >= TOWER_EVERY:
                towers.append((cx, cy, 'tower', dist))
                continue
            ax, ay = abs(tx), abs(ty)
            w, d = (2.8, 1.8) if ax >= 2 * ay else (1.8, 2.8) if ay >= 2 * ax else (2.3, 2.3)
            pieces.append((cx, cy, 'rampart', w, d))
        for cx, cy, kind, *rest in towers:
            self.add('tower', cx, cy, r=0, v=0, width=3.4, depth=3.4, color=TOWER_COLOR, label='')
        for cx, cy, kind, w, d in pieces:
            self.add('rampart', cx, cy, r=0, v=0, width=w, depth=d, color=WALL_COLOR, label='')
        self.wall = [(o['x'], o['y']) for o in self.objects if o['kind'] in ('rampart', 'tower')]
        # nothing else stands within 2.5 tiles of the wall; the pieces were added first
        self.block_cells(self.wall_field < 3.5)
        return len(pieces), len(towers)

    def block_cells(self, mask):
        self.blocked |= mask

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        w = self.w
        self.fixed = self.take_astrolabe()
        self.ground = np.zeros((self.n, self.n), np.uint8)
        for o in w['objects']:
            if o['kind'] == 'void':
                self.fixed.append(o)
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        self.block_disc(content.DOOR[0], content.DOOR[1] + 3, 9)
        for cx, cy in content.OASES:
            self.block_disc(cx, cy, 8)
        for h in HAM.values():
            assert self.F[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 9)
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)
        for p in content.PLACES + self.old_places():
            self.block_disc(p['x'], p['y'], 3.5)
        self.walled = self.build_wall()
        content.dress(self, HAM)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def old_places(self):
        door = content.DOOR
        return [dict(id='lapis_vault', x=door[0] - 8, y=door[1] + 6), dict(id='lapis_mirror', x=118.0, y=126.0), dict(id='lapis_east', x=209.0, y=158.0)] + \
            [dict(id=f'es_21_{i}', x=x, y=y) for i, (x, y) in enumerate(content.BELLS)]

    def take_astrolabe(self):
        """The Sunken Astrolabe's lens, moved whole to the brass terraces."""
        out = []
        dx, dy = content.D_DOOR
        for o in self.old['objects']:
            if o['kind'] == 'lapis_astrolabe':
                out.append(dict(o, x=round(o['x'] + dx, 2), y=round(o['y'] + dy, 2), layout=self.TAG))
        assert len(out) == 1
        return out

    def landmarks(self):
        ex = {k: (x, y) for k, x, y in content.ELITES}
        # the three oases: the old art plus its solid water disc
        for i, (cx, cy) in enumerate(content.OASES):
            self.add('lapis_oasis', cx, cy, r=0, v=i, solid=False)
            self.add('water', round(cx - .59, 2), round(cy - .59, 2), r=4.3, v=0)
            self.pooled = np.minimum(self.pooled, np.hypot(self.xs - cx, self.ys - cy) / 9)
        self.add('lapis_mirror', *content.MIRROR, r=1.2, v=0)
        self.add('lapis_roc_nest', ex['mirageroc'][0] - 2, ex['mirageroc'][1], r=1.4, v=0)
        self.add('lapis_salt_arch', 100, 46, r=1.3, v=0)
        # a ring of sandstone round each elite's pocket, open on one side, and a ring of date palms round each oasis
        self.ring_of(ex['dunecolossus'], 20, 18, 'lapis_sandstone', rot=.2, gaps=[(40, 40)])
        self.ring_of(ex['mirageroc'], 14, 14, 'lapis_sandstone', rot=.5, gaps=[(225, 40)])
        self.ring_of(ex['cobaltbasilisk'], 18, 20, 'lapis_salt_spire', rot=.1, gaps=[(150, 40)])
        for i, (cx, cy) in enumerate(content.OASES):
            self.ring_of((cx, cy), 8.5, 12, 'lapis_date_palm', rot=.4 + i)
        # silk flags in pairs either side of the trunk road
        pts = dense_points(self.ROADLIST[1], 1.0)
        for i in range(8, len(pts) - 4, 12):
            x, y = pts[i]
            side = 1 if (i // 12) % 2 else -1
            if self.ok(x + side * 3.4, y, 'lapis_silk_flag', lane=2.4):
                self.add('lapis_silk_flag', x + side * 3.4, y)
        # a low ring of dune grass round every hold circle and every elite
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'lapis_dunegrass', rot=.4)

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        self.objects[:] = [o for o in self.objects if not (o['kind'] in TALL and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        g[self.floor & (self.pooled < 1.0 + rough * .1)] = GROUND['shore']
        g[self.floor & (self.coast < 8 + rough * .5)] = GROUND['coast']
        door = content.DOOR
        g[self.floor & (np.hypot(self.xs - door[0], self.ys - door[1]) < 17 + rough)] = GROUND['brass']
        ex = {k: (x, y) for k, x, y in content.ELITES}
        g[self.floor & (np.hypot(self.xs - ex['mirageroc'][0], self.ys - ex['mirageroc'][1]) < 13 + rough)] = GROUND['rock']
        g[self.floor & (np.hypot(self.xs - ex['cobaltbasilisk'][0], self.ys - ex['cobaltbasilisk'][1]) < 12 + rough)] = GROUND['glass']
        g[self.floor & (self.wall_field < 9 + rough * .4)] = GROUND['rock']

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])
        for o in self.objects:
            if o['kind'] in TALL and o.get('layout') == self.TAG and 'v' not in o:
                o['v'] = self.rng.randrange(4)

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        out = []
        for s in self.old['slimes']:
            if str(s.get('ambush', '')).startswith('empty-seat:'):
                out.append(dict(s))
        out += [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in HAM.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
        solid = Grid()
        for o in self.fixed + self.objects:
            if o['kind'] != 'void':
                solid.add(o['x'], o['y'], max(o['r'], (o.get('width', 0) + o.get('depth', 0)) / 4))
        self.short = {}
        self.counts = {}
        for name, kinds in SPAWN_DENSITY.items():
            area = int(self.mask(name).sum())
            pool = [k for k, per in kinds.items() for _ in range(max(1, int(area * per * SPAWN_SCALE / 1000)))]
            self.counts[name] = len(pool)
            rng.shuffle(pool)
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.wall_field > WALL_KEEP))      # 4.4 keeps a spawn 3.4+ tiles from every road
            if not len(pts):
                self.short[name] = len(pool)
                continue
            sep, placed, tries = 12.0, 0, 0
            while placed < len(pool) and tries < 40000:
                tries += 1
                if tries % 8000 == 0:
                    sep *= .85
                j, i = pts[rng.randrange(len(pts))]
                x, y = round(i + rng.random() * .98, 2), round(j + rng.random() * .98, 2)
                if any(math.hypot(x - s['x'], y - s['y']) < sep for s in out) or not solid.free(x, y, .6, .15):
                    continue
                out.append({'x': x, 'y': y, 'kind': pool[placed], 'layout': self.TAG})
                placed += 1
            if placed < len(pool):
                self.short[name] = len(pool) - placed
        ordinary = [t for t in out if t.get('layout') == self.TAG]
        ordinary.sort(key=lambda t: t['kind'] != 'sandhopper')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]

    @property
    def coast(self):
        if not hasattr(self, '_coast'):
            self._coast = np.full((self.n, self.n), 1e9)
            for e in self.w['shape']['edges']:
                if e['kind'] == 'coast':
                    self._coast = np.minimum(self._coast, seg_field(e['points'], self.xs, self.ys))
        return self._coast


# ---- the old people, places and portals in the new frame ------------------------------------------------------------------
def restore_and_shift(zone, old, G):
    """A rebuild zone starts empty: bring the old people, places and portals back from the sidecar and put them in the new frame."""
    zone['spawn'] = dict(x=SPAWN[0], y=SPAWN[1])
    zone['npcs'] = copy.deepcopy(old['npcs'])
    zone['places'] = copy.deepcopy(old['places'])
    zone['futureInstance'] = copy.deepcopy(old['futureInstance'])
    door = content.DOOR
    for n in zone['npcs']:
        if n['id'] in content.HUB_NPCS:
            hn, ox, oy = content.HUB_NPCS[n['id']]
            h = content.HAMLETS[hn]
            n['x'], n['y'] = h['x'] + ox, h['y'] + oy
        elif n['id'] in content.WELLS_PEOPLE:
            h = content.HAMLETS['wells']
            n['x'], n['y'] = h['x'] + content.WELLS_PEOPLE[n['id']][0], h['y'] + content.WELLS_PEOPLE[n['id']][1]
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    for p in zone['places']:
        if p['id'] == 'lapis_vault':
            p['x'], p['y'] = door[0] - 8, door[1] + 6
        elif p['id'] == 'lapis_mirror':
            p['x'], p['y'] = 118.0, 126.0
        elif p['id'] == 'lapis_east':
            p['x'], p['y'] = 209.0, 158.0
        elif p['id'].startswith('es_21_'):
            p['x'], p['y'] = content.BELLS[int(p['id'][-1])]
        else:
            raise AssertionError(f"unplaced old place {p['id']}")
    keep = []
    for p in zone['portals']:
        if p['id'] == 'atlas_25_28':          # the wall covers it up: no crossing to the Yearwheel from here
            continue
        if p['id'] == 'lapis_astrolabe_gate':
            p['x'], p['y'] = door[0], door[1] + 3
        else:
            gx, gy, walk, arr = G[p['id']]
            p['x'], p['y'] = round(gx, 2), round(gy, 2)
            p['walk'] = list(walk)
        keep.append(p)
    zone['portals'] = keep
    zone['futureInstance']['x'], zone['futureInstance']['y'] = door


def close_yearwheel(world, zone):
    """Both halves of the old Lapis-Yearwheel crossing go: the portals, their exit routes and trails, the atlas link and the Spark links. Idempotent (compact_atlas makes them again on a
    full sync-world, and this runs after it)."""
    z28 = world['zones'][YEARWHEEL - 1]
    z28['portals'] = [p for p in z28['portals'] if p['to'] != ZONE]
    z28['exitRoutes'] = [r for r in z28.get('exitRoutes', []) if r['portal'] != 'atlas_28_25']
    gone = [p for p in z28.get('atlasPaths', []) if p and abs(p[0][0] - 267.5) < 1 and abs(p[0][1] - 394.5) < 1]
    z28['atlasPaths'] = [p for p in z28.get('atlasPaths', []) if p not in gone]
    z28['paths'] = [p for p in z28['paths'] if p not in gone]
    world['atlas']['links'] = [l for l in world['atlas']['links'] if {l['a'], l['b']} != {ZONE, YEARWHEEL}]
    mine = {n['id'] for n in zone['npcs'] if n.get('travelStop')}
    theirs = {n['id'] for n in z28['npcs'] if n.get('travelStop')}
    for n in zone['npcs']:
        if n.get('travelStop'):
            n['travelLinks'] = [t for t in n['travelLinks'] if t not in theirs]
    for n in z28['npcs']:
        if n.get('travelStop'):
            n['travelLinks'] = [t for t in n['travelLinks'] if t not in mine]


def link_travel(world):
    """Add (never strip) the Spark links across every portal into or out of the Lapis Erg, both ways, as compact_atlas.sync_travel_links does."""
    zones = [world] + world['zones']
    masters = lambda z: [n for n in z.get('npcs', []) if n.get('travelStop')]
    for i, z in enumerate(zones):
        for p in z['portals']:
            if p['to'] == i or ZONE not in (i, p['to']):
                continue
            mine, other = masters(z), masters(zones[p['to']])
            if not mine or not other:
                continue
            a = min(mine, key=lambda n: math.hypot(n['x'] - p['x'], n['y'] - p['y']))
            b = min(other, key=lambda n: math.hypot(n['x'] - p['tx'], n['y'] - p['ty']))
            if b['id'] not in a['travelLinks']:
                a['travelLinks'].append(b['id'])
            if a['id'] not in b['travelLinks']:
                b['travelLinks'].append(a['id'])


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    G = gates(F)
    restore_and_shift(zone, old, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the zone was rebuilt
    d = Lapis(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items()]
    door = content.DOOR
    zone['exitRoutes'].append(dict(portal='lapis_astrolabe_gate', points=[[door[0], door[1] + 3], [door[0], door[1] + 7]]))
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, zone, HAM, old)
    for q in zone['quests']:
        q.update(copy.deepcopy(content.REWRITES.get(q['id'], {})))
    # every crossing that arrives here follows the new frame: Sunward's and the Veyrroot Canopy's gates and the astrolabe's two ways out
    arrivals = {'path_20_25': G['path_25_20'][3], 'canopy_lapis_gate': G['lapis_canopy_gate'][3], 'sunken_astrolabe_return': (door[0], door[1] + 7), 'sunken_astrolabe_exit': (door[0], door[1] + 7)}
    found = set()
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals:
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
                found.add(p['id'])
    close_yearwheel(world, zone)
    link_travel(world)
    zones_ = [world] + world['zones']
    masters = {n['id']: n for z in zones_[:47] for n in z.get('npcs', []) if n.get('travelStop')}
    for n in zones_[ZONE].get('npcs', []):
        if n.get('travelStop'):
            for other in n['travelLinks']:
                assert other in masters and n['id'] in masters[other]['travelLinks'], f"Spark link {n['id']} -> {other} is not reciprocal"
    if write:
        content.record_mailboxes(zone, HAM, ROOT / 'world/mailboxes.txt')
    problems = check(world, zone, d, solid, seen, G, found)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), wall=d.walled, spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']),
                 kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('lapis_date_palm', 'lapis_dunegrass', 'lapis_sandstone', 'lapis_salt_spire', 'lapis_blue_flower', 'lapis_silk_flag')})
    if problems:
        if os.environ.get('LAPIS_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


def check(world, zone, d, solid, seen, G, found):
    problems = []
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    if not (lost < open_cells.sum() * .03):
        problems.append(f'{lost} open cells are cut off from the spawn')
    for t in zone['slimes']:
        if not d.floor[int(t['y']), int(t['x'])]:
            problems.append(f'spawn off land {t}')
        if not seen[int(t['y']), int(t['x'])]:
            problems.append(f'unreachable spawn {t}')
        if t.get('layout') == d.TAG and d.wall_field[int(t['y']), int(t['x'])] <= content_wall_keep():
            problems.append(f'spawn within {WALL_KEEP:.0f} tiles of the wall {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
        if not d.floor[int(p['y']), int(p['x'])]:
            problems.append(f"place {p['id']} off land")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
        if walk and not seen[int(gy - walk[1] * 3), int(gx - walk[0] * 3)]:
            problems.append(f'gate {g} is blocked from the inside')
    door = next(q for q in zone['portals'] if q['id'] == 'lapis_astrolabe_gate')
    if not seen[int(door['y'] + 2), int(door['x'])]:
        problems.append('the astrolabe door is cut off')
    if not seen[int(content.DOOR[1] + 7), int(content.DOOR[0])]:
        problems.append('the astrolabe arrival is cut off')
    # no crossing to the Yearwheel from either side, and the missing arrivals
    if any(p['to'] == YEARWHEEL for p in zone['portals']):
        problems.append('Lapis still has a portal to the Yearwheel')
    if any(p['to'] == ZONE for p in world['zones'][YEARWHEEL - 1]['portals']):
        problems.append('the Yearwheel still has a portal to the Lapis Erg')
    for need in ('path_20_25', 'canopy_lapis_gate', 'sunken_astrolabe_return', 'sunken_astrolabe_exit'):
        if need not in found:
            problems.append(f'no incoming portal {need} found to re-aim')
    # the wall: continuous (no gap wider than a player between neighbouring pieces), towers at both ends, and nothing reachable between it and the border
    wall = [o for o in zone['objects'] if o['kind'] in ('rampart', 'tower')]
    if len([o for o in wall if o['kind'] == 'tower']) < 4:
        problems.append('the wall needs at least four towers')
    for o in wall:
        if not d.floor[int(o['y']), int(o['x'])]:
            problems.append(f"wall piece off land at {o['x']},{o['y']}")
    cells = d.F & (d.wall_field < 1.2)
    ys, xs = np.nonzero(cells & seen)
    stray = [(int(x), int(y)) for x, y in zip(xs, ys)]
    if stray:
        problems.append(f'{len(stray)} cells between the wall and the border are reachable: {stray[:6]}')
    # an elite stands clear of everything a player walks to: awareness plus 3 tiles from every road, place and person, and from every hub and gate
    walked = [(q, 'road') for road in d.ROADLIST for q in dense_points(road)]
    walked += [((q['x'], q['y']), f"place {q['id']}") for q in zone['places']] + [((n['x'], n['y']), f"npc {n['id']}") for n in zone['npcs']]
    walked += [((q['x'], q['y']), f"portal {q['id']}") for q in zone['portals']]
    for kind, ex, ey in content.ELITES:
        near = min(((math.dist((ex, ey), q), what) for q, what in walked), key=lambda t: t[0])
        if near[0] < content.AWARENESS[kind] + 3:
            problems.append(f'{kind} stands {near[0]:.1f} tiles from a {near[1]}: its awareness is {content.AWARENESS[kind]:.0f}')
        for c in [zone['city']] + zone['camps']:
            gap = math.hypot(max(c['x0'] - ex, 0, ex - c['x1']), max(c['y0'] - ey, 0, ey - c['y1']))
            if gap < content.AWARENESS[kind] + 3:
                problems.append(f'{kind} stands {gap:.1f} tiles from a hub')
        for gname, (gx, gy, walk, arr) in G.items():
            if math.dist((ex, ey), (gx, gy)) < 20:
                problems.append(f'{kind} stands near the gate {gname}')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    for p in zone['places']:
        if p.get('waves') and d.road[int(p['y']), int(p['x'])] < 4:
            problems.append(f"hold circle {p['id']} stands on a road")
    bad = set()
    for road in d.ROADLIST + [r['points'] for r in zone['exitRoutes']]:
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                if not d.floor[int(y), int(x)]:
                    problems.append(f'road leaves the land at {x:.0f},{y:.0f}')
                inside = any(c['x0'] - 1 <= x <= c['x1'] + 1 and c['y0'] - 1 <= y <= c['y1'] + 3 for c in [zone['city']] + zone['camps'])
                if not inside and solid[int(y), int(x)]:
                    bad.add((int(x), int(y)))
    if bad:
        problems.append(f'something stands on the road at {sorted(bad)[:12]}')
    return problems


def content_wall_keep():
    return WALL_KEEP


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    T = zone['shape']['T']
    s = 1758 / 2048
    atlas = Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB')
    x0, y0 = int(round(T[0] * s)), int(round(T[1] * s))
    bg = atlas.crop((x0, y0, x0 + int(n * s), y0 + int(n * s))).resize((n * scale, n * scale), Image.LANCZOS)
    bg = Image.blend(bg, Image.new('RGB', bg.size, (40, 30, 20)), .35)
    pal = {1: (230, 190, 110), 2: (220, 160, 60), 3: (120, 170, 90), 4: (60, 190, 200), 5: (190, 210, 235), 6: (190, 120, 60), 7: (160, 90, 70), 8: (240, 225, 190), 9: (50, 120, 120)}
    a = np.array(bg)
    for k, c in pal.items():
        m = np.kron((d.ground == k) & d.floor, np.ones((scale, scale), bool))
        a[m] = (a[m] * .45 + np.array(c) * .55).astype(np.uint8)
    out_mask = np.kron(~d.floor, np.ones((scale, scale), bool))
    a[out_mask] = (a[out_mask] * .35).astype(np.uint8)
    im = Image.fromarray(a)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(250, 220, 120), width=scale)
    col = {'lapis_date_palm': (60, 130, 70), 'lapis_dunegrass': (170, 160, 80), 'lapis_sandstone': (150, 110, 80), 'lapis_salt_spire': (230, 240, 250), 'lapis_blue_flower': (80, 120, 230),
           'lapis_silk_flag': (240, 60, 120), 'water': (70, 170, 210), 'rampart': (255, 255, 255), 'tower': (40, 120, 230), 'lapis_caravan_tent': (250, 200, 120)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('lapis_blue_flower', 'lapis_dunegrass', 'rampart', 'tower') else 1)
        c = col.get(o['kind'], (255, 200, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'sandhopper': (240, 200, 90), 'dunefennec': (255, 150, 120), 'glassscorpion': (120, 200, 240), 'sunvulture': (200, 150, 200)}
    for s_ in zone['slimes']:
        c = kc.get(s_['kind'], (255, 20, 20))
        g.rectangle([s_['x'] * scale - 2, s_['y'] * scale - 2, s_['x'] * scale + 2, s_['y'] * scale + 2], fill=c, outline=(0, 0, 0))
    for camp in [zone['city']] + zone['camps']:
        g.rectangle([camp['x0'] * scale, camp['y0'] * scale, camp['x1'] * scale, camp['y1'] * scale], outline=(255, 160, 0), width=2)
        g.text((camp['plaza']['x'] * scale - 20, camp['plaza']['y'] * scale + 40), camp['name'], fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    for r in REGIONS.values():
        sx, sy = r['seeds'][0]
        g.text((sx * scale - 20, sy * scale - 14), r['name'], fill=(240, 240, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    for p in zone['places']:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(120, 255, 160), stroke_width=1, stroke_fill=(0, 0, 0))
    for p in zone['portals']:
        g.ellipse([p['x'] * scale - 6, p['y'] * scale - 6, p['x'] * scale + 6, p['y'] * scale + 6], outline=(255, 60, 60), width=3)
        g.text((p['x'] * scale + 8, p['y'] * scale - 6), p['name'], fill=(255, 120, 120), stroke_width=1, stroke_fill=(0, 0, 0))
    for kind, ex, ey in content.ELITES:
        g.ellipse([ex * scale - 8, ey * scale - 8, ex * scale + 8, ey * scale + 8], outline=(255, 0, 0), width=3)
        g.text((ex * scale + 10, ey * scale - 6), kind, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    im.save(out)


def main():
    world = json.loads(MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])


if __name__ == '__main__':
    main()
