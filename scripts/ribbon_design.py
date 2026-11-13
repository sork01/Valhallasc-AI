#!/usr/bin/env python3
"""The Ribbonwild as an authored map (zone 21 of the shapes pilot): no filler land, the whole outline used.

Owner request 2026-11-08: "for pilot. reshape ribbonwild. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against Emberwake
Caldera only (its whole west side), keep both elites and add one with no quest, three outposts. Sunward Vale (north), the Tanglecrown (south-east) and the Thousandfold
Pavilion stay walk-in gates.

The outline at k = 1.0 is grid 368 with 72,902 land tiles against the old 136 square's 18,496, and it has a south coast. The painting shows a pink field with a great golden
wheel of roads (a hub, eight spokes and a ring), a swirl in the west, a rosette in the south-west and flower rosettes along the east. The zone keeps its own style: four colour
courts, silk pavilions, painted lawns, ribbon poles, pinwheels and festival blooms.

Runs in `zone_shapes.py apply` after Emberwake's design. The zone is `designOnly` (zone-shapes.txt, `seamWith {21: [45]}`): it keeps the outline floor (`shapeFloor`), takes no
filler and places its own gates (`place_portals` skips it). Emberwake's approved design ran unchanged with its east gate as a phantom (`ember_design.LATE_SEAMS = {21}`: only the
spawns within 7 tiles of the new seam and the river circles within 17 went). The border to Emberwake is reserved from `shape.edges` runs: no art-less object or person within
20 tiles, no spawn within 22, no loose scenery within 2.5.

Fixed, moved as a rigid block from `world/zone-shapes/preshape-21.txt` (the old layout): the Thousandfold Pavilion's door, the keykeeper and the Meeting Stone. Every person,
place, portal and quest keeps its id.

    python3 scripts/ribbon_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
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
import ribbon_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, drop_near_seam, fbm, ground_spans, late_targets, seg_field, step_back_artless  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-21.txt'

ZONE = 21
D_DOOR = content.D_DOOR
CENTRE = content.CENTRE
SPAWN = (195.0, 206.0)           # Jubilee Crossroads' own entry
ES17 = (150.0, 160.0)            # A Mask for the Man He Was (Empty Seat chapter 17)
PAV_ARR = (293.0, 190.0)         # where the Pavilion's ways out arrive (old 113, 65)
WHORL = (70.0, 198.0)
ROSETTE = (112.0, 268.0)
RIM = 3

REGIONS = {
    'meadow':   dict(name='The Bunting Meadow', seeds=[(195, 66), (150, 62), (236, 66), (170, 82)]),
    'rose':     dict(name='The Rose Court', seeds=[(195, 122), (168, 106), (222, 108)]),
    'terraces': dict(name='The Marigold Terraces', seeds=[(138, 80), (118, 104), (150, 118)]),
    'pavilion': dict(name='The Pavilion Lawns', seeds=[(256, 96), (272, 120), (296, 160)]),
    'gold':     dict(name='The Gold Court', seeds=[(255, 190), (246, 160), (250, 222)]),
    'banks':    dict(name='The Petal Banks', seeds=[(300, 232), (312, 205), (320, 262)]),
    'green':    dict(name='Jubilee Green', seeds=[(195, 190), (185, 208), (206, 172)]),
    'teal':     dict(name='The Teal Court', seeds=[(195, 244), (166, 258), (224, 252)]),
    'sunset':   dict(name='The Sunset Stair', seeds=[(280, 296), (322, 300), (262, 308)]),
    'strand':   dict(name='The Silk Strand', seeds=[(135, 312), (195, 318), (240, 322)]),
    'violet':   dict(name='The Violet Court', seeds=[(146, 190), (140, 160), (148, 224)]),
    'whorl':    dict(name='The Ribbon Whorl', seeds=[(76, 196), (62, 222), (92, 172)]),
    'rosette':  dict(name='The Great Rosette', seeds=[(112, 268), (90, 286), (140, 288)]),
    'tatter':   dict(name='The Tatter Verge', seeds=[(44, 262), (28, 292), (66, 302)]),
}

# the roads follow the painting (tile coordinates); the gate roads are added by `roads()` from the gate points
RING = [(195, 104), (250, 130), (268, 190), (250, 252), (195, 272), (135, 250), (112, 190), (138, 130)]
R_RING = RING + [RING[0]]
R_SPOKES = [[CENTRE, v] for v in RING]
R_NW = [(138, 130), (112, 123), (92, 119), (78, 117)]                # towards Emberwake (the old east gate's road ends at the seam about here)
R_SW = [(135, 250), (108, 240), (78, 232), (46, 226)]                # the painted south-west road
R_W = [(112, 190), (98, 196)]                             # into the Ribbon Whorl
R_E = [(268, 190), (293, 192), (299, 190)]                           # to the Pavilion door
R_S = [(195, 272), (195, 300), (195, 312)]
R_COAST = [(98, 298), (140, 308), (195, 312), (262, 308), (330, 300)]

R = {'festival_bloom': .1, 'fan_topiary': .85, 'pinwheel': .22, 'ribbon_pole': .35, 'confetti_lantern': .3, 'rw_blossom_tree': .8, 'silk_pavilion': 0, 'painted_stall': 0,
     'mosaic_disc': 0, 'tent': 1.5}
TALL = ('fan_topiary', 'ribbon_pole', 'rw_blossom_tree', 'pinwheel')
GROUND = {'rose': 1, 'gold': 2, 'teal': 3, 'violet': 4, 'green': 5, 'drift': 6, 'sand': 7, 'marble': 8, 'marigold': 9, 'moss': 10}
REGION_GROUND = {'meadow': 'drift', 'rose': 'rose', 'terraces': 'marigold', 'pavilion': 'marble', 'gold': 'gold', 'banks': 'moss', 'green': 'green', 'teal': 'teal',
                 'sunset': 'marigold', 'strand': 'sand', 'violet': 'violet', 'whorl': 'drift', 'rosette': 'rose', 'tatter': 'drift'}
COURT = {'rose': 0, 'gold': 1, 'teal': 2, 'violet': 3}          # the colour of a court's scenery (shade index into the art's four colours)

# scenery per 1000 land tiles of the region (x DENSITY_SCALE)
DENSITY_SCALE = 1.4
DENSITY = {
    'meadow':   [('festival_bloom', 6), ('rw_blossom_tree', 2.2), ('pinwheel', 2.5)],
    'rose':     [('festival_bloom', 8), ('pinwheel', 3), ('fan_topiary', 2)],
    'terraces': [('fan_topiary', 3.5), ('rw_blossom_tree', 3), ('festival_bloom', 5)],
    'pavilion': [('fan_topiary', 3), ('festival_bloom', 5), ('ribbon_pole', 2)],
    'gold':     [('festival_bloom', 8), ('pinwheel', 3), ('ribbon_pole', 2)],
    'banks':    [('festival_bloom', 7), ('rw_blossom_tree', 3), ('pinwheel', 2)],
    'green':    [('festival_bloom', 5), ('fan_topiary', 2.5), ('ribbon_pole', 2)],
    'teal':     [('festival_bloom', 8), ('pinwheel', 3), ('fan_topiary', 2)],
    'sunset':   [('festival_bloom', 6), ('fan_topiary', 2.5), ('confetti_lantern', 1)],
    'strand':   [('festival_bloom', 5), ('confetti_lantern', 1.4), ('pinwheel', 2)],
    'violet':   [('festival_bloom', 8), ('pinwheel', 3), ('fan_topiary', 2)],
    'whorl':    [('festival_bloom', 5), ('pinwheel', 2.5)],
    'rosette':  [('festival_bloom', 6), ('fan_topiary', 2.5)],
    'tatter':   [('festival_bloom', 6), ('rw_blossom_tree', 2.5), ('pinwheel', 2)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): geckos by the north gate, beetles round the east, macaws and jesterlings south
SPAWN_DENSITY = {
    'meadow':   {'ribbongecko': 2.2},
    'rose':     {'ribbongecko': 2.0, 'balloonbeetle': .6},
    'terraces': {'ribbongecko': 1.6, 'balloonbeetle': .8},
    'pavilion': {'balloonbeetle': 1.6, 'ribbongecko': .5},
    'gold':     {'balloonbeetle': 1.8, 'paintedmacaw': .8},
    'banks':    {'paintedmacaw': 1.6, 'jesterling': .6},
    'green':    {'ribbongecko': .6, 'jesterling': .5},
    'teal':     {'paintedmacaw': 1.8, 'jesterling': 1.0},
    'sunset':   {'jesterling': 1.6, 'paintedmacaw': 1.2},
    'strand':   {'jesterling': 1.5, 'paintedmacaw': 1.0},
    'violet':   {'paintedmacaw': 1.6, 'jesterling': 1.2},
    'whorl':    {'paintedmacaw': 1.6, 'jesterling': 1.0},
    'rosette':  {'jesterling': 2.0, 'paintedmacaw': .8},
    'tatter':   {'paintedmacaw': 1.4, 'jesterling': 1.2},
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
    """The rim gates stand 2.5 tiles in from the last land cell, arrival six tiles inside: id -> (x, y, walk, arrival). Emberwake's border is a seam (no gate)."""
    out = {}
    x = 195
    y0 = int(np.nonzero(F[:, x])[0].min())
    out['ribbon_sun_gate'] = (x + .5, y0 + 2.5, (0, -1), (x + .5, y0 + 8.5))
    y = 292
    x1 = int(np.nonzero(F[y])[0].max())
    out['ribbon_tangle_gate'] = (x1 - 2.5, y + .5, (1, 0), (x1 - 8.5, y + .5))
    return out


def roads(G):
    sun, tan = G['ribbon_sun_gate'], G['ribbon_tangle_gate']
    return ([R_RING] + R_SPOKES + [R_NW, R_SW, R_W, R_E, R_S, R_COAST,
            [(sun[0], sun[1]), sun[3], (195, 104)],
            [(tan[0], tan[1]), tan[3], (305, 291), (278, 268), (250, 252)]])


class Ribbonwild(Designer):
    TAG, SEED = 'ribbon_design_v1', 20261109
    LATE_SEAMS = {22, 20}   # the Tanglecrown's seam (and, 2026-11-09, Sunward Vale's) arrived after this design was approved (2026-11-08): the masks stay as they were (the phantom gate ribbon_tangle_gate keeps its discs and its road)

    def __init__(self, world, old):
        self.old = old
        self.G = gates(np.array([[c == '#' for c in row] for row in world['shapeFloor']]))
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        # the border to Emberwake (45) is a seam: nothing the other side cannot draw stands near it
        self.reserve = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] == 45:
                self.reserve = np.minimum(self.reserve, seg_field(e['points'], self.xs, self.ys))
        self.coast = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'coast':
                self.coast = np.minimum(self.coast, seg_field(e['points'], self.xs, self.ys))

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.reserve[iy, ix] > 3
                and self.grid.free(x, y, R.get(kind, .5) if r is None else r, .3))

    def court_v(self, x, y):
        """The colour index of the court a point stands in (0 rose, 1 gold, 2 teal, 3 violet): the wheel's quadrants."""
        a = math.atan2(y - CENTRE[1], x - CENTRE[0])
        return [1, 2, 3, 0][int(((a + math.pi * 2 + math.pi / 4) % (math.pi * 2)) // (math.pi / 2))]

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
            placed += self.scatter([kind], k, self.mask(name) & (self.reserve > 3.5), gap=1.4 if tall else gap, road=3.2 if tall else road)
        return placed

    def take_hub(self):
        """The Pavilion's door, moved as a rigid block (the keykeeper and the Meeting Stone are people: shifted_state)."""
        out = []
        dx, dy = D_DOOR
        for o in self.old['objects']:
            if o['kind'] == 'grand_pavilion_gate':
                q = moved(o, dx, dy)
                q['layout'] = self.TAG
                out.append(q)
        for kind, place, pos in (('parade_standard', 'ribbon_gryphon_court', (158, 88)), ('mask_dais', 'ribbon_mask_court', (292, 232))):
            o = next(o for o in self.old['objects'] if o['kind'] == kind)
            q = dict(o, x=pos[0], y=pos[1], layout=self.TAG)
            out.append(q)
            self.grid.add(q['x'], q['y'], q['r'])
        return out

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        w = self.w
        self.fixed = self.take_hub()
        self.ground = np.zeros((self.n, self.n), np.uint8)
        for o in w['objects']:
            if o['kind'] == 'void':
                self.fixed.append(o)
        for p in w['places']:
            self.block_disc(p['x'], p['y'], 5)
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        self.block_disc(DOOR_PORTAL[0], DOOR_PORTAL[1], 9)
        self.blocked |= self.reserve < 2.5
        for h in content.HAMLETS.values():
            assert self.floor[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 9)
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3.5)
        content.dress(self, content.HAMLETS)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def landmarks(self):
        # the Ribbon Whorl: two turns of poles and pinwheels round the Whorlshell, open at the road that comes in from the east
        k = 0
        for i in range(int(2.3 * 26)):
            t = i / 26.0
            a = t * math.tau + .4
            rad = 14 + t * 8.6
            x, y = WHORL[0] + math.cos(a) * rad, WHORL[1] + math.sin(a) * rad * .86
            kind = 'ribbon_pole' if i % 2 == 0 else 'pinwheel'
            if self.ok(x, y, kind, lane=2.4):
                self.add(kind, x, y, v=(i // 3) % 4)
                k += 1
        # the Great Rosette: concentric rings of topiary and blooms round a mosaic disc, open to the north and south
        self.add('mosaic_disc', ROSETTE[0], ROSETTE[1], v=0)
        self.ring_of(ROSETTE, 9, 12, 'pinwheel', rot=.2, gaps=[(90, 18), (270, 18)], v=0)
        self.ring_of(ROSETTE, 16, 18, 'fan_topiary', rot=.1, gaps=[(90, 14), (270, 14)], v=1)
        self.ring_of(ROSETTE, 25, 28, 'fan_topiary', rot=.3, gaps=[(90, 10), (270, 10)], v=2)
        self.ring_of(ROSETTE, 20, 40, 'festival_bloom', rot=.05, gaps=[(90, 10), (270, 10)], v=3)
        # the avenue to the Pavilion: topiary in pairs either side of the east road for 28 tiles, and poles along the north road
        for i, (x, y) in enumerate(dense_points([(268, 190), (293, 192)], 4.0)):
            for side in (-1, 1):
                if self.ok(x, y + side * 5.2, 'fan_topiary', lane=3.0):
                    self.add('fan_topiary', x, y + side * 5.2, v=1)
        pts = dense_points([(195, 104), (195, 80), self.G['ribbon_sun_gate'][3], (self.G['ribbon_sun_gate'][0], self.G['ribbon_sun_gate'][1])], 1.0)
        for i in range(6, len(pts) - 4, 9):
            x, y = pts[i]
            side = 1 if (i // 9) % 2 else -1
            if self.ok(x + side * 3.6, y, 'ribbon_pole', lane=2.4):
                self.add('ribbon_pole', x + side * 3.6, y, v=(i // 9) % 4)
        # lanterns along the ring and the spokes every 30 tiles, on alternate sides
        for road in [R_RING, R_E, R_S] + R_SPOKES:
            pts = dense_points(road, 1.0)
            for i in range(12, len(pts) - 6, 30):
                x, y = pts[i]
                nx, ny = pts[min(i + 1, len(pts) - 1)][0] - pts[i - 1][0], pts[min(i + 1, len(pts) - 1)][1] - pts[i - 1][1]
                ln = math.hypot(nx, ny) or 1
                side = 1 if (i // 30) % 2 else -1
                lx, ly = x - ny / ln * 3.4 * side, y + nx / ln * 3.4 * side
                if self.ok(lx, ly, 'confetti_lantern', lane=2.0) and self.reserve[int(ly), int(lx)] > 22:
                    self.add('confetti_lantern', lx, ly, v=self.court_v(lx, ly))
        # the hold circles and the elites' rings: a low ring of blooms marks where each stands
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'festival_bloom', rot=.4, v=self.court_v(p['x'], p['y']))
        for _, x, y in content.ELITES:
            self.ring_of((x, y), 5.5, 6, 'festival_bloom', rot=.7, v=self.court_v(x, y))

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        self.objects[:] = [o for o in self.objects if not (o['kind'] in TALL and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        # the sand of the strand to the water's edge, the rose floor of the rosette's inner rings, the marble round the Pavilion's door
        g[self.floor & (self.coast < 14)] = GROUND['sand']
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        g[self.floor & (np.hypot(self.xs - ROSETTE[0], self.ys - ROSETTE[1]) < 27 + rough)] = GROUND['rose']
        g[self.floor & (np.hypot(self.xs - 293, self.ys - 191) < 17 + rough)] = GROUND['marble']
        g[self.floor & (np.hypot(self.xs - CENTRE[0], self.ys - CENTRE[1]) < 14 + rough * .4)] = GROUND['marble']

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])
        # scenery takes the colour of its court: the wheel's four quadrants (the art's shade index)
        for o in self.objects:
            if o['kind'] in ('festival_bloom', 'pinwheel', 'fan_topiary', 'ribbon_pole') and o.get('layout') == self.TAG and 'court' not in o:
                o['v'] = self.court_v(o['x'], o['y'])

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        out = []
        for s in self.old['slimes']:
            if str(s.get('ambush', '')).startswith('empty-seat:'):
                out.append(dict(s, x=round(ES17[0] + 2, 2), y=ES17[1]))
        out += [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in content.HAMLETS.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
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
        ordinary.sort(key=lambda t: t['kind'] != 'ribbongecko')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


DOOR_PORTAL = (119 + D_DOOR[0], 65 + D_DOOR[1])


# ---- moving the old people, places and portals ---------------------------------------------------------------------------
def shifted_state(zone, old, G):
    """Jubilee Crossroads, the Pavilion block, the people, the places and the gates in the new frame."""
    dx, dy = D_DOOR
    zone['spawn'] = dict(x=SPAWN[0], y=SPAWN[1])
    by = {n['id']: n for n in zone['npcs']}
    spots = {'travel_jubilee': (14, 10), 'mailbox_21_jubilee_crossroads': (-12, 12)}
    for n in old['npcs']:
        t = by.get(n['id'])
        if not t:
            continue
        if n['id'] in content.HUB_NPCS:
            hn, ox, oy = content.HUB_NPCS[n['id']]
            h = content.HAMLETS[hn]
            t['x'], t['y'] = h['x'] + ox, h['y'] + oy
        elif n['id'] in content.DOOR_NPCS:
            t['x'], t['y'] = round(n['x'] + dx, 2), round(n['y'] + dy, 2)
        elif n['id'] in spots:
            h = content.HAMLETS['jubilee']
            t['x'], t['y'] = h['x'] + spots[n['id']][0], h['y'] + spots[n['id']][1]
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    for p in zone['places']:
        o = next((q for q in old['places'] if q['id'] == p['id']), None)
        if p['id'] == 'es_17_m':
            p['x'], p['y'] = ES17
        elif p['id'] == 'ribbon_pavilion':
            p['x'], p['y'] = round(o['x'] + dx, 2), round(o['y'] + dy, 2)
        elif p['id'] == 'ribbon_gryphon_court':
            p['x'], p['y'] = content.ELITES[0][1], content.ELITES[0][2]
        elif p['id'] == 'ribbon_mask_court':
            p['x'], p['y'] = content.ELITES[1][1], content.ELITES[1][2]
    for p in zone['portals']:
        if p.get('seam'):           # the Emberwake seam (zone_shapes.make_seams): its line is the border, not a gate
            continue
        if p['id'] == 'ribbon_pavilion_gate':
            p['x'], p['y'] = round(119 + dx, 2), round(65 + dy, 2)
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'] = round(gx, 2), round(gy, 2)
        p['walk'] = list(walk)
    fi = zone.get('futureInstance')
    if fi:
        fi['x'], fi['y'] = round(120 + dx, 2), round(65 + dy, 2)


def link_travel(world):
    """Add (never strip) the Spark links across every portal into or out of the Ribbonwild, both ways, as compact_atlas.sync_travel_links does."""
    zones = [world] + world['zones']
    masters = lambda z: [n for n in z.get('npcs', []) if n.get('travelStop')]
    for i, z in enumerate(zones):
        for p in z['portals']:
            if p['to'] == i or ZONE not in (i, p['to']):
                continue
            if p.get('seam') and 22 in (i, p['to']):      # the Tanglecrown's seam (both its portals) is linked by tangle_design.link_travel once they are aimed at the crossing
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
    shifted_state(zone, old, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the zone was rebuilt
    d = Ribbonwild(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    d.late_dropped = d.late_moved = 0
    late = late_targets(zone, 22, 20)
    if late:      # the Tanglecrown's seam (2026-11-08) and Sunward Vale's (2026-11-09) replaced rim gates: only the spawns within 7 tiles of them and the loose scenery within 2.5 go (the art-less objects within 20 step back below)
        for t in late:
            d.late_dropped += drop_near_seam(zone, d, t)
        loose = [o for o in objects if o.get('layout') == d.TAG and o['kind'] != 'void' and d.seam_late[min(max(int(o['y']), 0), d.n - 1), min(max(int(o['x']), 0), d.n - 1)] < 2.5]
        objects = [o for o in objects if o not in loose]
        d.late_dropped += len(loose)
    zone['objects'] = objects
    # Trim the final spur past Pavilion Steps camp to ribbon_pavilion_gate from visible brown paths.
    visible_roads = [road[:-1] if road is R_E else road for road in d.ROADLIST]
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in visible_roads]
    zone['atlasPaths'] = []
    seamed = {p['id'] for p in zone['portals'] if p.get('seam')}      # the Tanglecrown's seam replaced the south-east rim gate: its line is the border, not a gate
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items() if g not in seamed]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, zone, content.HAMLETS, old)
    for t in late_targets(zone, 20):      # after the people stand in their final places: the art-less objects within 20 tiles of Sunward Vale's seam step back (see greenmeadow_design.step_back_artless)
        d.late_moved += step_back_artless(zone, zone['objects'], d, t)
    # every crossing that arrives here follows the new frame: Sunward's and the Tanglecrown's gates, and the Pavilion's two ways out (the Emberwake seam carries its own shift)
    arrivals = {'sun_ribbon_gate': G['ribbon_sun_gate'][3], 'tangle_ribbon_gate': G['ribbon_tangle_gate'][3], 'thousandfold_return': PAV_ARR, 'thousandfold_exit': PAV_ARR}
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals and not p.get('seam'):
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
    # the new masters join the Spark network of their neighbours (a global sync_travel_links would rewrite every other pilot zone's links)
    link_travel(world)
    if write:
        content.record_mailboxes(zone, content.HAMLETS, ROOT / 'world/mailboxes.txt')
    problems = check(zone, d, solid, seen, G)
    stats = dict(late_dropped=d.late_dropped, short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']),
                 kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('festival_bloom', 'fan_topiary', 'pinwheel', 'ribbon_pole', 'confetti_lantern', 'rw_blossom_tree')})
    if problems:
        if os.environ.get('RIBBON_LAX'):
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
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
        if walk and not seen[int(gy - walk[1] * 3), int(gx - walk[0] * 3)]:
            problems.append(f'gate {g} is blocked from the inside')
    door = next(q for q in zone['portals'] if q['id'] == 'ribbon_pavilion_gate')
    if not seen[int(door['y'] + 2), int(door['x'])]:
        problems.append('the Pavilion door is cut off')
    if not seen[int(PAV_ARR[1]), int(PAV_ARR[0])]:
        problems.append('the Pavilion arrival is cut off')
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
    walked += [((q['x'], q['y']), f"place {q['id']}") for q in zone['places'] if q['id'] not in ('ribbon_gryphon_court', 'ribbon_mask_court')] + [((n['x'], n['y']), f"npc {n['id']}") for n in zone['npcs']]
    walked += [((q['x'], q['y']), f"portal {q['id']}") for q in zone['portals'] if not q.get('seam')]
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
    # the Tanglecrown's seam (late): a seam neighbour draws scenery with art but no people and no art-less objects, so none of those stand within 20 tiles of it (the Pavilion's mailbox and Spark master stepped back)
    at_late = lambda o: d.seam_late[min(max(int(o['y']), 0), d.n - 1), min(max(int(o['x']), 0), d.n - 1)]
    near_late = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o['kind'] in ARTLESS and at_late(o) < 20]
    if near_late:
        problems.append(f'art-less objects within 20 tiles of the Tanglecrown seam: {near_late[:5]}')
    people_late = [(n['id'], round(float(at_late(n)), 1)) for n in zone['npcs'] if at_late(n) < 20]
    if people_late:
        problems.append(f'people within 20 tiles of the Tanglecrown seam pop in on crossing: {people_late[:5]}')
    loose_late = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o.get('layout') == d.TAG and o['kind'] != 'void' and at_late(o) < 2.5]
    if loose_late:
        problems.append(f'loose scenery within 2.5 tiles of the Tanglecrown seam: {loose_late[:5]}')
    if any(at_late(t) <= 7 for t in zone['slimes'] if t.get('layout') == d.TAG):
        problems.append('a spawn within 7 tiles of the Tanglecrown seam')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    for h in content.HAMLETS.values():
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
    bg = Image.blend(bg, Image.new('RGB', bg.size, (30, 20, 40)), .35)
    pal = {1: (240, 110, 150), 2: (240, 200, 90), 3: (90, 200, 210), 4: (170, 130, 220), 5: (110, 180, 100), 6: (240, 200, 220), 7: (230, 215, 160), 8: (245, 240, 225), 9: (240, 160, 70), 10: (110, 190, 150)}
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
    col = {'festival_bloom': (240, 120, 160), 'fan_topiary': (60, 150, 90), 'pinwheel': (120, 120, 240), 'ribbon_pole': (255, 255, 255), 'confetti_lantern': (255, 255, 160),
           'rw_blossom_tree': (255, 150, 200), 'mosaic_disc': (200, 160, 255), 'grand_pavilion_gate': (255, 90, 90)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('festival_bloom',) else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'ribbongecko': (240, 120, 120), 'balloonbeetle': (120, 220, 255), 'paintedmacaw': (240, 240, 120), 'jesterling': (230, 100, 230)}
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
