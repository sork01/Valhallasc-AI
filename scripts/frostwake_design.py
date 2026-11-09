#!/usr/bin/env python3
"""The Frostwake Shelf as an authored map (zone 26 of the shapes pilot): no filler land, the whole outline used, seamless against Cairnspine and walled against the Yearwheel.

Owner request 2026-11-09: "for pilot. reshape frostwake shelf. and remake the zone and quests to fit the new shape. no fillers. a wall towards yearwheel". Owner answers: seamless against
Cairnspine ONLY (Stormglass Flats and Sunward Vale stay rim gates), a solid wall and NO portal towards the Yearwheel (as on the Lapis Erg), keep the three elites (no new one), rebuild the hub
and add three outposts. The wall is built from the game's own isometric `rampart` and `tower` objects (the city wall art, real collision), never a flat drawing.

The outline at k = 1.0 is grid 312 with 51,614 land tiles (the old square held 25,600): a tall shelf. Cairnspine lies along the whole west side (283 tiles, the seam), the Yearwheel along the
east (305 tiles, the wall), Sunward Vale along the south (a gate), the Stormglass Flats on the south-west corner (a gate) and a frozen coast in the north. The painting shows pale snow with a dozen
small snowy peaks, a net of blue trails and a paler blue glacier in the south-west. Frostwake Station stands in the south, near both gates; the Bellward Post on the western slopes, the Aurora Post in the
north-east and the Ribwatch Camp on the northern rim.

Runs in `zone_shapes.py apply` after Cairnspine's design (its east rim gate became the seam: `cairn_design.aim_frostwake_seam` stands both seam portals where its road ends). The zone is
`designOnly` + `rebuild` (zone-shapes.txt, `seamWith {26: [27], 27: [14, 26]}`): the old 160 square is not moved, everything is made here from `world/zone-shapes/preshape-26.txt` (the people,
places, quests keep their ids). The Yearwheel crossing is closed on both sides: `close_yearwheel`.

    python3 scripts/frostwake_design.py plan OUT.png     draw the plan from the current world/map.txt (read only; FROST_WORLD=<cached shaped world>)
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
import frostwake_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-26.txt'

ZONE = 26
CAIRN, YEARWHEEL = 27, 28
HAM = content.HAMLETS
SPAWN = (HAM['station']['x'] - HAM['station']['hw'] + 5.5, HAM['station']['y'] + .5)     # the Station's own entry, inside the west side of the city
CROSS_IN = 6.5                      # the Cairnspine crossing's arrival, this many tiles inland
SEAM_SPAWN, SEAM_LOOSE, SEAM_PEOPLE, SEAM_DECAL = 10.0, 3.0, 22.0, 17.5
WALL_IN = 1.7                       # the wall stands this far inside the border (its outer face is the border)
WALL_STEP = 2.0
TOWER_EVERY = 28.0
WALL_COLOR, TOWER_COLOR = '#dbe9f0', '#3d6a94'       # frosted stone and glacier blue (the roof)
WALL_KEEP = 10.0                    # no spawn within this many tiles of the wall

REGIONS = {
    'station':   dict(name='The Station Flats', seeds=[(124, 268), (100, 290), (152, 284)]),
    'glacier':   dict(name='The Blue Glacier', seeds=[(84, 262), (66, 278), (96, 242)]),
    'sunward':   dict(name='The Sunward Drift', seeds=[(204, 284), (232, 270), (184, 300)]),
    'barrens':   dict(name='The Bell Barrens', seeds=[(112, 206), (96, 226), (128, 190)]),
    'bellward':  dict(name='The Bellward Slopes', seeds=[(168, 186), (160, 160), (186, 204)]),
    'fissures':  dict(name='The Blue Fissures', seeds=[(214, 240), (238, 222), (206, 262)]),
    'rim':       dict(name='The Cairn Rim', seeds=[(134, 110), (130, 84), (130, 142)]),
    'crossing':  dict(name='The Central Crossing', seeds=[(188, 118), (200, 138), (178, 142)]),
    'cliff':     dict(name='The Eastern Cliff', seeds=[(250, 122), (254, 152), (248, 92)]),
    'wallside':  dict(name='The Wheel Wall Verge', seeds=[(268, 30), (262, 182), (246, 226), (272, 70)]),
    'aurora':    dict(name='The Aurora Reach', seeds=[(232, 62), (250, 46), (214, 72)]),
    'ribfield':  dict(name='The Rib Fields', seeds=[(204, 26), (236, 24), (184, 18)]),
    'peaks':     dict(name='The Northern Peaks', seeds=[(140, 24), (132, 48), (152, 62)]),
    'poolfield': dict(name='The Pool Fields', seeds=[(208, 88), (196, 104), (222, 98)]),
    'coast':     dict(name='The Frozen Coast', seeds=[(170, 8), (226, 8), (130, 10)]),
}
GROUND = {'powder': 1, 'blueice': 2, 'crust': 3, 'deepice': 4, 'moraine': 5, 'aurora': 6, 'slate': 7, 'glacier': 8, 'coast': 9}
REGION_GROUND = {'station': 'crust', 'glacier': 'glacier', 'sunward': 'powder', 'barrens': 'crust', 'bellward': 'powder', 'fissures': 'deepice', 'rim': 'slate', 'crossing': 'blueice',
                 'cliff': 'moraine', 'wallside': 'slate', 'aurora': 'aurora', 'ribfield': 'deepice', 'peaks': 'moraine', 'poolfield': 'blueice', 'coast': 'coast'}

R = {'frostwake_snowdrift': .25, 'frostwake_ice_spire': .8, 'frostwake_snow_pine': 1.0, 'frostwake_iceflower': .1, 'frostwake_lantern': .17, 'frostwake_peak': 2.3,
     'frostwake_lodge': 2.2, 'frostwake_signal': .7, 'frostwake_hearth': .8, 'frostwake_obelisk': 1.6, 'frostwake_fossil': 1.2, 'frostwake_mammoth_bells': 1.0, 'frostwake_leviathan_rib': 1.1,
     'frostwake_crevasse': 0, 'frostwake_frozen_pool': 0}
TALL = ('frostwake_snow_pine', 'frostwake_ice_spire', 'frostwake_peak')
DECALS = ('frostwake_crevasse', 'frostwake_frozen_pool')

# scenery per 1000 land tiles of the region (x DENSITY_SCALE)
DENSITY_SCALE = 1.0
DENSITY = {
    'station':   [('frostwake_snowdrift', 5), ('frostwake_iceflower', 2), ('frostwake_snow_pine', 1.5), ('frostwake_ice_spire', 1)],
    'glacier':   [('frostwake_snowdrift', 3), ('frostwake_ice_spire', 4), ('frostwake_iceflower', 1.5), ('frostwake_peak', .25)],
    'sunward':   [('frostwake_snowdrift', 6), ('frostwake_snow_pine', 3), ('frostwake_iceflower', 3), ('frostwake_ice_spire', 1)],
    'barrens':   [('frostwake_snowdrift', 4), ('frostwake_ice_spire', 3), ('frostwake_snow_pine', 2), ('frostwake_peak', .3)],
    'bellward':  [('frostwake_snowdrift', 5), ('frostwake_snow_pine', 4), ('frostwake_iceflower', 3), ('frostwake_ice_spire', 1.5)],
    'fissures':  [('frostwake_snowdrift', 3), ('frostwake_ice_spire', 5), ('frostwake_iceflower', 1)],
    'rim':       [('frostwake_snowdrift', 4), ('frostwake_ice_spire', 3), ('frostwake_snow_pine', 3), ('frostwake_peak', .3)],
    'crossing':  [('frostwake_snowdrift', 5), ('frostwake_ice_spire', 2.5), ('frostwake_snow_pine', 2), ('frostwake_iceflower', 2)],
    'cliff':     [('frostwake_ice_spire', 5), ('frostwake_snowdrift', 3), ('frostwake_peak', .5), ('frostwake_snow_pine', 1)],
    'wallside':  [('frostwake_snowdrift', 4), ('frostwake_ice_spire', 3), ('frostwake_snow_pine', 2)],
    'aurora':    [('frostwake_snowdrift', 4), ('frostwake_ice_spire', 4), ('frostwake_iceflower', 3), ('frostwake_snow_pine', 2)],
    'ribfield':  [('frostwake_snowdrift', 3), ('frostwake_ice_spire', 5), ('frostwake_snow_pine', 1.5)],
    'peaks':     [('frostwake_peak', .8), ('frostwake_ice_spire', 4), ('frostwake_snow_pine', 4), ('frostwake_snowdrift', 3)],
    'poolfield': [('frostwake_snowdrift', 4), ('frostwake_iceflower', 4), ('frostwake_snow_pine', 2), ('frostwake_ice_spire', 1.5)],
    'coast':     [('frostwake_snowdrift', 4), ('frostwake_ice_spire', 3), ('frostwake_iceflower', 2)],
}
# ground decals (walkable cracks and frozen pools) per 1000 land tiles
DECAL_DENSITY = {
    'glacier': [('frostwake_crevasse', .8), ('frostwake_frozen_pool', .4)], 'barrens': [('frostwake_crevasse', .5)], 'fissures': [('frostwake_crevasse', 2.4)],
    'crossing': [('frostwake_crevasse', .8)], 'cliff': [('frostwake_crevasse', .6)], 'wallside': [('frostwake_crevasse', .3)], 'ribfield': [('frostwake_crevasse', 1.2)],
    'peaks': [('frostwake_crevasse', .6)], 'poolfield': [('frostwake_frozen_pool', 1.4), ('frostwake_crevasse', .4)], 'coast': [('frostwake_frozen_pool', .5)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): hares on the powder, otters at the pools, herons at the crossings and the cliff, crabs in the fissures
SPAWN_SCALE = 1.0
SPAWN_DENSITY = {
    'station':   {'snowhare': 1.4},
    'glacier':   {'iceotter': 1.6, 'glaciercrab': 1.2},
    'sunward':   {'snowhare': 2.4, 'frostheron': .8},
    'barrens':   {'snowhare': 1.6, 'glaciercrab': 1.2},
    'bellward':  {'snowhare': 2.4, 'frostheron': 1.0},
    'fissures':  {'glaciercrab': 3.6, 'iceotter': .6},
    'rim':       {'snowhare': 1.8, 'frostheron': 1.2},
    'crossing':  {'frostheron': 2.6, 'snowhare': 1.2},
    'cliff':     {'frostheron': 2.6, 'glaciercrab': .8},
    'wallside':  {'snowhare': 1.0, 'glaciercrab': 1.0},
    'aurora':    {'frostheron': 2.2, 'snowhare': 1.0},
    'ribfield':  {'glaciercrab': 2.2, 'frostheron': 1.4},
    'peaks':     {'snowhare': 1.8, 'glaciercrab': 1.2},
    'poolfield': {'iceotter': 3.4, 'frostheron': .6},
    'coast':     {'frostheron': 2.0, 'iceotter': 1.2},
}
# the small snowy peaks of the painting, in the shaped frame (kept only where the ground is free)
PEAKS = [(157, 13), (133, 27), (127, 41), (210, 44), (256, 38), (210, 122), (133, 162), (190, 192), (220, 198), (234, 216), (250, 172), (178, 240), (124, 224), (80, 254), (108, 288), (156, 148)]


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def inland_normal(F, seam, c):
    """The unit normal of the seam polyline at the point nearest to c, pointing onto our land."""
    pts = seam['points']
    best = min(range(len(pts) - 1), key=lambda i: math.dist(((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2), c))
    (x1, y1), (x2, y2) = pts[best], pts[best + 1]
    ln = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / ln, (x2 - x1) / ln
    if not F[int(c[1] + ny * 4), int(c[0] + nx * 4)]:
        nx, ny = -nx, -ny
    return nx, ny


def gates(F, zone):
    """Sunward's gate stands on the south rim (2.5 tiles in from the last land cell, arrival six tiles inside), the Stormglass gate on the south-west rim; the Cairnspine seam has no gate,
    only the crossing the roads aim at (where Cairnspine's own road ends: cairn_design.aim_frostwake_seam): id -> (x, y, walk, arrival). The Yearwheel has none (a wall)."""
    out = {}
    x = 170
    y1 = int(np.nonzero(F[:, x])[0].max())
    out['path_26_20'] = (x + .5, y1 - 1.5, (0, 1), (x + .5, y1 - 7.5))
    y = 288
    x0 = int(np.nonzero(F[y])[0].min())
    out['path_26_19'] = (x0 + 2.5, y + .5, (-1, 0), (x0 + 8.5, y + .5))
    seam = next((p for p in zone['portals'] if p.get('seam') and p['to'] == CAIRN), None)
    if seam:
        c = (seam['x'], seam['y'])
        nx, ny = inland_normal(F, seam['seam'], c)
        out['frostwake_cairn_gate'] = (c[0], c[1], None, (round(c[0] + CROSS_IN * nx, 2), round(c[1] + CROSS_IN * ny, 2)))
    return out


def roads(G):
    """Every hub is entered through a free corridor (the lodges stand north and west of an outpost's plaza, the fire, the people and the board east and south of it): the road ends
    at the plaza's east side and a short street runs on to the plaza."""
    sw, sg, cr = G['path_26_19'], G['path_26_20'], G['frostwake_cairn_gate']
    st, bw, au, rw = (HAM[k] for k in ('station', 'bellward', 'aurora', 'ribwatch'))
    J = (182, 112)
    nx, ny = cr[3][0] - cr[0], cr[3][1] - cr[1]
    ln = math.hypot(nx, ny)
    nx, ny = nx / ln, ny / ln
    pass_ = [(cr[0] + 1.2 * nx, cr[1] + 1.2 * ny), cr[3], (132, 112), (150, 110), (166, 112), J]
    gate_sw = [(sw[3][0], sw[3][1]), (60, 282), (82, 278), (104, 270.5), (120, 270.5)]
    gate_s = [(sg[3][0], sg[3][1]), (160, 288), (150, 278), (146, 268), (138, 266.5), (130, 266.8)]
    trunk_s = [(130, 266.8), (138, 266.5), (148, 258), (154, 240), (158, 222), (166, 206), (180, 201), (184, 194), (181, 186), (172, 186)]
    trunk_m = [(172, 186), (181, 186), (183, 172), (179, 150), (180, 128), J]
    trunk_n = [J, (184, 92), (190, 70), (190, 52), (186, 41), (179.5, 40), (170, 40)]
    east = [J, (204, 106), (222, 92), (232, 80), (241, 70), (240.5, 62), (231, 62)]
    link = [(240.5, 62), (242, 54), (236, 44), (226, 42), (206, 42), (190, 44), (186, 41)]
    bells = [(166, 206), (158, 203), (150, 203)]
    fissures = [(180, 201), (194, 214), (204, 228), (216, 238)]
    rib = [(186, 41), (190, 32), (194, 27), (198, 27)]
    crack = [(186, 41), (182, 28), (178, 20), (176, 18)]
    obelisk = [(242, 54), (244, 48)]
    cliff = [(222, 92), (224, 108), (230, 128)]
    pool = [(222, 92), (214, 88), (208, 86)]
    return [pass_, trunk_s, trunk_m, trunk_n, east, link, gate_s, gate_sw, bells, rib, crack, obelisk, cliff, fissures, pool]


class Frostwake(Designer):
    TAG, SEED = 'frostwake_design_v1', 20261112
    LATE_SEAMS = set()

    def __init__(self, world, old):
        self.old = old
        self.F = np.array([[c == '#' for c in row] for row in world['shapeFloor']])
        self.G = gates(self.F, world)
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        self.pooled = np.full((self.n, self.n), 1e9)
        self.wall = []

    def plan(self):
        return REGIONS, self.ROADLIST, R

    @property
    def wall_field(self):
        if not hasattr(self, '_wall_field'):
            self._wall_field = np.full((self.n, self.n), 1e9)
            for e in self.w['shape']['edges']:
                if e['kind'] == 'shared' and e['other'] == YEARWHEEL:
                    self._wall_field = np.minimum(self._wall_field, seg_field(e['points'], self.xs, self.ys))
        return self._wall_field

    def make_regions(self):
        out = super().make_regions()
        names = list(self.REGIONS)
        out[self.wall_field < 14] = names.index('wallside')          # a real strip along the wall
        out[self.coast < 11] = names.index('coast')
        return out

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.seam[iy, ix] > SEAM_LOOSE
                and self.wall_field[iy, ix] > 3.6 and self.grid.free(x, y, R.get(kind, .5) if r is None else r, .3))

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
            where = self.mask(name) & (self.seam > SEAM_LOOSE) & (self.wall_field > 3.6)
            placed += self.scatter([kind], k, where, gap=1.6 if tall else gap, road=3.4 if tall else road)
        return placed

    def decals(self, name, kinds):
        """Walkable ground art (cracks, frozen pools): at least 7 tiles apart, off roads, and 17+ tiles off the seam (the neighbour draws no such ground)."""
        area = int(self.mask(name).sum())
        pts = np.argwhere(self.mask(name) & self.inner & ~self.blocked & (self.road > 5) & (self.seam > SEAM_DECAL) & (self.wall_field > 6))
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per / 1000))
            made = 0
            for _ in range(k * 40):
                if made == k or not len(pts):
                    break
                j, i = pts[self.rng.randrange(len(pts))]
                x, y = i + self.rng.random(), j + self.rng.random()
                if any(math.hypot(o['x'] - x, o['y'] - y) < 7.5 for o in self.objects if o['kind'] in DECALS) or not self.grid.free(x, y, 2.2, .3):
                    continue
                self.add(kind, x, y, r=0, v=self.rng.randrange(4))
                made += 1
            placed += made
        return placed

    # ---- the Wheel Wall ----------------------------------------------------------------------------------------------------
    def build_wall(self):
        """A solid wall of isometric ramparts and towers along the whole Yearwheel border, 1.7 tiles inside it, with NO gate: it covers the old way east. Pieces are 2 tiles apart along the
        border and overlap, so nothing slips between them; a tower stands at both ends and about every 28 tiles."""
        runs = [e['points'] for e in self.w['shape']['edges'] if e['kind'] == 'shared' and e['other'] == YEARWHEEL]
        assert len(runs) == 1, 'one border run with the Yearwheel'
        pts = [tuple(p) for p in runs[0]]
        line = []
        for a, b in zip(pts, pts[1:]):
            ln = math.dist(a, b)
            nx, ny = -(b[1] - a[1]) / ln, (b[0] - a[0]) / ln
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            land = lambda s: bool(self.F[min(max(int(my + ny * s * 5), 0), self.n - 1), min(max(int(mx + nx * s * 5), 0), self.n - 1)])
            if not land(1):
                nx, ny = -nx, -ny
            k = max(1, int(ln / .5))
            for i in range(k + 1):
                t = i / k
                line.append((a[0] + (b[0] - a[0]) * t + nx * WALL_IN, a[1] + (b[1] - a[1]) * t + ny * WALL_IN, (b[0] - a[0]) / ln, (b[1] - a[1]) / ln))
        line = [p for p in line if self.F[min(max(int(p[1]), 0), self.n - 1), min(max(int(p[0]), 0), self.n - 1)]]      # the run's ends sit on the coast: the first and last land points take the end towers
        out, acc, last = [], 0.0, None
        for p in line:
            if last is not None:
                acc += math.dist(last[:2], p[:2])
            if last is None or acc >= WALL_STEP:
                out.append(p)
                acc = 0.0
            last = p
        out.append(line[-1])
        towers, dist = [], 0.0
        pieces = []
        for i, (cx, cy, tx, ty) in enumerate(out):
            if i:
                dist += math.dist(out[i - 1][:2], (cx, cy))
            ends = i in (0, len(out) - 1)
            if ends or (dist - (towers[-1][3] if towers else 0)) >= TOWER_EVERY:
                towers.append((cx, cy, 'tower', dist))
                continue
            ax, ay = abs(tx), abs(ty)
            w, d = (2.8, 1.8) if ax >= 2 * ay else (1.8, 2.8) if ay >= 2 * ax else (2.3, 2.3)
            pieces.append((cx, cy, 'rampart', w, d))
        for cx, cy, kind, *rest in towers:
            self.add('tower', cx, cy, r=0, v=0, width=3.4, depth=3.4, color=TOWER_COLOR, label='')
        for cx, cy, kind, w, d in pieces:
            self.add('rampart', cx, cy, r=0, v=0, width=w, depth=d, color=WALL_COLOR, label='')
        self.wall = [(o['x'], o['y']) for o in self.objects if o['kind'] in ('rampart', 'tower')]
        self.blocked |= self.wall_field < 3.5            # nothing else stands within 3.5 tiles of the wall; the pieces were added first
        return len(pieces), len(towers)

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
        self.block_disc(*content.ES22, 5.5)
        self.walled = self.build_wall()
        self.add('frostwake_mammoth_bells', 146, 203, r=1.0, v=0)
        self.add('frostwake_obelisk', 247, 43, r=1.6, v=0)
        self.add('frostwake_leviathan_rib', 201, 22, r=1.1, v=0)
        self.add('frostwake_fossil', 98, 232, r=1.2, v=0)
        self.add('frostwake_frozen_pool', 208, 80, r=0, v=0)
        content.dress(self, HAM)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def landmarks(self):
        ex = {k: (x, y) for k, x, y in content.ELITES}
        for x, y in PEAKS:
            if self.ok(x, y, 'frostwake_peak', lane=3.0):
                self.add('frostwake_peak', x, y)
        # a ring of ice spires round each elite's pocket (each open on one side)
        self.ring_of(ex['bellmammoth'], 13, 14, 'frostwake_ice_spire', rot=.2, gaps=[(0, 38)])
        self.ring_of(ex['auroramanta'], 15, 16, 'frostwake_ice_spire', rot=.4, gaps=[(180, 40)])
        self.ring_of(ex['crevasseleviathan'], 17, 18, 'frostwake_ice_spire', rot=.1, gaps=[(200, 40)])
        # lanterns in pairs along the main roads, one at every bend of the Lantern Road
        for road in (self.ROADLIST[1], self.ROADLIST[2], self.ROADLIST[3], self.ROADLIST[4], self.ROADLIST[0]):
            pts = dense_points(road, 1.0)
            for i in range(7, len(pts) - 4, 15):
                x, y = pts[i]
                side = 1 if (i // 15) % 2 else -1
                if self.ok(x + side * 2.8, y, 'frostwake_lantern', lane=2.2):
                    self.add('frostwake_lantern', x + side * 2.8, y)
        # a low ring of lanterns round every hold circle
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'frostwake_lantern', rot=.4)

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
        g[self.floor & (np.hypot(self.xs - ex['bellmammoth'][0], self.ys - ex['bellmammoth'][1]) < 13 + rough)] = GROUND['moraine']
        g[self.floor & (np.hypot(self.xs - ex['auroramanta'][0], self.ys - ex['auroramanta'][1]) < 13 + rough)] = GROUND['aurora']
        g[self.floor & (np.hypot(self.xs - ex['crevasseleviathan'][0], self.ys - ex['crevasseleviathan'][1]) < 14 + rough)] = GROUND['deepice']
        g[self.floor & (self.coast < 6 + rough * .5)] = GROUND['coast']

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])
        for name, kinds in DECAL_DENSITY.items():
            self.decals(name, kinds)
        for o in self.objects:
            if o['kind'] in TALL + ('frostwake_snowdrift',) and o.get('layout') == self.TAG and 'v' not in o:
                o['v'] = self.rng.randrange(4)

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        out = []
        for s in self.old['slimes']:
            if str(s.get('ambush', '')).startswith('empty-seat:'):
                out.append(dict(s, x=round(content.ES22[0] + 2, 2), y=content.ES22[1]))
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
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.seam > SEAM_SPAWN) & (self.wall_field > WALL_KEEP))      # 4.4 keeps a spawn 3.4+ tiles from every road
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
        ordinary.sort(key=lambda t: t['kind'] != 'snowhare')
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
        elif n['id'] in content.STATION_PEOPLE:
            h = content.HAMLETS['station']
            n['x'], n['y'] = h['x'] + content.STATION_PEOPLE[n['id']][0], h['y'] + content.STATION_PEOPLE[n['id']][1]
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    mine = {p['id']: p for p in content.PLACES}
    for p in zone['places']:
        if p['id'] in mine:
            p['x'], p['y'], p['r'] = mine[p['id']]['x'], mine[p['id']]['y'], mine[p['id']]['r']
        elif p['id'] == 'es_22_m':
            p['x'], p['y'] = content.ES22
        else:
            raise AssertionError(f"unplaced old place {p['id']}")
    keep = []
    for p in zone['portals']:
        if p['to'] == YEARWHEEL:           # the wall covers it up: no crossing to the Yearwheel from here
            continue
        if p.get('seam'):                  # the Cairnspine seam (zone_shapes.make_seams): its line is the border, not a gate (cairn_design.aim_frostwake_seam stands it)
            keep.append(p)
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'] = round(gx, 2), round(gy, 2)
        p['walk'] = list(walk)
        keep.append(p)
    zone['portals'] = keep


def close_yearwheel(world, zone):
    """Both halves of the old Frostwake-Yearwheel crossing go: the portals, their exit routes and trails, the atlas link and the Spark links. Idempotent (compact_atlas makes them again on a
    full sync-world, and this runs after it)."""
    z28 = world['zones'][YEARWHEEL - 1]
    gone_portals = [p for p in z28['portals'] if p['to'] == ZONE]
    z28['portals'] = [p for p in z28['portals'] if p['to'] != ZONE]
    ids = {p['id'] for p in gone_portals}
    z28['exitRoutes'] = [r for r in z28.get('exitRoutes', []) if r['portal'] not in ids]
    near = lambda a, p: math.hypot(a[0] - p['x'], a[1] - p['y']) < 1.0
    gone = [a for a in z28.get('atlasPaths', []) if any(near(a[0], p) or near(a[-1], p) for p in gone_portals)]
    z28['atlasPaths'] = [a for a in z28.get('atlasPaths', []) if a not in gone]
    z28['paths'] = [a for a in z28['paths'] if a not in gone]
    world['atlas']['links'] = [l for l in world['atlas']['links'] if {l['a'], l['b']} != {ZONE, YEARWHEEL}]
    mine = {n['id'] for n in zone['npcs'] if n.get('travelStop')}
    theirs = {n['id'] for n in z28['npcs'] if n.get('travelStop')}
    for n in zone['npcs']:
        if n.get('travelStop'):
            n['travelLinks'] = [t for t in n['travelLinks'] if t not in theirs]
    for n in z28['npcs']:
        if n.get('travelStop'):
            n['travelLinks'] = [t for t in n['travelLinks'] if t not in mine]


def link_travel(world):
    """Add (never strip) the Spark links across every portal into or out of the Frostwake Shelf, both ways, as compact_atlas.sync_travel_links does."""
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
    G = gates(F, zone)
    restore_and_shift(zone, old, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the zone was rebuilt
    d = Frostwake(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    seamed = {p['id'] for p in zone['portals'] if p.get('seam')}
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items() if g not in seamed]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, zone, HAM, old)
    # every crossing that arrives here follows the new frame: Sunward's and the Stormglass gates (the Cairnspine seam carries its own shift)
    arrivals = {'path_19_26': G['path_26_19'][3], 'path_20_26': G['path_26_20'][3]}
    found = set()
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals and not p.get('seam'):
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
                found.add(p['id'])
    close_yearwheel(world, zone)
    link_travel(world)
    zones_ = [world] + world['zones']
    masters = {n['id']: n for z in zones_[:47] for n in z.get('npcs', []) if n.get('travelStop')}
    for zi in (ZONE, CAIRN):          # both halves of the seam: a back-link dropped by the rebuild would not show on our side alone
        for n in zones_[zi].get('npcs', []):
            if n.get('travelStop'):
                for other in n['travelLinks']:
                    assert other in masters and n['id'] in masters[other]['travelLinks'], f"Spark link {n['id']} -> {other} is not reciprocal"
    if write:
        content.record_mailboxes(zone, HAM, ROOT / 'world/mailboxes.txt')
    problems = check(world, zone, d, solid, seen, G, found)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), wall=d.walled, spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']),
                 kinds={k: sum(1 for o in objects if o['kind'] == k) for k in R})
    if problems:
        if os.environ.get('FROST_LAX'):
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
        if t.get('layout') == d.TAG and d.wall_field[int(t['y']), int(t['x'])] <= WALL_KEEP:
            problems.append(f'spawn within {WALL_KEEP:.0f} tiles of the wall {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
        if d.seam[int(n['y']), int(n['x'])] < SEAM_PEOPLE:
            problems.append(f"npc {n['id']} stands within {SEAM_PEOPLE:.0f} tiles of a seam (a plain seam draws no people)")
    for n in zone['npcs']:
        if d.road[int(n['y']), int(n['x'])] < 1.4:
            problems.append(f"npc {n['id']} stands on a road at {n['x']},{n['y']}")
    for o in zone['objects']:
        if o['kind'] in ARTLESS and d.seam[int(o['y']), int(o['x'])] < SEAM_PEOPLE:
            problems.append(f"art-less {o['kind']} within {SEAM_PEOPLE:.0f} tiles of a seam at {o['x']},{o['y']}")
        if o['kind'] in DECALS and d.seam[int(o['y']), int(o['x'])] < SEAM_DECAL - .6:
            problems.append(f"{o['kind']} within {SEAM_DECAL:.0f} tiles of a seam at {o['x']},{o['y']}")
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
        if not d.floor[int(p['y']), int(p['x'])]:
            problems.append(f"place {p['id']} off land")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
        if walk and not seen[int(gy - walk[1] * 3), int(gx - walk[0] * 3)]:
            problems.append(f'gate {g} is blocked from the inside')
    for need in ('path_19_26', 'path_20_26'):
        if need not in found:
            problems.append(f'no incoming portal {need} found to re-aim')
    # no crossing to the Yearwheel from either side
    if any(p['to'] == YEARWHEEL for p in zone['portals']):
        problems.append('the Frostwake Shelf still has a portal to the Yearwheel')
    if any(p['to'] == ZONE for p in world['zones'][YEARWHEEL - 1]['portals']):
        problems.append('the Yearwheel still has a portal to the Frostwake Shelf')
    if not any(p.get('seam') and p['to'] == CAIRN for p in zone['portals']):
        problems.append('the Cairnspine seam is missing')
    # the wall: towers at both ends, on land, and nothing reachable between it and the border
    wall = [o for o in zone['objects'] if o['kind'] in ('rampart', 'tower')]
    if len([o for o in wall if o['kind'] == 'tower']) < 6:
        problems.append('the wall needs at least six towers')
    for o in wall:
        if not d.floor[int(o['y']), int(o['x'])]:
            problems.append(f"wall piece off land at {o['x']},{o['y']}")
    cells = d.F & (d.wall_field < 1.2)
    ys, xs = np.nonzero(cells & seen)
    stray = [(int(x), int(y)) for x, y in zip(xs, ys)]
    if stray:
        problems.append(f'{len(stray)} cells between the wall and the border are reachable: {stray[:6]}')
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
                if solid[int(y), int(x)]:             # no exemption inside a camp: a road never runs through a lodge, a fire or a stone there either (tests/seam-roads.py)
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
    pal = {1: (235, 242, 250), 2: (150, 200, 225), 3: (170, 185, 200), 4: (60, 120, 170), 5: (120, 125, 135), 6: (170, 225, 200), 7: (95, 105, 125), 8: (180, 215, 240), 9: (205, 215, 225)}
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
    col = {'frostwake_snowdrift': (240, 248, 255), 'frostwake_ice_spire': (110, 190, 220), 'frostwake_snow_pine': (40, 100, 110), 'frostwake_iceflower': (190, 120, 220),
           'frostwake_lantern': (255, 210, 120), 'frostwake_peak': (150, 160, 175), 'frostwake_crevasse': (30, 80, 150), 'frostwake_frozen_pool': (90, 160, 210), 'rampart': (255, 255, 255), 'tower': (255, 140, 0)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('frostwake_snowdrift', 'frostwake_lantern', 'frostwake_iceflower', 'rampart', 'tower') else 1)
        c = col.get(o['kind'], (255, 200, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'snowhare': (255, 255, 255), 'iceotter': (150, 110, 80), 'frostheron': (120, 160, 230), 'glaciercrab': (230, 100, 80)}
    for s_ in zone['slimes']:
        c = kc.get(s_['kind'], (255, 20, 20))
        g.rectangle([s_['x'] * scale - 2, s_['y'] * scale - 2, s_['x'] * scale + 2, s_['y'] * scale + 2], fill=c, outline=(0, 0, 0))
    for camp in [zone['city']] + zone['camps']:
        g.rectangle([camp['x0'] * scale, camp['y0'] * scale, camp['x1'] * scale, camp['y1'] * scale], outline=(255, 160, 0), width=2)
        g.text((camp['plaza']['x'] * scale - 20, camp['plaza']['y'] * scale + 40), camp['name'], fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    for r in REGIONS.values():
        sx, sy = r['seeds'][0]
        g.text((sx * scale - 20, sy * scale - 14), r['name'], fill=(30, 30, 60), stroke_width=1, stroke_fill=(255, 255, 255))
    for p in zone['places']:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(0, 140, 60), stroke_width=1, stroke_fill=(255, 255, 255))
    for p in zone['portals']:
        g.ellipse([p['x'] * scale - 6, p['y'] * scale - 6, p['x'] * scale + 6, p['y'] * scale + 6], outline=(255, 60, 60), width=3)
        g.text((p['x'] * scale + 8, p['y'] * scale - 6), p['name'], fill=(255, 60, 60), stroke_width=1, stroke_fill=(255, 255, 255))
    for kind, ex, ey in content.ELITES:
        g.ellipse([ex * scale - 8, ey * scale - 8, ex * scale + 8, ey * scale + 8], outline=(255, 0, 0), width=3)
        g.text((ex * scale + 10, ey * scale - 6), kind, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    im.save(out)


def main():
    src = os.environ.get('FROST_WORLD')       # a cached shaped world (JSON), else the current map
    world = json.loads(Path(src).read_text() if src else MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])


if __name__ == '__main__':
    main()
