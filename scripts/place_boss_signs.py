#!/usr/bin/env python3
"""Pick where each final boss's sign stands (BOSSMECH-SIGN-ENGINE, docs/boss-mechanics.md).

The rules (the Rust test `signs_stand_where_the_rules_say` checks the same ones on the shipped data):
  * on free ground a hero can reach from the arrival point, with open ground round it (readable, never wedged in a wall);
  * in a room that does not hold the boss (the last room before the boss's door or arena), or anywhere on the approach
    when the zone has no rooms (the Moonwell);
  * further from the boss's home than its awareness radius plus 2 tiles, so reading never wakes the boss;
  * at least 2.2 tiles from the shortest walk from the arrival point to the boss, so the sign is off every walked route;
  * at least 3 tiles from every monster home and every portal, and 3 tiles from where chests may appear (the server also
    keeps chests 3 tiles from the sign);
  * nearer the arrival point than the boss is (reading it never means walking through the boss's room);
  * the candidate closest to the point where the walk to the boss comes within AWARENESS_MAX + 4 tiles of it wins (the last
    stretch a hero cannot miss), ties broken by the sign's distance from the route.

`python3 scripts/place_boss_signs.py` prints the chosen spots; `--write` puts them into world/boss-signs.txt, keeping the
text already there. Generators are not involved: the spots depend only on the finished dungeon maps.
"""
import json
import math
import pathlib
import sys
from collections import deque

ROOT = pathlib.Path(__file__).resolve().parents[1]
SIGNS = ROOT / 'world' / 'boss-signs.txt'
PLAYER_RADIUS = 0.3
AWARENESS_MAX = 18.0       # above the largest awareness among the sixteen final bosses (the Rust test checks each boss's own)
OFF_ROUTE = 2.2
HOMES = 3.0
OPEN_RING = 1


def blocked_grid(zone):
    n = zone['size']
    grid = [False] * (n * n)
    margin = 1.2
    for j in range(n):
        for i in range(n):
            x, y = i + .5, j + .5
            if x < margin or y < margin or x > n - margin or y > n - margin:
                grid[j * n + i] = True
    for o in zone['objects']:
        if o.get('width', 0) > 0 and o.get('depth', 0) > 0:
            hx, hy = o['width'] / 2 + PLAYER_RADIUS, o['depth'] / 2 + PLAYER_RADIUS
            box = True
        else:
            hx = hy = o.get('r', 0) + PLAYER_RADIUS
            box = False
        for j in range(max(0, math.floor(o['y'] - hy)), min(n - 1, math.ceil(o['y'] + hy)) + 1):
            for i in range(max(0, math.floor(o['x'] - hx)), min(n - 1, math.ceil(o['x'] + hx)) + 1):
                x, y = i + .5, j + .5
                hit = (abs(x - o['x']) < hx and abs(y - o['y']) < hy) if box else math.hypot(x - o['x'], y - o['y']) < hx
                if hit:
                    grid[j * n + i] = True
    return grid


def distance_field(n, grid, start):
    dist = [None] * (n * n)
    fx, fy = int(start['x']), int(start['y'])
    queue = deque()
    for r in range(4):
        found = False
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = fx + dx, fy + dy
                if 0 <= x < n and 0 <= y < n and not grid[y * n + x]:
                    dist[y * n + x] = 0
                    queue.append((x, y))
                    found = True
                    break
            if found:
                break
        if found:
            break
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and not grid[ny * n + nx] and dist[ny * n + nx] is None:
                dist[ny * n + nx] = dist[y * n + x] + 1
                queue.append((nx, ny))
    return dist


def in_room(room, x, y):
    return room[0] <= x < room[2] + 1 and room[1] <= y < room[3] + 1


def route_cells(n, dist, goal):
    """The shortest walk from the arrival point to the cell nearest the boss, as cell centres."""
    gx, gy = int(goal['x']), int(goal['y'])
    best = min(((x, y) for y in range(n) for x in range(n) if dist[y * n + x] is not None),
               key=lambda c: math.hypot(c[0] + .5 - goal['x'], c[1] + .5 - goal['y']))
    cells = [best]
    x, y = best
    while dist[y * n + x]:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and dist[ny * n + nx] is not None and dist[ny * n + nx] == dist[y * n + x] - 1:
                x, y = nx, ny
                cells.append((x, y))
                break
    return [(cx + .5, cy + .5) for cx, cy in cells]


def place(zone):
    n = zone['size']
    boss_kind = zone['final_boss']
    boss = next(s for s in zone['slimes'] if s['kind'] == boss_kind)
    grid = blocked_grid(zone)
    dist = distance_field(n, grid, zone['spawn'])
    route = route_cells(n, dist, boss)
    from_boss = distance_field(n, grid, boss)
    boss_steps = dist[int(route[0][1]) * n + int(route[0][0])]   # a sign stands on the arrival side of the boss
    boss_rooms = [r for r in zone.get('rooms', []) if in_room(r, boss['x'], boss['y'])]
    homes = [(s['x'], s['y']) for s in zone['slimes']] + [(p['x'], p['y']) for p in zone['portals']]
    # Where the walk to the boss first comes within `AWARENESS_MAX + 4` tiles of it: the sign stands beside this point,
    # the last stretch before the boss that a hero cannot miss.
    anchor = next((c for c in route if math.hypot(c[0] - boss['x'], c[1] - boss['y']) >= AWARENESS_MAX + 4), route[-1])
    best = None
    for cy in range(n):
        for cx in range(n):
            steps = dist[cy * n + cx]
            if grid[cy * n + cx] or steps is None or steps >= boss_steps:
                continue
            if any(grid[y * n + x] for y in range(max(0, cy - OPEN_RING), min(n, cy + OPEN_RING + 1))
                   for x in range(max(0, cx - OPEN_RING), min(n, cx + OPEN_RING + 1))):
                continue
            x, y = cx + .5, cy + .5
            if math.hypot(x - boss['x'], y - boss['y']) < AWARENESS_MAX + 2:
                continue
            rooms = zone.get('rooms', [])
            if rooms and (not any(in_room(r, x, y) for r in rooms) or any(in_room(r, x, y) for r in boss_rooms)):
                continue
            if min(math.hypot(x - rx, y - ry) for rx, ry in route) < OFF_ROUTE:
                continue
            if any(math.hypot(x - hx, y - hy) < HOMES for hx, hy in homes):
                continue
            off = min(math.hypot(x - rx, y - ry) for rx, ry in route)
            rank = (round(math.hypot(x - anchor[0], y - anchor[1]), 3), -off)
            if best is None or rank < best[0]:
                best = (rank, x, y)
    if best is None:
        raise SystemExit(f"no spot for {boss_kind}")
    return boss_kind, best[1], best[2]


def main():
    world = json.loads((ROOT / 'world' / 'map.txt').read_text())
    zones = [world] + world['zones']
    spots = {}
    for zone in zones:
        if zone.get('final_boss'):
            kind, x, y = place(zone)
            spots[kind] = (x, y)
            print(f"{kind:22s} {x:6.1f} {y:6.1f}   ({zone.get('name')})")
    if '--write' in sys.argv:
        data = json.loads(SIGNS.read_text()) if SIGNS.exists() else {}
        for kind, (x, y) in spots.items():
            data.setdefault(kind, {})['x'] = x
            data[kind]['y'] = y
        SIGNS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
