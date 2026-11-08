#!/usr/bin/env python3
"""The Obsidian Orrery as an authored map (zone 15 of the shapes pilot): no filler land, the whole outline used.

Owner request 2026-11-08: "for pilot. reshape orrey. and remake the zone and quests to fit the new shape. no fillers." Owner answers: keep the Pendulum
Matron and the Epoch Engine and add one new elite with no quest, three new outposts, and the Orrery is seamless against Astralhollow (its north border)
and the Moonspore Canopy (its south border); the Crags, Nacrehold, the Prismwaste, Stormglass and Emberwake stay walk-in gates on the rim. The zone keeps its
own style: the starry black plain, three broken rings of clockwall round the machine's axis, obsidian spires, cogstones, timegrass, the Stillpoint refuge
and the Epoch Crown, four families banded by distance from the refuge (bronze mantises, gearlings, orbit seers, chronoguards).

Runs in `zone_shapes.py apply` after Astralhollow's design. The zone is `designOnly` (zone-shapes.txt, `seamWith {15: [13, 16]}`): it keeps the outline floor
(`shapeFloor`), takes no filler, and places its own gates (`place_portals` skips it). Astralhollow's approved design ran unchanged with its Orrery gate as a
phantom (its seam portal replaced the gate: astral_design.shifted_state); the Moonspore Canopy is a filler zone and only lost its gate. The borders to
Astralhollow and the Moonspore Canopy are reserved from `shape.edges` runs exactly as Astralhollow reserved this one: no art-less object or person within
20 tiles, no spawn within 7, no loose scenery within 2.5.

The painted atlas (tile = painted px * 2048/1758 - shape.T, T = [772, 310]) shows a dark starry plain with two trunk roads running down from the north,
a diamond of roads in the west, an X where they cross in the middle, a pale plaza at the south-west corner (the Stillpoint) and big obsidian shards.

Fixed, moved as a rigid block from `world/zone-shapes/preshape-15.txt` (the old layout): the Stillpoint (the pavilion and two hour pillars) with every
person. Every person, place, portal and quest keeps its id.

    python3 scripts/orrery_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
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
import orrery_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-15.txt'

ZONE = 15
D_HUB = (50, 189)          # old refuge (rect 11..48 x 103..125, plaza 29,112) -> plaza (79, 301)
SPAWN = (66.0, 301.0)
CROSS = (64.0, 230.0)      # the Ember Grave Cross: a quiet hollow in the Gearyards
ES_PLACE = (98.0, 176.0)   # The Clock That Counts Downward
AXIS = (140.0, 181.0)
CROWN = (192.0, 50.0)
RIM = 3

REGIONS = {
    'still':      dict(name='The Stillpoint', seeds=[(79, 301)]),
    'meadows':    dict(name='The Brass Meadows', seeds=[(150, 302), (196, 300), (120, 270), (225, 280), (165, 262)]),
    'verge':      dict(name='The Dust Verge', seeds=[(40, 256), (42, 214), (34, 176)]),
    'yards':      dict(name='The Gearyards', seeds=[(76, 238), (92, 206), (62, 198)]),
    'lowerring':  dict(name='The Lower Ring', seeds=[(166, 216), (160, 240), (122, 236), (186, 190)]),
    'axis':       dict(name='The Axis', seeds=[(140, 181), (120, 166), (166, 168), (160, 148)]),
    'westcourt':  dict(name='The Winding Court', seeds=[(104, 114), (84, 130), (122, 94), (110, 142)]),
    'terraces':   dict(name='The Seer Terraces', seeds=[(182, 120), (190, 136), (176, 98), (196, 162)]),
    'reaches':    dict(name='The Obsidian Reaches', seeds=[(258, 100), (252, 160), (262, 214), (246, 62), (276, 44)]),
    'crown':      dict(name='The Crown Valley', seeds=[(192, 52), (196, 74), (176, 40), (208, 68)]),
    'northwest':  dict(name='The Hourglass Heath', seeds=[(118, 46), (136, 30), (100, 60), (152, 56), (88, 40)]),
    'southeast':  dict(name='The Escapement', seeds=[(252, 248), (278, 232), (218, 262)]),
}

# the roads follow the painted atlas (tile coordinates); the gate roads are added by `roads()` from the arrival points
W_TRUNK = [(163, 26), (163, 52), (163, 82), (170, 100)]
NW_DIAG = [(163, 44), (135, 53), (105, 72), (80, 90), (57, 134)]
W_LOWER = [(57, 134), (80, 148), (105, 160), (125, 173), (140, 181)]
MID_W = [(170, 100), (166, 112), (163, 126), (150, 142), (140, 156), (138, 170), (140, 181)]
MID_E = [(170, 100), (180, 120), (190, 142)]
CROSS_X = [(190, 142), (170, 153), (150, 166), (140, 181)]
CROSS_E = [(190, 142), (205, 138)]
E_TRUNK = [(230, 25), (222, 42), (218, 60), (212, 85), (207, 105), (205, 125), (205, 140), (206, 160), (205, 180), (209, 200), (215, 225), (224, 236)]
E_LEFT = [(207, 200), (202, 215), (200, 235), (197, 255), (190, 280)]
E_LOOP = [(224, 236), (205, 241), (180, 248), (150, 256), (130, 261)]
AXIS_S = [(140, 181), (134, 196), (128, 212), (127, 235), (130, 258)]
AXIS_LOOP = [(143, 198), (158, 215), (165, 232), (150, 248), (131, 260)]
LOWER_W = [(130, 261), (115, 272), (100, 280)]
LOWER_S = [(129, 262), (128, 284)]
PLAZA_E = [(120, 285), (160, 285), (200, 282), (245, 278)]
PLAZA_E2 = [(120, 311), (145, 312), (175, 313)]
HUB_N = [(66, 301), (80, 298), (98, 287), (112, 284), (120, 285)]
HUB_W = [(98, 287), (100, 280)]
HUB_E = [(98, 308), (110, 310), (120, 311)]
WEST_ROAD = [(34, 186), (31, 220), (32, 250), (36, 280), (50, 294), (66, 301)]
BELL_SPUR = [(60, 128), (72, 124)]
CROWN_SPUR = [(163, 82), (178, 82)]
CROWN_ROAD = [(190, 70), (191, 58)]
WATCH_SPUR = [(205, 138), (230, 134), (242, 130)]
STILL_LANE = [(100, 280), (96, 272)]
BELL_LANE = [(80, 90), (80, 98)]
GATE_LANE = [(180, 120), (188, 114)]
SHARD_LANE = [(230, 62), (262, 68)]

R = {'blackspire': .72, 'cogstone': .48, 'timegrass': .22, 'clockwall': 1.05, 'hourpillar': .7, 'epoch_crown': 1.6, 'stillpoint': 1.7}
GROUND = {'brass': 1, 'dust': 2, 'gear': 3, 'ring': 4, 'axis': 5, 'glass': 6, 'valley': 7, 'heath': 8, 'ash': 9}
REGION_GROUND = {'still': 'brass', 'meadows': 'brass', 'verge': 'dust', 'yards': 'gear', 'lowerring': 'ring', 'axis': 'axis', 'westcourt': 'heath', 'terraces': 'valley',
                 'reaches': 'glass', 'crown': 'valley', 'northwest': 'heath', 'southeast': 'dust'}

# scenery per 1000 land tiles of the region
DENSITY = {
    'still':     [('timegrass', 8)],
    'meadows':   [('timegrass', 24), ('cogstone', 3), ('blackspire', 1.5)],
    'verge':     [('timegrass', 10), ('cogstone', 4), ('blackspire', 5)],
    'yards':     [('cogstone', 14), ('timegrass', 6), ('blackspire', 3)],
    'lowerring': [('cogstone', 8), ('timegrass', 8), ('blackspire', 4)],
    'axis':      [('cogstone', 5), ('blackspire', 5), ('timegrass', 5)],
    'westcourt': [('blackspire', 8), ('cogstone', 3), ('timegrass', 8)],
    'terraces':  [('blackspire', 7), ('timegrass', 6), ('cogstone', 4)],
    'reaches':   [('blackspire', 14), ('cogstone', 2), ('timegrass', 3)],
    'crown':     [('blackspire', 6), ('cogstone', 6), ('timegrass', 5)],
    'northwest': [('blackspire', 7), ('timegrass', 10), ('cogstone', 3)],
    'southeast': [('timegrass', 12), ('cogstone', 6), ('blackspire', 5)],
}
# (kind, count): difficulty comes from which kind stands where (a spawn has no level): mantises by the refuge, then gearlings, seers, chronoguards to the north
SPAWNS = {
    'meadows':   {'bronzemantis': 46, 'gearling': 6},
    'verge':     {'bronzemantis': 20, 'gearling': 12},
    'yards':     {'gearling': 26, 'bronzemantis': 8},
    'lowerring': {'gearling': 28, 'orbitseer': 6},
    'axis':      {'orbitseer': 20, 'gearling': 8},
    'westcourt': {'chronoguard': 16, 'orbitseer': 10},
    'terraces':  {'orbitseer': 26},
    'reaches':   {'orbitseer': 12, 'chronoguard': 20},
    'crown':     {'chronoguard': 22},
    'northwest': {'chronoguard': 14, 'orbitseer': 8},
    'southeast': {'gearling': 12, 'bronzemantis': 12, 'orbitseer': 4},
}
# stands of obelisks where the painting shows its big shards: centre, radius
SHARD_STANDS = [(136, 128, 9), (121, 24, 7), (70, 196, 8), (86, 248, 9), (262, 58, 10), (276, 150, 8)]


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
    """The five crossings that stay gates stand on the rim, six tiles in from the void edge: id -> (x, y, walk, arrival). Every one keeps its destination.
    The Astralhollow and Moonspore borders are seams (no gate)."""
    out = {}
    def west(y):
        x0 = int(np.nonzero(F[y])[0].min())
        return (x0 + 3.5, y + .5)
    def east(y):
        x1 = int(np.nonzero(F[y])[0].max())
        return (x1 - 2.5, y + .5)
    def south(x):
        y1 = int(np.nonzero(F[:, x])[0].max())
        return (x + .5, y1 - 2.5)
    def north(x):
        y0 = int(np.nonzero(F[:, x])[0].min())
        return (x + .5, y0 + 3.5)
    x, y = west(92)
    out['path_15_9'] = (x, y, (-1, 0), (x + 6, y))
    x, y = west(248)
    out['path_15_1'] = (x, y, (-1, 0), (x + 6, y))
    x, y = north(312)
    out['orrery_prism_gate'] = (x, y, (0, -1), (x, y + 6))
    x, y = east(150)
    out['path_15_19'] = (x, y, (1, 0), (x - 6, y))
    x, y = south(236)
    out['atlas_15_45'] = (x, y, (0, 1), (x, y - 6))
    return out


def roads(G):
    nac, crags, prism, storm, ember = G['path_15_9'], G['path_15_1'], G['orrery_prism_gate'], G['path_15_19'], G['atlas_15_45']
    return [W_TRUNK, NW_DIAG, W_LOWER, MID_W, MID_E, CROSS_X, CROSS_E, E_TRUNK, E_LEFT, E_LOOP, AXIS_S, AXIS_LOOP, LOWER_W, LOWER_S, PLAZA_E, PLAZA_E2,
            HUB_N, HUB_W, HUB_E, WEST_ROAD, BELL_SPUR, CROWN_SPUR, CROWN_ROAD, WATCH_SPUR, STILL_LANE, BELL_LANE, GATE_LANE, SHARD_LANE,
            # the gate roads: from the arrival point to the network
            [(nac[0], nac[1]), nac[3], (70, 91), (80, 90)],
            [(crags[0], crags[1]), crags[3], (32, 250)],
            [(prism[0], prism[1]), prism[3], (296, 28), (262, 27), (232, 26)],
            [(storm[0], storm[1]), storm[3], (250, 156), (206, 160)],
            [(ember[0], ember[1]), ember[3], (241, 278), (245, 278)]]


class Orrery(Designer):
    TAG, SEED = 'orrery_design_v1', 20261108
    LATE_SEAMS = set()

    def __init__(self, world, old):
        self.old = old
        self.G = gates(np.array([[c == '#' for c in row] for row in world['shapeFloor']]))
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        # the borders to Astralhollow (13) and the Moonspore Canopy (16) are seams: nothing the other side cannot draw stands near them
        self.reserve = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] in (13, 16):
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

    def oval(self, centre, rx, ry, step, kind, jitter=.5, lane=4.5, skip=()):
        """A broken ring of `kind` along an ellipse, open wherever a road crosses it (lane tiles each side)."""
        n = int(math.tau * (rx + ry) / 2 / step)
        placed = 0
        for i in range(n):
            a = i / n * math.tau + self.rng.uniform(-.02, .02)
            x = centre[0] + math.cos(a) * rx + self.rng.uniform(-jitter, jitter)
            y = centre[1] + math.sin(a) * ry + self.rng.uniform(-jitter, jitter)
            ix, iy = int(x), int(y)
            if not (0 <= ix < self.n and 0 <= iy < self.n) or not self.inner[iy, ix] or self.blocked[iy, ix] or self.road[iy, ix] < lane or self.reserve[iy, ix] < 3:
                continue
            if any(math.hypot(x - sx, y - sy) < sr for sx, sy, sr in skip):
                continue
            if self.grid.free(x, y, R[kind], .8):
                self.add(kind, x, y, v=i % 4)
                placed += 1
        return placed

    def fill(self, name, kinds, gap=.8, road=2.8):
        area = int(self.mask(name).sum())
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per / 1000))
            placed += self.scatter([kind], k, self.mask(name) & (self.reserve > 3.5), gap=gap if kind != 'blackspire' else 1.3, road=road if kind != 'blackspire' else 3.6)
        return placed

    def take_hub(self):
        old = self.old
        out = []
        for o in old['objects']:
            if o['kind'] in ('stillpoint', 'hourpillar') and 5 < o['x'] < 50 and o['y'] > 100:
                q = moved(o, *D_HUB)
                q['layout'] = self.TAG
                out.append(q)
                self.grid.add(q['x'], q['y'], max(q['r'], q.get('width', 0) / 2))
        return out

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        w, rng = self.w, self.rng
        self.fixed = self.take_hub()
        crown = dict(kind='epoch_crown', x=CROWN[0], y=CROWN[1], r=1.6, v=0, layout=self.TAG)
        self.fixed.append(crown)
        self.grid.add(CROWN[0], CROWN[1], 1.6)
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
        # the three broken rings of the machine, round the Axis: open at every road
        self.oval(AXIS, 26, 24, 4.6, 'clockwall', skip=elites + hamlets)
        self.oval(AXIS, 50, 46, 5.2, 'clockwall', skip=elites + hamlets)
        self.oval(AXIS, 76, 70, 5.8, 'clockwall', skip=elites + hamlets + [(CROSS[0], CROSS[1], 12)])
        # the Axis: four hour pillars round the crossing and a ring of cogstones
        for sx, sy in ((-7, -7), (7, -7), (7, 7), (-7, 7)):
            x, y = AXIS[0] + sx, AXIS[1] + sy
            if self.grid.free(x, y, .7, .8):
                self.add('hourpillar', x, y, v=0)
        self.ring_of(AXIS, 12, 10, 'cogstone', rot=.2)
        # the Crown: hour pillars flank the road up to it and a ring of obelisks stands round the Engine's court
        for sx in (-9, 9):
            x, y = CROWN[0] + sx, CROWN[1] + 8
            if self.grid.free(x, y, .7, .8):
                self.add('hourpillar', x, y, v=0)
        # the Stillpoint's dial: a ring of cogstones round the hold circle, and two pillars at each trunk junction
        self.ring_of((96, 268), 6.5, 8, 'cogstone', rot=.4)
        for jx, jy in ((170, 100), (190, 142), (130, 259), (224, 236)):
            for sx, sy in ((-4.5, -4.5), (4.5, 4.5)):
                x, y = jx + sx, jy + sy
                if 0 <= int(x) < self.n and 0 <= int(y) < self.n and self.inner[int(y), int(x)] and self.road[int(y), int(x)] > 2.6 and self.reserve[int(y), int(x)] > 20 and self.grid.free(x, y, .7, .8):
                    self.add('hourpillar', x, y, v=0)
        # the Pyre Hollow round the Ember Grave Cross: a ring of cogstones
        self.ring_of(CROSS, 5.2, 8, 'cogstone', rot=.4)
        # the elites' rings: a low ring of cogstones marks where each stands
        for _, x, y in content.ELITES:
            self.ring_of((x, y), 5.5, 6, 'cogstone', rot=.7)
        # the painting's big obsidian shards: stands of obelisks
        for cx, cy, rad in SHARD_STANDS:
            self.ring_of((cx, cy), rad, max(6, int(rad * 1.1)), 'blackspire', rot=cx * .13)
            self.ring_of((cx, cy), rad * .45, 4, 'blackspire', rot=cy * .11)

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        tall = ('blackspire', 'clockwall', 'hourpillar')
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
        tags = {t for *_, t in content.AMBUSH}
        # the Ember Grave Cross's sleeper moves with the cross
        sleepers = [dict(s, x=round(CROSS[0] - 2.5, 2), y=CROSS[1]) for s in self.old['slimes'] if s.get('ambush') and s['kind'] == 'ember_firelord']
        out = list(sleepers) + [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
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
        for name, kinds in SPAWNS.items():
            pool = [k for k, c in kinds.items() for _ in range(c)]
            rng.shuffle(pool)
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 3.5) & (self.reserve > 7))
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
        ordinary.sort(key=lambda t: t['kind'] != 'bronzemantis')
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
        if p['id'] == 'es_12_m':
            p['x'], p['y'] = ES_PLACE
    for cx in zone['crosses']:
        cx['x'], cx['y'] = CROSS
    for p in zone['portals']:
        if p.get('seam'):           # the Astralhollow and Moonspore seams (zone_shapes.make_seams): their line is the border, not a gate
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'], p['walk'] = round(gx, 2), round(gy, 2), list(walk)


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    G = gates(F)
    shifted_state(zone, old, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the refuge moved by its own delta, the plain was rebuilt
    d = Orrery(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items()]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(zone, content.HAMLETS)
    # every crossing that arrives here follows the new frame: the Crags', Nacrehold's, the Prismwaste's, Stormglass's and Emberwake's (the seams carry their own shift)
    inbound = {'path_15_9': ('path_9_15', 9), 'path_15_1': ('path_1_15', 1), 'orrery_prism_gate': ('prism_orrery_gate', 14), 'path_15_19': ('path_19_15', 19),
               'atlas_15_45': ('atlas_45_15', 45)}
    for mine, (theirs, zi) in inbound.items():
        for p in world['zones'][zi - 1]['portals']:
            if p['id'] == theirs:
                p['tx'], p['ty'] = round(G[mine][3][0], 2), round(G[mine][3][1], 2)
    if write:
        content.record_mailboxes(zone, content.HAMLETS, ROOT / 'world/mailboxes.txt')
    problems = check(zone, d, solid, seen, G)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']), kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('clockwall', 'blackspire', 'cogstone', 'timegrass', 'hourpillar')})
    if problems:
        if os.environ.get('ORRERY_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')


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
    want = {'pendulummatron': 'westcourt', 'epochengine': 'crown', 'mainspringwyrm': 'reaches'}
    for kind, ex, ey in content.ELITES:
        if region_of(ex, ey) != want[kind]:
            problems.append(f'{kind} stands in {region_of(ex, ey)}')
    # the hold circles, visit places and hamlets stand in the regions their quests name
    return problems


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    pal = {0: (40, 44, 70), 1: (110, 100, 70), 2: (90, 70, 60), 3: (80, 90, 110), 4: (70, 60, 100), 5: (150, 120, 80), 6: (30, 20, 50), 7: (60, 90, 120), 8: (80, 60, 100), 9: (80, 40, 50)}
    a = np.zeros((n, n, 3), np.uint8)
    a[:] = (10, 10, 20)
    for k, c in pal.items():
        a[(d.ground == k) & d.floor] = c
    im = Image.fromarray(a).resize((n * scale, n * scale), Image.NEAREST)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(230, 200, 120), width=scale)
    col = {'clockwall': (200, 170, 120), 'blackspire': (160, 170, 200), 'cogstone': (150, 150, 160), 'timegrass': (110, 130, 110), 'hourpillar': (255, 230, 150),
           'stillpoint': (255, 200, 90), 'epoch_crown': (255, 140, 60)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('timegrass',) else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'bronzemantis': (240, 120, 120), 'gearling': (80, 200, 255), 'orbitseer': (120, 220, 80), 'chronoguard': (230, 100, 230)}
    for s in zone['slimes']:
        c = kc.get(s['kind'], (255, 20, 20))
        g.rectangle([s['x'] * scale - 2, s['y'] * scale - 2, s['x'] * scale + 2, s['y'] * scale + 2], fill=c, outline=(0, 0, 0))
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
    im.save(out)


def main():
    world = json.loads(MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])


if __name__ == '__main__':
    main()
