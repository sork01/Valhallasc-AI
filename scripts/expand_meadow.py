#!/usr/bin/env python3
"""Fill Greenmeadow's unused east and south with trails, landmarks and hunting grounds.

Only objects and spawns tagged by this script are regenerated. Alderhaven, existing
player/portal positions, quests, other zones and pre-existing scenery are preserved.
Run node scripts/sync-world.cjs and rebuild Rust afterwards.
"""
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
TAG = 'greenmeadow_wide_v1'
PATHS = [
    [[36, 79], [36, 71], [36, 62], [33, 52], [38, 44], [36, 36], [42, 28], [50, 22], [54, 12]],
    [[36, 36], [26, 32], [16, 26], [10, 16]],
    [[33, 52], [21, 57], [11, 68], [8, 84]],
    [[38, 44], [55, 42], [66, 43], [75, 39], [84, 34], [90, 20]],
    [[50, 22], [64, 17], [78, 13], [89, 10]],
    [[38, 52], [54, 60], [69, 66], [79, 72], [87, 81]],
    [[36, 69], [52, 68], [67, 69], [79, 72]],
]
# Spawns are appended, so the original meadow's enemy ids remain in their old order.
NEW_SPAWNS = [
    ('green', 12, 79), ('green', 18, 74),
    ('green', 75, 58), ('green', 90, 88),
    ('blue', 72, 47), ('blue', 83, 16), ('blue', 81, 58),
    ('pink', 91, 32), ('yellow', 72, 24),
    ('beetle', 88, 49), ('beetle', 75, 86),
]
RADII = {'tree': .42, 'bush': .30, 'rock': .40}
# x0, x1, y0, y1, count, weighted kinds. Trails separate the regions into clear pockets.
REGIONS = [
    (67, 93, 3, 25, 42, ('tree', 'tree', 'rock', 'rock', 'bush')),
    (67, 93, 26, 58, 50, ('tree', 'tree', 'bush', 'bush', 'rock')),
    (66, 93, 59, 92, 53, ('tree', 'tree', 'tree', 'bush', 'bush', 'rock')),
    (4, 22, 66, 92, 20, ('tree', 'bush', 'bush', 'rock')),
]


def path_distance(x, y):
    best = math.inf
    for path in PATHS:
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def separated(x, y, radius, objects, margin):
    for o in objects:
        if 'width' in o:
            dx = max(0, abs(x - o['x']) - o['width'] / 2)
            dy = max(0, abs(y - o['y']) - o['depth'] / 2)
            if math.hypot(dx, dy) <= radius + margin:
                return False
        elif math.hypot(x - o['x'], y - o['y']) <= radius + o['r'] + margin:
            return False
    return True


def main():
    raw = MAP.read_text()
    world = json.loads(raw)
    assert json.dumps(world, indent=2) + '\n' == raw, 'map.txt must retain canonical 2-space JSON layout'
    assert world['size'] == 96 and world['city']['name'] == 'Alderhaven'
    world['objects'] = [o for o in world['objects'] if o.get('layout') != TAG]
    world['slimes'] = [s for s in world['slimes'] if s.get('layout') != TAG]
    kings = [s for s in world['slimes'] if s['kind'] == 'big']
    assert len(kings) == 2, 'the meadow still needs its two King Slime spawn slots'
    kings[1]['x'], kings[1]['y'] = 84, 41  # its second appearance can now be across the meadow
    assert world['spawn'] == {'x': 36, 'y': 60}
    assert any(p['id'] == 'emberfall_gate' and (p['x'], p['y']) == (54, 9) for p in world['portals'])

    new_spawns = [dict(kind=kind, x=x, y=y, layout=TAG) for kind, x, y in NEW_SPAWNS]
    all_spawns = world['slimes'] + new_spawns
    old_objects = world['objects']
    landmarks = [
        dict(kind='water', x=79, y=28, r=2.3, v=0, layout=TAG),
        dict(kind='water', x=81.5, y=29.5, r=2.2, v=0, layout=TAG),
        dict(kind='water', x=78.2, y=30.5, r=1.7, v=0, layout=TAG),
    ]
    # A gap on the east side lets travellers walk into the stone ring.
    for degrees in (45, 90, 135, 180, 225, 270, 315):
        angle = math.radians(degrees)
        landmarks.append(dict(kind='rock', x=round(82 + 5 * math.cos(angle), 2),
                              y=round(82 + 5 * math.sin(angle), 2), r=.42, v=degrees // 45 % 4, layout=TAG))
    for o in landmarks:
        assert separated(o['x'], o['y'], o['r'], old_objects, .3), f'landmark meets old terrain: {o}'
        assert all(math.hypot(o['x'] - s['x'], o['y'] - s['y']) > o['r'] + 2.5 for s in all_spawns), f'landmark meets spawn: {o}'
    for s in new_spawns:
        assert 3 < s['x'] < 93 and 3 < s['y'] < 93
        assert separated(s['x'], s['y'], .8, old_objects + landmarks, 1.3), f'spawn meets obstacle: {s}'
        assert all(s is t or math.hypot(s['x'] - t['x'], s['y'] - t['y']) > 4.5 for t in all_spawns), f'spawns crowded: {s}'

    rng = random.Random(20261007)
    additions = list(landmarks)
    for x0, x1, y0, y1, count, kinds in REGIONS:
        placed = 0
        for _ in range(count * 600):
            if placed == count:
                break
            x, y = round(rng.uniform(x0, x1), 2), round(rng.uniform(y0, y1), 2)
            kind = rng.choice(kinds)
            r = RADII[kind]
            if math.hypot(x - 82, y - 82) < 7.5:  # the stones stand in a readable grass clearing
                continue
            if path_distance(x, y) < (2.4 if kind == 'tree' else 1.8):
                continue
            if any(math.hypot(x - s['x'], y - s['y']) <= 3.2 + r for s in all_spawns):
                continue
            if not separated(x, y, r, old_objects + additions, .65):
                continue
            additions.append(dict(kind=kind, x=x, y=y, r=r, v=rng.randrange(4), layout=TAG))
            placed += 1
        assert placed == count, f'only placed {placed}/{count} objects in {x0}..{x1}, {y0}..{y1}'

    world['objects'].extend(additions)
    world['slimes'].extend(new_spawns)
    if 'paths' in world:
        world['paths'] = PATHS
    else:
        ordered = {}
        for name, value in world.items():
            if name == 'zones':
                ordered['paths'] = PATHS
            ordered[name] = value
        world = ordered
    MAP.write_text(json.dumps(world, indent=2) + '\n')
    print(f'Greenmeadow: {len(world["objects"])} objects, {len(world["slimes"])} spawns, {len(PATHS)} trail lines')


if __name__ == '__main__':
    main()
