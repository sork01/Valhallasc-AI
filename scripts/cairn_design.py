#!/usr/bin/env python3
"""Cairnspine as an authored map (zone 27 of the shapes pilot): no filler land, the whole outline used, seamless against the Prismwaste.

Owner request 2026-11-09: "for pilot. reshape cairnspine. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the Prismwaste only (the Frostwake
Shelf crossing stays a gate), keep all three elites and add a fourth with no quest, keep the Thunderheart Gate door and rebuild the hub, three outposts.

The outline at k = 1.0 is grid 272 with 32,469 land tiles (the old square held 28,224 but only a thin strip of it was used): a mountain shield. The Prismwaste lies along the whole
south-west diagonal (the seam), Frostwake along the east, a coast in the north. The painting shows white-capped slate ridges: a big massif in the north (the Thunderheart), switchback
terraces in the middle and a tapering toe in the south. Boulderwatch stands in the middle of the pass, the Singing Cairn Post on the western height, the Whitebark Post in the middle heights
and the Stormgate Camp on the northern ridge; the Thunderheart Gate is at the head of the ridge.

Runs in `zone_shapes.py apply` after the Prismwaste's design. The zone is `designOnly` + `rebuild` (zone-shapes.txt): the old 168 square is not moved, everything is made here from
`world/zone-shapes/preshape-27.txt` (the old people, places, quests and the Thunderheart door keep their ids).

    python3 scripts/cairn_design.py plan OUT.png     draw the plan from the cached shaped world (read only; CAIRN_WORLD=<json>)
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
import cairn_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, drop_near_seam, fbm, ground_spans, seg_field, step_back_artless  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-27.txt'

ZONE = 27
PRISM, FROSTWAKE, DUNGEON = 14, 26, 35
HAM = content.HAMLETS
SPAWN = (HAM['boulderwatch']['x'] - HAM['boulderwatch']['hw'] + 5.5, HAM['boulderwatch']['y'] + .5)     # Boulderwatch's own entry, inside the west side of the city
CROSS_IN = 6.5                      # the Prismwaste crossing's arrival, this many tiles inland (the seam's normal points east-north-east)
NORMAL = (214 / 246, -122 / 246)    # the seam's inland normal (the border runs (122, 214))
SEAM_SPAWN, SEAM_LOOSE, SEAM_PEOPLE = 10.0, 3.0, 22.0

REGIONS = {
    'terraces':    dict(name='The Boulderwatch Terraces', seeds=[(156, 170), (140, 190), (178, 186), (170, 160)]),
    'prismverge':  dict(name='The Prism Verge', seeds=[(112, 190), (96, 158), (78, 128), (62, 98), (50, 70)]),
    'fourturns':   dict(name='The Four Turns', seeds=[(160, 140), (150, 128), (172, 148)]),
    'toe':         dict(name='The Walking Toe', seeds=[(160, 236), (158, 216), (152, 252)]),
    'adderstones': dict(name='The Adder Stones', seeds=[(194, 196), (198, 172), (204, 150)]),
    'scree':       dict(name='The Scree Run', seeds=[(200, 128), (212, 100), (190, 108)]),
    'frostrim':    dict(name='The Frostwake Rim', seeds=[(226, 126), (224, 92), (226, 64)]),
    'whitebark':   dict(name='The Whitebark Slopes', seeds=[(132, 100), (142, 90), (118, 112)]),
    'whitewood':   dict(name='The Whitebark Wood', seeds=[(118, 56), (132, 48), (104, 46), (150, 74)]),
    'singing':     dict(name='The Singing Heights', seeds=[(98, 72), (90, 90), (108, 84)]),
    'hollowpeaks': dict(name='The Hollow Peaks', seeds=[(64, 52), (54, 72), (78, 42)]),
    'stormridge':  dict(name='The Stormgate Ridge', seeds=[(166, 40), (178, 62), (192, 62)]),
    'spires':      dict(name='The Condor Spires', seeds=[(212, 34), (226, 44), (200, 24)]),
    'coast':       dict(name='The Cold Coast', seeds=[(100, 26), (130, 14), (150, 12), (180, 14)]),
}
GROUND = {'slate': 1, 'ochre': 2, 'scree': 3, 'snow': 4, 'ash': 5, 'shale': 6, 'lichen': 7, 'pale': 8, 'basalt': 9}
REGION_GROUND = {'terraces': 'ochre', 'prismverge': 'scree', 'fourturns': 'slate', 'toe': 'shale', 'adderstones': 'pale', 'scree': 'scree', 'frostrim': 'snow', 'whitebark': 'ash',
                 'whitewood': 'ash', 'singing': 'lichen', 'hollowpeaks': 'basalt', 'stormridge': 'slate', 'spires': 'shale', 'coast': 'pale'}

R = {'cairn_boulder': 1.3, 'cairn_pebble': .17, 'cairn_dead_tree': .9, 'cairn_slate_spire': .8, 'cairn_windbanner': .15, 'cairn_stack': .55, 'cairn_lichen_rock': .7,
     'cairn_watchhall': 2.2, 'cairn_signal': .8, 'cairn_stonecircle': 1.0, 'cairn_whitegrove': 1.0, 'cairn_eyrie': 1.1, 'cairn_boulder_altar': 1.1}
TALL = ('cairn_dead_tree', 'cairn_slate_spire')

# scenery per 1000 land tiles of the region (x DENSITY_SCALE)
DENSITY_SCALE = 1.0
DENSITY = {
    'terraces':    [('cairn_boulder', 3), ('cairn_pebble', 8), ('cairn_stack', 3), ('cairn_lichen_rock', 3), ('cairn_windbanner', 1.2), ('cairn_dead_tree', 2)],
    'prismverge':  [('cairn_boulder', 4), ('cairn_pebble', 8), ('cairn_slate_spire', 3), ('cairn_lichen_rock', 3), ('cairn_stack', 1.5)],
    'fourturns':   [('cairn_boulder', 5), ('cairn_pebble', 6), ('cairn_stack', 3), ('cairn_slate_spire', 3), ('cairn_windbanner', 1.5), ('cairn_dead_tree', 2)],
    'toe':         [('cairn_boulder', 9), ('cairn_pebble', 8), ('cairn_slate_spire', 3), ('cairn_lichen_rock', 3)],
    'adderstones': [('cairn_boulder', 10), ('cairn_pebble', 8), ('cairn_lichen_rock', 5), ('cairn_stack', 2)],
    'scree':       [('cairn_boulder', 4), ('cairn_pebble', 12), ('cairn_slate_spire', 4), ('cairn_stack', 2)],
    'frostrim':    [('cairn_slate_spire', 5), ('cairn_boulder', 4), ('cairn_pebble', 6), ('cairn_windbanner', 1.5)],
    'whitebark':   [('cairn_dead_tree', 10), ('cairn_boulder', 2), ('cairn_pebble', 6), ('cairn_lichen_rock', 2)],
    'whitewood':   [('cairn_dead_tree', 18), ('cairn_pebble', 4), ('cairn_boulder', 2), ('cairn_lichen_rock', 2)],
    'singing':     [('cairn_boulder', 4), ('cairn_pebble', 6), ('cairn_stack', 4), ('cairn_slate_spire', 4), ('cairn_dead_tree', 4), ('cairn_lichen_rock', 3)],
    'hollowpeaks': [('cairn_slate_spire', 7), ('cairn_boulder', 6), ('cairn_pebble', 6), ('cairn_dead_tree', 3)],
    'stormridge':  [('cairn_slate_spire', 6), ('cairn_boulder', 4), ('cairn_pebble', 6), ('cairn_windbanner', 1.5), ('cairn_stack', 2)],
    'spires':      [('cairn_slate_spire', 10), ('cairn_boulder', 3), ('cairn_pebble', 5), ('cairn_dead_tree', 2)],
    'coast':       [('cairn_pebble', 8), ('cairn_boulder', 3), ('cairn_slate_spire', 2), ('cairn_lichen_rock', 2), ('cairn_dead_tree', 2)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): ferrets on the low scree, ibex on the slopes, ravens on the heights and the coast,
# adders on the warm stones
SPAWN_SCALE = 1.0
SPAWN_DENSITY = {
    'terraces':    {'screeferret': 1.6, 'ridgeadder': .8},
    'prismverge':  {'screeferret': 2.4, 'stoneibex': .8},
    'fourturns':   {'stoneibex': 2.2, 'screeferret': 1.0},
    'toe':         {'ridgeadder': 1.8, 'screeferret': 1.0},
    'adderstones': {'ridgeadder': 3.4},
    'scree':       {'screeferret': 2.2, 'stoneibex': 1.2},
    'frostrim':    {'slateraven': 2.0, 'stoneibex': 1.2},
    'whitebark':   {'stoneibex': 3.0, 'slateraven': .6},
    'whitewood':   {'slateraven': 2.4, 'stoneibex': 1.0},
    'singing':     {'slateraven': 2.2, 'ridgeadder': 1.2},
    'hollowpeaks': {'ridgeadder': 1.8, 'slateraven': 1.6},
    'stormridge':  {'slateraven': 2.4, 'screeferret': 1.2},
    'spires':      {'slateraven': 2.8},
    'coast':       {'slateraven': 1.6, 'screeferret': 1.0},
}


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def gates(F):
    """The Frostwake gate stands on the east rim, 2.5 tiles in from the last land cell, arrival six tiles inside; the Thunderheart door stands at the head of the northern ridge; the
    Prismwaste seam has no gate, only the crossing the roads aim at: id -> (x, y, walk, arrival)."""
    out = {}
    y = 118
    x1 = int(np.nonzero(F[y])[0].max())
    out['cairn_frostwake_gate'] = (x1 - 2.5, y + .5, (1, 0), (x1 - 8.5, y + .5))
    out['cairn_thunderheart_gate'] = (content.THUNDER[0], content.THUNDER[1] + .5, (0, -1), content.THUNDER_ARRIVAL)
    cx, cy = content.CROSS
    out['path_27_14'] = (cx, cy, (-1, 0), (round(cx + CROSS_IN * NORMAL[0], 2), round(cy + CROSS_IN * NORMAL[1], 2)))
    return out


def roads(G):
    fw, th, cr = G['cairn_frostwake_gate'], G['cairn_thunderheart_gate'], G['path_27_14']
    bw, sc, wb, sg = (HAM[k] for k in ('boulderwatch', 'singing', 'whitebark', 'stormgate'))
    pass_ = [(cr[0] + 1.2 * NORMAL[0], cr[1] + 1.2 * NORMAL[1]), cr[3], (116, 175), (130, 172), (144, 170), (bw['x'], bw['y'])]
    turns = [(bw['x'], bw['y']), (bw['x'], 152), (170, 146), (152, 140), (168, 133), (148, 126), (wb['x'], wb['y'])]
    west = [(wb['x'], wb['y']), (122, 106), (108, 98), (sc['x'], sc['y'])]
    north = [(wb['x'], wb['y']), (150, 100), (160, 88), (170, 74), (sg['x'], sg['y'])]
    gate = [(sg['x'], sg['y']), (172, 48), (166, 40), (th[0], 34), (th[0], th[1] - 1.2)]
    east = [(wb['x'], wb['y']), (160, 115), (184, 118), (208, 119), (fw[3][0], fw[3][1]), (fw[0], fw[1])]
    grove = [(124, 106), (125, 96), (125, 90)]
    cairn = [(sc['x'], sc['y']), (104, 91), (105, 80), (99, 72), (96, 69)]
    toe = [(bw['x'], bw['y']), (bw['x'], 188), (158, 200), (160, 212), (160, 218)]
    spires = [(sg['x'], sg['y']), (186, 58), (190, 52), (192, 49)]
    stones = [(bw['x'], bw['y']), (177, 172), (186, 172), (196, 172)]
    return [pass_, turns, west, north, gate, east, grove, cairn, toe, spires, stones]


class Cairn(Designer):
    TAG, SEED = 'cairn_design_v1', 20261111
    LATE_SEAMS = {26}       # the Frostwake Shelf's seam (2026-11-09) replaced the east rim gate after this design was approved: the masks stay as they were

    def __init__(self, world, old):
        self.old = old
        self.F = np.array([[c == '#' for c in row] for row in world['shapeFloor']])
        self.G = gates(self.F)
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        self.pooled = np.full((self.n, self.n), 1e9)

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.seam[iy, ix] > SEAM_LOOSE
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
            placed += self.scatter([kind], k, self.mask(name) & (self.seam > SEAM_LOOSE), gap=1.6 if tall else gap, road=3.4 if tall else road)
        return placed

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        self.ground = np.zeros((self.n, self.n), np.uint8)
        self.fixed = [o for o in self.w['objects'] if o['kind'] == 'void']
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        for h in HAM.values():
            assert self.F[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 9)
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3.5)
        for x, y in self.bells():
            self.block_disc(x, y, 3.5)
        self.add('cairn_thunder_gate', content.THUNDER[0], content.THUNDER[1] - 1.4, r=0, v=0, place='cairn_thunder', open=True)       # behind the portal: the way in and out runs south of it
        self.add('cairn_stonecircle', 96, 66, r=1.0, v=0)
        self.add('cairn_whitegrove', 125, 84, r=1.0, v=0)
        self.add('cairn_eyrie', 206, 38, r=1.1, v=0)
        self.add('cairn_boulder_altar', 196, 98, r=1.1, v=0)
        content.dress(self, HAM)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    @staticmethod
    def bells():
        return [(52 + content.BELLS_SHIFT[0], 62 + content.BELLS_SHIFT[1]), (59 + content.BELLS_SHIFT[0], 62 + content.BELLS_SHIFT[1]), (66 + content.BELLS_SHIFT[0], 62 + content.BELLS_SHIFT[1])]

    def landmarks(self):
        ex = {k: (x, y) for k, x, y in content.ELITES}
        # a ring of boulders round the Behemoth's toe, dead trees round the Titan's wood, spires round the Condor's roost and the Bear's hollow (each open on one side)
        self.ring_of(ex['cairnbehemoth'], 11, 14, 'cairn_boulder', rot=.2, gaps=[(270, 35)])
        self.ring_of(ex['whitebarktitan'], 19, 18, 'cairn_dead_tree', rot=.5, gaps=[(110, 40)])
        self.ring_of(ex['stormcondor'], 16, 16, 'cairn_slate_spire', rot=.1, gaps=[(200, 40)])
        self.ring_of(ex['avalanchebear'], 15, 16, 'cairn_slate_spire', rot=.3, gaps=[(40, 40)])
        # windbanners in pairs either side of the Four Turns road, a cairn stack at every bend
        pts = dense_points(self.ROADLIST[1], 1.0)
        for i in range(8, len(pts) - 4, 12):
            x, y = pts[i]
            side = 1 if (i // 12) % 2 else -1
            if self.ok(x + side * 3.4, y, 'cairn_windbanner', lane=2.4):
                self.add('cairn_windbanner', x + side * 3.4, y)
        for x, y in self.ROADLIST[1][2:-1]:
            if self.ok(x + 2.8, y + 1.5, 'cairn_stack', lane=2.0):
                self.add('cairn_stack', x + 2.8, y + 1.5)
        # a low ring of stacks round every hold circle
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'cairn_stack', rot=.4)

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        self.objects[:] = [o for o in self.objects if not (o['kind'] in TALL and o.get('layout') == self.TAG and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        ex = {k: (x, y) for k, x, y in content.ELITES}
        g[self.floor & (np.hypot(self.xs - ex['cairnbehemoth'][0], self.ys - ex['cairnbehemoth'][1]) < 13 + rough)] = GROUND['basalt']
        g[self.floor & (np.hypot(self.xs - ex['whitebarktitan'][0], self.ys - ex['whitebarktitan'][1]) < 14 + rough)] = GROUND['ash']
        g[self.floor & (np.hypot(self.xs - ex['stormcondor'][0], self.ys - ex['stormcondor'][1]) < 12 + rough)] = GROUND['snow']
        g[self.floor & (np.hypot(self.xs - ex['avalanchebear'][0], self.ys - ex['avalanchebear'][1]) < 12 + rough)] = GROUND['snow']
        g[self.floor & (np.hypot(self.xs - content.THUNDER[0], self.ys - content.THUNDER[1]) < 9 + rough)] = GROUND['basalt']          # the dark stone round the Thunderheart Gate
        g[self.floor & (self.coast < 6 + rough * .5)] = GROUND['pale']

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])
        for o in self.objects:
            if o['kind'] in TALL + ('cairn_boulder',) and o.get('layout') == self.TAG and 'v' not in o:
                o['v'] = self.rng.randrange(4)

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        out = []
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
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.seam > SEAM_SPAWN))      # 4.4 keeps a spawn 3.4+ tiles from every road
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
        ordinary.sort(key=lambda t: t['kind'] != 'screeferret')
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
    links = {n['id']: list(n.get('travelLinks', [])) for n in zone['npcs'] if n.get('travelStop')}       # the Spark links earlier designs added to the placeholder master in this run
    zone['npcs'] = copy.deepcopy(old['npcs'])
    for n in zone['npcs']:
        if n.get('travelStop') and n['id'] in links:
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + links[n['id']]))
    zone['places'] = copy.deepcopy(old['places'])
    zone['quests'] = copy.deepcopy(old['quests'])
    for n in zone['npcs']:
        if n['id'] in content.HUB_NPCS:
            hn, ox, oy = content.HUB_NPCS[n['id']]
            h = content.HAMLETS[hn]
            n['x'], n['y'] = h['x'] + ox, h['y'] + oy
        elif n['id'] in content.BOULDERWATCH_PEOPLE:
            h = content.HAMLETS['boulderwatch']
            n['x'], n['y'] = h['x'] + content.BOULDERWATCH_PEOPLE[n['id']][0], h['y'] + content.BOULDERWATCH_PEOPLE[n['id']][1]
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    mine = {p['id']: p for p in content.PLACES}
    for p in zone['places']:
        if p['id'] in mine:
            p['x'], p['y'], p['r'] = mine[p['id']]['x'], mine[p['id']]['y'], mine[p['id']]['r']
        elif p['id'].startswith('es_23_'):          # the Empty Seat's oath bells move rigidly with the Singing Cairn
            p['x'], p['y'] = round(p['x'] + content.BELLS_SHIFT[0], 2), round(p['y'] + content.BELLS_SHIFT[1], 2)
        else:
            raise AssertionError(f"unplaced old place {p['id']}")
    keep = []
    for p in zone['portals']:
        if p.get('seam'):          # the Prismwaste's seam (zone_shapes.make_seams): its line is the border, not a gate
            keep.append(p)
        else:
            gx, gy, walk, arr = G[p['id']]
            p['x'], p['y'] = round(gx, 2), round(gy, 2)
            if p['id'] == 'cairn_frostwake_gate':
                p['walk'] = list(walk)
            keep.append(p)
    zone['portals'] = keep
    zone['futureInstance'] = copy.deepcopy(old['futureInstance'])
    zone['futureInstance']['x'], zone['futureInstance']['y'] = content.THUNDER


def aim_seam(world, zone, G):
    """Both seam portals stand where the roads cross: on the border at the point the Prismwaste's own road ends (its old gate)."""
    mine = next(p for p in zone['portals'] if p.get('seam') and p['to'] == PRISM)
    theirs = next(p for p in world['zones'][PRISM - 1]['portals'] if p.get('seam') and p['to'] == ZONE)
    gx, gy, walk, arr = G['path_27_14']
    sh = mine['seam']['shift']
    mine['x'], mine['y'], mine['tx'], mine['ty'] = round(gx, 2), round(gy, 2), round(gx + sh[0], 2), round(gy + sh[1], 2)
    theirs['x'], theirs['y'], theirs['tx'], theirs['ty'] = mine['tx'], mine['ty'], mine['x'], mine['y']
    return (mine['x'], mine['y'])


def aim_frostwake_seam(world, zone, G):
    """The Frostwake seam (2026-11-09) replaced the east rim gate: both seam portals stand where the east road already ends, on the border at the gate's row. Returns the point (our frame) or None."""
    mine = next((p for p in zone['portals'] if p.get('seam') and p['to'] == FROSTWAKE), None)
    if not mine:
        return None
    theirs = next(p for p in world['zones'][FROSTWAKE - 1]['portals'] if p.get('seam') and p['to'] == ZONE)
    y = G['cairn_frostwake_gate'][1]
    pts = mine['seam']['points']
    best = None
    for a, b in zip(pts, pts[1:]):
        if (a[1] - y) * (b[1] - y) <= 0 and a[1] != b[1]:
            t = (y - a[1]) / (b[1] - a[1])
            best = (a[0] + (b[0] - a[0]) * t, y)
            break
    assert best, 'the Frostwake border does not cross the east road row'
    sh = mine['seam']['shift']
    mine['x'], mine['y'], mine['tx'], mine['ty'] = round(best[0], 2), round(best[1], 2), round(best[0] + sh[0], 2), round(best[1] + sh[1], 2)
    theirs['x'], theirs['y'], theirs['tx'], theirs['ty'] = mine['tx'], mine['ty'], mine['x'], mine['y']
    return (mine['x'], mine['y'])


def link_travel(world):
    """Add (never strip) the Spark links across every portal into or out of Cairnspine, both ways, as compact_atlas.sync_travel_links does."""
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
    aim_seam(world, zone, G)
    aim_frostwake_seam(world, zone, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the zone was rebuilt
    d = Cairn(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    d.late_dropped = d.late_moved = 0
    if any(p.get('seam') and p['to'] == FROSTWAKE for p in zone['portals']):      # the Frostwake seam (2026-11-09) replaced the east gate: only the spawns within 7 tiles of it and the loose scenery within 2.5 go, and the art-less objects within 20 step back
        d.late_dropped = drop_near_seam(zone, d, FROSTWAKE)
        loose = [o for o in objects if o.get('layout') == d.TAG and o['kind'] != 'void' and d.seam_late[min(max(int(o['y']), 0), d.n - 1), min(max(int(o['x']), 0), d.n - 1)] < 2.5]
        objects = [o for o in objects if o not in loose]
        d.late_dropped += len(loose)
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    zone['levels'] = [90, 95]
    seamed = {p['id'] for p in zone['portals'] if p.get('seam')}
    zone['exitRoutes'] = [dict(portal=g, points=[[round(G[g][0], 2), round(G[g][1], 2)], [round(G[g][3][0], 2), round(G[g][3][1], 2)]]) for g in ('cairn_frostwake_gate',) if g not in seamed]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, zone, HAM, old)
    if any(p.get('seam') and p['to'] == FROSTWAKE for p in zone['portals']):      # after the people stand in their final places (see greenmeadow_design.step_back_artless)
        d.late_moved = step_back_artless(zone, zone['objects'], d, FROSTWAKE)
    # every crossing that arrives here follows the new frame: Frostwake's gate and the Thunderheart Gate's two ways home (the Prismwaste seam carries its own shift)
    arrivals = {'frostwake_cairn_gate': G['cairn_frostwake_gate'][3], 'thunderheart_gate_return': content.THUNDER_ARRIVAL, 'thunderheart_gate_exit': content.THUNDER_ARRIVAL}
    found = set()
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals and not p.get('seam'):
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
                found.add(p['id'])
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
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']),
                 kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('cairn_boulder', 'cairn_pebble', 'cairn_dead_tree', 'cairn_slate_spire', 'cairn_windbanner', 'cairn_stack', 'cairn_lichen_rock')})
    if problems:
        if os.environ.get('CAIRN_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')


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
        if t.get('layout') == d.TAG and d.seam[int(t['y']), int(t['x'])] <= SEAM_SPAWN:
            problems.append(f'spawn within {SEAM_SPAWN:.0f} tiles of a seam {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
        if d.seam[int(n['y']), int(n['x'])] < SEAM_PEOPLE:
            problems.append(f"npc {n['id']} stands within {SEAM_PEOPLE:.0f} tiles of a seam (a plain seam draws no people)")
    for o in zone['objects']:
        if o['kind'] in ARTLESS and d.seam[int(o['y']), int(o['x'])] < SEAM_PEOPLE:
            problems.append(f"art-less {o['kind']} within {SEAM_PEOPLE:.0f} tiles of a seam at {o['x']},{o['y']}")
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
        if not d.floor[int(p['y']), int(p['x'])]:
            problems.append(f"place {p['id']} off land")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
    fw = G['cairn_frostwake_gate']
    walled = any(p.get('seam') and p['to'] == FROSTWAKE for p in zone['portals'])      # the Frostwake gate became a seam: no gate to check or re-aim
    if not walled and not seen[int(fw[1] - fw[2][1] * 3), int(fw[0] - fw[2][0] * 3)]:
        problems.append('Frostwake gate is blocked from the inside')
    for need in ('frostwake_cairn_gate', 'thunderheart_gate_return', 'thunderheart_gate_exit'):
        if need == 'frostwake_cairn_gate' and walled:
            continue
        if need not in found:
            problems.append(f'no incoming portal {need} found to re-aim')
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
        if not d.floor[int(ey), int(ex)]:
            problems.append(f'{kind} stands off the land')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    for p in zone['places']:
        if p.get('waves') and d.road[int(p['y']), int(p['x'])] < 4:
            problems.append(f"hold circle {p['id']} stands on a road")
    for k, x, y, tag in content.AMBUSH:
        if d.road[int(y), int(x)] < 3.4 or not d.floor[int(y), int(x)] or not seen[int(y), int(x)]:
            problems.append(f'ambush sleeper {tag} at {x},{y} stands on a road or off the land')
        if d.seam[int(y), int(x)] < 14:
            problems.append(f'ambush sleeper {tag} at {x},{y} stands near a seam')
    bad = set()
    for road in d.ROADLIST + [r['points'] for r in zone['exitRoutes']]:
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                if not d.floor[int(y), int(x)]:
                    problems.append(f'road leaves the land at {x:.0f},{y:.0f}')
                if solid[int(y), int(x)]:             # no exemption inside a camp: a road never runs through a tent, a fire or a stone there either (tests/seam-roads.py)
                    bad.add((int(x), int(y)))
    if bad:
        problems.append(f'something stands on the road at {sorted(bad)[:12]}')
    return problems


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    T = zone['shape']['T']
    s = 1758 / 2048
    atlas = Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB')
    x0, y0 = int(round(T[0] * s)), int(round(T[1] * s))
    bg = atlas.crop((x0, y0, x0 + int(n * s), y0 + int(n * s))).resize((n * scale, n * scale), Image.LANCZOS)
    bg = Image.blend(bg, Image.new('RGB', bg.size, (20, 24, 34)), .35)
    pal = {1: (90, 100, 120), 2: (190, 150, 90), 3: (150, 150, 150), 4: (225, 235, 250), 5: (200, 190, 160), 6: (60, 66, 82), 7: (110, 150, 110), 8: (210, 196, 160), 9: (40, 40, 52)}
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
    col = {'cairn_boulder': (120, 124, 130), 'cairn_pebble': (170, 160, 140), 'cairn_dead_tree': (235, 232, 215), 'cairn_slate_spire': (90, 100, 120), 'cairn_windbanner': (200, 140, 100),
           'cairn_stack': (190, 175, 150), 'cairn_lichen_rock': (210, 150, 60)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('cairn_pebble', 'cairn_windbanner') else 1)
        c = col.get(o['kind'], (255, 200, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'screeferret': (220, 190, 150), 'stoneibex': (190, 170, 130), 'slateraven': (120, 140, 200), 'ridgeadder': (150, 190, 120)}
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
    src = os.environ.get('CAIRN_WORLD')       # a cached shaped world (JSON), else the current map
    world = json.loads(Path(src).read_text() if src else MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])


if __name__ == '__main__':
    main()
