#!/usr/bin/env python3
"""Sunward Vale as an authored map (zone 20 of the shapes pilot): no filler land, the whole outline used, seamless against all six shaped neighbours and walled towards the Yearwheel with a vault.

Owner request 2026-11-09: "for pilot. reshape sunward vale. and remake the zone and quests to fit the new shape. no fillers. a wall with a vault opening towards yearwheel". Owner answers:
EVERY shaped neighbour is a seam (the Stormglass Flats west, the Ribbonwild south-west, the Tanglecrown south, the Veyrroot Canopy south-east, the Lapis Erg east, the Frostwake Shelf north),
keep Old Honeyjaw and the Wicker Warden and add one elite with no quest (the Harrow Ox), a wall with a vault opening towards the Yearwheel, rebuild the town and add three outposts.

The outline at k = 1.0 is grid 352 with 87,097 land tiles (the old square held 16,384): a broad green valley. The painting shows old oaks, a net of tan trails (a trunk road down the middle) and a
river across the middle. A plain seam draws the neighbour's scenery but no people, no art-less objects and no water, so every person, building and water circle stands 17+ tiles inland of
all six borders (hubs 32+): the valley's whole working core is a 250 x 255 rectangle inside a calm strip of oaks, hedges and hares. Millbridge stands south of the river at the trunk crossing, the Honeywood
Steading in the north-west, the Wickerfield Post in the north-east and Elderroot Camp by the Hollow door in the north.

Runs in `zone_shapes.py apply` after Frostwake's design (every neighbour's gate to Sunward became the seam and every approved design already ran with the new seam as a late seam:
`LATE_SEAMS` gains 20, the road end of each stays where it was). The zone is `designOnly` + `rebuild` (zone-shapes.txt, `seamWith {20: [19, 21, 22, 23, 25, 26]}`): the old 128 square is not moved,
everything is made here from `world/zone-shapes/preshape-20.txt` (the people, places, quests keep their ids). `aim_seams` stands both portals of each seam where the neighbour's road already
ends. The Yearwheel crossing is a wall with a vaulted opening: `build_wall`.

    python3 scripts/sunward_design.py plan OUT.png     draw the plan from the current world/map.txt (read only; SUN_WORLD=<cached shaped world>)
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
import sunward_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-20.txt'

ZONE = 20
PARTNERS = (19, 21, 22, 23, 25, 26)
YEARWHEEL = 28
HAM = content.HAMLETS
SPAWN = (HAM['millbridge']['x'] - HAM['millbridge']['hw'] + 6.5, HAM['millbridge']['y'] + .5)     # Millbridge's own entry, inside the west side of the town
CROSS_IN = 6.5                      # a seam crossing's arrival, this many tiles inland
SEAM_SPAWN, SEAM_LOOSE, SEAM_PEOPLE, SEAM_WATER = 10.0, 3.0, 22.0, 18.0
WALL_IN = 1.7                       # the wall stands this far inside the border (its outer face is the border)
WALL_STEP = 2.0
TOWER_EVERY = 26.0
WALL_COLOR, TOWER_COLOR = '#e6dcc0', '#9a5a3c'       # sun-bleached stone and terracotta (the roof)
WALL_KEEP = 10.0                    # no spawn within this many tiles of the wall
VAULT_X = 262.0                     # the vault stands on the wall line at about this x (the road from the Wickerfield Post meets it)
VAULT_HALF = 5.2                    # half width of the arch's opening (tiles)
GAP_HALF = VAULT_HALF + 1.5         # no rampart within this many tiles of the vault's centre along the wall

# where each neighbour's road already ends at the seam, in that neighbour's own frame (the approved designs ran unchanged: only their gate became the seam)
PARTNER_ROAD_END = {19: (286.5, 203.5), 21: (195.5, 59.5), 22: (58.5, 49.5), 23: (61.5, 130.5), 25: (15.5, 186.5), 26: (155.61, 308.81)}
SEAM_PORTAL = {19: 'sun_stormglass_gate', 21: 'sun_ribbon_gate', 22: 'path_20_22', 23: 'path_20_23', 25: 'path_20_25', 26: 'path_20_26'}

REGIONS = {
    'mill':      dict(name='The Millbridge Fields', seeds=[(126, 201), (100, 222), (160, 214)]),
    'leas':      dict(name='The Golden Leas', seeds=[(100, 190), (66, 226), (88, 262), (66, 196)]),
    'oakwood':   dict(name='The Western Oakwood', seeds=[(84, 132), (66, 154), (92, 108), (58, 130)]),
    'honey':     dict(name='The Honeywood', seeds=[(92, 72), (70, 52), (112, 56), (80, 40)]),
    'orchards':  dict(name='The Northern Orchards', seeds=[(132, 96), (124, 126), (142, 70)]),
    'elder':     dict(name='The Elder Roots', seeds=[(176, 66), (190, 44), (204, 76), (160, 42)]),
    'wicker':    dict(name='The Wicker Fields', seeds=[(236, 94), (264, 62), (276, 84), (252, 50)]),
    'loop':      dict(name='The Loop Meadows', seeds=[(214, 128), (200, 108), (240, 136)]),
    'downs':     dict(name='The Eastern Downs', seeds=[(284, 134), (298, 110), (292, 160), (280, 112)]),
    'appleglow': dict(name='The Appleglow Rows', seeds=[(196, 196), (178, 176), (214, 204)]),
    'pastures':  dict(name='The Southern Pastures', seeds=[(212, 250), (170, 270), (236, 270), (250, 240)]),
    'heath':     dict(name='The Hawthorn Heath', seeds=[(284, 214), (298, 244), (268, 196)]),
    'hedges':    dict(name='The Hedgerow Reach', seeds=[(150, 262), (120, 268), (110, 290)]),
    'river':     dict(name='The Long Water', seeds=[(150, 176)]),
    'verge':     dict(name='The Wheel Wall Verge', seeds=[(262, 14)]),
}
GROUND = {'meadow': 1, 'clover': 2, 'leas': 3, 'oakmoss': 4, 'orchard': 5, 'silt': 6, 'heath': 7, 'stubble': 8, 'loam': 9}
REGION_GROUND = {'mill': 'clover', 'leas': 'leas', 'oakwood': 'oakmoss', 'honey': 'oakmoss', 'orchards': 'orchard', 'elder': 'loam', 'wicker': 'stubble', 'loop': 'clover',
                 'downs': 'meadow', 'appleglow': 'orchard', 'pastures': 'meadow', 'heath': 'heath', 'hedges': 'clover', 'river': 'silt', 'verge': 'heath'}

R = {'oak_tree': 1.0, 'birch_tree': .68, 'apple_tree': .9, 'willow_tree': .85, 'hawthorn_bush': .34, 'wildflowers': .12, 'haystack': .58, 'wild_hive': 1.1, 'wicker_post': .9,
     'meadow_cottage': 2.6, 'meadow_mill': 3.2, 'stone_bridge': 0, 'elder_hollow_gate': 0, 'water': 1.9}
TALL = ('oak_tree', 'birch_tree', 'willow_tree', 'apple_tree')

# scenery per 1000 land tiles of the region (x DENSITY_SCALE)
DENSITY_SCALE = 1.0
DENSITY = {
    'mill':      [('wildflowers', 7), ('hawthorn_bush', 3), ('apple_tree', 1.2), ('oak_tree', .8), ('haystack', .6)],
    'leas':      [('wildflowers', 14), ('hawthorn_bush', 3), ('oak_tree', 1.2), ('birch_tree', 1.0)],
    'oakwood':   [('oak_tree', 5.5), ('hawthorn_bush', 5), ('birch_tree', 1.5), ('wildflowers', 4)],
    'honey':     [('oak_tree', 4.5), ('hawthorn_bush', 6), ('wildflowers', 9), ('birch_tree', 1.5)],
    'orchards':  [('apple_tree', 2.2), ('hawthorn_bush', 3.5), ('wildflowers', 7), ('oak_tree', 1.4)],
    'elder':     [('oak_tree', 5), ('hawthorn_bush', 3), ('wildflowers', 5), ('birch_tree', 2)],
    'wicker':    [('haystack', 1.6), ('hawthorn_bush', 4), ('wildflowers', 7), ('oak_tree', 1.4), ('birch_tree', 1.0)],
    'loop':      [('wildflowers', 9), ('hawthorn_bush', 3.5), ('oak_tree', 2.4), ('birch_tree', 1.4)],
    'downs':     [('wildflowers', 8), ('hawthorn_bush', 4), ('oak_tree', 2.0), ('haystack', .6)],
    'appleglow': [('apple_tree', 2.6), ('wildflowers', 9), ('hawthorn_bush', 3), ('oak_tree', 1.2)],
    'pastures':  [('wildflowers', 8), ('hawthorn_bush', 4.5), ('oak_tree', 1.8), ('haystack', .8)],
    'heath':     [('hawthorn_bush', 8), ('wildflowers', 5), ('oak_tree', 1.6), ('birch_tree', 2)],
    'hedges':    [('hawthorn_bush', 8), ('wildflowers', 6), ('oak_tree', 1.4)],
    'river':     [('willow_tree', 3.4), ('wildflowers', 5), ('hawthorn_bush', 2.5)],
    'verge':     [('hawthorn_bush', 6), ('oak_tree', 2), ('wildflowers', 4)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): hares on the open meadows, snails in the orchards, foxes in the oakwoods, badgers by the water and the heath
SPAWN_SCALE = 1.0
SPAWN_DENSITY = {
    'mill':      {'meadowhare': 1.6},
    'leas':      {'meadowhare': 2.4, 'sunbacksnail': 1.0},
    'oakwood':   {'brushfox': 3.0, 'spadebadger': 1.2},
    'honey':     {'brushfox': 2.2, 'spadebadger': 1.6},
    'orchards':  {'sunbacksnail': 3.2, 'meadowhare': 1.0},
    'elder':     {'spadebadger': 2.2, 'sunbacksnail': 1.6},
    'wicker':    {'meadowhare': 2.6, 'sunbacksnail': 1.4},
    'loop':      {'meadowhare': 2.2, 'brushfox': 1.2},
    'downs':     {'meadowhare': 1.8, 'brushfox': 1.0, 'spadebadger': .8},
    'appleglow': {'sunbacksnail': 2.6, 'meadowhare': 1.0},
    'pastures':  {'sunbacksnail': 2.0, 'brushfox': 1.4, 'meadowhare': 1.0},
    'heath':     {'spadebadger': 2.4, 'brushfox': 1.6},
    'hedges':    {'brushfox': 1.6, 'spadebadger': 1.2, 'meadowhare': 1.0},
    'river':     {'spadebadger': 2.2, 'brushfox': .6},
    'verge':     {'meadowhare': 1.2},
}
# the river: its centre line (a spring pond in the west, a marsh pond in the east), the circles' radius and the two stone bridges (the roads cross there; everywhere else a ford)
RIVER = [(60, 176), (78, 178), (100, 177.5), (122, 176.5), (140, 176), (152, 175), (166, 169), (186, 161), (206, 157.5), (226, 158.5), (246, 160), (270, 158), (296, 160)]
RIVER_R = 2.1
BRIDGES = [(151.5, 175.4), (236.5, 159.6)]
POOLS = [(58, 176, 5.5, 4.2), (297, 160, 6.0, 4.4)]


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def seam_line_dist(p, pts):
    best = (1e9, None)
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0., min(1., ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
        q = (a[0] + t * dx, a[1] + t * dy)
        d = math.dist(p, q)
        if d < best[0]:
            best = (d, q)
    return best


def inland_normal(F, pts, c):
    """The unit normal of the seam polyline at the point nearest to c, pointing onto our land."""
    best = min(range(len(pts) - 1), key=lambda i: math.dist(((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2), c))
    (x1, y1), (x2, y2) = pts[best], pts[best + 1]
    ln = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / ln, (x2 - x1) / ln
    if not F[int(c[1] + ny * 4), int(c[0] + nx * 4)]:
        nx, ny = -nx, -ny
    return nx, ny


def crossings(zone, F):
    """partner -> (x, y, (nx, ny), arrival) on the seam: the neighbour's own road end, carried into this frame and put on the line."""
    out = {}
    for z, pid in SEAM_PORTAL.items():
        p = next(q for q in zone['portals'] if q['id'] == pid)
        sh = p['seam']['shift']              # this zone's frame -> the neighbour's: x + sh
        end = (PARTNER_ROAD_END[z][0] - sh[0], PARTNER_ROAD_END[z][1] - sh[1])
        d, q = seam_line_dist(end, p['seam']['points'])
        nx, ny = inland_normal(F, p['seam']['points'], q)
        out[z] = (round(q[0], 2), round(q[1], 2), (nx, ny), (round(q[0] + CROSS_IN * nx, 2), round(q[1] + CROSS_IN * ny, 2)))
    return out


def gates(F, zone):
    """id -> (x, y, walk, arrival). The six seams have no gate, only the crossing the roads aim at (where the neighbour's own road ends). The Elder Hollow door stands north of Elderroot Camp;
    the Yearwheel gate is the wall's vault (the arch's centre on the wall line)."""
    out = {}
    for z, (x, y, n, arr) in crossings(zone, F).items():
        out[SEAM_PORTAL[z]] = (x, y, None, arr)
    h = HAM['elderroot']
    out['sun_elder_gate'] = (float(h['x']), float(h['y'] - h['hh'] - 14), None, (float(h['x']), float(h['y'] - h['hh'] - 8)))
    vx, vy = vault_spot(F, zone)
    out['path_20_28'] = (vx, vy, (0, -1), (vx, round(vy + 7.0, 2)))
    return out


def wall_line(zone):
    """The Yearwheel border run as a dense polyline, 1.7 tiles inside, each point with its tangent."""
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    n = F.shape[0]
    runs = [e['points'] for e in zone['shape']['edges'] if e['kind'] == 'shared' and e['other'] == YEARWHEEL]
    assert len(runs) == 1, 'one border run with the Yearwheel'
    pts = [tuple(p) for p in runs[0]]
    line = []
    for a, b in zip(pts, pts[1:]):
        ln = math.dist(a, b)
        nx, ny = -(b[1] - a[1]) / ln, (b[0] - a[0]) / ln
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        land = lambda s: bool(F[min(max(int(my + ny * s * 5), 0), n - 1), min(max(int(mx + nx * s * 5), 0), n - 1)])
        if not land(1):
            nx, ny = -nx, -ny
        k = max(1, int(ln / .5))
        for i in range(k + 1):
            t = i / k
            line.append((a[0] + (b[0] - a[0]) * t + nx * WALL_IN, a[1] + (b[1] - a[1]) * t + ny * WALL_IN, (b[0] - a[0]) / ln, (b[1] - a[1]) / ln))
    return [p for p in line if F[min(max(int(p[1]), 0), n - 1), min(max(int(p[0]), 0), n - 1)]]


def vault_spot(F, zone):
    line = wall_line(zone)
    p = min(line, key=lambda q: abs(q[0] - VAULT_X))
    return (round(p[0], 2), round(p[1], 2))


def roads(G, zone):
    """Every hub is entered through a free corridor (the houses stand north and west of a plaza, the fire, the people and the board east and south of it): the road ends at the plaza
    along its east side (Millbridge also from the west)."""
    mb, hw, wf, er = (HAM[k] for k in ('millbridge', 'honeywood', 'wickerfield', 'elderroot'))
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    cr = crossings(zone, F)
    def lead(z):
        x, y, n, arr = cr[z]
        return [(x + 1.2 * n[0], y + 1.2 * n[1]), arr]
    vx, vy = G['path_20_28'][0], G['path_20_28'][1]
    t1 = (153, 60)       # the northern junction on the trunk road
    t2 = (151, 148)      # the river junction, north of the trunk bridge
    t3 = (150, 246)      # the southern junction
    door = G['sun_elder_gate']
    out = {}
    out['frost'] = lead(26) + [(138, 24), (146, 38), (152, 50), t1]
    out['trunk_n'] = [t1, (155, 80), (153, 104), (151, 126), t2]
    out['trunk_b'] = [t2, (152, 160), (151.5, 175.4), (150, 190), (148, 199), (140, 201), (126, 201)]
    out['trunk_s'] = [(150, 190), (151, 220), t3]
    out['south_ribbon'] = [t3, (146, 268), (138, 290), lead(21)[1], lead(21)[0]]
    out['east_south'] = [t3, (180, 249), (210, 249), (236, 247), (270, 244), lead(23)[1], lead(23)[0]]
    out['tangle'] = [(236, 247), (240, 276), (246, 308), lead(22)[1], lead(22)[0]]
    out['west'] = lead(19) + [(70, 190), (96, 197), (104, 201), (126, 201)]
    out['elder'] = [(155, 84), (170, 90), (190, 84), (194, 70), (190, er['y']), (er['x'], er['y'])]
    out['elder_door'] = [(er['x'] + 2, er['y'] - er['hh'] - 2), (er['x'] + 2, door[3][1]), (er['x'], door[1] + 1.0)]
    out['elder_link'] = [(190, er['y']), (190, er['y'] - er['hh'] - 2), (er['x'] + 2, er['y'] - er['hh'] - 2)]
    out['honey'] = [t1, (136, 64), (118, 68), (104, 72), (hw['x'], hw['y'])]
    out['honey_s'] = [(hw['x'] + 8, hw['y']), (96, 96), (98, 124), (108, 146), (118, 164), (118, 176.5), (130, 186), (131, 196), (126, 201)]
    out['honey_hives'] = [(97, 98), (78, 100), (62, 104)]
    out['honey_ridge'] = [(98, 124), (110, 120), (120, 116)]
    out['orchard'] = [(155, 80), (146, 90), (138, 96)]
    out['east'] = [t2, (176, 144), (204, 140), (224, 126), (236, 108), (250, 102), (254, 100)]
    out['east_lapis'] = [(wf['x'], wf['y']), (254, 100), (276, 108), (300, 114), lead(25)[1], lead(25)[0]]
    out['wf_s'] = [(236, 108), (240, 134), (238, 158), (236.5, 159.6), (234, 182), (236, 214), (236, 247)]
    out['wf_vault'] = [(wf['x'] + 14, wf['y']), (244, 76), (250, 44), (258, 24), (vx, vy + 1.0)]
    out['wf_field'] = [(250, 76), (254, 66), (258, 62)]
    out['wf_rows'] = [(224, 126), (212, 130)]
    out['wf_barrow'] = [(276, 108), (276, 126), (274, 138)]
    out['springs'] = [(194, 70), (200, 82), (208, 96)]
    out['es'] = [(150, 205), (170, 208), (182, 210)]
    return out


class Sunward(Designer):
    TAG, SEED = 'sunward_design_v1', 20261113
    LATE_SEAMS = set()

    def __init__(self, world, old):
        self.old = old
        self.F = np.array([[c == '#' for c in row] for row in world['shapeFloor']])
        self.G = gates(self.F, world)
        self.ROADMAP = roads(self.G, world)
        self.ROADLIST = list(self.ROADMAP.values())
        super().__init__(world)
        self.pooled = np.full((self.n, self.n), 1e9)
        self.wall = []
        self.river_field = np.full((self.n, self.n), 1e9)
        for a, b in zip(RIVER, RIVER[1:]):
            self.river_field = np.minimum(self.river_field, seg_field([a, b], self.xs, self.ys))

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
        rf = np.full((self.n, self.n), 1e9)
        for a, b in zip(RIVER, RIVER[1:]):
            rf = np.minimum(rf, seg_field([a, b], self.xs, self.ys))
        out[rf < 9] = names.index('river')                 # a real belt along the water
        out[self.wall_field < 14] = names.index('verge')    # a real strip along the wall
        return out

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.seam[iy, ix] > SEAM_LOOSE
                and self.wall_field[iy, ix] > 3.6 and self.river_field[iy, ix] > (R['water'] + 1.2 if kind != 'willow_tree' else 3.0) and self.grid.free(x, y, R.get(kind, .5) if r is None else r, .3))

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
            where = self.mask(name) & (self.seam > SEAM_LOOSE) & (self.wall_field > 3.6) & (self.river_field > R['water'] + 1.5)
            placed += self.scatter([kind], k, where, gap=1.6 if tall else gap, road=3.4 if tall else road)
        return placed

    # ---- the river ---------------------------------------------------------------------------------------------------------
    def build_river(self):
        """Solid water circles along RIVER, a pond at each end, and a ford (no circle) wherever a road crosses; the two trunk roads cross on stone bridges. Nothing within 18 tiles of a seam
        (the neighbours draw no water)."""
        dense = dense_points(RIVER, 2.4)
        road_pts = [q for road in self.ROADLIST for q in dense_points(road, 1.0)]
        placed = 0
        def ford(x, y):
            return any(math.hypot(x - qx, y - qy) < RIVER_R + 2.6 for qx, qy in road_pts if abs(qy - y) < 8 and abs(qx - x) < 8)
        for x, y in dense:
            if self.seam[int(y), int(x)] < SEAM_WATER or ford(x, y):
                continue
            self.add('water', x, y, r=RIVER_R, solid=True)
            placed += 1
        for cx, cy, rx, ry in POOLS:
            step = 3.0
            yy = cy - ry
            row = 0
            while yy <= cy + ry:
                xx = cx - rx + (step / 2 if row % 2 else 0)
                while xx <= cx + rx:
                    wob = 1 + (fbm(self.noise, xx, yy, .2) - .5) * .5
                    if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= wob and self.seam[int(yy), int(xx)] >= SEAM_WATER and not ford(xx, yy):
                        self.add('water', xx, yy, r=2.3)
                        placed += 1
                    xx += step
                yy += step * .866
                row += 1
        for bx, by in BRIDGES:
            self.add('stone_bridge', bx, by, r=0, v=len([o for o in self.objects if o['kind'] == 'stone_bridge']) % 2)
        return placed

    # ---- the Yearwheel wall ------------------------------------------------------------------------------------------------
    def build_wall(self):
        """A wall of the city's isometric ramparts and towers along the whole Yearwheel border, 1.7 tiles inside it, with ONE opening: the vault (an arch of the game's own `exitArches`, a tower
        on each side). Pieces are 2 tiles apart so nothing slips between them; a tower stands at both ends and about every 26 tiles."""
        line = wall_line(self.w)
        vx, vy = self.G['path_20_28'][0], self.G['path_20_28'][1]
        out, acc, last = [], 0.0, None
        for p in line:
            if last is not None:
                acc += math.dist(last[:2], p[:2])
            if last is None or acc >= WALL_STEP:
                out.append(p)
                acc = 0.0
            last = p
        out.append(line[-1])
        towers, dist, pieces = [], 0.0, []
        for i, (cx, cy, tx, ty) in enumerate(out):
            if i:
                dist += math.dist(out[i - 1][:2], (cx, cy))
            if math.hypot(cx - vx, cy - vy) < GAP_HALF:
                continue                                   # the opening
            ends = i in (0, len(out) - 1)
            flank = abs(math.hypot(cx - vx, cy - vy) - GAP_HALF) < WALL_STEP * .6
            if ends or flank or (dist - (towers[-1][3] if towers else 0)) >= TOWER_EVERY:
                if flank and any(math.hypot(cx - t[0], cy - t[1]) < 4 for t in towers):
                    continue
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
        self.block_disc(*content.ES16, 5.5)
        self.walled = self.build_wall()
        self.watered = self.build_river()
        self.add('elder_hollow_gate', 176, self.G['sun_elder_gate'][1] - 3, r=0, v=0, width=9, depth=4, place='sun_elder_hollow')
        self.add('wild_hive', 96, 42, r=1.1, v=0, place='sun_honeywood')
        self.add('wicker_post', 264, 62, r=.9, v=0, place='sun_wicker_field')
        content.dress(self, HAM)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def landmarks(self):
        ex = {k: (x, y) for k, x, y in content.ELITES}
        # a ring of hawthorn round each elite's pocket (each open on one side)
        self.ring_of(ex['honeyjaw'], 13, 14, 'oak_tree', rot=.2, gaps=[(0, 38)])
        self.ring_of(ex['wickerwarden'], 15, 16, 'hawthorn_bush', rot=.4, gaps=[(180, 40)])
        self.ring_of(ex['harrowox'], 17, 18, 'hawthorn_bush', rot=.1, gaps=[(200, 40)])
        # a low ring of haystacks round every hold circle
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'haystack', rot=.4)
        # apple rows: orchards in the north and south of the river, with aisles
        for (x0, y0, x1, y1) in ((120, 78, 146, 112), (180, 186, 212, 218)):
            y = y0
            while y < y1:
                x = x0 + self.rng.uniform(0, 1)
                while x < x1:
                    if self.ok(x, y, 'apple_tree', lane=3.0):
                        self.add('apple_tree', x + self.rng.uniform(-.25, .25), y + self.rng.uniform(-.25, .25))
                    x += 5.5
                y += 6.5

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
        g[self.floor & (np.hypot(self.xs - ex['honeyjaw'][0], self.ys - ex['honeyjaw'][1]) < 13 + rough)] = GROUND['oakmoss']
        g[self.floor & (np.hypot(self.xs - ex['wickerwarden'][0], self.ys - ex['wickerwarden'][1]) < 13 + rough)] = GROUND['stubble']
        g[self.floor & (np.hypot(self.xs - ex['harrowox'][0], self.ys - ex['harrowox'][1]) < 14 + rough)] = GROUND['heath']
        g[self.floor & (self.river_field < 4.5 + rough * .4)] = GROUND['silt']
        # the golden leas of the painting: three glowing meadows
        for cx, cy, r in ((100, 186, 12), (64, 244, 11), (92, 262, 12)):
            g[self.floor & (np.hypot(self.xs - cx, self.ys - cy) < r + rough * .5)] = GROUND['leas']

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])
        for o in self.objects:
            if o['kind'] in TALL + ('wildflowers', 'hawthorn_bush') and o.get('layout') == self.TAG and 'v' not in o:
                o['v'] = self.rng.randrange(4)

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        out = []
        for s in self.old['slimes']:
            if str(s.get('ambush', '')).startswith('empty-seat:'):
                out.append(dict(s, x=round(content.ES16[0] + 2, 2), y=content.ES16[1]))
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
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.seam > SEAM_SPAWN) & (self.wall_field > WALL_KEEP) & (self.river_field > 5))      # 4.4 keeps a spawn 3.4+ tiles from every road
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
        ordinary.sort(key=lambda t: t['kind'] != 'meadowhare')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


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
            h = content.HAMLETS['millbridge']
            n['x'], n['y'] = h['x'] + content.STATION_PEOPLE[n['id']][0], h['y'] + content.STATION_PEOPLE[n['id']][1]
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    mine = {p['id']: p for p in content.PLACES}
    for p in zone['places']:
        if p['id'] in mine:
            p['x'], p['y'], p['r'] = mine[p['id']]['x'], mine[p['id']]['y'], mine[p['id']]['r']
        elif p['id'] == 'es_16_m':
            p['x'], p['y'] = content.ES16
        else:
            raise AssertionError(f"unplaced old place {p['id']}")
    for p in zone['portals']:
        if p.get('seam'):                  # the six seams (zone_shapes.make_seams): their line is the border, not a gate (aim_seams stands them where the roads cross)
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'] = round(gx, 2), round(gy, 2)
        if walk:
            p['walk'] = list(walk)
    zone['futureInstance'].update(x=content.PLACES[0]['x'], y=content.PLACES[0]['y'])


def aim_seams(world, zone, G):
    """Both seam portals of each seam stand where the neighbour's road ends (the seam road pass weighs the portals' points, and quest arrows aim at them)."""
    for z, pid in SEAM_PORTAL.items():
        mine = next(p for p in zone['portals'] if p['id'] == pid)
        theirs = next(p for p in world['zones'][z - 1]['portals'] if p.get('seam') and p['to'] == ZONE)
        gx, gy, walk, arr = G[pid]
        sh = mine['seam']['shift']
        mine['x'], mine['y'], mine['tx'], mine['ty'] = round(gx, 2), round(gy, 2), round(gx + sh[0], 2), round(gy + sh[1], 2)
        theirs['x'], theirs['y'], theirs['tx'], theirs['ty'] = mine['tx'], mine['ty'], mine['x'], mine['y']


def link_travel(world):
    """Add (never strip) the Spark links across every portal into or out of Sunward Vale, both ways, as compact_atlas.sync_travel_links does."""
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


def vault_arch(G):
    x, y = G['path_20_28'][0], G['path_20_28'][1]
    return dict(x=x, y=y, vertical=False, halfWidth=VAULT_HALF, towers=True, portal='path_20_28', name='The Yearwheel')


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    G = gates(F, zone)
    restore_and_shift(zone, old, G)
    aim_seams(world, zone, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the zone was rebuilt
    d = Sunward(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    zone['objects'] = objects
    # Omit teleport door spur (elder_door) from visible brown paths while keeping the Yearwheel vault road.
    visible_roads = [road for name, road in d.ROADMAP.items() if name != 'elder_door']
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in visible_roads]
    zone['atlasPaths'] = []
    seamed = {p['id'] for p in zone['portals'] if p.get('seam')}
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items() if g not in seamed]
    zone['exitArches'] = [vault_arch(G)]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, zone, HAM, old)
    # every crossing that arrives here follows the new frame: the Elder Hollow's two ways out and the Yearwheel's way in (the six seams carry their own shift)
    arrivals = {'elder_hollow_return': G['sun_elder_gate'][3], 'elder_hollow_exit': G['sun_elder_gate'][3], 'path_28_20': G['path_20_28'][3]}
    found = set()
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals and not p.get('seam'):
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
                found.add(p['id'])
    link_travel(world)
    zones_ = [world] + world['zones']
    masters = {n['id']: n for z in zones_[:47] for n in z.get('npcs', []) if n.get('travelStop')}
    for zi in (ZONE,) + PARTNERS:          # both halves of every seam: a back-link dropped by the rebuild would not show on our side alone
        for n in zones_[zi].get('npcs', []):
            if n.get('travelStop'):
                for other in n['travelLinks']:
                    assert other in masters and n['id'] in masters[other]['travelLinks'], f"Spark link {n['id']} -> {other} is not reciprocal"
    if write:
        content.record_mailboxes(zone, HAM, ROOT / 'world/mailboxes.txt')
    problems = check(world, zone, d, solid, seen, G, found)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), wall=d.walled, water=d.watered, spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']),
                 kinds={k: sum(1 for o in objects if o['kind'] == k) for k in R})
    if problems:
        if os.environ.get('SUN_LAX'):
            print(len(problems), 'problems:', *problems[:60], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:60]))
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
        if d.road[int(n['y']), int(n['x'])] < 1.4:
            problems.append(f"npc {n['id']} stands on a road at {n['x']},{n['y']}")
    for o in zone['objects']:
        k = d.seam[int(o['y']), int(o['x'])]
        if o['kind'] in ARTLESS and k < SEAM_PEOPLE:
            problems.append(f"art-less {o['kind']} within {SEAM_PEOPLE:.0f} tiles of a seam at {o['x']},{o['y']}")
        if o['kind'] == 'water' and k < SEAM_WATER - .6:
            problems.append(f"water within {SEAM_WATER:.0f} tiles of a seam at {o['x']},{o['y']}")
        if o.get('layout') == d.TAG and o['kind'] not in ('void', 'rampart', 'tower') and k < SEAM_LOOSE - .1:
            problems.append(f"loose {o['kind']} within {SEAM_LOOSE:.0f} tiles of a seam at {o['x']},{o['y']}")
    for c in [zone['city']] + zone['camps']:
        for corner in ((c['x0'], c['y0']), (c['x1'], c['y0']), (c['x0'], c['y1']), (c['x1'], c['y1'])):
            if d.seam[int(corner[1]), int(corner[0])] < 20:
                problems.append(f"hub {c['name']} reaches within 20 tiles of a seam")
                break
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
    for need in ('elder_hollow_return', 'elder_hollow_exit', 'path_28_20'):
        if need not in found:
            problems.append(f'no incoming portal {need} found to re-aim')
    for z in PARTNERS:
        if not any(p.get('seam') and p['to'] == z for p in zone['portals']):
            problems.append(f'the seam to zone {z} is missing')
    # the Yearwheel: a wall with ONE opening, the vault
    if sum(1 for p in zone['portals'] if p['to'] == YEARWHEEL) != 1:
        problems.append('Sunward Vale needs exactly one portal to the Yearwheel (the vault)')
    wall = [o for o in zone['objects'] if o['kind'] in ('rampart', 'tower')]
    if len([o for o in wall if o['kind'] == 'tower']) < 5:
        problems.append('the wall needs at least five towers')
    for o in wall:
        if not d.floor[int(o['y']), int(o['x'])]:
            problems.append(f"wall piece off land at {o['x']},{o['y']}")
    cells = d.F & (d.wall_field < 1.2)
    ys, xs = np.nonzero(cells & seen)
    stray = [(int(x), int(y)) for x, y in zip(xs, ys) if math.hypot(x + .5 - G['path_20_28'][0], y + .5 - G['path_20_28'][1]) > GAP_HALF + 1]
    if stray:
        problems.append(f'{len(stray)} cells between the wall and the border are reachable away from the vault: {stray[:6]}')
    # an elite stands clear of everything a player walks to: awareness plus 3 tiles from every road, place and person, and from every hub and gate
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
                if solid[int(y), int(x)]:             # no exemption inside a camp: a road never runs through a house, a fire or a stone there either (tests/seam-roads.py)
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
    bg = Image.blend(bg, Image.new('RGB', bg.size, (20, 30, 20)), .35)
    pal = {1: (140, 200, 90), 2: (120, 200, 130), 3: (230, 210, 100), 4: (60, 120, 70), 5: (180, 210, 110), 6: (150, 180, 190), 7: (170, 130, 150), 8: (220, 190, 120), 9: (150, 110, 80)}
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
    col = {'oak_tree': (20, 80, 30), 'birch_tree': (200, 220, 160), 'apple_tree': (220, 90, 80), 'willow_tree': (90, 160, 110), 'hawthorn_bush': (60, 130, 60), 'wildflowers': (255, 200, 240),
           'haystack': (230, 200, 90), 'water': (70, 150, 220), 'rampart': (255, 255, 255), 'tower': (255, 140, 0), 'meadow_cottage': (200, 120, 90), 'meadow_mill': (240, 200, 120), 'stone_bridge': (200, 190, 150)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('wildflowers', 'hawthorn_bush', 'rampart', 'tower') else 1)
        c = col.get(o['kind'], (255, 200, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'meadowhare': (255, 255, 255), 'sunbacksnail': (230, 190, 90), 'brushfox': (240, 120, 60), 'spadebadger': (90, 90, 110)}
    for s_ in zone['slimes']:
        c = kc.get(s_['kind'], (255, 20, 20))
        g.rectangle([s_['x'] * scale - 2, s_['y'] * scale - 2, s_['x'] * scale + 2, s_['y'] * scale + 2], fill=c, outline=(0, 0, 0))
    for camp in [zone['city']] + zone['camps']:
        g.rectangle([camp['x0'] * scale, camp['y0'] * scale, camp['x1'] * scale, camp['y1'] * scale], outline=(255, 160, 0), width=2)
        g.text((camp['plaza']['x'] * scale - 20, camp['plaza']['y'] * scale + 40), camp['name'], fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    for p in zone['places']:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(0, 140, 60), stroke_width=1, stroke_fill=(255, 255, 255))
    for p in zone['portals']:
        g.ellipse([p['x'] * scale - 6, p['y'] * scale - 6, p['x'] * scale + 6, p['y'] * scale + 6], outline=(255, 60, 60), width=3)
        g.text((p['x'] * scale + 8, p['y'] * scale - 6), p['name'], fill=(255, 60, 60), stroke_width=1, stroke_fill=(255, 255, 255))
        if p.get('seam'):
            g.line([(x * scale, y * scale) for x, y in p['seam']['points']], fill=(255, 0, 255), width=2)
    for kind, ex, ey in content.ELITES:
        g.ellipse([ex * scale - 8, ey * scale - 8, ex * scale + 8, ey * scale + 8], outline=(255, 0, 0), width=3)
        g.text((ex * scale + 10, ey * scale - 6), kind, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    im.save(out)


def main():
    src = os.environ.get('SUN_WORLD')       # a cached shaped world (JSON), else the current map
    world = json.loads(Path(src).read_text() if src else MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])


if __name__ == '__main__':
    main()
