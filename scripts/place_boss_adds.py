#!/usr/bin/env python3
"""Place the sleeping helpers of the final-boss mechanics (docs/boss-mechanics.md) in world/map.txt.

A mechanic wakes monsters that the map already holds: spawns with an `ambush` tag, dead and never respawning until
a fight wakes them (the singers of the Bound Chorus, the pearls of the Pearl Shell, seeds, treants, a cocoon each).
This script adds them round their boss, on free ground reachable from the arrival, and removes any it placed
before, so it is safe to run again. It also checks that every `hold` point and every `static` rod of
world/boss-mechanics.txt stands on free, reachable ground in its boss's room.

Run it after the dungeon generators (and `generate_sealed_dungeon_maps.py`, which rebuilds zones 29-39 without them),
then `node scripts/sync-world.cjs` and rebuild Rust.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_gloamfen as fen

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
TABLE = ROOT / 'world/boss-mechanics.txt'

# zone name, boss kind, then (tag, monster kind, how many, ring radius round the boss, first angle in degrees)
SPECS = [
    ('The Drowned Cathedral — Flooded Cloister', 'choirmother',
     [('chorus', 'choirsinger', 10, 10, 0)]),
    ('The Drowned Cathedral — Coral Reliquary', 'coralregent',
     [('pearl', 'reliquarypearl', 10, 9, 18), ('shellcrab', 'reliccrab', 2, 6, 90)]),
    ('The Seed Vault', 'seed_worldseed',
     [('seed', 'seed_sprout', 8, 7, 0), ('treant', 'seed_treant', 10, 8.5, 18)]),
    ('The Solar Crucible', 'solar_heart',
     [('cinder', 'solar_cinder', 1, 4, 20)]),
    ('The Amber Archive', 'amber_memory',
     [('cocoon', 'amber_cocoon', 6, 6, 30)]),
]
TAGS = {tag for _, _, groups in SPECS for tag, *_ in groups}
KINDS = {kind for _, _, groups in SPECS for _, kind, *_ in groups}


def boss_room(zone, boss):
    rooms = [r for r in zone['rooms'] if r[0] <= boss['x'] <= r[2] and r[1] <= boss['y'] <= r[3]]
    return max(rooms, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))


def free(blocked, seen, x, y, margin=1):
    i, j = int(x / .5), int(y / .5)
    n = blocked.shape[0]
    for dj in range(-margin, margin + 1):
        for di in range(-margin, margin + 1):
            a, b = i + di, j + dj
            if not (0 <= a < n and 0 <= b < n) or blocked[b, a]:
                return False
    return bool(seen[j, i])


def place(zone, boss, room, group, taken, blocked, seen):
    tag, kind, count, radius, first = group
    spots = []
    for n in range(count):
        angle = math.radians(first + 360 * n / count)
        for r in [radius - .5 * k for k in range(int(radius * 2) - 3)]:
            x = round(boss['x'] + r * math.cos(angle), 1)
            y = round(boss['y'] + r * math.sin(angle), 1)
            if not (room[0] + 1.5 <= x <= room[2] - 1.5 and room[1] + 1.5 <= y <= room[3] - 1.5):
                continue
            if free(blocked, seen, x, y) and all(math.hypot(x - tx, y - ty) >= 1.6 for tx, ty in taken):
                spots.append((x, y))
                taken.append((x, y))
                break
        else:
            raise SystemExit(f'{zone["name"]}: no free ground for {kind} #{n} round ({boss["x"]}, {boss["y"]})')
    return [dict(x=x, y=y, kind=kind, ambush=tag) for x, y in spots]


def check_points(zone, kind, blocked, seen, table):
    boss = next(s for s in zone['slimes'] if s['kind'] == kind)
    room = boss_room(zone, boss)
    for m in table.get(kind, {}).get('mechanics', []):
        points = m.get('points') or m.get('rods') or []
        for p in points:
            x, y = (p['x'], p['y']) if isinstance(p, dict) else p
            assert room[0] <= x <= room[2] and room[1] <= y <= room[3], (kind, m['name'], 'outside its room', x, y)
            assert free(blocked, seen, x, y, 1), (kind, m['name'], 'blocked or unreachable', x, y)


def main():
    world = json.loads(MAP.read_text())
    table = json.loads(TABLE.read_text())
    added = 0
    for zone in world['zones']:
        zone['slimes'] = [s for s in zone['slimes'] if not (s.get('ambush') in TAGS and s['kind'] in KINDS)]
    for name, boss_kind, groups in SPECS:
        zone = next(z for z in world['zones'] if z['name'] == name)
        assert zone['final_boss'] == boss_kind, (name, zone['final_boss'])
        boss = next(s for s in zone['slimes'] if s['kind'] == boss_kind)
        seen, blocked = fen.flood(zone, (zone['spawn']['x'], zone['spawn']['y']))
        room = boss_room(zone, boss)
        taken = [(s['x'], s['y']) for s in zone['slimes']]
        for group in groups:
            new = place(zone, boss, room, group, taken, blocked, seen)
            zone['slimes'].extend(new)
            added += len(new)
    for zone in world['zones']:
        fb = zone.get('final_boss')
        if fb in table and zone.get('rooms'):
            seen, blocked = fen.flood(zone, (zone['spawn']['x'], zone['spawn']['y']))
            check_points(zone, fb, blocked, seen, table)
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
    print(f'{added} sleeping helpers placed for {len(SPECS)} bosses')


if __name__ == '__main__':
    main()
