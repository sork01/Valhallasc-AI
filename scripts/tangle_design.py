#!/usr/bin/env python3
"""The Tanglecrown as an authored map (zone 22 of the shapes pilot): no filler land, the whole outline used.

Owner request 2026-11-08: "for pilot. reshape tanglecrown. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the Ribbonwild only
(its whole west side), keep every portal (Sunward Vale and the Veyrroot Canopy on the north border, the Temple of the Rain Crown door), keep both elites and add one with no
quest, three outposts.

The outline at k = 1.0 is grid 304 with 32,708 land tiles (the old 144 square held 20,736): a wide triangle with the Ribbonwild on its west side, Sunward Vale in the north-west
corner, the Veyrroot Canopy along the north-east side and a coast in the south-east. The painting shows a jungle cut by a net of pale trails (a trunk road with two junctions, a
western branch and an eastern fork). The zone keeps its own style: kapoks, strangler figs, banana palms, orchids, ferns, hanging vines, blackwater pools and a jade temple.

Runs in `zone_shapes.py apply` after the Ribbonwild's design. The zone is `designOnly` + `rebuild` (zone-shapes.txt, `seamWith {22: [21]}`): the old 144 square cannot sit inside
the outline, so nothing is moved: everything is made here from `world/zone-shapes/preshape-22.txt` (the people, places, quests, the temple door and the escort keep their ids).
The Ribbonwild's approved design ran unchanged (`ribbon_design.LATE_SEAMS = {22}`: its south-east gate became the seam; only its spawns within 7 tiles went and the Pavilion's
mailbox and Spark master stepped back). The border to the Ribbonwild is reserved from `shape.edges` runs: nothing art-less and nobody within 20 tiles of it, no spawn within 22,
no loose scenery within 2.5. The road to the seam ends where the Ribbonwild's south-east road ends.

    python3 scripts/tangle_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
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
import tangle_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, drop_near_seam, fbm, ground_spans, seg_field, step_back_artless  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-22.txt'

ZONE = 22
HAM = content.HAMLETS
SPAWN = (122.0, 203.0)           # Banyan Landing's own entry
ES18 = (90.0, 176.0)             # The Root That Refused the Order (Empty Seat chapter 18)
TEMPLE_ARR = (content.DOOR[0], content.DOOR[1] + 7)       # where the temple's ways out arrive (old 120, 30)
CROSS_Y = 253.3                  # the Ribbonwild's south-east road meets the border at this row (its old gate stood at (349.5, 292.5) there = (90.5, 253.5) here)
SEAM_END = (94.0, CROSS_Y)       # this side's road ends on the border (set by `aim_seam`)
BOARDWALK = (110.0, 144.0)       # Tamsin Reedfoot waits on the west road
JADE_POOL = (124.0, 104.0)
RIM = 3

REGIONS = {
    'stair':     dict(name='The Sunward Stair', seeds=[(52, 62), (78, 74), (68, 52)]),
    'hang':      dict(name='The Hanging Gardens', seeds=[(100, 120), (108, 140), (88, 100)]),
    'basin':     dict(name='The Jade Basin', seeds=[(128, 104), (112, 92), (146, 98)]),
    'rise':      dict(name='The Orchid Rise', seeds=[(200, 106), (184, 98), (214, 108)]),
    'gate':      dict(name='The Kapok Gate', seeds=[(170, 128), (152, 122), (162, 142)]),
    'glades':    dict(name='The Landing Glades', seeds=[(122, 190), (108, 166), (140, 206), (104, 214)]),
    'reach':     dict(name='The Gliders\' Reach', seeds=[(150, 150), (138, 160), (162, 164)]),
    'terrace':   dict(name='The High Jaguar Terrace', seeds=[(190, 162), (184, 174), (204, 152)]),
    'drums':     dict(name='The Drum Terraces', seeds=[(232, 126), (222, 114), (236, 142)]),
    'rainstep':  dict(name='The Rain Crown Steps', seeds=[(254, 146), (258, 158), (248, 134)]),
    'maze':      dict(name='The Strangler Maze', seeds=[(205, 192), (190, 204), (218, 180)]),
    'blackwater': dict(name='The Blackwater Edge', seeds=[(160, 226), (140, 220), (182, 214)]),
    'mangrove':  dict(name='The Mangrove Stair', seeds=[(150, 244), (122, 254), (176, 234)]),
    'verge':     dict(name='The Seam Verge', seeds=[(84, 150), (92, 196), (70, 112)]),
}

# the roads follow the painting's net of trails (tile coordinates); the gate roads are added by `roads()` from the gate points
J1 = (172, 112)
R_E = [J1, (192, 118), (203, 124), (214, 128), (232, 134), (246, 140), (254, 146)]                 # the east fork: Drumroot Post, then the temple camp
R_DS = [(214, 128), (226, 144), (230, 158), (236, 172)]                                           # south from Drumroot Post along the terraces
R_RS = [(254, 146), (253, 160), (248, 172)]                                                       # south from the camp to the Rainstep Stair
R_LT = [(122, 190), (122, 170), (128, 164), (140, 160), (154, 154), (169, 148)]                    # from the Landing to the trunk road
R_S = [(122, 190), (122, 210), (124, 226), (114, 242), SEAM_END]                                  # south from the Landing to the Ribbonwild
R_LS = [(160, 218), (142, 222), (124, 226)]                                                       # Stilt Post to the south road

R = {'kapok_tree': 1.45, 'strangler_fig': 1.2, 'banana_palm': 1.1, 'hanging_vines': .18, 'giant_fern': .42, 'orchid_cluster': .08, 'glow_mushroom': .08, 'jungle_water': .95,
     'jade_pool': 1.6, 'root_bridge': .7, 'jaguar_totem': .9, 'tent': 1.5}
TALL = ('kapok_tree', 'strangler_fig', 'banana_palm')
GROUND = {'canopy': 1, 'loam': 2, 'moss': 3, 'blackwater': 4, 'jade': 5, 'bloom': 6, 'litter': 7, 'clay': 8, 'fern': 9}
REGION_GROUND = {'stair': 'fern', 'hang': 'bloom', 'basin': 'jade', 'rise': 'bloom', 'gate': 'moss', 'glades': 'loam', 'reach': 'canopy', 'terrace': 'jade', 'drums': 'litter',
                 'rainstep': 'jade', 'maze': 'moss', 'blackwater': 'blackwater', 'mangrove': 'clay', 'verge': 'litter'}

# scenery per 1000 land tiles of the region (x DENSITY_SCALE)
DENSITY_SCALE = 1.25
DENSITY = {
    'stair':     [('kapok_tree', 4.5), ('giant_fern', 4), ('hanging_vines', 3.5), ('banana_palm', 2.5), ('orchid_cluster', 3)],
    'hang':      [('hanging_vines', 6), ('orchid_cluster', 6), ('strangler_fig', 3), ('giant_fern', 3), ('kapok_tree', 2.5)],
    'basin':     [('kapok_tree', 3.5), ('giant_fern', 4), ('banana_palm', 3), ('orchid_cluster', 2.5), ('glow_mushroom', 2)],
    'rise':      [('orchid_cluster', 8), ('banana_palm', 3), ('kapok_tree', 3), ('hanging_vines', 3)],
    'gate':      [('kapok_tree', 4.5), ('banana_palm', 3.5), ('giant_fern', 3), ('hanging_vines', 3)],
    'glades':    [('kapok_tree', 3), ('banana_palm', 4), ('giant_fern', 3), ('orchid_cluster', 3)],
    'reach':     [('kapok_tree', 4.5), ('strangler_fig', 3), ('hanging_vines', 5), ('giant_fern', 3), ('glow_mushroom', 1.5)],
    'terrace':   [('giant_fern', 5), ('strangler_fig', 3), ('banana_palm', 3), ('orchid_cluster', 2)],
    'drums':     [('banana_palm', 5), ('kapok_tree', 4), ('giant_fern', 3), ('hanging_vines', 2.5)],
    'rainstep':  [('giant_fern', 4), ('orchid_cluster', 4), ('banana_palm', 3), ('hanging_vines', 3)],
    'maze':      [('strangler_fig', 4), ('kapok_tree', 3), ('hanging_vines', 4), ('glow_mushroom', 3)],
    'blackwater': [('strangler_fig', 4), ('giant_fern', 4), ('glow_mushroom', 3), ('hanging_vines', 3), ('banana_palm', 2)],
    'mangrove':  [('strangler_fig', 4.5), ('banana_palm', 3.5), ('giant_fern', 3), ('hanging_vines', 3)],
    'verge':     [('kapok_tree', 3), ('banana_palm', 3), ('giant_fern', 3.5), ('orchid_cluster', 2.5), ('hanging_vines', 2.5)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): mantises by the north and west, gliders over the middle, caimans
# in the blackwater, gorillas on the east terraces
SPAWN_SCALE = 1.2
SPAWN_DENSITY = {
    'stair':     {'orchidmantis': 2.0, 'canopyglider': .8},
    'hang':      {'orchidmantis': 1.6, 'canopyglider': 1.2},
    'basin':     {'poolcaiman': 2.4, 'orchidmantis': .6},
    'rise':      {'orchidmantis': 2.0, 'canopyglider': 1.0},
    'gate':      {'orchidmantis': 1.3, 'canopyglider': 1.1},
    'glades':    {'canopyglider': 1.3, 'orchidmantis': .9},
    'reach':     {'canopyglider': 2.2, 'orchidmantis': .5},
    'terrace':   {'drumgorilla': 2.0, 'canopyglider': .8},
    'drums':     {'drumgorilla': 4.0, 'canopyglider': .5},
    'rainstep':  {'drumgorilla': 2.8, 'poolcaiman': 1.0},
    'maze':      {'canopyglider': .8, 'drumgorilla': 2.0},
    'blackwater': {'poolcaiman': 4.2, 'canopyglider': .4},
    'mangrove':  {'poolcaiman': 3.4, 'drumgorilla': 1.0},
    'verge':     {'orchidmantis': 1.3, 'canopyglider': 1.1},
}
# pools of blackwater: (centre x, centre y, rx, ry)
POOLS = [(124, 118, 7, 5), (136, 96, 6, 4), (176, 236, 8, 5), (140, 252, 7, 4), (196, 228, 6, 4), (120, 232, 6, 4), (232, 186, 5, 4), (70, 92, 6, 4), (214, 158, 5, 4)]


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def gates(F):
    """The rim gates stand 2.5 tiles in from the last land cell, arrival six tiles inside: id -> (x, y, walk, arrival). The Ribbonwild's border is a seam (no gate)."""
    out = {}
    x = 58
    y0 = int(np.nonzero(F[:, x])[0].min())
    out['path_22_20'] = (x + .5, y0 + 2.5, (0, -1), (x + .5, y0 + 8.5))
    x = 184
    y0 = int(np.nonzero(F[:, x])[0].min())
    out['tangle_worldheart_gate'] = (x + .5, y0 + 2.5, (0, -1), (x + .5, y0 + 8.5))
    return out


def roads(G):
    sun, ver = G['path_22_20'], G['tangle_worldheart_gate']
    n_road = [(ver[0], ver[1]), ver[3], (181, 104), J1, (170, 120), (172, 138), (167, 158), (161, 180), (158, 200), (160, 218)]
    nw_road = [(sun[0], sun[1]), sun[3], (68, 62), (84, 78), (96, 96), (98, 116), (104, 138), (114, 156), (122, 170)]
    return [n_road, nw_road, R_E, R_DS, R_RS, R_LT, R_S, R_LS]


class Tanglecrown(Designer):
    TAG, SEED = 'tangle_design_v1', 20261110
    LATE_SEAMS = {23}       # the Veyrroot's seam arrived after this design was approved (2026-11-09): the masks stay as they were (the gate tangle_worldheart_gate keeps its discs and its road)

    def __init__(self, world, old):
        self.old = old
        self.F = np.array([[c == '#' for c in row] for row in world['shapeFloor']])
        self.G = gates(self.F)
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        # the border to the Ribbonwild (21) is a seam: nothing the other side cannot draw stands near it
        self.reserve = np.full((self.n, self.n), 1e9)
        self.coast = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] == 21:
                self.reserve = np.minimum(self.reserve, seg_field(e['points'], self.xs, self.ys))
            if e['kind'] == 'coast':
                self.coast = np.minimum(self.coast, seg_field(e['points'], self.xs, self.ys))
        self.pooled = np.full((self.n, self.n), 1e9)

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.reserve[iy, ix] > 3
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
            placed += self.scatter([kind], k, self.mask(name) & (self.reserve > 3.5), gap=1.6 if tall else gap, road=3.4 if tall else road)
        return placed

    def pool(self, cx, cy, rx, ry):
        """A pool of blackwater: a union of small water discs (solid); the ground pass tints the mud round it."""
        step = 2.05
        k = 0
        y = cy - ry
        row = 0
        while y <= cy + ry:
            x = cx - rx + (step / 2 if row % 2 else 0)
            while x <= cx + rx:
                wob = 1 + (fbm(self.noise, x, y, .2) - .5) * .5
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= wob and self.ok(x, y, 'jungle_water', lane=3.0):
                    self.add('jungle_water', x, y, v=self.rng.randrange(2))
                    k += 1
                x += step
            y += step * .866
            row += 1
        self.pooled = np.minimum(self.pooled, np.hypot(self.xs - cx, self.ys - cy) / max(rx, ry))
        return k

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        w = self.w
        self.fixed = self.take_temple()
        self.ground = np.zeros((self.n, self.n), np.uint8)
        for o in w['objects']:
            if o['kind'] == 'void':
                self.fixed.append(o)
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        self.block_disc(content.DOOR[0], content.DOOR[1], 9)
        self.block_disc(*TEMPLE_ARR, 6)
        self.block_disc(*SEAM_END, 8)
        self.blocked |= self.reserve < 2.5
        for h in HAM.values():
            assert self.F[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 9)
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)
        for p in content.PLACES + self.old_places():
            self.block_disc(p['x'], p['y'], 3.5)
        content.dress(self, HAM)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def old_places(self):
        door = content.DOOR
        return [dict(id='tangle_temple', x=door[0] - 8, y=door[1] + 3), dict(id='tangle_anaconda_pool', x=JADE_POOL[0] + 1, y=JADE_POOL[1] + 1),
                dict(id='tangle_jaguar_terrace', x=content.ELITES[1][1], y=content.ELITES[1][2]), dict(id='es_18_m', x=ES18[0], y=ES18[1])]

    def take_temple(self):
        """The Temple of the Rain Crown's door, moved whole; the Jade Basin's pool and the two root bridges follow their places."""
        out = []
        dx, dy = content.D_DOOR
        for o in self.old['objects']:
            if o['kind'] == 'rain_crown_temple':
                q = dict(o, x=round(o['x'] + dx, 2), y=round(o['y'] + dy, 2), layout=self.TAG)
                out.append(q)
        for o in self.old['objects']:
            if o['kind'] == 'jade_pool':
                q = dict(o, x=JADE_POOL[0], y=JADE_POOL[1], layout=self.TAG)
                out.append(q)
                self.grid.add(q['x'], q['y'], q['r'])
        for pos in ((BOARDWALK[0] - 4, BOARDWALK[1] + 2), (content.HAMLETS['rainstep']['x'] + 4, content.HAMLETS['rainstep']['y'] - 14)):
            o = next(o for o in self.old['objects'] if o['kind'] == 'root_bridge')
            q = dict(o, x=pos[0], y=pos[1], layout=self.TAG)
            out.append(q)
            self.grid.add(q['x'], q['y'], q['r'])
        return out

    def landmarks(self):
        ex = {k: (x, y) for k, x, y in content.ELITES}
        # pools of blackwater round the basin, the blackwater edge and the mangroves
        for cx, cy, rx, ry in POOLS:
            self.pool(cx, cy, rx, ry)
        # a ring of totems round the jaguar's terrace, open to the south-west where the way up leads
        self.ring_of(ex['crownjaguar'], 9.5, 7, 'jaguar_totem', rot=.2, gaps=[(135, 40)], v=0)
        # the strangler maze: three rings of figs round the centipede, each with a gap, the gaps on opposite sides
        for radius, n, gap in ((15, 30, 0), (21, 40, 180), (27, 50, 0)):
            self.ring_of(ex['rootcentipede'], radius, n, 'strangler_fig', rot=.1, gaps=[(gap, 18)])
        # vines hang in pairs either side of the trunk road, and a totem marks each junction
        pts = dense_points(self.ROADLIST[0], 1.0)
        for i in range(10, len(pts) - 4, 14):
            x, y = pts[i]
            side = 1 if (i // 14) % 2 else -1
            if self.ok(x + side * 3.6, y, 'hanging_vines', lane=2.4):
                self.add('hanging_vines', x + side * 3.6, y)
        for x, y in (J1, (214, 128)):
            self.ring_of((x, y), 4.5, 4, 'jaguar_totem', rot=.8, v=0)
        # a low ring of ferns round every hold circle and every elite
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'giant_fern', rot=.4)
        for _, x, y in content.ELITES:
            self.ring_of((x, y), 5.5, 6, 'orchid_cluster', rot=.7)

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        self.objects[:] = [o for o in self.objects if not (o['kind'] in TALL and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        g[self.floor & (self.pooled < 1.5 + rough * .15)] = GROUND['blackwater']
        g[self.floor & (self.coast < 9 + rough * .5)] = GROUND['clay']
        for name in ('rainstep', 'basin', 'terrace'):
            pass
        door = content.DOOR
        g[self.floor & (np.hypot(self.xs - door[0], self.ys - door[1]) < 16 + rough)] = GROUND['jade']
        g[self.floor & (np.hypot(self.xs - JADE_POOL[0], self.ys - JADE_POOL[1]) < 13 + rough)] = GROUND['jade']
        ex = {k: (x, y) for k, x, y in content.ELITES}
        g[self.floor & (np.hypot(self.xs - ex['crownjaguar'][0], self.ys - ex['crownjaguar'][1]) < 12 + rough)] = GROUND['jade']
        g[self.floor & (np.hypot(self.xs - ex['rootcentipede'][0], self.ys - ex['rootcentipede'][1]) < 11 + rough)] = GROUND['moss']

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
                out.append(dict(s, x=round(ES18[0] + 2, 2), y=ES18[1]))
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
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.reserve > 22))      # 4.4 keeps a spawn 3.4+ tiles from every road (tests/seam-roads.py); 22 keeps a calm strip along the seam
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
        ordinary.sort(key=lambda t: t['kind'] != 'orchidmantis')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


# ---- the old people, places and portals in the new frame ------------------------------------------------------------------
LANDING_PEOPLE = {'travel_banyan': (7, 14), 'mailbox_22_banyan_landing': (8.65, 17.27)}


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
        elif n['id'] in LANDING_PEOPLE:
            h = content.HAMLETS['landing']
            n['x'], n['y'] = h['x'] + LANDING_PEOPLE[n['id']][0], h['y'] + LANDING_PEOPLE[n['id']][1]
        elif n['id'] == 'tangle_hatchling':
            n['x'], n['y'] = BOARDWALK
            n['escort']['route'] = [[112.0, 156.0], [122.0, 166.0], [134.0, 175.0]]
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    for p in zone['places']:
        if p['id'] == 'es_18_m':
            p['x'], p['y'] = ES18
        elif p['id'] == 'tangle_temple':
            p['x'], p['y'] = door[0] - 8, door[1] + 3
        elif p['id'] == 'tangle_anaconda_pool':
            p['x'], p['y'] = JADE_POOL[0] + 1, JADE_POOL[1] + 1
        elif p['id'] == 'tangle_jaguar_terrace':
            p['x'], p['y'] = content.ELITES[1][1], content.ELITES[1][2]
    for p in zone['portals']:
        if p.get('seam'):           # the Ribbonwild seam (zone_shapes.make_seams): its line is the border, not a gate
            continue
        if p['id'] == 'tangle_rain_gate':
            p['x'], p['y'] = door[0] - 3, door[1] + 1
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'] = round(gx, 2), round(gy, 2)
        p['walk'] = list(walk)
    zone['futureInstance']['x'], zone['futureInstance']['y'] = door


def aim_seam(world, zone):
    """Both seam portals stand where the road crosses (the seam road pass weighs the portals' points, and quest arrows aim at them): the old gate's place, in the south-west."""
    pts = next(e['points'] for e in zone['shape']['edges'] if e['kind'] == 'shared' and e['other'] == 21)
    cx = None
    for a, b in zip(pts, pts[1:]):
        if (a[1] - CROSS_Y) * (b[1] - CROSS_Y) <= 0 and a[1] != b[1]:
            cx = a[0] + (b[0] - a[0]) * (CROSS_Y - a[1]) / (b[1] - a[1])
    assert cx is not None
    mine = next(p for p in zone['portals'] if p.get('seam') and p['to'] == 21)
    theirs = next(p for p in world['zones'][20]['portals'] if p.get('seam') and p['to'] == ZONE)
    sh = mine['seam']['shift']
    mine['x'], mine['y'], mine['tx'], mine['ty'] = round(cx, 2), CROSS_Y, round(cx + sh[0], 2), round(CROSS_Y + sh[1], 2)
    theirs['x'], theirs['y'], theirs['tx'], theirs['ty'] = mine['tx'], mine['ty'], mine['x'], mine['y']
    return cx


def link_travel(world):
    """Add (never strip) the Spark links across every portal into or out of the Tanglecrown, both ways, as compact_atlas.sync_travel_links does."""
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
    assert abs(aim_seam(world, zone) - SEAM_END[0]) < .3, 'the road to the seam must end on the border'
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the zone was rebuilt
    d = Tanglecrown(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    d.late_dropped = d.late_moved = 0
    if any(p.get('seam') and p['to'] == 23 for p in zone['portals']):      # the Veyrroot's seam (2026-11-09) replaced the north-east rim gate: only the spawns within 7 tiles of it and the loose scenery within 2.5 go, and the art-less objects within 20 step back
        d.late_dropped = drop_near_seam(zone, d, 23)
        loose = [o for o in objects if o.get('layout') == d.TAG and o['kind'] != 'void' and d.seam_late[min(max(int(o['y']), 0), d.n - 1), min(max(int(o['x']), 0), d.n - 1)] < 2.5]
        objects = [o for o in objects if o not in loose]
        d.late_dropped += len(loose)
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    seamed = {p['id'] for p in zone['portals'] if p.get('seam')}      # the Ribbonwild's and the Veyrroot's seams replaced rim gates: their line is the border, not a gate
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items() if g not in seamed]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, zone, HAM, old)
    if any(p.get('seam') and p['to'] == 23 for p in zone['portals']):      # after the people stand in their final places: the art-less objects within 20 tiles of the Veyrroot seam step back (see greenmeadow_design.step_back_artless)
        d.late_moved = step_back_artless(zone, zone['objects'], d, 23)
    for q in zone['quests']:
        q.update(copy.deepcopy(content.REWRITES.get(q['id'], {})))
    # every crossing that arrives here follows the new frame: Sunward's and the Veyrroot Canopy's gates, and the temple's two ways out (the Ribbonwild seam carries its own shift)
    arrivals = {'path_20_22': G['path_22_20'][3], 'canopy_jungle_gate': G['tangle_worldheart_gate'][3], 'rain_crown_return': TEMPLE_ARR, 'rain_crown_exit': TEMPLE_ARR}
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals and not p.get('seam'):
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
    # the new masters join the Spark network of their neighbours (a global sync_travel_links would rewrite every other pilot zone's links)
    link_travel(world)
    zones_ = [world] + world['zones']
    masters = {n['id']: n for z in zones_[:47] for n in z.get('npcs', []) if n.get('travelStop')}
    for i in (21, 22):
        for n in zones_[i].get('npcs', []):
            if n.get('travelStop'):
                for other in n['travelLinks']:
                    assert other in masters and n['id'] in masters[other]['travelLinks'], f"Spark link {n['id']} -> {other} is not reciprocal"
    if write:
        content.record_mailboxes(zone, HAM, ROOT / 'world/mailboxes.txt')
    problems = check(zone, d, solid, seen, G)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']),
                 kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('kapok_tree', 'strangler_fig', 'banana_palm', 'hanging_vines', 'giant_fern', 'orchid_cluster', 'glow_mushroom', 'jungle_water')})
    if problems:
        if os.environ.get('TANGLE_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')


def check(zone, d, solid, seen, G):
    problems = []
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    if not (lost < open_cells.sum() * .02):
        problems.append(f'{lost} open cells are cut off from the spawn')
    for t in zone['slimes']:
        if not d.floor[int(t['y']), int(t['x'])]:
            problems.append(f'spawn off land {t}')
        if not seen[int(t['y']), int(t['x'])]:
            problems.append(f'unreachable spawn {t}')
        if d.reserve[int(t['y']), int(t['x'])] <= 7:
            problems.append(f'spawn within 7 tiles of the seam {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
        if d.reserve[int(n['y']), int(n['x'])] < 20:
            problems.append(f"person {n['id']} within 20 tiles of the seam")
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
        if walk and not seen[int(gy - walk[1] * 3), int(gx - walk[0] * 3)]:
            problems.append(f'gate {g} is blocked from the inside')
    door = next(q for q in zone['portals'] if q['id'] == 'tangle_rain_gate')
    if not seen[int(door['y'] + 2), int(door['x'])]:
        problems.append('the temple door is cut off')
    if not seen[int(TEMPLE_ARR[1]), int(TEMPLE_ARR[0])]:
        problems.append('the temple arrival is cut off')
    if not seen[int(SEAM_END[1]), int(SEAM_END[0])]:
        problems.append('the road to the Ribbonwild seam is cut off')
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
    # an elite stands clear of everything a player walks to: awareness plus 3 tiles from every road, place and person, and from every hub and gate
    walked = [(q, 'road') for road in d.ROADLIST for q in dense_points(road)]
    walked += [((q['x'], q['y']), f"place {q['id']}") for q in zone['places'] if q['id'] not in ('tangle_anaconda_pool', 'tangle_jaguar_terrace')] + [((n['x'], n['y']), f"npc {n['id']}") for n in zone['npcs'] if n['id'] != 'tangle_hatchling']
    walked += [((q['x'], q['y']), f"portal {q['id']}") for q in zone['portals'] if not q.get('seam')]
    walked += [(pt, 'escort route') for pt in [tuple(n['escort']['route'][i]) for n in zone['npcs'] if n['id'] == 'tangle_hatchling' for i in range(3)]]
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
    popping = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o['kind'] in ARTLESS and d.reserve[int(o['y']), int(o['x'])] < 20]
    if popping:
        problems.append(f'art-less objects within the camera reach of the seam pop in on crossing: {popping[:5]}')
    loose = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o.get('layout') == d.TAG and o['kind'] != 'void' and d.reserve[int(o['y']), int(o['x'])] < 2.5]
    if loose:
        problems.append(f'loose scenery within 2.5 tiles of the seam: {loose[:5]}')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    for h in HAM.values():
        if d.reserve[int(h['y']), int(h['x'])] < 20 + h['hw']:
            problems.append(f"{h['name']} stands within {20 + h['hw']} tiles of the seam")
    # a hold circle and its sleepers stand on land that is not a road and are reachable
    for p in zone['places']:
        if p.get('waves'):
            if d.road[int(p['y']), int(p['x'])] < 4:
                problems.append(f"hold circle {p['id']} stands on a road")
    return problems


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    T = zone['shape']['T']
    s = 1758 / 2048
    atlas = Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB')
    x0, y0 = int(round(T[0] * s)), int(round(T[1] * s))
    bg = atlas.crop((x0, y0, x0 + int(n * s), y0 + int(n * s))).resize((n * scale, n * scale), Image.LANCZOS)
    bg = Image.blend(bg, Image.new('RGB', bg.size, (20, 30, 28)), .35)
    pal = {1: (40, 130, 80), 2: (150, 90, 50), 3: (150, 220, 80), 4: (40, 90, 110), 5: (150, 220, 190), 6: (220, 120, 200), 7: (200, 170, 70), 8: (230, 200, 140), 9: (60, 190, 150)}
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
    col = {'kapok_tree': (20, 90, 50), 'strangler_fig': (10, 60, 40), 'banana_palm': (120, 200, 90), 'hanging_vines': (90, 160, 90), 'giant_fern': (80, 180, 120), 'orchid_cluster': (240, 120, 200),
           'glow_mushroom': (160, 255, 200), 'jungle_water': (70, 170, 210), 'jade_pool': (120, 240, 230), 'jaguar_totem': (240, 210, 120), 'rain_crown_temple': (255, 240, 160)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('orchid_cluster', 'glow_mushroom') else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'orchidmantis': (240, 120, 200), 'canopyglider': (120, 220, 255), 'poolcaiman': (90, 140, 120), 'drumgorilla': (200, 150, 100)}
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
        if p.get('seam'):
            g.line([(x * scale, y * scale) for x, y in p['seam']['points']], fill=(255, 60, 255), width=3)
            continue
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
