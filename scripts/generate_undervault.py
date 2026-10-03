#!/usr/bin/env python3
"""Writes the Undervault (zone 5), the five-player dungeon under Skaldholm, into world/map.txt, then checks it.

The plan (rooms, packs, bosses, doors) is in undervault_layout.py. This script turns it into a zone: a wall of stone
pieces round every room and corridor, pillars, braziers and bones for cover and mood, wall torches, the packs and the four
bosses, the stairs up and the portal that opens in the throne room when the last boss falls. The zone is a dungeon:
`copies: 4` makes the server keep four private copies of it (world/instances.rs). It also adds the dungeon's
loot materials to world/items.txt.

Idempotent and seeded: re-running replaces zone 5 and changes nothing else (checked byte for byte). Run it after
generate_skaldholm.py (which writes the stairs down to it). Afterwards: node scripts/sync-world.cjs, then rebuild Rust.
"""
import json
import math
from pathlib import Path
import random
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_gloamfen as fen                   # noqa: E402  (flood fill helpers)
import undervault_layout as L                     # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
SIZE = L.SIZE
MATERIALS = [  # id, name, sell: what the Undervault's monsters carry (items::material)
    ('crypt_bone', 'Crypt Bone', 90), ('bone_fletching', 'Bone Fletching', 95), ('hollow_ash', 'Hollow Ash', 105),
    ('wardens_signet', "Gatewarden's Signet", 600), ('hollow_chime', 'Hollow Chime', 700),
    ('runed_keystone', 'Runed Keystone', 800), ('crown_shard', 'Shard of the Hollow Crown', 1200)]
WALL_PIECE = 4                                    # longest wall piece, so a sprite box holds it


def walkable_mask():
    m = np.zeros((SIZE, SIZE), bool)
    for x0, y0, x1, y1 in L.ROOMS.values():
        m[y0:y1, x0:x1] = True
    return m


def wall_pieces(mask):
    """Cells that touch the floor (8 neighbours) become wall; runs are merged into rectangles, cut to WALL_PIECE long."""
    pad = np.pad(mask, 1)
    near = np.zeros_like(mask)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            near |= pad[1 + dj:1 + dj + SIZE, 1 + di:1 + di + SIZE]
    wall = near & ~mask
    rects = []
    used = np.zeros_like(wall)
    for j in range(SIZE):
        i = 0
        while i < SIZE:
            if wall[j, i] and not used[j, i]:
                i1 = i
                while i1 + 1 < SIZE and wall[j, i1 + 1] and not used[j, i1 + 1]:
                    i1 += 1
                j1 = j
                while j1 + 1 < SIZE and wall[j1 + 1, i:i1 + 1].all() and not used[j1 + 1, i:i1 + 1].any():
                    j1 += 1
                used[j:j1 + 1, i:i1 + 1] = True
                rects.append((i, j, i1 + 1, j1 + 1))
                i = i1 + 1
            else:
                i += 1
    out = []
    for x0, y0, x1, y1 in rects:
        w, d = x1 - x0, y1 - y0
        if w >= d:                                 # cut along x
            n = max(1, math.ceil(w / WALL_PIECE))
            for k in range(n):
                a, b = x0 + w * k / n, x0 + w * (k + 1) / n
                out.append(((a + b) / 2, (y0 + y1) / 2, b - a, d))
        else:
            n = max(1, math.ceil(d / WALL_PIECE))
            for k in range(n):
                a, b = y0 + d * k / n, y0 + d * (k + 1) / n
                out.append(((x0 + x1) / 2, (a + b) / 2, w, b - a))
    return out, wall


def build(rng):
    mask = walkable_mask()
    pieces, wall = wall_pieces(mask)
    objects = []
    for x, y, w, d in pieces:
        objects.append({'kind': 'vaultwall', 'x': round(x, 2), 'y': round(y, 2), 'r': round(max(w, d) / 2, 2),
                        'width': round(w, 2), 'depth': round(d, 2), 'v': rng.randrange(4)})
    # Spawns first: scenery keeps clear of them.
    slimes = []
    for room, (cx, cy), members in L.PACKS:
        for kind, dx, dy in members:
            slimes.append({'x': round(cx + dx, 2), 'y': round(cy + dy, 2), 'kind': kind})
    for room, kind, (x, y) in L.BOSSES:
        slimes.append({'x': float(x), 'y': float(y), 'kind': kind})
    keep = [(s['x'], s['y'], 3.0) for s in slimes] + [(L.ARRIVAL[0], L.ARRIVAL[1], 4.5), (L.STAIRS_UP[0], L.STAIRS_UP[1], 3.5),
                                                      (L.EXIT_PORTAL[0], L.EXIT_PORTAL[1], 3.5)]
    # Corridor mouths stay open: no scenery within 3 tiles of a doorway.
    for name, (x0, y0, x1, y1) in L.ROOMS.items():
        if name.startswith('c') and name != 'court':
            if x1 - x0 >= y1 - y0:
                keep += [(x0 + 1, (y0 + y1) / 2, 3.5), (x1 - 1, (y0 + y1) / 2, 3.5)]
            else:
                keep += [((x0 + x1) / 2, y0 + 1, 3.5), ((x0 + x1) / 2, y1 - 1, 3.5)]
    # The boss rooms keep their middle open as an arena.
    arenas = {name: (x, y) for name, _, (x, y) in L.BOSSES}

    def clear(x, y, r):
        return (all(math.hypot(x - kx, y - ky) > kr + r for kx, ky, kr in keep)
                and all(math.hypot(x - o['x'], y - o['y']) > o['r'] + r + .6 for o in objects if o['kind'] != 'vaultwall'))

    def inside(room, x, y, margin):
        x0, y0, x1, y1 = L.ROOMS[room]
        return x0 + margin <= x <= x1 - margin and y0 + margin <= y <= y1 - margin

    def add(kind, x, y, r, **extra):
        objects.append({'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': r, 'v': rng.randrange(4), **extra})
    # Pillars: a ring of them 3 tiles in from the walls of each hall, and four inside the big ones.
    for room in L.HALLS:
        x0, y0, x1, y1 = L.ROOMS[room]
        if room == 'hall0':
            continue
        step = 7.0
        xs = np.arange(x0 + 3.5, x1 - 3, step)
        ys = np.arange(y0 + 3.5, y1 - 3, step)
        for x in xs:
            for y in (y0 + 3.0, y1 - 3.0):
                if clear(x, y, .7):
                    add('pillar', x, y, .7)
        for y in ys:
            for x in (x0 + 3.0, x1 - 3.0):
                if clear(x, y, .7):
                    add('pillar', x, y, .7)
    # Cover in the middle of the trash halls: broken columns and sarcophagi break the archers' lines.
    for room, count, kind, radius in [('barracks', 5, 'sarcophagus', .9), ('ossuary', 8, 'sarcophagus', .9), ('chapel', 7, 'sarcophagus', .9),
                                      ('cistern', 6, 'pillar', .7), ('forge', 4, 'brazier', .5), ('court', 3, 'brazier', .5), ('throne', 4, 'brazier', .5)]:
        x0, y0, x1, y1 = L.ROOMS[room]
        placed, tries = 0, 0
        while placed < count and tries < 4000:
            tries += 1
            x, y = rng.uniform(x0 + 5, x1 - 5), rng.uniform(y0 + 5, y1 - 5)
            if room in arenas and math.hypot(x - arenas[room][0], y - arenas[room][1]) < 11:
                continue
            if clear(x, y, radius + 1.2):
                add(kind, x, y, radius)
                placed += 1
    # The stair hall: two braziers either side of the stairs.
    for dy in (-3.4, 3.4):
        add('brazier', L.STAIRS_UP[0] + 1.4, L.STAIRS_UP[1] + dy, .5)
    # Bones scattered everywhere on the floor (no collision worth speaking of).
    for _ in range(140):
        room = rng.choice(L.HALLS + ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7'])
        x0, y0, x1, y1 = L.ROOMS[room]
        x, y = rng.uniform(x0 + 1.5, x1 - 1.5), rng.uniform(y0 + 1.5, y1 - 1.5)
        if clear(x, y, .3):
            add('bones', x, y, .25)
    # Wall torches: a post just inside the wall, every ~9 tiles along the long walls of halls (they are not obstacles to speak of).
    torches = 0
    for room in L.HALLS:
        x0, y0, x1, y1 = L.ROOMS[room]
        for x in np.arange(x0 + 5, x1 - 4, 9.0):
            for y in (y0 + .5, y1 - .5):
                if clear(x, y, .2):
                    add('torch', x, y, .2)
                    torches += 1
    for y in (L.ROOMS['hall0'][1] + 5, L.ROOMS['hall0'][3] - 5):
        add('torch', L.ROOMS['hall0'][0] + .5, y, .2)
    zone = {
        'name': L.NAME, 'theme': 'vault', 'tagline': 'Beneath the Meeting Stone: a vault of bones, four wardens and a king',
        'size': SIZE, 'levels': [L.LEVEL, L.LEVEL], 'players': L.PLAYERS, 'min_level': L.LEVEL, 'copies': L.COPIES, 'final_boss': 'hollowking',
        'spawn': {'x': L.ARRIVAL[0], 'y': L.ARRIVAL[1]}, 'paths': [],
        'rooms': [list(r) for r in L.ROOMS.values()],
        'objects': objects, 'slimes': slimes,
        'portals': [
            {'id': 'undervault_stairs_up', 'name': 'the Stairs Up', 'x': L.STAIRS_UP[0], 'y': L.STAIRS_UP[1], 'r': 1.15, 'to': 4,
             'tx': L.STAIRS_RETURN[0], 'ty': L.STAIRS_RETURN[1], 'look': 'stairs_up'},
            {'id': 'undervault_exit', 'name': 'the Way Out', 'x': L.EXIT_PORTAL[0], 'y': L.EXIT_PORTAL[1], 'r': 1.3, 'to': 4,
             'tx': L.STAIRS_RETURN[0], 'ty': L.STAIRS_RETURN[1], 'after_clear': True, 'look': 'exit'},
        ],
    }
    return zone, torches


def check(zone):
    seen, blocked = fen.flood(zone, L.ARRIVAL)
    missing = []
    for s in zone['slimes']:
        if not seen[int(s['y'] / .5), int(s['x'] / .5)]:
            missing.append((s['kind'], s['x'], s['y']))
    for name, (x, y) in [('stairs up', (L.STAIRS_UP[0] + 1.5, L.STAIRS_UP[1])), ('exit', L.EXIT_PORTAL)]:
        if not seen[int(y / .5), int(x / .5)]:
            missing.append(name)
    # Every room reachable (a floor cell of each).
    for name, (x0, y0, x1, y1) in L.ROOMS.items():
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ok = any(seen[int((cy + dy) / .5), int((cx + dx) / .5)] for dx in range(-2, 3) for dy in range(-2, 3))
        if not ok:
            missing.append('room ' + name)
    # Spawns off scenery, no spawn near the arrival, packs apart.
    for s in zone['slimes']:
        near = [o for o in zone['objects'] if o['kind'] != 'vaultwall' and math.hypot(o['x'] - s['x'], o['y'] - s['y']) < o['r'] + .9]
        if near:
            missing.append(('on scenery', s))
        if math.hypot(s['x'] - L.ARRIVAL[0], s['y'] - L.ARRIVAL[1]) < 12:
            missing.append(('too near the arrival', s))
    centres = [(c, r) for r, c, _ in L.PACKS] + [(p, n) for n, _, p in L.BOSSES]
    for i, (a, an) in enumerate(centres):
        for b, bn in centres[i + 1:]:
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 12:
                missing.append(('packs too close', an, a, bn, b))
    return missing


def add_materials():
    items = json.loads(ITEMS.read_text())
    have = {i['id'] for i in items}
    for id, name, sell in MATERIALS:
        if id not in have:
            items.append({'id': id, 'name': name, 'kind': 'material', 'rarity': 'common', 'sell': sell})
    ITEMS.write_text(json.dumps(items, indent=2))


def main():
    raw = PATH.read_text()
    meadow = json.loads(raw)
    assert json.dumps(meadow, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    zones = meadow['zones']
    assert len(zones) >= 4 and zones[3]['name'] == 'Skaldholm', 'Skaldholm must be zone 4: run generate_skaldholm.py first'
    assert any(p['to'] == 5 for p in zones[3]['portals']), 'Skaldholm has no stairs to zone 5: run generate_skaldholm.py'
    zone, torches = build(random.Random(20261009))
    missing = check(zone)
    if missing:
        raise SystemExit(f'Undervault problems: {missing}')
    meadow['zones'] = zones[:4] + [zone]
    PATH.write_text(json.dumps(meadow, indent=2) + '\n')
    add_materials()
    kinds = {}
    for o in zone['objects']:
        kinds[o['kind']] = kinds.get(o['kind'], 0) + 1
    spawns = {}
    for s in zone['slimes']:
        spawns[s['kind']] = spawns.get(s['kind'], 0) + 1
    print(f"Wrote zone 5 {zone['name']}: {len(zone['objects'])} objects {kinds}; spawns {spawns}. Now run node scripts/sync-world.cjs")


if __name__ == '__main__':
    main()
