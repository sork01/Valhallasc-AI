#!/usr/bin/env python3
"""Writes Bifrost Reach (zone 7, levels 30-35) into world/map.txt, and checks it.

A sky zone: eight floating islands joined by rainbow-shard bridges over open void, one hub (Heimdall's Perch), five new
monster kinds and three wards for the new `hold` quest objective. The layout is in sky_layout.py, the people and quests in
sky_content.py. The zone lists its floor as 160 strings (`sky`: ' ' void, '#' island, '=' bridge) for the client, and the
void next to the floor as rectangles (`void` objects, up to two tiles thick) that the server collides with.

The zone is appended after the Wyrdwood, so no older enemy id moves; the dungeon copies, which the world appends after every
file zone, move from zones 7-9 to 8-10. Its return gate leads to the Wyrdwood's Stormrift, which generate_wyrdwood.py writes
(`open_stormrift`: it clears the summit court's north-west corner and adds the portal). Re-running replaces zone 7 and leaves
everything else alone; it is idempotent. Afterwards: node scripts/sync-world.cjs, then rebuild Rust.
Use --plot FILE.png to draw the layout.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_gloamfen as fen                    # noqa: E402  (flood fill helpers)
import generate_deep                               # noqa: E402  (open_maelstrom)
import generate_wyrdwood as wyrd                   # noqa: E402  (open_stormrift)
import progression_quests                          # noqa: E402
import sky_content as content                      # noqa: E402
import sky_layout as L                             # noqa: E402
import spark_travel                                # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
SIZE = L.SIZE
ZONE = 7
STEP = .5
VOID_PIECE = 8                                     # longest void rectangle
MATERIALS = [  # id, name, sell: what Bifrost Reach's monsters carry (items::material)
    ('gale_fang', 'Gale Fang', 400), ('prism_shard', 'Prism Shard', 430), ('stormray_wing', 'Stormray Wing', 460),
    ('rune_token', 'Worn Rune Token', 500), ('thunderroc_quill', 'Thunderroc Quill', 580)]


def obj(kind, x, y, r, v=0, **extra):
    o = {'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': r, 'v': v}
    o.update(extra)
    return o


# ---- the floor and the void ------------------------------------------------------------------------------------------------
def sky_rows(floor, bridges):
    return [''.join('=' if bridges[j, i] else '#' if floor[j, i] else ' ' for i in range(SIZE)) for j in range(SIZE)]


def void_pieces(floor):
    """Cells within two tiles (any direction) of the floor that are not floor become void; runs are merged into rectangles
    cut to VOID_PIECE long. Beyond that nothing is reachable, so nothing more is needed."""
    pad = np.pad(floor, 2)
    near = np.zeros_like(floor)
    for dj in range(-2, 3):
        for di in range(-2, 3):
            near |= pad[2 + dj:2 + dj + SIZE, 2 + di:2 + di + SIZE]
    wall = near & ~floor
    used = np.zeros_like(wall)
    rects = []
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
        if w >= d:
            n = max(1, math.ceil(w / VOID_PIECE))
            for k in range(n):
                a, b = x0 + w * k / n, x0 + w * (k + 1) / n
                out.append(((a + b) / 2, (y0 + y1) / 2, b - a, d))
        else:
            n = max(1, math.ceil(d / VOID_PIECE))
            for k in range(n):
                a, b = y0 + d * k / n, y0 + d * (k + 1) / n
                out.append(((x0 + x1) / 2, (a + b) / 2, w, b - a))
    return [{'kind': 'void', 'x': round(x, 2), 'y': round(y, 2), 'r': round(max(w, d) / 2, 2), 'width': round(w, 2), 'depth': round(d, 2)}
            for x, y, w, d in out]


# ---- hub and landmarks --------------------------------------------------------------------------------------------------------
def landmarks():
    out = []
    for place in L.PLACES:
        pid = place['id']
        x, y = place['x'], place['y']
        if pid in L.WARDS:
            out.append(obj('wardstone', x, y, .7, 0, place=pid))
        elif pid == 'sky_windcairn':
            out.append(obj('windcairn', x, y, .8, 0, place=pid))
        elif pid == 'sky_spire':
            out.append(obj('spirelight', x, y, .9, 0, place=pid))
        elif pid == 'sky_pylon':
            out.append(obj('pylon', x, y, 1.3, 0, place=pid))
        elif pid == 'sky_hallgate':
            out.append(dict(kind='hallgate', x=x, y=y, r=0, v=0, width=5.0, depth=1.4, place=pid))
    out.append(obj('nest', 115.0, 25.0, 2.3, 0))                      # the roc's nest, beside the last ward
    for dx in (-1.5, 1.5):                                           # the Stormrift's posts
        out.append(obj('post', L.GATE[0] + dx, L.GATE[1], .45, 0))
    return out


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


def build(rng):
    floor, bridges, _ = L.masks()
    isl_masks = {k: L.island_mask(i) for k, i in L.ISLANDS.items()}
    edge = ndimage.distance_transform_edt(floor)                 # tiles to the nearest void
    bridge_dist = ndimage.distance_transform_edt(~bridges)       # tiles to the nearest bridge cell
    npcs, quests, hub_objects, city = content.perch()
    objects = void_pieces(floor) + landmarks() + hub_objects
    ground = Ground()
    for o in objects:
        if o['kind'] != 'void':
            ground.add(o)

    def cell(x, y):
        return int(y), int(x)

    def on_island(name, x, y):
        return isl_masks[name][cell(x, y)]

    # --- spawns
    spawns = []
    place_keep = [(p['x'], p['y'], p['r'] + 6.0) for p in L.PLACES]
    for kind, count, spacing, islands in L.BANDS:
        placed, tries = 0, 0
        while placed < count and tries < 60000:
            tries += 1
            name = rng.choice(islands)
            isl = L.ISLANDS[name]
            x, y = rng.uniform(isl['cx'] - isl['rx'], isl['cx'] + isl['rx']), rng.uniform(isl['cy'] - isl['ry'], isl['cy'] + isl['ry'])
            if not (0 < x < SIZE and 0 < y < SIZE) or not on_island(name, x, y):
                continue
            if edge[cell(x, y)] < 3.5 or bridge_dist[cell(x, y)] < 8.0:
                continue
            if in_hub(x, y, 11.0) or math.hypot(x - L.ARRIVAL[0], y - L.ARRIVAL[1]) < 14:
                continue
            if any(math.hypot(x - a, y - b) < r for a, b, r in place_keep):
                continue
            if any(math.hypot(x - s['x'], y - s['y']) < (spacing if s['kind'] == kind else 6.5) for s in spawns):
                continue
            if not ground.clear(x, y, 2.3):
                continue
            spawns.append({'x': round(x, 2), 'y': round(y, 2), 'kind': kind})
            placed += 1
        assert placed == count, f'only {placed} of {count} {kind}'
    # --- ward waves: sleeping ambushers just outside each circle
    waves = {}
    for pid, plan in L.WARDS.items():
        place = next(p for p in L.PLACES if p['id'] == pid)
        host = next(k for k, m in isl_masks.items() if m[cell(place['x'], place['y'])])
        chosen = []
        for at, suffix, kind, n in plan:
            tag = f'{pid}#{suffix}'
            waves.setdefault(pid, []).append({'at': at, 'tag': tag})
            got = 0
            for _ in range(40000):
                ang = rng.uniform(0, 2 * math.pi)
                d = rng.uniform(place['r'] + 1.2, place['r'] + 7.0)
                x, y = place['x'] + d * math.cos(ang), place['y'] + d * math.sin(ang)
                if not (0 < x < SIZE and 0 < y < SIZE) or not isl_masks[host][cell(x, y)] or edge[cell(x, y)] < 2.5:
                    continue
                if any(math.hypot(x - q['x'], y - q['y']) < 3.0 for q in chosen):
                    continue
                if any(math.hypot(x - q['x'], y - q['y']) < 7.0 for q in spawns if not q.get('ambush')):
                    continue
                if not ground.clear(x, y, 1.6):
                    continue
                chosen.append({'x': round(x, 2), 'y': round(y, 2), 'kind': kind, 'ambush': tag})
                got += 1
                if got == n:
                    break
            assert got == n, f'no room for the {tag} wave'
        spawns += chosen
    for q in spawns:
        ground.add(dict(x=q['x'], y=q['y'], r=.4))

    # --- scenery on islands, off the hub, the bridges, the places and the edges
    def ok(x, y, r, margin, edge_min):
        if not (1 < x < SIZE - 1 and 1 < y < SIZE - 1) or not floor[cell(x, y)] or bridges[cell(x, y)]:
            return False
        if edge[cell(x, y)] < edge_min or bridge_dist[cell(x, y)] < 4.5:
            return False
        if in_hub(x, y, 1.0) or math.hypot(x - L.GATE[0], y - L.GATE[1]) < 7:
            return False
        if any(math.hypot(x - p['x'], y - p['y']) < p['r'] + 1.4 for p in L.PLACES):
            return False
        return ground.clear(x, y, r + margin)

    def scatter(kind, count, r, islands, margin=1.1, edge_min=3.0, v_choices=4):
        placed, tries = 0, 0
        while placed < count and tries < 60000:
            tries += 1
            name = rng.choice(islands)
            isl = L.ISLANDS[name]
            x, y = rng.uniform(isl['cx'] - isl['rx'], isl['cx'] + isl['rx']), rng.uniform(isl['cy'] - isl['ry'], isl['cy'] + isl['ry'])
            if not (0 < x < SIZE and 0 < y < SIZE) or not on_island(name, x, y) or not ok(x, y, r, margin, edge_min):
                continue
            o = obj(kind, x, y, r, rng.randrange(v_choices))
            objects.append(o)
            ground.add(o)
            placed += 1
        assert placed == count, f'only {placed} of {count} {kind}'

    every = list(L.ISLANDS)
    scatter('skypine', 26, .42, ['windward'])
    scatter('skypine', 10, .42, ['perch', 'hall', 'eyrie'])
    scatter('prism', 30, .6, ['shards'], margin=1.6)
    scatter('prism', 10, .6, ['crown', 'spire', 'eyrie'], margin=1.6)
    scatter('column', 14, .55, ['crown'], margin=1.8)
    scatter('column', 16, .55, ['hall'], margin=1.8)
    scatter('skyrock', 40, .45, every, margin=1.2)
    scatter('cloudpuff', 110, .3, every, margin=.8, edge_min=2.0)
    zone = {'name': L.NAME, 'theme': 'sky', 'tagline': 'Above the storm, where the rainbow bridge broke into shards', 'size': SIZE, 'levels': list(L.LEVELS),
            'spawn': {'x': L.ARRIVAL[0], 'y': L.ARRIVAL[1]}, 'paths': [],
            'sky': sky_rows(floor, bridges),
            'places': [dict(p, **({'waves': waves[p['id']]} if p['id'] in waves else {})) for p in L.PLACES],
            'objects': objects, 'slimes': spawns, 'npcs': npcs, 'quests': quests, 'city': city,
            'portals': [{'id': 'stormrift_down', 'name': 'the Stormrift', 'x': L.GATE[0], 'y': L.GATE[1], 'r': 1.2,
                         'to': 6, 'tx': L.WYRD_ARRIVAL[0], 'ty': L.WYRD_ARRIVAL[1]}]}
    return zone


# ---- plotting ------------------------------------------------------------------------------------------------------------------
def plot(zone, path, scale=5):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (SIZE * scale, SIZE * scale), (20, 30, 70))
    d = ImageDraw.Draw(img)
    for j, row in enumerate(zone['sky']):
        for i, c in enumerate(row):
            if c != ' ':
                d.rectangle([i * scale, j * scale, (i + 1) * scale - 1, (j + 1) * scale - 1], fill=(110, 160, 90) if c == '#' else (230, 180, 80))
    colours = {'skypine': (30, 100, 60), 'prism': (150, 220, 255), 'column': (220, 220, 230), 'skyrock': (130, 130, 140), 'cloudpuff': (240, 240, 250),
               'void': (60, 20, 40), 'house': (180, 120, 80), 'chapel': (200, 120, 100)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        c = colours.get(o['kind'], (255, 255, 255))
        if o.get('width'):
            d.rectangle([(o['x'] - o['width'] / 2) * scale, (o['y'] - o['depth'] / 2) * scale, (o['x'] + o['width'] / 2) * scale, (o['y'] + o['depth'] / 2) * scale], fill=c)
        else:
            r = o['r'] * scale
            d.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'galehound': (220, 60, 60), 'prismgolem': (60, 200, 255), 'skyray': (200, 60, 200), 'einherjar': (240, 240, 60), 'thunderroc': (255, 140, 0)}
    for s in zone['slimes']:
        r = 8 if not s.get('ambush') else 5
        d.ellipse([s['x'] * scale - r, s['y'] * scale - r, s['x'] * scale + r, s['y'] * scale + r], outline=kc[s['kind']], width=2)
    for n in zone['npcs']:
        d.rectangle([n['x'] * scale - 3, n['y'] * scale - 3, n['x'] * scale + 3, n['y'] * scale + 3], fill=(255, 255, 0))
    for p in zone['places']:
        d.ellipse([(p['x'] - p['r']) * scale, (p['y'] - p['r']) * scale, (p['x'] + p['r']) * scale, (p['y'] + p['r']) * scale], outline=(0, 255, 255), width=2)
    img.save(path)


# ---- checks --------------------------------------------------------------------------------------------------------------------
def cell(grid, x, y):
    return grid[int(y / STEP), int(x / STEP)]


def mid(points):
    """The middle of a bridge's longest leg, where a seal closes it."""
    legs = [((ax + bx) / 2, (ay + by) / 2, abs(ax - bx) + abs(ay - by)) for (ax, ay), (bx, by) in zip(points, points[1:])]
    x, y, _ = max(legs, key=lambda t: t[2])
    return x + .5, y + .5


def check(zone):
    """Everything a hero must reach is reachable, and each bridge closes exactly the islands it should."""
    problems = []
    full, _ = fen.flood(zone, L.ARRIVAL)
    targets = [(n['id'], n['x'], n['y']) for n in zone['npcs']] + [(s['kind'], s['x'], s['y']) for s in zone['slimes']]
    targets += [(p['id'], p['x'], p['y'] + 2.4) for p in zone['places']]   # a landmark stands in the middle of its place + [('gate', L.GATE[0], L.GATE[1] - 2)]
    for name, x, y in targets:
        if not cell(full, x, y):
            problems.append(f'{name} at ({x}, {y}) is unreachable from the arrival')
    floor, _, _ = L.masks()
    isl = {k: L.island_mask(i) for k, i in L.ISLANDS.items()}

    def seal(*ids):
        return [(*mid(L.BRIDGES[b]), L.BRIDGE_W / 2 + .8) for b in ids]

    def islands_cut(*ids):
        """Islands none of whose spawns/places can be reached with these bridges closed."""
        reach, _ = fen.flood(zone, L.ARRIVAL, seal(*ids))
        cut = set()
        for k in L.ISLANDS:
            probes = [(s['x'], s['y']) for s in zone['slimes'] if isl[k][int(s['y']), int(s['x'])]] + \
                     [(p['x'], p['y'] + 2.4) for p in zone['places'] if isl[k][int(p['y']), int(p['x'])]]
            if probes and not any(cell(reach, x, y) for x, y in probes):
                cut.add(k)
        return cut
    expect = [
        (('b_west', 'b_east'), {'windward', 'shards', 'crown', 'hall', 'eyrie', 'ward', 'spire'}),
        (('b_wcrown', 'b_scrown'), {'crown', 'hall', 'eyrie'}),
        (('b_west', 'b_wcrown'), {'windward', 'ward'}),
        (('b_east', 'b_scrown'), {'shards', 'spire'}),
        (('b_hall',), {'hall', 'eyrie'}),
        (('b_eyrie',), {'eyrie'}),
        (('b_ward',), {'ward'}),
        (('b_spire',), {'spire'}),
        (('b_west',), set()),
        (('b_wcrown',), set()),
    ]
    for ids, want in expect:
        got = islands_cut(*ids)
        if got != want:
            problems.append(f'closing {ids} cuts off {sorted(got)}, expected {sorted(want)}')
    # people stand on free ground inside the hub
    soft = fen.obstacle_grid(zone, STEP, margin=.35)
    h = content.HUB
    for n in zone['npcs']:
        if cell(soft, n['x'], n['y']):
            problems.append(f"{n['id']} stands inside scenery at ({n['x']}, {n['y']})")
        if not (h['x0'] <= n['x'] <= h['x1'] and h['y0'] <= n['y'] <= h['y1']):
            problems.append(f"{n['id']} is outside the hub")
    # the hub, the gate and the places are all floor with room round them
    rows = zone['sky']
    for o in zone['objects']:
        if o['kind'] in ('house', 'chapel', 'stall', 'fountain', 'lamp', 'bench', 'noticeboard') and rows[int(o['y'])][int(o['x'])] == ' ':
            problems.append(f"{o['kind']} at ({o['x']}, {o['y']}) hangs over the void")
    for name, (x, y) in [('arrival', L.ARRIVAL), ('gate', L.GATE)]:
        if rows[int(y)][int(x)] == ' ':
            problems.append(f'the {name} is over the void')
    edge = ndimage.distance_transform_edt(np.array([[c != ' ' for c in row] for row in rows]))
    for p in zone['places']:
        if edge[int(p['y']), int(p['x'])] < 3:
            problems.append(f"{p['id']} is too close to the edge")
    # spawns: spacing, off scenery, away from the arrival and the hub
    live = [s for s in zone['slimes'] if not s.get('ambush')]
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if math.hypot(a['x'] - b['x'], a['y'] - b['y']) < 6.0:
                problems.append(f"{a['kind']} and {b['kind']} stand within 6 at ({a['x']}, {a['y']})")
    for s in zone['slimes']:
        if math.hypot(s['x'] - L.ARRIVAL[0], s['y'] - L.ARRIVAL[1]) < 8:
            problems.append(f"{s['kind']} is within 8 of the arrival")
        if in_hub(s['x'], s['y'], 8.0):
            problems.append(f"{s['kind']} at ({s['x']}, {s['y']}) is within 8 of the hub")
    return problems


def add_materials():
    items = json.loads(ITEMS.read_text())
    have = {i['id'] for i in items}
    at = next(n for n, i in enumerate(items) if i['id'] == 'stormheart_shard') + 1
    new = [m for m in MATERIALS if m[0] not in have]
    for k, (id_, name, sell) in enumerate(new):
        items.insert(at + k, {'id': id_, 'name': name, 'kind': 'material', 'rarity': 'common', 'sell': sell})
    ITEMS.write_text(json.dumps(items, indent=2))
    return len(new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot', help='write a PNG of the layout to this path and stop')
    args = parser.parse_args()
    zone = build(random.Random(20261012))
    problems = check(zone)
    if args.plot:
        plot(zone, args.plot)
        print('plotted', args.plot, len(zone['objects']), 'objects;', len(problems), 'problem(s)')
        for p in problems[:40]:
            print('  ', p)
        return
    if problems:
        raise SystemExit('Bifrost Reach has problems:\n  ' + '\n  '.join(problems))
    raw = PATH.read_text()
    world = json.loads(raw)
    assert json.dumps(world, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    names = [z['name'] for z in world['zones']]
    assert names[:6] == ['Emberfall Crags', 'Rimeveil Glacier', 'Gloamfen', 'Skaldholm', 'The Undervault', 'Wyrdwood'], f'unexpected zones {names}'
    # a rebuild keeps every later zone (Ran's Deep) and puts Bifrost Reach back in the same place
    others = [z for z in world['zones'] if z['name'] != L.NAME]
    at = names.index(L.NAME) if L.NAME in names else len(others)
    world['zones'] = others[:at] + [zone] + others[at:]
    assert world['zones'][6]['name'] == L.NAME, 'Bifrost Reach must be zone 7'
    wyrd.open_stormrift(world['zones'][5], world)
    generate_deep.open_maelstrom(world['zones'][6], world)
    spark_travel.ensure(world)
    PATH.write_text(json.dumps(world, indent=2) + '\n')
    new = add_materials()
    kinds = {}
    for sl in zone['slimes']:
        kinds[sl['kind']] = kinds.get(sl['kind'], 0) + 1
    print(f"Wrote zone 7 {zone['name']}: {len(zone['objects'])} objects, spawns {kinds}, {len(zone['npcs'])} NPCs, {len(zone['quests'])} quests; {new} new materials. Now run node scripts/sync-world.cjs")


if __name__ == '__main__':
    main()
