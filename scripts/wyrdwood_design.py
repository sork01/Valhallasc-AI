#!/usr/bin/env python3
"""The Wyrdwood as an authored map (zone 6 of the shapes pilot): no filler land, the whole outline used.

Runs in `zone_shapes.py apply` after the seams and the other designs. The outline is a fat triangle with its apex to the north (traced from
the owner's painted atlas: tile = painted px * 2048/1758 - shape.T, T = [168, 71]): the West coast on the left, the cloud wall to Bifrost on
the right, Rimeveil and the Crags along the base. The painting shows a brown massif with the River Skuld straight across its middle.
The old 192 square cannot sit inside it at k = 1.0 (a near miss, 1.25), so `zone_shapes.py` warps it in only to make a valid shaped zone and
this design replaces everything: scenery, spawns, trails, hubs, people, places and quests. The old topology stays (the owner's painting
agrees): the town south of the river, one bridge, the fort at the north end of it, two ridges with one gap each stepping up to the storm
giant on the summit.

Fixed, moved as rigid blocks from `world/zone-shapes/preshape-06.txt` (the old layout): Hollowmoot with the Elder Ash and its people, the
Skuldwatch fort with its palisade, the Norn Stones with the Nornroot door and its three admission stones, the gallows, the Ember Grave
Cross and its sleeper, the Empty Seat circle, the rift stones. Moved by id: every person, place, portal and quest keeps its id.

Water is drawn from this zone's own frame only: the neighbours do not draw `water`, and art-less kinds (houses, lamps, benches...) have no
ghost art, so none of those stands within 20 tiles of a seam.

    python3 scripts/wyrdwood_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
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
import wyrdwood_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-06.txt'

D_HOLLOW = (45, 127)        # old Hollowmoot (rect 9..57 x 131..172) -> 54..103 x 258..300
D_FORT = (70, 117.5)        # old Skuldwatch fort, the bridge, the Norn Stones -> bridge at x 166, river y 226
D_GALLOWS = (142, 150)      # old Gallows Rock (160,172) and the mill (179,176) -> (302,322) and (321,326)
BRIDGE_X = 166.0
RIVER_Y = 226.15
GATE = (221.5, 146.5)       # the Bifrost gate, on the cloud wall beside the Ridge Beacon
GATE_WALK = (1, 0)
SPAWN = (70.0, 281.0)
FORD = 3.4

REGIONS = {
    'moot':      dict(name='The Moot Fields', seeds=[(78, 282), (60, 300), (112, 286), (70, 262), (100, 262)]),
    'rotfang':   dict(name='The Rotfang Wood', seeds=[(40, 300), (36, 318), (80, 318), (120, 310), (28, 286)]),
    'glade':     dict(name='The Moonpetal Glade', seeds=[(150, 298), (140, 306)]),
    'wyrdgate':  dict(name='The Wyrdgate Rise', seeds=[(170, 316), (200, 322), (132, 318), (210, 300)]),
    'banks':     dict(name='The Troll Banks', seeds=[(70, 246), (110, 244), (150, 244), (190, 246), (230, 246), (270, 246)]),
    'oakgrove':  dict(name="The Oakhorn's Grove", seeds=[(248, 262), (228, 272), (262, 270)]),
    'gallows':   dict(name='Gallows Hill', seeds=[(302, 316), (288, 306), (314, 308), (284, 328)]),
    'fells':     dict(name='The East Fells', seeds=[(330, 296), (312, 280), (296, 262), (300, 250)]),
    'mill':      dict(name='The Ruined Mill', seeds=[(330, 326), (352, 332), (320, 340)]),
    'yard':      dict(name='The Skuldwatch Yard', seeds=[(166, 190), (126, 205), (208, 205), (100, 214), (240, 214)]),
    'norn':      dict(name='The Norn Terrace', seeds=[(166, 172), (130, 176), (206, 176), (110, 190), (226, 190)]),
    'cliffs':    dict(name='The West Cliffs', seeds=[(90, 182), (76, 200), (100, 168)]),
    'terrace':   dict(name='The Storm Terrace', seeds=[(150, 144), (112, 140), (200, 146), (180, 134), (222, 150)]),
    'heights':   dict(name='The Highmoor', seeds=[(150, 112), (126, 108), (170, 108), (140, 96), (118, 118)]),
    'summit':    dict(name="Hrungnir's Summit", seeds=[(152, 76), (150, 64)]),
}

ROADS = [
    # Hollowmoot: the west gate posts, the plaza, the east gate
    [(49.5, 277), (54.5, 277), (78, 277), (103, 277)],
    # the Troll Bank road: east gate up the bank to the Troll Bridge, over it, through the fort gate, the plaza and out of the north gate
    [(103, 277), (118, 270), (132, 262), (146, 252), (158, 243), (166, 236), (166, 216), (166, 204), (166, 191), (167.4, 187), (167.4, 181)],
    # the south road: east gate down past the glade to Gallowsfoot
    [(103, 277), (120, 290), (140, 296), (150, 300), (175, 300), (205, 298), (230, 298), (255, 300)],
    # the Wyrdgate road: the south road down to the Rimeveil border
    [(120, 290), (128, 306), (136, 320), (141, 330)],
    # the Gallows trunk: the bridge's south end SE past the Oakhorn's Grove to Gallowsfoot, the hill and the mill
    [(166, 236), (190, 247), (214, 256), (236, 268), (252, 282), (255, 292), (262, 304), (280, 313), (302, 322), (316, 321.5)],
    # the mill to the Crags border
    [(316, 321.5), (326, 320.5), (340, 327), (356, 337), (368, 343)],
    # to the Ember Grave Cross
    [(103, 277), (112, 284), (114, 285)],
    # to Hollowmoot's Rotfang trail
    [(54.5, 277), (46, 290), (42, 306), (40, 316)],
    # the Norn Stones, the West Beacon, the barrow
    [(166, 190), (150, 187), (126, 182), (110, 178), (96, 176)],
    [(167.4, 185.5), (154, 185.5), (154, 183.5)],
    # up to the ridge: Norn terrace to the east gap, the Ridge Beacon and the Bifrost gate
    [(167.4, 181), (172, 170), (190, 166), (206, 166), (222.5, 165), (222.5, 156), (221.5, 146.5)],
    # the Ridge Beacon, the camp, the terrace and the west gap
    [(206, 150), (204, 145), (194, 143), (180, 143), (150, 138), (128, 136), (113, 133), (112.5, 126), (113, 118)],
    # up to the Storm Beacon and the hold, and on up to the giant's ring
    [(113, 118), (120, 108)],
    [(120, 108), (136, 110), (150, 112), (152, 102), (152, 92)],
    [(122, 100), (120, 108)],
]

# the river: a thick line (x, y, half width) from the sea to the cloud wall, and the stones of the ridges
RIVER = [(40, 226, 6.2), (60, 227, 6.2), (90, 225.5, 6.4), (120, 226.8, 6.2), (150, 225.6, 6.4), (180, 226.4, 6.2), (210, 225.4, 6.4), (240, 226.8, 6.2), (270, 226, 6.2), (292, 226, 6.2)]
RIDGE1 = dict(pts=[(70, 164), (100, 160), (130, 161.5), (160, 159), (190, 161), (220, 159), (250, 157)], gap=(218.5, 226.5))
RIDGE2 = dict(pts=[(80, 131), (110, 129), (140, 127.5), (170, 129), (200, 126), (225, 126)], gap=(108.5, 116.5))

R = {'tree': .42, 'pine': .42, 'bush': .30, 'rock': .40, 'spire': .55, 'crag': 1.5, 'water': 2.3, 'post': .3, 'bones': 1.1, 'gallows': .6, 'lamp': .18, 'beacon': .9,
     'brazier': .4, 'barrels': 0}
GROUND = {'leaf': 1, 'moss': 2, 'heath': 3, 'scree': 4, 'bank': 5, 'gold': 6, 'ember': 7}

SPAWNS = {
    'moot':     {'boar': 12},
    'rotfang':  {'boar': 36, 'crow': 3},
    'glade':    {'boar': 6},
    'wyrdgate': {'crow': 18, 'boar': 4},
    'banks':    {'troll': 30},
    'oakgrove': {'crow': 8, 'boar': 4},
    'gallows':  {'crow': 22, 'troll': 3},
    'fells':    {'troll': 16, 'crow': 4},
    'mill':     {'crow': 8, 'troll': 6},
    'yard':     {'weaver': 6},
    'norn':     {'weaver': 28},
    'cliffs':   {'weaver': 14, 'ram': 2},
    'terrace':  {'ram': 30},
    'heights':  {'ram': 24, 'weaver': 4},
    'summit':   {'ram': 4},
}


def thick_mask(d, pts, wob=.18, scale=.08):
    best = np.full((d.n, d.n), 1e9)
    for (ax, ay, aw), (bx, by, bw) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        t = np.clip(((d.xs - ax) * dx + (d.ys - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
        dist = np.hypot(d.xs - ax - t * dx, d.ys - ay - t * dy)
        best = np.minimum(best, dist - (aw + (bw - aw) * t))
    return best < (fbm(d.noise, d.xs, d.ys, scale) - .5) * wob * 14


def moved(o, dx, dy):
    q = dict(o)
    q['x'] = round(o['x'] + dx, 2)
    q['y'] = round(o['y'] + dy, 2)
    return q


def in_rect(o, x0, y0, x1, y1):
    return x0 <= o['x'] <= x1 and y0 <= o['y'] <= y1


class Wyrdwood(Designer):
    TAG, SEED = 'wyrdwood_design_v1', 20261110
    LATE_SEAMS = set()      # this zone was designed with every seam in place

    def __init__(self, world, old):
        self.old = old
        self._exits = [r['points'] for r in world['exitRoutes']]
        super().__init__(world)

    def plan(self):
        return REGIONS, ROADS, R

    def scatter(self, kinds, count, where, gap=.65, road=3.0):
        return super().scatter(kinds, int(count * .85), where, gap, road)

    def make_regions(self):
        out = super().make_regions()
        # the river divides the banks (south) from the yard (north): a seed on one side must not claim the other bank
        names = list(REGIONS)
        banks, yard = names.index('banks'), names.index('yard')
        out[(self.ys < RIVER_Y) & (out == banks)] = yard
        out[(self.ys >= RIVER_Y) & (out == yard)] = banks
        return out

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def water_at(self, x, y, r):
        self.add('water', x, y, r=round(float(r), 2), solid=False)
        self.grid.add(round(float(x), 2), round(float(y), 2), r)

    def lay_river(self):
        """Hex-packed solid water circles over the river band, right out to the coast and the cloud wall, with the bridge's corridor left dry."""
        mask = thick_mask(self, RIVER, wob=.05)
        r, step = 2.3, 2.9
        placed = 0
        todo = []
        y, row = 3.0, 0
        while y < self.n - 2:
            x = 3.0 + (step / 2 if row % 2 else 0)
            while x < self.n - 2:
                if mask[int(y), int(x)] and self.floor[int(y), int(x)] and not (abs(x - BRIDGE_X) < 2.8 + r and 214 < y < 238):
                    self.water_at(x, y, r)
                    todo.append((x, y, r))
                    placed += 1
                x += step
            y += step * .866
            row += 1
        for x, y, r in todo:
            self.block_disc(x, y, r + 1.4)
        self.river_cells = mask
        return placed

    def ridge(self, spec, gaps=None):
        """A wall of crags along a polyline, closed from coast to cloud wall except for one gap."""
        pts = spec['pts']
        g0, g1 = spec['gap']
        n = 0
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            ln = math.dist((ax, ay), (bx, by))
            k = int(ln / 1.9) + 1
            ux, uy = (bx - ax) / ln, (by - ay) / ln
            for s in range(k):
                x = ax + (bx - ax) * s / k
                y = ay + (by - ay) * s / k
                if g0 <= x <= g1:
                    continue
                px, py = -uy, ux
                j = self.rng.uniform(-.8, .8)
                x, y = x + px * j + self.rng.uniform(-.25, .25), y + py * j
                if 0 <= int(x) < self.n and 0 <= int(y) < self.n and self.floor[int(y), int(x)]:
                    self.add('crag', x, y, r=1.5)
                    n += 1
        return n

    def ring(self, centre, radius, n, kind, **extra):
        for k in range(n):
            a = k / n * math.tau + .3
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if 0 <= int(x) < self.n and 0 <= int(y) < self.n and self.floor[int(y), int(x)] and self.road[int(y), int(x)] > 2.4:
                self.add(kind, x, y, **extra)

    def take_block(self, rect, delta, kinds=None, skip=None):
        """Old objects inside `rect` (old coordinates), moved by `delta`, kept as they are."""
        out = []
        for o in self.old['objects']:
            if kinds and o['kind'] not in kinds:
                continue
            if not in_rect(o, *rect) or (skip and skip(o)):
                continue
            q = moved(o, *delta)
            q['layout'] = self.TAG
            out.append(q)
            if q['kind'] != 'void' and (q['r'] > 0 or q.get('width', 0) > 0):
                self.grid.add(q['x'], q['y'], max(q['r'], q.get('width', 0) / 2))
        return out

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        w, old = self.w, self.old
        hollow, fort = D_HOLLOW, D_FORT
        self.fixed = []
        # the old city and camp, as rigid blocks (the bridge posts are laid again below)
        fixed = self.take_block((4, 130, 58, 173), hollow)
        fixed += self.take_block((66, 73.5, 127, 99.5), fort, skip=lambda o: o['kind'] == 'post' and o['y'] > 98)
        # the Norn Stones: the ring and the three admission stones (old (96,57)), with the barrow door beside them
        fixed += self.take_block((86, 48, 106, 73), fort, kinds=('spire',))
        # the gallows, the stone beside the mill and the mill itself
        fixed += self.take_block((130, 154, 182, 182), D_GALLOWS, kinds=('gallows', 'spire', 'house'), skip=lambda o: o['kind'] == 'spire')
        # the rift stones (the old Stormrift): moved to the Highmoor's west, where the Gale Stones hold
        fixed += [dict(moved(o, 122 - 24, 100 - 9), layout=self.TAG) for o in old['objects'] if o['kind'] == 'spire' and o.get('rift')]
        self.fixed = fixed
        # blocks that did not move with the fort (none expected)
        self.ground = np.zeros((self.n, self.n), np.uint8)
        city = w['city']
        self.block(city['x0'] - 3, city['y0'] - 3, city['x1'] + 3, city['y1'] + 3)
        fort_camp = w['camps'][0]
        self.block(fort_camp['x0'] - 3, fort_camp['y0'] - 3, fort_camp['x1'] + 3, fort_camp['y1'] + 6)
        for o in w['objects']:
            if o['kind'] == 'void':
                self.fixed.append(o)
        for p in w['places'] + w['crosses']:
            self.block_disc(p['x'], p['y'], 5)
        for p in w['portals']:
            if not p.get('seam'):
                self.block_disc(p['x'], p['y'], 9)
                self.block_disc(p['x'] - p.get('walk', (0, 0))[0] * 8, p['y'] - p.get('walk', (0, 0))[1] * 8, 9)
        self.block_disc(*SPAWN, 5)
        self.blocked |= self.seam < 2.5
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
        for ring_c in ((152, 78),):
            self.block_disc(*ring_c, 12)
        for o in self.fixed:
            if o['kind'] != 'void' and (o['r'] > 0 or o.get('width', 0) > 0):
                self.grid.add(o['x'], o['y'], max(o['r'], o.get('width', 0) / 2))
        self.water_count = self.lay_river()
        # the bridge
        ys = np.linspace(216.5, 233.5, 8)
        for yy in ys:
            for xx in (BRIDGE_X - 3, BRIDGE_X + 3):
                self.add('post', xx, yy, r=.3, v=1)
        self.add('banner', BRIDGE_X - 4, 215.4, r=.3, color='#9a2f3a', solid=False)
        self.add('banner', BRIDGE_X + 4, 215.4, r=.3, color='#9a2f3a', solid=False)
        self.wdist = np.full((self.n, self.n), 1e9)
        for o in self.objects:
            if o['kind'] == 'water':
                r = int(o['r'] + 12)
                y0, y1, x0, x1 = max(int(o['y']) - r, 0), int(o['y']) + r, max(int(o['x']) - r, 0), int(o['x']) + r
                sub = np.hypot(self.xs[y0:y1, x0:x1] - o['x'], self.ys[y0:y1, x0:x1] - o['y']) - o['r']
                self.wdist[y0:y1, x0:x1] = np.minimum(self.wdist[y0:y1, x0:x1], sub)
        self.ridges = (self.ridge(RIDGE1), self.ridge(RIDGE2))
        content.dress(self, content.HAMLETS)
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        self.objects[:] = [o for o in self.objects if not (o['kind'] in ('tree', 'pine', 'spire') and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        """Ground classes beside the default leaf litter. None within 16-30 tiles of a seam: the other side blends toward its plain ground."""
        G, g = GROUND, self.ground
        far = self.seam > 16 + fbm(self.noise, self.xs, self.ys, .09) * 14
        for name, cls in (('moot', 'leaf'), ('rotfang', 'moss'), ('glade', 'gold'), ('wyrdgate', 'leaf'), ('banks', 'moss'), ('oakgrove', 'gold'), ('gallows', 'scree'),
                          ('fells', 'scree'), ('mill', 'moss'), ('yard', 'heath'), ('norn', 'heath'), ('cliffs', 'scree'), ('terrace', 'heath'), ('heights', 'heath'), ('summit', 'scree')):
            g[self.mask(name) & far] = G[cls]
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 5
        g[self.floor & far & (self.wdist + rough * .4 < 2.0)] = G['bank']
        ember = np.hypot(self.xs - 114, self.ys - 285) < 7 + rough
        g[ember & far] = G['ember']

    def lay_regions(self):
        dense = fbm(self.noise, self.xs + 200, self.ys + 300, .05)
        m = self.mask
        sc = self.scatter
        # The Moot Fields: tilled edges and oaks round the town
        sc(['tree', 'tree', 'bush'], 380, m('moot') & (dense > .4), gap=1.3)
        sc(['rock', 'bush'], 160, m('moot'), gap=1.4)
        # The Rotfang Wood: the oldest forest, thick with oaks and red-blighted undergrowth
        sc(['tree', 'tree', 'pine', 'bush'], 1100, m('rotfang') & (dense > .32), gap=1.0)
        sc(['bush', 'rock'], 260, m('rotfang'), gap=1.1)
        self.ring((40, 316), 5.5, 7, 'bones', r=1.1)
        # The Moonpetal Glade: a clearing of bracken and bees, a ring of old stones
        self.block_disc(150, 298, 7)
        self.ring((150, 298), 8, 9, 'rock')
        sc(['bush', 'bush', 'tree'], 140, m('glade'), gap=1.1)
        # The Wyrdgate Rise: oak and storm pine over the rise down to the Rimeveil border
        sc(['tree', 'pine', 'tree', 'bush'], 640, m('wyrdgate') & (dense > .35), gap=1.1)
        sc(['rock', 'bush'], 200, m('wyrdgate'), gap=1.3)
        # The Troll Banks: boulders and willows along the river's south bank
        sc(['rock', 'rock', 'bush', 'tree'], 520, m('banks'), gap=1.0)
        # The Oakhorn's Grove: the old oaks, close together, and a ring of stones round the thread
        self.block_disc(248, 262, 10)
        self.ring((248, 262), 10.5, 10, 'rock')
        sc(['tree', 'tree', 'tree', 'bush'], 480, m('oakgrove') & (dense > .3), gap=1.0)
        # Gallows Hill: dead trees, boulders, ribcages round the beam
        sc(['rock', 'rock', 'tree', 'bush'], 300, m('gallows'), gap=1.2)
        self.ring((308, 318), 12, 6, 'bones', r=1.1)
        # The East Fells: scree, crag outcrops and storm pines up to the cloud wall
        sc(['rock', 'rock', 'pine', 'bush'], 520, m('fells'), gap=1.1)
        sc(['crag'], 90, m('fells'), gap=2.5)
        # The Ruined Mill: a millrace of willows and rubble
        sc(['tree', 'rock', 'bush'], 260, m('mill'), gap=1.2)
        # The Skuldwatch Yard: cleared ground round the fort
        sc(['rock', 'bush', 'bush'], 240, m('yard'), gap=1.4)
        # The Norn Terrace: heather, boulders and stones round the Norn ring
        sc(['rock', 'pine', 'bush', 'rock'], 520, m('norn'), gap=1.2)
        sc(['spire'], 24, m('norn'), gap=6)
        # The West Cliffs: crags and pine above the sea
        sc(['pine', 'rock', 'pine'], 340, m('cliffs'), gap=1.1)
        sc(['crag'], 90, m('cliffs'), gap=2.5)
        # The Storm Terrace: the rams' ground, heather and crag outcrops
        sc(['rock', 'bush', 'pine', 'rock'], 520, m('terrace'), gap=1.2)
        sc(['crag'], 60, m('terrace'), gap=2.5)
        # The Highmoor: moor, standing stones, bones
        sc(['bush', 'rock', 'pine'], 420, m('heights'), gap=1.2)
        sc(['spire'], 18, m('heights'), gap=6)
        self.ring((126, 118), 6, 5, 'bones', r=1.1)
        # Hrungnir's Summit: the twelve stones of the ring
        self.ring((152, 78), 8.5, 12, 'spire', r=.55)
        sc(['rock', 'rock', 'pine'], 120, m('summit'), gap=1.4)

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        tags = {t for *_, t in content.AMBUSH}
        old_sleepers = [s for s in self.old['slimes'] if s.get('ambush') and s['ambush'] not in tags and not s['ambush'].startswith('wyrd_eydis')]
        # the old sleepers (the Ember Grave Cross firelord, the Empty Seat foes) move with their block
        sleepers = []
        for s in old_sleepers:
            if s['kind'] == 'ember_firelord':
                sleepers.append(dict(s, x=round(s['x'] + D_HOLLOW[0], 2), y=round(s['y'] + D_HOLLOW[1], 2)))
            else:
                sleepers.append(dict(s, x=round(150 + (s['x'] - 44), 2), y=round(298 + (s['y'] - 184), 2)))
        out = list(sleepers) + [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in content.HAMLETS.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
        city = w['city']
        keep[city['y0'] - 8:city['y1'] + 9, city['x0'] - 8:city['x1'] + 9] = True
        fc = w['camps'][0]
        keep[int(fc['y0']) - 8:int(fc['y1']) + 9, int(fc['x0']) - 8:int(fc['x1']) + 9] = True
        solid = Grid()
        for o in self.fixed + self.objects:
            if o['kind'] != 'void':
                solid.add(o['x'], o['y'], max(o['r'], (o.get('width', 0) + o.get('depth', 0)) / 4))
        self.short = {}
        for name, kinds in SPAWNS.items():
            pool = [k for k, c in kinds.items() for _ in range(c)]
            rng.shuffle(pool)
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 3.5) & (self.seam > 7))
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
        ordinary.sort(key=lambda t: t['kind'] != 'boar')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


# ---- moving the old people, places and portals ---------------------------------------------------------------------------
def shifted_state(zone, old):
    """Hubs, people, places, cross, portals and the escort in the new frame."""
    hx, hy = D_HOLLOW
    fx, fy = D_FORT
    gx, gy = D_GALLOWS
    c = old['city']
    zone['city'] = dict(c, x0=c['x0'] + hx, x1=c['x1'] + hx, y0=c['y0'] + hy, y1=c['y1'] + hy, plaza=dict(x=c['plaza']['x'] + hx, y=c['plaza']['y'] + hy),
                        entry=dict(x=c['entry']['x'] + hx, y=c['entry']['y'] + hy))
    k = old['camps'][0]
    camp = dict(k, x0=k['x0'] + fx, x1=k['x1'] + fx, y0=k['y0'] + fy, y1=k['y1'] + fy, plaza=dict(x=k['plaza']['x'] + fx, y=k['plaza']['y'] + fy),
                entry=dict(x=k['entry']['x'] + fx, y=k['entry']['y'] + fy))
    zone['spawn'] = dict(x=SPAWN[0], y=SPAWN[1])
    zone['camps'] = [camp]
    by = {n['id']: n for n in zone['npcs']}
    for n in old['npcs']:
        t = by.get(n['id'])
        if not t:
            continue
        i = n['id']
        if i in ('wyrd_eydis',):
            dx, dy = gx, gy
        elif i in ('wyrd_captain', 'wyrd_beacon', 'wyrd_mender', 'wyrd_quartermaster', 'wyrd_loremaster', 'wyrd_windspeaker', 'wyrd_smith', 'travel_skuldwatch', 'barrow_guide', 'barrow_scribe', 'mailbox_6_skuldwatch'):
            dx, dy = fx, fy
        else:
            dx, dy = hx, hy
        t['x'], t['y'] = round(n['x'] + dx, 2), round(n['y'] + dy, 2)
    pos = {
        'wyrd_glade': (150, 298), 'wyrd_gallows_rock': (302, 322), 'wyrd_beacon_west': (96, 176), 'wyrd_beacon_ridge': (206, 150), 'wyrd_beacon_storm': (120, 108),
        'wyrd_norn_stones': (96 + fx, 57 + fy), 'admit_cradle': (96 + fx, 58 + fy), 'admit_oath': (96 + fx, 65 + fy), 'admit_farewell': (88 + fx, 71 + fy), 'es_06_m': (150, 298),
    }
    for p in zone['places']:
        if p['id'] in pos:
            p['x'], p['y'] = pos[p['id']]
    for cx in zone['crosses']:
        cx['x'], cx['y'] = round(69 + hx, 2), round(158 + hy, 2)
    for p in zone['portals']:
        if p['id'] == 'wyrd_nornroot':
            p['x'], p['y'] = 84 + fx, 66 + fy
        elif p['id'] == 'sky_gate':
            p['x'], p['y'], p['walk'] = GATE[0], GATE[1], list(GATE_WALK)
    return camp


def escort(zone):
    """Eydis walks from the mill back along the Gallows trunk, over the Troll Bridge and into the fort: the road is clear by construction."""
    # (the fort's south gate has a lamp on the centre line: the last legs pass one tile east of it, as the old route did)
    road = ROADS[4][::-1] + [(166, 236), (167, 234), (167, 216), (167.25, 210), (166.25, 209.25)]
    pts = [(318, 324)] + [p for p in road[1:]]
    pts = [(round(a, 2), round(b, 2)) for a, b in pts]
    route = [list(pts[0])]
    for a, b in zip(pts, pts[1:]):
        k = max(1, math.ceil(math.dist(a, b) / 16))
        for s in range(1, k + 1):
            route.append([round(a[0] + (b[0] - a[0]) * s / k, 2), round(a[1] + (b[1] - a[1]) * s / k, 2)])
    eydis = next(n for n in zone['npcs'] if n['id'] == 'wyrd_eydis')
    eydis['escort']['route'] = route
    eydis['escort']['ambush'] = [dict(at=[290, 312], r=11.0, tag='wyrd_eydis#crow'), dict(at=[183, 246], r=11.0, tag='wyrd_eydis#troll')]
    eydis['x'], eydis['y'] = 318.0, 324.0
    return route


def design(world, write=False):
    zone = world['zones'][5]
    old = json.loads(OLD.read_text())
    camp = shifted_state(zone, old)
    zone['exitRoutes'] = [dict(portal='sky_gate', points=[list(GATE), [GATE[0] - 6, GATE[1]]])]
    d = Wyrdwood(zone, old)
    # the gate and its road before any scenery is laid
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    zone['objects'] = objects
    zone['paths'] = [[list(p) for p in road] for road in ROADS]
    zone['atlasPaths'] = []
    zone['bridges'] = [dict(x0=BRIDGE_X, y0=round(RIVER_Y - 10.99, 2), x1=BRIDGE_X, y1=round(RIVER_Y + 8.01, 2), w=5.0)]
    zone['exitRoutes'] = [dict(portal='sky_gate', points=[list(GATE), [GATE[0] - 6, GATE[1]]])]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(zone, content.HAMLETS, camp)
    route = escort(zone)
    # the portals that arrive here: Bifrost's Stormrift and both doors out of the barrow
    arrival = [GATE[0] - GATE_WALK[0] * 5.5, GATE[1] - GATE_WALK[1] * 5.5]
    for zi in (6, 40):
        for p in world['zones'][zi]['portals']:
            if p['to'] == 6:
                if p['id'].startswith('barrow'):
                    p['tx'], p['ty'] = 84 + D_FORT[0], 71 + D_FORT[1]
                else:
                    p['tx'], p['ty'] = arrival
    if write:
        content.record_mailboxes(zone, content.HAMLETS, ROOT / 'world/mailboxes.txt')
    # checks: the map must hold together as a map
    problems = []
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    if not (lost < open_cells.sum() * .01):
        problems.append(f'{lost} open cells are cut off from the spawn')

    for t in zone['slimes']:
        if not (d.floor[int(t['y']), int(t['x'])]):
            problems.append(f'spawn off land {t}')
        if not (seen[int(t['y']), int(t['x'])]):
            problems.append(f'unreachable spawn {t}')
    for n in zone['npcs']:
        if not n['id'].startswith(('mailbox', 'barrow')) or n['id'].startswith('mailbox_6_'):
            if not (seen[int(n['y']), int(n['x'])]):
                problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
    for p in zone['places']:
        if not (seen[int(p['y']), int(p['x'])]):
            problems.append(f"unreachable place {p['id']}")
    for p in zone['portals']:
        if not p.get('seam'):
            a = p['x'] - p.get('walk', (0, 0))[0] * 4, p['y'] - p.get('walk', (0, 0))[1] * 4
            if not (seen[int(a[1]), int(a[0])]):
                problems.append(f"gate cut off {p['id']}")
    bad = set()
    for road in ROADS + [r['points'] for r in zone['exitRoutes']]:
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                if not (d.floor[int(y), int(x)]):
                    problems.append(f'road leaves the land at {x:.0f},{y:.0f}')
                c = zone['city']
                inside = c['x0'] - 1 <= x <= c['x1'] + 1 and c['y0'] - 1 <= y <= c['y1'] + 3
                for fc in zone['camps']:
                    inside |= fc['x0'] - 1 <= x <= fc['x1'] + 1 and fc['y0'] - 1 <= y <= fc['y1'] + 3
                if not inside and solid[int(y), int(x)]:
                    bad.add((int(x), int(y)))
    if not (not bad):
        problems.append(f'something stands on the road at {sorted(bad)}')

    for a, b in zip(route, route[1:]):
        for k in range(21):
            x, y = a[0] + (b[0] - a[0]) * k / 20, a[1] + (b[1] - a[1]) * k / 20
            if not (not solid[int(y), int(x)]):
                problems.append(f'Eydis would walk into something at {x:.0f},{y:.0f}')
    artless = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')
    popping = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o['kind'] in artless and d.seam[int(o['y']), int(o['x'])] < 20]
    if not (not popping):
        problems.append(f'art-less objects within the camera reach of a seam pop in on crossing: {popping[:5]}')

    water = [o for o in objects if o['kind'] == 'water']
    seam_gap = min(d.seam[int(o['y']), int(o['x'])] - o['r'] for o in water)
    if not (seam_gap > 16):
        problems.append(f'water {seam_gap:.1f} tiles from a seam')

    if not (sum(d.short.values()) <= 12):
        problems.append(f'regions short of spawns: {d.short}')

    # the chokes: close the bridge and the north is cut off; close each ridge gap and what lies beyond it is cut off, in order
    def cut(x0, y0, x1, y1):
        s2 = solid.copy()
        s2[int(y0):int(y1) + 1, int(x0):int(x1) + 1] = True
        return d.reachable(s2, (int(SPAWN[0]), int(SPAWN[1])))
    plaza = zone['camps'][0]['entry']
    ring_south = (152, 92)
    east_beacon = (206, 150)
    storm_beacon = (120, 108)
    shut = cut(BRIDGE_X - 5, RIVER_Y - 4, BRIDGE_X + 5, RIVER_Y + 4)
    if shut[int(plaza['y']), int(plaza['x'])] or shut[ring_south[1], ring_south[0]]:
        problems.append('the river can be crossed somewhere besides the bridge')
    shut = cut(RIDGE1['gap'][0] - 3, 152, RIDGE1['gap'][1] + 3, 168)
    if shut[east_beacon[1], east_beacon[0]] or shut[ring_south[1], ring_south[0]] or not shut[int(plaza['y']), int(plaza['x'])]:
        problems.append('the first ridge has another way through, or shuts the fort off')
    shut = cut(RIDGE2['gap'][0] - 3, 120, RIDGE2['gap'][1] + 3, 136)
    if shut[storm_beacon[1], storm_beacon[0]] or shut[ring_south[1], ring_south[0]] or not shut[east_beacon[1], east_beacon[0]]:
        problems.append('the second ridge has another way through, or shuts the terrace off')
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), water=len(water), spawns=len(zone['slimes']), lost=lost,
                 land=int(d.floor.sum()), reachable=int(seen.sum()), ridges=d.ridges, seam_water=round(float(seam_gap), 1))
    if problems:
        if os.environ.get('WYRD_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    pal = {0: (74, 112, 66), 1: (150, 96, 50), 2: (70, 110, 60), 3: (120, 100, 120), 4: (140, 140, 140), 5: (60, 70, 52), 6: (196, 170, 70), 7: (50, 40, 40)}
    a = np.zeros((n, n, 3), np.uint8)
    a[:] = (20, 30, 50)
    for k, c in pal.items():
        a[(d.ground == k) & d.floor] = c
    a[d.floor & (d.ground == 0)] = (110, 90, 60)
    im = Image.fromarray(a).resize((n * scale, n * scale), Image.NEAREST)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(230, 200, 120), width=scale)
    col = {'water': (40, 100, 200), 'rock': (130, 130, 120), 'spire': (190, 200, 255), 'tree': (24, 80, 40), 'pine': (20, 60, 70), 'bush': (110, 150, 60), 'crag': (80, 70, 80),
           'lamp': (255, 230, 80), 'house': (200, 120, 60), 'chapel': (200, 120, 60), 'rampart': (150, 150, 160), 'tower': (150, 150, 160), 'bones': (240, 240, 230)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('lamp', 'post') else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'boar': (240, 120, 120), 'crow': (80, 80, 255), 'troll': (120, 220, 80), 'weaver': (230, 100, 230), 'ram': (255, 160, 40)}
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
    im.save(out)


def main():
    world = json.loads(MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][5], d, sys.argv[2])


if __name__ == '__main__':
    main()
