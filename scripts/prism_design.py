#!/usr/bin/env python3
"""The Prismwaste as an authored map (zone 14 of the shapes pilot): no filler land, the whole outline used.

Owner request 2026-11-08: "for pilot. reshape prism waste and remake the zone and quests to fit the new shape. no fillers." Owner answers: keep the Mirror Queen
and the Sunshard and add one new elite with no quest, three new outposts, and the Prismwaste is seamless against Astralhollow (its whole west side) and the
Obsidian Orrery (the short south-west corner); Stormglass (south) and Cairnspine (east) stay walk-in gates on the rim. The zone keeps its own style: a rose-salt
desert of standing mirrors, sunspires and glass, the Last Shade's awning, four families banded by distance from the refuge (mirage jackals, shard scarabs, glass
harriers, prism sentinels), the Broken Crown.

Runs in `zone_shapes.py apply` after the Orrery's design. The zone is `designOnly` (zone-shapes.txt, `seamWith {14: [13, 15]}`): it keeps the outline floor
(`shapeFloor`), takes no filler, and places its own gates (`place_portals` skips it). Astralhollow's and the Orrery's approved designs ran unchanged with their
Prismwaste gate as a phantom (the seam portal replaced the gate: `shifted_state` skips a seam portal, `exitRoutes` and the inbound rewrite too). The borders to
Astralhollow and the Orrery are reserved from `shape.edges` runs exactly as Astralhollow reserved this one: no art-less object or person within 20 tiles, no
spawn within 7, no loose scenery within 2.5.

The painted atlas (tile = painted px * 2048/1758 - shape.T, T = [1022, 51]) shows a rose-salt desert, a diamond of golden roads in the middle, a trunk road
up the west side to a pair of huge pink crystals, a road north-east to the coast, a road along the south coast to the Orrery corner, and big pink crystals
standing about the land: the design follows it.

Fixed, moved as a rigid block from `world/zone-shapes/preshape-14.txt` (the old layout): the Last Shade (its tent, three lens pillars) with every person, the
Empty Seat's place and its sleeper, the Ember Grave Cross and its sleeper. Every person, place, portal and quest keeps its id.

    python3 scripts/prism_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
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
import prism_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, drop_near_seam, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-14.txt'

ZONE = 14
D_HUB = (22, 58)           # old refuge (rect 47..81 x 105..124, plaza 64,114) -> plaza (86, 172)
SPAWN = (86.0, 174.0)
CROSS = (160.0, 172.0)     # the Ember Grave Cross: a quiet hollow in the Lens Fields
ES_PLACE = (128.0, 178.0)  # Break the Beautiful Lie
CROWN = (118.0, 24.0)
RIM = 3

REGIONS = {
    'shade':   dict(name='The Last Shade', seeds=[(86, 172)]),
    'flats':   dict(name='The Salt Flats', seeds=[(66, 226), (100, 238), (46, 200), (84, 208)]),
    'verge':   dict(name='The Western Verge', seeds=[(30, 172), (22, 142), (20, 114)]),
    'ridge':   dict(name='The First Ridge', seeds=[(106, 150), (122, 132), (96, 126)]),
    'lens':    dict(name='The Lens Fields', seeds=[(150, 162), (132, 176), (176, 150), (156, 194)]),
    'court':   dict(name='The Mirror Court', seeds=[(50, 84), (42, 62), (66, 62), (40, 98)]),
    'crown':   dict(name='The Broken Crown', seeds=[(112, 34), (92, 28), (130, 42), (96, 54)]),
    'north':   dict(name='The Beacon Rise', seeds=[(148, 68), (136, 88), (124, 72)]),
    'watch':   dict(name='The Broken Watch', seeds=[(184, 100), (170, 80), (200, 122)]),
    'cairn':   dict(name='The Cairn Slopes', seeds=[(214, 138), (222, 118), (206, 150)]),
    'spires':  dict(name='The Sunspire Reaches', seeds=[(232, 192), (252, 224), (214, 214), (236, 232)]),
    'brine':   dict(name='The Brine Road', seeds=[(160, 254), (120, 256), (200, 244), (90, 262)]),
}

# the roads follow the painted atlas (tile coordinates); the gate roads are added by `roads()` from the arrival points
RHO_NW = [(84, 160), (110, 141), (140, 124), (180, 108)]
RHO_NE = [(180, 108), (205, 133), (228, 158)]
RHO_SE = [(228, 158), (222, 182), (200, 198), (170, 209), (146, 221)]
RHO_SW = [(84, 160), (100, 180), (121, 199), (146, 221)]
LTRUNK = [(84, 160), (70, 148), (62, 132), (60, 118), (72, 103), (80, 92)]
NWROAD = [(80, 92), (100, 76), (125, 52), (145, 38), (158, 30)]
CROWN_ROAD = [(125, 52), (123, 38), (119, 28)]
WATCH_ROAD = [(145, 38), (162, 52), (172, 72), (180, 108)]
STEM_S = [(146, 221), (148, 236), (150, 250)]
S_WEST = [(150, 250), (130, 254), (117, 253), (90, 256), (66, 260), (52, 266), (58, 273)]
E_BOTTOM = [(150, 250), (175, 242), (200, 236), (230, 236), (262, 238), (276, 241)]
SE_LINK = [(200, 198), (204, 218), (200, 238)]
HUB_N = [(86, 174), (86, 166), (84, 160)]
MF_SPUR = [(76, 98), (94, 98)]
WS_SPUR_E = [(160, 70), (169, 68)]
WS_SPUR_W = [(136, 68), (127, 55)]
CF_SPUR = [(210, 162), (226, 162)]
AWNING_LANE = [(110, 141), (101, 145)]
GLASS_LANE = [(94, 80), (91, 76)]
BEACON_LANE = [(145, 38), (142, 42)]
CAIRN_LANE = [(210, 140), (204, 141)]
SPIRES_LANE = [(222, 182), (228, 194)]

R = {'sunspire': .8, 'glassstone': .55, 'saltbrush': .25, 'mirrorwall': 1.05, 'lens_pillar': .75, 'broken_crown': 1.4, 'shade_tent': 2.0}
GROUND = {'rose': 1, 'salt': 2, 'ridge': 3, 'court': 4, 'crown': 5, 'slate': 6, 'scree': 7, 'quartz': 8, 'brine': 9, 'ash': 10}
REGION_GROUND = {'shade': 'rose', 'flats': 'salt', 'verge': 'rose', 'ridge': 'ridge', 'lens': 'rose', 'court': 'court', 'crown': 'crown', 'north': 'quartz',
                 'watch': 'slate', 'cairn': 'scree', 'spires': 'quartz', 'brine': 'brine'}

# scenery per 1000 land tiles of the region
DENSITY = {
    'shade':  [('saltbrush', 6)],
    'flats':  [('saltbrush', 16), ('glassstone', 5), ('sunspire', 1.5)],
    'verge':  [('saltbrush', 8), ('glassstone', 5), ('sunspire', 3)],
    'ridge':  [('mirrorwall', 3), ('glassstone', 8), ('saltbrush', 6)],
    'lens':   [('saltbrush', 10), ('glassstone', 4), ('sunspire', 3), ('mirrorwall', 1)],
    'court':  [('sunspire', 8), ('mirrorwall', 5), ('glassstone', 3), ('saltbrush', 5)],
    'crown':  [('sunspire', 9), ('glassstone', 5), ('mirrorwall', 2)],
    'north':  [('saltbrush', 8), ('glassstone', 6), ('sunspire', 4)],
    'watch':  [('glassstone', 10), ('mirrorwall', 4), ('sunspire', 4)],
    'cairn':  [('glassstone', 14), ('sunspire', 3), ('saltbrush', 4)],
    'spires': [('sunspire', 10), ('glassstone', 5), ('saltbrush', 5)],
    'brine':  [('saltbrush', 14), ('glassstone', 6), ('sunspire', 1.5)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): jackals by the refuge, then scarabs, harriers and sentinels
SPAWN_DENSITY = {
    'flats':  {'miragejackal': 3.4, 'shardscarab': .8},
    'verge':  {'miragejackal': 3.0, 'shardscarab': 1.4},
    'ridge':  {'shardscarab': 3.0, 'miragejackal': 1.4},
    'lens':   {'shardscarab': 2.4, 'miragejackal': 1.4, 'glassharrier': 1.2},
    'court':  {'shardscarab': 2.4, 'glassharrier': 2.6},
    'crown':  {'prismsentinel': 3.0, 'glassharrier': 1.5},
    'north':  {'glassharrier': 2.2, 'prismsentinel': 2.2, 'shardscarab': .8},
    'watch':  {'prismsentinel': 4.0},
    'cairn':  {'glassharrier': 3.0, 'prismsentinel': 2.0},
    'spires': {'shardscarab': 2.2, 'prismsentinel': 2.0, 'glassharrier': 1.5},
    'brine':  {'shardscarab': 2.4, 'miragejackal': 2.0},
}
# stands of sunspires where the painting shows its huge pink crystals: centre, radius
SHARD_STANDS = [(37, 57, 10), (72, 60, 11), (64, 96, 9), (90, 27, 8), (140, 44, 9), (40, 124, 8), (80, 192, 10), (52, 226, 10), (42, 252, 7), (126, 250, 9), (232, 186, 10), (255, 222, 8)]
# standing mirrors in broken lines: the first ridge, the court's arc, the watch's arc, a line across the lens fields
RIDGES = [
    [(108, 126), (112, 150), (110, 176), (116, 196)],
    [(38, 76), (48, 68), (60, 70), (70, 80)],
    [(168, 90), (182, 82), (196, 90)],
    [(176, 170), (180, 190), (190, 204)],
]


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def moved(o, dx, dy):
    q = dict(o)
    q['x'] = round(o['x'] + dx, 2)
    q['y'] = round(o['y'] + dy, 2)
    return q


def gates(F):
    """The two crossings that stay gates stand on the rim, 2.5 tiles in from the last land cell, arrival six tiles beyond: id -> (x, y, walk, arrival).
    Every one keeps its destination. The Astralhollow and Orrery borders are seams (no gate)."""
    out = {}
    def east(y):
        x1 = int(np.nonzero(F[y])[0].max())
        return (x1 - 2.5, y + .5)
    def south(x):
        y1 = int(np.nonzero(F[:, x])[0].max())
        return (x + .5, y1 - 2.5)
    x, y = south(150)
    out['path_14_19'] = (x, y, (0, 1), (x, y - 6))
    x, y = east(150)
    out['path_14_27'] = (x, y, (1, 0), (x - 6, y))
    return out


def roads(G):
    storm, cairn = G['path_14_19'], G['path_14_27']
    return [RHO_NW, RHO_NE, RHO_SE, RHO_SW, LTRUNK, NWROAD, CROWN_ROAD, WATCH_ROAD, STEM_S, S_WEST, E_BOTTOM, SE_LINK, HUB_N, MF_SPUR, WS_SPUR_E, WS_SPUR_W, CF_SPUR,
            AWNING_LANE, GLASS_LANE, BEACON_LANE, CAIRN_LANE, SPIRES_LANE,
            # the west road to Astralhollow: across the seam at about (6, 141)
            [(70, 164), (50, 158), (30, 150), (14, 144), (8.5, 141.5)],
            # the gate roads: from the arrival point to the network
            [(storm[0], storm[1]), storm[3], (150, 250)],
            [(cairn[0], cairn[1]), cairn[3], (224, 154), (228, 158)]]


class Prismwaste(Designer):
    TAG, SEED = 'prism_design_v1', 20261114
    LATE_SEAMS = {19}       # Stormglass's seam arrived after this design was approved: the masks stay as they were

    def __init__(self, world, old):
        self.old = old
        self.G = gates(np.array([[c == '#' for c in row] for row in world['shapeFloor']]))
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        # the borders to Astralhollow (13) and the Orrery (15) are seams: nothing the other side cannot draw stands near them
        self.reserve = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] in (13, 15):
                self.reserve = np.minimum(self.reserve, seg_field(e['points'], self.xs, self.ys))

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ring_of(self, centre, radius, n, kind, rot=.3, **extra):
        k = 0
        for i in range(n):
            a = i / n * math.tau + rot
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if 0 <= int(x) < self.n and 0 <= int(y) < self.n and self.inner[int(y), int(x)] and self.road[int(y), int(x)] > 2.4 and self.reserve[int(y), int(x)] > 3 and self.grid.free(x, y, R.get(kind, .5), .3):
                self.add(kind, x, y, **extra)
                k += 1
        return k

    def ridge(self, pts, step=2.3, lane=4.0, skip=()):
        """A broken line of standing mirrors, open wherever a road crosses it (lane tiles each side)."""
        placed = 0
        for x, y in dense_points(pts, step):
            x += self.rng.uniform(-.35, .35)
            y += self.rng.uniform(-.35, .35)
            ix, iy = int(x), int(y)
            if not (0 <= ix < self.n and 0 <= iy < self.n) or not self.inner[iy, ix] or self.blocked[iy, ix] or self.road[iy, ix] < lane or self.reserve[iy, ix] < 3:
                continue
            if any(math.hypot(x - sx, y - sy) < sr for sx, sy, sr in skip):
                continue
            if self.grid.free(x, y, R['mirrorwall'], .9):
                self.add('mirrorwall', x, y, v=placed % 4)
                placed += 1
        return placed

    def lens_ring(self, centre, radius, n):
        k = 0
        for i in range(n):
            a = i / n * math.tau + .21
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            ix, iy = int(x), int(y)
            if 0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > 4.5 and self.reserve[iy, ix] > 3 and self.grid.free(x, y, .75, .8):
                self.add('lens_pillar', x, y, v=k % 4, r=.75)
                k += 1
        return k

    def fill(self, name, kinds, gap=.8, road=2.8):
        area = int(self.mask(name).sum())
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per / 1000))
            tall = kind in ('sunspire', 'mirrorwall')
            placed += self.scatter([kind], k, self.mask(name) & (self.reserve > 3.5), gap=1.3 if tall else gap, road=3.6 if tall else road)
        return placed

    def take_hub(self):
        old = self.old
        out = []
        for o in old['objects']:
            if o['kind'] in ('shade_tent', 'lens_pillar') and 40 < o['x'] < 90 and o['y'] > 100:
                q = moved(o, *D_HUB)
                q['layout'] = self.TAG
                out.append(q)
                self.grid.add(q['x'], q['y'], max(q['r'], q.get('width', 0) / 2))
        return out

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        w, rng = self.w, self.rng
        self.fixed = self.take_hub()
        crown = dict(kind='broken_crown', x=CROWN[0], y=CROWN[1], r=1.4, v=0, layout=self.TAG)
        self.fixed.append(crown)
        self.grid.add(CROWN[0], CROWN[1], 1.4)
        self.ground = np.zeros((self.n, self.n), np.uint8)
        city = w['city']
        self.block(city['x0'] - 3, city['y0'] - 3, city['x1'] + 3, city['y1'] + 3)
        for o in w['objects']:
            if o['kind'] == 'void':
                self.fixed.append(o)
        for p in w['places'] + w['crosses']:
            self.block_disc(p['x'], p['y'], 5)
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        self.blocked |= self.reserve < 2.5
        self.block_disc(*CROSS, 8)
        self.block_disc(*CROWN, 6)
        self.pins = []
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 9)
            self.pins.append((x, y, 9))
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3.5)
        for h in content.HAMLETS.values():
            assert self.floor[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
        content.dress(self, content.HAMLETS)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def landmarks(self):
        rng = self.rng
        elites = [(x, y, 12) for _, x, y in content.ELITES]
        hamlets = [(h['x'], h['y'], 17) for h in content.HAMLETS.values()]
        # the painting's huge crystals: stands of sunspires
        for cx, cy, rad in SHARD_STANDS:
            self.ring_of((cx, cy), rad, max(6, int(rad * 1.1)), 'sunspire', rot=cx * .13)
            self.ring_of((cx, cy), rad * .45, 4, 'sunspire', rot=cy * .11)
        # standing mirrors in broken lines
        for pts in RIDGES:
            self.ridge(pts, skip=elites + hamlets)
        # the Broken Crown: a ring of sunspires round it
        self.ring_of(CROWN, 7, 8, 'sunspire', rot=.2)
        # the Broken Watch: a ring of lens pillars where the observatory stood
        wx, wy = 184, 100
        self.ring_of((wx, wy), 8, 7, 'lens_pillar', rot=.4)
        # the hold circles: a low ring of glass stones round each
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'glassstone', rot=.4)
        # the Great Lens: a broken ring of lens pillars round the heart of the waste, open at every road
        self.lens_ring((150, 158), 24, 14)
        # the Pyre Hollow round the Ember Grave Cross: a ring of glass stones
        self.ring_of(CROSS, 5.2, 8, 'glassstone', rot=.4)
        # the elites' rings: a low ring of glass stones marks where each stands
        for _, x, y in content.ELITES:
            self.ring_of((x, y), 5.5, 6, 'glassstone', rot=.7)
        # two lens pillars at each trunk junction
        for jx, jy in ((84, 160), (180, 108), (228, 158), (146, 221), (150, 250)):
            for sx, sy in ((-4.5, -4.5), (4.5, 4.5)):
                x, y = jx + sx, jy + sy
                if 0 <= int(x) < self.n and 0 <= int(y) < self.n and self.inner[int(y), int(x)] and self.road[int(y), int(x)] > 2.6 and self.reserve[int(y), int(x)] > 20 and self.grid.free(x, y, .7, .8):
                    self.add('lens_pillar', x, y, v=0, r=.5)

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        tall = ('sunspire', 'mirrorwall', 'lens_pillar')
        self.objects[:] = [o for o in self.objects if not (o['kind'] in tall and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        # the burnt ground round the Ember Grave Cross
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        g[self.floor & (np.hypot(self.xs - CROSS[0], self.ys - CROSS[1]) < 7 + rough * .5)] = GROUND['ash']

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        # the sleepers move with their places: the Ember Grave Cross's firelord, the Empty Seat's foe
        out = []
        for s in self.old['slimes']:
            if s.get('ambush') == 'raid_key:14':
                out.append(dict(s, x=round(CROSS[0] - 2.5, 2), y=CROSS[1]))
            elif str(s.get('ambush', '')).startswith('empty-seat:'):
                out.append(dict(s, x=round(ES_PLACE[0] + 2, 2), y=ES_PLACE[1]))
        out += [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in content.HAMLETS.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
        city = w['city']
        keep[city['y0'] - 8:city['y1'] + 9, city['x0'] - 8:city['x1'] + 9] = True
        solid = Grid()
        for o in self.fixed + self.objects:
            if o['kind'] != 'void':
                solid.add(o['x'], o['y'], max(o['r'], (o.get('width', 0) + o.get('depth', 0)) / 4))
        self.short = {}
        self.counts = {}
        for name, kinds in SPAWN_DENSITY.items():
            area = int(self.mask(name).sum())
            pool = [k for k, per in kinds.items() for _ in range(max(1, int(area * per / 1000)))]
            self.counts[name] = len(pool)
            rng.shuffle(pool)
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.reserve > 7))      # a spawn is placed up to a cell off the cell's centre: 4.4 keeps it 3.4+ tiles from every road (tests/seam-roads.py)
            if not len(pts):
                self.short[name] = len(pool)
                continue
            sep, placed, tries = 11.0, 0, 0
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
        ordinary.sort(key=lambda t: t['kind'] != 'miragejackal')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


# ---- moving the old people, places and portals ---------------------------------------------------------------------------
def shifted_state(zone, old, G):
    """The refuge, its people, places, the cross and the gates in the new frame."""
    dx, dy = D_HUB
    c = old['city']
    zone['city'] = dict(c, x0=c['x0'] + dx, x1=c['x1'] + dx, y0=c['y0'] + dy, y1=c['y1'] + dy, plaza=dict(x=c['plaza']['x'] + dx, y=c['plaza']['y'] + dy),
                        entry=dict(x=c['entry']['x'] + dx, y=c['entry']['y'] + dy))
    zone['spawn'] = dict(x=SPAWN[0], y=SPAWN[1])
    by = {n['id']: n for n in zone['npcs']}
    for n in old['npcs']:
        t = by.get(n['id'])
        if t:
            t['x'], t['y'] = round(n['x'] + dx, 2), round(n['y'] + dy, 2)
    for p in zone['places']:
        if p['id'] == 'es_11_m':
            p['x'], p['y'] = ES_PLACE
    for cx in zone['crosses']:
        cx['x'], cx['y'] = CROSS
    for p in zone['portals']:
        if p.get('seam'):           # the Astralhollow and Orrery seams (zone_shapes.make_seams): their line is the border, not a gate
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'], p['walk'] = round(gx, 2), round(gy, 2), list(walk)


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    G = gates(F)
    shifted_state(zone, old, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the refuge moved by its own delta, the waste was rebuilt
    d = Prismwaste(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    if any(p.get('seam') and p['to'] == 19 for p in zone['portals']):      # Stormglass's seam (2026-11-08) replaced the south gate: only the spawns within 7 tiles of it go
        d.late_dropped = drop_near_seam(zone, d, 19)
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    seamed = {p['id'] for p in zone['portals'] if p.get('seam')}      # Stormglass's seam replaced the south rim gate: its line is the border, not a gate
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items() if g not in seamed]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(zone, content.HAMLETS)
    # every crossing that arrives here follows the new frame: Stormglass's and Cairnspine's (the seams carry their own shift)
    inbound = {'path_14_19': ('path_19_14', 19), 'path_14_27': ('path_27_14', 27)}
    for mine, (theirs, zi) in inbound.items():
        if mine in seamed:          # a seam arrives where it was crossed (the neighbour's portal carries the shift)
            continue
        for p in world['zones'][zi - 1]['portals']:
            if p['id'] == theirs:
                p['tx'], p['ty'] = round(G[mine][3][0], 2), round(G[mine][3][1], 2)
    if write:
        content.record_mailboxes(zone, content.HAMLETS, ROOT / 'world/mailboxes.txt')
    problems = check(zone, d, solid, seen, G)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']), kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('sunspire', 'glassstone', 'saltbrush', 'mirrorwall', 'lens_pillar')})
    if problems:
        if os.environ.get('PRISM_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post', 'shade_tent')


def check(zone, d, solid, seen, G):
    problems = []
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    if not (lost < open_cells.sum() * .01):
        problems.append(f'{lost} open cells are cut off from the spawn')
    for t in zone['slimes']:
        if not d.floor[int(t['y']), int(t['x'])]:
            problems.append(f'spawn off land {t}')
        if not seen[int(t['y']), int(t['x'])]:
            problems.append(f'unreachable spawn {t}')
        if d.reserve[int(t['y']), int(t['x'])] <= 7:
            problems.append(f'spawn within 7 tiles of a seam {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
        if d.reserve[int(n['y']), int(n['x'])] < 20:
            problems.append(f"npc {n['id']} within 20 tiles of a seam")
    for p in zone['places']:
        if not seen[int(p['y']), int(p['x'])]:
            problems.append(f"unreachable place {p['id']}")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
        if not seen[int(gy - walk[1] * 3), int(gx - walk[0] * 3)]:
            problems.append(f'gate {g} is blocked from the inside')
    bad = set()
    for road in d.ROADLIST + [r['points'] for r in zone['exitRoutes']]:
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                if not d.floor[int(y), int(x)]:
                    problems.append(f'road leaves the land at {x:.0f},{y:.0f}')
                c = zone['city']
                inside = c['x0'] - 1 <= x <= c['x1'] + 1 and c['y0'] - 1 <= y <= c['y1'] + 3
                for fc in zone['camps']:
                    inside |= fc['x0'] - 1 <= x <= fc['x1'] + 1 and fc['y0'] - 1 <= y <= fc['y1'] + 3
                if not inside and solid[int(y), int(x)]:
                    bad.add((int(x), int(y)))
    if bad:
        problems.append(f'something stands on the road at {sorted(bad)[:12]}')
    # an elite stands clear of everything a player walks to: awareness plus 3 tiles from every road, place and person, and from every hub
    walked = [(p, 'road') for road in d.ROADLIST for p in dense_points(road)]
    walked += [((q['x'], q['y']), f"place {q['id']}") for q in zone['places']] + [((n['x'], n['y']), f"npc {n['id']}") for n in zone['npcs']]
    for kind, ex, ey in content.ELITES:
        near = min(((math.dist((ex, ey), p), what) for p, what in walked), key=lambda t: t[0])
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
        problems.append(f'art-less objects within the camera reach of a seam pop in on crossing: {popping[:5]}')
    loose = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o.get('layout') == d.TAG and o['kind'] != 'void' and d.reserve[int(o['y']), int(o['x'])] < 2.5]
    if loose:
        problems.append(f'loose scenery within 2.5 tiles of a seam: {loose[:5]}')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    names = list(REGIONS)
    def region_of(x, y):
        return names[int(d.region[int(y), int(x)])]
    want = {'mirrorqueen': 'court', 'sunshard': 'crown', 'shatterhorn': 'spires'}
    for kind, ex, ey in content.ELITES:
        if region_of(ex, ey) != want[kind]:
            problems.append(f'{kind} stands in {region_of(ex, ey)}')
    for h in content.HAMLETS.values():
        if d.reserve[int(h['y']), int(h['x'])] < 20 + h['hw']:
            problems.append(f"{h['name']} stands within 20 tiles of a seam")
    return problems


def plan_picture(zone, d, out, scale=4):
    from PIL import Image, ImageDraw
    n = d.n
    T = zone['shape']['T']
    s = 1758 / 2048
    atlas = Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB')
    x0, y0 = int(round(T[0] * s)), int(round(T[1] * s))
    bg = atlas.crop((x0, y0, x0 + int(n * s), y0 + int(n * s))).resize((n * scale, n * scale), Image.LANCZOS)
    bg = Image.blend(bg, Image.new('RGB', bg.size, (60, 50, 70)), .45)
    pal = {1: (170, 110, 120), 2: (200, 180, 160), 3: (150, 110, 150), 4: (160, 80, 120), 5: (220, 190, 120), 6: (100, 110, 140), 7: (130, 110, 100), 8: (190, 120, 190), 9: (110, 150, 170), 10: (120, 50, 60)}
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
    col = {'sunspire': (255, 150, 230), 'glassstone': (130, 120, 150), 'saltbrush': (90, 130, 90), 'mirrorwall': (200, 230, 255), 'lens_pillar': (255, 240, 170),
           'broken_crown': (255, 140, 60), 'shade_tent': (255, 200, 90)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('saltbrush',) else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'miragejackal': (240, 120, 120), 'shardscarab': (80, 200, 255), 'glassharrier': (120, 220, 80), 'prismsentinel': (230, 100, 230)}
    for s_ in zone['slimes']:
        c = kc.get(s_['kind'], (255, 20, 20))
        g.rectangle([s_['x'] * scale - 2, s_['y'] * scale - 2, s_['x'] * scale + 2, s_['y'] * scale + 2], fill=c, outline=(0, 0, 0))
    c = zone['city']
    g.rectangle([c['x0'] * scale, c['y0'] * scale, c['x1'] * scale, c['y1'] * scale], outline=(255, 255, 0), width=2)
    for camp in zone['camps']:
        g.rectangle([camp['x0'] * scale, camp['y0'] * scale, camp['x1'] * scale, camp['y1'] * scale], outline=(255, 120, 0), width=2)
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
