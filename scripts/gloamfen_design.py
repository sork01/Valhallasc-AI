#!/usr/bin/env python3
"""Gloamfen as an authored map (zone 3 of the shapes pilot): no filler land, the whole outline used.

Runs in `zone_shapes.py apply` right after Rimeveil's design, after the seams, the Skaldholm vault and the wall exist, so the outline, the
borders and every crossing stay exactly as they were. It replaces all loose scenery, every spawn and the trails with the plan below, traced
from the owner's painted atlas (client/assets/world-atlas-painted.png; tile = painted px * 2048/1758 - shape.T): the brown Old Quarter and
Lanternmere on the northern rise, the black stream that runs west under the town and bends into the Mere, the Mere itself (a big C of water
round a green isle), the winding brown road down the west bank, the lanterns scattered over the whole fen and the dark thickets of the south-east.

Fixed, never touched: Lanternmere and its people, the spawn point, the Ember Grave Cross and its sleeper, the Empty Seat circle, the
Halloween ritual (lantern, pad, Hollow Rider's sleeper), the Gloomroot Colossus, the seam portals, the vault, the wall, the void.

Water is drawn from this zone's own frame only. The neighbours (Rimeveil and Greenmeadow seams, Skaldholm's vault) do not draw `water`:
none stands within 17 tiles of a seam, and none east of x = 222, which is as far as the camera sees into Gloamfen from inside Skaldholm
(the view is 1600 x 900 px at 88 x 44 px a tile: 19 tiles from the wall, plus the cull margin).

    python3 scripts/gloamfen_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import gloamfen_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'

VAULT_X = 222.0     # no water at or east of this: Skaldholm's camera does not reach further, and it draws no water
FORD = 3.4          # half width of a crossing
GLOOMROOT = (231.8, 180.8)

# ---- the plan -------------------------------------------------------------------------------------------------------
FAR = (-9999, -9999)
REGIONS = {
    'commons':   dict(name='The Lanternmere Commons', seeds=[(178, 60), (150, 62), (206, 72), (178, 98), (150, 90)]),
    'quarter':   dict(name='The Old Quarter', seeds=[(112, 62), (128, 74), (98, 52), (118, 50)]),
    'westbank':  dict(name='The Singing Bank', seeds=[(42, 46), (60, 66), (34, 62), (72, 48), (82, 72)]),
    'pilgrim':   dict(name='The Pilgrim Plank', seeds=[(70, 104), (86, 124), (92, 148), (76, 120)]),
    'mouth':     dict(name='The Mere Mouth', seeds=[(126, 112), (118, 100), (136, 122), (112, 130)]),
    'shorewalk': dict(name='The Shorewalk', seeds=[(100, 178), (108, 200), (116, 222), (104, 160)]),
    'isle':      dict(name='Hydra Isle', seeds=[FAR]),
    'dikes':     dict(name='The Southern Dikes', seeds=[(150, 244), (125, 238), (176, 244), (190, 234)]),
    'flats':     dict(name='The Seaward Flats', seeds=[(150, 268), (155, 260)]),
    'garrison':  dict(name='The Drowned Garrison', seeds=[(205, 124), (226, 134), (194, 140), (216, 112), (214, 152), (200, 156)]),
    'reedmarch': dict(name='The Reedmarch', seeds=[(228, 86), (214, 70), (238, 102), (196, 62)]),
    'mirewood':  dict(name='The Gloomroot Mire', seeds=[(228, 184), (208, 194), (200, 208), (236, 168)]),
}

ROADS = [
    # the summit road: Lanternmere's north side up to the Rimeveil border
    [(178, 69), (176, 60), (172, 54)],
    # the Pilgrim Plank: west out of the town, past the Ember Grave Cross turning, to Reedhallow, then down the west bank
    [(154, 84), (138, 89), (118, 92), (96, 94), (82, 97), (70, 100)],
    [(118, 92), (126, 97), (133, 101)],
    [(70, 100), (78, 104), (88, 108), (92, 122), (91, 138), (93, 152), (98, 165), (101, 180), (106, 195), (114, 210), (122, 227), (128, 236), (142, 240)],
    # the north-west way and the Old Quarter ride
    [(70, 100), (60, 86), (54, 70), (52, 55), (58, 40)],
    [(154, 76), (140, 70), (125, 64), (110, 58)],
    # the Plank Road: the town's south side over the first ford, down the east shore of the Mere, then round its south end to the dikes
    [(178, 95), (178, 102), (178, 116), (178, 135), (178, 155), (179, 175), (182, 190), (188, 203), (194, 218), (193, 232), (183, 243), (170, 246), (152, 244), (142, 240)],
    # the causeway over the side channel to Hydra Isle
    [(178, 170), (163, 170), (150, 172), (146, 184)],
    # the reed road: the town's east side over the second ford to Garrison's Rest, and on to Skaldholm's vault
    [(202, 86), (210, 92), (210, 102), (211, 120), (212, 138), (214, 152)],
    [(178, 128), (190, 134), (205, 141), (214, 152)],
    [(214, 152), (226, 142), (238, 132), (248.4, 126.2)],
    # the Mire trail to the Gloomroot
    [(214, 152), (220, 165), (228, 176), (232, 181)],
    # to the Halloween lantern, and down the dry Culvert to the wall
    [(202, 86), (219, 95)],
    [(210, 98), (230, 100), (244, 100)],
    # the shore spur at the south tip
    [(142, 240), (148, 254), (152, 264), (156, 272)],
    [(102, 178), (112, 184)],
]

# the Mere (a thick line: x, y, half width), the side channel round Hydra Isle, and the stream that feeds it
MERE = [(141, 136, 7), (128, 148, 10), (122, 165, 11), (124, 186, 11), (133, 204, 11), (148, 216, 10), (168, 221, 10), (188, 219, 9), (196, 212, 7)]
CHANNEL = [(161, 104, 2.2), (166, 114, 2.4), (162, 124, 2.4), (166, 138, 2.4), (163, 152, 2.4), (167, 166, 2.4), (162, 180, 2.4), (158, 198, 2.6), (150, 211, 3)]
STREAM = [(221, 100, 2.3), (205, 100.5, 2.3), (190, 101, 2.3), (175, 101.5, 2.3), (160, 103, 2.4), (151, 108, 2.6), (146, 119, 3), (144, 130, 4.5), (141, 136, 7)]

# the painted lanterns (tile coordinates): will-o'-wisp posts, the glow the fen is named for
LAMPS = [(59, 61), (51, 67), (82, 74), (61, 81), (71, 82), (106, 115), (74, 123), (130, 127), (171, 140), (194, 114), (217, 117), (224, 126), (235, 119), (202, 124),
         (221, 157), (226, 154), (239, 163), (241, 171), (238, 180), (216, 171), (220, 180), (225, 180), (232, 185), (226, 188), (187, 179), (192, 182), (157, 186),
         (139, 177), (139, 190), (140, 202), (149, 204), (187, 198), (197, 202), (205, 240), (96, 156), (62, 108), (112, 100), (150, 96), (190, 110), (236, 92),
         (120, 70), (100, 70), (138, 58), (45, 80), (40, 100), (84, 150), (100, 222), (165, 238), (184, 236)]

HAMLETS = {
    'reedhallow': dict(name='Reedhallow', x=70, y=100, hw=14, hh=11),
    'dikewatch':  dict(name='Dikewatch', x=142, y=240, hw=10, hh=8),     # 20+ tiles from the Greenmeadow seam: houses and tents have no art the seam ghosts could draw
    'lastlight':  dict(name="Garrison's Rest", x=214, y=156, hw=14, hh=11),
}

# Hunting grounds: difficulty comes from which kind stands where (toad 15, croc 17, knight 18, hydra 20): toads by the town and the west, crocs along the water,
# knights in the east, hydras on the isle and in the mire.
SPAWNS = {
    'commons':   {'toad': 14},
    'quarter':   {'toad': 12, 'croc': 4},
    'westbank':  {'toad': 26, 'croc': 3},
    'pilgrim':   {'toad': 14, 'croc': 10},
    'mouth':     {'croc': 14, 'toad': 4},
    'shorewalk': {'croc': 14, 'toad': 6},
    'isle':      {'hydra': 10, 'knight': 4},
    'dikes':     {'croc': 16, 'toad': 3},
    'flats':     {'croc': 4, 'knight': 2},
    'garrison':  {'knight': 30, 'croc': 4},
    'reedmarch': {'toad': 9, 'croc': 7},
    'mirewood':  {'knight': 12, 'hydra': 9},
}

R = {'tree': .42, 'bush': .30, 'rock': .40, 'spire': .55, 'thicket': 1.3, 'lamp': .18, 'water': 2.3, 'post': .45, 'bones': 0, 'brazier': .4, 'barrels': 0}
GROUND = {'peat': 1, 'mud': 2, 'moss': 3, 'reed': 4, 'clay': 5, 'shingle': 6, 'bog': 7, 'bed': 8}


def thick_mask(d, pts, wob=.18, scale=.08):
    """Cells within the half width of the polyline `pts` (x, y, half width), the width interpolated along it and the edge wobbled by noise."""
    best = np.full((d.n, d.n), 1e9)
    for (ax, ay, aw), (bx, by, bw) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        t = np.clip(((d.xs - ax) * dx + (d.ys - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
        dist = np.hypot(d.xs - ax - t * dx, d.ys - ay - t * dy)
        best = np.minimum(best, dist - (aw + (bw - aw) * t))
    return best < (fbm(d.noise, d.xs, d.ys, scale) - .5) * wob * 14


class Gloamfen(Designer):
    TAG, SEED = 'gloamfen_design_v1', 20261109

    def __init__(self, world):
        self._exits = [r['points'] for r in world['exitRoutes']]     # the painted exit marking is a road too
        super().__init__(world)

    def plan(self):
        return REGIONS, ROADS + self._exits, R

    def scatter(self, kinds, count, where, gap=.65, road=3.0):
        return super().scatter(kinds, int(count * .8), where, gap, road)

    # ---- the regions: Hydra Isle is the land the channel and the Mere enclose --------------------------------------------
    def make_regions(self):
        out = super().make_regions()
        isle = (self.xs > 128) & (self.xs < 163) & (self.ys > 150) & (self.ys < 212) & (self.ys > 150 + (self.xs - 128) * -.1)
        out[isle] = list(REGIONS).index('isle')
        return out

    # ---- water: the Mere, the channel, the stream, the pools ---------------------------------------------------------------
    def water_at(self, x, y, r):
        self.add('water', x, y, r=round(float(r), 2), solid=False)
        self.grid.add(round(float(x), 2), round(float(y), 2), r)

    def water_ok(self, x, y, r):
        ix, iy = int(x), int(y)
        if not (0 <= ix < self.n and 0 <= iy < self.n) or not self.floor[iy, ix] or not self.inner[iy, ix]:
            return False
        if x + r >= VAULT_X:
            return False
        if any(math.hypot(px - x, py - y) < r + rad for px, py, rad in self.pins):
            return False
        return bool(self.seam[iy, ix] - r > 17 and not self.blocked[iy, ix])

    def fill_water(self, mask, r=2.3, step=2.9, ford=True):
        """Hex-packed solid water circles over `mask`; a ford (no circle) wherever a road runs within FORD of the circle's edge."""
        n = placed = 0
        todo = []
        y, row = 3.0, 0
        while y < self.n - 2:
            x = 3.0 + (step / 2 if row % 2 else 0)
            while x < self.n - 2:
                if mask[int(y), int(x)] and self.water_ok(x, y, r):
                    if ford and self.road[int(y), int(x)] < FORD + r:
                        n += 1
                    else:
                        self.water_at(x, y, r)
                        self.wcircles.append((x, y, r))
                        todo.append((x, y, r))
                        placed += 1
                x += step
            y += step * .866
            row += 1
        for x, y, r in todo:                       # block only after the whole body is laid, or a circle would crowd out its neighbour
            self.block_disc(x, y, r + 1.4)
        return placed, n

    def hole(self, x, y, r):
        self.water_at(x, y, r)
        self.block_disc(x, y, r + 1.4)
        self.wcircles.append((x, y, r))

    def pools(self, where, count, rmin=1.5, rmax=3.0, gap=7):
        pts = np.argwhere(where & self.inner & ~self.blocked & (self.road > 6) & (self.seam > 19) & (self.xs < VAULT_X - 4))
        placed = 0
        for _ in range(count * 40):
            if placed == count or not len(pts):
                break
            j, i = pts[self.rng.randrange(len(pts))]
            x, y = i + self.rng.random(), j + self.rng.random()
            r = self.rng.uniform(rmin, rmax)
            if self.water_ok(x, y, r) and self.grid.free(x, y, r, gap):
                self.hole(x, y, r)
                placed += 1
        return placed

    def tarn(self, cx, cy, rx, ry):
        step = 2.6
        y = cy - ry
        row = 0
        while y <= cy + ry:
            x = cx - rx + (step / 2 if row % 2 else 0)
            while x <= cx + rx:
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.05 and self.water_ok(x, y, 2.0):
                    self.water_at(x, y, 2.0)
                    self.wcircles.append((x, y, 2.0))
                x += step
            y += step * .866
            row += 1
        self.block_disc(cx, cy, max(rx, ry) + 2.2)

    def lamp(self, x, y):
        """A lantern post at the painted spot, or the nearest clear ground within 6 tiles."""
        best = None
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                i, j = int(x) + dx, int(y) + dy
                if not (0 <= i < self.n and 0 <= j < self.n) or not self.inner[j, i] or self.blocked[j, i] or self.road[j, i] < 1.6 or self.wdist[j, i] < 2.2:
                    continue
                if self.seam[j, i] < 22:       # a lamp is art-less to the seam ghosts: keep it out of the camera's reach of every seam, or it pops in on crossing
                    continue
                d = math.hypot(dx, dy)
                if (best is None or d < best[0]) and self.grid.free(i + .5, j + .5, .18, .9):
                    best = (d, i + .5, j + .5)
        if best:
            self.add('lamp', best[1], best[2], r=.18)

    def ring(self, centre, radius, n, kind, **extra):
        for k in range(n):
            a = k / n * math.tau + .3
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if self.road[int(y), int(x)] > 2.4 and self.floor[int(y), int(x)]:
                self.add(kind, x, y, **extra)

    def build(self):
        w = self.w
        city = w['city']
        self.ground = np.zeros((self.n, self.n), np.uint8)
        self.block(city['x0'] - 3, city['y0'] - 3, city['x1'] + 3, city['y1'] + 3)
        kept = []
        for o in w['objects']:
            inside = city['x0'] - 1 <= o['x'] <= city['x1'] + 1 and city['y0'] - 1 <= o['y'] <= city['y1'] + 2.5
            if o['kind'] in ('void', 'rampart', 'tower') or inside:
                kept.append(o)
                if o['kind'] != 'void' and o['r'] + o.get('width', 0) > 0:
                    self.grid.add(o['x'], o['y'], max(o['r'], o.get('width', 0) / 2))
        for p in w['places'] + w['crosses']:
            self.block_disc(p['x'], p['y'], 5)
        for p in w['portals']:
            if not p.get('seam'):
                self.block_disc(p['x'], p['y'], 9)
                self.block_disc(p['x'] - p.get('walk', (0, 0))[0] * 8, p['y'] - p.get('walk', (0, 0))[1] * 8, 9)
        self.block_disc(w['spawn']['x'], w['spawn']['y'], 5)
        rit = w['halloweenRitual']
        self.block_disc(rit['x'], rit['y'], rit['radius'] + 5)
        self.block_disc(*rit['lantern'], 6)
        self.blocked |= self.seam < 2.5
        self.pins = []     # points no water may cover or crowd: elites, sleepers, places
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 7)
            self.pins.append((x, y, 7))
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)
            self.pins.append((x, y, 2.5))
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3)
            self.pins.append((p['x'], p['y'], p['r'] + 1))
        for p in w['places'] + w['crosses']:
            self.pins.append((p['x'], p['y'], 4))
        for h in HAMLETS.values():
            assert self.floor[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
            self.pins.append((h['x'], h['y'], max(h['hw'], h['hh']) + 3))

        self.wcircles = []
        self.short = {}
        # the three waters first: everything else keeps away from them
        mere = thick_mask(self, MERE)
        chan = thick_mask(self, CHANNEL, wob=.05)
        stream = thick_mask(self, STREAM, wob=.05)
        self.mere_cells = mere
        self.water_counts = dict(mere=self.fill_water(mere), channel=self.fill_water(chan, r=2.0, step=2.5), stream=self.fill_water(stream, r=2.0, step=2.5))
        # bog pools and tarns over the rest of the fen, thickest on the west bank
        self.tarn(70, 70, 7, 4)
        self.tarn(88, 50, 6, 4)
        self.tarn(112, 130, 5, 3.5)
        m = self.mask
        self.pool_count = 0
        for name, n in (('westbank', 18), ('quarter', 6), ('pilgrim', 10), ('mouth', 6), ('shorewalk', 6), ('dikes', 6), ('flats', 4), ('garrison', 6), ('reedmarch', 6), ('mirewood', 8), ('commons', 5), ('isle', 5)):
            self.pool_count += self.pools(m(name), n)
        self.wdist = np.full((self.n, self.n), 1e9)
        for o in self.objects:
            if o['kind'] == 'water':
                r = int(o['r'] + 12)
                y0, y1, x0, x1 = max(int(o['y']) - r, 0), int(o['y']) + r, max(int(o['x']) - r, 0), int(o['x']) + r
                sub = np.hypot(self.xs[y0:y1, x0:x1] - o['x'], self.ys[y0:y1, x0:x1] - o['y']) - o['r']
                self.wdist[y0:y1, x0:x1] = np.minimum(self.wdist[y0:y1, x0:x1], sub)
        content.dress(self, HAMLETS)
        self.lay_ground()
        self.lay_regions()
        for x, y in LAMPS:
            self.lamp(x, y)
        self.clear_glades()
        return kept + self.objects

    def clear_glades(self):
        """Tall scenery (willows, thickets, columns) standing in front of an elite hides it (the owner's first look at Bellowmaw: half behind willows): a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        self.objects[:] = [o for o in self.objects if not (o['kind'] in ('tree', 'thicket', 'spire') and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]
    def lay_ground(self):
        """Ground classes beside plain fen grass. None within 16-30 tiles of a seam: the other side blends toward plain Gloamfen ground."""
        G, g = GROUND, self.ground
        far = self.seam > 16 + fbm(self.noise, self.xs, self.ys, .09) * 14
        for name, cls in (('commons', 'peat'), ('quarter', 'clay'), ('westbank', 'moss'), ('pilgrim', 'peat'), ('mouth', 'reed'), ('shorewalk', 'shingle'),
                          ('isle', 'moss'), ('dikes', 'reed'), ('flats', 'shingle'), ('garrison', 'clay'), ('reedmarch', 'reed'), ('mirewood', 'bog')):
            g[self.mask(name) & far] = G[cls]
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 5
        g[self.floor & far & (self.wdist + rough * .4 < 2.4)] = G['mud']
        # the dry Culvert: the stream's old bed east of the last water, dark mud running to the wall
        bed = (abs(self.ys - 100.2) < 3.2 + (fbm(self.noise, self.xs, self.ys, .2) - .5) * 2) & (self.xs > 218) & (self.xs < 250) & self.floor
        g[bed & (self.seam > 12)] = G['bed']

    def lay_regions(self):
        dense = fbm(self.noise, self.xs + 200, self.ys + 300, .05)
        m = self.mask
        sc = self.scatter

        # The Lanternmere Commons: peat flats under the town's lamps, a few willows, reeds along the ditches.
        sc(['tree', 'bush', 'bush'], 140, m('commons') & (dense > .45), gap=1.4)
        sc(['rock', 'bush'], 160, m('commons'), gap=1.4)

        # The Old Quarter: what is left of the first Lanternmere: rows of columns, tumbled stone and brambles on the brown clay.
        for k, (x, y) in enumerate(((110, 66), (122, 58), (132, 70), (100, 58), (140, 62))):
            self.block_disc(x, y, 5)
            self.ring((x, y), 3.6, 5 + k % 3, 'spire')
            self.ring((x, y), 5.4, 5, 'rock')
        sc(['rock', 'rock', 'thicket', 'bush'], 280, m('quarter'), gap=1.2)
        sc(['spire'], 40, m('quarter'), gap=5)
        sc(['tree'], 40, m('quarter') & (dense > .5), gap=2.5)

        # The Singing Bank: the toads' chorus ground: dense willows and reed beds round the tarns.
        sc(['tree', 'tree', 'bush', 'tree'], 520, m('westbank') & (dense > .38), gap=1.0)
        sc(['bush', 'bush', 'rock'], 480, m('westbank'), gap=.9)
        sc(['thicket'], 40, m('westbank') & (dense > .55), gap=4)

        # The Pilgrim Plank: peat, birch-pale willows, boundary stones along the road.
        sc(['tree', 'bush'], 300, m('pilgrim') & (dense > .42), gap=1.2)
        sc(['rock', 'bush', 'spire'], 300, m('pilgrim'), gap=1.3)

        # The Mere Mouth: reeds either side of the stream, the dead standing in the shallows round the Grave Cross.
        sc(['bush', 'bush', 'tree'], 260, m('mouth'), gap=1.0)
        sc(['rock', 'spire'], 90, m('mouth'), gap=2.5)

        # The Shorewalk: shingle and driftwood between the coast and the Mere.
        sc(['rock', 'rock', 'bush', 'tree'], 360, m('shorewalk'), gap=1.2)
        sc(['spire'], 20, m('shorewalk'), gap=6)

        # Hydra Isle: the heads' lair: mossy ground, big willows, thicket walls round the nest.
        nest = (147, 182)
        self.block_disc(*nest, 8)
        self.ring(nest, 7.5, 12, 'thicket', r=1.3)
        sc(['tree', 'tree', 'bush'], 240, m('isle') & (dense > .38), gap=1.1)
        sc(['rock', 'bush', 'spire'], 260, m('isle'), gap=1.4)

        # The Southern Dikes: low stone dikes along the south shore, one broken through; reeds in their lee.
        self.dike(124, 236, 192, 238, gaps=(150, 176))
        sc(['bush', 'bush', 'rock', 'tree'], 360, m('dikes'), gap=1.1)
        sc(['spire'], 20, m('dikes'), gap=6)

        # The Seaward Flats: bare shingle, a few wind-twisted willows, the wreck of the ferry on the strand.
        wreck = (150, 270)
        self.block_disc(*wreck, 6)
        for dx, dy in ((-3, -1), (-1, 1), (1, -2), (3, 0), (4, 2), (-4, 2)):
            self.add('barrels', wreck[0] + dx, wreck[1] + dy, r=0, width=.6, depth=.6, color='', label='')
        self.ring(wreck, 5.5, 8, 'rock')
        sc(['rock', 'rock', 'bush'], 140, m('flats'), gap=1.2)
        sc(['tree'], 20, m('flats') & (dense > .5), gap=3)

        # The Drowned Garrison: the old fort's outline in tumbled stone, its gate toward the stream, columns standing in the yard.
        self.fort(206, 126, 34, 22)
        sc(['rock', 'bush', 'thicket', 'spire'], 300, m('garrison'), gap=1.3)
        sc(['tree'], 90, m('garrison') & (dense > .5), gap=2)

        # The Reedmarch: reeds as far as the eye goes, the ritual pad kept clear, the dry Culvert's stepping stones.
        sc(['bush', 'bush', 'bush', 'tree'], 480, m('reedmarch'), gap=.9)
        sc(['rock', 'thicket'], 120, m('reedmarch'), gap=2.4)
        for x in range(226, 240, 3):                      # none within 8 tiles of the wall: its strip is the city's own, and the city's frame draws no ghost there
            self.add('rock', x + .5, 97.2 + (x % 2) * 5.8, r=.4)

        # The Gloomroot Mire: black thickets and dead willows round the Colossus, as the painting darkens in the south-east.
        self.block_disc(*GLOOMROOT, 9)
        self.ring(GLOOMROOT, 14, 16, 'thicket', r=1.3)
        sc(['thicket', 'thicket', 'tree', 'bush'], 520, m('mirewood') & (dense > .35), gap=1.0)
        sc(['rock', 'bush', 'spire'], 300, m('mirewood'), gap=1.3)

    def dike(self, x0, y0, x1, y1, gaps=()):
        """A low dike of stones with breaks at `gaps` (x values)."""
        n = int(math.dist((x0, y0), (x1, y1)) / 1.5)
        for s in range(n + 1):
            x = x0 + (x1 - x0) * s / n
            y = y0 + (y1 - y0) * s / n + math.sin(s * .5) * .6
            if any(abs(x - g) < 3 for g in gaps) or self.road[int(y), int(x)] < 3.4:
                continue
            if self.inner[int(y), int(x)] and not self.blocked[int(y), int(x)] and self.wdist[int(y), int(x)] > 2.5 and self.grid.free(x, y, .4, .3):
                self.add('rock', x, y, r=.4)

    def fort(self, cx, cy, w, h):
        """The Garrison's outline: stone along its four sides, broken at the gates (north towards the stream, south towards the Rest), corner columns."""
        x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        for pts, gaps in (([(x0, y0), (x1, y0)], [(cx, y0)]), ([(x1, y0), (x1, y1)], []), ([(x1, y1), (x0, y1)], [(cx - 2, y1)]), ([(x0, y1), (x0, y0)], [])):
            (ax, ay), (bx, by) = pts
            n = int(math.dist((ax, ay), (bx, by)) / 1.6)
            for s in range(n + 1):
                x, y = ax + (bx - ax) * s / n, ay + (by - ay) * s / n
                if any(math.dist((x, y), g) < 4.2 for g in gaps) or self.road[int(y), int(x)] < 3.4 or self.wdist[int(y), int(x)] < 3:
                    continue
                if self.inner[int(y), int(x)] and not self.blocked[int(y), int(x)] and self.grid.free(x, y, .4, .3) and self.rng.random() < .86:
                    self.add('rock', x, y, r=.4)
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            if self.inner[int(y), int(x)] and self.road[int(y), int(x)] > 2.4 and self.wdist[int(y), int(x)] > 3:
                self.add('spire', x, y, r=.55)

    # ---- spawns -----------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        tags = {t for *_, t in content.AMBUSH}
        kept = [s for s in w['slimes'] if s.get('ambush') and s['ambush'] not in tags]
        out = list(kept) + [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in HAMLETS.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
        city = w['city']
        keep[city['y0'] - 8:city['y1'] + 9, city['x0'] - 8:city['x1'] + 9] = True
        solid = Grid()
        for o in self.objects:
            solid.add(o['x'], o['y'], max(o['r'], (o.get('width', 0) + o.get('depth', 0)) / 4))
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
                x, y = round(i + rng.random() * .98, 2), round(j + rng.random() * .98, 2)     # never rounds up into the next cell, which may be shut in
                if any(math.hypot(x - s['x'], y - s['y']) < sep for s in out) or not solid.free(x, y, .6, .15):
                    continue
                out.append({'x': x, 'y': y, 'kind': pool[placed], 'layout': self.TAG})
                placed += 1
            if placed < len(pool):
                self.short[name] = len(pool) - placed
        # ordinary enemies first: code and tests take the zone's first spawn as a plain enemy
        ordinary = [t for t in out if t.get('layout') == self.TAG]
        ordinary.sort(key=lambda t: t['kind'] != 'toad')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


def design(world, write=False):
    zone = world['zones'][2]
    d = Gloamfen(zone)
    objects = d.build()
    solid = d.solid_mask(objects)
    s = zone['spawn']
    seen = d.reachable(solid, (int(s['x']), int(s['y'])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    zone['objects'] = objects
    zone['paths'] = [[list(p) for p in road] for road in ROADS]
    zone['atlasPaths'] = []
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(zone, HAMLETS)
    if write:
        content.record_mailboxes(zone, HAMLETS, ROOT / 'world/mailboxes.txt')
    # checks: the map must hold together as a map
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    assert lost < open_cells.sum() * .01, f'{lost} open cells are cut off from the spawn'
    for t in zone['slimes']:
        assert d.floor[int(t['y']), int(t['x'])], f'spawn off land {t}'
        assert seen[int(t['y']), int(t['x'])], f'unreachable spawn {t}'
    prefix = ('fen_rh_', 'fen_dk_', 'fen_gr_', 'travel_reedhallow', 'travel_dikewatch', 'travel_lastlight', 'mailbox_3_reedhallow', 'mailbox_3_dikewatch', 'mailbox_3_lastlight')
    for n in zone['npcs']:
        if n['id'].startswith(prefix):
            assert seen[int(n['y']), int(n['x'])], f"unreachable npc {n['id']}"
    for p in zone['places']:
        assert seen[int(p['y']), int(p['x'])], f"unreachable place {p['id']}"
    for p in zone['portals']:
        if not p.get('seam'):
            a = p['x'] - p.get('walk', (0, 0))[0] * 4, p['y'] - p.get('walk', (0, 0))[1] * 4
            assert seen[int(a[1]), int(a[0])], f"gate cut off {p['id']}"
    bad = set()
    for road in ROADS + [r['points'] for r in zone['exitRoutes']]:
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                assert d.floor[int(y), int(x)], f'road leaves the land at {x:.0f},{y:.0f}'
                c = zone['city']
                inside = c['x0'] - 1 <= x <= c['x1'] + 1 and c['y0'] - 1 <= y <= c['y1'] + 3
                if not inside and solid[int(y), int(x)]:
                    bad.add((int(x), int(y)))
    assert not bad, f'something stands on the road at {sorted(bad)}'
    # the escort's walk is clear, leg by leg
    per = next(n for n in zone['npcs'] if n['id'] == 'fen_gr_per')
    route = per['escort']['route']
    for a, b in zip(route, route[1:]):
        for k in range(21):
            x, y = a[0] + (b[0] - a[0]) * k / 20, a[1] + (b[1] - a[1]) * k / 20
            assert not solid[int(y), int(x)], f'Per would walk into something at {x:.0f},{y:.0f}'
    artless = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')
    popping = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o['kind'] in artless and d.seam[int(o['y']), int(o['x'])] < 20 and o.get('layout') == d.TAG]
    assert not popping, f'art-less objects within the camera reach of a seam pop in on crossing: {popping[:5]}'
    water = [o for o in objects if o['kind'] == 'water']
    seam_gap = min(d.seam[int(o['y']), int(o['x'])] - o['r'] for o in water)
    vault_gap = min(VAULT_X - o['x'] - o['r'] for o in water)
    assert seam_gap > 16, f'water {seam_gap:.1f} tiles from a seam: the other side would not draw it'
    assert vault_gap > 0, f'water reaches {-vault_gap:.1f} tiles into the vault view'
    assert sum(d.short.values()) <= 14, f'regions short of spawns: {d.short}'
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), water=len(water), waters=d.water_counts, pools=d.pool_count, spawns=len(zone['slimes']),
                 lost=lost, land=int(d.floor.sum()), reachable=int(seen.sum()), lamps=len([o for o in objects if o['kind'] == 'lamp']), seam_water=round(float(seam_gap), 1),
                 vault_water=round(float(vault_gap), 1))
    return d, stats


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    pal = {0: (74, 112, 66), 1: (92, 86, 58), 2: (60, 70, 52), 3: (96, 148, 78), 4: (150, 160, 80), 5: (150, 118, 80), 6: (190, 180, 140), 7: (40, 56, 56), 8: (36, 40, 44)}
    a = np.zeros((n, n, 3), np.uint8)
    a[:] = (20, 30, 50)
    for k, c in pal.items():
        a[(d.ground == k) & d.floor] = c
    im = Image.fromarray(a).resize((n * scale, n * scale), Image.NEAREST)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(200, 160, 100), width=scale)
    col = {'water': (40, 100, 200), 'rock': (130, 130, 120), 'spire': (190, 200, 180), 'tree': (24, 80, 40), 'bush': (110, 150, 60), 'thicket': (110, 40, 90), 'lamp': (255, 230, 80),
           'house': (200, 120, 60), 'chapel': (200, 120, 60)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] == 'lamp' else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'toad': (120, 220, 80), 'croc': (255, 150, 60), 'knight': (200, 200, 220), 'hydra': (190, 60, 220)}
    for s in zone['slimes']:
        c = kc.get(s['kind'], (255, 60, 60))
        g.rectangle([s['x'] * scale - 2, s['y'] * scale - 2, s['x'] * scale + 2, s['y'] * scale + 2], fill=c, outline=(0, 0, 0))
    c = zone['city']
    g.rectangle([c['x0'] * scale, c['y0'] * scale, c['x1'] * scale, c['y1'] * scale], outline=(255, 255, 0), width=2)
    for h in HAMLETS.values():
        g.rectangle([(h['x'] - h['hw']) * scale, (h['y'] - h['hh']) * scale, (h['x'] + h['hw']) * scale, (h['y'] + h['hh']) * scale], outline=(255, 120, 0), width=2)
        g.text((h['x'] * scale - 20, h['y'] * scale), h['name'], fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    for r in REGIONS.values():
        sx, sy = r['seeds'][0]
        if sx > 0:
            g.text((sx * scale, sy * scale - 14), r['name'], fill=(240, 240, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    g.text((140 * scale, 175 * scale), 'Hydra Isle', fill=(240, 240, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    for p in content.PLACES:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(120, 255, 160), stroke_width=1, stroke_fill=(0, 0, 0))
    g.line([(VAULT_X * scale, 0), (VAULT_X * scale, n * scale)], fill=(255, 0, 255), width=1)
    im.save(out)


def main():
    world = json.loads(MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][2], d, sys.argv[2])


if __name__ == '__main__':
    main()
