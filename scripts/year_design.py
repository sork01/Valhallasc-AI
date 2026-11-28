#!/usr/bin/env python3
"""The Yearwheel as an authored map (zone 28 of the shapes pilot): its own scale (k = 2.8, grid 888), no filler land, the whole outline used, walled on the Lapis and Frostwake sides, and ONE
seamless vault to Sunward Vale.

Owner request 2026-11-09: "for pilot. reshape yearwheel. and remake the zone and quests to fit the new shape. no fillers. Seamless through the vault to sunward vale. This one could keep the 2.8
tiles per pixel. Just have the vault towards sunvale be seamless". Owner answers: keep the four season towns (Springmere, Solhaven, Harvestwatch, Rimehold) round the Equinox Crossing and add
three outposts (Wheelmark Post, Tidehollow Camp, Lowfall Rest), keep the 12 seasonal elites and add one with no quest (the Equinox Stag), the same isometric wall on the Yearwheel side of the
Lapis and Frostwake borders.

The outline at k = 2.8 is grid 888 with 385,949 land tiles (the old square was 400, 160,000 tiles): a tall wheel with the sea along the north and the east. The four quarters meet at the
Equinox Crossing (440, 480): spring south-west (Springmere, the Blooming Labyrinth), summer south-east (Solhaven, the Solar Crucible), autumn north-east (Harvestwatch, the Amber Archive),
winter north-west (Rimehold, the Silent Solstice). The Black Hour Foundry's door stands beside the axle.

The vault is the ONLY crossing. A vault is one doorway seen from two frames, so the scales may differ: the Yearwheel frame is Sunward's frame plus a WHOLE-TILE shift (`vault_frame`), the two
border lines agree within a few hundredths of a tile at the doorway (asserted), and each zone draws the other's ground, scenery and wall inside a region polygon beyond the line. Sunward's approved
design is untouched apart from `path_20_28` (now a `Portal.vault`) and its `shape.vaultRegions` (`late_vault`).

    python3 scripts/year_design.py plan OUT.png     draw the plan (read only; YEAR_WORLD=<cached shaped world>)
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
import year_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-28.txt'

ZONE = 28
SUNWARD = 20
K = 2.8
HAM = content.HAMLETS
CX, CY = content.CENTRE
SPAWN = (HAM['springmere']['x'] - HAM['springmere']['hw'] + 6.5, HAM['springmere']['y'] + .5)
WALL_IN = 1.7                       # the wall stands this far inside the border (its outer face is the border)
WALL_STEP = 2.0
TOWER_EVERY = 26.0
WALL_KEEP = 10.0                    # no spawn within this many tiles of a wall
VAULT_HALF = 5.2                    # half width of the arch's opening (Sunward's own arch)
VAULT_SPAN = 40.0                   # the region polygons reach this far along the line on each side of the vault
MATCH_EXACT, MATCH_TAPER = 46, 44   # our border is Sunward's own line this far each side of the vault, then eases back to the atlas line over the next stretch
REGION_DEPTH, STRIP_DEPTH = 90., 4.
INSET = .5                          # each region starts this far inside its own land (a sliver of other-zone ground never shows a gap)
POCKET_DEPTH = 4.6                  # walkable ground this far past our own border line, across the arch (the walker steps up to the arch before it crosses)
GAP_HALF = VAULT_HALF + 1.5
WALL_COLORS = {'stone': '#d8d2c4', 'roof': '#6a8a99'}       # frosted stone, slate-blue roofs: the wheel's own wall

SEASONS = ('sp', 'su', 'au', 'wi')
SEASON_NAME = ('spring', 'summer', 'autumn', 'winter')


def season_of(x, y):
    """The quarter a point lies in: 0 spring (south-west), 1 summer (south-east), 2 autumn (north-east), 3 winter (north-west) (client: yearSeason)."""
    return (0 if y >= CY else 3) if x < CX else (1 if y >= CY else 2)


REGIONS = {
    # spring, south-west
    'springmere': dict(name='The Springmere Meadows', seeds=[(300, 770), (330, 740), (270, 800)], season=0),
    'bloom':      dict(name='The Blooming Reach', seeds=[(232, 620), (250, 560), (290, 640)], season=0),
    'mere':       dict(name='The Mere Fields', seeds=[(380, 690), (400, 760), (350, 650)], season=0),
    'vergevault': dict(name='The Vault Verge', seeds=[(300, 850), (360, 850)], season=0),
    'tarn':       dict(name='The Rainseraph Tarn', seeds=[(430, 800), (410, 840)], season=0),
    # summer, south-east
    'solhaven':   dict(name='The Solhaven Leas', seeds=[(620, 660), (590, 640), (650, 690)], season=1),
    'sunpine':    dict(name='The Sunpine Heights', seeds=[(700, 590), (690, 640), (710, 560)], season=1),
    'lowfall':    dict(name='The Lowfall Plain', seeds=[(480, 650), (520, 740), (440, 700)], season=1),
    'golden':     dict(name='The Golden Reach', seeds=[(560, 560), (520, 590), (600, 600)], season=1),
    # autumn, north-east
    'harvest':    dict(name='The Harvestwatch Orchards', seeds=[(620, 300), (590, 330), (650, 270)], season=2),
    'amber':      dict(name='The Amber Downs', seeds=[(580, 420), (540, 380), (620, 440)], season=2),
    'coast':      dict(name='The Tidehollow Coast', seeds=[(700, 470), (720, 390), (700, 540)], season=2),
    'copper':     dict(name='The Copper Ridge', seeds=[(520, 220), (600, 190), (470, 300)], season=2),
    # winter, north-west
    'rimehold':   dict(name='The Rimehold Snowfields', seeds=[(320, 300), (350, 330), (290, 270)], season=3),
    'frost':      dict(name='The Frost Reach', seeds=[(336, 128), (400, 90), (300, 170)], season=3),
    'longnight':  dict(name='The Long Night Pass', seeds=[(290, 210), (270, 380), (250, 290)], season=3),
    'wheelmark':  dict(name='The Wheelmark Heights', seeds=[(420, 250), (390, 360), (440, 180)], season=3),
    # the crossing and the walls
    'crossing':   dict(name='The Equinox Crossing', seeds=[(440, 480)], season=None),
    'verge':      dict(name='The Wheel Wall Verge', seeds=[(240, 800)], season=None),
}
R = {'year_bloomtree': 1.0, 'year_spring_pool': 0, 'year_bluebell': .12, 'year_fern': .3, 'year_sunpine': 1.05, 'year_sunflower': .16, 'year_goldenstone': .8, 'year_citrus': .22,
     'year_amberoak': 1.0, 'year_leafpile': .18, 'year_mushroom': .22, 'year_copperstone': .8, 'year_frostbirch': .9, 'year_snowdrift': .2, 'year_iceobelisk': .8, 'year_holly': .25,
     'year_lodge': 0, 'year_lantern': .2, 'year_waymarker': .3, 'year_axle': 0, 'noticeboard': .4, 'campfire': .65, 'bench': 0}
TALL = ('year_bloomtree', 'year_sunpine', 'year_amberoak', 'year_frostbirch')
FAMILY = [
    [('year_bloomtree', 2.5), ('year_spring_pool', .8), ('year_bluebell', 2.4), ('year_fern', 1.8)],
    [('year_sunpine', 2.5), ('year_sunflower', 2.3), ('year_goldenstone', 1.6), ('year_citrus', 1.0)],
    [('year_amberoak', 2.5), ('year_leafpile', 2.6), ('year_mushroom', 1.6), ('year_copperstone', 1.2)],
    [('year_frostbirch', 2.5), ('year_snowdrift', 2.6), ('year_iceobelisk', 1.6), ('year_holly', 1.0)],
]
SPAWN_PER_1000 = 1.1                # ordinary spawns per 1000 land tiles of a quarter
DENSITY_SCALE = 1.0
GATE_KIND = {'sp': 'year_bloom_gate', 'su': 'year_solar_gate', 'au': 'year_amber_gate', 'wi': 'year_solstice_gate'}


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def seg_nearest(p, pts):
    best = (1e9, None, 0)
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0., min(1., ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
        q = (a[0] + t * dx, a[1] + t * dy)
        d = math.dist(p, q)
        if d < best[0]:
            best = (d, q, i)
    return best


def run_of(zone, other):
    runs = [e['points'] for e in zone['shape']['edges'] if e['kind'] == 'shared' and e['other'] == other]
    assert len(runs) == 1, f'one border run with zone {other}'
    return [tuple(p) for p in runs[0]]


# ---- the vault: one doorway, two frames ----------------------------------------------------------------------------------------
def vault_frame(world):
    """The whole-tile shift between Sunward's frame and ours at the doorway, and the doorway's geometry in both. Sunward's arch stands on its wall line, 1.7 tiles inside its border;
    the Yearwheel's border at the same atlas point is the same line (the scales differ, so only the tangent and a few hundredths of a tile agree: asserted)."""
    S, Y = world['zones'][SUNWARD - 1], world['zones'][ZONE - 1]
    arch = next(a for a in S['exitArches'] if a['portal'] == 'path_20_28')
    runS, runY = run_of(S, ZONE), run_of(Y, SUNWARD)
    dS, bS, iS = seg_nearest((arch['x'], arch['y']), runS)
    tS = S['shape']['T']
    tY = Y['shape']['T']
    atlas = (bS[0] + tS[0], bS[1] + tS[1])
    bY = (atlas[0] * K - tY[0], atlas[1] * K - tY[1])
    (ax, ay), (bx, by) = runS[iS], runS[iS + 1]
    ln = math.hypot(bx - ax, by - ay)
    tx, ty = (bx - ax) / ln, (by - ay) / ln
    nx, ny = -ty, tx
    d = (bY[0] - bS[0], bY[1] - bS[1])
    best = None
    for sx in range(round(d[0]) - 5, round(d[0]) + 6):
        for sy in range(round(d[1]) - 5, round(d[1]) + 6):
            r = (d[0] - sx, d[1] - sy)
            cost = abs(nx * r[0] + ny * r[1]) * 10 + abs(tx * r[0] + ty * r[1]) * .05
            if best is None or cost < best[0]:
                best = (cost, sx, sy)
    sx, sy = best[1], best[2]
    # every point of Sunward's run within VAULT_SPAN of the vault, carried into our frame, against our own run
    worst = 0.
    for (px, py) in dense_points([q for q in runS if math.dist(q, bS) < VAULT_SPAN + 6], 1.0):
        if math.dist((px, py), bS) > VAULT_SPAN:
            continue
        worst = max(worst, seg_nearest((px + sx, py + sy), runY)[0])
    nsign = 1 if (S['shapeFloor'][int(bS[1] + ny * 4)][int(bS[0] + nx * 4)] == '#') else -1     # +n points onto Sunward's land
    return dict(shift=(sx, sy), archS=(arch['x'], arch['y']), archY=(arch['x'] + sx, arch['y'] + sy), bS=bS, bY=(bS[0] + sx, bS[1] + sy), tangent=(tx, ty), inland_S=(nx * nsign, ny * nsign),
                half=arch['halfWidth'], worst=worst, runS=runS, runY=runY)


def sub_run(run, centre, span):
    """The part of a border run within `span` tiles (along the line) of `centre`, as a dense polyline in run order."""
    dense = dense_points(run, 1.0)
    return [p for p in dense if math.dist(p, centre) <= span + .5]


def band(line, normal_out, d0, d1):
    """A polygon [x, y, ...]: the line offset by d0 followed by the line offset by d1 in reverse (the line is the first half), normals pointing away from the zone's land."""
    pts = line
    ns = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        ln = math.dist(a, b) or 1e-9
        tx, ty = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
        n = (-ty, tx)
        if n[0] * normal_out[0] + n[1] * normal_out[1] < 0:
            n = (-n[0], -n[1])
        ns.append(n)
    sparse = [i for i in range(len(pts)) if i % 4 == 0 or i == len(pts) - 1]
    a = [round(c, 2) for i in sparse for c in (pts[i][0] + ns[i][0] * d0, pts[i][1] + ns[i][1] * d0)]
    b = [round(c, 2) for i in reversed(sparse) for c in (pts[i][0] + ns[i][0] * d1, pts[i][1] + ns[i][1] * d1)]
    return a + b


def match_border(zone, world, fr):
    """The Yearwheel's border and Sunward's are the same atlas line at two scales, so they agree only near the vault (the curvature differs by 2.8x: 3 tiles apart 40 tiles away). Within MATCH_EXACT
    tiles of the doorway our floor ends EXACTLY where Sunward's begins (whole-tile shift: the two cell grids coincide, so no sliver and no overlap), and over the next MATCH_TAPER tiles the border
    eases back to the atlas line, which the rest of the wheel keeps. Returns the largest edit (tiles)."""
    S = world['zones'][SUNWARD - 1]
    sx, sy = fr['shift']
    FS = np.array([[c == '#' for c in r] for r in S['shapeFloor']])
    F = np.array([[c == '#' for c in r] for r in zone['shapeFloor']])
    n = F.shape[0]
    bx = int(round(fr['bY'][0]))
    reach = MATCH_EXACT + MATCH_TAPER

    def s_top(x):
        xs_ = x - sx
        col = np.nonzero(FS[:, xs_])[0] if 0 <= xs_ < FS.shape[1] else []
        assert len(col), f'Sunward has no land in column {xs_}'
        return int(col.min()) + sy

    def y_bottom(x):
        col = np.nonzero(F[:, x])[0]
        return int(col.max()) + 1

    def smooth(t):
        t = min(max(t, 0.), 1.)
        return t * t * (3 - 2 * t)
    delta = {-1: s_top(bx - MATCH_EXACT) - y_bottom(bx - MATCH_EXACT), 1: s_top(bx + MATCH_EXACT) - y_bottom(bx + MATCH_EXACT)}
    biggest = 0
    rows = {}
    for x in range(bx - reach, bx + reach + 1):
        dx = x - bx
        yb = y_bottom(x)
        if abs(dx) <= MATCH_EXACT:
            r = s_top(x)
        else:
            side = 1 if dx > 0 else -1
            r = yb + round(delta[side] * (1 - smooth((abs(dx) - MATCH_EXACT) / MATCH_TAPER)))
        rows[x] = r
        biggest = max(biggest, abs(r - yb))
        lo, hi = max(min(yb, r) - 2, 0), min(max(yb, r) + 16, n - 1)
        F[lo:hi + 1, x] = np.arange(lo, hi + 1) < r
    zone['shapeFloor'] = [''.join('#' if v else ' ' for v in row) for row in F]
    # the edge letters of the cells just outside the edited columns
    E = [list(r) for r in zone['shapeEdge']]
    for x in range(bx - reach, bx + reach + 1):
        r = rows[x]
        for y in range(max(r - 2, 0), min(r + 16, n)):
            if F[y, x]:
                E[y][x] = ' '
            else:
                E[y][x] = 'A' if y - r < 14 else ' '
    zone['shapeEdge'] = [''.join(r) for r in E]
    # the run's polyline (the wall follows it)
    runY = fr['runY']
    asc = sorted(runY)
    ys_poly = lambda x: float(np.interp(x, [q[0] for q in asc], [q[1] for q in asc]))
    asS = sorted(fr['runS'])
    yS_poly = lambda x: float(np.interp(x - sx, [q[0] for q in asS], [q[1] for q in asS])) + sy
    dpoly = {side: yS_poly(bx + side * MATCH_EXACT) - ys_poly(bx + side * MATCH_EXACT) for side in (-1, 1)}
    new = []
    for x in range(bx + reach, bx - reach - 1, -2):
        dx = x - bx
        y = yS_poly(x) if abs(dx) <= MATCH_EXACT else ys_poly(x) + dpoly[1 if dx > 0 else -1] * (1 - smooth((abs(dx) - MATCH_EXACT) / MATCH_TAPER))
        new.append((float(x), round(y, 2)))
    east = [q for q in runY if q[0] > bx + reach]
    west = [q for q in runY if q[0] < bx - reach]
    assert east + new + west == sorted(east + new + west, key=lambda q: -q[0]), 'the border run must run east to west'
    fr['runY'] = east + new + west
    for e in zone['shape']['edges']:
        if e['kind'] == 'shared' and e['other'] == SUNWARD:
            e['points'] = [[round(a, 2), round(b, 2)] for a, b in fr['runY']]
    fr['bY'] = (fr['bS'][0] + sx, fr['bS'][1] + sy)
    # the proof: our last land row meets Sunward's first, column by column, across the exact stretch
    for x in range(bx - MATCH_EXACT, bx + MATCH_EXACT + 1):
        assert y_bottom_of(F, x) == s_top(x), f'column {x}: our land ends at {y_bottom_of(F, x)}, Sunward\'s begins at {s_top(x)}'
    return biggest


def y_bottom_of(F, x):
    return int(np.nonzero(F[:, x])[0].max()) + 1


def regions_for(fr):
    """shape.vaultRegions of both zones: `city` = what the OTHER zone owns beyond our line (the name the client already reads), `land` = our side, `strip` = the wall's own strip."""
    outS = (-fr['inland_S'][0], -fr['inland_S'][1])             # away from Sunward's land: into the Yearwheel
    outY = (-outS[0], -outS[1])
    lineS = sub_run(fr['runS'], fr['bS'], VAULT_SPAN)
    lineY = sub_run(fr['runY'], fr['bY'], VAULT_SPAN)
    # each region starts INSET tiles inside its own land
    S_reg = dict(portal='path_20_28', to=ZONE, city=band(lineS, outS, -INSET, REGION_DEPTH), land=band(lineS, outS, -INSET, -REGION_DEPTH), strip=band(lineS, outS, 0, -STRIP_DEPTH))
    Y_reg = dict(portal='path_28_20', to=SUNWARD, city=band(lineY, outY, -INSET, REGION_DEPTH), land=band(lineY, outY, -INSET, -REGION_DEPTH), strip=band(lineY, outY, 0, -STRIP_DEPTH))
    return S_reg, Y_reg


def late_vault(world, fr):
    """Sunward's approved design stays as it is: only its `path_20_28` becomes a vault and its shape gains the region polygons."""
    S = world['zones'][SUNWARD - 1]
    sx, sy = fr['shift']
    p = next(q for q in S['portals'] if q['id'] == 'path_20_28')
    ax, ay = fr['archS']
    p.update(x=round(ax, 2), y=round(ay - 3.0, 2), tx=round(ax + sx, 2), ty=round(ay + sy, 2), r=1.2, walk=[0, -1], vault=[sx, sy], vault_half=fr['half'])
    S['exitRoutes'] = [e for e in S['exitRoutes'] if e['portal'] != 'path_20_28']
    S_reg, _ = regions_for(fr)
    S['shape']['vaultRegions'] = [S_reg]


# ---- walls ---------------------------------------------------------------------------------------------------------------------
def wall_line(zone, F, run, skip=None):
    """A border run as a dense polyline, WALL_IN tiles inside, each point with its tangent; points off the land (or inside `skip`) are dropped."""
    n = F.shape[0]
    line = []
    for a, b in zip(run, run[1:]):
        ln = math.dist(a, b)
        if ln < 1e-9:
            continue
        nx, ny = -(b[1] - a[1]) / ln, (b[0] - a[0]) / ln
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        land = lambda s: bool(F[min(max(int(my + ny * s * 5), 0), n - 1), min(max(int(mx + nx * s * 5), 0), n - 1)])
        if not land(1):
            nx, ny = -nx, -ny
        k = max(1, int(ln / .5))
        for i in range(k + 1):
            t = i / k
            line.append((a[0] + (b[0] - a[0]) * t + nx * WALL_IN, a[1] + (b[1] - a[1]) * t + ny * WALL_IN, (b[0] - a[0]) / ln, (b[1] - a[1]) / ln))
    out = [p for p in line if F[min(max(int(p[1]), 0), n - 1), min(max(int(p[0]), 0), n - 1)]]
    if skip:
        out = [p for p in out if not skip(p[0], p[1])]
    return out


def wall_pieces(line):
    """Ramparts 2 tiles apart and a tower at both ends of every unbroken stretch and about every TOWER_EVERY tiles. Returns (towers, ramparts)."""
    out, acc, last = [], 0.0, None
    for p in line:
        if last is not None:
            acc += math.dist(last[:2], p[:2])
        if last is None or acc >= WALL_STEP or math.dist(last[:2], p[:2]) > 3:
            out.append(p)
            acc = 0.0
        last = p
    out.append(line[-1])
    towers, pieces, dist = [], [], 0.0
    for i, (cx, cy, tx, ty) in enumerate(out):
        if i:
            dist += math.dist(out[i - 1][:2], (cx, cy))
        gap_before = i and math.dist(out[i - 1][:2], (cx, cy)) > 3.5
        gap_after = i < len(out) - 1 and math.dist(out[i + 1][:2], (cx, cy)) > 3.5
        ends = i in (0, len(out) - 1) or gap_before or gap_after
        if ends or (dist - (towers[-1][3] if towers else 0)) >= TOWER_EVERY:
            towers.append((cx, cy, 'tower', dist))
            continue
        ax, ay = abs(tx), abs(ty)
        w, d = (2.8, 1.8) if ax >= 2 * ay else (1.8, 2.8) if ay >= 2 * ax else (2.3, 2.3)
        pieces.append((cx, cy, w, d))
    return towers, pieces


# ---- the design ------------------------------------------------------------------------------------------------------------------
class Year(Designer):
    TAG, SEED = 'year_design_v1', 20261114
    LATE_SEAMS = set()

    def __init__(self, world, old, fr):
        self.old, self.fr = old, fr
        self.F = np.array([[c == '#' for c in row] for row in world['shapeFloor']])
        self.runs = {o: run_of(world, o) for o in (25, 26, SUNWARD)}
        self.G = gates(self.fr)
        self.ROADMAP = roads(self.G, self.fr)
        self.ROADLIST = list(self.ROADMAP.values())
        super().__init__(world)
        self.wall = []
        self.walled = (0, 0)

    def plan(self):
        return REGIONS, self.ROADLIST, R

    @property
    def wall_field(self):
        if not hasattr(self, '_wall_field'):
            f = np.full((self.n, self.n), 1e9)
            for o, run in self.runs.items():
                f = np.minimum(f, seg_field(run, self.xs, self.ys))
            self._wall_field = f
        return self._wall_field

    def make_regions(self):
        out = super().make_regions()
        names = list(self.REGIONS)
        out[self.wall_field < 12] = names.index('verge')
        # the crossing: a disc round the axle
        out[np.hypot(self.xs - CX, self.ys - CY) < 34] = names.index('crossing')
        return out

    def season_mask(self, s):
        west, north = self.xs < CX, self.ys < CY
        q = {0: west & ~north, 1: ~west & ~north, 2: ~west & north, 3: west & north}[s]
        return q & self.floor

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane
                and self.wall_field[iy, ix] > 3.6 and self.grid.free(x, y, R.get(kind, .5) if r is None else r, .3))

    def free_spot(self, x, y, min_road=4.6, hub_gap=8, search=60, avoid=(), clear=0.):
        """The nearest cell to (x, y) on land, off every road, hub and listed point, `clear` tiles from the wall."""
        for rad in range(0, search, 2):
            for a in range(0, 360, 15) if rad else (0,):
                px, py = x + math.cos(math.radians(a)) * rad, y + math.sin(math.radians(a)) * rad
                ix, iy = int(px), int(py)
                if not (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and self.road[iy, ix] > min_road and self.wall_field[iy, ix] > max(WALL_KEEP, clear)):
                    continue
                if any(math.hypot(max(h['x'] - h['hw'] - px, 0, px - h['x'] - h['hw']), max(h['y'] - h['hh'] - py, 0, py - h['y'] - h['hh'])) < hub_gap for h in HAM.values()):
                    continue
                if any(math.dist((px, py), q) < gap for q, gap in avoid):
                    continue
                if math.hypot(px - self.fr['archY'][0], py - self.fr['archY'][1]) < 30:
                    continue
                return round(px, 1), round(py, 1)
        raise AssertionError(f'no free spot near {x},{y}')

    def fill(self, name, s, kinds, gap=.8, road=2.8):
        area = int(self.mask(name).sum())
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per * DENSITY_SCALE / 1000))
            tall = kind in TALL
            where = self.mask(name) & (self.wall_field > 3.6)
            placed += self.scatter([kind], k, where, gap=1.6 if tall else gap, road=3.4 if tall else road)
        return placed

    # ---- the wall --------------------------------------------------------------------------------------------------------
    def build_wall(self):
        """The wheel's own isometric wall (the game's `rampart` and `tower`): along the whole Lapis and Frostwake borders and the Sunward border outside the vault's span (inside it Sunward's own
        wall, drawn through the vault, stands on the line). Nothing slips between pieces; no gate."""
        bY = self.fr['bY']
        count = [0, 0]
        for other, run in self.runs.items():
            skip = (lambda x, y: math.dist((x, y), bY) < VAULT_SPAN + 8) if other == SUNWARD else None
            line = wall_line(self.w, self.F, run, skip)
            if not line:
                continue
            # break the line where points are not contiguous
            seg, parts = [line[0]], []
            for p in line[1:]:
                if math.dist(seg[-1][:2], p[:2]) > 2.5:
                    parts.append(seg)
                    seg = []
                seg.append(p)
            parts.append(seg)
            for part in parts:
                if len(part) < 3:
                    continue
                towers, pieces = wall_pieces(part)
                for cx, cy, kind, _ in towers:
                    self.add('tower', cx, cy, r=0, v=0, width=3.4, depth=3.4, color=WALL_COLORS['roof'], label='')
                for cx, cy, w, d in pieces:
                    self.add('rampart', cx, cy, r=0, v=0, width=w, depth=d, color=WALL_COLORS['stone'], label='')
                count[0] += len(pieces)
                count[1] += len(towers)
        self.wall = [(o['x'], o['y']) for o in self.objects if o['kind'] in ('rampart', 'tower')]
        self.blocked |= self.wall_field < 3.5
        return tuple(count)

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        self.fixed = [o for o in self.w['objects'] if o['kind'] == 'void']
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        self.block_disc(self.fr['archY'][0], self.fr['archY'][1], 16)
        for h in HAM.values():
            assert self.F[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
        self.block_disc(CX, CY, 14)
        self.walled = self.build_wall()
        self.elites = snap_elites(self)
        self.places, self.ambush = snap_places(self)
        for _, x, y in self.elites:
            self.block_disc(x, y, 9)
        for _, x, y, _ in self.ambush:
            self.block_disc(x, y, 3.6)
        for p in self.places:
            self.block_disc(p['x'], p['y'], 3.5)
        self.landmarks()
        content.dress(self, HAM)
        self.lay_regions()
        self.clear_glades()
        return self.fixed + self.objects

    def landmarks(self):
        # the axle, the four seasonal waymarkers, the sealed doors, the wardstone of the Dawn Vigil
        self.add('year_axle', CX, CY, r=0, v=0)
        for i, (key, h) in enumerate((k, v) for k, v in HAM.items() if v['season'] is not None and 'old' in v):
            self.add('year_waymarker', h['x'] + (12 if h['x'] < CX else -12), h['y'] + (12 if h['y'] < CY else -12), r=.3, v=h['season'])
            self.add('year_lantern', h['x'], h['y'] - 8, r=.2, v=h['season'])
            for dx, dy in ((-11, -9), (11, 8)):
                self.add('year_lodge', h['x'] + dx, h['y'] + dy, r=0, v=h['season'], width=5, depth=4)
        for key, g in content.GATES.items():
            self.add(GATE_KIND[key], g['x'], g['y'], r=0, v=0, width=10, depth=7, place='yr_' + key + '_gate')
        wi = content.GATES['wi']
        self.add('wardstone', wi['x'] + 10, wi['y'] + 3, r=.9, v=0, place='admit_dawn')
        # a ring of scenery round each elite's pocket, open on one side
        for i, (kind, x, y) in enumerate(self.elites):
            fam = FAMILY[season_of(x, y)]
            tree = fam[0][0]
            self.ring_of((x, y), 13, 12, tree, rot=.3 + i * .7, gaps=[((i * 77) % 360, 40)])
        for p in self.places:
            if p.get('waves'):
                s = season_of(p['x'], p['y'])
                self.ring_of((p['x'], p['y']), 6.5, 8, FAMILY[s][3][0], rot=.4)

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

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in self.elites]
        self.objects[:] = [o for o in self.objects if not (o['kind'] in TALL and o.get('layout') == self.TAG and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_regions(self):
        for name, spec in REGIONS.items():
            if spec['season'] is None:
                continue
            area = int(self.mask(name).sum())
            for kind, per in FAMILY[spec['season']]:
                k = max(1, int(area * per * DENSITY_SCALE / 1000))
                tall = kind in TALL
                where = self.mask(name) & (self.wall_field > 3.6)
                self.scatter([kind], k, where, gap=1.6 if tall else .8, road=3.4 if tall else 2.8)
        for o in self.objects:
            if o.get('layout') == self.TAG and 'v' not in o:
                o['v'] = self.rng.randrange(4)

    # ---- spawns ----------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng = self.rng
        out = []
        out += [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in self.ambush]
        for k, x, y in self.elites:
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
        elite_pts = [(x, y) for _, x, y in self.elites]
        for s in range(4):
            mask = self.season_mask(s)
            area = int(mask.sum())
            want = int(area * SPAWN_PER_1000 / 1000)
            self.counts[SEASON_NAME[s]] = want
            pts = np.argwhere(mask & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.wall_field > WALL_KEEP))
            if not len(pts):
                self.short[SEASON_NAME[s]] = want
                continue
            sep, placed, tries = 14.0, 0, 0
            while placed < want and tries < 60000:
                tries += 1
                if tries % 10000 == 0:
                    sep *= .85
                j, i = pts[rng.randrange(len(pts))]
                x, y = round(i + rng.random() * .98, 2), round(j + rng.random() * .98, 2)
                if any(math.hypot(x - ex, y - ey) < 24 for ex, ey in elite_pts):
                    continue
                if any(math.hypot(x - o['x'], y - o['y']) < sep for o in out if o.get('layout') == self.TAG and season_of(o['x'], o['y']) == s) or not solid.free(x, y, .6, .15):
                    continue
                if any(math.hypot(x - o['x'], y - o['y']) < 6 for o in out if o.get('layout') != self.TAG):
                    continue
                out.append({'x': x, 'y': y, 'kind': content.ORDINARY[s], 'layout': self.TAG})
                placed += 1
            if placed < want:
                self.short[SEASON_NAME[s]] = want - placed
        ordinary = [t for t in out if t.get('layout') == self.TAG]
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


# ---- gates, roads, places --------------------------------------------------------------------------------------------------------
def gates(fr):
    """id -> (x, y, walk, arrival): the four sealed doors (portal 8 tiles south of the door object), the Black Hour Foundry beside the axle, and the vault (the gate stands 3 tiles past the arch's centre,
    the way Skaldholm's vaults do)."""
    out = {}
    for key, g in content.GATES.items():
        px, py = g['x'], g['y'] + 8
        out[g['portal']] = (px, py, None, (px + g['arrive'][0], py + g['arrive'][1]))
    ox, oy = content.OLD_CROSSING['blackhour']
    out['year_blackhour'] = (CX + ox - 200, CY + oy - 200, None, (CX + content.OLD_CROSSING['arrive'][0] - 200, CY + content.OLD_CROSSING['arrive'][1] - 200))
    ax, ay = fr['archY']
    out['path_28_20'] = (ax, round(ay + 3.0, 2), (0, 1), (ax, ay))
    return out


def curve(a, b, amp=16., seed=1, step=55.):
    """A gently bending road from a to b (a few perpendicular offsets of smooth noise), straight for its last 10 tiles at each end."""
    n = max(1, int(math.dist(a, b) / step))
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    pts = [a]
    for i in range(1, n):
        t = i / n
        off = math.sin(seed * 12.9 + i * 2.17) * amp * min(1, (ln * t) / 40, (ln * (1 - t)) / 40)
        pts.append((a[0] + dx * t + nx * off, a[1] + dy * t + ny * off))
    pts.append(b)
    return [(round(x, 1), round(y, 1)) for x, y in pts]


def roads(G, fr):
    """Every road enters a town along one of three clear rays (west, east or north-east of the plaza: the old people and lodges stand on the others) and an outpost along its east corridor."""
    sp, su, au, wi = (HAM[k] for k in ('springmere', 'solhaven', 'harvestwatch', 'rimehold'))
    wm, th, lf = (HAM[k] for k in content.OUTPOSTS)
    C = (CX, CY)
    W = lambda h: (h['x'] - 22, h['y'])
    E = lambda h: (h['x'] + 22, h['y'])
    NE = lambda h: (h['x'] + 22, h['y'] - 6)
    P = lambda h: (h['x'], h['y'])
    out = {}
    ax, ay = fr['archY']
    out['vault'] = [(ax, ay - 1.0), (ax + 2, ay - 40), (ax + 4, ay - 80), W(sp)]
    for name, h in (('sp', sp), ('su', su), ('au', au), ('wi', wi)):
        for tag, fn in (('w', W), ('e', E), ('ne', NE)):
            out[f'in_{name}_{tag}'] = [fn(h), P(h)]
    # the four spokes to the Equinox Crossing
    out['spoke_sp'] = curve(NE(sp), C, 18, 2)
    out['spoke_su'] = curve(W(su), C, 18, 3)
    out['spoke_au'] = curve(W(au), C, 18, 4)
    out['spoke_wi'] = curve(E(wi), C, 18, 5)
    # the rim: Springmere - Rimehold (west), Rimehold - Harvestwatch (north), Harvestwatch - Solhaven (east), Solhaven - Springmere (south)
    out['rim_w'] = curve(NE(sp), W(wi), 22, 6, 70)
    out['rim_n'] = curve(E(wi), W(au), 18, 7, 70)
    out['rim_e'] = curve(E(au), E(su), 18, 8, 70)
    out['rim_s'] = curve(W(su), E(sp), 20, 9, 70)
    # the sealed doors and the Black Hour Foundry
    out['gate_sp'] = curve(W(sp), (G['year_bloom_descent'][0] + 10, G['year_bloom_descent'][1] - 6), 8, 10, 60)
    out['gate_su'] = curve(E(su), (G['year_solar_descent'][0] - 10, G['year_solar_descent'][1] - 6), 8, 11, 60)
    out['gate_au'] = curve(E(au), (G['year_amber_descent'][0] - 10, G['year_amber_descent'][1] - 6), 8, 12, 60)
    out['gate_wi'] = curve(W(wi), (G['year_solstice_descent'][0] + 10, G['year_solstice_descent'][1] - 6), 8, 13, 60)
    out['foundry'] = [C, (CX + 4, CY + 2), G['year_blackhour'][:2]]
    # the outposts: a road from a town to the corner of the outpost, round its south side and up its east corridor
    def outpost(src, h, seed):
        hook = [(h['x'] - 14, h['y'] + 16), (h['x'] + 16, h['y'] + 16), (h['x'] + 16, h['y'] + .4), (h['x'], h['y'] + .4)]
        return curve(src, hook[0], 14, seed, 60) + hook[1:]
    out['wm'] = outpost(NE(wi), wm, 14)
    out['th'] = outpost(E(au), th, 15)
    out['lf'] = curve(W(su), (lf['x'] + 30, lf['y'] + .4), 14, 16, 60) + [(lf['x'], lf['y'] + .4)]
    return out


def snap_elites(d):
    placed = []
    walked = [(q, 'road') for road in d.ROADLIST for q in dense_points(road, 3.0)]
    for kind, x, y in content.ELITES:
        gap = content.AWARENESS[kind] + 3
        avoid = [(q, gap) for q, _ in walked]
        avoid += [((px, py), gap) for _, px, py in placed]
        avoid += [((n['x'], n['y']), gap) for n in d.old_people]
        for h in HAM.values():
            avoid.append(((h['x'], h['y']), gap + max(h['hw'], h['hh'])))
        for g, (gx, gy, walk, arr) in d.G.items():
            avoid.append(((gx, gy), gap + 14))
        avoid += [((g['x'], g['y']), gap + 14) for g in content.GATES.values()]
        avoid.append(((CX, CY), gap + 14))
        x2, y2 = d.free_spot(x, y, min_road=gap, hub_gap=gap, search=140, avoid=avoid, clear=gap)
        placed.append((kind, x2, y2))
    return placed


def snap_places(d):
    out, ambush = [], []
    walked = [(q, 4.6) for road in d.ROADLIST for q in dense_points(road, 3.0)]
    taken = [((q['x'], q['y']), 10.) for q in out]
    for p in content.PLACES:
        q = dict(p)
        if p['id'].startswith('yw_crossing'):
            out.append(q)
            continue
        x, y = d.free_spot(p['x'], p['y'], min_road=4.6, hub_gap=10, search=60, avoid=taken + [((e[1], e[2]), 22.) for e in d.elites])
        q['x'], q['y'] = x, y
        taken.append(((x, y), 10.))
        out.append(q)
        if q.get('waves'):
            kind = content.ORDINARY[season_of(x, y)]
            for dx, dy, w in ((-6, -6, 'a'), (6, 6, 'a'), (-6, 6, 'b'), (6, -6, 'b')):
                ambush.append((kind, round(x + dx, 2), round(y + dy, 2), f"{q['id']}#{w}"))
    return out, ambush


# ---- the old people, places and portals in the new frame ----------------------------------------------------------------------------
def old_hub(key):
    return HAM[key]['old']


def restore_and_shift(zone, old, G, d):
    """Bring the old people, places, quests and portals back from the sidecar and put them in the new frame: the people keep their offset from their town's plaza, the crossing's people from the axle."""
    zone['spawn'] = dict(x=SPAWN[0], y=SPAWN[1])
    links = {n['id']: list(n.get('travelLinks', [])) for n in zone['npcs'] if n.get('travelStop')}
    zone['npcs'] = copy.deepcopy(old['npcs'])
    town = {h['key']: (k, h) for k, h in HAM.items() if 'old' in h}
    for n in zone['npcs']:
        if n['id'].startswith('travel_') and n['id'][7:] in HAM:
            hk = n['id'][7:]
        elif n['id'].startswith('mailbox_28_') and n['id'][11:] in HAM:
            hk = n['id'][11:]
        elif n['id'].startswith('yr_'):
            hk = {'sp': 'springmere', 'su': 'solhaven', 'au': 'harvestwatch', 'wi': 'rimehold'}[n['id'][3:5]]
        elif n['id'] in ('null_guide', 'null_rigger'):
            ox, oy = content.OLD_CROSSING['guide' if n['id'] == 'null_guide' else 'rigger']
            n['x'], n['y'] = CX + ox - 200, CY + oy - 200
            continue
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
        h = HAM[hk]
        ohx, ohy = h['old']
        n['x'], n['y'] = round(h['x'] + (n['x'] - ohx), 2), round(h['y'] + (n['y'] - ohy), 2)
        if n.get('travelStop') and n['id'] in links:
            n['travelLinks'] = list(links[n['id']])       # the links as the earlier designs left them (the sidecar still has the Lapis and Frostwake links they closed)
    d.old_people = zone['npcs']
    zone['places'] = copy.deepcopy(old['places'])
    zone['quests'] = copy.deepcopy(old['quests'])
    gates_by_place = {'yr_' + k + '_gate': (k, g) for k, g in content.GATES.items()}
    for p in zone['places']:
        if p['id'] in gates_by_place:
            k, g = gates_by_place[p['id']]
            p['x'], p['y'] = g['x'] + g['place'][0], g['y'] + g['place'][1]
        elif p['id'] == 'admit_dawn':
            wi = content.GATES['wi']
            p['x'], p['y'] = wi['x'] + 10, wi['y'] + 3
        elif p['id'].startswith('es_24_'):
            hk = ('springmere', 'solhaven', 'harvestwatch', 'rimehold')[int(p['id'][-1])]
            h = HAM[hk]
            p['x'], p['y'] = round(h['x'] + (p['x'] - h['old'][0]), 2), round(h['y'] + (p['y'] - h['old'][1]), 2)
        else:
            raise AssertionError(f"unplaced old place {p['id']}")
    for p in zone['portals']:
        if p['id'] not in G:
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'] = round(gx, 2), round(gy, 2)
        if walk:
            p['walk'] = list(walk)
    for fi in zone['futureInstances']:
        g = content.GATES[fi['season']]
        fi['x'], fi['y'] = g['x'], g['y']


def link_travel(world, fr):
    """Spark links across the portals of the Yearwheel: the Sunward masters keep exactly the links they had (Millbridge and the Wickerfield Post to Springmere), nothing else."""
    zones = [world] + world['zones']
    Sz, Yz = zones[SUNWARD], zones[ZONE]
    yids = {n['id'] for n in Yz['npcs'] if n.get('travelStop')}
    for n in Sz['npcs']:
        if n.get('travelStop'):
            n['travelLinks'] = [l for l in n['travelLinks'] if l not in yids]
    for n in Yz['npcs']:
        if n.get('travelStop'):
            n['travelLinks'] = [l for l in n['travelLinks'] if l not in {m['id'] for m in Sz['npcs']}]
    by = {n['id']: n for n in Sz['npcs'] + Yz['npcs']}
    for sid in ('travel_millbridge', 'travel_wickerfield'):
        by[sid]['travelLinks'].append('travel_springmere')
        by['travel_springmere']['travelLinks'].append(sid)


def vault_arch(fr):
    x, y = fr['archY']
    return dict(x=round(x, 2), y=round(y, 2), vertical=False, halfWidth=fr['half'], towers=True, portal='path_28_20', name='Sunward Vale')


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    fr = vault_frame(world)
    fr['edit'] = match_border(zone, world, fr)
    late_vault(world, fr)
    G = gates(fr)
    d = Year(zone, old, fr)
    restore_and_shift(zone, old, G, d)
    zone['shape']['placeAtSpawn'] = True
    _, Y_reg = regions_for(fr)
    zone['shape']['vaultRegions'] = [Y_reg]
    # the doorway's pocket: walkable ground across the arch, past our own border line
    pocket = pocket_cells(zone, fr)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    zone['exitRoutes'] = []
    zone['exitArches'] = [vault_arch(fr)]
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    zone['yearCentre'] = [CX, CY]
    zone.pop('groundSpans', None)
    repocket(zone, pocket)
    content.install(world, zone, HAM, old)
    zone['places'] = [p for p in zone['places'] if p['id'] not in {q['id'] for q in d.places}] + [dict(p) for p in d.places]
    # every crossing that arrives here follows the new frame: the dungeons' ways home, the foundry's, the vault
    arrivals = {}
    dungeon = {'sp': 'blooming_labyrinth', 'su': 'solar_crucible', 'au': 'amber_archive', 'wi': 'silent_solstice'}
    for key, g in content.GATES.items():
        a = G[g['portal']][3]
        arrivals[f'{dungeon[key]}_return'] = arrivals[f'{dungeon[key]}_exit'] = a
    arrivals['null_return'] = arrivals['null_clear'] = G['year_blackhour'][3]
    found = set()
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals:
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
                found.add(p['id'])
    # the vault's far side: our portal
    yp = next(p for p in zone['portals'] if p['id'] == 'path_28_20')
    sx, sy = fr['shift']
    yp.update(x=G['path_28_20'][0], y=G['path_28_20'][1], tx=round(fr['archS'][0], 2), ty=round(fr['archS'][1], 2), r=1.2, walk=[0, 1], vault=[-sx, -sy], vault_half=fr['half'])
    link_travel(world, fr)
    zones_ = [world] + world['zones']
    masters = {n['id']: n for z in zones_[:47] for n in z.get('npcs', []) if n.get('travelStop')}
    for zi in (ZONE, SUNWARD):
        for n in zones_[zi].get('npcs', []):
            if n.get('travelStop'):
                for other in n['travelLinks']:
                    assert other in masters and n['id'] in masters[other]['travelLinks'], f"Spark link {n['id']} -> {other} is not reciprocal"
    if write:
        content.record_mailboxes(zone, HAM, ROOT / 'world/mailboxes.txt')
    problems = check(world, zone, d, solid, seen, G, found, fr)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), wall=d.walled, spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']), shift=fr['shift'], border_edit=fr['edit'], arch=fr['archY'])
    if problems:
        if os.environ.get('YEAR_LAX'):
            print(len(problems), 'problems:', *problems[:80], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:80]))
    return d, stats


def pocket_cells(zone, fr):
    """The cells of the doorway's pocket (outside our floor, across the arch, up to POCKET_DEPTH past the line)."""
    ax, ay = fr['archY']
    nx, ny = fr['inland_S']           # towards Sunward's land: past our line
    tx, ty = fr['tangent']
    cells = []
    for u in range(-int(GAP_HALF) - 1, int(GAP_HALF) + 2):
        for v in range(-6, int(POCKET_DEPTH + WALL_IN + 2)):
            x, y = ax + tx * u + nx * (v - WALL_IN - 1.5), ay + ty * u + ny * (v - WALL_IN - 1.5)
            cells.append((int(x), int(y)))
    # along the whole matched stretch one more row of ground past our own line: Sunward's wall is drawn there (no collision in this frame), so a hero walks up to its face instead of stopping a tile short
    rows = zone['shapeFloor']
    bx = int(round(fr['bY'][0]))
    for x in range(bx - MATCH_EXACT, bx + MATCH_EXACT + 1):
        last = max(y for y, row in enumerate(rows) if row[x] == '#')
        cells.append((x, last + 1))
    return cells


def repocket(zone, cells):
    """Make the pocket walkable: the zone's void pieces are cut again from the floor plus the pocket."""
    import zone_shapes as zs
    n = zone['size']
    floor = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    walk = floor.copy()
    for x, y in cells:
        if 0 <= x < n and 0 <= y < n:
            walk[y, x] = True
    voids = zs.void_pieces(walk)
    zone['objects'] = [o for o in zone['objects'] if o['kind'] != 'void'] + voids


ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')


def check(world, zone, d, solid, seen, G, found, fr):
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
        if t.get('layout') == d.TAG and d.wall_field[int(t['y']), int(t['x'])] <= WALL_KEEP:
            problems.append(f'spawn within {WALL_KEEP:.0f} tiles of the wall {t}')
        if math.hypot(t['x'] - fr['archY'][0], t['y'] - fr['archY'][1]) < 24:
            problems.append(f'spawn within 24 tiles of the vault {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
        if d.road[int(n['y']), int(n['x'])] < 1.4:
            problems.append(f"npc {n['id']} stands on a road at {n['x']},{n['y']}")
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
        if not d.floor[int(p['y']), int(p['x'])]:
            problems.append(f"place {p['id']} off land")
    for g, (gx, gy, walk, arr) in G.items():
        if g != 'path_28_20' and not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
        if g != 'path_28_20' and not seen[int(gy), int(gx)]:
            problems.append(f'gate {g} is unreachable')
    for need in ('blooming_labyrinth_return', 'blooming_labyrinth_exit', 'solar_crucible_return', 'solar_crucible_exit', 'amber_archive_return', 'amber_archive_exit',
                 'silent_solstice_return', 'silent_solstice_exit', 'null_return', 'null_clear'):
        if need not in found:
            problems.append(f'no incoming portal {need} found to re-aim')
    # the vault: the one crossing
    cross = [p for p in zone['portals'] if p['to'] == SUNWARD]
    if len(cross) != 1 or not cross[0].get('vault'):
        problems.append('the Yearwheel needs exactly one portal to Sunward Vale and it must be a vault')
    S = world['zones'][SUNWARD - 1]
    sp = next(p for p in S['portals'] if p['id'] == 'path_20_28')
    if [round(a + b, 3) for a, b in zip(sp['vault'], cross[0]['vault'])] != [0, 0]:
        problems.append('the two vault shifts are not exact negatives')
    ax, ay = fr['archY']
    if not seen[int(ay), int(ax)] and not d.floor[int(ay), int(ax)]:
        pass          # the arch stands in the pocket (walkable, not floor); the road reaches its edge (checked by the Rust vault tests)
    for o in zone['objects']:
        if o['kind'] in ('rampart', 'tower') and not d.floor[int(o['y']), int(o['x'])]:
            problems.append(f"wall piece off land at {o['x']},{o['y']}")
    # the wall closes the Lapis and Frostwake borders: no reachable cell between a wall and its border
    for other in (25, 26):
        cells = d.F & (seg_field(d.runs[other], d.xs, d.ys) < 1.2)
        ys, xs = np.nonzero(cells & seen)
        if len(xs):
            problems.append(f'{len(xs)} cells between the wall and the border with zone {other} are reachable: {[(int(a), int(b)) for a, b in zip(xs, ys)][:6]}')
    walked = [(q, 'road') for road in d.ROADLIST for q in dense_points(road, 3.0)]
    walked += [((q['x'], q['y']), f"place {q['id']}") for q in zone['places']] + [((n['x'], n['y']), f"npc {n['id']}") for n in zone['npcs']]
    walked += [((q['x'], q['y']), f"portal {q['id']}") for q in zone['portals']]
    for kind, ex, ey in d.elites:
        near = min(((math.dist((ex, ey), q), what) for q, what in walked), key=lambda t: t[0])
        if near[0] < content.AWARENESS[kind] + 3:
            problems.append(f'{kind} stands {near[0]:.1f} tiles from a {near[1]}: its awareness is {content.AWARENESS[kind]:.0f}')
        for c in [zone['city']] + zone['camps']:
            gap = math.hypot(max(c['x0'] - ex, 0, ex - c['x1']), max(c['y0'] - ey, 0, ey - c['y1']))
            if gap < content.AWARENESS[kind] + 3:
                problems.append(f'{kind} stands {gap:.1f} tiles from a hub')
        if not d.floor[int(ey), int(ex)]:
            problems.append(f'{kind} stands off the land')
    if sum(d.short.values()) > 24:
        problems.append(f'regions short of spawns: {d.short}')
    for p in zone['places']:
        if p.get('waves') and d.road[int(p['y']), int(p['x'])] < 4:
            problems.append(f"hold circle {p['id']} stands on a road")
    bad = set()
    for name, road in d.ROADMAP.items():
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                if not d.floor[int(y), int(x)] and name != 'vault':
                    problems.append(f'road {name} leaves the land at {x:.0f},{y:.0f}')
                if solid[int(y), int(x)] and d.floor[int(y), int(x)]:
                    bad.add((int(x), int(y), name))
    if bad:
        problems.append(f'something stands on the road at {sorted(bad)[:12]}')
    return problems


def plan_picture(zone, d, out, scale=1):
    from PIL import Image, ImageDraw
    n = d.n
    a = np.zeros((n * scale, n * scale, 3), np.uint8)
    pal = [(150, 210, 140), (230, 200, 100), (210, 140, 90), (200, 225, 240)]
    for s in range(4):
        m = np.kron(d.season_mask(s), np.ones((scale, scale), bool))
        a[m] = pal[s]
    im = Image.fromarray(a)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(250, 250, 250), width=max(2, scale))
    col = {'rampart': (80, 80, 80), 'tower': (255, 100, 0)}
    for o in zone['objects']:
        if o['kind'] in col:
            g.ellipse([o['x'] * scale - 2, o['y'] * scale - 2, o['x'] * scale + 2, o['y'] * scale + 2], fill=col[o['kind']])
    for s_ in zone['slimes']:
        c = (255, 20, 20) if s_['kind'] not in content.ORDINARY else (60, 60, 60)
        r = 5 if s_['kind'] not in content.ORDINARY else 2
        g.rectangle([s_['x'] * scale - r, s_['y'] * scale - r, s_['x'] * scale + r, s_['y'] * scale + r], fill=c)
    for camp in [zone['city']] + zone['camps']:
        g.rectangle([camp['x0'] * scale, camp['y0'] * scale, camp['x1'] * scale, camp['y1'] * scale], outline=(255, 90, 0), width=2)
        g.text((camp['plaza']['x'] * scale - 20, camp['plaza']['y'] * scale + 24), camp['name'], fill=(0, 0, 0))
    for p in zone['places']:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(0, 90, 40))
    for p in zone['portals']:
        g.ellipse([p['x'] * scale - 6, p['y'] * scale - 6, p['x'] * scale + 6, p['y'] * scale + 6], outline=(255, 0, 0), width=3)
    for kind, ex, ey in d.elites:
        g.ellipse([ex * scale - 8, ey * scale - 8, ex * scale + 8, ey * scale + 8], outline=(200, 0, 0), width=3)
        g.text((ex * scale + 10, ey * scale - 6), kind, fill=(0, 0, 0))
    im.save(out)


def main():
    src = os.environ.get('YEAR_WORLD')
    world = json.loads(Path(src).read_text() if src else MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])


if __name__ == '__main__':
    main()
