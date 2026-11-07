#!/usr/bin/env python3
"""Astralhollow as an authored map (zone 13 of the shapes pilot): no filler land, the whole outline used.

Owner request 2026-11-07: "for pilot. reshape astralhollow. and remake the zone and quests to fit the new shape. no fillers." Owner answers: three
new elites (the zone had none; two with a quest, one without), three new outposts. The zone keeps its own style: the grassy impact basin, living
starglass groves and crystal spires, the observatory court and its starwell, five families by distance from the court, the lamps.

Runs in `zone_shapes.py apply` after Nacrehold's design. The zone is `designOnly` (zone-shapes.txt, `seamWith {13: []}`): it keeps the outline floor
(`shapeFloor`), takes no filler, and places its own gates (`place_portals` skips it). No seam is possible today (the Deep and Nacrehold exclude it,
the Prismwaste and the Orrery are not in the pilot), so all four crossings stay portals. The Orrery is the pilot's next candidate, so the borders to
the Prismwaste and the Orrery are reserved now exactly as the Deep reserved Nacrehold's: no art-less object or person within 20 tiles, no spawn
within 7, no loose scenery within 2.5 (`shape.edges` runs, not seam portals, so a later seam cannot change this design's masks or its RNG order).

The painted atlas (tile = painted px * 2048/1758 - shape.T, T = [770, 0]) shows a dark teal land with a pale court at the south end, one golden
trunk road straight up the middle, an oval ring road around a crater, and big cyan crystals along the ring: the design follows it.

Fixed, moved as a rigid block from `world/zone-shapes/preshape-13.txt` (the old layout): the Observatory Court (observatory, starwell, two houses,
six lamps) with every person, the Empty Seat place, the Ember Grave Cross and its sleeper. Every person, place, portal and quest keeps its id.

    python3 scripts/astral_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
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
import astral_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-13.txt'

ZONE = 13
D_HUB = (108, 178)         # old court (rect 45..83 x 106..124, plaza 64,116) -> plaza (172, 294)
SPAWN = (172.0, 294.0)
CROSS = (196.0, 128.0)     # the Ember Grave Cross: a quiet hollow inside the east side of the ring
RIM = 3

REGIONS = {
    'court':    dict(name='The Observatory Court', seeds=[(172, 293)]),
    'meadows':  dict(name='The Lantern Meadows', seeds=[(130, 306), (152, 322), (214, 310), (196, 326), (118, 280), (230, 288), (146, 262), (202, 258)]),
    'orchard':  dict(name='The Moth Orchard', seeds=[(100, 264), (106, 240), (240, 262), (250, 236), (246, 286)]),
    'glass':    dict(name='The Singing Glass', seeds=[(222, 244), (232, 220), (206, 224), (214, 252)]),
    'choir':    dict(name='The Choir Hollows', seeds=[(112, 200), (104, 178), (126, 186), (110, 214)]),
    'crossing': dict(name='The Hearth Crossing', seeds=[(176, 224), (160, 200), (190, 196), (170, 246)]),
    'heart':    dict(name='The Heart of the Fall', seeds=[(172, 152), (150, 142), (196, 150), (178, 120)]),
    'comet':    dict(name='The Cometfield', seeds=[(246, 150), (240, 190), (232, 118), (244, 172)]),
    'ringwest': dict(name='The Broken Ring', seeds=[(118, 128), (124, 104), (110, 152), (138, 116)]),
    'eclipse':  dict(name='The Eclipse Wood', seeds=[(112, 78), (132, 70), (100, 100), (142, 94), (84, 70), (92, 54)]),
    'dusk':     dict(name='The Dusk Spurs', seeds=[(228, 72), (252, 62), (214, 98), (200, 76)]),
    'fall':     dict(name='The Fallstone Fields', seeds=[(172, 34), (150, 22), (198, 34), (172, 64)]),
    'crown':    dict(name="The Comet's Crown", seeds=[(96, 34), (120, 18), (70, 36), (132, 40)]),
}

# the trunk (the Starway), the ring, the spurs and the four gate roads (`roads()` adds the arrival points of the gates)
TRUNK_S = [(172, 296), (179, 292), (179, 276), (176, 262), (176, 238)]     # round the observatory, which stands north of the starwell
TRUNK_N = [(176, 238), (172, 215), (160, 190), (150, 165), (150, 150), (158, 128), (168, 106), (172, 78), (172, 48), (172, 18)]
RING_W = [(176, 238), (150, 234), (130, 222), (120, 205), (120, 192), (116, 176), (112, 150), (118, 122), (136, 98), (156, 84), (172, 78)]
RING_E = [(176, 238), (205, 232), (222, 216), (228, 196), (222, 176), (226, 150), (222, 124), (204, 100), (186, 84), (172, 78)]
LOOP_SW = [(153, 290), (140, 270), (138, 250), (130, 222)]
LOOP_SE = [(191, 290), (210, 280), (220, 255), (222, 216)]
SPUR_NW = [(156, 84), (140, 66), (124, 48), (110, 34)]
SPUR_NE = [(204, 100), (218, 80), (230, 66), (238, 58)]
FALL_W = [(172, 48), (150, 30), (130, 20)]
FALL_E = [(172, 48), (200, 38), (222, 32)]
FIRE_LANE = [(222, 176), (206, 168)]
CHORD_LANE = [(120, 192), (128, 168)]
LAMP_LANE = [(205, 232), (203, 270)]
LINE_LANE = [(172, 48), (200, 54)]

R = {'crystal': .95, 'astraltree': .52, 'starstone': .45, 'astralshrub': .28, 'starbloom': .17, 'obelisk': .9, 'astrolamp': .35, 'starwell': .9, 'astralhouse': 1.8}
GROUND = {'lantern': 1, 'loam': 2, 'glass': 3, 'hollow': 4, 'ash': 5, 'comet': 6, 'dusk': 7, 'eclipse': 8, 'scree': 9}
REGION_GROUND = {'meadows': 'lantern', 'orchard': 'loam', 'glass': 'glass', 'choir': 'hollow', 'heart': 'ash', 'comet': 'comet', 'ringwest': 'dusk', 'eclipse': 'eclipse',
                 'dusk': 'dusk', 'fall': 'scree', 'crown': 'scree'}

# scenery per 1000 land tiles of the region
DENSITY = {
    'court':    [('astralshrub', 6), ('starbloom', 10), ('starstone', 1.5)],
    'meadows':  [('astralshrub', 7), ('starbloom', 20), ('starstone', 2.5), ('astraltree', 2)],
    'orchard':  [('astralshrub', 5), ('starbloom', 10), ('starstone', 2)],
    'glass':    [('crystal', 9), ('starstone', 4), ('starbloom', 5), ('astralshrub', 3)],
    'choir':    [('crystal', 7), ('astralshrub', 4), ('starstone', 3.5), ('starbloom', 5)],
    'crossing': [('starstone', 4), ('astralshrub', 4.5), ('starbloom', 12), ('astraltree', 3.5)],
    'heart':    [('starstone', 10), ('crystal', 2.5), ('starbloom', 3)],
    'comet':    [('starstone', 5), ('crystal', 4.5), ('starbloom', 4), ('astralshrub', 3)],
    'ringwest': [('crystal', 5), ('astralshrub', 5), ('starbloom', 6), ('starstone', 3)],
    'eclipse':  [('astraltree', 26), ('astralshrub', 8), ('starbloom', 3), ('starstone', 2)],
    'dusk':     [('astraltree', 6), ('crystal', 4.5), ('starstone', 5), ('astralshrub', 4)],
    'fall':     [('starstone', 11), ('crystal', 2), ('obelisk', .4), ('starbloom', 1.5)],
    'crown':    [('starstone', 8), ('astraltree', 5), ('crystal', 4), ('astralshrub', 4)],
}
# (kind, count): difficulty comes from which kind stands where (a spawn has no level)
SPAWNS = {
    'meadows':  {'voidmoth': 34},
    'orchard':  {'voidmoth': 22, 'crystalwyrm': 6},
    'glass':    {'crystalwyrm': 26},
    'choir':    {'crystalwyrm': 18, 'orbitbeetle': 12},
    'crossing': {'crystalwyrm': 20},
    'heart':    {'orbitbeetle': 20},
    'comet':    {'orbitbeetle': 24},
    'ringwest': {'orbitbeetle': 14, 'eclipsedryad': 10},
    'eclipse':  {'eclipsedryad': 36},
    'dusk':     {'eclipsedryad': 12, 'meteorgolem': 14},
    'fall':     {'meteorgolem': 26},
    'crown':    {'meteorgolem': 16, 'eclipsedryad': 8},
}


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
    """The four crossings stand on the rim, six tiles in from the void edge: id -> (x, y, walk, arrival). Every one keeps its destination."""
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
    x, y = west(296)
    out['astral_nacre_gate'] = (x, y, (-1, 0), (x + 6, y))
    x, y = west(226)
    out['path_13_8'] = (x, y, (-1, 0), (x + 6, y))
    x, y = east(195)
    out['astral_prism_gate'] = (x, y, (1, 0), (x - 6, y))
    x, y = south(172)
    out['path_13_15'] = (x, y, (0, 1), (x, y - 6))
    return out


def roads(G):
    nac, deep, prism, orr = G['astral_nacre_gate'], G['path_13_8'], G['astral_prism_gate'], G['path_13_15']
    return [TRUNK_S, TRUNK_N, RING_W, RING_E, LOOP_SW, LOOP_SE, SPUR_NW, SPUR_NE, FALL_W, FALL_E, FIRE_LANE, CHORD_LANE, LAMP_LANE, LINE_LANE,
            # the gate roads: from the arrival point to the network
            [(153, 294), (130, 296), (112, 296), nac[3], (nac[0], nac[1])],
            [(130, 222), (110, 226), deep[3], (deep[0], deep[1])],
            [(228, 196), (240, 195.5), prism[3], (prism[0], prism[1])],
            [(172, 302), (172, 316), orr[3], (orr[0], orr[1])]]


class Astralhollow(Designer):
    TAG, SEED = 'astral_design_v1', 20261112
    LATE_SEAMS = set()

    def __init__(self, world, old):
        self.old = old
        self.G = gates(np.array([[c == '#' for c in row] for row in world['shapeFloor']]))
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        # the borders to the Prismwaste (14) and the Orrery (15): the next pilot zone's seam, kept free now
        self.reserve = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] in (14, 15):
                self.reserve = np.minimum(self.reserve, seg_field(e['points'], self.xs, self.ys))

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ring_of(self, centre, radius, n, kind, rot=.3, gaps=True, **extra):
        k = 0
        for i in range(n):
            a = i / n * math.tau + rot
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if 0 <= int(x) < self.n and 0 <= int(y) < self.n and self.inner[int(y), int(x)] and self.road[int(y), int(x)] > 2.4 and self.reserve[int(y), int(x)] > 3 and self.grid.free(x, y, R.get(kind, .5), .3):
                self.add(kind, x, y, **extra)
                k += 1
        return k

    def oval(self, centre, rx, ry, step, kind, jitter=.8, lane=4.5, skip=()):
        """A broken ring of `kind` along an ellipse, open wherever a road crosses it (lane tiles each side)."""
        n = int(math.tau * (rx + ry) / 2 / step)
        placed = 0
        for i in range(n):
            a = i / n * math.tau + self.rng.uniform(-.03, .03)
            x = centre[0] + math.cos(a) * rx + self.rng.uniform(-jitter, jitter)
            y = centre[1] + math.sin(a) * ry + self.rng.uniform(-jitter, jitter)
            ix, iy = int(x), int(y)
            if not (0 <= ix < self.n and 0 <= iy < self.n) or not self.inner[iy, ix] or self.blocked[iy, ix] or self.road[iy, ix] < lane or self.reserve[iy, ix] < 3:
                continue
            if any(math.hypot(x - sx, y - sy) < sr for sx, sy, sr in skip):
                continue
            if self.grid.free(x, y, R[kind], .8):
                self.add(kind, x, y)
                placed += 1
        return placed

    def fill(self, name, kinds, gap=.8, road=2.8, extra=None):
        area = int(self.mask(name).sum())
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per / 1000))
            weights = [kind]
            placed += self.scatter(weights, k, self.mask(name) & (self.reserve > 3.5), gap=gap if kind != 'crystal' else 1.4, road=road if kind != 'crystal' else 4.0)
        return placed

    def take_hub(self):
        old = self.old
        out = []
        for o in old['objects']:
            if o['kind'] in ('observatory', 'starwell', 'astralhouse', 'astrolamp') and 40 < o['x'] < 90 and 100 < o['y'] < 128:
                q = moved(o, *D_HUB)
                q['layout'] = self.TAG
                out.append(q)
                self.grid.add(q['x'], q['y'], max(q['r'], q.get('width', 0) / 2))
        return out

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        w, rng = self.w, self.rng
        self.fixed = self.take_hub()
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
        self.lamps()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def landmarks(self):
        rng = self.rng
        # the Impact Ring: two broken rings of crystal round the crater, open at every road
        c = (175, 157)
        self.oval(c, 78, 90, 5.6, 'crystal', lane=5.5, skip=[(x, y, 12) for _, x, y in content.ELITES] + [(h['x'], h['y'], 16) for h in content.HAMLETS.values()])
        self.oval(c, 52, 64, 6.2, 'crystal', lane=5.5, skip=[(x, y, 12) for _, x, y in content.ELITES])
        # the Heart of the Fall: a ring of fallen stone and a ring of obelisks round the crater floor
        self.ring_of((172, 152), 19, 14, 'starstone', rot=.2)
        self.ring_of((172, 152), 29, 9, 'obelisk', rot=.5)
        # the Choir Stones, the Hearth Crossing's waystones and the Falling Line's craters
        self.ring_of((102, 178), 6.5, 9, 'obelisk', rot=.1)
        for a in range(4):
            x, y = 176 + math.cos(a * math.tau / 4 + .4) * 11, 236 + math.sin(a * math.tau / 4 + .4) * 11
            if self.inner[int(y), int(x)] and self.road[int(y), int(x)] > 3 and self.grid.free(x, y, .9, 1):
                self.add('obelisk', x, y)
        for i, (cx, cy) in enumerate(((152, 8), (166, 14), (180, 22), (196, 30), (212, 38))):
            if self.inner[cy, cx]:
                self.ring_of((cx, cy), 3.4, 6, 'starstone', rot=i)
        # the Pyre Hollow round the Ember Grave Cross
        self.ring_of(CROSS, 5.2, 8, 'starstone', rot=.4)
        # the elites' rings: a low ring of starstone marks where each stands
        for _, x, y in content.ELITES:
            self.ring_of((x, y), 5.5, 6, 'starstone', rot=.7)
        # the Moth Orchard: trees in rows, with aisles a player can walk down
        orchard = self.mask('orchard') & (self.reserve > 3.5)
        y = 238.0
        while y < 296:
            x = 84.0 + rng.uniform(0, 1)
            while x < 285:
                i, j = int(x), int(y)
                if 0 <= j < self.n and 0 <= i < self.n and orchard[j, i] and self.inner[j, i] and self.road[j, i] > 3.2 and not self.blocked[j, i] and self.grid.free(x, y, .6, 1.4):
                    self.add('astraltree', x + rng.uniform(-.3, .3), y + rng.uniform(-.3, .3))
                x += 6.2
            y += 6.6

    def lamps(self):
        """Lamps stand beside the long roads every 26 tiles, alternating sides; none inside a hub or near the border bands."""
        for road in (TRUNK_S, TRUNK_N, RING_W, RING_E):
            pts = dense_points(road, 1.0)
            last = -99
            side = 1
            for k in range(1, len(pts) - 1):
                if k - last < 26:
                    continue
                (ax, ay), (bx, by) = pts[k - 1], pts[k + 1]
                ln = math.hypot(bx - ax, by - ay) or 1
                x, y = pts[k][0] - (by - ay) / ln * 2.6 * side, pts[k][1] + (bx - ax) / ln * 2.6 * side
                ix, iy = int(x), int(y)
                near_hub = any(h['x'] - h['hw'] - 3 < x < h['x'] + h['hw'] + 3 and h['y'] - h['hh'] - 3 < y < h['y'] + h['hh'] + 3 for h in content.HAMLETS.values())
                city = self.w['city']
                near_hub |= city['x0'] - 3 < x < city['x1'] + 3 and city['y0'] - 3 < y < city['y1'] + 3
                if 0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not near_hub and self.reserve[iy, ix] > 20 and self.road[iy, ix] > 2.0 and self.grid.free(x, y, .35, 1.5):
                    self.add('astrolamp', x, y, r=.35)
                    last = k
                    side = -side

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        tall = ('astraltree', 'crystal', 'obelisk')
        self.objects[:] = [o for o in self.objects if not (o['kind'] in tall and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        # the burnt ground round the crater's heart and the Pyre Hollow
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        g[self.floor & (np.hypot(self.xs - 172, self.ys - 152) < 24 + rough)] = GROUND['ash']
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
        ordinary.sort(key=lambda t: t['kind'] != 'voidmoth')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


# ---- moving the old people, places and portals ---------------------------------------------------------------------------
def shifted_state(zone, old, G):
    """The court, its people, places, the cross and the gates in the new frame."""
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
        o = next((q for q in old['places'] if q['id'] == p['id']), None)
        if o:
            p['x'], p['y'] = round(o['x'] + dx, 2), round(o['y'] + dy, 2)
    for cx in zone['crosses']:
        cx['x'], cx['y'] = CROSS
    for p in zone['portals']:
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'], p['walk'] = round(gx, 2), round(gy, 2), list(walk)


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    G = gates(F)
    shifted_state(zone, old, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the court moved by its own delta, the basin was rebuilt
    d = Astralhollow(zone, old)
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
    # every crossing that arrives here follows the new frame: the Deep's, Nacrehold's, the Prismwaste's and the Orrery's
    inbound = {'path_13_8': ('path_8_13', 8), 'astral_nacre_gate': ('nacre_astral_gate', 9), 'astral_prism_gate': ('prism_astral_gate', 14), 'path_13_15': ('path_15_13', 15)}
    for mine, (theirs, zi) in inbound.items():
        for p in world['zones'][zi - 1]['portals']:
            if p['id'] == theirs:
                p['tx'], p['ty'] = round(G[mine][3][0], 2), round(G[mine][3][1], 2)
    if write:
        content.record_mailboxes(zone, content.HAMLETS, ROOT / 'world/mailboxes.txt')
    problems = check(zone, d, solid, seen, G)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']), kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('crystal', 'astraltree', 'starstone', 'astralshrub', 'starbloom', 'obelisk', 'astrolamp')})
    if problems:
        if os.environ.get('ASTRAL_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post', 'astralhouse', 'astrolamp', 'starwell')


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
            problems.append(f'spawn within 7 tiles of a reserved border {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
        if d.reserve[int(n['y']), int(n['x'])] < 20:
            problems.append(f"npc {n['id']} within 20 tiles of a reserved border")
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
        problems.append(f'art-less objects within the camera reach of a reserved border pop in on crossing: {popping[:5]}')
    loose = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o.get('layout') == d.TAG and o['kind'] != 'void' and d.reserve[int(o['y']), int(o['x'])] < 2.5]
    if loose:
        problems.append(f'loose scenery within 2.5 tiles of a reserved border: {loose[:5]}')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    # every place and elite sits in a region of its own band (the zone gets harder to the north)
    names = list(REGIONS)
    def region_of(x, y):
        return names[int(d.region[int(y), int(x)])]
    for kind, ex, ey in content.ELITES:
        if kind == 'cometmaw' and region_of(ex, ey) != 'comet':
            problems.append(f'cometmaw stands in {region_of(ex, ey)}')
        if kind == 'eclipsequeen' and region_of(ex, ey) != 'eclipse':
            problems.append(f'eclipsequeen stands in {region_of(ex, ey)}')
        if kind == 'orbitwarden' and region_of(ex, ey) != 'heart':
            problems.append(f'orbitwarden stands in {region_of(ex, ey)}')
    return problems


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    pal = {0: (74, 112, 96), 1: (110, 150, 90), 2: (60, 100, 70), 3: (130, 180, 190), 4: (90, 100, 160), 5: (80, 60, 70), 6: (150, 190, 220), 7: (110, 80, 130), 8: (30, 50, 40), 9: (130, 130, 140)}
    a = np.zeros((n, n, 3), np.uint8)
    a[:] = (20, 30, 50)
    for k, c in pal.items():
        a[(d.ground == k) & d.floor] = c
    im = Image.fromarray(a).resize((n * scale, n * scale), Image.NEAREST)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(230, 200, 120), width=scale)
    col = {'crystal': (120, 240, 240), 'starstone': (150, 160, 170), 'astraltree': (30, 90, 60), 'astralshrub': (110, 170, 120), 'starbloom': (220, 150, 230), 'obelisk': (255, 255, 255),
           'astrolamp': (255, 230, 80), 'astralhouse': (200, 120, 60), 'observatory': (255, 160, 60), 'starwell': (100, 200, 255)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('astrolamp', 'starbloom') else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'voidmoth': (240, 120, 120), 'crystalwyrm': (80, 80, 255), 'orbitbeetle': (120, 220, 80), 'eclipsedryad': (230, 100, 230), 'meteorgolem': (255, 160, 40)}
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
