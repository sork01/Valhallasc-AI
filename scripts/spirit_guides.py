#!/usr/bin/env python3
"""Place a Spirit Guide close to every ghost respawn anchor (zone spawn, camps, raid checkpoints).

Run by sync-world.cjs after zone_shapes.py apply so coordinates match the live geometry.
Idempotent: replaces existing spirit_guide NPCs in place.
"""
import json
import math
from pathlib import Path
from compact_atlas import connected

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'

DIALOGUE = (
    'Your spirit lingers between worlds. I can restore you to life here, '
    'though it drains 50% of your gear durability and leaves you with 10 minutes '
    'of Resurrection Sickness (all stats at 25%).'
)
OFFER = dict(id='spirit_resurrect', label='Resurrect at Spirit Guide', cost=0)


def clear(z, x, y, margin=0.6):
    if not (1.0 < x < z['size'] - 1.0 and 1.0 < y < z['size'] - 1.0):
        return False
    if z.get('sky') and z['sky'][int(y)][int(x)] == ' ':
        return False
    for o in z.get('objects', []):
        dx, dy = abs(x - o['x']), abs(y - o['y'])
        if o.get('width', 0) and o.get('depth', 0):
            if dx < o['width'] / 2 + margin and dy < o['depth'] / 2 + margin:
                return False
        elif math.hypot(dx, dy) < o.get('r', 0) + margin:
            return False
    return True


def anchors_for(z):
    anchors = [('spawn', z['spawn'])]
    city_name = (z.get('city') or {}).get('name')
    for c in z.get('camps', []):
        if c.get('name') == city_name:
            continue
        pt = {'x': (c['x0'] + c['x1']) * 0.5, 'y': (c['y0'] + c['y1']) * 0.5}
        if all(math.hypot(pt['x'] - a['x'], pt['y'] - a['y']) > 6.0 for _, a in anchors):
            anchors.append((c.get('name', 'camp'), pt))
    for p in z.get('places', []):
        if 'checkpoint' not in p.get('id', ''):
            continue
        pt = {'x': p['x'], 'y': p['y']}
        if all(math.hypot(pt['x'] - a['x'], pt['y'] - a['y']) > 6.0 for _, a in anchors):
            anchors.append((p['id'], pt))
    return anchors


def place(z, anchor):
    start = dict(x=anchor['x'], y=anchor['y'])
    if not clear(z, start['x'], start['y'], 0.5):
        for _, ox, oy in sorted(
            (math.hypot(dx, dy), int(anchor['x']) + dx + 0.5, int(anchor['y']) + dy + 0.5)
            for dx in range(-4, 5) for dy in range(-4, 5)
        ):
            if clear(z, ox, oy, 0.55):
                start = dict(x=ox, y=oy)
                break
    reachable = connected(z, origin=start)
    for slime_gap in (5.0, 2.0, 0.0):
        for radius in (2.4, 3.2, 4.0, 5.0, 6.5, 8.5, 11.0):
            for step in range(24):
                angle = step * math.tau / 24
                x = round(start['x'] + math.cos(angle) * radius, 2)
                y = round(start['y'] + math.sin(angle) * radius, 2)
                if not clear(z, x, y, 0.7):
                    continue
                if int(y) * z['size'] + int(x) not in reachable:
                    continue
                if any(math.hypot(x - n['x'], y - n['y']) < 1.8 for n in z.get('npcs', [])):
                    continue
                if any(math.hypot(x - p['x'], y - p['y']) < p.get('r', 1.5) + 1.4 for p in z.get('portals', [])):
                    continue
                if slime_gap and any(math.hypot(x - s['x'], y - s['y']) < slime_gap for s in z.get('slimes', [])):
                    continue
                if not all(
                    clear(z, start['x'] + (x - start['x']) * t / 20, start['y'] + (y - start['y']) * t / 20, 0.35)
                    for t in range(21)
                ):
                    continue
                return x, y
    raise ValueError(f"No reachable Spirit Guide position near {anchor} in {z.get('name', 'Greenmeadow')}")


def main():
    world = json.loads(MAP.read_text())
    total = 0
    for zi, z in enumerate([world, *world['zones']]):
        z['npcs'] = [n for n in z.get('npcs', []) if n.get('art') != 'spirit_guide']
        if z.get('name') == 'The Arena':
            continue
        for ai, (_, anchor) in enumerate(anchors_for(z)):
            x, y = place(z, anchor)
            z['npcs'].append(dict(
                id=f'spirit_guide_{zi}_{ai}',
                name='Spirit Guide',
                role='Resurrection',
                x=x,
                y=y,
                art='spirit_guide',
                buys=False,
                dialogue=DIALOGUE,
                offers=[dict(OFFER)],
            ))
            total += 1
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
    print(f'Placed {total} Spirit Guides across {len(world["zones"]) + 1} zones')


if __name__ == '__main__':
    main()
