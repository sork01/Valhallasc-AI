#!/usr/bin/env python3
"""Writes the Wyrdwood (zone 6, levels 20-30) into world/map.txt, and checks it.

A 192x192 autumn forest below a storm-wracked moor, with two quest hubs (Hollowmoot in the south-west, Skuldwatch at the
north end of the Troll Bridge), five monster kinds, two elites, an escort route with two ambushes and six named places
for `visit` objectives. The layout lives in wyrd_layout.py, the people and quests in wyrd_content.py.

The zone is appended after the Undervault, so no older enemy id moves. Its return gate leads to Skaldholm's East Gate
(generate_skaldholm.py writes the other half: it opens the wall and adds the portal). Re-running replaces zone 6 and
leaves everything else alone; it is idempotent. Afterwards: node scripts/sync-world.cjs, then rebuild Rust.
Use --plot FILE.png to draw the layout.
"""
import argparse
import heapq
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_gloamfen as fen                    # noqa: E402  (flood fill helpers)
import progression_quests                          # noqa: E402
import spark_travel                                # noqa: E402
import wyrd_content as content                     # noqa: E402
import wyrd_layout as L                            # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
SIZE = L.SIZE
ZONE = 6
STEP = .5
MATERIALS = [  # id, name, sell: what the Wyrdwood's monsters carry (items::material)
    ('rotfang_tusk', 'Rotfang Tusk', 260), ('gallows_feather', 'Gallows Feather', 280), ('mosshide_scrap', 'Mosshide Scrap', 310),
    ('fate_thread', 'Frayed Fate Thread', 340), ('stormram_horn', 'Stormram Horn', 390), ('oakhorn_crown', 'Oakhorn Crown Antler', 700),
    ('stormheart_shard', 'Stormheart Shard', 1100)]
DECOR = ('tree', 'pine', 'bush', 'rock', 'spire')


def obj(kind, x, y, r, v=0, **extra):
    o = {'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': r, 'v': v}
    o.update(extra)
    return o


def building(kind, x, y, w, d, color, label='', **extra):
    return obj(kind, x, y, 0, 0, width=w, depth=d, color=color, label=label, **extra)


# ---- the river and the ridges --------------------------------------------------------------------------------------------
def build_river(rng):
    """Three staggered rows of water discs along the Skuld; a gap at the bridge keeps a 5.6-wide corridor."""
    out = []
    for row, off in enumerate((-1.8, 0.0, 1.8)):
        x = 0.3 + (L.WATER_STEP / 2 if row % 2 else 0)
        while x < SIZE - .3:
            if abs(x - L.BRIDGE_X) >= 5.1:
                out.append(obj('water', x, L.river_y(x) + off, L.WATER_R, rng.randrange(4)))
            x += L.WATER_STEP
    return out


def build_bridge_rails():
    """Rail posts either side of the deck; the deck itself is a ground decal the client draws (`bridges`)."""
    b = L.BRIDGE
    out = []
    y = b['y0'] + 1.2
    while y < b['y1'] - .5:
        for sx in (-1, 1):
            out.append(obj('post', L.BRIDGE_X + sx * 2.95, y, .3, 1))
        y += 2.4
    return out


def ridge(points, rng, gap, kind='crag'):
    """Crag blocks along a polyline, every CRAG_STEP, leaving a gap of RIDGE_GAP_HALF either side of `gap`."""
    out = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / L.CRAG_STEP))
        for i in range(n + 1):
            t = i / n
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            x += .5 * math.sin(y * 1.3 + x * .5)
            y += .6 * math.sin(x * .45 + 1.7) + .4 * math.cos(x * 1.1)
            if abs(x - gap[0]) < L.RIDGE_GAP_HALF:
                continue
            out.append(obj(kind, x, y, L.CRAG_R, rng.randrange(4)))
    return out


# ---- the hubs ------------------------------------------------------------------------------------------------------------
def fort_walls():
    """Skuldwatch's rampart: a rectangle with a gate in the middle of the north and south sides."""
    W = L.STORM_WALL
    cx = 96.0
    gl, gr = cx - L.GATE_HALF - 1.7, cx + L.GATE_HALF + 1.7
    color = '#5f6a78'
    out = []
    for x, y in [(W['x0'], W['y0']), (W['x1'], W['y0']), (W['x0'], W['y1']), (W['x1'], W['y1']), (gl, W['y0']), (gr, W['y0']), (gl, W['y1']), (gr, W['y1'])]:
        out.append(building('tower', x, y, 3.4, 3.4, '#4a5a6c'))

    def run(x0, y0, x1, y1):
        horizontal = abs(y1 - y0) < 1e-6
        length = (x1 - x0) if horizontal else (y1 - y0)
        n = max(1, math.ceil((length - 3.4) / 6.0))
        piece = (length - 3.4) / n
        for i in range(n):
            c = -length / 2 + 1.7 + piece * (i + .5)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            out.append(building('rampart', mx + c, my, piece + .15, 1.8, color) if horizontal
                       else building('rampart', mx, my + c, 1.8, piece + .15, color))
    run(W['x0'], W['y0'], gl, W['y0'])
    run(gr, W['y0'], W['x1'], W['y0'])
    run(W['x0'], W['y1'], gl, W['y1'])
    run(gr, W['y1'], W['x1'], W['y1'])
    run(W['x0'], W['y0'], W['x0'], W['y1'])
    run(W['x1'], W['y0'], W['x1'], W['y1'])
    for sx in (-1, 1):                                               # banners on the south gate
        out.append(obj('banner', cx + sx * (L.GATE_HALF + .2), W['y1'] - 2.9, .3, 0, color='#2f5a9a' if sx > 0 else '#9a2f3a'))
    return out


def gate_posts():
    return [obj('post', L.GATE[0], L.GATE[1] + dy, .45, 0) for dy in (-1.5, 1.5)]


def stone_circle(cx, cy, radius, n, start=0.):
    return [obj('spire', cx + radius * math.cos(start + 2 * math.pi * i / n), cy + radius * math.sin(start + 2 * math.pi * i / n), .55, i % 4)
            for i in range(n)]


def beacons():
    out = []
    for place in L.PLACES:
        if place['id'] in L.BEACONS:
            out.append(obj('beacon', place['x'], place['y'], .9, 0, place=place['id']))
    return out


# ---- scenery and spawns --------------------------------------------------------------------------------------------------
class Ground:
    """Free-ground tests over a coarse grid of what is already placed."""

    def __init__(self):
        self.cell = 4.0
        self.n = int(SIZE / self.cell) + 1
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


def hub_rect(hub, pad=0.):
    return hub['x0'] - pad, hub['x1'] + pad, hub['y0'] - pad, hub['y1'] + pad


def in_rect(x, y, rect):
    return rect[0] <= x <= rect[1] and rect[2] <= y <= rect[3]


def forest_density(x, y):
    """0..1: how crowded the trees are. Thick in the boarwood and round the grove, thin on the hills and the moor."""
    if y > 112:
        d = .85
        if x > 118 and y > 148:
            d = .5                                     # gallows hill is bald
        return d
    return .5


def trail_polylines():
    """Dirt trails: the main road and its branches."""
    river_x = L.BRIDGE_X
    main = [(L.GATE[0], L.GATE[1]), (L.ARRIVAL[0], L.ARRIVAL[1]), (33, 150), (58, 150), (70, 144), (82, 134), (92, 124), (river_x, 116), (river_x, 98), (river_x, 86), (river_x, 74),
            (96, 66), (96, 58), (100, 52), (120, 48), (150, 46), (150, 40), (140, 34), (100, 33), (60, 30), (44, 26), (44, 20), (60, 14), (96, 12), (L.HRUNGNIR[0], L.HRUNGNIR[1] + 3)]
    gallows = [(58, 150), (80, 168), (110, 172), (140, 170), (160, 170), (L.EYDIS_START[0], L.EYDIS_START[1])]
    grove = [(river_x, 120), (120, 124), (145, 132), (L.OAKHORN[0] - 6, L.OAKHORN[1] - 2)]
    west_beacon = [(96, 60), (70, 60), (45, 58), (26, 58)]
    storm_beacon = [(44, 26), (46, 31)]
    return [main, gallows, grove, west_beacon, storm_beacon]


def dist_to_polylines(lines, x, y):
    return min(fen.dist_to_trail(line, x, y) for line in lines)


def build(rng):
    objects = []
    objects += build_river(rng)
    objects += build_bridge_rails()
    objects += ridge([(.8, L.R_A_Y), (SIZE - .8, L.R_A_Y)], rng, L.R_A_GAP)
    objects += ridge([(.8, L.R_B_Y), (SIZE - .8, L.R_B_Y)], rng, L.R_B_GAP)
    npcs1, quests1, hub1, city1 = content.hollowmoot()
    npcs2, quests2, hub2, city2 = content.skuldwatch()
    objects += gate_posts() + hub1 + hub2 + fort_walls() + beacons()
    objects += stone_circle(96, 57, 6.6, 9, .35)
    objects += stone_circle(L.HRUNGNIR[0], L.HRUNGNIR[1], 10.5, 12, .1)          # the summit court
    objects.append(obj('spire', L.EYDIS_START[0] - 2.5, L.EYDIS_START[1] - 1.5, .55, 2))   # the mill's broken chimney
    objects.append(building('house', L.EYDIS_START[0] + 3.2, L.EYDIS_START[1] + 1.8, 3.6, 3.2, '#5a4a3a', "Hirdman's Mill"))
    for x, y, v in L.GALLOWS:
        objects.append(obj('gallows', x, y, .6, v))
    for x, y, v in L.BONES:
        objects.append(obj('bones', x, y, 1.1, v))
    npcs = npcs1 + npcs2 + [content.EYDIS]
    quests = quests1 + quests2
    trails = trail_polylines()

    ground = Ground()
    for o in objects:
        ground.add(o)

    # Keep-outs for scenery: hubs, gates, trails, the bridge approach, the elites' courts.
    h1, h2 = hub_rect(L.HOLLOW, 2.0), hub_rect(L.STORM_WALL, 3.0)

    def scenery_ok(x, y, margin, trail_clear=2.6):
        if not (2 < x < SIZE - 2 and 2 < y < SIZE - 2):
            return False
        if in_rect(x, y, h1) or in_rect(x, y, h2):
            return False
        if math.hypot(x - L.GATE[0], y - L.GATE[1]) < 7:
            return False
        if abs(x - L.BRIDGE_X) < 7.5 and abs(y - L.river_y(L.BRIDGE_X)) < 15:
            return False
        if dist_to_polylines(trails, x, y) < trail_clear:
            return False
        if math.hypot(x - L.OAKHORN[0], y - L.OAKHORN[1]) < 9.5 or math.hypot(x - L.HRUNGNIR[0], y - L.HRUNGNIR[1]) < 9.0:
            return False
        if math.hypot(x - L.EYDIS_START[0], y - L.EYDIS_START[1]) < 4.5:
            return False
        for line in L.PLACES:
            if math.hypot(x - line['x'], y - line['y']) < line['r'] + 1.2:
                return False
        if abs(y - L.river_y(x)) < 6.5:
            return False
        if abs(y - L.R_A_Y) < 3.4 or abs(y - L.R_B_Y) < 3.4:
            return False
        return ground.clear(x, y, margin)

    def scatter(kind, count, r, region, density_fn=None, margin=1.1, v_choices=4, max_tries=60000):
        placed = 0
        tries = 0
        while placed < count and tries < max_tries:
            tries += 1
            x, y = rng.uniform(region[0], region[1]), rng.uniform(region[2], region[3])
            if density_fn and rng.random() > density_fn(x, y):
                continue
            if not scenery_ok(x, y, r + margin):
                continue
            o = obj(kind, x, y, r, rng.randrange(v_choices))
            objects.append(o)
            ground.add(o)
            placed += 1
        assert placed == count, f'only {placed} of {count} {kind}'

    south = (2, SIZE - 2, 115, SIZE - 2)
    heights = (2, SIZE - 2, 2, 100)
    scatter('tree', 330, .42, south, forest_density)
    scatter('bush', 150, .3, south, forest_density)
    scatter('rock', 40, .4, south)
    scatter('pine', 170, .42, heights, lambda x, y: .9 if y > 45 else .55)
    scatter('bush', 70, .3, heights)
    scatter('rock', 70, .4, heights)
    scatter('tree', 40, .42, (2, SIZE - 2, 100, 112))                     # a few oaks on the near bank only
    spawns = place_spawns(objects, rng, ground, trails)
    zone_for_route = {'size': SIZE, 'objects': objects}
    route = plan_route(zone_for_route, spawns)
    ambushes = []
    for a in L.AMBUSHES:
        tag = 'wyrd_eydis#' + a['tag']
        ambushes.append(dict(at=[a['at'][0], a['at'][1]], r=a['r'], tag=tag))
        spawns += ambush_slots(a, tag, zone_for_route, spawns, route, rng)
    eydis = dict(content.EYDIS, x=L.EYDIS_START[0], y=L.EYDIS_START[1])
    eydis['escort'] = dict(quest='wyrd_escort', **{'class': 'mage'}, female=True, hairColor=1, skin=0, level=26, speed=L.EYDIS_SPEED,
                           route=[[round(x, 2), round(y, 2)] for x, y in route[1:]], ambush=ambushes)
    npcs[-1] = eydis

    zone = {'name': L.NAME, 'theme': 'wyrd', 'tagline': 'Where the forest remembers every thread', 'size': SIZE, 'levels': list(L.LEVELS),
            'spawn': {'x': L.ARRIVAL[0], 'y': L.ARRIVAL[1]}, 'paths': [[[round(x, 1), round(y, 1)] for x, y in line] for line in trails],
            'bridges': [dict(L.BRIDGE)], 'places': [dict(p) for p in L.PLACES],
            'objects': objects, 'slimes': spawns, 'npcs': npcs, 'quests': quests, 'city': city1, 'camps': [city2],
            'portals': [{'id': 'skaldholm_gate', 'name': "Skaldholm's East Gate", 'x': L.GATE[0], 'y': L.GATE[1], 'r': 1.1,
                         'to': 4, 'tx': L.SKALD_ARRIVAL[0], 'ty': L.SKALD_ARRIVAL[1]}]}
    return zone


def place_spawns(objects, rng, ground, trails):
    spawns = []
    hubs = [hub_rect(L.HOLLOW, 11.0), hub_rect(L.STORM_WALL, 13.0)]
    keep_off = [(L.GATE[0], L.GATE[1], 24.), (L.OAKHORN[0], L.OAKHORN[1], 15.), (L.HRUNGNIR[0], L.HRUNGNIR[1], 14.), (L.EYDIS_START[0], L.EYDIS_START[1], 9.),
                (L.BRIDGE_X, L.river_y(L.BRIDGE_X), 9.), (L.R_A_GAP[0], L.R_A_GAP[1], 9.), (L.R_B_GAP[0], L.R_B_GAP[1], 9.)]
    keep_off += [(p['x'], p['y'], 5.) for p in L.PLACES if p['id'] != 'wyrd_norn_stones']
    # the route of the escort stays free of ordinary spawns closer than 9 (the ambushers are placed on purpose)
    route = [(x, y) for x, y in L.EYDIS_ROUTE]

    def ok(x, y, kind, spacing):
        if not (3 < x < SIZE - 3 and 3 < y < SIZE - 3):
            return False
        if any(in_rect(x, y, h) for h in hubs):
            return False
        if any(math.hypot(x - a, y - b) < r for a, b, r in keep_off):
            return False
        if abs(y - L.river_y(x)) < 8:
            return False
        if abs(y - L.R_A_Y) < 6 or abs(y - L.R_B_Y) < 6:
            return False
        if any(math.hypot(x - s['x'], y - s['y']) < spacing for s in spawns):
            return False
        if kind != 'troll' and fen.dist_to_trail(route, x, y) < 7:
            return False
        return ground.clear(x, y, 2.3)

    for kind, count, spacing, boxes in L.BANDS:
        placed = 0
        tries = 0
        while placed < count and tries < 40000:
            tries += 1
            x0, y0, x1, y1 = rng.choice(boxes)
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if not ok(x, y, kind, spacing):
                continue
            if kind == 'troll' and (abs(x - L.BRIDGE_X) < 24) != (placed < 4):
                continue                                    # the first four stand at the bridge
            spawns.append({'x': round(x, 2), 'y': round(y, 2), 'kind': kind})
            placed += 1
        if placed != count:
            raise SystemExit(f'no room for {count} {kind}: placed {placed}')
    spawns.append({'x': L.OAKHORN[0], 'y': L.OAKHORN[1], 'kind': 'oakhorn'})
    spawns.append({'x': L.HRUNGNIR[0], 'y': L.HRUNGNIR[1], 'kind': 'hrungnir'})
    return spawns


# ---- the escort's route --------------------------------------------------------------------------------------------------
def line_clear(blocked, a, b):
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / .2))
    for k in range(n + 1):
        x = a[0] + (b[0] - a[0]) * k / n
        y = a[1] + (b[1] - a[1]) * k / n
        if blocked[int(y / STEP), int(x / STEP)]:
            return False
    return True


def snap(blocked, p):
    """The nearest free cell centre to p (a via-point may land inside a tree)."""
    i0, j0 = int(p[0] / STEP), int(p[1] / STEP)
    for r in range(0, 40):
        for j in range(j0 - r, j0 + r + 1):
            for i in range(i0 - r, i0 + r + 1):
                if max(abs(i - i0), abs(j - j0)) == r and 0 <= i < blocked.shape[0] and 0 <= j < blocked.shape[0] and not blocked[j, i]:
                    return ((i + .5) * STEP, (j + .5) * STEP)
    raise SystemExit(f'no free ground near {p}')


def astar(blocked, cost, a, b):
    """8-connected cheapest walk over free cells; `cost` adds a penalty near dangers."""
    n = blocked.shape[0]
    start, goal = (int(a[0] / STEP), int(a[1] / STEP)), (int(b[0] / STEP), int(b[1] / STEP))
    assert not blocked[start[1], start[0]], f'route start {a} is blocked'
    assert not blocked[goal[1], goal[0]], f'route goal {b} is blocked'
    best = {start: 0.0}
    came = {}
    heap = [(0.0, start)]
    while heap:
        _, cur = heapq.heappop(heap)
        if cur == goal:
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = cur[0] + dx, cur[1] + dy
            if not (0 <= nx < n and 0 <= ny < n) or blocked[ny, nx]:
                continue
            if dx and dy and (blocked[cur[1], nx] or blocked[ny, cur[0]]):
                continue
            step = (1.414 if dx and dy else 1.0) * (1.0 + cost[ny, nx])
            g = best[cur] + step
            if g < best.get((nx, ny), 1e18):
                best[(nx, ny)] = g
                came[(nx, ny)] = cur
                h = math.hypot(goal[0] - nx, goal[1] - ny)
                heapq.heappush(heap, (g + h, (nx, ny)))
    assert goal in came or goal == start, f'no walk from {a} to {b}'
    path = [goal]
    while path[-1] != start:
        path.append(came[path[-1]])
    return [((i + .5) * STEP, (j + .5) * STEP) for i, j in reversed(path)]


def plan_route(zone, spawns):
    """The escort's waypoints: A* between the via-points of EYDIS_ROUTE over ground with 1.0 clearance, steering round
    ordinary packs (trolls and crows are on purpose), then cut down to the corners that line of sight needs."""
    blocked = fen.obstacle_grid(zone, STEP, margin=1.0)
    n = blocked.shape[0]
    cost = np.zeros((n, n))
    ii = (np.arange(n) + .5) * STEP
    X, Y = np.meshgrid(ii, ii)
    for s in spawns:
        if s['kind'] in ('troll', 'crow'):
            continue
        cost += np.where(np.hypot(X - s['x'], Y - s['y']) < 9.0, 4.0, 0.0)
    cells = []
    via = [snap(blocked, p) for p in L.EYDIS_ROUTE]
    for a, b in zip(via, via[1:]):
        cells += astar(blocked, cost, a, b)[(1 if cells else 0):]
    route = [cells[0]]
    i = 0
    while i < len(cells) - 1:
        j = len(cells) - 1
        while j > i + 1 and not line_clear(blocked, cells[i], cells[j]):
            j -= 1
        route.append(cells[j])
        i = j
    # a waypoint every 18 tiles at most keeps the stuck-recovery honest
    out = [route[0]]
    for p in route[1:]:
        q = out[-1]
        d = math.hypot(p[0] - q[0], p[1] - q[1])
        for k in range(1, int(d // 18) + 1):
            out.append((q[0] + (p[0] - q[0]) * k * 18 / d, q[1] + (p[1] - q[1]) * k * 18 / d))
        out.append(p)
    return out


def ambush_slots(a, tag, zone, spawns, route, rng):
    """`n` sleeping enemies of one kind near `a['near']`, off the path but within sight of it."""
    blocked = fen.obstacle_grid(zone, STEP, margin=1.2)
    chosen = []
    for _ in range(20000):
        ang = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(5.0, 9.0)
        x, y = a['near'][0] + d * math.cos(ang), a['near'][1] + d * math.sin(ang)
        if not (3 < x < SIZE - 3 and 3 < y < SIZE - 3) or blocked[int(y / STEP), int(x / STEP)]:
            continue
        if abs(y - L.river_y(x)) < 6.5 or fen.dist_to_trail(route, x, y) < 3.5:
            continue
        if any(math.hypot(x - q['x'], y - q['y']) < 3.0 for q in chosen):
            continue
        if any(math.hypot(x - q['x'], y - q['y']) < 5.0 for q in spawns):
            continue
        chosen.append({'x': round(x, 2), 'y': round(y, 2), 'kind': a['kind'], 'ambush': tag})
        if len(chosen) == a['n']:
            return chosen
    raise SystemExit(f'no room for the {a["tag"]} ambush near {a["near"]}')


# ---- plotting ------------------------------------------------------------------------------------------------------------
def plot(zone, path, scale=5):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (SIZE * scale, SIZE * scale), (58, 78, 44))
    d = ImageDraw.Draw(img)
    colours = {'tree': (150, 80, 30), 'pine': (30, 80, 50), 'bush': (110, 120, 50), 'rock': (130, 130, 130), 'crag': (80, 80, 90), 'water': (50, 120, 190),
               'spire': (220, 220, 200), 'post': (200, 160, 80), 'rampart': (120, 130, 150), 'tower': (90, 100, 130), 'house': (180, 120, 80),
               'chapel': (200, 120, 100), 'beacon': (255, 140, 0), 'elderash': (100, 70, 30)}
    for line in zone['paths']:
        d.line([(x * scale, y * scale) for x, y in line], fill=(170, 140, 90), width=int(2 * scale))
    for o in zone['objects']:
        c = colours.get(o['kind'], (255, 255, 255))
        if o.get('width'):
            d.rectangle([(o['x'] - o['width'] / 2) * scale, (o['y'] - o['depth'] / 2) * scale, (o['x'] + o['width'] / 2) * scale, (o['y'] + o['depth'] / 2) * scale], fill=c)
        else:
            r = o['r'] * scale
            d.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'boar': (220, 60, 60), 'crow': (60, 60, 60), 'troll': (60, 200, 60), 'weaver': (200, 60, 200), 'ram': (240, 240, 60), 'oakhorn': (255, 0, 0), 'hrungnir': (0, 0, 255)}
    for s in zone['slimes']:
        r = 4 if s['kind'] in ('oakhorn', 'hrungnir') else 2.6
        d.ellipse([s['x'] * scale - r * 2, s['y'] * scale - r * 2, s['x'] * scale + r * 2, s['y'] * scale + r * 2], outline=kc[s['kind']], width=3)
    for n in zone['npcs']:
        if 'x' not in n:
            continue
        d.rectangle([n['x'] * scale - 3, n['y'] * scale - 3, n['x'] * scale + 3, n['y'] * scale + 3], fill=(255, 255, 0))
    for p in zone['places']:
        d.ellipse([(p['x'] - p['r']) * scale, (p['y'] - p['r']) * scale, (p['x'] + p['r']) * scale, (p['y'] + p['r']) * scale], outline=(0, 255, 255), width=2)
    eydis = next(n for n in zone['npcs'] if n.get('escort'))
    pts = [(eydis['x'] * scale, eydis['y'] * scale)] + [(x * scale, y * scale) for x, y in eydis['escort']['route']]
    for a in eydis['escort']['route']:
        d.ellipse([a[0] * scale - 3, a[1] * scale - 3, a[0] * scale + 3, a[1] * scale + 3], fill=(255, 0, 255))
    d.line(pts, fill=(255, 0, 255), width=3)
    for a in eydis['escort']['ambush']:
        r = a['r'] * scale
        d.ellipse([a['at'][0] * scale - r, a['at'][1] * scale - r, a['at'][0] * scale + r, a['at'][1] * scale + r], outline=(255, 0, 255), width=2)
    img.save(path)


# ---- checks --------------------------------------------------------------------------------------------------------------
def cell(grid, x, y):
    return grid[int(y / STEP), int(x / STEP)]


def check(zone):
    """Everything a hero must reach is reachable, the river and both ridges close exactly where they should, and the bands
    sit in the order the zone's levels climb. Returns a list of problems (empty: all fine)."""
    problems = []
    start = L.ARRIVAL
    full, blocked = fen.flood(zone, start)
    bridge_y = L.river_y(L.BRIDGE_X)
    seal_bridge = [(L.BRIDGE_X, bridge_y, 3.4)]
    south_only, _ = fen.flood(zone, start, seal_bridge)
    seal_a = seal_bridge + [(L.R_A_GAP[0], L.R_A_GAP[1], L.RIDGE_GAP_HALF + .8)]
    below_a, _ = fen.flood(zone, start, [(L.R_A_GAP[0], L.R_A_GAP[1], L.RIDGE_GAP_HALF + .8)])
    below_b, _ = fen.flood(zone, start, [(L.R_B_GAP[0], L.R_B_GAP[1], L.RIDGE_GAP_HALF + .8)])
    targets = [(n['id'], n['x'], n['y']) for n in zone['npcs']] + [(s['kind'], s['x'], s['y']) for s in zone['slimes'] if not s.get('ambush')]
    targets += [(p['id'], p['x'], p['y'] + (2.4 if p['id'] in L.BEACONS else 0)) for p in zone['places']]   # a beacon stands in the middle of its place
    targets += [('gate', L.GATE[0] + 2, L.GATE[1]), ('start', *L.EYDIS_START)]
    for name, x, y in targets:
        if not cell(full, x, y):
            problems.append(f'{name} at ({x}, {y}) is unreachable from the arrival')
    # the river
    for s in zone['slimes']:
        north = s['y'] < bridge_y - 6
        if north and cell(south_only, s['x'], s['y']):
            problems.append(f"{s['kind']} at ({s['x']}, {s['y']}) is north of the river but reachable without the bridge")
    for name, x, y in [('Skuldwatch plaza', 96, 86), ('the heights', 96, 30)]:
        if cell(south_only, x, y):
            problems.append(f'{name} is reachable without the bridge')
    # the ridges: rams only above the first, Hrungnir only above the second
    for s in zone['slimes']:
        if s['kind'] == 'ram' and cell(below_a, s['x'], s['y']):
            problems.append(f"ram at ({s['x']}, {s['y']}) is reachable without the first ridge gap")
        if s['kind'] in ('weaver',) and not cell(below_a, s['x'], s['y']):
            problems.append(f"weaver at ({s['x']}, {s['y']}) is above the first ridge")
        if s['kind'] == 'hrungnir' and cell(below_b, s['x'], s['y']):
            problems.append('Hrungnir is reachable without the second ridge gap')
        if s['kind'] == 'ram' and not cell(below_b, s['x'], s['y']):
            problems.append(f"ram at ({s['x']}, {s['y']}) is above the second ridge")
    for pid in L.BEACONS:
        p = next(q for q in zone['places'] if q['id'] == pid)
        p = dict(p, y=p['y'] + 2.4)
        if pid == 'wyrd_beacon_ridge' and cell(below_a, p['x'], p['y']):
            problems.append('the Ridge Beacon is reachable without the first gap')
        if pid == 'wyrd_beacon_storm' and cell(below_a, p['x'], p['y']):
            problems.append('the Storm Beacon is reachable without the first gap')
    # people stand on free ground inside their hub
    soft = fen.obstacle_grid(zone, STEP, margin=.35)
    for n in zone['npcs']:
        if cell(soft, n['x'], n['y']):
            problems.append(f"{n['id']} stands inside scenery at ({n['x']}, {n['y']})")
    hubs = [(content.HOLLOW_CITY, 'wyrd_'), (content.SKULD_CITY, 'wyrd_')]
    hollow_ids = {n['id'] for n in content.hollowmoot()[0]}
    for n in zone['npcs']:
        if n['id'] == 'wyrd_eydis':
            continue
        hub = content.HOLLOW_CITY if n['id'] in hollow_ids else content.SKULD_CITY
        if not (hub['x0'] <= n['x'] <= hub['x1'] and hub['y0'] <= n['y'] <= hub['y1']):
            problems.append(f"{n['id']} is outside {hub['name']}")
    # the escort walks over clear ground the whole way, and ends in Skuldwatch
    route = [(zone_npc['x'], zone_npc['y']) for zone_npc in zone['npcs'] if zone_npc.get('escort')] + [tuple(p) for n in zone['npcs'] if n.get('escort') for p in n['escort']['route']]
    walk = fen.obstacle_grid(zone, STEP, margin=.8)
    for a, b in zip(route, route[1:]):
        if not line_clear(walk, a, b):
            problems.append(f'the escort route is blocked between {a} and {b}')
    end = route[-1]
    sk = content.SKULD_CITY
    if not (sk['x0'] <= end[0] <= sk['x1'] and sk['y0'] <= end[1] <= sk['y1']):
        problems.append(f'the escort route ends outside Skuldwatch at {end}')
    # spacing and bands
    live = [s for s in zone['slimes'] if not s.get('ambush')]
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if math.hypot(a['x'] - b['x'], a['y'] - b['y']) < 6.0:
                problems.append(f"{a['kind']} and {b['kind']} stand within 6 at ({a['x']}, {a['y']})")
    for s in zone['slimes']:
        for h in (L.HOLLOW, L.STORM_WALL):
            if in_rect(s['x'], s['y'], hub_rect(h, 8.0)):
                problems.append(f"{s['kind']} at ({s['x']}, {s['y']}) is within 8 of a hub")
        if math.hypot(s['x'] - L.ARRIVAL[0], s['y'] - L.ARRIVAL[1]) < 8:
            problems.append(f"{s['kind']} is within 8 of the arrival")
    return problems


def open_stormrift(zone, world):
    """The Stormrift in the summit court's north-west corner: a ring of standing stones round a portal up to Bifrost Reach.
    Done after the zone is built and only when Bifrost Reach exists, so no random number is drawn and the rest of the zone is
    unchanged; scenery in the clearing goes. Idempotent."""
    import sky_layout as S
    if not any(z['name'] == S.NAME for z in world['zones']):
        return
    gx, gy = S.WYRD_GATE
    zone['objects'] = [o for o in zone['objects'] if o['kind'] not in ('tree', 'pine', 'bush', 'rock', 'spire', 'post', 'bones', 'crag')
                       or math.hypot(o['x'] - gx, o['y'] - gy) > 8.0 or o.get('place')]
    zone['objects'] = [o for o in zone['objects'] if o.get('rift') is None]
    for i in range(7):
        a = 2 * math.pi * i / 7 + .3
        zone['objects'].append(obj('spire', gx + 3.6 * math.cos(a), gy + 3.6 * math.sin(a), .55, i % 4, rift=1))
    zone['portals'] = [p for p in zone['portals'] if p['id'] != 'sky_gate']
    zone['portals'].append({'id': 'sky_gate', 'name': 'the Stormrift', 'x': gx, 'y': gy, 'r': 1.3, 'to': 7, 'tx': S.ARRIVAL[0], 'ty': S.ARRIVAL[1]})
    # the summit court's arrival point must be free ground
    wx, wy = S.WYRD_ARRIVAL
    assert not any(math.hypot(o['x'] - wx, o['y'] - wy) < o['r'] + 1.0 for o in zone['objects'] if o.get('r')), 'the Stormrift arrival is blocked'


def add_materials():
    items = json.loads(ITEMS.read_text())
    have = {i['id'] for i in items}
    at = next(n for n, i in enumerate(items) if i['id'] == 'crown_shard') + 1
    for k, (id_, name, sell) in enumerate([m for m in MATERIALS if m[0] not in have]):
        items.insert(at + k, {'id': id_, 'name': name, 'kind': 'material', 'rarity': 'common', 'sell': sell})
    ITEMS.write_text(json.dumps(items, indent=2))
    return len(MATERIALS) - len(have & {m[0] for m in MATERIALS})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot', help='write a PNG of the layout to this path and stop')
    args = parser.parse_args()
    zone = build(random.Random(20261009))
    problems = check(zone)
    if args.plot:
        plot(zone, args.plot)
        print('plotted', args.plot, len(zone['objects']), 'objects;', len(problems), 'problem(s)')
        for p in problems[:40]:
            print('  ', p)
        return
    if problems:
        raise SystemExit('The Wyrdwood layout has problems:\n  ' + '\n  '.join(problems))
    raw = PATH.read_text()
    world = json.loads(raw)
    assert json.dumps(world, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    names = [z['name'] for z in world['zones']]
    assert names[:5] == ['Emberfall Crags', 'Rimeveil Glacier', 'Gloamfen', 'Skaldholm', 'The Undervault'], f'unexpected zones {names}'
    # a rebuild keeps every later zone (Bifrost Reach) and puts the Wyrdwood back in the same place
    others = [z for z in world['zones'] if z['name'] != L.NAME]
    at = names.index(L.NAME) if L.NAME in names else len(others)
    world['zones'] = others[:at] + [zone] + others[at:]
    assert world['zones'][5]['name'] == L.NAME, 'the Wyrdwood must be zone 6'
    open_stormrift(zone, world)
    skald = world['zones'][3]
    assert any(p['id'] == 'wyrd_gate' for p in skald['portals']), 'run generate_skaldholm.py first: Skaldholm has no East Gate'
    spark_travel.ensure(world)
    PATH.write_text(json.dumps(world, indent=2) + '\n')
    new = add_materials()
    kinds = {}
    for sl in zone['slimes']:
        kinds[sl['kind']] = kinds.get(sl['kind'], 0) + 1
    print(f"Wrote zone 6 {zone['name']}: {len(zone['objects'])} objects, spawns {kinds}, {len(zone['npcs'])} NPCs, {len(zone['quests'])} quests; {new} new materials. Now run node scripts/sync-world.cjs")


if __name__ == '__main__':
    main()
