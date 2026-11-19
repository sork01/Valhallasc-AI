#!/usr/bin/env python3
"""Generate validated candidate waters; the live game randomly spawns rich spots.

Run after zone_shapes.py apply. Never move scenery, quests or people. Each
candidate retains a shore/facing witness so Rust can verify its real cast.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[1]
HABITATS = {0: 'Shore', 1: 'Lava', 2: 'Cold', 3: 'Swamp', 6: 'Forest',
            19: 'Shore', 20: 'Forest', 22: 'Jungle', 25: 'Oasis',
            26: 'Cold', 28: 'Spring', 45: 'Lava'}
SURFACES = {'water', 'seafoam', 'jungle_water', 'year_spring_pool',
            'frostwake_frozen_pool', 'jade_pool', 'lapis_oasis', 'lava', 'ew_lava'}
MIN_RADIUS = {'seafoam', 'year_spring_pool', 'frostwake_frozen_pool', 'lapis_oasis'}
SCALE = 2


def radius(obj):
    r = obj.get('r', 0)
    return max(1., r) if obj['kind'] in MIN_RADIUS else r


def walkable(area):
    """Conservative half-tile grid, including circle/rectangle and point obstacles.

    Extra half-cell clearance keeps the entire walk between adjacent centres
    outside the hero's expanded collision footprints, not just the centres.
    """
    n = area['size'] * SCALE
    free = np.ones((n, n), dtype=bool)
    padding = .3 + .5 / SCALE
    for o in area['objects']:
        rect = o.get('width', 0) > 0 and o.get('depth', 0) > 0
        hx, hy = ((o['width'] / 2 + padding, o['depth'] / 2 + padding) if rect
                  else (o.get('r', 0) + padding,) * 2)
        x0, x1 = max(0, int((o['x'] - hx) * SCALE)), min(n, math.ceil((o['x'] + hx) * SCALE))
        y0, y1 = max(0, int((o['y'] - hy) * SCALE)), min(n, math.ceil((o['y'] + hy) * SCALE))
        if x0 >= x1 or y0 >= y1:
            continue
        xs = (np.arange(x0, x1) + .5) / SCALE - o['x']
        ys = (np.arange(y0, y1) + .5) / SCALE - o['y']
        solid = ((abs(xs)[None, :] < hx) & (abs(ys)[:, None] < hy) if rect
                 else xs[None, :] ** 2 + ys[:, None] ** 2 < hx ** 2)
        free[y0:y1, x0:x1] &= ~solid
    free[:2] = free[-2:] = False
    free[:, :2] = free[:, -2:] = False
    components, _ = label(free)
    spawn = area['spawn']
    # Saved spawns can touch a prop; choose the nearest free centre within 3 tiles.
    y, x = np.nonzero(free)
    ds = ((x + .5) / SCALE - spawn['x']) ** 2 + ((y + .5) / SCALE - spawn['y']) ** 2
    k = int(ds.argmin())
    if ds[k] > 9:
        raise ValueError(f"{area['name']}: spawn has no nearby walkable ground")
    return components == components[y[k], x[k]]


def segment_distance(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy) / max(1e-12, dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx, y-a[1]-t*dy)


def clear_of_hubs_and_seams(area, x, y):
    hubs = ([area['city']] if area.get('city') else []) + area.get('camps', [])
    for hub in hubs:
        dx = max(hub['x0'] - x, 0, x - hub['x1'])
        dy = max(hub['y0'] - y, 0, y - hub['y1'])
        if math.hypot(dx, dy) < 10:
            return False
    # Whole border, not just the portal midpoint: neighbouring scenery must not pop.
    for edge in area.get('shape', {}).get('edges', []):
        if edge.get('kind') == 'shared' and any(p.get('seam') and p.get('to') == edge.get('other') for p in area.get('portals', [])):
            points = edge.get('points', [])
            if any(segment_distance(x, y, a, b) < 18 for a, b in zip(points, points[1:])):
                return False
    for portal in area.get('portals', []):
        if portal.get('seam') and math.hypot(x-portal['x'], y-portal['y']) < 18:
            return False
    return True


def cast(pools, shore, facing):
    """Same facing-ray circle intersection as world/fishing.rs (dock not needed)."""
    nearest = None
    for o in pools:
        dx, dy = o['x'] - shore['x'], o['y'] - shore['y']
        r = radius(o)
        if math.hypot(dx, dy) < r:
            return None
        along = dx*facing['x'] + dy*facing['y']
        square = r*r - (dx*facing['y']-dy*facing['x']) ** 2
        if square <= 0:
            continue
        start, end = along - math.sqrt(square), along + math.sqrt(square)
        lo, hi = max(start, 3), min(end, 6)
        if 0 <= start <= 4 and lo < hi and (nearest is None or start < nearest[0]):
            d = (lo + hi) / 2
            nearest = start, dict(x=shore['x']+facing['x']*d, y=shore['y']+facing['y']*d)
    return nearest[1] if nearest else None


def generate(area, zone):
    reachable = walkable(area)
    pools = [o for o in area['objects'] if o['kind'] in SURFACES
             and (o['kind'] in ('lava', 'ew_lava')) == (HABITATS[zone] == 'Lava')]
    candidates = []
    for o in pools:
        for k in range(32):
            angle = k * math.tau / 32
            x, y = o['x'] + math.cos(angle)*(radius(o)+1.4), o['y'] + math.sin(angle)*(radius(o)+1.4)
            ix, iy = int(x*SCALE), int(y*SCALE)
            if not (0 <= ix < reachable.shape[1] and 0 <= iy < reachable.shape[0] and reachable[iy, ix]):
                continue
            shore = dict(x=(ix+.5)/SCALE, y=(iy+.5)/SCALE)
            dx, dy = o['x']-shore['x'], o['y']-shore['y']
            d = math.hypot(dx, dy)
            facing = dict(x=dx/d, y=dy/d)
            bobber = cast(pools, shore, facing)
            if not bobber or not all(clear_of_hubs_and_seams(area, **p) for p in (shore, bobber)):
                continue
            if any(math.hypot(bobber['x']-p['x'], bobber['y']-p['y']) < 1.1 for p in candidates):
                continue
            candidates.append(dict(zone=zone, habitat=HABITATS[zone], **bobber, shore=shore, facing=facing))
    # Farthest-first spreads the safe candidates across distinct waters.
    chosen = []
    while candidates and len(chosen) < 64:
        if chosen:
            best = max(range(len(candidates)), key=lambda i: min(
                math.hypot(candidates[i]['x']-p['x'], candidates[i]['y']-p['y']) for p in chosen))
        else:
            best = 0
        p = candidates.pop(best)
        if chosen and min(math.hypot(p['x']-q['x'], p['y']-q['y']) for q in chosen) < 1.6:
            break
        p['id'] = f'fish_{zone}_{len(chosen)+1:02}'
        chosen.append(p)
    if len(chosen) < 2:
        raise ValueError(f"{area['name']}: only {len(chosen)} reachable waters, need 2 for random spawning")
    return chosen


def build(world):
    areas = [world, *world['zones']]
    out = []
    for z in HABITATS:
        points = generate(areas[z], z)
        print(f'{z}: {areas[z]["name"]}: {len(points)} candidate waters', flush=True)
        out.extend(points)
    return out


def install(world, points):
    for area in [world, *world['zones']]:
        area.pop('fishingSpots', None)
    for zone in HABITATS:
        [world, *world['zones']][zone]['fishingSpots'] = [p for p in points if p['zone'] == zone]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'world/map.txt'
    world = json.loads(path.read_text())
    points = build(world)
    text = json.dumps(points, indent=2, ensure_ascii=False) + '\n'
    file = ROOT / 'world/fishing-spots.txt'
    if args.check:
        if not file.exists() or file.read_text() != text:
            raise SystemExit('Fishing candidate waters are stale')
        for zone in HABITATS:
            if [world, *world['zones']][zone].get('fishingSpots') != [p for p in points if p['zone'] == zone]:
                raise SystemExit(f'Zone {zone}: fishing overlay missing')
    if args.write:
        file.write_text(text)
        install(world, points)
        path.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
