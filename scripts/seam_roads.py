#!/usr/bin/env python3
"""Every seam between two shaped zones carries a road across it (owner, 2026-11-07: "all the zones should have roads from and to other zones, like now
I see no road from meadow to gloamfen").

A pass that runs LAST in `zone_shapes.py apply` (after the designs, the Skaldholm rebuild and the dock), so no design's seeded scatter moves. For each seam
pair of zones that draw dirt trails from `paths` it:

1. finds the crossing: the point of the border where the cheapest walk from one side's road network, plus the cheapest walk from the other side's, is
   smallest (a Dijkstra field from every road cell over the land that is neither water, lava, a building nor a wall),
2. lays one polyline on each side from the nearest road to that point and on 2.2 tiles past it, so the ground each side draws (and the neighbour's ground
   drawn across the seam, `groundSample`) overlaps on the line,
3. clears only what stands in the way: loose scenery within `CLEAR` tiles of the new road goes, spawns within `SPAWN_CLEAR` are pushed aside.

Nothing else of an approved design is touched. A seam that already has a road on both sides at the same point is left alone (idempotent).
`audit(world)` is the pure-data check the test uses: it lists each pair with the distance of each side's road to the border at the best crossing."""
import heapq
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

SEAM_MARGIN = 2.4            # land runs this far past a border (zone_shapes.SEAM_MARGIN)
EXTEND = 2.2                 # a road runs this far past the border
PORTAL_PULL = 0.5            # cost per tile between the crossing and each side's own seam portal (quest arrows and markers aim at the portal's point)
END_GAP = 14.0              # a crossing stands this far (along the border) from either end of it: ends are corners, coasts and Skaldholm's wall
JOIN = 1.2                   # a road within this of the border (both sides, same point) is a crossing already
CLEAR = 2.6                  # loose scenery stands at least this far from a road's centre line (the designs use 2.6)
SPAWN_CLEAR = 3.6            # spawns stand at least this far from a road (the designs use 3.5)
VOID_GAP = 0.7              # a road keeps this far from a void edge (the walker's body has a radius)
HALF = 1.3                   # half the width of the dirt, plus a hair: the routing keeps hard obstacles this far from the centre line
ELITE_CLEAR = 17.0           # awareness (up to 14) + 3: an elite stands this far from every road (Wyrdwood's rule, applied everywhere)

# Scenery that may be removed from a road's way. Everything else with a footprint is an obstacle the road goes round.
LOOSE = {'tree', 'bush', 'rock', 'wildflowers', 'hawthorn_bush', 'birch_tree', 'oak_tree', 'apple_tree', 'willow_tree', 'cairn_boulder',
         'cairn_pebble', 'flowers', 'haystack', 'bones', 'spire', 'thicket', 'pine', 'glowmoss', 'sporefern', 'gloomstalk', 'moonstone', 'mooncaps',
         'ew_basalt', 'crag'}          # (lamps light the camps and outposts: obstacles, never scatter)
# Zones that draw dirt trails from `paths` (not the cities, the sky or the sea). Zone 6 is the Wyrdwood, 13 Astralhollow, 14 the Prismwaste, 15 the Obsidian Orrery, 16 the Moonspore Canopy, 19 the Stormglass Flats, 21 the Ribbonwild, 22 the Tanglecrown, 45 Emberwake Caldera.
ROAD_ZONES = (0, 1, 2, 3, 6, 13, 14, 15, 16, 19, 21, 22, 45)


def zone_of(world, z):
    return world if z == 0 else world['zones'][z - 1]


def seam_pairs(world, zones=ROAD_ZONES):
    """[(a, b, shift a->b, border polyline in a's frame, border polyline in b's frame)] for a < b, both in `zones`."""
    out = []
    for a in zones:
        for p in zone_of(world, a).get('portals', []):
            b = p.get('to')
            if not p.get('seam') or b not in zones or b <= a:
                continue
            back = [q for q in zone_of(world, b).get('portals', []) if q.get('seam') and q.get('to') == a]
            if not back:
                continue
            sh = p['seam']['shift']
            assert [-sh[0], -sh[1]] == list(back[0]['seam']['shift']), f'seam {a}-{b}: the two shifts disagree'
            out.append((a, b, tuple(sh), [tuple(q) for q in p['seam']['points']], [tuple(q) for q in back[0]['seam']['points']]))
    return out


def seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def poly_dist(px, py, poly):
    return min(seg_dist(px, py, a, b) for a, b in zip(poly, poly[1:]))


def road_dist(zone, px, py):
    d = 1e9
    for road in zone.get('paths', []):
        for a, b in zip(road, road[1:]):
            d = min(d, seg_dist(px, py, a, b))
    return d


def border_points(poly, step=1.0, end_gap=0.0):
    """Points along a border polyline, `step` tiles apart, each with the unit tangent; none within `end_gap` tiles (along the line) of either end."""
    pts = []
    for a, b in zip(poly, poly[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        for k in range(max(int(L / step), 1)):
            t = k * step / L
            pts.append(((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), ((b[0] - a[0]) / L, (b[1] - a[1]) / L)))
    pts.append((poly[-1], pts[-1][1]))
    if end_gap:
        total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(poly, poly[1:]))
        keep = [p for k, p in enumerate(pts) if end_gap <= k * step <= total - end_gap]
        pts = keep or pts
    return pts


def audit(world, zones=ROAD_ZONES):
    """Each pair's best crossing by straight distance: (a, b, side-a distance, side-b distance), distance from a road to the border point."""
    rows = []
    for a, b, sh, pa, pb in seam_pairs(world, zones):
        za, zb = zone_of(world, a), zone_of(world, b)
        best = None
        for (x, y), _ in border_points(pa):
            da, db = road_dist(za, x, y), road_dist(zb, x + sh[0], y + sh[1])
            if best is None or da + db < best[0]:
                best = (da + db, da, db, (x, y))
        rows.append((a, b, round(best[1], 2), round(best[2], 2), best[3]))
    return rows


# ---- the walk grid of one zone --------------------------------------------------------------------------------------
class Land:
    def __init__(self, zone):
        self.zone = zone
        n = self.n = zone['size']
        self.ys, self.xs = np.mgrid[0:n, 0:n] + .5
        self.floor = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
        # The land a body can stand on is what no `void` piece covers (the voids are built from the floor plus the seam margin, so this IS the
        # margin, exactly); a road keeps VOID_GAP tiles from a void edge, as the server's body has a radius.
        void = np.zeros((n, n), bool)
        for o in zone['objects']:
            if o['kind'] == 'void':
                void |= (abs(self.xs - o['x']) <= o['width'] / 2 + VOID_GAP) & (abs(self.ys - o['y']) <= o['depth'] / 2 + VOID_GAP)
        self.walk = ~void
        self.hard = np.zeros((n, n), bool)
        self.soft = np.zeros((n, n))            # scenery the road would clear: a small cost, so it prefers open ground
        for o in zone['objects']:
            k = o['kind']
            if k == 'void':
                continue
            x, y = o['x'], o['y']
            w, d = o.get('width', 0), o.get('depth', 0)
            if k in LOOSE:
                self._disc(self.soft, x, y, o.get('r', 0) + 1.0, .6)
            elif w and d and k not in ('water', 'lava', 'ice'):
                self.hard[self._box(x, y, w / 2 + HALF, d / 2 + HALF)] = True
            else:
                r = o.get('r', 0)
                if k in ('water', 'lava', 'ice'):
                    r += .9                     # no fords here: the designs placed their own where a road had to cross
                elif r > 0:
                    r += HALF
                if r > 0:
                    self.hard[np.hypot(self.xs - x, self.ys - y) <= r] = True
        # people and places are not obstacles, but a road should not run over a person
        self.people = np.zeros((n, n))
        for npc in zone.get('npcs', []):
            self._disc(self.people, npc['x'], npc['y'], 1.6, 25.0)
        self.walk &= ~self.hard

    def _near(self, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = np.clip(((self.xs - a[0]) * dx + (self.ys - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
        return np.hypot(self.xs - a[0] - t * dx, self.ys - a[1] - t * dy)

    def _box(self, x, y, hw, hh):
        return (abs(self.xs - x) <= hw) & (abs(self.ys - y) <= hh)

    def _disc(self, grid, x, y, r, add):
        x0, x1 = max(int(x - r) - 1, 0), min(int(x + r) + 2, self.n)
        y0, y1 = max(int(y - r) - 1, 0), min(int(y + r) + 2, self.n)
        sub = np.hypot(self.xs[y0:y1, x0:x1] - x, self.ys[y0:y1, x0:x1] - y) <= r
        grid[y0:y1, x0:x1][sub] += add

    def cost(self):
        c = 1.0 + self.soft + self.people
        # keep the road off spawns and elites where a detour is cheap (they are moved afterwards if it is not)
        for s in self.zone.get('slimes', []):
            self._disc(c, s['x'], s['y'], 3.0, 1.5)
        return c

    def road_cells(self):
        """Cells whose centre lies on an existing road."""
        m = np.zeros((self.n, self.n), bool)
        for road in self.zone.get('paths', []):
            for a, b in zip(road, road[1:]):
                m |= self._near(a, b) <= .75
        return m & self.walk

    def dijkstra(self, sources, cost):
        """Cheapest walk (8 neighbours) from the `sources` mask to every walkable cell: (distance, parent index)."""
        n = self.n
        dist = np.full(n * n, np.inf)
        parent = np.full(n * n, -1, dtype=np.int64)
        walk = self.walk.ravel()
        flat = cost.ravel()
        heap = []
        for j, i in np.argwhere(sources):
            dist[j * n + i] = 0.0
            heap.append((0.0, int(j * n + i)))
        heapq.heapify(heap)
        steps = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0), (-1, -1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (1, 1, 1.4142)]
        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            j, i = divmod(u, n)
            for dj, di, w in steps:
                jj, ii = j + dj, i + di
                if not (0 <= jj < n and 0 <= ii < n):
                    continue
                v = jj * n + ii
                if not walk[v]:
                    continue
                if dj and di and not (walk[j * n + ii] and walk[jj * n + i]):
                    continue                            # no cutting a corner of an obstacle
                nd = d + w * (flat[v] + flat[u]) / 2
                if nd < dist[v]:
                    dist[v] = nd
                    parent[v] = u
                    heapq.heappush(heap, (nd, v))
        return dist.reshape(n, n), parent

    def open_at(self, x, y):
        i, j = int(x), int(y)
        return 0 <= i < self.n and 0 <= j < self.n and bool(self.walk[j, i])

    def trace(self, parent, j, i):
        """Cell centres from (i, j) back to its source."""
        pts = []
        u = j * self.n + i
        while u != -1:
            jj, ii = divmod(u, self.n)
            pts.append((ii + .5, jj + .5))
            u = parent[u]
        return pts

    def clear(self, a, b):
        """The straight segment a-b crosses no hard cell and leaves the walkable land nowhere."""
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        for k in range(int(L / .4) + 2):
            t = min(k * .4 / max(L, 1e-9), 1.0)
            x, y = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
            i, j = int(x), int(y)
            if not (0 <= i < self.n and 0 <= j < self.n) or not self.walk[j, i]:
                return False
        return True


def simplify(land, pts):
    """Fewest corners that keep every segment on clear land: from each point jump to the furthest point in line of sight."""
    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not land.clear(pts[i], pts[j]):
            j -= 1
        out.append(pts[j])
        i = j
    return out


# ---- one pair -------------------------------------------------------------------------------------------------------
def plan_pair(world, lands, a, b, sh, pa, pb):
    """The crossing and the road for each side: {'cross': (x, y) in a's frame, 'a': polyline or None, 'b': polyline or None}."""
    za, zb = zone_of(world, a), zone_of(world, b)
    fields = {}
    for z, land in ((a, lands[a]), (b, lands[b])):
        fields[z] = land.dijkstra(land.road_cells(), land.cost())
    best = None
    # where each zone's own seam portal stands, in a's frame
    pts = [(p['x'], p['y']) for p in za['portals'] if p.get('seam') and p['to'] == b] + \
          [(p['x'] - sh[0], p['y'] - sh[1]) for p in zb['portals'] if p.get('seam') and p['to'] == a]
    for (x, y), tang in border_points(pa, end_gap=END_GAP):
        # the border is the line between the two lands: step onto each side's walkable cell nearest to it
        ca = nearest_walk(lands[a], x, y)
        cb = nearest_walk(lands[b], x + sh[0], y + sh[1])
        if ca is None or cb is None:
            continue
        cost = fields[a][0][ca[1], ca[0]] + fields[b][0][cb[1], cb[0]]
        if not math.isfinite(cost):
            continue
        cost += PORTAL_PULL * sum(math.hypot(x - q[0], y - q[1]) for q in pts)
        # the road is already across if both roads touch the line here
        if best is None or cost < best[0]:
            best = (cost, (x, y), tang, ca, cb)
    assert best, f'seam {a}-{b}: no point of the border can be walked to from both roads'
    cost, (x, y), tang, ca, cb = best
    out = {'cross': (x, y), 'cost': round(cost, 1)}
    # which way is out of a's land: the side of the border whose cells are not a's floor
    nx, ny = -tang[1], tang[0]
    fa = lands[a].floor
    def inside(px, py):
        i, j = int(px), int(py)
        return 0 <= i < fa.shape[1] and 0 <= j < fa.shape[0] and fa[j, i]
    if inside(x + nx * 3, y + ny * 3) and not inside(x - nx * 3, y - ny * 3):
        nx, ny = -nx, -ny
    for z, zone, land, c, at, out_dir in ((a, za, lands[a], ca, (x, y), (nx, ny)), (b, zb, lands[b], cb, (x + sh[0], y + sh[1]), (-nx, -ny))):
        if road_dist(zone, at[0], at[1]) <= JOIN:
            out[z] = None
            continue
        pts = land.trace(fields[z][1], c[1], c[0])[::-1]          # road ... crossing cell
        pts = simplify(land, pts)
        if len(pts) > 1 and math.hypot(pts[-1][0] - at[0], pts[-1][1] - at[1]) < 1.6:
            pts = pts[:-1]                                         # the last cell is the border point's neighbour: go straight to the point
        pts = [(float(p[0]), float(p[1])) for p in pts]
        join = tuple(float(v) for v in nearest_road_point(zone, pts[0]))
        line = ([join] + pts[1:] if math.hypot(join[0] - pts[0][0], join[1] - pts[0][1]) < 1.5 else [join] + pts) + [at]
        reach = 0.0
        while reach + .25 <= EXTEND and land.open_at(at[0] + out_dir[0] * (reach + .25), at[1] + out_dir[1] * (reach + .25)):
            reach += .25
        if reach >= .5:
            line.append((at[0] + out_dir[0] * reach, at[1] + out_dir[1] * reach))
        out[z] = [[round(p[0], 2), round(p[1], 2)] for p in dedupe(line)]
    return out


def dedupe(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > .05:
            out.append(p)
    return out


def nearest_walk(land, x, y, reach=3.2):
    best = None
    for dj in range(-4, 5):
        for di in range(-4, 5):
            i, j = int(x) + di, int(y) + dj
            if 0 <= i < land.n and 0 <= j < land.n and land.walk[j, i]:
                d = math.hypot(i + .5 - x, j + .5 - y)
                if d <= reach and (best is None or d < best[0]):
                    best = (d, i, j)
    return None if best is None else (best[1], best[2])


def nearest_road_point(zone, p):
    best = (1e9, p)
    for road in zone.get('paths', []):
        for a, b in zip(road, road[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = dx * dx + dy * dy
            t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
            q = (a[0] + t * dx, a[1] + t * dy)
            d = math.hypot(p[0] - q[0], p[1] - q[1])
            if d < best[0]:
                best = (d, q)
    return best[1]


# ---- clearing what stands on the new road ---------------------------------------------------------------------------
def clear_road(zone, roads, elite_kinds, old_roads=()):
    gone, moved, hopped = {}, 0, 0
    # an elite is a kind of elite-power.txt with one or two spawns in the zone (the ordinary monsters of the late grid are in that file too)
    count = {}
    for s in zone['slimes']:
        count[s['kind']] = count.get(s['kind'], 0) + 1
    elite_kinds = {k for k in elite_kinds if 0 < count.get(k, 0) <= 2}
    keep = []
    for o in zone['objects']:
        if o['kind'] in LOOSE and any(poly_dist(o['x'], o['y'], r) < CLEAR + o.get('r', 0) * .5 for r in roads):
            gone[o['kind']] = gone.get(o['kind'], 0) + 1
            continue
        keep.append(o)
    zone['objects'] = keep
    land = Land(zone)
    for s in zone['slimes']:
        near = [(poly_dist(s['x'], s['y'], r), r) for r in roads]
        d, r = min(near, key=lambda t: t[0])
        # the wide clearance is a rule only where the zone's design kept it (an elite that already stood by a road is left to the ordinary one)
        wide = s['kind'] in elite_kinds and all(poly_dist(s['x'], s['y'], q) >= ELITE_CLEAR - .5 for q in old_roads)
        need = ELITE_CLEAR if wide else SPAWN_CLEAR
        if d >= need:
            continue
        # step away from the road, perpendicular, to the nearest clear ground
        best = None
        for ang in range(0, 360, 20):
            for dist in (need + 0.4, need + 3, need + 6, need + 10):
                x, y = s['x'] + math.cos(math.radians(ang)) * (dist - d), s['y'] + math.sin(math.radians(ang)) * (dist - d)
                i, j = int(x), int(y)
                if 0 <= i < land.n and 0 <= j < land.n and land.floor[j, i] and not land.hard[j, i] \
                        and min(poly_dist(x, y, q) for q in roads) >= need and (best is None or dist - d < best[0]):
                    best = (dist - d, x, y)
                    break
        if best:
            s['x'], s['y'] = round(best[1], 2), round(best[2], 2)
            moved += 1
        else:
            hopped += 1
    return gone, moved, hopped


def elite_kinds():
    p = ROOT / 'world/elite-power.txt'
    try:
        return set(json.loads(p.read_text()))
    except Exception:
        return set()


def build(world, zones=ROAD_ZONES, write=True):
    """Lay a road across every seam among `zones`; returns a report line per pair."""
    lands = {z: Land(zone_of(world, z)) for z in zones}
    elites = elite_kinds()
    report = []
    for a, b, sh, pa, pb in seam_pairs(world, zones):
        plan = plan_pair(world, lands, a, b, sh, pa, pb)
        line = f'{a}-{b} crossing ({plan["cross"][0]:.0f},{plan["cross"][1]:.0f}) cost {plan["cost"]}'
        for z in (a, b):
            road = plan.get(z)
            if road is None:
                line += f' | {z}: already there'
                continue
            zone = zone_of(world, z)
            if write:
                old = [list(map(tuple, r)) for r in zone['paths']]
                zone['paths'].append(road)
                gone, moved, hopped = clear_road(zone, [road], elites, old)
                lands[z] = Land(zone)
                line += f' | {z}: {len(road)} points, cleared {sum(gone.values())} objects, moved {moved} spawns' + (f', {hopped} spawns stay' if hopped else '')
            else:
                line += f' | {z}: {len(road)} points'
        report.append(line)
    return report


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'world/map.txt'
    w = json.loads(path.read_text())
    if '--audit' in sys.argv:
        for row in audit(w):
            print(row)
    else:
        for line in build(w, write=False):
            print(line)
