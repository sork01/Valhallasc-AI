#!/usr/bin/env python3
"""Writes Ran's Deep (zone 8, levels 35-40) into world/map.txt, and checks it.

A sea-floor zone under the storm of Bifrost Reach: Keelhaven (a camp of overturned longships) and the open Shallows in the south,
and the Net, a labyrinth of living coral, in the north, with Ran's Court (the Kraken) in its heart. The layout is in deep_layout.py,
the people and quests in deep_content.py. Five new monster kinds follow the maze's depth, the Kraken is the elite, and the new
`chime` objective sends heroes round three chains of tidebells (a bell is a `Place` with `chain` and `burn`).

The zone is appended after Bifrost Reach, so no older enemy id moves; the dungeon copies, which the world appends after every
file zone, move from zones 8-10 to 9-11. Its return gate leads to the Maelstrom that `open_maelstrom` writes into Bifrost Reach's
Roc's Eyrie (post-processing, no random numbers drawn except on its own stream; generate_bifrost.py calls it too).
Re-running replaces zone 8 and leaves everything else alone; it is idempotent. Afterwards: node scripts/sync-world.cjs, then
rebuild Rust. Use --plot FILE.png to draw the layout.
"""
import argparse
import heapq
import itertools
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deep_content as content                     # noqa: E402
import deep_layout as L                            # noqa: E402
import generate_gloamfen as fen                    # noqa: E402  (flood fill helpers)
import sky_layout as S                             # noqa: E402  (the Eyrie the Maelstrom stands on)
import spark_travel                                # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
SIZE = L.SIZE
STEP = .5
SPEED = 5.2                                        # the slowest class (warrior), tiles per second
MATERIALS = [  # id, name, sell: what Ran's Deep's monsters carry (items::material)
    ('drowned_coin', 'Drowned Coin', 620), ('angler_lure', 'Angler Lure', 660), ('moray_tooth', 'Moray Tooth', 700),
    ('siren_pearl', 'Siren Pearl', 760), ('shellback_plate', 'Shellback Plate', 820), ('kraken_beak', 'Kraken Beak', 1800),
    ('captains_signet', "Captain's Signet", 1400), ('ghostmaw_tooth', 'Ghostmaw Tooth', 1500)]
BELL_LABELS = {'deep_harbour': 'Harbour Bell', 'deep_net': 'Bell of the Net', 'deep_rans': "Bell of Rán"}
ROMAN = ['I', 'II', 'III', 'IV', 'V']


def obj(kind, x, y, r, v=0, **extra):
    o = {'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': r, 'v': v}
    o.update(extra)
    return o


def hash2(a, b, s=0):
    h = (a * 374761393 + b * 668265263 + s * 2147483647) & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    return ((h ^ (h >> 16)) & 0xffffffff) / 4294967296


# ---- the maze: hops, bells, the places that depend on it -------------------------------------------------------------------------
def hop_table(doors):
    """cell -> {cell: hops} over the open pairs."""
    pairs = L.open_pairs(doors)
    out = {}
    cells = [(c, r) for r in range(L.ROWS) for c in range(L.COLS)]
    for a in cells:
        d = {a: 0}
        queue = [a]
        for c in queue:
            for n in L.neighbours(*c):
                if n not in d and L.key(c, n) in pairs:
                    d[n] = d[c] + 1
                    queue.append(n)
        out[a] = d
    return out


def tour(hops, cells):
    """The shortest way to ring `cells` in some order, in hops."""
    best = None
    for order in itertools.permutations(cells):
        total = sum(hops[a][b] for a, b in zip(order, order[1:]))
        if best is None or total < best:
            best = total
    return best


def pick_bells(doors, depth, hops):
    """-> {'deep_net': [cells], 'deep_rans': [cells]}: sets of cells whose tour is 52-68 % (net) / 55-70 % (rans) of the distance a
    slowest-class hero covers while the first bell still rings. Chosen by a seeded stream, widest spread first."""
    rng = random.Random(20261014)
    band = L.band_of_cells(depth)
    out = {}
    specs = {
        'deep_net': (4, [c for c in depth if c not in L.BLOCK and band[c] in (1, 2)], .52, .68),
        'deep_rans': (5, [c for c in depth if c not in L.BLOCK and abs(c[0] - 4.5) <= 2.6 and abs(c[1] - 2.5) <= 2.6], .55, .70),
    }
    for chain, (n, pool, lo, hi) in specs.items():
        burn = L.CHAINS[chain][0]
        window = SPEED * burn
        found = []
        for combo in itertools.combinations(sorted(pool), n):
            if any(hops[a][b] < 2 for a, b in itertools.combinations(combo, 2)):
                continue
            t = tour(hops, combo) * L.PITCH
            if lo * window <= t <= hi * window:
                xs, ys = [L.cell_centre(*c)[0] for c in combo], [L.cell_centre(*c)[1] for c in combo]
                found.append(((max(xs) - min(xs)) * (max(ys) - min(ys)), combo))
        assert found, f'no bell set for {chain}'
        found.sort(key=lambda t: (-t[0], t[1]))
        top = [c for a, c in found[:max(1, len(found) // 20)]]
        out[chain] = list(rng.choice(top))
    return out


def bell_position(cell, chain, k):
    cx, cy = L.cell_centre(*cell)
    return (round(cx + (hash2(cell[0], cell[1], 11 + k) - .5) * 7, 2), round(cy + (hash2(cell[0], cell[1], 23 + k) - .5) * 7, 2))


def build_places(doors, depth, hops):
    bells = pick_bells(doors, depth, hops)
    places = [dict(p) for p in L.PLACES]
    band = L.band_of_cells(depth)
    # the Abyssal Garden: the deepest ordinary cell that holds no bell
    taken = {c for cells in bells.values() for c in cells}
    garden = max((c for c in depth if c not in L.BLOCK and c not in taken), key=lambda c: (depth[c], c[1], c[0]))
    gx, gy = L.cell_centre(*garden)
    # the Court Door: just outside the chamber door that is nearer to the entrance
    door = min(L.chamber_doors(doors), key=lambda d: min(depth[d[0]], depth[d[1]]))
    outer, inner = (door[0], door[1]) if door[0] not in L.BLOCK else (door[1], door[0])
    ox, oy = L.cell_centre(*outer)
    ix, iy = L.cell_centre(*inner)
    mx, my = (ox + ix) / 2, (oy + iy) / 2
    d = math.hypot(ox - ix, oy - iy)
    for p in places:
        if p['id'] == 'deep_garden':
            p['x'], p['y'] = gx, gy
        elif p['id'] == 'deep_courtdoor':
            p['x'], p['y'] = round(mx + (ox - mx) / (d / 2) * 4.5, 2), round(my + (oy - my) / (d / 2) * 4.5, 2)
    chains = {}
    for chain, (burn, fixed) in L.CHAINS.items():
        items = []
        if fixed:
            items = [(suffix, name, x, y) for suffix, name, x, y in fixed]
        else:
            for k, cell in enumerate(sorted(bells[chain], key=lambda c: (c[1], c[0]))):
                x, y = bell_position(cell, chain, k)
                items.append((f'{k + 1}', f'the {BELL_LABELS[chain]} {ROMAN[k]}', x, y))
        chains[chain] = items
        for suffix, name, x, y in items:
            places.append(dict(id=f'{chain}_{suffix}', name=name, x=x, y=y, r=L.BELL_R, chain=chain, burn=burn))
    return places, bells, garden, door


# ---- scenery ---------------------------------------------------------------------------------------------------------------------
class Ground:
    def __init__(self):
        self.cell = 4.0
        self.bins = {}

    def add(self, o):
        r = o.get('r') or max(o.get('width', 0), o.get('depth', 0)) / 2 * 1.42
        for i in range(int((o['x'] - r - 3) // self.cell), int((o['x'] + r + 3) // self.cell) + 1):
            for j in range(int((o['y'] - r - 3) // self.cell), int((o['y'] + r + 3) // self.cell) + 1):
                self.bins.setdefault((i, j), []).append((o['x'], o['y'], r))

    def clear(self, x, y, margin):
        for ox, oy, r in self.bins.get((int(x // self.cell), int(y // self.cell)), ()):
            if math.hypot(x - ox, y - oy) < r + margin:
                return False
        return True


def in_hub(x, y, pad=0.):
    h = content.HUB
    return h['x0'] - pad <= x <= h['x1'] + pad and h['y0'] - pad <= y <= h['y1'] + pad


def wall_objects(doors):
    out = []
    for x, y, w, d in L.wall_rects(doors):
        out.append({'kind': 'reefwall', 'x': round(x, 2), 'y': round(y, 2), 'r': 0, 'v': int(hash2(int(x * 4), int(y * 4), 3) * 4),
                    'width': round(w, 2), 'depth': round(d, 2)})
    return out


def trail_points(doors, depth, door):
    """The route a path draws: from Keelhaven's north edge up to the Pearl Gate and through the maze to the nearer Court door."""
    outer = door[0] if door[0] not in L.BLOCK else door[1]
    cells = L.trail(doors, depth, outer)
    pts = [(80.0, 141.0), (80.0, 125.0)] + [tuple(round(v, 2) for v in L.cell_centre(*c)) for c in cells]
    return pts


def build(rng):
    doors, depth = L.maze()
    hops = hop_table(doors)
    band = L.band_of_cells(depth)
    places, bells, garden, door = build_places(doors, depth, hops)
    npcs, quests, hub_objects, city = content.keelhaven()
    objects = wall_objects(doors) + hub_objects
    ground = Ground()
    for o in objects:
        ground.add(o)
    # --- landmarks
    for p in places:
        if p.get('chain'):
            objects.append(obj('tidebell', p['x'], p['y'], .8, 0, place=p['id']))
        elif p['id'] == 'deep_longship':
            for k, (dx, dy, v) in enumerate([(-3.2, -1.5, 0), (-1.0, -2.4, 1), (1.2, -2.6, 2), (3.1, -1.4, 3), (4.0, 1.2, 0), (-4.0, 1.4, 1)]):
                objects.append(obj('shiprib', p['x'] + dx, p['y'] + dy, 1.3, v, place=p['id']))
        elif p['id'] == 'deep_chapel':
            for k in range(6):
                a = k * math.pi / 5 + math.pi
                objects.append(obj('sunkencolumn', p['x'] + 5.2 * math.cos(a), p['y'] + 4.0 * math.sin(a) + 1.5, .55, k % 4, place=p['id']))
        elif p['id'] == 'deep_pearlgate':
            for dx in (-7.0, 7.0):
                objects.append(obj('sunkencolumn', 80 + dx, 121.2, .55, 1))
        elif p['id'] == 'deep_garden':
            for k in range(6):                                          # a ring with gaps wide enough to walk through
                a = k * 2 * math.pi / 6 + .4
                objects.append(obj('anemone', p['x'] + 3.4 * math.cos(a), p['y'] + 2.8 * math.sin(a), .5, k % 4))
        elif p['id'] == 'deep_courtdoor':
            pass
    for a, b in L.chamber_doors(doors):                                # columns flank each door of Ran's Court
        (ox, oy), (ix, iy) = L.cell_centre(*(a if a not in L.BLOCK else b)), L.cell_centre(*(b if b in L.BLOCK else a))
        mx, my = (ox + ix) / 2, (oy + iy) / 2
        horizontal = abs(ox - ix) > abs(oy - iy)                       # a door in a vertical wall: the columns stand above and below it
        for s in (-1, 1):
            objects.append(obj('sunkencolumn', mx + (0 if horizontal else s * 6.9), my + (s * 6.9 if horizontal else 0), .55, 2, court=1))
    for o in objects:
        if o['kind'] not in ('reefwall',):
            ground.add(o)
    for x, y in [(L.ARRIVAL[0] - 1.5, L.GATE[1]), (L.ARRIVAL[0] + 1.5, L.GATE[1])]:
        objects.append(obj('post', x, y, .45, 0))
    place_keep = [(p['x'], p['y'], p['r'] + (5.0 if p.get('chain') else 6.0)) for p in places]

    def cell_point(cell, inset):
        x0, y0, x1, y1 = L.cell_box(*cell)
        return rng.uniform(x0 + inset, x1 - inset), rng.uniform(y0 + inset, y1 - inset)

    def in_wing(x, y, inset):
        return any(b[0] + inset <= x <= b[2] - inset and b[1] + inset <= y <= b[3] - inset for b in L.WINGS.values())

    # --- spawns: the three elites first, so the bands keep clear of them
    spawns = []
    spawns.append({'x': round(L.BOSS[1], 2), 'y': round(L.BOSS[2], 2), 'kind': L.BOSS[0]})
    # two more elites: Hvitserk, the drowned captain, stands in the west Shallows beyond the Wreck of Naglfar (a quest: three heroes);
    # the Ghostmaw guards the deepest free corridor and has no quest at all (three heroes)
    spawns.append({'x': L.HVITSERK[0], 'y': L.HVITSERK[1], 'kind': 'hvitserk'})
    taken_cells = {c for cells in bells.values() for c in cells} | {garden}
    lair = next(c for c in sorted((c for c in depth if c not in L.BLOCK and c not in taken_cells), key=lambda c: (-depth[c], c[1], c[0]))
                if hops[c][garden] >= 2 and all(hops[c][t] >= 1 for t in taken_cells))
    lx, ly = L.cell_centre(*lair)
    spawns.append({'x': round(lx, 2), 'y': round(ly, 2), 'kind': 'ghostmaw'})

    # --- the ordinary kinds
    for kind, count, spacing, where in L.BANDS:
        placed, tries = 0, 0
        cells = [c for c in depth if c not in L.BLOCK and band[c] == where] if where != 'wings' else []
        while placed < count and tries < 60000:
            tries += 1
            if where == 'wings':
                b = L.WINGS[rng.choice(['west', 'east'])]
                x, y = rng.uniform(b[0] + 4, b[2] - 4), rng.uniform(b[1] + 4, b[3] - 4)
                if not in_wing(x, y, 4) or in_hub(x, y, 9.0):
                    continue
            else:
                cell = rng.choice(cells)
                x, y = cell_point(cell, 3.8)
            if any(math.hypot(x - a, y - b) < r for a, b, r in place_keep):
                continue
            if any(math.hypot(x - s['x'], y - s['y']) < (spacing if s['kind'] == kind else 7.0) for s in spawns):
                continue
            if not ground.clear(x, y, 2.3):
                continue
            spawns.append({'x': round(x, 2), 'y': round(y, 2), 'kind': kind})
            placed += 1
        assert placed == count, f'only {placed} of {count} {kind}'
    for q in spawns:
        ground.add(dict(x=q['x'], y=q['y'], r=.4))

    # --- scenery
    def free(x, y, r, margin):
        return ground.clear(x, y, r + margin) and not any(math.hypot(x - p['x'], y - p['y']) < p['r'] + 1.2 for p in places)

    def scatter_cells(kind, per_cell, r, margin=1.0, band_filter=None, v_choices=4):
        n = 0
        for cell in sorted(depth):
            if cell in L.BLOCK and kind not in ('coral', 'anemone'):
                continue
            if band_filter is not None and band[cell] not in band_filter and cell not in L.BLOCK:
                continue
            k = per_cell if isinstance(per_cell, int) else int(per_cell(cell))
            for _ in range(k):
                for _try in range(40):
                    if cell in L.BLOCK:
                        x0, y0, x1, y1 = L.cell_box(*cell)
                        x, y = rng.uniform(x0 + r + 1, x1 - r - 1), rng.uniform(y0 + r + 1, y1 - r - 1)
                    else:
                        x, y = cell_point(cell, r + 1.2)
                    if math.hypot(x - L.BOSS[1], y - L.BOSS[2]) < 6 and cell in L.BLOCK:
                        continue
                    if free(x, y, r, margin) and not any(math.hypot(x - s['x'], y - s['y']) < 3 for s in spawns):
                        o = obj(kind, x, y, r, rng.randrange(v_choices))
                        objects.append(o)
                        ground.add(o)
                        n += 1
                        break
        return n

    def scatter_wings(kind, count, r, margin=1.0, v_choices=4, boxes=('west', 'east'), hub_pad=2.0):
        placed, tries = 0, 0
        while placed < count and tries < 40000:
            tries += 1
            b = L.WINGS[rng.choice(boxes)]
            x, y = rng.uniform(b[0] + r + 1, b[2] - r - 1), rng.uniform(b[1] + r + 1, b[3] - r - 1)
            if in_hub(x, y, hub_pad) or not free(x, y, r, margin) or any(math.hypot(x - s['x'], y - s['y']) < 3 for s in spawns):
                continue
            o = obj(kind, x, y, r, rng.randrange(v_choices))
            objects.append(o)
            ground.add(o)
            placed += 1
        assert placed == count, f'only {placed} of {count} {kind}'

    scatter_cells('kelp', lambda c: 2 + int(hash2(c[0], c[1], 5) * 3), .35)
    scatter_cells('coral', lambda c: 1 + int(hash2(c[0], c[1], 6) * 2.4), .6, margin=1.2)
    scatter_cells('deeprock', lambda c: int(hash2(c[0], c[1], 7) * 2.2), .8, margin=1.4)
    scatter_cells('clam', lambda c: 1 if hash2(c[0], c[1], 8) < .3 else 0, .55, margin=1.4)
    scatter_cells('vent', lambda c: 1 if hash2(c[0], c[1], 9) < .22 else 0, .4, margin=2.0)
    scatter_cells('anchor', lambda c: 1 if hash2(c[0], c[1], 10) < .12 else 0, .5, margin=1.6)
    scatter_cells('shiprib', lambda c: 1 if hash2(c[0], c[1], 12) < .1 else 0, 1.3, margin=1.8, v_choices=4)
    scatter_cells('anemone', lambda c: 5 if c in L.BLOCK else 0, .5, margin=1.2)
    scatter_wings('kelp', 60, .35)
    scatter_wings('coral', 34, .6, margin=1.2)
    scatter_wings('deeprock', 24, .8, margin=1.4)
    scatter_wings('clam', 10, .55, margin=1.4)
    scatter_wings('vent', 8, .4, margin=2.0)
    scatter_wings('anchor', 6, .5, margin=1.6)
    scatter_wings('shiprib', 6, 1.3, margin=1.8, boxes=('west',))
    scatter_wings('sunkencolumn', 5, .55, margin=1.8, boxes=('east',))
    # a fringe of kelp and coral round Keelhaven's edge
    for _ in range(30):
        for _try in range(60):
            x, y = rng.uniform(L.HUB_BOX[0] - 4, L.HUB_BOX[2] + 4), rng.uniform(L.HUB_BOX[1] - 4, L.HUB_BOX[3] + 1.5)
            if in_hub(x, y, 0.0) or not free(x, y, .6, 1.4) or math.hypot(x - L.ARRIVAL[0], y - L.ARRIVAL[1]) < 6 or y > 172:
                continue
            o = obj('kelp' if rng.random() < .6 else 'coral', x, y, .4, rng.randrange(4))
            objects.append(o)
            ground.add(o)
            break
    # pearl lamps beside the trail
    path = trail_points(doors, depth, door)
    walked = 0.0
    lamp_every = 13.0
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        while walked < length:
            side = 1 if int(walked + ax + ay) % 2 else -1
            x, y = ax + ux * walked - uy * 2.6 * side, ay + uy * walked + ux * 2.6 * side
            if free(x, y, .2, .6) and not in_hub(x, y, 0.0) and not any(math.hypot(x - q['x'], y - q['y']) < 2.8 for q in spawns):
                o = obj('pearllamp', x, y, .2, int(hash2(int(x), int(y), 4) * 3))
                objects.append(o)
                ground.add(o)
            walked += lamp_every
        walked -= length
    zone = {'name': L.NAME, 'theme': 'deep', 'tagline': 'Under the storm, where the sea keeps what it catches', 'size': SIZE, 'levels': list(L.LEVELS),
            'spawn': {'x': L.ARRIVAL[0], 'y': L.ARRIVAL[1]}, 'paths': [[list(p) for p in path]], 'bounds': L.BOUNDS,
            'places': places, 'objects': objects, 'slimes': spawns, 'npcs': npcs, 'quests': quests, 'city': city,
            'portals': [{'id': 'maelstrom_up', 'name': 'the Maelstrom', 'x': L.GATE[0], 'y': L.GATE[1], 'r': 1.2,
                         'to': 7, 'tx': L.EYRIE_ARRIVAL[0], 'ty': L.EYRIE_ARRIVAL[1], 'look': 'maelstrom'}]}
    return zone, dict(doors=doors, depth=depth, hops=hops, bells=bells, band=band, garden=garden, door=door)


# ---- plotting --------------------------------------------------------------------------------------------------------------------
def plot(zone, path, scale=5):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (SIZE * scale, SIZE * scale), (12, 36, 62))
    d = ImageDraw.Draw(img)
    colours = {'reefwall': (232, 120, 100), 'kelp': (40, 160, 80), 'coral': (240, 140, 170), 'deeprock': (120, 130, 150), 'clam': (240, 240, 220),
               'vent': (160, 220, 255), 'anchor': (180, 180, 190), 'shiprib': (170, 120, 70), 'anemone': (120, 255, 200), 'sunkencolumn': (210, 210, 200),
               'pearllamp': (255, 250, 170), 'tidebell': (255, 200, 60), 'house': (180, 120, 80), 'chapel': (200, 120, 100)}
    for p in zone['paths']:
        d.line([(x * scale, y * scale) for x, y in p], fill=(60, 110, 140), width=6)
    for o in zone['objects']:
        c = colours.get(o['kind'], (255, 255, 255))
        if o.get('width'):
            d.rectangle([(o['x'] - o['width'] / 2) * scale, (o['y'] - o['depth'] / 2) * scale, (o['x'] + o['width'] / 2) * scale, (o['y'] + o['depth'] / 2) * scale], fill=c)
        else:
            r = max(o['r'], .3) * scale
            d.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'draugr': (120, 220, 120), 'angler': (255, 255, 90), 'moray': (255, 140, 0), 'siren': (255, 90, 220), 'shellback': (90, 200, 255), 'kraken': (255, 40, 40), 'hvitserk': (255, 200, 40), 'ghostmaw': (240, 250, 255)}
    for s in zone['slimes']:
        r = 8 if s['kind'] not in ('kraken', 'hvitserk', 'ghostmaw') else 16
        d.ellipse([s['x'] * scale - r, s['y'] * scale - r, s['x'] * scale + r, s['y'] * scale + r], outline=kc[s['kind']], width=2)
    for n in zone['npcs']:
        d.rectangle([n['x'] * scale - 3, n['y'] * scale - 3, n['x'] * scale + 3, n['y'] * scale + 3], fill=(255, 255, 0))
    for p in zone['places']:
        d.ellipse([(p['x'] - p['r']) * scale, (p['y'] - p['r']) * scale, (p['x'] + p['r']) * scale, (p['y'] + p['r']) * scale], outline=(0, 255, 255) if not p.get('chain') else (255, 160, 0), width=2)
    img.save(path)


# ---- checks ----------------------------------------------------------------------------------------------------------------------
def cell(grid, x, y):
    return grid[int(y / STEP), int(x / STEP)]


def distance_fields(blocked, sources):
    """True walking distance (8 neighbours, octile) from each source to every cell of the 0.5 grid, in tiles."""
    n = blocked.shape[0]
    idx = np.arange(n * n).reshape(n, n)
    rows, cols, vals = [], [], []
    for dj, di in ((0, 1), (1, 0), (1, 1), (1, -1)):
        j0, j1 = 0, n - dj
        i0, i1 = (0, n - di) if di >= 0 else (-di, n)
        a = idx[j0:j1, i0:i1]
        b = idx[j0 + dj:j1 + dj, i0 + di:i1 + di]
        ok = ~blocked[j0:j1, i0:i1] & ~blocked[j0 + dj:j1 + dj, i0 + di:i1 + di]
        if di and dj:                                              # a diagonal step must not cut a corner
            ok &= ~blocked[j0:j1, i0 + di:i1 + di] & ~blocked[j0 + dj:j1 + dj, i0:i1]
        rows.append(a[ok])
        cols.append(b[ok])
        vals.append(np.full(ok.sum(), STEP * (math.sqrt(2) if di and dj else 1)))
    r, c, v = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
    graph = coo_matrix((np.concatenate([v, v]), (np.concatenate([r, c]), np.concatenate([c, r]))), shape=(n * n, n * n)).tocsr()
    starts = [int(y / STEP) * n + int(x / STEP) for x, y in sources]
    return dijkstra(graph, directed=False, indices=starts).reshape(len(sources), n, n)


def probe(blocked, reach, p):
    """Where a hero stands to be in a place: its middle, or a point just beside it when a landmark stands there. Must be reachable."""
    for dx, dy in ((0, 0), (0, 2.0), (2.0, 0), (0, -2.0), (-2.0, 0), (1.5, 1.5), (-1.5, 1.5)):
        x, y = p['x'] + dx, p['y'] + dy
        if not blocked[int(y / STEP), int(x / STEP)] and reach[int(y / STEP), int(x / STEP)]:
            return x, y
    raise AssertionError(f"{p['id']} has no free point to stand on")


def check(zone, info):
    """Everything a hero must reach is reachable, the maze and the chamber close where they should, every bell chain can be rung
    in time (and not too easily), and nothing stands where it should not."""
    problems = []
    full, blocked = fen.flood(zone, L.ARRIVAL)
    probes = {p['id']: probe(blocked, full, p) for p in zone['places']}
    targets = [(n['id'], n['x'], n['y']) for n in zone['npcs']] + [(s['kind'], s['x'], s['y']) for s in zone['slimes']]
    targets += [(pid, x, y) for pid, (x, y) in probes.items()] + [('gate', L.GATE[0], L.GATE[1] - 2)]
    for name, x, y in targets:
        if not cell(full, x, y):
            problems.append(f'{name} at ({x}, {y}) is unreachable from the arrival')
    # closing the maze's door cuts off everything inside; closing both Court doors cuts off only the chamber
    door_x = L.OX + (L.ENTRY[0] + .5) * L.PITCH
    reach, _ = fen.flood(zone, L.ARRIVAL, [(door_x, L.SOUTH_WALL, 8.0)])
    inside = [t for t in targets if t[2] < L.SOUTH_WALL - 1]
    outside = [t for t in targets if t[2] > L.SOUTH_WALL + 3]
    if any(cell(reach, x, y) for _, x, y in inside):
        problems.append('closing the maze door leaves part of the maze reachable')
    if not all(cell(reach, x, y) for _, x, y in outside):
        problems.append('closing the maze door cuts off part of the Shallows')
    seals = []
    for a, b in L.chamber_doors(info['doors']):
        (ox, oy), (ix, iy) = L.cell_centre(*a), L.cell_centre(*b)
        seals.append(((ox + ix) / 2, (oy + iy) / 2, 8.0))
    both, _ = fen.flood(zone, L.ARRIVAL, seals)
    one = [fen.flood(zone, L.ARRIVAL, [s])[0] for s in seals]
    boss = (L.BOSS[1], L.BOSS[2])
    if cell(both, *boss):
        problems.append('the Kraken can be reached with both Court doors closed')
    for k, r in enumerate(one):
        if not cell(r, *boss):
            problems.append(f'closing only Court door {k} cuts off the Kraken: the doors are not independent')
    for name, x, y in targets:
        c = L.cell_of(x, y)
        if c in L.BLOCK or name == 'kraken' or any(math.hypot(x - sx, y - sy) < 10.0 for sx, sy, _ in seals):
            continue
        if not cell(both, x, y):
            problems.append(f'{name} is cut off by the Court doors')
    # every spawn stands in the cell quartile of its kind
    for s in zone['slimes']:
        if s['kind'] in ('kraken', 'hvitserk', 'ghostmaw'):
            continue
        want = next(w for k, _, _, w in L.BANDS if k == s['kind'])
        c = L.cell_of(s['x'], s['y'])
        if want == 'wings':
            if s['y'] < L.SOUTH_WALL:
                problems.append(f"a {s['kind']} stands in the maze at ({s['x']}, {s['y']})")
        elif info['band'].get(c) != want:
            problems.append(f"a {s['kind']} stands in a cell of quartile {info['band'].get(c)}, expected {want}")
    # bells: every chain's best tour is a fraction of what the slowest class walks while the first bell rings
    bells = {}
    for p in zone['places']:
        if p.get('chain'):
            bells.setdefault(p['chain'], []).append(p)
    fields = {}
    for chain, items in bells.items():
        burn = L.CHAINS[chain][0]
        if len(items) != {'deep_harbour': 3, 'deep_net': 4, 'deep_rans': 5}[chain]:
            problems.append(f'{chain} has {len(items)} bells')
        spots = [probes[p['id']] for p in items]
        dist = distance_fields(blocked, spots)
        fields[chain] = dist
        at = [(int(y / STEP), int(x / STEP)) for x, y in spots]
        best = None
        for order in itertools.permutations(range(len(items))):
            total = sum(dist[a][at[b]] for a, b in zip(order, order[1:]))
            best = total if best is None else min(best, total)
        window = SPEED * burn
        ratio = best / window
        if not .4 <= ratio <= .78:
            problems.append(f'{chain}: the best tour is {best:.0f} tiles, {ratio:.0%} of the {window:.0f} the slowest hero covers in {burn} s (want 40-78 %)')
        if min(dist[a][at[b]] for a in range(len(items)) for b in range(len(items)) if a != b) < 12:
            problems.append(f'{chain}: two bells are closer than 12 tiles')
    # people stand on free ground inside the hub
    soft = fen.obstacle_grid(zone, STEP, margin=.35)
    h = content.HUB
    for n in zone['npcs']:
        if cell(soft, n['x'], n['y']):
            problems.append(f"{n['id']} stands inside scenery at ({n['x']}, {n['y']})")
        if not (h['x0'] <= n['x'] <= h['x1'] and h['y0'] <= n['y'] <= h['y1']):
            problems.append(f"{n['id']} is outside the hub")
    for name, (x, y) in [('arrival', L.ARRIVAL), ('gate', L.GATE)]:
        if cell(blocked, x, y):
            problems.append(f'the {name} is blocked')
    for p in zone['places']:                                       # a hero must be able to stand inside every place's circle
        x, y = probes[p['id']]
        if math.hypot(x - p['x'], y - p['y']) > p['r'] - .5:
            problems.append(f"{p['id']} cannot be stood in")
    # the elites keep well away from the places a solo quest sends a hero to
    for e in [s for s in zone['slimes'] if s['kind'] in ('hvitserk', 'ghostmaw')]:
        for pl in zone['places']:
            need = pl['r'] + (10.0 if pl.get('chain') else 12.0)
            if math.hypot(e['x'] - pl['x'], e['y'] - pl['y']) < need:
                problems.append(f"{e['kind']} stands within {need:.0f} of {pl['id']}")
    # spawns: spacing, away from the arrival and the hub, clear of walls
    live = zone['slimes']
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if math.hypot(a['x'] - b['x'], a['y'] - b['y']) < 6.0:
                problems.append(f"{a['kind']} and {b['kind']} stand within 6 at ({a['x']}, {a['y']})")
    for s in live:
        if math.hypot(s['x'] - L.ARRIVAL[0], s['y'] - L.ARRIVAL[1]) < 8:
            problems.append(f"{s['kind']} is within 8 of the arrival")
        if in_hub(s['x'], s['y'], 8.0):
            problems.append(f"{s['kind']} at ({s['x']}, {s['y']}) is within 8 of the hub")
        if cell(blocked, s['x'], s['y']):
            problems.append(f"{s['kind']} at ({s['x']}, {s['y']}) stands in scenery")
    return problems


# ---- Bifrost Reach's end of the Maelstrom -------------------------------------------------------------------------------------------
def open_maelstrom(zone, world):
    """The Maelstrom on the Roc's Eyrie: a waterspout standing up out of the storm, ringed by floating rocks, with a portal down to
    Ran's Deep (the world's last zone). Done after the zone is built and only when Ran's Deep exists. Scenery near the gate goes,
    and spawns within 10.5 of the arrival move once (their own random stream), so a rebuild of Bifrost Reach stays byte-identical
    elsewhere. Idempotent."""
    names = [z['name'] for z in world['zones']]
    if L.NAME not in names:
        return
    to = names.index(L.NAME) + 1
    gx, gy = L.EYRIE_GATE
    ax, ay = L.EYRIE_ARRIVAL
    zone['objects'] = [o for o in zone['objects'] if o.get('rift') != 2]
    zone['objects'] = [o for o in zone['objects'] if o['kind'] not in ('skypine', 'prism', 'column', 'skyrock', 'cloudpuff', 'post')
                       or (math.hypot(o['x'] - gx, o['y'] - gy) > 5.0 and math.hypot(o['x'] - ax, o['y'] - ay) > 3.0) or o.get('place')]
    for i in range(6):
        a = 2 * math.pi * i / 6                      # none on the north-south axis: the spout is entered between the posts
        zone['objects'].append(obj('skyrock', gx + 3.4 * math.cos(a), gy + 3.4 * math.sin(a), .5, i % 4, rift=2))
    for dx in (-1.5, 1.5):
        zone['objects'].append(obj('post', gx + dx, gy, .45, 0, rift=2))
    zone['portals'] = [p for p in zone['portals'] if p['id'] != 'maelstrom_down']
    zone['portals'].append({'id': 'maelstrom_down', 'name': 'the Maelstrom', 'x': gx, 'y': gy, 'r': 1.3, 'to': to, 'tx': L.ARRIVAL[0], 'ty': L.ARRIVAL[1], 'look': 'maelstrom'})
    floor, _, _ = S.masks()
    edge = ndimage.distance_transform_edt(floor)
    eyrie = S.island_mask(S.ISLANDS['eyrie'])
    assert floor[int(gy), int(gx)] and floor[int(ay), int(ax)] and edge[int(gy), int(gx)] >= 3.5, 'the Maelstrom is not on the Eyrie'
    rng = random.Random(20261014)
    solid = [(o['x'], o['y'], o.get('r') or max(o.get('width', 0), o.get('depth', 0)) / 2 * 1.42) for o in zone['objects'] if o['kind'] != 'void']
    for s in zone['slimes']:
        if math.hypot(s['x'] - ax, s['y'] - ay) >= 10.5 and math.hypot(s['x'] - gx, s['y'] - gy) >= 9.0:
            continue
        for _ in range(60000):
            x, y = rng.uniform(95, 146), rng.uniform(12, 52)
            if not eyrie[int(y), int(x)] or edge[int(y), int(x)] < 3.5:
                continue
            if math.hypot(x - ax, y - ay) < 11 or math.hypot(x - gx, y - gy) < 11:
                continue
            if any(math.hypot(x - t['x'], y - t['y']) < (7.5 if t['kind'] == s['kind'] else 6.0) for t in zone['slimes'] if t is not s):
                continue
            if any(math.hypot(x - p['x'], y - p['y']) < p['r'] + 5 for p in zone['places']):
                continue
            if any(math.hypot(x - ox, y - oy) < r + 2.0 for ox, oy, r in solid):
                continue
            s['x'], s['y'] = round(x, 2), round(y, 2)
            break
        else:
            raise SystemExit('no room to move a spawn off the Maelstrom')


def add_materials():
    items = json.loads(ITEMS.read_text())
    have = {i['id'] for i in items}
    at = next(n for n, i in enumerate(items) if i['id'] == 'thunderroc_quill') + 1
    new = [m for m in MATERIALS if m[0] not in have]
    for k, (id_, name, sell) in enumerate(new):
        items.insert(at + k, {'id': id_, 'name': name, 'kind': 'material', 'rarity': 'common', 'sell': sell})
    ITEMS.write_text(json.dumps(items, indent=2))
    return len(new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot', help='write a PNG of the layout to this path and stop')
    args = parser.parse_args()
    zone, info = build(random.Random(20261014))
    problems = check(zone, info)
    if args.plot:
        plot(zone, args.plot)
        print('plotted', args.plot, len(zone['objects']), 'objects;', len(problems), 'problem(s)')
        for p in problems[:40]:
            print('  ', p)
        return
    if problems:
        raise SystemExit("Ran's Deep has problems:\n  " + '\n  '.join(problems))
    raw = PATH.read_text()
    world = json.loads(raw)
    assert json.dumps(world, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    names = [z['name'] for z in world['zones']]
    assert names[:7] == ['Emberfall Crags', 'Rimeveil Glacier', 'Gloamfen', 'Skaldholm', 'The Undervault', 'Wyrdwood', 'Bifrost Reach'], f'unexpected zones {names}'
    later = world['zones'][8:]
    world['zones'] = world['zones'][:7] + [zone] + later
    if any(z['name'] == 'Nacrehold' for z in later):
        from generate_nacrehold import open_tideway
        open_tideway(zone)
    open_maelstrom(world['zones'][6], world)
    spark_travel.ensure(world)
    PATH.write_text(json.dumps(world, indent=2) + '\n')
    new = add_materials()
    kinds = {}
    for sl in zone['slimes']:
        kinds[sl['kind']] = kinds.get(sl['kind'], 0) + 1
    print(f"Wrote zone 8 {zone['name']}: {len(zone['objects'])} objects, spawns {kinds}, {len(zone['npcs'])} NPCs, {len(zone['quests'])} quests; {new} new materials. Now run node scripts/sync-world.cjs")


if __name__ == '__main__':
    main()
