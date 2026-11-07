#!/usr/bin/env python3
"""Every seam between two shaped zones carries a road across it (owner, 2026-11-07: "all the zones should have roads from to other zones").

Pure data, no server. For every seam pair among the zones that draw dirt trails:
  1. at one point of the border BOTH sides have a road touching the line (the second side measured after the seam's shift),
  2. the roads that reach a border stand on open land: no building, wall, tower, water or other obstacle under their centre line,
  3. every point of such a road is at least 0.6 tiles from a void piece (the server's walker has a radius: three Rust road tests failed on this once),
  4. no loose scenery within 2.5 tiles of such a road and no spawn within 3.4 (the designs' own clearances).

`MAP=<path>` runs it against another map.txt: the map from before the pass must FAIL (mutation check).
"""
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import seam_roads as S

world = json.loads(Path(os.environ.get('MAP', ROOT / 'world/map.txt')).read_text())
failures = []
checks = 0


def fail(msg):
    failures.append(msg)
    print('FAIL', msg)


def inside(o, x, y):
    """The point (x, y) is under the footprint of obstacle o."""
    w, d = o.get('width', 0), o.get('depth', 0)
    if o['kind'] in ('water', 'lava', 'ice') or not (w and d):
        r = o.get('r', 0)
        return r > 0 and math.hypot(x - o['x'], y - o['y']) <= r
    return abs(x - o['x']) <= w / 2 and abs(y - o['y']) <= d / 2


pairs = S.seam_pairs(world)
assert len(pairs) >= 6, f'only {len(pairs)} seam pairs found: the test would prove nothing'
for a, b, sh, pa, pb in pairs:
    za, zb = S.zone_of(world, a), S.zone_of(world, b)
    best = None
    for (x, y), _ in S.border_points(pa):
        da, db = S.road_dist(za, x, y), S.road_dist(zb, x + sh[0], y + sh[1])
        if best is None or max(da, db) < best[0]:
            best = (max(da, db), (x, y), da, db)
    checks += 1
    if best[0] > S.JOIN + .3:
        fail(f'seam {a}-{b}: at best the roads are {best[2]:.1f} / {best[3]:.1f} tiles from the border at {best[1][0]:.0f},{best[1][1]:.0f}')
        continue
    # the roads that touch this border, on each side
    for z, zone, border in ((a, za, pa), (b, zb, [(p[0] + sh[0], p[1] + sh[1]) for p in pa])):
        touching = [r for r in zone['paths'] if min(S.poly_dist(p[0], p[1], border) for p in r) <= 3.0]
        assert touching, f'seam {a}-{b}: no road of zone {z} touches the border'
        walls = [o for o in zone['objects'] if o['kind'] not in S.LOOSE and o['kind'] != 'void']
        voids = [o for o in zone['objects'] if o['kind'] == 'void']
        for road in touching:
            for p, q in zip(road, road[1:]):
                L = math.hypot(q[0] - p[0], q[1] - p[1])
                for k in range(int(L / .5) + 1):
                    x, y = p[0] + (q[0] - p[0]) * k * .5 / max(L, 1e-9), p[1] + (q[1] - p[1]) * k * .5 / max(L, 1e-9)
                    checks += 1
                    gap = next((o for o in voids if abs(x - o['x']) < o['width'] / 2 + .6 and abs(y - o['y']) < o['depth'] / 2 + .6), None)
                    if gap:
                        fail(f'zone {z}: a road comes within 0.6 tiles of a void piece at {x:.1f},{y:.1f}')
                        break
                    hit = next((o for o in walls if abs(o['x'] - x) < 8 and abs(o['y'] - y) < 8 and inside(o, x, y)), None)
                    if hit:
                        fail(f'zone {z}: a road crosses a {hit["kind"]} at {hit["x"]:.0f},{hit["y"]:.0f}')
                        break
        near_road = lambda x, y: min(S.poly_dist(x, y, r) for r in touching)
        loose = [o for o in zone['objects'] if o['kind'] in S.LOOSE and near_road(o['x'], o['y']) < 2.5 and
                 min(S.poly_dist(o['x'], o['y'], r) for r in touching if min(S.poly_dist(p[0], p[1], border) for p in r) <= 3.0) < 2.5]
        # only the stretch the pass laid is cleared; the designs' own roads were cleared by them (2.6) already
        checks += 1
        if loose:
            fail(f'zone {z}: {len(loose)} loose objects stand within 2.5 tiles of a road to the border, first {loose[0]["kind"]} at {loose[0]["x"]:.0f},{loose[0]["y"]:.0f}')
        close = [s for s in zone['slimes'] if near_road(s['x'], s['y']) < 3.4]
        checks += 1
        if close:
            fail(f'zone {z}: {len(close)} spawns stand within 3.4 tiles of a road to the border, first {close[0]["kind"]} at {close[0]["x"]:.0f},{close[0]["y"]:.0f}')

print(f'{checks} checks, {len(failures)} failures, {len(pairs)} seam pairs')
sys.exit(1 if failures else 0)
