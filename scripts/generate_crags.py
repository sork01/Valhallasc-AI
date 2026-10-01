#!/usr/bin/env python3
"""Writes the Emberfall Crags (zone 1) and its gate into world/map.txt, then checks it.

Layout: four lava rivers cross a 96x96 map, each with one ford, so the way north zigzags between
difficulty bands (south = Cinder Wisps, then Magma Spiders, Ash Wraiths, Basalt Golems). The meadow
gains a stone gate at the end of its north road; two blue-slime spawns that stood in front of it
move clear. Re-running replaces zone 1 and the gate; world/map.txt stays the source of truth, so
hand edits made after running this script are lost on the next run. Seeded, so the output is stable.
Afterwards: node scripts/sync-world.cjs, then rebuild Rust.
"""
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
SIZE = 96
ARRIVAL = (48.0, 86.5)             # where the meadow gate drops you
RETURN_GATE = (48.0, 91.0)         # the way back
MEADOW_GATE = (54.0, 9.0)
MEADOW_ARRIVAL = (54.0, 13.5)
# (centre y, wobble, wobble phase, ford centre x): each river runs the whole width but for one ford.
RIVERS = [(68, 2.0, 0.0, 20), (52, 2.0, 1.0, 74), (36, 2.0, 2.0, 12), (20, 2.0, 3.0, 82)]
FORD = 4.2                         # half width of every ford
BANDS = [  # kind, count, y range
    ('wisp', 8, (54, 66)),
    ('spider', 7, (38, 50)),
    ('wraith', 6, (22, 34)),
    ('golem', 5, (6, 18)),
]


def river_y(river, x):
    y, amp, phase, _ = river
    return y + amp * math.sin(x / 9 + phase)


def dist_to_trail(trail, x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(trail, trail[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(x - ax - dx * t, y - ay - dy * t))
    return best


def build(rng, meadow_objects):
    lava = []
    for river in RIVERS:
        ford = river[3]
        x = 0.4
        while x < SIZE:
            if abs(x - ford) > FORD:
                y = river_y(river, x) + rng.uniform(-.3, .3)
                lava.append({'kind': 'lava', 'x': round(x, 2), 'y': round(y, 2), 'r': round(rng.uniform(1.25, 1.5), 2), 'v': rng.randrange(4)})
            x += 1.3
    trail = [(48, 90), (46, 80), (32, 74), (20, river_y(RIVERS[0], 20)), (24, 60), (50, 57), (74, river_y(RIVERS[1], 74)), (66, 44),
             (40, 42), (12, river_y(RIVERS[2], 12)), (20, 28), (50, 26), (82, river_y(RIVERS[3], 82)), (76, 12), (56, 9)]
    objects = list(lava)
    # The return gate: two posts, drawn as part of the gate itself.
    for dx in (-1.5, 1.5):
        objects.append({'kind': 'post', 'x': RETURN_GATE[0] + dx, 'y': RETURN_GATE[1], 'r': 0.45, 'v': 0})
    spawns = []
    for kind, count, (y0, y1) in BANDS:
        for _ in range(count):
            for _ in range(4000):
                x, y = rng.uniform(5, SIZE - 5), rng.uniform(y0, y1)
                if (all(math.hypot(x - o['x'], y - o['y']) > o['r'] + 2.6 for o in objects)
                        and all(math.hypot(x - s['x'], y - s['y']) > 7 for s in spawns)
                        and min(abs(x - r[3]) for r in RIVERS) > 6):
                    spawns.append({'x': round(x, 2), 'y': round(y, 2), 'kind': kind})
                    break
            else:
                raise SystemExit(f'no room for a {kind}')
    # Scenery, kept off the trail, the camp, the fords and every spawn.
    decor = [('rock', 46, .4), ('tree', 26, .42), ('bush', 20, .3), ('spire', 16, .5)]
    for kind, count, radius in decor:
        placed = 0
        for _ in range(20000):
            if placed == count:
                break
            x, y = rng.uniform(2, SIZE - 2), rng.uniform(2, SIZE - 2)
            if (dist_to_trail(trail, x, y) < 2.2 or math.hypot(x - ARRIVAL[0], y - 88) < 7
                    or any(math.hypot(x - o['x'], y - o['y']) < o['r'] + radius + 1.6 for o in objects)
                    or any(math.hypot(x - s['x'], y - s['y']) < 2.6 for s in spawns)
                    or any(abs(x - r[3]) < FORD + 2 and abs(y - river_y(r, x)) < 5 for r in RIVERS)):
                continue
            objects.append({'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': radius, 'v': rng.randrange(4)})
            placed += 1
        assert placed == count, f'only {placed} {kind}'
    zone = {
        'name': 'Emberfall Crags', 'theme': 'ember', 'size': SIZE, 'levels': [5, 10],
        'spawn': {'x': ARRIVAL[0], 'y': ARRIVAL[1]},
        'paths': [[[round(x, 1), round(y, 1)] for x, y in trail]],
        'objects': objects, 'slimes': spawns, 'npcs': [], 'quests': [], 'city': None,
        'portals': [{'id': 'meadow_gate', 'name': 'the Meadow Gate', 'x': RETURN_GATE[0], 'y': RETURN_GATE[1], 'r': 1.1,
                     'to': 0, 'tx': MEADOW_ARRIVAL[0], 'ty': MEADOW_ARRIVAL[1]}],
    }
    return zone


def reachable(zone):
    """Grid flood fill with the player's radius: every spawn and the gate must connect to the arrival."""
    step, margin = .5, .62
    n = int(SIZE / step)
    blocked = [[False] * n for _ in range(n)]
    for j in range(n):
        for i in range(n):
            x, y = (i + .5) * step, (j + .5) * step
            if x < .7 or y < .7 or x > SIZE - .7 or y > SIZE - .7:
                blocked[j][i] = True
                continue
            blocked[j][i] = any(math.hypot(x - o['x'], y - o['y']) < o['r'] + margin - .3 for o in zone['objects'])
    start = (int(ARRIVAL[0] / step), int(ARRIVAL[1] / step))
    seen = {start}
    queue = [start]
    for i, j in queue:
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < n and 0 <= b < n and (a, b) not in seen and not blocked[b][a]:
                seen.add((a, b))
                queue.append((a, b))
    targets = [(s['x'], s['y'], s['kind']) for s in zone['slimes']] + [(RETURN_GATE[0], RETURN_GATE[1] - 2, 'gate')]
    missing = [t for t in targets if (int(t[0] / step), int(t[1] / step)) not in seen]
    return missing


def main():
    raw = PATH.read_text()
    meadow = json.loads(raw)
    assert json.dumps(meadow, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    rng = random.Random(20261001)
    # Remove anything an earlier run added to the meadow.
    meadow['objects'] = [o for o in meadow['objects'] if o['kind'] != 'post']
    meadow.pop('zones', None)
    meadow.pop('portals', None)
    meadow['name'] = 'Greenmeadow'
    # Blue slimes that stood in front of the gate move to the nearest clear spot.
    for s in meadow['slimes']:
        if min(math.hypot(s['x'] - px, s['y'] - py) for px, py in (MEADOW_GATE, MEADOW_ARRIVAL)) < 9.5 and s['kind'] != 'beetle':
            ox, oy = s['x'], s['y']
            best = None
            for _ in range(3000):
                x, y = ox + rng.uniform(-14, 14), oy + rng.uniform(-14, 14)
                if (min(math.hypot(x - px, y - py) for px, py in (MEADOW_GATE, MEADOW_ARRIVAL)) > 10 and 4 < x < SIZE - 4 and 4 < y < 70
                        and all(math.hypot(x - o['x'], y - o['y']) > o['r'] + 2 for o in meadow['objects'])
                        and all(math.hypot(x - t['x'], y - t['y']) > 5 for t in meadow['slimes'] if t is not s)):
                    d = math.hypot(x - ox, y - oy)
                    if best is None or d < best[0]:
                        best = (d, x, y)
            assert best, 'no clear spot for a displaced spawn'
            s['x'], s['y'] = round(best[1], 2), round(best[2], 2)
    for dx in (-1.5, 1.5):
        meadow['objects'].append({'kind': 'post', 'x': MEADOW_GATE[0] + dx, 'y': MEADOW_GATE[1], 'r': 0.45, 'v': 0})
    meadow['portals'] = [{'id': 'emberfall_gate', 'name': 'the Emberfall Gate', 'x': MEADOW_GATE[0], 'y': MEADOW_GATE[1], 'r': 1.1,
                          'to': 1, 'tx': ARRIVAL[0], 'ty': ARRIVAL[1]}]
    for o in meadow['objects']:
        if o['kind'] != 'post' and math.hypot(o['x'] - MEADOW_GATE[0], o['y'] - MEADOW_GATE[1]) < o['r'] + 1.6:
            raise SystemExit(f'meadow object {o} blocks the gate')
    zone = build(rng, meadow['objects'])
    missing = reachable(zone)
    if missing:
        raise SystemExit(f'unreachable from the arrival point: {missing}')
    meadow['zones'] = [zone]
    PATH.write_text(json.dumps(meadow, indent=2) + '\n')
    kinds = {}
    for s in zone['slimes']:
        kinds[s['kind']] = kinds.get(s['kind'], 0) + 1
    print(f"Wrote zone 1 {zone['name']}: {len(zone['objects'])} objects, spawns {kinds}. Now run node scripts/sync-world.cjs")


if __name__ == '__main__':
    main()
