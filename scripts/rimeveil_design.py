#!/usr/bin/env python3
"""Rimeveil Glacier as an authored map (zone 2 of the shapes pilot): no filler land, the whole outline used.

Runs in `zone_shapes.py apply` after the seams, the Skaldholm vault and the wall exist, so the outline, the borders and every crossing stay
exactly as they were. It replaces all loose scenery, every spawn and the trails with the plan below, traced from the owner's painted atlas
(client/assets/world-atlas-painted.png; tile = painted px * 2048/1758 - shape.T): four rings of blue ice round a heart, the grey spine road
down the middle with a ford at every ring, the snow-capped peaks, and the dark ice-holes scattered over the whole glacier.

Fixed, never touched: Rimeward Camp and its people, the spawn point, the Ember Grave Cross and its sleeper, the Empty Seat circle, the
seasonal summoning pad (293,225), the seam portals, the Wyrdwood gate, the vault, the wall, the void.

Water (the rings, the holes) is drawn from this zone's own frame only: the neighbours (the Crags and Gloamfen seams, Skaldholm's vault)
do not draw `water` as scenery, so none stands within 16 tiles of a seam or inside the vault's land region.

    python3 scripts/rimeveil_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import rimeveil_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'

CENTRE = (167.0, 149.0)
# The four rings of the painting, outermost last: (x radius, y radius, half width, gaps as (centre degrees, half span); 0 = east, 90 = south).
RINGS = [
    (40, 31, 2.0, [(0, 40)]),
    (65, 53, 2.2, [(205, 14)]),
    (90, 70, 2.4, [(0, 16)]),
    (121, 80, 2.6, [(232, 10)]),
]
FORD = 4.2          # half width of a crossing

# ---- the plan -------------------------------------------------------------------------------------------------------
# The four ring bands are decided by the normalised radius (`band`); everything outside the outer ring by the nearest seed.
FAR = (-9999, -9999)
REGIONS = {
    'heart':     dict(name='The Heart of the Glacier', seeds=[FAR]),
    'whorl':     dict(name='The Inner Whorl', seeds=[FAR]),
    'blue':      dict(name='The Bluewater Walk', seeds=[FAR]),
    'rimewalk':  dict(name='The Rimewalk', seeds=[FAR]),
    'shelf':     dict(name='The Rimeward Shelf', seeds=[(245, 222), (280, 232), (212, 238), (292, 195)]),
    'drifts':    dict(name='The Southern Drifts', seeds=[(120, 262), (160, 262), (200, 266), (75, 250), (45, 236)]),
    'strand':    dict(name='The Shearwind Strand', seeds=[(22, 175), (18, 205), (24, 148), (30, 222)]),
    'fells':     dict(name='The Whalebone Fells', seeds=[(45, 100), (28, 75), (60, 62), (22, 118)]),
    'wyrdgate':  dict(name='The Wyrdgate Reach', seeds=[(100, 60), (150, 60), (205, 64), (240, 72)]),
    'horn':      dict(name='The Hornspire Ridge', seeds=[(285, 98), (300, 120), (265, 82)]),
    'whitefall': dict(name='The Whitefall', seeds=[(302, 160), (305, 195), (290, 225), (298, 140)]),
}
BAND = {'heart': (0, .42), 'whorl': (.42, .70), 'blue': (.70, .87), 'rimewalk': (.87, 1.04)}   # normalised to the outer ring

ROADS = [
    # the spine of the painting: the Wyrdwood gate straight down through every ring (a ford at each) to the south road
    [(167.5, 61.5), (167.5, 79.5), (168, 100), (168, 125), (167, 149), (168, 175), (168, 205), (168, 240)],
    # the south road: Rimeward's west gate, Driftwatch, the strand, up to Shearwind
    [(233, 240), (205, 244), (168, 240), (140, 246), (120, 250), (96, 252), (70, 246), (52, 232), (42, 212), (38, 190), (36, 172)],
    # up from the camp to the Ember Grave Cross, then the east shoulder road to Peakrest
    [(245, 248), (245, 237), (245, 225), (245, 219.5)],
    [(245, 219.5), (268, 208), (292, 190), (302, 165), (300, 140), (292, 118), (285, 98)],
    # the peak road: Peakrest west over the outer ring, down through the rings to the Heart
    [(285, 98), (271, 99), (262, 99), (250, 103), (236, 112), (222, 124), (208, 134), (190, 142), (167, 149)],
    # the north road: Wyrdgate east to Peakrest
    [(167.5, 61.5), (185, 62), (205, 64), (232, 71), (262, 82), (285, 98)],
    # the coast road: Shearwind north to the Wyrdgate
    [(36, 172), (34, 150), (32, 128), (36, 104), (52, 82), (88, 65), (130, 62), (167.5, 61.5)],
    # the camp's way out to Skaldholm's vault
    [(259.5, 246.5), (262.5, 246.5), (269.5, 247.5), (269, 254.5)],
    # spurs to the Fenward Gap and the Whale Cairn
    [(196, 243), (186, 262)],
    [(38, 206), (14, 206)],
]

# Peaks of the painting (foot of the mountain), with their size.
PEAKS = [(33, 91, 6), (67, 132, 5.5), (79, 161, 4.5), (95, 161, 4.5), (33, 180, 5), (60, 203, 5), (137, 223, 5), (155, 232, 6), (118, 262, 5), (238, 95, 5.5),
         (296, 82, 5), (269, 118, 5.5), (246, 132, 5), (288, 161, 5.5), (246, 180, 5), (263, 182, 4.5), (232, 203, 4.5), (281, 207, 5.5), (306, 207, 4.5), (13, 236, 4),
         (48, 244, 4), (24, 62, 4.5), (110, 58, 4), (205, 70, 4.5), (60, 120, 4.5), (90, 215, 4.5), (215, 232, 5), (135, 120, 4)]

HAMLETS = {
    'driftwatch': dict(name='Driftwatch', x=120, y=250, hw=15, hh=10),
    'shearwind':  dict(name='Shearwind Post', x=36, y=172, hw=14, hh=11),
    'peakrest':   dict(name='Peakrest', x=285, y=98, hw=14, hh=11),
}

# Hunting grounds: difficulty comes from which kind stands where (crab 10, wolf 12, yeti 13, wyrm 15). It climbs inward and north.
SPAWNS = {
    'shelf':     {'crab': 28, 'wolf': 4},
    'drifts':    {'crab': 32, 'wolf': 8},
    'strand':    {'wolf': 18, 'crab': 8},
    'fells':     {'wolf': 22, 'yeti': 6},
    'wyrdgate':  {'wolf': 6, 'yeti': 5},
    'horn':      {'yeti': 11, 'wyrm': 4},
    'whitefall': {'yeti': 11, 'wolf': 8},
    'rimewalk':  {'wolf': 30, 'yeti': 12},
    'blue':      {'yeti': 28, 'wolf': 8},
    'whorl':     {'yeti': 12, 'wyrm': 14},
    'heart':     {'wyrm': 14},
}

R = {'tree': .42, 'bush': .30, 'rock': .40, 'spire': .55, 'ice': 1.35, 'rime_peak': 5, 'cairn_boulder': 1.3, 'cairn_pebble': 0, 'bones': 0, 'brazier': .4,
     'cairn_signal': 1.1, 'water': 2.3}
GROUND = {'packed': 1, 'blue': 2, 'hoar': 3, 'moraine': 4, 'powder': 5, 'bank': 6, 'crevasse': 7}


class Rimeveil(Designer):
    TAG, SEED = 'rimeveil_design_v1', 20261108

    def plan(self):
        return REGIONS, ROADS, R

    def scatter(self, kinds, count, where, gap=.65, road=3.3):
        # the zone is big: a thinner hand keeps the object list a manageable size; the lane is wide enough for the biggest block (r 1.35)
        return super().scatter(kinds, int(count * .7), where, gap, road)

    # ---- the regions: ring bands round the Heart, nearest seed outside -------------------------------------------------
    def band(self):
        """Normalised radius round the Heart, as the outer ring sees it (1.0 = the outer ring's own line)."""
        rx, ry = RINGS[-1][0], RINGS[-1][1]
        wob = 1 + (fbm(self.noise, self.xs, self.ys, .05) - .5) * .06
        return np.hypot((self.xs - CENTRE[0]) / rx, (self.ys - CENTRE[1]) / ry) * wob

    def make_regions(self):
        out = super().make_regions()
        u = self.band()
        names = list(REGIONS)
        for name, (lo, hi) in BAND.items():
            out[(u >= lo) & (u < hi)] = names.index(name)
        return out

    # ---- water: the rings, the holes ---------------------------------------------------------------------------------------
    def water_at(self, x, y, r):
        self.add('water', x, y, r=round(float(r), 2), solid=False)
        self.grid.add(round(float(x), 2), round(float(y), 2), r)

    def water_ok(self, x, y, r):
        ix, iy = int(x), int(y)
        if not (0 <= ix < self.n and 0 <= iy < self.n) or not self.floor[iy, ix] or not self.inner[iy, ix]:
            return False
        if any(math.hypot(px - x, py - y) < r + rad for px, py, rad in self.pins):
            return False
        return bool(self.seam[iy, ix] - r > 17 and self.vdist[iy, ix] - r > 4 and not self.blocked[iy, ix])

    def ring_points(self, rx, ry, gaps):
        pts, last = [], None
        for k in range(1441):
            deg = k * .25
            if any(min(abs(deg - c) % 360, 360 - abs(deg - c) % 360) < h for c, h in gaps):
                last = None
                pts.append(None)
                continue
            a = math.radians(deg)
            p = (CENTRE[0] + rx * math.cos(a), CENTRE[1] + ry * math.sin(a))
            if last is None or math.dist(p, last) >= 1.4:
                pts.append(p)
                last = p
        return pts

    def ring_water(self, rx, ry, half, gaps):
        """An ice ring as overlapping water circles, with a ford wherever a road crosses and a natural gap or two; ends taper."""
        pts = self.ring_points(rx, ry, gaps)
        runs, cur = [], []
        fords, along = 0, 0
        for p in pts:
            if p is None:
                if cur:
                    runs.append(cur)
                cur = []
                continue
            wob = 1 + (fbm(self.noise, p[0], p[1], .09) - .5) * .5
            r = half * wob
            ix, iy = int(p[1]), int(p[0])
            if 0 <= ix < self.n and 0 <= iy < self.n and self.road[ix, iy] < FORD + r:
                fords += 1
                along += 1
                assert along < 16, f'a road runs along the ring at {p[0]:.0f},{p[1]:.0f}'
                if cur:
                    runs.append(cur)
                cur = []
                continue
            along = 0
            if not self.water_ok(p[0], p[1], r):
                if cur:
                    runs.append(cur)
                cur = []
                continue
            cur.append((p[0], p[1], r))
        if cur:
            runs.append(cur)
        count = 0
        for run in runs:
            if len(run) < 5:
                continue
            for i, (x, y, r) in enumerate(run):
                end = min(i, len(run) - 1 - i)
                self.water_at(x, y, r * min(1, .5 + end / 8))
                self.ring_circles.append((x, y, r))
                self.block_disc(x, y, r + 1.5)
                count += 1
        return fords, count

    def hole(self, x, y, r):
        self.water_at(x, y, r)
        self.block_disc(x, y, r + 1.4)

    def tarn(self, cx, cy, rx, ry):
        """A bigger ice-hole: a few overlapping discs."""
        step = 2.6
        y = cy - ry
        row = 0
        while y <= cy + ry:
            x = cx - rx + (step / 2 if row % 2 else 0)
            while x <= cx + rx:
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.05 and self.water_ok(x, y, 2.0):
                    self.water_at(x, y, 2.0)
                x += step
            y += step * .866
            row += 1
        self.block_disc(cx, cy, max(rx, ry) + 2.2)

    def holes(self, where, count, rmin=1.5, rmax=3.0, gap=6):
        pts = np.argwhere(where & self.inner & ~self.blocked & (self.road > 6) & (self.seam > 19) & (self.vdist > 8))
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

    def peak(self, x, y, size):
        # the painted spot, or the nearest ground that leaves the roads, the water and everything fixed clear of the mountain's foot
        clear = self.floor & (self.road > size + 2) & (self.wdist > size + 1.5)
        near = ~self.blocked & clear & self.inner & (self.seam > size + 3)
        disc = np.hypot(self.xs - x, self.ys - y)
        for j, i in sorted(np.argwhere(near & (disc < 40)).tolist(), key=lambda c: disc[c[0], c[1]]):
            if not (self.blocked & (np.hypot(self.xs - i - .5, self.ys - j - .5) < size + 1)).any():
                x, y = i + .5, j + .5
                break
        else:
            self.skipped.append((x, y, size))     # a painted mountain with no free ground within 40 tiles is left out
            return
        self.add('rime_peak', x, y, r=size, v=0 if size <= 4.5 else 1 if size <= 5 else 2)
        self.block_disc(x, y, size + 1.2)

    def ring(self, centre, radius, n, kind, **extra):
        for k in range(n):
            a = k / n * math.tau + .3
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if self.road[int(y), int(x)] > 2.4 and self.floor[int(y), int(x)]:
                self.add(kind, x, y, **extra)

    def vault_distance(self):
        """Distance to the land region Skaldholm's vault draws from the other side (0 inside it)."""
        from PIL import Image, ImageDraw
        regs = self.w['shape'].get('vaultRegions') or []
        out = np.full((self.n, self.n), 1e9)
        for reg in regs:
            poly = list(reg['land'])
            pts = [(poly[i], poly[i + 1]) for i in range(0, len(poly), 2)]
            im = Image.new('L', (self.n, self.n), 0)
            ImageDraw.Draw(im).polygon(pts, fill=1)
            inside = np.array(im, bool)
            edge = seg_field(pts + [pts[0]], self.xs, self.ys)
            out = np.minimum(out, np.where(inside, 0, edge))
        return out

    def build(self):
        w = self.w
        city = w['city']
        self.ground = np.zeros((self.n, self.n), np.uint8)
        self.vdist = self.vault_distance()
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
        for key in ('christmasRitual', 'easterRitual', 'solsticeRitual', 'valentineRitual'):
            if key in w:
                self.block_disc(w[key]['x'], w[key]['y'], w[key]['radius'] + 5)
                self.block_disc(*w[key]['tree'], 6)
        self.blocked |= self.seam < 2.5
        self.pins = []     # points no water may cover or crowd: elites, sleepers, places
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 7)
            self.pins.append((x, y, 7))
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)       # wide enough that no boulder's edge can reach the sleeper
            self.pins.append((x, y, 2.5))
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3)
            self.pins.append((p['x'], p['y'], p['r'] + 1))
        for h in HAMLETS.values():
            assert self.floor[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)

        self.fords = self.ring_count = 0
        self.skipped = []
        self.ring_circles = []
        self.short = {}
        for rx, ry, half, gaps in RINGS:
            f, c = self.ring_water(rx, ry, half, gaps)
            self.fords += f
            self.ring_count += c
        # dark ice-holes all over the glacier, thickest in the north-west fells as painted
        self.tarn(55, 68, 8, 5)
        self.tarn(40, 128, 4, 3)
        self.tarn(214, 258, 5, 3.5)
        m = self.mask
        self.hole_count = 0
        for name, n in (('fells', 16), ('wyrdgate', 8), ('strand', 5), ('drifts', 8), ('horn', 6), ('whitefall', 8), ('rimewalk', 14), ('blue', 8), ('whorl', 8), ('heart', 8), ('shelf', 4)):
            self.hole_count += self.holes(m(name), n)
        self.wdist = np.full((self.n, self.n), 1e9)
        for o in self.objects:
            if o['kind'] == 'water':
                r = int(o['r'] + 12)
                y0, y1, x0, x1 = max(int(o['y']) - r, 0), int(o['y']) + r, max(int(o['x']) - r, 0), int(o['x']) + r
                sub = np.hypot(self.xs[y0:y1, x0:x1] - o['x'], self.ys[y0:y1, x0:x1] - o['y']) - o['r']
                self.wdist[y0:y1, x0:x1] = np.minimum(self.wdist[y0:y1, x0:x1], sub)
        self.rdist = np.full((self.n, self.n), 1e9)
        for x, y, r in self.ring_circles:
            q = int(r + 8)
            y0, y1, x0, x1 = max(int(y) - q, 0), int(y) + q, max(int(x) - q, 0), int(x) + q
            self.rdist[y0:y1, x0:x1] = np.minimum(self.rdist[y0:y1, x0:x1], np.hypot(self.xs[y0:y1, x0:x1] - x, self.ys[y0:y1, x0:x1] - y) - r)
        for x, y, s in PEAKS:
            self.peak(x, y, s)
        content.dress(self, HAMLETS)
        self.lay_ground()
        self.lay_regions()
        return kept + self.objects

    def lay_ground(self):
        """Ground classes beside plain snow. None within 16-30 tiles of a seam: the other side blends toward plain Rimeveil ground."""
        G, g = GROUND, self.ground
        far = self.seam > 16 + fbm(self.noise, self.xs, self.ys, .09) * 14
        for name, cls in (('shelf', 'packed'), ('drifts', 'powder'), ('strand', 'moraine'), ('fells', 'moraine'), ('wyrdgate', 'hoar'), ('horn', 'hoar'),
                          ('whitefall', 'powder'), ('rimewalk', 'blue'), ('blue', 'packed'), ('whorl', 'crevasse'), ('heart', 'crevasse')):
            g[self.mask(name) & far] = G[cls]
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 5
        g[self.floor & far & ((self.rdist + rough < 4.5) | (self.wdist + rough * .4 < 1.6))] = G['bank']

    def lay_regions(self):
        dense = fbm(self.noise, self.xs + 200, self.ys + 300, .05)
        m = self.mask

        # The Heart: a ring of ice spires round the oldest ice, nothing else standing in the middle.
        self.block_disc(*CENTRE, 12)
        self.ring(CENTRE, 10, 12, 'spire')
        self.ring(CENTRE, 15, 8, 'ice')
        self.scatter(['ice', 'spire', 'rock'], 80, m('heart'), gap=2.4)
        self.scatter(['rock', 'bush'], 80, m('heart'), gap=1.4)

        # The Whorl: stacked ice and the wyrms' wallows.
        self.scatter(['ice', 'ice', 'spire'], 160, m('whorl'), gap=2.2)
        self.scatter(['rock', 'rock', 'bush'], 340, m('whorl'), gap=1.1)

        # The Bluewater Walk: meltwater country, scattered pines in the lee of the rings.
        self.scatter(['tree', 'tree', 'bush'], 260, m('blue') & (dense > .42), gap=1.2)
        self.scatter(['rock', 'spire', 'ice'], 360, m('blue'), gap=1.4)

        # The Rimewalk: the outermost ring's long lane, wolf country, windblown rock.
        self.scatter(['tree', 'tree', 'bush', 'tree'], 360, m('rimewalk') & (dense > .46), gap=1.1)
        self.scatter(['rock', 'rock', 'cairn_pebble', 'spire'], 520, m('rimewalk'), gap=1.1)
        self.scatter(['ice'], 70, m('rimewalk'), gap=4)

        # The Rimeward Shelf: packed snow round the camp, crab holes of broken ice and a few wind-bent pines.
        self.scatter(['tree', 'bush', 'tree'], 200, m('shelf') & (dense > .5), gap=1.2)
        self.scatter(['ice', 'rock', 'cairn_pebble'], 380, m('shelf'), gap=1.3)

        # The Southern Drifts: wide white plains towards the fen, a few drowned pines, broken ice where the crabs breed.
        self.scatter(['tree', 'bush'], 160, m('drifts') & (dense > .55), gap=1.6)
        self.scatter(['ice', 'ice', 'rock'], 300, m('drifts'), gap=1.5)
        self.scatter(['cairn_pebble', 'rock'], 260, m('drifts'), gap=1)

        # The Fenward Gap and the stranded sledge: a wreck of barrels and posts on the drift.
        wreck = (96, 259)
        self.block_disc(*wreck, 5)
        for dx, dy in ((-3, -1), (-1, 1), (1, -2), (3, 0), (4, 2), (-4, 2)):
            self.add('barrels', wreck[0] + dx, wreck[1] + dy, r=0, width=.6, depth=.6, color='', label='')
        self.ring(wreck, 5.5, 6, 'rock')

        # The Shearwind Strand: wind-scoured moraine along the western cliffs, the Whale Cairn of bones at the south end.
        self.ring((14, 206), 5, 10, 'bones')
        self.scatter(['rock', 'rock', 'cairn_boulder', 'bush'], 360, m('strand'), gap=1.2)
        self.scatter(['tree', 'bush'], 120, m('strand') & (dense > .5), gap=1.8)
        self.scatter(['ice', 'spire'], 90, m('strand'), gap=3)

        # The Whalebone Fells: pines and tusks of ice, Hoarhorn's range, the signal fire on the shoulder.
        self.ring((30, 128), 4.5, 6, 'brazier', r=.4)
        self.add('cairn_signal', 30, 125, r=1.1)
        self.ring((46, 102), 9, 10, 'spire')
        self.scatter(['tree', 'tree', 'bush'], 300, m('fells') & (dense > .4), gap=1.1)
        self.scatter(['rock', 'ice', 'spire'], 380, m('fells'), gap=1.3)
        self.scatter(['bones'], 30, m('fells'), gap=5)

        # The Wyrdgate Reach: the northern strip under the Wyrdwood's cliffs, cold pines and grey stone.
        self.scatter(['tree', 'tree', 'bush'], 320, m('wyrdgate') & (dense > .38), gap=1.1)
        self.scatter(['rock', 'cairn_pebble', 'spire'], 300, m('wyrdgate'), gap=1.1)

        # The Hornspire Ridge: peaks and spires, Whitewail's ground, the climbers' cairns.
        self.ring((268, 128), 8, 10, 'ice')
        self.scatter(['spire', 'spire', 'ice'], 130, m('horn'), gap=2.2)
        self.scatter(['rock', 'bones', 'cairn_pebble'], 260, m('horn'), gap=1.1)
        self.scatter(['tree', 'bush'], 80, m('horn') & (dense > .55), gap=2)

        # The Whitefall: the eastern slopes down towards the Crags, powder and scattered pines.
        self.scatter(['tree', 'bush', 'tree'], 260, m('whitefall') & (dense > .42), gap=1.2)
        self.scatter(['rock', 'spire', 'ice'], 360, m('whitefall'), gap=1.4)

        # Shardback's tide-pool of broken ice on the drifts.
        self.ring((214, 262), 7, 10, 'ice')

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
            sep, placed, tries = 11.0, 0, 0
            while placed < len(pool) and tries < 40000:
                tries += 1
                if tries % 8000 == 0:
                    sep *= .85
                j, i = pts[rng.randrange(len(pts))]
                x, y = round(i + rng.random(), 2), round(j + rng.random(), 2)
                if any(math.hypot(x - s['x'], y - s['y']) < sep for s in out) or not solid.free(x, y, .8, .5):
                    continue
                out.append({'x': x, 'y': y, 'kind': pool[placed], 'layout': self.TAG})
                placed += 1
            if placed < len(pool):
                self.short[name] = len(pool) - placed     # a narrow strip holds fewer than asked; the total is checked
        # ordinary enemies first: code and tests take the zone's first spawn as a plain enemy
        ordinary = [t for t in out if t.get('layout') == self.TAG]
        ordinary.sort(key=lambda t: t['kind'] != 'crab')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


def design(world, write=False):
    zone = world['zones'][1]
    d = Rimeveil(zone)
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
    prefix = ('rime_dw_', 'rime_sw_', 'rime_pk_', 'travel_driftwatch', 'travel_shearwind', 'travel_peakrest', 'mailbox_2_driftwatch', 'mailbox_2_shearwind', 'mailbox_2_peakrest')
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
    for road in ROADS + [r['points'] for r in zone['exitRoutes']]:   # the painted exit markings are roads too
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
    sif = next(n for n in zone['npcs'] if n['id'] == 'rime_pk_sif')
    route = sif['escort']['route']
    for a, b in zip(route, route[1:]):
        for k in range(21):
            x, y = a[0] + (b[0] - a[0]) * k / 20, a[1] + (b[1] - a[1]) * k / 20
            assert not solid[int(y), int(x)], f'Sif would walk into something at {x:.0f},{y:.0f}'
    water = [o for o in objects if o['kind'] == 'water']
    seam_gap = min(d.seam[int(o['y']), int(o['x'])] - o['r'] for o in water)
    vault_gap = min(d.vdist[int(o['y']), int(o['x'])] - o['r'] for o in water)
    assert seam_gap > 16, f'water {seam_gap:.1f} tiles from a seam: the other side would not draw it'
    assert vault_gap > 3, f'water {vault_gap:.1f} tiles from the vault region'
    assert sum(d.short.values()) <= 12, f'regions short of spawns: {d.short}'
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), water=len(water), ring_circles=d.ring_count, fords=d.fords, holes=d.hole_count, spawns=len(zone['slimes']),
                 lost=lost, land=int(d.floor.sum()), reachable=int(seen.sum()), peaks=len([o for o in objects if o['kind'] == 'rime_peak']), peaks_left_out=len(d.skipped), seam_water=round(float(seam_gap), 1), vault_water=round(float(vault_gap), 1))
    return d, stats


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    pal = {0: (200, 215, 232), 1: (214, 226, 238), 2: (150, 196, 228), 3: (170, 176, 184), 4: (96, 100, 112), 5: (240, 246, 252), 6: (120, 170, 214), 7: (140, 160, 190)}
    a = np.zeros((n, n, 3), np.uint8)
    a[:] = (28, 44, 74)
    for k, c in pal.items():
        a[(d.ground == k) & d.floor] = c
    im = Image.fromarray(a).resize((n * scale, n * scale), Image.NEAREST)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(120, 110, 100), width=scale)
    col = {'water': (30, 80, 170), 'rock': (110, 110, 120), 'cairn_boulder': (150, 150, 150), 'spire': (120, 190, 235), 'ice': (90, 160, 220), 'tree': (24, 70, 60), 'bush': (60, 100, 70),
           'rime_peak': (250, 250, 255), 'bones': (225, 220, 200), 'cairn_pebble': (130, 130, 135)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'crab': (255, 150, 60), 'wolf': (60, 60, 70), 'yeti': (255, 255, 255), 'wyrm': (190, 60, 220)}
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
            g.text((sx * scale, sy * scale - 14), r['name'], fill=(20, 20, 60), stroke_width=1, stroke_fill=(255, 255, 255))
    g.text((CENTRE[0] * scale - 40, CENTRE[1] * scale), 'Heart of the Glacier', fill=(20, 20, 60), stroke_width=1, stroke_fill=(255, 255, 255))
    for p in content.PLACES:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(20, 120, 60), stroke_width=1, stroke_fill=(255, 255, 255))
    im.save(out)


def main():
    world = json.loads(MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][1], d, sys.argv[2])


if __name__ == '__main__':
    main()
