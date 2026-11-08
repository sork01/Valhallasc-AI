#!/usr/bin/env python3
"""The Stormglass Flats as an authored map (zone 19 of the shapes pilot, formerly "The Stormglass Shore"): no filler land, the whole outline used.

Owner request 2026-11-08: "for pilot. reshape stormglass shore. probably rename it since its no shore. and remake the zone and quests to fit the new shape.
no fillers." Owner answers: The Stormglass Flats, seamless against the Prismwaste (north) and the Obsidian Orrery (west), keep the Maelstrom Heart and add two
new elites (one with a quest, one without), three new outposts. Sunward Vale (east), Frostwake (the north-east corner) and Emberwake (south) are not shaped:
they stay walk-in rim gates. Asterion is a landmark point inside this province (atlas `cities`): its gate stands on the painted compass rose.

The outline at k = 1.0 is landlocked (every border is a neighbour): grid 328, 72,140 land tiles against the old 128 square's 16,384. The painting shows a dark
night plain of black sand under huge blue storm-glass crystals, a pale flat in the south-west (Breakwater Camp), a straight trunk road down the middle, a
hexagon of roads round two crystals in the west, a diagonal web in the east and a compass rose in the south. The zone keeps its own style: black sand, salt,
tide bells, storm lamps, lightning and the sealed Eye Below: the sea has gone and left its floor, its bells and its creatures.

Runs in `zone_shapes.py apply` after the Prismwaste's and the Orrery's designs. The zone is `designOnly` (zone-shapes.txt, `seamWith {19: [14, 15]}`): it keeps
the outline floor (`shapeFloor`), takes no filler and places its own gates (`place_portals` skips it). The Prismwaste's and the Orrery's approved designs ran
unchanged with their Stormglass gate as a phantom; only the spawns within 7 tiles of the new seam were dropped (`prism_design.drop_near_seam`).
The borders to the Prismwaste and the Orrery are reserved from `shape.edges` runs: no art-less object or person within 20 tiles, no spawn within 7, no loose
scenery within 2.5.

Fixed, moved as rigid blocks from `world/zone-shapes/preshape-19.txt` (the old layout): Breakwater Camp (huts, lamps, bell, all its people, the Spark Travel
master and the mailbox) and the Eye (arch, descent, bell, the Meeting Stone and Mara). Every person, place, portal and quest keeps its id.

    python3 scripts/storm_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
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
import storm_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-19.txt'

ZONE = 19
NEW_NAME = 'The Stormglass Flats'
OLD_NAME = 'The Stormglass Shore'
D_HUB = (58, 154)          # old camp (rect 10..49 x 96..124, plaza 30,108) -> plaza (88, 262), on the pale flat of the painting
D_EYE = (133, 81)          # old Eye (arch 105,23) -> arch (238, 104), in the Eye Basin
SPAWN = (71.0, 259.0)      # the camp's own entry, moved with it
ES_PLACE = (118.0, 222.0)  # The Sea Cannot Swallow This Fire (Empty Seat)
HEART = (178.0, 50.0)
EYE = (238.0, 104.0)
COMPASS = (177.0, 277.0)   # the painted compass rose: Asterion's gate stands in it
ASTERION_GATE = (177.0, 271.0)
RIM = 3

REGIONS = {
    'camp':   dict(name='Breakwater Pan', seeds=[(88, 262), (112, 268), (60, 266)]),
    'dunes':  dict(name='The Black Dunes', seeds=[(52, 120), (50, 170), (60, 205), (70, 85)]),
    'seeps':  dict(name='The Reed Seeps', seeds=[(100, 150), (112, 178), (96, 128)]),
    'pans':   dict(name='The Salt Pans', seeds=[(80, 224), (104, 232), (70, 200)]),
    'north':  dict(name='The Northern Drift', seeds=[(98, 48), (120, 36), (72, 62)]),
    'spire':  dict(name='The Stormspire', seeds=[(180, 60), (166, 92), (198, 84)]),
    'cross':  dict(name='The Rodfields', seeds=[(184, 186), (160, 208), (208, 172), (150, 170)]),
    'eye':    dict(name='The Eye Basin', seeds=[(238, 104), (226, 86), (236, 128)]),
    'bank':   dict(name='The Sunward Bank', seeds=[(274, 150), (268, 110), (272, 200)]),
    'rose':   dict(name='The Compass Floor', seeds=[(177, 277), (150, 300), (206, 292), (160, 262)]),
    'shards': dict(name='The Low Shards', seeds=[(256, 262), (240, 296), (272, 244)]),
    'rim':    dict(name='The Cold Rim', seeds=[(262, 30), (240, 46), (282, 62)]),
}

# the roads follow the painted atlas (tile coordinates); the gate roads are added by `roads()` from the gate points
TRUNK = [(143.5, 16), (146, 40), (146, 82), (143, 120), (141, 160), (139, 200), (138, 236), (137, 262)]
VERT_N = [(192, 131), (192, 108)]
WESTHEX = [(114, 86), (75, 131), (73, 160), (80, 190), (108, 214), (136, 238)]
ESE = [(114, 86), (145, 105), (168, 122), (192, 135)]
NEDIAG = [(244, 75), (222, 100), (205, 118), (192, 131)]
EAST = [(244, 75), (251, 105), (257, 145), (252, 179)]
BOXTOP = [(236, 178), (252, 179), (278, 178)]
BOXE = [(278, 178), (278, 205), (278, 229)]
BOXBOT = [(278, 229), (258, 230), (238, 246), (204, 259)]
DIAGA = [(196, 152), (182, 169), (162, 196), (140, 214)]
VERT = [(192, 133), (190, 160), (186, 184), (180, 204), (178, 225), (177, 244), (177, 267)]
HORI = [(183, 187), (210, 193), (240, 199), (252, 201)]
LIGHT = [(216, 24), (216, 62), (208, 60), (206, 92), (197, 108), (192, 131)]
CAMP_E = [(107, 262), (137, 262)]
CAMP_N = [(88, 250), (92, 236), (108, 214)]
COMP_W = [(137, 277), (146, 277)]
WEST = [(42, 167.5), (58, 167), (73, 164)]
RS_W = [(88, 152), (74, 150)]
RS_E = [(112, 152), (126, 154), (141, 159)]
FP_E = [(124, 64), (145, 64)]
FP_S = [(112, 75), (114, 86)]
BH_W = [(260, 150), (256, 148)]
EYE_E = [(238, 111), (252, 112)]
EYE_W = [(210, 114), (228, 112), (238, 112)]

R = {'stormglass_spire': .9, 'saltpillar': .65, 'blackpebble': .4, 'seafoam': .1, 'stormreed': .25, 'tide_bell': .55, 'stormlamp': .28, 'breakwater_hut': 0}
GROUND = {'sand': 1, 'salt': 2, 'dune': 3, 'reed': 4, 'glass': 5, 'floor': 6, 'basin': 7, 'bank': 8, 'frost': 9, 'scorch': 10}
REGION_GROUND = {'camp': 'salt', 'dunes': 'dune', 'seeps': 'reed', 'pans': 'salt', 'north': 'sand', 'spire': 'glass', 'cross': 'sand', 'eye': 'basin',
                 'bank': 'bank', 'rose': 'floor', 'shards': 'glass', 'rim': 'frost'}

# scenery per 1000 land tiles of the region
DENSITY = {
    'camp':   [('blackpebble', 5), ('seafoam', 6)],
    'dunes':  [('blackpebble', 10), ('saltpillar', 3), ('stormreed', 4)],
    'seeps':  [('stormreed', 22), ('seafoam', 8), ('blackpebble', 4)],
    'pans':   [('saltpillar', 9), ('seafoam', 10), ('blackpebble', 5)],
    'north':  [('blackpebble', 7), ('stormreed', 5), ('saltpillar', 3), ('stormglass_spire', 1.5)],
    'spire':  [('stormglass_spire', 5), ('blackpebble', 6), ('saltpillar', 2)],
    'cross':  [('blackpebble', 6), ('stormreed', 6), ('saltpillar', 4), ('stormglass_spire', 1.5)],
    'eye':    [('saltpillar', 4), ('blackpebble', 5), ('seafoam', 6)],
    'bank':   [('blackpebble', 10), ('saltpillar', 3), ('stormreed', 5)],
    'rose':   [('blackpebble', 3), ('seafoam', 4)],
    'shards': [('stormglass_spire', 4), ('blackpebble', 6), ('saltpillar', 3)],
    'rim':    [('blackpebble', 9), ('saltpillar', 5), ('stormglass_spire', 2)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): claws by the camp, then gulls, rays and sentinels
SPAWN_DENSITY = {
    'camp':   {'saltclaw': 3.0},
    'dunes':  {'saltclaw': 3.4, 'stormgull': .8},
    'seeps':  {'saltclaw': 2.2, 'stormgull': 2.0, 'glassray': .8},
    'pans':   {'saltclaw': 1.6, 'glassray': 3.0},
    'north':  {'stormgull': 3.0, 'saltclaw': 1.2},
    'spire':  {'stormgull': 2.6, 'breakersentinel': 2.4},
    'cross':  {'glassray': 2.8, 'stormgull': 1.6, 'breakersentinel': 1.2},
    'eye':    {'breakersentinel': 4.0, 'glassray': 1.0},
    'bank':   {'breakersentinel': 2.8, 'glassray': 2.0},
    'rose':   {'glassray': 2.4, 'saltclaw': 1.8},
    'shards': {'glassray': 2.0, 'breakersentinel': 2.6},
    'rim':    {'stormgull': 2.2, 'breakersentinel': 3.0},
}
# stands of storm-glass spires where the painting shows its huge blue crystals: centre, radius
SPIRE_STANDS = [(180, 66, 22), (126, 69, 8), (233, 52, 5), (102, 122, 14), (100, 178, 11), (79, 213, 20), (156, 223, 5), (193, 213, 8), (216, 236, 9),
                (262, 203, 7), (262, 249, 8), (224, 138, 9), (220, 172, 6)]
# trunk junctions where two tide bells stand as waymarks
JUNCTIONS = [(192, 131), (140, 214), (252, 179), (114, 86), (75, 131), (146, 82)]


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
    """The rim gates stand 2.5 tiles in from the last land cell, arrival six tiles inside: id -> (x, y, walk, arrival). The Prismwaste and Orrery borders are seams
    (no gate). Asterion's gate stands on the compass rose (no walk: a two-post gate in the open) and its arrival is on the road side."""
    out = {}
    y = 203
    x1 = int(np.nonzero(F[y])[0].max())
    out['stormglass_sun_gate'] = (x1 - 2.5, y + .5, (1, 0), (x1 - 8.5, y + .5))
    x = 262
    y0 = int(np.nonzero(F[:, x])[0].min())
    out['path_19_26'] = (x + .5, y0 + 2.5, (0, -1), (x + .5, y0 + 8.5))
    x = 137
    y1 = int(np.nonzero(F[:, x])[0].max())
    out['path_19_45'] = (x + .5, y1 - 2.5, (0, 1), (x + .5, y1 - 8.5))
    out['stormglass_asterion_gate'] = (ASTERION_GATE[0] + .5, ASTERION_GATE[1], None, (ASTERION_GATE[0] + .5, ASTERION_GATE[1] - 7))
    return out


def roads(G):
    sun, nef, emb, ast = G['stormglass_sun_gate'], G['path_19_26'], G['path_19_45'], G['stormglass_asterion_gate']
    return [TRUNK, VERT_N, WESTHEX, ESE, NEDIAG, EAST, BOXTOP, BOXE, BOXBOT, DIAGA, VERT, HORI, LIGHT, CAMP_E, CAMP_N, COMP_W, WEST, RS_W, RS_E, FP_E, FP_S, BH_W, EYE_E, EYE_W,
            # the gate roads: from the gate to the network
            [(sun[0], sun[1]), sun[3], (278, 203)],
            [(nef[0], nef[1]), nef[3], (250, 24), (232, 24), (216, 24)],
            [(emb[0], emb[1]), emb[3], (137, 262)],
            [(ast[0], ast[1]), ast[3], (177, 262)]]


class Stormglass(Designer):
    TAG, SEED = 'storm_design_v1', 20261108
    LATE_SEAMS = set()

    def __init__(self, world, old):
        self.old = old
        self.G = gates(np.array([[c == '#' for c in row] for row in world['shapeFloor']]))
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        # the borders to the Prismwaste (14) and the Orrery (15) are seams: nothing the other side cannot draw stands near them
        self.reserve = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] in (14, 15):
                self.reserve = np.minimum(self.reserve, seg_field(e['points'], self.xs, self.ys))

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.reserve[iy, ix] > 3
                and self.grid.free(x, y, R.get(kind, .5), .3))

    def ring_of(self, centre, radius, n, kind, rot=.3, **extra):
        k = 0
        for i in range(n):
            a = i / n * math.tau + rot
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if self.ok(x, y, kind):
                self.add(kind, x, y, **extra)
                k += 1
        return k

    def fill(self, name, kinds, gap=.8, road=2.8):
        area = int(self.mask(name).sum())
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per / 1000))
            tall = kind in ('stormglass_spire', 'saltpillar')
            placed += self.scatter([kind], k, self.mask(name) & (self.reserve > 3.5), gap=1.3 if tall else gap, road=3.6 if tall else road)
        return placed

    def take_hub(self):
        """The camp's buildings, lamps and bell, and the Eye's arch and bell, moved as rigid blocks."""
        old = self.old
        c = old['city']
        out = []
        for o in old['objects']:
            if o['kind'] in ('breakwater_hut', 'stormlamp', 'tide_bell') and c['x0'] - 2 <= o['x'] <= c['x1'] + 2 and c['y0'] - 2 <= o['y'] <= c['y1'] + 2:
                q = moved(o, *D_HUB)
            elif o['kind'] in ('eye_arch', 'meetingstone', 'tide_bell') and o['x'] > 80 and o['y'] < 50:
                q = moved(o, *D_EYE)
            else:
                continue
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
        for p in w['places']:
            self.block_disc(p['x'], p['y'], 5)
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        self.block_disc(*EYE, 12)
        self.blocked |= self.reserve < 2.5
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
        elites = [(x, y, 12) for _, x, y in content.ELITES]
        # the painting's huge crystals: stands of storm-glass spires, a dense heart and a ring
        for cx, cy, rad in SPIRE_STANDS:
            self.ring_of((cx, cy), rad, max(6, int(rad * 1.1)), 'stormglass_spire', rot=cx * .13)
            self.ring_of((cx, cy), rad * .5, max(3, int(rad * .55)), 'stormglass_spire', rot=cy * .11)
        # the Eye Basin: broken rings of salt pillars round the sea's old whirlpool, open at every road
        for radius in (24, 38, 52):
            self.ring_of(EYE, radius, int(radius * math.tau / 5.2), 'saltpillar', rot=radius * .07)
        # the compass rose: eight tide bells at its points
        self.ring_of(COMPASS, 31, 8, 'tide_bell', rot=0.)
        # the hold circles: a low ring of black pebbles round each
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'blackpebble', rot=.4)
        # the elites' rings: a low ring of black pebbles marks where each stands
        for _, x, y in content.ELITES:
            self.ring_of((x, y), 5.5, 6, 'blackpebble', rot=.7)
        # two tide bells at each trunk junction, as waymarks
        for jx, jy in JUNCTIONS:
            for sx, sy in ((-4.5, -4.5), (4.5, 4.5)):
                x, y = jx + sx, jy + sy
                if 0 <= int(x) < self.n and 0 <= int(y) < self.n and self.inner[int(y), int(x)] and self.road[int(y), int(x)] > 2.6 and self.reserve[int(y), int(x)] > 20 and self.grid.free(x, y, .7, .8):
                    self.add('tide_bell', x, y, v=0, r=.55)

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        tall = ('stormglass_spire', 'saltpillar')
        self.objects[:] = [o for o in self.objects if not (o['kind'] in tall and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        # the scorched ground where the storm took shape
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        g[self.floor & (np.hypot(self.xs - HEART[0], self.ys - HEART[1]) < 9 + rough * .5)] = GROUND['scorch']
        # the pale flat of the camp is salt crust to its edge
        cx0, cy0, cx1, cy1 = 40, 246, 128, 280
        flat = self.floor & (self.xs > cx0) & (self.xs < cx1) & (self.ys > cy0) & (self.ys < cy1)
        g[flat] = GROUND['salt']

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        out = []
        for s in self.old['slimes']:
            if str(s.get('ambush', '')).startswith('empty-seat:'):
                out.append(dict(s, x=round(ES_PLACE[0] + 2, 2), y=ES_PLACE[1]))
        out += [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in content.HAMLETS.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
        city = w['city']
        keep[city['y0'] - 8:city['y1'] + 9, city['x0'] - 8:city['x1'] + 9] = True
        keep[int(EYE[1]) - 14:int(EYE[1]) + 24, int(EYE[0]) - 22:int(EYE[0]) + 14] = True
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
        ordinary.sort(key=lambda t: t['kind'] != 'saltclaw')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


# ---- moving the old people, places and portals ---------------------------------------------------------------------------
HUB_NPCS = ('stormglass_warden', 'stormglass_healer', 'stormglass_scout', 'stormglass_scholar', 'stormglass_trader', 'travel_breakwater', 'mailbox_19_breakwater_camp')
EYE_NPCS = ('stormglass_watcher', 'stormglass_stone')


def shifted_state(zone, old, G):
    """The camp, its people, the Eye, the places and the gates in the new frame."""
    dx, dy = D_HUB
    c = old['city']
    zone['city'] = dict(c, x0=c['x0'] + dx, x1=c['x1'] + dx, y0=c['y0'] + dy, y1=c['y1'] + dy, plaza=dict(x=c['plaza']['x'] + dx, y=c['plaza']['y'] + dy),
                        entry=dict(x=c['entry']['x'] + dx, y=c['entry']['y'] + dy))
    zone['spawn'] = dict(x=SPAWN[0], y=SPAWN[1])
    by = {n['id']: n for n in zone['npcs']}
    for n in old['npcs']:
        t = by.get(n['id'])
        if not t:
            continue
        d = D_HUB if n['id'] in HUB_NPCS else D_EYE if n['id'] in EYE_NPCS else None
        assert d, f"unplaced old person {n['id']}"
        t['x'], t['y'] = round(n['x'] + d[0], 2), round(n['y'] + d[1], 2)
    for p in zone['places']:
        if p['id'] == 'es_15_m':
            p['x'], p['y'] = ES_PLACE
        elif p['id'] in ('stormglass_eye', 'stormglass_bell'):
            o = next(q for q in old['places'] if q['id'] == p['id'])
            p['x'], p['y'] = round(o['x'] + D_EYE[0], 2), round(o['y'] + D_EYE[1], 2)
    zone['futureInstance']['x'], zone['futureInstance']['y'] = EYE
    for p in zone['portals']:
        if p.get('seam'):           # the Prismwaste and Orrery seams (zone_shapes.make_seams): their line is the border, not a gate
            continue
        if p['id'] == 'stormglass_eye_descent':
            p['x'], p['y'] = EYE[0], EYE[1] + 4
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'] = round(gx, 2), round(gy, 2)
        if walk:
            p['walk'] = list(walk)
        else:
            p.pop('walk', None)


def rename(world):
    """The zone is no shore: every text that names it follows (the name is also the `reach` objective's target, the portals' names, the achievement text). In place,
    so nothing that holds a zone keeps the old name."""
    def fix(v):
        return v.replace(OLD_NAME, NEW_NAME).replace('Stormglass Shore', 'Stormglass Flats')
    def walk(v):
        items = v.items() if isinstance(v, dict) else enumerate(v)
        for k, x in list(items):
            if isinstance(x, str):
                if 'Stormglass Shore' in x:
                    v[k] = fix(x)
            elif isinstance(x, (dict, list)):
                walk(x)
    walk(world)


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    G = gates(F)
    shifted_state(zone, old, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the camp moved by its own delta, the zone was rebuilt
    d = Stormglass(zone, old)
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
    # every crossing that arrives here follows the new frame: Asterion's, Sunward's, Frostwake's and Emberwake's gates, and the Eye's two ways back (the seams carry their own shift)
    arrivals = {'asterion_stormglass_gate': G['stormglass_asterion_gate'][3], 'sun_stormglass_gate': G['stormglass_sun_gate'][3],
                'path_26_19': G['path_19_26'][3], 'path_45_19': G['path_19_45'][3],
                'eye_below_return': (EYE[0], EYE[1] + 7), 'eye_below_exit': (EYE[0], EYE[1] + 7)}
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals and not p.get('seam'):
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
    if write:
        content.record_mailboxes(zone, content.HAMLETS, ROOT / 'world/mailboxes.txt')
    problems = check(zone, d, solid, seen, G)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']), kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('stormglass_spire', 'saltpillar', 'blackpebble', 'stormreed', 'seafoam', 'tide_bell')})
    if problems:
        if os.environ.get('STORM_LAX'):
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
        r = int(p.get('r', 2) + 1)       # a place that stands on a building (the Eye's arch, its bell) is reached from beside it
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
        if walk and not seen[int(gy - walk[1] * 3), int(gx - walk[0] * 3)]:
            problems.append(f'gate {g} is blocked from the inside')
        if not walk and not seen[int(gy + 2), int(gx)]:
            problems.append(f'gate {g} is blocked')
    p = next(q for q in zone['portals'] if q['id'] == 'stormglass_eye_descent')
    if not seen[int(p['y']), int(p['x'])] or not seen[int(p['y'] + 3), int(p['x'])]:
        problems.append('the Eye descent is cut off')
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
    # an elite stands clear of everything a player walks to: awareness plus 3 tiles from every road, place and person, and from every hub, gate and the Eye
    walked = [(q, 'road') for road in d.ROADLIST for q in dense_points(road)]
    walked += [((q['x'], q['y']), f"place {q['id']}") for q in zone['places']] + [((n['x'], n['y']), f"npc {n['id']}") for n in zone['npcs']]
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
        problems.append(f'art-less objects within the camera reach of a seam pop in on crossing: {popping[:5]}')
    loose = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o.get('layout') == d.TAG and o['kind'] != 'void' and d.reserve[int(o['y']), int(o['x'])] < 2.5]
    if loose:
        problems.append(f'loose scenery within 2.5 tiles of a seam: {loose[:5]}')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    names = list(REGIONS)
    def region_of(x, y):
        return names[int(d.region[int(y), int(x)])]
    want = {'maelstromheart': 'spire', 'lamphermit': 'pans', 'stormtusk': 'shards'}
    for kind, ex, ey in content.ELITES:
        if region_of(ex, ey) != want[kind]:
            problems.append(f'{kind} stands in {region_of(ex, ey)}')
    for h in content.HAMLETS.values():
        if d.reserve[int(h['y']), int(h['x'])] < 20 + h['hw']:
            problems.append(f"{h['name']} stands within 20 tiles of a seam")
    c = zone['city']
    if d.reserve[int((c['y0'] + c['y1']) / 2), int(c['x0'])] < 20:
        problems.append('Breakwater Camp stands within 20 tiles of a seam')
    return problems


def plan_picture(zone, d, out, scale=4):
    from PIL import Image, ImageDraw
    n = d.n
    T = zone['shape']['T']
    s = 1758 / 2048
    atlas = Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB')
    x0, y0 = int(round(T[0] * s)), int(round(T[1] * s))
    bg = atlas.crop((x0, y0, x0 + int(n * s), y0 + int(n * s))).resize((n * scale, n * scale), Image.LANCZOS)
    bg = Image.blend(bg, Image.new('RGB', bg.size, (20, 30, 50)), .5)
    pal = {1: (60, 70, 90), 2: (150, 180, 190), 3: (80, 60, 50), 4: (70, 130, 110), 5: (90, 130, 190), 6: (150, 150, 200), 7: (70, 60, 140), 8: (130, 130, 120), 9: (170, 200, 230), 10: (200, 90, 60)}
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
    col = {'stormglass_spire': (120, 200, 255), 'saltpillar': (220, 230, 225), 'blackpebble': (110, 120, 140), 'stormreed': (90, 160, 120), 'seafoam': (190, 240, 230),
           'tide_bell': (255, 200, 90), 'stormlamp': (255, 255, 160), 'breakwater_hut': (200, 160, 110), 'eye_arch': (255, 90, 90)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('stormreed', 'seafoam') else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'saltclaw': (240, 120, 120), 'stormgull': (240, 240, 120), 'glassray': (80, 200, 255), 'breakersentinel': (230, 100, 230)}
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
